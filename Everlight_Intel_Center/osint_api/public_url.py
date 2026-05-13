"""
public_url.py -- Single source of truth for outbound-facing URLs.

When EVERLIGHT_PUBLIC_HOST is set in env (after Cloudflare Tunnel is up),
every emailed sign URL / report link uses the public hostname so recipients
on the open internet (Mikal, Chris, etc) can actually click them.

Otherwise we fall back to 127.0.0.1 -- works for local sims, dies in real send.

Set both env vars when the tunnel ships:
    EVERLIGHT_PUBLIC_HOST_ESIGN=https://esign.everlightventures.io
    EVERLIGHT_PUBLIC_HOST_REPORTS=https://reports.everlightventures.io

A single EVERLIGHT_PUBLIC_HOST=https://esign.everlightventures.io also works
(reports inferred from the same root domain).
"""
from __future__ import annotations

import os


def _strip(s: str | None) -> str:
    return (s or "").strip().rstrip("/")


def esign_base() -> str:
    """Where /sign/<token> URLs live. Public if env set, else local 2302."""
    explicit = _strip(os.environ.get("EVERLIGHT_PUBLIC_HOST_ESIGN"))
    if explicit:
        return explicit
    one = _strip(os.environ.get("EVERLIGHT_PUBLIC_HOST"))
    if one:
        return one
    return "http://127.0.0.1:2302"


def reports_base() -> str:
    """Where /reports/... + /reports/deals/<key>/* live. Public if env set, else local 2200."""
    explicit = _strip(os.environ.get("EVERLIGHT_PUBLIC_HOST_REPORTS"))
    if explicit:
        return explicit
    # If only the unified host is set, infer reports from the same root domain
    one = _strip(os.environ.get("EVERLIGHT_PUBLIC_HOST"))
    if one and "esign." in one:
        return one.replace("esign.", "reports.")
    return "http://127.0.0.1:2200"


def hub_base() -> str:
    """Where the Master Hub lives."""
    explicit = _strip(os.environ.get("EVERLIGHT_PUBLIC_HOST_HUB"))
    if explicit:
        return explicit
    one = _strip(os.environ.get("EVERLIGHT_PUBLIC_HOST"))
    if one and "esign." in one:
        return one.replace("esign.", "hub.")
    return "http://127.0.0.1:2000"


def sign_url(token: str) -> str:
    return f"{esign_base()}/sign/{token}"


def deal_url(deal_key: str, doc_id: str | None = None) -> str:
    base = reports_base()
    if doc_id:
        return f"{base}/reports/deals/{deal_key}/{doc_id}.html"
    return f"{base}/reports/deals/{deal_key}/"


def signed_doc_url(deal_key: str, doc_id: str) -> str:
    return f"{reports_base()}/reports/deals/{deal_key}/{doc_id}_signed.html"


def deals_root_url(deal_key: str) -> str:
    return f"{reports_base()}/reports/deals/{deal_key}/"
