# OnyxPOS Subscription Testing Guide

Complete guide for testing the subscription system, including multi-device access, platform fees, and tier limits.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Testing Without Stripe (Simulation Mode)](#testing-without-stripe-simulation-mode)
3. [Testing With Stripe (Production Mode)](#testing-with-stripe-production-mode)
4. [Multi-Device Testing](#multi-device-testing)
5. [Platform Fee Testing](#platform-fee-testing)
6. [Upgrade/Downgrade Testing](#upgradedowngrade-testing)
7. [Tier Limit Testing](#tier-limit-testing)
8. [Common Test Scenarios](#common-test-scenarios)

---

## Quick Start

### Prerequisites

1. OnyxPOS backend running: `http://localhost:5000`
2. Registered tenant account with owner role
3. JWT access token from login

### Get Your Access Token

```bash
# Register or login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "yourpassword"
  }'

# Response includes access_token
{
  "access_token": "eyJ0eXAiOiJKV1...",
  "user": {...}
}

# Use this token in all subsequent requests:
# -H "Authorization: Bearer eyJ0eXAiOiJKV1..."
```

---

## Testing Without Stripe (Simulation Mode)

Perfect for development and testing without actual payments.

### 1. Check Available Plans

```bash
curl http://localhost:5000/api/v1/billing/plans
```

**Response:**
```json
{
  "plans": [
    {
      "tier": "core",
      "name": "Core",
      "price": 119,
      "devices": 2,
      "team_size": 6,
      "features": ["Auto-SKU", "Task Management", "Auto Scheduling", "FIFO/COGS"],
      "platform_fees": {
        "tiers": [
          {"range": "First $10,000", "rate": "10%"},
          {"range": "$10,001 - $50,000", "rate": "5%"},
          {"range": "Over $50,000", "rate": "1%"}
        ],
        "minimum": "$1,000/month"
      }
    },
    {
      "tier": "growth",
      "name": "Growth",
      "price": 249,
      "devices": 6,
      "team_size": 15,
      "features": ["All Core features", "Shopify", "Square", "Gusto", "QuickBooks"]
    },
    {
      "tier": "prime",
      "name": "Prime",
      "price": 399,
      "devices": "Unlimited",
      "team_size": "Unlimited",
      "features": ["All Growth features", "DoorDash", "UberEats", "Grubhub", "Instacart", "OnyxAI", "Priority Support"]
    }
  ]
}
```

### 2. Simulate Subscription Purchase

```bash
# Activate Core plan ($119/mo)
curl -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_tier": "core"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Simulated core subscription activated",
  "subscription": {
    "plan_tier": "core",
    "status": "active",
    "period_end": "2025-01-28T10:00:00",
    "monthly_cost": 119
  },
  "note": "This is a test subscription. No actual payment was processed."
}
```

### 3. Add Test Sales (GMV)

```bash
# Add $5,000 in sales
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Added $5000.00 in test sales",
  "gmv": {
    "previous": 0.0,
    "added": 5000.0,
    "total": 5000.0
  },
  "fees": {
    "subscription_fee": 119,
    "platform_fee": 1000.0,
    "total_monthly_cost": 1119.0
  },
  "breakdown": {
    "first_10k": 500.0,
    "next_40k": 0.0,
    "over_50k": 0.0,
    "minimum_applied": true
  }
}
```

**Note:** Platform fee is $500 (10% of $5,000), but minimum $1,000 fee applies.

### 4. Check Subscription Status

```bash
curl http://localhost:5000/api/v1/billing/subscription-status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "plan_tier": "core",
  "subscription_status": "active",
  "trial_ends_at": null,
  "current_period_end": "2025-01-28T10:00:00",
  "usage": {
    "transactions_this_month": 0,
    "active_users": 1,
    "locations": 0
  },
  "limits": {
    "max_devices": 2,
    "max_team_size": 6,
    "features": ["Auto-SKU", "Task Management", "Auto Scheduling", "FIFO/COGS"]
  },
  "platform_fees": {
    "current_month_gmv": 5000.0,
    "platform_fee": 1000.0,
    "subscription_fee": 119,
    "total_monthly_cost": 1119.0
  }
}
```

### 5. Reset Subscription (Start Fresh)

```bash
curl -X POST http://localhost:5000/api/v1/billing/test/reset-subscription \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "message": "Subscription reset to defaults",
  "tenant": {
    "plan_tier": "core",
    "subscription_status": "trialing",
    "gmv": 0.0
  }
}
```

---

## Testing With Stripe (Production Mode)

### 1. Set Up Stripe

Add to `.env`:
```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Create these prices in Stripe Dashboard:
STRIPE_PRICE_CORE=price_xxx  # $119/month
STRIPE_PRICE_GROWTH=price_yyy  # $249/month
STRIPE_PRICE_PRIME=price_zzz  # $399/month
```

### 2. Create Checkout Session

```bash
curl -X POST http://localhost:5000/api/v1/billing/create-checkout-session \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_tier": "growth",
    "success_url": "http://localhost:3000/billing?success=true",
    "cancel_url": "http://localhost:3000/billing?canceled=true"
  }'
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "session_id": "cs_test_..."
}
```

### 3. Complete Payment

1. Open `checkout_url` in browser
2. Use Stripe test card: `4242 4242 4242 4242`
3. Any future expiry date
4. Any CVC
5. Complete checkout

### 4. Stripe Webhooks

Stripe will send webhooks to: `http://localhost:5000/api/v1/billing/webhook`

**Events handled:**
- `checkout.session.completed` - Subscription created
- `customer.subscription.created` - Subscription activated
- `customer.subscription.updated` - Plan changed
- `customer.subscription.deleted` - Subscription canceled
- `invoice.payment_succeeded` - Payment successful
- `invoice.payment_failed` - Payment failed

### 5. Customer Portal

Allow customers to manage their subscription:

```bash
curl -X POST http://localhost:5000/api/v1/billing/create-portal-session \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "return_url": "http://localhost:3000/billing"
  }'
```

**Response:**
```json
{
  "portal_url": "https://billing.stripe.com/p/session/..."
}
```

---

## Multi-Device Testing

Test device limits and multi-device login as requested.

### Scenario: Test Core Plan (2 Device Limit)

#### Device 1 (Your Computer):

```bash
# Register device 1
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "browser-laptop-chrome-001",
    "fingerprint": "user-agent-canvas-hash-123",
    "device_name": "MacBook Pro - Chrome"
  }'
```

**Response:**
```json
{
  "success": true,
  "device": {
    "id": "...",
    "device_name": "MacBook Pro - Chrome",
    "is_active": true
  },
  "limits": {
    "tier": "core",
    "device_limit": 2,
    "active_devices": 1,
    "remaining": 1
  }
}
```

#### Device 2 (Different IP - iPad):

```bash
# From different network/IP
# Login with same credentials
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "yourpassword"
  }'

# Register device 2
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer NEW_TOKEN_FROM_DEVICE_2" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "browser-ipad-safari-001",
    "fingerprint": "user-agent-canvas-hash-456",
    "device_name": "iPad Pro - Safari"
  }'
```

**Response:**
```json
{
  "success": true,
  "device": {
    "id": "...",
    "device_name": "iPad Pro - Safari",
    "is_active": true
  },
  "limits": {
    "tier": "core",
    "device_limit": 2,
    "active_devices": 2,
    "remaining": 0
  }
}
```

#### Device 3 (Should Fail - iPhone):

```bash
# From another device/IP
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN_FROM_DEVICE_3" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "browser-iphone-safari-001",
    "device_name": "iPhone 13 - Safari"
  }'
```

**Response (403 Forbidden):**
```json
{
  "error": "Device limit reached",
  "message": "Your core plan allows 2 devices. Please upgrade to Growth plan for 6 devices.",
  "current_tier": "core",
  "device_limit": 2,
  "active_devices": 2,
  "upgrade_url": "/api/v1/billing/upgrade"
}
```

#### List Active Devices:

```bash
curl http://localhost:5000/api/v1/devices \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "devices": [
    {
      "id": "...",
      "device_name": "MacBook Pro - Chrome",
      "device_id": "browser-laptop-chrome-001",
      "last_active": "2025-12-29T10:30:00Z",
      "is_active": true
    },
    {
      "id": "...",
      "device_name": "iPad Pro - Safari",
      "device_id": "browser-ipad-safari-001",
      "last_active": "2025-12-29T09:15:00Z",
      "is_active": true
    }
  ],
  "limits": {
    "tier": "core",
    "device_limit": 2,
    "active_devices": 2,
    "remaining": 0
  }
}
```

#### Deactivate Device (Free Up Slot):

```bash
curl -X POST http://localhost:5000/api/v1/devices/DEVICE_ID/deactivate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Now device 3 can register.

---

## Platform Fee Testing

Test the tiered platform fee calculation.

### Test Case 1: $5,000 GMV (Below Minimum)

```bash
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000}'
```

**Expected:**
- Calculation: $5,000 × 10% = $500
- **Minimum $1,000 applies**
- Total: $119 (Core) + $1,000 = **$1,119/mo**

### Test Case 2: $15,000 GMV (Two Tiers)

```bash
# Reset first
curl -X POST http://localhost:5000/api/v1/billing/test/reset-subscription \
  -H "Authorization: Bearer YOUR_TOKEN"

# Add $15k sales
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 15000}'
```

**Expected:**
- First $10k × 10% = $1,000
- Next $5k × 5% = $250
- Total fee: $1,250
- Total: $119 (Core) + $1,250 = **$1,369/mo**

### Test Case 3: $100,000 GMV (All Three Tiers)

```bash
curl -X POST http://localhost:5000/api/v1/billing/test/reset-subscription \
  -H "Authorization: Bearer YOUR_TOKEN"

curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 100000}'
```

**Expected:**
- First $10k × 10% = $1,000
- Next $40k × 5% = $2,000
- Last $50k × 1% = $500
- Total fee: $3,500
- Total: $399 (Prime) + $3,500 = **$3,899/mo**

### Test Case 4: Incremental Sales

```bash
# Start fresh
curl -X POST http://localhost:5000/api/v1/billing/test/reset-subscription \
  -H "Authorization: Bearer YOUR_TOKEN"

# Add sales incrementally
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"amount": 5000}'

# Check fee: $1,000 (minimum)

curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"amount": 5000}'

# Check fee: $1,000 (10% of $10k)

curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"amount": 5000}'

# Check fee: $1,250 (10% of $10k + 5% of $5k)
```

---

## Upgrade/Downgrade Testing

### Test Upgrade Flow

#### 1. Start with Core Plan

```bash
curl -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"plan_tier": "core"}'
```

#### 2. Upgrade to Growth

```bash
curl -X POST http://localhost:5000/api/v1/billing/upgrade \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_tier": "growth"
  }'
