"""Agent API routes for interacting with the AI Co-Founder.

NOTE: The /chat and /chat/stream endpoints previously used the LangGraph pipeline.
That pipeline has been removed in Phase 40. These endpoints will be re-implemented
in Phase 41 using the AutonomousRunner (TAOR loop). Until then they return 503.
"""

import json
import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


def _extract_session_owner(session: dict) -> str | None:
    """Extract session owner user ID from session metadata/state."""
    owner = session.get("user_id")
    if owner:
        return owner
    state = session.get("state")
    if isinstance(state, dict):
        return state.get("user_id")
    return None


def _require_session_owner(session: dict, user_id: str) -> None:
    """Raise 404 when session is missing ownership metadata or owned by another user."""
    owner_id = _extract_session_owner(session)
    if owner_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")


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
    """Send a message to the AI Co-Founder agent.

    NOTE: This endpoint is pending Phase 41 AutonomousRunner implementation.
    The LangGraph pipeline was removed in Phase 40.
    """
    raise HTTPException(
        status_code=503,
        detail="Build agent temporarily unavailable — AutonomousRunner implementation in progress (Phase 41)",
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user: ClerkUser = Depends(require_subscription)):
    """Stream agent responses via SSE.

    NOTE: This endpoint is pending Phase 41 AutonomousRunner implementation.
    The LangGraph pipeline was removed in Phase 40.
    """
    raise HTTPException(
        status_code=503,
        detail="Build agent temporarily unavailable — AutonomousRunner implementation in progress (Phase 41)",
    )


@router.post("/sessions/{session_id}/resume")
async def resume_session(session_id: str, action: str = "continue", user: ClerkUser = Depends(require_subscription)):
    """Resume a paused session after human review.

    NOTE: This endpoint is pending Phase 41 AutonomousRunner implementation.
    The LangGraph pipeline was removed in Phase 40.
    """
    session = await _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _require_session_owner(session, user.user_id)
    session.setdefault("user_id", user.user_id)

    if action == "abort":
        state = session["state"]
        state["has_fatal_error"] = True
        state["status_message"] = "Aborted by user"
        await _save_session(session_id, session)
        return {"status": "aborted"}

    raise HTTPException(
        status_code=503,
        detail="Build agent resume unavailable — AutonomousRunner implementation in progress (Phase 41)",
    )


@router.get("/sessions/{session_id}")
async def get_session_state(session_id: str, user: ClerkUser = Depends(require_auth)):
    """Get the current state of a session."""
    session = await _get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _require_session_owner(session, user.user_id)

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
    except Exception:
        logger.exception("agent_history_fetch_failed", user_id=user.user_id, project_id=project_id)
        raise HTTPException(status_code=500, detail="Failed to load task history")


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
    except Exception:
        logger.exception("agent_error_patterns_fetch_failed", user_id=user.user_id, project_id=project_id)
        raise HTTPException(status_code=500, detail="Failed to load error patterns")


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
    except Exception:
        logger.exception("agent_memories_fetch_failed", user_id=user.user_id, project_id=project_id)
        raise HTTPException(status_code=500, detail="Failed to load memories")


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
