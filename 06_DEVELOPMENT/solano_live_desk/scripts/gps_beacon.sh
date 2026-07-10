#!/data/data/com.termux/files/usr/bin/bash
# Survival OS background GPS beacon.
#
# Posts your live location to the server every minute so proximity alerts fire
# with the console CLOSED (phone in your pocket on a delivery). The server-side
# alert worker then watches your 1.5mi zone 24/7 and pushes via ntfy.
#
# Runs ANDROID-SIDE in Termux (not proot): needs the Termux:API app for
# termux-location. Launch at boot via Termux:Boot; survives on a nohup loop
# because the phone has no crond.
#
# One-time setup (run these in TERMUX, not proot):
#   pkg install termux-api jq -y
#   mkdir -p ~/.termux/boot
#   scp e5:~/solano_live_desk/scripts/gps_beacon.sh ~/.termux/boot/gps_beacon.sh
#   printf 'URL=https://survival.everlightventures.io\nTOKEN=%s\n' \
#     "$(ssh e5 'grep ^SLD_ACCESS_TOKEN ~/solano_live_desk/.env | cut -d= -f2-')" \
#     > ~/.survival_beacon
#   chmod +x ~/.termux/boot/gps_beacon.sh
#   # then disable battery optimization for Termux, and reboot (or run it now).

set -u
CFG="${SURVIVAL_BEACON_CFG:-$HOME/.survival_beacon}"
[ -f "$CFG" ] && . "$CFG"
URL="${URL:-https://survival.everlightventures.io}"
INTERVAL="${INTERVAL:-60}"

if [ -z "${TOKEN:-}" ]; then
  echo "[beacon] no TOKEN. Put URL= and TOKEN= in $CFG (see header)."; exit 1
fi

echo "[beacon] posting GPS to $URL every ${INTERVAL}s"
while true; do
  LOC="$(termux-location -p gps -r once 2>/dev/null)"
  [ -z "$LOC" ] && LOC="$(termux-location -p network -r once 2>/dev/null)"
  LAT="$(printf '%s' "$LOC" | jq -r '.latitude // empty' 2>/dev/null)"
  LON="$(printf '%s' "$LOC" | jq -r '.longitude // empty' 2>/dev/null)"
  if [ -n "$LAT" ] && [ -n "$LON" ]; then
    if curl -s -m 15 -o /dev/null -X POST "$URL/api/location?lat=$LAT&lon=$LON&token=$TOKEN"; then
      echo "[beacon] $(date +%H:%M:%S) posted $LAT,$LON"
    else
      echo "[beacon] $(date +%H:%M:%S) post failed"
    fi
  else
    echo "[beacon] $(date +%H:%M:%S) no GPS fix"
  fi
  sleep "$INTERVAL"
done
