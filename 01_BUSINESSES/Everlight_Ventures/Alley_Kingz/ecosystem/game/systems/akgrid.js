/* game/systems/akgrid.js -- AK_GRID: THE ONE GRID <-> WORLD MAPPING.
 * AK-GRID 2026-07-19
 *
 * WHY THIS FILE EXISTS
 * --------------------
 * Three layers currently place things in this game and NONE of them agree on what a cell is:
 *
 *   1. buildmode.js:103  var GRID = 64;  buildmode.js:467  snap(v) = round(v/64)*64
 *      -> player structures center on MULTIPLES OF 64 (lattice corners).
 *   2. basegrid.js:180   tileToWorld(type,tx,ty) = origin + (tx + w/2)*64
 *      -> anchor+footprint, so a 1x1 centers on lattice+32 and a 2x2 centers on lattice.
 *      basegrid.js:32-38 documents this parity split and works around it with snapsClean().
 *   3. index.html:706-737 ZONES[].buildings via B(id,label,col,x,y,w,h,...)
 *      -> hand-authored centers. MEASURED: of the 18 hub buildings, ZERO sit on the 64
 *      lattice (560/64 = 8.75, 850/64 = 13.28, 1140/64 = 17.81, 430, 1270, 520, 1180...).
 *      The 3D district (world3d.js:521 buildBuildings) reads those same free-placed numbers.
 *
 * So the 2D builder, the base editor and the 3D district are three lattices pretending to be
 * one. That is the exact desync class this module exists to kill: ONE conversion, ONE record
 * shape, and every consumer reads through it.
 *
 * THE LATTICE (and why the origin is constrained)
 * -----------------------------------------------
 * CELL = 64, because buildmode's GRID is 64 and buildmode already owns live player data in
 * p.builds[]. Changing 64 would relocate every structure a player has ever placed, so 64 is
 * not a preference, it is a fixed point.
 *
 * ORIGIN MUST BE CONGRUENT TO 0 MOD 64. That is the whole compatibility contract. As long as
 * origin % 64 === 0, this module's cell boundaries land exactly on buildmode's snap() lattice,
 * so a structure written by snap() and a structure written by anchorToWorld() share one grid.
 * basegrid.fitToWorld already respects this (it rounds the origin to the tile), and
 * assertAligned() below refuses any config that would break it -- a silent half-cell drift is
 * the bug that takes a week to find.
 *
 * TWO CONVERSIONS, NOT ONE (they are different questions)
 * ------------------------------------------------------
 *   gridToWorld(gx,gy)              -> the CENTER of cell (gx,gy). 1x1 question.
 *   worldToGrid(x,y)                -> which cell CONTAINS this point. floor, not round.
 *   anchorToWorld(gx,gy,gw,gh)      -> the CENTER of a gw x gh footprint anchored at (gx,gy).
 *   worldToAnchor(x,y,gw,gh)        -> which anchor puts a gw x gh footprint's center here.
 *
 * gridToWorld/worldToGrid are EXACT INVERSES over the integers (the +0.5 lands mid-cell, so
 * floor returns the same integer). anchorToWorld/worldToAnchor are exact inverses too, and
 * anchorToWorld(gx,gy,1,1) is IDENTICAL to gridToWorld(gx,gy) -- selfTest() proves both.
 * worldToAnchor is deliberately TOLERANT (it rounds): a free-placed hub building or a legacy
 * pre-grid structure still resolves to a deterministic cell instead of throwing.
 *
 * ONE RECORD SHAPE
 * ----------------
 *   { id, type, gx, gy, gw, gh, rot, level, district }
 * Pure data. JSON-safe. No three.js, no DOM, no canvas, no Image. The 2D builder, the 3D
 * district and the save file all read THIS. Anything a producer needs that is not one of
 * those nine fields rides in `meta`, so fromBuild -> toBuild is byte-lossless.
 *
 * NO NEW SAVE SYSTEM
 * ------------------
 * Persistence is p.builds[] through AK_ECON.mutateProfile -- the same array buildmode.js:614
 * writes and basegrid.js:354 edits. This module adds ONE optional field to an entry (`gid`,
 * a stable id) and only ever on an explicit ensureIds() call, because p.builds identity is
 * otherwise an ARRAY INDEX and splice() invalidates indices the moment anything is demolished.
 * Reading this module writes nothing.
 *
 * FOOTPRINTS ARE NOT DUPLICATED
 * -----------------------------
 * basegrid.js:125 already owns a 24-entry FOOTPRINTS table. A second copy is a drift bomb, so
 * at runtime footprint() DELEGATES to AK_BASEGRID.FOOTPRINTS when that module is present and
 * only falls back to the mirror below when it is not (headless, or a page that omits it).
 * akgrid.test.js asserts the mirror is key-for-key identical to basegrid's table, so drift
 * becomes a failing test instead of a misplaced building.
 */
