"""Tenant management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import RequestContext, get_admin_context, get_request_context
from core.database import get_db
from core.security import hash_password
from models.tenant import User

router = APIRouter()


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    plan_tier: str | None = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = "member"
    temporary_password: str = "Welcome123!"


@router.get("/me")
async def get_tenant(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    seat_count = await db.scalar(
        select(func.count()).select_from(User).where(User.tenant_id == context.tenant.id, User.is_active.is_(True))
    ) or 0
    return {
        "id": context.tenant.id,
        "name": context.tenant.name,
        "slug": context.tenant.slug,
        "plan": context.tenant.plan_tier,
        "is_active": context.tenant.is_active,
        "stripe_customer_id": context.tenant.stripe_customer_id,
        "seats": seat_count,
    }


@router.patch("/me")
async def update_tenant(
    body: TenantUpdateRequest,
    context: RequestContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db),
):
    if body.name:
        context.tenant.name = body.name.strip()
    if body.plan_tier:
        context.tenant.plan_tier = body.plan_tier
    await db.commit()
    return {"updated": True, "tenant": {"id": context.tenant.id, "name": context.tenant.name, "plan": context.tenant.plan_tier}}


@router.get("/me/members")
async def list_members(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    members = await db.scalars(select(User).where(User.tenant_id == context.tenant.id).order_by(User.created_at.asc()))
    return {
        "members": [
            {
                "id": member.id,
                "email": member.email,
                "role": member.role,
                "is_active": member.is_active,
                "created_at": member.created_at.isoformat(),
            }
            for member in members
        ]
    }


@router.post("/me/members")
async def invite_member(
    body: InviteMemberRequest,
    context: RequestContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    user = User(
        tenant_id=context.tenant.id,
        email=body.email.lower(),
        hashed_password=hash_password(body.temporary_password),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"invited": True, "member_id": user.id, "email": user.email, "role": user.role}
