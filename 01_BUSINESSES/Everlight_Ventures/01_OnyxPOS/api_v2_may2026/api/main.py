"""
Onyx POS -- FastAPI Backend
Built by SaaS Factory: Amara Osei (backend), Zara Khoury (security), Leo Marchetti (AI)
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import bcrypt
import json
import anthropic

from config import CORS_ORIGINS, ANTHROPIC_API_KEY, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from db import supabase
from models import (
    SignupRequest, LoginRequest, PinLoginRequest,
    EmployeeCreate, EmployeeUpdate,
    ProductCreate, ProductUpdate, CategoryCreate,
    SaleCreate, PunchCreate, TimeOffRequest, ChatMessage,
    ScanResult,
    VendorBillUpdate, LotteryCheckRequest, LotteryRedeemRequest,
    WageAdvanceRequest, WageAdvanceApproval,
    NetworkJoinRequest, DeadStockListing, DeadStockClaim,
    CustomerLookup, PointsAction, SocialPostCreate,
    PredictionEventCreate, PredictionBetCreate, PredictionResolve,
    DropCreate, WaitlistJoin, VoiceOrderCreate,
)
from receipt_scanner import scan_receipt
from ecosystem import (
    save_vendor_bill, create_lottery_entry,
    check_lottery_code, redeem_lottery_code,
    generate_pricing_suggestions, calculate_earned_wages,
    request_wage_advance, find_nearby_merchants,
    generate_cross_promo, auto_detect_dead_stock,
)
from platform import (
    get_or_create_customer, earn_points, spend_points,
    record_visit, generate_qr_receipt,
    create_social_post, get_leaderboard,
    create_prediction_event, place_prediction_bet, resolve_prediction,
    create_drop, join_waitlist,
    create_voice_order, predict_customer_order,
)

app = FastAPI(title="Onyx POS API", version="3.0.0",
              description="The Protocol Layer for Neighborhood Commerce")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTH HELPERS
# ============================================================
def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

def verify_pin(pin: str, hashed: str) -> bool:
    return bcrypt.checkpw(pin.encode(), hashed.encode())

async def get_tenant_id(x_tenant_id: str = Header(...)) -> str:
    return x_tenant_id


# ============================================================
# AUTH ENDPOINTS
# ============================================================
@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    """Register a new business + owner account"""
    # Create Supabase auth user
    auth_resp = supabase.auth.sign_up({"email": req.email, "password": req.password})
    if not auth_resp.user:
        raise HTTPException(400, "Failed to create account")

    user_id = auth_resp.user.id

    # Create tenant
    tenant = supabase.table("onyx_tenants").insert({
        "business_name": req.business_name,
        "address_line1": req.address_line1,
        "address_line2": req.address_line2,
        "phone": req.phone,
        "tax_rate": req.tax_rate,
        "owner_user_id": user_id,
    }).execute()

    tenant_id = tenant.data[0]["id"]

    # Create owner as first employee
    supabase.table("onyx_employees").insert({
        "tenant_id": tenant_id,
        "user_id": user_id,
        "full_name": req.full_name,
        "role": "owner",
        "email": req.email,
        "phone": req.phone,
    }).execute()

    # Seed default categories (from Mountain Gardens template)
    categories = [
        {"tenant_id": tenant_id, "name": "Animal", "sort_order": 1},
        {"tenant_id": tenant_id, "name": "Product", "sort_order": 2},
        {"tenant_id": tenant_id, "name": "Plant", "sort_order": 3},
    ]
    supabase.table("onyx_categories").insert(categories).execute()

    return {"tenant_id": tenant_id, "user_id": user_id, "message": "Account created"}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Login with email/password"""
    auth_resp = supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
    if not auth_resp.user:
        raise HTTPException(401, "Invalid credentials")

    # Get tenant
    tenant = supabase.table("onyx_tenants").select("*").eq("owner_user_id", auth_resp.user.id).single().execute()

    return {
        "access_token": auth_resp.session.access_token,
        "tenant_id": tenant.data["id"],
        "business_name": tenant.data["business_name"],
        "user_id": auth_resp.user.id,
    }


@app.post("/api/auth/pin-login")
async def pin_login(req: PinLoginRequest):
    """Quick login with PIN (for employees at the register)"""
    employees = supabase.table("onyx_employees").select("*").eq("tenant_id", req.tenant_id).eq("status", "active").execute()

    for emp in employees.data:
        if emp["pin_hash"] and verify_pin(req.pin, emp["pin_hash"]):
            return {"employee_id": emp["id"], "full_name": emp["full_name"], "role": emp["role"]}

    raise HTTPException(401, "Invalid PIN")


