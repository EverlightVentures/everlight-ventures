#!/usr/bin/env bash
# secure_seed_cleanup.sh
# Shred every plaintext wallet-seed copy AFTER they are imported into Proton Pass.
# Added 2026-06-02. See memory: reference_crypto_seed_vault.md
#
#   RUN ONLY AFTER you have confirmed the Proton Pass import succeeded:
#     bash 03_AUTOMATION_CORE/01_Scripts/secure_seed_cleanup.sh
#
# Does NOT touch 03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key
# (the trading bot reads that live copy at runtime).
set -euo pipefail

# resolve workspace root (this script lives in 03_AUTOMATION_CORE/01_Scripts/)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

FILES=(
  "03_AUTOMATION_CORE/01_Scripts/atomic_sp.py"
  "03_AUTOMATION_CORE/01_Scripts/Zilpay_Bacardi_Wallet_SP.py"
  "03_AUTOMATION_CORE/01_Scripts/bcardi_coin_sp.py"
  "03_AUTOMATION_CORE/01_Scripts/phantom_sp.py"
  "05_PERSONAL/A_Personal_Notebook/Y_Accounts/Phantom/seed_phrase_phantom.py"
  "05_PERSONAL/00_Documents/Rich_Archive/Y_Accounts/Phantom/seed_phrase_phantom.py"
  "06_DEVELOPMENT/everlightventures/03_AUTOMATION_CORE/01_Scripts/Zilpay_Bacardi_Wallet_SP.py"
  "06_DEVELOPMENT/everlightventures/03_AUTOMATION_CORE/01_Scripts/atomic_sp.py"
  "06_DEVELOPMENT/everlightventures/03_AUTOMATION_CORE/01_Scripts/bcardi_coin_sp.py"
  "06_DEVELOPMENT/everlightventures/03_AUTOMATION_CORE/01_Scripts/phantom_sp.py"
  "08_BACKUPS/sync_conflicts_archive_20260514/contents/05_PERSONAL/A_Personal_Notebook/Y_Accounts/Phantom/seed_phrase_phantom.py"
  "03_AUTOMATION_CORE/03_Credentials/proton_pass_import.json"
)

echo "This will permanently remove ${#FILES[@]} plaintext secret files (incl. the import file)."
echo "ONLY proceed if the Proton Pass import is DONE and verified."
read -rp "Type YES to proceed: " ok
[ "$ok" = "YES" ] || { echo "Aborted. Nothing changed."; exit 1; }

n=0
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    if shred -u "$f" 2>/dev/null; then
      echo "  shredded: $f"
    else
      rm -f "$f" && echo "  removed (shred n/a on FUSE): $f"
    fi
    n=$((n+1))
  fi
done

echo ""
echo "Done -- $n files removed."
echo "WARNING: shred is best-effort on the sdcard FUSE mount (no in-place overwrite),"
echo "and copies may persist in cloud-sync trash / device backups. The only true fix for"
echo "any wallet that holds value is to ROTATE it (move funds to a fresh wallet whose seed"
echo "has never touched a file). Launch new coins from a fresh wallet."
