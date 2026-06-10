# Orchestration Doctrine

**The 10 Habits of a Multi-AI Operator**

This is how Lucrex (and every future Claude session on this workspace) dispatches work. The habits below are not optional -- they are the operating model.

---

## 0. Default Posture: Multi-AI, Parallel, Plan-First

Every non-trivial task routes to MULTIPLE AIs simultaneously. The Hive is not just Claude subagents -- it is Claude, Codex, Gemini, Perplexity, GPT, and the 42 named Everlight employees working concurrently. One mind is a point of failure; seven minds triangulate.

Stack:
- **Claude** (`clx_delegate.py`) -- primary reasoning, codebase ops, subagents
- **Codex** (`cx_terminal.py`) -- code generation alternate perspective
- **Gemini** (`gemx_delegate.py`) -- explain mode, long-context alternate
- **Perplexity** (`ppx_terminal.py`) -- real-time research, citations
- **GPT** (`ai_terminal.py`) -- general-purpose tiebreaker
- **Everlight agents** (`.claude/agents/*.md`) -- 63 named employees with firmware
- **MCP tools** (broker-os, blinko-memory, supabase, market-intel, Gmail, Slack) -- live data + execution

Router: `03_AUTOMATION_CORE/01_Scripts/ai_workers/ask_router.py`

---

## 1. Parallel Sessions / Parallel Subagents

One task, split into independent lanes, running concurrently.

- In-conversation: launch multiple `Agent` subagents **in a single message** (multiple tool-use blocks in one response = parallel execution).
- Cross-session: duplicate the project folder, open separate Claude sessions against each copy, merge at the end.
- Principle: if lanes have no data dependency on each other, they should never run serially.

**Rule of thumb:** any task with 2+ independent investigations spawns 2+ subagents in one message.

---

## 2. Plan First, Build Second, Second-Opinion Always

Every non-trivial task starts with `/plan` mode (read-only exploration + design). No edits until a plan exists.

Then a SECOND AI reviews the plan before execution:
- `ask --gm "review this plan for gaps and risks: <plan>"`
- `ask --cx "does this plan over-engineer?"`
- Or spawn a `Plan` subagent from inside Claude Code

Only when both primary and reviewer agree does execution begin. For stakes > $1K or anything customer-facing, get a 3rd opinion from Perplexity on whether the approach matches current best practice.

---

## 3. Live Data Over Screenshots

Never paste a screenshot when the data is pullable. Use MCP tools:
- Supabase: `mcp__supabase__execute_sql`
- Blinko RAG: `mcp__blinko-memory__blinko_query_memory`
- Broker OS state: `mcp__broker-os__broker_status`
- Market data: `mcp__market-intel__get_market_intel_state`

Pulling live means every answer is sourced at run time, which means every answer is auditable and reproducible.

---

## 4. Turn Repeated Work Into Skills / Slash Commands

Anything done more than once becomes a Claude Code skill or a slash command.

Location: `/mnt/sdcard/AA_MY_DRIVE/.claude/commands/` (project-level) or `/root/.claude/commands/` (user-level).

Examples to build (TBD):
- `/dispatch-hive <task>` -- auto-fan-out to cl + cx + gm + ppx + named agents, converge, post to Slack
- `/wholesale-daily` -- run the full L2 daily: scout + score + outreach + buyer blast
- `/compliance-check <state>` -- query state_gate + print per-channel rules
- `/deploy-oracle` -- wrap `deploy_to_oracle.sh` with pre-flight checks
- `/cleanup-session` -- run the 7-subagent cleanup pattern over recent changes

**Rule of thumb:** if Rich typed it twice in one week, Rich shouldn't type it a third time. Save it as a skill.

---

## 5. Paste Error, Say "Fix"

No step-by-step babysitting on bugs. Paste the traceback, paste the log, paste the failing test, and say `fix`. Claude reads, diagnoses, writes the patch, runs the tests. Rich reviews the diff, approves or counters.

Do NOT narrate debugging plans. Do NOT suggest "maybe try X." Just fix.

---

## 6. Make the AI Grill You

Before finalizing anything important, ask the primary AI to stress-test the work:

