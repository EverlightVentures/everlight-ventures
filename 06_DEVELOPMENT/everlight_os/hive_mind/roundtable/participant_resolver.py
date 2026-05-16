"""Participant resolver -- auto-compose the right team for each Roundtable.

Banking-committee model: standing members + state-pair injections + topic-
keyword additions + severity escalations + Solomon's discretion (extras /
excludes). The classifier picks the process template from the question;
the resolver composes the participant list.

Public API:
    from hive_mind.roundtable.participant_resolver import classify, resolve

    process, hints = classify(question)
    participants = resolve(process, state=hints['state'], topics=hints['topics'])

Design notes:
  - Classifier is keyword-based (deterministic, auditable, no LLM cost).
  - Resolver always includes the convener (solomon_vale) first.
  - Order matters: standing -> state -> topics -> severity -> extras, deduped
    while preserving first-seen order.
  - max_participants cap is enforced by dropping LAST-added (lowest priority)
    overflow, never standing members.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
for candidate in (Path("/mnt/sdcard/AA_MY_DRIVE"), Path("/home/opc/AA_MY_DRIVE"), Path("/home/opc")):
    if candidate.exists():
        WORKSPACE = candidate
        break

TEMPLATES_PATH = WORKSPACE / "06_DEVELOPMENT/everlight_os/hive_mind/roundtable/process_templates.yaml"


class ResolverError(Exception):
    """Raised when the resolver cannot pick a process or compose participants."""


_cache: dict[str, Any] = {}


def _load_templates() -> dict[str, Any]:
    """Lazy-load + cache the templates YAML."""
    if "templates" in _cache:
        return _cache["templates"]
    if yaml is None:
        raise ResolverError("PyYAML not installed. Run: pip install pyyaml")
    if not TEMPLATES_PATH.exists():
        raise ResolverError(f"Templates file missing: {TEMPLATES_PATH}")
    data = yaml.safe_load(TEMPLATES_PATH.read_text())
    _cache["templates"] = data
    return data


def classify(question: str, hints: dict | None = None) -> tuple[str, dict]:
    """Pick a process template + extract routing hints from the question.

    Args:
        question: The roundtable question text.
        hints: Optional explicit hints (process, state, topics, severity).
               Explicit hints override classifier output.

    Returns:
        (process_key, hints_dict). hints_dict contains:
          - state: detected 2-letter state code or None
          - topics: list of detected topic keywords
          - severity: "normal" | "high" | "critical"
          - confidence: float 0-1 (how strongly keywords matched)
          - all_scores: dict of process -> match count (for debugging)
    """
    hints = dict(hints or {})
    templates = _load_templates()
    processes = templates.get("processes", {})
    q_lower = question.lower()

    # If explicit process given, validate it and return
    if hints.get("process"):
        if hints["process"] not in processes:
            raise ResolverError(f"Unknown process: {hints['process']!r}. Available: {list(processes)}")
        return hints["process"], _build_hints(hints, q_lower, templates)

    # Score each process by keyword overlap (word-boundary match)
    scores: dict[str, int] = {}
    for proc_key, proc_cfg in processes.items():
        keywords = proc_cfg.get("keywords", [])
        score = sum(1 for kw in keywords if _kw_match(kw, q_lower))
        if score > 0:
            scores[proc_key] = score

    if not scores:
        raise ResolverError(
            f"No process template matched the question. "
            f"Either add keywords to a template or pass hints={{'process': '<key>'}}. "
            f"Available processes: {list(processes)}"
        )

    # Highest score wins; ties broken by alphabetical order for determinism
    top = max(scores.items(), key=lambda kv: (kv[1], -ord(kv[0][0])))
    process_key = top[0]

    out_hints = _build_hints(hints, q_lower, templates)
    out_hints["all_scores"] = scores
    out_hints["confidence"] = round(top[1] / max(len(processes[process_key].get("keywords", [])), 1), 2)
    return process_key, out_hints


def _build_hints(provided: dict, q_lower: str, templates: dict) -> dict:
    """Extract state + topics + severity from question text and merge with provided hints."""
    out = {
        "state": provided.get("state"),
        "topics": list(provided.get("topics") or []),
        "severity": provided.get("severity", "normal"),
    }

    # Detect state from question if not provided
    if not out["state"]:
        for state_code, patterns in templates.get("state_patterns", {}).items():
            for pat in patterns:
                if re.search(pat, q_lower):
                    out["state"] = state_code
                    break
            if out["state"]:
                break

    # Detect topic keywords (additive — don't replace provided)
    for topic, keywords in templates.get("topic_keywords", {}).items():
        if any(_kw_match(kw, q_lower) for kw in keywords):
            if topic not in out["topics"]:
                out["topics"].append(topic)

    return out


def _kw_match(keyword: str, text: str) -> bool:
    """Match a keyword against text using word boundaries.

    Short keywords (≤4 chars) or those containing only letters require word
    boundaries to prevent false positives (e.g., 'ui' shouldn't match 'build').
    Multi-word keywords (containing space, hyphen, etc.) match as substrings
    since regex word boundaries don't behave intuitively across whitespace.
    """
    kw = keyword.lower().strip()
    if not kw:
        return False
    # Multi-word keywords -- substring match (regex \b across spaces is messy)
    if re.search(r"[\s\-./]", kw):
        return kw in text
    # Single-word -- enforce word boundaries
    return bool(re.search(rf"\b{re.escape(kw)}\b", text))


def resolve(
    process: str,
    state: str | None = None,
    topics: list[str] | None = None,
    severity: str = "normal",
    extras: list[str] | None = None,
    excludes: list[str] | None = None,
) -> dict[str, Any]:
    """Compose the participant list for a process.

    Args:
        process: Process template key (e.g., 'dnc_post_mortem').
        state: Optional 2-letter state code to trigger state-pair injection.
        topics: List of topic keys to trigger ad_hoc_by_topic injections.
        severity: 'normal' | 'high' | 'critical' -- triggers escalation.
        extras: Solomon's chair-discretion additions (overrides cap).
        excludes: Agents to remove (conflict-of-interest, recusal).

    Returns:
        Dict with:
          - convener: agent key
          - participants: ordered list of agent keys (excluding convener)
          - dropped: list of (agent_key, reason) for anything cut by max cap
          - process: process key used
          - rationale: string explaining the composition
    """
    templates = _load_templates()
    processes = templates.get("processes", {})
    if process not in processes:
        raise ResolverError(f"Unknown process: {process!r}")
    cfg = processes[process]

    convener = cfg.get("convener", "solomon_vale")
    standing = list(cfg.get("standing", []))
    excludes_set = set(excludes or [])

    # Compose in priority order: standing -> state -> topics -> severity -> extras
    composed: list[tuple[str, str]] = []  # (agent_key, source)
    seen: set[str] = set()

    def _add(key: str, source: str):
        if key in excludes_set or key in seen or key == convener:
            return
        composed.append((key, source))
        seen.add(key)

    # 1. Standing (always present)
    for a in standing:
        _add(a, "standing")

    # 2. State-pair injection
    if state:
        for a in cfg.get("ad_hoc_by_state", {}).get(state.upper(), []):
            _add(a, f"state:{state.upper()}")

    # 3. Topic-keyword injections
    for topic in topics or []:
        for a in cfg.get("ad_hoc_by_topic", {}).get(topic, []):
            _add(a, f"topic:{topic}")

    # 4. Severity escalation
    if severity in ("high", "critical"):
        for a in cfg.get("severity_escalation", {}).get(severity, []):
            _add(a, f"severity:{severity}")

    # 5. Extras (Solomon's discretion — overrides cap)
    extras_added = []
    for a in extras or []:
        if a not in seen and a != convener and a not in excludes_set:
            extras_added.append((a, "chair_discretion"))
            seen.add(a)

    # Apply max_participants cap, but only to non-standing
    max_p = cfg.get("max_participants", 10)
    dropped: list[tuple[str, str]] = []
    standing_count = sum(1 for _, src in composed if src == "standing")
    non_standing = [(k, s) for k, s in composed if s != "standing"]
    keep_non_standing = max(0, max_p - standing_count)
    if len(non_standing) > keep_non_standing:
        kept = non_standing[:keep_non_standing]
        dropped = [(k, f"capped:{s}") for k, s in non_standing[keep_non_standing:]]
        composed = [(k, s) for k, s in composed if s == "standing"] + kept

    # Extras always make it in (chair discretion)
    composed.extend(extras_added)

    participants = [k for k, _ in composed]
    rationale = _build_rationale(process, cfg, composed, dropped, state, topics, severity)

    return {
        "convener": convener,
        "participants": participants,
        "composition": composed,    # (agent, source) tuples
        "dropped": dropped,
        "process": process,
        "rationale": rationale,
    }


def _build_rationale(process, cfg, composed, dropped, state, topics, severity) -> str:
    lines = [
        f"Process: **{process}** -- {cfg.get('description', '')}",
        f"Convener: {cfg.get('convener', 'solomon_vale')}",
        f"Participants seated: {len(composed)} of max {cfg.get('max_participants', 10)}",
    ]
    if state:
        lines.append(f"State injection: {state.upper()}")
    if topics:
        lines.append(f"Topic triggers: {', '.join(topics)}")
    if severity != "normal":
        lines.append(f"Severity escalation: {severity}")

    lines.append("")
    lines.append("Composition (in seating order):")
    for agent, source in composed:
        lines.append(f"  - {agent}  [{source}]")
    if dropped:
        lines.append("")
        lines.append("Dropped by max_participants cap:")
        for agent, reason in dropped:
            lines.append(f"  - {agent}  [{reason}]")

    return "\n".join(lines)


# --- CLI for testing/debugging ----------------------------------------------
def _cli() -> int:
    import argparse, json
    parser = argparse.ArgumentParser(description="Roundtable participant resolver")
    parser.add_argument("question", help="The roundtable question")
    parser.add_argument("--process", "-p", help="Explicit process key (skips classifier)")
    parser.add_argument("--state", "-s", help="2-letter state code")
    parser.add_argument("--topics", "-t", nargs="*", help="Explicit topic keys")
    parser.add_argument("--severity", default="normal", choices=["normal", "high", "critical"])
    parser.add_argument("--extras", "-x", nargs="*", help="Chair-discretion additions")
    parser.add_argument("--excludes", "-e", nargs="*", help="Recusal / conflict exclusions")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable")
    args = parser.parse_args()

    hints = {}
    if args.process: hints["process"] = args.process
    if args.state: hints["state"] = args.state
    if args.topics: hints["topics"] = args.topics
    if args.severity: hints["severity"] = args.severity

    process, classified_hints = classify(args.question, hints)
    result = resolve(
        process=process,
        state=classified_hints.get("state"),
        topics=classified_hints.get("topics", []),
        severity=classified_hints.get("severity", "normal"),
        extras=args.extras,
        excludes=args.excludes,
    )

    if args.json:
        print(json.dumps({
            "classified_process": process,
            "classified_hints": classified_hints,
            "resolved": result,
        }, indent=2, default=str))
    else:
        print(f"Question: {args.question}\n")
        print(f"Classifier picked: **{process}**")
        if "confidence" in classified_hints:
            print(f"Confidence: {classified_hints['confidence']}")
        if "all_scores" in classified_hints:
            print(f"All scores: {classified_hints['all_scores']}")
        print()
        print(result["rationale"])
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
