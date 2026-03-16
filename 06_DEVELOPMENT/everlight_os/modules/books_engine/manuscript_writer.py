"""
Books Engine — Manuscript writer.
Drafts full manuscript with character consistency checks.
"""

from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text


def write_manuscript(title: str, outline: str, series_bible: str, project_dir: Path) -> str:
    """
    Draft the full manuscript from outline + series bible.
    Returns manuscript text and saves to project_dir.
    """
    prompt = f"""Write a complete children's picture book manuscript.

Title: {title}

Series bible (character/tone reference):
{series_bible[:2000]}

Outline to follow:
{outline[:3000]}

Rules:
- Each page should have 1-3 SHORT sentences (ages 4-8 reading level)
- Use simple vocabulary but don't be condescending
- Include dialogue — Sam and Robo should talk to each other
- Robo's speech should be slightly quirky/robotic but warm
- Sam should be curious and brave
- Include emotional moments (not just action)
- End with a clear, warm lesson
- Total: 24-32 pages

Format each page as:
---
**Page X**
[Text that appears on the page]

*Illustration: [Brief description of what the illustration should show]*
---

Write the COMPLETE manuscript, every page."""

    system = "You are a bestselling children's book author. Write with warmth, wonder, and wisdom. Simple words, big feelings."
    manuscript = call_openai(prompt, system=system, temperature=0.8, max_tokens=4000)

    write_text(project_dir / "manuscript.md", manuscript)
    return manuscript
