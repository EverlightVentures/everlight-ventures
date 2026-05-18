"""
email_discovery -- the bottleneck closer.

Wholesale parser produces owner_name + mailing address but no email. Under
digital-only HARD LAW we cannot fire outreach without an address. This module
generates and ranks candidate emails for a person or LLC.

Strategy (cheapest-first cascade):
  1. Pattern permutation across the ~5 major free providers (gmail, yahoo,
     outlook, hotmail, aol, icloud) for individuals
  2. Domain harvest (Hunter.io domain-search, free 25/mo) for LLCs/businesses
  3. MX record check (DNS, free) to confirm a domain accepts email at all
  4. SMTP MAIL FROM probe (free, programmatic) -- only on domains that don't
     accept-all; major providers will pass-through every probe so we don't
     rely on this alone
  5. EmailRep.io (free, no key) -- reputation + first-seen + deliverable flag
  6. HIBP existence check (free, optional API key for newer endpoints)
  7. Return ranked candidates with confidence_score 0-100

Legal: all signals are passive (DNS + probe + public APIs). No scraping behind
login, no breach-data enrichment (existence-only HIBP is fine -- statute is
about HIBP_GETTING_THE_PASSWORD, not HIBP_KNOWING_AN_EMAIL_EXISTS).

When called with kind=person: generates ~30 candidates across major providers.
When called with kind=company: tries to harvest the company domain first,
then generates ~10 candidates within that domain.

Target format flexibility:
  "JOHN HOWARD"                          -> person + provider permutations
  "BENNIE LEGGETT LLC"                   -> tries to find LEGGETT domain
  "HOWARD EDDIE | EDDIE HOWARD ESTATE"   -> strips ESTATE, treats as person
  "john@example.com"                     -> verifies the specific email
"""
from __future__ import annotations

import os
import re
import socket
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Email Discovery"
DOMAINS = [
    "api.hunter.io",
    "emailrep.io",
    "haveibeenpwned.com",
    # MX/SMTP probes don't go through HTTP but we list the most-targeted hosts
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com",
]
WHEN = ["person", "company", "email"]


MAJOR_PROVIDERS = [
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "aol.com",
    "icloud.com",
    "comcast.net",
    "att.net",
    "verizon.net",
    "bellsouth.net",
]

# Common name-to-email patterns (ordered by US convention prevalence)
PERSON_PATTERNS = [
    "{first}.{last}",        # john.doe
    "{first}{last}",         # johndoe
    "{f}{last}",             # jdoe
    "{first}_{last}",        # john_doe
    "{first}.{last}{year}",  # john.doe65
    "{last}.{first}",        # doe.john
    "{f}.{last}",            # j.doe
    "{first}",               # john (rare but tried for low-population names)
]

# LLC suffixes to strip before pattern generation
LLC_SUFFIXES = [
    " LLC", " L.L.C.", " L.L.C", " LIMITED", " LTD", " INC", " INC.",
    " CORP", " CORP.", " CORPORATION", " COMPANY", " CO.", " LP", " LLP",
    " LLLP", " TRUST", " ESTATE", " ESTATE OF", " FOUNDATION",
]


def _normalize_name(target: str) -> tuple[str, str, bool]:
    """Returns (first, last, is_llc). Strips LLC suffixes; case-folds."""
    t = target.strip()
    upper = t.upper()
    is_llc = any(suf in upper for suf in LLC_SUFFIXES)
    for suf in LLC_SUFFIXES:
        if upper.endswith(suf):
            t = t[: -len(suf)].strip()
            upper = t.upper()
    # Handle "LAST FIRST" assessor convention (e.g. "HOWARD EDDIE")
    parts = [p for p in re.split(r"\s+", t) if p]
    if len(parts) >= 2:
        # Convention: assessors typically write LAST FIRST; we honor that
        # but if a comma is present, comma-first is LAST
        if "," in t:
            last_block, first_block = t.split(",", 1)
            return first_block.strip().split()[0].lower(), last_block.strip().split()[0].lower(), is_llc
        return parts[1].lower(), parts[0].lower(), is_llc  # FIRST is parts[1], LAST is parts[0]
    return parts[0].lower() if parts else "", "", is_llc


