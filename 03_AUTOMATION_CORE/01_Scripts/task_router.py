#!/usr/bin/env python3
"""
task_router.py - Everlight OS Task Queue Router
Owner: 03_engineering_foreman / 24_workflow_builder

Usage:
  python3 task_router.py route <task_json_or_file>
  python3 task_router.py list
  python3 task_router.py status <task_id>
  python3 task_router.py run-pending

Reads triggers.yaml for pipeline definitions.
Writes tasks to _logs/task_queue.jsonl.
"""

import json
import sys
import os
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# Paths
BASE = Path(__file__).resolve().parents[2]  # AA_MY_DRIVE root
TRIGGERS_FILE = BASE / "03_AUTOMATION_CORE" / "02_Config" / "triggers.yaml"
QUEUE_FILE = BASE / "_logs" / "task_queue.jsonl"
LOG_DIR = BASE / "_logs"

PT = ZoneInfo("America/Los_Angeles")


def now_pt():
    return datetime.now(PT).isoformat()


def ensure_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.touch(exist_ok=True)


# ---------------------------------------------------------------------------
# Pipeline -> executor mapping
# ---------------------------------------------------------------------------
PIPELINE_MAP = {
    "content_engine":     {"executor": "gemini",  "slack": "agent-content-strategy"},
    "analytics_engine":   {"executor": "codex",   "slack": "agent-analytics-auditor"},
    "engineering_engine": {"executor": "codex",   "slack": "agent-ops-logs"},
    "qa_engine":          {"executor": "claude",  "slack": "agent-approvals"},
    "ops_engine":         {"executor": "claude",  "slack": "ai-war-room"},
    "saas_engine":        {"executor": "codex",   "slack": "agent-ops-logs"},
    "hive_engine":        {"executor": "all",     "slack": "ai-war-room"},
    "escalation_engine":  {"executor": "claude",  "slack": "agent-errors"},
    "books_engine":       {"executor": "claude",  "slack": "agent-book-showrunner"},
    "trading_engine":     {"executor": "claude",  "slack": "ai-war-room"},
}

# Routing rules: intent keywords -> pipeline
INTENT_RULES = [
    (["trade", "xlm", "xlp", "perp", "bot", "margin", "pnl"], "trading_engine"),
    (["book", "chapter", "manuscript", "kdp", "series"],       "books_engine"),
    (["saas", "build", "launch", "app", "product"],            "saas_engine"),
    (["content", "post", "social", "blog", "publish"],         "content_engine"),
    (["data", "csv", "analytics", "kpi", "metric"],            "analytics_engine"),
    (["code", "script", "bug", "deploy", "test"],              "engineering_engine"),
    (["qa", "review", "quality", "check", "gate"],             "qa_engine"),
]


def classify_task(description: str) -> dict:
    """Route a task description to the correct pipeline + executor."""
    desc_lower = description.lower()
    for keywords, pipeline in INTENT_RULES:
        if any(kw in desc_lower for kw in keywords):
            meta = PIPELINE_MAP.get(pipeline, {})
            return {"pipeline": pipeline, **meta}
    # Default to ops
    return {"pipeline": "ops_engine", **PIPELINE_MAP["ops_engine"]}


def make_task(description: str, priority: int = 3, context_paths: list = None,
              inputs: dict = None, owner: str = None) -> dict:
    """Build a standard task object."""
    routing = classify_task(description)
    task = {
        "task_id": str(uuid.uuid4())[:8],
        "description": description,
        "pipeline": routing["pipeline"],
        "executor": routing["executor"],
        "slack_channel": routing.get("slack", "ai-war-room"),
        "owner": owner or routing["executor"],
        "status": "pending",
        "priority": priority,
        "context_paths": context_paths or [],
        "inputs": inputs or {},
        "outputs": {},
        "created_at": now_pt(),
        "updated_at": now_pt(),
        "next_action": description,
        "eta": None,
    }
    return task


def enqueue(task: dict):
    """Append a task to the queue file."""
    ensure_dirs()
    with open(QUEUE_FILE, "a") as f:
        f.write(json.dumps(task) + "\n")
    print(f"[+] Queued task {task['task_id']} -> {task['pipeline']} ({task['executor']})")
    return task


