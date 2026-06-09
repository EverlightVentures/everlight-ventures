#!/usr/bin/env python3
"""
Alley Kingz competitive balance + traits pass.
Reads the SoT cards.json, applies archetype-driven stats (scaled by rarity + cost),
adds an engine-legal abilityType per card, writes the SoT back in place,
then mirrors the SoT into game/canon.js (CANON_CARDS) preserving abilityType
and the exact generated structure + window.CANON_* exports. Also mirrors the
stat edits into the OnyxPOS source so _build_canon.py stays consistent.

NEVER touches name / cardNumber / faction / rarity / rig objects.
Tunes STATS (hp, damage, attack_speed, move_speed, range) + ability text/type.
"""
import json, collections, re, copy

SOT  = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/data/cards.json"
SRC  = "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/prototype_dec2025/game_design/cards.json"
CANON= "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game/canon.js"

EMD = chr(0x2014)  # em-dash, for the guard count only
END = chr(0x2013)  # en-dash
DD  = "-" + "-"     # plain double-hyphen used in generated comments

doc = json.load(open(SOT))
cards = doc["cards"]
assert len(cards) == 48, f"expected 48 got {len(cards)}"

before = {c["name"]: copy.deepcopy(c) for c in cards}

RARITY_MULT = {"Common":0.92, "Rare":1.0, "Epic":1.08, "Legendary":1.14, "Mythic":1.20}
MS = {"static":0.0, "slow":0.55, "med":0.85, "fast":1.1, "vfast":1.4}

ARCH = {
    "Vanguard":  dict(hp5=2300, hp_pc=120, dmg5=110, dmg_pc=8,  aspd=0.7, ms="slow",  rng=1, atype="dr"),
    "Striker":   dict(hp5=1300, hp_pc=90,  dmg5=150, dmg_pc=14, aspd=1.05,ms="med",   rng=1, atype="stun"),
    "Lancer":    dict(hp5=1050, hp_pc=70,  dmg5=165, dmg_pc=16, aspd=0.95,ms="med",   rng=2, atype="pierce"),
    "Skirmisher":dict(hp5=820,  hp_pc=55,  dmg5=120, dmg_pc=12, aspd=1.3, ms="vfast", rng=1, atype="dash"),
    "Assassin":  dict(hp5=1150, hp_pc=70,  dmg5=205, dmg_pc=18, aspd=1.1, ms="fast",  rng=1, atype="teleport"),
    "Blaster":   dict(hp5=720,  hp_pc=55,  dmg5=110, dmg_pc=11, aspd=1.1, ms="med",   rng=4, atype="pierce"),
    "Hacker":    dict(hp5=820,  hp_pc=55,  dmg5=85,  dmg_pc=8,  aspd=1.0, ms="med",   rng=3, atype="silence"),
    "Controller":dict(hp5=950,  hp_pc=80,  dmg5=95,  dmg_pc=9,  aspd=0.95,ms="med",   rng=3, atype="slow"),
    "Support":   dict(hp5=950,  hp_pc=70,  dmg5=60,  dmg_pc=5,  aspd=0.9, ms="med",   rng=3, atype="heal"),
    "Spawner":   dict(hp5=800,  hp_pc=60,  dmg5=60,  dmg_pc=5,  aspd=0.9, ms="med",   rng=2, atype="spawn"),
    "Structure": dict(hp5=1150, hp_pc=90,  dmg5=95,  dmg_pc=10, aspd=1.0, ms="static",rng=4, atype="ramp"),
}

