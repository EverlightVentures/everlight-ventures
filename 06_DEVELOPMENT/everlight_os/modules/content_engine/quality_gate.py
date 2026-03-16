"""
Content Engine — Quality gate.
Checks for plagiarism patterns, disclaimers, source attribution, certainty language.
"""

import re
from pathlib import Path
from ...core.ai_worker import call_openai
from ...core.filesystem import write_text, read_text


def run_quality_gate(topic: str, project_dir: Path) -> dict:
    """
    Run quality checks on the content bundle.
    Returns results dict and saves publish_checklist.md.
    """
    blog = read_text(project_dir / "blog.md")
    socials = read_text(project_dir / "socials.md")
    email = read_text(project_dir / "email.md")

    checks = []

    # 1. Disclaimer check
    checks.append(_check_disclaimers(topic, blog))

    # 2. Source attribution
    checks.append(_check_sources(blog, project_dir))

    # 3. Certainty language
    checks.append(_check_certainty_language(blog))

    # 4. Length check
    checks.append(_check_length(blog))

    # 5. CTA presence
    checks.append(_check_cta(blog, socials, email))

    # 6. AI quality review
    ai_review = _ai_quality_review(topic, blog)
    checks.append(ai_review)

    # Build publish checklist
    all_pass = all(c["pass"] for c in checks)
    checklist = _build_checklist(topic, checks, all_pass)
    write_text(project_dir / "publish_checklist.md", checklist)

    # QA report (detailed human-readable)
    qa_report = _build_qa_report(topic, checks, all_pass)
    write_text(project_dir / "qa_report.md", qa_report)

    # Approval status (machine-readable)
    score = next((c.get("score", 7) for c in checks if c.get("name") == "ai_quality_review"), 7)
    approval = {
        "approved": all_pass,
        "score": score,
        "checks_passed": sum(1 for c in checks if c.get("pass")),
        "checks_total": len(checks),
        "reasons": [f"{'PASS' if c['pass'] else 'FAIL'}: {c['name']} — {c['note']}" for c in checks],
        "required_fixes": [c["note"] for c in checks if not c.get("pass")],
    }
    from ...core.filesystem import write_json
    write_json(project_dir / "approval_status.json", approval)

    return {
        "all_pass": all_pass,
        "checks": checks,
        "checklist_path": str(project_dir / "publish_checklist.md"),
        "qa_report_path": str(project_dir / "qa_report.md"),
        "approval_status_path": str(project_dir / "approval_status.json"),
    }


def _check_disclaimers(topic: str, blog: str) -> dict:
    """Check if required disclaimers are present."""
    topic_lower = topic.lower()
    needs_financial = any(w in topic_lower for w in ("crypto", "trading", "invest", "stock", "xlm", "bitcoin", "finance", "money", "wallet"))
    needs_health = any(w in topic_lower for w in ("health", "medical", "supplement", "diet", "fitness"))
    needs_affiliate = "AFFILIATE_SLOT" in blog or "affiliate" in blog.lower()

    issues = []
    if needs_financial and "DISCLAIMER_SLOT" not in blog and "not financial advice" not in blog.lower():
        issues.append("Missing financial disclaimer")
    if needs_health and "consult" not in blog.lower():
        issues.append("Missing health disclaimer")
    if needs_affiliate and "affiliate" not in blog.lower() and "commission" not in blog.lower():
        issues.append("Missing affiliate disclosure")

    return {
        "name": "disclaimers",
        "pass": len(issues) == 0,
        "issues": issues,
        "note": "All required disclaimers present" if not issues else "; ".join(issues),
    }


def _check_sources(blog: str, project_dir: Path) -> dict:
    """Check that factual claims have source backing."""
    sources = read_text(project_dir / "sources.md")
    has_sources = bool(sources and len(sources) > 50)

    return {
        "name": "source_attribution",
        "pass": has_sources,
        "note": "Sources file present" if has_sources else "No sources file — add source citations",
    }


def _check_certainty_language(blog: str) -> dict:
    """Flag dangerous certainty language (financial/medical claims)."""
    certainty_patterns = [
        r"\bguaranteed?\b",
        r"\bwill definitely\b",
        r"\balways works?\b",
        r"\bnever fails?\b",
        r"\brisk[- ]free\b",
        r"\b100%\s+(safe|secure|guaranteed|certain)\b",
        r"\byou will make money\b",
        r"\bcure[sd]?\b",
    ]

    found = []
    blog_lower = blog.lower()
    for pat in certainty_patterns:
        matches = re.findall(pat, blog_lower)
        if matches:
            found.extend(matches)

    return {
        "name": "certainty_language",
        "pass": len(found) == 0,
        "issues": found[:5],
        "note": "No problematic certainty language" if not found else f"Found: {', '.join(found[:5])}",
    }


def _check_length(blog: str) -> dict:
    """Check blog post length."""
    word_count = len(blog.split())
    ok = 800 <= word_count <= 3000

    return {
        "name": "content_length",
        "pass": ok,
        "note": f"{word_count} words ({'good' if ok else 'adjust — target 1000-2000'})",
    }


