"""Tests for the per-line sales-tax engine. CA Reg 1588 / R&TC 6359: food-producing
plants are exempt; ornamentals + hardgoods are taxable; tax is decided per item in a
mixed cart; the rate is location-set (config), never hardcoded. Own-process run."""
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_tax_")
os.environ["MGN_DATA_DIR"] = _TMP
os.environ["MGN_TAX_RATE"] = "0.0825"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class TaxEngine(unittest.TestCase):
    def test_rate_decimal_and_percent_forms(self):
        os.environ["MGN_TAX_RATE"] = "0.095"
        self.assertAlmostEqual(C.get_tax_rate(), 0.095)
        os.environ["MGN_TAX_RATE"] = "8.25"   # percent form auto-normalizes
        self.assertAlmostEqual(C.get_tax_rate(), 0.0825)
        os.environ["MGN_TAX_RATE"] = "0.0825"

    def test_resolve_line_tax_flags(self):
        self.assertTrue(C.resolve_line_tax({"Taxable": "Y"})[0])
        self.assertFalse(C.resolve_line_tax({"Taxable": "N"})[0])
        taxable, reason = C.resolve_line_tax({"Taxable": "REVIEW"})
        self.assertTrue(taxable)
        self.assertIn("NEEDS_REVIEW", reason)
        self.assertTrue(C.resolve_line_tax({})[0])  # blank -> taxable

    def test_config_roundtrip(self):
        C.set_config("Store_Tax_Rate", "0.0875")
        self.assertEqual(C.get_config("Store_Tax_Rate"), "0.0875")

    def test_mixed_cart_only_taxes_taxable_line(self):
        C.create_item("POT1", "Clay Pot", "Product", "Pots", default_price=10)
        C.create_item("VEG1", "Tomato Start", "Plant", "Vegetable", default_price=5)
        C.update_csv_row(C.get_items_path(), C.ITEM_HEADERS, "SKU", "VEG1", {"Taxable": "N"})
        os.environ["MGN_TAX_RATE"] = "0.0825"
        rate = C.get_tax_rate()
        ok, res = C.record_sale(
            [{"sku": "POT1", "name": "Clay Pot", "price": 10, "qty": 1},
             {"sku": "VEG1", "name": "Tomato Start", "price": 5, "qty": 1}],
            "1001", "Owner", "CASH", 100)
        self.assertTrue(ok, res)
        self.assertAlmostEqual(res["tax"], round(10 * rate, 2), places=2)  # only the pot
        rows = {r["SKU"]: r for r in C.get_sales_for_date(date.today())}
        self.assertEqual(float(rows["VEG1"]["Tax_Amount"]), 0.0)
        self.assertIn("EXEMPT", rows["VEG1"]["Tax_Exempt_Reason"])
        self.assertGreater(float(rows["POT1"]["Tax_Amount"]), 0.0)

    def test_all_exempt_zero_tax(self):
        C.create_item("VEG2", "Pepper Start", "Plant", "Vegetable", default_price=4)
        C.update_csv_row(C.get_items_path(), C.ITEM_HEADERS, "SKU", "VEG2", {"Taxable": "N"})
        ok, res = C.record_sale(
            [{"sku": "VEG2", "name": "Pepper Start", "price": 4, "qty": 2}],
            "1001", "Owner", "CASH", 20)
        self.assertTrue(ok, res)
        self.assertEqual(res["tax"], 0.0)


if __name__ == "__main__":
    unittest.main()
