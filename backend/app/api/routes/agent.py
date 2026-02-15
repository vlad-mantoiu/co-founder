"""Agent API routes for interacting with the AI Co-Founder."""

import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.graph import create_cofounder_graph, create_production_graph
from app.agent.state import create_initial_state
from app.core.auth import ClerkUser, require_auth
from app.memory.episodic import get_episodic_memory
from app.memory.mem0_client import get_semantic_memory

router = APIRouter()

# In-memory session storage (replace with Redis in production)
_sessions: dict[str, dict] = {}
_episode_map: dict[str, int] = {}  # session_id -> episode_id


class ChatRequest(BaseModel):
    """Request to start or continue a chat with the agent."""

    message: str
    project_id: str = "default"
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Response from the agent."""

    session_id: str
    status: str
    current_node: str
    message: str
    is_complete: bool
    needs_human_review: bool


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: ClerkUser = Depends(require_auth)):
    """Send a message to the AI Co-Founder agent.

    This endpoint handles both new conversations and continuations.
    For real-time updates, use the /chat/stream endpoint.
    """
    # Create or retrieve session
    session_id = request.session_id or str(uuid.uuid4())
    user_id = user.user_id

    episodic = get_episodic_memory()

    if session_id not in _sessions:
        # New session - create initial state
        state = create_initial_state(
            user_id=user_id,
            project_id=request.project_id,
            project_path=f"/workspace/{request.project_id}",
            goal=request.message,
        )
        _sessions[session_id] = {"state": state, "graph": create_production_graph()}

        # Start episodic memory tracking
        try:
            episode_id = await episodic.start_episode(
                user_id=user_id,
                project_id=request.project_id,
                session_id=session_id,
                goal=request.message,
            )
            _episode_map[session_id] = episode_id
        except Exception:
            pass  # Episodic memory is optional
    else:
        # Existing session - update the goal if provided
        session = _sessions[session_id]
        if request.message:
            session["state"]["current_goal"] = request.message
            session["state"]["messages"].append({
                "role": "user",
                "content": request.message,
            })

    session = _sessions[session_id]
    graph = session["graph"]
    state = session["state"]

    # Run the graph
    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await graph.ainvoke(state, config)
        session["state"] = result

        # Update episodic memory
        if session_id in _episode_map:
            try:
                await episodic.update_episode(
                    episode_id=_episode_map[session_id],
                    steps_completed=result.get("current_step_index", 0),
                    errors=result.get("active_errors"),
                    status="success" if result.get("is_complete") else "in_progress",
                    files_created=list(result.get("working_files", {}).keys()),
                )
            except Exception:
                pass

        # Store conversation in semantic memory for learning
        try:
            semantic = get_semantic_memory()
            await semantic.add(
                content=f"Task: {request.message}\nResult: {result.get('status_message')}",
                user_id=user_id,
                project_id=request.project_id,
            )
        except Exception:
            pass

        return ChatResponse(
            session_id=session_id,
            status=result.get("status_message", "Processing"),
            current_node=result.get("current_node", "unknown"),
            message=_get_last_assistant_message(result),
            is_complete=result.get("is_complete", False),
            needs_human_review=result.get("needs_human_review", False),
        )
    except Exception as e:
        # Record failure in episodic memory
        if session_id in _episode_map:
            try:
                await episodic.complete_episode(
                    episode_id=_episode_map[session_id],
                    status="failed",
                    final_error=str(e),
                )
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user: ClerkUser = Depends(require_auth)):
    """Stream agent responses in real-time.

    Returns Server-Sent Events (SSE) with status updates as the agent works.
    """
    session_id = request.session_id or str(uuid.uuid4())

    if session_id not in _sessions:
        state = create_initial_state(
            user_id=user.user_id,
            project_id=request.project_id,
            project_path=f"/tmp/cofounder/{request.project_id}",
            goal=request.message,
        )
        _sessions[session_id] = {"state": state, "graph": create_cofounder_graph()}
    else:
        session = _sessions[session_id]
        if request.message:
            session["state"]["current_goal"] = request.message
            session["state"]["messages"].append({
                "role": "user",
                "content": request.message,
            })

    async def generate_events() -> AsyncGenerator[str, None]:
        session = _sessions[session_id]
        graph = session["graph"]
        state = session["state"]
        config = {"configurable": {"thread_id": session_id}}

        try:
            async for event in graph.astream(state, config):
                # Extract node name and state from event
                for node_name, node_state in event.items():
                    # Handle cases where node_state might not be a dict
                    if isinstance(node_state, dict):
                        status = node_state.get("status_message", "Processing...")
                    else:
                        status = f"Node output: {type(node_state).__name__}"
                    yield f"data: {_format_sse_event(session_id, node_name, status)}\n\n"

            # Final state
            final_state = session["state"]
            yield f"data: {_format_sse_event(session_id, 'complete', _get_last_assistant_message(final_state))}\n\n"

        except Exception as e:
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            yield f"data: {_format_sse_event(session_id, 'error', error_details)}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/sessions/{session_id}/resume")
async def resume_session(
    session_id: str, action: str = "continue", user: ClerkUser = Depends(require_auth)
):
    """Resume a paused session (e.g., after human review).

    Args:
        session_id: The session to resume.
        action: "continue" to proceed, "abort" to cancel.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]

    if action == "abort":
        session["state"]["has_fatal_error"] = True
        session["state"]["status_message"] = "Aborted by user"
        return {"status": "aborted"}

    # Clear the human review flag and continue
    session["state"]["needs_human_review"] = False

    graph = session["graph"]
    config = {"configurable": {"thread_id": session_id}}

    result = await graph.ainvoke(session["state"], config)
    session["state"] = result

    return {
        "status": result.get("status_message"),
        "is_complete": result.get("is_complete", False),
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: ClerkUser = Depends(require_auth)):
    """Get the current state of a session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = _sessions[session_id]["state"]

    return {
        "session_id": session_id,
        "current_goal": state.get("current_goal"),
        "current_node": state.get("current_node"),
        "status_message": state.get("status_message"),
        "is_complete": state.get("is_complete"),
        "needs_human_review": state.get("needs_human_review"),
        "plan": state.get("plan"),
        "messages": state.get("messages", [])[-20:],  # Last 20 messages
    }


def _get_last_assistant_message(state: dict) -> str:
    """Get the last assistant message from state."""
    messages = state.get("messages", [])
    for msg in reversed(messages):
        # Handle both dict messages and LangChain Message objects
        if isinstance(msg, dict):
            if msg.get("role") == "assistant":
                return msg.get("content", "")
        elif hasattr(msg, "content"):
            # LangChain Message object
            return msg.content
    return state.get("status_message", "Processing...")


def _format_sse_event(session_id: str, node: str, message: str) -> str:
    """Format an SSE event as JSON."""
    import json

    return json.dumps({
        "session_id": session_id,
        "node": node,
        "message": message,
    })


@router.get("/history")
async def get_task_history(
    project_id: str | None = None,
    limit: int = 20,
    status: str | None = None,
    user: ClerkUser = Depends(require_auth),
):
    """Get task history from episodic memory.

    Args:
        project_id: Optional project filter
        limit: Maximum number of results
        status: Optional status filter (success, failed, in_progress)
    """
    user_id = user.user_id
    episodic = get_episodic_memory()

    try:
        episodes = await episodic.get_recent_episodes(
            user_id=user_id,
            project_id=project_id,
            limit=limit,
            status=status,
        )
        return {"episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/errors")
async def get_error_patterns(
    project_id: str | None = None, user: ClerkUser = Depends(require_auth)
):
    """Get common error patterns from failed tasks.

    Args:
        project_id: Optional project filter
    """
    user_id = user.user_id
    episodic = get_episodic_memory()

    try:
        patterns = await episodic.get_error_patterns(
            user_id=user_id,
            project_id=project_id,
        )
        return {"error_patterns": patterns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories")
async def get_user_memories(
    project_id: str | None = None, user: ClerkUser = Depends(require_auth)
):
    """Get stored memories/preferences for the user.

    Args:
        project_id: Optional project filter
    """
    user_id = user.user_id
    semantic = get_semantic_memory()

    try:
        memories = await semantic.get_all(
            user_id=user_id,
            project_id=project_id,
        )
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
