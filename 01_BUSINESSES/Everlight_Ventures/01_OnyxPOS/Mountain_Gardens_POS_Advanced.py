#!/usr/bin/env python3
"""
Mountain Gardens Nursery & Pet - Management System v5.0
Growing Naturally with You Since 1980

VERSION 5.0 FEATURES:
  - Visual Calendar Date Picker for Time Off Requests
  - Employee Password Protection for Clock In/Sales
  - Updated Animal Categories (Rat, Mouse, Cricket, Guinea Pig, etc.)
  - Product Name + Item Name fields in Sales
  - Modern 2025 UI with animations and better visuals
  - All data logged to spreadsheets
"""

import csv
import os
import platform
import subprocess
import random
import hashlib
import calendar
from datetime import datetime, date, timedelta
from pathlib import Path
import time
import sys

# ==== BUSINESS CONFIG ====
BUSINESS_NAME = "Mountain Gardens Nursery & Pet"
BUSINESS_ADDR_1 = "503 S. Curry Street"
BUSINESS_ADDR_2 = "Tehachapi, CA 93561"
BUSINESS_PHONE = "(661) 822-4960"
BUSINESS_SLOGAN = "Growing Naturally with You Since 1980"
BUSINESS_TAGLINE = "Your Family's Source for Quality Plants & Pet Care"

# ==== FILE PATHS ====
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "Sales_Logs"
RECEIPTS_DIR = SCRIPT_DIR / "Receipts"
TIMECLOCK_DIR = SCRIPT_DIR / "Time_Clock"
TIME_OFF_DIR = SCRIPT_DIR / "Time_Off_Requests"
EMPLOYEES_DIR = SCRIPT_DIR / "Employees"
REPORTS_DIR = SCRIPT_DIR / "Daily_Reports"
TRANSACTION_LOG_DIR = SCRIPT_DIR / "Transaction_Logs"

TAX_RATE = 0.0825
CURRENCY = "$"

# California Labor Law
CA_MEAL_BREAK_HOURS = 5
CA_REST_BREAK_HOURS = 4
CA_OVERTIME_HOURS = 8
CA_MIN_TIME_OFF_NOTICE = 14

# ==== CSV HEADERS ====
SALES_CSV_HEADERS = [
    "Date", "Time", "Transaction_ID", "Employee_ID", "Employee_Name",
    "Category", "Subcategory", "Product_Name", "Item_Name", "Quantity", "Size",
    "Item_Description", "Unit_Price", "Subtotal", "Tax_Rate", "Tax_Amount",
    "Line_Total", "Payment_Method", "Amount_Received", "Change_Due", "Notes"
]

TIMECLOCK_CSV_HEADERS = [
    "Date", "Time", "Employee_ID", "Employee_Name", "Punch_Type",
    "Break_Number", "Hours_Worked_Today", "Overtime_Hours", "Notes", "Timestamp"
]

EMPLOYEE_CSV_HEADERS = [
    "Employee_ID", "Employee_Name", "Password_Hash", "PIN", "Date_Added",
    "Status", "Role", "Phone", "Email", "Emergency_Contact", "Notes", "Last_Updated"
]

TIME_OFF_CSV_HEADERS = [
    "Request_ID", "Request_Date", "Employee_ID", "Employee_Name",
    "Start_Date", "End_Date", "Total_Days", "Reason", "Status",
    "Manager_Notes", "Approved_By", "Approved_Date"
]

TRANSACTION_LOG_HEADERS = [
    "Transaction_ID", "Date", "Time", "Employee_ID", "Employee_Name",
    "Total_Items", "Subtotal", "Tax", "Grand_Total", "Payment_Method",
    "Amount_Received", "Change_Given", "Receipt_Number", "Notes"
]

DAILY_SUMMARY_HEADERS = [
    "Date", "Total_Transactions", "Total_Revenue", "Total_Tax_Collected",
    "Cash_Sales", "Card_Sales", "Total_Items_Sold", "Animals_Sold",
    "Products_Sold", "Plants_Sold", "Total_Employee_Hours", "Total_Overtime",
    "Employees_Worked", "Generated_At"
]

# ==== CATEGORIES ====
MAIN_CATEGORIES = {"a": "Animal", "p": "Product", "l": "Plant"}

# UPDATED ANIMAL SUBCATEGORIES - Removed Dog/Cat, Added small animals
ANIMAL_SUBCATEGORIES = {
    "r": "Rat",
    "m": "Mouse",
    "c": "Cricket",
    "g": "Guinea Pig",
    "h": "Hamster",
    "b": "Bird",
    "f": "Fish",
    "p": "Reptile",
    "s": "Snake",
    "t": "Tarantula/Spider",
    "o": "Other Animal"
}

PRODUCT_SUBCATEGORIES = {
    "s": "Soil & Amendments", "f": "Fertilizer", "p": "Pots & Containers",
    "t": "Tools & Equipment", "d": "Decor & Garden Art",
    "c": "Chemicals & Pest Control", "w": "Watering & Irrigation",
    "e": "Pet Food & Supplies", "g": "Gift & Seasonal",
    "h": "Hardware & Misc", "o": "Other Product"
}

PLANT_SUBCATEGORIES = {
    "t": "Tree", "s": "Shrub", "r": "Rose", "p": "Perennial",
    "a": "Annual", "h": "Houseplant", "c": "Cactus & Succulent",
    "v": "Vine & Climber", "g": "Groundcover", "e": "Edible & Vegetable",
    "n": "Native Plant", "o": "Other Plant"
}

# ==== MOTIVATIONAL MESSAGES ====
CLOCK_IN_MESSAGES = [
    "Welcome! Let's make today amazing!",
    "Good to see you! The plants are happy you're here!",
    "Rise and shine! Ready to help customers?",
    "Welcome back! Let's grow some smiles!",
    "You're here! Time for garden magic!",
]

CLOCK_OUT_MESSAGES = [
    "Great job today! See you next time!",
    "Thanks for your hard work! Rest well!",
    "You did it! Enjoy your time off!",
    "Thanks for everything! Take care!",
]

BREAK_MESSAGES = [
    "Enjoy your break! You've earned it!",
    "Take a breather! Stretch those legs!",
    "Rest time! Recharge those batteries!",
]

LUNCH_MESSAGES = [
    "Lunch time! Enjoy your meal!",
    "Bon appetit! Take your full 30!",
    "Lunch break! Fuel up!",
]


# ==== UTILITY FUNCTIONS ====
def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def print_header(title):
    """Print a styled header."""
    print()
    print("  +" + "=" * 74 + "+")
    print("  |" + title.center(74) + "|")
    print("  +" + "=" * 74 + "+")


def print_subheader(title):
    """Print a styled subheader."""
    print()
    print("  +-" + "-" * 72 + "-+")
    print("  | " + title.ljust(72) + " |")
    print("  +-" + "-" * 72 + "-+")


def print_box(lines, width=50):
    """Print content in a box."""
    print()
    print("  +" + "-" * width + "+")
    for line in lines:
        print("  | " + line.ljust(width - 2) + " |")
    print("  +" + "-" * width + "+")


def print_success(msg):
    print(f"\n  [OK] {msg}\n")


def print_error(msg):
    print(f"\n  [ERROR] {msg}\n")


def print_info(msg):
    print(f"\n  [INFO] {msg}\n")


def print_warning(msg):
    print(f"\n  [WARNING] {msg}\n")


def print_canceled(msg):
    print(f"\n  [CANCELED] {msg}\n")


def loading_animation(text="Loading", duration=1):
    """Show a loading animation."""
    frames = ["|", "/", "-", "\\"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r  {frames[i % len(frames)]} {text}...")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r  [OK] {text}... Done!\n")


def generate_id(prefix=""):
    """Generate unique ID with timestamp."""
    return f"{prefix}{datetime.now().strftime('%Y%m%d%H%M%S')}"


def hash_password(password):
    """Hash a password for secure storage."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hash_value):
    """Verify a password against its hash."""
    return hash_password(password) == hash_value


def get_week_number(d):
    first_day = d.replace(day=1)
    return (d.day + first_day.weekday() - 1) // 7 + 1


def get_week_range(d):
    days_since_sun = (d.weekday() + 1) % 7
    start = d - timedelta(days=days_since_sun)
    end = start + timedelta(days=6)
    first = d.replace(day=1)
    if d.month == 12:
        last = d.replace(day=31)
    else:
        last = d.replace(month=d.month + 1, day=1) - timedelta(days=1)
    if start < first:
        start = first
    if end > last:
        end = last
    return f"{start.strftime('%b_%d')}-{end.strftime('%b_%d')}"


def get_folder(base, d):
    folder = base / str(d.year) / f"{d.month:02d}_{d.strftime('%B')}" / f"Week_{get_week_number(d)}_{get_week_range(d)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def ensure_csv(path, headers):
    """Ensure CSV file exists with headers."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(headers)
    return path