# ============================================================
# EMPLOYEES
# ============================================================
@app.get("/api/employees")
async def list_employees(tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_employees").select("*").eq("tenant_id", tenant_id).eq("status", "active").order("full_name").execute()
    return result.data

@app.post("/api/employees")
async def create_employee(emp: EmployeeCreate, tenant_id: str = Depends(get_tenant_id)):
    data = {"tenant_id": tenant_id, **emp.model_dump(exclude_none=True)}
    if emp.pin:
        data["pin_hash"] = hash_pin(emp.pin)
        del data["pin"]
    result = supabase.table("onyx_employees").insert(data).execute()
    return result.data[0]

@app.patch("/api/employees/{employee_id}")
async def update_employee(employee_id: str, emp: EmployeeUpdate, tenant_id: str = Depends(get_tenant_id)):
    data = emp.model_dump(exclude_none=True)
    if "pin" in data:
        data["pin_hash"] = hash_pin(data.pop("pin"))
    result = supabase.table("onyx_employees").update(data).eq("id", employee_id).eq("tenant_id", tenant_id).execute()
    return result.data[0] if result.data else {"error": "Not found"}


# ============================================================
# PRODUCTS & CATEGORIES
# ============================================================
@app.get("/api/categories")
async def list_categories(tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_categories").select("*").eq("tenant_id", tenant_id).order("sort_order").execute()
    return result.data

@app.post("/api/categories")
async def create_category(cat: CategoryCreate, tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_categories").insert({"tenant_id": tenant_id, **cat.model_dump()}).execute()
    return result.data[0]

@app.get("/api/products")
async def list_products(tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_products").select("*, onyx_categories(name)").eq("tenant_id", tenant_id).eq("is_active", True).order("name").execute()
    return result.data

@app.post("/api/products")
async def create_product(prod: ProductCreate, tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_products").insert({"tenant_id": tenant_id, **prod.model_dump(exclude_none=True)}).execute()
    return result.data[0]

@app.patch("/api/products/{product_id}")
async def update_product(product_id: str, prod: ProductUpdate, tenant_id: str = Depends(get_tenant_id)):
    data = prod.model_dump(exclude_none=True)
    result = supabase.table("onyx_products").update(data).eq("id", product_id).eq("tenant_id", tenant_id).execute()
    return result.data[0] if result.data else {"error": "Not found"}


# ============================================================
# SALES (the core POS function)
# ============================================================
@app.post("/api/sales")
async def create_sale(sale: SaleCreate, tenant_id: str = Depends(get_tenant_id)):
    """Record a complete sale with line items"""
    # Get tenant tax rate
    tenant = supabase.table("onyx_tenants").select("tax_rate").eq("id", tenant_id).single().execute()
    tax_rate = Decimal(str(tenant.data["tax_rate"]))

    # Calculate totals
    subtotal = Decimal("0")
    line_items = []
    for item in sale.items:
        item_subtotal = Decimal(str(item.unit_price)) * item.quantity
        item_tax = (item_subtotal * tax_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        item_total = item_subtotal + item_tax
        subtotal += item_subtotal

        line_items.append({
            "tenant_id": tenant_id,
            "product_id": item.product_id,
            "product_name": item.product_name,
            "category_name": item.category_name,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "subtotal": float(item_subtotal),
            "tax_amount": float(item_tax),
            "line_total": float(item_total),
        })

    total_tax = (subtotal * tax_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total = subtotal + total_tax
    change_due = Decimal(str(sale.amount_received or 0)) - total if sale.amount_received else Decimal("0")

    # Create transaction
    tx = supabase.table("onyx_transactions").insert({
        "tenant_id": tenant_id,
        "employee_id": sale.employee_id,
        "subtotal": float(subtotal),
        "tax_rate": float(tax_rate),
        "tax_amount": float(total_tax),
        "total": float(total),
        "payment_method": sale.payment_method,
        "amount_received": sale.amount_received,
        "change_due": float(change_due) if change_due > 0 else 0,
        "notes": sale.notes,
    }).execute()

    tx_id = tx.data[0]["id"]

    # Insert line items
    for li in line_items:
        li["transaction_id"] = tx_id
    supabase.table("onyx_line_items").insert(line_items).execute()

    # Update stock quantities (read-then-write)
    for item in sale.items:
        if item.product_id:
            prod = supabase.table("onyx_products").select("stock_quantity").eq("id", item.product_id).single().execute()
            if prod.data and prod.data["stock_quantity"] is not None:
                new_qty = prod.data["stock_quantity"] - item.quantity
                supabase.table("onyx_products").update({"stock_quantity": new_qty}).eq("id", item.product_id).execute()

    # Generate lottery code (if enabled)
    lottery = create_lottery_entry(tenant_id, tx_id, float(total))

    result = {
        "transaction_id": tx_id,
        "subtotal": float(subtotal),
        "tax": float(total_tax),
        "total": float(total),
        "change_due": float(max(change_due, Decimal("0"))),
        "items": len(line_items),
    }
    if lottery:
        result["lottery"] = lottery

    return result


@app.get("/api/sales")
async def list_sales(tenant_id: str = Depends(get_tenant_id), days: int = 7):
    """List recent sales"""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    result = supabase.table("onyx_transactions").select("*, onyx_employees(full_name)").eq("tenant_id", tenant_id).gte("created_at", since).order("created_at", desc=True).execute()
    return result.data

@app.get("/api/sales/{transaction_id}")
async def get_sale(transaction_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get sale with line items"""
    tx = supabase.table("onyx_transactions").select("*, onyx_employees(full_name)").eq("id", transaction_id).eq("tenant_id", tenant_id).single().execute()
    items = supabase.table("onyx_line_items").select("*").eq("transaction_id", transaction_id).execute()
    return {"transaction": tx.data, "items": items.data}


# ============================================================
# REPORTS
# ============================================================
@app.get("/api/reports/daily")
async def daily_report(tenant_id: str = Depends(get_tenant_id), report_date: str = None):
    """Daily sales summary"""
    target = report_date or date.today().isoformat()
    start = f"{target}T00:00:00"
    end = f"{target}T23:59:59"

    txs = supabase.table("onyx_transactions").select("*").eq("tenant_id", tenant_id).gte("created_at", start).lte("created_at", end).eq("voided", False).execute()

    total_revenue = sum(t["total"] for t in txs.data)
    total_tax = sum(t["tax_amount"] for t in txs.data)
    cash_sales = sum(t["total"] for t in txs.data if t["payment_method"] == "cash")
    card_sales = sum(t["total"] for t in txs.data if t["payment_method"] == "card")

    return {
        "date": target,
        "total_transactions": len(txs.data),
        "total_revenue": round(total_revenue, 2),
        "total_tax": round(total_tax, 2),
        "cash_sales": round(cash_sales, 2),
        "card_sales": round(card_sales, 2),
    }

@app.get("/api/reports/top-products")
async def top_products(tenant_id: str = Depends(get_tenant_id), days: int = 30):
    """Top selling products"""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    items = supabase.table("onyx_line_items").select("product_name, quantity, line_total").eq("tenant_id", tenant_id).gte("created_at", since).execute()

    product_totals = {}
    for item in items.data:
        name = item["product_name"]
        if name not in product_totals:
            product_totals[name] = {"quantity": 0, "revenue": 0}
        product_totals[name]["quantity"] += item["quantity"]
        product_totals[name]["revenue"] += item["line_total"]

    sorted_products = sorted(product_totals.items(), key=lambda x: x[1]["revenue"], reverse=True)
    return [{"product": name, **data} for name, data in sorted_products[:20]]


# ============================================================
# TIME CLOCK
# ============================================================
@app.post("/api/timeclock/punch")
async def clock_punch(punch: PunchCreate, tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_time_punches").insert({
        "tenant_id": tenant_id,
        "employee_id": punch.employee_id,
        "punch_type": punch.punch_type,
    }).execute()
    return result.data[0]

@app.get("/api/timeclock/status/{employee_id}")
async def clock_status(employee_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get current clock status for an employee"""
    today = date.today().isoformat()
    punches = supabase.table("onyx_time_punches").select("*").eq("tenant_id", tenant_id).eq("employee_id", employee_id).gte("punched_at", f"{today}T00:00:00").order("punched_at").execute()

    if not punches.data:
        return {"status": "not_clocked_in", "hours_today": 0, "punches": []}

    last_punch = punches.data[-1]["punch_type"]
    status_map = {
        "clock_in": "clocked_in",
        "clock_out": "clocked_out",
        "break_start": "on_break",
        "break_end": "clocked_in",
        "lunch_start": "on_lunch",
        "lunch_end": "clocked_in",
    }

    return {
        "status": status_map.get(last_punch, "unknown"),
        "last_punch": last_punch,
        "punch_count": len(punches.data),
        "punches": punches.data,
    }

@app.get("/api/timeclock/hours")
async def employee_hours(tenant_id: str = Depends(get_tenant_id), days: int = 7):
    """Hours worked by all employees over the last N days"""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    punches = supabase.table("onyx_time_punches").select("*, onyx_employees(full_name)").eq("tenant_id", tenant_id).gte("punched_at", since).order("punched_at").execute()
    return punches.data


# ============================================================
# TIME OFF
# ============================================================
@app.post("/api/time-off")
async def request_time_off(req: TimeOffRequest, tenant_id: str = Depends(get_tenant_id)):
    total_days = (req.end_date - req.start_date).days + 1
    result = supabase.table("onyx_time_off").insert({
        "tenant_id": tenant_id,
        "employee_id": req.employee_id,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "total_days": total_days,
        "reason": req.reason,
    }).execute()
    return result.data[0]

@app.get("/api/time-off")
async def list_time_off(tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_time_off").select("*, onyx_employees(full_name)").eq("tenant_id", tenant_id).order("created_at", desc=True).execute()
    return result.data

@app.patch("/api/time-off/{request_id}")
async def update_time_off(request_id: str, status: str, approved_by: str, tenant_id: str = Depends(get_tenant_id)):
    result = supabase.table("onyx_time_off").update({
        "status": status,
        "approved_by": approved_by,
        "approved_at": datetime.utcnow().isoformat(),
    }).eq("id", request_id).eq("tenant_id", tenant_id).execute()
    return result.data[0] if result.data else {"error": "Not found"}


# ============================================================
# AI CHAT -- "Ask your POS anything"
# ============================================================
@app.post("/api/chat")
async def ai_chat(msg: ChatMessage, tenant_id: str = Depends(get_tenant_id)):
    """Conversational business intelligence powered by Claude"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "AI not configured")

    # Gather context: recent sales, top products, employee hours
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()

    sales_7d = supabase.table("onyx_transactions").select("total, payment_method, created_at").eq("tenant_id", tenant_id).gte("created_at", f"{week_ago}T00:00:00").eq("voided", False).execute()

    top_items = supabase.table("onyx_line_items").select("product_name, quantity, line_total").eq("tenant_id", tenant_id).gte("created_at", f"{week_ago}T00:00:00").execute()

    tenant_info = supabase.table("onyx_tenants").select("business_name").eq("id", tenant_id).single().execute()

    # Build context for Claude
    total_rev = sum(s["total"] for s in sales_7d.data)
    tx_count = len(sales_7d.data)

    product_summary = {}
    for item in top_items.data:
        name = item["product_name"]
        if name not in product_summary:
            product_summary[name] = {"qty": 0, "rev": 0}
        product_summary[name]["qty"] += item["quantity"]
        product_summary[name]["rev"] += item["line_total"]
    top_5 = sorted(product_summary.items(), key=lambda x: x[1]["rev"], reverse=True)[:5]

    context = f"""You are an AI business assistant for {tenant_info.data['business_name']}, a small business using Onyx POS.

Here is the business data for the last 7 days:
- Total transactions: {tx_count}
- Total revenue: ${total_rev:.2f}
- Top products: {json.dumps([{"name": n, "qty": d["qty"], "revenue": f"${d['rev']:.2f}"} for n, d in top_5])}
- Today's date: {today}

Answer the business owner's question in plain English. Be concise, specific, and actionable. Use numbers from the data above. If you don't have enough data to answer, say so honestly."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=context,
        messages=[{"role": "user", "content": msg.message}],
    )

    ai_text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens

    # Log to chat history
    supabase.table("onyx_chat_history").insert({
        "tenant_id": tenant_id,
        "employee_id": msg.employee_id,
        "user_message": msg.message,
        "ai_response": ai_text,
        "tokens_used": tokens,
    }).execute()

    return {"response": ai_text, "tokens_used": tokens}


# ============================================================
# STRIPE BILLING
# ============================================================
@app.post("/api/billing/create-checkout")
async def create_checkout(tenant_id: str = Depends(get_tenant_id)):
    """Create Stripe checkout session for $49/mo subscription"""
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    tenant = supabase.table("onyx_tenants").select("*").eq("id", tenant_id).single().execute()

    # Create or get Stripe customer
    if tenant.data.get("stripe_customer_id"):
        customer_id = tenant.data["stripe_customer_id"]
    else:
        customer = stripe.Customer.create(
            email=tenant.data.get("business_name"),
            metadata={"tenant_id": tenant_id},
        )
        customer_id = customer.id
        supabase.table("onyx_tenants").update({"stripe_customer_id": customer_id}).eq("id", tenant_id).execute()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": "Onyx POS - Starter Plan"},
                "unit_amount": 4900,  # $49.00
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }],
        mode="subscription",
        success_url="https://pos.everlightventures.io/dashboard?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://pos.everlightventures.io/pricing",
        metadata={"tenant_id": tenant_id},
    )

    return {"checkout_url": session.url}


@app.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(400, "Invalid webhook")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tenant_id = session["metadata"]["tenant_id"]
        addon = session["metadata"].get("addon")

        if addon == "smart_scanner":
            # Activate Smart Scanner add-on
            supabase.table("onyx_tenants").update({
                "scanner_enabled": True,
                "scanner_stripe_subscription_id": session.get("subscription"),
            }).eq("id", tenant_id).execute()
        else:
            # Main POS subscription
            supabase.table("onyx_tenants").update({
                "stripe_subscription_id": session.get("subscription"),
                "plan_status": "active",
            }).eq("id", tenant_id).execute()

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        # Check if it's the scanner sub or the main sub
        scanner_tenant = supabase.table("onyx_tenants").select("id").eq(
            "scanner_stripe_subscription_id", sub["id"]
        ).execute()
        if scanner_tenant.data:
            supabase.table("onyx_tenants").update({
                "scanner_enabled": False,
                "scanner_stripe_subscription_id": None,
            }).eq("scanner_stripe_subscription_id", sub["id"]).execute()
        else:
            supabase.table("onyx_tenants").update({
                "plan_status": "canceled",
            }).eq("stripe_subscription_id", sub["id"]).execute()

    return {"status": "ok"}


# ============================================================
# RECEIPT SCANNER (Smart Scanner add-on -- $29/mo or 10 free/mo)
# ============================================================
@app.post("/api/scan-receipt")
async def scan_receipt_endpoint(
    file: UploadFile = File(...),
    employee_id: str = None,
    scan_type: str = "receipt",
    tenant_id: str = Depends(get_tenant_id),
):
    """Scan a receipt/invoice image and extract structured data.

    Uses OpenCV preprocessing + Tesseract OCR.
    Free tier: 10 scans/month. Smart Scanner ($29/mo): unlimited.
    """
    # Check scan limits
    tenant = supabase.table("onyx_tenants").select(
        "scanner_enabled, monthly_scan_count, monthly_scan_limit"
    ).eq("id", tenant_id).single().execute()

    scan_limit = tenant.data.get("monthly_scan_limit", 10)
    scan_count = tenant.data.get("monthly_scan_count", 0)
    scanner_enabled = tenant.data.get("scanner_enabled", False)

    if not scanner_enabled and scan_count >= scan_limit:
        raise HTTPException(
            402,
            f"Free scan limit reached ({scan_limit}/month). "
            "Upgrade to Smart Scanner ($29/mo) for unlimited scans."
        )

    # Read image bytes
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB max
        raise HTTPException(413, "Image too large. Maximum 10MB.")

    # Run the CV pipeline
    result = scan_receipt(image_bytes)

    # Save to Supabase
    scan_record = supabase.table("onyx_receipt_scans").insert({
        "tenant_id": tenant_id,
        "employee_id": employee_id,
        "extracted_data": json.dumps(result),
        "raw_ocr_text": result.get("raw_text", ""),
        "confidence_score": result.get("confidence", 0),
        "scan_type": scan_type,
        "status": "completed",
    }).execute()

    # Increment monthly scan count
    supabase.table("onyx_tenants").update({
        "monthly_scan_count": scan_count + 1,
    }).eq("id", tenant_id).execute()

    return {
        "scan_id": scan_record.data[0]["id"],
        "result": result,
        "scans_remaining": "unlimited" if scanner_enabled else max(0, scan_limit - scan_count - 1),
    }


@app.get("/api/scans")
async def list_scans(tenant_id: str = Depends(get_tenant_id), limit: int = 20):
    """List recent receipt scans"""
    result = supabase.table("onyx_receipt_scans").select("*").eq(
        "tenant_id", tenant_id
    ).order("created_at", desc=True).limit(limit).execute()
    return result.data


@app.post("/api/billing/create-scanner-checkout")
async def create_scanner_checkout(tenant_id: str = Depends(get_tenant_id)):
    """Create Stripe checkout for Smart Scanner add-on ($29/mo)"""
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    tenant = supabase.table("onyx_tenants").select("*").eq("id", tenant_id).single().execute()

    customer_id = tenant.data.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(
            email=tenant.data.get("business_name"),
            metadata={"tenant_id": tenant_id},
        )
        customer_id = customer.id
        supabase.table("onyx_tenants").update(
            {"stripe_customer_id": customer_id}
        ).eq("id", tenant_id).execute()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": "Onyx POS - Smart Scanner Add-On",
                    "description": "Unlimited receipt & invoice scanning with AI-powered data extraction",
                },
                "unit_amount": 2900,  # $29.00
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }],
        mode="subscription",
        success_url="https://pos.everlightventures.io/dashboard?scanner=activated",
        cancel_url="https://pos.everlightventures.io/settings",
        metadata={"tenant_id": tenant_id, "addon": "smart_scanner"},
    )

    return {"checkout_url": session.url}


# ============================================================
# VENDOR BILL SCANNER (expense-side CV -- flip the receipt scanner)
# ============================================================
@app.post("/api/scan-bill")
async def scan_bill_endpoint(
    file: UploadFile = File(...),
    employee_id: str = None,
    tenant_id: str = Depends(get_tenant_id),
):
    """Scan a supplier invoice/bill and extract expense data.

    Same CV pipeline as receipt scanner, but saves to vendor_bills
    table and auto-categorizes expenses.
    """
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large. Maximum 10MB.")

    # Same CV pipeline
    result = scan_receipt(image_bytes)

    # Save as vendor bill (auto-categorizes)
    bill = save_vendor_bill(tenant_id, result, employee_id)

    return {
        "bill_id": bill["id"],
        "vendor": result.get("vendor"),
        "total": result.get("total"),
        "category": bill["expense_category"],
        "extracted_data": result,
    }


@app.get("/api/bills")
async def list_vendor_bills(
    tenant_id: str = Depends(get_tenant_id),
    paid: bool = None,
    limit: int = 50,
):
    """List vendor bills / expenses"""
    query = supabase.table("onyx_vendor_bills").select("*").eq(
        "tenant_id", tenant_id
    ).order("created_at", desc=True).limit(limit)

    if paid is not None:
        query = query.eq("paid", paid)

    result = query.execute()
    return result.data


@app.patch("/api/bills/{bill_id}")
async def update_vendor_bill(
    bill_id: str,
    update: VendorBillUpdate,
    tenant_id: str = Depends(get_tenant_id),
):
    """Update a vendor bill (mark paid, change category, etc.)"""
    data = update.model_dump(exclude_none=True)
    if data.get("paid"):
        data["paid_at"] = datetime.utcnow().isoformat()
    result = supabase.table("onyx_vendor_bills").update(data).eq(
        "id", bill_id
    ).eq("tenant_id", tenant_id).execute()
    return result.data[0] if result.data else {"error": "Not found"}


@app.get("/api/bills/summary")
async def expense_summary(tenant_id: str = Depends(get_tenant_id), days: int = 30):
    """Expense summary by category"""
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    bills = supabase.table("onyx_vendor_bills").select(
        "expense_category, total_amount, paid"
    ).eq("tenant_id", tenant_id).gte("created_at", since).execute()

    by_category = {}
    total_expenses = 0
    unpaid = 0
    for b in bills.data:
        cat = b["expense_category"]
        amt = float(b["total_amount"] or 0)
        by_category[cat] = by_category.get(cat, 0) + amt
        total_expenses += amt
        if not b["paid"]:
            unpaid += amt

    return {
        "period_days": days,
        "total_expenses": round(total_expenses, 2),
        "unpaid": round(unpaid, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: x[1], reverse=True)},
    }


