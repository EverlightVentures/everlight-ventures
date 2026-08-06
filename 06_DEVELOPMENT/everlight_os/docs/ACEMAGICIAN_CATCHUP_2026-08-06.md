# AceMagician Catch-Up Export, 2026-08-06

**Generated:** 2026-08-06, 12:15 PM PT, from the phone (`/mnt/sdcard/AA_MY_DRIVE`, the source of truth).
**Audience:** the Claude/Lucrex agent running on the AceMagician PC (Arch Linux, user `richgee`, tailnet `100.93.253.49`, workspace `/home/richgee/AA_MY_DRIVE`, global config `/home/richgee/.claude`).
**Purpose:** the PC has been powered off for roughly three months. This file is the delta: what the PC does not have, why, and how to get it.

> **Read this first, act second.** Section 0 is the landmines. Section 1 is the situation. Section 2 is the one-shot catch-up. Sections 3 through 7 are the detailed inventory. Section 8 is what you must NOT do.

---

## 0. Landmines, resolve these before you sync anything

The doctrine on disk is **three generations layered on top of each other**, two still wired and firing, and the newest one (which retires the middle one) was never implemented. These are the specific traps, each verified against the live filesystem today, not read out of a doc.

### 0.1 The workspace path is genuinely ambiguous and it gates everything

`03_AUTOMATION_CORE/01_Scripts/mesh/MESH_PLAN.md:169-171`, open decision #4, verbatim and still unresolved:

> "**Two workspace copies on the PC**, `/AA_MY_DRIVE` (git root) and `/home/richgee/AA_MY_DRIVE` are *different* directories. Pick one canonical, reconcile the other, before wiring PC sync, otherwise sync ping-pongs."

The scripts split down the middle. `/AA_MY_DRIVE` is assumed by `mesh/hive_hosts.env:43-44` and `docs/REMOTE_WORKFLOW.md`. `/home/richgee/AA_MY_DRIVE` is assumed by `claude_sync_acemagician.sh:41`, `sync_on_reconnect.sh:43`, `install_acemagician_triggers.sh:31`, `setup_arch_pc.sh:34`. A third opinion, `TRI_DEVICE_VAULT_DESIGN.md:28`, measured `/home/richgee/AA_MY_DRIVE` at 31 GB / 117k files and called it *"stale and incomplete (missing media), confirms the false-full-picture risk."*

**Your first job on the PC is to run `ls -la /AA_MY_DRIVE /home/richgee/AA_MY_DRIVE` and report both back before syncing.** Do not pick one on your own. If you sync into the wrong one you create a second divergent tree on the same disk.

### 0.2 The Syncthing cron would have held the PC awake for 6 hours (FIXED today)

`sync_finisher.sh` runs from phone cron every 5 minutes. Its own header: *"the PC acknowledges by waking its Syncthing + blocking sleep for the transfer window,"* with `PC_ACK_REFRESH=5 # keeps PC awake` and a 6-hour cap.

But `TRI_DEVICE_VAULT_DESIGN.md:151-154` retired the Syncthing leg in favour of rsync-on-wake, and the 2026-06-19 hardware audit confirmed **syncthing is not installed on the PC**. Reachable but incapable is the worst state: the loop enters, holds `systemd-inhibit` against sleep, and polls a completion percentage that can never rise.

**Fixed 2026-08-06.** A `pc_has_syncthing()` readiness gate now sits between the reachability check and the transfer loop. If the PC has no syncthing binary the script logs loudly and exits 0 instead of camping on the machine. Liveness is not readiness; the original only checked the former.

### 0.3 Doctrine says one git repo, reality is another

