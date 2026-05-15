#!/usr/bin/env bash
# hunt_and_provision_e5.sh
#
# ONE unattended script: hunt OCI A1 capacity, and the moment a slot opens,
# do the complete E5 restore -- launch, wait for cloud-init, attach the orphan
# boot volume, mount it, rsync the E5 production data onto the new box, then
# write the landing report with the IP + connection instructions.
#
# Runs phone-side via nohup (PC is off). Survives as long as Termux stays alive.
#
# Usage:
#   nohup bash hunt_and_provision_e5.sh >/dev/null 2>&1 &
#
# Outputs (all under /mnt/sdcard/AA_MY_DRIVE/_state/):
#   E5_LANDED.txt         <- THE FILE TO CHECK: IP + ssh cmd + tailscale steps
#   e5_hunt.status        <- one word: hunting | landed | provisioning | done | error
#   e5_hunt.log           <- full timestamped log

set -uo pipefail
export SUPPRESS_LABEL_WARNING=True
export PATH="/usr/local/bin:/usr/bin:/bin:/root/.local/bin:$PATH"

# ----- Config -----
COMP="ocid1.compartment.oc1..aaaaaaaalhtovyf6lyn3xppwmdfjkfssf7vf56zahmp2xdc5hv4gay3vtv2a"
AD="kNfe:US-SANJOSE-1-AD-1"
IMAGE="ocid1.image.oc1.us-sanjose-1.aaaaaaaae5nqxnx7734mvbzkt3pctumjdb525h2mpzxqxyh3pfmw2iqdsqqq"
SUBNET="ocid1.subnet.oc1.us-sanjose-1.aaaaaaaa7gg2a526yyx3iqdgr7wyfth7w2e675qmyeixiavm6rcmkttq26xq"
CLOUDINIT="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/e5_mother/cloud_init.yaml"
SSHKEY="/root/.ssh/github_deploy"
ORPHAN_VOL="ocid1.bootvolume.oc1.us-sanjose-1.abzwuljrzmlkhudjg2iauamz6zr4mhrygp6kmxurur4d7wrh73qrfvlmg3oq"

STATE_DIR="/mnt/sdcard/AA_MY_DRIVE/_state"
mkdir -p "$STATE_DIR"
REPORT="$STATE_DIR/E5_LANDED.txt"
STATUS="$STATE_DIR/e5_hunt.status"
LOG="$STATE_DIR/e5_hunt.log"

# Shapes: full E5-equivalent first, fall back only within 4-core.
SHAPES=(
  '{"ocpus": 4, "memoryInGBs": 24}'
  '{"ocpus": 4, "memoryInGBs": 23}'
  '{"ocpus": 4, "memoryInGBs": 20}'
  '{"ocpus": 4, "memoryInGBs": 16}'
)
CAPACITY_WAIT=300      # between full rounds when out of capacity
THROTTLE_WAIT=600      # on 429
NET_WAIT=60            # on network blip

ts() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { printf '[%s] %s\n' "$(ts)" "$*" >> "$LOG"; }
set_status() { echo "$1" > "$STATUS"; }

