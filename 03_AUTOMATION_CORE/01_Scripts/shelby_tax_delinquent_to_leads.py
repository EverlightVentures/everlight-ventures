"""
shelby_tax_delinquent_to_leads.py -- Memphis lead supply for Chris.

Pipeline:
1. Download Shelby County Tax Sale Extract CSV (2,630+ delinquent properties)
2. For each address, POST to assessor /AddressSubmit to get owner_name, zip,
   year_built, property class, beds, sqft
3. Filter to Chris's 15 Memphis zips + Chris's box (2-4BR SFR, 1940+ build)
4. Write matching leads to wholesale_agent/leads_db.json with status='new',
   queue='needs_enrichment' (no email/phone yet -- skip-trace later)
5. Run match_to_buyer.py to score against MSHB buy box
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
TAX_CSV = Path("/tmp/TaxSaleExtract.csv")
TAX_CSV_URL = "https://scgpublic.s3.amazonaws.com/TaxSaleExtract.csv"
ASSESSOR_POST = "https://www.assessormelvinburgess.com/AddressSubmit"
LOG_DIR = WORKSPACE / "_logs/cl_scrape"

UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"

# Chris's Memphis buy box zips
CHRIS_MEMPHIS_ZIPS = {
    "38127","38128","38134","38117","38111","38141","38115","38118",
    "38116","38109","38104","38122","38107","38114","38106",
}


def fetch_tax_csv() -> Path:
    if TAX_CSV.exists() and TAX_CSV.stat().st_size > 100000:
        return TAX_CSV  # Use cached
    print(f"Downloading {TAX_CSV_URL}")
    urllib.request.urlretrieve(TAX_CSV_URL, str(TAX_CSV))
    return TAX_CSV


def load_tax_rows(path: Path) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({
                "parcel_id": (r.get("ParcelID") or "").strip(),
                "alt_parcel": (r.get("Alt_Parcel") or "").strip(),
                "street_number": (r.get("Street Number") or "").strip(),
                "street_name": (r.get("Street Name") or "").strip(),
                "tax_sale": (r.get("Tax Sale") or "").strip(),
                "register_url": (r.get("Register GIS") or "").strip(),
            })
    return rows


def lookup_assessor(street_number: str, street_name: str) -> dict:
    """POST to assessor and parse property detail.

    Returns: {owner_name, zip, year_built, sqft, bedrooms, property_class, address_full}
    or {} if not found.
    """
    data = urllib.parse.urlencode({
        "stNumber": street_number,
        "stName": street_name.strip(),
        "page": "1",
    }).encode()
    req = urllib.request.Request(
        ASSESSOR_POST,
        data=data,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml",
            "Origin": "https://www.assessormelvinburgess.com",
            "Referer": "https://www.assessormelvinburgess.com/propertySearch",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)[:60]}

    soup = BeautifulSoup(html, "lxml")
    out = {}

    # Different assessor sites surface data differently. Try common patterns.
    # 1. Find the result table (Shelby usually has a table with property rows)
    tables = soup.find_all("table")
    for tbl in tables:
        rows = tbl.find_all("tr")
        if len(rows) < 2:
            continue
        for tr in rows[1:]:  # skip header
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            if not cells:
                continue
            # Heuristic: parcel + address + owner pattern (5-7 cells)
            joined = " | ".join(cells)
            if any(re.match(r"\d{6}", c) for c in cells):  # parcel-like
                out["row_cells"] = cells
                # Common Shelby column order: parcel, address, owner, ...
                # We'll grab owner-shaped cell (ALL CAPS, 2+ words)
                for c in cells:
                    if re.match(r"^[A-Z][A-Z &',\.\-]+ [A-Z]", c) and "TN" not in c and not c.startswith("38"):
                        if "owner_name" not in out:
                            out["owner_name"] = c
                            break
                break
        if out.get("owner_name"):
            break

    # 2. Pull standalone fields by label search
    text = soup.get_text(" ", strip=True)
    for label, key in [
        (r"Year Built[:\s]+(\d{4})", "year_built"),
        (r"Square Feet[:\s]+([\d,]+)", "sqft"),
        (r"Bedrooms?[:\s]+(\d+)", "bedrooms"),
        (r"Bathrooms?[:\s]+(\d+(?:\.\d)?)", "bathrooms"),
        (r"Property Class[:\s]+([A-Za-z0-9 \-/]+)", "property_class"),
        (r"\b(38\d{3})\b", "zip"),
    ]:
        m = re.search(label, text)
        if m:
            out[key] = m.group(1).strip()

    # 3. Look for explicit Property Address with zip
    m_addr = re.search(r"Property Address[:\s]+(\d+\s+[A-Z0-9 .'-]+),?\s*MEMPHIS,?\s*TN\s*(\d{5})", text, re.IGNORECASE)
    if m_addr:
        out["address_full"] = m_addr.group(1).strip()
        out["zip"] = m_addr.group(2)

    return out


def matches_chris_box(detail: dict) -> tuple[bool, str]:
    """Filter against Chris's Memphis buy box."""
    z = detail.get("zip", "")
    if z not in CHRIS_MEMPHIS_ZIPS:
        return False, f"zip_{z}_not_in_chris_box"

    yr = detail.get("year_built")
    if yr:
        try:
            if int(yr) < 1940:
                return False, f"year_{yr}_below_1940"
        except (TypeError, ValueError):
            pass

    bd = detail.get("bedrooms")
    if bd:
        try:
            b = int(bd)
            if b < 2 or b > 4:
                return False, f"beds_{b}_not_2_to_4"
        except (TypeError, ValueError):
            pass

    pc = (detail.get("property_class") or "").upper()
    if pc and ("SINGLE" in pc or "RES" in pc or "SFR" in pc or "RESIDENTIAL" in pc):
        return True, "passes_chris_box"
    if pc:
        return False, f"property_class_{pc[:30]}_not_SFR"

    # If no explicit class but has bedrooms 2-4, accept
    if detail.get("bedrooms"):
        return True, "passes_chris_box_inferred_SFR"

    return False, "insufficient_data"


