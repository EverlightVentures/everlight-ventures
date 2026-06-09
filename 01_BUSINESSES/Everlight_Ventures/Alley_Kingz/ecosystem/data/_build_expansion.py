#!/usr/bin/env python3
# ALLEY KINGZ -- CARD EXPANSION GENERATOR (48 -> 106)
# Transcribes the 58 Heavy/Street variants from ALLEY_KINGZ_CARD_EXPANSION.md
# (the design generator's authoritative output table) and merges them into:
#   - data/cards.json      (SoT: explicit combat fields, full per-card objects)
#   - game/canon.js        (window.CANON_*: variant objects + AIR/SPLASH lists + 10 decks)
#   - data/decks.json      (the 10 premade decks: 8 meta + 2 wildcard, 11 cards each)
# The 48 originals are left UNTOUCHED (stats verbatim). Variants inherit
# faction / domain / targets / splash / queen_target / abilityType / rig from
# their parent line; only the stat-tilt fields + cost + rarity + cooldown change.
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ECO  = os.path.dirname(HERE)
CARDS_JSON = os.path.join(HERE, 'cards.json')
DECKS_JSON = os.path.join(HERE, 'decks.json')
CANON_JS   = os.path.join(ECO, 'game', 'canon.js')

# ---- the 58 variants, transcribed verbatim from the master plan roster table ----
# (num, name, variant, parent, breed, role, rarity, cost, hp, dmg, atkspd, move, rng)
V = 'HEAVY'; S = 'STREET'
VARIANTS = [
 # Boneguard (14)
 ('0049','Cinderblock',V,'Balboa','Boxer','Striker','Legendary',7,1920,149,0.95,0.75,1),
 ('0050','Knuckles',   S,'Balboa','Boxer','Striker','Rare',     5,1080,219,1.18,0.94,1),
 ('0051','Tombstone',  V,'Iron Rottweiler','Rottweiler','Vanguard','Legendary',10,3648,132,0.63,0.48,1),
 ('0052','Razorgums',  S,'Iron Rottweiler','Rottweiler','Vanguard','Rare',      8,2052,194,0.78,0.61,1),
 ('0053','Anvil',      V,'Granite Saint','St. Bernard','Vanguard','Epic',  9,3392,115,0.63,0.48,1),
 ('0054','Hatchet',    S,'Granite Saint','St. Bernard','Vanguard','Common',7,1908,169,0.78,0.61,1),
 ('0055','Bonecrusher',V,'Grit Bulldog','Bulldog','Striker','Epic',  6,1664,128,0.95,0.75,1),
 ('0056','Switch',     S,'Grit Bulldog','Bulldog','Striker','Common',4, 936,188,1.18,0.94,1),
 ('0057','Warhorse',   V,'Alloy Akita','Akita','Lancer','Epic',  7,1408,153,0.85,0.75,2),
 ('0058','Lugnut',     S,'Alloy Akita','Akita','Lancer','Common',5, 792,225,1.06,0.94,2),
 ('0059','Ironhide',   V,'Warden Newfie','Newfoundland','Support','Epic',  8,1408,60,0.81,0.75,2),
 ('0060','Snaggle',    S,'Warden Newfie','Newfoundland','Support','Common',6, 792,88,1.01,0.94,2),
 ('0061','Slab',       V,'Rust Cane Corso','Cane Corso','Vanguard','Epic',  9,3392,115,0.63,0.48,1),
 ('0062','Brassknuck', S,'Rust Cane Corso','Cane Corso','Vanguard','Common',7,1908,169,0.78,0.61,1),
 # Zoomie (14)
 ('0063','Roadblock',  V,'Pixel Greyhound','Greyhound','Skirmisher','Epic',  4,896,81,1.17,1.23,1),
 ('0064','Nitro',      S,'Pixel Greyhound','Greyhound','Skirmisher','Common',2,504,119,1.46,1.54,1),
 ('0065','Bullbar',    V,'Circuit Shiba','Shiba Inu','Striker','Epic',  5,1536,115,0.95,0.97,1),
 ('0066','Switchblade',S,'Circuit Shiba','Shiba Inu','Striker','Common',3, 864,169,1.18,1.21,1),
 ('0067','Rollcage',   V,'Razor Vizsla','Vizsla','Lancer','Legendary',6,1472,153,0.85,0.75,2),
 ('0068','Ricochet',   S,'Razor Vizsla','Vizsla','Lancer','Rare',     4, 828,225,1.06,0.94,2),
 ('0069','Crashcage',  V,'Flash Saluki','Saluki','Skirmisher','Epic',  5,960,94,1.17,1.23,1),
 ('0070','Hotwire',    S,'Flash Saluki','Saluki','Skirmisher','Common',3,540,138,1.46,1.54,1),
 ('0071','Bumper',     V,'Bolt Corgi','Corgi','Spawner','Epic',  5,960,47,0.81,0.75,2),
 ('0072','Backfire',   S,'Bolt Corgi','Corgi','Spawner','Common',3,540,69,1.01,0.94,2),
 ('0073','Gridiron',   V,'Glitch Basenji','Basenji','Hacker','Epic',  4,896,60,0.90,0.75,3),
 ('0074','Skidmark',   S,'Glitch Basenji','Basenji','Hacker','Common',2,504,88,1.12,0.94,3),
 ('0075','Deadweight', V,'Aero Malinois','Malinois','Striker','Legendary',7,1920,149,0.95,0.97,1),
 ('0076','Flatline',   S,'Aero Malinois','Malinois','Striker','Rare',     5,1080,219,1.18,1.21,1),
 # Leashbreak (16)
 ('0077','Firewall',   V,'Synth Collie','Border Collie','Hacker','Legendary',6,1152,76,0.90,0.75,3),
 ('0078','Glitchfork', S,'Synth Collie','Border Collie','Hacker','Rare',     4, 648,112,1.12,0.94,3),
 ('0079','Deadbolt',   V,'Holo Husky','Husky','Support','Epic',  6,1216,51,0.81,0.75,3),
 ('0080','Static',     S,'Holo Husky','Husky','Support','Common',4, 684,75,1.01,0.94,3),
 ('0081','Bunkerlink', V,'Chill Samoyed','Samoyed','Support','Epic',  5,1152,47,0.81,0.75,3),
 ('0082','Shortcircuit',S,'Chill Samoyed','Samoyed','Support','Common',3, 648,69,1.01,0.94,3),
 ('0083','Faraday',    V,'Prism Poodle','Poodle','Controller','Epic',  5,1088,72,0.85,0.75,3),
 ('0084','Hexer',      S,'Prism Poodle','Poodle','Controller','Common',3, 612,106,1.06,0.94,3),
 ('0085','Sandbag',    V,'Noir Setter','Setter','Controller','Legendary',7,1408,94,0.85,0.75,3),
 ('0086','Whitenoise', S,'Noir Setter','Setter','Controller','Rare',     5, 792,138,1.06,0.94,3),
 ('0087','Blacksite',  V,'Signal Pointer','Pointer','Lancer','Epic',  5,1280,128,0.85,0.75,3),
 ('0088','Carrier',    S,'Signal Pointer','Pointer','Lancer','Common',3, 720,188,1.06,0.94,3),
 ('0089','Hardline',   V,'Ghost Spaniel','Spaniel','Skirmisher','Epic',  4,896,81,1.17,0.97,2),
 ('0090','Spike',      S,'Ghost Spaniel','Spaniel','Skirmisher','Common',2,504,119,1.46,1.21,2),
 ('0091','Bulwark',    V,'Pulse Border Collie','Border Collie','Support','Legendary',6,1344,55,0.81,0.75,3),
 ('0092','Brownout',   S,'Pulse Border Collie','Border Collie','Support','Rare',     4, 756,81,1.01,0.94,3),
 # K9 (14)
 ('0093','Bunker',     V,'Laser Beagle','Beagle','Structure','Epic',  5,1344,72,0.90,0.0,5),
 ('0094','Buckshot',   S,'Laser Beagle','Beagle','Structure','Common',3, 756,106,1.12,0.0,5),
 ('0095','Howitzer',   V,'Volt Corgi','Corgi','Spawner','Epic',  5,960,47,0.81,0.75,2),
 ('0096','Tripwire',   S,'Volt Corgi','Corgi','Spawner','Common',3,540,69,1.01,0.94,2),
 ('0097','Flakwall',   V,'Grid Schnauzer','Schnauzer','Structure','Epic',  6,1472,81,0.90,0.0,4),
 ('0098','Deadeye',    S,'Grid Schnauzer','Schnauzer','Structure','Common',4, 828,119,1.12,0.0,4),
 ('0099','Casemate',   V,'Circuit Retriever','Retriever','Support','Legendary',7,1408,60,0.81,0.75,3),
 ('0100','Shrapnel',   S,'Circuit Retriever','Retriever','Support','Rare',     5, 792,88,1.01,0.94,3),
 ('0101','Pillbox',    V,'Chrome Airedale','Airedale','Lancer','Epic',  6,1344,140,0.85,0.75,3),
 ('0102','Hairtrigger',S,'Chrome Airedale','Airedale','Lancer','Common',4, 756,206,1.06,0.94,3),
 ('0103','Stronghold', V,'Beacon Basset','Basset','Support','Epic',  5,1152,47,0.81,0.75,3),
 ('0104','Snubnose',   S,'Beacon Basset','Basset','Support','Common',3, 648,69,1.01,0.94,3),
 ('0105','Emplacement',V,'Nova Shepherd','German Shepherd','Structure','Legendary',8,1856,106,0.90,0.0,4),
 ('0106','Salvo',      S,'Nova Shepherd','German Shepherd','Structure','Rare',     6,1044,156,1.12,0.0,4),
]

