"""
Hive Mind Router - classifies a prompt and picks the best managers.
Perplexity always runs (intel scout). Router decides which of the
other 3 (Claude, Gemini, Codex) should also engage.
"""

import re
from typing import List, Tuple

from .config import load_roster


def classify(prompt: str, roster: dict = None) -> Tuple[str, List[str]]:
    """
    Classify a prompt and return (category, list_of_manager_keys).

    Perplexity is always included (it runs as intel scout separately).
    This returns the full set of managers needed.
    """
    if roster is None:
        roster = load_roster()

    rules = roster.get("routing_rules", {})
    prompt_lower = prompt.lower()

    scores = {}
    for category, rule in rules.items():
        keywords = rule.get("keywords", [])
        score = 0
        for kw in keywords:
            if kw.lower() in prompt_lower:
                score += 1
        if score > 0:
            scores[category] = score

    if not scores:
        # No keyword match - default to full deliberation (all workers)
        return "full", ["gemini", "codex", "perplexity"]

    # Pick the category with the highest score
    best_category = max(scores, key=scores.get)
    managers = rules[best_category].get("managers", [])

    # Perplexity is always included
    if "perplexity" not in managers:
        managers = ["perplexity"] + managers

    return best_category, managers


def classify_lite(roster: dict = None) -> Tuple[str, List[str]]:
    """Return the lite mode manager set."""
    if roster is None:
        roster = load_roster()
    return "lite", roster.get("lite_managers", ["claude", "perplexity"])


def classify_all() -> Tuple[str, List[str]]:
    """Force all workers."""
    return "all", ["gemini", "codex", "perplexity"]
