# Alley Kingz -- NARRATIVE CONTINUITY SPEC
*Make the game feel like ONE continuous saga, not disconnected screens. Mafia wars vibe: trying to be the top dog, we run the streets. 2026-06-30. Author: Isaac Castellano (Codex Labs). EXTENDS the existing canon, never reinvents it.*

> CANON SOURCES (read-only, this spec sits on top of them): `game/systems/story.js` (THE CROWN BLOODLINE spine, `window.AKStory`), `AK_ROADMAP_V2_NAMED.md` sec.0 (NAME CANON), `AK_STORY_MODE_DESIGN.md`, `AK_WORLD_BIBLE.md`, `game/systems/mission_active.js` (the FIXER + recruiter + escort loop), `game/index.html` (ZONES + KEEPERS + enterInterior/exitInterior).
>
> HARD RULE: use the canon names verbatim. Clans = Zoomie Syndicate / Leashbreak Tactix / Boneguard Crew / K9 Circuitry, neutral = Stray. Ranks = Stray, Pup, Runner, Warrior, Enforcer, Right Paw, King of the Block. Story = THE CROWN BLOODLINE, narrator = the OLD PACK, nemesis = the MONGREL KING (the Dog That Eats Names), apex monster = THE COLLAR (the pound / the catchers). Districts = THE LOT (HOME_TURF), DOWNTOWN, THE STRIP, NEON HEIGHTS, THE OVERLOOK, THE YARDS, FACTORY ROW, THE DOCKS, THE UNDERCITY. Market lane = THE FENCE / TRADE POST, guarding = THE WATCH.
>
> COPY RULE (in-game text): no em-dashes, no hyphen-as-dash. Plain punctuation only (periods, commas). Voice is gritty gold-cyberpunk street.

---

## 1. THE ARC (the throughline that threads through normal play)

You come up a nameless Stray on THE LOT with no collar, no crew, no name. The Old Pack (the dead-legend ancestors, our StarClan of fallen kings) deliver every objective as a dream louder than any quest popup, and the whole game is one climb: Stray to Pup to Runner to Warrior to Enforcer to Right Paw to KING OF THE BLOCK. You take the Fixer's first job, you bleed for a clan until they give you colors (Zoomie, Boneguard, Leashbreak, or K9, auto-derived from where your district karma runs deepest), you climb their respect to Trusted, you win crew wars and hold turf, you rule a whole season, then you climb the Town Hall tower and rip the crown off the Mongrel King, the Dog That Eats Names. That is the seven-chapter CROWN BLOODLINE spine already live in `story.js` (GEN_I), and near the ceiling the Old Pack reveals the twist that was always there: the real apex was never the Mongrel King, it was THE COLLAR. The pound, the catchers, the wagon that hauls strays off the block at dawn. The crown was the bait, the block was the cage.

This spec does not add a story. It makes the EXISTING story show up in the moment-to-moment loop so the player feels the saga move every session. Three threads tie the spine into normal play: (1) every mission you accept, win, and turn in fires a STORY PAYOFF that names what you just did and teases the next beat, so a turn-in is never just a loot drop, it is a plot point; (2) every building greets you on the way in and sends you off on the way out, in-voice, referencing your current chapter and clan, so doors feel like scenes; (3) every building carries its OWN ongoing chapter that deepens as you use and upgrade it, so going deeper into the FORGE or the WATCH is going deeper into the saga. The progression hook is simple: the player keeps playing to unfold the next beat, and the beats only unlock as rank and turf climb (see sec.5). The chapter gating is already non-linear in `story.js` (rank OR turf OR clan karma advances any rung), so the narrative pulls forward from whichever way the player likes to play.

---

## 2. MISSION STORY PAYOFFS (accept -> win -> payoff -> next beat)

### 2.1 The data shape

Every mission can carry an `onWinBeat`. Generated/Fixer/escort jobs that do not carry one get a beat resolved at win time by `AKStory` (sec.2.3), so NOTHING goes unacknowledged.

```js
// attached on the mission object (p.activeMissions[i].onWinBeat), all optional
onWinBeat: {
  id:        'escort_pup_homed',   // stable key, used for first-time-only beats + de-dupe
  title:     'THE OLD PACK IS WATCHING',        // chapter-card style header
  line:      "You walked the pup home...",      // the payoff narration, Old Pack / clan voice
  next:      "Next: the Boneguard owe you now. Run their blocks til they call you blood.", // teaser for the next move
  advancesChapter: true,           // after the beat, re-run AKStory.check() so a met gate can clear
  scar:      "Walked a lost pup home through Boneguard steel, never let the collar go." // -> AKStory.logDeed(scar)
}
```

