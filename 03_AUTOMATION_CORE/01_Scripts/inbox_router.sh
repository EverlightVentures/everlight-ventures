#!/bin/bash
# Inbox Auto-Router -- sorts files from 07_STAGING/Inbox to proper locations
#
# Usage:
#   bash inbox_router.sh --dry-run   # show what would happen
#   bash inbox_router.sh             # actually route files
#
# Routing rules:
#   *.py, *.sh, *.js    -> 03_AUTOMATION_CORE/01_Scripts/
#   *.md, *.txt          -> 07_STAGING/Review/
#   *.json, *.yaml       -> 03_AUTOMATION_CORE/02_Config/
#   *.csv, *.xlsx        -> 09_DASHBOARD/data/
#   *.pdf                -> 05_PERSONAL/Documents/
#   *.jpg, *.png, *.mp4  -> 04_MEDIA_LIBRARY/
#   *.docx               -> 07_STAGING/Review/
#   *                    -> 07_STAGING/Review/ (fallback)

BASE="/mnt/sdcard/AA_MY_DRIVE"
INBOX="$BASE/07_STAGING/Inbox"
DRY_RUN=false

[ "$1" = "--dry-run" ] && DRY_RUN=true

if [ ! -d "$INBOX" ]; then
    echo "Inbox not found: $INBOX"
    exit 1
fi

FILE_COUNT=$(find "$INBOX" -maxdepth 1 -type f 2>/dev/null | wc -l)
if [ "$FILE_COUNT" = "0" ]; then
    echo "Inbox is empty -- nothing to route."
    exit 0
fi

echo "Found $FILE_COUNT file(s) in inbox:"

route_file() {
    local file="$1"
    local name=$(basename "$file")
    local ext="${name##*.}"
    local dest=""

    case "$ext" in
        py|sh|js|ts)
            dest="$BASE/03_AUTOMATION_CORE/01_Scripts/"
            ;;
        json|yaml|yml|toml)
            dest="$BASE/03_AUTOMATION_CORE/02_Config/"
            ;;
        csv|xlsx|xls)
            dest="$BASE/09_DASHBOARD/data/"
            ;;
        pdf)
            dest="$BASE/05_PERSONAL/Documents/"
            ;;
        jpg|jpeg|png|gif|svg|mp4|mov|mp3|wav)
            dest="$BASE/04_MEDIA_LIBRARY/"
            ;;
        md|txt|docx|doc)
            dest="$BASE/07_STAGING/Review/"
            ;;
        *)
            dest="$BASE/07_STAGING/Review/"
            ;;
    esac

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY] $name -> $dest"
    else
        mkdir -p "$dest"
        mv "$file" "$dest"
        echo "  Routed: $name -> $dest"
    fi
}

find "$INBOX" -maxdepth 1 -type f | while read -r f; do
    route_file "$f"
done

echo ""
if [ "$DRY_RUN" = true ]; then
    echo "[DRY RUN] No files were moved."
else
    echo "Routing complete."
fi
