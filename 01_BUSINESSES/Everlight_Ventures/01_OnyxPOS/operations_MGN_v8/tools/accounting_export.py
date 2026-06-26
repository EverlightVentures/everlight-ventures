"""Accounting / bookkeeping export for the nursery's accountant (QuickBooks etc.).

No API keys -- it reads the POS sales + transaction logs and produces two CSVs:
  - daily_summary_rows: one row per day (gross sales, sales tax, COGS, cash/card).
  - journal_entry_rows: double-entry lines an accountant imports straight to
    QuickBooks (Undeposited Funds / Sales Income / Sales Tax Payable / COGS).

Uses the per-line tax + COGS the POS now records, so the numbers tie out to the till.
"""
from datetime import date, timedelta


def _f(row, key):
    try:
        return float(row.get(key) or 0)
    except Exception:
        return 0.0


def _date_range(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def daily_summary_rows(start, end):
    import POS_CORE as C
    out = []
    for d in _date_range(start, end):
        sales = C.get_sales_for_date(d) or []
        txns = C.get_transactions_for_date(d) or []
        gross = sum(_f(s, "Line_Total") for s in sales)
        tax = sum(_f(s, "Tax_Amount") for s in sales)
        cogs = sum(_f(s, "COGS_Line") for s in sales)
        cash = sum(_f(t, "Grand_Total") for t in txns
                   if (t.get("Payment_Method") or "").upper() == "CASH")
        card = sum(_f(t, "Grand_Total") for t in txns
                   if (t.get("Payment_Method") or "").upper() == "CARD")
        jim = sum(_f(t, "Grand_Total") for t in txns
                  if (t.get("Payment_Method") or "").upper() == "JIM")
        out.append({
            "Date": d.isoformat(), "Transactions": len(txns),
            "Gross_Sales": round(gross, 2), "Sales_Tax": round(tax, 2),
            "COGS": round(cogs, 2), "Gross_Profit": round(gross - cogs, 2),
            "Cash": round(cash, 2), "Card": round(card, 2), "JIM": round(jim, 2),
        })
    return out


def journal_entry_rows(start, end):
    """Double-entry journal lines (QuickBooks-importable). For each day with sales:
    Undeposited Funds (debit total) = Sales Income (credit) + Sales Tax Payable
    (credit); plus COGS (debit) / Inventory Asset (credit)."""
    rows = []
    for s in daily_summary_rows(start, end):
        if s["Transactions"] == 0:
            continue
        d = s["Date"]
        total = round(s["Gross_Sales"] + s["Sales_Tax"], 2)
        rows.append({"Date": d, "Account": "Undeposited Funds",
                     "Debit": f"{total:.2f}", "Credit": "", "Memo": "POS daily sales"})
        rows.append({"Date": d, "Account": "Sales Income",
                     "Debit": "", "Credit": f"{s['Gross_Sales']:.2f}", "Memo": "Gross sales"})
        if s["Sales_Tax"]:
            rows.append({"Date": d, "Account": "Sales Tax Payable",
                         "Debit": "", "Credit": f"{s['Sales_Tax']:.2f}",
                         "Memo": "Sales tax collected"})
        if s["COGS"]:
            rows.append({"Date": d, "Account": "Cost of Goods Sold",
                         "Debit": f"{s['COGS']:.2f}", "Credit": "", "Memo": "COGS"})
            rows.append({"Date": d, "Account": "Inventory Asset",
                         "Debit": "", "Credit": f"{s['COGS']:.2f}", "Memo": "COGS"})
    return rows
