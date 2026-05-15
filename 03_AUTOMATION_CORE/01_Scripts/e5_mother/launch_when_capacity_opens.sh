#!/usr/bin/env bash
# launch_when_capacity_opens.sh
#
# Polls OCI for free-tier Ampere capacity and submits the e5-mother launch
# the moment it lands. Tries shapes in descending preference (4/16 first, then
# step down). Stops on success or non-capacity error. Idempotent: if e5-mother
# already exists, exits immediately.
#
# Usage:
#   bash launch_when_capacity_opens.sh               # default: try forever, 120s interval
#   bash launch_when_capacity_opens.sh --max=200     # cap attempts (200 * 120s = ~6.5 hr)
#   bash launch_when_capacity_opens.sh --interval=60 # poll every 60s
#
# Output:
#   STDOUT  per-attempt one-liner
#   STATE   /mnt/sdcard/AA_MY_DRIVE/_state/e5_mother_launch.{status,ocid,ip,log}

set -uo pipefail
export SUPPRESS_LABEL_WARNING=True

# ----- Config -----
COMP="ocid1.compartment.oc1..aaaaaaaalhtovyf6lyn3xppwmdfjkfssf7vf56zahmp2xdc5hv4gay3vtv2a"
AD="kNfe:US-SANJOSE-1-AD-1"
IMAGE="ocid1.image.oc1.us-sanjose-1.aaaaaaaae5nqxnx7734mvbzkt3pctumjdb525h2mpzxqxyh3pfmw2iqdsqqq"
SUBNET="ocid1.subnet.oc1.us-sanjose-1.aaaaaaaa7gg2a526yyx3iqdgr7wyfth7w2e675qmyeixiavm6rcmkttq26xq"
CLOUDINIT="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/e5_mother/cloud_init.yaml"
SSHKEY="/root/.ssh/github_deploy.pub"

STATE_DIR="/mnt/sdcard/AA_MY_DRIVE/_state"
LOG_DIR="/mnt/sdcard/AA_MY_DRIVE/_logs"
mkdir -p "$STATE_DIR" "$LOG_DIR"

STATUS="$STATE_DIR/e5_mother_launch.status"
OCID_FILE="$STATE_DIR/e5_mother_launch.ocid"
IP_FILE="$STATE_DIR/e5_mother_launch.ip"
LOG="$LOG_DIR/e5_mother_launch_$(date +%Y%m%d_%H%M%S).log"

# ----- Args -----
MAX_ATTEMPTS=0     # 0 = unlimited
INTERVAL=120
for arg in "$@"; do
  case "$arg" in
    --max=*)      MAX_ATTEMPTS="${arg#--max=}" ;;
    --interval=*) INTERVAL="${arg#--interval=}" ;;
  esac
done

# ----- Shape preference order (try biggest first) -----
# Paid tier on file 2026-05-14: quota allows full 4 OCPU / 24 GB.
# Lead with the full E5-equivalent shape; fall back only to other 4-core
# variants (24->23 dodges the limit-boundary off-by-one) then 2-core.
# 1-core dropped -- user wants a real box, not a toy instance.
SHAPES=(
  '{"ocpus": 4, "memoryInGBs": 24}'
  '{"ocpus": 4, "memoryInGBs": 23}'
  '{"ocpus": 4, "memoryInGBs": 20}'
  '{"ocpus": 4, "memoryInGBs": 16}'
  '{"ocpus": 2, "memoryInGBs": 12}'
)

ts() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { printf '[%s] %s\n' "$(ts)" "$*" | tee -a "$LOG"; }

# ----- Pre-check: is e5-mother already up? -----
existing="$(oci compute instance list \
              --compartment-id "$COMP" \
              --all 2>/dev/null \
            | python3 -c "
import json,sys
d=json.load(sys.stdin)
for i in d.get('data', []):
    if i.get('display-name') == 'e5-mother' and i.get('lifecycle-state') in ('PROVISIONING','RUNNING'):
        print(i['id'])
        break
" 2>/dev/null)"

if [[ -n "$existing" ]]; then
  echo "$existing" > "$OCID_FILE"
  echo "exists" > "$STATUS"
  log "e5-mother already exists ($existing) -- no relaunch"
  exit 0
fi

# ----- Main loop -----
echo "polling" > "$STATUS"
log "=== launch hunter start  max=$MAX_ATTEMPTS interval=${INTERVAL}s ==="
log "shapes (in order): 4/16 -> 4/12 -> 2/12 -> 2/8 -> 1/6"

attempt=0
while :; do
  attempt=$((attempt + 1))
  [[ "$MAX_ATTEMPTS" -gt 0 && "$attempt" -gt "$MAX_ATTEMPTS" ]] && {
    log "max attempts ($MAX_ATTEMPTS) reached, giving up"
    echo "gave_up" > "$STATUS"
    exit 2
  }

  for shape in "${SHAPES[@]}"; do
    log "attempt #$attempt  shape=$shape"
    result="$(oci compute instance launch \
        --compartment-id "$COMP" \
        --availability-domain "$AD" \
        --shape "VM.Standard.A1.Flex" \
        --shape-config "$shape" \
        --image-id "$IMAGE" \
        --subnet-id "$SUBNET" \
        --display-name "e5-mother" \
        --assign-public-ip true \
        --hostname-label "e5-mother" \
        --boot-volume-size-in-gbs 50 \
        --ssh-authorized-keys-file "$SSHKEY" \
        --user-data-file "$CLOUDINIT" \
        2>&1)"
    rc=$?

    if [[ "$rc" -eq 0 ]] && echo "$result" | grep -q '"lifecycle-state"'; then
      ocid="$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)"
      log "SUCCESS  shape=$shape  ocid=$ocid"
      echo "$ocid" > "$OCID_FILE"
      echo "launched" > "$STATUS"
      # Try to grab the public IP -- may take a minute for VNIC to assign
      for poll in 1 2 3 4 5 6; do
        sleep 10
        ip="$(oci compute instance list-vnics --instance-id "$ocid" 2>/dev/null \
              | python3 -c "import json,sys
d=json.load(sys.stdin)
for v in d.get('data',[]):
    if v.get('public-ip'):
        print(v['public-ip']); break
" 2>/dev/null)"
        if [[ -n "$ip" ]]; then
          echo "$ip" > "$IP_FILE"
          log "  public IP: $ip"
          break
        fi
        log "  (VNIC not ready yet, retry $poll/6)"
      done
      log "=== launch complete -- next: bash provision.sh \$(cat $IP_FILE) ==="
      exit 0
    fi

    if echo "$result" | grep -q "Out of host capacity"; then
      log "  out of capacity at this shape -- trying smaller"
      continue
    fi

    if echo "$result" | grep -q "QuotaExceeded\|LimitExceeded"; then
      log "  QUOTA hit  -- $(echo "$result" | grep -oE '"message"[^,]*' | head -1)"
      echo "quota" > "$STATUS"
      exit 3
    fi

    # Some other error -- log and try next shape
    snippet="$(echo "$result" | tail -3 | head -1)"
    log "  unexpected error: $snippet"
  done

  log "  all shapes exhausted this round, sleeping ${INTERVAL}s"
  sleep "$INTERVAL"
done
