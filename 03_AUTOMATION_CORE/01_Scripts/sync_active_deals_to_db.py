#!/usr/bin/env python3
"""
sync_active_deals_to_db.py -- bridge active_deals/*.json into Django.

Why this exists:
  rex_negotiator.py writes deal state and seller conversations as JSON files
  in /home/opc/wholesale_agent/active_deals/. The dashboard at :8504 reads
  from the Django DB. Without this bridge, the dashboard is blind to actual
  reply traffic. Marquise sees an empty deal pipeline even when Rex is
  reading replies and replying back.

What it does:
  1. Walks active_deals/*.json
  2. For each, finds or creates the PropertyLead by (address, city, state).
     (If no PropertyLead can be matched, creates a minimal stub.)
  3. Finds or creates the Deal row, keyed on a stable hash of address+state
     stored in Deal.notes for de-dup.
  4. Walks the conversation array, creates DealEvent rows for any entry
     not already in the DB (deduped on the conversation timestamp).

Run as systemd timer every 5 min:  sync-deals.timer

Idempotent. Safe to run hot.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("sync_deals")

# Bootstrap Django.
DJANGO_ROOT = "/home/opc/hive_django"
if not Path(DJANGO_ROOT).exists():
    DJANGO_ROOT = "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"
sys.path.insert(0, DJANGO_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django  # noqa: E402

django.setup()

from broker_ops.models import Deal, DealEvent, PropertyLead  # noqa: E402

ACTIVE_DEALS_DIRS = [
    Path("/home/opc/wholesale_agent/active_deals"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/active_deals"),
]


def stable_id(address: str, state: str) -> str:
    raw = f"{address}|{state}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def upsert_lead(deal_data: dict) -> PropertyLead | None:
    """Find or create the PropertyLead matching this deal."""
    addr = (deal_data.get("address") or "").strip()
    city = (deal_data.get("city") or "").strip()
    state = (deal_data.get("state") or "").strip()
    if not addr:
        return None

    qs = PropertyLead.objects.filter(address__iexact=addr)
    if state:
        qs = qs.filter(state__iexact=state)
    lead = qs.first()
    if lead:
        return lead

    payload = {
        "address": addr,
        "state": state or "",
    }
    if "city" in {f.name for f in PropertyLead._meta.get_fields() if hasattr(f, "name")}:
        payload["city"] = city
    if "name" in {f.name for f in PropertyLead._meta.get_fields() if hasattr(f, "name")}:
        payload["name"] = deal_data.get("owner_name") or ""
    if "email" in {f.name for f in PropertyLead._meta.get_fields() if hasattr(f, "name")}:
        payload["email"] = deal_data.get("owner_email") or ""
    if "phone" in {f.name for f in PropertyLead._meta.get_fields() if hasattr(f, "name")}:
        payload["phone"] = deal_data.get("owner_phone") or ""
    if "source" in {f.name for f in PropertyLead._meta.get_fields() if hasattr(f, "name")}:
        payload["source"] = "rex_negotiator"

    try:
        return PropertyLead.objects.create(**payload)
    except Exception as exc:
        log.warning(f"could not create PropertyLead for {addr}: {exc}")
        return None


def upsert_deal(deal_data: dict, lead: PropertyLead | None) -> Deal | None:
    """Find or create the Deal. Idempotent via stable hash stored in notes."""
    addr = (deal_data.get("address") or "").strip()
    state = (deal_data.get("state") or "").strip()
    if not addr:
        return None
    sid = stable_id(addr, state)
    marker = f"[rex_sid:{sid}]"

    deal = Deal.objects.filter(notes__icontains=marker).first()
    if deal:
        return deal

    fields = {f.name for f in Deal._meta.get_fields() if hasattr(f, "name")}

    payload = {}
    if "lead" in fields and lead is not None:
        payload["lead"] = lead
    if "stage" in fields:
        payload["stage"] = deal_data.get("status", "outreach_sent")
    if "notes" in fields:
        payload["notes"] = (
            f"{marker}\nRex deal id: {deal_data.get('id','')}\n"
            f"Address: {addr}, {deal_data.get('city','')} {state}"
        )
    if "deal_value" in fields and deal_data.get("offer_price"):
        try:
            payload["deal_value"] = float(deal_data["offer_price"])
        except (TypeError, ValueError):
            pass

    try:
        return Deal.objects.create(**payload)
    except Exception as exc:
        log.warning(f"could not create Deal for {addr}: {exc}")
        return None


def upsert_events(deal: Deal, conversation: list[dict]) -> int:
    """Create DealEvent rows for conversation entries not yet in DB."""
    if not deal:
        return 0
    existing = set(
        DealEvent.objects.filter(deal=deal).values_list("metadata", flat=True)
    )
    existing_ts = set()
    for md in existing:
        if isinstance(md, dict) and md.get("conv_ts"):
            existing_ts.add(md["conv_ts"])

    created = 0
    for entry in conversation or []:
        ts = entry.get("timestamp", "")
        if not ts or ts in existing_ts:
            continue
        role = entry.get("role", "?")
        msg = entry.get("message", "")
        DealEvent.objects.create(
            deal=deal,
            event_type=f"{role}_message",
            title=f"{role.title()} message",
            detail=msg[:2000],
            agent_name="Rex Negotiator" if role == "agent" else role.title(),
            metadata={"conv_ts": ts, "source": "active_deals_sync"},
        )
        created += 1
    return created


def sync_one(json_path: Path) -> tuple[int, int]:
    """Returns (deals_touched, events_created)."""
    try:
        data = json.loads(json_path.read_text())
    except Exception as exc:
        log.warning(f"bad json {json_path.name}: {exc}")
        return (0, 0)

    lead = upsert_lead(data)
    deal = upsert_deal(data, lead)
    events = upsert_events(deal, data.get("conversation", []))
    return (1 if deal else 0, events)


def main():
    src_dir = next((p for p in ACTIVE_DEALS_DIRS if p.exists()), None)
    if not src_dir:
        log.info("no active_deals dir found, nothing to sync")
        return 0

    files = sorted(src_dir.glob("*.json"))
    log.info(f"scanning {src_dir}: {len(files)} json files")

    total_deals = 0
    total_events = 0
    for f in files:
        d, e = sync_one(f)
        total_deals += d
        total_events += e

    log.info(f"deals touched: {total_deals}  events created: {total_events}")
    log.info(f"DB totals -- Deal: {Deal.objects.count()}  DealEvent: {DealEvent.objects.count()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
