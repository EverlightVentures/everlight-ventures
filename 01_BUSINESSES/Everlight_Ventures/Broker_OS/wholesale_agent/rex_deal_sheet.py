"""
Rex Deal Sheet Generator -- produces branded HTML + plain-text deal sheets
for buyer blasts when a property is under contract.

Usage:
    from rex_deal_sheet import generate_deal_sheet

    deal = {
        "address": "1234 Elm St",
        "city": "Atlanta",
        "state": "GA",
        "zip": "30318",
        "beds": 3,
        "baths": 2,
        "sqft": 1400,
        "year_built": 1965,
        "lot_size": "0.18 acres",
        "contract_price": 85000,
        "assignment_fee": 10000,
        "arv": 185000,
        "comps": [
            {"address": "1240 Elm St", "sold_price": 182000, "sold_date": "2026-01-15"},
            {"address": "1300 Oak Ave", "sold_price": 190000, "sold_date": "2025-12-03"},
            {"address": "1188 Pine Rd", "sold_price": 178000, "sold_date": "2026-02-20"},
        ],
        "repairs": {
            "Roof": 8000,
            "HVAC": 4500,
            "Kitchen": 12000,
            "Bathrooms": 6000,
            "Flooring": 3500,
            "Paint / Drywall": 2500,
            "Electrical": 1500,
            "Plumbing": 2000,
        },
        "school_rating": "7/10",
        "walkability": "62/100",
        "population_growth": "+3.2% (5yr)",
        "title_company": "Peach State Title",
        "title_contact": "Lisa Monroe",
        "title_email": "lisa@peachstatetitle.com",
        "title_phone": "(404) 555-0199",
        "emd_amount": 5000,
        "photo_url": "",  # optional override; uses Street View if blank
    }

    result = generate_deal_sheet(deal)
    # result["html_body"]  -- full HTML email string
    # result["text_body"]  -- plain text fallback
    # result["subject"]    -- email subject line
"""

import os
import urllib.parse
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
BRAND_NAVY = "#1a1a2e"
BRAND_GOLD = "#c9a84c"
BRAND_DARK = "#0d0d1a"
BRAND_WHITE = "#f0f0f0"
GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def get_street_view_url(address: str, city: str, state: str) -> str:
    """Return a Google Street View static image URL for the property."""
    location = urllib.parse.quote(f"{address}, {city}, {state}")
    base = "https://maps.googleapis.com/maps/api/streetview"
    if GOOGLE_API_KEY:
        return f"{base}?size=600x400&location={location}&key={GOOGLE_API_KEY}"
    # No API key -- return empty so template can skip the image
    return ""


