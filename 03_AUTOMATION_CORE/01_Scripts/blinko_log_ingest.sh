#!/bin/bash
# Blinko Log Ingest -- pulls log summaries from Oracle and ingests into Blinko
# Runs after Oracle log rotation to preserve knowledge before trimming
#
# Cron: 30 11 * * * bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/blinko_log_ingest.sh

ORACLE_IP="129.159.38.250"
SSH_KEY="/root/.ssh/oracle_key.pem"
BLINKO_URL="${BLINKO_URL:-http://127.0.0.1:1111}"
LOCAL_QUEUE="/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_log_queue"
REMOTE_QUEUE="/home/opc/xlm-bot/logs/blinko_queue"
LOG="/mnt/sdcard/AA_MY_DRIVE/_logs/blinko_log_ingest.log"

mkdir -p "$LOCAL_QUEUE" "$(dirname "$LOG")"

ts() { date '+%Y-%m-%d %H:%M:%S PT'; }
log() { echo "[$(ts)] $1" >> "$LOG"; echo "[$(ts)] $1"; }

# Step 1: Pull queue from Oracle
log "Pulling Blinko queue from Oracle..."
scp -o ConnectTimeout=15 -i "$SSH_KEY" "opc@${ORACLE_IP}:${REMOTE_QUEUE}/*.md" "$LOCAL_QUEUE/" 2>/dev/null
COUNT=$(ls "$LOCAL_QUEUE"/*.md 2>/dev/null | wc -l)
log "  Found $COUNT summaries to ingest"

if [ "$COUNT" -eq 0 ]; then
    log "Nothing to ingest. Done."
    exit 0
fi

# Step 2: Ingest each summary into Blinko
INGESTED=0
for f in "$LOCAL_QUEUE"/*.md; do
    [ -f "$f" ] || continue
    CONTENT=$(cat "$f")
    FNAME=$(basename "$f")

    # Try Blinko API
    RESULT=$(curl -s -X POST "$BLINKO_URL/api/v1/note/upsert" \
        -H "Content-Type: application/json" \
        -d "{\"content\": $(python3 -c "import json; print(json.dumps(open('$f').read()))"), \"type\": 1}" \
        2>/dev/null)

    if echo "$RESULT" | grep -q '"id"'; then
        log "  Ingested: $FNAME"
        INGESTED=$((INGESTED + 1))
        # Move to processed
        mkdir -p "$LOCAL_QUEUE/processed"
        mv "$f" "$LOCAL_QUEUE/processed/"
    else
        log "  Failed: $FNAME (Blinko may be down, will retry next run)"
    fi
done

# Step 3: Clean processed files from Oracle
if [ "$INGESTED" -gt 0 ]; then
    ssh -o ConnectTimeout=15 -i "$SSH_KEY" "opc@${ORACLE_IP}" \
        "find $REMOTE_QUEUE -name '*.md' -mmin +60 -delete 2>/dev/null" 2>/dev/null
    log "Cleaned Oracle queue. Ingested $INGESTED summaries into Blinko."
fi

log "Done. $INGESTED/$COUNT ingested."
