"""
assessor_harvester.py -- E5-mother browser-driven owner enrichment via Playwright.

Runs on e5-mother (Playwright + Chromium available there).
Reads TN leads from leads_db that are missing enrichment, opens
https://www.assessormelvinburgess.com/propertySearch, types each address,
waits for ArcGIS JS results, extracts structured owner data, and writes
back into leads_db.

Usage
-----
    # queue preview (no browser needed):
    python3 assessor_harvester.py --dry-run --limit 10

    # live run on e5-mother:
    python3 assessor_harvester.py --limit 25 --state TN --delay-seconds 4

    # resume after partial run (skip assessor_done + assessor_failed):
    python3 assessor_harvester.py --resume --limit 50

NOT to be run on the phone proot -- Playwright requires Chromium.
If Playwright is missing this script prints an install hint and exits 2.

Selector assumption
-------------------
RESULTS_SELECTOR below is the CSS selector we wait on before grabbing HTML.
The assessormelvinburgess.com site is ArcGIS / Esri-based; it renders results
inside a <div class="esriPopupWrapper"> or a <div class="esriPopupContent"> on
earlier versions.  We use a fallback chain:
  1. ".esriPopupWrapper"
  2. "#resultsDiv"
  3. "table.results-table"
  4. "[data-dojo-attach-point='resultsContainer']"

TODO (verify on e5-mother): open https://www.assessormelvinburgess.com/propertySearch
in Chromium DevTools, perform a real search, inspect the DOM to confirm the
correct selector.  Update RESULTS_SELECTOR once verified.
"""
from __future__ import annotations

import argparse
import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Playwright guard -- must be at module level so --dry-run still imports cleanly
# ---------------------------------------------------------------------------
_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Shared extraction -- import from parse_assessor_mhtml (canonical parser).
# We add a thin shim so the script is importable even when BeautifulSoup is
# not installed (the dry-run path never calls extract_lead).
# ---------------------------------------------------------------------------
_PARSE_SCRIPT = Path(__file__).parent.parent.parent.parent.parent / \
    "03_AUTOMATION_CORE/01_Scripts/parse_assessor_mhtml.py"

# Also try relative to workspace root
# Workspace root -- the phone (canonical) when present, else the install dir
# (e.g. on E5 the module lives at /home/ubuntu/everlight_assessor/ and writes
# alongside itself).
_PHONE_ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
_WORKSPACE = _PHONE_ROOT if _PHONE_ROOT.exists() else Path(__file__).resolve().parent
_PARSE_SCRIPT_ABS = _WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/parse_assessor_mhtml.py"

_extract_lead_fn = None

