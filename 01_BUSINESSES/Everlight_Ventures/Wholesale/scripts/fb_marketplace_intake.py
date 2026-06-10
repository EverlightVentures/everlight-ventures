#!/usr/bin/env python3
"""
fb_marketplace_intake.py -- Facebook Marketplace LEAD SOURCE, the compliant way.

IMPORTANT (legal, per Priya Bhattacharya): scraping Facebook/Marketplace is a Meta ToS
violation and a litigation risk (Meta actively sues scrapers). There is NO sanctioned public
API to read Marketplace listings. So this is NOT a scraper and NOT a bot. Do NOT point the
hermes_browser_outreach harness at Facebook -- that crosses the ToS line.

The compliant path is HUMAN-IN-THE-LOOP review: a person browses Marketplace at normal pace,
reads "must sell fast / relocating / as-is / inherited" posts, and MANUALLY logs the ones worth
working with this tool. First contact is human-initiated and opt-in-seeking (the human asks the
seller to continue on a channel of their choice); nothing auto-fires. The lead carries
source='fb_marketplace_manual' provenance and is NEVER 'consented' for outreach on its own --
consent is logged later when the seller picks a real channel (channel_router).

If volume ever justifies automation, the sanctioned route is Meta LEAD ADS + the Graph leadgen
webhook (the user submits a form = opt-in), never a Marketplace scraper.

Usage (a human logs a lead they found):
  python3 fb_marketplace_intake.py --add --owner "Jane Doe" --address "123 Elm St, Memphis TN" \\
        --url "https://facebook.com/marketplace/item/..." --note "relocating, needs work, asking 60k"
  python3 fb_marketplace_intake.py --list          # show logged FB leads
  python3 fb_marketplace_intake.py --keywords      # the distressed-seller search terms to scan for
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
INTAKE = WH / "seller_intel" / "fb_marketplace_leads.jsonl"

# What a human reviewer scans Marketplace for (Memphis distressed-seller signals).
DISTRESS_KEYWORDS = [
    "must sell", "must sell fast", "need to sell", "moving", "relocating", "relocation",
    "inherited", "estate sale", "as is", "as-is", "needs work", "fixer", "handyman special",
    "behind on", "facing foreclosure", "tenant problem", "tired landlord", "cash only",
    "make offer", "motivated", "priced to sell", "downsizing", "out of state owner",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_lead(owner: str, address: str, url: str = "", note: str = "", asking: str = "") -> dict:
    rec = {
        "source": "fb_marketplace_manual",        # provenance -- never auto-consented for outreach
        "owner_name": owner, "property_address": address, "post_url": url,
        "note": note[:400], "asking": asking, "state": "TN",
        "status": "new", "consented": False,       # consent is captured later via channel_router
        "logged_by": "human_review", "logged_at": _now(),
    }
    INTAKE.parent.mkdir(parents=True, exist_ok=True)
    with INTAKE.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def list_leads() -> list:
    if not INTAKE.exists():
        return []
    out = []
    for line in INTAKE.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--keywords", action="store_true")
    ap.add_argument("--owner", default=""); ap.add_argument("--address", default="")
    ap.add_argument("--url", default=""); ap.add_argument("--note", default="")
    ap.add_argument("--asking", default="")
    a = ap.parse_args()
    if a.keywords:
        print("Memphis distressed-seller scan terms (human reads Marketplace for these):")
        print("  " + ", ".join(DISTRESS_KEYWORDS))
    elif a.add:
        if not (a.owner and a.address):
            print("need --owner and --address"); sys.exit(1)
        print(json.dumps(add_lead(a.owner, a.address, a.url, a.note, a.asking), indent=2))
    else:
        leads = list_leads()
        print(f"FB Marketplace manual leads: {len(leads)}")
        for l in leads[-15:]:
            print(f"  {l.get('owner_name')} | {l.get('property_address')} | {l.get('note','')[:50]}")
