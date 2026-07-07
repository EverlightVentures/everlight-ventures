#!/usr/bin/env bash
# Watchdog: keeps the dashboard AND tailscale alive, and captures WHY it crashed.
# Runs on e5 every minute (systemd timer). Never let a crash go undiagnosed again.
cd "$(dirname "$0")/.."
PORT="${PORT:-2600}"
LOG="logs/watchdog.log"
CRASH="logs/crash_diagnosis.log"
mkdir -p logs
ts() { date '+%Y-%m-%d %H:%M:%S %Z'; }

# 1. Keep tailscale online (his standing frustration -- never let it revert).
if command -v tailscale >/dev/null 2>&1; then
  if ! tailscale status >/dev/null 2>&1; then
    echo "$(ts) tailscale DOWN -> bringing up" >> "$LOG"
    (tailscale up --ssh 2>/dev/null || sudo tailscale up --ssh 2>/dev/null) || true
  fi
fi

# 2. Health-check the dashboard. If it does not answer, capture the crash cause
#    from the journal BEFORE restarting, so the reason is never lost.
if ! curl -s --max-time 8 "http://127.0.0.1:${PORT}/healthz" | grep -q '"ok":true'; then
  echo "$(ts) dashboard NOT healthy -> diagnosing + restarting" >> "$LOG"
  {
    echo "===== CRASH $(ts) ====="
    echo "--- last 40 journal lines (systemd user service) ---"
    journalctl --user -u solano-desk.service -n 40 --no-pager 2>/dev/null | tail -40
    echo "--- last 20 stderr lines ---"
    tail -20 logs/error.log 2>/dev/null
    echo "--- memory + top python procs ---"
    free -h | head -2
    ps -o pid,rss,%cpu,cmd -C python3 2>/dev/null | head -6
    echo ""
  } >> "$CRASH"
  systemctl --user restart solano-desk.service 2>/dev/null || bash scripts/start_dashboard.sh &
fi