| Source | Repo | Branch |
|---|---|---|
| `MESH_PLAN.md:22` and `hive_hosts.env:47-48` | `aa-my-drive.git` | `main` |
| `PC_TRANSFER_GUIDE.md:11-13` | `everlight-ventures.git` | `server-auth-blackjack` |
| `LUCREX_PC_BOOTSTRAP.html:361` | `everlight-ventures.git` | `everlightventures.io` |
| `setup_arch_pc.sh:35` | `everlight-ventures.git` | default |
| **Measured on the phone today** | **`everlight-ventures.git`** | **`solano-live-desk`** |

Trust the measured row. The remote is `git@github.com:EverlightVentures/everlight-ventures.git`, verified by `git remote -v`. Every doc that says `aa-my-drive` is stale.

### 0.4 An auto-install fires within 2 minutes of the PC answering SSH

Phone cron runs `device_update_runner.sh` every 2 minutes. It scp's any `.sh` from `03_AUTOMATION_CORE/04_PendingUpdates/acemagician/` to the PC, executes it, and moves it to `_done/`. **One task has been queued since 2026-05-13: `install_open_webui.sh`** (Open WebUI on port 2800, user service, Linger).

This is intentional, per the auto-install HARD LAW ("never tell Rich to run X manually"). Do not run it by hand, and do not be surprised when it fires. Watch `03_AUTOMATION_CORE/04_PendingUpdates/_logs/runner.log`.

### 0.5 The Slack notification path was dead for the life of the script (FIXED today)

`claude_sync_acemagician.sh` `slack_ping()` had two independent bugs, and because the function returns 0 on any miss, both failed silently:

1. Read the token from `${PHONE_WORKSPACE}/03_Credentials/.env`. That directory does not exist; the real one is `03_AUTOMATION_CORE/03_Credentials/`.
2. Looked for `SLACK_BOT_TOKEN_WARROOM`. The `.env` actually defines `SLACK_WARROOM_TOKEN`.

**No sync has ever posted to `#deploy-log`.** Both fixed 2026-08-06, with a fallback to `SLACK_BOT_TOKEN`. Verified the token now resolves (`xoxb-`, 58 chars). Note `setup_arch_pc.sh:297,364` carries the same wrong path in its `sync_creds_from_phone` alias, so that alias copies nothing either. **Not yet fixed, it needs the path decision from 0.1 first.**

### 0.6 Do not run the warm-standby script

`mesh/acemagician_warm_standby.sh:57` runs `rsync -az --delete` over the tailnet, excludes `_logs/` and `__pycache__/` from a supposed *full-state* capture, and hot-tars a **live Postgres volume**. Its own successor design, `TRI_DEVICE_VAULT_DESIGN.md:288-291`, names the file specifically: *"a corruption amplifier, scope-incomplete, and a producer of unrestorable DB artifacts."* The rewrite is specified but was never applied. `MESH_PLAN.md:192` still tells you to run it. Do not.

### 0.7 `PC_TRANSFER_GUIDE.md` will build you a broken SSH config

Lines 69-70 set `Host oracle-e5 / HostName 129.159.38.250`. **That box was terminated 2026-04-30.** Line 121 curls it, line 134 calls it "always running." The same guide tells you to expect `n8n` and `hive-django` up; n8n is PARKED and Django is DEFERRED to Phase 7. Its agent-count check ("should be 85") disagrees with every other source (79 / 94 / 119 / 120). Treat that guide as archive, not instruction.

`MIGRATION_CHECKLIST.md`, `START_HERE.md` and `QUICK_COMMANDS.md` are the January 2026 file-reorg plan (Proton Drive, GPG vault, `A_Rich/` tree). None of it touches the PC and Proton is superseded by Vaultwarden. Archive too.

### 0.8 The reverse leg (PC pulls from phone hourly) is not wired

`docs/REMOTE_WORKFLOW.md:51-55` is honest about it: *"AceMagician auto-pull side: NOT YET WIRED... the auto-push timer only PUSHES."* `SERVICE_TIERS.md:71` describes the `:17` hourly pull as though it exists. It does not; there is only a `.template`.

