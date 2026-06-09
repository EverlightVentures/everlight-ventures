#!/usr/bin/env python3
"""
Alley Kingz CANON-MERGE builder.
Reads the OnyxPOS canonical 48-dog roster, preserves every card EXACTLY,
annotates with meta + cardNumber + factionId + bodyArchetype + isMythic + rig + nft
per ROSTER_CANON.md (Section 4 dog->rig mapping, Section 9 schema).
No card is invented, dropped, or restatted. Merge + annotate only.
Run from anywhere; uses absolute paths.
"""
import json, collections

SRC = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/cards.json"
OUT = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/data/cards.json"

cards = json.load(open(SRC))
assert len(cards) == 48, f"expected 48, got {len(cards)}"

# --- Faction -> rig-class + machine key (ROSTER_CANON Section 1 + 4) ---
FACTION = {
    "Boneguard Crew":   {"id": "boneguard_crew",   "rigClass": "bruiser",     "bodyArchetype": "bruiser"},
    "Zoomie Syndicate": {"id": "zoomie_syndicate",  "rigClass": "sprinter",    "bodyArchetype": "sprinter"},
    "Leashbreak Tactix":{"id": "leashbreak_tactix", "rigClass": "tech_ops",    "bodyArchetype": "tech_ops"},
    "K9 Circuitry":     {"id": "k9_circuitry",      "rigClass": "turret_util", "bodyArchetype": "turret_util"},
}

# Weapon-mod per rig-class, from the 4 retired GAME_VISION car-spells
# (ROSTER_CANON Section 4: ram_plow | emp_array | slick_layer | incendiary).
WEAPON_MOD = {
    "bruiser":     "ram_plow",
    "sprinter":    "ram_plow",     # sprinters ram at speed; weapon overridden below for named/spell mappings
    "tech_ops":    "emp_array",
    "turret_util": "incendiary",
}

# GAME_VISION source-car per faction rig-class (Section 4 mapping table).
# We pick the representative source car per faction; Mythics get their named rig + the most fitting car.
SOURCE_CAR = {
    "bruiser":     "Muscle Car",   # ram bruiser is the faction signature (also Lowrider/Pickup/Monster Truck in the pool)
    "sprinter":    "GTR",          # nitro sport (also Drag Racer / Bike Duo in the pool)
    "tech_ops":    "Van",          # long-range sprayer (also Armored SUV / EMP in the pool)
    "turret_util": "Monster Truck",# area-crush turret platform (also Oil Slick / Molotov weapon mods)
}

# --- Named signature rigs for the 4 Mythics (ROSTER_CANON Section 2) ---
NAMED_RIG = {
    "$BCARDD":        {"name": "The Crown Rig", "weaponMod": "ram_plow",   "sourceCar": "Muscle Car",   "flavor": "matte-black armored war-truck, gold trim, ram plow. The coin/dealer dog."},
    "Jagged":         {"name": "Shadowblade",   "weaponMod": "ram_plow",   "sourceCar": "GTR",          "flavor": "low-slung nitro muscle car, blade fenders"},
    "Rosco":          {"name": "The Jammer",    "weaponMod": "emp_array",  "sourceCar": "Van",          "flavor": "antenna-bristled tech van, EMP dish"},
    "Crown Foxhound": {"name": "Railhound",     "weaponMod": "incendiary", "sourceCar": "Monster Truck","flavor": "turret-platform rig, rail-cannon mount"},
}

