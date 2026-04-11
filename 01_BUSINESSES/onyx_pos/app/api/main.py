"""
Onyx POS -- FastAPI Backend
Built by SaaS Factory: Amara Osei (backend), Zara Khoury (security), Leo Marchetti (AI)
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Request
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
)

app = FastAPI(title="Onyx POS API", version="1.0.0")

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

    return {
        "transaction_id": tx_id,
        "subtotal": float(subtotal),
        "tax": float(total_tax),
        "total": float(total),
        "change_due": float(max(change_due, Decimal("0"))),
        "items": len(line_items),
    }


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
        supabase.table("onyx_tenants").update({
            "stripe_subscription_id": session.get("subscription"),
            "plan_status": "active",
        }).eq("id", tenant_id).execute()

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        supabase.table("onyx_tenants").update({
            "plan_status": "canceled",
        }).eq("stripe_subscription_id", sub["id"]).execute()

    return {"status": "ok"}


# ============================================================
# HEALTH
# ============================================================
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "onyx-pos", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8600)
