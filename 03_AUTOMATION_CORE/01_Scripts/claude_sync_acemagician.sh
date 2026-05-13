#!/usr/bin/env bash
# ============================================================
# claude_sync_acemagician.sh
# Bidirectional sync of workspace .claude/ between phone and AceMagician PC
# over Tailscale.
#
# Scope (sync these):
#   .claude/agents/   .claude/commands/   .claude/hooks/
#   .claude/modes/    .claude/skills/     .claude/memory/
#   .claude/guard/    .claude/settings.json
#   .claude/feedback_*.md   .claude/sync_config.json
#
# Excluded (machine-local, ephemeral, or secret):
#   __pycache__/  projects/  plans/  scheduled_tasks.lock
#   settings.local.json  any *.token *.key *credentials*
#
# Modes:
#   --pull      : PC -> phone, merge (skip files newer on phone)
#   --push      : phone -> PC, merge (skip files newer on PC)
#   --sync      : pull then push (default; safe two-way reconcile)
#   --diff      : dry-run, show what would change in either direction
#   --notepad   : push the whole NOTEPAD/ tree (transcripts library) to PC
#   --full      : --sync (Claude doctrine) + --notepad (transcripts)
#   --mirror-from-pc : DESTRUCTIVE, PC wins, phone overwritten
#   --mirror-to-pc   : DESTRUCTIVE, phone wins, PC overwritten
#   --status    : ping PC, no transfer
#
# Conflict policy (default --sync):
#   newer mtime wins (rsync --update). When both sides edited the same
#   file, the older copy is preserved at .sync_conflicts/<timestamp>/
#   on the receiving side.
# ============================================================

set -euo pipefail

# ---------------- config ----------------
PC_USER="richgee"
PC_HOST="100.93.253.49"             # Tailnet IP
PC_HOST_NAME="acemagician-pc.tailfeeb43.ts.net"
PC_KEY="/root/.ssh/phone_to_arch"
PC_WORKSPACE="/home/richgee/AA_MY_DRIVE"

PHONE_WORKSPACE="/mnt/sdcard/AA_MY_DRIVE"
PHONE_CLAUDE="${PHONE_WORKSPACE}/.claude"

# PC's *active* Claude config is in the GLOBAL ~/.claude/ (94 agents live there
# and that's what `claude` on the PC actually reads). The PC's workspace
# ~/AA_MY_DRIVE/.claude/ is mostly cache + plugins + credentials. So the sync
# target on the PC is the global dir.
PC_CLAUDE="/home/${PC_USER}/.claude"

LOG_DIR="${PHONE_WORKSPACE}/03_AUTOMATION_CORE/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/claude_sync_$(date -u +%Y%m%d).log"
QUEUE_FILE="${LOG_DIR}/claude_sync_queue.flag"

# Everlight gold theme
GOLD='\033[38;5;214m'; GREEN='\033[0;32m'; RED='\033[0;31m'
DIM='\033[2m'; RESET='\033[0m'

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log()  { printf "${GOLD}[ev]${RESET}  %s\n" "$*" | tee -a "$LOG_FILE" >&2; }
ok()   { printf "${GREEN}[ok]${RESET}  %s\n" "$*" | tee -a "$LOG_FILE" >&2; }
err()  { printf "${RED}[err]${RESET} %s\n" "$*" | tee -a "$LOG_FILE" >&2; }
note() { printf "${DIM}      %s${RESET}\n" "$*" | tee -a "$LOG_FILE" >&2; }

# ---------------- doctrinal whitelist ----------------
# We sync ONLY these dirs + root-level feedback markdown.
# Everything else in ~/.claude/ (sessions, history.jsonl, telemetry, plugins,
# session-env, paste-cache, file-history, settings.json, .credentials.json,
# tasks/, todos/, debug/) is host-local and must not be mixed.
SYNC_DIRS=(agents commands hooks modes skills memory guard)
SYNC_GLOBS=(feedback_*.md sync_config.json)