FACTION_SHORT = {
 'Boneguard Crew':'Boneguard','Zoomie Syndicate':'Zoomie',
 'Leashbreak Tactix':'Leashbreak','K9 Circuitry':'K9',
}

def short_ability(parent):
    d = (parent.get('ability') or {}).get('description','').strip()
    if d and d[0].isupper():
        d = d[0].lower() + d[1:]
    return d.rstrip('.')

def build_variant(row, parent):
    num,name,variant,pname,breed,role,rarity,cost,hp,dmg,atkspd,move,rng = row
    pcd = int((parent.get('ability') or {}).get('cooldown',12) or 12)
    cd  = pcd + 2 if variant==V else max(6, pcd - 2)
    fac_short = FACTION_SHORT.get(parent['class'], parent['class'])
    ab = short_ability(parent)
    if variant==V:
        desc = ("%s -- the bunkered [HEAVY] build of %s's line (%s, %s). Up-armored: "
                "+28%% HP and heavier plating soak hits, trading bite and speed for a "
                "slower, near-unkillable frame. Same job: %s.") % (name,pname,role,fac_short,ab)
    else:
        desc = ("%s -- the stripped [STREET] build of %s's line (%s, %s). Glass-cannon: "
                "+25%% damage and quicker, panels torn off for the kill, but folds to one "
                "clean shot. Same job: %s.") % (name,pname,role,fac_short,ab)
    rig = dict(parent['rig'])
    rig['name'] = name + ' Rig'
    rig['flavor'] = ('bunkered ' if variant==V else 'stripped chop-shop ') + \
                    (parent['rig'].get('rigLanguage') or rig.get('rigClass','') + ' build')
    nft = dict(parent.get('nft', {}))
    card = collections.OrderedDict()
    card['class'] = parent['class']
    card['name'] = name
    card['breed'] = breed
    card['cost'] = cost
    card['role'] = role
    card['rarity'] = rarity
    card['tags'] = list(parent.get('tags', [])) + [variant.title()]
    card['hp'] = hp
    card['damage'] = dmg
    card['attack_speed'] = atkspd
    card['move_speed'] = move
    card['range'] = rng
    card['ability'] = collections.OrderedDict([
        ('name', (parent.get('ability') or {}).get('name','')),
        ('description', (parent.get('ability') or {}).get('description','')),
        ('cooldown', cd),
    ])
    card['queen_target'] = bool(parent.get('queen_target', False))
    card['abilityType'] = parent.get('abilityType')
    card['cardNumber'] = num
    card['factionId'] = parent['factionId']
    card['bodyArchetype'] = parent.get('bodyArchetype')
    card['isMythic'] = False
    card['rig'] = rig
    card['nft'] = nft
    # inherited explicit combat fields (verbatim from parent line)
    card['domain'] = parent.get('domain','ground')
    card['targets'] = parent.get('targets','ground')
    card['splash'] = bool(parent.get('splash', False))
    card['splashRadius'] = parent.get('splashRadius', 0)
    # variant-family metadata
    card['variant'] = variant
    card['family'] = pname
    card['parent'] = parent.get('cardNumber')
    card['desc'] = desc
    return card

