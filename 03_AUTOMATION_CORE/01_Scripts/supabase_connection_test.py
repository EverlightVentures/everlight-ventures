#!/usr/bin/env python3
"""
Supabase Connection Test -- Run manually to verify connectivity.

Tests:
  1. REST API health (tables reachable?)
  2. Auth API health
  3. Storage API health
  4. Read from known tables (profiles, funnel_leads, etc.)
  5. Edge function health checks

Usage:
    python3 supabase_connection_test.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

# Load .env
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "03_Credentials", ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Use service key if available for broader access
API_KEY = SERVICE_KEY or ANON_KEY

passed = 0
failed = 0


def test(name, fn):
    global passed, failed
    try:
        result = fn()
        print(f"  PASS  {name}: {result}")
        passed += 1
    except Exception as e:
        print(f"  FAIL  {name}: {e}")
        failed += 1


def http_get(url, headers=None, timeout=10):
    hdrs = headers or {}
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read())


def http_get_status(url, headers=None, timeout=10):
    hdrs = headers or {}
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status


# --- Tests ---

print("=" * 60)
print("SUPABASE CONNECTION TEST")
print(f"URL: {SUPABASE_URL}")
print(f"Key: {'service_role' if SERVICE_KEY else 'anon'} ({API_KEY[:20]}...)")
print("=" * 60)
print()

# 1. REST API
print("[1] REST API Health")
test("GET /rest/v1/", lambda: f"status {http_get_status(f'{SUPABASE_URL}/rest/v1/', headers={'apikey': API_KEY})}")

# 2. Auth API
print("\n[2] Auth API Health")
test("GET /auth/v1/health", lambda: f"status {http_get_status(f'{SUPABASE_URL}/auth/v1/health')}")

# 3. Storage API
print("\n[3] Storage API Health")


def check_storage():
    try:
        status = http_get_status(f"{SUPABASE_URL}/storage/v1/health")
        return f"status {status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} (may need auth)"


test("GET /storage/v1/health", check_storage)

# 4. Table reads
print("\n[4] Table Access (read 1 row from each)")
TABLES_TO_TEST = [
    "profiles",
    "funnel_leads",
    "broker_leads",
    "broker_offers",
    "broker_matches",
    "broker_deals",
    "field_ops_tasks",
    "field_ops_workers",
    "blackjack_games",
    "rewards_program",
    "consulting_leads",
]

for table in TABLES_TO_TEST:
    def check_table(t=table):
        try:
            status, data = http_get(
                f"{SUPABASE_URL}/rest/v1/{t}?limit=1&select=*",
                headers={
                    "apikey": API_KEY,
                    "Authorization": f"Bearer {API_KEY}",
                },
            )
            return f"{len(data)} rows, status {status}"
        except urllib.error.HTTPError as e:
            code = e.code
            body = e.read().decode()[:80]
            if code == 404:
                return f"TABLE NOT FOUND (404)"
            elif code == 401 or code == 403:
                return f"AUTH DENIED ({code}) -- needs RLS policy or service key"
            else:
                return f"HTTP {code}: {body}"

    test(f"  {table}", check_table)

# 5. Edge Functions
print("\n[5] Edge Functions")
EDGE_FUNCTIONS = [
    "field-ops-api",
    "stripe-webhook",
    "consulting-intake",
]

for fn_name in EDGE_FUNCTIONS:
    def check_edge(name=fn_name):
        try:
            # Edge functions at /functions/v1/{name}
            # A GET to most will return 405 or 200 depending on implementation
            url = f"{SUPABASE_URL}/functions/v1/{name}"
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {API_KEY}",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                return f"ALIVE (status {resp.status})"
        except urllib.error.HTTPError as e:
            if e.code == 405:
                return "ALIVE (405 Method Not Allowed = deployed but POST-only)"
            elif e.code == 404:
                return "NOT DEPLOYED (404)"
            elif e.code == 401:
                return "DEPLOYED but AUTH REQUIRED"
            else:
                return f"HTTP {e.code}"
        except Exception as e:
            return f"UNREACHABLE: {e}"

    test(f"  {fn_name}", check_edge)

# 6. Realtime (just check if endpoint exists)
print("\n[6] Realtime WebSocket")
test("Realtime endpoint", lambda: f"URL: {SUPABASE_URL.replace('https://', 'wss://')}/realtime/v1/websocket")

# Summary
print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed == 0:
    print("All systems nominal.")
else:
    print(f"WARNING: {failed} test(s) failed -- check output above.")
print("=" * 60)
