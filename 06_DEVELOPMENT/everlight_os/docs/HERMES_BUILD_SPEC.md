# Hermes Browser Harness -- Build-Ready Spec

**Date:** 2026-05-19
**Status:** SPEC ONLY (no code, no deploy)
**HOST DECISION (LOCKED 2026-05-19 by Rich):** AceMagician PC (free). Hostinger $5/mo is the Phase-2 fallback only if PC reliability fails the >2-failed-runs/week gate.
**Owner:** Forge (build), Cash Mooney (cost-gate), Piper Reeves (consumer of leads)
**Supersedes parts of:** `spikes/hermes_vs_perplexity_decision.md` (which is a decision doc, not a build doc)

---

## Why this exists

Wholesale pipeline bottleneck is lead acquisition. Per 2026-05-18 mailbox
audit: scout heartbeats show `properties_found: 0` for 60+ days. The
4 daily scouts are scanning Atlanta/Dallas, not TN, and even when on-target
they yield nothing. Meanwhile 114 TN parcels are hand-scraped, sitting in
`Wholesale/owner_downloads/parsed/` waiting on skip-trace.

Hermes is the agentic browser-harness that closes this gap: a self-improving
agent that drives Chrome through assessor sites, downloads MHT property
records, parses them, and emits structured leads into Supabase. Same shape
as the hand-scraping, automated.

## Scope (Phase 1 -- Deal 1 adjacent)

Scrape TN-only counties (Shelby, Davidson, Hamilton, Knox). Output: enriched
property records into `leads_db.json` + Supabase `broker_leads` table. Output
quality bar: must include parcel_id, owner_name, owner_mailing_address,
property_address, assessed_value, deed_type, deed_date. Skip-trace happens
downstream (existing `Wholesale/skip_trace/intel_enricher.py`).

OUT of scope Phase 1: outbound (still locked TN-only until 2026-06-17),
non-TN counties, deed image OCR, comp pulls (ATTOM not wired).

## Host decision (cost gate)

