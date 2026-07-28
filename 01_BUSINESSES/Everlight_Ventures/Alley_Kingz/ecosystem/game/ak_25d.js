/* ===========================================================================
   ALLEY KINGZ // ak_25d.js -- SHARED 2.5D POINTER-TILT SHIM + AK25D.apply helper
   ---------------------------------------------------------------------------
   ONE canonical source for the .ak-3d pointer-tilt behaviour. Consolidates the
   byte-identical IIFE that used to live inline in game/index.html (~L568-599)
   and game/shop/shop.js (~L2594-2625). Pairs with ak_25d.css. Loaded by
   index.html, game.html and shop/shop.html. Idempotent: guarded by
   window.__akTilt so loading it alongside any leftover inline copy is a no-op.

   1) Delegated pointer handler -> writes --ak-rx/--ak-ry (deg) onto the inner
      .ak-3d-tilt of whatever .ak-3d scene the pointer is over; the CSS does the
      rest. Touch / coarse-pointer / prefers-reduced-motion = static resting tilt
      only (the shim returns early; CSS keeps the thickness, drops the steer).
   2) window.AK25D.apply(el, opts) -- wraps any DOM element in a fresh
      .ak-3d > .ak-3d-tilt scene, marking the element as the .ak-3d-face, so
      callers without the shop's wrap3d() helper (game.html lobby, system
      overlays) can promote any tile/panel to the 2.5D treatment. Idempotent.
   =========================================================================== */
(function (global) {
  "use strict";

  /* ---- 1) delegated pointer-tilt shim (verbatim de-duped copy) ------------ */
  (function () {
    if (global.__akTilt) return; global.__akTilt = true;
    if (matchMedia('(hover:none),(pointer:coarse)').matches) return;     // static tilt only
    if (matchMedia('(prefers-reduced-motion:reduce)').matches) return;
    var MAX = 9, raf = 0, pend = null;
    function apply() {
      raf = 0; if (!pend) return;
      var t = pend.tilt, r = pend.rect;
      var nx = (pend.x - r.left) / r.width - .5;     // -0.5 .. 0.5
      var ny = (pend.y - r.top) / r.height - .5;
      t.style.setProperty('--ak-ry', (nx * 2 * MAX).toFixed(2) + 'deg');
      t.style.setProperty('--ak-rx', (-ny * 2 * MAX + 3).toFixed(2) + 'deg');  // +3 = tabletop bias
      pend = null;
    }
    document.addEventListener('pointermove', function (e) {
      if (e.pointerType === 'touch') return;
      var s = e.target.closest && e.target.closest('.ak-3d'); if (!s) return;
      var t = s.querySelector('.ak-3d-tilt'); if (!t) return;
      s.classList.add('ak-3d-live');
      pend = { tilt: t, rect: s.getBoundingClientRect(), x: e.clientX, y: e.clientY };
      if (!raf) raf = requestAnimationFrame(apply);
    }, { passive: true });
    document.addEventListener('pointerout', function (e) {
      var s = e.target.closest && e.target.closest('.ak-3d'); if (!s) return;
      if (s.contains(e.relatedTarget)) return;          // pointer still inside the scene
      s.classList.remove('ak-3d-live');
      var t = s.querySelector('.ak-3d-tilt');
      if (t) { t.style.removeProperty('--ak-rx'); t.style.removeProperty('--ak-ry'); }   // eases back to rest
    }, { passive: true });
  })();

  /* ---- 2) AK25D.apply(el, opts) -- promote any element to the 2.5D scene --- */
  // opts.shadow (default false) -> add .ak-3d-shadow contact shadow (OPT-IN; only
  //   for surfaces with no existing rest box-shadow).
  // opts.sceneClass -> extra class(es) on the .ak-3d scene wrapper.
  // opts.glow -> hex/colour written to --ak-glow on the scene (pairs with the
  //   .ak25-glow utility class if also applied).
  // Returns the scene wrapper (inserted in the element's place if it was in the DOM).
  function applyEl(el, opts) {
    if (!el || el.__ak25) return el;             // idempotent
    opts = opts || {};
    var parent = el.parentNode, next = el.nextSibling;
    var scene = document.createElement('div');
    scene.className = 'ak-3d' + (opts.sceneClass ? (' ' + opts.sceneClass) : '');
    if (opts.glow) scene.style.setProperty('--ak-glow', opts.glow);
    var tilt = document.createElement('div');
    tilt.className = 'ak-3d-tilt';
    el.classList.add('ak-3d-face');
    if (opts.shadow) el.classList.add('ak-3d-shadow');
    tilt.appendChild(el);
    scene.appendChild(tilt);
    if (parent) parent.insertBefore(scene, next);
    try { Object.defineProperty(el, '__ak25', { value: true, enumerable: false }); } catch (_e) { el.__ak25 = true; }
    return scene;
  }

  global.AK25D = global.AK25D || { apply: applyEl };
})(typeof window !== "undefined" ? window : this);
