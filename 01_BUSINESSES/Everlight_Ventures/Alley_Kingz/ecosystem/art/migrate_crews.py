#!/usr/bin/env python3
"""
Alley Kingz -- CREW MIGRATION (operator 2026-07-17: "update the 101 cards to have the new logic and names")

THE PROBLEM this fixes:
Two taxonomies described the same 106 dogs and 101 of them disagreed.
  - GAME layer  (unity_migration/cards.json, canon.js): 4 FACTIONS in `class` -- the DECK axis.
  - ART  layer  (art/pack_bonds.json):                  8 CREWS in `originCrew` -- derived from district.
And the token "BONEGUARD" existed on BOTH axes meaning different things, which is what actually
guaranteed confusion.

THE RESOLUTION (kept deliberately non-destructive):
  1. Every card carries its CREW explicitly, in the game data, as `crew` + `crewId`. The crew names
     are now first-class on the card instead of living only in the art layer.
  2. `class` (the 4 factions) is LEFT ALONE, because it is the deck axis. CANON_DECKS are 11 cards
     keyed by class and engine.js matches on those exact strings. The crews CANNOT take that job:
     five of eight have fewer than 11 dogs (SCRAPJAW 8, ASHLINE 7, BONEGUARD 5, RUST HALO 4), so
     crew-gated decks would be unbuildable for most of the map. Faction = what you field.
     Crew = where you're from. Two axes, no collision.
  3. The colliding crew token BONEGUARD is renamed CROWN LOT (HOME_TURF / THE LOT is $BCARDD's home
     block and he is the crowned king of it). Nothing named "Boneguard" survives on the crew axis.

Writes .bak next to every file it touches. Idempotent: safe to re-run.
"""
import json, re, shutil, collections
from pathlib import Path

HERE = Path(__file__).parent
ECO = HERE.parent
PACK = HERE / "pack_bonds.json"
CARDS = ECO / "unity_migration" / "cards.json"
ROSTER = HERE / "card_roster.json"
BUILDER = HERE / "build_pack_bonds.py"

# the ONE rename that removes the cross-axis collision
CREW_RENAME = {"BONEGUARD": "CROWN LOT"}
# stable machine ids so code never has to match on a display string with a $ or a space
CREW_ID = {
    "MUTT$": "muttz", "NIGHTSHIFT": "nightshift", "SNAKE EYES": "snake_eyes",
    "K-CLUB": "k_club", "SCRAPJAW": "scrapjaw", "ASHLINE": "ashline",
    "CROWN LOT": "crown_lot", "RUST HALO": "rust_halo",
}


def backup(p):
    if p.exists():
        shutil.copy2(p, p.with_suffix(p.suffix + ".bak"))


def main():
    pack = json.loads(PACK.read_text())
    dogs = pack["dogs"]

    # --- 1. rename the colliding crew everywhere inside pack_bonds -------------
    renamed = 0
    for cid, d in dogs.items():
        oc = d.get("originCrew")
        if oc in CREW_RENAME:
            d["originCrew"] = CREW_RENAME[oc]
            renamed += 1
        tags = d.get("bondTags") or []
        d["bondTags"] = [
            ("CREW:" + CREW_RENAME[t.split(":", 1)[1]])
            if t.startswith("CREW:") and t.split(":", 1)[1] in CREW_RENAME else t
            for t in tags
        ]
    pack["note"] = ("crew = ORIGIN BLOCK (where the dog is from, 8 crews). faction/class = DECK AXIS "
                    "(4 factions, 11-card decks). Two separate axes on purpose -- five crews are too "
                    "small to field a deck. No token is shared between the axes.")
    backup(PACK)
    PACK.write_text(json.dumps(pack, indent=2))

    # --- 2. stamp crew onto every card in the GAME data ------------------------
    cj = json.loads(CARDS.read_text())
    stamped, missing = 0, []
    for c in cj["cards"]:
        cid = str(c.get("cardNumber")).zfill(4)
        d = dogs.get(cid)
        if not d:
            missing.append(cid); continue
        crew = d.get("originCrew")
        c["crew"] = crew
        c["crewId"] = CREW_ID.get(crew, re.sub(r"[^a-z0-9]+", "_", (crew or "").lower()).strip("_"))
        stamped += 1
    backup(CARDS)
    CARDS.write_text(json.dumps(cj, indent=2))

    # --- 3. mirror onto the art roster so the art layer agrees too -------------
    roster_n = 0
    if ROSTER.exists():
        rj = json.loads(ROSTER.read_text())
        for c in rj.get("cards", []):
            d = dogs.get(str(c.get("num")).zfill(4))
            if d:
                c["crew"] = d.get("originCrew")
                c["crewId"] = CREW_ID.get(c["crew"], "")
                roster_n += 1
        backup(ROSTER)
        ROSTER.write_text(json.dumps(rj, indent=2))

    # --- 4. keep the GENERATOR honest so a re-run cannot resurrect BONEGUARD ---
    if BUILDER.exists():
        src = BUILDER.read_text()
        new = src.replace('"HOME_TURF": "BONEGUARD"', '"HOME_TURF": "CROWN LOT"')
        if new != src:
            backup(BUILDER)
            BUILDER.write_text(new)

    # --- report ---------------------------------------------------------------
    dist = collections.Counter(d.get("originCrew") for d in dogs.values())
    fac = collections.Counter(c.get("class") for c in cj["cards"])
    print(f"crew renamed on {renamed} dogs (BONEGUARD -> CROWN LOT)")
    print(f"crew stamped onto {stamped} cards in cards.json; roster mirrored {roster_n}")
    if missing:
        print("!! no pack_bonds entry for:", missing)
    print("\nCREW (origin block):   ", dict(dist.most_common()))
    print("FACTION (deck axis):   ", dict(fac.most_common()))
    collide = set(dist) & set(fac)
    print("\nCROSS-AXIS TOKEN COLLISIONS:", collide or "NONE")
    agree = sum(1 for c in cj["cards"] if c.get("crew") and c.get("class"))
    print(f"cards now carrying BOTH crew and faction: {agree}/{len(cj['cards'])}")


if __name__ == "__main__":
    main()
