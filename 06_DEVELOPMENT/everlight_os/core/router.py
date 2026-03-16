"""
Everlight OS — Request router.
Classifies input into engine + intent, produces a step plan.
"""

import re
from typing import Optional
from .contracts import RouterResult, StepDef


# --- Classification patterns ---

TRADING_PATTERNS = [
    r"\b(trade|trading)\b",
    r"\b(xlm|xlp|perp|derivatives?)\b",
    r"\b(bot|margin|pnl|p&l|position)\b",
    r"\b(report|anomal|regime|confluence)\b.*\b(trad|bot|market)\b",
]

BOOKS_PATTERNS = [
    r"\b(book|manuscript|series|chapter|kdp)\b",
    r"\b(sam|robo|luna)\b.*\b(learn|adventure|superpower|story)\b",
    r"\b(children|kids|coloring|illustration)\b.*\b(book|page|prompt)\b",
    r"\b(publish|kindle|amazon)\b.*\b(book|ebook)\b",
]

SAAS_PATTERNS = [
    r"\bbuild\s+saas\b",
    r"\bsaas\s+(idea|product|app|platform|tool)\b",
    r"\bsaas\s+factory\b",
    r"\blaunch\s+a\s+(saas|startup|app)\b",
    r"\bproduct\s+spec\b.*\b(saas|startup)\b",
]

STATUS_PATTERNS = [
    r"\beverlight\s+status\b",
    r"\bsystem\s+status\b",
    r"\bstatus\s+report\b",
]

CONTENT_SUBTYPES = {
    "howto": [
        r"\bhow\s+to\b",
        r"\bstep[\s-]by[\s-]step\b",
        r"\bguide\b",
        r"\btutorial\b",
    ],
    "comparison": [
        r"\bvs\.?\b",
        r"\bcompare|comparison\b",
        r"\bbest\b.*\bfor\b",
        r"\bbuyer.?s?\s+guide\b",
        r"\btop\s+\d+\b.*\b(for|to)\b",
    ],
    "news": [
        r"\bnews\b",
        r"\bupdate\b",
        r"\bannounce|announcement\b",
        r"\blaunch|launched\b",
        r"\b202\d\b",
    ],
    "listicle": [
        r"\btop\s+\d+\b",
        r"\b\d+\s+(best|ways|tips|tools|resources)\b",
        r"\blist\s+of\b",
    ],
    "explainer": [
        r"\bwhat\s+is\b",
        r"\bexplain\b",
        r"\bunderstand\b",
        r"\bintro(duction)?\s+to\b",
    ],
}


def _match_any(text: str, patterns: list) -> bool:
    text = text.lower()
    return any(re.search(p, text) for p in patterns)


def _detect_content_subtype(text: str) -> str:
    text = text.lower()
    best = "explainer"
    for subtype, patterns in CONTENT_SUBTYPES.items():
        if any(re.search(p, text) for p in patterns):
            return subtype
    return best


# --- Step plan builders ---

def _trading_steps(intent: str) -> list:
    if intent in ("daily_report", "report"):
        return [
            StepDef(name="parse_logs", worker="local", description="Read xlm_bot decision/trade/incident logs"),
            StepDef(name="compute_metrics", worker="local", description="Calculate gate pass rates, PnL, streaks, margin trajectory"),
            StepDef(name="detect_anomalies", worker="local", description="Flag unusual patterns in metrics"),
            StepDef(name="generate_report", worker="openai", description="Write natural-language daily report from metrics"),
            StepDef(name="post_to_slack", worker="slack", description="Post report summary to Slack"),
        ]
    elif intent == "status":
        return [
            StepDef(name="read_state", worker="local", description="Read current bot state + position"),
            StepDef(name="post_to_slack", worker="slack", description="Post status summary to Slack"),
        ]
    return []


def _content_steps(intent: str) -> list:
    return [
        StepDef(name="research", worker="perplexity", description="Deep research on topic with sources"),
        StepDef(name="outline", worker="openai", description="Create structured outline from template + research"),
        StepDef(name="draft", worker="openai", description="Write blog, socials, email, video script"),
        StepDef(name="seo", worker="openai", description="Generate SEO meta, schema, keywords"),
        StepDef(name="monetize", worker="local", description="Add affiliate slots, CTA variants, ad guidance"),
        StepDef(name="quality_gate", worker="openai", description="Check disclaimers, sources, no certainty language"),
        StepDef(name="post_to_slack", worker="slack", description="Post preview + approval request to Slack"),
    ]


