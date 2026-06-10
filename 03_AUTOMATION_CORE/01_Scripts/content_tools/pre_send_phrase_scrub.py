"""pre_send_phrase_scrub -- Justine's last-mile compliance gate.

Why this exists
---------------
Justine flagged that OH (and soon GA/TX/FL) outbound has phrases that, if they
slip through, cross into unauthorized-brokerage / agent-representation territory.
ORC 4735.02 exposure. A manual checklist is not enough -- humans miss it. This
runs as a code-level pre-send check on every chokepoint:

  - branded_mailer.send_branded_email()  (every email outbound)
  - lob_mail_sender.send_yellow_letter()  (every direct-mail outbound)

Source of truth
---------------
For OH: parsed from Section (f) of
  /home/opc/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/legal/
    HIVE_OPINION_OH_EQUITABLE_INTEREST.md
  (or the local workspace path if running on the phone)

For other states: a basic shared list of agent-representation language. Each
state appendix can extend this dict as it lands. State key is uppercase
2-letter postal code.

Public API
----------
    from pre_send_phrase_scrub import validate_outbound, ValidationResult

    result = validate_outbound(text, state="OH")
    if not result.ok:
        log.warning("phrase_scrub blocked: %s", result.blocked_phrases)

Logging
-------
Every block writes one line to /home/opc/_logs/phrase_scrub_blocks.jsonl
(falls back to ./_logs/ if /home/opc not writable -- phone case).
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("phrase_scrub")


# ---------------------------------------------------------------------------
# Source-of-truth paths
# ---------------------------------------------------------------------------

_OH_OPINION_CANDIDATES = [
    Path("/home/opc/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/legal/HIVE_OPINION_OH_EQUITABLE_INTEREST.md"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/legal/HIVE_OPINION_OH_EQUITABLE_INTEREST.md"),
]

_LOG_CANDIDATES = [
    Path("/home/opc/_logs/phrase_scrub_blocks.jsonl"),
    Path("./_logs/phrase_scrub_blocks.jsonl"),
]


# ---------------------------------------------------------------------------
# Default per-state lists. OH is parsed from the opinion file on first call.
# Everything else falls back to a shared baseline of agent-representation words.
# ---------------------------------------------------------------------------

_DEFAULT_BASELINE = [
    "list",
    "listing",
    "represent",
    "your agent",
    "your broker",
    "commission",
    "REALTOR",
    "MLS",
    "fiduciary",
    "act on your behalf",
]

# Module-level cache. First call to validate_outbound parses OH from disk.
STATE_FORBIDDEN_PHRASES: dict[str, list[str]] = {
    "OH": [],  # populated on first call from the opinion file
    "_DEFAULT": list(_DEFAULT_BASELINE),
    # Future state appendices land here, e.g.:
    # "GA": [...],
    # "TX": [...],
    # "FL": [...],
}

_OH_PARSED = False


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_oh_section_f(md_text: str) -> list[str]:
    """Pull bullet phrases out of Section (f).

    The section uses quoted phrases like:
        - "I will list your property" / "list with me" / "list your home"
    We capture every double-quoted span inside the section block, dedupe,
    and trim. Anything not in quotes (commentary lines) is ignored.
    """
    # Locate Section f -- header is exactly: "## f. Required Language ... MUST NOT Contain"
    m = re.search(
        r"^##\s*f\.\s*Required Language[^\n]*MUST NOT Contain\s*\n(.*?)(?=^##\s|\Z)",
        md_text,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []

    block = m.group(1)
    # Capture every double-quoted span. Use a non-greedy match.
    quoted = re.findall(r'"([^"\n]+?)"', block)
    out: list[str] = []
    seen: set[str] = set()
    for q in quoted:
        s = q.strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _ensure_oh_loaded() -> None:
    global _OH_PARSED
    if _OH_PARSED:
        return
    for path in _OH_OPINION_CANDIDATES:
        try:
            if path.exists():
                txt = path.read_text(encoding="utf-8")
                phrases = _parse_oh_section_f(txt)
                if phrases:
                    STATE_FORBIDDEN_PHRASES["OH"] = phrases
                    log.info("phrase_scrub loaded %d OH phrases from %s",
                             len(phrases), path)
                    _OH_PARSED = True
                    return
        except Exception as exc:
            log.warning("phrase_scrub: failed to read %s: %s", path, exc)
    # Fallback: use baseline if the opinion file is missing.
    STATE_FORBIDDEN_PHRASES["OH"] = list(_DEFAULT_BASELINE)
    _OH_PARSED = True
    log.warning("phrase_scrub: HIVE_OPINION_OH_EQUITABLE_INTEREST.md not found; "
                "using baseline list for OH")


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    ok: bool
    blocked_phrases: list[str] = field(default_factory=list)
    reason: str = ""
    matches: list[dict] = field(default_factory=list)  # phrase + position + snippet

    def as_tuple(self) -> tuple[bool, list[str], str]:
        return (self.ok, self.blocked_phrases, self.reason)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def _word_boundary_pattern(phrase: str) -> re.Pattern:
    """Build a case-insensitive word-boundary regex for a phrase.

    For multi-word phrases we collapse internal whitespace to \\s+ so
    "list with me" matches "list   with\nme" too.

    For single-word phrases we anchor with \\b on both sides so that
    "list" does NOT match inside "listing".
    """
    parts = [re.escape(tok) for tok in phrase.strip().split()]
    body = r"\s+".join(parts) if len(parts) > 1 else parts[0]
    return re.compile(rf"\b{body}\b", flags=re.IGNORECASE)


def _strip_html_to_text(text: str) -> str:
    """Strip HTML tags so phrase scan runs on visible content only."""
    if "<" not in text:
        return text
    # Drop script/style blocks first
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text,
                     flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return cleaned


def validate_outbound(
    text: str,
    state: str,
    *,
    channel: str = "email",
    recipient: Optional[str] = None,
    extra_phrases: Optional[list[str]] = None,
) -> ValidationResult:
    """Scan merged outbound text for forbidden phrases for the given state.

    Args:
        text:           merged final body. HTML or plain. Tokens already substituted.
        state:          recipient state (uppercase 2-letter postal). Empty -> baseline.
        channel:        "email" / "mail" / "sms" -- for log fields, no rule branching.
        recipient:      optional recipient identifier for the log entry.
        extra_phrases:  optional caller-supplied list to merge in for this call only.

    Returns ValidationResult. ok=True means safe to send.
    Logs every block to phrase_scrub_blocks.jsonl.
    """
    _ensure_oh_loaded()

    if not text:
        return ValidationResult(ok=True, reason="empty_text")

    state_key = (state or "").strip().upper()
    phrases: list[str] = []
    if state_key and state_key in STATE_FORBIDDEN_PHRASES and state_key != "_DEFAULT":
        # State-specific list inherits the baseline. The baseline is
        # the agent-representation/brokerage trap that applies everywhere;
        # state appendices add the state-law-specific phrases on top.
        phrases.extend(STATE_FORBIDDEN_PHRASES[state_key])
        phrases.extend(STATE_FORBIDDEN_PHRASES["_DEFAULT"])
    else:
        phrases.extend(STATE_FORBIDDEN_PHRASES["_DEFAULT"])
    if extra_phrases:
        phrases.extend(extra_phrases)

    # Dedupe while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for p in phrases:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(p)

    haystack = _strip_html_to_text(text)

    blocked: list[str] = []
    matches: list[dict] = []
    for phrase in deduped:
        try:
            pat = _word_boundary_pattern(phrase)
        except re.error:
            continue
        m = pat.search(haystack)
        if m:
            blocked.append(phrase)
            start = max(0, m.start() - 30)
            end = min(len(haystack), m.end() + 30)
            snippet = haystack[start:end].replace("\n", " ").strip()
            matches.append({
                "phrase": phrase,
                "start": m.start(),
                "end": m.end(),
                "snippet": snippet,
            })

    if blocked:
        reason = f"phrase_scrub_blocked: {blocked[0]}"
        result = ValidationResult(
            ok=False,
            blocked_phrases=blocked,
            reason=reason,
            matches=matches,
        )
        _log_block(
            state=state_key,
            channel=channel,
            recipient=recipient or "",
            blocked=blocked,
            matches=matches,
        )
        return result

    return ValidationResult(ok=True, reason="clean")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log_block(
    *,
    state: str,
    channel: str,
    recipient: str,
    blocked: list[str],
    matches: list[dict],
) -> None:
    """Append one JSONL line per blocked send."""
    for path in _LOG_CANDIDATES:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                for m in matches:
                    f.write(json.dumps({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "channel": channel,
                        "recipient_state": state,
                        "recipient": recipient,
                        "blocked_phrase": m["phrase"],
                        "position": m["start"],
                        "snippet": m["snippet"],
                        "all_blocked": blocked,
                    }) + "\n")
            return
        except Exception as exc:
            log.warning("phrase_scrub: failed to write log to %s: %s", path, exc)
            continue


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="phrase scrub smoke test")
    ap.add_argument("--state", default="OH")
    ap.add_argument("--text", default="Hi John, I will list your property fast.")
    args = ap.parse_args()
    res = validate_outbound(args.text, state=args.state, channel="cli")
    print(json.dumps({
        "ok": res.ok,
        "blocked_phrases": res.blocked_phrases,
        "reason": res.reason,
        "matches": res.matches,
    }, indent=2))
    return 0 if res.ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
