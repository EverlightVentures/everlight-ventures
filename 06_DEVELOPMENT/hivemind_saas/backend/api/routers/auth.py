"""
Auth API - signup, login, JWT token management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from core.security import create_access_token, hash_password, verify_password

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


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest):
    """
    Register a new tenant + admin user.
    Creates: tenant record, user record, default Slack audit config.
    """
    # TODO: check if email already exists
    # TODO: create tenant + user in DB
    # TODO: fire Slack audit USER_SIGNED_UP event
    # TODO: send welcome email

    raise HTTPException(status_code=501, detail="DB not yet connected - connect Supabase first")


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate with email + password, return JWT."""
    # TODO: look up user in DB, verify_password(), create_access_token()
    raise HTTPException(status_code=501, detail="DB not yet connected")


@router.post("/oauth/callback")
async def oauth_callback(provider: str, code: str, state: str):
    """
    OAuth callback handler for SSO providers (Google, GitHub).
    Exchanges code for tokens, creates or links user account.
    """
    # TODO: exchange code with provider, upsert user
    raise HTTPException(status_code=501, detail="OAuth not yet connected")


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh an expired access token."""
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.post("/logout")
async def logout():
    """Invalidate the current session (blacklist token in Redis)."""
    return {"message": "Logged out"}