def _load_extract_lead():
    """Lazy-import extract_lead from parse_assessor_mhtml. Returns None if unavailable."""
    global _extract_lead_fn
    if _extract_lead_fn is not None:
        return _extract_lead_fn
    # Try sys.path injection
    scripts_dir = str(_WORKSPACE / "03_AUTOMATION_CORE/01_Scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        import parse_assessor_mhtml as _pam
        _extract_lead_fn = _pam.extract_lead
        return _extract_lead_fn
    except Exception as e:
        print(f"[assessor_harvester] WARNING: could not import parse_assessor_mhtml: {e}")
        print("[assessor_harvester] extract_lead will not be available; only dry-run mode works.")
        return None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ASSESSOR_URL = "https://www.assessormelvinburgess.com/propertySearch"

# Verified 2026-05-27 via live Playwright probe on E5-mother. The Melvin
# Burgess assessor site (Shelby County TN) renders search hits as a single
# DataTables-style <table> with columns: Parcel ID | Owner Name | Property
# Location | Link. Wait on a data row to ensure results actually populated.
RESULTS_SELECTOR_CANDIDATES = [
    "table tbody tr td",   # primary: a real result cell exists
    "table tbody tr",
    "table",
]
RESULTS_SELECTOR = RESULTS_SELECTOR_CANDIDATES[0]

# The page has multiple text inputs; the search box is the first input on the
# results page. The probe found 6 inputs; index 0 worked.
SEARCH_INPUT_SELECTOR = "input[type='search'], input[type='text']"

_LEADS_PHONE = _PHONE_ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"
_LEADS_LOCAL = Path(__file__).resolve().parent / "leads_db.json"
LEADS_DB_PATH = _LEADS_PHONE if _LEADS_PHONE.exists() else _LEADS_LOCAL
LOG_DIR = _WORKSPACE / "_logs" / "enrichment"
LOG_PATH = LOG_DIR / "assessor_harvester.jsonl"

PAGE_TIMEOUT_MS = 30_000   # 30 s for page load
RESULT_TIMEOUT_MS = 15_000  # 15 s for results to render after search submit


# ---------------------------------------------------------------------------
# Leads DB helpers
# ---------------------------------------------------------------------------

def load_leads() -> list[dict]:
    if not LEADS_DB_PATH.exists():
        print(f"[assessor_harvester] leads_db not found at {LEADS_DB_PATH}")
        return []
    return json.loads(LEADS_DB_PATH.read_text())


def save_leads(leads: list[dict]) -> None:
    LEADS_DB_PATH.write_text(json.dumps(leads, indent=2, default=str))


def get_address_for_lead(lead: dict) -> Optional[str]:
    """Return the best street address string to search the assessor with."""
    # property_address is the clean street-only form (from assessor); prefer it
    addr = (lead.get("property_address") or "").strip()
    if addr:
        return addr
    # Fallback: strip city/state suffix from the combined address field
    full = (lead.get("address") or "").strip()
    if full:
        # "1596 GABAY, MEMPHIS, TN" -> "1596 GABAY"
        return full.split(",")[0].strip()
    return None


def select_candidates(leads: list[dict], state: str, limit: int, resume: bool,
                       source_contains: str = "") -> list[dict]:
    """Return up to `limit` leads eligible for harvesting.

    source_contains: substring filter on the lead's source/origin field. Use
    "shelby" to restrict to the tax-delinquent Shelby list (best funnel yield);
    "" allows any source. Also auto-excludes FSBO/Craigslist-origin lead_ids
    (lead_id starting with "fsbo_") -- those carry post titles, not addresses.
    """
    SKIP_STAGES = {"assessor_done", "assessor_failed"}
    needle = source_contains.lower().strip()
    candidates = []
    for lead in leads:
        if lead.get("state", "").upper() != state.upper():
            continue
        lid = str(lead.get("lead_id", "")).lower()
        if lid.startswith("fsbo_"):
            continue  # Craigslist-origin: address field is a post title, not an address
        if needle:
            src = str(lead.get("source", "")).lower()
            if needle not in src:
                continue
        addr = get_address_for_lead(lead)
        if not addr:
            continue
        stage = (lead.get("enrichment_stage") or "").strip()
        if resume and stage in SKIP_STAGES:
            continue
        candidates.append(lead)
        if len(candidates) >= limit:
            break
    return candidates


# ---------------------------------------------------------------------------
# Ledger writer
# ---------------------------------------------------------------------------

def write_ledger(entry: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ---------------------------------------------------------------------------
# Browser extraction
# ---------------------------------------------------------------------------

def _try_result_selector(page) -> Optional[str]:
    """Try each candidate selector; return the first that finds an element, or None."""
    for sel in RESULTS_SELECTOR_CANDIDATES:
        try:
            el = page.query_selector(sel)
            if el:
                return sel
        except Exception:
            pass
    return None


_TR_RE = __import__("re").compile(r"<tr[^>]*>(.*?)</tr>", __import__("re").IGNORECASE | __import__("re").DOTALL)
_TD_RE = __import__("re").compile(r"<t[dh][^>]*>(.*?)</t[dh]>", __import__("re").IGNORECASE | __import__("re").DOTALL)
_TAG_RE = __import__("re").compile(r"<[^>]+>")


def _clean(s: str) -> str:
    """Strip HTML tags + collapse whitespace."""
    return " ".join(_TAG_RE.sub(" ", s or "").split()).strip()


def _norm_addr(s: str) -> str:
    """Loose normalization: uppercase, collapse whitespace, drop punctuation."""
    import re as _re
    return _re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper()).split() and \
           " ".join(_re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper()).split()) or ""


def extract_from_results_table(html: str, target_address: str) -> dict:
    """Parse the Melvin Burgess DataTables results page. Find the row whose
    'Property Location' best matches target_address. Returns:
      {"owner_name", "parcel_id", "property_location", "match_quality",
       "all_candidates"}
    match_quality is "exact" | "substring" | "first_row" | "no_results".
    """
    rows = []
    for tr_html in _TR_RE.findall(html):
        cells = [_clean(td) for td in _TD_RE.findall(tr_html)]
        # We want rows that look like data rows: 4+ cells, first is parcel id pattern
        if len(cells) >= 3 and cells[0] and cells[1] and cells[2] and \
           cells[0].lower() != "parcel id":
            rows.append({"parcel_id": cells[0], "owner_name": cells[1],
                          "property_location": cells[2]})
    if not rows:
        return {"owner_name": "", "parcel_id": "", "property_location": "",
                "match_quality": "no_results", "candidate_count": 0}
    tgt = _norm_addr(target_address)
    n = len(rows)
    # exact normalized match wins
    for r in rows:
        if _norm_addr(r["property_location"]) == tgt:
            return {**r, "match_quality": "exact", "candidate_count": n}
    # substring either direction
    for r in rows:
        loc = _norm_addr(r["property_location"])
        if tgt and (tgt in loc or loc in tgt):
            return {**r, "match_quality": "substring", "candidate_count": n}
    # fallback: first row (operator should review)
    return {**rows[0], "match_quality": "first_row", "candidate_count": n}


