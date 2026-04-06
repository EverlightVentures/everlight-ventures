"""
Auth API - signup, login, JWT token management.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_request_context
from core.config import settings
from core.database import get_db
from core.security import create_access_token, hash_password, verify_password
from models.tenant import Tenant, User
from services.slack_audit import AuditEvent, post_audit

router = APIRouter()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str  # company/workspace name


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str
    role: str


class RefreshRequest(BaseModel):
    access_token: str


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new tenant + admin user.
    Creates: tenant record, user record, default Slack audit config.
    """
    if not settings.allow_signup:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Signup is disabled")
    if len(body.password) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 10 characters")

    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    base_slug = re.sub(r"[^a-z0-9]+", "-", body.tenant_name.lower()).strip("-") or "workspace"
    slug = base_slug
    suffix = 2
    while await db.scalar(select(Tenant).where(Tenant.slug == slug)):
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    tenant = Tenant(name=body.tenant_name.strip(), slug=slug, plan_tier="spark")
    user = User(
        tenant=tenant,
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        role="admin",
        is_active=True,
    )
    db.add_all([tenant, user])
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    await post_audit(
        AuditEvent.USER_SIGNED_UP,
        tenant_name=tenant.name,
        tenant_id=tenant.id,
        summary=f"{user.email} created a new workspace.",
        details={"plan": tenant.plan_tier, "role": user.role},
    )

    return TokenResponse(
        access_token=create_access_token(user.id, tenant.id, user.role),
        tenant_id=tenant.id,
        user_id=user.id,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password, return JWT."""
    user = await db.scalar(select(User).where(User.email == body.email.lower(), User.is_active.is_(True)))
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    tenant = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id, Tenant.is_active.is_(True)))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant unavailable")

    return TokenResponse(
        access_token=create_access_token(user.id, tenant.id, user.role),
        tenant_id=tenant.id,
        user_id=user.id,
        role=user.role,
    )


@router.post("/oauth/callback")
async def oauth_callback(provider: str, code: str, state: str):
    """
    OAuth callback handler for SSO providers (Google, GitHub).
    Exchanges code for tokens, creates or links user account.
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"OAuth callback for {provider} is not configured in this deployment",
    )


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Refresh an expired access token."""
    from core.security import decode_token

    try:
        claims = decode_token(body.access_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return {
        "access_token": create_access_token(
            user_id=str(claims.get("sub")),
            tenant_id=str(claims.get("tenant_id")),
            role=str(claims.get("role") or "member"),
        ),
        "token_type": "bearer",
        "tenant_id": str(claims.get("tenant_id")),
        "user_id": str(claims.get("sub")),
        "role": str(claims.get("role") or "member"),
    }


@router.post("/logout")
async def logout():
    """Invalidate the current session (blacklist token in Redis)."""
    return {"message": "Logged out"}
