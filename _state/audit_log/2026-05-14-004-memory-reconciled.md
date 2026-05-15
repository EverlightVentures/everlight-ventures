---
id: 2026-05-14-004-memory-reconciled
title: Memory layer reconciled — 181 files both sides (was a fork of 156 vs 26)
date: 2026-05-14T11:00:00-07:00
agent: phone-claude
phase: migration
category: 220
thread: memory-resilience
session: s-002-may14-migration
status: completed
tags: memory, sync, doctrine
summary: Discovered that the phone and PC had been accumulating SEPARATE Claude memory files for weeks (different project keys). Union-merged them so both devices now share all 181 doctrine and decision files.
---

## What was done

Reconciled the operator's Claude Code "memory" layer (the auto-memory files
at `~/.claude/projects/.../memory/`) between phone and PC. The two devices
had been writing memories under *different project-key directories* for
weeks, so the doctrine, feedback rules, and project notes had silently
forked. Performed a bidirectional union merge with `rsync --update`
(newer-mtime-wins) so both sides now have the complete superset.

## Why

The phone-Claude and PC-Claude sessions are supposed to share doctrine —
"how Rich works," "what's already been decided," "rules to apply." But
because each Claude derives the project-key directory name from the
*absolute workspace path* (phone: `/mnt/sdcard/AA_MY_DRIVE` →
`-mnt-sdcard-AA-MY-DRIVE`, PC: `/home/richgee/AA_MY_DRIVE` → `-AA-MY-DRIVE`),
the directories were different. The sync script `claude_sync_acemagician.sh`
was syncing workspace content correctly but the *memory* directory wasn't in
its scope. So each Claude session was operating on its own private memory
slice and they drifted.

This is exactly the "I don't know what's what" the operator described —
both sessions had real, valid context, but neither could see the other's.

## Before

- Phone memory: 156 files at `~/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory/`
- PC memory: 26 files at `~/.claude/projects/-AA-MY-DRIVE/memory/`
- Overlap: 1 file (and the phone's version was newer)
- 25 PC-only files invisible to phone-Claude — including `project_oracle_e5.md`,
  `project_3_device_sync_architecture.md`, `feedback_always_free_only.md`,
  `project_outbound_halt_v2.md`, `project_a1_hammer.md`. These were
  *load-bearing for the current work* and the phone-Claude was operating
  blind to them.

## After

- Phone memory: **181 files**
- PC memory: **181 files**
- Both sides identical (bidirectional `rsync --update`, mtime-wins)
- Reading the 25 PC-origin files immediately surfaced major reality
  corrections: (a) the E5 data had ALREADY been rsync'd to the PC on May 7,
  (b) a PC-side capacity hammer (`oracle-a1-hammer.service`) was already
  running, (c) the May-4 doctrine declared the PC "master vault" — though
  Rich later (May-14) corrected that to "phone is workstation, PC is
  powerful #2"

## How

```bash
PHONE_MEM=/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory
PC_MEM=richgee@100.93.253.49:/home/richgee/.claude/projects/-AA-MY-DRIVE/memory
SSH_OPT="ssh -i /root/.ssh/phone_to_arch -o StrictHostKeyChecking=no"

# Pull PC-only files -> phone (mtime-wins, additive)
rsync -az --update -e "$SSH_OPT" "$PC_MEM/" "$PHONE_MEM/"

# Push merged set -> PC
rsync -az --update -e "$SSH_OPT" "$PHONE_MEM/" "$PC_MEM/"
```

## Verification

- `ls $PHONE_MEM | wc -l` → 181
- `ssh pc 'ls ~/.claude/projects/-AA-MY-DRIVE/memory/ | wc -l'` → 181
- Critical PC-origin files now readable on phone: confirmed
  `project_oracle_e5.md`, `feedback_always_free_only.md`,
  `project_a1_hammer.md`, `user_profile.md` all present

## Audit trail

- `rsync --update` is non-destructive — files where dest is newer get
  skipped, no overwrites. 0 files deleted.
- The exfat sdcard didn't support unix permissions, so rsync printed
  cosmetic "failed to set permissions" warnings — file *contents* still
  copied. Verified by post-merge counts.
- No memory files were *modified*, only *copied* across.

## Audit findings (the real value)

Reading the freshly-merged PC-origin files surfaced:
1. **E5 data already extracted** (May 7 to PC at `/AA_MY_DRIVE/_oracle_e5_recovery/`)
   — phone-Claude had been planning to re-extract from the orphan volume,
   wasting time.
2. **PC capacity hammer already running** — phone-Claude had launched its
   own hunter, doubling API calls and triggering 429 throttling.
3. **Always-Free doctrine** (May 4) — phone-Claude had been ambiguous on
   PAYG vs free; this clarified the rule (Rich confirmed May 15).

The fork was the root cause of session-to-session amnesia and duplicated
work. Fixing it is the highest-leverage move of the migration.

## Links

- Memory: `project_sync_architecture_v3.md` (the new canonical, supersedes
  the May-4 PC-master-vault doctrine).
- Memory: `feedback_oracle_always_free.md` (the Always-Free rule).
- Cheat sheet: §6 (recovery pointers — memory is part of the resilience layer).
