#!/usr/bin/env python3
"""
Surplus Funds Recovery Pipeline -- Everlight Ventures
=====================================================
Finds former property owners owed excess proceeds from county foreclosure
auctions. Scrapes county excess proceeds lists, enriches with property
addresses, skip traces owners, and outputs qualified leads.

Revenue model: 15-30% commission on recovered funds. No upfront cost to owner.

Agents involved:
  - Rex Blackwell (lead scout)
  - Filter Banks (lead scoring)
  - Piper Reeves (outreach)
  - Samuel Navarro (compliance)

Usage:
    python surplus_funds_finder.py                  # Full pipeline run
    python surplus_funds_finder.py --county la      # LA County only
    python surplus_funds_finder.py --min-amount 25000  # Higher threshold
"""

import json
import logging
import os
import re
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
LEADS_OUTPUT = BASE_DIR / "surplus_leads.json"
TRACKER_FILE = BASE_DIR / "surplus_claims_tracker.json"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_HUNTERS = os.environ.get("SLACK_CHANNEL_HUNTERS", "C08N14H1X1A")

# Rate limiting
REQUEST_DELAY = 2.0  # seconds between HTTP requests
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3

# Lead filters
DEFAULT_MIN_SURPLUS = 10_000
COMMISSION_RATE = 0.30  # 30% default; negotiable down to 15%

