---
name: default_shift_check
description: Reflex skill. Before any non-trivial task, ask "can AI/automation do this?" Forces auto-dispatch instead of solo execution.
---

When to use:
- Every user request that takes > 5 min of human work.

Three-question gate:
1. Can a named Hive agent own this? (If yes -> dispatch, don't write solo.)
2. Can a cron / boot script make this recur? (If yes -> wire it now, don't promise it.)
3. Is the SAME source of truth used in 2+ places? (If yes -> central it through one chokepoint, don't fork it.)

Anti-patterns this skill blocks:
- "Let me just do it manually this once" -- if it'll repeat, build the recurrence in the same turn.
- "I'll add a script later" -- later is a fiction. Build it now or admit it won't ship.
- "I'll just write it in Slack" -- if it's a decision worth making, it's worth writing to a file or thread first (Comms Doctrine: written-first).

Output contract:
- State which of the three gates fired.
- If gate 1 fires, name the agent + dispatch in the same response.
- If gate 2 fires, name the cron/boot file path + edit in the same response.
- If gate 3 fires, name the single chokepoint module + refactor pointer.
