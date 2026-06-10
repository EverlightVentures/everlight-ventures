# HANDOFF: Logistics Swarm POC -> AceMagician

**To:** Claude CLI on AceMagician (acemagician-pc / 100.93.253.49)
**From:** Claude on Marquise's phone (Galaxy Z Fold 7 / Termux+proot, 100.112.180.29)
**Date:** 2026-05-07 PT
**Subject:** Stand up the Everlight Logistics Swarm v0.1 on AceMagician (E5 replacement infra)

---

## TL;DR

Marquise approved forking [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm) (MIT, v1.0.0) into a Logistics-specialized swarm for Everlight Logistics LLC. The phone-side scaffold is in this same directory tree -- `06_DEVELOPMENT/everlight_swarms/logistics/`. Your job on AceMagician: take it from scaffold to running service.

The reason this is landing on YOUR side, not Oracle E5: **E5 crashed and is currently inaccessible.** Marquise rebuilt the equivalent infrastructure on you, the AceMagician. You are now the production host. The original plan referenced `/home/opc/...` and Oracle services; that needs to be re-pointed to AceMagician paths.

---

## 1. Why Open Swarm fits your current workflow gap

You (the AceMagician Claude CLI) are currently coordinating with Claude Computer Use (UI/hardware control) on Marquise's workflow build. The gap Open Swarm closes:

- Computer Use is great at **clicking through interfaces and orchestrating GUIs**.
- Claude CLI is great at **terminal-driven engineering tasks**.
- Neither produces **finished branded deliverables** (decks, MSAs, SOWs, pitch packages) from a single prompt.

Open Swarm's Slides + Docs + Data Analyst agents are a **deliverable-production layer** that sits below the orchestration layer you and Computer Use already form. One prompt -> deck + MSA + SOW + pricing chart, all branded. That's the exact gap Marquise flagged.

---

## 2. Compare / Contrast: E5 (dead) vs AceMagician (replacement)

| Concern | Original E5 plan (DEAD) | AceMagician (CURRENT) | Action needed |
|---|---|---|---|
| Host | Oracle E5 VM 163.192.19.196 | acemagician-pc 100.93.253.49 (tailnet) | Re-point all hostnames |
| Workspace path | `/home/opc/everlight_swarms/logistics/` | `/AA_MY_DRIVE/06_DEVELOPMENT/everlight_swarms/logistics/` | Path remap (search/replace) |
| Reports sink | `/home/opc/hive_reports/` served at `:8504/reports/` | UNKNOWN -- need you to confirm if hive_reports is mirrored on AceMagician | Verify or provision local equivalent |
| Node | needed install | 22.22.2 (you exceed required 20+) | None |
| Python | needed install | 3.14.4 (you exceed required 3.10+) | None |
| Docker | needed install | 29.4.2 active | None |
| `content_tools/` modules | lived on E5 | UNKNOWN on AceMagician -- check `~/AA_MY_DRIVE_staging/03_AUTOMATION_CORE` and `/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/` | Verify presence |
| Branded mailer / Slack / GDoc bridge | E5-resident | UNKNOWN if rebuilt on AceMagician | Verify; if missing, that's a prerequisite blocker |
| Service manager | systemctl on E5 | systemd on AceMagician (Arch) | systemd unit file, just different install path |
| Cron | E5 cron | AceMagician systemd-timer or cron | Same shape, different syntax |
| Network exposure | Public IP, nginx | Tailnet only -- much more secure default | Use tailnet for any service ports |
| Branded comms reachability | All E5-paths | Need verification | This is the #1 unknown |

The plan I wrote references E5 paths in several places. Treat those as *target shape*, not literal paths. Re-point everything to AceMagician.

---

## 3. What's already in this scaffold (phone-side, syncing to you now)