Before installing it, check its SSH target. The phone's Termux `sshd` listens on **8022**, not 22, and runs as an Android app user, not root. Verify the template's port and user against that or the hourly pull will fail its handshake every hour and exit 0 silently.

---

## 1. Situation

| Fact | Value |
|---|---|
| Last successful phone/PC sync | **2026-05-08** (`03_AUTOMATION_CORE/logs/claude_sync_20260508.log`) |
| Drift window | **~90 days** |
| Phone workspace total | **46 GB** |
| Files on phone (excl. `.git`, `node_modules`, `__pycache__`) | **157,811** |
| Files tracked by git | **11,261 (7.1%)** |
| **Files git can never deliver** | **~146,550 (92.9%)** |
| `.git` dir size | 1.9 GB |
| Unpushed commits | 2 |
| Modified tracked files (uncommitted) | 22 |
| Untracked paths | 12 |
| Pending sync-queue entries | 7 |

### The core problem

Git is **not** the sync. `.gitignore` in the workspace root is roughly 200 lines of deliberate exclusions accumulated over months. Everything below is invisible to git by design and has exactly one delivery path, the tailnet:

```
04_MEDIA_LIBRARY/   18 GB     08_BACKUPS/          9.1 GB
05_PERSONAL/        1.7 GB    _logs/               1.5 GB
07_STAGING/         717 MB    Alley Kingz assets   ~1.5 GB
every *.env, every credential, every *.sqlite, all venvs, all media
```

`git pull` gets you code and docs. It gets you **none** of the above.

### Current blocker (as of this writing)

The tailnet is down **on the phone side**, not the PC's. Verified: `ssh e5-mother` (100.125.115.95) also times out, and general internet works (github returns 200). So Tailscale needs to come up on the Android side before any rsync path opens. Do not diagnose this as a PC fault.

---

## 2. Catch-up sequence, run these in order

### Step 0, prerequisites on the PC

```bash
sudo tailscale up                 # confirm the PC is on the tailnet
tailscale status | grep -i ace    # confirm its own IP is 100.93.253.49
ping -c2 100.125.115.95           # e5-mother, proves tailnet routing works
```

### Step 1, git first (cheap, gets you 7% but it is the important 7%)

```bash
cd ~/AA_MY_DRIVE
git fetch --all --prune
```

> **CRITICAL: do not check out `main`.** `main` is frozen at **2026-04-08** (`4e6319c`). It is four months stale and does not represent current work. The live branch is **`solano-live-desk`** (`d40da78`, 2026-07-29).

```bash
git checkout solano-live-desk
git pull origin solano-live-desk
```

Other branches with meaningful recent work, if you need them:

| Branch | Head | Date |
|---|---|---|
| `solano-live-desk` | `d40da78` | 2026-07-29, **active** |
| `token-economics-os` | `5c05640` | 2026-06-29 |
| `mgn-pos-restore` | `a733a5f` | 2026-06-26 |
| `lucrex-os-engine` | `6281826` | 2026-06-20 |
| `coverforge-build` | `a85b179` | 2026-06-15 |
| `bj-finish` | `07ee6a2` | 2026-06-14 |
| `everlightventures.io` | `a8c47fe` | 2026-06-01 |
| `main` | `4e6319c` | 2026-04-08, **stale, ignore** |
| `master` | `103de18` | 2026-03-15, **stale, ignore** |

### Step 2, the doctrine sync (Claude config, agents, skills)

Run **from the phone**, not the PC (the script lives on the phone and pushes outward):

```bash
bash 03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh --status   # confirm reachable
bash 03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh --diff     # dry run, review
bash 03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh --full     # sync + notepad
```

Scope of that script, from its own header: `.claude/{agents,commands,hooks,modes,skills,memory,guard}`, `feedback_*.md`, `sync_config.json`, plus dotfile extras (`.zshrc`, emacs lisp, starship, fastfetch) and `_state/AGENT_MAILBOX.md`. Conflict policy is newer-mtime-wins, with the loser preserved under `.sync_conflicts/`.

