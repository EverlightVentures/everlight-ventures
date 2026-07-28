/* game/systems/tutorial.js -- AK_SYSTEMS module: "tutorial" (first-run onboarding).
   ------------------------------------------------------------------------
   THE #1 RETENTION FIX. Operator playtest 2026-06-25: "I have no idea what I'm doing."
   A first-run, SKIPPABLE, gritty-voiced guided walkthrough that teaches the CORE LOOP
   CANON IN ORDER (see AK_CORE_LOOP_CANON.md):

     move -> TOWN HALL (controls buildings / builders / deck card-max)
          -> assign your 11-card deck to buildings by TRAIT + FACTION
          -> harvest / crops (the tools, the produce, the Fence)
          -> fortify districts with wood + stone (THE WATCH)
          -> win a card in a WILD ENCOUNTER
          -> survive a RAID (your 11 dogs defend RPG-style, not the tower lane)
          -> heal the wounded in the INFIRMARY
          -> climb RANK + the CROWN BLOODLINE story.

   VOICE: gritty gangland. Two narrators only, both canon:
     - THE OLD PACK (the dead-legend ancestor narrator of THE CROWN BLOODLINE)
     - THE FIXER    (Marrow the Fixer, runs the jobs -- glyph matches systems/missions.js)
   NAME CANON (AK_ROADMAP_V2_NAMED.md S0): clans Zoomie Syndicate / Leashbreak Tactix /
   Boneguard Crew / K9 Circuitry / Stray; ranks Stray -> Pup -> Runner -> Warrior ->
   Enforcer -> Right Paw -> King of the Block; the Fence = market, the Watch = guarding;
   the Mongrel King = "the Dog That Eats Names". NO Kimi generics, NO invented names.

   MECHANICS:
   - A step OVERLAY: a darkened scrim with a glowing SPOTLIGHT ring that highlights the
     real HUD chip the step is talking about (Town Hall, your Pack, Tools, the Watch, the
     Fence, Rank, Story). Steps without a UI anchor centre the card on a flat scrim.
   - NEXT advances; SKIP ends it; tapping the scrim also advances (mobile-friendly).
   - Persists p.tutorialDone (falsy-default) via AK_ECON.mutateProfile ONLY on finish/skip
     -- a fresh profile stays byte-identical until the player actually completes or skips.
   - Auto-runs ONCE on the first hub session (when the HUD is up and nothing else is open),
     and exposes a REPLAY entry the integration pass can wire to a menu button.

   PERFORMANCE (60fps cheap-Android): zero per-frame work -- no rAF render loop. The ring
   pulse is a GPU CSS keyframe. DOM is built lazily on start and torn down on finish.
   Repositioning is rAF-coalesced and only fires on resize. Capped auto-start polling.

   SAFETY: headless-safe (guards document); never throws into the host; EDITS ONLY this
   file; FROZEN engine.js untouched. Exposes window.AK_TUTORIAL for the integration pass.

   AK-COACHVID 2026-07-02: the first-visit contextual coach (VISITS below, ~20 screens)
   now carries an optional cinematic `video` header, reusing assets/cinematics/*.mp4 --
   free, no new renders. Render manifest (<=4 NET-NEW beats, screenId -> assets/
   tutorial_mp4/<screenId>.mp4) for the operator to shoot -- do NOT render these here:
     world -- cold-open "welcome to the block"
     deck  -- "this is your deck"
     raid  -- "raid the enemy crown"
     story -- "you're a king now" finale
   Every path degrades on 404 via onerror (buildCoach/openCoach), so an unrendered
   beat never breaks a screen -- it just shows no banner until it exists.
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';

  var doc = (typeof document !== 'undefined') ? document : null;

  // ---- the two canon narrators ---------------------------------------------
  var OLD_PACK = { name: 'THE OLD PACK', glyph: '🐺', color: '#c9b4ff' }; // wolf -- dead-legend ancestor
  var FIXER    = { name: 'THE FIXER',    glyph: '📋', color: '#ff9d5c' }; // clipboard -- matches missions.js

  // ---- the script: CORE LOOP CANON, taught IN ORDER ------------------------
  // target = a HUD element id to spotlight, or null to centre the card.
  var STEPS = [
    { who: OLD_PACK, target: null, title: 'THE CROWN BLOODLINE',
      line: "Listen close, Stray. I'm the Old Pack -- the dead legends who ran these blocks before you drew breath. The Mongrel King wears the crown now, the Dog That Eats Names. You're gonna take it off him. First, learn how we survive out here." },

    { who: FIXER, target: null, title: 'WORK THE STREETS',
      line: "Name's Marrow. I run the jobs round here. Move your mutt -- drag anywhere to walk, or tap H J K L if you're on keys. Get a feel for the block before somebody tries to take it from under you." },

    { who: FIXER, target: 'ph-th', title: 'THE TOWN HALL RUNS IT ALL',
      line: "That's your Town Hall. It's the master of everything -- how many BUILDINGS you run, how many BUILDERS you got working, and how high your deck can level. Pump the Town Hall and the whole block grows with it." },

    { who: FIXER, target: 'ph-crew', title: 'PUT YOUR PACK TO WORK',
      line: "You run this city with your 11-card deck -- your PACK. Walk into a building and ASSIGN a dog to it. Match the trait and the faction to the right job -- Zoomie Syndicate, Leashbreak Tactix, Boneguard Crew, K9 Circuitry -- and it pays out fatter. Wrong dog, weak yield." },

    { who: FIXER, target: 'ph-tools', title: 'HARVEST THE BLOCK',
      line: "Grab your TOOLS and work the land. Crops you grow you trade at the Fence for gold or burn on jobs. Wood and stone you pull off the trees and the rubble -- you'll need every scrap of it. No tools, no work, mutt." },

    { who: FIXER, target: 'ph-fence', title: 'MOVE IT THROUGH THE FENCE',
      line: "The Fence is where the block eats. Trade your crops and your scrap for gold here. Anything you took in a raid? It launders clean through the Fence before it spends. Every district moves its own product." },

    { who: FIXER, target: 'ph-watch', title: 'STAND THE WATCH',
      line: "Spend that wood and stone to FORTIFY your district -- that's THE WATCH. Post your pack as defenders and set your layout. A soft block gets raided in its sleep. A fortified one makes em bleed for every inch." },

    { who: FIXER, target: null, title: 'WIN A DOG IN THE ALLEY',
      line: "Roam the streets and a stray will square up on you -- a WILD ENCOUNTER. Beat it down and you keep a COPY of that card for your pack. Three ways to grow the pack: win em wild, unlock em through the Town Hall, or buy em at the Shop." },

    { who: OLD_PACK, target: 'ph-th', title: 'WHEN THE RAID COMES',
      line: "Another clan will come for your turf. That fight ain't the tower lane -- on the world map your 11 dogs defend RPG-style, paw to paw. Lose, and your Town Hall takes the hit and your whole deck drops a level. That's why the Watch matters, Stray." },

    { who: FIXER, target: null, title: 'PATCH UP THE WOUNDED',
      line: "A dog that falls in a raid don't just shake it off. Send it to the INFIRMARY and heal it before it can fight again. Your pack ain't disposable -- keep em breathing and they'll die for you." },

    { who: OLD_PACK, target: 'ph-rank', title: 'CLIMB THE LADDER',
      line: "Every win moves you up the ranks -- Stray, Pup, Runner, Warrior, Enforcer, Right Paw, and one day KING OF THE BLOCK. Win fights, hold turf, earn your clan's karma. Each one carves another notch in the Crown Bloodline." },

    { who: OLD_PACK, target: 'ph-story', title: 'YOUR STORY WAITS',
      line: "Tap the STORY any time and I'll tell you your next move. The Mongrel King is still out there. Take his crown, Stray -- the block is yours to run now. Go." }
  ];

  // ---- lazy module state ----------------------------------------------------
  var S = {
    running: false, i: 0, ctx: null, armed: false, autoTries: 0, _repo: 0, _onResize: null,
    root: null, ring: null, card: null, titleEl: null, lineEl: null,
    nameEl: null, glyphEl: null, countEl: null, nextBtn: null, skipBtn: null
  };

  // ---- economy bridge (state via AK_ECON.mutateProfile; falsy-default) ------
  function econ() { return global.AK_ECON || (S.ctx && S.ctx.econ) || null; }
  // AK-FIRSTRUN 2026-07-10: index.html's first-run orchestrator owns the onboarding
  // sequence (age -> auth -> block -> starter -> firstgame -> hudtut -> done). While
  // its stage exists and is NOT hudtut/done, every self-arm path here stands down --
  // the orchestrator explicitly starts the walkthrough at stage 5 (hudtut). The
  // __akFirstrunHold flag covers the parse-to-classify window before a stage is
  // stamped. No stage key + no hold = today's exact self-arming behavior.
  function orchestratorHolds() {
    try {
      if (global.__akFirstrunHold) return true;
      var st = localStorage.getItem('ak_firstrun_stage');
      return !!(st && st !== 'hudtut' && st !== 'done');
    } catch (_e) { return false; }
  }
  function isDone() {
    try { var e = econ(); return !!(e && e.loadProfile && e.loadProfile().tutorialDone); }
    catch (_e) { return false; }
  }
  function markDone() {
    try { var e = econ(); if (e && e.mutateProfile) e.mutateProfile(function (p) { p.tutorialDone = 1; }); }
    catch (_e) {}
  }
  function clearDone() {
    try { var e = econ(); if (e && e.mutateProfile) e.mutateProfile(function (p) { try { delete p.tutorialDone; } catch (_x) { p.tutorialDone = 0; } }); }
    catch (_e) {}
  }
  function banner(msg, secs) {
    try {
      var sb = (S.ctx && S.ctx.showBanner) || global.showBanner;
      if (typeof sb === 'function') sb(msg, secs || 2.2);
    } catch (_e) {}
  }

  // ---- one-time style inject (GPU pulse -- no JS per-frame cost) ------------
  function ensureStyle() {
    if (!doc || doc.getElementById('ak-tut-style')) return;
    var st = doc.createElement('style');
    st.id = 'ak-tut-style';
    st.textContent =
      '@keyframes ak-tut-pulse{0%,100%{box-shadow:0 0 0 9999px rgba(4,4,9,.80),0 0 0 2px #e8c55a,0 0 18px 4px rgba(232,197,90,.55)}' +
      '50%{box-shadow:0 0 0 9999px rgba(4,4,9,.80),0 0 0 3px #ffe08a,0 0 30px 9px rgba(232,197,90,.85)}}' +
      '@keyframes ak-tut-rise{from{transform:translateY(14px);opacity:0}to{transform:translateY(0);opacity:1}}' +
      '#ak-tut-ring{animation:ak-tut-pulse 1.5s ease-in-out infinite;will-change:box-shadow}' +
      '#ak-tut-card{animation:ak-tut-rise .22s ease-out}';
    (doc.head || doc.documentElement).appendChild(st);
  }

  // ---- build the overlay DOM (once per run) --------------------------------
  function buildDOM() {
    if (!doc || S.root) return;
    ensureStyle();

    var root = doc.createElement('div');
    root.id = 'ak-tut-root';
    root.style.cssText = 'position:fixed;inset:0;z-index:9000;touch-action:none;' +
      'font-family:Inter,system-ui,Segoe UI,sans-serif;-webkit-tap-highlight-color:transparent;';
    root.addEventListener('click', function () { advance(); }); // tap scrim -> next

    // the spotlight ring (its huge box-shadow darkens everything outside it)
    var ring = doc.createElement('div');
    ring.id = 'ak-tut-ring';
    ring.style.cssText = 'position:fixed;border-radius:13px;pointer-events:auto;display:none;';

    // the speech card
    var card = doc.createElement('div');
    card.id = 'ak-tut-card';
    card.style.cssText = 'position:fixed;left:50%;transform:translateX(-50%);' +
      'bottom:calc(18px + env(safe-area-inset-bottom,0px));width:min(560px,92vw);' +
      'background:linear-gradient(180deg,#15110a,#0c0a06);border:1px solid rgba(201,168,76,.5);' +
      'border-radius:16px;padding:16px 18px 14px;box-shadow:0 14px 40px rgba(0,0,0,.6);' +
      'pointer-events:auto;box-sizing:border-box;';
    card.addEventListener('click', function (e) { e.stopPropagation(); }); // card taps never advance

    var head = doc.createElement('div');
    head.style.cssText = 'display:flex;align-items:center;gap:10px;margin-bottom:8px;';
    var glyph = doc.createElement('span');
    glyph.style.cssText = 'font-size:22px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.6));';
    var nm = doc.createElement('span');
    nm.style.cssText = 'font-weight:900;letter-spacing:.06em;font-size:13px;';
    var count = doc.createElement('span');
    count.style.cssText = 'margin-left:auto;font-size:11px;font-weight:700;color:#8c7d4f;letter-spacing:.04em;';
    head.appendChild(glyph); head.appendChild(nm); head.appendChild(count);

    var title = doc.createElement('div');
    title.style.cssText = 'font-weight:900;font-size:17px;color:#e8c55a;letter-spacing:.02em;margin-bottom:5px;';
    var line = doc.createElement('div');
    line.style.cssText = 'font-size:14px;line-height:1.5;color:#e8e4d6;margin-bottom:14px;';

    var btnRow = doc.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:10px;';
    var skip = doc.createElement('button');
    skip.textContent = 'Skip';
    skip.style.cssText = 'flex:1;background:none;border:1px solid rgba(201,168,76,.45);color:#b9a76a;' +
      'border-radius:10px;padding:13px 0;font-weight:700;font-size:12px;cursor:pointer;';
    skip.addEventListener('click', function (e) { e.stopPropagation(); finish(true); });
    var next = doc.createElement('button');
    next.style.cssText = 'flex:2;background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:none;' +
      'border-radius:10px;padding:13px 0;font-weight:900;font-size:14px;letter-spacing:.03em;cursor:pointer;';
    next.addEventListener('click', function (e) { e.stopPropagation(); advance(); });
    btnRow.appendChild(skip); btnRow.appendChild(next);

    card.appendChild(head); card.appendChild(title); card.appendChild(line); card.appendChild(btnRow);
    root.appendChild(ring); root.appendChild(card);
    (doc.body || doc.documentElement).appendChild(root);

    S.root = root; S.ring = ring; S.card = card;
    S.titleEl = title; S.lineEl = line; S.nameEl = nm; S.glyphEl = glyph;
    S.countEl = count; S.nextBtn = next; S.skipBtn = skip;

    S._onResize = function () { scheduleRepo(); };
    try { global.addEventListener('resize', S._onResize); } catch (_e) {}
    try { if (global.visualViewport) global.visualViewport.addEventListener('resize', S._onResize); } catch (_e) {}
  }

  function teardownDOM() {
    if (S._repo) { try { (global.cancelAnimationFrame || clearTimeout)(S._repo); } catch (_e) {} S._repo = 0; }
    if (S._onResize) {
      try { global.removeEventListener('resize', S._onResize); } catch (_e) {}
      try { if (global.visualViewport) global.visualViewport.removeEventListener('resize', S._onResize); } catch (_e) {}
      S._onResize = null;
    }
    try { if (S.root && S.root.parentNode) S.root.parentNode.removeChild(S.root); } catch (_e) {}
    S.root = S.ring = S.card = S.titleEl = S.lineEl = S.nameEl = S.glyphEl = S.countEl = S.nextBtn = S.skipBtn = null;
  }

  // ---- render the current step ---------------------------------------------
  function render() {
    var step = STEPS[S.i]; if (!step || !S.root) return;
    var who = step.who || FIXER;
    S.glyphEl.textContent = who.glyph;
    S.nameEl.textContent = who.name;
    S.nameEl.style.color = who.color || '#e8c55a';
    S.countEl.textContent = (S.i + 1) + ' / ' + STEPS.length;
    S.titleEl.textContent = step.title || '';
    S.lineEl.textContent = step.line || '';
    S.nextBtn.textContent = (S.i >= STEPS.length - 1) ? 'ENTER THE BLOCK' : 'NEXT ▸';
    positionRing();
  }

  // ---- spotlight: ring over the step's HUD chip, or flat scrim if none -----
  function positionRing() {
    if (!S.root || !S.ring) return;
    var step = STEPS[S.i] || {};
    var el = step.target ? safeGet(step.target) : null;
    var r = null;
    if (el && el.getBoundingClientRect) {
      try { r = el.getBoundingClientRect(); } catch (_e) { r = null; }
      if (r && (r.width <= 0 || r.height <= 0)) r = null; // hidden / collapsed -> no anchor
    }
    if (r) {
      var pad = 7;
      S.ring.style.display = 'block';
      S.ring.style.left = Math.max(2, r.left - pad) + 'px';
      S.ring.style.top = Math.max(2, r.top - pad) + 'px';
      S.ring.style.width = (r.width + pad * 2) + 'px';
      S.ring.style.height = (r.height + pad * 2) + 'px';
      S.root.style.background = 'transparent';          // the ring box-shadow does the darkening
    } else {
      S.ring.style.display = 'none';
      S.root.style.background = 'rgba(4,4,9,.80)';       // flat scrim, card centred
    }
  }
  function safeGet(id) { try { return doc && doc.getElementById(id); } catch (_e) { return null; } }
  function scheduleRepo() {
    if (S._repo) return;
    var raf = global.requestAnimationFrame || function (f) { return setTimeout(f, 16); };
    S._repo = raf(function () { S._repo = 0; positionRing(); });
  }

  // ---- flow -----------------------------------------------------------------
  function advance() {
    if (!S.running) return;
    if (S.i >= STEPS.length - 1) { finish(false); return; }
    S.i++; render();
  }
  function start(opts) {
    opts = opts || {};
    if (S.running || !doc) return false;
    if (coachOpen()) return false;       // never stack the walkthrough on an open coach
    if (opts.onlyIfFirstRun && isDone()) return false;
    S.running = true; S.i = 0;
    buildDOM();
    render();
    return true;
  }
  function replay() { if (!S.running) start({ replay: true }); }
  function finish(skipped) {
    if (!S.running) { teardownDOM(); return; }
    S.running = false;
    markDone();                                          // ONLY now do we touch the profile
    teardownDOM();
    banner(skipped ? "Suit yourself. Replay it from the menu when you're ready, Stray."
                   : "You know the streets now, Stray. Go run the block.", 2.6);
  }

  // ---- first-run auto-start (capped, throttled, HUD-gated) -----------------
  function hudReady() {
    try {
      var h = doc.getElementById('phud');
      if (!h) return false;
      if (h.offsetParent === null && (h.clientHeight | 0) === 0) return false; // hidden
      if (doc.getElementById('ak-ov')) return false;                           // an overlay (encounter) is up
      // one game mode at a time (operator law): never mount over the cold-open comic or the starter sequence
      try { if (typeof window !== 'undefined' && typeof window.akStoryFocus === 'function' && window.akStoryFocus()) return false; } catch (_e2) {}
      var sp = doc.getElementById('starterpanel');
      if (sp && sp.style && sp.style.display && sp.style.display !== 'none') return false;
      if (doc.getElementById('chronpanel')) return false;                       // the comic reader is up
      var intr = doc.getElementById('interior');
      if (intr && intr.style && intr.style.display && intr.style.display !== 'none') return false; // inside a building
      return true;
    } catch (_e) { return false; }
  }
  function pollAuto() {
    if (S.running || isDone()) return;                   // first-run only, never while showing
    if (orchestratorHolds()) {                           // AK-FIRSTRUN: orchestrator owns stages age..firstgame -- keep waiting, never start
      S.autoTries++;
      if (S.autoTries < 25) setTimeout(pollAuto, 600);
      return;
    }
    S.autoTries++;
    if (hudReady()) { start(); return; }
    if (S.autoTries < 25) setTimeout(pollAuto, 600);     // ~15s grace for the hub to settle
  }
  function armAutoStart() {
    if (S.armed || !doc) return;
    S.armed = true;
    setTimeout(pollAuto, 1200);
  }
  function maybeAutoStart() {                            // public: integration pass can call when hub is ready
    if (S.running || isDone() || !doc) return false;
    if (orchestratorHolds()) return false;               // AK-FIRSTRUN: never start under stages age..firstgame (orchestrator calls at hudtut)
    if (!hudReady()) return false;
    return start();
  }

  // ==========================================================================
  // FIRST-VISIT CONTEXTUAL COACH  (the #2 retention fix)
  // --------------------------------------------------------------------------
  // The linear walkthrough above teaches the loop in ORDER, once, up front. But
  // the operator's pain is bigger: "the game is deep now but players dont know
  // how to play it OR its purpose -- every unique aspect needs to explain WHY
  // its there, WHAT it does, and HOW it works."
  //
  // So: the FIRST time a player lands on any key screen, we pop a single, clear
  // explainer card -- TITLE + three labelled blocks: YOUR MOVE (the objective),
  // WHY IT'S HERE (purpose in the game), HOW IT WORKS (the mechanics, plain +
  // a little fun). Gritty-clear voice: the Fixer runs the how-to, the Old Pack
  // carries the legend/stakes. Shown ONCE per screen (p.tutSeen[screenId],
  // falsy-default so a fresh profile is byte-identical until something fires),
  // skippable, and a "turn tips off" switch (p.tutSkipTips) kills them all.
  //
  // PERFORMANCE: lazy DOM, built once, toggled on display. Zero per-frame work.
  // SAFETY: never stacks on the linear walkthrough; never throws into the host.
  // ==========================================================================

  // ---- the CONTENT TABLE: every unique aspect of the game, WHY/WHAT/HOW ------
  // who   = narrator (FIXER = how-to, OLD_PACK = legend/stakes)
  // obj   = YOUR MOVE     (what to do on this screen, one line)
  // why   = WHY IT'S HERE (the purpose this thing serves in the game)
  // how   = HOW IT WORKS  (the mechanics, plain English, a little swagger)
  // ---- AK-COACHVID 2026-07-02: cinematic header per coach screen. Reuses the
  // existing assets/cinematics/*.mp4 library (free, no new renders) mapped by
  // theme; 4 screens (world, deck, raid, story) point at bespoke NET-NEW beats
  // in assets/tutorial_mp4/ that don't exist yet -- see the render manifest in
  // the module header comment. Every path degrades on 404 via onerror in
  // buildCoach/openCoach below, so an unrendered beat never breaks the screen.
  var VISITS = {
    // ---- the top-level "what even IS this game" purpose card ----------------
    game: { who: OLD_PACK, title: 'WHAT IS ALLEY KINGZ', video: 'assets/cinematics/story_intro.mp4',
      obj: 'Rise from a nameless Stray to KING OF THE BLOCK.',
      why: "Every block in this city's got a boss, and right now it ain't you. The whole game is the climb -- you earn the crown, nobody hands it over.",
      how: 'Build your block. Defend it. Raid rival clans for their stash. Climb the ranks. Do it in whatever order you like -- the streets do not hold your paw.',
      slides: [
        { video: 'assets/cinematics/story_intro.mp4',
          obj: 'Rise from a nameless Stray to KING OF THE BLOCK.',
          why: "I'm the Old Pack, pup -- the dead legends who ran these blocks before your paws touched dirt. Every street out here answers to somebody, and right now it ain't you.",
          how: "The whole game is one long climb. You earn the crown a block at a time -- nobody's ever gonna hand it over." },
        { video: 'assets/tutorial_mp4/game.mp4',
          obj: "Build your block, then take everybody else's.",
          why: "This city runs on gold, grit, and the size of your pack. Sit still and a rival clan eats your turf while you sleep.",
          how: "Grow your block, work your dogs, raid the crews around you for their stash. Do it in any order -- the streets don't hold your paw." },
        { video: 'assets/cinematics/win.mp4',
          obj: 'Climb until they call you KING OF THE BLOCK.',
          why: "The Mongrel King -- the Dog That Eats Names -- wears the crown you're owed. That's the whole story, pup. Take it off him.",
          how: "Every win moves you up the ranks. Stack enough and the crown is yours. Now go learn how we survive out here." }
      ] },

    // ---- the world / hub + movement -----------------------------------------
    world: { who: FIXER, title: 'THE BLOCK', video: 'assets/tutorial_mp4/world.mp4',    // NET-NEW: cold-open "welcome to the block"
      obj: 'Walk your turf and tap whatever catches your eye.',
      why: "This is home -- where you build, harvest, put your pack to work, and launch every job from. Learn it before somebody tries to take it out from under you.",
      how: 'Drag anywhere to walk, or tap H J K L on keys. Walk up to a building to step inside. Those chips up top are your shortcuts to everything on the block.',
      slides: [
        { video: 'assets/tutorial_mp4/world.mp4',
          obj: 'Walk your turf and tap whatever catches your eye.',
          why: "Name's Marrow, I run the jobs round here. This block is home -- where you build, harvest, and kick off every job you take.",
          how: "Drag anywhere to walk, or tap H J K L on keys. Get a feel for the streets before somebody tries to take em out from under you." },
        { video: 'assets/cinematics/transition_wipe.mp4',
          obj: 'Walk up to a building and step inside.',
          why: "Every door on this block does a job for you -- crops, scrap, gold, tools. The block only pays the dog that works it.",
          how: "Get close to a building and it lets you in. Inside is where you put a dog on it and pull what it owes you." },
        { video: 'assets/cinematics/chest_open.mp4',
          obj: 'Use the chips up top to jump anywhere fast.',
          why: "The block runs deep, mutt. Those shortcuts keep you from hoofin it across town for every little thing.",
          how: "Each chip up top drops you straight into a system -- your pack, the Fence, the Watch, your rank. Learn em, use em, move quick." }
      ] },

    // ---- the 11-card deck + assigning by trait/faction ----------------------
    deck: { who: FIXER, title: 'YOUR PACK', video: 'assets/tutorial_mp4/deck.mp4',       // NET-NEW: "this is your deck"
      obj: 'Put the right dog on the right job.',
      why: 'Your 11 cards ARE your crew -- they run every building on the block. A building with no dog on it runs on a no-name keeper and pays you scraps.',
      how: "Match a dog's TRAIT and FACTION to the building -- Zoomie Syndicate, Leashbreak Tactix, Boneguard Crew, K9 Circuitry. Right fit pays fat, wrong fit pays thin. Swap any time.",
      slides: [
        { video: 'assets/tutorial_mp4/deck.mp4',
          obj: 'Meet your pack -- 11 cards, your whole crew.',
          why: "These dogs ARE your labor. Every building on the block runs on one of em, and a spot with no dog runs on a no-name keeper for scraps.",
          how: "Tap through your 11 and learn what each one is built for. Their trait and their faction is the whole game." },
        { video: 'assets/cinematics/mission_accept.mp4',
          obj: 'Put the right dog on the right job.',
          why: "Fit is everything out here. Match trait and faction to the building -- Zoomie Syndicate, Leashbreak Tactix, Boneguard Crew, K9 Circuitry -- and it pays fat.",
          how: "Walk into a building, tap ASSIGN, drop your best-fit dog on it. Wrong fit still works, it just pays you thin." },
        { video: 'assets/cinematics/trade_done.mp4',
          obj: 'Swap your lineup whenever the job changes.',
          why: "You ain't locked in, pup. The block shifts, and a dog that's wasted on one spot is gold on another.",
          how: "Pull any dog off and slot it where it pays better. Keep tuning the pack -- that's how the sharp ones stay fed." }
      ] },

    // ---- the Town Hall: the master switch -----------------------------------
    townhall: { who: FIXER, title: 'THE TOWN HALL', video: 'assets/cinematics/ks_gold.mp4',
      obj: 'Pump the Town Hall with gold every chance you get.',
      why: 'It is the master of the whole block -- it caps how many BUILDINGS you run, how many BUILDERS you got, and how high your pack can level. Nothing grows past what the Town Hall allows.',
      how: 'Tap UPGRADE to spend gold and raise the level -- every level lifts all three caps at once. Keep it strong: a raid that cracks it drops your whole deck a level.' },

    // ---- the builders / the Foreman -----------------------------------------
    builders: { who: FIXER, title: 'THE BUILDERS', video: 'assets/cinematics/transition_wipe.mp4',
      obj: 'Put your builders to work raising the block.',
      why: "Buildings don't raise themselves -- builders do the labor. More builders means more you can put up and upgrade at the same time.",
      how: 'Open the Foreman, drop a dog into a build slot, and set it to work. The Town Hall caps how many slots you get, so upgrade it to grow your crew.' },

    // ---- inside a building ---------------------------------------------------
    interior: { who: FIXER, title: 'INSIDE THE SPOT', video: 'assets/cinematics/transition_glitch.mp4',
      obj: 'Meet the keeper, assign a dog, collect what is owed.',
      why: 'Every building does a job for the block -- crops, scrap, gold, tools. Stepping inside is how you work it and pull the payout.',
      how: 'Tap ASSIGN DOG to put one of your pack on this spot, then hit the action to run it. Come back later and collect what it earned.' },

    // ---- the Fence (market: barter, floating prices, laundering) ------------
    fence: { who: FIXER, title: 'THE FENCE', video: 'assets/cinematics/chest_open.mp4',
      obj: 'Turn your crops and scrap into cold gold.',
      why: "Goods don't spend -- gold does. The Fence is where the block cashes out, and where anything you took in a raid gets laundered clean before you can use it.",
      how: 'Prices float with the streets -- sell when they run high, barter the keeper down when you buy. Every district moves its own product, so shop around.' },

    // ---- the Hit List / missions --------------------------------------------
    hitlist: { who: FIXER, title: 'THE HIT LIST', video: 'assets/cinematics/story_ch1.mp4',
      obj: 'Take a job, go do it, bring the proof back.',
      why: 'Jobs are steady money -- gold, scrap, keys and bones -- and the fastest way to learn the city while your pockets fill.',
      how: 'Grab one from Marrow the Fixer, travel to where it points, do the deed, then turn it in for the payout. Fresh bounties drop daily, so check back.' },

    // ---- wild encounters -> a card copy -------------------------------------
    encounter: { who: FIXER, title: 'A WILD STRAY', video: 'assets/cinematics/win.mp4',
      obj: 'Win the face-off to add the stray to your pack.',
      why: 'Wild strays are free dogs -- one of only three ways to grow your pack (the others are the Town Hall and the Shop).',
      how: 'Read it, wear it down, then leash it when its guard drops. Beat it and you keep a COPY of that card. Mercy or strike is your call -- it shapes your karma.' },

    // ---- the raid map --------------------------------------------------------
    raidmap: { who: OLD_PACK, title: 'THE RAID MAP', video: 'assets/cinematics/ks_supreme.mp4',
      obj: 'Scout a rival block and pick a target worth hitting.',
      why: 'Other clans are sitting on stashes of gold and goods. The map is how you find their turf and decide who eats tonight.',
      how: "Each marker's another crew's block -- size up their strength, then send your pack in. Stronger targets guard fatter loot, and every hit burns STAMINA." },

    // ---- the raid itself (RPG, not the tower lane) --------------------------
    raid: { who: OLD_PACK, title: 'THE RAID', video: 'assets/tutorial_mp4/raid.mp4',     // NET-NEW: "raid the enemy crown"
      obj: 'Break their wall, beat their pack, haul off the loot.',
      why: "This ain't the tower lane. Out on the world map your 11 dogs fight RPG-style, paw to paw. Win and you walk with their stash. Lose and your dogs limp home hurt.",
      how: 'Your pack goes in and trades blows -- crack the wall, then drop the defenders. Any dog that falls goes down wounded and heads for the Infirmary. Hit harder than they can hold.',
      slides: [
        { video: 'assets/tutorial_mp4/raid.mp4',
          obj: 'Break their wall, beat their pack, haul off the loot.',
          why: "A raid ain't the tower lane, pup. Out on the world map your 11 dogs fight paw to paw, RPG-style.",
          how: "You send the pack in and they trade blows. Crack the wall first, then drop the crew posted behind it." },
        { video: 'assets/cinematics/win.mp4',
          obj: 'Hit harder than they can hold.',
          why: "Win and you walk off with their whole stash -- gold, goods, whatever they were sitting on.",
          how: "Strength on strength. Bring more than they got on the wall and it comes down. Bring too little and your dogs limp home hurt." },
        { video: 'assets/cinematics/chest_open.mp4',
          obj: 'Launder the haul, patch the wounded, run it back.',
          why: "Loot don't spend raw, and a hurt dog can't fight. Every raid takes something out of you before it pays.",
          how: "Run the stash through the Fence to clean it, send the fallen to the Infirmary to heal, and mind your STAMINA -- every hit burns it." }
      ] },

    // ---- the Infirmary -------------------------------------------------------
    infirmary: { who: FIXER, title: 'THE INFIRMARY', video: 'assets/cinematics/lose.mp4',
      obj: 'Heal your downed dogs before you field them again.',
      why: "A dog that falls in a raid don't just shake it off. Wounded dogs can't fight -- and a thin pack loses the next scrap.",
      how: 'Send the hurt ones here to heal over time, or pay to patch em up fast. Your pack is not disposable -- keep em breathing and they bleed for you.' },

    // ---- the Watch (defense) + fortify (wood/stone) -------------------------
    watch: { who: OLD_PACK, title: 'THE WATCH', video: 'assets/cinematics/ks_doggod.mp4',
      obj: 'Fortify your district and post your defenders.',
      why: 'A soft block gets raided in its sleep -- and a raid that lands cracks your Town Hall and drops your deck a level. The Watch is how you keep what is yours.',
      how: 'Spend WOOD and STONE to fortify, set your layout, and post your toughest dogs on the wall. The harder you build, the more it costs them to break in.' },

    // ---- farming / crops -----------------------------------------------------
    farming: { who: FIXER, title: 'WORK THE LAND', video: 'assets/cinematics/transition_wipe.mp4',
      obj: 'Grab your tools, plant, wait, and harvest.',
      why: "Crops are the block's lifeblood -- trade em at the Fence for gold or burn em on jobs. Free product, long as you put the work in.",
      how: 'Buy TOOLS, plant a plot, give it time to grow, then harvest. Wood and stone come off the trees and the rubble the same way -- no tools, no work, mutt.' },

    // ---- the Ladder + Block Rep + monthly reset + season exclusive ----------
    ladder: { who: OLD_PACK, title: 'THE LADDER', video: 'assets/cinematics/ks_gold.mp4',
      obj: 'Climb the ranks and stack Block Rep.',
      why: "The ladder is the scoreboard for the whole city -- it's how you prove you're rising from Stray toward King of the Block.",
      how: 'Win fights and hold turf to earn Block Rep. The board wipes every month -- climb high before the reset and you walk off with that season\'s exclusive reward.' },

    // ---- daily streak + raid stamina ----------------------------------------
    streak: { who: FIXER, title: 'SHOW UP DAILY', video: 'assets/cinematics/chest_open.mp4',
      obj: 'Log in every day. Spend stamina to raid.',
      why: 'Loyalty pays -- a daily streak stacks bigger rewards the longer you keep it. Stamina keeps raiding from turning into mindless spam.',
      how: 'Come back each day to grow the streak and claim the drop. Every raid burns STAMINA, and it refills over time -- so pick your hits, don\'t blow it all at once.' },

    // ---- day / night + weather ----------------------------------------------
    daynight: { who: OLD_PACK, title: 'DAY, NIGHT + WEATHER', video: 'assets/cinematics/transition_wipe.mp4',
      obj: 'Read the sky -- it changes the streets.',
      why: 'The block lives on a clock. Night and rough weather shift who is out, what spawns, and how the turf feels under your paws.',
      how: 'Time and weather roll on their own. Some strays and some jobs only show in certain conditions -- keep your eyes open right across the cycle.' },

    // ---- the Crown Bloodline story ------------------------------------------
    story: { who: OLD_PACK, title: 'THE CROWN BLOODLINE', video: 'assets/tutorial_mp4/story.mp4', // NET-NEW: "you're a king now" finale
      obj: 'Follow the story to your next move.',
      why: "You're the latest blood in a line of legends -- the Crown Bloodline. The Mongrel King, the Dog That Eats Names, wears the crown you are owed.",
      how: 'Tap STORY any time and I point you at what is next. Every win you stack carves another notch toward the day you take his crown.',
      slides: [
        { video: 'assets/cinematics/story_intro.mp4',
          obj: 'Follow the Crown Bloodline to your next move.',
          why: "You're the latest blood in a line of legends, pup. That line is the Crown Bloodline, and it runs straight through you.",
          how: "Tap STORY any time and I'll point you at what comes next." },
        { video: 'assets/cinematics/story_ch1.mp4',
          obj: 'Learn who wears the crown you are owed.',
          why: "The Mongrel King -- the Dog That Eats Names -- holds this whole city. He took what should have been ours.",
          how: "Every chapter I tell you gets you a step closer to his block. Keep coming back and the whole tale opens up." },
        { video: 'assets/tutorial_mp4/story.mp4',
          obj: 'Take his crown and end the line on top.',
          why: "Every legend before you fell short. You're the one who finishes it -- King of the Block, the dog that eats HIS name.",
          how: "Stack your wins, hold your turf, and when you're strong enough the story marches you to his door. Go earn it, pup." }
      ] },

    // ---- the economy overall -------------------------------------------------
    economy: { who: FIXER, title: 'HOW THE MONEY MOVES', video: 'assets/cinematics/ks_gold.mp4',
      obj: 'Know what every currency does before you spend it.',
      why: 'The block feeds itself -- crops and scrap become gold, gold builds and levels you up, a strong block raids for more. One loop, round and round.',
      how: 'GOLD builds and upgrades. WOOD and STONE fortify. CROPS and SCRAP trade at the Fence. GEMS only skip waits and buy looks -- never power, never a shortcut past the grind. Earn it all by playing.' },

    // ---- districts + turf control -------------------------------------------
    districts: { who: OLD_PACK, title: 'THE DISTRICTS', video: 'assets/cinematics/ks_supreme.mp4',
      obj: 'Hold turf and raise your standing in each district.',
      why: 'The city is carved into districts, each one ran by a faction. Whose turf you stand on changes the jobs, the prices, and the strays you meet.',
      how: 'Work a district, run its buildings, and help its people to raise your karma there -- friendlier streets, better deals, and turf that backs you when the raids come.' },

    // ==== AK-LIVINGMANGA 2026-07-09 (bible 10.5): the living-manga layer -------
    // Four new coach screens for the Section 10/11 systems. Same slides[] pager,
    // same dog-talking voice, EXISTING cinematics/tutorial_mp4 clips only (zero
    // net-new renders). Canon names only: gold/gems/bones/produce, the Fence,
    // the Mongrel King. Triggers: 'needs' + 'chronicle_choices' auto-wire below
    // (armVisitHooks); 'starter' + 'fence_lore' are replay-reachable and wait on
    // their flow owners to call AK_TUTORIAL.firstVisit(id) at the right beat.

    // ---- the living runner: hunger / energy / morale / honor (bible 10.1) ---
    needs: { who: FIXER, title: 'YOUR RUNNER IS ALIVE', video: 'assets/cinematics/trade_done.mp4',
      obj: 'Feed him, rest him, keep his name good on the block.',
      why: "Your runner ain't a token on a board -- he's a living dog. Hungry, tired, lonely or shamed, he fights like it. The comic pages read his state too.",
      how: 'Feed him PRODUCE off the farm. Let his energy refill between runs. Wins, chats and held turf keep his morale and his honor up. Let any of it rot and he gets worse.',
      slides: [
        { video: 'assets/cinematics/trade_done.mp4',
          obj: 'Keep your runner FED -- produce is dog food out here.',
          why: "A starving runner hits soft in a raid, and desperate choices start looking good to him. That's the farm's whole reason to exist, mutt.",
          how: "Grow produce, then put it in his bowl. Hunger drains slow, PT-day by PT-day -- a fed dog fights at full teeth." },
        { video: 'assets/cinematics/transition_wipe.mp4',
          obj: 'Let him REST -- energy is the same stamina every raid burns.',
          why: "An exhausted dog can't sprint and his lines shake on the page. Nobody runs the block on empty.",
          how: "Energy refills with time; bones can hurry it along. Pick your hits instead of blowing every run at once." },
        { video: 'assets/cinematics/watch_posted.mp4',
          obj: 'Guard his MORALE and his HONOR -- the block is watching.',
          why: "A lonely dog misses swings. A dishonored one gets worse prices and allies that hesitate. Keep him thriving and the manga pages shine gold.",
          how: "Morale feeds on chats, play and crew wins. Honor is your Block Rep -- wins, held defenses, duties done. Same dog, different legend." }
      ] },

    // ---- choice panels in the comic reader (bible 10.3) ---------------------
    chronicle_choices: { who: OLD_PACK, title: 'YOUR CHOICES INK THE STORY', video: 'assets/cinematics/story_ch1.mp4',
      obj: 'When a page offers you a choice, pick like it counts.',
      why: 'The chronicle remembers. Every pick you make gets inked into the record and pays off in later issue runs.',
      how: 'Some options only unlock in the right state -- starving opens desperate lines, honor opens authority. And your pick follows you into the next fight.',
      slides: [
        { video: 'assets/cinematics/story_ch1.mp4',
          obj: 'When a page offers you a choice, pick like it counts.',
          why: "The chronicle remembers, pup. Every pick gets inked into the record, and the ink don't wash out -- it pays off issues later.",
          how: "Read the beat, weigh the options, tap one. An answered page never asks again." },
        { video: 'assets/cinematics/story_intro.mp4',
          obj: 'Watch for lines only YOUR state can speak.',
          why: "The page reads the dog reading it. A starving runner sees desperate lines; an honored one gets to talk like authority.",
          how: "Locked options show dimmed with what they need -- hunger, morale, honor. Live right and the story opens wider." },
        { video: 'assets/cinematics/win.mp4',
          obj: 'Carry the choice into your next fight.',
          why: "A choice ain't just words -- rage, tactics or a lucky bone rides with you into the next battle.",
          how: "Pick rage and your pack hits harder while their dogs come in tougher. Pick tactical and their weakness gets marked. Pick the odd one and see what shakes loose." }
      ] },

    // ---- the handler + starter moment, for NEW players post-starter (11.1) --
    starter: { who: OLD_PACK, title: 'THE HANDLER AND THE FIRST DOG', video: 'assets/cinematics/mission_accept.mp4',
      obj: 'Your handler frames your climb. Your starter runs it.',
      why: "Something big moved on the rooftops the night you signed on -- nobody out here says its name. You picked a handler; the handler picked back.",
      how: 'Your handler is your commander and your teacher -- the authority on awakening your dogs. The starter they handed you is your first RUNNER: feed him, rest him, keep him alive.',
      slides: [
        { video: 'assets/cinematics/mission_accept.mp4',
          obj: 'Your handler is your commander -- learn their game.',
          why: "You picked one of the block's six handlers, and that choice frames how you fight. They're the authority on awakening your dogs, pup.",
          how: "Your handler's kit rides every match -- their special fires from the badge. Listen when they talk; the streets taught them first." },
        { video: 'assets/cinematics/story_intro.mp4',
          obj: 'Your starter is your first RUNNER. Keep him breathing.',
          why: "That dog they handed you ain't a card -- he's the one who walks your turf, runs your raids, and carries your name on the page.",
          how: "He lives like you do: feed him produce, let him rest, keep his honor up. His state follows him into every panel and every fight." },
        { video: 'assets/cinematics/lose.mp4',
          obj: 'Remember the pup who beat you to the choice.',
          why: "A pup from YOUR alley got to the handler first and took the counter to your starter. That grudge don't expire -- the block tracks it forever.",
          how: "Win or lose against your rival, the story adapts. Every rematch is a page. Settle it a fight at a time." }
      ] },

    // ---- money is lore: gold / gems / bones + the Fence's stock (10.4) ------
    fence_lore: { who: FIXER, title: 'MONEY IS A STORY HERE', video: 'assets/cinematics/ks_gold.mp4',
      obj: 'Know what each coin SAYS before you spend it.',
      why: "Out here money ain't numbers -- it's reputation you can carry. A heavy chest changes how the block draws you; a broke week roughs up your edges.",
      how: 'GOLD is street money -- earn it, spend it, let it talk. GEMS only skip waits and buy looks, never power. BONES are trust -- soulbound, earned, never sold.',
      slides: [
        { video: 'assets/cinematics/ks_gold.mp4',
          obj: 'GOLD is street money -- every big earn is a story beat.',
          why: "The chest was heavy. Good. Wealth puts gold in your panels; broke puts rough borders on em. The block draws you the way you live, mutt.",
          how: "Work the buildings, run the jobs, raid the crews. Big earns and big spends get stamped into the chronicle." },
        { video: 'assets/cinematics/chest_open.mp4',
          obj: 'GEMS buy looks and skip waits. BONES buy nothing -- they ARE you.',
          why: "Gems never buy power -- that's law on this block, always has been. And bones? Bones are trust. Soulbound. No dog can sell what the streets gave him.",
          how: "Spend gems on style and speed, never strength. Earn bones by showing up -- they mark how deep the block trusts you." },
        { video: 'assets/cinematics/trade_done.mp4',
          obj: "Shop the Fence like it's a place, cause it is.",
          why: "The Fence has a keeper, a history, and stock it don't show strangers. Some goods only surface when your story's earned em.",
          how: "Lore-locked stock sits dimmed till your chapters and your rep unlock it. Come back as your legend grows -- the shelves grow with you." }
      ] },

    // ==== AK-MANGA-TUT 2026-07-09 (bible 8.1 / 9.3): raids, defense, crews -----
    // Three more dog-talking coach storylines, EXISTING clips ONLY (zero net-new
    // renders; every path already ships in assets/cinematics + assets/tutorial_mp4).
    // Triggers (armVisitHooks below): 'raid_bases' rides akOpenRaidMap and
    // 'defense_posts' rides akOpenGuard -- the index.html AK-FIRSTVISIT wiring
    // teaches 'raidmap'/'watch' on the FIRST open, so these land on the NEXT open
    // (firstVisit never stacks two coaches). 'factions' fires off the first
    // recruiter-job accept (mission_active.js calls firstVisit('factions')).
    // All three stay replay-reachable via AK_TUTORIAL.show / AK_TUTORIAL.screens.

    // ---- world-map raids: scout, break the core, the bag comes home ----------
    raid_bases: { who: OLD_PACK, title: 'RAID THEIR BASES', video: 'assets/cinematics/ks_supreme.mp4',
      obj: 'Scout a base, break its core, walk the bag home.',
      why: "Every crew on the world map is sitting on a stash, pup. Raiding their bases is how a small block eats big.",
      how: 'Pick a target off the raid map, crack the core their whole base leans on, and haul the loot home before your dogs give out.',
      slides: [
        { video: 'assets/cinematics/ks_supreme.mp4',
          obj: 'SCOUT before you swing -- read the base first.',
          why: "Old heads never hit blind, pup. Every marker on that map is a crew with a wall, a pack, and a stash behind both.",
          how: "Open the raid map and size em up. Strength on the wall means fatter loot behind it -- pick a fight your pack can finish." },
        { video: 'assets/tutorial_mp4/raid.mp4',
          obj: 'BREAK THE CORE -- that is the whole job.',
          why: "A base don't fall wall by wall. It falls when the core it leans on cracks. Everything else is just teeth in your way.",
          how: "Your 11 fight paw to paw on the world map, RPG-style, no tower lane. Punch through the defenders and put the core in the dirt." },
        { video: 'assets/cinematics/chest_open.mp4',
          obj: 'THE BAG COMES HOME -- or the raid meant nothing.',
          why: "Loot on their floor ain't yours yet, mutt. The Old Pack only counts what makes it back to your block.",
          how: "Win and the stash rides home with you -- launder it through the Fence, send the wounded to the Infirmary, then run it back." }
      ] },

    // ---- the 4 defense posts + the shield ladder + the LAST NIGHT report -----
    defense_posts: { who: OLD_PACK, title: 'THE DEFENSE POSTS', video: 'assets/cinematics/watch_posted.mp4',
      obj: 'Man the posts, climb the shield ladder, read LAST NIGHT.',
      why: "While you sleep, somebody's testing your fence, pup. The posts are the dogs that answer for you.",
      how: 'Post your hardest on the 4 defense posts, buy a shield when you need to breathe, and read the LAST NIGHT report every dawn.',
      slides: [
        { video: 'assets/cinematics/watch_posted.mp4',
          obj: 'MAN THE POSTS -- 4 posts, your 4 hardest dogs.',
          why: "An empty post is an open door. The BLOCK WAR gets won by whoever's standing on the line when the hit comes.",
          how: "Open THE WATCH and drop a dog on each post. One dog, one post -- pull em, swap em, keep the line whole." },
        { video: 'assets/cinematics/ks_doggod.mp4',
          obj: 'CLIMB THE SHIELD LADDER when you need to breathe.',
          why: "Even kings sleep, pup. A shield buys the block quiet hours no raider can touch.",
          how: "Five rungs, each one longer: Street Cover, Crew Watch, Iron Curtain, Fortress Dome, and the Panic Button for when it all goes wrong." },
        { video: 'assets/cinematics/lose.mp4',
          obj: 'READ LAST NIGHT -- the block reports at dawn.',
          why: "What happened while you slept is already history, but history's got lessons in it. The report don't lie.",
          how: "LAST NIGHT lists every hit your posts took -- who held, who folded, what walked off. Read it, then fix the hole they came through." }
      ] },

    // ---- the four crews: one beat per crew, the S8.1 doctrine lines ----------
    factions: { who: OLD_PACK, title: 'THE FOUR CREWS', video: 'assets/cinematics/ks_gold.mp4',
      obj: 'Know whose colors run each block before you work it.',
      why: "Four crews carved up this city, pup, and every one is a different answer to the same question: every leash breaks -- who holds the crown when it does?",
      how: 'Boneguard Crew, Zoomie Syndicate, Leashbreak Tactix, K9 Circuitry. Work their turf, run their jobs, earn their karma -- but learn their doctrine first.',
      slides: [
        { video: 'assets/cinematics/ks_gold.mp4', title: 'BONEGUARD CREW',
          obj: 'BONEGUARD CREW -- the Rusted, out of FACTORY ROW.',
          why: "Their whole doctrine, pup: the pack IS the crown. No dog above the crew, no crown above the pack.",
          how: "Scrap, forge and rust-gold muscle. Haul for the Rusted, hold the line beside em, and they start counting you as kin." },
        { video: 'assets/cinematics/transition_wipe.mp4', title: 'ZOOMIE SYNDICATE',
          obj: 'ZOOMIE SYNDICATE -- the Unbound, off THE STRIP.',
          why: "Their answer is speed: outrun the leash. Nothing holds a dog the block can't catch.",
          how: "Commerce, the come-up, the strip lights. Run their jobs quick and clean -- the Unbound pay for fast paws." },
        { video: 'assets/cinematics/transition_glitch.mp4', title: 'LEASHBREAK TACTIX',
          obj: 'LEASHBREAK TACTIX -- the Hologhosts, up in NEON HEIGHTS.',
          why: "Their creed cuts hardest: cut every leash on principle. Any collar, any hand, any time.",
          how: "Ghosts, static and wire. Earn their trust and the Hologhosts open doors nobody else even sees." },
        { video: 'assets/cinematics/upgrade_done.mp4', title: 'K9 CIRCUITRY',
          obj: 'K9 CIRCUITRY -- the Crowned, holding THE DOCKS.',
          why: "The coldest answer of the four: become the system that holds the leashes. Don't break the game, own it.",
          how: "Circuits, grids and voltage. Stack karma with the Crowned and they plug you into jobs the street never hears about." }
      ] }
  };

  // ---- coach state + persistence (p.tutSeen[id], p.tutSkipTips) -------------
  var C = { root: null, glyph: null, name: null, tag: null, titleEl: null,
            objEl: null, whyEl: null, howEl: null, id: null, vidEl: null,
            gotBtn: null, offBtn: null, i: 0, slides: null, item: null };

  function getSeen() {
    try { var e = econ(); var p = e && e.loadProfile && e.loadProfile(); var t = p && p.tutSeen;
      return (t && typeof t === 'object') ? t : {}; } catch (_e) { return {}; }
  }
  function isSeen(id) { var t = getSeen(); return !!(t && t[id]); }
  function markSeen(id) {
    try { var e = econ(); if (e && e.mutateProfile) e.mutateProfile(function (p) {
      if (!p.tutSeen || typeof p.tutSeen !== 'object') p.tutSeen = {};
      p.tutSeen[id] = 1;
    }); } catch (_e) {}
  }
  function tipsOff() {
    try { var e = econ(); var p = e && e.loadProfile && e.loadProfile(); return !!(p && p.tutSkipTips); }
    catch (_e) { return false; }
  }
  function setTipsOff() {
    try { var e = econ(); if (e && e.mutateProfile) e.mutateProfile(function (p) { p.tutSkipTips = 1; }); }
    catch (_e) {}
  }
  function clearVisits() {   // dev/testing: forget every first-visit + re-enable tips
    try { var e = econ(); if (e && e.mutateProfile) e.mutateProfile(function (p) {
      try { delete p.tutSeen; } catch (_x) { p.tutSeen = null; }
      try { delete p.tutSkipTips; } catch (_y) { p.tutSkipTips = 0; }
    }); } catch (_e) {}
  }

  // ---- build the coach overlay (lazy, once) --------------------------------
  function buildCoach() {
    if (!doc || C.root) return;
    ensureStyle();   // reuses the ak-tut-rise keyframe

    var root = doc.createElement('div');
    root.id = 'ak-tut-coach';
    root.style.cssText = 'position:fixed;inset:0;z-index:9100;display:none;' +
      'background:rgba(4,4,9,.82);align-items:center;justify-content:center;padding:18px;' +
      'box-sizing:border-box;touch-action:none;font-family:Inter,system-ui,Segoe UI,sans-serif;' +
      '-webkit-tap-highlight-color:transparent;';
    root.addEventListener('click', function () { closeCoach(); }); // tap scrim -> dismiss

    var card = doc.createElement('div');
    card.id = 'ak-tut-coach-card';
    card.style.cssText = 'position:relative;width:min(540px,94vw);max-height:88vh;overflow:auto;' +
      '-webkit-overflow-scrolling:touch;box-sizing:border-box;' +
      'background:linear-gradient(168deg,#15110a,#0b0a06);border:1.5px solid rgba(201,168,76,.55);' +
      'border-radius:18px;padding:18px 18px 16px;box-shadow:0 18px 48px rgba(0,0,0,.66),0 0 34px rgba(232,197,90,.18);' +
      'animation:ak-tut-rise .22s ease-out;';
    card.addEventListener('click', function (e) { e.stopPropagation(); }); // card taps never dismiss

    var head = doc.createElement('div');
    head.style.cssText = 'display:flex;align-items:center;gap:10px;margin-bottom:10px;';
    var glyph = doc.createElement('span');
    glyph.style.cssText = 'font-size:24px;line-height:1;filter:drop-shadow(0 1px 2px rgba(0,0,0,.6));';
    var nm = doc.createElement('span');
    nm.style.cssText = 'font-weight:900;letter-spacing:.06em;font-size:12px;';
    var tag = doc.createElement('span');
    tag.textContent = 'FIRST LOOK';
    tag.style.cssText = 'margin-left:auto;font-size:10px;font-weight:800;color:#8c7d4f;letter-spacing:.12em;' +
      'border:1px solid rgba(201,168,76,.35);border-radius:999px;padding:3px 9px;';
    head.appendChild(glyph); head.appendChild(nm); head.appendChild(tag);

    // AK-COACHVID 2026-07-02: cinematic banner, muted/loop/autoplay/playsinline
    // (same <video> pattern as index.html's story panel + shop.js chestStinger).
    // onerror hides itself -- a not-yet-rendered NET-NEW beat degrades to no
    // banner at all, never a broken image or a blocked coach card.
    var vid = doc.createElement('video');
    vid.id = 'ak-tut-coach-vid';
    vid.muted = true; vid.loop = true; vid.autoplay = true; vid.playsInline = true;
    vid.setAttribute('muted', ''); vid.setAttribute('loop', ''); vid.setAttribute('autoplay', '');
    vid.setAttribute('playsinline', '');
    vid.style.cssText = 'display:none;width:100%;max-height:220px;object-fit:cover;' +
      'border-radius:11px;margin:0 0 11px;background:#000;';
    vid.onerror = function () { vid.style.display = 'none'; };

    var title = doc.createElement('div');
    title.style.cssText = 'font:900 21px/1.15 "Playfair Display",Georgia,serif;color:#e8c55a;' +
      'letter-spacing:.01em;margin-bottom:13px;';

    function block(label, color) {
      var wrap = doc.createElement('div');
      wrap.style.cssText = 'margin-bottom:12px;';
      var lab = doc.createElement('div');
      lab.textContent = label;
      lab.style.cssText = 'font-size:10px;font-weight:900;letter-spacing:.14em;color:' + color + ';margin-bottom:3px;';
      var body = doc.createElement('div');
      body.style.cssText = 'font-size:14px;line-height:1.5;color:#e8e4d6;';
      wrap.appendChild(lab); wrap.appendChild(body);
      return { wrap: wrap, body: body };
    }
    var bObj = block('YOUR MOVE', '#7CFFb0');     // green -- the action
    var bWhy = block("WHY IT'S HERE", '#ffd76b');  // gold  -- the purpose
    var bHow = block('HOW IT WORKS', '#7fc8ff');   // cyan  -- the mechanics

    var btnRow = doc.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:10px;margin-top:4px;';
    var off = doc.createElement('button');
    off.textContent = 'Turn tips off';
    off.style.cssText = 'flex:1;background:none;border:1px solid rgba(201,168,76,.4);color:#b9a76a;' +
      'border-radius:11px;padding:13px 0;font-weight:700;font-size:12px;cursor:pointer;';
    // left slot doubles as a BACK pager when C.i>0 (see renderSlide); else "turn tips off"
    off.addEventListener('click', function (e) {
      e.stopPropagation();
      if ((C.i | 0) > 0) { C.i--; renderSlide(); return; }   // BACK -- step to the previous beat
      setTipsOff(); closeCoach();                             // first beat -- kill all tips
    });
    var got = doc.createElement('button');
    got.textContent = 'GOT IT';
    got.style.cssText = 'flex:2;background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:none;' +
      'border-radius:11px;padding:13px 0;font-weight:900;font-size:14px;letter-spacing:.04em;cursor:pointer;';
    // primary slot pages NEXT while beats remain, else GOT IT (closeCoach -> markSeen)
    got.addEventListener('click', function (e) {
      e.stopPropagation();
      var n = (C.slides && C.slides.length) || 1;
      if ((C.i | 0) < n - 1) { C.i++; renderSlide(); return; }  // NEXT -- keep the panel open
      closeCoach();                                             // last beat -- GOT IT
    });
    btnRow.appendChild(off); btnRow.appendChild(got);

    card.appendChild(head); card.appendChild(vid); card.appendChild(title);
    card.appendChild(bObj.wrap); card.appendChild(bWhy.wrap); card.appendChild(bHow.wrap);
    card.appendChild(btnRow);
    root.appendChild(card);
    (doc.body || doc.documentElement).appendChild(root);

    C.root = root; C.glyph = glyph; C.name = nm; C.tag = tag; C.titleEl = title;
    C.objEl = bObj.body; C.whyEl = bWhy.body; C.howEl = bHow.body; C.vidEl = vid;
    C.gotBtn = got; C.offBtn = off;
  }

  function coachOpen() { return !!(C.root && C.root.style.display && C.root.style.display !== 'none'); }

  function lookupVisit(id, info) {
    var base = VISITS[id] || null;
    if (!base && !info) return null;
    info = info || {};
    return {
      id: id,
      who: info.who || (base && base.who) || FIXER,
      title: info.title || (base && base.title) || '',
      video: info.video || (base && base.video) || '',   // optional cinematic header, see VISITS
      obj: info.obj || (base && base.obj) || '',
      why: info.why || (base && base.why) || '',
      how: info.how || (base && base.how) || '',
      slides: info.slides || (base && base.slides) || null  // optional multi-beat storyline, see VISITS
    };
  }

  // AK-COACHSTORY 2026-07-03: a coach entry can carry a `slides` array of beats
  // ({video,obj,why,how[,title]}) so one screen becomes a mini storyline -- a dog
  // talks, you tap NEXT to the next MP4 + tidbit, then a third. A flat (no-slides)
  // entry is normalized to a single beat so its behavior is byte-identical to
  // before. renderSlide paints the current beat and swaps the pager exactly like
  // the STEPS flow (counter (i+1)/n, NEXT while beats remain, else GOT IT).
  function renderSlide() {
    if (!C.root) return;
    var slides = (C.slides && C.slides.length) ? C.slides : [{}];
    var n = slides.length;
    var i = C.i | 0; if (i < 0) i = 0; if (i > n - 1) i = n - 1; C.i = i;
    var sl = slides[i] || {};
    var base = C.item || {};
    C.titleEl.textContent = sl.title || base.title || '';
    C.objEl.textContent = sl.obj || '';
    C.whyEl.textContent = sl.why || '';
    C.howEl.textContent = sl.how || '';
    var v = sl.video || '';
    if (v && C.vidEl) {                          // per-beat cinematic -- onerror hides it if 404
      C.vidEl.style.display = 'block';
      C.vidEl.src = v;
      try { C.vidEl.play().catch(function () {}); } catch (_e) {}
    } else if (C.vidEl) {
      C.vidEl.style.display = 'none';
      try { C.vidEl.pause(); } catch (_e) {}
      C.vidEl.removeAttribute('src');
    }
    if (C.tag) C.tag.textContent = (n > 1) ? ((i + 1) + ' / ' + n) : 'FIRST LOOK';
    if (C.gotBtn) C.gotBtn.textContent = (i < n - 1) ? 'NEXT ▸' : 'GOT IT';
    if (C.offBtn) C.offBtn.textContent = (i > 0) ? '◂ BACK' : 'Turn tips off';
    if (C.root.scrollTop) C.root.scrollTop = 0;
  }

  function openCoach(item) {
    if (!doc || !item) return false;
    if (S.running) return false;        // never stack on the linear walkthrough
    buildCoach();
    if (!C.root) return false;
    var who = item.who || FIXER;
    C.id = item.id;
    C.item = item;
    C.glyph.textContent = who.glyph;
    C.name.textContent = who.name;
    C.name.style.color = who.color || '#e8c55a';
    // normalize to a beat array -- a no-slides entry is one beat (zero behavior change)
    C.slides = (item.slides && item.slides.length) ? item.slides
      : [{ title: item.title, video: item.video, obj: item.obj, why: item.why, how: item.how }];
    C.i = 0;
    renderSlide();
    C.root.style.display = 'flex';
    return true;
  }
  function closeCoach() {
    if (!C.root) return;
    C.root.style.display = 'none';
    try { if (C.vidEl) C.vidEl.pause(); } catch (_e) {}
    if (C.id) { markSeen(C.id); C.id = null; }   // remember this screen has been taught
  }

  // ---- public: first-visit (once-only) + show (replay anytime) -------------
  function firstVisit(screenId, info) {
    try {
      if (!doc || !screenId) return false;
      if (orchestratorHolds()) return false; // AK-FIRSTRUN: no coach cards over the age gate / auth / prologue / starter (the screen re-teaches on the NEXT visit)
      if (tipsOff()) return false;        // player switched tips off
      if (isSeen(screenId)) return false; // already taught this screen
      if (coachOpen()) return false;      // one coach at a time
      var item = lookupVisit(screenId, info);
      if (!item) return false;
      return openCoach(item);
    } catch (_e) { return false; }
  }
  function showVisit(screenId, info) {    // replay path -- ignores seen/tipsOff
    try {
      if (!doc || !screenId) return false;
      var item = lookupVisit(screenId, info);
      if (!item) return false;
      return openCoach(item);
    } catch (_e) { return false; }
  }

  // ---- expose for the integration pass -------------------------------------
  global.AK_TUTORIAL = {
    start: start,            // force-run the linear walkthrough
    replay: replay,          // wire to a "Replay tutorial" menu entry
    skip: function () { finish(true); },
    finish: function () { finish(false); },
    maybeAutoStart: maybeAutoStart,
    isDone: isDone,
    reset: clearDone,        // dev/testing: clear p.tutorialDone so it auto-runs again
    isRunning: function () { return !!S.running; },
    steps: STEPS.length,
    // ---- first-visit contextual coach (the per-screen explainers) ----------
    firstVisit: firstVisit,  // once-only: show screenId's coach the FIRST time
    show: showVisit,         // replay any screen's coach on demand
    seen: isSeen,            // has this screen been taught?
    closeCoach: closeCoach,  // dismiss the open coach
    resetVisits: clearVisits,// dev/testing: forget all first-visits + re-enable tips
    screens: (function () { var k = []; for (var x in VISITS) if (VISITS.hasOwnProperty(x)) k.push(x); return k; })()
  };

  // ==========================================================================
  // AK-LIVINGMANGA 2026-07-09 (bible 10.5): first-visit triggers for the new
  // coach screens. Same wrap-once pattern as index.html's AK-FIRSTVISIT wiring
  // (fire AFTER the original opener, throw-proof, capped poll):
  //   needs             -> first runner-picker open (window.akOpenRunnerPicker)
  //   chronicle_choices -> first comic-reader open (AK_CHRONICLES.open)
  //   starter           -> NO auto-hook: the starter-flow owner calls
  //                        AK_TUTORIAL.firstVisit('starter') right after the
  //                        starter moment; until then it lives in the replay
  //                        list (AK_TUTORIAL.screens / AK_TUTORIAL.show).
  //   fence_lore        -> same: the Fence owner fires it when lore-locked
  //                        stock first shows; replay-reachable meanwhile.
  // AK-MANGA-TUT 2026-07-09 additions:
  //   raid_bases        -> rides akOpenRaidMap. index.html's AK-FIRSTVISIT wrap
  //                        teaches 'raidmap' on the FIRST open (one coach at a
  //                        time), so this lands on the NEXT raid-map open.
  //   defense_posts     -> rides akOpenGuard, same stagger behind 'watch'.
  //   factions          -> fired by mission_active.js on the first recruiter-
  //                        job accept (AK_TUTORIAL.firstVisit('factions')).
  // A missing module or a throw = silent no-op, the wrapped opener never breaks.
  // ==========================================================================
  (function armVisitHooks() {
    if (!doc) return;
    function fv(id) { try { firstVisit(id); } catch (_e) {} }
    function wrapFn(name, id) {
      try {
        var orig = global[name];
        if (typeof orig !== 'function' || orig.__akTutWrap) return true;
        var w = function () { var r; try { r = orig.apply(this, arguments); } finally { fv(id); } return r; };
        w.__akTutWrap = true; global[name] = w; return true;
      } catch (_e) { return true; }
    }
    function wrapMethod(objName, method, id) {
      try {
        var o = global[objName];
        if (!o || typeof o[method] !== 'function' || o[method].__akTutWrap) return true;
        var orig = o[method];
        var w = function () { var r; try { r = orig.apply(this, arguments); } finally { fv(id); } return r; };
        w.__akTutWrap = true; o[method] = w; return true;
      } catch (_e) { return true; }
    }
    var tries = 0;
    (function poll() {
      var done = true;
      if (typeof global.akOpenRunnerPicker === 'function') wrapFn('akOpenRunnerPicker', 'needs'); else done = false;
      if (global.AK_CHRONICLES && typeof global.AK_CHRONICLES.open === 'function') wrapMethod('AK_CHRONICLES', 'open', 'chronicle_choices'); else done = false;
      if (typeof global.akOpenRaidMap === 'function') wrapFn('akOpenRaidMap', 'raid_bases'); else done = false;     // AK-MANGA-TUT -- staggers behind 'raidmap'
      if (typeof global.akOpenGuard === 'function') wrapFn('akOpenGuard', 'defense_posts'); else done = false;      // AK-MANGA-TUT -- staggers behind 'watch'
      if (!done && ++tries < 60) setTimeout(poll, 400);   // ~24s grace, same as the index.html wiring
    })();
  })();

  // ---- register the AK_SYSTEMS module (gives us the init() auto-arm hook) ---
  if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) {
    global.AK_SYSTEMS.register({
      id: 'tutorial',
      init: function (ctx) { S.ctx = ctx; armAutoStart(); }   // no onTick/onDrawWorld -- zero per-frame cost
    });
  }

  // ---- defensive arm even if initAll never reaches us ----------------------
  if (doc) {
    if (doc.readyState === 'complete' || doc.readyState === 'interactive') armAutoStart();
    else doc.addEventListener('DOMContentLoaded', armAutoStart);
  }
})(typeof window !== 'undefined' ? window : globalThis);
