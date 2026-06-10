#!/usr/bin/env python3
"""
Flip OS -- Penny Item Scraper v2
Fetches real SKUs from PennyCentral's live penny list, filters for CA items,
scores by retail value (highest margin first), and writes to Supabase flip_intel.

Runs daily at 5 AM PT via cron on Oracle.

Sources:
  1. PennyCentral live penny list (primary -- real SKUs, community-verified)
  2. Web search for Reddit/Facebook community reports (supplementary)
  3. Blinko knowledge base for prior finds

Target stores:
  - HD Vacaville #1043 (510 Orange Dr)
  - HD Fairfield #0637 (2121 Cadenasso Dr)
"""
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# Load env
ENV_PATH = Path(__file__).resolve().parent.parent.parent / "03_Credentials" / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
BLINKO_URL = os.environ.get("BLINKO_URL", "http://e5-mother:1111")  # Oracle E5

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FlipOS] %(message)s")
log = logging.getLogger("flip_os.scraper")

TARGET_STORES = [
    {"name": "HD Vacaville #1043", "city": "Vacaville", "store_id": "1043"},
    {"name": "HD Fairfield #0637", "city": "Fairfield", "store_id": "0637"},
]

CATEGORY_MAP = {
    "generator": "tools", "drill": "tools", "battery": "tools", "saw": "tools",
    "hammer": "tools", "wrench": "tools", "flashlight": "tools", "bit": "tools",
    "cordless": "tools", "compressor": "tools", "splitter": "tools", "blade": "tools",
    "vanity": "bath", "shower": "bath", "faucet": "kitchen", "sink": "kitchen",
    "trash can": "kitchen", "light": "lighting", "sconce": "lighting", "lumen": "lighting",
    "led": "lighting", "headlight": "lighting", "lamp": "lighting",
    "ac": "appliances", "mini split": "appliances", "heater": "appliances",
    "gutter": "hardware", "flag": "hardware", "adhesive": "hardware",
    "tiki": "outdoor", "fire pit": "outdoor", "grill": "outdoor",
    "pruning": "garden", "shears": "garden", "mower": "garden", "hose": "garden",
    "carpet": "flooring", "tile": "flooring", "plank": "flooring",
    "paint": "paint", "stain": "paint",
}

PLATFORM_MAP = {
    "tools": ["fb_marketplace", "ebay", "offerup"],
    "bath": ["fb_marketplace", "ebay"],
    "kitchen": ["fb_marketplace", "ebay", "amazon"],
    "lighting": ["fb_marketplace", "ebay", "amazon"],
    "appliances": ["fb_marketplace", "offerup", "ebay"],
    "hardware": ["fb_marketplace", "ebay"],
    "outdoor": ["fb_marketplace", "offerup"],
    "garden": ["fb_marketplace", "ebay"],
    "flooring": ["fb_marketplace"],
    "paint": ["fb_marketplace"],
    "unknown": ["fb_marketplace", "ebay"],
}


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def supa_headers():
    return {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

def supa_insert(table: str, rows: list[dict]) -> bool:
    if not rows:
        return True
    try:
        resp = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**supa_headers(), "Prefer": "return=minimal"},
            json=rows, timeout=10,
        )
        resp.raise_for_status()
        log.info("Inserted %d rows into %s", len(rows), table)
        return True
    except Exception as e:
        log.error("Supabase insert failed for %s: %s", table, e)
        return False

