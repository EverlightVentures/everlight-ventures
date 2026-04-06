"""
Integrations API - manage tenant-connected API keys and OAuth accounts.
All credentials are encrypted at rest before storage.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import RequestContext, get_request_context
from core.database import get_db
from core.security import decrypt_credential, encrypt_credential
from models.tenant import Integration

router = APIRouter()

SUPPORTED_PROVIDERS = [
    "anthropic", "openai", "google_ai", "google_gemini", "perplexity",
    "slack", "notion", "github", "google_drive", "stripe",
    "zapier", "airtable", "hubspot",
]


class IntegrationUpsert(BaseModel):
    provider: str
    credential_type: str  # "api_key" | "oauth"
    api_key: Optional[str] = None  # for api_key type
    oauth_code: Optional[str] = None  # for oauth type
    scopes: list[str] = []
    label: Optional[str] = None


class IntegrationResponse(BaseModel):
    id: str
    provider: str
    credential_type: str
    label: Optional[str]
    connected: bool
    scopes: list[str]
    created_at: str
    last_verified_at: Optional[str] = None
    masked_preview: Optional[str] = None


@router.get("/providers")
async def list_providers():
    """List all supported integration providers."""
    return {
        "providers": [
            {"id": p, "name": p.replace("_", " ").title(), "type": _provider_type(p)}
            for p in SUPPORTED_PROVIDERS
        ]
    }


@router.get("/", response_model=list[IntegrationResponse])
async def list_integrations(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """List all integrations for the current tenant (credentials are masked)."""
    rows = await db.scalars(
        select(Integration)
        .where(Integration.tenant_id == context.tenant.id)
        .order_by(Integration.created_at.desc())
    )
    return [_to_response(item) for item in rows]


@router.post("/", response_model=IntegrationResponse, status_code=201)
async def connect_integration(
    body: IntegrationUpsert,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Connect a new integration. API keys are encrypted before storage.
    For OAuth, exchange the code for tokens here.
    """
    if body.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported provider: {body.provider}")

    if body.credential_type == "api_key" and not body.api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="api_key is required")
    if body.credential_type == "oauth" and not body.oauth_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="oauth_code is required")

    payload = {
        "provider": body.provider,
        "credential_type": body.credential_type,
        "api_key": body.api_key or "",
        "oauth_code": body.oauth_code or "",
        "scopes": body.scopes,
    }
    encrypted = encrypt_credential(json.dumps(payload))
    existing = await db.scalar(
        select(Integration).where(
            Integration.tenant_id == context.tenant.id,
            Integration.provider == body.provider,
            Integration.label == (body.label or body.provider),
        )
    )

    if existing:
        existing.credential_type = body.credential_type
        existing.encrypted_credentials = encrypted
        existing.scopes = body.scopes
        existing.label = body.label or body.provider.replace("_", " ").title()
        existing.is_active = True
        integration = existing
    else:
        integration = Integration(
            tenant_id=context.tenant.id,
            provider=body.provider,
            credential_type=body.credential_type,
            encrypted_credentials=encrypted,
            scopes=body.scopes,
            label=body.label or body.provider.replace("_", " ").title(),
            is_active=True,
        )
        db.add(integration)

    await db.commit()
    await db.refresh(integration)
    return _to_response(integration)


@router.delete("/{integration_id}", status_code=204)
async def disconnect_integration(
    integration_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect and delete an integration."""
    integration = await db.scalar(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.tenant_id == context.tenant.id,
        )
    )
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    await db.delete(integration)
    await db.commit()
    return None


@router.post("/test/{integration_id}")
async def test_integration(
    integration_id: str,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Test that a connected integration is still valid."""
    integration = await db.scalar(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.tenant_id == context.tenant.id,
        )
    )
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")

    payload = json.loads(decrypt_credential(integration.encrypted_credentials))
    connected = bool(payload.get("api_key") or payload.get("oauth_code"))
    if connected:
        from datetime import datetime, timezone

        integration.last_verified_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(integration)

    return {
        "id": integration.id,
        "provider": integration.provider,
        "connected": connected,
        "last_verified_at": integration.last_verified_at.isoformat() if integration.last_verified_at else None,
    }


def _provider_type(provider: str) -> str:
    oauth_providers = {"slack", "notion", "github", "google_drive", "hubspot"}
    return "oauth" if provider in oauth_providers else "api_key"


def _masked_preview(integration: Integration) -> str:
    try:
        payload = json.loads(decrypt_credential(integration.encrypted_credentials))
        raw = payload.get("api_key") or payload.get("oauth_code") or ""
    except Exception:
        raw = ""
    if not raw:
        return ""
    if len(raw) <= 8:
        return "*" * len(raw)
    return f"{raw[:4]}...{raw[-4:]}"


def _to_response(integration: Integration) -> IntegrationResponse:
    return IntegrationResponse(
        id=integration.id,
        provider=integration.provider,
        credential_type=integration.credential_type,
        label=integration.label,
        connected=integration.is_active,
        scopes=integration.scopes or [],
        created_at=integration.created_at.isoformat(),
        last_verified_at=integration.last_verified_at.isoformat() if integration.last_verified_at else None,
        masked_preview=_masked_preview(integration),
    )
