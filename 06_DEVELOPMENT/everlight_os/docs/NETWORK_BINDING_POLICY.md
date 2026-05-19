# Network Binding Policy

**Effective:** 2026-05-18
**Owner:** Rich (operator), Marcus Cole (chief-of-staff), 69_security_engineer
**Status:** HARD LAW. Supersedes ad-hoc per-script binding choices.

---

## The Rule (One Line)

**Private by default. Public by `ev` domain.** Every service binds to
`127.0.0.1` unless it is explicitly published through Cloudflare on an
`*.everlightventures.io` domain or it is a managed-platform deployment
(Railway, Cloudflare Pages, Vercel) where the platform requires
`0.0.0.0:$PORT`.

---

## Why This Exists

A service bound to `0.0.0.0` is bound to **every network interface the
machine has**, including any public IP. On a phone, that means anyone on
the same Wi-Fi can reach it. On an Oracle VM, that means the entire
internet can reach it unless a firewall (security list) is filtering. On
the AceMagician PC behind a router, that means the LAN can reach it.

A service bound to `127.0.0.1` is bound to the **loopback interface only**.
Nothing outside the machine can reach it, regardless of firewall posture.

The historical practice in this workspace was "bind 0.0.0.0 and trust the
firewall." That is a single-point-of-failure security posture: if the
firewall ever opens (Oracle security list edit, Tailscale ACL drift,
phone hotspot on public Wi-Fi), every internal dashboard is suddenly
public. This policy makes the binding itself the security boundary so
firewalls become defense-in-depth, not the sole defense.

Public surfaces, and **only** public surfaces, go through the `ev`
domain at Cloudflare. The Cloudflare edge supplies the TLS, the WAF, the
rate-limit, and the audit trail.

---

## The Decision Tree

```
Is this service meant for the public internet?
+-- YES -> publish via Cloudflare on *.everlightventures.io
|          origin still binds 127.0.0.1 + cloudflared tunnel
|          OR origin binds 0.0.0.0 on a managed platform (Railway etc.)
+-- NO  -> does it need to reach OTHER devices on the tailnet?
           +-- YES -> bind to the tailnet interface IP (100.x.x.x)
           |          or bind 0.0.0.0 ONLY if the host has no public interface
           |          (verified: ev-box, e5-mother)
           +-- NO  -> bind 127.0.0.1 (FINAL)
```

---

## Per-Host Posture (Reality, 2026-05-18)

| Host | Public IP? | Default for new services |
|---|---|---|
| Phone (Termux/PRoot SOT) | yes (cellular) | **127.0.0.1, no exceptions** |
| Oracle Micro (xlm-bot) | yes (163.192.19.196) | **127.0.0.1**, SSH tunnel for access |
| e5-mother (Ampere, tailnet) | yes (port 2222 break-glass only) | tailnet IP only; 0.0.0.0 acceptable iff Oracle security list confirmed locked |
| AceMagician PC | LAN (no public route) | tailnet IP; LAN access allowed for printer/local-only utilities |
| ev-box (planned) | yes (2222 break-glass) | tailnet IP only |
| Cloudflare Pages / Railway | managed | 0.0.0.0:$PORT (platform requirement) |

---

## The Env-Var Override Pattern

Every patched script in the workspace now uses one of these shapes:

**Shell:**
```bash
# Bind policy: see 06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md
BIND_HOST="${EV_BIND:-127.0.0.1}"
exec uvicorn app:app --host "$BIND_HOST" --port "$PORT"
```

**Python:**
```python
# Bind policy: see 06_DEVELOPMENT/everlight_os/docs/NETWORK_BINDING_POLICY.md
import os
host = os.environ.get("EV_BIND", "127.0.0.1")
uvicorn.run(app, host=host, port=PORT)
```

To deliberately expose a service (e.g., on Oracle behind security list):
```bash
EV_BIND=0.0.0.0 ./start.sh
```

Per-service legacy env-vars are preserved where they pre-exist
(`HIVE_BIND_ALL=1`, `XLM_CHAT_HOST`, `MOLTBOOK_BIND`, `IC_BIND`,
`RELAY_HOST`) so existing operator muscle memory keeps working. `EV_BIND`
is the new canonical knob and supersedes per-script names in any conflict.