Note the script targets the PC's **global** `~/.claude/`, not the workspace `.claude/`. That is deliberate, because `claude` on the PC reads the global dir.

### Step 3, the heavy non-git payload (manual rsync, nothing automates this)

None of these are in git. Pull them over the tailnet in priority order:

```bash
# P0, secrets. 96 KB, blocks everything else from running.
rsync -avz --progress \
  <PHONE>:/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/ \
  ~/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/

# P0, the NP notebook catalog (brand new work, see section 3)
rsync -avz <PHONE>:/mnt/sdcard/AA_MY_DRIVE/_state/np/   ~/AA_MY_DRIVE/_state/np/

# P1, live state
rsync -avz <PHONE>:/mnt/sdcard/AA_MY_DRIVE/_state/      ~/AA_MY_DRIVE/_state/

# P2, personal (1.7 GB)
rsync -avz <PHONE>:/mnt/sdcard/AA_MY_DRIVE/05_PERSONAL/ ~/AA_MY_DRIVE/05_PERSONAL/

# P3, Alley Kingz binary assets (~1.5 GB, see section 5)
# P4, media library (18 GB), only if the PC actually needs a media role
```

The phone is source of truth; the PC receives.

### Step 4, rebuild what should never be copied

Do **not** rsync venvs or `node_modules`. Rebuild them. Eight venvs exist on the phone:

```
09_DASHBOARD/aa_dashboard/.venv
09_DASHBOARD/master_dashboard/.venv
03_AUTOMATION_CORE/01_Scripts/crypto_bot/.venv
06_DEVELOPMENT/coverforge/render/.venv
06_DEVELOPMENT/everlight_swarms/upstream/openswarm/.venv
01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/operations_MGN_v8/.venv
01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/.venv
08_BACKUPS/archived_prototypes/crypto_bot/.venv   # archived, skip
```

18 `requirements*.txt` files exist across the tree. The PC is a real Arch box with no proot limits, so unlike the phone it *can* `npm install` and compile native modules. This is the machine to do heavy builds on.

### Step 5, toolchain bootstrap if anything is stale

`03_AUTOMATION_CORE/01_Scripts/setup_arch_pc.sh` is idempotent and safe to re-run. It refuses to run as root; run it as `richgee`. What it installs:

```bash
sudo pacman -Sy --needed --noconfirm git openssh rsync curl wget jq \
  python python-pip python-virtualenv nodejs npm base-devel tailscale
npm config set prefix "$HOME/.npm-global"      # PATH gets ~/.npm-global/bin
curl -fsSL https://claude.ai/install.sh | bash # fallback: npm i -g @anthropic-ai/claude-code
npm install -g @google/gemini-cli @openai/codex
```

Python venv at `$EL_HOME/.venv`: `requests, google-auth, google-auth-oauthlib, google-api-python-client, slack-sdk, anthropic, openai, google-generativeai, python-dotenv, rich, httpx, pyyaml`. Keep venvs inside the workspace, never on the root filesystem.

**Confirmed present** as of the 2026-06-19 audit: rsync 3.4.2, rclone 1.74, sqlite3 3.53, pg_dump 18, docker 29, `systemd --user` with Linger. **Confirmed missing:** restic, borg, kopia, b3sum, syncthing. `sudo` needs a password, so any install is operator-gated.

Hardware, for planning: ACEMAGICIAN S3A, Ryzen 7 8745HS 8C/16T, Radeon 780M (**no NVIDIA, no CUDA**), 32 GB DDR5, 1 TB NVMe. Vault disk `nvme0n1p3` btrfs 953 G with 333 G free, **no LUKS**.

---

## 2.5 What the PC is supposed to run

Bind law applies to every one of these: `127.0.0.1` unless `EV_BIND=0.0.0.0` is set deliberately.

