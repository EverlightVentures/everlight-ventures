---
name: karpathy_rag_intake
description: Three-tier knowledge discipline (raw -> wiki -> output) for ingesting source material into the Hive memory layer.
---

When to use:
- Any new transcript, PDF, article, research note, or video summary lands in the workspace.
- A wiki page hasn't produced a real artifact in 90 days (audit trigger).

Three tiers (lives at `06_DEVELOPMENT/everlight_os/knowledge/`):

- `raw/`  Original source. Copy-pasted, never edited. Filename pattern: `<YYYY-MM-DD>_<topic>_<source>.<ext>`.
- `wiki/` Distilled summary. One HTML or markdown per source. Pulls the 3-5 actionable patterns out. Cross-links other wiki pages.
- `output/` Real artifacts produced from the wiki: skill files, agent firmware updates, dashboard widgets, Slack posts, Blinko notes. Each output cites which wiki page(s) it came from.

Promotion rules (action-based, not time-based):
1. raw -> wiki: only when the user or an agent decides to actually use it. Otherwise, raw stays raw. No premature digestion.
2. wiki -> output: only when an artifact ships somewhere (skill written, code changed, post published). If wiki sits idle 90 days, archive to `wiki/_archive/`.

Output contract for every wiki page (frontmatter):
- source: <raw filename>
- date_digested: YYYY-MM-DD
- patterns_extracted: [list]
- artifacts_produced: [list of paths] (filled as outputs ship)
- supersedes: [old wiki pages this replaces]

Cross-reference: see `wiki/INDEX.html` for the master list of digested sources.
