"""
Hive Sessions API - start/monitor/retrieve AI sessions.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import RequestContext, get_request_context
from core.database import AsyncSessionLocal, get_db
from core.security import decrypt_credential
from models.tenant import HiveSession as HiveSessionModel, Integration, Message

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
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new hive session. Runs agents in parallel.
    Returns immediately with session_id; client polls GET /sessions/:id for results.
    """
    session_id = str(uuid.uuid4())
    session = HiveSessionModel(
        id=session_id,
        tenant_id=context.tenant.id,
        prompt=body.prompt.strip(),
        agents=body.agents,
        mode=body.mode,
        status="queued",
    )
    db.add(session)
    db.add(Message(session_id=session_id, tenant_id=context.tenant.id, role="user", content=body.prompt.strip()))
    await db.commit()
    await db.refresh(session)

    background_tasks.add_task(
        _run_session_background,
        session_id,
        context.tenant.id,
        context.tenant.name,
        body.prompt.strip(),
        body.agents,
        body.mode,
    )

    return _serialize_session(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a session by ID."""
    session = await db.scalar(
        select(HiveSessionModel).where(
            HiveSessionModel.id == session_id,
            HiveSessionModel.tenant_id == context.tenant.id,
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _serialize_session(session)


@router.get("/")
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """List recent sessions for the current tenant."""
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    total = await db.scalar(
        select(func.count()).select_from(HiveSessionModel).where(HiveSessionModel.tenant_id == context.tenant.id)
    ) or 0
    rows = await db.scalars(
        select(HiveSessionModel)
        .where(HiveSessionModel.tenant_id == context.tenant.id)
        .order_by(HiveSessionModel.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return {"sessions": [_serialize_session(row).model_dump() for row in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/{session_id}/mindmap")
async def get_session_mindmap(
    session_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Get the React Flow mindmap graph for a session."""
    session = await db.scalar(
        select(HiveSessionModel).where(
            HiveSessionModel.id == session_id,
            HiveSessionModel.tenant_id == context.tenant.id,
        )
    )
    if not session or not session.mindmap_data:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.mindmap_data


async def _run_session_background(
    session_id: str,
    tenant_id: str,
    tenant_name: str,
    prompt: str,
    agents: list[str],
    mode: str,
):
    """Background task: runs the hive session and stores results."""
    from services.hive_runner import HiveSession

    async with AsyncSessionLocal() as db:
        session_row = await db.scalar(select(HiveSessionModel).where(HiveSessionModel.id == session_id))
        if not session_row:
            return

        session_row.status = "running"
        await db.commit()

        integrations = await db.scalars(
            select(Integration).where(Integration.tenant_id == tenant_id, Integration.is_active.is_(True))
        )
        tenant_keys: dict[str, str] = {}
        for item in integrations:
            try:
                payload = json.loads(decrypt_credential(item.encrypted_credentials))
            except Exception:
                continue
            secret = payload.get("api_key") or payload.get("oauth_code") or ""
            if not secret:
                continue
            tenant_keys[item.provider] = secret
            if item.provider == "google_ai":
                tenant_keys["google_gemini"] = secret

        session = HiveSession(
            session_id=session_id,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            prompt=prompt,
            agents=agents,
        )
        result = await session.run(tenant_keys=tenant_keys)

        session_row.status = result["status"]
        session_row.results = result["results"]
        session_row.mindmap_data = result["mindmap"]
        session_row.total_tokens = sum(item.get("tokens_used", 0) for item in result["results"])
        session_row.duration_s = result.get("duration_s")
        session_row.completed_at = datetime.now(timezone.utc)
        for item in result["results"]:
            db.add(
                Message(
                    session_id=session_id,
                    tenant_id=tenant_id,
                    role=item["agent"],
                    content=item["output"],
                    tokens_used=item.get("tokens_used", 0),
                )
            )

        await db.commit()


def _serialize_session(session: HiveSessionModel) -> SessionResponse:
    return SessionResponse(
        session_id=session.id,
        status=session.status,
        prompt=session.prompt,
        agents=session.agents or [],
        started_at=session.started_at.isoformat(),
        results=session.results,
        mindmap=session.mindmap_data,
    )
