# ALLEY KINGZ -- THE BLOCK CHRONICLES
## Production Story Bible v1.0 (canon-mined 2026-07-09)

**PRIME DIRECTIVE: ZERO INVENTED PROPER NOUNS.** Every faction, district, class,
handler, NPC, event and era name in this bible is mined from the live game data
files and cited per list. If a name is not in Section 1, it does not exist.
Writers who need a new name pull from the CANON REGISTRY or file a request --
they never coin one.

Banned strings from the superseded source doc appear in Section 7 ONLY, broken
with `//` on purpose (e.g. `Saint//line`) so a grep of this bible for the banned
spelling returns zero hits. That is a feature, not a typo.

No em-dashes anywhere in this file (hook law); use `--` instead.

---

# 1. CANON REGISTRY (the only names that exist)

## 1.1 The Four Crews + Stray
Source: `game/systems/raid.js` (FACTIONS, "crew, NEVER clan" in raid/UI copy),
`game/systems/population.js` (CLANS + STRAY: tags, epithets, home districts),
`game/canon.js` (CANON_META.factions). Note: `systems/story.js` prose uses the
word "clans" for the same four crews by design (HYBRID naming) -- the names
themselves never change.

| Crew | Accent | Tag | Epithet | Home turf | Gang sub-names (raid.js) |
|---|---|---|---|---|---|
| **Boneguard Crew** | `#e8c55a` gold (pop color `#C9772E` rust) | BONE | "the Rusted" | FACTORY ROW | The Boneyard Mob, Crypt Kings, Marrow Syndicate |
| **Zoomie Syndicate** | `#7CFFB0` green (pop color `#FF2E88` magenta) | ZOOM | "the Unbound" | THE STRIP | Zoomie Riot, Nitro Pack, The Burnouts |
| **Leashbreak Tactix** | `#9d8bff` violet (pop color `#7B5CFF`) | PHNTM | "the Hologhosts" | NEON HEIGHTS | Leashless Cartel, Ghost Wire Tactix, The Static Saints |
| **K9 Circuitry** | `#7fc8ff` blue (pop color `#00E0C0` teal) | VOLT | "the Crowned" | NEON HEIGHTS (capital) + THE OVERLOOK | Circuit Hounds, The Grid Pack, Voltage Kennel |
| **Stray** (no crew) | `#c9a84c` | STRAY | "no colors" | THE YARDS | -- |

Karma-layer faction keys (`systems/karma.js` DISTRICTS): `rusted` = Boneguard,
`unbound` = Zoomie, `hologhosts` = Leashbreak, `crowned` = K9, `neutral` = free.

## 1.2 Districts, Territories, Interiors

**The 9 walkable districts** (the 3x3 hub grid; source: `game/index.html` ZONES):

| District | Grid | Faction lean (karma.js) | Notes |
|---|---|---|---|
| **THE LOT** (HOME_TURF) | center | neutral | spawn / home block |
| **DOWNTOWN** | north | Zoomie (unbound) | commerce, the come-up |
| **NEON HEIGHTS** | NE | K9 (crowned) | glossy elite heights, the drip |
| **THE YARDS** | west | Boneguard (rusted) | industrial yards, scrap, stray turf |
| **FACTORY ROW** | east | Boneguard (rusted) | forge / mint / scrap |
| **THE STRIP** | south | Zoomie (unbound) | casino strip, street fights |
| **THE DOCKS** | SE | Leashbreak (hologhosts) | research / lab / tech |
| **THE OVERLOOK** | NW | K9 (crowned) | LOCKED -- barrier: POLICE CHECKPOINT |
| **THE UNDERCITY** | SW | Leashbreak (hologhosts) | LOCKED -- barrier: COLLAPSED BRIDGE |

**Interiors / buildings** (source: `game/index.html` ZONES buildings + HUD chips):
TOWN HALL (the Arena, seat of the block), TROPHY HALL, THE KENNEL (handlers),
the INFIRMARY (downed dogs recover here), THE DROP (shop), THE GARAGE (deck),
THE WARDROBE (drip), THE ARCHIVE (the Codex), CREW YARD, PASS HOUSE, THE FIXER
(Hit List / jobs), GEM MINE, GOLD MINT, CARD FORGE, RESEARCH LAB, THE GENERATOR,
THE STREET (street mode), THE ARCADE, THE FENCE (trade and launder goods).

**War-map territories** (source: `game/systems/worldmap.js` TERR_BGS + DBG):
downtown, neon_heights, the_yards, factory_row, the_strip, the_docks,
**the_overlook**, **the_undercity** -- rendered as enemy territory panels around
your home 3x3 base. War camps on the map are the six canon war crews
(`worldmap.js` localWarCrews): The Boneyard Mob, Crypt Kings, Zoomie Riot,
The Burnouts, **Leashless Cartel**, Circuit Hounds.

