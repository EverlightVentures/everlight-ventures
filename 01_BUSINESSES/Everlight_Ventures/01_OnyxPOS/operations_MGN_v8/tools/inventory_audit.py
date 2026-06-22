#!/usr/bin/env python3
"""
inventory_audit.py -- Inventory health auditor for the Mountain Gardens (Onyx)
Flask CSV POS.

WHAT IT DOES
------------
Reads the catalog (Inventory/Items.csv) and, optionally, the sales history
(Sales_Logs/) and reports the things that quietly break a CSV point-of-sale:

  * total items in the catalog
  * rows with a blank Item_Name        (a button with no label)
  * rows with a blank or zero sell-price (rings up as $0.00)
  * rows with a blank SKU              (can't be looked up / deduped)
  * duplicate SKUs                     (two products fight over one barcode)
  * the ALIGNMENT GAP -- items that appear in the sales logs whose SKU/name
    is NOT present in Items.csv (sold something the catalog doesn't know about,
    so reorder points, COGS and margin are all blind to it)
  * a 0-100 health score + letter grade rolled up from the above

REAL SCHEMA (learned from this repo, not guessed)
-------------------------------------------------
Items.csv header (Inventory/Items.csv):
    SKU, Item_Name, Category, Subcategory, Product_Name, Default_Unit,
    Default_Price, Taxable, Reorder_Point, Date_Added, Last_Updated, Status,
    Notes, Size, Item_Description, Wholesale_Cost, Retail_Markup, Retail_Price,
    Unit_Cost, Unit_Price, Last_Invoice_No, Last_Vendor, Last_Received_Date,
    Supplier_Barcode, QR_Code, QR_Image_Path

Sales logs (POS_CORE.SALES_HEADERS) carry, among others:
    ... Product_Name, Item_Name, SKU, Quantity, Unit_Price, Line_Total ...

POS_CORE uses Default_Price as the canonical sell/retail price (see
POS_CORE.py lines 1191 / 3558 / 3631), so that is the column this auditor
treats as the "sell price".

DESIGN
------
The functions are pure and importable: parsing (reading files) is separated
from auditing (operating on already-parsed lists of dicts), so unit tests can
call audit_items() / find_alignment_gap() / build_report() on tiny in-memory
fixtures with no disk I/O.

stdlib only. No third-party imports, no eval/exec, no shell-out.

CLI
---
    python3 inventory_audit.py --items <Items.csv> [--sales <Sales_Logs dir>] [--json]
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
from collections import Counter, OrderedDict

# --- real-schema column names -------------------------------------------------
SKU_COL = "SKU"
NAME_COL = "Item_Name"
# POS_CORE treats Default_Price as the canonical sell/retail price.
PRICE_COL = "Default_Price"
# Sales-log columns we read for the alignment check (from SALES_HEADERS).
SALES_SKU_COL = "SKU"
SALES_NAME_COL = "Item_Name"
SALES_QTY_COL = "Quantity"

# Health-score weights (penalty pool, summed then subtracted from 100).
_WEIGHTS = {
    "blank_name": 25.0,
    "blank_or_zero_price": 20.0,
    "blank_sku": 20.0,
    "duplicate_sku": 20.0,
    "alignment_gap": 15.0,
}


# =============================================================================
# small pure helpers
# =============================================================================
def _s(value) -> str:
    """Normalize any cell to a stripped string ('' for None)."""
    if value is None:
        return ""
    return str(value).strip()


def _to_float(value):
    """Parse a price/qty cell to float. Returns None if blank/unparseable.

    Tolerates currency symbols, commas and surrounding spaces ('$1,234.50').
    """
    text = _s(value)
    if not text:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


# =============================================================================
# I/O (thin wrappers -- the only part that touches disk)
# =============================================================================
def read_items(path: str) -> list:
    """Read an Items.csv into a list of dict rows (one per catalog item)."""
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def read_sales(sales_dir: str) -> list:
    """Recursively read every *SalesLog*.csv / *.csv under sales_dir.

    Returns a flat list of sale-line dicts: {"sku", "name", "qty"}.
    Files that don't look like sales logs (no SKU and no Item_Name column) are
    skipped. Missing dir -> empty list.
    """
    records = []
    if not sales_dir or not os.path.isdir(sales_dir):
        return records
    for root, _dirs, files in os.walk(sales_dir):
        for fname in files:
            if not fname.lower().endswith(".csv"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", newline="", encoding="utf-8-sig") as fh:
                    reader = csv.DictReader(fh)
                    cols = reader.fieldnames or []
                    if SALES_SKU_COL not in cols and SALES_NAME_COL not in cols:
                        continue  # not a sales log
                    for row in reader:
                        sku = _s(row.get(SALES_SKU_COL))
                        name = _s(row.get(SALES_NAME_COL))
                        if not sku and not name:
                            continue
                        qty = _to_float(row.get(SALES_QTY_COL))
                        records.append(
                            {"sku": sku, "name": name, "qty": qty if qty is not None else 0.0}
                        )
            except (OSError, csv.Error):
                # A single unreadable file should not abort the whole audit.
                continue
    return records


# =============================================================================
# pure audit logic (operates on already-parsed rows -- unit-test entry points)
# =============================================================================
def audit_items(rows: list) -> dict:
    """Audit a list of catalog dict rows. Pure -- no disk I/O.

    Returns a dict with total + per-issue counts and the duplicate-SKU detail.
    """
    total = len(rows)
    blank_name = 0
    blank_or_zero_price = 0
    blank_sku = 0
    sku_counter = Counter()

    for row in rows:
        if not _s(row.get(NAME_COL)):
            blank_name += 1

        price = _to_float(row.get(PRICE_COL))
        if price is None or price == 0:
            blank_or_zero_price += 1

        sku = _s(row.get(SKU_COL))
        if not sku:
            blank_sku += 1
        else:
            sku_counter[sku] += 1

    duplicates = OrderedDict()
    duplicate_row_count = 0
    for sku, count in sku_counter.items():
        if count > 1:
            duplicates[sku] = count
            duplicate_row_count += count  # all rows sharing the SKU

    return {
        "total_items": total,
        "blank_name": blank_name,
        "blank_or_zero_price": blank_or_zero_price,
        "blank_sku": blank_sku,
        "duplicate_skus": [{"sku": s, "count": c} for s, c in duplicates.items()],
        "duplicate_sku_groups": len(duplicates),
        "duplicate_sku_row_count": duplicate_row_count,
    }


def _catalog_keys(rows: list):
    """Build the sets of known SKUs and known (casefolded) names from items."""
    known_skus = set()
    known_names = set()
    for row in rows:
        sku = _s(row.get(SKU_COL))
        if sku:
            known_skus.add(sku)
        name = _s(row.get(NAME_COL))
        if name:
            known_names.add(name.casefold())
    return known_skus, known_names


def find_alignment_gap(item_rows: list, sales_records: list) -> dict:
    """Find items sold in the logs that are NOT present in the catalog. Pure.

    A sale line is "present" if its SKU matches a catalog SKU, OR (when the
    SKU is blank/unknown) its name matches a catalog Item_Name. Anything else
    is an alignment gap. Gaps are aggregated by (sku, name) with qty + line
    counts so a thing sold 40 times shows once.
    """
    known_skus, known_names = _catalog_keys(item_rows)

    distinct_sold = set()
    gap = OrderedDict()  # (sku, name_casefold) -> {sku,name,qty_sold,lines}
    total_lines = 0

    for rec in sales_records:
        sku = _s(rec.get("sku"))
        name = _s(rec.get("name"))
        if not sku and not name:
            continue
        total_lines += 1
        distinct_sold.add((sku, name.casefold()))

        present = (sku and sku in known_skus) or (name and name.casefold() in known_names)
        if present:
            continue

        key = (sku, name.casefold())
        if key not in gap:
            gap[key] = {"sku": sku, "name": name, "qty_sold": 0.0, "lines": 0}
        qty = rec.get("qty")
        gap[key]["qty_sold"] += float(qty) if qty else 0.0
        gap[key]["lines"] += 1

    return {
        "total_sold_lines": total_lines,
        "distinct_sold_keys": len(distinct_sold),
        "alignment_gap": list(gap.values()),
        "alignment_gap_count": len(gap),
    }


def compute_health_score(item_audit: dict, sales_audit) -> float:
    """Roll the issue counts into a 0-100 score. Pure.

    Each issue contributes a weighted penalty proportional to the share of
    rows it touches; penalties sum and subtract from 100. A blank catalog
    scores 0.
    """
    total = item_audit.get("total_items", 0)
    if total <= 0:
        return 0.0

    penalty = 0.0
    penalty += _WEIGHTS["blank_name"] * (item_audit["blank_name"] / total)
    penalty += _WEIGHTS["blank_or_zero_price"] * (item_audit["blank_or_zero_price"] / total)
    penalty += _WEIGHTS["blank_sku"] * (item_audit["blank_sku"] / total)
    penalty += _WEIGHTS["duplicate_sku"] * (item_audit["duplicate_sku_row_count"] / total)

    if sales_audit:
        distinct = sales_audit.get("distinct_sold_keys", 0)
        if distinct > 0:
            gap_frac = sales_audit["alignment_gap_count"] / distinct
            penalty += _WEIGHTS["alignment_gap"] * gap_frac

    score = max(0.0, 100.0 - penalty)
    return round(score, 1)


def build_report(item_rows: list, sales_records=None,
                 items_file: str = "", sales_dir: str = "") -> dict:
    """Full audit report from already-parsed rows. Pure -- no disk I/O.

    sales_records=None means "no sales data supplied"; the sales section and
    the alignment-gap penalty are omitted.
    """
    item_audit = audit_items(item_rows)
    sales_audit = None
    if sales_records is not None:
        sales_audit = find_alignment_gap(item_rows, sales_records)

    score = compute_health_score(item_audit, sales_audit)

    report = {
        "items_file": items_file,
        "sales_dir": sales_dir or None,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "total_items": item_audit["total_items"],
        "blank_name": item_audit["blank_name"],
        "blank_or_zero_price": item_audit["blank_or_zero_price"],
        "blank_sku": item_audit["blank_sku"],
        "duplicate_sku_groups": item_audit["duplicate_sku_groups"],
        "duplicate_sku_row_count": item_audit["duplicate_sku_row_count"],
        "duplicate_skus": item_audit["duplicate_skus"],
        "sales": sales_audit,
        "health_score": score,
        "health_grade": _grade(score),
    }
    return report


# =============================================================================
# rendering
# =============================================================================
def format_report(report: dict) -> str:
    """Render a report dict as a readable plain-text block."""
    lines = []
    add = lines.append
    add("=" * 60)
    add("  ONYX POS -- INVENTORY HEALTH AUDIT")
    add("=" * 60)
    add(f"  Items file : {report.get('items_file') or '(in-memory)'}")
    add(f"  Sales dir  : {report.get('sales_dir') or '(not supplied)'}")
    add(f"  Generated  : {report.get('generated_at')}")
    add("-" * 60)
    add(f"  Total items ................ {report['total_items']}")
    add(f"  Blank Item_Name ............ {report['blank_name']}")
    add(f"  Blank / $0 sell-price ...... {report['blank_or_zero_price']}")
    add(f"  Blank SKU .................. {report['blank_sku']}")
    add(f"  Duplicate SKU groups ....... {report['duplicate_sku_groups']}"
        f"  ({report['duplicate_sku_row_count']} rows)")

    dups = report.get("duplicate_skus") or []
    if dups:
        add("    duplicates:")
        for d in dups[:15]:
            add(f"      - {d['sku']}  x{d['count']}")
        if len(dups) > 15:
            add(f"      ... and {len(dups) - 15} more")

    sales = report.get("sales")
    add("-" * 60)
    if sales is None:
        add("  Sales / alignment .......... (no Sales_Logs supplied)")
    else:
        add(f"  Sold line-items ............ {sales['total_sold_lines']}")
        add(f"  Distinct sold items ........ {sales['distinct_sold_keys']}")
        add(f"  ALIGNMENT GAP (sold, not in catalog) ... {sales['alignment_gap_count']}")
        for g in sales.get("alignment_gap", [])[:15]:
            label = g["sku"] or "(no SKU)"
            name = g["name"] or "(no name)"
            add(f"      - {label} | {name} | qty {g['qty_sold']:g} | {g['lines']} line(s)")
        if sales["alignment_gap_count"] > 15:
            add(f"      ... and {sales['alignment_gap_count'] - 15} more")

    add("-" * 60)
    add(f"  HEALTH SCORE ............... {report['health_score']} / 100  ({report['health_grade']})")
    add("=" * 60)
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================
def run(items_path: str, sales_dir: str = "") -> dict:
    """Read from disk and build the report. Thin glue over the pure layer."""
    item_rows = read_items(items_path)
    sales_records = None
    if sales_dir:
        sales_records = read_sales(sales_dir)
    return build_report(item_rows, sales_records,
                        items_file=items_path, sales_dir=sales_dir)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit inventory health for the Onyx CSV POS.")
    parser.add_argument("--items", required=True,
                        help="path to Items.csv")
    parser.add_argument("--sales", default="",
                        help="optional path to a Sales_Logs directory")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of the readable report")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.items):
        parser.error(f"items file not found: {args.items}")

    report = run(args.items, args.sales)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
