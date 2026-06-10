"""managed_agent_runner -- third transport: cloud-hosted Anthropic Managed Agents.

Anthropic's Managed Agents (beta header `managed-agents-2026-04-01`) provides
a fully-managed agent harness: bash + file ops + web search + MCP, running in
a sandboxed cloud container. Best for long-running async tasks that don't
need to touch Rich's actual desktop.

Routing: envelopes with `transport: "managed_agent"` get claimed here.
Examples:
  - "Generate a 1000-row CSV of mock leads with realistic data"
  - "Research the latest Cloudflare DNS API changes and summarize"
  - "Write a Python script that ingests this PDF and produces summary stats"
  - Tasks where compute_use (screen) and browser_use (browser) are overkill.

Same envelope schema, same audit chain, same branded Slack reporting.

Beta status (May 2026): public beta, available to all API accounts. No request
needed. The Anthropic SDK auto-includes the beta header.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from desktop_runner import (  # type: ignore
    _check_safety,
    _atomic_move,
    _now_iso,
    _load_env,
    PENDING,
    IN_PROGRESS,
    DONE,
    FAILED,
)

try:
    import collab_lock  # type: ignore
except ImportError:
    collab_lock = None

try:
    import context_loader  # type: ignore
except ImportError:
    context_loader = None

RUNNER_LOG = Path("/AA_MY_DRIVE/_logs/managed_agent_runner.log")
POLL_SECONDS = float(os.environ.get("MANAGED_AGENT_RUNNER_POLL_SECONDS", "10"))
DEFAULT_MODEL = os.environ.get("MANAGED_AGENT_DEFAULT_MODEL", "claude-sonnet-4-5")

# State cache: agent_id + environment_id reused across tasks (cheaper).
# Per Anthropic doc: agents are reusable templates, sessions are per-task.
STATE_PATH = Path("/AA_MY_DRIVE/_state/managed_agent_runner.json")

log = logging.getLogger("managed-agent-runner")
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
    try:
        sys.path.insert(0, "/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance")
        from audit_log import write_envelope  # type: ignore
        write_envelope(agent_id="managed_agent_runner", action_type=action_type, payload=payload)
    except Exception:
        pass


def _branded_slack(text: str, channel: str = "#deploy-log",
                   title: str = "managed_agent_runner",
                   category: str = "ops") -> None:
    try:
        sys.path.insert(0, "/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools")
        from branded_slack import post_branded_slack  # type: ignore
        post_branded_slack(channel=channel, title=title, summary=text,
                           category=category, agent_name="Managed Agent")
        return
    except Exception:
        pass
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


def _routes_to_managed_agent(envelope: dict) -> bool:
    """Claim only envelopes that explicitly request managed_agent transport.
    Other transports (computer_use / browser_use) stay with their respective runners."""
    return envelope.get("transport") == "managed_agent"


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _ensure_agent_and_environment(client, model: str, system_prompt: str) -> tuple[str, str]:
    """Return (agent_id, environment_id), creating + caching once per process.
    Cached in /AA_MY_DRIVE/_state/managed_agent_runner.json."""
    state = _load_state()
    cache_key = f"{model}::lucrex"
    if cache_key in state.get("agents", {}):
        agent_id = state["agents"][cache_key]
    else:
        log.info("Creating new managed agent for model=%s", model)
        agent = client.beta.agents.create(
            name=f"Lucrex-{model}",
            model=model,
            system=system_prompt,
            tools=[{"type": "agent_toolset_20260401"}],
        )
        agent_id = agent.id
        state.setdefault("agents", {})[cache_key] = agent_id
        _save_state(state)
        log.info("Created agent %s (version %s)", agent_id, getattr(agent, "version", "?"))

    if "environment" in state:
        env_id = state["environment"]
    else:
        log.info("Creating Lucrex managed environment")
        env = client.beta.environments.create(
            name="lucrex-default",
            config={
                "type": "cloud",
                "networking": {"type": "unrestricted"},  # research + curl freely
            },
        )
        env_id = env.id
        state["environment"] = env_id
        _save_state(state)
        log.info("Created environment %s", env_id)

    return agent_id, env_id


def _build_system_prompt(envelope: dict) -> str:
    """Compose Lucrex voice rules + persona + operational context."""
    parts = [
        "You are a Lucrex managed agent (Everlight Ventures). Voice rules:",
        "* No em-dash; use double-hyphen `--` instead.",
        "* HTML over Markdown for structured output.",
        "* Verify before claiming; cite sources.",
        "* Terse and exact.",
        "* If task involves outbound (email/SMS), HONOR WHOLESALE_OUTBOUND_HALT env var.",
        "",
    ]
    persona = (envelope.get("context") or {}).get("persona", "")
    if persona:
        parts.append(f"DISPATCHED BY: {persona} (adopt their voice).")
    if context_loader is not None:
        try:
            parts.append(context_loader.build_operational_context(
                include_blinko=False, include_manifest_excerpt=False
            ))
        except Exception as e:
            log.warning("context_loader failed: %s", e)
    return "\n".join(parts)


def _run_managed_agent(envelope: dict, *, dry_run: bool = False) -> dict:
    """Sync wrapper. Creates session, sends user.message event, streams until idle."""
    task_id = envelope["task_id"]
    started_at = time.time()
    api_key = (os.environ.get("LUCREX_ANTHROPIC_KEY")
               or os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key:
        return {"status": "failed", "error": "no LUCREX_ANTHROPIC_KEY/ANTHROPIC_API_KEY"}

    if dry_run:
        return {
            "status": "done",
            "iterations": 0,
            "elapsed_seconds": 0.0,
            "final_text": "DRY_RUN: would have created managed agent session",
            "model": envelope.get("model_override") or DEFAULT_MODEL,
        }

    try:
        from anthropic import Anthropic
    except ImportError as e:
        return {"status": "failed", "error": f"anthropic SDK not installed: {e}"}

    client = Anthropic(api_key=api_key)
    model = envelope.get("model_override") or DEFAULT_MODEL
    system_prompt = _build_system_prompt(envelope)

    _audit("managed_agent.task.started", {
        "task_id": task_id,
        "model": model,
        "goal_preview": envelope["natural_language_goal"][:200],
    })

    try:
        agent_id, env_id = _ensure_agent_and_environment(client, model, system_prompt)
    except Exception as e:
        log.exception("agent/env setup failed")
        return {"status": "failed", "error": f"setup_failed: {e}"}

    # Create the session for this specific task
    try:
        session = client.beta.sessions.create(
            agent=agent_id,
            environment_id=env_id,
            title=envelope.get("title", task_id)[:80],
        )
        log.info("Session %s created for task %s", session.id, task_id)
    except Exception as e:
        log.exception("session create failed")
        return {"status": "failed", "error": f"session_create_failed: {e}"}

    # Open stream + send the user message
    final_text = ""
    tool_events = []
    iterations = 0
    status = "in_progress"
    try:
        with client.beta.sessions.events.stream(session.id) as stream:
            client.beta.sessions.events.send(
                session.id,
                events=[{
                    "type": "user.message",
                    "content": [{"type": "text",
                                  "text": envelope["natural_language_goal"]}],
                }],
            )
            for event in stream:
                # Collab lock: yield to CLI if Rich is typing
                if collab_lock is not None and collab_lock.is_paused_for_cli():
                    log.info("collab_lock=cli_active -- yielding")
                    collab_lock.wait_until_clear(max_wait=600.0, poll=1.5)
                    log.info("collab_lock cleared -- resuming")

                etype = getattr(event, "type", "")
                if etype == "agent.message":
                    for block in getattr(event, "content", []):
                        text = getattr(block, "text", "") or ""
                        final_text += text
                    iterations += 1
                elif etype == "agent.tool_use":
                    tool_events.append({
                        "name": getattr(event, "name", "?"),
                        "input_preview": str(getattr(event, "input", ""))[:120],
                    })
                    _audit("managed_agent.action.tool_use", {
                        "task_id": task_id, "tool": getattr(event, "name", "?")
                    })
                elif etype == "session.status_idle":
                    status = "done"
                    break
                # Time guard
                if time.time() - started_at > envelope.get("max_seconds", 600):
                    status = "aborted"
                    break
    except Exception as e:
        log.exception("stream failed")
        status = "failed"
        final_text += f"\n\n[STREAM ERROR] {e}"

    elapsed = round(time.time() - started_at, 2)
    _audit("managed_agent.task.completed", {
        "task_id": task_id, "session_id": session.id,
        "status": status, "iterations": iterations,
        "elapsed_seconds": elapsed, "tool_calls": len(tool_events),
    })

    return {
        "status": status,
        "iterations": iterations,
        "elapsed_seconds": elapsed,
        "final_text": final_text[:8000],
        "tool_events": tool_events[:20],
        "session_id": session.id,
        "model": model,
    }


def process_envelope(envelope_path: Path, *, dry_run: bool = False) -> dict:
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    task_id = envelope["task_id"]

    if not _routes_to_managed_agent(envelope):
        return envelope

    log.info("Processing %s: %s", task_id, envelope.get("title"))
    ok, reason = _check_safety(envelope)
    if not ok:
        envelope["status"] = "failed"
        envelope["completed_at"] = _now_iso()
        envelope["result"] = {"error": "safety_check_failed", "reason": reason}
        return envelope

    envelope["status"] = "in_progress"
    envelope["started_at"] = _now_iso()
    envelope_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    moved = _atomic_move(envelope_path, IN_PROGRESS)

    _branded_slack(
        f":cloud: managed_agent_runner picked up `{task_id}`: {envelope.get('title','(no title)')}",
        channel=envelope.get("callback_slack_channel", "#deploy-log"),
        title="Managed agent dispatched",
        category="ops",
    )

    try:
        result = _run_managed_agent(envelope, dry_run=dry_run)
    except Exception as e:
        log.exception("_run_managed_agent crashed")
        result = {"status": "failed", "error": f"runner_crash: {e}"}

    envelope["result"] = result
    envelope["completed_at"] = _now_iso()
    envelope["status"] = "done" if result.get("status") == "done" else "failed"

    moved.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    final = _atomic_move(moved, DONE if envelope["status"] == "done" else FAILED)

    summary = (
        f"{':white_check_mark:' if envelope['status'] == 'done' else ':x:'} "
        f"`{task_id}` -> {envelope['status']} via managed_agent "
        f"(model={result.get('model','?')}, tools={len(result.get('tool_events',[]))}, "
        f"{result.get('elapsed_seconds','?')}s). Final: {final.name}"
    )
    _branded_slack(summary,
                   channel=envelope.get("callback_slack_channel", "#deploy-log"),
                   title="Managed agent completed",
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
            if not _routes_to_managed_agent(envelope):
                continue
            process_envelope(f, dry_run=dry_run)
            n += 1
        except Exception as e:
            log.exception("envelope handler crashed for %s: %s", f, e)
    return n


def daemon_loop(*, poll_seconds: float = POLL_SECONDS, dry_run: bool = False) -> None:
    log.info("managed-agent-runner starting -- poll=%ss dry_run=%s default_model=%s",
             poll_seconds, dry_run, DEFAULT_MODEL)
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
    p = argparse.ArgumentParser(description="Managed-agent runner (Anthropic cloud)")
    p.add_argument("--once", action="store_true")
    p.add_argument("--dry-run", action="store_true")
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