```

**Response:**
```json
{
  "message": "Successfully upgraded to growth plan",
  "new_plan": {
    "name": "Growth",
    "price": 249,
    "devices": 6,
    "team_size": 15,
    "features": ["All Core features", "Shopify", "Square", "Gusto", "QuickBooks"]
  },
  "prorated_charge": "Prorated amount will appear on your next invoice"
}
```

#### 3. Verify New Limits

```bash
# Now you can register 6 devices instead of 2
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"device_id": "device-3", "device_name": "Device 3"}'
```

Should succeed now.

### Test Downgrade Flow

#### 1. Try to Downgrade with Too Many Devices

```bash
# Currently on Growth (6 devices), have 3 devices registered
curl -X POST http://localhost:5000/api/v1/billing/downgrade \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_tier": "core"
  }'
```

**Response (400 Bad Request):**
```json
{
  "error": "Cannot downgrade due to limit violations",
  "violations": [
    "You have 3 active devices but core plan allows 2"
  ],
  "action_required": "Please remove excess devices/team members before downgrading"
}
```

#### 2. Deactivate Excess Devices

```bash
curl -X POST http://localhost:5000/api/v1/devices/DEVICE_3_ID/deactivate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### 3. Downgrade Again

```bash
curl -X POST http://localhost:5000/api/v1/billing/downgrade \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"new_tier": "core"}'
```

