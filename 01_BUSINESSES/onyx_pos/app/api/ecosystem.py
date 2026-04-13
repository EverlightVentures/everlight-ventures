"""
Onyx POS -- Ecosystem Engine
The Operating System for Neighborhood Commerce

Contains business logic for:
1. Vendor Bill Scanner (expense-side CV)
2. Receipt Lottery (viral gamification)
3. Smart Pricing (demand-based suggestions)
4. Earned Wage Access (payroll advance)
5. Neighborhood Commerce Network (cross-promo)
6. Dead Stock Marketplace (B2B wholesale)
"""
import hashlib
import secrets
import string
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
import json

from db import supabase


# ============================================================
# 1. VENDOR BILL SCANNER
# ============================================================

def _guess_expense_category(text: str) -> str:
    """Auto-categorize a vendor bill based on OCR text."""
    t = text.lower()
    if any(k in t for k in ["electric", "gas", "water", "utility", "power", "internet", "phone"]):
        return "utilities"
    if any(k in t for k in ["rent", "lease", "property"]):
        return "rent"
    if any(k in t for k in ["food", "produce", "meat", "dairy", "beverage", "coffee", "grocery"]):
        return "food_bev"
    if any(k in t for k in ["clean", "repair", "maintenance", "plumb", "hvac"]):
        return "services"
    if any(k in t for k in ["equipment", "machine", "tool", "hardware"]):
        return "equipment"
    if any(k in t for k in ["advertis", "marketing", "promo", "sign", "print"]):
        return "marketing"
    if any(k in t for k in ["inventory", "wholesale", "bulk", "case", "pallet"]):
        return "inventory"
    return "supplies"


def save_vendor_bill(tenant_id: str, scan_result: dict, employee_id: str = None) -> dict:
    """Save a scanned vendor bill to the database."""
    category = _guess_expense_category(scan_result.get("raw_text", ""))

    record = supabase.table("onyx_vendor_bills").insert({
        "tenant_id": tenant_id,
        "vendor_name": scan_result.get("vendor"),
        "extracted_data": json.dumps(scan_result),
        "raw_ocr_text": scan_result.get("raw_text", ""),
        "confidence_score": scan_result.get("confidence", 0),
        "subtotal": scan_result.get("subtotal"),
        "tax_amount": scan_result.get("tax"),
        "total_amount": scan_result.get("total"),
        "expense_category": category,
    }).execute()

    return record.data[0]


# ============================================================
# 2. RECEIPT LOTTERY
# ============================================================

def _generate_lottery_code() -> str:
    """Generate a unique 8-character alphanumeric lottery code."""
    chars = string.ascii_uppercase + string.digits
    # Format: XXXX-XXXX (easy to read on receipts)
    part1 = "".join(secrets.choice(chars) for _ in range(4))
    part2 = "".join(secrets.choice(chars) for _ in range(4))
    return f"{part1}-{part2}"


def create_lottery_entry(tenant_id: str, transaction_id: str, transaction_total: float) -> dict:
    """Create a lottery code for a transaction.

    Win probability and prize amount are configured per tenant.
    The lottery fund is funded by 0.1% of each transaction.
    """
    # Get tenant lottery config
    tenant = supabase.table("onyx_tenants").select(
        "lottery_enabled, lottery_fund_pct, lottery_fund_balance, lottery_win_rate"
    ).eq("id", tenant_id).single().execute()

    if not tenant.data.get("lottery_enabled", False):
        return None

    fund_pct = float(tenant.data.get("lottery_fund_pct", 0.001))
    fund_balance = float(tenant.data.get("lottery_fund_balance", 0))
    win_rate = float(tenant.data.get("lottery_win_rate", 0.05))

    # Add to fund (0.1% of this transaction)
    contribution = round(transaction_total * fund_pct, 2)
    new_balance = fund_balance + contribution

    # Determine if this is a winner
    is_winner = secrets.randbelow(1000) < int(win_rate * 1000)

    # Prize amount (if winner): random between $1 and min($100, fund balance)
    prize_amount = 0.0
    if is_winner and new_balance >= 1.0:
        max_prize = min(100.0, new_balance * 0.5)  # Never drain more than half the fund
        prize_amount = round(max(1.0, secrets.randbelow(int(max_prize * 100)) / 100), 2)
        new_balance -= prize_amount

    # Generate unique code
    code = _generate_lottery_code()

    # Save
    entry = supabase.table("onyx_lottery_codes").insert({
        "tenant_id": tenant_id,
        "transaction_id": transaction_id,
        "lottery_code": code,
        "is_winner": is_winner and prize_amount > 0,
        "prize_amount": prize_amount,
        "prize_type": "store_credit",
    }).execute()

    # Update fund balance
    supabase.table("onyx_tenants").update({
        "lottery_fund_balance": new_balance,
    }).eq("id", tenant_id).execute()

    return {
        "lottery_code": code,
        "is_winner": is_winner and prize_amount > 0,
        "prize_amount": prize_amount if (is_winner and prize_amount > 0) else None,
        "message": "You won! Show this code to redeem your store credit." if (is_winner and prize_amount > 0) else "Better luck next time! Check back after your next purchase.",
    }


