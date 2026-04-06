#!/bin/bash
# Deploy wholesale pipeline to Oracle E5 and install crons
# Usage: bash deploy_wholesale.sh

KEY="/root/.ssh/oracle_key.pem"
E5="opc@129.159.38.250"
LOCAL_DIR="/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"
REMOTE_DIR="/home/opc/wholesale_agent"
CREDS="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"

ts() { date '+%Y-%m-%d %H:%M:%S PT'; }
log() { echo "[$(ts)] $1"; }

log "Deploying wholesale pipeline to Oracle E5..."

# Create remote dir structure
ssh -o ConnectTimeout=10 -i "$KEY" "$E5" "mkdir -p $REMOTE_DIR/{pipeline,outreach,reports,logs,failed_emails,pitches,cache,buyer_outreach,outreach_sent,daily_leads,search_urls,skip_traces}"

# Sync all Python files
log "Syncing Python files..."
scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_DIR"/*.py "$E5:$REMOTE_DIR/" 2>/dev/null
log "  Synced $(ls "$LOCAL_DIR"/*.py | wc -l) Python files"

# Sync pipeline data
log "Syncing pipeline data..."
scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_DIR/pipeline/"* "$E5:$REMOTE_DIR/pipeline/" 2>/dev/null

# Sync leads DB
if [ -f "$LOCAL_DIR/leads_db.json" ]; then
    scp -o ConnectTimeout=10 -i "$KEY" "$LOCAL_DIR/leads_db.json" "$E5:$REMOTE_DIR/" 2>/dev/null
    log "  Synced leads_db.json"
fi

# Push .env to Oracle (needed for API keys)
log "Pushing credentials..."
ssh -o ConnectTimeout=10 -i "$KEY" "$E5" "cat > /home/opc/.env.wholesale" << 'ENVEOF'
$(grep -E '^(RESEND_API_KEY|SMTP_|IMAP_|ATTOM_API_KEY|SLACK_BOT_TOKEN|ANTHROPIC_API_KEY|SUPABASE_URL|SUPABASE_SERVICE_ROLE_KEY|SUPABASE_ANON_KEY)' "$CREDS")
ENVEOF

# Install cron jobs
log "Installing cron jobs..."
ssh -o ConnectTimeout=10 -i "$KEY" "$E5" << 'CRONEOF'
# Remove old wholesale crons
crontab -l 2>/dev/null | grep -v wholesale_agent | grep -v rex_master > /tmp/cron_clean

# Add 3-phase daily pipeline (times in UTC, Oracle is UTC)
# Morning: 3 PM UTC = 8 AM PT
echo "0 15 * * * source /home/opc/.env.wholesale && cd /home/opc/wholesale_agent && python3 rex_master_pipeline.py --phase morning >> /home/opc/wholesale_agent/logs/cron.log 2>&1" >> /tmp/cron_clean

# Follow-up: 7 PM UTC = 12 PM PT
echo "0 19 * * * source /home/opc/.env.wholesale && cd /home/opc/wholesale_agent && python3 rex_master_pipeline.py --phase followup >> /home/opc/wholesale_agent/logs/cron.log 2>&1" >> /tmp/cron_clean

# Re-engage + retry: 12 AM UTC = 5 PM PT
echo "0 0 * * * source /home/opc/.env.wholesale && cd /home/opc/wholesale_agent && python3 rex_master_pipeline.py --phase reengage >> /home/opc/wholesale_agent/logs/cron.log 2>&1" >> /tmp/cron_clean

crontab /tmp/cron_clean
rm /tmp/cron_clean
echo "Crons installed:"
crontab -l | grep wholesale
CRONEOF

log "Deploy complete. Pipeline will run:"
log "  8 AM PT -- Scout + Score + Outreach + Buyer Blast"
log "  12 PM PT -- Follow-up sequences"
log "  5 PM PT -- Re-engage cold leads + retry dead letters"
log ""
log "To run immediately: ssh -i $KEY $E5 'source /home/opc/.env.wholesale && cd /home/opc/wholesale_agent && python3 rex_master_pipeline.py --phase morning'"
