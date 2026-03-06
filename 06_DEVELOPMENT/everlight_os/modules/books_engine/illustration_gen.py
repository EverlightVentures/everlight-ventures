"""
Books Engine — Illustration prompt generator.
Creates prompts for cover, interior illustrations, and coloring pages.
"""

from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text


def generate_illustration_prompts(title: str, manuscript: str, series_bible: str, project_dir: Path) -> dict:
    """
    Generate all illustration prompts from the manuscript.
    Returns dict of file paths created.
    """
    paths = {}

    # Cover prompt
    cover = _generate_cover_prompt(title, manuscript, series_bible)
    write_text(project_dir / "cover_prompt.txt", cover)
    paths["cover"] = str(project_dir / "cover_prompt.txt")

    # Interior illustration prompts
    interior = _generate_interior_prompts(manuscript, series_bible)
    write_text(project_dir / "illustration_prompts.txt", interior)
    paths["illustrations"] = str(project_dir / "illustration_prompts.txt")

    # Coloring page prompts
    coloring = _generate_coloring_prompts(manuscript, series_bible)
    write_text(project_dir / "coloring_page_prompts.txt", coloring)
    paths["coloring"] = str(project_dir / "coloring_page_prompts.txt")

    return paths


def _generate_cover_prompt(title: str, manuscript: str, series_bible: str) -> str:
    prompt = f"""Create a detailed AI image generation prompt for a children's book COVER.

Book title: {title}
Manuscript excerpt: {manuscript[:1000]}
Visual style from series bible: {series_bible[:500]}

The cover prompt should:
- Feature Sam and Robo prominently
- Be vibrant, colorful, eye-catching
- Convey the book's theme/adventure
- Leave space for the title text at top
- Match the "Adventures with Sam" series style
- Be specific enough for Midjourney/DALL-E

Write ONE detailed prompt (2-3 sentences) followed by:
- Style tags (e.g., "children's book illustration, vibrant colors, digital art")
- Color palette suggestion
- Composition notes"""

    system = "You are a children's book art director. Write specific, vivid image prompts."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=600)


def _generate_interior_prompts(manuscript: str, series_bible: str) -> str:
    prompt = f"""Generate illustration prompts for each page of this children's book manuscript.

Manuscript:
{manuscript[:4000]}

Visual style: {series_bible[:300]}

For each page that has an illustration note, create a detailed AI image prompt:
- Describe the scene, characters, expressions, and actions
- Specify vibrant, colorful, kid-friendly digital art style
- Maintain character consistency (Sam: curious kid, Robo: friendly robot companion)
- Include background/setting details
- Each prompt should be 1-2 sentences

Format:
Page X: [detailed prompt]
Style: [style tags]
"""

    system = "You are a children's book illustrator. Create vivid, consistent illustration prompts."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=3000)


def _generate_coloring_prompts(manuscript: str, series_bible: str) -> str:
    prompt = f"""Generate coloring page prompts for a children's book.

Manuscript excerpt:
{manuscript[:2000]}

Create 8-10 coloring page prompts:
- Black and white line art style
- Thick, clean outlines (easy for ages 4-8 to color)
- Simple compositions (not too detailed)
- Feature Sam and Robo in different scenes from the story
- Include at least 2 full-page character portraits
- Include at least 2 action scenes
- Include 1 "spot the difference" style page

Format:
Page X: [description]
Complexity: [simple/medium]
Focus: [character/scene/activity]"""

    system = "You are a children's activity book designer. Create fun, age-appropriate coloring page designs."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=1500)