def check_lottery_code(code: str) -> dict:
    """Check if a lottery code is a winner."""
    result = supabase.table("onyx_lottery_codes").select("*").eq(
        "lottery_code", code.upper().strip()
    ).single().execute()

    if not result.data:
        return {"valid": False, "message": "Invalid lottery code."}

    entry = result.data
    if entry["redeemed"]:
        return {"valid": True, "is_winner": entry["is_winner"], "redeemed": True,
                "message": "This code has already been redeemed."}

    now = datetime.now(timezone.utc)
    if entry.get("expires_at") and datetime.fromisoformat(entry["expires_at"].replace("Z", "+00:00")) < now:
        return {"valid": True, "is_winner": entry["is_winner"], "expired": True,
                "message": "This code has expired."}

    return {
        "valid": True,
        "is_winner": entry["is_winner"],
        "prize_amount": float(entry["prize_amount"]) if entry["is_winner"] else 0,
        "prize_type": entry["prize_type"],
        "redeemed": False,
        "message": f"Winner! ${entry['prize_amount']} store credit!" if entry["is_winner"] else "Not a winner this time.",
    }


def redeem_lottery_code(code: str, transaction_id: str = None) -> dict:
    """Redeem a winning lottery code."""
    result = supabase.table("onyx_lottery_codes").select("*").eq(
        "lottery_code", code.upper().strip()
    ).single().execute()

    if not result.data:
        return {"success": False, "message": "Invalid code."}

    entry = result.data
    if not entry["is_winner"]:
        return {"success": False, "message": "This code is not a winner."}
    if entry["redeemed"]:
        return {"success": False, "message": "Already redeemed."}

    supabase.table("onyx_lottery_codes").update({
        "redeemed": True,
        "redeemed_at": datetime.now(timezone.utc).isoformat(),
        "redeemed_transaction_id": transaction_id,
    }).eq("id", entry["id"]).execute()

    return {
        "success": True,
        "prize_amount": float(entry["prize_amount"]),
        "message": f"Redeemed! ${entry['prize_amount']} applied as store credit.",
    }


# ============================================================
# 3. SMART PRICING ENGINE
# ============================================================

