#!/bin/bash
# Install and enable always-on systemd services for bot + dashboard.
# Scope selection:
# - auto (default): use --user when available, else fallback to system scope.
# - user: force user scope.
# - system: force system scope (requires root).

set -euo pipefail

BOT_DIR="/mnt/sdcard/AA_MY_DRIVE/xlm_bot"
UNIT_SRC="$BOT_DIR/systemd"
USER_UNIT_DST="$HOME/.config/systemd/user"
SYSTEM_UNIT_DST="/etc/systemd/system"
SCOPE="${FORCE_SYSTEMD_SCOPE:-auto}"
BOT_BOOT_CMD="${BOT_BOOT_CMD:-./xpb}"
DASH_BOOT_CMD="${DASH_BOOT_CMD:-./xdr}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found"
  exit 1
fi

install_user_scope() {
  mkdir -p "$USER_UNIT_DST"
  cp -f "$UNIT_SRC/xlm-bot.service" "$USER_UNIT_DST/xlm-bot.service"
  cp -f "$UNIT_SRC/xlm-dashboard.service" "$USER_UNIT_DST/xlm-dashboard.service"

  systemctl --user daemon-reload
  systemctl --user enable --now xlm-bot.service
  systemctl --user enable --now xlm-dashboard.service

  echo "Enabled (user scope):"
  systemctl --user --no-pager --full status xlm-bot.service xlm-dashboard.service || true
}

install_system_scope() {
  if [ "${EUID}" -ne 0 ]; then
    echo "System scope install requires root. Re-run with sudo or as root."
    exit 1
  fi

  mkdir -p "$SYSTEM_UNIT_DST"
  cp -f "$UNIT_SRC/xlm-bot.service" "$SYSTEM_UNIT_DST/xlm-bot.service"
  cp -f "$UNIT_SRC/xlm-dashboard.service" "$SYSTEM_UNIT_DST/xlm-dashboard.service"

  sed -i 's/^WantedBy=.*/WantedBy=multi-user.target/' "$SYSTEM_UNIT_DST/xlm-bot.service"
  sed -i 's/^WantedBy=.*/WantedBy=multi-user.target/' "$SYSTEM_UNIT_DST/xlm-dashboard.service"

  systemctl daemon-reload
  systemctl enable --now xlm-bot.service
  systemctl enable --now xlm-dashboard.service

  echo "Enabled (system scope):"
  systemctl --no-pager --full status xlm-bot.service xlm-dashboard.service || true
}

can_use_user_scope() {
  if [ -z "${XDG_RUNTIME_DIR:-}" ] || [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    return 1
  fi
  systemctl --user status >/dev/null 2>&1
}

has_systemd_init() {
  [ -d /run/systemd/system ] && [ "$(cat /proc/1/comm 2>/dev/null || true)" = "systemd" ]
}

ensure_crontab() {
  if command -v crontab >/dev/null 2>&1; then
    return 0
  fi
  if ! command -v apt-get >/dev/null 2>&1; then
    return 1
  fi
  if [ "${EUID}" -ne 0 ]; then
    return 1
  fi
  echo "Installing cron package for @reboot persistence..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y >/dev/null 2>&1 || return 1
  apt-get install -y cron >/dev/null 2>&1 || return 1
  command -v crontab >/dev/null 2>&1
}

install_rc_local_fallback() {
  if [ "${EUID}" -ne 0 ]; then
    echo "rc.local fallback requires root; skipping."
    return 1
  fi
  local rc_path="/etc/rc.local"
  local bot_line="cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot && /bin/bash ${BOT_BOOT_CMD} >> /mnt/sdcard/AA_MY_DRIVE/xlm_bot/logs/xpb_boot.log 2>&1 &"
  local dash_line="cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot && /bin/bash ${DASH_BOOT_CMD} >> /mnt/sdcard/AA_MY_DRIVE/xlm_bot/logs/xdr_boot.log 2>&1 &"
  if [ ! -f "$rc_path" ]; then
    cat > "$rc_path" <<'EOF'
#!/bin/sh -e
exit 0
EOF
  fi
  if ! grep -Fq "$bot_line" "$rc_path"; then
    sed -i "/^exit 0/i $bot_line" "$rc_path"
  fi
  if ! grep -Fq "$dash_line" "$rc_path"; then
    sed -i "/^exit 0/i $dash_line" "$rc_path"
  fi
  chmod +x "$rc_path"
  echo "Installed rc.local fallback entries at $rc_path."
  return 0
}

install_nonsystemd_fallback() {
  echo "Systemd is unavailable in this environment. Installing non-systemd fallback."
  chmod +x "$BOT_DIR/xpb" "$BOT_DIR/xdr" "$BOT_DIR/xpb-fg" "$BOT_DIR/xdr-fg" "$BOT_DIR/xpb-guardian" 2>/dev/null || true

  cd "$BOT_DIR"
  bash "$BOT_BOOT_CMD" || true
  bash "$DASH_BOOT_CMD" || true

  if ensure_crontab; then
    current="$(crontab -l 2>/dev/null || true)"
    bot_line="@reboot cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot && /bin/bash ${BOT_BOOT_CMD} >> /mnt/sdcard/AA_MY_DRIVE/xlm_bot/logs/xpb_boot.log 2>&1"
    dash_line="@reboot cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot && /bin/bash ${DASH_BOOT_CMD} >> /mnt/sdcard/AA_MY_DRIVE/xlm_bot/logs/xdr_boot.log 2>&1"
    out="$current"
    if ! printf "%s\n" "$current" | grep -Fq "$bot_line"; then
      out="${out}"$'\n'"$bot_line"
    fi
    if ! printf "%s\n" "$current" | grep -Fq "$dash_line"; then
      out="${out}"$'\n'"$dash_line"
    fi
    printf "%s\n" "$out" | awk 'NF' | crontab -
    echo "Installed @reboot crontab entries for ${BOT_BOOT_CMD} and ${DASH_BOOT_CMD}."
  else
    echo "crontab unavailable; trying rc.local fallback."
    install_rc_local_fallback || true
  fi

  echo "Current processes:"
  pgrep -af "xpb-guardian --config config.yaml|xpb-fg --config config.yaml|main.py --config config.yaml --live --i-understand-live|xdr-fg|streamlit.*dashboard.py.*8502" || true
}

case "$SCOPE" in
  user)
    if ! has_systemd_init; then
      install_nonsystemd_fallback
      exit 0
    fi
    install_user_scope
    ;;
  system)
    if ! has_systemd_init; then
      install_nonsystemd_fallback
      exit 0
    fi
    install_system_scope
    ;;
  auto)
    if ! has_systemd_init; then
      install_nonsystemd_fallback
    elif can_use_user_scope; then
      install_user_scope
    else
      echo "No user DBus session detected; falling back to system scope."
      install_system_scope
    fi
    ;;
  *)
    echo "Unknown FORCE_SYSTEMD_SCOPE='$SCOPE' (expected: auto|user|system)"
    exit 1
    ;;
esac