def append_to_csv(path, headers, row):
    """Append row to CSV, creating if needed."""
    ensure_csv(path, headers)
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


def read_csv(path):
    """Read all rows from CSV."""
    if not path.exists():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except:
        return []


def print_file_loc(path, label="File"):
    """Print file location in a box."""
    print()
    print("  +" + "=" * 74 + "+")
    print("  | " + label.ljust(72) + " |")
    print("  +" + "-" * 74 + "+")
    filepath = str(path.resolve())
    while filepath:
        print("  | " + filepath[:72].ljust(72) + " |")
        filepath = filepath[72:]
    print("  +" + "=" * 74 + "+")


def open_path(path):
    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        print_success("Opened!")
    except Exception as e:
        print_error(f"Could not open: {e}")


def input_with_cancel(prompt, allow_empty=False):
    """Get input with cancel option. Returns (value, canceled)."""
    raw = input(f"      {prompt}").strip()
    if raw.upper() in ('X', 'CANCEL'):
        return (None, True)
    if not allow_empty and not raw:
        return (None, False)
    return (raw, False)


def input_float_cancel(prompt):
    while True:
        val, canceled = input_with_cancel(prompt)
        if canceled:
            return (None, True)
        if val is None:
            print_error("Enter a valid number")
            continue
        try:
            return (float(val.replace("$", "").replace(",", "")), False)
        except:
            print_error("Enter a valid number (e.g., 9.99)")


def input_int_cancel(prompt):
    while True:
        val, canceled = input_with_cancel(prompt)
        if canceled:
            return (None, True)
        if val is None:
            print_error("Enter a whole number")
            continue
        try:
            return (int(val), False)
        except:
            print_error("Enter a whole number (e.g., 1, 2, 3)")


def confirm_cancel():
    print()
    print("  +------------------------------------------+")
    print("  |      CANCEL THIS TRANSACTION?           |")
    print("  +------------------------------------------+")
    print("  |    [Y]  Yes, cancel and discard         |")
    print("  |    [N]  No, continue                    |")
    print("  +------------------------------------------+")
    return input("\n      Confirm? (Y/N): ").strip().lower() == 'y'


# ==== FILE PATH FUNCTIONS ====
def get_employee_master_path():
    """Get the master employee directory spreadsheet."""
    EMPLOYEES_DIR.mkdir(parents=True, exist_ok=True)
    return ensure_csv(
        EMPLOYEES_DIR / "Employee_Directory.csv",
        EMPLOYEE_CSV_HEADERS
    )


def get_timeclock_path():
    """Get today's time clock spreadsheet."""
    today = date.today()
    folder = get_folder(TIMECLOCK_DIR, today)
    return ensure_csv(
        folder / f"{today.isoformat()}_{today.strftime('%A')}_TimeClockLog.csv",
        TIMECLOCK_CSV_HEADERS
    )


def get_sales_path():
    """Get today's sales spreadsheet."""
    today = date.today()
    folder = get_folder(DATA_DIR, today)
    return ensure_csv(
        folder / f"{today.isoformat()}_{today.strftime('%A')}_SalesLog.csv",
        SALES_CSV_HEADERS
    )


def get_transaction_log_path():
    """Get today's transaction log spreadsheet."""
    today = date.today()
    folder = get_folder(TRANSACTION_LOG_DIR, today)
    return ensure_csv(
        folder / f"{today.isoformat()}_{today.strftime('%A')}_TransactionLog.csv",
        TRANSACTION_LOG_HEADERS
    )


def get_time_off_path():
    """Get time off requests spreadsheet."""
    TIME_OFF_DIR.mkdir(parents=True, exist_ok=True)
    return ensure_csv(
        TIME_OFF_DIR / f"{date.today().year}_TimeOffRequests.csv",
        TIME_OFF_CSV_HEADERS
    )


def get_daily_summary_path():
    """Get daily summary spreadsheet."""
    today = date.today()
    folder = get_folder(REPORTS_DIR, today)
    return ensure_csv(
        folder / f"{today.isoformat()}_{today.strftime('%A')}_DailySummary.csv",
        DAILY_SUMMARY_HEADERS
    )


def get_receipt_path(trans_id):
    """Get receipt file path."""
    today = date.today()
    folder = get_folder(RECEIPTS_DIR, today)
    return folder / f"Receipt_{trans_id}.txt"


# ==== VISUAL CALENDAR DATE PICKER ====
def display_calendar(year, month, selected_day=None, min_date=None):
    """Display a visual calendar for date selection."""
    cal = calendar.Calendar(firstweekday=6)  # Sunday first
    month_name = calendar.month_name[month]

    print()
    print("  +--------------------------------------------+")
    print(f"  |  CALENDAR: {month_name} {year}".ljust(45) + "|")
    print("  +--------------------------------------------+")
    print("  |   Sun  Mon  Tue  Wed  Thu  Fri  Sat       |")
    print("  +--------------------------------------------+")

    weeks = cal.monthdayscalendar(year, month)
    today = date.today()

    for week in weeks:
        row = "  |  "
        for day in week:
            if day == 0:
                row += "     "
            else:
                current_date = date(year, month, day)

                # Check if date is selectable (after min_date)
                if min_date and current_date < min_date:
                    row += f"  x  "
                elif selected_day and day == selected_day:
                    row += f" [{day:2d}]"
                elif current_date == today:
                    row += f" ({day:2d})"
                else:
                    row += f"  {day:2d} "
        row = row.ljust(45) + "|"
        print(row)

    print("  +--------------------------------------------+")
    print("  |  ( ) = Today   [ ] = Selected   x = N/A   |")
    print("  +--------------------------------------------+")


def select_date_from_calendar(prompt="Select date", min_date=None):
    """Interactive calendar date picker."""
    if min_date is None:
        min_date = date.today() + timedelta(days=CA_MIN_TIME_OFF_NOTICE)

    current_year = min_date.year
    current_month = min_date.month
    selected_day = None

    while True:
        clear_screen()
        print_header(prompt)
        print(f"\n      Minimum date: {min_date.strftime('%B %d, %Y')} ({CA_MIN_TIME_OFF_NOTICE} days advance)")

        display_calendar(current_year, current_month, selected_day, min_date)

        print()
        print("  +------------------------------------------+")
        print("  |  NAVIGATION:                             |")
        print("  |    [<]  Previous Month                   |")
        print("  |    [>]  Next Month                       |")
        print("  |    [D]  Enter Day Number                 |")
        print("  |    [S]  Select & Confirm                 |")
        print("  |    [X]  Cancel                           |")
        print("  +------------------------------------------+")

        if selected_day:
            sel_date = date(current_year, current_month, selected_day)
            print(f"\n      Selected: {sel_date.strftime('%A, %B %d, %Y')}")

        choice = input("\n      Choice: ").strip().lower()

        if choice == '<':
            if current_month == 1:
                current_month = 12
                current_year -= 1
            else:
                current_month -= 1
            selected_day = None

        elif choice == '>':
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1
            selected_day = None

        elif choice == 'd':
            try:
                day = int(input("      Enter day number: "))
                max_day = calendar.monthrange(current_year, current_month)[1]
                if 1 <= day <= max_day:
                    check_date = date(current_year, current_month, day)
                    if check_date >= min_date:
                        selected_day = day
                    else:
                        print_error(f"Date must be on or after {min_date.strftime('%B %d, %Y')}")
                        input("      Press Enter...")
                else:
                    print_error(f"Invalid day. Enter 1-{max_day}")
                    input("      Press Enter...")
            except ValueError:
                print_error("Enter a valid number")
                input("      Press Enter...")

        elif choice == 's':
            if selected_day:
                return date(current_year, current_month, selected_day)
            else:
                print_error("Please select a day first (press D)")
                input("      Press Enter...")

        elif choice == 'x':
            return None

        else:
            # Try direct number input
            try:
                day = int(choice)
                max_day = calendar.monthrange(current_year, current_month)[1]
                if 1 <= day <= max_day:
                    check_date = date(current_year, current_month, day)
                    if check_date >= min_date:
                        selected_day = day
            except:
                pass


