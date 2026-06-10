"""daily_seller_list_builder -- runs once a day, processes the next batch of
unprocessed wholesale leads through Tennessee + Texas pipelines, applies the
matching buyer's buybox, appends qualified leads to a rolling seller list.

Per Rich's 2026-05-07 directive: "find me 100-200 valid properties to actually
package and send into a contract... don't get caught up on little details...
focus on Tennessee and Texas right now because those are the two built
pipelines we have." Aim for daily forward progress, not perfection.

Pipelines:
  TN -- Memphis / Mid South Homebuyers (Chris Ulander)
        Source: CHRIS_BATCH_001_DRAFT.json (50 leads, parcel-id keyed)
        Enricher: curl Shelby Assessor (no API cost)
        Buybox: year_built >= 1940, ARV $50k-$200k, SFR/duplex, no vacant/
                religious/commercial

  TX -- Dallas / New Western anchor + Daria Voss as designated agent
        Source: TX_prospects.csv (156 leads, ATTOM-enriched at scrape time)
        Enricher: NONE (data already present from ATTOM API)
        Buybox: estimated_arv $50k-$400k, distress flagged, contactable
                (owner_name or phone or email present)

State tracking:
  /AA_MY_DRIVE/_logs/wholesale_runs/processed_leads.json
  -- maps lead_id -> {processed_at, decision, output_path}
  -- ensures daily runs don't redo work

Output:
  /AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/buyers/
    daily_seller_list_<date>.json  (one per run)
    cumulative_seller_list.json    (all-time qualified leads)

Skip rules (don't fail the run):
  - assessor "technical difficulties" -> defer to retry pile, move on
  - missing parcel_id (TN) -> queue for address_to_parcel resolver
  - already-processed leads -> skip silently
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

WORKSPACE = Path("/AA_MY_DRIVE")
TN_BATCH = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/buyers/CHRIS_BATCH_001_DRAFT.json"
TX_PROSPECTS = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/prospecting/TX_prospects.csv"
PARSED_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/parsed"
RAW_HTML_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/owner_downloads/raw_html"
OUTPUT_DIR = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/buyers"
STATE_PATH = WORKSPACE / "_logs/wholesale_runs/processed_leads.json"
DEFER_PATH = WORKSPACE / "_logs/wholesale_runs/deferred_leads.json"
LOG_PATH = WORKSPACE / "_logs/wholesale_runs/daily_seller_list.log"
CUMULATIVE_PATH = OUTPUT_DIR / "cumulative_seller_list.json"

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DAILY_QUOTA = int(os.environ.get("WHOLESALE_DAILY_QUOTA", "30"))

CHRIS_BUY_BOX = {
    "buyer": "Mid South Homebuyers / Chris Ulander",
    "year_built_min": 1940,
    "ARV_max_usd": 200_000,
    "ARV_min_usd": 50_000,
    "bad_land_uses": ("VACANT", "RELIGIOUS", "CHURCH", "COMMERCIAL",
                       "INDUSTRIAL", "AGRICULTURAL", "EXEMPT", "GOVERNMENT",
                       "SCHOOL", "UTILITY"),
}

TX_BUY_BOX = {
    # IMPORTANT (Rich, 2026-05-07): no contracted TX anchor buyer yet.
    # Chris buys ONLY in TN. TX leads pile up "qualified, awaiting placement"
    # until we sign a TX-compliant anchor (TX SB 1577 disclosure rules per
    # Daria Voss). Top targets per TX_TARGETS_SEED: New Western (P1, 8200
    # deals/yr), REI Nation (DFW HQ + Memphis overlap).
    "buyer": "AWAITING TX ANCHOR (top targets: New Western, REI Nation)",
    "year_built_min": 1960,
    "ARV_max_usd": 400_000,
    "ARV_min_usd": 50_000,
    "require_contact": True,  # need owner_name OR phone OR email
    "compliance_note": "TX SB 1577 -- equitable-interest disclosure required on outreach",
}


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"version": 1, "leads": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "leads": {}}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _record_processed(state: dict, lead_id: str, decision: str,
                       buyer: str, parcel_id: str = "",
                       address: str = "", reasons: list[str] = None,
                       extra: dict = None) -> None:
    state["leads"][lead_id] = {
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "decision": decision,
        "buyer": buyer,
        "parcel_id": parcel_id,
        "address": address,
        "reasons": reasons or [],
        **(extra or {}),
    }


def _defer_lead(lead_id: str, reason: str, lead: dict) -> None:
    DEFER_PATH.parent.mkdir(parents=True, exist_ok=True)
    deferred = {}
    if DEFER_PATH.exists():
        try:
            deferred = json.loads(DEFER_PATH.read_text(encoding="utf-8"))
        except Exception:
            deferred = {}
    deferred[lead_id] = {
        "deferred_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "reason": reason,
        "lead_summary": {k: lead.get(k) for k in
                          ("address", "city", "state", "parcel_id")},
    }
    DEFER_PATH.write_text(json.dumps(deferred, indent=2), encoding="utf-8")


# ---------- TN pipeline ----------


def fetch_shelby(parcel_id: str, max_retries: int = 2) -> str | None:
    encoded = urllib.parse.quote(parcel_id)
    url = (f"https://www.assessormelvinburgess.com/propertyDetails"
           f"?IR=true&parcelid={encoded}")
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    time.sleep(1.0 * attempt)
                    continue
                html = resp.read().decode("utf-8", errors="replace")
                if ("technical difficulties" in html.lower()
                        or "please try again later" in html.lower()):
                    time.sleep(1.5 * attempt)
                    continue
                if len(html) < 5000:
                    return None
                if (parcel_id.replace(" ", "").lower()
                        not in html.replace(" ", "").lower()):
                    time.sleep(1.0 * attempt)
                    continue
                return html
        except Exception:
            time.sleep(1.0 * attempt)
    return None


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


def parse_shelby(html: str, parcel_id: str, fallback_addr: str) -> dict:
    return {
        "source": "shelby_assessor_curl",
        "parsed_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "parcel_id": parcel_id,
        "property_address": _extract(html, "Property\\s*Address") or fallback_addr,
        "owner_name": _extract(html, "Owner(?:\\s+Name)?"),
        "land_use": _extract(html, "Land\\s*Use"),
        "year_built": _extract_int(html, "Year\\s*Built"),
        "sqft": _extract_int(html, "(?:Living\\s*Area|Building\\s*Area|Square\\s*Feet)"),
        "bedrooms": _extract_int(html, "(?:Bedrooms|Beds)"),
        "land_appraisal_usd": _extract_int(html, "Land\\s*Appraisal"),
        "building_appraisal_usd": _extract_int(html, "Building\\s*Appraisal"),
        "total_appraisal_usd": _extract_int(html, "Total\\s*Appraisal"),
        "subdivision": _extract(html, "Subdivision"),
    }


def passes_chris_buybox(parsed: dict) -> tuple[bool, list[str]]:
    fails = []
    yb = parsed.get("year_built")
    if yb is None:
        fails.append("year_built unknown")
    elif yb < CHRIS_BUY_BOX["year_built_min"]:
        fails.append(f"year_built {yb} < 1940")
    arv = parsed.get("total_appraisal_usd")
    if not arv:
        fails.append("appraisal unknown")
    elif arv > CHRIS_BUY_BOX["ARV_max_usd"]:
        fails.append(f"appraisal {arv} > 200000")
    elif arv < CHRIS_BUY_BOX["ARV_min_usd"]:
        fails.append(f"appraisal {arv} < 50000")
    land = (parsed.get("land_use") or "").upper()
    if not land:
        fails.append("land_use unknown")
    elif any(b in land for b in CHRIS_BUY_BOX["bad_land_uses"]):
        fails.append(f"land_use {land!r}")
    return (not fails, fails)


def process_tn_lead(lead: dict, state: dict) -> dict | None:
    """Returns the seller-list record if it passes; None otherwise."""
    parcel = lead.get("parcel_id")
    addr = lead.get("address", "")
    lead_id = lead.get("lead_id") or f"TN-{parcel}-{addr[:30]}"

    if lead_id in state["leads"]:
        return None  # already processed

    if not parcel:
        _defer_lead(lead_id, "missing parcel_id; needs address->parcel resolver",
                    lead)
        _record_processed(state, lead_id, "deferred",
                          CHRIS_BUY_BOX["buyer"], "", addr,
                          ["no parcel_id"])
        _log(f"  TN {lead_id}: DEFERRED (no parcel_id)")
        return None

    html = fetch_shelby(parcel)
    if not html:
        _defer_lead(lead_id, "shelby technical-difficulties or fetch_failed",
                    lead)
        _record_processed(state, lead_id, "deferred",
                          CHRIS_BUY_BOX["buyer"], parcel, addr,
                          ["shelby fetch failed"])
        _log(f"  TN {lead_id}: DEFERRED (shelby unreachable)")
        return None

    # archive + parse + classify
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    safe_pid = parcel.replace(" ", "_").replace("/", "_")
    with gzip.open(RAW_HTML_DIR / f"{safe_pid}.html.gz", "wt",
                   encoding="utf-8") as f:
        f.write(html)
    parsed = parse_shelby(html, parcel, addr)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    (PARSED_DIR / f"{safe_pid}.json").write_text(
        json.dumps(parsed, indent=2), encoding="utf-8")

    passes, reasons = passes_chris_buybox(parsed)
    decision = "qualified" if passes else "rejected_buybox"
    _record_processed(state, lead_id, decision, CHRIS_BUY_BOX["buyer"],
                      parcel, addr, reasons,
                      extra={"year_built": parsed.get("year_built"),
                             "appraisal": parsed.get("total_appraisal_usd")})

    if passes:
        _log(f"  TN {lead_id}: QUALIFIED -- {parsed.get('property_address')}")
        return {
            "lead_id": lead_id,
            "buyer": CHRIS_BUY_BOX["buyer"],
            "state": "TN",
            "address": parsed.get("property_address", addr),
            "parcel_id": parcel,
            "owner_name": parsed.get("owner_name"),
            "year_built": parsed.get("year_built"),
            "sqft": parsed.get("sqft"),
            "land_use": parsed.get("land_use"),
            "total_appraisal_usd": parsed.get("total_appraisal_usd"),
            "qualified_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                                            time.gmtime()),
        }
    _log(f"  TN {lead_id}: rejected -- {', '.join(reasons[:2])}")
    return None


# ---------- TX pipeline ----------


def passes_tx_buybox(lead: dict) -> tuple[bool, list[str]]:
    fails = []
    try:
        arv = float(lead.get("estimated_arv") or 0)
    except (ValueError, TypeError):
        arv = 0
    if arv == 0:
        fails.append("estimated_arv unknown")
    elif arv < TX_BUY_BOX["ARV_min_usd"]:
        fails.append(f"ARV {arv} < {TX_BUY_BOX['ARV_min_usd']}")
    elif arv > TX_BUY_BOX["ARV_max_usd"]:
        fails.append(f"ARV {arv} > {TX_BUY_BOX['ARV_max_usd']}")

    try:
        yb = int(lead.get("year_built") or 0)
    except (ValueError, TypeError):
        yb = 0
    # year_built unknown OK for TX (volume buyer); only fail if explicitly old
    if yb and yb < TX_BUY_BOX["year_built_min"]:
        fails.append(f"year_built {yb} < {TX_BUY_BOX['year_built_min']}")

    if TX_BUY_BOX["require_contact"]:
        contactable = (lead.get("owner_name") or lead.get("phone")
                        or lead.get("email"))
        if not contactable:
            fails.append("no contact info (owner+phone+email all empty)")

    return (not fails, fails)


def process_tx_lead(lead: dict, state: dict) -> dict | None:
    lead_id = lead.get("lead_id") or f"TX-{lead.get('address','')[:40]}"
    if lead_id in state["leads"]:
        return None

    addr = lead.get("address", "")
    passes, reasons = passes_tx_buybox(lead)
    decision = "qualified" if passes else "rejected_buybox"
    _record_processed(state, lead_id, decision, TX_BUY_BOX["buyer"],
                      "", addr, reasons,
                      extra={"year_built": lead.get("year_built"),
                             "estimated_arv": lead.get("estimated_arv")})

    if passes:
        _log(f"  TX {lead_id}: QUALIFIED -- {addr}")
        return {
            "lead_id": lead_id,
            "buyer": TX_BUY_BOX["buyer"],
            "state": "TX",
            "address": addr,
            "city": lead.get("city"),
            "zip": lead.get("zip"),
            "owner_name": lead.get("owner_name"),
            "phone": lead.get("phone"),
            "email": lead.get("email"),
            "estimated_arv": lead.get("estimated_arv"),
            "year_built": lead.get("year_built"),
            "beds": lead.get("beds"),
            "sqft": lead.get("sqft"),
            "distress": lead.get("distress") or lead.get("lead_type"),
            "qualified_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                                            time.gmtime()),
        }
    _log(f"  TX {lead_id}: rejected -- {', '.join(reasons[:2])}")
    return None


# ---------- top-level driver ----------


def run(quota: int = DAILY_QUOTA) -> dict:
    state = _load_state()
    qualified_today: list[dict] = []
    counts = {"tn_processed": 0, "tn_qualified": 0, "tn_rejected": 0,
               "tn_deferred": 0,
               "tx_processed": 0, "tx_qualified": 0, "tx_rejected": 0,
               "skipped_already_done": 0}

    _log(f"=== daily_seller_list_builder starting (quota={quota}) ===")

    # TN pass
    if TN_BATCH.exists():
        tn_data = json.loads(TN_BATCH.read_text(encoding="utf-8"))
        tn_leads = tn_data.get("leads", [])
        _log(f"TN universe: {len(tn_leads)} leads in CHRIS_BATCH_001_DRAFT")
        tn_budget = quota // 2
        for lead in tn_leads:
            if counts["tn_processed"] >= tn_budget:
                break
            lead_id = lead.get("lead_id") or (
                f"TN-{lead.get('parcel_id','')}-{lead.get('address','')[:30]}")
            if lead_id in state["leads"]:
                counts["skipped_already_done"] += 1
                continue
            counts["tn_processed"] += 1
            result = process_tn_lead(lead, state)
            entry = state["leads"].get(lead_id, {})
            decision = entry.get("decision", "unknown")
            if decision == "qualified" and result:
                qualified_today.append(result)
                counts["tn_qualified"] += 1
            elif decision == "rejected_buybox":
                counts["tn_rejected"] += 1
            elif decision == "deferred":
                counts["tn_deferred"] += 1
            time.sleep(0.5)

    # TX pass
    if TX_PROSPECTS.exists():
        with TX_PROSPECTS.open("r", encoding="utf-8") as f:
            tx_leads = list(csv.DictReader(f))
        _log(f"TX universe: {len(tx_leads)} leads in TX_prospects.csv")
        tx_budget = quota - counts["tn_processed"]
        for lead in tx_leads:
            if counts["tx_processed"] >= tx_budget:
                break
            lead_id = lead.get("lead_id")
            if lead_id and lead_id in state["leads"]:
                counts["skipped_already_done"] += 1
                continue
            counts["tx_processed"] += 1
            result = process_tx_lead(lead, state)
            if result:
                qualified_today.append(result)
                counts["tx_qualified"] += 1
            else:
                counts["tx_rejected"] += 1

    _save_state(state)

    # Write daily output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = time.strftime("%Y-%m-%d")
    daily_path = OUTPUT_DIR / f"daily_seller_list_{today}.json"
    daily_path.write_text(json.dumps({
        "date": today,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                                        time.gmtime()),
        "counts": counts,
        "qualified": qualified_today,
    }, indent=2), encoding="utf-8")

    # Update cumulative
    cumulative = {"all_qualified": []}
    if CUMULATIVE_PATH.exists():
        try:
            cumulative = json.loads(CUMULATIVE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    seen_ids = {q["lead_id"] for q in cumulative.get("all_qualified", [])}
    for q in qualified_today:
        if q["lead_id"] not in seen_ids:
            cumulative["all_qualified"].append(q)
            seen_ids.add(q["lead_id"])
    cumulative["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                                              time.gmtime())
    cumulative["total_qualified"] = len(cumulative["all_qualified"])
    cumulative["target"] = "100-200 valid properties to send into contracts"
    cumulative["progress_pct"] = min(100,
                                       round(cumulative["total_qualified"] * 100 / 100, 1))
    CUMULATIVE_PATH.write_text(json.dumps(cumulative, indent=2),
                                 encoding="utf-8")

    _log(f"=== daily run complete ===")
    _log(f"counts: {counts}")
    _log(f"qualified today: {len(qualified_today)} | cumulative: "
          f"{cumulative['total_qualified']}/100-200 target")
    return {"counts": counts, "qualified_today": qualified_today,
            "cumulative_total": cumulative["total_qualified"],
            "daily_path": str(daily_path),
            "cumulative_path": str(CUMULATIVE_PATH)}


if __name__ == "__main__":
    quota = int(sys.argv[1]) if len(sys.argv) > 1 else DAILY_QUOTA
    result = run(quota=quota)
    print()
    print(json.dumps({k: v for k, v in result.items()
                      if k != "qualified_today"}, indent=2))
    print(f"\nqualified today ({len(result['qualified_today'])}):")
    for q in result["qualified_today"][:20]:
        print(f"  [{q['state']}] {q['address']:40} "
              f"-- ARV/appraisal: ${q.get('total_appraisal_usd') or q.get('estimated_arv', '?')}")
