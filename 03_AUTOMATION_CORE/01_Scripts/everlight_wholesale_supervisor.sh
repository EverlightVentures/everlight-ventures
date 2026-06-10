#!/usr/bin/env bash
# everlight_wholesale_supervisor.sh -- keep the Next.js production server on :3011.
# Triggers `next build` when the workspace code is newer than .next/BUILD_ID.

set -u

LOG=/mnt/sdcard/AA_MY_DRIVE/_logs/everlight_wholesale.log
PIDFILE=/tmp/everlight_wholesale.pid
NATIVE=/root/everlight_wholesale
SRC=/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_wholesale
mkdir -p "$(dirname "$LOG")"

stamp() { date -Iseconds; }

is_healthy() {
  local code
  code=$(curl -sS --max-time 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:3011/ 2>/dev/null)
  [ "$code" = "200" ]
}

running_pid() {
  pgrep -f 'node.*next/dist/bin/next start' 2>/dev/null | head -1
}

# Fast path: healthy + running -> done.
if pid=$(running_pid) && [ -n "$pid" ] && is_healthy; then
  exit 0
fi

# Sync code delta from workspace to native FS
SYNCED=0
for d in app components lib; do
  if [ -d "$SRC/$d" ]; then
    before=$(find "$NATIVE/$d" -type f -newer "$NATIVE/.next/BUILD_ID" 2>/dev/null | wc -l)
    cp -r --update "$SRC/$d"/. "$NATIVE/$d"/ 2>/dev/null
    after=$(find "$NATIVE/$d" -type f -newer "$NATIVE/.next/BUILD_ID" 2>/dev/null | wc -l)
    [ "$after" -gt "$before" ] && SYNCED=1
  fi
done
for f in package.json tsconfig.json tailwind.config.ts postcss.config.js next.config.ts next-env.d.ts; do
  [ -f "$SRC/$f" ] && cp --update "$SRC/$f" "$NATIVE/$f"
done

# If we're down OR any code changed since last build, rebuild.
if [ ! -f "$NATIVE/.next/BUILD_ID" ] || [ "$SYNCED" = "1" ]; then
  echo "$(stamp) rebuilding (synced=$SYNCED)" >>"$LOG"
  if pid=$(running_pid); then kill "$pid" 2>/dev/null; sleep 2; fi
  cd "$NATIVE" || exit 1
  /usr/bin/node node_modules/next/dist/bin/next build >>"$LOG" 2>&1 || {
    echo "$(stamp) BUILD FAILED -- see log above" >>"$LOG"
    exit 1
  }
fi

# Start fresh
if pid=$(running_pid); then
  kill "$pid" 2>/dev/null
  sleep 2
fi

echo "$(stamp) starting production server" >>"$LOG"
cd "$NATIVE" || exit 1
nohup /usr/bin/node node_modules/next/dist/bin/next start -p 3011 -H 0.0.0.0 >>"$LOG" 2>&1 &
echo $! > "$PIDFILE"
