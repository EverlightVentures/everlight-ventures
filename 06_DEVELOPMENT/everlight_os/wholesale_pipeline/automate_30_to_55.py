"""automate_30_to_55 -- replace Rich's manual Shelby Assessor lookup with a
curl+parse loop. He did rows 1-29 manually; this picks up at row 30 and
extends the parsed/ directory with the rest of CHRIS_BATCH_001_DRAFT.

Pipeline:
  1. Read leads from CHRIS_BATCH_001_DRAFT.json
  2. For each lead in slice [start:end] that has a parcel_id:
     a. curl Shelby Assessor propertyDetails page (UA-spoofed)
     b. save HTML to Memphis Property Downloads/raw_html/
     c. parse year_built, sqft, owner, addr, land_use, appraisal, etc.
     d. write parsed/<parcel_id>.json (matches existing schema)
  3. Apply Chris buy box: year_built >= 1940, ARV $50k-$200k, SFR.
  4. Output a Chris seller-list JSON ready for review.

Per Rich's screenshot/secret doctrine: HTML files are NOT secrets but ARE
intermediates. We keep them only for audit and gzip-archive after parse.

No real outbound is sent. This is read-only enrichment.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

WORKSPACE = Path("/AA_MY_DRIVE")
BATCH_PATH = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/buyers/CHRIS_BATCH_001_DRAFT.json"
PARSED_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed"
RAW_HTML_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/raw_html"
OUTPUT_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/buyers"
LOG_PATH = WORKSPACE / "_logs/wholesale_runs/automate_30_to_55.log"

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

CHRIS_BUY_BOX = {
    "year_built_min": 1940,
    "ARV_max_usd": 200_000,
    "ARV_min_usd": 50_000,
    "memphis_zips_acceptable": True,  # all current leads are Memphis
}


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def fetch_assessor_html(parcel_id: str, max_retries: int = 3) -> str | None:
    """Curl the Shelby Assessor propertyDetails page. Detects the "technical
    difficulties" error template (HTTP 200 with no real data) and retries
    with backoff. Returns HTML or None.
    """
    encoded = urllib.parse.quote(parcel_id)
    url = f"https://www.assessormelvinburgess.com/propertyDetails?IR=true&parcelid={encoded}"

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                if resp.status != 200:
                    _log(f"  HTTP {resp.status} for {parcel_id} (attempt {attempt})")
                    time.sleep(1.5 * attempt)
                    continue
                html = data.decode("utf-8", errors="replace")

                # Detect Shelby Assessor's transient error template
                if ("technical difficulties" in html.lower()
                        or "please try again later" in html.lower()):
                    _log(f"  technical-difficulties page for {parcel_id} "
                         f"(attempt {attempt}), backing off")
                    time.sleep(2.0 * attempt)
                    continue

                if len(html) < 5000:
                    _log(f"  short response ({len(html)}b) for {parcel_id}")
                    return None

                # Quick sanity: real pages have parcel_id echoed back somewhere
                if parcel_id.replace(" ", "").lower() not in html.replace(" ", "").lower():
                    _log(f"  parcel echo missing for {parcel_id} (attempt {attempt})")
                    time.sleep(1.5 * attempt)
                    continue

                return html
        except Exception as e:
            _log(f"  fetch error for {parcel_id} (attempt {attempt}): {e}")
            time.sleep(1.5 * attempt)

    _log(f"  GIVING UP on {parcel_id} after {max_retries} attempts")
    return None


def _extract(html: str, label_pattern: str) -> str | None:
    """Find a labeled value in the HTML. Returns first match's text content."""
    rx = re.compile(
        rf"{label_pattern}\s*[:.]?\s*</[^>]+>\s*<[^>]+>([^<]+)",
        re.IGNORECASE
    )
    m = rx.search(html)
    if m:
        return m.group(1).strip()
    return None


def _extract_int(html: str, label_pattern: str) -> int | None:
    raw = _extract(html, label_pattern)
    if not raw:
        return None
    digits = re.search(r"-?\d[\d,]*", raw.replace("$", ""))
    if digits:
        try:
            return int(digits.group(0).replace(",", ""))
        except ValueError:
            return None
    return None


def parse_assessor_html(html: str, parcel_id: str, source_address: str) -> dict:
    """Extract structured property data. Best-effort; returns whatever we find."""
    out = {
        "source": "shelby_assessor_curl",
        "source_url": (f"https://www.assessormelvinburgess.com/propertyDetails"
                        f"?IR=true&parcelid={urllib.parse.quote(parcel_id)}"),
        "parsed_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "parcel_id": parcel_id,
        "property_address": _extract(html, "Property\\s*Address") or source_address,
        "owner_name": _extract(html, "Owner(?:\\s+Name)?"),
        "land_use": _extract(html, "Land\\s*Use"),
        "year_built": _extract_int(html, "Year\\s*Built"),
        "sqft": _extract_int(html, "(?:Living\\s*Area|Building\\s*Area|Square\\s*Feet)"),
        "bedrooms": _extract_int(html, "(?:Bedrooms|Beds)"),
        "bathrooms": _extract_int(html, "(?:Bathrooms|Baths)"),
        "land_sqft": _extract_int(html, "Land\\s*(?:Sq\\.?\\s*Ft|Square)"),
        "land_appraisal_usd": _extract_int(html, "Land\\s*Appraisal"),
        "building_appraisal_usd": _extract_int(html, "Building\\s*Appraisal"),
        "total_appraisal_usd": _extract_int(html, "Total\\s*Appraisal"),
        "total_assessment_usd": _extract_int(html, "Total\\s*Assessment"),
        "property_class": _extract(html, "Property\\s*Class"),
        "subdivision": _extract(html, "Subdivision"),
    }
    return out


