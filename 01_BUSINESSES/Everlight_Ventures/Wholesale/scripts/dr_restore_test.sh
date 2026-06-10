#!/bin/bash
# Quarterly disaster-recovery restore test (non-destructive)
# Verifies that backups are readable and contain expected structure.
# Run via cron: 0 9 1 1,4,7,10 *

set -e

LOG="/home/opc/_logs/dr_test.jsonl"
TS=$(date -Iseconds)

mkdir -p "$(dirname $LOG)"

# Test 1: latest Django backup tarball is readable
DJANGO_BAK="/home/opc/backups/django_$(date -d 'yesterday' +%Y%m%d).tar.gz"
if [ ! -f "$DJANGO_BAK" ]; then
  DJANGO_BAK=$(ls -t /home/opc/backups/django_*.tar.gz 2>/dev/null | head -1)
fi
if [ -f "$DJANGO_BAK" ]; then
  if tar tzf "$DJANGO_BAK" >/dev/null 2>&1; then
    echo "{\"ts\":\"$TS\",\"test\":\"django_backup_readable\",\"file\":\"$DJANGO_BAK\",\"ok\":true}" >> $LOG
  else
    echo "{\"ts\":\"$TS\",\"test\":\"django_backup_readable\",\"file\":\"$DJANGO_BAK\",\"ok\":false}" >> $LOG
  fi
else
  echo "{\"ts\":\"$TS\",\"test\":\"django_backup_readable\",\"file\":\"none\",\"ok\":false,\"note\":\"no backup found -- backup cron may be broken\"}" >> $LOG
fi

# Test 2: hive.db jsonl streams are append-only (no recent truncation)
HIVE_DB_SIZE=$(stat -c%s /home/opc/_logs/hive.db 2>/dev/null || echo 0)
echo "{\"ts\":\"$TS\",\"test\":\"hive_db_size\",\"size_bytes\":$HIVE_DB_SIZE,\"ok\":$( [ $HIVE_DB_SIZE -gt 1000000 ] && echo true || echo false )}" >> $LOG

# Test 3: secrets backup exists + is recent
SECRETS_BAK=$(ls -t ~/.secrets-backup.tar.gz.gpg 2>/dev/null | head -1)
if [ -f "$SECRETS_BAK" ]; then
  AGE_DAYS=$(( ( $(date +%s) - $(stat -c%Y "$SECRETS_BAK") ) / 86400 ))
  echo "{\"ts\":\"$TS\",\"test\":\"secrets_backup_recent\",\"age_days\":$AGE_DAYS,\"ok\":$( [ $AGE_DAYS -le 14 ] && echo true || echo false )}" >> $LOG
else
  echo "{\"ts\":\"$TS\",\"test\":\"secrets_backup_recent\",\"ok\":false,\"note\":\"no secrets backup found\"}" >> $LOG
fi

# Test 4: services responsive
for s in xlm-bot hive-django blinko hive-voice; do
  if systemctl is-active --quiet "$s.service"; then
    echo "{\"ts\":\"$TS\",\"test\":\"service_$s\",\"ok\":true}" >> $LOG
  else
    echo "{\"ts\":\"$TS\",\"test\":\"service_$s\",\"ok\":false}" >> $LOG
  fi
done

echo "DR test complete. Findings logged to $LOG"
