"""
Mountain Gardens POS — Invoice Importer (v2)
Writes invoice lines into Inventory/Items.csv (upsert) and optionally Inventory/Lots.csv,
while also logging invoice headers/lines for reporting.

Key behavior:
- Items.csv schema is auto-upgraded to include invoice + sales-metadata columns.
- Retail_Price = Wholesale_Cost * retail_markup (default 2.25)
- Default_Price is set to Retail_Price so the POS terminal pulls the retail price.
- Also sets Unit_Price/Unit_Cost mirrors to match Sales log column naming.
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------- Paths ----------

def _base_dir() -> Path:
    return Path(__file__).resolve().parent

def inventory_dir() -> Path:
    return _base_dir() / "Inventory"

def items_path() -> Path:
    return inventory_dir() / "Items.csv"

def lots_path() -> Path:
    return inventory_dir() / "Lots.csv"

def invoices_log_path() -> Path:
    return inventory_dir() / "Invoices_Log.csv"

def invoice_lines_log_path() -> Path:
    return inventory_dir() / "Invoice_Lines.csv"


# ---------- CSV helpers ----------

def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def ensure_csv(path: Path, headers: List[str]) -> None:
    _ensure_parent(path)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()
        return

    # Upgrade header if missing columns
    with open(path, "r", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        try:
            existing = next(r)
        except StopIteration:
            existing = []

    missing = [h for h in headers if h not in existing]
    if not missing:
        return

    new_headers = existing + missing
    rows = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        dr = csv.DictReader(f)
        for row in dr:
            rows.append(row)

    with open(path, "w", newline="", encoding="utf-8") as f:
        dw = csv.DictWriter(f, fieldnames=new_headers)
        dw.writeheader()
        for row in rows:
            dw.writerow(row)


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        dr = csv.DictReader(f)
        return list(dr)

def write_csv_dicts(path: Path, headers: List[str], rows: List[Dict[str, str]]) -> None:
    ensure_csv(path, headers)
    with open(path, "w", newline="", encoding="utf-8") as f:
        dw = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        dw.writeheader()
        for row in rows:
            dw.writerow(row)

def append_row(path: Path, headers: List[str], row: Dict[str, str]) -> None:
    ensure_csv(path, headers)
    with open(path, "a", newline="", encoding="utf-8") as f:
        dw = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        dw.writerow(row)


# ---------- Schema ----------

# Baseline columns already in your Items.csv today + the added invoice/sales-metadata fields.
REQUIRED_ITEM_HEADERS = [
    "SKU", "Item_Name", "Category", "Subcategory", "Product_Name",
    "Default_Unit", "Default_Price", "Taxable", "Reorder_Point",
    "Date_Added", "Last_Updated", "Status", "Notes",

    # Sales-metadata columns that map cleanly to your SALES_HEADERS naming
    "Size", "Item_Description",

    # Invoice/pricing columns
    "Wholesale_Cost", "Retail_Markup", "Retail_Price",

    # Mirrors to match Sales log naming (helps avoid "what is unit price?" confusion)
    "Unit_Cost", "Unit_Price",

    # Last invoice reference
    "Last_Invoice_No", "Last_Vendor", "Last_Received_Date",
]

LOT_HEADERS = ["Lot_ID", "SKU", "Received_Date", "Supplier", "Invoice_Ref",
               "Qty_Received", "Unit_Cost", "Qty_Remaining", "Expiry_Date", "Notes"]

INVOICE_LOG_HEADERS = [
    "Invoice_ID", "Invoice_No", "Vendor", "Received_Date",
    "Line_Count", "Invoice_Subtotal", "Invoice_Total",
    "Retail_Markup", "Imported_At", "Source_File",
]

INVOICE_LINE_HEADERS = [
    "Invoice_ID", "Invoice_No", "Vendor", "Received_Date",
    "Line_No", "SKU", "Item_Name", "Category", "Subcategory", "Product_Name",
    "Size", "Item_Description",
    "Qty", "Wholesale_Cost", "Retail_Markup", "Retail_Price",
    "Line_Wholesale_Total", "Line_Retail_Total",
]


# ---------- Column mapping ----------

def _pick(row: Dict[str, str], *candidates: str) -> str:
    for k in candidates:
        if k in row and str(row.get(k, "")).strip() != "":
            return str(row.get(k, "")).strip()
    # try case-insensitive match
    lower = {k.lower(): k for k in row.keys()}
    for c in candidates:
        key = lower.get(c.lower())
        if key and str(row.get(key, "")).strip() != "":
            return str(row.get(key, "")).strip()
    return ""

def _to_float(x: str, default: float = 0.0) -> float:
    try:
        return float(str(x).replace("$", "").replace(",", "").strip())
    except Exception:
        return default

def _to_int(x: str, default: int = 0) -> int:
    try:
        return int(float(str(x).strip()))
    except Exception:
        return default

def _round2(x: float) -> float:
    return float(f"{x:.2f}")


@dataclass
class ImportResult:
    ok: bool
    created: int = 0
    updated: int = 0
    lots_created: int = 0
    invoice_subtotal: float = 0.0
    invoice_total: float = 0.0
    invoice_id: str = ""
    errors: List[str] = None

    def as_dict(self) -> Dict:
        return {
            "ok": self.ok,
            "created": self.created,
            "updated": self.updated,
            "lots_created": self.lots_created,
            "invoice_subtotal": _round2(self.invoice_subtotal),
            "invoice_total": _round2(self.invoice_total),
            "invoice_id": self.invoice_id,
            "errors": self.errors or [],
        }


def import_invoice_csv(
    csv_path: str,
    invoice_no: Optional[str] = None,
    vendor: Optional[str] = None,
    received_date: Optional[str] = None,
    delimiter: str = ",",
    update_wholesale_cost: bool = True,
    create_lots: bool = True,
    retail_markup: float = 2.25,
    invoice_total: Optional[float] = None,
) -> Dict:
    """
    Import a vendor invoice CSV and upsert into Items.csv.

    Your invoice file can have flexible headers; we attempt to map:
    - SKU: SKU, sku, Item Code, Product Code
    - Item name: Item_Name, Item, Name, Description
    - Qty: Quantity, Qty, Units, Qty_Received
    - Cost: Unit_Cost, Unit Cost, Cost, Wholesale_Cost
    - Category/Subcategory/Product_Name/Size/Item_Description if present
    """

    result = ImportResult(ok=False, errors=[])

    src = Path(csv_path)
    if not src.exists():
        result.errors.append(f"CSV not found: {csv_path}")
        return result.as_dict()

    inv_dir = inventory_dir()
    inv_dir.mkdir(parents=True, exist_ok=True)

    # Ensure schemas exist/upgraded
    ensure_csv(items_path(), REQUIRED_ITEM_HEADERS)
    ensure_csv(lots_path(), LOT_HEADERS)
    ensure_csv(invoices_log_path(), INVOICE_LOG_HEADERS)
    ensure_csv(invoice_lines_log_path(), INVOICE_LINE_HEADERS)

    items = read_csv_dicts(items_path())
    items_by_sku = {i.get("SKU", "").strip(): i for i in items if i.get("SKU", "").strip()}

    inv_id = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    result.invoice_id = inv_id

    inv_no = (invoice_no or "").strip() or inv_id
    vend = (vendor or "").strip()
    rcv = (received_date or "").strip() or date.today().isoformat()

    line_no = 0
    subtotal = 0.0
    retail_total = 0.0
    lots_created = 0
    created = 0
    updated = 0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read invoice lines
    with open(src, "r", newline="", encoding="utf-8") as f:
        dr = csv.DictReader(f, delimiter=delimiter)
        if not dr.fieldnames:
            result.errors.append("Invoice CSV has no header row.")
            return result.as_dict()

        for raw in dr:
            line_no += 1

            sku = _pick(raw, "SKU", "sku", "Item SKU", "Item Code", "Product Code", "Code").strip()
            name = _pick(raw, "Item_Name", "Item Name", "Item", "Name", "Description", "Product").strip()
            category = _pick(raw, "Category", "Dept", "Department").strip()
            subcategory = _pick(raw, "Subcategory", "Sub Category", "Sub-Category").strip()
            product_name = _pick(raw, "Product_Name", "Product Name", "Product").strip()

            size = _pick(raw, "Size", "Pack", "UOM", "Unit", "Unit Size").strip()
            item_desc = _pick(raw, "Item_Description", "Item Description", "Description", "Notes").strip()

            qty = _to_int(_pick(raw, "Quantity", "Qty", "QTY", "Units", "Qty_Received", "Received"), default=1)

            unit_cost = _to_float(_pick(raw, "Unit_Cost", "Unit Cost", "Cost", "Wholesale_Cost", "Wholesale Cost", "UnitPrice", "Unit Price"), default=0.0)
            if unit_cost <= 0:
                # Skip lines that cannot price; still log error but keep going
                result.errors.append(f"Line {line_no}: missing/invalid Unit_Cost for SKU={sku or '?'}")
                continue

            wholesale_total = unit_cost * qty
            subtotal += wholesale_total

            rp = _round2(unit_cost * float(retail_markup))
            retail_line_total = rp * qty
            retail_total += retail_line_total

            # Upsert Items.csv
            if not sku:
                # We need a stable SKU
                sku = f"GEN-{uuid.uuid4().hex[:8].upper()}"

            existing = items_by_sku.get(sku)
            if not existing:
                created += 1
                row = {h: "" for h in REQUIRED_ITEM_HEADERS}
                row.update({
                    "SKU": sku,
                    "Item_Name": name or sku,
                    "Category": category,
                    "Subcategory": subcategory,
                    "Product_Name": product_name or (name or sku),
                    "Default_Unit": "each",
                    "Taxable": "Y",
                    "Reorder_Point": "5",
                    "Date_Added": now_str,
                    "Last_Updated": now_str,
                    "Status": "Active",
                    "Notes": "Imported from invoice",
                })
            else:
                updated += 1
                row = existing.copy()
                row["Last_Updated"] = now_str
                # only overwrite names/categories if invoice supplies them
                if name:
                    row["Item_Name"] = name
                if category:
                    row["Category"] = category
                if subcategory:
                    row["Subcategory"] = subcategory
                if product_name:
                    row["Product_Name"] = product_name

            # Always keep these aligned for Sales log compatibility
            row["Size"] = size or row.get("Size", "")
            row["Item_Description"] = item_desc or row.get("Item_Description", "")

            if update_wholesale_cost:
                row["Wholesale_Cost"] = f"{unit_cost:.2f}"
                row["Unit_Cost"] = f"{unit_cost:.2f}"

            row["Retail_Markup"] = f"{float(retail_markup):.2f}"
            row["Retail_Price"] = f"{rp:.2f}"
            row["Unit_Price"] = f"{rp:.2f}"

            # POS terminal pricing
            row["Default_Price"] = f"{rp:.2f}"

            # Invoice traceability
            row["Last_Invoice_No"] = inv_no
            row["Last_Vendor"] = vend
            row["Last_Received_Date"] = rcv

            # Save back
            items_by_sku[sku] = row

            # Lots
            if create_lots and qty > 0:
                lots_created += 1
                lot_row = {
                    "Lot_ID": f"LOT-{uuid.uuid4().hex[:10].upper()}",
                    "SKU": sku,
                    "Received_Date": rcv,
                    "Supplier": vend,
                    "Invoice_Ref": inv_no,
                    "Qty_Received": str(qty),
                    "Unit_Cost": f"{unit_cost:.2f}",
                    "Qty_Remaining": str(qty),
                    "Expiry_Date": "",
                    "Notes": f"Imported from invoice line {line_no}",
                }
                append_row(lots_path(), LOT_HEADERS, lot_row)

            # Log invoice line
            append_row(
                invoice_lines_log_path(),
                INVOICE_LINE_HEADERS,
                {
                    "Invoice_ID": inv_id,
                    "Invoice_No": inv_no,
                    "Vendor": vend,
                    "Received_Date": rcv,
                    "Line_No": str(line_no),
                    "SKU": sku,
                    "Item_Name": name or sku,
                    "Category": category,
                    "Subcategory": subcategory,
                    "Product_Name": product_name or (name or sku),
                    "Size": size,
                    "Item_Description": item_desc,
                    "Qty": str(qty),
                    "Wholesale_Cost": f"{unit_cost:.2f}",
                    "Retail_Markup": f"{float(retail_markup):.2f}",
                    "Retail_Price": f"{rp:.2f}",
                    "Line_Wholesale_Total": f"{wholesale_total:.2f}",
                    "Line_Retail_Total": f"{retail_line_total:.2f}",
                }
            )

    # Commit Items.csv rewrite
    new_headers = REQUIRED_ITEM_HEADERS[:]  # ensure order
    write_csv_dicts(items_path(), new_headers, list(items_by_sku.values()))

    # Totals
    result.invoice_subtotal = _round2(subtotal)
    result.invoice_total = _round2(invoice_total if invoice_total is not None else subtotal)
    result.lots_created = lots_created
    result.created = created
    result.updated = updated

    # Log invoice header
    append_row(
        invoices_log_path(),
        INVOICE_LOG_HEADERS,
        {
            "Invoice_ID": inv_id,
            "Invoice_No": inv_no,
            "Vendor": vend,
            "Received_Date": rcv,
            "Line_Count": str(line_no),
            "Invoice_Subtotal": f"{result.invoice_subtotal:.2f}",
            "Invoice_Total": f"{result.invoice_total:.2f}",
            "Retail_Markup": f"{float(retail_markup):.2f}",
            "Imported_At": now_str,
            "Source_File": src.name,
        }
    )

    result.ok = True if (created + updated) > 0 else False
    return result.as_dict()
