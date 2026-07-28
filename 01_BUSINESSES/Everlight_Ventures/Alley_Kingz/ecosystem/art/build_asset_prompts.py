#!/usr/bin/env python3
"""
Alley Kingz -- prompts for the OTHER 18k credits.

build_hero_prompts.py covers the 106 dogs (2,610 credits). This covers everything
else the Incorporation Matrix allocated: accessories, mods, chests, crowns,
buildings, Docks landmarks, bosses, handlers and props.

RIGS LIVE IN rig_bible.json, NOT HERE. See AK-RIGDEDUP 2026-07-18 below.

Same contract discipline as the dogs, adapted per asset class:
  - characters  -> A-pose, limbs clear of the torso (riggable)
  - buildings   -> three-quarter elevation, whole structure, flat base
  - props       -> single object, centered, no scene

Every prompt demands: ONE object, plain white background, even neutral lighting,
no baked shadows, no text. Those four are what make the mesh usable downstream:
lighting bakes fight the engine, scenes confuse the mesher, text becomes geometry.

    python3 build_asset_prompts.py             # writes asset_prompts.json
    python3 build_asset_prompts.py --summary   # counts + credit total
"""
import argparse, json
from pathlib import Path

HERE = Path(__file__).parent

# Shared clauses. Repeated verbatim so every asset lands in the same world.
CLEAN = ("single object centered in frame, plain solid white background, even neutral "
         "studio lighting, no cast shadows, no text, no watermark, no scene, no background objects")
STYLE = "stylized 3D game asset, gritty street gang aesthetic, 1980s street style, PBR game-ready"

# ----------------------------------------------------------------- RIGS (0)
# AK-RIGDEDUP 2026-07-18: the 20 rigs used to be authored here as RIG001..RIG020
# group rig_chassis, off one-line descriptions. rig_bible.json authors the SAME 20
# vehicles with full car-DNA look/weapon/armor/prompt payloads, and the generation
# manifest pulls from the bible. Two sources meant every rig was billed twice
# (20 x 55 = 1,100 credits) and meshed twice. The thin source is deleted; the
# bible wins. Do not re-add rigs here.

# ------------------------------------------------------------- CHESTS (5)
CHESTS = [
    ("wood",    "battered wooden crate, rope handles, rusted nails, splintered slats"),
    ("bronze",  "riveted bronze-banded strongbox, tarnished metal corners"),
    ("silver",  "polished silver-clad chest, engraved panels, heavy clasp"),
    ("gold",    "ornate gold chest, filigree scrollwork, jeweled lock plate"),
    ("diamond", "black vault chest crusted with diamonds, gold crown emblem on the lid, heavy hinges"),
]
CHEST_BASE = ("three-quarter view of a closed {desc}, lid shut, hinges and lock clearly visible "
              "on the front, sitting flat, {style}, {clean}")

# ------------------------------------------------------------- CROWNS (6)
CROWNS = [
    ("iron",     "crude iron crown, hammered spikes, rust and weld scars"),
    ("bronze",   "bronze crown, simple points, patina"),
    ("silver",   "silver crown, clean symmetrical points, faint engraving"),
    ("gold",     "gold crown, tall points, red gemstones set in the band"),
    ("platinum", "platinum crown, sharp modern points, cold white gems"),
    ("diamond",  "diamond-encrusted crown, brilliant faceted stones across every surface"),
]
CROWN_BASE = ("three-quarter view of a {desc}, complete circular crown, upright, "
              "hollow underneath, {style}, {clean}")

# ---------------------------------------------------------- BUILDINGS (12)
# 4 archetypes x 3 visual tiers. The 400 map tiles were only ever these.
BUILD_ARCH = [
    ("works",  "industrial workshop with a roller door, pipes and vents on the roof"),
    ("market", "street market stall building with an awning and shuttered counter"),
    ("gate",   "fortified checkpoint gate with a guard box and barrier arm"),
    ("core",   "block headquarters tower, flat roof, exterior stairs, barred windows"),
]
BUILD_TIER = [
    ("t1", "makeshift and scavenged, corrugated sheet, plywood patches, sagging"),
    ("t2", "reinforced and established, cinderblock, steel shutters, hung signage"),
    ("t3", "fortified and proud, clean concrete, gold trim, floodlights, crew banners"),
]
BUILD_BASE = ("three-quarter elevation view of a {arch}, {tier}, complete freestanding structure, "
              "flat ground-level base, whole building visible, {style}, {clean}")

