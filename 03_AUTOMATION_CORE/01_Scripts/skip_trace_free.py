"""skip_trace_free -- zero-cost skip tracing via public people-search sites.

Reads `leads_db.json` for leads missing email or phone, runs a web search
against TruePeopleSearch / FastPeopleSearch public HTML pages, and writes
phone/email back onto the lead record + per-state CSV.

Rate-limits heavily -- these sites IP-ban aggressive traffic. Default
cadence is 15 seconds between requests. Run in batches of ~30/day per
source to stay under the radar.

Usage:
    python3 skip_trace_free.py --limit 10            # weekend batch
    python3 skip_trace_free.py --limit 50            # full run
    python3 skip_trace_free.py --state GA            # only GA leads
    python3 skip_trace_free.py --dry-run             # preview without writes
    python3 skip_trace_free.py --test "Dan Avenick" "Atlanta" "GA"

Outputs:
    - Updates leads_db.json (phone, email, skip_traced_at, skip_trace_source)
    - Updates per-state CSV at Wholesale/prospecting/<STATE>_prospects.csv
    - Log at _logs/skip_trace_free.log

Respects:
    - Per-lead skip_traced_at: never re-traces within 90 days
    - User-agent randomization
    - 15s inter-request delay (adjustable via --delay)
    - Soft-fail on rate-limit (stops early, tomorrow is another day)
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

try:
    import httpx
except ImportError:
    print("ERR: httpx not installed. pip install httpx")
    sys.exit(1)
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERR: beautifulsoup4 not installed. pip install beautifulsoup4")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="[skip-trace %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("skip_trace_free")

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent" / "leads_db.json"
PROSP = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "prospecting"
LOG_DIR = ROOT / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "skip_trace_free.log"
STATE_LOG = LOG_DIR / "skip_trace_free_results.jsonl"

USER_AGENTS = [
    # Realistic recent browsers -- rotated per request
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

PHONE_RE  = re.compile(r"\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})")
EMAIL_RE  = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

STALE_AFTER_DAYS = 90


# ---------------------------------------------------------------------------
# Per-source scrapers -- each returns {"phones": [..], "emails": [..], "source": "..."}
# ---------------------------------------------------------------------------

def scrape_truepeoplesearch(name: str, city: str, state: str, timeout: float = 15) -> dict:
    """TruePeopleSearch public results page."""
    q = f"{name} {city} {state}".strip()
    url = f"https://www.truepeoplesearch.com/results?name={quote_plus(name)}&citystatezip={quote_plus(f'{city}, {state}')}"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            if r.status_code >= 400:
                return {"phones": [], "emails": [], "source": "tps", "error": f"http_{r.status_code}"}
            text = r.text
    except Exception as e:
        return {"phones": [], "emails": [], "source": "tps", "error": str(e)[:80]}

    soup = BeautifulSoup(text, "html.parser")
    # TPS shows phone numbers in `<span class="detail-phone">` or similar; fallback: any phone-looking text
    phones = set(f"{a}-{b}-{c}" for a, b, c in PHONE_RE.findall(text))
    emails = set(EMAIL_RE.findall(text))
    # strip obvious false positives
    phones = {p for p in phones if not p.startswith("000") and not p.startswith("555")}
    emails = {e for e in emails if not any(junk in e.lower() for junk in ("example.com", "truepeoplesearch.com", "support@", "noreply@"))}
    return {"phones": sorted(phones), "emails": sorted(emails), "source": "tps"}


def scrape_radaris(name: str, city: str, state: str, timeout: float = 15) -> dict:
    """Radaris public results page -- usually less bot-guarded than TPS/FPS."""
    slug_name = name.lower().replace(",", " ").strip().replace("  ", " ").replace(" ", "+")
    url = f"https://radaris.com/ng/search?ff={quote_plus(name.split()[0] if name.split() else '')}&fl={quote_plus(' '.join(name.split()[1:]) if len(name.split())>1 else '')}&ffm=1&flm=1&location={quote_plus(f'{city}, {state}')}"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            if r.status_code >= 400:
                return {"phones": [], "emails": [], "source": "radaris", "error": f"http_{r.status_code}"}
            text = r.text
    except Exception as e:
        return {"phones": [], "emails": [], "source": "radaris", "error": str(e)[:80]}
    phones = set(f"{a}-{b}-{c}" for a, b, c in PHONE_RE.findall(text))
    emails = set(EMAIL_RE.findall(text))
    phones = {p for p in phones if not p.startswith("000") and not p.startswith("555")}
    emails = {e for e in emails if not any(junk in e.lower() for junk in ("example.com", "radaris.com", "support@", "noreply@"))}
    return {"phones": sorted(phones), "emails": sorted(emails), "source": "radaris"}


def scrape_fastpeoplesearch(name: str, city: str, state: str, timeout: float = 15) -> dict:
    """FastPeopleSearch public results page."""
    # URL pattern: /name/<first>-<last>_<city>-<state>
    slug_name = name.lower().replace(",", "").replace("  ", " ").strip().replace(" ", "-")
    slug_loc = f"{city.lower().replace(' ','-')}-{state.lower()}"
    url = f"https://www.fastpeoplesearch.com/name/{slug_name}_{slug_loc}"
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9"}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            if r.status_code >= 400:
                return {"phones": [], "emails": [], "source": "fps", "error": f"http_{r.status_code}"}
            text = r.text
    except Exception as e:
        return {"phones": [], "emails": [], "source": "fps", "error": str(e)[:80]}

    phones = set(f"{a}-{b}-{c}" for a, b, c in PHONE_RE.findall(text))
    emails = set(EMAIL_RE.findall(text))
    phones = {p for p in phones if not p.startswith("000") and not p.startswith("555")}
    emails = {e for e in emails if not any(junk in e.lower() for junk in ("example.com", "fastpeoplesearch.com", "support@", "noreply@"))}
    return {"phones": sorted(phones), "emails": sorted(emails), "source": "fps"}


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------

def _lead_needs_trace(lead: dict) -> bool:
    if lead.get("email") or lead.get("owner_email") or lead.get("phone") or lead.get("owner_phone"):
        return False
    if lead.get("skip_traced_at"):
        try:
            ts = datetime.fromisoformat(lead["skip_traced_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - ts < timedelta(days=STALE_AFTER_DAYS):
                return False
        except Exception:
            pass
    if not (lead.get("owner_name") and lead.get("city") and lead.get("state")):
        return False
    # Skip institutional-looking names (same pattern state_property_hunter uses)
    INST = ("LLC", "TRUST", "INC", "CORP", " LP", "BANK", "AUTHORITY", "DIOCESE",
            "DEVELOPMENT", "ASSOCIATION", "REALTY", "HOLDINGS", "PARTNERS",
            "INVESTMENTS", "CITY OF", "STATE OF", "COUNTY")
    nm = (lead.get("owner_name") or "").upper()
    if any(t in nm for t in INST):
        return False
    return True


def _write_state_csv_incremental(state: str, leads_in_state: list[dict]) -> None:
    """Rewrite the per-state prospect CSV so the touches/email/phone columns reflect
    latest leads_db state. Minimal cost -- 1 rewrite per state per run."""
    path = PROSP / f"{state}_prospects.csv"
    PROSP.mkdir(parents=True, exist_ok=True)
    fields = [
        "lead_id", "address", "city", "state", "zip", "owner_name", "email", "phone",
        "estimated_arv", "beds", "baths", "sqft", "year_built", "lead_type", "distress",
        "status", "touches", "first_contacted", "last_contacted", "last_message",
        "reply_received", "offer_amount", "outcome", "source", "created_at",
        "skip_traced_at", "skip_trace_source",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for l in leads_in_state:
            w.writerow({
                "lead_id": l.get("id", ""),
                "address": l.get("address", ""),
                "city": l.get("city", ""),
                "state": l.get("state", ""),
                "zip": l.get("zip", ""),
                "owner_name": l.get("owner_name", ""),
                "email": l.get("email") or l.get("owner_email", ""),
                "phone": l.get("phone") or l.get("owner_phone", ""),
                "estimated_arv": l.get("estimated_arv", ""),
                "beds": l.get("beds", ""), "baths": l.get("baths", ""),
                "sqft": l.get("sqft", ""), "year_built": l.get("year_built", ""),
                "lead_type": l.get("lead_type", ""),
                "distress": l.get("detected_distress", ""),
                "status": l.get("status", ""),
                "touches": l.get("touch_count", 0),
                "first_contacted": l.get("first_contacted", ""),
                "last_contacted": l.get("last_contacted", ""),
                "last_message": l.get("last_message", ""),
                "reply_received": l.get("reply_received", False),
                "offer_amount": l.get("offer_amount", ""),
                "outcome": l.get("outcome", ""),
                "source": l.get("source", ""),
                "created_at": l.get("created_at", ""),
                "skip_traced_at": l.get("skip_traced_at", ""),
                "skip_trace_source": l.get("skip_trace_source", ""),
            })


def run(limit: int = 10, only_state: str | None = None,
        delay: float = 15.0, dry_run: bool = False) -> dict[str, Any]:
    if not LEADS_DB.exists():
        log.error("leads_db.json not found at %s", LEADS_DB)
        return {"processed": 0}

    leads = json.loads(LEADS_DB.read_text())
    # Filter queue
    queue = [l for l in leads if _lead_needs_trace(l)]
    if only_state:
        queue = [l for l in queue if (l.get("state") or "").upper() == only_state.upper()]
    queue = queue[:limit]

    log.info("queue=%d (limit=%d state=%s delay=%.1fs)", len(queue), limit, only_state or "all", delay)
    if dry_run:
        for l in queue[:10]:
            log.info("  would trace: %s @ %s, %s", l.get("owner_name"), l.get("city"), l.get("state"))
        return {"processed": 0, "queue_size": len(queue), "dry_run": True}

    results_log = STATE_LOG.open("a")
    hits_phone = 0; hits_email = 0; trace_attempts = 0
    touched_states: set[str] = set()
    rate_limited = False

    for lead in queue:
        if rate_limited:
            log.warning("rate-limit encountered -- stopping early")
            break
        name = lead.get("owner_name", "")
        city = lead.get("city", "")
        state = (lead.get("state") or "").upper()
        trace_attempts += 1
        log.info("tracing: %s / %s, %s", name, city, state)

        found = {"phones": [], "emails": [], "source": ""}
        for fn in (scrape_truepeoplesearch, scrape_fastpeoplesearch, scrape_radaris):
            r = fn(name, city, state)
            if r.get("error"):
                if "429" in str(r["error"]) or "forbidden" in str(r["error"]).lower():
                    log.warning("  %s rate-limited: %s", r.get("source"), r["error"])
                    rate_limited = True
                    break
                log.debug("  %s error: %s", r.get("source"), r["error"])
                continue
            if r.get("phones") or r.get("emails"):
                found = r
                break  # first source that hits is enough
            time.sleep(3)  # small between-source delay
        if rate_limited:
            break

        # Merge back into lead
        if found.get("phones"):
            lead["phone"] = found["phones"][0]
            hits_phone += 1
        if found.get("emails"):
            lead["email"] = found["emails"][0]
            hits_email += 1
        lead["skip_traced_at"] = datetime.now(timezone.utc).isoformat()
        lead["skip_trace_source"] = found.get("source", "none")

        results_log.write(json.dumps({
            "ts": lead["skip_traced_at"],
            "name": name, "city": city, "state": state,
            "phones": found.get("phones", []),
            "emails": found.get("emails", []),
            "source": found.get("source"),
        }) + "\n"); results_log.flush()
        touched_states.add(state)
        log.info("  result: phones=%d emails=%d via %s", len(found.get("phones", [])), len(found.get("emails", [])), found.get("source") or "none")

        # Persist incrementally so a kill doesn't lose the work
        LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))

        # Cooldown
        jitter = random.uniform(0, delay * 0.4)
        time.sleep(delay + jitter)

    # Rewrite per-state CSVs for the states we touched
    if not dry_run:
        from collections import defaultdict
        by_state = defaultdict(list)
        for l in leads:
            by_state[(l.get("state") or "UNK").upper()].append(l)
        for st in touched_states:
            _write_state_csv_incremental(st, by_state[st])

    results_log.close()
    summary = {
        "processed": trace_attempts,
        "queue_initial": len(queue),
        "hits_phone": hits_phone,
        "hits_email": hits_email,
        "touched_states": sorted(touched_states),
        "rate_limited": rate_limited,
    }
    log.info("DONE %s", summary)
    return summary


def generate_worklist(only_state: str | None = None, limit: int = 100) -> Path:
    """Produce a CSV the user can work through by hand in their browser.

    Columns: name, city, state, tps_url, fps_url, radaris_url, google_url, phone (blank), email (blank).
    User opens the URL, copies phone/email, pastes into the sheet.
    Then imports via --import.
    """
    PROSP.mkdir(parents=True, exist_ok=True)
    leads = json.loads(LEADS_DB.read_text())
    queue = [l for l in leads if _lead_needs_trace(l)]
    if only_state:
        queue = [l for l in queue if (l.get("state") or "").upper() == only_state.upper()]
    queue = queue[:limit]

    out = PROSP / f"SKIP_TRACE_WORKLIST_{only_state or 'ALL'}.csv"
    fields = [
        "lead_id", "name", "city", "state", "address",
        "tps_url", "fps_url", "radaris_url", "google_url",
        "phone_found", "email_found", "notes",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for l in queue:
            name = l.get("owner_name", "")
            city = l.get("city", "")
            state = (l.get("state") or "").upper()
            loc = quote_plus(f"{city}, {state}")
            w.writerow({
                "lead_id":    l.get("id", ""),
                "name":       name,
                "city":       city,
                "state":      state,
                "address":    l.get("address", ""),
                "tps_url":    f"https://www.truepeoplesearch.com/results?name={quote_plus(name)}&citystatezip={loc}",
                "fps_url":    f"https://www.fastpeoplesearch.com/name/{name.lower().replace(',', '').strip().replace(' ', '-')}_{city.lower().replace(' ','-')}-{state.lower()}",
                "radaris_url":f"https://radaris.com/ng/search?ff={quote_plus(name.split()[0] if name.split() else '')}&fl={quote_plus(' '.join(name.split()[1:]) if len(name.split())>1 else '')}&location={loc}",
                "google_url": f"https://www.google.com/search?q={quote_plus(f'{name} {city} {state} phone email')}",
                "phone_found": "",
                "email_found": "",
                "notes":       "",
            })
    return out


def import_results(csv_path: Path) -> dict:
    """Read a filled-in worklist CSV and write the phone/email back onto leads_db.json."""
    leads = json.loads(LEADS_DB.read_text())
    by_id = {str(l.get("id", "")): l for l in leads}
    updated = 0
    with csv_path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lid = (row.get("lead_id") or "").strip()
            p = (row.get("phone_found") or "").strip()
            e = (row.get("email_found") or "").strip()
            if not lid or (not p and not e):
                continue
            if lid not in by_id:
                continue
            lead = by_id[lid]
            if p and not lead.get("phone"): lead["phone"] = p
            if e and not lead.get("email"): lead["email"] = e
            lead["skip_traced_at"] = datetime.now(timezone.utc).isoformat()
            lead["skip_trace_source"] = "manual"
            updated += 1
    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))
    return {"imported": updated, "from": str(csv_path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10, help="max leads to trace this run")
    ap.add_argument("--state", help="single state filter (e.g. GA)")
    ap.add_argument("--delay", type=float, default=15.0, help="seconds between lookups")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test", nargs=3, metavar=("NAME", "CITY", "STATE"),
                    help="single-shot test of the scrapers (no DB writes)")
    ap.add_argument("--worklist", action="store_true",
                    help="Generate a manual-lookup worklist CSV (no scraping)")
    ap.add_argument("--import", dest="import_csv",
                    help="Import a filled-in worklist CSV back into leads_db.json")
    args = ap.parse_args()

    if args.import_csv:
        p = Path(args.import_csv)
        if not p.exists():
            print(f"ERR: {p} not found"); sys.exit(1)
        print(json.dumps(import_results(p), indent=2))
        return

    if args.worklist:
        out = generate_worklist(only_state=args.state, limit=args.limit)
        print(f"worklist: {out}")
        # Count lines for UX
        n = sum(1 for _ in out.open()) - 1
        print(f"leads in worklist: {n}")
        print("Fill phone_found / email_found columns in your spreadsheet, then:")
        print(f"  python3 skip_trace_free.py --import {out}")
        return

    if args.test:
        name, city, state = args.test
        print(f"--- TPS ---"); print(json.dumps(scrape_truepeoplesearch(name, city, state), indent=2))
        print(f"--- FPS ---"); print(json.dumps(scrape_fastpeoplesearch(name, city, state), indent=2))
        print(f"--- Radaris ---"); print(json.dumps(scrape_radaris(name, city, state), indent=2))
        return

    s = run(limit=args.limit, only_state=args.state, delay=args.delay, dry_run=args.dry_run)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
