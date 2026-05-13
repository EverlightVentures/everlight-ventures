# Cloudflare Tunnel Activation -- Handoff for Rich
**Date:** 2026-05-13
**Why this lives in a handoff doc:** Auto-mode classifier (correctly) blocks both
(a) downloading + installing an arbitrary binary as root, and (b) browser-auth flows
that need Rich's Cloudflare account login. This file gives Rich the exact 4 commands
to copy-paste when he's ready, with no surprises.

---

## What this unlocks

Once this tunnel is live, the autonomous deal engine can send REAL emails to Mikal
Hakeem (and any future seller / buyer) with sign URLs they can actually click.
Current state: every `intel deal launch <key>` produces an M7 contract package with
embedded `http://127.0.0.1:2302/sign/<token>` URLs that ONLY Rich's phone can open.
That's why we've been simulating on Rich's own inbox.

After the tunnel: those URLs become `https://esign.everlightventures.io/sign/<token>`
and work from anywhere. The deal engine goes from simulation-grade to production-grade.

The same tunnel will host:
- `esign.everlightventures.io` -> phone:2302 (E-Sign + Wire + Signatures dashboard)
- `reports.everlightventures.io` -> phone:2200 (branded HTML reports)

Both are tokenized at the application layer; cloudflare-side is a thin TLS passthrough.

---

## The 4 commands

### 1. Install cloudflared (one-time)

```bash
# In your Ubuntu proot shell:
curl -L -o /tmp/cloudflared \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
chmod +x /tmp/cloudflared
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
cloudflared --version
# expect: cloudflared version 2024.x.x (built xxxx)
```

### 2. Authenticate to your Cloudflare account (one-time, browser)

```bash
cloudflared tunnel login
```

This opens a Cloudflare URL in your browser. Log in with the account that owns
`everlightventures.io`, pick the zone, and Cloudflare drops a cert file at
`~/.cloudflared/cert.pem`. Then close the browser.

### 3. Create the tunnel + write config

```bash
# Create the tunnel (Cloudflare gives you a UUID)
cloudflared tunnel create everlight-esign
# Note the UUID it prints; you'll need it.

# Find the credentials file
ls ~/.cloudflared/*.json
# Example: /root/.cloudflared/abc123def456.json

# Write the config (replace <UUID> with the one from `tunnel create`):
cat > ~/.cloudflared/config.yml <<'EOF'
tunnel: <UUID>
credentials-file: /root/.cloudflared/<UUID>.json
ingress:
  - hostname: esign.everlightventures.io
    service: http://localhost:2302
  - hostname: reports.everlightventures.io
    service: http://localhost:2200
  - service: http_status:404
EOF

# Add DNS routes so the hostnames resolve to the tunnel
cloudflared tunnel route dns everlight-esign esign.everlightventures.io
cloudflared tunnel route dns everlight-esign reports.everlightventures.io
```

### 4. Run the tunnel + verify

```bash
# Test it in foreground first
cloudflared tunnel run everlight-esign
# In another shell or browser: curl -sI https://esign.everlightventures.io/healthz
# Expect: HTTP/2 200

# When verified, run as a background daemon
pkill -f "cloudflared tunnel run" 2>/dev/null
nohup cloudflared tunnel run everlight-esign > /tmp/cloudflared.log 2>&1 &
echo "tunnel pid: $!"
```

---

## After tunnel is live -- I'll do these

Once you confirm "tunnel is up," I will (no more permission prompts needed):

1. **Add cloudflared to `dashboards_watchdog.sh`** as an 8th service (process-name
   watch, not port watch -- cloudflared doesn't bind a local port).
2. **Set `EVERLIGHT_PUBLIC_HOST=esign.everlightventures.io` in `~/.zshrc`** so all
   future `esign_server.py` token URLs prefer the public hostname.
3. **Patch `esign_server.py:_public_url()`** to read that env var. If set, build
   URLs like `https://esign.everlightventures.io/sign/<token>` instead of
   `http://127.0.0.1:2302/sign/<token>`.
4. **Patch `arc_send.py`** -- the M7 contract package and Hammer's c_assignment
   email both embed sign URLs. Both call `_public_url()` (after step 3 above).
5. **Smoke test**: `intel deal launch test_self` -> click the M7 link from your
   phone -> verify the sign page loads via cloudflared.

---

## Failure modes + manual rollback

| Symptom | Cause | Fix |
|---|---|---|
| `cloudflared tunnel login` browser doesn't open | proot has no browser | Copy the URL it prints, open in phone browser, complete the flow, return |
| `tunnel run` exits with "no tunnel found" | UUID typo in config | Re-check `ls ~/.cloudflared/*.json` |
| DNS doesn't resolve after 5 min | DNS propagation lag | Wait 5-10 more min; Cloudflare DNS is usually instant |
| `curl https://esign.../healthz` returns 530 (cloudflare origin) | tunnel isn't running locally | `ps aux | grep cloudflared` -- restart |
| You want to rip it out | -- | `pkill -f cloudflared`; `cloudflared tunnel delete everlight-esign`; `rm -rf ~/.cloudflared` |

---

## Security note

The tunnel exposes ONLY ports 2302 and 2200 to the public internet, gated through
Cloudflare's network. Application-layer auth (tokenized URLs on :2302, static
report file system on :2200) is what actually protects the content. The tunnel
itself is TLS + a tiny TCP forward.

Don't add ports to the ingress list lightly. If you ever want to add :2000 (master
hub) or :2300 (intel center) to the tunnel, those would expose internal admin
surfaces with NO additional auth -- they'd need tokenized URLs added first.

---

## Why I couldn't do steps 1-4 for you

Auto-mode classifier rules (which are correct safeguards):
- **Step 1** -- downloading + chmod +x'ing a binary as root is "Code from External"
- **Step 2** -- browser auth flow needs your hands on the keyboard
- **Step 3** -- writing to `~/.cloudflared/config.yml` and creating tunnels affects
  your Cloudflare account state, which only you can authorize
- **Step 4** -- starting an internet-exposed daemon needs explicit go-ahead

When you've finished these 4 manual steps and the tunnel is up, ping me with
"tunnel is up" and I'll wire steps 1-5 of the after-tunnel-is-live section in one shot.
