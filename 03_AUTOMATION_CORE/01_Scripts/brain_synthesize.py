#!/usr/bin/env python3
"""
brain_synthesize.py -- the brain's TIER-2 layer (cognition, not storage).

The brain has ~1,665 raw notes (tier 1). Many are noise (sync/deploy/heartbeat
logs). A pile of logs is not a brain. This builds the connective tissue Rich asked
for: TRAIL notes that thread raw notes into a thought-process --
    what we KNEW  ->  what we KNOW now  ->  how it AFFECTS the mission (Deal 1).
Each trail links its constituent note ids so the thoughts understand each other.

Three-tier knowledge discipline (skill: karpathy_rag_intake):
  tier 1 = raw notes (the 1,665)         <- storage
  tier 2 = trails / synthesis (this)     <- cognition  [#hive/trail]
  tier 3 = the deliverable / decision    <- action

Commands:
  python3 brain_synthesize.py --stats              # signal-vs-noise per theme
  python3 brain_synthesize.py --bundle wholesale   # high-signal notes for a theme
  python3 brain_synthesize.py --wholesale-trail    # author+ingest the wholesale trail
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
BRAIN_DB = ROOT / "_logs" / "blinko_lite.db"
BLINKO_CANDIDATES = [
    "http://127.0.0.1:2700/api/v1/note/upsert",
    "http://127.0.0.1:1111/api/v1/note/upsert",
    "http://e5-mother:1111/api/v1/note/upsert",
]

# Notes that are operational exhaust, not knowledge. Filtered from the cognition view.
NOISE_PATTERNS = [
    r"sync complete: 0 items", r"^#\s*hive sync", r"deploy:\s*scripts",
    r"master log: deploy", r"heartbeat", r"status:\s*completed\s*$",
    r"0 items across", r"watchdog (ok|tick)", r"pulse \d",
]
_NOISE = re.compile("|".join(NOISE_PATTERNS), re.I | re.M)

THEMES = {
    "wholesale": ["wholesale", "rex", "seller", "buyer", "memphis", "deal", "tn-tracker", "chris"],
    "infra":     ["infra", "deploy", "e5", "mother", "oracle", "cron", "watchdog", "sync"],
    "brain":     ["brain", "blinko", "memory", "rag", "agentmemory"],
    "trading":   ["xlm", "trade", "bot", "perps", "scalp"],
    "moltbook":  ["moltbook", "lucrex", "karma", "persona"],
    "legal":     ["legal", "compliance", "sb909", "eradicat", "dnc", "streubel"],
}


def load_notes() -> list[dict]:
    c = sqlite3.connect(BRAIN_DB)
    rows = c.execute("SELECT id, content, tags, COALESCE(created_at,'') FROM notes").fetchall()
    c.close()
    return [{"id": i, "content": ct or "", "tags": tg or "", "created_at": ca} for i, ct, tg, ca in rows]


def is_signal(note: dict) -> bool:
    return not _NOISE.search(note["content"])


def theme_of(note: dict) -> str:
    blob = (note["tags"] + " " + note["content"][:200]).lower()
    best, score = "other", 0
    for theme, kws in THEMES.items():
        s = sum(1 for k in kws if k in blob)
        if s > score:
            best, score = theme, s
    return best


def stats() -> None:
    notes = load_notes()
    sig = [n for n in notes if is_signal(n)]
    noise = len(notes) - len(sig)
    print(f"brain: {len(notes)} notes | signal {len(sig)} | noise {noise} ({noise*100//max(len(notes),1)}%)")
    by_theme = Counter(theme_of(n) for n in sig)
    print("high-signal notes by theme:")
    for t, n in by_theme.most_common():
        print(f"  {t:10} {n}")


def bundle(theme: str, limit: int = 40) -> list[dict]:
    notes = [n for n in load_notes() if is_signal(n) and theme_of(n) == theme]
    notes.sort(key=lambda n: n["created_at"])
    return notes[:limit]


def ingest_trail(title: str, knew: str, know: str, affects: str,
                 related_ids: list[str] | None = None, tags: str = "") -> bool:
    """Write a tier-2 TRAIL note, local-first. Threads raw notes into a thought-process."""
    related = related_ids or []
    content = (
        f"# TRAIL: {title}\n"
        f"#hive/trail {tags}\n\n"
        f"## What we KNEW\n{knew.strip()}\n\n"
        f"## What we KNOW now\n{know.strip()}\n\n"
        f"## How it AFFECTS the mission (Deal 1)\n{affects.strip()}\n\n"
        f"## Threads (constituent notes)\n" + (", ".join(related) if related else "(seed trail)") + "\n"
        f"\n_synthesized {datetime.now(timezone.utc).isoformat()} -- tier-2 cognition layer_"
    )
    body = json.dumps({"content": content, "type": 1}).encode()
    for url in BLINKO_CANDIDATES:
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=4) as r:
                if r.status < 300:
                    return True
        except Exception:
            continue
    return False


def wholesale_trail() -> bool:
    """The authored wholesale knowledge trail -- the proof that thoughts connect.
    Ties the April build -> the May-15 freeze -> the May-24 diagnosis+fixes -> the
    Deal-1 play into ONE narrative the brain can reason over."""
    # link a few real constituent note ids for the thread
    rel = []
    for n in bundle("wholesale", 12) + bundle("legal", 6):
        rel.append(n["id"])
    return ingest_trail(
        title="Wholesale TN -- from arsenal to first deal",
        tags="#hive/wholesale #hive/tn #hive/deal-1",
        knew="""April 2026: we BUILT the arsenal -- ~80 modules (scout/score/enrich/offer/
negotiate/close), a 4-persona front (Piper->Henry->Marvin->Vaughn), 3,163 seeded leads
(2,470 Memphis), Chris @ Mid South Homebuyers as the anchor buyer, a real TN legal stack
(SB 909 Schedule A renderer that already produced one compliant package). We thought the
machine was nearly done.""",
        know="""May 24 diagnosis: the machine was built but NEVER flowed end-to-end. The
