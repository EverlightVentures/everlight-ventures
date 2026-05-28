"""
test_assessor_harvester.py -- pytest suite for the non-browser parts of
assessor_harvester (queue selector + ledger writer).

No Playwright required.  These tests cover:
  1. select_candidates -- filters TN, respects limit + resume flag
  2. get_address_for_lead -- address extraction priority
  3. write_ledger -- file written, valid JSON lines
  4. dry_run path -- run() returns 0 without touching browser
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Make assessor_harvester importable without Playwright installed
# ---------------------------------------------------------------------------
# Stub playwright so the import guard doesn't fail
if "playwright" not in sys.modules:
    pw_stub = types.ModuleType("playwright")
    sync_stub = types.ModuleType("playwright.sync_api")
    sync_stub.sync_playwright = None
    sync_stub.TimeoutError = Exception
    sys.modules["playwright"] = pw_stub
    sys.modules["playwright.sync_api"] = sync_stub

# Now import our module
sys.path.insert(0, str(Path(__file__).parent))
import assessor_harvester as ah


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LEADS = [
    {
        "id": "lead-tn-001",
        "state": "TN",
        "address": "101 MAIN ST, MEMPHIS, TN",
        "property_address": "101 MAIN ST",
        "owner_name": None,
        "enrichment_stage": None,
    },
    {
        "id": "lead-tn-002",
        "state": "TN",
        "address": "202 OAK AVE, MEMPHIS, TN",
        "property_address": "202 OAK AVE",
        "owner_name": None,
        "enrichment_stage": "assessor_done",
    },
    {
        "id": "lead-tn-003",
        "state": "TN",
        "address": "303 PINE RD, MEMPHIS, TN",
        "property_address": "303 PINE RD",
        "owner_name": None,
        "enrichment_stage": "assessor_failed",
    },
    {
        "id": "lead-ga-001",
        "state": "GA",
        "address": "404 PEACH ST, ATLANTA, GA",
        "property_address": "404 PEACH ST",
        "owner_name": None,
        "enrichment_stage": None,
    },
    {
        "id": "lead-tn-004",
        "state": "TN",
        "address": "505 ELM ST, MEMPHIS, TN",
        "property_address": "",   # no property_address -- should fall back to address field
        "owner_name": None,
        "enrichment_stage": None,
    },
    {
        "id": "lead-tn-noaddr",
        "state": "TN",
        "address": "",
        "property_address": "",
        "owner_name": None,
        "enrichment_stage": None,
    },
]


# ---------------------------------------------------------------------------
# Tests: select_candidates
# ---------------------------------------------------------------------------

class TestSelectCandidates:
    def test_filters_by_state(self):
        results = ah.select_candidates(SAMPLE_LEADS, "TN", limit=100, resume=False)
        states = {r["state"] for r in results}
        assert states == {"TN"}

    def test_excludes_leads_with_no_address(self):
        results = ah.select_candidates(SAMPLE_LEADS, "TN", limit=100, resume=False)
        ids = [r["id"] for r in results]
        assert "lead-tn-noaddr" not in ids

    def test_limit_respected(self):
        results = ah.select_candidates(SAMPLE_LEADS, "TN", limit=1, resume=False)
        assert len(results) == 1

    def test_resume_false_includes_done_and_failed(self):
        results = ah.select_candidates(SAMPLE_LEADS, "TN", limit=100, resume=False)
        stages = {r["enrichment_stage"] for r in results}
        # When resume=False, done+failed leads are included
        assert "assessor_done" in stages
        assert "assessor_failed" in stages

    def test_resume_true_skips_done_and_failed(self):
        results = ah.select_candidates(SAMPLE_LEADS, "TN", limit=100, resume=True)
        ids = [r["id"] for r in results]
        assert "lead-tn-002" not in ids   # assessor_done
        assert "lead-tn-003" not in ids   # assessor_failed
        assert "lead-tn-001" in ids       # None stage -- included

    def test_empty_when_state_has_no_leads(self):
        results = ah.select_candidates(SAMPLE_LEADS, "WY", limit=100, resume=False)
        assert results == []


# ---------------------------------------------------------------------------
# Tests: get_address_for_lead
# ---------------------------------------------------------------------------

class TestGetAddressForLead:
    def test_prefers_property_address(self):
        lead = {"property_address": "101 MAIN ST", "address": "101 MAIN ST, MEMPHIS, TN"}
        assert ah.get_address_for_lead(lead) == "101 MAIN ST"

    def test_falls_back_to_address_field(self):
        lead = {"property_address": "", "address": "505 ELM ST, MEMPHIS, TN"}
        result = ah.get_address_for_lead(lead)
        # Should strip city/state suffix
        assert result == "505 ELM ST"

    def test_returns_none_when_both_empty(self):
        lead = {"property_address": "", "address": ""}
        assert ah.get_address_for_lead(lead) is None

    def test_returns_none_when_keys_absent(self):
        assert ah.get_address_for_lead({}) is None


# ---------------------------------------------------------------------------
# Tests: write_ledger
# ---------------------------------------------------------------------------

class TestWriteLedger:
    def test_creates_file_and_writes_json(self, tmp_path, monkeypatch):
        # Redirect LOG_DIR and LOG_PATH to a temp dir
        monkeypatch.setattr(ah, "LOG_DIR", tmp_path)
        monkeypatch.setattr(ah, "LOG_PATH", tmp_path / "assessor_harvester.jsonl")

        entry = {"ts": "2026-01-01T00:00:00Z", "status": "ok", "address": "101 MAIN ST", "lead_id": "x"}
        ah.write_ledger(entry)

        log_file = tmp_path / "assessor_harvester.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["status"] == "ok"
        assert parsed["address"] == "101 MAIN ST"

    def test_appends_multiple_entries(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ah, "LOG_DIR", tmp_path)
        monkeypatch.setattr(ah, "LOG_PATH", tmp_path / "assessor_harvester.jsonl")

        for i in range(3):
            ah.write_ledger({"ts": f"ts-{i}", "status": "ok", "address": f"addr-{i}", "lead_id": str(i)})

        lines = (tmp_path / "assessor_harvester.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3


# ---------------------------------------------------------------------------
# Tests: dry_run path (run() without browser)
# ---------------------------------------------------------------------------

class TestDryRun:
    def _make_args(self, limit=3, state="TN", dry_run=True, resume=False):
        import argparse
        args = argparse.Namespace(
            limit=limit, state=state, dry_run=dry_run,
            delay_seconds=0.0, resume=resume
        )
        return args

    def test_dry_run_returns_zero(self, tmp_path, monkeypatch):
        # Patch leads to our sample set
        monkeypatch.setattr(ah, "load_leads", lambda: list(SAMPLE_LEADS))
        # save_leads should never be called in dry-run
        monkeypatch.setattr(ah, "save_leads", lambda _: pytest.fail("save_leads called in dry-run"))

        rc = ah.run(self._make_args(limit=3))
        assert rc == 0

    def test_dry_run_no_browser_even_without_playwright(self, monkeypatch):
        monkeypatch.setattr(ah, "_PLAYWRIGHT_AVAILABLE", False)
        monkeypatch.setattr(ah, "load_leads", lambda: list(SAMPLE_LEADS))
        monkeypatch.setattr(ah, "save_leads", lambda _: None)

        rc = ah.run(self._make_args(limit=2))
        # dry-run must work even without Playwright
        assert rc == 0

    def test_live_mode_exits_2_without_playwright(self, monkeypatch):
        monkeypatch.setattr(ah, "_PLAYWRIGHT_AVAILABLE", False)
        monkeypatch.setattr(ah, "load_leads", lambda: list(SAMPLE_LEADS))
        monkeypatch.setattr(ah, "save_leads", lambda _: None)

        args = self._make_args(dry_run=False)
        rc = ah.run(args)
        assert rc == 2

    def test_dry_run_respects_limit(self, monkeypatch, capsys):
        monkeypatch.setattr(ah, "load_leads", lambda: list(SAMPLE_LEADS))
        monkeypatch.setattr(ah, "save_leads", lambda _: None)

        ah.run(self._make_args(limit=2))
        captured = capsys.readouterr()
        # Should mention exactly 2 candidates
        assert "2 lead(s)" in captured.out
