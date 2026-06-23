"""Money OS -- the profit / payday / cash brain that sits ON TOP of the POS.

Read-first and provider-agnostic. It reuses the POS sales logs + the tamper-evident
time clock as the single source of truth, and computes:
  - daily / weekly P&L (revenue vs OT-correct labor vs overhead)        [section 1]
  - payroll-readiness gap incl. the "haven't run payroll in a while" catch-up [section 2]
  - fund-allocation envelopes (sales-tax swept first)                    [section 3]
  - cash-on-hand (manual now, Plaid later)                              [cross-cutting]

Nothing here rings sales, edits punches, or moves real money. It reads the existing
ledgers, computes the money picture, and (for envelopes/bills) stages actions that a
later UI gates behind owner approval. All writes go through POS_CORE's atomic,
fsync'd, _IO_LOCK-guarded helpers so they are crash-safe and concurrency-safe.

Paths track POS_CORE.DATA_DIR dynamically, so per-tenant data-dir context is honored.
"""
from datetime import datetime, date, timedelta

import POS_CORE
from POS_CORE import (
    read_csv, append_csv, ensure_csv, generate_id, _IO_LOCK,
    get_sales_for_date, get_punches_for_date, get_all_employees,
)

# ---------------------------------------------------------------------------
# Files (all under <DATA_DIR>/Money_OS, headers ensured on first touch)
# ---------------------------------------------------------------------------
OVERHEAD_HEADERS = ["Bill_ID", "Vendor", "Category", "Amount", "Frequency", "Due_Day",
                    "Autopay", "Account", "Active", "Notes"]
BILLS_HEADERS = ["Bill_ID", "Vendor", "Type", "Amount", "Due_Date", "Status", "Priority",
                 "Source", "Approved_By", "Approved_At", "Paid_At", "Notes"]
ENVELOPES_HEADERS = ["Envelope", "Balance", "Target", "Updated_At"]
ENV_LEDGER_HEADERS = ["Entry_ID", "Date", "Time", "Envelope", "Direction", "Amount",
                      "Source", "Ref", "Note"]
ALLOC_RULES_HEADERS = ["Rule_ID", "Trigger", "Envelope", "Percent", "Active"]
PNL_DAILY_HEADERS = ["Date", "Revenue", "COGS", "Gross_Profit", "Labor_Cost", "Employer_Tax",
                     "Overhead_Allocated", "Net_Profit", "Margin_Pct", "Flag"]
CASH_SNAP_HEADERS = ["Date", "Time", "Source", "Account", "Balance", "Note"]
PAYROLL_FUNDING_HEADERS = ["Period_ID", "As_Of", "Accrued_To_Date", "Employer_Tax_Est",
                           "Projected_To_Payday", "Cash_On_Hand", "Payroll_Envelope",
                           "Gap", "Alert_Level"]
SETTINGS_HEADERS = ["Key", "Value"]

DEFAULT_ENVELOPES = ["PAYROLL", "PAYROLL_TAX", "SALES_TAX", "BILLS", "RESERVE", "OWNER"]
# good-day set-aside as a % of NET profit (sales tax is swept separately, 100%)
DEFAULT_RULES = [("PAYROLL", 30.0), ("PAYROLL_TAX", 8.0), ("BILLS", 15.0), ("RESERVE", 10.0)]
DEFAULT_SETTINGS = {
    "EMPLOYER_TAX_BURDEN_PCT": "0.12",   # SS 6.2 + Medicare 1.45 + FUTA + CA UI/ETT (replaced by exact once known)
    "SALARY_WORKDAYS_PER_YEAR": "260",
    "SLOW_DAY_FRACTION": "0.6",          # < 60% of trailing avg net = SLOW
    "AUTOPILOT_MODE": "SUGGEST",         # OFF | SUGGEST | ARMED
}


def _mdir():
    d = POS_CORE.DATA_DIR / "Money_OS"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _p(name, headers):
    return ensure_csv(_mdir() / name, headers)


