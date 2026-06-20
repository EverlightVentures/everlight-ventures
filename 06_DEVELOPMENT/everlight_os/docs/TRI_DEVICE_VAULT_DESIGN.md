# Tri-Device Vault: Phone -> E5 -> AceMagician Backup & Sync Design

**Status:** Approved design / spec (v1). Implementation plan to follow. No production code shipped yet.
**Date:** 2026-06-19 · **Owner:** Lucrex / Rich · **Host of record for the vault:** AceMagician PC

> The goal in the operator's words: AceMagician becomes a **complete physical backup** that holds
> **both** the phone's production workspace **and** everything needed to rebuild the E5 server,
> encrypted, versioned, and continuously *proven* equal to its sources, so that if the phone is lost
> **or** E5 goes down, the full picture is recoverable **from a device in the operator's possession**,
> not from the cloud.

---

## 0. Ground Truth (verified live on AceMagician 2026-06-19)

These facts were measured, not assumed, and they shaped the design:

| Fact | Value | Consequence |
|---|---|---|
| OS / kernel | Garuda Linux, 7.0.3-zen | Arch-family; `pacman`; `systemd --user` |
| Vault disk | `nvme0n1p3` **btrfs**, 953G, **333G free** | Big enough for the full 1:1 plus a deep restic repo |
| Encryption at rest | **NONE, disk is plaintext (no LUKS)** | Use a **gocryptfs container for secrets/PII/seeds**, not full-disk LUKS (would require reinstall) |
| RAM | 30 GB (20 GB free) | Snapshots/hashing are comfortable |
| `systemd --user` | available, **Linger=yes** | Wake-orchestrator runs as a user service, survives reboot, no login needed |
| Tailscale | up, `100.93.253.49` | Reachable from phone proot when Android TS VPN is routing |
| Already installed | rsync 3.4.2, rclone 1.74, sqlite3 3.53, **pg_dump 18**, docker 29 | Reuse |
| **Missing** | **restic, borg, kopia, b3sum, syncthing** | Phase-0 install list |
| Existing mirror | `/home/richgee/AA_MY_DRIVE` = 31G / 117k files | Stale + incomplete (missing media), confirms the "false full picture" risk |
| `_oracle_e5_recovery` | **absent** | The assumed E5 cold copy does not currently exist |
| sudo | **password-required** (not passwordless) | Installs run by the operator on the PC, not remotely |

**E5 disk reality (decisive):** E5 has only ~43 GB free, but the workspace is ~44 GB. **E5 physically
cannot hold the full media-inclusive workspace.** Therefore:

- **The AceMagician PC is the only machine that holds the true full 1:1** (incl. the 18 GB media library).
- **E5 holds the working subset** (code, DBs, `_state`, secrets, host-state) as the always-on hot copy
  and the second snapshot history.
- The complete, media-inclusive picture flows **phone -> PC directly**, not through E5.

---

## 1. North Star + the 3-2-1 Guarantee

AceMagician becomes a *self-proving, encrypted, versioned physical vault* holding the complete picture of
both the phone workspace and E5's host state, recoverable from the operator's own hand with **zero cloud
dependency**, and continuously proven equal to its sources by **content hash**.

**Copies that exist after this design:**

| Data class | Phone (origin) | E5 (working subset) | E5 restic repo | AceMagician mirror | AceMagician restic repo | Cloud crypt |
|---|---|---|---|---|---|---|
| Workspace incl. media + `_logs` | ORIGIN | subset live | **versioned (subset)** | **FULL live mirror** | **FULL versioned** | safe-subset only |
| E5 host state (e5_data, docker vols, units, secrets) | - | ORIGIN | **versioned** | live mirror | **versioned** | NEVER |
| PII + wallet seeds/keys | ORIGIN | live | **versioned** | live (**gocryptfs**) | **versioned (encrypted)** | **NEVER** |