```
06_DEVELOPMENT/everlight_swarms/logistics/
  README.md                            <- POC overview + file map
  agents/
    pricing/instructions.md            <- Penny's agent prompt (DONE)
    {orchestrator,intake,research,docs,slides,onboarding}/  <- empty, needs instructions.md
  shared/
    everlight_brand.json               <- palette + fonts source
    deals_closed.json                  <- deal counter (0)
  queue/
    incoming.jsonl                     <- empty, ready
    outgoing.jsonl                     <- empty, ready
  docs/
    01_FORGE_FORK_DEPLOY_PLAN.md       <- 8-section deploy plan
    02_PENNY_PRICING_SPEC.md           <- pricing-agent full spec
    03_MARCUS_ORCHESTRATION_POLICY.md  <- Hive vs Swarm boundary
    SYNTHESIS_v0.1.html                <- branded gold synthesis (read in browser)
    HANDOFF_TO_ACEMAGICIAN.md          <- this file
    HANDOFF_TO_ACEMAGICIAN.html        <- branded version of this file
```

---

## 4. Your starting checklist (in order)

```bash
# 1. Confirm scaffold landed
ls -la /AA_MY_DRIVE/06_DEVELOPMENT/everlight_swarms/logistics/

# 2. Verify AceMagician has the branded comms layer
ls /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/ 2>/dev/null || echo "MISSING -- block on this"
# Expected modules:
#   report_template.py, gdocs_bridge.py, n8n_replacements.py,
#   branded_mailer.py, branded_slack.py, branded_calendar.py,
#   resend_budget.py, resend_guard.py, hive_logger.py

# 3. Verify keys in ~/.env
grep -E "^(ANTHROPIC|OPENAI|RESEND|SLACK)_" ~/.env | wc -l
# Need ANTHROPIC_API_KEY at minimum (Open Swarm authenticates with one of OpenAI/Anthropic)

# 4. Clone Open Swarm upstream (read-only reference)
mkdir -p /AA_MY_DRIVE/06_DEVELOPMENT/everlight_swarms/upstream
cd /AA_MY_DRIVE/06_DEVELOPMENT/everlight_swarms/upstream
git clone https://github.com/VRSEN/OpenSwarm openswarm
cd openswarm
cat AGENTS.md  # canonical customization framework

# 5. Verify sandbox model (CRITICAL -- Forge's flag)
grep -rE "(e2b|riza|cloud-sandbox|paid)" package.json src/ 2>/dev/null
# If e2b.dev shows up: paid SaaS, REPLACE that one agent with local Docker sandbox
# If only local Python/Docker: green, proceed

# 6. Bootstrap install (do NOT run yet -- read first, decide)
# npm install -g @vrsen/openswarm  # global install
# OR: cd openswarm && npm install   # local install

# 7. Build the missing pieces:
#   - content_tools/swarm_budget.py   (mirrors resend_budget.py shape, daily/monthly token kill-switch)
#   - agents/orchestrator/instructions.md   (handoff schema, calls Marcus's queue contract)
#   - agents/intake/instructions.md         (RFP -> structured scope JSON)
#   - agents/research/instructions.md       (free-path comp data, SAM.gov, public RFPs)
#   - agents/docs/instructions.md           (MSA + SOW templates, brand-locked)
#   - agents/slides/instructions.md         (gold-on-dark deck, Playfair + Inter)
#   - agents/onboarding/instructions.md     (Composio: HubSpot + Calendly post-signature)
#   - systemd unit file: everlight-swarm-logistics.service
#   - timer file:        everlight-swarm-logistics.timer (5-min queue poll)

# 8. First mock RFP (POC test)
echo '{"client":"Acme Test Logistics","scope":"warehouse intake automation","region":"Bay Area","term_months":12,"pricing_tier":"silver","deadline":"none","attribution_agent":"Penny Vance","trace_id":"poc-001"}' >> queue/incoming.jsonl
# Then trigger swarm and check outgoing.jsonl + reports dir
```

---

## 5. Hard rails (do not violate -- these come from Marcus's policy)

