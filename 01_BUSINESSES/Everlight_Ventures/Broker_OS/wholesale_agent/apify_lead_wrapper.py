"""
Apify Lead Gen Wrapper -- Uses Apify actors to pull property leads at scale.
Free tier: 50 runs/month = potentially 5,000-10,000 leads.

Part of the Everlight Ventures wholesale pipeline.
Agent: Rex Blackwell (lead scout) feeds into Filter Banks (scorer).

IMPORTANT: Verify actor IDs at apify.com/store before running.
Community actors change slugs occasionally. The ones below were valid
as of March 2026 but you should confirm in the Apify store.
"""

import os
import json
import time
import logging
import math
from pathlib import Path
from datetime import datetime, timezone

import requests

log = logging.getLogger("apify_leads")

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"
OUTPUT_DIR = Path(__file__).parent / "data"

# ---------------------------------------------------------------------------
# Pre-built community actors for real estate
# VERIFY these slugs at https://apify.com/store -- they may change.
# ---------------------------------------------------------------------------
ACTORS = {
    "zillow": "maxcopell~zillow-scraper",       # Community Zillow scraper
    "google_maps": "compass~crawler-google-places",  # Google Maps / Places
    "redfin": "epctex~redfin-scraper",           # Community Redfin scraper
}

# Default target cities for the wholesale pipeline
DEFAULT_CITIES = [
    ("Los Angeles", "CA"),
    ("St Louis", "MO"),
    ("Cleveland", "OH"),
    ("Dallas", "TX"),
    ("Atlanta", "GA"),
    ("Phoenix", "AZ"),
]

MAX_RETRIES = 3
POLL_INTERVAL = 5  # seconds


# ---------------------------------------------------------------------------
# Core Apify helpers
# ---------------------------------------------------------------------------

def _headers():
    return {
        "Authorization": f"Bearer {APIFY_TOKEN}",
        "Content-Type": "application/json",
    }


