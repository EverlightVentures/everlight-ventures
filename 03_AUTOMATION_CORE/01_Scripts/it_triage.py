#!/usr/bin/env python3
"""it_triage.py -- IT auto-repair worker.

Per HARD LAW feedback_fail_loud_with_it_auto_repair: every watchdog failure
queues an entry in `_logs/it_repair_queue.jsonl`. This script (cron, every
1 min) reads the queue, looks up the playbook for the failed service, runs
the recipe, verifies with a curl check, and posts resolution or escalation
to Slack via branded_slack.

No LLM in the loop -- playbooks are deterministic bash. The "IT team" is the
playbook execution layer. Secret-bound failures (Stripe key, Supabase token)
escalate immediately to operator without auto-repair, per doctrine.

Usage:
    python3 it_triage.py        # process the queue
    python3 it_triage.py --once # process at most one entry then exit
    python3 it_triage.py --dry  # show what would be done, no action

Cron (every 1 min):
    * * * * * python3 /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/it_triage.py >> _logs/it_triage.log 2>&1
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
QUEUE = ROOT / "_logs" / "it_repair_queue.jsonl"
PLAYBOOKS_PATH = ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "it_repair_playbooks.yaml"
LOG = ROOT / "_logs" / "it_triage.log"
ESCALATION_WINDOW = timedelta(minutes=15)
MAX_ATTEMPTS_DEFAULT = 2

# Add content_tools to path for branded_slack import.
sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"))


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}\n"
    print(line, end="")
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(line)
    except OSError as e:
        print(f"  log write failed: {e}", file=sys.stderr)


def load_playbooks() -> dict:
    """Read playbooks YAML. Minimal parser so we don't need PyYAML dependency."""
    try:
        import yaml  # type: ignore
        with PLAYBOOKS_PATH.open() as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback: rudimentary parse of the structure we control.
        log("WARN PyYAML missing -- using minimal parser. Install pyyaml for full feature parity.")
        return _minimal_yaml_parse(PLAYBOOKS_PATH.read_text())


def _minimal_yaml_parse(text: str) -> dict:
    """Tiny YAML parser limited to the it_repair_playbooks.yaml shape we control.

    Not a general YAML parser. Handles:
      - top-level keys: defaults, playbooks
      - playbook entries with: description, steps (list), verify, requires_secrets (list)
      - quoted strings, list-of-strings under steps/requires_secrets
    """
    result: dict = {"defaults": {}, "playbooks": {}}
    section: str = ""
    current_service: str = ""
    current_list_key: str = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        # Top-level keys (no indent)
        if line == "defaults:":
            section = "defaults"; current_service = ""; current_list_key = ""
            continue
        if line == "playbooks:":
            section = "playbooks"; current_service = ""; current_list_key = ""
            continue
        # Two-space indent: service name under playbooks
        if section == "playbooks" and line.startswith("  ") and not line.startswith("    "):
            name = line.strip().rstrip(":")
            current_service = name
            current_list_key = ""
            result["playbooks"][current_service] = {"steps": [], "requires_secrets": []}
            continue
        # Four-space indent: field or list start under a service
        if current_service and line.startswith("    ") and not line.startswith("      "):
            stripped = line.strip()
            if ":" in stripped and not stripped.startswith("-"):
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if val:
                    result["playbooks"][current_service][key] = val
                    current_list_key = ""
                else:
                    current_list_key = key
                    result["playbooks"][current_service].setdefault(key, [])
        # Six-space indent: list item under a field
        elif current_service and current_list_key and line.startswith("      - "):
            item = line.strip()[2:].strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            elif item.startswith("'") and item.endswith("'"):
                item = item[1:-1]
            result["playbooks"][current_service][current_list_key].append(item)
        # Defaults section
        elif section == "defaults" and line.startswith("  ") and ":" in line:
            key, _, val = line.strip().partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                try:
                    result["defaults"][key] = int(val)
                except ValueError:
                    result["defaults"][key] = val.strip('"').strip("'")
    return result


def read_queue() -> list[dict]:
    if not QUEUE.exists():
        return []
    entries: list[dict] = []
    with QUEUE.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def write_queue(entries: list[dict]) -> None:
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def run_step(cmd: str, env: dict) -> tuple[int, str]:
    """Run a single bash command, return (exit_code, output)."""
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, f"exception:{e}"


def post_slack(severity: str, title: str, detail: str, meta: dict) -> None:
    """Best-effort Slack alert via branded_slack. Non-fatal on failure."""
    try:
        from branded_slack import post_branded_alert  # type: ignore
        meta_str = " | ".join(f"{k}={v}" for k, v in meta.items())
        full_detail = f"{detail} | {meta_str}" if meta_str else detail
        post_branded_alert(
            channel="#hive-alerts",
            severity=severity,
            title=title,
            detail=full_detail,
            agent_name="IT Triage",
        )
    except Exception as e:
        log(f"  slack post failed: {e}")


