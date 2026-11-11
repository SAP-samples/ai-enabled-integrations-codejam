"""AMQP 1.0 event consumer for SAP Integration Suite, advanced event mesh (AEM).

Optional and OFF by default. Gated entirely by the ``ENABLE_EVENTING`` env var:

* ``ENABLE_EVENTING=1`` — on server startup, connect to an AEM broker over
  AMQP 1.0, consume events, and publish the agent's answers back to AEM.
* ``ENABLE_EVENTING=0`` (or unset) — this module is never activated and no
  broker connection is attempted; the agent runs as a plain A2A HTTP server.

Each incoming event is a CloudEvents 1.0 envelope whose ``data.message`` is a
free-text chat request — exactly what a user would type into the A2A chat UI
(e.g. "Get me the latest service requests for ai-integrations-000"). The text is
run through the same :class:`SampleAgent` the HTTP path uses, and the agent's
reply is published to a separate AEM topic as a CloudEvents 1.0 envelope over
the *same* AMQP connection (no separate REST endpoint or credentials).

The consumed queue must be subscribed to the request topic
``altura/customer-request-agent/request/v1`` on the broker so that request
events routed to that topic land on the queue.

Note on auth: the event path has no per-user JWT, so tool calls run without an
end-user token (``get_user_token()`` is ``None``). The primary customer-request
MCP server needs no auth and the service-locator MCP uses client credentials, so
both still work; only user-scoped tools would lack an end-user token here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Sequence
from urllib.parse import quote

from langchain_core.tools import BaseTool

from mcp_tools import get_mcp_tools

if TYPE_CHECKING:
    from agent import SampleAgent

logger = logging.getLogger(__name__)

REQUEST_EVENT_TYPE = "com.altura.customer-request-agent.request.v1"
RESPONSE_EVENT_TYPE = "com.altura.customer-request-agent.response.v1"
RESPONSE_SOURCE = "/customer-request-agent"
RESPONSE_CONTENT_TYPE = "application/cloudevents+json"
# Content type for plain-text replies (mirrors a plain-text request).
PLAIN_CONTENT_TYPE = "text/plain"

# The request topic the consumed queue must be subscribed to on the broker.
REQUEST_TOPIC = "altura/customer-request-agent/request/v1"

# How long receive() blocks before we loop back to check the stop flag.
_RECEIVE_TIMEOUT_SECONDS = 5.0
# Backoff between broker reconnection attempts.
_RECONNECT_DELAY_SECONDS = 10.0


def eventing_enabled() -> bool:
    """True only when ENABLE_EVENTING is explicitly set to "1"."""
    return os.getenv("ENABLE_EVENTING", "0").strip() == "1"


@dataclass
class ConsumerConfig:
    """Broker connection + reply-publish configuration, read from the environment."""

    amqp_host: str
    amqp_port: int
    amqp_user: str
    amqp_password: str
    queue_name: str
    tls_verify: bool
    # Topic the agent publishes its response CloudEvent to (same AMQP connection).
    response_topic: str

    @property
    def amqp_url(self) -> str:
        """amqps:// URL with URL-encoded credentials for SASL PLAIN."""
        userinfo = ""
        if self.amqp_user:
            userinfo = (
                f"{quote(self.amqp_user, safe='')}:"
                f"{quote(self.amqp_password, safe='')}@"
            )

        return f"amqps://{userinfo}{self.amqp_host}:{self.amqp_port}"

    def validate(self) -> list[str]:
        """Return a list of human-readable problems (empty = OK)."""
        problems: list[str] = []
        if not self.amqp_host:
            problems.append("AEM_AMQP_HOST is not set")
        if not self.queue_name:
            problems.append("AEM_AMQP_QUEUE_NAME is not set")
        if not self.amqp_user:
            problems.append("AEM_AMQP_USERNAME is not set")
        return problems


def load_config() -> ConsumerConfig:
    """Build a :class:`ConsumerConfig` from environment variables."""
    return ConsumerConfig(
        amqp_host=os.getenv("AEM_AMQP_HOST", "").strip(),
        amqp_port=int(os.getenv("AEM_AMQP_PORT", "5671")),
        amqp_user=os.getenv("AEM_AMQP_USERNAME", "").strip(),
        amqp_password=os.getenv("AEM_AMQP_PASSWORD", "").strip(),
        queue_name=os.getenv("AEM_AMQP_QUEUE_NAME", "").strip(),
        tls_verify=os.getenv("AEM_AMQP_TLS_VERIFY", "1").strip() != "0",
        response_topic=os.getenv("AEM_RESPONSE_TOPIC", "").strip().strip("/"),
    )


