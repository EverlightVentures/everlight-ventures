#!/data/data/com.termux/files/usr/bin/bash
# kill_termux_badge_flash.sh -- Z Fold 7 + One UI 8.5 badge-flash killer.
#
# Uses wireless ADB (NO ROOT) to:
#   1. Disable Samsung's BadgeProvider system-wide (kills the bracket-number badge)
#   2. Force Termux foreground notification channels to IMPORTANCE_MIN (no banner, no pulse)
#   3. Revoke Termux SYSTEM_ALERT_WINDOW (no floating overlay redraws)
#   4. Suppress Termux POST_NOTIFICATIONS to "ignore" mode (notification posted but invisible)
#
# Termux keeps running -- foreground service contract satisfied, just nothing visible.
# Reversible: bash kill_termux_badge_flash.sh --restore
#
# REQUIRES wireless ADB to be paired + connected before running.
# Setup (one-time, ~30 seconds, no PC needed):
#   1. Settings -> Developer options -> Wireless debugging -> ON
#   2. Inside Wireless debugging -> "Pair device with pairing code"
#      note: PAIR_IP:PAIR_PORT and the 6-digit pairing code
#   3. Run in Termux native (NOT inside proot/ubuntu):
#        pkg install -y android-tools
#        adb pair PAIR_IP:PAIR_PORT
#        (enter the 6-digit code when prompted)
#   4. Back on phone: the main "Wireless debugging" screen shows IP:CONNECT_PORT
#      (this is a DIFFERENT port than the pairing one)
#   5. Run: adb connect CONNECT_IP:CONNECT_PORT
#   6. Verify: adb devices  -> should show "device" (not "unauthorized")
#   7. Then run THIS script.

set -u

ACTION="${1:-kill}"
PKGS=(com.termux com.termux.boot com.termux.api com.termux.widget com.termux.styling)
BADGE_PKG="com.sec.android.provider.badge"

require_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "[FATAL] adb not installed. From native Termux (not proot), run:"
    echo "  pkg install -y android-tools"
    exit 1
  fi
  if ! adb devices 2>/dev/null | grep -qE "device$|emulator"; then
    echo "[FATAL] no ADB device connected. Wireless ADB setup steps:"
    echo "  1. Settings -> Developer options -> Wireless debugging -> ON"
    echo "  2. Pair device with pairing code -> note IP:PORT + 6-digit code"
    echo "  3. adb pair <IP:PORT>  (enter code when prompted)"
    echo "  4. adb connect <IP:PORT>  (using the main Wireless debugging port, not pair port)"
    echo "  5. adb devices  -> verify shows 'device'"
    echo "  6. Re-run this script."
    exit 1
  fi
  echo "[OK] adb connected: $(adb devices | grep -v 'List' | head -1)"
}

kill_badges() {
  echo ""
  echo "=== KILL MODE ==="
  echo ""
  echo "[1/4] Disabling Samsung BadgeProvider (kills ALL bracket-number badges)..."
  if adb shell pm disable-user --user 0 "$BADGE_PKG" 2>&1 | tee /tmp/badge_kill.log; then
    if grep -q "new state: disabled" /tmp/badge_kill.log; then
      echo "      [OK] BadgeProvider disabled"
    else
      echo "      [WARN] BadgeProvider command returned: $(cat /tmp/badge_kill.log)"
    fi
  fi

  echo ""
  echo "[2/4] Forcing Termux notification channels to IMPORTANCE_MIN..."
  for pkg in "${PKGS[@]}"; do
    if ! adb shell pm list packages 2>/dev/null | grep -q "package:$pkg"; then
      echo "      [skip] $pkg not installed"
      continue
    fi
    for chan in termux_normal_01 termux_app_01 termux_service termux_run_command_01 \
                termux_boot termux_api termux_widget termux_app foreground; do
      adb shell cmd notification set_importance "$pkg" "$chan" IMPORTANCE_MIN 2>/dev/null || true
    done
    echo "      [OK] $pkg channels -> IMPORTANCE_MIN (or skipped if channel absent)"
  done

  echo ""
  echo "[3/4] Revoking SYSTEM_ALERT_WINDOW for Termux apps (kills floating overlay)..."
  for pkg in "${PKGS[@]}"; do
    adb shell appops set "$pkg" SYSTEM_ALERT_WINDOW deny 2>/dev/null || true
  done
  echo "      [OK] overlay permission revoked"

  echo ""
  echo "[4/4] Setting POST_NOTIFICATIONS appops to 'ignore' for Termux..."
  # Note: 'ignore' on POST_NOTIFICATIONS means the app's notify() calls silently no-op.
  # Foreground service contract is still satisfied because the channel exists.
  # We do this LAST because it's the most aggressive.
  for pkg in com.termux.api com.termux.widget; do
    adb shell appops set "$pkg" POST_NOTIFICATION ignore 2>/dev/null || true
    echo "      [OK] $pkg POST_NOTIFICATION -> ignore"
  done
  echo "      [skip] com.termux + com.termux.boot left alone (foreground service needs to post)"

  echo ""
  echo "=== DONE ==="
  echo "Force-stop Termux now and reopen:"
  echo "  Settings -> Apps -> Termux -> Force stop"
  echo "Then open Termux again. The bracket badge should be GONE."
  echo ""
  echo "If badge still flashes after force-stop + reopen, the source is the"
  echo "Z Fold 7 Taskbar app-running indicator (a different system component)."
  echo "In that case, also run:"
  echo "  adb shell pm disable-user --user 0 com.samsung.android.app.taskedge"
  echo "  adb shell settings put global enable_taskbar 0"
}

restore_badges() {
  echo ""
  echo "=== RESTORE MODE ==="
  echo ""
  echo "[1/3] Re-enabling Samsung BadgeProvider..."
  adb shell pm enable "$BADGE_PKG" 2>&1
  echo ""
  echo "[2/3] Re-enabling Termux SYSTEM_ALERT_WINDOW..."
  for pkg in "${PKGS[@]}"; do
    adb shell appops set "$pkg" SYSTEM_ALERT_WINDOW default 2>/dev/null || true
  done
  echo ""
  echo "[3/3] Re-enabling Termux POST_NOTIFICATIONS..."
  for pkg in com.termux.api com.termux.widget; do
    adb shell appops set "$pkg" POST_NOTIFICATION allow 2>/dev/null || true
  done
  echo ""
  echo "Restored. Force-stop + reopen Termux to apply."
}

case "$ACTION" in
  kill|--kill|"")
    require_adb
    kill_badges
    ;;
  restore|--restore)
    require_adb
    restore_badges
    ;;
  *)
    echo "Usage: $0 [kill|restore]"
    exit 1
    ;;
esac
