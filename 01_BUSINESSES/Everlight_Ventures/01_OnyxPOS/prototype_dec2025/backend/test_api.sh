#!/bin/bash
# API Testing Script
# Usage: ./test_api.sh https://your-app.railway.app

if [ -z "$1" ]; then
    echo "Usage: ./test_api.sh <API_URL>"
    echo "Example: ./test_api.sh https://onyxpos-production.railway.app"
    exit 1
fi

API_URL="$1"
echo "========================================="
echo "  Testing OnyxPOS API"
echo "  URL: $API_URL"
echo "========================================="
echo ""

# Test 1: Health Check
echo "1️⃣  Testing Health Endpoint..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/health")
http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE:/d')

if [ "$http_code" = "200" ]; then
    echo "  ✅ Health check passed"
    echo "  Response: $body"
else
    echo "  ❌ Health check failed (HTTP $http_code)"
    echo "  Response: $body"
    exit 1
fi
echo ""

# Test 2: API Root
echo "2️⃣  Testing API Root..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/")
http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$http_code" = "200" ]; then
    echo "  ✅ API root accessible"
else
    echo "  ❌ API root failed (HTTP $http_code)"
fi
echo ""

# Test 3: Registration
echo "3️⃣  Testing Registration..."
TIMESTAMP=$(date +%s)
TEST_EMAIL="test-$TIMESTAMP@example.com"

registration_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "$API_URL/api/v1/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"business_name\": \"Test Store $TIMESTAMP\",
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"testpass123\",
        \"first_name\": \"Test\",
        \"last_name\": \"User\"
    }")

http_code=$(echo "$registration_response" | grep "HTTP_CODE:" | cut -d: -f2)
body=$(echo "$registration_response" | sed '/HTTP_CODE:/d')

if [ "$http_code" = "201" ]; then
    echo "  ✅ Registration successful"
    # Extract access token
    ACCESS_TOKEN=$(echo "$body" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    echo "  📝 Saved access token"
    echo "  👤 Email: $TEST_EMAIL"
else
    echo "  ❌ Registration failed (HTTP $http_code)"
    echo "  Response: $body"
    exit 1
fi
echo ""

# Test 4: Login
echo "4️⃣  Testing Login..."
login_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "$API_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"testpass123\"
    }")

http_code=$(echo "$login_response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$http_code" = "200" ]; then
    echo "  ✅ Login successful"
else
    echo "  ❌ Login failed (HTTP $http_code)"
fi
echo ""

# Test 5: Protected Endpoint (Dashboard Analytics)
echo "5️⃣  Testing Protected Endpoint (Analytics Dashboard)..."
dashboard_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X GET "$API_URL/api/v1/analytics/dashboard" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

http_code=$(echo "$dashboard_response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$http_code" = "200" ]; then
    echo "  ✅ Dashboard accessible with JWT"
else
    echo "  ❌ Dashboard failed (HTTP $http_code)"
fi
echo ""

# Test 6: Subscription Status
echo "6️⃣  Testing Subscription Status..."
subscription_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X GET "$API_URL/api/v1/billing/subscription-status" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

http_code=$(echo "$subscription_response" | grep "HTTP_CODE:" | cut -d: -f2)
body=$(echo "$subscription_response" | sed '/HTTP_CODE:/d')

if [ "$http_code" = "200" ]; then
    echo "  ✅ Subscription status retrieved"
    echo "  Response: $body"
else
    echo "  ❌ Subscription status failed (HTTP $http_code)"
fi
echo ""

# Test 7: Create Inventory Item
echo "7️⃣  Testing Create Inventory Item..."
inventory_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST "$API_URL/api/v1/inventory" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"sku\": \"TEST-$TIMESTAMP\",
        \"name\": \"Test Product\",
        \"description\": \"Test product for API testing\",
        \"sell_price\": 19.99,
        \"cost_price\": 10.00,
        \"stock_on_hand\": 100,
        \"category\": \"Test\"
    }")

http_code=$(echo "$inventory_response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$http_code" = "201" ]; then
    echo "  ✅ Inventory item created"
    ITEM_ID=$(echo "$inventory_response" | sed '/HTTP_CODE:/d' | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    echo "  📦 Item ID: $ITEM_ID"
else
    echo "  ❌ Inventory creation failed (HTTP $http_code)"
    echo "  Response: $(echo "$inventory_response" | sed '/HTTP_CODE:/d')"
fi
echo ""

# Test 8: Billing/GMV Endpoints
echo "8️⃣  Testing Billing/GMV Endpoints..."
pricing_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X GET "$API_URL/api/v1/billing/pricing-tiers")

http_code=$(echo "$pricing_response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$http_code" = "200" ]; then
    echo "  ✅ Pricing tiers accessible"
else
    echo "  ❌ Pricing tiers failed (HTTP $http_code)"
fi
echo ""

# Summary
echo "========================================="
echo "✅ API Testing Complete!"
echo ""
echo "Test Account Created:"
echo "  Email: $TEST_EMAIL"
echo "  Password: testpass123"
echo ""
echo "You can use these credentials to:"
echo "  - Log in to the mobile app"
echo "  - Test the web frontend"
echo "  - Create test sales"
echo "========================================="