**The 10 world-campaign cities** (source: `game.html` WORLD_CITIES, in order):
the_lot, neon_night, golden_industrial, rain_docks, undercity_subway,
skyline_rooftops, toxic_sewers, casino_strip, frost_district, **crown_citadel**.
Each city runs 4 in-match districts: gate, market, works, core (WORLD_DISTRICTS).
One named skyline drop exists in season copy: **NeonReach** ("A Blood Moon over
NeonReach", `systems/seasons.js` BLOOD MOON flavor).

## 1.3 Combat Classes and Roles

**The 7 combat classes** (source: `game/classes.js` CLASS_BY_FAMILY):
**BRUISER, ASSASSIN, MARKSMAN, CASTER, SUPPORT, SUMMONER, STRUCTURE.**
There is no other class. Muscle is BRUISER, never anything else.

STRUCTURE archetypes (classes.js ARCH_BY_FAMILY): ramper, turret, lockdown,
nest, pylon.

**Canon roles** (source: `game/canon.js` per-card `role`): Vanguard, Striker,
Lancer, Skirmisher, Assassin, Blaster, Controller, Hacker, Spawner, Support,
Structure. Roles are the job title; classes are the fighting style.

## 1.4 The Six Handlers (the commanders)
Source: `game/handlers_data.js` (verbatim names, breeds, kit). Handlers live at
THE KENNEL in THE LOT (index.html: KENNEL building routes to handlers).

| Handler | Breed / frame | Special | Passive | Accent | Persona (from kit + desc) |
|---|---|---|---|---|---|
| **The Mender** | St. Bernard / Medic | Field Kennel (heal totem) | Pack Scent (pack regen) | `#7FE3A0` | the battlefield saint; nobody dies on their watch |
| **The Tracker** | Bloodhound | Scent Probe (reveal + mark) | Keen Senses | `#E2B23A` | the nose that never loses a trail; impossible to hide from the pack |
| **The Shadow** | Basenji | Slipstream (stealth + speed) | Swift Paw | `#9B8CFF` | the silent one; teaches dogs to disappear |
| **The Rigger** | Doberman, Engineer | Drop Rig (Gun Nest / Tesla Coil / Flak Turret / Suppressor) | Structure Durability | `#D45A2C` | the wrench; builds the block's teeth |
| **The Bruiser** | Pit Bull / Mastiff | War Cry (rally) | Squad Toughness (+ Bone Wall synergy) | `#C0392B` | the wall that shouts back; Boneguard-coded |
| **The Dealer** | Coin Dog (Card #0001, $BCARDD mascot) | House Edge (luck flip) | Small Blessing | `#D4AF37` | the gold door legend; TEASE-ONLY in story copy (game.html hard rule: crown mark, white paw, a face-down card -- never named on-panel) |

## 1.5 The NPC Keepers
Source: `game/index.html` KEEPERS + keeperFor().

**Coach Diesel** (the Arena / Town Hall), **Prospector Pip** (Gem Mine),
**Banker Bones** (Gold Mint), **Sparks** (Card Forge), **Doc Wattson**
(Research Lab), **Patch the Medic** (Infirmary), **Mama Bones** (the Kennel),
**Goldie** (Trophy Hall), **Volt** (the Generator), **Scratch** (shops/markets),
**Roxy** (deck/crew rooms), **the Foreman** (Town Hall economy / builders),
**The Keeper** (generic fallback).

## 1.6 The Crown Bloodline (story spine)

**The 10 city acts + bosses** (source: `game.html` STORY_ACTS, WORLD_CITIES order):

| # | Act | City | Level-10 boss |
|---|---|---|---|
| 1 | **BORN IN THE DIRT** | the_lot | **THE LOT WARDEN** -- scarred old Bullmastiff who taxes every stray in the yard |
| 2 | **ALL TEETH, NO MERCY** | neon_night | **METER, THE NEON RUNNER** -- Greyhound fixer who bills by the second |
| 3 | **EVERY LEASH BREAKS** | golden_industrial | **THE IRON HANDLER** -- Cattle Dog foreman who keeps half the district collared |
| 4 | **EVERYTHING SHIPS** | rain_docks | **THE DOCK SOVEREIGN** -- Retriever quartermaster with a price for everyone |
| 5 | **THE QUIET LINE** | undercity_subway | **TERMINUS, THE STATION KING** -- barkless Basenji who jams every call for help |
| 6 | **SIGNAL AND CROWN** | skyline_rooftops | **THE SIGNAL KING** -- Foxhound spymaster selling secrets to the Citadel |
| 7 | **THE POISON WORKS** | toxic_sewers | **GANGRENE, THE PLAGUE WARDEN** -- Boneguard-bred Rottweiler exile |
| 8 | **THE HOUSE LIMIT** | casino_strip | **MARKER, THE PIT BOSS** -- silver-muzzled Afghan Hound in a velvet collar |
| 9 | **NOTHING STAYS FROZEN** | frost_district | **THE COLD SAINT** -- Samoyed warden of the Regent's freeze |
| 10 | **CROWNS GET TAKEN** | crown_citadel | **THE REGENT** -- the throne-sitter, ruling on borrowed legend |

The throne-city is **the Crown Citadel** ("a throne-city built by a stray and
squatted in by everything strays despise"). Clearing it mints the account stamp
**ALLEY KING** (game.html achievements).

**The Gen ladder** (source: `game/systems/story.js`): Gen I "THE STRAY'S RISE"
(the CROWN CLIMB: STRAY AWAKENING, PICK YOUR CLAN, PROVE YOURSELF, CREW WARS,
SEASONAL SUPREMACY, CHALLENGE THE KING, CROWNED). Gen II "THE BLOODLINE". Gen
III "THE LEGEND WARS".

**Story-layer figures** (story.js): **THE OLD PACK** (the dead legends, the
narrator chorus), **THE MONGREL KING, "the Dog That Eats Names"** (the named
nemesis on the throne climb), and **THE COLLAR** (the apex antagonist: the
pound, the catchers, the wagon -- the human system the Mongrel King served).

**Rank ladder** (story.js RANKS, mirrors economy.js rankDivision):
Stray, Pup, Runner, Warrior, Enforcer, Right Paw, **King of the Block**.

**District-rep tiers** (karma.js TIERS): Stranger, New Face, Known, Trusted,
Respected, Revered, Legend.

## 1.7 The Season Eras
Source: `game/systems/seasons.js` CHAPTERS (figurehead + crew are canon names):

| Era | Figurehead | Crew | Look |
|---|---|---|---|
| **JUNKYARD DYNASTY** | $BCARDD | Boneguard Crew | rust-gold, drifting embers |
| **NEON HOWL** | Jagged | Zoomie Syndicate | magenta neon, sparks |
| **DOG DAYS** | Rosco | Leashbreak Tactix | summer gold, heat shimmer |
| **BLOOD MOON** | Crown Foxhound | K9 Circuitry | crimson, red drizzle, "over NeonReach" |
| **FROSTBITE** | Stonejaw | Boneguard Crew | ice blue, snow, "locks the docks" |
| **GOLDEN LEASH** | $BCARDD | Boneguard Crew | gold finale, "crowns the kings of the street" |

## 1.8 The 5-Tier Shield Ladder (defense canon)
Source: `game/systems/raid.js` SHIELDS:
**Street Cover** (2h), **Crew Watch** (8h), **Iron Curtain** (12h),
**Fortress Dome** (16h), **Panic Button** (24h).
The live defense loop on THE LOT is the **BLOCK WAR** (index.html AK-BLOCKWAR,
4 defense posts; HUD: THE WATCH "defend your district", RAID "hit em for their
stash").

## 1.9 The Card Canon (106 cards)
Source: `game/canon.js` (CANON_META + CANON_CARDS), lore per card in
`game/cards_lore.js`, class per family in `game/classes.js`.

- **Counts:** 106 cards = 48 base dogs + 58 variants. Rarities: 34 Common,
  29 Rare, 29 Epic, 10 Legendary, **4 Mythic**.
- **The 4 Mythics (only four, ever):** **$BCARDD** (#0001, Dogo Argentino,
  Boneguard, "The Yung Printz", Crownbreaker), **Jagged** (#0013, Doberman,
  Zoomie, Shadow Fang), **Rosco** (#0025, Australian Cattle Dog, Leashbreak,
  Leashbreak), **Crown Foxhound** (#0037, Foxhound, K9 Circuitry, Royal Hunt).
- **Named Legendaries include:** Stonejaw (CANON_META.legendary), Cinderblock,
  Tombstone, Rollcage, Deadweight, Firewall, Sandbag, Bulwark, Casemate,
  Emplacement.
- **The 29 family lines** (canon.js `family`): every Rare/Epic base dog forked
  into two builds -- **[HEAVY]** ("bunkered, up-armored, +28% HP") and
  **[STREET]** ("stripped chop-shop build, +25% damage, glass"). Example, the
  **Balboa** line (Boxer, Haymaker): Cinderblock [HEAVY] and Knuckles [STREET].
  Full family list: Balboa, Iron Rottweiler, Granite Saint, Grit Bulldog, Alloy
  Akita, Warden Newfie, Rust Cane Corso, Pixel Greyhound, Circuit Shiba, Razor
  Vizsla, Flash Saluki, Bolt Corgi, Glitch Basenji, Aero Malinois, Synth Collie,
  Holo Husky, Chill Samoyed, Prism Poodle, Noir Setter, Signal Pointer, Ghost
  Spaniel, Pulse Border Collie, Laser Beagle, Volt Corgi, Grid Schnauzer,
  Circuit Retriever, Chrome Airedale, Beacon Basset, Nova Shepherd.
- **Rigs:** every card carries a `rig` (armored car build + flavor line) --
  panel-art gold. E.g. $BCARDD's **The Crown Rig**: "matte-black armored
  war-truck, gold trim, ram plow."
- **The 5 spells** (canon.js CANON_SPELLS + cards_lore.js S001-S005): Boneguard
  winter doctrine (zone freeze), Leashbreak tar line, K9 buried snare, Zoomie
  jolt, and the neutral fire classic.

## 1.10 The Street Population (bot roster)
Source: `game/systems/population.js`. Deterministic AI dogs, ~6 per crew plus
strays, ranked King of the Block down to Pup. First-name pool (NAMES, verbatim):
Rax, Cinder, Dozer, Switch, Maw, Rivet, Tilt, Grime, Husk, Cleat, Sarge, Vex,
Knuckles, Diesel, Scrap, Brick, Fang, Cobble, Nyx, Ratchet, Smoke, Wire, Gnash,
Tar, Hollow, Crank, Rebar, Slug, Patch, Choke, Vandal, Static, Dent, Marrow,
Gristle, Scab, Howl, Wretch, Bane, Creed, Mange, Ruckus, Sully, Ash, Mutt.
Street chatter attributes to these names; comic background dogs pull from here.

---

# 2. CITY TIMELINE (six anchor events, all derived from canon)

Every card story pins itself to at least one anchor. Two cards may remember the
same anchor differently (see the Contradiction Engine, 3.4) -- the EVENT never
changes, only the telling.

**T1 -- THE JUNKYARD DYNASTY (the founding era).**
Rust, chain-link, stacked dead cars: The Lot, "where you were whelped and where
the city expects you to die quiet" (STORY_ACTS act 1). In this era $BCARDD, the
white-coat Dogo Argentino, "took the alley throne bare-fanged and never looked
back" (cards_lore.js #0001). Boneguard Crew ran the scrapyards and hauled rust
into a crown (seasons.js JUNKYARD DYNASTY flavor). Everything after is measured
against this: the first crown came out of the dirt.
Sources: cards_lore.js 0001, seasons.js CHAPTERS[junkyard], game.html STORY_ACTS[0].

**T2 -- THE CHOP-SHOP SPLIT (the variant schism).**
The era the 29 family lines forked. Every great line split into a bunkered
**[HEAVY]** build and a stripped **[STREET]** build -- "up-armored, near
unkillable" versus "panels torn off for the kill" (canon.js variant desc; the
[STREET] rig flavor is literally "stripped chop-shop"). The Balboa line is the
famous one: Cinderblock, the legend "from the old fight pits under the
overpass," versus Knuckles, the young door-circuit brawler (cards_lore.js
0049/0050). Brother against brother, same Haymaker, two philosophies. Every
family line carries this wound.
Sources: canon.js variant/family/desc fields, cards_lore.js 0049-0106.

**T3 -- THE RISE OF THE CROWN CITADEL (the Regent's era).**
A throne-city "built by a stray and squatted in by everything strays despise"
(STORY_ACTS act 10). The Regent took the chair he was given, draped himself in
the old king colors, and wired the city under him: the Lot Warden taxing the
dirt, Meter billing the lanes, the Iron Handler running leashes, the Dock
Sovereign moving iron, Terminus jamming the tunnels, the Signal King selling
secrets to the Citadel, Gangrene exiled to the Poison Works, Marker keeping the
ledger, the Cold Saint administering the freeze -- every boss paying up to the
Citadel gate. The freeze of the frost_district was the Regent's warning to
crews that rise (act 9 intro).
Source: game.html STORY_ACTS[0..9].

**T4 -- EVERY LEASH BREAKS (the Leashbreak founding).**
Rosco, the Cattle Dog, "chewed off his own chain and came back for everyone
else's" (cards_lore.js #0025). The Leashbreak Tactix were born in yards like
the Iron Handler's -- "so was their grudge" (STORY_ACTS act 3 intro). The Iron
Handler "learned leash-craft from the same yards Rosco chewed out of, and never
forgave the Tactix for proving chains are temporary." The deeper truth sits
above every leash: THE COLLAR -- the pound, the catchers, the wagon -- the
system the Mongrel King himself served (story.js COLLAR).
Sources: cards_lore.js 0025, game.html STORY_ACTS[2], systems/story.js COLLAR.

**T5 -- THE BLOCK WAR (the present day).**
The live loop IS the story's now: crews raid each other's blocks for the stash
(raid.js), the Watch defends the district (BLOCK WAR posts on THE LOT,
index.html), war camps like the **Leashless Cartel** and **Crypt Kings** sit on
the war map (worldmap.js localWarCrews), and blocks buy quiet on the shield
ladder -- Street Cover to Panic Button (raid.js SHIELDS). Rank in this war runs
Stray to King of the Block (story.js RANKS). The Mongrel King, the Dog That
Eats Names, sits at the top of the ladder eating challengers (story.js).
Sources: systems/raid.js, systems/worldmap.js, index.html AK-BLOCKWAR, systems/story.js.

**T6 -- THE COMING OF THE MYTHICS (the rumor era, now unfolding).**
Four names the street only half believes: $BCARDD holding the Junkyard crown,
Jagged ("nobody has seen Jagged arrive, only leave," cards_lore.js #0013),
Rosco walking at the Queen with dead towers behind him, and Crown Foxhound --
the breed "bred to run royalty to ground" (#0037), the same bloodline as the
Signal King who watches everything for the Citadel. Each season era turns the
city toward one of them: NEON HOWL lights the strip for Jagged, DOG DAYS hands
Rosco the summer, BLOOD MOON runs Crown Foxhound's circuits red over NeonReach,
FROSTBITE digs Stonejaw's pack in, and the GOLDEN LEASH finale crowns the kings
of the street under $BCARDD.
Sources: canon.js CANON_META.mythics, cards_lore.js 0001/0013/0025/0037, seasons.js CHAPTERS.

---

# 3. TONE, READER PROMISE, CANON LAWS

## 3.1 Tone
Gritty gangland, GTA-of-dogs (story.js design note verbatim). Streets, turf,
betrayal, hard edges; the rescue-stray heart underneath. TV-MA voice, **nothing
past damn/hell** (game.html STORY_ACTS hard rule). Loyalty is earned. "Crowns
get taken, never given" (#0001 tagline) is the thesis of the whole universe.

## 3.2 Reader promise
Every card is a person. Every story pays off in the game you are already
playing: the dog you level is the dog whose secret you unlock; the district you
walk is the district on the panel; the boss you fight tonight is the name the
bio has been dreading for three beats. Nothing in the comics happens somewhere
you cannot stand.

## 3.3 The Character Contract (every dog, no exceptions)
Every story package carries exactly:
1. **One wound** -- what the streets took (seed it from the card's bio in cards_lore.js).
2. **One choice** -- the decision that defines them (usually crew vs self, HEAVY vs STREET, leash vs teeth).
3. **One ally** -- a named canon card, keeper, or handler.
4. **One rival** -- a named canon card, boss, or crew.
5. **One unresolved thread** -- left open on purpose; future issues collect it.
6. **One city-event anchor** -- a T1..T6 timeline tag.

## 3.4 The Contradiction Engine (no self-narration is objective)
Every voice is street testimony. When two cards reference the same anchor
event, they are ALLOWED (encouraged) to disagree on details -- who swung first
at the Chop-Shop Split, what Rosco really said when the chain broke, whether
the Dealer's gold door even exists. The data layer records the disagreement
explicitly (`contradictionLinks`, Section 4) so it reads as designed mythology,
not an error. Resolution, if it ever comes, is an EVENT (a new issue), never a
retcon.

## 3.5 Rarity is myth-weight (the in-universe table)
Mapped to OUR rarities (canon.js counts: 34/29/29/10/4):

| Rarity | In-universe meaning | Story privileges |
|---|---|---|
| **Common** (34) | Faces of the block. The street knows them by sight. | Full package; barks lean neighborly; they witness the myths. |
| **Rare** (29) | Names the block repeats. Proven in a crew war. | Full package + one contradiction link. |
| **Epic** (29) | District legends. Lieutenants; a keeper knows them by name. | Package + a boss or handler crossover beat. |
| **Legendary** (10) | Era-defining. A season era or war camp carries their echo (Stonejaw HAS an era: FROSTBITE). | Package + a timeline anchor they are load-bearing in. |
| **Mythic** (4, closed set: $BCARDD, Jagged, Rosco, Crown Foxhound) | The street is not sure they are real. | RUMOR-BEFORE-REVEAL: other cards talk about them for a full run before their own package unlocks. Their secretTruth beats stay locked longest. |

## 3.6 Canon laws (hard)
- Crews are the only factions. Raid/UI copy says **crew**; story prose may say
  clan (story.js hybrid rule). Never invent a fifth.
- The Dealer is TEASE-ONLY on panels: crown mark, white paw, a face-down card.
  Never named in a story beat as the figure behind the gold door (game.html rule).
- Only the four Mythics. No new Mythic, ever, in prose or art.
- The Collar (the pound / the catchers) is the apex threat; the Mongrel King
  served it. Late-arc stories may point at it; none may kill it.
- Every mode exits to the district map; every story exits to the block --
  endings land the dog back on named canon ground.
- No em-dashes in any shipped copy (hook law across the repo); use `--`.
- No new tracking systems: story unlocks read existing profile signals only
  (Section 4.2).

---

# 4. STORY PACKAGE SCHEMA -- `cards_stories.js`

Plain JS, headless-safe, window-guarded, keyed by cardNumber -- the exact
pattern of `cards_lore.js` and `classes.js`. canon.js stays untouched.

```js
/* AK-STORIES: Alley Kingz card stories -- THE BLOCK CHRONICLES data layer.
   Keys = cardNumber. Sidecar to canon.js/cards_lore.js. NO em-dashes (hook law). */
(function (global) {
  var STORIES = {
    "0003": {                                  // Balboa (example shape)
      codename: "Balboa",                      // MUST equal canon.js name
      metadata: {
        rarity: "Epic",                        // canon.js rarity, verbatim
        faction: "Boneguard Crew",             // canon.js class, verbatim
        cls: "BRUISER",                        // classes.js CLASS_BY_FAMILY
        familyLine: "Balboa",                  // canon.js family (null if none)
        district: "THE_YARDS",                 // a ZONES id from index.html
        timelineTags: ["T1_JUNKYARD_DYNASTY", "T2_CHOPSHOP_SPLIT"],
        relationshipTags: [
          { cardNumber: "0049", rel: "blood",  note: "Cinderblock, the HEAVY fork of his line" },
          { cardNumber: "0050", rel: "blood",  note: "Knuckles, the STREET fork" },
          { cardNumber: "0006", rel: "ally",   note: "Grit Bulldog, corner man" },
          { boss: "THE LOT WARDEN", rel: "rival" }   // bosses/handlers/keepers by canon name
        ],
        themes: ["legacy", "the split", "one more round"]
      },
      publicHook:   "One hand. Lights out.",   // may reuse cards_lore tagline
      coreWound:    "...",                     // the one wound (3.3)
      definingChoice: "...",
      secretTruth:  "...",                     // gated behind the deepest unlock
      beats: [
        { key: "origin",    unlock: "owned",          text: "...", panelPrompt: "..." },
        { key: "wound",     unlock: "cardLevel>=3",   text: "...", panelPrompt: "..." },
        { key: "oath",      unlock: "repRank>=2",     text: "...", panelPrompt: "..." },
        { key: "collision", unlock: "storyChapter>=3",text: "...", panelPrompt: "..." },
        { key: "secret",    unlock: "cardLevel>=5",   text: "...", panelPrompt: "..." }
      ],
      ambientBarks: {
        streetTalk:     ["..."],               // population.js feed lines
        keeperGreeting: { keeper: "Coach Diesel", lines: ["..."] },
        nemesisTaunts:  ["..."],               // vs rival card / boss
        infirmaryLines: ["..."]                // Patch the Medic context
      },
      contradictionLinks: [
        { cardNumber: "0049", event: "T2_CHOPSHOP_SPLIT",
          disagreement: "Balboa says the line split over doctrine; Cinderblock says it split over a purse." }
      ]
    }
  };
  if (global) { global.AK_STORIES = STORIES;
    global.AK_STORY_GET = function (n) { return STORIES[n] || null; }; }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
```

## 4.2 Unlock keys -- EXISTING profile signals ONLY
No new tracking. The five legal unlock expressions and where they already live:

| Unlock | Reads |
|---|---|
| `owned` | the card exists in the player's collection (economy.js profile cards) |
| `cardLevel>=3` / `cardLevel>=5` | the card's level on the profile (existing level system) |
| `repRank>=N` | trophies rank idx 0..6 via the RANKS ladder (story.js / economy.js rankDivision: Stray=0 ... King of the Block=6) |
| `storyChapter>=N` | `p.storyStage` 0..6 on the Crown Bloodline spine (story.js) |

Beat keys are the closed set `origin | wound | oath | collision | secret`.
Recommended default ladder: origin=owned, wound=cardLevel>=3,
oath=repRank>=2, collision=storyChapter>=3, secret=cardLevel>=5. Mythics
invert: their origin stays locked until storyChapter>=5 (rumor-before-reveal).

---

# 5. VOICE RULES + PANEL ART PROMPT RECIPE

## 5.1 Voice rules
- First-person or tight-third street testimony. Nobody is objective (3.4).
- TV-MA ceiling: damn/hell max. No slurs, no drugs-by-name, dogs never die
  on-panel -- they go down and land in the Infirmary (canon loop: "death ->
  infirmary").
- Crew diction: Boneguard talk in weight and debt ("the math only gets worse
  for you"); Zoomies talk in speed and receipts; Leashbreak talk in chains,
  signal and cold; K9 Circuitry talk in grids, logs and efficiency. Mine
  cards_lore.js bios -- the register is already set there.
- Keepers keep their index.html cadence (Mama Bones warm, Banker Bones
  count-it-twice, Coach Diesel fight-night, Patch gentle).
- No hyphens gymnastics, no em-dashes, use `--`.

## 5.2 Global style lock (prepend to every panel prompt)
> gritty gold-cyberpunk noir comic panel, heavy inks, halftone shadow, hard rim
> light, Everlight gold accent #e8c55a against ink-black #06060a, wet asphalt
> reflections, anthropomorphic street dogs, no humans on panel

## 5.3 Per-dog canonical description slot
Each dog's `panelPrompt` inserts, in order:
1. **Breed + build** from canon.js (`breed`, HEAVY = bulked and plated, STREET
   = lean, panels torn off).
2. **Crew colorway** from the accent table (1.1) -- collar, tag paint, glow.
3. **Signature kit tell** from the ability family (classes.js): a Bruiser's
   plated shoulders, a Caster's static halo, a Structure's bolted chassis.
4. **The rig** when vehicles appear: use canon.js `rig.flavor` verbatim.

## 5.4 Location law
Panels may ONLY reference the named canon ground of Section 1.2: the 9
districts, the listed interiors, the war-map territories, the 10 world cities
and their gate/market/works/core sub-districts, and the Crown Citadel. NO
invented landmarks, no unnamed "compound", no generic skyline -- if a rooftop
is needed, it is skyline_rooftops or NEON HEIGHTS; if a tunnel is needed, it is
THE UNDERCITY or undercity_subway.

---

# 6. ISSUE RUNS (publication plan, all canon-mapped)

**Run 01 -- KINGS OF THE LOT (protectors of the block).**
The Boneguard core 12 (#0001-#0012) holding the gate of T1. Coach Diesel and
Mama Bones as recurring keepers; the Lot Warden as the run's shadow. Ends on
the first Mythic rumor: the crown that came out of the dirt.

**Run 02 -- THE CHOP-SHOP SPLIT (the brother lines).**
The variant families two-by-two: Cinderblock/Knuckles, Tombstone/Razorgums,
Rollcage/Ricochet, Firewall/Glitchfork, Casemate/Shrapnel and the rest of the
29 lines. Every issue is one family, one wound, two tellings (the
contradiction engine at full volume). Anchor: T2.

**Run 03 -- THE HANDLER FILES (the six commanders).**
Six issues, one per REAL handler: The Mender, The Tracker, The Shadow, The
Rigger, The Bruiser, The Dealer. The Dealer issue obeys the tease law: told
entirely by witnesses (Marker the Pit Boss's ledger, Goldie's trophy stories,
a face-down card) -- the reader never sees past the gold door. Home base: THE
KENNEL in THE LOT.

**Run 04 -- PIT KINGS (the Arena circuit).**
Town Hall / Arena stories: Coach Diesel's fight cards, the ladder from Stray to
King of the Block, Marker's House Limit money upstream, the Mongrel King eating
challenger names. Anchor: T5, the Block War.

**Run 05 -- MYTHS IN THE SMOKE (the 4 real Mythics).**
$BCARDD, Jagged, Rosco, Crown Foxhound -- one arc each, released
rumor-before-reveal: two issues of street testimony (Commons and keepers
talking), then the Mythic's own locked package opens. The **Crown Foxhound**
arc carries the rollout twist and the **SIGNAL AND CROWN** tie: the Signal King
is a Foxhound too -- the spymaster wired into every camera, selling secrets to
the Citadel -- and the street cannot agree whether Crown Foxhound is his hunter,
his heir, or his cover story. That contradiction IS the marketing beat.
Anchors: T3, T6.

Season alignment: each run's shipping window matches the era that carries its
figurehead (1.7) -- Run 01 in JUNKYARD DYNASTY, Run 05's Crown Foxhound issues
under BLOOD MOON, finale copy under GOLDEN LEASH.

---

# 7. FORBIDDEN LIST (invented names that must NEVER appear)

The banned strings below are broken with `//` so this bible itself greps clean.
Writers: if you type the joined form anywhere, the review fails.

| Banned (from the superseded source doc) | Why it is wrong | Canon replacement |
|---|---|---|
| `Saint//line` (as a faction) | No such crew exists; only 4 crews + Stray (raid.js) | Use the real crew. If the "saint" flavor is wanted: **The Static Saints** (Leashbreak gang), **Granite Saint** (card #0005), or **THE COLD SAINT** (act 9 boss) |
| `North//Block` (as a district) | No such district (index.html ZONES) | The northern locked district is **THE OVERLOOK** (POLICE CHECKPOINT); northern row districts are DOWNTOWN and NEON HEIGHTS |
| `Tank` as a class | Classes are the 7 in classes.js; none is called that | **BRUISER** (class) or **Vanguard** (canon.js role). Note: **Tank Pug** (#0010) is a legal CARD name only |
| `Handler//compound` (as a place) | Handlers have no compound; no such interior exists | **THE KENNEL** in **THE LOT** (index.html: the handlers' building, kept by Mama Bones) |
| `Night//of//Broken//Leashes` (as an event) | Invented event name | **EVERY LEASH BREAKS** (Act 3 title) / the T4 anchor, Rosco's chain-break at the Iron Handler's yards |
| Any 5th faction, new district, new Mythic, new era, new boss, new keeper | Closed sets, all cited in Section 1 | Pull from the CANON REGISTRY or do not write it |

---

*Mined from: canon.js, cards_lore.js, classes.js, handlers_data.js,
systems/story.js, systems/seasons.js, systems/raid.js, systems/worldmap.js,
systems/population.js, systems/karma.js, index.html, game.html (STORY_ACTS,
WORLD_CITIES). Alley Kingz / Everlight Ventures. THE BLOCK CHRONICLES.*

---

# SECTION 8 -- THE CRAFT LAWS (master-class synthesis, operator-approved 2026-07-09)
The world layer (Sections 1-7) says WHAT the stories are. This section says HOW they are told and drawn.
Synthesized from the four masters; every technique translated to OUR canon. These govern all 106 books + panels.

## 8.1 The Series Thesis (the AoT "one-sentence truth")
**ALLEY KINGZ: "Every leash breaks -- the only question is who holds the crown when it does."**
Leashes vs crowns. Control vs self-rule. It was always in the canon: leashes, collars, kennels, the handlers,
the Citadel, THE COLLAR as apex antagonist, the act literally named EVERY LEASH BREAKS.
LAW: every dog's story embodies a different facet of leash-vs-crown. The crews are four different answers to it
(Boneguard: the pack IS the crown; Zoomie: outrun the leash; Leashbreak: cut every leash on principle;
K9 Circuitry: become the system that holds the leashes). Handlers are the leash made flesh. $BCARDD is the thesis walking.

## 8.2 Architecture (AoT -- the long con)
- Plant clues chapters early. The contradiction engine IS our long con: Marker's missing ledger page,
  the Mender's kennel record vs Granite Saint's telling, the face-down card. Every contradiction seeded now
  must PAY OFF in a later issue run -- keep a PAYOFF REGISTER at the end of this bible; nothing gets seeded without a scheduled payoff.
- Moral inversion law: no crew is the good guys. Each faction wave must include at least one story that makes
  that crew's enemy sympathetic and one that indicts the crew itself.

## 8.3 Tempo (Demon Slayer -- prepare / strike / relax)
Panel-sequence law for every multi-panel beat: p1 = PREPARE (wind-up, establishing, dread),
p2 = STRIKE (the single explosive impact frame), p3 = RELAX (aftermath, lingering emotion).
- IMPACT FRAMES: the strike panel is rendered high-contrast (near-monochrome gold-on-black flash) -- prompt tag:
  "high-contrast impact frame, single explosive moment". The reader may flash-cut to it.
- COLOR-CODED EMOTION mapped to canon: Everlight gold = our dog's power/hope; each rival wears his FACTION ACCENT
  (Boneguard gold #e8c55a, Zoomie green #7CFFB0, Leashbreak purple #9d8bff, K9 blue #7fc8ff); handler/Collar scenes
  drain to cold steel-grey. The reader tints gutters/captions with these -- the eye knows who owns the moment before the brain does.

## 8.4 DNA (DBZ -- epic simplicity)
- Core emotions stay simple and universal: loyalty, hunger, grief, pride. Complexity lives in the collisions between dogs, never in convoluted plotting.
- FLAW-FIRST character law (added to every worksheet): define the dog's FLAW before his power.
  $BCARDD hides behind jokes; Granite Saint is too merciful; Knuckles mistakes fear for respect; Cinderblock carries paid debts.
- Rival-to-ally arcs are the spine of issue runs (the Vegeta law): every run should turn one enemy sympathetic.
- Death has weight: downed = INFIRMARY on-screen consequences; a story death is permanent in the fiction and never cheap.
- The power-visual arc is EARNED: a dog's coolest visual form (killstreak aura, Crown Rig) never appears in his page 1.

## 8.5 Spectacle (Marvel -- panel as camera)
- Every panelPrompt declares a CAMERA: wide establishing / sudden close-up / low-angle hero / Dutch angle dread / over-the-shoulder.
- Body language is dialogue (the Ditko law): prompts specify posture emotion ("slumped shoulders", "hackles half-risen").
- SILHOUETTE RECOGNITION test: every flagship must be identifiable from a black silhouette
  ($BCARDD: crown + cigar + chain; Granite Saint: mountain bulk + cross; Crown Foxhound: antenna collar). New designs that fail the test get redesigned.
- Splash pages are promises: ONE full-bleed splash per issue, reserved for the run's biggest beat. Never spent casually.
- Kinetic energy: action prompts carry "motion lines, kinetic pose, about to burst from the panel".

## 8.6 Page Flow (production law)
- Thumbnails first: each issue is beat-sheeted (Setup -> Complication -> Twist -> Cliffhanger) before any panel renders.
  Every issue ENDS on a reason to open the next (cliffhanger law -- the last beat of every dog's book points at another dog's book).
- Gutter = breath: reflection pages use wide gutters; action pages tighten to near-zero. The reader implements gutter width per beat mood.
- The EMOTION CHECK (QA gate): cover the text -- if the panel sequence alone does not read, the panels re-render before ship.

## 8.7 The 2026 Standard
- Authenticity over polish: keep the ink rough, the halftone visible, the compositions human. Deliberate imperfection is the house voice; sterile AI-gloss fails QA.
- Cultural fusion IS the identity: manga tempo + Marvel camera + street-noir palette. That fusion is the Alley Kingz look; guard it.
- Sustainability: complete 5-page books and 5-8 chapter issue runs that stand alone. No infinite setups. Ship whole stories.

## 8.8 PAYOFF REGISTER (living -- update every wave)
- Marker's missing ledger page (seeded: 0049/0050 collision) -> pays off in Issue Run 02 finale (who really took the purse: neither -- a handler staged it; ties to the Chop-Shop Split anchor).
- The Mender vs Granite Saint kennel record (seeded: 0005 secret) -> pays off in Issue Run 03 (the Handler Files).
- $BCARDD's face-down card (seeded: 0001 secret) -> pays off at the Crown of the Block arc climax. Do not reveal early.
- Crown Foxhound "which Foxhound does the Citadel pay" (seeded: 0037) -> pays off in Issue Run 05 (Myths in the Smoke).
- The eaten name on the rooftop wall (seeded: prologue AK_STORIES['0000'], the cold open -- the silhouette is NEVER named on-panel) -> pays off when the nemesis is finally named in the EVERY LEASH BREAKS arc (Act 3 / T4); every issue run until then may only add witnesses, never the name.
- The empty yard behind the Boneguard gate (seeded: 0002 secret vs 0001 oath -- what Stonejaw actually held for three nights) -> pays off in Issue Run 01 finale (KINGS OF THE LOT): where the stash rolled that first midnight and who cleared the yard.
- What shifted its weight inside the empty yard on night three (seeded: 0002 collision) -> pays off in the same reveal window as the eaten name (Act 3 / T4); until then, add witnesses only, never the shape.
- The name under Tombstone's chest plate (seeded: 0051 secret) -> pays off when the spine reaches THE POISON WORKS (Act 7): whether Gangrene knows it is there, and why the exile said nothing the whole way down.
- The unsent call on the quiet line (seeded: 0075 secret; contradicted by 0076 "there was no static") -> pays off when the spine reaches THE QUIET LINE (Act 5): Terminus's own jam logs from that night settle it, and indict nobody the street expects.
- Who was on the main line the night the Razor Vizsla family split (seeded: 0067/0068 contradiction) -> pays off in Issue Run 02 (one family, one wound, two tellings): the dead war camp's raid logs resurface.
- The stall that kept its chain (seeded: 0025 secret vs THE IRON HANDLER's denial) -> pays off in the EVERY LEASH BREAKS arc (Act 3 / T4): what the Iron Handler wears under the buttoned foreman's collar.
- Jagged's arrival (seeded: 0013 secret, "I was already here") -> pays off in Issue Run 05 (Myths in the Smoke): the one room on the block he has never been inside, and why.
- The race nobody lost (seeded: 0013 <-> 0021 contradiction) -> minor thread; may resolve as a NEON HOWL side page, never before the 0013 secret beat unlocks.
- The unwelded crack under Anvil's chest plate (seeded: 0053 secret; 0054 contradiction re the press-gate jacks) -> pays off in Issue Run 02, Granite Saint family issue: the day the wall's rating runs out, and what Hatchet saw when he offered the way out.
- The blank payer field on the round-two stoppage (seeded: 0055 collision/secret) -> folds into the existing Marker's-missing-ledger-page payoff (Run 02 finale / Act 8 THE HOUSE LIMIT); Bonecrusher's reassembled page is a converging witness, never the reveal itself.
- The harness under Warhorse's plate + the Iron Handler's "willing" tally (seeded: 0057 secret + contradiction) -> pays off in the EVERY LEASH BREAKS arc (Act 3 / T4), same reveal window as the Iron Handler's buttoned collar.
- Ironhide's anonymous payments through THE FENCE (seeded: 0059 secret; Sovereign contradiction "both ledgers are accurate") -> pays off when the spine reaches EVERYTHING SHIPS (Act 4): the Sovereign's rate hike and the day the heavy pup is shown both ledgers.
- Slab's throttled speed and the dented YARDS wrecks (seeded: 0061 secret; 0062 contradiction re the door-work dates) -> pays off in Issue Run 02, Rust Cane Corso family issue: the night the ROW needs the real speed in daylight.
- The ghost time on the DOWNTOWN board (seeded: 0063 secret; 0064 contradiction) -> NEON HOWL side page, never before the 0063 secret beat unlocks (mirrors the 0013/0021 rule); Nitro's alarms are the fuse.
- The missing tape from the misfire night (seeded: 0065 secret; 0066 contradiction "walls don't need INFIRMARY cots") -> pays off in Issue Run 02, Circuit Shiba family issue: what Switchblade saw, and why she stripped her own tech the same season.
- The feud that is theater (seeded: 0069 secret; 0070 contradiction "perfect attendance") -> pays off in Issue Run 02, Flash Saluki family issue: the raid ledgers surface and the Syndicate finally asks both questions at the same meeting.
- The fourth Spark Pup (seeded: 0071 secret; 0072 contradiction "taken vs left") -> pays off when THE OVERLOOK opens: the trail that turned uphill toward NEON HEIGHTS. Until then, witnesses only -- never the buyer, never the pup.
- Gridiron's sealed static recording (seeded: 0073 secret; 0076 contradiction "there was no static" now three-witnessed) -> folds into the existing quiet-line payoff (Act 5 THE QUIET LINE); witnesses only until Terminus's jam logs surface, and the recording plays only THERE.
- The Tactix asset-rating bolt order (seeded: 0079 secret; 0080 contradiction re the amended intake times) -> pays off in Issue Run 02, Holo Husky family issue: who keyed HOLD POST SEALED, and what the Mender does when the log reaches THE KENNEL.
- The one warm room off the frozen line (seeded: 0081 secret; the Cold Saint's bent patrols) -> pays off in Act 9 NOTHING STAYS FROZEN: whether the warden's blind eye was mercy or bait, settled the night the freeze breaks.
- The resonance flaw in every Tactix ward (seeded: 0083 secret) -> pays off in Issue Run 02, Prism Poodle family issue: the day someone else strikes Faraday's note, and she must confess the master key to save the shield it lives in.
- The Ghost Wire officer who commissioned the cooked intel (seeded: 0087 secret; 0088 contradiction re the off-book knock) -> pays off in Issue Run 02, Signal Pointer family issue: the open file closes, and the crew learns who writes the quiet list.
- The shrinking window and Meter's shrinking bills (seeded: 0089 secret; 0090 contradiction "phased but present") -> pays off in Issue Run 02, Ghost Spaniel family issue: what shortens the family gift, and whether Spike's windows hold.
- The loose bolt and the torch-key (seeded: 0093 secret; 0094 contradiction re the runner that never logged) -> pays off in Issue Run 02, Laser Beagle family issue: the night Bunker turns the bolt, and what The Rigger always knew he built.
- The blank-paged four-berth den order (seeded: 0095 secret; 0096 contradiction "sabotage vs signature") -> converging witness on the fourth-Spark-Pup payoff (THE OVERLOOK opening); witnesses only law holds -- an order is not a buyer, a berth is not a pup.
- The auto-clear doctrine under every K9 arc kit (seeded: 0101 secret; 0102 contradiction "the flag does not exist") -> pays off in Issue Run 02, Chrome Airedale family issue: Doc Wattson reads both kits side by side. Marker's page-buying visit is a converging witness to the missing-ledger-page payoff, never the reveal itself.
- The unplayed seal under the listening post floor (seeded: 0103 secret; 0104 contradiction "three seconds heard") -> pays off when the spine reaches SIGNAL AND CROWN (Act 6): the recording plays, the beloved K9 name is marked, and the crew's split lands exactly as Stronghold priced it.

---

# SECTION 9 -- MANGA AS GAME STATE (the 360 integration, operator-approved 2026-07-09)
Not a game with comic cutscenes: A MANGA YOU CAN PLAY. Page turns are level loads, speech bubbles are dialogue,
splash pages are boss intros, TO BE CONTINUED is the retention mechanic. The manga script is the master document;
the game, the anime shorts, and the web comic are three interpretations of it.

## 9.1 The state machine
WORLD MAP -> DISTRICT (walkable) -> BUILDING ENTRY -> MANGA PANEL -> BATTLE -> MANGA PANEL -> VICTORY/LOOT -> back to DISTRICT.
Every transition owns a panel type:
| Panel type | Function | AK integration |
|---|---|---|
| Exposition | scene/mood | tap-advance (AK_CHRONICLES page) |
| Battle Call | "FIGHT" splash | triggers the battler/raid (replaces the plain transition) |
| Impact Frame | 3-6 frame high-contrast flash | killstreaks, crits, ability ults IN combat |
| Victory | pose + loot reveal | THE loot screen IS a manga page (rewards drawn onto the panel) |
| Cliffhanger | TO BE CONTINUED | session exit hook; next-chapter tease (retention law) |

## 9.2 The Rule of Reflection (story <-> mechanics MUST mirror)
- New technique learned in a page -> the ability actually unlocks in battle.
- Betrayal in story -> that dog appears as a boss/nemesis.
- District damaged in plot -> the walkable district shows it (battle-damage overlays exist -- reuse akBldgDmg).
- Story death -> out of the roster (infirmary/permadeath fiction).
- Time skip -> base production auto-accrues (offline accrual already models this).

## 9.3 Combat as manga
- Pre-battle: enemy-intro panel with a WEAKNESS HINT (one line, real intel).
- In-battle: impact frames on killstreak tiers + Crown Nuke + crits; speed lines; SFX text drawn as art (never android font).
- Victory freeze: battlefield freezes -> page-turn INTO the victory panel; loot lands on the page like printed ink.
- RAIDS + PVP get the full grammar: raid entry = Battle Call splash for THAT rival (their crest, their accent color),
  raid victory = a takeover panel (their base burning in halftone), defense report = LAST NIGHT drawn as a news-strip page.
- BUILDER: upgrade completion = a construction panel beat (the crew raising the wall); Town Hall level-ups get a splash.

## 9.4 One asset, three formats (the pipeline law)
MASTER = the story beats + panels (data/cards_stories.js + assets/story/). Derivatives:
1. GAME: AK_CHRONICLES pages + transition/impact hooks (Canvas2D now; the same data drives Unity later).
2. ANIME SHORTS (TikTok/IG 9:16): Ken Burns pan/zoom across the SAME panels + typewriter text + music -- rides AK_VIRAL's
   9:16 recorder (record the comic page playing = an instant short). Every chapter ships a highlight-reel cut.
3. WEB MANGA: the same pages as a scrollable issue on the site (marketing surface; later).
Content calendar per chapter: 5s teaser panel, 30-60s scene cut, 15s battle-highlight (impact frames from real gameplay), BTS clip.

## 9.5 Interaction grammar (playable-comic feel)
Tap bubble = advance + emote change; swipe = page turn w/ SFX; hold = focus-zoom into a panel detail;
device shake / big hits = screen shake + speed-line intensify. Dialogue CHOICES (later phase) buff/debuff the next battle
(aggressive = rage buff vs stronger foe; tactical = weakness revealed; comedic = easter-egg reward).
MANGA VISION (later phase): a toggle filter that renders the live district in ink/halftone with speed lines.

## 9.6 Chapter structure template (each issue run chapter)
Manga intro (3-5 panels, stakes) -> world map travel -> building-entry scene -> BATTLE 1 (lane/raid) ->
transition panel (twist) -> BATTLE 2 -> victory panel (development) -> CLIFFHANGER. Every chapter ends with a reason to return.

---

# SECTION 10 -- THE LIVING MANGA (Sims + episodic choice + money-as-lore, operator-approved 2026-07-09)
The hidden key under the missions and economics: the runner is ALIVE. The manga panels change based on how you
kept him. TRANSLATION LAW (operator: "don't rename anything, merge"): every concept below maps to an EXISTING
canon system. NOTHING new is named when a canon name exists.

## 10.1 The Runner Needs (Sims DNA, canon-mapped -- 4 needs, not 8)
| Need | Canon backing | Feeds from | Danger state (gameplay) | Manga mood |
|---|---|---|---|---|
| HUNGER | NEW field p.runnerNeeds.hunger | feed with PRODUCE/CROPS (gives the farm economy a daily WHY) | starving: raid damage -25%, desperate choice options appear | panels desaturate, gaunt expression |
| ENERGY | EXISTING stamina (AK_ECON staminaState) | rest/time, bones refill | exhausted: no sprint, shaky panel lines | wobbling borders, ZZZ |
| MORALE | NEW field (social+fun merged) | Street Talk chats, arcade play, crew wins, dog barks | lonely: miss chance up, clingy/withdrawn choices | blue tint, rain overlay, small-in-frame |
| HONOR | EXISTING repRank (Block Rep) | wins, held defenses, duties | dishonored: allies hesitate, merchant prices worse | cracked borders, sinister shadow |
- Decay: slow, PT-day based (never punishing an 8h absence more than a stamina bar would). First-run safe.
- The SIMS ADVERTISEMENT ENGINE = AK_FLYWHEEL (already built): extend nextAction to weigh needs -- a hungry
  runner's thought bubble points at the BARN/garden; lonely points at Street Talk/arcade; that IS the ad system.
- Needs read/write ONLY through AK_ECON.mutateProfile lazy fields.

## 10.2 The Manga Mood Ring
Every comic/manga surface (chronicles pages, manga_fx victory pages, battle call) reads the runner's needs and
applies a MOOD COCKTAIL: thriving = bright + clean lines + gold flourishes; starving = sepia drain + gaunt;
lonely = blue + rain; enraged (combat) = red-black impact grammar; honored = gold accents + crowd background.
Implementation: AK_MANGA/chronicles accept a mood param derived by AK_NEEDS.mood(). Same beat, different art.

## 10.3 Episodic Choice (Surviving High School DNA, canon-mapped)
- EPISODES = the existing STORY_ACTS chapters + season eras. No new episode system -- chapters GET choice points.
- CHOICE PANELS in the comic reader: a beat may carry choice:{prompt, options:[{label, req?, fx}]}.
  fx = small next-battle buff/debuff (rage +dmg vs tougher spawn; tactical reveals a weakness hint; comedic = easter egg),
  or a relationship tag delta. Choices log to p.chronChoices (the cumulative-payoff rule: seeded choices pay off
  in later issue runs per the Section 8 Payoff Register).
- STATE-LOCKED CHOICES: options gate on needs (starving unlocks desperate lines, locks diplomatic; honored unlocks
  authority lines). The needs system makes the choices personal.
- BONUS SCENES: perfect-choice chapters unlock a bonus page (the replay hook).

## 10.4 Money is Lore (canon currencies ONLY -- gold/gems/bones/scrap/keys/mats)
- GOLD already = street money; GEMS already = the premium "fragments" (server-only law holds -- "only skip waits
  and buy looks, never power" is ALREADY tutorial canon); BONES already = soulbound trust (the "Bond" concept EXISTS).
- Earning/spending becomes a STORY BEAT: big earns/spends render a one-panel manga stamp (manga_fx lite) --
  "The chest was heavy. Good." Wealth/poverty tints the hub panels (rich = gold accents; broke = rough borders).
- THE SHOP IS A PLACE: THE FENCE with its keeper (canon) IS the Black Market -- purchases get a keeper line +
  ink beat. LORE-LOCKED stock: some items unlock by story progress (chapter/rep), teased with a dimmed panel line.
- ALLEY PASS = the Chronicle of Seasons: pass tiers reference that season's issue-run chapters; tier milestones
  unlock bonus PAGES (side-story panels), not just items. Pass missions get manga framing lines. The earned-premium
  loop stays server-side (gems law).

## 10.5 Tutorials follow the manga
Every new system (needs, choices, mood, Fence lore-stock, pass chapters) gets a VISITS coach entry written as
slides[] in the dog-talking style (the Wave-4 pager) -- no plain text tutorials ever again.

## 10.6 Art needs for this layer (all house-style, CF-first)
Mood overlay assets are CSS/canvas (free, no renders). New renders needed: need-state portrait variants for the
flagship runner (gaunt/lonely/enraged/thriving $BCARDD -- 4, CF), THE FENCE keeper shop beat panel (1), pass season
splash per era (reuse seasons art first). Keep the Section 8 style lock.

---

# SECTION 11 -- THE STARTER MOMENT + EPISODE APPOINTMENT (Pokemon DNA, operator-approved 2026-07-09)
Professors = OUR HANDLERS. No renames; the first five minutes become destiny.

## 11.1 The first-run flow (replaces the cold generic boot)
1. MYSTERY BEFORE CHOICE: cold-open comic sequence (chronicles pages) -- night rooftops, a massive silhouette,
   witnesses whispering. It is THE MONGREL KING ("the Dog That Eats Names", canon nemesis) -- never named on screen.
   Players piece it together across issue runs (the Section 8 payoff register gets an entry).
2. THE HANDLER CHOICE (professor moment): the player meets the handlers and PICKS ONE as their commander --
   The Mender / The Tracker / The Shadow / The Rigger / The Bruiser (The Dealer stays tease-only law: he appears
   at the edge of the panel, face out of frame). The chosen handler frames the playstyle (their existing kits)
   and becomes the tutorial voice. The handler is the authority on AWAKENING (the canon EVO/killstreak ladder).
3. THE STARTER: the handler presents THREE canon cards (class-distinct, personality-distinct -- personalities per
   Section 10 needs: the proud one loses morale on defeat; the loyal one gains dmg at high bond; the wild one
   decays hunger faster but hits harder). Starter = your first RUNNER (p.heroName set right here).
4. THE RIVAL: a pup from YOUR alley (a named population-roster dog) gets to the handler first and takes the
   COUNTER starter. Wired into the EXISTING nemesis system so the grudge tracks forever.
5. IMMEDIATE STAKES: tutorial battle vs the rival RIGHT AFTER. Win or lose, canon adapts -- lose = a limping-home
   comic page (and the infirmary intro lands emotionally, not as a menu).

## 11.2 Episode appointment (the I-Survived-High-School + Prime model) -- PHASED
- NOW (client): weekly chapter drops already exist (seasons/duties cadence); episodes = STORY_ACTS chapters with
  choice points (Section 10.3). A LIVE WINDOW banner ("THE BLOCK IS HOT: raids x2 this weekend") = live-ops flag.
- LATER (server, after ak-raid deploys): real-time PvP windows, community canon votes ("top community vote becomes
  canon" -- 60% defend = the manga shows the pack victorious), episode-dictated matchmaking. Logged as the
  multiplayer phase alongside Crew Wars.
- Premium early-access to chapters rides the EXISTING Alley Pass premium lane (gems law holds).

## 11.3 Art needs
Cold-open sequence (4-5 panels, Mongrel King silhouette -- CF, style lock), handler choice portraits (the 6 exist
as handler art -- reuse; render only if missing), 3 starter intro panels, rival intro panel, limp-home page.

---

# SECTION 12 -- THE VISUAL ASSET PIPELINE (multi-phase card art, operator-approved 2026-07-10)
One image may NOT serve every context. Every dog has SEVEN visual phases across three contexts
(Collection / Hero / Gameplay), each with its own style, spec, and name. Research base: Hearthstone
hero-skin tiers, Pokemon TCG variants, Gods Unchained layered composition, MTG art briefs.

## 12.1 The seven phases, mapped to what AK already has
| Phase | Purpose | AK status | Asset path law |
|---|---|---|---|
| 1 CARD | shop/codex stat card | HAVE (106) | assets/cards/<NNNN>_<slug>.webp |
| 2 PORTRAIT | runner picker / profile / hero select | GAP (only $BCARDD avatar) | assets/portraits/<NNNN>.jpg -- shoulders-up, dramatic, NOT the stat card |
| 3 WALK | district movement | PARTIAL (hero $BCARDD 4-dir + 3 shared bot clips + 6 class walk clips) | assets/cardfx/<NNNN>_walk.mp4 (per-dog when hero) -> class fallback |
| 4 BATTLE IDLE | combat stance | PARTIAL (cardfx idle state defined, few clips) | assets/cardfx/<NNNN>_idle.mp4 -> class fallback |
| 5 BATTLE ACTION | attack/ability | PARTIAL (engage + vs_structure per class, 0001 signature) | assets/cardfx/<NNNN>_engage.mp4 -> class |
| 6 HIT/DEFEAT | damage + down | GAP | assets/cardfx/class_<cls>_hit.mp4 (class-level first) |
| 7 VICTORY | win screen | GAP (win.mp4 is ALWAYS $BCARDD -- wrong when another dog is the runner) | per-winner: victory page uses the WINNER's art + voice; per-dog victory clips later |
- FALLBACK CHAIN LAW (already engine canon): per-dog -> per-class -> graceful static. New phases join the same chain.
- CONTEXT LAW: the stat card NEVER appears as the hero portrait or in story pages; portraits NEVER carry stat frames.

## 12.2 Style locks per phase (one voice, different registers)
CARD = the existing stat-card frame (keep). PORTRAIT = Hearthstone-hero register: dramatic rim light, personality-forward,
clean dark backdrop, house gold. WALK/IDLE/ACTION = the cardfx clip register (gritty, motion). HIT/DEFEAT = clear-feedback
impact register, dramatic never graphic; downed = INFIRMARY canon. VICTORY = celebration register in the winner's
personality (the proud dog gloats; the loyal dog stands over you protective). ALL phases obey Section 8 craft laws +
the no-humans/no-text prompt armor + each dog's canonical look from canon.js.

## 12.3 Naming + audit law
Existing paths stay (no migration). NEW assets: portraits/<NNNN>.jpg, cardfx per the chain. Every art batch starts
from the AUDIT MANIFEST (ecosystem/AK_ASSET_GAP.md, generated by script) -- never render blind, never re-render
what exists. Priority order: PORTRAITS (highest impact: the picker) -> per-winner VICTORY voice/art -> class HIT ->
walk/idle coverage -> per-dog actions (flagships first, then faction waves).

## 12.4 Generation strategy (chain of command holds)
CF flux free window = bulk panels/portraits batches. Higgsfield = flagship/Mythic pieces + motion (walk/action clips).
Soul = $BCARDD photoreal marketing only (never mixed into the ink line). Every batch: PIL verify + visual spot-check
(the human-king lesson) before ship.


## CANON RESOLUTION -- THE DOCKS (settled 2026-07-21)

This document previously claimed THE DOCKS twice, for two different factions: the crew table gave it
to **K9 Circuitry** while the district table gave it to **Leashbreak (hologhosts)**. That is an
internal contradiction in this file, not a disagreement between file and code, and it was logged as
an open item in the 2026-07-17 audit.

**RESOLVED: THE DOCKS belongs to Leashbreak / the Hologhosts, violet `#7B5CFF`.**

Tie broken on evidence, two sources to one:
  - `game/systems/karma.js:74`  ->  `THE_DOCKS: 'hologhosts'`  -- the RUNTIME source. This is what
    the live district banner and the market-tax calculation actually read, so it is what a player
    sees today. Changing the code to match a doc would visibly alter shipped behaviour; changing the
    doc to match the code changes nothing a player experiences.
  - This file's own district table (row: THE DOCKS | SE | Leashbreak (hologhosts)) already agreed.
  - Only the crew table dissented, and it has been corrected: K9 Circuitry holds NEON HEIGHTS (its
    capital) and THE OVERLOOK, which is what both the depth plan and the runtime already say.

Why this mattered enough to settle: THE DOCKS' entire ambient palette hangs off the faction, so the
Higgsfield prompts for that district could not be generated without picking a side, and regenerating
after the fact is a credit cost. Art for THE DOCKS is now unblocked -- violet `#7B5CFF`, phantom/tech.
