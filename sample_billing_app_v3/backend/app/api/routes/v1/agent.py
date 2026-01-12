"""AI Agent WebSocket routes with streaming support (CrewAI Multi-Agent)."""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.crewai_assistant import CrewContext, get_crew
from app.api.deps import get_conversation_service
from app.db.session import get_db_context
from app.schemas.conversation import ConversationCreate, MessageCreate

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentConnectionManager:
    """WebSocket connection manager for AI agent."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Agent WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            f"Agent WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_event(self, websocket: WebSocket, event_type: str, data: Any) -> bool:
        """Send a JSON event to a specific WebSocket client.

        Returns True if sent successfully, False if connection is closed.
        """
        try:
            await websocket.send_json({"type": event_type, "data": data})
            return True
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed
            return False


manager = AgentConnectionManager()


@router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
) -> None:
    """WebSocket endpoint for CrewAI multi-agent with streaming support.

    Uses CrewAI to stream crew execution events including:
    - user_prompt: When user input is received
    - task_start: When a task begins execution
    - agent_action: When an agent takes an action
    - task_complete: When a task finishes
    - crew_complete: When all tasks are done
    - final_result: When the final result is ready
    - complete: When processing is complete
    - error: When an error occurs

    Expected input message format:
    {
        "message": "user message here",
        "history": [{"role": "user|assistant|system", "content": "..."}],
        "conversation_id": "optional-uuid-to-continue-existing-conversation"
    }

    Persistence: Set 'conversation_id' to continue an existing conversation.
    If not provided, a new conversation is created. The conversation_id is
    returned in the 'conversation_created' event.
    """

    await manager.connect(websocket)

    # Conversation state per connection
    conversation_history: list[dict[str, str]] = []
    context: CrewContext = {}
    current_conversation_id: str | None = None

    try:
        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            # Optionally accept history from client (or use server-side tracking)
            if "history" in data:
                conversation_history = data["history"]

            if not user_message:
                await manager.send_event(websocket, "error", {"message": "Empty message"})
                continue
            prompt_tokens_estimate = None
            billing_model_name = None

            # Handle conversation persistence
            try:
                async with get_db_context() as db:
                    conv_service = get_conversation_service(db)

                    # Get or create conversation
                    requested_conv_id = data.get("conversation_id")
                    if requested_conv_id:
                        current_conversation_id = requested_conv_id
                        # Verify conversation exists
                        await conv_service.get_conversation(UUID(requested_conv_id))
                    elif not current_conversation_id:
                        # Create new conversation
                        conv_data = ConversationCreate(
                            title=user_message[:50] if len(user_message) > 50 else user_message,
                        )
                        conversation = await conv_service.create_conversation(conv_data)
                        current_conversation_id = str(conversation.id)
                        await manager.send_event(
                            websocket,
                            "conversation_created",
                            {"conversation_id": current_conversation_id},
                        )

                    # Save user message
                    await conv_service.add_message(
                        UUID(current_conversation_id),
                        MessageCreate(role="user", content=user_message),
                    )
            except Exception as e:
                logger.warning(f"Failed to persist conversation: {e}")
                # Continue without persistence

            await manager.send_event(websocket, "user_prompt", {"content": user_message})

            try:
                crew_assistant = get_crew()

                final_output = ""

                await manager.send_event(
                    websocket,
                    "crew_start",
                    {
                        "crew_name": crew_assistant.config.name,
                        "process": crew_assistant.config.process,
                    },
                )

                # Stream crew execution events
                async for event in crew_assistant.stream(
                    user_message,
                    history=conversation_history,
                    context=context,
                ):
                    event_type = event.get("type", "unknown")

                    # Crew lifecycle events
                    if event_type == "crew_started":
                        await manager.send_event(
                            websocket,
                            "crew_started",
                            {
                                "crew_name": event.get("crew_name", ""),
                                "crew_id": event.get("crew_id", ""),
                            },
                        )

                    # Agent events
                    elif event_type == "agent_started":
                        await manager.send_event(
                            websocket,
                            "agent_started",
                            {
                                "agent": event.get("agent", ""),
                                "task": event.get("task", ""),
                            },
                        )

                    elif event_type == "agent_completed":
                        agent_name = event.get("agent", "")
                        agent_output = event.get("output", "")
                        await manager.send_event(
                            websocket,
                            "agent_completed",
                            {
                                "agent": agent_name,
                                "output": agent_output,
                            },
                        )
                        # Save agent's output as a separate message
                        if current_conversation_id and agent_output:
                            try:
                                async with get_db_context() as db:
                                    conv_service = get_conversation_service(db)
                                    await conv_service.add_message(
                                        UUID(current_conversation_id),
                                        MessageCreate(
                                            role="assistant",
                                            content=f"✅ **{agent_name}**\n\n{agent_output}",
                                        ),
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to persist agent response: {e}")

                    # Task events
                    elif event_type == "task_started":
                        await manager.send_event(
                            websocket,
                            "task_started",
                            {
                                "task_id": event.get("task_id", ""),
                                "description": event.get("description", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    elif event_type == "task_completed":
                        await manager.send_event(
                            websocket,
                            "task_completed",
                            {
                                "task_id": event.get("task_id", ""),
                                "output": event.get("output", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    # Tool events
                    elif event_type == "tool_started":
                        await manager.send_event(
                            websocket,
                            "tool_started",
                            {
                                "tool_name": event.get("tool_name", ""),
                                "tool_args": event.get("tool_args", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    elif event_type == "tool_finished":
                        await manager.send_event(
                            websocket,
                            "tool_finished",
                            {
                                "tool_name": event.get("tool_name", ""),
                                "tool_result": event.get("tool_result", ""),
                                "agent": event.get("agent", ""),
                            },
                        )

                    # LLM events
                    elif event_type == "llm_started":
                        await manager.send_event(
                            websocket,
                            "llm_started",
                            {
                                "agent": event.get("agent", ""),
                            },
                        )

                    elif event_type == "llm_completed":
                        await manager.send_event(
                            websocket,
                            "llm_completed",
                            {
                                "agent": event.get("agent", ""),
                                "response": event.get("response", ""),
                            },
                        )

                    # Final result
                    elif event_type == "crew_complete":
                        final_output = event.get("result", "")
                        await manager.send_event(
                            websocket,
                            "final_result",
                            {"output": final_output},
                        )

                    # Error
                    elif event_type == "error":
                        await manager.send_event(
                            websocket,
                            "error",
                            {"message": event.get("error", "Unknown error")},
                        )

                # Update conversation history
                conversation_history.append({"role": "user", "content": user_message})
                if final_output:
                    conversation_history.append({"role": "assistant", "content": final_output})
                # Note: Agent outputs are saved individually in agent_completed events above

                await manager.send_event(
                    websocket,
                    "complete",
                    {
                        "conversation_id": current_conversation_id,
                    },
                )

            except WebSocketDisconnect:
                # Client disconnected during processing - this is normal
                logger.info("Client disconnected during agent processing")
                break
            except Exception as e:
                logger.exception(f"Error processing agent request: {e}")
                # Try to send error, but don't fail if connection is closed
                await manager.send_event(websocket, "error", {"message": str(e)})

    except WebSocketDisconnect:
        pass  # Normal disconnect
    finally:
        manager.disconnect(websocket)