def generate_pricing_suggestions(tenant_id: str) -> list[dict]:
    """Analyze sales data and generate pricing suggestions.

    Looks at:
    - Day-of-week patterns (sell more on Sat? raise price)
    - Time-of-day patterns (morning rush vs afternoon lull)
    - Inventory levels (low stock = raise, high stock = discount to move)
    - Velocity trends (slowing sales = consider promo)
    """
    # Get last 30 days of sales
    since = (datetime.utcnow() - timedelta(days=30)).isoformat()
    items = supabase.table("onyx_line_items").select(
        "product_id, product_name, quantity, unit_price, line_total, created_at"
    ).eq("tenant_id", tenant_id).gte("created_at", since).execute()

    if not items.data or len(items.data) < 10:
        return []  # Not enough data

    # Get current products with stock
    products = supabase.table("onyx_products").select(
        "id, name, unit_price, stock_quantity, reorder_point"
    ).eq("tenant_id", tenant_id).eq("is_active", True).execute()

    product_map = {p["id"]: p for p in products.data}

    # Aggregate by product
    product_sales = {}
    for item in items.data:
        pid = item.get("product_id") or item["product_name"]
        if pid not in product_sales:
            product_sales[pid] = {
                "name": item["product_name"],
                "total_qty": 0,
                "total_revenue": 0,
                "prices": [],
                "by_day": {},  # day_of_week -> qty
            }
        ps = product_sales[pid]
        ps["total_qty"] += item["quantity"]
        ps["total_revenue"] += item["line_total"]
        ps["prices"].append(item["unit_price"])

        # Day of week analysis
        try:
            dt = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            dow = dt.strftime("%A")
            ps["by_day"][dow] = ps["by_day"].get(dow, 0) + item["quantity"]
        except (ValueError, TypeError):
            pass

    suggestions = []

    for pid, data in product_sales.items():
        if data["total_qty"] < 3:
            continue  # Not enough sales for this product

        current_price = data["prices"][-1] if data["prices"] else 0
        avg_price = sum(data["prices"]) / len(data["prices"])

        # --- Day-of-week demand surge ---
        if data["by_day"]:
            avg_daily = data["total_qty"] / max(len(data["by_day"]), 1)
            for day, qty in data["by_day"].items():
                if qty > avg_daily * 1.3:  # 30%+ above average
                    surge_pct = ((qty / avg_daily) - 1) * 100
                    suggested = round(current_price * 1.10, 2)  # 10% bump
                    change_pct = round(((suggested - current_price) / current_price) * 100, 2) if current_price else 0

                    suggestions.append({
                        "product_id": pid if pid in product_map else None,
                        "product_name": data["name"],
                        "current_price": current_price,
                        "suggested_price": suggested,
                        "price_change_pct": change_pct,
                        "reason": f"Sells {surge_pct:.0f}% more on {day}s -- raise price ${current_price:.2f} → ${suggested:.2f} on {day}s",
                        "trigger_type": "day_of_week",
                        "confidence": min(0.85, surge_pct / 100),
                        "data_points": {"day": day, "qty": qty, "avg": round(avg_daily, 1)},
                    })
                    break  # One suggestion per product

        # --- Inventory-based pricing ---
        if pid in product_map:
            prod = product_map[pid]
            stock = prod.get("stock_quantity")
            reorder = prod.get("reorder_point", 5)

            if stock is not None:
                if stock <= reorder and data["total_qty"] > 5:
                    # Low stock, high demand → raise price
                    suggested = round(current_price * 1.15, 2)
                    change_pct = round(((suggested - current_price) / current_price) * 100, 2) if current_price else 0
                    suggestions.append({
                        "product_id": pid,
                        "product_name": data["name"],
                        "current_price": current_price,
                        "suggested_price": suggested,
                        "price_change_pct": change_pct,
                        "reason": f"Only {stock} left in stock with strong demand ({data['total_qty']} sold in 30d). Raise price to protect margin.",
                        "trigger_type": "inventory_low",
                        "confidence": 0.75,
                        "data_points": {"stock": stock, "sold_30d": data["total_qty"]},
                    })
                elif stock > reorder * 5 and data["total_qty"] < 5:
                    # High stock, low demand → discount to move
                    suggested = round(current_price * 0.85, 2)
                    change_pct = round(((suggested - current_price) / current_price) * 100, 2) if current_price else 0
                    suggestions.append({
                        "product_id": pid,
                        "product_name": data["name"],
                        "current_price": current_price,
                        "suggested_price": suggested,
                        "price_change_pct": change_pct,
                        "reason": f"Overstocked ({stock} units) with only {data['total_qty']} sold in 30 days. Discount 15% to move inventory.",
                        "trigger_type": "inventory_high",
                        "confidence": 0.70,
                        "data_points": {"stock": stock, "sold_30d": data["total_qty"]},
                    })

    # Save suggestions to database
    for s in suggestions[:20]:  # Max 20 suggestions per run
        supabase.table("onyx_pricing_suggestions").insert({
            "tenant_id": tenant_id,
            "product_id": s["product_id"],
            "product_name": s["product_name"],
            "current_price": s["current_price"],
            "suggested_price": s["suggested_price"],
            "price_change_pct": s["price_change_pct"],
            "reason": s["reason"],
            "trigger_type": s["trigger_type"],
            "confidence": s["confidence"],
            "data_points": json.dumps(s["data_points"]),
        }).execute()

    return suggestions[:20]


# ============================================================
# 4. EARNED WAGE ACCESS
# ============================================================