def supa_select(table: str, params: dict) -> list[dict]:
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supa_headers(), params=params, timeout=8,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error("Supabase select failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Detect category from item name
# ---------------------------------------------------------------------------

def detect_category(name: str) -> str:
    name_lower = name.lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in name_lower:
            return cat
    return "unknown"


# ---------------------------------------------------------------------------
# Fetch PennyCentral live list via web fetch
# ---------------------------------------------------------------------------

def fetch_pennycentral() -> list[dict]:
    """Fetch the PennyCentral live penny list page and parse items."""
    log.info("Fetching PennyCentral live penny list...")
    items = []

    try:
        resp = requests.get(
            "https://www.pennycentral.com/penny-list",
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) FlipOS/2.0"},
            timeout=20,
        )
        if not resp.ok:
            log.warning("PennyCentral returned %d", resp.status_code)
            return items

        text = resp.text

        # Parse SKU patterns from the page
        # PennyCentral typically shows: SKU | Item Name | Price | Retail | States | Reports
        # Try multiple parsing patterns

        # Pattern 1: Look for SKU-like numbers followed by item descriptions
        sku_pattern = re.compile(
            r'(\d{3,4}-\d{3}(?:-\d{3})?)\s*[|\-]\s*(.+?)(?:\$0\.01|\$\.01)',
            re.IGNORECASE
        )

        # Pattern 2: Structured data in table rows or divs
        row_pattern = re.compile(
            r'(\d{3,4}-\d{3,4}(?:-\d{3,4})?)[^$]*?\$(\d+(?:\.\d{2})?)',
            re.IGNORECASE
        )

        # Pattern 3: JSON-LD or structured data
        json_blocks = re.findall(r'(?:data|items|products)\s*[:=]\s*(\[.+?\])', text, re.DOTALL)
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if isinstance(parsed, list):
                    for entry in parsed:
                        if isinstance(entry, dict) and ("sku" in entry or "SKU" in entry):
                            sku = entry.get("sku") or entry.get("SKU", "")
                            name = entry.get("name") or entry.get("title") or entry.get("description", "")
                            retail = entry.get("retail") or entry.get("price") or entry.get("originalPrice", 0)
                            states = entry.get("states") or entry.get("locations", "")
                            reports = entry.get("reports") or entry.get("confirmations", 0)
                            if sku and name:
                                items.append({
                                    "sku": str(sku),
                                    "name": str(name)[:200],
                                    "retail": float(retail) if retail else 0,
                                    "states": str(states) if isinstance(states, str) else ",".join(states) if isinstance(states, list) else "",
                                    "reports": int(reports) if reports else 0,
                                })
            except (json.JSONDecodeError, ValueError):
                continue

        # Pattern 4: Regex fallback for any SKU + price combos in the HTML
        if not items:
            for match in row_pattern.finditer(text):
                sku = match.group(1)
                price = float(match.group(2))
                # Get surrounding context for item name
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = re.sub(r'<[^>]+>', ' ', text[start:end]).strip()
                # Clean up name
                name = context[:100].strip()
                items.append({
                    "sku": sku,
                    "name": name,
                    "retail": price,
                    "states": "",
                    "reports": 0,
                })

        log.info("PennyCentral: parsed %d items from page", len(items))

    except Exception as e:
        log.error("PennyCentral fetch failed: %s", e)

    return items


# ---------------------------------------------------------------------------
# Web search for supplementary penny intel
# ---------------------------------------------------------------------------

def search_web(query: str, max_results: int = 10) -> list[dict]:
    results = []
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 14) FlipOS/2.0"},
            timeout=15,
        )
        if resp.ok:
            blocks = re.findall(
                r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
                r'class="result__snippet"[^>]*>(.*?)</span>',
                resp.text, re.DOTALL
            )
            for url, title, snippet in blocks[:max_results]:
                title = re.sub(r"<[^>]+>", "", title).strip()
                snippet = re.sub(r"<[^>]+>", "", snippet).strip()
                # Extract any SKUs from the snippet
                skus = re.findall(r'\d{3,4}-\d{3,4}(?:-\d{3,4})?', f"{title} {snippet}")
                results.append({
                    "url": url, "title": title, "snippet": snippet,
                    "skus": skus,
                })
    except Exception as e:
        log.warning("Web search failed: %s", e)
    return results


def extract_sku_items_from_search(results: list[dict]) -> list[dict]:
    """Extract items with SKUs from web search results."""
    items = []
    for r in results:
        for sku in r.get("skus", []):
            text = f"{r['title']} {r['snippet']}"
            # Try to find a price near the SKU
            prices = re.findall(r'\$(\d+(?:\.\d{2})?)', text)
            retail = max([float(p) for p in prices if float(p) > 1], default=0)
            items.append({
                "sku": sku,
                "name": r["title"][:200],
                "retail": retail,
                "states": "",
                "reports": 0,
                "source_url": r.get("url", ""),
            })
    return items


# ---------------------------------------------------------------------------
# Main scraper pipeline
# ---------------------------------------------------------------------------

