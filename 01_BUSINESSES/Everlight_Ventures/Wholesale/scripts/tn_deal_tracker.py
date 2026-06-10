#!/usr/bin/env python3
"""
tn_deal_tracker.py -- THE canonical daily Tennessee deal CRM.

ONE focused engine (not another scattered script). Every day it:
  1. Reads Shelby County Assessor parcels (owner_downloads/parsed/*.json) -- the
     real TN address source (owner NAME + property), pulled from the assessor site.
  2. Filters to Chris's buy-box (config/chris_buy_box.json): Memphis residential,
     no vacant lots, year/appraisal band, prefer absentee + tax-delinquent.
  3. Upserts each qualifying parcel into a TRACKED file (tn_deal_tracker.json),
     keyed by parcel_id. NEW parcels are added; existing ones keep their status.
  4. Tracks the full lifecycle per owner: new -> email_needed -> emailed ->
     replied -> negotiating -> under_contract -> assigned / dead.
  5. Flags parcels that need an EMAIL (digital-only doctrine: NO physical mail,
     ever -- skip-trace for the owner's email from name+property).
  6. Stamps the buyer match (Chris @ Mid South Homebuyers) on every qualifier.
  7. Feeds the brain (local-first) + the scoreboard so the Hive remembers.

Idempotent: re-running only adds genuinely new parcels and never double-counts.
Run daily (cron). Host hierarchy: e5-mother when up, else the phone (see
tn_deal_engine.sh launcher). Doctrine: feedback_digital_only_no_postcards,
feedback_brain_intact_local_first, 00_MISSION.md.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
PARSED_DIR = WH / "owner_downloads" / "parsed"
BUY_BOX = WH / "config" / "chris_buy_box.json"
TRACKER = WH / "tn_deal_tracker.json"
DIGEST = WH / "tn_deal_tracker_digest.md"

# Non-dwelling land-use markers (excluded -- Chris buys HOUSES, not lots/churches/commercial).
_VACANT_MARKERS = (
    "VACANT", "LOT", "ACREAGE", "LAND ONLY", "PARKING", "COMMON AREA",
    "RELIGIOUS", "CHURCH", "COMMERCIAL", "INDUSTRIAL", "OFFICE", "RETAIL",
    "WAREHOUSE", "SCHOOL", "GOVERNMENT", "EXEMPT", "UTILITY", "AGRICULTURAL",
    "CEMETERY", "CLUB", "MEDICAL", "BANK", "RESTAURANT", "HOTEL", "MOTEL",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def load_parcels() -> list[dict]:
    out = []
    if not PARSED_DIR.exists():
        return out
    for f in sorted(PARSED_DIR.glob("*.json")):
        p = load_json(f, None)
        if isinstance(p, dict) and p.get("parcel_id"):
            out.append(p)
    return out


def passes_buy_box(parcel: dict, box: dict) -> tuple[bool, str]:
    """Return (passes, reason). Filters on the data the assessor parse gives us."""
    prop = box.get("property", {})
    land_use = str(parcel.get("land_use", "")).upper()
    if prop.get("exclude_vacant_lot", True) and any(m in land_use for m in _VACANT_MARKERS):
        return False, f"vacant/non-dwelling ({land_use.strip(' -')})"
    yb = parcel.get("year_built") or 0
    if yb and prop.get("min_year_built") and yb < prop["min_year_built"]:
        return False, f"year {yb} < min"
    if yb and prop.get("max_year_built") and yb > prop["max_year_built"]:
        return False, f"year {yb} > max"
    appr = parcel.get("total_appraisal_usd") or 0
    if appr and prop.get("min_appraisal_usd") and appr < prop["min_appraisal_usd"]:
        return False, f"appraisal ${appr:,} < min"
    if appr and prop.get("max_appraisal_usd") and appr > prop["max_appraisal_usd"]:
        return False, f"appraisal ${appr:,} > max"
    return True, "fits buy-box"


def email_lookup_url(owner_name: str | None) -> str:
    """Digital-only: route to a free email/skip-trace lookup (NEVER a mailing addr).
    Reuses Wholesale/free_skip_trace if importable; else a TruePeopleSearch URL."""
    owner_name = (owner_name or "").strip()
    if not owner_name:
        return ""
    try:
        sys.path.insert(0, str(WH))
        import free_skip_trace  # type: ignore
        r = free_skip_trace.route_by_owner(owner_name, city="Memphis", state="TN")
        return r.get("url") or r.get("search_url") or ""
    except Exception:
        q = owner_name.replace(" ", "%20")
        return f"https://www.truepeoplesearch.com/results?name={q}&citystatezip=Memphis%2C%20TN"


SENDER_IDENTITY = WH / "config" / "sender_identity.json"
EMAIL_CONFIDENCE_BAR = 50  # email_discovery high-confidence threshold (safe-to-send)


def enrich_emails(limit: int = 10) -> dict:
    """Run REAL email discovery (skip_trace.cascade.discover_email) on the leads still
    needing an email. High-confidence hit -> store email + status 'email_found'. Else
    keep 'email_needed' and record the best candidate. Returns counts."""
    tracker = load_json(TRACKER, {})
    if not isinstance(tracker, dict):
        return {"enriched": 0, "found": 0}
    try:
        sys.path.insert(0, str(WH / "skip_trace"))
        import cascade  # type: ignore
    except Exception as e:
        return {"enriched": 0, "found": 0, "error": f"cascade import: {e}"}
    todo = [v for v in tracker.values() if v.get("status") == "email_needed"][:limit]
    found = 0
    for lead in todo:
        res = cascade.discover_email(lead.get("owner_name", ""))
        lead["email_confidence"] = res.get("confidence", 0)
        lead["email_candidates"] = res.get("candidates", [])
        lead["email_checked_at"] = _now()
        if res.get("email") and (res.get("high_confidence") or res.get("confidence", 0) >= EMAIL_CONFIDENCE_BAR):
            lead["email"] = res["email"]
            lead["status"] = "email_found"
            found += 1
    TRACKER.write_text(json.dumps(tracker, indent=2))
    return {"enriched": len(todo), "found": found}


def compliant_sender() -> tuple:
    """CAN-SPAM gate: a send is only compliant with a real physical postal address.
    Returns (ok, reason). If unset -> NOT ok -> sends PAUSE (Rich: make it compliant or pause)."""
    cfg = load_json(SENDER_IDENTITY, {})
    addr = (cfg.get("physical_address") or "").strip()
    # A compliant postal address has a street/PO-box number. Placeholders + bare
    # "California" do not qualify -> sends stay PAUSED until a deliverable address lands.
    if (not addr or "SET_REAL" in addr.upper() or "PENDING" in addr.upper()
            or not any(c.isdigit() for c in addr)):
        return False, "CAN-SPAM deliverable address not set (config/sender_identity.json) -- sends PAUSED"
    return True, "compliant"


def send_plan() -> dict:
    """How many emails to send today = min(Resend bulk budget remaining, email_found leads).
    Blocks entirely if the CAN-SPAM footer address is not set (compliant-or-pause)."""
    tracker = load_json(TRACKER, {})
    ready = [v for v in (tracker.values() if isinstance(tracker, dict) else [])
             if v.get("status") == "email_found"]
    ok, reason = compliant_sender()
    halt = os.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip() in {"1", "true", "TRUE", "yes"}
    budget_today = None
    try:
        sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE/01_Scripts/content_tools"))
        import resend_budget as rb
        st = rb.budget_status()
        budget_today = min(st.get("today_remaining", 0), st.get("daily_share", 0))
    except Exception:
        budget_today = 20  # conservative default if budget module unavailable
    if halt:
        return {"send_today": 0, "ready": len(ready), "budget_today": budget_today,
                "paused": True, "reason": "WHOLESALE_OUTBOUND_HALT active (operator-gated)"}
    if not ok:
        return {"send_today": 0, "ready": len(ready), "budget_today": budget_today,
                "paused": True, "reason": reason}
    return {"send_today": min(len(ready), budget_today), "ready": len(ready),
            "budget_today": budget_today, "paused": False, "reason": "ok"}


def run(dry_run: bool = False) -> dict:
    box = load_json(BUY_BOX, {})
    buyer = box.get("exit", {}).get("buyer_org", "Mid South Homebuyers")
    buyer_name = box.get("exit", {}).get("buyer_name", "Chris")
    parcels = load_parcels()
    tracker = load_json(TRACKER, {})
    if not isinstance(tracker, dict):
        tracker = {}

    added, requalified, skipped = 0, 0, 0
    for p in parcels:
        pid = str(p["parcel_id"]).strip()
        ok, reason = passes_buy_box(p, box)
        if not ok:
            skipped += 1
            continue
        if pid in tracker:
            # Existing lead: preserve status/history, refresh assessor facts only.
            tracker[pid]["assessor"] = {
                "property_address": p.get("property_address"),
                "owner_name": p.get("owner_name"),
                "land_use": p.get("land_use"),
                "year_built": p.get("year_built"),
                "total_appraisal_usd": p.get("total_appraisal_usd"),
            }
            tracker[pid]["last_seen"] = _now()
            requalified += 1
            continue
        # New qualifying lead -> add at the top of the lifecycle.
        owner = p.get("owner_name", "")
        tracker[pid] = {
            "parcel_id": pid,
            "owner_name": owner,
            "property_address": p.get("property_address"),
            "land_use": p.get("land_use"),
            "year_built": p.get("year_built"),
            "total_appraisal_usd": p.get("total_appraisal_usd"),
            "source_url": p.get("source_url"),
            # CRM lifecycle
            "status": "email_needed",          # new -> email_needed -> emailed -> replied -> ...
            "email": "",
            "email_lookup_url": email_lookup_url(owner),
            "outreach_count": 0,
            "last_contact": None,
            "replied": False,
            "reply_at": None,
            # disposition
            "buyer_match": f"{buyer_name} @ {buyer}",
            "buy_box_reason": reason,
            "first_seen": _now(),
            "last_seen": _now(),
            "notes": [],
        }
        added += 1

    summary = {
        "ran_at": _now(),
        "parcels_scanned": len(parcels),
        "qualifiers_total": sum(1 for v in tracker.values()),
        "added_new": added,
        "refreshed_existing": requalified,
        "skipped_non_buybox": skipped,
        "by_status": {},
        "needs_email": 0,
        "emailed": 0,
        "replied": 0,
    }
    for v in tracker.values():
        st = v.get("status", "unknown")
        summary["by_status"][st] = summary["by_status"].get(st, 0) + 1
        if st == "email_needed":
            summary["needs_email"] += 1
        if v.get("outreach_count", 0):
            summary["emailed"] += 1
        if v.get("replied"):
            summary["replied"] += 1

    if not dry_run:
        TRACKER.write_text(json.dumps(tracker, indent=2))
        _write_digest(tracker, summary, buyer_name, buyer)
        _feed_brain(summary)
        _bump_scoreboard()
    return summary


def _write_digest(tracker: dict, summary: dict, buyer_name: str, buyer: str) -> None:
    lines = [
        "# Tennessee Deal Tracker -- Daily Digest",
        f"*Updated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} | buyer: {buyer_name} @ {buyer}*",
        "",
        f"- Qualifying Memphis leads tracked: **{summary['qualifiers_total']}**",
        f"- Added today: **{summary['added_new']}** | need email: **{summary['needs_email']}** | "
        f"emailed: **{summary['emailed']}** | replied: **{summary['replied']}**",
        f"- Skipped (outside buy-box / vacant lots): {summary['skipped_non_buybox']}",
        "",
    ]
    # Email pipeline + quota-bounded send plan
    try:
        plan = send_plan()
        email_found = sum(1 for v in tracker.values() if v.get("status") == "email_found")
        lines += [
            "",
            "## Email pipeline + send plan (digital-only)",
            f"- Emails found (ready to contact): **{email_found}**",
            f"- Resend budget available today: {plan.get('budget_today')}",
            (f"- **Send today: {plan['send_today']}**" if not plan.get("paused")
             else f"- **Sends PAUSED** -- {plan.get('reason')}"),
        ]
    except Exception as e:
        lines += ["", f"_send plan unavailable: {e}_"]
    lines += [
        "",
        "## Leads needing an email (skip-trace next -- digital-only, NO mail)",
        "",
        "| Parcel | Owner | Property | Yr | Appraisal | Status |",
        "|---|---|---|---|---|---|",
    ]
    shown = 0
    for v in sorted(tracker.values(), key=lambda x: x.get("total_appraisal_usd") or 0, reverse=True):
        if v.get("status") != "email_needed":
            continue
        lines.append(
            f"| {v['parcel_id']} | {(v.get('owner_name') or '')[:28]} | "
            f"{(v.get('property_address') or '')[:24]} | {v.get('year_built') or ''} | "
            f"${(v.get('total_appraisal_usd') or 0):,} | {v.get('status')} |")
        shown += 1
        if shown >= 25:
            break

    # --- DNC / Suppression Ledger (internal compliance) -- the opt-out list Rich watches.
    lines += ["", "## DNC / Suppression Ledger (internal compliance)", ""]
    try:
        sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE/01_Scripts/content_tools"))
        import eradication_gate as eg
        opts = eg.list_opt_outs()
        today = datetime.now(timezone.utc).date().isoformat()
        new_today = sum(1 for o in opts if str(o.get("recorded_at_utc", "")).startswith(today))
        by_scope = {}
        for o in opts:
            s = o.get("scope", "email_only")
            by_scope[s] = by_scope.get(s, 0) + 1
        scope_str = " · ".join(f"{k}: {v}" for k, v in sorted(by_scope.items())) or "none"
        lines += [
            f"- New opt-outs today: **{new_today}**",
            f"- Running total suppressed: **{len(opts)}**  ({scope_str})",
            f"- Plus {1} hardcoded eradication (Streubel-class).",
            "- Honored same-day (legal ceiling is 10 business days).",
            "",
            "| Date | Subject | Scope | Via |",
            "|---|---|---|---|",
        ]
        for o in sorted(opts, key=lambda x: x.get("recorded_at_utc", ""), reverse=True)[:20]:
            subj = (o.get("subject_name") or (o.get("emails") or [""])[0])[:30]
            lines.append(f"| {str(o.get('recorded_at_utc',''))[:10]} | {subj} | "
                         f"{o.get('scope','')} | {o.get('source_channel','')} |")
        if not opts:
            lines.append("| (none yet) | -- | -- | -- |")
    except Exception as e:
        lines.append(f"_ledger unavailable: {e}_")

    DIGEST.write_text("\n".join(lines) + "\n")


def _feed_brain(summary: dict) -> None:
    """Local-first brain write (feedback_brain_intact_local_first)."""
    try:
        sys.path.insert(0, str(ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"))
        import rex_master_pipeline as r
        r.log_blinko(
            f"TN deal tracker daily run {datetime.now(timezone.utc).date()}",
            f"Qualifiers {summary['qualifiers_total']} | +{summary['added_new']} new | "
            f"need email {summary['needs_email']} | emailed {summary['emailed']} | "
            f"replied {summary['replied']}. #hive/wholesale #hive/tn-tracker")
    except Exception:
        pass


def _bump_scoreboard() -> None:
    try:
        sys.path.insert(0, str(ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"))
        import workbook_logger as wl
        wb = wl.WorkbookLogger()
        wb.sync_from_leads_db()
        wb.flush()
    except Exception:
        pass


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    s = run(dry_run=dry)
    # Daily loop: after refreshing the tracker, enrich emails (capped) then re-digest.
    if "--enrich" in sys.argv:
        i = sys.argv.index("--enrich")
        n = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit() else 10
        e = enrich_emails(limit=n)
        run(dry_run=dry)  # refresh digest with new statuses + send plan
        s["enrichment"] = e
    s["send_plan"] = send_plan()
    print(json.dumps(s, indent=2))