ABILITY = {
    "$BCARDD":          ("shield",  "Crownbreaker",  "Shields self for 18% HP; can strike the Queen"),
    "Stonejaw":         ("dr",      "Armor Pulse",   "Aura cuts nearby ally damage taken by 15%"),
    "Balboa":           ("stun",    "Haymaker",      "First hit stuns the target for 1s"),
    "Iron Rottweiler":  ("crit",    "Overclock Rage","Below 40% HP its bite damage spikes"),
    "Granite Saint":    ("dr",      "Bodywall",      "Bodywall aura soaks nearby damage for the pack"),
    "Grit Bulldog":     ("buff",    "Brawler",       "Powers up its own bite the longer it brawls"),
    "Alloy Akita":      ("knockback","Shock Push",   "Knockback cone shoves a melee line back"),
    "Tank Pug":         ("shield",  "Shield Bark",   "Drops a small temporary shield on one ally"),
    "Copper Chow":      ("ramp",    "Bitechain",     "Each consecutive hit ramps its damage"),
    "Warden Newfie":    ("buff",    "Fortify",       "Raises max HP of allies in an aura"),
    "Rust Cane Corso":  ("knockback","Grav Pull",    "Pulses a shove that scatters the nearest foes"),
    "Brick Bullmastiff":("dr",      "Stonehide",     "Short window of heavy damage resistance"),
    "Jagged":           ("teleport","Shadow Fang",   "Teleports onto the Queen for a kill window"),
    "Pixel Greyhound":  ("dash",    "Dash Loop",     "Refreshes its dash on a kill"),
    "Circuit Shiba":    ("dash",    "Blink Bite",    "Blinks a short hop on its first attack"),
    "Neon Whippet":     ("evasion", "Slipstream",    "Ignores slows and gains brief evasion"),
    "Turbo Jack":       ("crit",    "Burst Bite",    "Crits on the first strike after deploy"),
    "Razor Vizsla":     ("pierce",  "Pierce Rush",   "Lunges a line that pierces every foe hit"),
    "Flash Saluki":     ("dash",    "Sidecut",       "Dashes lane to lane to flank the backline"),
    "Bolt Corgi":       ("spawn",   "Spark Pups",    "Spawns three fast mini zoomers"),
    "Glitch Basenji":   ("silence", "Signal Scramble","Silences a target ability briefly"),
    "Aero Malinois":    ("double_hit","Twin Strike",  "Strikes twice in one attack swing"),
    "Drift Sheltie":    ("buff",    "Tag Boost",     "Boosts the move speed of nearby allies"),
    "Byte Beagle":      ("pierce",  "Tracer Round",  "Long shots that pierce shields; can hit Queen"),
    "Rosco":            ("disable_tower","Leashbreak","Disables a tower fire; can strike the Queen"),
    "Synth Collie":     ("disable_tower","Hack Jam", "Jams a tower so it cannot fire"),
    "Holo Husky":       ("heal",    "Heal Beacon",   "Pulsing area heal for the pack"),
    "Chill Samoyed":    ("slow",    "Frost Bark",    "Wide frost cone slows everything caught"),
    "Prism Poodle":     ("shield",  "Shatter",       "Strips enemy shields, then wards an ally"),
    "Echo Dalmatian":   ("slow",    "Echo Howl",     "Rolling area slow down the lane"),
    "Static Sheba Inu": ("silence", "Ping",          "Quick silence on the first target"),
    "Vibe Shih Tzu":    ("heal",    "Soothe",        "Small steady heal to a wounded ally"),
    "Noir Setter":      ("blind",   "Blackout",      "Blinds ranged foes so their shots miss"),
    "Signal Pointer":   ("reveal",  "Tag Shot",      "Tags a target, revealing stealth and weakening it"),
    "Ghost Spaniel":    ("invuln",  "Phase",         "Phases out for a brief untargetable window"),
    "Pulse Border Collie":("shield","Barrier Ring",  "Drops an area shield over the front line"),
    "Crown Foxhound":   ("turret_break","Royal Hunt","Shreds structures; can strike the Queen"),
    "Laser Beagle":     ("ramp",    "Overheat",      "Static turret that ramps fire the longer it shoots"),
    "Neon Dachshund":   ("spawn",   "Tunnel Drones", "Tunnels up two attack drones"),
    "Volt Corgi":       ("spawn",   "Spark Pups",    "Spawns three spark drones"),
    "Grid Schnauzer":   ("slow",    "Grid Lock",     "Turret field that slows attackers in range"),
    "Flux Pomeranian":  ("buff",    "Battery",       "Boosts the fire rate of nearby turrets"),
    "Rail Terrier":     ("turret_break","Rail Shot", "Long rail shots deal bonus vs structures"),
    "Circuit Retriever":("spawn",   "Drone Swarm",   "Releases five swarm drones"),
    "Chrome Airedale":  ("chain",   "Arc Shot",      "Arc that chains to three targets"),
    "Beacon Basset":    ("reveal",  "Beacon",        "Reveals stealth and marks foes for the pack"),
    "Pixel Pug":        ("spawn",   "Mini Pup",      "Deploys a single guard drone"),
    "Nova Shepherd":    ("ramp",    "Overclock",     "Heavy static turret with a burst fire window"),
}

def clampr(v, lo, hi):
    return max(lo, min(hi, v))