def calculate_earned_wages(tenant_id: str, employee_id: str) -> dict:
    """Calculate how much an employee has earned in the current pay period."""
    # Get employee info
    emp = supabase.table("onyx_employees").select(
        "hourly_rate, full_name"
    ).eq("id", employee_id).eq("tenant_id", tenant_id).single().execute()

    if not emp.data or not emp.data.get("hourly_rate"):
        return {"error": "Employee not found or no hourly rate set"}

    hourly_rate = float(emp.data["hourly_rate"])

    # Get tenant pay period config
    tenant = supabase.table("onyx_tenants").select(
        "wage_access_enabled, wage_advance_max_pct, default_pay_period"
    ).eq("id", tenant_id).single().execute()

    if not tenant.data.get("wage_access_enabled", False):
        return {"error": "Earned wage access not enabled for this business"}

    # Determine pay period
    pay_period = tenant.data.get("default_pay_period", "biweekly")
    today = date.today()

    if pay_period == "weekly":
        # Current week (Mon-Sun)
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)
    elif pay_period == "biweekly":
        # Approximate biweekly from start of year
        year_start = date(today.year, 1, 1)
        weeks_elapsed = (today - year_start).days // 7
        biweek_num = weeks_elapsed // 2
        period_start = year_start + timedelta(weeks=biweek_num * 2)
        period_end = period_start + timedelta(days=13)
    else:  # monthly
        period_start = today.replace(day=1)
        next_month = period_start + timedelta(days=32)
        period_end = next_month.replace(day=1) - timedelta(days=1)

    # Get hours worked this period
    punches = supabase.table("onyx_time_punches").select("*").eq(
        "tenant_id", tenant_id
    ).eq("employee_id", employee_id).gte(
        "punched_at", f"{period_start}T00:00:00"
    ).lte(
        "punched_at", f"{period_end}T23:59:59"
    ).order("punched_at").execute()

    # Calculate hours from clock_in/clock_out pairs
    total_hours = 0.0
    clock_in_time = None

    for punch in punches.data:
        if punch["punch_type"] == "clock_in":
            clock_in_time = datetime.fromisoformat(punch["punched_at"].replace("Z", "+00:00"))
        elif punch["punch_type"] == "clock_out" and clock_in_time:
            clock_out_time = datetime.fromisoformat(punch["punched_at"].replace("Z", "+00:00"))
            hours = (clock_out_time - clock_in_time).total_seconds() / 3600
            total_hours += hours
            clock_in_time = None

    # If currently clocked in, add hours so far
    if clock_in_time:
        hours_so_far = (datetime.now(timezone.utc) - clock_in_time).total_seconds() / 3600
        total_hours += hours_so_far

    earned = round(total_hours * hourly_rate, 2)
    max_advance_pct = float(tenant.data.get("wage_advance_max_pct", 0.50))
    max_advance = round(earned * max_advance_pct, 2)

    # Check existing advances this period
    existing = supabase.table("onyx_wage_advances").select("advance_amount").eq(
        "tenant_id", tenant_id
    ).eq("employee_id", employee_id).gte(
        "pay_period_start", period_start.isoformat()
    ).neq("status", "denied").execute()

    already_advanced = sum(a["advance_amount"] for a in existing.data)
    available = max(0, max_advance - already_advanced)

    return {
        "employee_name": emp.data["full_name"],
        "hours_worked": round(total_hours, 2),
        "hourly_rate": hourly_rate,
        "earned_amount": earned,
        "max_advance": max_advance,
        "already_advanced": already_advanced,
        "available_for_advance": available,
        "pay_period_start": period_start.isoformat(),
        "pay_period_end": period_end.isoformat(),
        "advance_fee": float(tenant.data.get("wage_advance_fee", 3.00) if hasattr(tenant.data, 'get') else 3.00),
    }


def request_wage_advance(tenant_id: str, employee_id: str, amount: float) -> dict:
    """Request an early wage advance."""
    earnings = calculate_earned_wages(tenant_id, employee_id)

    if "error" in earnings:
        return earnings

    if amount > earnings["available_for_advance"]:
        return {"error": f"Requested ${amount:.2f} exceeds available ${earnings['available_for_advance']:.2f}"}

    if amount < 5.0:
        return {"error": "Minimum advance is $5.00"}

    # Get tenant's advance fee
    tenant = supabase.table("onyx_tenants").select("wage_advance_fee").eq("id", tenant_id).single().execute()
    fee = float(tenant.data.get("wage_advance_fee", 3.00))

    record = supabase.table("onyx_wage_advances").insert({
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "hours_worked": earnings["hours_worked"],
        "hourly_rate": earnings["hourly_rate"],
        "earned_amount": earnings["earned_amount"],
        "advance_amount": amount,
        "advance_fee": fee,
        "pay_period_start": earnings["pay_period_start"],
        "pay_period_end": earnings["pay_period_end"],
        "status": "pending",
    }).execute()

    return {
        "advance_id": record.data[0]["id"],
        "amount": amount,
        "fee": fee,
        "net_amount": amount - fee,
        "status": "pending",
        "message": f"Advance of ${amount:.2f} requested (${fee:.2f} fee). Pending manager approval.",
    }