def extract_query(body: Any) -> tuple[str, dict]:
    """Extract the chat message from a raw AMQP message body.

    Expects a CloudEvents 1.0 JSON envelope whose ``data.message`` holds the chat
    text. Degrades gracefully: ``data`` may be a bare string, or the whole body
    may be plain (non-JSON) text.

    Returns ``(query, envelope)``. Raises ``ValueError`` if no chat text is found.
    """

    logger.info(str(body))

    # proton may hand back the AMQP data section as a memoryview.
    if isinstance(body, memoryview):
        body = body.tobytes()

    if isinstance(body, (bytes, bytearray)):
        body = bytes(body).decode("utf-8")

    logger.info(f"Decoded body: {body}")

    if isinstance(body, str):
        text = body.strip()
        try:
            envelope = json.loads(text)
        except json.JSONDecodeError:
            # Not JSON — treat the raw text as the chat message itself.
            if not text:
                raise ValueError("Empty event body")
            return text, {}
    elif isinstance(body, dict):
        envelope = body
    else:
        raise ValueError(f"Unsupported message body type: {type(body).__name__}")

    data = envelope.get("data", envelope) if isinstance(envelope, dict) else envelope
    if isinstance(data, str):
        query = data
    elif isinstance(data, dict):
        query = data.get("message") or data.get("text") or ""
    else:
        query = ""

    query = (query or "").strip()
    if not query:
        raise ValueError("Event contained no chat message (data.message is empty)")
    return query, envelope if isinstance(envelope, dict) else {}


