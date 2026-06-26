"""Tests for the backup engine. Own-process run."""
import importlib.util as ilu
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_bk_")
os.environ["MGN_DATA_DIR"] = _TMP
os.environ["MGN_BACKUP_DIR"] = os.path.join(_TMP, "_backups")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_p = Path(__file__).resolve().parent / "backup_data.py"
_s = ilu.spec_from_file_location("backup_data", str(_p))
B = ilu.module_from_spec(_s)
_s.loader.exec_module(B)


class Backup(unittest.TestCase):
    def setUp(self):
        (Path(_TMP) / "Sales_Logs").mkdir(exist_ok=True)
        (Path(_TMP) / "Sales_Logs" / "x.csv").write_text("a,b\n1,2\n")
        (Path(_TMP) / "Items.csv").write_text("SKU\nT1\n")

    def test_create_contains_data_and_lists(self):
        r = B.create_backup(stamp="20260625-000001")
        self.assertTrue(os.path.exists(r["file"]))
        self.assertFalse(r["encrypted"])           # no passphrase set
        with tarfile.open(r["file"]) as t:
            names = t.getnames()
        self.assertTrue(any("Items.csv" in n for n in names))
        self.assertTrue(any("Sales_Logs" in n for n in names))
        self.assertTrue(any(i["name"].startswith("mgn_backup_") for i in B.list_backups()))

    def test_rotation_keeps_n(self):
        for i in range(5):
            B.create_backup(stamp=f"20260625-10000{i}", keep=3)
        self.assertLessEqual(len(B.list_backups()), 3)


if __name__ == "__main__":
    unittest.main()
