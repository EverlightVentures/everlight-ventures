#!/usr/bin/env python3
"""
build_chris_fit_list.py -- the yin-yang wheel, stage 3.

Takes the validated TN property universe (ATTOM/Shelby) and produces TWO lists
(operator directive 2026-05-29):
  A) tn_all       -- every TN property we hold
  B) chris_fit    -- the subset that fits Chris Ulander's REAL buy-box
                     (config/chris_buy_box.json v2.0, sourced from his 2026-04-27 email)

Only List B is worth spending O-cent email-discovery effort on -- no point finding
emails for houses Chris won't buy. Stdlib only. Reads leads_db.json (canonical) and
falls back to TN_prospects.csv.

Output: config/_generated/chris_fit_list.json + a console breakdown.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES/Everlight_Ventures/Wholesale"
BUYBOX = WH / "config/chris_buy_box.json"
LEADS_DB = ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
TN_CSV = WH / "prospecting/TN_prospects.csv"
OUT = WH / "config/_generated/chris_fit_list.json"


def _int(v, default=0):
    try:
        return int(float(str(v).replace("$", "").replace(",", "").strip()))
    except Exception:
        return default


def load_tn_leads() -> list[dict]:
    """Prefer leads_db.json TN subset; fall back to TN_prospects.csv."""
    leads: list[dict] = []
    if LEADS_DB.exists():
        d = json.loads(LEADS_DB.read_text())
        rows = d if isinstance(d, list) else d.get("leads", list(d.values()) if isinstance(d, dict) else [])
        leads = [l for l in rows if isinstance(l, dict)
                 and str(l.get("state") or l.get("property_state") or "").upper().strip() == "TN"]
    if not leads and TN_CSV.exists():
        leads = list(csv.DictReader(TN_CSV.open()))
    return leads


def fits_chris(lead: dict, box: dict) -> tuple[bool, str]:
    """Return (fits, reason_if_not). Mirrors chris_buy_box.json v2.0."""
    geo = box["geography"]
    prop = box["property"]
    zips = set(geo["zips"])

    z = str(lead.get("zip") or lead.get("zip_code") or lead.get("owner_mailing_zip") or "").strip()[:5]
    if z not in zips:
        return False, f"zip {z or '?'} not in Chris's 15"

    lead_type = str(lead.get("lead_type") or "").lower()
    is_vacant = "vacant" in lead_type or "lot" in lead_type or "land" in lead_type

    yb = _int(lead.get("year_built"))
    if not is_vacant and yb and yb < prop["min_year_built"]:
        return False, f"built {yb} < {prop['min_year_built']} cutoff"

    arv = _int(lead.get("estimated_arv") or lead.get("county_appraisal") or lead.get("total_appraisal_usd"))
    if arv and not (prop["min_appraisal_usd"] <= arv <= prop["max_appraisal_usd"]):
        return False, f"ARV ${arv:,} outside ${prop['min_appraisal_usd']:,}-${prop['max_appraisal_usd']:,}"

    beds = _int(lead.get("beds"))
    if not is_vacant and beds and not (prop["bedrooms_min"] <= beds <= prop["bedrooms_max"]):
        return False, f"{beds}BR outside {prop['bedrooms_min']}-{prop['bedrooms_max']}"

    return True, ""


def tier(lead: dict) -> str:
    """Within Chris-fit: how reachable + how hot. Reachable = has email now."""
    has_email = bool((lead.get("email") or lead.get("owner_email") or "").strip())
    has_phone = bool((lead.get("phone") or lead.get("owner_phone") or "").strip())
    if has_email:
        return "reachable_email"
    if has_phone:
        return "reachable_phone"
    return "needs_ocent"


def main() -> int:
    box = json.loads(BUYBOX.read_text())
    leads = load_tn_leads()
    fit, miss_reasons = [], {}
    for l in leads:
        ok, why = fits_chris(l, box)
        if ok:
            fit.append(l)
        else:
            key = why.split()[0] if why else "other"
            miss_reasons[key] = miss_reasons.get(key, 0) + 1

    from collections import Counter
    tiers = Counter(tier(l) for l in fit)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "build_chris_fit_list.py | buy-box v2.0 (Chris email 2026-04-27)",
        "tn_total": len(leads),
        "chris_fit_total": len(fit),
        "tiers": dict(tiers),
        "chris_fit": fit,
    }, indent=2, default=str))

    print("=" * 64)
    print("CHRIS-FIT LIST (yin-yang wheel, stage 3)")
    print("=" * 64)
    print(f"TN universe:        {len(leads):5d}")
    print(f"Fits Chris buy-box: {len(fit):5d}")
    print("\nReachability of the Chris-fit list:")
    for t, c in tiers.most_common():
        print(f"  {c:5d}  {t}")
    print("\nWhy the rest missed (top reasons):")
    for r, c in sorted(miss_reasons.items(), key=lambda x: -x[1])[:8]:
        print(f"  {c:5d}  {r}")
    print(f"\nWrote -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
