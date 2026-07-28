/*
 * spritesheet.js -- AK_SPRITES (PRE-RENDERED 3D UNIT ATLASES)
 * AK-SPRITE3D 2026-07-18
 *
 * The runtime half of the 3D-to-sprite pipeline. art/render_sprites.py bakes an
 * animated GLB into <angles> x <frames> cells of ONE png; this reads that atlas
 * and blits the right cell. Units read as 3D without a 3D engine, exactly how
 * Clash of Clans does it -- the phone never runs a real renderer for a hundred
 * units, and because the frames are baked, two clients replaying the same battle
 * draw byte-identical poses.
 *
 * THIS IS A TEXTURE SOURCE, NOT AN ARCHITECTURE. The battler keeps its existing
 * 2D canvas draw path, its transforms, its clip, its overlays. draw() is a
 * drop-in swap for one drawImage call and NOTHING else moves.
 *
 * Public API (window.AK_SPRITES):
 *   load(slug)                                   -> Promise<bool>, guarded, never throws.
 *                                                   Fetches manifest + image. A slug with
 *                                                   no atlas is marked DEAD and never re-probed.
 *   ready(slug, clip)                            -> bool, sync. Safe to call every frame.
 *   draw(g, slug, clip, angleRad, t, x, y, scale)-> bool. TRUE = the cell was blitted,
 *                                                   FALSE = no atlas, caller must fall
 *                                                   back to its existing card art.
 *   clips(slug)                                  -> array of loaded clip names
 *   markDead(slug)                               -> blacklist by hand
 *
 * The FALSE return is the whole safety story: a missing/rotten sheet degrades to
 * today's PNG render instead of blanking a unit. Never make draw() throw.
 *
 * Conventions, matched to the manifest emitted by render_sprites.py:
 *   cell a=0 is the model's apparent yaw 0 (facing the camera). manifest.frontOffsetDeg
 *   is added before cell selection, so a model authored facing the wrong way is
 *   corrected by editing ONE json number instead of re-rendering the sheet.
 *   angleRad follows the engine convention: 0 = +x (screen right), growing clockwise
 *   on canvas (y is down).
 *
 * No innerHTML. No direct save writes of any kind: this module owns ZERO player
 * state (atlases are build artifacts), so it never touches the profile engine.
 * Anything persistent in this repo goes through AK_ECON.mutateProfile, and this
 * file deliberately has nothing to persist. Headless-safe: node --check clean and
 * every entry point no-ops when there is no document.
 */
