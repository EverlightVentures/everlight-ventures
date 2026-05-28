"""
test_enrich_batch.py -- TDD suite for enrich_batch.py.

Strategy:
- Monkeypatch parse_assessor_mhtml.extract_lead to return synthetic owner data.
- Monkeypatch homeowner_osint.resolve with a stub.
- Run a small batch end-to-end (with a tiny synthetic MHTML in tmp_path).
- Assert: send-ready output contains auto_email-tier records, ledger lines
  written, tiers categorized correctly.

No live OSINT, no real MHTML parsing required.
"""
from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_AGENT_ROOT = Path(__file__).parent
sys.path.insert(0, str(_AGENT_ROOT))

# Stub parse_assessor_mhtml so enrich_batch can import without BeautifulSoup
if "parse_assessor_mhtml" not in sys.modules:
    _stub_pam = types.ModuleType("parse_assessor_mhtml")
    _stub_pam.extract_lead = lambda html, source_url="", source_file="": {}
    _stub_pam.extract_html_from_mht = lambda path: ("", "")
    sys.modules["parse_assessor_mhtml"] = _stub_pam

# Stub homeowner_osint
if "homeowner_osint" not in sys.modules:
    _stub_osint = types.ModuleType("homeowner_osint")
    _stub_osint.resolve = lambda *a, **kw: {
        "candidate_emails": [],
        "identity_score": 0,
        "verdict": "stub",
        "raw_investigation_id": "",
    }
    sys.modules["homeowner_osint"] = _stub_osint

