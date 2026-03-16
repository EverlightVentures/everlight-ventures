"""
Books Engine — KDP metadata packager.
Generates title, description, keywords, categories for Amazon KDP.
"""

import json
from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_json


def generate_kdp_metadata(title: str, outline: str, series: str, project_dir: Path) -> dict:
    """
    Generate KDP-ready metadata.
    Returns metadata dict and saves kdp_metadata.json.
    """
    prompt = f"""Generate Amazon KDP metadata for this children's book.

Book idea/title: {title}
Series: {series}
Outline excerpt: {outline[:1500]}

Output a JSON object:
{{
    "title": "full book title",
    "subtitle": "optional subtitle",
    "series_name": "Adventures with Sam",
    "series_number": 5,
    "author": "Everlight Kids",
    "description": "book description for KDP listing (150-200 words, HTML allowed)",
    "keywords": ["7 keywords for KDP search, max 50 chars each"],
    "categories": ["2 BISAC category suggestions"],
    "age_range": "4-8",
    "grade_range": "Preschool-3",
    "language": "English",
    "page_count": 28,
    "trim_size": "8.5 x 8.5 inches",
    "interior_type": "Premium Color",
    "pricing": {{
        "paperback_usd": 9.99,
        "ebook_usd": 2.99,
        "hardcover_usd": 19.99
    }},
    "launch_date_suggestion": "suggested launch timing",
    "competing_titles": ["2-3 similar books on Amazon to position against"]
}}

Make the description compelling — parents are the buyers.
Keywords should be specific and searchable.
Output ONLY the JSON."""

    system = "You are an Amazon KDP publishing specialist for children's books. Output clean JSON."
    raw = call_openai(prompt, system=system, temperature=0.4, max_tokens=1500)

    # Parse JSON
    metadata = _parse_json(raw, title)
    write_json(project_dir / "kdp_metadata.json", metadata)
    return metadata


def _parse_json(raw: str, title: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    return {
        "title": title,
        "series_name": "Adventures with Sam",
        "author": "Everlight Kids",
        "parse_error": "Could not parse AI response",
    }