TIER_OVERRIDE = {
    "Neon Whippet":"vfast", "Pixel Greyhound":"vfast", "Flash Saluki":"vfast",
    "Turbo Jack":"fast", "Circuit Shiba":"fast", "Drift Sheltie":"fast",
    "Aero Malinois":"fast", "Jagged":"fast",
    "Iron Rottweiler":"slow", "Granite Saint":"slow", "Rust Cane Corso":"slow",
    "Ghost Spaniel":"fast",
}
RANGE_OVERRIDE = {
    "Byte Beagle":4, "Rail Terrier":4, "Laser Beagle":5, "Grid Schnauzer":4,
    "Nova Shepherd":4, "Crown Foxhound":1, "Razor Vizsla":2, "Alloy Akita":2,
    "Ghost Spaniel":2, "Signal Pointer":3, "Synth Collie":3, "Noir Setter":3,
    "Chrome Airedale":3, "Warden Newfie":2, "Bolt Corgi":2,
}

for c in cards:
    role = c["role"]; a = ARCH[role]; cost = c["cost"]; mult = RARITY_MULT[c["rarity"]]
    hp  = (a["hp5"]  + (cost - 5) * a["hp_pc"])  * mult
    dmg = (a["dmg5"] + (cost - 5) * a["dmg_pc"]) * mult
    hp  = int(round(hp  / 50.0) * 50)
    dmg = int(round(dmg / 5.0)  * 5)
    hp  = clampr(hp, 450, 2850)
    dmg = clampr(dmg, 35, 230)
    c["hp"] = hp; c["damage"] = dmg; c["attack_speed"] = a["aspd"]
    tier = TIER_OVERRIDE.get(c["name"], a["ms"])
    c["move_speed"] = MS[tier]
    c["range"] = RANGE_OVERRIDE.get(c["name"], a["rng"])
    atype, aname, adesc = ABILITY[c["name"]]
    cd = c["ability"].get("cooldown", 12)
    c["ability"] = {"name": aname, "description": adesc, "cooldown": cd}
    c["abilityType"] = atype

# every abilityType MUST be a key the engine ABILITY_KIND map can fire (engine.js L149-160)
ENGINE_ABILITY_KEYS = {
    "shield","buff","aura","dr","stun","slow","heal","crit","teleport","dash","spawn",
    "disable_tower","silence","knockback","ramp","line","aoe","double_hit","queen_target",
    "turret_break","pierce","reveal","evasion","invuln","blind","root","chain","dot",
    "burst","lane_swap","pierce_",
}
bad_types = sorted({c["abilityType"] for c in cards} - ENGINE_ABILITY_KEYS)
assert not bad_types, f"abilityType not in engine vocabulary: {bad_types}"

roles = collections.defaultdict(list)
for c in cards: roles[c["role"]].append(c)
assert max(c["hp"] for c in roles["Vanguard"]) >= 2200
assert max(c["hp"] for c in roles["Skirmisher"]) <= 1200

doc["meta"]["balance_pass"] = "2026-06-03 competitive archetype tuning (stats + abilityType added)"
with open(SOT, "w") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False)
print("WROTE SoT", SOT)

src = json.load(open(SRC))
by_name = {c["name"]: c for c in cards}
for sc in src:
    nc = by_name[sc["name"]]
    sc["hp"]=nc["hp"]; sc["damage"]=nc["damage"]
    sc["attack_speed"]=nc["attack_speed"]; sc["move_speed"]=nc["move_speed"]; sc["range"]=nc["range"]
    sc["ability"]={"name":nc["ability"]["name"],"description":nc["ability"]["description"],"cooldown":nc["ability"]["cooldown"]}
    sc["abilityType"]=nc["abilityType"]
with open(SRC, "w") as fh:
    json.dump(src, fh, indent=2, ensure_ascii=False)
print("WROTE OnyxPOS source", SRC)

def canon_card(c):
    out = collections.OrderedDict()
    out["name"]=c["name"]; out["breed"]=c["breed"]; out["class"]=c["class"]
    out["factionId"]=c["factionId"]; out["rarity"]=c["rarity"]; out["cost"]=c["cost"]
    out["role"]=c["role"]; out["hp"]=c["hp"]; out["damage"]=c["damage"]
    out["attack_speed"]=c["attack_speed"]; out["move_speed"]=c["move_speed"]; out["range"]=c["range"]
    out["ability"]=collections.OrderedDict([("name",c["ability"]["name"]),("description",c["ability"]["description"]),("cooldown",c["ability"]["cooldown"])])
    out["abilityType"]=c["abilityType"]
    out["queen_target"]=c.get("queen_target", False)
    out["cardNumber"]=c["cardNumber"]; out["isMythic"]=c["isMythic"]
    rig = collections.OrderedDict()
    rig["name"]=c["rig"]["name"]; rig["rigClass"]=c["rig"]["rigClass"]
    rig["weaponMod"]=c["rig"]["weaponMod"]; rig["sourceCar"]=c["rig"]["sourceCar"]
    rig["flavor"]=c["rig"].get("flavor","")
    out["rig"]=rig
    return out