# ------------------------------------------------------- LANDMARKS (30ish)
# The Docks holds 34 dogs and does not exist. The Undercity holds 4. Build them.
LANDMARKS = [
    ("docks", "towering gantry crane, rusted cables, hook block"),
    ("docks", "stacked shipping container tower, graffiti-tagged, doors ajar"),
    ("docks", "wooden pier section on barnacled pilings, missing planks"),
    ("docks", "dockside cargo winch, coiled steel rope, iron drum"),
    ("docks", "beached fishing trawler hull, peeling paint, exposed ribs"),
    ("docks", "harbor lighthouse stump, cracked lens housing"),
    ("docks", "chained bollard cluster with mooring rope"),
    ("docks", "corrugated dockside warehouse with a sliding freight door"),
    ("docks", "fuel depot tank, riveted, ladder up the side, stencil markings"),
    ("docks", "customs checkpoint booth, boom barrier, floodlight"),
    ("docks", "capsized dinghy, oars, tangled net"),
    ("docks", "stack of fish crates and ice bins"),
    ("docks", "seawall section with iron rungs and tide stains"),
    ("docks", "harbor foghorn tower, weathered speaker cone"),
    ("docks", "dry dock scaffold frame, catwalks"),
    ("docks", "sovereign's dock throne built from cargo pallets and chain"),
    ("undercity", "sewer outfall arch, iron grate, dripping brick"),
    ("undercity", "collapsed subway car, doors torn open, moss"),
    ("undercity", "underground steam junction, valve wheels, pipe cluster"),
    ("undercity", "cavern support pillar wrapped in cable and prayer rags"),
    ("undercity", "makeshift undercity shrine of welded scrap and candles"),
    ("undercity", "flooded tunnel walkway with a rusted handrail"),
    ("undercity", "abandoned maintenance shack, single bulb, tool board"),
    ("undercity", "ladder shaft up to a street manhole, rungs worn"),
    ("street", "chain link fence section with a torn gap"),
    ("street", "burning oil drum with a grate lid"),
    ("street", "dumpster, lid open, overflowing"),
    ("street", "stacked tire pile"),
    ("street", "concrete jersey barrier, tagged"),
    ("street", "bus shelter, cracked glass, faded ad panel"),
]
LM_BASE = "three-quarter view of a {desc}, {style}, {clean}"

# --------------------------------------------------------- BOSSES (12)
# Names verified from data/bosses_stories.js.
BOSSES = [
    ("THE LOT WARDEN", "Bullmastiff", "scarred territorial enforcer, riot plate armor, tax ledger chained to his belt"),
    ("METER, THE NEON RUNNER", "Greyhound", "wiry neon-lit courier, visor, light-trail rig, parking meter as a club"),
    ("THE IRON HANDLER", "Rottweiler", "hulking industrial enforcer, hydraulic gauntlet, chain leash coiled on his arm"),
    ("THE DOCK SOVEREIGN", "Newfoundland", "immense harbor king, oilskin coat, crane-hook scepter, barnacled crown"),
    ("TERMINUS, THE STATION KING", "Doberman", "rail-yard tyrant, conductor coat, signal lantern, spike maul"),
    ("THE SIGNAL KING", "German Shepherd", "antenna-crowned broadcast warlord, cabling harness, EMP array on his back"),
    ("GANGRENE, THE PLAGUE WARDEN", "Neapolitan Mastiff", "rotting plague warden, gas mask, dripping censer, hazard drapes"),
    ("MARKER, THE PIT BOSS", "Bull Terrier", "casino pit boss, sharp suit, loaded dice chain, brass knuckles"),
    ("THE COLD SAINT", "Siberian Husky", "frost-wreathed saint, ice-rimed vestments, halo of frozen chain"),
    ("THE REGENT", "Borzoi", "aristocratic pretender, tailored coat, thin blade, false crown"),
    ("THE MONGREL KING", "mixed-breed mongrel", "the crownless king, patchwork armor of every crew, scarred, immense"),
    ("THE COLLAR", "faceless authority", "towering faceless warden in a black coat, collar-and-chain iconography, no visible eyes"),
]
BOSS_BASE = ("full body character reference sheet of {desc}, an upright bipedal muscular "
             "anthropomorphic {breed} dog boss, dog head on a powerful humanoid body, "
             "standing upright on two legs, entire body visible from head to feet, "
             "symmetrical relaxed A-pose, both arms held out away from the body at roughly "
             "45 degrees with clear space between each arm and the torso, legs shoulder-width "
             "apart with clear space between the thighs, both feet flat and fully visible, "
             "menacing and imposing, boss-tier detail, {style}, {clean}")

