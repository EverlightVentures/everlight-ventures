# Claude + Codex Orchestration

This workspace now includes a structured Claude delegation command:

```bash
clx --mode execute "your task"
```

## Modes

- `execute`: `--permission-mode acceptEdits`
- `plan`: `--permission-mode plan`
- `review`: `--permission-mode plan` (read-only review posture)

Mode-specific prompts come from:
- `.claude/modes/execute.md`
- `.claude/modes/plan.md`
- `.claude/modes/review.md`

## JSON contract

Default output format is JSON envelope from `clx`:
- `ok`
- `mode`
- `permission_mode`
- `command` and `command_shell`
- `stdout` / `stderr`
- `parsed_output` (parsed Claude JSON or stream events)
- `log_file`

## Hooks and guardrails

Project hooks are configured in:
- `.claude/settings.json`

Hook scripts:
- `.claude/hooks/pre_tool_guard.py`
- `.claude/hooks/log_tool_use.py`

Logs:
- `_logs/claude_hooks/pretool.jsonl`
- `_logs/claude_hooks/posttool.jsonl`
- `_logs/claude_delegate/history.jsonl`

## Commands

```bash
# Headless delegation (Codex -> Claude)
clx --mode plan "Analyze repo and propose implementation plan"
clx --mode review --output-format text "Review xlm_bot risk logic for regressions"
clx --mode execute "Implement approved change and summarize rollback"

# Interactive mode sessions
claude-mode execute
claude-mode plan
claude-mode review
```

## Slash commands and skills

Project commands:
- `/ev-plan`
- `/ev-execute`
- `/ev-review`

Project skills:
- `plan_execute_verify`
- `everlight_copy_guard`
- `delegation_json_contract`
