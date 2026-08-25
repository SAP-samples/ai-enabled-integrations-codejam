import logging
import os

from a2a.server.agent_execution import AgentExecutor as A2AAgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import new_agent_text_message, new_task
from a2a.utils.errors import ServerError

from agent import SampleAgent
from load_skill_resources import get_load_skill_resource_tool
from mcp_tools import get_mcp_tools, get_user_token, set_user_token, reset_user_token

logger = logging.getLogger(__name__)


class AgentExecutor(A2AAgentExecutor):
    def __init__(self):
        self.agent = SampleAgent()
        self.skill_tools = get_load_skill_resource_tool()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent and stream results back via A2A protocol.

        Discovers and loads MCP tools from Agent Gateway before each execution.
        Tools are fetched per-request since both listing and calling require user credentials.

        Args:
            context: Request context containing user input and task info
            event_queue: Queue for publishing task status updates

        Raises:
            ServerError: On unrecoverable agent execution errors
        """
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        # Get user token from context variable (set by middleware)
        user_token = get_user_token()

        # Load MCP tools (handles both production and local testing modes internally)
        tools = []
        try:
            tools = await get_mcp_tools()
            if not tools:
                logger.warning("No tools returned from Agent Gateway")
            else:
                tool_names = [t.name for t in tools]
                logger.info("Loaded %d MCP tool(s) for agent execution: %s", len(tools), tool_names)
        except ValueError as e:
            # User token validation error
            logger.error(f"Invalid user token: {e}")
        except Exception as e:
            # Network, AGW, or other infrastructure errors
            logger.error(f"Failed to load tools from Agent Gateway: {e}")

        tools = [*tools, *self.skill_tools]

        updater = TaskUpdater(event_queue, task.id, task.context_id)

        try:
            async for item in self.agent.stream(query, task.context_id, tools=tools):
                is_task_complete = item["is_task_complete"]
                require_user_input = item["require_user_input"]
                content = item["content"]

                if require_user_input:
                    # Agent requests more input
                    await updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(content, task.context_id, task.id),
                        final=True,
                    )
                    break
                elif is_task_complete:
                    # Completed: add artifact and complete task
                    await updater.add_artifact(
                        [Part(root=TextPart(text=content))], name="agent_result"
                    )
                    await updater.complete()
                    break
                else:
                    # Working status update
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(content, task.context_id, task.id),
                    )
        except Exception as e:
            logger.exception("Agent execution error")
            raise ServerError(error=InternalError()) from e

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise ServerError(error=UnsupportedOperationError())
