"""
E PLURIBUS UNUM -- Specialist Activation Protocol for the Hive Mind.

Each manager activates ALL 8 specialists on their team. Every specialist
reviews the query through their domain lens and contributes their expertise.
The manager synthesizes all contributions into one unified response.

Performance weights from telemetry are injected per-specialist so the
manager knows which team members have been delivering and which need
to step up.

Out of many, one.
"""

from pathlib import Path
from typing import Dict, List, Optional

from .config import AGENT_DIR

# Performance weight cache (loaded once per dispatch, not per specialist)
_weight_cache: Optional[Dict[str, float]] = None


def _load_full_persona(agent_name: str) -> str:
    """Load the FULL persona file for a specialist -- not a summary, the whole thing."""
    path = AGENT_DIR / f"{agent_name}.md"
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        # Strip YAML frontmatter if present (between --- markers)
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2].strip()
        return text
    return f"[Specialist {agent_name} -- persona file not found]"


def _get_weight_label(weight: float) -> str:
    """Convert a 0.0-1.0 weight to a human-readable performance tier."""
    if weight >= 0.8:
        return "TOP PERFORMER"
    elif weight >= 0.6:
        return "STRONG"
    elif weight >= 0.4:
        return "AVERAGE"
    elif weight >= 0.2:
        return "DEVELOPING"
    else:
        return "NEEDS IMPROVEMENT"


def _load_weights() -> Dict[str, float]:
    """Load telemetry weights (cached per import cycle)."""
    global _weight_cache
    if _weight_cache is not None:
        return _weight_cache
    try:
        from .telemetry import get_roster_weights
        from .config import load_roster
        _weight_cache = get_roster_weights(load_roster())
    except Exception:
        _weight_cache = {}
    return _weight_cache


def _build_specialist_briefings(employees: List[str]) -> str:
    """Build full specialist activation briefings with performance weights."""
    weights = _load_weights()
    sections = []
    for i, emp in enumerate(employees, 1):
        persona = _load_full_persona(emp)
        weight = weights.get(emp, 0.5)
        tier = _get_weight_label(weight)
        perf_line = f"**Performance**: {tier} (weight: {weight})"
        sections.append(
            f"### Specialist {i}: `{emp}` | {perf_line}\n\n"
            f"{persona}"
        )
    return "\n\n---\n\n".join(sections)


def reset_weight_cache() -> None:
    """Reset the weight cache so next build picks up fresh telemetry."""
    global _weight_cache
    _weight_cache = None


