---
description: Export this chat session's work to AGENT_MAILBOX.md before ending. Per HARD LAW feedback-exit-exports-session-to-mailbox.
---

You are about to end this chat session. Per HARD LAW
**feedback-exit-exports-session-to-mailbox**, you MUST first export
the session's work to `_state/AGENT_MAILBOX.md` so any agent on any
device can catch up by reading the mailbox.

**Steps (in order):**

1. **Compose a session summary** in markdown. Format:

   ```
   # <one-line title naming the main accomplishment>

   ### Accomplished
   - <bullet 1>
   - <bullet 2>
   - ...

   ### Files created or modified
   - `path/to/file.py` -- one-line purpose
   - ...

   ### Doctrines added or changed
   - `feedback_<name>` -- one-line summary
   - ...

   ### Commits + pushes
   - `<sha>` on `<branch>` -- one-line message
   - ...

   ### Open items / handoffs / queued for next session
   - <item 1>
   - ...

   ### Honest gaps / known limitations
   - <gap 1>
   - ...

   ### Operator decisions deferred
   - <decision 1>
   - ...
   ```

   Use real session details. Don't invent. Skip empty sections.

2. **Pipe the summary** to the appender:

   ```bash
   echo "<your composed markdown>" | \
     python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/session_export_to_mailbox.py
   ```

   Or write to a temp file first if the markdown contains tricky shell
   characters:

   ```bash
   cat > /tmp/session.md <<'EOF'
   <your composed markdown>
   EOF
   python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/session_export_to_mailbox.py \
     --file /tmp/session.md
   rm /tmp/session.md
   ```

3. **Verify the JSON response** has `"ok": true`. If not, surface the error.

4. **Confirm to Rich:** "Session exported to AGENT_MAILBOX
   (`<derived-title>`, `<bytes>` bytes appended). Safe to exit."

5. **Append any decisions to the decision log.** The mailbox records what
   happened. `_state/DECISION_LOG.md` records *why* a fork went the way it did,
   which is the only part that cannot be reconstructed by reading the repo later.

   Log an entry for every choice in this session where a reasonable person could
   have chosen differently. Skip mechanical steps. Use exactly this header shape,
   because `session_brief.py` parses it:

   ```
   ## [YYYY-MM-DD HH:MM PT] Short decision name

   **Context:** what forced a choice
   **Options:** A / B / C
   **Chose:** what was taken
   **Why:** the actual reasoning, in plain language
   **Gave up:** what the other option would have bought
   **Revisit when:** the condition that should reopen this
   ```

   Only `**Why:**` is mandatory. Append, never edit past entries. If a prior
   decision got reversed this session, write a new entry saying so.

   If the session made no real decisions, say so and skip. An empty log is
   honest; a padded one is noise.

6. **Confirm both writes to Rich**, then note that `/brief` will load them at the
   start of the next session.

The script automatically queues a `file_replace` to peers via sync_queue,
so the updated mailbox propagates to e5-mother + AceMagician on the next
drain cycle.
