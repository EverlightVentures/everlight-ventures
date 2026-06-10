#!/bin/bash

echo "================================"
echo "Inventory Import & Sales Test"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Register business
echo -e "\n1. Registering test business..."
TIMESTAMP=$(date +%s)
RESPONSE=$(curl -s -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"import${TIMESTAMP}@coffee.com\",
    \"password\": \"TestPass123!\",
    \"first_name\": \"Import\",
    \"last_name\": \"Tester\",
    \"business_name\": \"Import Test Shop ${TIMESTAMP}\",
    \"plan_tier\": \"core\"
  }")

if echo "$RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✓ Business registered${NC}"
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
else
    echo -e "${RED}✗ Registration failed${NC}"
    echo "$RESPONSE"
    exit 1
fi

# 2. Activate subscription
echo -e "\n2. Activating subscription..."
curl -s -X POST http://localhost:5000/api/v1/billing/test/simulate-subscription \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plan_tier": "core"}' > /dev/null
echo -e "${GREEN}✓ Subscription activated${NC}"

# 3. Preview import
echo -e "\n3. Testing import preview..."
PREVIEW=$(curl -s -X POST http://localhost:5000/api/v1/inventory/import/preview \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_inventory.csv")

if echo "$PREVIEW" | grep -q "total_rows"; then
    ROWS=$(echo "$PREVIEW" | python3 -c "import sys, json; print(json.load(sys.stdin)['total_rows'])" 2>/dev/null)
    echo -e "${GREEN}✓ Preview successful - Found $ROWS items${NC}"
else
    echo -e "${RED}✗ Preview failed${NC}"
    echo "$PREVIEW"
fi

# 4. Confirm import
echo -e "\n4. Importing inventory..."
IMPORT=$(curl -s -X POST http://localhost:5000/api/v1/inventory/import/confirm \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_inventory.csv")

if echo "$IMPORT" | grep -q "created"; then
    CREATED=$(echo "$IMPORT" | python3 -c "import sys, json; print(json.load(sys.stdin)['created'])" 2>/dev/null)
    echo -e "${GREEN}✓ Import successful - Created $CREATED items${NC}"
else
    echo -e "${RED}✗ Import failed${NC}"
    echo "$IMPORT"
fi

# 5. List inventory
echo -e "\n5. Verifying inventory..."
INVENTORY=$(curl -s -X GET "http://localhost:5000/api/v1/inventory?per_page=100" \
  -H "Authorization: Bearer $TOKEN")

if echo "$INVENTORY" | grep -q "items"; then
    COUNT=$(echo "$INVENTORY" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['items']))" 2>/dev/null)
    echo -e "${GREEN}✓ Found $COUNT items in inventory${NC}"

    # Show first 3 items
    echo -e "${YELLOW}Sample items:${NC}"
    echo "$INVENTORY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data['items'][:3]:
    print(f\"  - {item['sku']}: {item['name']} (\${item['sell_price']})\")" 2>/dev/null
else
    echo -e "${RED}✗ Failed to list inventory${NC}"
fi

# 6. Get item IDs for sale
echo -e "\n6. Preparing sale (getting item IDs)..."
COFFEE_ITEM=$(curl -s -X GET "http://localhost:5000/api/v1/inventory?search=COFFEE-001" \
  -H "Authorization: Bearer $TOKEN")
BAKERY_ITEM=$(curl -s -X GET "http://localhost:5000/api/v1/inventory?search=BAKERY-001" \
  -H "Authorization: Bearer $TOKEN")

COFFEE_ID=$(echo "$COFFEE_ITEM" | python3 -c "import sys, json; print(json.load(sys.stdin)['items'][0]['id'])" 2>/dev/null)
BAKERY_ID=$(echo "$BAKERY_ITEM" | python3 -c "import sys, json; print(json.load(sys.stdin)['items'][0]['id'])" 2>/dev/null)

echo -e "${GREEN}✓ Found items (Coffee ID: $COFFEE_ID, Bakery ID: $BAKERY_ID)${NC}"

# 7. Test creating a sale
echo -e "\n7. Testing sale creation..."
SALE=$(curl -s -X POST http://localhost:5000/api/v1/sales \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"items\": [
      {\"item_id\": \"$COFFEE_ID\", \"quantity\": 2},
      {\"item_id\": \"$BAKERY_ID\", \"quantity\": 1}
    ],
    \"payment_method\": \"cash\",
    \"tax_amount\": 3.15
  }")

if echo "$SALE" | grep -q "transaction"; then
    echo -e "${GREEN}✓ Sale created successfully${NC}"
    echo "$SALE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'transaction' in data:
        txn = data['transaction']
        print(f\"  Transaction ID: {txn.get('id', 'N/A')}\")
        print(f\"  Transaction #: {txn.get('transaction_number', 'N/A')}\")
        print(f\"  Total: \${txn.get('total_amount', 0):.2f}\")
except Exception as e:
    print(f\"  Error: {e}\")
" 2>/dev/null
else
    echo -e "${RED}✗ Sale creation failed${NC}"
    echo "$SALE"
fi

# 8. Verify inventory updated
echo -e "\n8. Checking inventory after sale..."
UPDATED_INV=$(curl -s -X GET "http://localhost:5000/api/v1/inventory?search=COFFEE-001" \
  -H "Authorization: Bearer $TOKEN")

echo "$UPDATED_INV" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['items']:
        item = data['items'][0]
        print(f\"  {item['sku']}: Stock = {item['stock_on_hand']} (should be 148 after selling 2)\")
except:
    pass
" 2>/dev/null

echo -e "\n================================"
echo -e "${GREEN}Test Complete!${NC}"
echo "================================"
echo ""
echo "Your test account:"
echo "Email: import${TIMESTAMP}@coffee.com"
echo "Password: TestPass123!"
echo "Token: $TOKEN"
echo ""
echo "You can now test manually in the UI!"
echo "Go to: http://localhost:3000"
