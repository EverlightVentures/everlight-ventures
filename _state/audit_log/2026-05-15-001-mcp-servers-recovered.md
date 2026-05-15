---
id: 2026-05-15-001-mcp-servers-recovered
title: MCP server source code recovered (the missing /opt/mcp_servers tree)
date: 2026-05-15T07:00:00-07:00
agent: phone-claude
phase: migration
category: 530
thread: service-provisioning
session: s-003-may15-tooling
status: completed
tags: mcp, recovery, batch-2-unblock, lvm-xfs
summary: Third orphan boot volume pass succeeded after fixing a filesystem-type detection bug (kernel kept guessing EXT4 when the LV was actually XFS). Grabbed /opt/mcp_servers (4 MCP server source dirs), /usr/local, /root config, crontabs. 9.1 GB total. Batch 2 unblocked.
---

## What was done

Third re-attach of the orphan boot volume to e5-mother, this time with the
correct mount technique. The first re-attach (for `/etc`) had worked because
the kernel happened to guess the filesystem type correctly. The second
re-attach (for `/opt`) failed with `EXT4-fs: unable to read superblock` —
the kernel was now guessing wrong. Diagnosed via `blkid` that the LV
`/dev/ocivolume/root` is **XFS**, not EXT4. Explicitly specified `-t xfs` on
mount + `partprobe` first; mount succeeded; grabbed the missing trees.

## Why

The MCP fleet (the 7 `mcp-*-proxy` services that bridge agents to external
APIs like Blinko, Resend, Stripe, Supabase, market-intel, n8n) was the next
24/7 service tier to provision. The systemd units reference
`/opt/mcp_servers/<name>/server.py` paths — but `/opt/mcp_servers/` was on
the *Oracle Linux* filesystem hierarchy, **not** under `/home/opc/`, so it
hadn't been captured by the original data restore (which targeted only
`/home/opc/`). Without `/opt/mcp_servers/`, none of the MCP proxies can
start. Recovering it unblocks Batch 2.

## Before

- e5-mother had `/home/ubuntu/e5_data/` (3.8 GB — `/home/opc/` tree)
- Had `_etc_config/` from a separate pass (the env files)
- Did NOT have `/opt/mcp_servers/` — Batch 2 blocked
- 2 prior re-attach attempts in this session: one succeeded (`/etc/`),
  one failed (`/opt/` — wrong filesystem-type guess)

## After

- `/home/ubuntu/e5_recovered/opt/mcp_servers/` contains 4 MCP server source dirs:
  - `blinko_memory/`
  - `dispatcher_relay/`
  - `market_intel/`
  - `n8n_mcp/`
- `/home/ubuntu/e5_recovered/usr/local/` — custom binaries
- `/home/ubuntu/e5_recovered/root/` — root config (including `.ssh`)
- `/home/ubuntu/e5_recovered/var/spool/cron/` — crontabs (empty for opc;
  some root crons)
- `/home/ubuntu/e5_recovered/etc/cron.d/`, `letsencrypt/`, `postfix/`,
  `sysctl.d/` — additional config snapshots
- Total: **9.1 GB recovered this round**
- Orphan volume detached cleanly, lifecycle-state AVAILABLE (intact)

## How (the corrected technique)

```bash
# 1. Attach
oci compute volume-attachment attach --type paravirtualized \
  --instance-id <e5-mother-OCID> \
  --volume-id ocid1.bootvolume.oc1.us-sanjose-1.abzwuljrzmlkhudjg2iauamz6zr4mhrygp6kmxurur4d7wrh73qrfvlmg3oq
sleep 20  # let the block device fully register

# 2. The key fix: partprobe + detect fstype, don't let kernel guess
sudo partprobe /dev/sdc
sudo udevadm settle
sudo vgchange -an ocivolume 2>/dev/null  # bounce in case stale
sudo vgchange -ay ocivolume

fstype=$(sudo blkid -o value -s TYPE /dev/ocivolume/root)
# → "xfs" (kernel had been guessing "ext4" before)

# 3. Mount with EXPLICIT fstype, read-only
sudo mkdir -p /mnt/orphan_e5
sudo mount -t "$fstype" -o ro /dev/ocivolume/root /mnt/orphan_e5

# 4. Grab the missing trees
for dir in opt usr/local root var/spool/cron etc/cron.d etc/letsencrypt etc/postfix etc/sysctl.d; do
  src="/mnt/orphan_e5/$dir"
  [ -e "$src" ] && sudo rsync -a "$src" /home/ubuntu/e5_recovered/
done

# 5. Unmount + detach
sudo umount /mnt/orphan_e5
oci compute volume-attachment detach --volume-attachment-id <va-id> --force
```

## The diagnostic that unstuck us

When mount kept failing with `EXT4-fs: unable to read superblock`, the
fix wasn't more retries — it was *asking the disk*. `blkid -o value -s TYPE`
told us the filesystem was XFS. Passing `-t xfs` explicitly stopped the
kernel from making a bad guess. Lesson saved as a recovery pattern in the
mailbox and the cheat sheet.

## Verification

- `ls /home/ubuntu/e5_recovered/opt/mcp_servers/` → 4 server dirs visible
- `du -sh /home/ubuntu/e5_recovered/` → 9.1 GB
- Orphan volume detached: `oci bv boot-volume get ... | grep lifecycle` →
  AVAILABLE (intact for any future re-grab)

## Audit trail

- Mount was read-only throughout — orphan volume content unchanged.
- The orphan volume's lifecycle-state remained AVAILABLE; can be re-attached
  again if anything else turns out to be missing.
- Three separate re-attach cycles in this session, each clean detach
  afterward.

## What this unblocks (Batch 2)

With `/opt/mcp_servers/` now on e5-mother, Batch 2 can proceed:
1. `pip install mcp-proxy` on e5-mother
2. For each of the 4 MCP server dirs: install Python deps from `requirements.txt`
3. Translate the matching `.service` files (`opc` → `ubuntu`, `/opt/mcp_servers`
   → `/home/ubuntu/e5_recovered/opt/mcp_servers`)
4. `systemctl enable --now` each, verify on ports 3101–3107

## Links

- See entry `2026-05-14-002-e5-data-restored.md` for the original (smaller)
  data restore that captured only `/home/opc/`.
- Plan: Phase 10 (Batch 2/3/4 service provisioning).
- Cheat sheet: §4 (MCP fleet in service map).
