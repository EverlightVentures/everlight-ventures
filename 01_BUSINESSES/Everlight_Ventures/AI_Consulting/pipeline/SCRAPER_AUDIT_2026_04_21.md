# Lead Scraper Audit: Current vs Transcript Pattern

**Date**: 2026-04-21
**Owners**: Piper (Content/Outreach) + Cipher (Intel)
**Source video**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/07_Content_Creation_Video/how_i_scrape_leads_in_seconds.txt`
**Target script**: `01_BUSINESSES/Everlight_Ventures/AI_Consulting/pipeline/prospect_scraper.py`
**Decision gate**: Lucrex approval required before any code changes deploy.

---

## TL;DR

The current scraper is simpler and already-deployed using Google Maps Places API. The video uses a more elaborate Claude-Code-as-orchestrator + Apify stack designed for an agency serving multiple clients. We should **port 3 of the video's patterns** (quality gate, ICP config, Apify as a second lane) but **reject the Claude-Code wrapper** (added complexity for no benefit since we're a single-client operation).

## Side-by-side

| Dimension | Current scraper | Video's pattern |
|---|---|---|
| Orchestration layer | Plain Python CLI | Claude Code + 2-layer architecture |
| Data source | Google Maps Places API | Apify actors ($29/mo) |
| Output sink | Django broker_ops API, direct | Google Sheets |
| Multi-tenant | No (Everlight-only) | Yes (per-client folders) |
| ICP definition | Hardcoded VERTICALS dict | YAML per-client-per-ICP |
| Quality gate | None (scrapes, emits, done) | Test run 50 -> Claude audits -> scale |
| Enrichment | contact_enrichment module | Extra post-scrape Claude call |
| Cost floor | ~$0 (Places API free tier) | $29/mo Apify + Claude tokens |

## What to port (3 items)

### Port 1: Pre-scrape quality gate
The video runs a test batch of 50, asks Claude to audit quality ("filters captured mostly right industries but company size is skewing large"), then auto-tightens filters before scaling. This is the highest-impact missing piece in our scraper.

**Implementation**: add a `--test-batch N` flag. After the test batch, Haiku reads the results, rates industry-fit + size-fit, and either proceeds or adjusts filter parameters. Low LLM cost (under 2c per audit).

### Port 2: ICP YAML config per vertical
Move the hardcoded `VERTICALS` dict into `pipeline/icp/<vertical>.yaml` files. Each YAML specifies:
- Google Places search queries
- Apify actor + filters (if used)
- Target employee count range
- Target revenue proxy (Places reviews + ratings heuristic)
- Tone for Piper's outreach draft

This makes it trivial for Lucrex to add new verticals without touching Python.

### Port 3: Apify as a secondary lane
Google Places is great for location-based SMBs. Apify opens up LinkedIn / Instagram / TikTok / Facebook Ads library scrapes that Places cannot reach. Add `--source apify --actor <slug>` as an alternative path. Keep Google Places as default.

**Cost gate**: Apify is $29/mo. Before enabling, Cash confirms a 2-month trial budget and Piper commits to filling at least 1 vertical not reachable via Google Places.

## What to reject (1 item)

### Reject: Claude Code orchestration wrapper
The video's "two-layer architecture" (Claude Code reads YAMLs, writes scripts, executes Python) is a general-purpose autonomous agent wrapper for non-technical operators. We have Python engineers (Forge) and already-deployed scripts. Adding Claude Code as a middleman:
- Costs tokens on every scrape
- Slows each run by a factor of 5 to 10
- Adds failure modes (session expiration, mis-interpretation)
- Duplicates what the fire-team doctrine already handles

If Lucrex wants Piper to initiate scrapes by voice command, that is a different request (add to Marcus's voice handler, not to the scraper itself).

## Proposed diff

`prospect_scraper.py` gains:
```
# New flags
--test-batch N        # run N first, auto-audit with Haiku, then scale
--icp-config PATH     # load vertical config from pipeline/icp/*.yaml instead of VERTICALS dict
--source {places,apify}   # default: places
--apify-actor SLUG    # required if --source apify
```

New files to create:
- `pipeline/icp/dentist.yaml`
- `pipeline/icp/hvac.yaml`
- `pipeline/icp/agency.yaml`
- (one per vertical currently in VERTICALS dict)

New helpers:
- `pipeline/quality_gate.py` (Haiku-powered filter tightening)
- `pipeline/apify_client.py` (lightweight Apify actor runner)

Estimated scope: 4 hours Forge time. No breaking changes to existing callers.

## Risk ledger

- **Apify sign-up**: new vendor, new key to rotate. Cipher adds to credentials_map.md on approval.
- **Quality gate adds latency**: 10 to 20 extra seconds per scrape. Acceptable.
- **YAML-driven ICPs could drift from reality if not maintained**. Schedule: Piper reviews quarterly.

## Decision needed from Lucrex

1. Approve Port 1 (quality gate) now? (no new cost, under 2c per scrape)
2. Approve Port 2 (ICP YAMLs) now? (no cost, easier for you to tune)
3. Approve Port 3 (Apify) with $29/mo budget + 2-month trial? (or reject)
4. Confirm Reject of Claude Code wrapper.

Reply in thread on the `#ft-consult` Slack post (auto-posted with this audit) or say `"approve scraper audit ports 1 and 2, hold on 3"` in terminal.
