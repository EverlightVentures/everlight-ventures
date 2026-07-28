/*
 * cardfx.js -- AK_CARDFX (CARD MOTION REGISTRY)
 * The rails that let EVERY card carry its own MP4 motion states with graceful
 * archetype fallbacks. Shared by ALL modes: tower lane (game.html), RPG raid
 * (index.html, later pass), minigames. Pattern mirrors classes.js sidecar:
 * plain JS, headless-safe, window-guarded, NO em-dashes (hook law, use --).
 *
 * Public API (window.AK_CARDFX):
 *   resolve(cardOrUnit, state)          -> video PATH or null
 *       fallback chain: assets/cardfx/<cardNumber>_<state>.mp4
 *                    -> assets/cardfx/class_<combatclass>_<state>.mp4
 *                    -> null
 *       states: 'idle' | 'engage' | 'vs_structure' | 'walk'
 *       accepts an engine unit (u.card w/ cardNumber+combatClass) or canon card.
 *       404s are CACHED in a dead map (video onerror marks dead); a tried-and-
 *       dead path never re-probes, so resolve() skips straight to the fallback.
 *   acquire(path)                       -> playing <video> el (pooled, max 3) or null
 *       reuse if a pool slot already holds this src, else claim the
 *       least-recently-used unheld slot. Muted, loop, playsinline, preload=none.
 *   release(elOrPath)                   -> mark unheld; auto-paused after 2s unused
 *   playOverlay(x, y, sizePx, path, ms) -> transient killstreak-style screen-blend
 *       overlay at fixed SCREEN coords (x,y = center), capped 2.5s, self-removing,
 *       max 2 concurrent (excess dropped silently). Returns the el or null.
 *   markDead(path)                      -> manually blacklist a path
 *   STATES                              -> ['idle','engage','vs_structure','walk']
 *
 * document.hidden pauses every pooled video; visibility return resumes held ones.
 * Fully guarded: never throws, no-ops headless (node --check safe).
 */
