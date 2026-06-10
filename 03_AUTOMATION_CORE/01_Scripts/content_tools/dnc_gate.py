"""dnc_gate -- centralized Do-Not-Contact check for every outbound email.

Why
---
Before this gate, opt-outs lived in `opted_out_emails.json` and a half-dozen
ad-hoc checks. Streubel (`dave@municipalfirm.com`) was added after he
threatened a BBB complaint -- so his block is the canary: if dnc_gate
breaks, that block silently disappears, and the next send to him is the
end of the BBB conversation.

This module is the single is_dnc(email) call every sender must make
before hitting Resend. It checks two sources:

  1. Local JSON: `Broker_OS/wholesale_agent/opted_out_emails.json`
     (fast, always available, the operator-explicit ground truth)
  2. Supabase `dnc_emails` table
     (network-dependent, fleet-wide, cross-machine)

Cache: 60-second in-memory LRU on (email_lower, decision). Cheap enough
to call from inside a tight outreach loop.

Failure mode: if the JSON file says "blocked", we trust it (fail-closed
for known-good local data). If neither source returns a hit AND Supabase
errored, we LOG WARN and return False (fail-open) so a transient Supabase
hiccup never paralyzes the entire bot. The JSON is always available on
disk, so the canary email stays blocked even when the network is down.

Public API
----------
    from content_tools.dnc_gate import is_dnc, add_dnc, bulk_load

    if is_dnc("dave@municipalfirm.com"):  # -> True
        return  # never send

CLI
---
    python -m content_tools.dnc_gate --check dave@municipalfirm.com
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

log = logging.getLogger("dnc_gate")

# ── Source paths ────────────────────────────────────────────────────
_THIS = Path(__file__).resolve()

# JSON DNC files -- the operator-explicit ground truth.
# Two files exist with different schemas; both are read on every check and both are
# written by add_dnc(). Lite schema = quick lead-level suppression. Rich schema =
# full case record with channel-specific blocks + evidence + property addresses.
_DNC_JSON_LITE_CANDIDATES = [
    Path("/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json"),
    Path("/home/opc/wholesale/opted_out_emails.json"),
]
_DNC_JSON_RICH_CANDIDATES = [
    Path("/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json"),
    Path("/home/opc/wholesale/compliance/dnc_list.json"),
]


def _resolve_json_path(candidates: list[Path]) -> Optional[Path]:
    for p in candidates:
        if p.exists():
            return p
    return None


_DNC_JSON = _resolve_json_path(_DNC_JSON_LITE_CANDIDATES)
_DNC_JSON_RICH = _resolve_json_path(_DNC_JSON_RICH_CANDIDATES)


def _supabase_creds() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return url, key


# ── Cache ───────────────────────────────────────────────────────────
_CACHE: dict[str, tuple[float, bool]] = {}
_CACHE_TTL = 60.0
_CACHE_LOCK = threading.Lock()


def _normalize(email: str) -> str:
    return (email or "").strip().lower()


def _cache_get(email: str) -> Optional[bool]:
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(email)
        if not entry:
            return None
        ts, decision = entry
        if now - ts > _CACHE_TTL:
            _CACHE.pop(email, None)
            return None
        return decision


def _cache_put(email: str, decision: bool) -> None:
    with _CACHE_LOCK:
        _CACHE[email] = (time.monotonic(), decision)


# ── JSON source ─────────────────────────────────────────────────────
def _load_one_json(path: Optional[Path]) -> set[str]:
    """Load lowercased emails from a single JSON file. Empty set on error/missing."""
    if not path:
        return set()
    try:
        rows = json.loads(path.read_text())
    except Exception as exc:
        log.warning("dnc_gate: JSON load failed (%s): %s", path, exc)
        return set()
    out: set[str] = set()
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                addr = row.get("email") or row.get("to") or ""
            else:
                addr = str(row)
            addr = _normalize(addr)
            if addr:
                out.add(addr)
    return out


def _load_json_set() -> set[str]:
    """Return union of opted-out emails from BOTH JSON files (lite + rich schemas)."""
    return _load_one_json(_DNC_JSON) | _load_one_json(_DNC_JSON_RICH)


# ── Supabase source ─────────────────────────────────────────────────
def _supabase_check(email: str) -> tuple[Optional[bool], str]:
    """Return (decision, reason). decision None means Supabase unavailable."""
    url, key = _supabase_creds()
    if not key:
        return None, "no_service_key"
    try:
        import requests
    except ImportError:
        return None, "requests_missing"
    try:
        # Use ilike for case-insensitive match. We also keep a unique index on
        # lower(email) so even an exact eq match would be safe.
        endpoint = f"{url}/rest/v1/dnc_emails"
        resp = requests.get(
            endpoint,
            params={
                "select": "email",
                "email": f"ilike.{email}",
                "limit": "1",
            },
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
            },
            timeout=8,
        )
    except Exception as exc:
        return None, f"network:{exc.__class__.__name__}"
    if resp.status_code == 200:
        try:
            data = resp.json()
        except Exception:
            return None, "bad_json"
        return (len(data) > 0), "ok"
    if resp.status_code in (401, 403):
        return None, f"auth_{resp.status_code}"
    if resp.status_code == 404 or resp.status_code == 406:
        # Table missing -- treat as unavailable, do not crash.
        return None, f"table_missing_{resp.status_code}"
    return None, f"http_{resp.status_code}"


def _supabase_insert(email: str, reason: str, source: str, thread_id: Optional[str]) -> bool:
    url, key = _supabase_creds()
    if not key:
        return False
    try:
        import requests
    except ImportError:
        return False
    payload = {
        "email": email,
        "reason": reason or "",
        "source": source or "",
        "thread_id": thread_id or None,
    }
    try:
        resp = requests.post(
            f"{url}/rest/v1/dnc_emails",
            json=payload,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                # on_conflict on the unique index so re-runs are idempotent
                "Prefer": "resolution=ignore-duplicates,return=minimal",
            },
            params={"on_conflict": "email"},
            timeout=8,
        )
    except Exception as exc:
        log.warning("dnc_gate: supabase insert failed: %s", exc)
        return False
    return resp.status_code in (200, 201, 204, 409)


# ── Public API ──────────────────────────────────────────────────────
def is_dnc(email: str) -> bool:
    """Return True if the address is on the DNC list. Default fail-open.

    Rules:
      1. JSON hit  -> True (always trust local ground truth).
      2. Supabase hit -> True.
      3. Supabase unavailable + no JSON hit -> False with WARN log.
    """
    addr = _normalize(email)
    if not addr:
        return False
    cached = _cache_get(addr)
    if cached is not None:
        return cached

    json_set = _load_json_set()
    if addr in json_set:
        _cache_put(addr, True)
        return True

    decision, reason = _supabase_check(addr)
    if decision is True:
        _cache_put(addr, True)
        return True
    if decision is False:
        _cache_put(addr, False)
        return False

    # Supabase unavailable. Fail open but warn loudly.
    log.warning(
        "dnc_gate: Supabase unavailable (%s); JSON had no hit for %s -- ALLOWING send",
        reason, addr,
    )
    # Do not cache an unavailable result -- we want to retry on the next call.
    return False


def add_dnc(
    email: str,
    reason: str = "",
    source: str = "",
    thread_id: Optional[str] = None,
) -> dict:
    """Add an address to BOTH the JSON and Supabase. Idempotent.

    Returns a dict with {json_ok, supabase_ok, already_present}.
    """
    addr = _normalize(email)
    if not addr:
        return {"json_ok": False, "supabase_ok": False, "already_present": False, "error": "empty"}

    already_present = False
    json_ok = False
    json_rich_ok = False
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Write to LITE schema (opted_out_emails.json)
    if _DNC_JSON:
        try:
            rows = json.loads(_DNC_JSON.read_text())
            if not isinstance(rows, list):
                rows = []
            seen = {(_normalize(r.get("email", "")) if isinstance(r, dict) else "") for r in rows}
            if addr in seen:
                already_present = True
                json_ok = True
            else:
                rows.append({
                    "email": addr,
                    "reason": reason,
                    "source": source,
                    "thread_id": thread_id,
                    "opted_out_at": now_utc,
                })
                _DNC_JSON.write_text(json.dumps(rows, indent=2))
                json_ok = True
        except Exception as exc:
            log.warning("dnc_gate: JSON write (lite) failed: %s", exc)

    # Write to RICH schema (compliance/dnc_list.json) so cross-channel blocks land too
    if _DNC_JSON_RICH:
        try:
            rows = json.loads(_DNC_JSON_RICH.read_text())
            if not isinstance(rows, list):
                rows = []
            seen = {(_normalize(r.get("email", "")) if isinstance(r, dict) else "") for r in rows}
            if addr in seen:
                json_rich_ok = True  # already present in rich source too
            else:
                rows.append({
                    "id": f"dnc_{addr.replace('@', '_at_').replace('.', '_')}_{int(datetime.now().timestamp())}",
                    "added_utc": now_utc,
                    "name": "",
                    "email": addr,
                    "phone": None,
                    "property_addresses": [],
                    "blocked_channels": ["email", "sms", "phone", "mail", "all"],
                    "reason": reason,
                    "evidence": {
                        "source": source,
                        "thread_id": thread_id,
                    },
                    "do_not_contact": True,
                })
                _DNC_JSON_RICH.write_text(json.dumps(rows, indent=2))
                json_rich_ok = True
        except Exception as exc:
            log.warning("dnc_gate: JSON write (rich) failed: %s", exc)

    supabase_ok = _supabase_insert(addr, reason, source, thread_id)

    # Invalidate cache for this address.
    with _CACHE_LOCK:
        _CACHE.pop(addr, None)

    return {
        "json_ok": json_ok,
        "json_rich_ok": json_rich_ok,
        "supabase_ok": supabase_ok,
        "already_present": already_present,
    }


def bulk_load() -> set[str]:
    """Return a snapshot set of all DNC addresses (JSON union with Supabase).

    For batch scripts that want to filter a recipient list in-memory rather
    than calling is_dnc() per row.
    """
    union = _load_json_set()
    url, key = _supabase_creds()
    if not key:
        return union
    try:
        import requests
        resp = requests.get(
            f"{url}/rest/v1/dnc_emails",
            params={"select": "email", "limit": "10000"},
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            for row in resp.json():
                addr = _normalize(row.get("email", ""))
                if addr:
                    union.add(addr)
    except Exception as exc:
        log.warning("dnc_gate.bulk_load: supabase fetch failed: %s", exc)
    return union


# ── CLI ─────────────────────────────────────────────────────────────
def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", metavar="EMAIL", help="Check if EMAIL is on DNC list")
    ap.add_argument("--add", metavar="EMAIL", help="Add EMAIL to DNC list")
    ap.add_argument("--reason", default="", help="Reason (used with --add)")
    ap.add_argument("--source", default="cli_manual", help="Source tag (used with --add)")
    ap.add_argument("--thread-id", default=None, help="Optional thread id")
    ap.add_argument("--list", action="store_true", help="Print full DNC set")
    args = ap.parse_args()

    if args.check:
        decision = is_dnc(args.check)
        print(f"DNC: {decision}")
        return 0 if decision else 2

    if args.add:
        result = add_dnc(args.add, reason=args.reason, source=args.source, thread_id=args.thread_id)
        print(json.dumps(result, indent=2))
        return 0 if (result["json_ok"] or result["supabase_ok"]) else 1

    if args.list:
        for a in sorted(bulk_load()):
            print(a)
        return 0

    ap.print_help()
    return 1


__all__ = ["is_dnc", "add_dnc", "bulk_load"]


if __name__ == "__main__":
    # Smoke test -- assert Streubel returns True.
    if len(sys.argv) > 1:
        sys.exit(_cli())
    canary = "dave@municipalfirm.com"
    assert is_dnc(canary), f"SMOKE FAIL: {canary} should be DNC"
    print(f"SMOKE OK: {canary} -> True")