def _saas_steps(intent: str) -> list:
    if intent == "full_build":
        return [
            # Phase 0 — Spec
            StepDef(name="scope_idea", worker="openai", description="Validate idea, extract slug, ICP, revenue model, competitive moat"),
            StepDef(name="pick_stack", worker="openai", description="Select tech stack and architecture pattern"),
            StepDef(name="write_spec", worker="openai", description="Generate all 9 spec documents"),
            StepDef(name="spec_gate", worker="local", description="Phase 0 gate: verify all spec docs exist"),
            # Phase 1 — Build (stubs)
            StepDef(name="scaffold_repo", worker="local", description="Generate repo scaffold and RUNBOOK.md"),
            StepDef(name="write_tests", worker="local", description="Generate TEST_PLAN.md and test stubs"),
            StepDef(name="build_gate", worker="local", description="Phase 1 gate: code runs, tests pass"),
            # Phase 2 — Launch (stubs)
            StepDef(name="write_launch", worker="openai", description="Generate go-to-market pack"),
            StepDef(name="write_ops", worker="openai", description="Generate ops pack"),
            StepDef(name="launch_gate", worker="local", description="Phase 2 gate: all launch materials reviewed"),
            StepDef(name="post_to_slack", worker="slack", description="Post final summary to Slack"),
        ]
    # Default: spec_only (MVP)
    return [
        StepDef(name="scope_idea", worker="openai", description="Validate idea, extract slug, ICP, revenue model, competitive moat"),
        StepDef(name="pick_stack", worker="openai", description="Select tech stack and architecture pattern"),
        StepDef(name="write_spec", worker="openai", description="Generate all 9 spec documents"),
        StepDef(name="spec_gate", worker="local", description="Phase 0 gate: verify all spec docs exist"),
        StepDef(name="post_to_slack", worker="slack", description="Post spec summary and approval request to Slack"),
    ]


def _books_steps(intent: str) -> list:
    return [
        StepDef(name="series_bible", worker="openai", description="Load or create series bible with character profiles"),
        StepDef(name="outline", worker="openai", description="Create chapter outline with lesson/theme"),
        StepDef(name="manuscript", worker="openai", description="Draft full manuscript with character consistency"),
        StepDef(name="illustrations", worker="openai", description="Generate cover + interior + coloring page prompts"),
        StepDef(name="kdp_metadata", worker="openai", description="Generate KDP title, description, keywords, categories"),
        StepDef(name="launch_pack", worker="openai", description="Create social posts, email, video script for launch"),
        StepDef(name="post_to_slack", worker="slack", description="Post book summary + approval to Slack"),
    ]


# --- Main router ---

def classify(request_text: str, url: str = None, mode_hint: str = None) -> RouterResult:
    """
    Classify a request into engine + intent + step plan.

    Args:
        request_text: The user's request
        url: Optional URL to include in research
        mode_hint: Force a specific engine ("trading", "content", "books")

    Returns:
        RouterResult with engine, intent, confidence, and steps
    """
    text = request_text.lower().strip()

    # Mode hint override
    if mode_hint:
        engine = mode_hint
    # Explicit command prefixes (highest priority)
    elif text.startswith(("post ", "post: ", "content ", "write ")):
        engine = "content"
    elif text.startswith(("book ", "book: ", "new book ")):
        engine = "books"
    elif text.startswith(("trade ", "trade: ", "trading ")):
        engine = "trading"
    elif text.startswith(("build saas:", "build saas ", "saas ", "saas: ")):
        engine = "saas"
    # Status check
    elif _match_any(text, STATUS_PATTERNS):
        return RouterResult(engine="status", intent="full_status", confidence=0.95, steps=[])
    # Pattern-based classification
    elif _match_any(text, TRADING_PATTERNS):
        engine = "trading"
    elif _match_any(text, BOOKS_PATTERNS):
        engine = "books"
    elif _match_any(text, SAAS_PATTERNS):
        engine = "saas"
    # Default: content
    else:
        engine = "content"

    # Determine intent and steps
    if engine == "trading":
        if "status" in text:
            intent = "status"
        else:
            intent = "daily_report"
        steps = _trading_steps(intent)
        confidence = 0.85

    elif engine == "books":
        intent = "new_book"
        steps = _books_steps(intent)
        confidence = 0.80

    elif engine == "saas":
        intent = "full_build" if "full build" in text else "spec_only"
        steps = _saas_steps(intent)
        confidence = 0.90

    elif engine == "content":
        intent = _detect_content_subtype(text)
        steps = _content_steps(intent)
        confidence = 0.75

    else:
        intent = "unknown"
        steps = []
        confidence = 0.3

    return RouterResult(
        engine=engine,
        intent=intent,
        confidence=confidence,
        steps=steps,
        metadata={"url": url} if url else {},
    )
