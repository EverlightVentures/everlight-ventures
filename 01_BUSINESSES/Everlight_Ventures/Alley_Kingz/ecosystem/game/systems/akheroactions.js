/* ALLEY KINGZ -- AK_HEROACTIONS: one tap-button per animation the selected hero's GLB actually ships.
 * AK-HEROACTIONS 2026-07-28 (operator: "there should be action buttons for each of the animations that
 * are built out for our heros in their glb").
 *
 * WHAT IT DOES
 * The hub already drives ONE clip per hero at a time (hub3d.js: idle when still, walk/run when moving).
 * Every OTHER clip in the export -- the jabs, kicks, the guard, the taunts -- was dead weight nobody
 * could ever see. This module renders a small vertical rail of buttons, one PER non-locomotion clip of
 * the CURRENTLY SELECTED hero, and on tap plays that clip on the live <model-viewer> then hands control
 * back so the hero returns to idle. Switch hero -> the rail rebuilds for the new GLB. Deterministic, no
 * per-frame allocation, and a three.js/model-viewer failure costs nothing (no mv -> the rail hides and
 * the 2D game is untouched).
 *
 * ===========================================================================================
 * THE MAPS ARE MEASURED, NOT NAMED. Tripo exports every clip as "NlaTrack.00N" -- the names carry ZERO
 * meaning, so a button that trusted a name would be labelled gibberish and could fire a 17-second
 * victory cinematic where the player wanted a jab. Every clip in all three GLBs was parsed straight out
 * of the animation accessors (per-bone quaternion sweep in degrees, split by body region via the 43
 * named bones -- arm vs leg vs head vs spine -- plus root translation range in model units) and
 * classified by that signature. The measurement reproduces hub3d's independently-verified locomotion
 * indices EXACTLY (bcardd idle2/walk10/run7, balboa idle0/walk4), which is the proof the method is sound.
 *
 * FULL MEASURED TABLE (deg swept per region | tRange = root travel in model units | dur seconds):
 *   bcardd.glb (14 clips)          arm    leg   trans   dur   -> role
 *     idx 0  DODGE     balanced   1644   1843   0.096  1.38   quick bob/weave, low travel
 *     idx 1  COMBO     sustained  2592   2175   0.000  5.54   long shadow-box flurry, no travel
 *     idx 2  (idle)               163      53   0.004  6.00   * LOCOMOTION -- hub3d idle, excluded
 *     idx 3  (cine)               521     555   0.095 17.58   * 17.6s cinematic, excluded (see NOTE)
 *     idx 4  STRIKE    steps in   1773   1282   0.241  3.88   moderate hit, small forward step
 *     idx 5  (cine)              1544    1425   0.090 15.58   * 15.6s cinematic, excluded
 *     idx 6  GUARD     arm-domin  3687   1605   0.000  5.38   hands up, highest arm energy, no travel
 *     idx 7  (run)               6075   3453   2.295  2.75   * LOCOMOTION -- hub3d run, excluded
 *     idx 8  TAUNT     emote      1093    837   0.000  2.54   arm-lean emote, no travel
 *     idx 9  HOOK      explosive  3226   2575   0.000  1.29   shortest+hottest, arm>leg = fast punch
 *     idx 10 (walk)               869    1925   1.202  2.38   * LOCOMOTION -- hub3d walk, excluded
 *     idx 11 JAB       arm-domin  3370   1923   0.101  2.79   sharp arm strike (1.75x leg)
 *     idx 12 POSE      emote      1035    808   0.000  2.21   second emote, no travel
 *     idx 13 KICK      leg-domin  2280   2541   0.397  2.50   ONLY leg-dominant action + most travel
 *   balboa.glb (8 clips) -- SAME 43-bone rig, matched to bcardd by (arm,leg,trans) signature:
 *     idx 0 (idle=bcardd2)  idx 1 JAB(=b11)  idx 2 POSE(=b12)  idx 3 GUARD(=b6)
 *     idx 4 (walk=bcardd10) idx 5 STRIKE(=b4) idx 6 HOOK(=b9)  idx 7 TAUNT(=b8)
 *     Balboa has NO run clip (no counterpart to b7) and NO kick (no counterpart to b13, the only
 *     leg-dominant action). Do NOT invent a KICK here -- there is no clip for it.
 *   jagged.glb (4 clips) -- rig-shared, matched the same way:
 *     idx 0 (walk=bcardd10, trans 1.36 leg-dominant)   idx 1 (idle=bcardd2, 6s trans 0.004)
 *     idx 2 HOOK(=b9, 1.29s explosive)                 idx 3 STRIKE(=b4, forward step)
 *     ** hub3d.js CLIP_BY_MODEL['jagged.glb'] = {idle:3, walk:1, run:0} IS WRONG: measurement proves
 *        idle=1 and walk=0. That is a hub3d locomotion bug (flagged to Wire) and NOT this module's job.
 *        Our buttons play clips by their true index directly, so they are correct regardless of it; we
 *        only excluded the REAL locomotion indices (0,1) from getting buttons.
 * ===========================================================================================
 *
 * NOTE -- WHY LOCOMOTION AND CINEMATICS ARE EXCLUDED. idle/walk/run already have a driver (movement),
 * so a button for them is noise. The two long clips (bcardd idx3 17.6s, idx5 15.6s) are cutscene-length
 * story beats; wiring them to a spam-button would freeze the hero mid-district in a pose for 17 seconds.
 * "Action buttons" means short, repeatable actions -- everything else here is exactly that.
 *
 * HOW PLAYBACK WINS THE RACE WITH hub3d WITHOUT EDITING IT. hub3d only assigns mv.animationName when
 * ITS computed want-clip CHANGES (hub3d.js:241 `if (want && curAnim !== want)`), and it tracks its own
 * curAnim, not the element's. While the hero stands still, hub3d's want stays idle and its curAnim stays
 * idle, so it re-asserts NOTHING -- meaning our mv.animationName = actionClip STICKS until the player
 * moves (walking flips hub3d's want to walk != curAnim, hub3d rebinds, and our action is correctly
 * cancelled -- you literally walk out of the punch). When the hold expires we set the element back to
 * the MEASURED-correct idle clip ourselves (hub3d will not fight it, same curAnim logic). model-viewer
 * loops the active clip, so holding for the clip's own duration = it plays through ~once, then idle.
 *
 * WHY SELF-DRIVEN rAF AND NOT AK_SYSTEMS.onTick: the host only calls AK_SYSTEMS.tickAll() while
 * state==='IN_ZONE' (index.html:2745) -- registered onTicks never fire in a raid or a menu. The RUN/PUNCH
 * buttons dodge that by running their show/hide straight in loop() every frame (index.html:2657-2660).
 * We do the same shape with our own throttled rAF loop, gated on the ONE unambiguous "the 3D hero is on
 * screen" signal the hub already maintains: window.__hero3d.active (hub3d sets it true only once the
 * model-viewer is visible, false 160ms after the hub stops feeding it -- i.e. in interiors, menus, and
 * flat raids). That makes the rail self-hide EXACTLY where the other HUD buttons do, with no host edit
 * beyond the one <script> include.
 *
 * Safe DOM only (createElement/textContent), no innerHTML. Integration = ONE script tag after hub3d.js.
 */
