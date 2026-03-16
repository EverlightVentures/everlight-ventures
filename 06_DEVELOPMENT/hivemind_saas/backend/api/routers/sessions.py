"""
Hive Sessions API - start/monitor/retrieve AI sessions.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()


class StartSessionRequest(BaseModel):
    prompt: str
    agents: list[str] = ["claude", "gemini", "codex", "perplexity"]
    mode: str = "full"  # "full", "lite", "custom"


class SessionResponse(BaseModel):
    session_id: str
    status: str
    prompt: str
    agents: list[str]
    started_at: str
    results: Optional[list] = None
    mindmap: Optional[dict] = None


@router.post("/", response_model=SessionResponse, status_code=202)
async def start_session(
    body: StartSessionRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new hive session. Runs agents in parallel.
    Returns immediately with session_id; client polls GET /sessions/:id for results.
    """
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # TODO: persist session to DB, enqueue background job via BullMQ/Redis
    # For now return the stub so the frontend can integrate
    background_tasks.add_task(_run_session_background, session_id, body.prompt, body.agents)

    return SessionResponse(
        session_id=session_id,
        status="queued",
        prompt=body.prompt,
        agents=body.agents,
        started_at=now,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Retrieve a session by ID."""
    # TODO: fetch from DB
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/")
async def list_sessions(limit: int = 20, offset: int = 0):
    """List recent sessions for the current tenant."""
    # TODO: fetch from DB with RLS filtering by tenant
    return {"sessions": [], "total": 0, "limit": limit, "offset": offset}


@router.get("/{session_id}/mindmap")
async def get_session_mindmap(session_id: str):
    """Get the React Flow mindmap graph for a session."""
    # TODO: fetch from DB
    raise HTTPException(status_code=404, detail="Session not found")


async def _run_session_background(session_id: str, prompt: str, agents: list[str]):
    """Background task: runs the hive session and stores results."""
    from services.hive_runner import HiveSession
    # TODO: load tenant_keys from DB (decrypted)
    session = HiveSession(
        session_id=session_id,
        tenant_id="",
        tenant_name="",
        prompt=prompt,
        agents=agents,
    )
    await session.run(tenant_keys={})
