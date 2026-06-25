"""Regression tests for the 2026-06 employee fixes: name-saves-on-add, blank-name
guard, and owner set-specific-PIN. Run in its own process (shared POS_CORE.DATA_DIR
module global), against a temp data dir."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_emp_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE as C  # noqa: E402


class EmployeeFixes(unittest.TestCase):
    def test_compose_full_name(self):
        # The actual add-employee bug: form posts first/last, route read a missing
        # "name". compose_full_name is the combine that fixes it.
        self.assertEqual(C.compose_full_name("John", "Smith"), "John Smith")
        self.assertEqual(C.compose_full_name("  Maria ", " Lopez "), "Maria Lopez")
        self.assertEqual(C.compose_full_name("", "", "Solo Name"), "Solo Name")
        self.assertEqual(C.compose_full_name("Cher", ""), "Cher")
        self.assertEqual(C.compose_full_name("", ""), "")

    def test_blank_name_rejected_writes_no_row(self):
        before = len(C.get_all_employees(include_inactive=True))
        ok, _msg, eid = C.create_employee("   ", "Cashier", "1234")
        self.assertFalse(ok)
        self.assertEqual(eid, "")
        self.assertEqual(len(C.get_all_employees(include_inactive=True)), before)

    def test_name_persists_on_create(self):
        ok, msg, eid = C.create_employee("Jane Doe", "Cashier", "4444")
        self.assertTrue(ok, msg)
        self.assertEqual(C.get_employee(eid)["Employee_Name"], "Jane Doe")

    def test_bad_pin_rejected(self):
        ok, _msg, _eid = C.create_employee("Bad Pin", "Cashier", "12")
        self.assertFalse(ok)

    def test_set_specific_pin_value(self):
        ok, msg, eid = C.create_employee("Pin Person", "Cashier", "1111")
        self.assertTrue(ok, msg)
        ok2, msg2 = C.reset_pin(eid, "4321", "1001", "Owner")
        self.assertTrue(ok2, msg2)
        self.assertEqual(C.get_employee(eid)["PIN"], "4321")

    def test_set_pin_rejects_non_4_digit(self):
        ok, msg, eid = C.create_employee("Pin Two", "Cashier", "2222")
        self.assertTrue(ok, msg)
        ok2, _msg2 = C.reset_pin(eid, "12", "1001", "Owner")
        self.assertFalse(ok2)


if __name__ == "__main__":
    unittest.main()
