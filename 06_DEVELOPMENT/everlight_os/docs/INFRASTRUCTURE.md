# INFRASTRUCTURE.md -- Everlight Ventures Trinity

**Compiled:** 2026-04-28 by Marcus Cole orchestrating Iron Stack + Slate Mercer.
**Doctrine:** First Hive document produced under the new cross-check + synthesize pattern (CLAUDE.md phases 5-7). Audit outputs from Henrik Strand (DevOps), Zara Khoury (Security), Amara Osei (Backend Architecture). Cross-checked by Slate Mercer.
**Provenance:** every claim below is tagged with the contributing agent in `[brackets]`. Where they disagreed, the resolution is explicit.

---

## 60-Second Orientation

**Supabase is the brain. Oracle E5 is the body. Cloudflare + ImprovMX + Stripe + Twilio are the skin. The phone is a remote control, not an organ.** [Amara]

If the phone dies, the business does not.
If Oracle dies, the business sleeps until E5 reboots.
If Supabase dies, the business is amnesiac.
**E5 is mortal. Supabase is the only true persistence.** [Slate -- cross-check catch all three audits missed]

Every outbound email goes through `content_tools.branded_mailer`. Every report goes through `content_tools.n8n_replacements.publish_gdoc`. Every Slack post of substance goes through `content_tools.branded_slack`. Nothing else is canonical. [Amara, agreed]

---

## Trinity Diagram

```
                    LAYER 3 -- EDGE / PUBLIC
   +--------------------------------------------------------+
   |  Cloudflare Pages       ImprovMX (42 aliases)          |
   |  everlightventures.io   *@everlightventures.io ---->   |
   |  (React/Vite, GH CD)    forwards to Gmail inbox        |
   |  Stripe Checkout/Portal Twilio (DID -> /webhook/voice) |
   |  Documenso              sign.everlightventures.io      |
   +-------|---------------|----------------|---------------+
       anon-key reads      |             webhooks (HMAC)
            |              |                |
   +--------v--------------v----------------v----------+
   |          LAYER 1 -- SOURCE OF TRUTH               |
   |   Supabase (jdqqmsmwmbsnlnstyavl, RLS on)         |
   |   - leads, deals, commissions, sessions           |
   |   - HiveArtifact log, payments, contracts         |
   |   - Blinko (knowledge, 449+ notes) MIRRORED here  |
   +-----------^--------------------^------------------+
        service-role rw      |   service-role rw
                |            |
   +------------v------------v------------------------+
   |   LAYER 2 -- COMPUTE / ORCHESTRATION             |
   |   Oracle E5  (163.192.19.196, Restart=always)    |
   |   ALL services bound 127.0.0.1 except :22/:80/:443 |
   |   nginx (:80/:443) is the ONLY public face       |
   |   --------------------------------------------   |
   |   nginx routes:                                  |
   |     /              -> Cloudflare Pages (origin)  |
   |     /lucrex/       -> :3040 (Lucrex command)     |
   |     /ops/          -> :8504 (Django, behind CFA) |
   |     /webhook/twilio -> :8200 (HMAC verify)       |
   |     /webhook/stripe -> :8504/payments (HMAC)     |
   |     /webhook/documenso -> :8504/broker/webhook   |
   |   --------------------------------------------   |
   |   Internal (127.0.0.1 only):                     |
   |     :1111 blinko    :8200 hive-voice             |
   |     :8502 react-dash :8504 hive-django           |
   |     :3101-3107 MCP fleet (SSH-tunneled)          |
   |     :3040 lucrex-os  :5678 n8n (parked)          |
   +-----------^------------------^-------------------+
               | SSH (deploy)     | SSH tunnel (MCP)
               |                  |
   +-----------v------------------v-------------------+
   |   PHONE -- Termux Control Plane (NOT a host)     |
   |   /mnt/sdcard/AA_MY_DRIVE  Claude CLI            |
   |   deploy_to_oracle.sh, manual Piper batches      |
   |   Local SQLite = DEV ONLY, never prod            |
   |   ZERO crons. Migrated to Oracle systemd.        |
   +--------------------------------------------------+
```

---

## VCN Security List -- The Resolution