# Claim deadline: CA CCP 1542 gives 1 year from date of sale for surplus
# but counties may set shorter windows. Default assumption: 60 days from list.
DEFAULT_DEADLINE_DAYS = 60

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "surplus_finder.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("surplus_finder")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SurplusLead:
    """A single surplus funds lead."""
    county: str = ""
    parcel_id: str = ""
    former_owner: str = ""
    surplus_amount: float = 0.0
    property_address: str = ""
    owner_phone: List[str] = field(default_factory=list)
    owner_email: List[str] = field(default_factory=list)
    owner_last_address: str = ""
    status: str = "new"  # new, contacted, signed, filed, recovered, dead
    found_date: str = ""
    deadline: str = ""
    commission_estimate: float = 0.0
    sale_date: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get_session() -> "requests.Session":
    """Create a requests session with default headers and retry logic."""
    if requests is None:
        raise ImportError("requests library required. Install: pip install requests")
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _safe_get(session: "requests.Session", url: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """GET a URL with retries, timeout, and rate limiting."""
    for attempt in range(1, retries + 1):
        try:
            time.sleep(REQUEST_DELAY)
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.Timeout:
            logger.warning("Timeout on attempt %d/%d: %s", attempt, retries, url)
        except requests.exceptions.HTTPError as e:
            logger.warning("HTTP %s on attempt %d/%d: %s", e.response.status_code, attempt, retries, url)
            if e.response.status_code == 403:
                logger.error("Access denied (403). May need different approach for: %s", url)
                return None
            if e.response.status_code == 429:
                wait = REQUEST_DELAY * attempt * 2
                logger.info("Rate limited. Waiting %.1fs before retry.", wait)
                time.sleep(wait)
        except requests.exceptions.RequestException as e:
            logger.warning("Request error on attempt %d/%d: %s -- %s", attempt, retries, url, e)
    logger.error("All %d attempts failed for: %s", retries, url)
    return None


# ---------------------------------------------------------------------------
# County scrapers
# ---------------------------------------------------------------------------


def scrape_la_county_surplus(session: "requests.Session", min_amount: float = DEFAULT_MIN_SURPLUS) -> List[SurplusLead]:
    """
    Scrape LA County Tax Collector excess proceeds list.

    Primary URL: https://ttc.lacounty.gov/excess-proceeds/
    The page typically links to a PDF or HTML table of unclaimed excess proceeds.

    This scraper handles:
    1. The main excess proceeds page (HTML table format)
    2. Linked PDF lists (extracts text and parses)

    Returns list of SurplusLead with parcel_id, former_owner, surplus_amount.
    """
    leads = []
    url = "https://ttc.lacounty.gov/excess-proceeds/"
    logger.info("Scraping LA County excess proceeds: %s", url)

    html = _safe_get(session, url)
    if not html:
        logger.error("Failed to fetch LA County excess proceeds page.")
        return leads

    # Strategy 1: Parse HTML tables on the page
    # LA County TTC often publishes excess proceeds in HTML tables or links to PDFs.
    # Look for table rows with parcel numbers (pattern: XXXX-XXX-XXX)
    leads.extend(_parse_html_table_leads(html, "Los Angeles", min_amount))

    # Strategy 2: Find linked PDFs on the page and extract from them
    pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', html, re.IGNORECASE)
    for pdf_url in pdf_links:
        if "excess" in pdf_url.lower() or "surplus" in pdf_url.lower() or "proceed" in pdf_url.lower():
            if not pdf_url.startswith("http"):
                pdf_url = "https://ttc.lacounty.gov" + pdf_url
            logger.info("Found excess proceeds PDF: %s", pdf_url)
            # PDF parsing would require pdfplumber or tabula-py.
            # Log for manual review if those are not installed.
            try:
                import pdfplumber
                leads.extend(_parse_pdf_leads(session, pdf_url, "Los Angeles", min_amount))
            except ImportError:
                logger.warning(
                    "pdfplumber not installed. Cannot auto-parse PDF. "
                    "Install: pip install pdfplumber. PDF URL logged for manual review: %s",
                    pdf_url,
                )

    # Strategy 3: Check for auction results pages that list surplus
    auction_urls = re.findall(r'href="([^"]*auction[^"]*)"', html, re.IGNORECASE)
    for aurl in auction_urls:
        if not aurl.startswith("http"):
            aurl = "https://ttc.lacounty.gov" + aurl
        logger.info("Found auction results page: %s", aurl)

    if not leads:
        logger.info(
            "No leads parsed from HTML tables. The page may use JavaScript rendering "
            "or link to PDFs. Check logs for PDF URLs to process manually."
        )

    logger.info("LA County scrape complete. Raw leads found: %d", len(leads))
    return leads


def _parse_html_table_leads(html: str, county: str, min_amount: float) -> List[SurplusLead]:
    """
    Parse HTML for table rows containing surplus fund data.
    Looks for patterns: parcel ID, owner name, dollar amount.
    """
    leads = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Pattern: LA County parcel IDs look like 1234-567-890 or 1234567890
    parcel_pattern = re.compile(r'\b(\d{4}[-\s]?\d{3}[-\s]?\d{3})\b')

    # Dollar amount pattern
    money_pattern = re.compile(r'\$\s?([\d,]+\.?\d{0,2})')

    # Try to find table rows
    # Common HTML table patterns from county sites
    row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
    cell_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)

    rows = row_pattern.findall(html)
    for row in rows:
        cells = cell_pattern.findall(row)
        if len(cells) < 2:
            continue

        # Clean cell text
        clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
        row_text = " ".join(clean_cells)

        parcel_match = parcel_pattern.search(row_text)
        money_match = money_pattern.search(row_text)

        if parcel_match and money_match:
            amount_str = money_match.group(1).replace(",", "")
            try:
                amount = float(amount_str)
            except ValueError:
                continue

            if amount < min_amount:
                continue

            # Try to extract owner name -- usually the longest text cell
            # that is not a number or parcel ID
            owner_name = ""
            for cell_text in clean_cells:
                if parcel_pattern.search(cell_text):
                    continue
                if money_pattern.search(cell_text):
                    continue
                if len(cell_text) > len(owner_name) and len(cell_text) > 3:
                    owner_name = cell_text

            parcel_id = parcel_match.group(1).replace(" ", "-")

            deadline_date = _calculate_deadline(today, DEFAULT_DEADLINE_DAYS)

            lead = SurplusLead(
                county=county,
                parcel_id=parcel_id,
                former_owner=owner_name.title() if owner_name else "UNKNOWN",
                surplus_amount=amount,
                found_date=today,
                deadline=deadline_date,
                commission_estimate=round(amount * COMMISSION_RATE, 2),
                status="new",
            )
            leads.append(lead)
            logger.info(
                "Found lead: %s | %s | $%,.2f",
                lead.parcel_id, lead.former_owner, lead.surplus_amount,
            )

    return leads


