# Grist Spike - Replacement for JSON Workbook Storage

**Owner**: Forge (2-hour time-box)
**Source**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/08_Spreadsheets_and_Ops/` + `chatgpt_for_excel_how_to_use.txt`
**Date**: 2026-04-21

---

## Current state

Wholesale workbooks live in JSON files written by `workbook_logger.py`:
- `pipeline_master.json`
- `outreach_log.json`
- `deal_tracker.json`
- `performance_metrics.json`

Plus nightly Supabase push. No versioning. No row-level permissions. No query API.

## Grist pitch

Grist (Apache-2, https://getgrist.com) is a modern open-source spreadsheet with:
- Native API (read + write rows by ID)
- Granular permissions
- Built-in formula columns
- Live collaboration
- Self-hostable OR hosted free tier

If we migrate, the AI-powered helpers (`sheets_ai_helpers.py`) get a real DB target instead of overwriting whole JSON files.

## Spike plan (2 hours)

1. Spin up Grist free cloud workspace at `everlightventures@grist.com`.
2. Import `pipeline_master.json` as a table.
3. Write a read + write round-trip using Grist REST API.
4. Measure: is the API-driven workflow ergonomic enough that Filter Banks could drive it from Python?
5. Write one-paragraph verdict in `06_DEVELOPMENT/everlight_os/spikes/grist_vs_jsonstate.md`.

## Decision criteria

Migrate IF:
- API write latency under 500 ms
- Free tier covers our volume (10K rows per doc x 5 docs)
- Row-level permissions work (to let clients see their own wholesale pipeline slice once we add buyers)

Stay with JSON IF:
- None of the above clearly wins
- Our current $0 / all-local setup is already "good enough"

## Risk

Low. Spike is read-only through step 4. No data migrated.

## Status

Not started. 2-hour spike queued for Forge's next window.

## Resume

`start grist spike` triggers.
