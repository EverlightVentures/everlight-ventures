#!/usr/bin/env python3
"""
Regression tests for the canonical entity guard.

    python3 test_entity_guard.py

Locks the FATAL-finding fix from the 2026-06-01 stress test: the contract stack
must name exactly one canonical contracting party, and the guard must fail closed
the moment a forbidden party reappears.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import entity_identity as E  # noqa: E402


def test_canonical_is_sole_prop():
    assert E.ENTITY_STATUS == "sole_prop", E.ENTITY_STATUS
    assert E.ENTITY_LEGAL_NAME == "Richard Gee, an individual, doing business as Everlight Ventures"
    for bad in ("Everlight Logistics LLC", "Everlight Ventures, LLC", "Marquise Smith"):
        assert bad in E.FORBIDDEN_ENTITY_STRINGS, "missing from forbidden list: %r" % bad


def _run_guard():
    return subprocess.run(
        [sys.executable, str(HERE / "entity_guard.py")],
        capture_output=True, text=True,
    )


def test_clean_tree_passes():
    r = _run_guard()
    assert r.returncode == 0, "guard should PASS on a clean tree:\n%s%s" % (r.stdout, r.stderr)
    assert "PASSED" in r.stdout


def test_planted_violation_fails_closed():
    canary = HERE / "contracts" / "_entity_guard_selftest.md"
    canary.write_text("Buyer: Everlight Logistics LLC\n", encoding="utf-8")
    try:
        r = _run_guard()
        assert r.returncode == 1, "guard MUST fail when a forbidden party is present"
        assert "Everlight Logistics LLC" in r.stdout
        assert "_entity_guard_selftest.md" in r.stdout
    finally:
        canary.unlink(missing_ok=True)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print("PASS", fn.__name__)
    print("\nAll %d entity-guard tests passed." % len(tests))
