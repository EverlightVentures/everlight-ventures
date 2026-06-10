"""
gen_psa.py -- one-liner PSA generation for a wholesale deal.

Reads the prefill JSON, extracts the deal by parcel_id, sets
tn_sb909_acknowledged=True (required for TN), generates the PDF.

Usage:
    python3 -m gen_psa "035093  00032"           # by parcel
    python3 03_AUTOMATION_CORE/01_Scripts/gen_psa.py "035093  00032"

Prerequisites:
    - /Wholesale/contracts/psa_prefill_2026-04-29.json must exist (Henry generated)
    - /Broker_OS/contract_generator.py must be importable
    - The lead must have its 4-blocker resolved before this fires
      (estate authority, church trustee, ministry officer, mailing zip)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
PREFILL = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/contracts/psa_prefill_2026-04-29.json"

sys.path.insert(0, str(WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS"))
from contract_generator import generate_wholesale_contract


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gen_psa.py '<parcel_id>'")
        print("Example: python3 gen_psa.py '035093  00032'")
        sys.exit(1)

    parcel = sys.argv[1].strip()
    if not PREFILL.exists():
        print(f"ERROR: prefill not found at {PREFILL}")
        sys.exit(1)

    prefill = json.loads(PREFILL.read_text())
    leads = prefill.get("leads", [])

    # Henry's prefill is a list -- find by parcel_id
    deal_raw = next((l for l in leads if (l.get("parcel_id") or "").strip() == parcel), None)
    if not deal_raw:
        print(f"ERROR: parcel '{parcel}' not in prefill.")
        print(f"Available parcels:")
        for l in leads:
            print(f"  {(l.get('parcel_id') or '?').strip():18} -- {l.get('property_address','?')}")
        sys.exit(1)

    common = prefill.get("common", {})

    # Translate Henry's prefill schema -> contract_generator schema
    addr = deal_raw.get('property_address', '?').strip()
    if 'MEMPHIS' not in addr.upper():
        addr = f"{addr}, MEMPHIS, {deal_raw.get('state','TN')}"
    deal = {
        "property_address": addr,
        "seller_name": deal_raw.get("seller_full_legal_name") or deal_raw.get("seller_name", "?"),
        "seller_email": deal_raw.get("seller_email", "[TBD -- fill before sending PDF]"),
        "buyer_name": common.get("buyer_legal_name", "Richard Gee, an individual doing business as Everlight Ventures"),
        "buyer_email": common.get("buyer_email", "rich@everlightventures.io"),
        "purchase_price": deal_raw.get("suggested_purchase_price_usd") or deal_raw.get("purchase_price", 0),
        "assignment_fee": deal_raw.get("suggested_assignment_fee_usd") or deal_raw.get("assignment_fee", 0),
        "earnest_money": deal_raw.get("suggested_emd_usd") or deal_raw.get("earnest_money", 100),
        "closing_date": deal_raw.get("suggested_close_date") or common.get("default_close_date", "TBD"),
        "title_company": common.get("title_company_default", "Mid-South Title (Memphis, TN)"),
        "inspection_days": common.get("inspection_days_default", 14),
        "state": deal_raw.get("state", "TN"),
        "tn_sb909_acknowledged": True,  # required for TN -- generator refuses without it
    }

    print(f"Generating PSA for {parcel}:")
    print(f"  Property: {deal['property_address']}")
    print(f"  Seller:   {deal['seller_name']}")
    print(f"  Price:    ${deal['purchase_price']:,}")
    print(f"  Fee:      ${deal['assignment_fee']:,}")
    print(f"  EMD:      ${deal['earnest_money']:,}")
    print(f"  State:    {deal['state']}  (SB 909 ack: {deal['tn_sb909_acknowledged']})")
    print()

    pdf_path = generate_wholesale_contract(deal)
    print(f"PDF generated: {pdf_path}")
    print()
    print("Next steps:")
    print("  1. Upload PDF to Documenso (or sign it manually + email)")
    print("  2. Add seller email signature block")
    print("  3. Send for e-signature")
    print("  4. When seller signs: wire $100 EMD to Mid-South Title")
    print("  5. Package + send to Chris (or backup buyer)")


if __name__ == "__main__":
    main()
