"""
Books Engine — Launch planner.
Generates social posts, email, video script for book launch.
"""

from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text


def create_launch_pack(title: str, kdp_metadata: dict, outline: str, project_dir: Path) -> dict:
    """
    Generate complete launch content pack.
    Returns dict of file paths.
    """
    paths = {}

    # Social posts for launch
    socials = _draft_launch_socials(title, kdp_metadata, outline)
    write_text(project_dir / "launch_socials.md", socials)
    paths["socials"] = str(project_dir / "launch_socials.md")

    # Email announcement
    email = _draft_launch_email(title, kdp_metadata, outline)
    write_text(project_dir / "launch_email.md", email)
    paths["email"] = str(project_dir / "launch_email.md")

    # Video script
    video = _draft_launch_video(title, kdp_metadata)
    write_text(project_dir / "video_script.md", video)
    paths["video"] = str(project_dir / "video_script.md")

    # Seedance prompts
    seedance = _draft_seedance(title, video)
    write_text(project_dir / "seedance_prompts.txt", seedance)
    paths["seedance"] = str(project_dir / "seedance_prompts.txt")

    return paths


def _draft_launch_socials(title: str, metadata: dict, outline: str) -> str:
    desc = metadata.get("description", "")
    prompt = f"""Create social media launch posts for a new children's book.

Book: {title}
Series: Adventures with Sam
Description: {desc}
Outline excerpt: {outline[:800]}

Create:
## Instagram (3 posts)
1. Launch announcement (exciting, with book cover reference)
2. Behind-the-scenes / sneak peek
3. "Tag a parent" engagement post

## TikTok (2 posts)
1. Book reveal video caption
2. Reading a page aloud caption

## Facebook (1 post)
1. Launch announcement with purchase link placeholder

## X/Twitter (2 tweets)
1. Launch announcement
2. Thank you / personal story about the book

Include hashtags for each platform. Use [BOOK_LINK] placeholder."""

    system = "You are a children's book marketing specialist. Write warm, excited, parent-targeted social posts."
    return call_openai(prompt, system=system, temperature=0.8, max_tokens=2000)


def _draft_launch_email(title: str, metadata: dict, outline: str) -> str:
    prompt = f"""Write a book launch email for a children's book.

Book: {title}
Series: Adventures with Sam
Description: {metadata.get('description', '')}

Format:
- Subject line
- Preview text
- Warm greeting
- What the book is about (2 paragraphs)
- Why we wrote it
- Special launch offer (if applicable)
- CTA to purchase [BOOK_LINK]
- P.S. line

Audience: parents and family of the target age range (4-8).
Tone: warm, excited, personal."""

    system = "You are an email marketer for a children's book publisher. Write warm, compelling launch emails."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=1000)


def _draft_launch_video(title: str, metadata: dict) -> str:
    prompt = f"""Write a 30-45 second video script for a children's book launch.

Book: {title}
Series: Adventures with Sam
Description: {metadata.get('description', '')}

Format:
- HOOK (2s): Grab attention
- SETUP (5s): What's the book about
- HIGHLIGHT (10s): Show key pages / read a line
- SOCIAL PROOF (5s): Reviews or series track record
- CTA (3s): Where to buy

Include:
- Visual direction [in brackets]
- Voice-over text
- Music mood suggestion"""

    system = "You are a book trailer video producer. Create engaging, professional video scripts."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=800)


def _draft_seedance(title: str, video_script: str) -> str:
    prompt = f"""Convert this book launch video script into Seedance AI video prompts.

Book: {title}
Script:
{video_script}

Generate 3-4 scene prompts:
1. Book cover reveal (animated, sparkles, exciting)
2. Page flip / reading scene
3. Kids enjoying the book
4. Purchase CTA scene

Each prompt: detailed visual, camera movement, duration, mood."""

    system = "You are a video AI prompt engineer. Write vivid scene descriptions."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=800)
