---
id: 2026-05-14-001-e5-mother-launched
title: e5-mother instance launched (4 OCPU / 24 GB Always Free)
date: 2026-05-14T15:54:34-07:00
agent: phone-claude
phase: migration
category: 110
thread: oracle-recover-replace
session: s-002-may14-migration
status: completed
tags: oracle, infra, migration, always-free
summary: Launched the replacement Always-Free Ampere ARM instance after the .250 mother was terminated. New box runs at $0/month.
---

## What was done

Launched a new Oracle Cloud Ampere ARM instance named `e5-mother` to replace
the original Oracle E5 mother that had been terminated. Used the OCI CLI from
the phone (no console clicking), with no cloud-init script — the previous
launch attempt had a cloud-init bug that barricaded SSH (a `ufw` rule
referencing `tailscale0` before Tailscale was installed killed the first-boot
script). Bare Ubuntu was the safer choice; provisioning was done over SSH
afterward, where every command's result is visible.

## Why

The original Oracle E5 ".250" (hostname `xlm-bot-core-e5-2c16g`) was terminated
on 2026-04-30 because it was a paid shape no longer covered by the Always Free
tier. Without it, the Hive Mind had nowhere to run its 24/7 services — Blinko
RAG, hive-django, hive-voice, the MCP fleet. The wholesale revenue engine
couldn't run unattended. A replacement was non-optional for the business to
operate.

The 4 OCPU / 24 GB A1.Flex shape **is** the Always Free A1 allotment — no
recurring cost. The PAYG card on file was added 2026-05-14 only to escape the
$100-hold verification limbo, not to authorize spending.

## Before

- No live Oracle host for the Hive (only `xlm-bot` on the Micro at `163.192.19.196`)
- 113 systemd unit files + ~4 GB of production code stranded on the orphan
  boot volume from .250
- Blinko's 3,711 notes accessible only by re-mounting the orphan volume
- Multiple OCI launch attempts had been failing with "Out of host capacity"
  for ~30 hours (us-sanjose-1 free Ampere pool drained)
- 3 orphan boot volumes consuming 141 GB of the 200 GB free-tier block quota

## After

| Item | Value |
|---|---|
| Instance OCID | `ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgacztxdo45gi6hupzd67gumuqy7g33uycc5fad7al3wy6ra` |
| Shape | VM.Standard.A1.Flex, 4 OCPU / 24 GB RAM |
| OS | Ubuntu 22.04.5 LTS aarch64 |
| Boot disk | 50 GB (shrunk from 100 GB to fit free-tier block quota) |
| Public IP | `163.192.60.35` |
| Tailnet IP | `100.125.115.95` |
| SSH | port 22, `github_deploy` key authorized |
| Cost | **$0/month** (within Always Free) |

## How (the command)

```bash
oci compute instance launch \
  --compartment-id ocid1.compartment.oc1..aaaaaaaalhtovyf6lyn3xppwmdfjkfssf7vf56zahmp2xdc5hv4gay3vtv2a \
  --availability-domain "kNfe:US-SANJOSE-1-AD-1" \
  --shape VM.Standard.A1.Flex \
  --shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
  --image-id ocid1.image.oc1.us-sanjose-1.aaaaaaaae5nqxnx7734mvbzkt3pctumjdb525h2mpzxqxyh3pfmw2iqdsqqq \
  --subnet-id ocid1.subnet.oc1.us-sanjose-1.aaaaaaaa7gg2a526yyx3iqdgr7wyfth7w2e675qmyeixiavm6rcmkttq26xq \
  --display-name e5-mother \
  --assign-public-ip true \
  --hostname-label e5-mother \
  --boot-volume-size-in-gbs 50 \
  --ssh-authorized-keys-file /root/.ssh/github_deploy.pub
```

## Verification

- `oci compute instance get` → state RUNNING, shape matches
- `ssh -i ~/.ssh/github_deploy ubuntu@163.192.60.35 "echo UP; hostname; uptime"`
  → `UP / e5-mother / 3 min`

## Audit trail

- Pay-As-You-Go card added 2026-05-14 ~11:30 PT to unblock account from
  verification limbo. Card NOT used to authorize this shape (it's free).
- Previous barricaded instance (`192.18.137.52`) was terminated cleanly with
  boot volume deleted (it was a throwaway).
- Orphan boot volume `xlm-bot-core-e5-2c16g` left intact as cold backup.

## Links

- Plan: `/root/.claude/plans/yeah-its-a-r3c9ver-polymorphic-crystal.md`
- Memory: `feedback_oracle_always_free.md` (the standing rule for this account)
- Cheat sheet: `06_DEVELOPMENT/everlight_os/INFRASTRUCTURE_CHEATSHEET.md` §2
