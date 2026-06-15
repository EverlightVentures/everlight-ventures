#!/bin/bash
# dashboards_local.sh -- serve the Kalshi dashboards LOCALLY, the master_dashboard way.
#
# Rich (2026-06-15): "the dashboards should be here local, not hosted on the e5" + "follow
# the dashboard structure/bible." Per 09_DASHBOARD/master_dashboard: every dashboard is a
# LOCAL-FIRST service on a localhost port, registered in master_dashboard/config.json under
# apps[] (launchpad) + services{} (pid/health/start_cmd/log). The live trading data must
# live on e5 (bot + creds + 24/7 cron), so e5 stays the GENERATOR; this MIRRORS the rendered
# HTML down to the phone and serves it at 127.0.0.1:8503, so it shows on the Master Dashboard
# (8765) as "Kalshi Trader" and opens locally with no e5 URL. Phone crond is dead, so this is
# a singleton daemon (pidfile convention), launched by bot_run.sh / startup. If e5 is
# unreachable it keeps the last good copy.
#
#   open: http://localhost:8503/ops.html   (also /kalshi.html, /watchdog.html)
# bind:lan-required  (localhost only; viewed in the phone's own browser)
set -u
DIR=/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports
PORT="${DASH_PORT:-8503}"
REMOTE=/home/ubuntu/hive_reports
# source-on-e5 : local-name  (the P&L page is kalshi_dashboard.html in hive_reports,
# only renamed to kalshi.html in nginx -- so map it; the others are 1:1)
MIRROR="kalshi_dashboard.html:kalshi.html watchdog.html:watchdog.html ops.html:ops.html"
PIDF=/tmp/aa_kalshi_dash.pid
LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/aa_services/kalshi_dash.log

# singleton (matches the master_dashboard pid convention so /api/services/status works)
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null; then
  echo "kalshi_dash already running (pid $(cat "$PIDF"))"; exit 0
fi
echo $$ > "$PIDF"
mkdir -p "$DIR" "$(dirname "$LOG")"

# local static server as a child; clean it + the pidfile up when this daemon stops
if ! curl -s -o /dev/null --max-time 3 "http://127.0.0.1:$PORT/" 2>/dev/null; then
  ( cd "$DIR" && exec python3 -m http.server "$PORT" --bind 127.0.0.1 ) >>"$LOG" 2>&1 &
  SERVER_PID=$!
  trap 'kill "$SERVER_PID" 2>/dev/null; rm -f "$PIDF"' EXIT TERM INT
else
  trap 'rm -f "$PIDF"' EXIT TERM INT
fi

echo "$(date '+%F %T') kalshi_dash: serving $DIR at http://127.0.0.1:$PORT/ (mirroring from e5)"
while true; do
  for pair in $MIRROR; do
    src="${pair%%:*}"; dst="${pair##*:}"
    scp -q -o ConnectTimeout=12 -o ServerAliveInterval=5 "e5:$REMOTE/$src" "$DIR/$dst.tmp" 2>/dev/null \
      && mv "$DIR/$dst.tmp" "$DIR/$dst" 2>/dev/null
  done
  sleep 120
done
