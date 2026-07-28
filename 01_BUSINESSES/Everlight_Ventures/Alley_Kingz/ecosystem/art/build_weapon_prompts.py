#!/usr/bin/env python3
"""
Alley Kingz -- WEAPON + ATTACHMENT prompts (the War Rig Master Doc, Part 7).

The master doc introduced a full weapon system that was never prompted: 7 categories,
held (FPS/combat view) + mounted (RPG top-down view), plus a 5-slot attachment gunsmith.
This builds all of it in the SAME discipline as the cars: resemble real archetypes, never
copy a brand. No real gun-maker or model name (no AK, no MP5, no Barrett) reaches a mesh.
Names are original and street-gang flavored so they fit the AK world, not a mil-sim.

Two view meshes per weapon:
  held    8k faces, FPS detail, three-quarter, for the combat view
  mounted 1k faces, readable from above, for the RPG turret view
Rarity (Common..Ultra) is a MATERIAL/skin tier, applied as a free recolor, not a new mesh.

Output: weapon_prompts.json, consumed by tripo_batch.py the same way the others are.
Read-only. Writes one data file.
"""
import json, collections
from pathlib import Path

HERE = Path(__file__).parent

OBJ = ("game-ready 3D weapon model, single object centered, three-quarter view, "
       "even neutral studio lighting, clean plain solid white background, no hands, "
       "no character, no text, no brand markings, no manufacturer logo, no baked shadows")
MOUNTED_TAIL = ("mounted on a vehicle roof turret pintle, simplified low-poly, readable from "
                "above, game-ready 3D model, plain white background, no logos, no text")
NEG = ("hands, arms, character, dog, person, real brand logo, manufacturer name, text, "
       "watermark, multiple objects, busy background, baked shadow, blurry")

# Street-gang originals. Each RESEMBLES a real archetype (so it reads right) but carries no
# brand name. archetype = the silhouette reference for the artist, never shown to players.
WEAPONS = {
  "smg": [
    ("Stray",       "compact blowback SMG, stubby barrel, side-folding wire stock"),
    ("Yapper",      "micro machine pistol, no stock, extended mag"),
    ("Chatterbox",  "boxy stamped-steel SMG, top-folding stock, vented barrel shroud"),
    ("Ratatat",     "vintage drum-fed SMG, wood foregrip, round drum magazine"),
    ("Whisper",     "integrally suppressed SMG, fat barrel shroud, minimalist frame"),
    ("Buzzsaw",     "high-rate polymer SMG, aggressive muzzle, curved translucent mag"),
  ],
  "ar": [
    ("Workhorse",   "classic gas-piston assault rifle, curved magazine, carry handle"),
    ("Bulldog",     "compact bullpup rifle, magazine behind the trigger, integrated optic rail"),
    ("Streetsweeper","short-barrel carbine, collapsing stock, quad rail handguard"),
    ("Enforcer",    "heavy battle rifle, long barrel, wood-and-steel furniture"),
    ("Mongrel",     "welded-together rifle, mismatched parts, taped magazine"),
    ("Sidewinder",  "sleek modern rifle, monolithic upper, angled foregrip"),
  ],
  "lmg": [
    ("Grudge",      "belt-fed light machine gun, folding bipod, box ammo can"),
    ("Landlord",    "heavy squad machine gun, thick barrel, heat shield, carry handle"),
    ("Overkill",    "drum-fed light MG, top-mounted drum, ventilated shroud"),
    ("Payback",     "chain-fed rotary barrel gun, multiple barrels, ammo feed chute"),
  ],
  "shotgun": [
    ("Doorbell",    "pump-action shotgun, tube magazine, wooden pump, bead sight"),
    ("Last Call",   "double-barrel break-action shotgun, exposed hammers, cut stock"),
    ("Meat Grinder","full-auto box-fed combat shotgun, drum magazine, heat shroud"),
    ("Knock Knock", "sawn-off double shotgun, no stock, taped grip"),
  ],
  "sniper": [
    ("Long Goodbye","bolt-action sniper rifle, long fluted barrel, adjustable stock"),
    ("Silence",     "semi-auto marksman rifle, suppressor, tall scope rail"),
    ("Skyline",     "anti-materiel rifle, huge muzzle brake, folding bipod, side magazine"),
    ("Widowmaker",  "scoped lever-action rifle, worn wood, brass accents"),
  ],
  "launcher": [
    ("Eviction",    "shoulder rocket launcher, single tube, front grip, optical sight"),
    ("Grand Finale","multi-tube rotary rocket launcher, cluster of barrels"),
    ("Bad News",    "revolver grenade launcher, six-round drum, folding stock"),
  ],
  "special": [
    ("Hellhound",   "backpack flamethrower, fuel tanks, wand nozzle, pilot flame"),
    ("Livewire",    "tesla-coil arc gun, copper coils, glowing capacitor, cables"),
    ("Junkyard",    "scrap-cannon that fires nails and bolts, welded hopper, exposed spring"),
    ("Sledge",      "oversized gravity war-hammer, hydraulic head, glowing core"),
    ("Slick",       "oil-slick cannon, pressurized tank, wide spray nozzle"),
  ],
}