def passes_chris_buybox(parsed: dict) -> tuple[bool, list[str]]:
    """Apply Chris's filter. Tightened 2026-05-07 after first run produced
    false positives (church + missing-data row).

    Returns (passed, list of reasons if failed). Missing data is treated as
    a fail, not a pass -- Chris needs known specs to consider a deal.
    """
    fails: list[str] = []

    # Year built must be present AND >= 1940
    yb = parsed.get("year_built")
    if yb is None:
        fails.append("year_built unknown (parser found nothing)")
    elif yb < CHRIS_BUY_BOX["year_built_min"]:
        fails.append(f"year_built {yb} < {CHRIS_BUY_BOX['year_built_min']}")

    # Total appraisal must be present AND in $50k-$200k
    arv = parsed.get("total_appraisal_usd")
    if not arv:
        fails.append("total_appraisal unknown")
    elif arv > CHRIS_BUY_BOX["ARV_max_usd"]:
        fails.append(f"appraisal {arv} > {CHRIS_BUY_BOX['ARV_max_usd']}")
    elif arv < CHRIS_BUY_BOX["ARV_min_usd"]:
        fails.append(f"appraisal {arv} < {CHRIS_BUY_BOX['ARV_min_usd']}")

    # Land use must be residential (single-family, duplex acceptable; no
    # vacant, religious, commercial, industrial, agricultural)
    land_use = (parsed.get("land_use") or "").upper()
    if not land_use:
        fails.append("land_use unknown")
    else:
        bad_uses = ("VACANT", "RELIGIOUS", "CHURCH", "COMMERCIAL",
                    "INDUSTRIAL", "AGRICULTURAL", "EXEMPT", "GOVERNMENT",
                    "SCHOOL", "UTILITY")
        if any(b in land_use for b in bad_uses):
            fails.append(f"land_use disqualifies ({land_use!r})")

    return (len(fails) == 0, fails)


def archive_html(html: str, parcel_id: str) -> Path:
    """Gzip-archive the raw HTML for audit; saves storage."""
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    safe = parcel_id.replace(" ", "_").replace("/", "_")
    path = RAW_HTML_DIR / f"{safe}.html.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(html)
    return path


def run(start: int = 30, end: int = 55) -> dict:
    """Process leads [start..end] (1-indexed inclusive). Returns summary dict."""
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    batch = json.loads(BATCH_PATH.read_text(encoding="utf-8"))
    leads = batch["leads"]
    slice_start = start - 1
    slice_end = end
    target = leads[slice_start:slice_end]

    _log(f"=== automate_30_to_55: processing rows {start}-{end} of "
         f"{len(leads)} leads in CHRIS_BATCH_001_DRAFT ===")

    seller_list_pass: list[dict] = []
    seller_list_fail: list[dict] = []
    skipped_no_parcel: list[dict] = []

    for offset, lead in enumerate(target):
        row_num = start + offset
        addr = lead.get("address", "")
        parcel = lead.get("parcel_id")
        if not parcel:
            _log(f"  row {row_num}: SKIP (no parcel_id) -- {addr}")
            skipped_no_parcel.append({"row": row_num, "address": addr,
                                       "lead": lead})
            continue
        _log(f"  row {row_num}: fetching parcel={parcel!r} ({addr})")
        html = fetch_assessor_html(parcel)
        if not html:
            seller_list_fail.append({"row": row_num, "parcel_id": parcel,
                                      "address": addr, "reason": "fetch_failed"})
            continue

        archive_path = archive_html(html, parcel)
        parsed = parse_assessor_html(html, parcel, addr)

        # write parsed JSON next to the others
        safe_pid = parcel.replace(" ", "_").replace("/", "_")
        parsed_path = PARSED_DIR / f"{safe_pid}.json"
        parsed_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

        passes, fails = passes_chris_buybox(parsed)
        record = {
            "row": row_num,
            "parcel_id": parcel,
            "address": parsed.get("property_address", addr),
            "owner_name": parsed.get("owner_name"),
            "year_built": parsed.get("year_built"),
            "sqft": parsed.get("sqft"),
            "land_use": parsed.get("land_use"),
            "total_appraisal_usd": parsed.get("total_appraisal_usd"),
            "parsed_path": str(parsed_path),
            "raw_html_path": str(archive_path),
        }
        if passes:
            seller_list_pass.append(record)
            _log(f"    PASS chris buybox -- {parsed.get('property_address')}")
        else:
            record["fails"] = fails
            seller_list_fail.append(record)
            _log(f"    FAIL chris buybox: {', '.join(fails)}")

        time.sleep(0.6)  # be polite to the assessor

    # write the seller list output
    output_path = OUTPUT_DIR / f"chris_seller_list_rows_{start}_to_{end}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "buyer": "Mid South Homebuyers / Chris Ulander",
        "source_batch": "CHRIS_BATCH_001_DRAFT.json",
        "rows_processed": f"{start}..{end}",
        "buybox": CHRIS_BUY_BOX,
        "counts": {
            "passed": len(seller_list_pass),
            "failed_buybox": len(seller_list_fail),
            "skipped_no_parcel": len(skipped_no_parcel),
        },
        "passed": seller_list_pass,
        "failed_buybox": seller_list_fail,
        "skipped_no_parcel": skipped_no_parcel,
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _log(f"=== output written: {output_path} ===")
    _log(f"counts: {summary['counts']}")
    return summary


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    end = int(sys.argv[2]) if len(sys.argv) > 2 else 55
    result = run(start, end)
    print()
    print(json.dumps(result["counts"], indent=2))
    print(f"output: {result.get('output_path', '?')}")
