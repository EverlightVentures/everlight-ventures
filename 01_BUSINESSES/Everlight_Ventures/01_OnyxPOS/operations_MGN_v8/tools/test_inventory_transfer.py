#!/usr/bin/env python3
"""
Unit tests for inventory_transfer.py (stdlib unittest only).

Run from the tools/ directory:

    python3 -m unittest

Covers:
  * round-trip  mgn -> square -> mgn   preserves sku / name / price / qty
  * round-trip  mgn -> shopify -> mgn  preserves sku / name / price / qty
  * CSV-injection sanitization on export (formula cells get a guard apostrophe)
  * missing-column resilience (importers never crash, apply safe defaults)
"""

import unittest

import inventory_transfer as it


# --- helpers ---------------------------------------------------------------

def rows_to_dicts(headers, rows):
    """Turn an exporter's (headers, rows) back into DictReader-style dict rows,
    exactly as if the CSV had been written then read again."""
    return [dict(zip(headers, row)) for row in rows]


# Three representative MGN rows (DictReader shape: every column a string).
SAMPLE_MGN_ROWS = [
    {
        "SKU": "PLA-F810C1D9", "Item_Name": "plact, rose", "Category": "Plant",
        "Subcategory": "Plant", "Product_Name": "plact, rose",
        "Default_Unit": "each", "Default_Price": "34.99", "Taxable": "Y",
        "Item_Description": "plact, rose", "Wholesale_Cost": "12.75",
        "Retail_Price": "34.99", "Unit_Cost": "12.75", "Unit_Price": "34.99",
        "Last_Vendor": "Mountain Gardens", "Supplier_Barcode": "012345678905",
        "Qty_On_Hand": "7",
    },
    {
        "SKU": "SUP-DF071183", "Item_Name": "Plalosein", "Category": "Supply",
        "Subcategory": "Supply", "Product_Name": "Plalosein",
        "Default_Unit": "each", "Default_Price": "34.99", "Taxable": "Y",
        "Item_Description": "Plalosein", "Wholesale_Cost": "15.12",
        "Retail_Price": "34.99", "Unit_Cost": "15.12", "Unit_Price": "34.99",
        "Last_Vendor": "Mountain Gardens", "Supplier_Barcode": "",
        "Qty_On_Hand": "0",
    },
    {
        "SKU": "PLA-CB7C6B18", "Item_Name": "pland, herb", "Category": "Plant",
        "Subcategory": "Plant", "Product_Name": "pland, herb",
        "Default_Unit": "1 gal", "Default_Price": "7.99", "Taxable": "Y",
        "Item_Description": "pland, herb", "Wholesale_Cost": "",
        "Retail_Price": "7.99", "Unit_Cost": "", "Unit_Price": "7.99",
        "Last_Vendor": "Mountain Gardens", "Supplier_Barcode": "",
        "Qty_On_Hand": "120",
    },
]


def _key4(item):
    """The four fields the round-trip guarantee protects."""
    return (item["sku"], item["name"], round(item["price"], 2), item["quantity_on_hand"])


class RoundTripTests(unittest.TestCase):
    """mgn -> X -> mgn must preserve sku / name / price / qty."""

    def _round_trip_through(self, to_exporter, from_importer):
        start, _ = it.from_mgn(SAMPLE_MGN_ROWS)

        # mgn -> X
        x_headers, x_rows = to_exporter(start)
        x_dicts = rows_to_dicts(x_headers, x_rows)

        # X -> mgn
        mid, _ = from_importer(x_dicts)
        m_headers, m_rows = it.to_mgn(mid)
        m_dicts = rows_to_dicts(m_headers, m_rows)

        # mgn (final)
        end, _ = it.from_mgn(m_dicts)
        return start, end

    def test_mgn_square_mgn(self):
        start, end = self._round_trip_through(it.to_square, it.from_square)
        self.assertEqual([_key4(i) for i in start], [_key4(i) for i in end])

    def test_mgn_shopify_mgn(self):
        start, end = self._round_trip_through(it.to_shopify, it.from_shopify)
        self.assertEqual([_key4(i) for i in start], [_key4(i) for i in end])

    def test_round_trip_specific_values(self):
        """Spot-check the first item survives intact."""
        start, end = self._round_trip_through(it.to_square, it.from_square)
        self.assertEqual(end[0]["sku"], "PLA-F810C1D9")
        self.assertEqual(end[0]["name"], "plact, rose")
        self.assertEqual(end[0]["price"], 34.99)
        self.assertEqual(end[0]["quantity_on_hand"], 7)


