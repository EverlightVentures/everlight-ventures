---
description: Everlight planning command (read-only plan output).
argument-hint: [task]
allowed-tools: Read,Glob,Grep,WebSearch,WebFetch
---

Use plan mode behavior.

Task: $ARGUMENTS

Safety rule for this device:
- Do not use `Read` on local image files (`.jpg`, `.jpeg`, `.png`, `.webp`) under `/mnt/sdcard/DCIM/` or `/mnt/sdcard/DCIM/Screenshots/`. Local image reads have recently crashed Claude Code on this ARM device.
- If screenshot context is needed, ask the user to attach the screenshot, describe it, or provide the path for external/manual inspection without opening the image directly in Claude.

Return exactly:
1. Goal
2. Constraints and assumptions
3. Step-by-step plan
4. Risks and rollback
5. Next commands to run
