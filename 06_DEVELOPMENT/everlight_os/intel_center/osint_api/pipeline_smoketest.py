"""
pipeline_smoketest.py -- walk every U.S. state code and assert:
  1. STATE_TO_CLOSER has an entry for it
  2. The mapped agent file exists in .claude/agents/
  3. voice_extractor.load_agent(slug) returns a non-default voice
     (i.e., it's actually parsed firmware, not the fallback)

Run standalone:
    python3 -m osint_api.pipeline_smoketest

Exits 0 on full coverage, 1 on any gap. Prints a per-state report so the
operator can see what's mapped to whom.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make osint_api importable when invoked from /mnt/sdcard/AA_MY_DRIVE
_ROOT = Path("/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/intel_center")
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from osint_api.marketing_pipeline import STATE_TO_CLOSER  # noqa: E402
from osint_api.voice_extractor import load_agent, _default_voice  # noqa: E402

AGENTS_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/.claude/agents")

# 50 states + DC. We don't ship to U.S. territories yet.
ALL_STATES = [
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
    "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
    "VT","VA","WA","WV","WI","WY",
]

DEFAULT_NAME = _default_voice()["name"]


def main() -> int:
    rows: list[tuple[str, str, str]] = []  # (state, slug, status)
    missing_states: list[str] = []
    missing_files: list[tuple[str, str]] = []
    default_voices: list[tuple[str, str]] = []

    for state in ALL_STATES:
        slug = STATE_TO_CLOSER.get(state)
        if not slug:
            missing_states.append(state)
            rows.append((state, "<unmapped>", "MISSING"))
            continue

        agent_file = AGENTS_DIR / f"{slug}.md"
        if not agent_file.exists():
            missing_files.append((state, slug))
            rows.append((state, slug, "FILE_MISSING"))
            continue

        voice = load_agent(slug)
        if voice.get("name") == DEFAULT_NAME:
            default_voices.append((state, slug))
            rows.append((state, slug, "DEFAULT_VOICE"))
            continue

        rows.append((state, slug, f"OK ({voice.get('name')})"))

    # Print report
    print(f"{'STATE':<6}{'CLOSER SLUG':<32}STATUS")
    print("-" * 72)
    for state, slug, status in rows:
        print(f"{state:<6}{slug:<32}{status}")
    print("-" * 72)
    print(f"Total: {len(ALL_STATES)} states  |  "
          f"OK: {len(ALL_STATES) - len(missing_states) - len(missing_files) - len(default_voices)}  "
          f"Missing-state: {len(missing_states)}  "
          f"Missing-file: {len(missing_files)}  "
          f"Default-voice: {len(default_voices)}")

    failures = len(missing_states) + len(missing_files) + len(default_voices)
    if failures:
        print(f"\nFAIL -- {failures} gap(s):")
        if missing_states:
            print(f"  Missing STATE_TO_CLOSER entries: {missing_states}")
        if missing_files:
            print(f"  Mapped agent files do not exist: {missing_files}")
        if default_voices:
            print(f"  Voice extractor fell back to default (firmware unparseable): {default_voices}")
        return 1

    print("\nPASS -- every state has a mapped closer with parseable voice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
