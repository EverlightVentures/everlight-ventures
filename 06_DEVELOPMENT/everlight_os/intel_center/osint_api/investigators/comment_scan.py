"""comment_scan -- find public posts/comments that tie an email to this person.

For a target name + city, fan out 6-10 DuckDuckGo HTML search dorks like:
    "<NAME>" "@gmail.com" <city>
    "<NAME>" "@yahoo.com" <city>
    "<NAME>" <city> contact|email
    intext:"<NAME>" intext:"@" <city>

Pull the result snippets, regex out any email-like tokens, and emit each
(email, snippet, source_url) tuple as a finding. Strongest signal: an email
whose local-part matches a permutation of the name AND appears in a snippet
that also names the city or property -- that is a hard third-party tie.

Returns the standard investigator dict:
    {"findings": [...top items in {label,value,url} form...],
     "raw": {"hits": [...full records...]},
     "top_score": int 0-100, "high_confidence": bool}
"""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

from ._common import fetch, now_ms

NAME = "Comment Scan"
DOMAINS = ["html.duckduckgo.com"]
WHEN = ["person"]

# Delay between dork fetches to be polite to DDG
_INTER_DORK_DELAY_S = 0.6

# Max snippets to parse per dork response
_SNIPPETS_PER_DORK = 6

# Regex: matches email-like tokens in HTML-decoded text
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]{2,40}@[a-zA-Z0-9.\-]{2,30}\.[a-zA-Z]{2,6}"
)

# Regex to strip most HTML tags quickly
_HTML_TAG_RE = re.compile(r"<[^>]{1,200}>")

# Common spam / placeholder emails to discard
_JUNK_DOMAINS = {
    "example.com", "test.com", "domain.com", "email.com",
    "yourname.com", "placeholder.com", "sampleemail.com",
}


def _build_dorks(owner_name: str, city: str) -> list[str]:
    """Return 6-8 DuckDuckGo query strings for comment-scan coverage."""
    name = owner_name.strip()
    city = city.strip()
    dorks = [
        f'"{name}" "@gmail.com" {city}',
        f'"{name}" "@yahoo.com" {city}',
        f'"{name}" "@hotmail.com" {city}',
        f'"{name}" {city} contact email',
        f'"{name}" {city} "@"',
        f'intext:"{name}" {city} site:reddit.com email',
        f'intext:"{name}" {city} site:whitepages.com',
        f'"{name}" {city} email address',
    ]
    # Drop dorks with blank city (still valid, just less targeted)
    return [d for d in dorks if name]


def _name_match_score(email_local: str, owner_name: str) -> int:
    """0-40: how well does the email local-part match name permutations."""
    local = email_local.lower().replace(".", "").replace("_", "").replace("-", "")
    parts = [p.lower() for p in owner_name.split() if len(p) > 1]
    if not parts:
        return 0

    score = 0
    first = parts[0] if parts else ""
    last = parts[-1] if len(parts) > 1 else ""

    # Direct contains
    for p in parts:
        if p in local:
            score += 10
    # Combined first+last
    if first and last:
        if (first + last) in local or (last + first) in local:
            score += 20
    # Initials
    if all(p[0] in local for p in parts if p):
        score += 5

    return min(score, 40)


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub(" ", text)


def _parse_ddg_results(html: str) -> list[dict]:
    """Extract (title, snippet, url) tuples from DDG HTML response."""
    results = []

    # Match result blocks: DDG wraps each hit in a div.result
    blocks = re.findall(
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        html, re.DOTALL
    )
    if not blocks:
        # Fallback: grab anything that looks like a snippet
        blocks = re.findall(
            r'class="result__snippet[^"]*"[^>]*>(.*?)</(?:a|div|span)>',
            html, re.DOTALL
        )

    # Also grab result links/titles for URL pairing
    links = re.findall(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        html
    )

    for i, snippet_html in enumerate(blocks[:_SNIPPETS_PER_DORK]):
        snippet = _strip_html(snippet_html).strip()[:300]
        url = ""
        title = ""
        if i < len(links):
            raw_href, raw_title = links[i]
            title = _strip_html(raw_title).strip()[:120]
            # DDG wraps URLs in /l/?uddg= redirect
            if "uddg=" in raw_href:
                from urllib.parse import unquote, parse_qs, urlparse
                try:
                    qs = parse_qs(urlparse(raw_href).query)
                    url = unquote(qs.get("uddg", [""])[0])
                except Exception:
                    url = raw_href
            else:
                url = raw_href

        results.append({"title": title, "snippet": snippet, "url": url})

    return results