---

## Tagged Exceptions

Some services legitimately need 0.0.0.0. The audit script
(`03_AUTOMATION_CORE/01_Scripts/network_binding_audit.py`) recognizes
exception tags on the same line as the bind:

| Tag | Meaning |
|---|---|
| `# bind:public-by-design` | Receives unsolicited public traffic (webhooks, Twilio, public API) |
| `# bind:managed-platform` | Railway / Cloudflare Pages / Vercel / Heroku, platform requires 0.0.0.0 |
| `# bind:tailnet-only` | Host has no public interface OR public ports are firewalled and verified |
| `# bind:lan-required` | Customer-facing hardware on LAN (POS, kiosk) |
| `# bind:legacy-archive` | Frozen archive copy, not in use |

Anything else binding `0.0.0.0` is drift and fails the audit.

Audit-known approved bindings:
- `mcp_servers/dispatcher_relay/relay.py`, Supabase webhook receiver, `# bind:public-by-design`
- `03_AUTOMATION_CORE/01_Scripts/hive_voice_handler.py`, Twilio voice webhook, `# bind:public-by-design`
- POS apps under `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/operations_*`, LAN register access, `# bind:lan-required`
- Railway / Cloudflare Pages deploy targets, `# bind:managed-platform`

---

## What Got Patched in the 2026-05-18 Sweep

**Default flipped to 127.0.0.1:**
- `06_DEVELOPMENT/xlm_bot/run-dashboard.sh`
- `06_DEVELOPMENT/xlm_bot/dashboard.py`
- `06_DEVELOPMENT/xlm_bot/claude_chat_api.py`
- `06_DEVELOPMENT/xlm_bot/docker-entrypoint.sh`
- `06_DEVELOPMENT/xlm_bot/dashboard_django/start.sh`
- `09_DASHBOARD/aa_dashboard/app.py` and `master_restart.sh`
- `09_DASHBOARD/master_dashboard/app.py` and `master_restart.sh` and `analytics_run.sh`
- `03_AUTOMATION_CORE/01_Scripts/code_server_daemon.sh`
- `03_AUTOMATION_CORE/01_Scripts/start_code_server.sh`
- `03_AUTOMATION_CORE/01_Scripts/claude_chat_bridge.py`
- `03_AUTOMATION_CORE/01_Scripts/crypto_bot/run_dashboard.sh`
- `03_AUTOMATION_CORE/06_AI_Tools/echo_mind/server.py`
- `06_DEVELOPMENT/everlight_os/blinko/blinko_lite.py`
- `06_DEVELOPMENT/everlight_os/computer_use/server.py`
- `06_DEVELOPMENT/stark_ai/server.py`
- `06_DEVELOPMENT/hive_directory/run.sh` and `hive-directory.service`
- `06_DEVELOPMENT/hivemind_saas/installer/install_hivemind.sh`

**Left intentionally on 0.0.0.0 with tag:**
- `mcp_servers/dispatcher_relay/relay.py` (Supabase webhook receiver, `# bind:public-by-design`)
- `03_AUTOMATION_CORE/01_Scripts/hive_voice_handler.py` (Twilio voice, `# bind:public-by-design`)
- POS apps (LAN-required)
- Railway / Cloudflare Pages prototypes (managed-platform)

**Not touched:**
- `06_DEVELOPMENT/everlightventures/` (separate git repo for the public site mirror)
- `08_BACKUPS/`, `*.bak`, `legacy_*`, `prototype_*` (frozen archives)
- `_state/audit_log/*` (historical records of past state)
- Doc-only `0.0.0.0` mentions in `.md` runbooks (descriptive, not executable)

---

## Verification

After this sweep, every workspace service that was running on
`0.0.0.0` should restart on `127.0.0.1` after its next service restart.
On the phone right now (verified at sweep time), no process was actually
bound to `0.0.0.0`, the patches affect the *next* restart, not the
current process tree.

To run the audit anytime:
```bash
python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/network_binding_audit.py
```

Exit 0 = clean. Exit non-zero = drift, with file/line/reason printed.
