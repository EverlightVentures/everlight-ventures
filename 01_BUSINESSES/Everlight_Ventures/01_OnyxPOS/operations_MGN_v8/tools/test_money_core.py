"""Tests for the Money OS engine brain (money_core). Runs against a temp data dir."""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mgn_money_")
os.environ["MGN_DATA_DIR"] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import POS_CORE  # noqa: E402
import money_core as M  # noqa: E402

PAY_CFG_HEADERS = ["Employee_ID", "Pay_Type", "Hourly_Rate", "Salary_Amount", "Pay_Frequency"]
PERIOD_HEADERS = ["Period_ID", "Start_Date", "End_Date", "Pay_Date", "Status"]


def _punch(d, emp, ptype, t):
    POS_CORE.append_csv(POS_CORE.get_timeclock_path(d), POS_CORE.TIMECLOCK_HEADERS, {
        "Punch_ID": POS_CORE.generate_id("P"), "Date": d.strftime("%Y-%m-%d"), "Time": t,
        "Employee_ID": emp, "Employee_Name": emp, "Punch_Type": ptype})


def _sale(d, line_total, cogs, tax):
    POS_CORE.append_csv(POS_CORE.get_sales_path(d), POS_CORE.SALES_HEADERS, {
        "Date": d.strftime("%Y-%m-%d"), "Transaction_ID": POS_CORE.generate_id("TRX"),
        "Item_Name": "x", "SKU": "x", "Quantity": "1",
        "COGS_Line": str(cogs), "Tax_Amount": str(tax), "Line_Total": str(line_total)})


class MoneyCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # clean Money_OS so this class's P&L scenario has zero overhead regardless of
        # other test classes (shared temp dir; classes run alphabetically)
        shutil.rmtree(Path(_TMP) / "Money_OS", ignore_errors=True)
        # hourly employee $20/hr
        POS_CORE.append_csv(Path(_TMP) / "Payroll" / "Employee_Pay_Config.csv", PAY_CFG_HEADERS,
                            {"Employee_ID": "1004", "Pay_Type": "HOURLY", "Hourly_Rate": "20",
                             "Salary_Amount": "0", "Pay_Frequency": "WEEKLY"})
        cls.today = date.today()
        # today: 10h worked -> 8 reg + 2 OT ; a $500 sale (COGS 200, tax 41.25)
        _punch(cls.today, "1004", "CLOCK_IN", "09:00:00")
        _punch(cls.today, "1004", "CLOCK_OUT", "19:00:00")
        _sale(cls.today, 500.0, 200.0, 41.25)

    def test_labor_cost_is_ot_correct(self):
        lc = M.compute_labor_cost_for_date(self.today)
        # 8*20 + 2*20*1.5 = 220 ; employer tax 12%
        self.assertEqual(lc["wages"], 220.0)
        self.assertEqual(lc["employer_tax"], 26.4)

    def test_daily_pnl(self):
        p = M.compute_daily_pnl(self.today)
        self.assertEqual(p["revenue"], 500.0)
        self.assertEqual(p["cogs"], 200.0)
        self.assertEqual(p["gross_profit"], 300.0)
        self.assertEqual(p["labor_cost"], 220.0)
        self.assertEqual(p["net_profit"], 53.6)        # 300 - 220 - 26.4 - 0 overhead
        self.assertEqual(p["sales_tax_collected"], 41.25)
        self.assertEqual(p["flag"], "PROFITABLE")

    def test_allocation_sweeps_sales_tax_and_sets_aside(self):
        M.allocate_for_date(self.today)
        envs = {e["Envelope"]: float(e["Balance"]) for e in M.get_envelopes()}
        self.assertAlmostEqual(envs["SALES_TAX"], 41.25, places=2)   # collected tax swept
        self.assertAlmostEqual(envs["PAYROLL"], round(53.6 * 0.30, 2), places=2)  # 30% of net
        # idempotent
        again = M.allocate_for_date(self.today)
        self.assertTrue(again.get("skipped"))
        envs2 = {e["Envelope"]: float(e["Balance"]) for e in M.get_envelopes()}
        self.assertAlmostEqual(envs2["SALES_TAX"], 41.25, places=2)

    def test_cash_manual(self):
        M.set_cash_manual(1000, by="1001")
        c = M.get_cash_on_hand()
        self.assertEqual(c["amount"], 1000.0)
        self.assertEqual(c["source"], "MANUAL")

    def test_readiness_current_period_gap(self):
        POS_CORE.append_csv(Path(_TMP) / "Payroll" / "Pay_Periods.csv", PERIOD_HEADERS,
                            {"Period_ID": "PP-NOW", "Start_Date": self.today.strftime("%Y-%m-%d"),
                             "End_Date": (self.today + timedelta(days=6)).strftime("%Y-%m-%d"),
                             "Pay_Date": (self.today + timedelta(days=7)).strftime("%Y-%m-%d"),
                             "Status": "OPEN"})
        M.set_cash_manual(5000, by="1001")
        r = M.payroll_readiness()
        self.assertGreaterEqual(r["accrued_to_date"], 220.0)   # today's wages accrued
        self.assertEqual(r["gap"], 0.0)                        # 5000 cash covers it
        # (alert level depends on whether other periods are unrun -- asserted in the catch-up test)

    def test_catch_up_flags_unrun_past_period(self):
        past_day = self.today - timedelta(days=5)
        _punch(past_day, "1004", "CLOCK_IN", "09:00:00")
        _punch(past_day, "1004", "CLOCK_OUT", "17:00:00")   # 8h -> $160
        POS_CORE.append_csv(Path(_TMP) / "Payroll" / "Pay_Periods.csv", PERIOD_HEADERS,
                            {"Period_ID": "PP-OLD", "Start_Date": (self.today - timedelta(days=7)).strftime("%Y-%m-%d"),
                             "End_Date": (self.today - timedelta(days=3)).strftime("%Y-%m-%d"),
                             "Pay_Date": (self.today - timedelta(days=2)).strftime("%Y-%m-%d"),
                             "Status": "OPEN"})
        r = M.payroll_readiness()
        self.assertGreaterEqual(r["catch_up"], 160.0)
        self.assertEqual(r["alert_level"], "BLACK")


