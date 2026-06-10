#!/usr/bin/env bash
# ============================================================
# Deploy a PREVIEW of the vantaris Next.js app (the live everlightventures.io
# codebase) to Cloudflare Pages via wrangler direct-upload -- the ACTUAL deploy
# mechanism for this site (the git repos are vestigial; production is shipped by
# building locally and `wrangler pages deploy`-ing the static export).
#
# Run on a machine with Node + internet + the CF token (e5-mother is ideal;
# the phone proot cannot npm-build -> SIGSEGV). Does NOT touch production:
# it deploys to a PREVIEW branch, so live `main` is untouched until you promote.
#
# Usage on e5:   bash deploy_vantaris_preview.sh
#   (override:   BRANCH=my-preview REPO_ROOT=/home/ubuntu/AA_MY_DRIVE bash ...)
# ============================================================
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/AA_MY_DRIVE}"
VANTARIS="$REPO_ROOT/06_DEVELOPMENT/vantaris"
BRANCH="${BRANCH:-bj-finish-preview}"
PROJECT="everlightventures"
ACCOUNT_ID="d06376317522c7451e390a9af44aebba"

# CF token: env first, else the vault .env
TOKEN="${CLOUDFLARE_API_TOKEN:-${CF_API_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  TOKEN=$(grep -m1 '^CF_API_TOKEN=' "$REPO_ROOT/03_AUTOMATION_CORE/03_Credentials/.env" | cut -d= -f2-)
fi
export CLOUDFLARE_API_TOKEN="$TOKEN"
export CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID"

echo "[0/3] syncing vantaris to the bj-finish changes (blackjack window, dice, data rewire)..."
git -C "$REPO_ROOT" fetch origin bj-finish
git -C "$REPO_ROOT" checkout origin/bj-finish -- 06_DEVELOPMENT/vantaris

cd "$VANTARIS"
echo "[1/3] installing deps..."
npm ci 2>/dev/null || npm install

echo "[2/3] building static export (next build -> out/)..."
npm run build
[ -d out ] || { echo "ERROR: build output 'out/' missing"; exit 1; }

echo "[3/3] deploying PREVIEW branch '$BRANCH' (production 'main' untouched)..."
npx wrangler pages deploy out --project-name="$PROJECT" --branch="$BRANCH" --commit-dirty=true

echo
echo "DONE. Preview should be live at: https://${BRANCH}.${PROJECT}.pages.dev"
echo "Play-test /play/blackjack (the window) and /play/dice, then promote to prod when happy."