scouts hunted FL/GA/OH/TX/MO (never Memphis) on a DEAD Perplexity key (HTTP 401), the
scoreboard read all-zeros (orphaned), the 3,163 leads had fake Faker contacts (0 reachable),
and the brain feed wrote to a dead e5-mother and silently dropped everything since May 15 --
which is also when the Streubel 2nd-strike triggered a GLOBAL outbound halt that froze the
whole pipeline over one DNC contact. FIXED this session: brain feed is now local-first
(620->1,665 notes), scoreboard derives from real leads, Streubel is blocked at the
per-recipient gate (scoped, not global), and a canonical TN deal tracker now holds 26 real
Memphis buy-box qualifiers off the Shelby assessor parse.""",
        affects="""The gap to Deal 1 is now small and concrete: (1) skip-trace the 26 tracked
Memphis qualifiers for EMAIL (digital-only -- no mail, ever); (2) confirm Chris's buy-box
(houses, ZIPs, max ARV); (3) clear the halt-lift 6-box checklist + operator greenlight
(Streubel stays dead regardless); (4) Piper emails the qualifiers, Henry negotiates, Marvin
closes, assign to Chris, collect the spread. The arsenal was never the problem -- aim, wiring,
and one frozen switch were. Those are now understood and mostly fixed.""",
        related_ids=rel[:18],
    )


if __name__ == "__main__":
    if "--stats" in sys.argv:
        stats()
    elif "--bundle" in sys.argv:
        i = sys.argv.index("--bundle")
        th = sys.argv[i + 1] if i + 1 < len(sys.argv) else "wholesale"
        for n in bundle(th):
            print(f"  [{n['created_at'][:10]}] {n['id']}  {n['content'][:60].strip()}")
    elif "--wholesale-trail" in sys.argv:
        ok = wholesale_trail()
        print("wholesale trail ingested" if ok else "FAILED to ingest (no brain endpoint)")
    else:
        stats()