Rules:
- `line` is always shown on a win. `next` is shown when present. `title` defaults to the clan name or "THE STREETS REMEMBER".
- `advancesChapter:true` means the host calls `AKStory.check()` after the beat so a chapter that just became eligible flips and its dream-vision queues next (the spine never regresses, see `story.js` monotonic `storyStage`).
- `scar` (optional) feeds the existing `AKStory.logDeed()` ledger, so the Old Pack recites how you won inside the next dream-vision (`stage().scars`). This is already wired for raids/encounters; missions join it.
- Soft acknowledgement only. The beat narrates and gates. It pays NOTHING (rewards stay on the existing turn-in path). This matches the `story.js` contract.

### 2.2 The exact hook

Fire the payoff at the SUCCESSFUL completion of a turn-in, which is also the moment of victory for `win_battle` jobs (you win the ranked scrap, walk back, turn it in).

- HOOK FUNCTION: `turnIn(mid, ctx)` in `game/systems/mission_active.js`, on the `return { ok: true, ... }` path (currently the final line of the function, after the receipt is written and `showBanner` fires).
- The Fixer sub-path routes through `turnInFixer(m, ctx)` (called from `turnIn` when `m.source === 'fixer'`); its own `return { ok: true, ... }` needs the same call.
- Minimal change: add one helper and call it from BOTH ok-true returns:

```js
function emitMissionWin(m, ctx, receipt) {
  try {
    if (!global.AKStory) return;
    var beat = m.onWinBeat || AKStory.missionPayoff(m, ctx); // resolver fills generated jobs (sec.2.3)
    if (!beat) return;
    if (beat.scar) AKStory.logDeed(beat.scar);               // append to the how-you-won ledger
    if (ctx.ui && ctx.ui.storyBeat) ctx.ui.storyBeat(beat);  // host renders the card/toast (index.html owns render)
    else if (ctx.showBanner) ctx.showBanner(beat.line, 4.2); // graceful fallback to the banner
    if (beat.advancesChapter) AKStory.check();               // let a now-eligible chapter flip
  } catch (_) {}
}
```

Call `emitMissionWin(m, ctx, receipt);` right before `return { ok: true, mission: m, ... };` in `turnIn` and again before the `return { ok: true, mission: m, receipt: receipt };` in `turnInFixer`. That is the whole wire on the mission side. Everything else is data + the host renderer.

### 2.3 The resolver (so generated jobs still get a beat)

`AKStory.missionPayoff(m, ctx)` is a NEW pure-data function on `story.js`. It reads the completed mission plus the current chapter/clan and returns an `onWinBeat`, picking by `m.source` and `m.objective.type`/`m.objective.kind`. It writes nothing. It never throws. It is the catch-all so harvest/haul/scrap/escort/Fixer jobs always land a line even when no author hand-set one.

### 2.4 Twelve written payoff beats (street / mafia voice)

These are the library `missionPayoff` draws from and that authored jobs can set directly. Keyed by trigger.

1. FIRST FIXER JOB TURNED IN (Chapter I, STRAY_AWAKENING)
   - title: `YOU GOT A NAME NOW`
   - line: `"You ran Marrow's first job clean and walked it back like you'd done it a hundred times. The Old Pack stopped circling for half a second. That half second is the whole game, pup. Nobody fed you and you ate anyway."`
   - next: `"Next: a clan is already your blood. Go work their blocks til they call you family."`
   - scar: `"Ran the Fixer's first job clean, start to finish, no crew."`

2. LOST PUP WALKED HOME (escort delivered)
   - title: `THE OLD PACK IS WATCHING`
   - line: `"You walked the lost pup home through three blocks of steel and never once let go of his collar. Word travels fast on the wire. The whole crew owes you now, and the Old Pack circled tighter tonight. They saw."`
   - next: `"Next: keep running their turf. Loyalty like that earns colors."`
   - scar: `"Walked a lost pup home through enemy steel and never let the collar go."`

