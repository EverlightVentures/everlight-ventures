"""Tenant management endpoints."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/me")
async def get_tenant():
    return {"id": "", "name": "", "plan": "spark", "seats": 1}

@router.patch("/me")
async def update_tenant(body: dict):
    return {"updated": True}

@router.get("/me/members")
async def list_members():
    return {"members": []}

@router.post("/me/members")
async def invite_member(body: dict):
    return {"invited": True}