# ============================================================================
#              END OF PART 1 - COPY PART 2 BELOW THIS LINE
# ============================================================================
# ============================================================================
#              PART 2 - EMPLOYEE MANAGEMENT WITH PASSWORDS
# ============================================================================

def get_next_employee_id():
    """Get next available employee ID."""
    path = get_employee_master_path()
    rows = read_csv(path)
    if not rows:
        return "1001"
    try:
        max_id = max(int(r.get("Employee_ID", 1000)) for r in rows)
        return str(max_id + 1)
    except:
        return str(1001 + len(rows))


def add_employee():
    """Add new employee with password to master spreadsheet."""
    clear_screen()
    print_header("ADD NEW EMPLOYEE")

    name = input("\n      Full Name: ").strip()
    if not name:
        print_error("Name required!")
        return None

    # Password setup
    print()
    print("  +------------------------------------------+")
    print("  |  SET UP EMPLOYEE PASSWORD                |")
    print("  |  Password required for clock in/sales    |")
    print("  +------------------------------------------+")

    while True:
        password = input("\n      Enter password (min 4 chars): ").strip()
        if len(password) < 4:
            print_error("Password must be at least 4 characters")
            continue
        confirm = input("      Confirm password: ").strip()
        if password != confirm:
            print_error("Passwords don't match!")
            continue
        break

    # Optional 4-digit PIN for quick access
    print()
    pin = input("      Set 4-digit PIN (optional, Enter to skip): ").strip()
    if pin and (not pin.isdigit() or len(pin) != 4):
        print_warning("Invalid PIN format - skipping PIN setup")
        pin = ""

    emp_id = get_next_employee_id()

    print("\n      Optional info (press Enter to skip):")
    role = input("      Role/Position: ").strip() or "Team Member"
    phone = input("      Phone: ").strip() or ""
    email = input("      Email: ").strip() or ""
    emergency = input("      Emergency Contact: ").strip() or ""
    notes = input("      Notes: ").strip() or ""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    password_hash = hash_password(password)

    path = get_employee_master_path()
    append_to_csv(path, EMPLOYEE_CSV_HEADERS, [
        emp_id, name, password_hash, pin, now, "Active", role,
        phone, email, emergency, notes, now
    ])

    print()
    print("  +====================================================+")
    print("  |          EMPLOYEE ADDED SUCCESSFULLY!              |")
    print("  +----------------------------------------------------+")
    print(f"  |   ID:       {emp_id:<38} |")
    print(f"  |   Name:     {name:<38} |")
    print(f"  |   Role:     {role:<38} |")
    pin_display = "****" if pin else "Not Set"
    print(f"  |   PIN:      {pin_display:<38} |")
    print("  +----------------------------------------------------+")
    print("  |   Employee should remember their password!         |")
    print("  +====================================================+")

    print_file_loc(path, "Employee Directory")
    return emp_id


def list_employees():
    """Display all employees from master spreadsheet."""
    path = get_employee_master_path()
    rows = read_csv(path)

    clear_screen()
    print_header("EMPLOYEE DIRECTORY")

    if not rows:
        print_info("No employees registered yet.")
        print_file_loc(path, "Employee Directory")
        return

    print()
    print("  +========+==============================+================+==========+")
    print("  |   ID   |            NAME              |      ROLE      |  STATUS  |")
    print("  +========+==============================+================+==========+")

    for emp in rows:
        eid = emp.get("Employee_ID", "")[:6]
        name = emp.get("Employee_Name", "")[:28]
        role = emp.get("Role", "")[:14]
        status = emp.get("Status", "Active")[:8]
        status_mark = "[X]" if status == "Active" else "[ ]"
        print(f"  | {eid:<6} | {name:<28} | {role:<14} | {status_mark} {status:<4} |")

    print("  +========+==============================+================+==========+")

    print_file_loc(path, "Employee Directory Spreadsheet")


def get_employee(emp_id):
    """Get employee info by ID."""
    path = get_employee_master_path()
    rows = read_csv(path)
    for emp in rows:
        if emp.get("Employee_ID") == emp_id:
            return emp
    return None


def authenticate_employee(emp_id, for_action="access"):
    """Authenticate employee with password or PIN."""
    emp = get_employee(emp_id)
    if not emp:
        return None

    emp_name = emp.get("Employee_Name", "Unknown")
    password_hash = emp.get("Password_Hash", "")
    pin = emp.get("PIN", "")

    print()
    print("  +------------------------------------------+")
    print("  |  AUTHENTICATION REQUIRED                 |")
    print(f"  |  Employee: {emp_name:<28} |")
    print(f"  |  Action: {for_action:<30} |")
    print("  +------------------------------------------+")

    # Allow PIN or password
    if pin:
        print("\n      Enter PIN or Password:")
    else:
        print("\n      Enter Password:")

    attempts = 3
    while attempts > 0:
        entry = input("      >>> ").strip()

        # Check PIN first (if set)
        if pin and entry == pin:
            print_success(f"Welcome, {emp_name}!")
            return emp

        # Check password
        if verify_password(entry, password_hash):
            print_success(f"Welcome, {emp_name}!")
            return emp

        attempts -= 1
        if attempts > 0:
            print_error(f"Invalid credentials. {attempts} attempts remaining.")
        else:
            print_error("Too many failed attempts. Access denied.")
            return None

    return None


def select_and_authenticate_employee(for_action="access"):
    """Select employee and verify password."""
    path = get_employee_master_path()
    rows = read_csv(path)

    if not rows:
        print_warning("No employees registered!")
        if input("      Add employee now? (Y/N): ").lower() == 'y':
            emp_id = add_employee()
            if emp_id:
                emp = get_employee(emp_id)
                return emp_id, emp.get("Employee_Name", "Unknown")
        return None, None

    # Show employee list
    print()
    print("  +------------------------------------------+")
    print("  |           SELECT EMPLOYEE                |")
    print("  +------------------------------------------+")
    for emp in rows:
        if emp.get("Status", "Active") == "Active":
            eid = emp.get('Employee_ID', '')
            name = emp.get('Employee_Name', '')[:28]
            print(f"  |    ID: {eid:<6}  |  {name:<22} |")
    print("  +------------------------------------------+")

    emp_id = input("\n      Enter Employee ID: ").strip()

    emp = authenticate_employee(emp_id, for_action)
    if emp:
        return emp_id, emp.get("Employee_Name", "Unknown")

    return None, None


# ==== TIME CLOCK FUNCTIONS ====

def get_employee_punches_today(emp_id):
    """Get all punches for employee today from spreadsheet."""
    path = get_timeclock_path()
    rows = read_csv(path)
    return [r for r in rows if r.get("Employee_ID") == emp_id]


def calculate_hours_from_punches(punches):
    """Calculate hours worked from punch records."""
    total_minutes = 0
    clock_in_time = None

    for p in punches:
        punch_type = p.get("Punch_Type", "")
        time_str = p.get("Time", "")

        try:
            punch_time = datetime.strptime(time_str, "%H:%M:%S")
        except:
            continue

        if punch_type == "CLOCK_IN":
            clock_in_time = punch_time
        elif punch_type == "CLOCK_OUT" and clock_in_time:
            diff = (punch_time - clock_in_time).seconds / 60
            total_minutes += diff
            clock_in_time = None
        elif punch_type in ["BREAK_START", "LUNCH_START"] and clock_in_time:
            diff = (punch_time - clock_in_time).seconds / 60
            total_minutes += diff
            clock_in_time = None
        elif punch_type in ["BREAK_END", "LUNCH_END"]:
            clock_in_time = punch_time

    # If still clocked in, add time until now
    if clock_in_time:
        now = datetime.now()
        current = datetime(1900, 1, 1, now.hour, now.minute, now.second)
        diff = (current - clock_in_time).seconds / 60
        total_minutes += diff

    return round(total_minutes / 60, 2)


def get_current_status(punches):
    """Determine current clock status."""
    if not punches:
        return "NOT_CLOCKED_IN", 0, 0

    last_punch = punches[-1].get("Punch_Type", "")
    breaks = sum(1 for p in punches if p.get("Punch_Type") == "BREAK_END")
    lunches = sum(1 for p in punches if p.get("Punch_Type") == "LUNCH_END")

    if last_punch == "CLOCK_OUT":
        return "CLOCKED_OUT", breaks, lunches
    if last_punch == "BREAK_START":
        return "ON_BREAK", breaks, lunches
    if last_punch == "LUNCH_START":
        return "ON_LUNCH", breaks, lunches
    if last_punch in ["CLOCK_IN", "BREAK_END", "LUNCH_END"]:
        return "WORKING", breaks, lunches

    return "NOT_CLOCKED_IN", 0, 0


