# ev-box -- Local Personal Ops Environment

A second isolated Ubuntu inside Termux's proot ecosystem. Separate rootfs, separate apt world, separate SSH server, separate Tailscale identity. Phone is the host, ev-box is a sibling environment that looks like a distinct machine on your tailnet.

## Why local and not Oracle Cloud

The 4 OCPU / 24 GB Always-Free ARM Ampere quota is **reserved** for restoring xlm-bot to its proper E5 shape (`xlm-bot-core-e5-2c16g`). Burning any of it on a personal dev box would block that restore. So ev-box runs locally on the phone, costs $0, uses storage and CPU you already own.

## Why a sibling proot-distro and not user-level isolation

Real isolation matters: separate Ubuntu rootfs, separate package world, separate `/root`, separate Tailscale state, separate sshd port. If you mess something up in ev-box you can `proot-distro remove ev-box` and start over without touching the host Ubuntu.

## Active files in this directory

| File | Role |
| --- | --- |
| `setup_evbox.sh` | **THE script you run.** Idempotent post-install configurator. Runs INSIDE the new ev-box rootfs. Installs base packages, sshd on 2222, Tailscale userspace, Claude CLI, mirrors, DFIR-lite subset. |
| `README.md` | This file. |

The other files in this dir (`cloud_init.yaml`, `provision.sh`, `migrate_crons.sh`, `install_dfir_lite.sh`, `install_claude_layer.sh`) are **deprecated** -- they were the OCI-VM variant from an earlier plan iteration. Left in place for git history; not referenced by the local flow.

## How to bring it up

### Step 1 -- in a FRESH Termux session (NOT inside the Ubuntu proot)

Open Termux. **Don't** `proot-distro login ubuntu` first -- you need to be at the native Termux shell.

```bash
proot-distro install ubuntu --override-alias ev-box
```

Takes ~3 min. Cached rootfs is already at `/data/data/com.termux/files/usr/var/lib/proot-distro/dlcache/`, just extracts. Confirms with "Distribution installed".

### Step 2 -- run setup_evbox.sh INSIDE the new ev-box

From native Termux still:

```bash
proot-distro login ev-box -- bash /sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ev_box/setup_evbox.sh
```

Takes ~5-10 min (slow part is `apt update` + apt installs). When it finishes, follow the printed instructions to start sshd and Tailscale.

### Step 3 -- bring Tailscale up + start sshd

Inside ev-box (already there from Step 2):

```bash
mkdir -p /var/lib/tailscale /var/run/tailscale
/usr/local/sbin/tailscaled --tun=userspace-networking \
  --state=/var/lib/tailscale/tailscaled.state \
  --socket=/var/run/tailscale/tailscaled.sock &
sleep 2
/usr/local/bin/tailscale up --hostname=ev-box --ssh --accept-routes
```

Click the auth URL. ev-box appears on your tailnet as a separate device.

```bash
/usr/sbin/sshd -D &
```

From any other tailnet device:

```bash
ssh ev-box
```

You're in.

## What the DFIR-lite subset includes (and doesn't)

Inside proot, kernel-dependent tools don't work. Realistic subset:

| Tool | Status | Why |
| --- | --- | --- |
| osquery | works | userspace SQL queries over host state |
| Medusa SAST | works | userspace Python scanner |
| Velociraptor agent | works | single binary, userspace |
| auditd | NO | needs kernel audit subsystem |
| Wazuh agent | NO | needs systemd + kernel hooks |
| suricata | NO | needs raw sockets / promisc mode |
| fail2ban | NO | needs iptables |
| ufw | NO | needs iptables |

If you ever want the full stack, you need a real VM (QEMU TCG works but is slow on phones) or a cloud box.

## Known proot limitations vs a real VM

- Same kernel as host (Android kernel via Termux). No kernel isolation.
- Same network MAC. Tailnet identity is distinct, but L2 it's the same NIC.
- Tailscale must run with `--tun=userspace-networking` (no `/dev/net/tun` in proot).
- systemd doesn't run as PID 1 -- it's a regular bash invocation. Services that need `systemctl enable --now` won't auto-start; you start them manually or via wrapper scripts.

## Reset / start over

From native Termux (not from inside any proot-distro):

```bash
proot-distro remove ev-box
```

Then redo Step 1 + Step 2.

## What lives where (after setup)

| Location | What it is |
| --- | --- |
| `/root/AA_MY_DRIVE/` (inside ev-box) | symlink to `/sdcard/AA_MY_DRIVE` -- live workspace mirror |
| `/root/.claude/` (inside ev-box) | own copy -- ev-box has its own Claude config / sessions |
| `/opt/dfir-lite/` (inside ev-box) | Velociraptor binary lives here |
| `/var/log/setup_evbox.log` (inside ev-box) | install log from Step 2 |
| `/var/lib/tailscale/` (inside ev-box) | ev-box's tailnet state -- distinct identity |
