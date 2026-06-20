#!/usr/bin/env python3
"""
ALLEY KINGZ -- HUB ASSET FACTORY (walkable-world building facades + district grounds)
=====================================================================================
Bulk-generates the BIG-WORLD art via Leonardo (API, cheap, fast) -- the volume assets
that should NOT cost premium Seedance tokens. Reuses the proven leo_gen() from the maps
factory. Idempotent (skips existing). Premium hero art (Arena facade, avatar, transition
splash) is done in Seedance separately.

RUN:  LEONARDO_API_KEY=xxx python3 generate_hub_assets.py
OUT:  game/assets/hub/<slug>.png   (12 building facades + 3 district ground plates)
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from generate_world_maps import leo_gen   # proven Leonardo gen (832x1216, alchemy, retry/poll)

GAME = os.path.normpath(os.path.join(HERE, "..", "game"))
OUT  = os.path.join(GAME, "assets", "hub"); os.makedirs(OUT, exist_ok=True)

STYLE = (" . Gritty cyberpunk dog-gang street aesthetic, neon signage, rain-slick, gritty TV-MA, "
         "hyper-detailed game art, front-facing storefront facade, centered, vanta-black #050507 surroundings, "
         "$BCARDD Alley Kingz house style.")
BUILDINGS = [
  ("garage",  "a cyberpunk auto GARAGE / body shop facade, car rigs and tools inside, electric-blue neon"),
  ("drop",    "a glowing neon corner STORE bodega facade named 'THE DROP', hot-pink neon, goods in the windows"),
  ("clan",    "a dog-gang CLUBHOUSE / crew-yard facade, graffiti walls, purple neon crew banner"),
  ("pass",    "a sleek premium membership PASS lounge kiosk facade, teal neon, velvet rope"),
  ("fixer",   "a shady back-alley FIXER bounty-office facade, amber neon, wanted posters tacked up"),
  ("wardrobe","a streetwear DRIP boutique shopfront, pink and chrome, mannequins in the window"),
  ("archive", "an old neon ARCHIVE / records-vault facade, violet glow, shelves of files"),
  ("street",  "a gritty STREET-corner hangout facade, lime-green neon, concrete stoop"),
  ("kennel",  "a cyberpunk KENNEL / handler den facade, stacked dog crates, lime neon"),
  ("trophy",  "a gilded TROPHY HALL facade, gold cups and spotlights, regal gold trim"),
  ("arcade",  "a retro neon ARCADE storefront, cyan and magenta cabinets glowing through the glass"),
  # NOTE: 'arena' facade is Seedance (premium hero) -- intentionally NOT generated here.
]
DISTRICTS = [
  ("uptown_ground", "a seamless top-down wet asphalt city street ground texture, cool blue neon reflections, cyberpunk uptown, no buildings"),
  ("midtown_ground","a seamless top-down cracked concrete street ground texture, warm gold neon glints, cyberpunk midtown, no buildings"),
  ("docks_ground",  "a seamless top-down wet wooden dock planks and puddles ground texture, sickly green glow, cyberpunk harbor docks, no buildings"),
]

def run(items, key, tag):
    made = skip = fail = 0
    for slug, desc in items:
        out = os.path.join(OUT, slug + ".png")
        if os.path.exists(out):
            print(" skip", slug); skip += 1; continue
        prompt = desc + STYLE
        try:
            d = leo_gen(prompt, key)                    # build bytes first (maps-factory anti-truncation rule)
            if d and len(d) > 20000:
                open(out, "wb").write(d); print(" %s %s (%d KB)" % (tag, slug, len(d)//1024)); made += 1
            else:
                print(" FAIL %s %s: empty/small" % (tag, slug)); fail += 1
        except Exception as e:
            print(" FAIL %s %s: %s" % (tag, slug, str(e)[:70])); fail += 1
        time.sleep(2.0)
    return made, skip, fail

def main():
    key = os.environ.get("LEONARDO_API_KEY")
    if not key:
        print("no LEONARDO_API_KEY"); return 1
    m1, s1, f1 = run(BUILDINGS, key, "FACADE")
    m2, s2, f2 = run(DISTRICTS, key, "GROUND")
    print("\nDONE made=%d skip=%d fail=%d  -> game/assets/hub/  (arena facade + avatar + transition = Seedance)"
          % (m1+m2, s1+s2, f1+f2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
