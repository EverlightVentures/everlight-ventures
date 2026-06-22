"""
Mountain Gardens POS - Core Functions for Flask App
====================================================
v7.2 - Fixed version with AI/n8n Integration Support

Extracted from the main POS system for web use.
Used by: MGN_APP.py (Flask), CLI, Slack, n8n
"""
import os
import smtplib
import csv
import uuid
import hashlib
import json
import tempfile
import threading

from email.message import EmailMessage
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple, Any
from collections import defaultdict
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# ------------------------------------------------------------------------------
# Concurrency guard for CSV writes.
#
# Flask runs threaded by default, so two simultaneous sales can otherwise
# read-modify-rewrite the same file (e.g. Lots.csv) and lost-update inventory.
# Every full-file rewrite (write_csv), durable append (append_csv), the
# inventory read-modify-write (consume_from_lots), and the tamper-evident audit
# journal serialize on this single re-entrant lock. RLock (not Lock) so a
# function that already holds it can safely call write_csv/append_csv which
# re-acquire it.
# ------------------------------------------------------------------------------
_IO_LOCK = threading.RLock()






# ==============================================================================
#                              CONFIG
# ==============================================================================

BUSINESS_NAME = "Mountain Gardens Nursery & Pet"
VERSION = "7.2"  # Fixed version
TAX_RATE = 0.0825

SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR  # Alias for compatibility
DATA_DIR = Path(os.environ.get("MGN_DATA_DIR", SCRIPT_DIR)).resolve()

CUSTOMERS_DIR = DATA_DIR / "Customers"
CUSTOMER_RECEIPTS_PATH = CUSTOMERS_DIR / "customer_receipts.csv"

CUSTOMER_RECEIPTS_HEADERS = [
    "Timestamp", "First_Name", "Last_Name", "Email",
    "Transaction_ID", "Date", "Time", "Payment_Method",
    "Subtotal", "Tax", "Total", "Change_Due",
    "Items_Summary", "Items_JSON"
]


# Directory structure
EMPLOYEE_DIR = DATA_DIR / "Employees"
INVENTORY_DIR = DATA_DIR / "Inventory"
PRICING_DIR = DATA_DIR / "Pricing"
SALES_DIR = DATA_DIR / "Sales_Logs"
TRANSACTION_DIR = DATA_DIR / "Transaction_Logs"
TIMECLOCK_DIR = DATA_DIR / "Time_Clock"
TIMEOFF_DIR = DATA_DIR / "Time_Off_Requests"
NOTIFICATIONS_DIR = DATA_DIR / "Notifications"
AUDIT_DIR = DATA_DIR / "Audit"
RECEIPTS_DIR = DATA_DIR / "Receipts"
DAILY_REPORTS_DIR = DATA_DIR / "Daily_Reports"
TASKS_DIR = DATA_DIR / "Tasks"
PAYROLL_DIR = DATA_DIR / "Payroll"
# Task file paths
TASKS_MASTER_PATH = TASKS_DIR / "Tasks_Master.csv"
TASK_ASSIGNMENTS_PATH = TASKS_DIR / "Task_Assignments.csv"
TASK_EVENTS_PATH = TASKS_DIR / "Task_Events.csv"

def set_data_dir(new_base: Path) -> None:
    """Switch data root for multi-tenant mode."""
    global DATA_DIR
    global CUSTOMERS_DIR, CUSTOMER_RECEIPTS_PATH
    global EMPLOYEE_DIR, INVENTORY_DIR, PRICING_DIR, SALES_DIR, TRANSACTION_DIR
    global TIMECLOCK_DIR, TIMEOFF_DIR, NOTIFICATIONS_DIR, AUDIT_DIR
    global RECEIPTS_DIR, DAILY_REPORTS_DIR, TASKS_DIR, PAYROLL_DIR
    global TASKS_MASTER_PATH, TASK_ASSIGNMENTS_PATH, TASK_EVENTS_PATH

    DATA_DIR = Path(new_base).resolve()

    CUSTOMERS_DIR = DATA_DIR / "Customers"
    CUSTOMER_RECEIPTS_PATH = CUSTOMERS_DIR / "customer_receipts.csv"

    EMPLOYEE_DIR = DATA_DIR / "Employees"
    INVENTORY_DIR = DATA_DIR / "Inventory"
    PRICING_DIR = DATA_DIR / "Pricing"
    SALES_DIR = DATA_DIR / "Sales_Logs"
    TRANSACTION_DIR = DATA_DIR / "Transaction_Logs"
    TIMECLOCK_DIR = DATA_DIR / "Time_Clock"
    TIMEOFF_DIR = DATA_DIR / "Time_Off_Requests"
    NOTIFICATIONS_DIR = DATA_DIR / "Notifications"
    AUDIT_DIR = DATA_DIR / "Audit"
    RECEIPTS_DIR = DATA_DIR / "Receipts"
    DAILY_REPORTS_DIR = DATA_DIR / "Daily_Reports"
    TASKS_DIR = DATA_DIR / "Tasks"
    PAYROLL_DIR = DATA_DIR / "Payroll"

    TASKS_MASTER_PATH = TASKS_DIR / "Tasks_Master.csv"
    TASK_ASSIGNMENTS_PATH = TASKS_DIR / "Task_Assignments.csv"
    TASK_EVENTS_PATH = TASKS_DIR / "Task_Events.csv"

# ==============================================================================
#                              HEADERS
# ==============================================================================

EMPLOYEE_HEADERS = ["Employee_ID", "Employee_Name", "Role", "PIN", "Status",
                    "Hire_Date", "Phone", "Email", "Emergency_Contact", "Last_Updated", "Notes"]
AUDIT_HEADERS = ["Audit_ID", "Timestamp", "Actor_ID", "Actor_Name", "Action",
                 "Target_Type", "Target_ID", "Target_Name", "Old_Value", "New_Value", "Notes"]
NOTIFICATION_HEADERS = ["Notification_ID", "Employee_ID", "Employee_Name", "Date_Created",
                        "Message", "Type", "Read", "Read_Date"]



ITEM_HEADERS = ["SKU", "Item_Name", "Category", "Subcategory", "Product_Name",
                "Default_Unit", "Default_Price", "Taxable", "Reorder_Point",
                "Date_Added", "Last_Updated", "Status", "Notes", "Size", "Item_Description", "Wholesale_Cost", "Retail_Markup", "Retail_Price", "Unit_Cost", "Unit_Price",
  "Last_Invoice_No", "Last_Vendor", "Last_Received_Date",
                "Supplier_Barcode", "QR_Code", "QR_Image_Path",]  # aligned to the on-disk 26-col Items.csv so rewrites/appends never drop trailing columns



LOT_HEADERS = ["Lot_ID", "SKU", "Received_Date", "Supplier", "Invoice_Ref",
               "Qty_Received", "Unit_Cost", "Qty_Remaining", "Expiry_Date", "Notes"]
LEDGER_HEADERS = ["Entry_ID", "Timestamp", "SKU", "Lot_ID", "Delta_Qty",
                  "Reason", "Ref_Transaction_ID", "Employee_ID", "Notes"]
PRICING_RULE_HEADERS = ["Rule_ID", "Scope", "Target", "Method", "Value",
                        "Priority", "Active", "Created_Date", "Notes"]
SALES_HEADERS = ["Date", "Time", "Transaction_ID", "Employee_ID", "Employee_Name",
                 "Category", "Subcategory", "Product_Name", "Item_Name", "SKU",
                 "Quantity", "Size", "Item_Description", "Unit_Price", "Unit_Cost", "COGS_Line","Gross_Margin","Qty_Remaining_Before", "Qty_Remaining_After",
                 "Subtotal", "Tax_Rate", "Tax_Amount", "Line_Total",
                 "Payment_Method", "Amount_Received", "Change_Due", "Notes"]
TRANSACTION_HEADERS = ["Transaction_ID", "Date", "Time", "Employee_ID", "Employee_Name",
                       "Item_Count", "Subtotal", "Tax", "Card_Fee", "Grand_Total",
                       "Payment_Method", "Amount_Received", "Change_Due", "Receipt_Number", "Notes"]
TIMECLOCK_HEADERS = ["Punch_ID", "Date", "Time", "Employee_ID", "Employee_Name",
                     "Punch_Type", "Hours_Worked_Today", "Overtime_Hours", "Notes"]
TIMEOFF_HEADERS = ["Request_ID", "Employee_ID", "Employee_Name", "Request_Date",
                   "Start_Date", "End_Date", "Days_Requested", "Reason",
                   "Status", "Manager_Name", "Approval_Date", "Manager_Notes"]

# Task Headers
TASKS_MASTER_HEADERS = [
    "Task_ID", "Project_ID", "Title", "Description",
    "Category", "Priority", "Estimated_Minutes",
    "Created_By", "Created_At", "Active_Flag"
]
TASK_ASSIGNMENTS_HEADERS = [
    "Assignment_ID", "Task_ID", "Employee_ID",
    "Assigned_Date", "Due_Date", "Status",
    "Acknowledged_At", "Started_At", "Completed_At",
    "Skipped_At", "Skip_Reason",
    "Assigned_By", "Notes_From_Employee", "Quality_Score"
]
TASK_EVENTS_HEADERS = [
    "Event_ID", "Assignment_ID", "Timestamp",
    "Employee_ID", "Event_Type", "Event_Data"
]

# Payroll Headers
EMPLOYEE_PAY_HEADERS = [
    "Employee_ID", "Pay_Type", "Hourly_Rate", "Salary_Amount", "Pay_Frequency",
    "Federal_Filing_Status", "State_Filing_Status", "Federal_Allowances", "State_Allowances",
    "Additional_Withholding", "Direct_Deposit", "Bank_Account", "Bank_Routing",
    "Effective_Date", "Last_Updated", "Notes"
]
PAY_PERIOD_HEADERS = [
    "Period_ID", "Start_Date", "End_Date", "Pay_Date", "Status",
    "Created_By", "Created_At", "Processed_By", "Processed_At", "Notes"
]
PAYROLL_RUN_HEADERS = [
    "Payroll_ID", "Period_ID", "Employee_ID", "Employee_Name",
    "Regular_Hours", "Overtime_Hours", "Holiday_Hours", "PTO_Hours", "Sick_Hours",
    "Gross_Pay", "Federal_Tax", "State_Tax", "Social_Security", "Medicare",
    "Other_Deductions", "Net_Pay", "Pay_Method", "Check_Number",
    "Status", "Created_At", "Approved_By", "Approved_At", "Notes"
]
TIMECLOCK_EDIT_HEADERS = [
    "Edit_ID", "Punch_ID", "Edit_Date", "Editor_ID", "Editor_Name",
    "Original_Date", "Original_Time", "Original_Type",
    "New_Date", "New_Time", "New_Type",
    "Reason", "Approved_By", "Approved_At"
]

# Categories
MAIN_CATEGORIES = {"a": "Animal", "p": "Product", "l": "Plant"}
ANIMAL_SUBCATEGORIES = {"r": "Rat", "m": "Mouse", "c": "Cricket", "g": "Guinea Pig",
                        "h": "Hamster", "b": "Bird", "f": "Fish", "p": "Reptile",
                        "s": "Snake", "t": "Tarantula/Spider", "o": "Other Animal"}
PRODUCT_SUBCATEGORIES = {"s": "Soil & Amendments", "f": "Fertilizer", "p": "Pots & Containers",
                         "t": "Tools & Equipment", "d": "Decor & Garden Art", "c": "Chemicals/Pest Control",
                         "w": "Watering/Irrigation", "e": "Pet Food/Supplies", "g": "Gift & Seasonal",
                         "h": "Hardware & Misc", "o": "Other Product"}
PLANT_SUBCATEGORIES = {"t": "Tree", "s": "Shrub", "r": "Rose", "p": "Perennial",
                       "a": "Annual", "h": "Houseplant", "c": "Cactus/Succulent",
                       "v": "Vine & Climber", "g": "Groundcover", "e": "Edible/Vegetable",
                       "n": "Native Plant", "o": "Other Plant"}
ROLES = {"Cashier": {}, "Manager": {}, "Owner": {}, "Admin": {}}

# ==============================================================================
#                              DATA LAYER
# ==============================================================================

def ensure_csv(filepath: Path, headers: List[str]) -> Path:
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    if not filepath.exists():
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(headers)
    return filepath

