"""Inter-agent communication layer for AI trading advisors.

Provides a shared message board (JSON file) where Claude, Gemini, and Codex
post assessments, challenge each other's positions, and reach consensus
before the bot acts.  Designed for fire-and-forget subprocess architecture --
each agent writes its assessment atomically and reads peers on the next cycle.

Never crashes.  All external reads/writes wrapped in try/except.
Thread-safe via threading.Lock on all file mutations.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# -- Module state ------------------------------------------------------
_ENABLED: bool = False
_CHALLENGE_ROUND: bool = False
_CONSENSUS_REQUIRED: bool = False
_EXIT_CHALLENGE_THRESHOLD: float = 0.70
_MAX_DEBATE_TIME_SEC: int = 30
_LOG_DEBATES: bool = False
_CONFIG: dict = {}

_BASE: Path = Path(__file__).parent.parent
_BOARD_PATH: Path = _BASE / "data" / "agent_comms.json"
_DEBATE_LOG_PATH: Path = _BASE / "logs" / "agent_debates.jsonl"

_STALE_SECONDS: int = 120

_lock = threading.Lock()

_KNOWN_AGENTS = ("claude", "gemini", "codex")


# -- Init / status -----------------------------------------------------

def init(config: dict | None = None) -> None:
    """Initialize from config.ai.agent_comms section.  Call once at start."""
    global _ENABLED, _CHALLENGE_ROUND, _CONSENSUS_REQUIRED
    global _EXIT_CHALLENGE_THRESHOLD, _MAX_DEBATE_TIME_SEC, _LOG_DEBATES
    global _CONFIG

    ai_cfg = (config or {}).get("ai") or {}
    comms_cfg = ai_cfg.get("agent_comms") or {}

    _ENABLED = bool(comms_cfg.get("enabled", False))
    if not _ENABLED:
        return

    _CHALLENGE_ROUND = bool(comms_cfg.get("challenge_round", False))
    _CONSENSUS_REQUIRED = bool(comms_cfg.get("consensus_required", False))
    _EXIT_CHALLENGE_THRESHOLD = float(comms_cfg.get("exit_challenge_threshold", 0.70))
    _MAX_DEBATE_TIME_SEC = int(comms_cfg.get("max_debate_time_sec", 30))
    _LOG_DEBATES = bool(comms_cfg.get("log_debates", False))
    _CONFIG = comms_cfg

    try:
        _BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DEBATE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def is_enabled() -> bool:
    """True when inter-agent comms are configured and active."""
    return _ENABLED


# -- Message board I/O -------------------------------------------------

def _read_board() -> dict:
    """Read the full message board.  Returns {} on any error."""
    try:
        if _BOARD_PATH.exists():
            raw = _BOARD_PATH.read_text()
            if raw.strip():
                return json.loads(raw)
    except Exception:
        pass
    return {}


def _write_board(data: dict) -> None:
    """Atomic write of the full board via tmp-and-rename."""
    try:
        tmp = _BOARD_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(_BOARD_PATH)
    except Exception:
        pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_epoch() -> float:
    return time.time()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# -- Public API: post / read assessments --------------------------------

def post_assessment(agent_name: str, assessment: dict) -> None:
    """Write an agent's assessment to the shared message board.

    assessment should contain: action, confidence, reasoning, concerns.
    """
    if not _ENABLED:
        return

    name = str(agent_name).lower().strip()

    entry = {
        "action": str(assessment.get("action", "HOLD")).upper(),
        "confidence": _safe_float(assessment.get("confidence"), 0.0),
        "reasoning": str(assessment.get("reasoning", "")),
        "concerns": list(assessment.get("concerns") or []),
        "timestamp": _now_iso(),
        "epoch": _now_epoch(),
    }

    with _lock:
        board = _read_board()
        board[name] = entry
        _write_board(board)

    # Post to Slack war room (fire-and-forget)
    try:
        from alerts import slack as _slack
        _slack.war_room_assessment(name, entry)
    except Exception:
        pass


def get_all_assessments() -> dict:
    """Read all current (non-stale) assessments from the message board.

    Assessments older than 120 seconds are excluded automatically.
    """
    if not _ENABLED:
        return {}

    board = _read_board()
    now = _now_epoch()
    result = {}

    for agent, data in board.items():
        if not isinstance(data, dict):
            continue
        epoch = _safe_float(data.get("epoch"), 0.0)
        if (now - epoch) <= _STALE_SECONDS:
            result[agent] = data

    return result


# -- Challenge round prompt builders ------------------------------------

def build_challenge_prompt(
    agent_name: str,
    own_assessment: dict,
    peer_assessments: dict,
) -> str:
    """Create a debate prompt for an agent showing its position vs peers."""
    lines = [
        "=== INTER-AGENT CHALLENGE ROUND ===",
        "",
        f"You are {agent_name.upper()}.  Below is YOUR current assessment "
        "and your peers' assessments.",
        "Review your peers' positions.  Do you still agree with your own "
        "assessment?",
        "Address any concerns they raised.  If you want to change your "
        "position, explain why.",
        "",
        "--- YOUR ASSESSMENT ---",
        f"  Action:     {own_assessment.get('action', '?')}",
        f"  Confidence: {_safe_float(own_assessment.get('confidence'), 0.0):.0%}",
        f"  Reasoning:  {own_assessment.get('reasoning', '(none)')}",
        f"  Concerns:   {', '.join(own_assessment.get('concerns') or ['none'])}",
    ]

    for peer_name, peer_data in peer_assessments.items():
        if peer_name.lower() == agent_name.lower():
            continue
        lines.extend([
            "",
            f"--- {peer_name.upper()}'S ASSESSMENT ---",
            f"  Action:     {peer_data.get('action', '?')}",
            f"  Confidence: {_safe_float(peer_data.get('confidence'), 0.0):.0%}",
            f"  Reasoning:  {peer_data.get('reasoning', '(none)')}",
            f"  Concerns:   {', '.join(peer_data.get('concerns') or ['none'])}",
        ])

    lines.extend([
        "",
        "Respond ONLY with valid JSON (no markdown, no commentary):",
        "{",
        '  "action": "ENTER_LONG" or "ENTER_SHORT" or "EXIT" or "HOLD" or "FLAT",',
        '  "confidence": 0.0 to 1.0,',
        '  "reasoning": "your updated analysis after reviewing peers",',
        '  "changed": true or false,',
        '  "change_reason": "why you changed (or empty string if you did not)"',
        "}",
    ])

    return "\n".join(lines)


def build_consensus_prompt(all_final_assessments: dict) -> str:
    """Create the executive decision prompt for Claude after challenge round."""
    # Analyze agreement
    actions: dict[str, list[str]] = {}
    for name, data in all_final_assessments.items():
        act = str(data.get("action", "HOLD")).upper()
        actions.setdefault(act, []).append(name)

    majority_action = None
    majority_agents: list[str] = []
    dissenter = None
    for act, agents in sorted(actions.items(), key=lambda x: -len(x[1])):
        if majority_action is None:
            majority_action = act
            majority_agents = agents
        else:
            if dissenter is None and len(agents) >= 1:
                dissenter = agents[0]

    total_agents = len(all_final_assessments)
    agree_count = len(majority_agents)
    all_agree = (agree_count == total_agents and total_agents > 0)

    lines = [
        "=== CONSENSUS DECISION - EXECUTIVE MODE ===",
        "",
        "You are Claude, the executive decision maker.",
        "All agents have completed the challenge round.  Here are their "
        "FINAL positions:",
        "",
    ]

    for name, data in all_final_assessments.items():
        changed = data.get("changed", False)
        tag = " (CHANGED from challenge round)" if changed else ""
        lines.extend([
            f"--- {name.upper()}{tag} ---",
            f"  Action:     {data.get('action', '?')}",
            f"  Confidence: {_safe_float(data.get('confidence'), 0.0):.0%}",
            f"  Reasoning:  {data.get('reasoning', '(none)')}",
            "",
        ])

    lines.extend([
        "--- AGREEMENT ANALYSIS ---",
        f"  Total agents reporting: {total_agents}",
        f"  Majority action: {majority_action or 'none'} ({agree_count} agents)",
        f"  Dissenter: {dissenter or 'none'}",
        f"  All agree: {all_agree}",
        "",
        "--- CONSENSUS RULES ---",
        "  All 3 agree = HIGH confidence.  Full conviction size.",
        "  2 of 3 agree = MODERATE confidence.  Standard size.",
        "  All disagree = NO consensus.  Go FLAT.  Do not trade.",
        "",
        "Make the final call.  Respond ONLY with valid JSON "
        "(no markdown, no commentary):",
        "{",
        '  "final_action": "ENTER_LONG" or "ENTER_SHORT" or "EXIT" '
        'or "HOLD" or "FLAT",',
        '  "confidence": 0.0 to 1.0,',
        '  "size": integer (number of contracts, 1-5),',
        '  "consensus": true or false,',
        '  "dissenter": "agent_name" or null,',
        '  "reasoning": "your executive summary of why this is the right call"',
        "}",
    ])

    return "\n".join(lines)


# -- Exit challenge -----------------------------------------------------

def check_exit_challenge(challenger_name: str, exit_request: dict) -> dict:
    """Build a review prompt when an agent requests EXIT with high confidence.

    Returns empty dict if threshold not met or module disabled.
    """
    if not _ENABLED:
        return {}

    confidence = _safe_float(exit_request.get("confidence"), 0.0)
    if confidence < _EXIT_CHALLENGE_THRESHOLD:
        return {}

    reasoning = str(exit_request.get("reasoning", "(no reason given)"))
    action = str(exit_request.get("action", "EXIT")).upper()

    prompt_lines = [
        "=== EMERGENCY EXIT CHALLENGE ===",
        "",
        f"Agent {challenger_name.upper()} is requesting {action} with "
        f"{confidence:.0%} confidence.",
        "",
        f"Their reasoning: {reasoning}",
        "",
        "Concerns raised:",
    ]

    concerns = exit_request.get("concerns") or []
    if concerns:
        for c in concerns:
            prompt_lines.append(f"  - {c}")
    else:
        prompt_lines.append("  (none specified)")

    prompt_lines.extend([
        "",
        "You must actively OVERRIDE to stay in the position, or AGREE "
        "to exit.",
        "Staying in requires a clear reason why the challenger is wrong.",
        "",
        "Respond ONLY with valid JSON:",
        "{",
        '  "decision": "EXIT" or "OVERRIDE_STAY",',
        '  "confidence": 0.0 to 1.0,',
        '  "reasoning": "why you agree or disagree with the exit request"',
        "}",
    ])

    return {
        "challenger": challenger_name,
        "challenger_confidence": confidence,
        "challenger_reasoning": reasoning,
        "prompt": "\n".join(prompt_lines),
    }


# -- Board management ---------------------------------------------------

def clear_board() -> None:
    """Wipe the message board for a new assessment cycle."""
    if not _ENABLED:
        return
    with _lock:
        _write_board({})


# -- Debate logging -----------------------------------------------------

def log_consensus(result: dict) -> None:
    """Append a consensus record to the debate log."""
    if not _ENABLED or not _LOG_DEBATES:
        return

    entry = {
        "timestamp": _now_iso(),
        "epoch": _now_epoch(),
    }
    entry.update(result)

    with _lock:
        try:
            with open(_DEBATE_LOG_PATH, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    # Post consensus to Slack war room
    try:
        from alerts import slack as _slack
        _slack.war_room_consensus(result)
    except Exception:
        pass


def get_debate_summary(n: int = 10) -> list[dict]:
    """Return last N debate entries from agent_debates.jsonl."""
    try:
        if not _DEBATE_LOG_PATH.exists():
            return []
        lines = _DEBATE_LOG_PATH.read_text().strip().split("\n")
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except (json.JSONDecodeError, ValueError):
                pass
        return entries
    except Exception:
        return []
