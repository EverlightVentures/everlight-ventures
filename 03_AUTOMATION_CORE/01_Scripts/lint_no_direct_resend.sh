#!/usr/bin/env bash
# lint_no_direct_resend.sh
#
# Pre-commit-style guard: refuse to ship if any Python or TypeScript file
# outside the canonical mailer makes a direct call to api.resend.com.
#
# The ONLY allowed file is content_tools/branded_mailer.py (line ~45,
# the canonical RESEND_URL constant). Everything else must import
# send_branded_email() and go through the gates.
#
# Streubel-4435 backstop -- IRON 3.
# Rich Gee / Justine Park / Amara Osei -- 2026-05-05
#
# Usage:
#   bash 03_AUTOMATION_CORE/01_Scripts/lint_no_direct_resend.sh
#   exit 0 = clean, exit 1 = direct-resend hit found

set -u

ROOT="${LINT_ROOT:-/AA_MY_DRIVE}"
if [ ! -d "$ROOT" ]; then
  ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fi

ALLOWED_FILES_REGEX='content_tools/branded_mailer\.py:'

# Test fixtures may keep direct calls if they explicitly opt out.
FIXTURE_REGEX='# *noqa: *direct-resend'

exclude_dirs=(
  --exclude-dir='.venv'
  --exclude-dir='node_modules'
  --exclude-dir='__pycache__'
  --exclude-dir='.git'
  --exclude-dir='08_BACKUPS'
  --exclude-dir='venv'
  --exclude-dir='env'
  --exclude-dir='.next'
  --exclude-dir='dist'
  --exclude-dir='build'
)

include_globs=(
  --include='*.py'
  --include='*.sh'
  --include='*.js'
  --include='*.ts'
  --include='*.mjs'
  --include='*.cjs'
)

raw_hits="$(grep -rn "${exclude_dirs[@]}" "${include_globs[@]}" 'api\.resend\.com/emails' "$ROOT" 2>/dev/null || true)"

if [ -z "$raw_hits" ]; then
  echo "lint_no_direct_resend: clean -- no direct api.resend.com hits found"
  exit 0
fi

# Filter out the canonical mailer and any explicitly-marked fixtures.
violations="$(echo "$raw_hits" | grep -v -E "$ALLOWED_FILES_REGEX" | while IFS= read -r line; do
  file_part="${line%%:*}"
  if grep -qE "$FIXTURE_REGEX" "$file_part" 2>/dev/null; then
    continue
  fi
  echo "$line"
done)"

if [ -z "$violations" ]; then
  echo "lint_no_direct_resend: clean -- only canonical branded_mailer hit"
  exit 0
fi

count="$(echo "$violations" | grep -c '.' || true)"
echo "lint_no_direct_resend: FAIL -- $count direct api.resend.com call(s) outside branded_mailer:"
echo
echo "$violations"
echo
echo "Fix: import send_branded_email from content_tools/branded_mailer.py"
echo "     so the OUTBOUND_HALT, recipient_class, dnc_registrar, quiet-hours,"
echo "     weekly_cadence, phrase_scrub, resend_guard, and resend_budget gates"
echo "     all fire on every send."
echo
echo "Add '# noqa: direct-resend' on the offending line ONLY for explicit"
echo "test fixtures. Production code must go through the canonical mailer."
exit 1
