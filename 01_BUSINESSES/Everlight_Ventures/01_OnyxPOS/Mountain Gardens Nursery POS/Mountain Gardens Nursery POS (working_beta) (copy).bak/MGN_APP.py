#!/usr/bin/env python3
"""
Mountain Gardens POS - Flask Web Application v8.0
==================================================
Complete rebuild with proper code ordering and all features.

Features:
- Sales Terminal with inventory picker
- Time Clock + Break tracking
- Task Management + Automations
- Payroll Management
- Inventory + Invoice Import
- Reports (Daily, COGS, Net Profit)
- AI Assistant
- Role-based access control
"""

import os
import sys
import glob
import re
import json
import csv
import traceback
import tempfile
from zoneinfo import ZoneInfo
from pathlib import Path
from collections import defaultdict
from datetime import datetime, date, timedelta, time as dtime
from functools import wraps
from io import BytesIO

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort, send_file
)
from werkzeug.utils import secure_filename

# ==============================================================================
#                     FLASK APP SETUP
# ==============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mountain-gardens-pos-2024-dev-key')

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

# ==============================================================================
#                     AUTHENTICATION DECORATORS (MUST BE BEFORE ROUTES!)
# ==============================================================================

@app.context_processor
def inject_unread_counts():
    try:
        emp_id = str(session.get("employee_id", ""))
    except Exception:
        return {}

    if not emp_id:
        return {}

    notifs = get_all_notifications(emp_id, limit=500)

    def is_unread(n):
        return str(n.get("Read", n.get("Is_Read", "N"))).strip().upper() not in ("Y", "YES", "TRUE", "1")

    unread_task = sum(1 for n in notifs if (n.get("Type") == "TASK") and is_unread(n))
    unread_timeoff = sum(1 for n in notifs if (n.get("Type") == "TIMEOFF") and is_unread(n))

    return {
        "unread_task_count": unread_task,
        "unread_timeoff_count": unread_timeoff,
    }



