#!/usr/bin/env bash
# mcp_fleet_health.sh -- verify the 7-server MCP fleet is reachable from the phone.
# Exits 0 if all up; exits 1 and prints failures otherwise.

set -u

declare -a SERVERS=(
  "3101:blinko-memory"
  "3102:market-intel"
  "3103:n8n-mcp"
  "3104:broker-os"
  "3105:supabase"
  "3106:stripe-mcp"
  "3107:email-sending-service"
)

fail=0
for entry in "${SERVERS[@]}"; do
  port="${entry%%:*}"
  expect="${entry##*:}"
  got=$(curl -sS --max-time 5 \
      -X POST \
      -H "Content-Type: application/json" \
      -H "Accept: application/json, text/event-stream" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"health","version":"1"}}}' \
      "http://127.0.0.1:${port}/mcp" 2>&1 \
    | python3 -c 'import sys,json
try:
  d=json.loads(sys.stdin.read()); print(d["result"]["serverInfo"]["name"])
except Exception:
  print("FAIL")' 2>/dev/null)
  if [ "$got" = "$expect" ]; then
    printf "  OK   port %s -> %s\n" "$port" "$got"
  else
    printf "  FAIL port %s -> %s (expected %s)\n" "$port" "${got:-no-response}" "$expect"
    fail=1
  fi
done

if [ $fail -eq 0 ]; then
  echo "MCP fleet healthy (7/7)."
  exit 0
else
  echo "MCP fleet degraded -- see failures above."
  exit 1
fi
