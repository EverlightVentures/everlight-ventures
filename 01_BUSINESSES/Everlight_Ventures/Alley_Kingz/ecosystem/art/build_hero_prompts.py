#!/usr/bin/env python3
"""
Alley Kingz -- derive 106 full-body hero-pose prompts from the roster.

The prompts are NOT hand-written. Every card in cards.json already carries breed,
faction, rarity and rig class, so each prompt is generated from the data the game
already owns. That is what keeps 106 dogs looking like one family instead of 106
improvisations.

Two hard lessons are baked into the template and must not be edited out:
  1. Without explicit bipedal language FLUX returns a QUADRUPED wearing jeans.
     "standing upright on two legs" is load-bearing, not flavor.
  2. Without "entire body head to feet, both feet visible" you get a BUST, and a
     bust fed to Tripo produces a legless model. Proven twice. This wording is why
     the whole pipeline works.

Output: prompts.json -- consumed by the Colab notebook that batches the refs.

    python3 build_hero_prompts.py            # writes prompts.json
    python3 build_hero_prompts.py --show 3   # preview the first 3
"""
import argparse, json
from pathlib import Path

HERE = Path(__file__).parent
CARDS = HERE.parent / "unity_migration" / "cards.json"

# Locked canon. Every dog in the roster inherits this silhouette + framing.
#
# THE A-POSE CLAUSE IS LOAD-BEARING. DO NOT REMOVE IT.
# Auto-riggers (Mixamo, the free path this whole pipeline depends on) need limbs held
# AWAY from the torso. Arms at the sides fuse the mesh at the armpit, and a fused mesh
# cannot be rigged, cannot animate, cannot take a victory pose or an idle breathe loop.
# A ref generated without this produces a beautiful statue that can never move, and you
# only find out AFTER paying to mesh it. Our first $BCARDD mesh has exactly this defect:
# frozen mid-stride, arms down. Do not repeat it 106 times.
BASE = (
    "full body character reference sheet of a muscular anthropomorphic {breed} dog, "
    "dog head on a jacked humanoid bodybuilder body, standing upright on two legs like a "
    "Ninja Turtles character, entire body visible from head to feet, "
    "symmetrical relaxed A-pose, standing still and facing forward, "
    "both arms held out away from the body at roughly 45 degrees with clear space between "
    "each arm and the torso, hands open and away from the hips, "
    "legs straight and shoulder-width apart with clear space between the thighs, "
    "both feet flat and fully visible, "
    "{gear}, {faction}, stylized 3D game character render, even neutral lighting, "
    "clean plain solid white background, full figure, no cropping, no text, no watermark"
)

NEGATIVE = (
    "four legged, quadruped, dog on all fours, walking on four legs, bust, portrait, "
    "cropped legs, cut off at waist, headshot, torso only, "
    "arms crossed, arms at sides, arms touching torso, hands on hips, hands in pockets, "
    "walking, running, mid-stride, action pose, dynamic pose, twisted torso, "
    "legs crossed, legs together, foreshortening, "
    "blurry, text, watermark, multiple characters, busy background, harsh shadows"
)

# Gear escalates with rarity. Mythic carries the full $BCARDD canon loadout.
GEAR = {
    "Mythic": ("wearing a gold crown, flag aviator sunglasses, a cigar in his mouth, a thick gold "
               "cuban link chain with a large letter B medallion, an open denim vest, blue jeans "
               "with a gold belt buckle, and heavy boots"),
    "Legendary": ("wearing flag aviator sunglasses, a thick gold cuban link chain with a medallion, "
                  "an open denim vest, blue jeans with a gold belt buckle, and heavy boots"),
    "Epic": ("wearing aviator sunglasses, a gold chain, a street jacket, blue jeans, and boots"),
    "Rare": ("wearing a gold chain, a hoodie, blue jeans, and sneakers"),
    "Common": ("wearing a plain tank top, blue jeans, and sneakers"),
}

# Faction identity, mapped off the rig class the roster already assigns.
FACTION = {
    "Boneguard Crew":    "heavy armored bruiser build, broad shoulders, bone and gold accents",
    "Zoomie Syndicate":  "lean athletic sprinter build, streetwear, speed-runner styling",
    "Leashbreak Tactix": "tactical operator build, utility straps and tactical gear",
    "K9 Circuitry":      "cyber-tech build, subtle glowing circuitry and chrome tech accents",
}


def build(card):
    rarity = card.get("rarity", "Common")
    faction = card.get("class", "")
    return BASE.format(
        breed=card.get("breed", "pitbull"),
        gear=GEAR.get(rarity, GEAR["Common"]),
        faction=FACTION.get(faction, "street gangster styling"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", default=str(CARDS))
    ap.add_argument("--out", default=str(HERE / "prompts.json"))
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()

    cards = json.loads(Path(args.cards).read_text())["cards"]
    out = []
    for c in cards:
        out.append({
            "cardNumber": str(c["cardNumber"]).zfill(4),
            "name": c.get("name"),
            "breed": c.get("breed"),
            "faction": c.get("class"),
            "rarity": c.get("rarity"),
            "rigClass": (c.get("rig") or {}).get("rigClass"),
            "prompt": build(c),
            "negative": NEGATIVE,
        })

    payload = {"version": 1, "count": len(out), "negative": NEGATIVE, "prompts": out}
    Path(args.out).write_text(json.dumps(payload, indent=2))
    print(f"wrote {args.out}: {len(out)} prompts")

    by_rarity = {}
    for p in out:
        by_rarity[p["rarity"]] = by_rarity.get(p["rarity"], 0) + 1
    print("by rarity:", by_rarity)

    for p in out[: args.show]:
        print(f"\n--- {p['cardNumber']} {p['name']} ({p['rarity']}, {p['breed']}) ---")
        print(p["prompt"])


if __name__ == "__main__":
    main()