# ============================ 1. cards.json ============================
data = json.load(open(CARDS_JSON))
cards = data['cards']
byname = {c['name']: c for c in cards}
assert len(cards) == 48, 'expected 48 originals, got %d' % len(cards)

new_objs = []
for row in VARIANTS:
    parent = byname[row[3]]
    new_objs.append(build_variant(row, parent))

cards.extend(new_objs)
assert len(cards) == 106, 'expected 106, got %d' % len(cards)

# rarity + faction tallies
rc = collections.Counter(c['rarity'] for c in cards)
fc = collections.Counter(c['class'] for c in cards)
data['meta']['cardCount'] = 106
data['meta']['rarity_counts'] = {k: rc[k] for k in ['Mythic','Legendary','Epic','Rare','Common']}
data['meta']['faction_counts'] = {k: fc[k] for k in ['Boneguard Crew','Zoomie Syndicate','Leashbreak Tactix','K9 Circuitry']}
data['meta']['variant_expansion'] = ('48 originals (0001-0048) untouched + 58 Heavy/Street variants '
    '(0049-0106) via deterministic stat-tilt. 106 character cards + 5 spells. See '
    'ALLEY_KINGZ_CARD_EXPANSION.md.')
json.dump(data, open(CARDS_JSON,'w'), indent=2)
open(CARDS_JSON,'a').write('\n')
print('cards.json: 48 ->', len(cards), '| rarity', dict(rc), '| faction', dict(fc))

