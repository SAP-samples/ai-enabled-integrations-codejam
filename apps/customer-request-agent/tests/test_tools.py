"""Unit tests for MCP tools — one test per tool."""

import json
import os
import pytest

os.environ.setdefault("IBD_TESTING", "1")


@pytest.fixture
def mock_tools(tmp_path, monkeypatch):
    """Load tools from mcp-mock.json via the real _build_mock_tools path."""
    import sys
    app_path = str(
        __import__("pathlib").Path(__file__).parent.parent / "app"
    )
    if app_path not in sys.path:
        sys.path.insert(0, app_path)

    mock_file = __import__("pathlib").Path(__file__).parent.parent / "mcp-mock.json"
    import mcp_tools
    monkeypatch.setattr(mcp_tools, "_MOCK_FILE", mock_file)
    return mcp_tools._build_mock_tools()


def _find_tool(tools, name_fragment):
    for t in tools:
        if name_fragment in t.name:
            return t
    return None


@pytest.mark.asyncio
async def test_tool_query(mock_tools):
    tool = _find_tool(mock_tools, "query")
    assert tool is not None, "query tool not found"
    result = await tool.coroutine(entity="CustomerRequests")
    data = json.loads(result)
    assert "results" in data
    assert len(data["results"]) >= 1
    first = data["results"][0]
    assert "ID" in first
    assert "customer_id" in first


@pytest.mark.asyncio
async def test_tool_list_latest_customer_requests(mock_tools):
    tool = _find_tool(mock_tools, "list_latest")
    assert tool is not None, "list_latest_customer_requests tool not found"
    result = await tool.coroutine()
    data = json.loads(result)
    assert "results" in data
    assert len(data["results"]) >= 1
    first = data["results"][0]
    assert "urgency" in first
    assert "request_summary" in first


@pytest.mark.asyncio
async def test_tool_get_customer_requests(mock_tools):
    tool = _find_tool(mock_tools, "get_customer_requests")
    assert tool is not None, "get_customer_requests tool not found"
    result = await tool.coroutine(customer_id="CUST-001")
    data = json.loads(result)
    assert "results" in data
    assert data["results"][0]["customer_id"] == "CUST-001"


@pytest.mark.asyncio
async def test_tool_describe(mock_tools):
    tool = _find_tool(mock_tools, "describe")
    assert tool is not None, "describe tool not found"
    result = await tool.coroutine()
    data = json.loads(result)
    assert "entities" in data
    assert "CustomerRequests" in data["entities"]
