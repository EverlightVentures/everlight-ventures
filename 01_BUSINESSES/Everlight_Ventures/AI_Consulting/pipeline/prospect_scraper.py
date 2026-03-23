#!/usr/bin/env python3
"""
AI Consulting Prospect Scraper -- finds SMBs via Google Maps Places API.

Targets: dentists, home services, agencies in California.
Outputs leads to Django broker_ops API with category 'ai_consulting'.

Usage:
    python3 prospect_scraper.py --vertical dentist --location "Los Angeles, CA" --limit 20
    python3 prospect_scraper.py --vertical "hvac contractor" --location "San Diego, CA"
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = WORKSPACE / "_logs" / "ai_consulting"
GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

# Target verticals with search queries
VERTICALS = {
    "dentist": ["dentist", "dental practice", "dental office"],
    "hvac": ["hvac contractor", "heating and cooling", "air conditioning repair"],
    "plumber": ["plumber", "plumbing service", "plumbing contractor"],
    "electrician": ["electrician", "electrical contractor", "electrical service"],
    "agency": ["digital marketing agency", "web design agency", "seo agency"],
    "legal": ["law firm", "attorney", "legal practice"],
    "real_estate": ["real estate agent", "real estate team", "realtor"],
}


def search_places(query: str, location: str, limit: int = 20) -> list[dict]:
    """Search Google Maps Places API for businesses."""
    if not GOOGLE_API_KEY:
        print("[ERROR] GOOGLE_MAPS_API_KEY not set. Set it in your environment.")
        return []

    text_query = f"{query} in {location}"
    url = (
        "https://maps.googleapis.com/maps/api/place/textsearch/json?"
        + urllib.parse.urlencode({
            "query": text_query,
            "key": GOOGLE_API_KEY,
            "type": "establishment",
        })
    )

    results = []
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        for place in data.get("results", [])[:limit]:
            results.append({
                "business_name": place.get("name", ""),
                "address": place.get("formatted_address", ""),
                "google_rating": place.get("rating", 0),
                "review_count": place.get("user_ratings_total", 0),
                "place_id": place.get("place_id", ""),
                "category": query,
                "location": location,
                "types": place.get("types", []),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        print(f"[ERROR] Places API: {e}")

    return results


def get_place_details(place_id: str) -> dict:
    """Get detailed info (website, phone) for a place."""
    if not GOOGLE_API_KEY:
        return {}

    url = (
        "https://maps.googleapis.com/maps/api/place/details/json?"
        + urllib.parse.urlencode({
            "place_id": place_id,
            "fields": "website,formatted_phone_number,opening_hours,reviews",
            "key": GOOGLE_API_KEY,
        })
    )

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = data.get("result", {})
        return {
            "website": result.get("website", ""),
            "phone": result.get("formatted_phone_number", ""),
            "has_hours": bool(result.get("opening_hours")),
            "review_snippets": [
                r.get("text", "")[:200]
                for r in (result.get("reviews") or [])[:3]
            ],
        }
    except Exception:
        return {}


def ingest_to_django(leads: list[dict], django_url: str = "http://127.0.0.1:8504") -> int:
    """Push leads to Django broker_ops API."""
    ingested = 0
    for lead in leads:
        payload = json.dumps({
            "title": f"AI Consulting: {lead['business_name']}",
            "category": "ai_consulting",
            "description": (
                f"Vertical: {lead['category']}\n"
                f"Location: {lead['address']}\n"
                f"Rating: {lead['google_rating']} ({lead['review_count']} reviews)\n"
                f"Website: {lead.get('website', 'N/A')}\n"
                f"Phone: {lead.get('phone', 'N/A')}"
            ),
            "source": "google_maps_scraper",
            "keywords": [lead["category"], "ai_consulting", "smb"],
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                f"{django_url}/broker/api/ingest/offer/",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10):
                ingested += 1
        except Exception as e:
            print(f"[WARN] Failed to ingest {lead['business_name']}: {e}")

    return ingested


def main():
    parser = argparse.ArgumentParser(description="AI Consulting Prospect Scraper")
    parser.add_argument("--vertical", default="dentist", help="Target vertical")
    parser.add_argument("--location", default="Los Angeles, CA", help="Target location")
    parser.add_argument("--limit", type=int, default=20, help="Max results")
    parser.add_argument("--ingest", action="store_true", help="Push to Django")
    parser.add_argument("--details", action="store_true", help="Fetch place details")
    args = parser.parse_args()

    queries = VERTICALS.get(args.vertical, [args.vertical])
    all_leads = []

    for query in queries:
        print(f"[SCRAPE] Searching: '{query}' in {args.location}")
        leads = search_places(query, args.location, args.limit)
        print(f"  Found {len(leads)} results")

        if args.details:
            for lead in leads:
                details = get_place_details(lead["place_id"])
                lead.update(details)

        all_leads.extend(leads)

    # Dedupe by place_id
    seen = set()
    unique = []
    for lead in all_leads:
        pid = lead.get("place_id", lead["business_name"])
        if pid not in seen:
            seen.add(pid)
            unique.append(lead)

    print(f"\n[TOTAL] {len(unique)} unique leads")

    # Save to log
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"prospects_{args.vertical}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    log_file.write_text(json.dumps(unique, indent=2), encoding="utf-8")
    print(f"[SAVED] {log_file}")

    if args.ingest:
        ingested = ingest_to_django(unique)
        print(f"[INGEST] {ingested}/{len(unique)} pushed to Django broker_ops")


if __name__ == "__main__":
    main()