# ============================ 2. canon.js ============================
canon = open(CANON_JS).read()

def js_card(c):
    # canon shape: NO explicit domain/targets (annotateCombat derives them at load).
    o = collections.OrderedDict()
    o['name']=c['name']; o['breed']=c['breed']; o['class']=c['class']
    o['factionId']=c['factionId']; o['rarity']=c['rarity']; o['cost']=c['cost']
    o['role']=c['role']; o['hp']=c['hp']; o['damage']=c['damage']
    o['attack_speed']=c['attack_speed']; o['move_speed']=c['move_speed']; o['range']=c['range']
    o['ability']=c['ability']; o['abilityType']=c['abilityType']
    o['queen_target']=c['queen_target']; o['cardNumber']=c['cardNumber']
    o['isMythic']=False
    o['rig']=collections.OrderedDict([
        ('name',c['rig'].get('name','')),('rigClass',c['rig'].get('rigClass','')),
        ('weaponMod',c['rig'].get('weaponMod','')),('sourceCar',c['rig'].get('sourceCar','')),
        ('flavor',c['rig'].get('flavor','')),
    ])
    o['variant']=c['variant']; o['family']=c['family']; o['desc']=c['desc']
    return json.dumps(o, indent=1)

objs_js = ',\n'.join(js_card(c) for c in new_objs)

# 2a. splice the 58 objects in before the CANON_CARDS closing "];"
m = re.search(r'(const CANON_CARDS = \[)([\s\S]*?)(\n\];)', canon)
assert m, 'CANON_CARDS block not found'
canon = canon[:m.start()] + m.group(1) + m.group(2) + ',\n' + objs_js + m.group(3) + canon[m.end():]