def record_punch(emp_id, emp_name, punch_type, break_num=0, notes=""):
    """Record a punch to the time clock spreadsheet."""
    path = get_timeclock_path()
    now = datetime.now()

    # Calculate hours
    punches = get_employee_punches_today(emp_id)
    hours = calculate_hours_from_punches(punches)
    overtime = max(0, hours - CA_OVERTIME_HOURS)

    row = [
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        emp_id,
        emp_name,
        punch_type,
        break_num if break_num else "",
        f"{hours:.2f}",
        f"{overtime:.2f}" if overtime > 0 else "0.00",
        notes,
        now.strftime("%Y-%m-%d %H:%M:%S")
    ]

    append_to_csv(path, TIMECLOCK_CSV_HEADERS, row)
    return hours, overtime


def time_clock_menu():
    """Main time clock interface with password authentication."""
    clear_screen()

    print_header("TIME CLOCK")

    now = datetime.now()
    print()
    print("  +----------------------------------------------------+")
    print(f"  |  Date: {now.strftime('%A, %B %d, %Y'):<40} |")
    print(f"  |  Time: {now.strftime('%I:%M:%S %p'):<40} |")
    print("  +----------------------------------------------------+")

    # Select and authenticate employee
    emp_id, emp_name = select_and_authenticate_employee("Clock In/Out")
    if not emp_id:
        input("\n      Press Enter to return...")
        return

    # Get current status from spreadsheet
    punches = get_employee_punches_today(emp_id)
    status, breaks, lunches = get_current_status(punches)
    hours = calculate_hours_from_punches(punches)
    overtime = max(0, hours - CA_OVERTIME_HOURS)

    tc_path = get_timeclock_path()

    # Status display
    print()
    print("  +========================================================+")
    print(f"  |  Employee: {emp_name:<44} |")
    print(f"  |  ID: {emp_id:<50} |")
    print("  +--------------------------------------------------------+")
    print(f"  |  Status: {status.replace('_', ' '):<46} |")
    print(f"  |  Hours Today: {hours:.2f}".ljust(57) + "|")
    if overtime > 0:
        print(f"  |  Overtime: {overtime:.2f} hrs".ljust(57) + "|")
    print(f"  |  Breaks: {breaks}/2   Lunch: {lunches}/1".ljust(57) + "|")
    print("  +========================================================+")

    # Handle based on current status
    if status == "CLOCKED_OUT":
        print_info("Already clocked out for today!")
        print_file_loc(tc_path, "Time Clock Log")
        input("\n      Press Enter to return...")
        return

    if status == "NOT_CLOCKED_IN":
        print()
        print("  +------------------------------------------+")
        print("  |           CLOCK IN                       |")
        print("  +------------------------------------------+")

        if input("\n      Clock IN now? (Y/N): ").lower() == 'y':
            loading_animation("Clocking in", 0.5)
            hours, ot = record_punch(emp_id, emp_name, "CLOCK_IN", notes="Shift started")
            msg = random.choice(CLOCK_IN_MESSAGES)

            print()
            print("  +========================================================+")
            print(f"  |  CLOCKED IN at {datetime.now().strftime('%I:%M %p')}".ljust(57) + "|")
            print("  +--------------------------------------------------------+")
            print(f"  |  {msg:<54} |")
            print("  +========================================================+")

            print_file_loc(tc_path, "Time Clock Log - PUNCH RECORDED")

    elif status == "ON_BREAK":
        print()
        print("  +------------------------------------------+")
        print("  |           END BREAK                      |")
        print("  +------------------------------------------+")

        if input("\n      End break? (Y/N): ").lower() == 'y':
            loading_animation("Ending break", 0.3)
            hours, ot = record_punch(emp_id, emp_name, "BREAK_END", breaks + 1, "Returned from break")
            print_success(f"Welcome back, {emp_name}! Break ended at {datetime.now().strftime('%I:%M %p')}")
            print_file_loc(tc_path, "Time Clock Log - PUNCH RECORDED")

    elif status == "ON_LUNCH":
        print()
        print("  +------------------------------------------+")
        print("  |           END LUNCH                      |")
        print("  +------------------------------------------+")

        if input("\n      End lunch? (Y/N): ").lower() == 'y':
            loading_animation("Ending lunch", 0.3)
            hours, ot = record_punch(emp_id, emp_name, "LUNCH_END", notes="Returned from lunch")
            print_success(f"Welcome back, {emp_name}! Lunch ended at {datetime.now().strftime('%I:%M %p')}")
            print_file_loc(tc_path, "Time Clock Log - PUNCH RECORDED")

    elif status == "WORKING":
        print()
        print("  +------------------------------------------+")
        print("  |           PUNCH OPTIONS                  |")
        print("  +------------------------------------------+")
        if breaks < 2:
            remaining = 2 - breaks
            print(f"  |    [B]  Take Break ({remaining} remaining)          |")
        if lunches < 1:
            print("  |    [L]  Take Lunch (30 min)              |")
        print("  |    [O]  Clock OUT                        |")
        print("  |    [C]  Cancel / Return                  |")
        print("  +------------------------------------------+")

        # CA Labor Law warnings
        if hours >= CA_MEAL_BREAK_HOURS and lunches == 0:
            print()
            print_warning(f"CA LAW: Meal break required after 5 hrs! ({hours:.1f} hrs worked)")

        if hours >= CA_REST_BREAK_HOURS * (breaks + 1) and breaks < 2:
            print_warning(f"Rest break recommended ({hours:.1f} hrs since last break)")

        choice = input("\n      Choice: ").lower()

        if choice == 'b' and breaks < 2:
            loading_animation("Starting break", 0.3)
            break_num = breaks + 1
            hours, ot = record_punch(emp_id, emp_name, "BREAK_START", break_num, f"Break {break_num} started")
            msg = random.choice(BREAK_MESSAGES)

            print()
            print("  +========================================================+")
            print(f"  |  BREAK started at {datetime.now().strftime('%I:%M %p')}".ljust(57) + "|")
            print("  +--------------------------------------------------------+")
            print(f"  |  {msg:<54} |")
            print("  |  10-minute paid rest break                             |")
            print("  +========================================================+")

            print_file_loc(tc_path, "Time Clock Log - BREAK RECORDED")

        elif choice == 'l' and lunches == 0:
            loading_animation("Starting lunch", 0.3)
            hours, ot = record_punch(emp_id, emp_name, "LUNCH_START", notes="Lunch break started")
            msg = random.choice(LUNCH_MESSAGES)

            print()
            print("  +========================================================+")
            print(f"  |  LUNCH started at {datetime.now().strftime('%I:%M %p')}".ljust(57) + "|")
            print("  +--------------------------------------------------------+")
            print(f"  |  {msg:<54} |")
            print("  |  30-minute unpaid meal break (CA Law)                  |")
            print("  +========================================================+")

            print_file_loc(tc_path, "Time Clock Log - LUNCH RECORDED")

        elif choice == 'o':
            # Clock out warnings
            if hours >= CA_MEAL_BREAK_HOURS and lunches == 0:
                print_warning("No meal break taken! CA requires meal break after 5 hours.")

            if input("\n      Clock OUT now? (Y/N): ").lower() == 'y':
                loading_animation("Clocking out", 0.5)
                hours, ot = record_punch(emp_id, emp_name, "CLOCK_OUT", notes="Shift ended")

                # Recalculate final hours
                punches = get_employee_punches_today(emp_id)
                final_hours = calculate_hours_from_punches(punches)
                final_ot = max(0, final_hours - CA_OVERTIME_HOURS)

                msg = random.choice(CLOCK_OUT_MESSAGES)

                print()
                print("  +========================================================+")
                print(f"  |  CLOCKED OUT at {datetime.now().strftime('%I:%M %p')}".ljust(57) + "|")
                print("  +--------------------------------------------------------+")
                print(f"  |  Total Hours: {final_hours:.2f}".ljust(57) + "|")
                if final_ot > 0:
                    print(f"  |  Overtime: {final_ot:.2f} hours".ljust(57) + "|")
                lunch_str = "Yes" if lunches > 0 else "No"
                print(f"  |  Breaks: {breaks}   Lunch: {lunch_str}".ljust(57) + "|")
                print("  +--------------------------------------------------------+")
                print(f"  |  {msg:<54} |")
                print("  +========================================================+")

                print_file_loc(tc_path, "Time Clock Log - CLOCK OUT RECORDED")

        elif choice == 'c':
            return

    input("\n      Press Enter to continue...")