# ---------------------------------------------------------------------------
# COMBAT CATEGORIES (Combat Spec sections 1-3): domain / targets / splash.
# Derived + annotated here (and mirrored in game/canon.js annotateCombat()).
#   targets : MELEE (range 1) -> 'ground'; RANGED (range>=2) -> 'both' (anti-air).
#   domain  : 'ground' for all EXCEPT the hand-tagged AIR list below.
#   splash  : derived weaponType cannon|spread -> True; identity overrides too.
# ~9 FLYERS spread across all 4 factions; every faction keeps anti-air answers
# (every range>=2 card hits air), so no faction is helpless vs air.
# ---------------------------------------------------------------------------
AIR_UNITS = {
    "Tank Pug",                                            # Boneguard hover support-drone
    "Pixel Greyhound", "Neon Whippet", "Flash Saluki", "Bolt Corgi",  # Zoomie = the air faction
    "Ghost Spaniel", "Drift Sheltie",                      # Leashbreak/Zoomie phantom + hover support
    "Neon Dachshund", "Pixel Pug",                         # K9 drone flyers
}
# Identity splash overrides (a few legendaries crush swarms with a single weapon).
# Keyed on BOTH the source name ("$BCARDD") and the canon name ("$BCARDD") so the
# override applies regardless of which name the merge source carries.
SPLASH_OVERRIDE = {"$BCARDD": 1.4, "$BCARDD": 1.4, "Crown Foxhound": 1.3, "Nova Shepherd": 1.5}


def _weapon_type(role, rng, ability_type):
    # MUST mirror engine.deriveWeaponType so the splash flag matches the projectile.
    if role == "Spawner" or ability_type in ("spawn", "chain"):
        return "spread"
    if role == "Lancer" or ability_type in ("pierce", "line"):
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


def combat_fields(card):
    rng = card["range"]
    ranged = rng >= 2
    wt = _weapon_type(card["role"], rng, card.get("abilityType"))
    splashes = wt in ("cannon", "spread")
    radius = (2.2 if wt == "cannon" else 1.8) if splashes else 0
    if card["name"] in SPLASH_OVERRIDE:
        splashes = True
        radius = SPLASH_OVERRIDE[card["name"]]
    return {
        "domain": "air" if card["name"] in AIR_UNITS else "ground",
        "targets": "both" if ranged else "ground",
        "splash": bool(splashes),
        "splashRadius": radius,
    }


# Rig name fragments by faction so non-Mythic rigs read in faction rig-language (Section 1 column 5).
RIG_LANG = {
    "boneguard_crew":   "Armored bruiser rig -- ram plow, plate armor, slow and unstoppable",
    "zoomie_syndicate": "Sport speed rig -- nitro, drag body, glass-cannon velocity",
    "leashbreak_tactix":"Tech-ops rig -- jammer van, EMP array, signal-warfare",
    "k9_circuitry":     "Turret-utility rig -- mounted gun, drone bay, rail platform",
}

# Per-card rig display name derived from breed (one dog = one signature rig at base).
def rig_name_for(card):
    if card["name"] in NAMED_RIG:
        return NAMED_RIG[card["name"]]["name"]
    return f"{card['breed']} Rig"

# --- Deterministic card numbering: faction order, then descending rarity, then existing order. ---
FACTION_ORDER = ["Boneguard Crew", "Zoomie Syndicate", "Leashbreak Tactix", "K9 Circuitry"]
RARITY_RANK = {"Mythic": 0, "Legendary": 1, "Epic": 2, "Rare": 3, "Common": 4}
# $BCARDD MUST be #0001 (locked). We sort but pin $BCARDD first.
indexed = list(enumerate(cards))  # preserve original order as tiebreaker
def sort_key(item):
    i, c = item
    if c["name"] == "$BCARDD":
        return (-1, -1, -1, -1)  # absolute first
    return (FACTION_ORDER.index(c["class"]), RARITY_RANK[c["rarity"]], i, 0)
ordered = sorted(indexed, key=sort_key)
number_for = {}
for n, (i, c) in enumerate(ordered, start=1):
    number_for[id(c)] = f"{n:04d}"