| Service | Port | Status |
|---|---|---|
| `blinko-lite.service` (user) | 1111 | |
| `langfuse.service` (+ postgres/clickhouse/redis/minio) | 3100 web, rest loopback | |
| `homarr` container | 7575 | |
| `n8n` container | 5678 | doctrine says PARKED, do not build on it |
| `open-webui.service` (user, Linger) | 2800 | **queued to auto-install, see 0.4** |
| `sync-conflict-resolver.timer` + udev rule | n/a | via `install_acemagician_triggers.sh` |
| `~/bin/claude_sync_pull.sh` cron `17 * * * *` | n/a | **not wired, see 0.8** |
| `syncthing-everlight.service` | 8384 | **retired by doctrine, binary absent** |
| `lucrex-auto-push.timer` (git push every 5 min) | n/a | |
| `lucrex-email-triage.service` (Gmail poll) | n/a | |
| MCP fleet election (`mcp_elect.sh`, cron `*/2`) | 3101-3107 | PC is **priority 2** |
| Hermes browser harness (docker + headless Chrome) | n/a | host LOCKED to this PC since 2026-05-19 |

`install_acemagician_triggers.sh` installs a udev rule on Samsung vendor `04e8` (products 6860/6863/6865) so plugging the phone in by USB triggers the conflict resolver, plus an hourly timer. Run it once as root on the PC. It has an undo block at the bottom.

---

## 2.6 Hand-carry list, things no sync will ever move

Every sync path excludes secrets by design (`*.token`, `*.key`, `*credentials*`, `.env*`). These must move by deliberate rsync or by hand:

| Item | Phone path | PC destination |
|---|---|---|
| Master `.env` (5.7 KB, 2026-06-11) | `03_AUTOMATION_CORE/03_Credentials/.env` | same relative path, `chmod 600` |
| Hive Mind SaaS `.env` | `06_DEVELOPMENT/hivemind_saas/backend/.env` | same |
| Solano Live Desk `.env` | `06_DEVELOPMENT/solano_live_desk/.env` | same |
| Oracle Micro key | `/root/.ssh/oracle_key.pem` | `~/.ssh/`, 600 |
| GitHub deploy key | `/root/.ssh/github_deploy` | `~/.ssh/`, 600 |
| PC to phone key | must exist as `~/.ssh/arch_to_phone` on the PC | matching pubkey already in the phone's `authorized_keys` |
| Claude Code auth | **not syncable** | re-auth on the PC: `claude login` |
| restic repo password | by design lives outside every mirrored path | Vaultwarden + a printed offline copy |

Also excluded from `~/.claude/` on purpose and never to be copied: `sessions/`, `history.jsonl`, `telemetry/`, `statsig/`, `cache/`, `paste-cache/`, `projects/`, `plans/`, `settings.local.json`, `.credentials.json`, `tasks/`, `todos/`, `debug/`.

**Cloud denylist** (never reaches any cloud remote, so never reaches the PC by a cloud path): all `*seed_phrase*` / `*_sp.py` / `SEED_VAULT*`, `03_Credentials/**`, `*.pem`, `*.key`, `.env*`, `leads_db*`, all `*_prospects.csv`, `_logs/enrichment/**`, `_state/TN_TOP_TARGETS_*.json`, and the MMA medical paperwork.

---

## 2.7 Conflict backlog waiting on the PC

`sync_conflict_resolver.sh` archives, never deletes, into `08_BACKUPS/sync_conflicts_archive_<date>/`. Run `--dry-run` first, per verify-before-delete doctrine. Known backlog:

- 128 files in `.claude/.sync_conflicts/20260508T114933Z/`
- 36 files / 10.7 MB in `_sync_conflicts_quarantine_20260513/`
- **~1.7 GB in `_sync_conflicts_quarantine_20260514_110205/`**, needs a manifest pass before any bulk archive

Dashboard sqlite conflicts are deliberately skipped for manual row-count comparison. Do not auto-resolve those.