**Conflict resolved [Henrik vs Zara]:** Henrik's audit listed open ports as "what's needed to reach services." Zara's audit said delete public ingress for those ports. **Zara wins.** Henrik's reachability need is satisfied by nginx subpath routing (proven model with `/lucrex/` on :8080).

**Final VCN ingress rules:**

| Port | Source | Purpose |
|---|---|---|
| 22/TCP | Marquise's home IP + Oracle bastion CIDR | SSH (key-only, fail2ban) |
| 80/TCP | 0.0.0.0/0 | nginx HTTP -> 301 to 443 |
| 443/TCP | Cloudflare IP ranges only | nginx HTTPS, all public traffic |

**DELETE from VCN ingress:** 1111, 5678, 8200, 8502, 8504, 8080. They become 127.0.0.1-only behind nginx. [Zara]

**MCP fleet 3101-3107:** stays bound 127.0.0.1, never in VCN ingress. Phone reaches via SSH ProxyCommand. [Henrik + Zara, aligned]

---

## Service Inventory (canonical)

[Henrik's full table, with bind column corrected per Zara's prescription]

| Service | Internal Port | systemd Unit | Bind | Public Path |
|---|---|---|---|---|
| nginx | 80, 443 | nginx | 0.0.0.0 | yes (the only public face) |
| hive-django | 8504 | hive-django.service | 127.0.0.1 | nginx /ops/ behind CF Access |
| xlm-dash-react | 8502 | xlm-dash-react.service | 127.0.0.1 | nginx /xlm/ behind CF Access |
| blinko | 1111 | blinko.service | 127.0.0.1 | localhost only or via Wireguard |
| n8n | 5678 | n8n.service (parked) | 127.0.0.1 | NOT exposed; rip out by Phase 5 |
| hive-voice | 8200 | hive-voice.service | 127.0.0.1 | nginx /webhook/twilio (HMAC) |
| stark-ai | 8201 (TBD) | stark-ai.service | 127.0.0.1 | nginx-routed if/when public |
| lucrex-os | 3040 | lucrex-os.service | 127.0.0.1 | nginx /lucrex/ behind CF Access |
| MCP blinko-proxy | 3101 | mcp-blinko-proxy.service | 127.0.0.1 | SSH tunnel only |
| MCP market-intel-proxy | 3102 | mcp-market-intel-proxy.service | 127.0.0.1 | SSH tunnel only |
| MCP n8n-proxy | 3103 | mcp-n8n-proxy.service | 127.0.0.1 | SSH tunnel only |
| MCP supabase-proxy | 3105 | mcp-supabase-proxy.service | 127.0.0.1 | SSH tunnel only |
| MCP stripe-proxy | 3106 | mcp-stripe-proxy.service | 127.0.0.1 | SSH tunnel only |
| MCP resend-proxy | 3107 | mcp-resend-proxy.service | 127.0.0.1 | SSH tunnel only |
| xlm-bot | none | xlm-bot.service | n/a (CDP egress) | n/a |
| xlm-ws | none | xlm-ws.service | n/a (WS subscriber) | n/a |

[Henrik's count was 13 services; Amara's was 11. Reconciliation: Amara collapses MCP fleet as one logical layer; Henrik enumerates ports. Both correct at different resolutions. Use Amara's count in marketing, Henrik's in operations.]

---

## Cron + Timer Registry (Oracle systemd ONLY)

**Rule [Amara + Henrik aligned]:** Zero crons on phone. Every recurring job is an Oracle systemd unit. Phone keeps `deploy_to_oracle.sh` and dev-loop helpers only.

| Unit | Cadence | Purpose |
|---|---|---|
| hive-self-healer.timer | every 30 min | Recipe-driven failure recovery |
| triple-threat.timer | every 15 min | Scout/Diagnostic/Coordinator orchestration |
| rex-negotiator.timer | every 2 min | IMAP poll + reply handling |
| sync-deals.timer | every 5 min | Supabase deals sync |
| gmail-organizer.timer | every 10 min | Inbox triage |
| wealth-intel.timer | monthly 1st @ 14:17 UTC | Wealth_OS intel pull |
| broker-orch-replies.timer | every 2 hours | broker_daily_orchestrator replies |
| broker-orch-outreach.timer | 17:00 + 00:00 UTC | broker_daily_orchestrator outreach |
| hive-deal-orch.timer | every hour at :15 | hive_deal_orchestrator broker pipeline |
| hive_watchdog.cron | every 2 min | Service health curl loop |
| flip-os.cron | daily 12:00 PT | flip_os/run_pipeline |
| **NEW: oracle-heartbeat.timer** | every 60s | curl 127.0.0.1:{1111,8200,8502,8504,3040}; Slack-alert on failure |

