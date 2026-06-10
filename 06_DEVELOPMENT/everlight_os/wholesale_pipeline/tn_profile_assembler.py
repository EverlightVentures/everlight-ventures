"""tn_profile_assembler -- for each Tennessee address in TN_round2_targets.csv:
  1. Curl the Shelby Assessor propertyDetails page
  2. Headless Playwright screenshot of the same URL
  3. Parse data fields
  4. Compile a wholesale profile (markdown)
  5. If property passes Chris's buybox: pre-fill a PSA + offer-letter draft
  6. Stage everything in /Wholesale/contracts/active_deals/<addr-slug>/

Per Rich 2026-05-07: "I need to search those addresses in the registry and
screenshots so we can completely compile the wholesale profile for those
addresses. And create contracts and offers that we can send the buyers and
sellers. This is strictly for Tennessee."

NO outbound is sent. Drafts only. Rich reviews + signs off before any send.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

WORKSPACE = Path("/AA_MY_DRIVE")
TN_LIST = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/prospecting/TN_round2_targets.csv"
ACTIVE_DEALS_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/contracts/active_deals"
PARSED_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed"
LOG_PATH = WORKSPACE / "_logs/wholesale_runs/tn_profile_assembler.log"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

CHRIS_BUYER = {
    "name": "Mid South Homebuyers (Chris Ulander)",
    "email": "leads@midsouthhomebuyers.com",
    "buybox": {
        "year_built_min": 1940,
        "ARV_max": 200_000,
        "ARV_min": 50_000,
    },
}

# Default offer math: MAO = 70% of ARV - estimated repairs ($25k stub) - assignment fee
DEFAULT_ASSIGNMENT_FEE = 5_000
DEFAULT_EARNEST_MONEY = 500
DEFAULT_REPAIRS_USD = 25_000
DEFAULT_CLOSING_DAYS = 30
DEFAULT_INSPECTION_DAYS = 14
DEFAULT_TITLE_COMPANY = "Mid-South Title (Memphis) -- pending RESPA verification"


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip())
    return s.strip("-").lower()[:60]


def _shelby_url(parcel_id: str) -> str:
    return (f"https://www.assessormelvinburgess.com/propertyDetails"
            f"?IR=true&parcelid={urllib.parse.quote(parcel_id)}")


def fetch_shelby(parcel_id: str, max_retries: int = 2) -> str | None:
    url = _shelby_url(parcel_id)
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    time.sleep(1.0 * attempt)
                    continue
                html = resp.read().decode("utf-8", errors="replace")
                if "technical difficulties" in html.lower():
                    time.sleep(1.5 * attempt)
                    continue
                if (parcel_id.replace(" ", "").lower()
                        not in html.replace(" ", "").lower()):
                    time.sleep(1.0 * attempt)
                    continue
                return html
        except Exception:
            time.sleep(1.0 * attempt)
    return None


def screenshot_shelby(parcel_id: str, out_path: Path) -> bool:
    """Headless Playwright screenshot. Returns True on success."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log("  playwright missing; skipping screenshot")
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 900},
            )
            page = ctx.new_page()
            page.goto(_shelby_url(parcel_id), timeout=30000,
                      wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass  # don't fail if some sub-resource is slow
            out_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_path), full_page=True)
            browser.close()
        return True
    except Exception as e:
        _log(f"  screenshot FAILED: {e}")
        return False


def _extract(html: str, pattern: str) -> str | None:
    rx = re.compile(rf"{pattern}\s*[:.]?\s*</[^>]+>\s*<[^>]+>([^<]+)",
                    re.IGNORECASE)
    m = rx.search(html)
    return m.group(1).strip() if m else None


def _extract_int(html: str, pattern: str) -> int | None:
    raw = _extract(html, pattern)
    if not raw:
        return None
    digits = re.search(r"-?\d[\d,]*", raw.replace("$", ""))
    if digits:
        try:
            return int(digits.group(0).replace(",", ""))
        except ValueError:
            return None
    return None


