# Project BMO - Self-Improving Agent Research

**Origin**: Hive Mind session 2c819143 (2026-02-27)
**Source**: ngrok newsletter + Gemini specialist 23_automation_architect
**Status**: Research / Planning

---

## What is BMO?

BMO is a self-improving coding agent documented by the ngrok team. Key properties:

- Runs autonomously on coding tasks for extended periods
- Maintains a running "memory" of what it has learned
- Modifies its own operational heuristics ("changes its own batteries")
- Tracked through telemetry: attention, vigilance, task drift metrics

The ngrok author used BMO exclusively for 2 weeks and measured:
- Where attention degrades (long context, repetitive tasks)
- Vigilance patterns (when does it stop checking its own output?)
- Agentic harness gaps (what scaffolding it still needs)

---

## Everlight Relevance

The Hive Mind already has a self-referential loop:
1. Specialists deliberate on a query
2. Claude executes based on deliberation
3. Execution report feeds back into the war room

What BMO adds is a VERTICAL feedback loop:
- Agents track their own performance over time
- Low-performing specialists get retrained or deprioritized
- High-performing patterns get codified into persona briefings

---

## Proposed Architecture for Everlight BMO

### Phase 1 - Telemetry (low risk, high value)
Track per-specialist metrics in each session:
```
hive_mind/telemetry.jsonl
{
  "session": "2c819143",
  "specialist": "03_engineering_foreman",
  "manager": "codex",
  "response_quality": 0.85,  // human or auto-scored
  "task_category": "engineering",
  "tokens_used": 1240,
  "cited_sources": 0,
  "implemented": true,       // did Claude act on this?
  "outcome": "success"
}
```

### Phase 2 - Roster Feedback
Use telemetry to weight specialists:
- `roster.yaml` gains a `performance_weight` field per specialist
- Dispatcher routes higher-weight specialists first
- Low performers flagged for persona briefing review

### Phase 3 - Persona Drift Detection
Before each session, compare current persona briefing vs last 10 session outcomes:
- If specialist keeps missing a category, add a focus note to their briefing
- If specialist is consistent, mark them as "anchored" (skip refresh)

### Phase 4 - Controlled Self-Modification (GATED)
Allow specialists to propose changes to their own briefings.
HARD CONSTRAINTS:
- All proposed changes go to `07_STAGING/pending_persona_changes/`
- No change applied without human approval
- Rollback: keep last 3 versions of each persona briefing

---

## Risk Flags (from automation_architect)

1. **Role confusion**: If an agent modifies its own briefing mid-session, other agents
   in the same session get inconsistent behavior. Mitigation: changes only apply
   to the NEXT session, never the current one.

2. **Feedback loops**: Self-improvement that optimizes for "getting implemented"
   rather than "correct output" is a misalignment risk. Telemetry must measure
   real outcomes (bot performance, revenue, shipped code), not agent confidence.

3. **Persona pollution**: Over-specialized agents become brittle. Keep a "vanilla"
   fallback version of each persona briefing.

---

## Files to Create

```
everlight_os/
  hive_mind/
    telemetry.py          # write/read session telemetry
    telemetry.jsonl       # persistent log
    roster_feedback.py    # weight specialists by performance
  07_STAGING/
    pending_persona_changes/   # gated persona update proposals
```

---

## Next Step

Before writing any code:
1. Confirm with Rich that Phase 1 (telemetry only) is OK to implement
2. Define what "outcome" means for each task category
3. Review the ngrok bmo article for specific attention/vigilance metrics

Reference: https://ngrok.com/blog/bmo (see original ngrok newsletter)