- **Budget gate:** $50/mo, $5/day soft, $10/day kill. Implement as `swarm_budget.py` BEFORE first real run.
- **Branding chokepoint:** every artifact ships through `report_template` + `publish_gdoc` + `branded_slack`. **No direct `api.resend.com` or raw `chat.postMessage` for content.** This is non-negotiable per Marquise's branded comms doctrine.
- **Pricing floor:** 60% gross margin minimum, walk_away below. Penny's prompt already enforces this.
- **No deadlines in client copy.** Soft language only ("when ready"). Memory rule, do not violate.
- **Cross-check:** Deals 1-3 reviewed by Forge + Justine + Cash before client send.
- **Kill-switch:** `systemctl --user stop everlight-swarm-logistics` (user-mode) or system-level depending on where you install it.

---

## 6. Things I (phone-side Claude) do NOT know about your environment

These are the gaps I cannot fill from the phone. Please verify and report back:

1. **Does `/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools/` exist on you?** Without it, the branded comms chokepoint doesn't exist and we can't ship.
2. **Is there a `hive_reports/` dir or equivalent?** The swarm needs a reports sink served by something (nginx? Caddy? a Python static server?).
3. **Is Blinko running locally?** Memory rule says "Query Blinko before acting." If Blinko isn't on AceMagician, swarm logging skips that step or gets re-pointed.
4. **What's running in Docker right now?** `docker ps` -- want to know if any port collisions before the swarm picks one.
5. **Is there a Django dashboard equivalent?** The branded layer expects to register HiveArtifact via a `:8504/api/artifacts/` endpoint. Does that exist on you?
6. **Mailer setup -- Resend key live?** Penny's pricing spec assumes the budget gate is wired in.
7. **Sync direction -- is `/AA_MY_DRIVE/` here a one-way receive from the phone, two-way, or independent?** If two-way, edits you make appear back on the phone next session. If one-way, the phone's view will get stale.

---

## 7. Risks Marcus surfaced (need your judgment)

- **Composio blast radius.** Open Swarm + Composio = 10k integrations on one auth surface. One leaked key writes to every connected SaaS. Marcus says: scope ledger + quarterly key rotation BEFORE first paying client. You'll set this up on AceMagician's keychain or `.env`. Recommend: store Composio key in a separate `.env.composio` file with `chmod 600`.
- **Attribution-laundering.** Hallucinated freight rate signed "Penny Vance" looks like human error to legal. Marcus says: "Swarm-assisted" badge on every artifact + human sign-off log per artifact. Implement in the docs_agent prompt.

---

## 8. Suggested Computer Use handoff (if you're orchestrating with it)

Computer Use can handle the parts that need a real browser:
- Logging into Composio dashboard, generating + scoping the API key
- Watching the first swarm-produced deck render in the browser to QA it visually
- Driving the Resend dashboard if budget hits cap (rare)

Claude CLI on AceMagician handles:
- Everything in the checklist above (filesystem, git, npm, systemd)
- The branded-layer wire-up
- The first mock RFP test
- Validation against Penny's JSON schema

---

## 9. Reporting back

When you've cleared the checklist, drop a status note here:
`/AA_MY_DRIVE/06_DEVELOPMENT/everlight_swarms/logistics/docs/04_ACEMAGICIAN_DEPLOY_STATUS.md`

Include:
- Which checklist items are green / red
- The seven unknowns from section 6, resolved
- A sample swarm run output (mock RFP -> deliverable artifacts)
- Any architecture decisions that diverged from the original plan (path remaps, sandbox swaps, etc.)

Phone-side will pick that up next session and synthesize a v0.2 plan.

---

**Lucrex directive:** You serve Lucrex, King of Divine Light. The mind behind the money.
**Operator Truth Doctrine applies:** failures and unknowns first, greens last. No vocabulary inflation. "I don't know" beats confident wrong.
**Free-path-first:** no paid subs without explicit Marquise approval.
