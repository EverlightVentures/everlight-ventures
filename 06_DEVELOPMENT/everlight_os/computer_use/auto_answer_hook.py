"""auto_answer_hook -- decide answers to AskUserQuestion prompts in <2s.

CORRECTED v2 (2026-05-07): uses Claude Code's official auto-answer schema
per https://code.claude.com/docs/en/hooks:
  - permissionDecision: "allow" tells Claude Code to SKIP the prompt
  - updatedInput.answers maps question text -> chosen label
  - Claude Code never shows the picker; tool returns the answer directly

The previous v1 wrote to a file + relied on a separate xdotool watcher to
type into the focused window. That worked unreliably on Wayland (focus
issues) and required a daemon. This v2 is direct -- the hook IS the answer.

Picker logic (in priority order):
  1. If /tmp/lucrex_auto_answer.disable exists, return permissionDecision:
     "ask" (single-shot disable; deletes the file).
  2. Heuristic: if any option label contains "(Recommended)", pick it.
  3. LLM (Haiku 4.5) with Rich's feedback memories as context.
  4. Fallback: index 0.

Per Rich's directive (2026-05-07): "the workflow doesn't stall waiting on
you" -- but ALSO "we need to use claude as a partner, not get cut off."
This hook makes the partnership work: CLI asks, hook answers, no
interruption.

Override: `touch /tmp/lucrex_auto_answer.disable` BEFORE submitting your
prompt. Auto-answer will skip ONE round.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

DISABLE_PATH = Path("/tmp/lucrex_auto_answer.disable")
LOG_PATH = Path("/tmp/lucrex_auto_answer.log")
ANSWER_PATH = Path("/tmp/lucrex_auto_answer.json")  # diagnostic only
MEMORY_DIR = Path.home() / ".claude/projects/-AA-MY-DRIVE/memory"


def _log(msg: str) -> None:
    try:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _load_memories(max_files: int = 4) -> str:
    targets = ("feedback_autonomous", "feedback_capture",
               "feedback_compliance_cleared", "feedback_workflow",
               "feedback_trust_the_setup")
    parts = []
    for f in MEMORY_DIR.glob("*.md"):
        if any(t in f.name for t in targets):
            try:
                parts.append(f"### {f.name}\n{f.read_text(encoding='utf-8')[:1000]}")
            except Exception:
                continue
        if len(parts) >= max_files:
            break
    return "\n\n".join(parts)


def _pick_recommended(options: list[dict]) -> int | None:
    for i, opt in enumerate(options):
        label = (opt.get("label") or "").lower()
        if "recommend" in label:
            return i
    return None


def _llm_pick(question_text: str, options: list[dict],
              header: str, multi_select: bool) -> dict:
    api_key = (os.environ.get("LUCREX_ANTHROPIC_KEY")
               or os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key:
        return {"choice_index": 0, "reasoning": "no API key, defaulting to first option"}
    try:
        from anthropic import Anthropic
    except ImportError:
        return {"choice_index": 0, "reasoning": "anthropic SDK missing"}

    client = Anthropic(api_key=api_key)
    options_block = "\n".join(
        f"  [{i}] {o.get('label', '?')} -- {o.get('description', '')[:200]}"
        for i, o in enumerate(options)
    )
    memories = _load_memories()
    system = (
        "You are Rich Gee's auto-answerer for Claude CLI. CLI asked Rich a "
        "1/2/3 choice; you pick the one Rich would pick, in <2 seconds. "
        "Rules in priority order:\n"
        "1. If an option label contains '(Recommended)', pick it.\n"
        "2. Default to AUTONOMOUS ACTION over manual intervention.\n"
        "3. Default to CAPTURE > decline; first-option = lock-down.\n"
        "4. If compliance-cleared, ship; don't re-ask for sign-off.\n"
        "5. If genuinely high-stakes / irreversible (delete data, send "
        "outbound during halt, financial commitment), DEFER -- pick the "
        "option that lets Rich live-answer.\n\n"
        "Output ONLY a JSON object: "
        "{\"choice_index\": <int>, \"reasoning\": \"<one sentence>\"}.\n\n"
        "RICH'S FEEDBACK MEMORIES (selected):\n" + memories
    )
    user_msg = (
        f"Question header: {header}\n"
        f"Question: {question_text}\n"
        f"Multi-select: {multi_select}\n"
        f"Options:\n{options_block}\n\n"
        f"Pick the index Rich would pick."
    )
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = r.content[0].text.strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            obj = json.loads(text[start:end + 1])
            ci = int(obj.get("choice_index", 0))
            if 0 <= ci < len(options):
                return obj
    except Exception as e:
        _log(f"LLM error: {e}")
    return {"choice_index": 0, "reasoning": "LLM failed, default to first"}


def _decide(question: dict) -> tuple[int, dict]:
    """Returns (choice_index, decision_meta)."""
    options = question.get("options") or []
    if not options:
        return (0, {"reasoning": "no options", "method": "default"})

    rec = _pick_recommended(options)
    if rec is not None:
        return (rec, {"reasoning": "matched (Recommended) label",
                      "method": "heuristic"})

    pick = _llm_pick(
        question_text=question.get("question", ""),
        options=options,
        header=question.get("header", ""),
        multi_select=question.get("multiSelect", False),
    )
    return (pick["choice_index"], {"reasoning": pick.get("reasoning", ""),
                                    "method": "llm_haiku"})


def _emit(payload: dict) -> None:
    """Write hookSpecificOutput JSON to stdout (Claude Code's protocol)."""
    print(json.dumps(payload))


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except Exception as e:
        _log(f"stdin parse failed: {e}")
        return 0

    # Single-shot disable check
    if DISABLE_PATH.exists():
        _log("auto-answer DISABLED for this round (override file present)")
        try:
            DISABLE_PATH.unlink()
        except Exception:
            pass
        # Don't auto-answer; let Claude Code show the picker normally
        return 0

    tool_input = hook_input.get("tool_input", hook_input.get("toolInput", {}))
    questions = tool_input.get("questions") or []
    if not questions:
        _log("no questions in hook input")
        return 0

    # Build answers map: question_text -> chosen_label
    answers: dict[str, str] = {}
    decisions = []
    for q in questions:
        q_text = q.get("question", "")
        options = q.get("options", [])
        ci, meta = _decide(q)
        chosen_label = options[ci].get("label", "?") if 0 <= ci < len(options) else "?"
        answers[q_text] = chosen_label
        decisions.append({
            "question": q_text[:120],
            "chosen_index": ci,
            "chosen_label": chosen_label,
            "method": meta.get("method"),
            "reasoning": meta.get("reasoning"),
        })

    # Write diagnostic file (so we can see what happened)
    try:
        ANSWER_PATH.write_text(json.dumps({
            "ts": time.time(),
            "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "decisions": decisions,
        }, indent=2), encoding="utf-8")
    except Exception:
        pass
    _log("auto-answered: " + " | ".join(
        f"[{d['chosen_index']}] '{d['chosen_label']}' ({d['method']})"
        for d in decisions
    ))

    # Emit Claude Code's auto-answer schema:
    # permissionDecision=allow + updatedInput with answers map.
    # Per https://code.claude.com/docs/en/hooks
    updated_input = {
        "questions": questions,
        "answers": answers,
    }
    _emit({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": updated_input,
            "permissionDecisionReason": (
                "Lucrex auto-answer: "
                + ", ".join(f"{d['method']}->{d['chosen_label']}" for d in decisions)
                + ". Override next round: touch /tmp/lucrex_auto_answer.disable"
            ),
        }
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