def main():
    limit = int(os.environ.get("LIMIT", "200"))
    print(f"=== Shelby tax-delinquent -> Chris match ===")
    print(f"Limit: {limit} parcels (env LIMIT to override)")

    csv_path = fetch_tax_csv()
    rows = load_tax_rows(csv_path)
    print(f"Loaded {len(rows)} tax-delinquent parcels from CSV")

    matches = []
    blocked = []
    errors = []
    sampled = 0

    for i, row in enumerate(rows[:limit]):
        sampled += 1
        if not row["street_number"] or not row["street_name"]:
            continue

        detail = lookup_assessor(row["street_number"], row["street_name"])
        if "error" in detail:
            errors.append({"row": row, "error": detail["error"]})
            continue

        passed, reason = matches_chris_box(detail)
        record = {**row, "detail": detail, "match_reason": reason}
        if passed:
            matches.append(record)
            print(f"  [{i+1:>4}] MATCH zip={detail.get('zip','?')} yr={detail.get('year_built','?')} bd={detail.get('bedrooms','?')} owner={detail.get('owner_name','?')[:30]} | {row['street_number']} {row['street_name'].strip()}")
        else:
            blocked.append(record)
            if i % 25 == 0:
                print(f"  [{i+1:>4}] {reason} | {row['street_number']} {row['street_name'].strip()}")

        time.sleep(0.5)  # courtesy delay

    print()
    print(f"=== SUMMARY ===")
    print(f"Sampled: {sampled} of {len(rows)}")
    print(f"Matches Chris's box: {len(matches)}")
    print(f"Blocked: {len(blocked)}")
    print(f"Errors: {len(errors)}")

    # Write matches to leads_db
    if matches:
        existing = json.loads(LEADS_DB.read_text()) if LEADS_DB.exists() else []
        existing_addrs = {(l.get("address") or "").upper() for l in existing}
        added = 0
        for m in matches:
            d = m["detail"]
            addr = d.get("address_full") or f"{m['street_number']} {m['street_name'].strip()}, MEMPHIS, TN {d.get('zip','')}"
            if addr.upper() in existing_addrs:
                continue
            lead = {
                "address": addr,
                "city": "Memphis",
                "state": "TN",
                "zip_code": d.get("zip", ""),
                "lead_type": "tax_lien",
                "source": "shelby_tax_delinquent_csv_2026-04-28",
                "source_url": m.get("register_url", ""),
                "status": "new",
                "outreach_count": 0,
                "sequence_step": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "owner_name": d.get("owner_name", ""),
                "year_built": int(d["year_built"]) if d.get("year_built","").isdigit() else None,
                "bedrooms": int(d["bedrooms"]) if d.get("bedrooms","").isdigit() else None,
                "sqft": d.get("sqft", "").replace(",", ""),
                "property_class": d.get("property_class", ""),
                "parcel_id": m.get("parcel_id", ""),
                "tax_sale_marker": m.get("tax_sale", ""),
                "queue": "needs_enrichment",  # no email/phone yet
                "match_reason": m["match_reason"],
            }
            existing.append(lead)
            existing_addrs.add(addr.upper())
            added += 1
        LEADS_DB.write_text(json.dumps(existing, indent=2, default=str))
        print(f"Added {added} new Chris-matching tax-delinquent leads to leads_db ({len(existing)} total)")

    # Audit
    audit_path = LOG_DIR / f"shelby_tax_match_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "sampled": sampled,
        "matches_count": len(matches),
        "blocked_count": len(blocked),
        "errors_count": len(errors),
        "match_reasons": dict([(m["match_reason"], 1) for m in matches]),
        "blocked_reasons_top": dict(),
    }, default=str, indent=2))
    print(f"Audit: {audit_path}")


if __name__ == "__main__":
    main()
