---
description: Ingest a day's screenshots into organized text -- group by hashtag, suggest tags for the untagged, flag duplicates. Never reads images in-process (crash-proof).
---

You are ingesting Rich's daily screenshot dump into his system.

**Why this command exists:** Rich screenshots ~25 things a day to feed into the
Hive. Reading raw images in-process can OOM/segfault the CLI on Termux. This
command exiles the image work to a subprocess that calls the vision API and
hands back TEXT. **You never Read an image here** -- you read the text digest.
That is the whole point: the fragile in-process image path is never touched.

It also organizes on the way in, per Rich's rules:
- Screenshots with **visible hashtags** -> grouped under those tags.
- Screenshots with **no hashtag** -> get content-derived `#suggested` tags.
- **Near-duplicates** (perceptual hash) -> flagged for deletion, **never auto-deleted**.

**Usage:** `$ARGUMENTS` is optional.
- No args -> newest 25 from `/mnt/sdcard/DCIM/Screenshots`.
- A folder or file path -> that source instead.
- Flags: `--batch N` (default 25), `--model sonnet|opus` (default haiku = cheapest),
  `--out DIR`.

**Steps (in order):**

1. **Run the ingest script** (it does ALL the image handling -- do not Read images yourself):

   ```bash
   python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/screenshot_ingest.py $ARGUMENTS
   ```

   Stdout gives you a text digest grouped BY HASHTAG, a NO TAG (suggested) list,
   and a POSSIBLE DUPLICATES list. Stderr ends with the artifact dir + token cost.

2. **Read the `ingest.md`** in the printed artifact dir (it's text -- safe) if you
   need the full transcriptions. Never open the `.jpg`/`.png` originals.

3. **Present the organized digest to Rich:** what came in, grouped by hashtag;
   which ones you auto-tagged and with what; and the duplicate clusters.

4. **For duplicates:** show the `delete_candidates.sh` contents and ASK before
   running it. It keeps the newest of each cluster. Only run it on Rich's explicit
   OK (Commandment VII -- Verify Before Destroy).

5. **For "implement into the system":** use the transcriptions + action_items to do
   whatever Rich asked -- log to the brain, draft follow-ups, extract data, etc.
   If he didn't say, summarize the haul and ask what to do with each tag group.
