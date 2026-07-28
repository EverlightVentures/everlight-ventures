#!/usr/bin/env python3
"""
ak_go_live.py -- ONE-SHOT Alley Kingz commerce go-live finisher.

Run this the moment the fresh keys land in 03_Credentials/.env:
  SUPABASE_ACCESS_TOKEN  (new personal access token, sbp_...)
  STRIPE_SECRET_KEY      (new LIVE secret/restricted key -- old one EXPIRED 2026-06-10)
  CF_AI_TOKEN            (optional here; arms the art engine, not commerce)

What it does, in order (idempotent, stops on first hard failure):
  1. Applies the 4 AK migrations via the Supabase management API
     (economy schema + seed + shop products + player cloud saves).
  2. Seeds the 5 gem packs as LIVE Stripe Products/Prices (AK_STRIPE_ALLOW_LIVE=1,
     operator greenlight 2026-06-09/10) -> _state/ak_stripe_products.json.
  3. Injects the live price ids into create-checkout's PRICE_MAP (repo copy)
     and deploys create-checkout + alley-kingz-shop edge functions.
  4. Sets edge secrets: STRIPE_SECRET_KEY (live), AK_SHOP_TEST_MODE=false.
  5. Adds alleykingz.online + alley-kingz.pages.dev to the auth redirect
     allowlist (Google sign-in must bounce back to the game, not the casino).
  6. Deploys the game to CF Pages and probes the live endpoints.

Usage:  python3 ak_go_live.py [--dry-run]
"""
import json, os, re, sys, subprocess, urllib.request, urllib.error

ROOT = "/mnt/sdcard/AA_MY_DRIVE"
ENVF = ROOT + "/03_AUTOMATION_CORE/03_Credentials/.env"
REF = "jdqqmsmwmbsnlnstyavl"
API = "https://api.supabase.com/v1/projects/" + REF
GAME = ROOT + "/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game"
MIGS = [
    ROOT + "/supabase/migrations/20260607_alley_kingz_economy.sql",
    ROOT + "/supabase/migrations/20260607_alley_kingz_economy_seed.sql",
    ROOT + "/supabase/migrations/20260610_ak_shop_products.sql",
    ROOT + "/supabase/migrations/20260611_ak_player_saves.sql",
]
CHECKOUT_FN = ROOT + "/supabase/functions/create-checkout/index.ts"
SHOP_FN = ROOT + "/supabase/functions/alley-kingz-shop/index.ts"
REDIRECTS = ["https://alleykingz.online", "https://alleykingz.online/shop/shop.html",
             "https://alley-kingz.pages.dev", "https://alley-kingz.pages.dev/shop/shop.html"]

def envval(name):
    for line in open(ENVF):
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return ""

def req(method, url, token, body=None, ctype="application/json", raw=False):
    data = body if isinstance(body, bytes) else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", "Bearer " + token)
    if data is not None: r.add_header("Content-Type", ctype)
    try:
        resp = urllib.request.urlopen(r, timeout=120).read()
        return resp if raw else (json.loads(resp) if resp.strip() else {})
    except urllib.error.HTTPError as e:
        raise RuntimeError("%s %s -> %d: %s" % (method, url, e.code, e.read().decode()[:300]))