def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'employee_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def manager_required(f):
    """Decorator to require manager role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'employee_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') not in ('Manager', 'Owner', 'Admin'):
            flash('Manager access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ==============================================================================
#                     IMPORT POS CORE
# ==============================================================================

from POS_CORE import (
    # App meta
    BUSINESS_NAME, VERSION,
    MAIN_CATEGORIES, ANIMAL_SUBCATEGORIES, PRODUCT_SUBCATEGORIES, PLANT_SUBCATEGORIES,
    ROLES,
    
    # Data helpers
    read_csv, write_csv, append_csv, ensure_csv, get_lots_path, get_ledger_path,
    ITEM_HEADERS, LEDGER_HEADERS, create_lot, get_timeoff_path,
    get_timeclock_path, build_receipt_payload, log_customer_receipt,
    
    # Employees / auth
    get_all_employees, get_employee, create_employee,
    authenticate, reset_pin, deactivate_employee, reactivate_employee,

    #get task management
    get_or_create_task_template, get_task_assignment, get_task_events,
    
    # Audit / notifications
    get_audit_log, log_audit,
    create_notification, get_unread_notifications, get_all_notifications,
    mark_notification_read, mark_all_notifications_read,
    
    # Inventory
    get_all_items, get_item, get_items_path, create_item, search_items, generate_sku,
    get_lots_for_sku, get_stock_on_hand, get_average_cost, create_lot,
    check_low_stock, get_inventory_valuation,
    
    # Pricing / sales
    get_pricing_rules, create_pricing_rule,
    record_sale, get_transactions_for_date, get_sales_for_date,
    
    # Timeclock
    get_employee_status, clock_in, clock_out, start_break, end_break,
    get_punches_for_date, get_punch_by_id, edit_punch, add_punch, delete_punch,
    get_timeclock_edit_history,
    
    # Time off
    request_time_off, get_time_off_requests, get_pending_requests, approve_time_off,
    
    # Tasks
    get_all_tasks, create_task, assign_task,get_task,
    get_task_assignments_for_date, get_tasks_for_employee, update_task_status,
    
    # Reports
    generate_daily_summary, generate_employee_dashboard,
    
    # Payroll
    get_all_pay_configs, get_employee_pay_config, setup_employee_pay,
    get_pay_periods, create_pay_period, get_pay_period,
    calculate_hours_for_period, calculate_payroll,
    run_payroll, get_payroll_for_period, approve_payroll,
    generate_pay_stub, get_employee_pay_history,
)

# Try optional imports
try:
    from invoice_importer import import_invoice_csv
    HAS_INVOICE_IMPORTER = True
except ImportError:
    HAS_INVOICE_IMPORTER = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from openai import OpenAI
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
    openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except ImportError:
    openai_client = None

# ==============================================================================
#                     CONFIGURATION
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent
N8N_BASE_URL = os.environ.get('N8N_URL', 'http://localhost:5678')

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = str(SCRIPT_DIR)  # <— fixes NameError everywhere that uses DATA_DIR
# ==============================================================================
#                     HELPER FUNCTIONS
# ==============================================================================

def make_change_breakdown(amount: float):
    """Given a change amount in dollars, return breakdown in US currency."""
    remaining = int(round(amount * 100))
    denoms = [
        ("$100", 10000), ("$50", 5000), ("$20", 2000), ("$10", 1000),
        ("$5", 500), ("$1", 100), ("25¢", 25), ("10¢", 10), ("5¢", 5), ("1¢", 1),
    ]
    breakdown = []
    for label, value in denoms:
        if remaining <= 0:
            break
        count, remaining = divmod(remaining, value)
        if count:
            breakdown.append({"label": label, "count": int(count)})
    return breakdown


# ==============================================================================
#                     CONTEXT PROCESSORS
# ==============================================================================

@app.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    notif_count = 0
    my_tasks_count = 0
    
    if 'employee_id' in session:
        notifs = get_unread_notifications(session['employee_id'])
        notif_count = len(notifs) if notifs else 0
        
        try:
            tasks = get_tasks_for_employee(session['employee_id'], date.today())
            my_tasks_count = len([t for t in tasks if t.get('Status') not in ('COMPLETE', 'SKIPPED')])
        except:
            pass
    
    return {
        'business_name': BUSINESS_NAME,
        'current_year': datetime.now().year,
        'current_time': datetime.now(),
        'version': VERSION,
        'notification_count': notif_count,
        'my_tasks_count': my_tasks_count,
        'now': datetime.now(),
    }


@app.context_processor
def template_utils():
    """Helper functions for templates."""
    def has_endpoint(name: str) -> bool:
        return name in app.view_functions
    return dict(has_endpoint=has_endpoint)


# ==============================================================================
#                     ERROR HANDLERS
# ==============================================================================

@app.errorhandler(500)
def server_error(e):
    error_info = {
        'error': str(e),
        'traceback': traceback.format_exc(),
        'route': request.path,
        'timestamp': datetime.now().isoformat()
    }
    session['last_error'] = error_info
    return render_template('errors/500.html', error_info=error_info), 500


@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


# ==============================================================================
#                     AUTH ROUTES
# ==============================================================================

@app.route('/')
def index():
    if 'employee_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_id = request.form.get('employee_id', '').strip()
        pin = request.form.get('pin', '').strip()
        
        success, msg, emp = authenticate(emp_id, pin)
        
        if success:
            session['employee_id'] = emp_id
            session['employee_name'] = emp['Employee_Name']
            session['role'] = emp.get('Role', 'Cashier')
            
            notifs = get_unread_notifications(emp_id)
            if notifs:
                flash(f'You have {len(notifs)} unread notification(s)', 'info')
            
            return redirect(url_for('dashboard'))
        else:
            flash(msg, 'error')
    
    employees = get_all_employees()
    return render_template('login.html', employees=employees)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))






@app.route("/inventory/invoice-import/pdf", methods=["POST"])





def _read_csv_dicts(path):
    if not os.path.exists(path):
        return [], []
    with open(path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), (reader.fieldnames or [])

def _write_csv_dicts(path, rows, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def _append_csv_dict(path, row, fallback_headers):
    rows, headers = _read_csv_dicts(path)
    if not headers:
        headers = fallback_headers[:]
    # ensure all headers exist on the row
    out = {h: row.get(h, "") for h in headers}
    rows.append(out)
    _write_csv_dicts(path, rows, headers)

def _now_stamp():
    # matches your Ledger schema "Timestamp"
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _safe_float(v, default=0.0):
    try:
        return float(str(v).strip())
    except Exception:
        return default

def _safe_int(v, default=0):
    try:
        return int(float(str(v).strip()))
    except Exception:
        return default


@app.route("/inventory/invoice-import", methods=["POST"])
def inventory_invoice_import_post():
    # === 1) If CSV file upload exists, keep your existing importer ===
    if "invoice_csv" in request.files and request.files["invoice_csv"] and request.files["invoice_csv"].filename:
        f = request.files["invoice_csv"]
        if not f.filename.lower().endswith(".csv"):
            flash("Please upload a .csv file for invoice import.", "error")
            return redirect(url_for("receive_stock"))

        # ✅ your existing function (already in your app)
        try:
            tmp_path = os.path.join("uploads", f"invoice_{uuid4().hex}.csv")
            os.makedirs("uploads", exist_ok=True)
            f.save(tmp_path)

            results = import_invoice_csv(tmp_path)  # <-- existing in your code
            flash(f"Invoice imported: {results.get('lots_created', 0)} lots added.", "success")
            return redirect(url_for("inventory_view"))
        except Exception as e:
            flash(f"Invoice CSV import failed: {e}", "error")
            return redirect(url_for("receive_stock"))

    # === 2) Manual form import ===
    # Expected manual form fields (match your receive.html inputs):
    # sku (optional), item_name, category, default_price, unit_cost, qty_received, supplier, invoice_no, received_date, notes, taxable
    sku          = (request.form.get("sku") or "").strip()
    item_name    = (request.form.get("item_name") or "").strip()
    category     = (request.form.get("category") or "General").strip()
    default_price= _safe_float(request.form.get("default_price"), 0.0)
    unit_cost    = _safe_float(request.form.get("unit_cost"), 0.0)
    qty_received = _safe_int(request.form.get("qty_received"), 0)
    supplier     = (request.form.get("supplier") or "").strip()
    invoice_no   = (request.form.get("invoice_no") or "").strip()
    received_date= (request.form.get("received_date") or "").strip()
    notes        = (request.form.get("notes") or "").strip()
    taxable_raw  = (request.form.get("taxable") or "true").strip().lower()
    taxable      = "True" if taxable_raw in ("1", "true", "yes", "on") else "False"

    if qty_received <= 0:
        flash("Qty received must be 1 or more.", "error")
        return redirect(url_for("receive_stock"))

    if not received_date:
        received_date = datetime.now().strftime("%Y-%m-%d")

    # Inventory CSV paths (from your Tree.txt)
    items_path  = os.path.join("Inventory", "Items.csv")
    lots_path   = os.path.join("Inventory", "Lots.csv")
    ledger_path = os.path.join("Inventory", "Ledger.csv")

    # === Ensure SKU exists; if not provided, generate one ===
    # Uses your POS_CORE helper if available, else fallback.
    if not sku:
        try:
            sku = generate_sku(category=category)  # POS_CORE function in your project
        except Exception:
            sku = f"SKU-{uuid4().hex[:8].upper()}"

    # === Create or update the item in Items.csv ===
    items_rows, item_headers = _read_csv_dicts(items_path)
    if not item_headers:
        # fallback header set (won't break if your real file has more/less columns)
        item_headers = [
            "SKU","Item_Name","Category","Subcategory","Product_Name",
            "Default_Unit","Default_Price","Taxable","Reorder_Point",
            "Date_Added","Last_Updated","Status","Notes","Retail_Markup",
            "Retail_Price","Unit_Cost","Unit_Price",
            "Last_Invoice_No","Last_Vendor","Last_Received_Date"
        ]

    now_date = datetime.now().strftime("%Y-%m-%d")
    found = False
    for r in items_rows:
        if (r.get("SKU") or "").strip() == sku:
            # update only what we actually got from the manual form
            if item_name: r["Item_Name"] = item_name
            if category:  r["Category"]  = category
            if default_price > 0: r["Default_Price"] = str(default_price)
            if unit_cost > 0:     r["Unit_Cost"]     = str(unit_cost)
            r["Taxable"] = taxable
            r["Last_Updated"] = now_date
            r["Last_Invoice_No"] = invoice_no
            r["Last_Vendor"] = supplier
            r["Last_Received_Date"] = received_date
            if notes:
                r["Notes"] = (r.get("Notes","") + " | " + notes).strip(" |")
            found = True
            break

    if not found:
        new_row = {h: "" for h in item_headers}
        new_row["SKU"] = sku
        new_row["Item_Name"] = item_name or sku
        new_row["Category"] = category or "General"
        new_row["Default_Price"] = str(default_price) if default_price else "0"
        new_row["Unit_Cost"] = str(unit_cost) if unit_cost else "0"
        new_row["Taxable"] = taxable
        new_row["Date_Added"] = now_date
        new_row["Last_Updated"] = now_date
        new_row["Status"] = "Active"
        new_row["Last_Invoice_No"] = invoice_no
        new_row["Last_Vendor"] = supplier
        new_row["Last_Received_Date"] = received_date
        new_row["Notes"] = notes
        items_rows.append(new_row)

    _write_csv_dicts(items_path, items_rows, item_headers)

    # === Append a new Lot to Lots.csv (THIS is what Sales on-hand reads) ===
    lot_id = f"LOT-{uuid4().hex[:10].upper()}"
    lot_row = {
        "Lot_ID": lot_id,
        "SKU": sku,
        "Invoice_No": invoice_no,
        "Vendor": supplier,
        "Date_Received": received_date,
        "Qty_Received": str(qty_received),
        "Qty_Remaining": str(qty_received),
        "Unit_Cost": str(unit_cost),
        "Notes": notes
    }
    lot_headers = ["Lot_ID","SKU","Invoice_No","Vendor","Date_Received","Qty_Received","Qty_Remaining","Unit_Cost","Notes"]
    _append_csv_dict(lots_path, lot_row, lot_headers)

    # === Append Ledger receive event ===
    ledger_row = {
        "Entry_ID": f"LED-{uuid4().hex[:10].upper()}",
        "Timestamp": _now_stamp(),
        "SKU": sku,
        "Lot_ID": lot_id,
        "Delta_Qty": str(qty_received),
        "Reason": "RECEIVE",
        "Ref_Transaction_ID": invoice_no,
        "Employee_ID": "",
        "Notes": notes
    }
    ledger_headers = ["Entry_ID","Timestamp","SKU","Lot_ID","Delta_Qty","Reason","Ref_Transaction_ID","Employee_ID","Notes"]
    _append_csv_dict(ledger_path, ledger_row, ledger_headers)

    flash(f"Received {qty_received} × {sku} into {lot_id}. Sales on-hand should now update.", "success")
    return redirect(url_for("inventory_view"))

# ==============================================================================
#                     DASHBOARD
# ==============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    summary = generate_daily_summary()
    low_stock = check_low_stock()[:5]
    status = get_employee_status(session['employee_id'])
    my_tasks = get_tasks_for_employee(session['employee_id'], date.today())
    
    # Count employees clocked in
    employees_clocked_in = 0
    try:
        punches = read_csv(get_timeclock_path())
        clocked_in_ids = set()
        for p in punches:
            if p.get('Punch_Type') == 'CLOCK_IN':
                clocked_in_ids.add(p.get('Employee_ID'))
            elif p.get('Punch_Type') == 'CLOCK_OUT':
                clocked_in_ids.discard(p.get('Employee_ID'))
        employees_clocked_in = len(clocked_in_ids)
    except:
        pass
    emp_id = session.get("employee_id", "")
    clock_status = get_employee_status(emp_id) if emp_id else {"status": "NOT_CLOCKED_IN", "hours_today": 0, "overtime": 0}

    return render_template('dashboard.html', clock_status=clock_status,
        summary=summary,
        low_stock=low_stock,
        low_stock_items=low_stock,
        low_stock_count=len(check_low_stock()),
        status=status,
        my_tasks=my_tasks,
        today_sales=summary.get('total_revenue', 0),
        transaction_count=summary.get('transaction_count', 0),
        employees_clocked_in=employees_clocked_in
    )

# -----------------------------
# Dashboard helpers
# -----------------------------
def _to_float(x):
    try:
        return float(str(x).replace("$", "").replace(",", "").strip() or 0)
    except Exception:
        return 0.0

def _find_daily_file(root_dir, date_str, suffix):
    # suffix examples: "_SalesLog.csv", "_Transactions.csv"
    pattern = os.path.join(root_dir, "**", f"{date_str}*{suffix}")
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        return None
    matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return matches[0]


# -----------------------------
# Dashboard: Today's Sales (from Sales_Logs tree)
# -----------------------------
@app.route("/api/dashboard/sales")
@login_required
def api_dashboard_sales():
    from datetime import date as _date
    from pathlib import Path as _Path

    date_str = request.args.get("date") or _date.today().isoformat()

    def _to_float(x):
        s = str(x or "").strip().replace("$", "").replace(",", "")
        try:
            return float(s) if s else 0.0
        except Exception:
            return 0.0

    def _find_daily_file(base_dir: _Path, day: str, suffix: str):
        if not base_dir.exists():
            return None
        matches = list(base_dir.glob(f"**/{day}*{suffix}"))
        return matches[0] if matches else None

    tx_file = _find_daily_file(_Path("Transaction_Logs"), date_str, "_Transactions.csv")
    tx_rows = read_csv(tx_file) if tx_file else []

    total_revenue = 0.0
    cash_sales_count = 0
    card_sales_count = 0

    transactions = []
    for r in tx_rows:
        pm = (r.get("Payment_Method") or "").upper()
        grand = _to_float(r.get("Grand_Total"))

        total_revenue += grand
        if "CASH" in pm:
            cash_sales_count += 1
        elif pm:
            card_sales_count += 1

        transactions.append({
            "transaction_id": r.get("Transaction_ID", ""),
            "time": r.get("Time", ""),
            "items": r.get("Items_Count", ""),
            "payment_method": r.get("Payment_Method", ""),
            "total": grand,
        })

    return jsonify({
        "success": True,
        # ✅ keys your modal expects (most common)
        "total_revenue": total_revenue,
        "transactions_count": len(transactions),
        "cash_sales_count": cash_sales_count,
        "card_sales_count": card_sales_count,
        "transactions": transactions[::-1][-50:],  # last 50, newest last -> reverse if you want newest first

        # ✅ backward-compat (in case any older JS uses these)
        "total_sales": total_revenue,
        "cash_count": cash_sales_count,
        "card_count": card_sales_count,
    })

# -----------------------------
# Dashboard: Today's Transactions (from Transaction_Logs tree)
# -----------------------------
@app.route('/api/dashboard/transactions')
def api_dashboard_transactions():
    try:
        today_str = date.today().strftime("%Y-%m-%d")
        tx_root = os.path.join(BASE_DIR, "Transaction_Logs")
        tx_file = _find_daily_file(tx_root, today_str, "_Transactions.csv")

        if not tx_file or not os.path.exists(tx_file):
            return jsonify({"success": True, "count": 0, "transactions": []})

        rows = []
        with open(tx_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        # newest first if you have a Time column
        if rows and ("Time" in rows[0] or "time" in rows[0]):
            rows.sort(key=lambda r: (r.get("Time") or r.get("time") or ""), reverse=True)

        return jsonify({"success": True, "count": len(rows), "transactions": rows[:100]})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.get("/sales/receipt/<transaction_id>")
@login_required
def legacy_receipt_redirect(transaction_id):
    return redirect(url_for("sales"))




# ============================================
# API: Staff Working Now
# ============================================
@app.route('/api/dashboard/staff')
def api_dashboard_staff():
    """Get currently clocked-in staff from Time_Clock CSV"""
    try:
        today_str = date.today().strftime('%Y-%m-%d')
        staff = []
        total_hours = 0

        # Look for time clock file
        timeclock_dir = os.path.join(DATA_DIR, 'Time_Clock')

        possible_files = [
            os.path.join(timeclock_dir, f'timeclock_{today_str}.csv'),
            os.path.join(timeclock_dir, f'TimeLog_{today_str}.csv'),
            os.path.join(timeclock_dir, f'{today_str}.csv'),
            os.path.join(timeclock_dir, 'time_clock.csv'),
            os.path.join(timeclock_dir, 'TimeLog.csv'),
            os.path.join(timeclock_dir, 'timeclock.csv'),
        ]

        timeclock_file = None
        for f in possible_files:
            if os.path.exists(f):
                timeclock_file = f
                break

        # Track who is currently clocked in (no clock out time)
        clocked_in = {}

        if timeclock_file:
            with open(timeclock_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_date = row.get('Date', row.get('date', ''))

                    # Only look at today's entries
                    if today_str in row_date or not row_date:
                        emp_id = row.get('Employee_ID', row.get('employee_id', row.get('EmpID', '')))
                        emp_name = row.get('Employee_Name', row.get('employee_name', row.get('Name', 'Unknown')))
                        clock_in = row.get('Clock_In', row.get('clock_in', row.get('In', '')))
                        clock_out = row.get('Clock_Out', row.get('clock_out'), row.get('Out', ''))
                        role = row.get('Role', row.get('role', 'Employee'))

                        # If clocked in but not clocked out, they're working
                        if clock_in and not clock_out:
                            # Calculate hours worked so far
                            try:
                                clock_in_time = datetime.strptime(clock_in, '%H:%M:%S').replace(
                                    year=datetime.now().year,
                                    month=datetime.now().month,
                                    day=datetime.now().day
                                )
                                hours_worked = (datetime.now() - clock_in_time).total_seconds() / 3600
                            except:
                                try:
                                    clock_in_time = datetime.strptime(clock_in, '%H:%M').replace(
                                        year=datetime.now().year,
                                        month=datetime.now().month,
                                        day=datetime.now().day
                                    )
                                    hours_worked = (datetime.now() - clock_in_time).total_seconds() / 3600
                                except:
                                    hours_worked = 0

                            clocked_in[emp_id] = {
                                'name': emp_name,
                                'role': role,
                                'clock_in': clock_in,
                                'hours': round(hours_worked, 1)
                            }
                        elif clock_out and emp_id in clocked_in:
                            # They clocked out, remove from working list
                            del clocked_in[emp_id]

        # Also check Employees directory for additional info
        emp_file = os.path.join(DATA_DIR, 'Employees', 'employees.csv')
        emp_info = {}
        if os.path.exists(emp_file):
            with open(emp_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    emp_id = row.get('Employee_ID', row.get('employee_id', row.get('ID', '')))
                    emp_info[emp_id] = {
                        'name': row.get('Name', row.get('Employee_Name', '')),
                        'role': row.get('Role', row.get('role', 'Employee'))
                    }

        # Build final staff list
        for emp_id, data in clocked_in.items():
            if emp_id in emp_info:
                data['name'] = emp_info[emp_id]['name'] or data['name']
                data['role'] = emp_info[emp_id]['role'] or data['role']
            staff.append(data)
            total_hours += data['hours']

        return jsonify({
            'success': True,
            'staff': staff,
            'total_hours': round(total_hours, 1)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# API: Low Stock Items
# ============================================
@app.route('/api/dashboard/lowstock')
def api_dashboard_lowstock():
    """Get low stock items from Inventory CSV"""
    try:
        items = []
        critical_count = 0

        # Look for inventory file
        inv_dir = os.path.join(DATA_DIR, 'Inventory')

        possible_files = [
            os.path.join(inv_dir, 'inventory.csv'),
            os.path.join(inv_dir, 'Inventory.csv'),
            os.path.join(inv_dir, 'products.csv'),
            os.path.join(inv_dir, 'items.csv'),
        ]

        inv_file = None
        for f in possible_files:
            if os.path.exists(f):
                inv_file = f
                break

        if inv_file:
            with open(inv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Get quantity on hand
                    qty = int(row.get('Qty_On_Hand', row.get('qty_on_hand',
                              row.get('On_Hand', row.get('on_hand',
                              row.get('Stock', row.get('stock', 0)))))) or 0)

                    # Get reorder point (default 5)
                    reorder = int(row.get('Reorder_Point', row.get('reorder_point',
                                  row.get('Reorder', row.get('Min_Stock', 5)))) or 5)

                    # Check if below reorder point
                    if qty <= reorder:
                        item = {
                            'name': row.get('Item_Name', row.get('item_name',
                                    row.get('Name', row.get('name',
                                    row.get('Product', 'Unknown'))))),
                            'sku': row.get('SKU', row.get('sku', row.get('Item_ID', '-'))),
                            'on_hand': qty,
                            'reorder_point': reorder
                        }
                        items.append(item)

                        if qty <= 2:
                            critical_count += 1

        # Sort by quantity (lowest first)
        items.sort(key=lambda x: x['on_hand'])

        return jsonify({
            'success': True,
            'items': items,
            'critical_count': critical_count
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ============================================
# IMPORTANT: Update your DATA_DIR variable
# ============================================
# Make sure DATA_DIR points to your CSV data folder, e.g.:
# DATA_DIR = '/mnt/sdcard/Mountain Gardens Nursery POS/data'
# or
# DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
# ============================================

# ==============================================================================
#                     NOTIFICATIONS
# ==============================================================================

@app.route('/notifications')
@login_required
def notifications():
    notifs = get_all_notifications(session['employee_id'])
    return render_template('notifications.html', notifications=notifs)


@app.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    ntype = (request.form.get("type") or request.args.get("type") or "").strip().upper()
    emp_id = str(session.get("employee_id", ""))

    marked = 0
    try:
        rows = read_csv(get_notification_path())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for r in rows:
            if str(r.get("Employee_ID", "")) != emp_id:
                continue

            if ntype and (str(r.get("Type", "")) or "").upper() != ntype:
                continue

            read_flag = str(r.get("Read", r.get("Is_Read", "N"))).strip().upper()
            if read_flag in ("Y", "YES", "TRUE", "1"):
                continue

            r["Read"] = "Y"
            r["Read_Date"] = now
            marked += 1

        if marked:
            write_csv(get_notification_path(), NOTIFICATION_HEADERS, rows)

    except Exception:
        marked = 0

    # ✅ If called by JS/fetch, return JSON
    is_ajax = (request.headers.get("X-Requested-With") == "XMLHttpRequest")
    if is_ajax:
        return jsonify({"marked": marked})

    # ✅ Normal form post: redirect back
    return redirect(request.referrer or url_for("my_tasks"))



# ==============================================================================
#                     SALES TERMINAL
# ==============================================================================

@app.route('/sales')
@login_required
def sales():
    return render_template('sales/terminal.html',
        categories=MAIN_CATEGORIES,
        animal_subs=ANIMAL_SUBCATEGORIES,
        product_subs=PRODUCT_SUBCATEGORIES,
        plant_subs=PLANT_SUBCATEGORIES
    )


@app.route('/sales/search')
@login_required
def sales_search():
    query = request.args.get('q', '')
    items = search_items(query)
    
    results = []
    for item in items[:20]:
        stock = get_stock_on_hand(item['SKU'])
        results.append({
            'sku': item['SKU'],
            'name': item['Item_Name'],
            'label': f"{item['Item_Name']} — {item['SKU']}",
            'category': item.get('Category', ''),
            'price': float(item.get('Default_Price', 0)),
            'stock': stock
        })
    
    return jsonify({'items': results})


@app.route('/sales/item/<sku>')
@login_required
def sales_item_details(sku):
    item = get_item(sku)
    if not item:
        return jsonify({'ok': False, 'error': 'Item not found'}), 404
    
    stock = get_stock_on_hand(sku)
    avg_cost = get_average_cost(sku)
    
    return jsonify({
        'ok': True,
        'success': True,
        'sku': sku,
        'name': item.get('Item_Name', ''),
        'category': item.get('Category', ''),
        'price': float(item.get('Default_Price', 0)),
        'wholesale': avg_cost,
        'qty_on_hand': stock,
        'on_hand': stock,
        'taxable': item.get('Taxable', 'Y') == 'Y'
    })


@app.route('/sales/complete', methods=['POST'])
@login_required
def complete_sale():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            items = data.get('items', [])
            payment_method = data.get('payment_method', 'CASH')
            amount_received = float(data.get('cash_received') or data.get('amount_received') or 0)
        else:
            items_json = request.form.get('items', '[]')
            items = json.loads(items_json)
            payment_method = request.form.get('payment_method', 'CASH')
            amount_received = float(request.form.get('cash_received') or 0)
        
        if not items:
            return jsonify({'success': False, 'error': 'No items in cart'})
        
        success, result = record_sale(
            items=items,
            emp_id=session['employee_id'],
            emp_name=session['employee_name'],
            payment_method=payment_method,
            amount_received=amount_received,
            notes=''
        )
        
        if success:
            change = result.get('change_due', 0)
            return jsonify({
                'success': True,
                'transaction_id': result['transaction_id'],
                'total': result['total'],
                'change': change,
                'change_breakdown': make_change_breakdown(change)
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def _sales_logs_root() -> Path:
    # /mnt/sdcard/Mountain Gardens Nursery POS/Sales_Logs
    return Path(__file__).resolve().parent / "Sales_Logs"

def _list_saleslog_files() -> list[dict]:
    """
    Returns list of dicts:
      { "rel": "2025/12_December/Week_3/2025-12-15_Monday_SalesLog.csv",
        "label": "2025-12-15 Monday",
        "path": Path(...) }
    """
    root = _sales_logs_root()
    files = []
    if not root.exists():
        return files

    # Only SalesLog files (ignore other variants)
    for p in root.rglob("*SalesLog.csv"):
        rel = str(p.relative_to(root)).replace("\\", "/")

        # Try to build a nice label from filename: YYYY-MM-DD_Day_SalesLog.csv
        name = p.name
        m = re.match(r"(\d{4}-\d{2}-\d{2})_([A-Za-z]+)_SalesLog\.csv$", name)
        if m:
            label = f"{m.group(1)} {m.group(2)}"
        else:
            label = name

        files.append({"rel": rel, "label": label, "path": p})

    # Sort newest first by modified time
    files.sort(key=lambda x: x["path"].stat().st_mtime, reverse=True)
    return files

def _read_csv_rows(path: Path, limit: int = 300) -> tuple[list[str], list[dict]]:
    rows: list[dict] = []
    headers: list[str] = []
    if not path.exists():
        return headers, rows

    with path.open("r", newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        for i, row in enumerate(r):
            rows.append(row)
            if i + 1 >= limit:
                break
    return headers, rows

def _sales_logs_root() -> Path:
    # /mnt/sdcard/Mountain Gardens Nursery POS/Sales_Logs
    return Path(__file__).resolve().parent / "Sales_Logs"

def _transaction_logs_root() -> Path:
    # /mnt/sdcard/Mountain Gardens Nursery POS/Transaction_Logs
    return Path(__file__).resolve().parent / "Transaction_Logs"

def _list_saleslog_files() -> list[dict]:
    """
    Returns list of dicts:
      { "rel": "2025/12_December/Week_3/2025-12-15_Monday_SalesLog.csv",
        "label": "2025-12-15 Monday",
        "path": Path(...) }
    """
    root = _sales_logs_root()
    files = []
    if not root.exists():
        return files

    for p in root.rglob("*SalesLog.csv"):
        rel = str(p.relative_to(root)).replace("\\", "/")

        name = p.name
        m = re.match(r"(\d{4}-\d{2}-\d{2})_([A-Za-z]+)_SalesLog\.csv$", name)
        if m:
            label = f"{m.group(1)} {m.group(2)}"
        else:
            label = name

        files.append({"rel": rel, "label": label, "path": p})

    files.sort(key=lambda x: x["path"].stat().st_mtime, reverse=True)
    return files

def _read_csv_rows(path: Path, limit: int = 300) -> tuple[list[str], list[dict]]:
    rows: list[dict] = []
    headers: list[str] = []
    if not path or not path.exists():
        return headers, rows

    with path.open("r", newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        headers = r.fieldnames or []
        for i, row in enumerate(r):
            rows.append(row)
            if i + 1 >= limit:
                break
    return headers, rows

def _parse_day_from_saleslog_filename(name: str) -> tuple[str | None, str | None]:
    m = re.match(r"(\d{4}-\d{2}-\d{2})_([A-Za-z]+)_SalesLog\.csv$", name or "")
    if not m:
        return None, None
    return m.group(1), m.group(2)

def _find_matching_transaction_log(date_str: str, day_str: str) -> Path | None:
    """
    Looks for: YYYY-MM-DD_Day_TransactionLog.csv anywhere under Transaction_Logs.
    Falls back to looser patterns if needed.
    """
    root = _transaction_logs_root()
    if not root.exists():
        return None

    exact = f"{date_str}_{day_str}_TransactionLog.csv"
    for p in root.rglob(exact):
        return p

    # fallback patterns (in case naming differs slightly)
    patterns = [
        f"{date_str}_*_TransactionLog.csv",
        f"{date_str}*_TransactionLog.csv",
        f"*{date_str}*TransactionLog*.csv",
    ]
    for pat in patterns:
        hits = list(root.rglob(pat))
        if hits:
            hits.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return hits[0]

    return None

def _safe_float(x) -> float:
    try:
        return float(str(x).replace("$", "").strip() or 0)
    except Exception:
        return 0.0

def _safe_int(x) -> int:
    try:
        return int(float(str(x).strip() or 0))
    except Exception:
        return 0

@app.route("/sales/log")
@login_required
def sales_log():
    files = _list_saleslog_files()

    # Prefer today's SalesLog if present; else newest file
    selected_rel = (request.args.get("file") or "").strip()
    if not selected_rel:
        today = date.today().strftime("%Y-%m-%d")
        picked = None
        for f in files:
            if f["label"].startswith(today + " "):
                picked = f["rel"]
                break
        selected_rel = picked or (files[0]["rel"] if files else "")

    selected_sales_path = None
    for f in files:
        if f["rel"] == selected_rel:
            selected_sales_path = f["path"]
            break

    # Read SalesLog (line items)
    row_limit = 400
    sales_headers, sales_rows = ([], [])
    date_str, day_str = (None, None)
    if selected_sales_path:
        sales_headers, sales_rows = _read_csv_rows(selected_sales_path, limit=row_limit)
        date_str, day_str = _parse_day_from_saleslog_filename(selected_sales_path.name)

    # Auto-match TransactionLog for the same day
    tx_path = None
    tx_headers, tx_rows = ([], [])
    if date_str and day_str:
        tx_path = _find_matching_transaction_log(date_str, day_str)
        if tx_path:
            tx_headers, tx_rows = _read_csv_rows(tx_path, limit=row_limit)

    # Simple day metrics
    tx_total = sum(_safe_float(r.get("Total", 0)) for r in tx_rows) if tx_rows else 0.0
    tx_count = len(tx_rows) if tx_rows else 0

    items_sold = sum(_safe_int(r.get("Quantity", 0)) for r in sales_rows) if sales_rows else 0
    sales_line_total = sum(_safe_float(r.get("Line_Total", 0)) for r in sales_rows) if sales_rows else 0.0
    sales_cogs_total = sum(_safe_float(r.get("COGS_Line", 0)) for r in sales_rows) if sales_rows else 0.0
    sales_gross = (sales_line_total - sales_cogs_total)

    return render_template(
        "sales/log.html",
        files=files,
        selected_file=selected_rel,

        # Transactions (header rows)
        tx_headers=tx_headers,
        tx_rows=tx_rows,
        tx_file=(tx_path.name if tx_path else ""),

        # Sales (line rows)
        sales_headers=sales_headers,
        sales_rows=sales_rows,
        sales_file=(selected_sales_path.name if selected_sales_path else ""),

        # Metrics
        row_limit=row_limit,
        tx_count=tx_count,
        tx_total=tx_total,
        items_sold=items_sold,
        sales_line_total=sales_line_total,
        sales_cogs_total=sales_cogs_total,
        sales_gross=sales_gross,
    )

# --- Email receipt (logs + sends PDF attachment) ---
@app.route("/sales/receipt/<trans_id>/email", methods=["POST"])
def receipt_email(trans_id):
    emp_id = session.get("employee_id", "")
    customer_name = (request.form.get("customer_name") or "").strip()
    customer_email = (request.form.get("customer_email") or "").strip()

    if not customer_email or "@" not in customer_email:
        return jsonify({"ok": False, "error": "Enter a valid email."}), 400

    customer_id = upsert_customer(customer_name, customer_email)

    bundle = get_receipt_bundle(trans_id)
    if not bundle:
        return jsonify({"ok": False, "error": "Receipt not found."}), 404

    try:
        pdf_bytes = build_receipt_pdf_bytes(bundle)  # function you’ll add in POS_CORE
        send_receipt_email_smtp(
            to_email=customer_email,
            customer_name=customer_name,
            trans_id=trans_id,
            pdf_bytes=pdf_bytes,
        )
        log_receipt_delivery(
            trans_id,
            method="EMAIL",
            status="OK",
            notes="Sent receipt email",
            emp_id=emp_id,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
        )
        return jsonify({"ok": True})
    except Exception as e:
        log_receipt_delivery(
            trans_id,
            method="EMAIL",
            status="FAILED",
            notes=str(e),
            emp_id=emp_id,
            customer_id=customer_id,
            customer_name=customer_name,
            customer_email=customer_email,
        )
        return jsonify({"ok": False, "error": f"Email failed: {e}"}), 500


# ==============================================================================
#                     INVENTORY
# ==============================================================================

@app.route('/inventory')
@login_required
def inventory():
    items = get_all_items()
    for item in items:
        item['stock_on_hand'] = get_stock_on_hand(item['SKU'])
    return render_template('inventory/list.html', items=items)


@app.route('/inventory/add', methods=['GET', 'POST'])
@manager_required
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory', '')
        price = float(request.form.get('price', 0))
        reorder = int(request.form.get('reorder_point', 5))
        
        sku = generate_sku(name, category, subcategory)
        success, msg = create_item(sku, name, category, subcategory, name, price, reorder)
        
        if success:
            flash(f'Item created: {sku}', 'success')
            return redirect(url_for('inventory'))
        flash(msg, 'error')
    
    return render_template('inventory/add.html',
        categories=MAIN_CATEGORIES,
        animal_subs=ANIMAL_SUBCATEGORIES,
        product_subs=PRODUCT_SUBCATEGORIES,
        plant_subs=PLANT_SUBCATEGORIES
    )

@app.route('/inventory/edit/<sku>', methods=['GET', 'POST'])
@manager_required
def edit_item(sku):
    item = get_item(sku)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("inventory"))

    if request.method == "POST":
        new_sku = (request.form.get("SKU") or sku).strip()

        # --- build updates for Items.csv (match POS_CORE ITEM_HEADERS) ---
        updates = {
            "Item_Name": (request.form.get("Item_Name") or "").strip(),
            "Category": (request.form.get("Category") or "").strip(),
            "Subcategory": (request.form.get("Subcategory") or "").strip(),
            "Product_Name": (request.form.get("Product_Name") or "").strip(),
            "Default_Unit": (request.form.get("Default_Unit") or "").strip(),
            "Default_Price": (request.form.get("Default_Price") or "").strip(),
            "Taxable": (request.form.get("Taxable") or "Y").strip(),
            "Reorder_Point": (request.form.get("Reorder_Point") or "").strip(),
            "Status": (request.form.get("Status") or "Active").strip(),
            "Notes": (request.form.get("Notes") or "").strip(),
            "Size": (request.form.get("Size") or "").strip(),
            "Item_Description": (request.form.get("Item_Description") or "").strip(),
            "Wholesale_Cost": (request.form.get("Wholesale_Cost") or "").strip(),
            "Retail_Markup": (request.form.get("Retail_Markup") or "").strip(),
            "Retail_Price": (request.form.get("Retail_Price") or "").strip(),
            "Unit_Cost": (request.form.get("Unit_Cost") or "").strip(),
            "Unit_Price": (request.form.get("Unit_Price") or "").strip(),
        }

        # strip keys that user left blank (prevents wiping fields accidentally)
        updates = {k: v for k, v in updates.items() if v != ""}

        items = read_csv(get_items_path())

        # If SKU is being changed, ensure it doesn't collide
        if new_sku != sku:
            if any((r.get("SKU") or "").strip() == new_sku for r in items):
                flash(f"SKU '{new_sku}' already exists. Pick a different SKU.", "error")
                return redirect(url_for("edit_item", sku=sku))

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        saved = False
        for r in items:
            if (r.get("SKU") or "").strip() == sku:
                r.update(updates)
                r["SKU"] = new_sku
                r["Last_Updated"] = now
                saved = True
                break

        if not saved:
            flash("Could not update item (SKU not found in Items.csv).", "error")
            return redirect(url_for("inventory"))

        write_csv(get_items_path(), ITEM_HEADERS, items)

        # keep Lots.csv tied to the SKU if SKU changed
        if new_sku != sku:
            lots = read_csv(get_lots_path())
            for l in lots:
                if (l.get("SKU") or "").strip() == sku:
                    l["SKU"] = new_sku
            write_csv(get_lots_path(), LOT_HEADERS, lots)

            ledger = read_csv(get_ledger_path())
            for e in ledger:
                if (e.get("SKU") or "").strip() == sku:
                    e["SKU"] = new_sku
            write_csv(get_ledger_path(), LEDGER_HEADERS, ledger)

        flash("Item updated ✅", "success")
        return redirect(url_for("edit_item", sku=new_sku))

    # GET view (also show lots + stock)
    lots = get_lots_for_sku(sku, available_only=False)
    return render_template(
        "inventory/edit.html",
        item=item,
        lots=lots,
        stock=get_stock_on_hand(sku),
        avg_cost=get_average_cost(sku),
    )
    flash(f"✅ Received {qty} into {sku}.", "success")
    return redirect(url_for("receive_stock"))




@app.route("/inventory/lots/edit/<lot_id>", methods=["POST"])
@manager_required
def edit_lot(lot_id):
    sku = (request.form.get("sku") or "").strip()

    lots = read_csv(get_lots_path())
    found = False
    for l in lots:
        if (l.get("Lot_ID") or "").strip() == lot_id:
            l["Received_Date"] = (request.form.get("Received_Date") or l.get("Received_Date") or "").strip()
            l["Supplier"] = (request.form.get("Supplier") or l.get("Supplier") or "").strip()
            l["Invoice_Ref"] = (request.form.get("Invoice_Ref") or l.get("Invoice_Ref") or "").strip()
            l["Unit_Cost"] = (request.form.get("Unit_Cost") or l.get("Unit_Cost") or "").strip()
            l["Qty_Remaining"] = (request.form.get("Qty_Remaining") or l.get("Qty_Remaining") or "").strip()
            l["Expiry_Date"] = (request.form.get("Expiry_Date") or l.get("Expiry_Date") or "").strip()
            l["Notes"] = (request.form.get("Notes") or l.get("Notes") or "").strip()
            found = True
            break

    if not found:
        flash("Lot not found.", "error")
        return redirect(url_for("edit_item", sku=sku or ""))

    write_csv(get_lots_path(), LOT_HEADERS, lots)
    flash("Lot updated ✅", "success")
    return redirect(url_for("edit_item", sku=sku))



#ensure_csv_exists(get_lots_path(), LOT_HEADERS)
#ensure_csv_exists(get_ledger_path(), LEDGER_HEADERS)


@app.route("/inventory/receive", methods=["GET", "POST"], endpoint="receive_stock")
@manager_required
def receive_stock():
    # GET: show receive page
    if request.method == "GET":
        items = read_csv(get_items_path())
        return render_template("inventory/receive.html", items=items)

    # POST: process receiving
    mode = (request.form.get("mode") or "existing").strip()
    sku = (request.form.get("sku") or "").strip()

    supplier = (request.form.get("supplier") or "").strip()
    invoice_no = (request.form.get("invoice_no") or "").strip()
    note = (request.form.get("notes") or "").strip()

    try:
        qty = int(float(request.form.get("qty") or 0))
    except Exception:
        qty = 0

    try:
        unit_cost = float(request.form.get("unit_cost") or 0)
    except Exception:
        unit_cost = 0.0

    if qty <= 0:
        flash("Please enter a Quantity > 0.", "error")
        return redirect(url_for("receive_stock"))

    # NEW item: create in Items.csv first
    if mode == "new":
        item_name = (request.form.get("item_name") or "").strip()
        category = (request.form.get("category") or "General").strip()
        subcategory = (request.form.get("subcategory") or "General").strip()

        try:
            price = float(request.form.get("price") or 0)
        except Exception:
            price = 0.0

        try:
            reorder_point = int(float(request.form.get("reorder_point") or 5))
        except Exception:
            reorder_point = 5

        if not item_name:
            flash("New item requires an Item Name.", "error")
            return redirect(url_for("receive_stock"))

        if not sku:
            sku = generate_sku(prefix="MGN")

        ok, msg = create_item(
            sku, item_name, category, subcategory,
            item_name, price, reorder_point, note
        )
        if not ok:
            flash(msg, "error")
            return redirect(url_for("receive_stock"))

    # Existing item must provide SKU
    if mode != "new" and not sku:
        flash("Please select an existing SKU.", "error")
        return redirect(url_for("receive_stock"))

    # Canonical lot write (updates Lots.csv + Ledger.csv consistently)
    create_lot(
        sku=sku,
        qty=qty,
        cost=unit_cost,
        supplier=supplier,
        invoice=invoice_no,
        notes=note
    )

    flash(f"✅ Received {qty} into {sku}.", "success")
    return redirect(url_for("receive_stock"))



@app.route('/inventory/low-stock')
@login_required
def low_stock_report():
    low_stock = check_low_stock()
    return render_template('inventory/low_stock.html', items=low_stock)
    return lot_id

@app.route('/inventory/lots')
@login_required
def view_lots():
    sku = request.args.get('sku')
    if not sku:
        return redirect(url_for('inventory'))
    
    item = get_item(sku)
    if not item:
        flash('Item not found', 'error')
        return redirect(url_for('inventory'))
    
    lots = get_lots_for_sku(sku, available_only=False)
    return render_template('inventory/lots.html', item=item, lots=lots, 
                          stock=get_stock_on_hand(sku), avg_cost=get_average_cost(sku))

def _patch_receive_dates(lot_id: str, recv_date: str) -> None:
    # requires these to be imported from POS_CORE:
    # read_csv, write_csv, get_lots_path, LOT_HEADERS, get_ledger_path, LEDGER_HEADERS
    lots = read_csv(get_lots_path())
    for row in lots:
        if row.get("Lot_ID") == lot_id:
            row["Received_Date"] = recv_date
            break
    write_csv(get_lots_path(), LOT_HEADERS, lots)

    ledger = read_csv(get_ledger_path())
    for row in ledger:
        if row.get("Lot_ID") == lot_id and row.get("Reason") == "Receive":
            ts = row.get("Timestamp", "")
            time_part = ts.split(" ", 1)[1] if " " in ts else "00:00:00"
            row["Timestamp"] = f"{recv_date} {time_part}"
            break
    write_csv(get_ledger_path(), LEDGER_HEADERS, ledger)

# ==============================================================================
#                     TIME CLOCK
# ==============================================================================
LA_TZ = ZoneInfo("America/Los_Angeles")


def _parse_dt(s: str):
    """Best-effort datetime parser for common formats."""
    if not s:
        return None
    s = s.strip()
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except ValueError:
            pass
    # last resort: try fromisoformat
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def compute_seconds_worked_today(employee_id: str) -> int:
    """
    Reads clock events from CSV and computes worked seconds for today in America/Los_Angeles.
    Supports common columns: employee_id/emp_id/user_id, action/event/type, timestamp/time/datetime.
    Actions supported: IN/OUT, CLOCK_IN/CLOCK_OUT.
    """
    if not employee_id:
        return 0

    if not os.path.exists(TIME_CLOCK_CSV):
        return 0

    now = datetime.now(LA_TZ)
    today_start = datetime.combine(now.date(), dtime(0, 0, 0), tzinfo=LA_TZ)
    today_end = datetime.combine(now.date(), dtime(23, 59, 59), tzinfo=LA_TZ)

    # Load events for this employee
    events = []
    with open(TIME_CLOCK_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # employee id column variants
            rid = (row.get("employee_id") or row.get("emp_id") or row.get("user_id") or "").strip()
            if rid != str(employee_id):
                continue

            action = (row.get("action") or row.get("event") or row.get("type") or "").strip().upper()

            ts_raw = row.get("timestamp") or row.get("time") or row.get("datetime") or row.get("created_at") or ""
            dt = _parse_dt(ts_raw)

            if not dt:
                continue

            # assume local if naive
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=LA_TZ)
            else:
                dt = dt.astimezone(LA_TZ)

            # only today’s events matter
            if dt < today_start or dt > today_end:
                continue

            # normalize action
            if action in {"IN", "CLOCKIN", "CLOCK_IN", "CLOCK-IN"}:
                action = "IN"
            elif action in {"OUT", "CLOCKOUT", "CLOCK_OUT", "CLOCK-OUT"}:
                action = "OUT"
            else:
                # ignore unknown actions
                continue

            events.append((dt, action))

    if not events:
        return 0

    events.sort(key=lambda x: x[0])

    total = 0
    last_in = None

    for dt, action in events:
        if action == "IN":
            last_in = dt
        elif action == "OUT":
            if last_in:
                total += int((dt - last_in).total_seconds())
                last_in = None

    # if still clocked in, count up to now
    if last_in:
        total += int((now - last_in).total_seconds())

    return max(total, 0)


@app.route("/api/me/clock-status")
@login_required
def api_me_clock_status():
    emp_id = session.get("employee_id", "")
    status = get_employee_status(emp_id) or {}
    return jsonify({
        "employee_id": emp_id,
        "is_clocked_in": bool(status.get("is_clocked_in")),
        "hours_today": float(status.get("hours_today", 0.0) or 0.0),
        "last_punch": status.get("last_punch", ""),
    })


@app.get("/api/me/hours_today")
def api_me_hours_today():
    # adjust to how you store login identity
    employee_id = session.get("employee_id") or session.get("user_id")
    if not employee_id:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    seconds = compute_seconds_worked_today(str(employee_id))
    return jsonify({"ok": True, "seconds_today": seconds})
@app.route('/timeclock')
@login_required
def timeclock():
    status = get_employee_status(session['employee_id'])
    return render_template('time/clock.html', status=status)


@app.route('/timeclock/punch', methods=['POST'])
@login_required
def punch_clock():
    action = request.form.get('action')
    emp_id = session['employee_id']
    emp_name = session['employee_name']
    
    if action == 'clock_in':
        success, msg, _ = clock_in(emp_id, emp_name)
    elif action == 'clock_out':
        success, msg, _ = clock_out(emp_id, emp_name)
    elif action == 'break':
        success, msg, _ = start_break(emp_id, emp_name, 'BREAK')
    elif action == 'lunch':
        success, msg, _ = start_break(emp_id, emp_name, 'LUNCH')
    elif action == 'end_break':
        success, msg, _ = end_break(emp_id, emp_name)
    else:
        success, msg = False, 'Invalid action'
    
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('timeclock'))


@app.route('/timeclock/log')
@login_required
def timeclock_log():
    target_date = request.args.get('date')
    if target_date:
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    else:
        target_date = date.today()
    
    punches = read_csv(get_timeclock_path(target_date))
    
    if session.get('role') not in ('Manager', 'Owner', 'Admin'):
        punches = [p for p in punches if p.get('Employee_ID') == session['employee_id']]
    
    return render_template('time/log.html', punches=punches, selected_date=target_date)


@app.route('/timeclock/manage')
@manager_required
def timeclock_manage():
    target_date = request.args.get('date')
    if target_date:
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    else:
        target_date = date.today()
    
    punches = get_punches_for_date(target_date)
    employees = get_all_employees()
    return render_template('timeclock/manage.html', punches=punches, employees=employees, selected_date=target_date)


@app.route('/timeclock/edit/<punch_id>', methods=['GET', 'POST'])
@manager_required
def timeclock_edit_punch(punch_id):
    punch = get_punch_by_id(punch_id)
    if not punch:
        flash('Punch not found', 'error')
        return redirect(url_for('timeclock_manage'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        reason = request.form.get('reason', '')
        
        if action == 'update':
            new_time = request.form.get('punch_time')
            new_type = request.form.get('punch_type')
            success, msg = edit_punch(punch_id, new_time, new_type,
                                     session['employee_id'], session['employee_name'], reason)
        elif action == 'delete':
            success, msg = delete_punch(punch_id, session['employee_id'], session['employee_name'], reason)
        else:
            success, msg = False, "Invalid action"
        
        flash(msg, 'success' if success else 'error')
        return redirect(url_for('timeclock_manage', date=punch.get('Date')))
    
    punch_types = ['CLOCK_IN', 'CLOCK_OUT', 'BREAK', 'LUNCH', 'END_BREAK', 'END_LUNCH']
    return render_template('timeclock/edit_punch.html', punch=punch, punch_types=punch_types)


@app.route('/timeclock/add-punch', methods=['GET', 'POST'])
@manager_required
def timeclock_add_punch():
    if request.method == 'POST':
        punch_time = request.form.get('punch_time')
        if punch_time and len(punch_time) == 5:
            punch_time = f"{punch_time}:00"
        
        success, msg = add_punch(
            employee_id=request.form.get('employee_id'),
            employee_name=request.form.get('employee_name'),
            punch_date=request.form.get('punch_date'),
            punch_time=punch_time,
            punch_type=request.form.get('punch_type'),
            added_by_id=session['employee_id'],
            added_by_name=session['employee_name'],
            reason=request.form.get('reason', '')
        )
        flash(msg, 'success' if success else 'error')
        if success:
            return redirect(url_for('timeclock_manage', date=request.form.get('punch_date')))
    
    employees = get_all_employees()
    punch_types = ['CLOCK_IN', 'CLOCK_OUT', 'BREAK', 'LUNCH', 'END_BREAK', 'END_LUNCH']
    return render_template('timeclock/add_punch.html', employees=employees, punch_types=punch_types, today=date.today())


@app.route('/timeclock/edit-history')
@manager_required
def timeclock_edit_history_view():
    days = int(request.args.get('days', 30))
    employee_id = request.args.get('employee_id')
    history = get_timeclock_edit_history(employee_id, days)
    employees = get_all_employees()
    return render_template('timeclock/edit_history.html', history=history, employees=employees, selected_days=days)


# ==============================================================================
#                     TIME OFF
# ==============================================================================

# --- TIME OFF storage (local, stable) ---
TIMEOFF_HEADERS = [
    "Request_ID","Employee_ID","Employee_Name","Request_Date",
    "Start_Date","End_Date","Days_Requested","Reason",
    "Status","Manager_Name","Approval_Date","Manager_Notes"
]

def get_timeoff_path():
    # matches your structure: Time_Off_Requests/2025_TimeOffRequests.csv
    year = datetime.now().strftime("%Y")
    folder = os.path.join(BASE_DIR, "Time_Off_Requests")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{year}_TimeOffRequests.csv")


def generate_id(prefix="ID"):
    # unique enough for POS use (timestamp to milliseconds)
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"


def _request_time_off_core(emp_id, emp_name, start, end, reason=""):
    """Core logic: validate + write to Time_Off_Requests/YYYY_TimeOffRequests.csv"""
    if start < date.today():
        return False, "🚫 Cannot request past dates.", ""

    min_start = date.today() + timedelta(days=14)
    if start < min_start:
        return False, f"⏳ Must request at least 14 days in advance. Earliest: {min_start:%Y-%m-%d}", ""

    if end < start:
        return False, "🚫 End date must be on/after start date.", ""

    days = (end - start).days + 1
    req_id = generate_id("REQ")

    row = {
        "Request_ID": req_id,
        "Employee_ID": str(emp_id),
        "Employee_Name": emp_name,
        "Request_Date": date.today().strftime("%Y-%m-%d"),
        "Start_Date": start.strftime("%Y-%m-%d"),
        "End_Date": end.strftime("%Y-%m-%d"),
        "Days_Requested": str(days),
        "Reason": reason,
        "Status": "Pending",
        "Manager_Name": "",
        "Approval_Date": "",
        "Manager_Notes": "",
    }

    append_csv(get_timeoff_path(), TIMEOFF_HEADERS, row)


    return True, f"🎉 Request submitted ({days} days).", req_id


@app.route("/timeoff")
@login_required
def timeoff():
    my_requests = get_time_off_requests(employee_id=str(session["employee_id"]))
    pending = []
    if session.get("role") in ("Manager", "Owner", "Admin"):
        pending = get_pending_requests()

    earliest_date = (date.today() + timedelta(days=14)).strftime("%Y-%m-%d")

    my_requests = sorted(my_requests, key=lambda r: r.get("Request_Date", ""), reverse=True)
    pending = sorted(pending, key=lambda r: r.get("Request_Date", ""), reverse=True)

    return render_template(
        "time/timeoff.html",
        my_requests=my_requests,
        pending_requests=pending,
        earliest_date=earliest_date,
    )


@app.route("/timeoff/request", methods=["POST"], endpoint="request_timeoff")
@login_required
def request_timeoff():
    # Parse form
    start_s = (request.form.get("start_date") or "").strip()
    end_s = (request.form.get("end_date") or "").strip()
    reason = (request.form.get("reason") or "").strip()

    if not start_s or not end_s:
        flash("🚫 Start and End dates are required.", "error")
        return redirect(url_for("timeoff"))

    start = datetime.strptime(start_s, "%Y-%m-%d").date()
    end = datetime.strptime(end_s, "%Y-%m-%d").date()

    # Core write (saves to your existing YYYY_TimeOffRequests.csv)
    success, msg, req_id = _request_time_off_core(
        str(session["employee_id"]),
        session["employee_name"],
        start,
        end,
        reason,
    )

    if success:
        flash(f"{msg} ✅ {start} → {end} 🆔 {req_id}", "success")
        flash("📬 Your manager will review it soon — thanks for planning ahead 🙌", "info")

        # 🔔 Notify managers/owners/admins
        try:
            for e in get_all_employees(include_inactive=True):
                if e.get("Role") in ("Manager", "Owner", "Admin") and e.get("Status", "Active") != "Inactive":
                    if str(e.get("Employee_ID")) == str(session["employee_id"]):
                        continue
                    note = f"⏳ TIME OFF PENDING: {session['employee_name']} • {start} → {end} • ID {req_id}"
                    if reason:
                        note += f" • 📝 {reason}"
                    create_notification(e.get("Employee_ID"), e.get("Employee_Name"), note, "TIMEOFF")
        except Exception:
            pass
    else:
        flash(msg, "error")

    return redirect(url_for("timeoff"))


@app.route("/timeoff/decision", methods=["POST"], endpoint="timeoff_decision")
@login_required
def timeoff_decision():
    if session.get("role") not in ("Manager", "Owner", "Admin"):
        flash("🚫 Not authorized.", "error")
        return redirect(url_for("timeoff"))

    req_id = (request.form.get("req_id") or "").strip()
    decision = (request.form.get("decision") or "").strip()
    notes = (request.form.get("manager_notes") or "").strip()
    approved = (decision == "approve")

    if not notes:
        notes = "🎉 Approved! Enjoy your time off 🙌" if approved else "🙏 Thanks for understanding — not approved at this time. Please try different dates or talk with your manager. 💬"

    # IMPORTANT: call the POS_CORE function, not this file's route name
    ok, msg = approve_time_off(req_id, str(session["employee_id"]), session["employee_name"], approved, notes)

    flash(msg, "success" if ok else "error")
    return redirect(url_for("timeoff"))




# ==============================================================================
#                     EMPLOYEES
# ==============================================================================

@app.route('/employees')
@manager_required
def employees():
    emps = get_all_employees(include_inactive=True)
    return render_template('employees/list.html', employees=emps)


@app.route('/employees/add', methods=['GET', 'POST'])
@manager_required
def add_employee():
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        pin = request.form.get('pin')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        
        success, msg, emp_id = create_employee(name, role, pin, phone, email)
        if success:
            flash(msg, 'success')
            return redirect(url_for('employees'))
        flash(msg, 'error')
    
    return render_template('employees/add.html', roles=ROLES)


@app.route('/employees/<emp_id>')
@manager_required
def employee_detail(emp_id):
    emp = get_employee(emp_id)
    if not emp:
        flash('Employee not found', 'error')
        return redirect(url_for('employees'))
    
    pay_config = get_employee_pay_config(emp_id)
    return render_template('employees/detail.html', employee=emp, pay_config=pay_config)


# ==============================================================================
#                     TASKS
# ==============================================================================

@app.route('/tasks')
@manager_required
def tasks_owner_dashboard():
    today = date.today()

    employees = get_all_employees()
    templates = get_all_tasks()
    assignments = get_task_assignments_for_date(today)

    # group by employee
    by_emp = {}
    for e in employees:
        eid = e.get("Employee_ID")
        by_emp[eid] = {
            "emp": e,
            "tasks": [a for a in assignments if a.get("Employee_ID") == eid]
        }

    # Owner notifications (TASK-type)
    owner_notifs = [n for n in get_all_notifications(session["employee_id"], limit=30)
                    if n.get("Type") == "TASK"]

    return render_template(
        'tasks/owner_dashboard.html',
        today=today,
        employees=employees,
        templates=templates,
        by_emp=by_emp,
        owner_notifications=owner_notifs
    )


@app.route('/tasks/assign', methods=['POST'])
@manager_required
def tasks_assign():
    task_id = (request.form.get('task_id') or "").strip()
    employee_ids = request.form.getlist('employee_ids')  # multi-select
    due_date = (request.form.get('due_date') or date.today().isoformat()).strip()
    notes = (request.form.get('notes') or "").strip()

    if not task_id:
        flash('Please select a premade task.', 'error')
        return redirect(url_for('tasks_owner_dashboard'))

    if not employee_ids:
        flash('Please select at least 1 employee.', 'error')
        return redirect(url_for('tasks_owner_dashboard'))

    tmpl = get_task(task_id)
    title = (tmpl.get("Title") if tmpl else "Task")

    assigned_count = 0
    for eid in employee_ids:
        if not eid:
            continue

        assign_task(task_id, eid, due_date, session["employee_id"], notes)
        emp = get_employee(eid)
        if emp:
            create_notification(
                eid, emp.get("Employee_Name", ""),
                f"🧩 New task assigned: {title} (Due {due_date})",
                "TASK"
            )
        assigned_count += 1

    flash(f'Task assigned to {assigned_count} employee(s).', 'success')
    return redirect(url_for('tasks_owner_dashboard'))


@app.route('/tasks/quick-assign', methods=['POST'])
@manager_required
def tasks_quick_assign():
    """
    Custom task creator + assigner.
    ALSO auto-saves to templates via get_or_create_task_template().
    """
    title = (request.form.get('title') or "").strip()
    description = (request.form.get('description') or "").strip()
    category = (request.form.get('category') or "General").strip()
    priority = (request.form.get('priority') or "MEDIUM").strip()
    est_minutes = int(request.form.get('est_minutes') or 15)

    employee_ids = request.form.getlist('employee_ids')
    due_date = (request.form.get('due_date') or date.today().isoformat()).strip()
    notes = (request.form.get('notes') or "").strip()

    if not title:
        flash('Custom task title is required.', 'error')
        return redirect(url_for('tasks_owner_dashboard'))

    if not employee_ids:
        flash('Please select at least 1 employee.', 'error')
        return redirect(url_for('tasks_owner_dashboard'))

    task_id, created_new = get_or_create_task_template(
        title=title,
        description=description,
        category=category,
        priority=priority,
        estimated_minutes=est_minutes,
        created_by=session["employee_id"]
    )

    # Assign it
    assigned_count = 0
    for eid in employee_ids:
        if not eid:
            continue
        assign_task(task_id, eid, due_date, session["employee_id"], notes)
        emp = get_employee(eid)
        if emp:
            create_notification(
                eid, emp.get("Employee_Name", ""),
                f"🧩 New task assigned: {title} (Due {due_date})",
                "TASK"
            )
        assigned_count += 1

    if created_new:
        flash(f'Custom task created + saved to templates, assigned to {assigned_count}.', 'success')
    else:
        flash(f'Used existing template, assigned to {assigned_count}.', 'success')

    return redirect(url_for('tasks_owner_dashboard'))


@app.route('/tasks/my')
@login_required
def my_tasks():
    today = date.today().isoformat()

    # pull ALL tasks for employee (not just today)
    tasks_all = get_tasks_for_employee(session['employee_id'], target_date=None)

    # open tasks = anything not completed/skipped
    open_tasks = [t for t in tasks_all if t.get("Status") not in ("COMPLETE", "SKIPPED")]

    # show due today OR overdue (simple autonomy)
    due_tasks = []
    for t in open_tasks:
        due = (t.get("Due_Date") or "").strip()
        if not due or due <= today:
            due_tasks.append(t)

    completed_today = [t for t in tasks_all
                      if t.get("Status") == "COMPLETE" and (t.get("Completed_At") or "").startswith(today)]

    notifs = [
    n for n in get_all_notifications(session["employee_id"], limit=30)
    if n.get("Type") == "TASK"
    and str(n.get("Is_Read", n.get("Read", "N"))).upper() not in ("Y", "YES", "TRUE", "1")
]




    return render_template(
        'tasks/my_tasks.html',
        today=date.today(),
        due_tasks=due_tasks,
        completed_today=completed_today,
        notifications=notifs
    )




@app.route('/tasks/<assignment_id>')
@login_required
def task_detail(assignment_id):
    assignment = get_task_assignment(assignment_id)
    if not assignment:
        flash('Task not found', 'error')
        return redirect(url_for('my_tasks'))

    # access control: employee sees own; manager sees all
    if session.get("role") not in ("Owner", "Admin", "Manager"):
        if assignment.get("Employee_ID") != session.get("employee_id"):
            flash("Access denied.", "error")
            return redirect(url_for("my_tasks"))

    tmpl = get_task(assignment.get("Task_ID"))
    events = get_task_events(assignment_id)

    return render_template('tasks/detail.html', assignment=assignment, tmpl=tmpl, events=events)


@app.route('/tasks/my/update-status', methods=['POST'])
@login_required
def my_tasks_update_status():
    data = request.get_json(silent=True) or {}

    assignment_id = (data.get('assignment_id') or "").strip()
    new_status = (data.get('status') or "").strip().upper()
    note = (data.get('note') or "").strip()
    skip_reason = (data.get('skip_reason') or "").strip()

    if new_status not in ('ACKNOWLEDGED', 'IN_PROGRESS', 'COMPLETE', 'SKIPPED'):
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    ok = update_task_status(
        assignment_id=assignment_id,
        new_status=new_status,
        employee_id=session['employee_id'],
        note=note,
        skip_reason=skip_reason
    )

    # Notify owner/manager (Assigned_By) when employee changes status
    if ok:
        a = get_task_assignment(assignment_id) or {}
        tmpl = get_task(a.get("Task_ID")) or {}
        title = tmpl.get("Title", "Task")

        assigned_by = (a.get("Assigned_By") or "").strip()
        if assigned_by:
            mgr = get_employee(assigned_by) or {"Employee_Name": "Manager"}
            msg = f"📣 Task update: {session.get('employee_name','Employee')} set '{title}' → {new_status}"
            if note:
                msg += f" — {note}"
            if new_status == "SKIPPED" and skip_reason:
                msg += f" (Reason: {skip_reason})"

            create_notification(assigned_by, mgr.get("Employee_Name", "Manager"), msg, "TASK")

    return jsonify({'success': bool(ok)})


# ==============================================================================
#                     PAYROLL
# ==============================================================================

@app.route('/payroll')
@manager_required
def payroll_dashboard():
    periods = get_pay_periods()
    active_emps = len([e for e in get_all_employees() if e.get('Status') == 'Active'])
    current_period = periods[0] if periods else None
    
    return render_template('payroll/dashboard.html',
        periods=periods, active_count=active_emps, current_period=current_period
    )


@app.route('/payroll/create-period', methods=['GET', 'POST'])
@manager_required
def create_pay_period_view():
    if request.method == 'POST':
        start = request.form.get('start_date')
        end = request.form.get('end_date')
        pay_date = request.form.get('pay_date')
        
        period_id = create_pay_period(start, end, pay_date, session['employee_id'])
        flash(f'Pay period created: {period_id}', 'success')
        return redirect(url_for('payroll_dashboard'))
    
    return render_template('payroll/create_period.html')


@app.route('/payroll/run', methods=['GET', 'POST'])
@manager_required
def run_payroll_view():
    periods = [p for p in get_pay_periods() if p.get('Status') != 'CLOSED']
    
    if request.method == 'POST':
        period_id = request.form.get('period_id')
        result = run_payroll(period_id, session['employee_id'])
        flash('Payroll processed', 'success')
        return redirect(url_for('payroll_dashboard'))
    
    return render_template('payroll/run.html', periods=periods)


@app.route('/payroll/my-history')
@login_required
def my_pay_history():
    history = get_employee_pay_history(session['employee_id'])
    return render_template('payroll/my_history.html', history=history)


# ==============================================================================
#                     REPORTS
# ==============================================================================

@app.route('/reports')
@manager_required
def reports():
    return render_template('reports/index.html')



def _safe_float(x, default=0.0):
    try:
        return float(str(x).replace("$", "").strip() or 0)
    except Exception:
        return default

def _safe_int(x, default=0):
    try:
        return int(float(str(x).strip() or 0))
    except Exception:
        return default

def _find_saleslog_file_for_date(base_dir: str, date_str: str) -> str | None:
    """
    Looks for: Sales_Logs/2025-12-17_Wednesday_SalesLog.csv (your naming style)
    Also accepts other variants containing date + 'SalesLog'.
    """
    sales_dir = os.path.join(base_dir, "Sales_Logs")
    patterns = [
        os.path.join(sales_dir, f"{date_str}_*SalesLog*.csv"),
        os.path.join(sales_dir, f"{date_str}*SalesLog*.csv"),
        os.path.join(sales_dir, f"*{date_str}*SalesLog*.csv"),
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat), reverse=True)
        if hits:
            return hits[0]
    return None

def _load_saleslog_rows(path: str) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def _compute_daily_sales_metrics(rows: list[dict]) -> dict:
    """
    Expects SalesLog columns like your uploaded file:
    Date, Transaction_ID, Quantity, Subtotal, Tax_Amount, Payment_Method,
    Category, SKU, Item_Name, COGS_Line, Gross_Margin, etc.
    """
    if not rows:
        return {
            "total_revenue": 0.0,
            "transaction_count": 0,
            "items_sold": 0,
            "total_cogs": 0.0,
            "gross_profit": 0.0,
            "gross_margin": 0.0,
            "sales_by_category": [],
            "payment_breakdown": [],
            "transactions": [],
            "top_items": [],
        }

    # Totals
    total_revenue = 0.0   # Subtotal (pre-tax)
    total_cogs = 0.0
    gross_profit = 0.0
    items_sold = 0
    tx_ids = set()

    # Groupings
    cat_map = {}       # category -> {"category":..., "qty":..., "revenue":...}
    pay_map = {}       # method -> {"method":..., "count": set(tx_ids), "total":...}
    tx_map = {}        # tx_id -> aggregated transaction
    item_map = {}      # sku -> aggregated item

    for r in rows:
        tx_id = (r.get("Transaction_ID") or "").strip()
        tx_ids.add(tx_id)

        qty = _safe_int(r.get("Quantity", 0))
        subtotal = _safe_float(r.get("Subtotal", 0))
        cogs_line = _safe_float(r.get("COGS_Line", 0))
        gm = r.get("Gross_Margin", "")
        gross_line = _safe_float(gm, subtotal - cogs_line)

        total_revenue += subtotal
        total_cogs += cogs_line
        gross_profit += gross_line
        items_sold += qty

        # Sales by Category
        cat = (r.get("Category") or "Uncategorized").strip() or "Uncategorized"
        c = cat_map.setdefault(cat, {"category": cat, "qty": 0, "revenue": 0.0})
        c["qty"] += qty
        c["revenue"] += subtotal

        # Payment breakdown (count unique tx)
        pm = (r.get("Payment_Method") or "CASH").strip().upper()
        p = pay_map.setdefault(pm, {"method": pm, "tx_ids": set(), "total": 0.0})
        if tx_id:
            p["tx_ids"].add(tx_id)
        p["total"] += subtotal

        # Transactions (aggregate line-items into one tx card)
        t = tx_map.setdefault(tx_id or f"UNKNOWN-{len(tx_map)+1}", {
            "transaction_id": tx_id or "UNKNOWN",
            "time": (r.get("Time") or r.get("Timestamp") or "").strip(),
            "items": 0,
            "payment_method": pm,
            "total": 0.0
        })
        t["items"] += qty
        t["total"] += subtotal
        if not t.get("time"):
            t["time"] = (r.get("Time") or r.get("Timestamp") or "").strip()

        # Top items
        sku = (r.get("SKU") or "").strip()
        name = (r.get("Item_Name") or "Unknown").strip()
        key = sku or name
        it = item_map.setdefault(key, {"sku": sku, "name": name, "qty": 0, "revenue": 0.0})
        it["qty"] += qty
        it["revenue"] += subtotal

    # Finish up
    transaction_count = len([x for x in tx_ids if x]) or len(tx_map)
    gross_margin = (gross_profit / total_revenue * 100.0) if total_revenue else 0.0

    sales_by_category = sorted(cat_map.values(), key=lambda x: x["revenue"], reverse=True)

    payment_breakdown = []
    for v in pay_map.values():
        payment_breakdown.append({
            "method": v["method"],
            "count": len(v["tx_ids"]) if v["tx_ids"] else 0,
            "total": v["total"]
        })
    payment_breakdown.sort(key=lambda x: x["total"], reverse=True)

    transactions = sorted(tx_map.values(), key=lambda x: x.get("time") or "", reverse=True)
    top_items = sorted(item_map.values(), key=lambda x: x["revenue"], reverse=True)

    return {
        "total_revenue": round(total_revenue, 2),
        "transaction_count": transaction_count,
        "items_sold": items_sold,
        "total_cogs": round(total_cogs, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_margin": round(gross_margin, 1),
        "sales_by_category": sales_by_category,
        "payment_breakdown": payment_breakdown,
        "transactions": transactions,
        "top_items": top_items,
    }

def _get_labor_for_date_stub(base_dir: str, date_str: str) -> tuple[list[dict], float, float]:
    """
    Replace this with your real Time_Clock/Payroll calc.
    For now: returns no employees, 0 hours, 0 payroll (so report still works).
    """
    return [], 0.0, 0.0

@app.route('/reports/daily')
@manager_required
def daily_report():
    # 1) Date selection
    report_date = (request.args.get("date") or date.today().isoformat()).strip()
    try:
        d = datetime.strptime(report_date, "%Y-%m-%d").date()
    except Exception:
        d = date.today()
        report_date = d.isoformat()

    prev_date = (d - timedelta(days=1)).isoformat()
    next_date = (d + timedelta(days=1)).isoformat()
    is_today = (d == date.today())

    # 2) Locate & load SalesLog
    base_dir = os.path.dirname(os.path.abspath(__file__))
    saleslog_path = _find_saleslog_file_for_date(base_dir, report_date)
    rows = _load_saleslog_rows(saleslog_path) if saleslog_path else []

    # 3) Compute sales metrics
    m = _compute_daily_sales_metrics(rows)

    # 4) Labor (stub for now — wire to Time_Clock next)
    employee_hours, total_hours, total_payroll = _get_labor_for_date_stub(base_dir, report_date)

    # 5) Net profit
    net_profit = (m["gross_profit"] - (total_payroll or 0.0))

    # 6) Render
    return render_template(
        "reports/daily.html",
        report_date=report_date,
        report_date_formatted=d.strftime("%B %d, %Y"),
        day_of_week=d.strftime("%A"),
        prev_date=prev_date,
        next_date=next_date,
        is_today=is_today,

        # Summary cards
        total_revenue=m["total_revenue"],
        transaction_count=m["transaction_count"],
        items_sold=m["items_sold"],
        total_cogs=m["total_cogs"],
        gross_profit=m["gross_profit"],
        gross_margin=m["gross_margin"],
        total_payroll=round(total_payroll or 0.0, 2),
        total_hours=round(total_hours or 0.0, 1),
        net_profit=round(net_profit, 2),

        # Tables/lists
        sales_by_category=m["sales_by_category"],
        payment_breakdown=m["payment_breakdown"],
        transactions=m["transactions"],
        employee_hours=employee_hours,
        top_items=m["top_items"],
    )

# ==============================================================================
#                     AI ASSISTANT
# ==============================================================================

@app.route('/ai')
@login_required
def ai_assistant():
    return render_template('ai/chat.html')


@app.route('/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    if not openai_client:
        return jsonify({'error': 'AI not configured. Set OPENAI_API_KEY in .env'}), 503
    
    message = request.json.get('message', '')
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant for {BUSINESS_NAME}, a nursery and pet store. Help with plant care, inventory questions, and store operations."},
                {"role": "user", "content": message}
            ],
            max_tokens=500
        )
        reply = response.choices[0].message.content
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==============================================================================
#                     MAIN
# ==============================================================================

if __name__ == '__main__':
    print(f"\n{'='*60}")
    print(f"  Mountain Gardens POS v{VERSION}")
    print(f"  http://localhost:5000")
    print(f"{'='*60}\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
