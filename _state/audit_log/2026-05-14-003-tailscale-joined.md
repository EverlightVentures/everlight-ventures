---
id: 2026-05-14-003-tailscale-joined
title: e5-mother joined the tailnet (100.125.115.95)
date: 2026-05-14T16:10:00-07:00
agent: phone-claude
phase: migration
category: 120
thread: oracle-recover-replace
session: s-002-may14-migration
status: completed
tags: tailscale, network, security
summary: Installed Tailscale on the new mother and joined it to the operator's tailnet via interactive auth URL. Mother now reachable as a tailnet peer alongside phone, PC, and Dell.
---

## What was done

Installed the Tailscale daemon on e5-mother, brought it up with `--ssh` and
hostname `e5-mother`, and joined it to the operator's tailnet by handing
him a one-time auth URL to click (instead of using a pre-shared authkey,
which would require generating one and storing it). The operator approved
the device through `login.tailscale.com` and e5-mother received tailnet IP
`100.125.115.95`.

## Why

The operator's stated security model: every internal service rides the
tailnet, public surface shrinks to SSH only. For that to work, e5-mother
needs to be a tailnet peer so phone + PC can reach it on `100.125.115.95`
without exposing service ports publicly. Tailscale also gives us mesh-level
auth (the operator's identity gates device admission) and a private routing
plane that doesn't depend on the public IP, which can rotate.

Using the interactive auth URL (rather than a pre-shared authkey) keeps the
operator in control of *which devices* join — better security posture for a
4-device personal mesh than a long-lived shared secret in a file.

## Before

- e5-mother only reachable via public IP `163.192.60.35:22`
- Phone↔mother, PC↔mother had to go over public internet (security-list-gated)
- No private routing identity for the mother

## After

- e5-mother on the tailnet as `100.125.115.95` (hostname `e5-mother`)
- Visible from any other tailnet member: phone (`richards-z-fold7`,
  `100.112.180.29`), PC (`acemagician-pc`, `100.93.253.49`), Dell
  (`mgn-latitude-e7240`, `100.120.23.23`)
- Tailscale SSH advertised (`tailscale set --ssh`)
- Public surface stayed at SSH:22 only (Ubuntu's default iptables rejects
  everything else publicly via `icmp-host-prohibited`; tailnet traffic goes
  through the `ts-input` chain and bypasses the public deny)

## How

```bash
# On e5-mother
curl -fsSL https://tailscale.com/install.sh | sudo sh
sudo systemctl enable --now tailscaled
sudo nohup tailscale up --ssh --hostname=e5-mother --accept-routes=false &

# Tailscale printed an auth URL; handed it to the operator
# Operator clicked the URL, approved the device

# Verify
sudo tailscale status     # shows e5-mother + the other 3 peers
sudo tailscale ip -4      # 100.125.115.95
```

## Verification

- `tailscale status` lists `e5-mother  100.125.115.95  1m.rich.gee@  linux`
- The other 3 family members visible: acemagician-pc (online), phone
  (offline-4h-ago — known issue with stale phone tailscaled), Dell
  (offline-9d, expected)
- Phone → mother tailnet reach is blocked only by the phone's stale
  tailscaled, not by mother's setup

## Audit trail

- Auth URL not stored anywhere — single-use, click-and-discard.
- No pre-shared authkey written to disk on e5-mother.
- Tailscale ACL still default at this point (no custom `ssh` rules); the
  operator was given the recommended ACL snippet to paste in the admin
  console as a 2-minute follow-up.

## Open items downstream

- Tailscale ACL paste (operator's lane) — would enable Tailscale-SSH
  (keyless, identity-based) from PC → mother.
- Phone tailscaled kick (Termux side, outside proot) — fixes the
  phone-can't-reach-tailnet issue.

## Links

- Memory: `project_sync_architecture_v3.md` — the priority-ordered sync
  mesh design.
- Cheat sheet: §1 (the 4-device family with IPs).
