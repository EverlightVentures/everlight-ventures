---
id: cf_security_operator_checklist_2026-05-19
title: Cloudflare Security Hardening -- Operator Action Checklist
date: 2026-05-19
category: security
thread: cloudflare_hardening
status: pending_operator
tags: [cloudflare, security, operator_action, deal_1_adjacent]
summary: Operator-only steps to provision Cloudflare Access + WAF + Turnstile + Logpush on everlightventures.io. Pairs with cf_security_apply.py orchestrator. Estimated 25 minutes.
---

# Cloudflare Security Hardening -- Operator Checklist

Pairs with `03_AUTOMATION_CORE/01_Scripts/cf_security_apply.py`. Script handles
the API-mutable parts (Access apps, Service Token, WAF rules). This list is
the dashboard-only steps + the prerequisite credentials.

Estimated time: 25 minutes for Rich, can be paused / resumed mid-list.

---

## Step 1 -- Generate scoped CF_API_TOKEN (5 min, REQUIRED)

The existing `CLOUDFLARE_API_KEY` in `.env` starts with `cfk_` which is a
**Cloudflare Workers AI key** (for `@cf/...` model inference), not the REST
API token the orchestrator needs. Verified live: returns 401 on
`/user/tokens/verify`.

1. Open https://dash.cloudflare.com/profile/api-tokens
2. Click **Create Token** -> **Custom token**
3. Name: `everlight-security-orchestrator`
4. Permissions:
   - Account / Access: Apps and Policies / **Edit**
   - Account / Access: Service Tokens / **Edit**
   - Account / Cloudflare Pages / **Read** (already covered by your project key, harmless overlap)
   - Zone / Zone WAF / **Edit**
   - Zone / Zone / **Read**
   - Zone / DNS / **Read**
5. Account Resources: **Include All** (or specifically your Everlight account)
6. Zone Resources: **Include / Specific zone / everlightventures.io**
7. TTL: leave default (no expiry)
8. Continue -> Create Token -> Copy token (shown ONCE)
9. Append to `03_AUTOMATION_CORE/03_Credentials/.env`:
   ```
   CF_API_TOKEN=<paste-here>
   ```
10. Verify: `python3 03_AUTOMATION_CORE/01_Scripts/cf_security_apply.py --status`
    Expected: prints zone id + lists all 5 protected subdomains as `[MISSING]`,
    Service Token as `[MISSING]`, WAF rules as `[MISSING]`.

## Step 2 -- Set EV_OPERATOR_EMAIL (1 min, REQUIRED)

Email used for the Cloudflare Access allowlist on the 5 protected subdomains.
When you hit `hub.everlightventures.io` in a browser, you authenticate with
this email (one-time-pin sent there). Default: `1m.rich.gee@gmail.com`.

Append to `.env`:
```
EV_OPERATOR_EMAIL=1m.rich.gee@gmail.com
```

## Step 3 -- Initialize the secrets vault (3 min, RECOMMENDED)

The `secrets_vault.py` module (built this session) wraps every API key in a
Fernet-encrypted file at `/opt/everlight/secrets/keys.enc` (perm 600). One
master key holds the whole vault. Migration is graceful: until a secret moves
into the vault, callers fall back to `os.environ` so nothing breaks.

```bash
sudo mkdir -p /opt/everlight/secrets
sudo chown $(whoami):$(whoami) /opt/everlight/secrets
sudo chmod 700 /opt/everlight/secrets
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/secrets_vault.py init
```

The init prints a master key ONCE. Copy it. Append to `.env`:
```
EV_VAULT_KEY=<the-printed-key>
EV_SECRETS_DIR=/opt/everlight/secrets
```

Verify: `python3 .../secrets_vault.py self-test` -> expect `PASS: roundtrip ok`.

## Step 4 -- Apply Cloudflare Access + WAF (5 min, MUTATES PRODUCTION)

After Steps 1-2 are done:

```bash
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/cf_security_apply.py --status
# review the [MISSING] list one more time

python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/cf_security_apply.py --apply --operator-email "$EV_OPERATOR_EMAIL"
```

Script prints the Service Token client_id + client_secret ONCE. Copy both
and append to `.env`:
```
CF_ACCESS_CLIENT_ID=<from-script-output>
CF_ACCESS_CLIENT_SECRET=<from-script-output>
```

Verify (in a NEW shell so the new env vars load):
```bash
# Browser test
curl -I https://hub.everlightventures.io/
# expect: HTTP 302 redirect to cloudflareaccess.com login

# Service Token test
curl -I -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
        -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET" \
        https://hub.everlightventures.io/
# expect: HTTP 200 from origin (or 502 if e5-mother tunnel is offline; either way means Access let us through)
```