def view_timeclock_log():
    """View today's time clock spreadsheet."""
    path = get_timeclock_path()
    rows = read_csv(path)

    clear_screen()
    print_header(f"TIME CLOCK LOG - {date.today().strftime('%B %d, %Y')}")

    if not rows:
        print_info("No time clock entries today.")
    else:
        print()
        print("  +----------+--------+--------------------+---------------+--------+")
        print("  |   TIME   |   ID   |        NAME        |    PUNCH      | HOURS  |")
        print("  +----------+--------+--------------------+---------------+--------+")

        for r in rows:
            time_str = r.get("Time", "")[:8]
            emp_id = r.get("Employee_ID", "")[:6]
            name = r.get("Employee_Name", "")[:18]
            punch = r.get("Punch_Type", "").replace("_", " ")[:13]
            hours = r.get("Hours_Worked_Today", "0")[:6]

            print(f"  | {time_str:<8} | {emp_id:<6} | {name:<18} | {punch:<13} | {hours:<6} |")

        print("  +----------+--------+--------------------+---------------+--------+")

    print_file_loc(path, "Time Clock Spreadsheet")

    if input("\n      Open spreadsheet? (Y/N): ").lower() == 'y':
        open_path(path)


# ==== TIME OFF REQUESTS ====

def request_time_off():
    """Submit time off request with visual calendar picker."""
    clear_screen()

    print_header("REQUEST TIME OFF")

    min_date = date.today() + timedelta(days=CA_MIN_TIME_OFF_NOTICE)

    print()
    print("  +------------------------------------------------------------+")
    print(f"  |  California requires {CA_MIN_TIME_OFF_NOTICE} days advance notice".ljust(61) + "|")
    print(f"  |  Earliest available: {min_date.strftime('%B %d, %Y')}".ljust(61) + "|")
    print("  +------------------------------------------------------------+")

    # Select and authenticate employee
    emp_id, emp_name = select_and_authenticate_employee("Request Time Off")
    if not emp_id:
        input("\n      Press Enter to return...")
        return

    # Use calendar picker for START date
    print_info("Select START date from calendar...")
    input("      Press Enter to open calendar...")

    start_date = select_date_from_calendar("Select START Date", min_date)
    if not start_date:
        print_canceled("Request cancelled.")
        input("\n      Press Enter...")
        return

    # Use calendar picker for END date
    print_info("Select END date from calendar...")
    input("      Press Enter to open calendar...")

    end_date = select_date_from_calendar("Select END Date", start_date)
    if not end_date:
        print_canceled("Request cancelled.")
        input("\n      Press Enter...")
        return

    if end_date < start_date:
        print_error("End date cannot be before start date!")
        input("\n      Press Enter...")
        return

    total_days = (end_date - start_date).days + 1

    # Select reason
    clear_screen()
    print_header("SELECT REASON")

    print()
    print("  +------------------------------------------+")
    print("  |    [V]  Vacation                         |")
    print("  |    [P]  Personal                         |")
    print("  |    [S]  Sick / Medical                   |")
    print("  |    [F]  Family                           |")
    print("  |    [O]  Other                            |")
    print("  +------------------------------------------+")

    reasons = {'v': 'Vacation', 'p': 'Personal', 's': 'Sick/Medical', 'f': 'Family', 'o': 'Other'}
    reason = reasons.get(input("\n      Choice: ").lower(), 'Other')

    # Generate request ID
    request_id = f"PTO{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Confirmation display
    clear_screen()
    print_header("CONFIRM TIME OFF REQUEST")

    print()
    print("  +============================================================+")
    print("  |                    REQUEST SUMMARY                         |")
    print("  +------------------------------------------------------------+")
    print(f"  |  Request ID:  {request_id:<44} |")
    print(f"  |  Employee:    {emp_name:<44} |")
    print(f"  |  ID:          {emp_id:<44} |")
    print("  +------------------------------------------------------------+")
    print(f"  |  Start:  {start_date.strftime('%A, %B %d, %Y'):<49} |")
    print(f"  |  End:    {end_date.strftime('%A, %B %d, %Y'):<49} |")
    print(f"  |  Days:   {total_days:<49} |")
    print(f"  |  Reason: {reason:<49} |")
    print("  +============================================================+")

    if input("\n      Submit request? (Y/N): ").lower() == 'y':
        path = get_time_off_path()

        row = [
            request_id,
            date.today().strftime("%Y-%m-%d"),
            emp_id,
            emp_name,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            total_days,
            reason,
            "PENDING",
            "",
            "",
            ""
        ]

        loading_animation("Submitting request", 0.5)
        append_to_csv(path, TIME_OFF_CSV_HEADERS, row)

        print()
        print("  +============================================================+")
        print("  |         REQUEST SUBMITTED SUCCESSFULLY!                    |")
        print("  +------------------------------------------------------------+")
        print("  |  Status: PENDING                                           |")
        print("  |  A manager will review your request.                       |")
        print("  +============================================================+")

        print_file_loc(path, "Time Off Requests Spreadsheet")
    else:
        print_canceled("Request cancelled.")

    input("\n      Press Enter...")


def view_time_off():
    """View time off requests spreadsheet."""
    path = get_time_off_path()
    rows = read_csv(path)

    clear_screen()
    print_header("TIME OFF REQUESTS")

    if not rows:
        print_info("No time off requests on file.")
    else:
        print()
        print("  +------------------+------------+------------+------+------------+----------+")
        print("  |       NAME       |   START    |    END     | DAYS |   REASON   |  STATUS  |")
        print("  +------------------+------------+------------+------+------------+----------+")

        for r in rows:
            name = r.get("Employee_Name", "")[:16]
            start = r.get("Start_Date", "")[:10]
            end = r.get("End_Date", "")[:10]
            days = r.get("Total_Days", "")[:4]
            reason = r.get("Reason", "")[:10]
            status = r.get("Status", "")[:8]
            print(f"  | {name:<16} | {start:<10} | {end:<10} | {days:<4} | {reason:<10} | {status:<8} |")

        print("  +------------------+------------+------------+------+------------+----------+")

    print_file_loc(path, "Time Off Requests Spreadsheet")

    if input("\n      Open spreadsheet? (Y/N): ").lower() == 'y':
        open_path(path)

    input("\n      Press Enter...")


# ============================================================================
#              END OF PART 2 - COPY PART 3 BELOW THIS LINE
# ============================================================================
# ============================================================================
#              PART 3 - SALES, REPORTS & MAIN MENU
# ============================================================================

def select_category():
    """Select main category."""
    print()
    print("  +--------------------------------------------------+")
    print("  |              SELECT CATEGORY                     |")
    print("  +--------------------------------------------------+")
    print("  |    [A]  Animal                                   |")
    print("  |    [P]  Product                                  |")
    print("  |    [L]  Plant                                    |")
    print("  +--------------------------------------------------+")
    print("  |    [X]  CANCEL TRANSACTION                       |")
    print("  +--------------------------------------------------+")

    while True:
        c = input("\n      (A/P/L/X): ").lower()
        if c == 'x':
            return None, True
        if c in MAIN_CATEGORIES:
            return MAIN_CATEGORIES[c], False
        print_error("Invalid choice")