def read_csv(filepath: Path) -> List[Dict[str, str]]:
    filepath = Path(filepath)
    if not filepath.exists():
        return []

    try:
        # utf-8-sig strips BOM if present (fixes \ufeffSKU)
        with open(filepath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            def norm_key(k: str) -> str:
                return (k or "").replace("\ufeff", "").strip()

            rows: List[Dict[str, str]] = []
            for row in reader:
                clean = {norm_key(k): ("" if v is None else str(v)) for k, v in row.items()}
                rows.append(clean)

            return rows
    except Exception:
        return []





def append_csv(filepath: Path, headers: List[str], row: Dict) -> bool:
    """Append a single row, DURABLY.

    Durability: f.flush() + os.fsync() before close, so a power loss / crash
    immediately after a "sale complete" cannot silently drop the just-written
    row from the OS page cache. Serialized on _IO_LOCK so concurrent threads
    can't interleave partial rows into the same file. Returns bool (unchanged
    contract) -- callers that care about loss (record_sale) MUST check it.
    """
    filepath = Path(filepath)
    ensure_csv(filepath, headers)
    try:
        safe = {h: ("" if row.get(h) is None else str(row.get(h))) for h in headers}
        with _IO_LOCK:
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                writer.writerow(safe)
                f.flush()
                os.fsync(f.fileno())
        return True
    except Exception as e:
        # Optional: uncomment for debugging
        # print(f"[append_csv] FAILED {filepath}: {e}")
        return False


def ensure_customer_files():
    CUSTOMERS_DIR.mkdir(parents=True, exist_ok=True)
    ensure_csv(CUSTOMER_RECEIPTS_PATH, CUSTOMER_RECEIPTS_HEADERS)

def _iter_csv_files(root: Path, suffix: str):
    if not root.exists():
        return []
    files = list(root.rglob(f"*{suffix}.csv"))
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files

def find_transaction_anywhere(transaction_id: str, days_back: int = 60):
    """Search Transaction_Logs for the Transaction_ID. Returns (tx_row, tx_file_path) or (None, None)."""
    root = SCRIPT_DIR / "Transaction_Logs"
    files = _iter_csv_files(root, "TransactionLog")
    cutoff = datetime.now() - timedelta(days=days_back)

    for p in files:
        try:
            if datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
                continue
        except Exception:
            pass

        rows = read_csv(p)
        for r in rows:
            if (r.get("Transaction_ID") or "").strip() == transaction_id:
                return r, p
    return None, None

def find_sales_lines_for_transaction(transaction_id: str, tx_date: str | None = None):
    """Return sales line rows from Sales_Logs matching Transaction_ID."""
    root = SCRIPT_DIR / "Sales_Logs"
    files = _iter_csv_files(root, "SalesLog")

    # If we know the date, prefer files with that date in the filename
    if tx_date:
        preferred = [p for p in files if p.name.startswith(f"{tx_date}_")]
        others = [p for p in files if p not in preferred]
        files = preferred + others

    out = []
    for p in files:
        rows = read_csv(p)
        for r in rows:
            if (r.get("Transaction_ID") or "").strip() == transaction_id:
                out.append(r)
        if out and tx_date and p.name.startswith(f"{tx_date}_"):
            break
    return out

def build_receipt_payload(transaction_id: str):
    """Build a receipt payload from CSV logs."""
    tx, _ = find_transaction_anywhere(transaction_id)
    if not tx:
        return None

    tx_date = (tx.get("Date") or "").strip() or None
    lines = find_sales_lines_for_transaction(transaction_id, tx_date=tx_date)

    # Totals (support either header naming)
    subtotal = tx.get("Subtotal", "")
    tax = tx.get("Tax", "")
    total = tx.get("Grand_Total", tx.get("Total", ""))
    change_due = tx.get("Change_Due", "")

    items = []
    for r in lines:
        items.append({
            "sku": r.get("SKU", ""),
            "name": r.get("Item_Name", r.get("Product_Name", "")),
            "qty": r.get("Quantity", ""),
            "unit_price": r.get("Unit_Price", ""),
            "line_total": r.get("Line_Total", ""),
        })

    return {
        "transaction": tx,
        "items": items,
        "totals": {
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "change_due": change_due,
        }
    }

def log_customer_receipt(first_name: str, last_name: str, email: str, receipt_payload: dict):
    ensure_customer_files()

    tx = receipt_payload.get("transaction", {}) or {}
    items = receipt_payload.get("items", []) or []
    totals = receipt_payload.get("totals", {}) or {}

    summary = "; ".join([
        f'{i.get("qty","")}x {i.get("name","")}'.strip()
        for i in items
    ])[:5000]

    row = {
        "Timestamp": datetime.now().isoformat(timespec="seconds"),
        "First_Name": first_name.strip(),
        "Last_Name": last_name.strip(),
        "Email": email.strip(),
        "Transaction_ID": (tx.get("Transaction_ID") or ""),
        "Date": (tx.get("Date") or ""),
        "Time": (tx.get("Time") or ""),
        "Payment_Method": (tx.get("Payment_Method") or ""),
        "Subtotal": str(totals.get("subtotal","")),
        "Tax": str(totals.get("tax","")),
        "Total": str(totals.get("total","")),
        "Change_Due": str(totals.get("change_due","")),
        "Items_Summary": summary,
        "Items_JSON": json.dumps(items, ensure_ascii=False),
    }
    append_csv(CUSTOMER_RECEIPTS_PATH, CUSTOMER_RECEIPTS_HEADERS, row)
    return True

def write_csv(filepath: Path, headers: List[str], rows: List[Dict]) -> bool:
    """Rewrite the whole file ATOMICALLY + DURABLY.

    Writes to a temp file in the same directory, fsyncs it, then os.replace()
    (atomic on POSIX) onto the target. A crash mid-write therefore leaves the
    ORIGINAL file intact instead of a truncated/empty one -- critical for
    Inventory/Lots.csv, the source of truth for stock on hand. Serialized on
    _IO_LOCK so two concurrent sales can't lost-update inventory.
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _IO_LOCK:
            fd, tmp = tempfile.mkstemp(dir=str(filepath.parent), prefix=".tmp_", suffix=".csv")
            try:
                with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
                    writer.writeheader()
                    for row in rows:
                        safe = {h: ("" if row.get(h) is None else str(row.get(h))) for h in headers}
                        writer.writerow(safe)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, filepath)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        return True
    except Exception as e:
        # Optional: uncomment for debugging
        # print(f"[write_csv] FAILED {filepath}: {e}")
        return False

def update_csv_row(filepath: Path, headers: List[str], key: str, value: str, updates: Dict) -> bool:
    rows = read_csv(filepath)
    for row in rows:
        if row.get(key) == value:
            row.update(updates)
            return write_csv(filepath, headers, rows)
    return False
# ==============================================================================
#                              PATH HELPERS
# ==============================================================================

def to_int(x, default=0):
    """
    Convert values like "4", "4.0", 4.0, None safely into an int.
    """
    try:
        if x is None:
            return default
        s = str(x).strip()
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default

def get_dated_path(base_dir: Path, suffix: str, target_date: date = None) -> Path:
    if target_date is None:
        target_date = date.today()
    year = target_date.strftime("%Y")
    month = target_date.strftime("%m_%B")
    week = f"Week_{((target_date.day - 1) // 7) + 1}"
    filename = f"{target_date.strftime('%Y-%m-%d')}_{target_date.strftime('%A')}_{suffix}"
    return base_dir / year / month / week / filename


# ==============================================================================
#                            (reciepts)
# ==============================================================================
def _now_iso():
    return datetime.now().isoformat(timespec="seconds")

def _ensure_csv(path: Path, headers: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            w.writeheader()

def _append_csv_row(path: Path, headers: list[str], row: dict):
    _ensure_csv(path, headers)
    safe = {h: ("" if row.get(h) is None else str(row.get(h))) for h in headers}
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writerow(safe)

def get_receipt_delivery_log_path() -> Path:
    # keep it relative to the project folder you run from
    return Path("Receipts") / "Receipt_Delivery_Log.csv"

def log_receipt_delivery(
    trans_id: str,
    method: str,
    status: str,
    notes: str = "",
    emp_id: str = "",
    customer_id: str = "",
    customer_name: str = "",
    customer_email: str = "",
):
    """
    method: PRINT | EMAIL
    status: OK | PENDING | FAILED
    """
    headers = [
        "Trans_ID", "Method", "Customer_ID", "Customer_Name", "Customer_Email",
        "Sent_At", "Status", "Notes", "Employee_ID"
    ]
    row = {
        "Trans_ID": trans_id,
        "Method": (method or "").upper(),
        "Customer_ID": customer_id,
        "Customer_Name": customer_name,
        "Customer_Email": customer_email,
        "Sent_At": _now_iso(),
        "Status": (status or "").upper(),
        "Notes": notes,
        "Employee_ID": emp_id,
    }
    _append_csv_row(get_receipt_delivery_log_path(), headers, row)
    return row

def upsert_customer(name: str, email: str) -> str:
    """
    Creates/returns a Customer_ID based on email.
    Stores in Customers/Customers.csv
    """
    email = (email or "").strip().lower()
    name = (name or "").strip()

    customers_path = Path("Customers") / "Customers.csv"
    headers = ["Customer_ID", "Name", "Email", "Created_At"]

    _ensure_csv(customers_path, headers)

    rows = []
    with customers_path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
            if email and r.get("Email", "").strip().lower() == email:
                return r.get("Customer_ID", "").strip() or "CUST-1000"

    # make a new ID
    max_num = 1000
    for r in rows:
        cid = (r.get("Customer_ID") or "").strip()
        if cid.startswith("CUST-"):
            try:
                max_num = max(max_num, int(cid.split("-", 1)[1]))
            except Exception:
                pass
    new_id = f"CUST-{max_num + 1}"

    _append_csv_row(customers_path, headers, {
        "Customer_ID": new_id,
        "Name": name,
        "Email": email,
        "Created_At": _now_iso(),
    })
    return new_id

def get_receipt_bundle(trans_id: str) -> dict:
    """
    Minimal bundle so receipt.html can render without crashing.
    You can upgrade this later to pull exact line items from your sales logs.
    """
    # delivery history
    delivery = []
    log_path = get_receipt_delivery_log_path()
    if log_path.exists():
        with log_path.open("r", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r.get("Trans_ID") or "").strip() == trans_id:
                    delivery.append(r)

    # basic receipt object (safe defaults)
    receipt = {
        "trans_id": trans_id,
        "created_at": _now_iso(),
        "customer_name": "",
        "customer_email": "",
        "payment_method": "",
    }

    # NOTE: items/totals can be filled from your actual transaction CSV later
    items = []
    subtotal = 0.0
    tax = 0.0
    total = 0.0

    return {
        "receipt": receipt,
        "items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "delivery_history": delivery,
    }


def build_receipt_pdf_bytes(bundle: dict) -> bytes:
    """
    Builds a simple professional PDF receipt (fast, reliable).
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    receipt = bundle.get("receipt", {})
    items = bundle.get("items", [])
    subtotal = float(bundle.get("subtotal", 0.0) or 0.0)
    tax = float(bundle.get("tax", 0.0) or 0.0)
    total = float(bundle.get("total", 0.0) or 0.0)

    y = height - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Mountain Gardens Nursery")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Receipt: {receipt.get('trans_id','')}")
    y -= 14
    c.drawString(50, y, f"Date: {receipt.get('created_at','')}")
    y -= 14
    c.drawString(50, y, f"Cashier: {receipt.get('cashier_name','')}")
    y -= 20

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Items")
    y -= 14
    c.setFont("Helvetica", 10)

    if not items:
        c.drawString(50, y, "(No line items found)")
        y -= 14
    else:
        for it in items:
            qty = it.get("qty", it.get("Quantity", "1"))
            name = it.get("name", it.get("Item_Name", it.get("SKU", "")))
            line_total = it.get("line_total", it.get("Line_Total", ""))
            c.drawString(50, y, f"{qty} x {name}")
            c.drawRightString(width - 50, y, f"{line_total}")
            y -= 14
            if y < 120:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 10)

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - 50, y, f"Subtotal: ${subtotal:,.2f}")
    y -= 14
    c.drawRightString(width - 50, y, f"Tax: ${tax:,.2f}")
    y -= 14
    c.drawRightString(width - 50, y, f"Total: ${total:,.2f}")

    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Thanks for supporting Mountain Gardens 🌿")

    c.showPage()
    c.save()
    return buf.getvalue()


def send_receipt_email_smtp(to_email: str, customer_name: str, trans_id: str, pdf_bytes: bytes):
    """
    Requires SMTP env vars in .env:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
    """
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    pw = os.getenv("SMTP_PASS", "").strip()
    mail_from = os.getenv("SMTP_FROM", user).strip()

    if not host or not user or not pw:
        raise RuntimeError("SMTP not configured. Set SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS in .env")

    msg = EmailMessage()
    msg["Subject"] = f"Your Mountain Gardens receipt ({trans_id})"
    msg["From"] = mail_from
    msg["To"] = to_email

    greeting = customer_name or "there"
    msg.set_content(
        f"Hi {greeting},\n\nAttached is your receipt for transaction {trans_id}.\n\nThank you,\nMountain Gardens"
    )

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"receipt_{trans_id}.pdf",
    )

    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, pw)
        s.send_message(msg)





def get_employee_path(): return ensure_csv(EMPLOYEE_DIR / "Employee_Directory.csv", EMPLOYEE_HEADERS)
def get_audit_path(): return ensure_csv(AUDIT_DIR / "Employee_Audit.csv", AUDIT_HEADERS)
def get_notification_path(): return ensure_csv(NOTIFICATIONS_DIR / "Employee_Notifications.csv", NOTIFICATION_HEADERS)
def get_items_path(): return ensure_csv(INVENTORY_DIR / "Items.csv", ITEM_HEADERS)
def get_lots_path(): return ensure_csv(INVENTORY_DIR / "Lots.csv", LOT_HEADERS)
def get_ledger_path(): return ensure_csv(INVENTORY_DIR / "Ledger.csv", LEDGER_HEADERS)
def get_pricing_rules_path(): return ensure_csv(PRICING_DIR / "Pricing_Rules.csv", PRICING_RULE_HEADERS)
def get_sales_path(d=None): return ensure_csv(get_dated_path(SALES_DIR, "SalesLog.csv", d), SALES_HEADERS)
def get_transaction_path(d=None): return ensure_csv(get_dated_path(TRANSACTION_DIR, "TransactionLog.csv", d), TRANSACTION_HEADERS)

# Recovery log: a sale whose CSV write failed lands here so it is NEVER silently
# lost. record_sale() writes to this then returns failure (cashier re-rings).
FAILED_SALE_HEADERS = ["Transaction_ID", "Timestamp", "Employee_ID", "Total",
                       "Header_Written", "Lines_Written", "Payload_JSON"]
def get_failed_sales_path(): return ensure_csv(SALES_DIR / "_FAILED_SALES.csv", FAILED_SALE_HEADERS)
def get_timeclock_path(d=None): return ensure_csv(get_dated_path(TIMECLOCK_DIR, "TimeClockLog.csv", d), TIMECLOCK_HEADERS)
def get_timeoff_path(year=None): return ensure_csv(TIMEOFF_DIR / f"{year or date.today().year}_TimeOffRequests.csv", TIMEOFF_HEADERS)
def get_employee_pay_path(): return ensure_csv(PAYROLL_DIR / "Employee_Pay_Config.csv", EMPLOYEE_PAY_HEADERS)
def get_pay_periods_path(): return ensure_csv(PAYROLL_DIR / "Pay_Periods.csv", PAY_PERIOD_HEADERS)
def get_payroll_runs_path(year=None): return ensure_csv(PAYROLL_DIR / f"{year or date.today().year}_Payroll_Runs.csv", PAYROLL_RUN_HEADERS)
def get_timeclock_edits_path(): return ensure_csv(TIMECLOCK_DIR / "Time_Edits_Audit.csv", TIMECLOCK_EDIT_HEADERS)

def generate_id(prefix: str) -> str:
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"


# ==============================================================================
#                            Ledger_Entry(Sales)
# ==============================================================================

