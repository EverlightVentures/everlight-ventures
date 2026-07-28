#!/usr/bin/env python3
"""
Alley Kingz -- OPTION A: rebalance the roster so every crew can field a REAL deck.

THE ROOT CAUSE THIS FIXES
-------------------------
The roster has one axis wearing three costumes. Card number decided rig class,
rig class decided faction, and the district tags were assigned in the same
card-number blocks. Result: faction == class, and district ~= class. Four of the
eight districts are single-class today (Downtown is 10 sprinters, The Yards is 8
bruisers). That is the real reason the roster reads generic, and no amount of 3D
fixes it.

WHAT DECK-LEGAL ACTUALLY MEANS
------------------------------
The deck is 11 cards, assigned to buildings by trait + faction. So a mono-crew
deck needs BOTH:
  1. 11+ dogs in the crew                    (headcount)
  2. a spread of all four combat roles       (or the deck cannot function)
Headcount alone is a trap: 13 dogs that are all tech-ops is still an unplayable
crew. This planner treats class mix as a HARD constraint and lore fit as the
thing to optimize inside it.

METHOD
------
Each rig class holds ~26 dogs. Spread each class across the 8 districts, 3 to 4
per district, choosing for each dog the district its own book already points at
(vocabulary match). Dogs whose stories are truly welded to a place keep it: the
anchor score is scored first and the most-anchored dogs are placed first, so they
claim their rightful turf before anyone else is moved.

Read-only. Proposes, never writes.
"""
import re, json, collections
from pathlib import Path

HERE = Path(__file__).parent
STORIES = HERE.parent / "game" / "data" / "cards_stories.js"
CARDS = HERE.parent / "unity_migration" / "cards.json"

# 8 districts, 8 crews. Option A gives every crew turf.
CREW = {
    "HOME_TURF":     "BONEGUARD",
    "THE_YARDS":     "SCRAPJAW",
    "NEON_HEIGHTS":  "NIGHTSHIFT",
    "DOWNTOWN":      "K-CLUB",
    "FACTORY_ROW":   "ASHLINE",
    "THE_STRIP":     "SNAKE EYES",
    "THE_DOCKS":     "MUTT$",
    "THE_UNDERCITY": "RUST HALO",
}

# The vocabulary that means "this dog's story is actually about this place."
ANCHOR = {
    "HOME_TURF":     ["the lot", "home turf", "lot warden", "junkyard"],
    "THE_YARDS":     ["yard", "scrap", "junk", "salvage", "rust", "chop"],
    "NEON_HEIGHTS":  ["neon", "heights", "uptown", "holo", "chrome", "glass"],
    "DOWNTOWN":      ["downtown", "tower", "office", "suit", "vault", "mint"],
    "FACTORY_ROW":   ["factory", "foundry", "smokestack", "furnace", "kiln", "soot", "ash"],
    "THE_STRIP":     ["strip", "casino", "table", "dice", "chip", "pit boss", "marker"],
    "THE_DOCKS":     ["dock", "pier", "wharf", "harbor", "gull", "crane", "container",
                      "shipping", "sovereign", "tide"],
    "THE_UNDERCITY": ["undercity", "tunnel", "sewer", "beneath", "under the", "pipe"],
}

DISTRICTS = list(CREW.keys())
MIN_PER_CLASS = 3   # every crew fields at least 3 of every role


def parse_books(src):
    marks = [(m.start(), m.group(1)) for m in re.finditer(r'"(\d{4})"\s*:\s*\{', src)]
    out = []
    for i, (pos, cid) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(src)
        chunk = src[pos:end]
        d = re.search(r'district:\s*"([A-Z_]+)"', chunk)
        n = re.search(r'codename:\s*"([^"]+)"', chunk)
        out.append({"id": cid, "name": n.group(1) if n else cid,
                    "district": d.group(1) if d else None, "text": chunk.lower()})
    return out


def fit(book, dist):
    return sum(book["text"].count(w) for w in ANCHOR[dist])


