"""Agent API routes for interacting with the AI Co-Founder."""

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.graph import create_cofounder_graph, create_production_graph
from app.agent.state import create_initial_state
from app.core.auth import ClerkUser, require_auth, require_subscription
from app.core.llm_config import get_or_create_user_settings
from app.db.redis import get_redis
from app.memory.episodic import get_episodic_memory
from app.memory.mem0_client import get_semantic_memory

logger = structlog.get_logger(__name__)

router = APIRouter()

SESSION_TTL = 3600  # 1 hour
SESSION_PREFIX = "cofounder:session:"


# ---------- Helpers ----------


async def _get_session(session_id: str) -> dict | None:
    """Load session metadata from Redis."""
    r = get_redis()
    raw = await r.get(f"{SESSION_PREFIX}{session_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def _save_session(session_id: str, session: dict) -> None:
    """Persist session metadata to Redis with TTL."""
    r = get_redis()
    await r.set(
        f"{SESSION_PREFIX}{session_id}",
        json.dumps(session, default=str),
        ex=SESSION_TTL,
    )


async def _check_daily_session_limit(user_id: str) -> None:
    """Raise 403 if user has exceeded their daily session limit."""
    user_settings = await get_or_create_user_settings(user_id)
    tier = user_settings.plan_tier

    max_sessions = (
        user_settings.override_max_sessions_per_day
        if user_settings.override_max_sessions_per_day is not None
        else tier.max_sessions_per_day
    )

    if max_sessions == -1:
        return  # unlimited

    r = get_redis()
    today = date.today().isoformat()
    key = f"cofounder:sessions:{user_id}:{today}"
    count = int(await r.get(key) or 0)

    if count >= max_sessions:
        raise HTTPException(
            status_code=403,
            detail=f"Daily session limit reached ({count}/{max_sessions}). Resets at midnight UTC.",
        )


async def _increment_session_count(user_id: str) -> None:
    """Increment daily session counter."""
    r = get_redis()
    today = date.today().isoformat()
    key = f"cofounder:sessions:{user_id}:{today}"
    await r.incrby(key, 1)
    await r.expire(key, 90_000)  # 25h TTL


# ---------- Request / Response ----------


class ChatRequest(BaseModel):
    message: str
    project_id: str = "default"
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    status: str
    current_node: str
    message: str
    is_complete: bool
    needs_human_review: bool


# ---------- Endpoints ----------


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: ClerkUser = Depends(require_subscription)):
    """Send a message to the AI Co-Founder agent."""
    session_id = request.session_id or str(uuid.uuid4())
    user_id = user.user_id

    episodic = get_episodic_memory()
    session = await _get_session(session_id)
    episode_id: int | None = None

    if session is None:
        # New session — check limits first
        await _check_daily_session_limit(user_id)

        state = create_initial_state(
            user_id=user_id,
            project_id=request.project_id,
            project_path=f"/workspace/{request.project_id}",
            goal=request.message,
            session_id=session_id,
        )
        graph = create_production_graph()
        session = {"state": state}
        await _increment_session_count(user_id)

        # Start episodic memory tracking
        try:
            episode_id = await episodic.start_episode(
                user_id=user_id,
                project_id=request.project_id,
                session_id=session_id,
                goal=request.message,
            )
            session["episode_id"] = episode_id
        except Exception as e:
            logger.warning("episodic_memory_start_failed", error=str(e), error_type=type(e).__name__, user_id=user_id)
    else:
        state = session["state"]
        episode_id = session.get("episode_id")
        graph = create_production_graph()
        if request.message:
            state["current_goal"] = request.message
            state["messages"].append({"role": "user", "content": request.message})

    config = {"configurable": {"thread_id": session_id}}

    try:
        result = await graph.ainvoke(state, config)
        session["state"] = result
        await _save_session(session_id, session)

        # Update episodic memory
        if episode_id:
            try:
                await episodic.update_episode(
                    episode_id=episode_id,
                    steps_completed=result.get("current_step_index", 0),
                    errors=result.get("active_errors"),
                    status="success" if result.get("is_complete") else "in_progress",
                    files_created=list(result.get("working_files", {}).keys()),
                )
            except Exception as e:
                logger.warning(
                    "episodic_memory_update_failed", error=str(e), error_type=type(e).__name__, user_id=user_id
                )

        # Store in semantic memory
        try:
            semantic = get_semantic_memory()
            await semantic.add(
                content=f"Task: {request.message}\nResult: {result.get('status_message')}",
                user_id=user_id,
                project_id=request.project_id,
            )
        except Exception as e:
            logger.warning("semantic_memory_store_failed", error=str(e), error_type=type(e).__name__, user_id=user_id)

        return ChatResponse(
            session_id=session_id,
            status=result.get("status_message", "Processing"),
            current_node=result.get("current_node", "unknown"),
            message=_get_last_assistant_message(result),
            is_complete=result.get("is_complete", False),
            needs_human_review=result.get("needs_human_review", False),
        )
    except Exception as e:
        if episode_id:
            try:
                await episodic.complete_episode(
                    episode_id=episode_id,
                    status="failed",
                    final_error=str(e),
                )
            except Exception as ex:
                logger.warning(
                    "episodic_memory_complete_failed", error=str(ex), error_type=type(ex).__name__, user_id=user_id
                )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user: ClerkUser = Depends(require_subscription)):
    """Stream agent responses via SSE."""
    session_id = request.session_id or str(uuid.uuid4())
    session = await _get_session(session_id)

    if session is None:
        await _check_daily_session_limit(user.user_id)

        state = create_initial_state(
            user_id=user.user_id,
            project_id=request.project_id,
            project_path=f"/tmp/cofounder/{request.project_id}",
            goal=request.message,
            session_id=session_id,
        )
        session = {"state": state}
        await _increment_session_count(user.user_id)
    else:
        state = session["state"]
        if request.message:
            state["current_goal"] = request.message
            state["messages"].append({"role": "user", "content": request.message})

    graph = create_cofounder_graph()

    async def generate_events() -> AsyncGenerator[str, None]:
        config = {"configurable": {"thread_id": session_id}}

        try:
            async for event in graph.astream(state, config):
                for node_name, node_state in event.items():
                    if isinstance(node_state, dict):
                        status = node_state.get("status_message", "Processing...")
                    else:
                        status = f"Node output: {type(node_state).__name__}"
                    yield f"data: {_format_sse_event(session_id, node_name, status)}\n\n"

            # Save final state
            session["state"] = state
            await _save_session(session_id, session)

            yield f"data: {_format_sse_event(session_id, 'complete', _get_last_assistant_message(state))}\n\n"
        except Exception as e:
            error_details = f"{type(e).__name__}: {e}"
            yield f"data: {_format_sse_event(session_id, 'error', error_details)}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str, action: str = "continue", user: ClerkUser = Depends(require_subscription)):
    """Resume a paused session after human review."""
    session = await _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session["state"]

    if action == "abort":
        state["has_fatal_error"] = True
        state["status_message"] = "Aborted by user"
        await _save_session(session_id, session)
        return {"status": "aborted"}

    state["needs_human_review"] = False
    graph = create_production_graph()
    config = {"configurable": {"thread_id": session_id}}

    result = await graph.ainvoke(state, config)
    session["state"] = result
    await _save_session(session_id, session)

    return {
        "status": result.get("status_message"),
        "is_complete": result.get("is_complete", False),
    }


