#!/bin/bash
# ============================================
# Gear Engine One-Click Setup
# ============================================
# This script:
#   1. Links Supabase CLI to the project
#   2. Pushes the gear engine migration (creates tables + seeds data)
#   3. Verifies the cron job is installed
#   4. Runs a dry test of the daily drop orchestrator
#
# Prerequisites:
#   - Refresh your Supabase access token at: https://supabase.com/dashboard/account/tokens
#   - Set it: export SUPABASE_ACCESS_TOKEN=sbp_xxxxx
#   - Set your DB password: export SUPABASE_DB_PASSWORD=xxxxx
#     (found in Supabase Dashboard > Settings > Database > Connection string)
#
# Usage:
#   bash gear_engine_setup.sh
# ============================================

set -euo pipefail

PROJECT_REF="jdqqmsmwmbsnlnstyavl"
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
MIGRATION_FILE="$ROOT_DIR/supabase/migrations/20260318_gear_engine_tables.sql"

echo "============================================"
echo "  GEAR ENGINE SETUP"
echo "============================================"

# Check token
if [ -z "${SUPABASE_ACCESS_TOKEN:-}" ]; then
    echo "ERROR: SUPABASE_ACCESS_TOKEN not set."
    echo "  1. Go to https://supabase.com/dashboard/account/tokens"
    echo "  2. Generate a new token"
    echo "  3. Run: export SUPABASE_ACCESS_TOKEN=sbp_xxxxx"
    exit 1
fi

# Check DB password
if [ -z "${SUPABASE_DB_PASSWORD:-}" ]; then
    echo "ERROR: SUPABASE_DB_PASSWORD not set."
    echo "  1. Go to Supabase Dashboard > Settings > Database"
    echo "  2. Copy your database password"
    echo "  3. Run: export SUPABASE_DB_PASSWORD=xxxxx"
    exit 1
fi

echo ""
echo "[1/4] Linking Supabase project..."
cd "$ROOT_DIR"
supabase link --project-ref "$PROJECT_REF" --password "$SUPABASE_DB_PASSWORD" 2>/dev/null || true
echo "  Linked to $PROJECT_REF"

echo ""
echo "[2/4] Pushing gear engine migration..."
if [ -f "$MIGRATION_FILE" ]; then
    supabase db push --password "$SUPABASE_DB_PASSWORD" 2>&1 || {
        echo "  Migration push failed. Trying direct psql..."
        DB_URL="postgresql://postgres.${PROJECT_REF}:${SUPABASE_DB_PASSWORD}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        psql "$DB_URL" -f "$MIGRATION_FILE" 2>&1
    }
    echo "  Tables created + seed data loaded"
else
    echo "  ERROR: Migration file not found at $MIGRATION_FILE"
    exit 1
fi

echo ""
echo "[3/4] Verifying cron job..."
if crontab -l 2>/dev/null | grep -q "daily_drop_orchestrator"; then
    echo "  Cron OK: $(crontab -l | grep daily_drop_orchestrator)"
else
    echo "  Installing cron..."
    (crontab -l 2>/dev/null; echo "# Daily Gear Drop -- 6PM PT daily"; echo "0 18 * * * cd $ROOT_DIR && python3 03_AUTOMATION_CORE/01_Scripts/daily_drop_orchestrator.py full >> _logs/gear_drops/cron.log 2>&1") | crontab -
    echo "  Cron installed"
fi

echo ""
echo "[4/4] Running dry test..."
cd "$ROOT_DIR"
python3 03_AUTOMATION_CORE/01_Scripts/daily_drop_orchestrator.py fetch 2>&1

echo ""
echo "============================================"
echo "  SETUP COMPLETE"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Paste LOVABLE_GEAR_DROP_PROMPT.md into Lovable to build the frontend"
echo "  2. The orchestrator will auto-publish at 6 PM PT daily"
echo "  3. To publish NOW: python3 03_AUTOMATION_CORE/01_Scripts/daily_drop_orchestrator.py full"
echo ""