3. TURF SCRAP WON (win_battle turned in)
   - title: `THAT BLOCK KNOWS YOUR TEETH NOW`
   - line: `"You won the scrap and you held the ground after. The block that flinched when you walked in flinches harder now. Respect ain't handed out on these streets. You took it, bite by bite, like the dead ones told you."`
   - next: `"Next: stack wins like this and the old heads start nodding when you pass."`
   - scar: `"Won the scrap and held the block after the bell."`

4. SUPPLY RUN / HARVEST DELIVERED FOR A CLAN
   - title: `THE CREW EATS TONIGHT`
   - line: `"You hauled the goods and the crew eats tonight because of it. Small jobs build big names. The clan marked it. That is how a stray turns into somebody."`
   - next: `"Next: keep feeding them. Trust gets built one honest haul at a time."`

5. LONG HAUL ACROSS THE MAP
   - title: `YOU MOVE WEIGHT NOW`
   - line: `"You ran that load clear across the city, past two crews that wanted it for free, and you dropped it where it belonged. People remember who can move weight without losing it. Now they remember you."`
   - next: `"Next: a name that moves weight gets offered the jobs that pay in respect."`

6. CLAN KARMA HITS NEW FACE (Chapter II, PICK_CLAN clears)
   - title: `THEY CALL YOU BY YOUR COLORS`
   - line: `"They stopped calling you the stray. You bled for these blocks and now you wear the colors. A lone dog dies in winter, the old king said. You found your pack. Don't ever make em regret claiming you."`
   - next: `"Next: colors don't make you, work does. Climb til they Trust you."`
   - advancesChapter: true

7. CLAN KARMA HITS TRUSTED (Chapter III, PROVE_YOURSELF clears)
   - title: `THE OLD HEADS NOD`
   - line: `"You climbed to Trusted and the old heads nod when you pass now. No flinch, no test, just respect. You proved it the only way the streets accept. Over and over til it was undeniable."`
   - next: `"Next: peace is for pets. The Dog That Eats Names is already counting your blocks. Win a crew war."`
   - advancesChapter: true

8. CREW WAR WON / RAID OR DEFENSE LANDED (Chapter IV, CREW_WARS)
   - title: `YOU HELD THE LINE`
   - line: `"They came for what's yours and you buried them in the concrete before the Dog That Eats Names could swallow your name whole. The blocks held. The crew rides for you now, and the rivals tell stories about the wrong dog to cross."`
   - next: `"Next: one war don't crown nobody. Rule the whole season."`
   - advancesChapter: true
   - scar: `"Held the line in a crew war and buried the ones who came for mine."`

9. SEASON PUSH BANKED (Chapter V, SEASONAL_SUPREMACY)
   - title: `AN ERA WITH YOUR NAME ON IT`
   - line: `"You ran the whole season and pushed the clan's blocks to the top of the board. An era belongs to whoever survives it. The Mongrel King has eaten every season but his own. Make this one yours, and make him remember it."`
   - next: `"Next: the season's almost up. The King is up that tower and he won't kneel."`
   - advancesChapter: true

10. THREE DISTRICTS HELD (turf gate, unlocks CREW_WARS rung)
    - title: `THREE BLOCKS FLY YOUR COLORS`
    - line: `"Three districts fly your colors at dawn now. That is real weight. Hold it. Lose it and the story stalls til you take it back, cause out here you are only as big as the ground you can keep."`
    - next: `"Next: turn three into the whole city."`
    - advancesChapter: true

11. KING BEATEN IN THE TOWER FINAL (Chapter VI, CHALLENGE_THE_KING)
    - title: `YOU MADE HIM CHOKE ON YOUR NAME`
    - line: `"You climbed the Town Hall tower and faced the Dog That Eats Names where every king before you fell. He ate names for a living. Tonight he choked on yours. The Old Pack went dead silent and made room for one more crown."`
    - next: `"Next: take what he stole from all of us. Take the crown."`
    - advancesChapter: true
    - scar: `"Climbed the tower and beat the Mongrel King in the final."`

12. CROWNED (Chapter VII, KING OF THE BLOCK)
    - title: `KING OF THE BLOCK`
    - line: `"You put the Dog That Eats Names in the dirt and pulled the crown off his skull. You are the King now, the one the strays will dream about. But the Old Pack drift their eyes past you, up to the floodlights over the pound fence. The collar was always the real teeth. Now you finally see it."`
    - next: `"Next: hold the crown. Choose an heir when you're ready and let the bloodline ride."`
    - advancesChapter: true
    - scar: `"Took the crown and became the one the strays dream about."`

