export interface Env {
  UPSTREAM_GAMMA: string;
  UPSTREAM_CLOB: string;
}

// Hardcoded allowlist -- wrangler.toml [vars] values are advisory only.
// The Worker fails closed if env is misconfigured or tampered.
const ALLOWED_UPSTREAMS = [
  "https://gamma-api.polymarket.com",
  "https://clob.polymarket.com",
];

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const path = url.pathname;
    const search = url.search;

    let upstream: string;
    if (path.startsWith("/gamma/")) {
      upstream = env.UPSTREAM_GAMMA + path.slice("/gamma".length) + search;
    } else if (path.startsWith("/clob/")) {
      upstream = env.UPSTREAM_CLOB + path.slice("/clob".length) + search;
    } else {
      return new Response("not found", { status: 404 });
    }

    // C1: Validate upstream against hardcoded allowlist before forwarding
    // auth headers or any request data.
    if (!ALLOWED_UPSTREAMS.some(u => upstream.startsWith(u + "/") || upstream === u)) {
      return new Response(
        JSON.stringify({ error: "upstream_not_allowed", upstream }),
        { status: 500, headers: { "content-type": "application/json" } },
      );
    }

    const proxied = new Request(upstream, {
      method: req.method,
      headers: req.headers,
      body: req.method === "GET" || req.method === "HEAD" ? null : req.body,
    });

    // I2 + I3: 10s timeout + structured error body on fetch failure
    try {
      const resp = await fetch(proxied, { signal: AbortSignal.timeout(10_000) });
      return new Response(resp.body, {
        status: resp.status,
        statusText: resp.statusText,
        headers: resp.headers,
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: "upstream_fetch_failed", detail: String(err) }),
        { status: 502, headers: { "content-type": "application/json" } },
      );
    }
  },
};
