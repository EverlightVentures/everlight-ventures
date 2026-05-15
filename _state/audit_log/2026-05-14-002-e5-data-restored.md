---
id: 2026-05-14-002-e5-data-restored
title: E5 production data restored to new mother (3.8 GB, .env + 113 systemd units)
date: 2026-05-14T16:00:00-07:00
agent: phone-claude
phase: migration
category: 110
thread: oracle-recover-replace
session: s-002-may14-migration
status: completed
tags: oracle, data-recovery, restore, lvm
summary: Attached the orphan boot volume from the dead .250 mother to the new e5-mother, mounted Oracle Linux's LVM, rsync'd the full /home/opc tree (.env + production code + 113 systemd units) onto the new box.
---

## What was done

Reconnected to the data from the dead E5. The orphan boot volume
`xlm-bot-core-e5-2c16g` (47 GB, AVAILABLE state, retained by Oracle's
free-tier-retained policy) was attached as a secondary disk to the freshly
launched e5-mother. Mounted Oracle Linux's `ocivolume` LVM volume group
read-only, copied `/home/opc/*` over via rsync, copied `/etc/systemd/system/*`
into a `_systemd_units/` subdir for later translation. Then detached the
orphan volume so it stays intact as the cold backup of record.

## Why

The dead E5 hosted the *entire* business runtime — Blinko (3,711 notes),
hive-django (broker pipeline DB with 1,893 matches + 515 leads + 436
properties), hive-voice, wholesale orchestrators, MCP proxies, and all the
production `.env` keys (Anthropic, OpenAI, Resend, Stripe, Supabase, Slack,
Langfuse, Google Maps, ImprovMX). Without recovering this data, the new
e5-mother would be a bare Ubuntu box with no actual business on it.

The orphan boot volume is the *only* source of truth for some of this
content (n8n workflows, some `.env` keys never duplicated elsewhere).

## Before

- New e5-mother running but empty (just a bare Ubuntu 22.04 install)
- Orphan boot volume `xlm-bot-core-e5-2c16g` detached and AVAILABLE in OCI
- No `.env`, no production code, no systemd units on e5-mother

## After

- `/home/ubuntu/e5_data/` on e5-mother contains **3.8 GB** of recovered tree:
  - `.env` (83 lines, every production key)
  - 113 systemd unit files in `_systemd_units/`
  - Full `hive_*.py`, `broker_*.py`, `wholesale_*.py` source
  - `content_tools/`, `hive_django/`, `hive_mind/`, `wholesale/`
  - `blinko_lite.py` + `blinko_lite.db` (3,711 notes)
- Orphan boot volume re-detached, lifecycle-state AVAILABLE (cold backup
  preserved)

## How (the sequence)

```bash
# 1. Attach orphan volume to new mother
oci compute volume-attachment attach \
  --type paravirtualized \
  --instance-id <e5-mother-OCID> \
  --volume-id ocid1.bootvolume.oc1.us-sanjose-1.abzwuljrzmlkhudjg2iauamz6zr4mhrygp6kmxurur4d7wrh73qrfvlmg3oq

# 2. On e5-mother: activate Oracle Linux LVM
sudo vgscan --mknodes
sudo vgchange -ay ocivolume

# 3. Mount read-only
sudo mkdir /mnt/orphan_e5
sudo mount -o ro /dev/ocivolume/root /mnt/orphan_e5

# 4. Rsync the production tree
sudo rsync -a --exclude '.cache/' --exclude '.npm/' --exclude 'hive_reports/' \
  /mnt/orphan_e5/home/opc/ /home/ubuntu/e5_data/

# 5. Capture systemd units too
sudo cp -a /mnt/orphan_e5/etc/systemd/system/. /home/ubuntu/e5_data/_systemd_units/

# 6. Unmount + detach
sudo umount /mnt/orphan_e5
oci compute volume-attachment detach --volume-attachment-id <va-id> --force
```

## Verification

- `du -sh /home/ubuntu/e5_data` → 3.8 GB ✓
- `ls /home/ubuntu/e5_data/.env` → exists, 4395 bytes ✓
- `ls /home/ubuntu/e5_data/_systemd_units/ | wc -l` → 113 ✓
- Sample key files present: `content_tools/`, `hive_django/`, `wholesale/`,
  `broker_daily_orchestrator.py`, `hive_voice_handler.py` ✓

## Audit trail

- Mount was always read-only — no risk of writing to the orphan volume.
- Sensitive `.env` file landed at `/home/ubuntu/e5_data/.env` with default
  ubuntu user permissions (chmod 600 applied later when env files were
  placed in `/etc/default/rex-negotiator`).
- The orphan volume retains lifecycle-state AVAILABLE for repeat extracts
  (we re-mounted it twice more for `/etc` and `/opt/mcp_servers` grabs).

## Links

- See entry `2026-05-15-001-mcp-servers-recovered.md` for the later `/opt`
  grab that unblocked Batch 2 (MCP fleet provisioning).
- Cheat sheet: §2 (orphan volume OCID), §5 (recovery pointers).
