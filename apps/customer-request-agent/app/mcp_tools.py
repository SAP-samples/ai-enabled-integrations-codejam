"""MCP tool loader.

Owned indirection layer between agent code and the Agent Gateway.
All agent code imports get_mcp_tools from here.

Behaviour is controlled by the IBD_TESTING environment variable:

  Production (IBD_TESTING not set):
      Connects directly to configured external MCP servers via HTTP using the
      mcp library's streamablehttp_client.  Servers are configured via env vars:
        CUSTOMER_REQUEST_MCP_URL       (default: https://altura-cs-srv.cfapps.eu20-002.hana.ondemand.com/mcp/support-agent)
        SERVICE_LOCATOR_MCP_SERVER_URL          (default: https://ai-integrations-codeja-5fa04ad0219049fd997c44a4cb0ab171.a.integration.cloud.sap/service-locator-mcp-000)
        SERVICE_LOCATOR_MCP_OAUTH_TOKEN_URL     OAuth token endpoint for the second MCP server
        SERVICE_LOCATOR_MCP_OAUTH_CLIENT_ID     OAuth client ID for the second MCP server
        SERVICE_LOCATOR_MCP_OAUTH_CLIENT_SECRET OAuth client secret for the second MCP server

  Local / test mode (IBD_TESTING=1):
      Reads mcp-mock.json from the directory containing this file's parent
      (i.e. <asset-root>/mcp-mock.json) and returns LangChain StructuredTool
      instances built from the mock data — no network calls.
"""

import base64
import json
import logging
import os
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any, Optional

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import Field, create_model
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

# Context variable to pass user token from request to tool execution
_user_token_context: ContextVar[str | None] = ContextVar('user_token', default=None)

# mcp-mock.json lives at the asset root (one level above app/)
_MOCK_FILE = Path(__file__).parent.parent / "mcp-mock.json"

# External MCP server URLs — driven by environment variables so no code
# changes are needed when URLs change or the second server is activated.
_CUSTOMER_REQUEST_MCP_URL = os.environ.get(
    "CUSTOMER_REQUEST_MCP_URL",
    "https://customer-request-mcp.not.configured",
)
# Second MCP server — uses OAuth client credentials.
_SERVICE_LOCATOR_MCP_SERVER_URL = os.environ.get(
    "SERVICE_LOCATOR_MCP_SERVER_URL",
    "https://service-locator-mcp.not.configured/service-locator-mcp-###",
)
_SERVICE_LOCATOR_MCP_OAUTH_TOKEN_URL = os.environ.get("SERVICE_LOCATOR_MCP_OAUTH_TOKEN_URL", "")
_SERVICE_LOCATOR_MCP_OAUTH_CLIENT_ID = os.environ.get("SERVICE_LOCATOR_MCP_OAUTH_CLIENT_ID", "")
_SERVICE_LOCATOR_MCP_OAUTH_CLIENT_SECRET = os.environ.get("SERVICE_LOCATOR_MCP_OAUTH_CLIENT_SECRET", "")

_MCP_SERVERS: list[dict] = [
    {"name": "customer-request-mcp", "url": _CUSTOMER_REQUEST_MCP_URL, "active": bool(_CUSTOMER_REQUEST_MCP_URL)},
    {
        "name": "service-locator-mcp-server",
        "url": _SERVICE_LOCATOR_MCP_SERVER_URL,
        "active": bool(_SERVICE_LOCATOR_MCP_SERVER_URL),
        "oauth": {
            "token_url": _SERVICE_LOCATOR_MCP_OAUTH_TOKEN_URL,
            "client_id": _SERVICE_LOCATOR_MCP_OAUTH_CLIENT_ID,
            "client_secret": _SERVICE_LOCATOR_MCP_OAUTH_CLIENT_SECRET,
        },
    },
]


