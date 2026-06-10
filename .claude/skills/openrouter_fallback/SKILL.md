---
name: openrouter_fallback
description: Route low-stakes Hive calls through OpenRouter for 30-40% Anthropic burn reduction. NEVER on XLM bot, contracts, compliance, or final branded renders.
---

When to use:
- Low-stakes, high-volume, non-revenue-critical Hive calls.
- Specifically: Slack thread replies, status pings, log/cron output summaries, branded_slack body draft polish, Blinko note tagging, transcript chunk summarization, agent firmware lint, 1-paragraph rewrites.

NEVER use on:
- xlm_bot/claude_advisor (live capital)
- contract_generator, compliance_gate, deal_closer, financial_safeguard
- branded_mailer / branded_slack final renders (brand voice degrades)
- Client-facing email send-time (use for draft, polish on Sonnet)

Procedure:
1. Verify `OPENROUTER_API_KEY` in `~/.env` (phone) and `/home/opc/.env` (Oracle). If missing, halt + flag to Marquise.
2. Set env block at the call site:
   - `ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1`
   - `ANTHROPIC_AUTH_TOKEN=$OPENROUTER_API_KEY`
   - `ANTHROPIC_API_KEY=` (explicitly blank)
   - `ANTHROPIC_MODEL=openrouter/auto` (free-models router; per-model endpoints rate-limit hard)
3. Wrap with try/except. On HTTP 429 or empty content -> fall back to `minimax/minimax-m2.5` ($0.30/$1.20 -- 16x cheaper than Opus). Second failure -> direct Anthropic Sonnet.
4. Log the rung that won to `logs/router_decisions.jsonl` with correlation_id.
5. Add `model_used` to every HiveArtifact row so the :8504 dashboard can show $ saved per session.

Routable call sites (phase in one at a time, monitor 7d quality):
- hive_voice_handler Marcus phone-action acks
- inbound_watch_daemon email classifier first pass
- wholesale_engine Piper/Harrison draft generation (final polish stays on Sonnet)
- blinko_optimizer.py note tag/summary regeneration
- claude_bridge_guardian.sh cron-output summarization
- branded_slack short-form ops pings
- NOTEPAD transcript ingestion summaries
- Codex/Gemini cross-check synthesizer first draft

Quality gate:
- Compare 50 outputs side-by-side over 7 days before flipping a call site.
- If any drift in tone/voice/numbers, route stays on Sonnet.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/01_Claude_and_Codex/claude_code_plus_openrouter_free.txt
Owner: Forge (engineering) + Cash (cost report).
