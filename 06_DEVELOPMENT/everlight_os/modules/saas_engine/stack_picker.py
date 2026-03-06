"""
SaaS Factory — Tech stack selector.
Takes the scope dict, picks an appropriate stack, produces stack.json.
"""

import json
from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_json


def pick_stack(scope: dict, project_dir: Path) -> dict:
    """
    Select the tech stack for the SaaS given its scope.
    Returns the stack dict and writes stack.json.
    """
    stack_path = project_dir / "stack.json"
    if stack_path.exists():
        with open(stack_path) as f:
            return json.load(f)

    prompt = f"""You are a senior software architect specializing in SaaS products.

Product: {scope.get('product_name', 'Unknown')}
One-liner: {scope.get('one_liner', '')}
ICP: {scope.get('icp', '')}
Revenue model: {scope.get('revenue_model', '')}
MVP scope: {scope.get('mvp_scope', '')}

Select a practical, proven tech stack. Optimize for:
- Speed to MVP (favor batteries-included frameworks)
- Solo founder or small team viability
- Low operational overhead

Return ONLY valid JSON:
{{
  "frontend": "e.g. Next.js 14 (App Router)",
  "backend": "e.g. Next.js API routes / FastAPI",
  "database": "e.g. Supabase (Postgres)",
  "auth": "e.g. Supabase Auth / Clerk",
  "hosting": "e.g. Vercel + Supabase",
  "payments": "e.g. Stripe",
  "email": "e.g. Resend",
  "monitoring": "e.g. Sentry + Vercel Analytics",
  "ci_cd": "e.g. GitHub Actions",
  "rationale": "2-3 sentence explanation of choices",
  "summary": "One line: e.g. Next.js + Supabase + Vercel + Stripe"
}}

Return only JSON — no markdown, no explanation."""

    system = "You are a senior SaaS architect. Return only valid JSON."
    raw = call_openai(prompt, system=system, temperature=0.3, max_tokens=800)

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines)
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            stack = json.loads(clean[start:end])
        else:
            raise json.JSONDecodeError("No JSON", clean, 0)
    except json.JSONDecodeError:
        stack = {
            "frontend": "Next.js 14",
            "backend": "Next.js API routes",
            "database": "Supabase (Postgres)",
            "auth": "Supabase Auth",
            "hosting": "Vercel",
            "payments": "Stripe",
            "summary": "Next.js + Supabase + Vercel + Stripe (fallback)",
            "rationale": "AI could not generate structured stack — using defaults",
        }

    write_json(stack_path, stack)
    return stack
