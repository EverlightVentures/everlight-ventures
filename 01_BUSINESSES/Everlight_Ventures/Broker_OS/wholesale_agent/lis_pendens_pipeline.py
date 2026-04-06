#!/usr/bin/env python3
"""
Everlight Distressed Property Intelligence Pipeline
====================================================
Scrapes lis pendens / pre-foreclosure filings from 6 target counties,
enriches records, scores them, generates branded PDF reports, and
delivers weekly to subscribers via Resend.

Env vars required (set in .env or export):
    RESEND_API_KEY        -- Resend email delivery
    SUPABASE_URL          -- e.g. https://xxx.supabase.co
    SUPABASE_SERVICE_KEY  -- Supabase service-role key
    ZILLOW_API_KEY        -- (optional) for Zestimate enrichment
"""

import csv
import io
import json
import os
import re
import logging
import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s -- %(message)s",
)
log = logging.getLogger("lis_pendens")

# ---------------------------------------------------------------------------
# County Court Data Sources
# ---------------------------------------------------------------------------
COUNTY_SOURCES: dict[str, dict[str, Any]] = {
    "st_louis_mo": {
        "county": "St. Louis County",
        "state": "MO",
        "recorder_url": "https://www.stlouisco.com/PropertyTaxes/PolarisCivilSearch",
        "court_search_url": "https://www.stlouisco.com/LawandPublicSafety/CircuitCourt",
        "foia_email": "recorder@stlouisco.com",
        "data_format": "HTML table -- paginated search by date range, case type = LP",
        "search_params": {
            "case_type": "LP",
            "date_field": "FileDate",
            "results_per_page": 50,
        },
        "notes": (
            "St. Louis County Circuit Court provides a Polaris-based civil "
            "search. Filter by case type 'LP' (Lis Pendens). Bulk data may "
            "require a Sunshine Law (MO FOIA) request to the Recorder of Deeds."
        ),
        "foia_template": (
            "Dear St. Louis County Recorder of Deeds,\n\n"
            "Pursuant to Missouri's Sunshine Law (Chapter 610, RSMo), I request "
            "copies of all lis pendens filings recorded in the past 30 days. "
            "Please provide: case number, filing date, property address, "
            "plaintiff name, defendant name, and amount claimed.\n\n"
            "I prefer electronic delivery (CSV/Excel). Please advise of any "
            "fees before processing.\n\n"
            "Thank you,\nEverlight Ventures\ndata@everlightventures.io"
        ),
    },
    "fulton_ga": {
        "county": "Fulton County",
        "state": "GA",
        "recorder_url": "https://www.fultoncountyga.gov/services/clerk-of-superior-court",
        "court_search_url": (
            "https://publicrecordsaccess.fultoncountyga.gov/Portal/Home/Dashboard/29"
        ),
        "foia_email": "clerk@fultoncountyga.gov",
        "data_format": "Portal search -- instrument type = Lis Pendens, date range",
        "search_params": {
            "instrument_type": "Lis Pendens",
            "date_field": "RecordDate",
        },
        "notes": (
            "Fulton County Clerk of Superior Court has a public records portal. "
            "Search by instrument type 'Lis Pendens'. Bulk exports may require "
            "an Open Records Act (GA FOIA) request."
        ),
        "foia_template": (
            "Dear Fulton County Clerk of Superior Court,\n\n"
            "Under the Georgia Open Records Act (O.C.G.A. 50-18-70), I request "
            "all lis pendens filings recorded in the last 30 days including: "
            "instrument number, recording date, property address, grantor, "
            "grantee, and legal description.\n\n"
            "Electronic format preferred (CSV/Excel).\n\n"
            "Thank you,\nEverlight Ventures\ndata@everlightventures.io"
        ),
    },
    "dallas_tx": {
        "county": "Dallas County",
        "state": "TX",
        "recorder_url": "https://www.dallascounty.org/government/county-clerk/recording/",
        "court_search_url": (
            "https://www.dallascounty.org/government/county-clerk/online-records-search.php"
        ),
        "foia_email": "countyclerk@dallascounty.org",
        "data_format": "Online index search -- document type = Lis Pendens",
        "search_params": {
            "doc_type": "LIS PENDENS",
            "date_field": "FilingDate",
        },
        "notes": (
            "Dallas County Clerk provides an online records search. Select "
            "document type 'LIS PENDENS'. Texas Public Information Act requests "
            "can yield bulk data."
        ),
        "foia_template": (
            "Dear Dallas County Clerk,\n\n"
            "Under the Texas Public Information Act (Chapter 552, Government Code), "
            "I request all lis pendens filings from the past 30 days including: "
            "filing number, date, property address, plaintiff, defendant, and "
            "amount claimed.\n\n"
            "Electronic delivery preferred.\n\n"
            "Thank you,\nEverlight Ventures\ndata@everlightventures.io"
        ),
    },
    "mecklenburg_nc": {
        "county": "Mecklenburg County",
        "state": "NC",
        "recorder_url": "https://www.mecknc.gov/CountyManagersOffice/ROD/Pages/default.aspx",
        "court_search_url": (
            "https://rod.mecknc.gov/NewROD/Home.aspx"
        ),
        "foia_email": "rod@mecknc.gov",
        "data_format": "ROD portal -- document type = Lis Pendens, date search",
        "search_params": {
            "doc_type": "LIS PENDENS",
            "date_field": "RecordingDate",
        },
        "notes": (
            "Mecklenburg County Register of Deeds has a web portal. Search "
            "by document type. NC Public Records Law (Chapter 132) governs "
            "bulk requests."
        ),
        "foia_template": (
            "Dear Mecklenburg County Register of Deeds,\n\n"
            "Under North Carolina Public Records Law (G.S. 132), I request all "
            "lis pendens filed in the past 30 days: book/page, recording date, "
            "property address, grantor, grantee.\n\n"
            "Electronic format preferred.\n\n"
            "Thank you,\nEverlight Ventures\ndata@everlightventures.io"
        ),
    },
    "cuyahoga_oh": {
        "county": "Cuyahoga County",
        "state": "OH",
        "recorder_url": "https://recorder.cuyahogacounty.us/",
        "court_search_url": (
            "https://recorder.cuyahogacounty.us/searchs/SearchByDocType.aspx"
        ),
        "foia_email": "recorder@cuyahogacounty.us",
        "data_format": "Recorder portal -- doc type search, date range",
        "search_params": {
            "doc_type": "LIS PENDENS",
            "date_field": "RecordDate",
        },
        "notes": (
            "Cuyahoga County Fiscal Officer / Recorder provides online search. "
            "Ohio Public Records Act (ORC 149.43) for bulk requests."
        ),
        "foia_template": (
            "Dear Cuyahoga County Recorder,\n\n"
            "Under Ohio's Public Records Act (ORC 149.43), I request all lis "
            "pendens recordings from the past 30 days including: instrument "
            "number, recording date, property address, names of all parties.\n\n"
            "Electronic format preferred.\n\n"
            "Thank you,\nEverlight Ventures\ndata@everlightventures.io"
        ),
    },
    "duval_fl": {
        "county": "Duval County",
        "state": "FL",
        "recorder_url": "https://www.duvalclerk.com/",
        "court_search_url": (
            "https://core.duvalclerk.com/CoreCms.aspx"
        ),
        "foia_email": "clerkinfo@duvalclerk.com",
        "data_format": "CORE system -- case type = Lis Pendens / Foreclosure",
        "search_params": {
            "case_type": "CF",  # Circuit Civil -- Foreclosure
            "doc_type": "LP",
            "date_field": "FileDate",
        },
        "notes": (
            "Duval County Clerk of Courts uses the CORE system. Florida is "
            "a judicial foreclosure state so lis pendens are filed with the "
            "clerk. Florida's Public Records Law (Chapter 119) applies."
        ),
        "foia_template": (
            "Dear Duval County Clerk of Courts,\n\n"
            "Under Florida's Public Records Law (Chapter 119, F.S.), I request "
            "all lis pendens filings from the past 30 days: case number, "
            "filing date, property address, plaintiff, defendant, amount.\n\n"
            "Electronic delivery preferred.\n\n"
            "Thank you,\nEverlight Ventures\ndata@everlightventures.io"
        ),
    },
}


