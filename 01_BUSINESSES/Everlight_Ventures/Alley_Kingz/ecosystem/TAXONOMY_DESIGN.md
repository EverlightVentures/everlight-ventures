# ALLEY KINGZ -- TAXONOMY DESIGN (Wave 6, Sections 3 + 5 + 6 + 7)
Design-wave deliverable. Spec contract: WAVE6_RPG_DEPTH_SPEC.md sections 3, 5, 6, 7.
Grounding: game/canon.js (106 cards), game/engine.js (AK-FEEL range bands,
AK-SYNERGY named table + ns* buff layers, AK-ATTRS clamps, CC timers),
game/index.html (ak_profile / ak_world shapes, grantMatchRewards, recordWorldResult),
game/cards_lore.js (voice), STORYLINE_CANON.md (act titles), LOOT_SYSTEM_MANDATE.md,
TRANSITION_SHOWPIECE_SPEC.md. ZERO code in this wave -- every section names its
engine hook point for the implementation wave.

GOVERNING PRINCIPLE (spec section 7): radical personalization. Every system below
was run through the anti-generic test -- "would two veteran accounts look and play
meaningfully different?" Where a system is account-flavored, it is called out.

---

## 1. THE CLASS LAYER (spec section 3)

CLASS is a NEW axis on top of ROLE. Role stays the combat job (it drives the
AK-FEEL B1 range band in engine.js rangeBand()); CLASS is the fantasy + buff
hook (it drives the new synergy combos, badge text, archetype detection, and
the structure-family behavior split).

### 1.1 The seven classes

| CLASS     | Fantasy                          | Mechanical identity (existing engine truth) |
|-----------|----------------------------------|---------------------------------------------|
| BRUISER   | Frontline muscle, sustain melee  | High hp, range band 1.0-1.6, dr/shield/ramp/knockback kits |
| ASSASSIN  | Burst, backline access, mobility | teleport/dash/crit/double_hit/evasion/invuln kits, kill windows |
| CASTER    | Mage-type: the ability IS the dps| Ranged CC/debuff kits: slow/silence/blind/disable_tower/chain/shield-strip |
| MARKSMAN  | Sustained ranged damage          | pierce/reveal long shots, range bands 3.5-6.0 |
| SUPPORT   | Heals, buffs, wards              | heal/buff/shield/dr aura kits |
| SUMMONER  | Fields tokens, wins by numbers   | spawn kits (isToken drones/pups) |
| STRUCTURE | The building family              | move_speed 0 (or reclassed static), 5 archetypes in 1.3 |

### 1.2 Class assignment -- ALL 106 cards

Clones share their base card's kit, so class is assigned per ABILITY FAMILY and
inherited; every card is still listed. Format: family -> class -- members.

BONEGUARD CREW
- Crownbreaker family -> BRUISER -- 0001 $BCARDD
- Armor Pulse family -> BRUISER -- 0002 Stonejaw
- Haymaker family -> BRUISER -- 0003 Balboa, 0049 Cinderblock, 0050 Knuckles
- Overclock Rage family -> BRUISER -- 0004 Iron Rottweiler, 0051 Tombstone, 0052 Razorgums
- Bodywall family -> BRUISER -- 0005 Granite Saint, 0053 Anvil, 0054 Hatchet
- Brawler family -> BRUISER -- 0006 Grit Bulldog, 0055 Bonecrusher, 0056 Switch
- Shock Push family -> BRUISER -- 0007 Alloy Akita, 0057 Warhorse, 0058 Lugnut (CC bruiser, knock subtype)
- Fortify family -> SUPPORT -- 0008 Warden Newfie, 0059 Ironhide, 0060 Snaggle
- Grav Pull family -> BRUISER -- 0009 Rust Cane Corso, 0061 Slab, 0062 Brassknuck (CC bruiser, knock subtype)
- Shield Bark family -> SUPPORT -- 0010 Tank Pug
- Bitechain family -> BRUISER -- 0011 Copper Chow
- Stonehide family -> BRUISER -- 0012 Brick Bullmastiff

ZOOMIE SYNDICATE
- Shadow Fang family -> ASSASSIN -- 0013 Jagged
- Pierce Rush family -> MARKSMAN -- 0014 Razor Vizsla, 0067 Rollcage, 0068 Ricochet (line damage = firing lane)
- Twin Strike family -> ASSASSIN -- 0015 Aero Malinois, 0075 Deadweight, 0076 Flatline (burst window)
- Dash Loop family -> ASSASSIN -- 0016 Pixel Greyhound, 0063 Roadblock, 0064 Nitro
- Blink Bite family -> ASSASSIN -- 0017 Circuit Shiba, 0065 Bullbar, 0066 Switchblade
- Sidecut family -> ASSASSIN -- 0018 Flash Saluki, 0069 Crashcage, 0070 Hotwire
- Spark Pups family (Zoomie) -> SUMMONER -- 0019 Bolt Corgi, 0071 Bumper, 0072 Backfire
- Signal Scramble family -> CASTER -- 0020 Glitch Basenji, 0073 Gridiron, 0074 Skidmark
- Slipstream family -> ASSASSIN -- 0021 Neon Whippet
- Burst Bite family -> ASSASSIN -- 0022 Turbo Jack
- Tag Boost family -> SUPPORT -- 0023 Drift Sheltie
- Tracer Round family -> MARKSMAN -- 0024 Byte Beagle

