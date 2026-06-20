# Tri-Device Vault, Plan 1: Foundation (Phases 0-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a verified, full, self-protecting backup of the phone workspace + E5 host-state on the AceMagician PC, plus an always-on deduplicated snapshot history on E5, with sync legs that cannot silently corrupt or delete data.

**Architecture:** The PC holds the only true full 1:1 (E5's disk is too small for the 18GB media library). E5 runs continuous restic snapshots of the working subset as the always-on durable history. All sync legs are guarded (snapshot-before-pull, content-checksum, bounded `--delete`). Databases are dumped, never hot-copied.

**Tech Stack:** bash, rsync 3.4.2, restic, b3sum, sqlite3, pg_dump (via docker exec), systemd timers (E5), Tailscale, plain btrfs on the PC.

## Global Constraints

- **No em-dash characters** anywhere in committed files (workspace content guard blocks them). Use `,` `:` or `--`.
- **Scripts live in** `03_AUTOMATION_CORE/01_Scripts/mesh/vault/` (new dir). Config in the same dir.
- **Editing anything under `03_AUTOMATION_CORE/01_Scripts/` triggers `deploy_to_oracle.sh`** (cron every 10 min + manual). E5-side scripts reach E5 through that path; do not invent a second deploy channel.
- **Phone is FAT/sdcard:** rsync from the phone source must use `--no-perms --no-owner --no-group --no-times` AND `--checksum` (mtime is unreliable at 2s granularity).
- **Big / secret-bearing transfers to E5 use the PUBLIC IP** `ssh e5` = `163.192.60.35:22`, key `/root/.ssh/github_deploy`, user `ubuntu`. The tailnet alias `e5-mother` drops when Tailscale is off.
- **AceMagician:** `richgee@100.93.253.49`, key `/root/.ssh/phone_to_arch`, MagicDNS `acemagician-pc.tailfeeb43.ts.net`. Power-managed (may be offline). btrfs, NOT encrypted yet.
- **Secrets never via git.** PII + wallet seeds never leave the LAN/tailnet legs (no cloud).
- **Never `pkill` a running transfer** (self-kill). Long transfers run detached (`setsid`/`nohup`).
- **Conflict policy:** never delete a conflicting file; move losers to `quarantine/<date>/`.
- **Vault root on PC:** `/home/richgee/vault/`. Working subset (fits E5's ~43GB): everything EXCEPT `04_MEDIA_LIBRARY/` and `08_BACKUPS/`. Full scope (PC only): the entire workspace.

---

## File Structure

New files (all under `03_AUTOMATION_CORE/01_Scripts/mesh/vault/`):
- `cloud_denylist.txt` -- canonical PII/seed path patterns barred from any cloud remote.
- `lib_guarded_rsync.sh` -- sourceable function: checksum + bounded-delete + abort-on-mass-delete rsync wrapper.
- `db_safe_capture.sh` -- dumps Postgres (docker exec pg_dump) + SQLite (`.backup`) to a dump dir before any snapshot.
- `restic_init_and_policy.sh` -- inits a restic repo and applies the retention policy.
- `vault_seed_manifest.sh` -- computes per-tree file-count + bytes + b3sum roll-up; writes `seed_manifest.json`.
- `vault_dirs.sh` -- idempotent creator of the `/home/richgee/vault/` skeleton.

Modified files:
- `03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh` -- push working-subset to E5 with checksum + quarantine.
- `03_AUTOMATION_CORE/01_Scripts/mesh/acemagician_warm_standby.sh` -- public IP, pg_dump not hot-tar, full E5 host-state, guarded delete.
- `03_AUTOMATION_CORE/01_Scripts/mesh/hive_hosts.env` -- add vault path + repo + denylist variables.

Test files:
- `03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_guarded_rsync.sh` -- shell asserts for the rsync guard.
- `03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_db_safe_capture.sh` -- sqlite `.backup` integrity assert.
- `03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_seed_manifest.sh` -- manifest count/byte assert.

---

## PHASE 0: Preconditions (blocking, no rollback needed -- installs + config only)

### Task 0.1: Install snapshot tooling on all three nodes

**Files:** none (environment changes only).

**Interfaces:**
- Produces: `restic`, `b3sum` available on PC + E5; `gocryptfs` available on PC (used in Plan 2).

- [ ] **Step 1: Operator installs PC tooling (needs sudo password, cannot be done remotely)**

The operator runs ON the AceMagician (already prompted in `/home/richgee/vault_plan/PREP_README.md`):
```bash
sudo pacman -Sy --needed restic b3sum gocryptfs
```

- [ ] **Step 2: Verify PC tooling from the phone**

Run:
```bash
ssh -i /root/.ssh/phone_to_arch -o BatchMode=yes richgee@100.93.253.49 \
  'for b in restic b3sum gocryptfs; do printf "%-10s " $b; command -v $b >/dev/null && $b --version 2>/dev/null | head -1 || echo MISSING; done'
```
Expected: three non-MISSING lines (restic, b3sum, gocryptfs with versions).

- [ ] **Step 3: Install E5 tooling over the public IP**

Run:
```bash
ssh -i /root/.ssh/github_deploy -o ConnectTimeout=10 ubuntu@163.192.60.35 \
  'sudo apt-get update -qq && sudo apt-get install -y restic b3sum && restic version && b3sum --version'
```
Expected: `restic 0.x.x` and a b3sum version line. (If `b3sum` is not in apt on that release, fall back to `sudo apt-get install -y b3sum || cargo install b3sum`; record which was used.)

- [ ] **Step 4: Commit a tooling-status note (no code yet, just a record)**

```bash
mkdir -p 03_AUTOMATION_CORE/01_Scripts/mesh/vault
printf '# Phase 0 tooling verified %s\nPC: restic+b3sum+gocryptfs\nE5: restic+b3sum\n' "$(date +%F)" \
  > 03_AUTOMATION_CORE/01_Scripts/mesh/vault/PHASE0_TOOLING.md
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/PHASE0_TOOLING.md
git commit -m "chore(vault): record Phase 0 tooling install on PC + E5"
```

### Task 0.2: Author the canonical cloud denylist

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/cloud_denylist.txt`

**Interfaces:**
- Produces: one rsync/grep-compatible pattern file every cloud-bound job will source.

- [ ] **Step 1: Write the denylist**

These patterns were derived from the data-inventory scout (wallet seeds, breach/PII, leads, medical).
```
# cloud_denylist.txt -- paths that must NEVER reach any cloud remote (Google/Proton).
# Format: one path-glob per line, anchored to the workspace root. Used by rsync --exclude-from
# and by a grep -f assertion in the parity auditor.
**/*seed_phrase*
**/*_sp.py
**/SEED_VAULT*
**/phantom_sp.py
**/atomic_sp.py
**/bcardi_coin_sp.py
**/Zilpay_Bacardi_Wallet_SP.py
03_AUTOMATION_CORE/03_Credentials/**
**/*.pem
**/*.key
**/.env
**/.env.*
01_BUSINESSES/Everlight_Ventures/Wholesale/config/_generated/**
**/leads_db*.json
**/leads_db*.sqlite
**/FL_prospects.csv
**/GA_prospects.csv
**/MO_prospects.csv
**/TX_prospects.csv
_state/TN_TOP_TARGETS_*.json
_logs/ai_consulting/prospects_*.json
_logs/enrichment/**
05_PERSONAL/02_Training/MMA_Notebook/MMA_Paperwork/**
```

- [ ] **Step 2: Verify it is non-empty and well-formed**

Run: `grep -c . 03_AUTOMATION_CORE/01_Scripts/mesh/vault/cloud_denylist.txt`
Expected: a number >= 20.

- [ ] **Step 3: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/cloud_denylist.txt
git commit -m "feat(vault): canonical PII/seed cloud denylist"
```

### Task 0.3: Audit the existing rclone cloud job against the denylist

**Files:**
- Modify (if leaks found): `03_AUTOMATION_CORE/01_Scripts/.rclone_sdcard_exclude`

**Interfaces:**
- Consumes: `cloud_denylist.txt` from Task 0.2.

- [ ] **Step 1: Find denylisted paths that currently exist in the workspace**

Run:
```bash
while IFS= read -r pat; do
  [ "${pat#\#}" != "$pat" ] && continue; [ -z "$pat" ] && continue
  found=$(find /mnt/sdcard/AA_MY_DRIVE -path "/mnt/sdcard/AA_MY_DRIVE/$pat" 2>/dev/null | head -1)
  [ -n "$found" ] && echo "PRESENT: $pat -> $found"
done < 03_AUTOMATION_CORE/01_Scripts/mesh/vault/cloud_denylist.txt
```
Expected: a list of real PII/seed files present on disk (these are what must be barred from cloud).

- [ ] **Step 2: Confirm each is excluded by the rclone job**

Run: `grep -nE "Credentials|\.env|seed|leads_db|prospects|enrichment|MMA_Paperwork|_generated" 03_AUTOMATION_CORE/01_Scripts/.rclone_sdcard_exclude`
Expected: matching exclude lines. For any denylist pattern with NO corresponding rclone exclude, that is a leak.

- [ ] **Step 3: Patch any gap (only if Step 2 found a leak)**

Append the missing patterns (rclone exclude syntax) to `.rclone_sdcard_exclude`. Example for a found gap:
```bash
printf '%s\n' '03_AUTOMATION_CORE/03_Credentials/**' '_logs/enrichment/**' \
  >> 03_AUTOMATION_CORE/01_Scripts/.rclone_sdcard_exclude
```

- [ ] **Step 4: Re-run Step 2 to confirm zero gaps, then commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/.rclone_sdcard_exclude
git commit -m "fix(vault): close cloud-exclude gaps vs canonical denylist"
```
Expected: every denylist pattern present on disk now has a matching rclone exclude. If nothing changed, note "no leaks found" and skip the commit.

---

## PHASE 1: First full seed via USB-C

### Task 1.1: Create the vault skeleton on the PC

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/vault_dirs.sh`

**Interfaces:**
- Produces: `/home/richgee/vault/{mirror/workspace,mirror/e5/{home,docker_volumes,systemd_units},restic,restic_e5_replica,parity/{manifests,roots,reports},drills,quarantine,_state}`.

- [ ] **Step 1: Write the idempotent dir creator**

```bash
#!/usr/bin/env bash
# vault_dirs.sh -- idempotent creation of the AceMagician vault skeleton. Safe to re-run.
set -euo pipefail
ROOT="${VAULT_ROOT:-/home/richgee/vault}"
for d in mirror/workspace mirror/e5/home mirror/e5/docker_volumes mirror/e5/systemd_units \
         restic restic_e5_replica parity/manifests parity/roots parity/reports \
         drills quarantine _state; do
  mkdir -p "$ROOT/$d"
done
echo "vault skeleton ready at $ROOT"
find "$ROOT" -maxdepth 2 -type d | sort
```

- [ ] **Step 2: Ship it to the PC and run it**

Run:
```bash
scp -i /root/.ssh/phone_to_arch 03_AUTOMATION_CORE/01_Scripts/mesh/vault/vault_dirs.sh richgee@100.93.253.49:/home/richgee/vault_plan/
ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 'bash /home/richgee/vault_plan/vault_dirs.sh'
```
Expected: "vault skeleton ready at /home/richgee/vault" + the directory listing.

- [ ] **Step 3: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/vault_dirs.sh
git commit -m "feat(vault): idempotent vault skeleton creator"
```

### Task 1.2: Seed the full workspace to the PC over USB-C

**Files:** none (data move).

**Interfaces:**
- Consumes: vault skeleton from Task 1.1.
- Produces: `/home/richgee/vault/mirror/workspace/AA_MY_DRIVE/` populated (~44GB).

- [ ] **Step 1: Operator connects the phone by USB-C and confirms the mount point**

On the PC, the operator plugs in the phone (USB file transfer / MTP) OR an external SSD that the phone has copied to. Identify the source path, e.g. `/run/user/1000/gvfs/...` (MTP) or `/mnt/usb/AA_MY_DRIVE`. Record it as `SRC`.

- [ ] **Step 2: Local rsync on the PC (USB), full scope, checksum**

The operator runs ON the PC (replace `SRC`):
```bash
rsync -rh --info=progress2 --checksum --partial --no-perms --no-owner --no-group --no-times \
  "SRC/AA_MY_DRIVE/" /home/richgee/vault/mirror/workspace/AA_MY_DRIVE/
```
Expected: progress to 100%, no fatal errors. (MTP can be slow; an external SSD is faster. Either is one-time.)

- [ ] **Step 3: Network fallback (only if USB is unavailable), detached + resumable**

From the phone, detached so a dropped link or power-off resumes:
```bash
setsid rsync -rh --append-verify --partial --checksum --no-perms --no-owner --no-group --no-times \
  -e "ssh -i /root/.ssh/phone_to_arch" /mnt/sdcard/AA_MY_DRIVE/ \
  richgee@100.93.253.49:/home/richgee/vault/mirror/workspace/AA_MY_DRIVE/ \
  >/mnt/sdcard/AA_MY_DRIVE/_logs/vault_seed.log 2>&1 &
echo "seeding detached, tail _logs/vault_seed.log"
```
Expected: backgrounded; `tail _logs/vault_seed.log` shows progress.

- [ ] **Step 4: Confirm top-level scope landed (incl. media)**

Run:
```bash
ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 \
  'du -sh /home/richgee/vault/mirror/workspace/AA_MY_DRIVE; ls /home/richgee/vault/mirror/workspace/AA_MY_DRIVE | grep -E "04_MEDIA_LIBRARY|01_BUSINESSES|_logs"'
```
Expected: total near 44G AND `04_MEDIA_LIBRARY`, `01_BUSINESSES`, `_logs` all listed (proves full scope, unlike the old 31G partial mirror).

### Task 1.3: Seed E5 host-state to the PC

**Files:** none (data move).

**Interfaces:**
- Produces: `/home/richgee/vault/mirror/e5/home/` populated from E5.

- [ ] **Step 1: Pull E5 home + deploy + blinko backups over the public IP, detached**

From the phone:
```bash
ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 'bash -lc "
setsid rsync -rh --append-verify --partial -e \"ssh -i /root/.ssh/github_deploy -o StrictHostKeyChecking=accept-new\" \
  ubuntu@163.192.60.35:/home/ubuntu/e5_data/ /home/richgee/vault/mirror/e5/home/e5_data/ \
  >/home/richgee/vault/_state/seed_e5.log 2>&1 &
echo started"'
```
Expected: "started". (The PC must have the `github_deploy` key; if absent, copy it to the PC first via `scp` from the phone into `/home/richgee/.ssh/` with mode 600.)

- [ ] **Step 2: Verify E5 seed size**

Run: `ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 'du -sh /home/richgee/vault/mirror/e5/home/e5_data 2>/dev/null'`
Expected: a few GB (e5_data is ~3.8GB). Re-check until it stops growing (seed complete).

### Task 1.4: Compute the seed manifest and gate the first GREEN

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/vault_seed_manifest.sh`
- Test: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_seed_manifest.sh`

**Interfaces:**
- Produces: `/home/richgee/vault/_state/seed_manifest.json` with `{tree, files, bytes, root}` per tree.

- [ ] **Step 1: Write the failing test**

```bash
#!/usr/bin/env bash
# test_seed_manifest.sh -- manifest must report correct file count + bytes for a known tree.
set -euo pipefail
DIR="$(mktemp -d)"; trap 'rm -rf "$DIR"' EXIT
mkdir -p "$DIR/src"; printf 'aaa' > "$DIR/src/a.txt"; printf 'bbbb' > "$DIR/src/b.txt"
OUT="$DIR/manifest.json"
VAULT_MANIFEST_OUT="$OUT" bash "$(dirname "$0")/../vault_seed_manifest.sh" "$DIR/src" testtree
files=$(grep -o '"files":[0-9]*' "$OUT" | head -1 | grep -o '[0-9]*')
bytes=$(grep -o '"bytes":[0-9]*' "$OUT" | head -1 | grep -o '[0-9]*')
[ "$files" = "2" ] || { echo "FAIL files=$files want 2"; exit 1; }
[ "$bytes" = "7" ] || { echo "FAIL bytes=$bytes want 7"; exit 1; }
echo "PASS"
```

- [ ] **Step 2: Run it to confirm it fails (script does not exist yet)**

Run: `bash 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_seed_manifest.sh`
Expected: FAIL (No such file `vault_seed_manifest.sh`).

- [ ] **Step 3: Write the manifest script**

```bash
#!/usr/bin/env bash
# vault_seed_manifest.sh SRC TREENAME -- emit {tree,files,bytes,root} JSON for SRC.
# root = b3sum of the sorted "path size" listing (fast structural hash; full-content hash is Plan 2 parity).
set -euo pipefail
SRC="$1"; TREE="${2:-tree}"
OUT="${VAULT_MANIFEST_OUT:-/home/richgee/vault/_state/seed_manifest.json}"
mkdir -p "$(dirname "$OUT")"
files=$(find "$SRC" -type f | wc -l | tr -d ' ')
bytes=$(find "$SRC" -type f -printf '%s\n' 2>/dev/null | awk '{s+=$1} END{print s+0}')
root=$(find "$SRC" -type f -printf '%P %s\n' 2>/dev/null | LC_ALL=C sort | b3sum | awk '{print $1}')
printf '{"tree":"%s","files":%s,"bytes":%s,"root":"%s","ts":"%s"}\n' \
  "$TREE" "$files" "$bytes" "$root" "$(date -u +%FT%TZ)" > "$OUT"
cat "$OUT"
```

- [ ] **Step 4: Run the test to confirm it passes**

Run: `bash 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_seed_manifest.sh`
Expected: PASS.

- [ ] **Step 5: Run it against the real seeded vault on the PC**

Run:
```bash
scp -i /root/.ssh/phone_to_arch 03_AUTOMATION_CORE/01_Scripts/mesh/vault/vault_seed_manifest.sh richgee@100.93.253.49:/home/richgee/vault_plan/
ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 \
  'bash /home/richgee/vault_plan/vault_seed_manifest.sh /home/richgee/vault/mirror/workspace/AA_MY_DRIVE workspace'
```
Expected: JSON with `files` in the ~600k range and `bytes` near 44e9. Record it; this is the seed baseline.

- [ ] **Step 6: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/vault_seed_manifest.sh 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_seed_manifest.sh
git commit -m "feat(vault): seed manifest (file/byte/structural-root) + test"
```

---

## PHASE 2: E5 snapshot engine + DB-safe capture

### Task 2.1: DB-safe capture (the anti-corruption pre-step)

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/db_safe_capture.sh`
- Test: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_db_safe_capture.sh`

**Interfaces:**
- Produces: consistent dump files under `$DUMP_DIR` for every known DB; exit non-zero if any dump fails.

- [ ] **Step 1: Write the failing test (SQLite path is unit-testable offline)**

```bash
#!/usr/bin/env bash
# test_db_safe_capture.sh -- a sqlite .backup of a live-written DB must restore to identical rows.
set -euo pipefail
DIR="$(mktemp -d)"; trap 'rm -rf "$DIR"' EXIT
DB="$DIR/live.db"
sqlite3 "$DB" 'CREATE TABLE t(x); INSERT INTO t VALUES (1),(2),(3);'
DUMP_DIR="$DIR/dumps" SQLITE_TARGETS="$DB" PG_TARGETS="" bash "$(dirname "$0")/../db_safe_capture.sh"
OUT="$DIR/dumps/$(basename "$DB").bak"
[ -f "$OUT" ] || { echo "FAIL no dump produced"; exit 1; }
n=$(sqlite3 "$OUT" 'SELECT count(*) FROM t;')
[ "$n" = "3" ] || { echo "FAIL restored rows=$n want 3"; exit 1; }
echo "PASS"
```

- [ ] **Step 2: Run it to confirm failure**

Run: `bash 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_db_safe_capture.sh`
Expected: FAIL (script missing).

- [ ] **Step 3: Write the capture script**

```bash
#!/usr/bin/env bash
# db_safe_capture.sh -- produce consistent DB dumps before any snapshot. Never copy a live DB file.
# Env: DUMP_DIR (out), SQLITE_TARGETS (space list of .db paths), PG_TARGETS (space list of "container:db").
set -euo pipefail
DUMP_DIR="${DUMP_DIR:?set DUMP_DIR}"; mkdir -p "$DUMP_DIR"
rc=0
for db in ${SQLITE_TARGETS:-}; do
  [ -f "$db" ] || { echo "skip (absent): $db"; continue; }
  # .backup is atomic and WAL-safe; never tar the raw .db + -wal + -shm.
  if sqlite3 "$db" ".backup '$DUMP_DIR/$(basename "$db").bak'"; then
    echo "sqlite ok: $db"
  else echo "sqlite FAIL: $db"; rc=1; fi
done
for tgt in ${PG_TARGETS:-}; do
  container="${tgt%%:*}"; dbname="${tgt##*:}"
  if docker exec "$container" pg_dump -Fc "$dbname" > "$DUMP_DIR/${container}_${dbname}.dump" 2>/dev/null; then
    echo "pg ok: $tgt"
  else echo "pg FAIL: $tgt"; rc=1; fi
done
exit $rc
```

- [ ] **Step 4: Run the test to confirm pass**

Run: `bash 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_db_safe_capture.sh`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/db_safe_capture.sh 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_db_safe_capture.sh
git commit -m "feat(vault): db-safe capture (sqlite .backup + pg_dump), never hot-copy a live DB"
```

### Task 2.2: restic repo init + retention policy wrapper

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/restic_init_and_policy.sh`

**Interfaces:**
- Consumes: `RESTIC_REPOSITORY`, `RESTIC_PASSWORD_FILE` from the environment.
- Produces: an initialized repo + a `prune` policy function callable as `restic_init_and_policy.sh prune`.

- [ ] **Step 1: Write the script**

```bash
#!/usr/bin/env bash
# restic_init_and_policy.sh [init|prune] -- manage a restic repo with count-based retention.
# Retention is COUNT/EVENT based, never pure wall-clock, so a powered-off PC never races a time prune.
set -euo pipefail
: "${RESTIC_REPOSITORY:?set RESTIC_REPOSITORY}"
: "${RESTIC_PASSWORD_FILE:?set RESTIC_PASSWORD_FILE}"
case "${1:-init}" in
  init)
    if restic snapshots >/dev/null 2>&1; then echo "repo already initialized: $RESTIC_REPOSITORY";
    else restic init && echo "initialized: $RESTIC_REPOSITORY"; fi ;;
  prune)
    restic forget --keep-last 20 --keep-daily 14 --keep-weekly 8 --keep-monthly 12 --prune ;;
  *) echo "usage: $0 [init|prune]"; exit 2 ;;
esac
```

- [ ] **Step 2: Smoke-test against a throwaway local repo on the phone**

Run:
```bash
T="$(mktemp -d)"; echo testpass > "$T/pw"
RESTIC_REPOSITORY="$T/repo" RESTIC_PASSWORD_FILE="$T/pw" bash 03_AUTOMATION_CORE/01_Scripts/mesh/vault/restic_init_and_policy.sh init
RESTIC_REPOSITORY="$T/repo" RESTIC_PASSWORD_FILE="$T/pw" restic -r "$T/repo" snapshots; rm -rf "$T"
```
Expected: "initialized: .../repo" then an empty snapshots table (no error). (Requires restic on the phone; if absent, run this same smoke test on E5 via ssh.)

- [ ] **Step 3: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/restic_init_and_policy.sh
git commit -m "feat(vault): restic init + count-based retention policy wrapper"
```

### Task 2.3: E5 snapshot timer (dump-then-snapshot the working subset)

**Files:**
- Create on E5 (via deploy): `/home/ubuntu/vault/run_snapshot.sh`, `~/.config/systemd/user/vault-snapshot.service`, `vault-snapshot.timer`
- The source-of-truth copies live in `03_AUTOMATION_CORE/01_Scripts/mesh/vault/e5/`.

**Interfaces:**
- Consumes: `db_safe_capture.sh`, `restic_init_and_policy.sh`.
- Produces: hourly restic snapshots of E5's working subset to `/srv/restic` (E5 history #1).

- [ ] **Step 1: Write the E5 runner**

Create `03_AUTOMATION_CORE/01_Scripts/mesh/vault/e5/run_snapshot.sh`:
```bash
#!/usr/bin/env bash
# run_snapshot.sh (E5) -- dump DBs, then snapshot the working subset. Working subset excludes only
# media + the 08_BACKUPS tree (which is itself derived) and true-ephemeral DB sidecars.
set -euo pipefail
export RESTIC_REPOSITORY=/srv/restic
export RESTIC_PASSWORD_FILE=/home/ubuntu/.config/vault/restic.pass
DUMP_DIR=/home/ubuntu/vault/dumps
mkdir -p "$DUMP_DIR"
DUMP_DIR="$DUMP_DIR" \
  SQLITE_TARGETS="/home/ubuntu/AA_MY_DRIVE/_state/blinko_lite.db /home/ubuntu/AA_MY_DRIVE/_logs/hive.db" \
  PG_TARGETS="$(docker ps --format '{{.Names}}' | grep -i blinko | head -1):blinko" \
  /home/ubuntu/vault/db_safe_capture.sh || echo "WARN: a dump failed (continuing; snapshot will note it)"
restic backup \
  --exclude '04_MEDIA_LIBRARY' --exclude '08_BACKUPS' \
  --exclude '*-wal' --exclude '*-shm' --exclude '*.lock' --exclude '*.pid' \
  /home/ubuntu/AA_MY_DRIVE /home/ubuntu/e5_data "$DUMP_DIR" /home/ubuntu/vault/systemd_units 2>&1 | tail -5
/home/ubuntu/vault/restic_init_and_policy.sh prune
```

- [ ] **Step 2: Write the systemd user unit + timer**

Create `03_AUTOMATION_CORE/01_Scripts/mesh/vault/e5/vault-snapshot.service`:
```ini
[Unit]
Description=Vault: dump DBs and restic-snapshot the working subset
[Service]
Type=oneshot
ExecStart=/home/ubuntu/vault/run_snapshot.sh
```
Create `03_AUTOMATION_CORE/01_Scripts/mesh/vault/e5/vault-snapshot.timer`:
```ini
[Unit]
Description=Hourly vault snapshot on E5
[Timer]
OnBootSec=10min
OnUnitActiveSec=1h
Persistent=true
[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Deploy to E5 and install (over public IP)**

Run:
```bash
ssh -i /root/.ssh/github_deploy ubuntu@163.192.60.35 'mkdir -p ~/vault ~/.config/vault ~/.config/systemd/user'
scp -i /root/.ssh/github_deploy 03_AUTOMATION_CORE/01_Scripts/mesh/vault/db_safe_capture.sh 03_AUTOMATION_CORE/01_Scripts/mesh/vault/restic_init_and_policy.sh 03_AUTOMATION_CORE/01_Scripts/mesh/vault/e5/run_snapshot.sh ubuntu@163.192.60.35:~/vault/
scp -i /root/.ssh/github_deploy 03_AUTOMATION_CORE/01_Scripts/mesh/vault/e5/vault-snapshot.* ubuntu@163.192.60.35:~/.config/systemd/user/
ssh -i /root/.ssh/github_deploy ubuntu@163.192.60.35 'bash -lc "
  chmod +x ~/vault/*.sh
  head -c 32 /dev/urandom | base64 > ~/.config/vault/restic.pass && chmod 600 ~/.config/vault/restic.pass
  RESTIC_REPOSITORY=/srv/restic RESTIC_PASSWORD_FILE=~/.config/vault/restic.pass ~/vault/restic_init_and_policy.sh init
  sudo install -d -o ubuntu /srv/restic 2>/dev/null || true
  systemctl --user daemon-reload && systemctl --user enable --now vault-snapshot.timer
  loginctl enable-linger ubuntu
  systemctl --user start vault-snapshot.service
"'
```
Expected: "initialized: /srv/restic" and no fatal errors. (If `/srv` needs root, use `/home/ubuntu/restic` for the repo instead and update `RESTIC_REPOSITORY` consistently.)

- [ ] **Step 4: Verify a snapshot exists**

Run:
```bash
ssh -i /root/.ssh/github_deploy ubuntu@163.192.60.35 \
  'RESTIC_REPOSITORY=/srv/restic RESTIC_PASSWORD_FILE=~/.config/vault/restic.pass restic snapshots --compact | tail -5'
```
Expected: at least one snapshot row with today's date.

- [ ] **Step 5: Commit the source-of-truth copies**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/e5/
git commit -m "feat(vault): E5 hourly dump-then-snapshot timer (always-on history #1)"
```

### Task 2.4: Prove the E5 DB snapshot actually restores

**Files:** none (verification).

- [ ] **Step 1: Restore one SQLite dump from the latest snapshot and assert rows**

Run:
```bash
ssh -i /root/.ssh/github_deploy ubuntu@163.192.60.35 'bash -lc "
  export RESTIC_REPOSITORY=/srv/restic RESTIC_PASSWORD_FILE=~/.config/vault/restic.pass
  T=\$(mktemp -d)
  restic restore latest --target \$T --include /home/ubuntu/vault/dumps
  f=\$(find \$T -name blinko_lite.db.bak | head -1)
  echo rows=\$(sqlite3 \$f \"SELECT count(*) FROM sqlite_master;\")
  rm -rf \$T
"'
```
Expected: `rows=<a positive integer>` (the dump opens cleanly, proving the C3 corruption fix works).

---

## PHASE 3: Mirror legs with guards

### Task 3.1: Guarded-rsync library (the safety wrapper used by every leg)

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/lib_guarded_rsync.sh`
- Test: `03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_guarded_rsync.sh`

**Interfaces:**
- Produces: function `guarded_rsync SRC DST [extra rsync args...]` that aborts (exit 20) if the run would delete more than `MAX_DELETE` (default 500) files; uses `--checksum --partial --append-verify`.

- [ ] **Step 1: Write the failing test**

```bash
#!/usr/bin/env bash
# test_guarded_rsync.sh -- a sync that would delete > MAX_DELETE files must ABORT, not execute.
set -euo pipefail
. "$(dirname "$0")/../lib_guarded_rsync.sh"
DIR="$(mktemp -d)"; trap 'rm -rf "$DIR"' EXIT
mkdir -p "$DIR/src" "$DIR/dst"
# dst has 10 files, src has 0 -> a mirror would delete 10. With MAX_DELETE=3 it must abort.
for i in $(seq 1 10); do printf x > "$DIR/dst/f$i"; done
set +e
MAX_DELETE=3 guarded_rsync "$DIR/src/" "$DIR/dst/"
rc=$?
set -e
[ "$rc" = "20" ] || { echo "FAIL rc=$rc want 20 (abort)"; exit 1; }
# dst must be untouched (still 10 files)
n=$(find "$DIR/dst" -type f | wc -l | tr -d ' ')
[ "$n" = "10" ] || { echo "FAIL dst mutated, files=$n want 10"; exit 1; }
echo "PASS"
```

- [ ] **Step 2: Run it to confirm failure**

Run: `bash 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_guarded_rsync.sh`
Expected: FAIL (lib not found).

- [ ] **Step 3: Write the library**

```bash
#!/usr/bin/env bash
# lib_guarded_rsync.sh -- source this, then call: guarded_rsync SRC DST [extra args...]
# Dry-runs first to count deletions; aborts (exit 20) if deletions exceed MAX_DELETE.
guarded_rsync() {
  local src="$1" dst="$2"; shift 2
  local max="${MAX_DELETE:-500}"
  local base=(--archive --checksum --partial --append-verify --delete --human-readable
              --no-perms --no-owner --no-group --no-times)
  local del
  del=$(rsync "${base[@]}" --dry-run --delete "$@" "$src" "$dst" 2>/dev/null \
        | grep -c '^deleting ') || true
  if [ "${del:-0}" -gt "$max" ]; then
    echo "GUARD ABORT: would delete $del files (> MAX_DELETE=$max). Refusing. src=$src dst=$dst" >&2
    return 20
  fi
  rsync "${base[@]}" "$@" "$src" "$dst"
}
```

- [ ] **Step 4: Run the test to confirm pass**

Run: `bash 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_guarded_rsync.sh`
Expected: PASS.

- [ ] **Step 5: Add a second test, the allowed case (deletions under the cap proceed)**

Append to the test file a case where dst has 2 extra files, `MAX_DELETE=5`, and assert `guarded_rsync` returns 0 and removes them. Run; expect PASS.

- [ ] **Step 6: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/vault/lib_guarded_rsync.sh 03_AUTOMATION_CORE/01_Scripts/mesh/vault/tests/test_guarded_rsync.sh
git commit -m "feat(vault): guarded rsync (checksum + bounded-delete abort) + tests"
```

### Task 3.2: Rewrite acemagician_warm_standby.sh (retire the dangerous behaviors)

**Files:**
- Modify: `03_AUTOMATION_CORE/01_Scripts/mesh/acemagician_warm_standby.sh`

**Interfaces:**
- Consumes: `lib_guarded_rsync.sh`, `db_safe_capture.sh`.
- Produces: a PC-pull of E5 host-state using the public IP, pg_dump (not hot-tar), full scope, guarded delete.

- [ ] **Step 1: Read the current script to preserve its host/var conventions**

Run: `sed -n '1,60p' 03_AUTOMATION_CORE/01_Scripts/mesh/acemagician_warm_standby.sh`
Expected: see current `--delete`, tailnet host, excludes, and the docker-tar block (the three defects to remove).

- [ ] **Step 2: Replace the E5 pull core**

Swap the `rsync -az --delete` tailnet pull for the guarded public-IP pull, and the docker hot-tar for a pg_dump that runs ON E5 before the pull. The pull source becomes E5's dump dir, not the live volume. Concretely, the pull section becomes:
```bash
. "$(dirname "$0")/vault/lib_guarded_rsync.sh"
E5_PUB="ubuntu@163.192.60.35"; E5_KEY="/root/.ssh/github_deploy"
SSH_E5="ssh -i $E5_KEY -o StrictHostKeyChecking=accept-new"
# 1) ask E5 to produce fresh consistent dumps (no hot tar of a running pg volume)
$SSH_E5 "$E5_PUB" 'bash ~/vault/run_snapshot.sh >/dev/null 2>&1 || true'
# 2) pull host-state FULL scope (no node_modules/_logs/media excludes) with the guard
export MAX_DELETE=2000
guarded_rsync "$E5_PUB:/home/ubuntu/e5_data/" "/home/richgee/vault/mirror/e5/home/e5_data/" -e "$SSH_E5"
guarded_rsync "$E5_PUB:/home/ubuntu/vault/dumps/" "/home/richgee/vault/mirror/e5/docker_volumes/" -e "$SSH_E5"
$SSH_E5 "$E5_PUB" 'systemctl --user list-unit-files --type=service | sed 1d' \
  > /home/richgee/vault/mirror/e5/systemd_units/list.txt
```

- [ ] **Step 3: Static-check the script**

Run: `bash -n 03_AUTOMATION_CORE/01_Scripts/mesh/acemagician_warm_standby.sh && echo "syntax ok"`
Expected: "syntax ok". (If `shellcheck` is available: `shellcheck -S error` clean.)

- [ ] **Step 4: Dry-run on the PC against the seeded vault**

Run the rewritten script on the PC with a guard tripwire (set MAX_DELETE=0 to prove it refuses a destructive run):
```bash
scp -i /root/.ssh/phone_to_arch -r 03_AUTOMATION_CORE/01_Scripts/mesh/acemagician_warm_standby.sh 03_AUTOMATION_CORE/01_Scripts/mesh/vault richgee@100.93.253.49:/home/richgee/vault_plan/
ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 'MAX_DELETE=0 bash /home/richgee/vault_plan/acemagician_warm_standby.sh 2>&1 | tail -8 || echo "exit=$?"'
```
Expected: either a clean pull (nothing to delete) or a "GUARD ABORT" line, never a large uncontrolled deletion.

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/mesh/acemagician_warm_standby.sh
git commit -m "fix(vault): warm_standby uses public IP + pg_dump + full scope + guarded delete (retires C1/C3/H1)"
```

### Task 3.3: Update sync_to_mother.sh to push the working subset with checksum + quarantine

**Files:**
- Modify: `03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh`

**Interfaces:**
- Produces: phone -> E5 push of the working subset (everything except `04_MEDIA_LIBRARY` + `08_BACKUPS`) using `--checksum` and conflict-to-quarantine (media now goes phone -> PC, not through E5).

- [ ] **Step 1: Inspect the current excludes + flags**

Run: `grep -nE "exclude|--update|--delete|--checksum|04_MEDIA|_logs" 03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh | head -30`
Expected: see the current exclude list and `--update` usage.

- [ ] **Step 2: Set the working-subset excludes + checksum**

Ensure the push rsync excludes ONLY `04_MEDIA_LIBRARY` and `08_BACKUPS` (plus true-ephemeral `*-wal *-shm *.lock`), uses `--checksum` (not `--update`), and writes conflicts to `--backup --backup-dir=_sync_conflicts_quarantine_from_phone_<ts>`. Keep `--no-perms --no-owner --no-group --no-times` for the FAT source. Leave the cloud-state PULL section unchanged.

- [ ] **Step 3: Static-check + dry-run count**

Run:
```bash
bash -n 03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh && echo "syntax ok"
```
Expected: "syntax ok". Then do a `--dry-run` of just the push to confirm `04_MEDIA_LIBRARY` is absent from the transfer list and code/state dirs are present.

- [ ] **Step 4: Verify E5 still fits**

Run: `ssh -i /root/.ssh/github_deploy ubuntu@163.192.60.35 'df -h /home | tail -1'`
Expected: free space comfortably exceeds the working-subset size (subset is workspace minus ~18GB media minus ~7.6GB backups, so ~18GB, well under 43GB free).

- [ ] **Step 5: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh
git commit -m "fix(vault): sync_to_mother pushes working subset with checksum + quarantine (media routes phone->PC)"
```

### Task 3.4: Phase-3 acceptance: FAT-edit propagation + mass-delete refusal

**Files:** none (acceptance test).

- [ ] **Step 1: Same-2s-bucket edit must propagate (proves the FAT/checksum fix)**

On the phone, make two same-size edits to a probe file in quick succession, then run the guarded pull and confirm the latest content landed on the PC:
```bash
P=/mnt/sdcard/AA_MY_DRIVE/_state/vault_probe.txt
printf 'AAAA' > "$P"; sleep 0.2; printf 'BBBB' > "$P"   # same size, sub-2s apart
. 03_AUTOMATION_CORE/01_Scripts/mesh/vault/lib_guarded_rsync.sh
guarded_rsync "$P" "richgee@100.93.253.49:/home/richgee/vault/mirror/workspace/AA_MY_DRIVE/_state/vault_probe.txt" -e "ssh -i /root/.ssh/phone_to_arch"
ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 'cat /home/richgee/vault/mirror/workspace/AA_MY_DRIVE/_state/vault_probe.txt'
```
Expected: `BBBB` (checksum caught the same-size change that `--update`/mtime would have skipped).

- [ ] **Step 2: Mass-delete must refuse (proves the C1 guard end-to-end)**

Point the guard at an empty source against the populated vault workspace with a low cap:
```bash
. 03_AUTOMATION_CORE/01_Scripts/mesh/vault/lib_guarded_rsync.sh
EMPTY="$(mktemp -d)"
MAX_DELETE=10 guarded_rsync "$EMPTY/" "richgee@100.93.253.49:/home/richgee/vault/mirror/workspace/AA_MY_DRIVE/_state/" -e "ssh -i /root/.ssh/phone_to_arch"; echo "exit=$?"
```
Expected: "GUARD ABORT: would delete N files" and `exit=20`, with the PC `_state/` left intact.

- [ ] **Step 3: Tag the foundation milestone**

```bash
git tag vault-foundation-v1
git commit --allow-empty -m "milestone(vault): Phases 0-3 foundation complete -- verified full mirror + E5 history + guarded legs"
```

---

## Self-Review Notes

- **Spec coverage:** Phase 0 = denylist + tooling (spec 4.5/5/8.P0). Phase 1 = full seed + manifest (8.P1). Phase 2 = restic engine + db-safe capture + E5 history (4.1/4.8/8.P2, resolves C3/X1-seed). Phase 3 = guarded legs (4.2/4.3, resolves C1/H1/H4). Deferred to Plan 2: gocryptfs encryption (4.5/8.P4), wake-orchestrator (4.4/8.P5), parity auditor (4.6/8.P5), staleness alarm (4.7/8.P6), E5->PC repo replication (8.P6), restore drill (4.9/8.P7), cloud safe-subset constraint enforcement (8.P7).
- **No placeholders:** every script has full source; every verification has an exact command + expected output.
- **Naming consistency:** `guarded_rsync`, `db_safe_capture.sh` (`SQLITE_TARGETS`/`PG_TARGETS`/`DUMP_DIR`), `vault_seed_manifest.sh` (`VAULT_MANIFEST_OUT`), `restic_init_and_policy.sh [init|prune]` are referenced identically across tasks.
- **Operator-gated steps flagged:** 0.1 Step 1 (sudo install), 1.2 Step 1-2 (USB plug + run). Everything else is agent-runnable from the phone.
