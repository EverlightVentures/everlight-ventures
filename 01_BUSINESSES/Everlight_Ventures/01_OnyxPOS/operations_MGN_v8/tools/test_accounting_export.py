"""Tests for the accounting/bookkeeping export. Own-process run."""
import importlib.util as ilu
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_acct_")
os.environ["MGN_DATA_DIR"] = _TMP
os.environ["MGN_TAX_RATE"] = "0.10"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402

_p = Path(__file__).resolve().parent / "accounting_export.py"
_spec = ilu.spec_from_file_location("accounting_export", str(_p))
A = ilu.module_from_spec(_spec)
_spec.loader.exec_module(A)


class Accounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        C.create_item("POT9", "Clay Pot", "Product", "Pots", default_price=10)
        C.record_sale([{"sku": "POT9", "name": "Clay Pot", "price": 10, "qty": 2}],
                      "1001", "Owner", "CASH", 100)

    def test_daily_summary(self):
        rows = A.daily_summary_rows(date.today(), date.today())
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertAlmostEqual(r["Gross_Sales"], 20.0, places=2)
        self.assertAlmostEqual(r["Sales_Tax"], 2.0, places=2)   # 20 * 0.10
        self.assertEqual(r["Transactions"], 1)
        self.assertAlmostEqual(r["Cash"], 22.0, places=2)       # gross + tax collected

    def test_journal_balances(self):
        rows = A.journal_entry_rows(date.today(), date.today())
        debit = sum(float(x["Debit"] or 0) for x in rows)
        credit = sum(float(x["Credit"] or 0) for x in rows)
        self.assertAlmostEqual(debit, credit, places=2)          # double-entry must balance
        self.assertTrue(any(x["Account"] == "Sales Tax Payable" for x in rows))
        self.assertTrue(any(x["Account"] == "Sales Income" for x in rows))


if __name__ == "__main__":
    unittest.main()