(function (global) {
  'use strict';

  var VER = 'akgrid-1.0.0';

  /* ====================================================================== *
   * (0) CONFIG -- the lattice
   * ====================================================================== */
  var CELL = 64;                 // == buildmode.js:103 GRID. Not a preference; live data depends on it.

  var CFG = {
    cell: CELL,
    cols: 40,
    rows: 40,
    originX: 0,
    originY: 0,
    district: 'HOME_TURF',
    econ: null                   // injected AK_ECON (tests); null -> global.AK_ECON
  };

  function econ() { return CFG.econ || global.AK_ECON || null; }
  function loadP() {
    var e = econ();
    try { return (e && e.loadProfile) ? e.loadProfile() : null; } catch (_) { return null; }
  }
  function prof(p) { return p || loadP(); }
  function districtOf(d) { return d || CFG.district; }

  function config() {
    return {
      cell: CFG.cell, cols: CFG.cols, rows: CFG.rows,
      originX: CFG.originX, originY: CFG.originY, district: CFG.district
    };
  }

  // The compatibility invariant, stated as code. origin off-lattice => buildmode's snap()
  // and our anchorToWorld() disagree by a fraction of a cell forever.
  function assertAligned(ox, oy, cell) {
    return (ox % cell === 0) && (oy % cell === 0);
  }

  function configure(o) {
    if (o) {
      var ox = (o.originX != null && isFinite(o.originX)) ? +o.originX : CFG.originX;
      var oy = (o.originY != null && isFinite(o.originY)) ? +o.originY : CFG.originY;
      var cl = (o.cell > 0) ? (o.cell | 0) : CFG.cell;
      // Refuse silently-wrong geometry. Snapping is the safe repair: it keeps the lattice
      // coincident with buildmode instead of letting a caller introduce a half-cell offset.
      if (!assertAligned(ox, oy, cl)) {
        ox = Math.round(ox / cl) * cl;
        oy = Math.round(oy / cl) * cl;
      }
      CFG.cell = cl;
      CFG.originX = ox;
      CFG.originY = oy;
      if (o.cols > 0) CFG.cols = o.cols | 0;
      if (o.rows > 0) CFG.rows = o.rows | 0;
      if (o.district) CFG.district = o.district;
      if (o.econ) CFG.econ = o.econ;
    }
    return config();
  }

  // Fit a board inside a district (WORLD_W x WORLD_H). Deliberately BYTE-IDENTICAL to
  // basegrid.js:97 fitToWorld so the two modules land on the same origin from the same
  // inputs. MEASURED on the live 1700x1300 district with margin 40: cols=25 rows=19 ->
  // square 19x19, origin (256, 64). Both of those are 0 mod 64, so the lattice holds.
  function fitToDistrict(W, H, opts) {
    var margin = (opts && opts.margin != null) ? +opts.margin : 40;
    var t = CFG.cell;
    var cols = Math.max(1, Math.floor((W - margin * 2) / t));
    var rows = Math.max(1, Math.floor((H - margin * 2) / t));
    if (!opts || opts.square !== false) { var n = Math.min(cols, rows); cols = n; rows = n; }
    if (opts && opts.maxCols > 0) cols = Math.min(cols, opts.maxCols | 0);
    if (opts && opts.maxRows > 0) rows = Math.min(rows, opts.maxRows | 0);
    var ox = Math.round((W - cols * t) / 2 / t) * t;
    var oy = Math.round((H - rows * t) / 2 / t) * t;
    return configure({ cols: cols, rows: rows, originX: ox, originY: oy });
  }

  /* ====================================================================== *
   * (1) FOOTPRINTS -- delegated, mirrored only for headless
   * ====================================================================== *
   * MIRROR of basegrid.js:125 FOOTPRINTS. Kept ONLY so this module is usable with no
   * basegrid on the page. akgrid.test.js diffs the two tables key-for-key; if someone adds
   * a type to one and not the other the test fails loudly instead of a building landing
   * one cell off in the 3D district and nowhere near it in the 2D builder.
   */
  var MIRROR = {
    WALL:      { w: 1, h: 1, cat: 'wall',    gap: 0 },
    STONE:     { w: 1, h: 1, cat: 'wall',    gap: 0 },
    METAL:     { w: 1, h: 1, cat: 'wall',    gap: 0 },
    BARRICADE: { w: 1, h: 1, cat: 'wall',    gap: 0 },
    PATH:      { w: 1, h: 1, cat: 'deco',    gap: 0, walkable: true },
    PLANTER:   { w: 1, h: 1, cat: 'deco',    gap: 0 },
    GARDEN:    { w: 1, h: 1, cat: 'garden',  gap: 0 },

    TRAP_SPIKE:  { w: 1, h: 1, cat: 'trap',    gap: 0, hidden: true },
    TRAP_BOMB:   { w: 1, h: 1, cat: 'trap',    gap: 0, hidden: true },
    TRAP_SNARE:  { w: 2, h: 2, cat: 'trap',    gap: 0, hidden: true },
    DECO_SIGN:   { w: 1, h: 1, cat: 'deco',    gap: 0 },
    DECO_BRAZIER:{ w: 1, h: 1, cat: 'deco',    gap: 0 },

    HUT:         { w: 2, h: 2, cat: 'hut',     gap: 0 },
    BUILDER_HUT: { w: 2, h: 2, cat: 'hut',     gap: 0 },
    KENNEL:      { w: 2, h: 2, cat: 'hut',     gap: 0 },
    GATE:        { w: 2, h: 1, cat: 'wall',    gap: 0, touch: ['wall'] },

    STORAGE_GOLD: { w: 3, h: 3, cat: 'storage', gap: 0 },
    STORAGE_MATS: { w: 3, h: 3, cat: 'storage', gap: 0 },
    TOWER:        { w: 3, h: 3, cat: 'defense', gap: 0 },
    CANNON:       { w: 3, h: 3, cat: 'defense', gap: 0 },
    MORTAR:       { w: 3, h: 3, cat: 'defense', gap: 1 },

    TOWNHALL:  { w: 4, h: 4, cat: 'core', gap: 1 },
    BARRACKS:  { w: 4, h: 4, cat: 'army', gap: 0 },
    ARENA:     { w: 4, h: 4, cat: 'army', gap: 0 }
  };
  var FALLBACK = { w: 1, h: 1, cat: 'deco', gap: 0 };

  // Live delegation. AK_BASEGRID present -> its table IS the table (one object in memory).
  function table() {
    var bg = CFG.basegrid || global.AK_BASEGRID;
    return (bg && bg.FOOTPRINTS) ? bg.FOOTPRINTS : MIRROR;
  }
  function spec(type) {
    var t = table();
    return (type && t[type]) || (type && MIRROR[type]) || FALLBACK;
  }
  function known(type) { return !!(type && (table()[type] || MIRROR[type])); }
  function catOf(type) { return spec(type).cat; }

  // AK-ROTATE parity, identical rule to buildmode.js:472 rotSwap and basegrid.js:167.
  // rot is 0..3; odd rotations swap the long axis. Read falsy-safe as (rec.rot||0).
  function rotSwap(rot) { return ((rot | 0) & 1) === 1; }
  function dims(gw, gh, rot) {
    gw = Math.max(1, gw | 0); gh = Math.max(1, gh | 0);
    return rotSwap(rot) ? { gw: gh, gh: gw } : { gw: gw, gh: gh };
  }
  function footprint(type, rot) {
    var s = spec(type);
    return dims(s.w, s.h, rot);
  }
  // Even footprints center on the 64 lattice, so buildmode's snap() is a no-op on them and
  // buildmode.place() is a legal writer. Odd footprints center on lattice+32; those MUST be
  // written through put()/basegrid.fromInventory, never through place(), or snap() shifts
  // them half a cell. Same predicate as basegrid.js:172 snapsClean.
  function snapsClean(type, rot) {
    var f = footprint(type, rot);
    return (f.gw % 2 === 0) && (f.gh % 2 === 0);
  }

  /* ====================================================================== *
   * (2) THE CONVERSIONS
   * ====================================================================== */

  // Cell CENTER. The 1x1 question.
  function gridToWorld(gx, gy) {
    return {
      x: CFG.originX + ((gx | 0) + 0.5) * CFG.cell,
      y: CFG.originY + ((gy | 0) + 0.5) * CFG.cell
    };
  }
  // Which cell CONTAINS this point. floor, NOT round -- rounding would make the inverse
  // fail at cell boundaries and hand a pointer-pick the neighbouring cell half the time.
  function worldToGrid(x, y) {
    return {
      gx: Math.floor((x - CFG.originX) / CFG.cell),
      gy: Math.floor((y - CFG.originY) / CFG.cell)
    };
  }
  // Top-left corner of a cell, in world units.
  function cellCorner(gx, gy) {
    return { x: CFG.originX + (gx | 0) * CFG.cell, y: CFG.originY + (gy | 0) * CFG.cell };
  }

  // Footprint CENTER for an anchor. Same formula as basegrid.js:181 tileToWorld.
  function anchorToWorld(gx, gy, gw, gh) {
    gw = Math.max(1, gw | 0); gh = Math.max(1, gh | 0);
    return {
      x: CFG.originX + ((gx | 0) + gw / 2) * CFG.cell,
      y: CFG.originY + ((gy | 0) + gh / 2) * CFG.cell
    };
  }
  // Tolerant inverse. Same formula as basegrid.js:189 worldToTile. Rounds ANY world center
  // to the nearest legal anchor, so a free-placed hub building (index.html ZONES) and a
  // legacy pre-grid structure both resolve deterministically instead of throwing.
  function worldToAnchor(x, y, gw, gh) {
    gw = Math.max(1, gw | 0); gh = Math.max(1, gh | 0);
    return {
      gx: Math.round((x - CFG.originX) / CFG.cell - gw / 2),
      gy: Math.round((y - CFG.originY) / CFG.cell - gh / 2)
    };
  }
  // Is this world center ALREADY on a legal anchor for that footprint? Distinguishes a
  // clean round-trip from a quantisation. Callers that must not move a building silently
  // (the 3D district) check this before trusting worldToAnchor.
  function isAligned(x, y, gw, gh, eps) {
    eps = (eps == null) ? 1e-6 : eps;
    var a = worldToAnchor(x, y, gw, gh), w = anchorToWorld(a.gx, a.gy, gw, gh);
    return Math.abs(w.x - x) <= eps && Math.abs(w.y - y) <= eps;
  }

  /* ---- cell keys. IDENTICAL to basegrid.js:203 so occupancy maps interop verbatim ---- */
  function key(gx, gy) { return (gy | 0) * 100000 + (gx | 0); }
  function unkey(k) { var gy = Math.floor(k / 100000); return { gx: k - gy * 100000, gy: gy }; }

  /* ====================================================================== *
   * (3) FOOTPRINT GEOMETRY
   * ====================================================================== */

  // World AABB of a record. x/y = top-left corner, cx/cy = center. Renderers want pixels.
  function bounds(rec) {
    if (!rec) return null;
    var d = dims(rec.gw, rec.gh, 0);           // gw/gh on a record are ALREADY rotated
    var c = cellCorner(rec.gx, rec.gy);
    var w = d.gw * CFG.cell, h = d.gh * CFG.cell;
    return {
      x: c.x, y: c.y, w: w, h: h,
      x0: c.x, y0: c.y, x1: c.x + w, y1: c.y + h,
      cx: c.x + w / 2, cy: c.y + h / 2
    };
  }
  function center(rec) { return rec ? anchorToWorld(rec.gx, rec.gy, rec.gw, rec.gh) : null; }

  // Every cell a record occupies, as keys.
  function cellsOf(rec) {
    var out = [];
    if (!rec) return out;
    var gw = Math.max(1, rec.gw | 0), gh = Math.max(1, rec.gh | 0), i, j;
    for (j = 0; j < gh; j++) for (i = 0; i < gw; i++) out.push(key((rec.gx | 0) + i, (rec.gy | 0) + j));
    return out;
  }
  // Same, as {gx,gy} pairs, for callers that want coordinates not keys.
  function cellPairs(rec) {
    var out = [], ks = cellsOf(rec), i;
    for (i = 0; i < ks.length; i++) out.push(unkey(ks[i]));
    return out;
  }
  function inBounds(rec) {
    if (!rec) return false;
    var gw = Math.max(1, rec.gw | 0), gh = Math.max(1, rec.gh | 0);
    return (rec.gx | 0) >= 0 && (rec.gy | 0) >= 0 &&
           (rec.gx | 0) + gw <= CFG.cols && (rec.gy | 0) + gh <= CFG.rows;
  }
  // Integer AABB overlap on the cell lattice. Half-open ranges, so two records that merely
  // share an edge do NOT overlap -- walls must be allowed to sit flush.
  function overlaps(a, b) {
    if (!a || !b) return false;
    var aw = Math.max(1, a.gw | 0), ah = Math.max(1, a.gh | 0);
    var bw = Math.max(1, b.gw | 0), bh = Math.max(1, b.gh | 0);
    return (a.gx | 0) < (b.gx | 0) + bw && (b.gx | 0) < (a.gx | 0) + aw &&
           (a.gy | 0) < (b.gy | 0) + bh && (b.gy | 0) < (a.gy | 0) + ah;
  }
  function containsCell(rec, gx, gy) {
    if (!rec) return false;
    var gw = Math.max(1, rec.gw | 0), gh = Math.max(1, rec.gh | 0);
    return (gx | 0) >= (rec.gx | 0) && (gx | 0) < (rec.gx | 0) + gw &&
           (gy | 0) >= (rec.gy | 0) && (gy | 0) < (rec.gy | 0) + gh;
  }
  // Which record is under this world point? First hit wins, back to front is the caller's job.
  function pick(recs, x, y) {
    var g = worldToGrid(x, y), i;
    for (i = 0; i < (recs || []).length; i++) if (containsCell(recs[i], g.gx, g.gy)) return recs[i];
    return null;
  }

  /* ====================================================================== *
   * (4) THE RECORD -- pure data, the shared shape
   * ====================================================================== */
  var CANON = ['id', 'type', 'gx', 'gy', 'gw', 'gh', 'rot', 'level', 'district'];

  // Fields on a p.builds entry that this module maps onto canonical slots. Everything else
  // an entry carries (hp, maxHp, t, uc, crop, plantedAt, wx, em, and anything a future
  // system adds) rides in rec.meta untouched, which is what makes fromBuild -> toBuild
  // lossless instead of quietly dropping a builder job or a planted crop.
  var MAPPED = { type: 1, x: 1, y: 1, zone: 1, rot: 1, lvl: 1, gid: 1 };

  function makeRecord(o) {
    o = o || {};
    var rot = (o.rot | 0) & 3;
    var gw, gh;
    if (o.gw > 0 && o.gh > 0) {
      // Caller supplied explicit dims. Treat them as the ROTATED dims (what bounds() wants).
      gw = o.gw | 0; gh = o.gh | 0;
    } else {
      var f = footprint(o.type, rot);
      gw = f.gw; gh = f.gh;
    }
    return {
      id:       o.id != null ? String(o.id) : null,
      type:     o.type != null ? String(o.type) : null,
      gx:       o.gx | 0,
      gy:       o.gy | 0,
      gw:       Math.max(1, gw),
      gh:       Math.max(1, gh),
      rot:      rot,
      level:    Math.max(1, o.level | 0 || 1),
      district: o.district != null ? String(o.district) : districtOf(null),
      meta:     (o.meta && typeof o.meta === 'object') ? o.meta : {}
    };
  }

  function validate(rec) {
    var errs = [];
    if (!rec || typeof rec !== 'object') return { ok: false, errors: ['NOT_AN_OBJECT'] };
    if (!rec.type) errs.push('NO_TYPE');
    if (!rec.district) errs.push('NO_DISTRICT');
    if (!isFinite(rec.gx) || (rec.gx | 0) !== rec.gx) errs.push('GX_NOT_INT');
    if (!isFinite(rec.gy) || (rec.gy | 0) !== rec.gy) errs.push('GY_NOT_INT');
    if (!(rec.gw > 0) || (rec.gw | 0) !== rec.gw) errs.push('GW_BAD');
    if (!(rec.gh > 0) || (rec.gh | 0) !== rec.gh) errs.push('GH_BAD');
    if ((rec.rot | 0) !== rec.rot || rec.rot < 0 || rec.rot > 3) errs.push('ROT_RANGE');
    if (!(rec.level >= 1)) errs.push('LEVEL_BAD');
    if (!inBounds(rec)) errs.push('OUT_OF_BOUNDS');
    return { ok: errs.length === 0, errors: errs };
  }

  // JSON-safe by construction, but prove it rather than assert it: a record that survives a
  // JSON round-trip unchanged is a record a save file can hold.
  //
  // TWO CHECKS, NOT ONE -- they answer different questions and the first alone is not enough.
  // A live THREE.Mesh fails the JSON test on its own (methods get dropped, parent refs go
  // circular and throw), so for REAL engine objects the round-trip is sufficient. What it does
  // NOT catch is an engine-SHAPED plain object: {isMesh:true, geometry:{}, material:{}} is
  // perfectly JSON-safe and sails through. That is not a hypothetical -- it is what a caller
  // produces when it serialises a mesh "just to stash the ids", and it is worse than a live
  // handle because it persists. The record then round-trips clean for months, until someone
  // swaps the stub for the real object and the save silently starts dropping fields.
  // So: reject the SIGNATURE too. This module's header promises "no three.js, no DOM" -- this
  // is that promise expressed as code rather than as a comment.
  var ENGINE_KEYS = {
    isMesh: 1, isObject3D: 1, isBufferGeometry: 1, isMaterial: 1, isTexture: 1, isVector3: 1,
    geometry: 1, material: 1, renderer: 1, scene: 1,
    nodeType: 1, ownerDocument: 1, tagName: 1        // DOM handles
  };
  function hasEngineHandle(v, depth) {
    if (!v || typeof v !== 'object' || depth > 6) return false;
    if (typeof Node !== 'undefined' && v instanceof Node) return true;
    for (var k in v) {
      if (!Object.prototype.hasOwnProperty.call(v, k)) continue;
      if (ENGINE_KEYS[k]) return true;
      if (hasEngineHandle(v[k], depth + 1)) return true;
    }
    return false;
  }
  function isPure(rec) {
    try {
      if (JSON.stringify(JSON.parse(JSON.stringify(rec))) !== JSON.stringify(rec)) return false;
      return !hasEngineHandle(rec, 0);
    } catch (_) { return false; }
  }

  /* ====================================================================== *
   * (5) ADAPTER A -- p.builds[] (the 2D builder + raid collision)
   * ====================================================================== *
   * buildmode.js:614 entry shape:
   *   { type, x, y, hp, maxHp, zone, t, rot?, uc?{slot,t0,dur}, crop?, plantedAt?, wx?, em? }
   * x/y are the structure CENTER in world units.
   */

  // Deterministic fallback identity for an entry that has never been stamped. Position-derived
  // so a pure read is stable within a frame, but it CHANGES if the structure moves -- that is
  // why anything holding an id across a move must call ensureIds() first.
  function synthId(e) {
    return 'w:' + (e.zone || '') + ':' + (e.type || '') + ':' + Math.round(e.x || 0) + ':' + Math.round(e.y || 0);
  }

  function fromBuild(entry) {
    if (!entry) return null;
    var rot = (entry.rot | 0) & 3;
    var f = footprint(entry.type, rot);
    var a = worldToAnchor(entry.x, entry.y, f.gw, f.gh);
    var meta = {}, k;
    for (k in entry) if (Object.prototype.hasOwnProperty.call(entry, k) && !MAPPED[k]) meta[k] = entry[k];
    var rec = makeRecord({
      id: entry.gid || synthId(entry),
      type: entry.type,
      gx: a.gx, gy: a.gy, gw: f.gw, gh: f.gh,
      rot: rot,
      level: entry.lvl | 0 || 1,
      district: entry.zone,
      meta: meta
    });
    // Honest flag: a free-placed / legacy entry was QUANTISED to get here. Writing it back
    // will MOVE it. rec.meta._offLattice is how a caller notices before it happens.
    if (!isAligned(entry.x, entry.y, f.gw, f.gh)) {
      rec.meta._offLattice = { x: entry.x, y: entry.y };
    }
    return rec;
  }

  function toBuild(rec) {
    if (!rec) return null;
    var c = anchorToWorld(rec.gx, rec.gy, rec.gw, rec.gh);
    var e = {}, k;
    for (k in rec.meta) if (Object.prototype.hasOwnProperty.call(rec.meta, k) && k.charAt(0) !== '_') e[k] = rec.meta[k];
    e.type = rec.type;
    e.x = c.x;
    e.y = c.y;
    e.zone = rec.district;
    // Falsy-default discipline, copied from buildmode.js:615 -- rot/lvl/gid are written ONLY
    // when meaningful, so a zero-state profile stays byte-identical to what it was before
    // this module existed.
    if (rec.rot) e.rot = rec.rot;
    if (rec.level > 1) e.lvl = rec.level;
    if (rec.id && rec.id.charAt(0) !== 'w') e.gid = rec.id;
    return e;
  }

  // Every player structure in a district, as records.
  function list(district, p) {
    p = prof(p); district = districtOf(district);
    var builds = (p && p.builds) || [], out = [], i;
    for (i = 0; i < builds.length; i++) {
      var b = builds[i];
      if (!b || b.zone !== district) continue;
      var r = fromBuild(b);
      if (r) { r.meta._idx = i; out.push(r); }     // array index, valid for THIS read only
    }
    return out;
  }
  function get(id, district, p) {
    var recs = list(district, p), i;
    for (i = 0; i < recs.length; i++) if (recs[i].id === id) return recs[i];
    return null;
  }

  /* ---- WRITERS. All through AK_ECON.mutateProfile. No new save system, no localStorage ---- */

  // Stamp a stable `gid` on every entry in a district that lacks one, in ONE atomic pass.
  // Needed because p.builds identity is otherwise an ARRAY INDEX and buildmode.demolishAt /
  // basegrid.toInventory both splice(), which renumbers everything after the hole.
  function ensureIds(district, opts) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON', stamped: 0 };
    district = districtOf(district);
    var all = !!(opts && opts.allDistricts), stamped = 0;
    e.mutateProfile(function (p) {
      var builds = p.builds || [], i;
      if (!isFinite(p.akGridSeq)) p.akGridSeq = 0;
      for (i = 0; i < builds.length; i++) {
        var b = builds[i];
        if (!b || (!all && b.zone !== district)) continue;
        if (b.gid) continue;
        p.akGridSeq = (p.akGridSeq | 0) + 1;
        b.gid = 'g' + p.akGridSeq;
        stamped++;
      }
    });
    return { ok: true, stamped: stamped };
  }

  // Upsert. Matches on gid when the record carries a real one, otherwise on
  // type+district+cell, which is what a synth-id record can honestly be matched by.
  function put(rec) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    var v = validate(rec);
    if (!v.ok) return { ok: false, error: 'INVALID', errors: v.errors };
    var entry = toBuild(rec), mode = 'insert';
    e.mutateProfile(function (p) {
      if (!Array.isArray(p.builds)) p.builds = [];
      var at = -1, i;
      for (i = 0; i < p.builds.length; i++) {
        var b = p.builds[i]; if (!b) continue;
        if (entry.gid && b.gid === entry.gid) { at = i; break; }
        if (!entry.gid && b.zone === entry.zone && b.type === entry.type &&
            b.x === entry.x && b.y === entry.y) { at = i; break; }
      }
      if (at >= 0) {
        mode = 'update';
        // Preserve fields the record never modelled (a live builder job, a planted crop)
        // unless the record explicitly carried them through meta.
        var prev = p.builds[at], k;
        for (k in prev) if (Object.prototype.hasOwnProperty.call(prev, k) && !(k in entry)) entry[k] = prev[k];
        p.builds[at] = entry;
      } else {
        p.builds.push(entry);
      }
    });
    return { ok: true, mode: mode, id: rec.id, district: rec.district };
  }

  // Move / re-level / rotate an existing record without rebuilding it.
  function patch(id, fields, district) {
    var rec = get(id, district);
    if (!rec) return { ok: false, error: 'NO_RECORD' };
    var k;
    for (k in fields) if (Object.prototype.hasOwnProperty.call(fields, k)) {
      if (k === 'meta') continue;
      rec[k] = fields[k];
    }
    // rot changed and dims were not explicitly given -> re-derive the rotated footprint.
    if (fields && fields.rot != null && fields.gw == null) {
      var f = footprint(rec.type, rec.rot);
      rec.gw = f.gw; rec.gh = f.gh;
    }
    return put(rec);
  }

  function remove(id, district) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    district = districtOf(district);
    var removed = 0;
    e.mutateProfile(function (p) {
      var builds = p.builds || [], i;
      for (i = builds.length - 1; i >= 0; i--) {
        var b = builds[i];
        if (!b || b.zone !== district) continue;
        if ((b.gid && b.gid === id) || (!b.gid && synthId(b) === id)) { builds.splice(i, 1); removed++; }
      }
    });
    return removed ? { ok: true, removed: removed } : { ok: false, error: 'NO_RECORD' };
  }

  /* ====================================================================== *
   * (6) ADAPTER B -- ZONES[].buildings (the 3D district + the hub facades)
   * ====================================================================== *
   * index.html:705  B(id,label,col,x,y,w,h,url,act) -- x/y are the CENTER, w/h a PIXEL
   * footprint (measured range: w 160-210, h 96-124). world3d.js:521 buildBuildings reads
   * the same records to raise the 3D boxes.
   *
   * MEASURED, and this is the finding that matters: NONE of the 18 hub buildings sit on the
   * 64 lattice. So a hub building is a FREE-PLACED record. This adapter therefore reports
   * both truths -- the exact authored world box (meta.px) and the quantised grid cells --
   * and flags meta._offLattice. A consumer that wants pixel-exact placement (the 3D
   * district today) reads meta.px; a consumer that wants cells (occupancy, pathing, a
   * builder that must not overlap the Town Hall) reads gx/gy/gw/gh and accepts the quantise.
   * Nothing is silently moved.
   */
  function fromZoneBuilding(b, districtId, levels) {
    if (!b) return null;
    var pw = +b.w || 160, ph = +b.h || 96;
    // Cell count from the authored pixel footprint. ceil, not round: a building must never
    // claim FEWER cells than it visually covers or the builder will let a wall clip it.
    var gw = Math.max(1, Math.ceil(pw / CFG.cell));
    var gh = Math.max(1, Math.ceil(ph / CFG.cell));
    var a = worldToAnchor(b.x, b.y, gw, gh);
    var lvl = (levels && levels[b.id]) | 0 || 1;
    var rec = makeRecord({
      id: b.id, type: b.id,
      gx: a.gx, gy: a.gy, gw: gw, gh: gh,
      rot: 0, level: lvl,
      district: districtId,
      meta: {
        hub: true,
        px: { x: b.x, y: b.y, w: pw, h: ph },     // authored truth, never quantised
        label: b.label, col: b.col, url: b.url, act: b.act
      }
    });
    if (!isAligned(b.x, b.y, gw, gh)) rec.meta._offLattice = { x: b.x, y: b.y };
    return rec;
  }
  // Back to the B() shape, so a tool that edits hub layout on the grid can emit source.
  function toZoneBuilding(rec) {
    if (!rec) return null;
    var m = rec.meta || {};
    var c = m.px ? { x: m.px.x, y: m.px.y } : anchorToWorld(rec.gx, rec.gy, rec.gw, rec.gh);
    return {
      id: rec.type, label: m.label || rec.type, col: m.col || '#e8c55a',
      x: c.x, y: c.y,
      w: (m.px && m.px.w) || rec.gw * CFG.cell,
      h: (m.px && m.px.h) || rec.gh * CFG.cell,
      url: m.url || '', act: m.act || ''
    };
  }
  // A whole zone as records. `zone` is a ZONES[] entry; `levels` is index.html:608 LV.
  function fromZone(zone, levels) {
    var out = [], i;
    if (!zone || !zone.buildings) return out;
    for (i = 0; i < zone.buildings.length; i++) {
      var r = fromZoneBuilding(zone.buildings[i], zone.id, levels);
      if (r) out.push(r);
    }
    return out;
  }

  // THE unified read: fixed hub buildings AND player structures, one district, one shape,
  // one lattice. This is the call that makes the 2D builder and the 3D district agree.
  function snapshot(ctx, district, p) {
    district = districtOf(district || (ctx && ctx.zoneId));
    var out = [], zone = null, lv = null;
    try {
      if (ctx && ctx.ZONES) zone = ctx.ZONES[district];
      if (ctx && ctx.buildingLevels) lv = ctx.buildingLevels;
    } catch (_) {}
    if (zone) out = out.concat(fromZone(zone, lv));
    return out.concat(list(district, p));
  }

  /* ====================================================================== *
   * (7) RECONCILE -- keep basegrid on the same lattice
   * ====================================================================== *
   * Two modules holding two origins IS the desync this file exists to prevent. On init we
   * adopt basegrid's config if it has already fitted itself (it runs fitToWorld in its own
   * init hook), otherwise we push ours into it. Either way both end up on one origin, and
   * the return value says which way it went so a caller can log it.
   */
  function reconcile(bg) {
    bg = bg || CFG.basegrid || global.AK_BASEGRID;
    if (!bg || !bg.config) return { ok: false, error: 'NO_BASEGRID', direction: 'none' };
    var c = bg.config();
    if (c.tile !== CFG.cell) {
      return { ok: false, error: 'CELL_MISMATCH', ours: CFG.cell, theirs: c.tile, direction: 'none' };
    }
    if (c.originX !== CFG.originX || c.originY !== CFG.originY ||
        c.cols !== CFG.cols || c.rows !== CFG.rows) {
      // basegrid fitted first (its init hook runs fitToWorld); adopt it rather than fight it.
      configure({ originX: c.originX, originY: c.originY, cols: c.cols, rows: c.rows });
      return { ok: true, direction: 'adopted', config: config() };
    }
    return { ok: true, direction: 'already-agreed', config: config() };
  }

  /* ====================================================================== *
   * (8) SELF TEST -- `node systems/akgrid.js`
   * ====================================================================== *
   * Same convention as world3d.js:290 selfTest(). Pure math only, no deps, so it runs
   * anywhere including a browser console.
   */
  function selfTest(opts) {
    var fails = [], checks = 0;
    function ok(cond, label) { checks++; if (!cond) fails.push(label); }

    var saved = config();

    // -- (a) EXACT INVERSE over a few hundred cells, at TWO different origins ------------
    var origins = [{ x: 0, y: 0 }, { x: 256, y: 64 }, { x: -128, y: 640 }];
    for (var o = 0; o < origins.length; o++) {
      configure({ originX: origins[o].x, originY: origins[o].y, cols: 4096, rows: 4096 });
      var bad = 0, n = 0;
      for (var gy = -12; gy <= 12; gy++) {
        for (var gx = -12; gx <= 12; gx++) {
          n++;
          var w = gridToWorld(gx, gy);
          var b = worldToGrid(w.x, w.y);
          if (b.gx !== gx || b.gy !== gy) bad++;
        }
      }
      ok(n === 625, 'roundtrip/count@' + o + ' expected 625 got ' + n);
      ok(bad === 0, 'roundtrip/exact@origin(' + origins[o].x + ',' + origins[o].y + ') ' + bad + ' mismatches');
    }

    // -- (b) worldToGrid maps EVERY point inside a cell to that cell (not just the center)
    configure({ originX: 0, originY: 0, cols: 4096, rows: 4096 });
    var interiorBad = 0;
    for (var cy = 0; cy < 8; cy++) for (var cx = 0; cx < 8; cx++) {
      var corner = cellCorner(cx, cy);
      var probes = [
        [corner.x + 0.01, corner.y + 0.01],
        [corner.x + CFG.cell / 2, corner.y + CFG.cell / 2],
        [corner.x + CFG.cell - 0.01, corner.y + CFG.cell - 0.01]
      ];
      for (var pi = 0; pi < probes.length; pi++) {
        var g = worldToGrid(probes[pi][0], probes[pi][1]);
        if (g.gx !== cx || g.gy !== cy) interiorBad++;
      }
    }
    ok(interiorBad === 0, 'containment: ' + interiorBad + ' probes landed in the wrong cell');

    // -- (c) 1x1 anchor conversion IS the cell conversion --------------------------------
    var same = 0, diff = 0;
    for (var k = -20; k <= 20; k++) {
      var a1 = anchorToWorld(k, k, 1, 1), g1 = gridToWorld(k, k);
      if (a1.x === g1.x && a1.y === g1.y) same++; else diff++;
    }
    ok(diff === 0, 'anchor(1x1) !== gridToWorld in ' + diff + ' cases');
    ok(same === 41, 'anchor(1x1) sample count ' + same);

    // -- (d) FOOTPRINT round-trip for every size in the table, every rotation ------------
    var fpBad = [], t = table(), typ;
    for (typ in t) {
      if (!Object.prototype.hasOwnProperty.call(t, typ)) continue;
      for (var rot = 0; rot < 4; rot++) {
        var f = footprint(typ, rot);
        for (var ty = 0; ty < 6; ty++) for (var tx = 0; tx < 6; tx++) {
          var wc = anchorToWorld(tx, ty, f.gw, f.gh);
          var back = worldToAnchor(wc.x, wc.y, f.gw, f.gh);
          if (back.gx !== tx || back.gy !== ty) fpBad.push(typ + '/r' + rot + '@' + tx + ',' + ty);
          if (!isAligned(wc.x, wc.y, f.gw, f.gh)) fpBad.push(typ + '/r' + rot + ' !isAligned');
        }
      }
    }
    ok(fpBad.length === 0, 'footprint roundtrip failures: ' + fpBad.slice(0, 6).join(' '));

    // -- (e) rotation swaps the long axis and is an involution at 180 --------------------
    var d0 = dims(4, 2, 0), d1 = dims(4, 2, 1), d2 = dims(4, 2, 2), d3 = dims(4, 2, 3);
    ok(d0.gw === 4 && d0.gh === 2, 'rot0 dims');
    ok(d1.gw === 2 && d1.gh === 4, 'rot1 swaps');
    ok(d2.gw === 4 && d2.gh === 2, 'rot2 == rot0');
    ok(d3.gw === 2 && d3.gh === 4, 'rot3 == rot1');
    ok(snapsClean('HUT', 0) === true, 'HUT 2x2 snaps clean');
    ok(snapsClean('WALL', 0) === false, 'WALL 1x1 does NOT snap clean');
    ok(snapsClean('GATE', 0) === false, 'GATE 2x1 does NOT snap clean');
    ok(snapsClean('TOWNHALL', 1) === true, 'TOWNHALL 4x4 snaps clean rotated');

    // -- (f) bounds / cells / overlap ----------------------------------------------------
    configure({ originX: 0, originY: 0, cols: 40, rows: 40 });
    var rec = makeRecord({ id: 'r1', type: 'TOWNHALL', gx: 2, gy: 3, district: 'HOME_TURF' });
    ok(rec.gw === 4 && rec.gh === 4, 'TOWNHALL footprint from type');
    var bb = bounds(rec);
    ok(bb.x === 128 && bb.y === 192, 'bounds corner ' + bb.x + ',' + bb.y);
    ok(bb.w === 256 && bb.h === 256, 'bounds size ' + bb.w + 'x' + bb.h);
    ok(bb.cx === 256 && bb.cy === 320, 'bounds center ' + bb.cx + ',' + bb.cy);
    var ctr = center(rec);
    ok(ctr.x === bb.cx && ctr.y === bb.cy, 'center() agrees with bounds()');
    ok(cellsOf(rec).length === 16, 'TOWNHALL occupies 16 cells, got ' + cellsOf(rec).length);
    ok(containsCell(rec, 2, 3) && containsCell(rec, 5, 6), 'containsCell inclusive corners');
    ok(!containsCell(rec, 6, 6) && !containsCell(rec, 1, 3), 'containsCell excludes outside');

    var flushA = makeRecord({ type: 'WALL', gx: 0, gy: 0, district: 'D' });
    var flushB = makeRecord({ type: 'WALL', gx: 1, gy: 0, district: 'D' });
    ok(!overlaps(flushA, flushB), 'flush walls must NOT overlap');
    ok(overlaps(rec, makeRecord({ type: 'HUT', gx: 5, gy: 6, district: 'D' })), 'corner overlap detected');
    ok(!overlaps(rec, makeRecord({ type: 'HUT', gx: 6, gy: 7, district: 'D' })), 'adjacent hut clear');

    // -- (g) key parity with basegrid's key() --------------------------------------------
    ok(key(7, 3) === 300007, 'key(7,3) === 300007 got ' + key(7, 3));
    var uk = unkey(key(7, 3));
    ok(uk.gx === 7 && uk.gy === 3, 'unkey inverts key');

    // -- (h) record purity + validation ---------------------------------------------------
    ok(isPure(rec), 'record is JSON-pure');
    ok(validate(rec).ok, 'valid record validates');
    ok(!validate(makeRecord({ type: 'HUT', gx: -1, gy: 0, district: 'D' })).ok, 'negative gx rejected');
    ok(validate(makeRecord({ type: 'HUT', gx: 39, gy: 0, district: 'D' })).errors.indexOf('OUT_OF_BOUNDS') >= 0,
       'overhang past cols rejected');
    var noType = validate(makeRecord({ gx: 0, gy: 0, district: 'D' }));
    ok(noType.errors.indexOf('NO_TYPE') >= 0, 'missing type rejected');

    // -- (i) p.builds adapter is LOSSLESS on a lattice-legal entry -----------------------
    var entry = {
      type: 'HUT', x: anchorToWorld(4, 5, 2, 2).x, y: anchorToWorld(4, 5, 2, 2).y,
      hp: 200, maxHp: 200, zone: 'HOME_TURF', t: 1700000000000,
      uc: { slot: 1, t0: 1700000000000, dur: 60000 }, gid: 'g7'
    };
    var r2 = fromBuild(entry);
    ok(r2.id === 'g7', 'gid becomes id');
    ok(r2.gx === 4 && r2.gy === 5, 'entry anchor recovered ' + r2.gx + ',' + r2.gy);
    ok(r2.district === 'HOME_TURF', 'zone becomes district');
    ok(r2.meta.hp === 200 && r2.meta.uc && r2.meta.uc.slot === 1, 'unmapped fields ride in meta');
    ok(!r2.meta._offLattice, 'lattice-legal entry not flagged');
    var e2 = toBuild(r2);
    ok(JSON.stringify(e2) === JSON.stringify({
      hp: 200, maxHp: 200, t: 1700000000000, uc: { slot: 1, t0: 1700000000000, dur: 60000 },
      type: 'HUT', x: entry.x, y: entry.y, zone: 'HOME_TURF', gid: 'g7'
    }), 'toBuild(fromBuild(e)) lossless, got ' + JSON.stringify(e2));

    // -- (j) rot + lvl are falsy-default (zero-state byte-identical) ----------------------
    var plain = toBuild(makeRecord({ type: 'WALL', gx: 1, gy: 1, district: 'D' }));
    ok(!('rot' in plain) && !('lvl' in plain) && !('gid' in plain),
       'rot/lvl/gid omitted when default, got ' + JSON.stringify(plain));
    var fancy = toBuild(makeRecord({ id: 'g9', type: 'WALL', gx: 1, gy: 1, rot: 2, level: 5, district: 'D' }));
    ok(fancy.rot === 2 && fancy.lvl === 5 && fancy.gid === 'g9', 'rot/lvl/gid written when set');

    // -- (k) OFF-LATTICE detection on a real hub building --------------------------------
    // index.html:706 B('DROP',...,560,560,170,104,...) -- 560/64 = 8.75, so this is the
    // free-placed case the adapter must flag rather than silently move.
    var hub = fromZoneBuilding(
      { id: 'DROP', label: 'THE DROP', col: '#ff8fae', x: 560, y: 560, w: 170, h: 104, url: '', act: '' },
      'DOWNTOWN', { DROP: 5 });
    ok(hub.level === 5, 'hub level from LV table');
    ok(hub.gw === 3 && hub.gh === 2, 'DROP 170x104 -> 3x2 cells, got ' + hub.gw + 'x' + hub.gh);
    ok(!!hub.meta._offLattice, 'free-placed hub building IS flagged off-lattice');
    ok(hub.meta.px.x === 560 && hub.meta.px.y === 560, 'authored pixel center preserved');
    var backB = toZoneBuilding(hub);
    ok(backB.x === 560 && backB.y === 560 && backB.w === 170 && backB.h === 104,
       'toZoneBuilding restores authored geometry exactly');

    // -- (l) an ALIGNED hub building round-trips with no flag ----------------------------
    var aligned = fromZoneBuilding({ id: 'X', x: anchorToWorld(3, 3, 3, 2).x, y: anchorToWorld(3, 3, 3, 2).y, w: 170, h: 104 }, 'D', null);
    ok(!aligned.meta._offLattice, 'aligned hub building not flagged');
    ok(aligned.gx === 3 && aligned.gy === 3, 'aligned anchor recovered');

    // -- (m) fitToDistrict reproduces basegrid's numbers on the live world ---------------
    var fit = fitToDistrict(1700, 1300);
    ok(fit.cols === 19 && fit.rows === 19, 'fit 1700x1300 -> 19x19, got ' + fit.cols + 'x' + fit.rows);
    ok(fit.originX === 256 && fit.originY === 64, 'fit origin (256,64), got (' + fit.originX + ',' + fit.originY + ')');
    ok(assertAligned(fit.originX, fit.originY, fit.cell), 'fitted origin is 0 mod cell');

    // -- (n) configure REFUSES an off-lattice origin (snaps instead of drifting) ---------
    var drift = configure({ originX: 100, originY: 30 });
    ok(drift.originX % 64 === 0 && drift.originY % 64 === 0,
       'off-lattice origin snapped, got (' + drift.originX + ',' + drift.originY + ')');

    // -- (o) pick() resolves a world point to the record under it ------------------------
    configure({ originX: 0, originY: 0, cols: 40, rows: 40 });
    var recs = [makeRecord({ type: 'HUT', gx: 0, gy: 0, district: 'D' }),
                makeRecord({ type: 'TOWNHALL', gx: 4, gy: 4, district: 'D' })];
    ok(pick(recs, 40, 40) === recs[0], 'pick hits the hut');
    ok(pick(recs, 300, 300) === recs[1], 'pick hits the town hall');
    ok(pick(recs, 900, 900) === null, 'pick misses empty ground');

    configure(saved);

    var res = { ok: fails.length === 0, checks: checks, failures: fails, version: VER };
    if (!opts || opts.log !== false) {
      try {
        console.log('[AK_GRID selfTest] ' + (res.ok ? 'PASS' : 'FAIL') +
                    ' -- ' + checks + ' checks, ' + fails.length + ' failures');
        if (fails.length) fails.forEach(function (f) { console.log('   x ' + f); });
      } catch (_) {}
    }
    return res;
  }

  /* ====================================================================== *
   * EXPORTS
   * ====================================================================== */
  var API = {
    CELL: CELL,
    version: function () { return VER; },
    // config
    configure: configure, config: config, fitToDistrict: fitToDistrict,
    assertAligned: assertAligned, reconcile: reconcile,
    // footprints (delegated to AK_BASEGRID when present)
    FOOTPRINTS_MIRROR: MIRROR, spec: spec, known: known, catOf: catOf,
    footprint: footprint, dims: dims, snapsClean: snapsClean,
    // THE conversions
    gridToWorld: gridToWorld, worldToGrid: worldToGrid, cellCorner: cellCorner,
    anchorToWorld: anchorToWorld, worldToAnchor: worldToAnchor, isAligned: isAligned,
    key: key, unkey: unkey,
    // footprint geometry
    bounds: bounds, center: center, cellsOf: cellsOf, cellPairs: cellPairs,
    inBounds: inBounds, overlaps: overlaps, containsCell: containsCell, pick: pick,
    // the record
    CANON: CANON, makeRecord: makeRecord, validate: validate, isPure: isPure,
    // adapter A -- p.builds (2D builder / raid collision)
    fromBuild: fromBuild, toBuild: toBuild, list: list, get: get,
    ensureIds: ensureIds, put: put, patch: patch, remove: remove,
    // adapter B -- ZONES[].buildings (3D district / hub facades)
    fromZoneBuilding: fromZoneBuilding, toZoneBuilding: toZoneBuilding,
    fromZone: fromZone, snapshot: snapshot,
    // proof
    selfTest: selfTest
  };

  global.AK_GRID = API;

  // Register with the hub ONLY when the registry exists. This is a pure data layer, so it
  // stays fully usable (and node-requireable) on a page with no registry -- same stance as
  // basegrid.js:671. init() is the ONLY place we touch live config: adopt the district's
  // real size, then reconcile with basegrid so there is exactly one lattice in memory.
  if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) {
    global.AK_SYSTEMS.register({
      id: 'akgrid',
      init: function (ctx) {
        try {
          if (ctx && ctx.econ) CFG.econ = ctx.econ;
          if (ctx && ctx.zoneId) CFG.district = ctx.zoneId;
          if (ctx && ctx.world && ctx.world.WORLD_W) fitToDistrict(ctx.world.WORLD_W, ctx.world.WORLD_H);
          reconcile();
        } catch (_) {}
      },
      // Districts change by POLL, not by event (index.html:1354 enterZone notifies nobody).
      // Same idiom as world3d.js:900 -> setZone: compare, early-out, only work on change.
      onTick: function (dt, ctx) {
        if (!ctx || !ctx.zoneId || ctx.zoneId === CFG.district) return;
        CFG.district = ctx.zoneId;
        try {
          if (ctx.world && ctx.world.WORLD_W) fitToDistrict(ctx.world.WORLD_W, ctx.world.WORLD_H);
          reconcile();
        } catch (_) {}
      }
    });
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
    // `node systems/akgrid.js` runs the proof, same convention as world3d.js:290.
    if (require.main === module) {
      var r = selfTest();
      if (typeof process !== 'undefined' && process.exit) process.exit(r.ok ? 0 : 1);
    }
  }
})(typeof window !== 'undefined' ? window : globalThis);
