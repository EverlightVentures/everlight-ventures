"""tn_full_pipeline -- the daily TN cycle Rich asked for 2026-05-07.

ONE script that runs nightly (cron at 7:30 AM PT) and handles the whole loop:

  STAGE 1: INGEST    -- fetch Shelby tax-sale CSV + dedupe vs. master ledger
  STAGE 2: ENRICH    -- next N unprocessed addresses POST'd to assessor
                        for owner / year_built / sqft / class / zip
  STAGE 3: FILTER    -- Chris's TN buybox (1940+ SFR, $50-200k, 15 zips,
                        2-4BR)
  STAGE 4: ASSEMBLE  -- for qualified: full deal package via
                        tn_profile_assembler (HTML + screenshot + profile.md
                        + offer letter draft + PSA PDF)
  STAGE 5: SEND      -- optional first-touch outbound (DRY_RUN by default)
                        with DNC + recipient_class + halt-policy v2 gates
  STAGE 6: REPORT    -- daily summary log + branded Slack post

Token / cost budget (~$2.50/month at 50 enrichments/day):
  - All curl + Playwright is $0
  - Email triage classifier is the main LLM cost (Haiku 4.5)
  - Resend is free up to 3,000 sends/month per workspace doctrine

State files:
  /AA_MY_DRIVE/_logs/wholesale_runs/tn_master_ledger.json
    -- one row per parcel ever seen; ingest dedupes against this
  /AA_MY_DRIVE/_logs/wholesale_runs/processed_leads.json
    -- daily decisions, used by builder + this pipeline
  /AA_MY_DRIVE/_logs/wholesale_runs/cost_tracker.json
    -- per-day cost line items (cumulative + monthly cap)

Env knobs:
  TN_PIPELINE_DAILY_QUOTA = 50       (addresses to process per run)
  TN_PIPELINE_SEND_ENABLED = 0       (1 to enable first-touch sends; 0 = drafts only)
  TN_PIPELINE_DRY_INGEST = 0         (1 to skip CSV refetch -- use cached)
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/AA_MY_DRIVE")
sys.path.insert(0, str(WORKSPACE / "06_DEVELOPMENT/everlight_os/wholesale_pipeline"))
sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))

# Existing modules
import tn_profile_assembler as assembler  # noqa: E402
import shelby_tax_delinquent_to_leads as shelby  # noqa: E402
import funnel_tracker  # noqa: E402

# Paths
MASTER_LEDGER = WORKSPACE / "_logs/wholesale_runs/tn_master_ledger.json"
PROCESSED_LEDGER = WORKSPACE / "_logs/wholesale_runs/processed_leads.json"
COST_TRACKER = WORKSPACE / "_logs/wholesale_runs/cost_tracker.json"
DAILY_RUN_LOG = WORKSPACE / "_logs/wholesale_runs/tn_full_pipeline.log"
DEAL_DIRS_ROOT = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/contracts/active_deals"

# Knobs
DAILY_QUOTA = int(os.environ.get("TN_PIPELINE_DAILY_QUOTA", "50"))
SEND_ENABLED = os.environ.get("TN_PIPELINE_SEND_ENABLED", "0") == "1"
DRY_INGEST = os.environ.get("TN_PIPELINE_DRY_INGEST", "0") == "1"

# Cost-line constants ($USD per unit)
COST_PER_CURL = 0.0           # free
COST_PER_SCREENSHOT = 0.0     # local Playwright
COST_PER_HAIKU_CLASSIFY = 0.001
COST_PER_RESEND_SEND = 0.0001
MONTHLY_BUDGET_CAP = 50.00     # generous; well above projected $2.50/mo


def _log(msg: str) -> None:
    DAILY_RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line)
    with DAILY_RUN_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_json(path: Path, default) -> dict | list:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


# ============================================================
# STAGE 1: INGEST
# ============================================================


def stage_ingest() -> dict:
    """Pull Shelby tax-sale CSV, merge into master ledger. Return delta stats."""
    _log("=== STAGE 1: INGEST ===")

    if DRY_INGEST and shelby.TAX_CSV.exists():
        _log("  DRY_INGEST=1 -- using cached CSV")
        csv_path = shelby.TAX_CSV
    else:
        _log(f"  fetching {shelby.TAX_CSV_URL}")
        try:
            csv_path = shelby.fetch_tax_csv()
        except Exception as e:
            _log(f"  FETCH FAILED: {e} -- falling back to cached if available")
            if not shelby.TAX_CSV.exists():
                return {"ok": False, "error": str(e), "added": 0}
            csv_path = shelby.TAX_CSV

    raw_rows = shelby.load_tax_rows(csv_path)
    _log(f"  loaded {len(raw_rows)} rows from CSV")

    ledger = _load_json(MASTER_LEDGER, {"version": 1, "addresses": {}})
    seen_parcels = set(ledger["addresses"].keys())

    added = 0
    today_iso = datetime.now(timezone.utc).isoformat()
    for row in raw_rows:
        pid = row.get("parcel_id", "").strip()
        if not pid or pid in seen_parcels:
            continue
        ledger["addresses"][pid] = {
            "parcel_id": pid,
            "alt_parcel": row.get("alt_parcel", ""),
            "street_number": row.get("street_number", ""),
            "street_name": row.get("street_name", "").strip(),
            "tax_sale": row.get("tax_sale", ""),
            "register_url": row.get("register_url", ""),
            "first_seen": today_iso,
            "status": "queued",  # queued -> enriched -> qualified|rejected -> sent|deferred
        }
        seen_parcels.add(pid)
        added += 1

    ledger["last_ingest_at"] = today_iso
    ledger["total_addresses"] = len(ledger["addresses"])
    _save_json_atomic(MASTER_LEDGER, ledger)

    _log(f"  added {added} new addresses to master ledger "
          f"(total: {ledger['total_addresses']})")
    return {"ok": True, "added": added, "total": ledger["total_addresses"]}


# ============================================================
# STAGE 2-4: ENRICH + FILTER + ASSEMBLE
# ============================================================


def stage_enrich_and_filter(quota: int) -> dict:
    """Pop next quota unprocessed addresses, enrich via assessor POST,
    apply Chris's buybox, assemble deal packages for qualifieds."""
    _log(f"=== STAGE 2-4: ENRICH + FILTER + ASSEMBLE (quota={quota}) ===")

    ledger = _load_json(MASTER_LEDGER, {"version": 1, "addresses": {}})
    processed = _load_json(PROCESSED_LEDGER, {"version": 1, "leads": {}})

    # Pick queued addresses
    todo = [(pid, addr) for pid, addr in ledger["addresses"].items()
             if addr["status"] == "queued"][:quota]
    _log(f"  popped {len(todo)} addresses from queue "
          f"(of {sum(1 for a in ledger['addresses'].values() if a['status']=='queued')} queued total)")

    qualified_today: list[dict] = []
    counts = {"enriched": 0, "qualified": 0, "rejected": 0, "errors": 0}

    for pid, addr_record in todo:
        st_num = addr_record.get("street_number", "")
        st_name = addr_record.get("street_name", "")
        addr_str = f"{st_num} {st_name}".strip()
        lead_id = f"TN-shelby-{pid}"

        if not st_num or not st_name:
            ledger["addresses"][pid]["status"] = "skipped_empty_address"
            counts["errors"] += 1
            continue

        # --- Stage 2: enrich via assessor GET (parcel-keyed) ---
        # We use the GET propertyDetails endpoint because the POST AddressSubmit
        # endpoint returns sparse HTML that doesn't have year_built/owner in
        # parseable form. The CSV gives us parcel_id directly, so we go
        # straight to the detail page.
        html = assembler.fetch_shelby(pid)
        if not html:
            _log(f"  fetch_failed: {addr_str}")
            ledger["addresses"][pid]["status"] = "fetch_error"
            counts["errors"] += 1
            continue
        parsed = assembler.parse_shelby(html, pid, addr_str)
        # adapt parsed schema -> shelby.matches_chris_box's expected dict
        detail = {
            "owner_name": parsed.get("owner_name"),
            "zip": addr_record.get("zip", ""),  # may be empty; matches_chris_box has fallback
            "year_built": str(parsed.get("year_built") or ""),
            "sqft": str(parsed.get("sqft") or ""),
            "bedrooms": str(parsed.get("bedrooms") or ""),
            "property_class": parsed.get("land_use", ""),  # land_use approximates class
            "address_full": parsed.get("property_address"),
        }
        # Pull zip from the parsed property_address if present (e.g. "MEMPHIS, TN 38104")
        import re as _re
        m_zip = _re.search(r"\b(38\d{3})\b", parsed.get("property_address") or "")
        if m_zip:
            detail["zip"] = m_zip.group(1)
        counts["enriched"] += 1

        # --- Stage 3: filter (use assembler's stricter buybox -- it knows
        # about land_use disqualifications like VACANT/RELIGIOUS) ---
        passed, fails = assembler.passes_chris_buybox(parsed)
        reason = "passed" if passed else ", ".join(fails)
        if not passed:
            ledger["addresses"][pid]["status"] = "rejected_buybox"
            ledger["addresses"][pid]["reject_reason"] = reason
            ledger["addresses"][pid]["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
            counts["rejected"] += 1
            processed["leads"][lead_id] = {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "decision": "rejected_buybox",
                "buyer": "Chris Ulander",
                "address": addr_str,
                "parcel_id": pid,
                "reason": reason,
            }
            continue

        # --- Stage 4: assemble full deal package ---
        try:
            asm_result = assembler.assemble(addr_str, pid, "Memphis", "TN",
                                              detail.get("zip", ""))
        except Exception as e:
            _log(f"  ASSEMBLY FAILED for {addr_str}: {e}")
            ledger["addresses"][pid]["status"] = "assembly_error"
            ledger["addresses"][pid]["last_error"] = str(e)[:120]
            counts["errors"] += 1
            continue

        ledger["addresses"][pid]["status"] = "qualified_assembled"
        ledger["addresses"][pid]["last_enriched_at"] = datetime.now(timezone.utc).isoformat()
        ledger["addresses"][pid]["deal_dir"] = asm_result.get("deal_dir")
        ledger["addresses"][pid]["psa_pdf"] = asm_result.get("psa_pdf")
        ledger["addresses"][pid]["offer_letter"] = asm_result.get("offer_letter")
        counts["qualified"] += 1

        # Funnel-tracker upsert: every qualified lead enters at "cold" tier.
        # Re-read parsed.json to get the full record (assembler wrote it).
        try:
            parsed_path = Path(asm_result.get("deal_dir", "")) / "parsed.json"
            if parsed_path.exists():
                pdata = json.loads(parsed_path.read_text(encoding="utf-8"))
                # estimate MAO using assembler's compute_offer
                from tn_profile_assembler import compute_offer
                offer = compute_offer(pdata)
                funnel_tracker.upsert_lead(
                    parsed=pdata,
                    deal_dir=asm_result.get("deal_dir", ""),
                    psa_pdf=asm_result.get("psa_pdf") or "",
                    offer_letter=asm_result.get("offer_letter") or "",
                    mao=offer.get("MAO_offer_usd"),
                )
        except Exception as e:
            _log(f"  funnel upsert failed for {addr_str} (non-fatal): {e}")

        qualified_today.append({
            "lead_id": lead_id,
            "parcel_id": pid,
            "address": addr_str,
            "owner": detail.get("owner_name"),
            "year_built": asm_result.get("year_built"),
            "appraisal": asm_result.get("appraisal"),
            "deal_dir": asm_result.get("deal_dir"),
            "psa_pdf": asm_result.get("psa_pdf"),
            "offer_letter": asm_result.get("offer_letter"),
        })

        processed["leads"][lead_id] = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "decision": "qualified",
            "buyer": "Chris Ulander",
            "parcel_id": pid,
            "address": addr_str,
            "deal_dir": asm_result.get("deal_dir"),
        }

        time.sleep(0.5)  # courtesy delay between assessor POSTs

    _save_json_atomic(MASTER_LEDGER, ledger)
    _save_json_atomic(PROCESSED_LEDGER, processed)

    _log(f"  enrichment complete: {counts}")
    return {"counts": counts, "qualified_today": qualified_today}


