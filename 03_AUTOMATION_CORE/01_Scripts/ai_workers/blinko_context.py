#!/usr/bin/env python3
"""
Blinko Context Retriever - quick RAG query for Claude Code pre-conversation context.

Used by the hive dispatcher to pull relevant past decisions before routing.
Can also be called standalone:

    python blinko_context.py "stripe integration recommendations"
    python blinko_context.py --ai "what was the last XLM trade decision?"
"""
from __future__ import annotations

import sys
from pathlib import Path

# Import from sibling module
sys.path.insert(0, str(Path(__file__).parent))
from blinko_bridge import query_context


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: blinko_context.py [--ai] <question>")
        return 1

    use_ai = "--ai" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--ai"]
    question = " ".join(args)

    result = query_context(question, use_ai=use_ai)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