---

## 3. PER-BUILDING NARRATIVE (17 buildings, each its own chapter)

Format per building: SETTING, ROLE, ENTER greetings, EXIT goodbyes, ONGOING CHAPTER. Keeper name is the existing canon keeper where one exists (from `index.html` KEEPERS / `keeperFor`); buildings marked NEW propose a keeper name as additive flavor (free text, not core canon). Voice is kept distinct per building. District control is shown so lines can reference whose turf it sits on. All copy is dash-free, plain punctuation.

### THE LOT (HOME_TURF, neutral, the seat of power)

**ARENA = TOWN HALL** (keeper: Coach Diesel)
- SETTING: the pulsing neon-crown tower at the center of the city, visible from every block, the throne you climb toward.
- ROLE: the seat of power and the stage of the whole climb. Where the Crown Bloodline begins and ends. The throne fight against the Mongrel King happens here.
- ENTER: `"Step up, champ. Crown's on the line every single night in here."` / `"The whole city can see this tower. Make em see who's standing under it."` / `"You smell that? That's the throne. Closer every time you walk in."`
- EXIT: `"Go run your blocks. The crown waits for the dog who earns it."` / `"Tower's still standing. So are you. Back to work."` / `"Next time you climb these steps, climb em higher."`
- CHAPTER: starts as a hall you visit, becomes the throne set-piece. As your rank climbs it fills with your pack and your colors; at Right Paw the Old Pack drops the COLLAR reveal here; at King of the Block it becomes your court. The tower itself is the finale arena.

**TROPHY = TROPHY HALL** (keeper: Goldie)
- SETTING: a dim gold-lit hall of belts and broken collars, every win you ever took mounted on the wall.
- ROLE: the memory of the saga. The ledger of how you won made physical. Ties to the scar ledger.
- ENTER: `"Admire the hardware. You bled for every piece on this wall."` / `"Every belt up here tells a story, and they all end with somebody on their back."` / `"Hall of kings. You keep climbing, you belong here."`
- EXIT: `"Go make me something new to hang."` / `"Empty hooks bother me. Fill em."` / `"Walls remember even when the streets forget. Go give em something."`
- CHAPTER: grows from a near-empty room into a packed hall. Surfaces the freshest scars from `AKStory.ledger()`; late game it displays the crown and the Mongrel King's broken collar.

**KENNEL = THE KENNEL** (keeper: Mama Bones)
- SETTING: a warm den behind the Lot where the bloodline is raised, straw and old blankets and a dozen sets of eyes.
- ROLE: where the pack grows and the bloodline lives. The torch-pass heir is chosen from here in spirit.
- ENTER: `"Lookin to grow the family? Come in out of the cold."` / `"My pups are the finest in this city. Raise em right."` / `"Blood means nothing til it bleeds. Pick smart."`
- EXIT: `"Keep em close. A lone dog dies in winter."` / `"Go on. Family's only family if you come back for em."` / `"Raise the next one to outlast you. That's the whole point."`
- CHAPTER: at King of the Block this is where the optional torch-pass story begins. The heir you crown (`AKStory.passTorch`) is framed as raised here.

### DOWNTOWN (Zoomie Syndicate turf, the come-up)

**DROP = THE DROP** (the shop, keeper: Scratch, NEW)
- SETTING: a glowing vendor cart on a Zoomie corner, fast deals and faster talk, gems under the counter.
- ROLE: the black-market hustle, the quick come-up. Pure street commerce.
- ENTER: `"What you in the market for, fast feet? I move quick, so should you."` / `"Zoomie blocks, Zoomie prices. Step up before the deal runs off."` / `"I got what you need and I got it now. Cash or trade?"`
- EXIT: `"Spend it on the streets, not in here. Go."` / `"You know where I'm at. Always am."` / `"Run fast, come back faster."`
- CHAPTER: as Downtown karma climbs the cart upgrades from a milk-crate stall into a neon storefront. Deals get richer as you earn Zoomie trust.

