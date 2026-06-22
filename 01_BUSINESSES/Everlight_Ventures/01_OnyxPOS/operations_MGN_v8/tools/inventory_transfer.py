#!/usr/bin/env python3
"""
inventory_transfer.py -- Universal inventory CSV transfer / auto-format tool
for the Mountain Gardens Nursery (Onyx POS) inventory.

WHAT IT DOES
------------
Converts the Onyx/Mountain Gardens (MGN) inventory CSV to and from the import
formats used by Square, Shopify, and QuickBooks Online -- in either direction.
You can take a Square export and load it into MGN, take MGN and hand it to
Shopify, etc. One tool, every direction.

THE CANONICAL MODEL (the "hub" every format passes through)
-----------------------------------------------------------
Every importer parses its platform's CSV into a list of identical "canonical
product" dicts. Every exporter renders that same canonical list back out into a
target platform's columns. Because everything funnels through one neutral shape,
adding a new platform later only means writing one importer + one exporter -- not
N*N direct converters.

A canonical product is a plain dict with exactly these keys:

    sku                str   stock-keeping unit / unique id
    name               str   item / product name
    category           str   product category (e.g. "Plant", "Supply")
    description         str   long description
    price              float retail / sales price (>= 0)
    cost               float wholesale / purchase cost (>= 0)
    quantity_on_hand   int   units in stock
    barcode            str   UPC / GTIN / supplier barcode
    vendor             str   supplier / vendor name
    taxable            bool  whether sales tax applies
    unit               str   unit of measure (e.g. "each", "2 gal")

A note on MGN stock-on-hand: the real Onyx schema keeps current stock in the
LOT ledger (Inventory/Lots.csv `Qty_Remaining`, summed per SKU, with movements
in Inventory/Ledger.csv `Delta_Qty`) -- NOT in Items.csv, which carries the
catalog (price/cost/category) plus a `Reorder_Point` but no live count. So when
importing a raw Items.csv export, `quantity_on_hand` defaults to 0 unless the
file carries a quantity column. To make a clean round-trip possible, `to_mgn()`
appends a convenience `Qty_On_Hand` column and `from_mgn()` reads it back.

ROUND-TRIP GUARANTEE
--------------------
For any platform X in {square, shopify, quickbooks}:

    mgn -> X -> mgn   preserves  sku, name, price, and quantity_on_hand.

(cost survives too for square/shopify/quickbooks; barcode/vendor/taxable/unit
survive where the target platform has a column for them -- e.g. QuickBooks Online
product import has no barcode field, so a qb round-trip will not preserve it.)
The four guaranteed fields -- sku / name / price / qty -- are the ones the unit
tests lock down.

CLI
---
    python3 inventory_transfer.py --from <mgn|square|shopify|quickbooks|auto> \
                                  --to   <mgn|square|shopify|quickbooks> \
                                  --in   input.csv \
                                  --out  output.csv

    --from auto   sniffs the header row and picks the source format for you.

A summary (items converted, rows skipped + why) is printed to STDERR so it never
pollutes the CSV on STDOUT/the out-file.

SECURITY
--------
- Pure Python standard library only (csv, argparse, io, sys, pathlib, datetime).
  No third-party deps -- runs anywhere with plain python3.
- No eval / no exec / no shell / no network. All CSV input is treated as
  untrusted.
- CSV-injection (a.k.a. formula injection) defense: on EXPORT, any cell whose
  text begins with '=', '+', '-', or '@' is prefixed with a single quote so a
  spreadsheet won't execute it as a formula. On IMPORT, that guard apostrophe is
  transparently stripped, so the protection is invisible to a clean round-trip.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical model
# ---------------------------------------------------------------------------

# The exact key set every importer must produce and every exporter consumes.
CANONICAL_FIELDS = [
    "sku",
    "name",
    "category",
    "description",
    "price",
    "cost",
    "quantity_on_hand",
    "barcode",
    "vendor",
    "taxable",
    "unit",
]

# Characters that make a spreadsheet treat a cell as a formula (OWASP CSV
# injection). Cells starting with any of these get a guard apostrophe on export.
_FORMULA_TRIGGERS = ("=", "+", "-", "@")


def blank_product() -> dict:
    """Return a fresh canonical product dict with safe defaults.

    Nursery items are taxable by default and sold "each" unless told otherwise.
    """
    return {
        "sku": "",
        "name": "",
        "category": "",
        "description": "",
        "price": 0.0,
        "cost": 0.0,
        "quantity_on_hand": 0,
        "barcode": "",
        "vendor": "",
        "taxable": True,
        "unit": "each",
    }


# ---------------------------------------------------------------------------
# Small, defensive value coercers (never raise on bad data)
# ---------------------------------------------------------------------------

def _strip_guard(s: str) -> str:
    """Reverse the CSV-injection guard: drop a single leading apostrophe when it
    is shielding a formula trigger char (e.g. "'=2+2" -> "=2+2"). Makes the
    sanitize-on-export / clean-on-import pair a no-op for round-trips."""
    if len(s) >= 2 and s[0] == "'" and s[1] in _FORMULA_TRIGGERS:
        return s[1:]
    return s


def _clean(value) -> str:
    """Normalize an untrusted cell to a trimmed string and undo the guard
    apostrophe. Never raises -- None becomes ''."""
    if value is None:
        return ""
    return _strip_guard(str(value).strip())


def _to_float(value, default: float = 0.0) -> float:
    """Coerce to float; tolerate '$', thousands commas, blanks, and the guard
    apostrophe. Falls back to `default` on anything unparseable."""
    s = _clean(value).replace("$", "").replace(",", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _to_int(value, default: int = 0) -> int:
    """Coerce to int (via float so '5.0' works); blank/garbage -> default."""
    s = _clean(value).replace(",", "")
    if not s:
        return default
    try:
        return int(float(s))
    except ValueError:
        return default


_TRUE_TOKENS = {"y", "yes", "true", "t", "1", "taxable"}
_FALSE_TOKENS = {"n", "no", "false", "f", "0", "nontaxable", "non-taxable", "exempt"}


def _to_bool(value, default: bool = True) -> bool:
    """Coerce common truthy/falsey spellings to bool; unknown -> default."""
    s = _clean(value).lower()
    if not s:
        return default
    if s in _TRUE_TOKENS:
        return True
    if s in _FALSE_TOKENS:
        return False
    return default


def _money(value) -> str:
    """Render a number as a 2-decimal money string for export."""
    return f"{_to_float(value):.2f}"


def _sanitize(value) -> str:
    """EXPORT guard. Stringify a cell and, if it begins with a formula trigger,
    prefix a single quote so spreadsheets won't execute it. Idempotent enough for
    our purposes (we only ever sanitize once, on the way out)."""
    s = "" if value is None else str(value)
    if s and s[0] in _FORMULA_TRIGGERS:
        return "'" + s
    return s


# ---------------------------------------------------------------------------
# Header-tolerant row access
# ---------------------------------------------------------------------------

def _norm(header: str) -> str:
    """Normalize a header for matching: lowercase, underscores -> spaces, collapse
    runs of whitespace. Lets 'Item_Name' and 'Item Name' resolve the same."""
    return " ".join(str(header).strip().lower().replace("_", " ").split())


def _rowmap(row: dict) -> dict:
    """Build a {normalized_header: cleaned_value} view of a DictReader row."""
    out = {}
    for key, val in row.items():
        if key is None:
            continue  # extra/ragged columns DictReader stuffs under None
        out[_norm(key)] = _clean(val)
    return out


def _pick(rowmap: dict, *candidates: str, prefix: bool = False) -> str:
    """Return the first non-empty value among `candidates` (already normalized).

    When prefix=True, also match any header that STARTS WITH a candidate -- this
    catches Square's location-suffixed columns like
    'current quantity mountain gardens'. Missing column -> '' (never KeyError)."""
    for cand in candidates:
        if cand in rowmap and rowmap[cand] != "":
            return rowmap[cand]
    if prefix:
        for cand in candidates:
            for key, val in rowmap.items():
                if key.startswith(cand) and val != "":
                    return val
    return ""


def _is_blank_row(row: dict) -> bool:
    """True when every cell in the row is empty/whitespace."""
    return all((v is None or str(v).strip() == "") for v in row.values())


# ===========================================================================
# IMPORTERS  (platform CSV rows -> list[canonical])
# ===========================================================================
#
# Each importer takes an iterable of dict rows (as from csv.DictReader) and
# returns (items, skipped) where `skipped` is a list of (row_number, reason)
# for rows that could not be used. A row is skipped only if it is blank or has
# neither a SKU nor a name (nothing to key on).
# ---------------------------------------------------------------------------

def _finish(item: dict, idx: int, skipped: list) -> dict | None:
    """Shared tail: reject rows with no identity, else return the item."""
    if not item["sku"] and not item["name"]:
        skipped.append((idx, "no SKU and no name -- cannot identify item"))
        return None
    return item


def from_mgn(rows) -> tuple[list, list]:
    """Parse Mountain Gardens / Onyx POS Items.csv rows into canonical products.

    Real Items.csv header:
      SKU, Item_Name, Category, Subcategory, Product_Name, Default_Unit,
      Default_Price, Taxable, Reorder_Point, Date_Added, Last_Updated, Status,
      Notes, Size, Item_Description, Wholesale_Cost, Retail_Markup, Retail_Price,
      Unit_Cost, Unit_Price, Last_Invoice_No, Last_Vendor, Last_Received_Date,
      Supplier_Barcode, QR_Code, QR_Image_Path
    Items.csv has no live stock column, so quantity is read from an optional
    Qty_On_Hand / Quantity / Qty_Remaining column if present (else 0).
    """
    items, skipped = [], []
    for idx, row in enumerate(rows, start=2):  # start=2: header is line 1
        if _is_blank_row(row):
            skipped.append((idx, "blank row"))
            continue
        rm = _rowmap(row)
        item = blank_product()
        item["sku"] = _pick(rm, "sku")
        item["name"] = _pick(rm, "item name", "product name", "name")
        item["category"] = _pick(rm, "category", "subcategory")
        item["description"] = _pick(rm, "item description", "description", "notes")
        # Price priority: explicit retail, then unit, then default/catalog price.
        item["price"] = _to_float(_pick(rm, "retail price", "unit price", "default price", "price"))
        item["cost"] = _to_float(_pick(rm, "wholesale cost", "unit cost", "cost"))
        # Live stock from the lot ledger (denormalized into the file if present).
        item["quantity_on_hand"] = _to_int(
            _pick(rm, "qty on hand", "quantity on hand", "quantity", "qty",
                  "qty remaining", "on hand", "stock")
        )
        item["barcode"] = _pick(rm, "supplier barcode", "barcode", "upc", "qr code")
        item["vendor"] = _pick(rm, "last vendor", "vendor", "supplier")
        item["taxable"] = _to_bool(_pick(rm, "taxable", "tax"))
        item["unit"] = _pick(rm, "default unit", "unit") or "each"
        if (it := _finish(item, idx, skipped)) is not None:
            items.append(it)
    return items, skipped


def from_square(rows) -> tuple[list, list]:
    """Parse a Square Item Library export into canonical products.

    Square item-library columns include: Token, Item Name, Variation Name, SKU,
    Description, Category, GTIN, Price, Default Unit Cost, Default Vendor Name,
    and per-location 'Current Quantity <Location>'.
    """
    items, skipped = [], []
    for idx, row in enumerate(rows, start=2):
        if _is_blank_row(row):
            skipped.append((idx, "blank row"))
            continue
        rm = _rowmap(row)
        item = blank_product()
        item["sku"] = _pick(rm, "sku")
        item["name"] = _pick(rm, "item name", "name")
        item["category"] = _pick(rm, "category", "reporting category")
        item["description"] = _pick(rm, "description")
        item["price"] = _to_float(_pick(rm, "price"))
        item["cost"] = _to_float(_pick(rm, "default unit cost", "unit cost"))
        # Square suffixes the location name onto the quantity header -> prefix match.
        item["quantity_on_hand"] = _to_int(
            _pick(rm, "current quantity", "new quantity", "quantity", prefix=True)
        )
        item["barcode"] = _pick(rm, "gtin", "barcode", "upc", "sku barcode")
        item["vendor"] = _pick(rm, "default vendor name", "vendor")
        item["taxable"] = _to_bool(_pick(rm, "tax sales tax", "taxable", "tax", prefix=True))
        item["unit"] = _pick(rm, "variation name", "unit") or "each"
        if (it := _finish(item, idx, skipped)) is not None:
            items.append(it)
    return items, skipped


def from_shopify(rows) -> tuple[list, list]:
    """Parse a Shopify products CSV into canonical products.

    Shopify columns include: Handle, Title, Body (HTML), Vendor, Type,
    Variant SKU, Variant Price, Variant Inventory Qty, Variant Barcode,
    Variant Taxable, and 'Cost per item'.
    """
    items, skipped = [], []
    for idx, row in enumerate(rows, start=2):
        if _is_blank_row(row):
            skipped.append((idx, "blank row"))
            continue
        rm = _rowmap(row)
        item = blank_product()
        item["sku"] = _pick(rm, "variant sku", "sku")
        item["name"] = _pick(rm, "title", "name")
        item["category"] = _pick(rm, "type", "product category", "category")
        item["description"] = _pick(rm, "body (html)", "body html", "body", "description")
        item["price"] = _to_float(_pick(rm, "variant price", "price"))
        item["cost"] = _to_float(_pick(rm, "cost per item", "variant cost", "cost"))
        item["quantity_on_hand"] = _to_int(
            _pick(rm, "variant inventory qty", "inventory qty", "quantity")
        )
        item["barcode"] = _pick(rm, "variant barcode", "barcode", "upc")
        item["vendor"] = _pick(rm, "vendor", "supplier")
        item["taxable"] = _to_bool(_pick(rm, "variant taxable", "taxable"))
        item["unit"] = _pick(rm, "variant unit", "unit") or "each"
        if (it := _finish(item, idx, skipped)) is not None:
            items.append(it)
    return items, skipped


def from_quickbooks(rows) -> tuple[list, list]:
    """Parse a QuickBooks Online product/service (inventory) import into canon.

    QBO product import columns include: Name, SKU, Type, Sales Description,
    Sales Price, Purchase Cost, Quantity On Hand, Reorder Point, Category,
    Taxable.
    """
    items, skipped = [], []
    for idx, row in enumerate(rows, start=2):
        if _is_blank_row(row):
            skipped.append((idx, "blank row"))
            continue
        rm = _rowmap(row)
        item = blank_product()
        item["sku"] = _pick(rm, "sku")
        item["name"] = _pick(rm, "name", "product/service name", "product service name", "item name")
        item["category"] = _pick(rm, "category")
        item["description"] = _pick(rm, "sales description", "purchase description", "description")
        item["price"] = _to_float(_pick(rm, "sales price", "price", "rate"))
        item["cost"] = _to_float(_pick(rm, "purchase cost", "cost"))
        item["quantity_on_hand"] = _to_int(
            _pick(rm, "quantity on hand", "qty on hand", "quantity", "qty")
        )
        item["barcode"] = _pick(rm, "barcode", "upc")  # QBO product import has no native barcode
        item["vendor"] = _pick(rm, "preferred vendor", "vendor", "supplier")
        item["taxable"] = _to_bool(_pick(rm, "taxable", "tax", "sales tax"))
        item["unit"] = _pick(rm, "unit", "u/m", "sales unit") or "each"
        if (it := _finish(item, idx, skipped)) is not None:
            items.append(it)
    return items, skipped


# ===========================================================================
# EXPORTERS  (list[canonical] -> (headers, rows))
# ===========================================================================
#
# Each exporter returns (headers, rows) where:
#   headers : list[str]        -- the platform's import column names, in order
#   rows    : list[list[str]]  -- one list per item, every cell SANITIZED
# Unmappable platform columns are emitted blank but PRESENT so the file matches
# the platform's import template shape.
# ---------------------------------------------------------------------------

def _row(headers: list, mapping: dict) -> list:
    """Build a sanitized row list positionally from a {header: value} mapping.
    Any header absent from `mapping` is emitted as ''."""
    return [_sanitize(mapping.get(h, "")) for h in headers]


def to_mgn(items) -> tuple[list, list]:
    """Render canonical products as Mountain Gardens / Onyx Items.csv rows.

    Emits the real Items.csv columns (so the file drops straight back into the
    POS) and appends a convenience `Qty_On_Hand` column. The POS's authoritative
    stock still lives in the lot ledger; `Qty_On_Hand` exists so a foreign
    system's count survives the round trip.
    """
    headers = [
        "SKU", "Item_Name", "Category", "Subcategory", "Product_Name",
        "Default_Unit", "Default_Price", "Taxable", "Reorder_Point",
        "Date_Added", "Last_Updated", "Status", "Notes", "Size",
        "Item_Description", "Wholesale_Cost", "Retail_Markup", "Retail_Price",
        "Unit_Cost", "Unit_Price", "Last_Invoice_No", "Last_Vendor",
        "Last_Received_Date", "Supplier_Barcode", "QR_Code", "QR_Image_Path",
        "Qty_On_Hand",  # appended convenience column (not in the stock POS schema)
    ]
    today = date.today().isoformat()
    rows = []
    for it in items:
        price = _money(it["price"])
        cost = _money(it["cost"])
        rows.append(_row(headers, {
            "SKU": it["sku"],
            "Item_Name": it["name"],
            "Category": it["category"],
            "Subcategory": it["category"],   # mirror; canonical has no subcategory
            "Product_Name": it["name"],
            "Default_Unit": it["unit"],
            "Default_Price": price,
            "Taxable": "Y" if it["taxable"] else "N",
            "Reorder_Point": "",
            "Date_Added": "",
            "Last_Updated": today,
            "Status": "Active",
            "Notes": "",
            "Size": "",
            "Item_Description": it["description"],
            "Wholesale_Cost": cost,
            "Retail_Markup": "",
            "Retail_Price": price,
            "Unit_Cost": cost,
            "Unit_Price": price,
            "Last_Invoice_No": "",
            "Last_Vendor": it["vendor"],
            "Last_Received_Date": "",
            "Supplier_Barcode": it["barcode"],
            "QR_Code": "",
            "QR_Image_Path": "",
            "Qty_On_Hand": str(it["quantity_on_hand"]),
        }))
    return headers, rows


def to_square(items) -> tuple[list, list]:
    """Render canonical products as a Square Item Library import.

    # NOTE: Square's live import expects the quantity and tax headers to carry
    # the location name, e.g. 'Current Quantity <Location>' and a tax column
    # named after the actual tax rate. We emit generic 'Current Quantity' /
    # 'Tax - Sales Tax' headers; rename them to your location/tax on the way in,
    # or let Square's importer map them. The data is correct, only the header
    # suffix is location-specific.
    """
    headers = [
        "Token",            # blank for new items; Square assigns one on import
        "Item Name",
        "Variation Name",
        "SKU",
        "Description",
        "Category",
        "GTIN",             # barcode / UPC
        "Price",
        "Default Unit Cost",
        "Default Vendor Name",
        "Current Quantity",  # NOTE: real header is 'Current Quantity <Location>'
        "New Quantity",
        "Stock Alert Enabled",
        "Stock Alert Count",
        "Tax - Sales Tax",   # NOTE: real header is named after the tax rate
    ]
    rows = []
    for it in items:
        rows.append(_row(headers, {
            "Token": "",
            "Item Name": it["name"],
            "Variation Name": "",        # single-variation item
            "SKU": it["sku"],
            "Description": it["description"],
            "Category": it["category"],
            "GTIN": it["barcode"],
            "Price": _money(it["price"]),
            "Default Unit Cost": _money(it["cost"]),
            "Default Vendor Name": it["vendor"],
            "Current Quantity": str(it["quantity_on_hand"]),
            "New Quantity": "",
            "Stock Alert Enabled": "",
            "Stock Alert Count": "",
            "Tax - Sales Tax": "Y" if it["taxable"] else "N",
        }))
    return headers, rows


def to_shopify(items) -> tuple[list, list]:
    """Render canonical products as a Shopify products CSV.

    Uses Shopify's real import headers. 'Cost per item' is Shopify's documented
    cost column. Handle is slugified from the name (falling back to SKU).
    """
    headers = [
        "Handle",
        "Title",
        "Body (HTML)",
        "Vendor",
        "Type",
        "Tags",
        "Published",
        "Variant SKU",
        "Variant Inventory Tracker",
        "Variant Inventory Qty",
        "Variant Inventory Policy",
        "Variant Fulfillment Service",
        "Variant Price",
        "Variant Taxable",
        "Variant Barcode",
        "Cost per item",   # NOTE: Shopify's documented per-unit cost column
        "Status",
    ]
    rows = []
    for it in items:
        rows.append(_row(headers, {
            "Handle": _slug(it["name"]) or _slug(it["sku"]),
            "Title": it["name"],
            "Body (HTML)": it["description"],
            "Vendor": it["vendor"],
            "Type": it["category"],
            "Tags": "",
            "Published": "TRUE",
            "Variant SKU": it["sku"],
            "Variant Inventory Tracker": "shopify",
            "Variant Inventory Qty": str(it["quantity_on_hand"]),
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",
            "Variant Price": _money(it["price"]),
            "Variant Taxable": "TRUE" if it["taxable"] else "FALSE",
            "Variant Barcode": it["barcode"],
            "Cost per item": _money(it["cost"]),
            "Status": "active",
        }))
    return headers, rows


def to_quickbooks(items) -> tuple[list, list]:
    """Render canonical products as a QuickBooks Online product/service import.

    # NOTE: QBO's product import has no barcode/UPC column, so barcode is not
    # emitted (and will not survive an mgn->quickbooks->mgn round trip). 'Type'
    # defaults to 'Inventory'. Some QBO templates label the first column
    # 'Product/Service Name' instead of 'Name'; we use 'Name' (importer accepts
    # both).
    """
    headers = [
        "Name",
        "SKU",
        "Type",
        "Sales Description",
        "Sales Price",
        "Income Account",
        "Purchase Description",
        "Purchase Cost",
        "Expense Account",
        "Quantity On Hand",
        "Reorder Point",
        "As Of Date",
        "Category",
        "Taxable",
    ]
    rows = []
    for it in items:
        rows.append(_row(headers, {
            "Name": it["name"],
            "SKU": it["sku"],
            "Type": "Inventory",
            "Sales Description": it["description"],
            "Sales Price": _money(it["price"]),
            "Income Account": "",
            "Purchase Description": it["description"],
            "Purchase Cost": _money(it["cost"]),
            "Expense Account": "",
            "Quantity On Hand": str(it["quantity_on_hand"]),
            "Reorder Point": "",
            "As Of Date": "",
            "Category": it["category"],
            "Taxable": "Y" if it["taxable"] else "N",
        }))
    return headers, rows


def _slug(text: str) -> str:
    """Lowercase URL-safe slug for Shopify Handle: alnum runs joined by '-'."""
    out, prev_dash = [], False
    for ch in str(text).lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


# ---------------------------------------------------------------------------
# Dispatch tables + format auto-detection
# ---------------------------------------------------------------------------

IMPORTERS = {
    "mgn": from_mgn,
    "square": from_square,
    "shopify": from_shopify,
    "quickbooks": from_quickbooks,
}

EXPORTERS = {
    "mgn": to_mgn,
    "square": to_square,
    "shopify": to_shopify,
    "quickbooks": to_quickbooks,
}


def detect_format(headers) -> str | None:
    """Sniff the source format from the header row. Returns a format key or None.

    Order matters: MGN and Square both have an 'item name' column once
    normalized, so MGN's distinctive columns (default price / wholesale cost /
    qr image path) are checked before Square's (token / variation name)."""
    hs = {_norm(h) for h in headers if h}
    if "handle" in hs and ("variant sku" in hs or "variant price" in hs):
        return "shopify"
    if "default price" in hs or "wholesale cost" in hs or "qr image path" in hs:
        return "mgn"
    if "token" in hs or "variation name" in hs:
        return "square"
    if "sales price" in hs or "sales description" in hs:
        return "quickbooks"
    # Loose fallbacks.
    if "variant sku" in hs:
        return "shopify"
    if "item name" in hs:
        return "square"
    return None


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------