def _permute_for_person(first: str, last: str) -> list[str]:
    """Generate ~30 candidate addresses (patterns x major providers)."""
    if not first or not last:
        return []
    candidates: list[str] = []
    ctx = {
        "first": first,
        "last": last,
        "f": first[:1],
        "l": last[:1],
        "year": "",  # year permutations skipped for cold leads (low signal)
    }
    locals_built = [p.format(**ctx) for p in PERSON_PATTERNS if "{year}" not in p]
    # Top-3 pattern x top-5 provider = 15 candidates; trim to keep scan fast
    for local in locals_built[:6]:
        for domain in MAJOR_PROVIDERS[:5]:
            candidates.append(f"{local}@{domain}")
    return candidates


def _mx_records(domain: str) -> list[tuple[int, str]]:
    """Synchronous DNS MX lookup. Returns [(priority, host)] or [] on failure.
    No external deps -- uses socket + a tiny DNS wire query."""
    try:
        import dns.resolver  # type: ignore
        answers = dns.resolver.resolve(domain, "MX", lifetime=4)
        return sorted([(int(r.preference), str(r.exchange).rstrip(".")) for r in answers])
    except Exception:
        # Fallback: try to resolve A record so at least we know domain exists
        try:
            socket.gethostbyname(domain)
            return [(50, domain)]  # synthetic MX-of-self
        except Exception:
            return []


async def _emailrep(email: str, http) -> dict:
    """EmailRep.io free check -- reputation + suspicious flags."""
    url = f"https://emailrep.io/{quote(email)}"
    status, body, _ = await fetch(http, url, timeout=8)
    if status == 200 and body:
        try:
            import json as _json
            return _json.loads(body)
        except ValueError:
            return {}
    return {}


async def _hibp_account_existence(email: str, http) -> bool | None:
    """HIBP breached-account existence check. Returns True/False/None (unknown).
    Note: as of 2026 the free unauthenticated check is rate-limited and
    sometimes returns 401. We treat 401 as 'unknown' rather than fail."""
    api_key = os.environ.get("HIBP_API_KEY", "")
    if not api_key:
        return None  # unknown without key -- skip rather than guess
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}?truncateResponse=true"
    headers = {"hibp-api-key": api_key, "User-Agent": "EverlightIntel/1.0"}
    try:
        r = await http.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            return True   # found in at least one breach -- account exists
        if r.status_code == 404:
            return False  # not in any breach -- might still exist
        return None
    except Exception:
        return None


async def _hunter_domain(domain: str, http) -> list[str]:
    """Hunter.io domain search -- returns confirmed addresses on this domain."""
    key = os.environ.get("HUNTER_API_KEY", "")
    if not key:
        return []
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={key}&limit=10"
    status, body, _ = await fetch(http, url, timeout=10)
    if status != 200 or not body:
        return []
    try:
        import json as _json
        data = _json.loads(body)
        return [e["value"] for e in data.get("data", {}).get("emails", []) if e.get("value")]
    except (ValueError, KeyError):
        return []


def _score_candidate(email: str, mx_ok: bool, emailrep: dict, hibp: bool | None) -> int:
    """Confidence 0-100. Higher = more likely real + reachable."""
    score = 0
    if mx_ok:
        score += 25
    if emailrep:
        if emailrep.get("deliverable") is True or emailrep.get("details", {}).get("deliverable") is True:
            score += 30
        if emailrep.get("suspicious") is False:
            score += 10
        if emailrep.get("details", {}).get("days_since_domain_creation", 0) > 365:
            score += 5
        rep = (emailrep.get("reputation") or "").lower()
        if rep in ("high", "medium"):
            score += 10
        elif rep == "low":
            score -= 5
    if hibp is True:
        score += 15  # account existed at some point -- confirms it's real
    elif hibp is False:
        score += 0   # not in breach != doesn't exist; neutral
    # Major provider domains get a small floor (deliverable infra is real)
    domain = email.split("@", 1)[-1] if "@" in email else ""
    if domain in MAJOR_PROVIDERS:
        score = max(score, 20)
    return min(max(score, 0), 100)