# 2b. CANON_META cardCount 48 -> 106
canon = canon.replace('"cardCount": 48,', '"cardCount": 106,', 1)

# 2c. AIR_UNITS += the 8 new air variants
air_anchor = "  'Neon Dachshund':true, 'Pixel Pug':true\n};"
assert air_anchor in canon, 'AIR_UNITS anchor not found'
air_add = ("  'Neon Dachshund':true, 'Pixel Pug':true,\n"
           "  // Heavy/Street air variants (inherit their parent line's air domain):\n"
           "  'Roadblock':true, 'Nitro':true, 'Crashcage':true, 'Hotwire':true,\n"
           "  'Bumper':true, 'Backfire':true, 'Hardline':true, 'Spike':true\n};")
canon = canon.replace(air_anchor, air_add, 1)

# 2d. SPLASH_OVERRIDE += Emplacement, Salvo (German Shepherd structure variants)
sp_anchor = "const SPLASH_OVERRIDE = { '$BCARDD':1.4, 'Crown Foxhound':1.3, 'Nova Shepherd':1.5 };"
assert sp_anchor in canon, 'SPLASH_OVERRIDE anchor not found'
canon = canon.replace(sp_anchor,
    "const SPLASH_OVERRIDE = { '$BCARDD':1.4, 'Crown Foxhound':1.3, 'Nova Shepherd':1.5, "
    "'Emplacement':1.5, 'Salvo':1.5 };", 1)

# ============================ 3. the 10 decks ============================
DECKS = [
 dict(name='CROWN MARCH', cls='Boneguard Crew', archetype='Beatdown', avgCost=6.2, wildcard=False,
   winCon='One unstoppable splash-tank push behind $BCARDD they cannot answer in time.',
   cards=['$BCARDD','Iron Rottweiler','Stonejaw','Warden Newfie','Balboa','Alloy Akita','Brick Bullmastiff','Grit Bulldog','Boneshatter Freeze','Copper Chow','Tank Pug']),
 dict(name='HYPER LOOP', cls='Zoomie Syndicate', archetype='Cycle', avgCost=3.3, wildcard=False,
   winCon='Death by a thousand cuts: cheapest deck, fastest hand, never stop chipping.',
   cards=['Neon Whippet','Drift Sheltie','Pixel Greyhound','Turbo Jack','Byte Beagle','Glitch Basenji','Jolt','Circuit Shiba','Flash Saluki','Bolt Corgi','Razor Vizsla']),
 dict(name='SIGNAL LOCKDOWN', cls='Leashbreak Tactix', archetype='Control', avgCost=4.5, wildcard=False,
   winCon='Out-resource and outlast: slow, silence and disable every push, win the chip war with Rosco.',
   cards=['Rosco','Noir Setter','Synth Collie','Pulse Border Collie','Chill Samoyed','Prism Poodle','Signal Pointer','Tar Pour','Echo Dalmatian','Static Sheba Inu','Vibe Shih Tzu']),
 dict(name='TURRET TRAP', cls='K9 Circuitry', archetype='Siege', avgCost=4.5, wildcard=False,
   winCon='Park static turrets and protect the engine while it chips from range.',
   cards=['Crown Foxhound','Nova Shepherd','Grid Schnauzer','Chrome Airedale','Laser Beagle','Beacon Basset','Volt Corgi','Rail Terrier','Snare Trap','Flux Pomeranian','Pixel Pug']),
 dict(name='SKY PACK', cls='Zoomie Syndicate', archetype='Air', avgCost=3.2, wildcard=False,
   winCon='Flood with AIR a ground-only army physically cannot hit; punish light anti-air.',
   cards=['Bolt Corgi','Flash Saluki','Neon Dachshund','Pixel Greyhound','Ghost Spaniel','Tank Pug','Jolt','Pixel Pug','Neon Whippet','Drift Sheltie','Aero Malinois']),
 dict(name='IRON WALL', cls='Boneguard Crew', archetype='Heavy-Tank', avgCost=6.6, wildcard=False,
   winCon='Build an immortal tank ball (double Vanguard + heal + shield) that does not die on the walk.',
   cards=['$BCARDD','Iron Rottweiler','Granite Saint','Rust Cane Corso','Stonejaw','Warden Newfie','Alloy Akita','Holo Husky','Pulse Border Collie','Boneshatter Freeze','Tank Pug']),
 dict(name='DRONE FLOOD', cls='K9 Circuitry', archetype='Swarm-Bait', avgCost=3.7, wildcard=False,
   winCon='Bait the one splash or spell, then overwhelm with constant spawned drones.',
   cards=['Circuit Retriever','Grid Schnauzer','Chrome Airedale','Bolt Corgi','Volt Corgi','Beacon Basset','Neon Dachshund','Rail Terrier','Snare Trap','Flux Pomeranian','Pixel Pug']),
 dict(name='HEX STORM', cls='Leashbreak Tactix', archetype='Spell-heavy', avgCost=3.3, wildcard=False,
   winCon='Run all 5 spells; bait support out, melt every push, finish with Strike + Jolt while Byte Beagle chips.',
   cards=['Boneshatter Freeze','Strike','Tar Pour','Jolt','Snare Trap','Signal Pointer','Byte Beagle','Echo Dalmatian','Glitch Basenji','Static Sheba Inu','Vibe Shih Tzu']),
 dict(name='DECAPITATION', cls='K9 Circuitry', archetype='Triple-Assassin Queen Dive', avgCost=5.0, wildcard=True,
   winCon='Ignore the lane war; run every Queen-target threat and assassinate the Queen before they build a defense.',
   cards=['Crown Foxhound','Jagged','Rosco','Circuit Shiba','Byte Beagle','Ghost Spaniel','Jolt','Snare Trap','Tank Pug','Static Sheba Inu','Drift Sheltie']),
 dict(name='FOUR CROWNS', cls='Boneguard Crew', archetype='Rainbow Midrange Toolbox', avgCost=4.6, wildcard=True,
   winCon='No single plan: one signature tool from all 4 factions; out-value every matchup by always having the answer.',
   cards=['Balboa','Aero Malinois','Noir Setter','Chrome Airedale','Razor Vizsla','Grit Bulldog','Prism Poodle','Beacon Basset','Strike','Turbo Jack','Glitch Basenji']),
]

