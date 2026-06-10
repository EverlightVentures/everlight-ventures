#!/usr/bin/env bash
# blinko_mirror.sh - Nightly export of all Blinko notes to markdown mirror.
#
# Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/04_Self_Hosting_and_Offline_AI/how_to_build_a_private_ai_secondbrain.txt
#
# Ensures Blinko (running on Oracle E5) has a local markdown backup that survives
# service death or accidental deletion. 30 rolling daily snapshots + monthly archive.
#
# Install on Oracle: crontab entry
#   0 3 * * * /home/opc/hive_scripts/blinko_mirror.sh

set -euo pipefail

BLINKO_URL="${BLINKO_URL:-http://127.0.0.1:1111}"

if [ -d "/mnt/sdcard/AA_MY_DRIVE" ] && [ -w "/mnt/sdcard/AA_MY_DRIVE" ]; then
  MIRROR_ROOT="/mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/blinko_mirror"
elif [ -d "/home/opc" ] && [ -w "/home/opc" ]; then
  MIRROR_ROOT="/home/opc/hive_reports/blinko_mirror"
else
  MIRROR_ROOT="/tmp/blinko_mirror"
fi

DATE_STAMP="$(date -u +%Y-%m-%d)"
MONTH_STAMP="$(date -u +%Y-%m)"
DAILY_DIR="$MIRROR_ROOT/daily/$DATE_STAMP"
MONTHLY_DIR="$MIRROR_ROOT/monthly/$MONTH_STAMP"

mkdir -p "$DAILY_DIR" "$MONTHLY_DIR"

echo "[blinko_mirror] $DATE_STAMP - starting (root=$MIRROR_ROOT)"

# Delegate the whole fetch+write loop to Python so we do not fight heredoc quoting.
python3 - "$BLINKO_URL" "$DAILY_DIR" <<'PYEOF'
import json, sys, os, urllib.request, urllib.error

blinko_url, daily_dir = sys.argv[1], sys.argv[2]
total = 0
page = 1
SIZE = 100
SAFETY = 50  # max 50 pages = 5000 notes

while page <= SAFETY:
    body = json.dumps({"page": page, "size": SIZE, "searchText": ""}).encode()
    req = urllib.request.Request(
        f"{blinko_url}/api/v1/note/list",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw, strict=False)  # tolerate control chars in string values
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[warn] page {page} failed: {e}", file=sys.stderr)
        break
    items = data.get("items") or []
    if not items:
        break
    for note in items:
        nid = str(note.get("id") or f"unknown_{total}")[:16].replace("/", "_")
        content = note.get("content", "") or ""
        tags = note.get("tags", "") or ""
        created = note.get("created_at", "") or ""
        updated = note.get("updated_at", "") or ""
        md = (
            "---\n"
            f"id: {nid}\n"
            f"created: {created}\n"
            f"updated: {updated}\n"
            f"tags: {tags}\n"
            "---\n\n"
            f"{content}\n"
        )
        out_path = os.path.join(daily_dir, f"{nid}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
        total += 1
    if len(items) < SIZE:
        break
    page += 1

print(f"[blinko_mirror] wrote {total} notes to {daily_dir}")
PYEOF

COUNT=$(ls "$DAILY_DIR" 2>/dev/null | wc -l | tr -d ' ')

# Snapshot into monthly archive
if [ "$COUNT" -gt 0 ]; then
  tar -czf "$MONTHLY_DIR/$DATE_STAMP.tar.gz" -C "$DAILY_DIR" . 2>/dev/null || true
fi

# Rotate: keep last 30 daily dirs + last 12 monthly dirs
find "$MIRROR_ROOT/daily" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true
find "$MIRROR_ROOT/monthly" -mindepth 1 -maxdepth 1 -type d -mtime +370 -exec rm -rf {} \; 2>/dev/null || true

# Log entry
echo "{\"date\": \"$DATE_STAMP\", \"notes_mirrored\": $COUNT, \"daily_dir\": \"$DAILY_DIR\"}" \
  >> "$MIRROR_ROOT/mirror.log"

echo "[blinko_mirror] $DATE_STAMP - done ($COUNT notes)"