**Recoverability:**
- **Phone lost** -> full workspace from PC mirror (current) or either restic repo (any point in time).
- **E5 down** -> host state from PC mirror + restic rebuilds E5; `failover_to_acemagician.sh` stands services up.
- **AceMagician dies** -> a **second independent snapshot history lives on E5**, so the vault disk dying is
  redundancy loss, **not data loss**.
- **Phone + AceMagician both die** -> E5 restic repo holds full history of the working set; decrypt with the
  Proton Pass recovery key or the printed offline copy.

This is genuine 3-2-1, not a single vault: **two independent snapshot repos (E5 + PC)** on two machines.

---

## 2. Architecture + Data Flow

```
        EDIT ORIGIN                              ALWAYS-ON PROD (small disk)
   +----------------------+                +-------------------------------+
   |  PHONE (Z Fold 7)    |                |   E5 (e5-mother, ARM, ~43G free)|
   |  /AA_MY_DRIVE ~44GB   |                |  e5_data, secrets, docker vols |
   |  FAT sdcard, no cron  |                |  units · systemd timers OK     |
   |  daemon loops only    |                |  +- snapshots WORKING SUBSET   |
   +---------+------------+                |     hourly -> E5 restic repo #1 |
             |                              +------+---------------+--------+
   (A) full push of WORKING SUBSET (fits 43G)      |               |
       sync_to_mother.sh over PUBLIC IP ----------->               | E5 host-state
       163.192.60.35:22 (fast)                      |               | pulled on wake
             |                                       |               |
   (B) FULL workspace incl. 18G media --------------+---------------+------+
       phone -> PC direct (PC pulls on wake)         |               |      |
             |                                        v               v      v
   +--------------------------------------------------------------------------+
   |   ACEMAGICIAN PC  (btrfs, 333G free, off-when-idle, Linger=yes)           |
   |                                                                            |
   |   WAKE-ORCHESTRATOR (flock singleton) when tailnet comes up:              |
   |     1. snapshot CURRENT vault -> PC restic repo   (BEFORE any pull)       |
   |     2. btrfs snapshot of /vault (free CoW safety net)                     |
   |     3. rsync-pull FULL workspace from phone (--checksum, guarded delete)  |
   |     4. rsync-pull E5 host-state (warm_standby, fixed)                     |
   |     5. replicate E5 restic repo -> PC  (2nd history)                      |
   |     6. PARITY AUDIT (3 pairwise content-hash diffs) -> publish roots      |
   |     7. report staleness ("I was N days behind phone / M behind E5")      |
   |                                                                            |
   |   gocryptfs (secrets/PII/seeds)  ·  restic repo #2  ·  full live mirror   |
   +--------------------------------------+-----------------------------------+
                                          | rclone crypt: SAFE-SUBSET ONLY
                                          v  (PII/seed denylist enforced)
                               +----------------------+
                               | Google / Proton crypt |  offsite copy, non-PII only
                               +----------------------+
```

**Always-on watcher = E5, not the vault.** A powered-off PC cannot alarm about being stale, so E5 owns the
staleness alarm and the monthly restore drill.

---

## 3. Vault Layout on AceMagician

```
/home/richgee/vault/                       (btrfs; secrets subtree is gocryptfs)
+- mirror/                                 # fast live 1:1
|  +- workspace/AA_MY_DRIVE/               # leg B: FULL phone workspace incl media + _logs
|  +- e5/                                  # leg from E5
|     +- home/                            # e5_data, ak_deploy, blinko_backups
|     +- docker_volumes/                  # pg DUMPS (not raw hot tars)
|     +- systemd_units/                   # unit files for failover
+- secrets.crypt/                          # gocryptfs CIPHERTEXT (.env, *.pem, tokens, seeds, raw PII)
|  +- (mounted at /vault/secrets only during the sync window, then unmounted)
+- restic/                                 # PC snapshot repo (encrypted, dedup, versioned)
+- restic_e5_replica/                      # pulled copy of E5's repo (2nd independent history)
+- parity/
|  +- manifests/<device>/<ts>.b3           # per-device content-hash manifests
|  +- roots/<ts>.json                      # 3 merkle roots + last-match timestamp
|  +- reports/<ts>.md                      # human one-screen diff
+- drills/<ts>/                            # restore-drill scratch (ephemeral)
+- quarantine/<date>/                      # conflict losers (NEVER delete, existing policy)
+- _state/
   +- seed_manifest.json                   # gates the first GREEN
   +- wake.lock                            # flock singleton
   +- last_wake.json                       # staleness beacon (posted to E5)
```

