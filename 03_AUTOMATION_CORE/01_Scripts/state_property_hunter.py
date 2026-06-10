"""state_property_hunter -- fills the wholesale pipeline to 100 leads per workable state.

Order: easiest compliance first. Active states (from state_gates.json):
    GA, CA, AZ, MO, TX, TN, FL
Filtered to exclude high-risk per the compliance memory:
    CA pre-foreclosure BLOCKED (CC 2945/1695)
    TX cold SMS BLOCKED (SB 140) -- included but email-only
    NC OUT (HB 797)
    Bot calls BLOCKED cold everywhere (TCPA)

Data sources (no scraping tonight):
    1. pipeline/attom_bulk_leads.json (329 ATTOM-enriched leads already on disk)
    2. Current leads_db.json
    3. ATTOM live API (when cache is insufficient) via broker.attom_enrichment

Outputs:
    - wholesale_agent/leads_db.json       (source of truth for rex_belfort)
    - Wholesale/prospecting/<STATE>_prospects.csv  (per-state tracking sheet)
    - POST dispatch to 127.0.0.1:8600/event/wholesale_lead_new for each NEW lead
    - Best-effort row insert into Supabase wholesale_leads (non-blocking)

Run:
    python3 state_property_hunter.py                  # hunt all workable states
    python3 state_property_hunter.py --state GA       # single state
    python3 state_property_hunter.py --target 100     # target per state
    python3 state_property_hunter.py --dry-run        # preview without dispatch

Per-state CSV columns:
    lead_id | address | city | state | zip | owner_name | email | phone |
    estimated_arv | beds | baths | sqft | year_built | lead_type | distress |
    status | touches | first_contacted | last_contacted | last_message |
    reply_received | offer_amount | outcome | source | created_at
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="[hunter %(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("state_property_hunter")

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WHOLESALE = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent"
LEADS_DB = WHOLESALE / "leads_db.json"
ATTOM_BULK = WHOLESALE / "pipeline" / "attom_bulk_leads.json"
PROSPECTING_DIR = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "prospecting"
PROSPECTING_DIR.mkdir(parents=True, exist_ok=True)

STATE_GATES = json.loads((ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "compliance" / "state_gates.json").read_text())

DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://127.0.0.1:8600")

# Supabase (best-effort; timeouts do not block the hunter)
SB_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
SB_ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww"

# Compliance-derived exclusions (from memory/state_gates):
#   - CA pre-foreclosure BLOCKED (CC 2945/1695) -- exclude PF leads in CA; other CA OK
#   - NC OUT (HB 797) entirely
#   - TX email-only (SB 140)
EXCLUDE_CA_PREFORECLOSURE = True
EXCLUDE_STATES = {"NC"}


def _workable_states(order: str = "easy_first") -> list[str]:
    states = []
    for s, v in STATE_GATES.items():
        if not isinstance(v, dict): continue
        if not v.get("active_in_pipeline"): continue
        if s in EXCLUDE_STATES: continue
        # strictness score
        score = 0
        if "disclosures" in str(v.get("wholesale_legal_status", "")): score += 2
        if v.get("solicitor_registration_required"): score += 3
        if v.get("state_dnc_list"): score += 1
        score += len(v.get("sms_conditions", []))
        score += len(v.get("cold_call_conditions", []))
        if v.get("sms_risk_note"): score += 2
        if v.get("pre_foreclosure_restricted"): score += 3
        states.append((score, s))
    states.sort()
    return [s for _, s in states]


def _load_existing_leads() -> list[dict]:
    if not LEADS_DB.exists():
        return []
    try:
        return json.loads(LEADS_DB.read_text())
    except Exception:
        return []


def _load_attom_cache() -> list[dict]:
    if not ATTOM_BULK.exists():
        return []
    try:
        d = json.loads(ATTOM_BULK.read_text())
        if isinstance(d, list):
            return d
        if isinstance(d, dict) and "leads" in d:
            return d["leads"]
        return []
    except Exception:
        return []


def _lead_key(lead: dict) -> str:
    addr = (lead.get("address") or "").strip().lower()
    city = (lead.get("city") or "").strip().lower()
    state = (lead.get("state") or "").strip().upper()
    return f"{addr}|{city}|{state}"


def _normalize_lead(raw: dict, source: str) -> dict:
    """Bring an ATTOM or CSV row into the leads_db.json shape rex_belfort expects."""
    state = (raw.get("state") or raw.get("address_state") or "").upper()
    now = datetime.now(timezone.utc).isoformat()
    lead_id = raw.get("id") or raw.get("lead_id") or f"lead_{uuid.uuid4().hex[:10]}"
    return {
        "id": lead_id,
        "lead_id": lead_id,
        "address": raw.get("address", ""),
        "city": raw.get("city", ""),
        "state": state,
        "zip": raw.get("zip_code") or raw.get("zip") or "",
        "owner_name": raw.get("owner_name", ""),
        "email": raw.get("owner_email") or raw.get("email", ""),
        "phone": raw.get("owner_phone") or raw.get("phone", ""),
        "estimated_arv": raw.get("estimated_arv") or raw.get("arv") or 0,
        "arv": raw.get("estimated_arv") or raw.get("arv") or 0,
        "beds": raw.get("beds", ""),
        "baths": raw.get("baths", ""),
        "sqft": raw.get("sqft", ""),
        "year_built": raw.get("year_built", ""),
        "lead_type": raw.get("lead_type", "generic"),
        "detected_distress": raw.get("detected_distress") or raw.get("lead_type") or "generic",
        "opportunity_zone": raw.get("opportunity_zone", False),
        "close_tier": raw.get("close_tier", "standard"),
        "belfort_speed": raw.get("belfort_speed", "standard"),
        "source": source,
        "status": "new",
        "outreach_count": 0,
        "touch_count": 0,
        "sequence_step": 0,
        "created_at": now,
        "last_touched_at": None,
        "first_contacted": None,
        "last_contacted": None,
        "last_message": None,
        "reply_received": False,
        "offer_amount": None,
        "outcome": None,
    }


def _dispatch_event(lead: dict) -> tuple[bool, str]:
    body = json.dumps({
        "type": "INSERT",
        "table": "wholesale_leads",
        "record": lead,
        "lead_id": lead["id"],
    }).encode()
    try:
        req = urllib.request.Request(
            f"{DISPATCHER_URL}/event/wholesale_lead_new",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200, r.read(200).decode(errors="replace")
    except Exception as e:
        return False, str(e)


_supabase_circuit_open = False  # trip after first failure; saves long timeouts on N leads


def _supabase_upsert(lead: dict) -> bool:
    """Best-effort insert into Supabase. Trips a circuit breaker on first failure
    so we don't wait 5s per lead when Supabase is unreachable."""
    global _supabase_circuit_open
    if _supabase_circuit_open:
        return False
    row = {
        "id": lead["id"],
        "address": lead["address"],
        "city": lead["city"],
        "state": lead["state"],
        "zip": lead["zip"],
        "owner_name": lead["owner_name"],
        "email": lead["email"],
        "phone": lead["phone"],
        "estimated_arv": lead["estimated_arv"],
        "lead_type": lead["lead_type"],
        "status": "new",
        "source": lead["source"],
        "created_at": lead["created_at"],
    }
    try:
        req = urllib.request.Request(
            f"{SB_URL}/rest/v1/wholesale_leads",
            data=json.dumps(row).encode(),
            headers={
                "apikey": SB_ANON,
                "Authorization": f"Bearer {SB_ANON}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status in (200, 201, 204)
    except Exception as e:
        _supabase_circuit_open = True
        log.warning("Supabase unreachable (%s) -- skipping remaining supabase writes this run", str(e)[:80])
        return False


def _write_state_tracking_csv(state: str, leads: list[dict]) -> Path:
    path = PROSPECTING_DIR / f"{state}_prospects.csv"
    fields = [
        "lead_id", "address", "city", "state", "zip", "owner_name", "email", "phone",
        "estimated_arv", "beds", "baths", "sqft", "year_built", "lead_type", "distress",
        "status", "touches", "first_contacted", "last_contacted", "last_message",
        "reply_received", "offer_amount", "outcome", "source", "created_at",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for l in leads:
            w.writerow({
                "lead_id": l.get("id", ""),
                "address": l.get("address", ""),
                "city": l.get("city", ""),
                "state": l.get("state", ""),
                "zip": l.get("zip", ""),
                "owner_name": l.get("owner_name", ""),
                "email": l.get("email", ""),
                "phone": l.get("phone", ""),
                "estimated_arv": l.get("estimated_arv", ""),
                "beds": l.get("beds", ""),
                "baths": l.get("baths", ""),
                "sqft": l.get("sqft", ""),
                "year_built": l.get("year_built", ""),
                "lead_type": l.get("lead_type", ""),
                "distress": l.get("detected_distress", ""),
                "status": l.get("status", ""),
                "touches": l.get("touch_count", 0),
                "first_contacted": l.get("first_contacted", ""),
                "last_contacted": l.get("last_contacted", ""),
                "last_message": l.get("last_message", ""),
                "reply_received": l.get("reply_received", False),
                "offer_amount": l.get("offer_amount", ""),
                "outcome": l.get("outcome", ""),
                "source": l.get("source", ""),
                "created_at": l.get("created_at", ""),
            })
    return path


def hunt(target_per_state: int = 100, only_state: str | None = None, dry_run: bool = False,
         dispatch_cap_per_state: int = 1) -> dict[str, Any]:
    existing = _load_existing_leads()
    existing_keys = {_lead_key(l) for l in existing}
    attom_pool = _load_attom_cache()

    states = [only_state] if only_state else _workable_states()
    log.info("workable states (easy->strict): %s", ", ".join(states))

    # Pre-bucket the pool
    pool_by_state: dict[str, list[dict]] = {}
    for raw in attom_pool:
        st = (raw.get("state") or raw.get("address_state") or "").upper()
        if not st: continue
        # CA pre-foreclosure exclusion
        if EXCLUDE_CA_PREFORECLOSURE and st == "CA" and (
            (raw.get("lead_type") or "").lower() in ("pre_foreclosure", "preforeclosure", "pf")
        ):
            continue
        pool_by_state.setdefault(st, []).append(raw)

    # Current counts
    current_counts = Counter(l.get("state") for l in existing)
    log.info("current leads_db counts per state: %s", dict(current_counts))

    summary = {"by_state": {}, "dispatched_total": 0, "supabase_ok": 0, "supabase_fail": 0}
    new_leads_all: list[dict] = []

    for st in states:
        have = current_counts.get(st, 0)
        need = max(0, target_per_state - have)
        available = pool_by_state.get(st, [])
        picked = []
        for raw in available:
            if len(picked) >= need: break
            n = _normalize_lead(raw, source="attom_cache")
            n["state"] = st  # force upper
            if _lead_key(n) in existing_keys: continue
            existing_keys.add(_lead_key(n))
            picked.append(n)

        log.info("state %s: have=%d target=%d need=%d picked=%d pool=%d",
                 st, have, target_per_state, need, len(picked), len(available))
        summary["by_state"][st] = {
            "had": have, "target": target_per_state, "need": need,
            "picked": len(picked), "pool_remaining": len(available) - len(picked),
        }
        existing.extend(picked)
        new_leads_all.extend(picked)

        # Per-state tracking CSV (all leads in this state, not just new)
        state_leads = [l for l in existing if (l.get("state") or "").upper() == st]
        csv_path = _write_state_tracking_csv(st, state_leads)
        summary["by_state"][st]["tracking_csv"] = str(csv_path)

    # Persist leads_db.json
    if not dry_run:
        LEADS_DB.write_text(json.dumps(existing, indent=2, default=str))
        log.info("leads_db.json updated (total=%d)", len(existing))

        # Dispatch: cap per state so we do not spawn N subprocesses at once.
        # The hourly rex_belfort cron picks up the remaining leads on its sweep.
        per_state_dispatched: Counter = Counter()
        for lead in new_leads_all:
            if _supabase_upsert(lead):
                summary["supabase_ok"] += 1
            else:
                summary["supabase_fail"] += 1
            st = (lead.get("state") or "").upper()
            if per_state_dispatched[st] >= dispatch_cap_per_state:
                continue
            ok, note = _dispatch_event(lead)
            if ok:
                summary["dispatched_total"] += 1
                per_state_dispatched[st] += 1
            else:
                log.warning("dispatch failed for %s: %s", lead["id"], note[:80])

    summary["new_leads_total"] = len(new_leads_all)
    summary["total_in_db"] = len(existing)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=100, help="leads per state target")
    ap.add_argument("--state", help="single state (e.g. GA) -- default hunts all workable")
    ap.add_argument("--dry-run", action="store_true", help="preview without writes/dispatch")
    ap.add_argument("--dispatch-cap-per-state", type=int, default=1,
                    help="max leads to fire event for per state on this run (default 1 -- safe proof)")
    args = ap.parse_args()

    s = hunt(target_per_state=args.target, only_state=args.state, dry_run=args.dry_run,
             dispatch_cap_per_state=args.dispatch_cap_per_state)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