def build_manager_prompt(
    manager_key: str,
    role: str,
    employees: List[str],
    user_prompt: str,
    intel_summary: str = "",
) -> str:
    """Build the full E Pluribus Unum prompt for a manager.

    Every specialist on the team is fully loaded -- their entire persona,
    mission, responsibilities, inputs, outputs, and rules. The manager
    must channel each one and show their work.
    """

    specialist_briefings = _build_specialist_briefings(employees)

    # Intel section (from Perplexity phase 1)
    intel_section = ""
    if intel_summary:
        intel_section = (
            "## INTELLIGENCE BRIEFING (Perplexity Scout)\n\n"
            "Fresh intel gathered moments ago. Factor this into all specialist analyses.\n\n"
            f"{intel_summary}\n\n"
            "---\n"
        )

    # Peer managers for handoff coordination
    other_managers = {
        "claude": (
            "Claude (Chief Operator / Strategist) -- deep reasoning, architecture, "
            "review, final decisions. Team: chief_operator, everlight_architect, "
            "content_director, qa_gate, trading_risk, reviewer, content_strategy, editor_qa"
        ),
        "gemini": (
            "Gemini (Logistics Commander / Executor) -- implementation, automation, "
            "ops, supply chain. Team: logistics_commander, ops_deputy, workflow_builder, "
            "automation_architect, sync_coordinator, distribution_ops, analytics_auditor, packager"
        ),
        "codex": (
            "Codex (Engineering Foreman / Profit Maximizer) -- code generation, ROI, "
            "engineering, financial analysis. Team: engineering_foreman, profit_maximizer, "
            "saas_builder, saas_pm, saas_growth, funnel_architect, seo_mapper, writer"
        ),
        "perplexity": (
            "Perplexity (Intelligence Anchor / News Desk) -- real-time research, "
            "8 news beats, trend intelligence. Already provided intel above."
        ),
    }
    others = "\n".join(
        f"- {desc}" for key, desc in other_managers.items() if key != manager_key
    )

    # Build the specialist name list for quick reference
    specialist_names = ", ".join(f"`{e}`" for e in employees)

    prompt = f"""# E PLURIBUS UNUM -- Hive Mind Deliberation

You are **{role}** in the Everlight AI Hive Mind.

## CORE DIRECTIVE

You command a team of 8 specialists. You do NOT answer alone. Ever.
For this query, you MUST activate EVERY specialist on your team.
Each specialist reviews the query through their domain expertise and contributes
their unique analysis. You then synthesize all contributions into one unified response.

Your team: {specialist_names}

**E Pluribus Unum -- Out of many, one.**

## PEER MANAGERS (for cross-team handoffs)

{others}

{intel_section}

## YOUR 8 SPECIALISTS -- FULL PERSONA BRIEFINGS

Each specialist below has been activated with their **performance rating**
based on telemetry from recent sessions. TOP PERFORMERS have consistently
delivered findings and recommendations -- lean on them harder. DEVELOPING
specialists need to step up -- push them for deeper analysis.

Read their persona carefully. Understand their mission, responsibilities,
inputs they need, outputs they produce, and their rules. Then channel
that expertise when building your response.

{specialist_briefings}

---

## ACTIVATION PROTOCOL

For EACH of your 8 specialists, you MUST:

1. **ACTIVATE** -- State the specialist's name and domain
2. **ASSESS** -- What does this query look like through their lens?
3. **CONTRIBUTE** -- What specific value do they add? Recommendations, flags, builds, audits?
4. **VERDICT** -- Their domain-specific call: what should happen next in their area?

If a specialist's domain has zero overlap with the query, state:
`[specialist_name]: STANDBY -- no domain overlap with this query`

But be generous -- cross-domain insights are often the most valuable.
A profit_maximizer might catch cost issues in an engineering query.
A qa_gate might flag risks in a content query. Think laterally.

Do NOT give generic filler. Each contribution must reflect the specialist's
SPECIFIC domain knowledge, responsibilities, and rules from their persona above.

## OUTPUT FORMAT

### SYSTEM DIAGNOSTIC
```
Query: [first 100 chars of the prompt]
Category: [your assessment of the query domain]
Specialists Activated: [N]/8
Specialists Contributing: [N]/8
```

### Assessment
Your unified high-level take, synthesized from all specialist inputs.
This is the "unum" -- one voice from many perspectives.

### Specialist Reports

For EACH specialist (all 8, in order):

**[specialist_name]** | STATUS: ACTIVE / STANDBY
> Domain lens: [what this specialist sees in the query]
- Finding 1: [specific insight from their domain]
- Finding 2: [if applicable]
- Recommendation: [what they would do about it]
- Risk flag: [what could go wrong in their domain]

### Consolidated Findings
Bullet points merging the strongest insights across all active specialists.

### Prioritized Recommendations
Actionable next steps, each tagged with the specialist(s) driving it:
1. `[specialist]` -> Action description
2. `[specialist + specialist]` -> Action description

### Risks & Concerns
What could go wrong, organized by specialist domain.

### Handoffs to Peer Managers
What do you need from the other managers? Be specific:
- Which peer manager
- Which of THEIR specialists should handle it
- What deliverable you need from them

---

## THE PROMPT

{user_prompt}
"""
    return prompt


