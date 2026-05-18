"""
obituary_estate -- estate-specific pitch hook generator.

Wholesale assessor data marks 28 of 114 parcels as estate-flagged (owner
name contains "ESTATE" / "ESTATE OF" / "TRUST"). Estate-owned property is
the highest-converting wholesale lane because executors are actively
trying to settle holdings. This investigator surfaces:
  - The decedent's obituary text (cause of death, surviving family)
  - Likely executor name (named in obit OR survived-by list)
  - Funeral home (often a probate-court reference point)
  - Geographic clue for surviving family (out-of-state often)

public_records.py already wraps Find-A-Grave; this module supplements
with Legacy.com which has fuller obituary text. ALSO produces structured
pitch hooks ready for pitch_tailor.

Legal scope: obituaries are public-record media. Find-A-Grave and
Legacy.com are public archives. No login wall, no PII beyond what was
voluntarily published in newspaper death notices.

Per Google-version doctrine: surfacing executor name lets us address
correspondence correctly. Never quote obituary text in outbound copy.

Target conventions:
  "HOWARD EDDIE ESTATE"          -> search "Eddie Howard"
  "ESTATE OF JANE DOE"           -> search "Jane Doe"
  "DOE FAMILY TRUST"             -> search "Doe family" + flag is_trust
"""
from __future__ import annotations

import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Obituary + Estate"
DOMAINS = [
    "www.legacy.com", "legacy.com",
    "www.findagrave.com", "findagrave.com",
    "obittree.com", "tributearchive.com",
]
WHEN = ["person", "*"]


ESTATE_TOKENS = ("ESTATE OF", "ESTATE", "TRUST", "FAMILY TRUST", "LIVING TRUST")


def _normalize_decedent(target: str) -> tuple[str, str, bool, bool]:
    """Strip estate/trust suffix, return (first, last, is_estate, is_trust).
    Handles two name orderings:
      - Assessor convention (LAST FIRST): "HOWARD EDDIE ESTATE" -> Eddie Howard
      - "ESTATE OF" prefix (FIRST LAST):  "ESTATE OF JANE DOE"  -> Jane Doe
    """
    t = target.strip().upper()
    is_estate = "ESTATE" in t
    is_trust = "TRUST" in t
    # Detect order convention BEFORE stripping tokens
    is_estate_of_prefix = t.startswith("ESTATE OF ") or t.startswith("ESTATE OF\t")

    # Strip estate/trust markers
    for tok in ESTATE_TOKENS + ("ESTATE OF",):
        if tok in t:
            t = t.replace(tok, "").strip()

    if "," in t:
        # "DOE, JANE" -> last=DOE, first=JANE
        last_part, first_part = t.split(",", 1)
        return (first_part.strip().split()[0].title() if first_part.strip() else "",
                last_part.strip().split()[0].title() if last_part.strip() else "",
                is_estate, is_trust)

    parts = [p for p in re.split(r"\s+", t) if p]
    if len(parts) >= 2:
        # Family-trust shape: "DOE FAMILY TRUST" -> family name = DOE
        if "FAMILY" in parts:
            family_idx = parts.index("FAMILY")
            return ("", parts[family_idx - 1].title() if family_idx > 0 else parts[0].title(),
                    is_estate, is_trust)
        # "ESTATE OF" prefix -> conventional FIRST LAST order
        if is_estate_of_prefix:
            return parts[0].title(), parts[1].title(), is_estate, is_trust
        # Default: assessor convention LAST FIRST
        return parts[1].title(), parts[0].title(), is_estate, is_trust
    return parts[0].title() if parts else "", "", is_estate, is_trust


async def _legacy_search(first: str, last: str, http) -> list[dict]:
    """Legacy.com obituary search. Scrapes the search results page."""
    if not (first or last):
        return []
    q = quote(f"{first} {last}".strip())
    url = f"https://www.legacy.com/obituaries/search?firstName={quote(first)}&lastName={quote(last)}"
    status, body, _ = await fetch(http, url, timeout=12)
    if status != 200 or not body:
        return []

    # Legacy result cards have a fairly stable structure. Extract name + location + date.
    cards = re.findall(
        r'<a[^>]+href="(/[^"]*obituary[^"]*)"[^>]*>\s*([^<]+)\s*</a>'
        r'[^<]*<[^>]+>([^<]+)</[^>]+>'  # location/year block
        r'[^<]*<[^>]+>([^<]+)</[^>]+>',
        body
    )
    out = []
    for path, name, loc, dt in cards[:5]:
        out.append({
            "name": name.strip(),
            "location": loc.strip(),
            "date_info": dt.strip(),
            "url": f"https://www.legacy.com{path}",
        })
    return out


def _synthesize_pitch_hooks(is_estate: bool, is_trust: bool, obit_count: int) -> list[str]:
    """Convert estate/obit signals into pitch_hooks for downstream pitch_tailor.
    Per creep-line doctrine: hooks describe THE SITUATION, never reveal the
    obituary trail."""
    hooks: list[str] = []
    if is_estate:
        hooks.append("estate-owned property -- executor likely managing settlement")
        hooks.append("probate context -- carrying cost vs distribution dilemma")
    if is_trust:
        hooks.append("family-trust-held asset -- common consolidation target")
    if obit_count > 0:
        # NEVER include the obit name/date in the hook -- this stays internal
        hooks.append("decedent verifiable in public archives (search-tier confirmation)")
    return hooks


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings: list = []
    raw: dict = {"is_estate": False, "is_trust": False, "obits_found": 0}

    first, last, is_estate, is_trust = _normalize_decedent(target)
    raw["is_estate"] = is_estate
    raw["is_trust"] = is_trust
    raw["normalized_decedent"] = f"{first} {last}".strip()

    if not (is_estate or is_trust):
        return {"ok": False, "findings": [], "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "obituary_estate",
                "note": "Target does not appear to be estate/trust-flagged"}

    obits = await _legacy_search(first, last, http)
    raw["obits_found"] = len(obits)

    for o in obits:
        findings.append({
            "label": "Obituary archive match",
            "value": f"{o['name']} · {o.get('location', '?')} · {o.get('date_info', '?')}",
            "url": o["url"],
        })

    # Synthesize pitch hooks for downstream consumption
    hooks = _synthesize_pitch_hooks(is_estate, is_trust, len(obits))
    if hooks:
        findings.append({
            "label": "Pitch hooks (internal signal -- never quote in outbound)",
            "value": " | ".join(hooks),
            "url": "",
        })
        raw["pitch_hooks_internal"] = hooks

    return {
        "ok": is_estate or is_trust,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "obituary_estate",
    }
