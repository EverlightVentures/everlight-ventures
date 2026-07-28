/* ALLEY KINGZ -- AK_PORTAL: the building ENTRY ROUTER + DOOR MEMORY + exit watchdog.
   systems/akportal.js  (2026-07-19)

   WHY THIS EXISTS. Building entry in this repo is a chain, not a function: index.html:1286
   enterInterior(b) fires AK_SYSTEMS.enterBuilding(b, AK_CTX) at index.html:1289 and the FIRST
   registered module returning strictly `true` owns the screen (_registry.js:19). Eleven modules
   are in that chain today. Nothing owns the OTHER half of the contract -- what happens on the way
   OUT. Three concrete holes were measured before a line of this file was written:

     (1) THE GARAGE SOFT-LOCKS THE DISTRICT. garage.js:1415 sets claimBuilding = true, so
         garage.js:1424 open({}) claims the building and index.html:1289 sets interiorOpen = true.
         The panel's own CLOSE button (garage.js:1291) is wired straight to close() (garage.js:1312),
         which removes #ak-gar from the DOM and touches NOTHING ELSE. interiorOpen stays true
         forever. That one boolean gates three separate systems:
             index.html:2383  movement  -> the player can no longer walk
             index.html:2410  dwell     -> no other building can be entered
             index.html:2426  akTickSystems -> every plug-in tick dies (world3d stops rendering,
                                               production/missions/roamers/encounters all freeze)
         Recovery today is a page reload. The other ten claimants are safe because they render
         through ctx.ui.keeperCard (index.html:3232) whose LEAVE button calls exitInterior
         (index.html:3264). Garage is the only one that paints its own sheet.

     (2) EVERY EXIT LANDS ON THE SOUTH FACE, EVEN WHEN YOU NEVER WALKED THERE. exitInterior
         (index.html:1347) hardcodes me.y = b.y + b.h/2 + (me.r+85). For a dwell walk-in that is
         correct -- the dwell test (index.html:2410) only fires within me.r+30 = 53px of the south
         door point, so you did approach from the south. But SIX buildings are enterable by TAP
         from anywhere in the 1700x1300 district: akOpenUpgrade routes GEM/MINT/FORGE/LAB/GEN at
         index.html:996 and INFIRMARY at index.html:997 straight into enterInterior(b). Tap the Gem
         Mine from the far side of Factory Row and you get teleported ~600 world units on the way
         out. The operator's real-life-logic law says left is left: if you never walked to the door,
         leaving must not move you.

     (3) THERE IS NO ROUTE TABLE. Which building opens what is spread across eleven onEnterBuilding
         bodies plus a keeper fallback plus two special-cases in interiorGo (index.html:1342-1344).
         Nothing can ask "what kind of place is this?" before opening it.

   WHAT THIS MODULE DOES NOT DO. It never claims a building. onEnterBuilding here always returns
   false. AK_PORTAL loads LAST in index.html's systems block, so by the time the chain reaches it
   every real claimant has already had its turn; returning false keeps the host's default keeper
   card (index.html:1290+) exactly as it is. This module OBSERVES the chain and owns the way out.
   That is the difference between cooperating with enterBuilding and replacing it.

   THE FOUR MODES are a classification of what a door leads to, used by route()/mode() and by the
   establishing-shot layer:
     'panel'      a DOM card owns the screen -- keeperCard, or a module's own sheet (#ak-gar).
     'video'      the room itself is the content: a full-bleed interiors_mp4 loop, then the card.
     'minigame2d' entry hands off to a canvas/page game surface (battler, gulag, arcade, test-drive).
     'interior3d' a real walk-in 3D room. NOTHING implements this yet -- see provide() below. It is
                  declared so the router has a name for it, and provide() is the seam that fills it
                  in without this file changing. Read the honesty note on provide() before using it.

   ONE RENDERER LAW: this module constructs no WebGLRenderer and touches no three.js. It is DOM +
   arithmetic only. */

