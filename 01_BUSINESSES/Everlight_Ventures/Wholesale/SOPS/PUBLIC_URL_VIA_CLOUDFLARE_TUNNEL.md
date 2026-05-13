# Public URL for Esign + Wire Forms via Cloudflare Tunnel

**Problem**: `http://127.0.0.1:2302/sign/<token>` only resolves on the phone running the
esign server. Real recipients (Mikal at `mhakeem@timemphis.org`, Chris at
`leads@midsouthhomebuyers.com`) cannot click the link from their inboxes; their
browsers can't reach 127.0.0.1 on Rich's phone.

**Symptom Rich hit**: clicking the M7 sign URL from his Gmail "led to something
broken" — Gmail's link-prefetch and any non-phone device returns connection refused.

**Fix**: Cloudflare Tunnel. Free. Gives a public hostname that proxies to phone:2302.
No port-forwarding, no DDNS, no inbound firewall changes. Set up once, runs forever.

---

## Why Cloudflare Tunnel beats the alternatives

| Option | Cost | Trade-off |
|---|---|---|
| **Cloudflare Tunnel** | Free (uses your existing CF account) | Best uptime, custom domain, no rate limits, TLS auto-issued |
| ngrok free | Free | Subdomain rotates per restart, 4h session cap, painful |
| ngrok paid | $8-20/mo | Stable subdomain but Cloudflare is free with same quality |
| Tailscale Funnel | Free | Public URL but requires Cloudflare-equivalent setup; works |
| Re-host on Oracle when reachable | $0 incremental | Oracle Micro is dead since 2026-04-30; not a near-term option |
| Cloudflare Pages + Workers | Free | Server is in browser, can't run Python uvicorn there |

Cloudflare Tunnel is the right pick. We already use Cloudflare for
`everlightventures.io` (per CLAUDE.md), so the account exists.

---

## One-time setup (15 minutes)

### Step 1 — Install cloudflared on the phone

```bash
# Termux:
pkg install cloudflared

# Verify:
cloudflared --version
```

If `pkg` doesn't have it, download the ARM64 Linux binary from
https://github.com/cloudflare/cloudflared/releases/latest and chmod +x.

### Step 2 — Authenticate cloudflared with your Cloudflare account

```bash
cloudflared tunnel login
```

This opens a browser to log into your Cloudflare account and authorize the
tunnel client. Pick the `everlightventures.io` zone when prompted.

### Step 3 — Create the tunnel

```bash
cloudflared tunnel create esign-tunnel
```

This generates a UUID for the tunnel + writes credentials to
`~/.cloudflared/<UUID>.json`. Save the UUID; you'll reference it by name from here.

### Step 4 — Add a DNS route

Pick a subdomain, e.g. `esign.everlightventures.io`:

```bash
cloudflared tunnel route dns esign-tunnel esign.everlightventures.io
```

Cloudflare automatically creates a CNAME record pointing `esign.everlightventures.io`
at the tunnel UUID. No manual DNS work.

### Step 5 — Configure the tunnel to proxy to phone:2302

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: esign-tunnel
credentials-file: /root/.cloudflared/<UUID>.json

ingress:
  - hostname: esign.everlightventures.io
    service: http://127.0.0.1:2302
  - service: http_status:404
```

### Step 6 — Run the tunnel

```bash
# Foreground (test):
cloudflared tunnel run esign-tunnel

# Background (production):
nohup cloudflared tunnel run esign-tunnel > /tmp/cloudflared.log 2>&1 &
disown

# Or as a Termux boot service:
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start_cloudflared.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 30  # wait for network
cloudflared tunnel run esign-tunnel >> /mnt/sdcard/AA_MY_DRIVE/_logs/cloudflared.log 2>&1 &
EOF
chmod +x ~/.termux/boot/start_cloudflared.sh
```

### Step 7 — Verify

From any device (laptop, another phone):

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://esign.everlightventures.io/healthz
# Expect: 200
```

If 200: anyone with a valid token URL can now sign from any device. Done.

---

## Update the esign server to mint public URLs

Once the tunnel is up, change one constant in `arc_send.py` and `esign_server.py`
so generated URLs use the public hostname instead of 127.0.0.1.

### Change in `arc_send.py:m7_contract` and `c_assignment`

```python
# OLD:
sign_url = f"http://127.0.0.1:2302/sign/{token}"

# NEW:
PUBLIC_ESIGN_HOST = os.environ.get("ESIGN_PUBLIC_HOST", "https://esign.everlightventures.io")
sign_url = f"{PUBLIC_ESIGN_HOST}/sign/{token}"
```

### Change in `esign_server.py:sign_form` (iframe doc URL)

```python
# OLD:
doc_url = f"/doc/{token}/{doc_id}"  # this stays relative -- works regardless of host

# NEW: still relative; no change needed since the iframe loads from same origin
```

The doc iframe stays relative (`/doc/...`) because the browser loads it from the
same origin as the sign page. So when the sign page is at
`https://esign.everlightventures.io/sign/<token>`, the iframe automatically loads
from `https://esign.everlightventures.io/doc/<token>/01_PSA`. No change needed.

### Add the env var to phone shell

```bash
echo 'export ESIGN_PUBLIC_HOST="https://esign.everlightventures.io"' >> ~/.bashrc
source ~/.bashrc
```

---

## Security notes

- Tunnels expose ONLY the routes Cloudflare proxies. The sign server stays bound
  to 127.0.0.1; the tunnel is the only inbound path.
- Token-gated `/doc/<token>/<file>` route is HMAC-protected. Even with a public
  hostname, only a valid token unlocks a contract.
- Tokens TTL = 168 hours (7 days). After expiry the URL 410s.
- `audit_log` captures every doc view + sign + IP at the time of access. Cloudflare
  tunnel passes through the client IP via `CF-Connecting-IP` header (already
  captured by FastAPI's `request.client.host` because we read the header).
- Add Cloudflare Access (free for up to 50 users) for an extra layer if you want
  to require email-link verification before the URL even renders.

---

## Daily operations

```bash
# Start (one-shot)
nohup cloudflared tunnel run esign-tunnel > /tmp/cloudflared.log 2>&1 &

# Status
cloudflared tunnel info esign-tunnel

# Stop
pkill cloudflared

# Tail log
tail -f /tmp/cloudflared.log

# Verify from external network
curl -I https://esign.everlightventures.io/healthz
```

---

## When to set this up

- **Before the first real send to Mikal at `mhakeem@timemphis.org`** (Day 0 of
  going live). Until then, all M7 / sign URLs only work on the phone, which is
  fine for self-tests but kills the autonomous loop with real counterparties.
- **After Deal 1 commission**, this also enables:
  - Wire confirmation form public URL (`/wire/<deal_key>` accessible to title firm)
  - Settlement statement preview public URL (Chris reviews from his desktop)
  - PDF certificate downloads from anywhere

---

## Cost summary

- Cloudflare Tunnel: $0 (uses existing CF account on your `everlightventures.io` zone)
- DNS record: $0 (already paying for the domain)
- TLS cert: $0 (Cloudflare auto-issues + auto-renews)
- **Total**: $0 for unlimited bandwidth + uptime

This is the right answer per the autonomous-stack-first doctrine in memory:
self-hosted free path, no DocuSign $25/mo, no ngrok subscription.