def load_env_from_file(path: Path) -> dict:
    """Source the .env file into a dict so subshells inherit secrets."""
    env = dict(os.environ)
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def process_entry(entry: dict, playbooks: dict, env: dict, dry: bool) -> dict:
    """Process one queue entry. Returns updated entry."""
    name = entry.get("service", "")
    pb = playbooks.get("playbooks", {}).get(name)
    if not pb:
        entry["status"] = "no_playbook"
        log(f"  {name}: no playbook defined, marking no_playbook")
        return entry

    # Secret-bound failures escalate immediately, never auto-repair.
    reason = entry.get("failure_reason", "")
    if reason.startswith("secret_") or "secret" in reason.lower():
        entry["status"] = "escalated"
        entry["escalation_reason"] = "secret_bound_failure_never_auto_repaired"
        log(f"  {name}: secret-bound failure ({reason}) -- escalating to operator")
        if not dry:
            post_slack(
                "critical",
                f"MCP {name} needs operator action",
                f"Secret-bound failure: {reason}. Auto-repair never touches secrets. Rich must rotate the credential.",
                {"service": name, "port": entry.get("port"), "reason": reason},
            )
        return entry

    # Pre-flight: if the verify command already succeeds, the service is alive
    # (someone else fixed it, or eventual consistency caught up). Mark resolved
    # without running the playbook steps. Saves wasted restarts.
    verify_cmd_pre = pb.get("verify", "")
    if verify_cmd_pre:
        rc_pre, _ = run_step(verify_cmd_pre, env)
        if rc_pre == 0:
            entry["status"] = "resolved"
            entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
            entry["resolution"] = "pre_flight_already_alive"
            log(f"  {name}: pre-flight verify succeeded -- already alive, skipping playbook")
            return entry

    # Attempt-count check.
    attempts = entry.get("attempt_count", 1)
    max_attempts = pb.get("max_attempts") or playbooks.get("defaults", {}).get("max_attempts", MAX_ATTEMPTS_DEFAULT)
    if attempts > max_attempts:
        entry["status"] = "escalated"
        entry["escalation_reason"] = f"exceeded_max_attempts_{max_attempts}"
        entry["escalated_at"] = datetime.now(timezone.utc).isoformat()
        log(f"  {name}: exceeded {max_attempts} attempts -- escalating to operator")
        if not dry:
            post_slack(
                "critical",
                f"MCP {name} auto-repair exhausted",
                f"Failed {attempts} consecutive repair attempts. Manual investigation required.",
                {"service": name, "port": entry.get("port"), "attempts": attempts},
            )
        return entry

    # Run the playbook steps.
    log(f"  {name}: running playbook (attempt {attempts}/{max_attempts})")
    if dry:
        log(f"    DRY -- {len(pb.get('steps', []))} steps would run")
        entry["status"] = "dry_run"
        return entry

    for step in pb.get("steps", []):
        rc, out = run_step(step, env)
        if "escalate:" in out:
            entry["status"] = "escalated"
            entry["escalation_reason"] = out.strip()
            log(f"    step escalated: {out.strip()}")
            post_slack(
                "critical",
                f"MCP {name} repair escalated",
                f"Playbook step requested escalation: {out.strip()}",
                {"service": name, "port": entry.get("port")},
            )
            return entry
        if rc not in (0, 1):  # 0 = success, 1 = expected (e.g. pkill no match)
            log(f"    step rc={rc}: {step[:80]}")

    # Verify.
    verify_cmd = pb.get("verify", "")
    if verify_cmd:
        rc, _ = run_step(verify_cmd, env)
        if rc == 0:
            entry["status"] = "resolved"
            entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
            log(f"  {name}: ✓ resolved")
            post_slack(
                "info",
                f"MCP {name} auto-repaired",
                f"Watchdog flagged {name} as down. IT triage ran the playbook. Service back up.",
                {"service": name, "port": entry.get("port"), "attempts": attempts},
            )
        else:
            entry["status"] = "pending"
            entry["attempt_count"] = attempts + 1
            log(f"  {name}: ✗ verify failed (rc={rc}), attempt {attempts+1}/{max_attempts}")
    else:
        entry["status"] = "no_verify"
        log(f"  {name}: no verify command, marking no_verify")

    return entry


def prune_old_resolved(entries: list[dict]) -> list[dict]:
    """Keep resolved/escalated entries for ESCALATION_WINDOW, then drop.

    Tolerates both tz-aware ISO timestamps and tz-naive "YYYY-MM-DD HH:MM:SS"
    strings written by older mcp_watchdog.sh versions. Naive strings are
    assumed to be UTC.
    """
    cutoff = datetime.now(timezone.utc) - ESCALATION_WINDOW
    keep: list[dict] = []
    for e in entries:
        if e.get("status") in ("resolved", "escalated"):
            resolved_at = e.get("resolved_at") or e.get("escalated_at") or e.get("ts")
            t = None
            if resolved_at:
                try:
                    t = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    try:
                        t = datetime.strptime(resolved_at, "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        t = None
                if t is not None and t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
            if t and t < cutoff:
                continue
        keep.append(e)
    return keep


def main() -> int:
    once = "--once" in sys.argv
    dry = "--dry" in sys.argv

    env = load_env_from_file(ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env")
    playbooks = load_playbooks()
    entries = read_queue()

    if not entries:
        return 0

    log(f"=== it_triage cycle: {len(entries)} entries in queue ===")

    updated: list[dict] = []
    for entry in entries:
        status = entry.get("status", "pending")
        if status != "pending":
            updated.append(entry)
            continue
        entry = process_entry(entry, playbooks, env, dry)
        updated.append(entry)
        if once:
            break

    updated = prune_old_resolved(updated)
    if not dry:
        write_queue(updated)

    return 0


if __name__ == "__main__":
    sys.exit(main())
