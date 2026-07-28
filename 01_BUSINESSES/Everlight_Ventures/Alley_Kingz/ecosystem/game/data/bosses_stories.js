/* AK-BOSSES: Alley Kingz BOSS chronicles -- THE CROWN'S CEILINGS data layer.
   ============================================================================
   The 106 dog books (data/cards_stories.js) tell the STREET from below. This
   sidecar tells it from ABOVE: full legend profiles + 5-beat origin stories for
   the bosses who stand between a stray and the crown. Same self-registering IIFE
   + STYLE-var contract as cards_stories.js -- pure DATA, headless-safe, no engine
   edits, window/globalThis guarded, load-order independent.

   CANON SOURCES (zero invented proper nouns -- every name/place already exists):
     - game.html STORY_ACTS[0..9] -- the 10-act campaign bosses (intro/clear text)
     - systems/story.js -- THE MONGREL KING "the Dog That Eats Names" (nemesis)
       and THE COLLAR (apex antagonist: the pound / the catchers / the wagon --
       the human system the Mongrel King only ever SERVED)
     - AK_BLOCK_CHRONICLES_BIBLE.md 1.6 (the boss table) + 1.7 (season eras)
     - data/cards_stories.js relationshipTags -- every boss note here EXTENDS an
       existing dog-book reference (never contradicts it); tiedDogBooks lists the
       card numbers whose books already name the boss.

   MASTER ROSTER = 12 bosses (AK_BOSS_ROSTER, full manifest below):
     Acts 1-10 city bosses: THE LOT WARDEN, METER THE NEON RUNNER, THE IRON
     HANDLER, THE DOCK SOVEREIGN, TERMINUS THE STATION KING, THE SIGNAL KING,
     GANGRENE THE PLAGUE WARDEN, MARKER THE PIT BOSS, THE COLD SAINT, THE REGENT;
     plus the two story-layer apex antagonists: THE MONGREL KING and THE COLLAR.

   THIS FILE profiles ALL 12 bosses. The FIRST HALF (the 7 climb-ceilings, Acts
   1-7) and the SECOND HALF (Marker Act 8, the Cold Saint Act 9, the Regent Act
   10, plus the two story-layer apex antagonists -- THE MONGREL KING and THE
   COLLAR) all carry full 5-beat books below. Every ROSTER entry is 'PROFILED'.
   The Mongrel King's TRUE FACE is never named or shown -- he wears the names he
   ate, none his own. THE COLLAR is the human system (pound / catchers / wagon)
   and is drawn ONLY as apparatus, never a human on panel (STYLE law).

   VOICE: third-person legend narration + a signature first-person line per boss
   (signatureLine), one first-person boss quote woven into every beat. Gritty gold
   cyberpunk dog-gang street culture, matched to the bible tone + the dog-book web.

   NO em-dashes anywhere in this file (hook law); use -- instead.
   ============================================================================ */
