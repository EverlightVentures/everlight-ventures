/*
 * bossfx.js -- AK_BOSSFX (BOSS-BATTLE visual fx layer, adrenaline grammar)
 * The big-fight overlay: a dramatic boss ENTRANCE, a cinematic segmented
 * BOSS HP BAR, combat HIT pops with screen shake, PHASE-transition punches,
 * a persistent low-HP ENRAGE state, and the killing-blow SLOW-MO finish.
 * Studies systems/manga_fx.js: reuses AK_MANGA.impactFrame for the ink hit
 * (guarded), mirrors its style constants, faction palette, esc() escaping,
 * canvas/overlay recipes and single-book look. Bosses are named canon cards
 * (bible Section 3, act-10 boss table) -- this layer only paints; the caller
 * passes the canon name/accent/portrait.
 *
 * Plain JS, headless-safe (node --check clean), window-guarded, NO em-dashes
 * (hook law, use --), NO emoji. Zero load-time DOM: nothing is created until
 * a method is called. Every dependency (AK_MANGA, matchMedia, rAF) is
 * optional and degrades gracefully. no document = every method no-ops.
 *
 * Public API (window.AK_BOSSFX):
 *   enter(opts)        -> dramatic boss ENTRANCE: a heavy vignette closes in,
 *                         the boss name slams with a shockwave + screen flash,
 *                         (reuses AK_MANGA.impactFrame if present). Returns a
 *                         Promise resolving when the entrance clears, so the
 *                         caller chains into combat. opts={name,accent,portrait}.
 *   hpBar(cur,max,opts)-> mount/update the big BOSS HP BAR pinned top-center:
 *                         phase-segmented pips, gold-on-black, chunky, damage
 *                         flash on decrease, cracks as it empties. Call on
 *                         every damage tick; auto-hides at 0. opts={name,phases,accent}.
 *   hit(x,y,opts)      -> combat hit pop: AK_MANGA.impactFrame (guarded) + a
 *                         hit-flash + a brief SCREEN SHAKE. opts.heavy = bigger
 *                         frame + longer shake.
 *   phase(n)           -> PHASE-TRANSITION punch: screen flash + a rising tint
 *                         + the HP bar pip lighting -- the boss powered up.
 *   enrage(on)         -> persistent low-HP ENRAGE: a pulsing crimson edge
 *                         vignette + faster ambient shake. enrage(false) clears.
 *   slowmoFinish(cb)   -> KILLING-BLOW moment: brief slow-motion + desaturate +
 *                         white impact bloom, then calls cb. Sets a time-scale
 *                         hint at window.__akBossTimeScale the wire lane reads.
 *   shake(intensity,ms)-> standalone screen shake (translate #app, decaying).
 *   clear()            -> removes all overlays, resets shake/enrage/time-scale.
 *
 * TIME-SCALE HINT: window.__akBossTimeScale (number, default 1). This layer
 * never freezes the sim; it only writes a hint. slowmoFinish() drops it toward
 * ~0.3 for the finish beat, then restores it to 1. The wire lane that owns the
 * combat clock should multiply its dt by (window.__akBossTimeScale || 1).
 */
