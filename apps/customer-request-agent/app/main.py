# CRITICAL: Initialize telemetry BEFORE importing AI frameworks
from sap_cloud_sdk.aicore import set_aicore_config
from sap_cloud_sdk.core.telemetry import auto_instrument

set_aicore_config()
auto_instrument()

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from agent_executor import AgentExecutor
from mcp_tools import reset_user_token, set_user_token
from ui import INDEX_HTML
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "5678"))


class JWTContextMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts JWT token from Authorization header and sets it in context."""

    async def dispatch(self, request, call_next):
        # Extract JWT token from Authorization header
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

        # Set the token in the context variable, capturing the reset token
        token_ctx = set_user_token(token)

        try:
            response = await call_next(request)
            return response
        finally:
            # Restore the previous context value to prevent cross-request leakage
            reset_user_token(token_ctx)


@click.command()
@click.option("--host", default=HOST)
@click.option("--port", default=PORT)
def main(host: str, port: int):
    skill = AgentSkill(
        id="customer-request-agent",
        name="customer-request-agent",
        description="An AI agent that autonomously handles customer requests via MCP-exposed tools",
        tags=["customer", "request", "agent"],
        examples=["How do I check the status of my request?", "I need help with my service ticket"],
    )

    # url=os.environ.get("AGENT_PUBLIC_URL", f"http://host.containers.internal:{port}/"),
    logger.info(f"Agent modified name: customer-request-agent")

    agent_card = AgentCard(
        name="customer-request-agent",
        description="An AI agent that autonomously handles customer requests via MCP-exposed tools",
        url=f"http://host.containers.internal:{port}/",
        version="1.0.0",
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        skills=[skill],
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=DefaultRequestHandler(
            agent_executor=AgentExecutor(),
            task_store=InMemoryTaskStore(),
        ),
    )
    app = server.build()

    #########
    # Serve a minimal built-in web UI at GET /ui (POST / is the JSON-RPC endpoint).
    img_dir = Path(__file__).parent / "img"
    app.mount("/img", StaticFiles(directory=str(img_dir)), name="img")

    async def ui(request):
        return HTMLResponse(INDEX_HTML)

    app.routes.append(Route("/ui", ui, methods=["GET"], name="ui"))
    #########

    # Add JWT context middleware
    app.add_middleware(JWTContextMiddleware)

    StarletteInstrumentor().instrument_app(app)

    logger.info(f"Starting A2A server at http://{host}:{port}")
    logger.info(f"Web UI available at http://{host}:{port}/ui")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
