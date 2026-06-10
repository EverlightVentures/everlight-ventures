# Hive Skill Patterns

Ported from Daniel Miessler's Fabric (MIT license) per `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/05_OSINT_and_Security/fabric_opensource_ai_framework.txt`.

Every pattern here is a reusable prompt module any Hive agent can invoke. They are plain markdown so Claude Code reads them natively.

## Why these patterns

Fabric's pattern library is a collection of battle-tested prompts. Rather than re-deriving them, we port the ones that fit Everlight's workflows. This raises the baseline quality of every Hive agent's output without us having to hand-engineer prompts each time.

## Loading a pattern

When an agent needs to process text through one of these patterns, the orchestrator reads the `.md` file and prepends it to the user input. Example:

```python
from pathlib import Path
pattern = Path(".claude/agents/patterns/summarize.md").read_text()
text_to_summarize = "..."
prompt = f"{pattern}\n\n# INPUT\n{text_to_summarize}"
# Send prompt to LLM
```

For agents that support skills natively (Claude Code agents), reference the pattern path in the agent's system prompt:
> "When asked to summarize, follow the instructions in `.claude/agents/patterns/summarize.md`."

## Available patterns

- `summarize.md` - Produce a one-sentence + bullet summary of any text
- `extract_insights.md` - Pull surprising, action-relevant insights
- `extract_wisdom.md` - Pull durable lessons + memorable quotes
- `analyze_claims.md` - Fact-check each claim in a piece for evidence strength
- `create_tags.md` - Generate 5-10 relevant tags for Blinko indexing

## Hive-specific additions

Any Hive-original patterns live here too. Prefix Hive ones with `hive_` to distinguish from Fabric imports.

- `hive_slack_reply.md` - Tight, on-brand Slack reply
- `hive_ceo_brief_line.md` - One-liner for Marcus's morning brief
- `hive_wholesale_headline.md` - Rex Blackwell's lead-of-the-day headline

## Changelog

- 2026-04-21: Initial import of 5 Fabric patterns + 3 Hive originals.
