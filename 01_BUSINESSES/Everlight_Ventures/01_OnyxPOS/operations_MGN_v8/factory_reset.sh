#!/bin/bash
##############################################################################
# Mountain Gardens POS - Factory Reset Script
# Version: 1.0
# Purpose: Clean all transactional data while preserving system structure
##############################################################################

# ANSI color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "  Mountain Gardens POS - FACTORY RESET"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo -e "${YELLOW}WARNING: This will delete all transactional data!${NC}"
echo ""
echo "This script will:"
echo "  ${GREEN}✓${NC} Keep: Code, templates, and system structure"
echo "  ${GREEN}✓${NC} Keep: Employee accounts (optional)"
echo "  ${RED}✗${NC} Delete: All sales, inventory, receipts, time clock data"
echo "  ${RED}✗${NC} Delete: All reports, transactions, and audit logs"
echo ""

# Confirmation
read -p "Are you sure you want to continue? (type 'YES' to confirm): " confirm
if [ "$confirm" != "YES" ]; then
    echo -e "${BLUE}Aborted. No changes made.${NC}"
    exit 0
fi

# Ask about employee data
echo ""
read -p "Do you want to KEEP existing employee accounts? (y/n): " keep_employees

echo ""
echo "Starting factory reset..."
echo ""

# Create backup timestamp
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$SCRIPT_DIR/backups/factory_reset_$BACKUP_TIMESTAMP"

echo -e "${BLUE}Creating backup at: $BACKUP_DIR${NC}"
mkdir -p "$BACKUP_DIR"

##############################################################################
# BACKUP CRITICAL FILES
##############################################################################
echo ""
echo "📦 Backing up critical files..."

# Backup employee data
if [ -d "$SCRIPT_DIR/Employees" ]; then
    cp -r "$SCRIPT_DIR/Employees" "$BACKUP_DIR/" 2>/dev/null
    echo "  ✓ Employees backed up"
fi

# Backup vendor mapping (useful to keep)
if [ -f "$SCRIPT_DIR/Inventory/Vendor_Mapping.csv" ]; then
    mkdir -p "$BACKUP_DIR/Inventory"
    cp "$SCRIPT_DIR/Inventory/Vendor_Mapping.csv" "$BACKUP_DIR/Inventory/" 2>/dev/null
    echo "  ✓ Vendor mapping backed up"
fi

##############################################################################
# CLEAR TRANSACTIONAL DATA
##############################################################################
echo ""
echo "🗑️  Clearing transactional data..."

# Function to clear CSV files (keep headers)
clear_csv_keep_headers() {
    local file="$1"
    if [ -f "$file" ]; then
        # Keep only the header line
        head -n 1 "$file" > "${file}.tmp"
        mv "${file}.tmp" "$file"
        echo "  ✓ Cleared: $(basename $file)"
    fi
}

# Function to delete entire directory tree
delete_directory_tree() {
    local dir="$1"
    if [ -d "$dir" ]; then
        rm -rf "$dir"
        echo "  ✓ Deleted: $dir"
    fi
}

# 1. SALES DATA
echo ""
echo "Clearing Sales Data..."
delete_directory_tree "$SCRIPT_DIR/Sales_Logs"
mkdir -p "$SCRIPT_DIR/Sales_Logs"
echo "  ✓ Created fresh Sales_Logs directory"

# 2. TRANSACTION LOGS
echo ""
echo "Clearing Transaction Logs..."
delete_directory_tree "$SCRIPT_DIR/Transaction_Logs"
mkdir -p "$SCRIPT_DIR/Transaction_Logs"
echo "  ✓ Created fresh Transaction_Logs directory"

# 3. RECEIPTS
echo ""
echo "Clearing Receipts..."
delete_directory_tree "$SCRIPT_DIR/Receipts"
mkdir -p "$SCRIPT_DIR/Receipts"
echo "  ✓ Created fresh Receipts directory"

# 4. DAILY REPORTS
echo ""
echo "Clearing Daily Reports..."
delete_directory_tree "$SCRIPT_DIR/Daily_Reports"
mkdir -p "$SCRIPT_DIR/Daily_Reports"
echo "  ✓ Created fresh Daily_Reports directory"

# 5. TIME CLOCK DATA
echo ""
echo "Clearing Time Clock Data..."
delete_directory_tree "$SCRIPT_DIR/Time_Clock"
mkdir -p "$SCRIPT_DIR/Time_Clock"
if [ -f "$SCRIPT_DIR/Time_Clock/Time_Edits_Audit.csv" ]; then
    echo "Timestamp,Editor_ID,Editor_Name,Employee_ID,Employee_Name,Action,Old_Value,New_Value,Reason,IP_Address" > "$SCRIPT_DIR/Time_Clock/Time_Edits_Audit.csv"
fi
echo "  ✓ Created fresh Time_Clock directory"