def get_settings():
    rows = read_csv(_p("Money_Settings.csv", SETTINGS_HEADERS))
    s = dict(DEFAULT_SETTINGS)
    for r in rows:
        if r.get("Key"):
            s[r["Key"]] = r.get("Value", "")
    return s


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ===========================================================================
# Section 1 -- LABOR COST (OT-correct) + DAILY / WEEKLY P&L
# ===========================================================================
def _worked_hours(punches):
    """Net worked hours for one employee on one day (clock pairs minus breaks)."""
    def dt(p):
        try:
            return datetime.strptime(f"{p.get('Date','')} {p.get('Time','')}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    pts = sorted([p for p in punches if dt(p)], key=dt)
    total = 0.0
    open_in = None
    for p in pts:
        t = (p.get("Punch_Type") or "").upper()
        d = dt(p)
        if t == "CLOCK_IN":
            open_in = d
        elif t == "CLOCK_OUT" and open_in:
            total += (d - open_in).total_seconds() / 3600.0
            open_in = None
        elif t in ("BREAK", "LUNCH") and open_in:
            total += (d - open_in).total_seconds() / 3600.0
            open_in = None
        elif t in ("END_BREAK", "END_LUNCH"):
            open_in = d
    return round(max(0.0, total), 2)


def ca_split(hours):
    """California DAILY overtime split: reg <=8, OT 8-12 (1.5x), DT >12 (2x)."""
    reg = min(hours, 8.0)
    ot = min(max(hours - 8.0, 0.0), 4.0)
    dt = max(hours - 12.0, 0.0)
    return round(reg, 2), round(ot, 2), round(dt, 2)


def _pay_config():
    cfg = {}
    for r in read_csv(POS_CORE.DATA_DIR / "Payroll" / "Employee_Pay_Config.csv"):
        if r.get("Employee_ID"):
            cfg[str(r["Employee_ID"])] = r
    return cfg


def compute_labor_cost_for_date(d):
    """True labor cost for a day: hourly OT-correct + salaried prorated, + employer tax."""
    s = get_settings()
    burden = _f(s["EMPLOYER_TAX_BURDEN_PCT"], 0.12)
    workdays = _f(s["SALARY_WORKDAYS_PER_YEAR"], 260) or 260
    cfg = _pay_config()
    punches = get_punches_for_date(d)
    by_emp = {}
    for p in punches:
        by_emp.setdefault(str(p.get("Employee_ID", "")), []).append(p)

    wages = 0.0
    detail = []
    for emp_id, ep in by_emp.items():
        if not emp_id:
            continue
        c = cfg.get(emp_id, {})
        worked = _worked_hours(ep)
        if (c.get("Pay_Type") or "").upper() == "SALARY":
            day_cost = _f(c.get("Salary_Amount")) / workdays  # flat daily cost on a worked day
            wages += day_cost
            detail.append({"emp_id": emp_id, "type": "SALARY", "hours": worked, "cost": round(day_cost, 2)})
        else:
            rate = _f(c.get("Hourly_Rate"))
            reg, ot, dt = ca_split(worked)
            cost = reg * rate + ot * rate * 1.5 + dt * rate * 2.0
            wages += cost
            detail.append({"emp_id": emp_id, "type": "HOURLY", "hours": worked,
                           "reg": reg, "ot": ot, "dt": dt, "rate": rate, "cost": round(cost, 2)})
    employer_tax = round(wages * burden, 2)
    return {"wages": round(wages, 2), "employer_tax": employer_tax,
            "total": round(wages + employer_tax, 2), "detail": detail}


def _overhead_daily_share():
    per = {"DAILY": 1.0, "WEEKLY": 7.0, "MONTHLY": 30.44, "QUARTERLY": 91.31, "ANNUAL": 365.0}
    total = 0.0
    for r in read_csv(_p("Overhead.csv", OVERHEAD_HEADERS)):
        if (r.get("Active", "Y") or "Y").upper() == "N":
            continue
        total += _f(r.get("Amount")) / per.get((r.get("Frequency") or "MONTHLY").upper(), 30.44)
    return round(total, 2)


def _trailing_avg_net(d, days=28):
    rows = read_csv(_p("PnL_Daily.csv", PNL_DAILY_HEADERS))
    cutoff = (d - timedelta(days=days)).strftime("%Y-%m-%d")
    dstr = d.strftime("%Y-%m-%d")
    nets = [_f(r.get("Net_Profit")) for r in rows if cutoff <= r.get("Date", "") < dstr]
    return round(sum(nets) / len(nets), 2) if nets else None


def compute_daily_pnl(d=None, persist=False):
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    sales = get_sales_for_date(d) or []
    revenue = round(sum(_f(r.get("Line_Total")) for r in sales), 2)
    cogs = round(sum(_f(r.get("COGS_Line")) for r in sales), 2)
    gross = round(revenue - cogs, 2)
    labor = compute_labor_cost_for_date(d)
    overhead = _overhead_daily_share()
    net = round(gross - labor["total"] - overhead, 2)
    margin = round((net / revenue) * 100, 1) if revenue else 0.0

    avg = _trailing_avg_net(d)
    slow_frac = _f(get_settings()["SLOW_DAY_FRACTION"], 0.6)
    if net < 0:
        flag = "LOSS"
    elif avg is not None and net < avg * slow_frac:
        flag = "SLOW"
    else:
        flag = "PROFITABLE"

    out = {"date": d.strftime("%Y-%m-%d"), "revenue": revenue, "cogs": cogs,
           "gross_profit": gross, "labor_cost": labor["wages"], "employer_tax": labor["employer_tax"],
           "overhead_allocated": overhead, "net_profit": net, "margin_pct": margin,
           "flag": flag, "sales_tax_collected": round(sum(_f(r.get("Tax_Amount")) for r in sales), 2)}
    if persist:
        _upsert_pnl(out)
    return out


def _upsert_pnl(o):
    path = _p("PnL_Daily.csv", PNL_DAILY_HEADERS)
    with _IO_LOCK:
        rows = [r for r in read_csv(path) if r.get("Date") != o["date"]]
        rows.append({"Date": o["date"], "Revenue": o["revenue"], "COGS": o["cogs"],
                     "Gross_Profit": o["gross_profit"], "Labor_Cost": o["labor_cost"],
                     "Employer_Tax": o["employer_tax"], "Overhead_Allocated": o["overhead_allocated"],
                     "Net_Profit": o["net_profit"], "Margin_Pct": o["margin_pct"], "Flag": o["flag"]})
        rows.sort(key=lambda r: r.get("Date", ""))
        POS_CORE.write_csv(path, PNL_DAILY_HEADERS, rows)


def compute_weekly_pnl(week_start):
    if isinstance(week_start, str):
        week_start = datetime.strptime(week_start, "%Y-%m-%d").date()
    days = [compute_daily_pnl(week_start + timedelta(days=i)) for i in range(7)]
    agg = {k: round(sum(x[k] for x in days), 2) for k in
           ("revenue", "cogs", "gross_profit", "labor_cost", "employer_tax", "overhead_allocated", "net_profit")}
    best = max(days, key=lambda x: x["net_profit"])
    worst = min(days, key=lambda x: x["net_profit"])
    agg.update({"week_start": week_start.strftime("%Y-%m-%d"), "days": days,
                "best_day": best["date"], "worst_day": worst["date"]})
    return agg


# ===========================================================================
# Section 3 -- ENVELOPES + DAILY ALLOCATION (sales tax swept first)
# ===========================================================================
def get_envelopes():
    path = _p("Envelopes.csv", ENVELOPES_HEADERS)
    rows = read_csv(path)
    have = {r.get("Envelope") for r in rows}
    missing = [e for e in DEFAULT_ENVELOPES if e not in have]
    if missing:
        with _IO_LOCK:
            for e in missing:
                append_csv(path, ENVELOPES_HEADERS,
                           {"Envelope": e, "Balance": "0.00", "Target": "0.00",
                            "Updated_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        rows = read_csv(path)
    return rows


def _adjust_envelope(name, direction, amount, source, ref, note=""):
    """direction IN/OUT. Appends a ledger row + updates the running balance, atomically."""
    amount = round(_f(amount), 2)
    if amount <= 0:
        return False
    now = datetime.now()
    with _IO_LOCK:
        get_envelopes()  # ensure defaults exist
        path = _p("Envelopes.csv", ENVELOPES_HEADERS)
        rows = read_csv(path)
        for r in rows:
            if r.get("Envelope") == name:
                bal = _f(r.get("Balance")) + (amount if direction == "IN" else -amount)
                r["Balance"] = f"{bal:.2f}"
                r["Updated_At"] = now.strftime("%Y-%m-%d %H:%M:%S")
                break
        else:
            rows.append({"Envelope": name, "Balance": f"{amount if direction=='IN' else -amount:.2f}",
                         "Target": "0.00", "Updated_At": now.strftime("%Y-%m-%d %H:%M:%S")})
        POS_CORE.write_csv(path, ENVELOPES_HEADERS, rows)
        append_csv(_p("Envelope_Ledger.csv", ENV_LEDGER_HEADERS), ENV_LEDGER_HEADERS,
                   {"Entry_ID": generate_id("ENV"), "Date": now.strftime("%Y-%m-%d"),
                    "Time": now.strftime("%H:%M:%S"), "Envelope": name, "Direction": direction,
                    "Amount": f"{amount:.2f}", "Source": source, "Ref": ref, "Note": note})
    return True


def _already_allocated(ref):
    return any(r.get("Ref") == ref for r in read_csv(_p("Envelope_Ledger.csv", ENV_LEDGER_HEADERS)))


def get_allocation_rules():
    rows = read_csv(_p("Allocation_Rules.csv", ALLOC_RULES_HEADERS))
    active = [(r.get("Envelope"), _f(r.get("Percent"))) for r in rows
              if (r.get("Active", "Y") or "Y").upper() == "Y" and r.get("Envelope")]
    return active or DEFAULT_RULES


def allocate_for_date(d=None):
    """Idempotent per day. Sweeps collected sales tax (always), then sets aside a %
    of NET profit on a profitable day per the allocation rules."""
    if d is None:
        d = date.today()
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    dstr = d.strftime("%Y-%m-%d")
    base_ref = f"alloc:{dstr}"
    if _already_allocated(base_ref + ":salestax"):
        return {"date": dstr, "skipped": True, "reason": "already allocated"}

    pnl = compute_daily_pnl(d)
    moves = []
    # 1) sales tax is never the store's money -> always sweep it
    if pnl["sales_tax_collected"] > 0:
        _adjust_envelope("SALES_TAX", "IN", pnl["sales_tax_collected"], "daily_allocation",
                         base_ref + ":salestax", "collected sales tax")
        moves.append(("SALES_TAX", pnl["sales_tax_collected"]))
    else:
        # still stamp the ref so the day is marked allocated
        _adjust_envelope("SALES_TAX", "IN", 0.01, "daily_allocation", base_ref + ":salestax", "stamp")
        _adjust_envelope("SALES_TAX", "OUT", 0.01, "daily_allocation", base_ref + ":stampback", "stamp")
    # 2) good-day set-asides from NET profit
    if pnl["net_profit"] > 0:
        for env, pct in get_allocation_rules():
            amt = round(pnl["net_profit"] * pct / 100.0, 2)
            if amt > 0:
                _adjust_envelope(env, "IN", amt, "daily_allocation", f"{base_ref}:{env}",
                                 f"{pct}% of net {pnl['net_profit']}")
                moves.append((env, amt))
    return {"date": dstr, "net_profit": pnl["net_profit"], "flag": pnl["flag"], "moves": moves}


def move_envelope(src, dst, amount, by=""):
    amount = round(_f(amount), 2)
    if amount <= 0:
        return False, "amount must be > 0"
    ref = generate_id("MOV")
    _adjust_envelope(src, "OUT", amount, f"manual_move:{by}", ref, f"-> {dst}")
    _adjust_envelope(dst, "IN", amount, f"manual_move:{by}", ref, f"<- {src}")
    return True, f"moved {amount} {src} -> {dst}"


# ===========================================================================
# Cross-cutting -- CASH ON HAND (manual now, Plaid later)
# ===========================================================================
def set_cash_manual(amount, by="", account="operating"):
    now = datetime.now()
    append_csv(_p("Cash_Snapshots.csv", CASH_SNAP_HEADERS), CASH_SNAP_HEADERS,
               {"Date": now.strftime("%Y-%m-%d"), "Time": now.strftime("%H:%M:%S"),
                "Source": "MANUAL", "Account": account, "Balance": f"{_f(amount):.2f}",
                "Note": f"entered by {by}"})
    return True


def get_cash_on_hand():
    rows = read_csv(_p("Cash_Snapshots.csv", CASH_SNAP_HEADERS))
    if not rows:
        return {"amount": 0.0, "source": "NONE", "as_of": None, "stale": True}
    rows.sort(key=lambda r: f"{r.get('Date','')} {r.get('Time','')}")
    last = rows[-1]
    as_of = f"{last.get('Date','')} {last.get('Time','')}".strip()
    stale = True
    try:
        stale = (datetime.now() - datetime.strptime(as_of, "%Y-%m-%d %H:%M:%S")) > timedelta(hours=24)
    except ValueError:
        pass
    return {"amount": _f(last.get("Balance")), "source": last.get("Source", "MANUAL"),
            "as_of": as_of, "stale": stale}


# ===========================================================================
# Section 2 -- PAYROLL READINESS (incl. the "haven't run payroll in a while" catch-up)
# ===========================================================================
def _gross_for_range(start_d, end_d):
    """Sum OT-correct wages across worked days in [start, end] (today-capped)."""
    total = 0.0
    cur = start_d
    today = date.today()
    while cur <= end_d and cur <= today:
        total += compute_labor_cost_for_date(cur)["wages"]
        cur += timedelta(days=1)
    return round(total, 2)


def _pay_periods():
    return read_csv(POS_CORE.DATA_DIR / "Payroll" / "Pay_Periods.csv")


def _period_has_run(period_id):
    for r in read_csv(POS_CORE.DATA_DIR / "Payroll" / f"{date.today().year}_Payroll_Runs.csv"):
        if str(r.get("Period_ID", "")) == str(period_id):
            return True
    return False


def _avg_daily_labor(days=14):
    today = date.today()
    vals = []
    for i in range(1, days + 1):
        vals.append(compute_labor_cost_for_date(today - timedelta(days=i))["wages"])
    nonzero = [v for v in vals if v > 0]
    return round(sum(nonzero) / len(nonzero), 2) if nonzero else 0.0


def payroll_readiness(persist=False):
    s = get_settings()
    burden = _f(s["EMPLOYER_TAX_BURDEN_PCT"], 0.12)
    periods = _pay_periods()
    today = date.today()

    # current open period
    open_periods = [p for p in periods if (p.get("Status", "") or "").upper() == "OPEN"]
    cur = None
    for p in open_periods:
        try:
            if datetime.strptime(p["Start_Date"], "%Y-%m-%d").date() <= today <= datetime.strptime(p["End_Date"], "%Y-%m-%d").date():
                cur = p
                break
        except (ValueError, KeyError):
            continue

    accrued = 0.0
    pay_date = None
    period_id = cur.get("Period_ID", "") if cur else ""
    if cur:
        try:
            accrued = _gross_for_range(datetime.strptime(cur["Start_Date"], "%Y-%m-%d").date(), today)
            pay_date = cur.get("Pay_Date", "")
        except (ValueError, KeyError):
            pass

    # CATCH-UP: closed-but-never-run open periods (the "haven't paid in a while" case)
    catch_up = 0.0
    catch_up_periods = []
    for p in periods:
        try:
            end = datetime.strptime(p["End_Date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        if end <= today and (p.get("Status", "") or "").upper() != "PROCESSED" and not _period_has_run(p.get("Period_ID", "")):
            g = _gross_for_range(datetime.strptime(p["Start_Date"], "%Y-%m-%d").date(), end)
            if g > 0 and p.get("Period_ID") != period_id:
                catch_up += g
                catch_up_periods.append({"period_id": p.get("Period_ID"), "end": p.get("End_Date"), "gross": g})

    # projected to next payday
    projected = accrued
    if cur and pay_date:
        try:
            pd = datetime.strptime(pay_date, "%Y-%m-%d").date()
            remaining = max((pd - today).days, 0)
            projected = round(accrued + _avg_daily_labor() * remaining, 2)
        except ValueError:
            pass

    owed = round(accrued + catch_up, 2)
    employer_tax = round((owed + (projected - accrued)) * burden, 2)
    total_need = round(projected + catch_up + employer_tax, 2)

    cash = get_cash_on_hand()
    envs = {e["Envelope"]: _f(e["Balance"]) for e in get_envelopes()}
    payroll_env = round(envs.get("PAYROLL", 0.0) + envs.get("PAYROLL_TAX", 0.0), 2)
    covered_by = max(cash["amount"], payroll_env)
    gap = round(max(total_need - covered_by, 0.0), 2)

    if catch_up > 0:
        level = "BLACK"
    elif gap > 0:
        level = "RED"
    elif cash["amount"] >= total_need > payroll_env:
        level = "AMBER"
    else:
        level = "GREEN"

    out = {"period_id": period_id, "as_of": today.strftime("%Y-%m-%d"),
           "accrued_to_date": round(accrued, 2), "catch_up": round(catch_up, 2),
           "catch_up_periods": catch_up_periods, "projected_to_payday": projected,
           "employer_tax_est": employer_tax, "total_need": total_need,
           "pay_date": pay_date, "cash_on_hand": cash["amount"], "cash_stale": cash["stale"],
           "payroll_envelope": payroll_env, "gap": gap, "alert_level": level}
    if persist:
        append_csv(_p("Payroll_Funding.csv", PAYROLL_FUNDING_HEADERS), PAYROLL_FUNDING_HEADERS,
                   {"Period_ID": period_id, "As_Of": out["as_of"], "Accrued_To_Date": out["accrued_to_date"],
                    "Employer_Tax_Est": employer_tax, "Projected_To_Payday": projected,
                    "Cash_On_Hand": cash["amount"], "Payroll_Envelope": payroll_env,
                    "Gap": gap, "Alert_Level": level})
    return out
