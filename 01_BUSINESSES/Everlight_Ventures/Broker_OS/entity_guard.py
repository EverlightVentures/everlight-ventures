#!/usr/bin/env python3
"""
Fail-closed entity guard for Everlight Ventures Broker OS.

No signable artifact -- contract template, the contract generator, or the
outbound sender-identity config -- may name a contracting party other than the
current canonical entity declared in entity_identity.py (which mirrors
BUSINESS_ENTITY_STATUS.md).

This exists because the 2026-06-01 stress test found FIVE conflicting principals
across the contract stack (Kill List #1, the only FATAL finding): a deal-sinking
misrepresentation + busted SB 909 disclosure + pierced-veil exposure. This guard
makes that class of drift impossible to ship.

Usage:
    python3 entity_guard.py            # scan; exit 1 on any violation
    python3 entity_guard.py --verbose  # also list the files scanned

Wire into pre-commit / CI. Exit code 0 = clean, 1 = violation(s) found.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import entity_identity as E  # noqa: E402

# Signable artifacts only. Internal SOPs/audits/analysis that legitimately
# *discuss* the LLC (e.g. BUSINESS_ENTITY_STATUS.md, the stress-test report) are
# intentionally out of scope -- they are not parties to anything.
WHOLESALE_CONFIG = HERE.parent / "Wholesale" / "config" / "sender_identity.json"

SCAN_DIRS = [
    HERE / "contracts",
    HERE / "wholesale_agent" / "contracts",
]
SCAN_FILES = [
    HERE / "contract_generator.py",
    WHOLESALE_CONFIG,
]
# Paths containing any of these segments are skipped (records, not templates).
SKIP_SEGMENTS = ("audits", "audit_", "/analysis/")


def _iter_targets():
    for d in SCAN_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.md")):
            if any(seg in str(p).lower() for seg in SKIP_SEGMENTS):
                continue
            yield p
    for f in SCAN_FILES:
        if f.is_file():
            yield f


def scan():
    violations = []
    scanned = []
    for path in _iter_targets():
        scanned.append(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # fail closed: an unreadable target is a violation
            violations.append((path, 0, "UNREADABLE: %s" % exc))
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for bad in E.FORBIDDEN_ENTITY_STRINGS:
                if bad in line:
                    violations.append((path, i, "names forbidden party %r" % bad))
    return scanned, violations


def main(argv):
    verbose = "--verbose" in argv or "-v" in argv
    scanned, violations = scan()

    if verbose:
        print("Canonical party (%s): %s" % (E.ENTITY_STATUS, E.ENTITY_LEGAL_NAME))
        print("Scanned %d artifact(s):" % len(scanned))
        for p in scanned:
            print("  - %s" % p)
        print()

    if violations:
        print("ENTITY GUARD FAILED -- %d violation(s):" % len(violations))
        for path, line, why in violations:
            loc = "%s:%d" % (path, line) if line else str(path)
            print("  X %s -- %s" % (loc, why))
        print()
        print("Fix: every contracting party must read as %r." % E.ENTITY_LEGAL_NAME)
        print("Do NOT hand-edit to a different entity -- flip entity_identity.ENTITY_STATUS instead.")
        return 1

    print("ENTITY GUARD PASSED -- %d artifact(s) clean; sole party is %r."
          % (len(scanned), E.ENTITY_LEGAL_NAME))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