class SanitizationTests(unittest.TestCase):
    """Formula-leading cells must be neutralized on export."""

    def test_export_prefixes_formula_cells(self):
        evil = it.blank_product()
        evil.update({
            "sku": "=cmd|'/c calc'!A1",   # classic CSV-injection payload
            "name": "+SUM(1+1)",
            "description": "@SUM(2)",
            "vendor": "-2+3",
            "price": 9.99, "quantity_on_hand": 1,
        })
        for exporter in (it.to_square, it.to_shopify, it.to_quickbooks, it.to_mgn):
            headers, rows = exporter([evil])
            flat = rows[0]
            # Every dangerous value must now start with a guard apostrophe.
            self.assertTrue(any(c.startswith("'=") for c in flat),
                            f"{exporter.__name__}: '=' cell not guarded")
            self.assertTrue(any(c.startswith("'+") for c in flat),
                            f"{exporter.__name__}: '+' cell not guarded")
            self.assertTrue(any(c.startswith("'@") for c in flat),
                            f"{exporter.__name__}: '@' cell not guarded")
            # No raw cell may still begin with a formula trigger.
            for cell in flat:
                if cell:
                    self.assertNotIn(
                        cell[0], it._FORMULA_TRIGGERS,
                        f"{exporter.__name__}: unguarded formula cell {cell!r}",
                    )

    def test_guard_is_reversible_on_import(self):
        """A guarded value re-imports to its original text (clean round-trip)."""
        item = it.blank_product()
        item.update({"sku": "SKU1", "name": "=2+2", "price": 5.0, "quantity_on_hand": 3})
        headers, rows = it.to_square([item])
        back, _ = it.from_square(rows_to_dicts(headers, rows))
        self.assertEqual(back[0]["name"], "=2+2")


class ResilienceTests(unittest.TestCase):
    """Importers must never crash on missing columns or junk."""

    def test_missing_columns_use_defaults(self):
        sparse = [{"SKU": "X1"}]  # name/price/qty/everything else absent
        items, skipped = it.from_mgn(sparse)
        self.assertEqual(len(items), 1)
        p = items[0]
        self.assertEqual(p["sku"], "X1")
        self.assertEqual(p["price"], 0.0)
        self.assertEqual(p["cost"], 0.0)
        self.assertEqual(p["quantity_on_hand"], 0)
        self.assertEqual(p["unit"], "each")
        self.assertTrue(p["taxable"])

    def test_blank_and_identityless_rows_skipped(self):
        rows = [
            {"SKU": "", "Item_Name": ""},          # no identity -> skipped
            {"SKU": "", "Item_Name": "", "Category": ""},  # all blank -> skipped
            {"SKU": "GOOD", "Item_Name": "Thing"}, # kept
        ]
        items, skipped = it.from_mgn(rows)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["sku"], "GOOD")
        self.assertEqual(len(skipped), 2)

    def test_garbage_numbers_fall_back(self):
        rows = [{"SKU": "Z", "Item_Name": "Z", "Retail_Price": "not-a-number",
                 "Qty_On_Hand": "??"}]
        items, _ = it.from_mgn(rows)
        self.assertEqual(items[0]["price"], 0.0)
        self.assertEqual(items[0]["quantity_on_hand"], 0)

    def test_detect_format(self):
        self.assertEqual(it.detect_format(list(SAMPLE_MGN_ROWS[0].keys())), "mgn")
        sq_h, _ = it.to_square([it.blank_product()])
        self.assertEqual(it.detect_format(sq_h), "square")
        sh_h, _ = it.to_shopify([it.blank_product()])
        self.assertEqual(it.detect_format(sh_h), "shopify")
        qb_h, _ = it.to_quickbooks([it.blank_product()])
        self.assertEqual(it.detect_format(qb_h), "quickbooks")


if __name__ == "__main__":
    unittest.main(verbosity=2)
