# MCP Runbook

**Last audit: 2026-04-22. Keep this doc current; it is the first thing to read when something breaks.**

## Quick Status (Live Audit)

| Server | State | Notes |
|---|---|---|
| blinko-memory | WORKING | MCP call succeeded live; returns 386 indexed notes |
| supabase | FIXED (pending CLI reload) | Token was stale in `.mcp.json`; synced to `.env` value. Restart Claude CLI to pick up. |
| broker-os | DEGRADED | MCP server up; Django at Oracle port 8504 is DOWN. Commissions endpoint returns "Django not running". |
| market-intel | EMPTY | XLM bot state bundle is empty. Oracle xlm-bot service may have stopped or state path is wrong. |
| n8n | WORKING | Oracle E5 healthz 200 |
| Gmail / Slack / Calendar / Drive | WORKING | OAuth intact |
| **resend** | **CRITICAL: KEY REVOKED** | HTTP 401. All email outreach silently failing. Rotate key at resend.com NOW. |
| **stripe** | **CRITICAL: KEY EXPIRED** | Stripe confirms "Expired API Key". All payment processing dead. Rotate key NOW. |

## Monitor

`03_AUTOMATION_CORE/01_Scripts/mcp_health_monitor.py` -- runs every 10 min on Oracle, posts Slack alerts on new failures, escalates on sustained failures.

Install cron on Oracle E5:
```bash
# On Oracle E5 (ssh oracle-e5):
crontab -l > /tmp/c.$$
echo "*/10 * * * * cd /home/opc/hive_workspace && python3 mcp_health_monitor.py >> /home/opc/_logs/mcp_health.log 2>&1" >> /tmp/c.$$
crontab /tmp/c.$$
rm /tmp/c.$$
```

Manual run (any machine with network to Oracle):
```bash
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/mcp_health_monitor.py --loud
```

Snapshot JSON: `09_DASHBOARD/reports/mcp_health_latest.json` (dashboard can read this).

State file (dedup + consecutive-fail tracking): `_logs/mcp_health_state.json`

## Per-Server Remediation

### resend -- CRITICAL, ROTATE NOW
- **Symptom:** 401 from api.resend.com; emails fail silently
- **Impact:** Every outbound email (L2 outreach, buyer blast, contract delivery) fails. Resend does NOT bounce -- it refuses at the API. Our pipeline thinks everything is sent.
- **Fix:**
  1. Log into resend.com/api-keys
  2. Create a new API key (full access, name it "everlight-2026-04-22")
  3. Update `03_AUTOMATION_CORE/03_Credentials/.env`:
     - `RESEND_API_KEY=<new>`
     - `SMTP_PASS=<same new key>`
  4. Update `.mcp.json`:
     - broker-os SMTP_PASS env (line 14)
     - resend RESEND_API_KEY env (line 60)
  5. Restart Claude CLI to reload MCP config
  6. Verify: `python3 mcp_health_monitor.py --loud | grep resend` -> OK

