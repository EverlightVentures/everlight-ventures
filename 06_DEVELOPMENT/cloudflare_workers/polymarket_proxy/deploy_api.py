#!/usr/bin/env python3
"""Deploy the Polymarket CLOB proxy Worker via the Cloudflare API (no wrangler).

Uses the global API key from the Everlight .env. Uploads an ES-module Worker that
forwards /clob/* -> clob.polymarket.com and /gamma/* -> gamma-api.polymarket.com,
enables the workers.dev subdomain, and prints the public URL. Free tier.

Purpose: test whether Cloudflare's egress clears Polymarket's regional order
geoblock. If a real order through this URL is ACCEPTED (not 403), we are live.
"""
import json
import sys
import urllib.request
from pathlib import Path

ENV = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
NAME = "polymarket-proxy"
WORKER_JS = """
const ALLOWED = ["https://gamma-api.polymarket.com", "https://clob.polymarket.com"];
export default {
  async fetch(req) {
    const url = new URL(req.url);
    let upstream;
    if (url.pathname.startsWith("/gamma/")) upstream = "https://gamma-api.polymarket.com" + url.pathname.slice(6) + url.search;
    else if (url.pathname.startsWith("/clob/")) upstream = "https://clob.polymarket.com" + url.pathname.slice(5) + url.search;
    else return new Response("not found", {status: 404});
    if (!ALLOWED.some(u => upstream.startsWith(u + "/") || upstream === u)) return new Response("bad upstream", {status: 500});
    const h = new Headers(req.headers); h.delete("host");
    try {
      const r = await fetch(upstream, {method: req.method, headers: h,
        body: (req.method === "GET" || req.method === "HEAD") ? null : await req.arrayBuffer(),
        signal: AbortSignal.timeout(20000)});
      return new Response(r.body, {status: r.status, statusText: r.statusText, headers: r.headers});
    } catch (e) { return new Response(JSON.stringify({error: "upstream_failed", detail: String(e)}), {status: 502, headers: {"content-type": "application/json"}}); }
  }
};
"""


def env(k):
    for line in ENV.read_text().splitlines():
        if line.startswith(k + "="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def api(method, path, body=None, headers=None, raw=None, ctype=None):
    # CLOUDFLARE_API_KEY is a scoped token (cfk_ prefix) -> Bearer auth.
    token = env("CLOUDFLARE_API_TOKEN") or env("CLOUDFLARE_API_KEY")
    h = {"Authorization": f"Bearer {token}"}
    if headers:
        h.update(headers)
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if ctype:
        h["Content-Type"] = ctype
    elif body is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(f"https://api.cloudflare.com/client/v4{path}", data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def main():
    acct = env("CLOUDFLARE_ACCOUNT_ID")
    # multipart upload of an ES module worker
    boundary = "----evboundary"
    meta = json.dumps({"main_module": "worker.js", "compatibility_date": "2026-01-01"})
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"\r\nContent-Type: application/json\r\n\r\n{meta}\r\n")
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"worker.js\"; filename=\"worker.js\"\r\nContent-Type: application/javascript+module\r\n\r\n{WORKER_JS}\r\n")
    parts.append(f"--{boundary}--\r\n")
    payload = "".join(parts).encode()
    up = api("PUT", f"/accounts/{acct}/workers/scripts/{NAME}", raw=payload,
             ctype=f"multipart/form-data; boundary={boundary}")
    print("upload success:", up.get("success"), (up.get("errors") if not up.get("success") else ""))
    if not up.get("success"):
        return 2
    # enable workers.dev subdomain for the script
    api("POST", f"/accounts/{acct}/workers/scripts/{NAME}/subdomain", body={"enabled": True})
    sub = api("GET", f"/accounts/{acct}/workers/subdomain")
    subdomain = (sub.get("result") or {}).get("subdomain")
    if not subdomain:
        print("no workers.dev subdomain on account:", sub.get("errors"))
        return 3
    url = f"https://{NAME}.{subdomain}.workers.dev"
    print("WORKER URL:", url)
    print("test:", f"{url}/gamma/markets?limit=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
