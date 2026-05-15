# e5_mother -- Restoring the dead "Oracle E5 mother" instance

## What

The doctrine claims an Oracle E5 VM at `129.159.38.250` hosts Blinko + n8n + hive-voice + hive-django. **It's dead** -- the May 10 audit confirmed SSH key auth is denied and no services answer.

This directory provisions a replacement on a fresh Oracle Cloud free-tier ARM instance (4 OCPU / 16-18 GB RAM Ampere). Mirrors the `ev_box/` pattern but sized + scripted for the heavy services.

## Why a new instance (vs. recovering .250)

- Permission denied with our only key
- We have no console access pre-built
- Cleaner to launch fresh + restore data than to forensically recover a dead VM
- A fresh instance gets the lockdown-by-default config (port 2222 SSH, tailscale0-only services, UFW + fail2ban)

## Sizing

Asked for 4 OCPU / 24 GB. OCI free-tier capacity gave us 4 OCPU / 16-18 GB.
That's fine: Blinko + agentmemory + Open WebUI + hive-django + nginx idle at ~3-4 GB.
Headroom for ffmpeg voice work + concurrent users.

## Provisioning sequence

### Phase 0 -- launch the VM (manual, OCI Console)

1. https://cloud.oracle.com -> Compute -> Instances -> Create Instance
2. Shape: VM.Standard.A1.Flex, 4 OCPU, 18 GB (or 16 GB if 18 unavailable)
3. Image: Canonical-Ubuntu-22.04-aarch64-* (latest)
4. Boot volume: 100 GB
5. Networking: existing VCN, public subnet, public IP YES
6. SSH key: paste the public side of `/root/.ssh/github_deploy`
7. **Advanced -> Management -> Cloud-init script -> paste the entire `cloud_init.yaml` from this folder**
8. Create. Wait 5-7 minutes (slower than ev-box because Docker).

### Phase 1 -- provision (automatic, from phone)

```bash
# get the new VM's public IP from OCI Console
bash 03_AUTOMATION_CORE/01_Scripts/e5_mother/provision.sh <public-ip>

# or step-by-step
bash 03_AUTOMATION_CORE/01_Scripts/e5_mother/provision.sh <public-ip> --interactive
```

This:
- Handshakes SSH on port 2222
- Joins tailnet (needs `/root/.ssh/tailscale_authkey` on phone)
- One-way rsyncs the workspace mirror
- Deploys Blinko (Docker, :1111 localhost)
- Deploys agentmemory MCP (:3108 localhost)
- Deploys Open WebUI (Docker, :8080 localhost)
- Configures nginx as tailnet reverse proxy
- Registers `e5-mother` SSH alias on the phone
- Smoke-tests each endpoint

### Phase 2 -- restore data (manual)

- **Blinko notes**: from `08_BACKUPS/` or rclone-mirror to `~/blinko-restore` on mother
- **hive-django**: not auto-deployed -- decide first if we actually want it back, or kill the doctrine entry
- **n8n**: parked per doctrine (`GDOCS_DISABLE_N8N=1`) -- container ready, autostart off

### Phase 3 -- doctrine reconciliation

Update `/mnt/sdcard/AA_MY_DRIVE/CLAUDE.md`:
- Replace `Oracle E5 (163.192.19.196)` with `Oracle Micro (xlm-bot, 163.192.19.196)`
- Replace any `Oracle E5 (129.159.38.250)` with `e5-mother (tailnet only)`
- Update Blinko URL from `163.192.19.196:1111` to `http://e5-mother/blinko/` (or tailnet IP)

## What lives where (final tier map)

| Service               | Lives on        | Why                                                          |
|-----------------------|-----------------|--------------------------------------------------------------|
| xlm-bot, xlm-ws       | Micro (163.x)   | Already there, stable. Don't move.                          |
| Blinko RAG            | e5-mother       | Heavy enough to warrant the bigger box.                     |
| agentmemory MCP       | e5-mother       | Always-on session-memory store.                             |
| Open WebUI            | e5-mother       | 2-4 GB RAM, fits the bigger box.                            |
| MCP fleet bridge      | e5-mother       | Same VM as the things it bridges to.                        |
| hive-django (:8504)   | e5-mother       | Decide first if needed.                                     |
| hive-voice (:8200)    | e5-mother       | ffmpeg lives here.                                          |
| branded comms workers | e5-mother       | mail/slack queue processors.                                |
| ops crons, mail watch | ev-box          | Already specified in ev-box memory; keep separation.        |
| DFIR-lite             | ev-box          | Lightweight security observability.                         |
| Public webhooks       | Cloudflare      | everlightventures.io stays on Pages; webhook to e5-mother.  |

## Resource budget on e5-mother (18 GB / 4 OCPU)

| Service       | Idle RAM | Under load |
|---------------|----------|------------|
| Blinko        | ~600 MB  | ~1.2 GB    |
| agentmemory   | ~300 MB  | ~800 MB    |
| Open WebUI    | ~700 MB  | ~3 GB      |
| nginx         | ~30 MB   | ~80 MB     |
| hive-django   | ~250 MB  | ~600 MB    |
| hive-voice    | ~200 MB  | ~1.5 GB    |
| Docker engine | ~150 MB  | ~250 MB    |
| OS + overhead | ~800 MB  | ~1 GB      |
| **Total**     | **~3 GB**| **~8.5 GB**|

Leaves ~9 GB headroom -- enough for occasional multi-model parallel runs.
