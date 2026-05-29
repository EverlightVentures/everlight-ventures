"""test_sb909_notice.py -- pytest suite for sb909_notice.py

Run:
    cd 01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent
    pytest test_sb909_notice.py -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Add the wholesale_agent dir to sys.path so imports resolve
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# ---------------------------------------------------------------------------
# Patch the ledger path to a temp file for every test so tests are hermetic
# ---------------------------------------------------------------------------
import pytest
import sb909_notice  # noqa: E402  (import after sys.path fixup)


@pytest.fixture(autouse=True)
def _isolated_ledger(tmp_path, monkeypatch):
    """Point the ledger at a per-test temp file."""
    ledger = tmp_path / "sb909_notices.jsonl"
    monkeypatch.setattr(sb909_notice, "_LEDGER_PATH", ledger)
    yield ledger


# ---------------------------------------------------------------------------
# business_days_between
# ---------------------------------------------------------------------------


class TestBusinessDaysBetween:
    def test_fri_to_mon_is_1(self):
        """Friday to Monday spans the weekend; only Monday counts."""
        fri = date(2026, 5, 22)  # known Friday
        mon = date(2026, 5, 25)  # known Monday
        assert sb909_notice.business_days_between(fri, mon) == 1

    def test_mon_to_thu_is_3(self):
        mon = date(2026, 5, 25)
        thu = date(2026, 5, 28)
        assert sb909_notice.business_days_between(mon, thu) == 3

    def test_same_day_is_0(self):
        d = date(2026, 5, 26)
        assert sb909_notice.business_days_between(d, d) == 0

    def test_end_before_start_is_0(self):
        assert sb909_notice.business_days_between(date(2026, 5, 28), date(2026, 5, 25)) == 0

    def test_weekend_days_not_counted(self):
        """Mon to next Mon = 5 business days."""
        mon1 = date(2026, 5, 25)
        mon2 = date(2026, 6, 1)
        assert sb909_notice.business_days_between(mon1, mon2) == 5

    def test_fri_to_wed_next_week_is_3(self):
        """Fri -> Mon (1) -> Tue (2) -> Wed (3)."""
        fri = date(2026, 5, 22)
        wed = date(2026, 5, 27)
        assert sb909_notice.business_days_between(fri, wed) == 3


# ---------------------------------------------------------------------------
# notice_clear_date
# ---------------------------------------------------------------------------


class TestNoticeClearDate:
    def _monday_dt(self) -> datetime:
        """Monday 2026-05-25 09:00 UTC"""
        return datetime(2026, 5, 25, 9, 0, 0, tzinfo=timezone.utc)

    def _friday_dt(self) -> datetime:
        """Friday 2026-05-22 14:00 UTC"""
        return datetime(2026, 5, 22, 14, 0, 0, tzinfo=timezone.utc)

    def test_sent_monday_clears_thursday(self):
        """Mon -> +1 Tue, +2 Wed, +3 Thu.  Clears Thursday 00:00 UTC."""
        clear = sb909_notice.notice_clear_date(self._monday_dt())
        assert clear.date() == date(2026, 5, 28)  # Thursday

    def test_sent_friday_clears_wednesday(self):
        """Fri anchor: +1 Mon, +2 Tue, +3 Wed.  Clears Wednesday 00:00 UTC."""
        clear = sb909_notice.notice_clear_date(self._friday_dt())
        assert clear.date() == date(2026, 5, 27)  # Wednesday

    def test_returns_midnight_utc(self):
        clear = sb909_notice.notice_clear_date(self._monday_dt())
        assert clear.hour == 0
        assert clear.minute == 0
        assert clear.second == 0
        assert clear.tzinfo == timezone.utc

    def test_sent_saturday_clears_wednesday(self):
        """Sat is treated as Fri anchor: same result as Friday send."""
        sat_dt = datetime(2026, 5, 23, 10, 0, 0, tzinfo=timezone.utc)
        clear = sb909_notice.notice_clear_date(sat_dt)
        assert clear.date() == date(2026, 5, 27)

    def test_sent_sunday_clears_wednesday(self):
        """Sun is treated as Fri anchor."""
        sun_dt = datetime(2026, 5, 24, 10, 0, 0, tzinfo=timezone.utc)
        clear = sb909_notice.notice_clear_date(sun_dt)
        assert clear.date() == date(2026, 5, 27)


# ---------------------------------------------------------------------------
# render_sb909_notice
# ---------------------------------------------------------------------------


_RITA_LEAD = {
    "owner_name": "TOWNSEND RITA M",
    "address": "836 N BELLEVUE, MEMPHIS, TN 38107",
    "email": "rita.townsend@gmail.com",
    "state": "TN",
    "parcel_id": "021083  00056",
}

_RITA_DEAL_TERMS = {
    "assignment_fee": 11500,
    "purchase_price": 55000,
    "end_buyer": "Mid South Homebuyers, LLC (Chris Ulander)",
}


class TestRenderSb909Notice:
    def _rendered(self):
        return sb909_notice.render_sb909_notice(_RITA_LEAD, _RITA_DEAL_TERMS)

    def test_returns_subject_and_body(self):
        out = self._rendered()
        assert "subject" in out
        assert "body_html" in out

    def test_body_contains_assign(self):
        body = self._rendered()["body_html"].lower()
        assert "assign" in body

    def test_body_contains_assignment_fee(self):
        """The rendered notice must state the $11,500 fee."""
        body = self._rendered()["body_html"]
        assert "11,500" in body

    def test_body_contains_3_business_days(self):
        body = self._rendered()["body_html"].lower()
        assert "3 business days" in body or "three (3) business days" in body.lower()

    def test_body_contains_cancel_instruction(self):
        """Seller must know HOW to cancel."""
        body = self._rendered()["body_html"].lower()
        assert "cancel" in body

    def test_body_signs_as_sole_prop(self):
        """Must say 'sole proprietor' (or d/b/a) -- never 'LLC'."""
        body = self._rendered()["body_html"].lower()
        assert "sole proprietor" in body or "d/b/a" in body

    def test_body_no_llc(self):
        """Richard Gee has NOT formed the LLC yet -- it must NOT appear."""
        body = self._rendered()["body_html"]
        # The end_buyer may contain 'LLC' for Mid South Homebuyers -- that is
        # acceptable.  The SIGNER must not claim to be an LLC.
        # Strip the end-buyer mention and check the signer block.
        signer_section = body.split("Sincerely,", 1)[-1] if "Sincerely," in body else body
        assert "Everlight Ventures LLC" not in signer_section
        assert "Everlight Logistics LLC" not in signer_section

    def test_subject_contains_address(self):
        subject = self._rendered()["subject"]
        assert "836" in subject or "BELLEVUE" in subject or "TN" in subject


# ---------------------------------------------------------------------------
# send_sb909_notice (dry_run=True)
# ---------------------------------------------------------------------------


class TestSendSb909NoticeDryRun:
    _DEAL = {"deal_id": "tn_rita_001"}

    def test_dry_run_returns_row(self):
        row = sb909_notice.send_sb909_notice(
            self._DEAL, _RITA_LEAD, _RITA_DEAL_TERMS, dry_run=True
        )
        assert row["deal_id"] == "tn_rita_001"
        assert row["dry_run"] is True
        assert row["seller_email"] == "rita.townsend@gmail.com"
        assert row["assignment_fee"] == 11500
        assert "sent_ts" in row
        assert "clear_date" in row

    def test_dry_run_writes_nothing(self, _isolated_ledger):
        sb909_notice.send_sb909_notice(
            self._DEAL, _RITA_LEAD, _RITA_DEAL_TERMS, dry_run=True
        )
        assert not _isolated_ledger.exists(), (
            "dry_run=True must NOT write to the ledger"
        )

    def test_dry_run_sends_nothing(self):
        """No email should be sent during dry_run."""
        mock_rutils = mock.MagicMock()
        mock_rutils.safe_send_email.return_value = True
        # Inject a fake rex_utils into sys.modules so the import inside
        # send_sb909_notice resolves to our mock.
        with mock.patch.dict(sys.modules, {"rex_utils": mock_rutils}):
            sb909_notice.send_sb909_notice(
                self._DEAL, _RITA_LEAD, _RITA_DEAL_TERMS, dry_run=True
            )
            # dry_run=True must return BEFORE ever calling safe_send_email.
            mock_rutils.safe_send_email.assert_not_called()


# ---------------------------------------------------------------------------
# assignment_gate
# ---------------------------------------------------------------------------


class TestAssignmentGate:
    _DEAL_ID = "tn_gate_test_001"

    def test_blocks_with_no_notice(self):
        ok, reason = sb909_notice.assignment_gate(self._DEAL_ID)
        assert ok is False
        assert reason == "no_sb909_notice_sent"

    def test_blocks_before_clear_date(self, _isolated_ledger):
        """Write a real notice row but set clear_date in the future."""
        sent_ts = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
        clear_dt = datetime(2026, 5, 28, 0, 0, tzinfo=timezone.utc)
        row = {
            "row_type": "sb909_notice",
            "deal_id": self._DEAL_ID,
            "seller_email": "test@example.com",
            "sent_ts": sent_ts.isoformat(),
            "clear_date": clear_dt.isoformat(),
            "assignment_fee": 11500,
            "message_id": None,
            "dry_run": False,
        }
        with _isolated_ledger.open("w") as f:
            f.write(json.dumps(row) + "\n")

        # Now = one day BEFORE clear_date
        now_before = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc)
        ok, reason = sb909_notice.assignment_gate(self._DEAL_ID, now=now_before)
        assert ok is False
        assert "sb909_3day_clock_not_elapsed" in reason
        assert "2026-05-28" in reason

    def test_allows_after_clear_date(self, _isolated_ledger):
        """Real notice + now AFTER clear_date -> cleared."""
        sent_ts = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
        clear_dt = datetime(2026, 5, 28, 0, 0, tzinfo=timezone.utc)
        row = {
            "row_type": "sb909_notice",
            "deal_id": self._DEAL_ID,
            "seller_email": "test@example.com",
            "sent_ts": sent_ts.isoformat(),
            "clear_date": clear_dt.isoformat(),
            "assignment_fee": 11500,
            "message_id": None,
            "dry_run": False,
        }
        with _isolated_ledger.open("w") as f:
            f.write(json.dumps(row) + "\n")

        # now = clear_date + 1 hour
        now_after = datetime(2026, 5, 28, 1, 0, tzinfo=timezone.utc)
        ok, reason = sb909_notice.assignment_gate(self._DEAL_ID, now=now_after)
        assert ok is True
        assert reason == "sb909_cleared"

    def test_blocks_on_rescission(self, _isolated_ledger):
        """Even after clear_date, a rescission row blocks."""
        sent_ts = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
        clear_dt = datetime(2026, 5, 28, 0, 0, tzinfo=timezone.utc)
        notice_row = {
            "row_type": "sb909_notice",
            "deal_id": self._DEAL_ID,
            "seller_email": "test@example.com",
            "sent_ts": sent_ts.isoformat(),
            "clear_date": clear_dt.isoformat(),
            "assignment_fee": 11500,
            "message_id": None,
            "dry_run": False,
        }
        rescission_row = {
            "row_type": "sb909_rescission",
            "deal_id": self._DEAL_ID,
            "recorded_ts": datetime(2026, 5, 26, 10, 0, tzinfo=timezone.utc).isoformat(),
            "reason": "seller_called_cancel",
        }
        with _isolated_ledger.open("w") as f:
            f.write(json.dumps(notice_row) + "\n")
            f.write(json.dumps(rescission_row) + "\n")

        now_after = datetime(2026, 5, 29, 0, 0, tzinfo=timezone.utc)
        ok, reason = sb909_notice.assignment_gate(self._DEAL_ID, now=now_after)
        assert ok is False
        assert reason == "seller_rescinded"

    def test_dry_run_notice_does_not_clear(self, _isolated_ledger):
        """A dry_run=True row must NOT satisfy the gate."""
        sent_ts = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
        clear_dt = datetime(2026, 5, 28, 0, 0, tzinfo=timezone.utc)
        row = {
            "row_type": "sb909_notice",
            "deal_id": self._DEAL_ID,
            "seller_email": "test@example.com",
            "sent_ts": sent_ts.isoformat(),
            "clear_date": clear_dt.isoformat(),
            "assignment_fee": 11500,
            "message_id": None,
            "dry_run": True,  # <-- dry run
        }
        with _isolated_ledger.open("w") as f:
            f.write(json.dumps(row) + "\n")

        now_after = datetime(2026, 5, 29, 0, 0, tzinfo=timezone.utc)
        ok, reason = sb909_notice.assignment_gate(self._DEAL_ID, now=now_after)
        assert ok is False
        assert reason == "no_sb909_notice_sent"

    def test_fails_closed_on_unreadable_ledger(self, monkeypatch):
        """If the ledger raises on read, gate must block (fail closed)."""
        def _boom():
            raise IOError("disk error")
        monkeypatch.setattr(sb909_notice, "_read_ledger", _boom)
        ok, reason = sb909_notice.assignment_gate(self._DEAL_ID)
        assert ok is False
        assert "ledger_read_error" in reason

    def test_only_matches_own_deal_id(self, _isolated_ledger):
        """Notice for deal_X must NOT clear deal_Y."""
        sent_ts = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)
        clear_dt = datetime(2026, 5, 28, 0, 0, tzinfo=timezone.utc)
        row = {
            "row_type": "sb909_notice",
            "deal_id": "DIFFERENT_DEAL",
            "seller_email": "other@example.com",
            "sent_ts": sent_ts.isoformat(),
            "clear_date": clear_dt.isoformat(),
            "assignment_fee": 5000,
            "message_id": None,
            "dry_run": False,
        }
        with _isolated_ledger.open("w") as f:
            f.write(json.dumps(row) + "\n")

        now_after = datetime(2026, 5, 29, 0, 0, tzinfo=timezone.utc)
        ok, reason = sb909_notice.assignment_gate(self._DEAL_ID, now=now_after)
        assert ok is False
        assert reason == "no_sb909_notice_sent"


# ---------------------------------------------------------------------------
# record_rescission
# ---------------------------------------------------------------------------


class TestRecordRescission:
    def test_writes_rescission_row(self, _isolated_ledger):
        sb909_notice.record_rescission("tn_test_002", "seller called to cancel")
        rows = [json.loads(l) for l in _isolated_ledger.read_text().splitlines() if l.strip()]
        assert len(rows) == 1
        r = rows[0]
        assert r["row_type"] == "sb909_rescission"
        assert r["deal_id"] == "tn_test_002"
        assert "cancel" in r["reason"]

    def test_blocks_gate_after_rescission(self, _isolated_ledger):
        """record_rescission + gate check = blocked."""
        sb909_notice.record_rescission("tn_test_002")
        ok, reason = sb909_notice.assignment_gate("tn_test_002")
        assert ok is False
        assert reason == "seller_rescinded"


# ---------------------------------------------------------------------------
# Integration: render Rita's notice (operator readability check)
# ---------------------------------------------------------------------------


def test_rita_notice_full_render():
    """Render Rita Townsend's notice at $11,500 -- human-readable output test."""
    out = sb909_notice.render_sb909_notice(_RITA_LEAD, _RITA_DEAL_TERMS)
    body = out["body_html"]

    # All mandatory legal elements
    assert "11,500" in body, "assignment fee must be in notice"
    assert "3 business" in body.lower() or "three (3) business" in body.lower()
    assert "assign" in body.lower()
    assert "cancel" in body.lower()
    assert "richard gee" in body.lower(), "sole-prop signer must appear"
    assert "sole proprietor" in body.lower() or "d/b/a" in body.lower()
    # Seller name appears
    assert "TOWNSEND" in body or "townsend" in body.lower()
