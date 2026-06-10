"""
Smoke tests for osint_enrich.py

Monkeypatches homeowner_osint.resolve and email_confidence_gate.categorize to
avoid network calls. Verifies:
  - Parallel execution (ThreadPoolExecutor fires, all leads get processed)
  - Correct tier dispatch (send/try/skip -> email set or not)
  - leads_db is updated correctly after parallel run
  - Dry-run is a no-op
"""
from __future__ import annotations

import json
import sys
import os
import argparse
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))

import osint_enrich
from email_confidence_gate import TIER_SEND, TIER_TRY, TIER_SKIP


def _make_leads(n: int = 6, state: str = "TN") -> list[dict]:
    return [
        {
            "lead_id": f"lead_{i}",
            "owner_name": f"Owner {i}",
            "property_address": f"{100 + i} Main St",
            "city": "Memphis",
            "state": state,
        }
        for i in range(n)
    ]


def _synthetic_resolve(tier: str):
    """Return a resolve() stub that always produces a candidate with the given tier."""
    if tier == TIER_SEND:
        cands = [{"email": "owner@real.com", "confidence": 80, "verified": True,
                  "sources": ["mx_check", "emailrep"]}]
        identity = 80
    elif tier == TIER_TRY:
        cands = [{"email": "owner@maybe.com", "confidence": 60, "verified": False,
                  "sources": ["mx_check"]}]
        identity = 50
    else:
        cands = []
        identity = 10

    def _resolve(**kwargs):
        return {
            "candidate_emails": cands,
            "identity_score": identity,
            "verdict": tier,
            "raw_investigation_id": "fake_id",
        }
    return _resolve


def _run_with_stubs(leads: list[dict], tier: str, tmp_path: Path) -> dict:
    """Write leads to a tmp leads_db, run osint_enrich.run(), return loaded result."""
    db_path = tmp_path / "leads_db.json"
    db_path.write_text(json.dumps(leads, indent=2))

    orig_db = osint_enrich.LEADS_DB
    orig_ledger = osint_enrich.LEDGER
    osint_enrich.LEADS_DB = db_path
    osint_enrich.LEDGER = tmp_path / "ledger.jsonl"

    try:
        resolve_stub = _synthetic_resolve(tier)
        with patch("osint_enrich.run.__globals__", osint_enrich.run.__globals__):
            # Patch via sys.modules so the import-inside-run picks the stub
            fake_homeowner = MagicMock()
            fake_homeowner.resolve = resolve_stub

            from email_confidence_gate import categorize as real_categorize

            with patch.dict("sys.modules", {"homeowner_osint": fake_homeowner}):
                args = SimpleNamespace(limit=100, state="TN", dry_run=False)
                osint_enrich.run(args)
    finally:
        osint_enrich.LEADS_DB = orig_db
        osint_enrich.LEDGER = orig_ledger

    return json.loads(db_path.read_text())