def select_subcategory(cat):
    """Select subcategory with updated animal options."""
    if cat == "Animal":
        opts = ANIMAL_SUBCATEGORIES
        print()
        print("  +--------------------------------------------------+")
        print("  |           SELECT ANIMAL TYPE                     |")
        print("  +--------------------------------------------------+")
        print("  |    [R]  Rat                                      |")
        print("  |    [M]  Mouse                                    |")
        print("  |    [C]  Cricket                                  |")
        print("  |    [G]  Guinea Pig                               |")
        print("  |    [H]  Hamster                                  |")
        print("  |    [B]  Bird                                     |")
        print("  |    [F]  Fish                                     |")
        print("  |    [P]  Reptile                                  |")
        print("  |    [S]  Snake                                    |")
        print("  |    [T]  Tarantula/Spider                         |")
        print("  |    [O]  Other Animal                             |")
        print("  +--------------------------------------------------+")
        print("  |    [X]  CANCEL                                   |")
        print("  +--------------------------------------------------+")

    elif cat == "Product":
        opts = PRODUCT_SUBCATEGORIES
        print()
        print("  +--------------------------------------------------+")
        print("  |           SELECT PRODUCT TYPE                    |")
        print("  +--------------------------------------------------+")
        print("  |    [S]  Soil & Amendments                        |")
        print("  |    [F]  Fertilizer                               |")
        print("  |    [P]  Pots & Containers                        |")
        print("  |    [T]  Tools & Equipment                        |")
        print("  |    [D]  Decor & Garden Art                       |")
        print("  |    [C]  Chemicals & Pest Control                 |")
        print("  |    [W]  Watering & Irrigation                    |")
        print("  |    [E]  Pet Food & Supplies                      |")
        print("  |    [G]  Gift & Seasonal                          |")
        print("  |    [H]  Hardware & Misc                          |")
        print("  |    [O]  Other Product                            |")
        print("  +--------------------------------------------------+")
        print("  |    [X]  CANCEL                                   |")
        print("  +--------------------------------------------------+")

    else:  # Plant
        opts = PLANT_SUBCATEGORIES
        print()
        print("  +--------------------------------------------------+")
        print("  |           SELECT PLANT TYPE                      |")
        print("  +--------------------------------------------------+")
        print("  |    [T]  Tree                                     |")
        print("  |    [S]  Shrub                                    |")
        print("  |    [R]  Rose                                     |")
        print("  |    [P]  Perennial                                |")
        print("  |    [A]  Annual                                   |")
        print("  |    [H]  Houseplant                               |")
        print("  |    [C]  Cactus & Succulent                       |")
        print("  |    [V]  Vine & Climber                           |")
        print("  |    [G]  Groundcover                              |")
        print("  |    [E]  Edible & Vegetable                       |")
        print("  |    [N]  Native Plant                             |")
        print("  |    [O]  Other Plant                              |")
        print("  +--------------------------------------------------+")
        print("  |    [X]  CANCEL                                   |")
        print("  +--------------------------------------------------+")

    while True:
        c = input("\n      Choice: ").lower()
        if c == 'x':
            return None, True
        if c in opts:
            return opts[c], False
        print_error("Invalid choice")


def get_item_details(cat, subcat):
    """Get item details including Product Name and Item Name."""
    print()
    print(f"  +--------------------------------------------------+")
    print(f"  |  {cat} > {subcat}".ljust(51) + "|")
    print(f"  +--------------------------------------------------+")

    # Product Name (brand/type)
    product_name, canceled = input_with_cancel("Product/Brand Name: ")
    if canceled:
        return None, None, None, True
    product_name = product_name or subcat

    # Item Name (specific item)
    item_name, canceled = input_with_cancel("Item Name: ")
    if canceled:
        return None, None, None, True
    item_name = item_name or f"Unknown {subcat}"

    # Description
    desc, canceled = input_with_cancel("Description (optional): ", True)
    if canceled:
        return None, None, None, True

    return product_name, item_name, desc or item_name, False


def change_breakdown(amt):
    """Calculate change breakdown."""
    if amt <= 0:
        return {}
    denoms = [(100, "$100"), (50, "$50"), (20, "$20"), (10, "$10"), (5, "$5"), (1, "$1"),
              (.25, "Quarters"), (.10, "Dimes"), (.05, "Nickels"), (.01, "Pennies")]
    result = {}
    for val, nm in denoms:
        cnt = int(amt / val)
        if cnt:
            result[nm] = cnt
            amt = round(amt - cnt * val, 2)
    return result


def generate_receipt(items, subtot, tax, total, method, recv, change,
                     emp_id, emp_name, comment, dt, tm, trans_id):
    """Generate receipt text."""
    lines = [
        "=" * 58,
        "",
        BUSINESS_NAME.center(58),
        BUSINESS_ADDR_1.center(58),
        BUSINESS_ADDR_2.center(58),
        BUSINESS_PHONE.center(58),
        "",
        "-" * 58,
        BUSINESS_SLOGAN.center(58),
        "-" * 58,
        "",
        "=" * 58,
        f"  Transaction: {trans_id}",
        f"  Date: {dt}    Time: {tm}",
        f"  Cashier: {emp_name} (ID: {emp_id})",
        "-" * 58
    ]

    for i in items:
        lines.append(f"  [{i['category']} > {i['subcategory']}]")
        lines.append(f"  {i['product_name']} - {i['item_name']}")
        size_str = f" ({i['size']})" if i['size'] else ""
        lines.append(f"    {i['quantity']}x @ ${i['unit_price']:.2f}{size_str}")
        lines.append(f"    Subtotal: ${i['subtotal']:.2f}  Tax: ${i['tax_amount']:.2f}  Total: ${i['line_total']:.2f}")
        lines.append("")

    lines.extend([
        "-" * 58,
        f"  {'Subtotal:':<20} ${subtot:>12.2f}",
        f"  {'Tax (8.25%):':<20} ${tax:>12.2f}",
        "=" * 58,
        f"  {'TOTAL:':<20} ${total:>12.2f}",
        "-" * 58,
        f"  {'Paid (' + method + '):':<20} ${recv:>12.2f}",
        f"  {'Change:':<20} ${change:>12.2f}"
    ])

    if comment:
        lines.extend(["-" * 58, f"  Note: {comment}"])

    lines.extend([
        "",
        "=" * 58,
        "",
        BUSINESS_TAGLINE.center(58),
        "Thank you for your business!".center(58),
        ""
    ])

    return "\n".join(lines)