# Extra dotfiles to sync between phone <-> AceMagician PC.
# Format: "phone_path|pc_path".  These live outside ~/.claude/ so they
# can't ride SYNC_DIRS.  We sync them as standalone files in run_extras().
# Added 2026-05-13 to keep Emacs + shell config in lockstep across hosts.
SYNC_EXTRAS=(
  "/root/.emacs.d/init.el|~/.emacs.d/init.el"
  "/root/.emacs.d/lisp/lucrex-workspace.el|~/.emacs.d/lisp/lucrex-workspace.el"
  "/root/.emacs.d/lisp/lucrex-commands.el|~/.emacs.d/lisp/lucrex-commands.el"
  "/root/.emacs.d/lisp/lucrex-browser.el|~/.emacs.d/lisp/lucrex-browser.el"
  "/root/.emacs.d/lisp/lucrex-dashboard.el|~/.emacs.d/lisp/lucrex-dashboard.el"
  "/root/.zshrc|~/.zshrc"
  "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/everlight_shell.zsh|~/everlight_shell.zsh"
  "/root/.config/fastfetch/config.jsonc|~/.config/fastfetch/config.jsonc"
  "/root/.config/starship.toml|~/.config/starship.toml"
)

RSYNC_EXCLUDES=(
  --exclude='__pycache__/'
  --exclude='*.pyc'
  --exclude='*.token'
  --exclude='*.key'
  --exclude='*credentials*'
  --exclude='.sync_conflicts/'
  --exclude='scheduled_tasks.lock'
)

# Common rsync flags. -a = archive (perms, times, recursive). -z compress.
# --backup + --backup-dir = the receiver tucks the older copy into a quarantine
# dir before overwriting (only triggers when --update lets a transfer happen).
# --update = skip if dest is newer (this is the merge policy).
RSYNC_BASE_FLAGS=(
  -avz
  --update
  --backup
  --partial
  --human-readable
)

# ---------------- helpers ----------------
ssh_pc() {
  ssh -i "$PC_KEY" -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
      -o BatchMode=yes "${PC_USER}@${PC_HOST}" "$@"
}

pc_reachable() {
  if ssh_pc 'echo ok' >/dev/null 2>&1; then return 0; fi
  return 1
}

queue_for_later() {
  local mode="$1"
  echo "$(ts) ${mode}" >> "$QUEUE_FILE"
  note "Queued '${mode}' to ${QUEUE_FILE}; will retry on next run when PC wakes."
}