restic repo password/keyfile lives **outside every mirrored path** (systemd-creds + Proton Pass), never
beside its own ciphertext.

---

## 4. Components (each isolated: what / trigger / depends-on)

### 4.1 Snapshot engine: restic (on BOTH E5 and PC)
Content-addressed, encrypted, deduplicated point-in-time snapshots. Full scope on the PC (node_modules
included, dedup makes it cheap). Resumable (power-off just resumes) and immune to FAT mtime lies (content
addressed). **Retention = count/event-based, never pure wall-clock:** `keep-last 20, keep-daily 14,
keep-weekly 8, keep-monthly 12`, and never prune the last snapshot containing a path absent from source.
*Trigger:* E5 systemd timer (hourly + daily); PC wake-orchestrator steps 1 & 5. *New tool.*

### 4.2 Live-mirror sync: rsync (ownership unified on rsync; Syncthing retired)
Syncthing is **missing on the PC** and the red-team flagged Syncthing-vs-rsync delete wars. Decision:
**retire Syncthing; the PC pulls everything via rsync on wake.** The phone keeps Termux sshd up so the PC
can pull `/mnt/sdcard/AA_MY_DRIVE` when the phone is on the tailnet; if the phone is unreachable at wake, the
PC pulls the working subset from E5 and **queues the media leg** until the phone returns.
*Safety:* snapshot-BEFORE-pull is hard-sequenced; rsync runs `--checksum` (FAT-safe) `--partial
--append-verify --max-delete=500`; a mass-deletion event **aborts and alerts** instead of mirroring damage.

### 4.3 E5-rebuild pull: extends `mesh/acemagician_warm_standby.sh`
Pulls what's needed to rebuild E5 elsewhere: e5_data, secrets, **docker volumes as pg dumps**, systemd units.
Fixes the three current defects: switch to the **public-IP path** for big transfers, replace hot-tar of live
Postgres with `pg_dump`, and remove the full-scope excludes (media/_logs/node_modules). *Trigger:* wake step 4.

### 4.4 Wake-catchup daemon: NEW `mesh/vault_wake_orchestrator.sh`
Detects tailnet-join, runs the orchestrator sequence (snapshot -> btrfs-snap -> pull phone -> pull E5 ->
replicate E5 repo -> parity -> staleness report), and reports "I was N days behind." *Trigger:* `systemd --user`
path/network unit on the PC (Linger=yes makes it reboot-proof); singleton via `flock`.

### 4.5 Encryption layer: gocryptfs (secrets) + restic AES (repos)
Disk is plaintext btrfs, so **full-disk LUKS is out** (needs reinstall). Instead: a **gocryptfs container**
holds the secret/PII/seed subtree, mounted only during the sync window and unmounted after, so a stolen
powered-off PC yields no plaintext secrets. restic native AES covers both repos. rclone crypt covers the
offsite safe-subset. *Optional later:* migrate to full-disk LUKS on a planned reinstall.

### 4.6 Parity auditor: NEW `mesh/parity_audit.py` (content hash, not mtime)
`b3sum` manifest of every in-scope path per device -> one **merkle root** per device -> **three pairwise**
diffs (phone-E5, phone-PC, E5-PC, no transitivity assumption). Outputs only-on-X, hash mismatches, and the
3 roots + last-match timestamp. Never compares mtime/size (FAT lies). *Bonus:* btrfs `scrub` adds bit-rot
detection beneath the hash check.

