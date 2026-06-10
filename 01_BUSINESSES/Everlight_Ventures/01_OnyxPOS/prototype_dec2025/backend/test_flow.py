"""
Test Complete User Flow:
1. Register → 2. Login → 3. Import Inventory → 4. Make Sale
"""
import requests
import json

BASE_URL = "http://localhost:5000/api/v1"

def test_complete_flow():
    print("🧪 Testing Complete OnyxPOS Flow\n")

    # Step 1: Register
    print("1️⃣ Registering new business...")
    random_num = import_random()
    register_data = {
        "business_name": f"Test Coffee Shop {random_num}",
        "email": f"test{random_num}@example.com",
        "password": "testpass123",
        "first_name": "John",
        "last_name": "Doe"
    }

    try:
        r = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        print(f"   Status: {r.status_code}")

        if r.status_code == 201:
            data = r.json()
            token = data.get('access_token')
            tenant = data.get('tenant', {})
            tenant_id = tenant.get('id')
            print(f"   ✅ Registered! Tenant ID: {tenant_id}")
            if tenant:
                print(f"   Subscription: {tenant.get('subscription_status', 'N/A')}")
                print(f"   Trial ends: {tenant.get('trial_ends_at', 'N/A')}")
        else:
            print(f"   ❌ Failed: {r.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Step 2: Test Import Preview
    print("\n2️⃣ Testing inventory import preview...")
    headers = {"Authorization": f"Bearer {token}"}

    import_data = {
        "items": [
            {
                "name": "Americano",
                "sku": "COFFEE-001",
                "category": "Coffee",
                "price": 4.50,
                "cost_price": 1.20,
                "stock_quantity": 100
            },
            {
                "name": "Latte",
                "sku": "COFFEE-002",
                "category": "Coffee",
                "price": 5.50,
                "cost_price": 1.50,
                "stock_quantity": 100
            }
        ]
    }

    try:
        r = requests.post(
            f"{BASE_URL}/inventory/import/preview",
            headers=headers,
            json=import_data
        )
        print(f"   Status: {r.status_code}")

        if r.status_code == 200:
            print(f"   ✅ Import preview success!")
            print(f"   Items: {r.json()}")
        else:
            print(f"   ❌ Failed: {r.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Step 3: Execute Import
    print("\n3️⃣ Executing inventory import...")
    try:
        r = requests.post(
            f"{BASE_URL}/inventory/import/execute",
            headers=headers,
            json=import_data
        )
        print(f"   Status: {r.status_code}")

        if r.status_code == 200:
            print(f"   ✅ Import executed!")
            print(f"   Created: {r.json()['created_count']} items")
        else:
            print(f"   ❌ Failed: {r.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Step 4: Create a Sale
    print("\n4️⃣ Creating test sale...")
    # First get the item we just created
    r = requests.get(f"{BASE_URL}/inventory", headers=headers)
    items = r.json()['items']
    item_id = items[0]['id']

    sale_data = {
        "items": [
            {"item_id": item_id, "quantity": 2}
        ],
        "payment_method": "cash",
        "tax_rate": 0.08
    }

    try:
        r = requests.post(
            f"{BASE_URL}/sales/transactions",
            headers=headers,
            json=sale_data
        )
        print(f"   Status: {r.status_code}")

        if r.status_code == 200:
            print(f"   ✅ Sale created!")
            txn = r.json()['transaction']
            print(f"   Transaction #: {txn['transaction_number']}")
            print(f"   Total: ${txn['total_amount']}")
        else:
            print(f"   ❌ Failed: {r.text}")
            return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    print("\n✅ ALL TESTS PASSED! OnyxPOS is working!")
    return True


def import_random():
    import random
    return random.randint(1000, 9999)


if __name__ == "__main__":
    test_complete_flow()
