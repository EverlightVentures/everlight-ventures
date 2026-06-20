/* game/systems/worldmap.js -- AK_SYSTEMS module: SPRINT 1 "THE ZOOM" (World-Map / base view).
 * ============================================================================
 * Grounds: AK_2D_3D_CONCEPT.md S2 (MODE A World Map), S3 (transition state
 * machine), S9 (sensor packages incl. Dynamic Obstacle). MODULE_CONTRACT S1.2
 * (module shape), S2 (ctx). Touches NO shared files -- self-registers + mounts
 * its own HUD button + uses ctx.overlay.open for the zoomed view.
 *
 * WHAT IT SHIPS
 *   (A) MODE A "World Map" as a Clash-of-Clans-style top-down view of the
 *       PLAYER'S OWN territory -- the live 3x3 ZONES grid drawn as a base the
 *       player can PAN (drag) + PINCH-zoom. Reuses the existing districtBg + the
 *       building facade art. Shows building Lv badges, the Town Hall (ARENA,
 *       crowned), perimeter walls + open space, locked districts as silhouettes
 *       (POLICE CHECKPOINT / COLLAPSED BRIDGE). Tap a district -> select ->
 *       "DIVE IN" reuses the host's own enterZone() transition (S3 dive_in).
 *       Toggled from the hub-walk via a floating gold HUD button (init-mounted).
 *   (B) OBSTACLE-COLLISION layer for the hub -- a per-district collision-geometry
 *       model (rects/circles matching the painted fences / cars / trains) exposed
 *       as window.AK_COLLISION. The host AK-MOVE3 block calls resolve() to block
 *       me.x/me.y out of obstacles and SLIDE along edges. Starter geometry for
 *       HOME_TURF + DOWNTOWN + THE_YARDS ships here (BUILTIN); ZONES.obstacles
 *       overrides it when the Lead relocates the data.
 *
 * APPROACH DECISION (lower-risk, per the brief):
 *   Zoomed view uses ctx.overlay.open -- NOT an onDrawWorld camera-scale hack.
 *   WHY: the host draw() is FROZEN and renders the live hub every frame off
 *   cam.x/cam.y + wx()/wy(); onDrawWorld composites OVER that live render in
 *   world-space (it can't replace it) and the hub keeps running physics +
 *   edge-transitions underneath (the player could walk into a district edge
 *   while "zoomed"). ctx.overlay.open gives a fresh fullscreen Canvas2D, FREEZES
 *   the hub (state='TRANSITIONING' -> movement/ticks/roamers/edge-transitions
 *   all pause), routes pointer events for pan/pinch, and restores cleanly on
 *   close -- exactly the contract's "raid target picker" use case (S2.e). Zero
 *   risk of corrupting the live hub canvas state.
 *
 * HARD RULES honored: 2.5D Canvas2D only, battler untouched. Soft-currency /
 * cosmetic only (this view grants nothing -- it is a strategic VIEW). "crew"
 * never "clan". Gritty gold cyberpunk dog-gang voice. Reuses ZONES + the painted
 * districtBg + facade art BY PATH. Headless-safe: no top-level DOM/localStorage.
 * ========================================================================== */
