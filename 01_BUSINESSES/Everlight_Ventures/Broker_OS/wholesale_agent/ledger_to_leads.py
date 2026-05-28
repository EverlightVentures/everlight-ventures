"""
ledger_to_leads.py -- apply harvester ledger entries to the phone leads_db.

Reads `_logs/enrichment/assessor_harvester_e5.jsonl` (rsync'd from E5),
matches each ok-status row to a lead in leads_db (by lead_id), and writes
back owner_name + parcel_id + enrichment_stage + enrichment_at. Additive
only -- never clobbers existing fields, only fills empties.

Idempotent: each line has a Message-ID-like (ts+lead_id) dedup signature
tracked in `_logs/enrichment/ledger_applied.json` so re-runs are safe.

Usage:
    python3 ledger_to_leads.py                       # apply default ledger
    python3 ledger_to_leads.py --ledger /path/x.jsonl
    python3 ledger_to_leads.py --dry-run
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEADS_DB = HERE / "leads_db.json"
DEFAULT_LEDGER = HERE.parent.parent.parent.parent / "_logs" / "enrichment" / "assessor_harvester_e5.jsonl"
APPLIED = HERE.parent.parent.parent.parent / "_logs" / "enrichment" / "ledger_applied.json"


def _load_applied() -> set[str]:
    try:
        return set(json.loads(APPLIED.read_text()))
    except Exception:
        return set()


def _save_applied(s: set[str]) -> None:
    APPLIED.parent.mkdir(parents=True, exist_ok=True)
    APPLIED.write_text(json.dumps(sorted(s)))


def _sig(entry: dict) -> str:
    return f"{entry.get('ts','')}|{entry.get('lead_id','')}|{entry.get('owner_name','')}"


def apply(ledger_path: Path, dry_run: bool = False) -> dict:
    if not ledger_path.exists():
        return {"ok": False, "reason": f"ledger not found: {ledger_path}"}
    leads = json.loads(LEADS_DB.read_text())
    if isinstance(leads, dict):
        leads_list = list(leads.values()); was_dict = True
    else:
        leads_list = leads; was_dict = False
    # Phone leads can be keyed by lead_id / id / parcel_id depending on source.
    # Build a lookup that hits any of the three so the ledger's lead_id matches.
    by_id: dict[str, dict] = {}
    for l in leads_list:
        if not isinstance(l, dict):
            continue
        for k in ("lead_id", "id", "parcel_id"):
            v = str(l.get(k) or "").strip()
            if v:
                by_id.setdefault(v, l)
    applied = _load_applied()
    updated = 0
    skipped_seen = 0
    no_match = 0
    ts_now = datetime.now(timezone.utc).isoformat()
    for line in ledger_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("status") != "ok":
            continue
        sig = _sig(row)
        if sig in applied:
            skipped_seen += 1
            continue
        lid = str(row.get("lead_id", ""))
        lead = by_id.get(lid)
        if not lead:
            no_match += 1
            continue
        if not lead.get("owner_name"):
            lead["owner_name"] = row.get("owner_name", "")
        if not lead.get("parcel_id"):
            lead["parcel_id"] = row.get("parcel_id", "")
        if not lead.get("property_location_assessor"):
            lead["property_location_assessor"] = row.get("property_location") or row.get("address", "")
        lead["enrichment_stage"] = "assessor_done"
        lead.setdefault("enrichment_at", ts_now)
        if row.get("match_quality"):
            lead["assessor_match_quality"] = row["match_quality"]
        updated += 1
        applied.add(sig)
    if dry_run:
        return {"ok": True, "dry_run": True, "would_update": updated,
                "skipped_already_applied": skipped_seen, "no_lead_match": no_match}
    LEADS_DB.write_text(json.dumps(leads_list if not was_dict else
                                    {str(l.get("lead_id","")): l for l in leads_list},
                                    indent=2, default=str))
    _save_applied(applied)
    return {"ok": True, "updated": updated,
            "skipped_already_applied": skipped_seen, "no_lead_match": no_match}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    print(json.dumps(apply(Path(args.ledger), dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
