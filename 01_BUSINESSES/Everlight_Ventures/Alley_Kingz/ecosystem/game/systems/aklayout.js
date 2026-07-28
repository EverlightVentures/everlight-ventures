/* ALLEY KINGZ -- AK_LAYOUT: give the screen back to the world.  AK-LAYOUT 2026-07-20.
 *
 * OPERATOR: "40% of the screen is UI chrome, minimap, buttons -- the 3D view is a tiny window."
 *
 * He was not exaggerating and he was not rounding. MEASURED headless at a 390x844 phone viewport,
 * world3d ON, tutorial skipped, BLOCK CHRONICLES dismissed and confirmed gone:
 *
 *     persistent UI chrome ....... 36.51% of all pixels   (clear 3D view 63.49%)
 *     with a toast on screen ..... 49.35%                 (clear 3D view 50.65%)
 *
 * Union area per owning container, biggest first -- this is the target list:
 *
 *     15.22%  #phud      the chip + currency stack. 25 visible children, WRAPPED INTO 11 ROWS,
 *                        bbox x=10..273 y=30..336. 306px of a 844px screen -- 36% of the height.
 *      5.50%  #ak-beacon goal tracker, bottom-centre
 *      4.98%  #hud       a STATIC help string: "THE LOT - walk to a building to enter its mode
 *                        - tap / joystick / WASD / arrows / hjkl". Onboarding text, on forever.
 *      4.23%  #stick     the joystick. LEAVE IT ALONE (see LOCKED CONTROLS below).
 *      4.03%  #radar     the minimap. LEAVE ITS GEOMETRY ALONE (see LOCKED CONTROLS below).
 *      2.13%  #dist      the district title
 *      1.18%  .tag       "walkable world proto - 3 districts - not the final build" (dev text)
 *      1.18%  #ak-wm-btn + #ak-bm-btn (world map / build mode, right edge)
 *     12.09%  #banner    transient day/night + street-talk toast, not counted in the 36.51%
 *
 * The chip stack is the whole story: it is 3x the next offender, and it is not even dense -- it is
 * 25 small pills that wrap because index.html:134 gives #phud
 * `flex-wrap:wrap;max-width:calc(100vw - 116px)`. At 390px wide that is a 274px column, so the row
 * breaks eleven times. Collapse that one thing and most of the complaint goes away.
 *
 * ---------------------------------------------------------------------------
 * THE LAYER DISAGREEMENT -- the bug underneath the cosmetic one
 * ---------------------------------------------------------------------------
 * index.html:13 sizes the 2D canvas  #c{display:block;width:100vw;height:100vh;}
 * world3d.js:697 mounts the GL canvas  width:100vw;height:100dvh
 * world3d.js:1611 feeds the camera     proj.setViewport(innerWidth, innerHeight)
 * world3d.js:1643 renders              renderer.setSize(S.W, S.H, false)   <- updateStyle=FALSE
 *
 * On a phone with a dynamic toolbar those are THREE different numbers:
 *   100vh  resolves to the LARGE viewport (toolbar retracted) -- the tallest
 *   100dvh tracks the CURRENT dynamic viewport
 *   innerHeight is the current viewport too, so dvh ~= innerHeight but neither equals 100vh
 *
 * Two consequences, and the second is the expensive one:
 *   1. #c is taller than the GL canvas by the toolbar band, so the layers disagree by a strip
 *      along the bottom -- the visible symptom.
 *   2. index.html:723 does W=cv.clientWidth,H=cv.clientHeight -- so the 2D hub's wx()/wy()
 *      projection runs at H=100vh while the 3D camera runs at S.H=innerHeight. THE SAME WORLD
 *      POINT PROJECTS TO A DIFFERENT SCREEN Y IN THE TWO LAYERS. On Chrome Android that ratio is
 *      roughly 844/788 = 1.07, i.e. a ~7% vertical drift that grows toward the bottom of the
 *      screen. Every 2D-drawn marker slides off the 3D geometry it is supposed to label.
 *
 * THE FIX IS STRUCTURAL, NOT TUNED. Rather than guess a band height, AK_LAYOUT makes both layers
 * read ONE number. It writes `#c{width:Npx;height:Mpx}` and the same for `#ak-world3d` into a
 * managed stylesheet, with N,M taken straight from innerWidth/innerHeight. index.html:722 then
 * clears the inline size and reads clientWidth/clientHeight -- which now RESOLVE TO innerWidth /
 * innerHeight exactly -- and world3d already uses innerWidth/innerHeight. They cannot drift,
 * because there is no longer a second source to drift from.
 *
 * ORDERING, AND WHY THE SCRIPT TAG POSITION MATTERS:
 * index.html registers its own `resize` listener at index.html:727, inside the inline <script>
 * that opens at index.html:711. DOM listeners fire in registration order, so this module must be
 * included with the other systems/*.js tags (which all sit ABOVE line 711) -- then on every resize
 * OUR handler runs first, republishes the pixel sizes, and index.html's resize() reads fresh
 * numbers in the same event. Included after that inline block, we would be one frame stale.
 *
 * ---------------------------------------------------------------------------
 * LOCKED CONTROLS -- two things that look easy and are not. Do not "optimise" these.
 * ---------------------------------------------------------------------------
 * #stick (4.23%) -- the joystick's pixel geometry is hard-read by JS in five places:
 *     index.html:1025  stick.style.left=(e.clientX-58)+'px'     58 = half of the 116px box
 *     index.html:1041  dx=e.clientX-(r.left+58)                 same 58, again
 *     index.html:1045  nub.style.left='33px'                    nub rest position
 *     index.html:1036  stick.style.left='16px'; bottom='16px'   snap-back on pointer-up
 *     index.html:2540  same snap-back when BUILD MODE closes
 *   Scaling it breaks the deflection math. Moving it does not even STICK: 1036 and 2540 write the
 *   16px/16px rest position as INLINE style, which beats any stylesheet rule we could add, on
 *   every single pointer-up. So AK_LAYOUT does not size it, move it, or hide it. Untouched.
 *
 * #radar (4.03%) -- fast-travel maps taps with HARD-CODED pixel constants at index.html:2519:
 *     if(ly<=16){var i=Math.floor(lx/(100/ZNAV.length)); ...}
 *   `100` is the radar's CSS width and `16` is the pip-strip height, but `lx`/`ly` come from
 *   getBoundingClientRect(), which reports the RENDERED box. Shrink the radar to 72px and lx runs
 *   0..72 while the divisor stays 100/N -- every pip resolves to the wrong district and the
 *   rightmost ones become unreachable. A transform:scale() has the same problem, because
 *   getBoundingClientRect() returns the transformed rect. So AK_LAYOUT changes the radar's OPACITY
 *   and its corner OFFSET only -- both safe, because the handler derives its origin from
 *   r.left/r.top and never assumes a position. Geometry is left at exactly 100x128.
 *   To actually shrink it later, index.html:2519 has to become resolution-independent first:
 *       var i=Math.floor(lx/(r.width/ZNAV.length));   and   if(ly<=16*(r.height/128))
 *   That is an index.html edit, so it is handed to the Wire phase as OPTIONAL, and
 *   setRadarScale() stays a no-op until someone opts in.
 *
 * WHY CSS RULES AND NOT INLINE STYLE:
 * index.html:1764 akRaidHudChrome() does e.style.display = show?'':'none' over
 * ['phud','ak-beacon','radar','encind','hud','dist',...] every time a raid starts and ends. Inline
 * style beats a stylesheet, so anything we set inline would be wiped on the next raid. Driving
 * everything from one injected <style> keyed on html[data-ak-lay] survives that, and the raid's
 * own display:none still wins while the raid owns the screen -- which is what we want.
 *
 * TAPS: the pointer-events discipline the lane asks for is already RIGHT in most of this codebase
 * -- #phud, #hud, #dist, #ak-beacon and #stick are all pointer-events:none shells whose real
 * controls opt back in with pointer-events:auto. The measured exception is `.tag`, a decorative
 * 390x10 dev footer sitting at pointer-events:auto across the full width of the bottom edge. It is
 * hidden in lean mode and forced to pointer-events:none in every mode, so it can never eat a tap.
 * Note also index.html:1024: the LEFT 45% of the canvas is the floating-joystick spawn zone, so
 * chrome placed there costs movement input, not just pixels. The 263x306 chip block sits squarely
 * in it -- collapsing the stack hands back control surface as well as view.
 */
