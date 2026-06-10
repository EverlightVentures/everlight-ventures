# File-over-AI Audit

**Owner**: Cipher + Marcus
**Source**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/06_Knowledge_Management/any_model_any_app_ai_os_nick_milo.txt`
**Date**: 2026-04-21

---

## Principle

Nick Milo's "File over AI" = your knowledge must live in files you own, not locked in an AI tool. If the tool dies, your knowledge survives.

## Everlight audit

| Knowledge store | Owner | Portability | Backup | Verdict |
|---|---|---|---|---|
| Blinko (3,301 notes) | Oracle E5 | Exported nightly to markdown via `blinko_mirror.sh` (shipped) | 30d daily + 12mo monthly in `hive_reports/blinko_mirror/` | PASS |
| Memory MD files | Phone + git | Plain markdown | In git + phone sdcard | PASS |
| Wholesale workbooks | Oracle + Supabase | JSON + Supabase rows | Nightly Supabase backup + git commit of JSON state | PASS |
| Slack channels | Slack cloud | Export available (manual) | NOT auto-backed-up | GAP |
| Google Docs (via gdocs_bridge) | Google Drive | Owner = Everlight Gmail | Google's redundancy + 30-day trash | PASS |
| Django DB (hive.db + Supabase) | Oracle + Supabase | Exportable | Daily via `rotate_logs.py` + Supabase backups | PASS |
| XLM bot decisions.jsonl | Oracle | Raw JSONL file | Rotated via `rotate_logs.py`, archived to `memory_pipeline` | PASS |
| Agent .md files (roster + identity) | Phone + git | Plain markdown | In git | PASS |
| Claude Code conversation transcripts | Anthropic cloud | NOT currently saved locally | Missing | GAP |

## Gaps to close

### Gap 1: Slack channel export

Slack Free/Pro plans support "Export" (public channels only). We should:
- Monthly cron: `slack-export` via the Slack Export API
- Save exports to `08_BACKUPS/slack_exports/YYYY-MM/`
- Hash-link to Blinko

Tooling: `slackdump` open-source CLI handles public + DM exports on Pro tier.

Ticket: `08_BACKUPS/slack_exports/` directory creation + monthly cron on Oracle. Deferred to next session.

### Gap 2: Claude Code transcripts

Our biggest loss risk: long conversations like this session never persist anywhere. If the browser tab or CLI closes mid-session, the reasoning is gone.

Options:
- Manual: every N messages, ask the assistant to dump a summary to a markdown file in `_logs/sessions/`.
- Automatic: add a `SessionEnd` or `Stop` hook in `.claude/hooks/` that saves the transcript to disk.

Recommended: hook-based. File under `.claude/hooks/session_save.sh`. Runs on every session stop, reads the transcript (if exposed by Claude Code), writes to `_logs/sessions/YYYY-MM-DD_HH-MM.md`.

Research required: does Claude Code expose the transcript to `Stop` hooks? If not, the manual-dump approach + periodic "save this conversation" commands remain.

Ticket: spike hook availability in next session.

## Done state

- [x] Blinko mirror nightly (this session)
- [x] Memory MD in git (already)
- [x] Wholesale workbooks JSON + Supabase (already)
- [x] Agent .md files in git (already)
- [ ] Slack export monthly cron (next session)
- [ ] Session transcript preservation hook (next session)

## Resume

`finish file over ai audit` triggers the remaining 2 items.
