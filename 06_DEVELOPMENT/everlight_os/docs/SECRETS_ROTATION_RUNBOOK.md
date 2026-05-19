# Secrets Rotation Runbook -- Everlight

**Owner:** Rich (operator-only; no agent has write access to provider dashboards)
**Last reviewed:** 2026-05-19
**Companion module:** `03_AUTOMATION_CORE/01_Scripts/content_tools/secrets_vault.py`

---

## When to rotate

| Trigger | Rotation scope |
|---------|----------------|
| Suspected leak (key posted to Slack, screenshot, paste, git commit) | The leaked key + every key from the same provider |
| Employee/agent decommissioned | Every key that agent had access to |
| Quarterly hygiene | Pick 2-3 providers per quarter on rotation |
| Provider security advisory | The keys named in the advisory |
| New vault master key | All vault contents are re-encrypted automatically by `secrets_vault.py rotate-master` |

After rotation, the OLD key must be revoked at the provider, not just replaced.
Leaving the old key valid means the leak window stays open until the old key expires.

---

## Pre-flight (every rotation)

1. Vault initialized + master key in `EV_VAULT_KEY` env:
   ```bash
   python3 03_AUTOMATION_CORE/01_Scripts/content_tools/secrets_vault.py status
   # initialized: true, master_key_present: true
   ```
2. Confirm last working version of the secret:
   ```bash
   python3 .../secrets_vault.py get ANTHROPIC_API_KEY > /dev/null && echo "vault has it"
   ```
3. Stage rotation off-hours where possible. Most providers honor both keys
   simultaneously for a brief window; some do not.

---

## Per-provider procedure

### 1. Anthropic API key
- Dashboard: https://console.anthropic.com/settings/keys
- Generate new key with name `everlight-hive-YYYYMMDD`
- Smoke test: `python3 -c "from anthropic import Anthropic; print(Anthropic(api_key='NEW').messages.create(model='claude-haiku-4-5', max_tokens=1, messages=[{'role':'user','content':'.'}]))"` (5 sec, $0.00)
- Save: `secrets_vault.py set ANTHROPIC_API_KEY 'NEW'`
- Update `.env`: comment out `ANTHROPIC_API_KEY=` (let vault take over)
- Revoke old key in dashboard
- Sanity check: any cron that ran in the last 5 min logged a successful Claude call

### 2. OpenAI API key
- Dashboard: https://platform.openai.com/api-keys
- Create new key, attach to default project
- Smoke test: `curl -H "Authorization: Bearer NEW" https://api.openai.com/v1/models | head -50`
- Save + update + revoke (same pattern as Anthropic)

### 3. Resend API key
- Dashboard: https://resend.com/api-keys
- New key with same permissions (Full access for sending + reading bounces)
- Smoke test: GET the Resend `/domains` REST endpoint with the new key (see resend.com/docs); expect HTTP 200 + your verified domain list
- Save: `secrets_vault.py set RESEND_API_KEY 'NEW'`
- Update `.env`, revoke old key
- Special: `branded_mailer.py` reads from `RESEND_API_KEY` env var; vault fallback handles transition

### 4. Supabase service-role key (HIGHEST BLAST RADIUS)
- Dashboard: https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl/settings/api
- This key bypasses RLS -- never paste in chat, never log it
- Service-role key cannot be rotated independently of project; instead:
  - **Option A (low-disruption):** Use Supabase Edge Functions w/ JWT auth as a wrapper, deprecate the service-role key over time
  - **Option B (full rotation):** Regenerate JWT secret (Settings -> API -> JWT Secret -> Roll). This invalidates ALL service-role + anon + signed JWTs. Major disruption: every running service that uses these tokens must restart with new env. Plan a maintenance window.
- For Option B: after roll, copy new `service_role` key, smoke test via `curl -H "apikey: NEW" -H "Authorization: Bearer NEW" https://jdqqmsmwmbsnlnstyavl.supabase.co/rest/v1/`, then push to vault + every dependent service.