def get_county_config(county_key: str) -> dict[str, Any]:
    """Return config for a county by key. Raises KeyError if unknown."""
    if county_key not in COUNTY_SOURCES:
        raise KeyError(
            f"Unknown county key '{county_key}'. "
            f"Valid: {list(COUNTY_SOURCES.keys())}"
        )
    return COUNTY_SOURCES[county_key]


def list_counties() -> list[dict[str, str]]:
    """Return summary list of all configured counties."""
    return [
        {"key": k, "county": v["county"], "state": v["state"]}
        for k, v in COUNTY_SOURCES.items()
    ]


def generate_foia_request(county_key: str) -> str:
    """Return the pre-filled FOIA letter for a county."""
    cfg = get_county_config(county_key)
    return cfg["foia_template"]


# ---------------------------------------------------------------------------
# B. Enrichment Pipeline
# ---------------------------------------------------------------------------

def _estimate_arv(address: str, city: str, state: str, zip_code: str) -> Optional[float]:
    """
    Attempt to get an ARV estimate.  Tries Zillow API if key is set,
    otherwise returns None (caller should use county assessor value).
    """
    api_key = os.getenv("ZILLOW_API_KEY")
    if not api_key:
        log.debug("No ZILLOW_API_KEY -- skipping Zestimate lookup")
        return None

    # Zillow's ZWSID / RapidAPI bridge
    try:
        resp = requests.get(
            "https://zillow-com1.p.rapidapi.com/property",
            params={"address": f"{address}, {city}, {state} {zip_code}"},
            headers={
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("zestimate") or data.get("price") or 0) or None
    except Exception as exc:
        log.warning("Zestimate lookup failed for %s: %s", address, exc)

    return None


def _assess_property_details(
    address: str, city: str, state: str, zip_code: str
) -> dict[str, Any]:
    """
    Placeholder for county assessor API integration.
    In production, wire this to each county's assessor search or
    a data aggregator like ATTOM, CoreLogic, or PropertyShark.
    Returns whatever we can find; missing fields are None.
    """
    return {
        "beds": None,
        "baths": None,
        "sqft": None,
        "year_built": None,
        "assessed_value": None,
        "property_type": "sfr",  # default assumption
        "owner_name": None,
        "owner_mailing_address": None,
        "mortgage_balance": None,
    }


def enrich_filing(filing_data: dict[str, Any]) -> dict[str, Any]:
    """
    Takes a raw lis pendens record and returns an enriched dict.

    Expected input keys:
        case_number, address, city, state, zip_code, filing_date,
        amount_owed (optional), county (optional)

    Returns the original fields plus:
        beds, baths, sqft, year_built, property_type,
        estimated_arv, owner_name, owner_mailing_address,
        equity_estimate, equity_pct, days_since_filing,
        mortgage_balance, motivation_score, enrichment_source
    """
    address = filing_data.get("address", "")
    city = filing_data.get("city", "")
    state = filing_data.get("state", "")
    zip_code = filing_data.get("zip_code", "")

    # County assessor data
    details = _assess_property_details(address, city, state, zip_code)

    # ARV estimate
    arv = _estimate_arv(address, city, state, zip_code)
    if arv is None and details.get("assessed_value"):
        # Rough proxy: assessed value * 1.15 for market premium
        arv = float(details["assessed_value"]) * 1.15
    arv = arv or 0.0

    # Equity estimate
    mortgage = details.get("mortgage_balance")
    amount_owed = filing_data.get("amount_owed")
    if mortgage and arv:
        equity = arv - float(mortgage)
    elif amount_owed and arv:
        equity = arv - float(amount_owed)
    else:
        equity = None

    equity_pct = round((equity / arv) * 100, 1) if (equity and arv) else None

    # Days since filing
    filing_date_raw = filing_data.get("filing_date")
    if isinstance(filing_date_raw, str):
        try:
            filing_dt = datetime.strptime(filing_date_raw, "%Y-%m-%d").date()
        except ValueError:
            filing_dt = None
    elif isinstance(filing_date_raw, date):
        filing_dt = filing_date_raw
    else:
        filing_dt = None

    days_since = (date.today() - filing_dt).days if filing_dt else None

    # Absentee owner check (mailing address differs from property)
    owner_mailing = details.get("owner_mailing_address") or ""
    is_absentee = bool(
        owner_mailing
        and address
        and owner_mailing.lower().split(",")[0].strip()
        != address.lower().strip()
    )

    enriched = {
        **filing_data,
        "beds": details.get("beds"),
        "baths": details.get("baths"),
        "sqft": details.get("sqft"),
        "year_built": details.get("year_built"),
        "property_type": details.get("property_type", "sfr"),
        "estimated_arv": round(arv, 2) if arv else None,
        "owner_name": details.get("owner_name"),
        "owner_mailing_address": owner_mailing or None,
        "mortgage_balance": mortgage,
        "equity_estimate": round(equity, 2) if equity else None,
        "equity_pct": equity_pct,
        "days_since_filing": days_since,
        "is_absentee": is_absentee,
        "amount_owed": amount_owed,
        "motivation_score": 0,  # filled by score_lis_pendens
        "enrichment_source": "county_assessor",
        "enriched_at": datetime.utcnow().isoformat(),
    }

    # Score it
    enriched["motivation_score"] = score_lis_pendens(enriched)

    return enriched


# ---------------------------------------------------------------------------
# C. Scoring Function
# ---------------------------------------------------------------------------

def score_lis_pendens(record: dict[str, Any]) -> int:
    """
    Score 0-100 based on institutional investor attractiveness.

    Factors:
        High equity (>50%)              +25
        SFR property                    +15
        ARV $100k-$500k sweet spot      +20
        Filed recently (<30 days)       +15
        Absentee owner                  +10
        Multi-family (2-4 units)        +10
        Filed amount > $50k             +5
    """
    score = 0

    # Equity
    eq_pct = record.get("equity_pct")
    if eq_pct is not None and eq_pct > 50:
        score += 25
    elif eq_pct is not None and eq_pct > 30:
        score += 15
    elif eq_pct is not None and eq_pct > 10:
        score += 5

    # Property type
    ptype = (record.get("property_type") or "").lower()
    if ptype in ("sfr", "single_family", "single-family"):
        score += 15
    elif ptype in ("multi", "multi_family", "multi-family", "duplex", "triplex", "quadplex"):
        score += 10

    # ARV sweet spot
    arv = record.get("estimated_arv") or 0
    if 100_000 <= arv <= 500_000:
        score += 20
    elif 50_000 <= arv < 100_000:
        score += 10
    elif 500_000 < arv <= 750_000:
        score += 5

    # Recency
    days = record.get("days_since_filing")
    if days is not None and days < 30:
        score += 15
    elif days is not None and days < 60:
        score += 8

    # Absentee
    if record.get("is_absentee"):
        score += 10

    # Amount owed
    amt = record.get("amount_owed")
    if amt is not None:
        try:
            if float(amt) > 50_000:
                score += 5
        except (ValueError, TypeError):
            pass

    return min(score, 100)


# ---------------------------------------------------------------------------
# D. Report Generator (HTML-based, convertible to PDF)
# ---------------------------------------------------------------------------

def _html_escape(text: Any) -> str:
    """Minimal HTML escaping."""
    s = str(text) if text is not None else "--"
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_weekly_report(
    records: list[dict[str, Any]],
    market: str,
    report_date: Optional[date] = None,
) -> bytes:
    """
    Generate a branded HTML report as bytes.

    To convert to PDF, pipe through weasyprint or wkhtmltopdf:
        weasyprint.HTML(string=html).write_pdf(target_path)

    Returns: UTF-8 encoded HTML bytes.
    """
    report_date = report_date or date.today()
    week_label = report_date.strftime("%B %d, %Y")

    sorted_records = sorted(
        records, key=lambda r: r.get("motivation_score", 0), reverse=True
    )

    total = len(sorted_records)
    avg_equity = 0.0
    equity_vals = [r["equity_pct"] for r in sorted_records if r.get("equity_pct")]
    if equity_vals:
        avg_equity = sum(equity_vals) / len(equity_vals)

    top_10 = sorted_records[:10]
    avg_score = 0
    if sorted_records:
        avg_score = sum(r.get("motivation_score", 0) for r in sorted_records) // total

    # Trend placeholders (in production, compare against last week's data)
    trend_note = "Trend data requires 2+ weeks of collection."

    # Build rows
    rows_html = ""
    for i, r in enumerate(sorted_records, 1):
        rows_html += f"""
        <tr>
            <td>{i}</td>
            <td>{_html_escape(r.get('address'))}</td>
            <td>{_html_escape(r.get('city'))}, {_html_escape(r.get('state'))}</td>
            <td>{_html_escape(r.get('property_type', 'sfr')).upper()}</td>
            <td>${r.get('estimated_arv', 0):,.0f}</td>
            <td>{r.get('equity_pct', '--')}%</td>
            <td><strong>{r.get('motivation_score', 0)}</strong></td>
            <td>{_html_escape(r.get('filing_date'))}</td>
            <td>{r.get('days_since_filing', '--')}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Everlight Distressed Property Intelligence -- {_html_escape(market)}</title>
<style>
    @page {{ margin: 0.75in; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; margin: 0; padding: 0; }}
    .cover {{ background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
              color: #fff; padding: 60px 40px; text-align: center; page-break-after: always; }}
    .cover h1 {{ font-size: 36px; margin-bottom: 8px; letter-spacing: 1px; }}
    .cover h2 {{ font-size: 22px; font-weight: 300; color: #a8a8d8; }}
    .cover .date {{ font-size: 16px; margin-top: 30px; color: #ccc; }}
    .cover .brand {{ font-size: 14px; margin-top: 60px; color: #888; }}
    .section {{ padding: 20px 40px; }}
    h3 {{ color: #302b63; border-bottom: 2px solid #302b63; padding-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
    th {{ background: #302b63; color: #fff; padding: 8px 6px; text-align: left; }}
    td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
    tr:nth-child(even) {{ background: #f4f4f8; }}
    .summary-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px; margin: 20px 0; }}
    .stat-card {{ background: #f4f4f8; border-radius: 8px; padding: 16px; text-align: center; }}
    .stat-card .num {{ font-size: 28px; font-weight: 700; color: #302b63; }}
    .stat-card .label {{ font-size: 12px; color: #666; margin-top: 4px; }}
    .disclaimer {{ font-size: 10px; color: #999; margin-top: 40px; padding-top: 20px;
                   border-top: 1px solid #ddd; }}
</style>
</head>
<body>

<!-- Cover Page -->
<div class="cover">
    <h1>EVERLIGHT DISTRESSED PROPERTY INTELLIGENCE</h1>
    <h2>{_html_escape(market)} Market Report</h2>
    <div class="date">Week of {week_label}</div>
    <div class="brand">Everlight Ventures -- Institutional Data Services</div>
</div>

<!-- Executive Summary -->
<div class="section">
    <h3>Executive Summary</h3>
    <div class="summary-grid">
        <div class="stat-card">
            <div class="num">{total}</div>
            <div class="label">Total Filings</div>
        </div>
        <div class="stat-card">
            <div class="num">{avg_equity:.1f}%</div>
            <div class="label">Avg Equity</div>
        </div>
        <div class="stat-card">
            <div class="num">{avg_score}</div>
            <div class="label">Avg Score</div>
        </div>
        <div class="stat-card">
            <div class="num">{len(top_10)}</div>
            <div class="label">Top Opportunities</div>
        </div>
    </div>
    <p>This report covers {total} lis pendens filings identified in {_html_escape(market)}.
    Average estimated equity across all properties is {avg_equity:.1f}%. The top-scoring
    opportunities are highlighted below.</p>
</div>

<!-- Full Data Table -->
<div class="section">
    <h3>All Filings -- Sorted by Motivation Score</h3>
    <table>
        <thead>
            <tr>
                <th>#</th><th>Address</th><th>City/State</th><th>Type</th>
                <th>Est. ARV</th><th>Equity</th><th>Score</th>
                <th>Filed</th><th>Days</th>
            </tr>
        </thead>
        <tbody>
            {rows_html if rows_html else '<tr><td colspan="9">No records for this period.</td></tr>'}
        </tbody>
    </table>
</div>

<!-- Market Trends -->
<div class="section">
    <h3>Market Trends</h3>
    <p>{trend_note}</p>
</div>

<!-- Disclaimer -->
<div class="section">
    <div class="disclaimer">
        <strong>DISCLAIMER:</strong> This report is provided for informational purposes only.
        Everlight Ventures makes no warranties regarding the accuracy or completeness of this
        data. Property values are estimates and should be independently verified. This does not
        constitute legal, financial, or investment advice. Recipients are responsible for
        conducting their own due diligence. Data sourced from public court records and third-party
        APIs. Redistribution prohibited without written consent.<br><br>
        &copy; {report_date.year} Everlight Ventures -- All Rights Reserved.
    </div>
</div>

</body>
</html>"""

    return html.encode("utf-8")


def save_report(html_bytes: bytes, market: str, report_date: Optional[date] = None) -> str:
    """Save report HTML to disk and return the file path."""
    report_date = report_date or date.today()
    reports_dir = Path(__file__).parent / "reports" / "intelligence"
    reports_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", market.lower()).strip("_")
    filename = f"everlight_intel_{slug}_{report_date.isoformat()}.html"
    path = reports_dir / filename
    path.write_bytes(html_bytes)
    log.info("Report saved: %s", path)
    return str(path)


# ---------------------------------------------------------------------------
# E. CSV Export by Tier
# ---------------------------------------------------------------------------

BASIC_FIELDS = [
    "address", "city", "state", "zip_code", "filing_date",
    "property_type", "estimated_arv",
]

PRO_FIELDS = BASIC_FIELDS + [
    "owner_name", "equity_estimate", "equity_pct",
    "motivation_score", "days_since_filing",
]

ENTERPRISE_FIELDS = PRO_FIELDS + [
    "owner_mailing_address", "owner_phone", "owner_email",
    "beds", "baths", "sqft", "year_built",
    "mortgage_balance", "amount_owed", "case_number",
    "is_absentee", "county",
]


def export_leads_csv(
    records: list[dict[str, Any]],
    tier: str = "basic",
    output_dir: Optional[str] = None,
) -> str:
    """
    Export leads to CSV filtered by subscription tier.

    Args:
        records: list of enriched record dicts
        tier: 'basic', 'pro', or 'enterprise'
        output_dir: directory to write into (default: reports/intelligence/)

    Returns: absolute path to written CSV file.
    """
    tier = tier.lower()
    if tier == "enterprise":
        fields = ENTERPRISE_FIELDS
    elif tier == "pro":
        fields = PRO_FIELDS
    else:
        fields = BASIC_FIELDS

    out_dir = Path(output_dir) if output_dir else Path(__file__).parent / "reports" / "intelligence"
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"everlight_leads_{tier}_{date.today().isoformat()}.csv"
    path = out_dir / filename

    sorted_records = sorted(
        records, key=lambda r: r.get("motivation_score", 0), reverse=True
    )

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for rec in sorted_records:
            writer.writerow(rec)

    log.info("CSV exported (%s tier, %d records): %s", tier, len(sorted_records), path)
    return str(path)


# ---------------------------------------------------------------------------
# F. Auto-Delivery via Resend
# ---------------------------------------------------------------------------

def deliver_report(
    subscriber_email: str,
    report_path: str,
    csv_path: str,
    market: str = "Multi-Market",
    report_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Send weekly report + CSV to a subscriber via Resend API.

    Env: RESEND_API_KEY must be set.

    Returns: Resend API response dict.
    Raises: ValueError if API key missing, requests.HTTPError on failure.
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise ValueError("RESEND_API_KEY environment variable is not set")

    report_date = report_date or date.today()
    week_label = report_date.strftime("%B %d, %Y")
    subject = (
        f"Everlight Intelligence -- {market} Distressed Property Report "
        f"-- Week of {week_label}"
    )

    # Read attachments
    import base64

    attachments = []
    for fpath, fname_override in [
        (report_path, f"Everlight_Report_{market.replace(' ', '_')}_{report_date.isoformat()}.html"),
        (csv_path, None),
    ]:
        p = Path(fpath)
        if not p.exists():
            log.warning("Attachment not found, skipping: %s", fpath)
            continue
        content_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        attachments.append({
            "filename": fname_override or p.name,
            "content": content_b64,
        })

    payload = {
        "from": "Everlight Intelligence <data@everlightventures.io>",
        "to": [subscriber_email],
        "subject": subject,
        "html": (
            f"<h2>Your Weekly Distressed Property Report</h2>"
            f"<p>Attached is your Everlight Intelligence report for "
            f"<strong>{_html_escape(market)}</strong>, week of {week_label}.</p>"
            f"<p>This report contains {len(attachments)} file(s). "
            f"If you have questions, reply to this email.</p>"
            f"<br><p style='color:#888;font-size:12px;'>"
            f"Everlight Ventures -- Institutional Data Services</p>"
        ),
        "attachments": attachments,
    }

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    log.info("Report delivered to %s -- Resend ID: %s", subscriber_email, result.get("id"))
    return result


# ---------------------------------------------------------------------------
# Supabase Helpers
# ---------------------------------------------------------------------------

def _supabase_headers() -> dict[str, str]:
    """Return auth headers for Supabase REST API."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _supabase_url(table: str) -> str:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    return f"{base}/rest/v1/{table}"


def upsert_records_to_supabase(records: list[dict[str, Any]]) -> int:
    """
    Push enriched lis pendens records to the lis_pendens_records table.
    Uses case_number + address as a dedup key via a content hash.
    Returns count of upserted rows.
    """
    headers = _supabase_headers()
    rows = []
    for r in records:
        rows.append({
            "address": r.get("address", ""),
            "city": r.get("city", ""),
            "state": r.get("state", ""),
            "zip_code": r.get("zip_code"),
            "county": r.get("county"),
            "filing_date": r.get("filing_date"),
            "case_number": r.get("case_number"),
            "amount_owed": r.get("amount_owed"),
            "property_type": r.get("property_type", "sfr"),
            "estimated_arv": r.get("estimated_arv"),
            "equity_pct": r.get("equity_pct"),
            "owner_name": r.get("owner_name"),
            "motivation_score": r.get("motivation_score", 0),
            "enrichment_data": json.dumps({
                k: v for k, v in r.items()
                if k not in (
                    "address", "city", "state", "zip_code", "county",
                    "filing_date", "case_number", "amount_owed",
                    "property_type", "estimated_arv", "equity_pct",
                    "owner_name", "motivation_score",
                )
            }),
        })

    resp = requests.post(
        _supabase_url("lis_pendens_records"),
        headers=headers,
        json=rows,
        timeout=30,
    )
    resp.raise_for_status()
    log.info("Upserted %d records to Supabase", len(rows))
    return len(rows)


def get_active_subscribers(tier: Optional[str] = None) -> list[dict[str, Any]]:
    """Fetch active intelligence subscribers from Supabase."""
    headers = _supabase_headers()
    params = {"status": "eq.active"}
    if tier:
        params["tier"] = f"eq.{tier}"

    resp = requests.get(
        _supabase_url("intelligence_subscribers"),
        headers=headers,
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Orchestrator -- Weekly Run
# ---------------------------------------------------------------------------

def run_weekly_pipeline(
    records: list[dict[str, Any]],
    market: str = "Multi-Market",
) -> dict[str, Any]:
    """
    Full weekly pipeline:
    1. Enrich all raw records
    2. Push to Supabase
    3. Generate report
    4. Export CSVs for each tier
    5. Deliver to subscribers

    Args:
        records: list of raw filing dicts (from scraper or manual import)
        market: market label for branding

    Returns: summary dict with counts and file paths.
    """
    log.info("=== Everlight Intelligence Weekly Pipeline ===")
    log.info("Market: %s | Raw records: %d", market, len(records))

    # 1. Enrich
    enriched = []
    for raw in records:
        try:
            enriched.append(enrich_filing(raw))
        except Exception as exc:
            log.error("Failed to enrich %s: %s", raw.get("address"), exc)
    log.info("Enriched %d / %d records", len(enriched), len(records))

    # 2. Push to Supabase
    try:
        upsert_records_to_supabase(enriched)
    except Exception as exc:
        log.error("Supabase upsert failed: %s", exc)

    # 3. Generate report
    html_bytes = generate_weekly_report(enriched, market)
    report_path = save_report(html_bytes, market)

    # 4. Export CSVs
    csv_paths = {}
    for tier in ("basic", "pro", "enterprise"):
        csv_paths[tier] = export_leads_csv(enriched, tier)

    # 5. Deliver to subscribers
    delivered = 0
    try:
        subscribers = get_active_subscribers()
    except Exception as exc:
        log.error("Could not fetch subscribers: %s", exc)
        subscribers = []

    for sub in subscribers:
        sub_tier = sub.get("tier", "basic")
        sub_markets = sub.get("markets", [])
        # Only send if subscriber covers this market (or has no market filter)
        if sub_markets and market not in sub_markets:
            continue
        csv_for_tier = csv_paths.get(sub_tier, csv_paths["basic"])
        try:
            deliver_report(sub["email"], report_path, csv_for_tier, market)
            delivered += 1
        except Exception as exc:
            log.error("Delivery failed for %s: %s", sub["email"], exc)

    summary = {
        "market": market,
        "total_raw": len(records),
        "enriched": len(enriched),
        "report_path": report_path,
        "csv_paths": csv_paths,
        "subscribers_delivered": delivered,
        "run_date": date.today().isoformat(),
    }
    log.info("Pipeline complete: %s", json.dumps(summary, indent=2))
    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Everlight Lis Pendens Intelligence Pipeline"
    )
    sub = parser.add_subparsers(dest="command")

    # List counties
    sub.add_parser("counties", help="List configured county sources")

    # Generate FOIA letter
    foia_cmd = sub.add_parser("foia", help="Print FOIA request for a county")
    foia_cmd.add_argument("county_key", choices=list(COUNTY_SOURCES.keys()))

    # Run pipeline from a JSON file of raw records
    run_cmd = sub.add_parser("run", help="Run weekly pipeline from JSON input")
    run_cmd.add_argument("input_file", help="Path to JSON array of raw filings")
    run_cmd.add_argument("--market", default="Multi-Market", help="Market label")

    # Export CSV only
    export_cmd = sub.add_parser("export", help="Export CSV from JSON input")
    export_cmd.add_argument("input_file")
    export_cmd.add_argument("--tier", default="basic", choices=["basic", "pro", "enterprise"])

    # Generate report only
    report_cmd = sub.add_parser("report", help="Generate HTML report from JSON input")
    report_cmd.add_argument("input_file")
    report_cmd.add_argument("--market", default="Multi-Market")

    args = parser.parse_args()

    if args.command == "counties":
        for c in list_counties():
            print(f"  {c['key']:20s}  {c['county']}, {c['state']}")

    elif args.command == "foia":
        print(generate_foia_request(args.county_key))

    elif args.command == "run":
        with open(args.input_file) as f:
            raw = json.load(f)
        run_weekly_pipeline(raw, args.market)

    elif args.command == "export":
        with open(args.input_file) as f:
            raw = json.load(f)
        enriched = [enrich_filing(r) for r in raw]
        path = export_leads_csv(enriched, args.tier)
        print(f"Exported: {path}")

    elif args.command == "report":
        with open(args.input_file) as f:
            raw = json.load(f)
        enriched = [enrich_filing(r) for r in raw]
        html = generate_weekly_report(enriched, args.market)
        path = save_report(html, args.market)
        print(f"Report: {path}")

    else:
        parser.print_help()
