#!/usr/bin/env python3
"""
build_proton_pass_import.py  --  Everlight secret consolidator (2026-06-02)

Reads the canonical credential sources scattered across the workspace and emits
ONE structured Bitwarden-format JSON that Proton Pass imports cleanly
(Settings > Import > Bitwarden > .json), organized into folders with Login /
Secure-Note item types and hidden custom fields.

This script contains NO secrets. It reads them from the source files at run
time, so it is safe to keep in the repo and re-run whenever a key rotates.

Output: 03_AUTOMATION_CORE/03_Credentials/proton_pass_import.json  (git-ignored)

After you import the file into Proton Pass and verify, run:
    bash 03_AUTOMATION_CORE/01_Scripts/setup/shred_plaintext_secrets.sh
"""
import json, os

ROOT = "/mnt/sdcard/AA_MY_DRIVE"


# ---------- helpers ----------
def load_env(path):
    """Parse KEY=VALUE .env into a dict; strips quotes; first '=' splits."""
    d = {}
    p = os.path.join(ROOT, path)
    if not os.path.isfile(p):
        return d
    for line in open(p, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        if v:
            d[k.strip()] = v
    return d


def read_abs(path):
    try:
        return open(path, encoding="utf-8", errors="ignore").read().strip()
    except Exception:
        return ""


def read_file(path):
    return read_abs(os.path.join(ROOT, path))


def seed_words(path):
    """Pull a mnemonic out of one of the *_sp.py storage files."""
    raw = read_file(path)
    if not raw:
        return ""
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    joined = [l for l in lines if len(l.split()) >= 11]  # a full phrase on one line
    if joined:
        return " ".join(joined[-1].split())
    words = []
    for l in lines:
        for w in l.replace(".", " ").split():
            if w.isalpha():
                words.append(w.lower())
    return " ".join(words)


# ---------- load sources ----------
env_root = load_env(".env")
env_cred = load_env("03_AUTOMATION_CORE/03_Credentials/.env")
env_e5 = load_env("_state/cloud_mirror_secrets/e5_data.env")
env_saas = load_env("06_DEVELOPMENT/hivemind_saas/backend/.env")
env_mkt = load_env("01_BUSINESSES/Everlight_Ventures/04_Automation/marketing_platform_dec2025/.env")
env_hzt = load_env("03_AUTOMATION_CORE/03_Credentials/hetzner_token.env")
env_hzp = load_env("03_AUTOMATION_CORE/03_Credentials/hetzner_proxy.env")

gtok = {}
try:
    gtok = json.load(open(os.path.join(ROOT, "_state/cloud_mirror_secrets/google_tokens.json")))
except Exception:
    pass

rclone = read_file("03_AUTOMATION_CORE/03_Credentials/RCLONE_CRYPT_RECOVERY.txt")


def grab(txt, label):
    for line in txt.splitlines():
        if line.strip().startswith(label):
            return line.split(":", 1)[1].strip()
    return ""


rclone_pw = grab(rclone, "PASSWORD")
rclone_salt = grab(rclone, "SALT")
github_key = read_abs("/root/.ssh/github_deploy")

# ---------- Bitwarden item builders ----------
FOLDERS = [
    "Crypto Wallets", "AI / LLM APIs", "Email & Comms", "Slack",
    "Payments (Stripe)", "Cloud & Infra", "Databases & Supabase",
    "Google", "Voice & Telephony", "Data APIs", "App Secrets",
]
folder_ids = {name: f"ev-{i:02d}" for i, name in enumerate(FOLDERS)}
items = []
_n = [0]


def hidden(name, value):
    return {"name": name, "value": value, "type": 1}  # type 1 = hidden


def text(name, value):
    return {"name": name, "value": value, "type": 0}


def note(folder, name, secret_label, secret, body="", fields=None):
    if not secret and not fields:
        return
    _n[0] += 1
    f = list(fields or [])
    if secret:
        f.insert(0, hidden(secret_label, secret))
    items.append({
        "id": f"ev-item-{_n[0]:03d}", "organizationId": None,
        "folderId": folder_ids[folder], "type": 2,
        "name": name, "notes": body or None, "favorite": False,
        "secureNote": {"type": 0}, "fields": f,
    })


def login(folder, name, username, password, uri="", body="", fields=None):
    if not password and not username:
        return
    _n[0] += 1
    items.append({
        "id": f"ev-item-{_n[0]:03d}", "organizationId": None,
        "folderId": folder_ids[folder], "type": 1,
        "name": name, "notes": body or None, "favorite": False,
        "fields": list(fields or []),
        "login": {"username": username or None, "password": password or None,
                  "uris": ([{"match": None, "uri": uri}] if uri else [])},
    })


# ===== Crypto Wallets =====
note("Crypto Wallets", "ZilPay (Zilliqa) - BCARDI legacy", "recovery phrase (24w)",
     seed_words("03_AUTOMATION_CORE/01_Scripts/Zilpay_Bacardi_Wallet_SP.py"),
     "Legacy Zilliqa wallet from the original $BCARDI architecture. EXPOSED in plaintext on synced devices -> rotate if it holds value.")
note("Crypto Wallets", "Phantom (Solana) #1", "recovery phrase (12w)",
     seed_words("03_AUTOMATION_CORE/01_Scripts/phantom_sp.py"),
     "Solana wallet. EXPOSED in plaintext -> do NOT use for the new $BCARDI launch; generate a fresh wallet.")
note("Crypto Wallets", "Phantom (Solana) #2", "recovery phrase (12w)",
     seed_words("05_PERSONAL/A_Personal_Notebook/Y_Accounts/Phantom/seed_phrase_phantom.py"),
     "Second, DIFFERENT Solana wallet. EXPOSED in plaintext -> rotate if funded.")
note("Crypto Wallets", "Atomic Wallet", "recovery phrase (12w)",
     seed_words("03_AUTOMATION_CORE/01_Scripts/atomic_sp.py"),
     "Atomic multi-chain wallet. EXPOSED in plaintext -> rotate if funded.")
note("Crypto Wallets", "BCARDI coin wallet (likely MetaMask 0x20DC)", "recovery phrase (12w)",
     seed_words("03_AUTOMATION_CORE/01_Scripts/bcardi_coin_sp.py"),
     "Probably the MetaMask wallet 0x20DC8EE835B235409Fe6fe6B3Afff5925C5efE80 holding Cronos $BCRDI (contract 0xc7AdBbA52EA64B008a7e5d7666876628Dc391d69). EXPOSED -> rotate if funded.",
     fields=[text("MetaMask address", "0x20DC8EE835B235409Fe6fe6B3Afff5925C5efE80"),
             text("Cronos $BCRDI contract", "0xc7AdBbA52EA64B008a7e5d7666876628Dc391d69")])
login("Crypto Wallets", "Polymarket trading wallet (EVM)",
      read_file("03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.addr"),
      read_file("03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key"),
      "https://polymarket.com",
      "Private key in PASSWORD, address in USERNAME. Holds ~116 USDC.e. ACTIVE: the bot reads the live copy at 03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key - leave that file in place. EXPOSED -> rotate when feasible.")

# ===== AI / LLM APIs (capture every divergent copy) =====
note("AI / LLM APIs", "Anthropic API - workspace", "ANTHROPIC_API_KEY", env_cred.get("ANTHROPIC_API_KEY", ""), "Canonical key used by the phone/workspace.")
note("AI / LLM APIs", "Anthropic API - e5 server", "ANTHROPIC_API_KEY", env_e5.get("ANTHROPIC_API_KEY", ""), "Key configured on e5-mother.")
note("AI / LLM APIs", "Anthropic API - Hive Mind SaaS", "ANTHROPIC_API_KEY", env_saas.get("ANTHROPIC_API_KEY", ""), "Key in the Hive Mind SaaS backend.")
note("AI / LLM APIs", "OpenAI API - main", "OPENAI_API_KEY", env_root.get("OPENAI_API_KEY", ""), "Primary OpenAI project key (root + credentials + e5).")
note("AI / LLM APIs", "OpenAI API - Hive Mind SaaS", "OPENAI_API_KEY", env_saas.get("OPENAI_API_KEY", ""))
note("AI / LLM APIs", "Perplexity API - primary", "PERPLEXITY_API_KEY", env_root.get("PERPLEXITY_API_KEY", ""), "Used by root .env + Hive Mind.")
note("AI / LLM APIs", "Perplexity API - credentials/.env", "PERPLEXITY_API_KEY", env_cred.get("PERPLEXITY_API_KEY", ""), "Divergent value - confirm which is active.")
note("AI / LLM APIs", "Google Gemini API", "GEMINI_API_KEY", env_e5.get("GEMINI_API_KEY", ""))
note("AI / LLM APIs", "Langfuse (LLM tracing)", "LANGFUSE_SECRET_KEY", env_e5.get("LANGFUSE_SECRET_KEY", ""),
     "Public key: " + env_e5.get("LANGFUSE_PUBLIC_KEY", "") + " | host: " + env_e5.get("LANGFUSE_HOST", ""))

# ===== Email & Comms =====
login("Email & Comms", "Gmail IMAP app password - current (root .env)",
      env_root.get("IMAP_USER", ""), env_root.get("IMAP_PASS", ""),
      "https://mail.google.com", "App password for IMAP reply-detection.")
login("Email & Comms", "Gmail IMAP app password - credentials/.env",
      env_cred.get("IMAP_USER", ""), env_cred.get("IMAP_PASS", ""),
      "https://mail.google.com", "Divergent app password - confirm which is live, revoke the other.")
note("Email & Comms", "Resend API - current", "RESEND_API_KEY", env_root.get("RESEND_API_KEY", ""), "Used by root + e5.")
note("Email & Comms", "Resend API - credentials/.env", "RESEND_API_KEY", env_cred.get("RESEND_API_KEY", ""), "Divergent value.")
note("Email & Comms", "ImprovMX API", "IMPROVMX_API_KEY", env_root.get("IMPROVMX_API_KEY", ""), "Alias mgmt for everlightventures.io (42 addresses).")

# ===== Slack =====
note("Slack", "Slack bot token (xlmbot)", "SLACK_BOT_TOKEN", env_cred.get("SLACK_BOT_TOKEN", ""))
note("Slack", "Slack warroom token", "SLACK_WARROOM_TOKEN", env_cred.get("SLACK_WARROOM_TOKEN", ""))
note("Slack", "Slack app credentials", "SLACK_CLIENT_SECRET", env_cred.get("SLACK_CLIENT_SECRET", ""),
     "Signing secret + webhooks attached.",
     fields=[hidden("SLACK_SIGNING_SECRET", env_cred.get("SLACK_SIGNING_SECRET", "")),
             hidden("webhook (default)", env_cred.get("SLACK_WEBHOOK_URL", "")),
             hidden("webhook (warroom)", env_cred.get("SLACK_WEBHOOK_WARROOM", "")),
             hidden("webhook (alerts)", env_cred.get("SLACK_WEBHOOK_ALERTS", ""))])

# ===== Payments =====
note("Payments (Stripe)", "Stripe LIVE secret key (full access)", "STRIPE_SECRET_KEY", env_root.get("STRIPE_SECRET_KEY", ""),
     "sk_live full-access. Publishable key attached.",
     fields=[text("STRIPE_PUBLISHABLE_KEY", env_root.get("STRIPE_PUBLISHABLE_KEY", ""))])
note("Payments (Stripe)", "Stripe LIVE restricted key", "STRIPE_SECRET_KEY (rk_live)", env_cred.get("STRIPE_SECRET_KEY", ""),
     "Restricted key from credentials/.env - narrower scope.")
note("Payments (Stripe)", "Stripe price IDs (Hive Mind)", "", "",
     "Plan price IDs - not secret, kept for reference.",
     fields=[text("SPARK", env_saas.get("STRIPE_PRICE_SPARK", "")),
             text("HIVE", env_saas.get("STRIPE_PRICE_HIVE", "")),
             text("ENTERPRISE", env_saas.get("STRIPE_PRICE_ENTERPRISE", ""))])

# ===== Cloud & Infra =====
note("Cloud & Infra", "Cloudflare Global API Key", "CLOUDFLARE_API_KEY", env_cred.get("CLOUDFLARE_API_KEY", ""),
     "Use with X-Auth-Email + X-Auth-Key headers.",
     fields=[text("email", env_cred.get("CLOUDFLARE_EMAIL", "")),
             text("account id", env_cred.get("CLOUDFLARE_ACCOUNT_ID", "")),
             text("pages project", env_cred.get("CLOUDFLARE_PAGES_PROJECT", ""))])
note("Cloud & Infra", "Hetzner API token", "HETZNER_API_TOKEN", env_hzt.get("HETZNER_API_TOKEN", ""))
login("Cloud & Infra", "Hetzner proxy server (egress)",
      env_hzp.get("PROXY_USER", ""), env_hzp.get("PROXY_PASS", ""),
      "", "Server id " + env_hzp.get("HETZNER_SERVER_ID", "") + " @ " + env_hzp.get("PROXY_IP", ""),
      fields=[text("PROXY_URL", env_hzp.get("PROXY_URL", ""))])
note("Cloud & Infra", "n8n API key", "N8N_API_KEY", env_e5.get("N8N_API_KEY", ""), "n8n is PARKED but key retained.")
note("Cloud & Infra", "GitHub deploy SSH key (ed25519)", "private key", github_key,
     "Deploy key for github.com/EverlightVentures/everlight-ventures. Lives at /root/.ssh/github_deploy.")
note("Cloud & Infra", "Oracle VM SSH key (RSA)", "private key",
     read_file("08_BACKUPS/System_Artifacts/uploads_archive/contents/oracle_key.pem"),
     "RSA private key for Oracle VM access (archived copy).")
note("Cloud & Infra", "rclone crypt recovery (Drive backup)", "PASSWORD", rclone_pw,
     "Required to decrypt drive_everlight_crypt. LOSE THIS = lose the encrypted Drive backup forever.",
     fields=[hidden("SALT", rclone_salt)])

# ===== Databases & Supabase =====
note("Databases & Supabase", "Supabase service role key (RLS bypass)", "SUPABASE_SERVICE_ROLE_KEY", env_cred.get("SUPABASE_SERVICE_ROLE_KEY", ""),
     "Project: " + env_cred.get("SUPABASE_URL", ""),
     fields=[hidden("SUPABASE_ANON_KEY", env_cred.get("SUPABASE_ANON_KEY", "")),
             text("SUPABASE_URL", env_cred.get("SUPABASE_URL", ""))])
note("Databases & Supabase", "Supabase access token - current", "SUPABASE_ACCESS_TOKEN", env_root.get("SUPABASE_ACCESS_TOKEN", ""), "sbp_268 (root + e5).")
note("Databases & Supabase", "Supabase access token - credentials/.env", "SUPABASE_ACCESS_TOKEN", env_cred.get("SUPABASE_ACCESS_TOKEN", ""), "Divergent value sbp_b8c - confirm/revoke.")
note("Databases & Supabase", "Marketing platform Postgres + secrets", "DATABASE_URL", env_mkt.get("DATABASE_URL", ""),
     fields=[hidden("NEXTAUTH_SECRET", env_mkt.get("NEXTAUTH_SECRET", "")),
             hidden("SOCIAL_MEDIA_ENCRYPTION_KEY", env_mkt.get("SOCIAL_MEDIA_ENCRYPTION_KEY", ""))])

# ===== Google =====
note("Google", "Google OAuth2 client (Docs/Drive)", "GOOGLE_OAUTH_CLIENT_SECRET", env_cred.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
     "Client id + live refresh token attached.",
     fields=[text("client_id", env_cred.get("GOOGLE_OAUTH_CLIENT_ID", "")),
             hidden("refresh_token", gtok.get("refresh_token", "")),
             hidden("access_token", gtok.get("access_token", ""))])
note("Google", "Google Maps API key", "GOOGLE_MAPS_API_KEY", env_cred.get("GOOGLE_MAPS_API_KEY", ""))

# ===== Voice & Telephony =====
note("Voice & Telephony", "ElevenLabs API", "ELEVENLABS_API_KEY", env_cred.get("ELEVENLABS_API_KEY", ""))
login("Voice & Telephony", "Twilio", env_cred.get("TWILIO_ACCOUNT_SID_REAL", env_cred.get("TWILIO_ACCOUNT_SID", "")),
      env_cred.get("TWILIO_AUTH_TOKEN", ""), "https://twilio.com",
      "Account SID in username (use the AC one), auth token in password.",
      fields=[hidden("recovery code (one-time)", env_cred.get("TWILIO_RECOVERY_CODE", "")),
              text("phone number", env_cred.get("TWILIO_PHONE_NUMBER", ""))])

# ===== Data APIs =====
note("Data APIs", "ATTOM Data (real estate)", "ATTOM_API_KEY", env_cred.get("ATTOM_API_KEY", ""), "Trial key - RE wholesale.")

# ===== App Secrets =====
note("App Secrets", "Hive Mind SaaS app secrets", "JWT_SECRET", env_saas.get("JWT_SECRET", ""),
     "Bootstrap admin login + JWT.",
     fields=[text("BOOTSTRAP_EMAIL", env_saas.get("BOOTSTRAP_EMAIL", "")),
             hidden("BOOTSTRAP_PASSWORD", env_saas.get("BOOTSTRAP_PASSWORD", ""))])

# ---------- emit ----------
export = {
    "encrypted": False,
    "folders": [{"id": fid, "name": name} for name, fid in folder_ids.items()],
    "items": items,
}
out = os.path.join(ROOT, "03_AUTOMATION_CORE/03_Credentials/proton_pass_import.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(export, f, indent=2)

# masked summary
by_folder = {}
for it in items:
    fname = [n for n, i in folder_ids.items() if i == it["folderId"]][0]
    by_folder[fname] = by_folder.get(fname, 0) + 1
print(f"Wrote {out}")
print(f"Total items: {len(items)}  across {len(by_folder)} folders")
for fn in FOLDERS:
    if by_folder.get(fn):
        print(f"  {fn:28s} {by_folder[fn]}")
