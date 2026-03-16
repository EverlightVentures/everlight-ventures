#!/bin/bash
# Staging Purge -- archives old files from 07_STAGING/Review/
#
# Usage:
#   bash staging_purge.sh --dry-run   # show what would move
#   bash staging_purge.sh             # actually move files

STAGING="/mnt/sdcard/AA_MY_DRIVE/07_STAGING/Review"
ARCHIVE="/mnt/sdcard/AA_MY_DRIVE/D_Backups/staging_archive"
DRY_RUN=false

[ "$1" = "--dry-run" ] && DRY_RUN=true

if [ ! -d "$STAGING" ]; then
    echo "Staging dir not found: $STAGING"
    exit 1
fi

FILE_COUNT=$(find "$STAGING" -maxdepth 1 -type f | wc -l)
if [ "$FILE_COUNT" = "0" ]; then
    echo "Staging is clean -- nothing to archive."
    exit 0
fi

echo "Found $FILE_COUNT file(s) in staging:"
find "$STAGING" -maxdepth 1 -type f -exec ls -lh {} \;
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] Would archive $FILE_COUNT files to:"
    echo "  $ARCHIVE/$(date +%Y%m%d)/"
    exit 0
fi

DEST="$ARCHIVE/$(date +%Y%m%d)"
mkdir -p "$DEST"

MOVED=0
find "$STAGING" -maxdepth 1 -type f | while read -r f; do
    mv "$f" "$DEST/"
    echo "  Moved: $(basename "$f")"
    MOVED=$((MOVED + 1))
done

echo ""
echo "Archived $FILE_COUNT file(s) to $DEST/"
echo "Staging is now clean."