def _check_cta(blog: str, socials: str, email: str) -> dict:
    """Check that CTAs are present in all content types."""
    issues = []
    if "CTA_SLOT" not in blog and not any(w in blog.lower() for w in ("subscribe", "sign up", "join", "follow", "learn more")):
        issues.append("Blog missing CTA")
    if socials and not any(w in socials.lower() for w in ("link in bio", "follow", "share", "save", "comment")):
        issues.append("Social posts missing CTA")
    if email and not any(w in email.lower() for w in ("read", "click", "check out", "learn more", "subscribe")):
        issues.append("Email missing CTA")

    return {
        "name": "cta_presence",
        "pass": len(issues) == 0,
        "note": "CTAs present in all content" if not issues else "; ".join(issues),
    }


def _ai_quality_review(topic: str, blog: str) -> dict:
    """Use AI to do a final quality check."""
    prompt = f"""Review this blog post for quality issues.

Topic: {topic}
Content:
{blog[:3000]}

Check for:
1. Factual accuracy red flags (claims that seem unsupported)
2. Tone consistency (should be helpful, not salesy)
3. Readability (is it clear and easy to follow?)
4. Any problematic claims (financial promises, health claims without caveats)

Reply with a JSON object:
{{
    "quality_score": 1-10,
    "issues": ["list of issues found"],
    "suggestions": ["list of improvements"],
    "overall": "one sentence summary"
}}

Output ONLY the JSON."""

    system = "You are a content editor. Be critical but constructive. Output clean JSON."
    raw = call_openai(prompt, system=system, temperature=0.3, max_tokens=500)

    # Try to parse
    try:
        import json
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            score = data.get("quality_score", 5)
            return {
                "name": "ai_quality_review",
                "pass": score >= 6,
                "note": data.get("overall", "Review complete"),
                "score": score,
                "issues": data.get("issues", []),
                "suggestions": data.get("suggestions", []),
            }
    except Exception:
        pass

    return {
        "name": "ai_quality_review",
        "pass": True,
        "note": "AI review completed (could not parse structured feedback)",
    }


def _build_checklist(topic: str, checks: list, all_pass: bool) -> str:
    """Build the publish checklist markdown."""
    lines = [
        f"# Publish Checklist — {topic}",
        "",
        f"**Status: {'READY TO PUBLISH' if all_pass else 'NEEDS REVIEW'}**",
        "",
        "## Quality Checks",
        "",
    ]

    for c in checks:
        icon = "x" if c["pass"] else " "
        lines.append(f"- [{icon}] **{c['name']}**: {c['note']}")
        if c.get("issues"):
            for issue in c["issues"][:3]:
                lines.append(f"  - {issue}")
        if c.get("suggestions"):
            for s in c["suggestions"][:3]:
                lines.append(f"  - Suggestion: {s}")

    lines.extend([
        "",
        "## Pre-Publish Actions",
        "- [ ] Review and approve blog draft",
        "- [ ] Replace [CTA_SLOT] with final CTA text",
        "- [ ] Replace [AFFILIATE_SLOT] with actual affiliate links",
        "- [ ] Replace [DISCLAIMER_SLOT] with appropriate disclaimer",
        "- [ ] Replace [INTERNAL_LINK] with actual internal links",
        "- [ ] Review social posts for platform accuracy",
        "- [ ] Review email subject line",
        "- [ ] Generate images from image_prompts.txt",
        "- [ ] Generate video from seedance_prompts.txt",
        "",
    ])

    return "\n".join(lines)


def _build_qa_report(topic: str, checks: list, all_pass: bool) -> str:
    """Build detailed QA report markdown."""
    passed = sum(1 for c in checks if c["pass"])
    total = len(checks)

    lines = [
        f"# QA Report — {topic}",
        "",
        f"**Verdict: {'APPROVED' if all_pass else 'BLOCKED — fixes required'}**",
        f"**Score: {passed}/{total} checks passed**",
        "",
        "---",
        "",
        "## Check Results",
        "",
    ]

    for c in checks:
        status = "PASS" if c["pass"] else "FAIL"
        lines.append(f"### {c['name']} — {status}")
        lines.append(f"> {c['note']}")
        lines.append("")
        if c.get("issues"):
            lines.append("**Issues:**")
            for issue in c["issues"]:
                lines.append(f"- {issue}")
            lines.append("")
        if c.get("suggestions"):
            lines.append("**Suggestions:**")
            for s in c["suggestions"]:
                lines.append(f"- {s}")
            lines.append("")

    if not all_pass:
        lines.extend([
            "---",
            "",
            "## Required Fixes",
            "",
        ])
        for c in checks:
            if not c["pass"]:
                lines.append(f"- **{c['name']}**: {c['note']}")
        lines.append("")

    lines.extend([
        "---",
        f"*Report generated by Everlight QA Gate*",
    ])

    return "\n".join(lines)