| Option | Cost | Effort | Verdict |
|--------|------|--------|---------|
| AceMagician PC (tailnet, already on) | **$0** | 2-4 hrs | **RECOMMENDED Phase 1** |
| Hostinger VPS KVM 1 | $5/mo | 1 hr | Phase 2 fallback if PC unreliable |
| Hostinger Shared Hosting | $10/mo | 1 hr | NO (PHP-only, can't run Chrome) |
| Browser-use Cloud (per-run) | ~$0.10/scrape | 0 setup | NO (lock-in, latency) |

AceMagician is the right call: free, fast, already on tailnet, peer-cache for
Hive memory already. Per `feedback_no_trash_until_deal1` + `feedback_apply_macro_micro_gate_before_recommendation_list`,
paid infrastructure waits until Deal 1 funds it. PC unreliability mitigated
by: nightly cron retry, alerts on staleness via `it_triage`.

If PC reliability turns out to be the actual bottleneck (>2 failed runs/week),
flip to Hostinger KVM 1 -- one-day port of the docker-compose stack.

## Component map

```
[AceMagician PC, tailnet 100.93.253.49]
  |
  +- docker-compose.yml
  |   +- chromium-headless         (Playwright base image, no GUI)
  |   +- hermes-agent              (Hermes OSS, talks to LLM via OpenRouter)
  |   +- redis                     (job queue + dedup cache)
  |   +- hermes-runner             (cron-fed: every 6h, picks target county, fires hermes)
  |
  +- volumes:
      +- ./_scraped/              (raw MHT downloads, retained 30 days)
      +- ./_skill_library/        (Hermes self-written skills, persisted)
      +- ./_logs/                 (per-run audit jsonl)
  |
  +- writes to:
      +- _state/scraping_queue.jsonl   (over tailnet sshfs to phone workspace)
      +- Supabase broker_leads table   (via service-role key from vault)
```

## Critical wiring points

1. **LLM auth via OpenRouter, not direct Anthropic/OpenAI.** Per
   `openrouter_fallback` skill: 30-40% cost reduction on low-stakes calls.
   Hermes uses Claude Haiku 4.5 by default (cheap + fast for browser navigation),
   escalates to Sonnet 4.6 only when stuck on a non-trivial UI.

2. **Output goes through `http_client.request_urllib`** (built this session)
   when writing to Supabase. Picks up canonical UA, retry, audit log.

3. **No direct outbound to property owners.** Hermes is intake-only.
   Phase 1 outbound is still locked TN per `senders_authority.yaml` lockdown.

4. **DNC gate runs at Supabase insert time, not scrape time.** Scraping
   public records is legal; soliciting DNC-listed numbers is not. Gate enforces
   at downstream send via existing `dnc_gate.py`.

5. **Eradication gate runs at every layer.** `eradication_gate.py` blocks
   Streubel-class records from ever entering the pipeline, even if the assessor
   site returns them. Hardcoded list per `feedback_streubel_permanent_eradication`.

## Phase 1 build sequence (1-week sprint, ~12 hours of work)

| Day | Task | Owner |
|-----|------|-------|
| 1 | AceMagician: install docker + docker-compose; verify Chrome headless launches | Forge |
| 1 | Clone Hermes OSS, configure for OpenRouter + Claude Haiku 4.5 | Forge |
| 2 | Write 4 county-specific Hermes skills (Shelby, Davidson, Hamilton, Knox assessor flows) | Forge + Hermes (self-improving loop) |
| 3 | hermes-runner cron: every 6h, picks a county, scrapes 50 most-recent deed transfers | Forge |
| 3 | Output to `_scraped/<county>/<date>.json` + Supabase `broker_leads` upsert | Forge |
| 4 | Smoke test: 4 counties x 1 run = 200 candidate leads | Forge + Piper review for quality |
| 5 | Reliability: 7-day soak, alert on >2 failed runs via `it_triage` queue | Marcus monitors |
| 6 | Skip-trace gate: only leads with parseable owner mailing address advance to Piper queue | Piper |
| 7 | Volume sanity: target 50-100 fresh TN leads/week minimum to justify the build | Cash Mooney decision |

## Success criteria (gate to Phase 2)

- 50+ fresh TN leads/week sustained for 2 consecutive weeks
- <2 failed Hermes runs/week
- Piper confirms at least 5 of the first 50 leads were ones she would have missed
- Zero rogue sends (Hermes never triggers outbound, only fills the queue)

Failing any criterion = back to the spike-doc decision branch (Perplexity
Computer trial, or abandon for now).

## What this build does NOT do

- Outbound (still TN-locked until 2026-06-17)
- Skip-trace (separate module, exists already)
- Comp valuation (ATTOM not wired)
- Multi-state expansion (post-lockdown, post-Deal 1)
- Image/PDF OCR on deed scans (deferred until parser proves volume)
- Browser-use Cloud integration (defer; AceMagician proves the pattern first)

## Cost ceiling (hard)

- AceMagician: $0 (already running)
- OpenRouter tokens: ~$5-15/mo at 4 county scans x 50 leads/run x daily
  (Claude Haiku 4.5 at $1/Mtok input, $5/Mtok output, ~5K tokens per scrape decision)
- Total Phase 1: under $20/mo, within `feedback_apply_macro_micro_gate` budget

If costs exceed $20/mo, pause and audit before continuing. Hermes self-
improving loop will try to optimize prompt length on its own.

## Open items for operator

1. Confirm AceMagician is the host (vs Hostinger KVM 1 at $5/mo)
2. Confirm OpenRouter account is funded (or fund $10 starter credit)
3. Confirm Supabase service-role key has insert permission on `broker_leads`
4. Greenlight start of Day 1

Once these 4 are confirmed, Forge can begin the 7-day sprint.