### 4.7 Staleness alarm: NEW `mesh/vault_staleness_alarm.sh` (lives on E5)
E5 timer checks when the PC last posted a parity root / wake beacon; if > threshold (default **7 days**) it
fires `branded_slack.post_branded_alert()` to `#hive-alerts`. Wake clears it.

### 4.8 DB-aware capture: NEW `mesh/db_safe_capture.sh`
Never file-copies a live DB. Postgres -> `pg_dump`/`pg_dumpall` (via `docker exec`); SQLite (`blinko_lite.db`,
Django `db.sqlite3`, `hive.db`) -> `sqlite3 .backup` / `VACUUM INTO` (atomic, WAL-safe). Snapshot the dump.
Exclude live `-wal/-shm/.lock/*.pid/sockets` from the mirror (the only justified ephemeral excludes).

### 4.9 Restore-drill verifier: extends `mesh/failover_to_acemagician.sh --drill`
Monthly on E5: restore one random snapshot to scratch, open a restored DB and assert row counts, checksum a
file sample vs live, post PASS/FAIL to `#hive-alerts`. "Vault healthy" is claimable only as of the last GREEN
drill.

---

## 5. Encryption · Secrets · Cloud Boundary · Key Escrow

- **At rest:** gocryptfs for the secret/PII/seed subtree on the PC; restic AES for both repos. Secrets exist
  in plaintext only while the gocryptfs mount is up (sync window), then unmount.
- **In transit:** node-to-node over Tailscale/SSH/rsync only. Secrets **never via git**. Big/secret transfers
  over the public-IP SSH leg, detached (`setsid`/`nohup`, never self-`pkill`).
- **Cloud boundary:** ONE canonical PII/seed **denylist** (`config/cloud_denylist.txt`) sourced by *every*
  cloud-bound job (rclone `sdcard_sync_to_drive.sh`, future rsync-to-cloud, git pre-commit). Parity asserts no
  denylisted path appears in any cloud remote's manifest. "Encrypted by rclone" does not equal "allowed on
  Google", doctrine is *don't put it there at all*.
- **Key escrow, 2 independent decrypt locations:** restic supports multiple keys per repo. Provision distinct
  keys on **phone**, on **E5**, and a **recovery key held only in Proton Pass** + a **printed offline copy**.
  The recovery key is **tested by an actual restore once** (Phase 4) or it doesn't count. Losing any one or
  two devices still leaves a usable key.

---

## 6. Parity · Verification · Restore-Drill Cadence

| Check | Cadence | Runs on | Proof artifact |
|---|---|---|---|
| Content-hash parity (3 pairwise merkle roots) | every wake + daily | PC (wake) + E5 | `parity/roots/<ts>.json` + Slack |
| Staleness alarm | daily | E5 (always-on) | `#hive-alerts` if > 7d |
| Seed-completion gate | once + on full reseed | PC | `seed_manifest.json` |
| restic repo integrity (`restic check`) | weekly | E5 + PC | check log |
| btrfs scrub (bit-rot) | monthly | PC | scrub status |
| **Verified restore drill** (open DB, assert rows) | **monthly** | E5 | PASS/FAIL -> `#hive-alerts` |

A "vault healthy" claim requires last parity GREEN **and** last monthly drill GREEN.

---

## 7. Reuse Map

