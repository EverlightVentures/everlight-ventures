#!/usr/bin/env python3
"""
Unit tests for inventory_audit.py.

Covers both the in-memory pure layer (audit_items / find_alignment_gap /
build_report on tiny dict fixtures) and the on-disk layer (real-schema temp
Items.csv + Sales_Logs). stdlib only.

The three load-bearing assertions the prompt asks for:
  * a blank-Item_Name row is flagged
  * a duplicate SKU is flagged
  * a sold-but-missing SKU shows up in the alignment gap
"""

import csv
import os
import tempfile
import unittest

import inventory_audit as ia

# Real Items.csv header (subset is fine -- the reader uses DictReader.get()).
ITEMS_HEADER = ["SKU", "Item_Name", "Category", "Default_Price",
                "Status", "Unit_Cost"]
# Real SALES_HEADERS subset.
SALES_HEADER = ["Date", "Time", "Transaction_ID", "Item_Name", "SKU",
                "Quantity", "Unit_Price", "Line_Total"]


def _item(sku="", name="", price="", category="Plant"):
    return {"SKU": sku, "Item_Name": name, "Category": category,
            "Default_Price": price, "Status": "Active", "Unit_Cost": "1.00"}


def _sale(sku="", name="", qty="1"):
    # matches the record shape read_sales() emits: lowercase sku/name/qty
    return {"sku": sku, "name": name, "qty": qty}


class TestPureAuditLayer(unittest.TestCase):
    """audit_items / find_alignment_gap on in-memory dict fixtures."""

    def test_total_and_clean_catalog(self):
        rows = [_item("A-1", "Rose", "9.99"), _item("A-2", "Fern", "4.50")]
        out = ia.audit_items(rows)
        self.assertEqual(out["total_items"], 2)
        self.assertEqual(out["blank_name"], 0)
        self.assertEqual(out["blank_or_zero_price"], 0)
        self.assertEqual(out["blank_sku"], 0)
        self.assertEqual(out["duplicate_sku_groups"], 0)

    def test_flags_blank_name(self):
        rows = [_item("A-1", "Rose", "9.99"), _item("A-2", "", "4.50")]
        out = ia.audit_items(rows)
        self.assertEqual(out["blank_name"], 1)

    def test_flags_blank_and_zero_price(self):
        rows = [
            _item("A-1", "Rose", "9.99"),
            _item("A-2", "Fern", ""),      # blank price
            _item("A-3", "Moss", "0"),     # zero price
            _item("A-4", "Oak", "0.00"),   # zero price
        ]
        out = ia.audit_items(rows)
        self.assertEqual(out["blank_or_zero_price"], 3)

    def test_flags_blank_sku(self):
        rows = [_item("A-1", "Rose", "9.99"), _item("", "Fern", "4.50")]
        out = ia.audit_items(rows)
        self.assertEqual(out["blank_sku"], 1)

    def test_flags_duplicate_sku(self):
        rows = [
            _item("DUP-1", "Rose", "9.99"),
            _item("DUP-1", "Rose Bush", "12.99"),  # same SKU again
            _item("UNIQ-9", "Fern", "4.50"),
        ]
        out = ia.audit_items(rows)
        self.assertEqual(out["duplicate_sku_groups"], 1)
        self.assertEqual(out["duplicate_sku_row_count"], 2)
        dup_skus = [d["sku"] for d in out["duplicate_skus"]]
        self.assertIn("DUP-1", dup_skus)

    def test_alignment_gap_flags_sold_but_missing_sku(self):
        catalog = [_item("KNOWN-1", "Rose", "9.99")]
        sales = [
            _sale("KNOWN-1", "Rose", "2"),    # present -> not a gap
            _sale("GHOST-9", "Ghost Item", "5"),  # missing -> gap
        ]
        out = ia.find_alignment_gap(catalog, sales)
        self.assertEqual(out["alignment_gap_count"], 1)
        gap_skus = [g["sku"] for g in out["alignment_gap"]]
        self.assertIn("GHOST-9", gap_skus)
        self.assertNotIn("KNOWN-1", gap_skus)
        # qty aggregated
        ghost = out["alignment_gap"][0]
        self.assertEqual(ghost["qty_sold"], 5.0)

    def test_alignment_gap_name_fallback_when_sku_blank(self):
        # Sold with no SKU but a name that DOES exist in the catalog -> present.
        catalog = [_item("KNOWN-1", "Rose", "9.99")]
        sales = [_sale("", "rose", "1")]  # case-insensitive name match
        out = ia.find_alignment_gap(catalog, sales)
        self.assertEqual(out["alignment_gap_count"], 0)

    def test_health_score_perfect_and_penalized(self):
        clean = ia.audit_items([_item("A-1", "Rose", "9.99")])
        self.assertEqual(ia.compute_health_score(clean, None), 100.0)

        dirty = ia.audit_items([_item("", "", "")])  # blank everything
        self.assertLess(ia.compute_health_score(dirty, None), 100.0)

        empty = ia.audit_items([])
        self.assertEqual(ia.compute_health_score(empty, None), 0.0)

    def test_build_report_shape(self):
        rows = [_item("A-1", "Rose", "9.99"), _item("A-2", "", "0")]
        rep = ia.build_report(rows, sales_records=[_sale("Z-9", "Zed", "1")])
        for key in ("total_items", "blank_name", "blank_or_zero_price",
                    "blank_sku", "duplicate_skus", "sales",
                    "health_score", "health_grade"):
            self.assertIn(key, rep)
        self.assertEqual(rep["total_items"], 2)
        self.assertEqual(rep["blank_name"], 1)
        self.assertIsNotNone(rep["sales"])
        # format_report must not raise.
        self.assertIn("HEALTH SCORE", ia.format_report(rep))


