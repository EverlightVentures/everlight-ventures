"""Tests for the loyalty/rewards engine: earn (tier multipliers), balance, redeem.
Own-process run."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_rw_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class Rewards(unittest.TestCase):
    def test_earn_with_tier_multiplier(self):
        self.assertEqual(C.award_points("CUST-1", "a@x.com", 100, tier="BRONZE"), 100)
        self.assertEqual(C.points_balance("a@x.com"), 100)
        self.assertEqual(C.award_points("CUST-1", "a@x.com", 100, tier="GOLD"), 150)  # 1.5x
        self.assertEqual(C.points_balance("a@x.com"), 250)

    def test_dollar_value(self):
        C.award_points("CUST-2", "b@x.com", 200, tier="BRONZE")  # 200 pts
        self.assertEqual(C.points_dollar_value("b@x.com"), 10.0)  # 200 * $0.05

    def test_redeem_caps_at_balance(self):
        C.award_points("CUST-3", "c@x.com", 100)  # 100 pts
        ok, dollars = C.redeem_points("CUST-3", "c@x.com", 60)
        self.assertTrue(ok)
        self.assertEqual(dollars, 3.0)              # 60 * $0.05
        self.assertEqual(C.points_balance("c@x.com"), 40)
        ok2, _ = C.redeem_points("CUST-3", "c@x.com", 100)  # more than balance
        self.assertFalse(ok2)
        self.assertEqual(C.points_balance("c@x.com"), 40)   # unchanged

    def test_no_email_no_points(self):
        self.assertEqual(C.award_points("", "", 100), 0)

    def test_record_sale_discount_reduces_total_and_floors_at_zero(self):
        os.environ["MGN_TAX_RATE"] = "0"
        C.create_item("RW1", "Pot", "Product", "P", default_price=20)
        ok, res = C.record_sale([{"sku": "RW1", "name": "Pot", "price": 20, "qty": 1}],
                                "1001", "Owner", "CASH", 100, discount=5)
        self.assertTrue(ok, res)
        self.assertEqual(res["discount"], 5.0)
        self.assertEqual(res["total"], 15.0)        # 20 - 5 (no tax)
        ok2, res2 = C.record_sale([{"sku": "RW1", "name": "Pot", "price": 20, "qty": 1}],
                                  "1001", "Owner", "CASH", 100, discount=999)
        self.assertTrue(ok2)
        self.assertEqual(res2["total"], 0.0)         # discount can't go negative


if __name__ == "__main__":
    unittest.main()
