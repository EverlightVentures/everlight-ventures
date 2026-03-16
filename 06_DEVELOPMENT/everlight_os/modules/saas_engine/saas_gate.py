"""
SaaS Factory — Phase gates.
run_spec_gate(): Phase 0 — all 9 spec docs must exist and have content.
run_build_gate(): Phase 1 stub.
run_launch_gate(): Phase 2 stub.
"""

from pathlib import Path
from ...core.filesystem import write_json, write_text

REQUIRED_SPEC_DOCS = [
    "spec/01_PRD.md",
    "spec/02_USER_STORIES.md",
    "spec/03_ACCEPTANCE_CRITERIA.md",
    "spec/04_NONFUNCTIONAL_REQUIREMENTS.md",
    "spec/05_DATA_MODEL.md",
    "spec/06_API_SPEC.md",
    "spec/07_UI_MAP.md",
    "spec/08_RISK_REGISTER.md",
    "spec/09_ROADMAP.md",
]

MIN_WORDS_PER_DOC = 200


def run_spec_gate(project_dir: Path) -> dict:
    """
    Phase 0 gate. Checks all 9 spec docs exist with real content.
    Writes spec_approval.json and spec_gate_report.md.
    """
    checks_passed = []
    checks_failed = []

    for f in ("scope.json", "stack.json"):
        p = project_dir / f
        if p.exists():
            checks_passed.append(f"{f} exists")
        else:
            checks_failed.append(f"{f} MISSING")

    for rel_path in REQUIRED_SPEC_DOCS:
        p = project_dir / rel_path
        if not p.exists():
            checks_failed.append(f"{rel_path} MISSING")
            continue
        word_count = len(p.read_text().split())
        if word_count < MIN_WORDS_PER_DOC:
            checks_failed.append(f"{rel_path} too short ({word_count} words, need {MIN_WORDS_PER_DOC})")
        else:
            checks_passed.append(f"{rel_path} OK ({word_count} words)")

    approved = len(checks_failed) == 0
    total = len(checks_passed) + len(checks_failed)
    result = {
        "phase": 0,
        "approved": approved,
        "score": round(len(checks_passed) / max(total, 1) * 10, 1),
        "checks_passed": len(checks_passed),
        "checks_total": total,
        "passed": checks_passed,
        "failed": checks_failed,
        "required_fixes": checks_failed,
        "next_step": "Proceed to Phase 1 (Build)" if approved else "Fix failed checks before building",
    }

    write_json(project_dir / "spec_approval.json", result)

    lines = [
        f"# Spec Gate Report — Phase 0\n",
        f"**Status:** {'APPROVED' if approved else 'BLOCKED'}\n",
        f"**Score:** {result['score']}/10\n",
        f"**Checks:** {result['checks_passed']}/{total}\n\n",
        "## Passed\n",
    ]
    for c in checks_passed:
        lines.append(f"- {c}\n")
    if checks_failed:
        lines.append("\n## Failed\n")
        for c in checks_failed:
            lines.append(f"- {c}\n")
    lines.append(f"\n**Next step:** {result['next_step']}\n")

    write_text(project_dir / "spec_gate_report.md", "".join(lines))
    return result


def run_build_gate(project_dir: Path) -> str:
    """Phase 1 gate — STUB."""
    result = {
        "phase": 1,
        "approved": False,
        "message": "[STUB] Build gate not yet implemented. Manual approval required.",
    }
    write_json(project_dir / "build_approval.json", result)
    return str(project_dir / "build_approval.json")


def run_launch_gate(project_dir: Path) -> str:
    """Phase 2 gate — STUB."""
    result = {
        "phase": 2,
        "approved": False,
        "message": "[STUB] Launch gate not yet implemented. Manual approval required.",
    }
    write_json(project_dir / "launch_approval.json", result)
    return str(project_dir / "launch_approval.json")