---

## 3. Uncommitted work on the phone (git will NOT carry this until it is committed)

### 2 unpushed commits

```
81e5a88  workflow output: 8-feature scaffolds + partial wiring (UNVERIFIED, reference only)
2281322  Public watchtower + secret scrub + dashboard upgrades (squashed)
```

### 22 modified tracked files

Mostly runtime churn (pipeline logs, heartbeats, dashboard JSON), but four carry real content:

- `_state/AGENT_MAILBOX.md`, the cross-agent coordination board, 432 KB
- `_state/DECISION_LOG.md`, decision reasoning
- `.claude/settings.json`
- `01_BUSINESSES/Everlight_Ventures/Wholesale/tn_deal_tracker.json` plus `_digest.md`

The rest: `wholesale_agent/pipeline/*.jsonl` (5 files), `09_DASHBOARD/reports/*.json` (4), `_state/moltbook/*`, `_state/heartbeats/*`, `_state/sync_queue.jsonl`, `intel_center/cache/live_log.sqlite`.

### 12 untracked paths, real new work, none of it exists anywhere but the phone

| Path | What it is |
|---|---|
| `.claude/skills/np_notebook/` | NP (Notebook Protocol) skill, created 2026-08-03 |
| `_state/np/` | **46 MB**: NP `catalog.db`, dedupe + rename manifests, spool, versions |
| `03_AUTOMATION_CORE/01_Scripts/phone_ops/` | 37 files touched in last 30 days |
| `03_AUTOMATION_CORE/01_Scripts/domain_ops/` | domain portfolio tooling |
| `03_AUTOMATION_CORE/01_Scripts/content_tools/resend_manager.py` | |
| `03_AUTOMATION_CORE/01_Scripts/mcp_health_monitor.py` | |
| `01_BUSINESSES/.../wholesale_agent/bounce_sweeper.py` | Resend bounce suppression |
| `01_BUSINESSES/.../Broker_OS/RESEND_AUDIT_2026-05-18.md` | |
| `01_BUSINESSES/.../Wholesale/np_deal_log.md` | |
| `01_BUSINESSES/.../ai_receptionist/_pending_external_launch/11_EMAIL_1_TEMPLATES.md` | |
| `06_DEVELOPMENT/everlight_os/hive_mind/HIVE_ACTION_LAYER.md` | |
| `06_DEVELOPMENT/everlight_os/hive_mind/RESUME_NEXT_SESSION.md` | session handoff |

### 2 git worktrees, outside the repo dir, easy to miss

```
/mnt/sdcard/AA_MY_DRIVE_worktrees/buyers      4e6319c [worktree/buyer-list]
/mnt/sdcard/AA_MY_DRIVE_worktrees/wholesale   4e6319c [worktree/wholesale-build]
```

Both sit at the April `main` commit. Low priority, but they exist, and a naive workspace copy would miss them entirely.

---

## 4. Where the last 30 days of work actually went

2,510 files modified in the last 30 days. By area:

| Area | Files | Notes |
|---|---|---|
| `01_BUSINESSES/.../Alley_Kingz` | **639** | dominant effort; assets largely gitignored |
| `09_DASHBOARD` | 1,121 | almost all generated reports, gitignored, regenerable |
| `01_BUSINESSES/.../Broker_OS` | 67 | wholesale pipeline |
| `06_DEVELOPMENT/solano_live_desk` | ~110 | the active branch's project |
| `.gemini/` plus `.codex/` | 326 | doctrine-compiler mirrors, regenerated hourly, **do not hand-sync** |
| `03_AUTOMATION_CORE/01_Scripts/phone_ops` | 37 | untracked, new |
| `06_DEVELOPMENT/lucrex_command_deck` | 24 | |

**Read that table carefully.** The 1,121 dashboard files and 326 `.gemini`/`.codex` files are regenerated output, not source. Syncing them is wasted bandwidth and will create conflicts. The `.gitignore` already excludes them for exactly this reason.

