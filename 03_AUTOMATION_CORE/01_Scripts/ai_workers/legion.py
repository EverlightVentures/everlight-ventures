#!/usr/bin/env python3
"""
LUCREX LEGION -- multi-Mother command front door.

Themed military ranks over the existing Hive engine (ai_workers delegates +
.claude/agents). No new orchestration engine -- this only routes to the
delegates you already own and merges their reports.

Ranks:
  legion status                      Show which Mothers are live.
  legion ltc  <mother> "<task>"      One Mother, one task.
  legion cpt  <m1,m2>  "<task>"      Coordinated strike (listed Mothers).
  legion maj  "<task>"               SWARM: every live Mother, in parallel.
  legion gen  <ticket>               Lucrex reads all reports -> ONE deliverable.

Options:
  --agent <name>   Prepend .claude/agents/<name>.md so any Mother plays that
                   role (the shared 121-agent pool -- one roster, five actors).
  --mode <m>       execute | plan | explain   (default: explain, read-only)
  --workspace <d>  Working directory (default: AA_MY_DRIVE)

Mothers: claude, codex, gemini, kimi, aider, perplexity
Reports: _logs/legion/reports/<ticket>/<mother>.md
"""

import argparse
import concurrent.futures
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
AI_WORKERS = WORKSPACE / "03_AUTOMATION_CORE" / "01_Scripts" / "ai_workers"
AGENTS_DIR = WORKSPACE / ".claude" / "agents"
REPORTS_ROOT = WORKSPACE / "_logs" / "legion" / "reports"

MAX_PARALLEL = 3  # proot is memory-constrained; cap concurrent Mothers.


def _delegate(script: str, mode: str) -> list:
    return [
        "python3",
        str(AI_WORKERS / script),
        "--raw",
        "--mode",
        mode,
        "--output-format",
        "text",
    ]


# name -> (binary that must exist, argv builder(mode) -> list; prompt appended last)
MOTHERS = {
    "claude": {
        # clx_delegate speaks {execute, plan, review}; map canonical explain -> review.
        "needs": "claude",
        "argv": lambda mode: _delegate("clx_delegate.py", "review" if mode == "explain" else mode),
        "desc": "King -- deepest reasoning",
    },
    "gemini": {
        "needs": "gemini",
        "argv": lambda mode: _delegate("gemx_delegate.py", mode),
        "desc": "alt-perspective, big context",
    },
    "kimi": {
        "needs": "kimi",
        "argv": lambda mode: _delegate("kimi_delegate.py", mode),
        "desc": "fast pragmatic coder",
    },
    "aider": {
        "needs": "aider",
        "argv": lambda mode: _delegate("aider_delegate.py", mode),
        "desc": "git-native editor (needs model+key)",
    },
    "codex": {
        # ChatGPT-account plan gates which models Codex accepts. Set CODEX_MODEL
        # to the one your plan allows (see `codex` TUI -> /model); otherwise use
        # codex's own config.toml default (no override).
        "needs": "codex",
        "argv": lambda mode: ["codex", "exec", "--skip-git-repo-check"] + (
            ["-c", f"model={os.environ['CODEX_MODEL']}"] if os.environ.get("CODEX_MODEL") else []
        ),
        "desc": "structured code (GPT)",
    },
    "perplexity": {
        "needs": "python3",
        "argv": lambda mode: ["python3", str(AI_WORKERS / "ppx_terminal.py")],
        "desc": "real-time research scout",
    },
}


def live_mothers() -> list:
    return [n for n, m in MOTHERS.items() if shutil.which(m["needs"])]


def load_agent(name: str) -> str:
    """Return an agent-persona preamble, or empty string if not found."""
    if not name:
        return ""
    path = AGENTS_DIR / (name if name.endswith(".md") else f"{name}.md")
    if not path.exists():
        print(f"[legion] agent '{name}' not found at {path}", file=sys.stderr)
        return ""
    body = path.read_text(errors="ignore")
    return (
        "You are operating in-character as the following Everlight Hive agent. "
        "You serve Lucrex, King of Divine Light -- the mind behind the money.\n"
        f"--- AGENT SPEC ({name}) ---\n{body}\n--- END AGENT SPEC ---\n\n"
    )


def run_mother(mother: str, prompt: str, mode: str, workspace: Path) -> dict:
    spec = MOTHERS[mother]
    argv = spec["argv"](mode) + [prompt]
    try:
        proc = subprocess.run(
            argv, cwd=str(workspace), capture_output=True, text=True, check=False
        )
        out = proc.stdout.strip() or proc.stderr.strip()
        return {"mother": mother, "ok": proc.returncode == 0, "output": out,
                "returncode": proc.returncode}
    except FileNotFoundError:
        return {"mother": mother, "ok": False, "output": f"{mother}: binary not found",
                "returncode": 127}


