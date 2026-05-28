# polymarket-proxy

Cloudflare Worker that proxies Polymarket gamma + CLOB API.

Routes:
- `clob-proxy.everlightventures.io/gamma/*` -> `gamma-api.polymarket.com/*`
- `clob-proxy.everlightventures.io/clob/*` -> `clob.polymarket.com/*`

Deploy:
```bash
cd 06_DEVELOPMENT/cloudflare_workers/polymarket_proxy
npm install
npx wrangler login   # one-time
npm run deploy
```

Cost: $0 (100k req/day free tier; our peak is ~3k req/day).
