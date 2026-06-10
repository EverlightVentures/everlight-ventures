#!/bin/bash
# Oracle A1.Flex 4-OCPU/24-GB capacity hammer.
# Runs until a slot lands or 7 days. Persisted via systemd user service.
# Doctrine: feedback_always_free_only.md (90s cadence, SJ-1 AD-1, Always Free).

set -u

# systemd user service has minimal PATH; ensure oci CLI resolves
export PATH="/home/richgee/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

WORKDIR=/AA_MY_DRIVE/_oracle_e5_recovery/2026-05-07
LOG="$WORKDIR/hammer_v2.log"
LANDED_FLAG="$WORKDIR/A1_LANDED.json"
STATE_FILE="$WORKDIR/hammer_state.json"

mkdir -p "$WORKDIR"

# If already landed, exit clean.
if [ -f "$LANDED_FLAG" ]; then
  echo "[$(date -Iseconds)] A1_LANDED flag present, hammer exits. Delete $LANDED_FLAG to re-arm." >> "$LOG"
  exit 0
fi

# Source .env for Slack creds (recovered from dead E5)
ENV_FILE="$WORKDIR/home_opc_critical/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

TEN=ocid1.tenancy.oc1..aaaaaaaacm32hkslhfxorfn7jubhjqjffr4roltyjwjrkfcdkup37o7qt4ca
SUBNET=ocid1.subnet.oc1.us-sanjose-1.aaaaaaaa7gg2a526yyx3iqdgr7wyfth7w2e675qmyeixiavm6rcmkttq26xq
IMAGE=ocid1.image.oc1.us-sanjose-1.aaaaaaaaftv62flimah5zljujj7crzmlxmbkq7e4eciw4f3itd3ylhtneubq
AD="kNfe:US-SANJOSE-1-AD-1"

slack_post() {
  local msg="$1"
  local channel="${SLACK_ALERTS_CH:-#hive-alerts}"
  if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
    curl -s --max-time 10 -X POST https://slack.com/api/chat.postMessage \
      -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
      -H "Content-Type: application/json; charset=utf-8" \
      -d "{\"channel\":\"${channel}\",\"text\":${msg}}" >/dev/null 2>&1 || true
  fi
}

desktop_notify() {
  local title="$1"; local body="$2"
  command -v notify-send >/dev/null 2>&1 && notify-send -u critical "$title" "$body" || true
}

START=$(date +%s)
attempt=0
MAX_HOURS=168  # 7 days

slack_post "\"Oracle A1.Flex hammer started -- targeting 4 OCPU / 24 GB in us-sanjose-1 AD-1, 90s cadence, will run up to 7 days.\""

while true; do
  attempt=$((attempt+1))
  ts=$(date '+%Y-%m-%d %H:%M:%S')

  out=$(oci --profile API_KEY compute instance launch \
    --availability-domain "$AD" \
    --compartment-id "$TEN" \
    --shape "VM.Standard.A1.Flex" \
    --shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
    --image-id "$IMAGE" \
    --subnet-id "$SUBNET" \
    --display-name "everlight-prod-a1" \
    --hostname-label "everlight-prod-a1" \
    --assign-public-ip true \
    --ssh-authorized-keys-file /home/richgee/.ssh/oracle_key.pub \
    --boot-volume-size-in-gbs 50 2>&1)

  if echo "$out" | grep -qE '"lifecycle-state": "(PROVISIONING|RUNNING)"'; then
    INSTANCE_OCID=$(echo "$out" | grep -oP '"id": "ocid1\.instance\.[^"]+' | head -1 | cut -d'"' -f4)
    elapsed=$(( ($(date +%s) - START) / 60 ))
    echo "[$ts] *** SLOT CAUGHT *** attempt=$attempt elapsed=${elapsed}m ocid=$INSTANCE_OCID" >> "$LOG"

    # Wait for RUNNING + capture IP
    sleep 30
    for i in 1 2 3 4 5 6 7 8 9 10; do
      state=$(oci --profile API_KEY compute instance get --instance-id "$INSTANCE_OCID" \
                --query 'data."lifecycle-state"' --raw-output 2>/dev/null)
      [ "$state" = "RUNNING" ] && break
      sleep 15
    done

    A1_IP=$(oci --profile API_KEY compute instance list-vnics --instance-id "$INSTANCE_OCID" \
              --query 'data[0]."public-ip"' --raw-output 2>/dev/null)

    cat > "$LANDED_FLAG" <<EOF
{
  "landed_at": "$(date -Iseconds)",
  "attempt_number": $attempt,
  "elapsed_minutes": $elapsed,
  "instance_ocid": "$INSTANCE_OCID",
  "public_ip": "$A1_IP",
  "shape": "VM.Standard.A1.Flex",
  "ocpus": 4,
  "memory_gb": 24,
  "region": "us-sanjose-1",
  "ad": "$AD"
}
EOF
    echo "[$ts] A1 RUNNING at $A1_IP, flag written" >> "$LOG"

    slack_post "\"*A1.Flex 4 OCPU / 24 GB LANDED.* IP \`$A1_IP\` -- caught on attempt $attempt after ${elapsed} min. Ready to deploy hive stack.\""
    desktop_notify "Oracle A1 LANDED" "$A1_IP -- attempt $attempt, ${elapsed}m elapsed"
    exit 0
  fi

  if echo "$out" | grep -qE 'Out of host capacity|InternalError'; then
    if [ $((attempt % 20)) -eq 0 ]; then
      elapsed=$(( ($(date +%s) - START) / 60 ))
      echo "[$ts] still hammering: attempt=$attempt elapsed=${elapsed}m" >> "$LOG"
    fi
    sleep 180
  elif echo "$out" | grep -qE '"status": 429|TooManyRequests|Too many requests'; then
    elapsed=$(( ($(date +%s) - START) / 60 ))
    echo "[$ts] 429 throttled at attempt=$attempt elapsed=${elapsed}m, backing off 600s" >> "$LOG"
    sleep 600
  elif echo "$out" | grep -qE 'RequestException|connection.*timed out|ConnectTimeout|ReadTimeout|ConnectionError|Max retries exceeded'; then
    elapsed=$(( ($(date +%s) - START) / 60 ))
    echo "[$ts] transient network error at attempt=$attempt elapsed=${elapsed}m, retry in 60s" >> "$LOG"
    sleep 60
  else
    echo "[$ts] non-capacity error attempt=$attempt:" >> "$LOG"
    echo "$out" | tail -10 >> "$LOG"
    slack_post "\"Oracle hammer hit a non-capacity error -- check $LOG. Hammer paused.\""
    exit 1
  fi

  # Hard cap at 7 days
  elapsed_h=$(( ($(date +%s) - START) / 3600 ))
  if [ "$elapsed_h" -ge "$MAX_HOURS" ]; then
    echo "[$ts] 7-day cap reached, exiting" >> "$LOG"
    slack_post "\"Oracle hammer hit 7-day cap without landing A1. Manual intervention recommended.\""
    exit 2
  fi
done