def read_rows(path: Path) -> tuple[list, list]:
    """Read a CSV file into (header_list, list_of_dict_rows). utf-8-sig handles
    a BOM from Excel/Square exports."""
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        rows = list(reader)
    return headers, rows


def write_rows(path: Path, headers: list, rows: list) -> None:
    """Write (headers, rows) to a CSV file. Cells are already sanitized."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)


def convert(src_fmt: str, dst_fmt: str, headers: list, rows: list) -> tuple[list, list, list]:
    """Run importer then exporter. Returns (out_headers, out_rows, skipped)."""
    items, skipped = IMPORTERS[src_fmt](rows)
    out_headers, out_rows = EXPORTERS[dst_fmt](items)
    return out_headers, out_rows, skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="inventory_transfer.py",
        description="Convert Mountain Gardens / Onyx inventory CSV to/from "
                    "Square, Shopify, and QuickBooks import formats.",
    )
    parser.add_argument(
        "--from", dest="src", required=True,
        choices=["mgn", "square", "shopify", "quickbooks", "auto"],
        help="source format ('auto' sniffs the header row)",
    )
    parser.add_argument(
        "--to", dest="dst", required=True,
        choices=["mgn", "square", "shopify", "quickbooks"],
        help="target format",
    )
    parser.add_argument("--in", dest="infile", required=True, help="input CSV path")
    parser.add_argument("--out", dest="outfile", required=True, help="output CSV path")
    args = parser.parse_args(argv)

    in_path = Path(args.infile)
    if not in_path.is_file():
        print(f"[error] input file not found: {in_path}", file=sys.stderr)
        return 2

    headers, rows = read_rows(in_path)

    src_fmt = args.src
    if src_fmt == "auto":
        src_fmt = detect_format(headers)
        if src_fmt is None:
            print("[error] could not auto-detect source format from headers: "
                  f"{headers}", file=sys.stderr)
            return 2
        print(f"[info] auto-detected source format: {src_fmt}", file=sys.stderr)

    out_headers, out_rows, skipped = convert(src_fmt, args.dst, headers, rows)
    write_rows(Path(args.outfile), out_headers, out_rows)

    # --- summary to STDERR (keeps STDOUT/out-file clean) ---
    print(f"[done] {src_fmt} -> {args.dst}: {len(out_rows)} item(s) written to "
          f"{args.outfile}", file=sys.stderr)
    if skipped:
        print(f"[warn] skipped {len(skipped)} row(s):", file=sys.stderr)
        for line_no, reason in skipped:
            print(f"        line {line_no}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
