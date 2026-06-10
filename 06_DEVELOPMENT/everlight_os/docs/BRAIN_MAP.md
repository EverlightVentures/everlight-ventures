# THE BRAIN -- Where Memory Lives (canonical map)

> "I don't know where the memory in the brain is." -- Rich, 2026-05-24.
> This doc answers that, permanently. The brain is not one thing. It is three layers,
> and the rule is: **the brain must be intact at all times (local-first, always-on).**

## The three layers of the brain

| Layer | What it holds | Where it physically lives | Served at | Status |
|---|---|---|---|---|
| **1. Doctrine / long-term memory** | The 236 HARD-LAW + project + feedback memory files, indexed by MEMORY.md | `/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory/*.md` | read by Claude every session | always local, never down |
| **2. RAG notes (the "vector DB")** | 619 Hive session notes, deal intel, decisions -- FTS5 text search | `_logs/blinko_lite.db` (SQLite) | `http://127.0.0.1:2700` and `:1111` (blinko-lite) | **LOCAL = UP.** Remote vector layer (e5-mother:1111) is the upgrade, down since 2026-05-15 |
| **3. Session continuity** | Every session's accomplishments, files, doctrines, open items | `_state/AGENT_MAILBOX.md` | flat file, read on resume | always local |

Plus the **offline queue** (`_logs/blinko_log_queue/`) -- writes wait here when every Blinko
endpoint is down, drained by `blinko_queue_drain.py` (cron `*/17`). A note NEVER vanishes.

## Cognition, not just storage (the tier-2 trail layer)
Raw notes alone are a pile, not a brain. Three-tier discipline (skill: karpathy_rag_intake):
- **tier 1 = raw notes** (1,665+) -- the daily `log_blinko()` writes. Storage.
- **tier 2 = TRAIL notes** (`#hive/trail`) -- cognition. `03_AUTOMATION_CORE/01_Scripts/brain_synthesize.py`
  filters noise (`--stats`), groups by theme (`--bundle <theme>`), and ingests connective
  trails (`ingest_trail`) shaped **what we KNEW -> what we KNOW now -> how it AFFECTS Deal 1**,
  linking constituent note ids so thoughts understand each other.
- **tier 3 = the decision / deliverable** -- action.
First trail (2026-05-24): "Wholesale TN -- from arsenal to first deal". Doctrine:
[[feedback_brain_synergy_trails_not_logs]]. New significant notes should link to their trail,
not sit orphaned. Run a synthesis pass per theme periodically so trails stay current.

## The always-on rule (HARD LAW, 2026-05-24)
Every brain WRITE is **local-first**: try `127.0.0.1:2700` -> `127.0.0.1:1111` -> `e5-mother:1111`,
and if all fail, drop the note in the offline queue. The old bug was code that wrote ONLY to
e5-mother (down) and silently swallowed the failure -- so the brain stopped learning on 2026-05-15
without anyone noticing. Fixed in `rex_master_pipeline.log_blinko()` on 2026-05-24. Any new
brain-writer must follow the local-first pattern or reuse `blinko_queue_drain.enqueue()`.

## How the wholesale pipeline feeds the brain
- **Pipeline -> brain:** `rex_master_pipeline.log_blinko()` and `wholesale_hive_pipeline._wb.log_to_blinko()`
  write session notes (local-first as of 2026-05-24).
- **Leads -> scoreboard:** `workbook_logger.sync_from_leads_db()` rebuilds `performance_metrics.json`
  from the real `leads_db.json` every run (wired into the pipeline report stage 2026-05-24).
- **Sessions -> brain:** `session_export_to_mailbox.py` writes `_state/AGENT_MAILBOX.md`.
  (GAP: it does not yet ALSO enqueue the session summary as a searchable Blinko note --
  next wiring task so the brain learns from every session, not just ad-hoc notes.)

## When e5-mother comes back
The remote Blinko on e5-mother is the *embedding/vector* upgrade over local FTS5. When the
tailnet returns, `blinko_queue_drain.py` flushes the local queue to it and the two reconcile.
Nothing is lost in the meantime -- local is the source, remote is the amplifier.

## One-glance health check
```bash
curl -s http://127.0.0.1:2700/health        # local brain (should be 200)
python3 -c "import sqlite3;print(sqlite3.connect('_logs/blinko_lite.db').execute('SELECT COUNT(*) FROM notes').fetchone()[0],'notes')"
ls _logs/blinko_log_queue/*.md 2>/dev/null | wc -l   # offline backlog (0 = drained)
```

*Maintained by Lucrex. Reread when anyone asks "where is the memory."*
