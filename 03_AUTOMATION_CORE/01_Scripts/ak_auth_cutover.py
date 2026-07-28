#!/usr/bin/env python3
"""
ak_auth_cutover.py -- flip Alley Kingz onto its OWN Supabase project + Google client.

Per AUTH_SEPARATION_DOCTRINE.md (operator hard law 2026-06-11): two games, two
logins, two accounts. Run AFTER Rich creates the "Alley Kingz" Google OAuth client
and drops these in 03_Credentials/.env:
  AK_GOOGLE_CLIENT_ID=...apps.googleusercontent.com
  AK_GOOGLE_CLIENT_SECRET=GOCSPX-...

Already in .env (provisioned 2026-06-11): AK_SUPABASE_URL / AK_SUPABASE_ANON_KEY /
AK_SUPABASE_SERVICE_ROLE_KEY / AK_SUPABASE_DB_PASS / SUPABASE_ACCESS_TOKEN.
New project mfghdobptredxxhbjwyz already has: all 4 migrations, alley-kingz-shop +
create-checkout edge fns, live Stripe secrets, site_url=alleykingz.online,
game-domain-only redirect allowlist.

What this does:
  1. Enables Google on the AK project with the AK-branded client.
  2. Rewrites game client constants (ak_account.js SB_URL/SB_ANON, shop/shop.js FN)
     to the AK project.
  3. Prints the e5 deploy command to ship it (phone radio unreliable).
Players who signed in on the shared project get fresh accounts on first login
(expected: cutover is happening day-1, before a real player base).
"""
import json, re, sys, urllib.request

ROOT = "/mnt/sdcard/AA_MY_DRIVE"
ENVF = ROOT + "/03_AUTOMATION_CORE/03_Credentials/.env"
REF = "mfghdobptredxxhbjwyz"
GAME = ROOT + "/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game"

def envval(n):
    for l in open(ENVF):
        if l.startswith(n + "="): return l.split("=", 1)[1].strip().strip('"')
    return ""

def main():
    sat = envval("SUPABASE_ACCESS_TOKEN")
    cid = envval("AK_GOOGLE_CLIENT_ID"); csec = envval("AK_GOOGLE_CLIENT_SECRET")
    anon = envval("AK_SUPABASE_ANON_KEY")
    if not (cid and csec): print("FATAL: AK_GOOGLE_CLIENT_ID / AK_GOOGLE_CLIENT_SECRET missing in .env"); return 2
    if not (sat and anon): print("FATAL: missing SUPABASE_ACCESS_TOKEN or AK_SUPABASE_ANON_KEY"); return 2

    # 1. enable Google on the AK project
    body = json.dumps({"external_google_enabled": True,
                       "external_google_client_id": cid,
                       "external_google_secret": csec}).encode()
    rq = urllib.request.Request("https://api.supabase.com/v1/projects/%s/config/auth" % REF,
                                data=body, method="PATCH")
    rq.add_header("Authorization", "Bearer " + sat); rq.add_header("Content-Type", "application/json")
    urllib.request.urlopen(rq, timeout=60)
    print("[1] Google enabled on AK project (AK-branded client)")

    # 2. flip client constants
    a = open(GAME + "/ak_account.js").read()
    a = re.sub(r'var SB_URL = "https://[a-z]+\.supabase\.co"',
               'var SB_URL = "https://%s.supabase.co"' % REF, a)
    a = re.sub(r'var SB_ANON = "[^"]+"', 'var SB_ANON = "%s"' % anon, a)
    open(GAME + "/ak_account.js", "w").write(a)
    s = open(GAME + "/shop/shop.js").read()
    s = re.sub(r'var SUPABASE_URL = "https://[a-z]+\.supabase\.co"',
               'var SUPABASE_URL = "https://%s.supabase.co"' % REF, s)
    open(GAME + "/shop/shop.js", "w").write(s)
    print("[2] game client flipped to AK project")

    print("[3] ship it from e5 (phone radio unreliable):")
    print("    rsync -az --partial %s/ e5:~/ak_deploy/game/" % GAME)
    print("    ssh e5 'source ~/ak_deploy/cf.env && cd ~/ak_deploy && python3 cf_pages_direct_upload.py --dir game --project alley-kingz --branch main'")
    return 0

if __name__ == "__main__": sys.exit(main())
