# Quick Start Testing Guide

Follow these steps to test OnyxPOS end-to-end.

---

## Step 1: Start the Backend

```bash
cd /home/mgn/Projects/OnyxPOS/backend

# Activate virtual environment
source venv/bin/activate

# Start the server
python3 app.py
```

You should see:
```
============================================================
  OnyxPOS API Server
  Next-Generation Point of Sale
  http://localhost:5000
============================================================
```

Keep this terminal open.

---

## Step 2: Test the System (Open New Terminal)

### A. Register a New Business

```bash
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@coffeeshop.com",
    "password": "TestPass123!",
    "business_name": "Test Coffee Shop",
    "plan_tier": "core"
  }'
```

**Save the `access_token` from the response!**

Example response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": "...",
    "email": "test@coffeeshop.com",
    "role": "owner"
  },
  "tenant": {
    "business_name": "Test Coffee Shop",
    "plan_tier": "core"
  }
}
```

**Export your token for easy use:**
```bash
export TOKEN="paste-your-access-token-here"
```

---

### B. Test Subscription & Platform Fees

#### 1. Activate Core Subscription ($119/mo)

```bash
curl -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_tier": "core"}'
```

You should see:
```json
{
  "success": true,
  "message": "Simulated core subscription activated",
  "subscription": {
    "plan_tier": "core",
    "status": "active",
    "monthly_cost": 119
  }
}
```

#### 2. Add Test Sales to See Platform Fees

**Test with $5,000 in sales:**
```bash
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000}'
```

Expected result:
```json
{
  "gmv": {
    "total": 5000.0
  },
  "fees": {
    "subscription_fee": 119,
    "platform_fee": 1000.0,
    "total_monthly_cost": 1119.0
  },
  "breakdown": {
    "first_10k": 500.0,
    "minimum_applied": true
  }
}
```

**$5k × 10% = $500, but minimum $1,000 applies → Total: $1,119/mo**

**Now add more sales to hit $25,000 total:**
```bash
curl -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 20000}'
```

Expected result:
```json
{
  "gmv": {
    "total": 25000.0
  },
  "fees": {
    "subscription_fee": 119,
    "platform_fee": 1750.0,
    "total_monthly_cost": 1869.0
  },
  "breakdown": {
    "first_10k": 1000.0,
    "next_40k": 750.0
  }
}
```

**$10k × 10% + $15k × 5% = $1,750 → Total: $1,869/mo**

#### 3. Check Full Subscription Status

```bash
curl http://localhost:5000/api/v1/billing/subscription-status \
  -H "Authorization: Bearer $TOKEN"
```

You'll see your complete subscription details with GMV and calculated fees.

---

### C. Test Multi-Device Access (Your Main Request!)

#### Device 1 - Your Current Computer

```bash
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "laptop-chrome-001",
    "device_name": "My Laptop - Chrome"
  }'
