"""Tests for marketing: CAN-SPAM unsubscribe + spend tiers. Own-process run."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_mkt_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class Marketing(unittest.TestCase):
    def test_tier_thresholds(self):
        self.assertEqual(C.customer_tier(0), "BRONZE")
        self.assertEqual(C.customer_tier(199.99), "BRONZE")
        self.assertEqual(C.customer_tier(200), "SILVER")
        self.assertEqual(C.customer_tier(500), "GOLD")
        self.assertEqual(C.customer_tier(1500), "PLATINUM")

    def test_unsubscribe_by_email_then_excluded_from_active(self):
        cid = C.upsert_customer("Jo", "jo@x.com")
        added, _sid = C.add_newsletter_subscriber(cid, "jo@x.com", "Jo")
        self.assertTrue(added)
        self.assertEqual(len(C.get_newsletter_subscribers(active_only=True)), 1)
        ok, email = C.unsubscribe_newsletter("jo@x.com")
        self.assertTrue(ok)
        self.assertEqual(email, "jo@x.com")
        # unsubscribed -> not in the active list (so the CSV export / sends skip them)
        self.assertEqual(len(C.get_newsletter_subscribers(active_only=True)), 0)

    def test_unsubscribe_unknown_is_false(self):
        ok, _ = C.unsubscribe_newsletter("nobody@nowhere.com")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