(function (global) {
  'use strict';

  var STATES = ['idle', 'engage', 'vs_structure', 'walk'];
  var POOL_MAX = 8;         // shared <video> elements for looped states. walk clips resolve to class_<combatclass>_walk.mp4, so the pool keys BY combatClass -- a handful of shared els cover the whole board (~6 moving classes + headroom), mirroring the hub's shared roamer clips.
  var OVERLAY_MAX = 2;      // concurrent transient overlays
  var OVERLAY_CAP_MS = 2500;
  var RELEASE_MS = 2000;    // unheld + unused this long -> pause

  var DEAD = {};            // path -> true (probed and 404/failed; never re-probe)
  var POOL = [];            // [{el, path, lastUse, held}]
  var overlayCount = 0;

  var HEADLESS = (typeof document === 'undefined');

  // ---- card normalization: engine unit (u.card) or canon card ----
  function cardOf(x) { return (x && x.card && typeof x.card === 'object') ? x.card : x; }

  function classOf(card, num) {
    var cls = card && card.combatClass;
    if (!cls && num && typeof global.AK_CLASS_GET === 'function') {
      try { var row = global.AK_CLASS_GET(num); cls = row && (row.cls || row.combatClass); } catch (e) {}
    }
    return cls ? String(cls).toLowerCase() : null;
  }

  function candidates(cardOrUnit, state) {
    var out = [];
    var card = cardOf(cardOrUnit);
    if (!card || !state || STATES.indexOf(state) < 0) return out;
    var num = card.cardNumber || null;
    if (num) out.push('assets/cardfx/' + num + '_' + state + '.mp4');
    var cls = classOf(card, num);
    if (cls) out.push('assets/cardfx/class_' + cls + '_' + state + '.mp4');
    return out;
  }

  // resolve: first candidate NOT already known-dead, else null.
  function resolve(cardOrUnit, state) {
    try {
      var cands = candidates(cardOrUnit, state);
      for (var i = 0; i < cands.length; i++) { if (!DEAD[cands[i]]) return cands[i]; }
    } catch (e) {}
    return null;
  }

  function markDead(path) { if (path) DEAD[path] = true; }

  // ---- pooled looping videos (idle states etc.) ----
  function mkVideo() {
    var v = document.createElement('video');
    v.muted = true; v.loop = true; v.playsInline = true;
    v.setAttribute('playsinline', ''); v.setAttribute('muted', '');
    v.preload = 'none';
    return v;
  }

  function acquire(path) {
    if (HEADLESS || !path || DEAD[path]) return null;
    try {
      var now = Date.now(), i, s;
      // reuse: a slot already loaded with this src
      for (i = 0; i < POOL.length; i++) {
        s = POOL[i];
        if (s.path === path) {
          s.lastUse = now; s.held = true;
          try { var rp = s.el.play(); if (rp && rp.catch) rp.catch(function () {}); } catch (e) {}
          return s.el;
        }
      }
      // claim: grow to POOL_MAX, else the least-recently-used unheld slot
      var slot = null;
      if (POOL.length < POOL_MAX) { slot = { el: mkVideo(), path: null, lastUse: 0, held: false }; POOL.push(slot); }
      else {
        for (i = 0; i < POOL.length; i++) {
          s = POOL[i];
          if (s.held) continue;
          if (!slot || s.lastUse < slot.lastUse) slot = s;
        }
      }
      if (!slot) return null; // every slot held; drop silently
      slot.path = path; slot.lastUse = now; slot.held = true;
      var el = slot.el;
      el.onerror = function () {
        markDead(path);
        if (slot.path === path) { slot.path = null; slot.held = false; try { el.pause(); } catch (e) {} }
      };
      el.src = path;
      try { el.load(); } catch (e) {}
      try { var p = el.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {}
      return el;
    } catch (e) { return null; }
  }

  function release(elOrPath) {
    try {
      for (var i = 0; i < POOL.length; i++) {
        var s = POOL[i];
        if (s.el === elOrPath || (elOrPath && s.path === elOrPath)) { s.held = false; s.lastUse = Date.now(); }
      }
    } catch (e) {}
  }

  // sweep: pause unheld slots after RELEASE_MS of no use (battery + decode budget)
  if (!HEADLESS) {
    setInterval(function () {
      try {
        var now = Date.now();
        for (var i = 0; i < POOL.length; i++) {
          var s = POOL[i];
          if (!s.held && s.path && (now - s.lastUse) > RELEASE_MS && !s.el.paused) { try { s.el.pause(); } catch (e) {} }
        }
      } catch (e) {}
    }, 1000);

    document.addEventListener('visibilitychange', function () {
      try {
        var i;
        if (document.hidden) { for (i = 0; i < POOL.length; i++) { try { POOL[i].el.pause(); } catch (e) {} } }
        else {
          for (i = 0; i < POOL.length; i++) {
            var s = POOL[i];
            if (s.held && s.path) { try { var p = s.el.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {} }
          }
        }
      } catch (e) {}
    });
  }

  // ---- transient screen-blend overlay (the AK-KSFX pattern, generalized) ----
  // x,y = SCREEN center coords (caller adds canvas.getBoundingClientRect offsets).
  function playOverlay(x, y, sizePx, path, ms) {
    if (HEADLESS) return null;
    try {
      if (!path || DEAD[path]) return null;
      if (overlayCount >= OVERLAY_MAX) return null; // drop excess silently
      overlayCount++;
      var dur = Math.max(200, Math.min((ms | 0) || OVERLAY_CAP_MS, OVERLAY_CAP_MS));
      var sz = Math.max(24, sizePx | 0 || 120);
      var v = document.createElement('video');
      v.muted = true; v.playsInline = true;
      v.setAttribute('playsinline', ''); v.setAttribute('muted', '');
      v.autoplay = true; v.src = path;
      v.style.cssText = 'position:fixed;left:' + (x - sz / 2) + 'px;top:' + (y - sz / 2) +
        'px;width:' + sz + 'px;height:' + sz + 'px;object-fit:cover;z-index:50;' +
        'pointer-events:none;mix-blend-mode:screen;';
      var done = false;
      function kill() { if (done) return; done = true; overlayCount = Math.max(0, overlayCount - 1); try { v.remove(); } catch (e) {} }
      v.addEventListener('ended', kill);
      v.addEventListener('error', function () { markDead(path); kill(); });
      document.body.appendChild(v);
      setTimeout(kill, dur);
      try { var p = v.play(); if (p && p.catch) p.catch(kill); } catch (e) { kill(); }
      return v;
    } catch (e) { return null; }
  }

  global.AK_CARDFX = {
    STATES: STATES,
    resolve: resolve,
    acquire: acquire,
    release: release,
    playOverlay: playOverlay,
    markDead: markDead,
    _dead: DEAD,
    _pool: POOL
  };
}(typeof window !== 'undefined' ? window : this));