(function (global) {
  'use strict';

  var BASE = 'assets/sprites/units/';
  var HEADLESS = (typeof document === 'undefined' || typeof Image === 'undefined');

  var SHEETS = {};      // slug -> { clip -> {man, img, ok} }
  var DEAD = {};        // slug -> true, probed and absent, never re-probe
  var PENDING = {};     // slug -> Promise, so N units of one card share ONE fetch

  var TAU = Math.PI * 2;

  function deg(rad) { return rad * 180 / Math.PI; }

  function norm360(d) { d = d % 360; return d < 0 ? d + 360 : d; }

  // ---- manifest sanity. A truncated or hand-edited json must not crash a frame.
  function validMan(m) {
    return !!(m && m.cell > 0 && m.cols > 0 && m.rows > 0 &&
              m.angles > 0 && m.frames > 0 && m.image);
  }

  function loadImage(src) {
    return new Promise(function (res) {
      try {
        var im = new Image();
        im.onload = function () { res(im); };
        im.onerror = function () { res(null); };
        im.src = src;
      } catch (e) { res(null); }
    });
  }

  function loadClip(slug, clip) {
    var stem = BASE + slug + '_' + clip;
    // AK-SPRITE3D 2026-07-19: fetch is called inside a .map(), so a missing fetch
    // threw SYNCHRONOUSLY -- before any promise existed -- and the .catch() below
    // never ran. load() then threw instead of resolving, drawUnit threw with it,
    // and the exception surfaced inside the battler's draw loop, killing the very
    // frame this module promises it can never break. Old WebViews are exactly
    // where a missing fetch shows up, so probe it instead of assuming it.
    if (typeof fetch !== 'function') return Promise.resolve(null);
    try {
      return fetch(stem + '.json', { cache: 'force-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (man) {
        if (!validMan(man)) return null;
        // image name comes from the manifest so a renamed png stays resolvable
        return loadImage(BASE + (man.image || (slug + '_' + clip + '.png')))
          .then(function (img) {
            if (!img || !img.width) return null;
            return { man: man, img: img, ok: true };
          });
      })
      .catch(function () { return null; });
    } catch (e) { return Promise.resolve(null); }
  }

  /**
   * load(slug) -- probe every known clip name for this unit. Resolves true if at
   * least ONE sheet landed. Concurrent callers share the same in-flight promise.
   */
  function load(slug, clipNames) {
    if (HEADLESS || !slug) return Promise.resolve(false);
    if (DEAD[slug]) return Promise.resolve(false);
    if (SHEETS[slug]) return Promise.resolve(true);
    if (PENDING[slug]) return PENDING[slug];

    var names = clipNames && clipNames.length ? clipNames : ['idle', 'walk', 'run'];
    try {
    var p = Promise.all(names.map(function (c) {
      return loadClip(slug, c).then(function (s) { return { clip: c, sheet: s }; });
    })).then(function (rows) {
      var bag = {}, any = false;
      rows.forEach(function (r) { if (r.sheet) { bag[r.clip] = r.sheet; any = true; } });
      if (!any) { DEAD[slug] = true; delete PENDING[slug]; return false; }
      SHEETS[slug] = bag;
      delete PENDING[slug];
      return true;
    }).catch(function () {
      DEAD[slug] = true; delete PENDING[slug]; return false;
    });

    PENDING[slug] = p;
    return p;
    // belt AND braces: load() is called from inside a draw loop via drawUnit, so
    // it must resolve-or-return, never throw, no matter what the environment lacks.
    } catch (e) { DEAD[slug] = true; delete PENDING[slug]; return Promise.resolve(false); }
  }

  // ---- clip resolution: asked-for clip, else idle, else whatever loaded. A unit
  // with only an idle sheet still renders while walking instead of vanishing.
  function pickSheet(slug, clip) {
    var bag = SHEETS[slug];
    if (!bag) return null;
    if (clip && bag[clip]) return bag[clip];
    if (bag.idle) return bag.idle;
    for (var k in bag) { if (Object.prototype.hasOwnProperty.call(bag, k)) return bag[k]; }
    return null;
  }

  function ready(slug, clip) {
    return !!(!HEADLESS && slug && !DEAD[slug] && pickSheet(slug, clip));
  }

  function clips(slug) {
    var bag = SHEETS[slug];
    return bag ? Object.keys(bag) : [];
  }

  function markDead(slug) { if (slug) { DEAD[slug] = true; delete SHEETS[slug]; } }

  /**
   * draw(g, slug, clip, angleRad, t, x, y, scale)
   *   g        canvas 2d context, already transformed by the caller
   *   angleRad unit heading, engine convention (0 = +x)
   *   t        seconds; wrapped by the clip duration
   *   x,y      CENTER of the unit in the current frame
   *   scale    drawn size in px (the battler's d = r*2.4)
   * Returns true only when a cell was actually blitted.
   */
  function draw(g, slug, clip, angleRad, t, x, y, scale) {
    if (HEADLESS || !g || !slug || DEAD[slug]) return false;
    var s = pickSheet(slug, clip);
    if (!s || !s.ok) return false;
    var m = s.man;

    try {
      // ---- angle -> column. frontOffsetDeg lets a mis-authored model be fixed
      // in the manifest instead of a 20-minute re-render.
      var yaw = norm360(deg(angleRad || 0) + (m.frontOffsetDeg || 0));
      var step = m.angleStepDeg || (360 / m.angles);
      var ai = Math.round(yaw / step) % m.angles;      // NEAREST cell, not floor
      if (ai < 0) ai += m.angles;

      // ---- time -> row
      var fi = 0;
      if (m.frames > 1) {
        var dur = m.duration > 0 ? m.duration : (m.frames / (m.fps || 12));
        var u = ((t || 0) % dur) / dur;
        if (u < 0) u += 1;
        fi = Math.floor(u * m.frames) % m.frames;
      }

      var cell = m.cell;
      var sx = ai * cell, sy = fi * cell;
      // clamp: a manifest claiming more cells than the png holds would otherwise
      // blit garbage or throw mid-frame
      if (sx + cell > (m.atlasW || s.img.width) || sy + cell > (m.atlasH || s.img.height)) return false;

      var d = scale || cell;
      g.drawImage(s.img, sx, sy, cell, cell, x - d / 2, y - d / 2, d, d);
      return true;
    } catch (e) { return false; }
  }

  /* ------------------------------------------------------------------ *
   * AK-SPRITE3D 2026-07-19: card-name -> atlas-slug, and the one-call
   * wrapper the battler uses.
   *
   * slugFor MUST stay byte-identical to slugify() in art/render_sprites.py,
   * because that function decides the FILENAME on disk and this one decides
   * what we ask for. Python: re.sub(r'[^a-z0-9]+','_', s.lower()).strip('_').
   * Card names carry sigils ("$BCARDD"), so a naive toLowerCase() would ask
   * for "$bcardd" and miss a sheet that is sitting right there.
   * ------------------------------------------------------------------ */
  function slugFor(name) {
    if (!name) return '';
    return String(name).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  }

  /**
   * drawUnit(g, cardName, angleRad, t, x, y, scale) -- the battler's entry point.
   * Resolves the slug, kicks off a ONE-TIME lazy load the first time a card is
   * seen, and blits if a sheet is already resident.
   *
   * Returns FALSE on the first frames (fetch in flight) and forever for cards
   * with no atlas, which is exactly the contract the caller wants: false means
   * "draw the card photo you already draw". Nothing stalls waiting on a sheet,
   * so a cold cache costs a few frames of the old look, never a blank unit.
   */
  function drawUnit(g, cardName, angleRad, t, x, y, scale, clip) {
    if (HEADLESS || !cardName) return false;
    var slug = slugFor(cardName);
    if (!slug || DEAD[slug]) return false;
    if (!SHEETS[slug]) { load(slug); return false; }   // load() self-guards repeats
    // clip defaults to idle; an unknown clip still resolves through pickSheet's
    // idle fallback, so passing 'run' before a run sheet exists is safe.
    return draw(g, slug, clip || 'idle', angleRad, t, x, y, scale);
  }

  global.AK_SPRITES = {
    load: load,
    ready: ready,
    draw: draw,
    drawUnit: drawUnit,
    slugFor: slugFor,
    clips: clips,
    markDead: markDead,
    get base() { return BASE; },
    set base(v) { if (v) BASE = String(v); },
    _sheets: SHEETS,
    _dead: DEAD
  };
}(typeof window !== 'undefined' ? window : this));
