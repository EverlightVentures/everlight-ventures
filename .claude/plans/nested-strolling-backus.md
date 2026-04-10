# Plan: Fix PRoot SSH, Configure Slack War Room Webhook, Deploy ngrok + Nextcloud

## Context

Three user requests, all blocked by one root issue:
1. SSH from PRoot times out connecting to Oracle VM (163.192.19.196). This blocks deploying ngrok, Nextcloud, everything.
2. Slack war room webhook - user provided new webhook credentials for the hive mind war room channel.
3. Nextcloud server - user wants cross-device sync, will use hive to plan/deploy on Oracle VM.

---

## Task 1: Fix PRoot SSH (highest priority, unblocks everything)

**Root cause** (confirmed by verbose SSH trace from explore agent):
- TCP to 163.192.19.196:22 SUCCEEDS (`Connection established`)
- SSH key parsing FAILS inside PRoot (`no pubkey loaded, type -1`)
- Banner exchange times out waiting for auth that never starts
- PRoot's ptrace filesystem layer breaks OpenSSL's key loading
- Android's `fwmarkd` socket marking also doesn't work inside PRoot

**Fix**: Use a `ProxyCommand` with Termux's native `ncat` binary to handle the TCP connection, and create an SSH config with `IPQoS none` to avoid Android packet marking issues.

### Files to create/modify:

**CREATE `/root/.ssh/config`:**
```
Host oracle
    HostName 163.192.19.196
    User opc
    IdentityFile /root/.ssh/oracle_key.pem
    StrictHostKeyChecking no
    ConnectTimeout 15
    ServerAliveInterval 30
    ServerAliveCountMax 3
    IPQoS none
    ProxyCommand /data/data/com.termux/files/usr/bin/ncat %h %p
```
The ProxyCommand forces the TCP socket through Termux's native binary (properly Android-integrated), bypassing PRoot's broken socket path entirely.

**UPDATE `03_AUTOMATION_CORE/01_Scripts/oracle_watchdog.sh`:**
- Change `check_ssh()` and `check_bot_full()` to use `-F /root/.ssh/config` and `Host oracle` alias
- This makes the watchdog use the same fix

**UPDATE `QUICK_COMMANDS.md`:**
- Simplify Oracle SSH commands to use `ssh oracle` alias

### Verification:
```bash
ssh oracle "echo OK"   # should return within 5 seconds
ssh oracle "docker ps"  # confirm bot is running
```

---

## Task 2: Configure Slack War Room Webhook

User provided 3 credential segments: `14e79a74511e3ef2079713d09419bdfa`, `1becd3dde82a6959190b5eb5d0760170`, `b3JGofW91an0TihIn0smLDNe`

Webhook URL: `https://hooks.slack.com/services/14e79a74511e3ef2079713d09419bdfa/1becd3dde82a6959190b5eb5d0760170/b3JGofW91an0TihIn0smLDNe`

### Files to modify:

**`xlm_bot/config.yaml` line 722:**
- Set `war_room_webhook_url` to the new webhook URL

**`everlight_os/hive_mind/convergence.py` `_notify_slack()`:**
- Currently only checks `SLACK_WEBHOOK_URL` env var and `everlight.yaml` - misses the war room webhook from `xlm_bot/config.yaml`
- Update to also try loading from `xlm_bot/config.yaml` `slack.war_room_webhook_url`

### Verification:
```bash
curl -s -X POST "<war_room_webhook>" \
  -H 'Content-type: application/json' \
  -d '{"text":"Hive Mind war room connected."}'
```

---

## Task 3: Deploy ngrok to Oracle (now unblocked by SSH fix)

Once SSH works, execute the ngrok setup from earlier:
```bash
scp -F /root/.ssh/config 03_AUTOMATION_CORE/01_Scripts/ngrok_tunnel.sh oracle:~/
ssh oracle "chmod +x ~/ngrok_tunnel.sh && bash ~/ngrok_tunnel.sh --background"
```
User provides authtoken and sets password.

---

## Task 4: Nextcloud via Hive

Run hive session to deliberate on Nextcloud deployment:
```
hive --all "Deploy Nextcloud on Oracle Cloud VM for cross-device file sync.
VM: opc@163.192.19.196, ARM64, Ubuntu 22.04, Docker installed.
Need: Nextcloud + MariaDB via docker-compose, persistent volumes, port exposure, ngrok access."
```
Then execute the hive recommendations via the now-working SSH.

---

## Execution Order

1. Check if ncat exists at Termux path (install if missing)
2. Create `/root/.ssh/config` with ProxyCommand fix
3. Test SSH: `ssh oracle "echo OK"`
4. Update `oracle_watchdog.sh` to use SSH config
5. Wire Slack war room webhook into config + convergence
6. Test Slack webhook
7. Copy ngrok script to Oracle + set up
8. Run hive for Nextcloud
9. Deploy Nextcloud via SSH

## Risk Notes
- ncat must exist at `/data/data/com.termux/files/usr/bin/ncat` - check first
- If ProxyCommand doesn't fix key parsing, fallback: use ssh-agent in Termux and forward the agent socket
- Nextcloud on free-tier Oracle VM needs careful resource planning (2 OCPU / 12GB already running xlm_bot Docker)