def record_sale():
    """Record a sale with employee authentication."""
    clear_screen()

    print_header("NEW SALE")
    print("\n      Type X anytime to CANCEL transaction")

    # Select and authenticate cashier
    print()
    print("  +------------------------------------------+")
    print("  |       SELECT CASHIER (Employee Login)    |")
    print("  +------------------------------------------+")

    emp_id, emp_name = select_and_authenticate_employee("Process Sale")
    if not emp_id:
        print_canceled("No cashier authenticated - sale cancelled.")
        input("\n      Press Enter...")
        return

    print_success(f"Cashier: {emp_name} (ID: {emp_id})")

    # Generate transaction ID
    trans_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"

    items = []
    item_num = 1

    while True:
        print()
        print("  +------------------------------------------+")
        item_label = f"  ITEM {item_num}"
        print(f"  |{item_label.center(42)}|")
        print("  +------------------------------------------+")

        if item_num > 1:
            print()
            print("  +------------------------------------------+")
            print("  |    [Y]  Add another item                 |")
            print("  |    [N]  Done - proceed to payment        |")
            print("  |    [X]  Cancel entire transaction        |")
            print("  +------------------------------------------+")

            c = input("\n      Choice: ").lower()
            if c == 'x':
                if confirm_cancel():
                    print_canceled("Transaction cancelled - nothing saved.")
                    input("\n      Press Enter...")
                    return
                continue
            if c != 'y':
                break

        cat, canceled = select_category()
        if canceled:
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
            continue

        subcat, canceled = select_subcategory(cat)
        if canceled:
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
            continue

        product_name, item_name, desc, canceled = get_item_details(cat, subcat)
        if canceled:
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
            continue

        qty, canceled = input_int_cancel("Quantity: ")
        if canceled:
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
            continue

        size, canceled = input_with_cancel("Size (optional): ", True)
        if canceled:
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
            continue
        size = size or ""

        price, canceled = input_float_cancel("Unit Price: $")
        if canceled:
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
            continue

        subtotal = price * qty
        tax_amt = round(subtotal * TAX_RATE, 2)
        line_tot = round(subtotal + tax_amt, 2)

        items.append({
            "category": cat, "subcategory": subcat,
            "product_name": product_name, "item_name": item_name,
            "quantity": qty, "size": size, "desc": desc, "unit_price": price,
            "subtotal": subtotal, "tax_amount": tax_amt, "line_total": line_tot
        })

        print()
        print_success(f"Added: {qty}x {product_name} - {item_name} = ${line_tot:.2f}")
        item_num += 1

    if not items:
        print_canceled("No items - sale cancelled.")
        input("\n      Press Enter...")
        return

    # Calculate totals
    inv_sub = sum(i["subtotal"] for i in items)
    inv_tax = sum(i["tax_amount"] for i in items)
    inv_tot = round(sum(i["line_total"] for i in items), 2)

    # Invoice summary
    clear_screen()
    print_header("INVOICE SUMMARY")

    print()
    print("  +========================================================================+")
    print(f"  |  Transaction: {trans_id}".ljust(73) + "|")
    print(f"  |  Cashier: {emp_name} (ID: {emp_id})".ljust(73) + "|")
    print("  +------------------------------------------------------------------------+")

    for i in items:
        line = f"  |  {i['quantity']}x {i['product_name'][:20]} - {i['item_name'][:25]}"
        print(f"{line:<60} ${i['line_total']:>10.2f} |")

    print("  +------------------------------------------------------------------------+")
    print(f"  |  {'Subtotal:':<55} ${inv_sub:>10.2f} |")
    print(f"  |  {'Tax (8.25%):':<55} ${inv_tax:>10.2f} |")
    print("  +========================================================================+")
    print(f"  |  {'TOTAL:':<55} ${inv_tot:>10.2f} |")
    print("  +========================================================================+")

    # Payment
    print()
    print("  +------------------------------------------+")
    print("  |    [C]  Cash                             |")
    print("  |    [D]  Card                             |")
    print("  |    [X]  Cancel                           |")
    print("  +------------------------------------------+")

    while True:
        pay = input("\n      Payment method: ").lower()
        if pay == 'x':
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
            continue
        if pay in ('c', 'cash'):
            method = 'Cash'
            break
        if pay in ('d', 'card'):
            method = 'Card'
            break
        print_error("Enter C, D, or X")

    if method == 'Card':
        received = inv_tot
        change = 0.0
        print_success(f"Card payment: ${received:.2f}")
    else:
        received, canceled = input_float_cancel("Cash received: $")
        if canceled:
            if confirm_cancel():
                print_canceled("Transaction cancelled - nothing saved.")
                input("\n      Press Enter...")
                return
        change = round(received - inv_tot, 2)
        if change > 0:
            print()
            print("  +------------------------------------------+")
            print(f"  |  CHANGE DUE: ${change:.2f}".ljust(43) + "|")
            print("  +------------------------------------------+")
            for d, c in change_breakdown(change).items():
                print(f"  |     {d}: {c}".ljust(43) + "|")
            print("  +------------------------------------------+")
        elif change < 0:
            print_warning(f"SHORT ${abs(change):.2f}!")

    comment, _ = input_with_cancel("Note (optional): ", True)
    comment = comment or ""

    # === SAVE EVERYTHING TO SPREADSHEETS ===
    now = datetime.now()
    dt_str = now.strftime("%Y-%m-%d")
    tm_str = now.strftime("%H:%M:%S")

    loading_animation("Saving transaction", 0.5)

    # 1. Save to SALES LOG (item details) - with Product_Name field
    sales_path = get_sales_path()
    for i in items:
        row = [
            dt_str, tm_str, trans_id, emp_id, emp_name,
            i["category"], i["subcategory"], i["product_name"], i["item_name"],
            i["quantity"], i["size"], i["desc"],
            f"{i['unit_price']:.2f}", f"{i['subtotal']:.2f}",
            f"{TAX_RATE:.4f}", f"{i['tax_amount']:.2f}", f"{i['line_total']:.2f}",
            "", "", "", ""
        ]
        append_to_csv(sales_path, SALES_CSV_HEADERS, row)

    # Add invoice total row
    total_row = [
        dt_str, tm_str, trans_id, emp_id, emp_name,
        "", "", "=== INVOICE TOTAL ===", "",
        len(items), "", "",
        f"{inv_sub:.2f}", f"{TAX_RATE:.4f}", f"{inv_tax:.2f}", f"{inv_tot:.2f}",
        method, f"{received:.2f}", f"{change:.2f}", comment
    ]
    append_to_csv(sales_path, SALES_CSV_HEADERS, total_row)
    append_to_csv(sales_path, SALES_CSV_HEADERS, [""] * len(SALES_CSV_HEADERS))

    # 2. Save to TRANSACTION LOG
    trans_path = get_transaction_log_path()
    trans_row = [
        trans_id, dt_str, tm_str, emp_id, emp_name,
        len(items), f"{inv_sub:.2f}", f"{inv_tax:.2f}", f"{inv_tot:.2f}",
        method, f"{received:.2f}", f"{change:.2f}",
        trans_id, comment
    ]
    append_to_csv(trans_path, TRANSACTION_LOG_HEADERS, trans_row)

    # 3. Save RECEIPT
    receipt_path = get_receipt_path(trans_id)
    receipt_text = generate_receipt(
        items, inv_sub, inv_tax, inv_tot, method, received, change,
        emp_id, emp_name, comment, dt_str, tm_str, trans_id
    )

    try:
        with receipt_path.open("w", encoding="utf-8") as f:
            f.write(receipt_text)
    except Exception as e:
        print_error(f"Could not save receipt: {e}")

    # Success display
    print()
    print("  +========================================================================+")
    print("  |                    TRANSACTION COMPLETED!                             |")
    print("  +------------------------------------------------------------------------+")
    print(f"  |  Transaction ID:  {trans_id:<52} |")
    print(f"  |  Employee ID:     {emp_id:<52} |")
    print(f"  |  Employee Name:   {emp_name:<52} |")
    print(f"  |  Total:           ${inv_tot:.2f}".ljust(73) + "|")
    print(f"  |  Payment:         {method:<52} |")
    print("  +------------------------------------------------------------------------+")
    print("  |  DATA SAVED TO:                                                       |")
    print("  |     - Sales Log                                                       |")
    print("  |     - Transaction Log                                                 |")
    print("  |     - Receipt                                                         |")
    print("  +========================================================================+")

    # Print receipt?
    if input("\n      Print receipt? (Y/N): ").lower() == 'y':
        try:
            if platform.system() == "Windows":
                os.startfile(receipt_path, "print")
            else:
                subprocess.run(["lpr", str(receipt_path)])
            print_success("Sent to printer!")
        except:
            print_error("Could not print")

    input("\n      Press Enter to continue...")


# ==== DAILY REPORTS ====

