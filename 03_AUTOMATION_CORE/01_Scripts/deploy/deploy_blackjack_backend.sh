#!/usr/bin/env bash
# ============================================================================
# deploy_blackjack_backend.sh -- one-shot deploy of the blackjack server pieces
# that the new features (B-Card jackpot stat, single-player leaderboard feed,
# Pro Coaching AI dealer) depend on. Backend only -- invisible to public users
# until the frontend flags are flipped + redeployed (see TEST/GO-LIVE below).
#
# USAGE (needs a VALID Supabase Management token from Proton Pass):
#   SUPABASE_ACCESS_TOKEN=sbp_xxxxx bash deploy_blackjack_backend.sh
#
# Run from the phone (has the supabase CLI) at repo root, OR from e5.
# ============================================================================
set -uo pipefail
REF="jdqqmsmwmbsnlnstyavl"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"   # -> /mnt/sdcard/AA_MY_DRIVE
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

if [ -z "${SUPABASE_ACCESS_TOKEN:-}" ]; then
  echo "ERROR: export SUPABASE_ACCESS_TOKEN=<valid sbp_ token from Proton Pass> first."
  exit 1
fi

echo "==> 1/3  Applying migrations via Management API (idempotent DDL)"
for mig in "20260607_blackjack_leaderboard.sql" "20260607_coaching_pass.sql"; do
  f="$ROOT/supabase/migrations/$mig"
  [ -f "$f" ] || { echo "  skip (missing): $mig"; continue; }
  python3 - "$f" <<'PY'
import sys, json, urllib.request, os
sql=open(sys.argv[1]).read()
tok=os.environ["SUPABASE_ACCESS_TOKEN"]; ref="jdqqmsmwmbsnlnstyavl"
ua="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
req=urllib.request.Request(f"https://api.supabase.com/v1/projects/{ref}/database/query",
  data=json.dumps({"query":sql}).encode(),
  headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json","User-Agent":ua,"Accept":"application/json"},
  method="POST")
try:
  r=urllib.request.urlopen(req,timeout=45); print("   OK", os.path.basename(sys.argv[1]), r.status)
except urllib.error.HTTPError as e:
  print("   FAIL", os.path.basename(sys.argv[1]), e.code, e.read()[:200].decode(errors="ignore")); sys.exit(1)
PY
done

echo "==> 2/3  Deploying the blackjack-api edge function (dealer-ai, buy-coaching-pass, jackpots_won, stats_only)"
cd "$ROOT"
supabase functions deploy blackjack-api --project-ref "$REF" --no-verify-jwt || {
  echo "  edge deploy failed -- check the token + that the supabase CLI is installed."; exit 1; }

echo "==> 3/3  Sanity: confirm PERPLEXITY_API_KEY is set on the project (Pro Coaching needs it)"
supabase secrets list --project-ref "$REF" 2>/dev/null | grep -qi PERPLEXITY \
  && echo "   OK PERPLEXITY_API_KEY present" \
  || echo "   WARN: PERPLEXITY_API_KEY not found -- set it: supabase secrets set PERPLEXITY_API_KEY=... --project-ref $REF"

cat <<'NEXT'

==> BACKEND DEPLOYED (public site UNCHANGED -- frontend flags still off).

TEST (private preview): flip these to true, then build+deploy frontend to the
bj-finish-preview branch (NOT the public site):
  - 06_DEVELOPMENT/vantaris/src/components/blackjack/DealerChat.tsx : PRO_COACHING_ENABLED = true
  - 06_DEVELOPMENT/vantaris/src/app/play/blackjack/page.tsx        : LEADERBOARD_SP_FEED = true

GO LIVE (after Rich approves): keep the flags true and deploy frontend to bj-finish (public).
NEXT
echo "done."