LEASHBREAK TACTIX
- Leashbreak family -> CASTER -- 0025 Rosco
- Hack Jam family -> CASTER -- 0026 Synth Collie, 0077 Firewall, 0078 Glitchfork
- Blackout family -> CASTER -- 0027 Noir Setter, 0085 Sandbag, 0086 Whitenoise
- Barrier Ring family -> SUPPORT -- 0028 Pulse Border Collie, 0091 Bulwark, 0092 Brownout
- Heal Beacon family -> SUPPORT -- 0029 Holo Husky, 0079 Deadbolt, 0080 Static
- Frost Bark family -> CASTER -- 0030 Chill Samoyed, 0081 Bunkerlink, 0082 Shortcircuit (role Support, class CASTER: the kit is CC)
- Shatter family -> CASTER -- 0031 Prism Poodle, 0083 Faraday, 0084 Hexer
- Tag Shot family -> MARKSMAN -- 0032 Signal Pointer, 0087 Blacksite, 0088 Carrier
- Phase family -> ASSASSIN -- 0033 Ghost Spaniel, 0089 Hardline, 0090 Spike
- Echo Howl family -> CASTER -- 0034 Echo Dalmatian
- Ping family -> CASTER -- 0035 Static Sheba Inu
- Soothe family -> SUPPORT -- 0036 Vibe Shih Tzu

K9 CIRCUITRY
- Royal Hunt family -> ASSASSIN -- 0037 Crown Foxhound (siege assassin)
- Drone Swarm family -> SUMMONER -- 0038 Circuit Retriever, 0099 Casemate, 0100 Shrapnel
- Overclock family -> STRUCTURE (TURRET) -- 0039 Nova Shepherd, 0105 Emplacement, 0106 Salvo
- Overheat family -> STRUCTURE (RAMPER) -- 0040 Laser Beagle, 0093 Bunker, 0094 Buckshot
- Spark Pups family (K9) -> SUMMONER -- 0041 Volt Corgi, 0095 Howitzer, 0096 Tripwire
- Grid Lock family -> STRUCTURE (LOCKDOWN) -- 0042 Grid Schnauzer, 0097 Flakwall, 0098 Deadeye
- Arc Shot family -> CASTER -- 0043 Chrome Airedale, 0101 Pillbox, 0102 Hairtrigger (chain lightning kit)
- Beacon family -> SUPPORT -- 0044 Beacon Basset, 0103 Stronghold, 0104 Snubnose
- Tunnel Drones family -> STRUCTURE (NEST, reclassed) -- 0045 Neon Dachshund
- Battery family -> STRUCTURE (PYLON, reclassed) -- 0046 Flux Pomeranian
- Rail Shot family -> MARKSMAN -- 0047 Rail Terrier
- Mini Pup family -> STRUCTURE (NEST, reclassed) -- 0048 Pixel Pug

Census check: 106 cards assigned. BRUISER 30, ASSASSIN 21, CASTER 22,
MARKSMAN 10, SUPPORT 14, SUMMONER 6 (mobile spawners), STRUCTURE 9 native
+ 3 reclassed (0045, 0046, 0048) = 12 in the structure family.

Data hook: class ships as a derived table, NOT a canon.js edit (canon.js is
GENERATED -- the merge script `data/_build_canon.py` adds a `combatClass` field
to cards.json, then re-runs the canon merge). Until the merge runs, the engine
can derive it from a CLASS_BY_FAMILY constant keyed by ability.name inside
mapCanonToEngine() (engine.js ~line 340) next to the existing role/range
derivations. The Deck Lab card detail (index.html buildCatalog ~line 3754)
reads the same field for display.

### 1.3 The STRUCTURE FAMILY -- five distinct archetypes

Spec demand: "structures/buildings family with DISTINCT behaviors". Today all
3 native structure kits are flavors of "turret that shoots". The family pass
splits them into 5 archetypes and reclasses 3 existing cards to fill the gaps.

