"""
Books Engine — Book outline step.
Creates chapter-by-chapter outline with lesson/theme.
"""

from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text


def create_book_outline(title: str, series_bible: str, project_dir: Path) -> str:
    """
    Create a detailed book outline from the idea + series bible.
    Returns outline text and saves to project_dir.
    """
    prompt = f"""Create a detailed children's picture book outline.

Book title/idea: {title}

Series bible (for character/world consistency):
{series_bible[:3000]}

Create an outline with:
1. **Book concept** — one paragraph summary, the lesson/superpower/theme
2. **Target details** — age range, page count (24-32), reading time
3. **Page-by-page breakdown** (each page = one spread):
   - Page 1-2: Opening/setup
   - Pages 3-16: Story arc (problem, adventure, challenges)
   - Pages 17-22: Climax and resolution
   - Pages 23-24: Lesson reinforcement + ending

For each page/spread:
- Brief text (what the page says, 1-3 sentences for this age range)
- Illustration note (what the picture shows)
- Emotional beat (what the reader feels)

4. **Key lesson** — what the child takes away
5. **Character moments** — specific scenes that showcase each character's personality
6. **Callback/continuity** — how this connects to previous books in the series

Output clean markdown."""

    system = "You are a children's book author specializing in picture books for ages 4-8. Create engaging, educational stories with heart."
    outline = call_openai(prompt, system=system, temperature=0.7, max_tokens=3000)

    write_text(project_dir / "outline.md", outline)
    return outline