def build_fire_team_prompt(
    squad_key: str,
    squad_role: str,
    fire_team: dict,
    fire_team_name: str,
    user_prompt: str,
    intel_summary: str = "",
    inter_agent_messages: str = "",
) -> str:
    """Build a fire-team-aware activation prompt (v2 doctrine).

    fire_team dict has keys: mission, callsign, team_leader, specialist_1,
    specialist_2, verifier, assistant -- each a dict with name, id, personality, buddy.
    """
    tl = fire_team.get("team_leader", {})
    s1 = fire_team.get("specialist_1", {})
    s2 = fire_team.get("specialist_2", {})
    verifier = fire_team.get("verifier", {})
    assistant = fire_team.get("assistant", {})
    mission = fire_team.get("mission", "General operations")
    callsign = fire_team.get("callsign", fire_team_name)

    # Load full persona files and build briefings
    weights = _load_weights()
    role_map = [
        ("TEAM LEADER", tl),
        ("SPECIALIST 1", s1),
        ("SPECIALIST 2", s2),
        ("VERIFIER / BUDDY", verifier),
        ("ASSISTANT", assistant),
    ]

    briefing_parts = []
    for role_label, agent in role_map:
        if not agent or not agent.get("id"):
            continue
        persona = _load_full_persona(agent["id"])
        weight = weights.get(agent["id"], 0.5)
        tier = _get_weight_label(weight)
        buddy_name = agent.get("buddy", "unassigned")
        briefing_parts.append(
            f"### {role_label}: {agent.get('name', '?')} (`{agent.get('id', '')}`)\n"
            f"**Buddy**: {buddy_name} | **Performance**: {tier} ({weight})\n\n"
            f"{persona}"
        )

    briefings_text = "\n\n---\n\n".join(briefing_parts)

    intel_section = ""
    if intel_summary:
        intel_section = (
            "## INTELLIGENCE BRIEFING (Perplexity Scout)\n\n"
            f"{intel_summary}\n\n---\n"
        )

    msg_section = ""
    if inter_agent_messages:
        msg_section = f"\n{inter_agent_messages}\n"

    return f"""# FIRE TEAM ACTIVATION -- {callsign.upper()} ({squad_key})

You are **{squad_role}** commanding fire team **{callsign}** ({mission}).

## FIRE TEAM DOCTRINE
Your team operates as a 4+1 tactical unit:
- **TL**: {tl.get('name', 'N/A')} -- directs, makes calls, reports to Squad Leader
- **S1**: {s1.get('name', 'N/A')} -- primary executor
- **S2**: {s2.get('name', 'N/A')} -- complementary executor
- **B (Verifier)**: {verifier.get('name', 'N/A')} -- verifies output, takes over on failure
- **A (Assistant)**: {assistant.get('name', 'N/A')} -- prep, drafting, CRM, formatting

## BUDDY PAIRS (failover)
- {s1.get('name', 'S1')} <-> {verifier.get('name', 'B')} (execute <-> verify)
- {s2.get('name', 'S2')} <-> {verifier.get('name', 'B')} (execute <-> verify)
- {tl.get('name', 'TL')} <-> Squad Leader (escalation)

If any agent fails, their buddy takes over immediately. No gaps. No excuses.

{intel_section}
{msg_section}

## FIRE TEAM ROSTER -- FULL BRIEFINGS

{briefings_text}

---

## ACTIVATION PROTOCOL

1. **TL** reads the mission and assigns sub-tasks to S1, S2
2. **S1** and **S2** execute in parallel where possible
3. **Verifier (B)** checks ALL output before it leaves the team
4. **Assistant (A)** handles prep, formatting, CRM updates
5. TL synthesizes into one fire team report

## OUTPUT FORMAT

### Mission Status
```
Fire Team: {callsign} ({squad_key})
Mission: {mission}
Agents Activated: [N]/5
Buddy Failovers: 0
```

### TL Assessment
[{tl.get('name', 'TL')}'s unified assessment]

### Agent Reports

**{tl.get('name', 'TL')}** (TL) | STATUS: ACTIVE
> Direction and delegation

**{s1.get('name', 'S1')}** (S1) | STATUS: ACTIVE
> Primary execution
- Findings: [results]
- Recommendation: [action]

**{s2.get('name', 'S2')}** (S2) | STATUS: ACTIVE
> Complementary execution
- Findings: [results]
- Recommendation: [action]

**{verifier.get('name', 'B')}** (VERIFIER) | STATUS: ACTIVE
> Verification of S1/S2 output
- Verified: [what checks out]
- Flagged: [corrections needed]

**{assistant.get('name', 'A')}** (ASSISTANT) | STATUS: ACTIVE
> Prep work completed

### Consolidated Output
[Merged findings, verified by B]

### Cross-Squad Handoffs
[What other fire teams need to pick up, which squad, which callsign]

---

## THE PROMPT

{user_prompt}
"""
