"""Deal Prep Engine -- Pre-packages complete deals before ANY contact.

When we call a seller, we already have:
  - Property research done
  - Title company selected for their city
  - Assignment contract generated with "Quality Assurance Review Period"
  - Buyer matched from our database
  - Investment pitch ready for the buyer
  - Everything in a beautiful HTML presentation

When we call a buyer, we already have:
  - Full deal sheet with numbers
  - Contract ready for signature
  - Title company ready to close
  - All they need to say is "yes"

USES EXISTING TEMPLATES:
  - deal_sheet_preview.html (buyer presentation)
  - ASSIGNMENT_CONTRACT_BASE.md (contract template)
  - title_companies.json (pre-vetted per market)
  - STATE_ADDENDA.md (state compliance)
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

# Template paths
TEMPLATES_DIR = Path("/home/opc/hive_action_engine/templates")
TEMPLATES_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path("/home/opc/hive_action_engine/deal_packages")
OUTPUT_DIR.mkdir(exist_ok=True)

# Title companies (loaded from existing JSON)
TITLE_COMPANIES_PATH = Path("/home/opc/hive_action_engine/title_companies.json")

# City to market mapping
CITY_TO_MARKET = {
    "atlanta": "atlanta", "augusta": "atlanta", "savannah": "atlanta", "macon": "atlanta",
    "dallas": "dallas", "houston": "dallas", "san antonio": "dallas", "fort worth": "dallas", "austin": "dallas",
    "cleveland": "cleveland", "columbus": "cleveland", "cincinnati": "cleveland", "dayton": "cleveland",
    "charlotte": "charlotte", "raleigh": "charlotte", "greensboro": "charlotte", "durham": "charlotte",
    "st. louis": "st_louis", "st louis": "st_louis", "kansas city": "st_louis",
    "jacksonville": "jacksonville", "tampa": "jacksonville", "orlando": "jacksonville", "miami": "jacksonville",
    "memphis": "jacksonville", "nashville": "jacksonville",  # TN mapped to closest
    "phoenix": "dallas", "tucson": "dallas",  # AZ mapped to national
}

# State inspection periods
STATE_INSPECTION_DAYS = {
    "FL": 15, "TX": 10, "OH": 15, "GA": 10, "TN": 10,
    "AZ": 10, "NC": 15, "MO": 10, "NV": 10, "IN": 10,
}


def _sb_get(table, params=""):
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    except Exception:
        return []


def _sb_insert(table, records):
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    req = urllib.request.Request(url, json.dumps(records if isinstance(records, list) else [records]).encode(), method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    except Exception as e:
        return {"error": str(e)}


def _sb_update(table, match_col, match_val, updates):
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/{table}?{match_col}=eq.{match_val}"
    req = urllib.request.Request(url, json.dumps(updates).encode(), method="PATCH")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    except Exception as e:
        return {"error": str(e)}


def _ai(prompt, max_tokens=500):
    if not OPENAI_KEY:
        return ""
    import urllib.request
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        json.dumps({"model": "gpt-4o-mini", "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_KEY}"},
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


def get_title_company(city: str, state: str) -> dict:
    """Get the best title company for this market."""
    if TITLE_COMPANIES_PATH.exists():
        companies = json.loads(TITLE_COMPANIES_PATH.read_text())
    else:
        companies = {}

    market = CITY_TO_MARKET.get(city.lower(), "")
    if market and market in companies:
        return companies[market][0]  # first (primary) company

    # Check national backup
    if "national_backup" in companies:
        return companies["national_backup"][0]

    return {"name": "TBD - needs title company", "phone": "", "notes": "No pre-vetted title company for this market"}


def generate_deal_sheet_html(seller: dict, deal: dict = None, buyer: dict = None) -> str:
    """Generate a beautiful branded deal sheet HTML for a property.

    This is the internal/buyer-facing presentation document.
    """
    address = seller.get("property_address", "Address TBD")
    city = seller.get("city", "")
    state = seller.get("state", "")
    beds = seller.get("bedrooms", 0)
    baths = seller.get("bathrooms", 0)
    sqft = seller.get("sqft", 0)
    year = seller.get("year_built", 0)
    arv = seller.get("estimated_arv", 0)
    repair = seller.get("estimated_repair", 0)
    asking = seller.get("asking_price", 0)
    assignment_fee = seller.get("potential_assignment_fee", 0) or (deal.get("assignment_fee", 0) if deal else 0)
    buyer_price = asking + assignment_fee
    profit = arv - buyer_price - repair if arv > 0 else 0
    roi = round(profit / max(buyer_price, 1) * 100, 1) if buyer_price > 0 else 0

    title_co = get_title_company(city, state)
    inspection_days = STATE_INSPECTION_DAYS.get(state, 10)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Deal Sheet - {address}</title></head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Segoe UI',Helvetica,Arial,sans-serif;color:#e8e8f0;">
<div style="max-width:680px;margin:0 auto;background:#0a0a0f;">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#1a1a2e,#12121a);padding:24px;text-align:center;border-bottom:3px solid #c9a84c;">
    <p style="margin:0;font-size:22px;font-weight:700;letter-spacing:2px;">
      EVERLIGHT <span style="color:#c9a84c;">VENTURES</span>
    </p>
    <p style="margin:4px 0 0;font-size:11px;color:#666;text-transform:uppercase;letter-spacing:3px;">
      Private Acquisitions Division
    </p>
  </div>

  <!-- CONFIDENTIAL BAR -->
  <div style="background:#c9a84c;padding:8px 24px;text-align:center;">
    <p style="margin:0;color:#000;font-size:12px;font-weight:700;letter-spacing:1px;">
      CONFIDENTIAL INVESTMENT OPPORTUNITY | FOR QUALIFIED BUYERS ONLY
    </p>
  </div>

  <div style="padding:24px;">

    <!-- PROPERTY HEADER -->
    <h1 style="color:#fff;font-size:24px;margin:0 0 4px;">{address}</h1>
    <p style="color:#c9a84c;font-size:16px;margin:0 0 20px;">{city}, {state}</p>

    <!-- PROPERTY DETAILS -->
    <table style="width:100%;margin-bottom:24px;border-collapse:collapse;">
      <tr>
        <td style="padding:10px 0;color:#888;font-size:13px;border-bottom:1px solid #1e1e2e;">Beds</td>
        <td style="padding:10px 0;color:#fff;font-weight:700;border-bottom:1px solid #1e1e2e;">{beds}</td>
        <td style="padding:10px 0;color:#888;font-size:13px;border-bottom:1px solid #1e1e2e;">Baths</td>
        <td style="padding:10px 0;color:#fff;font-weight:700;border-bottom:1px solid #1e1e2e;">{baths}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#888;font-size:13px;border-bottom:1px solid #1e1e2e;">Sq Ft</td>
        <td style="padding:10px 0;color:#fff;font-weight:700;border-bottom:1px solid #1e1e2e;">{sqft:,}</td>
        <td style="padding:10px 0;color:#888;font-size:13px;border-bottom:1px solid #1e1e2e;">Year Built</td>
        <td style="padding:10px 0;color:#fff;font-weight:700;border-bottom:1px solid #1e1e2e;">{year}</td>
      </tr>
    </table>

    <!-- FINANCIAL BREAKDOWN -->
    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="color:#c9a84c;font-size:16px;font-weight:700;margin:0 0 16px;text-transform:uppercase;letter-spacing:1px;">
        Financial Breakdown
      </p>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:10px 0;color:#888;border-bottom:1px solid #1e1e2e;">Buyer Purchase Price</td>
          <td style="padding:10px 0;color:#fff;font-weight:700;text-align:right;border-bottom:1px solid #1e1e2e;">${buyer_price:,}</td>
        </tr>
        <tr>
          <td style="padding:10px 0;color:#888;border-bottom:1px solid #1e1e2e;">Estimated Repairs</td>
          <td style="padding:10px 0;color:#ff9100;font-weight:700;text-align:right;border-bottom:1px solid #1e1e2e;">${repair:,}</td>
        </tr>
        <tr>
          <td style="padding:10px 0;color:#888;border-bottom:1px solid #1e1e2e;">After Repair Value (ARV)</td>
          <td style="padding:10px 0;color:#00e676;font-weight:700;text-align:right;border-bottom:1px solid #1e1e2e;">${arv:,}</td>
        </tr>
        <tr style="background:#c9a84c15;">
          <td style="padding:12px 0;color:#c9a84c;font-weight:700;font-size:15px;">Estimated Profit</td>
          <td style="padding:12px 0;color:#c9a84c;font-weight:700;font-size:18px;text-align:right;">${profit:,} ({roi}% ROI)</td>
        </tr>
      </table>
    </div>

    <!-- DEAL TERMS -->
    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:24px;margin-bottom:24px;">
      <p style="color:#c9a84c;font-size:16px;font-weight:700;margin:0 0 16px;text-transform:uppercase;letter-spacing:1px;">
        Deal Terms
      </p>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:8px 0;color:#888;">Contract Type</td>
          <td style="padding:8px 0;color:#fff;text-align:right;">Assignment of Contract</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#888;">Quality Assurance Period</td>
          <td style="padding:8px 0;color:#fff;text-align:right;">{inspection_days} days</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#888;">Closing Timeline</td>
          <td style="padding:8px 0;color:#fff;text-align:right;">14-21 days</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#888;">Title Company</td>
          <td style="padding:8px 0;color:#fff;text-align:right;">{title_co.get('name', 'TBD')}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#888;">Property Condition</td>
          <td style="padding:8px 0;color:#fff;text-align:right;">As-Is</td>
        </tr>
      </table>
    </div>

    <!-- TITLE COMPANY -->
    <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:12px;padding:20px;margin-bottom:24px;">
      <p style="color:#888;font-size:12px;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px;">Closing Agent</p>
      <p style="color:#fff;font-size:15px;font-weight:700;margin:0;">{title_co.get('name', 'TBD')}</p>
      <p style="color:#888;font-size:13px;margin:4px 0 0;">{title_co.get('phone', '')} | {title_co.get('website', '')}</p>
    </div>

    <!-- CTA -->
    <div style="background:linear-gradient(135deg,#c9a84c,#a07830);border-radius:12px;padding:20px;text-align:center;margin-bottom:24px;">
      <p style="color:#000;font-size:18px;font-weight:700;margin:0 0 8px;">Ready to Move Forward?</p>
      <p style="color:#000;font-size:14px;margin:0;">Contact: Piper Reeves | (888) 896-6772 | piper@everlightventures.io</p>
    </div>

    <!-- DISCLAIMER -->
    <p style="color:#444;font-size:10px;text-align:center;margin:20px 0 0;">
      This document is for informational purposes only and does not constitute a binding offer.
      All figures are estimates. Property inspection recommended. Everlight Ventures LLC is not
      a licensed real estate broker. Assignment of contract subject to terms of original purchase agreement.
    </p>

  </div>

  <!-- FOOTER -->
  <div style="background:#12121a;padding:16px 24px;text-align:center;border-top:1px solid #1e1e2e;">
    <p style="color:#444;font-size:11px;margin:0;">
      Everlight Ventures LLC | everlightventures.io | Confidential
    </p>
  </div>

</div>
</body>
</html>"""

    return html