# ------------------------------------------------------- ACCESSORIES (~200)
# 8 slots. drip.js already ships head/eyes/neck/muzzle/torso/hand; legs and back
# are the two the Fortnite layer is missing. Authored here so the taxonomy is
# fixed BEFORE art is commissioned against it.
ACC_SLOTS = {
    "head":   ["spiked bar cap", "backwards snapback", "welding helmet", "bandana durag", "gas mask hood",
               "iron circlet", "hard hat with lamp", "fur ushanka", "crown of nails", "hooded cowl",
               "biker helmet", "chef paper hat", "bucket hat", "visor cap", "police cap",
               "wolf skull cap", "beret", "sweatband", "top hat", "hood with fur trim",
               "cage mask", "flat cap", "bowler hat", "war bonnet of scrap", "trucker cap"],
    "eyes":   ["flag aviator sunglasses", "round wire spectacles", "cracked ski goggles", "neon visor",
               "eyepatch", "welding goggles", "mirrored shades", "monocle", "tactical night optics",
               "heart-shaped glasses", "blackout wraparounds", "steampunk lens rig", "safety glasses",
               "diamond-studded shades", "half-mask respirator over the nose", "scar over one eye",
               "LED strip visor", "opera mask", "swim goggles", "gold-rim shades",
               "bandage over one eye", "targeting monocle", "shutter shades", "bug-eye goggles", "clip-on flip shades"],
    "neck":   ["gold cuban link chain with a B medallion", "spiked leather collar", "prison-issue tag chain",
               "bandana knotted at the throat", "chunky rope chain", "choke chain",
               "dog tags on a ball chain", "pearl strand", "bike chain wrapped twice",
               "neon LED collar", "scarf", "bolo tie", "padlock on a chain", "bone necklace",
               "diamond tennis chain", "electrical cable coil", "shark tooth cord", "crown pendant chain",
               "barbed wire loop", "medal ribbon", "silk cravat", "chain with a dice charm",
               "leash clipped to the collar", "iron torc", "hazard tag lanyard"],
    "muzzle": ["lit cigar", "toothpick", "cigarette", "gold grill fangs", "wire muzzle cage",
               "bandana pulled up", "respirator", "bone in the teeth", "matchstick", "pipe",
               "rose in the teeth", "leather muzzle strap", "dust mask", "cigar with an ash trail",
               "chain bit", "welding mask flipped up", "lollipop stick", "bubble gum", "whistle",
               "scarred lip", "gold tooth", "muzzle brace", "cigarillo", "vape stick", "toothpick and a smirk"],
    "torso":  ["open denim vest", "leather biker jacket", "bare muscular chest with tattoos", "hoodie",
               "puffer coat", "tank top", "letterman jacket", "flak vest", "bomber jacket",
               "trench coat", "mechanic coveralls unzipped to the waist", "hazmat top",
               "chain mail over a shirt", "varsity cardigan", "tracksuit top", "poncho",
               "plate carrier", "fur coat", "suit jacket over a bare chest", "welding apron",
               "sleeveless flannel", "racing jacket", "prison jumpsuit top", "duster coat", "crop puffer"],
    "hand":   ["brass knuckles", "fingerless gloves", "boxing wraps", "gold rings on every finger",
               "baseball bat wrapped in wire", "crowbar", "chain wrapped around the fist",
               "welding gloves", "sledgehammer", "pipe wrench", "switchblade", "boombox",
               "briefcase of cash", "spray can", "revolver", "sawn-off shotgun", "katana",
               "nail bat", "crutch", "cleaver", "megaphone", "handheld radio", "bolt cutters",
               "hockey stick", "trash can lid shield"],
    "legs":   ["blue jeans with a gold belt buckle", "cargo pants", "track pants with side stripes",
               "leather chaps", "shorts", "camo fatigues", "suit trousers", "ripped jeans",
               "mechanic coverall legs", "kilt", "padded moto pants", "sweatpants",
               "chain-draped jeans", "hazard-striped work pants", "basketball shorts",
               "riding leathers", "denim cutoffs", "tactical pants with knee pads", "pinstripe slacks",
               "patched jeans", "snow pants", "biker jeans with armor plates", "linen pants",
               "prison jumpsuit legs", "parachute pants"],
    "back":   ["duffel bag", "sledge slung across the back", "neon sign panel strapped on",
               "jetpack of welded scrap", "backpack", "guitar case", "tattered cape",
               "oxygen tanks", "banner pole with crew colors", "quiver of rebar",
               "boombox harness", "toolbox rig", "antenna array", "rolled bedroll",
               "chain spool", "surfboard", "fire extinguisher pack", "satellite dish",
               "wings of scrap metal", "cooler box", "crate on a shoulder strap", "gas canister pair",
               "rolled carpet", "ladder", "wrapped bindle on a stick"],
}
ACC_BASE = "three-quarter view of a single {desc}, isolated wearable game prop, {style}, {clean}"

