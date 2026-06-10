---
name: docstring_discipline
description: Minimal-but-complete code documentation. Naming + structure beats heavy docstrings. From Arjan ("How to Document Like a Pro") + Christian ("Writing Technical Documentation").
---

When to use:
- Writing or reviewing any Python module, class, or function in this workspace.
- Building shared modules under `content_tools/`, `06_DEVELOPMENT/everlight_os/`, `03_AUTOMATION_CORE/01_Scripts/`.

The hierarchy (do these IN ORDER):

1. **Naming first.** A function named `_compute_score_inner_v2` documents nothing. Rename it (`score_lead_against_buyer_criteria`) and you can delete most comments. Same for variables. Same for classes.

2. **Type hints second.** Every function in shared modules has signature types. Use `from __future__ import annotations` for forward refs, or `Self` (Py 3.11+). Run `pyright --strict` on `content_tools/`. Type errors block merge.

3. **Docstrings third, sparingly.** ONLY where naming + types can't tell the story:
   - Module-level: 1-2 lines on what the module is for.
   - Public-API functions: 1 line + Args + Returns + Raises (NumPy style).
   - Private functions / one-liners: NO docstring. Naming carries it.
   - DO NOT generate docstrings just because Copilot offers; they bulk the file without adding signal.

4. **Comments fourth, only for WHY.** Never for WHAT (the code says what). Use comments for:
   - Hidden constraints ("Coinbase rate-limits to 10rps")
   - Subtle invariants ("must run before deploy_to_oracle picks up the file")
   - Workarounds for bugs ("Resend API returns 200 even on bounce; check audit log")
   - Behavior that would surprise a reader

5. **mkdocs / sphinx ONLY for libraries others consume.** For internal Hive code, READMEs in the directory are enough. Don't build a docs site for code only Lucrex reads.

Anti-patterns this skill blocks:
- Docstrings restating function signature in English.
- Comments explaining `i += 1`.
- Docs as a substitute for renaming a bad function.
- "TODO: add docs" left in committed code (either add or delete).

Hive-specific:
- All `content_tools/` modules: full type hints + module docstring.
- Agent firmware files (`.claude/agents/*.md`) ARE the documentation for that agent's behavior; no separate docstring.
- Skill files (`.claude/skills/*/SKILL.md`) are the documentation for skills; no separate doc page.

Source:
- 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/Claude Code Desktop/Default_medium_How to Document Your Code Like_*.txt
- 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/Claude Code Desktop/Default_medium_Writing technical documentatio_*.txt
- 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/Claude Code Desktop/Default_medium_Documentation Best Practices_*.txt