def load_queue() -> list:
    """Load all tasks from queue file."""
    ensure_dirs()
    tasks = []
    with open(QUEUE_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    tasks.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return tasks


def save_queue(tasks: list):
    """Overwrite queue file with updated task list."""
    ensure_dirs()
    with open(QUEUE_FILE, "w") as f:
        for t in tasks:
            f.write(json.dumps(t) + "\n")


def update_task_status(task_id: str, status: str, next_action: str = None):
    """Update status of a task in the queue."""
    tasks = load_queue()
    found = False
    for t in tasks:
        if t["task_id"] == task_id:
            t["status"] = status
            t["updated_at"] = now_pt()
            if next_action:
                t["next_action"] = next_action
            found = True
            break
    if not found:
        print(f"[!] Task {task_id} not found")
        return False
    save_queue(tasks)
    print(f"[+] Task {task_id} -> {status}")
    return True


def list_tasks(filter_status: str = None):
    """Print all tasks, optionally filtered by status."""
    tasks = load_queue()
    if filter_status:
        tasks = [t for t in tasks if t["status"] == filter_status]
    if not tasks:
        print("No tasks found.")
        return
    print(f"\n{'ID':8}  {'STATUS':10}  {'PRI':3}  {'PIPELINE':20}  DESCRIPTION")
    print("-" * 80)
    for t in sorted(tasks, key=lambda x: x["priority"]):
        desc = t["description"][:45] + "..." if len(t["description"]) > 45 else t["description"]
        print(f"{t['task_id']:8}  {t['status']:10}  {t['priority']:3}  {t['pipeline']:20}  {desc}")


def show_task(task_id: str):
    """Print full detail for one task."""
    tasks = load_queue()
    for t in tasks:
        if t["task_id"] == task_id:
            print(json.dumps(t, indent=2))
            return
    print(f"[!] Task {task_id} not found")


def run_pending():
    """
    Print pending tasks sorted by priority.
    In a real deployment this would dispatch to the executor CLI.
    For now: prints the dispatch commands that should be run.
    """
    tasks = load_queue()
    pending = [t for t in tasks if t["status"] == "pending"]
    pending.sort(key=lambda x: x["priority"])
    if not pending:
        print("No pending tasks.")
        return
    print(f"\nPending tasks ({len(pending)}) - highest priority first:\n")
    for t in pending:
        print(f"  [{t['priority']}] {t['task_id']} | {t['executor']:8} | {t['description'][:60]}")
        if t["executor"] == "claude":
            print(f"       -> cl \"{t['description']}\"")
        elif t["executor"] == "gemini":
            print(f"       -> gm \"{t['description']}\"")
        elif t["executor"] == "codex":
            print(f"       -> cx \"{t['description']}\"")
        elif t["executor"] == "all":
            print(f"       -> hive \"{t['description']}\"")
        print()


def main():
    parser = argparse.ArgumentParser(description="Everlight Task Router")
    sub = parser.add_subparsers(dest="cmd")

    # route command
    r = sub.add_parser("route", help="Create and queue a task")
    r.add_argument("description", nargs="?", help="Task description")
    r.add_argument("--file", help="JSON file with task definition")
    r.add_argument("--priority", type=int, default=3, help="Priority 1-5 (1=urgent)")
    r.add_argument("--owner", help="Override executor/owner")
    r.add_argument("--context", nargs="*", help="Relevant file paths")

    # list command
    ls = sub.add_parser("list", help="List tasks")
    ls.add_argument("--status", help="Filter by status")

    # status command
    st = sub.add_parser("status", help="Show task detail")
    st.add_argument("task_id")

    # update command
    up = sub.add_parser("update", help="Update task status")
    up.add_argument("task_id")
    up.add_argument("status", choices=["pending", "active", "blocked", "done"])
    up.add_argument("--next", help="Next action description")

    # run-pending command
    sub.add_parser("run-pending", help="Print dispatch commands for pending tasks")

    args = parser.parse_args()

    if args.cmd == "route":
        if args.file:
            with open(args.file) as f:
                task_def = json.load(f)
            task = make_task(
                description=task_def.get("description", "Unknown"),
                priority=task_def.get("priority", 3),
                context_paths=task_def.get("context_paths"),
                inputs=task_def.get("inputs"),
                owner=task_def.get("owner"),
            )
        elif args.description:
            task = make_task(
                description=args.description,
                priority=args.priority,
                context_paths=args.context,
                owner=args.owner,
            )
        else:
            print("Error: provide a description or --file")
            sys.exit(1)
        enqueue(task)

    elif args.cmd == "list":
        list_tasks(filter_status=args.status)

    elif args.cmd == "status":
        show_task(args.task_id)

    elif args.cmd == "update":
        update_task_status(args.task_id, args.status, next_action=args.next)

    elif args.cmd == "run-pending":
        run_pending()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
