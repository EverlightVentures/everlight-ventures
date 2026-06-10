"""MaxDispo client -- push a signed contract for buyer placement.

MaxDispo (maxdispo.com) accepts wholesale contracts and matches them to their
cash-buyer network. They charge a fee split on close, not per-submission.

Submission today is a web form. An API is rumored but unconfirmed. This client
supports two modes:

1. If MAXDISPO_WEBHOOK_URL is set, POST the deal as JSON (future API mode)
2. Otherwise log the deal to a submission queue file that Piper manually
   submits through the web form

Environment:
    MAXDISPO_WEBHOOK_URL    optional API/webhook URL (preferred)
    MAXDISPO_AGENT_ID       our partner/agent ID with MaxDispo
    MAXDISPO_API_KEY        optional API key

Usage:
    from integrations.maxdispo_client import push_deal
    result = push_deal({
        "address": "123 Main St", "city": "Atlanta", "state": "GA",
        "purchase_price": 145000, "arv": 245000, "repairs": 22000,
        "assignment_fee": 10000, "contract_pdf_url": "https://...",
    })
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("maxdispo")

SUBMISSION_QUEUE = Path(__file__).resolve().parent.parent / "data" / "maxdispo_queue.jsonl"
SUBMISSION_QUEUE.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class MaxDispoResult:
    ok: bool
    mode: str = ""  # "webhook" or "queued"
    address: str = ""
    submission_id: str = ""
    queued_at: str = ""
    buyer_count_estimate: Optional[int] = None
    raw: dict = field(default_factory=dict)
    error: str = ""


REQUIRED_DEAL_FIELDS = (
    "address", "city", "state", "purchase_price", "arv", "assignment_fee",
)


def push_deal(deal: dict) -> MaxDispoResult:
    """Submit a deal to MaxDispo. Uses webhook if configured, else queue file."""
    missing = [f for f in REQUIRED_DEAL_FIELDS if not deal.get(f)]
    if missing:
        return MaxDispoResult(
            ok=False, address=deal.get("address", ""),
            error=f"missing_fields:{','.join(missing)}",
        )

    webhook_url = os.environ.get("MAXDISPO_WEBHOOK_URL", "")
    agent_id = os.environ.get("MAXDISPO_AGENT_ID", "")
    api_key = os.environ.get("MAXDISPO_API_KEY", "")

    payload = {
        "agent_id": agent_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "deal": deal,
    }

    if webhook_url:
        return _push_via_webhook(webhook_url, api_key, payload)
    return _queue_for_manual_submission(payload)


def _push_via_webhook(url: str, api_key: str, payload: dict) -> MaxDispoResult:
    try:
        import requests
    except ImportError:
        return MaxDispoResult(
            ok=False, address=payload["deal"].get("address", ""),
            error="requests_not_installed",
        )

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
    except requests.RequestException as exc:
        return MaxDispoResult(
            ok=False, address=payload["deal"].get("address", ""),
            mode="webhook", error=f"http_error:{exc}",
        )

    if resp.status_code not in (200, 201, 202):
        return MaxDispoResult(
            ok=False, address=payload["deal"].get("address", ""),
            mode="webhook", error=f"status_{resp.status_code}",
            raw={"body_preview": resp.text[:200]},
        )

    data = {}
    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        pass

    return MaxDispoResult(
        ok=True,
        mode="webhook",
        address=payload["deal"].get("address", ""),
        submission_id=str(data.get("submission_id", "")),
        buyer_count_estimate=data.get("buyer_count_estimate"),
        raw=data,
    )


def _queue_for_manual_submission(payload: dict) -> MaxDispoResult:
    """Append to a JSONL queue file that Piper reviews and submits via the web form."""
    submission_id = f"md_{int(datetime.now(timezone.utc).timestamp())}"
    payload["submission_id"] = submission_id

    with open(SUBMISSION_QUEUE, "a") as f:
        f.write(json.dumps(payload) + "\n")

    log.info("MaxDispo deal queued for manual submission: %s (%s)",
             payload["deal"].get("address"), submission_id)

    return MaxDispoResult(
        ok=True,
        mode="queued",
        address=payload["deal"].get("address", ""),
        submission_id=submission_id,
        queued_at=payload["submitted_at"],
    )
