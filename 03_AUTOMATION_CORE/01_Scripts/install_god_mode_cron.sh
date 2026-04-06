#!/bin/bash
# Install God Mode cron on Oracle E5
# Replaces the hourly hive_deal_orchestrator with 10-minute god mode
#
# Run this on Oracle E5:
#   bash install_god_mode_cron.sh
#
# Or from the phone:
#   ssh -i /root/.ssh/oracle_key.pem opc@129.159.38.250 'bash /home/opc/install_god_mode_cron.sh'

echo "=== Installing God Mode Cron ==="

# Backup current crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null
echo "Backed up current crontab to /tmp/"

# Remove old orchestrator cron (any line with hive_deal_orchestrator)
crontab -l 2>/dev/null | grep -v 'hive_deal_orchestrator' > /tmp/crontab_new.txt

# Check if god mode cron already exists
if grep -q 'hive_god_mode' /tmp/crontab_new.txt; then
    echo "God Mode cron already installed. Updating..."
    grep -v 'hive_god_mode' /tmp/crontab_new.txt > /tmp/crontab_clean.txt
    mv /tmp/crontab_clean.txt /tmp/crontab_new.txt
fi

# Add God Mode cron -- every 10 minutes
echo '*/10 * * * * source /home/opc/.env && cd /home/opc && python3 hive_god_mode.py >> /tmp/hive_god_mode.log 2>&1' >> /tmp/crontab_new.txt

# Install new crontab
crontab /tmp/crontab_new.txt

echo "Done. New crontab:"
crontab -l | grep -E 'god_mode|orchestrator'
echo ""
echo "God Mode will run every 10 minutes."
echo "Old orchestrator cron has been removed."
echo "Logs: /tmp/hive_god_mode.log"