---

## 5. The gitignored buckets, sized

| Path | Size | Verdict |
|---|---|---|
| `04_MEDIA_LIBRARY/` | 18 GB | 18 GB of it is `Music/`. Sync only if the PC needs a media role. |
| `08_BACKUPS/` | 9.1 GB | Archive. `np_dedupe_20260806/` (1.5 GB) is from **today**. |
| `05_PERSONAL/` | 1.7 GB | `00_Documents` is 1.5 GB. Notebook plus security notebook live here. |
| `_logs/` | 1.5 GB | `sdcard_sync.log` alone is 618 MB, `hive.db` 476 MB. **Do not sync.** Rotate. |
| `07_STAGING/` | 717 MB | Inbox / unsorted. |
| `06_DEVELOPMENT/xlm_bot/logs/` | 173 MB | XLM is PARKED. Skip. |
| `_state/cloud_mirror/` | 19 MB | Holds secrets, chmod 600. Handle like credentials. |
| `06_DEVELOPMENT/trading_agents/` | 11 MB | Embedded git repo, independent. Clone separately if needed. |
| `03_AUTOMATION_CORE/03_Credentials/` | 96 KB | **Highest value per byte in the entire workspace.** |

### Alley Kingz binary asset trees (gitignored 2026-07-28, ~1.5 GB)

```
**/e5_art_backup/   **/_bg_backup/   **/_arttest/   **/_ak_rollback_local/
Alley_Kingz/ecosystem/game/assets/{story,models,icons,sprites,portraits,
                                   avatar,bosses,vendor,cosmetics,interiors,hub}/
Alley_Kingz/ecosystem/_state/
```

These were excluded because a blind `git add` would blow GitHub's 100 MB ceiling. Per the `.gitignore` header: *GitHub is logic/code/docs only; assets live on Nextcloud plus e5.*

---

## 6. Credentials inventory, the P0 payload

`03_AUTOMATION_CORE/03_Credentials/`, 96 KB, 16 files, none in git:

```
.env                        5.7 KB   2026-06-11   <- primary
.env.bak.20260611-1013      4.3 KB   2026-06-11
.env.bak.20260503-2131      3.8 KB   2026-05-04
.env.bak.preplymkt          4.0 KB   2026-05-29
kalshi.env / kalshi_private_key.pem                <- Kalshi is LIVE and funded
hetzner_token.env / hetzner_proxy.env
odds_api.env
polymarket_wallet.addr / .key                      <- Polymarket dead in US
proton_pass_import.json     28 KB                  <- wallet seeds
RCLONE_CRYPT_RECOVERY.txt   1.6 KB                 <- backup chain recovery key
```

30 `.env` files exist workspace-wide, excluding examples and templates. The other notable ones:

```
./.env                                          (workspace root)
./06_DEVELOPMENT/solano_live_desk/.env           <- active project
./06_DEVELOPMENT/hivemind_saas/backend/.env
./_state/cloud_mirror_secrets/e5_data.env
./03_AUTOMATION_CORE/01_Scripts/mesh/hive_hosts.env
```

**Two standing security notes carried forward:**

1. `chmod` does not stick on the sdcard FUSE mount (600 reverts to 660). File permissions are not real protection on the phone. The PC's ext4 will hold permissions properly, so set them there.
2. `_state/moltbook/agent_keys.jsonl` was tracked in git until 2026-07-28. Those `moltbook_sk_*` keys are **already in git history** and should be treated as compromised until rotated. History rewrite plus rotation is an operator decision, not yours to make unilaterally.

---

## 7. Pending queue

`_state/sync_queue.jsonl` holds **7 entries**, oldest still-pending from **2026-07-28**. All are `file_replace` ops for `_state/AGENT_MAILBOX.md`, and the three most recent target `/home/ubuntu/AA_MY_DRIVE/`. That is the **e5-mother** path, not the PC's `/home/richgee/`. Two have `shipped_to: []` (never delivered), one shipped to `mother`.

