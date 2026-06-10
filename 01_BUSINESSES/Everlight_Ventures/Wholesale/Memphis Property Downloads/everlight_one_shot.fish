#!/usr/bin/env fish
# Everlight Logistics — One-Shot Bootstrap (Pi ↔ Proton ↔ Ryzen)
# Timestamp: (America/Los_Angeles) (generated) 2025-10-28T06:34:53.197596
# Run on the Orange Pi (Ubuntu 22.04, fish shell)
#
# What this does:
# 1) Validates mount and prerequisites
# 2) OPTIONAL package installs (rclone, fdupes, rmlint, sshfs) — can skip with SKIP_INSTALL=1
# 3) Local duplicate removal (exact-content)
# 4) High-speed Pi→Proton and Proton→Pi sync (≈50GB burst friendly)
# 5) Removes empty directories (cloud & local)
# 6) Sets up and enables systemd user bisync timer (10 min)
#
# Safe defaults: will exit early if Proton remote missing.
# Authoritative side for dedupe: Pi (LOCAL).

function banner
    set_color cyan
    echo -n "==> "
    set_color normal
    echo $argv
end

function die
    set_color red; echo "ERROR: "$argv; set_color normal
    exit 1
end

# -------- Config (edit if needed) --------
set -Ux LOCAL "/media/richgee/0123-4567/AA_MY_DRIVE"
set -Ux REMOTE "Proton_Drive_On_Pi:AA_MY_DRIVE_CLOUD/AceMagician"

# Speed profile (approx 50GB burst friendly)
set -Ux RCLONE_SPEED_TRANSFERS 12
set -Ux RCLONE_SPEED_CHECKERS 32
set -Ux RCLONE_SPEED_BUFFER 128M
set -Ux RCLONE_SPEED_MTS 8
set -Ux RCLONE_SPEED_CUTOFF 128M

# Control toggles
set -q SKIP_INSTALL; or set -Ux SKIP_INSTALL 0
set -q USE_RMLINT ; or set -Ux USE_RMLINT 1   # 1=rmlint scripted dedupe; 0=fdupes interactive dedupe

# Logs
set -l LOGDIR "$HOME"
set -l PUSH_LOG "$LOGDIR/proton_push_speed.log"
set -l PULL_LOG "$LOGDIR/proton_pull_speed.log"
set -l RM_DIRS_LOG "$LOGDIR/proton_rmdirs.log"
set -l BISYNC_LOG "$LOGDIR/proton_bisync.log"
set -l DEDUPE_LOG "$LOGDIR/dedupe.log"

# -------- Preflight --------
banner "Checking mount and data path..."
test -d (dirname $LOCAL); or die "Parent mount for LOCAL not found: "(dirname $LOCAL)
mkdir -p "$LOCAL"

banner "Verifying write access to LOCAL..."
test -w "$LOCAL"; or die "LOCAL not writable: $LOCAL"

banner "Checking rclone presence..."
type -q rclone; or begin
    if test "$SKIP_INSTALL" = "1"
        die "rclone not found and SKIP_INSTALL=1"
    else
        banner "Installing rclone..."
        sudo apt update && sudo apt install -y rclone || die "Failed to install rclone"
    end
end

banner "Checking Proton remote exists..."
set -l REMS (rclone listremotes)
echo $REMS | grep -q "^Proton_Drive_On_Pi:$"; or die "Remote Proton_Drive_On_Pi: missing. Run: rclone config  (create protondrive remote)"
rclone about Proton_Drive_On_Pi: | cat

# -------- Optional installs --------
if test "$SKIP_INSTALL" != "1"
    banner "Installing dedupe tools (fdupes, rmlint) and sshfs (optional)..."
    sudo apt update
    sudo apt install -y fdupes rmlint sshfs
end

# -------- Local Deduplication (Authoritative = Pi) --------
banner "Starting local deduplication on $LOCAL (Authoritative = Pi)"

if test "$USE_RMLINT" = "1"
    banner "Using rmlint (scripted) — see $DEDUPE_LOG"
    rmlint "$LOCAL" | tee "$DEDUPE_LOG"
    rmlint -o sh:dedupe.sh "$LOCAL" | tee -a "$DEDUPE_LOG"
    if test -f ./dedupe.sh
        bash ./dedupe.sh | tee -a "$DEDUPE_LOG"
    else
        banner "No dedupe.sh produced; either no duplicates or rmlint failed."
    end
