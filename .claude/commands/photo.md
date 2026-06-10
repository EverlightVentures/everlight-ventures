---
description: Prep a photo or folder for safe viewing (auto-resize to avoid OOM crash on phone). Pass --full for pixel-perfect quality.
---

You are about to view a photo (or batch of photos) without crashing.

**Why this command exists:** Z Fold 7 photos are 2-6 MB JPEGs. Base64-encoding
them into the model context can OOM the Claude CLI on Termux. This command
shrinks them first to a safe size (<=1600px, q85, ~300 KB) before you Read.

**Usage:** `$ARGUMENTS` is the path Rich gave you. It is one of:

- A single photo file: `/sdcard/DCIM/Camera/20250921_104725.jpg`
- A folder of photos: `/sdcard/DCIM/Camera` (processes up to 5 newest by default)
- Same paths with optional flags: `--full` (skip resize, pixel-perfect),
  `--batch N` (override the 5-photo cap), `--max-edge N`, `--quality N`

**Steps (in order):**

1. **Run the prep script:**

   ```bash
   python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/claude_photo_prep.py $ARGUMENTS
   ```

   Stdout will contain one or more `PATH: /tmp/claude_photos/<file>.jpg` lines.
   Stderr has a human summary (mode, originals -> resized sizes).

2. **Read each `PATH:` output** using the Read tool. Those paths live in
   `/tmp/claude_photos/` which is allowed by your permissions.

3. **Describe what Rich asked you to do with the photos** -- OCR, summarize,
   compare, extract data, identify objects, whatever the surrounding chat
   message asked for. If Rich did not give a specific task, briefly describe
   each photo and ask what he wants to do with them.

4. **Mention the mode** at the top of your response so Rich knows whether
   he got resized or full-quality views. Example: "Read 3 photos (resized
   for safety). [...]" or "Read 1 photo at full quality. [...]"

**If the script fails:**

- "not found" -> Rich gave a bad path. Show him what the path was, ask for the right one.
- "no photo files in <dir>" -> the folder has no image files. List what is in there.
- Any other error -> surface the stderr verbatim, don't paper over it.

**Trade-offs to mention if Rich asks why his photos look small:**
The default mode trades pixel detail for not-crashing. If he needs full
fidelity (color matching, fine print, brand asset comparison), tell him
to re-run with `--full`. The pass-through mode copies the original
unchanged and may still crash on very large photos -- that is the trade-off.
