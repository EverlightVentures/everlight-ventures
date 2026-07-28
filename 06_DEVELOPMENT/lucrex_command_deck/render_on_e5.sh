#!/usr/bin/env bash
# render_on_e5.sh -- render the LUCREX Command Deck on e5 with headless chromium
# and pull screenshots back, so UI changes can be SEEN before shipping (the phone
# proot has no browser). One-time setup on e5 already done: ~/shot has playwright
# + chromium; ~/lucrex_deck_shot runs the deck; tmux session "deckshot" hosts it.
#
# Usage: bash render_on_e5.sh        (sync web/, re-shoot, pull PNGs locally)
# Output: <app>/.shots/deck_wide.png + deck_folded.png (git-ignored scratch)
#
# Pulls use base64-over-ssh (rsync/scp flake over the tailnet from proot).

set -u
APP="/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/lucrex_command_deck"
OUT="$APP/.shots"; mkdir -p "$OUT"
E5="e5"                       # ssh config alias -> 163.192.60.35
PORT=2799

echo "[1/4] sync web/ to e5"
rsync -rltz -e ssh "$APP/web/" "$E5:~/lucrex_deck_shot/web/" >/dev/null 2>&1 || { echo "rsync failed"; exit 1; }

echo "[2/4] ensure deck server up on e5 (:$PORT)"
ssh "$E5" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$PORT/ | grep -q 200 || (tmux kill-session -t deckshot 2>/dev/null; tmux new-session -d -s deckshot 'cd ~/lucrex_deck_shot && SHELL_CLAUDE=/bin/bash EV_BIND=127.0.0.1 python3 blubber_server.py $PORT >/tmp/deck$PORT.log 2>&1'; sleep 2)" >/dev/null 2>&1

echo "[3/4] screenshot (wide + folded)"
ssh "$E5" 'cd ~/shot && node shot.js 2>&1 | grep -iE "done|err|fatal"' 2>&1 | sed 's/^/    /'

echo "[4/4] pull PNGs via base64-over-ssh"
for name in deck_wide deck_folded; do
  ssh -o ConnectTimeout=12 "$E5" "base64 -w0 ~/shot/$name.png" > "$OUT/$name.b64" 2>/dev/null
  base64 -d "$OUT/$name.b64" > "$OUT/$name.png" 2>/dev/null && rm -f "$OUT/$name.b64" \
    && echo "    $OUT/$name.png ($(stat -c%s "$OUT/$name.png") b)" || echo "    FAILED $name"
done
echo "done. View the PNGs (they auto-resize on Read)."
