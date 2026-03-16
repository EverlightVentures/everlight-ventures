#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/sdcard/AA_MY_DRIVE"
REMOTE_URL="https://github.com/EverlightVentures/everlight-ventures.git"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PUBLISH_DIR="/tmp/everlight_site_publish_${STAMP}"

mkdir -p "$PUBLISH_DIR"
cd "$ROOT"

rsync -a --relative \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/LOVABLE*.md \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/README.md \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/PRODUCT_TO_PROFIT_PIPELINE.md \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/REVENUE_PLAN.md \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/SITE_ARCHITECTURE_V2.md \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/SOCIAL_CASINO_*.md \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/STRIPE_PRODUCT_CATALOG.md \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/blackjack_strategy_data.json \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/assets/ \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/edge_functions/ \
  01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/gear_engine/ \
  09_DASHBOARD/hive_dashboard/blackjack/ \
  09_DASHBOARD/hive_dashboard/broker_ops/ \
  09_DASHBOARD/hive_dashboard/business_os/ \
  09_DASHBOARD/hive_dashboard/funnel/ \
  09_DASHBOARD/hive_dashboard/rewards/ \
  09_DASHBOARD/hive_dashboard/everlight_site_copy.md \
  09_DASHBOARD/hive_dashboard/manage.py \
  09_DASHBOARD/hive_dashboard/hive_dashboard/settings.py \
  09_DASHBOARD/hive_dashboard/hive_dashboard/urls.py \
  09_DASHBOARD/reports/EVERLIGHT_BLACKJACK_OS_AUDIT_2026.md \
  09_DASHBOARD/reports/EVERLIGHT_BUSINESS_OS_AUDIT_2026.md \
  09_DASHBOARD/reports/EVERLIGHT_STACK_RATIONALIZATION_2026.md \
  09_DASHBOARD/reports/XLM_BOT_INTELLIGENCE_AUDIT_2026.md \
  WORKSPACE_MANIFEST.md \
  "$PUBLISH_DIR"

if rg -n '(sk-(live|proj|test)-[A-Za-z0-9_-]+|xox[baprs]-[A-Za-z0-9-]+|https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+|whsec_[A-Za-z0-9]+|AIza[0-9A-Za-z\-_]{20,})' "$PUBLISH_DIR"; then
  echo "Refusing to publish: potential secret detected in payload." >&2
  exit 1
fi

cd "$PUBLISH_DIR"
git init -b main >/dev/null
git config user.name "Codex"
git config user.email "codex@openai.local"
git add .
git commit -m "Update Everlight site publish payload" >/dev/null
git remote add origin "$REMOTE_URL"
git push -u origin main

echo "Published clean site repo from $PUBLISH_DIR"