# 6. TIME OFF REQUESTS
echo ""
echo "Clearing Time Off Requests..."
if [ -f "$SCRIPT_DIR/Time_Off_Requests/2025_TimeOffRequests.csv" ]; then
    clear_csv_keep_headers "$SCRIPT_DIR/Time_Off_Requests/2025_TimeOffRequests.csv"
fi

# 7. INVENTORY DATA
echo ""
echo "Clearing Inventory Data..."
clear_csv_keep_headers "$SCRIPT_DIR/Inventory/Items.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Inventory/Lots.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Inventory/Ledger.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Inventory/Invoice_Lines.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Inventory/Invoices_Log.csv"
# Keep Vendor_Mapping.csv - useful for new company

# 8. AUDIT LOGS
echo ""
echo "Clearing Audit Logs..."
clear_csv_keep_headers "$SCRIPT_DIR/Audit/Employee_Audit.csv"

# 9. NOTIFICATIONS
echo ""
echo "Clearing Notifications..."
clear_csv_keep_headers "$SCRIPT_DIR/Notifications/Employee_Notifications.csv"

# 10. TASKS
echo ""
echo "Clearing Tasks..."
clear_csv_keep_headers "$SCRIPT_DIR/Tasks/Tasks_Master.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Tasks/Task_Assignments.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Tasks/Task_Events.csv"

# 11. PAYROLL
echo ""
echo "Clearing Payroll Data..."
clear_csv_keep_headers "$SCRIPT_DIR/Payroll/2025_Payroll_Runs.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Payroll/Pay_Periods.csv"
clear_csv_keep_headers "$SCRIPT_DIR/Payroll/Deductions.csv"

# Handle Employee Pay Config based on choice
if [ "$keep_employees" = "y" ] || [ "$keep_employees" = "Y" ]; then
    echo "  ⊙ Keeping Employee_Pay_Config.csv (will need to configure for new employees)"
else
    clear_csv_keep_headers "$SCRIPT_DIR/Payroll/Employee_Pay_Config.csv"
fi

# 12. TILL/CASH DRAWER
echo ""
echo "Clearing Till Data..."
if [ -d "$SCRIPT_DIR/till" ]; then
    clear_csv_keep_headers "$SCRIPT_DIR/till/ledger.csv"
    clear_csv_keep_headers "$SCRIPT_DIR/till/till_ledger.csv"
    clear_csv_keep_headers "$SCRIPT_DIR/till/till_state.csv"
    # Remove daily till files
    rm -f "$SCRIPT_DIR/till/till_"*.csv 2>/dev/null
    echo "  ✓ Till data cleared"
fi

# 13. PRICING RULES (Optional - might want to keep)
echo ""
echo "Clearing Pricing Rules..."
clear_csv_keep_headers "$SCRIPT_DIR/Pricing/Pricing_Rules.csv"

##############################################################################
# HANDLE EMPLOYEE DATA
##############################################################################
echo ""
if [ "$keep_employees" = "y" ] || [ "$keep_employees" = "Y" ]; then
    echo -e "${GREEN}✓ Keeping employee accounts${NC}"
    echo "  Employee accounts preserved in Employees/Employee_Directory.csv"
else
    echo -e "${YELLOW}Creating fresh employee directory...${NC}"
    echo "Employee_ID,Employee_Name,Role,PIN,Status,Hire_Date,Phone,Email,Emergency_Contact,Last_Updated,Notes" > "$SCRIPT_DIR/Employees/Employee_Directory.csv"
    echo "  ✓ Empty employee directory created"
    echo ""
    echo -e "${YELLOW}⚠ NOTE: You'll need to create new employee accounts${NC}"
    echo "  Use the web interface at /employees/add or run seed_owner.py"
fi

##############################################################################
# CLEAR CACHE FILES
##############################################################################
echo ""
echo "Clearing cache files..."
rm -rf "$SCRIPT_DIR/__pycache__" 2>/dev/null
rm -rf "$SCRIPT_DIR/pos_core/__pycache__" 2>/dev/null
rm -f "$SCRIPT_DIR/employees.json" 2>/dev/null
echo "  ✓ Cache cleared"

##############################################################################
# COMPLETION
##############################################################################
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✓ FACTORY RESET COMPLETE${NC}"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Backup created at:"
echo "  $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "  1. Review the backup if needed"
echo "  2. Update business name in POS_CORE.py (BUSINESS_NAME variable)"
echo "  3. Configure tax rate in POS_CORE.py (TAX_RATE variable)"

if [ "$keep_employees" != "y" ] && [ "$keep_employees" != "Y" ]; then
    echo "  4. Create owner account: python3 seed_owner.py"
    echo "  5. Or use web interface: /employees/add"
else
    echo "  4. Reset employee PINs as needed via /employees"
fi

echo "  6. Start the POS: ./START_POS.sh (or python3 MGN_APP.py)"
echo "  7. Begin setting up inventory, pricing rules, etc."
echo ""
echo -e "${BLUE}The POS system is now ready for a fresh installation!${NC}"
echo ""
