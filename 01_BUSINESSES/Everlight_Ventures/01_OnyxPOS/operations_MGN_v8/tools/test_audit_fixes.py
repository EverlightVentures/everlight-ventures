"""Regression tests for the 2026-06-25 audit fixes: correct inventory-ledger row on
sale (was a mis-called ledger_entry writing garbage), and botanical/common name
fields. Own-process run."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_af_")
os.environ["MGN_DATA_DIR"] = _TMP
os.environ["MGN_TAX_RATE"] = "0.0"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class AuditFixes(unittest.TestCase):
    def test_sale_writes_correct_inventory_ledger_row(self):
        C.create_item("LT1", "Lemon Tree", "Plant", "Tree", default_price=40)
        C.create_lot("LT1", 8, 15.0, supplier="GrowCo", invoice="INV9")
        ok, res = C.record_sale(
            [{"sku": "LT1", "name": "Lemon Tree", "price": 40, "qty": 2}],
            "1001", "Owner", "CASH", 100)
        self.assertTrue(ok, res)
        led = C.read_csv(C.get_ledger_path())
        sale_rows = [r for r in led if r.get("SKU") == "LT1" and r.get("Reason") == "Sale"]
        self.assertTrue(sale_rows, "no 'Sale' inventory-ledger row was written")
        self.assertEqual(float(sale_rows[0]["Delta_Qty"]), -2.0)   # 2 units left the shelf
        self.assertEqual(sale_rows[0]["Ref_Transaction_ID"], res["transaction_id"])
        # stock + COGS still correct (the sale itself was always fine)
        self.assertEqual(C.get_stock_on_hand("LT1"), 6)

    def test_botanical_and_common_name_persist(self):
        self.assertIn("Botanical_Name", C.ITEM_HEADERS)
        self.assertIn("Common_Name", C.ITEM_HEADERS)
        C.create_item("AP1", "Apple", "Plant", "Tree", default_price=30)
        C.update_csv_row(C.get_items_path(), C.ITEM_HEADERS, "SKU", "AP1",
                         {"Botanical_Name": "Malus domestica", "Common_Name": "Apple Tree"})
        it = C.get_item("AP1")
        self.assertEqual(it["Botanical_Name"], "Malus domestica")
        self.assertEqual(it["Common_Name"], "Apple Tree")


if __name__ == "__main__":
    unittest.main()
