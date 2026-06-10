# Ready-to-Use Orchestration Prompts

Copy-paste templates for deploying the 10-habit doctrine across Slack, n8n, and Claude CLI. Every prompt assumes the multi-AI stack (`ask_router.py`, named agents, MCP tools) is already wired.

---

## Claude CLI (terminal in this workspace)

### Dispatch the hive (multi-AI fan-out)
```
Dispatch the hive on this: [TASK].
Launch in parallel: 3 named Everlight agents appropriate to the domain, one Codex review
via clx_delegate --mode review, one Gemini perspective via gemx_delegate --mode explain,
one Perplexity research sweep if market-facing. Converge the findings. Post the decision
to #war-room via hive_3format.py with a branded Google Doc.
```

### Plan first, two AIs review, then build
```
Enter plan mode. Build the full plan for [TASK] using Explore subagents.
When the plan is ready, spawn two concurrent reviewers:
  - researcher subagent for external best-practice gaps
  - Plan subagent for architectural holes
Only after both approve do we ExitPlanMode and execute.
```

### Parallel subagents for independent sub-tasks
```
Use subagents. Split [TASK] into independent lanes and launch them in a single message
so they run concurrently. When they all return, converge and report.
```

### Paste an error, say fix
```
[paste traceback or error]
Fix.
```

### Grill me / prove it works
```
Grill me on the changes I just made. Don't finalize anything until I pass your test.
Specifically: red-team production failure modes, compare old vs new for behavioral diff,
and flag any test I should have written but didn't.
```

### Save as skill
```
We do [REPEATED TASK] daily. Save it as a slash command at
.claude/commands/<name>.md with the prompt, required tools, and a short description.
```

### Live data only
```
Pull live from Supabase / Blinko / broker-os MCP. Do not summarize cached state.
If the data isn't fresh, refetch.
```

---

## Slack (#war-room, #ceo-brief, #ft-* channels)

### Kickoff a hive dispatch
```
@lucrex dispatch:
task: [ONE-LINE TASK]
stakes: [low|med|high]
domains: [wholesale|trading|content|engineering|broker|research]
deadline: [when]
```
n8n webhook picks this up, routes to the appropriate fire team, posts the branded Google Doc back to the same thread.

### Quick second-opinion request
```
@lucrex second-opinion: [link to doc or PR]
Use Codex + Gemini + Perplexity. 300-word summary back to this thread. Flag any disagreement.
```

### Daily pipeline pulse
```
@lucrex pulse: wholesale
```
Returns the 3-format report (Google Doc + HTML + Slack summary) built from live Supabase + Blinko data.

---

## n8n (workflow scaffolds)

### Hive Fan-Out Workflow (JSON-in, JSON-out)
```
Trigger: Webhook -- POST body { "task": "...", "stakes": "high", "domains": ["wholesale"] }
Node 1: Switch on stakes. If high, fan out to 4 HTTP request nodes in parallel:
   - clx_delegate (Claude review mode)
   - gemx_delegate (Gemini explain mode)
   - ppx_terminal (Perplexity)
   - task-tool-invoke (named agents list from domains lookup)
Node 2: Wait-for-all aggregator.
Node 3: Merge + diff -- flag disagreements.
Node 4: Claude converge node (clx_delegate --mode execute) writes the final decision.
Node 5: gdocs_bridge.publish_report -- branded Google Doc.
Node 6: Slack post to #war-room with thread link + GDoc link.
Node 7: Log to Blinko via /api/v1/note/upsert.
```

### Skill Promotion Workflow
```
Trigger: cron daily @ 11:59 PT
Node 1: scan last 24h of Claude CLI transcripts (from /home/opc/hive_reports/transcripts)
Node 2: clx_delegate --mode review -- identify any task done 2+ times that isn't a slash command
Node 3: Draft slash command content
Node 4: Post draft to #ops channel with "approve as skill?" buttons
Node 5: On approve, write to .claude/commands/ + git commit + deploy to Oracle
```

### Voice-to-Dispatch Pipeline
```
Trigger: hive-voice.service on Oracle E5 (port 8200) -- Marcus's phone number receives a call
Node 1: Speech-to-text
Node 2: clx_delegate --mode plan -- classify task + domains + stakes
Node 3: Same fan-out workflow as "Hive Fan-Out"
Node 4: Text-to-speech summary back to the caller
```

---

## The Three Test Prompts (from the guru's playbook)

Copy these into any Claude session when working on something important:

**Plan + review:**
```
Enter plan mode. Build the plan. When done, open a second subagent to review it like a
senior employee auditing the plan for risks and gaps. Only proceed to ExitPlanMode if
both agree.
```

**Grill:**
```
Grill me on these changes. Do not finalize anything until I pass your test. Specifically:
1. What are 3 ways this fails in production?
2. What tests are missing?
3. What invariants did I accidentally break?
```

**Prove it works:**
```
Prove this actually works. Compare the old version to the new: what behaviors changed,
what stayed the same, what regressed. Run any existing tests and report the diff.
```

---

## The Golden Rule

Rich writes it once. Rich reviews it. The AIs (all of them, in parallel) build it, review it, grill it, and ship it. The more minds on each decision, the better the decision. CarMax didn't outcompete Mike's Used Cars by being smarter -- it outcompeted by having a system where mistakes were caught BEFORE the customer saw them.

That is Everlight. That is Lucrex. Seven minds, one decision, zero surprises.