# ============================================================
# RECEIPT LOTTERY (gamification / viral growth engine)
# ============================================================
@app.post("/api/lottery/check")
async def lottery_check(req: LotteryCheckRequest):
    """Check if a lottery code is a winner"""
    return check_lottery_code(req.lottery_code)


@app.post("/api/lottery/redeem")
async def lottery_redeem(req: LotteryRedeemRequest, tenant_id: str = Depends(get_tenant_id)):
    """Redeem a winning lottery code for store credit"""
    return redeem_lottery_code(req.lottery_code, req.transaction_id)


@app.get("/api/lottery/stats")
async def lottery_stats(tenant_id: str = Depends(get_tenant_id)):
    """Lottery statistics for this merchant"""
    tenant = supabase.table("onyx_tenants").select(
        "lottery_enabled, lottery_fund_balance, lottery_win_rate"
    ).eq("id", tenant_id).single().execute()

    codes = supabase.table("onyx_lottery_codes").select(
        "is_winner, prize_amount, redeemed, shared_social"
    ).eq("tenant_id", tenant_id).execute()

    total_codes = len(codes.data)
    winners = [c for c in codes.data if c["is_winner"]]
    redeemed = [c for c in winners if c["redeemed"]]
    shared = [c for c in codes.data if c.get("shared_social")]
    total_prizes = sum(float(c["prize_amount"]) for c in winners)

    return {
        "enabled": tenant.data.get("lottery_enabled", False),
        "fund_balance": float(tenant.data.get("lottery_fund_balance", 0)),
        "total_codes_issued": total_codes,
        "total_winners": len(winners),
        "total_prizes_awarded": round(total_prizes, 2),
        "redemption_rate": round(len(redeemed) / max(len(winners), 1) * 100, 1),
        "social_shares": len(shared),
        "win_rate_pct": float(tenant.data.get("lottery_win_rate", 0.05)) * 100,
    }