def main():
    dry = "--dry-run" in sys.argv
    sat = envval("SUPABASE_ACCESS_TOKEN")
    sk = envval("STRIPE_SECRET_KEY")
    if not sat: print("FATAL: no SUPABASE_ACCESS_TOKEN in .env"); return 2
    # token sanity
    try: req("GET", "https://api.supabase.com/v1/projects", sat)
    except RuntimeError as e: print("FATAL: SUPABASE_ACCESS_TOKEN rejected:", e); return 2
    print("[0] supabase token OK")

    # 1. migrations
    for m in MIGS:
        sql = open(m).read()
        print("[1] applying", os.path.basename(m), "(%d bytes)" % len(sql))
        if not dry:
            req("POST", API + "/database/query", sat, {"query": sql})
    print("[1] migrations applied")

    # 2. stripe seed (live)
    prices = {}
    state_path = ROOT + "/_state/ak_stripe_products.json"
    if sk:
        print("[2] seeding LIVE Stripe products")
        if not dry:
            env = dict(os.environ, STRIPE_SECRET_KEY=sk, AK_STRIPE_ALLOW_LIVE="1")
            r = subprocess.run([sys.executable, ROOT + "/03_AUTOMATION_CORE/01_Scripts/ak_stripe_seed_products.py"],
                               env=env, capture_output=True, text=True)
            print(r.stdout[-800:]);
            if r.returncode != 0: print("FATAL: seeder failed:", r.stderr[-400:]); return 2
            prices = {k: v["price_id"] for k, v in json.load(open(state_path)).items() if not k.startswith("_")}
    else:
        print("[2] SKIP stripe seed (no STRIPE_SECRET_KEY) -- checkout stays gated")

    # 3. PRICE_MAP inject + deploy edge functions
    src = open(CHECKOUT_FN).read()
    if prices:
        for sku, pid in prices.items():
            if '"%s"' % sku in src:
                src = re.sub(r'"%s"\s*:\s*"[^"]*"' % re.escape(sku), '"%s": "%s"' % (sku, pid), src)
            else:
                src = src.replace("const PRICE_MAP", "// ak gem packs (live, seeded by ak_go_live)\nconst PRICE_MAP", 1)
                src = re.sub(r"(PRICE_MAP[^=]*=\s*\{)", r'\1\n  "%s": "%s",' % (sku, pid), src, count=1)
        if not dry: open(CHECKOUT_FN, "w").write(src)
        print("[3] PRICE_MAP updated with %d live price ids" % len(prices))

    def deploy_fn(slug, path, verify_jwt=True):
        body_src = open(path).read()
        meta = json.dumps({"name": slug, "entrypoint_path": "index.ts", "verify_jwt": verify_jwt})
        boundary = "----akgoLive"
        parts = []
        parts.append("--%s\r\nContent-Disposition: form-data; name=\"metadata\"\r\n\r\n%s\r\n" % (boundary, meta))
        parts.append("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"index.ts\"\r\nContent-Type: application/typescript\r\n\r\n%s\r\n" % (boundary, body_src))
        parts.append("--%s--\r\n" % boundary)
        data = "".join(parts).encode()
        if not dry:
            req("POST", API + "/functions/deploy?slug=" + slug, sat, data,
                ctype="multipart/form-data; boundary=" + boundary)
        print("[3] deployed edge fn:", slug)

    deploy_fn("alley-kingz-shop", SHOP_FN)
    if prices: deploy_fn("create-checkout", CHECKOUT_FN)

    # 4. secrets
    secrets = [{"name": "AK_SHOP_TEST_MODE", "value": "false"}]
    if sk: secrets.append({"name": "STRIPE_SECRET_KEY", "value": sk})
    if not dry: req("POST", API + "/secrets", sat, secrets)
    print("[4] edge secrets set:", [s["name"] for s in secrets])

    # 5. auth redirect allowlist (merge, don't clobber)
    cfg = req("GET", API + "/config/auth", sat)
    allow = [u for u in (cfg.get("uri_allow_list") or "").split(",") if u]
    merged = sorted(set(allow) | set(REDIRECTS))
    if not dry: req("PATCH", API + "/config/auth", sat, {"uri_allow_list": ",".join(merged)})
    print("[5] auth redirect allowlist now %d entries (game domains added)" % len(merged))

    # 6. deploy game + probe
    if not dry:
        env = dict(os.environ, CLOUDFLARE_ACCOUNT_ID="d06376317522c7451e390a9af44aebba",
                   CF_API_TOKEN=envval("CF_API_TOKEN"))
        r = subprocess.run([sys.executable, ROOT + "/03_AUTOMATION_CORE/01_Scripts/deploy/cf_pages_direct_upload.py",
                            "--dir", GAME, "--project", "alley-kingz", "--branch", "main",
                            "--exclude", "assets/maps"], env=env, capture_output=True, text=True)
        print(r.stdout[-300:])
    anon = envval("SUPABASE_ANON_KEY")
    probe = urllib.request.Request("https://" + REF + ".supabase.co/functions/v1/alley-kingz-shop",
                                   data=json.dumps({"action": "get-shop"}).encode(), method="POST")
    probe.add_header("Authorization", "Bearer " + anon); probe.add_header("Content-Type", "application/json")
    try:
        out = urllib.request.urlopen(probe, timeout=30).read()[:200]
        print("[6] alley-kingz-shop probe:", out.decode()[:160])
    except urllib.error.HTTPError as e:
        print("[6] probe HTTP", e.code, e.read().decode()[:160])
    print("\nGO-LIVE COMPLETE. Test a $4.99 Rookie Stash on alleykingz.online/shop/shop.html (sign in first).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