# Post a one-line ops ping to Slack (raw chat.postMessage; per doctrine this
# is fine for short ops pings, branded_slack is for full reports).
slack_ping() {
  local text="$1"
  local token_file="${PHONE_WORKSPACE}/03_Credentials/.env"
  [ -f "$token_file" ] || return 0
  # shellcheck disable=SC1090
  local token
  token=$(grep -E '^SLACK_BOT_TOKEN_WARROOM=' "$token_file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
  [ -z "$token" ] && return 0
  curl -s -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer ${token}" \
    -H 'Content-type: application/json' \
    -d "{\"channel\":\"#deploy-log\",\"text\":\"${text//\"/\\\"}\"}" \
    >/dev/null 2>&1 || true
}

# ---------------- conflict quarantine setup ----------------
# rsync's --backup-dir is interpreted relative to the destination.  The
# receiving side stashes the older file there before overwriting.
make_backup_dir() {
  echo ".sync_conflicts/$(date -u +%Y%m%dT%H%M%SZ)"
}

# ---------------- transfer primitives ----------------
SSH_CMD="ssh -i ${PC_KEY} -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new"

# Sync one dir in a given direction.
# args: <direction pull|push> <relative_path> <backup_dir> [extra_rsync_flags...]
sync_one() {
  local direction="$1"; local rel="$2"; local backup_dir="$3"; shift 3
  local src dst
  if [ "$direction" = "pull" ]; then
    src="${PC_USER}@${PC_HOST}:${PC_CLAUDE}/${rel}"
    dst="${PHONE_CLAUDE}/${rel}"
  else
    src="${PHONE_CLAUDE}/${rel}"
    dst="${PC_USER}@${PC_HOST}:${PC_CLAUDE}/${rel}"
  fi
  rsync "${RSYNC_BASE_FLAGS[@]}" "${RSYNC_EXCLUDES[@]}" \
    --backup-dir="${backup_dir}" \
    -e "${SSH_CMD}" "$@" "${src}" "${dst}" 2>&1 | tee -a "$LOG_FILE"
}

run_whitelist() {
  local direction="$1"
  local backup_dir; backup_dir=$(make_backup_dir)
  # Make sure parent dirs exist on receiver
  if [ "$direction" = "pull" ]; then
    mkdir -p "${PHONE_CLAUDE}"
  else
    ssh_pc "mkdir -p ${PC_CLAUDE}" || true
  fi
  for d in "${SYNC_DIRS[@]}"; do
    log "  ${direction}: ${d}/"
    if [ "$direction" = "pull" ]; then
      mkdir -p "${PHONE_CLAUDE}/${d}"
    else
      ssh_pc "mkdir -p ${PC_CLAUDE}/${d}" || true
    fi
    sync_one "$direction" "${d}/" "../.sync_conflicts/$(basename "$backup_dir")" || true
  done
  # root-level files matched by SYNC_GLOBS
  for pat in "${SYNC_GLOBS[@]}"; do
    if [ "$direction" = "pull" ]; then
      rsync "${RSYNC_BASE_FLAGS[@]}" "${RSYNC_EXCLUDES[@]}" \
        -e "${SSH_CMD}" \
        "${PC_USER}@${PC_HOST}:${PC_CLAUDE}/${pat}" "${PHONE_CLAUDE}/" \
        2>&1 | tee -a "$LOG_FILE" || true
    else
      # shellcheck disable=SC2086
      rsync "${RSYNC_BASE_FLAGS[@]}" "${RSYNC_EXCLUDES[@]}" \
        -e "${SSH_CMD}" \
        ${PHONE_CLAUDE}/${pat} "${PC_USER}@${PC_HOST}:${PC_CLAUDE}/" \
        2>&1 | tee -a "$LOG_FILE" || true
    fi
  done
}

run_extras() {
  # Sync the EXTRAS list (Emacs + shell + fastfetch + starship).
  # direction = pull|push.  Each entry is "phone_path|pc_path".
  local direction="$1"
  [ "${#SYNC_EXTRAS[@]}" -eq 0 ] && return 0
  for entry in "${SYNC_EXTRAS[@]}"; do
    local phone_path="${entry%%|*}"
    local pc_path="${entry##*|}"
    # Make sure target dir exists on the receiver
    local phone_dir; phone_dir=$(dirname "$phone_path")
    local pc_dir; pc_dir=$(dirname "$pc_path")
    if [ "$direction" = "pull" ]; then
      mkdir -p "$phone_dir" 2>/dev/null || true
      rsync "${RSYNC_BASE_FLAGS[@]}" -e "${SSH_CMD}" \
        "${PC_USER}@${PC_HOST}:${pc_path}" "${phone_path}" \
        2>&1 | tee -a "$LOG_FILE" || true
    else
      ssh_pc "mkdir -p ${pc_dir}" 2>/dev/null || true
      [ -f "$phone_path" ] || { note "skip (missing on phone): ${phone_path}"; continue; }
      rsync "${RSYNC_BASE_FLAGS[@]}" -e "${SSH_CMD}" \
        "${phone_path}" "${PC_USER}@${PC_HOST}:${pc_path}" \
        2>&1 | tee -a "$LOG_FILE" || true
    fi
  done
}

do_pull() {
  log "Pull PC -> phone (whitelist, --update, conflicts quarantined)"
  run_whitelist pull
  log "Pull EXTRAS (Emacs + shell + fastfetch)"
  run_extras pull
}

do_push() {
  log "Push phone -> PC (whitelist, --update, conflicts quarantined)"
  run_whitelist push
  log "Push EXTRAS (Emacs + shell + fastfetch)"
  run_extras push
}

do_diff() {
  log "Diff (dry-run, no transfer). PC <-> phone."
  for d in "${SYNC_DIRS[@]}"; do
    echo
    log "--- ${d}/ ---"
    log "[would PULL from PC]:"
    rsync -avzn --update "${RSYNC_EXCLUDES[@]}" -e "${SSH_CMD}" \
      "${PC_USER}@${PC_HOST}:${PC_CLAUDE}/${d}/" "${PHONE_CLAUDE}/${d}/" \
      2>/dev/null | grep -vE '^(sending|receiving|sent |total |building file|$)' | head -20 || true
    log "[would PUSH to PC]:"
    rsync -avzn --update "${RSYNC_EXCLUDES[@]}" -e "${SSH_CMD}" \
      "${PHONE_CLAUDE}/${d}/" "${PC_USER}@${PC_HOST}:${PC_CLAUDE}/${d}/" \
      2>/dev/null | grep -vE '^(sending|receiving|sent |total |building file|$)' | head -20 || true
  done
}

do_notepad() {
  log "Push NOTEPAD/ tree phone -> PC (--update, ~6 MB / 175 files)"
  ssh_pc "mkdir -p ${PC_WORKSPACE}/NOTEPAD" || true
  rsync -avz --update --human-readable "${RSYNC_EXCLUDES[@]}" \
    -e "${SSH_CMD}" \
    "${PHONE_WORKSPACE}/NOTEPAD/" \
    "${PC_USER}@${PC_HOST}:${PC_WORKSPACE}/NOTEPAD/" \
    2>&1 | tee -a "$LOG_FILE"
  # Drop an INGEST_QUEUE marker so the PC's claude session sees what's new.
  ssh_pc "cat > ${PC_WORKSPACE}/NOTEPAD/INGEST_QUEUE.md" <<EOF
# Ingest Queue (auto-generated by claude_sync_acemagician.sh)
Last updated: $(ts)

## Action
PC's Claude agent: read these new/updated transcripts and refresh the
agent firmware / skills accordingly. Cross-reference with:

  06_DEVELOPMENT/everlight_os/AIOS_FRAMEWORK.html

Folder index:
- 01_Claude_and_Codex/        AIOS framework, skills, plugins
- 02_AI_Agents_and_Swarms/    Multi-agent patterns, OpenSwarm, LangGraph
- 03_Slack_and_Communication/ Slackbot AI patterns
- 04_Self_Hosting_and_Offline_AI/  n8n homelab, local LLM stacks
- 05_OSINT_and_Security/      Skip-trace, OSINT pipelines
- 06_Knowledge_Management/    Obsidian / Karpathy RAG / memory layer
- 07_Content_Creation_Video/  Remotion, content factory
- 08_Spreadsheets_and_Ops/    Sheets-as-DB patterns
- 09_Research_and_Perplexity/ ppx workflows
- 10_Sales_and_Services/      Cold email, finder fees
- Ai_Brain/                   Persona / voice cloning notes
- BLACKJACK/                  Vantaris dealer AI research
- Trading/                    Fibonacci / hedging / shorting
- Personalities/              Astrology research (Lucrex weights)

When done, append entries to:
  06_DEVELOPMENT/everlight_os/hive_mind/transcripts_library/SUMMARY.md
EOF
  ok "INGEST_QUEUE.md written to PC"
}

do_full() {
  log "FULL sync: doctrine + NOTEPAD"
  do_pull
  do_push
  do_notepad
}

do_mirror_from_pc() {
  log "MIRROR PC -> phone (DESTRUCTIVE; phone-only files in scope deleted)"
  for d in "${SYNC_DIRS[@]}"; do
    rsync -avz --delete "${RSYNC_EXCLUDES[@]}" -e "${SSH_CMD}" \
      "${PC_USER}@${PC_HOST}:${PC_CLAUDE}/${d}/" "${PHONE_CLAUDE}/${d}/" \
      2>&1 | tee -a "$LOG_FILE"
  done
}

do_mirror_to_pc() {
  log "MIRROR phone -> PC (DESTRUCTIVE; PC-only files in scope deleted)"
  for d in "${SYNC_DIRS[@]}"; do
    rsync -avz --delete "${RSYNC_EXCLUDES[@]}" -e "${SSH_CMD}" \
      "${PHONE_CLAUDE}/${d}/" "${PC_USER}@${PC_HOST}:${PC_CLAUDE}/${d}/" \
      2>&1 | tee -a "$LOG_FILE"
  done
}

# ---------------- queue replay ----------------
# If a previous run was queued because PC was offline, replay it now.
replay_queue() {
  [ -f "$QUEUE_FILE" ] || return 0
  log "Replaying queued sync requests"
  local replayed=0
  while IFS= read -r line; do
    local mode; mode=$(echo "$line" | awk '{print $2}')
    case "$mode" in
      pull) do_pull && replayed=$((replayed+1)) ;;
      push) do_push && replayed=$((replayed+1)) ;;
      sync) do_pull && do_push && replayed=$((replayed+1)) ;;
    esac
  done < "$QUEUE_FILE"
  rm -f "$QUEUE_FILE"
  ok "Replayed ${replayed} queued request(s)"
}