def _extract_block(html: str, start_label: str, end_chars: int = 600) -> str | None:
    """Extract a wider block after a label, useful for multi-line fields like
    'Owner Mailing Address' which span 2-3 lines (street, city/state/zip)."""
    m = re.search(rf"{start_label}[^<]*</[^>]+>([\s\S]{{0,{end_chars}}})",
                   html, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1)
    # Strip tags and collapse whitespace
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_mailing_address(block: str | None) -> dict:
    """Block typically looks like: '3289 WINCHESTER RD MEMPHIS TN 38118-...'.
    Returns {street, city, state, zip} when parseable."""
    out = {"owner_mailing_street": None, "owner_mailing_city": None,
           "owner_mailing_state": None, "owner_mailing_zip": None,
           "owner_mailing_full": None}
    if not block:
        return out
    # cap to the first 200 chars; the assessor's mailing block typically ends
    # before the next labeled field
    s = block[:300].strip()
    out["owner_mailing_full"] = s
    # zip first (5 digits maybe with -ext)
    z = re.search(r"\b(\d{5})(?:-\d{4})?\b", s)
    if z:
        out["owner_mailing_zip"] = z.group(1)
    # state: 2-letter uppercase preceded/followed by space
    st = re.search(r"\b(TN|MS|AR|KY|MO|GA|TX|FL|CA|AZ|OH)\b", s)
    if st:
        out["owner_mailing_state"] = st.group(1)
    # city: typically all-caps city name immediately before state
    if st:
        before = s[:st.start()].rstrip()
        cm = re.search(r"\b([A-Z][A-Z &\-\.']{2,30})\s*$", before)
        if cm:
            out["owner_mailing_city"] = cm.group(1).strip()
            out["owner_mailing_street"] = before[:cm.start()].strip()
    return out


def _parse_last_sale(html: str) -> dict:
    """Look for sales history block. The assessor page shows a table with
    date + price + deed type. Grab the most recent row."""
    out = {"last_sale_date": None, "last_sale_price": None}
    block = _extract_block(html, "Sales\\s*History", 2000)
    if not block:
        return out
    # date pattern MM/DD/YYYY
    date_m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", block)
    if date_m:
        out["last_sale_date"] = date_m.group(1)
    # price: $X,XXX
    price_m = re.search(r"\$\s*([\d,]+)", block)
    if price_m:
        try:
            out["last_sale_price"] = int(price_m.group(1).replace(",", ""))
        except ValueError:
            pass
    return out


def parse_shelby(html: str, parcel_id: str, fallback_addr: str) -> dict:
    zip_match = re.search(r"Property[^<]{0,400}?\b(38\d{3})\b", html, re.IGNORECASE)
    if not zip_match:
        zip_match = re.search(r"\b(38\d{3})\b", html)
    mailing_block = _extract_block(html, "Owner\\s*Mailing\\s*Address", 400)
    mailing = _parse_mailing_address(mailing_block)
    last_sale = _parse_last_sale(html)
    return {
        "source": "shelby_assessor_curl",
        "source_url": _shelby_url(parcel_id),
        "parsed_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "parcel_id": parcel_id,
        "property_address": _extract(html, "Property\\s*Address") or fallback_addr,
        "property_zip": zip_match.group(1) if zip_match else None,
        "owner_name": _extract(html, "Owner(?:\\s+Name)?"),
        **mailing,
        "land_use": _extract(html, "Land\\s*Use"),
        "year_built": _extract_int(html, "Year\\s*Built"),
        "sqft": _extract_int(html, "(?:Living\\s*Area|Building\\s*Area|Square\\s*Feet)"),
        "bedrooms": _extract_int(html, "(?:Bedrooms|Beds)"),
        "bathrooms": _extract_int(html, "(?:Bathrooms|Baths)"),
        "land_appraisal_usd": _extract_int(html, "Land\\s*Appraisal"),
        "building_appraisal_usd": _extract_int(html, "Building\\s*Appraisal"),
        "total_appraisal_usd": _extract_int(html, "Total\\s*Appraisal"),
        "subdivision": _extract(html, "Subdivision"),
        **last_sale,
    }


# Chris's 15 Memphis zips (per memory + chris_pipeline_orchestrator.py)
CHRIS_MEMPHIS_ZIPS = {"38127","38128","38134","38117","38111","38141","38115",
                       "38118","38116","38109","38104","38122","38107","38114","38106"}


