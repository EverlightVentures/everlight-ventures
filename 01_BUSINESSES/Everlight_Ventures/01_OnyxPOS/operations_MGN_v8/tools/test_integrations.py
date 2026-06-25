"""Tests for CSV import/export integrations: import_items upsert + converter export.
Own-process run."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_ix_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402

_ITEMS = [
    {"sku": "SQ-1", "name": "Basil 4in", "category": "Plant", "description": "Herb",
     "price": 4.99, "cost": 1.5, "quantity_on_hand": 12, "barcode": "111",
     "vendor": "GreenCo", "taxable": False, "unit": "each"},
    {"sku": "SQ-2", "name": "Clay Pot 6in", "category": "Supply", "description": "",
     "price": 7.50, "cost": 3.0, "quantity_on_hand": 0, "barcode": "222",
     "vendor": "PotCo", "taxable": True, "unit": "each"},
    {"sku": "", "name": "", "category": "", "price": 0, "cost": 0, "taxable": True},  # skipped
]


class Integrations(unittest.TestCase):
    def test_a_import_creates_and_seeds_stock(self):
        res = C.import_items(_ITEMS, create_lots=True)
        self.assertEqual(res["created"], 2)
        self.assertEqual(res["skipped"], 1)      # the blank row
        self.assertEqual(res["lots"], 1)         # only SQ-1 had a quantity
        basil = C.get_item("SQ-1")
        self.assertEqual(basil["Item_Name"], "Basil 4in")
        self.assertEqual(basil["Taxable"], "N")  # food-exempt preserved through import
        self.assertEqual(C.get_stock_on_hand("SQ-1"), 12)

    def test_b_import_updates_existing_by_sku(self):
        C.import_items([{"sku": "SQ-1", "name": "Basil Updated", "category": "Plant",
                         "price": 5.99, "cost": 1.5, "taxable": False}])
        self.assertEqual(C.get_item("SQ-1")["Item_Name"], "Basil Updated")
        self.assertEqual(C.get_item("SQ-1")["Default_Price"], "5.99")

    def test_c_export_via_converter(self):
        import importlib.util as ilu
        p = Path(__file__).resolve().parent / "inventory_transfer.py"
        spec = ilu.spec_from_file_location("inventory_transfer", str(p))
        itx = ilu.module_from_spec(spec)
        spec.loader.exec_module(itx)
        headers, rows, _ = itx.convert("mgn", "square", C.ITEM_HEADERS, C.get_all_items())
        self.assertGreaterEqual(len(rows), 2)
        # Square export carries an item-name + token style header
        joined = " ".join(headers).lower()
        self.assertTrue("item name" in joined or "token" in joined)


if __name__ == "__main__":
    unittest.main()