# ---------------- main ----------------
mode="${1:---sync}"

log "Mode: ${mode}"
log "Log:  ${LOG_FILE}"

# Status check first.  If PC is asleep, queue and exit cleanly.
if [ "$mode" != "--status" ]; then
  if ! pc_reachable; then
    err "PC not reachable at ${PC_HOST} (${PC_HOST_NAME})"
    note "Likely sleeping. Tailscale will wake on activity, but rsync timed out."
    queue_for_later "${mode#--}"
    slack_ping ":sleeping: claude_sync queued (PC asleep). Mode=${mode}. Will retry next run."
    exit 0
  fi
  ok "PC reachable"
  replay_queue
fi

case "$mode" in
  --status)
    if pc_reachable; then
      remote_count=$(ssh_pc "ls ${PC_CLAUDE}/agents/ 2>/dev/null | wc -l")
      remote_disk=$(ssh_pc "du -sh ${PC_CLAUDE}/ 2>/dev/null | cut -f1")
      ok "PC online. Agents on PC: ${remote_count}. Size: ${remote_disk}"
      ok "Agents on phone: $(ls "${PHONE_CLAUDE}/agents/" | wc -l). Size: $(du -sh "${PHONE_CLAUDE}/" | cut -f1)"
    else
      err "PC offline (Tailscale asleep / host down)"
      [ -f "$QUEUE_FILE" ] && note "Pending queue: $(wc -l < "$QUEUE_FILE") request(s)"
    fi
    ;;
  --pull)  do_pull ;;
  --push)  do_push ;;
  --sync)  do_pull; do_push ;;
  --diff)  do_diff ;;
  --notepad) do_notepad ;;
  --full)    do_full ;;
  --mirror-from-pc) do_mirror_from_pc ;;
  --mirror-to-pc)   do_mirror_to_pc ;;
  -h|--help)
    sed -n '2,30p' "$0"
    exit 0
    ;;
  *)
    err "Unknown mode: ${mode}"
    sed -n '2,30p' "$0"
    exit 2
    ;;
esac

ok "Done at $(ts)"
slack_ping ":white_check_mark: claude_sync ${mode} ok ($(ts))"