### 5. Slack bot token
- Dashboard: https://api.slack.com/apps -> your app -> OAuth & Permissions
- "Rotate" button (NOT "Revoke") preserves install context
- New token is `xoxb-...` prefixed
- Smoke test: `curl -H "Authorization: Bearer NEW" https://slack.com/api/auth.test`
- Save: `secrets_vault.py set SLACK_BOT_TOKEN 'NEW'`
- Old token invalid immediately on rotate; expect a few cron retries until restart

### 6. Cloudflare API token
- Dashboard: https://dash.cloudflare.com/profile/api-tokens
- Delete old token (the `cfk_` Workers AI key in .env can stay since it's a different scope)
- Create new with Account/Access:Edit + Zone/WAF:Edit + Zone/Read scopes
- Smoke test: `curl -H "Authorization: Bearer NEW" https://api.cloudflare.com/client/v4/user/tokens/verify`
- Save: `secrets_vault.py set CF_API_TOKEN 'NEW'`
- Trigger a no-op status: `python3 03_AUTOMATION_CORE/01_Scripts/cf_security_apply.py --status`

### 7. Twilio auth token
- Dashboard: https://console.twilio.com/us1/account/keys-credentials/auth-tokens
- Twilio supports primary + secondary auth tokens (rolling rotation possible)
- Promote secondary -> primary, generate new secondary
- Update `.env` with new primary, smoke test:
  `curl -u $TWILIO_ACCOUNT_SID:NEW https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID.json`
- Hive voice handler at `hive_voice_handler.py :8200` will pick up new token on next restart

### 8. Gmail App Password
- Dashboard: https://myaccount.google.com/apppasswords
- Generate new app password named `everlight-hive-YYYYMMDD`
- Save: `secrets_vault.py set GMAIL_APP_PASSWORD 'NEW'`
- Smoke test: `python3 -c "import smtplib; s=smtplib.SMTP_SSL('smtp.gmail.com', 465); s.login('1m.rich.gee@gmail.com','NEW'); s.quit(); print('ok')"`
- Revoke old in same dashboard

### 9. Google OAuth refresh token (gdocs_bridge)
- This is a refresh token, not a static key. Rotation = re-running OAuth flow.
- Run: `python3 /home/opc/reauth_google_docs.py` (on e5-mother once tailnet healthy)
- New token saved to `/home/opc/secrets/google_docs_token.json` automatically
- Browser prompt (2 min) -> confirm scope -> done

---

## Master vault key rotation

Different from per-secret rotation. Run when:
- The master key has been on the same machine for >12 months
- A device that had the master key was lost/stolen
- Audit cadence calls for it

```bash
python3 03_AUTOMATION_CORE/01_Scripts/content_tools/secrets_vault.py rotate-master
# Prints the NEW master key once. Save to .env immediately.
# All stored secrets re-encrypted in place; no data loss.
```

---

## Verification (after any rotation)

1. Audit log line confirms the call worked:
   `grep "<provider>" _logs/http_client.jsonl | tail -1`
2. Any active cron that depends on the rotated key logged a success
   within the next scheduled fire window
3. If the rotated secret was used by an external integration (Stripe webhooks,
   Twilio voice), trigger a sandbox event to confirm

---

## Rollback

- Vault: `secrets_vault.py set NAME 'OLD-value-from-screenshot-or-1password'`
- `.env` fallback: uncomment the original `NAME=` line; vault check still
  passes first, but if vault is empty for that key, env wins

If a rotation breaks things and the old key was already revoked: no rollback.
Generate a brand-new key with the same permissions, save it, and update
every downstream consumer. This is why smoke tests run BEFORE revoke.

---

## What NOT to rotate

- `CLOUDFLARE_API_KEY` (cfk_ prefix) -- this is the Workers AI key, not a
  REST API token. Leave it unless you stop using Workers AI.
- Stripe publishable keys (pk_) -- meant to be public, no rotation needed
- Supabase anon key (jdq...) -- public-by-design, RLS gates access
- GitHub Deploy Key (in `/root/.ssh/github_deploy`) -- already short-scoped to
  this repo; rotate only if device compromise suspected
