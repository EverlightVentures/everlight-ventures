/* game/systems/basegrid.js -- AK_SYSTEMS module: BASE TILE GRID + INVENTORY EDITING MODEL.
 * AK-BASEGRID 2026-07-18
 *
 * THE DATA + RULES LAYER under Clash-style base editing. NOT a renderer: no DOM, no
 * canvas, no markup injection, no localStorage. Pure math plus AK_ECON.mutateProfile writes,
 * so the exact same functions can run on a server tick later.
 *
 * ONE SHARED STATE (the law that makes nested worlds work)
 * -------------------------------------------------------
 * Walking the 3D district is the outer world; entering the BUILDER building drops you
 * into the base editor. An edit made inside the nested world MUST be standing there when
 * you walk out. That only holds if there is ONE state and MANY renderers. buildmode.js
 * already owns that state:
 *
 *     p.builds[] = [{ type, x, y, hp, maxHp, zone, t, rot?, uc?{slot,t0,dur},
 *                     crop?, plantedAt?, wx?, em? }]
 *     x / y are the structure CENTER in WORLD units, snapped to the 64 lattice.
 *
 * THIS MODULE DOES NOT INVENT A SECOND PLACEMENT SCHEMA. It reads and writes that exact
 * array through the same AK_ECON.mutateProfile path buildmode uses, so a hut moved here
 * is moved in the hub draw (onDrawWorld -> drawStruct) and in raid defense (buildRects ->
 * AK_COLLISION.obstaclesFor) with no sync step.
 *
 * TILE MODEL
 * ----------
 * TILE = 64 = buildmode's GRID, so the tile lattice IS the placement lattice. Tile (tx,ty)
 * spans world [ORIGIN.x + tx*TILE, ORIGIN.x + (tx+1)*TILE). The canonical anchor of a
 * placement is its TOP-LEFT TILE; the world center is DERIVED:
 *
 *     centerX = ORIGIN.x + (tx + w/2) * TILE
 *
 * PARITY NOTE (real, stated plainly): with one uniform tile grid, odd and even footprints
 * cannot both center on the same lattice. Even footprints (2x2 huts, 4x4 Town Hall) land
 * exactly on the 64 lattice, so buildmode's snap() is idempotent on them. Odd footprints
 * (1x1 traps/walls, 3x3 defenses) center on lattice+32, which buildmode's snap() would
 * shift by half a tile. That is why the writer path here is fromInventory/moveAll (direct
 * mutateProfile, no snap) and NOT buildmode.place(). snapsClean(type) tells a caller which
 * types are safe to route through place(). worldToTile() is tolerant either way: it rounds
 * any world center to the nearest legal anchor, so legacy entries placed by the old
 * in-world path still resolve to a tile deterministically.
 *
 * INVENTORY IS THE WHOLE POINT
 * ----------------------------
 * CoC editing feels good because you do not shuffle buildings one at a time. You REMOVE
 * them into a tray, clear the map, and rebuild from nothing without losing anything. So a
 * structure is EITHER in p.builds (placed) or in p.baseTray (removed), never both and
 * never duplicated. A tray item is the SAME entry object minus x/y/zone, so putting it
 * back is literally re-adding x/y/zone: hp, crop, plantedAt, rot all ride along.
 *
 * Falsy-default / zero-state byte-identical: p.baseTray, p.baseLayouts and p.baseTraySeq
 * are lazily created on first edit. Reading this module writes nothing.
 */
