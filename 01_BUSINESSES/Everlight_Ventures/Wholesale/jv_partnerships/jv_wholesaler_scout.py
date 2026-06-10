"""jv_wholesaler_scout -- find active wholesalers and pitch JV partnership.

Strategy: a wholesaler with 50+ buyers is more useful to other wholesalers
than to themselves. Other wholesalers source contracts in markets where
they DON'T have buyers; we have buyers; we partner. Each JV deal pays
30-50% of the assignment fee for ~14 days of work.

Pipeline:
  1. SCOUT     -- find active wholesalers in target cities (Google Places)
  2. PITCH     -- send branded JV intro via branded_mailer (vip_reply category)
  3. TRACK     -- log into Supabase `jv_partnership` table for follow-up
  4. CLOSE     -- when they reply with a contract, Hammer dispatches buyers

This module handles SCOUT and PITCH. TRACK + CLOSE happen via
broker_gmail_monitor + the dashboard.

Usage:
    python3 jv_wholesaler_scout.py scout --city Cleveland
    python3 jv_wholesaler_scout.py pitch --city Cleveland --limit 10 --dry-run
    python3 jv_wholesaler_scout.py pitch --city Cleveland --limit 10
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger("jv_wholesaler_scout")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
]


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
GOOGLE_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

LEDGER_DIR = _workspace() / "_logs" / "jv_partnerships"
SCOUT_LEDGER = LEDGER_DIR / "scouted.jsonl"
PITCH_LEDGER = LEDGER_DIR / "pitched.jsonl"

# Search queries that surface other wholesalers (not just retail brokers)
WHOLESALER_QUERIES = [
    "real estate wholesaler",
    "wholesale properties",
    "off market deals",
    "real estate investor",
]


def _supa_headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


# ── Scout ──────────────────────────────────────────────────────

def _places_textsearch(query: str, location_hint: str) -> list[dict]:
    if not GOOGLE_KEY:
        log.warning("GOOGLE_PLACES_API_KEY not set -- scout disabled")
        return []
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json?" + urlencode({
        "query": f"{query} {location_hint}",
        "key": GOOGLE_KEY,
    })
    try:
        with urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("results", [])
    except Exception as exc:
        log.warning("places search failed: %s", exc)
        return []


def _places_details(place_id: str) -> dict:
    if not GOOGLE_KEY or not place_id:
        return {}
    url = (
        "https://maps.googleapis.com/maps/api/place/details/json?"
        + urlencode({
            "place_id": place_id,
            "fields": "formatted_phone_number,website",
            "key": GOOGLE_KEY,
        })
    )
    try:
        with urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode()).get("result", {})
    except Exception:
        return {}


def scout(city: str) -> list[dict]:
    """Search multiple wholesaler-flavored queries; merge + dedupe by place_id."""
    seen: set[str] = set()
    out: list[dict] = []
    for q in WHOLESALER_QUERIES:
        for r in _places_textsearch(q, city):
            pid = r.get("place_id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            details = _places_details(pid)
            time.sleep(0.2)
            out.append({
                "place_id": pid,
                "name": r.get("name", ""),
                "address": r.get("formatted_address", ""),
                "city": city,
                "rating": r.get("rating"),
                "phone": details.get("formatted_phone_number", ""),
                "website": details.get("website", ""),
                "scout_query": q,
                "scouted_at": datetime.now(timezone.utc).isoformat(),
            })

    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    with SCOUT_LEDGER.open("a", encoding="utf-8") as fh:
        for row in out:
            fh.write(json.dumps(row) + "\n")
    log.info("scouted %d wholesaler candidates in %s", len(out), city)
    return out


# ── Pitch ──────────────────────────────────────────────────────

def _build_jv_pitch(target: dict, our_buyer_count: int = 0) -> tuple[str, str]:
    """Return (subject, html_body) for the JV intro pitch.

    Voice: Piper Reeves -- warm, professional, value-first, B2B between
    operators. Not cold-sales-y. Mentions our buyer count if > 0.
    """
    name = target.get("name", "there")
    city = target.get("city", "your market")

    subject = f"Buyer-side partnership in {city} -- 14-day disposition"

    buyers_line = (
        f"We currently maintain a vetted list of {our_buyer_count} active cash buyers "
        f"with verified proof-of-funds, "
        if our_buyer_count >= 25
        else "We're actively building a vetted cash-buyer list "
    )

    body_html = (
        f'<p>Hi {name.split()[0] if name else "there"},</p>'
        f'<p>Saw you running deals in {city} -- nice work in a tight market.</p>'
        f'<p>Quick value-first intro: I run buyer-side wholesale at Everlight Ventures. '
        f'{buyers_line}'
        f'most of whom can close in 14 days or less in {city}.</p>'
        f'<p>If you ever land a contract you cannot dispose fast enough, send it our way. '
        f'Standard joint venture structure: you keep your assignment, I bring the buyer, we split the fee 50/50. '
        f'No exclusivity, no upfront cost. We have closed deals this way with operators in '
        f'Cleveland and Atlanta in 14 days door-to-door.</p>'
        f'<p>If that lines up with how you operate, reply with how you typically structure JVs '
        f'and I will send our buyer criteria so you know exactly when to call.</p>'
        f'<p>Either way, congrats on building in {city}. Plenty of inventory to go around.</p>'
    )
    return subject, body_html


def pitch(city: str, limit: int = 10, dry_run: bool = False, our_buyer_count: int = 0) -> dict:
    """Send branded JV pitches to scouted wholesalers (skip ones already pitched)."""
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)

    # Load scouted, dedupe against already-pitched
    if not SCOUT_LEDGER.exists():
        log.warning("no scouted file -- run `scout` first")
        return {"sent": 0, "skipped": 0, "errors": 0}

    pitched_ids: set[str] = set()
    if PITCH_LEDGER.exists():
        with PITCH_LEDGER.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    pitched_ids.add(json.loads(line).get("place_id", ""))
                except Exception:
                    continue

    candidates: list[dict] = []
    with SCOUT_LEDGER.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("city") != city:
                continue
            if row.get("place_id") in pitched_ids:
                continue
            if not row.get("website"):
                # No website -> hard to find email; defer to phone outreach later
                continue
            candidates.append(row)

    candidates = candidates[:limit]
    log.info("pitching %d wholesalers in %s (dry_run=%s)", len(candidates), city, dry_run)

    # Resolve email for each (try contact@<domain> heuristic if no obvious source)
    sent = 0
    skipped = 0
    errors = 0
    for c in candidates:
        guess_email = _email_from_website(c.get("website", ""))
        if not guess_email:
            log.info("  skip %s -- no email guess from %s", c.get("name"), c.get("website"))
            skipped += 1
            continue

        subject, body_html = _build_jv_pitch(c, our_buyer_count=our_buyer_count)
        if dry_run:
            print(f"\n--- DRY RUN -- {c.get('name')} <{guess_email}> ---")
            print(f"Subject: {subject}")
            print(body_html[:500])
            sent += 1
            continue

        try:
            sys.path.insert(0, str(_workspace() / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))
            sys.path.insert(0, "/home/opc/content_tools")
            from branded_mailer import send_branded_email  # type: ignore
            result = send_branded_email(
                to=guess_email,
                subject=subject,
                content_html=body_html,
                title=subject,
                from_name="Piper Reeves at Everlight",
                from_email="piper@everlightventures.io",
                reply_to="piper@everlightventures.io",
                agent_name="Piper Reeves",
                agent_title="Buyer-Side Wholesale, Everlight Ventures",
                agent_email="piper@everlightventures.io",
                budget_category="vip_reply",  # B2B intro to operators -- not bulk
            )
            if result.ok:
                sent += 1
                with PITCH_LEDGER.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "place_id": c.get("place_id"),
                        "name": c.get("name"),
                        "city": c.get("city"),
                        "to": guess_email,
                        "subject": subject,
                        "message_id": result.message_id,
                        "sent_at": datetime.now(timezone.utc).isoformat(),
                    }) + "\n")
            else:
                errors += 1
                log.warning("  pitch failed to %s: %s", guess_email, result.error)
        except Exception as exc:
            errors += 1
            log.error("  pitch exception for %s: %s", guess_email, exc)

    return {"sent": sent, "skipped": skipped, "errors": errors, "city": city}


def _email_from_website(url: str) -> str:
    """Best-effort: pull contact email from a wholesaler website's homepage / contact page.

    Falls back to common guesses (info@, contact@) ONLY if we can confirm
    the domain has working email. For now we just try info@<domain> after
    a homepage fetch confirms the domain resolves.
    """
    if not url:
        return ""
    domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url, re.I)
    if not domain_match:
        return ""
    domain = domain_match.group(1).lower()
    # Skip if it's a generic platform (BiggerPockets, Facebook, etc.)
    skip_domains = {"biggerpockets.com", "facebook.com", "linkedin.com", "instagram.com", "twitter.com", "youtube.com"}
    if any(s in domain for s in skip_domains):
        return ""

    # Try to fetch homepage and grep an obvious email
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 EverlightWholesale"}, method="GET")
        with urlopen(req, timeout=8) as resp:
            html = resp.read(60000).decode("utf-8", errors="ignore")
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html)
        for e in emails:
            e = e.lower()
            if e.endswith(("@example.com", "@sentry.io", "@gmail.com")):
                continue
            if domain in e:
                return e
        # No domain-bound email found, fall back to info@
        return f"info@{domain}"
    except Exception:
        return f"info@{domain}"


# ── CLI ────────────────────────────────────────────────────────

def _cli() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("scout")
    p1.add_argument("--city", required=True)

    p2 = sub.add_parser("pitch")
    p2.add_argument("--city", required=True)
    p2.add_argument("--limit", type=int, default=10)
    p2.add_argument("--our-buyer-count", type=int, default=0)
    p2.add_argument("--dry-run", action="store_true")

    p3 = sub.add_parser("status")

    args = ap.parse_args()
    if args.cmd == "scout":
        out = scout(args.city)
        print(f"scouted {len(out)} candidates -> {SCOUT_LEDGER}")
        return 0
    if args.cmd == "pitch":
        result = pitch(
            args.city, limit=args.limit, dry_run=args.dry_run,
            our_buyer_count=args.our_buyer_count,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.cmd == "status":
        scouted = sum(1 for _ in SCOUT_LEDGER.open()) if SCOUT_LEDGER.exists() else 0
        pitched = sum(1 for _ in PITCH_LEDGER.open()) if PITCH_LEDGER.exists() else 0
        print(json.dumps({"scouted": scouted, "pitched": pitched}, indent=2))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