### stripe -- CRITICAL, ROTATE NOW
- **Symptom:** "Expired API Key" from api.stripe.com
- **Impact:** Every customer payment fails. Stripe dashboard shows the old key is expired (Stripe doesn't auto-expire; someone rotated it without updating `.mcp.json`).
- **Fix:**
  1. Stripe dashboard > Developers > API keys > find current secret key
  2. Update `.mcp.json` line 50: `--api-key=sk_live_<new>`
  3. Also update `03_AUTOMATION_CORE/03_Credentials/.env` if Stripe is referenced there
  4. Restart Claude CLI
  5. Verify: monitor stripe row -> OK

### supabase -- FIXED, PENDING CLI RELOAD
- **Was broken by:** stale token `sbp_26818a09...` in `.mcp.json` vs current token `sbp_b8c0fa99...` in `.env`
- **Done:** Updated `.mcp.json` supabase access-token to match `.env`
- **To complete:** Restart Claude CLI (`exit` and relaunch) so the MCP subprocess picks up the new config.
- Monitor 403 is the Supabase **Management API** which requires a different scope than the MCP token. The MCP tool itself is what matters for our workflow. This is why the monitor flags WARN not FAIL -- distinguish "can't call management API" from "MCP is broken."

### broker-os -- Django restart needed on Oracle
- **Symptom:** broker_status returns `"error": "Django not running"`
- **Impact:** Commissions data, deal pipeline, broker_leads all inaccessible through MCP
- **Fix on Oracle E5 (ssh oracle-e5):**
  ```bash
  sudo systemctl status hive-django
  sudo systemctl restart hive-django
  sudo journalctl -u hive-django -n 100 --no-pager
  ```
- If service unit missing, reinstall via the deploy script.

### market-intel -- XLM bot state needs verification
- **Symptom:** `get_market_intel_state` returns empty bundle
- **Impact:** Trading intel feeds return empty; XLM bot decisions may be operating on stale/no market intel
- **Fix on Oracle (xlm bot lives there):**
  ```bash
  ssh oracle-e5
  sudo systemctl status xlm-bot
  ls -la /home/opc/xlm_bot/state.json  # should be < 1 hour old
  journalctl -u xlm-bot -n 50 --no-pager
  ```

### blinko-memory -- already working
- MCP calls succeed. Monitor may show "unreachable" when run from the phone due to phone-network path; run from Oracle for accurate readings.

### n8n -- working
- Oracle E5 port 5678, `/healthz` returns 200.

## Why We Weren't Alerted Before

Three root causes:

1. **No MCP-specific monitor existed.** `hive_health_monitor.py` checks Slack / Resend / Blinko / n8n endpoints generally, but not the full MCP server matrix and not credential-validation explicitly. The new `mcp_health_monitor.py` fixes this.

2. **Silent failures in the outbound pipeline.** `hive_outreach.py` logged errors but only to local files; no Slack post on API-auth failure. When Resend started returning 401, the pipeline accumulated thousands of failed sends without anyone noticing.

3. **Token drift between `.env` and `.mcp.json`.** No tooling enforced that the two files stay in sync. The Supabase token was rotated in `.env` but never updated in `.mcp.json`, so the MCP call path was using the old token.

## Prevention (Go-Forward)

1. **`mcp_health_monitor.py` runs every 10 min on Oracle** and posts Slack `#hive-alerts` on new failures or 3+ consecutive failures. **INSTALL BEFORE NEXT DEPLOY.**

2. **Token-sync lint.** Add to pre-commit: a check that every secret in `.mcp.json` exists identically in `.env`. (TBD script -- low priority, manual review of this runbook every Monday in the meantime.)

3. **Credential rotation calendar.** Justine Park owns a monthly recurring task to verify all API keys are valid by running `python3 mcp_health_monitor.py --loud`. If any FAIL, rotate immediately.

4. **Outreach-pipeline regression test.** Before L2 goes live at scale, add a dry-run test in `hive_outreach.py` that hits Resend with a verification endpoint BEFORE sending any real email. If auth fails, abort the batch with a loud Slack alert.

5. **Dashboard tile.** `09_DASHBOARD/reports/mcp_health_latest.json` is now a supported data source. Add a tile to the Django dashboard showing live MCP status with last-check timestamp.

## Gotcha: "auth failure" can mean "process never started"

On 2026-04-22 the Resend MCP kept reporting auth failure in `/mcp` even after a valid key rotation. Root cause: `.mcp.json` referenced `mcp-send-email`, an npm package with no `bin` field. `npx -y mcp-send-email` fails with "could not determine executable to run", so the MCP subprocess never launched. Claude CLI surfaced this as an auth error because it couldn't complete the handshake.

**Diagnosis command before chasing credentials:**
```bash
# Where <pkg> is the package in .mcp.json args
RESEND_API_KEY=... timeout 6 npx -y <pkg>
# If you see "could not determine executable to run" -- package is broken, not the key
# If it hangs waiting for stdin -- the MCP server is alive (correct behavior)
```

**Correct package for Resend:** `resend-mcp` v2.6.0+ (maintained by Resend employees zenorocha/drish/felipefreitag). Verify with `npm view resend-mcp bin` -> should show `{ "resend-mcp": "dist/index.js" }` or similar.

## Contacts When It Breaks

- Slack `#hive-alerts` -- automated alerts from the monitor
- Slack `#ceo-brief` -- Rich's daily brief includes MCP health summary
- Runbook (this doc) -- always-current remediation steps

## Files Touched This Audit

- `/mnt/sdcard/AA_MY_DRIVE/.mcp.json` -- Supabase token synced to `.env`
- `/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/mcp_health_monitor.py` -- new monitor
- `/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports/mcp_health_latest.json` -- first snapshot written
- `/mnt/sdcard/AA_MY_DRIVE/_logs/mcp_health_state.json` -- monitor state (consecutive-fail tracking)
- `/mnt/sdcard/AA_MY_DRIVE/_logs/mcp_health.log` -- monitor log