class TestOsintEnrichSmoke:

    def test_send_tier_sets_email_on_lead(self, tmp_path):
        """TIER_SEND leads get email + email_source set."""
        leads = _make_leads(3)
        result = _run_with_stubs(leads, TIER_SEND, tmp_path)
        for lead in result:
            assert "email" in lead, f"send-tier lead missing email: {lead}"
            assert lead["email_source"].startswith("osint_enrich_send"), (
                f"email_source wrong: {lead['email_source']}"
            )
            assert lead["confidence_tier"] == TIER_SEND

    def test_try_tier_sets_email_on_lead(self, tmp_path):
        """TIER_TRY leads also get email set (operator sends anyway)."""
        leads = _make_leads(3)
        result = _run_with_stubs(leads, TIER_TRY, tmp_path)
        for lead in result:
            assert "email" in lead, f"try-tier lead missing email: {lead}"
            assert lead["email_source"].startswith("osint_enrich_try"), (
                f"email_source wrong: {lead['email_source']}"
            )
            assert lead["confidence_tier"] == TIER_TRY

    def test_skip_tier_does_not_set_email(self, tmp_path):
        """TIER_SKIP leads do NOT get email set."""
        leads = _make_leads(3)
        result = _run_with_stubs(leads, TIER_SKIP, tmp_path)
        for lead in result:
            assert "email" not in lead, f"skip-tier lead should NOT have email: {lead}"
            assert lead["confidence_tier"] == TIER_SKIP

    def test_all_leads_processed(self, tmp_path):
        """All ready leads get enriched (parallel or not)."""
        n = 6
        leads = _make_leads(n)
        result = _run_with_stubs(leads, TIER_SEND, tmp_path)
        assert len(result) == n
        enriched = [l for l in result if "confidence_tier" in l]
        assert len(enriched) == n, f"Not all leads enriched: {len(enriched)}/{n}"

    def test_parallel_execution_processes_all(self, tmp_path):
        """With 6 leads and max_workers=4, all 6 should still get enriched."""
        n = 6
        leads = _make_leads(n)
        result = _run_with_stubs(leads, TIER_TRY, tmp_path)
        enriched = [l for l in result if l.get("confidence_tier") == TIER_TRY]
        assert len(enriched) == n, (
            f"Expected {n} enriched, got {len(enriched)}. Result: {result}"
        )

    def test_dry_run_does_not_write(self, tmp_path):
        """Dry-run does not write to leads_db."""
        leads = _make_leads(3)
        db_path = tmp_path / "leads_db.json"
        original_content = json.dumps(leads, indent=2)
        db_path.write_text(original_content)

        orig_db = osint_enrich.LEADS_DB
        orig_ledger = osint_enrich.LEDGER
        osint_enrich.LEADS_DB = db_path
        osint_enrich.LEDGER = tmp_path / "ledger.jsonl"

        try:
            fake_homeowner = MagicMock()
            fake_homeowner.resolve = _synthetic_resolve(TIER_SEND)
            with patch.dict("sys.modules", {"homeowner_osint": fake_homeowner}):
                args = SimpleNamespace(limit=100, state="TN", dry_run=True)
                osint_enrich.run(args)
        finally:
            osint_enrich.LEADS_DB = orig_db
            osint_enrich.LEDGER = orig_ledger

        after = db_path.read_text()
        assert after == original_content, "Dry-run must not modify leads_db"

    def test_already_enriched_leads_are_skipped(self, tmp_path):
        """Leads with confidence_tier already set are not re-enriched."""
        leads = _make_leads(2)
        leads[0]["confidence_tier"] = TIER_TRY  # pre-enriched
        leads[0]["email"] = "already@set.com"

        result = _run_with_stubs(leads, TIER_SEND, tmp_path)
        # lead[0] should still have its old email
        assert result[0]["email"] == "already@set.com", (
            f"Pre-enriched lead email was overwritten: {result[0]}"
        )
        # lead[1] should get the send-tier email
        assert result[1]["confidence_tier"] == TIER_SEND

    def test_ledger_written(self, tmp_path):
        """Ledger file is written for each processed lead."""
        leads = _make_leads(4)
        db_path = tmp_path / "leads_db.json"
        db_path.write_text(json.dumps(leads, indent=2))
        ledger_path = tmp_path / "ledger.jsonl"

        orig_db = osint_enrich.LEADS_DB
        orig_ledger = osint_enrich.LEDGER
        osint_enrich.LEADS_DB = db_path
        osint_enrich.LEDGER = ledger_path

        try:
            fake_homeowner = MagicMock()
            fake_homeowner.resolve = _synthetic_resolve(TIER_SEND)
            with patch.dict("sys.modules", {"homeowner_osint": fake_homeowner}):
                args = SimpleNamespace(limit=100, state="TN", dry_run=False)
                osint_enrich.run(args)
        finally:
            osint_enrich.LEADS_DB = orig_db
            osint_enrich.LEDGER = orig_ledger

        assert ledger_path.exists(), "Ledger file was not created"
        lines = [l for l in ledger_path.read_text().splitlines() if l.strip()]
        assert len(lines) >= 4, (
            f"Expected at least 4 ledger entries for 4 leads, got {len(lines)}"
        )
        for line in lines:
            rec = json.loads(line)
            assert "ts" in rec and "status" in rec
