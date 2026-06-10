#!/usr/bin/env bash
# Cron wrapper for auto_sort_transcripts.py
# Runs hourly. Logs to /mnt/sdcard/AA_MY_DRIVE/_logs/auto_sort_transcripts.log
#
# Install on phone:
#   crontab -e
#   0 * * * * /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/auto_sort_transcripts.sh
#
# Install on Oracle E5 (after deploy_to_oracle.sh syncs it):
#   ssh oracle-e5
#   crontab -e
#   0 * * * * /home/opc/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/auto_sort_transcripts.sh

set -euo pipefail

# Load API key from the credentials file if available
if [ -f "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"
  set +a
fi

cd "$(dirname "$0")"
python3 auto_sort_transcripts.py --apply 2>&1