RUN_HEADERS = ["Payroll_ID", "Period_ID", "Employee_ID", "Gross_Pay", "Federal_Tax",
               "State_Tax", "Social_Security", "Medicare", "CA_SDI", "Net_Pay", "Status"]


class BillsAndFiling(unittest.TestCase):
    def test_recurring_bill_materializes_once(self):
        due_day = date.today().day  # due today -> within window
        M.add_overhead("Rent Co", "Rent", 2000, "MONTHLY", due_day)
        first = M.generate_due_bills()
        second = M.generate_due_bills()  # idempotent
        self.assertGreaterEqual(first, 1)
        self.assertEqual(second, 0)

    def test_bill_lifecycle_and_priority(self):
        bid = M.add_bill("Vendor X", 150, date.today().strftime("%Y-%m-%d"))
        M.approve_bill(bid, "1001")
        view = M.bill_priority_view()
        self.assertIn("available_after_payroll", view)
        self.assertTrue(any(b["Bill_ID"] == bid for b in view["bills"]))
        M.pay_bill(bid, "1001")
        paid = [b for b in POS_CORE.read_csv(M._p("Bills.csv", M.BILLS_HEADERS)) if b["Bill_ID"] == bid]
        self.assertEqual(paid[0]["Status"], "PAID")

    def test_autopilot_mode_and_arm(self):
        self.assertEqual(M.set_autopilot_mode("ARMED"), "ARMED")
        self.assertEqual(M.get_autopilot_mode(), "ARMED")
        M.add_overhead("AutoUtil", "Utilities", 120, "MONTHLY", date.today().day, autopay="Y")
        M.add_bill("AutoUtil", 120, date.today().strftime("%Y-%m-%d"), source="manual")
        res = M.run_autopilot(ceiling=500)
        self.assertEqual(res["mode"], "ARMED")
        self.assertTrue(any(a["vendor"] == "AutoUtil" for a in res["actions"]))
        M.set_autopilot_mode("SUGGEST")  # reset so it doesn't leak

    def test_filing_summary_deposit_figures(self):
        yr = date.today().year
        path = Path(_TMP) / "Payroll" / f"{yr}_Payroll_Runs.csv"
        POS_CORE.append_csv(path, RUN_HEADERS, {
            "Payroll_ID": "PR1", "Period_ID": "PP-FILE", "Employee_ID": "1004", "Gross_Pay": "1000",
            "Federal_Tax": "100", "State_Tax": "30", "Social_Security": "62", "Medicare": "14.5",
            "CA_SDI": "13", "Net_Pay": "780", "Status": "PROCESSED"})
        f = M.filing_summary("PP-FILE", yr)
        self.assertEqual(f["federal_deposit_eftps"], 253.0)   # 100 + 2*62 + 2*14.5
        self.assertEqual(f["ca_deposit_de88"], 78.0)          # 30 + 13 + 35 (UI/ETT est)
        self.assertEqual(f["direct_deposit_total"], 780.0)


if __name__ == "__main__":
    unittest.main()
