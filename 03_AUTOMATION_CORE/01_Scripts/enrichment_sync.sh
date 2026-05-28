#!/bin/bash
# enrichment_sync.sh -- pull harvester ledger from E5 to phone for ledger_to_leads.
# Runs on the phone before ledger_to_leads + osint_enrich.
set -e
DEST=/mnt/sdcard/AA_MY_DRIVE/_logs/enrichment
mkdir -p "$DEST"
rsync -ah --no-perms --no-times \
  -e "ssh -i /root/.ssh/github_deploy -o BatchMode=yes -o ConnectTimeout=15" \
  e5-mother:/home/ubuntu/AA_MY_DRIVE/_logs/enrichment/assessor_harvester.jsonl \
  "$DEST/assessor_harvester_e5.jsonl" 2>&1 | tail -3
echo "[enrichment_sync] $(wc -l < $DEST/assessor_harvester_e5.jsonl) rows local"
