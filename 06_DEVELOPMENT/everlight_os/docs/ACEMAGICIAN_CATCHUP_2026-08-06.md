# AceMagician Catch-Up Export, 2026-08-06

**Generated:** 2026-08-06, 12:15 PM PT, from the phone (`/mnt/sdcard/AA_MY_DRIVE`, the source of truth).
**Audience:** the Claude/Lucrex agent running on the AceMagician PC (Arch Linux, user `richgee`, tailnet `100.93.253.49`, workspace `/home/richgee/AA_MY_DRIVE`, global config `/home/richgee/.claude`).
**Purpose:** the PC has been powered off for roughly three months. This file is the delta: what the PC does not have, why, and how to get it.

> **Read this first, act second.** Section 1 is the situation. Section 2 is the one-shot catch-up. Sections 3 through 7 are the detailed inventory. Section 8 is what you must NOT do.

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