## Step 5 -- Turnstile on the e-sign form (5 min, DASHBOARD)

The orchestrator does NOT touch Turnstile because it requires frontend changes
beyond a config flip. Turnstile is the only public form path (sellers signing
PSAs), so it gets a CAPTCHA instead of Access.

1. Open https://dash.cloudflare.com/?to=/:account/turnstile
2. Add Site -> Site name: `everlight-esign` -> Hostname: `esign.everlightventures.io`
3. Widget Mode: **Managed** (auto-decides invisible vs interactive)
4. Pre-clearance: **Yes** (lets Turnstile satisfy WAF challenges too)
5. Save -> Copy **Site Key** + **Secret Key**
6. Append to `.env`:
   ```
   CF_TURNSTILE_SITE_KEY=<site-key>
   CF_TURNSTILE_SECRET=<secret-key>
   ```
7. Frontend integration (separate task, post-checklist): the e-sign HTML at
   `esign.everlightventures.io` needs the Turnstile JS widget + a server-side
   verify call before processing form submissions. Defer until Rich greenlights.

## Step 6 -- Cloudflare Logpush to e5-mother (10 min, OPTIONAL)

Pushes WAF + Access events to e5-mother for daily Slack digest. Free tier
includes Logpush. Skip if e5-mother tunnel isn't healthy yet.

1. Open https://dash.cloudflare.com/?to=/:account/logs/logpush
2. Add Logpush Job -> Service: **HTTP requests** (covers WAF + Access)
3. Destination: HTTP endpoint on e5-mother
   - URL: `https://api.everlightventures.io/cf-logpush/ingest` (TBD endpoint; defer until built)
   - Or temporary: AWS S3 / R2 (you have R2 in your account)
4. Fields: include Action, ClientIP, ClientRequestUserAgent, ClientCountry,
   EdgeResponseStatus, RayID, FirewallMatchesActions, FirewallMatchesRuleIDs
5. Save

This step can wait until after `cf_logpush_consumer.py` is built. Documented
here so it's not forgotten.

## Step 7 -- Rotate exposed secrets (15 min, RECOMMENDED post-vault-init)

Sweep audit flagged the following keys in `.env` as live:

| Key | Rotate at | Notes |
|-----|-----------|-------|
| ANTHROPIC_API_KEY | https://console.anthropic.com/settings/keys | Used by Hive everywhere |
| OPENAI_API_KEY | https://platform.openai.com/api-keys | Codex + occasional |
| RESEND_API_KEY | https://resend.com/api-keys | Outbound email |
| SUPABASE_SERVICE_KEY | https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl/settings/api | RLS bypass, highest blast radius |
| SLACK_BOT_TOKEN | https://api.slack.com/apps -> your app -> OAuth | Hive Slack writes |
| CLOUDFLARE_API_KEY | DELETE this (it's the cfk_ Workers AI key, only needed if you call Workers AI) | Keep CF_API_TOKEN as the new canonical |
| TWILIO_AUTH_TOKEN | https://console.twilio.com/us1/account/keys-credentials/api-keys | Voice handler |
| GMAIL_APP_PASSWORD | https://myaccount.google.com/apppasswords | Gmail SMTP fallback |

For each: rotate in the provider dashboard, paste new key into vault
(`secrets_vault.py set NAME 'new-value'`), then verify a sample call works,
then delete from `.env`. See full procedure in
`06_DEVELOPMENT/everlight_os/docs/SECRETS_ROTATION_RUNBOOK.md` (separate doc).

---

## What this checklist does NOT cover

- **Pro plan upgrade ($25/mo)** -- unlocks Super Bot Fight Mode, more rules,
  WAF analytics. Free plan is sufficient for Phase 1. Revisit post-Deal 1.
- **Frontend Turnstile widget code** -- separate task, requires touching the
  esign HTML template.
- **Migration of remaining 6 SMTP-bypass scripts** to branded_mailer. Task #27
  in mailbox, post-Deal-1.
- **Stripe MCP escalation loop** -- `it_triage` has been escalating Stripe
  every minute since at least 21:08 UTC 2026-05-19. Worth investigating
  separately; not security-perimeter related but flagged here for visibility.

---

## Rollback (any step is reversible)

- Cloudflare Access app: dashboard -> Zero Trust -> Access -> Apps -> Delete
- Service Token: Zero Trust -> Access -> Service Auth -> Revoke
- WAF Custom Rule: Security -> WAF -> Custom Rules -> Disable
- Turnstile widget: Turnstile -> Site -> Delete
- Vault: just stop using it; `.env` fallback continues to work

No infrastructure destruction. All changes are config-only.
