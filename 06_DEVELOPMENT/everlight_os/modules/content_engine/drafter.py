"""
Content Engine — Drafting step.
Generates blog post, social posts, email, and video script from outline + research.
"""

from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text


def draft_all(topic: str, intent: str, outline: str, research: dict, project_dir: Path) -> dict:
    """
    Generate all content drafts from the outline.
    Returns dict of file paths created.
    """
    paths = {}

    # Blog post
    blog = _draft_blog(topic, outline, research)
    write_text(project_dir / "blog.md", blog)
    paths["blog"] = str(project_dir / "blog.md")

    # Social posts
    socials = _draft_socials(topic, intent, blog)
    write_text(project_dir / "socials.md", socials)
    paths["socials"] = str(project_dir / "socials.md")

    # Email newsletter
    email = _draft_email(topic, blog)
    write_text(project_dir / "email.md", email)
    paths["email"] = str(project_dir / "email.md")

    # Video script
    video = _draft_video_script(topic, blog)
    write_text(project_dir / "video_script.md", video)
    paths["video_script"] = str(project_dir / "video_script.md")

    # Image prompts
    img_prompts = _draft_image_prompts(topic, intent)
    write_text(project_dir / "image_prompts.txt", img_prompts)
    paths["image_prompts"] = str(project_dir / "image_prompts.txt")

    # Seedance video prompts
    seedance = _draft_seedance_prompts(topic, video)
    write_text(project_dir / "seedance_prompts.txt", seedance)
    paths["seedance_prompts"] = str(project_dir / "seedance_prompts.txt")

    return paths


def _draft_blog(topic: str, outline: str, research: dict) -> str:
    raw_research = research.get("raw_research", "")
    prompt = f"""Write a complete blog post based on this outline.

Topic: {topic}

Outline:
{outline}

Research to reference:
{raw_research[:3000]}

Rules:
- Write 1200-1800 words
- Use the outline's H1/H2 structure
- Include specific facts and numbers from the research
- Natural, conversational tone — not robotic
- Include CTA_SLOT, AFFILIATE_SLOT, DISCLAIMER_SLOT markers where the outline indicates
- Add internal link placeholders as [INTERNAL_LINK: related topic]
- End with a strong conclusion and call-to-action"""

    system = "You are an expert content writer. Write engaging, well-researched blog posts. Use facts, not fluff."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=4000)


def _draft_socials(topic: str, intent: str, blog: str) -> str:
    prompt = f"""Create social media posts for this blog post.

Topic: {topic}
Blog excerpt: {blog[:1500]}

Generate EXACTLY these posts:

## Instagram
- 1 carousel caption (150-200 words, 3-5 hashtags, CTA to bio link)

## TikTok
- 1 video caption (hook in first line, casual tone, 7-10 hashtags)

## X (Twitter)
- 2 tweets (under 280 chars each, one standalone + one thread starter)

## Facebook
- 1 post (200-300 words, link included, professional tone)

Rules:
- Each post should feel native to its platform
- Don't just repeat the same content — adapt the angle
- Include relevant hashtags per platform norms
- Each post must have a clear CTA"""

    system = "You are a social media manager for multiple platforms. Write platform-native content that drives engagement."
    return call_openai(prompt, system=system, temperature=0.8, max_tokens=2000)


def _draft_email(topic: str, blog: str) -> str:
    prompt = f"""Write a newsletter email based on this blog post.

Topic: {topic}
Blog excerpt: {blog[:1500]}

Format:
- Subject line (compelling, under 60 chars)
- Preview text (under 100 chars)
- Greeting
- 3-4 paragraphs summarizing key insights (NOT the full blog)
- CTA to read the full post
- Sign-off

Rules:
- Conversational, like writing to a friend who's interested in this topic
- Tease the best insights but leave them wanting to click through
- Under 300 words total"""

    system = "You are an email marketing writer. Write concise, clickable newsletter emails."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=1000)


def _draft_video_script(topic: str, blog: str) -> str:
    prompt = f"""Write a short-form video script (15-45 seconds) based on this blog post.

Topic: {topic}
Blog excerpt: {blog[:1000]}

Format:
- HOOK (first 2-3 seconds — attention grabber)
- BODY (key insight in 3-4 sentences)
- CTA (what to do next)

Also include:
- Visual direction notes [in brackets]
- Suggested background music mood
- Estimated duration

Rules:
- Must work for both TikTok and Instagram Reels
- Casual, energetic tone
- One clear takeaway"""

    system = "You are a short-form video scriptwriter. Write punchy, engaging scripts that hook in 2 seconds."
    return call_openai(prompt, system=system, temperature=0.8, max_tokens=800)


def _draft_image_prompts(topic: str, intent: str) -> str:
    prompt = f"""Generate image generation prompts for a blog post about: {topic}

Create 4 prompts:

1. HERO IMAGE — blog header, wide format, eye-catching
2. INLINE IMAGE 1 — illustrates a key concept from the post
3. INLINE IMAGE 2 — illustrates another key concept
4. SOCIAL THUMBNAIL — square format, bold text overlay friendly

Each prompt should:
- Be 1-2 sentences
- Specify style (photo-realistic, illustration, flat design, etc.)
- Specify mood and color palette
- Be specific enough for AI image generation (Midjourney/DALL-E style)"""

    system = "You are a creative director. Write specific, visual image generation prompts."
    return call_openai(prompt, system=system, temperature=0.8, max_tokens=800)


def _draft_seedance_prompts(topic: str, video_script: str) -> str:
    prompt = f"""Convert this video script into Seedance AI video generation prompts.

Topic: {topic}
Script:
{video_script}

Generate 3 Seedance prompts:
1. Opening shot (2-3 seconds)
2. Main content shot (5-10 seconds)
3. Closing/CTA shot (2-3 seconds)

Each prompt should describe:
- Visual scene in detail
- Camera movement (pan, zoom, static)
- Mood and lighting
- Text overlays if applicable
- Duration"""

    system = "You are a video production AI prompt engineer. Write detailed scene descriptions for AI video generation."
    return call_openai(prompt, system=system, temperature=0.7, max_tokens=800)