# --- Annotate (NEVER mutate existing keys; only ADD) ---
out_cards = []
for c in cards:
    f = FACTION[c["class"]]
    is_mythic = c["rarity"] == "Mythic"
    if c["name"] in NAMED_RIG:
        nr = NAMED_RIG[c["name"]]
        rig = {
            "name": nr["name"],
            "rigClass": f["rigClass"],
            "weaponMod": nr["weaponMod"],
            "sourceCar": nr["sourceCar"],
            "rigLanguage": RIG_LANG[f["id"]],
            "flavor": nr["flavor"],
            "skinnable": True,
            "choppable": True,
        }
    else:
        rig = {
            "name": rig_name_for(c),
            "rigClass": f["rigClass"],
            "weaponMod": WEAPON_MOD[f["rigClass"]],
            "sourceCar": SOURCE_CAR[f["rigClass"]],
            "rigLanguage": RIG_LANG[f["id"]],
            "skinnable": True,
            "choppable": True,
        }
    # build the annotated card: existing fields verbatim first, then merge fields.
    # The source roster now carries an engine-legal `abilityType` (added by the
    # balance pass); dict(c) copies it through verbatim so canon stays in sync.
    nc = dict(c)  # exact copy of every original key/value
    nc["cardNumber"] = number_for[id(c)]
    nc["factionId"] = f["id"]
    nc["bodyArchetype"] = f["bodyArchetype"]
    nc["isMythic"] = is_mythic
    nc["rig"] = rig
    nc["nft"] = {
        "chain": "solana",
        "standard": "metaplex-core",
        "animation_url": "",
        "onchain_stats": ["hp", "damage", "ability"],
    }
    # Combat categories (Combat Spec sections 1-3) -- ADDED, never mutates originals.
    nc.update(combat_fields(c))
    out_cards.append(nc)

# --- Integrity assertion: every original card preserved exactly ---
orig_by_name = {c["name"]: c for c in cards}
for nc in out_cards:
    oc = orig_by_name[nc["name"]]
    for k, v in oc.items():
        assert nc[k] == v, f"MUTATED field {k} on {nc['name']}"
assert len({nc["cardNumber"] for nc in out_cards}) == 48, "card numbers not unique"
assert number_for[id(orig_by_name["$BCARDD"])] == "0001", "$BCARDD not #0001"

# ---------------------------------------------------------------------------
# SPELLS (Combat Spec section 4) -- new card type cast at a POINT/AREA.
# All 5 built per the locked operator decisions. Mirrored in game/canon.js
# CANON_SPELLS (the engine reads the runtime copy; this is the SoT record).
# ---------------------------------------------------------------------------
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

doc = {
    "meta": {
        "title": "Alley Kingz -- Canonical Card Roster",
        "chain": "solana",
        "ticker": "$BCARDD",
        "standard": "metaplex-core",
        "cardCount": len(out_cards),
        "factions": ["Boneguard Crew", "Zoomie Syndicate", "Leashbreak Tactix", "K9 Circuitry"],
        "mythics": ["$BCARDD", "Jagged", "Rosco", "Crown Foxhound"],
        "legendary": ["Stonejaw"],
        "source": "01_OnyxPOS/prototype_dec2025/game_design/cards.json (48 dogs, byte-identical Unity copy retired)",
        "canon_authority": "Alley_Kingz/ecosystem/ROSTER_CANON.md",
        "note": "Dogs are the IP. Vehicles (rigs) are the toys. Existing card stats preserved verbatim; rig + nft + ids added by the canon-merge, no restats.",
        "date": "2026-06-03",
        "combat": "domain/targets/splash added 2026-06-04 (Combat Spec); 5 spells added.",
    },
    "cards": out_cards,
    "spells": SPELLS,
}

with open(OUT, "w") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False)

print("WROTE", OUT)
print("count", len(out_cards))
print("factions", dict(collections.Counter(c["class"] for c in out_cards)))
print("rarity", dict(collections.Counter(c["rarity"] for c in out_cards)))
print("$BCARDD#", number_for[id(orig_by_name["$BCARDD"])])
print("numbers sample", [(c["cardNumber"], c["name"], c["rarity"]) for c in out_cards[:6]])
