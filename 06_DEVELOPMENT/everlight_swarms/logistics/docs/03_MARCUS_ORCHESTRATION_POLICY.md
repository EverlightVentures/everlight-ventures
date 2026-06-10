# Logistics Swarm Orchestration Policy v0.1
**Owner:** Marcus Cole, Chief Operator | **Date:** 2026-05-07 PT
**Authority:** Lucrex directive, Marquise approval

Right then. The Hive and the Swarm are different layers. They do not collide.

## 1. LAYER SEPARATION
- **Hive Mind (63 agents)** = decision layer. Classify, debate, decide, dispatch. Triggered by user query or scheduled task.
- **Logistics Swarm (8 Open Swarm specialists)** = production layer. One prompt produces one finished artifact (deck, doc, chart, video).
- **Rule:** the Swarm never decides whether to pursue a deal. The Hive decides. The Swarm produces. No exceptions.

## 2. TRIGGER CONTRACT
- **Caller:** Marcus Cole, on behalf of the Hive. No agent invokes the Swarm directly.
- **Precondition:** Lead Qualifier (29) scores a Logistics prospect at or above 70, AND Penny Vance approves the pricing tier.
- **Handoff JSON (canonical):** `{client, scope, region, term_months, pricing_tier, deadline, attribution_agent, trace_id}`.
- **Queue:** drop JSON line to `/home/opc/everlight_swarms/logistics/queue/incoming.jsonl`.
- **Pickup:** Oracle cron every 5 min. Swarm runs, writes to `outgoing.jsonl` with `{trace_id, status, artifact_uri}`.

## 3. BUDGET GATE
- **Hard cap:** $50/month on Logistics Swarm token spend.
- **Soft cap:** $5/day. VIP override only on confirmed deals (deal stage at or above proposal).
- **Module:** `content_tools/swarm_budget.py`, mirrors `resend_budget.py` pattern. Categories: `proposal | invoice | onboarding | demo`.
- **Kill-switch:** at daily cap, swarm refuses new runs and posts ONE Slack alert to `#hive-alerts`. No retry storms. No backfill at midnight.

## 4. PUBLISHING + COMMS CONTRACT
Every swarm artifact ships through the branded layer. Brand is default, not discipline.
- HTML to `/home/opc/hive_reports/` (served at `:8504/reports/`)
- Google Doc via `content_tools.n8n_replacements.publish_gdoc`
- Slack card via `content_tools.branded_slack.post_branded_slack` (category=`report`)
- **Forbidden:** direct `api.resend.com` calls; raw `chat.postMessage` for content.

## 5. ATTRIBUTION
Every artifact footer reads: "Drafted by [Human-Named Agent] via Logistics Swarm v0.1." The named agent is the `attribution_agent` field. Surfaces in Blinko, Hive session log, and Django artifact registry.

## 6. CROSS-CHECK RULE
- **Deals 1 through 3:** cross-checked by Forge (engineering soundness), Justine (compliance), Cash (revenue/pricing) before client send.
- **Deal 4 onward:** Justine spot-check only. Forge and Cash on-call for anomalies.
- Per `feedback_cross_check_and_synthesize.md`. Production layer still earns its peer review.

## 7. ROLLBACK / KILL
- One-line kill: `systemctl stop everlight-swarm-logistics` on Oracle.
- If the Swarm goes off-rails or burns budget, kill first, debug second.
- Restart only after Marcus signs off in `#war-room` thread.

---
**Decision:** Approved. Pilot 30 days. Review 2026-06-07.
**Filed under:** ORGANIZATION.md, hive_mind/ORCHESTRATION_DOCTRINE.md (linked).