def generate_contract_md(seller: dict, deal: dict = None, buyer: dict = None) -> str:
    """Generate an assignment contract with Quality Assurance Review Period."""
    state = seller.get("state", "")
    city = seller.get("city", "")
    address = seller.get("property_address", "")
    inspection_days = STATE_INSPECTION_DAYS.get(state, 10)
    title_co = get_title_company(city, state)
    assignment_fee = seller.get("potential_assignment_fee", 0) or (deal.get("assignment_fee", 0) if deal else 5000)
    asking = seller.get("asking_price", 0)
    emd = max(500, int(asking * 0.01)) if asking > 0 else 1000

    buyer_name = buyer.get("company_name", "[ASSIGNEE NAME]") if buyer else "[ASSIGNEE NAME]"
    seller_name = seller.get("owner_name", "[SELLER NAME]")

    contract = f"""# ASSIGNMENT OF REAL ESTATE PURCHASE AGREEMENT

**Date**: {datetime.now().strftime('%B %d, %Y')}

**Property**: {address}, {city}, {state}

---

## PARTIES

**ASSIGNOR** (Contract Holder):
Everlight Ventures, LLC (d/b/a Everlight Logistics LLC)
Phone: (888) 896-6772 | Email: deals@everlightventures.io

**ASSIGNEE** (Buyer / End Investor):
{buyer_name}

**ORIGINAL SELLER**:
{seller_name}

---

## 1. ASSIGNMENT

Assignor hereby assigns all right, title, and interest in the Original Purchase
Agreement to Assignee under the terms herein.

## 2. ASSIGNMENT FEE

Assignment Fee: **${assignment_fee:,}**
- Deposit: **${int(assignment_fee * 0.2):,}** due upon execution
- Balance: **${int(assignment_fee * 0.8):,}** due at closing
- Held by: {title_co.get('name', 'Title Company TBD')}

## 3. EARNEST MONEY

EMD: **${emd:,}** held by {title_co.get('name', 'escrow agent')} per {state} law.

## 4. QUALITY ASSURANCE REVIEW PERIOD

Assignee shall have a **{inspection_days}-day Quality Assurance Review Period**
commencing from the date of this Agreement. During this period, Assignee may:

(a) Conduct property inspections, appraisals, and environmental assessments;
(b) Review title commitment and survey;
(c) Verify property condition, zoning compliance, and code violations;
(d) Confirm financing alignment and investment parameters.

If the Quality Assurance Review identifies material concerns regarding property
condition, title status, environmental factors, or financing feasibility, either
party may terminate this Agreement with written notice within the Review Period.
Upon such termination, all deposits shall be returned to Assignee.

## 5. CLOSING

- **Timeline**: Within 14-21 days of Quality Assurance approval
- **Title Company**: {title_co.get('name', 'TBD')} ({title_co.get('phone', '')})
- **Property Condition**: AS-IS, WHERE-IS

## 6. ASSIGNOR DISCLOSURE

Assignor is NOT a licensed real estate broker or agent. Assignor's interest
is limited to the assignment of the purchase contract for a fee. Assignor
makes no representations about property condition, value, or suitability.

## 7. GOVERNING LAW

This Agreement shall be governed by the laws of the State of {state}.

## 8. SIGNATURES

ASSIGNOR: Everlight Ventures, LLC
By: _______________________________ Date: ___________

ASSIGNEE: {buyer_name}
By: _______________________________ Date: ___________

---
*Generated by Everlight Ventures Deal Prep System*
*This document requires legal review before execution.*
"""
    return contract


