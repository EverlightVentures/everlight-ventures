#!/usr/bin/env bash
# Install mcp_elect cron on this node. Detects whether we're on phone,
# AceMagician, or Dell PC and sets MCP_NODE_NAME accordingly.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ELECT="$SCRIPT_DIR/mcp_elect.sh"

if [ ! -f "$ELECT" ]; then
  echo "ERROR: $ELECT not found"
  exit 1
fi

chmod +x "$ELECT" 2>/dev/null

# Detect node
HOST="$(hostname)"
case "$HOST" in
  *phone*|*localhost*|*proot*)
    NODE_NAME="phone"; PRIORITY=1 ;;
  *acemagician*|*arch*)
    NODE_NAME="acemagician"; PRIORITY=2 ;;
  *dell*|*windows*|*pc*)
    NODE_NAME="dell"; PRIORITY=3 ;;
  *)
    NODE_NAME="$HOST"; PRIORITY=9 ;;
esac

echo "Detected node: $NODE_NAME (priority $PRIORITY)"

# Add cron line
CRON_LINE="*/2 * * * * MCP_NODE_NAME=$NODE_NAME MCP_PRIORITY=$PRIORITY $ELECT >> /tmp/mcp_elect.log 2>&1"

# Update crontab if not present
if crontab -l 2>/dev/null | grep -q "mcp_elect.sh"; then
  echo "  cron already installed"
else
  ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
  echo "  cron installed: $CRON_LINE"
fi

# First election
MCP_NODE_NAME=$NODE_NAME MCP_PRIORITY=$PRIORITY "$ELECT"

echo
echo "MCP failover installed on $NODE_NAME. Tail the log:"
echo "  tail -f /tmp/mcp_elect.log"
echo
echo "Order: phone -> AceMagician -> Dell PC. Highest-priority alive node hosts the MCP fleet."
