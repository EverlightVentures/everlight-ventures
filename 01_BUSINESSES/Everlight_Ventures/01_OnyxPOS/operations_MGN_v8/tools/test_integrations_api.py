"""Tests for the credential-gated live-sync adapters (safe-by-default)."""
import importlib.util as ilu
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_p = Path(__file__).resolve().parent / "integrations_api.py"
_spec = ilu.spec_from_file_location("integrations_api", str(_p))
API = ilu.module_from_spec(_spec)
_spec.loader.exec_module(API)


class IntegrationsAPI(unittest.TestCase):
    def setUp(self):
        for k in ["SQUARE_ACCESS_TOKEN", "QBO_CLIENT_ID", "SHOPIFY_STORE"]:
            os.environ.pop(k, None)

    def test_unconfigured_by_default(self):
        self.assertFalse(API.is_configured("square"))
        st = {s["platform"]: s for s in API.status()}
        self.assertEqual(set(st), {"quickbooks", "square", "shopify"})
        self.assertFalse(st["square"]["configured"])
        self.assertIn("SQUARE_ACCESS_TOKEN", st["square"]["missing"])

    def test_push_degrades_gracefully(self):
        r = API.push_catalog("square", [])
        self.assertFalse(r["ok"])
        self.assertIn("not connected", r["reason"])

    def test_configured_when_env_set_but_no_live_call(self):
        os.environ["SQUARE_ACCESS_TOKEN"] = "tok_123"
        try:
            self.assertTrue(API.is_configured("square"))
            self.assertTrue(API.test_connection("square")["ok"])
            # even with creds, no live call is made yet -> push reports not-wired
            self.assertFalse(API.push_catalog("square", [])["ok"])
        finally:
            os.environ.pop("SQUARE_ACCESS_TOKEN", None)

    def test_unknown_platform(self):
        self.assertFalse(API.push_sale("fake", {})["ok"])


if __name__ == "__main__":
    unittest.main()