cur = open(CANON).read()
m = re.search(r"const CANON_DECKS = (\[.*?\]);\n", cur, re.S)
assert m, "could not find CANON_DECKS in canon.js"
decks_literal = m.group(1)

meta = collections.OrderedDict([
    ("title", doc["meta"]["title"]), ("ticker", doc["meta"]["ticker"]), ("chain", doc["meta"]["chain"]),
    ("cardCount", doc["meta"]["cardCount"]), ("factions", doc["meta"]["factions"]),
    ("mythics", doc["meta"]["mythics"]), ("legendary", doc["meta"]["legendary"]), ("canon_date", doc["meta"]["date"]),
])

cc = [canon_card(c) for c in cards]
header = (
"// ==========================================================================\n"
"// ALLEY KINGZ " + DD + " CANON DATA (inlined for offline play)\n"
"// SOURCE OF TRUTH: ecosystem/data/cards.json (48 dogs) + ability_params.json + decks.json\n"
"// This file is GENERATED. Do not hand-edit stats " + DD + " re-run the canon merge instead.\n"
"// Stats (hp/damage/attack_speed/move_speed/range/cost) are byte-faithful to the canon.\n"
"// ==========================================================================\n"
)
body  = "const CANON_META = " + json.dumps(meta, indent=2, ensure_ascii=False) + ";\n\n"
body += "const CANON_CARDS = [\n"
body += ",\n".join(" " + json.dumps(c, indent=1, ensure_ascii=False).replace("\n","\n ") for c in cc)
body += "\n];\n\n"
body += "const CANON_DECKS = " + decks_literal + ";\n\n"
body += "if (typeof module !== 'undefined' && module.exports) { module.exports = { CANON_META, CANON_CARDS, CANON_DECKS }; }\n"
body += "// Browser: top-level const does NOT attach to window, but engine.js reads window.CANON_*.\n"
body += "// Publish to the global object so the engine (and any script) can see the canon.\n"
body += "if (typeof window !== 'undefined') { window.CANON_META = CANON_META; window.CANON_CARDS = CANON_CARDS; window.CANON_DECKS = CANON_DECKS; }\n"

with open(CANON, "w") as fh:
    fh.write(header + body)
print("WROTE canon.js", CANON)

for f in (SOT, SRC, CANON):
    txt = open(f, encoding="utf-8").read()
    bad = txt.count(EMD) + txt.count(END)
    assert bad == 0, f"dash found in {f}: {bad}"
print("dash check: 0 across written files")

EX = ["$BCARDD","Neon Whippet","Razor Vizsla","Byte Beagle","Holo Husky"]
print("\n=== 5 EXAMPLE CARDS BEFORE -> AFTER ===")
for nm in EX:
    b = before[nm]; a = by_name[nm]
    print(f"{nm} ({a['role']}/{a['rarity']}/cost{a['cost']}):")
    print(f"   HP {b['hp']}->{a['hp']}  DMG {b['damage']}->{a['damage']}  AS {b['attack_speed']}->{a['attack_speed']}  MS {b['move_speed']}->{a['move_speed']}  RNG {b['range']}->{a['range']}  type={a['abilityType']}")

print("\n=== SPREAD BY ROLE (hp min-max | dmg min-max | range set | ms set) ===")
order=["Vanguard","Striker","Lancer","Skirmisher","Assassin","Blaster","Hacker","Controller","Support","Spawner","Structure"]
for r in order:
    cs=roles[r]
    hps=[c['hp'] for c in cs]; dms=[c['damage'] for c in cs]; rng=sorted({c['range'] for c in cs}); ms=sorted({c['move_speed'] for c in cs})
    print(f"{r:11} n={len(cs)}  HP {min(hps)}-{max(hps)}  DMG {min(dms)}-{max(dms)}  RNG {rng}  MS {ms}")
allhp=[c['hp'] for c in cards]; alldm=[c['damage'] for c in cards]; allrng=sorted({c['range'] for c in cards})
print(f"\nROSTER:  HP {min(allhp)}-{max(allhp)}  DMG {min(alldm)}-{max(alldm)}  RANGE {allrng}")
deltas=sorted(cards, key=lambda c: abs(c['hp']-before[c['name']]['hp'])+abs(c['damage']-before[c['name']]['damage'])*5, reverse=True)
print("\nBIGGEST CHANGERS:")
for c in deltas[:6]:
    b=before[c['name']]
    print(f"  {c['name']:20} HP {b['hp']}->{c['hp']}  DMG {b['damage']}->{c['damage']}")