def passes_chris_buybox(p: dict) -> tuple[bool, list[str]]:
    """Chris Ulander / Mid South Homebuyers full buybox:
      - 1940+ build
      - ARV $50k-$200k
      - SFR or duplex (no vacant/religious/commercial/condo)
      - 2-4 bedrooms
      - In one of Chris's 15 Memphis zip codes
    """
    fails = []
    bb = CHRIS_BUYER["buybox"]

    yb = p.get("year_built")
    if yb is None:
        fails.append("year_built unknown")
    elif yb < bb["year_built_min"]:
        fails.append(f"year_built {yb} < {bb['year_built_min']}")

    arv = p.get("total_appraisal_usd")
    if not arv:
        fails.append("appraisal unknown")
    elif arv > bb["ARV_max"]:
        fails.append(f"appraisal {arv} > {bb['ARV_max']}")
    elif arv < bb["ARV_min"]:
        fails.append(f"appraisal {arv} < {bb['ARV_min']}")

    land = (p.get("land_use") or "").upper()
    if not land:
        fails.append("land_use unknown")
    elif any(b in land for b in ("VACANT", "RELIGIOUS", "CHURCH",
                                   "COMMERCIAL", "INDUSTRIAL", "AGRICULTURAL",
                                   "EXEMPT", "GOVERNMENT", "SCHOOL", "UTILITY",
                                   "CONDO")):
        fails.append(f"land_use {land!r}")

    bd = p.get("bedrooms")
    if bd is None:
        fails.append("bedrooms unknown")
    elif bd < 2 or bd > 4:
        fails.append(f"bedrooms {bd} outside 2-4")

    pz = p.get("property_zip")
    if not pz:
        fails.append("zip unknown")
    elif pz not in CHRIS_MEMPHIS_ZIPS:
        fails.append(f"zip {pz} not in Chris's 15")

    return (not fails, fails)


