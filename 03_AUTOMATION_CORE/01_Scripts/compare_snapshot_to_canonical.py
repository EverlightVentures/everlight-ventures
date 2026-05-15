#!/usr/bin/env python3
"""
compare_snapshot_to_canonical.py -- full compare-and-contrast of a frozen
snapshot tree against the live canonical tree.

The sprawl problem: work migrated Oracle -> phone -> Dell -> PC as connections
dropped. Each hop may have left unique config/settings work behind. Before a
snapshot can be safely archived, we must prove every file in it is either
(a) already in canonical at an equal-or-newer version, or
(b) surfaced as UNIQUE / SNAPSHOT-NEWER so it can be merged forward.

Categories per file:
  UNIQUE            -- path not in canonical at all          -> MERGE candidate
  SNAPSHOT_NEWER    -- snapshot mtime newer than canonical    -> MERGE candidate (review)
  SAMETIME_DIFFSIZE -- same mtime, different size             -> SUSPICIOUS, review
  CANONICAL_NEWER   -- canonical is newer                     -> safe, snapshot is stale
  IDENTICAL         -- same mtime + size                      -> safe, fully captured

Usage:
  compare_snapshot_to_canonical.py <snapshot_root> <canonical_root> <out_prefix>

Example:
  compare_snapshot_to_canonical.py \
    /home/richgee/phone_rescue_2026-05-03/AA_MY_DRIVE \
    /AA_MY_DRIVE \
    /AA_MY_DRIVE/_audit/phone_rescue_vs_canonical

Outputs (next to out_prefix):
  <out_prefix>.summary.txt   -- counts + the headline numbers
  <out_prefix>.unique.txt    -- every UNIQUE file (rel path, size, mtime)
  <out_prefix>.newer.txt     -- every SNAPSHOT_NEWER + SAMETIME_DIFFSIZE file
"""

from __future__ import annotations
import os
import sys
import time

MTIME_TOLERANCE = 2  # seconds -- fs mtime granularity / rsync rounding


def walk_files(root: str):
    """Yield (relpath, full_path) for every regular file under root."""
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        # skip noise that's regenerable or version-control internals
        dirnames[:] = [d for d in dirnames
                       if d not in ('.git', 'node_modules', '__pycache__', '.cache')]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if os.path.islink(full):
                continue
            rel = os.path.relpath(full, root)
            yield rel, full


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2

    snap_root, canon_root, out_prefix = argv[1], argv[2], argv[3]

    if not os.path.isdir(snap_root):
        print(f"FATAL: snapshot root not a dir: {snap_root}", file=sys.stderr)
        return 3
    if not os.path.isdir(canon_root):
        print(f"FATAL: canonical root not a dir: {canon_root}", file=sys.stderr)
        return 3

    os.makedirs(os.path.dirname(out_prefix), exist_ok=True)

    counts = {
        'UNIQUE': 0, 'SNAPSHOT_NEWER': 0, 'SAMETIME_DIFFSIZE': 0,
        'CANONICAL_NEWER': 0, 'IDENTICAL': 0, 'TOTAL': 0,
    }
    unique_lines: list[str] = []
    newer_lines: list[str] = []

    for rel, snap_full in walk_files(snap_root):
        counts['TOTAL'] += 1
        try:
            s_st = os.stat(snap_full)
        except OSError:
            continue
        canon_full = os.path.join(canon_root, rel)

        if not os.path.exists(canon_full):
            counts['UNIQUE'] += 1
            unique_lines.append(f"{int(s_st.st_mtime)}\t{s_st.st_size}\t{rel}")
            continue

        try:
            c_st = os.stat(canon_full)
        except OSError:
            # canonical path exists but unreadable -- treat as unique-ish, flag
            counts['UNIQUE'] += 1
            unique_lines.append(f"{int(s_st.st_mtime)}\t{s_st.st_size}\t{rel}\t[canon-unreadable]")
            continue

        dt = s_st.st_mtime - c_st.st_mtime
        if dt > MTIME_TOLERANCE:
            counts['SNAPSHOT_NEWER'] += 1
            newer_lines.append(
                f"SNAPSHOT_NEWER\t{int(s_st.st_mtime)}\t{int(c_st.st_mtime)}\t"
                f"{s_st.st_size}\t{c_st.st_size}\t{rel}")
        elif abs(dt) <= MTIME_TOLERANCE:
            if s_st.st_size == c_st.st_size:
                counts['IDENTICAL'] += 1
            else:
                counts['SAMETIME_DIFFSIZE'] += 1
                newer_lines.append(
                    f"SAMETIME_DIFFSIZE\t{int(s_st.st_mtime)}\t{int(c_st.st_mtime)}\t"
                    f"{s_st.st_size}\t{c_st.st_size}\t{rel}")
        else:
            counts['CANONICAL_NEWER'] += 1

    # ----- write outputs -----
    with open(f"{out_prefix}.unique.txt", 'w') as f:
        f.write("# mtime_epoch\tsize_bytes\trelpath\n")
        f.write("\n".join(sorted(unique_lines)))
        f.write("\n")

    with open(f"{out_prefix}.newer.txt", 'w') as f:
        f.write("# category\tsnap_mtime\tcanon_mtime\tsnap_size\tcanon_size\trelpath\n")
        f.write("\n".join(sorted(newer_lines)))
        f.write("\n")

    actionable = counts['UNIQUE'] + counts['SNAPSHOT_NEWER'] + counts['SAMETIME_DIFFSIZE']
    safe = counts['CANONICAL_NEWER'] + counts['IDENTICAL']
    summary = f"""compare_snapshot_to_canonical -- {time.strftime('%Y-%m-%d %H:%M:%S %Z')}
snapshot : {snap_root}
canonical: {canon_root}

  TOTAL files scanned : {counts['TOTAL']}
  ------------------------------------------------
  UNIQUE              : {counts['UNIQUE']:>8}   <- not in canonical, MERGE candidate
  SNAPSHOT_NEWER      : {counts['SNAPSHOT_NEWER']:>8}   <- snapshot is newer, REVIEW + merge
  SAMETIME_DIFFSIZE   : {counts['SAMETIME_DIFFSIZE']:>8}   <- same mtime diff size, SUSPICIOUS
  ------------------------------------------------
  CANONICAL_NEWER     : {counts['CANONICAL_NEWER']:>8}   <- canonical fresher, snapshot stale (safe)
  IDENTICAL           : {counts['IDENTICAL']:>8}   <- fully captured already (safe)
  ================================================
  ACTIONABLE (review) : {actionable:>8}
  SAFE (no action)    : {safe:>8}

verdict: {'SAFE TO ARCHIVE -- everything captured' if actionable == 0 else f'{actionable} files need a merge decision before archive'}

detail files:
  {out_prefix}.unique.txt   ({counts['UNIQUE']} rows)
  {out_prefix}.newer.txt    ({counts['SNAPSHOT_NEWER'] + counts['SAMETIME_DIFFSIZE']} rows)
"""
    with open(f"{out_prefix}.summary.txt", 'w') as f:
        f.write(summary)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