**GARAGE = THE GARAGE** (deck builder, keeper: Roxy, NEW)
- SETTING: a graffiti-tagged chop shop where the pack gets assembled and tuned.
- ROLE: where you build your crew (deck). The war room before the war.
- ENTER: `"Wanna check the crew? Pull em up, let's tune the lineup."` / `"Your deck's looking sharp. Sharper if you let me work."` / `"Pick your fighters wise. The wrong pack gets you put down."`
- EXIT: `"Roll out with the right dogs. I did my part."` / `"Crew's tuned. Now go prove it on the blocks."` / `"Come back when you outgrow this lineup. You will."`
- CHAPTER: deepens as your roster grows; late game it tracks pack-size unlocks gated by rank (Stray 3 up to King of the Block 15, per `AKStory.packCap`).

### NEON HEIGHTS (K9 Circuitry turf, the drip)

**WARD = THE WARDROBE** (drip cosmetics, keeper: Sable, NEW)
- SETTING: a glossy mirrored loft in the elite heights, holo-ads and gold trim, the look that says you made it.
- ROLE: the flex. Cosmetic identity, how the city reads your status before you say a word.
- ENTER: `"Up here the look talks first. Let's make em listen."` / `"K9 don't do plain. Neither should you now."` / `"You climbed to the Heights. Dress like it."`
- EXIT: `"Go let em see you coming. That's the point."` / `"Clean fit. Now back down to the dirt where the work is."` / `"Looking like a king is half of being one. Go earn the other half."`
- CHAPTER: unlocks deeper drip tiers as you climb the Heights; ties to season cosmetics. The reactive, dominant K9 tone.

**ARCH = THE ARCHIVE** (the Codex, keeper: Codex Keeper Vex, NEW)
- SETTING: a quiet humming vault of screens in K9 territory, every legend and every fallen king logged.
- ROLE: the lore room. Where the saga is recorded and the player can read the Crown Bloodline back.
- ENTER: `"Every king who ever fell is logged in here. You wanna read how, or write your own line?"` / `"The Archive remembers what the streets forget. Step in."` / `"Knowledge is the sharpest fang. Sharpen up."`
- EXIT: `"Your chapter's still being written. Go write it."` / `"The dead are watching the record. Make yours worth keeping."` / `"Come back when you've done something worth logging."`
- CHAPTER: surfaces unlocked Crown Bloodline chapter cards and the collar reveal as readable entries. Deepens as the player advances the spine.

### THE YARDS (Boneguard Crew turf, scrap and walls)

**CLAN = CREW YARD** (crews / chat, keeper: Roxy, NEW)
- SETTING: a fenced lot of shipping crates and barrel fires where the crews meet and talk.
- ROLE: the social heart. Where crew bonds, alliances, and the running-with-the-crew co-op live.
- ENTER: `"Crews talk in here. Who you rolling with tonight?"` / `"Boneguard built these walls. You wanna stand behind em, earn it."` / `"A lone dog dies in winter. This is where you stop being lone."`
- EXIT: `"Roll out with the crew. You ride harder together."` / `"Your pack's only as tight as you keep it. Go keep it."` / `"Walls hold cause the crew holds. Don't be the weak brick."`
- CHAPTER: grows from a quiet lot to a fortified yard as your clan karma and alliances climb. The calm, immovable Boneguard grit.

**PASS = PASS HOUSE** (Alley Pass, keeper: Tallyman Burr, NEW)
- SETTING: a clipboard-and-cash-box shack at the Yards gate where the season's track gets stamped.
- ROLE: the seasonal engine. Where the season story and rewards are tracked. Feeds SEASONAL_SUPREMACY.
- ENTER: `"Season's running, dog. You on the track or sitting it out?"` / `"Every stamp on this card is a block you ran. Let's add some."` / `"An era belongs to whoever survives it. You surviving?"`
- EXIT: `"Go stack stamps. The season don't wait."` / `"Board resets when the era ends. Climb before it does."` / `"Make the whole city flinch when your name drops. That's the season."`
- CHAPTER: tied directly to season marks/streak (the SEASONAL_SUPREMACY gate). Deepens each season; late game it tracks prestige legacy.

