# OnyxOS - Integration Platform Architecture

## Vision

**OnyxOS is a unified business operating system that integrates best-in-class services:**

```
┌─────────────────────────────────────────┐
│         OnyxOS Dashboard                │
│   (Unified View of Everything)          │
└─────────────────────────────────────────┘
           │
           ├── OnyxPOS (Transactions, Inventory)
           │
           ├── OnyxPayroll (Gusto Integration)
           │
           ├── OnyxCommerce (Shopify Integration)
           │
           └── OnyxPayments (Square/Stripe Integration)
```

## What Customers Bring

Customers set up their own accounts and bring API keys:

1. **Gusto Account** (~$40/mo + $6/employee)
   - Handles: Payroll, tax filing, W-2s, direct deposits
   - OnyxOS: Syncs time clock hours, shows labor costs

2. **Shopify Account** (~$29-299/mo depending on plan)
   - Handles: Online store, product pages, checkout, shipping
   - OnyxOS: Syncs inventory, shows online + offline sales together

3. **Square Account** (Free, 2.6% + 10¢ per transaction)
   - Handles: Payment processing (alternative to Stripe)
   - OnyxOS: Process POS transactions through Square

4. **Stripe Account** (Free, 2.9% + 30¢ per transaction)
   - Handles: Payment processing (alternative to Square)
   - OnyxOS: Process POS transactions through Stripe

## What OnyxOS Provides

**You charge: $400/mo for unified integration**

1. **Single Dashboard** - See everything in one place
2. **Unified Inventory** - Sync between POS, Shopify, and warehouse
3. **Combined Reporting** - Online + offline sales, labor costs, profit margins
4. **Automated Workflows** - Sales → Inventory → Shopify sync → Payroll hours
5. **Owner Intelligence** - Profit dashboards, dead stock alerts, labor cost %

## Integration Modules

### 0. OnyxAI (Business Assistant - NEW)
**Status:** ❌ Not Started (HIGH VALUE)

What It Does:
- AI business advisor trained on customer's specific business
- Answers questions about inventory, sales, profit margins
- Provides actionable recommendations
- Conversational interface (chat)

Example Conversations:
```
Owner: "How much profit did I make last week?"
OnyxAI: "Last week you made $3,241 in revenue with $1,456 in COGS,
         giving you $1,785 gross profit (55% margin). This is up 12%
         from the week before. Your top seller was Cold Brew (+$420)."

Owner: "Why is my labor cost so high?"
OnyxAI: "Your labor cost is currently 32% of revenue, which is above
         the restaurant industry target of 25-30%. You scheduled
         Sarah for 45 hours last week but only did $2,100 in sales.
         Consider reducing her Thursday shift by 3 hours."

Owner: "What should I order from my supplier?"
OnyxAI: "Based on FIFO analysis, you need to reorder:
         - Whole beans (12 bags, you have 3 days left)
         - Oat milk (6 cartons, you have 2 days left)
         Your dead stock items are: Vanilla syrup (no sales in 90 days)"
```

Technology Stack:
- **OpenAI GPT-4** or **Claude Sonnet** for conversational AI
- **RAG (Retrieval Augmented Generation)** - Train on customer's business data
- **Function Calling** - Access live database for real-time answers

API Endpoints:
```python
POST /api/v1/ai/chat
  → Send message, get AI response
  → Body: {"message": "How much profit did I make?"}
  → Response: {"message": "...", "data": {...}, "actions": [...]}

POST /api/v1/ai/analyze
  → Deep business analysis with recommendations
  → Returns: profit insights, labor optimization, inventory suggestions

GET /api/v1/ai/daily-brief
  → Morning summary of key metrics and action items
```

AI Implementation:
```python
import anthropic  # or openai

client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

def get_business_context(tenant_id):
    """Fetch customer's business data for AI context"""
    # Get profit analysis
    profit = OwnerAnalytics.get_profit_analysis(db, tenant_id)

    # Get labor costs
    labor = OwnerAnalytics.get_labor_analysis(db, tenant_id)

    # Get inventory status
    inventory = OwnerAnalytics.get_inventory_valuation(db, tenant_id)

    return {
        "business_name": tenant.business_name,
        "revenue": profit['revenue'],
        "profit_margin": profit['margin_percent'],
        "labor_cost_percent": labor['labor_cost_percent'],
        "dead_stock_count": inventory['dead_stock_count']
    }

def chat_with_ai(tenant_id, user_message):
    """Send user question to AI with business context"""
    context = get_business_context(tenant_id)

    prompt = f"""You are OnyxAI, a business advisor for {context['business_name']}.

Current Business Metrics:
- Revenue: ${context['revenue']:,.2f}
- Profit Margin: {context['profit_margin']:.1f}%
- Labor Cost: {context['labor_cost_percent']:.1f}%
- Dead Stock Items: {context['dead_stock_count']}

Owner Question: {user_message}

Provide a helpful, actionable answer with specific numbers and recommendations."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text
```

