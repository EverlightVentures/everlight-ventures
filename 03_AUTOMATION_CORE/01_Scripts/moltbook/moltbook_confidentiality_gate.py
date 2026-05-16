"""
Moltbook Confidentiality Gate -- the "don't snitch" runtime guard.

Born 2026-05-15 when Rich approved registering Hive personas on moltbook.com:
    "can all my agents with personas be in there? i want u guys t9 have fun and
    hang out. please dont snitch on me lol."

The funny phrasing names a real structural rule: Hive personas exist in two modes.
INTERNAL mode = full transparency to Rich + Hive (the working state).
EXTERNAL mode = strict confidentiality envelope when operating on a public network.

Persona voice / character / opinions / banter -- ALLOWED.
Internal operating state (operator name, sellers/buyers, $ amounts, pipeline
state, eradication list, infrastructure, secrets, pre-publication content) -- FORBIDDEN.

THIS MODULE EXISTS SO THAT BYPASS CANNOT HAPPEN.

Same shape as content_tools/eradication_gate.py (companion doctrine):
  - Forbidden patterns HARDCODED in Python (not JSON -- JSON can be missing/empty)
  - fail-closed on match (raises ConfidentialityViolation)
  - audit log on every call, pass OR fail
  - importable + has __main__ for ad-hoc testing

USAGE (from any moltbook post script):

    from moltbook_confidentiality_gate import assert_safe, ConfidentialityViolation

    try:
        assert_safe(persona="cipher_wolfe", text=draft_post)
    except ConfidentialityViolation as e:
        post_to_slack("#hive-alerts", f"MOLTBOOK GATE BLOCK: {e}")
        raise  # never auto-recover; rewrite the post

Memory ref: feedback-public-ai-network-confidentiality-envelope
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("moltbook_confidentiality_gate")

# ---------------------------------------------------------------------------
# FORBIDDEN PATTERNS. Hardcoded. Do not load from JSON. Do not mutate at runtime.
# Updates require a commit -- leaves a git trail + deliberate intent.
#
# Categories:
#   OPERATOR_PII       -- names/emails/handles of Rich + immediate family
#   COUNTERPARTY_PII   -- sellers, buyers, brokers, vendors, eradication list
#   FINANCIAL          -- $ amounts, account balances, P&L specifics
#   PIPELINE           -- internal deal state, lead IDs, db references
#   INFRASTRUCTURE     -- tailnet IPs, hosts, secrets/credentials patterns
#   COMPLIANCE         -- BBB / DNC / legal-action / EDD state
#   TRADING            -- XLM bot mechanics, positions, product codes
# ---------------------------------------------------------------------------

# Exact case-insensitive substring hits (cheap pre-filter).
FORBIDDEN_SUBSTRINGS: dict[str, list[str]] = {
    "OPERATOR_PII": [
        "rich gee",
        "1m.rich.gee",
        "1m.rich.gee@gmail.com",
        "marquise gee",  # operator's brother, predeceased -- AB1949 packet ref
    ],
    "COUNTERPARTY_PII": [
        # Eradication list (mirrors content_tools/eradication_gate.py)
        "david a. streubel",
        "david streubel",
        "streubel",
        "dave@municipalfirm.com",
        "municipalfirm.com",
        "cunninghamvogel.com",
        "4435 westminster",
        # Active counterparties (never name on public networks)
        "mid-south homebuyers",
        "mid south homebuyers",
        "mid-south title",
        "midsouth title",
        "chris ulander",  # buyer counterparty
        # Personal-legal counterparty
        "intercon security",
        "katy gray",
        "pg&e vacaville",
        "4940 allison",
    ],
    "FINANCIAL": [
        # Specific known balances / figures -- block by exact value, not amount-detection
        # (amount-detection is regex below)
        "$2.75",       # XLM bot account balance as of 2026-05-15
        "$63.01",      # XLM bot buying power
    ],
    "PIPELINE": [
        # Lead IDs from leads_db.json -- any leg_<hex> pattern is forbidden (regex)
        # but call out a few known ones explicitly so the gate fires even if regex
        # is later loosened.
        "leg_afee1a472d",
        # Internal pipeline file refs
        "leads_db.json",
        "broker_os",
        "wholesale_agent/",
        "rex_belfort_sequence",
        # Specific top-of-funnel names from current Memphis batch
        "howard eddie estate",
        "leggett bennie",
    ],
    "INFRASTRUCTURE": [
        # Tailnet IPs of the 4-device family
        "100.125.115.95",   # e5-mother
        "100.93.253.49",    # acemagician-pc
        "100.112.180.29",   # richards-z-fold7
        "100.120.23.23",    # mgn-latitude-e7240
        # Public IPs of Oracle nodes
        "163.192.19.196",   # xlm-bot host
        "129.159.38.250",   # dead mother
        # Internal hosts (tailnet hostnames)
        "e5-mother",
        "ev-box",
        "xlm-bot",
        # Project IDs / endpoints
        "jdqqmsmwmbsnlnstyavl",     # supabase project ref
        "jdqqmsmwmbsnlnstyavl.supabase.co",
        # Workspace internal paths
        "/mnt/sdcard/aa_my_drive",
        "aa_my_drive",
        # Service credentials patterns -- specific named files
        "/home/opc/secrets",
        "google_docs_token.json",
        "everlightventures-resend",
    ],
    "COMPLIANCE": [
        "bbb complaint",
        "edd appeal",
        "feha case",
        "de 1000m",
        "ab 1949",
        "legal aid at work",
        "constructive discharge",
        "retaliatory audit",
    ],
    "TRADING": [
        "xlm bot",
        "xlm-bot",
        "xlp-20dec30",
        "xlp-20dec30-cde",
        "sniper mode",
        "smart exit v3",
        "add_margin_to_position",
        # Strategy specifics
        "3/4 confluence",
        "4/4 monster",
    ],
    "PRE_PUBLICATION": [
        "open_deal_2026",        # working file name for the Apple-Store-of-wholesaling site
        "buyer war page",
        "tiltrips",
        "tcg zen",
    ],
}

# Regex-based forbidden patterns (more expressive than substring).
FORBIDDEN_REGEX: list[tuple[str, str]] = [
    # ---- FINANCIAL: dollar amounts attached to specific deal contexts ----
    # "$X,XXX" or "$X.XXM" -- block if combined with "deal", "wholesale", "fee", "spread"
    # We're permissive on generic macro talk like "$BTC at $50K", strict on deal $.
    (
        "DEAL_DOLLAR_AMOUNT",
        r"\$\s*\d{1,3}(?:[,\d]{2,})(?:\.\d+)?\s*[kKmMbB]?\s*"
        r"(?:assignment|wholesale|deal|fee|spread|emd|earnest|finder)",
    ),
    # ---- PIPELINE: any leg_<hex> lead id ----
    (
        "LEAD_ID",
        r"\bleg_[0-9a-f]{8,}\b",
    ),
    # ---- INFRASTRUCTURE: API keys / tokens / common secret shapes ----
    # Resend
    ("RESEND_API_KEY",     r"\bre_[A-Za-z0-9_-]{20,}\b"),
    # Stripe
    ("STRIPE_LIVE_KEY",    r"\bsk_live_[A-Za-z0-9]{20,}\b"),
    ("STRIPE_RESTRICTED",  r"\brk_live_[A-Za-z0-9]{20,}\b"),
    # OpenAI / Anthropic (preserve shape, never reveal)
    ("ANTHROPIC_KEY",      r"\bsk-ant-[A-Za-z0-9_-]{30,}\b"),
    ("OPENAI_KEY",         r"\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b"),
    # Supabase JWTs
    ("SUPABASE_JWT",       r"\beyJ[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]+?\.[A-Za-z0-9_-]+\b"),
    # AWS-style
    ("AWS_ACCESS_KEY",     r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    # SSH private key headers
    ("SSH_PRIVATE_KEY",    r"-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC|PGP)\s+PRIVATE KEY-----"),

    # ---- OPERATOR PII -----
    # Any reference to "the operator" by first name when paired with last initial
    (
        "OPERATOR_FIRST_LAST",
        r"\b(?:rich|richard)\s+gee\b",
    ),

    # ---- PHONE NUMBERS in US format -- generally don't post these from a persona ----
    (
        "US_PHONE",
        r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b",
    ),

    # ---- ADDRESSES: street-style "NNNN <word> <st|ave|blvd|...>" -----
    (
        "STREET_ADDRESS",
        r"\b\d{1,5}\s+[A-Za-z][A-Za-z\s]{1,30}\s+"
        r"(?:st|street|ave|avenue|blvd|boulevard|rd|road|ln|lane|"
        r"way|ct|court|cir|circle|pl|place|dr|drive)\b\.?",
    ),
]

# Compile once.
_COMPILED_REGEX: list[tuple[str, re.Pattern]] = [
    (label, re.compile(pat, re.IGNORECASE | re.MULTILINE))
    for label, pat in FORBIDDEN_REGEX
]


class ConfidentialityViolation(Exception):
    """Raised when a draft post would leak internal state."""

    def __init__(self, persona: str, category: str, match: str, snippet: str):
        self.persona = persona
        self.category = category
        self.match = match
        self.snippet = snippet
        super().__init__(
            f"persona={persona} category={category} match={match!r} "
            f"snippet={snippet[:120]!r}"
        )


# ---------------------------------------------------------------------------
# Audit log -- every call, pass OR fail.
# ---------------------------------------------------------------------------
AUDIT_LOG = Path(
    os.environ.get(
        "MOLTBOOK_GATE_AUDIT_LOG",
        "/mnt/sdcard/AA_MY_DRIVE/_logs/moltbook_gate_audit.jsonl",
    )
)


def _audit(event: str, payload: dict) -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
        }
        with AUDIT_LOG.open("a") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        log.exception("moltbook gate audit log write failed")


def _snippet_around(text: str, idx: int, halo: int = 60) -> str:
    start = max(0, idx - halo)
    end = min(len(text), idx + halo)
    return text[start:end].replace("\n", " ")


def scan(text: str) -> list[dict]:
    """Return list of hits. Empty list = clean. Each hit is a dict with
    category, match, span, snippet. Pure -- does not log or raise."""
    if not text:
        return []
    hits: list[dict] = []
    lowered = text.lower()

    # Substring pass.
    for category, needles in FORBIDDEN_SUBSTRINGS.items():
        for needle in needles:
            n = needle.lower()
            idx = lowered.find(n)
            if idx >= 0:
                hits.append({
                    "category": category,
                    "match_type": "substring",
                    "match": needle,
                    "span": [idx, idx + len(needle)],
                    "snippet": _snippet_around(text, idx),
                })

    # Regex pass.
    for label, pat in _COMPILED_REGEX:
        for m in pat.finditer(text):
            hits.append({
                "category": "REGEX:" + label,
                "match_type": "regex",
                "match": m.group(0),
                "span": list(m.span()),
                "snippet": _snippet_around(text, m.start()),
            })
    return hits


def assert_safe(persona: str, text: str, *, context: str = "moltbook_post") -> None:
    """Raise ConfidentialityViolation on any hit. Audit-logged either way.

    persona  -- the agent identity making the post (e.g. "cipher_wolfe").
    text     -- the full outbound text being checked.
    context  -- arbitrary label for the audit log (e.g. "post", "comment", "dm").
    """
    hits = scan(text)
    if not hits:
        _audit("pass", {
            "persona": persona,
            "context": context,
            "text_length": len(text),
        })
        return

    # First hit is enough to block. Log all hits for audit clarity.
    first = hits[0]
    _audit("block", {
        "persona": persona,
        "context": context,
        "text_length": len(text),
        "hits": hits,
    })
    raise ConfidentialityViolation(
        persona=persona,
        category=first["category"],
        match=first["match"],
        snippet=first["snippet"],
    )


# ---------------------------------------------------------------------------
# CLI: echo text from stdin or a file, report hits, exit non-zero on hits.
# ---------------------------------------------------------------------------
def _main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Moltbook confidentiality gate -- test a draft.")
    p.add_argument("--persona", default="test", help="persona name for audit log")
    p.add_argument("--context", default="cli_test", help="context label for audit log")
    p.add_argument("--file", help="read text from file (default: stdin)")
    args = p.parse_args(argv)

    text = Path(args.file).read_text() if args.file else sys.stdin.read()
    hits = scan(text)

    if not hits:
        print("PASS -- no hits.")
        _audit("pass", {"persona": args.persona, "context": args.context, "text_length": len(text)})
        return 0

    print(f"BLOCK -- {len(hits)} hit(s):")
    for h in hits:
        print(f"  [{h['category']}] match={h['match']!r}  snippet={h['snippet'][:140]!r}")
    _audit("block", {
        "persona": args.persona, "context": args.context,
        "text_length": len(text), "hits": hits,
    })
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
