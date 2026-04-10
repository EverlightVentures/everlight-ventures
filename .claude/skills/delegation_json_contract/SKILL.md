---
name: delegation_json_contract
description: Standardize headless Claude outputs for Codex orchestration.
---

Use for delegated/headless tasks.

Required envelope:
- `goal`
- `assumptions`
- `steps`
- `risks`
- `next_commands`

Execution variant:
- `changed_files`
- `validation`
- `rollback`

Guidelines:
- Keep fields deterministic and parseable.
- Separate facts from inference.
- Keep command suggestions safe-by-default.
