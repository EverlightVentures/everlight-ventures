#!/usr/bin/env bash
# mcp_elect.sh -- Tailnet-coordinated MCP server election.
#
# Runs every 2 min via cron on each node (phone, AceMagician, Dell PC).
# Election order: phone (highest) -> AceMagician -> Dell PC.
# Each node checks if a higher-priority node is reachable; if yes, stops local
# MCP servers; if no, starts them. The MCP fleet always runs on exactly one
# node, with sub-2-min failover when a node drops.
#
# Deploy:
#   bash 03_AUTOMATION_CORE/01_Scripts/mcp_failover/install.sh
# Then add to crontab on this node:
#   */2 * * * * /path/to/mcp_elect.sh >> /tmp/mcp_elect.log 2>&1

set -u

# Identify this node by hostname / Tailnet IP
THIS_NODE="${MCP_NODE_NAME:-$(hostname)}"
case "$THIS_NODE" in
  *phone*|*localhost*|*proot*) MY_PRIORITY=1 ;;
  *acemagician*|*arch*)        MY_PRIORITY=2 ;;
  *dell*|*windows*|*pc*)       MY_PRIORITY=3 ;;
  *) MY_PRIORITY="${MCP_PRIORITY:-9}" ;;
esac

# Tailnet hostnames of higher-priority nodes.
# Phone has no Tailscale yet -- override MCP_PHONE in env when it's joined.
# AceMagician is known at 100.93.253.49 per CLAUDE.md tailnet doctrine.
PHONE_TAILNET="${MCP_PHONE:-}"
ACE_TAILNET="${MCP_ACE:-100.93.253.49}"

PEERS_HIGHER=()
case "$MY_PRIORITY" in
  2) [ -n "$PHONE_TAILNET" ] && PEERS_HIGHER=("$PHONE_TAILNET") ;;
  3)
     [ -n "$PHONE_TAILNET" ] && PEERS_HIGHER+=("$PHONE_TAILNET")
     [ -n "$ACE_TAILNET" ] && PEERS_HIGHER+=("$ACE_TAILNET")
     ;;
esac

START_ALL="${MCP_START_SCRIPT:-/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/start_all.sh}"
STOP_ALL="${MCP_STOP_SCRIPT:-/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/mcp_servers/stop_all.sh}"

# Heartbeat dir (synced via Tailscale or rclone)
HB_DIR="${MCP_HEARTBEAT_DIR:-/var/lib/mcp_election}"
mkdir -p "$HB_DIR" 2>/dev/null || HB_DIR="/tmp/mcp_election"
mkdir -p "$HB_DIR"

date +%s > "$HB_DIR/$THIS_NODE.ts"

# Check if any higher-priority node is alive (heartbeat within last 5 min)
SHOULD_RUN=1
NOW=$(date +%s)
for peer in "${PEERS_HIGHER[@]}"; do
  HB="$HB_DIR/${peer%%.*}.ts"
  if [ -f "$HB" ]; then
    AGE=$((NOW - $(cat "$HB" 2>/dev/null || echo 0)))
    if [ "$AGE" -lt 300 ]; then
      SHOULD_RUN=0
      echo "[$(date)] $THIS_NODE: peer $peer is alive (${AGE}s old) -- standing down"
      break
    fi
  fi
  # Fallback: tcp ping the MCP port
  if timeout 2 bash -c "</dev/tcp/$peer/3101" 2>/dev/null; then
    SHOULD_RUN=0
    echo "[$(date)] $THIS_NODE: peer $peer port 3101 is open -- standing down"
    break
  fi
done

# Are MCP servers running locally?
RUNNING=$(pgrep -f "mcp-server-|mcp_server_|broker_mcp" | wc -l)

if [ "$SHOULD_RUN" -eq 1 ] && [ "$RUNNING" -eq 0 ]; then
  echo "[$(date)] $THIS_NODE: should_run=1, running=0 -- starting MCP fleet"
  if [ -x "$START_ALL" ]; then
    nohup bash "$START_ALL" > /tmp/mcp_start.log 2>&1 &
  else
    echo "[$(date)] $THIS_NODE: ERROR - start script not found at $START_ALL"
  fi
elif [ "$SHOULD_RUN" -eq 0 ] && [ "$RUNNING" -gt 0 ]; then
  echo "[$(date)] $THIS_NODE: should_run=0, running=$RUNNING -- stopping MCP fleet"
  if [ -x "$STOP_ALL" ]; then
    bash "$STOP_ALL"
  else
    pkill -f "mcp-server-|mcp_server_|broker_mcp"
  fi
else
  echo "[$(date)] $THIS_NODE: state OK (should_run=$SHOULD_RUN, running=$RUNNING)"
fi
