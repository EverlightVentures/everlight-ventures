"""
Hive Mind Dispatcher - the core engine.

Flow:
  1. Perplexity intel scout (real-time research)
  2. Router classifies prompt, picks workers
  3. Gemini + Codex deliberate in parallel (E Pluribus Unum)
  4. Results converge into war room
  5. Claude EXECUTES -- reads recommendations, implements changes,
     delegates to sub-agents (SEO, SaaS builder, architect, etc.)
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import manager_gemini, manager_codex, manager_claude
from .contracts import HiveSession, ManagerResult, _now, _new_id
from .config import load_roster, WORKSPACE
from .intel import run_intel_scout
from .router import classify, classify_lite, classify_all
from .prompts import build_manager_prompt, reset_weight_cache
from .convergence import (
    write_war_room_files, build_combined_summary, log_session,
    update_war_room_session,
)
from .telemetry import log_session_telemetry


# Map worker keys to their run functions (NO Claude - Claude is the caller)
_RUNNERS = {
    "gemini": lambda prompt, conf: manager_gemini.run(
        prompt, conf.get("timeout_seconds", 120), conf.get("cli_mode", "plan")
    ),
    "codex": lambda prompt, conf: manager_codex.run(
        prompt, conf.get("timeout_seconds", 120)
    ),
}

# Progress tracking directory
_PROGRESS_DIR = WORKSPACE / "_logs" / ".hive_active"


def _write_progress(session_id: str, data: dict) -> None:
    """Write a progress update file for dashboard polling."""
    _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    progress_file = _PROGRESS_DIR / f"{session_id}.json"
    progress_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def dispatch(
    user_prompt: str,
    mode: str = "full",
    verbose: bool = False,
    session_id: str | None = None,
) -> HiveSession:
    """Run a full Hive Mind deliberation.

    Claude is the orchestrator - it calls this function, dispatches to
    Gemini/Codex/Perplexity, and then synthesizes the results itself.

    Args:
        session_id: Optional pre-assigned ID (for dashboard tracking).
    """
    roster = load_roster()
    reset_weight_cache()  # Fresh telemetry weights for this session

    sid = session_id or _new_id()
    session = HiveSession(
        id=sid,
        prompt=user_prompt,
        mode=mode,
        status="running",
    )

    # Write initial progress for dashboard polling
    _write_progress(sid, {
        "session_id": sid,
        "status": "running",
        "phase": "intel",
        "query": user_prompt[:200],
        "mode": mode,
        "routed_to": [],
        "agents": {},
        "started_at": session.created,
    })

    # Phase 1: Perplexity intel scout (always runs first)
    if verbose:
        print("[HIVE] Phase 1: Perplexity intel scout...")

    intel_result = run_intel_scout(user_prompt, roster)
    session.intel_summary = intel_result.response_text
    session.managers.append(intel_result)

    if verbose:
        status_icon = "+" if intel_result.status == "done" else "!"
        print(f"[HIVE] Intel [{status_icon}] {intel_result.duration_s}s")

    # Phase 2: Route to the right workers
    if mode == "lite":
        category, manager_keys = classify_lite(roster)
    elif mode == "all":
        category, manager_keys = classify_all()
    else:
        category, manager_keys = classify(user_prompt, roster)

    # Remove perplexity from parallel dispatch (already ran as scout)
    parallel_keys = [k for k in manager_keys if k != "perplexity"]
    session.routed_to = manager_keys

    if verbose:
        print(f"[HIVE] Phase 2: Routed as '{category}' -> {manager_keys}")

    # Update progress: routing done, agents dispatching
    _write_progress(sid, {
        "session_id": sid,
        "status": "running",
        "phase": "workers",
        "query": user_prompt[:200],
        "mode": mode,
        "category": category,
        "routed_to": manager_keys,
        "intel_status": intel_result.status,
        "intel_preview": (intel_result.response_text or "")[:300],
        "agents": {k: {"status": "running"} for k in parallel_keys},
        "started_at": session.created,
    })

    # Phase 3: Build prompts and dispatch in parallel
    if verbose and parallel_keys:
        print(f"[HIVE] Phase 3: Dispatching to {parallel_keys}...")

    start = time.time()

    def _run_worker(key: str) -> ManagerResult:
        conf = roster["managers"].get(key, {})
        employees = conf.get("employees", [])
        role = conf.get("role", key)

        mgr_prompt = build_manager_prompt(
            manager_key=key,
            role=role,
            employees=employees,
            user_prompt=user_prompt,
            intel_summary=session.intel_summary,
        )

        runner = _RUNNERS.get(key)
        if runner is None:
            return ManagerResult(
                manager=key, role=role, status="failed",
                error=f"No runner for worker '{key}'",
            )

        # Attempt 1: primary runner
        result = runner(mgr_prompt, conf)
        result.employees_consulted = employees

        # Retry once on failure (not timeout -- timeouts mean the agent
        # ran but took too long, retrying would just waste more time)
        if result.status == "failed":
            if verbose:
                print(f"[HIVE] {key.upper()} failed, retrying once...")
            retry = runner(mgr_prompt, conf)
            retry.employees_consulted = employees
            if retry.status == "done":
                retry.error = f"(retry succeeded after: {result.error})"
                return retry
            # Both attempts failed -- return original error
            result.error = f"2 attempts failed: {result.error}"

        return result

    if parallel_keys:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_run_worker, k): k for k in parallel_keys}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    mgr_result = future.result()
                except Exception as e:
                    mgr_result = ManagerResult(
                        manager=key, status="failed",
                        error=str(e)[:500],
                    )
                session.managers.append(mgr_result)

                # BMO Phase 1: Log specialist telemetry
                if roster.get("telemetry", {}).get("enabled", False):
                    try:
                        log_session_telemetry(
                            session_id=sid,
                            manager_key=key,
                            employees=mgr_result.employees_consulted or [],
                            response_text=mgr_result.response_text or "",
                            status=mgr_result.status,
                            duration_s=mgr_result.duration_s,
                            category=locals().get("category", ""),
                        )
                    except Exception:
                        pass  # telemetry is best-effort

                if verbose:
                    status_icon = "+" if mgr_result.status == "done" else "!"
                    print(f"[HIVE] {key.upper()} [{status_icon}] {mgr_result.duration_s}s")

                # Update progress: agent completed
                try:
                    progress_file = _PROGRESS_DIR / f"{sid}.json"
                    if progress_file.exists():
                        prog = json.loads(progress_file.read_text(encoding="utf-8"))
                    else:
                        prog = {"agents": {}}
                    prog["agents"][key] = {
                        "status": mgr_result.status,
                        "duration_s": mgr_result.duration_s,
                        "preview": (mgr_result.response_text or "")[:500],
                        "error": mgr_result.error,
                        "employees": mgr_result.employees_consulted,
                    }
                    _write_progress(sid, prog)
                except Exception:
                    pass  # Progress updates are best-effort

    session.total_duration_s = round(time.time() - start + intel_result.duration_s, 1)

    # Phase 4: Convergence
    if verbose:
        print("[HIVE] Phase 4: Converging results...")

    _write_progress(sid, {
        "session_id": sid,
        "status": "converging",
        "phase": "convergence",
        "query": user_prompt[:200],
        "mode": mode,
        "routed_to": manager_keys,
        "agents": {
            m.manager: {
                "status": m.status,
                "duration_s": m.duration_s,
                "preview": (m.response_text or "")[:500],
                "error": m.error,
                "employees": m.employees_consulted,
            }
            for m in session.managers
        },
        "started_at": session.created,
    })

    war_room_path = write_war_room_files(session, roster)
    session.war_room_dir = str(war_room_path)
    session.combined_summary = build_combined_summary(session)

    log_session(session, roster)

    # Re-write session.json after convergence
    session.status = "done"
    session.finished = _now()
    update_war_room_session(session)

    # Phase 5: Claude Execution -- read recommendations, execute them
    # Any successful agent responses mean there are recommendations to act on
    has_recommendations = any(
        m.status == "done" and m.response_text
        for m in session.managers
        if m.manager != "perplexity"
    )

    if has_recommendations and mode != "lite":
        if verbose:
            print("[HIVE] Phase 5: Claude executing recommendations...")

        _write_progress(sid, {
            "session_id": sid,
            "status": "executing",
            "phase": "execution",
            "query": user_prompt[:200],
            "mode": mode,
            "category": locals().get("category", ""),
            "routed_to": manager_keys + ["claude"],
            "war_room_dir": str(war_room_path),
            "agents": {
                m.manager: {
                    "status": m.status,
                    "duration_s": m.duration_s,
                    "response_text": m.response_text,
                    "error": m.error,
                    "employees": m.employees_consulted,
                    "role": m.role,
                }
                for m in session.managers
            } | {"claude": {"status": "running", "role": "Chief Operator / Executor"}},
            "started_at": session.created,
        })

        # Launch Claude execution as detached process so we don't block the
        # dashboard from showing deliberation results. The execution report
        # gets written to the war room when Claude finishes.
        try:
            manager_claude.run_detached(
                user_query=user_prompt,
                combined_summary=session.combined_summary,
                category=locals().get("category", "full"),
                war_room_dir=str(war_room_path),
                timeout=300,
            )
            if verbose:
                print("[HIVE] Phase 5: Claude execution launched (detached)")
        except Exception as e:
            if verbose:
                print(f"[HIVE] Phase 5: Claude execution failed to launch: {e}")

    # Final progress: done with full results
    _write_progress(sid, {
        "session_id": sid,
        "status": "done",
        "phase": "complete",
        "query": user_prompt[:200],
        "mode": mode,
        "category": locals().get("category", ""),
        "routed_to": manager_keys,
        "war_room_dir": str(war_room_path),
        "total_duration_s": session.total_duration_s,
        "agents": {
            m.manager: {
                "status": m.status,
                "duration_s": m.duration_s,
                "response_text": m.response_text,
                "error": m.error,
                "employees": m.employees_consulted,
                "role": m.role,
            }
            for m in session.managers
        },
        "started_at": session.created,
        "finished_at": session.finished,
    })

    return session