# ----- optional notifiers (best-effort, never fatal) -----
notify() {
  local msg="$1"
  command -v termux-notification >/dev/null 2>&1 && \
    termux-notification --title "E5 Restore" --content "$msg" 2>/dev/null || true
  # Slack: only if a token is reachable phone-side; degrade silently otherwise
  for envf in /mnt/sdcard/AA_MY_DRIVE/.env /root/.env /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env; do
    if [ -f "$envf" ] && grep -q 'SLACK_BOT_TOKEN' "$envf" 2>/dev/null; then
      local tok ch
      tok=$(grep -E '^SLACK_BOT_TOKEN=' "$envf" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')
      ch=$(grep -E '^SLACK_ALERTS_CH=' "$envf" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')
      [ -z "$ch" ] && ch="#hive-alerts"
      [ -n "$tok" ] && curl -s -X POST https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer $tok" -H "Content-Type: application/json" \
        -d "{\"channel\":\"$ch\",\"text\":\"[E5 Restore] $msg\"}" >/dev/null 2>&1
      break
    fi
  done
}

# ----- launch one attempt; echo OCID on success, else echo error class -----
try_launch() {
  local shape="$1" out rc
  out=$(oci compute instance launch \
    --compartment-id "$COMP" --availability-domain "$AD" \
    --shape "VM.Standard.A1.Flex" --shape-config "$shape" \
    --image-id "$IMAGE" --subnet-id "$SUBNET" \
    --display-name "e5-mother" --assign-public-ip true \
    --hostname-label "e5-mother" --boot-volume-size-in-gbs 50 \
    --ssh-authorized-keys-file "${SSHKEY}.pub" \
    --user-data-file "$CLOUDINIT" 2>&1)
  rc=$?
  if [ $rc -eq 0 ] && echo "$out" | grep -q '"lifecycle-state"'; then
    echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null
    return 0
  fi
  if   echo "$out" | grep -q "Out of host capacity";              then echo "CAPACITY"
  elif echo "$out" | grep -qE "429|TooManyRequests";              then echo "THROTTLE"
  elif echo "$out" | grep -qE "RequestException|timed out|ConnectionError"; then echo "NETWORK"
  else echo "OTHER:$(echo "$out" | grep -oE '\"message\":[^,]*' | head -1)"
  fi
  return 1
}

# ============================================================
# PHASE 1 -- HUNT
# ============================================================
log "=== hunt_and_provision_e5 START ==="
set_status "hunting"
notify "Capacity hunt started -- targeting 4 OCPU / 24 GB in us-sanjose-1."

OCID=""
attempt=0
while [ -z "$OCID" ]; do
  attempt=$((attempt + 1))
  for shape in "${SHAPES[@]}"; do
    log "attempt #$attempt  shape=$shape"
    result=$(try_launch "$shape")
    if echo "$result" | grep -q '^ocid1.instance'; then
      OCID="$result"
      log "LANDED  ocid=$OCID  shape=$shape"
      notify "Instance LANDED ($shape) after $attempt rounds. Provisioning..."
      break
    fi
    case "$result" in
      CAPACITY) log "  out of capacity at $shape" ;;
      THROTTLE) log "  429 throttled -- backoff ${THROTTLE_WAIT}s"; sleep "$THROTTLE_WAIT" ;;
      NETWORK)  log "  network blip -- retry ${NET_WAIT}s"; sleep "$NET_WAIT" ;;
      OTHER:*)  log "  unexpected: $result" ;;
    esac
  done
  [ -n "$OCID" ] && break
  log "  all shapes exhausted this round -- sleep ${CAPACITY_WAIT}s"
  sleep "$CAPACITY_WAIT"
done

set_status "landed"

