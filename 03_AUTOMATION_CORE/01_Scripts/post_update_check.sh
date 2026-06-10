#!/bin/bash
# post_update_check.sh -- run this after any Samsung One UI / Android OS update.
#
# Why: major OS updates reset notification channels, battery whitelists, and
# auto-start permissions. After 2026-05-13 (One UI 8.5), Termux flashed 3x/sec
# because the foreground-service notification channel was bumped from Silent to
# Alerting. This script verifies the consequences are still intact and tells
# you exactly which Settings toggle to fix if something regressed.
#
# Usage: bash 03_AUTOMATION_CORE/01_Scripts/post_update_check.sh

set -u
ROOT=/mnt/sdcard/AA_MY_DRIVE
PASS=0
FAIL=0
WARN=0

ok()   { echo "  [OK]   $*"; PASS=$((PASS+1)); }
fail() { echo "  [FAIL] $*"; FAIL=$((FAIL+1)); }
warn() { echo "  [WARN] $*"; WARN=$((WARN+1)); }
hdr()  { echo ""; echo "=== $* ==="; }

hdr "Termux:Boot ran (start_hive + xlm_bot)"
if [ -f /data/data/com.termux/files/home/.termux/boot/xlm_bot_keepalive.pid ]; then
  pid=$(cat /data/data/com.termux/files/home/.termux/boot/xlm_bot_keepalive.pid 2>/dev/null)
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    ok "xlm_bot keepalive alive (pid $pid)"
  else
    fail "xlm_bot keepalive pidfile exists but process is dead -- reboot or run keepalive manually"
  fi
else
  fail "no keepalive pidfile -- Termux:Boot permission likely revoked (Settings -> Apps -> Termux:Boot -> Permissions)"
fi

hdr "Crons are loaded"
n=$(crontab -l 2>/dev/null | grep -v '^#' | grep -cE '^\s*[0-9*/]')
if [ "$n" -ge 10 ]; then
  ok "$n cron lines active"
else
  fail "only $n cron lines -- did crond start? Run 'crond' or check ~/.termux/boot/start_hive.sh"
fi

hdr "Watchdog cron is NOT every-minute (flash multiplier)"
if crontab -l 2>/dev/null | grep -E '^\s*\* \* \* \* \* .*dashboards_watchdog' >/dev/null; then
  fail "watchdog still every-minute -- spawn rate is 5x normal. Edit crontab -e and change to */5"
else
  ok "watchdog is on the slow schedule"
fi

hdr "notify_status.sh is silenced (no termux-notification calls)"
for f in $ROOT/06_DEVELOPMENT/xlm_bot/notify_status.sh $ROOT/06_DEVELOPMENT/everlightventures/06_DEVELOPMENT/xlm_bot/notify_status.sh; do
  if [ -f "$f" ]; then
    if grep -qE '^[[:space:]]*termux-notification[[:space:]]' "$f"; then
      fail "$f still has an uncommented termux-notification call"
    else
      ok "$(basename $(dirname $f))/notify_status.sh -- silenced"
    fi
  fi
done

hdr "termux-wake-lock NOT called from shell init (THE flash source on One UI 8.5)"
for f in /data/data/com.termux/files/home/.bashrc /data/data/com.termux/files/home/bin/ubuntu $ROOT/03_AUTOMATION_CORE/01_Scripts/everlight_shell.zsh; do
  if [ -f "$f" ]; then
    if grep -qE '^[[:space:]]*termux-wake-lock' "$f"; then
      fail "$f calls termux-wake-lock on every shell -- THIS IS THE FLASH SOURCE. Comment it out."
    else
      ok "$(basename $f) -- wake-lock not fired per-shell"
    fi
  fi
done

hdr "Local dashboards respond"
for port in 2000 2200 2300 2400 2500 2700; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:$port/ 2>/dev/null)
  if [ "$code" = "200" ] || [ "$code" = "404" ]; then
    ok ":$port responds ($code)"
  else
    warn ":$port not responding ($code) -- watchdog will restart on next cycle"
  fi
done

hdr "SSH tunnel to Oracle e5-mother"
if pgrep -f "ssh.*-L 5678.*opc@" >/dev/null 2>&1; then
  ok "n8n tunnel alive"
else
  warn "n8n tunnel dead -- start_hive.sh re-creates on boot, or run manually"
fi

hdr "Sticky Termux notifications cleared"
warn "cannot inspect Android notification stack from inside proot -- if you still see flashes after this script reports clean, do the OS-side toggle (see footer)"

echo ""
echo "================================================================"
echo " Summary: $PASS pass / $WARN warn / $FAIL fail"
echo "================================================================"
echo ""
echo "If you STILL see Termux notifications flashing after this script:"
echo "  Settings -> Apps -> Termux -> Notifications -> Allow notifications OFF"
echo "  Settings -> Apps -> Termux:Boot -> Notifications -> Allow notifications OFF"
echo "  Settings -> Apps -> Termux:API -> Notifications -> Allow notifications OFF"
echo "  Termux keeps running -- Android shows a minimal system indicator instead."
echo ""
echo "After ANY major Android update, also re-check:"
echo "  Settings -> Apps -> Termux -> Battery -> Unrestricted"
echo "  Settings -> Apps -> Termux:Boot -> Permissions -> all enabled"
echo "  Settings -> Battery -> Background usage limits -> Termux removed from Deep Sleeping"
echo "  Settings -> Notifications -> Notification cooldown -> OFF for Termux"

exit $FAIL