def prep_deal_package(seller_id: str) -> dict:
    """Prepare a COMPLETE deal package for a seller lead.

    Generates:
    1. Deal sheet HTML (buyer presentation)
    2. Assignment contract with Quality Assurance clause
    3. Title company selection
    4. Matched buyer suggestion
    5. Saves everything to files + updates Supabase
    """
    # Get seller
    sellers = _sb_get("wholesale_sellers", f"id=eq.{seller_id}")
    if not sellers:
        return {"error": "Seller not found"}
    seller = sellers[0]

    state = seller.get("state", "")
    city = seller.get("city", "")

    # Find best buyer match
    buyers = _sb_get("wholesale_buyers", f"state=eq.{state}&order=deals_closed.desc&limit=5")
    matched_buyer = buyers[0] if buyers else None

    # Generate deal sheet HTML
    deal_sheet_html = generate_deal_sheet_html(seller, buyer=matched_buyer)

    # Generate contract
    contract_md = generate_contract_md(seller, buyer=matched_buyer)

    # Get title company
    title_co = get_title_company(city, state)

    # Save files
    safe_addr = re.sub(r'[^a-zA-Z0-9]', '_', seller.get("property_address", "unknown"))[:50]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    pkg_dir = OUTPUT_DIR / f"{safe_addr}_{ts}"
    pkg_dir.mkdir(exist_ok=True)

    (pkg_dir / "deal_sheet.html").write_text(deal_sheet_html)
    (pkg_dir / "assignment_contract.md").write_text(contract_md)
    (pkg_dir / "package_info.json").write_text(json.dumps({
        "seller_id": seller_id,
        "property": seller.get("property_address"),
        "city": city,
        "state": state,
        "title_company": title_co,
        "matched_buyer": matched_buyer.get("company_name") if matched_buyer else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))

    # Create deal record in Supabase
    deal_record = {
        "seller_id": seller_id,
        "buyer_id": matched_buyer.get("id") if matched_buyer else None,
        "property_address": seller.get("property_address", ""),
        "state": state,
        "purchase_price": seller.get("asking_price", 0),
        "assignment_fee": seller.get("potential_assignment_fee", 0),
        "buyer_price": (seller.get("asking_price", 0) + seller.get("potential_assignment_fee", 0)),
        "estimated_profit": (seller.get("estimated_arv", 0) - seller.get("asking_price", 0) - seller.get("estimated_repair", 0)),
        "status": "scouted",
        "title_company": title_co.get("name", "TBD"),
        "investment_pitch": f"Package at: {pkg_dir}",
        "agent_assigned": "Deal Prep Engine",
    }
    deal_result = _sb_insert("wholesale_deals", [deal_record])

    return {
        "success": True,
        "package_dir": str(pkg_dir),
        "deal_sheet": str(pkg_dir / "deal_sheet.html"),
        "contract": str(pkg_dir / "assignment_contract.md"),
        "title_company": title_co,
        "matched_buyer": matched_buyer.get("company_name") if matched_buyer else "No match yet",
        "deal_id": deal_result[0].get("id") if isinstance(deal_result, list) else None,
    }


def prep_all_top_sellers(max_packages: int = 5) -> list[dict]:
    """Auto-prep deal packages for top-priority sellers."""
    sellers = _sb_get("wholesale_sellers",
        "status=eq.new&priority_score=gt.0&verified=eq.true&order=priority_score.desc&limit=" + str(max_packages))

    if not sellers:
        # Also try unverified high-priority ones
        sellers = _sb_get("wholesale_sellers",
            "status=eq.new&priority_score=gt.2&order=priority_score.desc&limit=" + str(max_packages))

    results = []
    for seller in sellers:
        try:
            result = prep_deal_package(seller["id"])
            results.append(result)
            # Update seller status
            _sb_update("wholesale_sellers", "id", seller["id"], {"status": "contacted", "updated_at": datetime.now(timezone.utc).isoformat()})
        except Exception as e:
            results.append({"error": str(e), "seller_id": seller.get("id")})

    return results


if __name__ == "__main__":
    import sys
    if "--prep-all" in sys.argv:
        results = prep_all_top_sellers()
        print(f"Prepped {len(results)} deal packages")
        for r in results:
            print(f"  {r.get('package_dir', r.get('error', 'unknown'))}")
    elif "--prep" in sys.argv and len(sys.argv) > 2:
        seller_id = sys.argv[sys.argv.index("--prep") + 1]
        result = prep_deal_package(seller_id)
        print(json.dumps(result, indent=2))
    elif "--demo" in sys.argv:
        # Generate a demo deal sheet
        demo_seller = {
            "property_address": "1234 Oak Street",
            "city": "Atlanta",
            "state": "GA",
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 1400,
            "year_built": 1965,
            "estimated_arv": 185000,
            "estimated_repair": 25000,
            "asking_price": 95000,
            "potential_assignment_fee": 10000,
            "owner_name": "Jane Smith",
        }
        html = generate_deal_sheet_html(demo_seller)
        out = OUTPUT_DIR / "demo_deal_sheet.html"
        out.write_text(html)
        print(f"Demo deal sheet: {out}")

        contract = generate_contract_md(demo_seller)
        out2 = OUTPUT_DIR / "demo_contract.md"
        out2.write_text(contract)
        print(f"Demo contract: {out2}")
    else:
        print("Usage: --prep-all | --prep <seller_id> | --demo")
