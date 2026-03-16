#!/usr/bin/env python3
"""
AI Router - Routes queries to the best AI tool for the job
Usage: ask "your question here"
       ask --ppx "latest crypto news"       (force Perplexity)
       ask --gm  "write a python function"  (force Gemini)
       ask --cl  "analyze this codebase"    (force Claude)
       ask --ai  "general question"         (force GPT)
       ask --cx  "code focused request"     (force Codex)
"""

import re
import subprocess
import sys
import shutil


TOOLS = {
    "ppx": {
        "name": "Perplexity",
        "cmd": ["python3", "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/ppx_terminal.py"],
        "desc": "real-time research",
    },
    "gm": {
        "name": "Gemini",
        "cmd": [
            "python3",
            "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/gemx_delegate.py",
            "--raw",
            "--mode",
            "explain",
            "--output-format",
            "text",
        ],
        "desc": "memory-driven explain mode",
    },
    "cl": {
        "name": "Claude",
        "cmd": [
            "python3",
            "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/clx_delegate.py",
            "--raw",
            "--mode",
            "review",
            "--output-format",
            "text",
        ],
        "desc": "review-mode reasoning with hooks",
    },
    "ai": {
        "name": "GPT",
        "cmd": ["python3", "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/ai_terminal.py"],
        "desc": "general queries",
    },
    "cx": {
        "name": "Codex",
        "cmd": ["python3", "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ai_workers/cx_terminal.py"],
        "desc": "code generation",
    },
}

RESEARCH_PATTERNS = [
    r"\b(latest|current|news|today|202\d)\b",
    r"\b(what is|who is|when did|where is|how much)\b",
    r"\b(price|stock|weather|stats|statistics)\b",
    r"\b(research|find out|look up|search)\b",
]

CODE_PATTERNS = [
    r"\b(write|create|implement|build)\b.*\b(code|function|class|script|api|app)\b",
    r"\b(python|javascript|rust|go|java|typescript|bash|sql)\b",
    r"\b(error|exception|bug|crash|traceback)\b",
    r"\b(fix|debug|refactor|optimize)\b.*\b(code|function|script)\b",
]

REASONING_PATTERNS = [
    r"\b(explain|analyze|review|compare|evaluate)\b",
    r"\b(this file|this project|this codebase|this repo)\b",
    r"\b(architecture|design|trade.?off|pros and cons)\b",
    r"\b(why|how does|what happens when)\b.*\b(work|happen|cause)\b",
]


def detect_tool(query: str) -> str:
    q = query.lower()

    for pat in RESEARCH_PATTERNS:
        if re.search(pat, q):
            return "ppx"

    for pat in REASONING_PATTERNS:
        if re.search(pat, q):
            return "cl"

    for pat in CODE_PATTERNS:
        if re.search(pat, q):
            return "gm"

    return "ai"


def run_tool(tool_key: str, query: str):
    tool = TOOLS[tool_key]
    cmd = tool["cmd"] + [query]

    # Check if the binary exists
    if not shutil.which(cmd[0]):
        print(f"[!] {tool['name']} ({cmd[0]}) not found in PATH")
        sys.exit(1)

    print(f"[ask] Routing to {tool['name']} ({tool['desc']})")
    print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print()


def show_help():
    print("ask - Smart AI Router")
    print()
    print("Usage: ask \"your question\"")
    print("       ask --TOOL \"your question\"")
    print()
    print("Auto-routing logic:")
    print("  Research/news/prices  -> ppx (Perplexity)")
    print("  Explain/analyze/why   -> cl  (Claude)")
    print("  Write code/fix bugs   -> gm  (Gemini)")
    print("  Everything else       -> ai  (GPT)")
    print()
    print("Force a specific tool:")
    for key, tool in TOOLS.items():
        print(f"  --{key:4s}  {tool['name']:12s} ({tool['desc']})")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)

    args = sys.argv[1:]
    force_tool = None

    # Check for --tool flag
    if args[0].startswith("--"):
        flag = args[0][2:]
        if flag in ("help", "h"):
            show_help()
            sys.exit(0)
        if flag in TOOLS:
            force_tool = flag
            args = args[1:]
        # Also accept long names
        name_map = {t["name"].lower(): k for k, t in TOOLS.items()}
        if flag in name_map:
            force_tool = name_map[flag]
            args = args[1:]

    if not args:
        show_help()
        sys.exit(0)

    query = " ".join(args)
    tool_key = force_tool or detect_tool(query)
    run_tool(tool_key, query)


if __name__ == "__main__":
    main()