def main():
    books = {b["id"]: b for b in parse_books(STORIES.read_text())}
    cards = {str(c["cardNumber"]).zfill(4): c for c in json.loads(CARDS.read_text())["cards"]}
    for cid, b in books.items():
        b["cls"] = (cards[cid].get("rig") or {}).get("rigClass")
        b["rarity"] = cards[cid].get("rarity")
        b["anchor"] = fit(b, b["district"]) if b["district"] else 0

    by_class = collections.defaultdict(list)
    for b in books.values():
        by_class[b["cls"]].append(b)

    print("=== THE ROOT CAUSE, MEASURED ===")
    before = collections.defaultdict(collections.Counter)
    for b in books.values():
        before[b["district"]][b["cls"]] += 1
    for d in sorted(before, key=lambda x: -sum(before[x].values())):
        c = dict(before[d])
        n = sum(c.values())
        print(f"  {d:15} {n:3} dogs, {len(c)} of 4 roles  {c}")
    broken = [d for d in before if len(before[d]) < 3]
    print(f"\n  districts that CANNOT field a working deck today: {len(broken)} -> {broken}\n")

    # capacity: spread each class 3-4 per district
    cap = {}
    for cls, pool in by_class.items():
        base = len(pool) // len(DISTRICTS)
        extra = len(pool) % len(DISTRICTS)
        cap[cls] = {d: base + (1 if i < extra else 0) for i, d in enumerate(DISTRICTS)}

    # place the most-anchored dogs first so they keep the turf their book claims
    assign = {}
    for cls, pool in by_class.items():
        for b in sorted(pool, key=lambda x: -x["anchor"]):
            scored = sorted(
                ((fit(b, d), d) for d in DISTRICTS if cap[cls][d] > 0),
                reverse=True
            )
            if not scored:
                continue
            # a dog that still fits its original home and has room keeps it
            home = next((s for s in scored if s[1] == b["district"]), None)
            pick = home[1] if (home and b["anchor"] > 0 and home[0] >= scored[0][0]) else scored[0][1]
            cap[cls][pick] -= 1
            assign[b["id"]] = pick

    after = collections.defaultdict(collections.Counter)
    for cid, d in assign.items():
        after[d][books[cid]["cls"]] += 1

    print("=== AFTER: class mix as a hard constraint ===")
    ok = True
    for d in DISTRICTS:
        c = dict(after[d]); n = sum(c.values())
        roles = len(c)
        legal = n >= 11 and roles == 4 and min(c.values()) >= MIN_PER_CLASS
        ok = ok and legal
        print(f"  {d:15} {n:3} dogs  {CREW[d]:11} roles={roles}/4  {c}"
              f"  {'OK' if legal else 'SHORT'}")
    print(f"\n  every crew fields 11+ dogs across all 4 roles: {ok}")

    moves = [{"id": cid, "name": books[cid]["name"], "cls": books[cid]["cls"],
              "rarity": books[cid]["rarity"], "from": books[cid]["district"], "to": d,
              "anchor": books[cid]["anchor"], "fit": fit(books[cid], d),
              "crew": CREW[d],
              "lore_pass": "NONE" if books[cid]["district"] == d
                           else ("LIGHT" if books[cid]["anchor"] <= 2 else "REWRITE")}
             for cid, d in assign.items() if books[cid]["district"] != d]
    stay = len(books) - len(moves)

    print(f"\n=== COST ===")
    print(f"  dogs that keep their district: {stay}")
    print(f"  dogs that move:                {len(moves)}")
    lp = collections.Counter(m["lore_pass"] for m in moves)
    print(f"  of those, light touch: {lp.get('LIGHT',0)}   real rewrite: {lp.get('REWRITE',0)}")

    print("\n=== SAMPLE MOVES (heaviest lore cost first) ===")
    for m in sorted(moves, key=lambda x: -x["anchor"])[:12]:
        print(f"  {m['id']} {m['name'][:17]:17} [{m['cls']:11}] "
              f"{m['from']:14} -> {m['to']:14} anchor={m['anchor']:2} {m['lore_pass']}")

    out = HERE / "district_rebalance_plan.json"
    out.write_text(json.dumps({
        "version": 2, "option": "A", "crews": CREW,
        "rule": "11+ dogs and all 4 roles per crew, min 3 per role",
        "moves": moves,
        "after": {d: dict(after[d]) for d in DISTRICTS},
    }, indent=2))
    print(f"\nplan written: {out}")


if __name__ == "__main__":
    main()
