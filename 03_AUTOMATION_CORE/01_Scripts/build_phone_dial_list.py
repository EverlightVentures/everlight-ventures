"""
build_phone_dial_list.py -- Generate Tuesday + Wednesday phone dial CSVs.

Reads leads_db.json (post-scoring), filters to GA/TX phone-only leads, splits
into daily 32-row CSVs for Marquise to dial Tuesday (ATL) + Wednesday (DFW).

Per Piper's hard rule: 32/day max. No 64-in-one-sitting.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def is_atl_metro(addr: str, city: str, state: str) -> bool:
    """Loose match -- if state is GA we treat it as ATL metro for dialing purposes
    (we don't have many GA leads outside ATL anyway). Address text fallback when city missing."""
    a = (addr or "").upper()
    c = (city or "").upper()
    s = (state or "").upper()
    if c in {"ATLANTA", "MARIETTA", "DECATUR", "SANDY SPRINGS", "BUCKHEAD",
             "ALPHARETTA", "ROSWELL", "SMYRNA", "TUCKER", "EAST POINT",
             "FOREST PARK", "STONE MOUNTAIN", "LITHONIA", "KENNESAW"}:
        return True
    if any(m in a for m in ("ATLANTA", "MARIETTA", "DECATUR", "SANDY SPRINGS", "ROSWELL", "ALPHARETTA")):
        return True
    return s == "GA"  # Default GA -> ATL queue


def is_dfw_metro(addr: str, city: str, state: str) -> bool:
    a = (addr or "").upper()
    c = (city or "").upper()
    s = (state or "").upper()
    if c in {"DALLAS", "FORT WORTH", "FORTWORTH", "PLANO", "FRISCO", "ARLINGTON",
             "IRVING", "GRAND PRAIRIE", "GARLAND", "MESQUITE", "CARROLLTON",
             "RICHARDSON", "ROWLETT", "DENTON", "LEWISVILLE", "EULESS"}:
        return True
    if any(m in a for m in ("DALLAS", "FORT WORTH", "PLANO", "FRISCO", "ARLINGTON",
                             "IRVING", "GARLAND", "RICHARDSON")):
        return True
    return s == "TX"  # Default TX -> DFW queue


def main():
    db_path = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/leads_db.json")
    if not db_path.exists():
        print(f"FATAL: {db_path} not found", file=sys.stderr)
        sys.exit(1)

    leads = json.loads(db_path.read_text())

    # Justine auto-block (5 categories cold first-touch):
    #   1. LLC/entity owners
    #   2. Realty/agent businesses
    #   3. Bank-owned REO / servicer-held
    #   4. Trust with institutional fiduciary
    #   5. Active-litigation parcels
    LLC_SIGNALS = (" LLC", " INC", " CORP", " LP ", " LTD", " COMPANY",
                   " INVESTMENTS", " PROPERTIES", " HOLDINGS", " HLDGS",
                   " REALTY", " REAL ESTATE", " HOMES ", "REALTY SERVICES",
                   " GROUP", " CONTRACTOR", " CONTRACTORS")
    REO_SIGNALS = ("REO", "FANNIE", "FREDDIE", "WELLS FARGO", "BANK OF AMERICA",
                   "JPMORGAN", "CHASE BANK", "DEUTSCHE", "HUD ", "FREDDIE MAC",
                   "FANNIE MAE", "U S BANK", "U.S. BANK")
    GENERIC_SIGNALS = ("PROPERTY OWNER", "OWNER OF RECORD", "CURRENT OWNER", "UNKNOWN")

    def auto_block_reason(name: str) -> str:
        n = (name or "").upper()
        if not n:
            return "no-owner-name"
        if any(s in n for s in REO_SIGNALS):
            return "REO_or_servicer"
        if any(s in n for s in LLC_SIGNALS):
            return "LLC_or_business"
        if "TRUST" in n and ("INSTITUTIONAL" in n or "BANK" in n or "TRUSTEE OF" in n):
            return "institutional_trust"
        if any(s == n.strip() for s in GENERIC_SIGNALS):
            return "generic_placeholder"
        return ""

    # Filter: GA or TX, phone-only, status='new', no prior contact, has phone, not auto-blocked.
    phone_eligible = []
    blocked = []
    for l in leads:
        if l.get("queue") != "phone":
            continue
        if (l.get("state") or "").upper() not in {"GA", "TX"}:
            continue
        if l.get("status") != "new":
            continue
        if l.get("last_contacted"):
            continue
        if not (l.get("owner_phone") or l.get("phone")):
            continue
        block_reason = auto_block_reason(l.get("owner_name") or l.get("first_name") or "")
        if block_reason:
            l["_block_reason"] = block_reason
            blocked.append(l)
            continue
        phone_eligible.append(l)
    phone_eligible.sort(key=lambda l: l.get("score", 0), reverse=True)

    # State-based split: GA -> ATL queue, TX -> DFW queue. Cleaner than substring matching.
    atl = [l for l in phone_eligible if (l.get("state") or "").upper() == "GA"][:32]
    dfw = [l for l in phone_eligible if (l.get("state") or "").upper() == "TX"][:32]

    # Output dir
    data_dir = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Tuesday = ATL, Wednesday = DFW
    today = datetime.now()
    tuesday = today + timedelta(days=(1 - today.weekday()) % 7)  # next Tuesday
    wednesday = tuesday + timedelta(days=1)

    columns = ["row", "lead_id", "score", "owner_name", "owner_phone", "address", "city", "state", "lead_type", "outcome", "notes"]

    def write_csv(path: Path, leads_list, header_note: str):
        with open(path, "w", newline="") as f:
            f.write(f"# {header_note}\n")
            f.write(f"# Outcomes: talked | vm | dnc | wrong# | callback | voicemail_dropped\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            w = csv.DictWriter(f, fieldnames=columns)
            w.writeheader()
            for i, l in enumerate(leads_list, 1):
                w.writerow({
                    "row": i,
                    "lead_id": l.get("django_lead_id") or l.get("address", "")[:40],
                    "score": l.get("score", 0),
                    "owner_name": l.get("owner_name", ""),
                    "owner_phone": l.get("owner_phone") or l.get("phone", ""),
                    "address": l.get("address", ""),
                    "city": l.get("city", ""),
                    "state": l.get("state", ""),
                    "lead_type": l.get("lead_type", ""),
                    "outcome": "",
                    "notes": "",
                })

    atl_path = data_dir / f"dial_list_ATL_{tuesday.strftime('%Y-%m-%d')}.csv"
    dfw_path = data_dir / f"dial_list_DFW_{wednesday.strftime('%Y-%m-%d')}.csv"

    write_csv(atl_path, atl, f"ATL DIAL LIST -- TUESDAY {tuesday.strftime('%Y-%m-%d')} -- {len(atl)} leads")
    write_csv(dfw_path, dfw, f"DFW DIAL LIST -- WEDNESDAY {wednesday.strftime('%Y-%m-%d')} -- {len(dfw)} leads")

    # Also a combined live phone_only_leads.csv that Piper SOP references
    live_path = data_dir / "phone_only_leads.csv"
    write_csv(live_path, phone_eligible[:64], f"COMBINED PHONE-ONLY ATL+DFW -- {len(phone_eligible[:64])} leads -- top by score")

    # Dial log -- create if not exists
    dial_log = data_dir / "dial_log.csv"
    if not dial_log.exists():
        with open(dial_log, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_pt", "lead_id", "owner_name", "phone", "outcome", "notes"])

    print(f"Phone-eligible leads (GA+TX, phone-only, status=new, Justine-cleared): {len(phone_eligible)}")
    print(f"Auto-blocked by Justine compliance gate: {len(blocked)}")
    if blocked:
        block_reasons = {}
        for b in blocked:
            r = b.get("_block_reason", "?")
            block_reasons[r] = block_reasons.get(r, 0) + 1
        for r, c in sorted(block_reasons.items(), key=lambda x: -x[1]):
            print(f"  {r}: {c}")
    print(f"  ATL split: {len(atl)} -> {atl_path}")
    print(f"  DFW split: {len(dfw)} -> {dfw_path}")
    print(f"  Combined: {min(64, len(phone_eligible))} -> {live_path}")
    print(f"  Dial log: {dial_log}")

    if len(atl) < 32:
        print(f"\n  WARNING: ATL has only {len(atl)} leads (target 32). Need lead-supply enrichment.")
    if len(dfw) < 32:
        print(f"  WARNING: DFW has only {len(dfw)} leads (target 32). Need lead-supply enrichment.")


if __name__ == "__main__":
    main()
