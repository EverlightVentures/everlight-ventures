#!/bin/bash
# Single poll, called by termux-job-scheduler every 15 min.
set -a
. /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env 2>/dev/null
set +a
exec python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/phone_imap_poller.py --once --since-minutes 30 >> /mnt/sdcard/AA_MY_DRIVE/_logs/inbound/phone_imap_watch.log 2>&1
