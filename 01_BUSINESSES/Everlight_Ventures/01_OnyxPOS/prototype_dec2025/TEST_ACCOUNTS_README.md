# 🧪 OnyxPOS Test Accounts Guide

## ✅ What's Been Fixed

### 1. **Logout Button Added**
- ✓ Always visible in the top-right corner
- ✓ Shows your name and role
- ✓ One-click logout

### 2. **Employee Sales Tracking**
- ✓ Every sale automatically records which employee created it
- ✓ Stored in `cashier_id` field on transactions
- ✓ Can see who made each sale in reports

### 3. **Role-Based Access**
- ✓ Navigation menu adapts based on user role
- ✓ Different permissions for owner/manager/cashier/laborer
- ✓ Backend enforces permissions on all API endpoints

---

## 🔐 Test Accounts

All accounts are in the same business: **Import Test Shop 1767114825**
This business already has **10 inventory items** imported and ready to test with!

**Password for all accounts:** `Test123!`

### 👑 OWNER - Sarah Johnson
**Email:** `owner@test.com`

**Can Access:**
- ✅ Everything (full system access)
- ✅ Billing & Subscription Management
- ✅ Platform Revenue Dashboard
- ✅ Employee Management
- ✅ Payroll
- ✅ Analytics & Reports
- ✅ Sales & Inventory
- ✅ Schedule & Time Clock

**Navigation Items:**
- Dashboard, Sales, Inventory, Time Clock, Employees, Schedule, Analytics, Payroll, Settings, Billing, 💰 Your Profit

---

### 📊 MANAGER - Mike Davis
**Email:** `manager@test.com`

**Can Access:**
- ✅ Sales & Inventory Management
- ✅ Employee Management
- ✅ Schedule & Payroll
- ✅ Analytics & Reports
- ✅ Time Clock
- ❌ No Billing/Subscription access
- ❌ No Platform Revenue view

**Navigation Items:**
- Dashboard, Sales, Inventory, Time Clock, Employees, Schedule, Analytics, Payroll, Settings

---

### 💰 CASHIER - Emily Wilson
**Email:** `cashier@test.com`

**Can Access:**
- ✅ Sales Terminal (create sales)
- ✅ Inventory (view only)
- ✅ Time Clock (own hours)
- ✅ Dashboard (limited view)
- ❌ Cannot manage employees
- ❌ Cannot view analytics
- ❌ Cannot manage payroll

**Navigation Items:**
- Dashboard, Sales, Inventory, Time Clock, Settings

**Use Case:** Point-of-sale operations, checking stock levels

---

### 🔧 LABORER - Tom Brown
**Email:** `laborer@test.com`

**Can Access:**
- ✅ Time Clock (clock in/out)
- ✅ Schedule (view own schedule)
- ✅ Dashboard (very limited)
- ❌ No sales access
- ❌ No inventory access
- ❌ No employee management

**Navigation Items:**
- Dashboard, Time Clock, Schedule, Settings

**Use Case:** Warehouse/stock workers, general labor

---

## 🧪 Testing Steps

### Step 1: Hard Refresh Browser
Press `Ctrl + Shift + R` (or `Cmd + Shift + R` on Mac)

### Step 2: Logout Current Account
Click the **"Logout"** button in the top-right corner

### Step 3: Test Each Role

1. **Login as CASHIER** (`cashier@test.com` / `Test123!`)
   - ✓ Check you can see Sales Terminal
   - ✓ Make a test sale with the imported inventory
   - ✓ Verify your name appears as the cashier
   - ✓ Check you DON'T see Billing, Payroll, Analytics

2. **Logout and Login as MANAGER** (`manager@test.com` / `Test123!`)
   - ✓ Check you can see Payroll and Analytics
   - ✓ Verify you can manage employees
   - ✓ Check you DON'T see Billing or Platform Revenue

3. **Logout and Login as OWNER** (`owner@test.com` / `Test123!`)
   - ✓ Check you see ALL navigation items
   - ✓ Access Billing page
   - ✓ Access Platform Revenue page
   - ✓ View all analytics

4. **Logout and Login as LABORER** (`laborer@test.com` / `Test123!`)
   - ✓ Check you only see Dashboard, Time Clock, Schedule
   - ✓ Verify restricted access
   - ✓ Test time clock functionality

---

## 📝 What to Look For

### Sales Tracking
When you make a sale as a cashier:
1. The sale should show in Analytics (if you're owner/manager)
2. The transaction record includes who made the sale
3. Each employee's sales can be tracked separately

### Navigation Differences
- **Owner**: Sees 11 menu items (including Billing + Your Profit)
- **Manager**: Sees 9 menu items (including Payroll)
- **Cashier**: Sees 5 menu items (basics only)
- **Laborer**: Sees 4 menu items (minimal access)

### Permission Errors
If you try to access something you don't have permission for:
- Backend returns 403 Forbidden
- Should show clear error message
- Won't break the app

---

## 🐛 Known Issues / Future Enhancements

### To Be Added:
1. **Employee-specific dashboards** - Each role should see different dashboard metrics
2. **Sales by employee report** - Analytics showing which employee made which sales
3. **Time tracking integration** - Clock in/out tied to sales terminal
4. **Manager override** - Managers can approve/void transactions
5. **Custom role creation** - Define your own roles with specific permissions

---

## 🔧 Technical Details

### Database Fields
- `User.role`: owner | manager | cashier | laborer
- `Transaction.cashier_id`: Links to User who created the sale
- `User.tenant_id`: All employees belong to same business

### API Permission Decorators
```python
@require_role("owner", "manager")  # Only owners and managers
@require_role("owner")  # Owner only
@require_role("owner", "manager", "cashier")  # Not laborers
```

### Frontend Route Protection
- `OwnerRoute`: Only owners can access
- `ProtectedRoute`: Any authenticated user
- Role-based navigation menu filtering

---

## 📞 Support

If you find issues:
1. Check browser console for errors
2. Check backend logs: `tail -f /tmp/onyxpos.log`
3. Verify you're using the correct test account
4. Try hard refresh and clear browser cache

**All test accounts use the same business with shared inventory!**