**Response:**
```json
{
  "message": "Downgrade to core plan scheduled",
  "new_plan": {
    "name": "Core",
    "price": 119,
    "devices": 2,
    "team_size": 6
  },
  "effective_date": "2025-01-28T10:00:00",
  "note": "Downgrade will take effect at the end of your current billing period"
}
```

---

## Tier Limit Testing

### Test Team Size Limits

#### Core Plan (6 team members max):

```bash
# Create employee 1
curl -X POST http://localhost:5000/api/v1/employees \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "employee1@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "cashier"
  }'

# Repeat for employees 2-6...

# Try to create employee 7 (should fail)
curl -X POST http://localhost:5000/api/v1/employees \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "email": "employee7@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "role": "cashier"
  }'
```

**Response (403 Forbidden):**
```json
{
  "error": "Team size limit reached",
  "message": "Your core plan allows 6 team members. Please upgrade to Growth plan for 15 team members.",
  "current_tier": "core",
  "team_limit": 6,
  "active_team_members": 6
}
```

### Test Prime Plan (Unlimited)

```bash
# Upgrade to Prime
curl -X POST http://localhost:5000/api/v1/billing/upgrade \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"new_tier": "prime"}'

# Now can register unlimited devices and team members
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"device_id": "device-100", "device_name": "Device 100"}'
```

