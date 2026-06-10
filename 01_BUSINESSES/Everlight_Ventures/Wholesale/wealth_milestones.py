"""wealth_milestones -- the 3-deal wealth roadmap, codified.

Rich's roadmap (locked 2026-04-25):
  Deal 1 ($10-15k commission)  -> file LLC + reinstate license + 1yr subscriptions
  Deal 2 + 3 ($10-30k each)    -> Airbnb side hustle ($2-4k/mo recurring)
  Deal 4+                       -> wholesaling never pauses; Airbnb compounds
  All-in: tax / savings / benefits / credit strategies sequenced post-deal

This module:
  1. Tracks cumulative commission across all closed deals
  2. Detects when a milestone threshold is crossed
  3. Posts the milestone checklist to Slack
  4. Pre-loads the next milestone in the queue

Each milestone is a triplet:
  - threshold (cumulative $ in commissions to trigger)
  - title + checklist (what to do when fired)
  - status (pending / fired / completed)

This runs on every closed Deal via a Django signal (signals.py wires it),
plus a daily cron sweep as a safety net.

Usage:
  python3 wealth_milestones.py status
  python3 wealth_milestones.py check          # check + fire any newly-crossed
  python3 wealth_milestones.py mark-complete --milestone-code=llc_filed
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/content_tools",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("wealth_milestones")

# Persistent ledger of milestone fires + completions
LEDGER = Path("/home/opc/wholesale/_logs/wealth_milestones.jsonl")
LEDGER.parent.mkdir(parents=True, exist_ok=True)


# ── The roadmap ─────────────────────────────────────────────────

MILESTONES = [
    # ── Deal 1 ($10-15k) ──
    {
        "code": "deal_1_closed",
        "threshold_dollars": 1.0,  # any close >0 = first deal landed
        "category": "deal",
        "title": "First deal closed",
        "checklist": [
            "Confirm wire received in personal/business account",
            "Sweep 30% to tax-savings account immediately",
            "Sweep 30% to operating buffer (HYSA)",
            "Pay yourself 40% as the first profit distribution",
        ],
    },
    {
        "code": "llc_filed",
        "threshold_dollars": 10000.0,
        "category": "structure",
        "title": "File the LLC",
        "checklist": [
            "GA Sec of State LLC filing online ($100, 5 days)",
            "Get EIN from IRS (free, 5 minutes online)",
            "Order LLC operating agreement template ($100 LegalZoom or free Nolo)",
            "Open business checking (Chase / Mercury / Bluevine)",
            "Move all subsequent commissions through the LLC, not personal",
        ],
    },
    {
        "code": "license_reinstated",
        "threshold_dollars": 10000.0,
        "category": "structure",
        "title": "Reinstate real estate license",
        "checklist": [
            "Pay GA Real Estate Commission reinstatement fee",
            "Complete any required CE hours (check status on grec.state.ga.us)",
            "Update license status in agent dispatch + Slack handles",
            "Attach license # to PSA templates + email signatures",
        ],
    },
    {
        "code": "subscription_stack",
        "threshold_dollars": 12000.0,
        "category": "tools",
        "title": "Annual subscription stack (1 year prepaid)",
        "checklist": [
            "BatchSkipTracing $30/mo (annual ~$360) -- unlocks the 110 phone-only leads",
            "PropStream $99/mo (annual ~$1,200) -- replaces manual title search",
            "Brex business credit card (free, no PG)",
            "Carrot landing page builder $49/mo (annual ~$590) -- inbound funnel",
            "DocuSign Business $40/mo -- e-sig PSA + assignment",
            "Total ~$2,500/year. Pull from operating buffer, not commission.",
        ],
    },
    # ── Deal 2 + 3 cumulative ──
    {
        "code": "airbnb_research",
        "threshold_dollars": 25000.0,
        "category": "expansion",
        "title": "Begin Airbnb side hustle research",
        "checklist": [
            "Identify 3 target neighborhoods (Atlanta short-term-rental friendly)",
            "Pull AirDNA / Mashvisor data (free trial) on each neighborhood",
            "Estimate gross monthly revenue per property ($2-4k target)",
            "Decide structure: rental arbitrage vs management agreement vs co-host",
            "Draft your standard homeowner pitch + management contract",
        ],
    },
    {
        "code": "airbnb_first_contract",
        "threshold_dollars": 35000.0,
        "category": "expansion",
        "title": "Lock in first Airbnb homeowner contract",
        "checklist": [
            "Approach 5 absentee landlords from PropertyLead pool",
            "Pitch: you cover ALL operating costs, split revenue 50/50 or 60/40",
            "Sign one 12-month management agreement",
            "List on Airbnb + VRBO + Booking.com (free)",
            "Hand off cleaning to TurnoverBnB or local cleaner",
            "Target $2-4k/mo recurring within 60 days of listing",
        ],
    },
    # ── Deal 4+ recurring ──
    {
        "code": "s_corp_election",
        "threshold_dollars": 50000.0,
        "category": "tax",
        "title": "S-Corp election (saves 15.3% SE tax on distributions)",
        "checklist": [
            "File IRS Form 2553 within 75 days of LLC formation OR by March 15 of tax year",
            "Set up payroll: pay yourself reasonable comp as W-2",
            "Take the rest as distributions (no SE tax)",
            "Estimated savings: 5-15k/yr at $50-100k net income",
            "Talk to a CPA before filing -- this election is one-way for 5 years",
        ],
    },
    {
        "code": "solo_401k",
        "threshold_dollars": 60000.0,
        "category": "tax",
        "title": "Open Solo 401(k) for tax-deferred wealth",
        "checklist": [
            "Open Solo 401(k) at Fidelity / Schwab / Vanguard (free)",
            "$66,000/yr contribution limit (2026)",
            "$23,000 employee contribution + 25% employer contribution",
            "Reduces taxable income $-for-$",
            "Set monthly auto-contribution; revisit annually",
        ],
    },
    {
        "code": "credit_ladder",
        "threshold_dollars": 75000.0,
        "category": "credit",
        "title": "Open business credit ladder",
        "checklist": [
            "Apply for Brex (no PG, free) -- by now you should qualify",
            "Apply for Amex Business Gold ($295/yr but 4x dining + groceries for client meals)",
            "Open Capital One Spark Cash Plus (2% on everything)",
            "Get DUNS number (free at dnb.com)",
            "Open net-30 vendor accounts: Uline, Quill, Crown Office Supply",
            "Goal: $50k in business credit lines within 90 days",
        ],
    },
    {
        "code": "hsa_disability",
        "threshold_dollars": 100000.0,
        "category": "benefits",
        "title": "Health + disability protection",
        "checklist": [
            "Switch to HDHP if not already on one (deductible insurance)",
            "Open HSA -- $4,300 single (2026) max contribution, triple tax advantage",
            "Get disability insurance (Guardian / Northwestern Mutual ~$50/mo)",
            "Both deductible if S-corp + employee on group plan",
        ],
    },
]


def cumulative_commission() -> float:
    """Sum of all CommissionRecord rows (or closed Deal.value if commission table empty)."""
    from django.db.models import Sum
    total = 0.0
    try:
        from broker_ops.models import CommissionRecord
        total = float(CommissionRecord.objects.aggregate(t=Sum("amount"))["t"] or 0.0)
    except Exception:
        total = 0.0

    # Fallback: sum closed Deal.value when CommissionRecord table is empty
    if total == 0.0:
        try:
            from broker_ops.models import Deal
            total = float(Deal.objects.filter(
                stage__in=["closed", "funded", "wired"]
            ).aggregate(t=Sum("value"))["t"] or 0.0)
        except Exception:
            pass

    return total


def _load_status() -> dict:
    """Read the ledger and return {code: status} dict."""
    status = {}
    if not LEDGER.exists():
        return status
    for line in LEDGER.read_text().splitlines():
        try:
            r = json.loads(line)
            code = r.get("code")
            event = r.get("event")
            if code and event in ("fired", "completed"):
                status[code] = event
        except Exception:
            continue
    return status


def _record(event: str, code: str, payload: dict) -> None:
    LEDGER.open("a").write(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "code": code,
        **payload,
    }) + "\n")


def check_and_fire() -> dict:
    """Compare cumulative commission vs each milestone threshold; fire newly-crossed."""
    cumul = cumulative_commission()
    status = _load_status()
    fired = []

    for ms in MILESTONES:
        if status.get(ms["code"]) in ("fired", "completed"):
            continue
        if cumul >= ms["threshold_dollars"]:
            _fire_milestone(ms, cumul)
            fired.append(ms["code"])

    return {"cumulative_commission": cumul, "fired_now": fired,
             "status_snapshot": status}


def _fire_milestone(ms: dict, cumul: float) -> None:
    log.info(f"FIRING milestone {ms['code']} at cumul=${cumul:,.0f}")
    _record("fired", ms["code"], {
        "cumulative": cumul,
        "title": ms["title"],
        "category": ms["category"],
    })
    # Slack ping with the checklist
    try:
        from branded_slack import post_branded_slack  # type: ignore
        checklist_md = "\n".join(f"- [ ] {item}" for item in ms["checklist"])
        post_branded_slack(
            channel="#ceo-brief",
            category="report",
            title=f"WEALTH MILESTONE -- {ms['title']}",
            summary=f"Cumulative commission ${cumul:,.0f} crossed ${ms['threshold_dollars']:,.0f} threshold.",
            body=f"Category: {ms['category']}\n\nChecklist:\n{checklist_md}\n\nMilestone code: {ms['code']}",
            agent_name="Marcus Cole",
            agent_title="Chief Operator",
        )
    except Exception:
        pass


def mark_complete(code: str) -> dict:
    """Manually mark a milestone complete (CEO confirms it's done)."""
    _record("completed", code, {})
    log.info(f"milestone {code} marked completed")
    return {"code": code, "status": "completed"}


def status() -> dict:
    cumul = cumulative_commission()
    s = _load_status()
    out = {"cumulative_commission": cumul, "milestones": []}
    for ms in MILESTONES:
        out["milestones"].append({
            "code": ms["code"],
            "title": ms["title"],
            "category": ms["category"],
            "threshold": ms["threshold_dollars"],
            "status": s.get(ms["code"], "pending"),
            "crossed": cumul >= ms["threshold_dollars"],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "check", "mark-complete"])
    ap.add_argument("--milestone-code", default="")
    args = ap.parse_args()

    if args.cmd == "status":
        result = status()
    elif args.cmd == "check":
        result = check_and_fire()
    elif args.cmd == "mark-complete":
        if not args.milestone_code:
            print("--milestone-code required")
            return
        result = mark_complete(args.milestone_code)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