# ============================================================
# 5. NEIGHBORHOOD COMMERCE NETWORK
# ============================================================

def find_nearby_merchants(tenant_id: str, radius_miles: float = 1.0) -> list[dict]:
    """Find nearby Onyx merchants for cross-promotion.

    Uses simple distance calculation (good enough for neighborhood scale).
    """
    # Get this merchant's location
    me = supabase.table("onyx_merchant_network").select("*").eq(
        "tenant_id", tenant_id
    ).single().execute()

    if not me.data:
        return []

    my_lat = float(me.data["latitude"])
    my_lon = float(me.data["longitude"])

    # Get all active merchants in the same city
    merchants = supabase.table("onyx_merchant_network").select(
        "*, onyx_tenants(business_name)"
    ).eq("network_active", True).eq("city", me.data["city"]).neq(
        "tenant_id", tenant_id
    ).execute()

    # Filter by distance (approximate miles using lat/lon)
    nearby = []
    for m in merchants.data:
        lat = float(m["latitude"])
        lon = float(m["longitude"])
        # Haversine approximation for short distances
        dlat = abs(lat - my_lat) * 69  # ~69 miles per degree latitude
        dlon = abs(lon - my_lon) * 54.6  # ~54.6 miles per degree longitude at ~38°N
        distance = (dlat**2 + dlon**2) ** 0.5

        if distance <= radius_miles:
            m["distance_miles"] = round(distance, 2)
            nearby.append(m)

    return sorted(nearby, key=lambda x: x["distance_miles"])


def generate_cross_promo(source_tenant_id: str, target_tenant_id: str) -> dict:
    """Generate a cross-promotion code between two merchants."""
    # Get target's promo config
    target = supabase.table("onyx_merchant_network").select(
        "promo_discount_pct, promo_budget_monthly"
    ).eq("tenant_id", target_tenant_id).single().execute()

    if not target.data or not target.data.get("promo_discount_pct"):
        return {"error": "Target merchant not configured for cross-promos"}

    code = f"ONYX-{secrets.token_hex(3).upper()}"
    discount = float(target.data["promo_discount_pct"])

    promo = supabase.table("onyx_cross_promos").insert({
        "source_tenant_id": source_tenant_id,
        "target_tenant_id": target_tenant_id,
        "promo_code": code,
        "discount_pct": discount,
    }).execute()

    return {
        "promo_code": code,
        "discount_pct": discount,
        "message": f"Show code {code} for {discount}% off at the partner store!",
        "expires_in": "7 days",
    }


# ============================================================
# 6. DEAD STOCK MARKETPLACE
# ============================================================

def auto_detect_dead_stock(tenant_id: str, days_threshold: int = 60) -> list[dict]:
    """Automatically identify products that haven't sold in X days.

    Returns products that are overstocked and slow-moving,
    suggesting them for the dead stock marketplace.
    """
    # Get all products with stock
    products = supabase.table("onyx_products").select("*").eq(
        "tenant_id", tenant_id
    ).eq("is_active", True).execute()

    # Get recent sales
    since = (datetime.utcnow() - timedelta(days=days_threshold)).isoformat()
    sales = supabase.table("onyx_line_items").select(
        "product_id, quantity"
    ).eq("tenant_id", tenant_id).gte("created_at", since).execute()

    # Count sales per product
    sales_by_product = {}
    for s in sales.data:
        pid = s.get("product_id")
        if pid:
            sales_by_product[pid] = sales_by_product.get(pid, 0) + s["quantity"]

    dead_stock = []
    for prod in products.data:
        stock = prod.get("stock_quantity")
        if stock is None or stock <= 0:
            continue

        sold = sales_by_product.get(prod["id"], 0)

        # Dead stock: has inventory but barely sold in the period
        if sold <= 2 and stock >= 5:
            suggested_clearance = round(float(prod["unit_price"]) * 0.6, 2)  # 40% off
            dead_stock.append({
                "product_id": prod["id"],
                "product_name": prod["name"],
                "original_price": float(prod["unit_price"]),
                "suggested_clearance_price": suggested_clearance,
                "stock_quantity": stock,
                "units_sold_period": sold,
                "days_analyzed": days_threshold,
                "discount_pct": 40,
            })

    return sorted(dead_stock, key=lambda x: x["stock_quantity"], reverse=True)
