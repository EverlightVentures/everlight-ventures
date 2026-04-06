#!/usr/bin/env python3
"""
Wholesale Property Scraper -- Playwright + Trafilatura automation.

Rex Blackwell's autonomous research assistant. Scrapes:
  - County assessor websites for property details
  - Zillow/Redfin for listing data
  - Public records for ownership info

Feeds data into the wholesale pipeline for deal scoring.

Cron: integrate into rex_master_pipeline.py morning phase
"""
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("wholesale_scraper")

# Add neuromorphic to path
for p in ["/home/opc/06_DEVELOPMENT/everlight_os/neuromorphic",
          "/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/neuromorphic"]:
    if p not in sys.path:
        sys.path.insert(0, p)


def scrape_property_page(url: str) -> dict:
    """Scrape a property listing page with Trafilatura (no browser needed)."""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {"error": "fetch_failed", "url": url}

        text = trafilatura.extract(downloaded) or ""
        metadata = trafilatura.extract(downloaded, output_format="json")

        # Extract key property data with regex
        result = {
            "url": url,
            "text_length": len(text),
            "prices": re.findall(r'\$[\d,]+(?:\.\d{2})?', text),
            "addresses": re.findall(r'\d+\s+[\w\s]+(?:St|Ave|Blvd|Dr|Ln|Rd|Way|Ct|Pl)\b', text),
            "sqft": re.findall(r'([\d,]+)\s*(?:sq\s*ft|sqft|square feet)', text, re.I),
            "bedrooms": re.findall(r'(\d+)\s*(?:bed|br|bedroom)', text, re.I),
            "bathrooms": re.findall(r'(\d+\.?\d*)\s*(?:bath|ba|bathroom)', text, re.I),
            "raw_text": text[:3000],
        }

        # NLP analysis for sentiment and key phrases
        try:
            from nlp_engine import analyze_text
            analysis = analyze_text(text[:2000])
            result["nlp"] = {
                "key_phrases": analysis.key_phrases[:10],
                "money_amounts": analysis.money_amounts,
                "locations": analysis.locations,
            }
        except Exception:
            pass

        return result

    except Exception as e:
        return {"error": str(e), "url": url}


def scrape_with_browser(url: str, wait_selector: str = "body") -> dict:
    """Full browser scrape with Playwright for JS-heavy sites."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_selector(wait_selector, timeout=10000)

            # Get page content
            content = page.content()
            text = page.inner_text("body")

            # Screenshot for records
            screenshot_dir = Path("/mnt/data/agent-photos") if Path("/mnt/data").exists() else Path("/tmp")
            screenshot_path = screenshot_dir / f"scrape_{int(time.time())}.png"
            page.screenshot(path=str(screenshot_path))

            browser.close()

            return {
                "url": url,
                "text_length": len(text),
                "screenshot": str(screenshot_path),
                "raw_text": text[:5000],
            }

    except Exception as e:
        log.warning(f"Browser scrape failed for {url}: {e}")
        # Fallback to Trafilatura
        return scrape_property_page(url)


def research_property(address: str, city: str = "", state: str = "", county: str = "") -> dict:
    """Research a property by address using multiple sources."""
    results = {
        "address": address,
        "city": city,
        "state": state,
        "county": county,
        "sources": [],
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Source 1: Zillow search (Trafilatura - no browser needed)
    zillow_query = f"{address} {city} {state}".replace(" ", "-")
    zillow_url = f"https://www.zillow.com/homes/{zillow_query}_rb/"
    zillow_data = scrape_property_page(zillow_url)
    if zillow_data.get("text_length", 0) > 100:
        results["sources"].append({"source": "zillow", **zillow_data})
        results["zillow_prices"] = zillow_data.get("prices", [])

    # Source 2: Redfin
    redfin_url = f"https://www.redfin.com/search?q={address} {city} {state}"
    redfin_data = scrape_property_page(redfin_url)
    if redfin_data.get("text_length", 0) > 100:
        results["sources"].append({"source": "redfin", **redfin_data})

    # Combine and score
    all_prices = []
    for src in results["sources"]:
        all_prices.extend(src.get("prices", []))
    if all_prices:
        # Parse prices to numbers
        parsed = []
        for p in all_prices:
            try:
                parsed.append(float(p.replace("$", "").replace(",", "")))
            except ValueError:
                continue
        if parsed:
            results["estimated_value"] = {
                "min": min(parsed),
                "max": max(parsed),
                "median": sorted(parsed)[len(parsed) // 2],
            }

    return results


def enrich_wholesale_lead(lead: dict) -> dict:
    """Full enrichment pipeline for a wholesale lead."""
    address = lead.get("address", "")
    city = lead.get("city", "")
    state = lead.get("state", "")

    if not address:
        return {"error": "no_address"}

    # Research property
    research = research_property(address, city, state)

    # ML scoring
    try:
        from ml_models import get_toolkit
        toolkit = get_toolkit()
        score = toolkit.score_lead({
            "budget": research.get("estimated_value", {}).get("median", 0),
            "urgency": lead.get("urgency", 0.5),
            "is_tech": 0,
            "pain_score": lead.get("motivation_score", 0.5),
            "referral_source": 0.3,
        })
        research["ml_score"] = round(score, 1)
    except Exception:
        pass

    # Log to Blinko
    try:
        import urllib.request
        blinko_payload = {
            "content": (
                f"# Property Research: {address}\n"
                f"#hive/wholesale #hive/rex-blackwell\n\n"
                f"City: {city}, {state}\n"
                f"Sources: {len(research.get('sources', []))}\n"
                f"Est value: {research.get('estimated_value', 'unknown')}\n"
                f"ML Score: {research.get('ml_score', 'n/a')}"
            ),
            "type": 1,
        }
        req = urllib.request.Request(
            "http://localhost:1111/api/v1/note/upsert",
            data=json.dumps(blinko_payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

    return research


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["research", "scrape"])
    parser.add_argument("--address", type=str, default="")
    parser.add_argument("--url", type=str, default="")
    parser.add_argument("--city", type=str, default="")
    parser.add_argument("--state", type=str, default="")
    args = parser.parse_args()

    if args.command == "research" and args.address:
        result = research_property(args.address, args.city, args.state)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "scrape" and args.url:
        result = scrape_property_page(args.url)
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python3 wholesale_property_scraper.py research --address '123 Main St' --city Portland --state OR")
