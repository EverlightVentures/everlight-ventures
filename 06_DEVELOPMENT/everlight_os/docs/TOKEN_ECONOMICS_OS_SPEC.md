# Token Economics OS (TEO) - Design Spec

**Status:** Approved (Rich, 2026-06-25). Build Phases 1 through 5.
**Owner:** Lucrex / Hive. Code lives in `03_AUTOMATION_CORE/01_Scripts/token_economics/`.
**One-liner:** Every AI token we spend is COGS. TEO catalogs the keys that spend it, measures what each project costs in tokens, measures what each project recoups (through ANY avenue, attention being the primary one), and reports the payback ratio per project so we route effort to where compute actually pays back.

---

## Why this exists (the operator framing)

Rich's thesis: our projects are built on AI tools; AI tools cost tokens; so the root unit of our P&L is the token. If we cannot make a token net-positive for ourselves, we cannot make it net-positive for a customer. First job: prove every project clears its own token cost. Recoup is "by any means" (ads, IAP, trading-fee share, affiliate, leads, traffic), with attention as the number-one currency because it converts into all the others.

Today the data needed to see this is scattered: keys live in plaintext `.env`, some hardcoded in `.mcp.json` (in git), token spend is logged but untagged, and attention is measured for exactly one project (Vantaris) while Alley Kingz and BCARDI are dark. TEO centralizes all of it.

## The one brutal truth (from 2026 research, see Findings below)

Monetization rate is not the problem. Distribution is. Every attention channel pays roughly $1 to $5 per 1,000 sessions. So the 4X to 10X payback target cashes out to: recouping 25 cents of tokens needs about 125 real sessions; 4X needs about 500. The lever is not "better ad network." It is "who supplies the traffic." The two lanes where someone else supplies or bypasses traffic, on assets we already shipped:
1. Web-game portals (CrazyGames / Poki via Playgama Bridge) lend 30M+ MAU, 50 to 80 percent rev share. Alley Kingz is already HTML5.
2. pump.fun creator fees pay on trading volume, not views; small-cap earns the highest rate (0.95 percent per trade). BCARDD already exists on Solana.

TEO's job is to make this visible per project and route us to these lanes.

---

## Architecture: two pillars plus one agent

### Pillar 1: Key Registry (the substrate)
A single agent-readable catalog of every key. Metadata only, never the secret string. Fields per key:
`key_name | project | sub_avenue | provider | owner | created | expires | refresh_cadence | monthly_cost_usd | status | value_location`

- Secret VALUES stay in `secrets_vault.py` / Proton Pass. The registry stores only `value_location` (a pointer like `vault:CF_API_TOKEN` or `proton:BCARDD_TG`).
- Why it is the substrate: cost-per-project is impossible until every key is tagged to a project plus sub-avenue.
- Security loop closed in Phase 1: keys hardcoded in `.mcp.json` (tracked by git) get pulled into the vault and replaced with references.

### Pillar 2: Token Payback Meter
- Cost side (COGS): token spend per project. Extend the existing `content_tools/swarm_budget.py` ledger (`_logs/swarm_budget.jsonl`) to tag every call with `project` plus `sub_avenue` via the registry. Roll up to per-build micro-cost AND monthly aggregate dollars.
- Recoup side (income, any avenue): thread Alley Kingz plus BCARDI into the EXISTING Vantaris Supabase analytics sink. Add monetization event types: `ad_impression`, `ad_revenue`, `referral_click`, `creator_fee`, `affiliate`, `iap`, `lead`.
- Output: `payback_ratio = recoup_income / token_cogs` per project, vs the 4X target, plus the leading indicator sessions-per-token-dollar.

### The Analytical Agent
Scheduled agent (runs on e5, never the phone, per cron doctrine). Weekly it: reads the meter, computes payback per project, flags underwater projects, and converts the numbers into the next move ("Alley Kingz: X dollars tokens, Y sessions, 0 dollars income, not on a portal, ship to CrazyGames"). Posts a branded Slack card plus 3-format report.