@router.get("/sessions/{session_id}")
async def get_session_state(session_id: str, user: ClerkUser = Depends(require_auth)):
    """Get the current state of a session."""
    session = await _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    state = session["state"]

    return {
        "session_id": session_id,
        "current_goal": state.get("current_goal"),
        "current_node": state.get("current_node"),
        "status_message": state.get("status_message"),
        "is_complete": state.get("is_complete"),
        "needs_human_review": state.get("needs_human_review"),
        "plan": state.get("plan"),
        "messages": state.get("messages", [])[-20:],
    }


# ---------- History / Memory ----------


@router.get("/history")
async def get_task_history(
    project_id: str | None = None,
    limit: int = 20,
    status: str | None = None,
    user: ClerkUser = Depends(require_auth),
):
    """Get task history from episodic memory."""
    episodic = get_episodic_memory()
    try:
        episodes = await episodic.get_recent_episodes(
            user_id=user.user_id,
            project_id=project_id,
            limit=limit,
            status=status,
        )
        return {"episodes": episodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/errors")
async def get_error_patterns(project_id: str | None = None, user: ClerkUser = Depends(require_auth)):
    """Get common error patterns from failed tasks."""
    episodic = get_episodic_memory()
    try:
        patterns = await episodic.get_error_patterns(
            user_id=user.user_id,
            project_id=project_id,
        )
        return {"error_patterns": patterns}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories")
async def get_user_memories(project_id: str | None = None, user: ClerkUser = Depends(require_auth)):
    """Get stored memories/preferences for the user."""
    semantic = get_semantic_memory()
    try:
        memories = await semantic.get_all(
            user_id=user.user_id,
            project_id=project_id,
        )
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Formatters ----------


def _get_last_assistant_message(state: dict) -> str:
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, dict):
            if msg.get("role") == "assistant":
                return msg.get("content", "")
        elif hasattr(msg, "content"):
            return msg.content
    return state.get("status_message", "Processing...")


def _format_sse_event(session_id: str, node: str, message: str) -> str:
    return json.dumps({"session_id": session_id, "node": node, "message": message})