Should succeed (no limit).

---

## Common Test Scenarios

### Scenario 1: New Business Onboarding

```bash
# 1. Register
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newbiz@example.com",
    "password": "SecurePass123!",
    "business_name": "New Coffee Shop",
    "plan_tier": "core"
  }'

# 2. Simulate subscription (testing mode)
curl -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer TOKEN" \
  -d '{"plan_tier": "core"}'

# 3. Register POS device
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "device_id": "pos-ipad-001",
    "device_name": "Front Counter iPad"
  }'

# 4. Add inventory with auto-SKU
curl -X POST http://localhost:5000/api/v1/inventory \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "name": "Espresso",
    "category": "Coffee",
    "price": 3.50
  }'

# 5. Make first sale
curl -X POST http://localhost:5000/api/v1/sales \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "items": [{"sku": "COFFEE-A3B2-001", "quantity": 1, "price": 3.50}],
    "total": 3.50,
    "payment_method": "cash"
  }'

# 6. Check subscription status
curl http://localhost:5000/api/v1/billing/subscription-status \
  -H "Authorization: Bearer TOKEN"
```

### Scenario 2: Growing Business (Upgrade Path)

```bash
# Month 1: Core plan, $8k sales
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer TOKEN" \
  -d '{"amount": 8000}'

# Cost: $119 + $1,000 (min) = $1,119

# Month 3: Growing, need more devices
# Try to add 3rd device - FAILS
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{"device_id": "device-3", "device_name": "Device 3"}'

# Upgrade to Growth
curl -X POST http://localhost:5000/api/v1/billing/upgrade \
  -H "Authorization: Bearer TOKEN" \
  -d '{"new_tier": "growth"}'

# Month 6: $30k sales
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer TOKEN" \
  -d '{"amount": 30000}'

# Cost: $249 + $2,000 (10% of $10k + 5% of $20k) = $2,249

# Month 12: $75k sales, need delivery integrations
curl -X POST http://localhost:5000/api/v1/billing/upgrade \
  -H "Authorization: Bearer TOKEN" \
  -d '{"new_tier": "prime"}'

# Cost: $399 + $3,250 = $3,649
```

### Scenario 3: Multi-Location Setup

```bash
# Business owner wants 3 locations, each with 2 devices = 6 devices total
# Needs Growth plan minimum

# Location 1
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{"device_id": "loc1-pos1", "device_name": "Downtown - Register 1"}'

curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{"device_id": "loc1-pos2", "device_name": "Downtown - Register 2"}'

# Location 2
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{"device_id": "loc2-pos1", "device_name": "Uptown - Register 1"}'

curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{"device_id": "loc2-pos2", "device_name": "Uptown - Register 2"}'

# Location 3
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{"device_id": "loc3-pos1", "device_name": "Airport - Register 1"}'

curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer TOKEN" \
  -d '{"device_id": "loc3-pos2", "device_name": "Airport - Register 2"}'

# All 6 devices registered successfully on Growth plan
```

---

## Testing Checklist

