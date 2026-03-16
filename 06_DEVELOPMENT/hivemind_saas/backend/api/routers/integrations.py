"""
Integrations API - manage tenant-connected API keys and OAuth accounts.
All credentials are encrypted at rest before storage.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

SUPPORTED_PROVIDERS = [
    "anthropic", "openai", "google_gemini", "perplexity",
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
async def list_integrations():
    """List all integrations for the current tenant (credentials are masked)."""
    # TODO: fetch from DB with tenant RLS
    return []


@router.post("/", response_model=IntegrationResponse, status_code=201)
async def connect_integration(body: IntegrationUpsert):
    """
    Connect a new integration. API keys are encrypted before storage.
    For OAuth, exchange the code for tokens here.
    """
    if body.provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")

    # TODO: encrypt credential, persist to DB, fire Slack audit
    raise HTTPException(status_code=501, detail="DB not yet connected")


@router.delete("/{integration_id}", status_code=204)
async def disconnect_integration(integration_id: str):
    """Disconnect and delete an integration."""
    # TODO: delete from DB, revoke OAuth token if applicable
    raise HTTPException(status_code=404, detail="Integration not found")


@router.post("/test/{integration_id}")
async def test_integration(integration_id: str):
    """Test that a connected integration is still valid."""
    # TODO: decrypt key, make a lightweight API call to verify
    raise HTTPException(status_code=404, detail="Integration not found")


def _provider_type(provider: str) -> str:
    oauth_providers = {"slack", "notion", "github", "google_drive", "hubspot"}
    return "oauth" if provider in oauth_providers else "api_key"