def ledger_entry(
    action: str,
    sku: str = "",
    item_name: str = "",
    qty_delta: float | int = 0,
    unit_cost: float | int = 0,
    unit_price: float | int = 0,
    employee_id: str = "",
    employee_name: str = "",
    notes: str = ""
) -> dict:
    """
    Append a single row to Inventory/Ledger.csv.

    This exists because the Sales/Inventory code expects a function called
    `ledger_entry(...)` to log inventory/sales-related movements.
    """

    # Ensure file path exists
    ledger_path = INVENTORY_DIR / "Ledger.csv"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    # Normalize numbers safely
    def _num(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    row = {
        "Timestamp": datetime.now().isoformat(timespec="seconds"),
        "Action": str(action or ""),
        "SKU": str(sku or ""),
        "Item_Name": str(item_name or ""),
        "Qty_Delta": _num(qty_delta),
        "Unit_Cost": _num(unit_cost),
        "Unit_Price": _num(unit_price),
        "Employee_ID": str(employee_id or ""),
        "Employee_Name": str(employee_name or ""),
        "Notes": str(notes or ""),
    }

    headers = list(row.keys())

    file_exists = ledger_path.exists()
    with ledger_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        if not file_exists or ledger_path.stat().st_size == 0:
            w.writeheader()
        w.writerow(row)

    return row
# ==============================================================================
#                              EMPLOYEES
# ==============================================================================

def get_all_employees(include_inactive=False):
    emps = read_csv(get_employee_path())
    return emps if include_inactive else [e for e in emps if e.get("Status", "Active") == "Active"]

def get_employee(emp_id):
    for e in read_csv(get_employee_path()):
        if e.get("Employee_ID") == emp_id:
            return e
    return None

def create_employee(name, role, pin, phone="", email=""):
    if not pin.isdigit() or len(pin) != 4:
        return False, "PIN must be 4 digits", ""
    if role not in ROLES:
        return False, f"Invalid role", ""

    emps = read_csv(get_employee_path())
    max_id = max([int(e.get("Employee_ID", 1000)) for e in emps], default=1000)
    emp_id = str(max_id + 1)

    row = {"Employee_ID": emp_id, "Employee_Name": name, "Role": role, "PIN": pin,
           "Status": "Active", "Hire_Date": date.today().strftime("%Y-%m-%d"),
           "Phone": phone, "Email": email, "Emergency_Contact": "",
           "Last_Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Notes": ""}

    if append_csv(get_employee_path(), EMPLOYEE_HEADERS, row):
        return True, f"Employee {name} created (ID: {emp_id})", emp_id
    return False, "Failed to create", ""

def authenticate(emp_id, pin):
    emp = get_employee(emp_id)
    if not emp:
        return False, "Employee not found", None
    if emp.get("Status") == "Inactive":
        return False, "Account deactivated", None
    if emp.get("PIN") != pin:
        return False, "Invalid PIN", None
    return True, "Login successful", emp

def reset_pin(target_id, new_pin, actor_id, actor_name):
    if not new_pin.isdigit() or len(new_pin) != 4:
        return False, "PIN must be 4 digits"
    target = get_employee(target_id)
    if not target:
        return False, "Employee not found"
    if update_csv_row(get_employee_path(), EMPLOYEE_HEADERS, "Employee_ID", target_id,
                     {"PIN": new_pin, "Last_Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}):
        log_audit(actor_id, actor_name, "PIN_RESET", "Employee", target_id, target.get("Employee_Name", ""))
        create_notification(target_id, target.get("Employee_Name", ""),
                          f"Your PIN was reset by {actor_name}. Please change it if you didn't request this.",
                          "SECURITY")
        return True, f"PIN reset for {target.get('Employee_Name')}"
    return False, "Failed to reset"

def deactivate_employee(target_id, actor_id, actor_name, reason=""):
    target = get_employee(target_id)
    if not target:
        return False, "Employee not found"
    if target.get("Status") == "Inactive":
        return False, "Already inactive"
    if update_csv_row(get_employee_path(), EMPLOYEE_HEADERS, "Employee_ID", target_id,
                     {"Status": "Inactive", "Last_Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}):
        log_audit(actor_id, actor_name, "DEACTIVATE", "Employee", target_id, target.get("Employee_Name", ""), "Active", "Inactive", reason)
        return True, f"{target.get('Employee_Name')} deactivated"
    return False, "Failed"

def reactivate_employee(target_id, actor_id, actor_name):
    target = get_employee(target_id)
    if not target:
        return False, "Employee not found"
    if target.get("Status") == "Active":
        return False, "Already active"
    if update_csv_row(get_employee_path(), EMPLOYEE_HEADERS, "Employee_ID", target_id,
                     {"Status": "Active", "Last_Updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}):
        log_audit(actor_id, actor_name, "REACTIVATE", "Employee", target_id, target.get("Employee_Name", ""))
        create_notification(target_id, target.get("Employee_Name", ""),
                          f"Your account was reactivated by {actor_name}. Welcome back!",
                          "INFO")
        return True, f"{target.get('Employee_Name')} reactivated"
    return False, "Failed"

# ==============================================================================
#                              AUDIT & NOTIFICATIONS
# ==============================================================================

def log_audit(actor_id, actor_name, action, target_type, target_id, target_name="", old="", new="", notes=""):
    row = {"Audit_ID": generate_id("AUD"), "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "Actor_ID": actor_id, "Actor_Name": actor_name, "Action": action,
           "Target_Type": target_type, "Target_ID": target_id, "Target_Name": target_name,
           "Old_Value": old, "New_Value": new, "Notes": notes}
    append_csv(get_audit_path(), AUDIT_HEADERS, row)
    return row["Audit_ID"]

def get_audit_log(limit=100):
    return read_csv(get_audit_path())[-limit:]

def create_notification(emp_id, emp_name, message, ntype="INFO"):
    row = {"Notification_ID": generate_id("NTF"), "Employee_ID": emp_id, "Employee_Name": emp_name,
           "Date_Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "Message": message, "Type": ntype, "Read": "N", "Read_Date": ""}
    append_csv(get_notification_path(), NOTIFICATION_HEADERS, row)
    return row["Notification_ID"]

def get_unread_notifications(emp_id):
    return [n for n in read_csv(get_notification_path())
            if n.get("Employee_ID") == emp_id and n.get("Read") != "Y"]

def get_all_notifications(emp_id, limit=50):
    notifs = [n for n in read_csv(get_notification_path()) if n.get("Employee_ID") == emp_id]
    notifs.sort(key=lambda x: x.get("Date_Created", ""), reverse=True)
    return notifs[:limit]

def mark_notification_read(notification_id):
    notifs = read_csv(get_notification_path())
    for n in notifs:
        if n.get("Notification_ID") == notification_id:
            n["Read"] = "Y"
            n["Read_Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            write_csv(get_notification_path(), NOTIFICATION_HEADERS, notifs)
            return True
    return False

def mark_all_notifications_read(emp_id):
    notifs = read_csv(get_notification_path())
    count = 0
    for n in notifs:
        if n.get("Employee_ID") == emp_id and n.get("Read") != "Y":
            n["Read"] = "Y"
            n["Read_Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            count += 1
    if count > 0:
        write_csv(get_notification_path(), NOTIFICATION_HEADERS, notifs)
    return count

# ==============================================================================
#                              INVENTORY
# ==============================================================================

def generate_sku(name, category, subcategory):
    prefix = {"Animal": "ANM", "Product": "PRD", "Plant": "PLT"}.get(category, "GEN")
    sub = subcategory[:3].upper() if subcategory else "GEN"
    h = hashlib.md5(name.lower().encode()).hexdigest()[:4].upper()
    ts = datetime.now().strftime("%m%d")
    sku = f"{prefix}-{sub}-{h}-{ts}"
    existing = {i.get("SKU", "") for i in read_csv(get_items_path())}
    if sku in existing:
        n = 1
        while f"{sku}-{n}" in existing:
            n += 1
        sku = f"{sku}-{n}"
    return sku

def get_item(sku):
    for i in read_csv(get_items_path()):
        if i.get("SKU") == sku:
            return i
    return None

def get_all_items(active_only=True):
    items = read_csv(get_items_path())
    return items if not active_only else [i for i in items if i.get("Status") != "Inactive"]

def search_items(query, category=None):
    q = (query or "").lower().strip()
    results = []

    for i in read_csv(get_items_path()):
        if i.get("Status") == "Inactive":
            continue
        if category and i.get("Category") != category:
            continue

        haystack = " ".join([
            (i.get("SKU") or ""),
            (i.get("Item_Name") or ""),
            (i.get("Product_Name") or ""),
            (i.get("Item_Description") or ""),
        ]).lower()

        if not q or q in haystack:
            results.append(i)

    return results



def create_item(sku, name, category, subcategory, product_name="", default_price=0, reorder_point=5, notes=""):
    if get_item(sku):
        return False, "SKU already exists"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {"SKU": sku, "Item_Name": name, "Category": category, "Subcategory": subcategory,
           "Product_Name": product_name or name, "Default_Unit": "each", "Default_Price": f"{default_price:.2f}",
           "Taxable": "Y", "Reorder_Point": str(reorder_point), "Date_Added": now,
           "Last_Updated": now, "Status": "Active", "Notes": notes}
    if append_csv(get_items_path(), ITEM_HEADERS, row):
        return True, f"Item created: {sku}"
    return False, "Failed to create item"


# ==============================================================================
#          QUICK-ADD (sell on the spot) + END-OF-DAY RECONCILIATION
# ==============================================================================
# A cashier can add an item mid-sale with just a name + price. It is persisted as
# a normal, immediately-sellable item with a "QA-" SKU so a manager can later map
# it to the real catalog product on the reconciliation matrix -- keeping sold
# items aligned with inventory even when the catalog is incomplete.

RECON_MAP_HEADERS = ["Map_ID", "QA_SKU", "QA_Name", "Canonical_SKU",
                     "Canonical_Name", "Mapped_By", "Mapped_At", "Reason"]
def get_recon_map_path(): return ensure_csv(INVENTORY_DIR / "Reconciliation_Map.csv", RECON_MAP_HEADERS)


def quick_add_item(name, price, category="Quick-Add", size="", emp_id="", emp_name=""):
    """Cashier 'add on the spot'. Returns (sku, row).

    Provisional item: 'QA-' SKU, fully sellable. Price is written into EVERY price
    column so search/sale read it regardless of which column they prefer. The
    QA- prefix is the durable marker for the reconciliation matrix.
    """
    name = (name or "").strip() or "Quick Item"
    try:
        price = round(float(price or 0), 2)
    except Exception:
        price = 0.0
    sku = "QA-" + datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:3].upper()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "SKU": sku, "Item_Name": name, "Category": category or "Quick-Add",
        "Subcategory": "", "Product_Name": name, "Default_Unit": "each",
        "Default_Price": f"{price:.2f}", "Taxable": "Y", "Reorder_Point": "0",
        "Date_Added": now, "Last_Updated": now, "Status": "Active",
        "Notes": f"QUICK-ADD by {emp_name or emp_id} -- needs reconciliation",
        "Size": size or "", "Item_Description": "",
        "Retail_Price": f"{price:.2f}", "Unit_Price": f"{price:.2f}",
    }
    append_csv(get_items_path(), ITEM_HEADERS, row)
    try:
        append_audit_event("quick_add_item", {"sku": sku, "name": name, "price": price, "emp_id": emp_id})
    except Exception:
        pass
    return sku, row


def get_unreconciled_quickadds():
    """All quick-add items not yet reconciled (the EOD matrix rows)."""
    return [i for i in read_csv(get_items_path())
            if str(i.get("SKU", "")).startswith("QA-") and i.get("Status", "") != "Inactive"]


def reconcile_quickadd(qa_sku, canonical_sku, mapped_by="", reason=""):
    """Map a provisional QA item to a real catalog product. Records the mapping,
    then deactivates the QA item so future sales use the canonical product."""
    qa = get_item(qa_sku)
    if not qa:
        return False, "Quick-add item not found"
    canon = get_item(canonical_sku)
    if not canon:
        return False, "Target catalog item not found"
    append_csv(get_recon_map_path(), RECON_MAP_HEADERS, {
        "Map_ID": generate_id("RMAP"), "QA_SKU": qa_sku, "QA_Name": qa.get("Item_Name", ""),
        "Canonical_SKU": canonical_sku, "Canonical_Name": canon.get("Item_Name", ""),
        "Mapped_By": mapped_by, "Mapped_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Reason": reason,
    })
    update_csv_row(get_items_path(), ITEM_HEADERS, "SKU", qa_sku,
                   {"Status": "Inactive", "Notes": f"Reconciled -> {canonical_sku} by {mapped_by}"})
    try:
        append_audit_event("reconcile_quickadd", {"qa_sku": qa_sku, "canonical_sku": canonical_sku, "by": mapped_by})
    except Exception:
        pass
    return True, f"Reconciled {qa_sku} -> {canonical_sku}"


def create_lot(sku, qty, cost, supplier="", invoice="", notes=""):
    lot_id = generate_id("LOT")
    row = {"Lot_ID": lot_id, "SKU": sku, "Received_Date": date.today().strftime("%Y-%m-%d"),
           "Supplier": supplier, "Invoice_Ref": invoice, "Qty_Received": str(qty),
           "Unit_Cost": f"{cost:.2f}", "Qty_Remaining": str(qty), "Expiry_Date": "", "Notes": notes}
    append_csv(get_lots_path(), LOT_HEADERS, row)
    ledger_row = {"Entry_ID": generate_id("LED"), "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  "SKU": sku, "Lot_ID": lot_id, "Delta_Qty": str(qty), "Reason": "Receive",
                  "Ref_Transaction_ID": "", "Employee_ID": "", "Notes": notes}
    append_csv(get_ledger_path(), LEDGER_HEADERS, ledger_row)
    return lot_id

def get_lots_for_sku(sku, available_only=True):
    lots = [l for l in read_csv(get_lots_path()) if l.get("SKU") == sku]
    if available_only:
        lots = [l for l in lots if to_int(l.get("Qty_Remaining", 0), default=0)]

    lots.sort(key=lambda x: x.get("Received_Date", ""))
    return lots

def get_stock_on_hand(sku):
   return sum(to_int(l.get("Qty_Remaining", 0)) for l in read_csv(get_lots_path()) if l.get("SKU") == sku)


def get_average_cost(sku):
    lots = get_lots_for_sku(sku)
    total_qty = sum(int(float(l.get("Qty_Remaining", 0) or 0)) for l in lots)
    total_cost = sum(
    int(float(l.get("Qty_Remaining", 0) or 0)) * float(l.get("Unit_Cost", 0) or 0)
    for l in lots
)



    return total_cost / total_qty if total_qty > 0 else 0

def fifo_deplete(sku, qty_needed, trans_id="", emp_id=""):
    lots = get_lots_for_sku(sku)
    total = sum(to_int(l.get("Qty_Remaining", 0), default=0)
 for l in lots)
    if total < qty_needed:
        return False, 0, "Insufficient stock"

    remaining = qty_needed
    cogs = 0
    all_lots = read_csv(get_lots_path())

    for lot in lots:
        if remaining <= 0:
            break
        lot_id = lot.get("Lot_ID")
        qty_in = to_int(l.get("Qty_Remaining", 0), default=0)


        cost = float(lot.get("Unit_Cost", 0))
        take = min(remaining, qty_in)

        for l in all_lots:
            if l.get("Lot_ID") == lot_id:
                l["Qty_Remaining"] = str(qty_in - take)
                break

        ledger = {"Entry_ID": generate_id("LED"), "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                  "SKU": sku, "Lot_ID": lot_id, "Delta_Qty": str(-take), "Reason": "Sale",
                  "Ref_Transaction_ID": trans_id, "Employee_ID": emp_id, "Notes": ""}
        append_csv(get_ledger_path(), LEDGER_HEADERS, ledger)

        cogs += take * cost
        remaining -= take

    write_csv(get_lots_path(), LOT_HEADERS, all_lots)
    return True, cogs, None

def consume_from_lots(sku, qty, trans_id, emp_id):
    lots = get_lots_for_sku(sku, available_only=True)
    remaining = qty
    consumed = []
    for lot in lots:
        if remaining <= 0:
            break
        available = float(lot.get("Qty_Remaining", 0))
        take = min(available, remaining)
        lot["Qty_Remaining"] = str(available - take)
        remaining -= take
        consumed.append({"lot_id": lot["Lot_ID"], "qty": take, "cost": float(lot.get("Unit_Cost", 0))})
        ledger_entry(sku, lot["Lot_ID"], -take, "SALE", trans_id, emp_id, "")
    # Lock the whole re-read -> subtract -> rewrite so two concurrent sales
    # can't both read the same on-hand and lost-update Lots.csv.
    with _IO_LOCK:
        all_lots = read_csv(get_lots_path())
        for lot in all_lots:
            for c in consumed:
                if lot.get("Lot_ID") == c["lot_id"]:
                    lot["Qty_Remaining"] = str(float(lot.get("Qty_Remaining", 0)) - c["qty"])
        write_csv(get_lots_path(), LOT_HEADERS, all_lots)
    return consumed
def check_low_stock():
    alerts = []
    for item in get_all_items():
        sku = item.get("SKU", "")
        reorder = int(item.get("Reorder_Point", 5))
        stock = get_stock_on_hand(sku)
        if stock <= reorder:
            alerts.append({"sku": sku, "item_name": item.get("Item_Name", ""),
                          "category": item.get("Category", ""), "on_hand": stock,
                          "reorder_point": reorder, "status": "OUT" if stock == 0 else "LOW"})
    return alerts

def get_pricing_rules():
    return [r for r in read_csv(get_pricing_rules_path()) if r.get("Active") == "Y"]

def create_pricing_rule(scope, target, method, value, priority=10, notes=""):
    row = {"Rule_ID": generate_id("RULE"), "Scope": scope, "Target": target, "Method": method,
           "Value": str(value), "Priority": str(priority), "Active": "Y",
           "Created_Date": date.today().strftime("%Y-%m-%d"), "Notes": notes}
    append_csv(get_pricing_rules_path(), PRICING_RULE_HEADERS, row)
    return row["Rule_ID"]

def get_inventory_valuation():
    total_units = total_cost = total_retail = 0
    for item in get_all_items():
        sku = item.get("SKU", "")
        stock = get_stock_on_hand(sku)
        cost = get_average_cost(sku)
        retail = float(item.get("Default_Price", 0))
        if stock > 0:
            total_units += stock
            total_cost += stock * cost
            total_retail += stock * retail
    return {"total_units": total_units, "total_cost": total_cost,
            "total_retail": total_retail, "potential_margin": total_retail - total_cost}
def get_reorder_recommendations():
    low_stock = check_low_stock()
    recs = []
    for item_data in low_stock:
        item = item_data["item"]
        recs.append({
            "sku": item["SKU"],
            "item_name": item["Item_Name"],
            "category": item["Category"],
            "subcategory": item.get("Subcategory", ""),
            "on_hand": item_data["stock"],
            "reorder_point": item_data["reorder_point"],
            "avg_cost": get_average_cost(item["SKU"]),
            "default_price": float(item.get("Default_Price", 0))
        })
    return recs

# ==============================================================================
#                              PRICING
# ==============================================================================

def get_pricing_rules():
    return read_csv(get_pricing_rules_path())

def create_pricing_rule(scope, target, method, value, priority=10):
    rule_id = generate_id("PR")
    row = {"Rule_ID": rule_id, "Scope": scope, "Target": target, "Method": method,
           "Value": str(value), "Priority": str(priority), "Active": "Y",
           "Created_Date": date.today().strftime("%Y-%m-%d"), "Notes": ""}
    append_csv(get_pricing_rules_path(), PRICING_RULE_HEADERS, row)
    return rule_id

def calculate_price(sku, base_price):
    rules = [r for r in get_pricing_rules() if r.get("Active") == "Y"]
    item = get_item(sku)
    if not item:
        return base_price
    applicable = []
    for rule in rules:
        scope, target = rule.get("Scope"), rule.get("Target", "*")
        if scope == "SKU" and target == sku:
            applicable.append(rule)
        elif scope == "Category" and target == item.get("Category"):
            applicable.append(rule)
        elif scope == "Subcategory" and target == item.get("Subcategory"):
            applicable.append(rule)
        elif scope == "Global":
            applicable.append(rule)
    if not applicable:
        return base_price
    applicable.sort(key=lambda x: int(x.get("Priority", 10)))
    rule = applicable[0]
    method, value = rule.get("Method"), float(rule.get("Value", 0))
    if method == "FIXED":
        return value
    elif method == "MARKUP":
        return base_price * (1 + value / 100)
    elif method == "DISCOUNT":
        return base_price * (1 - value / 100)
    return base_price
# ==============================================================================
#                              SALES
# ==============================================================================

def record_sale(items, emp_id, emp_name, payment_method, amount_received, notes="", card_fee=0.0):
    """
    Expects items like:
      {"sku":"...", "name":"...", "price":7.98, "qty":3}
    Also accepts "quantity" instead of "qty".
    Returns: (success: bool, result: dict)
    """
    def _to_int(v, default=1):
        try:
            return int(float(v))
        except Exception:
            return default

    now = datetime.now()
    transaction_id = f"TRX{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"

    pm = (payment_method or "CASH").strip().upper()
    try:
        amt_recv = float(amount_received or 0)
    except Exception:
        amt_recv = 0.0

    if not items:
        return False, {"error": "No items in cart"}

    normalized = []
    subtotal = 0.0
    total_cogs = 0.0
    total_items = 0

    for it in items:
        sku = str(it.get("sku") or it.get("SKU") or "").strip()
        name = str(
            it.get("name")
            or it.get("Item_Name")
            or it.get("item_name")
            or it.get("Item")
            or sku
            or "Item"
        ).strip()

        qty = _to_int(it.get("quantity", it.get("qty", 1)), default=1)
        if qty <= 0:
            continue

        try:
            unit_price = float(it.get("price", it.get("Unit_Price", 0)) or 0)
        except Exception:
            unit_price = 0.0

        qty_before = ""
        if sku:
            try:
                qty_before = str(get_stock_on_hand(sku))
            except Exception:
                qty_before = ""

        line_total = round(unit_price * qty, 2)
        subtotal += line_total
        total_items += qty

        consumed = []
        line_cogs = 0.0
        if sku:
            try:
                consumed = consume_from_lots(sku, qty, transaction_id, emp_id)
                line_cogs = sum(float(c["qty"]) * float(c["cost"]) for c in consumed)
            except Exception:
                consumed = []
                line_cogs = 0.0

        total_cogs += line_cogs
        unit_cost = (line_cogs / qty) if qty else 0.0

        qty_after = ""
        if sku:
            try:
                qty_after = str(get_stock_on_hand(sku))
            except Exception:
                qty_after = ""

        normalized.append({
            "sku": sku,
            "name": name,
            "qty": qty,
            "unit_price": unit_price,
            "unit_cost": unit_cost,
            "line_total": line_total,
            "line_cogs": round(line_cogs, 2),
            "qty_before": qty_before,
            "qty_after": qty_after,
        })

    if not normalized:
        return False, {"error": "No valid items to record"}

    tax = round(subtotal * float(TAX_RATE), 2)
    try:
        card_fee_amt = float(card_fee or 0)
    except Exception:
        card_fee_amt = 0.0
    if pm != "CARD":
        card_fee_amt = 0.0
    total = round(subtotal + tax + card_fee_amt, 2)

    change_due = 0.0
    if pm == "CASH":
        change_due = round(max(0.0, amt_recv - total), 2)

    gross_profit = round(total - total_cogs, 2)

    # --- write TRANSACTION header row ---
    tx_row = {
        "Transaction_ID": transaction_id,
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%H:%M:%S"),
        "Employee_ID": str(emp_id),
        "Employee_Name": str(emp_name),
        "Item_Count": str(total_items),
        "Subtotal": f"{subtotal:.2f}",
        "Tax": f"{tax:.2f}",
        "Card_Fee": f"{card_fee_amt:.2f}",
        "Grand_Total": f"{total:.2f}",
        "Payment_Method": pm,
        "Amount_Received": f"{amt_recv:.2f}",
        "Change_Due": f"{change_due:.2f}",
        "Receipt_Number": transaction_id,
        "Notes": notes or "",
        # extra keys are OK if append_csv ignores extras
        "COGS_Total": f"{total_cogs:.2f}",
        "Gross_Profit": f"{gross_profit:.2f}",
    }
    # Capture the durability result of every write. A failed write must FAIL
    # LOUD (return success=False) so the cashier re-rings instead of the sale
    # being silently dropped while the screen says "complete".
    tx_ok = append_csv(get_transaction_path(now.date()), TRANSACTION_HEADERS, tx_row)
    lines_ok = True

    # --- write SALES line rows (one per cart line) ---
    for n in normalized:
        meta = get_item(n["sku"]) or {}
        category = meta.get("Category", "") or ""
        subcategory = meta.get("Subcategory", "") or ""
        product_name = meta.get("Product_Name", "") or meta.get("Item_Name", n["name"]) or n["name"]
        item_name = meta.get("Item_Name", n["name"]) or n["name"]
        size = meta.get("Size", "") or ""
        item_desc = meta.get("Item_Description", "") or meta.get("Notes", "") or ""

        # proportional line tax (optional)
        line_tax = 0.0
        if subtotal > 0:
            line_tax = round((n["line_total"] / subtotal) * tax, 2)

        sales_row = {
            "Date": now.strftime("%Y-%m-%d"),
            "Time": now.strftime("%H:%M:%S"),
            "Transaction_ID": transaction_id,
            "Employee_ID": str(emp_id),
            "Employee_Name": str(emp_name),

            "Category": category,
            "Subcategory": subcategory,
            "Product_Name": product_name,
            "Item_Name": item_name,
            "SKU": n["sku"],

            "Quantity": str(n["qty"]),
            "Size": size,
            "Item_Description": item_desc,

            "Unit_Price": f"{n['unit_price']:.2f}",
            "Unit_Cost": f"{n['unit_cost']:.2f}",
            "COGS_Line": f"{n['line_cogs']:.2f}",

            "Subtotal": f"{subtotal:.2f}",
            "Tax_Rate": str(TAX_RATE),
            "Tax_Amount": f"{line_tax:.2f}",
            "Line_Total": f"{n['line_total']:.2f}",

            "Payment_Method": pm,
            "Amount_Received": f"{amt_recv:.2f}",
            "Change_Due": f"{change_due:.2f}",
            "Notes": notes or "",

            # extra fields are fine if ignored
            "Qty_Remaining_Before": n["qty_before"],
            "Qty_Remaining_After": n["qty_after"],
            "Gross_Margin": f"{(n['line_total'] - n['line_cogs']):.2f}",
        }
        if not append_csv(get_sales_path(now.date()), SALES_HEADERS, sales_row):
            lines_ok = False

    if not (tx_ok and lines_ok):
        # Best-effort: preserve the sale to a recovery file so nothing is lost,
        # then fail loud. complete_sale() surfaces result["error"] to the cashier.
        try:
            append_csv(get_failed_sales_path(), FAILED_SALE_HEADERS, {
                "Transaction_ID": transaction_id,
                "Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "Employee_ID": str(emp_id),
                "Total": f"{total:.2f}",
                "Header_Written": "Y" if tx_ok else "N",
                "Lines_Written": "Y" if lines_ok else "N",
                "Payload_JSON": json.dumps(
                    {"items": normalized, "payment": pm, "amount_received": amt_recv},
                    ensure_ascii=False),
            })
        except Exception:
            pass
        return False, {
            "error": "SALE NOT RECORDED -- write failure. Saved to recovery log; re-ring to confirm.",
            "transaction_id": transaction_id,
        }

    return True, {
        "transaction_id": transaction_id,
        "subtotal": round(subtotal, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
        "change_due": round(change_due, 2),
        "total_items": total_items,
        "cogs_total": round(total_cogs, 2),
        "gross_profit": gross_profit,
    }


def get_transactions_for_date(d=None):
    return read_csv(get_transaction_path(d))

def get_sales_for_date(d=None):
    return read_csv(get_sales_path(d))


# ==============================================================================
#                              REPORTS
# ==============================================================================

def generate_daily_summary(d=None):

    if d is None:
        d = date.today()

    trans = get_transactions_for_date(d) or []
    sales = get_sales_for_date(d) or []

    def _f(row, *keys, default=0.0):
        for k in keys:
            v = row.get(k)
            if v not in (None, "", "None"):
                try:
                    return float(v)
                except Exception:
                    pass
        return float(default)

    total_trans = len(trans)
    total_rev = sum(_f(t, "Total", "Grand_Total") for t in trans)
    total_tax = sum(_f(t, "Tax") for t in trans)

    cash = 0.0
    card = 0.0
    for t in trans:
        pm = (t.get("Payment_Method") or "").strip().upper()
        amt = _f(t, "Total", "Grand_Total")
        if pm == "CASH":
            cash += amt
        elif pm in ("CARD", "DEBIT", "CREDIT"):
            card += amt

    total_items = 0
    emp_sales = defaultdict(float)
    cat_sales = defaultdict(lambda: {"qty": 0, "revenue": 0.0})

    for s in sales:
        # skip blank/summary rows if any
        if not (s.get("Item_Name") or s.get("SKU")):
            continue
        try:
            qty = int(float(s.get("Quantity", 0) or 0))
        except Exception:
            qty = 0
        rev = _f(s, "Line_Total", default=0.0)

        if qty <= 0 and rev == 0:
            continue

        total_items += max(qty, 0)
        emp_sales[(s.get("Employee_Name") or "Unknown")] += rev

        cat = (s.get("Category") or "Other").strip() or "Other"
        cat_sales[cat]["qty"] += max(qty, 0)
        cat_sales[cat]["revenue"] += rev

    # Timeclock hours summary (optional; safe if file missing)
    emp_hrs = {}
    total_hours = 0.0
    total_overtime = 0.0
    try:
        tc = read_csv(get_timeclock_path(d)) or []
        for p in tc:
            if p.get("Punch_Type") == "CLOCK_OUT":
                hrs = float(p.get("Hours_Worked_Today", 0) or 0)
                ot = float(p.get("Overtime_Hours", 0) or 0)
                emp_hrs[p.get("Employee_Name", "")] = {"hours": hrs, "overtime": ot}
                total_hours += hrs
                total_overtime += ot
    except Exception:
        pass

    top = max(emp_sales.items(), key=lambda x: x[1]) if emp_sales else ("", 0)

    return {
        "date": d.strftime("%Y-%m-%d"),
        "total_transactions": total_trans,
        "total_revenue": round(total_rev, 2),
        "total_tax": round(total_tax, 2),
        "cash_sales": round(cash, 2),
        "card_sales": round(card, 2),
        "total_items": int(total_items),
        "category_sales": dict(cat_sales),
        "employee_sales": dict(emp_sales),
        "total_hours": round(total_hours, 2),
        "total_overtime": round(total_overtime, 2),
        "employees_worked": len(emp_hrs),
        "employee_hours": emp_hrs,
        "top_seller_name": top[0],
        "top_seller_revenue": round(top[1], 2),
        "low_stock_count": len(check_low_stock()),
    }


def generate_employee_dashboard(d=None):
    """
    Employee leaderboard + category breakdown.
    Safe even if some rows are missing fields.
    """
    if d is None:
        d = date.today()

    sales = get_sales_for_date(d) or []
    employees = {}

    for s in sales:
        if not (s.get("Item_Name") or s.get("SKU")):
            continue

        emp = (s.get("Employee_Name") or "Unknown").strip() or "Unknown"
        if emp not in employees:
            employees[emp] = {
                "total_revenue": 0.0,
                "transactions": set(),
                "items_sold": 0,
                "categories": defaultdict(float),
            }

        try:
            employees[emp]["total_revenue"] += float(s.get("Line_Total", 0) or 0)
            employees[emp]["transactions"].add(s.get("Transaction_ID", "") or "")
            employees[emp]["items_sold"] += int(float(s.get("Quantity", 0) or 0))
            employees[emp]["categories"][(s.get("Category") or "Other")] += float(s.get("Line_Total", 0) or 0)
        except Exception:
            pass

    for emp in employees.values():
        emp["transaction_count"] = len(emp["transactions"])
        emp["categories"] = dict(emp["categories"])
        del emp["transactions"]

    leaderboard = sorted(employees.items(), key=lambda x: x[1]["total_revenue"], reverse=True)
    team_rev = sum(e["total_revenue"] for e in employees.values())

    return {
        "date": d.strftime("%Y-%m-%d"),
        "employees": employees,
        "leaderboard": leaderboard,
        "team_revenue": round(team_rev, 2),
        "team_transactions": sum(e["transaction_count"] for e in employees.values()),
    }


# ==============================================================================
#                              TIME CLOCK
# ==============================================================================

def get_employee_status(emp_id):
    punches = [p for p in read_csv(get_timeclock_path()) if p.get("Employee_ID") == emp_id]
    if not punches:
        return {"status": "NOT_CLOCKED_IN", "hours_today": 0, "overtime": 0}
    last = punches[-1]
    pt = last.get("Punch_Type", "")
    status = "CLOCKED_OUT" if pt == "CLOCK_OUT" else "ON_BREAK" if pt in ("BREAK", "LUNCH") else "WORKING"
    return {"status": status, "last_punch": pt, "hours_today": float(last.get("Hours_Worked_Today", 0)),
            "overtime": float(last.get("Overtime_Hours", 0))}

def _parse_dt_row(p):
    # safest: Date + Time together
    d = (p.get("Date") or "").strip()
    t = (p.get("Time") or "00:00:00").strip()

    # accept HH:MM or HH:MM:SS
    if len(t.split(":")) == 2:
        t = t + ":00"

    try:
        return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M:%S")
    except Exception:
        # fallback: now (won't crash your app)
        return datetime.now()

def _calc_hours(emp_id, target_date=None):
    """
    Calculate live hours for a single day.
    Returns: (hours_today, overtime_hours)
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    punches = [
        p for p in read_csv(get_timeclock_path())
        if p.get("Employee_ID") == emp_id and p.get("Date") == target_date
    ]

    if not punches:
        return 0.0, 0.0

    punches.sort(key=_parse_dt_row)

    total_minutes = 0.0
    clock_in_dt = None

    for p in punches:
        pt = (p.get("Punch_Type") or "").upper()
        dt = _parse_dt_row(p)

        if pt == "CLOCK_IN":
            clock_in_dt = dt

        elif pt == "CLOCK_OUT" and clock_in_dt:
            total_minutes += (dt - clock_in_dt).total_seconds() / 60.0
            clock_in_dt = None

        elif pt in ("BREAK", "LUNCH") and clock_in_dt:
            # break starts -> stop counting work time
            total_minutes += (dt - clock_in_dt).total_seconds() / 60.0
            clock_in_dt = None

        elif pt in ("END_BREAK", "END_LUNCH"):
            # break ends -> resume counting
            clock_in_dt = dt

    # still clocked in right now -> count live time up to now
    if clock_in_dt:
        total_minutes += (datetime.now() - clock_in_dt).total_seconds() / 60.0

    hours = total_minutes / 60.0
    return round(hours, 2), round(max(0.0, hours - 8.0), 2)


def clock_in(emp_id, emp_name, notes=""):
    status = get_employee_status(emp_id)
    if status.get("status") in ("WORKING", "ON_BREAK"):
        return False, "Already clocked in", status

    now = datetime.now()
    row = {
        "Punch_ID": generate_id("P"),
        "Date": now.strftime("%Y-%m-%d"),
        "Time": now.strftime("%H:%M:%S"),
        "Employee_ID": emp_id,
        "Employee_Name": emp_name,
        "Punch_Type": "CLOCK_IN",
        "Hours_Worked_Today": "0",
        "Overtime_Hours": "0",
        "Notes": notes,
    }
    append_csv(get_timeclock_path(), TIMECLOCK_HEADERS, row)
    append_audit_event("punch", {"punch_id": row.get("Punch_ID"), "emp_id": row.get("Employee_ID"),
                                 "name": row.get("Employee_Name"), "type": row.get("Punch_Type"),
                                 "date": row.get("Date"), "time": row.get("Time")})
    return True, f"Clocked in at {now.strftime('%I:%M %p')}", {}


def get_employee_status(emp_id):
    punches = [p for p in read_csv(get_timeclock_path()) if p.get("Employee_ID") == emp_id]

    if not punches:
        return {"status": "NOT_CLOCKED_IN", "hours_today": 0.0, "overtime": 0.0, "last_punch": ""}

    # last punch overall = current status
    punches.sort(key=_parse_dt_row)
    last = punches[-1]
    pt = (last.get("Punch_Type") or "").upper()

    if pt == "CLOCK_OUT":
        status = "CLOCKED_OUT"
    elif pt in ("BREAK", "LUNCH"):
        status = "ON_BREAK"
    else:
        status = "WORKING"

    # hours_today should be LIVE and for TODAY only
    hours_today, overtime = _calc_hours(emp_id)

    return {
        "status": status,
        "last_punch": pt,
        "hours_today": float(hours_today),
        "overtime": float(overtime),
    }


def clock_out(emp_id, emp_name, notes=""):
    status = get_employee_status(emp_id)
    if status["status"] != "WORKING":
        return False, "Not currently working", status
    now = datetime.now()
    hours, ot = _calc_hours(emp_id)
    row = {"Punch_ID": generate_id("P"), "Date": now.strftime("%Y-%m-%d"), "Time": now.strftime("%H:%M:%S"),
           "Employee_ID": emp_id, "Employee_Name": emp_name, "Punch_Type": "CLOCK_OUT",
           "Hours_Worked_Today": str(hours), "Overtime_Hours": str(ot), "Notes": notes}
    append_csv(get_timeclock_path(), TIMECLOCK_HEADERS, row)
    append_audit_event("punch", {"punch_id": row.get("Punch_ID"), "emp_id": row.get("Employee_ID"),
                                 "name": row.get("Employee_Name"), "type": row.get("Punch_Type"),
                                 "date": row.get("Date"), "time": row.get("Time")})
    return True, f"Clocked out - {hours:.2f} hrs", {"hours": hours, "overtime": ot}

def start_break(emp_id, emp_name, break_type="BREAK"):
    status = get_employee_status(emp_id)
    if status["status"] != "WORKING":
        return False, "Must be working", status
    now = datetime.now()
    hours, ot = _calc_hours(emp_id)
    row = {"Punch_ID": generate_id("P"), "Date": now.strftime("%Y-%m-%d"), "Time": now.strftime("%H:%M:%S"),
           "Employee_ID": emp_id, "Employee_Name": emp_name, "Punch_Type": break_type,
           "Hours_Worked_Today": str(hours), "Overtime_Hours": str(ot), "Notes": ""}
    append_csv(get_timeclock_path(), TIMECLOCK_HEADERS, row)
    append_audit_event("punch", {"punch_id": row.get("Punch_ID"), "emp_id": row.get("Employee_ID"),
                                 "name": row.get("Employee_Name"), "type": row.get("Punch_Type"),
                                 "date": row.get("Date"), "time": row.get("Time")})
    return True, f"Started {break_type.lower()}", {}

def end_break(emp_id, emp_name):
    status = get_employee_status(emp_id)
    if status["status"] != "ON_BREAK":
        return False, "Not on break", status
    now = datetime.now()
    hours, ot = _calc_hours(emp_id)
    pt = "END_LUNCH" if status.get("last_punch") == "LUNCH" else "END_BREAK"
    row = {"Punch_ID": generate_id("P"), "Date": now.strftime("%Y-%m-%d"), "Time": now.strftime("%H:%M:%S"),
           "Employee_ID": emp_id, "Employee_Name": emp_name, "Punch_Type": pt,
           "Hours_Worked_Today": str(hours), "Overtime_Hours": str(ot), "Notes": ""}
    append_csv(get_timeclock_path(), TIMECLOCK_HEADERS, row)
    append_audit_event("punch", {"punch_id": row.get("Punch_ID"), "emp_id": row.get("Employee_ID"),
                                 "name": row.get("Employee_Name"), "type": row.get("Punch_Type"),
                                 "date": row.get("Date"), "time": row.get("Time")})
    return True, "Break ended", {}
def get_punches_for_date(target_date, employee_id=None):
    punches = read_csv(get_timeclock_path(target_date))
    if employee_id:
        punches = [p for p in punches if p.get("Employee_ID") == employee_id]
    return punches

# ==============================================================================
#                              TIME CLOCK EDITING
# ==============================================================================

def get_punch_by_id(punch_id, search_days=14):
    today = date.today()
    for i in range(search_days):
        target = today - timedelta(days=i)
        punches = read_csv(get_timeclock_path(target))
        for p in punches:
            if p.get("Punch_ID") == punch_id:
                p["_file_date"] = target
                return p
    return None

def edit_punch(punch_id, editor_id, editor_name, new_date=None, new_time=None, new_type=None, reason=""):
    if not reason:
        return False, "Reason is required"
    punch = get_punch_by_id(punch_id)
    if not punch:
        return False, "Punch not found"
    file_date = punch.get("_file_date")
    original_date = punch.get("Date")
    original_time = punch.get("Time")
    original_type = punch.get("Punch_Type")
    final_date = new_date if new_date else original_date
    final_time = new_time if new_time else original_time
    final_type = new_type if new_type else original_type
    valid_types = ["CLOCK_IN", "CLOCK_OUT", "BREAK", "LUNCH", "END_BREAK", "END_LUNCH"]
    if final_type not in valid_types:
        return False, f"Invalid punch type"
    edit_row = {"Edit_ID": generate_id("EDIT"), "Punch_ID": punch_id,
                "Edit_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Editor_ID": editor_id, "Editor_Name": editor_name,
                "Original_Date": original_date, "Original_Time": original_time, "Original_Type": original_type,
                "New_Date": final_date, "New_Time": final_time, "New_Type": final_type,
                "Reason": reason, "Approved_By": editor_id, "Approved_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    append_csv(get_timeclock_edits_path(), TIMECLOCK_EDIT_HEADERS, edit_row)
    append_audit_event("timeclock_edit", {"punch_id": edit_row.get("Punch_ID"), "editor_id": edit_row.get("Editor_ID"),
                                          "editor": edit_row.get("Editor_Name"), "from_type": edit_row.get("Original_Type"),
                                          "to_type": edit_row.get("New_Type"), "reason": edit_row.get("Reason")})
    punches = read_csv(get_timeclock_path(file_date))
    for p in punches:
        if p.get("Punch_ID") == punch_id:
            p["Date"] = final_date
            p["Time"] = final_time
            p["Punch_Type"] = final_type
            p["Notes"] = f"{p.get('Notes', '')} [EDITED by {editor_name}: {reason}]".strip()
    write_csv(get_timeclock_path(file_date), TIMECLOCK_HEADERS, punches)
    create_notification(punch.get("Employee_ID"), punch.get("Employee_Name"),
        f"Your time punch on {original_date} was edited by {editor_name}. Reason: {reason}", "TIMECLOCK")
    return True, "Punch edited successfully"

def add_punch(employee_id, employee_name, punch_date, punch_time, punch_type, added_by_id, added_by_name, reason=""):
    if not reason:
        return False, "Reason is required"
    valid_types = ["CLOCK_IN", "CLOCK_OUT", "BREAK", "LUNCH", "END_BREAK", "END_LUNCH"]
    if punch_type not in valid_types:
        return False, "Invalid punch type"
    try:
        target_date = datetime.strptime(punch_date, "%Y-%m-%d").date()
    except:
        return False, "Invalid date format"
    punch_id = generate_id("P")
    row = {"Punch_ID": punch_id, "Date": punch_date, "Time": punch_time,
           "Employee_ID": employee_id, "Employee_Name": employee_name, "Punch_Type": punch_type,
           "Hours_Worked_Today": "0", "Overtime_Hours": "0",
           "Notes": f"[ADDED by {added_by_name}: {reason}]"}
    append_csv(get_timeclock_path(target_date), TIMECLOCK_HEADERS, row)
    edit_row = {"Edit_ID": generate_id("EDIT"), "Punch_ID": punch_id,
                "Edit_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Editor_ID": added_by_id, "Editor_Name": added_by_name,
                "Original_Date": "", "Original_Time": "", "Original_Type": "",
                "New_Date": punch_date, "New_Time": punch_time, "New_Type": punch_type,
                "Reason": f"ADDED: {reason}", "Approved_By": added_by_id,
                "Approved_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    append_csv(get_timeclock_edits_path(), TIMECLOCK_EDIT_HEADERS, edit_row)
    append_audit_event("timeclock_edit", {"punch_id": edit_row.get("Punch_ID"), "editor_id": edit_row.get("Editor_ID"),
                                          "editor": edit_row.get("Editor_Name"), "from_type": edit_row.get("Original_Type"),
                                          "to_type": edit_row.get("New_Type"), "reason": edit_row.get("Reason")})
    create_notification(employee_id, employee_name,
        f"A time punch was added for {punch_date} by {added_by_name}. Reason: {reason}", "TIMECLOCK")
    return True, f"Punch added: {punch_id}"

def delete_punch(punch_id, deleted_by_id, deleted_by_name, reason=""):
    if not reason:
        return False, "Reason is required"
    punch = get_punch_by_id(punch_id)
    if not punch:
        return False, "Punch not found"
    file_date = punch.get("_file_date")
    edit_row = {"Edit_ID": generate_id("EDIT"), "Punch_ID": punch_id,
                "Edit_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Editor_ID": deleted_by_id, "Editor_Name": deleted_by_name,
                "Original_Date": punch.get("Date"), "Original_Time": punch.get("Time"),
                "Original_Type": punch.get("Punch_Type"),
                "New_Date": "DELETED", "New_Time": "DELETED", "New_Type": "DELETED",
                "Reason": f"DELETED: {reason}", "Approved_By": deleted_by_id,
                "Approved_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    append_csv(get_timeclock_edits_path(), TIMECLOCK_EDIT_HEADERS, edit_row)
    append_audit_event("timeclock_edit", {"punch_id": edit_row.get("Punch_ID"), "editor_id": edit_row.get("Editor_ID"),
                                          "editor": edit_row.get("Editor_Name"), "from_type": edit_row.get("Original_Type"),
                                          "to_type": edit_row.get("New_Type"), "reason": edit_row.get("Reason")})
    punches = read_csv(get_timeclock_path(file_date))
    for p in punches:
        if p.get("Punch_ID") == punch_id:
            p["Punch_Type"] = f"DELETED_{p['Punch_Type']}"
            p["Notes"] = f"[DELETED by {deleted_by_name}: {reason}] {p.get('Notes', '')}".strip()
    write_csv(get_timeclock_path(file_date), TIMECLOCK_HEADERS, punches)
    create_notification(punch.get("Employee_ID"), punch.get("Employee_Name"),
        f"Your time punch on {punch.get('Date')} was deleted by {deleted_by_name}. Reason: {reason}", "TIMECLOCK")
    return True, "Punch deleted"

def get_timeclock_edit_history(employee_id=None, days=30):
    edits = read_csv(get_timeclock_edits_path())
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    edits = [e for e in edits if e.get("Edit_Date", "") >= cutoff]
    return sorted(edits, key=lambda x: x.get("Edit_Date", ""), reverse=True)

# ==============================================================================
#            TAMPER-EVIDENT AUDIT CHAIN (time clock + payroll)
# ==============================================================================
# Append-only, hash-chained journal. Each line's row_hash folds in the PREVIOUS
# line's hash, so editing / deleting / inserting any past line breaks every line
# after it -- making out-of-band tampering with punches or payroll DETECTABLE.
# It is a sidecar file: it never touches the existing CSV schemas.

def get_audit_chain_path():
    p = TIMECLOCK_DIR / "_audit" / "chain.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def append_audit_event(category, payload):
    """Append a hash-chained audit line. Returns the row_hash, or None on failure.

    Best-effort + never raises into a punch/payroll flow: if the journal can't be
    written we return None rather than blocking the operation. verify_audit_chain()
    later proves whether the chain is intact.
    """
    with _IO_LOCK:
        path = get_audit_chain_path()
        prev_hash, seq = "GENESIS", 0
        if path.exists():
            try:
                last = None
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            last = line
                if last:
                    prev = json.loads(last)
                    prev_hash = prev.get("row_hash", "GENESIS")
                    seq = int(prev.get("seq", 0)) + 1
            except Exception:
                pass  # unreadable tail -> still append; verify will flag the break
        core = {
            "seq": seq,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": str(category),
            "payload": payload,
            "prev_hash": prev_hash,
        }
        row_hash = hashlib.sha256((prev_hash + _canonical(core)).encode("utf-8")).hexdigest()
        record = dict(core); record["row_hash"] = row_hash
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(_canonical(record) + "\n")
                f.flush()
                os.fsync(f.fileno())
            return row_hash
        except Exception:
            return None

def verify_audit_chain():
    """Recompute the whole chain. Returns (ok: bool, first_broken_seq: int|None).

    ok=False means a line was edited, deleted, or inserted out of band -- the
    first_broken_seq is where the chain stops matching.
    """
    path = get_audit_chain_path()
    if not path.exists():
        return True, None
    prev_hash = "GENESIS"
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                core = {
                    "seq": rec.get("seq"),
                    "ts": rec.get("ts"),
                    "category": rec.get("category"),
                    "payload": rec.get("payload"),
                    "prev_hash": rec.get("prev_hash"),
                }
                expected = hashlib.sha256((prev_hash + _canonical(core)).encode("utf-8")).hexdigest()
                if rec.get("prev_hash") != prev_hash or rec.get("row_hash") != expected:
                    return False, rec.get("seq")
                prev_hash = rec.get("row_hash")
    except Exception:
        return False, -1
    return True, None


# ==============================================================================
#                              TIME OFF
# ==============================================================================

def request_time_off(emp_id, emp_name, start, end, reason=""):
    if start < date.today():
        return False, "Cannot request past dates", ""
    if end < start:
        return False, "End must be after start", ""
    days = (end - start).days + 1
    req_id = generate_id("REQ")
    row = {"Request_ID": req_id, "Employee_ID": emp_id, "Employee_Name": emp_name,
           "Request_Date": date.today().strftime("%Y-%m-%d"), "Start_Date": start.strftime("%Y-%m-%d"),
           "End_Date": end.strftime("%Y-%m-%d"), "Days_Requested": str(days), "Reason": reason,
           "Status": "Pending", "Manager_Name": "", "Approval_Date": "", "Manager_Notes": ""}
    append_csv(get_timeoff_path(), TIMEOFF_HEADERS, row)
    return True, f"Request submitted ({days} days)", req_id

def get_time_off_requests(employee_id=None, status=None, year=None):
    reqs = read_csv(get_timeoff_path(year))
    if employee_id:
        reqs = [r for r in reqs if r.get("Employee_ID") == employee_id]
    if status:
        reqs = [r for r in reqs if r.get("Status") == status]
    return reqs

def get_pending_requests():
    return get_time_off_requests(status="Pending")

def approve_time_off(req_id, mgr_id, mgr_name, approved, notes=""):
    reqs = read_csv(get_timeoff_path())
    for r in reqs:
        if r.get("Request_ID") == req_id:
            if r.get("Status") != "Pending":
                return False, f"Already {r.get('Status')}"
            r["Status"] = "Approved" if approved else "Denied"
            r["Manager_Name"] = mgr_name
            r["Approval_Date"] = date.today().strftime("%Y-%m-%d")
            r["Manager_Notes"] = notes
            write_csv(get_timeoff_path(), TIMEOFF_HEADERS, reqs)
            status_text = "approved" if approved else "denied"
            create_notification(r.get("Employee_ID"), r.get("Employee_Name"),
                f"Your time off request ({r.get('Start_Date')} to {r.get('End_Date')}) was {status_text} by {mgr_name}." +
                (f" Note: {notes}" if notes else ""), "TIMEOFF")
            return True, status_text.capitalize()
    return False, "Not found"

# ==============================================================================
#                              TASK MANAGEMENT
# ==============================================================================

def ensure_task_files():
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    ensure_csv(TASKS_MASTER_PATH, TASKS_MASTER_HEADERS)
    ensure_csv(TASK_ASSIGNMENTS_PATH, TASK_ASSIGNMENTS_HEADERS)
    ensure_csv(TASK_EVENTS_PATH, TASK_EVENTS_HEADERS)

def get_all_tasks():
    ensure_task_files()
    return [t for t in read_csv(TASKS_MASTER_PATH) if t.get("Active_Flag") != "0"]

def get_task(task_id):
    for t in read_csv(TASKS_MASTER_PATH):
        if t.get("Task_ID") == task_id:
            return t
    return None

def create_task(title, description="", category="General", priority="MEDIUM",
                estimated_minutes=15, created_by=""):
    ensure_task_files()
    task_id = generate_id("TSK")
    row = {"Task_ID": task_id, "Project_ID": "", "Title": title, "Description": description,
           "Category": category, "Priority": priority, "Estimated_Minutes": str(estimated_minutes),
           "Created_By": created_by, "Created_At": datetime.now().isoformat(), "Active_Flag": "1"}
    append_csv(TASKS_MASTER_PATH, TASKS_MASTER_HEADERS, row)
    return task_id

def assign_task(task_id, employee_id, due_date, assigned_by, notes=""):
    ensure_task_files()
    assignment_id = generate_id("ASN")
    if isinstance(due_date, date):
        due_date = due_date.isoformat()
    row = {"Assignment_ID": assignment_id, "Task_ID": task_id, "Employee_ID": employee_id,
           "Assigned_Date": date.today().isoformat(), "Due_Date": due_date, "Status": "ASSIGNED",
           "Acknowledged_At": "", "Started_At": "", "Completed_At": "", "Skipped_At": "",
           "Skip_Reason": "", "Assigned_By": assigned_by, "Notes_From_Employee": notes, "Quality_Score": ""}
    append_csv(TASK_ASSIGNMENTS_PATH, TASK_ASSIGNMENTS_HEADERS, row)
    log_task_event(assignment_id, assigned_by, "ASSIGNED", f"Due: {due_date}")
    return assignment_id

def get_task_assignments_for_date(target_date):
    ensure_task_files()
    if isinstance(target_date, date):
        target_date = target_date.isoformat()
    assignments = read_csv(TASK_ASSIGNMENTS_PATH)
    return [a for a in assignments if a.get("Due_Date") == target_date]

def get_tasks_for_employee(employee_id, target_date=None):
    ensure_task_files()
    assignments = read_csv(TASK_ASSIGNMENTS_PATH)
    result = [a for a in assignments if a.get("Employee_ID") == employee_id]
    if target_date:
        if isinstance(target_date, date):
            target_date = target_date.isoformat()
        result = [a for a in result if a.get("Due_Date") == target_date]
    for a in result:
        task = get_task(a.get("Task_ID"))
        if task:
            a["task_title"] = task.get("Title")
            a["task_description"] = task.get("Description")
            a["task_category"] = task.get("Category")
            a["task_priority"] = task.get("Priority")
            a["estimated_minutes"] = task.get("Estimated_Minutes")
    return result

def update_task_status(assignment_id, new_status, employee_id, note="", skip_reason=""):
    ensure_task_files()
    assignments = read_csv(TASK_ASSIGNMENTS_PATH)
    now = datetime.now().isoformat()
    for a in assignments:
        if a.get("Assignment_ID") == assignment_id:
            a["Status"] = new_status
            if new_status == "ACKNOWLEDGED":
                a["Acknowledged_At"] = now
            elif new_status == "IN_PROGRESS":
                a["Started_At"] = now
            elif new_status == "COMPLETE":
                a["Completed_At"] = now
            elif new_status == "SKIPPED":
                a["Skipped_At"] = now
                a["Skip_Reason"] = skip_reason
            if note:
                existing = a.get("Notes_From_Employee", "")
                a["Notes_From_Employee"] = f"{existing}\n[{now}] {note}".strip()
            write_csv(TASK_ASSIGNMENTS_PATH, TASK_ASSIGNMENTS_HEADERS, assignments)
            log_task_event(assignment_id, employee_id, new_status, note or skip_reason)
            return True
    return False

def log_task_event(assignment_id, employee_id, event_type, event_data=""):
    ensure_task_files()
    row = {"Event_ID": generate_id("EVT"), "Assignment_ID": assignment_id,
           "Timestamp": datetime.now().isoformat(), "Employee_ID": employee_id,
           "Event_Type": event_type, "Event_Data": event_data}
    append_csv(TASK_EVENTS_PATH, TASK_EVENTS_HEADERS, row)

def get_pending_task_count(employee_id):
    tasks = get_tasks_for_employee(employee_id, date.today())
    return len([t for t in tasks if t.get("Status") in ("ASSIGNED", "ACKNOWLEDGED")])




# ==============================================================================
#                              TASK HELPERS
# ==============================================================================

def normalize_task_priority(p):
    p = (p or "").strip().upper()
    mapping = {
        "LOW": "LOW", "L": "LOW",
        "MED": "MEDIUM", "MEDIUM": "MEDIUM", "M": "MEDIUM",
        "HIGH": "HIGH", "H": "HIGH",
        "URGENT": "HIGH"
    }
    return mapping.get(p, "MEDIUM")


def get_task_by_title(title, category=None):
    """Find an existing active task template by title (+ optional category)."""
    ensure_task_files()
    tnorm = (title or "").strip().lower()
    cnorm = (category or "").strip().lower() if category else None

    for t in read_csv(TASKS_MASTER_PATH):
        if t.get("Active_Flag", "1") == "0":
            continue
        if (t.get("Title", "").strip().lower() == tnorm):
            if cnorm is None:
                return t
            if t.get("Category", "").strip().lower() == cnorm:
                return t
    return None


def get_or_create_task_template(title, description="", category="General", priority="MEDIUM",
                               estimated_minutes=15, created_by=""):
    """
    If a template with same Title (+Category) already exists, reuse it.
    Otherwise create it. This is what makes "custom tasks" auto-save into templates.
    Returns: (task_id, created_new_bool)
    """
    ensure_task_files()

    category = category or "General"
    priority = normalize_task_priority(priority)

    existing = get_task_by_title(title, category=category)
    if existing:
        return existing.get("Task_ID"), False

    task_id = create_task(
        title=title,
        description=description,
        category=category,
        priority=priority,
        estimated_minutes=estimated_minutes,
        created_by=created_by
    )
    return task_id, True


def get_task_assignment(assignment_id):
    """Fetch a single assignment row by Assignment_ID."""
    ensure_task_files()
    for a in read_csv(TASK_ASSIGNMENTS_PATH):
        if a.get("Assignment_ID") == assignment_id:
            return a
    return None


def get_task_events(assignment_id):
    """Event timeline for a task assignment."""
    ensure_task_files()
    ev = [e for e in read_csv(TASK_EVENTS_PATH) if e.get("Assignment_ID") == assignment_id]
    ev.sort(key=lambda x: x.get("Timestamp", ""))
    return ev


def get_business_snapshot():
    today_summary = generate_daily_summary()
    low_stock = check_low_stock()[:10]
    working = []
    for emp in get_all_employees():
        status = get_employee_status(emp.get("Employee_ID"))
        if status.get("status") == "WORKING":
            working.append({"id": emp.get("Employee_ID"), "name": emp.get("Employee_Name")})
    return {
        "today": today_summary,
        "low_stock_count": len(low_stock),
        "working_employees": working,
        "timestamp": datetime.now().isoformat()
    }


# ==============================================================================
#                    ADD TO CONFIG SECTION (near other directories)
# ==============================================================================

PAYROLL_DIR = SCRIPT_DIR / "Payroll"

# ==============================================================================
#                    ADD TO HEADERS SECTION
# ==============================================================================

# Employee Pay Configuration
EMPLOYEE_PAY_HEADERS = [
    "Employee_ID", "Pay_Type", "Hourly_Rate", "Salary_Amount", "Pay_Frequency",
    "Federal_Filing_Status", "State_Filing_Status", "Federal_Allowances", "State_Allowances",
    "Additional_Withholding", "Direct_Deposit", "Bank_Account", "Bank_Routing",
    "Effective_Date", "Last_Updated", "Notes"
]

# Pay Periods
PAY_PERIOD_HEADERS = [
    "Period_ID", "Start_Date", "End_Date", "Pay_Date", "Status",
    "Created_By", "Created_At", "Processed_By", "Processed_At", "Notes"
]

# Payroll Runs (individual employee pay for a period)
PAYROLL_RUN_HEADERS = [
    "Payroll_ID", "Period_ID", "Employee_ID", "Employee_Name",
    "Regular_Hours", "Overtime_Hours", "Holiday_Hours", "PTO_Hours", "Sick_Hours",
    "Gross_Pay", "Federal_Tax", "State_Tax", "Social_Security", "Medicare",
    "Other_Deductions", "Net_Pay", "Pay_Method", "Check_Number",
    "Status", "Created_At", "Approved_By", "Approved_At", "Notes"
]

# Deductions Configuration
DEDUCTION_HEADERS = [
    "Deduction_ID", "Employee_ID", "Deduction_Type", "Description",
    "Amount", "Is_Percentage", "Is_PreTax", "Frequency",
    "Start_Date", "End_Date", "Active", "Notes"
]

# Time Clock Edits (audit trail)
TIMECLOCK_EDIT_HEADERS = [
    "Edit_ID", "Punch_ID", "Edit_Date", "Editor_ID", "Editor_Name",
    "Original_Date", "Original_Time", "Original_Type",
    "New_Date", "New_Time", "New_Type",
    "Reason", "Approved_By", "Approved_At"
]

# Enhanced Task Metrics
TASK_METRICS_HEADERS = [
    "Metric_ID", "Employee_ID", "Period_Start", "Period_End",
    "Tasks_Assigned", "Tasks_Completed", "Tasks_Skipped", "Tasks_Overdue",
    "Avg_Completion_Minutes", "On_Time_Rate", "Quality_Score_Avg",
    "Calculated_At"
]

# ==============================================================================
#                    PATH HELPERS
# ==============================================================================

def get_employee_pay_path():
    return ensure_csv(PAYROLL_DIR / "Employee_Pay_Config.csv", EMPLOYEE_PAY_HEADERS)

def get_pay_periods_path():
    return ensure_csv(PAYROLL_DIR / "Pay_Periods.csv", PAY_PERIOD_HEADERS)

def get_payroll_runs_path(year=None):
    if year is None:
        year = date.today().year
    return ensure_csv(PAYROLL_DIR / f"{year}_Payroll_Runs.csv", PAYROLL_RUN_HEADERS)

def get_deductions_path():
    return ensure_csv(PAYROLL_DIR / "Deductions.csv", DEDUCTION_HEADERS)

def get_timeclock_edits_path():
    return ensure_csv(TIMECLOCK_DIR / "Time_Edits_Audit.csv", TIMECLOCK_EDIT_HEADERS)

def get_task_metrics_path():
    return ensure_csv(TASKS_DIR / "Task_Metrics.csv", TASK_METRICS_HEADERS)


# ==============================================================================
#                    PAYROLL SYSTEM
# ==============================================================================

# Tax rates (2024 simplified - you'd want to update these annually)
FEDERAL_TAX_BRACKETS = [
    (11600, 0.10), (47150, 0.12), (100525, 0.22), (191950, 0.24),
    (243725, 0.32), (609350, 0.35), (float('inf'), 0.37)
]
STATE_TAX_RATE = 0.0725  # California simplified
SOCIAL_SECURITY_RATE = 0.062
SOCIAL_SECURITY_WAGE_BASE = 168600
MEDICARE_RATE = 0.0145
MEDICARE_ADDITIONAL_RATE = 0.009  # Over $200k

def setup_employee_pay(employee_id: str, pay_type: str = "HOURLY",
                       hourly_rate: float = 0, salary_amount: float = 0,
                       pay_frequency: str = "BIWEEKLY", federal_status: str = "SINGLE",
                       state_status: str = "SINGLE", federal_allowances: int = 1,
                       state_allowances: int = 1, additional_withholding: float = 0,
                       direct_deposit: bool = False, bank_account: str = "",
                       bank_routing: str = "", notes: str = "") -> Tuple[bool, str]:
    """
    Set up or update an employee's pay configuration.

    Args:
        employee_id: Employee ID
        pay_type: HOURLY or SALARY
        hourly_rate: Hourly pay rate (if HOURLY)
        salary_amount: Annual salary (if SALARY)
        pay_frequency: WEEKLY, BIWEEKLY, SEMIMONTHLY, MONTHLY
        federal_status: SINGLE, MARRIED, MARRIED_SEPARATE, HEAD_OF_HOUSEHOLD
        state_status: State filing status
        federal_allowances: Number of federal allowances
        state_allowances: Number of state allowances
        additional_withholding: Additional tax to withhold per period
        direct_deposit: Whether to use direct deposit
        bank_account: Bank account number (last 4 shown)
        bank_routing: Bank routing number
        notes: Any notes
    """
    emp = get_employee(employee_id)
    if not emp:
        return False, "Employee not found"

    # Validate pay type
    if pay_type not in ("HOURLY", "SALARY"):
        return False, "Pay type must be HOURLY or SALARY"

    if pay_type == "HOURLY" and hourly_rate <= 0:
        return False, "Hourly rate must be greater than 0"
    if pay_type == "SALARY" and salary_amount <= 0:
        return False, "Salary amount must be greater than 0"

    # Check if config exists
    configs = read_csv(get_employee_pay_path())
    existing = next((c for c in configs if c.get("Employee_ID") == employee_id), None)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "Employee_ID": employee_id,
        "Pay_Type": pay_type,
        "Hourly_Rate": f"{hourly_rate:.2f}",
        "Salary_Amount": f"{salary_amount:.2f}",
        "Pay_Frequency": pay_frequency,
        "Federal_Filing_Status": federal_status,
        "State_Filing_Status": state_status,
        "Federal_Allowances": str(federal_allowances),
        "State_Allowances": str(state_allowances),
        "Additional_Withholding": f"{additional_withholding:.2f}",
        "Direct_Deposit": "Y" if direct_deposit else "N",
        "Bank_Account": bank_account[-4:] if bank_account else "",  # Store only last 4
        "Bank_Routing": bank_routing[-4:] if bank_routing else "",
        "Effective_Date": date.today().strftime("%Y-%m-%d"),
        "Last_Updated": now,
        "Notes": notes
    }

    if existing:
        # Update existing
        for c in configs:
            if c.get("Employee_ID") == employee_id:
                c.update(row)
        write_csv(get_employee_pay_path(), EMPLOYEE_PAY_HEADERS, configs)
        return True, f"Pay configuration updated for employee {employee_id}"
    else:
        # Create new
        append_csv(get_employee_pay_path(), EMPLOYEE_PAY_HEADERS, row)
        return True, f"Pay configuration created for employee {employee_id}"


def get_employee_pay_config(employee_id: str) -> Optional[Dict]:
    """Get an employee's pay configuration."""
    configs = read_csv(get_employee_pay_path())
    return next((c for c in configs if c.get("Employee_ID") == employee_id), None)


def get_all_pay_configs() -> List[Dict]:
    """Get all employee pay configurations."""
    return read_csv(get_employee_pay_path())


def add_deduction(employee_id: str, deduction_type: str, description: str,
                  amount: float, is_percentage: bool = False, is_pretax: bool = False,
                  frequency: str = "PER_PAY", start_date: str = None,
                  end_date: str = None, notes: str = "") -> str:
    """
    Add a deduction for an employee.

    Args:
        employee_id: Employee ID
        deduction_type: Type (401K, HEALTH, DENTAL, VISION, HSA, GARNISHMENT, OTHER)
        description: Description of deduction
        amount: Dollar amount or percentage
        is_percentage: If True, amount is a percentage of gross
        is_pretax: If True, deducted before tax calculation
        frequency: PER_PAY, MONTHLY, ANNUAL
        start_date: When deduction starts
        end_date: When deduction ends (optional)
        notes: Any notes
    """
    deduction_id = generate_id("DED")

    row = {
        "Deduction_ID": deduction_id,
        "Employee_ID": employee_id,
        "Deduction_Type": deduction_type,
        "Description": description,
        "Amount": f"{amount:.2f}",
        "Is_Percentage": "Y" if is_percentage else "N",
        "Is_PreTax": "Y" if is_pretax else "N",
        "Frequency": frequency,
        "Start_Date": start_date or date.today().strftime("%Y-%m-%d"),
        "End_Date": end_date or "",
        "Active": "Y",
        "Notes": notes
    }

    append_csv(get_deductions_path(), DEDUCTION_HEADERS, row)
    return deduction_id


def get_employee_deductions(employee_id: str, active_only: bool = True) -> List[Dict]:
    """Get all deductions for an employee."""
    deductions = read_csv(get_deductions_path())
    result = [d for d in deductions if d.get("Employee_ID") == employee_id]
    if active_only:
        result = [d for d in result if d.get("Active") == "Y"]
    return result


def create_pay_period(start_date: date, end_date: date, pay_date: date,
                      created_by: str, notes: str = "") -> str:
    """
    Create a new pay period.

    Args:
        start_date: First day of pay period
        end_date: Last day of pay period
        pay_date: Date employees will be paid
        created_by: Employee ID of creator
        notes: Any notes
    """
    period_id = generate_id("PP")

    row = {
        "Period_ID": period_id,
        "Start_Date": start_date.strftime("%Y-%m-%d"),
        "End_Date": end_date.strftime("%Y-%m-%d"),
        "Pay_Date": pay_date.strftime("%Y-%m-%d"),
        "Status": "OPEN",
        "Created_By": created_by,
        "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Processed_By": "",
        "Processed_At": "",
        "Notes": notes
    }

    append_csv(get_pay_periods_path(), PAY_PERIOD_HEADERS, row)
    return period_id


def get_pay_periods(status: str = None) -> List[Dict]:
    """Get all pay periods, optionally filtered by status."""
    periods = read_csv(get_pay_periods_path())
    if status:
        periods = [p for p in periods if p.get("Status") == status]
    return periods


def get_pay_period(period_id: str) -> Optional[Dict]:
    """Get a specific pay period by ID."""
    periods = read_csv(get_pay_periods_path())
    return next((p for p in periods if p.get("Period_ID") == period_id), None)


def calculate_hours_for_period(employee_id: str, start_date: date, end_date: date) -> Dict:
    """
    Calculate total hours worked by an employee during a pay period.

    Returns dict with: regular_hours, overtime_hours, total_hours
    """
    total_regular = 0
    total_overtime = 0

    current = start_date
    while current <= end_date:
        # Read time clock for this day
        punches = read_csv(get_timeclock_path(current))
        emp_punches = [p for p in punches if p.get("Employee_ID") == employee_id]

        if emp_punches:
            # Find the clock out punch for this day (has final hours)
            clock_out = next((p for p in reversed(emp_punches)
                             if p.get("Punch_Type") == "CLOCK_OUT"), None)
            if clock_out:
                day_hours = float(clock_out.get("Hours_Worked_Today", 0))
                day_ot = float(clock_out.get("Overtime_Hours", 0))

                regular = day_hours - day_ot
                total_regular += regular
                total_overtime += day_ot

        current += timedelta(days=1)

    return {
        "regular_hours": round(total_regular, 2),
        "overtime_hours": round(total_overtime, 2),
        "total_hours": round(total_regular + total_overtime, 2)
    }


def calculate_federal_tax(annual_income: float, filing_status: str = "SINGLE",
                          allowances: int = 1) -> float:
    """
    Calculate federal income tax withholding (simplified).

    Uses 2024 tax brackets. This is a simplified calculation.
    In production, you'd use IRS Publication 15-T.
    """
    # Standard deduction based on status
    standard_deductions = {
        "SINGLE": 14600,
        "MARRIED": 29200,
        "MARRIED_SEPARATE": 14600,
        "HEAD_OF_HOUSEHOLD": 21900
    }

    standard_deduction = standard_deductions.get(filing_status, 14600)
    allowance_amount = allowances * 4300  # Approximate per-allowance amount

    taxable_income = max(0, annual_income - standard_deduction - allowance_amount)

    tax = 0
    prev_bracket = 0

    for bracket_limit, rate in FEDERAL_TAX_BRACKETS:
        if taxable_income <= bracket_limit:
            tax += (taxable_income - prev_bracket) * rate
            break
        else:
            tax += (bracket_limit - prev_bracket) * rate
            prev_bracket = bracket_limit

    return round(tax, 2)


def calculate_payroll(employee_id: str, period_id: str,
                      holiday_hours: float = 0, pto_hours: float = 0,
                      sick_hours: float = 0, notes: str = "") -> Tuple[bool, Dict]:
    """
    Calculate payroll for an employee for a pay period.

    Returns tuple of (success, payroll_data or error_dict)
    """
    emp = get_employee(employee_id)
    if not emp:
        return False, {"error": "Employee not found"}

    pay_config = get_employee_pay_config(employee_id)
    if not pay_config:
        return False, {"error": "No pay configuration found for employee"}

    period = get_pay_period(period_id)
    if not period:
        return False, {"error": "Pay period not found"}

    # Parse period dates
    start_date = datetime.strptime(period["Start_Date"], "%Y-%m-%d").date()
    end_date = datetime.strptime(period["End_Date"], "%Y-%m-%d").date()

    # Calculate hours from time clock
    hours = calculate_hours_for_period(employee_id, start_date, end_date)
    regular_hours = hours["regular_hours"]
    overtime_hours = hours["overtime_hours"]

    # Calculate gross pay
    pay_type = pay_config.get("Pay_Type", "HOURLY")
    hourly_rate = float(pay_config.get("Hourly_Rate", 0))
    salary_amount = float(pay_config.get("Salary_Amount", 0))
    pay_frequency = pay_config.get("Pay_Frequency", "BIWEEKLY")

    if pay_type == "HOURLY":
        regular_pay = regular_hours * hourly_rate
        overtime_pay = overtime_hours * hourly_rate * 1.5  # Time and a half
        holiday_pay = holiday_hours * hourly_rate * 1.5
        pto_pay = pto_hours * hourly_rate
        sick_pay = sick_hours * hourly_rate
        gross_pay = regular_pay + overtime_pay + holiday_pay + pto_pay + sick_pay

        # For tax calculation, annualize
        periods_per_year = {"WEEKLY": 52, "BIWEEKLY": 26, "SEMIMONTHLY": 24, "MONTHLY": 12}
        annual_gross = gross_pay * periods_per_year.get(pay_frequency, 26)
    else:
        # Salary
        periods_per_year = {"WEEKLY": 52, "BIWEEKLY": 26, "SEMIMONTHLY": 24, "MONTHLY": 12}
        gross_pay = salary_amount / periods_per_year.get(pay_frequency, 26)
        annual_gross = salary_amount

    # Get pre-tax deductions
    deductions = get_employee_deductions(employee_id)
    pretax_deductions = 0
    posttax_deductions = 0

    for ded in deductions:
        amount = float(ded.get("Amount", 0))
        is_percentage = ded.get("Is_Percentage") == "Y"
        is_pretax = ded.get("Is_PreTax") == "Y"

        if is_percentage:
            ded_amount = gross_pay * (amount / 100)
        else:
            ded_amount = amount

        if is_pretax:
            pretax_deductions += ded_amount
        else:
            posttax_deductions += ded_amount

    # Calculate taxable income
    taxable_gross = gross_pay - pretax_deductions
    annual_taxable = annual_gross - (pretax_deductions * periods_per_year.get(pay_frequency, 26))

    # Calculate taxes
    federal_status = pay_config.get("Federal_Filing_Status", "SINGLE")
    federal_allowances = int(pay_config.get("Federal_Allowances", 1))
    additional_withholding = float(pay_config.get("Additional_Withholding", 0))

    annual_federal_tax = calculate_federal_tax(annual_taxable, federal_status, federal_allowances)
    federal_tax = (annual_federal_tax / periods_per_year.get(pay_frequency, 26)) + additional_withholding

    state_tax = taxable_gross * STATE_TAX_RATE

    social_security = min(taxable_gross * SOCIAL_SECURITY_RATE,
                          SOCIAL_SECURITY_WAGE_BASE * SOCIAL_SECURITY_RATE / periods_per_year.get(pay_frequency, 26))

    medicare = taxable_gross * MEDICARE_RATE
    if annual_taxable > 200000:
        medicare += taxable_gross * MEDICARE_ADDITIONAL_RATE

    # Calculate net pay
    total_taxes = federal_tax + state_tax + social_security + medicare
    total_deductions = pretax_deductions + posttax_deductions
    net_pay = gross_pay - total_taxes - total_deductions

    payroll_data = {
        "employee_id": employee_id,
        "employee_name": emp.get("Employee_Name"),
        "period_id": period_id,
        "regular_hours": regular_hours,
        "overtime_hours": overtime_hours,
        "holiday_hours": holiday_hours,
        "pto_hours": pto_hours,
        "sick_hours": sick_hours,
        "gross_pay": round(gross_pay, 2),
        "federal_tax": round(federal_tax, 2),
        "state_tax": round(state_tax, 2),
        "social_security": round(social_security, 2),
        "medicare": round(medicare, 2),
        "pretax_deductions": round(pretax_deductions, 2),
        "posttax_deductions": round(posttax_deductions, 2),
        "total_deductions": round(total_deductions + total_taxes, 2),
        "net_pay": round(net_pay, 2),
        "pay_method": "DIRECT_DEPOSIT" if pay_config.get("Direct_Deposit") == "Y" else "CHECK",
        "notes": notes
    }

    return True, payroll_data


def run_payroll(period_id: str, processed_by: str) -> Tuple[bool, Dict]:
    """
    Run payroll for all employees for a pay period.

    Returns tuple of (success, results_dict)
    """
    period = get_pay_period(period_id)
    if not period:
        return False, {"error": "Pay period not found"}

    if period.get("Status") != "OPEN":
        return False, {"error": f"Pay period is already {period.get('Status')}"}

    # Get all active employees with pay configs
    employees = get_all_employees()
    pay_configs = get_all_pay_configs()
    configured_emp_ids = {c.get("Employee_ID") for c in pay_configs}

    results = {
        "period_id": period_id,
        "processed": [],
        "skipped": [],
        "errors": [],
        "totals": {
            "gross_pay": 0,
            "federal_tax": 0,
            "state_tax": 0,
            "social_security": 0,
            "medicare": 0,
            "net_pay": 0
        }
    }

    for emp in employees:
        emp_id = emp.get("Employee_ID")

        if emp_id not in configured_emp_ids:
            results["skipped"].append({
                "employee_id": emp_id,
                "employee_name": emp.get("Employee_Name"),
                "reason": "No pay configuration"
            })
            continue

        success, payroll_data = calculate_payroll(emp_id, period_id)

        if success:
            # Save to payroll runs
            payroll_id = generate_id("PAY")

            row = {
                "Payroll_ID": payroll_id,
                "Period_ID": period_id,
                "Employee_ID": emp_id,
                "Employee_Name": payroll_data["employee_name"],
                "Regular_Hours": str(payroll_data["regular_hours"]),
                "Overtime_Hours": str(payroll_data["overtime_hours"]),
                "Holiday_Hours": str(payroll_data["holiday_hours"]),
                "PTO_Hours": str(payroll_data["pto_hours"]),
                "Sick_Hours": str(payroll_data["sick_hours"]),
                "Gross_Pay": f"{payroll_data['gross_pay']:.2f}",
                "Federal_Tax": f"{payroll_data['federal_tax']:.2f}",
                "State_Tax": f"{payroll_data['state_tax']:.2f}",
                "Social_Security": f"{payroll_data['social_security']:.2f}",
                "Medicare": f"{payroll_data['medicare']:.2f}",
                "Other_Deductions": f"{payroll_data['pretax_deductions'] + payroll_data['posttax_deductions']:.2f}",
                "Net_Pay": f"{payroll_data['net_pay']:.2f}",
                "Pay_Method": payroll_data["pay_method"],
                "Check_Number": "",
                "Status": "PENDING",
                "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Approved_By": "",
                "Approved_At": "",
                "Notes": payroll_data["notes"]
            }

            append_csv(get_payroll_runs_path(), PAYROLL_RUN_HEADERS, row)

            payroll_data["payroll_id"] = payroll_id
            results["processed"].append(payroll_data)

            # Update totals
            results["totals"]["gross_pay"] += payroll_data["gross_pay"]
            results["totals"]["federal_tax"] += payroll_data["federal_tax"]
            results["totals"]["state_tax"] += payroll_data["state_tax"]
            results["totals"]["social_security"] += payroll_data["social_security"]
            results["totals"]["medicare"] += payroll_data["medicare"]
            results["totals"]["net_pay"] += payroll_data["net_pay"]
        else:
            results["errors"].append({
                "employee_id": emp_id,
                "employee_name": emp.get("Employee_Name"),
                "error": payroll_data.get("error", "Unknown error")
            })

    # Update pay period status
    periods = read_csv(get_pay_periods_path())
    for p in periods:
        if p.get("Period_ID") == period_id:
            p["Status"] = "PROCESSED"
            p["Processed_By"] = processed_by
            p["Processed_At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_csv(get_pay_periods_path(), PAY_PERIOD_HEADERS, periods)

    # Round totals
    for key in results["totals"]:
        results["totals"][key] = round(results["totals"][key], 2)

    return True, results


def get_payroll_for_period(period_id: str) -> List[Dict]:
    """Get all payroll runs for a pay period."""
    runs = read_csv(get_payroll_runs_path())
    return [r for r in runs if r.get("Period_ID") == period_id]


def get_employee_pay_history(employee_id: str, year: int = None) -> List[Dict]:
    """Get payroll history for an employee."""
    runs = read_csv(get_payroll_runs_path(year))
    return [r for r in runs if r.get("Employee_ID") == employee_id]


def approve_payroll(period_id: str, approved_by: str) -> Tuple[bool, str]:
    """Approve all pending payroll for a period."""
    runs = read_csv(get_payroll_runs_path())
    count = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for r in runs:
        if r.get("Period_ID") == period_id and r.get("Status") == "PENDING":
            r["Status"] = "APPROVED"
            r["Approved_By"] = approved_by
            r["Approved_At"] = now
            count += 1

    write_csv(get_payroll_runs_path(), PAYROLL_RUN_HEADERS, runs)

    # Update period status
    periods = read_csv(get_pay_periods_path())
    for p in periods:
        if p.get("Period_ID") == period_id:
            p["Status"] = "APPROVED"
    write_csv(get_pay_periods_path(), PAY_PERIOD_HEADERS, periods)

    return True, f"Approved {count} payroll records"


def generate_pay_stub(payroll_id: str) -> Optional[Dict]:
    """Generate pay stub data for a payroll record."""
    runs = read_csv(get_payroll_runs_path())
    payroll = next((r for r in runs if r.get("Payroll_ID") == payroll_id), None)

    if not payroll:
        return None

    period = get_pay_period(payroll.get("Period_ID"))
    emp = get_employee(payroll.get("Employee_ID"))
    pay_config = get_employee_pay_config(payroll.get("Employee_ID"))

    return {
        "business_name": BUSINESS_NAME,
        "payroll_id": payroll_id,
        "employee": {
            "id": payroll.get("Employee_ID"),
            "name": payroll.get("Employee_Name"),
            "pay_type": pay_config.get("Pay_Type") if pay_config else "HOURLY",
            "hourly_rate": float(pay_config.get("Hourly_Rate", 0)) if pay_config else 0
        },
        "period": {
            "start_date": period.get("Start_Date") if period else "",
            "end_date": period.get("End_Date") if period else "",
            "pay_date": period.get("Pay_Date") if period else ""
        },
        "hours": {
            "regular": float(payroll.get("Regular_Hours", 0)),
            "overtime": float(payroll.get("Overtime_Hours", 0)),
            "holiday": float(payroll.get("Holiday_Hours", 0)),
            "pto": float(payroll.get("PTO_Hours", 0)),
            "sick": float(payroll.get("Sick_Hours", 0))
        },
        "earnings": {
            "gross_pay": float(payroll.get("Gross_Pay", 0))
        },
        "taxes": {
            "federal": float(payroll.get("Federal_Tax", 0)),
            "state": float(payroll.get("State_Tax", 0)),
            "social_security": float(payroll.get("Social_Security", 0)),
            "medicare": float(payroll.get("Medicare", 0))
        },
        "deductions": {
            "other": float(payroll.get("Other_Deductions", 0))
        },
        "net_pay": float(payroll.get("Net_Pay", 0)),
        "pay_method": payroll.get("Pay_Method"),
        "check_number": payroll.get("Check_Number"),
        "status": payroll.get("Status")
    }


# ==============================================================================
#                    TIME CLOCK EDIT FUNCTIONS
# ==============================================================================

def get_punches_for_date(target_date: date, employee_id: str = None) -> List[Dict]:
    """Get all punches for a specific date, optionally filtered by employee."""
    punches = read_csv(get_timeclock_path(target_date))
    if employee_id:
        punches = [p for p in punches if p.get("Employee_ID") == employee_id]
    return punches


def get_punch_by_id(punch_id: str, search_days: int = 7) -> Optional[Dict]:
    """Find a punch by ID, searching recent days."""
    today = date.today()
    for i in range(search_days):
        target = today - timedelta(days=i)
        punches = read_csv(get_timeclock_path(target))
        for p in punches:
            if p.get("Punch_ID") == punch_id:
                p["_date"] = target  # Add date reference
                return p
    return None


def edit_punch(punch_id: str, editor_id: str, editor_name: str,
               new_date: str = None, new_time: str = None, new_type: str = None,
               reason: str = "") -> Tuple[bool, str]:
    """
    Edit a time clock punch. Creates an audit trail.

    Args:
        punch_id: ID of punch to edit
        editor_id: Employee ID of person making edit
        editor_name: Name of person making edit
        new_date: New date (YYYY-MM-DD) or None to keep original
        new_time: New time (HH:MM:SS) or None to keep original
        new_type: New punch type or None to keep original
        reason: Reason for the edit (required)
    """
    if not reason:
        return False, "Reason is required for time clock edits"

    # Find the punch
    punch = get_punch_by_id(punch_id)
    if not punch:
        return False, "Punch not found"

    original_date = punch.get("Date")
    original_time = punch.get("Time")
    original_type = punch.get("Punch_Type")
    punch_file_date = punch.get("_date")

    # Determine new values
    final_date = new_date if new_date else original_date
    final_time = new_time if new_time else original_time
    final_type = new_type if new_type else original_type

    # Validate new values
    valid_types = ["CLOCK_IN", "CLOCK_OUT", "BREAK", "LUNCH", "END_BREAK", "END_LUNCH"]
    if final_type not in valid_types:
        return False, f"Invalid punch type. Must be one of: {', '.join(valid_types)}"

    try:
        datetime.strptime(final_time, "%H:%M:%S")
    except ValueError:
        return False, "Invalid time format. Use HH:MM:SS"

    try:
        datetime.strptime(final_date, "%Y-%m-%d")
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"

    # Log the edit first (audit trail)
    edit_id = generate_id("EDIT")
    edit_row = {
        "Edit_ID": edit_id,
        "Punch_ID": punch_id,
        "Edit_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Editor_ID": editor_id,
        "Editor_Name": editor_name,
        "Original_Date": original_date,
        "Original_Time": original_time,
        "Original_Type": original_type,
        "New_Date": final_date,
        "New_Time": final_time,
        "New_Type": final_type,
        "Reason": reason,
        "Approved_By": editor_id,  # Self-approved for managers
        "Approved_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    append_csv(get_timeclock_edits_path(), TIMECLOCK_EDIT_HEADERS, edit_row)
    append_audit_event("timeclock_edit", {"punch_id": edit_row.get("Punch_ID"), "editor_id": edit_row.get("Editor_ID"),
                                          "editor": edit_row.get("Editor_Name"), "from_type": edit_row.get("Original_Type"),
                                          "to_type": edit_row.get("New_Type"), "reason": edit_row.get("Reason")})

    # Update the punch record
    punches = read_csv(get_timeclock_path(punch_file_date))
    for p in punches:
        if p.get("Punch_ID") == punch_id:
            p["Date"] = final_date
            p["Time"] = final_time
            p["Punch_Type"] = final_type
            p["Notes"] = f"{p.get('Notes', '')} [EDITED {datetime.now().strftime('%Y-%m-%d')} by {editor_name}: {reason}]".strip()

    write_csv(get_timeclock_path(punch_file_date), TIMECLOCK_HEADERS, punches)

    # If date changed, we might need to move the record
    if new_date and new_date != original_date:
        # This is complex - the punch might need to move to a different file
        # For simplicity, we'll note this in the punch but keep it in original file
        pass

    # Log audit
    log_audit(editor_id, editor_name, "TIMECLOCK_EDIT", "Punch", punch_id,
              punch.get("Employee_Name", ""),
              f"{original_date} {original_time} {original_type}",
              f"{final_date} {final_time} {final_type}",
              reason)

    # Notify the employee
    create_notification(
        punch.get("Employee_ID"),
        punch.get("Employee_Name"),
        f"Your time punch on {original_date} at {original_time} was edited by {editor_name}. Reason: {reason}",
        "TIMECLOCK"
    )

    return True, f"Punch edited successfully. Edit ID: {edit_id}"


def add_punch(employee_id: str, employee_name: str, punch_date: str, punch_time: str,
              punch_type: str, added_by_id: str, added_by_name: str,
              reason: str = "") -> Tuple[bool, str]:
    """
    Add a new time clock punch (for missed punches).

    Args:
        employee_id: Employee ID
        employee_name: Employee name
        punch_date: Date of punch (YYYY-MM-DD)
        punch_time: Time of punch (HH:MM:SS)
        punch_type: Type of punch
        added_by_id: Manager ID adding the punch
        added_by_name: Manager name adding the punch
        reason: Reason for adding the punch
    """
    if not reason:
        return False, "Reason is required when adding punches"

    valid_types = ["CLOCK_IN", "CLOCK_OUT", "BREAK", "LUNCH", "END_BREAK", "END_LUNCH"]
    if punch_type not in valid_types:
        return False, f"Invalid punch type"

    try:
        target_date = datetime.strptime(punch_date, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid date format"

    try:
        datetime.strptime(punch_time, "%H:%M:%S")
    except ValueError:
        return False, "Invalid time format"

    punch_id = generate_id("P")

    row = {
        "Punch_ID": punch_id,
        "Date": punch_date,
        "Time": punch_time,
        "Employee_ID": employee_id,
        "Employee_Name": employee_name,
        "Punch_Type": punch_type,
        "Hours_Worked_Today": "0",  # Will be recalculated
        "Overtime_Hours": "0",
        "Notes": f"[ADDED by {added_by_name} on {date.today()}: {reason}]"
    }

    append_csv(get_timeclock_path(target_date), TIMECLOCK_HEADERS, row)

    # Log edit for audit trail
    edit_id = generate_id("EDIT")
    edit_row = {
        "Edit_ID": edit_id,
        "Punch_ID": punch_id,
        "Edit_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Editor_ID": added_by_id,
        "Editor_Name": added_by_name,
        "Original_Date": "",
        "Original_Time": "",
        "Original_Type": "",
        "New_Date": punch_date,
        "New_Time": punch_time,
        "New_Type": punch_type,
        "Reason": f"ADDED: {reason}",
        "Approved_By": added_by_id,
        "Approved_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    append_csv(get_timeclock_edits_path(), TIMECLOCK_EDIT_HEADERS, edit_row)
    append_audit_event("timeclock_edit", {"punch_id": edit_row.get("Punch_ID"), "editor_id": edit_row.get("Editor_ID"),
                                          "editor": edit_row.get("Editor_Name"), "from_type": edit_row.get("Original_Type"),
                                          "to_type": edit_row.get("New_Type"), "reason": edit_row.get("Reason")})

    # Log audit
    log_audit(added_by_id, added_by_name, "TIMECLOCK_ADD", "Punch", punch_id,
              employee_name, "", f"{punch_date} {punch_time} {punch_type}", reason)

    # Notify employee
    create_notification(employee_id, employee_name,
        f"A time punch was added for you on {punch_date} at {punch_time} ({punch_type}) by {added_by_name}. Reason: {reason}",
        "TIMECLOCK")

    return True, f"Punch added successfully. Punch ID: {punch_id}"


def delete_punch(punch_id: str, deleted_by_id: str, deleted_by_name: str,
                 reason: str = "") -> Tuple[bool, str]:
    """
    Delete a time clock punch (soft delete - marks as deleted).
    """
    if not reason:
        return False, "Reason is required for deletions"

    punch = get_punch_by_id(punch_id)
    if not punch:
        return False, "Punch not found"

    punch_file_date = punch.get("_date")

    # Log the deletion
    edit_id = generate_id("EDIT")
    edit_row = {
        "Edit_ID": edit_id,
        "Punch_ID": punch_id,
        "Edit_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Editor_ID": deleted_by_id,
        "Editor_Name": deleted_by_name,
        "Original_Date": punch.get("Date"),
        "Original_Time": punch.get("Time"),
        "Original_Type": punch.get("Punch_Type"),
        "New_Date": "DELETED",
        "New_Time": "DELETED",
        "New_Type": "DELETED",
        "Reason": f"DELETED: {reason}",
        "Approved_By": deleted_by_id,
        "Approved_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    append_csv(get_timeclock_edits_path(), TIMECLOCK_EDIT_HEADERS, edit_row)
    append_audit_event("timeclock_edit", {"punch_id": edit_row.get("Punch_ID"), "editor_id": edit_row.get("Editor_ID"),
                                          "editor": edit_row.get("Editor_Name"), "from_type": edit_row.get("Original_Type"),
                                          "to_type": edit_row.get("New_Type"), "reason": edit_row.get("Reason")})

    # Mark punch as deleted (don't actually remove)
    punches = read_csv(get_timeclock_path(punch_file_date))
    for p in punches:
        if p.get("Punch_ID") == punch_id:
            p["Punch_Type"] = f"DELETED_{p['Punch_Type']}"
            p["Notes"] = f"[DELETED by {deleted_by_name}: {reason}] {p.get('Notes', '')}".strip()

    write_csv(get_timeclock_path(punch_file_date), TIMECLOCK_HEADERS, punches)

    # Log and notify
    log_audit(deleted_by_id, deleted_by_name, "TIMECLOCK_DELETE", "Punch", punch_id,
              punch.get("Employee_Name", ""),
              f"{punch.get('Date')} {punch.get('Time')} {punch.get('Punch_Type')}",
              "DELETED", reason)

    create_notification(punch.get("Employee_ID"), punch.get("Employee_Name"),
        f"Your time punch on {punch.get('Date')} at {punch.get('Time')} was deleted by {deleted_by_name}. Reason: {reason}",
        "TIMECLOCK")

    return True, "Punch deleted successfully"


def get_timeclock_edit_history(employee_id: str = None, days: int = 30) -> List[Dict]:
    """Get time clock edit history."""
    edits = read_csv(get_timeclock_edits_path())

    if employee_id:
        # Filter by employee (need to look up punch records)
        filtered = []
        for edit in edits:
            punch = get_punch_by_id(edit.get("Punch_ID"))
            if punch and punch.get("Employee_ID") == employee_id:
                filtered.append(edit)
        edits = filtered

    # Filter by date range
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    edits = [e for e in edits if e.get("Edit_Date", "") >= cutoff]

    return sorted(edits, key=lambda x: x.get("Edit_Date", ""), reverse=True)


# ==============================================================================
#                    ENHANCED TASK MANAGEMENT METRICS
# ==============================================================================

def get_task_completion_stats(for_date: date = None, employee_id: str = None) -> dict:
    """
    Get task completion statistics.
    Returns dict with: total, completed, in_progress, pending, skipped, completion_rate
    """
    assignments = []

    if TASK_ASSIGNMENTS_PATH.exists():
        with open(TASK_ASSIGNMENTS_PATH, 'r', newline='') as f:
            for row in csv.DictReader(f):
                if for_date and row.get('Due_Date') != for_date.isoformat():
                    continue
                if employee_id and row.get('Employee_ID') != employee_id:
                    continue
                assignments.append(row)

    total = len(assignments)
    completed = len([a for a in assignments if a.get('Status') == 'COMPLETE'])
    in_progress = len([a for a in assignments if a.get('Status') == 'IN_PROGRESS'])
    acknowledged = len([a for a in assignments if a.get('Status') == 'ACKNOWLEDGED'])
    pending = len([a for a in assignments if a.get('Status') == 'ASSIGNED'])
    skipped = len([a for a in assignments if a.get('Status') == 'SKIPPED'])

    # Calculate overdue
    today = date.today().isoformat()
    overdue = len([a for a in assignments
                   if a.get('Status') not in ('COMPLETE', 'SKIPPED')
                   and a.get('Due_Date', '') < today])

    completion_rate = (completed / total * 100) if total > 0 else 0

    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'acknowledged': acknowledged,
        'pending': pending,
        'skipped': skipped,
        'overdue': overdue,
        'completion_rate': round(completion_rate, 1)
    }


def calculate_employee_task_metrics(employee_id: str, start_date: date, end_date: date) -> Dict:
    """
    Calculate comprehensive task metrics for an employee over a period.
    """
    assignments = []

    if TASK_ASSIGNMENTS_PATH.exists():
        with open(TASK_ASSIGNMENTS_PATH, 'r', newline='') as f:
            for row in csv.DictReader(f):
                if row.get('Employee_ID') != employee_id:
                    continue
                due_date = row.get('Due_Date', '')
                if due_date and start_date.isoformat() <= due_date <= end_date.isoformat():
                    assignments.append(row)

    total = len(assignments)
    completed = [a for a in assignments if a.get('Status') == 'COMPLETE']
    skipped = [a for a in assignments if a.get('Status') == 'SKIPPED']

    # Calculate overdue
    today = date.today().isoformat()
    overdue = [a for a in assignments
               if a.get('Status') not in ('COMPLETE', 'SKIPPED')
               and a.get('Due_Date', '') < today]

    # Calculate on-time completion rate
    on_time = 0
    completion_times = []

    for task in completed:
        completed_at = task.get('Completed_At', '')
        due_date = task.get('Due_Date', '')

        if completed_at and due_date:
            try:
                completed_dt = datetime.fromisoformat(completed_at)
                due_dt = datetime.strptime(due_date, "%Y-%m-%d")
                due_dt = due_dt.replace(hour=23, minute=59, second=59)

                if completed_dt <= due_dt:
                    on_time += 1
            except:
                pass

        # Calculate completion time
        started_at = task.get('Started_At', '')
        if started_at and completed_at:
            try:
                start_dt = datetime.fromisoformat(started_at)
                end_dt = datetime.fromisoformat(completed_at)
                minutes = (end_dt - start_dt).total_seconds() / 60
                if 0 < minutes < 480:  # Sanity check: less than 8 hours
                    completion_times.append(minutes)
            except:
                pass

    on_time_rate = (on_time / len(completed) * 100) if completed else 0
    avg_completion = sum(completion_times) / len(completion_times) if completion_times else 0

    # Calculate quality score average
    quality_scores = []
    for task in completed:
        score = task.get('Quality_Score', '')
        if score:
            try:
                quality_scores.append(float(score))
            except:
                pass

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

    return {
        "employee_id": employee_id,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "tasks_assigned": total,
        "tasks_completed": len(completed),
        "tasks_skipped": len(skipped),
        "tasks_overdue": len(overdue),
        "completion_rate": round(len(completed) / total * 100, 1) if total else 0,
        "on_time_rate": round(on_time_rate, 1),
        "avg_completion_minutes": round(avg_completion, 1),
        "avg_quality_score": round(avg_quality, 2),
        "assignments": assignments
    }


def generate_task_performance_report(start_date: date, end_date: date) -> Dict:
    """
    Generate a performance report for all employees over a period.
    """
    employees = get_all_employees()

    report = {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": {
            "total_assigned": 0,
            "total_completed": 0,
            "total_skipped": 0,
            "total_overdue": 0,
            "avg_completion_rate": 0,
            "avg_on_time_rate": 0
        },
        "employees": [],
        "top_performers": [],
        "needs_improvement": []
    }

    completion_rates = []
    on_time_rates = []

    for emp in employees:
        emp_id = emp.get("Employee_ID")
        metrics = calculate_employee_task_metrics(emp_id, start_date, end_date)

        if metrics["tasks_assigned"] > 0:
            emp_data = {
                "employee_id": emp_id,
                "employee_name": emp.get("Employee_Name"),
                "tasks_assigned": metrics["tasks_assigned"],
                "tasks_completed": metrics["tasks_completed"],
                "tasks_skipped": metrics["tasks_skipped"],
                "tasks_overdue": metrics["tasks_overdue"],
                "completion_rate": metrics["completion_rate"],
                "on_time_rate": metrics["on_time_rate"],
                "avg_completion_minutes": metrics["avg_completion_minutes"],
                "avg_quality_score": metrics["avg_quality_score"]
            }
            report["employees"].append(emp_data)

            report["summary"]["total_assigned"] += metrics["tasks_assigned"]
            report["summary"]["total_completed"] += metrics["tasks_completed"]
            report["summary"]["total_skipped"] += metrics["tasks_skipped"]
            report["summary"]["total_overdue"] += metrics["tasks_overdue"]

            completion_rates.append(metrics["completion_rate"])
            on_time_rates.append(metrics["on_time_rate"])

    # Calculate averages
    if completion_rates:
        report["summary"]["avg_completion_rate"] = round(sum(completion_rates) / len(completion_rates), 1)
    if on_time_rates:
        report["summary"]["avg_on_time_rate"] = round(sum(on_time_rates) / len(on_time_rates), 1)

    # Sort employees by performance
    sorted_employees = sorted(report["employees"],
                             key=lambda x: (x["completion_rate"], x["on_time_rate"]),
                             reverse=True)

    # Top performers (90%+ completion rate with tasks)
    report["top_performers"] = [e for e in sorted_employees
                                if e["completion_rate"] >= 90 and e["tasks_assigned"] >= 5][:5]

    # Needs improvement (under 70% completion or many overdue)
    report["needs_improvement"] = [e for e in sorted_employees
                                   if e["completion_rate"] < 70 or e["tasks_overdue"] >= 3]

    return report


def rate_task_quality(assignment_id: str, quality_score: float, rated_by: str,
                      notes: str = "") -> Tuple[bool, str]:
    """
    Rate the quality of a completed task.

    Args:
        assignment_id: ID of the task assignment
        quality_score: Score from 1-5
        rated_by: Employee ID of the rater (usually manager)
        notes: Optional notes about the rating
    """
    if not 1 <= quality_score <= 5:
        return False, "Quality score must be between 1 and 5"

    assignments = []
    found = False

    if TASK_ASSIGNMENTS_PATH.exists():
        with open(TASK_ASSIGNMENTS_PATH, 'r', newline='') as f:
            for row in csv.DictReader(f):
                if row.get('Assignment_ID') == assignment_id:
                    if row.get('Status') != 'COMPLETE':
                        return False, "Can only rate completed tasks"
                    row['Quality_Score'] = str(quality_score)
                    if notes:
                        existing = row.get('Notes_From_Employee', '')
                        row['Notes_From_Employee'] = f"{existing}\n[Quality rated {quality_score}/5 by {rated_by}: {notes}]".strip()
                    found = True
                assignments.append(row)

    if not found:
        return False, "Assignment not found"

    with open(TASK_ASSIGNMENTS_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=TASK_ASSIGNMENTS_HEADERS)
        writer.writeheader()
        writer.writerows(assignments)

    # Log the event
    log_task_event(assignment_id, rated_by, "QUALITY_RATED", f"Score: {quality_score}/5. {notes}")

    return True, f"Task rated {quality_score}/5"


def save_task_metrics_snapshot(employee_id: str, start_date: date, end_date: date) -> str:
    """
    Save a snapshot of task metrics for an employee.
    Useful for historical tracking and reviews.
    """
    metrics = calculate_employee_task_metrics(employee_id, start_date, end_date)

    metric_id = generate_id("TM")
    row = {
        "Metric_ID": metric_id,
        "Employee_ID": employee_id,
        "Period_Start": start_date.isoformat(),
        "Period_End": end_date.isoformat(),
        "Tasks_Assigned": str(metrics["tasks_assigned"]),
        "Tasks_Completed": str(metrics["tasks_completed"]),
        "Tasks_Skipped": str(metrics["tasks_skipped"]),
        "Tasks_Overdue": str(metrics["tasks_overdue"]),
        "Avg_Completion_Minutes": str(metrics["avg_completion_minutes"]),
        "On_Time_Rate": str(metrics["on_time_rate"]),
        "Quality_Score_Avg": str(metrics["avg_quality_score"]),
        "Calculated_At": datetime.now().isoformat()
    }

    append_csv(get_task_metrics_path(), TASK_METRICS_HEADERS, row)
    return metric_id


def get_employee_metrics_history(employee_id: str) -> List[Dict]:
    """Get historical task metrics for an employee."""
    metrics = read_csv(get_task_metrics_path())
    return [m for m in metrics if m.get("Employee_ID") == employee_id]




# ==============================================================================
#                              AI / N8N HELPERS
# ==============================================================================

def get_business_snapshot():
    """Get a snapshot of business data for AI analysis."""
    today = date.today()

    # Sales / daily summary
    summary = generate_daily_summary(today)

    # Inventory data
    low_stock = check_low_stock()
    valuation = get_inventory_valuation()

    # Full inventory items with on-hand quantities
    items = []
    for item in get_all_items():
        sku = item.get("SKU", "")
        items.append({
            "sku": sku,
            "name": item.get("Item_Name", ""),
            "category": item.get("Category", ""),
            "subcategory": item.get("Subcategory", ""),
            "default_price": float(item.get("Default_Price", 0) or 0),
            "on_hand": get_stock_on_hand(sku),
            "reorder_point": int(item.get("Reorder_Point", 0) or 0),
            "status": item.get("Status", ""),
        })

    # Time clock – who is actually clocked in
    clocked_in = get_clocked_in_employees()

    # Task assignments for today
    todays_tasks = get_task_assignments_for_date(today)

    return {
        "business_name": BUSINESS_NAME,
        "version": VERSION,
        "tax_rate": TAX_RATE,

        "today": {
            "date": summary.get("date"),
            "revenue": summary.get("total_revenue", 0),
            "transactions": summary.get("total_transactions", 0),
            "items_sold": summary.get("total_items", 0),
            "top_seller": summary.get("top_seller_name", ""),
        },

        "inventory": {
            "total_items": len(items),
            "low_stock_count": len(low_stock),
            "low_stock_items": [
                {
                    "sku": i["sku"],
                    "name": i["item_name"],
                    "on_hand": i["on_hand"],
                    "reorder_point": i["reorder_point"],
                    "status": i["status"],
                }
                for i in low_stock[:50]
            ],
            # NEW: full items list so the bot can name them
            "items": items,
            "valuation": valuation,
        },

        "employees": {
            # Total active employees in the directory
            "active_count": len(get_all_employees()),
            # NEW: only people actually clocked in
            "clocked_in_count": len(clocked_in),
            "clocked_in": clocked_in,
        },

        # NEW: tasks visible to the AI
        "tasks": {
            "date": today.isoformat(),
            "total_assignments": len(todays_tasks),
            "today_assignments": todays_tasks,
        },
    }


def get_reorder_recommendations():
    low_stock = check_low_stock()
    recommendations = []
    for item in low_stock:
        full_item = get_item(item["sku"])
        if full_item:
            recommendations.append({
                "sku": item["sku"],
                "item_name": item["item_name"],
                "category": item["category"],
                "on_hand": item["on_hand"],
                "reorder_point": item["reorder_point"],
                "avg_cost": get_average_cost(item["sku"]),
                "default_price": float(full_item.get("Default_Price", 0)),
                "status": item["status"],
            })
    return recommendations
