"""Unit tests for the AMQP event consumer — no live broker required.

Covers CloudEvent parsing, response-envelope construction, REST reply publishing,
and the end-to-end process_event flow with the agent and broker mocked out.
The proton library is only imported lazily inside the broker loop, so these
tests run without python-qpid-proton installed.
"""

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("IBD_TESTING", "1")

# Make app/ importable as top-level modules, matching the runtime layout.
_APP_PATH = str(Path(__file__).parent.parent / "app")
if _APP_PATH not in sys.path:
    sys.path.insert(0, _APP_PATH)

import event_consumer as ec


class _FakeMessage:
    """Minimal stand-in for a proton Message."""

    def __init__(self, body):
        self.body = body


class _FakeResponse:
    """Minimal stand-in for SampleAgent's AgentResponse."""

    def __init__(self, message):
        self.status = "completed"
        self.message = message


def _sample_config() -> ec.ConsumerConfig:
    return ec.ConsumerConfig(
        amqp_host="broker.example.com",
        amqp_port=5671,
        amqp_user="user",
        amqp_password="secret",
        queue_name="q",
        tls_verify=True,
        response_topic="altura/customer-request-agent/response/v1",
    )


# --------------------------------------------------------------------------- #
# extract_query
# --------------------------------------------------------------------------- #


def test_extract_query_from_cloudevent():
    body = json.dumps(
        {
            "specversion": "1.0",
            "type": ec.REQUEST_EVENT_TYPE,
            "id": "evt-1",
            "data": {"message": "Get me the latest service requests for ai-integrations-000"},
        }
    )
    query, envelope = ec.extract_query(body)
    assert query == "Get me the latest service requests for ai-integrations-000"
    assert envelope["id"] == "evt-1"


def test_extract_query_accepts_bytes():
    body = json.dumps({"data": {"message": "hello"}}).encode("utf-8")
    query, _ = ec.extract_query(body)
    assert query == "hello"


def test_extract_query_accepts_memoryview():
    # proton delivers the AMQP data section as a memoryview.
    raw = json.dumps({"data": {"message": "from memoryview"}}).encode("utf-8")
    query, _ = ec.extract_query(memoryview(raw))
    assert query == "from memoryview"


def test_extract_query_bare_string_data():
    body = json.dumps({"data": "just the message"})
    query, _ = ec.extract_query(body)
    assert query == "just the message"


def test_extract_query_raw_text_fallback():
    query, envelope = ec.extract_query("plain chat text, not json")
    assert query == "plain chat text, not json"
    assert envelope == {}


def test_extract_query_empty_message_raises():
    body = json.dumps({"data": {"message": "   "}})
    with pytest.raises(ValueError):
        ec.extract_query(body)


# --------------------------------------------------------------------------- #
# build_response_event
# --------------------------------------------------------------------------- #


def test_build_response_event_shape():
    event = ec.build_response_event("the answer", "ctx-123")
    assert event["specversion"] == "1.0"
    assert event["type"] == ec.RESPONSE_EVENT_TYPE
    assert event["source"] == ec.RESPONSE_SOURCE
    assert event["datacontenttype"] == "application/json"
    assert event["data"] == {"context_id": "ctx-123", "message": "the answer"}
    assert event["id"] and event["time"]


# --------------------------------------------------------------------------- #
# publish_reply
# --------------------------------------------------------------------------- #


def test_publish_reply_sends_cloudevent():
    captured = {}

    def publisher(event_json):
        captured["json"] = event_json

    ec.publish_reply(publisher, "hello back", "ctx-9")

    payload = json.loads(captured["json"])
    assert payload["type"] == ec.RESPONSE_EVENT_TYPE
    assert payload["source"] == ec.RESPONSE_SOURCE
    assert payload["data"]["message"] == "hello back"
    assert payload["data"]["context_id"] == "ctx-9"


def test_publish_reply_skips_when_no_publisher():
    # publish=None (no response topic configured) must not raise.
    ec.publish_reply(None, "msg", "ctx")


# --------------------------------------------------------------------------- #
# process_event
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_process_event_invokes_agent_and_publishes(monkeypatch):
    invoked = {}
    published = {}

    class _FakeAgent:
        async def invoke(self, query, context_id, tools=None):
            invoked["query"] = query
            invoked["context_id"] = context_id
            invoked["tools"] = tools
            return _FakeResponse("agent answer")

    async def fake_get_mcp_tools():
        return []

    def publisher(event_json):
        published["json"] = event_json

    monkeypatch.setattr(ec, "get_mcp_tools", fake_get_mcp_tools)

    body = json.dumps({"id": "evt-42", "data": {"message": "list my requests"}})
    await ec.process_event(_FakeAgent(), [], publisher, body)

    assert invoked["query"] == "list my requests"
    # A fresh UUID context id is generated per event.
    assert invoked["context_id"] and invoked["context_id"] != "evt-42"
    payload = json.loads(published["json"])
    assert payload["data"]["message"] == "agent answer"
    assert payload["data"]["context_id"] == invoked["context_id"]


@pytest.mark.asyncio
async def test_process_event_tolerates_tool_load_failure(monkeypatch):
    published = {}

    class _FakeAgent:
        async def invoke(self, query, context_id, tools=None):
            # Tools should fall back to just the skill tools on MCP failure.
            assert tools == ["skill-tool"]
            return _FakeResponse("ok")

    async def failing_get_mcp_tools():
        raise RuntimeError("gateway down")

    def publisher(event_json):
        published["json"] = event_json

    monkeypatch.setattr(ec, "get_mcp_tools", failing_get_mcp_tools)

    body = json.dumps({"data": {"message": "hi"}})
    await ec.process_event(_FakeAgent(), ["skill-tool"], publisher, body)

    assert json.loads(published["json"])["data"]["message"] == "ok"


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #


def test_eventing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_EVENTING", raising=False)
    assert ec.eventing_enabled() is False
    monkeypatch.setenv("ENABLE_EVENTING", "0")
    assert ec.eventing_enabled() is False
    monkeypatch.setenv("ENABLE_EVENTING", "1")
    assert ec.eventing_enabled() is True


def test_amqp_url_encodes_credentials():
    config = _sample_config()
    config.amqp_user = "user@vpn"
    config.amqp_password = "p@ss:word"
    url = config.amqp_url
    assert url == "amqps://user%40vpn:p%40ss%3Aword@broker.example.com:5671"


def test_validate_reports_missing_fields():
    config = _sample_config()
    config.amqp_host = ""
    config.queue_name = ""
    problems = config.validate()
    assert any("AEM_AMQP_HOST" in p for p in problems)
    assert any("AEM_AMQP_QUEUE_NAME" in p for p in problems)