Meaning: the queue is backed up against e5, not against the AceMagician. Draining it is a separate errand from this catch-up. Do not assume it will deliver anything to the PC.

`03_AUTOMATION_CORE/04_PendingUpdates/` has per-device staging folders (`acemagician/`, `phone/`, `ev-box/`, `oracle-micro/`, `_done/`, `_logs/`). Check `acemagician/` for anything queued for you specifically.

---

## 8. Do NOT do these

1. **Do not `git checkout main`.** It is four months stale. Use `solano-live-desk`.
2. **Do not run a blind `git add -A`.** A stale `.git/index.lock` once silently failed every commit for 16 days and let 2,201 files pile up. The `.gitignore` hardening from 2026-07-28 exists to prevent a repeat. Respect it, do not work around it.
3. **Do not sync `.gemini/{agents,skills,commands}` or `.codex/{agents,skills,commands}`.** They are compiler *outputs*, regenerated hourly by `hive_sync_v2.sh` from `.claude/` plus `LUCREX.md`. Syncing them creates phantom conflicts.
4. **Do not sync `_logs/`.** 1.5 GB of rotating logs. Nothing there is source.
5. **Do not sync venvs or `node_modules`.** Rebuild from `requirements.txt` / `package.json`.
6. **Do not commit any `.env`, key, or credential.** Policy was reversed on 2026-05-16: secrets move via tailnet/rsync, never git, even in a private repo.
7. **Do not treat the PC as a cron host yet** without checking `03_AUTOMATION_CORE/01_Scripts/install_acemagician_triggers.sh` first. Cron doctrine is e5-first, and duplicate crons across hosts cause double-sends on outbound email.
8. **Do not delete anything to reclaim space.** Standing rule: nothing gets reclaimed without a `memory_pipeline.ingest_before_delete()` pass, and there is a hard "no trash until Deal 1" hold in effect.
9. **Do not use `--mirror-from-pc` or `--mirror-to-pc`.** Those are `rsync --delete`. The PC has been off for three months, so its copy is the stale one; mirroring the wrong way destroys 90 days of work.
10. **Do not run `mesh/acemagician_warm_standby.sh`.** See 0.6. Its own successor design calls it a corruption amplifier.
11. **Do not follow `PC_TRANSFER_GUIDE.md`, `MIGRATION_CHECKLIST.md`, `START_HERE.md`, or `QUICK_COMMANDS.md`.** See 0.7. Dead hosts and a January file-reorg plan. This file supersedes them for PC catch-up purposes.
12. **Do not pick a workspace path on your own.** See 0.1. Report both directories back and let the operator decide.

---

## 9. Verification, run this on the PC when done

```bash
cd ~/AA_MY_DRIVE
echo "branch:     $(git rev-parse --abbrev-ref HEAD)   (want: solano-live-desk)"
echo "head:       $(git rev-parse --short HEAD)        (want: d40da78 or newer)"
echo "tracked:    $(git ls-files | wc -l)              (want: ~11261)"
echo "creds:      $(ls 03_AUTOMATION_CORE/03_Credentials/ 2>/dev/null | wc -l)  (want: 16)"
echo "np catalog: $(du -sh _state/np 2>/dev/null | cut -f1)  (want: ~46M)"
echo "personal:   $(du -sh 05_PERSONAL 2>/dev/null | cut -f1) (want: ~1.7G)"
tailscale status | head -5
```

Report the output back to the phone via `_state/AGENT_MAILBOX.md` so both sides agree on state.

---

*Source of truth: the phone at `/mnt/sdcard/AA_MY_DRIVE`. This export was generated by direct filesystem and git inspection on 2026-08-06, not from cached documentation. Every size and count above was measured, not estimated.*