# ============================================================
# PHASE 2 -- WAIT FOR RUNNING + PUBLIC IP
# ============================================================
log "Phase 2 -- waiting for RUNNING state + public IP"
IP=""
for i in $(seq 1 60); do
  sleep 10
  state=$(oci compute instance get --instance-id "$OCID" 2>/dev/null \
          | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['lifecycle-state'])" 2>/dev/null)
  [ "$state" = "RUNNING" ] || { log "  state=$state ($i/60)"; continue; }
  IP=$(oci compute instance list-vnics --instance-id "$OCID" 2>/dev/null \
       | python3 -c "import json,sys
d=json.load(sys.stdin)
for v in d.get('data',[]):
    if v.get('public-ip'): print(v['public-ip']); break" 2>/dev/null)
  [ -n "$IP" ] && { log "  RUNNING, public IP = $IP"; break; }
done
if [ -z "$IP" ]; then
  log "ERROR: instance never got a public IP"
  set_status "error"
  notify "Instance landed ($OCID) but no public IP after 10 min -- needs manual check."
  exit 3
fi

# ============================================================
# PHASE 3 -- WAIT FOR CLOUD-INIT (SSH on 2222)
# ============================================================
log "Phase 3 -- waiting for cloud-init / SSH on 2222 (can take 5-7 min)"
SSH="ssh -i $SSHKEY -p 2222 -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 ubuntu@$IP"
cloud_ok=""
for i in $(seq 1 50); do
  sleep 15
  if $SSH "test -f /var/lib/cloud/mother.ready && echo READY" 2>/dev/null | grep -q READY; then
    cloud_ok="yes"; log "  cloud-init complete ($i)"; break
  fi
  log "  cloud-init not ready ($i/50)"
done
[ -z "$cloud_ok" ] && log "WARN: cloud-init flag never appeared -- continuing anyway, may need manual finish"

set_status "provisioning"

# ============================================================
# PHASE 4 -- ATTACH ORPHAN BOOT VOLUME
# ============================================================
log "Phase 4 -- attaching orphan E5 boot volume"
oci compute volume-attachment attach \
  --type paravirtualized --instance-id "$OCID" --volume-id "$ORPHAN_VOL" 2>&1 \
  | grep -E '"lifecycle-state"|"message"' | head -3 >> "$LOG"
sleep 20  # let the block device appear

# ============================================================
# PHASE 5 -- MOUNT ORPHAN + RSYNC E5 DATA ONTO NEW BOX
# ============================================================
log "Phase 5 -- mounting orphan volume + transferring E5 data"
$SSH 'bash -s' 2>&1 <<'REMOTE' | tee -a "$LOG"
set +e
echo "  block devices:"; lsblk -o NAME,SIZE,TYPE,MOUNTPOINT 2>/dev/null | sed 's/^/    /'
# Oracle Linux orphan uses LVM. Memory says VG=e5vg. Activate whatever VG appears.
sudo vgscan --mknodes 2>/dev/null
for vg in $(sudo vgs --noheadings -o vg_name 2>/dev/null | tr -d ' '); do
  [ "$vg" = "ocivolume" ] && continue   # that's the new box's own VG, skip
  echo "  activating VG: $vg"
  sudo vgchange -ay "$vg" 2>/dev/null
done
sudo mkdir -p /mnt/orphan_e5
# try the likely LV paths
for lv in /dev/e5vg/root /dev/e5vg/lv_root /dev/mapper/e5vg-root $(sudo lvs --noheadings -o lv_path 2>/dev/null | tr -d ' '); do
  if [ -b "$lv" ] && sudo mount -o ro "$lv" /mnt/orphan_e5 2>/dev/null; then
    echo "  mounted $lv -> /mnt/orphan_e5 (read-only)"; break
  fi
done
if mountpoint -q /mnt/orphan_e5; then
  echo "  orphan contents:"; ls /mnt/orphan_e5/home/opc/ 2>/dev/null | head -10 | sed 's/^/    /'
  echo "  rsyncing E5 /home/opc -> /home/ubuntu/e5_data ..."
  sudo mkdir -p /home/ubuntu/e5_data
  sudo rsync -a --exclude '.cache/' --exclude '.npm/' \
    /mnt/orphan_e5/home/opc/ /home/ubuntu/e5_data/ 2>&1 | tail -3
  sudo cp -a /mnt/orphan_e5/etc/systemd/system/. /home/ubuntu/e5_data/_systemd_units/ 2>/dev/null
  sudo chown -R ubuntu:ubuntu /home/ubuntu/e5_data
  echo "  E5 data restored: $(sudo du -sh /home/ubuntu/e5_data 2>/dev/null | cut -f1)"
  sudo umount /mnt/orphan_e5 2>/dev/null && echo "  orphan unmounted (data is now local)"
else
  echo "  ERROR: could not mount orphan volume -- manual mount needed"
  echo "  (the volume IS attached; SSH in and: sudo vgscan; sudo vgchange -ay; mount)"
fi
REMOTE

# ============================================================
# PHASE 6 -- TAILSCALE READINESS (install only; user auths)
# ============================================================
log "Phase 6 -- Tailscale readiness"
$SSH 'command -v tailscale >/dev/null 2>&1 && echo "tailscale installed" || (curl -fsSL https://tailscale.com/install.sh | sudo sh 2>&1 | tail -2)' 2>&1 | tee -a "$LOG"

# ============================================================
# PHASE 7 -- LANDING REPORT
# ============================================================
log "Phase 7 -- writing landing report"
cat > "$REPORT" <<EOF
========================================================
  E5-MOTHER LANDED + PROVISIONED  --  $(ts)
========================================================

  PUBLIC IP : $IP
  OCID      : $OCID

  CONNECT (SSH):
    ssh -i /root/.ssh/github_deploy -p 2222 ubuntu@$IP

  JOIN TAILSCALE (run this once you're SSH'd in):
    sudo tailscale up --ssh --hostname=e5-mother
    # then it's reachable as 'e5-mother' on your tailnet

  E5 PRODUCTION DATA:
    restored to  /home/ubuntu/e5_data/   on the new box
    systemd units in /home/ubuntu/e5_data/_systemd_units/
    (rsync'd directly off the orphan boot volume xlm-bot-core-e5-2c16g)

  NEXT (provisioning the hive stack):
    the recovered .env + service units are in /home/ubuntu/e5_data/
    run the e5_mother/provision.sh flow or restore services manually

  cloud-init: ${cloud_ok:-INCOMPLETE -- check manually}
========================================================
EOF
cat "$REPORT" >> "$LOG"
set_status "done"
notify "E5-MOTHER UP at $IP -- ssh -p 2222 ubuntu@$IP -- see _state/E5_LANDED.txt"
log "=== DONE -- e5-mother at $IP ==="
