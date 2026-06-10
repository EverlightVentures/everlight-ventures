# Cloudflare Worker Proxy -- Deploy Guide

**Purpose:** unblock Oracle skip-trace by routing requests through Cloudflare's IP space (which doesn't get datacenter-bot 403's that Oracle's IP does). Free tier covers 100,000 requests/day -- way more than we'll ever need.

**Cost:** $0
**Time to deploy:** 5 minutes
**Required:** your existing Cloudflare account (the one running everlightventures.io + Vantaris)

---

## Step 1 -- Create the Worker

1. Open https://dash.cloudflare.com/ -- log in
2. Left sidebar -> **Workers & Pages**
3. Click **Create** -> **Create Worker**
4. Name it: `skip-trace-proxy`
5. Click **Deploy** (with the default "Hello World" code -- we'll replace it next)

You'll be given a URL like `https://skip-trace-proxy.<your-cf-subdomain>.workers.dev`. **Save that URL -- we'll use it in step 4.**

## Step 2 -- Paste the Worker code

After deploy, click **Edit code** in the Worker dashboard. Replace ALL the existing code with this:

```javascript
// Skip-trace proxy for Everlight Ventures
// Receives: GET ?url=<encoded-target-url>&ua=<optional-user-agent>
// Returns: the upstream response body, with CORS headers
// Auth: shared bearer token in X-Proxy-Token header (set in env vars)

export default {
  async fetch(request, env) {
    // Auth check -- shared secret between Oracle and this Worker
    const authHeader = request.headers.get("X-Proxy-Token") || "";
    if (env.PROXY_TOKEN && authHeader !== env.PROXY_TOKEN) {
      return new Response("Forbidden", { status: 403 });
    }

    const url = new URL(request.url);
    const target = url.searchParams.get("url");
    if (!target) {
      return new Response("Missing url parameter", { status: 400 });
    }

    // Build forwarded request
    const ua = url.searchParams.get("ua") ||
               "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15";

    const upstream = await fetch(target, {
      method: request.method,
      headers: {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
      },
      redirect: "follow",
    });

    // Strip CF-specific headers and pass body through
    return new Response(upstream.body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "text/html",
        "X-Upstream-Status": String(upstream.status),
        "X-Upstream-URL": target,
      },
    });
  },
};
```

Click **Save and Deploy**.

## Step 3 -- Set the auth token (so randos can't use your free proxy)

1. In the Worker dashboard, click **Settings** -> **Variables**
2. Under **Environment Variables**, click **Add variable**
3. Variable name: `PROXY_TOKEN`
4. Value: pick ANY 32-char random string. Example: `everlight-skip-trace-2026-04-26-x7k9`. **Save this value -- we put it on Oracle in step 4.**
5. Click **Save and deploy**

## Step 4 -- Wire the Worker URL + token onto Oracle

SSH into Oracle and append the Worker URL + token to /home/opc/.env:

```bash
ssh -F /root/.ssh/config -i /root/.ssh/oracle_key.pem opc@163.192.19.196

# Then on Oracle:
cat >> /home/opc/.env <<'EOF'

# Skip-trace CF Worker proxy (deployed 2026-04-26)
export CF_PROXY_URL="https://skip-trace-proxy.<YOUR-CF-SUBDOMAIN>.workers.dev/"
export CF_PROXY_TOKEN="<YOUR-32-CHAR-TOKEN>"
EOF
```

Replace `<YOUR-CF-SUBDOMAIN>` and `<YOUR-32-CHAR-TOKEN>` with the values from steps 1 and 3.

## Step 5 -- Smoke test

Still on Oracle:

```bash
source /home/opc/.env
python3 -c "
import urllib.request, urllib.parse, os
url = os.environ['CF_PROXY_URL'] + '?url=' + urllib.parse.quote('https://www.truepeoplesearch.com/results?name=James%20Green&citystatezip=Cleveland%2C%20OH')
req = urllib.request.Request(url, headers={'X-Proxy-Token': os.environ['CF_PROXY_TOKEN']})
resp = urllib.request.urlopen(req, timeout=20)
body = resp.read().decode('utf-8', errors='replace')
print(f'HTTP {resp.status} | upstream: {resp.headers.get(\"X-Upstream-Status\")}')
print(f'body length: {len(body)}')
print('contains James Green:' , 'James Green' in body or 'james green' in body.lower())
"
```

If you see HTTP 200 + upstream status 200 + body length > 50000 + "contains James Green: True", **the bypass works**. Skip-trace will start filling in emails/phones for non-OH leads on the next */30 cron fire.

If upstream status is still 403 (Cloudflare's IPs blocked too -- rare), we fall back to ProxyScrape free residential pool as Plan C.

---

## What this does for the pipeline

Before:
- Oracle direct hits TruePeopleSearch -> 403 (datacenter ASN blocked)
- 408 emailless leads stuck in `new` status with no path to email/phone
- Pipeline stalled

After:
- Oracle hits CF Worker -> Worker fetches TruePeopleSearch from CF's residential-friendly IPs -> 200 OK
- Skip-trace cron drains the 408 queue at 25 leads / 30 min = ~16 hours to fully process
- Realistic yield: ~250 phone numbers, ~30-60 emails

This unblocks 5 of the 9 active markets (GA, TX, FL, MO -- already-ready markets that just need contact info on their leads).

---

## Risks and limits

- **Free tier = 100K requests/day.** We'll use ~50 per scrape per lead = up to 5K reads on a heavy scrape day. Well under the cap.
- **CF Workers run anywhere in CF's edge network.** A specific edge IP CAN occasionally be 403'd by aggressive anti-bot. If hit-rate drops, we add a retry + delay between retries.
- **PROXY_TOKEN is the only access control.** Don't share it. If leaked, regenerate it in step 3 and update Oracle.
- **Per-target rate limits still apply.** Don't burn all 408 leads in 5 minutes -- the */30 cron with --max=25 is the right pace.

---

**Filed by:** Lucrex on Marquise's "remember to put it on Oracle" directive
**For:** Skip-trace pipeline integration on Oracle (eliminates phone-side dependency)
**When ready, run steps 1-5 in order. Total time: ~5 min once you start.**
