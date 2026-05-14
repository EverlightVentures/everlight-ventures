#!/usr/bin/env bash
# gen_stignore.sh -- Regenerate .stignore so Syncthing ignores every git-tracked
# file. Git owns tracked content (via GitHub); Syncthing carries ONLY untracked
# data. Two tools, zero overlap, zero conflicts.
#
# Run this whenever a meaningful batch of new files gets git-committed.
# Safe to run anytime -- it's deterministic.

set -euo pipefail
ROOT=/mnt/sdcard/AA_MY_DRIVE
cd "$ROOT"

OUT="$ROOT/.stignore"
TMP="$(mktemp)"

{
  echo "// Syncthing ignore file -- AUTO-GENERATED $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "// by 03_AUTOMATION_CORE/01_Scripts/gen_stignore.sh"
  echo "//"
  echo "// ARCHITECTURE: git owns version-controlled files (synced via GitHub)."
  echo "// Syncthing carries ONLY untracked data (_logs, owner_downloads, Blinko"
  echo "// DB, deal audit, parsed leads, caches of real value). The two never"
  echo "// touch the same file -> no sync-conflict storms."
  echo "//"
  echo "// Regenerate after large git commits:  bash 03_AUTOMATION_CORE/01_Scripts/gen_stignore.sh"
  echo ""
  echo "// ---- hard excludes (never sync, either tool) ----"
  echo ".git"
  echo "**/.git"
  echo "node_modules"
  echo "**/node_modules"
  echo "__pycache__"
  echo "**/__pycache__"
  echo "*.pyc"
  echo ".cache"
  echo "**/.cache"
  echo "*.tmp"
  echo "*.swp"
  echo "~syncthing~*"
  echo "(?d).sync-conflict-*"
  echo "_sync_conflicts_quarantine_20260513"
  echo "_logs/syncthing_config"
  echo "open_webui_pkgs"
  echo "**/open_webui_pkgs"
  echo "open_webui_venv"
  echo "**/open_webui_venv"
  echo "*.venv"
  echo "**/Library/PackageCache"
  echo "**/Library/Bee"
  echo "**/Library/Artifacts"
  echo "**/Library/ShaderCache"
  echo "**/[Tt]emp"
  echo ""
  echo "// ---- git-tracked files: git owns these, Syncthing must skip them ----"
  echo "// ($(git ls-files | wc -l) entries as of generation)"
  git -c core.quotePath=false ls-files | sed 's|^|/|'
} > "$TMP"

mv "$TMP" "$OUT"
echo "wrote $OUT ($(wc -l < "$OUT") lines, $(git ls-files | wc -l) tracked-file entries)"
