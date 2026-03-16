# Everlight Ventures -- Stripe Payment Infrastructure Architecture

**Owner:** Everlight Ventures
**Last Updated:** 2026-03-06
**Status:** Design Document (Pre-Implementation)
**Stack:** Stripe + Lovable (Supabase) + Django Ops Backend

---

## Table of Contents

1. [Product Catalog](#1-stripe-product-catalog)
2. [Supabase / Lovable Side](#2-supabase--lovable-side)
3. [Django Ops Backend](#3-django-ops-backend)
4. [Stripe Configuration](#4-stripe-configuration)
5. [Webhook Event Matrix](#5-webhook-event-matrix)
6. [Revenue Dashboard](#6-revenue-dashboard)
7. [Implementation Sequence](#7-implementation-sequence)
8. [Security Checklist](#8-security-checklist)

---

## 1. Stripe Product Catalog

Every product and price that must exist in Stripe. Create these via the Stripe Dashboard or API before any integration code runs.

### 1A. ONYX POS

| Stripe Product Name       | Price ID Label            | Amount    | Billing   | Trial  | Notes                        |
|---------------------------|---------------------------|-----------|-----------|--------|------------------------------|
| Onyx POS -- Monthly       | onyx_pos_monthly          | $49.00    | Recurring | 14 day | Auto-bill after trial ends   |

- **Stripe Mode:** Subscription with `trial_period_days: 14`
- **Customer Portal:** Enabled (cancel, update payment method, view invoices)

### 1B. HIVE MIND SaaS

| Stripe Product Name            | Price ID Label             | Amount     | Billing   | Trial  | Notes                        |
|--------------------------------|----------------------------|------------|-----------|--------|------------------------------|
| Hive Mind -- Starter           | hivemind_starter_monthly   | $29.00     | Recurring | None   | Invite-only during waitlist  |
| Hive Mind -- Pro               | hivemind_pro_monthly       | $79.00     | Recurring | None   |                              |
| Hive Mind -- Enterprise        | hivemind_enterprise_monthly| $149.00    | Recurring | None   |                              |
| Hive Mind -- Founding Starter  | hivemind_founding_starter  | $19.00     | Recurring | None   | Locked price, coupon-based   |
| Hive Mind -- Founding Pro      | hivemind_founding_pro      | $49.00     | Recurring | None   | Locked price, coupon-based   |
| Hive Mind -- Founding Enterprise| hivemind_founding_enterprise| $99.00   | Recurring | None   | Locked price, coupon-based   |

- **Founding Member Pricing:** Create separate prices (not coupons) so the price is truly locked for life. Alternatively, use a Stripe Coupon with `duration: forever` applied at checkout.
- **Recommendation:** Use separate price objects. Simpler to track, no coupon expiry risk.

### 1C. Book Sales (Direct)

| Stripe Product Name                | Price ID Label              | Amount  | Billing  | Notes                          |
|------------------------------------|-----------------------------|---------|----------|--------------------------------|
| Beyond the Veil -- Ebook           | btv_ebook                   | $14.99  | One-time | Instant download after payment |
| Beyond the Veil -- Paperback       | btv_paperback               | $24.99  | One-time | Triggers shipping fulfillment  |
| Everlight Kids -- Ebook (Tier 1)   | kids_ebook_t1               | $9.99   | One-time | Per-title, clone as needed     |
| Everlight Kids -- Ebook (Tier 2)   | kids_ebook_t2               | $12.99  | One-time |                                |
| Everlight Kids -- Paperback        | kids_paperback              | $14.99  | One-time | Triggers shipping fulfillment  |

- **Per-Title Products:** Each book title should be its own Stripe Product with metadata `{ "book_slug": "beyond-the-veil", "format": "ebook" }`.
- **Digital Fulfillment:** On `checkout.session.completed`, generate a signed S3/R2 download URL valid for 72 hours, email to customer.
- **Physical Fulfillment:** On `checkout.session.completed`, create a fulfillment record in Django and trigger shipping workflow.

### 1D. Alley Kingz (Future)

| Integration       | Notes                                                      |
|--------------------|------------------------------------------------------------|
| iOS / Android IAP  | Apple App Store + Google Play billing -- NOT Stripe         |
| NFT Fiat On-Ramp   | Stripe Checkout for purchasing credits/NFTs via fiat       |

- **No immediate Stripe setup needed.** When the NFT marketplace launches, create a `alley_kingz_credits` product for fiat-to-crypto on-ramp.

### 1E. HIM Loadout

- **No Stripe integration.** Revenue comes from affiliate links (Amazon Associates, brand partnerships). Track clicks/conversions in Django, not payments.

### 1F. Everlight Logistics

| Stripe Product Name               | Price ID Label               | Amount     | Billing     | Notes                       |
|------------------------------------|------------------------------|------------|-------------|-----------------------------|
| Logistics -- Monthly Retainer      | logistics_retainer_monthly   | Variable   | Invoice     | Custom per client            |
| Logistics -- Project Invoice       | logistics_project            | Variable   | One-time    | Custom per project           |

- **Use Stripe Invoicing API**, not Checkout. Create invoices programmatically from Django.
- Each B2B client gets a Stripe Customer with `metadata: { "client_type": "logistics", "company": "..." }`.

---

## 2. Supabase / Lovable Side

This is the public-facing layer. Lovable generates the frontend; Supabase handles auth, database, and Edge Functions for Stripe.

### 2A. Database Schema (Supabase / Postgres)

```sql
-- Customers table: links Supabase auth users to Stripe
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_customer_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Products table: mirror of Stripe product catalog
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_product_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Prices table: mirror of Stripe prices
CREATE TABLE prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_price_id TEXT UNIQUE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    amount INTEGER NOT NULL,            -- in cents
    currency TEXT DEFAULT 'usd',
    interval TEXT,                       -- 'month', 'year', or NULL for one-time
    trial_period_days INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Subscriptions table: active/past subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT UNIQUE NOT NULL,
    stripe_price_id TEXT NOT NULL,
    status TEXT NOT NULL,               -- 'trialing', 'active', 'canceled', 'past_due', 'unpaid'
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    trial_start TIMESTAMPTZ,
    trial_end TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- One-time purchases (books, etc.)
CREATE TABLE purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    stripe_payment_intent_id TEXT UNIQUE NOT NULL,
    stripe_price_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT DEFAULT 'usd',
    status TEXT NOT NULL,               -- 'succeeded', 'refunded', 'failed'
    product_metadata JSONB DEFAULT '{}'::jsonb,
    fulfillment_status TEXT DEFAULT 'pending',  -- 'pending', 'fulfilled', 'shipped'
    download_url TEXT,
    download_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Waitlist (Hive Mind)
CREATE TABLE waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    invited BOOLEAN DEFAULT false,
    invited_at TIMESTAMPTZ,
    founding_member BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS policies (critical)
-- customers: users can only read their own row
-- subscriptions: users can only read their own
-- purchases: users can only read their own
-- waitlist: insert-only for anon, read for service_role
```

### 2B. Edge Functions (Supabase)

File structure inside `supabase/functions/`:

```
supabase/functions/
  create-checkout-session/
    index.ts          -- Creates Stripe Checkout Session
  create-portal-session/
    index.ts          -- Creates Stripe Customer Portal session
  stripe-webhook/
    index.ts          -- Receives and processes all Stripe webhooks
  sync-products/
    index.ts          -- One-time sync: pull products/prices from Stripe into DB
```

#### `create-checkout-session/index.ts`

```
Function: serve(req: Request) -> Response

Input (JSON body):
  - price_id: string        -- Stripe Price ID
  - mode: 'subscription' | 'payment'
  - success_url: string
  - cancel_url: string
  - customer_email?: string  -- Optional, for guest checkout (books)
  - metadata?: object        -- e.g. { product: 'onyx_pos', tier: 'starter' }

Logic:
  1. Authenticate user via Supabase JWT (skip for guest book purchases)
  2. Look up or create Stripe Customer (link to Supabase user_id)
  3. Call stripe.checkout.sessions.create({
       customer: stripe_customer_id,
       line_items: [{ price: price_id, quantity: 1 }],
       mode: mode,
       success_url: success_url,
       cancel_url: cancel_url,
       subscription_data: { trial_period_days: 14 }  // only for Onyx
       metadata: metadata
     })
  4. Return { url: session.url }

Response: { url: string }
```

#### `create-portal-session/index.ts`

```
Function: serve(req: Request) -> Response

Input (JSON body):
  - return_url: string

Logic:
  1. Authenticate user via Supabase JWT
  2. Look up stripe_customer_id from customers table
  3. Call stripe.billingPortal.sessions.create({
       customer: stripe_customer_id,
       return_url: return_url
     })
  4. Return { url: session.url }

Response: { url: string }
```

#### `stripe-webhook/index.ts`

```
Function: serve(req: Request) -> Response

Logic:
  1. Read raw body and Stripe-Signature header
  2. Verify signature using STRIPE_WEBHOOK_SECRET
  3. Parse event type and route:

  Event handlers:
    checkout.session.completed:
      - If mode == 'subscription':
          Upsert subscription record in subscriptions table
          Set status to 'active' or 'trialing'
      - If mode == 'payment':
          Insert purchase record in purchases table
          If product is digital book:
            Generate signed download URL, store in purchases.download_url
            Send download email via Resend/Postmark
          If product is physical book:
            Set fulfillment_status = 'pending'
            POST to Django /api/fulfillment/create/ with order details

    customer.subscription.updated:
      - Update subscription status, period dates in subscriptions table

    customer.subscription.deleted:
      - Update subscription status to 'canceled'
      - (Account deactivation handled by RLS -- no active sub = no access)

    invoice.payment_succeeded:
      - Update subscription current_period_end
      - Log revenue event

    invoice.payment_failed:
      - Update subscription status to 'past_due'
      - Trigger dunning email

    payment_intent.succeeded:
      - Update purchase status to 'succeeded' (if not already via checkout.session.completed)

  4. Return 200 OK (always, even if event is unhandled)
```

### 2C. Row-Level Security for Access Gating

```sql
-- Example: Onyx POS features gated by active subscription
CREATE POLICY "onyx_access" ON onyx_data
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM subscriptions s
      JOIN customers c ON s.customer_id = c.id
      WHERE c.user_id = auth.uid()
      AND s.stripe_price_id LIKE 'price_%'  -- Onyx price IDs
      AND s.status IN ('active', 'trialing')
    )
  );
```

This means access control is declarative -- no middleware needed. If the subscription is not active/trialing, Supabase returns zero rows.

---

## 3. Django Ops Backend

The Django backend handles internal operations: revenue tracking, fulfillment, Slack notifications, and the admin revenue dashboard.

### 3A. Django App Structure

```
ops_backend/
  manage.py
  ops_backend/
    settings.py
    urls.py
    wsgi.py
  payments/
    __init__.py
    models.py          -- StripeCustomer, StripeSubscription, StripePayment, Revenue
    views.py           -- Webhook receiver, revenue API endpoints
    webhook_handler.py -- Event routing and processing logic
    stripe_sync.py     -- Sync customers/subs from Stripe API on demand
    signals.py         -- Post-save signals for Slack notifications
    admin.py           -- Admin views for payment records
    urls.py
    tests/
      test_webhook.py
      test_revenue.py
  fulfillment/
    __init__.py
    models.py          -- Order, ShippingLabel, FulfillmentStatus
    views.py           -- Fulfillment API (receives from Supabase webhook)
    services.py        -- Shipping provider integration
    admin.py
    urls.py
  dashboard/
    __init__.py
    views.py           -- Revenue dashboard views (MRR, churn, LTV)
    calculators.py     -- MRR calculation, churn rate, LTV formulas
    serializers.py
    urls.py
  notifications/
    __init__.py
    slack.py           -- Slack webhook sender
    email.py           -- Transactional email triggers (Resend/Postmark)
```

### 3B. Django Models

```python
# payments/models.py

class StripeCustomer(models.Model):
    stripe_customer_id = models.CharField(max_length=255, unique=True, db_index=True)
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    product_line = models.CharField(
        max_length=50,
        choices=[
            ('onyx_pos', 'Onyx POS'),
            ('hivemind', 'Hive Mind'),
            ('books', 'Book Sales'),
            ('logistics', 'Everlight Logistics'),
        ]
    )
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['product_line']),
            models.Index(fields=['email']),
        ]


class StripeSubscription(models.Model):
    customer = models.ForeignKey(StripeCustomer, on_delete=models.CASCADE, related_name='subscriptions')
    stripe_subscription_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_price_id = models.CharField(max_length=255)
    status = models.CharField(max_length=50)  # active, trialing, canceled, past_due, unpaid
    amount = models.IntegerField()  # cents
    currency = models.CharField(max_length=10, default='usd')
    current_period_start = models.DateTimeField(null=True)
    current_period_end = models.DateTimeField(null=True)
    trial_start = models.DateTimeField(null=True)
    trial_end = models.DateTimeField(null=True)
    canceled_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['current_period_end']),
        ]


class StripePayment(models.Model):
    customer = models.ForeignKey(StripeCustomer, on_delete=models.CASCADE, related_name='payments')
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_price_id = models.CharField(max_length=255)
    amount = models.IntegerField()  # cents
    currency = models.CharField(max_length=10, default='usd')
    status = models.CharField(max_length=50)  # succeeded, refunded, failed
    product_line = models.CharField(max_length=50)
    product_metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class RevenueEvent(models.Model):
    """Immutable log of every revenue-generating event for analytics."""
    event_type = models.CharField(max_length=50)  # subscription_payment, one_time_purchase, invoice_paid
    product_line = models.CharField(max_length=50)
    amount = models.IntegerField()  # cents
    currency = models.CharField(max_length=10, default='usd')
    stripe_customer_id = models.CharField(max_length=255)
    stripe_event_id = models.CharField(max_length=255, unique=True)  # idempotency
    occurred_at = models.DateTimeField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['product_line', 'occurred_at']),
            models.Index(fields=['occurred_at']),
        ]
```

```python
# fulfillment/models.py

class Order(models.Model):
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    customer_email = models.EmailField()
    customer_name = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    product_type = models.CharField(max_length=20, choices=[('digital', 'Digital'), ('physical', 'Physical')])
    quantity = models.IntegerField(default=1)
    amount = models.IntegerField()  # cents
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('fulfilled', 'Fulfilled'),
            ('shipped', 'Shipped'),
            ('delivered', 'Delivered'),
        ]
    )
    shipping_address = models.JSONField(null=True, blank=True)
    tracking_number = models.CharField(max_length=255, blank=True)
    download_url = models.URLField(blank=True)
    download_expires_at = models.DateTimeField(null=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 3C. Webhook Receiver (Django)

```python
# payments/views.py

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    POST /api/stripe/webhook/

    Verifies Stripe signature, then dispatches to handler.
    Returns 200 on all valid events (even unhandled ones).
    Returns 400 on signature failure.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    # Idempotency check
    if RevenueEvent.objects.filter(stripe_event_id=event['id']).exists():
        return HttpResponse(status=200)

    # Route to handler
    handler = WEBHOOK_HANDLERS.get(event['type'])
    if handler:
        handler(event)

    return HttpResponse(status=200)
```

```python
# payments/webhook_handler.py

WEBHOOK_HANDLERS = {
    'checkout.session.completed': handle_checkout_completed,
    'customer.subscription.created': handle_subscription_created,
    'customer.subscription.updated': handle_subscription_updated,
    'customer.subscription.deleted': handle_subscription_deleted,
    'invoice.payment_succeeded': handle_invoice_paid,
    'invoice.payment_failed': handle_invoice_failed,
    'payment_intent.succeeded': handle_payment_succeeded,
}

def handle_checkout_completed(event):
    """
    Handles both subscription and one-time payment checkouts.
    1. Upsert StripeCustomer
    2. Create StripeSubscription or StripePayment record
    3. Log RevenueEvent
    4. Send Slack notification
    5. If book purchase: trigger fulfillment
    """
    pass  # Implementation

def handle_subscription_updated(event):
    """
    Updates subscription status and period dates.
    Detects downgrades, upgrades, and cancellation scheduling.
    """
    pass

def handle_subscription_deleted(event):
    """
    Marks subscription as canceled.
    Sends Slack churn notification.
    """
    pass

def handle_invoice_paid(event):
    """
    Logs recurring revenue event.
    Updates subscription period dates.
    """
    pass

def handle_invoice_failed(event):
    """
    Marks subscription as past_due.
    Triggers dunning email.
    Sends Slack alert.
    """
    pass

def handle_payment_succeeded(event):
    """
    For one-time payments (books).
    Triggers fulfillment pipeline.
    """
    pass
```

### 3D. Slack Notifications

```python
# notifications/slack.py

import requests
from django.conf import settings

def notify_sale(product_line: str, amount_cents: int, customer_email: str, event_type: str):
    """
    Sends a Slack message on every sale/subscription event.

    Channel: #everlight-revenue
    Format:
      [ONYX POS] New subscription -- $49.00/mo -- customer@email.com
      [BOOKS] Sale -- $14.99 -- Beyond the Veil (ebook) -- customer@email.com
      [HIVEMIND] Churn -- Pro tier -- customer@email.com
    """
    amount_str = f"${amount_cents / 100:.2f}"
    msg = f"[{product_line.upper()}] {event_type} -- {amount_str} -- {customer_email}"

    requests.post(settings.SLACK_WEBHOOK_URL, json={"text": msg}, timeout=5)


def notify_churn(product_line: str, customer_email: str, tier: str):
    """Slack alert for subscription cancellation."""
    msg = f"[{product_line.upper()}] CHURN -- {tier} -- {customer_email}"
    requests.post(settings.SLACK_WEBHOOK_URL, json={"text": msg}, timeout=5)
```

### 3E. Revenue Dashboard Calculations

```python
# dashboard/calculators.py

from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from payments.models import StripeSubscription, RevenueEvent

def calculate_mrr() -> dict:
    """
    Returns current MRR broken down by product line.
    MRR = sum of all active subscription amounts.
    """
    active_subs = StripeSubscription.objects.filter(
        status__in=['active', 'trialing']
    )
    total_mrr = active_subs.aggregate(total=Sum('amount'))['total'] or 0

    by_product = {}
    for sub in active_subs.values('customer__product_line').annotate(mrr=Sum('amount')):
        by_product[sub['customer__product_line']] = sub['mrr']

    return {
        'total_mrr_cents': total_mrr,
        'total_mrr_dollars': total_mrr / 100,
        'by_product': by_product,
        'as_of': datetime.utcnow().isoformat(),
    }


def calculate_churn_rate(days: int = 30) -> dict:
    """
    Churn rate = (canceled in period) / (active at start of period) * 100
    """
    pass  # Implementation


def calculate_ltv(product_line: str) -> dict:
    """
    LTV = Average Monthly Revenue per Customer / Monthly Churn Rate
    """
    pass  # Implementation


def revenue_summary(period: str = 'month') -> dict:
    """
    Returns revenue totals for the given period.
    Periods: 'day', 'week', 'month'
    Breaks down by: subscriptions, one-time, invoices
    """
    pass  # Implementation
```

---

## 4. Stripe Configuration

### 4A. Stripe Dashboard Setup Checklist

1. **Create Products and Prices** per Section 1 above
2. **Enable Customer Portal** (Settings > Billing > Customer Portal)
   - Allow: cancel subscription, update payment method, view invoices
   - Branding: Everlight Ventures logo, colors
3. **Register Webhook Endpoints:**

| Endpoint URL                                          | Events                                                                 |
|-------------------------------------------------------|------------------------------------------------------------------------|
| `https://<supabase-project>.supabase.co/functions/v1/stripe-webhook` | checkout.session.completed, customer.subscription.updated, customer.subscription.deleted, invoice.payment_succeeded, invoice.payment_failed, payment_intent.succeeded |
| `https://ops.everlightventures.com/api/stripe/webhook/` | Same events as above (Django receives a copy for ops/analytics)        |

- **Two endpoints, same events.** Supabase handles user-facing state (access control). Django handles ops (revenue tracking, Slack, fulfillment).

4. **Tax Configuration:**
   - Enable Stripe Tax if selling physical books (sales tax varies by state)
   - Digital goods: configure based on nexus states
   - SaaS subscriptions: generally not taxed in most states, but monitor

5. **Payout Schedule:**
   - Standard: 2-day rolling payouts to business bank account
   - Or weekly on Fridays if cash flow smoothing is preferred

### 4B. Environment Variables

```bash
# .env -- NEVER commit this file

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET_SUPABASE=whsec_...    # For Supabase endpoint
STRIPE_WEBHOOK_SECRET_DJANGO=whsec_...      # For Django endpoint

# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Django
DJANGO_SECRET_KEY=...
DATABASE_URL=postgres://...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../...

# Email (Resend or Postmark)
RESEND_API_KEY=re_...

# Book fulfillment
BOOK_DOWNLOAD_BUCKET=everlight-books
BOOK_DOWNLOAD_URL_EXPIRY_HOURS=72
```

---

## 5. Webhook Event Matrix

Complete mapping of which events go where and what they trigger.

| Stripe Event                        | Supabase Action                          | Django Action                          |
|-------------------------------------|------------------------------------------|----------------------------------------|
| `checkout.session.completed` (sub)  | Upsert subscription, set status          | Log RevenueEvent, Slack notify         |
| `checkout.session.completed` (pay)  | Insert purchase, generate download URL   | Create Order, Slack notify             |
| `customer.subscription.updated`     | Update subscription status/dates         | Update StripeSubscription              |
| `customer.subscription.deleted`     | Set status = canceled                    | Log churn, Slack churn alert           |
| `invoice.payment_succeeded`         | Update period_end                        | Log RevenueEvent                       |
| `invoice.payment_failed`            | Set status = past_due                    | Slack alert, trigger dunning email     |
| `payment_intent.succeeded`          | Update purchase status                   | Update StripePayment                   |

---

## 6. Revenue Dashboard

### 6A. Metrics to Track

| Metric                    | Formula                                              | Update Frequency |
|---------------------------|------------------------------------------------------|------------------|
| MRR (Monthly Recurring)   | Sum of all active subscription amounts               | Real-time        |
| ARR (Annual Recurring)    | MRR * 12                                             | Real-time        |
| Daily Revenue             | Sum of RevenueEvents for today                       | Real-time        |
| Weekly Revenue            | Sum of RevenueEvents for last 7 days                 | Daily            |
| Monthly Revenue           | Sum of RevenueEvents for current month               | Daily            |
| Churn Rate                | Canceled subs / Active subs at period start           | Weekly           |
| LTV                       | Avg revenue per customer / monthly churn rate         | Monthly          |
| Trial-to-Paid Conversion  | Converted trials / Total trials                       | Weekly           |
| Revenue by Product Line   | Grouped sum by product_line                           | Real-time        |

### 6B. Django Dashboard Endpoints

```
GET /api/dashboard/mrr/                -- Current MRR breakdown
GET /api/dashboard/revenue/?period=day -- Revenue for given period
GET /api/dashboard/churn/              -- Churn rate and details
GET /api/dashboard/ltv/               -- LTV by product line
GET /api/dashboard/customers/          -- Customer count by product/status
```

These endpoints feed either a React admin panel or a Streamlit dashboard (at `09_DASHBOARD/`).

---

## 7. Implementation Sequence

Phase order matters. Do not skip ahead.

### Phase 1: Stripe Setup (Day 1)
- [ ] Create all Products and Prices in Stripe Dashboard
- [ ] Enable Customer Portal
- [ ] Register both webhook endpoints (use Stripe CLI for local testing first)
- [ ] Set up `.env` files for both Supabase and Django

### Phase 2: Supabase Schema + Edge Functions (Days 2-3)
- [ ] Run SQL migrations for all tables (customers, products, prices, subscriptions, purchases, waitlist)
- [ ] Enable RLS policies
- [ ] Deploy `create-checkout-session` Edge Function
- [ ] Deploy `create-portal-session` Edge Function
- [ ] Deploy `stripe-webhook` Edge Function
- [ ] Run `sync-products` to populate products/prices tables
- [ ] Test: create a test subscription via Stripe CLI, verify DB updates

### Phase 3: Django Backend (Days 4-5)
- [ ] Create `payments`, `fulfillment`, `dashboard`, `notifications` Django apps
- [ ] Run migrations
- [ ] Implement webhook receiver with signature verification
- [ ] Implement all webhook handlers
- [ ] Implement Slack notifications
- [ ] Test: replay Stripe CLI events, verify Django processing

### Phase 4: Lovable Frontend Integration (Days 6-7)
- [ ] Add "Subscribe" buttons on Onyx POS landing page -- calls `create-checkout-session`
- [ ] Add "Manage Billing" button -- calls `create-portal-session`
- [ ] Add Hive Mind waitlist form -- inserts into waitlist table
- [ ] Add Hive Mind pricing page with checkout buttons (gated by invite)
- [ ] Add book purchase buttons on publishing pages

### Phase 5: Testing and Go-Live (Days 8-10)
- [ ] End-to-end test in Stripe test mode for each product
- [ ] Test trial expiry flow (Stripe test clock)
- [ ] Test cancellation flow
- [ ] Test failed payment / dunning flow
- [ ] Test book purchase -- digital download delivery
- [ ] Test book purchase -- physical fulfillment trigger
- [ ] Verify Slack notifications for all event types
- [ ] Verify revenue dashboard numbers
- [ ] Switch to live Stripe keys
- [ ] Monitor first real transactions

---

## 8. Security Checklist

- [ ] Stripe webhook signatures verified on EVERY request (both Supabase and Django)
- [ ] STRIPE_SECRET_KEY never exposed to frontend -- only used in Edge Functions and Django
- [ ] STRIPE_PUBLISHABLE_KEY is the only key used client-side
- [ ] All Supabase tables have RLS enabled -- no public access without auth
- [ ] Webhook endpoints are idempotent (check stripe_event_id before processing)
- [ ] Download URLs for digital books are signed and expire after 72 hours
- [ ] `.env` files are in `.gitignore`
- [ ] Customer Portal configured to prevent unauthorized access
- [ ] Django webhook endpoint is `csrf_exempt` but verifies Stripe signature instead
- [ ] Rate limiting on checkout session creation (prevent abuse)

---

## Appendix A: Stripe CLI Testing Commands

```bash
# Listen to webhooks locally
stripe listen --forward-to localhost:8000/api/stripe/webhook/

# Trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
stripe trigger customer.subscription.deleted
stripe trigger invoice.payment_failed

# Create a test clock for trial expiry testing
stripe test_clocks create --frozen-time="2026-03-06T00:00:00Z"
```

## Appendix B: Founding Member Implementation

To lock founding member pricing for life:

1. Create separate Stripe Price objects for founding tiers (already in catalog above)
2. During early access period, the `create-checkout-session` function checks if the user's email is in the waitlist table with `founding_member = true`
3. If founding member, use the founding price ID instead of the standard price ID
4. The subscription is created at the founding price -- Stripe will never change this price unless you explicitly do so
5. Standard pricing kicks in for all new signups after the founding window closes
6. To close the founding window: flip a feature flag or remove the founding price IDs from the checkout flow

## Appendix C: Logistics Invoice Workflow

```
Django Admin Action:
  1. Select client from StripeCustomer (product_line = 'logistics')
  2. Enter line items, amounts, due date
  3. Call stripe.invoices.create({
       customer: stripe_customer_id,
       collection_method: 'send_invoice',
       days_until_due: 30,
     })
  4. Add line items via stripe.invoiceItems.create()
  5. Call stripe.invoices.sendInvoice()
  6. Stripe sends branded invoice email to client
  7. Client pays via hosted invoice page
  8. Webhook: invoice.payment_succeeded triggers RevenueEvent logging
```
