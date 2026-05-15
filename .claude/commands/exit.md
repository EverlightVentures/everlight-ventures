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

The script automatically queues a `file_replace` to peers via sync_queue,
so the updated mailbox propagates to e5-mother + AceMagician on the next
drain cycle.