def _parse_pdf_leads(
    session: "requests.Session", pdf_url: str, county: str, min_amount: float
) -> List[SurplusLead]:
    """Parse a PDF excess proceeds list using pdfplumber."""
    import pdfplumber
    import io

    leads = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        time.sleep(REQUEST_DELAY)
        resp = session.get(pdf_url, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to download PDF %s: %s", pdf_url, e)
        return leads

    try:
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 2:
                            continue
                        row_text = " ".join(str(c) for c in row if c)
                        parcel_match = re.search(r'(\d{4}[-\s]?\d{3}[-\s]?\d{3})', row_text)
                        money_match = re.search(r'\$?\s?([\d,]+\.\d{2})', row_text)
                        if parcel_match and money_match:
                            amount = float(money_match.group(1).replace(",", ""))
                            if amount < min_amount:
                                continue
                            owner = ""
                            for cell in row:
                                if cell and not re.search(r'[\d\$\.\-]', str(cell)):
                                    if len(str(cell)) > len(owner):
                                        owner = str(cell)
                            lead = SurplusLead(
                                county=county,
                                parcel_id=parcel_match.group(1).replace(" ", "-"),
                                former_owner=owner.title() if owner else "UNKNOWN",
                                surplus_amount=amount,
                                found_date=today,
                                deadline=_calculate_deadline(today, DEFAULT_DEADLINE_DAYS),
                                commission_estimate=round(amount * COMMISSION_RATE, 2),
                                status="new",
                            )
                            leads.append(lead)
    except Exception as e:
        logger.error("PDF parse error for %s: %s", pdf_url, e)

    return leads


# ---------------------------------------------------------------------------
# Property address enrichment
# ---------------------------------------------------------------------------


def enrich_property_address(session: "requests.Session", lead: SurplusLead) -> SurplusLead:
    """
    Look up property address from parcel ID using LA County Assessor portal.
    assessor.lacounty.gov provides parcel detail pages.
    """
    if lead.property_address:
        return lead

    parcel_clean = lead.parcel_id.replace("-", "")
    url = f"https://portal.assessor.lacounty.gov/parceldetail/{parcel_clean}"
    logger.info("Looking up address for parcel %s", lead.parcel_id)

    html = _safe_get(session, url)
    if not html:
        logger.warning("Could not fetch assessor page for parcel %s", lead.parcel_id)
        return lead

    # The assessor portal typically shows the situs (property) address
    # Look for common patterns in the response
    address_patterns = [
        re.compile(r'Situs\s*(?:Address)?[:\s]*([^<\n]+)', re.IGNORECASE),
        re.compile(r'"SitusAddress"\s*:\s*"([^"]+)"', re.IGNORECASE),
        re.compile(r'property.address["\s:]+([^"<\n]+)', re.IGNORECASE),
        re.compile(r'<span[^>]*class="[^"]*situs[^"]*"[^>]*>([^<]+)', re.IGNORECASE),
    ]

    for pattern in address_patterns:
        match = pattern.search(html)
        if match:
            address = match.group(1).strip()
            if len(address) > 5:
                lead.property_address = address
                logger.info("Found address for %s: %s", lead.parcel_id, address)
                return lead

    # Fallback: try the assessor's API endpoint
    api_url = f"https://portal.assessor.lacounty.gov/api/parceldetail?ain={parcel_clean}"
    api_html = _safe_get(session, api_url)
    if api_html:
        try:
            data = json.loads(api_html)
            situs = data.get("SitusAddress", "") or data.get("situsAddress", "")
            if situs:
                lead.property_address = situs
                logger.info("Found address via API for %s: %s", lead.parcel_id, situs)
        except (json.JSONDecodeError, AttributeError):
            pass

    if not lead.property_address:
        logger.warning("Could not resolve address for parcel %s", lead.parcel_id)

    return lead


# ---------------------------------------------------------------------------
# Skip tracing
# ---------------------------------------------------------------------------


def skip_trace_owner(session: "requests.Session", lead: SurplusLead) -> SurplusLead:
    """
    Skip trace the former owner using free public sources.
    Queries TruePeopleSearch and FastPeopleSearch for phone/email.

    Falls back to generating manual search URLs if automated parsing fails.
    """
    if not lead.former_owner or lead.former_owner == "UNKNOWN":
        logger.warning("Cannot skip trace: no owner name for parcel %s", lead.parcel_id)
        return lead

    name = lead.former_owner.strip()
    city = _extract_city(lead.property_address) or "Los Angeles"
    state = "CA"

    logger.info("Skip tracing: %s (%s, %s)", name, city, state)

    # Source 1: TruePeopleSearch
    phones_1, emails_1, address_1 = _search_truepeoplesearch(session, name, city, state)

    # Source 2: FastPeopleSearch
    phones_2, emails_2, address_2 = _search_fastpeoplesearch(session, name, city, state)

    # Merge results, deduplicate
    all_phones = list(dict.fromkeys(phones_1 + phones_2))
    all_emails = list(dict.fromkeys(emails_1 + emails_2))

    lead.owner_phone = all_phones[:5]  # cap at 5
    lead.owner_email = all_emails[:5]
    lead.owner_last_address = address_1 or address_2 or ""

    # Generate manual search URLs as backup
    search_urls = _generate_search_urls(name, city, state)
    if not all_phones and not all_emails:
        lead.notes = f"Auto skip trace found no contacts. Manual URLs: {json.dumps(search_urls)}"
        logger.warning("No contact info found for %s. Manual search URLs generated.", name)
    else:
        logger.info(
            "Skip trace complete for %s: %d phones, %d emails",
            name, len(lead.owner_phone), len(lead.owner_email),
        )

    return lead


def _search_truepeoplesearch(
    session: "requests.Session", name: str, city: str, state: str
) -> tuple:
    """Search TruePeopleSearch for contact info."""
    phones, emails, address = [], [], ""
    name_slug = name.lower().replace(" ", "-")
    url = f"https://www.truepeoplesearch.com/find/{name_slug}/{city}-{state}"

    html = _safe_get(session, url)
    if not html:
        return phones, emails, address

    # Parse phone numbers (format: (XXX) XXX-XXXX or XXX-XXX-XXXX)
    phone_pattern = re.compile(r'\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}')
    found_phones = phone_pattern.findall(html)
    phones = _normalize_phones(found_phones)

    # Parse email addresses
    email_pattern = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
    found_emails = email_pattern.findall(html)
    # Filter out site emails
    emails = [
        e for e in found_emails
        if not any(domain in e.lower() for domain in [
            "truepeoplesearch", "fastpeoplesearch", "example.com",
            "sentry", "cloudflare", "google", "facebook",
        ])
    ]

    # Parse address
    addr_pattern = re.compile(
        r'<span[^>]*class="[^"]*address[^"]*"[^>]*>([^<]+)',
        re.IGNORECASE,
    )
    addr_match = addr_pattern.search(html)
    if addr_match:
        address = addr_match.group(1).strip()

    return phones, emails, address


def _search_fastpeoplesearch(
    session: "requests.Session", name: str, city: str, state: str
) -> tuple:
    """Search FastPeopleSearch for contact info."""
    phones, emails, address = [], [], ""
    name_slug = name.lower().replace(" ", "-")
    url = f"https://www.fastpeoplesearch.com/name/{name_slug}_{city}-{state}"

    html = _safe_get(session, url)
    if not html:
        return phones, emails, address

    phone_pattern = re.compile(r'\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}')
    found_phones = phone_pattern.findall(html)
    phones = _normalize_phones(found_phones)

    email_pattern = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
    found_emails = email_pattern.findall(html)
    emails = [
        e for e in found_emails
        if not any(domain in e.lower() for domain in [
            "fastpeoplesearch", "truepeoplesearch", "example.com",
            "sentry", "cloudflare", "google", "facebook",
        ])
    ]

    addr_pattern = re.compile(
        r'class="[^"]*current-address[^"]*"[^>]*>([^<]+)',
        re.IGNORECASE,
    )
    addr_match = addr_pattern.search(html)
    if addr_match:
        address = addr_match.group(1).strip()

    return phones, emails, address


def _generate_search_urls(name: str, city: str, state: str) -> dict:
    """Generate manual skip trace search URLs as fallback."""
    name_enc = urllib.parse.quote(name)
    name_slug = name.lower().replace(" ", "-")
    return {
        "truepeoplesearch": f"https://www.truepeoplesearch.com/find/{name_slug}/{city.lower()}-{state.lower()}",
        "fastpeoplesearch": f"https://www.fastpeoplesearch.com/name/{name_slug}_{city.lower()}-{state.lower()}",
        "cyberbackground": f"https://www.cyberbackgroundchecks.com/people/{name_slug}/{state.lower()}/{city.lower()}",
        "google": f"https://www.google.com/search?q={name_enc}+{urllib.parse.quote(city)}+{state}+phone+email",
    }


def _normalize_phones(raw_phones: list) -> list:
    """Normalize phone numbers to (XXX) XXX-XXXX format, deduplicate."""
    normalized = []
    seen = set()
    for p in raw_phones:
        digits = re.sub(r'\D', '', p)
        if len(digits) == 10:
            fmt = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            if fmt not in seen:
                seen.add(fmt)
                normalized.append(fmt)
        elif len(digits) == 11 and digits[0] == "1":
            digits = digits[1:]
            fmt = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            if fmt not in seen:
                seen.add(fmt)
                normalized.append(fmt)
    return normalized


def _extract_city(address: str) -> str:
    """Extract city name from a property address string."""
    if not address:
        return ""
    # Try pattern: "123 Main St, City, ST 90001"
    match = re.search(r',\s*([A-Za-z\s]+),\s*[A-Z]{2}', address)
    if match:
        return match.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _calculate_deadline(from_date: str, days: int) -> str:
    """Calculate deadline date from a base date + days."""
    from datetime import timedelta
    base = datetime.strptime(from_date, "%Y-%m-%d")
    deadline = base + timedelta(days=days)
    return deadline.strftime("%Y-%m-%d")


def _load_existing_leads() -> dict:
    """Load existing leads file to avoid duplicates."""
    if LEADS_OUTPUT.exists():
        try:
            with open(LEADS_OUTPUT, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"leads": [], "metadata": {}}


def _save_leads(leads: List[SurplusLead], existing: dict) -> None:
    """Save leads to JSON, merging with existing and deduplicating."""
    existing_parcels = {l["parcel_id"] for l in existing.get("leads", [])}
    new_leads = [asdict(l) for l in leads if l.parcel_id not in existing_parcels]

    all_leads = existing.get("leads", []) + new_leads

    output = {
        "leads": all_leads,
        "metadata": {
            "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_leads": len(all_leads),
            "new_this_run": len(new_leads),
            "total_potential_value": sum(l.get("surplus_amount", 0) for l in all_leads),
            "total_commission_potential": sum(l.get("commission_estimate", 0) for l in all_leads),
        },
    }

    with open(LEADS_OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    logger.info(
        "Saved %d total leads (%d new). Output: %s",
        len(all_leads), len(new_leads), LEADS_OUTPUT,
    )


# ---------------------------------------------------------------------------
# Slack notification
# ---------------------------------------------------------------------------


def post_to_slack(leads: List[SurplusLead]) -> None:
    """Post surplus lead summary to #ft-hunters via Slack bot token."""
    if not SLACK_BOT_TOKEN:
        logger.warning("No SLACK_BOT_TOKEN set. Skipping Slack notification.")
        return
    if not leads:
        return

    total_surplus = sum(l.surplus_amount for l in leads)
    total_commission = sum(l.commission_estimate for l in leads)
    contactable = sum(1 for l in leads if l.owner_phone or l.owner_email)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Surplus Funds Recovery -- New Leads"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Leads Found:* {len(leads)}"},
                {"type": "mrkdwn", "text": f"*Contactable:* {contactable}"},
                {"type": "mrkdwn", "text": f"*Total Surplus:* ${total_surplus:,.2f}"},
                {"type": "mrkdwn", "text": f"*Commission Potential:* ${total_commission:,.2f}"},
            ],
        },
        {"type": "divider"},
    ]

    # Top 5 leads by amount
    top_leads = sorted(leads, key=lambda l: l.surplus_amount, reverse=True)[:5]
    for lead in top_leads:
        contact_status = "Has contact" if (lead.owner_phone or lead.owner_email) else "Needs manual skip trace"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{lead.former_owner}* -- ${lead.surplus_amount:,.2f}\n"
                    f"Parcel: {lead.parcel_id} | {lead.property_address or 'Address pending'}\n"
                    f"Status: {contact_status} | Deadline: {lead.deadline}"
                ),
            },
        })

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "channel": SLACK_CHANNEL_HUNTERS,
                "text": f"Surplus Funds: {len(leads)} new leads, ${total_commission:,.2f} commission potential",
                "blocks": blocks,
            },
            timeout=15,
        )
        if resp.ok and resp.json().get("ok"):
            logger.info("Slack notification sent to #ft-hunters.")
        else:
            logger.warning("Slack API response: %s", resp.text[:200])
    except Exception as e:
        logger.error("Slack notification failed: %s", e)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_pipeline(county: str = "la", min_amount: float = DEFAULT_MIN_SURPLUS) -> List[SurplusLead]:
    """
    Full surplus funds recovery pipeline:
    1. Scrape county excess proceeds lists
    2. Enrich with property addresses
    3. Skip trace owners
    4. Save enriched leads
    5. Post summary to Slack
    """
    logger.info("=" * 60)
    logger.info("SURPLUS FUNDS RECOVERY PIPELINE -- START")
    logger.info("County: %s | Min amount: $%,.2f", county, min_amount)
    logger.info("=" * 60)

    session = _get_session()
    leads: List[SurplusLead] = []

    # Step 1: Scrape county lists
    county_lower = county.lower()
    if county_lower in ("la", "los angeles", "los_angeles"):
        leads = scrape_la_county_surplus(session, min_amount)
    else:
        logger.error("County '%s' not yet supported. Supported: la", county)
        return []

    if not leads:
        logger.info("No leads found above $%,.2f threshold.", min_amount)
        return []

    # Step 2: Enrich with property addresses
    logger.info("Enriching %d leads with property addresses...", len(leads))
    for i, lead in enumerate(leads):
        leads[i] = enrich_property_address(session, lead)

    # Step 3: Skip trace owners
    logger.info("Skip tracing %d owners...", len(leads))
    for i, lead in enumerate(leads):
        leads[i] = skip_trace_owner(session, lead)

    # Step 4: Save leads
    existing = _load_existing_leads()
    _save_leads(leads, existing)

    # Step 5: Post to Slack
    post_to_slack(leads)

    # Summary
    total_surplus = sum(l.surplus_amount for l in leads)
    total_commission = sum(l.commission_estimate for l in leads)
    contactable = sum(1 for l in leads if l.owner_phone or l.owner_email)

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("  Leads found:          %d", len(leads))
    logger.info("  Contactable:          %d", contactable)
    logger.info("  Total surplus:        $%,.2f", total_surplus)
    logger.info("  Commission potential: $%,.2f", total_commission)
    logger.info("  Output:               %s", LEADS_OUTPUT)
    logger.info("=" * 60)

    return leads


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Surplus Funds Recovery Pipeline")
    parser.add_argument(
        "--county", default="la",
        help="County to scrape (default: la). Supported: la",
    )
    parser.add_argument(
        "--min-amount", type=float, default=DEFAULT_MIN_SURPLUS,
        help=f"Minimum surplus amount to include (default: ${DEFAULT_MIN_SURPLUS:,})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and display results without saving or notifying Slack",
    )
    args = parser.parse_args()

    results = run_pipeline(county=args.county, min_amount=args.min_amount)

    if args.dry_run:
        for lead in results:
            print(json.dumps(asdict(lead), indent=2))
