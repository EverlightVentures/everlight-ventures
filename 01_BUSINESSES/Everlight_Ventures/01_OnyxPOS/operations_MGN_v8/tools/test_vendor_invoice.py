"""Tests for vendor-invoice ingest: master-SKU <- vendor-SKU aliases + FIFO lots.
Own-process run."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_vinv_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class VendorInvoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        C.create_item("SUN100", "Sunflower 1G", "Plant", "Perennial", default_price=9.99)

    def test_a_ingest_mapped_creates_fifo_lot(self):
        C.map_vendor_sku("SUN100", "West Covina", "WC-SF-22")
        before = C.get_stock_on_hand("SUN100")
        res = C.ingest_invoice_lines("West Covina", "INV-1001", [
            {"vendor_sku": "WC-SF-22", "desc": "Sunflower", "qty": 10, "unit_cost": 3.50}])
        self.assertEqual(len(res["received"]), 1)
        self.assertEqual(res["unmapped"], [])
        self.assertEqual(C.get_stock_on_hand("SUN100"), before + 10)
        lots = C.get_lots_for_sku("SUN100")
        self.assertTrue(any(l.get("Invoice_Ref") == "INV-1001"
                            and l.get("Supplier") == "West Covina" for l in lots))

    def test_b_map_and_resolve_case_insensitive_idempotent(self):
        C.map_vendor_sku("SUN100", "West Covina", "WC-SF-22", "Sunflower")
        self.assertEqual(C.resolve_vendor_sku("west covina", "wc-sf-22"), "SUN100")
        self.assertIsNone(C.resolve_vendor_sku("Nowhere", "ZZZ"))
        # idempotent: one alias for West Covina even after repeats
        wc = [a for a in C.get_vendor_aliases_for_sku("SUN100")
              if a.get("Vendor") == "West Covina"]
        self.assertEqual(len(wc), 1)

    def test_c_unmapped_then_map_then_reingest(self):
        res = C.ingest_invoice_lines("Oregon", "OR-7", [
            {"vendor_sku": "8841-SUN", "desc": "Sunflower OR", "qty": 5, "unit_cost": 4.0}])
        self.assertEqual(len(res["unmapped"]), 1)
        self.assertEqual(res["received"], [])
        # operator maps it once on the reconciliation screen
        C.map_vendor_sku("SUN100", "Oregon", "8841-SUN", "Sunflower OR")
        res2 = C.ingest_invoice_lines("Oregon", "OR-7", [
            {"vendor_sku": "8841-SUN", "desc": "Sunflower OR", "qty": 5, "unit_cost": 4.0}])
        self.assertEqual(len(res2["received"]), 1)
        # two different vendors now nest under the ONE master SKU
        vendors = {a.get("Vendor") for a in C.get_vendor_aliases_for_sku("SUN100")}
        self.assertIn("West Covina", vendors)
        self.assertIn("Oregon", vendors)


if __name__ == "__main__":
    unittest.main()