```

Expected:
```json
{
  "success": true,
  "device": {
    "device_name": "My Laptop - Chrome",
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

#### Device 2 - Simulate Different IP/Device

**To truly test from different IP, you would:**
1. Open a different browser/incognito mode
2. OR use your phone's mobile data (different IP)
3. OR ask a friend to test from their location

**For now, simulate with a different device ID:**

```bash
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "ipad-safari-001",
    "device_name": "iPad POS Terminal"
  }'
```

Expected:
```json
{
  "success": true,
  "limits": {
    "device_limit": 2,
    "active_devices": 2,
    "remaining": 0
  }
}
```

#### Device 3 - Should FAIL (Core allows only 2 devices)

```bash
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "iphone-safari-001",
    "device_name": "iPhone 13"
  }'
```

Expected (403 Forbidden):
```json
{
  "error": "Device limit reached",
  "message": "Your core plan allows 2 devices. Please upgrade to Growth plan for 6 devices.",
  "current_tier": "core",
  "device_limit": 2,
  "active_devices": 2
}
```

#### List Your Active Devices

```bash
curl http://localhost:5000/api/v1/devices \
  -H "Authorization: Bearer $TOKEN"
```

You'll see both devices listed.

---

### D. Test Upgrade to Growth Plan

```bash
curl -X POST http://localhost:5000/api/v1/billing/upgrade \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_tier": "growth"}'
```

Expected:
```json
{
  "message": "Successfully upgraded to growth plan",
  "new_plan": {
    "name": "Growth",
    "price": 249,
    "devices": 6,
    "team_size": 15
  }
}
```

**Now try device 3 again - it should work!**

```bash
curl -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "iphone-safari-001",
    "device_name": "iPhone 13"
  }'
```

Should succeed now (6 device limit on Growth).

---

### E. Test Auto-SKU Generation

```bash
curl -X POST http://localhost:5000/api/v1/inventory \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Espresso Blend",
    "category": "Coffee",
    "price": 12.99,
    "cost": 6.50,
    "stock_quantity": 100
  }'
```

Notice: **No SKU provided!**

Expected response:
```json
{
  "item": {
    "id": "...",
    "sku": "COFFEE-A3B2-001",
    "sku_auto_generated": true,
    "name": "Espresso Blend",
    "price": 12.99
  }
}
```

**SKU automatically generated as `COFFEE-A3B2-001`!**

Try another item:
```bash
curl -X POST http://localhost:5000/api/v1/inventory \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cappuccino Blend",
    "category": "Coffee",
    "price": 10.99
  }'
```

Gets unique SKU like `COFFEE-B4C3-001`.

---

### F. Test Task Management

#### Create a Project

```bash
curl -X POST http://localhost:5000/api/v1/tasks/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Grand Opening Prep",
    "description": "Tasks for opening week"
  }'
```

**Save the project ID from response.**

#### Create Tasks

```bash
curl -X POST http://localhost:5000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Order coffee beans",
    "description": "Need 50 lbs of house blend",
    "priority": "high",
    "status": "to_do"
  }'
```

```bash
curl -X POST http://localhost:5000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Set up POS terminals",
    "priority": "urgent",
    "status": "in_progress"
  }'
```

#### List Tasks

```bash
curl http://localhost:5000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN"
```

You'll see all your tasks!

#### Filter by Status

```bash
curl "http://localhost:5000/api/v1/tasks?status=in_progress&priority=urgent" \
  -H "Authorization: Bearer $TOKEN"
```

---

### G. Test Available Plans

```bash
curl http://localhost:5000/api/v1/billing/plans
```

See all 3 tiers with pricing and platform fee breakdown.

---

## Step 3: Test From Different Device/IP (Real Multi-Device Test)

### On Your Phone (Different IP):

1. **Login to get new token:**
   ```bash
   curl -X POST http://YOUR_SERVER_IP:5000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@coffeeshop.com",
       "password": "TestPass123!"
     }'
   ```

2. **Register phone as device:**
   ```bash
   curl -X POST http://YOUR_SERVER_IP:5000/api/v1/devices/register \
     -H "Authorization: Bearer TOKEN_FROM_STEP_1" \
     -H "Content-Type: application/json" \
     -d '{
       "device_id": "iphone-12-safari",
       "device_name": "Owner iPhone"
     }'
   ```

3. **Check devices from laptop:**
   ```bash
   curl http://localhost:5000/api/v1/devices \
     -H "Authorization: Bearer $TOKEN"
   ```

   You should see devices from both IPs!

---

## Step 4: Test Channel Integrations

### List Available Channels

```bash
curl http://localhost:5000/api/v1/channels \
  -H "Authorization: Bearer $TOKEN"
```

### Connect to DoorDash (requires Prime plan)

```bash
# First upgrade to Prime
curl -X POST http://localhost:5000/api/v1/billing/upgrade \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_tier": "prime"}'

# Initiate DoorDash connection
curl http://localhost:5000/api/v1/channels/doordash/connect \
  -H "Authorization: Bearer $TOKEN"
```

You'll get an OAuth URL to complete the connection.

---

## Quick Test Script

Want to test everything at once? Run this:

```bash
#!/bin/bash

echo "=== Testing OnyxPOS ==="

# 1. Register
echo -e "\n1. Registering business..."
RESPONSE=$(curl -s -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "quicktest@test.com",
    "password": "TestPass123!",
    "business_name": "Quick Test Shop",
    "plan_tier": "core"
  }')

TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "Got token: ${TOKEN:0:20}..."

# 2. Activate subscription
echo -e "\n2. Activating Core subscription..."
curl -s -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_tier": "core"}' | grep -o '"message":"[^"]*'

# 3. Add sales
echo -e "\n3. Adding $15,000 in sales..."
curl -s -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 15000}' | grep -o '"total_monthly_cost":[^,]*'

# 4. Register devices
echo -e "\n4. Registering device 1..."
curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device-1", "device_name": "Device 1"}' | grep -o '"success":[^,]*'

echo -e "\n5. Registering device 2..."
curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device-2", "device_name": "Device 2"}' | grep -o '"active_devices":[^,]*'

echo -e "\n6. Trying device 3 (should fail)..."
curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device-3", "device_name": "Device 3"}' | grep -o '"error":"[^"]*'

# 7. Create inventory with auto-SKU
echo -e "\n7. Creating item with auto-SKU..."
curl -s -X POST http://localhost:5000/api/v1/inventory \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Espresso",
    "category": "Coffee",
    "price": 3.50
  }' | grep -o '"sku":"[^"]*'

# 8. Create task
echo -e "\n8. Creating task..."
curl -s -X POST http://localhost:5000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Task",
    "priority": "high"
  }' | grep -o '"title":"[^"]*'

echo -e "\n\n=== Testing Complete! ==="
echo "Check the results above."
```

Save as `test.sh`, make executable, and run:
```bash
chmod +x test.sh
./test.sh
```

---

## What to Look For

✅ **Subscription activated** - Core plan at $119/mo
✅ **Platform fees calculated** - $15k sales = $1,250 fee
✅ **Device limits enforced** - 2 devices allowed, 3rd fails
✅ **Auto-SKU works** - Items get unique SKUs automatically
✅ **Tasks created** - Task management system working
✅ **Upgrade works** - Can upgrade to Growth/Prime

---

## Need Help?

- Check server logs in the terminal running `python3 app.py`
- All endpoints documented in `AUTONOMOUS_FEATURES_GUIDE.md`
- Full testing guide in `SUBSCRIPTION_TESTING_GUIDE.md`

Happy testing! 🚀