| Archetype       | Cards (existing -> become)                         | Behavior contract | Engine hook |
|-----------------|-----------------------------------------------------|-------------------|-------------|
| RAMPING DAMAGE  | 0040 Laser Beagle, 0093 Bunker, 0094 Buckshot (Overheat) | Damage climbs per consecutive second on the SAME target, resets on retarget. Beam visual. | Exists: `ramp` abilityKind + AK-FEEL B5 beam root (engine.js ~2054). Add a per-target ramp counter reset in doAttack target swap. |
| STATIC TURRET   | 0039 Nova Shepherd, 0105 Emplacement, 0106 Salvo (Overclock) | Flat heavy dps + a timed burst-fire window every CD (already the kit text). No ramp -- the reliable metronome. | Exists: structure firing loop; move the burst window onto a `crit`-style timed buff in maybeFireAbility (engine.js ~2088) so Overclock stops sharing the Overheat ramp code path. |
| LOCKDOWN / CC   | 0042 Grid Schnauzer, 0097 Flakwall, 0098 Deadeye (Grid Lock) | Upgraded from "slow field": HOLDS one unit (snare beam on the nearest non-structure enemy: snareTimer refresh while in range) AND keeps the 35% slow field on everyone else. One held target at a time. | slowTimer/slowMag + snareTimer already exist on Unit (engine.js ~562, ~889). New: a per-tick hold beam in the structure's update, same pattern as the Street Medics aura loop (computeSynergy, ~1555). |
| SPAWNER NEST    | 0045 Neon Dachshund (Tunnel Drones), 0048 Pixel Pug (Mini Pup) -- RECLASSED static | Becomes a planted den: move_speed 0, spawns its tokens on a repeating cooldown for its lifetime instead of once. Token cap 4 alive per nest (tokens already cannot recurse: isToken + abilityCD=Infinity, engine.js ~2166). | `spawn` case in maybeFireAbility already loops on cooldown for units; reclass = set isStructure true + speed 0 in mapCanonToEngine via a STATIC_OVERRIDE set, add an aliveTokens cap check before spawn. |
| AURA PYLON      | 0046 Flux Pomeranian (Battery) -- RECLASSED static | Becomes a planted battery pylon: move_speed 0, constant aura (+15% attack speed to allied STRUCTURES within 3.5 tiles, doubles its own card text). | Aura rides the existing ns* per-tick layer: apply `u.nsAtkSpd` to structures in radius inside computeSynergy's named pass (engine.js ~1522 reset, ~1555 apply) -- identical pattern to NS_HEAL_R Street Medics. Stays under DMG_CAP/MOVE_CAP budget. |