- `Grill me on these changes and don't finalize anything until I pass your test`
- `Prove to me this actually works -- compare the old version to the new`
- `Red-team this plan: what are the 3 ways it fails in production?`

Then run the same grill via Gemini and Codex separately. If any of the three finds a hole, fix before ship.

This is how CarMax-grade quality is built: adversarial review baked into the pipeline, not bolted on at the end.

---

## 7. Subagents for Every Sub-Task

When a task has multiple independent sub-pieces, the main Claude conversation never does all of them itself. It launches subagents.

Subagent types already wired:
- `Explore` -- codebase search (use for anything needing 3+ search queries)
- `Plan` -- architectural design review
- `researcher` -- source-backed external research
- `everlight_researcher` -- Everlight-context research with workspace awareness
- 63 named Everlight agents (Rex Blackwell, Piper Reeves, Justine Park, etc.)
- Specialty agents: `36_rex_wholesale`, `37_ace_deal_marketer`, `34_compliance_gate`, `53_derivatives_beat`, `54_geopolitical_risk`

Say `use subagents` and the main Claude splits the work, dispatches, merges.

---

## 8. Pull Data Through MCP Tools, Not Manual Queries

The MCP layer is the auth + rate-limit + log boundary for every external system. Never hit APIs directly from an ad-hoc script when an MCP tool exists.

Current MCP servers:
- `broker-os` -- offers, leads, matches, deals, commissions
- `blinko-memory` -- RAG knowledge base (500+ notes)
- `market-intel` -- trading signals
- `supabase` -- database ops + migrations + edge functions
- `Gmail`, `Google_Calendar`, `Google_Drive`, `Slack`, `n8n`

Any new external system gets wrapped in a new MCP server before the pipeline uses it.

---

## 9. Environment: Explanatory Mode + Context-Aware Status Line

Default shell setup:
- Status bar shows context %, model, branch, token usage in real time
- Output style: `explanatory` (so every code change is explained, not just shipped)
- `/fast` mode when latency matters more than deep reasoning
- Memory system at `/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory/` (always loaded)

You don't just work faster. You understand what you shipped.

---

## 10. One-Click Auto-Dispatch (Hive-Wide Fan-Out)

When Rich says "dispatch the hive" or the task classifier flags a query as HIGH-STAKES (revenue decision, legal exposure, architecture change, customer-visible), the default pattern is:

```
1. Main Claude classifies task + picks fire team
2. In ONE message, main Claude launches:
   a. 3-5 named Everlight agents via Task tool (subagent_type)
   b. Parallel Codex query (clx --mode review) for code/architecture validation
   c. Parallel Gemini query (gmx --mode explain) for alternate perspective
   d. Parallel Perplexity query (ppx) for real-time research on anything market-facing
3. Main Claude waits for all to return
4. Main Claude converges: point out disagreements, resolve via Lucrex, write the decision
5. Log to Blinko + post Google Doc + Slack summary
```

This is the "7-mind triangulation" pattern. One perspective can be wrong; seven rarely are.

---

## When NOT to Fan Out

- Trivial edits (typo, formatting, one-line change) -- one-tool is fine
- Pure lookups (read file, check status) -- one-tool is fine
- High-latency tasks where the first answer is directionally correct and the rest would just add delay

The fan-out overhead is 30-90 seconds and several dollars in API cost. Don't use it for $0.10 decisions. Use it for $100+ decisions.

---

## Measurement

Chart Dawson owns a weekly report on orchestration discipline:
- % of non-trivial tasks that used multi-AI fan-out
- Number of times the 2nd / 3rd AI caught something the primary missed (value of fan-out)
- Subagent parallelism rate (tasks with 3+ subagents launched in one message)
- Skill reuse count (how many slash commands ran this week)

Goal: 80% of high-stakes tasks fan out. Every caught-bug from a 2nd-AI review is a win we publish internally.

---

## Maintenance

- This doc is reviewed on the 1st of each month by Marcus Cole + Justine Park
- New AI tools added to the stack get their dispatch pattern documented here
- Removed tools get archived (not deleted) with a note on why
- Reference: `03_AUTOMATION_CORE/01_Scripts/ai_workers/ask_router.py` is the canonical tool list
