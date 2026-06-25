"""Tests for customer capture: profile upsert, purchase history, newsletter list.
Own-process run (shared POS_CORE.DATA_DIR module global)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_cust_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class CustomerCapture(unittest.TestCase):
    def test_upsert_customer_idempotent_by_email(self):
        cid1 = C.upsert_customer("Jane Doe", "jane@example.com")
        cid2 = C.upsert_customer("Jane D", "JANE@example.com")  # same email, diff case
        self.assertEqual(cid1, cid2)
        self.assertTrue(cid1.startswith("CUST-"))

    def test_newsletter_idempotent_and_validates(self):
        added1, sid1 = C.add_newsletter_subscriber("CUST-1", "news@example.com", "Fan")
        added2, sid2 = C.add_newsletter_subscriber("CUST-1", "NEWS@example.com", "Fan")
        self.assertTrue(added1)
        self.assertFalse(added2)            # no duplicate
        self.assertEqual(sid1, sid2)
        bad, _ = C.add_newsletter_subscriber("CUST-1", "notanemail", "x")
        self.assertFalse(bad)               # rejects invalid email

    def test_purchase_history(self):
        payload = {
            "transaction": {"Transaction_ID": "TRX1", "Date": "2026-06-25",
                            "Time": "10:00", "Payment_Method": "CASH"},
            "items": [{"qty": "2", "name": "Tomato Start"}],
            "totals": {"subtotal": "10", "tax": "0", "total": "10", "change_due": "0"},
        }
        C.log_customer_receipt("Buy", "Er", "buyer@example.com", payload)
        C.log_customer_receipt("Buy", "Er", "buyer@example.com", payload)
        hist = C.get_customer_history("buyer@example.com")
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[0]["Email"], "buyer@example.com")
        self.assertIn("Tomato", hist[0]["Items_Summary"])


if __name__ == "__main__":
    unittest.main()
