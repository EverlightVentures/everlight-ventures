#!/usr/bin/env bash
# Aggressive A1.Flex 4/24 hunter -- single shape, fast retry.
# Always Free, no PAYG. SJ-only. Hammer LaunchInstance every 90 s.

set -uo pipefail
OCI_BIN="${OCI_BIN:-$HOME/.local/bin/oci}"
OCI_AUTH="--auth security_token --profile DEFAULT"
COMPARTMENT="ocid1.tenancy.oc1..aaaaaaaacm32hkslhfxorfn7jubhjqjffr4roltyjwjrkfcdkup37o7qt4ca"
SUBNET="ocid1.subnet.oc1.us-sanjose-1.aaaaaaaa7gg2a526yyx3iqdgr7wyfth7w2e675qmyeixiavm6rcmkttq26xq"
IMAGE="ocid1.image.oc1.us-sanjose-1.aaaaaaaazhvzqjm54opnv6eu35koucrgahoqfa35sx2qurqx2jkbwi5h7q5a"
AD="kNfe:US-SANJOSE-1-AD-1"
SHAPE="VM.Standard.A1.Flex"
SHAPE_CONFIG='{"ocpus":4,"memoryInGBs":24}'
DISPLAY_NAME="${DISPLAY_NAME:-Everlight-Flex-24}"
SSH_PUB="${SSH_PUB:-$HOME/.ssh/oracle_key.pem.pub}"
STATE="$HOME/.local/state/oci-instance-hunter"
LOG="$STATE/hunter.log"
MARKER="$STATE/.instance_acquired"
COUNTER="$STATE/sj_failed_count"

mkdir -p "$STATE"
log(){ printf "[%s] %s\n" "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" | tee -a "$LOG"; }

[[ -f "$MARKER" ]] && { log "marker present -- exit"; exit 0; }
[[ -x "$OCI_BIN" ]] || { log "no oci"; exit 1; }
[[ -f "$SSH_PUB" ]] || { log "no ssh pubkey at $SSH_PUB"; exit 1; }

if ! $OCI_BIN $OCI_AUTH iam region list --query 'data[0].name' >/dev/null 2>&1; then
  log "AUTH FAIL -- run: oci session authenticate --region us-sanjose-1"; exit 2
fi

N=$(cat "$COUNTER" 2>/dev/null || echo 0)
log "LAUNCH attempt $((N+1)) shape=$SHAPE config=$SHAPE_CONFIG"

OUT=$($OCI_BIN $OCI_AUTH --region us-sanjose-1 compute instance launch \
  --compartment-id "$COMPARTMENT" --availability-domain "$AD" \
  --shape "$SHAPE" --shape-config "$SHAPE_CONFIG" \
  --source-details "{\"sourceType\":\"image\",\"imageId\":\"$IMAGE\"}" \
  --subnet-id "$SUBNET" --assign-public-ip true \
  --display-name "$DISPLAY_NAME" \
  --ssh-authorized-keys-file "$SSH_PUB" \
  --wait-for-state RUNNING --max-wait-seconds 240 \
  --query 'data.{id:"id",state:"lifecycle-state",name:"display-name"}' 2>&1)
RC=$?

if echo "$OUT" | grep -qiE 'Out of host capacity|InternalError.*capacity'; then
  N=$((N+1)); echo "$N" > "$COUNTER"
  log "  -> OUT_OF_CAPACITY (cumulative $N)"
elif (( RC == 0 )) && echo "$OUT" | grep -q 'RUNNING'; then
  log "  -> SUCCESS: $OUT"
  echo "$OUT" > "$MARKER"
  WEBHOOK=$(grep -E '^SLACK_WEBHOOK_URL=' /AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env 2>/dev/null | cut -d= -f2- | tr -d '"')
  [[ -n "$WEBHOOK" ]] && curl -s -X POST -H 'Content-Type: application/json' \
    --data "{\"text\":\"[OCI hunter] LANDED A1.Flex 4/24 after $((N+1)) attempts\"}" "$WEBHOOK" >/dev/null 2>&1
else
  log "  -> ERROR rc=$RC: $(echo "$OUT" | head -2 | tr '\n' ' ')"
fi