def _extract_emails_from_text(text: str) -> list[str]:
    """Pull all plausible email addresses from a text blob."""
    raw = _EMAIL_RE.findall(text)
    out = []
    for e in raw:
        domain = e.split("@", 1)[-1].lower()
        if domain in _JUNK_DOMAINS:
            continue
        # Skip obviously auto-generated patterns (noreply, no-reply, etc.)
        local = e.split("@")[0].lower()
        if any(skip in local for skip in ("noreply", "no-reply", "donotreply", "mailer")):
            continue
        out.append(e.lower())
    return out


def _score_hit(
    email: str,
    snippet: str,
    owner_name: str,
    city: str,
) -> int:
    """
    Compute confidence score 0-100 for a (email, snippet, owner_name, city) tuple.

    Breakdown:
    - 0-40: name permutation match in email local-part
    - 0-30: city / state mentioned in snippet
    - 0-20: email domain plausibility (gmail/yahoo/icloud higher than random)
    - 0-10: snippet length / richness bonus
    """
    local, domain = email.split("@", 1) if "@" in email else (email, "")

    name_score = _name_match_score(local, owner_name)

    city_lower = city.lower()
    snippet_lower = snippet.lower()
    city_score = 0
    if city_lower and city_lower in snippet_lower:
        city_score = 30
    elif city_lower and any(w in snippet_lower for w in city_lower.split()):
        city_score = 15

    trusted_domains = {"gmail.com", "yahoo.com", "hotmail.com", "icloud.com",
                       "outlook.com", "live.com", "aol.com", "protonmail.com"}
    domain_score = 20 if domain.lower() in trusted_domains else 8

    richness_score = min(10, len(snippet.strip()) // 30)

    return min(100, name_score + city_score + domain_score + richness_score)


async def run(target: str, http) -> dict:
    """
    Run comment_scan for target.

    Target format accepted:
      - "First Last, City"   -> parsed automatically
      - "First Last"         -> city left blank (lower signal)

    The caller (orchestrator) may inject extra context by passing a string
    like "Rita Townsend, Memphis" or just "Rita Townsend".
    """
    t0 = now_ms()

    # Parse target: "Name, City" or "Name"
    if "," in target:
        name_part, city_part = target.split(",", 1)
        owner_name = name_part.strip().title()
        city = city_part.strip().title()
    else:
        owner_name = target.strip().title()
        city = ""

    dorks = _build_dorks(owner_name, city)

    # {email -> {score, snippets, urls}}
    seen: dict[str, dict] = {}
    raw_hits: list[dict] = []

    for dork in dorks:
        encoded = quote(dork)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        status, text, err = await fetch(http, url, timeout=8)

        if err or status != 200 or not text:
            raw_hits.append({"dork": dork, "status": status, "error": err, "emails": []})
            await asyncio.sleep(_INTER_DORK_DELAY_S)
            continue

        parsed = _parse_ddg_results(text)
        dork_emails: list[str] = []

        for result in parsed:
            combined = f"{result['title']} {result['snippet']}"
            emails = _extract_emails_from_text(combined)
            for email in emails:
                score = _score_hit(email, combined, owner_name, city)
                if email not in seen:
                    seen[email] = {
                        "email": email,
                        "score": score,
                        "snippets": [],
                        "urls": [],
                    }
                else:
                    # Corroboration bump: same email found in multiple dorks
                    seen[email]["score"] = min(100, seen[email]["score"] + 8)

                if result["snippet"]:
                    seen[email]["snippets"].append(result["snippet"][:200])
                if result["url"]:
                    seen[email]["urls"].append(result["url"])
                dork_emails.append(email)

        raw_hits.append({
            "dork": dork,
            "status": status,
            "emails": dork_emails,
            "results_count": len(parsed),
        })
        await asyncio.sleep(_INTER_DORK_DELAY_S)

    # Build findings list (sorted by score, highest first)
    sorted_hits = sorted(seen.values(), key=lambda h: h["score"], reverse=True)

    findings = []
    for hit in sorted_hits[:12]:
        best_snippet = hit["snippets"][0] if hit["snippets"] else ""
        best_url = hit["urls"][0] if hit["urls"] else ""
        findings.append({
            "label": f"email:{hit['email']} (score {hit['score']})",
            "value": best_snippet or hit["email"],
            "url": best_url,
            "email": hit["email"],
            "score": hit["score"],
        })

    top_score = sorted_hits[0]["score"] if sorted_hits else 0
    high_confidence = top_score >= 55

    return {
        "ok": len(findings) > 0,
        "findings": findings,
        "raw": {"hits": raw_hits, "unique_emails_found": len(seen)},
        "top_score": top_score,
        "high_confidence": high_confidence,
        "elapsed_ms": now_ms() - t0,
        "investigator": NAME,
        "investigator_id": "comment_scan",
    }
