"""
Content Engine — SEO optimization step.
Generates meta tags, schema markup, keywords, and internal link plan.
"""

import json
from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_json


def optimize_seo(topic: str, intent: str, blog: str, project_dir: Path) -> dict:
    """
    Generate SEO pack from the blog post.
    Returns SEO data dict and saves seo.json to project_dir.
    """
    prompt = f"""Generate a complete SEO optimization pack for this blog post.

Topic: {topic}
Content type: {intent}
Blog excerpt: {blog[:2000]}

Output a JSON object with these fields:
{{
    "title_tag": "under 60 chars, keyword-rich",
    "meta_description": "under 155 chars, compelling, includes CTA",
    "primary_keyword": "main target keyword",
    "secondary_keywords": ["list", "of", "3-5", "related", "keywords"],
    "slug": "url-friendly-slug",
    "h1": "main heading",
    "schema_type": "Article, HowTo, FAQ, etc.",
    "schema_markup": {{}},
    "internal_link_suggestions": [
        {{"anchor_text": "text", "suggested_topic": "related article topic"}}
    ],
    "external_link_suggestions": [
        {{"anchor_text": "text", "reason": "why link here"}}
    ],
    "readability_notes": "brief assessment of content readability"
}}

Rules:
- Title tag must include the primary keyword near the start
- Meta description should be a compelling one-sentence summary
- Schema markup should be valid JSON-LD compatible
- Internal links should reference topics a content site would naturally cover
- Output ONLY the JSON, no markdown fences"""

    system = "You are an SEO specialist. Output clean JSON. Be specific with keywords and schema."
    raw = call_openai(prompt, system=system, temperature=0.3, max_tokens=1500)

    # Parse JSON from response
    seo_data = _parse_json(raw, topic)

    write_json(project_dir / "seo.json", seo_data)
    return seo_data


def _parse_json(raw: str, topic: str) -> dict:
    """Try to parse JSON from AI response, fall back to defaults."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    # Fallback
    return {
        "title_tag": topic[:60],
        "meta_description": f"Learn about {topic}. Complete guide with expert insights.",
        "primary_keyword": topic.lower(),
        "secondary_keywords": [],
        "slug": topic.lower().replace(" ", "-")[:60],
        "parse_error": "Could not parse AI response",
        "raw_response": raw[:500],
    }
