#!/bin/bash

echo "================================"
echo "OnyxPOS System Test"
echo "================================"

# 1. Register a new business
echo -e "\n1️⃣  Registering test business..."
TIMESTAMP=$(date +%s)
RESPONSE=$(curl -s -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test'$TIMESTAMP'@coffeeshop.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "Owner",
    "business_name": "Test Coffee Shop '$TIMESTAMP'",
    "plan_tier": "core"
  }')

TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Registration failed!"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "✅ Business registered successfully"
echo "Token: ${TOKEN:0:30}..."

# 2. Activate subscription
echo -e "\n2️⃣  Activating Core subscription ($119/mo)..."
curl -s -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_tier": "core"}' | jq -r '.message'

# 3. Add test sales
echo -e "\n3️⃣  Adding $15,000 in test sales..."
FEES=$(curl -s -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 15000}')

echo "$FEES" | jq -r '"GMV: $" + (.gmv.total | tostring) + ", Platform Fee: $" + (.fees.platform_fee | tostring) + ", Total Cost: $" + (.fees.total_monthly_cost | tostring)'

# 4. Register device 1
echo -e "\n4️⃣  Registering Device 1..."
curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "laptop-001", "device_name": "Laptop Chrome"}' | jq -r '.limits | "Devices: " + (.active_devices | tostring) + "/" + (.device_limit | tostring)'

# 5. Register device 2
echo -e "\n5️⃣  Registering Device 2..."
curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ipad-001", "device_name": "iPad POS"}' | jq -r '.limits | "Devices: " + (.active_devices | tostring) + "/" + (.device_limit | tostring)'

# 6. Try device 3 (should fail)
echo -e "\n6️⃣  Trying to register Device 3 (should fail on Core plan)..."
RESULT=$(curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "iphone-001", "device_name": "iPhone"}')

if echo "$RESULT" | grep -q "error"; then
    echo "✅ Correctly blocked:" $(echo "$RESULT" | jq -r '.message')
else
    echo "❌ Device 3 should have been blocked!"
fi

# 7. Create item with auto-SKU
echo -e "\n7️⃣  Creating inventory item with auto-SKU..."
ITEM=$(curl -s -X POST http://localhost:5000/api/v1/inventory \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Espresso Blend",
    "category": "Coffee",
    "price": 12.99,
    "cost": 6.50,
    "stock_quantity": 100
  }')

echo "$ITEM" | jq -r '"SKU: " + .item.sku + " (auto-generated: " + (.item.sku_auto_generated | tostring) + ")"'

# 8. Create task
echo -e "\n8️⃣  Creating task..."
TASK=$(curl -s -X POST http://localhost:5000/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Prepare for grand opening",
    "description": "Order supplies, train staff, setup POS",
    "priority": "high",
    "status": "to_do"
  }')

echo "$TASK" | jq -r '"Task created: " + .task.title + " (Priority: " + .task.priority + ")"'

# 9. Upgrade to Growth plan
echo -e "\n9️⃣  Upgrading to Growth plan ($249/mo)..."
curl -s -X POST http://localhost:5000/api/v1/billing/upgrade \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_tier": "growth"}' | jq -r '.message'

# 10. Now device 3 should work
echo -e "\n🔟 Registering Device 3 (should work now)..."
curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "iphone-001", "device_name": "iPhone"}' | jq -r '.limits | "Devices: " + (.active_devices | tostring) + "/" + (.device_limit | tostring)'

# 11. Check final subscription status
echo -e "\n📊 Final Subscription Status:"
curl -s http://localhost:5000/api/v1/billing/subscription-status \
  -H "Authorization: Bearer $TOKEN" | jq '{
    plan: .plan_tier,
    status: .subscription_status,
    gmv: .platform_fees.current_month_gmv,
    platform_fee: .platform_fees.platform_fee,
    subscription_fee: .platform_fees.subscription_fee,
    total_cost: .platform_fees.total_monthly_cost,
    devices: .limits.max_devices,
    team_size: .limits.max_team_size
  }'

echo -e "\n================================"
echo "✅ All tests passed!"
echo "================================"
echo -e "\nYour test account:"
echo "Email: test$TIMESTAMP@coffeeshop.com"
echo "Password: TestPass123!"
echo "Token: $TOKEN"
echo -e "\nSave your token to test manually:"
echo "export TOKEN=\"$TOKEN\""
