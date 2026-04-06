# Everlight Master Workspace Memory

This is the top-level context for `/mnt/sdcard/AA_MY_DRIVE`.

## The Hive Mind Protocol
You are operating as part of an AI Triad (Claude, Gemini, Codex).
- **Collaboration Rules:** Read `HIVE_MIND.md`.
- **War Room:** Log handoffs and progress in `_logs/ai_war_room/`.

## Operating Style (Synergy Mode)
- **Plan before execution.**
- Keep outputs concise and actionable.
- Prefer editing files directly over long inline code blocks.
- **Default Response Shape:** Summary, Steps, Risks, Rollback.
- Use shell/tools only when needed for the task.

## Safety & Security
- Treat shell/file-destructive actions as high risk.
- **Read-first behavior** when the task is unclear.
- **Credential Protection:** Never log, print, or commit secrets.
- Cite sources when external/current information is required.

## Modes & Skill Handoffs
- **Planning only:** Switch to `.gemini/plan`.
- **Architecture walkthroughs:** Switch to `.gemini/explain`.
- **Custom Everlight Commands:**
  - `activate_skill ev_plan`: Structured planning.
  - `activate_skill ev_execute`: Scoped implementation.
  - `activate_skill ev_review`: Security/QA review.
  - `activate_skill ticket-manager`: Manage project tickets.

## Workspace Structure
- **Source of truth:** `WORKSPACE_MANIFEST.md` (updated 2026-03-06)
- ALWAYS refer to WORKSPACE_MANIFEST.md before executing file operations.
- See that file for the full Agent File Save Rules table.

## Key Project Paths
| Project | Path |
|---------|------|
| Alley Kingz | `01_BUSINESSES/Everlight_Ventures/Alley_Kingz/` |
| Books/Publishing | `01_BUSINESSES/Everlight_Ventures/Everlight_Literature/` |
| Brand/Site docs | `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/` |
| Onyx POS | `01_BUSINESSES/onyx_pos/` |
| XLM Bot | `06_DEVELOPMENT/xlm_bot/` |
| Hive Mind SaaS | `06_DEVELOPMENT/hivemind_saas/` |
| Content drafts | `02_CONTENT_FACTORY/01_Queue/` |
| Scripts | `03_AUTOMATION_CORE/01_Scripts/` |
| Reports | `09_DASHBOARD/reports/` |

## CRITICAL: File Save Rules
- NEVER save project outputs to the workspace root or random directories.
- Each project has a designated folder. See WORKSPACE_MANIFEST.md for the routing table.
- Unsorted files go to `07_STAGING/Inbox/`.

## Claude Integration
- **Skills:** Found in `.claude/skills/`, `.gemini/skills/`
- **Agents:** Found in `.claude/agents/`, `.gemini/agents/`, `.codex/agents/`
- **Modes:** `.claude/modes/`, `.gemini/plan/`, `.gemini/explain/`