def write_report(ticket: str, mother: str, mode: str, task: str, result: dict) -> Path:
    d = REPORTS_ROOT / ticket
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{mother}.md"
    status = "OK" if result["ok"] else f"FAILED (rc={result['returncode']})"
    path.write_text(
        f"# Legion report -- {mother}\n"
        f"- ticket: {ticket}\n- mode: {mode}\n- status: {status}\n"
        f"- utc: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"## Task\n{task}\n\n## Output\n{result['output']}\n"
    )
    return path


def dispatch(mothers: list, task: str, mode: str, agent: str, workspace: Path,
             ticket: str, parallel: bool) -> list:
    preamble = load_agent(agent)
    prompt = preamble + task
    live = live_mothers()
    todo = [m for m in mothers if m in live]
    skipped = [m for m in mothers if m not in live]
    for s in skipped:
        print(f"[legion] SKIP {s} (not installed)", file=sys.stderr)

    results = []

    def _one(m):
        print(f"[legion] dispatch {m} ({mode})...", file=sys.stderr)
        res = run_mother(m, prompt, mode, workspace)
        rp = write_report(ticket, m, mode, task, res)
        print(f"[legion] {'OK ' if res['ok'] else 'ERR'} {m} -> {rp}", file=sys.stderr)
        return res

    if parallel and len(todo) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
            results = list(ex.map(_one, todo))
    else:
        results = [_one(m) for m in todo]
    return results


def synthesize(ticket: str, workspace: Path) -> int:
    d = REPORTS_ROOT / ticket
    reports = sorted(d.glob("*.md")) if d.exists() else []
    if not reports:
        print(f"[legion] no reports for ticket {ticket} at {d}", file=sys.stderr)
        return 1
    bundle = "\n\n".join(f"===== {r.stem} =====\n{r.read_text(errors='ignore')}"
                         for r in reports)
    synth_prompt = (
        "You are Lucrex synthesizing a multi-Mother swarm. Below are independent "
        "reports from different AI CLIs on the SAME task. Cross-check them: resolve "
        "conflicts, merge the best ideas, cite which Mother contributed which piece, "
        "and list anything you dropped and why. Produce ONE canonical deliverable.\n\n"
        f"{bundle}"
    )
    argv = _delegate("clx_delegate.py", "review") + [synth_prompt]
    print(f"[legion] GEN synthesizing {len(reports)} reports via Claude...", file=sys.stderr)
    proc = subprocess.run(argv, cwd=str(workspace), text=True, check=False)
    return proc.returncode


def cmd_status() -> int:
    live = set(live_mothers())
    print("LUCREX LEGION -- Mother status")
    for n, m in MOTHERS.items():
        mark = "LIVE " if n in live else "down "
        print(f"  [{mark}] {n:11s} {m['desc']}")
    print(f"\nAgents in shared pool: {len(list(AGENTS_DIR.glob('*.md')))}")
    return 0


def new_ticket() -> str:
    return "leg-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    p = argparse.ArgumentParser(description="Lucrex Legion multi-Mother command.")
    p.add_argument("rank", help="status | ltc | cpt | maj | gen")
    p.add_argument("rest", nargs="*", help="rank-specific args")
    p.add_argument("--mode", choices=["execute", "plan", "explain"], default="explain")
    p.add_argument("--agent", default="", help="agent persona from .claude/agents/")
    p.add_argument("--workspace", default=str(WORKSPACE))
    args = p.parse_args()

    rank = args.rank.lower()
    workspace = Path(args.workspace).resolve()
    ticket = new_ticket()

    if rank == "status":
        return cmd_status()

    if rank == "gen":
        if not args.rest:
            print("usage: legion gen <ticket>", file=sys.stderr)
            return 2
        return synthesize(args.rest[0], workspace)

    if rank == "ltc":
        if len(args.rest) < 2:
            print('usage: legion ltc <mother> "<task>"', file=sys.stderr)
            return 2
        mother, task = args.rest[0], " ".join(args.rest[1:])
        if mother not in MOTHERS:
            print(f"unknown mother '{mother}'. options: {', '.join(MOTHERS)}", file=sys.stderr)
            return 2
        dispatch([mother], task, args.mode, args.agent, workspace, ticket, parallel=False)
        print(f"\n[legion] ticket {ticket} -- reports in {REPORTS_ROOT / ticket}")
        return 0

    if rank == "cpt":
        if len(args.rest) < 2:
            print('usage: legion cpt <m1,m2> "<task>"', file=sys.stderr)
            return 2
        mothers = [m.strip() for m in args.rest[0].split(",") if m.strip()]
        task = " ".join(args.rest[1:])
        dispatch(mothers, task, args.mode, args.agent, workspace, ticket, parallel=True)
        print(f"\n[legion] ticket {ticket} -- synthesize with: legion gen {ticket}")
        return 0

    if rank == "maj":
        if not args.rest:
            print('usage: legion maj "<task>"', file=sys.stderr)
            return 2
        task = " ".join(args.rest)
        dispatch(list(MOTHERS), task, args.mode, args.agent, workspace, ticket, parallel=True)
        print(f"\n[legion] ticket {ticket} -- synthesize with: legion gen {ticket}")
        return 0

    print(f"unknown rank '{rank}'. use: status | ltc | cpt | maj | gen", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