# ------------------------------------------------------------ HANDLERS (6)
HANDLERS = [
    ("Marcus", "the strategist commander, long coat, clipboard, calm"),
    ("Vex", "the demolition commander, blast goggles, det cord bandolier"),
    ("Sable", "the infiltration commander, hood, silenced pistol, gloves"),
    ("Rook", "the fortification commander, riot shield, hard hat"),
    ("Circuit", "the tech commander, cable harness, tablet rig, headset"),
    ("Vega", "the logistics commander, aviators, cargo manifest, radio"),
]
HANDLER_BASE = ("full body character reference sheet of {desc}, an upright bipedal anthropomorphic "
                "dog commander, standing upright on two legs, entire body visible head to feet, "
                "symmetrical relaxed A-pose, arms held out away from the body at roughly 45 degrees "
                "with clear space between each arm and the torso, legs shoulder-width apart, "
                "both feet flat and visible, {style}, {clean}")

NEGATIVE_CHAR = ("four legged, quadruped, dog on all fours, bust, portrait, cropped legs, "
                 "cut off at waist, headshot, arms at sides, arms touching torso, arms crossed, "
                 "walking, mid-stride, action pose, legs together, blurry, text, watermark, "
                 "multiple characters, busy background, harsh shadows")
NEGATIVE_OBJ = ("multiple objects, scene, environment, background clutter, people, hands holding it, "
                "cropped, cut off, blurry, text, watermark, harsh shadows, dramatic lighting")


def build():
    out = []

    def add(aid, group, name, prompt, negative, credits, tier):
        out.append({"assetId": aid, "group": group, "name": name, "prompt": prompt,
                    "negative": negative, "credits": credits, "tier": tier})

    # AK-RIGDEDUP 2026-07-18: no rig rows. rig_bible.json is the single rig source.
    for name, desc in CHESTS:
        add(f"CHEST_{name}", "chest", name,
            CHEST_BASE.format(desc=desc, style=STYLE, clean=CLEAN), NEGATIVE_OBJ, 20, "standard")

    for name, desc in CROWNS:
        add(f"CROWN_{name}", "crown", name,
            CROWN_BASE.format(desc=desc, style=STYLE, clean=CLEAN), NEGATIVE_OBJ, 20, "standard")

    for arch, adesc in BUILD_ARCH:
        for tkey, tdesc in BUILD_TIER:
            add(f"BLD_{arch}_{tkey}", "building", f"{arch} {tkey}",
                BUILD_BASE.format(arch=adesc, tier=tdesc, style=STYLE, clean=CLEAN),
                NEGATIVE_OBJ, 20, "standard")

    for i, (zone, desc) in enumerate(LANDMARKS, 1):
        add(f"LM{i:03d}_{zone}", "landmark", desc[:34],
            LM_BASE.format(desc=desc, style=STYLE, clean=CLEAN), NEGATIVE_OBJ, 20, "standard")

    for i, (name, breed, desc) in enumerate(BOSSES, 1):
        add(f"BOSS{i:02d}", "boss", name,
            BOSS_BASE.format(desc=desc, breed=breed, style=STYLE, clean=CLEAN),
            NEGATIVE_CHAR, 55, "hero")

    for i, (name, desc) in enumerate(HANDLERS, 1):
        add(f"HAND{i:02d}", "handler", name,
            HANDLER_BASE.format(desc=desc, style=STYLE, clean=CLEAN), NEGATIVE_CHAR, 55, "hero")

    for slot, items in ACC_SLOTS.items():
        for i, desc in enumerate(items, 1):
            add(f"ACC_{slot}_{i:02d}", "accessory", f"{slot}: {desc}",
                ACC_BASE.format(desc=desc, style=STYLE, clean=CLEAN), NEGATIVE_OBJ, 20, "standard")

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "asset_prompts.json"))
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    rows = build()
    payload = {"version": 1, "count": len(rows), "assets": rows}
    Path(args.out).write_text(json.dumps(payload, indent=2))

    groups, credits = {}, 0
    for r in rows:
        g = groups.setdefault(r["group"], {"n": 0, "cr": 0})
        g["n"] += 1; g["cr"] += r["credits"]; credits += r["credits"]

    print(f"wrote {args.out}: {len(rows)} assets")
    print(f"{'group':<14}{'count':>7}{'credits':>10}")
    for g in sorted(groups, key=lambda k: -groups[k]["cr"]):
        print(f"{g:<14}{groups[g]['n']:>7}{groups[g]['cr']:>10}")
    print(f"{'TOTAL':<14}{len(rows):>7}{credits:>10}")
    print(f"\nplus 106 dogs at 2,610  ->  grand total {credits + 2610} of 25,000")


if __name__ == "__main__":
    main()