def build_response_event(message: str, context_id: str) -> dict:
    """Wrap the agent's answer in a CloudEvents 1.0 envelope."""
    return {
        "specversion": "1.0",
        "type": RESPONSE_EVENT_TYPE,
        "source": RESPONSE_SOURCE,
        "id": str(uuid.uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": {"context_id": context_id, "message": message},
    }


def publish_reply(
    publish: Callable[[str, str], None] | None,
    message: str,
    context_id: str,
    plain_text: bool = False,
) -> None:
    """Publish the agent's answer via the given AMQP publisher.

    ``publish`` sends one already-serialized payload and its content type to the
    response topic. It is ``None`` when no response topic is configured, in which
    case the reply is skipped.

    When ``plain_text`` is true (the request arrived as raw text), the raw answer
    string is sent as ``text/plain``. Otherwise the answer is wrapped in a
    CloudEvents 1.0 envelope and sent as ``application/cloudevents+json``.
    """
    if publish is None:
        logger.warning("Reply not published: AEM_RESPONSE_TOPIC not configured")
        return

    if plain_text:
        payload = message
        content_type = PLAIN_CONTENT_TYPE
    else:
        payload = json.dumps(build_response_event(message, context_id))
        content_type = RESPONSE_CONTENT_TYPE

    try:
        logger.info(
            "Publishing response (context_id=%s, content_type=%s): %s",
            context_id,
            content_type,
            payload,
        )
        publish(payload, content_type)
        logger.info("Published response (context_id=%s)", context_id)
    except Exception as e:
        logger.error("Failed to publish response to AEM: %s", e)


async def process_event(
    agent: SampleAgent,
    skill_tools: Sequence[BaseTool],
    publish: Callable[[str, str], None] | None,
    body: Any,
) -> None:
    """Run one event through the agent and publish the reply.

    Mirrors the tool-loading + invoke sequence in ``AgentExecutor.execute``.
    """
    query, envelope = extract_query(body)
    # An empty envelope means the request body was raw text, not a CloudEvent;
    # reply in kind so the response matches the request format.
    is_plain = not envelope
    context_id = str(uuid.uuid4())
    logger.info(
        "Event received (id=%s) -> context_id=%s",
        envelope.get("id", "<none>"),
        context_id,
    )

    # Load MCP tools per-event, same as the HTTP path. Failures are non-fatal:
    # the agent will explain that tools are unavailable rather than crash.
    tools: list[BaseTool] = list(skill_tools)
    try:
        mcp_tools = await get_mcp_tools()
        if mcp_tools:
            tools = [*mcp_tools, *skill_tools]
            logger.info("Loaded %d MCP tool(s) for event execution", len(mcp_tools))
        else:
            logger.warning("No MCP tools returned for event execution")
    except Exception as e:
        logger.error("Failed to load MCP tools for event: %s", e)

    response = await agent.invoke(query, context_id, tools=tools)
    publish_reply(publish, response.message, context_id, plain_text=is_plain)


def _consume_loop(
    config: ConsumerConfig,
    agent: SampleAgent,
    skill_tools: Sequence[BaseTool],
    stop_event: threading.Event,
) -> None:
    """Connect to the broker and consume until ``stop_event`` is set.

    Runs a single AMQP connection; raises on connection failure so the caller's
    reconnect loop can retry. Replies are published over the same connection via
    a sender on the response topic.
    """
    from proton import Delivery, Message, SSLDomain, Timeout
    from proton.utils import BlockingConnection

    ssl_domain = SSLDomain(SSLDomain.MODE_CLIENT)
    ssl_domain.set_peer_authentication(
        SSLDomain.VERIFY_PEER_NAME if config.tls_verify else SSLDomain.ANONYMOUS_PEER
    )

    logger.info(
        "Connecting to AEM broker %s:%s, queue '%s'",
        config.amqp_host,
        config.amqp_port,
        config.queue_name,
    )
    conn = BlockingConnection(config.amqp_url, ssl_domain=ssl_domain, heartbeat=30)
    receiver = conn.create_receiver(config.queue_name)

    # Reply publisher over the same connection, if a response topic is configured.
    publish: Callable[[str, str], None] | None = None
    if config.response_topic:
        # Solace treats an unqualified sender target as a queue; the explicit
        # topic:// prefix forces topic addressing so the publish is routed
        # (and not rejected as an unknown queue).
        sender_address = f"topic://{config.response_topic}"
        sender = conn.create_sender(sender_address)

        def publish(payload: str, content_type: str, _sender=sender) -> None:
            # error_states=[] so we inspect the disposition ourselves and can
            # log the broker's rejection condition rather than a bare state code.
            delivery = _sender.send(
                Message(body=payload, content_type=content_type),
                error_states=[],
            )
            state = delivery.remote_state
            if state in (Delivery.REJECTED, Delivery.RELEASED, Delivery.MODIFIED):
                condition = getattr(delivery.remote, "condition", None)
                raise RuntimeError(
                    f"broker did not accept publish (state={state}, "
                    f"condition={condition})"
                )

        logger.info("Publishing responses to '%s'", sender_address)
    else:
        logger.warning("AEM_RESPONSE_TOPIC not set — replies will not be published")

    # Proton is blocking; agent entry points are coroutines. Give this thread
    # its own event loop so we can drive them with run_until_complete.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    logger.info("AEM consumer ready — waiting for messages")
    try:
        while not stop_event.is_set():
            try:
                msg = receiver.receive(timeout=_RECEIVE_TIMEOUT_SECONDS)
            except Timeout:
                continue

            try:
                loop.run_until_complete(
                    process_event(agent, skill_tools, publish, msg.body)
                )
                receiver.accept()
            except Exception:
                logger.exception(
                    "Failed to process event; releasing for redelivery"
                )
                try:
                    receiver.release(delivered=True)
                except Exception:
                    logger.exception("Failed to release message")
    finally:
        loop.close()
        try:
            conn.close()
        except Exception:
            logger.exception("Error closing broker connection")


def _run_with_reconnect(
    config: ConsumerConfig,
    agent: SampleAgent,
    skill_tools: Sequence[BaseTool],
    stop_event: threading.Event,
) -> None:
    """Consumer thread entry point: consume with reconnect + backoff."""
    problems = config.validate()
    if problems:
        logger.error(
            "Eventing enabled but consumer not started — missing config: %s",
            "; ".join(problems),
        )
        return

    while not stop_event.is_set():
        try:
            _consume_loop(config, agent, skill_tools, stop_event)
        except Exception as e:
            logger.error("AEM consumer connection error: %s", e)
            # Wait before reconnecting, but stay responsive to shutdown.
            stop_event.wait(_RECONNECT_DELAY_SECONDS)
    logger.info("AEM consumer stopped")


def start_consumer_thread(
    agent: SampleAgent,
    skill_tools: Sequence[BaseTool],
) -> tuple[threading.Thread, threading.Event]:
    """Start the AMQP consumer on a daemon thread.

    Returns ``(thread, stop_event)``; set ``stop_event`` and join to shut down.
    """
    config = load_config()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_run_with_reconnect,
        args=(config, agent, skill_tools, stop_event),
        name="aem-consumer",
        daemon=True,
    )
    thread.start()
    return thread, stop_event