(function (global) {
  'use strict';

  // Global style lock (bible 5.2) -- prepended to every panel prompt.
  // Mirrors data/cards_stories.js STYLE byte for byte.
  var STYLE = "gritty gold-cyberpunk noir comic panel, heavy inks, halftone shadow, hard rim light, Everlight gold accent #e8c55a against ink-black #06060a, wet asphalt reflections, anthropomorphic street dogs, no humans on panel";

  /* ---- MASTER ROSTER MANIFEST -- all 12 bosses. status: 'PROFILED' = full
     profile + 5-beat book in BOSSES below. Every entry is PROFILED (both halves
     complete); the manifest stays so the master list is discoverable. -------- */
  var ROSTER = [
    { key: 'LOT_WARDEN',     codename: 'THE LOT WARDEN',        act: 1,  city: 'the_lot',           source: 'game.html STORY_ACTS[0]', status: 'PROFILED' },
    { key: 'METER',          codename: 'METER, THE NEON RUNNER', act: 2, city: 'neon_night',        source: 'game.html STORY_ACTS[1]', status: 'PROFILED' },
    { key: 'IRON_HANDLER',   codename: 'THE IRON HANDLER',      act: 3,  city: 'golden_industrial',  source: 'game.html STORY_ACTS[2]', status: 'PROFILED' },
    { key: 'DOCK_SOVEREIGN', codename: 'THE DOCK SOVEREIGN',    act: 4,  city: 'rain_docks',         source: 'game.html STORY_ACTS[3]', status: 'PROFILED' },
    { key: 'TERMINUS',       codename: 'TERMINUS, THE STATION KING', act: 5, city: 'undercity_subway', source: 'game.html STORY_ACTS[4]', status: 'PROFILED' },
    { key: 'SIGNAL_KING',    codename: 'THE SIGNAL KING',       act: 6,  city: 'skyline_rooftops',   source: 'game.html STORY_ACTS[5]', status: 'PROFILED' },
    { key: 'GANGRENE',       codename: 'GANGRENE, THE PLAGUE WARDEN', act: 7, city: 'toxic_sewers',  source: 'game.html STORY_ACTS[6]', status: 'PROFILED' },
    { key: 'MARKER',         codename: 'MARKER, THE PIT BOSS',  act: 8,  city: 'casino_strip',       source: 'game.html STORY_ACTS[7]', status: 'PROFILED' },
    { key: 'COLD_SAINT',     codename: 'THE COLD SAINT',        act: 9,  city: 'frost_district',     source: 'game.html STORY_ACTS[8]', status: 'PROFILED' },
    { key: 'REGENT',         codename: 'THE REGENT',            act: 10, city: 'crown_citadel',      source: 'game.html STORY_ACTS[9]', status: 'PROFILED' },
    { key: 'MONGREL_KING',   codename: 'THE MONGREL KING',      act: null, city: null,               source: 'systems/story.js (nemesis, "the Dog That Eats Names")', status: 'PROFILED' },
    { key: 'THE_COLLAR',     codename: 'THE COLLAR',            act: null, city: null,               source: 'systems/story.js COLLAR (apex antagonist)', status: 'PROFILED' }
  ];

  /* ======================================================================== *
   * THE BOSSES -- all 12, full profiles. FIRST HALF: the 7 climb-ceilings,
   * Acts 1-7. SECOND HALF (further down): Marker (8), the Cold Saint (9), the
   * Regent (10), and the two apex antagonists -- the Mongrel King + the Collar.
   * ======================================================================== */
  var BOSSES = {

    /* ================================================================
       ACT 1 -- BORN IN THE DIRT -- THE LOT WARDEN (Bullmastiff, the_lot)
       The first tax on the block. Extends 0001/0002/0005/0010/0011/0012.
       ================================================================ */
    LOT_WARDEN: {
      codename: "THE LOT WARDEN",
      title: "Scarred old Bullmastiff who taxes every stray in the yard",
      faction: "Boneguard dirt (THE LOT)",
      turf: "THE LOT",
      metadata: {
        act: 1, actTitle: "BORN IN THE DIRT", city: "the_lot",
        breed: "Bullmastiff", role: "Level-10 city boss",
        clanTurf: "Boneguard Crew", overlord: "THE REGENT",
        timelineTags: ["T1_JUNKYARD_DYNASTY"],
        themes: ["the first tax", "guarding vs billing", "dirt makes kings"]
      },
      publicHook: "Everything whelped in this dirt owes the Lot. Even you.",
      coreWound: "He held THE LOT so long he forgot the difference between guarding dirt and taxing it. The yard stopped being his to protect and became his to bill, and a wall that only counts coin quits watching the gate.",
      coreDrive: "Keep the ledger balanced. Every stray weighed at birth, every breath priced, nothing crossing the yard without the Lot's cut.",
      profile: "The oldest tax on the block, a grey-muzzled Bullmastiff who has stood the Boneguard dirt since before the current strays were whelped and wrote each of them into the ledger on their first night. He rules THE LOT by making the small pay first and pay quiet, because the small never argue and never remember they could refuse. His flaw is the flaw of old walls: he taxes the dirt instead of watching it, and the pup he under-priced grew up out of the very ground he was too busy billing to guard.",
      signatureLine: "Everything in this yard pays the Lot. I wrote your number the night you were born.",
      beats: [
        { key: "origin",
          text: "Before the Boneguard had a name, before the Crew held the gate, there was a young Bullmastiff who stood between the strays and the wagon and asked for nothing. The block called it protection then. \"I kept them fed and I kept them counted,\" he says, \"and one night I noticed the counting was the only part anybody ever thanked me for.\" The dirt made him. Then it paid him, and he learned to prefer the second thing.",
          panelPrompt: STYLE + ", young grey Bullmastiff standing guard between huddled strays and a distant wagon in THE LOT, chain-link and stacked dead cars, Boneguard gold #e8c55a collar tag, drifting embers of the JUNKYARD DYNASTY era, wagon headlights far down the fence line" },
        { key: "rise",
          text: "He turned a favor into a fee and a fee into a floor no stray could get under. Every litter whelped in THE LOT was weighed, numbered, and written into the tax book on its first night. \"Weigh them early,\" he told the collectors. \"They pay quiet when they've never known a night off the ledger.\" By the time the Boneguard Crew rose around him, he was already the oldest debt on the block.",
          panelPrompt: STYLE + ", grey Bullmastiff hunched over a heavy ledger in THE LOT, rows of numbered tags hanging like a curtain, a line of small dogs waiting to be weighed, Boneguard gold #e8c55a rim light, rust #C9772E scrap piles" },
        { key: "rule",
          text: "He taxes the small first, because the small pay quiet, and the big he simply outlasts. Nothing crosses THE LOT dirt without leaving a coin in the Lot's book, and the book has never once shown a debt forgiven. \"Show me a stray who says he owes the Lot nothing,\" he grins, \"and I'll show you a stray who hasn't been weighed yet.\"",
          panelPrompt: STYLE + ", scarred old Bullmastiff enthroned on a heap of scrap and dead cars in THE LOT, tax-tags strung like a curtain behind him, Boneguard gold #e8c55a glow, TOWN HALL dark on the horizon, halftone shadow" },
        { key: "wound",
          text: "The trouble with taxing dirt is you stop watching it. He priced a white-coated pup low, the way you price anything you expect the yard to bury by winter, filed the number, and forgot the dog. \"The small pay quiet,\" he had always said. He never heard the one who decided to stop paying at all.",
          panelPrompt: STYLE + ", Dutch angle, old Bullmastiff squinting at a low number circled in the ledger, an unseen white Dogo Argentino silhouette rising out of the scrap behind him, wagon lights sweeping the fence, gold #e8c55a on his set jaw, dread in the negative space" },
        { key: "reckoning",
          text: "When the crown finally came for THE LOT, it came up out of the same dirt he had been billing, and the yard he taxed instead of guarded did not stand with him. He falls the way old walls fall: not shoved, just no longer propped. \"You came up out of my ground,\" he says at the end, almost proud. \"I should have watched it instead of counting it.\" The Lot raised the king. Tonight it learned his name.",
          panelPrompt: STYLE + ", white Dogo Argentino standing over the toppled old Bullmastiff in THE LOT's dirt center, ledger pages blowing across wet asphalt, strays no longer kneeling, Boneguard gold #e8c55a dawn breaking over stacked dead cars" }
      ],
      relationToPlayer: "He is the crown's first ceiling: the block's founding lie that where you are whelped is where you die owing. Take the Lot and you prove the ledger was never law, just an old dog's habit. Leave it standing and every rung above it still carries your birth-number.",
      tiedDogBooks: ["0001", "0002", "0005", "0010", "0011", "0012"],
      portrait: "assets/bosses/lot_warden.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The oldest tax on the block plants himself in the gate, ledger open across both paws. \"You owe the Lot before you cross it,\" he says. \"I wrote your number the night you were born.\"" },
          { key: "taunt", text: "The strays behind him have never once seen the book forgive a debt. \"Everything whelped in this dirt pays me first,\" he grins. \"Especially the ones who came up out of it.\"" }
        ],
        choice: {
          prompt: "The Lot Warden blocks the gate with the ledger. How do you settle the account?",
          options: [
            { label: "Skip the Book", line: "You knock the ledger out of his paws before he can read a number off it. No more weighing, old dog -- I came to close the account with teeth. The yard's oldest wall has never once been rushed.", fx: "rage", tone: "defiant" },
            { label: "Read the Ledger", line: "You point to your own birth-line, the low number he priced to die by winter. Check your own math -- you undercounted the dog standing in your gate. The column he trusted for years turns cold in his paws.", fx: "tactical", tone: "calculating" },
            { label: "Ask Who He Guarded", line: "You ask him to name one stray he ever protected instead of billed. He opens his mouth and nothing comes out. That silence is the whole reckoning -- he quit guarding the dirt the day counting it paid better.", fx: "easter", tone: "needling" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 2 -- ALL TEETH, NO MERCY -- METER, THE NEON RUNNER
       (Greyhound, neon_night / DOWNTOWN, Zoomie Syndicate lanes)
       Extends 0013/0014/0016/0021/0022/0023/0033/0063/0064/0067/0068/0089/0090.
       ================================================================ */
    METER: {
      codename: "METER, THE NEON RUNNER",
      title: "Greyhound fixer who owns every lane and bills by the second",
      faction: "Zoomie Syndicate lanes",
      turf: "DOWNTOWN / THE STRIP lanes",
      metadata: {
        act: 2, actTitle: "ALL TEETH, NO MERCY", city: "neon_night",
        breed: "Greyhound", role: "Level-10 city boss",
        clanTurf: "Zoomie Syndicate", overlord: "THE REGENT",
        timelineTags: ["T2_NEON_HOWL"],
        themes: ["billing by the second", "speed without loyalty", "renting your own legs"]
      },
      publicHook: "I bill this city by the second. You're already behind.",
      coreWound: "Meter has never lost a race because he has never run one fair. He clocks every runner and credits none, so the fastest dog in the city has never once found out if he is actually fast -- only that he is owed.",
      coreDrive: "Keep the clock running and keep it his. Sign young legs before they know their worth, bill the lanes by the second, and make sure no straight line ever runs for free.",
      profile: "The Greyhound fixer who owns the DOWNTOWN lanes and rents them back to the dogs who run them, billing THE STRIP by the second and signing young legs to the circuit before they have paid for anything. He rules the Zoomie Syndicate's asphalt not by being faster but by owning the stopwatch, and he clocks the runners while never crediting the dog who set their pace. His flaw is that speed without loyalty is just running away in style: the moment his own runners would rather watch than chase, the fastest dog in the city has nowhere left to run to.",
      signatureLine: "I bill this city by the second, and nobody has ever run me a fair one.",
      beats: [
        { key: "origin",
          text: "He was the actual fastest thing on the lanes once, a young Greyhound who never lost. Then he learned the bet was worth more than the win. \"I quit racing the day I figured out the clock pays better than the finish line,\" he says. He never ran another honest race, and he never had to.",
          panelPrompt: STYLE + ", young lean Greyhound mid-stride on a DOWNTOWN lane, magenta #FF2E88 and Zoomie green #7CFFB0 neon streaking off wet asphalt, a stopwatch glinting in the foreground shadow, speed lines etched into the halftone" },
        { key: "rise",
          text: "He bought the stopwatch, then the lanes, then the young legs themselves. He signs pups to the circuit before they have paid for anything and clocks them for the privilege. \"Sign the legs young,\" he tells the collectors. \"A dog who never learned his own price will run yours forever.\"",
          panelPrompt: STYLE + ", sleek Greyhound at a lit STRIP toll lane, contracts spread on a neon podium, young runners lined up in the glow, Zoomie green #7CFFB0 accents, magenta #FF2E88 reflections, no humans on panel" },
        { key: "rule",
          text: "He bills the city by the second and has never lost a race, because he has never run one. The lanes owe him even when they are empty. \"Show me a straight line,\" he says, \"and I'll show you a dog who thinks he owes nothing by the hour. Wait.\"",
          panelPrompt: STYLE + ", lean electric Greyhound silhouette standing over a glowing grid of DOWNTOWN lanes, running meters and timers everywhere, magenta #FF2E88 and green #7CFFB0 neon, ink-black shadow, wet asphalt reflections" },
        { key: "wound",
          text: "The rot is the crediting. He clocks the runners and never once names the dog who set their pace, so his whole circuit is dogs who never found out they were fast, only that they were billed. When a Lot stray with a body count came up his lanes, the runners he had never credited stood aside to watch. \"Speed without loyalty,\" the Old Pack whispers, \"is just running away in style.\"",
          panelPrompt: STYLE + ", Greyhound glancing back over his shoulder as a line of Zoomie runners stand dead still refusing to chase, neon flicker, magenta #FF2E88 and green #7CFFB0, one white stray silhouette gaining in the distance" },
        { key: "reckoning",
          text: "His own Syndicate runners step aside, and a stray catches the dog who has never been caught. \"I clocked everybody on this block,\" he says, watching the finish line come to him, \"but the one who came to clock me.\" Downtown clocks everything. It just clocked him losing.",
          panelPrompt: STYLE + ", white Dogo Argentino crossing a glowing finish line over a fallen Greyhound on a DOWNTOWN lane, Zoomie runners watching from the shoulder, magenta #FF2E88 and green #7CFFB0 neon, wet asphalt, gold #e8c55a rim light" }
      ],
      relationToPlayer: "He owns the second ceiling: the lie that you must rent your own speed from the dog with the stopwatch. Beat him and the lanes run free, and the runners he never credited finally find out what they are worth. Leave him and the fastest dog in the city keeps paying by the second to move his own legs.",
      tiedDogBooks: ["0013", "0014", "0016", "0021", "0022", "0023", "0033", "0063", "0064", "0067", "0068", "0089", "0090"],
      portrait: "assets/bosses/meter.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The neon runner clicks his stopwatch and the whole lane lights up under your paws. \"Clock's already on you, dog,\" he says. \"I bill this city by the second and you're behind.\"" },
          { key: "taunt", text: "He has never lost a race because he has never run one fair. \"Sign the lane or run it,\" he shrugs. \"Either way the meter's mine and the second is already spent.\"" }
        ],
        choice: {
          prompt: "Meter meters the lane before you can move. How do you run it?",
          options: [
            { label: "Break the Clock", line: "You go for the stopwatch instead of the finish line. I'm not racing your lane -- I'm coming for the hand that holds the watch. The one thing Meter never armored, because nobody ever aimed there.", fx: "rage", tone: "blunt" },
            { label: "Run It Honest", line: "You call the fastest dog in the city out onto a fair line for once. Let's find out if you're actually quick or just the dog who owns the clock. He stalls -- he has spent his whole reign never needing to know.", fx: "tactical", tone: "baiting" },
            { label: "Tip the Runners", line: "You turn to the young legs he signed and never once credited. He clocked all of you and named none -- watch me run one for free. They step off the lane to watch, and Meter loses the only thing he ever really owned.", fx: "easter", tone: "rallying" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 3 -- EVERY LEASH BREAKS -- THE IRON HANDLER
       (Australian Cattle Dog, golden_industrial, Leashbreak Tactix grudge)
       Extends 0007/0025/0026/0054/0057/0058/0078/0097/0098 -- the buttoned
       foreman's collar secret + the "pulled willing" tally + collar-off-signature.
       ================================================================ */
    IRON_HANDLER: {
      codename: "THE IRON HANDLER",
      title: "Cattle Dog foreman who keeps half the district collared and calls it order",
      faction: "golden_industrial yards",
      turf: "golden_industrial container yards",
      metadata: {
        act: 3, actTitle: "EVERY LEASH BREAKS", city: "golden_industrial",
        breed: "Australian Cattle Dog", role: "Level-10 city boss",
        clanTurf: "Leashbreak Tactix (grudge)", overlord: "THE REGENT / THE COLLAR",
        timelineTags: ["T3_CROWN_CITADEL"],
        themes: ["the leash that holds the handler", "quota as order", "chains are temporary"]
      },
      publicHook: "Order is a leash somebody's holding. Guess whose.",
      coreWound: "He learned leash-craft in the same yards Rosco chewed out of and never forgave the Leashbreak Tactix for proving chains are temporary. What he cannot say aloud is the thing buttoned under his own foreman's collar: a handler is just a dog on a longer leash.",
      coreDrive: "Keep the district signed, tallied, and collared. Every dog a number in the quota book, every load pulled 'willing,' every fork of every family collared off one captured signature.",
      profile: "A blue Australian Cattle Dog foreman who runs the golden_industrial yards on leashes and quotas and calls the whole grinding thing order. He rules by the tally: a signature column that swears every collared dog pulled willing, and one captured signature is enough to collar an entire line, though he has learned the hard way that he cannot collar a fork that was never signed. His flaw is buttoned under his own collar. He came up in the same chains the Leashbreak Tactix did, and he has never forgiven them for proving a chain can break, because it means his can too.",
      signatureLine: "Nobody pulls unwilling in my yard. I keep a column that proves it -- I wrote every name in it myself.",
      beats: [
        { key: "origin",
          text: "He was whelped a yard dog and collared young, and where another pup would have chewed at the chain he studied it. \"They put me on a leash,\" he says, \"and I learned the leash better than the dog holding it. Then I asked to hold it.\" These were the same yards Rosco chewed out of. The Handler chose the other end.",
          panelPrompt: STYLE + ", young blue Australian Cattle Dog studying a chain in a golden_industrial container yard, amber #E2B23A work light, stacked containers like a giant's dominoes, rust #C9772E steel, a leash coiled in the foreground" },
        { key: "rise",
          text: "He turned leash-craft into a district. He built the tally, the quota, the signature column, and collared whole lines off one captured signature. \"Sign one and you've signed the blood,\" he says. \"A family is just a leash with more ends.\"",
          panelPrompt: STYLE + ", Cattle Dog foreman before a quota board with a signature column, collared dogs hauling containers in rows, golden_industrial amber #E2B23A light, gold #e8c55a trim, chain-link everywhere" },
        { key: "rule",
          text: "He keeps half the district collared and calls it order, and every load in his yard is pulled willing because the tally says so. \"Nobody pulls unwilling in my yard,\" he tells any dog who asks. \"Read the column. I keep the column.\" The top button of his foreman's collar stays buttoned, always.",
          panelPrompt: STYLE + ", buttoned foreman's collar on a stern Cattle Dog overseeing leashed dogs in the golden_industrial yard, quota tallies pinned to the wall, amber #E2B23A and gold #e8c55a, ink-black shadow behind the container stacks" },
        { key: "wound",
          text: "The Tactix are the wound. He rose from the same chains they did, and where they chewed free he asked to hold the leash instead, and he has never forgiven them for proving the chain could break. Buttoned under his own foreman's collar, where no dog in the yard has ever seen it, is a collar. \"A handler is just a dog on a longer leash\" is the one sentence he will not let the yard hear him think.",
          panelPrompt: STYLE + ", intimate close camera, the Cattle Dog alone at night, the top button of his foreman's collar straining over a hint of metal underneath, Leashbreak purple #9d8bff ghosting at the yard edge, amber #E2B23A lamp, dread in the negative space" },
        { key: "reckoning",
          text: "He falls the moment the collared choose to be uncollared in front of him. His own leashed dogs watch the crown fight free, and the yard goes off the chain. \"You cut yours in front of mine,\" he says, and for once his voice is not a foreman's. \"Now I have to feel mine.\" Every leash in the yard got two feet shorter. The crown's got cut.",
          panelPrompt: STYLE + ", leashed dogs dropping their chains all at once in the golden_industrial yard, the Iron Handler's own hidden collar exposed at last, a white stray breaking free at the center, Leashbreak purple #9d8bff and Boneguard gold #e8c55a, sparks off the chain-link" }
      ],
      relationToPlayer: "He is the crown's third ceiling and the first to name the real monster by accident: the collar. Beat him and the district learns chains are temporary. Leave him and every dog stays a signature in a book held by a dog who is himself on a leash he pretends not to feel.",
      tiedDogBooks: ["0007", "0025", "0026", "0054", "0057", "0058", "0078", "0097", "0098"],
      portrait: "assets/bosses/iron_handler.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The foreman taps the quota board, the top button of his collar done up tight. \"Everything in my yard pulls willing,\" he says. \"It's in the column. I wrote every name in it myself.\"" },
          { key: "taunt", text: "He came up in the same chains he now holds and never forgave the dogs who chewed free. \"Order is a leash somebody's holding,\" he says flatly. \"In here that's me. Pick a line and pull it.\"" }
        ],
        choice: {
          prompt: "The Iron Handler puts you on the tally. Which line are you on?",
          options: [
            { label: "Off the Chain", line: "You snap the nearest leash clean in his face and drop it in the dirt. Write this into your column, foreman -- unwilling. The yard has never once heard the word said out loud, and neither has he.", fx: "rage", tone: "raw" },
            { label: "Burn the Page", line: "One captured signature collars a whole line, so you tear out the page he signed you onto. No name, no leash, no line to pull. He reaches for a tally that is suddenly missing its most useful lie.", fx: "tactical", tone: "surgical" },
            { label: "Name His Collar", line: "You nod at the top button no dog in the yard has ever seen him undo. A handler is just a dog on a longer leash -- go on, tell the yard I'm wrong. For once his voice drops all the way out of foreman.", fx: "easter", tone: "quiet" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 4 -- EVERYTHING SHIPS -- THE DOCK SOVEREIGN
       (Golden Retriever quartermaster, rain_docks, K9 Circuitry buyers)
       Extends 0008/0038/0041/0059/0060/0095/0096/0099/0100 -- rescue-as-debt,
       price is never gold (one unsigned job), never touches his own cargo.
       ================================================================ */
    DOCK_SOVEREIGN: {
      codename: "THE DOCK SOVEREIGN",
      title: "Retriever quartermaster with a manifest for everything and a price for everyone",
      faction: "rain_docks (THE DOCKS)",
      turf: "rain_docks / THE DOCKS",
      metadata: {
        act: 4, actTitle: "EVERYTHING SHIPS", city: "rain_docks",
        breed: "Golden Retriever", role: "Level-10 city boss",
        buyers: "K9 Circuitry", overlord: "THE REGENT",
        timelineTags: ["T3_CROWN_CITADEL"],
        themes: ["rescue as a debt", "the price is never gold", "never touch your own cargo"]
      },
      publicHook: "Everything ships. Everything has a price. Yours is on page nine.",
      coreWound: "Five drones shadow him like gulls, and he has never once touched his own cargo. He turned even rescue into a ledger line, so a dog he saved is not saved, he is a debtor, and one of those debts has been accruing for years.",
      coreDrive: "Move the city's iron, take the cut in obedience, and price everything -- especially the things that were never supposed to be for sale, like a saved life or an unsigned job.",
      profile: "A golden Retriever quartermaster who moves the city's iron across the rain_docks and takes his cut in obedience, five drones shadowing him like gulls and a manifest for every crate that crosses the water. He rules by the book: every rescue on the docks has a price entered in the Sovereign's ledger, and the price is never gold, it is an unsigned job, a name, a debt that accrues in the dark. His flaw is that he has never once touched his own cargo, so when the audit finally comes in teeth he does not know his own iron well enough to turn it back on the dog cracking his crates.",
      signatureLine: "Everything ships. I priced your rescue the day I made it, and it has been accruing ever since.",
      beats: [
        { key: "origin",
          text: "He learned early that the city runs on what moves through the docks, and whoever writes the manifest owns the city without ever lifting a crate. \"I never carried a thing in my life,\" he says. \"I carry the book. The book carries everything else.\" A Retriever who chose the ledger over the load.",
          panelPrompt: STYLE + ", young golden Retriever with a clipboard-manifest at the edge of the rain_docks, cranes swinging cargo through the rain, teal #00E0C0 and gold #e8c55a neon smeared on wet planks, a crate humming faintly, no humans on panel" },
        { key: "rise",
          text: "He turned the manifest into a throne. He knew what wintered in which shed and charged for the knowing, and he named his price for a rescue exactly once, to a dog's face, and it was not gold. \"Gold is for dogs who don't understand leverage,\" he says. \"I take names. I take favors owed. I take the one job you swore you'd never sign.\"",
          panelPrompt: STYLE + ", golden Retriever behind glass over the rain_docks, five drones hovering like gulls, ledger screens glowing, stacked crates in the rain, K9 blue #7fc8ff buyers in shadow, teal #00E0C0 accents" },
        { key: "rule",
          text: "He has a price for everyone. The K9 Circuitry buy from him and nobody ever said they liked him, and every rescue on his water is a debt with his name at the bottom. \"You think I saved you?\" he says. \"I invoiced you. Check page nine.\"",
          panelPrompt: STYLE + ", stern golden Retriever quartermaster at a manifest desk on the rain_docks, five drones like gulls above him, crates humming with something not yet awake, teal #00E0C0 and gold #e8c55a, rain on the planks" },
        { key: "wound",
          text: "He has never once touched his own cargo. He knows the price of every crate and the weight of none, so when the debts he has been accruing come due all at once, he cannot lift his own iron to defend it. \"I have a manifest for everything,\" he admits, \"and I have never once needed to know what a crate feels like. That was the luxury. Turns out it was the flaw.\"",
          panelPrompt: STYLE + ", golden Retriever reaching uncertainly for a crate he does not know how to open on the rain_docks, drones scattering upward, an audit closing in from the water's edge, teal #00E0C0 low, gold #e8c55a rim light, rain" },
        { key: "reckoning",
          text: "The audit comes in teeth. The crown cracks his crates, turns his own iron on him, and the Circuitry quietly update their shipping address. \"Everything ships,\" he says, watching his own cargo roll over him. \"I never learned to carry it. You did.\" The docks move everything out of this city. Tonight they moved him.",
          panelPrompt: STYLE + ", crates bursting open on the rain_docks, iron and cargo turned back on the fallen Sovereign, K9 Circuitry logistics rerouting away in the background, teal #00E0C0 and gold #e8c55a, wet planks, drones fleeing" }
      ],
      relationToPlayer: "He owns the fourth ceiling: the lie that even your rescue is a debt somebody holds. Beat him and the docks move free. Leave him and every kindness on the water stays a line accruing in a book you were never allowed to read.",
      tiedDogBooks: ["0008", "0038", "0041", "0059", "0060", "0095", "0096", "0099", "0100"],
      portrait: "assets/bosses/dock_sovereign.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The quartermaster checks his manifest without looking up, five drones hanging over him like gulls. \"Everything ships and everything has a price,\" he says. \"Yours is on page nine.\"" },
          { key: "taunt", text: "He has never once touched his own cargo in his life. \"I priced your rescue the day I made it,\" he says. \"It has been accruing ever since. Come settle it.\"" }
        ],
        choice: {
          prompt: "The Dock Sovereign puts your rescue on the ledger. How do you pay it?",
          options: [
            { label: "Crack the Crates", line: "You pop the seals on his own iron, the cargo he prices but never carries. You never touched a crate in your life -- let me show you what one weighs. His drones scatter upward and his manifest cannot lift a thing to stop you.", fx: "rage", tone: "brute" },
            { label: "Audit the Book", line: "You call for the debt that has been accruing in the dark for years and read it into the open. Every rescue in your ledger is a leash -- so let's total mine out loud, page nine and all. He turns pages he has never had to defend.", fx: "tactical", tone: "precise" },
            { label: "Tear Out Page Nine", line: "You tell him plainly you were never saved, only invoiced, and you are not signing. The Sovereign has a line for every debtor except the one who simply refuses the bill. Everything ships, but not this.", fx: "easter", tone: "dry" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 5 -- THE QUIET LINE -- TERMINUS, THE STATION KING
       (Basenji, undercity_subway, jams every call for help)
       Extends 0015/0018/0020/0069/0070/0072/0073/0074/0075/0076 -- the
       "silence that either ate a call or never had to" + the kinship question.
       ================================================================ */
    TERMINUS: {
      codename: "TERMINUS, THE STATION KING",
      title: "Barkless Basenji who rules the undercity by jamming every call for help",
      faction: "the quiet line (undercity_subway)",
      turf: "undercity_subway / the quiet line",
      metadata: {
        act: 5, actTitle: "THE QUIET LINE", city: "undercity_subway",
        breed: "Basenji", role: "Level-10 city boss",
        overlord: "THE REGENT",
        timelineTags: ["T3_CROWN_CITADEL"],
        themes: ["silence as a kingdom", "the call that went unanswered", "silence runs both ways"]
      },
      publicHook: "You called for help. The line was already mine.",
      coreWound: "A barkless dog who made silence a kingdom. Dogs go into his tunnels and nobody hears what happens, but silence runs both ways, and the same jammed network that swallows every cry for help cannot warn him when the cry is coming for him.",
      coreDrive: "Keep the quiet line quiet. Move dogs through the stations, answer nowhere they go, and jam every signal until the undercity forgets that help was ever a sound it could make.",
      profile: "A barkless Basenji who rules the undercity_subway by owning its silence, running quiet cargo down the line under the Regent's nose and jamming every signal and call for help until the tunnels forget the sound. He runs the DOWNTOWN stations on a timetable and does not answer where the dogs he moves go, and the block cannot even agree whether he jammed THE call the night it went unanswered or whether that call never had anywhere to connect. His flaw is that silence runs both ways: the network that eats every warning also eats his own.",
      signatureLine: "I don't bark. I don't have to. Down here the quiet answers to me -- and the quiet never warned a soul I was coming.",
      beats: [
        { key: "origin",
          text: "He was a barkless pup in a city that only respects a loud dog, and he learned the tunnels held a thing louder than any bark: the absence of one. \"The block never heard me,\" he says, in the way a Basenji says anything, which is not with sound. \"So I took the one place hearing goes to die.\"",
          panelPrompt: STYLE + ", a lean barkless Basenji alone in a flickering undercity_subway tunnel, grimy tile, dead tube light, a silhouette dwarfed by the dark mouth of the line, cold cyan glow, ink-black shadow swallowing the platform edge" },
        { key: "rise",
          text: "He jammed the first signal as a favor, then as a fee, then as a kingdom. He learned the quiet line ran under everything and answered to no timetable but his. \"A jammed call isn't a call anymore,\" he says. \"It's just a dog finding out, alone, that nobody's coming.\"",
          panelPrompt: STYLE + ", Basenji at a jamming rig in an undercity_subway maintenance bay, signal bars going dead across a board, tunnels darkening in sequence, cold blue static, ink-black, no humans on panel" },
        { key: "rule",
          text: "He rules the undercity by jamming every call for help, and dogs go into his tunnels and nobody hears what happens. The street cannot agree whether he jammed THE call or whether it never connected, and he lets both stories stand, because the not-answering is its own answer. \"Did I jam the call that went unanswered?\" he lets the block ask. \"They're still asking. That's the only answer I sell.\"",
          panelPrompt: STYLE + ", barkless Basenji standing on an undercity_subway platform, one unanswered signal blinking on a dead board, quiet cargo crates behind him, ink-black tunnels, cold flickering tube light, wet tile reflections" },
        { key: "wound",
          text: "Silence runs both ways. The same network that swallows every cry cannot make a sound when the crown's crew comes down the line, so the king of the quiet is the last dog to hear his own kingdom fall. There is a second barkless Basenji on the block, and the street keeps asking if they are kin, and his refusal to answer that is the one silence he cannot rule. \"I jammed the whole city's help,\" he says. \"I forgot to leave one line open for my own.\"",
          panelPrompt: STYLE + ", the Basenji turning a beat too late on a dark undercity_subway platform, his own signal board unable to warn him, a crew's shadows already flooding the far end of the rail, cold blue light, dread in the negative space" },
        { key: "reckoning",
          text: "His jammed network cannot warn him the crown is already on the platform. The undercity finally hears something, and it is the station king hitting the rail. \"The quiet line,\" he signs, no bark left in him, \"ran under everything but me.\"",
          panelPrompt: STYLE + ", a crew emerging from the tunnels onto an undercity_subway platform, Terminus down on the rail, the signal board flickering back to life above him, cold cyan and gold #e8c55a rim light, wet tile" }
      ],
      relationToPlayer: "He owns the fifth ceiling: the lie that no help is coming and no cry connects. Beat him and the undercity can call out again. Leave him and every dog who goes into the dark finds out alone that the line was already his.",
      tiedDogBooks: ["0015", "0018", "0020", "0069", "0070", "0072", "0073", "0074", "0075", "0076"],
      portrait: "assets/bosses/terminus.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The station king signs from the dead platform, no bark, the signal board black behind him. \"Down here the quiet answers to me,\" he says without a sound. \"Call for help. See who comes.\"" },
          { key: "taunt", text: "Dogs go into his tunnels and nobody ever hears what happens. \"I jammed the whole city's cry for help,\" he signs. \"The line was already mine before you reached for it.\"" }
        ],
        choice: {
          prompt: "Terminus owns the silence on the line. How do you come at him?",
          options: [
            { label: "Come In Loud", line: "You charge the platform howling straight into the jam. You eat quiet cries, station king -- choke on a loud one. The undercity has not heard a sound this size since the night the call went unanswered.", fx: "rage", tone: "eruptive" },
            { label: "Kill the Jammer", line: "You go for the rig and not the dog, because silence runs both ways and his network cannot warn him either. The board flickers back to life -- the first open signal down here in years, and it is counting his steps now, not yours.", fx: "tactical", tone: "methodical" },
            { label: "Ask If He's Kin", line: "You nod toward the second barkless Basenji the block keeps whispering about. They still ask if you two are blood -- that's the one silence you can't jam. He turns a beat too late, and the beat is the whole tell.", fx: "easter", tone: "probing" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 6 -- SIGNAL AND CROWN -- THE SIGNAL KING
       (Foxhound spymaster, skyline_rooftops, sells to the Citadel)
       Extends the Beacon Basset line (0044/0103/0106) sealed-tape/three-seconds/
       the name, plus 24 books total; owns every camera above, nothing below.
       ================================================================ */
    SIGNAL_KING: {
      codename: "THE SIGNAL KING",
      title: "Foxhound spymaster wired into every camera and beacon, selling secrets to the Citadel",
      faction: "the beacon network (skyline_rooftops)",
      turf: "skyline_rooftops / the relay towers",
      metadata: {
        act: 6, actTitle: "SIGNAL AND CROWN", city: "skyline_rooftops",
        breed: "Foxhound", role: "Level-10 city boss",
        buyers: "the Citadel", overlord: "THE REGENT / the Citadel",
        timelineTags: ["T3_CROWN_CITADEL"],
        themes: ["a city of cameras", "the one blind spot", "the secret he never sold"]
      },
      publicHook: "I sell every secret but my own. Smile -- you're already on the network.",
      coreWound: "Royalty pays him to hunt royalty's problems, and he owns every camera above ground. But he owns nothing under it, and the one secret he never sold -- a name he caught on a sealed recording, three clean seconds of it -- is the one that owns him.",
      coreDrive: "See everything, sell everything, owe nothing. Wire the whole skyline into a network that marks every dog on the block, and rent the point of it to whoever on the throne pays.",
      profile: "A lean Foxhound spymaster wired into every camera and beacon on the skyline_rooftops, selling the block's secrets up to the Citadel and hunting royalty's problems for royalty's coin. He rules a city of cameras, an empire of installed structures that each bill double, and he has been watching the crown since THE LOT, which he mistakes for knowing it. His flaw is his blind spot: he owns every camera above ground and owns nothing under it, and when his own beacon network is finally turned to mark HIM, the only place left unwatched is the roof he is standing on.",
      signatureLine: "I've got a thousand cameras and one blind spot. Right now I'm standing on it.",
      beats: [
        { key: "origin",
          text: "He was a Foxhound who learned the block's real currency was never teeth or gold but the thing a dog does when he thinks no one is looking. He wired the first camera himself. \"Everybody's got a secret,\" he says. \"I just built the city that films it.\"",
          panelPrompt: STYLE + ", a young lean Foxhound mounting the first camera on a skyline_rooftops antenna, Citadel gold #e8c55a light low on the horizon, K9 blue #7fc8ff cabling, the city laid out below like a debt, velvet-dark ink shadows" },
        { key: "rise",
          text: "He turned the skyline into a network, every camera and beacon an installed structure that bills double, all of it rented up to the Citadel. He caught a sealed recording once, a ranked voice, a manifest, a name, three clean seconds of it, and for a reason even he will not name, he never sold it. \"I sell every secret on this block,\" he says. \"Every one but the one I keep sealed. A king needs one card he'd never play.\"",
          panelPrompt: STYLE + ", a sleek Foxhound enthroned among a wall of glowing camera feeds on skyline_rooftops, a beacon array behind him, K9 blue #7fc8ff cabling, one sealed recording glowing gold #e8c55a on the console, empty streets on every monitor" },
        { key: "rule",
          text: "He owns every camera above ground, and royalty pays him to hunt royalty's problems. His open contracts on rival craft are the politest threats on the block. \"Royalty pays me to hunt royalty's problems,\" he says. \"I never told them the biggest problem royalty's got is how much I've already filmed.\"",
          panelPrompt: STYLE + ", lean Foxhound overlooking the NeonReach skyline from skyline_rooftops, monitors of empty streets except one pure blur of motion, Citadel gold #e8c55a on the horizon, K9 blue #7fc8ff glow, camera on a pole turning" },
        { key: "wound",
          text: "He owns everything above ground and nothing beneath it, and the sealed name he never played sits under the block where no camera of his can reach. The crown learns this: take the relay towers one by one and the all-seeing dog goes blind from the ground up. \"I built a city that sees everything,\" he says, \"on a foundation I never once looked at.\"",
          panelPrompt: STYLE + ", a Foxhound watching his own camera feeds cut to static one by one, a sealed recording glowing in an underground corner no lens covers, crimson BLOOD MOON over skyline_rooftops, K9 blue #7fc8ff faltering, dread in the dark below" },
        { key: "reckoning",
          text: "His own beacon network marks HIM. The crown takes the relay towers until the only blind spot left is the roof he stands on, and the sealed name finally surfaces from under the block. \"Smile,\" he says, as his own network turns on him. \"You're on the only camera I forgot to own.\" The city's eyes are under new management.",
          panelPrompt: STYLE + ", relay towers going dark in sequence across skyline_rooftops, a lean Foxhound alone on the last lit rooftop, marked by a beam from his own beacon, crimson and gold #e8c55a sky, the Citadel towers cold behind him" }
      ],
      relationToPlayer: "He owns the sixth ceiling: the lie that you are already known, already filmed, already owned by whoever rents the point. Beat him and the city's eyes change hands. Leave him and every secret on the block, including the sealed name he never played, stays his to sell up to the throne.",
      tiedDogBooks: ["0024", "0027", "0031", "0032", "0034", "0035", "0037", "0044", "0045", "0046", "0047", "0048", "0066", "0077", "0083", "0084", "0086", "0087", "0088", "0099", "0103", "0104", "0105", "0106"],
      portrait: "assets/bosses/signal_king.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The spymaster sits inside a wall of glowing feeds, every camera on the skyline his. \"Smile,\" he says. \"You've been on my network since THE LOT. I sell every secret but my own.\"" },
          { key: "taunt", text: "He owns every lens above ground and mistakes watching the crown for knowing it. \"A thousand cameras and one card I'd never play,\" he says. \"Come see if you can make me play it.\"" }
        ],
        choice: {
          prompt: "The Signal King has watched you climb the whole ladder. How do you play him?",
          options: [
            { label: "Take the Towers", line: "You rush the relay array he built his empire on top of. You see everything above ground -- I'm coming up from under it. The feeds start cutting to static one by one as the all-seeing dog goes blind from the ground up.", fx: "rage", tone: "charging" },
            { label: "Find the Blind Spot", line: "You step onto the one patch his own network never covers, the tar roof under his paws. A thousand cameras, one blind spot, and you're standing on it. He looks down and finds there is no lens on the only ground that matters now.", fx: "tactical", tone: "knowing" },
            { label: "Play the Sealed Card", line: "You name the one recording he caught and never sold -- three clean seconds, a ranked voice, a name. Want the whole block to hear the card you kept sealed? For the first time the dog who films everyone does not want to be on the record.", fx: "easter", tone: "bluff-calling" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 7 -- THE POISON WORKS -- GANGRENE, THE PLAGUE WARDEN
       (Rottweiler exile, toxic_sewers, Boneguard-bred, refused the poison)
       Extends 0004/0029/0036/0051/0052/0079/0080 -- "the healing trade that
       chooses who to spend" + Tombstone walked him to the sewer gate.
       ================================================================ */
    GANGRENE: {
      codename: "GANGRENE, THE PLAGUE WARDEN",
      title: "Boneguard-bred Rottweiler exile who rules the poison works and decides which wounds are worth the medicine",
      faction: "the poison works (toxic_sewers)",
      turf: "toxic_sewers / the poison works",
      metadata: {
        act: 7, actTitle: "THE POISON WORKS", city: "toxic_sewers",
        breed: "Rottweiler", role: "Level-10 city boss",
        originClan: "Boneguard Crew (exiled)", overlord: "THE REGENT (defied)",
        timelineTags: ["T1_JUNKYARD_DYNASTY", "T3_CROWN_CITADEL"],
        themes: ["the crown's dark twin", "who to save vs who to spend", "pain made him cruel"]
      },
      publicHook: "Down here I decide which wounds are worth the medicine. Hold still.",
      coreWound: "Boneguard-bred and sentenced to the Regent's poison, he refused to die of it and built a kingdom out of the dogs the city threw away. Pain made him strong the way it makes the Boneguard strong, but it made him cruel, and he crossed the line from choosing who to save to choosing who to spend.",
      coreDrive: "Rule the discarded. Turn the healing trade inside out -- ration the medicine, price the gauze, and decide in the green dark who is worth saving and who is only worth spending.",
      profile: "A Rottweiler exile, Boneguard-bred, whom the Regent sentenced to the poison works and who refused to flush away with the rest of the district's failures. He rules the toxic_sewers as a warden of the discarded, a kingdom built from dogs the city threw away, and the same pain that made him strong made him the proof of what the healing trade becomes when it stops choosing who to save and starts choosing who to spend. His flaw is the crown's mirror: the player learned the same hunger down in THE LOT and stayed sane, so Gangrene fights the one dog who knows exactly what he could have been and refused to become.",
      signatureLine: "Same yards, same scrap, same sentence as you. I just decided which wounds were worth the medicine -- and down here I still do.",
      beats: [
        { key: "origin",
          text: "He was Boneguard-bred, walked to the sewer gate by Tombstone and left there under the Regent's poison sentence. He was supposed to rot. \"They flushed me down here to die with the rest of the district's failures,\" he says. \"I looked at the failures. I saw a crew.\"",
          panelPrompt: STYLE + ", a Rottweiler at the mouth of the toxic_sewers under a poison sentence, sickly green #7FE3A0 glow, dripping pipes, a huge Boneguard Legendary silhouette turning away at the sewer gate behind him, rust #C9772E iron, ink-black" },
        { key: "rise",
          text: "He built a kingdom out of the thrown-away. Pain made him strong the Boneguard way, and he turned the healing trade inside out, rationing the medicine, deciding which wounds were worth it. \"The healers ask who they can save,\" he says. \"I asked a better question. Who's worth spending.\"",
          panelPrompt: STYLE + ", a Rottweiler warden over a court of discarded dogs in the toxic_sewers, a green #7FE3A0 healing totem glow doled out unevenly, dripping pipes, air that bites back, gold #e8c55a rim light cutting the green" },
        { key: "rule",
          text: "He is the boss who decides which wounds are worth the medicine. He bills the Iron line in rot and reopens what the healers stitch shut. \"Every crew's got a Mender who chooses who to save,\" he says. \"I'm the Warden who chooses who to spend. Same paw. I just don't lie about it.\"",
          panelPrompt: STYLE + ", Gangrene handing medicine to one wounded dog and turning coldly from another in the toxic_sewers, green #7FE3A0 totem light, rot and iron, halftone shadow, sickly glow on the wet pipes" },
        { key: "wound",
          text: "Pain made him strong and it made him cruel, and he can no longer tell the two apart. Then a stray came down out of THE LOT carrying the exact same hunger he did, and had stayed sane. \"You came up the way I did,\" he says. \"Same dirt. Same starving. You just never let it decide who to spend. I hate that you're proof I could have.\"",
          panelPrompt: STYLE + ", a Rottweiler facing a white Lot stray across the green dark of the toxic_sewers, the same hunger in both faces, one gone cruel and one not, green #7FE3A0 and gold #e8c55a, mirror composition, dread in the negative space" },
        { key: "reckoning",
          text: "He falls because the crown learned the same hunger in THE LOT and stayed sane. \"I decided who was worth the medicine down here for years,\" he says. \"Nobody ever came down worth deciding against me.\" You walked into the city's poison, and the poison blinked.",
          panelPrompt: STYLE + ", Gangrene toppled in the green poison works, the discarded dogs rising behind a white Dogo Argentino stray, toxic_sewers, gold #e8c55a dawn light cutting through the sickly green #7FE3A0, wet pipes dripping" }
      ],
      relationToPlayer: "He is the crown's dark twin, the seventh ceiling and the last one that is a warning instead of a wall. Beat him and the discarded get to choose their own worth. Become him and the crown is just another warden deciding who to spend.",
      tiedDogBooks: ["0004", "0029", "0036", "0051", "0052", "0079", "0080"],
      portrait: "assets/bosses/gangrene.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The plague warden wipes green off his paws in the poison works. \"Same yards, same scrap, same sentence as you,\" he says. \"I just decided which wounds were worth the medicine.\"" },
          { key: "taunt", text: "Pain made him strong the Boneguard way and then it made him cruel. \"Down here I still choose who to save and who to spend,\" he says. \"Hold still and I'll price yours.\"" }
        ],
        choice: {
          prompt: "Gangrene decides which wounds get the medicine. What's your call?",
          options: [
            { label: "Spill the Medicine", line: "You wreck the rationing totem and let the cure run to every wounded dog at once. Nobody decides who's worth spending down here -- not even the one who survived the sentence. The green dark has never seen the medicine given free.", fx: "rage", tone: "furious" },
            { label: "Turn His Court", line: "You point to the discarded dogs standing behind you, the crew he built from the ones the city threw away. You taught them they were worth spending -- watch them un-build you. His own kingdom shifts to your shoulder in the poison light.", fx: "tactical", tone: "cold" },
            { label: "Show Him the Mirror", line: "You tell him quietly you came up the exact same starving and never once let it pick who to spend. You hate that I'm proof you could have stayed sane. The court goes silent, and so, for a breath, does the warden.", fx: "easter", tone: "level" }
          ]
        }
      }
    },

    /* ======================================================================== *
     * THE BOSSES -- SECOND HALF. Acts 8-10 climb-ceilings + the two apex
     * antagonists. Same shape, same laws, same web-coherence as the first half.
     * ======================================================================== */

    /* ================================================================
       ACT 8 -- THE HOUSE LIMIT -- MARKER, THE PIT BOSS
       (silver-muzzled Afghan Hound, velvet collar, casino_strip)
       Extends 0003/0011/0043/0049/0050/0055/0056/0062/0085/0101/0102 --
       the split-night ledger, the missing page, the blank payer field, the
       velvet-collar dog who collects dogs and never raised a paw.
       ================================================================ */
    MARKER: {
      codename: "MARKER, THE PIT BOSS",
      title: "Silver-muzzled Afghan Hound in a velvet collar who never raised a paw and owns every marker on the row",
      faction: "THE HOUSE LIMIT (casino_strip)",
      turf: "casino_strip / THE STRIP row",
      metadata: {
        act: 8, actTitle: "THE HOUSE LIMIT", city: "casino_strip",
        breed: "Afghan Hound", role: "Level-10 city boss",
        house: "THE HOUSE LIMIT", overlord: "THE REGENT",
        timelineTags: ["T3_CROWN_CITADEL", "T5_BLOCK_WAR"],
        themes: ["the house always wins", "an open account is a leash", "he collects dogs not gold"]
      },
      publicHook: "The house always wins. Sign here. You already did.",
      coreWound: "He never raised a paw in his life, so he has never once found out whether he could take a thing instead of pricing it. Everything he holds, he holds on paper, and paper only holds a dog who believes the number. He collects dogs and not gold because an open account is a leash, and the one page his book cannot cover is a debt already cleared or a legend who is not a bet but a demolition.",
      coreDrive: "Keep every marker on the row running upstream to his ledger. Sign the muscle, price the door, and never let an account close, because a closed account is a dog who walks off the leash and out of the book.",
      profile: "A silver-muzzled Afghan Hound in a velvet collar who runs THE HOUSE LIMIT on the casino_strip and has never raised a paw in his life. He rules the row by the ledger: every marker signed on THE STRIP ends up in his book, the house always wins, nobody hits the bank, and behind the biggest pit on the row is a gold door the street swears hides a dealer who has never lost a hand. His flaw is the velvet: he collects dogs and not gold, because an open account is a leash, and he has run the whole row on paper so long that he has forgotten the one thing paper cannot price -- a dog who owes nothing, or a legend who is not a bet but a demolition walking up the strip.",
      signatureLine: "The house always wins. I never raised a paw to make it true -- I just kept the book, and the book keeps you.",
      beats: [
        { key: "origin",
          text: "He never fought. Not as a pup, not for a purse, not once. He watched the pits and learned the fighters bled and the book got paid. \"Everybody in that ring is a bet,\" he says, velvet smooth at his throat. \"I quit being a bet the day I bought the ledger the bets are written in.\" An Afghan Hound who chose the paper over the paw and never looked back down at the sawdust.",
          panelPrompt: STYLE + ", a silver-muzzled Afghan Hound pup in a velvet collar watching a fight-pit from behind glass on the casino_strip, gold #e8c55a marquee glare, chip stacks, a closed ledger under one delicate paw, magenta #FF2E88 signage bleeding across wet asphalt" },
        { key: "rise",
          text: "He turned the row into a book. Every marker signed on THE STRIP ran upstream to his ledger, and he learned an open account is worth more than any purse. \"Gold spends and it's gone,\" he says. \"A debt just sits there being loyal. I don't collect gold, dog. I collect dogs.\" He never once closed an account he could keep bleeding.",
          panelPrompt: STYLE + ", velvet-collared Afghan Hound behind a ledger table on the casino_strip, HOUSE LIMIT signage glowing, a line of dogs setting small gold #e8c55a stacks on velvet, an open ledger with a blank payer field, chip stacks and ledger screens, magenta #FF2E88 reflections" },
        { key: "rule",
          text: "He runs the house on one rule -- the house always wins, and nobody hits the bank -- and behind the biggest pit is a gold door where the street swears a dealer works who has never lost a hand. His book has a page for every dog on the row and one page, for one split night, that has gone missing. He does not go looking for it. \"A missing page is just an account I can never mark paid,\" he says. \"The House Limit is a wall. I've watched a lot of dogs learn what walls are named after.\"",
          panelPrompt: STYLE + ", silver-muzzled Afghan Hound in a velvet collar enthroned behind glass over the biggest pit on the casino_strip, a gold #e8c55a door glowing behind him, ledger screens, one ledger page conspicuously torn out, chip stacks, wet asphalt reflections, halftone shadow" },
        { key: "wound",
          text: "The velvet is the wound. He collects dogs, but a dog whose debt was cleared years back and never told keeps paying out of habit until the day he learns and stops, and a dog who bolted plates on to carry a number instead of running from it is not an account, he is a demolition. \"I priced every dog on this strip,\" he says, watching one come up the neon toward the glass. \"I never priced the one who was already paid and coming anyway.\"",
          panelPrompt: STYLE + ", velvet-collared Afghan Hound looking up from his ledger as a plated heavyweight Boxer walks the casino_strip neon toward the glass, gold #e8c55a chip stacks, a cleared-debt stamp glowing on a page he never showed, magenta #FF2E88 bleed, dread in the negative space" },
        { key: "reckoning",
          text: "He bet the house against a legend, and the house does not cover a demolition. The row's markers stop running upstream, the gold door opens, and somebody turns a card on the crown's name. \"Nobody hits the bank,\" he says, velvet still smooth as the bank walks in to collect him. \"I never once checked whether the crown was a bet -- or the thing bets are made against.\" The pit boss called the bluff. The crown was not bluffing.",
          panelPrompt: STYLE + ", white Dogo Argentino standing over a toppled silver-muzzled Afghan Hound on the casino_strip, a gold #e8c55a door swinging open behind, a single card turned face-up on velvet, chip stacks scattered across wet asphalt, HOUSE LIMIT sign gone dark, gold rim light" }
      ],
      relationToPlayer: "He is the crown's eighth ceiling: the lie that every dog on the row is an account the house holds and the house always wins. Beat him and the markers stop running upstream and the cleared debts finally get told. Leave him standing and every dog on THE STRIP keeps paying interest on a leash he calls a ledger.",
      tiedDogBooks: ["0003", "0011", "0043", "0049", "0050", "0055", "0056", "0062", "0085", "0101", "0102"],
      portrait: "assets/bosses/marker.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The pit boss never looks up from the book, velvet smooth at his throat. \"The house always wins, dog,\" he says. \"You already signed. I never even raised a paw.\"" },
          { key: "taunt", text: "He collects dogs and not gold, because an open account is a leash. \"Every dog on this row is a marker in my book,\" he says. \"Sit down and I'll find your page.\"" }
        ],
        choice: {
          prompt: "Marker holds every marker on the row. How do you play the house?",
          options: [
            { label: "Flip the Table", line: "You send the chips and the ledger flying across the velvet. You never raised a paw in your life, pit boss -- let's fix that tonight. The house that runs entirely on paper meets the one thing paper cannot price: a paw.", fx: "rage", tone: "blunt" },
            { label: "Call the House", line: "You tell him his book only holds a dog who believes the number, and your account cleared years back. There is nothing left to bleed. He reaches for the one page of the ledger that has gone missing and can mark you neither paid nor owing.", fx: "tactical", tone: "sharp" },
            { label: "Open the Gold Door", line: "You nod at the gold door behind the biggest pit, where the dealer who never lost a hand supposedly works. Deal me in -- or is the house scared of a legend it can't price? The velvet at his throat goes tight.", fx: "easter", tone: "taunting" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 9 -- NOTHING STAYS FROZEN -- THE COLD SAINT
       (Samoyed warden of the Regent's freeze, frost_district)
       Extends 0028/0030/0081/0082/0091/0092 -- cold-as-policy, the warm room
       his patrols bend around, the four-word mystery, "same breed opposite dial."
       ================================================================ */
    COLD_SAINT: {
      codename: "THE COLD SAINT",
      title: "Samoyed warden of the Regent's freeze, a smile like sunrise and a heart like January",
      faction: "the Regent's freeze (frost_district)",
      turf: "frost_district / the freeze line",
      metadata: {
        act: 9, actTitle: "NOTHING STAYS FROZEN", city: "frost_district",
        breed: "Samoyed", role: "Level-10 city boss",
        overlord: "THE REGENT",
        timelineTags: ["T3_CROWN_CITADEL", "T5_BLOCK_WAR"],
        themes: ["cold as policy", "a frozen district is a safe one", "nothing stays frozen"]
      },
      publicHook: "Hold still. The cold is the only thing keeping this block fed.",
      coreWound: "He is the same breed and the same weather as the Chill Samoyed line he froze out, and he turned his coat to administer the Citadel's winter on a schedule. He tells himself the freeze is mercy -- rations move while the ice holds, and cold beats the fire the Regent would send instead -- and the one warm room he leaves burning off the frozen line is the crack in that certainty he patrols around and will not close.",
      coreDrive: "Keep the district frozen and call it safe. Deliver the cold as policy, ration by ration, checkpoint by checkpoint, because a frozen block does not riot, it only slows, and a slow block is a governed one.",
      profile: "A Samoyed who administers the Regent's freeze over the frost_district with a smile like sunrise on fresh snow and a heart like January. He rules by the isobar: cold delivered as policy on a schedule, rations moving only while the ice holds, checkpoints where doors used to be, convinced down to his white coat that a frozen district is a safe one. His flaw is the family weather he shares with the Chill Samoyed line he froze out -- same breed, same grin, opposite dial -- and the one warm room he bends his own patrols around, because a warden who leaves a single light on has already half-answered the question of whether the freeze was ever mercy at all.",
      signatureLine: "I administer the winter the Citadel signed. A frozen block is a safe block -- ask the ones still breathing under the ice.",
      beats: [
        { key: "origin",
          text: "He was whelped to the same weather as every Samoyed on the block, the grin that reads friendly and the coat built for January. Then the Citadel offered him a winter to run. \"They asked who could hold a freeze without loving the dogs under it,\" he says, grinning like sunrise. \"I could hold the freeze. The grin does the rest.\"",
          panelPrompt: STYLE + ", a white Samoyed in warden white standing at a frost_district gate under the Regent's iced seal, ice-blue field, ration sheds glowing faint gold #e8c55a behind a hard freeze-line, breath in January shapes, snow as halftone static" },
        { key: "rise",
          text: "He turned cold into policy. He learned nobody riots at negative temperatures -- they get slow, then compliant, then moved -- so he administered the freeze instead of fighting it, a schedule the Regent signed and a warden delivered. \"Weather is innocent,\" he says. \"What I run is not weather. It arrives on time, and it takes exactly what the schedule says it takes.\"",
          panelPrompt: STYLE + ", white Samoyed warden walking a frozen frost_district street of slow grey ration queues, doors turned to checkpoints, the Regent's seal iced onto a post, cold steel-grey with one thread of gold #e8c55a lamplight, blowing snow" },
        { key: "rule",
          text: "He rules the district by holding it still and calls the stillness safety. When his frost came down off the frost_district like the Regent clearing his throat and FROSTBITE locked the docks solid, the crews learned cold is a dome too -- city-wide, patient, exactly as merciless as any budget. \"A frozen block does not fight me,\" he says. \"It cannot. That is not cruelty. Ask any dog I have kept too cold to starve.\"",
          panelPrompt: STYLE + ", THE DOCKS locked under ice-blue FROSTBITE snowfall, a pale Samoyed watching from a frost ridge, a single warm violet #9d8bff Barrier Ring glowing far below like a lantern in the white waste, cold steel-grey field, dread scale" },
        { key: "wound",
          text: "Nothing stays frozen, and he knows it, and the knowing is the one warm room. Off a jammer van's route there is a light he leaves burning, and he has bent his patrols around it two winters running, clean as an isobar, and never spoken of it. \"I hold a freeze for the Citadel and leave one room warm,\" he says, grin thinning. \"Some nights I think it is mercy. Some nights I think it is the little warmth that keeps the big cold deniable. A warden who cannot decide is already thawing.\"",
          panelPrompt: STYLE + ", a single warm-gold doorway glowing in a black frozen scrapline off the frost_district, a white warden-shaped Samoyed deliberately walking the long way around it through violet #9d8bff snow-static, stray silhouettes filing toward the light, one gold #e8c55a light in a steel-grey world, dread held gentle" },
        { key: "reckoning",
          text: "He falls the way ice falls: not shattered, just no longer cold enough to hold. The crown cracks the heat mains, the streets run wet, and a saint without his winter is just a dog who smiled while everyone shivered. \"Break the freeze before the block is ready and the Citadel sends fire, and fire has no warden,\" he says, the grin finally failing. \"You broke it when the block WAS ready. I never planned for that.\" The ice broke. Hell of a sound, a district breathing again.",
          panelPrompt: STYLE + ", heat mains cracked open in the frost_district, ice sheeting off the walls into running water, a gaunt regal white Samoyed warden going down as the streets thaw, a white Dogo Argentino at the melt-line, cold steel-grey giving way to gold #e8c55a dawn, snow turning to rain" }
      ],
      relationToPlayer: "He is the crown's ninth ceiling: the lie that a frozen block is a safe block and stillness is the same as mercy. Beat him and the district thaws and finds out it can move. Leave him and every dog on the frost_district stays kept just warm enough not to starve and just cold enough not to rise.",
      tiedDogBooks: ["0028", "0030", "0081", "0082", "0091", "0092"],
      portrait: "assets/bosses/cold_saint.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The warden of the freeze smiles like sunrise on fresh snow, the district iced still behind him. \"A frozen block is a safe block,\" he says. \"Hold still. This is mercy.\"" },
          { key: "taunt", text: "He administers the Citadel's winter on a schedule and calls the stillness safety. \"I keep this district just warm enough not to starve,\" he says, grinning, \"and just cold enough not to rise.\"" }
        ],
        choice: {
          prompt: "The Cold Saint holds the whole district frozen. How do you meet the freeze?",
          options: [
            { label: "Crack the Mains", line: "You drive straight for the heat mains and blow the freeze-line open. You call the ice mercy -- I call it a leash that leaves no marks. Steam bursts through January and the streets run wet for the first time in two winters.", fx: "rage", tone: "hot" },
            { label: "Break It Ready", line: "You tell him the truth of his own schedule: break the freeze early and the Citadel sends fire, so you waited until the block was ready, and it is, right now. His timetable has no line drawn for a thaw that arrives on the block's clock instead of his.", fx: "tactical", tone: "patient" },
            { label: "Find the Warm Room", line: "You name the one door off the jammer route that he leaves burning and bends his patrols around. A warden who leaves a single light on already half-answered whether the freeze was ever mercy. The sunrise grin finally thins.", fx: "easter", tone: "gentle" }
          ]
        }
      }
    },

    /* ================================================================
       ACT 10 -- CROWNS GET TAKEN -- THE REGENT
       (throne-sitter, crown_citadel, draped in old king colors, serves THE COLLAR)
       Extends 0001/0028/0030/0081/0082 -- the throne-city built by a stray and
       squatted in, "Regent. Nice chair. Whose is it?", the freeze as his warning.
       ================================================================ */
    REGENT: {
      codename: "THE REGENT",
      title: "The throne-sitter, draped in the old king colors, ruling on borrowed legend",
      faction: "the Crown Citadel (crown_citadel)",
      turf: "crown_citadel / the Citadel gate",
      metadata: {
        act: 10, actTitle: "CROWNS GET TAKEN", city: "crown_citadel",
        breed: "unknown -- draped in the old king colors he never earned", role: "Level-10 throne boss",
        overlord: "THE COLLAR",
        timelineTags: ["T3_CROWN_CITADEL", "T5_BLOCK_WAR"],
        themes: ["borrowed legend", "flinching is not kneeling", "crowns get taken never given"]
      },
      publicHook: "Every boss on the block pays up to this gate. Lower your eyes.",
      coreWound: "He was given the chair. He has the old king's guard, the gold, the room, and the colors -- everything except the one thing the chair runs on, which cannot be issued or seized: a block that kneels because it believes, not because it flinches. He rules on borrowed legend, and the legend he borrows is the terror of the dog that eats names, because he has none of his own.",
      coreDrive: "Hold the chair he was handed. Keep every boss on the ladder paying up to the Citadel gate, keep the old king colors on his back and the freeze on the districts that rise, and never let the block learn the difference between a flinch and a knee.",
      profile: "The throne-sitter of the Crown Citadel, draped in the old king colors he never earned, ruling a throne-city built by a stray and squatted in by everything strays despise. He rules on borrowed legend: the Lot Warden taxing the dirt, Meter billing the lanes, Marker keeping the ledger, the Cold Saint administering the freeze, every boss on the block paying up to his gate. His flaw is the chair itself -- he was given it, not took it -- so he has the guard and the gold and the colors and not the one thing a crown actually runs on, and when a stray who came up out of THE LOT dirt reaches the gate, the whole borrowed edifice learns that nobody ever knelt for the Regent. They only ever flinched.",
      signatureLine: "Every boss on my ladder pays up to this gate. Crowns get taken, never given -- and I would know. I was given mine.",
      beats: [
        { key: "origin",
          text: "He did not come up out of the dirt. He was placed on the chair, draped in the old king colors while the seat was still warm, and told to sit. \"A stray built this city and something worse squatted it,\" he says. \"When the chair came open I did not fight for it. I was handed it. I have spent every season since making sure nobody asks by whom.\"",
          panelPrompt: STYLE + ", a throne-sitter draped in old king colors on a gilded chair inside the crown_citadel, gold #e8c55a light, the Citadel core towers behind, a cold paid guard formation flanking an empty dais, crimson and gold sky, hollow grandeur" },
        { key: "rise",
          text: "He did not rise. He wired the city under the chair he was handed. Every boss became a rung paying up to his gate, and he froze the districts that rose as a warning. \"I do not climb,\" he says. \"I collect. The Lot Warden, Meter, the Iron Handler, the Sovereign, Terminus, Marker, the Cold Saint -- every one pays up to this gate, and I have never once climbed down to see what holds them there.\"",
          panelPrompt: STYLE + ", a gilded Citadel gate with tribute lines of taxes and ledgers and iced districts flowing upward toward it, the Regent small on a high throne, cold steel-grey districts below and gold #e8c55a Citadel above, the frost_district freeze-line visible as a warning" },
        { key: "rule",
          text: "He rules on borrowed legend, and the legend he borrows is the terror of the dog that eats names. He sits the chair the way you wear a coat cut for a bigger dog, and he keeps the block flinching because a flinch, seen from the throne, looks exactly like a knee. \"They pay. They lower their eyes. They flinch when I pass,\" he says. \"From up here you cannot tell a flinch from a knee. I have staked a whole reign on the block never learning the difference.\"",
          panelPrompt: STYLE + ", the Regent on the crown_citadel throne draped in old king colors, a wide crowd below lowering their eyes in a flinch, gold #e8c55a throne-light, the old king's guard standing cold and paid, crimson banners, ink-black shadow under the dais" },
        { key: "wound",
          text: "The chair runs on a thing he cannot issue and cannot seize, and he knows he does not have it. Above his own throne is the collar the whole city serves -- the pound, the wagon, the leash he sits inside and calls a crown -- and he is its best-dressed manager, propped where the dog that eats names once stood, doing the same biting in borrowed colors. \"The old king was taken. I was given,\" he says, the one time he says it. \"A crown you are given is just a longer leash with a chair attached. I have known that since the day they sat me. I sit anyway.\"",
          panelPrompt: STYLE + ", intimate close camera, the Regent alone at night on the crown_citadel throne, the old king colors slipping off one shoulder to show a collar underneath, the cold floodlights of a distant pound fence burning over the Citadel wall, gold #e8c55a and dread in the negative space" },
        { key: "reckoning",
          text: "He falls because a crown he was given cannot survive a crown that is taken. Every boss the stray dropped paid up to this gate; every rival is in the stands; and when the crown comes up out of THE LOT dirt to the Citadel, the block finds out at last that it was only ever flinching. \"You were not given anything,\" he says, watching the chair change hands. \"You came up out of the dirt and took it. That is the one move I never had in me.\" The chair is yours. The city holds its breath. The alley just made another king.",
          panelPrompt: STYLE + ", a white Dogo Argentino taking the gilded crown_citadel throne as the Regent falls from it, old king colors pooling on the dais, the crowd in the stands rising from a flinch into something upright, gold #e8c55a light flooding the Citadel, crimson sky breaking" }
      ],
      relationToPlayer: "He is the crown's tenth ceiling and the last face before the real teeth: the lie that the chair belongs to whoever was handed it, and that a flinching block is a kneeling one. Beat him and the block learns the crown was always takeable -- but taking the chair only reveals the collar above it. The Regent was a middle-manager of a system that hands out crowns as bait.",
      tiedDogBooks: ["0001", "0028", "0030", "0081", "0082"],
      portrait: "assets/bosses/regent.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The throne-sitter waves you closer from the gilded chair, draped in the old king colors. \"Every boss on the block pays up to this gate,\" he says. \"Lower your eyes.\"" },
          { key: "taunt", text: "He has the guard, the gold, and the colors, and none of the thing the chair actually runs on. \"They kneel when I pass,\" he says. \"Come and add your knee to the count.\"" }
        ],
        choice: {
          prompt: "The Regent rules on borrowed legend. How do you approach the crown?",
          options: [
            { label: "Take the Chair", line: "You walk straight up the dais and reach for the throne itself. Crowns get taken, never given -- and you were handed yours. The one move a given king never had in him is the one climbing the steps at him now.", fx: "rage", tone: "direct" },
            { label: "Cut the Tribute", line: "You remind him every rung under the gate already fell -- the Lot, Meter, Marker, the Saint, all of it. Nothing is paying up to this chair anymore. He is a throne with no city, and he learns it in real time.", fx: "tactical", tone: "strategic" },
            { label: "Whose Chair Is It", line: "You ask him the one question a given crown cannot answer: whose chair is this, really? He came up out of no dirt for it, and the whole borrowed edifice hears the silence where the answer should be.", fx: "easter", tone: "quiet" }
          ]
        }
      }
    },

    /* ================================================================
       APEX I -- THE MONGREL KING, "the Dog That Eats Names"
       (story-layer nemesis, systems/story.js -- NEVER name his true face)
       Extends the wagon / first-light / eaten-name MOTIF (no dog book names him
       directly): 0001 (the schedule), 0002 (the wagon at FACTORY ROW), 0072,
       0077. He wears every name he ate and none of his own; he served THE COLLAR.
       ================================================================ */
    MONGREL_KING: {
      codename: "THE MONGREL KING",
      title: "The Dog That Eats Names -- the nemesis atop the ladder, wearing every name he swallowed and none of his own",
      faction: "the top of the ladder (story-layer nemesis)",
      turf: "the throne climb / atop the rank ladder",
      metadata: {
        act: null, actTitle: "CHALLENGE THE KING", city: null,
        breed: "unknown -- a mongrel of every name he ate, his own face never shown", role: "story-layer nemesis (systems/story.js)",
        overlord: "THE COLLAR",
        timelineTags: ["T5_BLOCK_WAR", "T6_MYTHICS"],
        themes: ["the dog that eats names", "he wore a collar too", "a champion who mistook the leash for a crown"]
      },
      publicHook: "I have every name on this block but one. Climb up here and I'll take yours too.",
      coreWound: "He has no name of his own. He ate so many -- every king before you, the old king's crown and name in the same breath -- that nothing is left underneath but the collar. He did the pound's biting on a chain he called a crown, and he never once let the block see the one thing the crown was covering: that he was never king of anything, only the catchers' best tooth.",
      coreDrive: "Sit the top of the ladder and eat every name that climbs it. Keep the seven rungs looking like a stray's road to a crown, so the strays keep climbing into the collar's ladder and he keeps feeding, fat and proud on a chain.",
      profile: "The named nemesis at the top of the rank ladder, \"the Dog That Eats Names,\" who took the old king's crown and the old king's name in the same breath and has eaten every season but his own. He rules the ceiling by devouring whatever climbs to it, a mongrel wearing every name he ever swallowed -- which is why the street has a thousand stories of his face and not one that agrees, because there is no face under the names to agree on. His flaw is the collar he never takes off: he was never king of anything, only the pound's champion doing its biting on a chain he calls a crown, and the day a climber refuses that crown instead of fighting him for it, the dog that eats names has nothing left to eat.",
      signatureLine: "Ask the block my name and you'll get a hundred. Every one of them belonged to a dog I ate. My own? I gave that to the collar a long time ago.",
      beats: [
        { key: "origin",
          text: "He came up nameless, the way every stray does, and where another dog fought the wagon he took its offer. \"The catchers don't want your body, pup,\" he says, in a voice made of other dogs' voices. \"They want your name off the block by first light. I gave them mine first. Then I ate everybody else's.\" A mongrel who traded his own name for the job of taking names.",
          panelPrompt: STYLE + ", a hulking mongrel silhouette at the top of a long ladder of rungs, his face lost entirely in ink-black shadow so no features show, a collar catching cold light at his throat, a distant pound fence floodlight behind, crimson sky, dread scale" },
        { key: "rise",
          text: "He climbed the seven rungs the strays climb, and at the top he found the old king and took his crown and his name in one bite. Then he kept eating. \"Every season has a king,\" he says. \"I've eaten all of them but the one I'm wearing this week. Names are the only thing on this block that keep.\"",
          panelPrompt: STYLE + ", a faceless mongrel at the top of the ladder closing over a fallen crowned dog, the old king's name and crown drawn as light being swallowed into shadow, the Old Pack's dead-legend silhouettes lining the alley below, crimson and gold #e8c55a, ink-black where his face should be" },
        { key: "rule",
          text: "He sits the ceiling and eats what climbs it, and he lets the seven rungs keep looking like a road to a crown. \"They think they're climbing to me,\" he says, with somebody else's laugh. \"They're climbing into the ladder the catchers built, and I'm the last rung, and every dog who reaches me feeds me and thinks he almost won.\" Fat and proud on a chain he calls a crown.",
          panelPrompt: STYLE + ", the faceless Mongrel King enthroned at the ladder's top, a chain running from his collar down out of frame, a line of climbers ascending toward him lit like moths, his features never visible, pound floodlights cold behind, crimson drizzle, gold #e8c55a rung-light" },
        { key: "wound",
          text: "Under the crown is the collar, and he has never once taken it off, because there is nothing underneath it anymore -- he ate his own name first and gave it to the wagon, and a dog who has eaten every name including his own is not a king, he is a mouth the pound points. \"You want to see my true face,\" he says. \"So does the block. There's nothing to see. I'm the last name I ate, and next week I'll be another. The crown covers the collar. The collar goes all the way down.\"",
          panelPrompt: STYLE + ", intimate close camera, the crown lifted a hand's width off the Mongrel King's head to show a catchers' collar beneath and only shadow where a face should be, a chain taut from the collar toward a distant wagon, cold light, crimson and ink-black, dread in the negative space" },
        { key: "reckoning",
          text: "He does not fall to a better fighter. He falls to a climber who reaches the top and refuses the crown instead of fighting for it, because a dog that eats names starves the moment nobody offers theirs. \"Beat me and you're the new tooth,\" he says. \"Refuse me and you're the first dog in the history of this block the collar couldn't feed to itself. Which one are you?\" Climb the tower and make him choke on your name, or take the crown off his skull and finally see there was never a king under it -- only the leash.",
          panelPrompt: STYLE + ", a white Dogo Argentino at the ladder's top with the crown held out and not put on, the faceless Mongrel King collapsing into the pile of names he ate, the chain from his collar going slack, the Old Pack bowing below, gold #e8c55a dawn cutting the crimson, ink-black dispersing" }
      ],
      relationToPlayer: "He is the named face of the ceiling, the nemesis the Old Pack aims you at, and the last lie before the truth. Beat him for the crown and you become the collar's next champion. See past him to the chain at his throat and you learn the fight was never with the dog that eats names. It was with the thing that fed him.",
      tiedDogBooks: ["0001", "0002", "0072", "0077"],
      portrait: "assets/story/nemesis_mongrel.png",
      preFight: {
        intro: [
          { key: "confront", text: "The dog that eats names waits at the ladder's top, wearing a hundred stolen ones and none of his own. \"Climb up here,\" he says in a voice made of other dogs' voices, \"and I'll take yours too.\"" },
          { key: "taunt", text: "Under the crown is a collar he has never once taken off. \"Ask the block my name and you'll get a hundred,\" he says. \"Every one belonged to a dog I ate. Now feed me yours.\"" }
        ],
        choice: {
          prompt: "The Mongrel King eats every name that climbs to him. How do you reach the crown?",
          options: [
            { label: "Feed Him a Name", line: "You charge the last rung head-on and offer the one name he cannot swallow whole. You eat names -- come choke on mine. The champion who has never been out-fought meets a name that fights back.", fx: "rage", tone: "ferocious" },
            { label: "Lift the Crown", line: "You reach not for him but for the crown, to show the block the collar underneath it. There was never a king under here, just the pound's tooth on a chain he calls a throne. The chain at his throat pulls taut in the light.", fx: "tactical", tone: "revealing" },
            { label: "Refuse the Crown", line: "You climb all the way up and refuse the crown instead of fighting for it. A dog that eats names starves the moment nobody offers one -- so keep it. He has, for the first time, nothing left to eat, and the block finally sees the leash.", fx: "easter", tone: "eerie" }
          ]
        }
      }
    },

    /* ================================================================
       APEX II -- THE COLLAR (the human system: pound / catchers / wagon)
       (story-layer APEX antagonist, systems/story.js COLLAR)
       The system every leash serves -- the Iron Handler's buttoned collar, the
       Regent's borrowed colors, the Mongrel King's crown are one collar worn
       three ways. Drawn ONLY as apparatus, NEVER a human on panel (STYLE law).
       Extends the pound / wagon / first-light books: 0001/0002/0007/0025/0026/
       0038/0054/0077/0078/0097.
       ================================================================ */
    THE_COLLAR: {
      codename: "THE COLLAR",
      title: "The apex antagonist -- the pound, the catchers, the wagon; the system every leash serves",
      faction: "the pound (the human system)",
      turf: "the whole block / off the block by first light",
      metadata: {
        act: null, actTitle: "THE COLLAR IS THE MONSTER", city: null,
        breed: "n/a -- the system: pound, catchers, leash, wire, wagon", role: "story-layer APEX antagonist (systems/story.js COLLAR)",
        overlord: null,
        timelineTags: ["T3_CROWN_CITADEL", "T4_EVERY_LEASH_BREAKS", "T5_BLOCK_WAR"],
        themes: ["the real monster is the system", "the crown was the bait", "off the block by first light"]
      },
      publicHook: "You will be off this block by first light. All of you. On schedule.",
      coreWound: "It is not a dog and it carries no wound. Its one vulnerability is that it needs the strays to believe the ladder is theirs and the crown is real -- it runs on dogs climbing willingly into its own cage. The Mongrel King wore it as a crown, the Regent wears it as colors, the Iron Handler buttons it under his own, and every leash on the block serves it. It has no face on the panel because it never needed one. The dogs only ever see the wagon.",
      coreDrive: "Clear the block by first light, every season, forever. Hand out crowns as bait, let the champions do the biting, and keep the seven-rung climb looking like a stray's road up when it is the catchers' ladder down.",
      profile: "The apex antagonist the Old Pack reveals near the throne: not the Mongrel King, not the Regent, but the pound itself -- the catchers, the leash, the wire, the wagon that hauls strays off the block at first light. It is the system every leash serves and every boss pays up to; the Iron Handler's buttoned collar, the Regent's borrowed colors, and the Mongrel King's crown are all the same collar worn three ways. Its flaw is the only one a system has: it runs on belief. The seven-rung climb is the catchers' own ladder and the crown is the bait, and the day a king rips the collar off the whole city instead of wearing it pretty, the thing that ate every king before finally has nothing left to point.",
      signatureLine: "I am not a dog. I am the schedule every dog is on. Off the block by first light -- crown or no crown, it was always the same wagon.",
      beats: [
        { key: "origin",
          text: "Before there was a crown to climb toward, there was a fence with a light on it and a wagon that came at first light. \"The block gives a stray with no colors one thing,\" it states, in the flat voice of a schedule. \"Where you were whelped is where the wagon expects to collect you. I do not need your obedience. I only need you on the block when the headlights come.\"",
          panelPrompt: STYLE + ", a matte pound wagon idling at the end of a chain-link block at first light, one cold floodlight on the fence, an empty catch-pole leaning against the gate, wet asphalt, no dogs and no humans on panel, gold #e8c55a dawn bleeding cold, dread in the emptiness" },
        { key: "rise",
          text: "It did not rise. It built a ladder and let the dogs climb it. Seven rungs, Stray to King of the Block, every one the catchers' own, dressed up as a stray's road up. \"I do not chase what climbs toward a crown,\" it states. \"A dog racing up my ladder is a dog delivering himself. I built the rungs. The strays supply the legs.\"",
          panelPrompt: STYLE + ", a long ladder of seven rungs rising from a chain-link block toward a distant gilded crown, each rung a leash or a catch-pole laid crosswise, a pound wagon waiting at the top instead of a throne, cold floodlight glare, no humans on panel, crimson and steel-grey, gold #e8c55a crown as bait far above" },
        { key: "rule",
          text: "It rules by first light and by proxy. It never bites the block itself; it hands out a crown and lets the champion do the biting -- the Mongrel King fat on a chain, the Regent draped in borrowed colors, the Iron Handler with a collar buttoned under his own. \"Every leash on this block serves me,\" it states. \"I keep one collar and wear it a hundred ways. The dogs name each way a different king. They are all the same wagon.\"",
          panelPrompt: STYLE + ", three collars laid in a cold row -- a foreman's buttoned collar, a crown, a warden's chain -- identical underneath, a pound wagon's headlights washing over them, chain-link and floodlight, no humans on panel, ink-black and gold #e8c55a, wet asphalt reflections" },
        { key: "wound",
          text: "A system has one wound: it needs to be believed. Every leash it holds depends on the dog at the end thinking the climb is his and the crown is real. The Leashbreak Tactix proved a chain can break, Rosco chewed off his own and came back for everyone else's, and the Iron Handler felt his own collar the day the leashed chose to be uncollared. \"I am strongest when a dog wears me pretty and calls it a throne,\" it states. \"I am finished the moment one king rips me off the whole city instead. I have fed on every king who chose the throne. I have never met the other kind.\"",
          panelPrompt: STYLE + ", a single leash snapping taut and breaking at its midpoint against a chain-link block, the pound floodlight flickering, a catch-pole dropped on wet asphalt, no dogs and no humans on panel, Leashbreak purple #9d8bff sparking along the broken links, gold #e8c55a underlight, dread turning to defiance" },
        { key: "reckoning",
          text: "It is the last thing the Old Pack shows you, and the only boss the game does not let you simply beat -- it lets you choose. Rip the collar off the whole city, or wear it pretty like the dog that ate names did and call it a throne. \"The Mongrel King did my biting and thought it was his crown,\" it states. \"The Regent wears my leash and calls it the old king colors. You climbed my ladder to a crown that was always bait. So choose, King of the Block: take the collar off this city, or become the next best-dressed way I clear the block by first light.\" The crown was the bait. The block was the cage. Now you finally see the real teeth.",
          panelPrompt: STYLE + ", a white Dogo Argentino at a chain-link block gate, one paw on a fallen catch-pole, the pound wagon's headlights going dark, the whole city's collars and leashes lying cut across wet asphalt behind him, first-light gold #e8c55a breaking over the fence, no humans on panel, the floodlight finally off" }
      ],
      relationToPlayer: "It is the apex, and the only ceiling that is a mirror instead of a wall. Every other boss was a dog you could drop; the Collar is the system all of them served, and it cannot be dropped, only refused. Beat the Mongrel King and you inherit the collar. Take the crown from the Regent and you inherit the collar. The Collar is the one fight the crown does not win by climbing -- it wins by taking the leash off the whole block instead of wearing it.",
      tiedDogBooks: ["0001", "0002", "0007", "0025", "0026", "0038", "0054", "0077", "0078", "0097"],
      portrait: "assets/bosses/the_collar.jpg",
      preFight: {
        intro: [
          { key: "confront", text: "The collar speaks in the flat voice of a schedule, no dog on the panel, just the wagon idling at the chain-link gate. \"Off the block by first light,\" it states. \"Crown or no crown, it was always the same wagon.\"" },
          { key: "taunt", text: "It hands out crowns as bait and lets the champions do its biting. \"I keep one collar and wear it a hundred ways,\" it states. \"You climbed my ladder. Now choose which way you wear me.\"" }
        ],
        choice: {
          prompt: "The Collar is the system every leash serves. How do you face what can't be dropped?",
          options: [
            { label: "Rip the Collar Off", line: "You tear the leash off the whole block instead of wearing it pretty. Every king before me wore you like a crown -- I'm taking you off all of them at once. The one move the system has never survived comes down on it now.", fx: "rage", tone: "defiant" },
            { label: "Break the Belief", line: "You show the whole block the truth the system runs on, that the climb was never theirs and the ladder was always the catchers'. Belief is the only thing holding the leash, so you make the block stop believing, and the wagon's headlights go dark.", fx: "tactical", tone: "cold" },
            { label: "Be the Other Kind", line: "You tell it flat that you are the king it hands the crown to and never met, the one who takes the leash off instead of putting it on. It has fed on every champion who chose the throne. It has no schedule for you.", fx: "easter", tone: "level" }
          ]
        }
      }
    }

  };

  /* ---- self-register (mirrors cards_stories.js export contract) ----------- */
  if (global) {
    global.AK_BOSSES = BOSSES;
    global.AK_BOSS_ROSTER = ROSTER;
    global.AK_BOSS_GET = function (k) { return (k && BOSSES[k]) ? BOSSES[k] : null; };
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