def run_scraper():
    log.info("=== Flip OS Penny Scraper v2 starting ===")
    all_items = []

    # 1. Fetch PennyCentral live list (primary source)
    pc_items = fetch_pennycentral()
    all_items.extend(pc_items)

    # 2. Supplementary web searches for SKU-specific intel
    searches = [
        "Home Depot penny items this week SKU California 2026",
        "site:reddit.com/r/HomeDepot penny $0.01 SKU",
        "Home Depot clearance penny list California April 2026",
    ]
    for query in searches:
        log.info("Searching: %s", query)
        results = search_web(query)
        sku_items = extract_sku_items_from_search(results)
        all_items.extend(sku_items)
        log.info("  -> %d SKU items extracted", len(sku_items))

    # 3. Deduplicate by SKU
    seen_skus = set()
    unique_items = []
    for item in all_items:
        sku = item.get("sku", "")
        if sku and sku not in seen_skus:
            seen_skus.add(sku)
            unique_items.append(item)

    log.info("Total unique SKU items: %d", len(unique_items))

    # 4. Check which SKUs we already have
    existing = supa_select("flip_intel", {
        "select": "item_sku",
        "source": "eq.pennycentral",
        "acted_on": "eq.false",
    })
    existing_skus = {r["item_sku"] for r in existing if r.get("item_sku")}
    new_items = [i for i in unique_items if i.get("sku") not in existing_skus]
    log.info("New SKUs (not already in DB): %d", len(new_items))

    # 5. Build Supabase rows
    rows = []
    for item in new_items:
        retail = item.get("retail", 0)
        ca_confirmed = "CA" in item.get("states", "")
        category = detect_category(item.get("name", ""))
        margin = ((retail - 0.01) / retail * 100) if retail > 0 else 0
        platforms = PLATFORM_MAP.get(category, ["fb_marketplace", "ebay"])

        # Score: CA priority + retail value + community reports
        reports = item.get("reports", 0)
        score = int(min(99,
            (margin / 100 * 30) +
            (min(reports, 20) * 2) +
            (30 if ca_confirmed else 0) +
            min(retail / 20, 20)
        ))

        rows.append({
            "source": "pennycentral",
            "store": TARGET_STORES[0]["name"] if ca_confirmed else None,
            "item_name": item.get("name", "Unknown")[:200],
            "item_sku": item.get("sku"),
            "original_price": retail if retail > 0 else None,
            "clearance_price": 0.01,
            "penny_confirmed": True,
            "category": category,
            "est_resale": round(retail * 0.5, 2) if retail > 0 else None,
            "demand_score": score,
            "margin_pct": round(margin, 2) if margin > 0 else None,
            "platforms": platforms,
            "source_url": item.get("source_url", "https://www.pennycentral.com/penny-list"),
            "notes": f"PennyCentral. States: {item.get('states', 'unknown')}. Reports: {reports}. {'CA CONFIRMED' if ca_confirmed else 'Check in-store'}",
            "acted_on": False,
        })

    # 6. Sort by score (highest first) before insert
    rows.sort(key=lambda x: x.get("demand_score", 0), reverse=True)

    # 7. Write to Supabase
    if rows:
        supa_insert("flip_intel", rows)

    # 8. Log to Blinko
    try:
        ca_rows = [r for r in rows if r.get("store")]
        summary = f"# Flip OS Scraper v2 Run\n#hive/flip-os #hive/penny\n\n"
        summary += f"Date: {datetime.now(timezone.utc).isoformat()}\n"
        summary += f"Total SKUs found: {len(unique_items)}\n"
        summary += f"New SKUs added: {len(rows)}\n"
        summary += f"CA confirmed: {len(ca_rows)}\n\n"
        summary += "Top items:\n"
        for r in rows[:10]:
            summary += f"- SKU {r['item_sku']} | ${r.get('original_price', '?')} | {r['item_name'][:40]}\n"

        requests.post(
            f"{BLINKO_URL}/api/v1/note/upsert",
            json={"content": summary, "type": 1},
            timeout=8,
        )
    except Exception:
        pass

    # 9. Print hunt list
    if rows:
        print(f"\n{'='*70}")
        print(f"DAILY SKU HUNT LIST -- {len(rows)} items (highest margin first)")
        print(f"{'='*70}")
        ca = [r for r in rows if r.get("store")]
        other = [r for r in rows if not r.get("store")]
        for label, group in [("CA CONFIRMED -- GO HUNT", ca), ("OTHER STATES -- may appear", other)]:
            if group:
                print(f"\n--- {label} ---")
                for r in group[:15]:
                    print(f"  SKU {r['item_sku']:>15s} | ${r.get('original_price',0):>8.2f} -> ~${r.get('est_resale',0):>7.2f} | Score:{r['demand_score']:>3d} | {r['item_name'][:40]}")

    log.info("=== Scraper v2 complete: %d new SKUs ===", len(rows))
    return rows


if __name__ == "__main__":
    items = run_scraper()
    print(f"\nTotal: {len(items)} new items loaded. Dashboard at :8504/flip/")