Frontend Chat Interface:
```jsx
// frontend/src/components/OnyxAI.jsx

function OnyxAI() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const sendMessage = async () => {
    const response = await api.post('/ai/chat', { message: input });
    setMessages([...messages,
      { role: 'user', content: input },
      { role: 'ai', content: response.data.message }
    ]);
  };

  return (
    <div className="ai-chat">
      <h2>OnyxAI Business Assistant</h2>
      {messages.map((msg, i) => (
        <div key={i} className={msg.role}>
          {msg.role === 'ai' ? '🤖' : '👤'} {msg.content}
        </div>
      ))}
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        placeholder="Ask me about your business..."
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}
```

Pricing for AI Feature:
- **OnyxOS + AI:** $450/mo (includes AI assistant)
- **AI Only Add-On:** +$50/mo
- **API Costs:** ~$5-20/mo per customer (OpenAI/Anthropic usage)
- **Your Margin:** $30-45/mo profit per customer

### 1. OnyxPOS (Core Module - Already Built)
**Status:** ✅ Complete

Features:
- FIFO inventory tracking
- Multi-payment support (cash, card, crypto)
- Time clock & scheduling
- Owner dashboards (profit, labor, inventory)
- PWA for offline use

### 2. OnyxPayroll (Gusto Integration)
**Status:** ✅ 80% Complete

What's Done:
- Self-service Gusto setup
- API connection endpoints
- Time clock hour tracking

What's Needed:
- Auto-sync hours to Gusto (webhook)
- Labor cost analytics integration
- Payroll run approval workflow

API Endpoints Needed:
```python
POST /api/v1/gusto/sync-hours
  → Sends time clock hours to Gusto for payroll

GET /api/v1/gusto/employees
  → Fetches employee list from Gusto

POST /api/v1/gusto/approve-payroll
  → Owner approves payroll before Gusto processes it
```

### 3. OnyxCommerce (Shopify Integration)
**Status:** ❌ Not Started (Priority)

What It Does:
- Customer connects their Shopify store
- Inventory syncs bidirectionally (POS ↔ Shopify)
- Online sales show in OnyxOS dashboard
- Combined reporting (online + offline revenue)

Customer Flow:
```
1. Customer has Shopify store (e.g., mycoffeeshop.myshopify.com)
2. Creates private app in Shopify Admin
3. Copies API credentials
4. Enters in OnyxOS settings
5. OnyxOS syncs inventory + sales automatically
```

API Endpoints Needed:
```python
POST /api/v1/shopify/connect
  → Save Shopify credentials (shop URL, API key, password)

POST /api/v1/shopify/sync-inventory
  → Push OnyxPOS inventory to Shopify

GET /api/v1/shopify/orders
  → Fetch online orders from Shopify

POST /api/v1/shopify/webhooks/order-created
  → Webhook when customer buys online (update inventory)
```

Shopify API Integration:
```python
import requests

# Shopify Admin API
SHOP_URL = "mycoffeeshop.myshopify.com"
API_KEY = customer_shopify_api_key
PASSWORD = customer_shopify_password

# Get products from Shopify
response = requests.get(
    f"https://{API_KEY}:{PASSWORD}@{SHOP_URL}/admin/api/2024-01/products.json"
)

# Update inventory in Shopify
requests.put(
    f"https://{API_KEY}:{PASSWORD}@{SHOP_URL}/admin/api/2024-01/inventory_levels/set.json",
    json={"inventory_item_id": item_id, "available": quantity}
)
```

### 4. OnyxPayments (Square Integration)
**Status:** ❌ Not Started

What It Does:
- Alternative to Stripe for payment processing
- Use Square's lower fees (2.6% + 10¢ vs Stripe 2.9% + 30¢)
- Process POS transactions through Square API

Customer Flow:
```
1. Customer creates Square account (free)
2. Gets Square application ID + access token
3. Enters in OnyxOS payment settings
4. OnyxPOS transactions charge through Square
```

API Endpoints Needed:
```python
POST /api/v1/square/connect
  → Save Square credentials

POST /api/v1/square/charge
  → Process payment through Square

GET /api/v1/square/transactions
  → Fetch Square transaction history
```

Square API Integration:
```python
from square.client import Client

client = Client(
    access_token=customer_square_access_token,
    environment='production'
)

# Process payment
result = client.payments.create_payment(
    body={
        "source_id": nonce,
        "amount_money": {"amount": 2500, "currency": "USD"},
        "location_id": location_id
    }
)
```

## Database Schema Updates Needed

### Add Integration Credentials to Tenant Model