# 40-piece gunsmith: 5 slots. From the master doc Part 7, verbatim types.
ATTACH = {
  "barrel":     [("short","short ported barrel, compact"), ("long","long fluted barrel, extended"),
                 ("heavy","heavy bull barrel, thick profile"), ("light","skeletonized lightweight barrel")],
  "muzzle":     [("suppressor","cylindrical suppressor, visible baffles, matte black"),
                 ("brake","ported muzzle brake, compensator"), ("flash","birdcage flash hider"),
                 ("breacher","toothed breacher standoff device")],
  "underbarrel":[("grip_vertical","vertical polymer foregrip"), ("grip_angled","angled polymer foregrip"),
                 ("bipod","folding spring bipod"), ("gl","single-shot grenade launcher"),
                 ("chainsaw","motorized chainsaw bayonet, chain blade, fuel tank"),
                 ("laser","compact laser emitter with pressure switch")],
  "magazine":   [("extended","extended curved magazine"), ("drum","circular drum magazine"),
                 ("fast","tapered quick-draw magazine"), ("dual","jungle-taped dual magazine")],
  "optic":      [("reddot","tubular red dot sight, glowing lens"), ("acog","magnified ACOG-style scope"),
                 ("sniper","long variable sniper scope with sunshade"), ("holo","wide holographic sight"),
                 ("iron","folding iron sight leaf"), ("thermal","boxy thermal optic")],
}

RARITY_SKIN = {
  "Common":"scuffed matte steel", "Uncommon":"green-tinted parkerized finish",
  "Rare":"blued steel with blue accents", "Epic":"purple anodized with etched panels",
  "Legendary":"gold-plated with engraving", "Mythic":"blood-red evolving finish with glow",
  "Ultra":"shifting prismatic chrome, one of one",
}


def main():
    out = []

    def add(wid, group, name, prompt, credits, view, extra=None):
        row = {"assetId": wid, "group": group, "name": name, "prompt": prompt,
               "negative": NEG, "credits": credits, "view": view}
        if extra:
            row.update(extra)
        out.append(row)

    for cat, guns in WEAPONS.items():
        for nm, arch in guns:
            base = nm.lower().replace(" ", "_")
            # held (combat/FPS) 8k
            add(f"wpn_{cat}_{base}_held", "weapon_held", nm,
                f"a street-gang {arch}, worn and battle-used, aggressive gritty aesthetic, "
                f"detailed receiver and moving parts, {OBJ}, 8k faces",
                20, "combat", {"category": cat, "archetype": arch})
            # mounted (RPG top-down) 1k
            add(f"wpn_{cat}_{base}_mounted", "weapon_mounted", nm,
                f"a {arch}, {MOUNTED_TAIL}, 1k faces",
                20, "rpg", {"category": cat, "archetype": arch})

    for slot, parts in ATTACH.items():
        for key, desc in parts:
            add(f"attach_{slot}_{key}", "attachment", f"{slot}:{key}",
                f"a {desc} weapon attachment, matte finish, quick-detach mount, {OBJ}",
                20, "both", {"slot": slot})

    payload = {
        "version": 1,
        "rarity_skins": RARITY_SKIN,
        "note": "rarity is a free material recolor, not a new mesh. held+mounted are two meshes per weapon.",
        "count": len(out),
        "credits_total": sum(r["credits"] for r in out),
        "assets": out,
    }
    p = HERE / "weapon_prompts.json"
    p.write_text(json.dumps(payload, indent=2))

    g = collections.Counter(r["group"] for r in out)
    print(f"wrote {p}\n")
    for k in ("weapon_held", "weapon_mounted", "attachment"):
        print(f"  {k:16} {g[k]:4}")
    n_guns = sum(len(v) for v in WEAPONS.values())
    print(f"\n  base weapons: {n_guns} (each held + mounted)")
    print(f"  attachments : {sum(len(v) for v in ATTACH.values())}")
    print(f"  total meshes: {payload['count']}  credits: {payload['credits_total']}")
    print(f"  rarity skins per weapon: {len(RARITY_SKIN)} (free recolors)")
    print(f"\n  sample held : {out[0]['name']} -> {out[0]['prompt'][:80]}")


if __name__ == "__main__":
    main()