def _money(value) -> str:
    """Format an integer/float as $XXX,XXX."""
    try:
        return f"${int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _pct(value) -> str:
    """Format a float as XX.X%."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return str(value)


def format_comp_table(comps: list) -> str:
    """Return an HTML table of comparable sales."""
    if not comps:
        return "<p style='color:#aaa;'>No comps available.</p>"

    rows = ""
    for c in comps:
        addr = c.get("address", "N/A")
        price = _money(c.get("sold_price", 0))
        date = c.get("sold_date", "N/A")
        rows += (
            f"<tr>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #2a2a4a;color:#ccc;'>{addr}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #2a2a4a;color:{BRAND_GOLD};font-weight:700;'>{price}</td>"
            f"<td style='padding:8px 12px;border-bottom:1px solid #2a2a4a;color:#aaa;'>{date}</td>"
            f"</tr>"
        )

    return (
        f"<table style='width:100%;border-collapse:collapse;margin:12px 0;'>"
        f"<tr style='background:{BRAND_NAVY};'>"
        f"<th style='padding:10px 12px;text-align:left;color:{BRAND_GOLD};font-size:13px;'>Address</th>"
        f"<th style='padding:10px 12px;text-align:left;color:{BRAND_GOLD};font-size:13px;'>Sold Price</th>"
        f"<th style='padding:10px 12px;text-align:left;color:{BRAND_GOLD};font-size:13px;'>Sold Date</th>"
        f"</tr>"
        f"{rows}"
        f"</table>"
    )


def _format_comp_text(comps: list) -> str:
    """Plain-text comp list."""
    if not comps:
        return "  No comps available.\n"
    lines = []
    for c in comps:
        lines.append(
            f"  - {c.get('address','N/A')}  |  "
            f"{_money(c.get('sold_price',0))}  |  "
            f"{c.get('sold_date','N/A')}"
        )
    return "\n".join(lines)


def _repair_rows_html(repairs: dict) -> str:
    """HTML rows for the repair estimate table."""
    if not repairs:
        return "<tr><td colspan='2' style='padding:8px;color:#aaa;'>TBD</td></tr>"
    rows = ""
    for item, cost in repairs.items():
        rows += (
            f"<tr>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #2a2a4a;color:#ccc;'>{item}</td>"
            f"<td style='padding:6px 12px;border-bottom:1px solid #2a2a4a;color:#fff;font-weight:600;'>{_money(cost)}</td>"
            f"</tr>"
        )
    return rows


def _repair_text(repairs: dict) -> str:
    """Plain-text repair breakdown."""
    if not repairs:
        return "  TBD\n"
    lines = []
    for item, cost in repairs.items():
        lines.append(f"  - {item}: {_money(cost)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN GENERATOR
# ---------------------------------------------------------------------------

def generate_deal_sheet(deal: dict) -> dict:
    """
    Generate a branded deal sheet from a deal dictionary.

    Returns:
        dict with keys: html_body, text_body, subject
    """
    # -- Derived numbers --
    contract_price = int(deal.get("contract_price", 0))
    assignment_fee = int(deal.get("assignment_fee", 0))
    buyer_price = contract_price + assignment_fee
    arv = int(deal.get("arv", 0))
    repairs = deal.get("repairs", {})
    total_repairs = sum(int(v) for v in repairs.values()) if repairs else 0
    buyer_profit = arv - buyer_price - total_repairs
    roi = (buyer_profit / buyer_price * 100) if buyer_price > 0 else 0

    address = deal.get("address", "")
    city = deal.get("city", "")
    state = deal.get("state", "")
    zip_code = deal.get("zip", "")
    full_address = f"{address}, {city}, {state} {zip_code}".strip()

    emd = int(deal.get("emd_amount", 5000))
    comps = deal.get("comps", [])

    # Photo
    photo_url = deal.get("photo_url", "") or get_street_view_url(address, city, state)

    subject = f"Off-Market Deal | {address}, {city} {state} | {_money(arv)} ARV"

    # -- Photo block --
    photo_html = ""
    if photo_url:
        photo_html = (
            f"<div style='text-align:center;margin-bottom:24px;'>"
            f"<img src='{photo_url}' alt='Property Photo' "
            f"style='max-width:100%;border-radius:8px;border:2px solid {BRAND_GOLD};' />"
            f"</div>"
        )

    # -- Neighborhood --
    neighborhood_html = ""
    neighborhood_items = []
    if deal.get("school_rating"):
        neighborhood_items.append(f"School Rating: {deal['school_rating']}")
    if deal.get("walkability"):
        neighborhood_items.append(f"Walk Score: {deal['walkability']}")
    if deal.get("population_growth"):
        neighborhood_items.append(f"Population Growth: {deal['population_growth']}")
    if neighborhood_items:
        nh_cells = "".join(
            f"<td style='padding:8px 16px;text-align:center;'>"
            f"<span style='color:{BRAND_GOLD};font-weight:700;'>{item.split(': ')[1]}</span><br>"
            f"<span style='color:#aaa;font-size:12px;'>{item.split(': ')[0]}</span></td>"
            for item in neighborhood_items
        )
        neighborhood_html = (
            f"<table style='width:100%;margin:16px 0;'><tr>{nh_cells}</tr></table>"
        )

    # -- Title company --
    title_html = ""
    if deal.get("title_company"):
        title_html = (
            f"<div style='background:{BRAND_NAVY};border:1px solid #2a2a4a;border-radius:8px;"
            f"padding:16px;margin:20px 0;'>"
            f"<p style='color:{BRAND_GOLD};font-weight:700;margin:0 0 8px;'>Title Company -- Wire EMD Here</p>"
            f"<p style='color:#ccc;margin:0;'>"
            f"{deal.get('title_company','')}<br>"
            f"{deal.get('title_contact','')}<br>"
            f"{deal.get('title_email','')}<br>"
            f"{deal.get('title_phone','')}"
            f"</p></div>"
        )

    # -- Build HTML --
    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:{BRAND_DARK};font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
<div style="max-width:640px;margin:0 auto;background:{BRAND_DARK};">

  <!-- HEADER -->
  <div style="background:{BRAND_NAVY};padding:20px 24px;text-align:center;border-bottom:3px solid {BRAND_GOLD};">
    <p style="margin:0;font-size:20px;font-weight:700;color:#fff;letter-spacing:1px;">
      EVERLIGHT <span style="color:{BRAND_GOLD};">VENTURES</span>
    </p>
    <p style="margin:4px 0 0;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:2px;">
      Private Acquisitions
    </p>
  </div>

  <!-- URGENCY BAR -->
  <div style="background:#8b0000;padding:12px 24px;text-align:center;">
    <p style="margin:0;color:#fff;font-size:14px;font-weight:700;">
      &#9888; MULTIPLE BUYERS ARE REVIEWING THIS PROPERTY &#9888;
    </p>
  </div>

  <div style="padding:24px;">

    <!-- PHOTO -->
    {photo_html}

    <!-- PROPERTY DETAILS -->
    <h1 style="color:#fff;font-size:22px;margin:0 0 4px;">{address}</h1>
    <p style="color:{BRAND_GOLD};font-size:16px;margin:0 0 20px;">{city}, {state} {zip_code}</p>

    <table style="width:100%;margin-bottom:24px;">
      <tr>
        <td style="padding:8px 0;color:#aaa;font-size:13px;">Beds</td>
        <td style="padding:8px 0;color:#fff;font-weight:700;">{deal.get('beds','--')}</td>
        <td style="padding:8px 0;color:#aaa;font-size:13px;">Baths</td>
        <td style="padding:8px 0;color:#fff;font-weight:700;">{deal.get('baths','--')}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:#aaa;font-size:13px;">Sq Ft</td>
        <td style="padding:8px 0;color:#fff;font-weight:700;">{deal.get('sqft','--'):,}</td>
        <td style="padding:8px 0;color:#aaa;font-size:13px;">Year Built</td>
        <td style="padding:8px 0;color:#fff;font-weight:700;">{deal.get('year_built','--')}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:#aaa;font-size:13px;">Lot Size</td>
        <td colspan="3" style="padding:8px 0;color:#fff;font-weight:700;">{deal.get('lot_size','--')}</td>
      </tr>
    </table>

    <!-- FINANCIAL BREAKDOWN -->
    <div style="background:{BRAND_NAVY};border:1px solid #2a2a4a;border-radius:8px;padding:20px;margin-bottom:24px;">
      <p style="color:{BRAND_GOLD};font-size:16px;font-weight:700;margin:0 0 16px;text-transform:uppercase;">
        Financial Breakdown
      </p>
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:8px 0;color:#aaa;">Buyer Purchase Price</td>
          <td style="padding:8px 0;color:#fff;font-weight:700;text-align:right;">{_money(buyer_price)}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#aaa;font-size:12px;padding-left:16px;">Contract Price</td>
          <td style="padding:8px 0;color:#ccc;text-align:right;font-size:13px;">{_money(contract_price)}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#aaa;font-size:12px;padding-left:16px;">Assignment Fee</td>
          <td style="padding:8px 0;color:#ccc;text-align:right;font-size:13px;">{_money(assignment_fee)}</td>
        </tr>
        <tr style="border-top:1px solid #2a2a4a;">
          <td style="padding:8px 0;color:#aaa;">Estimated ARV</td>
          <td style="padding:8px 0;color:{BRAND_GOLD};font-weight:700;text-align:right;font-size:18px;">{_money(arv)}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;color:#aaa;">Estimated Repairs</td>
          <td style="padding:8px 0;color:#fff;font-weight:700;text-align:right;">{_money(total_repairs)}</td>
        </tr>
        <tr style="border-top:2px solid {BRAND_GOLD};">
          <td style="padding:12px 0;color:#fff;font-weight:700;font-size:16px;">Projected Profit</td>
          <td style="padding:12px 0;color:#00cc66;font-weight:700;text-align:right;font-size:20px;">{_money(buyer_profit)}</td>
        </tr>
        <tr>
          <td style="padding:4px 0;color:#aaa;">ROI</td>
          <td style="padding:4px 0;color:#00cc66;font-weight:700;text-align:right;">{_pct(roi)}</td>
        </tr>
      </table>
    </div>

    <!-- COMPS -->
    <div style="margin-bottom:24px;">
      <p style="color:{BRAND_GOLD};font-size:14px;font-weight:700;text-transform:uppercase;margin:0 0 8px;">
        Comparable Sales
      </p>
      {format_comp_table(comps)}
    </div>

    <!-- REPAIRS -->
    <div style="margin-bottom:24px;">
      <p style="color:{BRAND_GOLD};font-size:14px;font-weight:700;text-transform:uppercase;margin:0 0 8px;">
        Estimated Repair Breakdown
      </p>
      <table style="width:100%;border-collapse:collapse;">
        {_repair_rows_html(repairs)}
        <tr style="border-top:2px solid {BRAND_GOLD};">
          <td style="padding:8px 12px;color:#fff;font-weight:700;">Total Repairs</td>
          <td style="padding:8px 12px;color:{BRAND_GOLD};font-weight:700;">{_money(total_repairs)}</td>
        </tr>
      </table>
    </div>

    <!-- NEIGHBORHOOD -->
    {neighborhood_html}

    <!-- TITLE COMPANY -->
    {title_html}

    <!-- EMD CTA -->
    <div style="background:{BRAND_GOLD};border-radius:8px;padding:24px;text-align:center;margin:24px 0;">
      <p style="margin:0 0 8px;color:{BRAND_DARK};font-size:18px;font-weight:700;">
        FIRST BUYER TO WIRE {_money(emd)} EMD GETS THIS DEAL
      </p>
      <p style="margin:0;color:{BRAND_DARK};font-size:14px;">
        Reply <strong>INTERESTED</strong> to lock this deal now.
      </p>
    </div>

  </div>

  <!-- FOOTER -->
  <div style="background:{BRAND_NAVY};padding:16px 24px;text-align:center;border-top:1px solid #2a2a4a;">
    <p style="margin:0;color:#888;font-size:12px;">
      Everlight Ventures | Everlight Logistics LLC<br>
      <a href="mailto:hammer@everlightventures.io" style="color:{BRAND_GOLD};">hammer@everlightventures.io</a> |
      <a href="https://everlightventures.io" style="color:{BRAND_GOLD};">everlightventures.io</a>
    </p>
    <p style="margin:8px 0 0;color:#555;font-size:10px;">
      This deal sheet is confidential. Do not forward without permission.
    </p>
  </div>

</div>
</body>
</html>"""

    # -- Build plain text --
    text_body = f"""====================================================
  EVERLIGHT VENTURES -- PRIVATE ACQUISITIONS
====================================================

*** MULTIPLE BUYERS ARE REVIEWING THIS PROPERTY ***

PROPERTY: {full_address}
Beds: {deal.get('beds','--')}  |  Baths: {deal.get('baths','--')}  |  Sq Ft: {deal.get('sqft','--')}
Year Built: {deal.get('year_built','--')}  |  Lot: {deal.get('lot_size','--')}

----------------------------------------------------
FINANCIAL BREAKDOWN
----------------------------------------------------
  Buyer Purchase Price:  {_money(buyer_price)}
    - Contract Price:    {_money(contract_price)}
    - Assignment Fee:    {_money(assignment_fee)}
  Estimated ARV:         {_money(arv)}
  Estimated Repairs:     {_money(total_repairs)}
  ---
  PROJECTED PROFIT:      {_money(buyer_profit)}
  ROI:                   {_pct(roi)}

----------------------------------------------------
COMPARABLE SALES
----------------------------------------------------
{_format_comp_text(comps)}

----------------------------------------------------
REPAIR ESTIMATE
----------------------------------------------------
{_repair_text(repairs)}
  ---
  Total Repairs:         {_money(total_repairs)}

----------------------------------------------------
NEIGHBORHOOD
----------------------------------------------------
  School Rating:      {deal.get('school_rating', 'N/A')}
  Walk Score:         {deal.get('walkability', 'N/A')}
  Population Growth:  {deal.get('population_growth', 'N/A')}

----------------------------------------------------
TITLE COMPANY -- WIRE EMD HERE
----------------------------------------------------
  {deal.get('title_company', 'TBD')}
  {deal.get('title_contact', '')}
  {deal.get('title_email', '')}
  {deal.get('title_phone', '')}

====================================================
  FIRST BUYER TO WIRE {_money(emd)} EMD GETS THIS DEAL
  Reply INTERESTED to lock this deal now.
====================================================

Everlight Ventures | Everlight Logistics LLC
hammer@everlightventures.io | everlightventures.io
This deal sheet is confidential. Do not forward without permission.
"""

    return {
        "html_body": html_body,
        "text_body": text_body,
        "subject": subject,
    }


