#!/usr/bin/env bash
set -euo pipefail

# Master launcher: dashboard + analytics + bots
BASE="/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/master_dashboard"
LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs/aa_services"
mkdir -p "$LOG_DIR"

echo "Starting master dashboard..."
bash "$BASE/master_restart.sh" > "$LOG_DIR/master_dashboard.log" 2>&1 &
DASH_PID=$!
echo "  Dashboard PID: ${DASH_PID} (port 8765)"

# Wait for dashboard to stabilize before starting more services
sleep 3

echo "Starting analytics..."
bash "$BASE/analytics_run.sh" > "$LOG_DIR/analytics.log" 2>&1 &
ANALYTICS_PID=$!
echo "  Analytics PID: ${ANALYTICS_PID} (port 8777)"

# Stagger bot starts to avoid memory spike
sleep 2

if [ -f "$BASE/bot_run.sh" ]; then
  echo "Starting bot dashboards..."
  bash "$BASE/bot_run.sh" > "$LOG_DIR/bots.log" 2>&1 &
  BOT_PID=$!
  echo "  Bots PID: ${BOT_PID} (ports 8501, 8502)"
fi

echo ""
echo "All services started."
echo "  adr  = restart dashboard only"
echo "  mdl  = relaunch everything"
wait