# Stub email_confidence_gate
if "email_confidence_gate" not in sys.modules:
    _stub_gate = types.ModuleType("email_confidence_gate")
    def _stub_categorize(candidates, identity_score):
        if not candidates:
            return {"tier": "directmail", "best_email": None, "score": 0,
                    "reason": "no candidates", "ranked": []}
        best = candidates[0]
        score = min(100, (identity_score or 0) + (best.get("confidence") or 0) // 2)
        tier = "auto_email" if score >= 75 else "review" if score >= 55 else "directmail"
        return {
            "tier": tier,
            "best_email": best.get("email"),
            "score": score,
            "reason": "stub",
            "ranked": [{"email": best.get("email"), "score": score, "tier": tier}],
        }
    _stub_gate.categorize = _stub_categorize
    sys.modules["email_confidence_gate"] = _stub_gate

import enrich_batch as eb

# ---------------------------------------------------------------------------
# Synthetic MHTML helper
# ---------------------------------------------------------------------------

MINIMAL_MHTML_TEMPLATE = """\
MIME-Version: 1.0
Content-Type: multipart/related; boundary="----=_Part_0"

------=_Part_0
Content-Type: text/html; charset=utf-8
Content-Location: https://www.assessormelvinburgess.com/propertySearch

<html><body>
<table>
<tr><td>Parcel ID</td><td>{parcel_id}</td></tr>
<tr><td>Property Address</td><td>{property_address}</td></tr>
<tr><td>Owner Name</td><td>{owner_name}</td></tr>
<tr><td>Owner Mailing Address</td><td>{mailing_street}</td></tr>
<tr><td>Owner City/State/Zip</td><td>{mailing_csz}</td></tr>
<tr><td>Year Built</td><td>{year_built}</td></tr>
</table>
</body></html>
------=_Part_0--
"""

SYNTHETIC_OWNERS = [
    {
        "parcel_id": "TEST001",
        "property_address": "101 TEST ST",
        "owner_name": "SMITH JOHN A",
        "mailing_street": "101 TEST ST",
        "mailing_csz": "MEMPHIS TN 38101",
        "year_built": "1965",
    },
    {
        "parcel_id": "TEST002",
        "property_address": "202 DEMO AVE",
        "owner_name": "JOHNSON MARY",
        "mailing_street": "9999 OUT OF STATE RD",
        "mailing_csz": "DALLAS TX 75001",
        "year_built": "1980",
    },
    {
        "parcel_id": "TEST003",
        "property_address": "303 MOCK BLVD",
        "owner_name": "WILLIAMS ESTATE",
        "mailing_street": "303 MOCK BLVD",
        "mailing_csz": "MEMPHIS TN 38103",
        "year_built": "1952",
    },
]


def make_synthetic_inbox(tmp_path: Path, owners: list[dict] = None) -> Path:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for owner in (owners or SYNTHETIC_OWNERS):
        content = MINIMAL_MHTML_TEMPLATE.format(**owner)
        (inbox / f"{owner['parcel_id']}.mht").write_text(content, encoding="utf-8")
    return inbox


# ---------------------------------------------------------------------------
# OSINT stubs
# ---------------------------------------------------------------------------

def make_osint_stub(identity_score: int = 85, email: str = "owner@example.com",
                    confidence: int = 80, verified: bool = True):
    """Factory for OSINT stubs with configurable confidence."""
    def _resolve(name, address="", city="", state="", mailing_address="", lead_id=None):
        return {
            "candidate_emails": [
                {
                    "email": email,
                    "confidence": confidence,
                    "verified": verified,
                    "sources": ["mock"],
                }
            ],
            "identity_score": identity_score,
            "verdict": "strong_match",
            "raw_investigation_id": f"mock-{name[:8]}",
        }
    return _resolve


def make_low_confidence_osint_stub():
    """Returns stub that produces directmail-tier results."""
    def _resolve(name, address="", city="", state="", mailing_address="", lead_id=None):
        return {
            "candidate_emails": [
                {
                    "email": "low@example.com",
                    "confidence": 20,
                    "verified": False,
                    "sources": [],
                }
            ],
            "identity_score": 30,
            "verdict": "weak_match",
            "raw_investigation_id": "mock-low",
        }
    return _resolve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_args(inbox, limit=10, dry_run=False, mock_osint=False):
    return argparse.Namespace(
        inbox=str(inbox),
        limit=limit,
        dry_run=dry_run,
        mock_osint=mock_osint,
    )


def read_ledger(log_dir: Path) -> list[dict]:
    log_file = log_dir / "enrich_batch.jsonl"
    if not log_file.exists():
        return []
    return [json.loads(line) for line in log_file.read_text().strip().splitlines() if line.strip()]


def read_send_ready_files(log_dir: Path) -> list[dict]:
    records = []
    for f in sorted(log_dir.glob("send_ready_*.jsonl")):
        for line in f.read_text().strip().splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Tests: process_file unit tests
# ---------------------------------------------------------------------------

class TestProcessFile:
    """Unit tests for process_file() in isolation."""

    def _make_extract_fn(self, owner_data: dict):
        """Return an extract_lead stub that returns controlled parsed data."""
        def _extract(html, source_url="", source_file=""):
            return {
                "parcel_id": owner_data["parcel_id"],
                "property_address": owner_data["property_address"],
                "owner_name": owner_data["owner_name"],
                "owner_mailing_full": f"{owner_data['mailing_street']}, {owner_data['mailing_csz']}",
            }
        return _extract

    @staticmethod
    def _stub_html_extractor(mht_path):
        """Return minimal HTML stub -- bypasses real MHTML parsing in unit tests."""
        return ("<html><body>stub</body></html>", "https://assessor.test/")

    def test_auto_email_tier_when_high_confidence(self, tmp_path):
        inbox = make_synthetic_inbox(tmp_path, [SYNTHETIC_OWNERS[0]])
        mht = inbox / "TEST001.mht"

        from email_confidence_gate import categorize as real_categorize

        result = eb.process_file(
            mht_path=mht,
            leads=[],
            extract_lead_fn=self._make_extract_fn(SYNTHETIC_OWNERS[0]),
            osint_resolve_fn=make_osint_stub(identity_score=90, confidence=80, verified=True),
            gate_categorize_fn=real_categorize,
            dry_run=True,
            extract_html_fn=self._stub_html_extractor,
        )
        assert result["ok"] is True
        assert result["tier"] == "auto_email"
        assert result["best_email"] == "owner@example.com"
        assert result["score"] >= 75

    def test_directmail_tier_when_low_confidence(self, tmp_path):
        inbox = make_synthetic_inbox(tmp_path, [SYNTHETIC_OWNERS[0]])
        mht = inbox / "TEST001.mht"

        from email_confidence_gate import categorize as real_categorize

        result = eb.process_file(
            mht_path=mht,
            leads=[],
            extract_lead_fn=self._make_extract_fn(SYNTHETIC_OWNERS[0]),
            osint_resolve_fn=make_low_confidence_osint_stub(),
            gate_categorize_fn=real_categorize,
            dry_run=True,
            extract_html_fn=self._stub_html_extractor,
        )
        assert result["ok"] is True
        assert result["tier"] == "directmail"
        assert result["score"] < 55

    def test_error_when_no_owner_name(self, tmp_path):
        inbox = make_synthetic_inbox(tmp_path, [SYNTHETIC_OWNERS[0]])
        mht = inbox / "TEST001.mht"

        def _no_owner_extract(html, source_url="", source_file=""):
            return {"parcel_id": "TEST001", "property_address": "101 TEST ST", "owner_name": ""}

        from email_confidence_gate import categorize as real_categorize
        result = eb.process_file(
            mht_path=mht,
            leads=[],
            extract_lead_fn=_no_owner_extract,
            osint_resolve_fn=make_osint_stub(),
            gate_categorize_fn=real_categorize,
            dry_run=True,
            extract_html_fn=self._stub_html_extractor,
        )
        assert result["ok"] is False
        assert "no_owner_name" in result["error"]


# ---------------------------------------------------------------------------
# Module-level HTML extractor stub (bypasses real MHTML parsing in batch tests)
# ---------------------------------------------------------------------------

def _stub_html_extractor(mht_path):
    """Return minimal HTML stub -- bypasses real MHTML parsing."""
    return ("<html><body>stub</body></html>", "https://assessor.test/")


# ---------------------------------------------------------------------------
# Tests: full batch run
# ---------------------------------------------------------------------------

class TestBatchRun:
    def test_auto_email_leads_in_send_ready(self, tmp_path, monkeypatch):
        """End-to-end: 3 files, high-confidence OSINT -> send-ready has all 3."""
        inbox = make_synthetic_inbox(tmp_path)
        log_dir = tmp_path / "_logs/enrichment"

        monkeypatch.setattr(eb, "LOG_DIR", log_dir)
        monkeypatch.setattr(eb, "BATCH_LOG", log_dir / "enrich_batch.jsonl")
        monkeypatch.setattr(eb, "load_leads", lambda: [])
        monkeypatch.setattr(eb, "save_leads", lambda _: None)
        monkeypatch.setattr(eb, "_default_extract_html", _stub_html_extractor)

        from email_confidence_gate import categorize as real_categorize

        def _extract(html, source_url="", source_file=""):
            name = Path(source_file).stem if source_file else "UNKNOWN"
            return {
                "parcel_id": name,
                "property_address": f"{name} ST",
                "owner_name": f"OWNER {name}",
                "owner_mailing_full": "101 ANYWHERE, MEMPHIS TN 38101",
            }

        monkeypatch.setattr(
            eb, "_load_modules",
            lambda: (_extract, make_osint_stub(identity_score=90, confidence=80, verified=True), real_categorize)
        )

        args = make_args(inbox=inbox, limit=3, dry_run=False, mock_osint=False)
        rc = eb.run(args)
        assert rc == 0

        # Ledger should have 3 entries
        ledger = read_ledger(log_dir)
        assert len(ledger) == 3

        # All 3 should be auto_email
        tiers = [e.get("tier") for e in ledger]
        assert all(t == "auto_email" for t in tiers), f"Expected all auto_email, got: {tiers}"

        # Send-ready file should exist with 3 records
        send_ready = read_send_ready_files(log_dir)
        assert len(send_ready) == 3
        for rec in send_ready:
            assert rec["tier"] == "auto_email"
            assert rec["best_email"] == "owner@example.com"
            assert rec["score"] >= 75

    def test_mixed_tiers_correctly_bucketed(self, tmp_path, monkeypatch):
        """One high-confidence lead, one low-confidence lead -> correct tier split."""
        owners = [SYNTHETIC_OWNERS[0], SYNTHETIC_OWNERS[1]]
        inbox = make_synthetic_inbox(tmp_path, owners)
        log_dir = tmp_path / "_logs/enrichment"

        monkeypatch.setattr(eb, "LOG_DIR", log_dir)
        monkeypatch.setattr(eb, "BATCH_LOG", log_dir / "enrich_batch.jsonl")
        monkeypatch.setattr(eb, "load_leads", lambda: [])
        monkeypatch.setattr(eb, "save_leads", lambda _: None)
        monkeypatch.setattr(eb, "_default_extract_html", _stub_html_extractor)

        from email_confidence_gate import categorize as real_categorize

        call_count = [0]
        def _alternating_osint(name, address="", city="", state="", mailing_address="", lead_id=None):
            """First call returns high confidence; second returns low confidence."""
            call_count[0] += 1
            if call_count[0] == 1:
                return make_osint_stub(identity_score=90, confidence=80, verified=True)(name)
            else:
                return make_low_confidence_osint_stub()(name)

        def _extract(html, source_url="", source_file=""):
            name = Path(source_file).stem if source_file else "X"
            return {"parcel_id": name, "property_address": f"{name} ST", "owner_name": f"OWNER {name}"}

        monkeypatch.setattr(eb, "_load_modules", lambda: (_extract, _alternating_osint, real_categorize))

        args = make_args(inbox=inbox, limit=2, dry_run=False)
        rc = eb.run(args)
        assert rc == 0

        ledger = read_ledger(log_dir)
        assert len(ledger) == 2

        tiers = [e.get("tier") for e in ledger]
        assert "auto_email" in tiers
        assert "directmail" in tiers

        # Only the auto_email one should appear in send-ready
        send_ready = read_send_ready_files(log_dir)
        assert len(send_ready) == 1
        assert send_ready[0]["tier"] == "auto_email"

    def test_dry_run_no_ledger_written(self, tmp_path, monkeypatch):
        """dry-run: no ledger, no send-ready file, no leads_db write."""
        inbox = make_synthetic_inbox(tmp_path, [SYNTHETIC_OWNERS[0]])
        log_dir = tmp_path / "_logs/enrichment"

        monkeypatch.setattr(eb, "LOG_DIR", log_dir)
        monkeypatch.setattr(eb, "BATCH_LOG", log_dir / "enrich_batch.jsonl")
        monkeypatch.setattr(eb, "save_leads", lambda _: pytest.fail("save_leads called in dry-run"))
        monkeypatch.setattr(eb, "_default_extract_html", _stub_html_extractor)

        from email_confidence_gate import categorize as real_categorize

        def _extract(html, source_url="", source_file=""):
            return {"parcel_id": "TEST001", "property_address": "101 TEST ST", "owner_name": "SMITH JOHN"}

        monkeypatch.setattr(eb, "_load_modules", lambda: (_extract, make_osint_stub(), real_categorize))

        args = make_args(inbox=inbox, limit=5, dry_run=True)
        rc = eb.run(args)
        assert rc == 0

        # No ledger
        assert not (log_dir / "enrich_batch.jsonl").exists()
        # No send-ready files
        assert list(log_dir.glob("send_ready_*.jsonl")) == []

    def test_empty_inbox_returns_zero(self, tmp_path, monkeypatch):
        """Empty inbox should exit cleanly."""
        inbox = tmp_path / "empty_inbox"
        inbox.mkdir()

        monkeypatch.setattr(eb, "load_leads", lambda: [])
        monkeypatch.setattr(eb, "save_leads", lambda _: None)

        args = make_args(inbox=inbox, limit=10)
        rc = eb.run(args)
        assert rc == 0

    def test_leads_db_updated_for_matched_lead(self, tmp_path, monkeypatch):
        """When a lead matches by parcel_id, best_email + tier are written back."""
        inbox = make_synthetic_inbox(tmp_path, [SYNTHETIC_OWNERS[0]])
        log_dir = tmp_path / "_logs/enrichment"

        monkeypatch.setattr(eb, "LOG_DIR", log_dir)
        monkeypatch.setattr(eb, "BATCH_LOG", log_dir / "enrich_batch.jsonl")
        monkeypatch.setattr(eb, "_default_extract_html", _stub_html_extractor)

        existing_leads = [
            {
                "parcel_id": "TEST001",
                "address": "101 TEST ST, MEMPHIS, TN",
                "state": "TN",
                "owner_name": "SMITH JOHN A",
            }
        ]
        saved_leads_container = []

        monkeypatch.setattr(eb, "load_leads", lambda: list(existing_leads))
        monkeypatch.setattr(eb, "save_leads", lambda leads: saved_leads_container.extend(leads))

        from email_confidence_gate import categorize as real_categorize

        def _extract(html, source_url="", source_file=""):
            return {"parcel_id": "TEST001", "property_address": "101 TEST ST", "owner_name": "SMITH JOHN A"}

        monkeypatch.setattr(eb, "_load_modules", lambda: (
            _extract,
            make_osint_stub(identity_score=90, confidence=80, verified=True, email="smith@test.com"),
            real_categorize,
        ))

        args = make_args(inbox=inbox, limit=1, dry_run=False)
        rc = eb.run(args)
        assert rc == 0

        assert saved_leads_container, "save_leads was never called"
        updated_lead = next((l for l in saved_leads_container if l.get("parcel_id") == "TEST001"), None)
        assert updated_lead is not None
        assert updated_lead["best_email"] == "smith@test.com"
        assert updated_lead["confidence_tier"] == "auto_email"
        assert updated_lead["confidence_score"] >= 75