# ============================================================
# SMART PRICING ENGINE (demand-based dynamic pricing)
# ============================================================
@app.post("/api/pricing/generate")
async def generate_prices(tenant_id: str = Depends(get_tenant_id)):
    """Analyze sales data and generate pricing suggestions"""
    suggestions = generate_pricing_suggestions(tenant_id)
    return {
        "suggestions": suggestions,
        "count": len(suggestions),
        "message": f"Generated {len(suggestions)} pricing suggestions based on your last 30 days of sales data.",
    }


@app.get("/api/pricing/suggestions")
async def list_pricing_suggestions(
    tenant_id: str = Depends(get_tenant_id),
    status: str = "pending",
):
    """List pricing suggestions"""
    result = supabase.table("onyx_pricing_suggestions").select("*").eq(
        "tenant_id", tenant_id
    ).eq("status", status).order("confidence", desc=True).execute()
    return result.data


@app.patch("/api/pricing/suggestions/{suggestion_id}")
async def respond_to_suggestion(
    suggestion_id: str,
    accept: bool,
    tenant_id: str = Depends(get_tenant_id),
):
    """Accept or reject a pricing suggestion. If accepted, update the product price."""
    suggestion = supabase.table("onyx_pricing_suggestions").select("*").eq(
        "id", suggestion_id
    ).eq("tenant_id", tenant_id).single().execute()

    if not suggestion.data:
        raise HTTPException(404, "Suggestion not found")

    new_status = "accepted" if accept else "rejected"
    supabase.table("onyx_pricing_suggestions").update({
        "status": new_status,
        "accepted_at": datetime.utcnow().isoformat() if accept else None,
    }).eq("id", suggestion_id).execute()

    # If accepted and product_id exists, update the actual product price
    if accept and suggestion.data.get("product_id"):
        supabase.table("onyx_products").update({
            "unit_price": float(suggestion.data["suggested_price"]),
        }).eq("id", suggestion.data["product_id"]).eq("tenant_id", tenant_id).execute()

    return {
        "status": new_status,
        "product": suggestion.data["product_name"],
        "price_change": f"${suggestion.data['current_price']:.2f} → ${suggestion.data['suggested_price']:.2f}" if accept else "No change",
    }