- [ ] **Subscription Creation**
  - [ ] Core plan activation
  - [ ] Growth plan activation
  - [ ] Prime plan activation
  - [ ] Stripe checkout flow (if using Stripe)

- [ ] **Platform Fees**
  - [ ] $5k sales → $1,000 minimum fee
  - [ ] $15k sales → $1,250 calculated fee
  - [ ] $30k sales → $2,000 calculated fee
  - [ ] $100k sales → $3,500 calculated fee

- [ ] **Device Limits**
  - [ ] Core: 2 devices enforced
  - [ ] Growth: 6 devices enforced
  - [ ] Prime: Unlimited devices
  - [ ] Device registration from different IPs
  - [ ] Device deactivation

- [ ] **Team Limits**
  - [ ] Core: 6 team members enforced
  - [ ] Growth: 15 team members enforced
  - [ ] Prime: Unlimited team members

- [ ] **Upgrade/Downgrade**
  - [ ] Successful upgrade with prorating
  - [ ] Downgrade blocked by violations
  - [ ] Downgrade after removing excess resources
  - [ ] Downgrade scheduled for period end

- [ ] **Multi-Device**
  - [ ] Login from device 1
  - [ ] Login from device 2 (different IP)
  - [ ] Device 3 blocked on Core plan
  - [ ] Device 3 allowed after upgrade

---

## Environment Setup

### Development (.env)

```bash
# Database
DATABASE_URL=sqlite:///onyxpos_dev.db

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production

# Stripe (Test Mode)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...

# Plan Price IDs (create in Stripe Dashboard)
STRIPE_PRICE_CORE=price_test_core119
STRIPE_PRICE_GROWTH=price_test_growth249
STRIPE_PRICE_PRIME=price_test_prime399
```

### Production (.env.production)

```bash
# Database
DATABASE_URL=postgresql://user:pass@prod-db/onyxpos

# JWT
JWT_SECRET_KEY=super-secure-random-key-here

# Stripe (Live Mode)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# Plan Price IDs (live products)
STRIPE_PRICE_CORE=price_live_core119
STRIPE_PRICE_GROWTH=price_live_growth249
STRIPE_PRICE_PRIME=price_live_prime399
```

---

## Troubleshooting

### "Device limit reached" but I deactivated devices

**Solution:** Check active devices:
```bash
curl http://localhost:5000/api/v1/devices \
  -H "Authorization: Bearer TOKEN"
```

Ensure `is_active: false` for deactivated devices.

### Platform fee not calculating correctly

**Solution:** Check current GMV:
```bash
curl http://localhost:5000/api/v1/billing/subscription-status \
  -H "Authorization: Bearer TOKEN"
```

Look at `platform_fees.current_month_gmv`. Reset if needed:
```bash
curl -X POST http://localhost:5000/api/v1/billing/test/reset-subscription \
  -H "Authorization: Bearer TOKEN"
```

### Stripe webhook not working

**Solution:**
1. Use Stripe CLI for local testing:
   ```bash
   stripe listen --forward-to localhost:5000/api/v1/billing/webhook
   ```

2. Copy webhook signing secret to `.env`:
   ```bash
   STRIPE_WEBHOOK_SECRET=whsec_xxx
   ```

3. Trigger test event:
   ```bash
   stripe trigger checkout.session.completed
   ```

### Can't upgrade/downgrade

**Solution:** Check subscription status:
```bash
curl http://localhost:5000/api/v1/billing/subscription-status \
  -H "Authorization: Bearer TOKEN"
```

Ensure `subscription_status: "active"` and you have `stripe_subscription_id`.

---

## Summary

You now have a complete testing suite for:

1. **Subscription Management** - Create, upgrade, downgrade subscriptions
2. **Platform Fees** - Tiered fee calculation (10%/5%/1%)
3. **Device Limits** - Multi-device testing across different IPs
4. **Team Limits** - Team size enforcement
5. **Autonomous Features** - Auto-SKU, auto-scheduling, task management

Use simulation mode (`/test/` endpoints) for rapid development testing, then switch to real Stripe for production validation.

All endpoints are documented in: `AUTONOMOUS_FEATURES_GUIDE.md`
