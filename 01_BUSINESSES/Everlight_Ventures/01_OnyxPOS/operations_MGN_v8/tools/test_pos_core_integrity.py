"""Integrity tests for the POS money path (sales logging durability).

Runs POS_CORE against a throwaway temp data dir (MGN_DATA_DIR) so it NEVER
touches real business CSVs. Proves:
  1. write_csv is atomic (target intact, no temp litter).
  2. record_sale FAILS LOUD when a log write fails (no silent sale loss).
  3. record_sale success path still records a sale.

Run:  cd tools && python3 -m unittest test_pos_core_integrity -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Point POS_CORE at a temp data dir BEFORE importing it.
_TMP = tempfile.mkdtemp(prefix="mgn_test_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `import POS_CORE` works

import POS_CORE  # noqa: E402


class WriteCsvAtomic(unittest.TestCase):
    def test_atomic_write_leaves_no_temp_and_round_trips(self):
        p = Path(_TMP) / "atomic_check.csv"
        ok = POS_CORE.write_csv(p, ["A", "B"], [{"A": "1", "B": "2"}, {"A": "3", "B": "4"}])
        self.assertTrue(ok)
        rows = POS_CORE.read_csv(p)
        self.assertEqual([r["A"] for r in rows], ["1", "3"])
        # No half-written temp files left behind in the dir
        leftovers = list(Path(_TMP).glob(".tmp_*.csv"))
        self.assertEqual(leftovers, [], f"temp litter left behind: {leftovers}")


class RecordSaleFailsLoud(unittest.TestCase):
    def test_failed_write_returns_failure_not_success(self):
        orig = POS_CORE.append_csv
        POS_CORE.append_csv = lambda *a, **k: False  # simulate disk/permission failure
        try:
            success, result = POS_CORE.record_sale(
                items=[{"sku": "TEST1", "name": "Test Item", "price": 1.0, "qty": 1}],
                emp_id="1001", emp_name="Owner",
                payment_method="CASH", amount_received=5.0,
            )
        finally:
            POS_CORE.append_csv = orig
        self.assertFalse(success, "a failed write must NOT report success")
        self.assertIn("SALE NOT RECORDED", result.get("error", ""))

    def test_success_path_records_a_sale(self):
        success, result = POS_CORE.record_sale(
            items=[{"sku": "TEST2", "name": "Good Item", "price": 2.5, "qty": 2}],
            emp_id="1001", emp_name="Owner",
            payment_method="CASH", amount_received=10.0,
        )
        self.assertTrue(success, f"clean sale should succeed: {result}")
        self.assertEqual(result["total"], round(2.5 * 2 * (1 + float(POS_CORE.TAX_RATE)), 2))
        # the sales log for today should now contain our line
        sales = POS_CORE.get_sales_for_date()
        self.assertTrue(any(r.get("SKU") == "TEST2" for r in sales))


if __name__ == "__main__":
    unittest.main()
