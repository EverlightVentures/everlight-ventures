#!/usr/bin/env python3
"""Stopgap repair for MGN Items.csv: make every product distinguishable + searchable.

WHY: the original import flattened 986/989 product names to the literal word "Plant",
and the named source CSV is gone -- real names are NOT recoverable from data. This
synthesizes a distinguishable label from the attributes that ARE clean (Size, Category,
price, SKU), so cashiers can find items today. A proper re-import later overwrites these.

SAFE BY DESIGN:
- Backs up Items.csv -> Items.csv.bak-YYYYMMDD-HHMMSS before writing.
- Reads + writes with the file's OWN on-disk header (preserves all 26 columns; never
  drops Supplier_Barcode/QR_Code/QR_Image_Path).
- Idempotent: only touches rows whose Item_Name is the generic "Plant"/"plant"/blank;
  re-running skips already-labelled rows.
- Never touches SKU or any price column. The one all-prices-blank row is set Inactive.

Usage:  python3 repair_item_names.py [path/to/Items.csv]   (default: ../Inventory/Items.csv)
        python3 repair_item_names.py --dry-run [path]       (report only, no write)
"""
import csv
import os
import sys
from datetime import datetime

GENERIC_NAMES = {"plant", ""}


def best_price(row):
    for k in ("Retail_Price", "Default_Price", "Unit_Price"):
        v = (row.get(k) or "").strip()
        try:
            f = float(v)
            if f > 0:
                return f
        except ValueError:
            pass
    return 0.0


def is_generic(name):
    return (name or "").strip().lower() in GENERIC_NAMES


def synth_label(row):
    """Build a distinguishable, searchable label from clean attributes."""
    size = (row.get("Size") or "").strip()
    cat = (row.get("Category") or "").strip()
    price = best_price(row)
    sku = (row.get("SKU") or "").strip()
    parts = ["Plant"]
    if size:
        parts.append(size)
    elif cat and cat.lower() not in ("plant", "plants", ""):
        parts.append(cat)
    if price > 0:
        parts.append(f"${price:.2f}")
    label = " ".join(parts).strip()
    tail = sku.split("-")[-1][:6] if sku else ""
    return f"{label} ({tail})" if tail else label


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    here = os.path.dirname(os.path.abspath(__file__))
    items_path = args[0] if args else os.path.join(here, "..", "Inventory", "Items.csv")
    items_path = os.path.abspath(items_path)
    if not os.path.exists(items_path):
        print(f"ERROR: {items_path} not found", file=sys.stderr)
        return 2

    with open(items_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames  # the file's OWN header -- preserve exactly
        rows = list(reader)

    repaired = 0
    deactivated = 0
    for r in rows:
        if is_generic(r.get("Item_Name", "")):
            label = synth_label(r)
            # keep the original word so nothing is lost
            if not (r.get("Item_Description") or "").strip():
                r["Item_Description"] = (r.get("Item_Name") or "").strip()
            r["Item_Name"] = label
            r["Product_Name"] = label
            repaired += 1
        if best_price(r) <= 0 and r.get("Status", "") != "Inactive":
            r["Status"] = "Inactive"  # all-prices-blank row: keep it out of the sellable menu (reversible)
            deactivated += 1

    distinct = len({r.get("Item_Name", "") for r in rows})
    print(f"items={len(rows)} repaired={repaired} deactivated_priceless={deactivated} distinct_names_now={distinct}")
    if dry:
        print("(dry-run: no file written)")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = f"{items_path}.bak-{stamp}"
    with open(items_path, newline="", encoding="utf-8-sig") as src, open(backup, "w", newline="", encoding="utf-8") as dst:
        dst.write(src.read())
    print(f"backup -> {backup}")

    tmp = items_path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, items_path)
    print(f"wrote {items_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
