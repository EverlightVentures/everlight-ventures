# OnyxOS Build Roadmap

## Current Status: 60% Complete

### ✅ What's Done (Ready for Launch)
- Backend API (Flask, multi-tenant)
- Frontend PWA (React, offline support)
- FIFO inventory tracking
- Owner intelligence dashboards
- Stripe billing integration
- Gusto payroll setup (self-service)
- Weekly email digests
- Time clock & scheduling
- Basic POS transactions

### ❌ What's Missing (Blocking Launch)
1. **Google OAuth Login** (easy signup)
2. **Auto-generated SKUs** (convenience)
3. **QR Code Generation** (product labels)
4. **Inventory import bug** (critical!)

### 🚀 What Makes OnyxOS Unique (Future Features)
5. **Shopify Integration** (e-commerce sync)
6. **Square Integration** (payment alternative)
7. **OnyxAI Assistant** (business advisor)

---

## Phase 1: Fix Critical Bugs (2-3 Days)
**Goal:** Make current features actually work

### 1. Fix Inventory Import Permission Bug
**Status:** In Progress
**Impact:** HIGH (blocks onboarding)

Problem: Middleware blocks inventory import during trial
Fix: Ensure trial users have full access

```python
# backend/middleware/subscription_guard.py
# Already allows status='trial', need to debug why it's not working
```

### 2. Add Google OAuth Login
**Status:** Not Started
**Impact:** HIGH (easier signup)

What It Does:
- "Sign up with Google" button
- No password required
- Faster onboarding

Implementation:
```bash
# Install library
pip install google-auth google-auth-oauthlib

# Add to backend/api/auth.py
@auth_bp.route('/google/callback', methods=['POST'])
def google_login():
    # Verify Google token
    # Create/login user
    # Return JWT
```

**Time:** 4-6 hours

### 3. Add Auto-Generated SKUs
**Status:** Not Started
**Impact:** MEDIUM (convenience)

What It Does:
- When creating product, SKU auto-fills if left blank
- Format: CATEGORY-YYYYMMDD-XXXX
- Example: COFFEE-20251229-0001

Implementation:
```python
# backend/models.py - Item model
def generate_sku(tenant_id, category=None):
    from datetime import datetime
    date_str = datetime.now().strftime('%Y%m%d')

    # Get last SKU for today
    last_item = db.query(Item).filter(
        Item.tenant_id == tenant_id,
        Item.sku.like(f'%-{date_str}-%')
    ).order_by(Item.created_at.desc()).first()

    if last_item:
        # Extract number and increment
        seq = int(last_item.sku.split('-')[-1]) + 1
    else:
        seq = 1

    prefix = category[:3].upper() if category else 'ITM'
    return f'{prefix}-{date_str}-{seq:04d}'
```

**Time:** 2-3 hours

### 4. Add QR Code Generation
**Status:** Not Started
**Impact:** MEDIUM (nice to have)

What It Does:
- Generate QR code for each product SKU
- Print on labels for quick scanning
- Returns PNG image

Implementation:
```bash
# Install library
pip install qrcode[pil]

# Add endpoint
GET /api/v1/inventory/items/{item_id}/qr-code
  → Returns PNG image of QR code
```

```python
import qrcode
from io import BytesIO

@inventory_bp.route('/items/<item_id>/qr-code', methods=['GET'])
def get_qr_code(item_id):
    item = db.query(Item).get(item_id)

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(item.sku)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Return as PNG
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return send_file(buf, mimetype='image/png')
```

**Time:** 2-3 hours

---

## Phase 2: Shopify Integration (1-2 Weeks)
**Goal:** Sync inventory with customer's online store

### Features
1. **Connection Setup**
   - Customer enters Shopify store URL
   - Creates private app in Shopify
   - Saves API credentials in OnyxOS

2. **Inventory Sync**
   - Push OnyxPOS products to Shopify
   - Bi-directional updates (POS ↔ Shopify)
   - Image upload support

3. **Order Import**
   - Fetch online orders from Shopify
   - Show in unified sales dashboard
   - Update inventory when online sale happens

4. **Webhooks**
   - Real-time order notifications
   - Inventory updates from Shopify admin

### Implementation Files
```
backend/
├── api/shopify_integration.py
├── services/shopify_service.py
└── models.py (add shopify fields to Tenant)

frontend/
└── src/pages/ShopifyConnect.jsx
```

**Time Estimate:** 40-60 hours

---

## Phase 3: Square Integration (1 Week)
**Goal:** Alternative payment processor to Stripe

### Features
1. **Connection Setup**
   - Square account credentials
   - Location selection

2. **Payment Processing**
   - Process POS transactions through Square
   - Lower fees: 2.6% + 10¢ (vs Stripe 2.9% + 30¢)

3. **Transaction Sync**
   - Import Square transaction history
   - Unified reporting

### Implementation Files
```
backend/
├── api/square_integration.py
├── services/square_service.py
└── models.py (add square fields)

frontend/
└── src/pages/PaymentSettings.jsx
```

