# polymarket-proxy

Cloudflare Worker that proxies Polymarket gamma + CLOB API.

Routes:
- `clob-proxy.everlightventures.io/gamma/*` -> `gamma-api.polymarket.com/*`
- `clob-proxy.everlightventures.io/clob/*` -> `clob.polymarket.com/*`

## Prerequisites

Before deploy, the operator must add a DNS record in the everlightventures.io
Cloudflare zone:
- Type: CNAME (or A pointing to the orange-cloud-proxied IP)
- Name: clob-proxy
- Target: anything CF-proxied (e.g. 100:: -- CF will route via Workers regardless)
- Proxy status: Proxied (orange cloud)

Without this DNS record, wrangler deploy succeeds but the Worker is unreachable.

## Deploy

```bash
cd 06_DEVELOPMENT/cloudflare_workers/polymarket_proxy
npm install
npx wrangler login   # one-time
npm run deploy
```

Cost: $0 (100k req/day free tier; our peak is ~3k req/day).