window.AK_LAYOUT = (function (root) {
  'use strict';

  var doc = root && root.document;

  // ---- tunables -----------------------------------------------------------
  // Collapsed rows of #phud. 1 row = 26px of chip + nothing else; the measured stack is 11 rows
  // (306px). We keep the primary currencies on that row and put navigation behind the tray.
  var LEAN_DEFAULT = 'lean';       // 'lean' | 'full'. 'full' is byte-for-byte today's chrome.
  var RADAR_OPACITY = 0.62;        // semi-transparent: the minimap still reads, the world shows through
  var RADAR_SCALE = 1;             // LOCKED at 1 -- see the #radar note above. setRadarScale() guards it.
  var DIST_FADE_MS = 2600;         // the district title is an arrival label, not a permanent banner
  var STYLE_ID = 'ak-layout-css';
  var TRAY_ID = 'ak-lay-tray';
  var LS_KEY = 'ak_layout_chrome';

  var _mode = LEAN_DEFAULT, _open = false, _styleEl = null, _tray = null;
  var _pinW = 0, _pinH = 0, _pins = 0, _lastPoll = 0, _distAt = 0, _wired = false;
  // _ticks exists purely so diag() can PROVE the host is dispatching us. "Code nothing calls" is
  // the most expensive recurring failure in this repo, and this module got bitten by it once
  // already: the first wiring put the <script> above systems/_registry.js:422, so AK_SYSTEMS was
  // undefined at load, register() was skipped, and onTick never ran -- with no error anywhere.
  // A counter in diag() turns that class of silent no-op into a one-line assertion in the tests.
  var _ticks = 0, _registered = false;

  function $(id) { try { return doc && doc.getElementById(id); } catch (_e) { return null; } }

  // ---- the managed stylesheet ---------------------------------------------
  // ONE <style>, appended last so equal-specificity id rules (#c, #radar) win over index.html's
  // head block by document order -- no !important needed for those. The chip-hiding rules DO use
  // !important, because #ph-resume / #ph-def are created at runtime with inline display values and
  // an inline style would otherwise beat us.
  function ensureStyle() {
    if (_styleEl && _styleEl.parentNode) return _styleEl;
    if (!doc) return null;
    var el = $(STYLE_ID);
    if (!el) {
      el = doc.createElement('style');
      el.id = STYLE_ID;
      (doc.head || doc.documentElement).appendChild(el);
    }
    _styleEl = el;
    return el;
  }

  // Static half of the stylesheet -- everything that does not depend on the live pixel size.
  function chromeCSS() {
    return [
      /* .tag is decorative and was measured at pointer-events:auto across the full bottom edge
         (390x10 at y=829). Never let it take a tap, in any mode. */
      '.tag{pointer-events:none!important;}',

      /* Cornered chrome respects the notch / home indicator. env() is 0 on a device without
         insets, so this is a no-op there rather than a layout shift. */
      'html[data-ak-lay] #phud{top:calc(30px + env(safe-area-inset-top,0px));' +
        'left:calc(10px + env(safe-area-inset-left,0px));}',
      'html[data-ak-lay] #radar{top:calc(46px + env(safe-area-inset-top,0px));' +
        'right:calc(10px + env(safe-area-inset-right,0px));opacity:' + RADAR_OPACITY + ';' +
        'transition:opacity .18s;}',
      /* Touching the minimap brings it back to full strength -- a faded map you are reading is
         worse than no fade at all. */
      'html[data-ak-lay] #radar:active{opacity:1;}',

      /* ---- LEAN MODE ---- */
      /* The help strip and the proto footer are text-only onboarding/dev furniture: 4.98% + 1.18%
         of the screen, permanently. */
      'html[data-ak-lay="lean"] #hud{display:none!important;}',
      'html[data-ak-lay="lean"] .tag{display:none!important;}',

      /* The district title is an ARRIVAL label. Keep the reveal, drop the permanence. */
      'html[data-ak-lay="lean"] #dist{transition:opacity .5s;}',
      'html[data-ak-lay="lean"][data-ak-dist="idle"] #dist{opacity:0;}',

      /* The chip stack, collapsed. Hiding by CLASS (not by id list) is deliberate: #ph-resume and
         #ph-def are appended at runtime and were both present in the measurement, so an id list
         would silently miss whatever gets added next. */
      'html[data-ak-lay="lean"]:not([data-ak-tray="open"]) #phud{max-width:calc(100vw - 150px);}',
      'html[data-ak-lay="lean"]:not([data-ak-tray="open"]) #phud .chip{display:none!important;}',
      'html[data-ak-lay="lean"]:not([data-ak-tray="open"]) #phud #ak-auth{display:none!important;}',
      /* Raw materials belong to build mode, not to the walking-around screen. Gold/gem/scrap/keys/
         bones stay -- they are the numbers a player actually glances at. */
      'html[data-ak-lay="lean"]:not([data-ak-tray="open"]) #phud #ph-wood,' +
        'html[data-ak-lay="lean"]:not([data-ak-tray="open"]) #phud #ph-stone,' +
        'html[data-ak-lay="lean"]:not([data-ak-tray="open"]) #phud #ph-metal,' +
        'html[data-ak-lay="lean"]:not([data-ak-tray="open"]) #phud #ph-produce{display:none!important;}',

      /* Open tray: a scrollable sheet rather than an 11-row wall. Capped at 46vh so the world is
         still visible behind the thing you opened.
         THE WIDTH CAP IS A CONTROL FIX, NOT STYLING. The first cut let the open sheet keep
         index.html:134's max-width:calc(100vw - 116px) = 274px. With left:50px and 6px of right
         padding that put its right edge at 330px, and #radar's centre is at x=329 -- so the sheet
         covered the minimap and document.elementFromPoint returned div#phud there. Fast-travel
         (index.html:2518) silently stopped working while the tray was open. Caught by the
         acceptance test's hit-test audit, not by looking at it.
         The radar column is 102px wide at right:10px, so the sheet must stop at
         100vw - 102 - 10 - 8(gap) = 100vw - 120. Subtract left:50 and 6 padding -> 100vw - 176. */
      'html[data-ak-lay="lean"][data-ak-tray="open"] #phud{max-height:46vh;overflow-y:auto;' +
        'overscroll-behavior:contain;padding:4px 6px 6px 0;border-radius:12px;' +
        'max-width:calc(100vw - 176px - env(safe-area-inset-left,0px) - env(safe-area-inset-right,0px));' +
        'background:linear-gradient(168deg,rgba(10,10,16,.72),rgba(6,6,10,.62));' +
        'backdrop-filter:blur(2px);-webkit-backdrop-filter:blur(2px);pointer-events:auto;}',
      /* A wide chip (#ph-story measures 153px, #ph-infirm 105px) must wrap inside a narrow sheet
         rather than overflow the box back across the radar. Flex items do not shrink below their
         content width without this. */
      'html[data-ak-lay="lean"][data-ak-tray="open"] #phud .chip{max-width:100%;min-width:0;}',
      /* Belt and braces: even if a future chip or a 320px-wide phone pushes the sheet back under
         the minimap, the minimap WINS the hit test. #phud is z-index:6 (index.html:24) and the
         tray button is 7, so 8 puts the radar above both. A control must never depend on a width
         calculation staying true. */
      'html[data-ak-lay="lean"][data-ak-tray="open"] #radar{z-index:8;opacity:1;}',

      /* The tray button. 34x26 to line up with the 26px chip row, cornered top-left at the same
         origin #phud uses, and pointer-events:auto because it IS a control. */
      '#' + TRAY_ID + '{position:fixed;z-index:7;display:none;align-items:center;justify-content:center;' +
        'top:calc(30px + env(safe-area-inset-top,0px));left:calc(10px + env(safe-area-inset-left,0px));' +
        'width:34px;height:26px;padding:0;border-radius:13px;cursor:pointer;' +
        'background:rgba(8,8,14,.82);border:1px solid rgba(201,168,76,.55);color:#e8c55a;' +
        'font-family:Inter,system-ui,sans-serif;font-size:12px;font-weight:800;line-height:1;' +
        'letter-spacing:.02em;pointer-events:auto;touch-action:manipulation;' +
        '-webkit-tap-highlight-color:transparent;text-shadow:0 1px 3px #000;}',
      'html[data-ak-lay="lean"] #' + TRAY_ID + '{display:flex;}',
      '#' + TRAY_ID + ':active{transform:translateY(1px);}',
      /* Shift the chip row clear of the 34px tray button (10 + 34 + 6 gap = 50). */
      'html[data-ak-lay="lean"] #phud{left:calc(50px + env(safe-area-inset-left,0px));}',

      /* The beacon is gameplay (next objective + the daily claim), so it stays -- just slimmer and
         a touch lower, riding the home-indicator inset instead of a fixed 142px. */
      'html[data-ak-lay="lean"] #ak-beacon{padding:5px 8px;' +
        'bottom:calc(142px + env(safe-area-inset-bottom,0px));max-width:min(78vw,340px);}'
    ].join('\n');
  }

  // Live half -- the pixel pin. Rewritten on every resize.
  function sizeCSS(w, h) {
    // Both layers, one number. `#c` is index.html:13's 100vw/100vh; `#ak-world3d` is
    // world3d.js:697's 100vw/100dvh. Overriding both with the SAME px pair is what makes
    // cv.clientHeight === innerHeight === proj.state.H.
    //
    // #c needs no !important. index.html:722 CLEARS the inline size before measuring
    // (cv.style.width=''), reads clientWidth/clientHeight -- which resolve to the rule below --
    // and only then does AK_RESPONSIVE.fitCanvas (responsive.js:180) echo those same numbers back
    // as inline style. The inline value is therefore always a copy of ours, never a competitor.
    //
    // #ak-world3d DOES need !important, and this was a real defect in the first cut of this file.
    // world3d.js:697 sizes the GL canvas with el.style.cssText, i.e. an INLINE declaration, and an
    // inline declaration beats a stylesheet rule of any specificity. Without !important the rule
    // below was completely inert -- it parsed, it matched, and it changed nothing. The headless
    // test could not see it either, because with no browser toolbar 100dvh === innerHeight, so the
    // canvas measured correct for the wrong reason.
    // Two things this buys beyond tidiness:
    //   1. the GL layer is pinned to innerHeight EXACTLY, not "close, via dvh"
    //   2. dvh is unsupported on older Android WebViews. There, `height:100dvh` is an invalid
    //      declaration and gets dropped -- leaving the canvas with no author height at all and
    //      falling back to the 150px intrinsic default. A px pin cannot fail that way.
    return '#c{width:' + w + 'px;height:' + h + 'px;}\n' +
           '#ak-world3d{width:' + w + 'px!important;height:' + h + 'px!important;}';
  }

  function writeStyle() {
    var el = ensureStyle();
    if (!el) return false;
    try { el.textContent = sizeCSS(_pinW, _pinH) + '\n' + chromeCSS(); } catch (_e) { return false; }
    return true;
  }

  // ---- the pin ------------------------------------------------------------
  /* pin(force) -- republish the viewport size into the stylesheet.
   * Returns true if it actually changed anything (used by the tests and by diag).
   * Cheap by design: it early-outs when the size has not moved, so calling it from onTick at 4Hz
   * costs two property reads and a compare on the overwhelming majority of frames. */
  function pin(force) {
    if (!root) return false;
    var w = root.innerWidth || 0, h = root.innerHeight || 0;
    if (!(w > 0 && h > 0)) return false;                 // headless/detached: never write garbage
    if (!force && w === _pinW && h === _pinH) return false;
    _pinW = w; _pinH = h; _pins++;
    if (!writeStyle()) return false;
    // world3d re-reads innerWidth/innerHeight itself every frame (world3d.js:1611), so it needs no
    // poke. The 2D hub only re-measures on its own resize handler, which runs right after ours in
    // the same event -- except when we were called from visualViewport, which does NOT fire a
    // window resize on iOS. Nudge it, guarded, so that path is covered too.
    try { if (typeof root.resize === 'function') root.resize(); } catch (_e) {}
    return true;
  }

  // ---- the tray -----------------------------------------------------------
  function trayLabel() { return _open ? '×' : '≡'; }   // multiplication sign / identical-to (hamburger)

  function buildTray() {
    if (!doc || _tray) return _tray;
    var b = $(TRAY_ID);
    if (!b) {
      b = doc.createElement('button');
      b.id = TRAY_ID;
      b.type = 'button';
      b.setAttribute('aria-label', 'Show or hide the chip bar');
      b.title = 'Chips & currencies';
      try { (doc.body || doc.documentElement).appendChild(b); } catch (_e) { return null; }
    }
    b.textContent = trayLabel();
    // click, not pointerdown: pointerdown on the left 45% is the joystick spawn zone
    // (index.html:1024) and we do not want to race it. The button is pointer-events:auto and sits
    // above the canvas, so the canvas never sees this tap at all.
    try { b.addEventListener('click', function (e) { try { e.stopPropagation(); } catch (_x) {} toggle(); }); } catch (_e) {}
    _tray = b;
    return b;
  }

  function applyTray() {
    try {
      var de = doc && doc.documentElement;
      if (de) { if (_open) de.setAttribute('data-ak-tray', 'open'); else de.removeAttribute('data-ak-tray'); }
      if (_tray) { _tray.textContent = trayLabel(); _tray.setAttribute('aria-expanded', _open ? 'true' : 'false'); }
    } catch (_e) {}
  }

  function toggle(force) {
    _open = (typeof force === 'boolean') ? force : !_open;
    applyTray();
    try { root.localStorage.setItem(LS_KEY + '_open', _open ? '1' : '0'); } catch (_e) {}
    return _open;
  }

  // ---- mode ---------------------------------------------------------------
  /* setChrome('lean'|'full'). 'full' removes the attribute entirely, which restores today's exact
   * chrome -- the rollback is one call, not a redeploy. */
  function setChrome(mode) {
    _mode = (mode === 'full') ? 'full' : 'lean';
    try {
      var de = doc && doc.documentElement;
      if (de) {
        de.setAttribute('data-ak-lay', _mode);
        if (_mode !== 'lean') de.removeAttribute('data-ak-tray');
      }
      root.localStorage.setItem(LS_KEY, _mode);
    } catch (_e) {}
    if (_mode === 'lean') applyTray();
    return _mode;
  }

  // ---- district-title auto-fade -------------------------------------------
  // The title is a "you have arrived" label. We watch its text and restart a timer when it
  // changes, rather than hooking enterZone -- no coupling to index.html internals, and it keeps
  // working if the zone code moves.
  var _distTxt = null;
  function pollDist(now) {
    var d = $('dist');
    if (!d) return;
    var t = '';
    try { t = (d.textContent || '').trim(); } catch (_e) { return; }
    if (t !== _distTxt) { _distTxt = t; _distAt = now; }
    try {
      var de = doc.documentElement;
      var idle = (t && (now - _distAt) > DIST_FADE_MS);
      if (idle) { if (de.getAttribute('data-ak-dist') !== 'idle') de.setAttribute('data-ak-dist', 'idle'); }
      else if (de.getAttribute('data-ak-dist')) de.removeAttribute('data-ak-dist');
    } catch (_e) {}
  }

  // ---- wiring -------------------------------------------------------------
  function wire() {
    if (_wired || !root || !root.addEventListener) return;
    _wired = true;
    // Registered from a systems/*.js tag, i.e. ABOVE index.html:711, so this handler runs BEFORE
    // index.html:727's resize() and that call reads sizes we have already republished.
    try { root.addEventListener('resize', function () { pin(false); }); } catch (_e) {}
    try { root.addEventListener('orientationchange', function () { pin(true); }); } catch (_e) {}
    // The toolbar show/hide that causes the whole 100vh-vs-innerHeight problem often fires ONLY
    // here on iOS -- a window resize never arrives.
    try {
      if (root.visualViewport && root.visualViewport.addEventListener) {
        root.visualViewport.addEventListener('resize', function () { pin(false); });
      }
    } catch (_e) {}
  }

  function boot() {
    if (!doc) return false;
    var saved = null, savedOpen = null;
    try { saved = root.localStorage.getItem(LS_KEY); savedOpen = root.localStorage.getItem(LS_KEY + '_open'); } catch (_e) {}
    _open = (savedOpen === '1');
    ensureStyle();
    pin(true);
    buildTray();
    setChrome(saved === 'full' ? 'full' : (saved === 'lean' ? 'lean' : LEAN_DEFAULT));
    wire();
    return true;
  }

  // ---- AK_SYSTEMS plug-in --------------------------------------------------
  // init() is the right hook: the hub builds AK_CTX and calls initAll() once the DOM exists, which
  // is exactly when a layout module wants to run. onTick does the two cheap upkeep jobs -- a
  // throttled re-pin (covers any resize path that fires no event at all, e.g. a fold) and the
  // district-title fade. Both are guarded; neither allocates.
  var api = {
    id: 'aklayout',
    init: function () { try { boot(); } catch (_e) {} },
    onTick: function () {
      try {
        _ticks++;
        var now = (root.performance && root.performance.now) ? root.performance.now() : Date.now();
        if (now - _lastPoll < 250) return;                 // 4Hz is plenty for a layout concern
        _lastPoll = now;
        pin(false);
        if (_mode === 'lean') pollDist(now);
      } catch (_e) {}
    }
  };
  // The include MUST sit below systems/_registry.js:422 (which defines AK_SYSTEMS) and above the
  // inline <script> at index.html:711 (so our resize listener registers first). Both ends matter;
  // see the ORDERING note in the header. If AK_SYSTEMS is missing we still function -- boot() runs
  // from the immediate path below and the resize listener is wired directly -- but the onTick
  // upkeep (district fade, event-less re-pin) is lost, so say so out loud rather than fail quietly.
  if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) {
    _registered = !!root.AK_SYSTEMS.register(api);
  }
  if (!_registered) {
    try { console.warn('[AK_LAYOUT] not registered with AK_SYSTEMS -- the <script> tag is above ' +
                       'systems/_registry.js. Layout still applies; onTick upkeep is inactive.'); } catch (_e) {}
  }

  // Boot immediately when the DOM is already parsed. The systems/*.js tags sit in <body> after the
  // markup they touch (index.html:399+, the elements are at 347-398), so document.body exists by
  // the time this runs and we do NOT have to wait for initAll(). Waiting would leave one frame at
  // 100vh, which is a visible jump on a phone. init() above is idempotent with this.
  try {
    if (doc && doc.body) boot();
    else if (doc && doc.addEventListener) doc.addEventListener('DOMContentLoaded', function () { try { boot(); } catch (_e) {} });
  } catch (_e) {}

  return {
    pin: pin,
    setChrome: setChrome,
    chrome: function () { return _mode; },
    toggleTray: toggle,
    trayOpen: function () { return _open; },
    // Locked at 1 on purpose. index.html:2519 maps radar taps with a hard-coded /100 and <=16, so
    // any scale silently misroutes fast-travel. Opt in ONLY after that line is made proportional.
    setRadarScale: function (v) {
      var n = +v;
      if (!(n > 0) || n === 1) { RADAR_SCALE = 1; return 1; }
      if (!root.__akRadarTapIsProportional) {
        try { console.warn('[AK_LAYOUT] setRadarScale ignored: index.html:2519 still hard-codes /100 and <=16, ' +
                           'so scaling the radar misroutes fast-travel. Set window.__akRadarTapIsProportional=true ' +
                           'after making that handler use r.width/r.height.'); } catch (_e) {}
        return RADAR_SCALE;
      }
      RADAR_SCALE = n; writeStyle(); return RADAR_SCALE;
    },
    radarScale: function () { return RADAR_SCALE; },
    isOn: function () { return !!_styleEl && _pinW > 0; },
    diag: function () {
      return {
        mode: _mode, trayOpen: _open, pinW: _pinW, pinH: _pinH, pins: _pins,
        ticks: _ticks, registered: _registered,
        radarScale: RADAR_SCALE, styled: !!(_styleEl && _styleEl.parentNode), tray: !!_tray,
        innerW: (root && root.innerWidth) || 0, innerH: (root && root.innerHeight) || 0
      };
    }
  };
})(window);
