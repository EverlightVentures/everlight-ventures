"""free_skip_trace -- $0 skip-trace via public people-search routing.

Same pattern as free_title_search: we don't pay for the data, we route to
the right public search URL and return a manual-lookup link. A VA or you
can click the link, copy the phone/email, and paste back into the lead.

Sources (all public, no auth):
  - TruePeopleSearch.com -- free name + city search, returns phone + relatives
  - FastPeopleSearch.com -- mirror of TruePeopleSearch
  - WhitePages.com -- limited free tier, address lookups
  - SpyTox -- free for 5/day

Why we route instead of scrape:
  These sites all have aggressive anti-scrape (CAPTCHA, rate limiting, IP bans).
  Routing returns a clean URL the human can open in a browser. Hands-on but $0.

When BatchSkipTracing budget unlocks (~$30/mo post Deal 1), this gets
deprecated in favor of the API. Until then, this is the free path.

Usage:
  python3 free_skip_trace.py route --address="123 Main St, Atlanta, GA 30309"
  python3 free_skip_trace.py route --owner="John Smith" --city="Atlanta" --state="GA"
  python3 free_skip_trace.py batch --state=GA --limit=20    # routes top 20 GA leads
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

for p in ("/home/opc/hive_django",
          "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()


def route_by_address(address: str, city: str = "", state: str = "") -> dict:
    """Build search URLs across all public skip-trace sites for one address."""
    addr_q = urllib.parse.quote_plus(address)
    citystate = urllib.parse.quote_plus(f"{city}, {state}".strip(", "))
    return {
        "address": address,
        "city": city,
        "state": state,
        "tps_address": f"https://www.truepeoplesearch.com/results?streetaddress={addr_q}&citystatezip={citystate}",
        "fps_address": f"https://www.fastpeoplesearch.com/address/{addr_q}_{citystate}",
        "whitepages_address": f"https://www.whitepages.com/address/{addr_q}/{state.upper()}",
        "spytox_address": f"https://www.spytox.com/address/{addr_q}",
        "instructions": (
            "Open any URL above. Each shows the address resident's name + phone "
            "+ relatives (free). Copy phone/email back to the PropertyLead row."
        ),
    }


def route_by_owner(owner_name: str, city: str = "", state: str = "") -> dict:
    """Build URLs to find a known owner's contact info."""
    name_q = urllib.parse.quote_plus(owner_name)
    citystate = urllib.parse.quote_plus(f"{city}, {state}".strip(", "))
    return {
        "owner_name": owner_name,
        "city": city,
        "state": state,
        "tps_name": f"https://www.truepeoplesearch.com/results?name={name_q}&citystatezip={citystate}",
        "fps_name": f"https://www.fastpeoplesearch.com/name/{name_q}_{citystate}",
        "whitepages_name": f"https://www.whitepages.com/name/{name_q}/{state.upper()}",
        "spytox_name": f"https://www.spytox.com/people/{name_q}",
        "instructions": "Best for finding owners after we have their name from county records.",
    }


def batch_route(state: str = "GA", limit: int = 20) -> dict:
    """Route the top N leads in this state that lack contact info."""
    from broker_ops.models import PropertyLead
    qs = PropertyLead.objects.filter(state=state).filter(
        owner_phone="", owner_email=""
    )[:limit]
    out = []
    for lead in qs:
        if getattr(lead, "owner_name", ""):
            r = route_by_owner(lead.owner_name, lead.city or "", state)
            r["lead_id"] = str(lead.id)
            r["address"] = lead.address
        else:
            r = route_by_address(lead.address or "", lead.city or "", state)
            r["lead_id"] = str(lead.id)
        out.append(r)
    return {"state": state, "routed_count": len(out), "leads": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["route", "batch"])
    ap.add_argument("--address", default="")
    ap.add_argument("--owner", default="")
    ap.add_argument("--city", default="")
    ap.add_argument("--state", default="GA")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    if args.cmd == "route":
        if args.owner:
            result = route_by_owner(args.owner, args.city, args.state)
        elif args.address:
            result = route_by_address(args.address, args.city, args.state)
        else:
            print("--owner OR --address required for route mode")
            return
    elif args.cmd == "batch":
        result = batch_route(args.state, args.limit)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
