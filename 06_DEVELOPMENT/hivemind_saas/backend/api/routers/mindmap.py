"""Mindmap endpoints - serve React Flow graph data for session visualization."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import RequestContext, get_request_context
from core.database import get_db
from models.tenant import HiveSession

router = APIRouter()


@router.get("/{session_id}")
async def get_mindmap(
    session_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    session = await db.scalar(
        select(HiveSession).where(
            HiveSession.id == session_id,
            HiveSession.tenant_id == context.tenant.id,
        )
    )
    if not session or not session.mindmap_data:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.mindmap_data


@router.get("/")
async def list_mindmaps(
    limit: int = 20,
    offset: int = 0,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    total = await db.scalar(
        select(func.count())
        .select_from(HiveSession)
        .where(HiveSession.tenant_id == context.tenant.id, HiveSession.mindmap_data.is_not(None))
    ) or 0
    rows = await db.scalars(
        select(HiveSession)
        .where(HiveSession.tenant_id == context.tenant.id, HiveSession.mindmap_data.is_not(None))
        .order_by(HiveSession.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return {
        "mindmaps": [
            {
                "session_id": row.id,
                "prompt": row.prompt,
                "status": row.status,
                "started_at": row.started_at.isoformat(),
                "mindmap": row.mindmap_data,
            }
            for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