# ---------------------------------------------------------------------------
# CLI TEST
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_deal = {
        "address": "1234 Elm St",
        "city": "Atlanta",
        "state": "GA",
        "zip": "30318",
        "beds": 3,
        "baths": 2,
        "sqft": 1400,
        "year_built": 1965,
        "lot_size": "0.18 acres",
        "contract_price": 85000,
        "assignment_fee": 10000,
        "arv": 185000,
        "comps": [
            {"address": "1240 Elm St", "sold_price": 182000, "sold_date": "2026-01-15"},
            {"address": "1300 Oak Ave", "sold_price": 190000, "sold_date": "2025-12-03"},
            {"address": "1188 Pine Rd", "sold_price": 178000, "sold_date": "2026-02-20"},
        ],
        "repairs": {
            "Roof": 8000,
            "HVAC": 4500,
            "Kitchen": 12000,
            "Bathrooms": 6000,
            "Flooring": 3500,
            "Paint / Drywall": 2500,
            "Electrical": 1500,
            "Plumbing": 2000,
        },
        "school_rating": "7/10",
        "walkability": "62/100",
        "population_growth": "+3.2% (5yr)",
        "title_company": "Peach State Title",
        "title_contact": "Lisa Monroe",
        "title_email": "lisa@peachstatetitle.com",
        "title_phone": "(404) 555-0199",
        "emd_amount": 5000,
    }

    result = generate_deal_sheet(sample_deal)
    print(f"Subject: {result['subject']}\n")
    print("=== TEXT VERSION ===")
    print(result["text_body"])

    # Save HTML for preview
    from pathlib import Path
    out = Path(__file__).parent / "deal_sheet_preview.html"
    out.write_text(result["html_body"])
    print(f"\nHTML preview saved to {out}")
