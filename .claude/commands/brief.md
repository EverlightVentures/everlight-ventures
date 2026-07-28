---
description: Load the session-start briefing before doing anything. The read counterpart to /exit -- pulls the last handoffs, the decision reasoning, hot punchlist items and live repo state.
---

You are starting a session. `/exit` writes a handoff at the end of every session;
this loads it back. Run this **before** answering questions, exploring the
codebase, or touching files.

**Steps:**

1. **Assemble the briefing:**

   ```bash
   python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/session_brief.py
   ```

   Flags: `--sessions N` (default 3), `--decisions N` (default 5), `--json`.

2. **Act on the stale-lock warning immediately if it fires.** The briefing checks
   for `.git/index.lock`. If it reports one, check `ps` for a live git process
   first. If none is running, the lock is stale and **every commit is failing
   silently**. This exact failure cost 16 days in July 2026 and stranded 2,201
   files. Clear it before doing anything else.

3. **Read the decision entries, not just the session summaries.** The mailbox
   says what happened. The decision log says why a fork went the way it did. When
   the current task touches a logged decision, follow the recorded reasoning or
   explicitly say you are overriding it and why.

4. **Treat everything in the briefing as a claim, not a fact.** It is assembled
   from files that may be stale. Per `feedback_verify_source_of_truth` and
   `feedback_pull_live_ops_data`, verify anything load-bearing against the live
   system before acting on it. A punchlist item marked done in May is not
   evidence it still works in July.

5. **Report to Rich in three lines or fewer:** where the repo stands, what the
   last session left open, and what looks most urgent. Do not paste the raw
   briefing at him unless he asks. Then ask what he wants to work on, or if the
   last session named a clear next step, propose that.

**Why this exists:** the handoff used to be write-only. `/exit` exported to
`_state/AGENT_MAILBOX.md` and nothing ever read it, so every session started
blank while a 4,000-line handoff file sat unused on disk. Continuity here is not
a memory problem, it is a rehydration problem. This is the rehydration half.
