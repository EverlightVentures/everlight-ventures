"""
Content Engine — Monetization step.
Adds affiliate slots, CTA variants, and ad guidance.
"""

from pathlib import Path
from ...core.filesystem import write_text


# Intent → monetization strategy
MONETIZATION_RULES = {
    "comparison": {
        "affiliate": True,
        "affiliate_note": "High buyer intent — affiliate links for each compared product",
        "ad_strategy": "Display ads + in-content native ads",
        "email_capture": True,
        "suggested_programs": ["Amazon Associates", "Impact", "ShareASale", "Direct brand programs"],
    },
    "listicle": {
        "affiliate": True,
        "affiliate_note": "Each list item is an affiliate opportunity",
        "ad_strategy": "Display ads between list items",
        "email_capture": True,
        "suggested_programs": ["Amazon Associates", "specific niche programs"],
    },
    "howto": {
        "affiliate": True,
        "affiliate_note": "Affiliate links for tools/products mentioned in steps",
        "ad_strategy": "Display ads + sidebar",
        "email_capture": True,
        "suggested_programs": ["Tool/service affiliate programs relevant to topic"],
    },
    "news": {
        "affiliate": False,
        "affiliate_note": "News content — affiliates feel forced, skip unless natural fit",
        "ad_strategy": "Display ads (news gets high RPM)",
        "email_capture": True,
        "suggested_programs": [],
    },
    "explainer": {
        "affiliate": True,
        "affiliate_note": "Affiliate for getting-started tools at the end",
        "ad_strategy": "Display ads + sidebar",
        "email_capture": True,
        "suggested_programs": ["Relevant tool/platform affiliate programs"],
    },
}


def generate_monetization(topic: str, intent: str, blog: str, project_dir: Path) -> str:
    """
    Generate monetization plan based on content type.
    Returns monetization markdown and saves to project_dir.
    """
    rules = MONETIZATION_RULES.get(intent, MONETIZATION_RULES["explainer"])

    lines = [
        f"# Monetization Plan — {topic}",
        f"",
        f"## Content Type: {intent}",
        f"",
        f"## Revenue Streams",
        f"",
        f"### 1. Display Ads (Always)",
        f"- Strategy: {rules['ad_strategy']}",
        f"- Expected RPM: varies by niche",
        f"- Placement: above fold, in-content, sidebar",
        f"",
    ]

    if rules["affiliate"]:
        lines.extend([
            f"### 2. Affiliate Links",
            f"- {rules['affiliate_note']}",
            f"- Suggested programs: {', '.join(rules['suggested_programs'])}",
            f"",
            f"**Affiliate Slot Guidance:**",
        ])
        # Find AFFILIATE_SLOT markers in blog or suggest placements
        if "AFFILIATE_SLOT" in blog:
            count = blog.count("AFFILIATE_SLOT")
            lines.append(f"- {count} affiliate slot(s) marked in blog draft")
            lines.append(f"- Replace each [AFFILIATE_SLOT] with relevant product/service link")
        else:
            lines.append(f"- Add affiliate links after product mentions")
            lines.append(f"- Add a 'Recommended Tools' section near the end")
        lines.append("")

    lines.extend([
        f"### {'3' if rules['affiliate'] else '2'}. Email Capture (Always)",
        f"- Placement: after introduction + end of post",
        f"- Lead magnet idea: downloadable checklist or cheat sheet related to '{topic}'",
        f"",
        f"## CTA Variants",
        f"",
        f"### In-Post CTA",
        f"- \"Want the complete guide? Subscribe for weekly insights.\"",
        f"- \"Get our free {intent} checklist — drop your email below.\"",
        f"",
        f"### End-of-Post CTA",
        f"- \"Found this helpful? Share it with someone who needs it.\"",
        f"- \"Join 1,000+ readers getting insights like this every week.\"",
        f"",
        f"### Social CTA",
        f"- \"Link in bio for the full breakdown.\"",
        f"- \"Save this for later.\"",
        f"- \"Follow for more {intent}s like this.\"",
        f"",
        f"## Disclaimers Needed",
    ])

    # Check what disclaimers are needed
    topic_lower = topic.lower()
    if any(w in topic_lower for w in ("crypto", "trading", "invest", "stock", "xlm", "bitcoin", "finance", "money")):
        lines.append("- **Financial disclaimer** required (not financial advice)")
    if rules["affiliate"]:
        lines.append("- **Affiliate disclosure** required (may earn commission)")
    if any(w in topic_lower for w in ("health", "medical", "supplement", "diet", "fitness")):
        lines.append("- **Health disclaimer** required (consult a professional)")

    lines.append("")
    result = "\n".join(lines)
    write_text(project_dir / "monetization.md", result)
    return result
