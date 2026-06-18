"""watchdog v2 brakes+gas decisions + engine state-reading. Pure logic, no network.

Safety: this NEVER writes the real data/watchdog_state.json -- it points the engine at a
temp path so running on e5 can't wipe a live quarantine.

    python3 -m kalshi_agent.tests.test_watchdog_autopatch
"""
import json
import time
import tempfile
from pathlib import Path

from kalshi_agent.watchdog import decide_actions
import kalshi_agent.auto_edge as ae

CFG = {"watchdog_quarantine_hours": 24, "watchdog_lean_in_mult": 1.25}
NOW = 1_000_000


def main():
    fails = []

    # a COVERED bleeder -> BRAKES (quarantine, expiring after the cooldown)
    bleed = {"culprit": ("nba", {"wr": 0.30, "n": 6}), "hot": None}
    q, li, acts = decide_actions(bleed, CFG, lambda s: False, NOW)
    if "nba" not in q or not any("BRAKES" in x for x in acts):
        fails.append("covered bleeder should be quarantined: q=%s acts=%s" % (q, acts))
    if q.get("nba", {}).get("until") != NOW + 24 * 3600:
        fails.append("quarantine should expire after the cooldown window")

    # a BLIND bleeder -> NO quarantine (the no-coverage gate already skips it), just a note
    q2, _, acts2 = decide_actions(bleed, CFG, lambda s: True, NOW)
    if q2 or not any("BLIND" in x for x in acts2):
        fails.append("blind bleeder must NOT be quarantined: q=%s acts=%s" % (q2, acts2))

    # a COVERED hot segment -> GAS (bounded lean-in)
    hot = {"culprit": None, "hot": ("mlb", {"wr": 0.80, "n": 7})}
    _, li3, acts3 = decide_actions(hot, CFG, lambda s: False, NOW)
    if li3.get("mlb", {}).get("mult") != 1.25 or not any("GAS" in x for x in acts3):
        fails.append("covered hot segment should get lean-in: li=%s acts=%s" % (li3, acts3))

    # the ENGINE reads live entries and DROPS expired ones -- via a temp path (never the real file)
    tmp = Path(tempfile.mktemp(suffix="_wdstate.json"))
    real = ae.WD_STATE
    try:
        ae.WD_STATE = tmp
        tmp.write_text(json.dumps({"quarantine": {"wc": {"until": time.time() + 3600},
                                                  "old": {"until": time.time() - 10}}, "lean_in": {}}))
        st = ae.load_watchdog_state()
        if "wc" not in st["quarantine"] or "old" in st["quarantine"]:
            fails.append("engine should keep live quarantine + drop expired, got %s" % st)
    finally:
        ae.WD_STATE = real
        tmp.unlink(missing_ok=True)

    if ae.sport_of("KXWCGAME-26JUN15ESPCPV-ESP") != "wc" or ae.sport_of("KXUFCFIGHT-X-GAE") != "ufc":
        fails.append("sport_of mis-parsed a ticker prefix")

    # a COVERED sport on a loss STREAK -> quarantined (rotate away), even with no win-rate culprit
    streak = {"culprit": None, "hot": None, "cold_streak": ("mlb", 3)}
    q4, _, acts4 = decide_actions(streak, CFG, lambda s: False, NOW)
    if "mlb" not in q4 or not any("streak" in x.lower() for x in acts4):
        fails.append("cold-streak covered sport should be quarantined: q=%s acts=%s" % (q4, acts4))
    # a BLIND streak sport -> NOT quarantined (gate handles it)
    q5, _, acts5 = decide_actions(streak, CFG, lambda s: True, NOW)
    if q5:
        fails.append("blind streak sport must NOT be quarantined: q=%s" % (q5,))

    if fails:
        print("FAIL:")
        for f in fails:
            print("  -", f)
        raise SystemExit(1)
    print("OK: watchdog v2 brakes+gas decisions correct; engine reads + auto-expires state.")


if __name__ == "__main__":
    main()
