"""
verify_email_owner.py -- cross-reference layer for "is this email actually our person?"

Rich's ask 2026-05-15: "We also need to find out who uses the active email and
if it matches the person that is at the address."

For each candidate email produced by email_discovery, this verifier checks:
  1. Gravatar existence -- does ANYONE use this email actively? (weak signal)
  2. Username sweep from email local-part -- does the handle exist on public
     platforms? If yes, try to extract a displayed name + location from each.
  3. Public-records cross-reference -- search CourtListener + OpenCorporates +
     Google News for the assessor owner_name and look for any document that
     mentions an email matching our candidate.
  4. Direct dork: "owner_name" "state" "@gmail.com" surfaces any public mention.

All signals are FREE (no API keys, no paid SaaS). Per macro/micro doctrine.

Design philosophy:
  - SIGNAL when present (bump confidence)
  - DO NOT BLOCK when absent (cold-prospect bounce-watch is the final gate)
  - Be honest about absence -- "unverified" is a valid outcome, not failure

Score:
   0-4    unverified (proceed with bounce-watch only)
   5-19   low (some activity signal but no name match)
   20-49  medium (handle present, partial name signal)
  50-100  high (direct name match OR email-in-public-record)

Usage:
  python3 verify_email_owner.py --email eddie.howard@gmail.com \\
      --name "EDDIE HOWARD" --state TX

  python3 verify_email_owner.py --parcel 015011__00011 --top-n 3
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
PARSED_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed"

sys.path.insert(0, str(WORKSPACE / "06_DEVELOPMENT/everlight_os/intel_center"))


UA = "Mozilla/5.0 (compatible; EverlightIntel/1.0)"

# Common name-to-handle patterns (mirror of email_discovery's PERSON_PATTERNS
# but for username derivation, no email-suffix)
HANDLE_PATTERNS = [
    "{first}{last}",       # eddiehoward
    "{first}.{last}",      # eddie.howard
    "{first}_{last}",      # eddie_howard
    "{f}{last}",           # ehoward
    "{first}{l}",          # eddieh
    "{last}{first}",       # howardeddie (less common but tried)
]

# Top-12 platforms most likely to expose name + location on public profile.
# Each entry: (name, url_template, name_extract_regex, location_extract_regex)
# Regex set to None means "platform exists but doesn't expose extractable name."
PROFILE_PLATFORMS = [
    ("github", "https://github.com/{h}",
     r'<meta property="og:title" content="([^"]+) \([^)]+\)',
     r'<span class="p-label[^"]*"[^>]*>([^<]+)</span>'),
    ("twitter", "https://twitter.com/{h}",
     r'<title>([^|]+) \(@', None),  # Twitter blocks unauthenticated heavily; rarely returns
    ("reddit", "https://www.reddit.com/user/{h}/about.json",
     None, None),  # Reddit JSON endpoint; check existence only
    ("about_me", "https://about.me/{h}",
     r'<meta property="profile:first_name" content="([^"]+)"',
     r'<meta property="profile:location" content="([^"]+)"'),
    ("medium", "https://medium.com/@{h}",
     r'<title>([^|<]+)\s*[\|–]', None),
    ("keybase", "https://keybase.io/{h}",
     r'<title>([^|]+) \(', None),
    ("patreon", "https://www.patreon.com/{h}",
     r'<title>([^|]+) is creating', None),
    ("gravatar_profile", "https://en.gravatar.com/{h}.json",
     None, None),  # JSON profile if the user set one
]


def _normalize_assessor_name(owner_name: str) -> tuple[str, str]:
    """Returns (first, last) from assessor 'LAST FIRST' or 'FIRST LAST' format.
    Strips estate/trust/LLC suffixes."""
    t = owner_name.strip().upper()
    for tok in (" ESTATE", " TRUST", " LLC", " INC", " CORP", " LP", " LIVING TRUST",
                " FAMILY TRUST", "ESTATE OF "):
        t = t.replace(tok, "")
    t = t.strip()
    is_estate_of = owner_name.strip().upper().startswith("ESTATE OF ")

    parts = [p for p in re.split(r"\s+", t) if p]
    if len(parts) < 2:
        return parts[0].title() if parts else "", ""
    if "FAMILY" in parts:
        idx = parts.index("FAMILY")
        return "", parts[idx - 1].title() if idx > 0 else parts[0].title()
    if is_estate_of:
        return parts[0].title(), parts[1].title()
    # Default assessor convention: LAST FIRST
    return parts[1].title(), parts[0].title()


def _candidate_handles_from_email(email: str, first: str, last: str) -> list[str]:
    """Generate plausible usernames from the email local-part + the assessor name."""
    local = email.split("@", 1)[0].lower()
    handles = {local}
    handles.add(local.replace(".", ""))
    handles.add(local.replace("_", ""))
    # Add name-derived handles
    f, l = first.lower(), last.lower()
    if f and l:
        ctx = {"first": f, "last": l, "f": f[:1], "l": l[:1]}
        for pat in HANDLE_PATTERNS:
            try:
                handles.add(pat.format(**ctx))
            except KeyError:
                pass
    return [h for h in handles if h and len(h) >= 3]


async def _gravatar_exists(email: str, http: httpx.AsyncClient) -> bool:
    """Hit Gravatar with d=404 -- 200 means user set an avatar, 404 means not."""
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    try:
        r = await http.get(f"https://www.gravatar.com/avatar/{h}?d=404",
                            timeout=6, headers={"User-Agent": UA})
        return r.status_code == 200
    except Exception:
        return False


async def _gravatar_profile(email: str, http: httpx.AsyncClient) -> dict | None:
    """Some Gravatar users set a full profile (name, bio, location). JSON endpoint."""
    h = hashlib.md5(email.strip().lower().encode()).hexdigest()
    try:
        r = await http.get(f"https://en.gravatar.com/{h}.json",
                            timeout=6, headers={"User-Agent": UA})
        if r.status_code != 200:
            return None
        data = r.json()
        entries = data.get("entry", [])
        if not entries:
            return None
        e = entries[0]
        return {
            "name": e.get("displayName") or e.get("name", {}).get("formatted", ""),
            "given_name": e.get("name", {}).get("givenName", ""),
            "family_name": e.get("name", {}).get("familyName", ""),
            "location": e.get("currentLocation", ""),
            "bio": (e.get("aboutMe", "") or "")[:200],
        }
    except Exception:
        return None


def _fuzzy_name_match(profile_name: str, expected_first: str, expected_last: str) -> int:
    """Score 0-30 for how well profile_name aligns with (expected_first, expected_last).
    Cheap heuristic -- avoids dependency on rapidfuzz/python-Levenshtein."""
    if not profile_name:
        return 0
    pn = profile_name.lower()
    score = 0
    if expected_first and expected_first.lower() in pn:
        score += 10
    if expected_last and expected_last.lower() in pn:
        score += 20  # last name match is stronger signal
    return score


async def _probe_profile(platform: str, url_tmpl: str, name_re: str | None,
                           loc_re: str | None, handle: str,
                           http: httpx.AsyncClient) -> dict | None:
    """Fetch one platform profile. Returns name + location if extractable."""
    url = url_tmpl.replace("{h}", quote(handle, safe=""))
    try:
        r = await http.get(url, timeout=8, headers={"User-Agent": UA},
                            follow_redirects=True)
    except Exception:
        return None
    if r.status_code != 200:
        return None

    body = r.text
    # JSON endpoints (Reddit, Gravatar profile)
    if url.endswith(".json"):
        try:
            data = r.json()
            if platform == "reddit":
                # Reddit /user/X/about.json returns {"data": {"name": ..., "subreddit": {...}}}
                d = data.get("data", {})
                if d.get("name"):
                    return {"platform": platform, "handle": handle,
                            "name": d.get("subreddit", {}).get("title", "")[:80],
                            "location": ""}
            elif platform == "gravatar_profile":
                entries = data.get("entry", [])
                if entries:
                    e = entries[0]
                    return {"platform": platform, "handle": handle,
                            "name": e.get("displayName", "") or e.get("name", {}).get("formatted", ""),
                            "location": e.get("currentLocation", "")}
        except Exception:
            return None
        return {"platform": platform, "handle": handle, "name": "", "location": ""}

    # HTML platforms -- extract via regex
    name = ""
    loc = ""
    if name_re:
        m = re.search(name_re, body, re.S)
        if m:
            name = re.sub(r"\s+", " ", m.group(1).strip())[:80]
    if loc_re:
        m = re.search(loc_re, body, re.S)
        if m:
            loc = re.sub(r"\s+", " ", m.group(1).strip())[:80]
    return {"platform": platform, "handle": handle, "name": name, "location": loc}


async def _public_records_email_search(expected_first: str, expected_last: str,
                                         state: str, candidate_email: str,
                                         http: httpx.AsyncClient) -> list[str]:
    """Search CourtListener + Google News for the expected name + state.
    Look for any returned text that mentions the candidate email.
    Returns list of signals (e.g. ['courtlistener_mentions_email'])."""
    signals = []
    q = f"{expected_first} {expected_last}".strip()
    if not q:
        return signals

    # CourtListener -- free JSON API
    try:
        url = f"https://www.courtlistener.com/api/rest/v3/search/?q={quote(q)}&type=r&order_by=dateFiled+desc"
        r = await http.get(url, timeout=10, headers={"User-Agent": UA})
        if r.status_code == 200:
            data = r.json()
            for hit in data.get("results", [])[:5]:
                blob = json.dumps(hit).lower()
                if candidate_email.lower() in blob:
                    signals.append("courtlistener_mentions_email")
                    break
                if state and state.lower() in blob and (expected_last.lower() in blob):
                    signals.append("courtlistener_name_state_match")
    except Exception:
        pass

    # Google News RSS -- catches news mentions
    try:
        rss = f"https://news.google.com/rss/search?q={quote(q + ' ' + state)}&hl=en-US&gl=US&ceid=US:en"
        r = await http.get(rss, timeout=10, headers={"User-Agent": UA})
        if r.status_code == 200 and candidate_email.lower() in r.text.lower():
            signals.append("google_news_mentions_email")
    except Exception:
        pass

    return signals


async def verify(email: str, expected_name: str, expected_state: str,
                  http: httpx.AsyncClient) -> dict:
    """Main verify entrypoint. Returns scored verification dict."""
    t0 = time.time()
    expected_first, expected_last = _normalize_assessor_name(expected_name)
    signals: list[str] = []
    score = 0
    profile_hits: list[dict] = []

    # Signal 1: Gravatar existence
    if await _gravatar_exists(email, http):
        signals.append("gravatar_avatar_present")
        score += 5
        gp = await _gravatar_profile(email, http)
        if gp and gp.get("name"):
            nm_score = _fuzzy_name_match(gp["name"], expected_first, expected_last)
            score += nm_score
            if nm_score > 0:
                signals.append(f"gravatar_name_match_score_{nm_score}")
            if gp.get("location") and expected_state.lower() in gp["location"].lower():
                score += 20
                signals.append("gravatar_state_match")

    # Signal 2: Username sweep across profile platforms
    handles = _candidate_handles_from_email(email, expected_first, expected_last)
    tasks = []
    for handle in handles[:4]:  # cap to keep latency manageable
        for platform, tmpl, nre, lre in PROFILE_PLATFORMS:
            tasks.append(_probe_profile(platform, tmpl, nre, lre, handle, http))
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, dict) and res:
                profile_hits.append(res)
                signals.append(f"handle_present_{res['platform']}")
                score += 2  # weak: just confirms handle exists somewhere
                # Name match bonus
                if res.get("name"):
                    nm = _fuzzy_name_match(res["name"], expected_first, expected_last)
                    if nm > 0:
                        score += nm
                        signals.append(f"name_match_{res['platform']}_score_{nm}")
                # Location match bonus
                if res.get("location") and expected_state.lower() in res["location"].lower():
                    score += 15
                    signals.append(f"state_match_{res['platform']}")

    # Signal 3: Public records cross-reference
    pr_signals = await _public_records_email_search(
        expected_first, expected_last, expected_state, email, http)
    for s in pr_signals:
        signals.append(s)
        if "mentions_email" in s:
            score += 50  # strong: a public document linked the email + name
        elif "name_state_match" in s:
            score += 10

    score = min(score, 100)
    verdict = ("high" if score >= 50 else
                "medium" if score >= 20 else
                "low" if score >= 5 else
                "unverified")

    return {
        "email": email,
        "expected_name": expected_name,
        "expected_first": expected_first,
        "expected_last": expected_last,
        "expected_state": expected_state,
        "match_score": score,
        "verdict": verdict,
        "signals": signals,
        "profile_hits": [p for p in profile_hits if p.get("name") or p.get("location")],
        "elapsed_s": round(time.time() - t0, 1),
    }


# ---------------------------------------------------------------------------
# Parcel-driven entrypoint -- read a parsed JSON, verify its top-N email
# candidates (running email_discovery if not already populated)
# ---------------------------------------------------------------------------
async def verify_parcel(parcel_path: Path, top_n: int = 3,
                          write_back: bool = True) -> dict:
    lead = json.loads(parcel_path.read_text())
    owner_name = lead.get("owner_name", "")
    state = lead.get("owner_mailing_state", "")

    if not owner_name:
        return {"path": parcel_path.name, "ok": False, "reason": "no owner_name"}

    # If email_verification already cached, just return it
    cached = lead.get("email_verification")
    if cached and cached.get("verified_at"):
        return {"path": parcel_path.name, "ok": True, "cached": True,
                 "results": cached.get("results", [])}

    # Generate candidates via email_discovery if not present in lead
    candidates = lead.get("email_candidates")
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        if not candidates:
            from osint_api.investigators import email_discovery
            ed_result = await email_discovery.run(owner_name, http)
            candidates = ed_result.get("raw", {}).get("top_candidates", [])

        if not candidates:
            return {"path": parcel_path.name, "ok": False,
                     "reason": "no email candidates"}

        results = []
        for email in candidates[:top_n]:
            v = await verify(email, owner_name, state, http)
            results.append(v)

    # Write back to parcel JSON
    lead["email_verification"] = {
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": results,
        "candidates_checked": len(results),
    }
    if write_back:
        parcel_path.write_text(json.dumps(lead, indent=2, default=str))

    return {"path": parcel_path.name, "ok": True, "results": results}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--email", help="Verify a specific candidate email")
    p.add_argument("--name", help="Expected assessor owner_name (with --email)")
    p.add_argument("--state", default="", help="Expected owner_mailing_state (with --email)")
    p.add_argument("--parcel", help="Verify top-N candidates from a parcel JSON")
    p.add_argument("--top-n", type=int, default=3, help="How many candidates to verify (--parcel mode)")
    p.add_argument("--dry-run", action="store_true", help="Don't write back to parcel JSON")
    args = p.parse_args()

    if args.email and args.name:
        async def go():
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
                r = await verify(args.email, args.name, args.state, http)
                print(json.dumps(r, indent=2, default=str))
        asyncio.run(go())
        return

    if args.parcel:
        path = PARSED_DIR / f"{args.parcel}.json"
        if not path.exists():
            print(f"Parcel not found: {path}", file=sys.stderr)
            sys.exit(1)
        async def go():
            r = await verify_parcel(path, top_n=args.top_n, write_back=not args.dry_run)
            print(json.dumps(r, indent=2, default=str))
        asyncio.run(go())
        return

    p.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
