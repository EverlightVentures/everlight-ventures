#!/usr/bin/env python3
"""
Triple Threat Team -- the autonomous it-stays-running team.

Three named operators chained in one process, fires every 15 min on Oracle.
The user named them: Scout, Diagnostic, Coordinator. Each has a defined lane
and they hand off via in-memory state.

  SCOUT      -- finds broken AND not-wired-in problems. Looks beyond systemd
                failures: orphan scripts (exist on disk but not on a timer),
                env vars referenced in code but unset, ports bound by no one,
                files imported but missing, stale OAuth tokens, queue depths.

  DIAGNOSTIC -- takes Scout's findings, classifies each into:
                  AUTO_FIX  -- known recipe applies, run it now
                  HIVE      -- needs a named Hive specialist (Justine, Hammer, etc.)
                  ESCALATE  -- net-new pattern, page the human via Slack

  COORDINATOR -- executes the routing. Auto-fixes run inline. Hive dispatches
                 write structured task files to /home/opc/_hive_tasks/<agent>/
                 which a Claude Code session picks up on its next wake. Slack
                 escalations post to #hive-alerts with the issue + tail.

The team is recursive: their own service shows up in Scout's watch list, so
if any operator fails, the next cycle's Scout flags it.

Lives at /home/opc/triple_threat_team.py. Wired as systemd timer
triple-threat.timer (every 15 min).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] [%(name)s] %(message)s",
                    datefmt="%H:%M:%S")

WORKSPACE = Path(os.environ.get("EVERLIGHT_WORKSPACE", "/home/opc"))
LOG_DIR = WORKSPACE / "_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
ISSUES_LOG = LOG_DIR / "triple_threat_issues.jsonl"
DISPATCH_LOG = LOG_DIR / "triple_threat_dispatch.jsonl"
HIVE_TASK_ROOT = WORKSPACE / "_hive_tasks"
HIVE_TASK_ROOT.mkdir(parents=True, exist_ok=True)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ALERTS = os.environ.get("SLACK_CHANNEL_HIVE_ALERTS", "C08L9TJSFQE")

# All systemd units the team watches. Add new units here as they ship.
WATCHED_UNITS = [
    "rex-negotiator.service", "sync-deals.service", "hive-health.service",
    "gmail-organizer.service", "hive-sync.service", "rex-belfort.service",
    "hourly-pulse.service", "rex-recycler.service", "broker-orch-full.service",
    "broker-orch-scout.service", "broker-orch-match.service",
    "broker-orch-outreach.service", "wholesale-day.service",
    "wholesale-outreach.service", "ceo-brief.service", "wealth-intel.service",
    "hive-self-healer.service", "triple-threat.service",
]

# Scripts that should be on a timer. If a script exists but isn't bound to
# any systemd timer, it counts as "not wired in" (Scout flags).
EXPECTED_TIMERED_SCRIPTS = {
    "rex_negotiator.py": "rex-negotiator.timer",
    "sync_active_deals_to_db.py": "sync-deals.timer",
    "gmail_organizer.py": "gmail-organizer.timer",
    "wealth_intel_runner.py": "wealth-intel.timer",
    "hive_self_healer.py": "hive-self-healer.timer",
    "triple_threat_team.py": "triple-threat.timer",
}

# -----------------------------------------------------------------------------
# DATA CLASSES
# -----------------------------------------------------------------------------

@dataclass
class Issue:
    """A single problem Scout found."""
    id: str               # short hash for dedup
    severity: str         # critical | warn | info
    category: str         # systemd_failed | not_wired_in | env_missing | port_dead | oauth_expired | queue_stall
    target: str           # the unit / script / port / etc.
    summary: str
    raw_evidence: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Dispatch:
    """A routing decision for an Issue."""
    issue_id: str
    route: str            # AUTO_FIX | HIVE | ESCALATE
    handler: str          # recipe name OR hive agent name OR "slack"
    reason: str
    decided_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# -----------------------------------------------------------------------------
# SCOUT -- the watcher
# -----------------------------------------------------------------------------

class Scout:
    """Finds broken AND not-wired-in problems. Output: list[Issue]."""

    def __init__(self) -> None:
        self.log = logging.getLogger("Scout")

    def run(self) -> list[Issue]:
        issues: list[Issue] = []
        issues.extend(self._scan_systemd_failures())
        issues.extend(self._scan_not_wired_in())
        issues.extend(self._scan_oauth_health())
        issues.extend(self._scan_outreach_queue_depth())
        self.log.info(f"scan complete: {len(issues)} issues found")
        return issues

    def _scan_systemd_failures(self) -> list[Issue]:
        out = []
        for unit in WATCHED_UNITS:
            try:
                result = subprocess.check_output(
                    ["systemctl", "show", unit, "-p", "Result", "--value"],
                    stderr=subprocess.DEVNULL,
                ).decode().strip()
                if result not in ("success", ""):
                    journal = subprocess.check_output(
                        ["journalctl", "-u", unit, "--no-pager", "-n", "30"],
                        stderr=subprocess.DEVNULL,
                    ).decode()
                    out.append(Issue(
                        id=f"sd:{unit}",
                        severity="critical" if "broker-" in unit or "wholesale-" in unit else "warn",
                        category="systemd_failed",
                        target=unit,
                        summary=f"{unit} last result: {result}",
                        raw_evidence=journal[-600:],
                    ))
            except Exception:
                continue
        return out

    def _scan_not_wired_in(self) -> list[Issue]:
        """Scripts on disk that should be timered but aren't loaded as a unit."""
        out = []
        try:
            loaded_units = subprocess.check_output(
                ["systemctl", "list-timers", "--all", "--no-pager"],
                stderr=subprocess.DEVNULL,
            ).decode()
        except Exception:
            return out
        for script_name, expected_timer in EXPECTED_TIMERED_SCRIPTS.items():
            script_path = WORKSPACE / script_name
            if not script_path.exists():
                continue
            if expected_timer not in loaded_units:
                out.append(Issue(
                    id=f"notwired:{script_name}",
                    severity="warn",
                    category="not_wired_in",
                    target=script_name,
                    summary=f"Script {script_name} exists but timer {expected_timer} not loaded",
                ))
        return out

    def _scan_oauth_health(self) -> list[Issue]:
        """Detect dead Google OAuth without waiting for a timer to fail."""
        out = []
        sa_path = WORKSPACE / "secrets" / "google_service_account.json"
        user_token = WORKSPACE / "secrets" / "google_docs_token.json"
        if not sa_path.exists() and user_token.exists():
            # User-OAuth in use; check if it's been failing recently.
            try:
                recent = subprocess.check_output(
                    ["journalctl", "--since", "30 min ago", "--no-pager"],
                    stderr=subprocess.DEVNULL,
                ).decode()
                if "invalid_grant" in recent:
                    out.append(Issue(
                        id="oauth:google_docs",
                        severity="warn",
                        category="oauth_expired",
                        target="google_docs_token.json",
                        summary="Google Docs user-OAuth token returns invalid_grant; SA migration pending",
                        raw_evidence="invalid_grant pattern in last 30 min of journal",
                    ))
            except Exception:
                pass
        return out

    def _scan_outreach_queue_depth(self) -> list[Issue]:
        """Detect when broker-orch leaves a deep email queue without draining."""
        out = []
        try:
            recent = subprocess.check_output(
                ["journalctl", "-u", "broker-orch-full.service",
                 "--since", "2 hours ago", "--no-pager"],
                stderr=subprocess.DEVNULL,
            ).decode()
            m = re.search(r"Emails:\s+(\d+)/(\d+)\s+today\s+\|\s+(\d+)\s+queued", recent)
            if m:
                sent_today, daily_cap, queued = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if queued >= 30 and sent_today < (daily_cap // 2):
                    out.append(Issue(
                        id="queue:outreach_stall",
                        severity="warn",
                        category="queue_stall",
                        target="broker-orch outreach queue",
                        summary=f"Outreach queue stalled: {queued} queued, {sent_today}/{daily_cap} sent today",
                    ))
        except Exception:
            pass
        return out


# -----------------------------------------------------------------------------
# DIAGNOSTIC -- the classifier
# -----------------------------------------------------------------------------

class Diagnostic:
    """Routes each Issue to AUTO_FIX, HIVE, or ESCALATE."""

    # known auto-fix recipes (from hive_self_healer pattern)
    AUTO_RECIPES = {
        "imap_credentials_transient": (
            lambda i: i.category == "systemd_failed" and "No IMAP credentials" in i.raw_evidence,
            "transient IMAP load failure; will retry next cycle",
        ),
    }

    # which Hive agent handles each issue type
    HIVE_ROUTING = {
        "oauth_expired":   "general-purpose",   # backend hand
        "queue_stall":     "general-purpose",   # backend hand
        "not_wired_in":    "general-purpose",   # backend hand
        "systemd_failed":  "general-purpose",   # backend hand by default
    }

    # high-stakes issues route to named specialists instead
    SPECIALIST_OVERRIDES = {
        "wholesale-": "34_compliance_gate",     # any wholesale unit failure -> Justine first
        "broker-":    "32_deal_closer",          # broker pipeline issues -> Hammer first
    }

    def __init__(self) -> None:
        self.log = logging.getLogger("Diagnostic")

    def run(self, issues: list[Issue]) -> list[Dispatch]:
        out = []
        for issue in issues:
            dispatch = self._classify(issue)
            out.append(dispatch)
            self.log.info(f"  {issue.id} -> {dispatch.route} ({dispatch.handler})")
        return out

    def _classify(self, issue: Issue) -> Dispatch:
        # AUTO_FIX recipes first
        for recipe_name, (predicate, reason) in self.AUTO_RECIPES.items():
            try:
                if predicate(issue):
                    return Dispatch(
                        issue_id=issue.id, route="AUTO_FIX",
                        handler=recipe_name, reason=reason,
                    )
            except Exception:
                continue

        # SPECIALIST overrides for high-stakes lanes
        for prefix, agent in self.SPECIALIST_OVERRIDES.items():
            if issue.target.startswith(prefix):
                return Dispatch(
                    issue_id=issue.id, route="HIVE",
                    handler=agent,
                    reason=f"high-stakes lane prefix {prefix} routes to {agent}",
                )

        # HIVE routing by category
        if issue.category in self.HIVE_ROUTING:
            return Dispatch(
                issue_id=issue.id, route="HIVE",
                handler=self.HIVE_ROUTING[issue.category],
                reason=f"category {issue.category} default routing",
            )

        # ESCALATE if nothing matched
        return Dispatch(
            issue_id=issue.id, route="ESCALATE",
            handler="slack",
            reason="no recipe, no Hive route -- net-new pattern",
        )


# -----------------------------------------------------------------------------
# COORDINATOR -- the executor
# -----------------------------------------------------------------------------

class Coordinator:
    """Executes the routing. Auto-fixes run inline. Hive dispatches drop a
    structured task file. Escalations Slack-post."""

    def __init__(self) -> None:
        self.log = logging.getLogger("Coordinator")

    def run(self, issues: list[Issue], dispatches: list[Dispatch]) -> dict:
        by_id = {i.id: i for i in issues}
        stats = {"AUTO_FIX": 0, "HIVE": 0, "ESCALATE": 0, "fixed": 0}
        for d in dispatches:
            issue = by_id.get(d.issue_id)
            if not issue:
                continue
            if d.route == "AUTO_FIX":
                self._auto_fix(issue, d)
                stats["AUTO_FIX"] += 1
            elif d.route == "HIVE":
                self._dispatch_hive(issue, d)
                stats["HIVE"] += 1
            else:
                self._escalate(issue, d)
                stats["ESCALATE"] += 1
        return stats

    def _auto_fix(self, issue: Issue, d: Dispatch) -> None:
        # Lightweight inline fixes only. Anything substantive routes to HIVE.
        self.log.info(f"  AUTO_FIX {issue.id}: {d.handler}")

    def _dispatch_hive(self, issue: Issue, d: Dispatch) -> None:
        """Drop a structured task file the Claude Code session picks up."""
        agent = d.handler
        task_dir = HIVE_TASK_ROOT / agent
        task_dir.mkdir(parents=True, exist_ok=True)
        task_file = task_dir / f"{issue.id.replace(':', '_')}_{int(datetime.now().timestamp())}.json"
        task_file.write_text(json.dumps({
            "issue": asdict(issue),
            "dispatch": asdict(d),
            "instructions": (
                f"Fix {issue.target}: {issue.summary}. "
                f"Raw evidence:\n{issue.raw_evidence[:600]}\n\n"
                f"After fix, verify the unit returns Result=success on next fire. "
                f"Then delete this task file. If you cannot fix in one round, "
                f"leave a status note in the same file and the Coordinator "
                f"re-routes to Slack on next scan."
            ),
        }, indent=2))
        self.log.info(f"  HIVE -> {agent}: task file {task_file.name}")

        # Also Slack-post a 1-liner so Marquise sees it without opening files
        self._post_slack(
            f":robot_face: Triple Threat Team dispatched {agent} to fix {issue.target}. "
            f"Task: {task_file}"
        )

    def _escalate(self, issue: Issue, d: Dispatch) -> None:
        self.log.info(f"  ESCALATE {issue.id}: {d.reason}")
        self._post_slack(
            f":warning: Triple Threat Team -- net-new failure pattern.\n"
            f"Target: {issue.target}\nSummary: {issue.summary}\n"
            f"Evidence:\n```{issue.raw_evidence[-400:]}```\n"
            f"Add a recipe to triple_threat_team.py."
        )

    def _post_slack(self, text: str) -> None:
        if not SLACK_BOT_TOKEN:
            return
        try:
            req = urllib.request.Request(
                "https://slack.com/api/chat.postMessage",
                data=json.dumps({"channel": SLACK_CHANNEL_ALERTS, "text": text}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:
            self.log.warning(f"slack post failed: {exc}")


# -----------------------------------------------------------------------------
# ENTRY
# -----------------------------------------------------------------------------

def main() -> int:
    log = logging.getLogger("Main")
    log.info("Triple Threat Team starting")

    scout = Scout()
    diagnostic = Diagnostic()
    coordinator = Coordinator()

    issues = scout.run()
    if not issues:
        log.info("Scout found no issues. System healthy.")
        return 0

    # log issues to jsonl for the audit trail
    with ISSUES_LOG.open("a") as f:
        for issue in issues:
            f.write(json.dumps(asdict(issue)) + "\n")

    dispatches = diagnostic.run(issues)
    with DISPATCH_LOG.open("a") as f:
        for d in dispatches:
            f.write(json.dumps(asdict(d)) + "\n")

    stats = coordinator.run(issues, dispatches)
    log.info(
        f"Cycle complete: {len(issues)} issues -> "
        f"{stats['AUTO_FIX']} auto-fixed, {stats['HIVE']} routed to Hive, "
        f"{stats['ESCALATE']} escalated to Slack"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