[Henrik proposed oracle-heartbeat. Zara endorsed it as defensible because curls localhost, never widens attack surface. Combined recommendation.]

---

## Auth Layer -- Decision

**Strategic call [Slate flagged this as the single biggest decision Marquise needs to make]:**

**Branch A -- Cloudflare Access free tier (50 users, GitHub/Google SSO).** Recommended. ~75% confidence right call.
- Pros: zero ops cost, ships in 2 hours, locks every public path behind SSO before traffic hits nginx, free tier stays free at our scale.
- Cons: vendor lock to Cloudflare ecosystem.
- Use it for: `/ops/`, `/lucrex/`, `/xlm/`, `/blinko/` (if ever public).

**Branch B -- Tailscale (rejected for now).**
- Pros: private mesh, zero public ingress except :22.
- Cons: every operator needs Tailscale client; less convenient for occasional Hive operator access.
- Reconsider at: Phase 5+ if scale demands.

**Branch C -- Build own SSO (rejected).** Vanity. We need to close deals, not build auth.

**Webhook auth [Zara catch]:** Twilio + Stripe + Documenso webhooks all enforce HMAC signature validation server-side. Drop unsigned at nginx. Zero exceptions.

---

## The 5 Critical Data Flows (Lead -> Commission)

[Amara, kept verbatim]

1. **Scout -> Supabase.** Rex Blackwell pulls Zillow/ATTOM/county on Oracle cron, inserts `leads` row with motivation_score + state_gate verdict.
2. **Qualify -> Outreach.** Django job filters state_gate='allow' + score>=70, queues outreach_tasks, branded_mailer ships via Resend, logged to HiveArtifact.
3. **Reply -> Negotiate.** IMAP IDLE on Oracle detects reply, flips lead.status='engaged', creates match row, Marcus dispatches Harrison/Cupid; conversation in Supabase messages.
4. **Contract -> Sign.** PSA generator renders, documenso_client.create_envelope() posts to sign.everlightventures.io, webhook back to Oracle flips deals.stage='contracted'.
5. **Close -> Commission.** Title firm wires, Stripe webhook hits Oracle, Django writes commissions row, branded Slack card to #revenue-dashboard, ledger immutable.

---

## The 5 Gaps All Three Audits Missed