---

## What we REUSE (do not rebuild)

| Need | Existing asset | Action |
|---|---|---|
| Secret storage | `content_tools/secrets_vault.py` (Fernet) | Reuse as value store; finish migration off plaintext `.env` |
| Env loading | `content_tools/env_loader.py` | Reuse |
| Token spend ledger | `content_tools/swarm_budget.py` plus `_logs/swarm_budget.jsonl` | Extend with project / sub_avenue tags |
| Attention sink | Vantaris Supabase: `sessions`, `analytics_events`, `page_views`, `high_scores`, `web_leads`, view `site_traffic_daily` | Reuse as the canonical sink; thread AK plus BCARDI in |
| Revenue plumbing | Vantaris `stripe-products.ts` plus `create-checkout` edge fn | Reuse; emit `iap` / `checkout_completed` into analytics |
| Reporting | `content_tools/n8n_replacements.publish_gdoc` plus `branded_slack` | Reuse for the agent's weekly report |

## What we BUILD NEW
- The Key Registry catalog (local manifest plus schema) plus a small CLI / agent reader.
- COGS tagging layer on top of `swarm_budget`.
- AK plus BCARDI analytics client shims into the Vantaris sink.
- The payback-ratio view plus a single dashboard panel.
- The Analytical Agent plus its weekly schedule.

---

## Build phases (each usable standalone)

**Phase 1: Key Registry plus leak fix.** Build the catalog (metadata-only), populate it from current `.env` / `.mcp.json` / vault, tag every key to project plus sub_avenue, and pull hardcoded keys out of `.mcp.json` into the vault. Outcome: one place any agent can read "what keys exist, whose, expiring when, costing what."

**Phase 2: COGS ledger.** Tag token spend by project / sub_avenue. Outcome: dollar cost per project, per build and per month.

**Phase 3: Attention sink.** Wire Alley Kingz plus BCARDI into the Vantaris analytics tables. Outcome: sessions / clicks / income per project, all in one sink.

**Phase 4: Payback dashboard plus Analytical Agent.** One view: tokens to dollar COGS to sessions to income to payback ratio per project; agent narrates weekly. Outcome: the number Rich asked for, automated.

**Phase 5: The 3 distribution plays the meter points to.** (a) portal-publish Alley Kingz, (b) wire BCARDD's creator-fee claim wallet, (c) monetize plus route the Telegram bot. Outcome: the actual recoup lanes turned on.

---

## Storage and doctrine
- Catalog metadata: version-controlled local manifest (offline-first, agent-readable) plus Supabase mirror for the dashboard. Secret values: vault / Proton only.
- Crons on e5, never phone. Free-first throughout. Branded reporting for any human-facing output.

## Findings appendix (2026 research, cited)
- Tiny-traffic web yield: about $1 to $5 per 1,000 sessions; realistically $1 to $2 blended low-geo. (Playgama, Coinis, Adsterra, Monetag, 2026)
- Rewarded web-game eCPM US $15 to $28; portal session RPM about $1 to $5 tier-1. Poki 50/50, Playgama Bridge about 80 percent, GameMonetize about 45 percent. (Playgama, Poki / CrazyGames docs, 2026)
- pump.fun creator fee 0.95 percent down to 0.05 percent sliding by mcap; $10M volume is about $5k creator payout; up to 10 split wallets. (pump.fun docs, The Block, CoinDesk, 2025-2026)
- Telegram mini-app: rewarded interstitial CTR 20 to 40 percent, video / bot CPM $3 to $3.80; Stars about $0.013 each. (Adsgram, Merge, 2026)
- Honest gap across all sources: traffic, not rate. Ride borrowed traffic (portals) plus volume rewards (pump.fun) for same-quarter payback; treat own-channel audience as a 6 to 12 month build.
