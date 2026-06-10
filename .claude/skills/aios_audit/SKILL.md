---
name: aios_audit
description: Audit the Hive against the AIOS Four C's (Context, Connections, Capabilities, Cadence). Surfaces gaps. Sourced from Build & Sell Claude transcript.
---

When to use:
- Quarterly review (Feb 1 / May 1 / Aug 1 / Nov 1).
- Any time a new tool / SaaS / model is being evaluated for the stack.
- After a 3+ day Hive outage or doctrinal drift report.

Four C's checklist:

1. **Context** -- what does Claude know about the user and the work?
   - CLAUDE.md present and current (root + project)?
   - MEMORY.md index <= 200 lines?
   - Agent firmware files have voice + relationships sections?
   - Last 7 days of session logs present in Blinko?
   - GAP if any answer is no.

2. **Connections** -- what live systems can Claude touch?
   - All 7 MCP servers reachable (broker-os, blinko, market-intel, Gmail, Slack, Calendar, supabase)?
   - Tailscale mesh up across phone + Oracle + AceMagician PC?
   - Branded comms layer functional (`branded_mailer`, `branded_slack`, `n8n_replacements.publish_gdoc`)?
   - GAP if any connection is dead > 24h.

3. **Capabilities** -- what named skills / agents / commands can fire?
   - .claude/skills/ count vs last audit (growing, not shrinking)?
   - 94 agents firmware files load cleanly (no syntax errors in YAML frontmatter)?
   - .claude/commands/ matches doctrinal modes (plan/execute/review)?
   - GAP if any skill exists in wiki/ but not skills/.

4. **Cadence** -- how often does the system act on its own?
   - Oracle crons firing (CEO brief 7AM PT, hourly pulse, log rotation)?
   - deploy_to_oracle 10-min loop healthy?
   - claude_sync_acemagician boot+cron trigger working?
   - GAP if any expected schedule had 0 runs in last 24h.

Output contract:
- One row per C, status GREEN/AMBER/RED with the specific gap.
- For every RED, dispatch a fix in the same turn (per self-healing rule).
- File the audit at `06_DEVELOPMENT/everlight_os/audits/aios_<YYYY-MM-DD>.html`.