(function (root) {
  'use strict';

  var HAS_DOM = (typeof document !== 'undefined' && !!document.body) ||
                (typeof document !== 'undefined' && typeof document.getElementById === 'function');

  /* ---------------------------------------------------------------------------
     SECTION 1 -- THE ROUTE TABLE
     All 18 buildings across the 9 districts (index.html:706-737). `owner` records who actually
     claims the building in the chain TODAY, verified by reading each onEnterBuilding body, not by
     guessing. Keeping the observed owner next to the mode is what makes this table auditable: if a
     module stops claiming its building, the table is provably stale and route() will say so.
     `mp4` is the assets/interiors_mp4/<stem>.mp4 stem, mirroring INT_BG at index.html:622. All 18
     stems were confirmed present on disk (20 files in that folder; merchant + town_hall are unused
     by INT_BG).
  --------------------------------------------------------------------------- */
  var ROUTE = {
    // --- HOME_TURF (the spawn district) ---
    ARENA:     { mode: 'minigame2d', owner: 'host',       mp4: 'arena',        note: 'keeper -> game.html, the card battler' },
    TROPHY:    { mode: 'panel',      owner: 'seasons',    mp4: 'trophy_hall',  note: 'seasons.js:621 claims' },
    KENNEL:    { mode: 'video',      owner: 'host',       mp4: 'kennel',       note: 'keeper -> shop#handlers' },
    INFIRMARY: { mode: 'panel',      owner: 'host',       mp4: 'infirmary',    note: 'infirmary.js:471 deliberately returns false; interiorGo index.html:1343 -> akOpenInfirmary' },
    // --- DOWNTOWN ---
    DROP:      { mode: 'video',      owner: 'host',       mp4: 'drop_shop',    note: 'keeper -> shop#gems' },
    GARAGE:    { mode: 'minigame2d', owner: 'garage',     mp4: 'garage',       note: 'garage.js:1419 claims, paints #ak-gar, NEVER releases interiorOpen -- see watchdog' },
    // --- NEON_HEIGHTS ---
    WARD:      { mode: 'video',      owner: 'host',       mp4: 'wardrobe',     note: 'keeper -> shop#drip2' },
    ARCH:      { mode: 'video',      owner: 'host',       mp4: 'archive',      note: 'keeper -> shop#codex2' },
    // --- THE_YARDS ---
    CLAN:      { mode: 'video',      owner: 'host',       mp4: 'crew_yard',    note: 'keeper -> shop#crew2' },
    PASS:      { mode: 'video',      owner: 'host',       mp4: 'pass_house',   note: 'keeper -> shop#pass2' },
    FIXER:     { mode: 'panel',      owner: 'missions',   mp4: 'fixer_den',    note: 'missions.js:526 claims' },
    // --- FACTORY_ROW ---
    GEM:       { mode: 'panel',      owner: 'production', mp4: 'gem_mine',     note: 'production.js:227 claims; ALSO tap-enterable index.html:996' },
    MINT:      { mode: 'panel',      owner: 'production', mp4: 'gold_mint',    note: 'production.js:227 claims; ALSO tap-enterable index.html:996' },
    FORGE:     { mode: 'panel',      owner: 'production', mp4: 'card_forge',   note: 'production.js:227 claims; ALSO tap-enterable index.html:996' },
    // --- THE_STRIP ---
    STREET:    { mode: 'minigame2d', owner: 'modes',      mp4: 'street_mode',  note: 'modes.js:2053 claims -> gulag / encounter / defense overlays' },
    ARCADE:    { mode: 'minigame2d', owner: 'arcade',     mp4: 'arcade',       note: 'arcade.js:924 claims -> mini-games' },
    // --- THE_DOCKS ---
    LAB:       { mode: 'panel',      owner: 'production', mp4: 'research_lab', note: 'production.js:227 claims; ALSO tap-enterable index.html:996' },
    GEN:       { mode: 'panel',      owner: 'production', mp4: 'power_gen',    note: 'production.js:227 claims; ALSO tap-enterable index.html:996' }
  };

  var MODES = ['panel', 'video', 'minigame2d', 'interior3d'];

  // Unknown building (a raid-generated structure carries b._raid / b.type, index.html:2588) falls
  // back to 'panel' -- the host keeper card is the universal default and always works.
  var FALLBACK = { mode: 'panel', owner: 'host', mp4: null, note: 'not in the route table' };

  function idOf(b) {
    if (!b) return '';
    return String((typeof b === 'object' ? (b.id || b.key || '') : b) || '').toUpperCase();
  }
  function route(b) { return ROUTE[idOf(b)] || FALLBACK; }
  function mode(b)  { return route(b).mode; }
  function owner(b) { return route(b).owner; }

  /* ---------------------------------------------------------------------------
     SECTION 2 -- DOOR MEMORY (pure arithmetic, node-testable)

     ENTRY_R = 63 is not a taste number. It is me.r + 40, the WIDEST walk-in radius the hub uses --
     akNearestBuilding at index.html:812 (the keyboard/vim path). The dwell path is tighter at
     me.r + 30 = 53 (index.html:2410). Anything outside 63 could not have been a walk-in, so it was
     a tap from range (index.html:996-997) and the player never physically approached the door.

     CLEAR = me.r + 85 = 108 reproduces the hub's own exit clearance (index.html:1347) exactly. That
     number exists so the player lands far enough off the door that the 0.22s dwell timer
     (index.html:2413) cannot instantly re-enter the building you just left.

     THE COMPATIBILITY PROOF. The canonical door is the SOUTH face centre (b.x, b.y + b.h/2) -- both
     the dwell test (index.html:2410) and akNearestBuilding (index.html:812) measure to that point.
     A dwell walk-in therefore always stands south of centre, faceFor() returns 'S', and the exit
     point computed here is (b.x, b.y + b.h/2 + 108) -- byte-identical to what index.html:1347 does
     today. The behaviour only DIVERGES on the tap-from-range case, which is the bug. That is why
     this can ship without re-testing all 18 walk-ins.
  --------------------------------------------------------------------------- */
  var ENTRY_R = 63;
  var CLEAR   = 108;

  // Which wall did the player approach? Normalising dx/dy by the building's own half-extents (not
  // raw pixels) is what makes this correct for the wide-and-flat footprints this game uses -- every
  // building is 160-210 wide by 96-124 tall, so a raw |dx|>|dy| test would call a corner approach
  // 'E' when the player is plainly standing south of the wall.
  function faceFor(b, fx, fy) {
    var hw = Math.max(1, (b && b.w ? b.w : 160) / 2);
    var hh = Math.max(1, (b && b.h ? b.h : 96) / 2);
    var nx = (fx - (b ? b.x : 0)) / hw;
    var ny = (fy - (b ? b.y : 0)) / hh;
    if (Math.abs(nx) > Math.abs(ny)) return nx > 0 ? 'E' : 'W';
    return ny > 0 ? 'S' : 'N';
  }

  // The world is 1700x1300 (index.html:588). Clamping to a 40px inset keeps a restored exit inside
  // the playfield when a building sits near a district edge -- otherwise a west-face exit off THE
  // YARDS' left column would drop the player at a negative x and the camera clamp would fight it.
  function clampWorld(p, worldW, worldH) {
    var W = worldW || 1700, H = worldH || 1300, M = 40;
    p.x = Math.max(M, Math.min(W - M, p.x));
    p.y = Math.max(M, Math.min(H - M, p.y));
    return p;
  }

  /* doorFor(b, from, world) -> {x, y, face, walked}
     `from` is where the player stood at the MOMENT OF ENTRY (captured by the enterInterior wrap in
     Section 5, before the host moves anything).
       walked === true   the player was inside ENTRY_R of the door: push them clear of the face they
                         approached, so leaving mirrors arriving.
       walked === false  a tap from range: hand back the exact standing position. No teleport. */
  function doorFor(b, from, world) {
    var doorX = b ? b.x : 0;
    var doorY = b ? (b.y + (b.h || 96) / 2) : 0;
    var fx = (from && isFinite(from.x)) ? from.x : doorX;
    var fy = (from && isFinite(from.y)) ? from.y : doorY;

    var walked = Math.hypot(fx - doorX, fy - doorY) <= ENTRY_R;
    if (!walked) {
      return clampWorld({ x: fx, y: fy, face: faceFor(b, fx, fy), walked: false },
                        world && world.WORLD_W, world && world.WORLD_H);
    }

    var face = faceFor(b, fx, fy);
    var hw = (b && b.w ? b.w : 160) / 2;
    var hh = (b && b.h ? b.h : 96) / 2;
    var out = { x: b ? b.x : 0, y: b ? b.y : 0, face: face, walked: true };
    if (face === 'S') out.y = b.y + hh + CLEAR;
    else if (face === 'N') out.y = b.y - hh - CLEAR;
    else if (face === 'E') out.x = b.x + hw + CLEAR;
    else                   out.x = b.x - hw - CLEAR;
    return clampWorld(out, world && world.WORLD_W, world && world.WORLD_H);
  }

  /* ---------------------------------------------------------------------------
     SECTION 3 -- TRANSITION RUNNER

     The hub already owns a full-screen fade: #fade (index.html:397), driven by opacity in
     doEnter (index.html:1350) and enterZone (index.html:1354). Reusing it instead of appending
     another sheet keeps exactly one black layer in the stack -- a second one would double-darken
     during a district swap that overlaps a portal transition.

     run() is deliberately callback-shaped rather than promise-shaped: this file is ES5-style to
     match the rest of systems/, and every other async seam in the repo (akPlayCinematic
     index.html:2110, AK_THREE.loadGLB) is callback-shaped too.

     The `swap` callback ALWAYS runs, even with no DOM and even if the fade element is missing --
     a transition that can swallow its own payload is how a mode ends up unreachable. Same contract
     akPlayCinematic keeps at index.html:2128.
  --------------------------------------------------------------------------- */
  var FADE_MS = 240;   // matches the 480ms doEnter budget at index.html:1352, halved per leg

  function fadeEl() {
    try { return document.getElementById('fade'); } catch (_e) { return null; }
  }
  function setFade(v) {
    var f = fadeEl(); if (!f) return false;
    try { f.style.opacity = String(v); return true; } catch (_e) { return false; }
  }

  function run(spec) {
    spec = spec || {};
    var swap = typeof spec.swap === 'function' ? spec.swap : null;
    var done = typeof spec.done === 'function' ? spec.done : null;
    var ms   = isFinite(spec.ms) ? spec.ms : FADE_MS;

    // No DOM (node self-test) or no #fade: run the payload synchronously. Never drop it.
    if (!HAS_DOM || !setFade(1)) {
      try { swap && swap(); } catch (_e) { warn('swap', _e); }
      try { done && done(); } catch (_e2) { warn('done', _e2); }
      return false;
    }
    setTimeout(function () {
      try { swap && swap(); } catch (_e) { warn('swap', _e); }
      setFade(0);
      setTimeout(function () { try { done && done(); } catch (_e2) { warn('done', _e2); } }, ms);
    }, ms);
    return true;
  }

  function warn(where, e) {
    // Never silent. A corrupt vendor file once hid for hours in this repo behind an empty catch.
    try { if (root.console && console.warn) console.warn('[AK_PORTAL]', where, e); } catch (_x) {}
  }

  /* ---------------------------------------------------------------------------
     SECTION 4 -- THE ESTABLISHING SHOT ('video' mode, and the only mode that changes what a
     player sees today)

     assets/interiors_mp4/ holds 20 clips and INT_BG (index.html:622) maps all 18 buildings onto
     them. Today those clips only ever appear as a LOOP behind the keeper card, played by
     systems/loops.js through window.akInteriorWantsVideo (index.html:691). The first time you push
     open a door there is no establishing beat at all -- the card just appears.

     'video' mode gives the six pure-storefront buildings (KENNEL/DROP/WARD/ARCH/CLAN/PASS -- the
     ones whose entire interior is a backdrop plus one nav button) a one-shot full-bleed clip the
     FIRST time you enter each, per session.

     WHY THIS IS SAFE AND ADDITIVE: the shot is fired and this module returns FALSE. It never
     claims the building. The host renders its normal keeper card underneath immediately
     (index.html:1290+); the clip sits over it at z-index 37 and reveals the card when it ends. If
     the mp4 404s, decodes badly, or autoplay is refused, the card is ALREADY THERE -- there is no
     failure path where the player is left looking at nothing. Every terminator (ended / error /
     pointerdown / 5s hard cap / play().catch) routes through one idempotent fin().

     z-index 37 sits below akPlayTransition's wipe at 38 (index.html:2103) and below the cinematic
     player at 39 (index.html:2119), so a wipe still reads on top of it.
  --------------------------------------------------------------------------- */
  var ESTABLISH_MS = 5000;                 // hard cap. akPlayCinematic uses 6500 for story beats;
                                           // a storefront reveal that outlasts 5s is an obstacle.
  var _seen = {};                          // per-session, per-building. Reload = see it again.
  var establish = true;                    // flip AK_PORTAL.establish = false to disable entirely.

  function mp4For(b) {
    var r = route(b);
    return r.mp4 ? ('assets/interiors_mp4/' + r.mp4 + '.mp4') : null;
  }

  function playEstablish(b, then) {
    var src = mp4For(b);
    if (!HAS_DOM || !src) { if (then) then(); return false; }
    var fired = false;
    try {
      var wrap = document.createElement('div');
      wrap.style.cssText = 'position:fixed;inset:0;z-index:37;background:#000;display:flex;' +
                           'align-items:center;justify-content:center;';
      var v = document.createElement('video');
      v.src = src; v.muted = true; v.playsInline = true;
      v.setAttribute('playsinline', ''); v.autoplay = true;
      v.style.cssText = 'width:100%;height:100%;object-fit:cover;';
      var skip = document.createElement('div');
      skip.textContent = 'TAP TO SKIP';
      skip.style.cssText = 'position:absolute;bottom:26px;right:18px;color:#e8c55a;' +
                           'font:800 11px Inter,system-ui;letter-spacing:.1em;opacity:.75;';

      function fin() {
        if (fired) return; fired = true;
        try { wrap.remove(); } catch (_e) {}
        if (then) { try { then(); } catch (_e2) { warn('establish-then', _e2); } }
      }
      wrap.appendChild(v); wrap.appendChild(skip);
      document.body.appendChild(wrap);
      wrap.addEventListener('pointerdown', fin);
      v.addEventListener('ended', fin);
      v.addEventListener('error', fin);
      setTimeout(fin, ESTABLISH_MS);       // hard cap -- never trap the player behind a stalled clip
      var p = v.play(); if (p && p.catch) p.catch(fin);
      return true;
    } catch (e) {
      warn('establish', e);
      if (!fired) { fired = true; if (then) { try { then(); } catch (_e3) {} } }
      return false;
    }
  }

  /* ---------------------------------------------------------------------------
     SECTION 5 -- THE INTEGRATION: wrapping enterInterior / exitInterior

     Both are top-level `function` declarations in a classic script (index.html:1286 and
     index.html:1345), so both ARE on window -- systems/vimmode.js:413 already calls
     window.exitInterior() on that basis, which is the precedent this follows.

     Wrapping rather than editing index.html's bodies is deliberate: the entry chain is being worked
     on by more than one lane, and a wrap that captures state around the original cannot conflict
     with an edit inside it. The originals keep running, unmodified, in their entirety.

     ORDER MATTERS IN BOTH WRAPS:
       enterInterior -- capture me.x/me.y BEFORE the original runs. The original may hand the
                        building to a claimant that opens an overlay and moves things.
       exitInterior  -- let the original run FIRST (it fires the exit stinger, the goodbye bark, and
                        clears interiorB/dwellB), THEN overwrite the position it chose. Overwriting
                        first would just be undone by index.html:1347.
  --------------------------------------------------------------------------- */
  var _open = null;      // {b, id, from:{x,y}, at, mode} while an interior is believed open
  var _wrapped = false;

  function ctx() { return root.AK_CTX || null; }

  function meOf() {
    var c = ctx();
    return (c && c.me) ? c.me : null;      // `const me` (index.html:747) is not on window; AK_CTX.me is the same object
  }

  function worldOf() {
    var c = ctx();
    if (!c || !c.world) return { WORLD_W: 1700, WORLD_H: 1300 };
    return { WORLD_W: c.world.WORLD_W || 1700, WORLD_H: c.world.WORLD_H || 1300 };
  }

  function wrapHost() {
    if (_wrapped || !HAS_DOM) return false;
    if (typeof root.enterInterior !== 'function' || typeof root.exitInterior !== 'function') return false;

    var origEnter = root.enterInterior;
    var origExit  = root.exitInterior;

    root.enterInterior = function (b) {
      var m = meOf();
      var from = m ? { x: m.x, y: m.y } : null;
      var r = origEnter.apply(this, arguments);
      // The host bails at index.html:1286 when interiorOpen is already true. Only record when an
      // entry actually took hold, otherwise a double-fire would overwrite the real door with the
      // position of a rejected re-entry.
      if (b && !_open) {
        _open = { b: b, id: idOf(b), from: from, at: now(), mode: mode(b) };
        armWatchdog();
      }
      return r;
    };

    root.exitInterior = function () {
      var rec = _open;
      var r = origExit.apply(this, arguments);
      _open = null;
      disarmWatchdog();
      if (rec && rec.b) {
        var m = meOf();
        if (m) {
          var d = doorFor(rec.b, rec.from, worldOf());
          m.x = d.x; m.y = d.y;
          // Clear any click-to-move target. index.html:2384 keeps walking toward me.tx/me.ty when
          // it is set, so a stale target from before the visit would immediately drag the player
          // back across the door we just placed them outside of. enterZone does the same at
          // index.html:1356.
          m.tx = null; m.ty = null;
        }
      }
      return r;
    };
    _wrapped = true;
    return true;
  }

  function now() {
    try { return (root.performance && performance.now) ? performance.now() : Date.now(); }
    catch (_e) { return Date.now(); }
  }

  /* ---------------------------------------------------------------------------
     SECTION 6 -- THE EXIT WATCHDOG (this is the garage soft-lock fix)

     A claimant that paints its own sheet can close that sheet without ever telling the host, which
     leaves interiorOpen true and the district dead (see the header, hole 1). The watchdog asks one
     question on a slow poll: do we believe an interior is open while NO interior surface is
     actually on screen? If so the host was never released, and we release it.

     IT CANNOT BE onTick. index.html:2426 gates akTickSystems on !interiorOpen -- the exact
     condition being healed is the condition that stops ticks arriving. A standalone setInterval is
     the only clock that survives it. 300ms and only while an interior is believed open, so the
     resting cost is zero timers.

     GRACE = 700ms covers the gap between enterInterior setting interiorOpen and a claimant's panel
     reaching the DOM. garage.js:1301 appends #ak-gar synchronously inside open(), and keeperCard
     shows #interior synchronously (index.html:3265), so the real gap is one frame -- 700ms is
     ~40x margin against a slow phone, chosen because a false heal (ejecting the player out of a
     panel that was mid-open) is far worse than healing 700ms late.

     SURFACE PROBES are the extension point. Three are built in and cover every claimant audited:
       #interior visible  -> the keeper card (10 of 11 claimants + the host default)
       #ak-gar present    -> garage.js:1281, the only self-painted sheet in the repo today
       #ak-ov present     -> the ctx.overlay canvas (index.html:3288), used by modes/defense/encounters
     Any future module that paints its own surface registers a probe via AK_PORTAL.holdOpen(fn)
     instead of being hardcoded here.
  --------------------------------------------------------------------------- */
  var WATCH_MS = 300;
  var GRACE_MS = 700;
  var _timer = null;
  var _probes = [];

  function interiorVisible() {
    try {
      var el = document.getElementById('interior');
      return !!el && el.style.display !== 'none' && el.style.display !== '';
    } catch (_e) { return false; }
  }
  function byId(id) { try { return !!document.getElementById(id); } catch (_e) { return false; } }

  function anySurfaceUp() {
    if (interiorVisible()) return true;
    if (byId('ak-gar')) return true;       // garage.js:1281
    if (byId('ak-ov'))  return true;       // AK_CTX.overlay.open, index.html:3288
    for (var i = 0; i < _probes.length; i++) {
      try { if (_probes[i]()) return true; } catch (e) { warn('probe', e); }
    }
    return false;
  }

  function armWatchdog() {
    if (_timer || !HAS_DOM) return;
    try {
      _timer = setInterval(function () {
        if (!_open) { disarmWatchdog(); return; }
        if (now() - _open.at < GRACE_MS) return;
        if (anySurfaceUp()) return;
        // Nothing is on screen but the host still believes an interior is open. Release it through
        // the real exitInterior so the wrap in Section 5 restores the door too.
        var id = _open.id;
        try {
          if (typeof root.exitInterior === 'function') root.exitInterior();
          else { _open = null; disarmWatchdog(); }
        } catch (e) { warn('heal', e); _open = null; disarmWatchdog(); }
        try {
          if (root.console && console.info) {
            console.info('[AK_PORTAL] released a stuck interior (' + id +
                         ') -- its module closed without calling exitInterior');
          }
        } catch (_x) {}
      }, WATCH_MS);
    } catch (e) { warn('arm', e); }
  }
  function disarmWatchdog() {
    if (!_timer) return;
    try { clearInterval(_timer); } catch (_e) {}
    _timer = null;
  }

  /* ---------------------------------------------------------------------------
     SECTION 7 -- PROVIDERS (the 'interior3d' seam)

     HONESTY NOTE, and it matters more than the code under it: NOTHING PROVIDES 'interior3d' TODAY.
     No building routes to it in the table above and no provider is registered, so this map is empty
     at runtime. It is not a claim that 3D interiors work.

     It exists because the 3D interior cannot be built from this file yet, for a reason that is
     structural rather than a matter of effort: index.html:2426 stops akTickSystems while
     interiorOpen is true, and world3d only renders from its own onTick (world3d.js:900), so the GL
     canvas is FROZEN for the entire duration of any interior -- it keeps displaying the last
     district frame under the DOM overlay. A 3D room therefore needs either a tick that survives
     interiorOpen or its own rAF reusing AK_R3D (never a second WebGLRenderer -- world3d.js:463,
     three_boot.js:74; phones evict contexts around 8 and hub3d's pool already spends up to 4).
     Both of those are integration-phase changes to files this lane must not edit.

     provide() is the seam so that lands as a registration, not a rewrite of the router.
  --------------------------------------------------------------------------- */
  var _providers = {};

  function provide(modeName, fn) {
    if (MODES.indexOf(modeName) < 0) { warn('provide', 'unknown mode ' + modeName); return false; }
    if (typeof fn !== 'function') return false;
    _providers[modeName] = fn;
    return true;
  }
  function provider(modeName) { return _providers[modeName] || null; }

  /* ---------------------------------------------------------------------------
     SECTION 8 -- THE PLUG-IN

     REGISTRATION ORDER IS THE WHOLE DESIGN. _registry.js:19 walks modules in registration order and
     the first `true` wins, and registration order is script order in index.html. This tag is placed
     LAST in the systems block (after agegate.js) so every real claimant -- production.js:436,
     missions.js:437, raid.js:462, seasons.js:464, trading.js:469, arcade.js:470, modes.js:471,
     guard.js:484, marketplace.js:485, infirmary.js:489, garage.js:505 -- gets its turn first.

     onEnterBuilding ALWAYS RETURNS FALSE. That is not a stub, it is the contract: this module
     augments the chain and owns the exit, it never takes a building away from the module that owns
     it or from the host's default keeper card. The only thing it does on the way in is fire the
     establishing shot for 'video' buildings, which layers over the card rather than replacing it.
  --------------------------------------------------------------------------- */
  var api = {
    id: 'akportal',

    init: function (c) {
      // The wrap needs window.enterInterior/exitInterior to exist. initAll runs from the hub's
      // bootstrap, well after both declarations are hoisted, so this normally takes on the first
      // try; the retry covers a future reorder rather than today's load order.
      if (!wrapHost()) { try { setTimeout(wrapHost, 0); } catch (_e) {} }
      return true;
    },

    onEnterBuilding: function (b, c) {
      try {
        var r = route(b);
        if (establish && r.mode === 'video' && !_seen[idOf(b)]) {
          _seen[idOf(b)] = 1;
          playEstablish(b, null);          // layers OVER the host card; never gates it
        }
      } catch (e) { warn('enter', e); }
      return false;                        // never claim -- see Section 8 header
    }
  };

  /* ---------------------------------------------------------------------------
     SECTION 9 -- SELF TEST
     Same convention as systems/world3d.js:290: the proof harness ships inside the module and runs
     when the file is executed directly under node. `node systems/akportal.js` is the gate.
  --------------------------------------------------------------------------- */
  function selfTest() {
    var fails = [], n = 0;
    function ok(cond, label) {
      n++;
      if (!cond) fails.push(label);
    }
    function near(a, b2, tol, label) { ok(Math.abs(a - b2) <= (tol || 0.001), label + ' (got ' + a + ', want ' + b2 + ')'); }

    // -- route table integrity ------------------------------------------------
    var ids = Object.keys(ROUTE);
    ok(ids.length === 18, 'route table covers all 18 buildings, got ' + ids.length);
    for (var i = 0; i < ids.length; i++) {
      var r = ROUTE[ids[i]];
      ok(MODES.indexOf(r.mode) >= 0, ids[i] + ' has a legal mode');
      ok(!!r.mp4, ids[i] + ' has an interiors_mp4 stem');
      ok(!!r.owner, ids[i] + ' records an owner');
    }
    ok(mode('GEM') === 'panel', 'GEM is a panel');
    ok(owner('GARAGE') === 'garage', 'GARAGE is owned by garage.js');
    ok(mode({ id: 'arcade' }) === 'minigame2d', 'lookup is case-insensitive and accepts a building object');
    ok(mode('NOT_A_BUILDING') === 'panel', 'unknown building falls back to panel');
    ok(route('NOT_A_BUILDING').owner === 'host', 'unknown building falls back to host');

    // -- door memory: the compatibility proof --------------------------------
    // GEM MINE, FACTORY_ROW: B('GEM',...,520,540,160,100,...) -> index.html:730
    var gem = { id: 'GEM', x: 520, y: 540, w: 160, h: 100 };
    var doorY = gem.y + gem.h / 2;                       // 590, the hub's canonical door point
    // A dwell walk-in stands within me.r+30 = 53px of that point, south of it.
    var walk = doorFor(gem, { x: 520, y: doorY + 30 }, { WORLD_W: 1700, WORLD_H: 1300 });
    ok(walk.walked === true, 'a dwell-range approach is classified as walked');
    ok(walk.face === 'S', 'a dwell approach reads as the south face');
    near(walk.x, 520, 0.001, 'walked exit keeps the door x');
    near(walk.y, 590 + 108, 0.001, 'walked exit reproduces index.html:1347 exactly (b.y+b.h/2+me.r+85)');

    // The exact number index.html:1347 would produce, computed independently here:
    var hubExitY = gem.y + gem.h / 2 + (23 + 85);
    near(walk.y, hubExitY, 0.001, 'walked exit is byte-identical to the hub formula');

    // -- door memory: the bug being fixed ------------------------------------
    // Tap the Gem Mine from across Factory Row (index.html:996 routes taps straight to
    // enterInterior with no proximity requirement at all).
    var far = doorFor(gem, { x: 1180, y: 1000 }, { WORLD_W: 1700, WORLD_H: 1300 });
    ok(far.walked === false, 'a tap from 700+ units away is not a walk-in');
    near(far.x, 1180, 0.001, 'tap-entry exit restores the standing x -- no teleport');
    near(far.y, 1000, 0.001, 'tap-entry exit restores the standing y -- no teleport');
    var drift = Math.hypot(far.x - walk.x, far.y - walk.y);
    ok(drift > 400, 'the fix is load-bearing: it removes a ' + Math.round(drift) + '-unit teleport');

    // -- face selection on every wall ----------------------------------------
    ok(doorFor(gem, { x: 520, y: 540 - 60 }).face === 'N', 'north approach reads N');
    ok(doorFor(gem, { x: 520 + 90, y: 540 }).face === 'E', 'east approach reads E');
    ok(doorFor(gem, { x: 520 - 90, y: 540 }).face === 'W', 'west approach reads W');
    // Half-extent normalising: 60px east / 40px south of centre on a 160x100 footprint is 0.75 vs
    // 0.80 in normalised space -> SOUTH. A raw pixel test would wrongly answer EAST.
    ok(faceFor(gem, 520 + 60, 540 + 40) === 'S', 'corner approach normalises by half-extent, not raw pixels');

    // -- walked exits clear the wall on every face ---------------------------
    var faces = [
      [{ x: 520, y: doorY + 20 }, 'S'],
      [{ x: 520, y: doorY - 20 }, 'N']    // still inside ENTRY_R of the door, but north of centre
    ];
    for (var f = 0; f < faces.length; f++) {
      var d = doorFor(gem, faces[f][0]);
      ok(d.walked === true, 'near-door approach ' + faces[f][1] + ' is a walk-in');
      var outside = (d.x <= gem.x - gem.w / 2) || (d.x >= gem.x + gem.w / 2) ||
                    (d.y <= gem.y - gem.h / 2) || (d.y >= gem.y + gem.h / 2);
      ok(outside, 'walked exit on face ' + d.face + ' lands outside the footprint');
      var dist = Math.hypot(d.x - gem.x, d.y - (gem.y + gem.h / 2));
      ok(dist > 53, 'walked exit on face ' + d.face + ' clears the 53px dwell radius (got ' + Math.round(dist) + ')');
    }

    // -- world clamping -------------------------------------------------------
    // THE YARDS' FIXER sits at x=850,y=960 (index.html:723); force a south exit near the wall.
    var edge = doorFor({ id: 'X', x: 850, y: 1280, w: 160, h: 96 }, { x: 850, y: 1328 },
                       { WORLD_W: 1700, WORLD_H: 1300 });
    ok(edge.y <= 1300 - 40, 'a south exit at the district edge clamps inside the world');
    ok(edge.x >= 40 && edge.x <= 1700 - 40, 'clamped exit stays in x bounds');

    // -- degenerate input -----------------------------------------------------
    var noFrom = doorFor(gem, null);
    ok(noFrom.walked === true && noFrom.face === 'S',
       'a missing entry position defaults to the canonical south door (today behaviour)');
    near(noFrom.y, hubExitY, 0.001, 'missing entry position still reproduces the hub formula');

    // -- transition runner ----------------------------------------------------
    var swapped = 0, finished = 0;
    run({ swap: function () { swapped++; }, done: function () { finished++; } });
    ok(swapped === 1, 'run() executes swap with no DOM');
    ok(finished === 1, 'run() executes done with no DOM');
    var threw = false;
    try { run({ swap: function () { throw new Error('boom'); }, done: function () { finished++; } }); }
    catch (_e) { threw = true; }
    ok(!threw, 'a throwing swap does not escape run()');
    ok(finished === 2, 'done still runs after swap throws -- a transition never strands a mode');

    // -- providers ------------------------------------------------------------
    ok(provider('interior3d') === null, 'interior3d has NO provider -- the seam is empty, as documented');
    ok(provide('interior3d', function () { return 1; }) === true, 'provide() accepts a legal mode');
    ok(typeof provider('interior3d') === 'function', 'provide() registers');
    ok(provide('nonsense', function () {}) === false, 'provide() rejects an unknown mode');
    delete _providers.interior3d;

    // -- establishing shot is a no-op without DOM ----------------------------
    var cb = 0;
    playEstablish({ id: 'DROP' }, function () { cb++; });
    ok(cb === 1, 'playEstablish always fires its continuation, even with no DOM');
    ok(mp4For({ id: 'DROP' }) === 'assets/interiors_mp4/drop_shop.mp4', 'mp4 path matches INT_BG index.html:622');
    ok(mp4For({ id: 'NOPE' }) === null, 'unknown building has no clip');

    // -- video mode only touches the six storefronts -------------------------
    var vids = ids.filter(function (k) { return ROUTE[k].mode === 'video'; }).sort();
    ok(vids.join(',') === 'ARCH,CLAN,DROP,KENNEL,PASS,WARD',
       'video mode is scoped to the 6 storefronts, got ' + vids.join(','));
    // 11 modules define onEnterBuilding, but five of them (guard.js:531, marketplace.js:1488,
    // raid.js:709, trading.js:987, infirmary.js:471) return false on purpose and own no building.
    // Six modules actually claim, and between them they take 10 of the 18 doors; the host keeps 8.
    var claimed = ids.filter(function (k) { return ROUTE[k].owner !== 'host'; });
    ok(claimed.length === 10, '10 buildings are claimed by other modules, got ' + claimed.length);
    var claimants = {};
    claimed.forEach(function (k) { claimants[ROUTE[k].owner] = 1; });
    ok(Object.keys(claimants).length === 6, '6 distinct modules claim buildings, got ' + Object.keys(claimants).sort().join(','));
    ok(ids.length - claimed.length === 8, 'the host default keeper card owns the remaining 8 doors');
    for (var v = 0; v < vids.length; v++) {
      ok(ROUTE[vids[v]].owner === 'host',
         vids[v] + ' is unclaimed -- the establishing shot can never fight a claimant');
    }

    return { pass: n - fails.length, total: n, fails: fails };
  }

  /* ---------------------------------------------------------------------------
     SECTION 10 -- PUBLISH
  --------------------------------------------------------------------------- */
  var PUBLIC = {
    // routing
    ROUTE: ROUTE, MODES: MODES,
    route: route, mode: mode, owner: owner,
    // door memory
    doorFor: doorFor, faceFor: faceFor, ENTRY_R: ENTRY_R, CLEAR: CLEAR,
    // transitions
    run: run, fade: setFade,
    // establishing shot
    playEstablish: playEstablish, mp4For: mp4For,
    get establish() { return establish; },
    set establish(v) { establish = !!v; },
    // providers (interior3d seam -- empty today, see Section 7)
    provide: provide, provider: provider,
    // watchdog extension: register a predicate meaning "my surface is still on screen"
    holdOpen: function (fn) { if (typeof fn === 'function') { _probes.push(fn); return true; } return false; },
    // introspection / test
    current: function () { return _open ? { id: _open.id, mode: _open.mode, from: _open.from } : null; },
    wrapped: function () { return _wrapped; },
    selfTest: selfTest
  };

  root.AK_PORTAL = PUBLIC;

  try {
    if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) root.AK_SYSTEMS.register(api);
  } catch (e) { warn('register', e); }

  // node: `node systems/akportal.js` runs the harness; `require()` returns the API.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = PUBLIC;
    if (typeof require !== 'undefined' && require.main === module) {
      var res = selfTest();
      console.log('[AK_PORTAL selfTest] ' + res.pass + '/' + res.total + ' passed');
      if (res.fails.length) {
        console.log('FAILURES:');
        res.fails.forEach(function (f) { console.log('  - ' + f); });
        process.exit(1);
      }
    }
  }

})(typeof window !== 'undefined' ? window : globalThis);