# validate every deck card resolves to a known card or spell
known = set(c['name'] for c in cards)
canon_spell_names = re.findall(r"name: '([^']+)'", canon)  # spells use name: '...'
known |= set(canon_spell_names)
for d in DECKS:
    assert len(d['cards']) == 11, '%s has %d cards' % (d['name'], len(d['cards']))
    assert len(set(d['cards'])) == 11, '%s has a duplicate' % d['name']
    for nm in d['cards']:
        assert nm in known, 'deck %s references unknown card %r' % (d['name'], nm)

def js_deck(d):
    o = collections.OrderedDict()
    o['name']=d['name']; o['class']=d['cls']; o['archetype']=d['archetype']
    o['avgCost']=d['avgCost']; o['wildcard']=d['wildcard']; o['winCon']=d['winCon']
    o['cards']=d['cards']
    return json.dumps(o, indent=1)

decks_js = 'const CANON_DECKS = [\n' + ',\n'.join(js_deck(d) for d in DECKS) + '\n];'
canon = re.sub(r'const CANON_DECKS = \[[\s\S]*?\n\];', decks_js, canon, count=1)

open(CANON_JS,'w').write(canon)
print('canon.js: inserted %d variants, 10 decks, +8 AIR, +2 SPLASH override' % len(new_objs))

# ============================ 4. decks.json ============================
decks_out = {'decks': [collections.OrderedDict([
    ('name',d['name']),('class',d['cls']),('archetype',d['archetype']),
    ('avgCost',d['avgCost']),('wildcard',d['wildcard']),('winCon',d['winCon']),
    ('cards',d['cards'])]) for d in DECKS]}
json.dump(decks_out, open(DECKS_JSON,'w'), indent=2)
open(DECKS_JSON,'a').write('\n')
print('decks.json: wrote %d decks' % len(DECKS))
print('DONE.')
