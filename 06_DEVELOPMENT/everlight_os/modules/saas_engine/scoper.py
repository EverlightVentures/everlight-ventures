"""
SaaS Factory — Idea scoper.
Validates the idea, extracts slug, ICP, revenue model, moat, competitors.
Produces scope.json — the foundation every other step builds on.
"""

import json
from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_json, slugify


def validate_and_scope(idea: str, project_dir: Path) -> dict:
    """
    Take a raw idea string, validate it, and extract structured scope fields.
    Returns the scope dict and writes scope.json.
    """
    scope_path = project_dir / "scope.json"
    if scope_path.exists():
        with open(scope_path) as f:
            return json.load(f)

    prompt = f"""You are a SaaS product manager and startup advisor.

Idea: {idea}

Analyze this SaaS idea and return ONLY valid JSON with these fields:
{{
  "slug": "url-safe-product-name-max-30-chars",
  "product_name": "Human readable product name",
  "one_liner": "One sentence value proposition (under 20 words)",
  "problem": "The specific problem this solves (2-3 sentences)",
  "solution": "How the product solves it (2-3 sentences)",
  "icp": "Ideal customer profile — who is the primary user",
  "revenue_model": "e.g. subscription $X/mo, usage-based, freemium, etc.",
  "moat": "Competitive advantage or differentiation (1-2 sentences)",
  "competitors": ["Competitor A", "Competitor B", "Competitor C"],
  "market_size": "Rough TAM estimate with reasoning",
  "mvp_scope": "Minimum viable feature set to validate core value",
  "risks": ["Risk 1", "Risk 2", "Risk 3"],
  "viable": true
}}

Return only JSON — no markdown, no explanation."""

    system = "You are a SaaS product strategist. Return only valid JSON."
    raw = call_openai(prompt, system=system, temperature=0.4, max_tokens=1200)

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines)
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            scope = json.loads(clean[start:end])
        else:
            raise json.JSONDecodeError("No JSON object", clean, 0)
    except json.JSONDecodeError:
        scope = {
            "slug": slugify(idea)[:30],
            "product_name": idea.title(),
            "one_liner": idea,
            "problem": idea,
            "solution": "TBD — AI could not generate structured scope",
            "icp": "TBD",
            "revenue_model": "TBD",
            "moat": "TBD",
            "competitors": [],
            "mvp_scope": idea,
            "risks": ["Scope not fully generated — review manually"],
            "viable": True,
        }

    write_json(scope_path, scope)
    return scope
