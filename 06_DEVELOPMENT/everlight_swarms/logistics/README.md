# Everlight Logistics Swarm v0.1 (POC)

**Status:** SCAFFOLDED (phone-side). NOT deployed. Oracle SSH currently unreachable.
**Upstream:** [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm) v1.0.0 (MIT, 2026-04-22)
**Owner:** Forge (engineering) | Penny (pricing) | Marcus Cole (orchestration)

## Purpose
One terminal prompt to a full Logistics client package: pitch deck + MSA + SOW +
pricing/margin chart + onboarding packet. Replaces hand-built proposals.

## Layer separation
- **Hive (63 agents)** = decides whether to pursue a deal, classifies, qualifies, prices.
- **Logistics Swarm (8 specialists)** = produces the artifact AFTER the Hive approves.
- The Swarm never decides. The Hive decides. The Swarm produces.

## Trigger contract
Marcus Cole drops a JSON to `queue/incoming.jsonl`:
```
{"client": str, "scope": str, "region": str, "term_months": int,
 "pricing_tier": str, "deadline": ISO8601, "attribution_agent": str,
 "trace_id": uuid}
```
Oracle cron fires the swarm every 5 min. Output lands in `outgoing.jsonl` +
`/home/opc/hive_reports/swarm_logistics/<trace_id>/`.

## Budget gate (HARD)
- Monthly: $50 cap
- Daily: $5 soft, kill at $10
- Module: `content_tools/swarm_budget.py` (mirrors `resend_budget.py`)
- Categories: `proposal | invoice | onboarding | demo`
- Kill-switch: ONE Slack alert to `#hive-alerts`, no retry storms.

## Branding contract
Every artifact ships through:
- `content_tools.report_template` (palette: gold #D4A843 / dark #0A0A0A / light #E8E8E8)
- `content_tools.n8n_replacements.publish_gdoc`
- `content_tools.branded_slack.post_branded_slack(category="report")`
NO direct `api.resend.com` or raw `chat.postMessage` for content.

## Cross-check rule
- Deals 1-3: Forge + Justine + Cash review before client send.
- Deal 4+: Justine spot-check only.

## Kill-switch
`systemctl stop everlight-swarm-logistics` on Oracle. Kill first, debug second.

## File map
```
agents/
  orchestrator/   # task router (Marcus's canonical handoff schema)
  intake/         # captures client RFP -> structured scope
  research/       # competitive bid research, regional rate cards
  pricing/        # Penny's margin model + walk-away floor (DONE)
  docs/           # MSA + SOW (Word + PDF)
  slides/         # branded pitch deck (HTML -> PowerPoint)
  onboarding/     # post-signature kickoff packet (Composio: HubSpot + Calendly)
shared/
  everlight_brand.json     # palette + fonts + wordmark
  deals_closed.json        # deal counter for risk premium tier
  state_gates.json         # symlink to Wholesale/compliance for region rules
queue/
  incoming.jsonl           # Marcus drops triggers here
  outgoing.jsonl           # swarm writes results here
```

## Outstanding (BLOCKERS)
1. **Oracle SSH unreachable from phone** (probed 8504/1111/8504, all returned 000).
   Marquise must verify Oracle health and routing before any deploy.
2. **Open Swarm sandbox model unverified.** Data analyst sandbox could be paid
   `e2b.dev`. Forge to confirm against upstream `package.json` before clone.
3. **AGENTS.md schema not yet ingested.** Pulled from upstream README; the actual
   AGENTS.md fetch + parse is pending.
4. **Composio decision pending** -- free tier confirmation in progress.

## Decisions logged
- Synthesized plan: `docs/SYNTHESIS_v0.1.html`
- Forge fork+deploy plan: `/tmp/forge_logistics_swarm_plan.md`
- Penny pricing spec: `/tmp/penny_pricing_agent_spec.md`
- Marcus orchestration policy: `/tmp/marcus_swarm_orchestration_policy.md`