**FIXER = THE FIXER** (Hit List, keeper: Marrow the Fixer)
- SETTING: a back-room wire desk lit by one bulb, jobs coming in faster than a dog can run em.
- ROLE: the job engine, the origin of the whole climb. The first job and every job after. Already wired to `mission_active.js`.
- ENTER: `"Got work on the wire. You want it or you want to stay a nobody?"` / `"Marrow don't deal with amateurs. Prove you ain't one."` / `"Every king on these streets started taking my jobs. Now move."`
- EXIT: `"Squared up. There's always more on the wire. Come back."` / `"Run it clean and the bigger jobs find you."` / `"You did good. Don't let it go to your head. Next one's harder."`
- CHAPTER: the Fixer is Chapter I's launchpad and stays the steady job source; the jobs escalate in stakes and pay as rank climbs. The Hit List is where accept happens, the turn-in is where the payoff (sec.2) fires.

### FACTORY ROW (Boneguard Crew turf, the forge)

**GEM = GEM MINE** (production: gems, keeper: Prospector Pip)
- SETTING: a slick wet shaft cut into the factory bedrock, headlamps and the clink of pick on stone.
- ROLE: a producer. The grind that funds the climb.
- ENTER: `"Gems don't mine themselves, partner. Grab a light."` / `"Rich veins today. Haul while it's hot."` / `"Careful in the shaft, it's slick. The greedy ones slip."`
- EXIT: `"Take your haul and go. Veins'll be here tomorrow."` / `"Good dig. Spend it smart, not fast."` / `"Back to the surface. The streets pay better than the stone, eventually."`
- CHAPTER: upgrading the mine raises its rate and cap (real numbers via `production.js`); narratively the deeper you dig the more Boneguard backs your operation.

**MINT = GOLD MINT** (production: gold, the FENCE / TRADE POST, keeper: Banker Bones)
- SETTING: a barred counter stacked with coin, a scale, and a fence who launders raided goods clean.
- ROLE: the money lane and THE FENCE. Where gold is made and stolen goods get washed before they spend.
- ENTER: `"Gold's good here, and so's whatever fell off the back of a truck. What you need washed?"` / `"The mint never sleeps, friend. Neither do your debts."` / `"Count it twice. That's how you stay breathing in this business."`
- EXIT: `"Come back when your pockets are heavier. Or lighter. I work both."` / `"Money moves or money dies. Go move it."` / `"You know where the gold lives. Don't be a stranger."`
- CHAPTER: the Fence grows from a back-counter into a real laundering operation as your economy scales; raided/looted goods route through here per the FENCE canon.

**FORGE = CARD FORGE** (production: cards, keeper: Sparks)
- SETTING: a roaring anvil shop in the heart of Factory Row, sparks and the smell of hot metal.
- ROLE: a producer and the maker of legends. Where scrap becomes the pack.
- ENTER: `"Forge is lit. Let's make something that bites."` / `"Bring me scraps, I'll bring the heat. Every legend starts on this anvil."` / `"You want a fighter or a memory? I make both. Pick."`
- EXIT: `"Take it to the streets and don't shame the work."` / `"Anvil's still hot. Come back with more scrap."` / `"What you forge here decides what you become out there. Go become it."`
- CHAPTER: deepens with upgrades; the forge is where rare and legendary cards are tempered, framed as the Boneguard putting their steel behind your rise.

### THE STRIP (Zoomie Syndicate turf, lights and fights)

**STREET = THE STREET** (street mode, keeper: Hollywood, NEW)
- SETTING: a casino-strip block buzzing with neon and quick money, street fights in the alley behind the lights.
- ROLE: the fast-action lane. Where you run street mode and live out the come-up energy.
- ENTER: `"Strip's alive tonight, fast feet. You here to run or to watch?"` / `"Lights, money, fights. The Zoomie way. Step in."` / `"Easy money's a lie out here, but the action's real. Let's go."`
- EXIT: `"Run the Strip dry and come back tomorrow. It refills."` / `"Lights don't sleep. Neither should a dog on the come-up."` / `"Go fast. Slow dogs get left under these lights."`
- CHAPTER: the Strip stays the high-energy quick loop; as Zoomie karma climbs the action and stakes rise. The excitable ride-or-die tone.