**Time Estimate:** 20-30 hours

---

## Phase 4: OnyxAI Assistant (2-3 Weeks)
**Goal:** AI business advisor for each customer

### Features
1. **Chat Interface**
   - Ask questions about business
   - Get answers with real data
   - Actionable recommendations

2. **Daily Brief**
   - Morning summary email
   - Key metrics + action items
   - AI-generated insights

3. **Proactive Alerts**
   - "Your labor cost is high this week"
   - "You should reorder coffee beans"
   - "Dead stock alert: 5 items"

### Implementation
```bash
# Install AI library
pip install anthropic  # or openai

# Create endpoints
POST /api/v1/ai/chat
GET /api/v1/ai/daily-brief
POST /api/v1/ai/analyze
```

```python
# backend/services/ai_service.py

import anthropic

client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

def chat(tenant_id, message):
    # Get business context
    context = get_business_metrics(tenant_id)

    # Send to Claude
    response = client.messages.create(
        model="claude-sonnet-4-5",
        system=f"You are OnyxAI, business advisor for {context['business_name']}",
        messages=[{"role": "user", "content": message}]
    )

    return response.content[0].text
```

**Time Estimate:** 60-80 hours

---

## Launch Strategy

### Minimum Viable Product (MVP)
**What you need to launch TODAY:**
1. ✅ Working POS (done)
2. ✅ Stripe billing (done)
3. ✅ Gusto setup (done)
4. ❌ Fix inventory import bug (1 hour)
5. ❌ Google OAuth (6 hours)
6. ❌ Auto SKU generation (3 hours)

**Total:** 10 hours to MVP

### Full Product (v1.0)
**What makes you competitive:**
- MVP features ✅
- Shopify integration ✅
- Square integration ✅
- QR codes ✅

**Total:** ~100 hours (2.5 weeks full-time)

### Premium Product (v2.0)
**What makes you UNIQUE:**
- All v1.0 features ✅
- OnyxAI assistant ✅
- Advanced analytics ✅
- Multi-location support ✅

**Total:** ~180 hours (1 month full-time)

---

## Revenue Projections

### Pricing Tiers
1. **OnyxPOS Only:** $249/mo
   - Core POS features
   - No integrations

2. **OnyxOS Standard:** $400/mo
   - POS + Shopify + Square + Gusto
   - All integrations

3. **OnyxOS + AI:** $450/mo
   - Everything + AI assistant
   - Daily briefs, proactive alerts

### Break-Even Analysis

**Costs per customer:**
- Hosting: $20/mo (Railway/Heroku)
- Email: $1/mo (Resend)
- AI API: $10/mo (Anthropic/OpenAI)
- Support: $50/mo (amortized)
- **Total:** $81/mo

**Revenue per customer:**
- OnyxOS Standard: $400/mo
- Costs: $81/mo
- **Profit: $319/mo per customer**

**Break-even:** 1 customer

**Target (Year 1):**
- 50 customers at $400/mo
- Revenue: $20,000/mo ($240k/year)
- Costs: $4,050/mo
- **Profit: $15,950/mo ($191k/year)**

---

## Next 48 Hours

### TODAY (Day 1)
- [ ] Fix inventory import bug (1 hour)
- [ ] Test signup → import → sale flow (1 hour)
- [ ] Add Google OAuth backend (4 hours)
- [ ] Add Google OAuth frontend (2 hours)

**Total: 8 hours**

### TOMORROW (Day 2)
- [ ] Add auto-generated SKUs (3 hours)
- [ ] Add QR code generation (3 hours)
- [ ] Test all new features (2 hours)

**Total: 8 hours**

### Day 3: LAUNCH MVP
- [ ] Deploy to Railway/Vercel
- [ ] Test in production
- [ ] Get first beta customer
- [ ] Start building Shopify integration

---

## Focus Priority

**Do FIRST:**
1. Fix bugs (inventory import)
2. Add Google OAuth (easier signup)
3. Launch MVP and get paying customers

**Do NEXT:**
4. Build Shopify integration (biggest value-add)
5. Build Square integration (competitive advantage)

**Do LAST:**
6. Build AI assistant (premium differentiator)

---

## Success Metrics

**Week 1:**
- [ ] MVP launched
- [ ] 1 beta customer signed up
- [ ] No critical bugs

**Month 1:**
- [ ] 5 paying customers
- [ ] Shopify integration live
- [ ] $2,000 MRR

**Month 3:**
- [ ] 20 paying customers
- [ ] AI assistant beta
- [ ] $8,000 MRR

**Month 6:**
- [ ] 50 paying customers
- [ ] All integrations live
- [ ] $20,000 MRR

---

**Current Status:** Ready to fix bugs and launch MVP
**Time to MVP:** 10 hours
**Time to v1.0:** 2.5 weeks
**Time to v2.0:** 1 month

Let's build this! 🚀
