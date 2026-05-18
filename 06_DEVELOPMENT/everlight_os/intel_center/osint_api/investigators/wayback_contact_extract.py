"""
wayback_contact_extract -- skip-trace fallback via Wayback Machine.

When a current LLC website is scrubbed (deliberately or via business shut),
the Wayback Machine often still has 3-10 year old snapshots that captured
the original email + phone + executor contact info. This module pulls the
oldest few snapshots and regex-extracts contact details.

Companion to archive_org.py (which exists but only fetches site metadata);
this one specifically extracts contacts from historical snapshots.

Strategy:
  1. Query Wayback CDX API for snapshots of the target domain
  2. Fetch the oldest 3 snapshots (most likely to have original founder info)
  3. Extract email + phone via regex; ignore generic webmaster@/info@
  4. Surface the cleanest contact found

Legal scope:
  - Wayback Machine is public archival service
  - No login, no scraping behind auth
  - In-scope per legal_scope.IN_SCOPE["court_records"] adjacency
"""
from __future__ import annotations

import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Wayback Contact Extract"
DOMAINS = ["web.archive.org", "archive.org"]
WHEN = ["domain", "company", "email"]


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

GENERIC_LOCALS = {"webmaster", "info", "contact", "admin", "office", "support",
                  "hello", "team", "sales", "press"}


def _extract_domain(target: str) -> str:
    """Pull a domain from target string. Returns '' if can't determine."""
    t = target.strip().lower()
    if "@" in t and "." in t.split("@", 1)[-1]:
        return t.split("@", 1)[-1]
    if t.startswith(("http://", "https://")):
        return t.split("://", 1)[-1].split("/", 1)[0]
    if "." in t and " " not in t:
        return t.split("/", 1)[0]
    return ""


async def _cdx_snapshots(domain: str, http) -> list[str]:
    """Wayback CDX API -- returns timestamps of available snapshots."""
    url = f"https://web.archive.org/cdx/search/cdx?url={quote(domain)}&output=json&limit=5&filter=statuscode:200"
    status, body, _ = await fetch(http, url, timeout=10)
    if status != 200 or not body:
        return []
    try:
        import json as _json
        rows = _json.loads(body)
        # First row is headers; rest are [urlkey, timestamp, original, mimetype, statuscode, digest, length]
        return [row[1] for row in rows[1:] if len(row) >= 3]
    except (ValueError, IndexError):
        return []


async def _fetch_snapshot(domain: str, timestamp: str, http) -> str:
    """Fetch a specific Wayback snapshot. Returns the HTML body or empty."""
    url = f"https://web.archive.org/web/{timestamp}/http://{domain}"
    status, body, _ = await fetch(http, url, timeout=12)
    if status == 200 and body:
        return body
    return ""


def _extract_contacts(html: str) -> tuple[list[str], list[str]]:
    """Pull emails + phones, dedup, filter out Wayback toolbar + generic locals."""
    if not html:
        return [], []
    # Wayback wraps the original page in a frame -- the toolbar emits
    # webarchive@archive.org etc. Strip those out.
    html = re.sub(r"<!--\s*BEGIN WAYBACK TOOLBAR.*?<!--\s*END WAYBACK TOOLBAR\s*-->",
                  "", html, flags=re.S)

    emails = set()
    for match in EMAIL_RE.findall(html):
        local = match.split("@", 1)[0].lower()
        domain = match.split("@", 1)[-1].lower()
        if domain in ("archive.org", "web.archive.org"):
            continue
        if local in GENERIC_LOCALS:
            # Keep generic-local matches but down-rank them
            emails.add(("generic", match))
        else:
            emails.add(("specific", match))

    phones = set()
    for match in PHONE_RE.findall(html):
        digits = re.sub(r"\D", "", match)
        if len(digits) >= 10:
            # Normalize
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            phones.add(f"({digits[:3]}) {digits[3:6]}-{digits[6:]}")

    # Sort: specific emails before generic
    sorted_emails = sorted(emails, key=lambda x: 0 if x[0] == "specific" else 1)
    return [e for _, e in sorted_emails], sorted(phones)


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings: list = []
    raw: dict = {"snapshots_checked": 0, "emails_found": 0, "phones_found": 0}

    domain = _extract_domain(target)
    if not domain:
        return {"ok": False, "findings": [], "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "wayback_contact_extract",
                "note": f"Could not extract a domain from target '{target}'"}

    raw["domain"] = domain
    timestamps = await _cdx_snapshots(domain, http)
    if not timestamps:
        return {"ok": False, "findings": [], "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "wayback_contact_extract",
                "note": f"No Wayback snapshots for {domain}"}

    all_emails: set[str] = set()
    all_phones: set[str] = set()
    for ts in timestamps[:3]:  # oldest 3 snapshots
        body = await _fetch_snapshot(domain, ts, http)
        emails, phones = _extract_contacts(body)
        all_emails.update(emails)
        all_phones.update(phones)
        raw["snapshots_checked"] += 1

    raw["emails_found"] = len(all_emails)
    raw["phones_found"] = len(all_phones)

    for e in sorted(all_emails)[:5]:
        findings.append({
            "label": "Historical email (Wayback snapshot)",
            "value": e,
            "url": f"https://web.archive.org/web/*/{domain}",
        })
    for p in sorted(all_phones)[:3]:
        findings.append({
            "label": "Historical phone (Wayback snapshot)",
            "value": p,
            "url": f"https://web.archive.org/web/*/{domain}",
        })

    return {
        "ok": len(findings) > 0,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "wayback_contact_extract",
    }