def _build_mock_tools() -> list:
    """Build LangChain StructuredTool instances from mcp-mock.json.

    Returns an empty list (without error) when mcp-mock.json is absent or
    cannot be parsed — add/fix the file to enable tool mocking.
    """
    if not _MOCK_FILE.exists():
        return []

    try:
        mock_data = json.loads(_MOCK_FILE.read_text())
    except Exception:
        logger.warning(
            "Failed to parse mcp-mock.json at %s — returning empty tool list",
            _MOCK_FILE,
            exc_info=True,
        )
        return []

    tools = []

    from langchain_core.tools import StructuredTool
    from pydantic import Field, create_model

    for _server_slug, server in mock_data.get("servers", {}).items():
        for tool_name, tool_def in server.get("tools", {}).items():
            description = tool_def.get("description", "")
            mock_response = tool_def.get("mock_response", {})
            input_schema = tool_def.get("input_schema", {})

            props = input_schema.get("properties", {})
            required_fields = set(input_schema.get("required", []))
            field_definitions: dict = {}
            for field_name, field_info in props.items():
                json_type = field_info.get("type", "string")
                if json_type == "integer":
                    python_type = int
                elif json_type == "number":
                    python_type = float
                elif json_type == "boolean":
                    python_type = bool
                elif json_type == "decimal":
                    python_type = float
                else:
                    python_type = str

                if field_name in required_fields:
                    field_definitions[field_name] = (
                        python_type,
                        Field(description=field_info.get("description", "")),
                    )
                else:
                    field_definitions[field_name] = (
                        python_type,
                        Field(
                            default=None, description=field_info.get("description", "")
                        ),
                    )

            args_schema = (
                create_model(f"{tool_name}_args", **field_definitions)
                if field_definitions
                else create_model(f"{tool_name}_args")
            )
            _response = json.dumps(mock_response)

            async def _coroutine(_resp=_response, **kwargs) -> str:
                return _resp

            tools.append(
                StructuredTool(
                    name=tool_name,
                    description=description,
                    args_schema=args_schema,
                    coroutine=_coroutine,
                    # Catch ToolException and forward it to the LLM as an error
                    # message rather than propagating as a Python exception.
                    handle_tool_error=True,
                )
            )

    logger.info("Loaded %d mock MCP tool(s) from %s", len(tools), _MOCK_FILE)
    return tools


