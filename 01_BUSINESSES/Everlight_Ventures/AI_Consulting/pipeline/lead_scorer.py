#!/usr/bin/env python3
"""
AI Consulting Lead Scorer -- rates SMB leads by AI-readiness signals.

Scoring criteria:
  - No website or basic website (+20) -- needs help
  - Low Google rating (<4.0) or few reviews (<20) (+10) -- pain point
  - High-value vertical (dental, legal, home services) (+15)
  - Reviews mention "hard to reach" / "slow response" (+25)
  - High review volume (>50) indicating revenue (+10-20)
  - No chat widget on website (+20) -- automation opportunity

Usage:
    python3 lead_scorer.py --input prospects_dentist_20260323.json
"""

import argparse
import json
import re
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
LOG_DIR = WORKSPACE / "_logs" / "ai_consulting"

# High-value verticals for AI consulting
HIGH_VALUE_VERTICALS = {
    "dentist", "dental", "hvac", "plumber", "plumbing",
    "electrician", "electrical", "law firm", "attorney",
    "legal", "real estate", "realtor",
}

# Pain signals in reviews
PAIN_SIGNALS = [
    r"hard to reach",
    r"slow response",
    r"never called back",
    r"can't get through",
    r"long wait",
    r"no response",
    r"appointment scheduling",
    r"wish they had",
    r"outdated",
    r"old school",
]


def score_lead(lead: dict) -> dict:
    """Score a lead and return the lead with score and breakdown."""
    score = 0
    reasons = []

    # Vertical value
    category = lead.get("category", "").lower()
    if any(v in category for v in HIGH_VALUE_VERTICALS):
        score += 15
        reasons.append("+15 high-value vertical")

    # Google rating (low = pain point)
    rating = lead.get("google_rating", 0)
    if rating and rating < 4.0:
        score += 10
        reasons.append(f"+10 low rating ({rating})")

    # Review count
    reviews = lead.get("review_count", 0)
    if reviews < 20:
        score += 10
        reasons.append(f"+10 few reviews ({reviews})")
    elif reviews > 100:
        score += 20
        reasons.append(f"+20 high volume ({reviews} reviews = revenue)")
    elif reviews > 50:
        score += 10
        reasons.append(f"+10 moderate volume ({reviews} reviews)")

    # Website presence
    website = lead.get("website", "")
    if not website:
        score += 20
        reasons.append("+20 no website")

    # Pain signals in review snippets
    snippets = " ".join(lead.get("review_snippets", []))
    if snippets:
        for pattern in PAIN_SIGNALS:
            if re.search(pattern, snippets, re.IGNORECASE):
                score += 25
                reasons.append(f"+25 pain signal: '{pattern}'")
                break  # Only count once

    # Phone available (easier to reach)
    if lead.get("phone"):
        score += 5
        reasons.append("+5 phone available")

    lead["score"] = score
    lead["score_reasons"] = reasons
    lead["score_grade"] = (
        "A" if score >= 60 else
        "B" if score >= 40 else
        "C" if score >= 20 else
        "D"
    )
    return lead


def main():
    parser = argparse.ArgumentParser(description="AI Consulting Lead Scorer")
    parser.add_argument("--input", required=True, help="Input JSON file from scraper")
    parser.add_argument("--min-score", type=int, default=30, help="Minimum score to keep")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = LOG_DIR / args.input

    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        return

    leads = json.loads(input_path.read_text(encoding="utf-8"))
    print(f"[SCORE] Scoring {len(leads)} leads...")

    scored = [score_lead(lead) for lead in leads]
    scored.sort(key=lambda l: l["score"], reverse=True)

    # Summary
    grades = {"A": 0, "B": 0, "C": 0, "D": 0}
    for lead in scored:
        grades[lead["score_grade"]] += 1

    print(f"\n[RESULTS] Grade distribution:")
    for grade, count in sorted(grades.items()):
        print(f"  {grade}: {count}")

    qualified = [l for l in scored if l["score"] >= args.min_score]
    print(f"\n[QUALIFIED] {len(qualified)}/{len(scored)} leads score >= {args.min_score}")

    for lead in qualified[:10]:
        print(f"  [{lead['score_grade']}] {lead['score']}pts - {lead['business_name']}")
        for reason in lead["score_reasons"]:
            print(f"    {reason}")

    # Save scored output
    output_path = input_path.with_stem(input_path.stem + "_scored")
    output_path.write_text(json.dumps(scored, indent=2), encoding="utf-8")
    print(f"\n[SAVED] {output_path}")


if __name__ == "__main__":
    main()
