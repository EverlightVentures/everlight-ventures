"""hive_tags.py - Controlled tag vocabulary for the Hive logging pipeline.

Seeded from organic tags already in use across:
  - ai_workers/blinko_bridge.py (TAGS dict, lines 55-63)
  - rex_master_pipeline.py (#hive/wholesale, #hive/pipeline)
  - hive_slack_digest.py (#hive/session, #hive/claude-cli)
  - memory_pipeline.py (#hive/memory-pipeline)

Any tag not in VALID_TAGS is remapped to #hive/uncategorized by tag_or_default(),
with a warning printed to stderr so drift is observable without breaking bots.

Usage:
    from content_tools.hive_tags import VALID_TAGS, tag_or_default, normalize

    tags = [tag_or_default(t) for t in raw_tags]
"""
from __future__ import annotations

import sys

VALID_TAGS: set[str] = {
    "#hive/session",
    "#hive/claude-cli",
    "#hive/wholesale",
    "#hive/pipeline",
    "#hive/memory-pipeline",
    "#hive/war-room",
    "#hive/convergence",
    "#hive/intel",
    "#hive/report",
    "#hive/uncategorized",
    "#hive/roundtable",
    "#hive/judiciary",
    "#xlm/trade-decision",
    "#xlm/directive",
    "#claude/memory",
    "#claude/audit",
    "#broker/ops",
    "#content/factory",
    "#field/ops",
}

_FALLBACK = "#hive/uncategorized"


def normalize(tag: str) -> str:
    """Lowercase and ensure a leading '#'."""
    t = (tag or "").strip()
    if not t:
        return ""
    if not t.startswith("#"):
        t = "#" + t
    return t.lower()


def tag_or_default(tag: str, warn: bool = True) -> str:
    """Return tag if it is in VALID_TAGS, else #hive/uncategorized.

    Warns once per unknown tag (stderr only). Callers never see an exception.
    """
    t = normalize(tag)
    if t in VALID_TAGS:
        return t
    if warn:
        print(
            f"[hive_tags] unknown tag {t!r} remapped to {_FALLBACK!r}",
            file=sys.stderr,
        )
    return _FALLBACK


def validate_list(tags: list[str]) -> list[str]:
    """Normalize and validate a list of tags. Preserves order, drops duplicates."""
    seen: list[str] = []
    for raw in tags or []:
        t = tag_or_default(raw)
        if t not in seen:
            seen.append(t)
    return seen
