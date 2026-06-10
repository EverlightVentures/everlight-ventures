"""funnel_tracker -- single rolling sheet of every qualified TN lead with
its current funnel stage. Updated by tn_full_pipeline daily.

Stages (lowercase, match status flow exactly):
  cold       -- enriched + qualified + package built; never touched
  reached    -- letter mailed (we have a deliverable on the way)
  warm       -- any reply received (intent unknown)
  hot        -- reply expresses interest in selling / pricing
  contracted -- seller signed PSA
  closed     -- Chris bought; assignment fee paid
  rejected   -- explicitly declined
  dnc        -- on do-not-contact list

Output:
  /AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/buyers/funnel_master.csv
  -- one row per parcel ever-qualified, columns track lifecycle dates

Usage:
  from funnel_tracker import upsert_lead, mark_stage, snapshot_metrics
  upsert_lead(parsed, deal_dir, mailing_full)
  mark_stage(parcel_id, "reached", note="USPS first-class 2026-05-08")
  print(snapshot_metrics())
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

WORKSPACE = Path("/AA_MY_DRIVE")
FUNNEL_CSV = WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/buyers/funnel_master.csv"
HISTORY_LOG = WORKSPACE / "_logs/wholesale_runs/funnel_history.jsonl"

STAGES = ("cold", "reached", "warm", "hot", "contracted", "closed",
          "rejected", "dnc")

COLUMNS = [
    "parcel_id", "address", "city", "state", "zip", "owner_name",
    "owner_mailing_full", "year_built", "bedrooms", "sqft",
    "total_appraisal_usd", "mao_offer_usd", "land_use",
    "deal_dir", "psa_pdf", "offer_letter",
    "stage",
    "first_qualified_at", "reached_at", "warm_at", "hot_at",
    "contracted_at", "closed_at", "rejected_at", "dnc_at",
    "outreach_count", "last_outreach_at", "last_outreach_channel",
    "reply_count", "last_reply_at", "last_reply_summary",
    "buyer_assigned", "assignment_fee_usd", "notes",
]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())


def _load() -> list[dict]:
    if not FUNNEL_CSV.exists():
        return []
    with FUNNEL_CSV.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(rows: list[dict]) -> None:
    FUNNEL_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp = FUNNEL_CSV.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    tmp.replace(FUNNEL_CSV)


def _log_event(event: dict) -> None:
    HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


def upsert_lead(parsed: dict, deal_dir: str, psa_pdf: str = "",
                offer_letter: str = "", mao: int | None = None) -> dict:
    """Add or refresh a qualified lead in the funnel. Stage defaults to 'cold'."""
    rows = _load()
    pid = parsed.get("parcel_id")
    existing = next((r for r in rows if r["parcel_id"] == pid), None)
    is_new = existing is None
    record = existing or {c: "" for c in COLUMNS}
    record.update({
        "parcel_id": pid,
        "address": parsed.get("property_address") or "",
        "city": "Memphis",
        "state": "TN",
        "zip": parsed.get("property_zip") or "",
        "owner_name": parsed.get("owner_name") or "",
        "owner_mailing_full": parsed.get("owner_mailing_full") or "",
        "year_built": parsed.get("year_built") or "",
        "bedrooms": parsed.get("bedrooms") or "",
        "sqft": parsed.get("sqft") or "",
        "total_appraisal_usd": parsed.get("total_appraisal_usd") or "",
        "mao_offer_usd": mao or "",
        "land_use": parsed.get("land_use") or "",
        "deal_dir": deal_dir,
        "psa_pdf": psa_pdf,
        "offer_letter": offer_letter,
    })
    if is_new:
        record["stage"] = "cold"
        record["first_qualified_at"] = _now()
        record["outreach_count"] = "0"
        record["reply_count"] = "0"
        rows.append(record)
    _save(rows)
    _log_event({"ts": _now(), "event": "upsert", "parcel_id": pid,
                 "is_new": is_new})
    return record


def mark_stage(parcel_id: str, stage: str, note: str = "",
                channel: str = "") -> dict | None:
    """Promote (or set) a lead's funnel stage. Stamps the timestamp column.
    Records an event in funnel_history.jsonl."""
    if stage not in STAGES:
        return None
    rows = _load()
    rec = next((r for r in rows if r["parcel_id"] == parcel_id), None)
    if not rec:
        return None
    prev_stage = rec.get("stage", "cold")
    rec["stage"] = stage
    rec[f"{stage}_at"] = _now()
    if note:
        nb = rec.get("notes", "")
        rec["notes"] = (nb + " | " if nb else "") + f"{stage}: {note}"
    if stage == "reached" and channel:
        rec["last_outreach_at"] = _now()
        rec["last_outreach_channel"] = channel
        try:
            rec["outreach_count"] = str(int(rec.get("outreach_count") or 0) + 1)
        except ValueError:
            rec["outreach_count"] = "1"
    if stage == "warm" or stage == "hot":
        try:
            rec["reply_count"] = str(int(rec.get("reply_count") or 0) + 1)
        except ValueError:
            rec["reply_count"] = "1"
        rec["last_reply_at"] = _now()
        rec["last_reply_summary"] = note[:200]
    _save(rows)
    _log_event({"ts": _now(), "event": "mark_stage",
                 "parcel_id": parcel_id, "from": prev_stage, "to": stage,
                 "note": note, "channel": channel})
    return rec


def snapshot_metrics() -> dict:
    """Funnel metrics for the dashboard / Slack report."""
    rows = _load()
    counts = {s: 0 for s in STAGES}
    for r in rows:
        s = r.get("stage", "cold")
        if s in counts:
            counts[s] += 1
    total = len(rows)
    metrics = {
        "total_qualified_ever": total,
        "stages": counts,
        "current_pipeline": total - counts["closed"] - counts["rejected"]
                              - counts["dnc"],
        "conversion_rates": {},
    }
    # crude conversion rates (cumulative-style, not strict)
    if total:
        metrics["conversion_rates"]["qualified_to_reached"] = round(
            100 * (total - counts["cold"]) / total, 1)
    reached_total = total - counts["cold"]
    if reached_total:
        warm_or_better = (counts["warm"] + counts["hot"]
                           + counts["contracted"] + counts["closed"])
        metrics["conversion_rates"]["reached_to_replied"] = round(
            100 * warm_or_better / reached_total, 1)
    closed_target = counts["closed"]
    if total:
        metrics["conversion_rates"]["qualified_to_closed"] = round(
            100 * closed_target / total, 2)
    return metrics


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        print(json.dumps(snapshot_metrics(), indent=2))
    elif len(sys.argv) >= 4 and sys.argv[1] == "mark":
        result = mark_stage(sys.argv[2], sys.argv[3],
                             note=sys.argv[4] if len(sys.argv) > 4 else "")
        print(json.dumps(result, indent=2, default=str)
               if result else "(no such parcel_id)")
    else:
        print(f"funnel CSV: {FUNNEL_CSV}")
        print(f"rows: {len(_load())}")
        print(json.dumps(snapshot_metrics(), indent=2))