**ARCADE = THE ARCADE** (mini-games, keeper: Pixel, NEW)
- SETTING: a flickering arcade tucked off the Strip, cabinets named BONE DIG, ALLEY DASH, WHACK-A-STRAY, VEIN STRIKE, CARD TEMPER.
- ROLE: the crew-training cabinets. Skill over spend. Where the pack sharpens between wars.
- ENTER: `"Cabinets are warm. Train the crew or just kill time, your call."` / `"High score sharpens a real fang in here, dog. Play to win."` / `"BONE DIG, ALLEY DASH, the lot. Pick your poison."`
- EXIT: `"Sharper than you walked in. Go use it."` / `"Scores reset weekly. Come defend yours."` / `"Training's free. Losing on the streets ain't. Come back."`
- CHAPTER: cabinets map to pack-role stats; high scores permanently sharpen a role. Weekly leaderboards give it an ongoing rivalry beat.

### THE DOCKS (Leashbreak Tactix turf, phantom tech)

**LAB = RESEARCH LAB** (production: skill points, keeper: Doc Wattson)
- SETTING: a half-flooded dock lab humming with salvaged tech and phantom-blue light.
- ROLE: a producer and the upgrade brain. Where skill points and the tech edge come from.
- ENTER: `"Science waits for no dog. Pick your upgrades."` / `"The skill tree's blooming. Come look before the Leashbreak ghosts spook you off."` / `"Knowledge is the sharpest fang. Let me sharpen yours."`
- EXIT: `"Go apply it. Theory dies on the streets without practice."` / `"The tree keeps growing. So should you. Back later."` / `"Smarter than you walked in. The Docks reward that."`
- CHAPTER: deepens with the skill tree; the aloof Leashbreak ghosts back your research as you earn Docks trust. Late game unlocks the tech that wins crew wars.

**GEN = THE GENERATOR** (production: power, keeper: Volt)
- SETTING: a thrumming dock powerhouse of cables and caged lightning, the juice that runs every other rig.
- ROLE: a producer. The power that feeds the whole operation. No juice, no muscle.
- ENTER: `"Keep the power flowing. Everything else dies without it."` / `"No juice, no muscle. Simple as that. Top her up."` / `"She's humming sweet today. Don't let her go quiet."`
- EXIT: `"Power's up. Go burn it on something worth the watts."` / `"Keep her fed and she keeps you running. Back soon."` / `"Lights stay on cause you came through. Now go."`
- CHAPTER: upgrades raise output; narratively the Generator is the lifeline that lets you hold turf during the WATCH and crew wars.

### LOCKED DISTRICTS (story teases, not buildings)
- THE OVERLOOK (POLICE CHECKPOINT) and THE UNDERCITY (COLLAPSED BRIDGE) are barriers, not enterable buildings. THE OVERLOOK is the on-ramp to THE COLLAR reveal: the checkpoint is the pound's hand on the city. Surface a one-line tease at the barrier near Right Paw ("That checkpoint ain't police, pup. That's the catchers. The real teeth.") so the apex monster is felt before it is named.

---

## 4. WIRING NOTES (for the implementer)

What is pure text/data (FREE, can do now, no art, no spend):
1. `mission_active.js`: add `emitMissionWin(m, ctx, receipt)` (sec.2.2) and call it from the two `ok:true` returns in `turnIn` and `turnInFixer`. ~12 lines, self-contained, try/catch wrapped, no engine touch.
2. `story.js`: add the beat library (sec.2.4) + `missionPayoff(m, ctx)` resolver (sec.2.3) + a `BUILDING_LINES` table (sec.3, enter/exit per building id) + `buildingLine(buildingId, kind, ctx)` returning a chapter-and-clan-flavored line. Export both on `window.AKStory`. All pure data + reads, writes nothing except via the existing `logDeed`/`check` paths, stays headless byte-identical (follow the existing module contract in `story.js`).
3. `index.html` enterInterior(b) (around line 820-847): after the keeper greeting is set (the `int-line` text at line 827, and after `applyGreeter` at line 846), if `window.AKStory`, OVERLAY the story-flavored enter line via `AKStory.buildingLine(b.id, 'enter', AK_CTX)` (append below the keeper line or alternate it in). Free text.
4. `index.html` exitInterior() (line 849): currently shows NO goodbye. Add a send-off before hiding the panel: `if (window.AKStory && window.showBanner) showBanner(AKStory.buildingLine(b.id, 'exit', AK_CTX), 2.4);` using the saved `interiorB` (`b`) reference before it is nulled at line 851. Free text.
5. Host renderer `ctx.ui.storyBeat(beat)` (the card the mission payoff shows). If you do not want a new full-screen card yet, the `emitMissionWin` fallback already degrades to `showBanner(beat.line)`, so step 1 ships value with ZERO new UI. The card is a nice-to-have upgrade, still free (DOM only), reuse the chapter-card styling pattern already in `story.js` CARD_META consumers.