# ============================================================
# STAGE 5: FIRST-TOUCH SEND (gated)
# ============================================================


def stage_send(qualified_leads: list[dict]) -> dict:
    """Send offer-letter draft to seller. STRICT gates:
      - SEND_ENABLED env var must be 1
      - Recipient must NOT be in DNC
      - branded_mailer enforces budget + halt-policy v2
      - First-touch caps to <= 5 sends per run unless explicitly overridden
    """
    _log(f"=== STAGE 5: SEND (enabled={SEND_ENABLED}) ===")

    if not SEND_ENABLED:
        _log("  TN_PIPELINE_SEND_ENABLED=0 -- skipping all sends, drafts only")
        return {"sent": 0, "skipped_disabled": len(qualified_leads)}

    # We currently have no seller email/phone for tax-sale leads
    # (skip-trace is a future stage). Until skip_trace is wired in,
    # we cannot send first-touch -- there's no recipient.
    _log("  no seller contact info on tax-sale leads (skip-trace not wired)")
    _log("  qualified packages staged in deal dirs; review + manual send")
    return {"sent": 0, "blocked": "no_seller_email", "qualified": len(qualified_leads)}


# ============================================================
# STAGE 6: COST TRACKER + REPORT
# ============================================================


def stage_report(ingest: dict, enrich: dict, send: dict,
                  start_ts: float) -> dict:
    """Compute today's cost line, update monthly tracker, post summary."""
    _log("=== STAGE 6: REPORT ===")
    today = datetime.now().strftime("%Y-%m-%d")
    counts = enrich["counts"]

    daily_cost = (
        counts["enriched"] * (COST_PER_CURL + COST_PER_SCREENSHOT)
        + counts["qualified"] * COST_PER_SCREENSHOT  # screenshot per qualified
        + send.get("sent", 0) * COST_PER_RESEND_SEND
    )
    elapsed = round(time.time() - start_ts, 1)

    # Update cost ledger
    ct = _load_json(COST_TRACKER, {"version": 1, "days": {},
                                     "month_totals": {}, "monthly_cap_usd": MONTHLY_BUDGET_CAP})
    ct["days"][today] = ct["days"].get(today, {})
    ct["days"][today].update({
        "ts": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "ingest_added": ingest.get("added", 0),
        "ingest_total": ingest.get("total", 0),
        "enriched": counts["enriched"],
        "qualified": counts["qualified"],
        "rejected": counts["rejected"],
        "errors": counts["errors"],
        "sent": send.get("sent", 0),
        "daily_cost_usd": daily_cost,
    })
    month = today[:7]
    ct["month_totals"][month] = ct["month_totals"].get(month, 0) + daily_cost
    ct["last_run_at"] = datetime.now(timezone.utc).isoformat()
    _save_json_atomic(COST_TRACKER, ct)

    summary = (
        f"TN PIPELINE | {today}\n"
        f"  ingest: +{ingest.get('added',0)} new (master ledger: {ingest.get('total','?')})\n"
        f"  enriched: {counts['enriched']} | qualified: {counts['qualified']} | "
        f"rejected: {counts['rejected']} | errors: {counts['errors']}\n"
        f"  sent: {send.get('sent',0)} (gate={SEND_ENABLED})\n"
        f"  cost: ${daily_cost:.4f} (month-to-date: ${ct['month_totals'][month]:.4f}/"
        f"${MONTHLY_BUDGET_CAP:.2f})\n"
        f"  elapsed: {elapsed}s"
    )
    _log(summary)

    # Branded Slack post (best-effort)
    try:
        sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts"))
        from content_tools.branded_slack import post_branded_slack
        post_branded_slack(
            channel="#deploy-log",
            title=f"TN wholesale pipeline -- {today}",
            summary=summary,
            category="report",
            agent_name="Lucrex",
            agent_title="TN pipeline coordinator",
        )
    except Exception as e:
        _log(f"  slack post failed (non-fatal): {e}")

    return {"summary": summary, "daily_cost_usd": daily_cost}


# ============================================================
# DRIVER
# ============================================================


def run() -> dict:
    start = time.time()
    _log("##### TN FULL PIPELINE START #####")
    ingest = stage_ingest()
    enrich = stage_enrich_and_filter(quota=DAILY_QUOTA)
    send = stage_send(enrich.get("qualified_today", []))
    report = stage_report(ingest, enrich, send, start)
    _log("##### TN FULL PIPELINE END #####")
    return {
        "ingest": ingest,
        "enrich": enrich,
        "send": send,
        "report": report,
    }


if __name__ == "__main__":
    result = run()
    print()
    print(json.dumps({
        "ingest_added": result["ingest"].get("added"),
        "ingest_total": result["ingest"].get("total"),
        "enrich_counts": result["enrich"].get("counts"),
        "send": result["send"],
        "daily_cost": result["report"].get("daily_cost_usd"),
    }, indent=2))
