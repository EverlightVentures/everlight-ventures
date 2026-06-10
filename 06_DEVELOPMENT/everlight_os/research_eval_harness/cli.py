"""cli.py -- one entry point for the harness.

Usage:
    python -m research_eval_harness run --paper N --condition X --seeds K [--dry-run]
    python -m research_eval_harness aggregate --paper N --runs runs/paperN/
    python -m research_eval_harness verify --manifest path/to/manifest.json
    python -m research_eval_harness list-conditions [--paper N]

All real work raises NotImplementedError until Rich greenlights SPEC.md §9.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import PAPERS, SUPPORTED_CONDITIONS, SUPPORTED_METRICS, __version__


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="research_eval_harness",
        description="Shared eval harness for the 3-paper Anthropic bridge portfolio.",
    )
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Execute one condition x seed batch.")
    run.add_argument("--paper", type=int, choices=PAPERS, required=True)
    run.add_argument("--condition", type=str, required=True)
    run.add_argument("--seeds", type=int, default=3, help="Number of seeds (default 3).")
    run.add_argument("--n-probes", type=int, default=None, help="Override probe count.")
    run.add_argument("--output", type=Path, default=Path("runs"))
    run.add_argument("--dry-run", action="store_true", help="Estimate cost, no API calls.")
    run.add_argument("--force-budget", action="store_true", help="Override budget cap (hard-abort floor still enforced).")
    run.add_argument("--budget", type=Path, default=Path(__file__).parent / "budget.yaml")
    run.add_argument("--mock", action="store_true", help="Use canned LLM responses (no spend).")

    agg = sub.add_parser("aggregate", help="Aggregate across conditions + emit summary.")
    agg.add_argument("--paper", type=int, choices=PAPERS, required=True)
    agg.add_argument("--runs", type=Path, required=True)
    agg.add_argument("--publish", action="store_true", help="Publish branded Google Doc + Slack card.")

    verify = sub.add_parser("verify", help="Reload a manifest and report reproducibility status.")
    verify.add_argument("--manifest", type=Path, required=True)

    lst = sub.add_parser("list-conditions", help="List supported conditions per paper.")
    lst.add_argument("--paper", type=int, choices=PAPERS, default=None)

    return p


def _cmd_run(args: argparse.Namespace) -> int:
    valid = SUPPORTED_CONDITIONS[args.paper]
    if args.condition not in valid:
        sys.stderr.write(f"Condition {args.condition!r} not valid for paper {args.paper}. Valid: {valid}\n")
        return 2
    raise NotImplementedError(
        "TODO: 1) load budget; 2) load probes for paper; 3) instantiate condition; 4) estimate cost;"
        " 5) abort if over cap unless --force; 6) hive_logger.start; 7) loop probes x seeds, call apply;"
        " 8) score metrics; 9) write events.jsonl + metrics.json + manifest.json per seed"
    )


def _cmd_aggregate(args: argparse.Namespace) -> int:
    raise NotImplementedError(
        "TODO: glob runs/paperN/<condition>/<seed>/metrics.json; group by condition; build pairs;"
        " call aggregator.aggregate; print summary path"
    )


def _cmd_verify(args: argparse.Namespace) -> int:
    raise NotImplementedError("TODO: manifest.verify(args.manifest); pretty-print diff report")


def _cmd_list(args: argparse.Namespace) -> int:
    papers = [args.paper] if args.paper else list(PAPERS)
    for p in papers:
        print(f"Paper {p}:")
        print(f"  conditions: {', '.join(SUPPORTED_CONDITIONS[p])}")
        print(f"  metrics:    {', '.join(SUPPORTED_METRICS[p])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "run": _cmd_run,
        "aggregate": _cmd_aggregate,
        "verify": _cmd_verify,
        "list-conditions": _cmd_list,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
