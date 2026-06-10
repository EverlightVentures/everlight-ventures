"""desktop_runner -- polling worker that drains the browser-task queue.

Watches /AA_MY_DRIVE/_logs/browser_tasks/pending/ for new task envelopes.
For each envelope:
  1. Atomic-move pending/{id}.json -> in_progress/{id}.json
  2. Mark started_at, status=in_progress
  3. Call desktop_agent.run_task() with the natural_language_goal
  4. Update envelope with result, completed_at, status (done|failed|aborted)
  5. Atomic-move in_progress/{id}.json -> done/ or failed/
  6. Post Slack #deploy-log update via branded_slack (best effort)

Run modes:
  python3 desktop_runner.py             -> daemon mode (poll forever)
  python3 desktop_runner.py --once      -> drain queue once, exit
  python3 desktop_runner.py --dry-run   -> log actions without executing

Designed for systemd user service:
    ~/.config/systemd/user/desktop-runner.service
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make desktop_agent importable
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from desktop_agent import run_task  # type: ignore
from screen_inhibitor import ScreenInhibitor  # type: ignore

ROOT = Path("/AA_MY_DRIVE/_logs/browser_tasks")
PENDING = ROOT / "pending"
IN_PROGRESS = ROOT / "in_progress"
DONE = ROOT / "done"
FAILED = ROOT / "failed"
SCREENSHOT_ROOT = ROOT / "screenshots"
RUNNER_LOG = Path("/AA_MY_DRIVE/_logs/desktop_runner.log")

POLL_SECONDS = float(os.environ.get("DESKTOP_RUNNER_POLL_SECONDS", "10"))

log = logging.getLogger("desktop-runner")
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slack_post(text: str, channel: str = "#deploy-log") -> None:
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


def _atomic_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.move(str(src), str(dst))
    return dst


def _load_env() -> None:
    """Source /AA_MY_DRIVE/.env into os.environ if not already loaded."""
    p = Path("/AA_MY_DRIVE/.env")
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def _check_safety(envelope: dict) -> tuple[bool, str]:
    """Run pre-flight safety checks. Returns (ok, reason)."""
    safety = envelope.get("safety", {})
    if safety.get("honor_outbound_halt", True):
        if os.environ.get("WHOLESALE_OUTBOUND_HALT", "").lower() in ("1", "true", "yes"):
            goal = (envelope.get("natural_language_goal") or "").lower()
            # Block tasks that would send mail or initiate outbound campaigns
            if any(s in goal for s in ("send email", "send the email", "send a campaign",
                                        "blast", "send outreach", "fire off email")):
                return False, "outbound_halt_active"
    prohibited = [u.lower() for u in safety.get("prohibited_urls", [])]
    goal_lower = (envelope.get("natural_language_goal") or "").lower()
    for u in prohibited:
        token = u.replace("*", "")
        if token and token in goal_lower:
            return False, f"prohibited_url_referenced:{token}"
    return True, "ok"


def _routes_to_browser_use(envelope: dict) -> bool:
    """Returns True if this envelope should be claimed by browser_use_runner,
    not desktop_runner. Single queue, two transports.

    Routing rules:
      - explicit transport == 'browser_use'   -> browser_use
      - explicit transport == 'computer_use'  -> desktop_runner (this one)
      - target_url present + no transport     -> browser_use (URL-driven default)
      - everything else                        -> desktop_runner
    """
    transport = envelope.get("transport")
    if transport == "browser_use":
        return True
    if transport == "computer_use":
        return False
    if envelope.get("target_url"):
        return True
    return False


def process_envelope(envelope_path: Path, *, dry_run: bool = False) -> dict:
    """Process a single task envelope. Returns the updated envelope dict.
    If the envelope is routed to browser_use, leaves it in pending/ untouched."""
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    task_id = envelope["task_id"]

    # Routing predicate -- skip browser_use envelopes (browser_use_runner claims those)
    if _routes_to_browser_use(envelope):
        log.info("skipped %s (routed to browser_use)", task_id)
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

    _slack_post(f":robot_face: desktop_runner picked up `{task_id}`: {envelope.get('title')}",
                channel=envelope.get("callback_slack_channel", "#deploy-log"))

    # Run the agent inside a screen-inhibitor (KDE Plasma 6 Wayland goes idle and
    # spectacle returns 32KB bilevel screenshots otherwise -- v2 fix).
    sshots = SCREENSHOT_ROOT / task_id
    max_secs = envelope.get("max_seconds", 300)
    try:
        with ScreenInhibitor(reason=f"browser-task {task_id}",
                             max_seconds=max_secs) as inh_state:
            if inh_state.locked_at_start:
                log.warning("screen LOCKED at dispatch -- refusing %s", task_id)
                result = {
                    "status": "failed",
                    "error": "screen_locked_at_dispatch",
                    "steps": [],
                    "abort_reason": "screen was locked when runner picked up the task; "
                                    "unlock and re-queue the envelope to retry",
                }
            else:
                # Per-envelope model_override overrides DEFAULT_MODEL.
                # Allows Sonnet 4.5 default with Opus 4.7 / Haiku 4.5 escape hatch.
                from desktop_agent import DEFAULT_MODEL  # type: ignore
                model = envelope.get("model_override") or DEFAULT_MODEL
                result = run_task(
                    task=envelope["natural_language_goal"],
                    screenshots_dir=sshots,
                    max_iterations=envelope.get("max_iterations", 30),
                    max_seconds=max_secs,
                    abort_on_human_override=envelope.get("safety", {}).get("abort_on_human_override", True),
                    dry_run=dry_run,
                    context=envelope.get("context"),
                    model=model,
                )
    except Exception as e:
        log.exception("run_task crashed for %s", task_id)
        result = {"status": "failed", "error": f"crash: {e}", "steps": []}

    # Update envelope and file in correct sink
    envelope["result"] = result
    envelope["completed_at"] = _now_iso()
    envelope["status"] = "done" if result.get("status") == "done" else "failed"

    # Re-write current location with final state
    moved.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    if envelope["status"] == "done":
        final = _atomic_move(moved, DONE)
    else:
        final = _atomic_move(moved, FAILED)

    # SCREENSHOT SECURITY: delete the task's screenshot dir.
    # Pixels can capture API keys, OTPs, .env contents, terminal history. Per
    # feedback_screenshot_security.md: "if a human (or AI) outside this Claude
    # session can see the pixel, treat the data as exfiltrated." Audit envelope
    # already has the action trail; no need to keep raw images.
    if not envelope.get("safety", {}).get("keep_screenshots", False):
        import shutil as _shutil
        try:
            if sshots.exists():
                _shutil.rmtree(sshots)
                log.info("auto-deleted screenshots dir %s (sensitive)", sshots)
        except Exception as e:
            log.warning("failed to delete screenshots dir %s: %s", sshots, e)

    summary = (
        f"{':white_check_mark:' if envelope['status'] == 'done' else ':x:'} "
        f"`{task_id}` -> {envelope['status']} after {result.get('iterations',0)} steps "
        f"({result.get('elapsed_seconds','?')}s). Final: {final.name}"
    )
    _slack_post(summary, channel=envelope.get("callback_slack_channel", "#deploy-log"))
    log.info(summary)
    return envelope


def drain_once(*, dry_run: bool = False) -> int:
    """Process all pending envelopes once. Returns count processed."""
    PENDING.mkdir(parents=True, exist_ok=True)
    files = sorted(PENDING.glob("*.json"))
    if not files:
        return 0
    n = 0
    for f in files:
        try:
            process_envelope(f, dry_run=dry_run)
            n += 1
        except Exception as e:
            log.exception("envelope handler crashed for %s: %s", f, e)
    return n


def daemon_loop(*, poll_seconds: float = POLL_SECONDS, dry_run: bool = False) -> None:
    """Run forever, polling every poll_seconds. Sigterm-safe."""
    log.info("desktop-runner starting -- poll=%ss dry_run=%s", poll_seconds, dry_run)
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
    p = argparse.ArgumentParser(description="Desktop runner for browser tasks")
    p.add_argument("--once", action="store_true", help="Drain queue once and exit")
    p.add_argument("--dry-run", action="store_true", help="Log actions without executing")
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
