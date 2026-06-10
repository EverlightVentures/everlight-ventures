"""browser_use_runner -- DOM-driven browser automation worker.

Sister daemon to desktop_runner. Both poll /AA_MY_DRIVE/_logs/browser_tasks/pending/.
Routing predicate (in desktop_runner._routes_to_browser_use) decides which one
claims each envelope:
  - explicit transport == 'browser_use'   -> this runner
  - explicit transport == 'computer_use'  -> desktop_runner
  - target_url present + no transport     -> this runner (URL-driven default)
  - everything else                       -> desktop_runner

Why DOM-driven over screenshot+click for browsers:
  - 10-30x cheaper (DOM text << 1MB screenshot)
  - Deterministic clicks (element IDs, not coordinate guesses)
  - No coordinate-scaling bugs
  - OAuth flows work because login forms have stable DOM IDs
  - Sonnet 4.5 default is plenty smart for pre-decomposed tasks

Persistent Chromium context lives at /AA_MY_DRIVE/_state/browser_use_chromium/
so cookies/sessions persist across tasks. First-time login per site is manual
(headed Chromium, sign in once); subsequent tasks reuse cookies.

Run modes:
    python3 browser_use_runner.py             -> daemon mode (poll forever)
    python3 browser_use_runner.py --once      -> drain queue once, exit
    python3 browser_use_runner.py --dry-run   -> no LLM call, validate path

Designed for systemd user service:
    ~/.config/systemd/user/lucrex-browser-use-runner.service
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Reuse desktop_runner machinery
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from desktop_runner import (  # type: ignore
    _check_safety,
    _atomic_move,
    _now_iso,
    _load_env,
    _routes_to_browser_use,
    PENDING,
    IN_PROGRESS,
    DONE,
    FAILED,
    SCREENSHOT_ROOT,
)

# Optional: collab_lock for CLI <-> runner turn-taking
try:
    import collab_lock  # type: ignore
except ImportError:
    collab_lock = None

# Optional: context_loader for Rich's memory + aliases injected into agent prompt
try:
    import context_loader  # type: ignore
except ImportError:
    context_loader = None

PERSISTENT_CONTEXT_DIR = Path(os.environ.get(
    "BROWSER_USE_USER_DATA_DIR",
    "/AA_MY_DRIVE/_state/browser_use_chromium"
))
RUNNER_LOG = Path("/AA_MY_DRIVE/_logs/browser_use_runner.log")
POLL_SECONDS = float(os.environ.get("BROWSER_USE_RUNNER_POLL_SECONDS", "10"))
DEFAULT_MODEL = os.environ.get("BROWSER_USE_DEFAULT_MODEL", "claude-sonnet-4-5")

log = logging.getLogger("browser-use-runner")
if not log.handlers:
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(sh)
    try:
        RUNNER_LOG.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(RUNNER_LOG)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except Exception:
        pass
    log.setLevel(logging.INFO)


def _audit(action_type: str, payload: dict) -> None:
    """Best-effort hash-chained audit envelope. Same chain as desktop_agent."""
    try:
        import sys as _s
        _s.path.insert(0, "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance")
        from audit_log import write_envelope  # type: ignore
        write_envelope(agent_id="browser_use_agent", action_type=action_type, payload=payload)
    except Exception:
        pass


def _branded_slack(text: str, channel: str = "#deploy-log",
                   title: str = "browser_use_runner",
                   category: str = "ops") -> None:
    """Try branded_slack; fall back to raw chat.postMessage."""
    try:
        import sys as _s
        _s.path.insert(0, "/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from branded_slack import post_branded_slack  # type: ignore
        post_branded_slack(channel=channel, title=title, summary=text,
                           category=category, agent_name="Browser Use Agent")
        return
    except Exception:
        pass
    # Fallback: raw chat.postMessage
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel, "text": text}).encode(),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json; charset=utf-8"},
        )
        urllib.request.urlopen(req, timeout=6).read()
    except Exception:
        pass


def _load_persona_firmware(persona: str) -> str:
    """Read agent .md firmware to inject voice/style. Returns short snippet."""
    if not persona:
        return ""
    # Try common persona name patterns: "Piper Reeves" -> piper_reeves.md
    slug = persona.lower().replace(" ", "_")
    candidates = [
        Path(f"/AA_MY_DRIVE/.claude/agents/{slug}.md"),
        Path(f"/AA_MY_DRIVE/.claude/agents/state_{slug}.md"),
        Path(f"/AA_MY_DRIVE/.claude/agents/legal_{slug}.md"),
    ]
    for p in candidates:
        if p.exists():
            text = p.read_text(encoding="utf-8", errors="replace")
            # Pull just speech/voice section if present
            for marker in ("## Firmware", "## Speech", "## Personality"):
                if marker in text:
                    block = text.split(marker, 1)[1]
                    block = block.split("\n## ", 1)[0]
                    return f"\nDISPATCHED BY {persona} -- adopt their voice in narration:\n{marker}{block[:1200]}"
            return f"\nDISPATCHED BY {persona}\n{text[:800]}"
    return f"\nDISPATCHED BY {persona} (no firmware file found, narrate generically)"


def _build_extend_system_message(envelope: dict) -> str:
    """Compose the extend_system_message: voice rules + persona + Rich's
    operational context (cached for cost). browser-use prepends its own
    system prompt; ours extends it."""
    parts = []
    parts.append(
        "<EVERLIGHT_VOICE_RULES>\n"
        "* Never use em-dash (the `--` character pair only).\n"
        "* HTML over Markdown for any structured output.\n"
        "* Verify before claiming -- read state via DOM extraction before reporting success.\n"
        "* Terse: 'logged in, captured key' beats 'I successfully completed the login process and then proceeded to capture'.\n"
        "* When task complete, end with a JSON code block of captured values.\n"
        "* Never delete user data, never click 'Delete' / 'Remove' / 'Cancel subscription' unless task explicitly says.\n"
        "* If 2FA / SMS / passkey appears, end with text 'BLOCKED_2FA' (no JSON).\n"
        "</EVERLIGHT_VOICE_RULES>"
    )
    # Persona firmware
    persona = (envelope.get("context") or {}).get("persona", "")
    if persona:
        parts.append(_load_persona_firmware(persona))
    # Operational context (Rich's memory + aliases + recent state)
    if context_loader is not None:
        try:
            parts.append(context_loader.build_operational_context(
                include_blinko=False,  # Oracle E5 dead per memory
                include_manifest_excerpt=False,  # save tokens, not browser-relevant
            ))
        except Exception as e:
            log.warning("context_loader failed (non-fatal): %s", e)
    # Envelope context fields
    ctx = envelope.get("context") or {}
    if ctx.get("conversation_summary"):
        parts.append(f"\nWHY THIS TASK MATTERS:\n{ctx['conversation_summary']}")
    if ctx.get("success_criteria"):
        parts.append("\nSUCCESS CRITERIA (verify each before declaring done):")
        for c in ctx["success_criteria"]:
            parts.append(f"  - {c}")
    if ctx.get("do_not"):
        parts.append("\nABSOLUTELY DO NOT:")
        for d in ctx["do_not"]:
            parts.append(f"  - {d}")
    return "\n".join(parts)


def _make_step_callback(task_id: str):
    """Returns a sync callback fired after each agent step. Yields to
    collab_lock if CLI is asking the user a question, and writes audit."""
    def cb(state, output, step_num):
        # Collab lock check -- pause if CLI grabbed the floor
        if collab_lock is not None and collab_lock.is_paused_for_cli():
            log.info("collab_lock=cli_active -- yielding step %d to CLI", step_num)
            collab_lock.wait_until_clear(max_wait=600.0, poll=1.5)
            log.info("collab_lock cleared -- resuming step %d", step_num)
        # Audit each step
        try:
            url = getattr(state, "url", "") if state else ""
            actions_summary = ""
            if output and hasattr(output, "action"):
                actions_summary = str(output.action)[:200]
            _audit("browser_use.step", {
                "task_id": task_id,
                "step": step_num,
                "url": url[:200],
                "actions": actions_summary,
            })
        except Exception as e:
            log.debug("audit step %d failed: %s", step_num, e)
    return cb


async def _run_browser_task(envelope: dict, *, dry_run: bool = False) -> dict:
    """Run a single envelope through browser-use. Returns result dict."""
    task_id = envelope["task_id"]
    api_key = (os.environ.get("LUCREX_ANTHROPIC_KEY")
               or os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key:
        return {"status": "failed", "error": "no LUCREX_ANTHROPIC_KEY/ANTHROPIC_API_KEY"}

    model = envelope.get("model_override") or DEFAULT_MODEL
    target_url = envelope.get("target_url")
    goal = envelope["natural_language_goal"]

    # Compose the task: include target URL prominently if provided
    task_str = goal
    if target_url:
        task_str = f"Navigate to {target_url} and then: {goal}"

    started_at = time.time()
    _audit("browser_use.task.started", {
        "task_id": task_id,
        "model": model,
        "target_url": target_url,
        "goal_preview": goal[:200],
    })

    if dry_run:
        return {
            "status": "done",
            "iterations": 0,
            "elapsed_seconds": 0.0,
            "final_text": "DRY_RUN: would have run browser-use Agent",
            "model": model,
        }

    # Lazy imports so the module loads even if browser-use isn't installed
    try:
        from browser_use import Agent, Browser, ChatAnthropic  # type: ignore
    except ImportError as e:
        return {"status": "failed",
                "error": f"browser-use not installed: {e}",
                "hint": "/AA_MY_DRIVE/.venv/bin/pip install browser-use && playwright install chromium"}

    PERSISTENT_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    sshots_dir = SCREENSHOT_ROOT / task_id
    sshots_dir.mkdir(parents=True, exist_ok=True)

    llm = ChatAnthropic(model=model, api_key=api_key, max_tokens=4096)
    browser = Browser(
        headless=False,  # so Rich can see and the cooperative-brake is live
        user_data_dir=str(PERSISTENT_CONTEXT_DIR),
        wait_between_actions=0.5,
        accept_downloads=False,
        disable_security=False,
    )
    extend_msg = _build_extend_system_message(envelope)

    agent = Agent(
        task=task_str,
        llm=llm,
        browser=browser,
        extend_system_message=extend_msg,
        max_actions_per_step=4,
        max_failures=3,
        step_timeout=int(envelope.get("max_seconds", 300)),
        save_conversation_path=str(sshots_dir / "conversation.jsonl"),
        register_new_step_callback=_make_step_callback(task_id),
        task_id=task_id,
        calculate_cost=True,
    )

    final_text = ""
    iterations = 0
    status = "in_progress"
    abort_reason: Optional[str] = None
    final_screenshot: Optional[str] = None

    try:
        max_iters = envelope.get("max_iterations", 30)
        history = await agent.run(max_steps=max_iters)
        # AgentHistoryList has methods like .final_result(), .urls(), .errors()
        try:
            final_text = history.final_result() or ""
        except Exception:
            final_text = ""
        try:
            iterations = len(history.history) if hasattr(history, "history") else 0
        except Exception:
            iterations = 0
        try:
            errors = history.errors() if hasattr(history, "errors") else []
            errors = [e for e in errors if e]
        except Exception:
            errors = []
        if errors:
            status = "failed"
            abort_reason = "; ".join(str(e)[:120] for e in errors[:3])
        else:
            status = "done"
        # Final screenshot via the browser's current page
        try:
            page = await browser.get_current_page() if hasattr(browser, "get_current_page") else None
            if page is not None:
                shot_path = sshots_dir / "99_final.png"
                await page.screenshot(path=str(shot_path), full_page=False)
                final_screenshot = str(shot_path)
        except Exception as e:
            log.debug("final screenshot failed: %s", e)
    except Exception as e:
        log.exception("agent.run() crashed for %s", task_id)
        status = "failed"
        abort_reason = f"crash: {e}"
    finally:
        try:
            await browser.close() if hasattr(browser, "close") else None
        except Exception:
            pass

    elapsed = round(time.time() - started_at, 2)
    _audit("browser_use.task.completed", {
        "task_id": task_id,
        "status": status,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "abort_reason": abort_reason,
    })

    return {
        "status": status,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "final_text": final_text[:5000],
        "final_screenshot": final_screenshot,
        "abort_reason": abort_reason,
        "model": model,
    }


def process_envelope(envelope_path: Path, *, dry_run: bool = False) -> dict:
    """Process a single envelope. Returns the updated dict."""
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    task_id = envelope["task_id"]

    # Routing predicate -- skip if not ours
    if not _routes_to_browser_use(envelope):
        log.debug("skipped %s (not routed to browser_use)", task_id)
        return envelope

    log.info("Processing %s: %s", task_id, envelope.get("title"))

    # Safety pre-flight
    ok, reason = _check_safety(envelope)
    if not ok:
        envelope["status"] = "failed"
        envelope["completed_at"] = _now_iso()
        envelope["result"] = {"error": "safety_check_failed", "reason": reason}
        return envelope

    # Move to in_progress
    envelope["status"] = "in_progress"
    envelope["started_at"] = _now_iso()
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    moved = _atomic_move(envelope_path, IN_PROGRESS)

    _branded_slack(
        f":globe_with_meridians: browser_use_runner picked up `{task_id}`: {envelope.get('title','(no title)')}",
        channel=envelope.get("callback_slack_channel", "#deploy-log"),
        title="Browser task dispatched",
        category="ops",
    )

    try:
        result = asyncio.run(_run_browser_task(envelope, dry_run=dry_run))
    except Exception as e:
        log.exception("_run_browser_task crashed")
        result = {"status": "failed", "error": f"runner_crash: {e}"}

    envelope["result"] = result
    envelope["completed_at"] = _now_iso()
    envelope["status"] = "done" if result.get("status") == "done" else "failed"

    moved.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    final = _atomic_move(moved, DONE if envelope["status"] == "done" else FAILED)

    # SCREENSHOT SECURITY: auto-delete task's screenshot dir + conversation
    # jsonl after envelope persists. browser-use captures DOM rather than full
    # screenshots but still saves a final png + the conversation trace which
    # may include captured values. Per feedback_screenshot_security.md.
    if not envelope.get("safety", {}).get("keep_screenshots", False):
        import shutil as _shutil
        sshots_dir = SCREENSHOT_ROOT / task_id
        try:
            if sshots_dir.exists():
                _shutil.rmtree(sshots_dir)
                log.info("auto-deleted screenshots dir %s (sensitive)", sshots_dir)
        except Exception as e:
            log.warning("failed to delete screenshots dir %s: %s", sshots_dir, e)

    summary = (
        f"{':white_check_mark:' if envelope['status'] == 'done' else ':x:'} "
        f"`{task_id}` -> {envelope['status']} after {result.get('iterations', 0)} steps "
        f"({result.get('elapsed_seconds', '?')}s, model={result.get('model','?')}). Final: {final.name}"
    )
    _branded_slack(summary,
                   channel=envelope.get("callback_slack_channel", "#deploy-log"),
                   title="Browser task completed",
                   category="report" if envelope["status"] == "done" else "alert")
    log.info(summary)
    return envelope


def drain_once(*, dry_run: bool = False) -> int:
    PENDING.mkdir(parents=True, exist_ok=True)
    files = sorted(PENDING.glob("*.json"))
    if not files:
        return 0
    n = 0
    for f in files:
        try:
            envelope = json.loads(f.read_text(encoding="utf-8"))
            if not _routes_to_browser_use(envelope):
                continue  # leave for desktop_runner
            process_envelope(f, dry_run=dry_run)
            n += 1
        except Exception as e:
            log.exception("envelope handler crashed for %s: %s", f, e)
    return n


def daemon_loop(*, poll_seconds: float = POLL_SECONDS, dry_run: bool = False) -> None:
    log.info("browser-use-runner starting -- poll=%ss dry_run=%s default_model=%s",
             poll_seconds, dry_run, DEFAULT_MODEL)
    log.info("persistent context: %s", PERSISTENT_CONTEXT_DIR)
    _load_env()
    while True:
        try:
            n = drain_once(dry_run=dry_run)
            if n:
                log.info("processed %d task(s)", n)
        except Exception as e:
            log.exception("loop error (continuing): %s", e)
        time.sleep(poll_seconds)


def _cli() -> int:
    p = argparse.ArgumentParser(description="Browser-use runner for browser tasks")
    p.add_argument("--once", action="store_true", help="Drain queue once and exit")
    p.add_argument("--dry-run", action="store_true", help="No LLM call, validate path only")
    p.add_argument("--poll", type=float, default=POLL_SECONDS)
    args = p.parse_args()

    _load_env()

    if args.once:
        n = drain_once(dry_run=args.dry_run)
        print(f"processed {n} task(s)")
        return 0

    daemon_loop(poll_seconds=args.poll, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