class TestOnDiskLayer(unittest.TestCase):
    """End-to-end through real-schema temp CSV files."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="invaudit_")
        self.items_path = os.path.join(self.tmp, "Items.csv")
        with open(self.items_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=ITEMS_HEADER)
            w.writeheader()
            w.writerow(_item("PLA-001", "Rose", "34.99"))
            w.writerow(_item("PLA-002", "", "7.99"))           # blank name
            w.writerow(_item("PLA-003", "Fern", "12.50"))
            w.writerow(_item("PLA-003", "Fern (dup)", "13.00"))  # duplicate SKU

        self.sales_dir = os.path.join(self.tmp, "Sales_Logs", "2025", "Week_1")
        os.makedirs(self.sales_dir)
        sales_path = os.path.join(self.sales_dir, "2025-12-21_SalesLog.csv")
        with open(sales_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=SALES_HEADER)
            w.writeheader()
            w.writerow({"Date": "2025-12-21", "Time": "10:00:00",
                        "Transaction_ID": "T1", "Item_Name": "Rose",
                        "SKU": "PLA-001", "Quantity": "1",
                        "Unit_Price": "34.99", "Line_Total": "34.99"})
            # sold something the catalog never heard of -> alignment gap
            w.writerow({"Date": "2025-12-21", "Time": "10:05:00",
                        "Transaction_ID": "T2", "Item_Name": "Mystery Mulch",
                        "SKU": "GHOST-777", "Quantity": "3",
                        "Unit_Price": "5.00", "Line_Total": "15.00"})

    def tearDown(self):
        for root, dirs, files in os.walk(self.tmp, topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
        os.rmdir(self.tmp)

    def test_end_to_end_report(self):
        rep = ia.run(self.items_path, self.sales_dir)
        self.assertEqual(rep["total_items"], 4)
        self.assertEqual(rep["blank_name"], 1)           # blank-name row flagged
        dup_skus = [d["sku"] for d in rep["duplicate_skus"]]
        self.assertIn("PLA-003", dup_skus)               # duplicate SKU flagged
        gap_skus = [g["sku"] for g in rep["sales"]["alignment_gap"]]
        self.assertIn("GHOST-777", gap_skus)             # sold-but-missing flagged
        self.assertNotIn("PLA-001", gap_skus)            # real item not flagged
        self.assertLess(rep["health_score"], 100.0)
        self.assertGreaterEqual(rep["health_score"], 0.0)

    def test_read_sales_skips_non_sales_csv(self):
        # A stray non-sales CSV in the tree must be ignored, not crash.
        junk = os.path.join(self.tmp, "Sales_Logs", "notes.csv")
        with open(junk, "w", newline="", encoding="utf-8") as fh:
            fh.write("Foo,Bar\n1,2\n")
        recs = ia.read_sales(os.path.join(self.tmp, "Sales_Logs"))
        skus = {r["sku"] for r in recs}
        self.assertIn("GHOST-777", skus)
        self.assertIn("PLA-001", skus)

    def test_missing_sales_dir_is_safe(self):
        self.assertEqual(ia.read_sales(os.path.join(self.tmp, "nope")), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
