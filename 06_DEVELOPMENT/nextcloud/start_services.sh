#!/bin/bash
# =============================================================================
# start_services.sh -- Start Nextcloud stack INSIDE PRoot-Ubuntu
# No systemctl. Uses apache2ctl + mysqld_safe directly.
#
# Call from Termux (outside PRoot):
#   proot-distro login ubuntu --bind /mnt/sdcard:/mnt/sdcard -- \
#     bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/start_services.sh
#
# Or from inside PRoot:
#   bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/start_services.sh
# =============================================================================

LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud"
mkdir -p "$LOG_DIR"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(timestamp)] Starting Nextcloud services..."

# ---- MariaDB ----------------------------------------------------------------
if pgrep -x mysqld > /dev/null 2>&1; then
    echo "[$(timestamp)] MariaDB already running."
else
    echo "[$(timestamp)] Starting MariaDB..."
    mysqld_safe \
        --user=root \
        --datadir=/var/lib/mysql \
        --log-error="$LOG_DIR/mariadb.log" \
        --daemonize \
        2>>"$LOG_DIR/mariadb.log"
    sleep 3

    if pgrep -x mysqld > /dev/null 2>&1; then
        echo "[$(timestamp)] MariaDB started OK."
    else
        echo "[$(timestamp)] ERROR: MariaDB failed to start. Check $LOG_DIR/mariadb.log"
        exit 1
    fi
fi

# ---- Apache -----------------------------------------------------------------
if pgrep -x apache2 > /dev/null 2>&1; then
    echo "[$(timestamp)] Apache already running."
else
    echo "[$(timestamp)] Starting Apache..."
    apache2ctl start 2>>"$LOG_DIR/apache.log"
    sleep 2

    if pgrep -x apache2 > /dev/null 2>&1; then
        echo "[$(timestamp)] Apache started OK on port 8080."
    else
        echo "[$(timestamp)] ERROR: Apache failed to start. Check $LOG_DIR/apache.log"
        exit 1
    fi
fi

# ---- Health check -----------------------------------------------------------
PHONE_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' \
    || hostname -I | awk '{print $1}')

echo ""
echo "  Nextcloud is up."
echo "  LAN:   http://${PHONE_IP}:8080"
echo "  Local: http://localhost:8080"
echo ""
echo "  To add ngrok tunnel, run: bash setup_ngrok.sh"