(function (global) {
  'use strict';

  if (global.AK_BOSSFX) return;
  var HEADLESS = (typeof document === 'undefined');

  /* ---- style constants mirrored from manga_fx.js / chronicles.js (ONE look) */
  var GOLD = '#e8c55a';
  var GOLD_HI = '#f6dc80';
  var GOLD_DEEP = '#b8922e';
  var INK = '#05050a';
  var CRIMSON = '#c81f2e';                 // enrage / low-HP red
  var CRIMSON_DEEP = '#780810';
  var DISPLAY_FONT = "'Bangers','Luckiest Guy','Comic Neue','Arial Black',Inter,system-ui,sans-serif";
  // Faction accent tints -- the ONE canon palette (mirrors manga_fx FAC_COL).
  var FAC_COL = {
    boneguard_crew:    '#C9772E',
    zoomie_syndicate:  '#FF2E88',
    leashbreak_tactix: '#7B5CFF',
    k9_circuitry:      '#00E0C0',
    neutral:           '#c9a84c'
  };

  // z-band: impact flash sits at 60 (manga contract), manga pages at 80.
  var Z_ENRAGE = 62;                       // edge vignette, above impact
  var Z_HP = 78;                           // boss HP bar, below manga pages
  var Z_ENTER = 90;                        // entrance splash above pages
  var Z_FINISH = 96;                       // slow-mo desaturate + bloom
  var Z_FLASH = 98;                        // screen flash tops everything

  var MARK = 'data-akbossfx';              // tag every overlay so clear() sweeps

  // shared time-scale hint the combat wire lane reads (see header).
  try { if (global.__akBossTimeScale == null) global.__akBossTimeScale = 1; } catch (_ts) {}

  /* =============================== helpers =============================== */

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function accentOr(ac) {
    if (!ac) return GOLD;
    var k = String(ac).toLowerCase();
    return FAC_COL[k] || String(ac);
  }
  function isImgPath(s) {
    return /\.(png|jpe?g|webp|gif|svg)(\?|$)/i.test(String(s || ''));
  }
  function tnow() {
    try { return (global.performance && global.performance.now) ? global.performance.now() : Date.now(); }
    catch (_e) { return Date.now(); }
  }
  function raf(fn) {
    try { if (typeof global.requestAnimationFrame === 'function') return global.requestAnimationFrame(fn); }
    catch (_e) {}
    return setTimeout(function () { fn(tnow()); }, 16);
  }
  function caf(id) {
    try { if (typeof global.cancelAnimationFrame === 'function') { global.cancelAnimationFrame(id); return; } }
    catch (_e) {}
    clearTimeout(id);
  }
  // reduced-motion: dampen shake + flash (mirrors modes.js/loops.js probe).
  function reduced() {
    try { return !!(global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches); }
    catch (_e) { return false; }
  }
  function ampScale() { return reduced() ? 0.34 : 1; }   // shake amplitude damp
  function opaScale() { return reduced() ? 0.5 : 1; }    // flash opacity damp

  function mk(tag, css) {
    var el = document.createElement(tag);
    if (css) el.style.cssText = css;
    return el;
  }
  // append to body + tag so clear() can sweep every overlay we ever mount
  function markBody(el) {
    try { el.setAttribute(MARK, '1'); } catch (_e) {}
    try { document.body.appendChild(el); } catch (_e2) {}
    return el;
  }
  // fade an element out then remove it
  function fadeRemove(el, ms) {
    if (!el) return;
    try {
      el.style.transition = 'opacity ' + (ms || 260) + 'ms ease';
      el.style.opacity = '0';
      setTimeout(function () { try { el.remove(); } catch (_e) {} }, (ms || 260) + 40);
    } catch (_e) { try { el.remove(); } catch (_e2) {} }
  }

  // one-shot full-screen flash (white by default), self-removing
  function flash(color, ms, maxOpa) {
    if (HEADLESS) return;
    try {
      var f = mk('div', 'position:fixed;inset:0;z-index:' + Z_FLASH + ';pointer-events:none;'
        + 'background:' + (color || '#fff7e6') + ';opacity:0;');
      markBody(f);
      var top = (maxOpa == null ? 0.82 : maxOpa) * opaScale();
      void f.offsetWidth;
      f.style.transition = 'opacity ' + (ms || 240) + 'ms ease-out';
      f.style.opacity = String(top);
      setTimeout(function () { f.style.opacity = '0'; }, 40);
      setTimeout(function () { try { f.remove(); } catch (_e) {} }, (ms || 240) + 120);
    } catch (_e) {}
  }

  // guarded reuse of the manga ink STRIKE frame
  function mangaImpact(o) {
    try {
      if (global.AK_MANGA && typeof global.AK_MANGA.impactFrame === 'function') {
        global.AK_MANGA.impactFrame(o || {});
      }
    } catch (_e) {}
  }

  /* ================================ SHAKE =============================== */
  // Translate the game root (#app / #stage / #board, else body) a few px,
  // decaying. Boss overlays live on <body> as siblings of #app, so they stay
  // pinned while the world shakes. Enrage adds a persistent ambient floor.

  var SHK = { amp: 0, t0: 0, dur: 0, ambient: 0, id: null, el: null, base: '' };

  function resolveShakeEl() {
    if (HEADLESS) return null;
    if (SHK.el) { try { if (document.contains(SHK.el)) return SHK.el; } catch (_e) {} SHK.el = null; }
    var sel = ['#app', '#stage', '#board'], el = null;
    for (var i = 0; i < sel.length; i++) {
      try { el = document.querySelector(sel[i]); } catch (_e2) { el = null; }
      if (el) break;
    }
    if (!el) el = document.body;
    SHK.el = el;
    return el;
  }

  function ensureShakeLoop() {
    if (HEADLESS || SHK.id != null) return;
    var el = resolveShakeEl();
    if (!el) return;
    SHK.base = el.style.transform || '';         // preserve any existing transform
    SHK.id = raf(shakeLoop);
  }

  function shakeLoop() {
    SHK.id = null;
    try {
      var el = resolveShakeEl();
      if (!el) return;
      var now = tnow(), impulse = 0;
      if (SHK.dur > 0) {
        var e = (now - SHK.t0) / SHK.dur;
        if (e < 1) { var k = 1 - e; impulse = SHK.amp * k * k; }   // ease-out decay
        else { SHK.dur = 0; SHK.amp = 0; }
      }
      var amp = impulse + SHK.ambient;
      if (amp <= 0.25) {
        el.style.transform = SHK.base;                            // settle exactly to base
        return;                                                   // loop stops (no reschedule)
      }
      var a = Math.random() * 6.2832;
      var dx = Math.cos(a) * amp, dy = Math.sin(a) * amp * 0.82;
      el.style.transform = SHK.base + ' translate3d(' + dx.toFixed(1) + 'px,' + dy.toFixed(1) + 'px,0)';
    } catch (_e) {}
    SHK.id = raf(shakeLoop);
  }

  function shake(intensity, ms) {
    if (HEADLESS) return;
    try {
      var amp = Math.max(0, (+intensity || 0)) * ampScale();
      var dur = Math.max(60, (+ms || 300));
      var now = tnow(), remain = 0;
      if (SHK.dur > 0) { var e = (now - SHK.t0) / SHK.dur; if (e < 1) remain = SHK.amp * (1 - e); }
      SHK.amp = Math.max(amp, remain);          // refresh: take the stronger energy
      SHK.t0 = now; SHK.dur = dur;
      ensureShakeLoop();
    } catch (_e) {}
  }

  /* =============================== enter ================================ */
  // Boss ENTRANCE: heavy vignette closes in, portrait ghosts behind, the name
  // slams with a shockwave ring + screen flash + ink strike frame. Resolves
  // when the splash clears so the caller chains straight into combat.

  var entering = false;
  function enter(opts) {
    if (HEADLESS) return Promise.resolve();
    return new Promise(function (resolve) {
      try {
        if (entering) { resolve(); return; }        // one entrance at a time
        entering = true;
        opts = opts || {};
        var ac = accentOr(opts.accent);
        var name = String(opts.name || 'THE BOSS').toUpperCase();
        var portrait = (opts.portrait && isImgPath(opts.portrait)) ? String(opts.portrait) : '';
        var RM = reduced();
        var HOLD = RM ? 620 : 1180;                 // full lifetime of the splash

        var root = mk('div', 'position:fixed;inset:0;z-index:' + Z_ENTER + ';pointer-events:none;'
          + 'display:flex;align-items:center;justify-content:center;overflow:hidden;'
          + 'font-family:Inter,system-ui,sans-serif;');

        // heavy vignette that closes IN (edges darken, scale settles from wide)
        var vig = mk('div', 'position:absolute;inset:0;'
          + 'background:radial-gradient(ellipse at 50% 50%, rgba(4,4,10,0) 30%, rgba(4,4,10,.55) 66%, rgba(2,2,6,.96) 100%);'
          + 'opacity:0;transform:scale(1.6);'
          + 'transition:opacity ' + (RM ? 200 : 360) + 'ms ease,transform ' + (RM ? 200 : 380) + 'ms cubic-bezier(.2,.8,.3,1);');
        root.appendChild(vig);

        // portrait ghost behind the name (canon art, menacing + accent-lit)
        if (portrait) {
          var pim = mk('img', 'position:absolute;left:50%;top:50%;width:min(70vw,360px);height:min(70vw,360px);'
            + 'object-fit:contain;transform:translate(-50%,-52%) scale(1.15);opacity:0;'
            + 'filter:grayscale(.35) contrast(1.05) drop-shadow(0 0 42px ' + ac + '88);'
            + 'transition:opacity ' + (RM ? 200 : 420) + 'ms ease,transform ' + (RM ? 200 : 640) + 'ms ease;');
          pim.alt = '';
          pim.onerror = function () { try { pim.style.display = 'none'; } catch (_e) {} };
          pim.src = portrait;
          root.appendChild(pim);
          setTimeout(function () { try { pim.style.opacity = '.42'; pim.style.transform = 'translate(-50%,-52%) scale(1)'; } catch (_e) {} }, RM ? 20 : 60);
        }

        // two shockwave rings that blow out from center on the slam
        function ring(delay, thick) {
          var r = mk('div', 'position:absolute;left:50%;top:50%;width:46px;height:46px;border-radius:50%;'
            + 'border:' + thick + 'px solid ' + ac + ';box-shadow:0 0 24px ' + ac + '99;'
            + 'transform:translate(-50%,-50%) scale(.2);opacity:0;');
          root.appendChild(r);
          setTimeout(function () {
            try {
              void r.offsetWidth;
              r.style.transition = 'transform ' + (RM ? 320 : 560) + 'ms cubic-bezier(.1,.7,.3,1),opacity ' + (RM ? 320 : 560) + 'ms ease-out';
              r.style.opacity = String(0.9 * opaScale());
              r.style.transform = 'translate(-50%,-50%) scale(' + (RM ? 6 : 10) + ')';
              setTimeout(function () { r.style.opacity = '0'; }, 60);
            } catch (_e) {}
          }, delay);
        }

        // the boss name, slammed in with overshoot + heavy comic ink outline
        var nm = mk('div', 'position:relative;z-index:2;max-width:94vw;text-align:center;'
          + 'font:900 clamp(38px,13vw,86px)/0.96 ' + DISPLAY_FONT + ';color:' + GOLD + ';'
          + 'text-transform:uppercase;letter-spacing:.02em;padding:0 12px;'
          + 'text-shadow:4px 4px 0 ' + INK + ',-3px -3px 0 ' + INK + ',3px -3px 0 ' + INK + ',-3px 3px 0 ' + INK
          + ',0 0 32px ' + ac + 'aa,0 16px 40px rgba(0,0,0,.9);'
          + 'transform:scale(2.4) rotate(-5deg);opacity:0;');
        nm.textContent = name;                                    // textContent = no injection
        root.appendChild(nm);

        // sub-kicker under the name
        var kick = mk('div', 'position:absolute;left:0;right:0;text-align:center;'
          + 'top:calc(50% + min(20vw,120px));z-index:2;'
          + 'font:800 11px Inter,system-ui;letter-spacing:.42em;color:' + ac + ';text-transform:uppercase;'
          + 'opacity:0;transition:opacity 300ms ease;text-shadow:0 2px 10px rgba(0,0,0,.9);');
        kick.textContent = 'BOSS';
        root.appendChild(kick);

        markBody(root);

        // choreography ------------------------------------------------------
        void root.offsetWidth;
        vig.style.opacity = '1'; vig.style.transform = 'scale(1)';

        var slamAt = RM ? 120 : 220;
        setTimeout(function () {
          try {
            void nm.offsetWidth;
            nm.style.transition = 'transform ' + (RM ? 160 : 220) + 'ms cubic-bezier(.2,1.7,.3,1),opacity ' + (RM ? 140 : 180) + 'ms ease';
            nm.style.transform = 'scale(1) rotate(-2deg)';
            nm.style.opacity = '1';
            kick.style.opacity = '.9';
          } catch (_e) {}
          flash('#fff7e6', RM ? 200 : 260, 0.85);                 // screen flash on the slam
          ring(0, 4); ring(RM ? 90 : 150, 2);                     // shockwave
          mangaImpact({ full: true, color: ac });                 // reuse the ink STRIKE frame
          shake(RM ? 5 : 13, RM ? 260 : 520);                     // the entrance hit
        }, slamAt);

        function done() {
          entering = false;
          try { root.remove(); } catch (_e) {}
          resolve();
        }
        setTimeout(function () { fadeRemove(root, RM ? 200 : 320); }, slamAt + HOLD);
        setTimeout(done, slamAt + HOLD + (RM ? 240 : 380));
      } catch (_e) { entering = false; resolve(); }
    });
  }

  /* =============================== hpBar =============================== */
  // The big cinematic boss HP bar: phase-segmented, gold-on-black, chunky,
  // pinned top-center. Damage-flashes on decrease, cracks as it empties,
  // auto-hides at 0. Built once; hpBar() re-renders on every damage tick.

  var HP = null;    // { root,name,pips[],track,fill,seg,flashEl,crackCv,phases,last,max,ac }

  function buildHp(phases, ac, name) {
    var root = mk('div', 'position:fixed;top:max(10px,env(safe-area-inset-top));left:50%;'
      + 'transform:translateX(-50%) translateY(-14px);z-index:' + Z_HP + ';'
      + 'width:min(92vw,520px);pointer-events:none;opacity:0;'
      + 'transition:opacity 260ms ease,transform 300ms cubic-bezier(.2,1.2,.4,1);'
      + 'font-family:Inter,system-ui,sans-serif;');

    var head = mk('div', 'display:flex;align-items:center;justify-content:space-between;'
      + 'gap:8px;margin:0 2px 5px;');
    var nm = mk('div', 'font:900 13px ' + DISPLAY_FONT + ';letter-spacing:.06em;color:' + GOLD + ';'
      + 'text-transform:uppercase;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'
      + 'text-shadow:1px 1px 0 ' + INK + ',0 2px 10px rgba(0,0,0,.8);');
    nm.textContent = String(name || 'BOSS').toUpperCase();
    var pipRow = mk('div', 'display:flex;gap:5px;flex:0 0 auto;');
    head.appendChild(nm); head.appendChild(pipRow);
    root.appendChild(head);

    // pips: one per phase, deplete right-to-left as the boss loses HP
    var pips = [];
    for (var i = 0; i < phases; i++) {
      var p = mk('div', 'width:11px;height:11px;border-radius:2px;border:1.5px solid ' + INK + ';'
        + 'background:' + GOLD + ';box-shadow:0 0 8px ' + GOLD + '99;'
        + 'transition:background 200ms ease,box-shadow 200ms ease,transform 160ms ease;');
      pipRow.appendChild(p);
      pips.push(p);
    }

    var track = mk('div', 'position:relative;height:22px;border-radius:5px;overflow:hidden;'
      + 'background:linear-gradient(180deg,#141018,#08060c);'
      + 'border:2px solid ' + INK + ';box-shadow:0 4px 16px rgba(0,0,0,.7),inset 0 0 0 1px rgba(232,197,90,.14);');
    var fill = mk('div', 'position:absolute;left:0;top:0;bottom:0;width:100%;'
      + 'background:linear-gradient(180deg,' + GOLD_HI + ',' + GOLD + ' 46%,' + GOLD_DEEP + ');'
      + 'box-shadow:inset 0 0 0 1px rgba(255,255,255,.25),0 0 18px ' + ac + '66;'
      + 'transition:width 260ms cubic-bezier(.3,.9,.3,1),background 200ms ease;');
    track.appendChild(fill);

    // phase divider ticks over the fill
    var seg = mk('div', 'position:absolute;inset:0;pointer-events:none;');
    for (var d = 1; d < phases; d++) {
      var tk = mk('div', 'position:absolute;top:0;bottom:0;width:2px;background:rgba(5,5,10,.85);'
        + 'left:' + (100 * d / phases).toFixed(3) + '%;box-shadow:1px 0 0 rgba(232,197,90,.2);');
      seg.appendChild(tk);
    }
    track.appendChild(seg);

    // cracks canvas (drawn over the fill as HP empties)
    var crackCv = mk('canvas', 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none;');
    track.appendChild(crackCv);

    // damage-flash overlay (white pulse on decrease)
    var flashEl = mk('div', 'position:absolute;inset:0;background:#fff;opacity:0;pointer-events:none;'
      + 'transition:opacity 220ms ease;mix-blend-mode:screen;');
    track.appendChild(flashEl);

    root.appendChild(track);
    markBody(root);
    void root.offsetWidth;
    root.style.opacity = '1';
    root.style.transform = 'translateX(-50%) translateY(0)';

    return { root: root, name: nm, pips: pips, pipRow: pipRow, track: track, fill: fill,
             seg: seg, crackCv: crackCv, flashEl: flashEl, phases: phases, last: 1, max: 1, ac: ac };
  }

  function drawCracks(cv, frac, ac) {
    try {
      var w = Math.max(1, cv.clientWidth || 300), h = Math.max(1, cv.clientHeight || 22);
      var dpr = Math.min(2, (global.devicePixelRatio || 1));
      cv.width = (w * dpr) | 0; cv.height = (h * dpr) | 0;
      var g = cv.getContext('2d');
      g.scale(dpr, dpr);
      g.clearRect(0, 0, w, h);
      if (frac >= 0.72) return;                                   // healthy = uncracked
      var sev = 1 - frac;                                         // 0..1 as it empties
      var n = Math.round(sev * 9);
      g.save();
      g.lineCap = 'round';
      for (var i = 0; i < n; i++) {
        var x = Math.random() * w, y0 = Math.random() < 0.5 ? 0 : h;
        var y1 = y0 === 0 ? h : 0;
        var seg = 3 + ((Math.random() * 3) | 0);
        g.globalAlpha = 0.25 + sev * 0.55;
        g.strokeStyle = Math.random() < 0.5 ? INK : 'rgba(255,240,200,.5)';
        g.lineWidth = 0.8 + Math.random() * 1.6;
        g.beginPath();
        g.moveTo(x, y0);
        var cx = x, cy = y0;
        for (var s = 1; s <= seg; s++) {
          cx += (Math.random() - 0.5) * (w * 0.16);
          cy = y0 + (y1 - y0) * (s / seg);
          g.lineTo(cx, cy);
        }
        g.stroke();
      }
      g.restore();
    } catch (_e) {}
  }

  function hpBar(cur, max, opts) {
    if (HEADLESS) return null;
    try {
      opts = opts || {};
      var mx = Math.max(1, +max || (HP ? HP.max : 1));
      var cv = Math.max(0, Math.min(mx, +cur || 0));
      var frac = cv / mx;
      var phases = Math.max(1, Math.min(9, (opts.phases | 0) || (HP ? HP.phases : 3)));
      var ac = accentOr(opts.accent || (HP ? HP.ac : GOLD));

      // (re)build if not mounted or the phase count changed
      if (!HP || !HP.root || HP.phases !== phases) {
        if (HP && HP.root) { try { HP.root.remove(); } catch (_e0) {} }
        HP = buildHp(phases, ac, opts.name);
        HP.max = mx; HP.last = frac; HP.ac = ac;
      }
      if (opts.name) { try { HP.name.textContent = String(opts.name).toUpperCase(); } catch (_e1) {} }
      HP.max = mx; HP.ac = ac;

      // damage detected -> flash + a small shake + brief hot-white fill
      if (frac < HP.last - 0.0005) {
        try {
          HP.flashEl.style.opacity = String(0.85 * opaScale());
          setTimeout(function () { try { HP.flashEl.style.opacity = '0'; } catch (_e) {} }, 60);
          HP.fill.style.background = '#fff2cf';
          setTimeout(function () {
            try { HP.fill.style.background = 'linear-gradient(180deg,' + GOLD_HI + ',' + GOLD + ' 46%,' + GOLD_DEEP + ')'; } catch (_e) {}
          }, 130);
        } catch (_e2) {}
        shake(3, 170);
      }

      HP.fill.style.width = (frac * 100).toFixed(2) + '%';

      // pip lighting: leftmost ceil(frac*phases) pips stay lit
      var alive = Math.ceil(frac * phases - 1e-6);
      for (var i = 0; i < HP.pips.length; i++) {
        var on = i < alive;
        HP.pips[i].style.background = on ? GOLD : '#2a2530';
        HP.pips[i].style.boxShadow = on ? ('0 0 8px ' + GOLD + '99') : 'none';
      }

      drawCracks(HP.crackCv, frac, ac);
      HP.last = frac;

      // auto-hide at 0
      if (cv <= 0) {
        flash('#fff7e6', 260, 0.7);
        var dead = HP;
        HP = null;
        fadeRemove(dead.root, 360);
      }
      return HP ? HP.root : null;
    } catch (_e) { return null; }
  }

  /* =============================== phase =============================== */
  // PHASE-TRANSITION punch: screen flash + a rising accent tint from the floor
  // + the HP bar pips pulse -- the boss just powered up.

  function phase(n) {
    if (HEADLESS) return;
    try {
      var RM = reduced();
      var ac = (HP && HP.ac) ? HP.ac : GOLD;
      flash(ac, RM ? 220 : 300, 0.5);

      // rising tint sheet from the bottom
      var rise = mk('div', 'position:fixed;inset:0;z-index:' + (Z_FLASH - 1) + ';pointer-events:none;'
        + 'background:linear-gradient(0deg,' + ac + ' 0%,' + ac + '55 26%,transparent 60%);'
        + 'opacity:0;transform:translateY(40%);');
      markBody(rise);
      void rise.offsetWidth;
      rise.style.transition = 'opacity ' + (RM ? 260 : 420) + 'ms ease,transform ' + (RM ? 360 : 620) + 'ms cubic-bezier(.2,.7,.3,1)';
      rise.style.opacity = String(0.6 * opaScale());
      rise.style.transform = 'translateY(-10%)';
      setTimeout(function () { rise.style.opacity = '0'; }, RM ? 200 : 320);
      setTimeout(function () { try { rise.remove(); } catch (_e) {} }, RM ? 620 : 1060);

      // pips flare: pulse the named phase pip (1-indexed), else pulse them all
      if (HP && HP.pips && HP.pips.length) {
        var idx = (n | 0) - 1;
        for (var i = 0; i < HP.pips.length; i++) {
          if (idx >= 0 && idx < HP.pips.length && i !== idx) continue;
          (function (p) {
            try {
              p.style.transform = 'scale(1.6)';
              p.style.boxShadow = '0 0 16px ' + ac + ',0 0 6px #fff';
              setTimeout(function () { try { p.style.transform = 'scale(1)'; } catch (_e) {} }, 240);
            } catch (_e) {}
          })(HP.pips[i]);
        }
      }
      mangaImpact({ full: true, color: ac });
      shake(RM ? 4 : 10, RM ? 240 : 460);
    } catch (_e) {}
  }

  /* =============================== enrage ============================== */
  // Persistent low-HP ENRAGE: pulsing crimson edge vignette + faster ambient
  // shake. enrage(false) clears both. (bible: enraged combat = red-black.)

  var enrageEl = null, enrageStyle = null;
  function enrage(on) {
    if (HEADLESS) return;
    try {
      if (on === false) {
        SHK.ambient = 0;                         // let the shake loop settle out
        if (enrageEl) { fadeRemove(enrageEl, 300); enrageEl = null; }
        return;
      }
      var RM = reduced();
      if (!enrageStyle) {
        enrageStyle = mk('style', '');
        enrageStyle.textContent = '@keyframes akbfEnrage{0%,100%{opacity:.5}50%{opacity:.95}}';
        try { enrageStyle.setAttribute(MARK, '1'); (document.head || document.body).appendChild(enrageStyle); }
        catch (_e0) {}
      }
      if (!enrageEl) {
        enrageEl = mk('div', 'position:fixed;inset:0;z-index:' + Z_ENRAGE + ';pointer-events:none;'
          + 'background:radial-gradient(ellipse at 50% 50%,transparent 54%,' + CRIMSON_DEEP + '47 78%,' + CRIMSON_DEEP + '99 100%);'
          + 'box-shadow:inset 0 0 90px 22px ' + CRIMSON + '80,inset 0 0 210px 60px ' + CRIMSON_DEEP + '66;'
          + 'opacity:.5;'
          + (RM ? '' : 'animation:akbfEnrage 1.15s ease-in-out infinite;'));
        markBody(enrageEl);
      }
      SHK.ambient = (RM ? 0.6 : 1.5) * ampScale();  // faster ambient shake floor
      ensureShakeLoop();
    } catch (_e) {}
  }

  /* ============================ slowmoFinish =========================== */
  // The KILLING-BLOW: brief slow-motion (a time-scale hint the wire lane reads
  // at window.__akBossTimeScale) + desaturate + a white impact bloom, then cb.

  var finishing = false;
  function slowmoFinish(cb) {
    if (HEADLESS) { try { if (typeof cb === 'function') cb(); } catch (_e) {} return; }
    try {
      if (finishing) { try { if (typeof cb === 'function') cb(); } catch (_e0) {} return; }
      finishing = true;
      var RM = reduced();
      var HOLD = RM ? 340 : 780;

      // time-scale hint: drop toward slow-mo, restored at the end
      try { global.__akBossTimeScale = RM ? 0.6 : 0.32; } catch (_e1) {}

      // desaturate the world underneath (backdrop grayscale, gracefully ignored
      // where unsupported -- the bloom still lands)
      var desat = mk('div', 'position:fixed;inset:0;z-index:' + Z_FINISH + ';pointer-events:none;opacity:0;'
        + 'background:rgba(6,6,10,.18);'
        + '-webkit-backdrop-filter:grayscale(1) brightness(.85) contrast(1.05);'
        + 'backdrop-filter:grayscale(1) brightness(.85) contrast(1.05);'
        + 'transition:opacity ' + (RM ? 120 : 200) + 'ms ease;');
      markBody(desat);
      void desat.offsetWidth;
      desat.style.opacity = '1';

      // white impact bloom from center
      var bloom = mk('div', 'position:fixed;left:50%;top:50%;z-index:' + (Z_FINISH + 1) + ';pointer-events:none;'
        + 'width:40vmax;height:40vmax;border-radius:50%;'
        + 'background:radial-gradient(circle,#fffdf5 0%,#fff2cf 34%,rgba(255,240,200,0) 70%);'
        + 'transform:translate(-50%,-50%) scale(.1);opacity:0;');
      markBody(bloom);
      void bloom.offsetWidth;
      bloom.style.transition = 'transform ' + (RM ? 260 : 520) + 'ms cubic-bezier(.15,.7,.3,1),opacity ' + (RM ? 260 : 520) + 'ms ease-out';
      bloom.style.opacity = String(0.95 * opaScale());
      bloom.style.transform = 'translate(-50%,-50%) scale(1.6)';
      setTimeout(function () { bloom.style.opacity = '0'; }, RM ? 140 : 240);

      mangaImpact({ full: true, color: '#fff7e0' });
      flash('#ffffff', RM ? 220 : 300, 0.9);
      shake(RM ? 4 : 9, RM ? 240 : 420);

      var called = false;
      function fire() {
        if (called) return;
        called = true;
        try { if (typeof cb === 'function') cb(); } catch (_e2) {}
      }
      // hand control back mid-bloom so the caller freezes/keeps its own timing
      setTimeout(fire, RM ? 180 : 380);
      setTimeout(function () {
        try { global.__akBossTimeScale = 1; } catch (_e3) {}
        fadeRemove(desat, RM ? 160 : 260);
        try { bloom.remove(); } catch (_e4) {}
        finishing = false;
        fire();                                   // safety: cb always runs once
      }, HOLD);
    } catch (_e) {
      finishing = false;
      try { global.__akBossTimeScale = 1; } catch (_e5) {}
      try { if (typeof cb === 'function') cb(); } catch (_e6) {}
    }
  }

  /* =============================== hit ================================= */
  // Combat HIT pop: the manga ink STRIKE frame (guarded reuse) + a local
  // hit-flash + a brief screen shake. heavy = bigger frame + longer shake.

  function hit(x, y, opts) {
    if (HEADLESS) return;
    try {
      opts = opts || {};
      var heavy = !!opts.heavy;
      var hasXY = (x != null && y != null);
      mangaImpact(hasXY ? { x: +x, y: +y, full: heavy } : { full: true });

      // local hit-flash bloom at the strike point (fades fast)
      if (hasXY) {
        var r = heavy ? 130 : 84;
        var hf = mk('div', 'position:fixed;z-index:' + (Z_FLASH - 1) + ';pointer-events:none;border-radius:50%;'
          + 'left:' + (+x) + 'px;top:' + (+y) + 'px;width:' + (r * 2) + 'px;height:' + (r * 2) + 'px;'
          + 'margin:-' + r + 'px 0 0 -' + r + 'px;'
          + 'background:radial-gradient(circle,#fff7e0 0%,' + GOLD_HI + 'cc 30%,rgba(232,197,90,0) 70%);'
          + 'transform:scale(.5);opacity:' + (0.9 * opaScale()).toFixed(2) + ';');
        markBody(hf);
        void hf.offsetWidth;
        hf.style.transition = 'transform 220ms cubic-bezier(.2,1.4,.4,1),opacity 240ms ease-out';
        hf.style.transform = 'scale(1.15)';
        hf.style.opacity = '0';
        setTimeout(function () { try { hf.remove(); } catch (_e) {} }, 300);
      } else {
        flash(GOLD_HI, heavy ? 200 : 150, heavy ? 0.5 : 0.32);
      }

      shake(heavy ? 11 : 6, heavy ? 380 : 200);
    } catch (_e) {}
  }

  /* =============================== clear =============================== */

  function clear() {
    if (HEADLESS) return;
    try {
      // stop + settle the shake, restore the game root transform exactly
      SHK.ambient = 0; SHK.amp = 0; SHK.dur = 0;
      if (SHK.id != null) { caf(SHK.id); SHK.id = null; }
      try { if (SHK.el) SHK.el.style.transform = SHK.base; } catch (_e0) {}
      SHK.el = null; SHK.base = '';

      try { global.__akBossTimeScale = 1; } catch (_e1) {}
      HP = null; enrageEl = null; enrageStyle = null;
      entering = false; finishing = false;

      var nodes = document.querySelectorAll('[' + MARK + ']');
      for (var i = 0; i < nodes.length; i++) { try { nodes[i].remove(); } catch (_e2) {} }
    } catch (_e) {}
  }

  /* =============================== export ============================== */

  global.AK_BOSSFX = {
    enter: enter,
    hpBar: hpBar,
    hit: hit,
    phase: phase,
    enrage: enrage,
    slowmoFinish: slowmoFinish,
    shake: shake,
    clear: clear
  };

})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));
