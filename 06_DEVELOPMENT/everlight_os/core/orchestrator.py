"""
Everlight OS — Orchestrator.
Executes step plans, manages state, writes artifacts, supports resume.
"""

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

from .contracts import ProjectState, RouterResult, StepDef, RunLogEntry, _now, _new_id
from . import log as elog
from .slack_client import get_client as get_slack

logger = logging.getLogger(__name__)


class Orchestrator:
    """Execute a routed plan step-by-step with state persistence and resume."""

    def __init__(self):
        self.step_handlers: Dict[str, Callable] = {}
        self.slack = get_slack()

    def register_handler(self, engine: str, step_name: str, handler: Callable):
        """Register a handler function for engine:step_name."""
        key = f"{engine}:{step_name}"
        self.step_handlers[key] = handler

    def run(self, route: RouterResult, request: str, project_dir: Path) -> ProjectState:
        """
        Execute a routed plan.

        Args:
            route: RouterResult from the router
            request: Original user request text
            project_dir: Where to write artifacts and state.json

        Returns:
            Final ProjectState
        """
        state_path = project_dir / "state.json"
        start_time = time.time()

        # Resume or create new state
        if state_path.exists():
            state = ProjectState.from_json(str(state_path))
            logger.info(f"Resuming project {state.id} from step {state.current_step}")
        else:
            state = ProjectState(
                id=_new_id(),
                engine=route.engine,
                intent=route.intent,
                request=request,
                status="running",
                steps=[s.to_dict() for s in route.steps],
                project_dir=str(project_dir),
            )

        state.status = "running"
        state.save(str(state_path))

        # Execute steps
        for i, step_dict in enumerate(state.steps):
            if step_dict.get("status") == "done":
                continue  # Already completed (resume)

            step_name = step_dict["name"]
            worker = step_dict["worker"]
            key = f"{route.engine}:{step_name}"

            handler = self.step_handlers.get(key)
            if not handler:
                logger.warning(f"No handler for {key}, skipping")
                step_dict["status"] = "skipped"
                state.current_step = i + 1
                state.save(str(state_path))
                continue

            # Run the step
            step_dict["status"] = "running"
            step_dict["started_at"] = _now()
            state.current_step = i
            state.save(str(state_path))

            logger.info(f"[{state.id}] Step {i+1}/{len(state.steps)}: {step_name}")

            try:
                result = handler(state, step_dict, project_dir)

                step_dict["status"] = "done"
                step_dict["finished_at"] = _now()
                if isinstance(result, str) and result:
                    step_dict["output_path"] = result
                    state.artifacts.append(result)

                dt = time.time() - time.mktime(
                    datetime.fromisoformat(step_dict["started_at"]).timetuple()
                ) if step_dict["started_at"] else 0
                step_dict["duration_s"] = round(dt, 1)

            except Exception as e:
                step_dict["status"] = "failed"
                step_dict["error"] = str(e)
                step_dict["finished_at"] = _now()
                state.errors.append(f"Step {step_name}: {e}")
                state.status = "failed"
                state.save(str(state_path))

                logger.error(f"Step {step_name} failed: {e}")
                logger.debug(traceback.format_exc())

                # Log the failed run
                self._log_run(state, time.time() - start_time)

                # Notify Slack
                self.slack.post_error(state.id, f"Step {step_name} failed: {e}")
                return state

            state.current_step = i + 1
            state.save(str(state_path))

        # All steps done
        state.status = "done"
        state.save(str(state_path))

        duration = time.time() - start_time
        self._log_run(state, duration)

        logger.info(f"[{state.id}] Complete — {len(state.artifacts)} artifacts in {duration:.1f}s")
        return state

    def _log_run(self, state: ProjectState, duration: float):
        """Append run to everlight_runs.jsonl."""
        entry = RunLogEntry(
            project_id=state.id,
            engine=state.engine,
            intent=state.intent,
            request=state.request,
            steps_completed=sum(1 for s in state.steps if s.get("status") == "done"),
            steps_total=len(state.steps),
            artifacts=state.artifacts,
            status="ok" if state.status == "done" else "fail",
            errors=state.errors,
            duration_s=round(duration, 1),
        )
        elog.append_run(entry.to_dict())
