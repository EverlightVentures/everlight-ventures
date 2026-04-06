"""
Shared Supabase client helpers for the hive_dashboard project.

Centralizes URL resolution, auth headers, REST API calls, and edge function
calls so that individual apps do not hardcode credentials or duplicate logic.

Uses the ``requests`` library (already in the project). All functions are
synchronous -- add async wrappers later if needed.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

PROJECT_REF = "jdqqmsmwmbsnlnstyavl"

_DEFAULT_SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"
_DEFAULT_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMs"
    "ImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"
)


# ---------------------------------------------------------------------------
# Credential resolution
# ---------------------------------------------------------------------------

def get_url() -> str:
    """Return the Supabase project URL, checking Django settings, env, then fallback."""
    return (
        getattr(django_settings, "SUPABASE_URL", "")
        or os.environ.get("SUPABASE_URL", "")
        or _DEFAULT_SUPABASE_URL
    ).strip()


def get_anon_key() -> str:
    """Return the Supabase anon/service key, checking Django settings, env, then fallback."""
    return (
        getattr(django_settings, "SUPABASE_ANON_KEY", "")
        or os.environ.get("SUPABASE_ANON_KEY", "")
        or os.environ.get("SUPABASE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or _DEFAULT_SUPABASE_ANON_KEY
    ).strip()


def get_headers() -> dict[str, str]:
    """Return standard auth headers for Supabase REST and edge function calls."""
    key = get_anon_key()
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if key:
        headers["apikey"] = key
        headers["Authorization"] = f"Bearer {key}"
    return headers


def is_configured() -> bool:
    """Return True when both URL and key are available."""
    return bool(get_url() and get_anon_key())


# ---------------------------------------------------------------------------
# REST API helper  --  /rest/v1/<table>
# ---------------------------------------------------------------------------

def supabase_rest(
    table: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | list[dict[str, Any]] | None = None,
    params: dict[str, str] | None = None,
    timeout: float = 6.0,
    extra_headers: dict[str, str] | None = None,
) -> requests.Response:
    """
    Call the Supabase PostgREST endpoint for *table*.

    Returns the raw ``requests.Response`` so callers can inspect status, json,
    etc.  Raises on HTTP errors -- callers should handle exceptions.

    Examples::

        # SELECT rows
        resp = supabase_rest("xlm_bot_metrics", params={"select": "*", "id": "eq.1"})
        rows = resp.json()

        # INSERT
        resp = supabase_rest("events", method="POST", data={"kind": "ping"})
    """
    url = f"{get_url()}/rest/v1/{table}"
    headers = get_headers()
    if extra_headers:
        headers.update(extra_headers)

    response = requests.request(
        method.upper(),
        url,
        headers=headers,
        params=params,
        json=data,
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def supabase_rest_rows(
    table: str,
    *,
    params: dict[str, str],
    timeout: float = 4.0,
) -> list[dict]:
    """
    Convenience wrapper that returns a list of dicts (rows) from a GET query.

    Returns an empty list on any error so callers can safely iterate.
    """
    try:
        resp = supabase_rest(table, method="GET", params=params, timeout=timeout)
        payload = resp.json()
        return payload if isinstance(payload, list) else []
    except Exception as exc:
        logger.debug("supabase_rest_rows failed for %s: %s", table, exc)
        return []


# ---------------------------------------------------------------------------
# Edge Function helper  --  /functions/v1/<function_name>
# ---------------------------------------------------------------------------

def supabase_function(
    function_name: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 20.0,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    POST to a Supabase Edge Function by name.

    Returns the parsed JSON dict.  Raises on HTTP errors.
    """
    url = f"{get_url()}/functions/v1/{function_name}"
    headers = get_headers()
    if extra_headers:
        headers.update(extra_headers)

    response = requests.post(
        url,
        headers=headers,
        json=payload or {},
        timeout=timeout,
    )
    response.raise_for_status()
    result = response.json()
    return result if isinstance(result, dict) else {}