def harvest_one(page, address: str, delay_seconds: float) -> dict:
    """
    Navigate to the assessor search page, type address, submit, wait for
    results, return extracted lead dict.  Raises on hard failures.
    """

    # 'load' (default) waits for ALL resources; this heavy ArcGIS site routinely
    # blows past 30s on that. The probe proved 'domcontentloaded' renders enough
    # of the DOM to drive the search input within seconds.
    page.goto(ASSESSOR_URL, timeout=60_000, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)  # give widgets a moment to wire up

    # Wait for search input
    search_input = page.wait_for_selector(
        SEARCH_INPUT_SELECTOR, timeout=PAGE_TIMEOUT_MS
    )
    search_input.fill("")
    search_input.type(address, delay=80)
    search_input.press("Enter")

    # Wait for results container
    try:
        found_sel = None
        # Try each candidate with a short timeout; take first that fires
        for sel in RESULTS_SELECTOR_CANDIDATES:
            try:
                page.wait_for_selector(sel, timeout=RESULT_TIMEOUT_MS // len(RESULTS_SELECTOR_CANDIDATES))
                found_sel = sel
                break
            except Exception:
                continue
        if not found_sel:
            # One final attempt with primary
            page.wait_for_selector(RESULTS_SELECTOR, timeout=RESULT_TIMEOUT_MS)
            found_sel = RESULTS_SELECTOR
    except Exception as e:
        raise RuntimeError(f"Results container did not appear for '{address}': {e}")

    # Grab the full page HTML (results rendered into the DOM)
    html = page.content()

    # Rate-limit courtesy pause
    if delay_seconds > 0:
        time.sleep(delay_seconds)

    # Extract structured record from the live results table (verified shape:
    # Parcel ID | Owner Name | Property Location | Link). Match best row to
    # the target address; tolerate fuzzy results from the assessor's search.
    return extract_from_results_table(html, address)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    leads = load_leads()
    candidates = select_candidates(leads, args.state, args.limit, args.resume,
                                    source_contains=args.source_contains)

    if not candidates:
        print(f"[assessor_harvester] No eligible TN leads to process (limit={args.limit}, resume={args.resume}).")
        return 0

    if args.dry_run:
        print(f"[assessor_harvester] DRY-RUN -- would process {len(candidates)} lead(s):")
        for i, lead in enumerate(candidates, 1):
            addr = get_address_for_lead(lead)
            lid = lead.get("id") or lead.get("parcel_id") or lead.get("address", "")[:30]
            stage = lead.get("enrichment_stage") or "none"
            owner = lead.get("owner_name") or "(no owner)"
            print(f"  {i:>3}. [{stage}] {addr!r}  owner={owner!r}  id={lid!r}")
        print(f"[assessor_harvester] DRY-RUN complete. No browser opened, no writes made.")
        return 0

    # --- LIVE mode: requires Playwright ---
    if not _PLAYWRIGHT_AVAILABLE:
        print(
            "assessor_harvester requires Playwright + Chromium; install on E5:\n"
            "  pip install playwright && playwright install chromium\n"
            "Refusing to run on the phone proot."
        )
        return 2

    print(f"[assessor_harvester] Starting live harvest: {len(candidates)} leads, delay={args.delay_seconds}s")

    success_count = 0
    fail_count = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for lead in candidates:
            address = get_address_for_lead(lead)
            lead_id = str(lead.get("id") or lead.get("parcel_id") or address)
            ts = datetime.now(timezone.utc).isoformat()

            print(f"[assessor_harvester] Searching: {address!r}")
            try:
                extracted = harvest_one(page, address, args.delay_seconds)

                # Merge extracted fields into lead
                for k, v in extracted.items():
                    if v is not None and v != "":
                        lead[k] = v
                lead["enrichment_stage"] = "assessor_done"
                lead["enrichment_at"] = ts
                lead.pop("enrichment_error", None)

                write_ledger({
                    "ts": ts,
                    "status": "ok",
                    "address": address,
                    "lead_id": lead_id,
                    "owner_name": extracted.get("owner_name"),
                    "parcel_id": extracted.get("parcel_id"),
                })
                success_count += 1
                print(f"  -> OK  owner={extracted.get('owner_name','?')} parcel={extracted.get('parcel_id','?')}")

            except Exception as e:
                err_msg = str(e)
                lead["enrichment_stage"] = "assessor_failed"
                lead["enrichment_error"] = err_msg
                lead["enrichment_at"] = ts
                write_ledger({
                    "ts": ts,
                    "status": "error",
                    "address": address,
                    "lead_id": lead_id,
                    "error": err_msg,
                })
                fail_count += 1
                print(f"  -> FAIL {err_msg[:120]}")

        context.close()
        browser.close()

    # Write back leads_db
    save_leads(leads)

    print(f"[assessor_harvester] Done. success={success_count} fail={fail_count}")
    print(f"[assessor_harvester] Log: {LOG_PATH}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="E5 browser-driven assessor owner enrichment (Playwright)."
    )
    p.add_argument("--limit", type=int, default=25,
                   help="Max leads to process (default 25)")
    p.add_argument("--state", default="TN",
                   help="Filter leads by state (default TN)")
    p.add_argument("--delay-seconds", type=float, default=4.0,
                   help="Seconds to wait between requests (default 4)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print queue without opening browser")
    p.add_argument("--source-contains", default="shelby",
                   help="filter leads whose 'source' contains this substring (default: 'shelby' = tax-delinquent list; pass '' to allow any)")
    p.add_argument("--resume", action="store_true",
                   help="Skip leads already marked assessor_done or assessor_failed")
    return p


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(run(args))
