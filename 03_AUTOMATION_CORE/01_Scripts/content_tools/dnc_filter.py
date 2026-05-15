"""
DNC Filter -- the SUPERVISORY layer that ensures DNC contacts never appear in
any autonomous working set.

Doctrine (Rich, 2026-05-15):
    "never should those DNC contacts be part of an autonomous process. they are
     do not contact and blacklisted. we only remember them so we don't accidentally
     reach out again but they are essentially blocked."

Architecture: this module is called at LOAD TIME by any pipeline that reads a
lead source (leads_db.json, OSINT caches, follow-up schedulers, batch queues, etc.).
It filters DNC contacts OUT of the working set before any downstream logic sees
them. If a DNC contact appears AT ALL in a working set, the filter logs it,
posts a Slack alert, and asks "why is this DNC contact being interacted with?"

This is upstream defense. The eradication_gate at the send-call moment is the
LAST-RESORT tripwire -- it should never fire in production because this filter
should have already removed the contact from the working set.

Public API:
    is_dnc(email=..., address=..., lead_id=..., phone=...) -> bool
    filter_dnc(records, *, key_fns) -> (clean_records, removed_records)
    alert_dnc_touch(context, caller) -> None    # log + Slack + return
    purge_from_file(path, key='email')          # offline scrub utility
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

log = logging.getLogger("dnc_filter")

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# The hardcoded source-of-truth list. Cannot be bypassed by JSON file deletion.
try:
    from eradication_gate import ERADICATED, find_hit
except ImportError as _err:
    log.error("dnc_filter cannot load eradication_gate -- failing closed")
    raise

# JSON DNC stores (secondary sources, additive to the hardcoded list)
DNC_LIST_JSON = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_list.json")
OPTED_OUT_JSON = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/opted_out_emails.json")
ALERT_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/dnc_touch_alerts.log")
SLACK_WEBHOOK_ENV = "SLACK_HIVE_ALERTS_WEBHOOK"


def _load_json_list(p: Path) -> list[dict]:
    try:
        if p.exists():
            data = json.loads(p.read_text())
            return data if isinstance(data, list) else []
    except Exception as exc:
        log.warning("dnc_filter could not read %s: %s", p, exc)
    return []


def _dynamic_dnc_set() -> dict[str, set[str]]:
    """Build a normalized lookup from JSON DNC files. Additive to the hardcoded list."""
    emails: set[str] = set()
    addresses: set[str] = set()
    lead_ids: set[str] = set()
    phones: set[str] = set()
    for rec in _load_json_list(DNC_LIST_JSON) + _load_json_list(OPTED_OUT_JSON):
        if not isinstance(rec, dict):
            continue
        if rec.get("email"):
            emails.add(rec["email"].lower().strip())
        for addr in (rec.get("property_addresses") or []):
            addresses.add(addr.lower().strip())
        if rec.get("property_address"):
            addresses.add(rec["property_address"].lower().strip())
        if rec.get("lead_id"):
            lead_ids.add(str(rec["lead_id"]).lower().strip())
        if rec.get("phone"):
            phones.add(str(rec["phone"]).strip())
    return {"emails": emails, "addresses": addresses, "lead_ids": lead_ids, "phones": phones}


def is_dnc(
    email: Optional[str] = None,
    name: Optional[str] = None,
    address: Optional[str] = None,
    lead_id: Optional[str] = None,
    phone: Optional[str] = None,
) -> bool:
    """Return True if any field matches the hardcoded list OR the JSON DNC stores."""
    if find_hit(email=email, name=name, address=address, lead_id=lead_id, phone=phone):
        return True
    dyn = _dynamic_dnc_set()
    if email and email.lower().strip() in dyn["emails"]:
        return True
    if address:
        a = address.lower().strip()
        if any(a == d or d in a or a in d for d in dyn["addresses"]):
            return True
    if lead_id and str(lead_id).lower().strip() in dyn["lead_ids"]:
        return True
    if phone and str(phone).strip() in dyn["phones"]:
        return True
    return False


def _record_keys(rec: dict, key_fns: dict[str, Callable[[dict], Optional[str]]]) -> dict[str, Optional[str]]:
    out = {}
    for k, fn in key_fns.items():
        try:
            out[k] = fn(rec)
        except Exception:
            out[k] = None
    return out


def filter_dnc(
    records: Iterable[dict],
    *,
    key_fns: Optional[dict[str, Callable[[dict], Optional[str]]]] = None,
    caller: str = "unknown",
) -> tuple[list[dict], list[dict]]:
    """
    Walk an iterable of dict records, return (clean, removed).

    Default key_fns extracts common Everlight fields. Override per-pipeline if
    record shape differs.

    Every removal triggers an alert (log + Slack + audit ledger).
    """
    if key_fns is None:
        key_fns = {
            "email": lambda r: (r.get("owner_email") or r.get("email") or "").strip() or None,
            "address": lambda r: (r.get("address") or r.get("property_address") or "").strip() or None,
            "lead_id": lambda r: str(r.get("lead_id") or r.get("id") or "").strip() or None,
            "name": lambda r: (r.get("owner_name") or r.get("name") or "").strip() or None,
            "phone": lambda r: (r.get("owner_phone") or r.get("phone") or "").strip() or None,
        }

    clean: list[dict] = []
    removed: list[dict] = []
    for r in records:
        if not isinstance(r, dict):
            clean.append(r)
            continue
        keys = _record_keys(r, key_fns)
        if is_dnc(**keys):
            removed.append(r)
            alert_dnc_touch(
                context={"record_keys": keys, "stage": "filter_dnc"},
                caller=caller,
            )
            continue
        clean.append(r)
    return clean, removed


def alert_dnc_touch(context: dict, caller: str = "unknown") -> None:
    """
    Fire when a DNC contact is observed in any autonomous context.
    Writes a structured event AND posts to Slack (if webhook configured).
    The presence of a DNC touch is a process bug -- the alert asks "why?"
    """
    payload = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "caller": caller,
        "context": context,
        "question": "why is this DNC contact being interacted with?",
    }

    # Always log to disk first -- audit trail does not depend on network.
    try:
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ALERT_LOG.open("a") as fh:
            fh.write(json.dumps(payload) + "\n")
    except Exception as exc:
        log.warning("dnc_filter could not write alert log: %s", exc)

    # Best-effort Slack alert. Never raises.
    webhook = os.environ.get(SLACK_WEBHOOK_ENV, "").strip()
    if webhook:
        try:
            from urllib.request import Request, urlopen
            body = json.dumps({
                "text": (
                    f":rotating_light: DNC TOUCH from `{caller}` -- "
                    f"a do-not-contact subject appeared in an autonomous working set.\n"
                    f"Context: ```{json.dumps(context, indent=2)}```\n"
                    f"Question: why is this DNC contact being interacted with?"
                ),
            }).encode()
            req = Request(webhook, data=body, headers={"Content-Type": "application/json"})
            urlopen(req, timeout=5)
        except Exception as exc:
            log.warning("dnc_filter could not post Slack alert: %s", exc)

    log.error("DNC TOUCH alert: caller=%s context=%s", caller, context)


def purge_from_file(path: Path | str, key: str = "email") -> dict:
    """
    Offline scrub utility: remove every DNC-matching record from a JSON list file.
    Returns a summary of what was purged. Always writes a .bak.pre-purge sidecar
    first so the operation is reversible.
    """
    p = Path(path)
    data = json.loads(p.read_text())
    if not isinstance(data, list):
        return {"path": str(p), "error": "not_a_list", "purged": 0}
    backup = p.with_suffix(p.suffix + ".bak.pre-purge")
    backup.write_text(p.read_text())
    clean: list = []
    purged: list = []
    for rec in data:
        if isinstance(rec, dict):
            keys = {
                "email": (rec.get(key) or "").strip() if key in rec else None,
                "address": (rec.get("address") or rec.get("property_address") or "").strip() or None,
                "lead_id": str(rec.get("lead_id") or rec.get("id") or "").strip() or None,
                "name": (rec.get("owner_name") or rec.get("name") or "").strip() or None,
            }
            if is_dnc(**{k: v for k, v in keys.items() if v}):
                purged.append(rec)
                continue
        clean.append(rec)
    p.write_text(json.dumps(clean, indent=2))
    return {"path": str(p), "purged": len(purged), "remaining": len(clean), "backup": str(backup)}


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> int:
    failures = 0

    print("--- is_dnc() cases ---")
    cases = [
        ("streubel email", {"email": "dave@municipalfirm.com"}, True),
        ("streubel caps", {"email": "Dave@MunicipalFirm.com"}, True),
        ("streubel address", {"address": "4435 WESTMINSTER PL, SAINT LOUIS, MO 63108"}, True),
        ("streubel lead_id", {"lead_id": "leg_afee1a472d"}, True),
        ("clean homeowner", {"email": "owner@gmail.com"}, False),
    ]
    for label, kwargs, expect in cases:
        got = is_dnc(**kwargs)
        ok = got == expect
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: expect={expect} got={got}")
        if not ok:
            failures += 1

    print("\n--- filter_dnc() case ---")
    sample = [
        {"lead_id": "leg_clean_1", "owner_email": "alice@gmail.com", "address": "100 Main St"},
        {"lead_id": "leg_afee1a472d", "owner_email": "dave@municipalfirm.com", "address": "4435 WESTMINSTER PL"},
        {"lead_id": "leg_clean_2", "owner_email": "bob@gmail.com", "address": "200 Oak Ave"},
    ]
    clean, removed = filter_dnc(sample, caller="selftest")
    if len(clean) == 2 and len(removed) == 1 and removed[0]["lead_id"] == "leg_afee1a472d":
        print("  [PASS] filter removed exactly 1 record, kept 2")
    else:
        print(f"  [FAIL] expected (clean=2, removed=1) got (clean={len(clean)}, removed={len(removed)})")
        failures += 1

    if failures:
        print(f"\nFAILED: {failures}")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    if len(sys.argv) > 2 and sys.argv[1] == "purge":
        print(json.dumps(purge_from_file(sys.argv[2]), indent=2))
        sys.exit(0)
    print("Usage:")
    print("  python3 dnc_filter.py selftest")
    print("  python3 dnc_filter.py purge <path/to/leads_db.json>")
    sys.exit(2)