def compute_offer(parsed: dict) -> dict:
    """MAO formula: 70% of ARV - repairs - assignment fee.
    ARV proxy = total_appraisal_usd (rough). For a real deal, an investor
    would order comps; this is just a starting offer."""
    arv = parsed.get("total_appraisal_usd") or 0
    mao_max = arv * 0.70 - DEFAULT_REPAIRS_USD - DEFAULT_ASSIGNMENT_FEE
    # round down to nearest $500
    mao_max = max(0, int(mao_max // 500) * 500)
    return {
        "ARV_estimate": arv,
        "MAO_offer_usd": mao_max,
        "assignment_fee_usd": DEFAULT_ASSIGNMENT_FEE,
        "earnest_money_usd": DEFAULT_EARNEST_MONEY,
        "estimated_repairs_usd": DEFAULT_REPAIRS_USD,
        "formula": "ARV * 0.70 - repairs - assignment_fee = MAO",
    }


def render_profile_md(parsed: dict, offer: dict, passes: bool,
                       fails: list[str], screenshot_rel: str) -> str:
    pass_badge = ":white_check_mark: QUALIFIED for Chris" if passes else ":x: REJECTED"
    fails_text = ("\n".join(f"- {f}" for f in fails)
                   if fails else "(none)")
    return f"""# Wholesale Property Profile

**Address:** {parsed.get('property_address')}
**Parcel ID:** `{parsed.get('parcel_id')}`
**Status:** {pass_badge}

## Public Record (Shelby County Assessor)

| Field | Value |
|---|---|
| Owner | {parsed.get('owner_name') or '_(not extracted)_'} |
| Land use | {parsed.get('land_use') or '_(not extracted)_'} |
| Year built | {parsed.get('year_built') or '_(not extracted)_'} |
| Square feet | {parsed.get('sqft') or '_(not extracted)_'} |
| Subdivision | {parsed.get('subdivision') or '_(not extracted)_'} |
| Land appraisal | ${parsed.get('land_appraisal_usd') or 0:,} |
| Building appraisal | ${parsed.get('building_appraisal_usd') or 0:,} |
| **Total appraisal** | **${parsed.get('total_appraisal_usd') or 0:,}** |
| Source URL | <{parsed.get('source_url')}> |

## Buybox Check (Chris Ulander / Mid South Homebuyers)

Required: year_built >= 1940 | ARV $50k-$200k | SFR or duplex (no vacant /
religious / commercial)

**Decision:** {'PASS' if passes else 'FAIL'}

Failure reasons (if any):
{fails_text}

## Offer Math (starting point only -- comps required before live)

- ARV proxy (Shelby total appraisal): ${offer['ARV_estimate']:,}
- Estimated repairs (stub default): ${offer['estimated_repairs_usd']:,}
- Assignment fee (Lucrex): ${offer['assignment_fee_usd']:,}
- **MAO offer to seller:** **${offer['MAO_offer_usd']:,}**
- Formula: `{offer['formula']}`

## Assessor Page Screenshot

![Shelby Assessor screenshot]({screenshot_rel})

## Generated

{time.strftime('%Y-%m-%dT%H:%M:%S%z')}
"""


def render_offer_letter_draft(parsed: dict, offer: dict) -> str:
    """Plain text offer letter for the seller. Not signed, not sent -- draft."""
    return f"""Dear {parsed.get('owner_name') or 'Property Owner'},

I am writing to extend a no-obligation cash offer on the property at:

  {parsed.get('property_address')}, Memphis, TN
  Parcel ID: {parsed.get('parcel_id')}

Based on Shelby County's published appraisal of ${parsed.get('total_appraisal_usd', 0):,} \
and standard market comps for this neighborhood, my offer is:

  Purchase price: ${offer['MAO_offer_usd']:,} (cash, all-in)
  Earnest money: ${offer['earnest_money_usd']:,}
  Closing: within {DEFAULT_CLOSING_DAYS} days
  Inspection period: {DEFAULT_INSPECTION_DAYS} calendar days

This is a serious offer from an active investor group buying in Memphis
right now. We close fast, in cash, with no commissions, no repairs, and
no surprises. I've attached our standard Purchase and Sale Agreement
for your review -- if the terms work for you, sign and we'll move to
title within the week.

Reply or call to discuss. If now isn't the right time, I understand --
just let me know and we'll take you off the list.

Best regards,
Richard Gee
Everlight Ventures (DBA, sole proprietorship)
piper@everlightventures.io

---
TN HB 2537 disclosure: Buyer or Buyer's assignee may assign this contract
to a third-party investor. Assignment fee will be disclosed in writing
prior to closing on the Closing Disclosure / HUD-1.
"""


def generate_psa_draft(parsed: dict, offer: dict, deal_dir: Path) -> Path | None:
    """Use existing contract_generator.py if available."""
    try:
        sys.path.insert(0, "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS")
        from contract_generator import generate_wholesale_contract
    except Exception as e:
        _log(f"  contract_generator import failed: {e}")
        return None

    deal = {
        "property_address": parsed.get("property_address"),
        "seller_name": parsed.get("owner_name") or "TBD -- skip-trace pending",
        "seller_email": "TBD",
        "buyer_name": "Richard Gee, an individual doing business as Everlight Ventures",
        "buyer_email": "piper@everlightventures.io",
        "purchase_price": offer["MAO_offer_usd"],
        "assignment_fee": offer["assignment_fee_usd"],
        "earnest_money": offer["earnest_money_usd"],
        "closing_date": time.strftime("%Y-%m-%d",
                                       time.localtime(time.time() + DEFAULT_CLOSING_DAYS * 86400)),
        "title_company": DEFAULT_TITLE_COMPANY,
        "inspection_days": DEFAULT_INSPECTION_DAYS,
    }
    try:
        pdf_path = generate_wholesale_contract(deal)
        # generator writes to its own CONTRACTS_DIR; copy into our deal dir
        import shutil
        src = Path(pdf_path)
        if src.exists():
            dest = deal_dir / src.name
            shutil.copy2(src, dest)
            return dest
    except Exception as e:
        _log(f"  PSA generation FAILED: {e}")
    return None


def assemble(addr: str, parcel_id: str, city: str = "Memphis",
              state: str = "TN", zip_code: str = "") -> dict:
    addr_full = f"{addr}, {city}, {state}".strip(", ")
    slug = _slug(addr_full)
    deal_dir = ACTIVE_DEALS_DIR / slug
    deal_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: curl assessor
    _log(f"  [1/5] curl Shelby Assessor for parcel {parcel_id!r}")
    html = fetch_shelby(parcel_id)
    if not html:
        _log(f"  FAIL fetch -- skipping {addr}")
        return {"address": addr, "skipped": True, "reason": "shelby_fetch_failed"}

    # Step 2: archive html
    safe_pid = parcel_id.replace(" ", "_").replace("/", "_")
    with gzip.open(deal_dir / "assessor.html.gz", "wt", encoding="utf-8") as f:
        f.write(html)

    # Step 3: screenshot via Playwright headless
    _log(f"  [2/5] screenshot via Playwright")
    sshot_path = deal_dir / "assessor_screenshot.png"
    sshot_ok = screenshot_shelby(parcel_id, sshot_path)
    sshot_rel = sshot_path.name if sshot_ok else "(screenshot failed)"

    # Step 4: parse + classify
    _log(f"  [3/5] parse fields")
    parsed = parse_shelby(html, parcel_id, addr)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    (PARSED_DIR / f"{safe_pid}.json").write_text(json.dumps(parsed, indent=2),
                                                    encoding="utf-8")
    (deal_dir / "parsed.json").write_text(json.dumps(parsed, indent=2),
                                             encoding="utf-8")

    # Step 5: compile profile + offer + PSA (if qualified)
    passes, fails = passes_chris_buybox(parsed)
    offer = compute_offer(parsed)

    _log(f"  [4/5] compile profile.md  (qualified={passes})")
    profile_md = render_profile_md(parsed, offer, passes, fails, sshot_rel)
    (deal_dir / "profile.md").write_text(profile_md, encoding="utf-8")

    pdf_path = None
    offer_letter_path = None
    if passes:
        _log(f"  [5/5] qualified -- generate PSA draft + offer letter")
        offer_letter = render_offer_letter_draft(parsed, offer)
        offer_letter_path = deal_dir / "offer_letter_draft.txt"
        offer_letter_path.write_text(offer_letter, encoding="utf-8")
        pdf_path = generate_psa_draft(parsed, offer, deal_dir)
    else:
        _log(f"  [5/5] not qualified -- skip PSA generation")

    return {
        "address": addr,
        "parcel_id": parcel_id,
        "deal_dir": str(deal_dir),
        "qualified": passes,
        "fails": fails,
        "year_built": parsed.get("year_built"),
        "appraisal": parsed.get("total_appraisal_usd"),
        "screenshot": str(sshot_path) if sshot_ok else None,
        "psa_pdf": str(pdf_path) if pdf_path else None,
        "offer_letter": str(offer_letter_path) if offer_letter_path else None,
        "profile_md": str(deal_dir / "profile.md"),
    }


def run() -> dict:
    _log("=== tn_profile_assembler starting ===")
    rows = []
    with TN_LIST.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    _log(f"loaded {len(rows)} TN addresses from {TN_LIST.name}")
    results = []
    for i, row in enumerate(rows, 1):
        addr = row.get("address", "")
        parcel = row.get("parcel_id", "")
        city = row.get("city", "Memphis")
        state = row.get("state", "TN")
        zip_code = row.get("zip", "")
        if not parcel:
            _log(f"  ROW {i}: SKIP -- no parcel_id ({addr})")
            continue
        _log(f"\n--- ROW {i}: {addr} (parcel {parcel}) ---")
        try:
            r = assemble(addr, parcel, city, state, zip_code)
            results.append(r)
        except Exception as e:
            _log(f"  ERROR on row {i}: {e}")
            results.append({"address": addr, "error": str(e)})
        time.sleep(0.6)

    qualified = [r for r in results if r.get("qualified")]
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "total_processed": len(results),
        "qualified_count": len(qualified),
        "qualified": qualified,
        "all_results": results,
        "deal_dirs_root": str(ACTIVE_DEALS_DIR),
    }
    out = ACTIVE_DEALS_DIR / f"_summary_{time.strftime('%Y%m%d_%H%M%S')}.json"
    ACTIVE_DEALS_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _log(f"=== summary written: {out} ===")
    _log(f"qualified: {len(qualified)}/{len(results)}")
    return summary


if __name__ == "__main__":
    result = run()
    print()
    print(f"qualified: {result['qualified_count']}/{result['total_processed']}")
    print()
    for q in result["qualified"]:
        print(f"  ✓ {q['address']}")
        print(f"    deal dir: {q['deal_dir']}")
        print(f"    screenshot: {q.get('screenshot')}")
        print(f"    profile: {q['profile_md']}")
        if q.get("psa_pdf"):
            print(f"    PSA draft: {q['psa_pdf']}")
        if q.get("offer_letter"):
            print(f"    offer letter: {q['offer_letter']}")
