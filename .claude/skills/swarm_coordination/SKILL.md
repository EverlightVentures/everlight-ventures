---
name: swarm_coordination
description: Multi-agent task decomposition pattern. Orchestrator breaks a single prompt into specialist sub-tasks, merges their outputs into one deliverable. Sourced from OpenSwarm transcripts; mapped to existing Hive fire teams.
---

When to use:
- A user prompt would produce multiple distinct deliverables (deck + doc + video, research + analysis + summary).
- A task spans 2+ specialty domains (research + writing, scoring + outreach + close).
- Estimated single-agent time > 15 minutes of work.

Pattern (mirrors Marcus Cole orchestration doctrine):

1. **Orchestrator (Marcus Cole)** receives prompt. Classifies via `roster.yaml` routing_rules. Never produces final output; only dispatches + merges.
2. **Specialists fan out IN PARALLEL** (single message, multi-Agent blocks):
   - Deep Research = Cipher Wolfe / Bull Archer / researcher subagent
   - Data Analysis = Penny Vance / Chart Dawson
   - Slides / HTML deck = everlight_packager + writer
   - Docs = writer + everlight_seo_formatter
   - Image / video = (placeholder; codex_collab handles Remotion)
   - Virtual assistant tasks = brief_calloway / outreach agents
3. **Cross-check pass** (per CLAUDE.md doctrine phase 5): each specialist reviews 1-2 peer outputs. Flags conflicts.
4. **Synthesize** (one named agent, usually Marcus or the topic owner) merges into ONE canonical deliverable. Resolves conflicts, cites provenance ("Penny ran the math; Cipher pulled the on-chain data; Hammer wrote the close").
5. **Publish** through `publish_gdoc()` (HTML + Google Doc + branded Slack card).
6. **Log** the run -- Blinko + HiveArtifact rows show which agents contributed.

Anti-patterns this skill blocks:
- Solo execution on a multi-domain task ("All hands at all times" rule).
- Fan-out without a synthesize step (you get N drafts, no deliverable).
- Synthesize without cross-check (you propagate first-draft errors).

Skip cross-check + synthesize ONLY for trivial tasks (single-lane bug fix, typo). Default to full 9-phase pattern. Token cost: ~30% over solo. Worth it on stakes > $100 decisions.

Output contract:
- One merged canonical deliverable.
- Provenance line per section: which agent contributed.
- Conflicts list (resolved or flagged for Lucrex).
- Dropped recommendations (with one-line reason).
