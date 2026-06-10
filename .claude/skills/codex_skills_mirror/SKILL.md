---
name: codex_skills_mirror
description: Treat OpenAI Codex as a cross-check reviewer + specialist for iOS/Figma/Remotion. Claude stays primary executor. Pattern from Riley Brown's Codex guide.
---

When to use:
- Hive workflow repeated 3+ times AND spans 2+ external APIs (scrape -> score -> publish, research -> deck -> launch video).
- Shipping a new SaaS product needing 6-deliverable bundle (iOS / web / landing / deck / launch-video / social automation).

NOT for:
- One-off tasks
- Single-API calls
- Anything Claude already does well (Python, branded comms, agent firmware writing)

Procedure:
1. List the recipe: every API + agent + output artifact in order. If under 3 steps, it's a script not a skill -- exit.
2. Create `.claude/skills/<skill_name>/SKILL.md` with frontmatter (trigger, inputs, outputs, agents, mcp_tools).
3. Map Codex Skills -> Claude agent files. Map Codex Plugins -> existing MCP servers (broker-os, blinko-memory, market-intel, Gmail, Slack, Calendar). NEVER build a new MCP if a plugin-equivalent already exists.
4. For SaaS launches, bolt on `remotion_launch_video` skill: takes product name + 3 bullets, renders 30s MP4 to `09_DASHBOARD/reports/launch_videos/`. The one Codex feature worth copying immediately.
5. Register the skill in `06_DEVELOPMENT/everlight_os/hive_mind/roster.yaml` under `skills:` and assign a TL agent who owns failures.
6. Log first 3 invocations to Blinko `#hive/skill/<name>`. Promote to production only if all 3 succeed.

Codex / Claude split (no duplication):
- **Codex** = iOS/Swift code (Claude is weaker), Figma plugin work, Remotion video composition.
- **Claude** = named-agent personality writing (Piper's drawl etc.), wholesale/broker domain logic, all branded comms final renders, XLM trading decisions.
- **Cross-check pattern**: `clx_delegate.py --mode review` runs both ways before ship.
- **Hand-off**: Claude plans + writes + brands. Codex compiles iOS / renders video / lints Figma.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/01_Claude_and_Codex/openai_codex_complete_guide.md
Owner: Forge.
