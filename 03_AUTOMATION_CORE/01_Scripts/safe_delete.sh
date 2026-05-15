#!/usr/bin/env bash
# safe_delete.sh -- the verify-before-delete-with-manifest doctrine, scripted.
#
# Every destructive operation on >100 MB of data MUST run through this.
# Per HARD LAW `feedback_verify_before_delete_with_manifest`:
#   1. Emit a manifest of every file path + SHA-256 hash + size + mtime
#   2. Diff against the claimed-canonical tree
#   3. List unique files that would be lost
#   4. Require explicit operator confirmation
#   5. Only THEN delete + write audit-log entry
#
# Usage:
#   safe_delete.sh --target /path/to/delete --canonical /path/to/canonical [--force]
#   safe_delete.sh --target /path/to/delete --canonical-host user@host:/path --remote
#   safe_delete.sh --target /path/to/delete --no-canonical    # for true ephemeral data
#
# Exits 0 on safe delete, 1 on user abort, 2 on diff-found-unique-files.

set -uo pipefail

TARGET=""
CANONICAL=""
REMOTE=""
FORCE=""
NO_CANONICAL=""
SSH_KEY="/root/.ssh/github_deploy"

# --- arg parse ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)         TARGET="$2"; shift 2;;
    --canonical)      CANONICAL="$2"; shift 2;;
    --canonical-host) CANONICAL="$2"; REMOTE="yes"; shift 2;;
    --remote)         REMOTE="yes"; shift;;
    --force)          FORCE="yes"; shift;;
    --no-canonical)   NO_CANONICAL="yes"; shift;;
    -h|--help)
      head -25 "$0" | grep '^#'
      exit 0;;
    *) echo "unknown arg: $1"; exit 1;;
  esac
done

if [[ -z "$TARGET" ]]; then echo "ERROR: --target required"; exit 1; fi
if [[ ! -e "$TARGET" ]]; then echo "ERROR: target $TARGET does not exist"; exit 1; fi
if [[ -z "$CANONICAL" && -z "$NO_CANONICAL" ]]; then
  echo "ERROR: --canonical, --canonical-host, or --no-canonical required"
  echo "       (use --no-canonical ONLY for truly ephemeral data like /tmp builds)"
  exit 1
fi

# --- manifest emission ---
TS="$(date +%Y%m%d_%H%M%S)"
SAFE_TARGET="$(echo "$TARGET" | tr / _)"
MANIFEST_DIR="/mnt/sdcard/AA_MY_DRIVE/_state/safe_delete_manifests"
mkdir -p "$MANIFEST_DIR"
MANIFEST="$MANIFEST_DIR/manifest_${TS}_${SAFE_TARGET}.txt"

echo "=========================================="
echo "  safe_delete.sh"
echo "  target    : $TARGET"
echo "  canonical : ${CANONICAL:-NONE (ephemeral data)}"
echo "  manifest  : $MANIFEST"
echo "=========================================="
echo

# Size + file count before
SIZE_BYTES=$(du -sb "$TARGET" 2>/dev/null | awk '{print $1}')
SIZE_HUMAN=$(du -sh "$TARGET" 2>/dev/null | awk '{print $1}')
FILE_COUNT=$(find "$TARGET" -type f 2>/dev/null | wc -l)
echo "  size  : $SIZE_HUMAN ($SIZE_BYTES bytes)"
echo "  files : $FILE_COUNT"
echo

# Emit manifest
echo "writing manifest..."
{
  echo "# safe_delete.sh manifest"
  echo "# target=$TARGET"
  echo "# canonical=${CANONICAL:-NONE}"
  echo "# timestamp=$(date -Iseconds)"
  echo "# size=$SIZE_BYTES"
  echo "# file_count=$FILE_COUNT"
  echo "# format: SHA256<TAB>SIZE<TAB>MTIME<TAB>PATH"
  find "$TARGET" -type f -print0 2>/dev/null | xargs -0 -P 4 -I{} bash -c '
    h=$(sha256sum "$1" 2>/dev/null | cut -d" " -f1)
    s=$(stat -c "%s" "$1" 2>/dev/null)
    m=$(stat -c "%Y" "$1" 2>/dev/null)
    echo -e "${h}\t${s}\t${m}\t$1"
  ' _ {} 2>/dev/null
} > "$MANIFEST"
echo "  manifest size: $(wc -l < "$MANIFEST") lines"
echo

# --- diff against canonical ---
if [[ -z "$NO_CANONICAL" ]]; then
  echo "diffing against canonical: $CANONICAL"
  DIFF_OUT="$MANIFEST_DIR/diff_${TS}_${SAFE_TARGET}.txt"

  if [[ "$REMOTE" == "yes" ]]; then
    rsync -azn --delete --itemize-changes \
      -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
      "$TARGET/" "$CANONICAL/" > "$DIFF_OUT" 2>&1
  else
    if [[ ! -d "$CANONICAL" ]]; then
      echo "ERROR: canonical $CANONICAL does not exist"
      exit 1
    fi
    diff -rq "$TARGET" "$CANONICAL" > "$DIFF_OUT" 2>&1 || true
  fi

  # parse the diff
  UNIQUE_IN_TARGET=$(grep -E "^(Only in $TARGET|<f)" "$DIFF_OUT" 2>/dev/null | wc -l)
  DIFFERS=$(grep -E "differ$" "$DIFF_OUT" 2>/dev/null | wc -l)

  echo "  diff output : $DIFF_OUT"
  echo "  unique-in-target files (would be LOST): $UNIQUE_IN_TARGET"
  echo "  files that DIFFER between trees       : $DIFFERS"
  echo

  if [[ "$UNIQUE_IN_TARGET" -gt 0 ]]; then
    echo "  ⚠  WARNING: $UNIQUE_IN_TARGET files exist in target but NOT in canonical"
    echo "  first 10 of those:"
    grep -E "^(Only in $TARGET|<f)" "$DIFF_OUT" | head -10 | sed 's/^/    /'
    echo
    if [[ -z "$FORCE" ]]; then
      echo "  ABORTING. Re-run with --force to override, OR copy unique files to canonical first."
      exit 2
    fi
  fi
fi

# --- confirmation prompt ---
if [[ -z "$FORCE" ]]; then
  echo
  read -p "  PROCEED with delete? (type 'yes-delete' to confirm): " CONFIRM
  if [[ "$CONFIRM" != "yes-delete" ]]; then
    echo "  ABORTED by operator"
    exit 1
  fi
fi

# --- the delete ---
echo
echo "  deleting $TARGET ..."
rm -rf "$TARGET"
echo "  done. manifest preserved at: $MANIFEST"

# --- audit log entry ---
AUDIT_LOG="/mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/safe_delete_audit.log"
echo "$(date -Iseconds)|target=$TARGET|size=$SIZE_HUMAN|files=$FILE_COUNT|canonical=${CANONICAL:-NONE}|manifest=$MANIFEST" >> "$AUDIT_LOG"
echo "  logged to: $AUDIT_LOG"
