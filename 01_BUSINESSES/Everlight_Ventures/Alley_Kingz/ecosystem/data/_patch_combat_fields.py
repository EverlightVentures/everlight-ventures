#!/usr/bin/env python3
"""
One-shot SoT patch: add Combat-Spec fields (domain/targets/splash/splashRadius)
to every card in cards.json and append the 5 spell cards -- IN PLACE, preserving
every existing field and the locked "$BCARDD = #0001" name.

Why a patch instead of re-running _build_canon.py:
The OnyxPOS merge SOURCE drifted (the Mythic dog is named "$BCARDD" there, while
the canon/runtime artifacts use "$BCARDD"), so a full regenerate would rename the
king and break a locked decision. This patch updates the canonical cards.json
in place with the exact same derivation logic _build_canon.py now carries.
Derivation mirrors game/canon.js annotateCombat() + _build_canon.py combat_fields().
Run from anywhere; uses an absolute path.
"""
import json

PATH = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/data/cards.json"

AIR_UNITS = {
    "Tank Pug",
    "Pixel Greyhound", "Neon Whippet", "Flash Saluki", "Bolt Corgi",
    "Ghost Spaniel", "Drift Sheltie",
    "Neon Dachshund", "Pixel Pug",
}
SPLASH_OVERRIDE = {"$BCARDD": 1.4, "$BCARDD": 1.4, "Crown Foxhound": 1.3, "Nova Shepherd": 1.5}


def weapon_type(role, rng, at):
    if role == "Spawner" or at in ("spawn", "chain"):
        return "spread"
    if role == "Lancer" or at in ("pierce", "line"):
        return "lance"
    if role in ("Hacker", "Controller") or rng >= 4:
        return "beam"
    if role in ("Vanguard", "Blaster") and rng >= 2:
        return "cannon"
    if role in ("Striker", "Skirmisher") and rng >= 2:
        return "bullet"
    if rng >= 2:
        return "bullet"
    return "melee"


SPELLS = [
    {"name": "Boneshatter Freeze", "short": "FREEZE", "type": "spell",
     "factionId": "boneguard_crew", "class": "Boneguard Crew", "rarity": "Epic",
     "cost": 5, "cooldown": 14, "effect": "freeze", "radius": 3.0, "duration": 3.0,
     "damage": 0, "spellNumber": "S001", "glyph": "❄", "fx": "freeze",
     "description": "Enemies in the area STOP (no move, no attack) for ~3s. Towers freeze too."},
    {"name": "Tar Pour", "short": "TAR SLOW", "type": "spell",
     "factionId": "leashbreak_tactix", "class": "Leashbreak Tactix", "rarity": "Rare",
     "cost": 4, "cooldown": 12, "effect": "slow", "radius": 3.2, "duration": 4.0,
     "damage": 0, "slowPct": 0.35, "spellNumber": "S002", "glyph": "◉", "fx": "slow",
     "description": "Tar slick: -35% move + -35% attack speed to enemies in the area for ~4s."},
    {"name": "Snare Trap", "short": "SNARE", "type": "spell",
     "factionId": "k9_circuitry", "class": "K9 Circuitry", "rarity": "Rare",
     "cost": 3, "cooldown": 13, "effect": "trap", "radius": 1.8, "duration": 1.6,
     "damage": 90, "spellNumber": "S003", "glyph": "☢", "fx": "trap",
     "description": "Plants a hidden trap. Arms, then roots + small damage when an enemy crosses it. Zone control."},
    {"name": "Jolt", "short": "JOLT", "type": "spell",
     "factionId": "zoomie_syndicate", "class": "Zoomie Syndicate", "rarity": "Common",
     "cost": 3, "cooldown": 9, "effect": "zap", "radius": 2.4, "duration": 0.5,
     "damage": 130, "spellNumber": "S004", "glyph": "⚡", "fx": "zap",
     "description": "Instant AOE damage + 0.5s stun. Kills swarms, resets attacks."},
    {"name": "Strike", "short": "STRIKE", "type": "spell",
     "factionId": "neutral", "class": "Neutral", "rarity": "Epic",
     "cost": 4, "cooldown": 11, "effect": "strike", "radius": 2.6, "duration": 0,
     "damage": 320, "spellNumber": "S005", "glyph": "✹", "fx": "strike",
     "description": "The fireball: medium AOE burst damage at a point."},
]


def main():
    d = json.load(open(PATH))
    for c in d["cards"]:
        rng = c["range"]
        ranged = rng >= 2
        wt = weapon_type(c["role"], rng, c.get("abilityType"))
        splashes = wt in ("cannon", "spread")
        radius = (2.2 if wt == "cannon" else 1.8) if splashes else 0
        if c["name"] in SPLASH_OVERRIDE:
            splashes = True
            radius = SPLASH_OVERRIDE[c["name"]]
        c["domain"] = "air" if c["name"] in AIR_UNITS else "ground"
        c["targets"] = "both" if ranged else "ground"
        c["splash"] = bool(splashes)
        c["splashRadius"] = radius
    d["spells"] = SPELLS
    d["meta"]["combat"] = "domain/targets/splash added 2026-06-04 (Combat Spec); 5 spells added."
    with open(PATH, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    air = [c["name"] for c in d["cards"] if c["domain"] == "air"]
    splash = [c["name"] for c in d["cards"] if c["splash"]]
    print("OK patched", PATH)
    print("card#0001:", d["cards"][0]["name"], "| domain", d["cards"][0]["domain"],
          "| targets", d["cards"][0]["targets"], "| splash", d["cards"][0]["splash"])
    print("air units:", len(air), air)
    print("splash units:", len(splash), splash)
    print("spells:", [s["short"] for s in d["spells"]])


if __name__ == "__main__":
    main()