# ============================================================
# EARNED WAGE ACCESS (payroll advance)
# ============================================================
@app.get("/api/wages/earned/{employee_id}")
async def get_earned_wages(employee_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Calculate earned wages for an employee in the current pay period"""
    return calculate_earned_wages(tenant_id, employee_id)


@app.post("/api/wages/advance")
async def create_wage_advance(req: WageAdvanceRequest, tenant_id: str = Depends(get_tenant_id)):
    """Request an early wage advance"""
    return request_wage_advance(tenant_id, req.employee_id, req.advance_amount)


@app.patch("/api/wages/advance/{advance_id}")
async def approve_wage_advance(
    advance_id: str,
    approval: WageAdvanceApproval,
    approved_by: str = None,
    tenant_id: str = Depends(get_tenant_id),
):
    """Approve or deny a wage advance request"""
    if approval.approved:
        supabase.table("onyx_wage_advances").update({
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": datetime.utcnow().isoformat(),
        }).eq("id", advance_id).eq("tenant_id", tenant_id).execute()
        return {"status": "approved", "message": "Advance approved. Employee can pick up funds."}
    else:
        supabase.table("onyx_wage_advances").update({
            "status": "denied",
            "denial_reason": approval.denial_reason,
        }).eq("id", advance_id).eq("tenant_id", tenant_id).execute()
        return {"status": "denied", "reason": approval.denial_reason}


@app.get("/api/wages/advances")
async def list_wage_advances(
    tenant_id: str = Depends(get_tenant_id),
    status: str = None,
):
    """List wage advance requests"""
    query = supabase.table("onyx_wage_advances").select(
        "*, onyx_employees(full_name)"
    ).eq("tenant_id", tenant_id).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data


# ============================================================
# NEIGHBORHOOD COMMERCE NETWORK (cross-promotion engine)
# ============================================================
@app.post("/api/network/join")
async def join_network(req: NetworkJoinRequest, tenant_id: str = Depends(get_tenant_id)):
    """Join the Onyx neighborhood commerce network"""
    # Check if already in network
    existing = supabase.table("onyx_merchant_network").select("id").eq(
        "tenant_id", tenant_id
    ).execute()

    if existing.data:
        # Update existing entry
        supabase.table("onyx_merchant_network").update(
            req.model_dump()
        ).eq("tenant_id", tenant_id).execute()
        return {"status": "updated", "message": "Network profile updated."}

    record = supabase.table("onyx_merchant_network").insert({
        "tenant_id": tenant_id,
        **req.model_dump(),
    }).execute()

    return {
        "status": "joined",
        "network_id": record.data[0]["id"],
        "message": "Welcome to the Onyx neighborhood network! Nearby merchants will now cross-promote with you.",
    }


@app.get("/api/network/nearby")
async def get_nearby_merchants(
    tenant_id: str = Depends(get_tenant_id),
    radius: float = 1.0,
):
    """Find nearby Onyx merchants for cross-promotion"""
    merchants = find_nearby_merchants(tenant_id, radius)
    return {
        "nearby_merchants": merchants,
        "count": len(merchants),
        "radius_miles": radius,
    }


@app.post("/api/network/promo/{target_tenant_id}")
async def create_cross_promo(
    target_tenant_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Generate a cross-promotion code to send to a nearby merchant's customers"""
    return generate_cross_promo(tenant_id, target_tenant_id)


# ============================================================
# DEAD STOCK MARKETPLACE (B2B wholesale between merchants)
# ============================================================
@app.get("/api/marketplace/detect-dead-stock")
async def detect_dead_stock(
    tenant_id: str = Depends(get_tenant_id),
    days: int = 60,
):
    """Auto-detect slow-moving inventory eligible for dead stock marketplace"""
    dead = auto_detect_dead_stock(tenant_id, days)
    return {
        "dead_stock_items": dead,
        "count": len(dead),
        "message": f"Found {len(dead)} products that barely sold in the last {days} days.",
    }


@app.post("/api/marketplace/list")
async def create_dead_stock_listing(
    listing: DeadStockListing,
    tenant_id: str = Depends(get_tenant_id),
):
    """List a product on the dead stock marketplace"""
    discount_pct = round(
        ((listing.original_price - listing.clearance_price) / listing.original_price) * 100, 1
    ) if listing.original_price > 0 else 0

    record = supabase.table("onyx_dead_stock").insert({
        "seller_tenant_id": tenant_id,
        "product_id": listing.product_id,
        "product_name": listing.product_name,
        "description": listing.description,
        "original_price": listing.original_price,
        "clearance_price": listing.clearance_price,
        "discount_pct": discount_pct,
        "quantity_available": listing.quantity_available,
        "category": listing.category,
        "condition": listing.condition,
        "days_in_stock": listing.days_in_stock,
    }).execute()

    return {
        "listing_id": record.data[0]["id"],
        "discount_pct": discount_pct,
        "message": f"Listed {listing.product_name} at ${listing.clearance_price:.2f} ({discount_pct}% off). Visible to all Onyx merchants.",
    }


@app.get("/api/marketplace/browse")
async def browse_dead_stock(
    category: str = None,
    tenant_id: str = Depends(get_tenant_id),
):
    """Browse the dead stock marketplace (all active listings from other merchants)"""
    query = supabase.table("onyx_dead_stock").select(
        "*, onyx_tenants!onyx_dead_stock_seller_tenant_id_fkey(business_name)"
    ).eq("status", "active").neq("seller_tenant_id", tenant_id).order("created_at", desc=True)

    if category:
        query = query.eq("category", category)

    result = query.execute()
    return result.data


@app.post("/api/marketplace/claim")
async def claim_dead_stock(
    claim: DeadStockClaim,
    tenant_id: str = Depends(get_tenant_id),
):
    """Claim a dead stock listing (buy from another merchant)"""
    listing = supabase.table("onyx_dead_stock").select("*").eq(
        "id", claim.listing_id
    ).eq("status", "active").single().execute()

    if not listing.data:
        raise HTTPException(404, "Listing not found or already claimed")

    if listing.data["seller_tenant_id"] == tenant_id:
        raise HTTPException(400, "Can't buy your own listing")

    if claim.quantity > listing.data["quantity_available"]:
        raise HTTPException(400, f"Only {listing.data['quantity_available']} available")

    remaining = listing.data["quantity_available"] - claim.quantity
    new_status = "sold" if remaining == 0 else "active"

    supabase.table("onyx_dead_stock").update({
        "buyer_tenant_id": tenant_id,
        "claimed_at": datetime.utcnow().isoformat(),
        "status": new_status,
        "quantity_available": remaining,
    }).eq("id", claim.listing_id).execute()

    total_cost = claim.quantity * float(listing.data["clearance_price"])

    return {
        "status": "claimed",
        "product": listing.data["product_name"],
        "quantity": claim.quantity,
        "total_cost": round(total_cost, 2),
        "savings": round(claim.quantity * (float(listing.data["original_price"]) - float(listing.data["clearance_price"])), 2),
        "message": f"Claimed {claim.quantity}x {listing.data['product_name']} for ${total_cost:.2f}. Contact the seller to arrange pickup.",
    }


# ============================================================
# CUSTOMER PROFILES + LOYALTY WALLET
# ============================================================
@app.post("/api/customers/lookup")
async def customer_lookup(req: CustomerLookup):
    """Get or create a customer by phone number"""
    customer = get_or_create_customer(req.phone, req.display_name)
    return customer


@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get customer profile"""
    result = supabase.table("onyx_customers").select("*").eq("id", customer_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Customer not found")
    return result.data


@app.get("/api/customers/{customer_id}/points")
async def get_points_history(customer_id: str, limit: int = 50):
    """Get customer points history"""
    result = supabase.table("onyx_points_ledger").select("*").eq(
        "customer_id", customer_id
    ).order("created_at", desc=True).limit(limit).execute()
    return result.data


@app.post("/api/customers/visit")
async def log_customer_visit(
    customer_id: str,
    transaction_id: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Log a customer visit (called after a sale to update loyalty)"""
    # Get transaction details
    tx = supabase.table("onyx_transactions").select("total").eq(
        "id", transaction_id
    ).single().execute()

    items_data = supabase.table("onyx_line_items").select(
        "product_name, quantity, unit_price"
    ).eq("transaction_id", transaction_id).execute()

    items = [{"name": i["product_name"], "qty": i["quantity"], "price": float(i["unit_price"])}
             for i in items_data.data]

    result = record_visit(customer_id, tenant_id, transaction_id, items, float(tx.data["total"]))

    # Generate QR receipt
    qr = generate_qr_receipt(tenant_id, transaction_id, customer_id)
    result["qr_receipt"] = qr

    return result


# ============================================================
# SOCIAL CLOUT SYSTEM (sharing, streaks, leaderboards)
# ============================================================
@app.post("/api/social/share")
async def create_share(
    post: SocialPostCreate,
    tenant_id: str = Depends(get_tenant_id),
):
    """Share a purchase, win, or milestone for clout points"""
    return create_social_post(
        post.customer_id, post.post_type, tenant_id,
        post.content_text, post.reference_id, post.platforms,
    )


@app.get("/api/social/leaderboard")
async def leaderboard(
    board_type: str = "spending",
    period: str = "weekly",
    tenant_id: str = Depends(get_tenant_id),
):
    """Get leaderboard rankings"""
    rankings = get_leaderboard(tenant_id, board_type, period)
    return {"board_type": board_type, "period": period, "rankings": rankings}


@app.get("/api/social/feed")
async def social_feed(tenant_id: str = Depends(get_tenant_id), limit: int = 20):
    """Recent social activity at this merchant"""
    result = supabase.table("onyx_social_posts").select(
        "*, onyx_customers(display_name, avatar_url, tier)"
    ).eq("tenant_id", tenant_id).order("created_at", desc=True).limit(limit).execute()
    return result.data


# ============================================================
# SPORTS PREDICTION MARKET (loyalty points, not cash = legal)
# ============================================================
@app.post("/api/predictions/events")
async def create_event(
    event: PredictionEventCreate,
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a prediction event (sports, local, weather, etc.)"""
    return create_prediction_event(
        event.title, event.category, event.options,
        event.locks_at, event.event_time, tenant_id,
    )


@app.get("/api/predictions/events")
async def list_events(status: str = "open", tenant_id: str = Depends(get_tenant_id)):
    """List prediction events"""
    query = supabase.table("onyx_prediction_events").select("*").order("locks_at")
    if status:
        query = query.eq("status", status)
    # Show platform-wide + this merchant's events
    result = query.execute()
    return [e for e in result.data if e.get("tenant_id") is None or e["tenant_id"] == tenant_id]


@app.post("/api/predictions/bet")
async def place_bet(bet: PredictionBetCreate):
    """Place a prediction bet using loyalty points"""
    return place_prediction_bet(
        bet.customer_id, bet.event_id, bet.option_id, bet.points_wagered,
    )


@app.post("/api/predictions/events/{event_id}/resolve")
async def resolve_event(
    event_id: str,
    resolution: PredictionResolve,
    tenant_id: str = Depends(get_tenant_id),
):
    """Resolve a prediction event and pay out winners"""
    return resolve_prediction(event_id, resolution.correct_option_id)


@app.get("/api/predictions/my-bets/{customer_id}")
async def my_bets(customer_id: str, limit: int = 20):
    """Get a customer's betting history"""
    result = supabase.table("onyx_prediction_bets").select(
        "*, onyx_prediction_events(title, status, correct_option_id)"
    ).eq("customer_id", customer_id).order("created_at", desc=True).limit(limit).execute()
    return result.data


# ============================================================
# FASHION DROP CULTURE ENGINE (limited releases, hype, FOMO)
# ============================================================
@app.post("/api/drops")
async def create_drop_endpoint(
    drop: DropCreate,
    tenant_id: str = Depends(get_tenant_id),
):
    """Create a product drop event"""
    return create_drop(
        tenant_id, drop.title, drop.products, drop.drop_time,
        drop.drop_type, drop.max_per_customer, drop.collab_tenant_id,
    )


@app.get("/api/drops")
async def list_drops(status: str = None, tenant_id: str = Depends(get_tenant_id)):
    """List drop events"""
    query = supabase.table("onyx_drops").select("*").order("drop_time", desc=True)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data


@app.get("/api/drops/{drop_id}")
async def get_drop(drop_id: str):
    """Get drop details with waitlist count"""
    drop = supabase.table("onyx_drops").select("*").eq("id", drop_id).single().execute()
    if not drop.data:
        raise HTTPException(404, "Drop not found")
    return drop.data


@app.post("/api/drops/{drop_id}/waitlist")
async def join_drop_waitlist(drop_id: str, req: WaitlistJoin):
    """Join the waitlist for a drop"""
    return join_waitlist(drop_id, req.customer_id, req.bid_amount)


@app.get("/api/drops/{drop_id}/waitlist")
async def get_waitlist(drop_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get waitlist for a drop (merchant view)"""
    result = supabase.table("onyx_drop_waitlist").select(
        "*, onyx_customers(display_name, tier)"
    ).eq("drop_id", drop_id).order("position").execute()
    return result.data


# ============================================================
# VOICE COMMERCE / AI AGENT ORDERING
# ============================================================
@app.post("/api/orders/voice")
async def voice_order(req: VoiceOrderCreate, tenant_id: str = Depends(get_tenant_id)):
    """Start a voice/text commerce order via AI agent"""
    target_tenant = req.tenant_id or tenant_id
    return create_voice_order(req.customer_id, req.channel, req.message, target_tenant)


@app.get("/api/orders/voice")
async def list_voice_orders(tenant_id: str = Depends(get_tenant_id), status: str = None):
    """List voice/chat orders"""
    query = supabase.table("onyx_voice_orders").select("*").eq(
        "tenant_id", tenant_id
    ).order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data


@app.patch("/api/orders/voice/{order_id}")
async def update_voice_order(
    order_id: str,
    status: str,
    tenant_id: str = Depends(get_tenant_id),
):
    """Update voice order status (confirmed, preparing, ready, etc.)"""
    update_data = {"status": status}
    if status == "confirmed":
        update_data["confirmed_at"] = datetime.utcnow().isoformat()
    elif status == "ready":
        update_data["ready_at"] = datetime.utcnow().isoformat()

    result = supabase.table("onyx_voice_orders").update(update_data).eq(
        "id", order_id
    ).eq("tenant_id", tenant_id).execute()
    return result.data[0] if result.data else {"error": "Not found"}


# ============================================================
# PREDICTIVE COMMERCE ("Your usual?")
# ============================================================
@app.get("/api/predict/{customer_id}")
async def predict_order(customer_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Predict what a customer will order based on their history"""
    return predict_customer_order(customer_id, tenant_id)


@app.get("/api/predict/accuracy")
async def prediction_accuracy(tenant_id: str = Depends(get_tenant_id)):
    """Check prediction accuracy over time"""
    predictions = supabase.table("onyx_customer_predictions").select(
        "was_accurate, prediction_confidence"
    ).eq("tenant_id", tenant_id).execute()

    if not predictions.data:
        return {"accuracy": None, "message": "No predictions to evaluate yet"}

    evaluated = [p for p in predictions.data if p.get("was_accurate") is not None]
    if not evaluated:
        return {"accuracy": None, "total_predictions": len(predictions.data), "evaluated": 0}

    accurate = sum(1 for p in evaluated if p["was_accurate"])

    return {
        "accuracy": round(accurate / len(evaluated) * 100, 1),
        "total_predictions": len(predictions.data),
        "evaluated": len(evaluated),
        "accurate": accurate,
    }


# ============================================================
# HEALTH
# ============================================================
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "onyx-platform",
        "version": "3.0.0",
        "tagline": "The Protocol Layer for Neighborhood Commerce",
        "merchant_features": {
            "pos_core": True,
            "ai_chat": True,
            "receipt_scanner": True,
            "vendor_bill_scanner": True,
            "receipt_lottery": True,
            "smart_pricing": True,
            "earned_wage_access": True,
            "neighborhood_network": True,
            "dead_stock_marketplace": True,
        },
        "consumer_features": {
            "customer_profiles": True,
            "loyalty_wallet": True,
            "qr_receipts": True,
            "social_clout": True,
            "prediction_market": True,
            "fashion_drops": True,
            "voice_commerce": True,
            "predictive_commerce": True,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