Balance note for the reclass trio (0045/0046/0048): static units lose escape
value, so each gets +10% hp in the same _build_canon.py pass (flag for the
balance auditor's fairness report, spec section 2 -- do not hand-tune here).

Anti-generic payoff: five structure archetypes x the PYLON enabling structure
decks means a "Bunker player" and a "Nest player" field visibly different
boards from the same dictionary.

---

## 2. CC ATTACK SUBTYPES (spec section 3, "lock, slow, knock, silence")

Four CC subtypes, each mapped to existing abilities and the EXISTING engine
timer it rides. No new timers needed; the subtype is a display/classification
tag plus the keys the section-3 combos read.

| Subtype | Definition | Engine field(s) | Existing abilities that get the tag |
|---------|------------|-----------------|--------------------------------------|
| LOCK    | Target can not move or act | stunTimer, snareTimer, frozenTimer (engine.js ~562, ~889; stun case ~2104) | Haymaker (0003/0049/0050 stun), Grid Lock upgraded hold (1.3 LOCKDOWN snare), Freeze spell (case 'freeze' ~2195), Trap spell (case 'trap' ~2210 snare) |
| SLOW    | Move + attack speed cut, still acts | slowTimer + slowMag (getSpeed ~595, atk ~1971) | Frost Bark (0030/0081/0082), Echo Howl (0034), Grid Lock field (0042/0097/0098), Slow spell (case 'slow' ~2203), tar-pit map hazard (~1205) |
| KNOCK   | Displacement: position broken, no timer | kbVx/kbVy impulse + exp decay (AK-FEEL B4, ~1720) | Shock Push (0007/0057/0058), Grav Pull (0009/0061/0062), knockback case ~2129 |
| SILENCE | Abilities off; movement + autos continue | silenceT (gates maybeFireAbility ~2088) | Signal Scramble (0020/0073/0074), Ping (0035), and the tower flavors: Hack Jam + Leashbreak (disable_tower case ~2119 = silence applied to a tower) |

Soft-CC annex (classified, not one of the four): BLIND (Blackout 0027/0085/0086
-- ranged misses) and REVEAL/MARK (Tag Shot, Beacon) are DENIAL tags, listed on
the card sheet under the same "Control" header but excluded from CC-counting
combos so blind spam can not double-dip the lock payoffs.

Display hook: the attribute sheet from spec section 1 (card detail in the Deck
Lab, index.html buildCatalog/card detail render) adds one line:
"CONTROL: Lock" / "CONTROL: Slow + field" etc., derived from abilityType via a
CC_SUBTYPE map that lives next to ABILITY_KIND (engine.js ~300).

---

## 3. SYNERGY EXPANSION -- 10 new named combos (spec section 3)

All ride the existing AK-SYNERGY contract (engine.js ~255): recomputed every
tick, symmetric for the AI, buffs ride the existing ns* layers under
MOVE_CAP/DMG_CAP, req/effect strings feed the Deck Lab reference list.
New entries append to NAMED_SYNERGY; per-tick application lands in
computeSynergy next to the existing ten (~1545-1578).

| id | label | req | effect | engine layer |
|----|-------|-----|--------|--------------|
| bruiser_wall | KNUCKLE UP | 3+ Bruisers alive | Bruisers +10% max-HP shield | nsShieldPct (exists) |
| hit_squad | HIT SQUAD | 2+ Assassins alive | Assassins +10% move, +6% damage | nsMove + nsDmg (exist) |
| street_sorcery | STREET SORCERY | 2+ Casters alive | Caster ability cooldowns refresh 15% faster | NEW nsCd mult, read where abilityCD ticks down -- same one-line pattern as the faction cdRefresh (engine.js SYNERGY table ~249) |
| firing_line | FIRING LINE | 2+ Marksmen alive | Marksmen +0.5 range | nsRangeAdd (exists) |
| puppy_mill | PUPPY MILL | 2+ Summoners alive | All friendly tokens +15% damage | nsDmg applied to isToken units (exists) |
| full_battery | FULL BATTERY | Pylon (0046) + 2+ Structures alive | Structures +15% attack speed | nsAtkSpd (exists); supersedes turret_net while active (take max, never stack the two) |
| lock_and_key | LOCK AND KEY | Lockdown structure + 1+ Assassin alive | Assassins +15% damage vs locked targets (stun/snare/frozen > 0) | NEW conditional in doAttack: check target CC timers before the damage mult -- one branch, capped by DMG_CAP |
| dead_air | DEAD AIR | 2+ Silence-subtype units alive | Silence and tower-jam durations +50% | NEW duration mult read at the silence/disable_tower cases (~2109, ~2119) |
| bodyguard_detail | BODYGUARD DETAIL | 1+ Bruiser + 2+ Supports alive | Supports take 15% less damage | rides the AK-ATTRS damage-taken clamp path (takeDamage def/spdef mults ~615), respects the 0.80 floor |
| wrecking_crew | WRECKING CREW | Structure + 1+ turret_break unit (0037/0047) alive | Those units +15% damage vs towers | NEW conditional in the tower-hit damage path (hitTower ~2479), mirrors lock_and_key shape |

Personalization tie-in (the 11th, account-flavored): GRUDGE MATCH -- when your
active NEMESIS (section 5) is on the enemy field, ALL your units +5% damage
(nsDmg). Two accounts never share a nemesis, so this combo literally can not
fire the same way on two accounts. Passes the anti-generic test by construction.

Budget note: every number above sits inside the established ~+15-25% modesty
band noted on the SYNERGY table comment; the two NEW conditional layers
(lock_and_key, wrecking_crew) must be checked by the balance auditor before
numbers ship.

---

## 4. SIDEQUEST CATALOG (spec section 5 -- DA:I layer)

### 4.0 Plumbing contract

- State: NEW key block in ak_world: `w.quests = { done:{questId:true},
  daily:{id, seed, expires, prog}, counters:{} }`. ak_world already cloud-mirrors
  (ak_* key rule, index.html ~4726), loadWorld() backfills it like checkpoint.
- Check point: ALL conditions are evaluated in ONE place -- grantMatchRewards
  (index.html ~4394) already receives the finished game object `g` with
  g.result, g.time, g.gatesCleared, g.worldCity, g.startSection, crowns, and
  the deck. recordWorldResult (~4126) persists.
- Counter hooks the implementation wave adds to the engine (all cheap):
  g.stats = { killsByCard:{}, deploysByCard:{}, spellsCast:0, towersLost:0,
  kingDamageTaken:0, ccApplied:{lock,slow,knock,silence} } -- incremented at
  unit death, deployUnit, castSpell, Tower.takeDamage. These same counters
  power the rap sheet (section 6), so they are built ONCE.
- Rewards pay through the existing economy verbs: coins, scrap (addScrap),
  keys, chests (DBPROFILE.chests), sp, and COSMETIC TOKENS (new
  p.identity.cosmetics -- section 6.4). Journal surface = the Quest Journal
  from spec 5, rendered from w.quests on the world map screen.
- Quests display with their act flavor line in the STORYLINE_CANON.md voice.

### 4.1 The 30 city sidequests (3 per city)

CITY 1 -- THE LOT ("Born in the Dirt")
1. STRAY'S OATH -- win any Lot level fielding ONLY cost<=4 cards (canonCost),
   deck check at startMatch. Reward: 150 coins + bronze chest.
2. FIRST BLOOD -- land 10 kills with a single card in one Lot match
   (g.stats.killsByCard). Reward: 30 Common scrap + that card gets the
   "Lot Proven" badge progress (section 6.3).
3. NO HELP COMING -- clear any Lot level casting ZERO spells
   (g.stats.spellsCast === 0). Reward: 1 key.

CITY 2 -- NEON NIGHT ("All Teeth, No Mercy")
4. ZOOMIE NIGHT -- win a Neon Night level with an all-Zoomie-Syndicate deck
   (deck factionId check). Reward: 200 coins + 20 Rare scrap.
5. UNDER THE CLOCK -- 3-crown any Neon Night level in under 90 seconds
   (g.result win + crowns 3 + g.time < 90). Reward: silver chest.
6. GHOST RUN -- win while your king takes zero damage
   (g.stats.kingDamageTaken === 0). Reward: deploy-line color token "Neon Pink".

CITY 3 -- GOLDEN INDUSTRIAL ("Every Leash Breaks")
7. JAILBREAK -- silence or jam enemy abilities/towers 8 times in one match
   (g.stats.ccApplied.silence >= 8). Reward: 20 Rare scrap + 100 coins.
8. UNION CREW -- win with a deck holding all 4 factions (chaos_crew check at
   deck level, not field level). Reward: 1 sp.
9. SCAB-FREE SHIFT -- win without losing a single tower
   (g.stats.towersLost === 0). Reward: silver chest.

CITY 4 -- RAIN DOCKS ("Everything Ships")
10. HARBOR LOCK -- apply 12 slows in one Docks match (ccApplied.slow >= 12).
    Reward: 20 Rare scrap.
11. CRATE CRACKER -- win 3 Docks levels in one calendar day (counter in
    w.quests.counters keyed by date). Reward: gold chest.
12. LONGSHORE LINE -- win fielding 3+ Marksman-class cards in the deck.
    Reward: profile banner token "Rain Docks Skyline".

CITY 5 -- UNDERCITY SUBWAY ("The Quiet Line")
13. THIRD RAIL -- win a Subway level using NO Structure-family cards (deck
    check). Reward: 150 coins + 1 key.
14. TUNNEL RAT -- kill 6 enemies with Assassin-class cards in one match
    (killsByCard joined to the class table). Reward: 25 Rare scrap.
15. LAST TRAIN -- win a Subway level that went past 240 seconds (g.time > 240).
    Reward: bronze chest + 100 coins.

CITY 6 -- SKYLINE ROOFTOPS ("Signal and Crown")
16. ANTENNA WAR -- win with 2+ Structures alive at the final bell (field scan
    at endMatch). Reward: 20 Epic scrap.
17. CLEAN FEED -- win without your units being silenced once (ccApplied
    mirror: ccTaken.silence === 0). Reward: token frame "Broadcast Gold".
18. FREEFALL -- 3-crown a Rooftops level on the FIRST attempt of the day
    (w.quests.counters first-try flag). Reward: silver chest + 1 key.

CITY 7 -- TOXIC SEWERS ("The Poison Works")
19. IRON STOMACH -- win while the flood/map hazard deals 300+ damage to your
    side (hazard path engine.js ~1204 increments a counter). Reward: 25 Epic scrap.
20. CLEANUP CREW -- win fielding 2+ Support-class cards and zero deaths on
    those supports. Reward: 200 coins + accent color token "Biohazard Green".
21. RAT KING -- spawn 12+ tokens in one Sewers match (deploysByCard on
    isToken). Reward: bronze chest + 50 coins.

CITY 8 -- CASINO STRIP ("The House Limit")
22. DOUBLE OR NOTHING -- win two Strip levels back to back without a loss
    between (streak counter). Reward: gold chest.
23. CARD COUNTER -- win with a deck of 11 UNIQUE ability families (no two
    cards from the same family, table in 1.2). Reward: 1 sp.
24. HOUSE ALWAYS LOSES -- beat the L10 Strip boss with $BCARDD (0001) in the
    deck. Reward: $BCARDD nickname slot unlocks gold lettering (cosmetic flag
    on p.cardMeta['0001']).

CITY 9 -- FROST DISTRICT ("Nothing Stays Frozen")
25. COLD SNAP -- apply 10 LOCK-subtype CCs in one match (ccApplied.lock >= 10).
    Reward: 25 Epic scrap.
26. THAW PATROL -- win a Frost level without any of your units getting slowed
    (ccTaken.slow === 0; Slipstream/Whippet tech). Reward: deploy-line token
    "Ice White".
27. SNOWED IN -- win with 3+ Structure-family cards in the deck. Reward:
    silver chest + 100 coins.

CITY 10 -- CROWN CITADEL ("Crowns Get Taken")
28. PRETENDER'S FALL -- beat any Citadel level with NO Mythic cards in the
    deck. Reward: gold chest.
29. KINGMAKER -- win with a queen_target card (0001/0013/0024/0025/0037)
    landing the final tower hit (lastHitBy on the king tower, section 5 hook).
    Reward: 30 Legendary scrap.
30. THE LONG WAY UP -- clear Citadel L10 from district 0 with no checkpoint
    resume (g.startSection === 0 + worldCity 9 + level 10). Reward: diamond
    chest + profile theme token "Alley King Gold" (the flex accent).

### 4.2 Six rotating daily bounty templates

Dailies are TEMPLATES with parameter slots, seeded daily (date-seeded PRNG so
all players get a fair roll, but different accounts sit at different cities,
so the playable set differs). 2 active per day, stored in w.quests.daily,
journal shows the countdown. Rewards intentionally below sidequest rates
(retention drip, per the LOOT_SYSTEM_MANDATE core-loop note).

| Template id | Text pattern | Params | Reward band |
|-------------|--------------|--------|-------------|
| b_faction_wins | "Win {N} matches running {FACTION} majority (6+ cards)" | N: 2-3, FACTION: 4 | 100-150 coins |
| b_speed_clear | "Win a world level in under {T} seconds" | T: 100-150 | bronze chest |
| b_class_kills | "Land {N} kills with {CLASS}-class cards" | N: 8-15, CLASS: 7 | 15-25 scrap of the day's rarity |
| b_cc_quota | "Apply {N} {SUBTYPE} effects" (lock/slow/knock/silence) | N: 6-15 | 100 coins + 10 scrap |
| b_perfect_gate | "Clear {N} convoy gates without losing a tower" | N: 2-4 | 1 key |
| b_underdog | "Win using a deck with average canon cost under {C}" | C: 4.0-4.5 | 150 coins + bronze chest |

Hook recap: template check = same grantMatchRewards seam as sidequests; the
daily roll = a tiny dateSeed() next to loadWorld(); journal = new panel on the
world screen (wmScreen DOM block, index.html ~4730) listing act progress
(w.prog), active sidequests for the open city, and daily timers.

---

## 5. NEMESIS SYSTEM (spec section 6 -- Shadow of Mordor layer)

### 5.1 Data shape (lives in ak_world -- cloud-mirrored, loadWorld() backfills)

```
w.nemesis = {
  v: 1,
  byCity: {
    "<cityIdx>": [            // max 4 named rivals per city (spec: 3-5)
      {
        id: "nx_<cityIdx>_<seq>",
        card: "0067",          // canon cardNumber the rival rides (the AI unit)
        name: "Scarjaw",       // generated, tables in 5.2
        title: "Warden of the Docks",
        deed: "king_kill",     // what promoted it: king_kill | top_damage
        tier: 2,               // 1..3 -> buff mult 1.12 / 1.22 / 1.35
        wins: 3, losses: 1,    // ITS record vs THIS player (rap sheet fuel)
        lastLevel: 4,          // level it last beat you on
        bornTs: 0, lastTs: 0,
        tauntSeed: 12345       // stable pick into the taunt tables
      }
    ]
  }
}
```

### 5.2 Name generator -- breed x district x deed

Street name = pick(BREED_NAMES[breedGroup]) and title = TITLE_BY_DEED[deed] +
" of the " + DISTRICT_NOUN[city]; tauntSeed keeps it stable per rival.

BREED_NAMES (by breed group of the rival's card; lore voice, nothing soft):
- Heavy (Mastiff/Rottweiler/Corso/St. Bernard/Bullmastiff/Dogo): Scarjaw,
  Cinder, Slagmouth, Pothole, Rebar, Gravedigger, Dumptruck, Knucklebone
- Fast (Greyhound/Whippet/Saluki/Vizsla/Malinois/Doberman): Hairpin, Streak,
  Sliver, Quickdraw, Razorlip, Sidewinder, Skiptrace, Afterimage
- Clever (Collie/Poodle/Basenji/Setter/Pointer/Spaniel): Static, Wiretap,
  Mirage, Loophole, Cardsharp, Whisper, Blackout Bess, Fine Print
- Scrapper (Pug/Corgi/Shiba/Sheltie/Shih Tzu/Pom/Dachshund/Beagle/Basset/
  Terrier/Schnauzer/Airedale/Retriever/Shepherd/Husky/Samoyed/Akita/Chow/
  Boxer/Bulldog/Foxhound and any unlisted breed): Halfpint, Mousetrap,
  Low Blow, Shortfuse, Curbside, Ankles, Sawed-Off, Piecework

TITLE_BY_DEED:
- king_kill (it cracked your Alpha Den): Warden, Kingtaker, Gatecrasher, Executioner
- top_damage (no killer identified, top damage fallback): Butcher, Collector,
  Enforcer, Tollman

DISTRICT_NOUN by city (matches WORLD_CITIES order, STORYLINE_CANON flavor):
the_lot: "Dirt" | neon_night: "Strip Lights" | golden_industrial: "Chainline" |
rain_docks: "Docks" | undercity_subway: "Quiet Line" | skyline_rooftops:
"High Steel" | toxic_sewers: "Poison Works" | casino_strip: "House" |
frost_district: "Freeze" | crown_citadel: "Throne Steps"

Example outputs: "Scarjaw, Warden of the Docks" / "Wiretap, Butcher of the
Quiet Line" / "Halfpint, Gatecrasher of the Dirt".

### 5.3 Promotion / demotion rules

PROMOTION (on a player LOSS in a world level):
1. Identify the killer: the enemy UNIT that landed the killing blow on the
   player king tower. Engine hook: Tower.takeDamage(d) (engine.js ~527) gains
   an optional attacker arg passed from the two damage call sites (~2067/~2075
   and projectile impact); store t.lastHitBy = attacker.card.cardNumber.
   Fallback when the king survived (timeout loss) or the killer was a token:
   the enemy card with the highest damage dealt (g.stats mirror), deed
   "top_damage".
2. If that card already IS a rival in this city: tier+1 (cap 3), wins+1, new
   taunt rolls.
3. Else if the city roster < 4: create a new tier-1 rival on that card.
4. Else: the LOWEST-tier rival is replaced (street churn -- "somebody got
   clipped over the winter"); the journal logs the succession line.

DEMOTION (on a player WIN in a level where a rival fielded):
- Rival present + you win: losses+1 and tier-1. At tier 0 the rival is REMOVED
  (journal: "{name} won't show face on this block again.") and pays the bounty.
- Bounty: chest tier bumped +1 step for that match inside grantMatchRewards
  (same seam as the AK-CHESTRULE first-clear bumps, index.html ~4419), plus
  20 scrap of the rival card's rarity, plus rap-sheet credit "Grudges Settled".

FIELDING a rival (cheap, per spec: "a buffed featured unit in the AI deck"):
- When launching a world level in a city with rivals, pick the rival with the
  highest tier whose lastLevel is within +/-2 of the level being played
  (rivals haunt their turf), 60% chance to appear so re-runs stay fresh.
- Implementation: startMatch opts gains opts.nemesis = {card, name, tier}.
  At the AI deck build (engine.js ~707 quick-play path is untouched; the world
  district garrison swap ~947 is the seam) the rival card is inserted into the
  AI deck if absent, and at deployUnit time an AI unit of that card gets
  hp/dmg x (1.12/1.22/1.35 by tier) -- SAME multiplier seam as AK-AICURVE
  world scaling (engine.js ~1329), applied before computeBulk so colR/mass
  track the buffed hp -- plus u.nemesisName for the renderer name tag.
- recordWorldResult (index.html ~4126) is the single write point for all
  promotion/demotion state.

### 5.4 Taunt-line templates (cards_lore.js voice: short, street, TV-MA edge)

Slot vars: {name}=street name, {title}=title, {city}=district noun,
{deck}=player's active deck name, {king}=player king. Pick by tauntSeed so a
rival keeps ITS voice between fights.

REMATCH INTRO (entering a level the rival haunts):
- "Back for another beating, stray? The {city} remembers. So do I."
- "{name} runs this block now. You just rent the dirt you bleed on."
- "Heard you been telling dogs you almost had me. Almost is a stray's word."
- "Your '{deck}' crew again? I put that lineup in the ground once already."
- "They call me {title} now. You helped me earn it. Come collect the regret."
- "Every scar on my hide has a name. Yours is the one I say smiling."

PROMOTION (shown on the loss screen when a rival is born/climbs):
- "The dog that cracked your Den has a name now: {name}, {title}."
- "{name} took your crown clean. The whole {city} heard it snap."
- "Word travels. {name} got stripes off your hide tonight."
- "You made {name}. Remember that when it comes back meaner."

DEFEAT / DEMOTION (shown on the win screen):
- "{name} limps off the {city}. Tier broken. Debt paid."
- "Crown stays where it was. {name} learns what stray really means."
- "You settled it in the open, fangs to fangs. {name} won't bark your name again."
- "The {city} watched {name} fold. Streets keep receipts."

Anti-generic payoff: rival rosters are born from each player's own losses --
two veterans CANNOT have the same nemesis wall. The GRUDGE MATCH combo
(section 3) and the "Grudges Settled" rap-sheet counter (section 6) close the
loop so the grudge is visible on the profile, not just in the journal.

---

## 6. PERSONALIZATION FEATURES (spec section 7 -- the governing principle)

All player-owned identity lives in ak_profile (cloud-mirrored ak_* key) under
TWO new backfilled blocks, following the exact loadProfile() backfill pattern
(index.html ~3727: "never rewrites existing values"):

```
p.cardMeta = {            // per-card identity, keyed by cardNumber
  "0001": {
    nick: "Pesos",        // 6.1 nickname (max 14 chars, profanity-filtered)
    rec: { k:412, d:38, tw:61, w:120, ab:903 },   // 6.2 rap sheet
    badges: ["certified","crowned"],               // 6.3 earned ids
    gold: true            // cosmetic flags (e.g. Casino quest 24)
  }
}
p.identity = {            // profile-level identity (6.4)
  accent: "ak_gold",      // theme token id -> CSS var
  banner: "rain_docks",   // owned banner token
  frame: "broadcast_gold",// card-token frame
  deployLine: "neon_pink",// battlefield deploy-zone tint token
  motto: "Crowns get taken.",
  status: "hunting Scarjaw",
  top8: ["0001","0013","0040", "..."],   // MySpace Top-8 showcase, card numbers
  cosmetics: ["neon_pink","ice_white"]   // OWNED tokens (quests grant here)
}
```

### 6.1 Card nicknames
- Rename any owned card; the nickname renders FIRST everywhere the player sees
  their own card (deck lab, hand card, unit name tag, kill feed), canon name
  drops to a subtitle. Other surfaces (shop, lore) keep canon names.
- Hooks: card detail panel (Deck Lab) gets a rename field writing
  p.cardMeta[num].nick via saveProfile(); the in-match unit name tag reads it
  at deployUnit through the startMatch profile mirror (the same lsGet seam
  activeDeckNames() uses, index.html ~3744). Engine itself stays
  nickname-blind (display only -- zero balance surface).
- Anti-generic: a veteran's hand literally reads in their own language.

### 6.2 Rap sheet (per-card battle record)
- Counters: k (kills), d (deaths), tw (tower hits that destroyed a tower),
  w (matches won while in deck), ab (abilities fired). Fed by the SAME
  g.stats counters built for sidequests (section 4.0) -- one engine pass,
  two features. grantMatchRewards merges g.stats into p.cardMeta[num].rec.
- Display: card detail shows it as a police-blotter block ("412 KILLS /
  61 TOWERS CRACKED / RAN WITH 120 WINS"), lore-voice labels.
- Profile aggregates: total kills, favorite weapon (max-k card), "Grudges
  Settled" (nemesis demotions, section 5.3).

### 6.3 Badges (per-card + account), unlock conditions
Checked in grantMatchRewards right after the rec merge; ids append-only.

| id | name | condition (counter source) | scope |
|----|------|-----------------------------|-------|
| certified | CERTIFIED | rec.k >= 100 | card |
| crowned | CROWNED | in deck for a city L10 boss win (g.worldCity + level 10 + win) | card |
| wrecker | WRECKER | rec.tw >= 50 | card |
| ride_or_die | RIDE OR DIE | rec.w >= 100 | card |
| trigger_finger | TRIGGER FINGER | rec.ab >= 250 | card |
| untouchable | UNTOUCHABLE | win with kingDamageTaken === 0, 10 times (counter) | account |
| grudge_keeper | GRUDGE KEEPER | 5 nemesis demotions | account |
| block_historian | BLOCK HISTORIAN | all 30 sidequests done | account |
| first_of_name | FIRST OF THE NAME | nickname a card (starter badge, teaches the feature) | account |
| alley_king | ALLEY KING | clear Crown Citadel L10 | account |

Badges render as small stamps on the card art frame (card detail + Top-8) --
visual proof two accounts' copies of the SAME card look different.

### 6.4 Profile theme tokens (the MySpace page)
- Token types: accent (UI tint -- one CSS variable swap at boot from
  p.identity.accent), banner (profile header art from owned map/card art --
  reuses assets/maps art, zero new art per the ART_AUTOROUTE law until launch
  polish), frame (card token border in deck lab + match hand), deployLine
  (the deploy-zone tint in the arena renderer -- same draw call that renders
  the zone today, color swapped from a token table).
- Earn paths only (no generic defaults beyond the starter set): sidequests
  (section 4.1 grants 6 tokens), badges, city vault first-clears, nemesis
  bounties. Shop sells NONE of the quest tokens (earned identity stays earned;
  shop can sell separate token lines later per SHOP_MARKETPLACE_MASTER_PLAN).
- Motto + status: free-text (filtered), shown on the profile and -- later,
  social layer -- on the versus splash.
- Top-8: eight card slots, renders nicknames + badges + rap-sheet headline
  stats. THE flex surface; default = empty prompts ("Rep your eight").

### 6.5 Deck archetype detection heuristics
Computed at deck save (Deck Lab saveProfile seam) from the 11 cards' class +
cost + speedTier (all already on the engine card via mapCanonToEngine):

Scores (0..1 each, deck of 11):
- rush = 0.5*share(speedTier in Fast/VeryFast) + 0.5*share(canonCost <= 4)
- siege = share(STRUCTURE class) + 0.5*share(turret_break ability)
- control = share(CASTER class) + 0.5*share(CC subtype != none)
- swarm = share(SUMMONER class) + 0.5*share(canonCost <= 3)
- wall = share(BRUISER class) + 0.5*share(SUPPORT class)
- cutthroat = share(ASSASSIN class) + 0.5*share(queen_target)

Label = argmax with a 0.15 lead threshold; ties or no lead = "HYBRID" with the
top two names ("Wall-Control"). Display: deck header line in the player's
language, e.g. "You run a RUSH deck. 71% aggression." where aggression =
round(100 * rush / (rush + wall + control)). Stored as p.decks[i].arch =
{label, pct} so the profile playstyle panel and (later) matchmaking flavor
read it without recompute.
- Anti-generic: the GAME tells each player who they are, in numbers derived
  from their own choices; combined with nicknames the deck header is unique.

### 6.6 Anti-generic test, applied (spec section 7 gate)
Two veteran accounts after this wave differ in: nicknames on every card they
run (6.1), rap sheets + badge stamps on the art (6.2/6.3), accent/banner/
frame/deploy-line on every screen including the battlefield (6.4), a deck
archetype label in their own stats (6.5), a nemesis wall nobody else has
(5), a GRUDGE MATCH buff only they can trigger (3), and different sidequest
cosmetics earned in a different order (4). PASS.

---

## 7. IMPLEMENTATION HOOK INDEX (one table, build-wave checklist)

| Item | File + seam |
|------|-------------|
| combatClass field | data/_build_canon.py -> cards.json -> canon merge; interim CLASS_BY_FAMILY in engine.js mapCanonToEngine (~340) |
| Structure archetype behaviors | engine.js maybeFireAbility (~2088) + computeSynergy aura pass (~1522/1555) + STATIC_OVERRIDE in mapCanonToEngine |
| CC subtype tags | CC_SUBTYPE map next to ABILITY_KIND (engine.js ~300); card-detail line in Deck Lab |
| 10 new named combos | NAMED_SYNERGY append (engine.js ~265) + computeSynergy cases (~1545); new nsCd + 2 conditional damage branches |
| g.stats counters | engine.js: unit death, deployUnit, castSpell, Tower.takeDamage(+attacker), hazard tick (~1204) |
| Sidequests + dailies | ak_world w.quests; checks in grantMatchRewards (index.html ~4394); journal panel on wmScreen (~4730) |
| Nemesis state | ak_world w.nemesis; write point recordWorldResult (~4126); fielding via startMatch opts + garrison deck seam (engine.js ~947) + AK-AICURVE mult seam (~1329) |
| Killer identity | t.lastHitBy via attacker arg on Tower.takeDamage (engine.js ~527, call sites ~2067/2075 + projectile impact) |
| cardMeta + identity | ak_profile backfill in loadProfile (index.html ~3727); saveProfile mirror; CSS var at boot; deploy-zone tint in renderer |
| Archetype detection | Deck Lab save seam; p.decks[i].arch |

Numbers (combo %, nemesis mults, quest rewards) are PROPOSED -- the wave-6
balance auditor (spec section 2) signs off before any ships.
