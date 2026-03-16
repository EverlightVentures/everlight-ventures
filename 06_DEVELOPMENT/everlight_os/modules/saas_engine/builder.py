"""
SaaS Factory — Repo scaffolder. STUB — Phase 1.
"""

from pathlib import Path
from ...core.filesystem import write_text


def scaffold(scope: dict, stack: dict, project_dir: Path) -> str:
    build_dir = project_dir / "build"
    build_dir.mkdir(exist_ok=True)
    runbook = (
        f"# {scope.get('product_name', 'Product')} — Runbook\n\n"
        f"[STUB] This file will contain setup, deploy, and ops instructions.\n\n"
        f"Stack: {stack.get('summary', 'TBD')}\n"
    )
    write_text(build_dir / "RUNBOOK.md", runbook)
    write_text(build_dir / ".env.example", "# [STUB] Environment variables go here\n")
    (build_dir / "deployment").mkdir(exist_ok=True)
    return str(build_dir / "RUNBOOK.md")


def write_test_plan(scope: dict, project_dir: Path) -> str:
    build_dir = project_dir / "build"
    build_dir.mkdir(exist_ok=True)
    content = f"# {scope.get('product_name', 'Product')} — Test Plan\n\n[STUB] Phase 1 expansion.\n"
    write_text(build_dir / "TEST_PLAN.md", content)
    return str(build_dir / "TEST_PLAN.md")