What needs ART (FLAG: needs the art pipeline + a token, do NOT assume it exists):
- Per-building interior backdrops that SHIFT with turf control (prosperous when your clan holds the district, decayed when contested), per `AK_ROADMAP_V2_NAMED.md` sec.1. The enter/exit TEXT works on the current static PNGs now; the mood-shift art is a later pass.
- Keeper portraits for the NEW keepers proposed in sec.3 (DROP/Scratch already heuristic-named, GARAGE/Roxy, WARD/Sable, ARCH/Vex, PASS/Burr, STREET/Hollywood, ARCADE/Pixel). Until painted, the existing glyph fallback in `setKeeperPortrait` covers them (no breakage).
- Any new story-beat chapter-card backdrop beyond the reused `assets/hub/*.png` set already used by `story.js`.
- Art generation routes through the art_factory queue and requires `CF_AI_TOKEN` (per workspace memory `feedback_art_autoroute_no_generic`). Flagging it: art is BLOCKED until that token is available. The text/data layer (steps 1 to 5) is NOT blocked and delivers the continuity feel on its own.

Provenance / no-contradiction check: the spine, clans, ranks, Old Pack, Mongrel King, and COLLAR all come straight from `story.js` GEN_I + CARD_META + COLLAR and `AK_ROADMAP_V2_NAMED.md` sec.0. The payoff beats reuse the exact dream-vision language already in `story.js` so the new turn-in beats and the existing HUD visions speak in one voice. Nothing here regresses `storyStage`, pays currency, or edits the frozen engine.

---

## 5. PROGRESSION TABLE (story gates with play)

| Chapter (story.js id) | Unlocks at (rank OR turf OR clan, non-linear per `gateMet`) | Where it lives (district / building) | Beat that fires (sec.2.4) |
|---|---|---|---|
| I STRAY_AWAKENING | Game start (Stray). Clears on first Fixer turn-in / first trophies / first capture | THE LOT + THE FIXER (THE YARDS) | Beat 1 (first Fixer job) |
| II PICK_CLAN | Pup (200) OR 1 district OR clan New Face | Your clan's home district (Downtown/Heights/Yards/Docks) + CREW YARD | Beat 6 (colors) |
| III PROVE_YOURSELF | Runner to Warrior OR clan Trusted (karma idx 3) | Deeper into clan turf + CREW YARD / TROPHY HALL | Beat 7 (old heads nod) |
| IV CREW_WARS | HARD gate: hold 3 districts (Warrior+). Re-locks if turf drops below 3 | Contested FACTORY ROW / THE DOCKS, THE WATCH defense | Beat 8 (held the line) + Beat 10 (3 blocks) |
| V SEASONAL_SUPREMACY | Enforcer (1800) OR season marks/streak (PASS HOUSE) | PASS HOUSE (THE YARDS), all open districts | Beat 9 (an era) |
| VI CHALLENGE_THE_KING | Right Paw (3000). THE COLLAR reveal fires here (or at Right Paw rank) | TOWN HALL tower; THE OVERLOOK barrier tease | Beat 11 (made him choke) |
| VII CROWNED | King of the Block (5000 trophies) OR season-final force-crown | TOWN HALL throne; unlocks KENNEL torch-pass | Beat 12 (King of the Block) |
| GEN II/III (optional) | Post-Crowned torch-pass (`passTorch`) | KENNEL (heir raised) | data stubs in `story.js` GEN_II/GEN_III |

Building chapters deepen on a parallel track tied to USE/UPGRADE, not just rank: producers (GEM/MINT/FORGE/LAB/GEN) deepen as you raise their level via `production.js`; the social/season/job buildings (CREW YARD, PASS HOUSE, THE FIXER) deepen as the matching chapter gate is met; the FENCE (MINT) and THE WATCH (guard) deepen as your held turf grows. Going deeper into a building is going deeper into the saga.

---

*End of spec. Implementation order: ship sec.4 steps 1 to 4 first (pure text/data, free, delivers the continuity feel today), add the `storyBeat` card (step 5) next, queue the mood-shift art + new keeper portraits behind `CF_AI_TOKEN` last.*