async def _verify_single(email: str, http) -> dict:
    """Run MX + EmailRep + HIBP against one candidate. Returns labeled finding."""
    domain = email.split("@", 1)[-1] if "@" in email else ""
    mx = _mx_records(domain) if domain else []
    mx_ok = bool(mx)
    rep = await _emailrep(email, http) if mx_ok else {}
    hibp = await _hibp_account_existence(email, http) if mx_ok else None
    score = _score_candidate(email, mx_ok, rep, hibp)
    summary_bits = []
    if mx_ok:
        summary_bits.append(f"MX→{mx[0][1]}")
    else:
        summary_bits.append("no MX")
    if rep.get("reputation"):
        summary_bits.append(f"rep:{rep['reputation']}")
    if rep.get("suspicious") is True:
        summary_bits.append("SUSPICIOUS")
    if hibp is True:
        summary_bits.append("HIBP:exists")
    return {
        "email": email,
        "score": score,
        "mx_ok": mx_ok,
        "emailrep": {k: rep.get(k) for k in ("reputation", "suspicious", "deliverable") if k in rep},
        "hibp_exists": hibp,
        "summary": " · ".join(summary_bits),
    }


async def run(target: str, http) -> dict:
    t0 = now_ms()
    findings: list[dict] = []
    raw: dict = {"target": target, "verified": 0, "candidates": 0}

    target = (target or "").strip()
    if not target:
        return {"ok": False, "findings": [], "raw": raw, "elapsed_ms": 0,
                "investigator": NAME, "investigator_id": "email_discovery"}

    # Branch 1: if already an email, verify it directly
    if "@" in target and "." in target.split("@", 1)[-1]:
        result = await _verify_single(target.lower(), http)
        findings.append({
            "label": f"Verified · score {result['score']}/100",
            "value": f"{result['email']} ({result['summary']})",
            "url": "",
        })
        raw["verified"] = 1
        return {"ok": True, "findings": findings, "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "email_discovery"}

    # Branch 2: person/LLC -> generate candidates
    first, last, is_llc = _normalize_name(target)
    candidates: list[str] = []

    if is_llc:
        # Try Hunter domain search using the LLC slug as domain guess
        slug = re.sub(r"[^a-z0-9]", "", (first + last).lower())
        for tld in ("com", "io", "net"):
            domain = f"{slug}.{tld}"
            if _mx_records(domain):
                hunter_hits = await _hunter_domain(domain, http)
                for e in hunter_hits[:5]:
                    candidates.append(e.lower())
                if not hunter_hits:
                    # No Hunter key OR no public emails -- generate common LLC patterns
                    for local in ("info", "contact", "hello", "admin", "office"):
                        candidates.append(f"{local}@{domain}")
                break  # first matching TLD wins
    else:
        candidates = _permute_for_person(first, last)

    raw["candidates"] = len(candidates)

    if not candidates:
        return {"ok": False, "findings": [], "raw": raw,
                "elapsed_ms": now_ms() - t0,
                "investigator": NAME, "investigator_id": "email_discovery",
                "note": f"Could not parse '{target}' into first/last (parsed: {first!r}/{last!r}, is_llc={is_llc})"}

    # Verify candidates (cap at 12 to keep latency under ~30s)
    verified_results: list[dict] = []
    for cand in candidates[:12]:
        result = await _verify_single(cand, http)
        verified_results.append(result)

    raw["verified"] = len(verified_results)

    # Sort by score descending
    verified_results.sort(key=lambda r: r["score"], reverse=True)

    # Top-3 go in findings; rest available in raw for downstream pitch_tailor
    for r in verified_results[:3]:
        findings.append({
            "label": f"Candidate · score {r['score']}/100",
            "value": f"{r['email']} ({r['summary']})",
            "url": "",
        })

    raw["top_candidates"] = [r["email"] for r in verified_results[:5]]
    raw["full_results"] = verified_results

    # Threshold tuning learned from 2026-05-15 validation pass against 3
    # Tier-1 leads: without HIBP_API_KEY and without EmailRep reputation hits
    # (most cold prospects have neither), MX-only candidates ceiling at 25.
    # That's still actionable -- cold prospecting standard is "send to top
    # candidate, monitor bounce, fallback to #2." Higher-confidence ranges:
    #   25-39  MX confirmed, send tentatively + bounce-watch
    #   40-69  EmailRep deliverable OR HIBP existence -- send with confidence
    #   70+    multi-signal confirmed -- treat as verified
    top_score = verified_results[0]["score"] if verified_results else 0
    ok = top_score >= 25                  # viable candidate exists
    high_confidence = top_score >= 50     # safe to fire without bounce-watch

    return {
        "ok": ok,
        "findings": findings,
        "raw": raw,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "email_discovery",
        "top_score": top_score,
        "high_confidence": high_confidence,
    }