def generate_daily_summary():
    """Generate comprehensive daily summary."""
    clear_screen()

    print_header(f"DAILY SUMMARY REPORT - {date.today().strftime('%B %d, %Y')}")

    loading_animation("Generating report", 1)

    # === SALES DATA ===
    trans_path = get_transaction_log_path()
    trans_rows = read_csv(trans_path)

    total_trans = len(trans_rows)
    total_revenue = 0
    total_tax = 0
    cash_sales = 0
    card_sales = 0

    for r in trans_rows:
        try:
            amt = float(r.get("Grand_Total", 0))
            tax = float(r.get("Tax", 0))
            total_revenue += amt
            total_tax += tax
            if r.get("Payment_Method", "").lower() == "cash":
                cash_sales += amt
            else:
                card_sales += amt
        except:
            pass

    # === ITEM COUNTS ===
    sales_path = get_sales_path()
    sales_rows = read_csv(sales_path)

    total_items = 0
    animals = products = plants = 0

    for r in sales_rows:
        if r.get("Item_Name") and not r.get("Product_Name", "").startswith("==="):
            try:
                qty = int(r.get("Quantity", 0))
                total_items += qty
                cat = r.get("Category", "")
                if cat == "Animal":
                    animals += qty
                elif cat == "Product":
                    products += qty
                elif cat == "Plant":
                    plants += qty
            except:
                pass

    # === TIME CLOCK DATA ===
    tc_path = get_timeclock_path()
    tc_rows = read_csv(tc_path)

    employee_hours = {}
    total_overtime = 0

    for r in tc_rows:
        if r.get("Punch_Type") == "CLOCK_OUT":
            emp_name = r.get("Employee_Name", "")
            try:
                hours = float(r.get("Hours_Worked_Today", 0))
                ot = float(r.get("Overtime_Hours", 0))
                employee_hours[emp_name] = hours
                total_overtime += ot
            except:
                pass

    total_emp_hours = sum(employee_hours.values())
    employees_worked = len(employee_hours)

    # Display Summary
    print()
    print("  +========================================================================+")
    print("  |                         SALES SUMMARY                                 |")
    print("  +------------------------------------------------------------------------+")
    print(f"  |  Total Transactions:".ljust(50) + f"{total_trans:>20}  |")
    print(f"  |  Total Items Sold:".ljust(50) + f"{total_items:>20}  |")
    print("  +------------------------------------------------------------------------+")
    print(f"  |  Total Revenue:".ljust(50) + f"${total_revenue:>19.2f}  |")
    print(f"  |  Tax Collected:".ljust(50) + f"${total_tax:>19.2f}  |")
    print("  +------------------------------------------------------------------------+")
    print(f"  |  Cash Sales:".ljust(50) + f"${cash_sales:>19.2f}  |")
    print(f"  |  Card Sales:".ljust(50) + f"${card_sales:>19.2f}  |")
    print("  +========================================================================+")
    print("  |                      CATEGORY BREAKDOWN                               |")
    print("  +------------------------------------------------------------------------+")
    print(f"  |  Animals Sold:".ljust(50) + f"{animals:>20}  |")
    print(f"  |  Products Sold:".ljust(50) + f"{products:>20}  |")
    print(f"  |  Plants Sold:".ljust(50) + f"{plants:>20}  |")
    print("  +========================================================================+")
    print("  |                      TIME CLOCK SUMMARY                               |")
    print("  +------------------------------------------------------------------------+")
    print(f"  |  Employees Worked:".ljust(50) + f"{employees_worked:>20}  |")
    print(f"  |  Total Hours:".ljust(50) + f"{total_emp_hours:>20.2f}  |")
    print(f"  |  Total Overtime:".ljust(50) + f"{total_overtime:>20.2f}  |")

    if employee_hours:
        print("  +------------------------------------------------------------------------+")
        print("  |  Employee Hours:                                                      |")
        for emp, hrs in employee_hours.items():
            print(f"  |     {emp:<30} {hrs:>8.2f} hrs".ljust(73) + "|")

    print("  +========================================================================+")

    # Save to summary spreadsheet
    summary_path = get_daily_summary_path()

    summary_row = [
        date.today().strftime("%Y-%m-%d"),
        total_trans,
        f"{total_revenue:.2f}",
        f"{total_tax:.2f}",
        f"{cash_sales:.2f}",
        f"{card_sales:.2f}",
        total_items,
        animals,
        products,
        plants,
        f"{total_emp_hours:.2f}",
        f"{total_overtime:.2f}",
        employees_worked,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]

    append_to_csv(summary_path, DAILY_SUMMARY_HEADERS, summary_row)

    print_success("Daily summary saved!")

    print("\n  TODAY'S SPREADSHEETS:")
    print(f"     - Sales Log:       {get_sales_path().name}")
    print(f"     - Transactions:    {get_transaction_log_path().name}")
    print(f"     - Time Clock:      {get_timeclock_path().name}")
    print(f"     - Daily Summary:   {summary_path.name}")

    if input("\n      Open all spreadsheets? (Y/N): ").lower() == 'y':
        open_path(get_sales_path())
        time.sleep(0.3)
        open_path(get_transaction_log_path())
        time.sleep(0.3)
        open_path(get_timeclock_path())
        time.sleep(0.3)
        open_path(summary_path)

    input("\n      Press Enter to continue...")


def show_all_files():
    """Show all file locations."""
    clear_screen()

    print_header("FILE LOCATIONS")

    print()
    print("  +========================================================================+")
    print(f"  |  Main Folder: {str(SCRIPT_DIR)[:55]}".ljust(73) + "|")
    print("  +------------------------------------------------------------------------+")
    print("  |                                                                        |")
    print("  |  Mountain_Gardens_Sales/                                               |")
    print("  |  |                                                                     |")
    print("  |  +-- Mountain_Gardens_POS.py                                           |")
    print("  |  +-- README.txt                                                        |")
    print("  |  |                                                                     |")
    print("  |  +-- Employees/                                                        |")
    print("  |  |   +-- Employee_Directory.csv  (Master List)                         |")
    print("  |  |                                                                     |")
    print("  |  +-- Sales_Logs/YYYY/MM/Week/                                          |")
    print("  |  +-- Transaction_Logs/YYYY/MM/Week/                                    |")
    print("  |  +-- Time_Clock/YYYY/MM/Week/                                          |")
    print("  |  +-- Daily_Reports/YYYY/MM/Week/                                       |")
    print("  |  +-- Receipts/YYYY/MM/Week/                                            |")
    print("  |  +-- Time_Off_Requests/                                                |")
    print("  |                                                                        |")
    print("  +========================================================================+")

    print("\n  Each day creates NEW files - data is NEVER overwritten!")

    if input("\n      Open main folder? (Y/N): ").lower() == 'y':
        open_path(SCRIPT_DIR)

    input("\n      Press Enter to continue...")


# ==== MAIN MENU ====

def main():
    """Main program entry."""

    # Ensure all directories exist
    get_sales_path()
    get_timeclock_path()
    get_employee_master_path()
    get_transaction_log_path()

    while True:
        clear_screen()

        now = datetime.now()

        # Header
        print()
        print("  +========================================================================+")
        print("  |                                                                        |")
        print(f"  |{BUSINESS_NAME.center(72)}|")
        print(f"  |{BUSINESS_SLOGAN.center(72)}|")
        print("  |                                                                        |")
        print("  |                    MANAGEMENT SYSTEM v5.0                              |")
        print("  |                                                                        |")
        print("  +========================================================================+")

        # Date/Time
        print()
        print(f"      Date: {now.strftime('%A, %B %d, %Y')}")
        print(f"      Time: {now.strftime('%I:%M:%S %p')}")

        # Menu
        print()
        print("  +========================================================================+")
        print("  |                           MAIN MENU                                   |")
        print("  +========================================================================+")
        print("  |                                                                        |")
        print("  |    ==================  SALES  ==================                       |")
        print("  |    [1]  New Sale                                                       |")
        print("  |    [2]  View Sales Log                                                 |")
        print("  |    [3]  View Transactions                                              |")
        print("  |                                                                        |")
        print("  |    ================  TIME CLOCK  ================                      |")
        print("  |    [4]  Clock In/Out                                                   |")
        print("  |    [5]  View Time Clock Log                                            |")
        print("  |                                                                        |")
        print("  |    ================  TIME OFF  ==================                      |")
        print("  |    [6]  Request Time Off                                               |")
        print("  |    [7]  View Time Off Requests                                         |")
        print("  |                                                                        |")
        print("  |    ==================  ADMIN  ==================                       |")
        print("  |    [8]  Manage Employees                                               |")
        print("  |    [9]  Daily Summary Report                                           |")
        print("  |    [0]  File Locations                                                 |")
        print("  |                                                                        |")
        print("  |    [Q]  Quit                                                           |")
        print("  |                                                                        |")
        print("  +========================================================================+")

        cmd = input("\n      Enter choice: ").strip().lower()

        if cmd == '1':
            record_sale()
        elif cmd == '2':
            path = get_sales_path()
            print_file_loc(path, "Sales Log")
            if input("      Open? (Y/N): ").lower() == 'y':
                open_path(path)
            input("\n      Press Enter...")
        elif cmd == '3':
            path = get_transaction_log_path()
            print_file_loc(path, "Transaction Log")
            if input("      Open? (Y/N): ").lower() == 'y':
                open_path(path)
            input("\n      Press Enter...")
        elif cmd == '4':
            time_clock_menu()
        elif cmd == '5':
            view_timeclock_log()
        elif cmd == '6':
            request_time_off()
        elif cmd == '7':
            view_time_off()
        elif cmd == '8':
            clear_screen()
            print_header("EMPLOYEE MANAGEMENT")
            print()
            print("  +------------------------------------------+")
            print("  |    [A]  Add New Employee                 |")
            print("  |    [V]  View All Employees               |")
            print("  |    [O]  Open Employee Spreadsheet        |")
            print("  |    [B]  Back to Menu                     |")
            print("  +------------------------------------------+")

            c = input("\n      Choice: ").lower()
            if c == 'a':
                add_employee()
                input("\n      Press Enter...")
            elif c == 'v':
                list_employees()
                input("\n      Press Enter...")
            elif c == 'o':
                open_path(get_employee_master_path())
                input("\n      Press Enter...")
        elif cmd == '9':
            generate_daily_summary()
        elif cmd == '0':
            show_all_files()
        elif cmd == 'q':
            clear_screen()
            print()
            print("  +========================================================================+")
            print("  |                                                                        |")
            print("  |            Thank you for using Mountain Gardens POS!                   |")
            print("  |                                                                        |")
            print(f"  |{BUSINESS_TAGLINE.center(72)}|")
            print("  |                                                                        |")
            print("  |                        Have a great day!                               |")
            print("  |                                                                        |")
            print("  +========================================================================+")
            print()
            break
        else:
            print_error("Invalid choice. Enter 0-9 or Q.")
            time.sleep(1)


if __name__ == "__main__":
    main()
