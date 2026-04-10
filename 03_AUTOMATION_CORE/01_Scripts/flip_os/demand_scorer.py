#!/usr/bin/env python3
"""
Flip OS -- Demand Scoring Engine
For each item in flip_intel, estimates resale value by searching eBay sold
listings and Amazon pricing. Assigns a demand_score (0-100) and margin_pct.

Scoring formula:
  - Base: (est_resale - buy_cost) / est_resale * 100 = margin %
  - demand_score = weighted average of:
      - margin_pct (40%)
      - sell_velocity (how fast similar items sell on eBay) (30%)
      - platform_count (how many platforms it can sell on) (15%)
      - category_bonus (tools, electronics = +15; seasonal = -10) (15%)

Items with demand_score >= 70 and est_resale >= $20 are flagged as "GO".
"""
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ENV_PATH = Path(__file__).resolve().parent.parent.parent / "03_Credentials" / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FlipOS-Scorer] %(message)s")
log = logging.getLogger("flip_os.scorer")

# Category value multipliers
CATEGORY_BONUS = {
    "tools": 15, "electrical": 12, "plumbing": 10, "lighting": 10,
    "appliances": 15, "hardware": 8, "storage": 8, "flooring": 5,
    "outdoor": 10, "garden": 5, "kitchen": 8, "bath": 6,
    "paint": 3, "decor": 3, "seasonal": -5, "unknown": 0, "clearance": 5,
}

# Platform suitability by category
PLATFORM_MAP = {
    "tools": ["ebay", "fb_marketplace", "offerup"],
    "electrical": ["ebay", "amazon", "fb_marketplace"],
    "plumbing": ["ebay", "fb_marketplace"],
    "lighting": ["ebay", "fb_marketplace", "amazon"],
    "appliances": ["fb_marketplace", "offerup", "ebay"],
    "hardware": ["ebay", "fb_marketplace"],
    "storage": ["fb_marketplace", "offerup"],
    "flooring": ["fb_marketplace"],
    "outdoor": ["fb_marketplace", "offerup", "ebay"],
    "garden": ["fb_marketplace", "offerup"],
    "kitchen": ["ebay", "fb_marketplace", "amazon"],
    "bath": ["ebay", "fb_marketplace"],
    "paint": ["fb_marketplace"],
    "decor": ["fb_marketplace", "ebay"],
    "seasonal": ["fb_marketplace", "ebay"],
    "unknown": ["fb_marketplace", "ebay"],
    "clearance": ["fb_marketplace", "ebay"],
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

def supa_select(table: str, params: dict) -> list[dict]:
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supa_headers(), params=params, timeout=8,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error("Select failed: %s", e)
        return []

def supa_update(table: str, row_id: int, data: dict) -> bool:
    try:
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**supa_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{row_id}"},
            json=data,
            timeout=8,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        log.error("Update failed for %s id=%d: %s", table, row_id, e)
        return False

# ---------------------------------------------------------------------------
# Price research via web search
# ---------------------------------------------------------------------------

def search_ebay_sold(item_name: str) -> dict:
    """Search for eBay sold listings to estimate resale value and velocity."""
    try:
        query = f"site:ebay.com sold {item_name} home depot"
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 FlipOS/1.0"},
            timeout=15,
        )
        if not resp.ok:
            return {"est_price": 0, "velocity": 0}

        text = resp.text
        # Look for price patterns in snippets
        prices = re.findall(r"\$(\d{1,4}(?:\.\d{2})?)", text)
        prices = [float(p) for p in prices if 1.0 < float(p) < 500.0]

        if prices:
            avg_price = sum(prices) / len(prices)
            # Velocity: more price hits = more sales = higher velocity
            velocity = min(len(prices) * 10, 100)
            return {"est_price": round(avg_price, 2), "velocity": velocity}
    except Exception as e:
        log.warning("eBay search failed for '%s': %s", item_name, e)

    return {"est_price": 0, "velocity": 0}

def search_amazon_price(item_name: str) -> float:
    """Search Amazon for retail price reference."""
    try:
        query = f"site:amazon.com {item_name}"
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 FlipOS/1.0"},
            timeout=15,
        )
        if resp.ok:
            prices = re.findall(r"\$(\d{1,4}(?:\.\d{2})?)", resp.text)
            prices = [float(p) for p in prices if 5.0 < float(p) < 500.0]
            if prices:
                return round(min(prices), 2)  # Use lowest Amazon price as ceiling
    except Exception as e:
        log.warning("Amazon search failed for '%s': %s", item_name, e)
    return 0.0

