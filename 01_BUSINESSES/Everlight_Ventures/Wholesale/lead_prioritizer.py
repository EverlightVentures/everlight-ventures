"""lead_prioritizer -- score and rank leads by ChatGPT's "ugly box house" criteria.

Why this exists:
  ChatGPT's framework calls out specific criteria as the highest-converting
  lead profile:
    - Built before 1970 (older = more rehab need = motivated seller)
    - Small square footage (under 1500 = wholesale-friendly comp pricing)
    - Distressed signal (vacant, pre-foreclosure, absentee owner)

  This module scores every PropertyLead against these criteria so the
  outreach cron picks the highest-converting first.

Score breakdown (0-100):
  +25  Built before 1970 (ATTOM year_built field, falls back to year_built)
  +15  Built before 1990 (still old enough to need work)
  +20  Square footage < 1500 (small box = easy flip)
  +10  Square footage < 2000
  +20  Lead type contains "vacant" or "absentee"
  +20  Lead type contains "pre_foreclosure" or "foreclosure"
  +10  Owner phone present (callable)
  +10  Owner email present (emailable)

Usage:
  python3 lead_prioritizer.py rank --state=GA --limit=20
  from lead_prioritizer import rank_leads
  top_leads = rank_leads(state="GA", limit=25)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

for p in ("/home/opc/hive_django",
          "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()


def _score(lead) -> tuple[int, list[str]]:
    """Return (score, list of matched criteria)."""
    score = 0
    matched = []

    year = int(getattr(lead, "year_built", 0) or 0)
    if year and year < 1970:
        score += 25
        matched.append(f"built_pre_1970:{year}")
    elif year and year < 1990:
        score += 15
        matched.append(f"built_pre_1990:{year}")

    sqft = int(getattr(lead, "sqft", 0) or 0)
    if sqft and sqft < 1500:
        score += 20
        matched.append(f"sqft_under_1500:{sqft}")
    elif sqft and sqft < 2000:
        score += 10
        matched.append(f"sqft_under_2000:{sqft}")

    lt = (getattr(lead, "lead_type", "") or "").lower()
    if "vacant" in lt or "absentee" in lt:
        score += 20
        matched.append(f"distress:{lt}")
    if "foreclosure" in lt:
        score += 20
        matched.append(f"foreclosure:{lt}")

    if getattr(lead, "owner_phone", ""):
        score += 10
        matched.append("has_phone")
    if getattr(lead, "owner_email", ""):
        score += 10
        matched.append("has_email")

    return score, matched


def rank_leads(state: str = "GA", limit: int = 25, min_score: int = 30):
    """Return top-scored leads in this state, sorted descending by score."""
    from broker_ops.models import PropertyLead
    qs = PropertyLead.objects.filter(state=state, status="new")
    scored = []
    for lead in qs:
        s, criteria = _score(lead)
        if s >= min_score:
            scored.append((s, criteria, lead))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rank", "stats"])
    ap.add_argument("--state", default="GA")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--min-score", type=int, default=30)
    args = ap.parse_args()

    if args.cmd == "rank":
        ranked = rank_leads(args.state, args.limit, args.min_score)
        out = [
            {
                "score": s,
                "criteria": c,
                "address": lead.address,
                "owner": lead.owner_name,
                "year_built": getattr(lead, "year_built", None),
                "sqft": lead.sqft,
                "lead_type": lead.lead_type,
                "callable": bool(lead.owner_phone),
                "emailable": bool(lead.owner_email),
            }
            for s, c, lead in ranked
        ]
        print(json.dumps(out, indent=2, default=str))
    elif args.cmd == "stats":
        from broker_ops.models import PropertyLead
        from django.db.models import Q
        qs = PropertyLead.objects.filter(state=args.state)
        old = qs.filter(year_built__lt=1970).count()
        small = qs.filter(sqft__lt=1500).count()
        old_and_small = qs.filter(year_built__lt=1970, sqft__lt=1500).count()
        print(json.dumps({
            "state": args.state,
            "total_leads": qs.count(),
            "built_pre_1970": old,
            "sqft_under_1500": small,
            "BOTH_old_and_small": old_and_small,
        }, indent=2))


if __name__ == "__main__":
    main()
