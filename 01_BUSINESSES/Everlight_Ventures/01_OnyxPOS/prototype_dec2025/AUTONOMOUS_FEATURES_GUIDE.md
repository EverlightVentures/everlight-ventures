# OnyxPOS Autonomous Features & Channel Integrations Guide

## Overview

This guide covers all autonomous features and channel integrations built into OnyxPOS, including automated scheduling, auto-SKU generation, task management, device limits, and delivery platform integrations.

---

## Table of Contents

1. [Pricing Model & Platform Fees](#pricing-model--platform-fees)
2. [Autonomous Features](#autonomous-features)
3. [Device & Team Limits](#device--team-limits)
4. [Google OAuth Integration](#google-oauth-integration)
5. [Channel Integrations](#channel-integrations)
6. [Environment Variables](#environment-variables)
7. [API Reference](#api-reference)
8. [Testing Guide](#testing-guide)

---

## Pricing Model & Platform Fees

### Subscription Tiers

| Tier | Monthly Fee | Devices | Team Size | Key Features |
|------|------------|---------|-----------|--------------|
| **Core** | $119/mo | 2 | 6 | Basic POS, auto-SKU, task management, auto-scheduling, FIFO/COGS |
| **Growth** | $249/mo | 6 | 15 | Core + Shopify, Square, Gusto, QuickBooks integrations |
| **Prime** | $399/mo | Unlimited | Unlimited | Growth + DoorDash, UberEats, Grubhub, Instacart, OnyxAI, Priority Support |

### Platform Fee Structure

Commission-based pricing that scales with your business:

- **10%** on first $10,000/month in sales
- **5%** on sales from $10,001 to $50,000/month
- **1%** on all sales over $50,000/month
- **Minimum:** $1,000/month platform fee

#### Example Calculations:

**$5,000/mo in sales (Core):**
- Calculation: $5,000 × 10% = $500
- Minimum fee applies: $1,000
- Total: $119 + $1,000 = **$1,119/mo**

**$25,000/mo in sales (Growth):**
- First $10k × 10% = $1,000
- Next $15k × 5% = $750
- Total: $249 + $1,750 = **$1,999/mo**

**$100,000/mo in sales (Prime):**
- First $10k × 10% = $1,000
- Next $40k × 5% = $2,000
- Last $50k × 1% = $500
- Total: $399 + $3,500 = **$3,899/mo**

### Implementation

Platform fees are calculated automatically in the billing system:

```python
# backend/models.py - Tenant.calculate_usage_fee()
def calculate_usage_fee(self, gmv_amount=None):
    gmv = gmv_amount if gmv_amount is not None else float(self.gmv_current_month or 0)

    platform_fee = 0.0
    if gmv > 0:
        tier1 = min(gmv, 10000)
        platform_fee += tier1 * 0.10
    if gmv > 10000:
        tier2 = min(gmv - 10000, 40000)
        platform_fee += tier2 * 0.05
    if gmv > 50000:
        tier3 = gmv - 50000
        platform_fee += tier3 * 0.01

    # Enforce minimum fee
    platform_fee = max(platform_fee, 1000.00)
    return round(platform_fee, 2)
```

---

## Autonomous Features

### 1. Auto-SKU Generation

Automatically generates unique SKUs for inventory items, eliminating manual entry.

**Format:** `{CATEGORY}-{HASH}-{COUNTER}`
**Example:** `COFFEE-A3B2-001`

#### How It Works:

1. Extracts category prefix (e.g., "COFFEE" → "COFFEE")
2. Generates MD5 hash of item name (first 4 chars)
3. Adds incrementing counter for uniqueness
4. Validates against existing SKUs

#### API Usage:

```bash
# Create item without SKU - will auto-generate
POST /api/v1/inventory
{
  "name": "Espresso Blend",
  "category": "Coffee",
  "price": 12.99
  # No SKU provided
}

# Response includes auto-generated SKU
{
  "item": {
    "id": "...",
    "sku": "COFFEE-A3B2-001",
    "sku_auto_generated": true,
    "name": "Espresso Blend"
  }
}

# Can still manually provide SKU
POST /api/v1/inventory
{
  "sku": "CUSTOM-SKU-001",
  "name": "Custom Item"
}
```

#### Code Location:
- `backend/services/sku_generator.py` - SKU generation logic
- `backend/api/inventory.py:67-75` - Integration into inventory API

---

### 2. Automated Shift Scheduling

Learns from manual shift entries and generates recurring schedules automatically.

#### Pattern Recognition:

- Analyzes last 4 weeks of shift history
- Identifies common work days and times
- Calculates confidence scores (50%+ threshold)
- Generates suggestions for recurring schedules

#### Confidence Scoring:

```
Confidence = (Number of occurrences) / (Total weeks analyzed)

Example:
- Employee works Mondays 9am-5pm for 3 out of 4 weeks
- Confidence: 3/4 = 75% ✓ (meets 50% threshold)
```

#### API Usage:

```bash
# Get automated schedule suggestions
GET /api/v1/schedule/auto-suggestions/{employee_id}?weeks=2

Response:
{
  "employee_id": "...",
  "suggestions": [
    {
      "day_of_week": 1,  # Monday
      "start_time": "09:00",
      "end_time": "17:00",
      "confidence": 0.75,
      "occurrences": 3,
      "weeks_analyzed": 4
    }
  ]
}

# Auto-create schedules from patterns
POST /api/v1/schedule/auto-create/{employee_id}
{
  "weeks": 2,
  "auto_confirm": false  # Set true to skip manual review
}

Response:
{
  "created": 8,
  "schedules": [...]
}

# Analyze coverage gaps
GET /api/v1/schedule/analyze-coverage?date=2025-12-29

Response:
{
  "date": "2025-12-29",
  "required_coverage": {
    "09:00-17:00": 2  # Need 2 employees
  },
  "actual_coverage": {
    "09:00-17:00": 1  # Only have 1
  },
  "gaps": [
    {
      "time_range": "09:00-17:00",
      "required": 2,
      "actual": 1,
      "shortage": 1
    }
  ]
}
```

#### Code Location:
- `backend/services/automated_scheduling.py` - Pattern recognition algorithm
- `backend/api/schedule.py:77-127` - Automated scheduling endpoints

---

### 3. Task Management System

Full Asana-style task management with projects, subtasks, assignments, and comments.

#### Features:

- Create tasks with priority, due dates, assignments
- Organize into projects
- Create subtasks (hierarchical structure)
- Add comments and discussions
- Filter by status, priority, assignee
- Search across tasks

#### Task Statuses:
- `to_do` - Not started
- `in_progress` - Currently working on
- `completed` - Finished
- `blocked` - Waiting on dependencies

#### Priority Levels:
- `low` - Nice to have
- `medium` - Normal priority
- `high` - Important
- `urgent` - Critical

#### API Usage:

```bash
# Create project
POST /api/v1/tasks/projects
{
  "name": "Q1 2025 Inventory Audit",
  "description": "Complete inventory count and reconciliation"
}

# Create task
POST /api/v1/tasks
{
  "title": "Count beverage inventory",
  "description": "Physical count of all beverages in stock",
  "status": "to_do",
  "priority": "high",
  "project_id": "...",
  "assigned_to": "employee_user_id",
  "due_date": "2025-01-15T17:00:00Z"
}

# Create subtask
POST /api/v1/tasks
{
  "title": "Count coffee beans",
  "parent_task_id": "parent_task_id",
  "assigned_to": "..."
}

# List tasks with filters
GET /api/v1/tasks?status=in_progress&priority=high&assigned_to=user_id

# Add comment
POST /api/v1/tasks/{task_id}/comments
{
  "comment": "Counted 45 bags of coffee beans"
}

# Update task status
PUT /api/v1/tasks/{task_id}
{
  "status": "completed"
}
```

#### Code Location:
- `backend/models.py:850-920` - Task, Project, TaskComment models
- `backend/api/tasks.py` - Complete task management API

---

## Device & Team Limits

Tier-based limits enforce subscription boundaries and drive upgrades.

### Limits by Tier:

| Tier | Devices | Team Members |
|------|---------|--------------|
| Core | 2 | 6 |
| Growth | 6 | 15 |
| Prime | Unlimited | Unlimited |

### Device Registration:

```bash
POST /api/v1/devices/register
{
  "device_id": "browser-unique-id",
  "fingerprint": "user-agent-canvas-hash",
  "device_name": "iPad POS Terminal 1"
}

# If limit reached:
{
  "error": "Device limit reached",
  "message": "Your core plan allows 2 devices. Please upgrade to Growth plan for 6 devices.",
  "current_tier": "core",
  "device_limit": 2,
  "active_devices": 2,
  "upgrade_url": "/api/v1/billing/upgrade"
}
```

### Team Member Creation:

```bash
POST /api/v1/employees
{
  "email": "employee@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "cashier"
}

# If limit reached:
{
  "error": "Team size limit reached",
  "message": "Your core plan allows 6 team members. Please upgrade to Growth plan for 15 team members.",
  "current_tier": "core",
  "team_limit": 6,
  "active_team_members": 6
}
```

### List Active Devices:

```bash
GET /api/v1/devices

Response:
{
  "devices": [
    {
      "id": "...",
      "device_name": "iPad POS Terminal 1",
      "last_active": "2025-12-29T10:30:00Z",
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

### Deactivate Device:

```bash
POST /api/v1/devices/{device_id}/deactivate
```

#### Code Location:
- `backend/models.py:180-195` - Device limit methods
- `backend/api/devices.py` - Device management API
- `backend/api/employees.py:32-47` - Team limit enforcement

---

## Google OAuth Integration

Sign in with Google for faster onboarding.

### OAuth Flow:

1. **Initiate OAuth:**
```bash
GET /api/v1/auth/google?mode=login
# mode can be: login, signup

Response:
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&state=..."
}
```

2. **Redirect user to auth_url**

3. **Google redirects back to callback:**
```
GET /api/v1/auth/google/callback?code=...&state=...
```

4. **Backend exchanges code for tokens and creates/logs in user:**
```json
{
  "access_token": "jwt-token",
  "user": {
    "id": "...",
    "email": "user@gmail.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

### Environment Variables:

```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/v1/auth/google/callback
```

#### Code Location:
- `backend/api/auth.py:178-280` - Google OAuth implementation

---

## Channel Integrations

Integrate with delivery platforms to receive orders directly in OnyxPOS.

### Supported Channels:

1. **DoorDash** - Restaurant delivery
2. **UberEats** - Restaurant delivery
3. **Grubhub** - Restaurant delivery
4. **Instacart** - Retail delivery

### Integration Flow:

#### 1. Connect Channel (OAuth):

```bash
GET /api/v1/channels/{channel}/connect
# channel: doordash, ubereats, grubhub, instacart

Response:
{
  "auth_url": "https://identity.doordash.com/connect/authorize?client_id=...&state=..."
}
```

#### 2. OAuth Callback:

User completes OAuth on channel's site, redirected back:

```
GET /api/v1/channels/{channel}/callback?code=...&state=...

Response:
{
  "success": true,
  "integration": {
    "id": "...",
    "channel": "doordash",
    "status": "connected",
    "merchant_id": "store-12345"
  }
}
```

#### 3. List Integrations:

```bash
GET /api/v1/channels

Response:
{
  "integrations": [
    {
      "id": "...",
      "channel": "doordash",
      "status": "connected",
      "merchant_id": "store-12345",
      "connected_at": "2025-12-29T10:00:00Z",
      "menu_last_synced": "2025-12-29T12:00:00Z"
    }
  ]
}
```

#### 4. Sync Menu to Channel:

```bash
POST /api/v1/channels/{integration_id}/sync-menu

Response:
{
  "success": true,
  "synced_items": 45,
  "failed_items": 0,
  "sync_time": "2025-12-29T12:30:00Z"
}
```

#### 5. Receive Orders (Webhook):

Channels send webhooks when new orders are placed:

```bash
POST /api/v1/channels/webhook/{channel}
{
  "event": "order.created",
  "order_id": "DD-ORDER-12345",
  "customer_name": "John Doe",
  "items": [...],
  "total": 45.99,
  "delivery_fee": 3.99,
  "platform_commission": 6.90  # 15% commission
}

# OnyxPOS creates ChannelOrder and Sale records automatically
```

#### 6. List Channel Orders:

```bash
GET /api/v1/channels/orders?channel=doordash&status=pending

Response:
{
  "orders": [
    {
      "id": "...",
      "channel": "doordash",
      "channel_order_id": "DD-ORDER-12345",
      "customer_name": "John Doe",
      "total": 45.99,
      "platform_commission": 6.90,
      "net_payout": 39.09,
      "status": "pending",
      "created_at": "2025-12-29T13:00:00Z"
    }
  ]
}
```

#### 7. Update Order Status:

```bash
PATCH /api/v1/channels/orders/{order_id}/update-status
{
  "status": "confirmed"  # confirmed, preparing, ready, picked_up, delivered
}

# Sends status update back to delivery platform
```

#### 8. Get Analytics:

```bash
GET /api/v1/channels/analytics?start_date=2025-12-01&end_date=2025-12-31

Response:
{
  "summary": {
    "total_orders": 145,
    "total_revenue": 6547.85,
    "total_commission": 981.18,
    "total_net_payout": 5566.67,
    "avg_commission_percent": 14.99
  },
  "by_channel": {
    "doordash": {
      "orders": 67,
      "revenue": 3021.45,
      "commission": 453.22,
      "net_payout": 2568.23,
      "avg_commission_percent": 15.0
    },
    "ubereats": {
      "orders": 52,
      "revenue": 2341.20,
      "commission": 351.18,
      "net_payout": 1990.02,
      "avg_commission_percent": 15.0
    },
    "grubhub": {
      "orders": 26,
      "revenue": 1185.20,
      "commission": 176.78,
      "net_payout": 1008.42,
      "avg_commission_percent": 14.92
    }
  }
}
```

### Channel Configuration:

Each channel has specific OAuth and API settings:

```python
# backend/api/channels.py
CHANNEL_CONFIGS = {
    "doordash": {
        "name": "DoorDash",
        "oauth_url": "https://identity.doordash.com/connect/authorize",
        "token_url": "https://identity.doordash.com/connect/token",
        "api_base": "https://openapi.doordash.com",
        "required_scopes": ["merchant.read", "merchant.write", "orders.read"],
        "commission_rate": 0.15  # 15%
    },
    "ubereats": {
        "name": "Uber Eats",
        "oauth_url": "https://login.uber.com/oauth/v2/authorize",
        "token_url": "https://login.uber.com/oauth/v2/token",
        "api_base": "https://api.uber.com/v1/eats",
        "required_scopes": ["eats.store", "eats.orders"],
        "commission_rate": 0.15
    },
    "grubhub": {
        "name": "Grubhub",
        "oauth_url": "https://api.grubhub.com/oauth/authorize",
        "token_url": "https://api.grubhub.com/oauth/token",
        "api_base": "https://api.grubhub.com/v1",
        "required_scopes": ["restaurant", "orders"],
        "commission_rate": 0.15
    },
    "instacart": {
        "name": "Instacart",
        "oauth_url": "https://connect.instacart.com/oauth/authorize",
        "token_url": "https://connect.instacart.com/oauth/token",
        "api_base": "https://connect.instacart.com/v1",
        "required_scopes": ["catalog", "orders"],
        "commission_rate": 0.12  # 12% for retail
    }
}
```

### Webhook Security:

Channels send webhooks with HMAC signatures for verification:

```python
# Verify webhook signature
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)
```

#### Code Location:
- `backend/models.py:950-1020` - ChannelIntegration, ChannelOrder models
- `backend/api/channels.py` - Complete channel integration API

---

## Environment Variables

### Required for Production:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/onyxpos

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production

# Stripe (for subscription billing)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/v1/auth/google/callback

# DoorDash
DOORDASH_CLIENT_ID=your-doordash-client-id
DOORDASH_CLIENT_SECRET=your-doordash-client-secret
DOORDASH_REDIRECT_URI=https://yourdomain.com/api/v1/channels/doordash/callback
DOORDASH_WEBHOOK_SECRET=your-doordash-webhook-secret

# UberEats
UBEREATS_CLIENT_ID=your-ubereats-client-id
UBEREATS_CLIENT_SECRET=your-ubereats-client-secret
UBEREATS_REDIRECT_URI=https://yourdomain.com/api/v1/channels/ubereats/callback
UBEREATS_WEBHOOK_SECRET=your-ubereats-webhook-secret

# Grubhub
GRUBHUB_CLIENT_ID=your-grubhub-client-id
GRUBHUB_CLIENT_SECRET=your-grubhub-client-secret
GRUBHUB_REDIRECT_URI=https://yourdomain.com/api/v1/channels/grubhub/callback
GRUBHUB_WEBHOOK_SECRET=your-grubhub-webhook-secret

# Instacart
INSTACART_CLIENT_ID=your-instacart-client-id
INSTACART_CLIENT_SECRET=your-instacart-client-secret
INSTACART_REDIRECT_URI=https://yourdomain.com/api/v1/channels/instacart/callback
INSTACART_WEBHOOK_SECRET=your-instacart-webhook-secret

# Optional
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## API Reference

### Quick Reference:

#### Authentication
- `POST /api/v1/auth/register` - Register new tenant
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/google` - Initiate Google OAuth
- `GET /api/v1/auth/google/callback` - Google OAuth callback

#### Inventory
- `GET /api/v1/inventory` - List items
- `POST /api/v1/inventory` - Create item (auto-SKU)
- `GET /api/v1/inventory/{item_id}` - Get item details
- `PUT /api/v1/inventory/{item_id}` - Update item
- `DELETE /api/v1/inventory/{item_id}` - Delete item

#### Tasks
- `GET /api/v1/tasks` - List tasks (with filters)
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/tasks/{task_id}` - Get task details
- `PUT /api/v1/tasks/{task_id}` - Update task
- `POST /api/v1/tasks/{task_id}/comments` - Add comment
- `GET /api/v1/tasks/projects` - List projects
- `POST /api/v1/tasks/projects` - Create project

#### Scheduling
- `GET /api/v1/schedule` - List schedules
- `POST /api/v1/schedule` - Create schedule
- `GET /api/v1/schedule/auto-suggestions/{employee_id}` - Get AI suggestions
- `POST /api/v1/schedule/auto-create/{employee_id}` - Auto-create schedules
- `GET /api/v1/schedule/analyze-coverage` - Analyze coverage gaps

#### Devices
- `GET /api/v1/devices` - List devices
- `POST /api/v1/devices/register` - Register device
- `POST /api/v1/devices/{device_id}/deactivate` - Deactivate device

#### Employees
- `GET /api/v1/employees` - List employees
- `POST /api/v1/employees` - Create employee (with team limit check)
- `GET /api/v1/employees/{employee_id}` - Get employee details

#### Channels
- `GET /api/v1/channels` - List integrations
- `GET /api/v1/channels/{channel}/connect` - Connect channel (OAuth)
- `GET /api/v1/channels/{channel}/callback` - OAuth callback
- `POST /api/v1/channels/{integration_id}/sync-menu` - Sync menu
- `GET /api/v1/channels/orders` - List channel orders
- `PATCH /api/v1/channels/orders/{order_id}/update-status` - Update order
- `GET /api/v1/channels/analytics` - Get analytics
- `POST /api/v1/channels/webhook/{channel}` - Receive webhooks

#### Billing
- `GET /api/v1/billing/subscription` - Get subscription details
- `POST /api/v1/billing/upgrade` - Upgrade plan
- `GET /api/v1/billing/usage` - Get usage and fees

---

## Testing Guide

### 1. Test Subscription Flow

```bash
# 1. Register new tenant
POST /api/v1/auth/register
{
  "email": "test@example.com",
  "password": "TestPass123!",
  "business_name": "Test Coffee Shop",
  "plan_tier": "core"
}

# 2. Login and get token
POST /api/v1/auth/login
{
  "email": "test@example.com",
  "password": "TestPass123!"
}

# 3. Check subscription
GET /api/v1/billing/subscription
Authorization: Bearer {token}

# 4. Add some sales to test platform fees
POST /api/v1/sales
{
  "items": [...],
  "total": 50.00
}

# 5. Check usage and fees
GET /api/v1/billing/usage
# Should show GMV and calculated platform fee
```

### 2. Test Device Limits

```bash
# 1. Register device 1
POST /api/v1/devices/register
{
  "device_id": "device-1",
  "device_name": "iPad 1"
}

# 2. Register device 2
POST /api/v1/devices/register
{
  "device_id": "device-2",
  "device_name": "iPad 2"
}

# 3. Try to register device 3 (should fail on Core plan)
POST /api/v1/devices/register
{
  "device_id": "device-3",
  "device_name": "iPad 3"
}
# Expected: 403 error with upgrade message

# 4. Upgrade to Growth plan
POST /api/v1/billing/upgrade
{
  "new_tier": "growth"
}

# 5. Now device 3 should work
POST /api/v1/devices/register
{
  "device_id": "device-3",
  "device_name": "iPad 3"
}
```

### 3. Test Auto-SKU Generation

```bash
# 1. Create item without SKU
POST /api/v1/inventory
{
  "name": "Espresso Blend",
  "category": "Coffee",
  "price": 12.99
}

# Response should include auto-generated SKU like "COFFEE-A3B2-001"

# 2. Create another coffee item
POST /api/v1/inventory
{
  "name": "House Blend",
  "category": "Coffee",
  "price": 10.99
}

# Should get unique SKU like "COFFEE-B4C3-001"

# 3. Verify no duplicate SKUs
GET /api/v1/inventory
# Check that all SKUs are unique
```

### 4. Test Automated Scheduling

```bash
# 1. Create manual schedules for pattern recognition
# (Create at least 3 shifts on Mondays 9am-5pm)
POST /api/v1/schedule
{
  "employee_id": "...",
  "date": "2025-12-09",  # Monday
  "start_time": "09:00",
  "end_time": "17:00"
}

# Repeat for Dec 16, Dec 23

# 2. Get auto-suggestions
GET /api/v1/schedule/auto-suggestions/{employee_id}

# Should show Monday 9am-5pm with 75% confidence

# 3. Auto-create next 2 weeks
POST /api/v1/schedule/auto-create/{employee_id}
{
  "weeks": 2,
  "auto_confirm": false
}

# Should create 2 Monday shifts
```

### 5. Test Channel Integration (Sandbox)

```bash
# 1. Connect to DoorDash (sandbox)
GET /api/v1/channels/doordash/connect

# Follow OAuth flow in browser

# 2. Sync menu
POST /api/v1/channels/{integration_id}/sync-menu

# 3. Simulate webhook (test order)
POST /api/v1/channels/webhook/doordash
{
  "event": "order.created",
  "order_id": "TEST-ORDER-001",
  "customer_name": "Test Customer",
  "items": [
    {
      "name": "Espresso",
      "quantity": 2,
      "price": 3.50
    }
  ],
  "total": 7.00,
  "delivery_fee": 2.00,
  "platform_commission": 1.05
}

# 4. Check channel orders
GET /api/v1/channels/orders

# 5. Update order status
PATCH /api/v1/channels/orders/{order_id}/update-status
{
  "status": "confirmed"
}

# 6. Get analytics
GET /api/v1/channels/analytics?start_date=2025-12-01&end_date=2025-12-31
```

### 6. Test Multi-Device Login (Different IPs)

```bash
# Test from different devices/IPs:

# Device 1 (192.168.1.100):
POST /api/v1/auth/login
# Register device 1

# Device 2 (192.168.1.101):
POST /api/v1/auth/login
# Register device 2

# Device 3 (192.168.1.102):
POST /api/v1/auth/login
# Should fail on Core plan

# Verify sessions
GET /api/v1/devices
# Should show 2 active devices on Core plan
```

---

## Summary

### What's Built:

✅ **Autonomous Features:**
- Auto-SKU generation (hash-based, unique)
- Automated shift scheduling (pattern recognition)
- Task management (Asana-style)

✅ **Pricing & Limits:**
- Tiered subscription (Core/Growth/Prime)
- Commission-based platform fees (10%/5%/1%)
- Device limits (2/6/unlimited)
- Team size limits (6/15/unlimited)

✅ **Integrations:**
- Google OAuth (sign in with Google)
- DoorDash integration (OAuth, menu sync, orders)
- UberEats integration (OAuth, menu sync, orders)
- Grubhub integration (OAuth, menu sync, orders)
- Instacart integration (OAuth, menu sync, orders)

✅ **Analytics:**
- Channel-level revenue tracking
- Commission reconciliation
- Net payout calculations

### What's Next:

🔲 Stripe subscription checkout flow
🔲 Shopify bidirectional sync
🔲 Square payment processing
🔲 QuickBooks accounting sync
🔲 OnyxAI assistant
🔲 Hardware setup (printer, scanner)
🔲 End-to-end testing

---

## Support

For questions or issues:
- GitHub: [Repository URL]
- Email: support@onyxpos.com
- Docs: [Documentation URL]
