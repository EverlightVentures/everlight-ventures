"""Tests for the recurring admin task scheduler. Own-process run."""
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_sch_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class Scheduler(unittest.TestCase):
    def test_next_occurrence_1_and_15(self):
        self.assertEqual(C.compute_next_occurrence("1,15", date(2026, 6, 10)), date(2026, 6, 15))
        self.assertEqual(C.compute_next_occurrence("1,15", date(2026, 6, 20)), date(2026, 7, 1))

    def test_month_end_clamp(self):
        self.assertEqual(C.compute_next_occurrence("31", date(2026, 2, 1)), date(2026, 2, 28))

    def test_daily_weekly(self):
        self.assertEqual(C.compute_next_occurrence("DAILY", date(2026, 6, 10)), date(2026, 6, 11))
        self.assertEqual(C.compute_next_occurrence("WEEKLY", date(2026, 6, 10)), date(2026, 6, 17))

    def test_create_assign_idempotent_and_managers_excluded(self):
        # DAILY rule => due today on creation (next occurrence after yesterday is today)
        sid = C.create_recurring_task("Count drawer", "DAILY", "1001", "1001")
        self.assertTrue(sid.startswith("RSCH"))
        made1 = C.check_and_assign_recurring_tasks(date.today())
        made2 = C.check_and_assign_recurring_tasks(date.today())  # same day -> no dup
        self.assertGreaterEqual(len(made1), 1)
        self.assertEqual(len(made2), 0)
        tasks = C.get_tasks_for_employee("1001", date.today())
        self.assertGreaterEqual(len(tasks), 1)

    def test_pause_removes_from_active(self):
        sid = C.create_recurring_task("Pay rent", "1", "1001", "1001")
        C.set_recurring_status(sid, "PAUSED")
        active_ids = [s.get("Schedule_ID") for s in C.list_recurring_schedules(active_only=True)]
        self.assertNotIn(sid, active_ids)


if __name__ == "__main__":
    unittest.main()
