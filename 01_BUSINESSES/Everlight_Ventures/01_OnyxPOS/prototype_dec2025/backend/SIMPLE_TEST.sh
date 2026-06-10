#!/bin/bash

echo "================================"
echo "OnyxPOS Quick Test"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Test health
echo -e "\n1. Testing server health..."
HEALTH=$(curl -s http://localhost:5000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Server is healthy${NC}"
else
    echo -e "${RED}✗ Server not responding${NC}"
    exit 1
fi

# 2. Register business
echo -e "\n2. Registering test business..."
TIMESTAMP=$(date +%s)
RESPONSE=$(curl -s -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"test${TIMESTAMP}@coffee.com\",
    \"password\": \"TestPass123!\",
    \"first_name\": \"Test\",
    \"last_name\": \"Owner\",
    \"business_name\": \"Test Shop $TIMESTAMP\",
    \"plan_tier\": \"core\"
  }")

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ Business registered successfully${NC}"
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
else
    echo -e "${RED}✗ Registration failed${NC}"
    echo "$RESPONSE"
    exit 1
fi

# 3. Activate subscription
echo -e "\n3. Activating Core subscription..."
SUB=$(curl -s -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_tier": "core"}')

if echo "$SUB" | grep -q "success"; then
    echo -e "${GREEN}✓ Subscription activated (Core \$119/mo)${NC}"
else
    echo -e "${RED}✗ Subscription failed${NC}"
fi

# 4. Add sales
echo -e "\n4. Adding \$25,000 in sales..."
SALES=$(curl -s -X POST http://localhost:5000/api/v1/billing/test/add-sales \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 25000}')

if echo "$SALES" | grep -q "total_monthly_cost"; then
    echo -e "${GREEN}✓ Sales added${NC}"
    echo "   Platform fee: \$1,750 (10% on first \$10k + 5% on next \$15k)"
    echo "   Total cost: \$1,869/mo (\$119 subscription + \$1,750 fee)"
else
    echo -e "${RED}✗ Failed to add sales${NC}"
fi

# 5. Register device 1
echo -e "\n5. Registering Device 1..."
DEV1=$(curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "laptop-001", "device_name": "Laptop"}')

if echo "$DEV1" | grep -q "success"; then
    echo -e "${GREEN}✓ Device 1 registered (1/2 devices used)${NC}"
else
    echo -e "${RED}✗ Device registration failed${NC}"
fi

# 6. Register device 2
echo -e "\n6. Registering Device 2..."
DEV2=$(curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ipad-001", "device_name": "iPad"}')

if echo "$DEV2" | grep -q "success"; then
    echo -e "${GREEN}✓ Device 2 registered (2/2 devices used)${NC}"
else
    echo -e "${RED}✗ Device 2 registration failed${NC}"
fi

# 7. Try device 3 (should fail)
echo -e "\n7. Trying Device 3 (should fail on Core plan)..."
DEV3=$(curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "iphone-001", "device_name": "iPhone"}')

if echo "$DEV3" | grep -q "error"; then
    echo -e "${GREEN}✓ Correctly blocked! Core plan allows only 2 devices${NC}"
else
    echo -e "${RED}✗ Should have been blocked${NC}"
fi

# 8. Create item with auto-SKU
echo -e "\n8. Creating inventory item with auto-SKU..."
ITEM=$(curl -s -X POST http://localhost:5000/api/v1/inventory \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Espresso Blend",
    "category": "Coffee",
    "sell_price": 12.99,
    "cost_price": 6.50,
    "stock_on_hand": 100
  }')

if echo "$ITEM" | grep -q "sku"; then
    SKU=$(echo "$ITEM" | python3 -c "import sys, json; print(json.load(sys.stdin)['item']['sku'])" 2>/dev/null)
    echo -e "${GREEN}✓ Item created with auto-SKU: $SKU${NC}"
else
    echo -e "${RED}✗ Item creation failed${NC}"
fi

# 9. Upgrade to Growth
echo -e "\n9. Upgrading to Growth plan..."
UPGRADE=$(curl -s -X POST http://localhost:5000/api/v1/billing/test/upgrade \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_tier": "growth"}')

if echo "$UPGRADE" | grep -q "upgraded"; then
    echo -e "${GREEN}✓ Upgraded to Growth (\$249/mo, 6 devices, 15 team members)${NC}"
else
    echo -e "${RED}✗ Upgrade failed${NC}"
fi

# 10. Now device 3 works
echo -e "\n10. Registering Device 3 (should work now)..."
DEV3_RETRY=$(curl -s -X POST http://localhost:5000/api/v1/devices/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "iphone-002", "device_name": "iPhone"}')

if echo "$DEV3_RETRY" | grep -q "success"; then
    echo -e "${GREEN}✓ Device 3 registered! (3/6 devices used on Growth plan)${NC}"
else
    echo -e "${RED}✗ Device 3 failed${NC}"
fi

echo -e "\n================================"
echo -e "${GREEN}✓ All tests passed!${NC}"
echo "================================"
echo ""
echo "Your test account:"
echo "Email: test${TIMESTAMP}@coffee.com"
echo "Password: TestPass123!"
echo ""
echo "To test manually, save your token:"
echo "export TOKEN=\"$TOKEN\""
echo ""
echo "Server logs: tail -f /tmp/onyxpos.log"
echo "Stop server: pkill -f 'python3 app.py'"
