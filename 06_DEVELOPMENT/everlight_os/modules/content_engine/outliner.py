"""
Content Engine — Outline step.
Creates structured H1/H2 outline from template + research.
"""

from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text


TEMPLATES = {
    "howto": """# How to {topic}

## Introduction
- What this guide covers
- Who it's for
- What you'll need

## Step 1: [First Step]
- Details
- Tips

## Step 2: [Second Step]
- Details
- Tips

## Step 3: [Third Step]
- Details
- Tips

## Common Mistakes to Avoid
- Mistake 1
- Mistake 2

## FAQ
- Q1
- Q2

## Conclusion
- Summary
- [CTA_SLOT]
- [AFFILIATE_SLOT]

## Disclaimer
[DISCLAIMER_SLOT]""",

    "comparison": """# {topic}: Complete Comparison Guide

## Introduction
- Why this comparison matters
- Who this guide helps

## Quick Comparison Table
| Feature | Option A | Option B |
|---------|----------|----------|

## Option A: [Name]
### Pros
### Cons
### Best For
### Pricing
[AFFILIATE_SLOT]

## Option B: [Name]
### Pros
### Cons
### Best For
### Pricing
[AFFILIATE_SLOT]

## Our Recommendation
- [CTA_SLOT]

## FAQ

## Disclaimer
[DISCLAIMER_SLOT]""",

    "news": """# {topic}

## What Happened
- Key facts
- Timeline

## Why It Matters
- Impact analysis
- Who's affected

## Expert Reactions
- Quote 1
- Quote 2

## What's Next
- Predictions
- Action items

## [CTA_SLOT]

## Disclaimer
[DISCLAIMER_SLOT]""",

    "listicle": """# {topic}

## Introduction
- What we're covering
- How we chose these

## 1. [Item Name]
- Description
- Key features
- [AFFILIATE_SLOT]

## 2. [Item Name]
- Description
- Key features
- [AFFILIATE_SLOT]

## 3. [Item Name]
- Description
- Key features

## How to Choose
- Decision factors

## Conclusion
- [CTA_SLOT]

## Disclaimer
[DISCLAIMER_SLOT]""",

    "explainer": """# {topic}: Everything You Need to Know

## What Is {topic_short}?
- Definition
- Brief history

## How It Works
- Mechanism
- Key components

## Why It Matters
- Benefits
- Use cases

## Examples
- Example 1
- Example 2

## Common Misconceptions
- Myth vs reality

## Getting Started
- First steps
- Resources
- [CTA_SLOT]

## FAQ

## Disclaimer
[DISCLAIMER_SLOT]""",
}


def create_outline(topic: str, intent: str, research: dict, project_dir: Path = None) -> str:
    """
    Create a structured outline using the template + research.
    Returns outline as markdown string.
    """
    template = TEMPLATES.get(intent, TEMPLATES["explainer"])
    key_points = research.get("key_points", [])
    raw_research = research.get("raw_research", "")

    # Use topic for template placeholders
    topic_short = topic.split()[-1] if len(topic.split()) > 3 else topic

    prompt = f"""Create a detailed blog post outline for: "{topic}"

Content type: {intent}

Use this template structure as a starting point:
{template.format(topic=topic, topic_short=topic_short)}

Research findings to incorporate:
{chr(10).join('- ' + p for p in key_points[:10])}

Additional research context:
{raw_research[:2000]}

Instructions:
- Fill in all [bracketed] placeholders with specific content
- Keep the H1/H2 structure but make it specific to the topic
- Add 2-3 more sections if the research supports them
- Mark CTA_SLOT, AFFILIATE_SLOT, DISCLAIMER_SLOT positions (don't fill these yet)
- Include specific facts from the research
- Output clean markdown"""

    system = "You are a content strategist. Create detailed, SEO-friendly blog outlines. Be specific, not generic."
    outline = call_openai(prompt, system=system, temperature=0.5, max_tokens=2000)

    if project_dir:
        write_text(project_dir / "outline.md", outline)

    return outline
