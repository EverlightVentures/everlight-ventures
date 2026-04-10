---
description: Everlight execution command for approved plans.
argument-hint: [approved_plan_or_task]
allowed-tools: Read,Glob,Grep,Edit,MultiEdit,Write,Bash(git:*),Bash(rg:*),Bash(ls:*),Bash(python3:*)
---

Implement this approved plan/task:
$ARGUMENTS

Rules:
- Keep scope tight.
- Prefer reversible edits.
- Run minimal validation checks.
- Do not use `Read` on local image files (`.jpg`, `.jpeg`, `.png`, `.webp`) under `/mnt/sdcard/DCIM/` or `/mnt/sdcard/DCIM/Screenshots/`; ask for attachment/description instead because local image reads can crash Claude Code on this device.

Return:
1. What changed
2. Validation performed
3. Residual risks
4. Rollback commands
