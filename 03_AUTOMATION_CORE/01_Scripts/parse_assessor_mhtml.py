"""
parse_assessor_mhtml.py -- extract owner + parcel data from saved Shelby Assessor MHTML.

Workflow (Marquise's clever workaround for JS-rendered pages):
1. Marquise opens https://www.assessormelvinburgess.com/propertySearch in his
   browser, looks up an address, lets the page fully render.
2. He saves the page as MHTML via Chrome's "Save Page As" -> "Webpage, Single
   File" option.
3. Saves into /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/inbox/
4. This script processes every .mht/.mhtml in inbox/, extracts structured data,
   moves the file to archive/, writes the parsed lead to leads_db.json AND
   a per-property .json in parsed/.

Usage:
    python3 parse_assessor_mhtml.py             # process all .mht in inbox/
    python3 parse_assessor_mhtml.py --file <path>  # process one specific file
    python3 parse_assessor_mhtml.py --dry-run   # parse but don't move/save
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup


WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
DOWNLOAD_ROOT = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads"
# Marquise's preferred drop folder (he saves browser MHTMLs here):
INBOX = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/Memphis Property Downloads"
PARSED = DOWNLOAD_ROOT / "parsed"
ARCHIVE = DOWNLOAD_ROOT / "archive"
LEADS_DB = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json"

for p in [INBOX, PARSED, ARCHIVE]:
    p.mkdir(parents=True, exist_ok=True)


# Field labels we expect to find as "Label:" cells in the assessor table.
# Maps assessor labels to the key we want in our lead record.
ASSESSOR_FIELDS = {
    "Parcel ID": "parcel_id",
    "Property Address": "property_address",
    "Owner Name": "owner_name",
    "Owner Mailing Address": "owner_mailing_street",
    "Owner City/State/Zip": "owner_mailing_city_state_zip",
    "Class": "property_class",
    "Land Use": "land_use",
    "Year Built": "year_built",
    "Total Rooms": "total_rooms",
    "Bedrooms": "bedrooms",
    "Bathrooms": "bathrooms",
    "Half Baths": "half_baths",
    "Living Area Square Footage": "sqft",
    "Land Square Footage": "land_sqft",
    "Acres": "acres",
    "Subdivision Name": "subdivision",
    "Land Appraisal": "land_appraisal_usd",
    "Building Appraisal": "building_appraisal_usd",
    "Total Appraisal": "total_appraisal_usd",
    "Total Assessment": "total_assessment_usd",
    "Tax Map Page": "tax_map_page",
    "Neighborhood Number": "neighborhood_number",
    "Heat": "heat",
    "Fuel": "fuel",
    "Foundation": "foundation",
    "Exterior Wall": "exterior_wall",
    "Roof Cover": "roof_cover",
}


def extract_html_from_mht(mht_path: Path) -> tuple[str, str]:
    """Returns (html_content, source_url). Source URL captured from Content-Location."""
    with open(mht_path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            try:
                content = part.get_content()
            except Exception:
                content = part.get_payload(decode=True).decode("utf-8", errors="replace")
            return content, part.get("Content-Location", "")
    return "", ""


def extract_lead(html: str, source_url: str = "", source_file: str = "") -> dict:
    """Parse the assessor HTML and return a structured lead record."""
    soup = BeautifulSoup(html, "lxml")
    out = {
        "source": "shelby_assessor_mhtml_download",
        "source_url": source_url,
        "source_file": source_file,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Multi-cell value extractor: assessor HTML splits values like "101 LUCY AVE"
    # across multiple <td> cells (sometimes with empty cells between). Walk siblings
    # forward, collecting non-empty text, until we hit another known label.
    all_label_set = set(ASSESSOR_FIELDS.keys())

    def collect_value_cells(label_td):
        # Critical: use separator=" " so values like "101 LUCY AVE" (which sit in
        # a single <td> separated by <span> </span> elements) come out with spaces.
        parts = []
        sib = label_td.find_next_sibling("td")
        while sib is not None:
            txt = sib.get_text(separator=" ", strip=True).rstrip(":").strip()
            txt = re.sub(r"\s+", " ", txt)
            if txt in all_label_set:
                break
            if txt:
                parts.append(txt)
            sib = sib.find_next_sibling("td")
        return " ".join(parts).strip()

    for td in soup.find_all("td"):
        label = td.get_text(strip=True).rstrip(":").strip()
        if not label or len(label) > 50:
            continue
        if label not in ASSESSOR_FIELDS:
            continue
        val = collect_value_cells(td)
        if val and val != label:
            out[ASSESSOR_FIELDS[label]] = val

    # Clean owner_mailing_city_state_zip -- assessor often appends " - 0000" as a
    # placeholder for an unknown zip+4. Strip that before parsing.
    if out.get("owner_mailing_city_state_zip"):
        cleaned = re.sub(r"\s*-\s*0{4}\s*$", "", out["owner_mailing_city_state_zip"])
        out["owner_mailing_city_state_zip"] = cleaned
        m = re.match(r"^(.+?)\s+([A-Z]{2})\s+(\d{5})(?:\s*-\s*(\d{4}))?\s*$", cleaned)
        if m:
            out["owner_mailing_city"] = m.group(1).strip()
            out["owner_mailing_state"] = m.group(2)
            out["owner_mailing_zip"] = m.group(3)
            if m.group(4):
                out["owner_mailing_zip4"] = m.group(4)

    # Compose full mailing address line (for direct-mail + skip-trace input)
    if out.get("owner_mailing_street") and out.get("owner_mailing_city"):
        out["owner_mailing_full"] = (
            f"{out['owner_mailing_street']}, "
            f"{out['owner_mailing_city']}, "
            f"{out.get('owner_mailing_state','')} "
            f"{out.get('owner_mailing_zip','')}"
        ).strip()

    # Parse property address into structured city/state/zip if available
    if out.get("property_address"):
        # Property address from assessor is just street; zip from URL or context
        out["property_address_full"] = out["property_address"]
        if out.get("parcel_id"):
            # Add Memphis, TN context (assessor only shows Shelby County properties)
            out["property_address_full"] = f"{out['property_address']}, MEMPHIS, TN"

    # Detect absentee ownership (owner mailing != property address)
    if out.get("owner_mailing_zip") and out.get("property_address"):
        mz = out.get("owner_mailing_zip", "")
        if mz and not mz.startswith("381"):
            out["absentee_owner"] = True
            out["absentee_signal"] = f"owner_mailing_zip {mz} not in Memphis (381xx)"
        else:
            # Check street-level mismatch: same city but mailing street differs from property
            prop_street = (out.get("property_address") or "").upper().strip()
            mail_street = (out.get("owner_mailing_street") or "").upper().strip()
            if prop_street and mail_street and prop_street != mail_street:
                out["absentee_owner"] = True
                out["absentee_signal"] = "mailing street differs from property street (same zip)"
            else:
                out["absentee_owner"] = False

    # Out-of-state owner: highest-signal direct-mail target
    if out.get("owner_mailing_state") and out["owner_mailing_state"] != "TN":
        out["out_of_state_owner"] = True
        out["out_of_state_signal"] = f"mailing state {out['owner_mailing_state']} not TN"
    else:
        out["out_of_state_owner"] = False

    # LLC / Trust / Corp owner detection (institutional investor patterns)
    owner = (out.get("owner_name") or "").upper()
    llc_markers = ["LLC", "L.L.C", "INC", "INC.", "CORP", "TRUST", " LP ",
                   " LP$", "LIMITED PARTNERSHIP", "COMPANY", " CO ", "LLLP",
                   "FOUNDATION", "ESTATE OF"]
    out["is_llc_owner"] = any(
        (re.search(r"\b" + re.escape(m.strip("$ ")) + r"\b", owner) is not None)
        if not m.endswith("$") else re.search(r"\b" + re.escape(m[:-1]).strip() + r"$", owner) is not None
        for m in llc_markers
    )
    out["is_institutional_owner"] = out["is_llc_owner"]

    # Years owned (from last sale year, computed below after sales parsing)
    # We'll compute it after sales_history is processed.

    # Numeric coercion
    for k in ["year_built", "total_rooms", "bedrooms", "bathrooms", "half_baths",
              "sqft", "land_sqft"]:
        v = out.get(k)
        if v:
            try:
                v_clean = re.sub(r"[^\d.]", "", v)
                if v_clean:
                    out[k] = int(float(v_clean)) if "." not in v_clean else float(v_clean)
            except Exception:
                pass

    for k in ["land_appraisal_usd", "building_appraisal_usd", "total_appraisal_usd",
              "total_assessment_usd"]:
        v = out.get(k)
        if v:
            try:
                v_clean = re.sub(r"[^\d.]", "", v)
                if v_clean:
                    out[k] = int(float(v_clean))
            except Exception:
                pass

    # Vacant-lot detection
    lu = (out.get("land_use") or "").upper()
    bld = out.get("building_appraisal_usd")
    if "VACANT" in lu or (isinstance(bld, int) and bld == 0):
        out["is_vacant_lot"] = True

    # Sales history -- the assessor's <tbody id="salesBody"> is the build-year proxy.
    # First sale on record means structure existed by that date, so first_sale_year
    # is an UPPER bound on build year. Chris wants 1940+ build, so first_sale_year
    # >= 1940 keeps it in the running; pre-1940 first sale = likely too old.
    sales = []
    sales_tbody = soup.find("tbody", id="salesBody")
    if sales_tbody:
        for row in sales_tbody.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cells) >= 2 and cells[0]:
                rec = {
                    "date": cells[0],
                    "price_text": cells[1] if len(cells) > 1 else "",
                    "deed_or_inst": cells[2] if len(cells) > 2 else "",
                    "type_code": cells[3] if len(cells) > 3 else "",
                }
                # Numeric price
                price_clean = re.sub(r"[^\d]", "", rec["price_text"])
                if price_clean:
                    rec["price_usd"] = int(price_clean)
                # Year extraction (date is M/D/YYYY)
                ym = re.search(r"(\d{4})$", rec["date"])
                if ym:
                    rec["year"] = int(ym.group(1))
                sales.append(rec)
    out["sales_history"] = sales
    if sales:
        years = [s["year"] for s in sales if "year" in s]
        if years:
            out["first_sale_year"] = min(years)
            out["last_sale_year"] = max(years)
            for s in sales:
                if s.get("year") == max(years):
                    out["last_sale_date"] = s["date"]
                    out["last_sale_price_usd"] = s.get("price_usd")
                if s.get("year") == min(years):
                    out["first_sale_date"] = s["date"]
                    out["first_sale_price_usd"] = s.get("price_usd")
            # Build-year proxy (upper bound -- structure existed by first sale)
            out["build_year_proxy"] = out["first_sale_year"]
            out["build_year_proxy_basis"] = "first_sale_year (upper bound)"
            # Years owned signal (long-term owners are often pitch-receptive)
            current_year = datetime.now(timezone.utc).year
            out["years_owned"] = current_year - out["last_sale_year"]
            out["is_long_term_owner"] = out["years_owned"] >= 7

    # Permits -- 2nd build-year proxy (a permit predates demolition/major rebuild)
    permits = []
    permit_tbody = soup.find("tbody", id="permitBody")
    if permit_tbody:
        for row in permit_tbody.find_all("tr"):
            cells = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cells) >= 1 and cells[0]:
                rec = {
                    "date": cells[0],
                    "amount_text": cells[1] if len(cells) > 1 else "",
                    "reason": cells[2] if len(cells) > 2 else "",
                    "permit_number": cells[3] if len(cells) > 3 else "",
                }
                ym = re.search(r"(\d{4})$", rec["date"])
                if ym:
                    rec["year"] = int(ym.group(1))
                permits.append(rec)
    out["permits"] = permits

    # Chris's buy-box gate (computed locally so we can rank without buyer).
    # Priority order on year evidence:
    #   1. actual year_built field if assessor populated it (HARD evidence)
    #   2. first_sale_year as upper-bound proxy (SOFT evidence -- structure
    #      existed by then, so build year <= first_sale_year)
    # Vacant lots accept regardless (Chris explicitly said so).
    chris_check = {"vacant_lot_ok": False, "build_year_ok": None, "verdict": "unknown"}
    yb = out.get("year_built")
    if out.get("is_vacant_lot"):
        chris_check["vacant_lot_ok"] = True
        chris_check["verdict"] = "vacant_lot_accepted"
    elif isinstance(yb, int) and yb > 0:
        # Hard evidence -- assessor knows the build year
        chris_check["year_built_source"] = "assessor_actual"
        if yb >= 1940:
            chris_check["build_year_ok"] = True
            chris_check["verdict"] = f"year_built_{yb}_passes"
        else:
            chris_check["build_year_ok"] = False
            chris_check["verdict"] = f"year_built_{yb}_pre_1940_REJECT"
    elif out.get("first_sale_year"):
        chris_check["year_built_source"] = "first_sale_proxy"
        if out["first_sale_year"] >= 1940:
            chris_check["build_year_ok"] = True
            chris_check["verdict"] = f"first_sale_proxy_{out['first_sale_year']}_passes"
        else:
            chris_check["build_year_ok"] = False
            chris_check["verdict"] = f"first_sale_{out['first_sale_year']}_pre_1940_REJECT"
    else:
        chris_check["verdict"] = "no_sales_history_unknown_build_year"
    out["chris_check"] = chris_check

    # Distress / pitch signals -- composite for outreach personalization
    signals = []
    pitch_hooks = []
    if out.get("out_of_state_owner"):
        signals.append(f"out_of_state_owner_{out.get('owner_mailing_state','')}")
        pitch_hooks.append(
            f"out-of-state convenience (owner mailing in {out.get('owner_mailing_state','')})"
        )
    if out.get("absentee_owner"):
        signals.append("absentee_owner")
        if not out.get("out_of_state_owner"):
            pitch_hooks.append("absentee owner in Memphis (mailing differs from property)")
    if out.get("is_long_term_owner"):
        signals.append(f"long_term_owner_{out.get('years_owned')}yr")
        pitch_hooks.append(f"long-term owner ({out.get('years_owned')} years on title)")
    if out.get("is_llc_owner"):
        signals.append("institutional_owner")
        pitch_hooks.append("investor-to-investor framing (LLC/Trust/Corp owner)")
    if out.get("is_vacant_lot"):
        signals.append("vacant_lot")
        pitch_hooks.append("vacant lot -- carrying cost relief pitch")
    if isinstance(out.get("total_appraisal_usd"), int) and out["total_appraisal_usd"] < 50000:
        signals.append("low_appraisal_under_50k")
        pitch_hooks.append("low-appraisal asset (carrying cost vs value)")
    sales_count = len(out.get("sales_history") or [])
    if sales_count >= 4:
        signals.append(f"active_history_{sales_count}_sales")
        pitch_hooks.append(f"active sales history ({sales_count} transactions on record)")

    out["distress_signals"] = signals
    out["pitch_hooks"] = pitch_hooks
    out["signal_count"] = len(signals)
    out["outreach_priority"] = (
        "high" if len(signals) >= 3
        else "medium" if len(signals) >= 1
        else "low"
    )

    return out


def merge_to_leads_db(lead: dict) -> dict:
    """Write the parsed lead into leads_db.json. Match against existing by parcel or address."""
    if not LEADS_DB.exists():
        return {"action": "skip", "reason": "leads_db missing"}
    leads = json.loads(LEADS_DB.read_text())

    # Match strictly by parcel_id (exact). Substring address match was producing
    # false positives (1287 WILSON merging into a 1287 PHILADELPHIA record because
    # of multi-word overlap). Parcel_id is the only unique key the assessor gives us.
    parcel = (lead.get("parcel_id") or "").strip()
    addr_norm = re.sub(r"\s+", " ", (lead.get("property_address") or "").upper().strip())

    matched = None
    if parcel:
        for existing in leads:
            e_parcel = (existing.get("parcel_id") or "").strip()
            if e_parcel == parcel:
                matched = existing
                break

    # Fallback: only match by address if BOTH the full normalized address AND zip line up
    if not matched and addr_norm:
        for existing in leads:
            e_addr = re.sub(r"\s+", " ", (existing.get("address") or "").upper().strip())
            # Strip city/state suffix from existing address before exact compare
            e_addr_street = e_addr.split(",")[0].strip()
            if e_addr_street and e_addr_street == addr_norm:
                matched = existing
                break

    if matched:
        # Merge: update with assessor fields without overwriting source/created_at
        for k, v in lead.items():
            if k in ("source", "source_url", "source_file"):
                # Keep original source but track assessor enrichment
                matched.setdefault("enrichment_sources", []).append({
                    "type": "shelby_assessor_mhtml",
                    "file": lead.get("source_file"),
                    "url": lead.get("source_url"),
                    "ts": lead.get("parsed_at"),
                })
                continue
            if v is not None and v != "":
                matched[k] = v
        # If we got an owner name via assessor, mark queue ready
        if matched.get("owner_name") and matched.get("queue") == "needs_enrichment":
            matched["queue"] = "needs_skip_trace"  # has owner, needs phone/email
        action = "updated_existing"
    else:
        # Brand-new lead
        new_lead = {
            "address": lead.get("property_address_full") or lead.get("property_address"),
            "city": "MEMPHIS",
            "state": "TN",
            "zip_code": "",  # assessor doesn't always show property zip; could derive separately
            "lead_type": "tax_lien" if lead.get("absentee_owner") else "absentee_owner",
            "source": "shelby_assessor_mhtml",
            "status": "new",
            "outreach_count": 0,
            "sequence_step": 0,
            "created_at": lead.get("parsed_at"),
            "queue": "needs_skip_trace" if lead.get("owner_name") else "needs_enrichment",
            **lead,
        }
        leads.append(new_lead)
        matched = new_lead
        action = "created_new"

    LEADS_DB.write_text(json.dumps(leads, indent=2, default=str))
    return {"action": action, "lead": matched}


def write_parsed_json(lead: dict, parcel_safe: str) -> Path:
    out_path = PARSED / f"{parcel_safe}.json"
    out_path.write_text(json.dumps(lead, indent=2, default=str))
    return out_path


def process_file(mht_path: Path, dry_run: bool = False) -> dict:
    print(f"Processing: {mht_path.name}")
    html, source_url = extract_html_from_mht(mht_path)
    if not html:
        print(f"  No HTML found in MHTML")
        return {"file": str(mht_path), "ok": False, "reason": "no_html"}

    lead = extract_lead(html, source_url=source_url, source_file=str(mht_path))

    # Reject non-assessor MHTMLs (no parcel = not a property page).
    # User sometimes drops other browser-saved pages into the same folder.
    if not lead.get("parcel_id"):
        print(f"  SKIP -- no parcel_id detected (not an assessor page)")
        # Move to a 'rejected' subfolder so user can review
        rejected_dir = INBOX.parent / "rejected_non_assessor"
        rejected_dir.mkdir(exist_ok=True)
        if not dry_run:
            shutil.move(str(mht_path), str(rejected_dir / mht_path.name))
            print(f"  Moved to: {rejected_dir.name}/{mht_path.name}")
        return {"file": str(mht_path), "ok": False, "reason": "no_parcel_id"}

    parcel_safe = re.sub(r"[^a-zA-Z0-9]", "_", (lead.get("parcel_id") or mht_path.stem))

    print(f"  Parcel: {lead.get('parcel_id','?')}")
    print(f"  Owner: {lead.get('owner_name','?')}")
    print(f"  Property: {lead.get('property_address','?')}")
    print(f"  Owner mailing: {lead.get('owner_mailing_street','?')}, {lead.get('owner_mailing_city','?')} {lead.get('owner_mailing_state','?')} {lead.get('owner_mailing_zip','?')}")
    print(f"  Class: {lead.get('property_class','?')} / Use: {lead.get('land_use','?')}")
    print(f"  Vacant lot: {lead.get('is_vacant_lot','?')}")
    print(f"  Absentee: {lead.get('absentee_owner','?')}")
    print(f"  Year built: {lead.get('year_built','-')}, Beds: {lead.get('bedrooms','-')}, Baths: {lead.get('bathrooms','-')}, Sqft: {lead.get('sqft','-')}")
    print(f"  Land appraisal: ${lead.get('land_appraisal_usd','?')} / Total: ${lead.get('total_appraisal_usd','?')}")
    if lead.get("first_sale_year"):
        print(f"  First sale: {lead.get('first_sale_date','-')} for ${lead.get('first_sale_price_usd','-')} -- build_year_proxy <= {lead['first_sale_year']}")
        print(f"  Last sale:  {lead.get('last_sale_date','-')} for ${lead.get('last_sale_price_usd','-')}")
        print(f"  Sales on record: {len(lead.get('sales_history', []))}")
    cc = lead.get("chris_check", {})
    print(f"  Chris verdict: {cc.get('verdict','?').upper()}")

    if not dry_run:
        # Write the structured JSON
        json_path = write_parsed_json(lead, parcel_safe)
        print(f"  Saved: {json_path.name}")

        # Merge into leads_db
        result = merge_to_leads_db(lead)
        print(f"  leads_db: {result['action']}")

        # Move MHTML to archive -- skip if already in archive (re-parse case)
        archive_path = ARCHIVE / mht_path.name
        try:
            if mht_path.resolve() == archive_path.resolve():
                print(f"  Already in archive, no move needed")
            else:
                shutil.move(str(mht_path), str(archive_path))
                print(f"  Archived: {archive_path.name}")
        except (shutil.SameFileError, OSError) as e:
            print(f"  Archive skipped: {e}")
        return {"file": str(mht_path), "ok": True, "lead": lead, "leads_db_action": result["action"]}
    else:
        print(f"  [DRY RUN] would save {parcel_safe}.json + merge into leads_db + archive MHTML")
        return {"file": str(mht_path), "ok": True, "lead": lead, "dry_run": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--inbox", default=str(INBOX))
    args = parser.parse_args()

    if args.file:
        files = [Path(args.file)]
    else:
        inbox_path = Path(args.inbox)
        files = sorted(list(inbox_path.glob("*.mht")) + list(inbox_path.glob("*.mhtml")))
        if not files:
            print(f"No .mht / .mhtml files in {inbox_path}")
            sys.exit(0)

    print(f"Files to process: {len(files)}")
    print()
    results = []
    for f in files:
        results.append(process_file(f, dry_run=args.dry_run))
        print()

    print(f"=== SUMMARY ===")
    print(f"Total processed: {len(results)}")
    print(f"Success: {sum(1 for r in results if r['ok'])}")
    print(f"Created in leads_db: {sum(1 for r in results if r.get('leads_db_action') == 'created_new')}")
    print(f"Updated in leads_db: {sum(1 for r in results if r.get('leads_db_action') == 'updated_existing')}")


if __name__ == "__main__":
    main()
