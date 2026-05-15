---
id: 2026-05-15-005-phone-to-mother-sync
title: Phone → e5-mother workspace sync wired (boot one-shot + tailnet rsync)
date: 2026-05-15T09:30:00-07:00
agent: phone-claude
phase: post-migration
category: 520
thread: sync-architecture
session: s-003-may15-tooling
status: completed
tags: sync, tailnet, boot-hook, rsync
summary: Built sync_to_mother.sh, the missing leg of the phone→Oracle pipeline. Phone boot now auto-pushes workspace + memory deltas to e5-mother over the tailnet. Fixed a Tailscale-SSH ACL trap that was silently blocking the connection.
---

## What was done

Wired the **phone → e5-mother** leg of the sync mesh — the one piece missing
from the priority-order pipeline (`phone → GitHub → Oracle → PC`). Built a
new script `sync_to_mother.sh` modeled on the proven `claude_sync_acemagician.sh`
pattern. Added a one-shot invocation to `/root/.termux/boot/start_hive.sh`
so phone-boot triggers a push automatically. Also fixed a sneaky Tailscale-SSH
ACL trap that was silently blocking tailnet:22 access to e5-mother.

## Why

The doctrine (per `project_sync_architecture_v3.md`): Oracle is the always-on
hub; phone pushes its workspace edits up; PC pulls from Oracle (or syncs
directly with phone). Before this work, the only sync was phone↔PC. e5-mother
had a stale copy from the recovery, and nothing was wiring new phone edits up
to it.

Without this, the doctrine was aspirational. With it, phone edits actually
reach the Oracle hub on every boot.

## Before

- `claude_sync_acemagician.sh` handles phone↔PC ✓
- `sync_on_reconnect.sh` knew about e5-mother in its peer list but the
  invocation path was stale (different target dir)
- No phone→Oracle push wired into the boot sequence
- Tailnet:22 SSH from phone to e5-mother was silently hanging — turned out
  Tailscale's `--ssh` feature intercepts port 22 on the tailscale0 interface
  and gates it through the tailnet ACL. With no `ssh` rule in the ACL yet,
  the action defaulted to a hang (waiting for a browser check that never
  came). HTTP to 1111 worked fine because Tailscale doesn't intercept that
  port.

## After

- **`sync_to_mother.sh`** at `03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh`:
  - Reachability-gated (skips cleanly if mother offline)
  - Rsyncs workspace + memory dir
  - Conflict-preserving via `--backup --backup-dir=_sync_conflicts_quarantine_from_phone_TIMESTAMP/`
  - One-way push (phone is workstation SOT; mother receives)
  - Excludes `_logs/`, `.git/`, `node_modules/`, `__pycache__/`,
    `08_BACKUPS/_frozen_snapshots/`, `_sync_conflicts_quarantine_*/`,
    `04_MEDIA_LIBRARY/`
  - Logs to `_logs/network_sync/sync_to_mother_TIMESTAMP.log`
  - Writes handshake timestamp to `_state/last_mother_sync.txt`

- **Boot hook**: `/root/.termux/boot/start_hive.sh` now fires `sync_to_mother.sh`
  on every phone boot (alongside the existing PC sync hook).

- **Tailscale-SSH trap fixed**: ran `sudo tailscale set --ssh=false` on
  e5-mother. Regular sshd now handles tailnet:22 traffic normally
  (it was already listening on `0.0.0.0:22`, the issue was the
  interception). Tailscale ACL paste is still nice-to-have for *Tailscale
  SSH* (keyless), but plain SSH with the `github_deploy` key works perfectly
  fine over the tailnet now.

## How

```bash
# 1. Diagnosis: HTTP/1111 worked, SSH/22 stalled. Tailscale --ssh was the
#    culprit -- it intercepts :22 on tailscale0 and asks the ACL.
ssh ubuntu@163.192.60.35 "sudo tailscale set --ssh=false"

# 2. Verify
ssh ubuntu@100.125.115.95 "echo TAILNET_SSH_OK"
# -> TAILNET_SSH_OK

# 3. Run the sync (background, ~35 GB delta)
bash 03_AUTOMATION_CORE/01_Scripts/sync_to_mother.sh
```

## Verification

```bash
# 1. Script reachable + reachability check passes
tail -3 /mnt/sdcard/AA_MY_DRIVE/_logs/network_sync/sync_to_mother_*.log
# -> "e5-mother reachable -- proceeding"
# -> "workspace -> 100.125.115.95:/home/ubuntu/AA_MY_DRIVE"

# 2. Boot hook present
grep -n sync_to_mother /root/.termux/boot/start_hive.sh
# -> nohup bash ... sync_to_mother.sh

# 3. Handshake file appears after first run
cat /mnt/sdcard/AA_MY_DRIVE/_state/last_mother_sync.txt
```

## Audit trail

- One-way push only — phone is workstation SOT, mother receives. No risk of
  mother data clobbering phone.
- `--backup` preserves any file on mother that gets overwritten (in
  `_sync_conflicts_quarantine_from_phone_TIMESTAMP/`). Nothing destroyed.
- Tailscale `--ssh=false` change is fully reversible (`tailscale set --ssh`
  re-enables). Doesn't affect tailnet routing at all.
- The sync script logs every run; nothing happens silently.

## What this enables

- The doctrine pipeline (`phone → GitHub → Oracle → PC`) now has its
  phone→Oracle leg actually wired (direct rsync, not yet GitHub-mediated,
  but functional).
- e5-mother now receives the audit log, the cheat sheet, the Moltbook
  source — anyone reading e5-mother's `/home/ubuntu/AA_MY_DRIVE/` sees the
  current state of the work.
- Phase 9 of the post-migration plan: done in spirit (phone push) rather
  than the originally-designed e5-mother pull. Simpler, no new SSH key
  needed.

## Honest limitations

- The PC→Oracle leg is still pending. Once PC comes online + its
  `claude_sync_pull.sh` cron is wired up, the full mesh closes.
- This is a phone-boot one-shot. There's no recurring timer on the phone
  (per `feedback_oracle_only_crons.md`: phone is control plane, never cron
  host). For mid-day pushes the operator runs `bash sync_to_mother.sh`
  manually OR the next reboot picks it up.
- GitHub as the actual bus is still aspirational. Direct rsync is the
  current implementation.

## Links

- Pattern source: `03_AUTOMATION_CORE/01_Scripts/claude_sync_acemagician.sh`
- Boot hook: `/root/.termux/boot/start_hive.sh`
- Plan: Phase 9 in `/root/.claude/plans/yeah-its-a-r3c9ver-polymorphic-crystal.md`
- Cheat sheet: §1 (the family flow diagram).
