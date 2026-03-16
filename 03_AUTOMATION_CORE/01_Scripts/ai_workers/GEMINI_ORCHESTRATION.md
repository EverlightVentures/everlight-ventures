# Gemini + Codex Orchestration

This workspace now includes a structured Gemini delegation command:

```bash
gmx --mode execute "your task"
```

## Modes

- `execute`: runs in workspace root with `auto_edit` approval mode.
- `plan`: runs in `.gemini/plan` with `plan` approval mode (read-only planning).
- `explain`: runs in `.gemini/explain` with `plan` approval mode (architecture/explain focus).

## JSON contract

Default output is JSON envelope with:
- `ok`
- `mode`
- `approval_mode`
- `command` and `command_shell`
- `stdout` / `stderr`
- `parsed_output` (parsed Gemini JSON when available)
- `log_file` (if logging enabled)

## Logging

Delegation logs are written to:
- `_logs/gemini_delegate/<timestamp>_<mode>.json`
- `_logs/gemini_delegate/history.jsonl`

## Commands

```bash
# Headless delegation (recommended for orchestration)
gmx --mode plan "Propose a migration strategy for xlm_bot"
gmx --mode explain --output-format text "Explain main.py order execution path"
gmx --mode execute "Implement and test change Y"

# Interactive mode sessions
gem-mode execute
gem-mode plan
gem-mode explain
```

## Memory files

- `GEMINI.md` (workspace root)
- `.gemini/GEMINI.md` (core doctrine)
- `.gemini/plan/GEMINI.md` (planning-only behavior)
- `.gemini/explain/GEMINI.md` (explanation-first behavior)

Inside Gemini interactive sessions:
- `/memory list`
- `/memory show`
- `/memory refresh`
- `/stats` or `/stats tools`
