"""Mindmap endpoints - serve React Flow graph data for session visualization."""
from fastapi import APIRouter, HTTPException
router = APIRouter()

@router.get("/{session_id}")
async def get_mindmap(session_id: str):
    # TODO: load from DB
    raise HTTPException(status_code=404, detail="Session not found")

@router.get("/")
async def list_mindmaps(limit: int = 20):
    # TODO: list recent sessions with mindmap data
    return {"mindmaps": [], "total": 0}