(function (global) {
  'use strict';

  /* ====================================================================== *
   * (0) CONFIG -- tile lattice + grid extent
   * ====================================================================== */
  var CFG = {
    tile: 64,            // MUST match buildmode GRID (64) or the two lattices drift
    cols: 40,            // CoC reference board
    rows: 40,
    originX: 0,          // world coords of tile (0,0)'s top-left corner
    originY: 0,
    zone: 'HOME_TURF',   // default zone these placements belong to
    econ: null           // injected AK_ECON (tests); null -> global.AK_ECON
  };

  function econ() {
    if (CFG.econ) return CFG.econ;
    return global.AK_ECON || null;
  }
  function loadP() {
    var e = econ();
    try { return (e && e.loadProfile) ? e.loadProfile() : null; } catch (_) { return null; }
  }
  function prof(p) { return p || loadP(); }
  function zoneOf(z) { return z || CFG.zone; }

  // configure({tile,cols,rows,originX,originY,zone,econ}). Returns the live config copy.
  function configure(o) {
    if (o) {
      if (o.tile    > 0) CFG.tile    = o.tile | 0;
      if (o.cols    > 0) CFG.cols    = o.cols | 0;
      if (o.rows    > 0) CFG.rows    = o.rows | 0;
      if (o.originX != null && isFinite(o.originX)) CFG.originX = +o.originX;
      if (o.originY != null && isFinite(o.originY)) CFG.originY = +o.originY;
      if (o.zone)  CFG.zone = o.zone;
      if (o.econ)  CFG.econ = o.econ;
    }
    return config();
  }
  function config() {
    return { tile: CFG.tile, cols: CFG.cols, rows: CFG.rows, originX: CFG.originX, originY: CFG.originY, zone: CFG.zone };
  }

  // Fit a board inside a hub zone (WORLD_W x WORLD_H). Shrinks cols/rows to what actually
  // fits, centers the board, and snaps the origin to the TILE lattice so tile boundaries
  // stay coincident with buildmode's snap() lattice. Square by default so rotateAll works.
  function fitToWorld(W, H, opts) {
    var margin = (opts && opts.margin != null) ? +opts.margin : 40;      // buildmode placeReason uses m=40
    var t = CFG.tile;
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
   * (1) FOOTPRINTS -- the per-type tile registry
   * ====================================================================== *
   * w/h are TILES at rot 0. cat drives grouping in the tray + the scout filter.
   * gap     = tiles of mandatory clearance around the piece (0 = may sit flush).
   * hidden  = invisible to an attacker until it fires (traps) -> scoutView drops it.
   * touch   = list of categories at least one of which must be orthogonally adjacent.
   *
   * The first block is the EXISTING buildmode STRUCT keys mapped to CoC-canonical tile
   * sizes. The second block is the CoC-shaped catalog the renderer lane can add STRUCT
   * entries for; footprints live here first so grid rules never wait on art.
   */
  var FOOTPRINTS = {
    /* --- existing buildmode STRUCT keys --- */
    WALL:      { w: 1, h: 1, cat: 'wall',    gap: 0 },
    STONE:     { w: 1, h: 1, cat: 'wall',    gap: 0 },
    METAL:     { w: 1, h: 1, cat: 'wall',    gap: 0 },
    BARRICADE: { w: 1, h: 1, cat: 'wall',    gap: 0 },
    PATH:      { w: 1, h: 1, cat: 'deco',    gap: 0, walkable: true },
    PLANTER:   { w: 1, h: 1, cat: 'deco',    gap: 0 },
    GARDEN:    { w: 1, h: 1, cat: 'garden',  gap: 0 },

    /* --- CoC-shaped catalog (grid rules ready ahead of art) --- */
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
    MORTAR:       { w: 3, h: 3, cat: 'defense', gap: 1 },   // needs breathing room, CoC splash piece

    TOWNHALL:  { w: 4, h: 4, cat: 'core', gap: 1 },
    BARRACKS:  { w: 4, h: 4, cat: 'army', gap: 0 },
    ARENA:     { w: 4, h: 4, cat: 'army', gap: 0 }
  };
  var FALLBACK = { w: 1, h: 1, cat: 'deco', gap: 0 };

  function spec(type) { return (type && FOOTPRINTS[type]) || FALLBACK; }
  function known(type) { return !!(type && FOOTPRINTS[type]); }
  function catOf(type) { return spec(type).cat; }
  function isHidden(type) { return !!spec(type).hidden; }

  // AK-ROTATE parity, identical rule to buildmode: odd rot swaps width <-> height.
  function rotSwap(rot) { return ((rot | 0) & 1) === 1; }
  function footprint(type, rot) {
    var s = spec(type);
    return rotSwap(rot) ? { w: s.h, h: s.w } : { w: s.w, h: s.h };
  }
  // Even footprints center on the 64 lattice -> buildmode.place()'s snap() is a no-op on
  // them. Odd footprints center on lattice+32 and MUST be written by this module instead.
  function snapsClean(type, rot) {
    var f = footprint(type, rot);
    return (f.w % 2 === 0) && (f.h % 2 === 0);
  }

  /* ====================================================================== *
   * (2) WORLD <-> TILE
   * ====================================================================== */
  function tileToWorld(type, tx, ty, rot) {
    var f = footprint(type, rot), t = CFG.tile;
    return { x: CFG.originX + ((tx | 0) + f.w / 2) * t, y: CFG.originY + ((ty | 0) + f.h / 2) * t };
  }
  // Tolerant inverse: rounds ANY world center to the nearest legal anchor for this
  // footprint. tileToWorld -> worldToTile round-trips exactly; worldToTile is also what
  // resolves legacy 64-lattice entries (placed by the old in-world path) onto the board.
  function worldToTile(type, wx, wy, rot) {
    var f = footprint(type, rot), t = CFG.tile;
    return {
      tx: Math.round((wx - CFG.originX) / t - f.w / 2),
      ty: Math.round((wy - CFG.originY) / t - f.h / 2)
    };
  }
  // Generous pointer snap: the finger names the CENTER, we return the anchor under it.
  function snapPointer(type, wx, wy, rot) { return worldToTile(type, wx, wy, rot); }

  function entryTile(entry) {
    if (!entry) return null;
    return worldToTile(entry.type, entry.x, entry.y, entry.rot || 0);
  }
  // world AABB of a footprint, for a renderer that wants pixels not tiles
  function tileRect(type, tx, ty, rot) {
    var f = footprint(type, rot), t = CFG.tile;
    return { x: CFG.originX + (tx | 0) * t, y: CFG.originY + (ty | 0) * t, w: f.w * t, h: f.h * t };
  }

  function key(tx, ty) { return (ty | 0) * 100000 + (tx | 0); }     // grid never exceeds 100k cols
  function unkey(k) { var ty = Math.floor(k / 100000); return { tx: k - ty * 100000, ty: ty }; }

  function tilesFor(type, tx, ty, rot) {
    var f = footprint(type, rot), out = [];
    for (var j = 0; j < f.h; j++) for (var i = 0; i < f.w; i++) out.push(key((tx | 0) + i, (ty | 0) + j));
    return out;
  }
  function inBounds(type, tx, ty, rot) {
    var f = footprint(type, rot);
    return (tx | 0) >= 0 && (ty | 0) >= 0 && (tx | 0) + f.w <= CFG.cols && (ty | 0) + f.h <= CFG.rows;
  }

  /* ====================================================================== *
   * (3) OCCUPANCY -- built from the REAL p.builds[]
   * ====================================================================== *
   * Returns { map, cells, cols, rows, count, offGrid }.
   *   map[key(tx,ty)] = { idx, type, tx, ty, uc }   idx is the p.builds index.
   *   offGrid = entries whose derived anchor falls outside the board (legacy placements
   *             from before the grid existed). Reported, never silently dropped.
   * opts.blocked = [{tx,ty,w,h}] extra blocked regions (the zone's fixed host buildings).
   * opts.exclude = index or array of indices to ignore (the piece being dragged).
   */
  function occupancy(p, zone, opts) {
    p = prof(p); zone = zoneOf(zone);
    var builds = (p && p.builds) || [], map = {}, cells = [], offGrid = [], count = 0;
    var ex = {}, i, j, k, t;
    if (opts && opts.exclude != null) {
      var xs = Array.isArray(opts.exclude) ? opts.exclude : [opts.exclude];
      for (i = 0; i < xs.length; i++) ex[xs[i] | 0] = true;
    }
    for (i = 0; i < builds.length; i++) {
      var b = builds[i];
      if (!b || b.zone !== zone) continue;
      if (ex[i]) continue;
      var a = entryTile(b);
      if (!inBounds(b.type, a.tx, a.ty, b.rot || 0)) { offGrid.push({ idx: i, type: b.type, tx: a.tx, ty: a.ty }); continue; }
      var ts = tilesFor(b.type, a.tx, a.ty, b.rot || 0);
      var cell = { idx: i, type: b.type, tx: a.tx, ty: a.ty, rot: b.rot || 0, uc: !!b.uc };
      cells.push(cell); count++;
      for (j = 0; j < ts.length; j++) map[ts[j]] = cell;
    }
    if (opts && opts.blocked) {
      for (i = 0; i < opts.blocked.length; i++) {
        var r = opts.blocked[i];
        for (j = 0; j < (r.h | 0 || 1); j++) for (k = 0; k < (r.w | 0 || 1); k++) {
          t = key((r.tx | 0) + k, (r.ty | 0) + j);
          if (!map[t]) map[t] = { idx: -1, type: r.type || 'BLOCKED', tx: (r.tx | 0) + k, ty: (r.ty | 0) + j, rot: 0, uc: false, fixed: true };
        }
      }
    }
    return { map: map, cells: cells, cols: CFG.cols, rows: CFG.rows, count: count, offGrid: offGrid, zone: zone };
  }

  /* ====================================================================== *
   * (4) canPlace -- bounds, overlap, clearance, adjacency
   * ====================================================================== */
  function canPlace(type, tx, ty, rot, opts) {
    opts = opts || {};
    if (!known(type)) return { ok: false, reason: 'BAD_TYPE', tiles: [] };
    rot = (rot | 0) & 3;
    tx = tx | 0; ty = ty | 0;
    if (!inBounds(type, tx, ty, rot)) return { ok: false, reason: 'OUT_OF_BOUNDS', tiles: [] };

    var occ = opts.occ || occupancy(opts.profile, opts.zone, { exclude: opts.exclude, blocked: opts.blocked });
    var ts = tilesFor(type, tx, ty, rot), i;
    for (i = 0; i < ts.length; i++) if (occ.map[ts[i]]) return { ok: false, reason: 'SPOT_TAKEN', tiles: ts, at: occ.map[ts[i]] };

    var s = spec(type), f = footprint(type, rot);

    // clearance ring: this piece's own gap, AND any neighbour that demands a gap of its own
    var gap = s.gap | 0, x, y, c;
    var ringGap = Math.max(gap, 1);          // scan 1 ring minimum so neighbour gaps are seen
    for (y = ty - ringGap; y < ty + f.h + ringGap; y++) {
      for (x = tx - ringGap; x < tx + f.w + ringGap; x++) {
        if (x >= tx && x < tx + f.w && y >= ty && y < ty + f.h) continue;   // own tiles
        c = occ.map[key(x, y)];
        if (!c) continue;
        var dist = ringDist(tx, ty, f.w, f.h, x, y);
        var need = Math.max(gap, spec(c.type).gap | 0);
        if (dist <= need) return { ok: false, reason: 'NEEDS_CLEARANCE', tiles: ts, at: c, gap: need };
      }
    }

    // adjacency requirement (GATE must touch a wall)
    if (s.touch && s.touch.length) {
      var touched = false;
      for (y = ty - 1; y < ty + f.h + 1 && !touched; y++) {
        for (x = tx - 1; x < tx + f.w + 1 && !touched; x++) {
          if (x >= tx && x < tx + f.w && y >= ty && y < ty + f.h) continue;
          if (ringDist(tx, ty, f.w, f.h, x, y) !== 1) continue;             // orthogonal ring only
          c = occ.map[key(x, y)];
          if (c && s.touch.indexOf(catOf(c.type)) >= 0) touched = true;
        }
      }
      if (!touched) return { ok: false, reason: 'NEEDS_ADJACENT', tiles: ts, need: s.touch.slice() };
    }
    return { ok: true, reason: null, tiles: ts };
  }
  // Chebyshev-style ring distance from a tile to the nearest edge of a w*h box.
  function ringDist(bx, by, bw, bh, x, y) {
    var dx = (x < bx) ? (bx - x) : (x >= bx + bw ? x - (bx + bw) + 1 : 0);
    var dy = (y < by) ? (by - y) : (y >= by + bh ? y - (by + bh) + 1 : 0);
    return Math.max(dx, dy);
  }
  // Renderer hook: valid/invalid highlight for the ghost under the finger.
  function highlight(type, tx, ty, rot, opts) {
    var r = canPlace(type, tx, ty, rot, opts);
    return { ok: r.ok, reason: r.reason, tiles: r.tiles.map(unkey), world: tileRect(type, tx, ty, rot) };
  }

  /* ====================================================================== *
   * (5) INVENTORY TRAY -- the remove/rebuild flow
   * ====================================================================== *
   * p.baseTray[] = [{ iid, type, hp, maxHp, rot?, lvl?, t, crop?, plantedAt?, wx?, em? }]
   * Same entry as p.builds MINUS x/y/zone. A structure is placed OR in the tray, never
   * both, so the shared-state law survives the round trip.
   */
  var TRAY_KEEP = ['type', 'hp', 'maxHp', 'rot', 'lvl', 't', 'crop', 'plantedAt', 'wx', 'em'];

  function toTrayItem(b, iid) {
    var it = { iid: iid };
    for (var i = 0; i < TRAY_KEEP.length; i++) { var k = TRAY_KEEP[i]; if (b[k] !== undefined) it[k] = b[k]; }
    return it;
  }
  function toBuildEntry(it, zone, x, y, rot) {
    var e = { type: it.type, x: x, y: y, hp: it.hp | 0, maxHp: it.maxHp | 0, zone: zone, t: it.t || Date.now() };
    if (rot) e.rot = rot;                                     // falsy-safe, exactly like buildmode
    if (it.lvl) e.lvl = it.lvl;
    if (it.crop !== undefined) { e.crop = it.crop; e.plantedAt = it.plantedAt; if (it.wx !== undefined) e.wx = it.wx; if (it.em !== undefined) e.em = it.em; }
    return e;
  }
  function nextIid(p) { p.baseTraySeq = (p.baseTraySeq | 0) + 1; return 'i' + p.baseTraySeq; }
  function ensureTray(p) { if (!Array.isArray(p.baseTray)) p.baseTray = []; return p.baseTray; }

  // Remove ONE placed structure into the tray. entryIdx is the p.builds index (the same
  // handle buildmode.demolishAt / moveBuild use). Refuses an in-progress build so a
  // builder slot is never stranded; opts.force cancels the job the way demolishAt does.
  function toInventory(entryIdx, opts) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    opts = opts || {};
    var idx = entryIdx | 0, p0 = loadP();
    var b = p0 && p0.builds && p0.builds[idx];
    if (!b) return { ok: false, error: 'NO_BUILD' };
    if (b.zone !== zoneOf(opts.zone)) return { ok: false, error: 'OTHER_ZONE' };
    if (b.uc && !opts.force) return { ok: false, error: 'UNDER_CONSTRUCTION' };
    var iid = null;
    e.mutateProfile(function (p) {
      var q = p.builds && p.builds[idx]; if (!q) return;
      var tray = ensureTray(p);
      iid = nextIid(p);
      if (q.uc && p.crew && p.crew[q.uc.slot]) { p.crew[q.uc.slot].started = 0; p.crew[q.uc.slot].dur = 0; }  // free the builder
      tray.push(toTrayItem(q, iid));
      p.builds.splice(idx, 1);
    });
    bump();
    return iid ? { ok: true, iid: iid, type: b.type } : { ok: false, error: 'WRITE_FAILED' };
  }

  // Clear the whole zone into the tray in ONE mutateProfile pass. This is the move that
  // makes CoC editing feel free: wipe the board, keep every building, rebuild from scratch.
  function clearAll(opts) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON', moved: 0 };
    opts = opts || {};
    var zone = zoneOf(opts.zone), moved = 0, skipped = 0, iids = [];
    e.mutateProfile(function (p) {
      var builds = p.builds || [], tray = ensureTray(p);
      for (var i = builds.length - 1; i >= 0; i--) {          // back to front: indices stay valid
        var b = builds[i];
        if (!b || b.zone !== zone) continue;
        if (b.uc && !opts.force) { skipped++; continue; }
        if (b.uc && p.crew && p.crew[b.uc.slot]) { p.crew[b.uc.slot].started = 0; p.crew[b.uc.slot].dur = 0; }
        var iid = nextIid(p);
        tray.push(toTrayItem(b, iid));
        iids.push(iid);
        builds.splice(i, 1);
        moved++;
      }
    });
    bump();
    return { ok: true, moved: moved, skipped: skipped, iids: iids };
  }

  // Drag a tray item back onto the board. FREE: rearranging is a layout decision, not a
  // purchase (same stance as buildmode.moveBuild).
  function fromInventory(itemId, tx, ty, rot, opts) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    opts = opts || {};
    var zone = zoneOf(opts.zone), p0 = loadP();
    var tray = (p0 && p0.baseTray) || [], pos = -1, i;
    for (i = 0; i < tray.length; i++) if (tray[i].iid === itemId) { pos = i; break; }
    if (pos < 0) return { ok: false, error: 'NO_ITEM' };
    var it = tray[pos];
    rot = (rot == null ? (it.rot || 0) : (rot | 0)) & 3;
    var v = canPlace(it.type, tx, ty, rot, { profile: p0, zone: zone, blocked: opts.blocked });
    if (!v.ok) return { ok: false, error: v.reason, at: v.at || null };
    var w = tileToWorld(it.type, tx, ty, rot);
    e.mutateProfile(function (p) {
      var tr = ensureTray(p), at = -1, j;
      for (j = 0; j < tr.length; j++) if (tr[j].iid === itemId) { at = j; break; }
      if (at < 0) return;
      var item = tr[at];
      tr.splice(at, 1);
      if (!Array.isArray(p.builds)) p.builds = [];
      p.builds.push(toBuildEntry(item, zone, w.x, w.y, rot));
    });
    bump();
    return { ok: true, iid: itemId, type: it.type, tx: tx, ty: ty, rot: rot, x: w.x, y: w.y };
  }

  // The tray as the UI shows it: GROUPED BY TYPE AND LEVEL, CoC-style stacks.
  function inventory(p) {
    p = prof(p);
    var tray = (p && p.baseTray) || [], groups = {}, order = [];
    for (var i = 0; i < tray.length; i++) {
      var it = tray[i], lvl = it.lvl | 0 || 1, gk = it.type + '@' + lvl;
      var g = groups[gk];
      if (!g) { g = groups[gk] = { key: gk, type: it.type, lvl: lvl, cat: catOf(it.type), fp: footprint(it.type, 0), count: 0, iids: [] }; order.push(g); }
      g.count++; g.iids.push(it.iid);
    }
    order.sort(function (a, b) { return a.cat === b.cat ? (a.type < b.type ? -1 : 1) : (a.cat < b.cat ? -1 : 1); });
    return { total: tray.length, groups: order };
  }

  /* ====================================================================== *
   * (6) WHOLE-LAYOUT TRANSFORMS -- atomic or nothing
   * ====================================================================== *
   * The pre-check runs over EVERY piece before a single write. A shift that would push
   * any piece off the board is rejected whole, never half-applied, so you can hammer the
   * arrow keys against a wall and the base never smears.
   */
  function planAll(p, zone, fn) {
    p = prof(p); zone = zoneOf(zone);
    var builds = (p && p.builds) || [], plan = [], i;
    for (i = 0; i < builds.length; i++) {
      var b = builds[i]; if (!b || b.zone !== zone) continue;
      var a = entryTile(b), rot = b.rot || 0;
      if (!inBounds(b.type, a.tx, a.ty, rot)) return { ok: false, reason: 'OFF_GRID', idx: i, type: b.type };
      var n = fn(b, a, rot);
      if (!inBounds(b.type, n.tx, n.ty, n.rot)) return { ok: false, reason: 'OUT_OF_BOUNDS', idx: i, type: b.type, tx: n.tx, ty: n.ty };
      plan.push({ idx: i, type: b.type, tx: n.tx, ty: n.ty, rot: n.rot });
    }
    // self-consistency: the transform is rigid, so the moved set must not self-collide
    var seen = {};
    for (i = 0; i < plan.length; i++) {
      var ts = tilesFor(plan[i].type, plan[i].tx, plan[i].ty, plan[i].rot);
      for (var j = 0; j < ts.length; j++) {
        if (seen[ts[j]] != null) return { ok: false, reason: 'SELF_OVERLAP', idx: plan[i].idx, other: seen[ts[j]] };
        seen[ts[j]] = plan[i].idx;
      }
    }
    return { ok: true, plan: plan };
  }

  function applyPlan(plan, zone) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    zone = zoneOf(zone);
    e.mutateProfile(function (p) {
      var builds = p.builds || [];
      for (var i = 0; i < plan.length; i++) {
        var it = plan[i], b = builds[it.idx]; if (!b) continue;
        var w = tileToWorld(it.type, it.tx, it.ty, it.rot);
        b.x = w.x; b.y = w.y;
        if (it.rot) b.rot = it.rot; else if (b.rot) delete b.rot;   // falsy-safe, rot 0 is never written
      }
    });
    bump();
    return { ok: true, moved: plan.length };
  }

  // Shift the whole layout dx,dy tiles. Atomic: pre-checked, then written.
  function moveAll(dx, dy, opts) {
    opts = opts || {};
    var zone = zoneOf(opts.zone);
    var r = planAll(opts.profile, zone, function (b, a, rot) { return { tx: a.tx + (dx | 0), ty: a.ty + (dy | 0), rot: rot }; });
    if (!r.ok) return { ok: false, error: r.reason, idx: r.idx, type: r.type, moved: 0 };
    if (opts.dryRun) return { ok: true, dryRun: true, moved: r.plan.length, plan: r.plan };
    var w = applyPlan(r.plan, zone);
    return w.ok ? { ok: true, moved: w.moved, dx: dx | 0, dy: dy | 0 } : { ok: false, error: w.error, moved: 0 };
  }

  // Rotate the whole layout 90deg about the board center. dir 1 = clockwise, -1 = ccw.
  // Square board only: a non-square rotation is not a bijection on the tile set.
  function rotateAll(dir, opts) {
    opts = opts || {};
    if (CFG.cols !== CFG.rows) return { ok: false, error: 'NON_SQUARE_GRID', moved: 0 };
    var N = CFG.cols, cw = (dir | 0) >= 0 ? 1 : -1, zone = zoneOf(opts.zone);
    var r = planAll(opts.profile, zone, function (b, a, rot) {
      var f = footprint(b.type, rot);
      // CW:  (tx,ty,w,h) -> anchor (N - ty - h, tx), footprint swaps -> rot + 1
      // CCW: (tx,ty,w,h) -> anchor (ty, N - tx - w), footprint swaps -> rot + 3
      if (cw > 0) return { tx: N - a.ty - f.h, ty: a.tx, rot: (rot + 1) & 3 };
      return { tx: a.ty, ty: N - a.tx - f.w, rot: (rot + 3) & 3 };
    });
    if (!r.ok) return { ok: false, error: r.reason, idx: r.idx, type: r.type, moved: 0 };
    if (opts.dryRun) return { ok: true, dryRun: true, moved: r.plan.length, plan: r.plan };
    var w = applyPlan(r.plan, zone);
    return w.ok ? { ok: true, moved: w.moved, dir: cw } : { ok: false, error: w.error, moved: 0 };
  }

  /* ====================================================================== *
   * (7) LAYOUT SLOTS -- named saved bases
   * ====================================================================== *
   * p.baseLayouts = { "<zone>/<name>": { name, zone, t, cols, rows, tile, builds:[], tray:[] } }
   * A layout is a SHAPE, not a job queue: b.uc is stripped on save. Loading refuses while
   * a builder is mid-job in the zone, so no crew slot is ever orphaned by a swap.
   */
  var MAX_SLOTS = 8;
  function slotKey(zone, name) { return zoneOf(zone) + '/' + String(name); }
  function stripUc(b) { var o = {}, k; for (k in b) if (b.hasOwnProperty(k) && k !== 'uc') o[k] = b[k]; return o; }

  function saveLayout(name, opts) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    if (!name) return { ok: false, error: 'NO_NAME' };
    opts = opts || {};
    var zone = zoneOf(opts.zone), sk = slotKey(zone, name), saved = 0, err = null;
    e.mutateProfile(function (p) {
      if (!p.baseLayouts || typeof p.baseLayouts !== 'object') p.baseLayouts = {};
      if (!p.baseLayouts[sk] && Object.keys(p.baseLayouts).length >= MAX_SLOTS) { err = 'SLOTS_FULL'; return; }
      var builds = p.builds || [], snap = [], i;
      for (i = 0; i < builds.length; i++) if (builds[i] && builds[i].zone === zone) snap.push(stripUc(builds[i]));
      var tray = (p.baseTray || []).slice();
      p.baseLayouts[sk] = {
        name: String(name), zone: zone, t: Date.now(),
        cols: CFG.cols, rows: CFG.rows, tile: CFG.tile, originX: CFG.originX, originY: CFG.originY,
        builds: snap, tray: tray
      };
      saved = snap.length;
    });
    bump();
    return err ? { ok: false, error: err } : { ok: true, name: String(name), zone: zone, builds: saved };
  }

  function loadLayout(name, opts) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    opts = opts || {};
    var zone = zoneOf(opts.zone), sk = slotKey(zone, name), p0 = loadP();
    var L = p0 && p0.baseLayouts && p0.baseLayouts[sk];
    if (!L) return { ok: false, error: 'NO_LAYOUT' };
    var builds = (p0 && p0.builds) || [], i;
    for (i = 0; i < builds.length; i++) if (builds[i] && builds[i].zone === zone && builds[i].uc) return { ok: false, error: 'BUILDERS_BUSY' };
    if (L.tile !== CFG.tile) return { ok: false, error: 'TILE_MISMATCH', saved: L.tile, live: CFG.tile };
    var placed = 0;
    e.mutateProfile(function (p) {
      if (!Array.isArray(p.builds)) p.builds = [];
      for (var j = p.builds.length - 1; j >= 0; j--) if (p.builds[j] && p.builds[j].zone === zone) p.builds.splice(j, 1);
      for (var k = 0; k < L.builds.length; k++) { p.builds.push(JSON.parse(JSON.stringify(L.builds[k]))); placed++; }
      p.baseTray = JSON.parse(JSON.stringify(L.tray || []));
    });
    bump();
    return { ok: true, name: L.name, zone: zone, builds: placed, tray: (L.tray || []).length };
  }

  function listLayouts(p, zone) {
    p = prof(p); zone = zoneOf(zone);
    var L = (p && p.baseLayouts) || {}, out = [];
    for (var k in L) if (L.hasOwnProperty(k) && L[k] && L[k].zone === zone) out.push({ name: L[k].name, zone: L[k].zone, t: L[k].t, builds: (L[k].builds || []).length, tray: (L[k].tray || []).length, cols: L[k].cols, rows: L[k].rows });
    out.sort(function (a, b) { return (b.t | 0) - (a.t | 0); });
    return { max: MAX_SLOTS, used: out.length, slots: out };
  }

  function deleteLayout(name, opts) {
    var e = econ(); if (!e || !e.mutateProfile) return { ok: false, error: 'NO_ECON' };
    opts = opts || {};
    var sk = slotKey(opts.zone, name), had = false;
    e.mutateProfile(function (p) { if (p.baseLayouts && p.baseLayouts[sk]) { had = true; delete p.baseLayouts[sk]; } });
    bump();
    return had ? { ok: true, name: String(name) } : { ok: false, error: 'NO_LAYOUT' };
  }

  /* ====================================================================== *
   * (8) SCOUT VIEW -- what an attacker actually sees
   * ====================================================================== */
  function scoutView(p, zone, opts) {
    p = prof(p); zone = zoneOf(zone);
    var occ = occupancy(p, zone, opts), out = [], hiddenN = 0;
    for (var i = 0; i < occ.cells.length; i++) {
      var c = occ.cells[i];
      if (isHidden(c.type)) { hiddenN++; continue; }
      out.push({ idx: c.idx, type: c.type, tx: c.tx, ty: c.ty, rot: c.rot, cat: catOf(c.type), fp: footprint(c.type, c.rot) });
    }
    return { zone: zone, visible: out, hiddenCount: hiddenN, total: occ.count };
  }

  /* ====================================================================== *
   * (9) DEBUG -- ascii tile map (headless, no DOM)
   * ====================================================================== */
  var GLYPH = { wall: '#', trap: '^', deco: '.', hut: 'h', storage: 'S', defense: 'D', army: 'A', core: 'T', garden: 'g' };
  function tileMap(p, zone, opts) {
    opts = opts || {};
    var occ = opts.occ || occupancy(p, zone, opts);
    var lines = [], x, y;
    for (y = 0; y < CFG.rows; y++) {
      var row = '';
      for (x = 0; x < CFG.cols; x++) {
        var c = occ.map[key(x, y)];
        if (!c) { row += '-'; continue; }
        if (opts.scout && isHidden(c.type)) { row += '-'; continue; }
        row += (c.fixed ? 'X' : (GLYPH[catOf(c.type)] || '?'));
      }
      lines.push(row);
    }
    return lines.join('\n');
  }

  /* ====================================================================== *
   * (10) CATALOG AUDIT -- where buildmode's pixel boxes disagree with tiles
   * ====================================================================== *
   * Not cosmetic. buildmode's cw/ch is the COLLISION box; if it is wider than the tile
   * footprint, two flush 1x1 walls overlap in collision while the grid says they are
   * legal. This reports the exact cw/ch each registered type should carry.
   */
  function catalogAudit(struct) {
    var S = struct || (global.AK_BUILDMODE && global.AK_BUILDMODE.STRUCT) || null;
    if (!S) return { ok: false, error: 'NO_STRUCT', rows: [] };
    var rows = [], k;
    for (k in FOOTPRINTS) {
      if (!FOOTPRINTS.hasOwnProperty(k)) continue;
      var d = S[k];
      if (!d) { rows.push({ type: k, status: 'NO_STRUCT_ENTRY', want: { cw: FOOTPRINTS[k].w * CFG.tile, ch: FOOTPRINTS[k].h * CFG.tile } }); continue; }
      var wantW = FOOTPRINTS[k].w * CFG.tile, wantH = FOOTPRINTS[k].h * CFG.tile;
      var haveW = d.shape === 'circle' ? (d.cr || 24) * 2 : (d.cw || 66);
      var haveH = d.shape === 'circle' ? (d.cr || 24) * 2 : (d.ch || 66);
      if (haveW > wantW || haveH > wantH) rows.push({ type: k, status: 'PIXEL_OVERFLOW', have: { cw: haveW, ch: haveH }, want: { cw: wantW, ch: wantH } });
    }
    return { ok: true, rows: rows, clean: rows.length === 0 };
  }

  /* ====================================================================== *
   * (11) VERSION STAMP -- lets a renderer cache against edits
   * ====================================================================== */
  var VER = 0;
  function bump() { VER++; try { if (global.AK_BUILDMODE && global.AK_BUILDMODE.refresh) global.AK_BUILDMODE.refresh(); } catch (_) {} }
  function version() { return VER; }

  /* ====================================================================== *
   * EXPORTS
   * ====================================================================== */
  var API = {
    // config
    configure: configure, config: config, fitToWorld: fitToWorld,
    // registry
    FOOTPRINTS: FOOTPRINTS, spec: spec, known: known, catOf: catOf, isHidden: isHidden,
    footprint: footprint, snapsClean: snapsClean,
    // conversions (PURE, node-requireable, round-trip testable)
    tileToWorld: tileToWorld, worldToTile: worldToTile, snapPointer: snapPointer,
    entryTile: entryTile, tileRect: tileRect, tilesFor: tilesFor, inBounds: inBounds,
    key: key, unkey: unkey,
    // rules
    occupancy: occupancy, canPlace: canPlace, highlight: highlight,
    // inventory tray
    toInventory: toInventory, fromInventory: fromInventory, clearAll: clearAll, inventory: inventory,
    // whole-layout transforms
    moveAll: moveAll, rotateAll: rotateAll,
    // layout slots
    saveLayout: saveLayout, loadLayout: loadLayout, listLayouts: listLayouts, deleteLayout: deleteLayout,
    maxSlots: MAX_SLOTS,
    // views + debug
    scoutView: scoutView, tileMap: tileMap, catalogAudit: catalogAudit, version: version
  };

  global.AK_BASEGRID = API;

  // Register with the hub ONLY when the registry is present. This module is a pure data
  // layer, so it stays fully usable (and node-requireable) on pages with no registry.
  if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) {
    global.AK_SYSTEMS.register({
      id: 'basegrid',
      init: function (ctx) {
        try {
          if (ctx && ctx.econ) CFG.econ = ctx.econ;
          if (ctx && ctx.zoneId) CFG.zone = ctx.zoneId;
          if (ctx && ctx.world && ctx.world.WORLD_W) fitToWorld(ctx.world.WORLD_W, ctx.world.WORLD_H);
        } catch (_) {}
      }
    });
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : globalThis);