else
    banner "Using fdupes (interactive) — deleting exact duplicates"
    fdupes -r "$LOCAL"
    fdupes -rdN "$LOCAL"
end

# -------- High-Speed Pi → Proton push --------
banner "High-speed Pi → Proton copy (skip existing; merge same-name folders)"
rclone copy "$LOCAL" "$REMOTE" \
  --update --ignore-existing \
  --track-renames --track-renames-strategy hash \
  --create-empty-src-dirs \
  --fast-list --transfers=$RCLONE_SPEED_TRANSFERS --checkers=$RCLONE_SPEED_CHECKERS \
  --buffer-size $RCLONE_SPEED_BUFFER \
  --multi-thread-streams $RCLONE_SPEED_MTS --multi-thread-cutoff $RCLONE_SPEED_CUTOFF \
  --retries 10 --retries-sleep 10s --low-level-retries 50 \
  --timeout 5m --contimeout 15s --expect-continue-timeout 5s \
  --protondrive-replace-existing-draft=true \
  --log-file="$PUSH_LOG" --log-level INFO --progress

# -------- High-Speed Proton → Pi backfill --------
banner "High-speed Proton → Pi backfill (skip existing)"
rclone copy "$REMOTE" "$LOCAL" \
  --update --ignore-existing \
  --fast-list --transfers=$RCLONE_SPEED_TRANSFERS --checkers=$RCLONE_SPEED_CHECKERS \
  --buffer-size $RCLONE_SPEED_BUFFER \
  --multi-thread-streams $RCLONE_SPEED_MTS --multi-thread-cutoff $RCLONE_SPEED_CUTOFF \
  --retries 10 --retries-sleep 10s --low-level-retries 50 \
  --timeout 5m --contimeout 15s --expect-continue-timeout 5s \
  --log-file="$PULL_LOG" --log-level INFO --progress

# -------- Remove empty directories (cloud & local) --------
banner "Removing empty directories on Proton (keeping root)"
rclone rmdirs "$REMOTE" --leave-root --fast-list --checkers=$RCLONE_SPEED_CHECKERS \
  --log-file="$RM_DIRS_LOG" --log-level INFO --progress

banner "Removing empty directories locally (Pi)"
find "$LOCAL" -type d -empty -print
find "$LOCAL" -type d -empty -delete

# -------- Bisync Dry Run --------
banner "Bisync dry-run (preview changes)"
rclone bisync "$LOCAL" "$REMOTE" \
  --compare size,modtime --check-access --fast-list \
  --checkers=$RCLONE_SPEED_CHECKERS --transfers=$RCLONE_SPEED_TRANSFERS \
  --buffer-size $RCLONE_SPEED_BUFFER \
  --multi-thread-streams $RCLONE_SPEED_MTS --multi-thread-cutoff $RCLONE_SPEED_CUTOFF \
  --retries 10 --retries-sleep 10s --low-level-retries 50 \
  --timeout 5m --contimeout 15s --expect-continue-timeout 5s \
  --log-file="$BISYNC_LOG" --log-level INFO --dry-run --verbose

# -------- Systemd user timer (10 min) --------
banner "Installing systemd user service & timer for bisync (10 min)"
mkdir -p ~/.config/systemd/user

# Service unit
cat > ~/.config/systemd/user/proton-bisync.service <<'EOF'
[Unit]
Description=Pi <-> Proton bisync

[Service]
Type=oneshot
ExecStart=/usr/bin/rclone bisync /media/richgee/0123-4567/AA_MY_DRIVE Proton_Drive_On_Pi:AA_MY_DRIVE_CLOUD/AceMagician \
  --compare size,modtime --conflict-resolve newer --check-access --fast-list \
  --checkers 8 --transfers 4 --retries 8 --low-level-retries 24 \
  --tpslimit 4 --tpslimit-burst 4 \
  --log-file=/home/richgee/proton_bisync.log --log-level INFO
EOF

# Timer unit
cat > ~/.config/systemd/user/proton-bisync.timer <<'EOF'
[Unit]
Description=Run proton-bisync every 10 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
Unit=proton-bisync.service

[Install]
WantedBy=timers.target
EOF

# Enable & start timer
systemctl --user daemon-reload
systemctl --user enable --now proton-bisync.timer
systemctl --user list-timers | grep proton-bisync

banner "DONE ✅  Review logs: $PUSH_LOG  $PULL_LOG  $RM_DIRS_LOG  $BISYNC_LOG"
banner "If everything looks good, bisync timer is active every 10 minutes."
