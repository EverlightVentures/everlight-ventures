#!/usr/bin/env python3
"""
migrate_buyers_to_db.py -- one-shot import of buyers_db.json into the
broker_ops.InvestorBuyer table.

Reason: 84 cash buyers were sitting in a flat JSON file at
Broker_OS/wholesale_agent/buyers_db.json since 2026-03-20. The Django
dashboard reads from the InvestorBuyer table, which had 0 rows. Result:
the buyer-matching engine had no buyers to match against.

This script:
  1. Reads the JSON
  2. For each buyer, upsert into InvestorBuyer keyed on email (or phone if
     email is missing). Existing rows get updated, new ones get created.
  3. Logs counts.

Run on Oracle: python3 /home/opc/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/migrate_buyers_to_db.py
Run on phone : cd /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard &&
               python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/migrate_buyers_to_db.py

Idempotent. Safe to run multiple times.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Auto-detect Django project root.
HERE = Path(__file__).resolve().parent
candidates = [
    Path("/home/opc/hive_django"),
    HERE.parent.parent / "09_DASHBOARD" / "hive_dashboard",
    Path("/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"),
]
for c in candidates:
    if (c / "manage.py").exists():
        sys.path.insert(0, str(c))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        break
else:
    print("Could not find Django project. Aborting.", file=sys.stderr)
    sys.exit(1)

import django  # noqa: E402

django.setup()

from broker_ops.models import InvestorBuyer  # noqa: E402

# Locate the JSON.
JSON_CANDIDATES = [
    Path("/home/opc/wholesale_agent/buyers_db.json"),
    Path("/home/opc/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/buyers_db.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent/buyers_db.json"),
]
src = next((p for p in JSON_CANDIDATES if p.exists()), None)
if not src:
    print(f"buyers_db.json not found in any of {JSON_CANDIDATES}", file=sys.stderr)
    sys.exit(2)

buyers = json.loads(src.read_text())
if isinstance(buyers, dict):
    # support either dict-of-lists or flat dict
    buyers = list(buyers.values()) if all(isinstance(v, dict) for v in buyers.values()) else [buyers]

print(f"Source: {src}")
print(f"Buyers in JSON: {len(buyers)}")

# What columns does InvestorBuyer expose?
field_names = {f.name for f in InvestorBuyer._meta.get_fields() if hasattr(f, "name")}
print(f"InvestorBuyer fields: {sorted(field_names)}")

created = 0
updated = 0
skipped = 0

for b in buyers:
    if not isinstance(b, dict):
        skipped += 1
        continue
    email = (b.get("email") or "").strip().lower()
    phone = (b.get("phone") or "").strip()
    if not email and not phone:
        skipped += 1
        continue

    # Build kwargs by intersecting JSON keys with model fields.
    payload = {}
    mapping = {
        "name": "name",
        "company": "company",
        "email": "email",
        "phone": "phone",
        "city": "city",
        "state": "state",
        "market": "market",
        "buy_criteria": "buy_criteria",
        "max_offer": "max_offer",
        "deals_closed": "deals_closed",
        "responded": "responded",
    }
    for jk, fk in mapping.items():
        if fk in field_names and b.get(jk) is not None:
            payload[fk] = b[jk]

    lookup = {"email": email} if email else {"phone": phone}
    obj, was_created = InvestorBuyer.objects.update_or_create(
        defaults=payload, **lookup
    )
    if was_created:
        created += 1
    else:
        updated += 1

print(f"Created: {created}")
print(f"Updated: {updated}")
print(f"Skipped (no email and no phone): {skipped}")
print(f"Final InvestorBuyer count: {InvestorBuyer.objects.count()}")
