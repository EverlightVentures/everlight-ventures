"""
match_to_buyer.py -- Score wholesale leads against an InvestorBuyer's buy box.

For every property in leads_db.json, compute a match-score against each active
buyer's buy_box. Highest-score buyers get the deal first.

Initial buyer: Chris Ulander @ Mid South Homebuyers (Memphis + Little Rock).

Match dimensions:
- zip in buyer's zip list (HARD requirement -- skip if not)
- bedrooms in range
- price in range
- build year >= cutoff
- construction type acceptable
- condition acceptable
- not in blocked submarket
- vacant_lot bonus if buyer takes lots

Score: 0-100. >=70 = ship to buyer immediately. 40-69 = enrich + maybe ship.
<40 = not a fit for this buyer, score against next buyer.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
BUYERS_DB = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/buyers/buyers_db.json"


def parse_zip(addr: str, explicit_zip: str = "") -> str:
    if explicit_zip:
        return str(explicit_zip).strip()[:5]
    if not addr:
        return ""
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", addr)
    return m.group(1) if m else ""


def in_zip_list(zip_code: str, zip_list: list[str]) -> bool:
    return zip_code in {str(z) for z in (zip_list or [])}


def match_buy_box(lead: dict, buy_box: dict) -> tuple[int, list[str], list[str]]:
    """Return (score 0-100, matched_reasons, blocked_reasons)."""
    score = 0
    matched = []
    blocked = []

    zip_code = parse_zip(lead.get("address", ""), lead.get("zip_code", ""))

    # ZIP is HARD requirement -- if not in list, skip
    if buy_box.get("zip_codes"):
        if not zip_code:
            blocked.append("no_zip_to_match")
            return 0, matched, blocked
        if not in_zip_list(zip_code, buy_box["zip_codes"]):
            blocked.append(f"zip_{zip_code}_not_in_buyer_list")
            return 0, matched, blocked
        matched.append(f"zip_{zip_code}_in_list")
        score += 20

    # Submarket-blocked check (Little Rock NLR/Benton)
    submarkets_blocked = buy_box.get("submarkets_blocked", [])
    city = (lead.get("city") or "").upper()
    addr = (lead.get("address") or "").upper()
    for sm in submarkets_blocked:
        if sm.upper() in city or sm.upper() in addr:
            blocked.append(f"submarket_{sm}_blocked")
            return 0, matched, blocked

    # Bedrooms
    bed = lead.get("bedrooms")
    if bed is not None:
        bed = int(bed) if isinstance(bed, (int, float, str)) and str(bed).isdigit() else None
    if bed and buy_box.get("bedrooms_min"):
        if bed < buy_box["bedrooms_min"]:
            blocked.append(f"bedrooms_{bed}_below_min_{buy_box['bedrooms_min']}")
            return 0, matched, blocked
        if buy_box.get("bedrooms_max") and bed > buy_box["bedrooms_max"]:
            blocked.append(f"bedrooms_{bed}_above_max_{buy_box['bedrooms_max']}")
            return 0, matched, blocked
        matched.append(f"bedrooms_{bed}_in_range")
        score += 15
    elif bed is None and buy_box.get("bedrooms_min"):
        # Unknown -- partial credit, still ship
        score += 5

    # Price
    asking = lead.get("asking_price") or 0
    try:
        asking = float(asking)
    except (TypeError, ValueError):
        asking = 0
    if asking > 0 and buy_box.get("price_max_usd"):
        if asking > buy_box.get("price_max_stretch_usd", buy_box["price_max_usd"]):
            blocked.append(f"price_{int(asking)}_above_stretch_max")
            return 0, matched, blocked
        if asking <= buy_box["price_max_usd"]:
            score += 20
            matched.append(f"price_{int(asking)}_in_typical_range")
        else:
            score += 10  # In stretch range
            matched.append(f"price_{int(asking)}_in_stretch_range")
        # Bonus if in their sweet-spot range
        if (buy_box.get("price_typical_low_usd", 0) <= asking <= buy_box.get("price_typical_high_usd", 0)):
            score += 10
            matched.append("price_in_sweet_spot_30-60k")

    # Build year
    yr = lead.get("year_built")
    if yr and buy_box.get("build_year_min"):
        try:
            yr = int(yr)
            if yr < buy_box["build_year_min"]:
                blocked.append(f"build_year_{yr}_below_cutoff_{buy_box['build_year_min']}")
                return 0, matched, blocked
            score += 10
            matched.append(f"build_year_{yr}_above_cutoff")
        except (TypeError, ValueError):
            pass

    # Construction
    construction = (lead.get("construction") or "").lower()
    if construction and buy_box.get("construction_pref"):
        if construction == buy_box["construction_pref"].lower():
            score += 5
            matched.append("construction_brick_preferred")
        elif construction in (buy_box.get("construction_acceptable") or []):
            score += 2
            matched.append("construction_acceptable")

    # Condition
    cond = (lead.get("condition") or lead.get("lead_type") or "").lower()
    if cond:
        if any(c in cond for c in ["distressed", "fixer", "needs_repair", "code_violation", "tax_lien", "probate", "pre_foreclos"]):
            if "distressed" in (buy_box.get("condition_acceptable") or []) or "needs_repair" in (buy_box.get("condition_acceptable") or []):
                score += 10
                matched.append(f"condition_{cond}_acceptable")
        elif "livable" in cond and "livable" in (buy_box.get("condition_acceptable") or []):
            score += 5
            matched.append("condition_livable")

    # Vacant lot bonus
    if "vacant_lot" in (lead.get("property_type") or "").lower() and buy_box.get("vacant_lots_accepted"):
        score += 15
        matched.append("vacant_lot_buyer_accepts_citywide")

    # Cap at 100
    score = min(100, score)
    return score, matched, blocked


def match_lead_to_all_buyers(lead: dict, buyers: list[dict]) -> list[dict]:
    """For one lead, score against every active buyer. Return list sorted by score."""
    matches = []
    state = (lead.get("state") or "").upper()
    for b in buyers:
        if b.get("status") != "active_buyer":
            continue
        # Buy box per market -- pick the one matching lead's state
        market_box = None
        market_name = None
        if state == "TN" and "memphis" in b.get("buy_box", {}):
            market_box = b["buy_box"]["memphis"]
            market_name = "memphis"
        elif state == "AR" and "little_rock" in b.get("buy_box", {}):
            market_box = b["buy_box"]["little_rock"]
            market_name = "little_rock"
        if not market_box:
            continue
        score, matched, blocked = match_buy_box(lead, market_box)
        matches.append({
            "buyer_id": b.get("id"),
            "buyer_company": b.get("company"),
            "buyer_email": b.get("deal_inbox") or b.get("email"),
            "market": market_name,
            "score": score,
            "matched": matched,
            "blocked": blocked,
        })
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


def main():
    if not LEADS_DB.exists() or not BUYERS_DB.exists():
        print("FATAL: leads_db or buyers_db missing", file=sys.stderr)
        sys.exit(1)

    leads = json.loads(LEADS_DB.read_text())
    buyers = json.loads(BUYERS_DB.read_text())
    print(f"Leads: {len(leads)}, Buyers: {len(buyers)}")

    # For each lead, compute buyer matches
    high_score_matches = []
    for lead in leads:
        matches = match_lead_to_all_buyers(lead, buyers)
        # Attach to lead for future reference
        lead["buyer_matches"] = matches
        if matches and matches[0]["score"] >= 70:
            high_score_matches.append((lead, matches[0]))

    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

    # Summary
    print(f"\n=== HIGH-SCORE MATCHES (>=70 to a buyer) ===")
    print(f"Count: {len(high_score_matches)}")
    high_score_matches.sort(key=lambda x: x[1]["score"], reverse=True)
    for lead, m in high_score_matches[:20]:
        addr = (lead.get("address") or "")[:40]
        print(f"  score={m['score']:3} | {addr:<40} | -> {m['buyer_company']} ({m['market']})")
        if lead.get("owner_email"):
            print(f"      seller: {lead['owner_email']}")
        if m["matched"]:
            print(f"      matched: {', '.join(m['matched'][:5])}")

    # Memphis-specific count (any score, even 0)
    memphis_zips = ["38127","38128","38134","38117","38111","38141","38115","38118","38116","38109","38104","38122","38107","38114","38106"]
    memphis_in_db = [l for l in leads if parse_zip(l.get("address",""), l.get("zip_code","")) in memphis_zips]
    print(f"\n=== Memphis (Chris-buy-box-zips) leads currently in DB: {len(memphis_in_db)} ===")
    for l in memphis_in_db[:10]:
        print(f"  {(l.get('address') or '')[:50]} | source={l.get('source','?')[:30]}")


if __name__ == "__main__":
    main()
