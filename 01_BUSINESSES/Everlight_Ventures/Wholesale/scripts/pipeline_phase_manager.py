#!/usr/bin/env python3
"""
pipeline_phase_manager.py -- the CONDUCTOR. One unified view of every lead's phase,
plus a proactive sweep that pushes silent/stalled leads to the next phase. Nothing
slips through the cracks.

This is a LAYER ON TOP, not a parallel engine. It reconciles state from the scattered
stores (leads_db, tn_deal_tracker, deal_meta), then DELEGATES the actual work:
  - replies advance via persona_inbox_orchestrator (reactive, already wired)
  - follow-ups / re-engagement fire via arc_send (the 10-stage arc)
It never duplicates send logic, and every action passes the same gates (eradication,
opt-out, TN lockdown, CAN-SPAM compliant-or-pause, Resend budget, HALT).

Phase ladder (seller M-side -> buyer C-side -> close):
  0 sourced -> 1 enriched -> 2 contacted -> 3 engaged -> 4 negotiating
  -> 5 under_contract -> 6 buyer_matched -> 7 assigning -> 8 closing -> 9 closed
  (terminal: dead / dnc)

Usage:
  python3 pipeline_phase_manager.py --state          # the pipeline-state report (who's where)
  python3 pipeline_phase_manager.py --sweep --dry-run   # what WOULD advance (default safe)
  python3 pipeline_phase_manager.py --sweep --agent piper_reeves   # one agent's lane
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
LEADS_DB = ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
TRACKER = WH / "tn_deal_tracker.json"
DEALS_DIR = ROOT / "09_DASHBOARD" / "reports" / "deals"

# --- The canonical phase ladder: phase -> (order, owner persona, next action, advance trigger)
PHASES = {
    "sourced":        (0, "rex_blackwell",  "find the owner's email (Hermes/discovery)", "email found"),
    "enriched":       (1, "piper_reeves",   "send Piper touch-1 (personalized)",          "first email sent"),
    "contacted":      (2, "piper_reeves",   "follow-up touch if silent; watch for reply",  "seller replies"),
    "engaged":        (3, "henry_hammond",  "Henry runs the numbers / opening offer",      "price discussion"),
    "negotiating":    (4, "henry_hammond",  "counter rounds M3/M5/M7 to agreed price",     "seller agrees"),
    "under_contract": (5, "marvin_cohen",   "PSA signed + EMD (SB909 Schedule A)",         "contract executed"),
    "buyer_matched":  (6, "marvin_cohen",   "pitch the deal to Chris @ Mid-South (C1)",    "buyer interested"),
    "assigning":      (7, "marvin_cohen",   "assignment agreement + fee disclosure (C4)",  "assignment signed"),
    "closing":        (8, "vaughn_sterling","title coordination + settlement (C5/T2)",     "funded"),
    "closed":         (9, "vaughn_sterling","collect the spread; log the win",             "-"),
    "dead":           (-1, "-",             "recycle in 90 days or leave dead",            "-"),
    "review_inbound": (-2, "-",             "QUARANTINE: inbound from a non-outreached sender (likely newsletter) -- NOT a seller, do not advance", "-"),
}

WHOLESALE_STATES = {"TN", "TX", "GA", "OH", "FL", "AZ", "MO", "NC", "CA", "MS", "AR"}


def _is_real_seller(lead: dict) -> bool:
    """A real seller lead has a numeric street address AND a US wholesale state.
    Guards against the phone_imap_poller auto-creating 'leads' from personal-inbox
    newsletters (Carnival/Groupon/etc.) -- those must NEVER enter the seller pipeline."""
    addr = str(lead.get("address", "") or "")
    return any(c.isdigit() for c in addr) and lead.get("state") in WHOLESALE_STATES

# Re-engagement cadence (TUNABLE -- operator can edit these 4 numbers).
# Default = the marketing playbook: 5 touches over ~14 days, then 90-day cold rest.
FOLLOWUP_DAYS = [3, 7, 11, 14]   # days after first contact to send touches 2..5
MAX_TOUCHES = 5                  # after this with no reply -> dead_cold
COLD_REST_DAYS = 90              # dead_cold leads come back for one fresh angle after this


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def _days_since(iso: str) -> float:
    try:
        return (_now() - datetime.fromisoformat(iso.replace("Z", "+00:00"))).total_seconds() / 86400
    except Exception:
        return 999.0


def _deal_stage_to_phase(stage: str) -> str:
    s = (stage or "").upper()
    if s in ("M1",): return "contacted"
    if s in ("M3", "M5", "M7"): return "negotiating"
    if s in ("M8",): return "under_contract"
    if s in ("C1", "C3"): return "buyer_matched"
    if s in ("C4",): return "assigning"
    if s in ("C5", "T2"): return "closing"
    return "engaged"


def reconcile() -> list[dict]:
    """Map every lead from every store into ONE phase view. De-dupes deal_meta over
    tracker over leads_db (deal_meta is the most advanced truth)."""
    rows: dict[str, dict] = {}

    # Layer 1: leads_db (the wide base)
    for ld in _load(LEADS_DB, []):
        if not isinstance(ld, dict):
            continue
        key = (ld.get("id") or ld.get("address") or "").strip()
        if not key:
            continue
        st = str(ld.get("status", "new")).lower()
        phase = {"new": "sourced", "contacted": "contacted", "engaged": "engaged",
                 "dead": "dead", "opted_out": "dead", "dnc": "dead"}.get(st, "sourced")
        # GUARD: anything auto-created from inbound (the poller scrapes the personal inbox
        # indiscriminately -> Carnival/Groupon/etc.) must be REVIEWED before it can advance.
        # A real seller reply updates an EXISTING outreached lead; a fresh hot_inbound_auto
        # record is unverified by definition. Also quarantine any non-real-seller shape.
        if phase in ("engaged", "contacted"):
            if str(ld.get("source", "")).startswith("hot_inbound_auto") or not _is_real_seller(ld):
                phase = "review_inbound"
        rows[key] = {"key": key, "who": ld.get("owner_name") or ld.get("address"),
                     "state": ld.get("state"), "phase": phase, "source": "leads_db",
                     "last_touch": ld.get("last_outreach"), "outreach_count": ld.get("outreach_count", 0)}

    # Layer 2: tn_deal_tracker (the curated Memphis house queue -- more precise)
    tracker = _load(TRACKER, {})
    if isinstance(tracker, dict):
        for pid, v in tracker.items():
            st = v.get("status", "email_needed")
            phase = {"email_needed": "sourced", "browser_queued": "sourced",
                     "email_found": "enriched", "emailed": "contacted",
                     "replied": "engaged"}.get(st, "sourced")
            rows[f"tn:{pid}"] = {"key": f"tn:{pid}", "who": v.get("owner_name"),
                                 "state": "TN", "phase": phase, "source": "tn_tracker",
                                 "last_touch": v.get("last_contact"),
                                 "outreach_count": v.get("outreach_count", 0),
                                 "email": v.get("email", "")}

    # Layer 3: deal_meta (active deals -- the most advanced truth, overrides)
    if DEALS_DIR.exists():
        for meta_file in DEALS_DIR.glob("*/deal_meta.json"):
            m = _load(meta_file, {})
            if not isinstance(m, dict):
                continue
            stage = m.get("last_stage") or m.get("stage") or ""
            rows[f"deal:{meta_file.parent.name}"] = {
                "key": f"deal:{meta_file.parent.name}", "who": m.get("seller_name") or m.get("counterparty"),
                "state": m.get("state", "TN"), "phase": _deal_stage_to_phase(stage),
                "source": "deal_meta", "last_touch": m.get("last_contact_at"),
                "deal_stage": stage, "outreach_count": m.get("touch_count", 0)}

    return list(rows.values())


def pipeline_state() -> dict:
    rows = reconcile()
    by_phase: dict[str, int] = {}
    for r in rows:
        by_phase[r["phase"]] = by_phase.get(r["phase"], 0) + 1
    needs_action = _needs_action(rows)
    ordered = sorted(by_phase.items(), key=lambda kv: PHASES.get(kv[0], (99,))[0])
    return {"ran_at": _now().isoformat(), "total_leads": len(rows),
            "by_phase": dict(ordered), "needs_action_count": len(needs_action),
            "needs_action": needs_action[:40]}


def _needs_action(rows: list[dict]) -> list[dict]:
    """The heart of 'nothing slips through the cracks': who is waiting on US to advance them."""
    out = []
    for r in rows:
        phase, oc = r["phase"], r.get("outreach_count", 0) or 0
        days = _days_since(r.get("last_touch") or "") if r.get("last_touch") else None
        if phase == "engaged":
            out.append({**_slim(r), "action": "ADVANCE: seller replied -> Henry runs numbers", "priority": 1})
        elif phase == "enriched":
            out.append({**_slim(r), "action": "SEND: Piper touch-1 (has email, never contacted)", "priority": 2})
        elif phase == "contacted" and days is not None:
            touch_idx = min(oc, len(FOLLOWUP_DAYS))
            if oc >= MAX_TOUCHES:
                out.append({**_slim(r), "action": "REST: max touches, move to dead_cold (90d recycle)", "priority": 5})
            elif touch_idx < len(FOLLOWUP_DAYS) and days >= FOLLOWUP_DAYS[touch_idx - 1 if touch_idx > 0 else 0]:
                out.append({**_slim(r), "action": f"FOLLOW-UP: touch {oc+1} due (silent {days:.0f}d)", "priority": 3})
        elif phase in ("negotiating", "under_contract", "buyer_matched", "assigning", "closing"):
            if days is not None and days >= 3:
                out.append({**_slim(r), "action": f"NUDGE: {phase} stalled {days:.0f}d -> {PHASES[phase][1]} follow up", "priority": 1})
    return sorted(out, key=lambda x: x["priority"])


def _slim(r: dict) -> dict:
    return {"key": r["key"], "who": r.get("who"), "phase": r["phase"], "owner": PHASES.get(r["phase"], ("","-"))[1]}


def sweep(dry_run: bool = True, agent: str = "") -> dict:
    """Proactively act on the needs-action list. Delegates real sends to the existing
    arc/orchestrator; gated by halt + compliance. dry_run reports intent only."""
    actions = _needs_action(reconcile())
    if agent:
        actions = [a for a in actions if a["owner"] == agent]
    halt = os.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}
    fired, blocked = 0, []
    if not dry_run and halt:
        blocked.append("WHOLESALE_OUTBOUND_HALT active -- no sends")
    # NOTE: real firing delegates to persona_inbox_orchestrator (replies) / arc_send
    # (follow-ups). Left as dry-run-reporting until halt lifts + address set; the
    # conductor's job is to SURFACE + SEQUENCE, the existing engines DO the send.
    return {"ran_at": _now().isoformat(), "agent": agent or "all", "dry_run": dry_run,
            "halt_active": halt, "actionable": len(actions), "fired": fired,
            "blocked": blocked, "queue": actions[:25]}


def report() -> str:
    s = pipeline_state()
    lines = ["# Wholesale Pipeline -- Phase State", f"*{s['ran_at'][:16]} | {s['total_leads']} leads*", ""]
    lines.append("## Leads by phase")
    for ph, n in s["by_phase"].items():
        order = PHASES.get(ph, (99, "-", "-"))[0]
        lines.append(f"- **{order if order>=0 else 'X'}. {ph}**: {n}  ({PHASES.get(ph,('','-','-'))[2]})")
    lines += ["", f"## Needs action now: {s['needs_action_count']}"]
    for a in s["needs_action"][:20]:
        lines.append(f"- [{a['phase']}] {str(a['who'])[:30]} -> {a['action']}  ({a['owner']})")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    if "--sweep" in sys.argv:
        ag = ""
        if "--agent" in sys.argv:
            i = sys.argv.index("--agent")
            ag = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        print(json.dumps(sweep(dry_run="--run" not in sys.argv, agent=ag), indent=2))
    else:
        print(report())
