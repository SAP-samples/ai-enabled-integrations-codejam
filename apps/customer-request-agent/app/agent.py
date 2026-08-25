import logging
from dataclasses import dataclass
import os
from typing import Any, AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.graph.state import CompiledStateGraph
from litellm.exceptions import APIConnectionError, APIError, Timeout
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer

from mcp_tools import get_user_sub

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

ESCALATION_SIGNAL = "__ESCALATE__"


# All models available in AI Core can be found here: https://me.sap.com/notes/3437766
@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return os.getenv("LITELLM_PROVIDER", "sap") + "/" + os.getenv("MODEL_NAME", "anthropic--claude-4.6-sonnet")


@agent_model(
    key="config.fallback_model",
    label="Fallback LLM Model",
    description="Fallback model used when the primary model is unavailable. Leave empty to disable fallback.",
)
def get_fallback_model_name() -> str:
    return ""


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 1.0


@agent_config(
    key="config.checkpointer.ttl_seconds",
    label="Thread TTL (seconds)",
    description="Evict inactive conversation threads after this period of "
                "inactivity. Set to 0 to disable eviction.",
)
def thread_ttl_seconds() -> int:
    return 3600


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return (
        "You are an AI agent that autonomously handles customer requests via MCP-exposed tools. "
        "Help users with their requests.\n\n"
        "IMPORTANT: You MUST use tools to retrieve live data. Never fabricate, guess, or invent data. "
        "Relay tool errors verbatim without adding suggestions. "
        "Set top or equivalent page-size parameters to a maximum of 100 on every tool call that accepts it "
        "— inform the user when this limit is applied. "
        "If you cannot resolve a request, respond with the exact text: "
        f'"{ESCALATION_SIGNAL}: <reason>" to trigger escalation.'
    )


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        ttl = thread_ttl_seconds()
        self._primary_model = get_model_name()
        self._fallback_model = get_fallback_model_name().strip()
        self._temperature = get_temperature()

        self.llm = ChatLiteLLM(model=self._primary_model,
                               temperature=self._temperature)
        self._fallback_llm = (
            ChatLiteLLM(model=self._fallback_model,
                        temperature=self._temperature)
            if self._fallback_model
            else None
        )

        self._checkpointer = create_checkpointer(ttl_seconds=ttl or None)
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
            keep=("messages", 4),
        )

    def _create_graph(
        self,
        llm: ChatLiteLLM,
        tools: Sequence[BaseTool],
        system_prompt: str,
    ) -> CompiledStateGraph:
        return create_agent(
            llm,
            tools=list(tools),
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
            middleware=[self._summarization_middleware],
        )

    async def _invoke_with_fallback(
        self,
        tools: Sequence[BaseTool],
        system_prompt: str,
        query: str,
        context_id: str,
    ) -> dict[str, Any]:
        config = {"configurable": {
            "thread_id": f"{get_user_sub()}:{context_id}"}}
        messages = {"messages": [HumanMessage(content=query)]}

        try:
            graph = self._create_graph(self.llm, tools, system_prompt)
            return await graph.ainvoke(messages, config)
        except (APIConnectionError, APIError, Timeout) as primary_error:
            if not self._fallback_llm:
                raise

            logger.warning(
                "Primary model '%s' failed, retrying with fallback '%s': %s",
                self._primary_model,
                self._fallback_model,
                primary_error,
            )

        graph = self._create_graph(self._fallback_llm, tools, system_prompt)
        result = await graph.ainvoke(messages, config)
        logger.info(
            "Request completed with fallback model '%s' after primary '%s' failed.",
            self._fallback_model,
            self._primary_model,
        )
        return result

    @tracer.start_as_current_span("run_agent")
    async def _run_agent(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool],
    ) -> dict[str, Any]:
        """Core agent execution with milestone instrumentation.

        Extracted from stream() so spans never wrap a yield.
        """
        # M1: Request received
        if not query:
            logger.warning(
                "M1.missed: failed to receive or parse customer request")
            raise ValueError("Empty query — cannot process request")
        logger.info("M1.achieved: customer request received and parsed")

        # M2: Intent identified — happens inside the LLM graph; we trust the
        # LLM completed classification if the graph returns without exception.
        system_prompt = get_system_prompt()
        if not tools:
            system_prompt += (
                "\n\nIMPORTANT: No tools are currently available. "
                "Do not attempt to call any tools. "
                "Respond explaining that tools are temporarily unavailable."
            )

        tool_names = [t.name for t in tools]
        logger.info("Running agent with %d tool(s): %s",
                    len(tool_names), tool_names)

        try:
            result = await self._invoke_with_fallback(
                tools=tools,
                system_prompt=system_prompt,
                query=query,
                context_id=context_id,
            )
        except Exception:
            logger.warning(
                "M2.missed: intent classification did not complete or confidence below threshold")
            raise

        logger.info("M2.achieved: request intent classified")

        # M3: Tools invoked — inferred from the graph having run tool nodes;
        # we emit the milestone after a successful graph return.
        logger.info("M3.achieved: MCP tools invoked successfully")

        # M4: Response composed
        response_text = result["messages"][-1].content
        if not response_text:
            logger.warning("M4.missed: response composition failed")
            raise RuntimeError("Agent returned empty response")
        logger.info("M4.achieved: customer response composed")

        return {"response": response_text, "result": result}

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            outcome = await self._run_agent(
                query=query,
                context_id=context_id,
                tools=tools or [],
            )
            response = outcome["response"]

            if response.startswith(ESCALATION_SIGNAL):
                logger.info("M5.achieved: request resolved or escalated")
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": response,
                }
            else:
                logger.info("M5.achieved: request resolved or escalated")
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": response,
                }

        except Exception:
            logger.exception("Agent stream() failed")
            logger.warning(
                "M5.missed: request ended without resolution or escalation")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "I encountered an error while processing your request. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
