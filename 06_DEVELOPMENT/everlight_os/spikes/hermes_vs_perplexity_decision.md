# Hermes Agent vs Perplexity Computer - Agent-Browser Decision

**Date**: 2026-04-21
**Owner**: Marcus Cole + Forge + Cash Mooney
**Sources**:
- `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/02_AI_Agents_and_Swarms/hermes_agent_100k_github_stars.txt`
- `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/09_Research_and_Perplexity/perplexity_computer_clearly_explained.txt`

---

## Context

Everlight has three candidate "agent with a browser" stacks for running Piper's outbound and Hammer's follow-up:

1. Hermes Agent + browser-harness (self-hosted on Hostinger VPS, ~$10-50/mo)
2. Perplexity Computer (hosted, pay-per-run, Pro+ required)
3. Build-our-own (Puppeteer/Playwright + Claude orchestration)

## Comparison

| Dimension | Hermes + browser-harness | Perplexity Computer | Build-our-own |
|---|---|---|---|
| Setup time | 1 hour (Hostinger template) | 10 min (add Pro+ plan) | 2-3 weeks |
| Recurring cost | ~$10/mo VPS + OpenRouter tokens | $20+/mo for Perplexity Pro+ + per-run | $0 infra if on Oracle, but engineering time |
| Self-improving skills | YES (Hermes writes new skills) | NO (fixed capabilities) | Only what we build |
| Browser reliability | browser-harness "self-healing" | proprietary, opaque | depends on our code |
| Output ownership | our VPS, our logs | Perplexity cloud | our infra |
| Integration with our Hive | via OpenRouter + our skill library | via Perplexity web UI | deep native |
| Privacy | our VPS | data to Perplexity | our infra |

## Recommendation

**Hermes + browser-harness first, Perplexity Computer as a tried-alongside backup, build-our-own never (waste of cycles).**

Reasons:
1. Hermes is actively developed (741 PRs in 20 days at time of video) and already includes browser capability via browser-harness.
2. $10/mo VPS fits the Hive's cost discipline better than a per-run service.
3. Self-improving skills directly match our fire-team doctrine (agents that learn and compound).
4. Build-our-own is 2-3 weeks of Forge's time we would rather spend on revenue-path work.

## What would flip the recommendation

- If Hostinger's Hermes template is broken or the LLM call pattern is incompatible with Opus/Sonnet routing, fall to Perplexity Computer for urgency.
- If Perplexity announces a unified plan that covers Computer + Spaces + Sonar API at < $50/mo, re-evaluate.
- If we have a client-facing deliverable that requires deterministic repeatability (compliance), Perplexity's audit trail may be preferable.

## Decision gate

Lucrex has parked Hermes VPS this session (cost gate). When unparked, spike it for 1 week. If Piper sources at least 3 extra qualified leads/day that Hammer confirms would have been missed, promote to permanent. Otherwise cancel and pull the plug.

## Status

Parked. Resume when ready. Doc is here to make the call fast.
