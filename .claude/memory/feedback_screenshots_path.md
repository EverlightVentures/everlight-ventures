---
name: Screenshots location
description: User screenshots are always at /mnt/sdcard/DCIM/Screenshots/ (internal storage), but do not auto-open image files directly on this ARM device because local JPG/PNG reads can crash Claude Code.
type: feedback
---

Screenshots are always at /mnt/sdcard/DCIM/Screenshots/

**Why:** User told us to remember this. "Internal storage DCIM screenshots, same as always."

**Crash guard:** On this device, avoid using `Read` on local screenshot/image files (`.jpg`, `.jpeg`, `.png`, `.webp`) under `/mnt/sdcard/DCIM/Screenshots/` unless the user explicitly asks to risk it. Recent sessions crashed the Claude CLI immediately after local screenshot reads.

**How to apply:** When user mentions "my screenshot" or "last screenshot", identify the likely file path from `/mnt/sdcard/DCIM/Screenshots/` sorted by date, but ask for attachment/description or use a non-Claude image viewer path instead of opening the image directly in Claude.