[Slate's cross-check found these. None are in the original audits. They become Phase 5+ work.]

1. **Backup / DR for Supabase + Blinko + jsonl logs.** No daily snapshot, no offsite, no restore drill. **E5 is mortal.** If the disk corrupts or Oracle Always-Free reclaims the instance for inactivity, the entire Layer 2 disappears. Mitigation: nightly Supabase dump + Blinko export -> Oracle Object Storage. Owner: Henrik.

2. **Secrets-management lifecycle.** Resend, Twilio, Stripe, Supabase keys live in `/home/opc/.env` with no rotation cadence. OpenAI key already rotated once -- ad hoc, not policy. Mitigation: HashiCorp Vault or sops + age. Quarterly rotation cron. Owner: Zara.

3. **Monitoring / alerting SLO doctrine.** Heartbeat alerts on failure -- but no SLO definitions, no alert-fatigue guards, no escalation path beyond "Slack-ping Marquise." Mitigation: define SLO per service (uptime %, p95 latency), alert thresholds, burn-rate alerts. Owner: Henrik.

4. **On-call / single-operator continuity.** Marquise IS on-call. No runbook for "Marquise unreachable for 48h." Mitigation: written runbook per service + hive_self_healer recipe coverage so the system survives 48h alone. Owner: Marcus.

5. **Cost monitoring tripwires.** Oracle Always-Free has bandwidth caps. Resend has 3000/mo (gated). Twilio + Supabase row counts have no tripwire. Mitigation: daily cost-snapshot cron + Slack-alert on threshold cross. Owner: Penny.

---

## The Phasing -- Execute in This Order

[Slate's recommendation, accepted.]

| Phase | When | Work | Owner |
|---|---|---|---|
| **0** | TODAY (2-4h) | Stripe + Twilio + Documenso HMAC signature validation. Highest EV-loss prevention, lowest effort. One forged webhook = real-money or compliance hit. | Zara + Forge |
| **0.5** | TODAY | **Oracle reachability** -- Marquise verifies E5 via Cloud Console + VCN security list. Nothing else moves until Oracle is accessible. | Marquise |
| **1** | This week | Cloudflare Access in front of `/ops/`, `/lucrex/`, `/xlm/`. Then rebind 1111/5678/8200/8502/8504/3040/3101-3107 to 127.0.0.1. | Henrik + Zara |
| **2** | This week | Delete VCN ingress for 1111/5678/8200/8502/8504/8080. Only AFTER Phase 1 verifies reachability via nginx routing. | Henrik |
| **3** | Next week | oracle-heartbeat.service + Slack alert wiring. Hive_self_healer recipe coverage extension. | Henrik + Forge |
| **4** | Next week | Migrate 7+ phone crons to Oracle systemd. Delete phone copies (CRON_MIGRATION_TO_ORACLE.md cleanup pass). | Aria Chen + Forge |
| **5** | Week 3 | Backup / DR -- Supabase nightly dump + Blinko export to Oracle Object Storage. Restore drill quarterly. | Henrik |
| **6** | Week 4 | Secrets-rotation cron, cost-monitoring tripwires, SLO doctrine, on-call runbook. | Zara + Penny + Marcus |

---

## What This Architecture Does NOT Cover

[Honest scope limits]

- **Multi-region failover.** Single VM, single region. Acceptable at current scale; revisit at $50k+/mo revenue.
- **Compliance certifications.** SOC 2 Type II posture is documented in Move D Mac-Minis playbook but not yet implemented. Required for regulated SMB consulting installs.
- **Database HA.** Supabase managed handles this for them, but Blinko self-host has no HA. Acceptable as long as Supabase remains the source of truth and Blinko is a derived index.
- **Disaster runbooks for non-Marquise operators.** No documented playbook for "stranger-takes-over." Out of scope until first hire.

---

## Provenance Index

| Section | Primary contributor | Cross-checker | Resolution |
|---|---|---|---|
| 60-second orientation | Amara Osei | Slate Mercer | Slate added "E5 is mortal" caveat |
| Trinity diagram | Amara Osei | Henrik Strand | Henrik corrected port bindings to localhost |
| VCN security list | Zara Khoury | Slate Mercer (cross-check) | Zara wins over Henrik's open-port list |
| Service inventory | Henrik Strand | Zara Khoury (bind column) | Combined: Henrik's enumeration + Zara's bind discipline |
| Cron registry | Henrik Strand | Amara Osei | Aligned: zero phone crons; oracle-heartbeat new |
| Auth decision | Zara Khoury | Slate Mercer (option tree) | Cloudflare Access wins; Tailscale + custom rejected |
| 5 critical data flows | Amara Osei | (no conflicts found) | Verbatim |
| 5 gaps missed | Slate Mercer | (none of original 3 covered these) | New section |
| Phasing | Slate Mercer | Marcus Cole | Accepted with TODAY 0.5 added for Oracle reachability |

**Single canonical entry point** -- this file. Any new Hive agent reads this first. [Amara]

**Decision log:** every conflict resolved above is logged below for future audits.

---

## Decision Log

- **2026-04-28 conflict:** VCN ingress -- Henrik's open-ports vs Zara's localhost-only. **Resolution:** Zara wins. Henrik's reachability needs satisfied by nginx subpath routing.
- **2026-04-28 strategic call:** Auth layer -- 3 branches considered (CF Access, Tailscale, build-own). **Decision:** CF Access free tier. ~75% confidence; reversible.
- **2026-04-28 cross-check finding:** All three audits treated E5 as immortal. **Acknowledgment:** E5 is ephemeral, Supabase is persistence. Phase 5 backup/DR addresses.
- **2026-04-28 doctrine update:** Hive Mind Auto-Dispatch now has 9 phases (was 7), with Cross-Check (5) and Synthesize (6) added. This INFRASTRUCTURE.md is the first artifact produced under that pattern. See `feedback_cross_check_and_synthesize.md` memory.

---

**Next review:** quarterly OR after any phase completes. Owner: Marcus Cole.