(function (global) {
  'use strict';

  /* ---- palette (Everlight gold cyberpunk) -------------------------------- */
  var GOLD = '#e8c55a', GOLD_D = '#c9a84c', TXT = '#E8E8E8', DIM = '#9a8f6a',
      INK = '#06060a', RED = '#C0392B', WALLC = '#6b5a2e';

  /* ---- world dims (mirror the host constants; read-only, asset layout) ---- */
  var ZW = 1700, ZH = 1300;

  /* ---- building facade + district-bg art (reuse the SAME painted assets the
   * hub loads; cosmetic filename maps only -- low-risk asset reuse) ---------- */
  var FAC = { TROPHY:'trophy', FIXER:'fixer', GARAGE:'garage', DROP:'drop',
    KENNEL:'kennel', CLAN:'clan', PASS:'pass', WARD:'wardrobe', ARCH:'archive',
    STREET:'street', ARCADE:'arcade', GEM:'gem_mine', MINT:'gold_mint',
    FORGE:'card_forge', LAB:'research_lab', GEN:'power_gen', ARENA:'' };
  var DBG = { HOME_TURF:'the_lot', DOWNTOWN:'downtown', NEON_HEIGHTS:'neon_heights',
    THE_YARDS:'the_yards', FACTORY_ROW:'factory_row', THE_STRIP:'the_strip',
    THE_DOCKS:'the_docks' };
  var GLYPH = { ARENA:'👑', TROPHY:'🏆', KENNEL:'🦴',
    DROP:'🛒', GARAGE:'🃏', WARD:'👕', ARCH:'📜',
    CLAN:'🏴', PASS:'🎟️', FIXER:'🎯', GEM:'⛏️',
    MINT:'💰', FORGE:'🔧', STREET:'🥊', ARCADE:'🕹️',
    LAB:'🔬', GEN:'⚡' };

  /* ---- lazy hub-art cache (graceful fallback to colored icon) ------------- */
  var _img = {};
  function img(path) {
    if (typeof Image === 'undefined' || !path) return null;
    if (_img.hasOwnProperty(path)) return _img[path];
    var im = new Image(); _img[path] = im;
    try { im.src = path; } catch (_) { _img[path] = null; }
    return im;
  }
  function ready(im) { return !!(im && im.complete && im.naturalWidth > 0); }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  /* ======================================================================== *
   * (B) OBSTACLE-COLLISION LAYER  -- window.AK_COLLISION
   *   Pure geometry; defined at load (no DOM) so the host AK-MOVE3 edit can call
   *   it on the very first frame. Player is a circle (me.x,me.y,me.r); obstacles
   *   are rects {type:'rect',x,y,w,h}  (x,y = TOP-LEFT, world units) and circles
   *   {type:'circle',x,y,r} (x,y = CENTER). 'kind' is art-flavor only.
   *   resolve() pushes the player OUT of every overlap along the shortest normal
   *   -> motion parallel to a wall is preserved == sliding (no axis-locking).
   * ======================================================================== */

  // STARTER geometry, hand-placed to MATCH the painted maps' fences/cars/trains
  // while leaving every building DOOR, the centre plaza, the spawn points, and
  // all 4 edge corridors clear. Coords are in the ZW x ZH (1700x1300) world.
  var BUILTIN = {
    // --- HOME_TURF / "THE LOT" (spawn hub; ARENA=Town Hall @850,360) -------
    HOME_TURF: [
      { type:'rect',   x:1466, y:280,  w:52,  h:560, kind:'train' }, // east freight rail (clear of KENNEL@1270 + E edge@1658)
      { type:'rect',   x:520,  y:780,  w:96,  h:48,  kind:'car'   }, // junked sedan, centre-left
      { type:'rect',   x:1040, y:556,  w:120, h:18,  kind:'fence' }, // chain fence NE of plaza
      { type:'circle', x:300,  y:520,  r:50,         kind:'rubble'}, // collapsed-wall rubble NW
      { type:'rect',   x:980,  y:1132, w:300, h:16,  kind:'fence' }, // south fence (clear of NPC@850,1080 + S edge)
      { type:'circle', x:1180, y:640,  r:40,         kind:'rubble'}  // dumpster pile mid-right
    ],
    // --- DOWNTOWN (DROP@560,560 + GARAGE@1140,560; arrive bottom-centre) ----
    DOWNTOWN: [
      { type:'rect',   x:800,  y:516,  w:104, h:50,  kind:'car'   }, // parked car between the two shops
      { type:'rect',   x:300,  y:760,  w:140, h:18,  kind:'fence' }, // SW fence line
      { type:'circle', x:1380, y:820,  r:46,         kind:'rubble'}, // SE construction rubble
      { type:'rect',   x:740,  y:864,  w:90,  h:46,  kind:'car'   }, // second car (clear of y=1150 landing)
      { type:'rect',   x:1250, y:300,  w:54,  h:230, kind:'train' }  // NE transit barrier (E of GARAGE footprint@1225, clear of E edge)
    ],
    // --- THE_YARDS (docks/industrial; CLAN@560,560 PASS@1140,560 FIXER@850,960)
    THE_YARDS: [
      { type:'rect',   x:120,  y:760,  w:60,  h:420, kind:'train' }, // long W-rail train (x>42 corridor kept)
      { type:'rect',   x:780,  y:516,  w:120, h:18,  kind:'fence' }, // fence between CLAN/PASS
      { type:'circle', x:560,  y:824,  r:48,         kind:'rubble'}, // scrap pile below CLAN (door@612 clear)
      { type:'rect',   x:1180, y:824,  w:96,  h:46,  kind:'car'   }, // junked car SE
      { type:'circle', x:1040, y:1040, r:44,         kind:'rubble'}  // scrap near FIXER (door@1008 clear)
    ]
  };

  function obstaclesFor(zone) {
    if (!zone) return [];
    if (zone.obstacles && zone.obstacles.length) return zone.obstacles; // ZONES override wins
    return BUILTIN[zone.id] || [];
  }

  // true if circle (x,y,r) overlaps ANY obstacle in obs
  function blocks(x, y, r, obs) {
    if (!obs) return false;
    for (var i = 0; i < obs.length; i++) {
      var o = obs[i];
      if (o.type === 'circle') {
        if (Math.hypot(x - o.x, y - o.y) < r + (o.r || 0)) return true;
      } else {
        var cx = clamp(x, o.x, o.x + o.w), cy = clamp(y, o.y, o.y + o.h);
        var dx = x - cx, dy = y - cy;
        if (dx * dx + dy * dy < r * r) return true;
      }
    }
    return false;
  }

  // push me OUT of every obstacle (slide). px,py = pre-move pos (anti-stick fallback).
  function resolve(me, px, py, obs) {
    if (!me || !obs || !obs.length) return;
    var r = me.r || 20;
    for (var iter = 0; iter < 3; iter++) {
      var moved = false;
      for (var i = 0; i < obs.length; i++) {
        var o = obs[i];
        if (o.type === 'circle') {
          var dx = me.x - o.x, dy = me.y - o.y, rr = r + (o.r || 0), d = Math.hypot(dx, dy);
          if (d < rr) {
            if (d > 0.0001) { var p = rr - d; me.x += dx / d * p; me.y += dy / d * p; }
            else { me.x += rr; }
            moved = true;
          }
        } else {
          var ox = o.x, oy = o.y, ow = o.w, oh = o.h;
          var cx = clamp(me.x, ox, ox + ow), cy = clamp(me.y, oy, oy + oh);
          var ddx = me.x - cx, ddy = me.y - cy, d2 = ddx * ddx + ddy * ddy;
          if (d2 < r * r) {
            if (d2 > 0.0001) { var dd = Math.sqrt(d2), pp = r - dd; me.x += ddx / dd * pp; me.y += ddy / dd * pp; }
            else { // centre is INSIDE the rect -> eject along the least-penetration axis
              var L = me.x - ox, R = (ox + ow) - me.x, T = me.y - oy, Bm = (oy + oh) - me.y;
              var mn = Math.min(L, R, T, Bm);
              if (mn === L) me.x = ox - r; else if (mn === R) me.x = ox + ow + r;
              else if (mn === T) me.y = oy - r; else me.y = oy + oh + r;
            }
            moved = true;
          }
        }
      }
      if (!moved) break;
    }
    // anti-stick safety: if still embedded but the pre-move spot was clear, revert
    if (px != null && py != null && blocks(me.x, me.y, r, obs) && !blocks(px, py, r, obs)) {
      me.x = px; me.y = py;
    }
  }

  // building-placement rule: a building's DOOR (b.x, b.y+b.h/2) must be clear AND
  // its footprint must not overlap an obstacle. Used by future build/rearrange.
  function validPlacement(zone, b, clearance) {
    var obs = obstaclesFor(zone); if (!obs.length) return true;
    var doorX = b.x, doorY = b.y + (b.h || 0) / 2, c = (clearance == null ? 30 : clearance) + 23;
    if (blocks(doorX, doorY, c, obs)) return false;
    // footprint vs obstacle AABB overlap
    var bx = b.x - (b.w || 0) / 2, by = b.y - (b.h || 0) / 2, bw = b.w || 0, bh = b.h || 0;
    for (var i = 0; i < obs.length; i++) {
      var o = obs[i];
      var ox, oy, ow, oh;
      if (o.type === 'circle') { ox = o.x - o.r; oy = o.y - o.r; ow = o.r * 2; oh = o.r * 2; }
      else { ox = o.x; oy = o.y; ow = o.w; oh = o.h; }
      if (bx < ox + ow && bx + bw > ox && by < oy + oh && by + bh > oy) return false;
    }
    return true;
  }

  global.AK_COLLISION = {
    resolve: resolve, blocks: blocks, validPlacement: validPlacement,
    obstaclesFor: obstaclesFor, OBSTACLES: BUILTIN
  };

  /* ---- LATER-SPRINT server hook (rival/crew bases on the world map) -------- */
  // TODO-SERVER: replace with an ak-worldmap edge fn returning crew + rival base
  // snapshots (ak_grants pattern, soft-currency loot only). Stubbed empty so the
  // base view renders the player's OWN territory now; "SCOUT RIVALS" stays locked.
  function getRivalBases() { return []; }

  /* If there's no registry we're not on the hub page -- AK_COLLISION is still
   * exported above (harmless), but skip all the DOM / overlay wiring. */
  if (!global.AK_SYSTEMS) return;

  /* ======================================================================== *
   * (A) THE WORLD-MAP / BASE VIEW  (ctx.overlay.open)
   * ======================================================================== */
  var WM = { ctx:null, ov:null, cam:{ x:0, y:0 }, scale:1, fitScale:1,
    sel:null, ptrs:{}, pinch:null, panMoved:0, btns:[] };

  // visual grid: each district is a TILE square with GAP between, WALL perimeter
  var TILE = 230, GAP = 30, WALL = 16;
  var GRID_W = 3 * TILE + 2 * GAP, GRID_H = 3 * TILE + 2 * GAP;

  function profile(ctx) { try { return ctx.econ ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }

  // building level for the badge -- single source of truth, in priority order:
  //   ctx.buildingLevels[id] (if the Lead exposes the host LV map) ->
  //   ARENA = real Town Hall level -> producer = profile.prod[id].lvl -> 1
  function buildingLevel(ctx, id) {
    try {
      if (ctx.buildingLevels && ctx.buildingLevels[id] != null) return ctx.buildingLevels[id] | 0;
      if (id === 'ARENA' && ctx.econ && ctx.econ.townHallLevel) return ctx.econ.townHallLevel();
      var p = profile(ctx);
      if (p && p.prod && p.prod[id] && p.prod[id].lvl) return p.prod[id].lvl | 0;
    } catch (_) {}
    return 1;
  }

  function rr(g, x, y, w, h, rad) {
    g.beginPath(); g.moveTo(x + rad, y);
    g.arcTo(x + w, y, x + w, y + h, rad); g.arcTo(x + w, y + h, x, y + h, rad);
    g.arcTo(x, y + h, x, y, rad);         g.arcTo(x, y, x + w, y, rad); g.closePath();
  }
  function label(g, s, x, y, size, col, weight, align) {
    g.fillStyle = col || TXT; g.textAlign = align || 'center'; g.textBaseline = 'middle';
    g.font = (weight || '700') + ' ' + size + 'px Inter, system-ui, sans-serif';
    g.fillText(s, x, y);
  }

  // grid (gx,gy) -> top-left of that district tile, in GRID space (pre cam/scale)
  function tileXY(gx, gy) { return { x: gx * (TILE + GAP), y: gy * (TILE + GAP) }; }
  // GRID space -> screen
  function sx(x) { return WM.cam.x + x * WM.scale; }
  function sy(y) { return WM.cam.y + y * WM.scale; }

  function fitToScreen(vp) {
    var pad = 46;
    WM.fitScale = Math.min((vp.w - pad * 2) / GRID_W, (vp.h - 150) / GRID_H);
    WM.scale = WM.fitScale;
    WM.cam.x = (vp.w - GRID_W * WM.scale) / 2;
    WM.cam.y = (vp.h - GRID_H * WM.scale) / 2 - 8;
  }
  function clampCam(vp) {
    var gw = GRID_W * WM.scale, gh = GRID_H * WM.scale, pad = 90;
    if (gw <= vp.w) WM.cam.x = (vp.w - gw) / 2;
    else WM.cam.x = clamp(WM.cam.x, vp.w - gw - pad, pad);
    if (gh <= vp.h) WM.cam.y = (vp.h - gh) / 2 - 8;
    else WM.cam.y = clamp(WM.cam.y, vp.h - gh - pad, pad);
  }

  // ---- draw one district tile (bg art / tint, walls, buildings, badges) ----
  function drawDistrict(g, ctx, z) {
    var t = tileXY(z.gx, z.gy), X = sx(t.x), Y = sy(t.y), S = TILE * WM.scale;
    if (X > WM.ctx.world.W || Y > WM.ctx.world.H || X + S < 0 || Y + S < 0) return; // cull

    g.save();
    rr(g, X, Y, S, S, 12 * WM.scale); g.clip();
    // district background -- reuse the painted districtBg PNG, else the tint
    var bg = DBG[z.id] ? img('assets/hub/' + DBG[z.id] + '_bg.png') : null;
    if (ready(bg)) { g.globalAlpha = z.locked ? 0.32 : 0.9; g.drawImage(bg, X, Y, S, S); g.globalAlpha = 1; }
    else { var c = z.tint || [12, 12, 18]; g.fillStyle = 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')'; g.fillRect(X, Y, S, S); }
    if (z.locked) { g.fillStyle = 'rgba(6,6,10,.62)'; g.fillRect(X, Y, S, S); }
    g.restore();

    // tile frame + perimeter "wall" feel
    g.save();
    rr(g, X, Y, S, S, 12 * WM.scale);
    g.lineWidth = Math.max(2, WALL * 0.5 * WM.scale);
    g.strokeStyle = z.locked ? 'rgba(120,120,130,.5)' : (z.id === WM.ctx.zoneId ? GOLD : 'rgba(201,168,76,.42)');
    if (z.id === WM.ctx.zoneId) { g.shadowColor = GOLD; g.shadowBlur = 16; }
    g.stroke();
    g.restore();

    // district name banner
    label(g, z.name, X + S / 2, Y + 13 * WM.scale, clamp(13 * WM.scale, 9, 15), z.locked ? '#9a9aa6' : GOLD, '800');

    if (z.locked) {
      label(g, '🔒', X + S / 2, Y + S / 2 - 8 * WM.scale, clamp(30 * WM.scale, 16, 34), '#cfcfd6', '800');
      label(g, z.barrierLabel || 'SEALED', X + S / 2, Y + S / 2 + 18 * WM.scale, clamp(10 * WM.scale, 8, 12), '#9a9aa6', '700');
      return;
    }

    // obstacles (CoC-style base clutter -- matches the live collision geometry)
    var obs = obstaclesFor(z);
    g.save(); g.globalAlpha = 0.5;
    for (var oi = 0; oi < obs.length; oi++) {
      var o = obs[oi];
      g.fillStyle = (o.kind === 'train') ? 'rgba(90,80,110,.9)' : (o.kind === 'car') ? 'rgba(120,70,60,.9)' : (o.kind === 'fence') ? 'rgba(150,130,80,.85)' : 'rgba(80,80,90,.85)';
      if (o.type === 'circle') { g.beginPath(); g.arc(X + (o.x / ZW) * S, Y + (o.y / ZH) * S, Math.max(1.5, (o.r / ZW) * S), 0, 7); g.fill(); }
      else { g.fillRect(X + (o.x / ZW) * S, Y + (o.y / ZH) * S, Math.max(1.5, (o.w / ZW) * S), Math.max(1.5, (o.h / ZH) * S)); }
    }
    g.restore();

    // buildings -- placed at their REAL relative (x,y) inside the district
    var bs = z.buildings || [];
    for (var i = 0; i < bs.length; i++) {
      var b = bs[i];
      var isTH = (b.id === 'ARENA');
      var bw = (isTH ? 0.20 : 0.155) * S, bx = X + (b.x / ZW) * S, by = Y + (b.y / ZH) * S;
      g.save();
      // facade art clipped to the icon, else colored chip
      var fa = (FAC[b.id]) ? img('assets/hub/' + FAC[b.id] + '.png') : null;
      rr(g, bx - bw / 2, by - bw / 2, bw, bw, 6 * WM.scale); g.clip();
      if (ready(fa)) { g.drawImage(fa, bx - bw / 2, by - bw / 2, bw, bw); }
      else { g.fillStyle = '#1a1925'; g.fillRect(bx - bw / 2, by - bw / 2, bw, bw); }
      g.restore();
      // chip frame (Town Hall = crowned gold glow)
      g.save();
      rr(g, bx - bw / 2, by - bw / 2, bw, bw, 6 * WM.scale);
      g.lineWidth = isTH ? Math.max(2, 3 * WM.scale) : Math.max(1, 2 * WM.scale);
      g.strokeStyle = isTH ? GOLD : (b.col || GOLD_D);
      if (isTH) { g.shadowColor = GOLD; g.shadowBlur = 14; }
      g.stroke();
      g.restore();
      if (!ready(fa)) label(g, GLYPH[b.id] || '🏢', bx, by, clamp(bw * 0.5, 9, 26), '#fff', '700');
      // Lv badge
      var lv = buildingLevel(ctx, b.id);
      var by2 = by + bw / 2;
      g.fillStyle = 'rgba(8,8,14,.9)'; rr(g, bx - 13 * WM.scale, by2 - 6 * WM.scale, 26 * WM.scale, 13 * WM.scale, 4 * WM.scale); g.fill();
      label(g, (isTH ? 'TH ' : 'Lv') + lv, bx, by2, clamp(9 * WM.scale, 7, 11), isTH ? GOLD : (b.col || GOLD), '800');
      if (isTH) label(g, 'TOWN HALL', bx, by - bw / 2 - 8 * WM.scale, clamp(9 * WM.scale, 7, 11), GOLD, '800');
    }

    // "YOU ARE HERE" + the player dot on the active district
    if (z.id === WM.ctx.zoneId) {
      var me = WM.ctx.me;
      var px = X + clamp(me.x / ZW, 0, 1) * S, py = Y + clamp(me.y / ZH, 0, 1) * S;
      g.save(); g.fillStyle = '#fff'; g.shadowColor = GOLD; g.shadowBlur = 8;
      g.beginPath(); g.arc(px, py, Math.max(2.5, 4 * WM.scale), 0, 7); g.fill(); g.restore();
    }

    // selection ring
    if (WM.sel === z.id) {
      g.save(); rr(g, X - 3, Y - 3, S + 6, S + 6, 14 * WM.scale);
      g.lineWidth = 3; g.strokeStyle = GOLD; g.setLineDash([8, 6]); g.stroke(); g.restore();
    }
  }

  function liveTerritoryCount(ctx) {
    var n = 0, Z = ctx.ZONES; for (var k in Z) if (Z.hasOwnProperty(k) && !Z[k].locked) n++; return n;
  }

  // ---- screen-space HUD (title, close, rivals stub, selected-district bar) --
  function drawHud(g, vp, ctx) {
    WM.btns = [];
    // top title
    g.fillStyle = 'rgba(8,8,12,.78)'; g.fillRect(0, 0, vp.w, 50);
    label(g, '🗺️  YOUR TERRITORY', 14, 25, 15, GOLD, '900', 'left');
    label(g, liveTerritoryCount(ctx) + ' districts held', 14, 41, 11, DIM, '700', 'left');
    // close (x)
    var cb = { id:'close', x: vp.w - 50, y: 8, w: 38, h: 34 };
    g.fillStyle = 'rgba(255,255,255,.06)'; rr(g, cb.x, cb.y, cb.w, cb.h, 9); g.fill();
    label(g, '×', cb.x + cb.w / 2, cb.y + cb.h / 2, 24, '#ccc', '700'); WM.btns.push(cb);

    // bottom action bar
    var z = WM.sel ? ctx.ZONES[WM.sel] : null;
    var barY = vp.h - 78;
    g.fillStyle = 'rgba(8,8,12,.9)'; g.fillRect(0, barY, vp.w, 78);
    g.strokeStyle = 'rgba(201,168,76,.25)'; g.lineWidth = 1; g.beginPath(); g.moveTo(0, barY); g.lineTo(vp.w, barY); g.stroke();
    if (z) {
      label(g, z.name, 16, barY + 22, 14, z.locked ? '#9a9aa6' : GOLD, '800', 'left');
      var sub = z.locked ? (z.barrierLabel || 'SEALED -- soon')
        : ((z.buildings ? z.buildings.length : 0) + ' buildings  ·  ' + (z.id === ctx.zoneId ? 'you are here' : 'tap DIVE IN to walk it'));
      label(g, sub, 16, barY + 44, 11, DIM, '700', 'left');
      if (!z.locked && z.id !== ctx.zoneId) {
        var db = { id:'dive', z:z.id, x: vp.w - 150, y: barY + 18, w: 134, h: 42 };
        g.save(); rr(g, db.x, db.y, db.w, db.h, 11);
        var grd = g.createLinearGradient(0, db.y, 0, db.y + db.h); grd.addColorStop(0, GOLD); grd.addColorStop(1, GOLD_D);
        g.fillStyle = grd; g.fill(); g.restore();
        label(g, 'DIVE IN ▸', db.x + db.w / 2, db.y + db.h / 2, 14, '#15110a', '900'); WM.btns.push(db);
      } else if (!z.locked && z.id === ctx.zoneId) {
        label(g, 'YOU ARE HERE', vp.w - 16, barY + 36, 12, GOLD, '800', 'right');
      }
    } else {
      label(g, 'Tap a district to inspect it. Drag to pan, pinch to zoom.', 16, barY + 26, 12, DIM, '700', 'left');
      // rivals stub (later sprint -- server)
      var rb = { id:'rivals', x: vp.w - 150, y: barY + 18, w: 134, h: 42 };
      g.save(); rr(g, rb.x, rb.y, rb.w, rb.h, 11); g.fillStyle = 'rgba(255,255,255,.05)';
      g.fill(); g.strokeStyle = 'rgba(201,168,76,.3)'; g.lineWidth = 1; g.stroke(); g.restore();
      label(g, '🔒 SCOUT RIVALS', rb.x + rb.w / 2, barY + 39, 11, '#9a9aa6', '800'); WM.btns.push(rb);
    }
  }

  // ---- frame ----
  function drawFrame(g, dt, vp, ctx) {
    g.fillStyle = INK; g.fillRect(0, 0, vp.w, vp.h);
    // faint backdrop grid
    g.save(); g.strokeStyle = 'rgba(201,168,76,.05)'; g.lineWidth = 1;
    for (var x = (WM.cam.x % 60); x < vp.w; x += 60) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, vp.h); g.stroke(); }
    for (var y = (WM.cam.y % 60); y < vp.h; y += 60) { g.beginPath(); g.moveTo(0, y); g.lineTo(vp.w, y); g.stroke(); }
    g.restore();
    // perimeter wall around the whole 3x3 territory (CoC base wall)
    g.save();
    rr(g, sx(-WALL), sy(-WALL), (GRID_W + WALL * 2) * WM.scale, (GRID_H + WALL * 2) * WM.scale, 18 * WM.scale);
    g.lineWidth = Math.max(3, WALL * WM.scale); g.strokeStyle = WALLC; g.stroke();
    g.restore();
    // districts
    var Z = WM.ctx.ZONES;
    for (var k in Z) if (Z.hasOwnProperty(k)) { try { drawDistrict(g, ctx, Z[k]); } catch (_e) {} }
    drawHud(g, vp, ctx);
  }

  // ---- pointer: pan (1 finger) / pinch (2) / tap (select + buttons) --------
  function ptrList() { var a = []; for (var k in WM.ptrs) if (WM.ptrs.hasOwnProperty(k)) a.push(WM.ptrs[k]); return a; }
  function onPointer(e, api) {
    var vp = api.vp;
    if (e.type === 'pointerdown') {
      WM.ptrs[e.pointerId] = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY };
      WM.panMoved = 0;
      var pl = ptrList();
      if (pl.length === 2) WM.pinch = { d: Math.hypot(pl[0].x - pl[1].x, pl[0].y - pl[1].y), s: WM.scale,
        mx: (pl[0].x + pl[1].x) / 2, my: (pl[0].y + pl[1].y) / 2,
        wx: ((pl[0].x + pl[1].x) / 2 - WM.cam.x) / WM.scale, wy: ((pl[0].y + pl[1].y) / 2 - WM.cam.y) / WM.scale };
    } else if (e.type === 'pointermove') {
      var p = WM.ptrs[e.pointerId]; if (!p) return;
      var pdx = e.clientX - p.x, pdy = e.clientY - p.y; p.x = e.clientX; p.y = e.clientY;
      var pl2 = ptrList();
      if (pl2.length >= 2 && WM.pinch) {
        var nd = Math.hypot(pl2[0].x - pl2[1].x, pl2[0].y - pl2[1].y);
        WM.scale = clamp(WM.pinch.s * (nd / (WM.pinch.d || 1)), WM.fitScale * 0.55, 2.6);
        // keep the pinch midpoint anchored
        WM.cam.x = WM.pinch.mx - WM.pinch.wx * WM.scale;
        WM.cam.y = WM.pinch.my - WM.pinch.wy * WM.scale;
        clampCam(vp);
      } else {
        WM.cam.x += pdx; WM.cam.y += pdy; WM.panMoved += Math.hypot(pdx, pdy); clampCam(vp);
      }
    } else if (e.type === 'pointerup' || e.type === 'pointercancel') {
      var wasSingle = ptrList().length === 1, moved = WM.panMoved;
      delete WM.ptrs[e.pointerId]; if (ptrList().length < 2) WM.pinch = null;
      if (wasSingle && moved < 9) handleTap(e.clientX, e.clientY, api);
    }
  }

  function handleTap(px, py, api) {
    var ctx = WM.ctx;
    // HUD buttons first
    for (var i = 0; i < WM.btns.length; i++) {
      var b = WM.btns[i];
      if (px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h) {
        if (b.id === 'close') { api.close(); return; }
        if (b.id === 'rivals') { ctx.showBanner('Rival recon unlocks with the war update.', 1.6); return; }
        if (b.id === 'dive') { api.close({ dive: b.z }); return; }
        return;
      }
    }
    // district hit-test (GRID space)
    var Z = ctx.ZONES;
    for (var k in Z) {
      if (!Z.hasOwnProperty(k)) continue;
      var z = Z[k], t = tileXY(z.gx, z.gy), X = sx(t.x), Y = sy(t.y), S = TILE * WM.scale;
      if (px >= X && px <= X + S && py >= Y && py <= Y + S) { WM.sel = (WM.sel === z.id ? null : z.id); return; }
    }
    WM.sel = null;
  }

  function openMap(ctx) {
    WM.ctx = ctx; WM.sel = ctx.zoneId; WM.ptrs = {}; WM.pinch = null;
    var vp0 = { w: (typeof innerWidth !== 'undefined' ? innerWidth : 360), h: (typeof innerHeight !== 'undefined' ? innerHeight : 640) };
    fitToScreen(vp0);
    try {
      WM.ov = ctx.overlay.open({
        id: 'worldmap',
        onFrame: function (g, dt, vp) { drawFrame(g, dt, vp, ctx); },
        onPointer: function (e, api) { try { onPointer(e, api); } catch (_e) {} },
        onClose: function (res) {
          WM.ov = null;
          if (res && res.dive && global.enterZone) { // host's own dive_in transition (S3); state is IN_ZONE again here
            try { global.enterZone(res.dive, { x: ZW / 2, y: ZH / 2 }); } catch (_e) {}
          }
        }
      });
    } catch (_e) { WM.ov = null; }
  }

  /* ---- the floating HUD "zoom out to base" button (init-mounted) ---------- */
  function mountButton(ctx) {
    if (typeof document === 'undefined' || document.getElementById('ak-wm-btn')) return;
    var b = document.createElement('button');
    b.id = 'ak-wm-btn'; b.type = 'button';
    b.textContent = '🗺️';
    b.title = 'World Map -- view your base';
    // z-index 6 == same band as #phud; naturally hidden behind #interior(12)/overlay(40)/load(50)
    b.style.cssText = 'position:fixed;right:10px;top:184px;width:44px;height:44px;z-index:6;' +
      'border-radius:12px;border:1px solid rgba(201,168,76,.6);background:rgba(8,8,14,.82);' +
      'color:#e8c55a;font-size:20px;line-height:1;box-shadow:0 3px 12px rgba(0,0,0,.5);' +
      'display:flex;align-items:center;justify-content:center;padding:0;cursor:pointer;-webkit-tap-highlight-color:transparent;';
    b.addEventListener('click', function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      if (WM.ov) return;             // already open
      if (!WM.ctx) WM.ctx = ctx;
      openMap(WM.ctx);
    });
    document.body.appendChild(b);
  }

  /* ======================================================================== *
   * REGISTER
   * ======================================================================== */
  global.AK_SYSTEMS.register({
    id: 'worldmap',
    init: function (ctx) {
      WM.ctx = ctx;
      try { mountButton(ctx); } catch (_e) {}
      // warm the painted-art cache so the first open paints instantly
      try {
        var Z = ctx.ZONES;
        for (var k in Z) if (Z.hasOwnProperty(k)) {
          if (DBG[k]) img('assets/hub/' + DBG[k] + '_bg.png');
          var bs = Z[k].buildings || [];
          for (var i = 0; i < bs.length; i++) if (FAC[bs[i].id]) img('assets/hub/' + FAC[bs[i].id] + '.png');
        }
      } catch (_e2) {}
    },
    // OPTIONAL debug: outline live obstacles in the hub (set window.AK_WM_DEBUG=1).
    // OFF by default -- the painted maps ALREADY draw the fences/cars/trains, so
    // we don't double-draw them in normal play.
    onDrawWorld: function (ctx) {
      if (!global.AK_WM_DEBUG) return;
      var g = ctx.world.g, obs = obstaclesFor(ctx.activeZone); if (!obs.length) return;
      g.save(); g.strokeStyle = 'rgba(192,57,43,.8)'; g.lineWidth = 2;
      for (var i = 0; i < obs.length; i++) { var o = obs[i];
        if (o.type === 'circle') { g.beginPath(); g.arc(ctx.world.wx(o.x), ctx.world.wy(o.y), o.r, 0, 7); g.stroke(); }
        else { g.strokeRect(ctx.world.wx(o.x), ctx.world.wy(o.y), o.w, o.h); } }
      g.restore();
    }
  });

})(typeof window !== 'undefined' ? window : globalThis);