def run_actor(actor_id: str, input_params: dict, wait: bool = True, timeout: int = 300) -> list | dict:
    """Run an Apify actor and optionally wait for results.

    Returns list of result items when wait=True, or {"run_id": ...} when wait=False.
    Returns empty list on any failure.
    """
    if not APIFY_TOKEN:
        log.error("No APIFY_TOKEN set -- export APIFY_TOKEN=apify_api_xxx")
        return []

    url = f"{APIFY_BASE}/acts/{actor_id}/runs"

    try:
        r = requests.post(url, headers=_headers(), json=input_params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as exc:
        log.error("Failed to start actor %s: %s", actor_id, exc)
        return []

    run_data = r.json().get("data", {})
    run_id = run_data.get("id")
    if not run_id:
        log.error("No run_id returned from Apify for actor %s", actor_id)
        return []

    log.info("Actor %s started -- run_id=%s", actor_id, run_id)

    if not wait:
        return {"run_id": run_id}

    # Poll until complete
    status = "RUNNING"
    status_url = f"{APIFY_BASE}/actor-runs/{run_id}"
    iterations = math.ceil(timeout / POLL_INTERVAL)

    for _ in range(iterations):
        try:
            sr = requests.get(status_url, headers=_headers(), timeout=15)
            sr.raise_for_status()
            status = sr.json().get("data", {}).get("status", "UNKNOWN")
        except requests.RequestException as exc:
            log.warning("Poll error for run %s: %s -- retrying", run_id, exc)
            time.sleep(POLL_INTERVAL)
            continue

        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
        time.sleep(POLL_INTERVAL)

    if status != "SUCCEEDED":
        log.error("Actor run %s finished with status: %s", run_id, status)
        return []

    # Fetch results from default dataset
    dataset_id = sr.json().get("data", {}).get("defaultDatasetId")
    if not dataset_id:
        log.error("No dataset returned for run %s", run_id)
        return []

    items_url = f"{APIFY_BASE}/datasets/{dataset_id}/items"
    try:
        items_r = requests.get(items_url, headers=_headers(), params={"format": "json"}, timeout=30)
        items_r.raise_for_status()
        return items_r.json()
    except requests.RequestException as exc:
        log.error("Failed to fetch dataset %s: %s", dataset_id, exc)
        return []


# ---------------------------------------------------------------------------
# Search functions
# ---------------------------------------------------------------------------

def search_zillow(city: str, state: str, max_results: int = 100) -> list:
    """Search Zillow for properties in a city via Apify actor."""
    return run_actor(ACTORS["zillow"], {
        "searchType": "sale",
        "location": f"{city}, {state}",
        "maxItems": max_results,
        "status": "forSale",
    })


def search_google_maps(query: str, location: str, max_results: int = 50) -> list:
    """Search Google Maps for businesses (useful for consulting leads)."""
    return run_actor(ACTORS["google_maps"], {
        "searchStringsArray": [query],
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": max_results,
    })


def search_redfin(city: str, state: str, max_results: int = 100) -> list:
    """Search Redfin for properties via Apify actor."""
    return run_actor(ACTORS["redfin"], {
        "location": f"{city}, {state}",
        "maxItems": max_results,
    })


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_zillow_leads(raw_items: list) -> list[dict]:
    """Normalize Zillow results to standard lead format."""
    leads = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        leads.append({
            "source": "zillow_apify",
            "address": item.get("address", ""),
            "city": item.get("city", ""),
            "state": item.get("state", ""),
            "zip": item.get("zipcode", ""),
            "price": item.get("price", 0),
            "beds": item.get("bedrooms", 0),
            "baths": item.get("bathrooms", 0),
            "sqft": item.get("livingArea", 0),
            "property_type": item.get("homeType", ""),
            "status": item.get("homeStatus", ""),
            "url": item.get("url", ""),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "raw": item,
        })
    return leads


def normalize_google_maps_leads(raw_items: list) -> list[dict]:
    """Normalize Google Maps results to standard lead format (consulting pipeline)."""
    leads = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        leads.append({
            "source": "google_maps_apify",
            "business_name": item.get("title", ""),
            "address": item.get("address", ""),
            "city": item.get("city", ""),
            "state": item.get("state", ""),
            "phone": item.get("phone", ""),
            "website": item.get("website", ""),
            "category": item.get("categoryName", ""),
            "rating": item.get("totalScore", 0),
            "reviews": item.get("reviewsCount", 0),
            "url": item.get("url", ""),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "raw": item,
        })
    return leads


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_lead_gen(cities: list[tuple[str, str]] | None = None, max_per_city: int = 50) -> list[dict]:
    """Run full lead gen cycle across target cities.

    Returns list of normalized leads and saves to data/apify_leads.json.
    """
    if cities is None:
        cities = DEFAULT_CITIES

    all_leads = []
    errors = []

    for city, state in cities:
        log.info("Scouting %s, %s via Apify Zillow actor...", city, state)
        try:
            raw = search_zillow(city, state, max_results=max_per_city)
            leads = normalize_zillow_leads(raw)
            all_leads.extend(leads)
            log.info("Found %d leads in %s, %s", len(leads), city, state)
        except Exception as exc:
            log.error("Error scouting %s, %s: %s", city, state, exc)
            errors.append({"city": city, "state": state, "error": str(exc)})
        time.sleep(2)  # Rate limit between cities

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "apify_leads.json"
    payload = {
        "leads": all_leads,
        "count": len(all_leads),
        "cities_searched": len(cities),
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)

    log.info("Total: %d leads saved to %s (%d errors)", len(all_leads), output_path, len(errors))
    return all_leads


def run_consulting_lead_gen(queries: list[dict] | None = None) -> list[dict]:
    """Run lead gen for AI consulting pipeline via Google Maps.

    Each query is {"query": "...", "location": "..."}.
    """
    if queries is None:
        queries = [
            {"query": "small business", "location": "Los Angeles, CA"},
            {"query": "real estate agency", "location": "Dallas, TX"},
            {"query": "accounting firm", "location": "Atlanta, GA"},
        ]

    all_leads = []
    for q in queries:
        log.info("Searching Google Maps: %s in %s", q["query"], q["location"])
        try:
            raw = search_google_maps(q["query"], q["location"], max_results=30)
            leads = normalize_google_maps_leads(raw)
            all_leads.extend(leads)
            log.info("Found %d consulting leads for '%s'", len(leads), q["query"])
        except Exception as exc:
            log.error("Error searching '%s': %s", q["query"], exc)
        time.sleep(2)

    output_path = OUTPUT_DIR / "consulting_leads.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"leads": all_leads, "count": len(all_leads),
                    "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=2)

    log.info("Total: %d consulting leads saved to %s", len(all_leads), output_path)
    return all_leads


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    leads = run_lead_gen()
    print(f"Generated {len(leads)} wholesale leads")
