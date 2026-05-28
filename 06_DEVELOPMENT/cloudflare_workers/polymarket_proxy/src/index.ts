export interface Env {
  UPSTREAM_GAMMA: string;
  UPSTREAM_CLOB: string;
}

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

    const proxied = new Request(upstream, {
      method: req.method,
      headers: req.headers,
      body: req.method === "GET" || req.method === "HEAD" ? null : req.body,
    });
    const resp = await fetch(proxied);
    return new Response(resp.body, {
      status: resp.status,
      statusText: resp.statusText,
      headers: resp.headers,
    });
  },
};