# ---------------------------------------------------------------------------
# Score calculation
# ---------------------------------------------------------------------------

def calculate_score(item: dict, ebay_data: dict, amazon_price: float) -> dict:
    """Calculate demand score and pricing for an item."""
    buy_cost = float(item.get("clearance_price") or 0.01)
    category = item.get("category", "unknown")

    # Estimate resale price (eBay avg, Amazon reference, or category estimate)
    est_resale = ebay_data["est_price"]
    if est_resale == 0 and amazon_price > 0:
        est_resale = amazon_price * 0.6  # Can sell at ~60% of Amazon
    if est_resale == 0:
        # Category-based fallback estimate
        fallback = {"tools": 25, "electrical": 20, "lighting": 15, "appliances": 40,
                    "hardware": 12, "outdoor": 20, "kitchen": 18, "plumbing": 15}
        est_resale = fallback.get(category, 10.0)

    # Margin
    margin_pct = ((est_resale - buy_cost) / est_resale * 100) if est_resale > 0 else 0
    margin_pct = min(margin_pct, 99.9)

    # Platform count
    platforms = PLATFORM_MAP.get(category, ["fb_marketplace", "ebay"])
    platform_score = min(len(platforms) * 25, 100)

    # Category bonus
    cat_bonus = CATEGORY_BONUS.get(category, 0)

    # Velocity from eBay
    velocity = ebay_data["velocity"]

    # Weighted demand score
    demand_score = int(
        (margin_pct / 100 * 40) +      # 40% weight on margin
        (velocity / 100 * 30) +          # 30% weight on sell velocity
        (platform_score / 100 * 15) +    # 15% weight on platform options
        cat_bonus                         # 15% category bonus/penalty
    )
    demand_score = max(0, min(demand_score, 100))

    return {
        "est_resale": round(est_resale, 2),
        "demand_score": demand_score,
        "margin_pct": round(margin_pct, 2),
        "platforms": platforms,
    }

# ---------------------------------------------------------------------------
# Main scoring pipeline
# ---------------------------------------------------------------------------

def run_scorer(hours_back: int = 24):
    """Score all unscored flip_intel items from the last N hours."""
    log.info("=== Flip OS Demand Scorer starting ===")

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
    items = supa_select("flip_intel", {
        "select": "*",
        "demand_score": "eq.0",
        "found_date": f"gte.{cutoff}",
        "order": "found_date.desc",
        "limit": "50",
    })

    if not items:
        log.info("No unscored items found in last %d hours", hours_back)
        return []

    log.info("Scoring %d items...", len(items))
    scored = []

    for item in items:
        name = item["item_name"]
        log.info("  Scoring: %s", name[:60])

        # Research pricing
        ebay_data = search_ebay_sold(name)
        amazon_price = search_amazon_price(name)

        # Calculate score
        result = calculate_score(item, ebay_data, amazon_price)

        # Update Supabase
        supa_update("flip_intel", item["id"], result)

        go_flag = "GO" if result["demand_score"] >= 70 and result["est_resale"] >= 20 else "---"
        log.info("    -> Score: %d | Resale: $%.2f | Margin: %.1f%% | %s",
                 result["demand_score"], result["est_resale"], result["margin_pct"], go_flag)

        scored.append({**item, **result})

    # Summary
    go_items = [s for s in scored if s["demand_score"] >= 70 and s["est_resale"] >= 20]
    log.info("=== Scored %d items. %d flagged as GO ===", len(scored), len(go_items))

    return scored


if __name__ == "__main__":
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    scored = run_scorer(hours)

    print(f"\n{'='*60}")
    print(f"SCORED: {len(scored)} items")
    go = [s for s in scored if s["demand_score"] >= 70 and s.get("est_resale", 0) >= 20]
    if go:
        print(f"\nGO ITEMS ({len(go)}):")
        for item in go:
            print(f"  [{item['demand_score']}] {item['item_name'][:50]} -> ${item['est_resale']:.2f} ({item['margin_pct']:.0f}% margin)")
    else:
        print("\nNo GO items this run. Check back tomorrow.")
