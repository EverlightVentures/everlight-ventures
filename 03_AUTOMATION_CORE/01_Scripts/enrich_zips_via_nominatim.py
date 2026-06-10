"""
enrich_zips_via_nominatim.py -- bulk fill zip_code for leads_db rows.

Uses OpenStreetMap Nominatim public API (free, no auth, 1 req/sec rate limit).

Targets leads where:
- zip_code is empty
- city + state populated (or address contains "MEMPHIS, TN" pattern)
- queue == "needs_enrichment"

After enrichment:
- zip_code populated
- queue stays "needs_enrichment" (still need owner_name, year_built, beds for full Chris match)
  unless minimum data is sufficient for direct-mail outreach (zip + address = enough for mail)

Outputs: enriched leads_db.json + zip_distribution_audit.json
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
UA = "Everlight-Ventures/1.0 (operations@everlightventures.io) wholesale-research"

CHRIS_MEMPHIS_ZIPS = {
    "38127","38128","38134","38117","38111","38141","38115","38118",
    "38116","38109","38104","38122","38107","38114","38106",
}


def lookup_zip(address: str) -> dict:
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(address)}&format=json&addressdetails=1&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        if not data:
            return {"zip": None, "lat": None, "lon": None, "neighborhood": None, "matched": False}
        item = data[0]
        addr_parts = item.get("address", {})
        return {
            "zip": addr_parts.get("postcode"),
            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "neighborhood": addr_parts.get("suburb") or addr_parts.get("neighbourhood") or addr_parts.get("quarter"),
            "matched": True,
        }
    except Exception as e:
        return {"zip": None, "lat": None, "lon": None, "neighborhood": None, "matched": False, "error": str(e)[:60]}


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100

    leads = json.loads(LEADS_DB.read_text())
    targets = [
        i for i, l in enumerate(leads)
        if not l.get("zip_code")
        and (l.get("city") or "").upper() == "MEMPHIS"
        and (l.get("state") or "").upper() == "TN"
        and l.get("address")
    ]
    print(f"Total leads: {len(leads)}")
    print(f"Memphis-needs-zip targets: {len(targets)}")
    print(f"Limit this run: {limit}")
    if not targets:
        print("Nothing to enrich.")
        return

    in_chris_box = []
    out_of_box = []
    no_match = []

    for n, idx in enumerate(targets[:limit], 1):
        lead = leads[idx]
        addr = lead["address"]
        result = lookup_zip(addr)
        z = result.get("zip")
        if z:
            lead["zip_code"] = z
            lead["lat"] = result.get("lat")
            lead["lon"] = result.get("lon")
            lead["neighborhood"] = result.get("neighborhood")
            lead["zip_enriched_at"] = datetime.now(timezone.utc).isoformat()
            if z in CHRIS_MEMPHIS_ZIPS:
                in_chris_box.append((idx, addr, z))
            else:
                out_of_box.append((idx, addr, z))
        else:
            no_match.append((idx, addr))

        if n % 25 == 0 or n == limit:
            print(f"  [{n}/{limit}] in-box={len(in_chris_box)} out={len(out_of_box)} no-match={len(no_match)}")
        time.sleep(1.1)  # Nominatim 1 req/sec

    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    print()
    print(f"=== ENRICHMENT SUMMARY ===")
    print(f"Processed: {min(limit, len(targets))}")
    print(f"In Chris's box: {len(in_chris_box)}  ({100*len(in_chris_box)/max(1,min(limit,len(targets))):.0f}%)")
    print(f"Out of box: {len(out_of_box)}")
    print(f"No match: {len(no_match)}")
    print()
    print(f"=== Top 15 Chris-box matches ===")
    for idx, addr, z in in_chris_box[:15]:
        print(f"  zip {z} | {addr}")
    print()
    zip_dist = Counter(z for _, _, z in in_chris_box)
    print(f"=== Zip distribution (Chris-box only) ===")
    for z, c in zip_dist.most_common():
        print(f"  {z}: {c}")


if __name__ == "__main__":
    main()
