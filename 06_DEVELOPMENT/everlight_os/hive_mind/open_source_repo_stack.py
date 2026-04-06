#!/usr/bin/env python3
"""Inspect and summarize the curated open-source repo stack."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required to read open_source_repo_stack.yaml") from exc

STACK_PATH = Path(__file__).with_name("open_source_repo_stack.yaml")


def load_stack() -> dict:
    data = yaml.safe_load(STACK_PATH.read_text()) or {}
    data.setdefault("repos", [])
    return data


def matches(repo: dict, workflows: set[str], phases: set[str], categories: set[str]) -> bool:
    if workflows and "all" not in workflows:
        repo_workflows = set(repo.get("workflows") or [])
        if workflows.isdisjoint(repo_workflows) and "all" not in repo_workflows:
            return False
    if phases and repo.get("phase") not in phases:
        return False
    if categories and repo.get("category") not in categories:
        return False
    return True


def detect_repo(repo: dict) -> dict:
    detection = repo.get("detection") or {}
    module_hits = {}
    binary_hits = {}

    for module_name in detection.get("python_modules") or []:
        module_hits[module_name] = importlib.util.find_spec(module_name) is not None

    for binary_name in detection.get("binaries") or []:
        binary_hits[binary_name] = shutil.which(binary_name) is not None

    installed = bool(module_hits or binary_hits) and (
        all(module_hits.values()) if module_hits else True
    ) and (
        all(binary_hits.values()) if binary_hits else True
    )

    return {
        "installed": installed,
        "module_hits": module_hits,
        "binary_hits": binary_hits,
    }


def filtered_repos(args) -> list[dict]:
    stack = load_stack()
    workflows = set(args.workflow or [])
    phases = set(args.phase or [])
    categories = set(args.category or [])
    repos = [repo for repo in stack["repos"] if matches(repo, workflows, phases, categories)]
    repos.sort(key=lambda item: (item.get("priority", 999), item.get("id", "")))
    return repos


def cmd_list(args) -> int:
    for repo in filtered_repos(args):
        print(
            f"{repo['priority']:>2}. {repo['id']:<18} "
            f"{repo['phase']:<9} {repo['owner_agent']:<18} "
            f"{repo['category']:<24} {repo['url']}"
        )
    return 0


def cmd_status(args) -> int:
    for repo in filtered_repos(args):
        status = detect_repo(repo)
        marker = "installed" if status["installed"] else "missing"
        print(f"{repo['id']}: {marker}")
        if status["module_hits"]:
            print(f"  modules: {json.dumps(status['module_hits'], sort_keys=True)}")
        if status["binary_hits"]:
            print(f"  binaries: {json.dumps(status['binary_hits'], sort_keys=True)}")
    return 0


def cmd_plan(args) -> int:
    repos = filtered_repos(args)
    by_phase: dict[str, list[dict]] = {}
    for repo in repos:
        by_phase.setdefault(repo["phase"], []).append(repo)

    for phase in sorted(by_phase):
        print(phase)
        for repo in by_phase[phase]:
            install = repo.get("install") or {}
            preferred = (
                install.get("docker")
                or install.get("shell")
                or install.get("pip")
                or install.get("conda")
                or install.get("sql")
                or "manual"
            )
            print(f"  - {repo['id']} [{repo['owner_agent']}]")
            print(f"    install: {preferred}")
            print(f"    fit: {', '.join(repo.get('workflows') or [])}")
            notes = repo.get("integration_notes") or []
            if notes:
                print(f"    note: {notes[0]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Everlight open-source repo stack helper")
    parser.add_argument("--workflow", action="append", help="Filter by workflow, e.g. broker, research, voice")
    parser.add_argument("--phase", action="append", help="Filter by phase, e.g. phase_1, phase_2, baseline")
    parser.add_argument("--category", action="append", help="Filter by category")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List curated repos")
    subparsers.add_parser("status", help="Check which repos look installed locally")
    subparsers.add_parser("plan", help="Print an installation plan")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "list":
        return cmd_list(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "plan":
        return cmd_plan(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
