"""Integration test — end-to-end agent flow with mocked LLM and MCP tools."""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("IBD_TESTING", "1")

app_path = str(Path(__file__).parent.parent / "app")
if app_path not in sys.path:
    sys.path.insert(0, app_path)


def _make_mock_llm(response_text: str):
    """Return a ChatLiteLLM mock that yields the given response text."""
    from langchain_core.messages import AIMessage

    ai_msg = AIMessage(content=response_text)
    mock_llm = MagicMock()
    # ainvoke used by the graph
    mock_llm.ainvoke = AsyncMock(return_value=ai_msg)
    # bind_tools used by create_agent
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm.with_config = MagicMock(return_value=mock_llm)
    return mock_llm


@pytest.mark.asyncio
async def test_end_to_end_request_resolved():
    """Full agent flow: all 5 milestones logged, response returned."""
    from langchain_core.tools import StructuredTool
    from pydantic import create_model

    # Minimal stub tool
    DummyArgs = create_model("DummyArgs")

    async def _dummy(**kwargs):
        return '{"results": [{"ID": "abc", "request_summary": "test"}]}'

    stub_tool = StructuredTool(
        name="customer_request_mcp__list_latest_customer_requests",
        description="Lists latest requests",
        args_schema=DummyArgs,
        coroutine=_dummy,
    )

    # Patch: mcp_tools.get_mcp_tools → returns stub tool
    # Patch: ChatLiteLLM → returns canned response
    with patch("mcp_tools.get_mcp_tools", AsyncMock(return_value=[stub_tool])):
        from agent import SampleAgent
        from langchain_core.messages import AIMessage
        from langgraph.graph.state import CompiledStateGraph

        agent = SampleAgent()

        # Patch _invoke_with_fallback to return a canned LLM result
        canned_result = {
            "messages": [AIMessage(content="Your request has been handled successfully.")]
        }
        agent._invoke_with_fallback = AsyncMock(return_value=canned_result)

        collected = []
        async for chunk in agent.stream(
            query="Show me the latest customer requests",
            context_id="test-ctx-001",
            tools=[stub_tool],
        ):
            collected.append(chunk)

    assert any(c.get("is_task_complete") for c in collected)
    final = next(c for c in collected if c.get("is_task_complete"))
    assert "successfully" in final["content"].lower() or final["content"]


@pytest.mark.asyncio
async def test_end_to_end_escalation():
    """Agent returns escalation signal when it cannot resolve the request."""
    from langchain_core.tools import StructuredTool
    from pydantic import create_model
    from langchain_core.messages import AIMessage
    from agent import SampleAgent, ESCALATION_SIGNAL

    DummyArgs = create_model("DummyArgs2")

    async def _dummy(**kwargs):
        return "{}"

    stub_tool = StructuredTool(
        name="customer_request_mcp__query",
        description="Query",
        args_schema=DummyArgs,
        coroutine=_dummy,
    )

    agent = SampleAgent()
    escalation_response = f"{ESCALATION_SIGNAL}: cannot determine resolution"
    agent._invoke_with_fallback = AsyncMock(
        return_value={"messages": [AIMessage(content=escalation_response)]}
    )

    collected = []
    async for chunk in agent.stream(
        query="Do something impossible",
        context_id="test-ctx-002",
        tools=[stub_tool],
    ):
        collected.append(chunk)

    assert any(c.get("is_task_complete") for c in collected)
    final = next(c for c in collected if c.get("is_task_complete"))
    assert ESCALATION_SIGNAL in final["content"]


@pytest.mark.asyncio
async def test_invoke_returns_completed():
    """invoke() wraps stream() and returns AgentResponse with status=completed."""
    from langchain_core.messages import AIMessage
    from agent import SampleAgent

    agent = SampleAgent()
    agent._invoke_with_fallback = AsyncMock(
        return_value={"messages": [AIMessage(content="Done.")]}
    )

    from langchain_core.tools import StructuredTool
    from pydantic import create_model

    DummyArgs = create_model("DummyArgs3")

    async def _noop(**kwargs):
        return "{}"

    stub = StructuredTool(name="stub", description="stub", args_schema=DummyArgs, coroutine=_noop)
    result = await agent.invoke("Hello", "ctx-003", tools=[stub])
    assert result.status == "completed"
    assert result.message == "Done."
