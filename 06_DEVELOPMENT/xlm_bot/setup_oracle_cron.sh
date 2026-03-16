#!/bin/bash
# Script to generate crontab entries for Oracle VM

BOT_DIR="/home/opc/xlm-bot"

echo "### XLM BOT AUTOMATION ###"
echo "1-56/5 * * * * flock -xn /tmp/xlm_memguard.lock $BOT_DIR/memory_guard.sh"
echo "2-57/5 * * * * flock -xn /tmp/xlm_watchdog.lock $BOT_DIR/watchdog.sh"
echo "*/10 * * * * flock -xn /tmp/xlm_cb.lock $BOT_DIR/circuit_breaker.sh"
echo "0 * * * * flock -xn /tmp/xlm_logrotate.lock $BOT_DIR/log_rotate.sh"
echo "### END XLM BOT AUTOMATION ###"

echo ""
echo "INSTRUCTIONS:"
echo "1. SSH into Oracle VM: ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196"
echo "2. Run: crontab -e"
echo "3. Paste the lines above into the editor and save."
