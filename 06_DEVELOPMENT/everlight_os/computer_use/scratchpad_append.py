#!/usr/bin/env python3
"""scratchpad_append -- one canonical way for any side (CLI or Computer) to
append a labeled block to /tmp/tandem/scratch.md atomically.

Why this exists (Rich, 2026-05-07): in the wholesale-dashboard tandem run,
Computer burned 13 of 16 iterations fighting with shell heredoc syntax to
append its observations to the shared scratchpad. It tried sed -i, cat <<EOF,
python -c "...", and 5 other variants before one succeeded -- by then it was
out of iterations and the PLAN_NEEDED escalation never fired.

This script is the ONE pattern Computer (and CLI) call. One bash line. No
heredoc. No retry. Atomic (file-locked). Always works.

Usage from Computer's brief:
  /AA_MY_DRIVE/.venv/bin/python3 \\
      /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use/scratchpad_append.py \\
      "Computer / Sonnet 4.5" \\
      "KPIs visible: Total=32 | Phase3=18 ..."

Special section labels with magic behavior:
  PLAN_NEEDED       -- writes under '## PLAN_NEEDED escalations' instead of EOF
  ASK->CLI          -- writes under '## Asks + answers (live)'
  ASK->COMP         -- same
  COMPUTER_DONE     -- writes the block AND touches /tmp/tandem/computer_done.flag
  CLI_DONE          -- writes the block AND touches /tmp/tandem/cli_done.flag

For everything else (e.g. "Computer / Sonnet 4.5", "CLI / Opus 4.7"), the block
is appended to the end of the scratchpad with a timestamp.
"""
from __future__ import annotations

import argparse
import fcntl
import sys
import time
from pathlib import Path

SCRATCH = Path("/tmp/tandem/scratch.md")
COMPUTER_DONE_FLAG = Path("/tmp/tandem/computer_done.flag")
CLI_DONE_FLAG = Path("/tmp/tandem/cli_done.flag")


def _insert_under_section(text: str, section_header: str, block: str) -> str:
    """Insert block after the section_header line, replacing '[empty]' or
    '[none yet]' placeholder if present. Falls back to append-at-end if the
    section isn't found.
    """
    lines = text.splitlines()
    out = []
    inserted = False
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if not inserted and lines[i].strip() == section_header.strip():
            # find the placeholder line (next 1-5 lines)
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].strip() in ("[empty]", "[none yet]", "[awaiting]"):
                    # skip past the placeholder; insert block in its place
                    for line in block.splitlines():
                        out.append(line)
                    i = j  # advance past the placeholder
                    inserted = True
                    break
            if not inserted:
                # no placeholder; just insert the block right after the header
                for line in block.splitlines():
                    out.append(line)
                inserted = True
        i += 1
    if not inserted:
        out.append("")
        out.extend(block.splitlines())
    return "\n".join(out) + ("\n" if not text.endswith("\n") else "")


def append(section: str, body: str) -> dict:
    SCRATCH.parent.mkdir(parents=True, exist_ok=True)
    if not SCRATCH.exists():
        SCRATCH.write_text("# tandem scratchpad\n", encoding="utf-8")

    ts = time.strftime("%H:%M:%S")
    header = f"\n[{section}] -- {ts} PT"
    block = f"{header}\n{body.rstrip()}\n"

    with SCRATCH.open("r+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            text = f.read()

            if section == "PLAN_NEEDED":
                text = _insert_under_section(
                    text, "## PLAN_NEEDED escalations", block
                )
            elif section in ("ASK->CLI", "ASK->COMP", "ANS->CLI", "ANS->COMP"):
                text = _insert_under_section(
                    text, "## Asks + answers (live)", block
                )
            else:
                text += block

            f.seek(0)
            f.truncate()
            f.write(text)
            f.flush()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

    flag_set = None
    if section == "COMPUTER_DONE":
        COMPUTER_DONE_FLAG.touch()
        flag_set = str(COMPUTER_DONE_FLAG)
    elif section == "CLI_DONE":
        CLI_DONE_FLAG.touch()
        flag_set = str(CLI_DONE_FLAG)

    return {
        "ok": True,
        "section": section,
        "bytes_added": len(block),
        "flag_set": flag_set,
        "scratch_path": str(SCRATCH),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Append a labeled block to the tandem scratchpad")
    p.add_argument("section", help='Section label, e.g. "Computer / Sonnet 4.5", "PLAN_NEEDED", "COMPUTER_DONE"')
    p.add_argument("body", help="Body text (multi-line OK; quote it)")
    args = p.parse_args()

    result = append(args.section, args.body)
    print(f"appended {result['bytes_added']} bytes to {result['scratch_path']} "
          f"(section={result['section']}{', flag=' + result['flag_set'] if result['flag_set'] else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
