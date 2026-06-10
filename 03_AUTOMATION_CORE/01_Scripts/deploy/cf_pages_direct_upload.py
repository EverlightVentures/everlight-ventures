#!/usr/bin/env python3
"""
CLOUDFLARE PAGES -- DIRECT UPLOAD (wrangler-free)
=================================================
THE durable deploy path from this phone-proot. `wrangler` SEGFAULTS here
(exit 139 -- the bundled native CLI crashes on aarch64/proot; the bin wrapper
masks it as a silent exit 0). So we reimplement Cloudflare's Direct-Upload
flow with pure stdlib + blake3, exactly as wrangler does it under the hood:

  1. GET  /accounts/{acct}/pages/projects/{proj}/upload-token        -> jwt
  2. hash every file: blake3( base64(bytes) + extension_no_dot ).hex()[:32]
  3. POST /pages/assets/check-missing   (Bearer jwt)  -> which hashes to upload
  4. POST /pages/assets/upload          (Bearer jwt)  -> [{key,value,metadata,base64}]
  5. POST /accounts/{acct}/pages/projects/{proj}/deployments (Bearer token,
         multipart) with field manifest={path:hash} + branch -> creates deploy

Auth: CF_API_TOKEN from secrets_vault (account-scoped, works for /accounts+/pages).
The base64+extension hashing is wrangler's exact quirk -- get it wrong and the
manifest won't validate.

RUN:
  python3 cf_pages_direct_upload.py --dir <build_dir> --project alley-kingz --branch main

Requires: pip install --break-system-packages blake3   (already installed on phone)
"""
import os, sys, json, base64, time, argparse, mimetypes, urllib.request, urllib.error

API = "https://api.cloudflare.com/client/v4"
VAULT = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/secrets_vault.py"


def vault_get(name):
    import subprocess
    try:
        out = subprocess.run([sys.executable, VAULT, "get", name],
                             capture_output=True, text=True, timeout=30)
        v = (out.stdout or "").strip()
        return v or None
    except Exception:
        return None


def blake3_hash(b64_str, ext):
    from blake3 import blake3
    return blake3((b64_str + ext).encode("utf-8")).hexdigest()[:32]


def http(method, url, token, body=None, headers=None, is_json=True, timeout=180):
    h = {"Authorization": "Bearer " + token}
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        if is_json:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        else:
            data = body  # raw bytes (multipart sets its own Content-Type via headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:500]}


def collect_files(root, exclude=None):
    files = []
    root = os.path.abspath(root)
    SPECIAL = {"_headers", "_redirects", "_routes.json", "_worker.js"}
    exclude = exclude or []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel in SPECIAL or rel.split("/")[-1] in SPECIAL:
                continue
            if any(rel.startswith(p) for p in exclude):
                continue
            files.append((rel, full))
    return sorted(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--project", required=True)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--exclude", default="", help="comma-separated relpath prefixes to skip (e.g. assets/maps)")
    ap.add_argument("--account", default=os.environ.get("CLOUDFLARE_ACCOUNT_ID",
                    "d06376317522c7451e390a9af44aebba"))
    args = ap.parse_args()

    token = os.environ.get("CF_API_TOKEN") or vault_get("CF_API_TOKEN")
    if not token:
        print("FATAL: no CF_API_TOKEN (env or vault)"); return 2
    acct = args.account

    # 1. upload token (jwt)
    st, resp = http("GET", f"{API}/accounts/{acct}/pages/projects/{args.project}/upload-token", token)
    if not resp.get("success"):
        print("FATAL upload-token:", st, json.dumps(resp)[:400]); return 2
    jwt = resp["result"]["jwt"]
    print(f"[1/5] got upload jwt (len {len(jwt)})")

    # 2. hash files
    files = collect_files(args.dir, [p for p in args.exclude.split(",") if p])
    manifest = {}
    blobs = {}  # hash -> (b64, contentType)
    for rel, full in files:
        with open(full, "rb") as fh:
            content = fh.read()
        b64 = base64.b64encode(content).decode("ascii")
        ext = os.path.splitext(rel)[1].lstrip(".")
        h = blake3_hash(b64, ext)
        manifest["/" + rel] = h
        ct = mimetypes.guess_type(rel)[0] or "application/octet-stream"
        blobs[h] = (b64, ct)
    print(f"[2/5] hashed {len(files)} files ({len(blobs)} unique blobs)")

    # 3. check-missing
    all_hashes = list(blobs.keys())
    st, resp = http("POST", f"{API}/pages/assets/check-missing", jwt, body={"hashes": all_hashes})
    if not resp.get("success"):
        print("FATAL check-missing:", st, json.dumps(resp)[:400]); return 2
    missing = resp["result"] or []
    print(f"[3/5] {len(missing)} of {len(all_hashes)} blobs need upload")

    # 4. upload missing, batched by cumulative payload size (~10MB) or 40 files
    to_up = missing if missing else []
    batch, batch_bytes, uploaded = [], 0, 0
    BUDGET = 600 * 1024   # tiny batches survive flaky phone uplinks (was 10MB)

    def flush(batch):
        nonlocal uploaded
        if not batch:
            return
        for attempt in range(8):
            st, resp = http("POST", f"{API}/pages/assets/upload", jwt, body=batch, timeout=300)
            if resp.get("success"):
                uploaded += len(batch)
                return
            print(f"  upload retry {attempt+1}: {st} {json.dumps(resp)[:200]}")
            time.sleep(2 + attempt * 2)
        raise SystemExit("FATAL: upload batch failed after retries")

    for h in to_up:
        b64, ct = blobs[h]
        item = {"key": h, "value": b64, "metadata": {"contentType": ct}, "base64": True}
        sz = len(b64)
        if batch and (batch_bytes + sz > BUDGET or len(batch) >= 40):
            flush(batch); batch, batch_bytes = [], 0
        batch.append(item); batch_bytes += sz
    flush(batch)
    print(f"[4/5] uploaded {uploaded} blobs")

    # 5. create deployment (multipart: manifest + branch)
    boundary = "----ak" + str(len(files)) + "boundary7707"
    parts = []

    def add_field(name, value):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n')

    add_field("manifest", json.dumps(manifest))
    add_field("branch", args.branch)
    # _headers / _redirects are NOT hashed assets -- Cloudflare takes them as
    # raw multipart fields on deployment-create. Pass through if present.
    for special in ("_headers", "_redirects"):
        sp = os.path.join(os.path.abspath(args.dir), special)
        if os.path.isfile(sp):
            with open(sp, "r", encoding="utf-8") as fh:
                add_field(special, fh.read())
            print(f"      + included {special}")
    bodytxt = "".join(parts) + f"--{boundary}--\r\n"
    body = bodytxt.encode("utf-8")
    st, resp = http("POST", f"{API}/accounts/{acct}/pages/projects/{args.project}/deployments",
                    token, body=body, is_json=False,
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    if not resp.get("success"):
        print("FATAL deploy create:", st, json.dumps(resp)[:600]); return 2
    r = resp["result"]
    print(f"[5/5] DEPLOYED -> {r.get('url')}  id={r.get('id')}")
    print("PROD ALIAS: https://%s.pages.dev" % args.project)
    return 0


if __name__ == "__main__":
    sys.exit(main())