**Extend (don't reinvent):**

| Existing script | How extended |
|---|---|
| `mesh/acemagician_warm_standby.sh` | Public-IP path for big pulls; `pg_dump` instead of hot-tar; remove full-scope excludes; guard `--delete` (`--max-delete`, snapshot-first); `--checksum`. |
| `sync_to_mother.sh` | Push the *working subset* to E5 (media stays phone->PC); `--checksum`; conflict to quarantine. |
| `claude_sync_acemagician.sh` | Stays the `.claude/` config leg; folded under the orchestrator lock. |
| `blinko_sync.py` | Unchanged; brain DB also captured via `.backup`. |
| `mesh/failover_to_acemagician.sh` | `--drill` becomes the monthly verified restore. |
| `mesh/hive_hosts.env` | Add vault paths, denylist path, repo locations, public-IP preference flag. |
| `sync_queue.py` | Offline-first queue for the deferred media leg + wake intents. |
| `rclone` + `sdcard_sync_to_drive.sh` | Constrained to the safe-subset via the canonical denylist. |

**New scripts:** `vault_wake_orchestrator.sh`, `db_safe_capture.sh`, `parity_audit.py`,
`vault_staleness_alarm.sh`, `restic_init_and_policy.sh`, `e5_restic_replicate.sh`, `restore_drill.sh`,
`config/cloud_denylist.txt`.

---

## 8. Phased Rollout (smallest verifiable steps; each reversible)

- **Phase 0, Preconditions (blocking).** Install `restic b3sum gocryptfs` on the PC (operator runs
  `sudo pacman -Sy --needed restic b3sum gocryptfs`); install restic+b3sum on E5; write `cloud_denylist.txt`;
  audit `sdcard_sync_to_drive.sh` against it. *Test:* `restic version` on all 3; denylist grep finds zero PII
  paths in the last cloud manifest. *Rollback:* none (installs only).
- **Phase 1, First full seed via USB-C.** Copy the 44 GB workspace + E5 host-state once over USB-C directly to
  `/vault/mirror`, then incrementals over the wire. Write `seed_manifest.json`. *Test:* manifest complete; sizes
  reconcile. *Rollback:* delete `/vault/mirror`, reseed.
- **Phase 2, E5 snapshot engine + DB-safe capture.** `db_safe_capture.sh` + E5 restic repo + timer. *Test:*
  restore one pg dump to scratch, assert row counts. *Rollback:* disable timer (repo is additive).
- **Phase 3, Mirror legs with guards.** Fix `warm_standby.sh`/`sync_to_mother.sh` (subset to E5, full to PC,
  `--checksum`, snapshot-first, `--max-delete`). *Test:* same-2s-bucket edit propagates (FAT fix); 600-file
  delete aborts. *Rollback:* revert script edits (git-tracked).
- **Phase 4, Encryption + key escrow.** gocryptfs container for secrets; per-device restic keys + Proton Pass
  recovery key + printed copy; **restore once from the recovery key.** *Test:* recovery-key restore succeeds.
- **Phase 5, Wake-orchestrator + parity auditor.** `vault_wake_orchestrator.sh` (flock) + `parity_audit.py`.
  *Test:* power-cycle -> snapshot-first, pull, 3 roots + "N days behind"; inject divergence -> parity reports it.
- **Phase 6, Second history + watcher.** `e5_restic_replicate.sh` + `vault_staleness_alarm.sh`. *Test:* kill
  PC repo -> history restores from E5 replica; PC off 8 days -> E5 posts STALE.
- **Phase 7, Restore drill + offsite safe-subset.** `restore_drill.sh` monthly on E5; constrain rclone to the
  safe-subset. *Test:* drill posts PASS; denylisted path absent from crypt remote.

---

## 9. Residual Risks Accepted + Open Questions

**Accepted:** PC is a single SSD (no RAID), mitigated by the E5 second history; power-off windows bound the
PC's RPO, E5's always-on snapshots are the continuous RPO and the staleness alarm makes the gap visible;
PII/seeds have zero offsite copy by design (physical possession is the point).

**Open questions for the operator:**
1. Full-disk LUKS later (planned reinstall) vs. gocryptfs-for-secrets now? (Design assumes gocryptfs now.)
2. Retire Syncthing in favor of rsync-pull (design's choice), OK?
3. Staleness threshold 7 days, comfortable?
4. Where does the printed recovery-key copy physically live?

**Worst current fact this fixes first:** `acemagician_warm_standby.sh` runs `rsync -az --delete` over the
flaky tailnet, excludes the very dirs that must be full-scope, and hot-tars a live Postgres volume: a
corruption amplifier, scope-incomplete, and a producer of unrestorable DB artifacts. Phases 2-3 retire those
three behaviors before anything is trusted.
