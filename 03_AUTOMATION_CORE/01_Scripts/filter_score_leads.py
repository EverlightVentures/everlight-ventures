"""
filter_score_leads.py -- Filter Banks's lead scoring.

Reads leads_db.json, scores each lead 0-100 using Filter's weights, writes back.
Two-queue scoring (per Slate's cross-check):
  - Email queue: max 100 (full weights)
  - Phone-only queue: max 75 (no email points possible, scaled internally)

Run before each rex_sdr morning batch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter


LEAD_TYPE_WEIGHTS = {
    "tax_lien": 25,
    "tax-lien": 25,
    "pre_foreclosure": 25,
    "preforeclosure": 25,
    "code_violation": 18,
    "code-violation": 18,
    "expired_listing": 15,
    "expired-listing": 15,
    "vacant": 15,
    "absent_owner": 15,
    "absentee": 15,
    "inherited": 18,
    "probate": 18,
    "high_equity": 12,
    "fsbo": 10,
    "general": 5,
    "": 5,
}

ACTIVE_STATES = {"GA", "TX", "FL", "IN"}
ADJACENT_STATES = {"AZ", "OH", "MO"}  # AZ/OH/MO = active but lower priority


def lead_type_pts(lt: str) -> int:
    return LEAD_TYPE_WEIGHTS.get((lt or "").lower(), 5)


def state_pts(state: str) -> int:
    s = (state or "").upper()
    if s in ACTIVE_STATES:
        return 20
    if s in ADJACENT_STATES:
        return 10
    return 0


def email_pts(lead: dict) -> int:
    em = (lead.get("owner_email") or lead.get("email") or "").strip()
    ph = (lead.get("owner_phone") or lead.get("phone") or "").strip()
    if em and "@" in em and not em.endswith("."):
        return 25
    if ph:
        return 8
    return 0


def price_pts(lead: dict) -> int:
    try:
        p = float(lead.get("asking_price") or 0)
        return 10 if p > 0 else 0
    except (TypeError, ValueError):
        return 0


def dom_pts(lead: dict) -> int:
    try:
        d = int(lead.get("days_on_market") or 0)
    except (TypeError, ValueError):
        return 0
    if d > 180:
        return 10
    if d > 90:
        return 7
    if d > 30:
        return 4
    return 1 if d > 0 else 0


def owner_pts(lead: dict) -> int:
    name = (lead.get("owner_name") or "").upper()
    if not name:
        return 0
    llc_signals = (" LLC", " INC", " CORP", " LP ", " LTD", " COMPANY",
                   " INVESTMENTS", " PROPERTIES", " HOLDINGS", " REALTY", " CONTRACTOR")
    trust_signals = (" TRUST", " TRUSTEE")
    if any(s in name for s in llc_signals):
        return 2
    if any(s in name for s in trust_signals):
        return 6
    return 10


def score_lead(lead: dict) -> dict:
    """Returns {score, queue, reason}. Mutates lead with score field."""
    pts = {
        "lead_type": lead_type_pts(lead.get("lead_type", "")),
        "email": email_pts(lead),
        "state": state_pts(lead.get("state", "")),
        "price": price_pts(lead),
        "dom": dom_pts(lead),
        "owner": owner_pts(lead),
    }
    total = sum(pts.values())

    em = (lead.get("owner_email") or lead.get("email") or "").strip()
    ph = (lead.get("owner_phone") or lead.get("phone") or "").strip()
    has_email = bool(em and "@" in em and not em.endswith("."))

    if has_email:
        queue = "email"
    elif ph:
        queue = "phone"
    else:
        queue = "needs_enrichment"

    lead["score"] = total
    lead["score_breakdown"] = pts
    lead["queue"] = queue
    return {"score": total, "queue": queue}


def main():
    paths_to_try = [
        Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"),
        Path("/home/opc/wholesale_agent/leads_db.json"),
    ]
    db_path = next((p for p in paths_to_try if p.exists()), None)
    if not db_path:
        print(f"FATAL: no leads_db.json in any of {[str(p) for p in paths_to_try]}", file=sys.stderr)
        sys.exit(1)

    leads = json.loads(db_path.read_text())
    print(f"Loaded {len(leads)} leads from {db_path}")

    queue_counts = Counter()
    band_counts = Counter()
    for lead in leads:
        result = score_lead(lead)
        queue_counts[result["queue"]] += 1
        s = result["score"]
        if s >= 60:
            band_counts["60-100"] += 1
        elif s >= 30:
            band_counts["30-59"] += 1
        else:
            band_counts["0-29"] += 1

    db_path.write_text(json.dumps(leads, indent=2, default=str))
    print(f"Wrote scores back to {db_path}")
    print("")
    print("=== Queue distribution ===")
    for q, c in queue_counts.most_common():
        print(f"  {q:20} {c:>5}")
    print("")
    print("=== Score band distribution ===")
    for b, c in band_counts.most_common():
        print(f"  {b:10} {c:>5}")
    print("")

    # Top-50 outreach list (Filter's rule)
    actionable = [
        l for l in leads
        if l.get("score", 0) >= 60
        and l.get("queue") == "email"
        and (l.get("state") or "").upper() in ACTIVE_STATES
        and l.get("status") == "new"
    ]
    actionable.sort(key=lambda l: l.get("score", 0), reverse=True)
    print(f"=== TOP EMAIL-QUEUE OUTREACH LIST (score>=60, email, active state, status=new): {len(actionable)} ===")
    for l in actionable[:25]:
        print(f"  score={l['score']:3} {l.get('state','?')} | {(l.get('owner_email','') or '')[:35]:35} | {(l.get('owner_name','') or '')[:25]:25} | {(l.get('address','') or '')[:35]}")

    # Phone queue (Slate's cross-check resolution)
    phone_queue = [
        l for l in leads
        if l.get("score", 0) >= 50  # 50 of 75-effective-max
        and l.get("queue") == "phone"
        and (l.get("state") or "").upper() in {"GA", "TX"}
        and l.get("status") == "new"
        and not l.get("last_contacted")
    ]
    phone_queue.sort(key=lambda l: l.get("score", 0), reverse=True)
    print("")
    print(f"=== PHONE-QUEUE OUTREACH LIST (score>=50, phone-only, GA/TX, status=new): {len(phone_queue)} ===")
    for l in phone_queue[:10]:
        ph = (l.get("owner_phone") or "")[:14]
        print(f"  score={l['score']:3} {l.get('state','?')} | {ph:14} | {(l.get('owner_name','') or '')[:25]:25} | {(l.get('address','') or '')[:35]}")
    if len(phone_queue) > 10:
        print(f"  ... +{len(phone_queue) - 10} more (full list in dial CSV)")


if __name__ == "__main__":
    main()
