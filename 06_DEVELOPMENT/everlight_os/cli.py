#!/usr/bin/env python3
"""
Everlight OS — CLI entry point.
Usage:
    python3 cli.py "trade report"
    python3 cli.py "trade status"
    python3 cli.py "post how to pick an XLM wallet"
    python3 cli.py "post link https://example.com"
    python3 cli.py "book Sam and Robo learn patience"
    python3 cli.py "everlight status"
"""

import logging
import sys
import os
from pathlib import Path

# Ensure everlight_os is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load env vars
try:
    from dotenv import load_dotenv
    load_dotenv(Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env"))
except ImportError:
    pass

from everlight_os.core.router import classify
from everlight_os.core.orchestrator import Orchestrator
from everlight_os.core.filesystem import trading_report_dir, content_project_dir, books_project_dir, saas_project_dir, slugify
from everlight_os.core.contracts import ProjectState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("everlight")


def _build_orchestrator() -> Orchestrator:
    """Create orchestrator with all engine handlers registered."""
    orch = Orchestrator()

    # Register trading engine handlers
    from everlight_os.modules.trading_engine import register_handlers as reg_trading
    reg_trading(orch)

    # Register content engine handlers (if available)
    try:
        from everlight_os.modules.content_engine import register_handlers as reg_content
        reg_content(orch)
    except (ImportError, Exception) as e:
        logger.debug(f"Content engine not loaded: {e}")

    # Register books engine handlers (if available)
    try:
        from everlight_os.modules.books_engine import register_handlers as reg_books
        reg_books(orch)
    except (ImportError, Exception) as e:
        logger.debug(f"Books engine not loaded: {e}")

    # Register saas engine handlers (if available)
    try:
        from everlight_os.modules.saas_engine import register_handlers as reg_saas
        reg_saas(orch)
    except (ImportError, Exception) as e:
        logger.debug(f"SaaS engine not loaded: {e}")

    return orch


def _get_project_dir(route) -> Path:
    """Determine project directory based on engine type."""
    if route.engine == "trading":
        return trading_report_dir()
    elif route.engine == "content":
        # Extract topic for slug
        return content_project_dir(slugify(route.metadata.get("topic", "untitled")))
    elif route.engine == "books":
        series = route.metadata.get("series", "adventures_with_sam")
        title = route.metadata.get("title", "untitled")
        return books_project_dir(series, title)
    elif route.engine == "saas":
        slug = route.metadata.get("slug", slugify(route.metadata.get("product", "untitled")))
        return saas_project_dir(slug)
    else:
        return trading_report_dir()  # fallback


def _handle_status():
    """Handle 'everlight status' — aggregate all engines."""
    from everlight_os.modules.trading_engine.analyzer import read_state, read_snapshot
    from everlight_os.core import log as elog
    from everlight_os.core.slack_client import get_client

    print("\n=== EVERLIGHT STATUS ===\n")

    # Trading
    state = read_state()
    snapshot = read_snapshot()
    print("TRADING:")
    print(f"  Equity: ${state.get('equity_start_usd', 0):.2f}")
    print(f"  PnL today: ${state.get('pnl_today_usd', 0):.2f}")
    print(f"  Position: {'OPEN' if state.get('open_position') else 'FLAT'}")
    print(f"  Regime: {snapshot.get('regime', '?')} / Vol: {snapshot.get('vol_phase', '?')}")
    print(f"  Last cycle: {state.get('last_cycle_ts', '?')}")

    # Recent runs
    recent = elog.read_recent_runs(5)
    print(f"\nRECENT RUNS ({len(recent)}):")
    for r in recent:
        print(f"  [{r.get('status', '?')}] {r.get('engine', '?')}/{r.get('intent', '?')} — {r.get('timestamp', '?')[:19]}")

    # System
    runs_today = elog.count_runs_today()
    print(f"\nSYSTEM:")
    print(f"  Runs today: {runs_today}")

    slack = get_client()
    print(f"  Slack: {'connected' if slack.enabled else 'not configured'}")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    request = " ".join(sys.argv[1:])
    logger.info(f"Request: {request}")

    # Parse optional URL
    url = None
    words = request.split()
    for w in words:
        if w.startswith("http://") or w.startswith("https://"):
            url = w
            request = request.replace(w, "").strip()

    # Route
    route = classify(request, url=url)
    logger.info(f"Route: engine={route.engine} intent={route.intent} confidence={route.confidence:.2f} steps={len(route.steps)}")

    # Handle status specially
    if route.engine == "status":
        _handle_status()
        return

    if not route.steps:
        print(f"No steps defined for engine={route.engine} intent={route.intent}")
        sys.exit(1)

    # Enrich route metadata with parsed info
    if route.engine == "content":
        # Strip "post" prefix for topic
        topic = request.lower()
        for prefix in ("post ", "post: ", "content ", "write "):
            if topic.startswith(prefix):
                topic = topic[len(prefix):]
        route.metadata["topic"] = topic.strip()
    elif route.engine == "books":
        # Strip "book" prefix for title
        title = request.lower()
        for prefix in ("book ", "book: ", "new book "):
            if title.startswith(prefix):
                title = title[len(prefix):]
        route.metadata["title"] = title.strip()
        route.metadata["series"] = "adventures_with_sam"
    elif route.engine == "saas":
        # Strip "build saas:" prefix for product idea
        idea = request
        for prefix in ("build saas:", "build saas ", "saas: ", "saas "):
            if idea.lower().startswith(prefix):
                idea = idea[len(prefix):]
        route.metadata["idea"] = idea.strip()
        route.metadata["product"] = idea.strip()
        route.metadata["slug"] = slugify(idea.strip())

    # Get project directory
    project_dir = _get_project_dir(route)
    logger.info(f"Project dir: {project_dir}")

    # Build and run orchestrator
    orch = _build_orchestrator()
    state = orch.run(route, request, project_dir)

    # Summary
    print(f"\n{'='*60}")
    print(f"Project: {state.id}")
    print(f"Status: {state.status}")
    print(f"Engine: {state.engine}/{state.intent}")
    print(f"Steps: {sum(1 for s in state.steps if s.get('status') == 'done')}/{len(state.steps)} completed")
    if state.artifacts:
        print(f"Artifacts:")
        for a in state.artifacts:
            print(f"  {a}")
    if state.errors:
        print(f"Errors:")
        for e in state.errors:
            print(f"  {e}")
    print(f"Output: {project_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