window.AK_HEROACTIONS = (function (root) {
  'use strict';

  // Per-model action list. idx = clip index (== availableAnimations index; model-viewer exposes clips
  // by NAME in accessor order). dur = MEASURED seconds, used as the play-once hold. kind is cosmetic
  // grouping only -- this module does no gameplay damage (that is akPunch()'s job; keeping actions
  // purely visual keeps them deterministic and decoupled from RAID internals).
  /* AK-3DALL 2026-07-28: rebuilt for the new *_3d_all hero GLBs. Every idx below was RE-MEASURED from
   * the new export's animation accessors (scratchpad/glb_measure.py -> gen_tables.py): locomotion
   * (idle/walk/run) is excluded, then the remaining clips are classified by motion signature --
   * leg-dominant -> KICK, highest arm energy -> JAB/HOOK/STRIKE, longest -> COMBO, quietest held ->
   * GUARD, head/emote -> TAUNT/POSE. LOCOMOTION indices are high-confidence; the individual combat
   * LABELS are a best-effort from motion analysis and may want a render-verify pass to confirm e.g.
   * JAB vs HOOK -- but every button fires a REAL, correct combat clip regardless of its label. */
  /* AK-CLIPFIX 2026-07-28 (operator: "why a hook I dash forward"). Old table mapped combat buttons
   * onto LEG-lunge clips, so a hook played a forward step. RE-MEASURED from the GLB accessors:
   * PUNCH buttons fire ONLY arm-dominant clips, KICK fires the leg-dominant non-locomotion clip,
   * and NO button fires idle/walk/run. Labels are best-effort by energy; each fires a real clip. */
  var ACTIONS = {
    'bcardd.glb': [
      { idx:  3, label: 'JAB',    glyph: '👊', kind: 'combat' },
      { idx:  6, label: 'HOOK',   glyph: '🥊', kind: 'combat' },
      { idx:  8, label: 'STRIKE', glyph: '⚔', kind: 'combat' },
      { idx: 12, label: 'COMBO',  glyph: '💥', kind: 'combat' },
      { idx:  1, label: 'KICK',   glyph: '🦵', kind: 'combat' }
    ],
    'balboa.glb': [
      { idx: 14, label: 'JAB',    glyph: '👊', kind: 'combat' },
      { idx: 10, label: 'HOOK',   glyph: '🥊', kind: 'combat' },
      { idx:  9, label: 'STRIKE', glyph: '⚔', kind: 'combat' },
      { idx:  3, label: 'COMBO',  glyph: '💥', kind: 'combat' },
      { idx:  0, label: 'KICK',   glyph: '🦵', kind: 'combat' }
    ],
    'jagged.glb': [
      { idx:  5, label: 'JAB',    glyph: '👊', kind: 'combat' },
      { idx: 11, label: 'HOOK',   glyph: '🥊', kind: 'combat' },
      { idx: 13, label: 'STRIKE', glyph: '⚔', kind: 'combat' },
      { idx:  2, label: 'COMBO',  glyph: '💥', kind: 'combat' },
      { idx:  0, label: 'KICK',   glyph: '🦵', kind: 'combat' }
    ],
    'rottweiler.glb': [
      { idx: 10, label: 'JAB',    glyph: '👊', kind: 'combat' },
      { idx:  1, label: 'HOOK',   glyph: '🥊', kind: 'combat' },
      { idx:  0, label: 'KICK',   glyph: '🦵', kind: 'combat' }
    ],
    'bulldog.glb': [
      { idx:  2, label: 'JAB',    glyph: '👊', kind: 'combat' },
      { idx:  0, label: 'HOOK',   glyph: '🥊', kind: 'combat' },
      { idx:  5, label: 'STRIKE', glyph: '⚔', kind: 'combat' },
      { idx:  4, label: 'KICK',   glyph: '🦵', kind: 'combat' }
    ],
    'malamute.glb': [
      { idx:  9, label: 'JAB',    glyph: '👊', kind: 'combat' },
      { idx:  3, label: 'HOOK',   glyph: '🥊', kind: 'combat' },
      { idx:  1, label: 'STRIKE', glyph: '⚔', kind: 'combat' },
      { idx:  8, label: 'KICK',   glyph: '🦵', kind: 'combat' }
    ]
  };

  // The MEASURED-correct idle clip index per model. Used to return the hero to a real idle when an
  // action's hold expires. AK-3DALL 2026-07-28: re-measured for the new GLBs.
  var IDLE_IDX = {
    'bcardd.glb': 5, 'balboa.glb': 15, 'jagged.glb': 9,
    'bulldog.glb': 1, 'rottweiler.glb': 4, 'malamute.glb': 11
  };

  var HOLD_CAP_MS = 5000;   // never lock the hero longer than this from a single tap
  var UPKEEP_EVERY = 6;     // throttle show/hide/build upkeep to ~every 6th frame (cheap, off hot path)

  var S = {
    bar: null, mv: null, model: '', names: [],
    acting: 0, curName: '', idleName: '',   // action-hold state
    tick: 0, shown: false
  };

  function nowMs() { return (root.performance && root.performance.now) ? root.performance.now() : Date.now(); }

  /* Resolve the hero <model-viewer>. hub3d builds it lazily and never exposes it; the one stable
   * discriminator is z-index 3 (hub3d.js:168 -- crew units are z-index 2). Re-resolve if torn out. */
  function heroEl() {
    if (S.mv && S.mv.isConnected) return S.mv;
    S.mv = null;
    try {
      var all = document.querySelectorAll('model-viewer');
      for (var i = 0; i < all.length; i++) {
        if (all[i].style && all[i].style.zIndex === '3') { S.mv = all[i]; break; }
      }
      if (!S.mv && all.length === 1) S.mv = all[0];   // only one on stage = it is the hero
    } catch (_e) { S.mv = null; }
    return S.mv;
  }

  function modelOf(mv) {
    try { return (mv.getAttribute('src') || '').split('/').pop() || ''; } catch (_e) { return ''; }
  }
  function actionsFor(model) {
    for (var k in ACTIONS) { if (model.indexOf(k) !== -1) return ACTIONS[k]; }
    return null;
  }
  function idleNameFor(model, names) {
    var idx = 2;   // hub3d CLIP_DEFAULT idle
    for (var k in IDLE_IDX) { if (model.indexOf(k) !== -1) { idx = IDLE_IDX[k]; break; } }
    return names[idx] || names[0] || '';
  }
  function clearKids(el) { while (el.firstChild) el.removeChild(el.firstChild); }

  function ensureBar() {
    if (S.bar && S.bar.isConnected) return S.bar;
    var b = document.getElementById('ak-heroact-bar');
    if (!b) {
      b = document.createElement('div');
      b.id = 'ak-heroact-bar';
      // Right margin, anchored into the CLEAR BAND between the top-right minimap (renders ~y28-165 on a
      // 390x844 phone) and the RUN/PUNCH buttons pinned bottom-right (index.html #runbtn/#punchbtn:
      // right:14/82px, bottom:150px -> their top is ~y628). top:172 + 9 buttons of 44px/5px gap = 436px
      // ends at ~y608, so the full rail sits between the two with NO overlap and NO scroll needed on a
      // normal phone. max-height + scroll is the safety net for unusually short viewports only.
      b.style.cssText = 'position:fixed;right:8px;top:172px;z-index:6;display:flex;flex-direction:column;' +
        'gap:5px;pointer-events:none;max-height:calc(100vh - 210px);overflow-y:auto;' +
        '-webkit-overflow-scrolling:touch;';
      document.body.appendChild(b);
    }
    S.bar = b; return b;
  }

  function makeButton(nm, a) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.setAttribute('data-clip', nm);
    btn.setAttribute('aria-label', a.label);
    var g = document.createElement('span');
    g.textContent = a.glyph;
    g.style.cssText = 'font-size:19px;line-height:1';
    var l = document.createElement('span');
    l.textContent = a.label;
    l.style.cssText = 'font-size:8px;font-weight:800;letter-spacing:.03em;color:#e8c55a;margin-top:1px';
    btn.appendChild(g); btn.appendChild(l);
    btn.style.cssText = 'pointer-events:auto;width:44px;height:44px;border-radius:12px;flex:0 0 auto;' +
      'display:flex;flex-direction:column;align-items:center;justify-content:center;' +
      'background:radial-gradient(circle at 40% 28%,rgba(255,255,255,.16),#241d10 60%,#140f08 130%);' +
      'border:2px solid rgba(232,197,90,.5);box-shadow:0 3px 9px rgba(0,0,0,.5);' +
      'touch-action:manipulation;-webkit-tap-highlight-color:transparent;';
    // click, not pointerdown, so a scroll-drag on the rail does not fire an action.
    btn.addEventListener('click', function (ev) { ev.preventDefault(); play(nm, a); }, { passive: false });
    return btn;
  }

  /* (Re)build the rail for the model currently on the hero element. Idempotent: no-op if the model has
   * not changed and the bar already has buttons. Allocates DOM only on a real model switch. */
  function build() {
    var mv = heroEl(); if (!mv) return false;
    var model = modelOf(mv);
    var names = mv.availableAnimations || [];
    if (!names.length) return false;                 // GLB not loaded yet -> try again next upkeep
    var acts = actionsFor(model);
    if (!acts) return false;                          // unknown hero model -> no rail (never guess clips)
    if (model === S.model && S.bar && S.bar.childNodes.length) return true;   // already built for this hero
    S.model = model; S.names = names; S.idleName = idleNameFor(model, names);
    var bar = ensureBar(); clearKids(bar);
    /* AK-EMOTE-COLLAPSE 2026-07-29 (contextual-UI declutter): the 9-button rail crowded the roam view.
     * It now defaults COLLAPSED to a single glove chip; tap to expand the fight/emote buttons, tap to
     * close. Every action stays one tap away, but a district walk isn't buried under 9 buttons. Persisted. */
    var open = false; try { open = localStorage.getItem('ak_emote_open') === '1'; } catch (_e) {}
    var list = document.createElement('div');
    list.id = 'ak-heroact-list';
    list.style.cssText = 'display:' + (open ? 'flex' : 'none') + ';flex-direction:column;gap:5px;';
    var tog = document.createElement('button');
    tog.type = 'button'; tog.setAttribute('aria-label', 'toggle fight moves');
    tog.textContent = open ? '▾' : '🥊';
    tog.style.cssText = 'pointer-events:auto;width:44px;height:44px;border-radius:12px;flex:0 0 auto;font-size:18px;' +
      'display:flex;align-items:center;justify-content:center;color:#e8c55a;' +
      'background:radial-gradient(circle at 40% 28%,rgba(255,255,255,.16),#241d10 60%,#140f08 130%);' +
      'border:2px solid rgba(232,197,90,.6);box-shadow:0 3px 9px rgba(0,0,0,.5);touch-action:manipulation;';
    tog.addEventListener('click', function (ev) {
      ev.preventDefault();
      var o = list.style.display === 'none';         // currently hidden -> open it
      list.style.display = o ? 'flex' : 'none';
      tog.textContent = o ? '▾' : '🥊';
      try { localStorage.setItem('ak_emote_open', o ? '1' : '0'); } catch (_e) {}
    }, { passive: false });
    bar.appendChild(tog); bar.appendChild(list);
    for (var i = 0; i < acts.length; i++) {
      var a = acts[i], nm = names[a.idx];
      if (!nm) continue;                             // this export lacks that index -> skip, no crash
      list.appendChild(makeButton(nm, a));
    }
    return true;
  }

  function show() { if (S.bar && !S.shown) { S.bar.style.display = 'flex'; S.shown = true; } }
  function hide() { if (S.bar && S.shown) { S.bar.style.display = 'none'; S.shown = false; } }

  /* Play one action clip. Sets the element's animation, records an expiry, and lets model-viewer loop
   * it until the hold ends. No reassert loop -- while the hero is still, hub3d does not fight us (see
   * header); if the player moves, hub3d rebinds to walk, which is the correct cancel. */
  function play(nm, a) {
    var mv = heroEl(); if (!mv || !nm) return;
    var hold = Math.min(HOLD_CAP_MS, Math.max(500, (a.dur || 1.5) * 1000));
    S.acting = nowMs() + hold; S.curName = nm;
    try { mv.animationName = nm; mv.play(); } catch (_e) {}
    try { root.__akHeroAction = { name: nm, until: S.acting }; } catch (_e2) {}   // optional hook for hub3d
    try { if (root.navigator && navigator.vibrate) navigator.vibrate(a.kind === 'emote' ? 8 : [8, 20, 8]); } catch (_e3) {}
  }

  /* Finisher: when the hold expires, return the hero to the MEASURED-correct idle clip so the action
   * does not loop forever. Only acts if the element is still on our action clip (if the player walked,
   * hub3d already rebound and we leave it alone). Runs every frame but is a couple of primitive reads. */
  function finish() {
    if (!S.acting) return;
    if (nowMs() < S.acting) return;
    S.acting = 0;
    try { root.__akHeroAction = null; } catch (_e) {}
    var mv = heroEl(); if (!mv) return;
    try {
      if (mv.animationName === S.curName && S.idleName) { mv.animationName = S.idleName; mv.play(); }
    } catch (_e2) {}
    S.curName = '';
  }

  /* Upkeep: show the rail exactly when the live 3D hero is visible; rebuild on hero switch; hide
   * otherwise. __hero3d.active is the hub's own "3D hero on screen" flag -- true only while the hub is
   * feeding positions (i.e. walking a district/raid), false in interiors, menus, and where the hero is
   * not 3D. That is the same surface the other HUD buttons self-hide against. */
  function upkeep() {
    var h3 = root.__hero3d;
    var mv = heroEl();
    var live = !!(h3 && h3.active) && !!mv && (mv.availableAnimations || []).length > 0;
    if (!live) { hide(); return; }
    if (modelOf(mv) !== S.model || !S.bar || !S.bar.childNodes.length) {
      if (!build()) { hide(); return; }
    }
    show();
  }

  (function frame() {
    try {
      finish();                                        // cheap, every frame -> crisp return-to-idle
      if ((++S.tick % UPKEEP_EVERY) === 0) upkeep();    // show/hide/build off the hot path
    } catch (_e) {}
    try { root.requestAnimationFrame(frame); } catch (_e2) {}
  })();

  var api = {
    id: 'akheroactions',
    // no onTick registration: the host would only tick it in IN_ZONE; we self-drive so raids work too.
    play: function (label) {   // programmatic trigger (tests / tutorials): play by label on current hero
      var acts = actionsFor(S.model) || [];
      for (var i = 0; i < acts.length; i++) {
        if (acts[i].label === label) { var nm = S.names[acts[i].idx]; if (nm) play(nm, acts[i]); return true; }
      }
      return false;
    },
    rebuild: function () { S.model = ''; return build(); },
    diag: function () {
      return { model: S.model, buttons: S.bar ? S.bar.childNodes.length : 0, clips: S.names.length,
               shown: S.shown, acting: S.acting > 0, idle: S.idleName };
    },
    ACTIONS: ACTIONS, IDLE_IDX: IDLE_IDX
  };
  // Register for diag/discoverability only; visibility is self-driven (see above).
  if (root.AK_SYSTEMS && root.AK_SYSTEMS.register) root.AK_SYSTEMS.register(api);
  return api;
})(window);
