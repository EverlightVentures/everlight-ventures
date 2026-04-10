---
name: Bot is Oracle only
description: XLM bot runs on Oracle Cloud only. Local phone copy is stale/archived. "My bot" always means Oracle.
type: feedback
---

When user says "my bot" they mean the Oracle Cloud XLM bot, never the local phone copy.

**Why:** The local xlm_bot/ directory has stale logs from Feb 28 2026. Oracle is the live production environment. Local bot should be archived and never run again.

**How to apply:** Don't check local logs for bot performance. Can't access Oracle logs from this phone without SSH/sync. If user asks about bot performance, remind them we need Oracle access or log syncing set up.
