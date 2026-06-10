"""Propwire client -- mortgage balance and property detail lookup by address.

Propwire (propwire.com) exposes a public property lookup that returns mortgage
balance, lien history, and recent title activity. As of this writing Propwire
does not publish an official REST API; we authenticate with a session cookie
captured from a logged-in browser and hit the internal JSON endpoints used by
their web app.

Environment:
    PROPWIRE_SESSION_COOKIE   full cookie string from a logged-in session
    PROPWIRE_API_KEY          if/when they release an official API

Usage:
    from integrations.propwire_client import lookup_balance
    result = lookup_balance("123 Main St", "Atlanta", "GA")
    if result.ok:
        print(result.mortgage_balance)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("propwire")

PROPWIRE_BASE = "https://propwire.com"
PROPWIRE_SEARCH_PATH = "/api/properties/search"  # TODO verify endpoint from browser devtools


@dataclass
class PropwireResult:
    ok: bool
    address: str = ""
    mortgage_balance: Optional[float] = None
    estimated_value: Optional[float] = None
    last_sale_price: Optional[float] = None
    last_sale_date: Optional[str] = None
    lien_count: int = 0
    owner_occupied: Optional[bool] = None
    raw: dict = field(default_factory=dict)
    error: str = ""


def _load_auth() -> tuple[str, str]:
    return (
        os.environ.get("PROPWIRE_SESSION_COOKIE", ""),
        os.environ.get("PROPWIRE_API_KEY", ""),
    )


def lookup_balance(address: str, city: str, state: str) -> PropwireResult:
    """Look up mortgage balance for an address. Returns PropwireResult with ok=False
    if credentials are missing or the lookup fails.
    """
    cookie, api_key = _load_auth()
    if not cookie and not api_key:
        return PropwireResult(ok=False, address=address, error="no_credentials")

    try:
        import requests
    except ImportError:
        return PropwireResult(ok=False, address=address, error="requests_not_installed")

    query = urllib.parse.urlencode({"q": f"{address}, {city}, {state}"})
    url = f"{PROPWIRE_BASE}{PROPWIRE_SEARCH_PATH}?{query}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if cookie:
        headers["Cookie"] = cookie

    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as exc:
        log.warning("propwire http error: %s", exc)
        return PropwireResult(ok=False, address=address, error=f"http_error:{exc}")

    if resp.status_code != 200:
        return PropwireResult(
            ok=False, address=address,
            error=f"status_{resp.status_code}",
            raw={"body_preview": resp.text[:200]},
        )

    try:
        data = resp.json()
    except json.JSONDecodeError:
        return PropwireResult(ok=False, address=address, error="invalid_json")

    # TODO: once we observe a real Propwire response, pin these field names.
    # Current mapping is a best-guess based on their UI labels.
    first = (data.get("results") or [None])[0] if isinstance(data, dict) else None
    if not first:
        return PropwireResult(ok=False, address=address, error="no_match", raw=data)

    return PropwireResult(
        ok=True,
        address=address,
        mortgage_balance=_as_float(first.get("mortgage_balance")),
        estimated_value=_as_float(first.get("estimated_value") or first.get("zestimate")),
        last_sale_price=_as_float(first.get("last_sale_price")),
        last_sale_date=first.get("last_sale_date"),
        lien_count=int(first.get("lien_count") or 0),
        owner_occupied=first.get("owner_occupied"),
        raw=first,
    )


def _as_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        if isinstance(val, str):
            val = val.replace("$", "").replace(",", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return None
