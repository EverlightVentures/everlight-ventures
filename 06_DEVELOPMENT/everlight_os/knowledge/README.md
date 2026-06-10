# Everlight Knowledge Layer

Karpathy-style RAG memory for the Hive. Three tiers, action-based promotion.

## Layout

- `raw/` -- original source material (transcripts, PDFs, articles). Never edit. Filename: `<YYYY-MM-DD>_<topic>_<source>.<ext>`.
- `wiki/` -- digested summaries. One HTML or markdown per source. Each has frontmatter listing `source` + `patterns_extracted` + `artifacts_produced`.
- `output/` -- artifacts produced FROM the wiki (skill files, agent firmware updates, dashboard widgets, Slack posts, code changes). Each cites which wiki page it came from.

## Promotion rules

1. **raw -> wiki**: only when an agent or Marquise decides to actually use the source. No premature digestion.
2. **wiki -> output**: only when something ships (skill written, code changed, post published).
3. If a wiki page sits idle 90 days with no output, archive to `wiki/_archive/`.

## Skill

Use the `karpathy_rag_intake` skill (lives at `.claude/skills/karpathy_rag_intake/SKILL.md`) for the canonical procedure.

## Index

See `wiki/INDEX.html` for the master list of digested sources and the artifacts they produced.
