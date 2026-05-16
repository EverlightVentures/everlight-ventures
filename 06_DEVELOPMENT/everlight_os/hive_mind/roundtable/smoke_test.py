"""Smoke test for the Hive Roundtable engine.

Runs a synthetic, no-PII, no-real-stakes question through the full 5-phase
pipeline in --mock mode. Validates:
  - Dossier loading from .claude/agents/
  - Eradication gate pre-flight
  - All 5 phases execute without error
  - Transcript + synthesis + disagreements parse correctly
  - Archive file lands in 08_BACKUPS/roundtables/
  - Publish path is skipped cleanly in mock mode

This test runs WITHOUT spending Anthropic tokens. To run with real LLM calls
(on Oracle where the SDK is installed), drop the --mock flag and supply real
participant keys via the CLI.

Usage:
    python3 smoke_test.py            # mock mode (default)
    python3 smoke_test.py --real     # real API mode (needs anthropic SDK)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the roundtable module importable when run as a script
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR.parent.parent) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR.parent.parent))

from hive_mind.roundtable.roundtable import roundtable, RoundtableError

# --- Smoke test config ------------------------------------------------------
SMOKE_QUESTION = (
    "Should an early-stage operator allocate 20% of working capital to a "
    "BTC/ETH treasury reserve, or keep 100% in USD for operational runway?"
)
SMOKE_CONTEXT = (
    "Synthetic smoke-test scenario. No real operator, no real capital, no real "
    "decisions are being made. This run validates the roundtable engine end to end."
)
SMOKE_PARTICIPANTS = ["bull_archer", "cipher_wolfe", "pitch_adler"]


def run_smoke(real: bool = False) -> int:
    mode = "REAL API" if real else "MOCK"
    print(f"== Hive Roundtable Smoke Test ({mode}) ==\n")
    print(f"Question: {SMOKE_QUESTION}")
    print(f"Participants: {', '.join(SMOKE_PARTICIPANTS)}\n")

    try:
        result = roundtable(
            question=SMOKE_QUESTION,
            participants=SMOKE_PARTICIPANTS,
            context=SMOKE_CONTEXT,
            channel="#war-room",
            publish=False if not real else True,  # never publish in mock mode
            smoke_test=True,
            mock=not real,
        )
    except RoundtableError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"FAIL (unexpected): {type(e).__name__}: {e}", file=sys.stderr)
        return 3

    # Validation checks
    checks = []

    checks.append(("Participants loaded", len(result["participants"]) == 3))
    checks.append(("Transcript present", bool(result.get("transcript"))))
    checks.append(("Synthesis present", bool(result.get("synthesis"))))
    checks.append(("Disagreements field exists", "disagreements" in result))
    checks.append(("Archive path set", bool(result.get("archive_path"))))
    if result.get("archive_path"):
        checks.append(("Archive file exists on disk", Path(result["archive_path"]).exists()))
    checks.append(("Smoke test flag = True", result.get("smoke_test") is True))
    checks.append(("Mock flag matches mode", result.get("mock") == (not real)))
    checks.append(("Elapsed time recorded", isinstance(result.get("elapsed_s"), (int, float))))
    checks.append(("No errors in errors[]", len(result.get("errors", [])) == 0))

    all_pass = all(passed for _, passed in checks)
    for label, passed in checks:
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {label}")

    print(f"\nElapsed: {result.get('elapsed_s', '?')}s")
    print(f"Participants (display): {result['participants']}")
    print(f"Unresolved disagreements: {len(result.get('disagreements', []))}")
    if result.get("archive_path"):
        print(f"Archive: {result['archive_path']}")

    if not all_pass:
        print(f"\nFULL RESULT:\n{json.dumps({k: v for k, v in result.items() if k not in ('transcript', 'synthesis')}, indent=2, default=str)}")
        return 1

    print("\n== ALL SMOKE TEST CHECKS PASSED ==")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Hive Roundtable smoke test")
    parser.add_argument(
        "--real", action="store_true",
        help="Run with real Anthropic API (needs SDK + spends tokens). Default is mock.",
    )
    args = parser.parse_args()
    return run_smoke(real=args.real)


if __name__ == "__main__":
    sys.exit(main())
