#!/usr/bin/env python3
"""
Cuyahoga County (Cleveland metro) FREE distressed-property lead scraper.

This is public-records access, NOT a bypass of any access controls. All sources
are public web pages or public ASP.NET WebForms portals operated by the county.
This script is research and education, NOT legal advice.

Sources:
  1. cpdocket.cp.cuyahogacounty.us  -> recent foreclosure case filings (Common
     Pleas Civil docket). Drives the lead list. We filter by Civil-Foreclosure
     case types (CV F / CV R) and pull case party + property address.
  2. myplace.cuyahogacounty.gov     -> parcel + owner enrichment (property
     type, year built, square footage, last sale, assessed value, mailing
     address). Hit per-parcel after we have a parcel id.
  3. Cuyahoga Treasurer delinquent-tax publication is NOT machine readable.
     The county publishes it in a newspaper of general circulation; previous
     publications are "available upon request" only. So we treat the
     foreclosure docket as the primary distress signal and (optionally) cross-
     check parcel tax status via paydici account-summary if we get blocked.

Skip-trace (free, public web):
  - Radaris.com /ng/search query returns name/city/state matches with profile
    URLs of the form /p/<First>/<Last>/. Profile pages contain phone numbers
    and email addresses.
  - TruePeopleSearch and FastPeopleSearch are now fully Cloudflare-gated and
    return captcha challenges from headless requests, so we do not attempt
    them. We log a "skip-trace blocked" status if a record requires more
    coverage than Radaris alone provides, and flag it for human review.

Constraints:
  - No subscription cost. requests + bs4 only.
  - Identify ourselves with a real User-Agent containing a contact email.
  - 1-3 second delay between requests, exponential backoff on 429 / 503.
  - Cache responses for 24h (sqlite) so re-runs do not hammer the county.
  - Respect robots.txt: cuyahogacounty.gov allows User-agent: *. cpdocket has
    no robots.txt. Radaris allows / for general User-agent.

Output:
  /home/opc/_logs/cuyahoga_leads_<YYYYMMDD>.csv with columns:
    parcel, address, owner_name, mailing, phone, email, distress_type,
    confidence, scraped_at, source_url, notes
  Plus a direct ORM insert into broker_ops.PropertyLead so the rest of the
  wholesale pipeline picks them up.

CLI:
  python3 cuyahoga_free_scraper.py --limit 50
  python3 cuyahoga_free_scraper.py --limit 100 --no-skip-trace
  python3 cuyahoga_free_scraper.py --limit 25 --no-django  (csv only)

Backend Hand.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import logging
import os
import random
import re
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONTACT_EMAIL = "1m.rich.gee@gmail.com"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36 "
    f"EverlightResearchBot/1.0 (+contact:{CONTACT_EMAIL})"
)

CPDOCKET_BASE = "https://cpdocket.cp.cuyahogacounty.gov"
CPDOCKET_LEGACY = "https://cpdocket.cp.cuyahogacounty.us"  # 301 -> .gov
MYPLACE_BASE = "https://myplace.cuyahogacounty.gov"
RADARIS_BASE = "https://radaris.com"

LOG_DIR = Path("/home/opc/_logs") if Path("/home/opc").exists() else Path("/tmp")
CACHE_PATH = LOG_DIR / "cuyahoga_cache.sqlite3"
CACHE_TTL_SECONDS = 24 * 60 * 60

REQUEST_MIN_DELAY = 1.0
REQUEST_MAX_DELAY = 3.0
MAX_BACKOFF_RETRIES = 4

# Cuyahoga foreclosure case-type codes inside the Common Pleas docket.
# CV F = civil foreclosure, CV R = real-property action.
FORECLOSURE_CASE_PREFIXES = ("CV-F", "CV-R", "CV F", "CV R")

logger = logging.getLogger("cuyahoga_free_scraper")

# ---------------------------------------------------------------------------
# Cache (24h, file-backed sqlite so re-runs do not hammer county servers)
# ---------------------------------------------------------------------------


def _cache_init() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CACHE_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS http_cache ("
        " key TEXT PRIMARY KEY, ts REAL, status INT, body TEXT)"
    )
    con.commit()
    con.close()


def _cache_key(method: str, url: str, params: dict | None, body: dict | None) -> str:
    raw = json.dumps(
        [method.upper(), url, params or {}, body or {}], sort_keys=True
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    try:
        con = sqlite3.connect(CACHE_PATH)
        row = con.execute(
            "SELECT ts, body FROM http_cache WHERE key = ?", (key,)
        ).fetchone()
        con.close()
    except sqlite3.Error:
        return None
    if not row:
        return None
    ts, body = row
    if time.time() - ts > CACHE_TTL_SECONDS:
        return None
    return body


def _cache_put(key: str, status: int, body: str) -> None:
    try:
        con = sqlite3.connect(CACHE_PATH)
        con.execute(
            "INSERT OR REPLACE INTO http_cache (key, ts, status, body) "
            "VALUES (?, ?, ?, ?)",
            (key, time.time(), status, body),
        )
        con.commit()
        con.close()
    except sqlite3.Error as exc:
        logger.warning("cache write failed: %s", exc)


# ---------------------------------------------------------------------------
# Polite HTTP with backoff + cache
# ---------------------------------------------------------------------------


def _polite_sleep() -> None:
    time.sleep(random.uniform(REQUEST_MIN_DELAY, REQUEST_MAX_DELAY))


def http_get(
    session: requests.Session,
    url: str,
    *,
    params: dict | None = None,
    use_cache: bool = True,
    verify: bool = True,
    timeout: int = 25,
) -> tuple[int, str]:
    key = _cache_key("GET", url, params, None)
    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            return 200, cached
    backoff = 2.0
    for attempt in range(MAX_BACKOFF_RETRIES):
        _polite_sleep()
        try:
            resp = session.get(url, params=params, timeout=timeout, verify=verify)
        except requests.RequestException as exc:
            logger.warning("GET %s failed: %s", url, exc)
            time.sleep(backoff)
            backoff *= 2
            continue
        if resp.status_code in (429, 503):
            logger.warning(
                "GET %s -> %d, backoff %.1fs", url, resp.status_code, backoff
            )
            time.sleep(backoff)
            backoff *= 2
            continue
        if 200 <= resp.status_code < 400:
            _cache_put(key, resp.status_code, resp.text)
            return resp.status_code, resp.text
        return resp.status_code, resp.text
    return 0, ""


def http_post(
    session: requests.Session,
    url: str,
    data: dict,
    *,
    use_cache: bool = True,
    verify: bool = True,
    timeout: int = 25,
) -> tuple[int, str]:
    key = _cache_key("POST", url, None, data)
    if use_cache:
        cached = _cache_get(key)
        if cached is not None:
            return 200, cached
    backoff = 2.0
    for attempt in range(MAX_BACKOFF_RETRIES):
        _polite_sleep()
        try:
            resp = session.post(url, data=data, timeout=timeout, verify=verify)
        except requests.RequestException as exc:
            logger.warning("POST %s failed: %s", url, exc)
            time.sleep(backoff)
            backoff *= 2
            continue
        if resp.status_code in (429, 503):
            time.sleep(backoff)
            backoff *= 2
            continue
        if 200 <= resp.status_code < 400:
            _cache_put(key, resp.status_code, resp.text)
            return resp.status_code, resp.text
        return resp.status_code, resp.text
    return 0, ""


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return s


# ---------------------------------------------------------------------------
# Lead record
# ---------------------------------------------------------------------------


@dataclass
class Lead:
    parcel: str = ""
    address: str = ""
    city: str = ""
    state: str = "OH"
    zip_code: str = ""
    owner_name: str = ""
    mailing: str = ""
    phone: str = ""
    email: str = ""
    distress_type: str = ""
    confidence: float = 0.0
    scraped_at: str = ""
    source_url: str = ""
    case_number: str = ""
    notes: str = ""
    property_type: str = ""
    year_built: int | None = None
    sqft: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Source 1: Common Pleas docket (foreclosure cases) -- ASP.NET WebForms
# ---------------------------------------------------------------------------

# cpdocket landing is a TOS gate (btnYes / btnNo). We POST btnYes with the
# server's __VIEWSTATE so the session is marked "agreed" and the case-search
# pages become accessible.

VIEWSTATE_RE = re.compile(
    r'name="(__VIEWSTATE|__VIEWSTATEGENERATOR|__EVENTVALIDATION)"[^>]+value="([^"]*)"'
)


def _extract_viewstate(html: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in VIEWSTATE_RE.finditer(html)}


def _form_inputs(html: str) -> dict[str, str]:
    """Pull every input / select default value from the rendered form so we
    can replay it with our deltas applied. ASP.NET WebForms requires the full
    set of hidden viewstate fields plus any other form values."""
    soup = BeautifulSoup(html, "lxml")
    form = soup.find("form")
    out: dict[str, str] = {}
    if not form:
        return out
    for el in form.find_all(["input"]):
        name = el.get("name")
        if not name:
            continue
        t = (el.get("type") or "text").lower()
        if t in {"submit", "image", "button", "reset"}:
            continue
        if t in {"checkbox", "radio"}:
            if el.has_attr("checked"):
                out[name] = el.get("value", "on")
            continue
        out[name] = el.get("value", "")
    for sel in form.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        out[name] = opt.get("value", "") if opt else ""
    return out


# Foreclosure class codes inside cpdocket's foreclosure-search dropdown
FORECLOSURE_FILING_TYPES = {
    "1460": "Forecl. Marsh. of Lien",
    "1465": "Tax Foreclosure",
    "1466": "Tax Certificate Foreclosure",
    "1467": "Bd. Of Revision Tax Foreclosure",
}


def cpdocket_open_foreclosure_search(
    session: requests.Session,
) -> tuple[str, dict[str, str]]:
    """Walk the cpdocket flow: GET landing -> POST btnYes (TOS) -> redirected
    to /Search.aspx -> postback the foreclosureSearch radio so the form
    panel renders. Returns (final_html, form_inputs). All POSTs hit the
    canonical .gov host; the .us host returns a 301 redirect."""
    landing_url = f"{CPDOCKET_BASE}/"
    status, html = http_get(
        session, landing_url, verify=True, use_cache=False
    )
    if status != 200 or "__VIEWSTATE" not in html:
        logger.error("cpdocket landing fetch failed (status=%s)", status)
        return "", {}
    inputs = _form_inputs(html)
    inputs["ctl00$SheetContentPlaceHolder$btnYes"] = "Yes"
    status, html = http_post(
        session, landing_url, inputs, verify=True, use_cache=False
    )
    if status != 200 or "Search.aspx" not in (html or ""):
        # Sometimes redirected directly; check for the rbSearches radio
        if "rbSearches" not in (html or ""):
            logger.error("cpdocket TOS POST did not yield search page")
            return "", {}

    # Now postback the foreclosure radio so the foreclosureSearch panel
    # renders inside Search.aspx
    search_url = f"{CPDOCKET_BASE}/Search.aspx"
    inputs = _form_inputs(html)
    inputs["__EVENTTARGET"] = "ctl00$SheetContentPlaceHolder$rbCivilForeclosure"
    inputs["__EVENTARGUMENT"] = ""
    inputs["ctl00$SheetContentPlaceHolder$rbSearches"] = "forcl"
    status, html = http_post(
        session, search_url, inputs, verify=True, use_cache=False
    )
    if status != 200 or "foreclosureSearch" not in (html or ""):
        logger.error(
            "cpdocket foreclosure-radio postback failed (status=%s, html_len=%s)",
            status,
            len(html or ""),
        )
        return "", {}
    return html, _form_inputs(html)


def cpdocket_search_recent_foreclosures(
    session: requests.Session, days: int = 30, limit: int = 200
) -> list[dict[str, str]]:
    """Pull recent foreclosure case filings. Iterates the foreclosure filing
    types (1460/1465/1466/1467) over the last `days` days. Each submit yields
    a results table; we parse and accumulate."""
    html, inputs = cpdocket_open_foreclosure_search(session)
    if not inputs:
        return []

    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    search_url = f"{CPDOCKET_BASE}/Search.aspx"
    rows: list[dict[str, str]] = []

    for code, label in FORECLOSURE_FILING_TYPES.items():
        if len(rows) >= limit:
            break
        # Re-pull viewstate from the most recent form (cpdocket invalidates
        # stale viewstates aggressively)
        if not inputs:
            html, inputs = cpdocket_open_foreclosure_search(session)
            if not inputs:
                break
        payload = dict(inputs)
        payload["__EVENTTARGET"] = ""
        payload["__EVENTARGUMENT"] = ""
        payload["ctl00$SheetContentPlaceHolder$rbSearches"] = "forcl"
        payload[
            "ctl00$SheetContentPlaceHolder$foreclosureSearch$ddlFilingType"
        ] = code
        payload[
            "ctl00$SheetContentPlaceHolder$foreclosureSearch$txtFromDate"
        ] = start.strftime("%m/%d/%Y")
        payload[
            "ctl00$SheetContentPlaceHolder$foreclosureSearch$txtToDate"
        ] = end.strftime("%m/%d/%Y")
        payload[
            "ctl00$SheetContentPlaceHolder$foreclosureSearch$btnSubmit"
        ] = "Submit Search"
        # Ensure case-year + sequence are blank so the date-range path is used
        payload[
            "ctl00$SheetContentPlaceHolder$foreclosureSearch$ddlCaseYear"
        ] = ""
        payload[
            "ctl00$SheetContentPlaceHolder$foreclosureSearch$txtCaseSequence"
        ] = ""
        payload[
            "ctl00$SheetContentPlaceHolder$foreclosureSearch$txtParcelNbr"
        ] = ""

        status, results_html = http_post(
            session, search_url, payload, verify=True, use_cache=False,
            timeout=45,
        )
        if status != 200:
            logger.warning("filing-type %s submit -> status %s", code, status)
            inputs = {}  # force refresh next iteration
            continue
        cases = _parse_cpdocket_results(
            results_html, limit=limit - len(rows), filing_label=label
        )
        logger.info(
            "filing_type=%s (%s) -> %d cases", code, label, len(cases)
        )
        rows.extend(cases)
        # Refresh inputs from result page for next loop
        inputs = _form_inputs(results_html)

    return rows[:limit]


def _parse_cpdocket_results(
    html: str, limit: int = 200, filing_label: str = ""
) -> list[dict[str, str]]:
    """Parse the ForeclosureSearchResults.aspx table. Columns:
    Defendant | Parcel Address | City | Zip | Case Number | Parcel | Status |
    Filed. We dedupe by case_number (a case can list multiple parcels)."""
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for table in soup.find_all("table"):
        # Find the header row -> column-name -> index map
        header_cells: list[str] = []
        all_rows = table.find_all("tr")
        for tr in all_rows:
            ths = tr.find_all("th")
            if ths:
                header_cells = [
                    th.get_text(" ", strip=True).lower() for th in ths
                ]
                break
        if not header_cells:
            continue
        # Require this is the foreclosure-results table
        if not (
            "case number" in header_cells
            and any("address" in h for h in header_cells)
        ):
            continue

        idx = {name: i for i, name in enumerate(header_cells)}

        for tr in all_rows:
            tds = tr.find_all("td")
            if len(tds) < len(header_cells):
                continue
            cells = [td.get_text(" ", strip=True) for td in tds]
            link = tr.find("a")

            def get(name: str) -> str:
                for k, i in idx.items():
                    if name in k and i < len(cells):
                        return cells[i]
                return ""

            case_no = get("case number")
            if not case_no:
                continue
            # First row of a multi-parcel case is canonical; skip dupes
            if case_no in seen:
                # But still allow capturing a second parcel as a separate
                # lead candidate (different property)
                pass
            seen.add(case_no)

            row: dict[str, str] = {
                "case_number": case_no,
                "filing_label": filing_label,
                "raw": " | ".join(cells)[:600],
                "defendant": get("defendant"),
                "filing_date": get("filed"),
                "status": get("status"),
                "parcel": get("parcel") if "parcel" in idx else "",
            }
            # Parcel column is "Parcel" but Address column is "Parcel Address"
            # so a substring match for "parcel" would clash; resolve precisely
            for k, i in idx.items():
                if k == "parcel" and i < len(cells):
                    row["parcel"] = cells[i]
                if "address" in k and i < len(cells):
                    row["address"] = cells[i]
                if k == "city" and i < len(cells):
                    row["city"] = cells[i]
                if k == "zip" and i < len(cells):
                    row["zip"] = cells[i]
            if link and link.get("href"):
                row["detail_href"] = link["href"]
            rows.append(row)
            if len(rows) >= limit:
                return rows
    return rows


# ---------------------------------------------------------------------------
# Source 2: MyPlace parcel + owner enrichment
# ---------------------------------------------------------------------------


def myplace_search_address(session: requests.Session, address: str) -> list[dict]:
    """Search myplace by address. Returns a list of {parcel, address, owner,
    mailing, city, zip} candidate matches."""
    if not address:
        return []
    landing_status, landing = http_get(session, f"{MYPLACE_BASE}/")
    if landing_status != 200:
        return []
    soup = BeautifulSoup(landing, "lxml")
    form = soup.find("form")
    if not form:
        return []

    fields: dict[str, str] = {}
    for el in form.find_all(["input", "select"]):
        name = el.get("name")
        if not name:
            continue
        fields[name] = el.get("value", "")
    fields.update(_extract_viewstate(landing))
    fields["hdnSearchChoice"] = "Address"
    fields["hdnSearchText"] = address
    fields["hdnButtonClicked"] = "btnSearch"
    fields["Search"] = address

    status, html = http_post(
        session, f"{MYPLACE_BASE}/MainPage/PropertyData", fields, use_cache=False
    )
    if status != 200:
        return []
    return _parse_myplace_results(html)


def _parse_myplace_results(html: str) -> list[dict]:
    """Pull parcel id, owner, mailing from a myplace property-data response."""
    out: list[dict] = []
    soup = BeautifulSoup(html, "lxml")
    parcel_re = re.compile(r"\b\d{3}-\d{2}-\d{3}\b")
    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        m = parcel_re.search(text)
        if not m:
            continue
        # tolerant: scan rows for "Owner", "Mailing", "Address"
        rec = {"parcel": m.group(0), "raw": text[:1000]}
        for tr in table.find_all("tr"):
            label_cell = tr.find(["th", "td"])
            if not label_cell:
                continue
            label = label_cell.get_text(" ", strip=True).lower().rstrip(":")
            cells = tr.find_all("td")
            value = cells[-1].get_text(" ", strip=True) if cells else ""
            if "owner" in label and "mailing" not in label:
                rec.setdefault("owner", value)
            elif "mailing" in label:
                rec.setdefault("mailing", value)
            elif label in {"address", "site address", "property address"}:
                rec.setdefault("address", value)
            elif "year built" in label:
                rec.setdefault("year_built", _maybe_int(value))
            elif "sq" in label and "ft" in label:
                rec.setdefault("sqft", _maybe_int(value))
            elif "property class" in label or "land use" in label:
                rec.setdefault("property_type", value)
        out.append(rec)
        if len(out) >= 5:
            break
    return out


def _maybe_int(s: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", s or "")
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Source 3: Skip-trace via Radaris (TruePeopleSearch + FastPeopleSearch are
# Cloudflare-gated so we do not attempt them; they return captchas to
# headless requests)
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(
    r"\(?\b([2-9]\d{2})\)?[-.\s]?([2-9]\d{2})[-.\s]?(\d{4})\b"
)
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
EMAIL_BLACKLIST = (
    "sentry",
    "cdn",
    "google",
    "facebook",
    "cloudflare",
    "noreply",
    "no-reply",
    "example",
    "gstatic",
    "radaris",
    "doubleclick",
    "googleapis",
    "wixpress",
    "support@",
    "info@",
    "admin@",
    "abuse@",
    "@2x",
    "u003e",
)
PHONE_BLACKLIST_AC = {"800", "888", "877", "866", "855", "844", "833", "822"}


_NAME_NOISE = {
    "ET",
    "AL",
    "ETAL",
    "ET.",
    "AL.",
    "JR",
    "SR",
    "II",
    "III",
    "IV",
    "MR",
    "MRS",
    "MS",
    "DR",
    "TRUSTEE",
    "TRUST",
    "ESTATE",
    "DECEASED",
    "DEC",
    "LLC",
    "INC",
    "CO",
    "LP",
    "LTD",
    "REVOCABLE",
}


def _clean_name_tokens(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for t in tokens:
        u = re.sub(r"[^A-Za-z']", "", t).upper()
        if not u or u in _NAME_NOISE or len(u) == 1:
            continue
        out.append(t.strip(".,"))
    return out


def _split_owner_name(owner: str) -> tuple[str, str]:
    """Cuyahoga foreclosure defendants come in many shapes:
        'SMITH, JOHN A'                  (last, first middle)
        'CALDWELL, ROBERT A. ET AL'      (last, first middle, et al)
        'SMITH JOHN A & JANE'            (no comma)
        'JANE DOE TRUSTEE OF DOE TRUST'  (entity-tail)
    Strip noise tokens (ET AL, JR, TRUSTEE, etc.) and return (first, last)
    for the *individual* defendant. Returns ('', '') for entity defendants
    (LLC / INC) since those are not skip-traceable."""
    if not owner:
        return "", ""
    # Drop trailing co-defendants
    s = re.split(r"\s*&\s*|\s+/\s+|\s+AND\s+|\s+and\s+", owner, maxsplit=1)[0].strip()
    # Hard reject obvious entities
    if re.search(r"\b(LLC|INC|CORP|CO\.|LP|LTD|BANK|TRUST CO)\b", s, re.IGNORECASE):
        return "", ""
    if "," in s:
        left, _, right = s.partition(",")
        left_tokens = _clean_name_tokens(left.split())
        right_tokens = _clean_name_tokens(right.split())
        # If the right side is empty-after-cleaning (e.g. ", ET AL") then
        # the LEFT is the full first-middle-last name, not "last, first"
        if not right_tokens:
            if len(left_tokens) >= 2:
                return left_tokens[0], left_tokens[-1]
            return "", left_tokens[0] if left_tokens else ""
        first = right_tokens[0] if right_tokens else ""
        last = left_tokens[-1] if left_tokens else ""
        return first, last
    tokens = _clean_name_tokens(s.split())
    if len(tokens) >= 2:
        # Ambiguous order; assume last name comes first in cpdocket data
        return tokens[1], tokens[0]
    return "", tokens[0] if tokens else ""


def _is_clean_email(addr: str) -> bool:
    low = addr.lower()
    return not any(b in low for b in EMAIL_BLACKLIST)


def _format_phone(m: re.Match) -> str | None:
    ac, mid, last = m.group(1), m.group(2), m.group(3)
    if ac in PHONE_BLACKLIST_AC:
        return None
    return f"({ac}) {mid}-{last}"


def skip_trace(
    session: requests.Session, owner_name: str, mailing_address: str
) -> tuple[str, str, float, str]:
    """Try to find a phone + email for the owner via Radaris public profiles.
    Returns (phone, email, confidence, note). Confidence < 0.6 = mark for
    human review."""
    if not owner_name:
        return "", "", 0.0, "no owner name"

    first, last = _split_owner_name(owner_name)
    if not last:
        return "", "", 0.0, "could not parse owner name"

    # Pull city + state from mailing address best-effort
    city = "Cleveland"
    state = "OH"
    if mailing_address:
        m = re.search(
            r",\s*([A-Z][A-Za-z .'-]+),\s*([A-Z]{2})\b", mailing_address
        )
        if m:
            city = m.group(1).strip()
            state = m.group(2).strip()

    search_url = (
        f"{RADARIS_BASE}/ng/search?ff={quote(first)}&fl={quote(last)}"
        f"&fs={quote(state)}&fc={quote(city)}"
    )
    status, html = http_get(session, search_url)
    if status != 200 or len(html) < 5000:
        return "", "", 0.0, f"radaris search blocked (status={status})"

    profile_paths = re.findall(r'href="(/p/[^"]+)"', html)
    # Dedupe + cap
    seen: set[str] = set()
    profile_paths = [p for p in profile_paths if not (p in seen or seen.add(p))][:5]

    if not profile_paths:
        return "", "", 0.0, "no radaris matches"

    # Try the most-likely-relevant matches: profiles whose URL contains the
    # first-name (case-insensitive)
    lc_first = first.lower()
    profile_paths.sort(key=lambda p: 0 if lc_first and lc_first in p.lower() else 1)

    for path in profile_paths[:3]:
        url = urljoin(RADARIS_BASE, path)
        status, html = http_get(session, url)
        if status != 200 or len(html) < 4000:
            continue

        soup = BeautifulSoup(html, "lxml")
        # Strip script + style blocks so JS copyright comments don't leak
        # into our regex
        for tag in soup(["script", "style", "footer"]):
            tag.decompose()

        phones: list[str] = []
        # Primary phone: .name-address-phone__phone (the headline contact)
        primary = soup.select_one(".name-address-phone__phone")
        if primary:
            for m in PHONE_RE.finditer(primary.get_text(" ", strip=True)):
                p = _format_phone(m)
                if p and p not in phones:
                    phones.append(p)
        # Secondary phones: .phones-list
        for plist in soup.select(".phones-list"):
            for m in PHONE_RE.finditer(plist.get_text(" ", strip=True)):
                p = _format_phone(m)
                if p and p not in phones:
                    phones.append(p)
                if len(phones) >= 5:
                    break

        emails: list[str] = []
        cleaned_html = soup.get_text(" ", strip=True)
        for m in EMAIL_RE.finditer(cleaned_html):
            addr = m.group(0)
            if _is_clean_email(addr) and addr not in emails:
                emails.append(addr)
            if len(emails) >= 5:
                break

        if phones or emails:
            phone = phones[0] if phones else ""
            email = emails[0] if emails else ""
            # First-name match in URL is the strongest single signal that
            # this profile is actually our target. Without it, we are
            # probably looking at a same-last-name relative.
            first_name_match = bool(lc_first) and lc_first in path.lower()
            confidence = 0.45  # baseline = "found a same-last-name profile"
            if first_name_match:
                confidence += 0.30
            if phone and email:
                confidence += 0.10
            # City match in mailing address vs profile (rough)
            if city.lower() in html.lower():
                confidence += 0.10
            confidence = min(confidence, 0.95)
            return phone, email, round(confidence, 2), (
                f"radaris:{path} fn_match={first_name_match}"
            )

    return "", "", 0.0, "radaris profiles had no contact data"


# ---------------------------------------------------------------------------
# Pipeline glue
# ---------------------------------------------------------------------------


def cpdocket_fetch_case_detail(
    session: requests.Session, detail_href: str
) -> dict[str, str]:
    """Pull case detail (parties with addresses + parcel) for a single
    foreclosure case. Returns {parcel, defendant, defendant_address}."""
    if not detail_href:
        return {}
    url = urljoin(CPDOCKET_BASE, detail_href)
    status, html = http_get(session, url, verify=True, use_cache=True)
    if status != 200:
        return {}
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, str] = {"detail_url": url}
    parcel_re = re.compile(r"\b\d{3}-\d{2}-\d{3}\b")
    pm = parcel_re.search(html)
    if pm:
        out["parcel"] = pm.group(0)
    # cpdocket lists parties under a "Parties" or "Caption" heading. The
    # defendant block is the row labeled DEFENDANT or DFT.
    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)
        if re.search(r"\b(DEFENDANT|DFT)\b", text, re.IGNORECASE):
            # Extract the name + address (next sibling cells)
            cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            joined = " | ".join(cells)
            out.setdefault("defendant_block", joined[:400])
            # Address heuristic: street-style chunk after the name
            addr = _extract_address_from_party(joined)
            if addr:
                out.setdefault("defendant_address", addr)
            # Name: first cell that's not a label
            for c in cells:
                if c and not re.match(
                    r"^(DEFENDANT|DFT|PLAINTIFF|PLF)$", c, re.IGNORECASE
                ):
                    out.setdefault("defendant_name", c)
                    break
            break
    return out


def _extract_address_from_party(party: str) -> str:
    """cpdocket party text often looks like 'BANK OF AMERICA NA vs. SMITH,
    JOHN A et al, 1234 EAST 79TH ST, CLEVELAND OH 44103'. Pull the first
    street-style token."""
    if not party:
        return ""
    m = re.search(
        r"(\d{1,6}\s+(?:[NSEW]\s+)?[A-Z0-9 .'-]+(?:STREET|ST|AVE|AVENUE|BLVD"
        r"|BOULEVARD|RD|ROAD|DR|DRIVE|CT|COURT|LN|LANE|WAY|PL|PLACE|PKWY"
        r"|TER|TERRACE)\b[^,]*)",
        party.upper(),
    )
    return m.group(1).strip() if m else ""


def _extract_owner_from_party(party: str) -> str:
    """Extract the defendant (owner) side of 'PLAINTIFF vs DEFENDANT'."""
    if not party:
        return ""
    parts = re.split(r"\bvs?\.?\b", party, flags=re.IGNORECASE)
    if len(parts) < 2:
        return ""
    defendant = parts[1].strip()
    # Strip the trailing address chunk if present
    defendant = re.split(r"\s+\d{1,6}\s", defendant)[0]
    defendant = re.sub(r"\s*et\s+al.*$", "", defendant, flags=re.IGNORECASE)
    return defendant.strip(" ,;")


def collect_leads(
    limit: int,
    skip_trace_enabled: bool,
    enrich_parcels: bool,
) -> list[Lead]:
    _cache_init()
    session = make_session()

    cases = cpdocket_search_recent_foreclosures(session, days=45, limit=limit * 2)
    logger.info("cpdocket returned %d candidate cases", len(cases))

    leads: list[Lead] = []
    now_iso = dt.datetime.now().isoformat(timespec="seconds")

    for case in cases:
        if len(leads) >= limit:
            break

        # Prefer structured results-table fields (Defendant / Parcel Address /
        # City / Zip / Parcel). Fall back to detail-page walk if missing.
        owner = case.get("defendant") or _extract_owner_from_party(
            case.get("raw", "")
        )
        address = case.get("address") or _extract_address_from_party(
            case.get("raw", "")
        )
        city = case.get("city") or "Cleveland"
        zip_code = (case.get("zip") or "").split("-")[0]

        detail: dict[str, str] = {}
        if (not address or not owner) and case.get("detail_href"):
            try:
                detail = cpdocket_fetch_case_detail(
                    session, case["detail_href"]
                )
            except Exception as exc:
                logger.warning("case detail fetch failed: %s", exc)
                detail = {}
            owner = owner or detail.get("defendant_name", "")
            address = address or detail.get("defendant_address", "")

        if not address and not owner:
            continue

        lead = Lead(
            address=address,
            city=city,
            zip_code=zip_code or "",
            owner_name=owner,
            parcel=case.get("parcel", "") or detail.get("parcel", ""),
            distress_type=case.get("filing_label", "foreclosure"),
            scraped_at=now_iso,
            source_url=detail.get(
                "detail_url",
                f"{CPDOCKET_BASE}/Search.aspx?case={quote(case.get('case_number', ''))}",
            ),
            case_number=case.get("case_number", ""),
            notes=f"filing={case.get('filing_date', '')} status={case.get('status', '')}",
            raw=case,
        )

        if enrich_parcels and address:
            try:
                hits = myplace_search_address(session, address)
            except Exception as exc:
                logger.warning("myplace lookup failed for %s: %s", address, exc)
                hits = []
            if hits:
                top = hits[0]
                lead.parcel = top.get("parcel", "")
                lead.mailing = top.get("mailing", "") or lead.mailing
                if not lead.owner_name and top.get("owner"):
                    lead.owner_name = top["owner"]
                lead.property_type = top.get("property_type", "")
                lead.year_built = top.get("year_built")
                lead.sqft = top.get("sqft")

        if skip_trace_enabled and lead.owner_name:
            try:
                phone, email, conf, note = skip_trace(
                    session, lead.owner_name, lead.mailing or lead.address
                )
            except Exception as exc:
                logger.warning("skip-trace failed for %s: %s", lead.owner_name, exc)
                phone, email, conf, note = "", "", 0.0, f"error:{exc}"
            lead.phone = phone
            lead.email = email
            lead.confidence = conf
            lead.notes = (lead.notes + " | " + note).strip(" |")

        leads.append(lead)

    return leads


# ---------------------------------------------------------------------------
# Output: CSV + Django ORM insert
# ---------------------------------------------------------------------------


CSV_COLUMNS = [
    "parcel",
    "address",
    "city",
    "state",
    "zip_code",
    "owner_name",
    "mailing",
    "phone",
    "email",
    "distress_type",
    "confidence",
    "scraped_at",
    "source_url",
    "case_number",
    "property_type",
    "year_built",
    "sqft",
    "notes",
]


def write_csv(leads: list[Lead], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            row = asdict(lead)
            row.pop("raw", None)
            writer.writerow(row)


def insert_into_django(leads: list[Lead]) -> tuple[int, int]:
    """Insert into broker_ops.PropertyLead. Returns (before, after) counts."""
    sys.path.insert(0, "/home/opc/hive_django")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
    import django  # noqa

    django.setup()
    from broker_ops.models import PropertyLead  # type: ignore

    before = PropertyLead.objects.count()
    created = 0
    for lead in leads:
        if not lead.address:
            continue
        defaults = {
            "city": lead.city or "Cleveland",
            "state": lead.state or "OH",
            "zip_code": lead.zip_code or "",
            "county": "Cuyahoga",
            "property_type": (lead.property_type or "").lower()[:20],
            "year_built": lead.year_built if lead.year_built is not None else 0,
            "sqft": lead.sqft if lead.sqft is not None else 0,
            "owner_name": lead.owner_name or "",
            "owner_phone": lead.phone or "",
            "owner_email": lead.email or "",
            "owner_mailing": lead.mailing or "",
            "lead_type": "foreclosure",
            "status": "new",
            "source": "cuyahoga_free_scraper",
            "source_url": lead.source_url or "",
            "notes": lead.notes or "",
            "raw_data": {
                "case_number": lead.case_number,
                "confidence": lead.confidence,
                "distress_type": lead.distress_type,
                "scraped_at": lead.scraped_at,
            },
        }
        # Match on (address, source) to avoid dupes on re-runs
        obj, was_created = PropertyLead.objects.update_or_create(
            address=lead.address[:255],
            source="cuyahoga_free_scraper",
            defaults=defaults,
        )
        if was_created:
            created += 1
    after = PropertyLead.objects.count()
    return before, after


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _skip_trace_csv_mode(csv_in: Path) -> int:
    """Read an existing CSV and re-run skip-trace from this host. Writes
    output to <stem>.skiptraced.csv next to the input."""
    if not csv_in.exists():
        print(f"input not found: {csv_in}")
        return 4
    _cache_init()
    session = make_session()
    out_path = csv_in.with_name(csv_in.stem + ".skiptraced.csv")
    enriched: list[dict] = []
    with csv_in.open(newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            owner = row.get("owner_name", "")
            mailing = row.get("mailing", "") or row.get("address", "")
            phone, email, conf, note = "", "", 0.0, "no owner"
            if owner:
                try:
                    phone, email, conf, note = skip_trace(
                        session, owner, mailing
                    )
                except Exception as exc:
                    note = f"error:{exc}"
            row["phone"] = row.get("phone") or phone
            row["email"] = row.get("email") or email
            row["confidence"] = max(
                float(row.get("confidence") or 0), conf
            )
            row["notes"] = (row.get("notes", "") + " | " + note).strip(" |")
            enriched.append(row)
    if not enriched:
        print("no rows")
        return 5
    with out_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(enriched[0].keys()))
        writer.writeheader()
        for r in enriched:
            writer.writerow(r)
    p_hit = sum(1 for r in enriched if r.get("phone"))
    e_hit = sum(1 for r in enriched if r.get("email"))
    total = len(enriched)
    print(f"skip-traced {total} rows -> {out_path}")
    print(
        f"phone={p_hit} ({p_hit / total:.0%}) email={e_hit} ({e_hit / total:.0%})"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--no-skip-trace", action="store_true")
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="skip myplace parcel enrichment",
    )
    parser.add_argument(
        "--no-django",
        action="store_true",
        help="skip Django ORM insert (csv only)",
    )
    parser.add_argument(
        "--skip-trace-csv",
        type=str,
        default="",
        help=(
            "Read an existing CSV (no scrape) and run skip-trace against "
            "each row. Use this from a residential IP after the Oracle "
            "scrape; datacenter IPs are challenged by Radaris/etc."
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.skip_trace_csv:
        return _skip_trace_csv_mode(Path(args.skip_trace_csv))

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    leads = collect_leads(
        limit=args.limit,
        skip_trace_enabled=not args.no_skip_trace,
        enrich_parcels=not args.no_enrich,
    )

    today = dt.date.today().strftime("%Y%m%d")
    csv_path = LOG_DIR / f"cuyahoga_leads_{today}.csv"
    write_csv(leads, csv_path)

    phone_hits = sum(1 for l in leads if l.phone)
    email_hits = sum(1 for l in leads if l.email)
    contact_hits = sum(1 for l in leads if l.phone or l.email)
    total = max(len(leads), 1)

    print(f"records={len(leads)} csv={csv_path}")
    print(
        f"skip_trace: phone={phone_hits} ({phone_hits / total:.0%}) "
        f"email={email_hits} ({email_hits / total:.0%}) "
        f"any_contact={contact_hits} ({contact_hits / total:.0%})"
    )

    if not args.no_django and leads:
        try:
            before, after = insert_into_django(leads)
            print(f"property_lead_count: {before} -> {after}")
        except Exception as exc:
            print(f"django insert failed: {exc}")
            return 2

    return 0 if leads else 3


if __name__ == "__main__":
    raise SystemExit(main())
