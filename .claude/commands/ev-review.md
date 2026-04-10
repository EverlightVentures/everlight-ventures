---
description: Everlight review command focused on bugs and regressions.
argument-hint: [scope]
allowed-tools: Read,Glob,Grep,Bash(git status:*),Bash(git diff:*)
---

Review scope:
$ARGUMENTS

Output format:
1. Findings (highest severity first)
2. Open questions/assumptions
3. Suggested fixes

Safety rule:
- Do not use `Read` on local image files (`.jpg`, `.jpeg`, `.png`, `.webp`) under `/mnt/sdcard/DCIM/` or `/mnt/sdcard/DCIM/Screenshots/`; use text descriptions or external/manual inspection instead because local image reads can crash Claude Code on this device.

If no findings:
- Explicitly state no issues found.
- List testing gaps or residual risk.
