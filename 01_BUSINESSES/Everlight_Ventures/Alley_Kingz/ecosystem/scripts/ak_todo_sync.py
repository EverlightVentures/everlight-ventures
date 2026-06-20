#!/usr/bin/env python3
"""
ALLEY KINGZ -- TODO AUTO-SYNC (the check-off trigger)
=====================================================
Scans live signals (the CDN + the scaffolded module tree) and flips statuses in
ALLEY_KINGZ_TODO.md so progress is tracked without manual bookkeeping. Run at
session end, or on a cron/daemon (phone crond is dead -> run from e5 cron or a
hive_inner_startup daemon loop, or just `python3 ak_todo_sync.py`).

Status flip rule: a tracked item flips to [x] only when its CHECK passes live.
Idempotent. Prints a diff of what it flipped + the overall % done.
"""
import os, re, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ECO  = os.path.normpath(os.path.join(HERE, ".."))
TODO = os.path.join(ECO, "ALLEY_KINGZ_TODO.md")
CORE = os.path.join(ECO, "ALLEY_KINGZ_CORE")

def live_has(path, marker, timeout=10):
    """True if the live CDN file contains the marker (cache-busted)."""
    try:
        import time as _t
        url = "https://alleykingz.online/%s?cb=%d" % (path, int(_t.time()))
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return marker in r.read().decode("utf-8", "replace")
    except Exception:
        return False

def file_exists(rel):
    return os.path.exists(os.path.join(CORE, rel))

# Only AUTO-flip what can be VERIFIED truly done on the live edge (no over-claiming).
# Module/wave status is nuanced ([b] stub, [~] spec'd, [x] done+working) -> set manually
# from AK_BUILD_PLAN.md at session boundaries, not by mere file existence.
# (substring that identifies the TODO line, check -> bool). First match per line wins.
CHECKS = [
    # the active deploy blocker: flips to [x] ONLY when BOTH live markers are present
    ("hub_proto 1/8s dwell + Arena", lambda: live_has("hub_proto", "0.125") and live_has("index.html", "AK-HUBGO")),
]

def main():
    if not os.path.exists(TODO):
        print("no TODO at", TODO); return 1
    lines = open(TODO, encoding="utf-8").read().splitlines()
    flipped = []
    for i, ln in enumerate(lines):
        for needle, check in CHECKS:
            if needle in ln and re.search(r"\[( |~|!|b)\]", ln):
                if check():
                    lines[i] = re.sub(r"\[( |~|!|b)\]", "[x]", ln, count=1)
                    flipped.append(needle)
                break
    open(TODO, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    total = sum(1 for l in lines if re.search(r"\[( |x|~|!|b)\]", l))
    done  = sum(1 for l in lines if "[x]" in l)
    pct = (100 * done // total) if total else 0
    print("flipped:", flipped or "(none)")
    print("progress: %d/%d items done (%d%%)" % (done, total, pct))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