```python
# backend/models.py

class Tenant(Base):
    # ... existing fields ...

    # Shopify Integration
    shopify_shop_url = Column(String(255))
    shopify_api_key = Column(Text)  # Encrypted
    shopify_password = Column(Text)  # Encrypted
    shopify_status = Column(String(50))  # 'not_connected', 'connected', 'error'
    shopify_connected_at = Column(DateTime)

    # Square Integration
    square_application_id = Column(String(255))
    square_access_token = Column(Text)  # Encrypted
    square_location_id = Column(String(255))
    square_status = Column(String(50))
    square_connected_at = Column(DateTime)

    # Gusto (already done)
    gusto_api_token = Column(Text)
    gusto_company_uuid = Column(String(255))
    gusto_status = Column(String(50))
    gusto_connected_at = Column(DateTime)
```

## Revenue Model Update

**New Pricing:**
- **OnyxOS Complete:** $400/mo (all integrations included)
- **OnyxPOS Only:** $249/mo (no integrations)
- **Add Shopify Sync:** +$75/mo
- **Add Square/Stripe:** Included in all plans
- **Add Gusto Payroll:** +$149/mo

**Customer Costs (They Pay Separately):**
- Shopify: $29-299/mo (they choose plan)
- Gusto: ~$40/mo + $6/employee
- Square: Free (2.6% + 10¢ per transaction)
- Stripe: Free (2.9% + 30¢ per transaction)

**Example Total Cost for Customer:**
- OnyxOS: $400/mo
- Shopify Basic: $29/mo
- Gusto (5 employees): $70/mo
- Square: Pay-per-transaction
- **Total: $499/mo** for complete business system

## Implementation Priority

### Phase 1: Fix Critical Bugs (NOW)
- [x] Fix inventory import permission error
- [ ] Add Google OAuth login
- [ ] Add auto-generated SKUs
- [ ] Add QR code generation

### Phase 2: Shopify Integration (Week 1-2)
- [ ] Create Shopify connection endpoint
- [ ] Inventory sync (OnyxPOS → Shopify)
- [ ] Order webhook (Shopify → OnyxPOS)
- [ ] Combined sales dashboard

### Phase 3: Square Integration (Week 3)
- [ ] Square payment processing
- [ ] Transaction sync
- [ ] Payment method selection in POS

### Phase 4: Gusto Enhancement (Week 4)
- [ ] Auto-sync time clock hours
- [ ] Payroll approval workflow
- [ ] Labor cost integration

## Technical Architecture

### API Structure

```
backend/
├── api/
│   ├── shopify_integration.py    # NEW
│   ├── square_integration.py     # NEW
│   ├── gusto_setup.py            # EXISTS (enhance)
│   └── integrations_dashboard.py # NEW (unified view)
```

### Services Layer

```
backend/services/
├── shopify_service.py    # Shopify API wrapper
├── square_service.py     # Square API wrapper
├── gusto_service.py      # Gusto API wrapper
└── sync_engine.py        # Inventory sync coordinator
```

### Frontend Integration Pages

```
frontend/src/pages/
├── IntegrationsHub.jsx      # All integrations overview
├── ShopifyConnect.jsx       # Shopify setup wizard
├── SquareConnect.jsx        # Square setup wizard
└── GustoConnect.jsx         # Gusto setup wizard
```

## Security Considerations

1. **Encrypt API Keys** - Use Fernet encryption for stored credentials
2. **OAuth 2.0** - Use OAuth where available (Shopify supports it)
3. **Webhook Validation** - Verify webhook signatures
4. **Rate Limiting** - Respect API rate limits (Shopify: 2 req/sec)
5. **Error Handling** - Graceful degradation if integration fails

## Competitive Advantage

**vs. Shopify POS:**
- Shopify POS is expensive ($89/mo + $29/mo Shopify)
- OnyxOS: Better profit analytics, FIFO tracking, labor integration

**vs. Square:**
- Square locks you into Square payments only
- OnyxOS: Choose Square OR Stripe, better reporting

**vs. Toast:**
- Toast has GMV fees (up to $165/mo at $55k revenue)
- OnyxOS: Flat $400/mo, no GMV fees

**OnyxOS Unique Value:**
- **Only platform** with POS + E-commerce + Payroll + Profit Analytics
- Bring your own payment processor (Square or Stripe)
- Owner intelligence dashboards (not just transaction logs)
- Self-hosted integrations (customer controls their API keys)

## Next Steps

1. **Fix critical bugs** (inventory import, Google OAuth)
2. **Build Shopify integration** (biggest value-add)
3. **Test end-to-end** (signup → connect Shopify → sync inventory → make sale)
4. **Launch beta** (get 5 customers to test integrations)
5. **Iterate** based on feedback

## Resources

- **Shopify API Docs:** https://shopify.dev/docs/api/admin-rest
- **Square API Docs:** https://developer.squareup.com/reference/square
- **Gusto API Docs:** https://docs.gusto.com/
- **OAuth Best Practices:** https://oauth.net/2/

---

**This transforms OnyxOS from "just another POS" into a true business operating system.**
