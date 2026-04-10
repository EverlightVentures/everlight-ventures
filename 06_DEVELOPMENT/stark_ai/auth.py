"""Stark AI -- Supabase authentication layer."""
from __future__ import annotations
import requests
from fastapi import HTTPException, Request
from config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY


def _headers(token: str | None = None, service: bool = False) -> dict:
    key = SUPABASE_SERVICE_KEY if service else SUPABASE_ANON_KEY
    h = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    if service and SUPABASE_SERVICE_KEY:
        h["Authorization"] = f"Bearer {SUPABASE_SERVICE_KEY}"
    elif token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def signup(email: str, password: str, display_name: str | None = None) -> dict:
    """Create Supabase user + stark_profiles row."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        json={"email": email, "password": password},
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        detail = resp.json().get("msg", resp.json().get("error_description", "Signup failed"))
        raise HTTPException(status_code=resp.status_code, detail=detail)
    data = resp.json()
    user_id = data.get("user", {}).get("id")
    if user_id:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/stark_profiles",
            json={
                "id": user_id,
                "tier": "client",
                "display_name": display_name or email.split("@")[0],
            },
            headers={**_headers(service=True), "Prefer": "return=representation"},
            timeout=10,
        )
    return data


async def login(email: str, password: str) -> dict:
    """Authenticate and return tokens."""
    resp = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    data = resp.json()
    # Fetch stark profile
    user_id = data.get("user", {}).get("id")
    profile = await get_profile(user_id)
    data["stark_profile"] = profile
    return data


async def get_profile(user_id: str) -> dict:
    """Get stark_profiles row for a user."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/stark_profiles?id=eq.{user_id}&select=*",
        headers=_headers(service=True),
        timeout=10,
    )
    rows = resp.json() if resp.status_code == 200 else []
    if rows and isinstance(rows, list) and len(rows) > 0:
        return rows[0]
    return {"id": user_id, "tier": "public", "display_name": "Anonymous"}


async def verify_token(request: Request) -> dict:
    """Extract and verify Supabase JWT from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    token = auth_header[7:]
    resp = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers=_headers(token),
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = resp.json()
    profile = await get_profile(user["id"])
    return {
        "id": user["id"],
        "email": user.get("email", ""),
        "tier": profile.get("tier", "public"),
        "display_name": profile.get("display_name", ""),
        "voice_enabled": profile.get("voice_enabled", True),
        "preferred_voice": profile.get("preferred_voice", ""),
    }


async def update_profile(user_id: str, updates: dict) -> dict:
    """Update stark_profiles fields."""
    resp = requests.patch(
        f"{SUPABASE_URL}/rest/v1/stark_profiles?id=eq.{user_id}",
        json=updates,
        headers={**_headers(service=True), "Prefer": "return=representation"},
        timeout=10,
    )
    rows = resp.json() if resp.status_code == 200 else []
    return rows[0] if rows and isinstance(rows, list) else {}
