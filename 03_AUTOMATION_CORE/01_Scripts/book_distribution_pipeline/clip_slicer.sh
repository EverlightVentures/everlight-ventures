#!/usr/bin/env bash
# clip_slicer.sh -- Beyond the Veil social clip generator
# Takes a master audio WAV and slices into 60-90s social clips with chapter markers
#
# Dependencies: ffmpeg, ffprobe
# Usage: ./clip_slicer.sh <master_audio.wav> <chapters_file.txt> [output_dir]
#
# chapters_file.txt format (one per line):
#   HH:MM:SS  Chapter Title or social hook text
#   00:00:00  Nobody saw it coming
#   00:12:34  The call that changed everything
#   00:28:01  She knew the truth

set -euo pipefail

MASTER="${1:-}"
CHAPTERS_FILE="${2:-}"
OUTPUT_DIR="${3:-./social_clips}"
CLIP_DURATION=75  # seconds (adjustable 60-90)

# Validation
if [[ -z "$MASTER" || -z "$CHAPTERS_FILE" ]]; then
  echo "Usage: $0 <master_audio.wav> <chapters_file.txt> [output_dir]"
  exit 1
fi

if ! command -v ffmpeg &>/dev/null; then
  echo "ERROR: ffmpeg not found. Install with: apt install ffmpeg"
  exit 1
fi

if [[ ! -f "$MASTER" ]]; then
  echo "ERROR: Master file not found: $MASTER"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "=== Beyond the Veil Clip Slicer ==="
echo "Master: $MASTER"
echo "Output: $OUTPUT_DIR"
echo "Clip duration: ${CLIP_DURATION}s"
echo ""

CLIP_NUM=1

while IFS=$'\t ' read -r TIMESTAMP TITLE_REST || [[ -n "$TIMESTAMP" ]]; do
  # Skip empty lines and comments
  [[ -z "$TIMESTAMP" || "$TIMESTAMP" == \#* ]] && continue

  TITLE=$(echo "$TITLE_REST" | sed 's/[^a-zA-Z0-9 _-]//g' | tr ' ' '_' | cut -c1-40)
  START_SECONDS=$(echo "$TIMESTAMP" | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')

  PADDED=$(printf "%02d" "$CLIP_NUM")
  OUTFILE="${OUTPUT_DIR}/clip_${PADDED}_${TITLE}.wav"

  echo "Slicing clip $PADDED: [$TIMESTAMP] $TITLE_REST"

  ffmpeg -y \
    -ss "$START_SECONDS" \
    -i "$MASTER" \
    -t "$CLIP_DURATION" \
    -af "afade=t=in:st=0:d=0.3,afade=t=out:st=$((CLIP_DURATION - 2)):d=2" \
    -ar 44100 \
    -ac 1 \
    -c:a pcm_s16le \
    "$OUTFILE" \
    2>/dev/null

  if [[ -f "$OUTFILE" ]]; then
    SIZE=$(du -sh "$OUTFILE" | cut -f1)
    echo "  -> $OUTFILE ($SIZE)"
  else
    echo "  -> ERROR: clip not created"
  fi

  CLIP_NUM=$((CLIP_NUM + 1))

done < "$CHAPTERS_FILE"

echo ""
echo "Done. $((CLIP_NUM - 1)) clips created in $OUTPUT_DIR"
echo "Next: Add subtitles with subtitle_burner.py before posting to TikTok/Reels"