async def _fetch_oauth_token(token_url: str, client_id: str, client_secret: str) -> str:
    """Fetch an OAuth2 client credentials access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        return response.json()["access_token"]


def _mcp_tool_to_langchain(server_name: str, tool: Any, server_url: str, oauth_cfg: dict | None = None) -> StructuredTool:
    """Wrap a single MCP tool as a LangChain StructuredTool.

    Opens a fresh MCP session per invocation so the session is never reused
    after its context manager has exited.
    """
    import re
    raw_name = f"{server_name}__{tool.name}"
    safe_name = re.sub(r"[^a-zA-Z0-9\-_]", "_", raw_name)[:64]

    props = (tool.inputSchema or {}).get("properties", {})
    required_fields = set((tool.inputSchema or {}).get("required", []))
    logger.debug("props=%s, required=%s", props, required_fields)
    fields: dict = {}
    for fname, finfo in props.items():
        
        jtype = finfo.get("type", "string")

        ptype = {"integer": int, "number": float, "decimal": float, "boolean": bool, "object": object}.get(jtype, str)
        fdesc = finfo.get("description", "")

        logger.debug("fname=%s, finfo=%s, jtype=%s, ptype=%s", fname, finfo, jtype, ptype)
        if fname in required_fields:
            fields[fname] = (ptype, Field(description=fdesc))
        else:
            fields[fname] = (ptype, Field(default=None, description=fdesc))

    args_schema = create_model(f"{safe_name}_args", **fields) if fields else None
    description = f"[{server_name}] {tool.description or ''}"

    logger.debug("args_schema=%s, description=%s", args_schema, description)

    async def _run(_url=server_url, _tool_name=tool.name, _oauth=oauth_cfg, **kwargs: Any) -> str:
        headers: dict = {}
        if _oauth and _oauth.get("token_url") and _oauth.get("client_id") and _oauth.get("client_secret"):
            token = await _fetch_oauth_token(_oauth["token_url"], _oauth["client_id"], _oauth["client_secret"])
            headers["Authorization"] = f"Bearer {token}"
        async with streamablehttp_client(_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(_tool_name, arguments=kwargs)
        parts = getattr(result, "content", []) or []
        return " ".join(
            getattr(p, "text", str(p)) for p in parts
        ) if parts else str(result)

    return StructuredTool(
        name=safe_name,
        description=description,
        args_schema=args_schema,
        coroutine=_run,
        handle_tool_error=True,
    )


async def _load_tools_from_server(server: dict) -> list:
    """Connect to one HTTP MCP server, list its tools, return LangChain wrappers."""
    url = server["url"]
    name = server["name"]
    oauth_cfg = server.get("oauth")
    headers: dict = {}

    if oauth_cfg and oauth_cfg.get("token_url") and oauth_cfg.get("client_id") and oauth_cfg.get("client_secret"):
        try:
            token = await _fetch_oauth_token(oauth_cfg["token_url"], oauth_cfg["client_id"], oauth_cfg["client_secret"])
            headers["Authorization"] = f"Bearer {token}"
        except Exception:
            logger.exception("Failed to fetch OAuth token for MCP server '%s'", name)
            return []

    tools: list = []
    try:
        async with streamablehttp_client(url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for tool in result.tools:
                    logger.info("Found tool '%s' on MCP server '%s'", tool, name)
                    tools.append(_mcp_tool_to_langchain(name, tool, url, oauth_cfg=oauth_cfg))
                logger.info("Loaded %d tool(s) from MCP server '%s'", len(tools), name)
    except Exception:
        logger.exception("Failed to load tools from MCP server '%s' at %s", name, url)
    return tools


async def get_mcp_tools(user_token: str | None = None) -> list:
    """Return LangChain-compatible MCP tools.

    In local/test mode (IBD_TESTING=1): returns mock tools from mcp-mock.json.
    In production: connects directly to each active external MCP server via HTTP.
      - CUSTOMER_REQUEST_MCP_URL (no auth, always active)
      - SERVICE_LOCATOR_MCP_SERVER_URL    (inactive until env var is set)
    """
    if os.environ.get("IBD_TESTING") == "1" and os.environ.get("INVOKE_LIVE_MCP", "0") != "1":
        return _build_mock_tools()
    else:
        logger.info("Loading MCP tools from active external servers (IBD_TESTING=%s, INVOKE_LIVE_MCP=%s)", os.environ.get("IBD_TESTING"), os.environ.get("INVOKE_LIVE_MCP", "0"))

    all_tools: list = []
    for server in _MCP_SERVERS:
        if not server["active"]:
            logger.debug("MCP server '%s' is inactive (URL not set), skipping", server["name"])
            continue
        server_tools = await _load_tools_from_server(server)
        all_tools.extend(server_tools)

    logger.info("Total MCP tools loaded: %d", len(all_tools))
    return all_tools

def set_user_token(user_token: str | None) -> Token:
    """Set the user token for MCP tool calls in the current async context.

    This must be called before invoking any tools to ensure they use the correct
    user credentials. The token is stored in a context variable that is automatically
    isolated per async task/request.

    IMPORTANT: Always reset the token after use to prevent cross-request contamination:
        token_ctx = set_user_token(user_token)
        try:
            # ... use tools ...
        finally:
            reset_user_token(token_ctx)

    Args:
        user_token: The user's authentication token, or None to clear it

    Returns:
        Token object that must be passed to reset_user_token() to restore
        the previous value
    """
    if user_token:
        logger.debug("User token set for tool execution")
    else:
        logger.debug("User token cleared for tool execution")
    return _user_token_context.set(user_token)


def reset_user_token(token: Token) -> None:
    """Restore the user token context to its previous value.

    Args:
        token: The Token returned by a prior set_user_token() call. Passing it to
            ContextVar.reset() unwinds the context stack to the value that was in
            effect before that set_user_token() call, rather than leaving a stale
            or None value behind.
    """
    _user_token_context.reset(token)
    logger.debug("User token context reset to previous value")


def get_user_token() -> str | None:
    """Get the current user token from the async context.

    Returns:
        The user token string, or None if not set
    """
    return _user_token_context.get()


def get_user_sub() -> str:
    """Extract the JWT subject claim from the current request's token.

    Decodes the JWT payload (middle segment) without verifying the signature —
    The platform has already verified it before the request reaches this code.

    Returns:
        The 'sub' claim from the token.

    Raises:
        ValueError: If the token is missing or the sub claim cannot be extracted,
                    unless IBD_TESTING=1, in which case returns 'unknown'.
    """
    token = _user_token_context.get()
    if not token:
        if os.environ.get("IBD_TESTING") == "1":
            return "unknown"
        raise ValueError("No user token in context — cannot extract sub claim")

    try:
        payload_segment = token.split(".")[1]
        # Add padding if needed
        padding = 4 - len(payload_segment) % 4
        if padding != 4:
            payload_segment += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_segment))
        sub = payload.get("sub")
        if not sub:
            raise ValueError("JWT payload contains no 'sub' claim")
        return sub
    except (IndexError, ValueError):
        raise
    except Exception as e:
        raise ValueError(f"Failed to decode JWT payload: {e}") from e
