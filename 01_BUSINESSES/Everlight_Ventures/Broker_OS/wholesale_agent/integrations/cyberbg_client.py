"""CyberBackgroundChecks client -- owner name and phone lookup by address.

cyberbackgroundchecks.com is a free public-records aggregator. No official API.
This client hits the search URL and parses the owner block from the HTML response.

The site rate-limits aggressively and will serve a captcha under scrape load.
Real production use needs a rotating residential proxy or a headless browser.
This client structures the call and env-var surface so both paths can plug in.

Environment:
    CYBERBG_SESSION_COOKIE    optional cookie from a logged-in session
    CYBERBG_PROXY_URL         optional HTTPS proxy (recommended for volume)
    CYBERBG_HEADLESS_API_URL  optional browserless-style endpoint

Usage:
    from integrations.cyberbg_client import lookup_owner
    result = lookup_owner("123 Main St", "Atlanta", "GA", "30310")
    if result.ok:
        print(result.owner_name, result.phone)
"""
from __future__ import annotations

import logging
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("cyberbg")

CYBERBG_BASE = "https://www.cyberbackgroundchecks.com"
CYBERBG_SEARCH_PATH = "/address"


@dataclass
class CyberBGResult:
    ok: bool
    address: str = ""
    owner_name: str = ""
    phone: str = ""
    age: Optional[int] = None
    prior_addresses: list = field(default_factory=list)
    raw_html_preview: str = ""
    error: str = ""


def lookup_owner(address: str, city: str, state: str, zip_code: str = "") -> CyberBGResult:
    """Look up owner name and phone for an address.

    Returns CyberBGResult with ok=False on any failure. Never raises.
    """
    cookie = os.environ.get("CYBERBG_SESSION_COOKIE", "")
    proxy = os.environ.get("CYBERBG_PROXY_URL", "")
    headless_api = os.environ.get("CYBERBG_HEADLESS_API_URL", "")

    if headless_api:
        return _lookup_via_headless(headless_api, address, city, state, zip_code)

    try:
        import requests
    except ImportError:
        return CyberBGResult(ok=False, address=address, error="requests_not_installed")

    path_parts = [
        _slug(state),
        _slug(city),
        _slug(zip_code) if zip_code else "",
        _slug(address),
    ]
    path_parts = [p for p in path_parts if p]
    url = f"{CYBERBG_BASE}{CYBERBG_SEARCH_PATH}/{'/'.join(path_parts)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Hive/1.0)",
        "Accept": "text/html",
    }
    if cookie:
        headers["Cookie"] = cookie

    proxies = {"https": proxy, "http": proxy} if proxy else None

    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=20)
    except requests.RequestException as exc:
        return CyberBGResult(ok=False, address=address, error=f"http_error:{exc}")

    if resp.status_code == 403 or resp.status_code == 429:
        return CyberBGResult(ok=False, address=address, error=f"rate_limited_{resp.status_code}")
    if resp.status_code != 200:
        return CyberBGResult(ok=False, address=address, error=f"status_{resp.status_code}")

    return _parse_html(resp.text, address)


def _lookup_via_headless(endpoint: str, address: str, city: str, state: str, zip_code: str) -> CyberBGResult:
    """Dispatch the lookup to a browserless/playwright service when configured."""
    try:
        import requests
    except ImportError:
        return CyberBGResult(ok=False, address=address, error="requests_not_installed")

    payload = {"address": address, "city": city, "state": state, "zip": zip_code}
    try:
        resp = requests.post(endpoint, json=payload, timeout=30)
    except requests.RequestException as exc:
        return CyberBGResult(ok=False, address=address, error=f"headless_error:{exc}")

    if resp.status_code != 200:
        return CyberBGResult(ok=False, address=address, error=f"headless_status_{resp.status_code}")

    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    html = data.get("html", "") if isinstance(data, dict) else ""
    return _parse_html(html, address)


def _parse_html(html: str, address: str) -> CyberBGResult:
    """Extract owner name and phone from cyberbackgroundchecks HTML.

    TODO: pin these selectors once we capture a real response. Current regexes
    match the owner card pattern observed in 2024 scrapes.
    """
    if not html:
        return CyberBGResult(ok=False, address=address, error="empty_html")

    name_match = re.search(r'class="full-name"[^>]*>([^<]+)<', html)
    phone_match = re.search(r'class="phone"[^>]*>(\+?[\d\-\(\)\s\.]+)<', html)
    age_match = re.search(r'class="age"[^>]*>(\d+)<', html)

    if not name_match:
        return CyberBGResult(ok=False, address=address, error="owner_not_found",
                             raw_html_preview=html[:500])

    return CyberBGResult(
        ok=True,
        address=address,
        owner_name=name_match.group(1).strip(),
        phone=_normalize_phone(phone_match.group(1)) if phone_match else "",
        age=int(age_match.group(1)) if age_match else None,
        raw_html_preview=html[:500],
    )


def _slug(s: str) -> str:
    s = (s or "").strip().replace(" ", "-").replace(",", "").replace(".", "")
    return urllib.parse.quote(s, safe="-")


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1{digits}"
    return ""
