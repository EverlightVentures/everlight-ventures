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
 * SPRINT 2 (this pass) -- two additive features in the SAME zoom-out view:
 *   (A) OTHER PLAYERS' BASES: tappable RAID pins ringed around the player's own
 *       base (HOME_TURF). Snapshots fetched LIVE from the ak-raid edge fn
 *       ({action:'targets'}) through the shared Supabase client (AKAccount.client
 *       -- the same handle social.js + raid.js use). Degrades to canon-named local
 *       pins when signed out / offline. Tapping a pin reuses raid.js's full WAR MAP
 *       (window.AKRaid.warMap) if loaded, else launches the raid battle directly
 *       via ctx.battle.launch({mode:'raid',...}). Loot stays server-authoritative.
 *   (B) BASE REARRANGE: a REARRANGE edit toggle lets the player DRAG one of their
 *       OWN buildings to a new spot inside its district. Drop snaps to a grid,
 *       validates with AK_COLLISION.validPlacement (door clear + footprint off
 *       obstacles) + a sibling-overlap guard, then persists the new x,y into the
 *       falsy-default p.baseLayout via AK_ECON.mutateProfile. The saved layout is
 *       APPLIED to the live ZONES building objects on init -- and index.html's
 *       (frozen) draw() reads those objects every frame -- so the HUB renders the
 *       rearranged base, doors/roads/radar all follow, with ZERO host edit. The
 *       only host hook returned is the ensureShape falsy-default (see the return).
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
    ],
// --- NEON_HEIGHTS (planters/holo-kiosks; WARD@560,560 door@560,608  ARCH@1140,560 door@1140,608) ---
    NEON_HEIGHTS: [
      { type:'circle', x:690,  y:320,  r:34,         kind:'planter' }, // holo-kiosk flanking N entrance (left of x775-925 lane)
      { type:'circle', x:1010, y:320,  r:34,         kind:'planter' }, // holo-kiosk flanking N entrance (right of lane)
      { type:'circle', x:300,  y:430,  r:40,         kind:'planter' }, // big planter NW (above W corridor y575-725)
      { type:'rect',   x:440,  y:716,  w:230, h:16,  kind:'fence'   }, // holo-barrier S of WARDROBE (door@560,608 clear, 108px below)
      { type:'circle', x:1400, y:430,  r:40,         kind:'planter' }, // big planter NE (above E corridor)
      { type:'rect',   x:1030, y:716,  w:230, h:16,  kind:'fence'   }, // holo-barrier S of ARCHIVE (door@1140,608 clear)
      { type:'circle', x:700,  y:840,  r:36,         kind:'planter' }, // planter framing S approach (left of x775-925)
      { type:'circle', x:1000, y:840,  r:36,         kind:'planter' }  // planter framing S approach (right of lane)
    ],
    // --- FACTORY_ROW (pipes/crates/forklifts; GEM@520,540 door@520,590  MINT@1180,540 door@1180,590  FORGE@850,960 door@850,1012) ---
    FACTORY_ROW: [
      { type:'rect',   x:140,  y:250,  w:18,  h:260, kind:'pipe'      }, // W coolant pipe, upper (ends y510, above W corridor)
      { type:'rect',   x:140,  y:770,  w:18,  h:300, kind:'pipe'      }, // W coolant pipe, lower (starts y770, below W corridor)
      { type:'rect',   x:640,  y:466,  w:72,  h:72,  kind:'container' }, // crate stack E of GEM MINE (footprint x440-600 clear)
      { type:'rect',   x:980,  y:466,  w:72,  h:72,  kind:'container' }, // crate stack W of GOLD MINT (footprint x1100-1260 clear)
      { type:'rect',   x:1300, y:280,  w:18,  h:240, kind:'pipe'      }, // E coolant pipe, upper
      { type:'rect',   x:636,  y:756,  w:96,  h:48,  kind:'car'       }, // parked forklift, center-left (W of FORGE footprint x765-935)
      { type:'rect',   x:984,  y:756,  w:96,  h:48,  kind:'car'       }, // parked forklift, center-right (E of FORGE footprint)
      { type:'rect',   x:1290, y:770,  w:210, h:18,  kind:'pipe'      }, // E low pipe run (below E corridor)
      { type:'circle', x:300,  y:1120, r:40,         kind:'rubble'    }, // slag pile SW corner
      { type:'circle', x:1400, y:1120, r:40,         kind:'rubble'    }  // slag pile SE corner
    ],
    // --- THE_STRIP (parked cars/club barriers/bollards; STREET@560,560 door@560,608  ARCADE@1140,560 door@1140,608) ---
    THE_STRIP: [
      { type:'rect',   x:372,  y:356,  w:96,  h:48,  kind:'car'   }, // parked car, NW curb
      { type:'rect',   x:500,  y:356,  w:96,  h:48,  kind:'car'   }, // parked car, NW curb (row)
      { type:'rect',   x:1100, y:356,  w:96,  h:48,  kind:'car'   }, // parked car, NE curb
      { type:'rect',   x:1228, y:356,  w:96,  h:48,  kind:'car'   }, // parked car, NE curb (row)
      { type:'rect',   x:556,  y:822,  w:188, h:16,  kind:'fence' }, // club stanchion line S-left (right edge 744 < S lane 775)
      { type:'rect',   x:956,  y:822,  w:188, h:16,  kind:'fence' }, // club stanchion line S-right (left edge 956 > S lane 925)
      { type:'circle', x:300,  y:440,  r:24,         kind:'fence' }, // bollard W-upper (above W corridor)
      { type:'circle', x:300,  y:860,  r:24,         kind:'fence' }, // bollard W-lower (below W corridor)
      { type:'circle', x:1400, y:440,  r:24,         kind:'fence' }, // bollard E-upper (above E corridor)
      { type:'circle', x:1400, y:860,  r:24,         kind:'fence' }  // bollard E-lower (below E corridor)
    ],
    // --- THE_DOCKS (shipping containers/crates/mooring posts; LAB@560,540 door@560,590  GEN@1140,540 door@1140,590) ---
    THE_DOCKS: [
      { type:'rect',   x:250,  y:300,  w:120, h:56,  kind:'container' }, // container stack NW (left of LAB footprint x480-640)
      { type:'rect',   x:250,  y:366,  w:120, h:56,  kind:'container' }, // container stack NW (stacked, ends y422 < W corridor)
      { type:'rect',   x:660,  y:460,  w:64,  h:64,  kind:'container' }, // crate pile E of LAB (door@560,590 clear)
      { type:'rect',   x:1330, y:300,  w:120, h:56,  kind:'container' }, // container stack NE (right of GEN footprint x1060-1220)
      { type:'rect',   x:980,  y:460,  w:64,  h:64,  kind:'container' }, // crate pile W of GEN (door@1140,590 clear)
      { type:'rect',   x:380,  y:900,  w:160, h:60,  kind:'container' }, // long container row SW (above S lane, W of x775)
      { type:'rect',   x:1160, y:900,  w:160, h:60,  kind:'container' }, // long container row SE (above S lane, E of x925)
      { type:'circle', x:1500, y:460,  r:20,         kind:'pipe'      }, // mooring post E-upper (above E corridor)
      { type:'circle', x:1500, y:840,  r:20,         kind:'pipe'      }, // mooring post E-lower (below E corridor)
      { type:'circle', x:640,  y:1140, r:20,         kind:'pipe'      }, // mooring post S (left of x775-925 lane)
      { type:'circle', x:1060, y:1140, r:20,         kind:'pipe'      }  // mooring post S (right of lane)
    ],
    // --- THE_OVERLOOK (LOCKED; for when unlocked -- POLICE CHECKPOINT theme; no buildings; active edges E->DOWNTOWN, S->THE_YARDS) ---
    THE_OVERLOOK: [
      { type:'rect',   x:520,  y:360,  w:240, h:16,  kind:'fence'     }, // police barricade N-left (right edge 760 < N lane 775)
      { type:'rect',   x:940,  y:360,  w:240, h:16,  kind:'fence'     }, // police barricade N-right (left edge 940 > N lane 925)
      { type:'rect',   x:1040, y:460,  w:64,  h:56,  kind:'container' }, // checkpoint booth (off plaza & lanes)
      { type:'circle', x:320,  y:430,  r:40,         kind:'rubble'    }, // rubble NW (above W corridor)
      { type:'circle', x:320,  y:860,  r:40,         kind:'rubble'    }, // rubble SW (below W corridor)
      { type:'rect',   x:660,  y:780,  w:96,  h:48,  kind:'car'       }  // police cruiser (right edge 756 < S lane 775)
    ],
    // --- THE_UNDERCITY (LOCKED; for when unlocked -- COLLAPSED BRIDGE theme; no buildings; active edges N->THE_YARDS, E->THE_STRIP) ---
    THE_UNDERCITY: [
      { type:'circle', x:560,  y:820,  r:56,         kind:'rubble'    }, // collapsed-bridge rubble (top edge 764 > plaza 730)
      { type:'circle', x:1100, y:820,  r:50,         kind:'rubble'    }, // bridge rubble chunk SE-center
      { type:'rect',   x:1300, y:300,  w:18,  h:260, kind:'pipe'      }, // fallen conduit, E-upper (ends y560 < E corridor)
      { type:'rect',   x:1280, y:820,  w:140, h:56,  kind:'container' }, // collapsed container SE
      { type:'circle', x:320,  y:430,  r:42,         kind:'rubble'    }, // concrete debris NW (above W corridor)
      { type:'rect',   x:520,  y:360,  w:200, h:18,  kind:'rubble'    }, // debris row left of N lane (right edge 720 < 775)
      { type:'rect',   x:980,  y:360,  w:200, h:18,  kind:'rubble'    }  // debris row right of N lane (left edge 980 > 925)
    ],
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

  /* SPRINT 2 (A): rival bases are now LIVE -- fetched from the ak-raid edge fn
   * ({action:'targets'}) via the shared Supabase client (see fetchRivals() in the
   * WORLD-MAP section below). Degrades to canon-named local pins when signed out. */

  /* If there's no registry we're not on the hub page -- AK_COLLISION is still
   * exported above (harmless), but skip all the DOM / overlay wiring. */
  if (!global.AK_SYSTEMS) return;

  /* ======================================================================== *
   * (A) THE WORLD-MAP / BASE VIEW  (ctx.overlay.open)
   * ======================================================================== */
  var WM = { ctx:null, ov:null, cam:{ x:0, y:0 }, scale:1, fitScale:1,
    sel:null, ptrs:{}, pinch:null, panMoved:0, btns:[],
    // SPRINT 2 -- (A) rival RAID pins  +  (B) base REARRANGE edit mode
    rivals:[], rivalsLoading:false, pins:[], editMode:false, drag:null };

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

  /* ======================================================================== *
   * SPRINT 2 (A) -- OTHER PLAYERS' BASES  (live ak-raid snapshots as RAID pins)
   * ======================================================================== */
  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  // canon crew names (verbatim from raid.js FACTIONS.gangs) so the signed-out
  // fallback still reuses REAL crews BY NAME -- never invented placeholders.
  function localRivals() {
    return [
      { id:'wm_loc_0', name:'The Boneyard Mob', cls:'Boneguard Crew',   accent:'#e8c55a', tier:1, local:true },
      { id:'wm_loc_1', name:'Zoomie Riot',      cls:'Zoomie Syndicate', accent:'#7CFFB0', tier:2, local:true },
      { id:'wm_loc_2', name:'Circuit Hounds',   cls:'K9 Circuitry',     accent:'#7fc8ff', tier:3, local:true }
    ];
  }
  function fetchRivals(ctx) {
    if (WM.rivalsLoading) return;
    var sb = sbc();
    if (!sb) { if (!WM.rivals.length) WM.rivals = localRivals(); return; }   // signed out / no client -> local pins
    WM.rivalsLoading = true;
    try {
      sb.functions.invoke('ak-raid', { body: { action: 'targets' } }).then(function (r) {
        WM.rivalsLoading = false;
        var d = r && r.data;
        if (d && d.ok && Array.isArray(d.bases) && d.bases.length) WM.rivals = d.bases.slice(0, 3);
        else if (!WM.rivals.length) WM.rivals = localRivals();
      }, function () { WM.rivalsLoading = false; if (!WM.rivals.length) WM.rivals = localRivals(); });
    } catch (_) { WM.rivalsLoading = false; if (!WM.rivals.length) WM.rivals = localRivals(); }
  }
  // resolve a base's marquee defender -> a fielded nemesis blob (engine AK-NEMESIS)
  function nemesisFor(ctx, base) {
    try {
      var nm = base && base.roster && base.roster[0];
      if (!nm) return null;
      var c = ctx.cards()[nm];
      var num = c && (c.cardNumber || c.id);
      if (!num) return null;
      return { card: String(num), name: nm, title: base.name, tier: base.tier || 1, taunt: 'Wrong block, mutt.' };
    } catch (_) { return null; }
  }
  // launch the raid battle straight (base layout = battlefield; mode:'raid').
  // Difficulty mirrors raid.js's tier->city/level mapping so it's consistent.
  function raidFrom(ctx, base) {
    var tier = (base && base.tier) || 1;
    ctx.battle.launch({
      mode: 'raid',
      city: (base && base.city != null) ? base.city : clamp(tier + 1, 0, 9),
      level: (base && base.level != null) ? base.level : clamp(2 + tier * 2, 1, 10),
      diffOffset: (base && base.diffOffset != null) ? base.diffOffset : (tier - 1),
      nemesis: nemesisFor(ctx, base),
      label: 'RAID -- ' + ((base && base.name) || 'Rival Crew')
    });
  }

  /* ======================================================================== *
   * SPRINT 2 (B) -- BASE REARRANGE  (drag a building to a new grid tile)
   *   placeOK() = AK_COLLISION.validPlacement (door clear + footprint off
   *   obstacles) + an in-bounds clamp + a sibling-overlap guard. commitMove()
   *   persists into falsy-default p.baseLayout; applyLayout() mirrors the saved
   *   layout onto the LIVE ZONES building objects (which the hub already draws).
   * ======================================================================== */
  var GSTEP = 100;                                   // grid snap (world units inside a 1700x1300 district)
  function snap(v) { return Math.round(v / GSTEP) * GSTEP; }
  function zoneObj(ctx, b) { return (b && b._zid && ctx.ZONES[b._zid]) || null; }
  // candidate footprint overlaps another building in the same zone? (don't stack)
  function overlapsSibling(zone, b, x, y) {
    var bs = zone.buildings || [], gap = 12;
    var ax0 = x - (b.w||0)/2 - gap, ay0 = y - (b.h||0)/2 - gap, ax1 = x + (b.w||0)/2 + gap, ay1 = y + (b.h||0)/2 + gap;
    for (var i = 0; i < bs.length; i++) { var o = bs[i]; if (o === b) continue;
      var ox0 = o.x - (o.w||0)/2, oy0 = o.y - (o.h||0)/2, ox1 = o.x + (o.w||0)/2, oy1 = o.y + (o.h||0)/2;
      if (ax0 < ox1 && ax1 > ox0 && ay0 < oy1 && ay1 > oy0) return true; }
    return false;
  }
  function placeOK(ctx, b, x, y) {
    var zone = zoneObj(ctx, b); if (!zone) return false;
    if (x < (b.w||0)/2 + 30 || x > ZW - (b.w||0)/2 - 30) return false;       // keep footprint inside the district
    if (y < (b.h||0)/2 + 24 || y > ZH - (b.h||0)/2 - 48) return false;       // leave room for the door (y + h/2)
    var cand = { id: b.id, x: x, y: y, w: b.w, h: b.h };
    if (!(global.AK_COLLISION && global.AK_COLLISION.validPlacement(zone, cand))) return false;  // door clear + off obstacles
    if (overlapsSibling(zone, b, x, y)) return false;                        // not on top of another building
    return true;
  }
  // apply the saved p.baseLayout onto the LIVE ZONES building objects (idempotent;
  // captures each building's authored home the first time so a reset can restore it).
  function applyLayout(ctx) {
    var p = profile(ctx), layout = (p && p.baseLayout) || {};
    var Z = ctx.ZONES;
    for (var k in Z) { if (!Z.hasOwnProperty(k)) continue; var bs = Z[k].buildings || [];
      for (var i = 0; i < bs.length; i++) { var b = bs[i];
        b._zid = Z[k].id;
        if (b._hx == null) { b._hx = b.x; b._hy = b.y; }                     // authored home, captured once
        var L = layout[b.id];
        if (L && typeof L.x === 'number' && typeof L.y === 'number') { b.x = L.x; b.y = L.y; }
        else { b.x = b._hx; b.y = b._hy; }
      }
    }
  }
  function commitMove(ctx, b) {
    if (!ctx.econ) return;
    try { ctx.econ.mutateProfile(function (p) {
      if (!p.baseLayout || typeof p.baseLayout !== 'object') p.baseLayout = {};
      p.baseLayout[b.id] = { x: Math.round(b.x), y: Math.round(b.y) };
    }); } catch (_) {}
  }
  function resetLayout(ctx) {
    if (ctx.econ) { try { ctx.econ.mutateProfile(function (p) { p.baseLayout = {}; }); } catch (_) {} }
    applyLayout(ctx);
  }
  // screen -> a building's home-district LOCAL world coords (0..ZW, 0..ZH)
  function screenToLocal(b, px, py) {
    var z = WM.ctx.ZONES[b._zid]; if (!z) return null;
    var t = tileXY(z.gx, z.gy), X = sx(t.x), Y = sy(t.y), S = TILE * WM.scale;
    if (S <= 0) return null;
    return { x: (px - X) / S * ZW, y: (py - Y) / S * ZH };
  }
  // hit-test a building chip in the zoom-out view (screen space). null = miss.
  function buildingAt(ctx, px, py) {
    var Z = ctx.ZONES;
    for (var k in Z) { if (!Z.hasOwnProperty(k)) continue; var z = Z[k]; if (z.locked) continue;
      var t = tileXY(z.gx, z.gy), X = sx(t.x), Y = sy(t.y), S = TILE * WM.scale;
      var bs = z.buildings || [];
      for (var i = 0; i < bs.length; i++) { var b = bs[i];
        var bw = (b.id === 'ARENA' ? 0.20 : 0.155) * S, hh = Math.max(bw / 2, 14);
        var bx = X + (b.x / ZW) * S, by = Y + (b.y / ZH) * S;
        if (px >= bx - hh && px <= bx + hh && py >= by - hh && py <= by + hh) { b._zid = z.id; return b; }
      }
    }
    return null;
  }

  // ---- (A) rival RAID pins ringed around the player's base (HOME_TURF tile) ----
  function drawRaidPins(g, ctx) {
    WM.pins = [];
    if (WM.editMode) return;                          // hidden while rearranging (no tap conflict)
    var rivals = WM.rivals; if (!rivals || !rivals.length) return;
    var home = ctx.ZONES.HOME_TURF; if (!home) return;
    var t = tileXY(home.gx, home.gy);
    var cxg = t.x + TILE / 2, cyg = t.y + TILE / 2;   // HOME_TURF tile center (GRID space)
    var ringG = TILE * 0.92, n = rivals.length;
    for (var i = 0; i < n; i++) {
      var base = rivals[i];
      var ang = -Math.PI / 2 + (i / n) * Math.PI * 2;  // start at top, spread evenly
      var px = sx(cxg + Math.cos(ang) * ringG), py = sy(cyg + Math.sin(ang) * ringG);
      var pr = clamp(15 * WM.scale, 11, 20), ac = base.accent || RED;
      // tether line back to the base
      g.save(); g.strokeStyle = 'rgba(192,57,43,.32)'; g.lineWidth = 1; g.setLineDash([4, 4]);
      g.beginPath(); g.moveTo(sx(cxg), sy(cyg)); g.lineTo(px, py); g.stroke(); g.restore();
      // skull chip
      g.save();
      g.beginPath(); g.arc(px, py, pr, 0, 7); g.fillStyle = 'rgba(10,8,10,.92)'; g.fill();
      g.lineWidth = 2; g.strokeStyle = ac; g.shadowColor = ac; g.shadowBlur = 8; g.stroke();
      g.restore();
      label(g, '☠', px, py + 0.5, clamp(pr, 10, 18), ac, '900');
      // tier stars + crew-name tag
      var st = ''; for (var s = 0; s < (base.tier || 1); s++) st += '★';
      label(g, st, px, py - pr - 6 * WM.scale, clamp(8 * WM.scale, 7, 11), GOLD, '800');
      var nm = String(base.name || 'Rival Crew');
      g.save(); g.font = '800 ' + clamp(9 * WM.scale, 8, 11) + 'px Inter,system-ui'; g.textAlign = 'center';
      var tw = g.measureText(nm).width + 10;
      g.fillStyle = 'rgba(8,8,12,.82)'; rr(g, px - tw / 2, py + pr + 3 * WM.scale, tw, 14 * WM.scale, 4); g.fill();
      g.restore();
      label(g, nm, px, py + pr + 10 * WM.scale, clamp(9 * WM.scale, 8, 11), '#f3d9a8', '800');
      WM.pins.push({ x: px, y: py, r: pr + 8, base: base });
    }
  }

  // ---- (B) live valid/invalid feedback for the building being dragged ----------
  function drawDragFx(g, ctx) {
    if (!WM.drag) return;
    var b = WM.drag.b, z = ctx.ZONES[b._zid]; if (!z) return;
    var t = tileXY(z.gx, z.gy), X = sx(t.x), Y = sy(t.y), S = TILE * WM.scale;
    var nx = snap(b.x), ny = snap(b.y), ok = placeOK(ctx, b, nx, ny);
    var bw = (b.id === 'ARENA' ? 0.20 : 0.155) * S;
    // snapped ghost target
    var gx = X + (nx / ZW) * S, gy = Y + (ny / ZH) * S, col = ok ? '#7CFFB0' : '#ff5a4d';
    g.save(); g.globalAlpha = .55; g.fillStyle = ok ? 'rgba(124,255,176,.22)' : 'rgba(255,90,77,.20)';
    rr(g, gx - bw / 2, gy - bw / 2, bw, bw, 6 * WM.scale); g.fill(); g.restore();
    // dashed ring on the dragged chip
    var bx = X + (b.x / ZW) * S, by = Y + (b.y / ZH) * S;
    g.save(); rr(g, bx - bw / 2 - 4, by - bw / 2 - 4, bw + 8, bw + 8, 8 * WM.scale);
    g.lineWidth = 3; g.setLineDash([7, 5]); g.strokeStyle = col; g.shadowColor = col; g.shadowBlur = 10; g.stroke();
    g.restore();
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
    label(g, WM.editMode ? '🛠️  REBUILD YOUR BASE' : '🗺️  YOUR TERRITORY', 14, 25, 15, GOLD, '900', 'left');
    label(g, WM.editMode ? 'drag a building to a new spot · snaps to grid'
      : (liveTerritoryCount(ctx) + ' districts held'), 14, 41, 11, DIM, '700', 'left');
    // close (x)
    var cb = { id:'close', x: vp.w - 50, y: 8, w: 38, h: 34 };
    g.fillStyle = 'rgba(255,255,255,.06)'; rr(g, cb.x, cb.y, cb.w, cb.h, 9); g.fill();
    label(g, '×', cb.x + cb.w / 2, cb.y + cb.h / 2, 24, '#ccc', '700'); WM.btns.push(cb);
    // (B) REARRANGE / LOCK IN toggle (top bar, left of close)
    var eb = { id:'edit', x: vp.w - 50 - 12 - 116, y: 8, w: 116, h: 34 };
    g.save(); rr(g, eb.x, eb.y, eb.w, eb.h, 9);
    if (WM.editMode) { var grd0 = g.createLinearGradient(0, eb.y, 0, eb.y + eb.h); grd0.addColorStop(0, GOLD); grd0.addColorStop(1, GOLD_D); g.fillStyle = grd0; g.fill(); }
    else { g.fillStyle = 'rgba(201,168,76,.10)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,.5)'; g.lineWidth = 1; g.stroke(); }
    g.restore();
    label(g, WM.editMode ? '✓ LOCK IN' : '✛ REARRANGE', eb.x + eb.w / 2, eb.y + eb.h / 2, 12, WM.editMode ? '#15110a' : GOLD, '900'); WM.btns.push(eb);

    // bottom action bar
    var barY = vp.h - 78;
    g.fillStyle = 'rgba(8,8,12,.9)'; g.fillRect(0, barY, vp.w, 78);
    g.strokeStyle = 'rgba(201,168,76,.25)'; g.lineWidth = 1; g.beginPath(); g.moveTo(0, barY); g.lineTo(vp.w, barY); g.stroke();

    if (WM.editMode) {                                  // (B) edit-mode bar
      label(g, 'EDIT MODE', 16, barY + 22, 14, GOLD, '800', 'left');
      label(g, 'Buildings stay in their district. Green = OK, red = blocked.', 16, barY + 44, 11, DIM, '700', 'left');
      var rsb = { id:'reset', x: vp.w - 150, y: barY + 18, w: 134, h: 42 };
      g.save(); rr(g, rsb.x, rsb.y, rsb.w, rsb.h, 11); g.fillStyle = 'rgba(255,255,255,.05)';
      g.fill(); g.strokeStyle = 'rgba(201,168,76,.4)'; g.lineWidth = 1; g.stroke(); g.restore();
      label(g, '↺ RESET LAYOUT', rsb.x + rsb.w / 2, barY + 39, 11, GOLD, '800'); WM.btns.push(rsb);
      return;
    }

    var z = WM.sel ? ctx.ZONES[WM.sel] : null;
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
      label(g, 'Tap a district to inspect · drag to pan, pinch to zoom', 16, barY + 26, 12, DIM, '700', 'left');
      // (A) SCOUT RIVALS -> raid.js war map if loaded, else a heads-up
      var live = !!(global.AKRaid && global.AKRaid.warMap);
      var rb = { id:'rivals', x: vp.w - 150, y: barY + 18, w: 134, h: 42 };
      g.save(); rr(g, rb.x, rb.y, rb.w, rb.h, 11);
      if (live) { g.fillStyle = 'rgba(192,57,43,.18)'; g.fill(); g.strokeStyle = 'rgba(192,57,43,.6)'; g.lineWidth = 1.2; g.stroke(); }
      else { g.fillStyle = 'rgba(255,255,255,.05)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,.3)'; g.lineWidth = 1; g.stroke(); }
      g.restore();
      label(g, '☠ SCOUT RIVALS', rb.x + rb.w / 2, barY + 39, 11, live ? '#f3a0a0' : GOLD, '800'); WM.btns.push(rb);
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
    try { drawRaidPins(g, ctx); } catch (_e1) {}      // (A) rival pins around HOME_TURF
    try { drawDragFx(g, ctx); } catch (_e2) {}        // (B) drag valid/invalid feedback
    drawHud(g, vp, ctx);
  }

  // ---- pointer: pan (1 finger) / pinch (2) / tap (select + buttons) --------
  function ptrList() { var a = []; for (var k in WM.ptrs) if (WM.ptrs.hasOwnProperty(k)) a.push(WM.ptrs[k]); return a; }
  function onPointer(e, api) {
    var vp = api.vp;
    if (e.type === 'pointerdown') {
      if (WM.drag) return;                              // (B) already dragging -> ignore extra fingers
      // (B) rearrange: grab a building (instead of panning) when edit mode is on
      if (WM.editMode && ptrList().length === 0) {
        var hb = buildingAt(WM.ctx, e.clientX, e.clientY);
        if (hb) { WM.drag = { b: hb, id: e.pointerId, x0: hb.x, y0: hb.y }; WM.panMoved = 0; return; }
      }
      WM.ptrs[e.pointerId] = { x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY };
      WM.panMoved = 0;
      var pl = ptrList();
      if (pl.length === 2) WM.pinch = { d: Math.hypot(pl[0].x - pl[1].x, pl[0].y - pl[1].y), s: WM.scale,
        mx: (pl[0].x + pl[1].x) / 2, my: (pl[0].y + pl[1].y) / 2,
        wx: ((pl[0].x + pl[1].x) / 2 - WM.cam.x) / WM.scale, wy: ((pl[0].y + pl[1].y) / 2 - WM.cam.y) / WM.scale };
    } else if (e.type === 'pointermove') {
      if (WM.drag && e.pointerId === WM.drag.id) {      // (B) drag the building under the finger
        var loc = screenToLocal(WM.drag.b, e.clientX, e.clientY);
        if (loc) { var bb = WM.drag.b;
          bb.x = clamp(loc.x, (bb.w||0)/2 + 20, ZW - (bb.w||0)/2 - 20);
          bb.y = clamp(loc.y, (bb.h||0)/2 + 16, ZH - (bb.h||0)/2 - 40); }
        return;
      }
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
      if (WM.drag && e.pointerId === WM.drag.id) {       // (B) drop: snap + validate + persist (or revert)
        var b = WM.drag.b, nx = snap(b.x), ny = snap(b.y);
        if (placeOK(WM.ctx, b, nx, ny)) { b.x = nx; b.y = ny; commitMove(WM.ctx, b); WM.ctx.showBanner((b.label || 'Building') + ' moved.', 1.0); }
        else { b.x = WM.drag.x0; b.y = WM.drag.y0; WM.ctx.showBanner("Can't build there -- blocked.", 1.3); }
        WM.drag = null; return;
      }
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
        if (b.id === 'edit') { WM.editMode = !WM.editMode; WM.drag = null;
          ctx.showBanner(WM.editMode ? 'Rearrange mode -- drag your buildings.' : 'Base locked in.', WM.editMode ? 1.6 : 1.1); return; }
        if (b.id === 'reset') { resetLayout(ctx); ctx.showBanner('Base layout reset to default.', 1.4); return; }
        if (b.id === 'rivals') {
          if (global.AKRaid && global.AKRaid.warMap) api.close({ warmap: true });
          else ctx.showBanner('Rival recon comes online with the war update.', 1.8);
          return;
        }
        if (b.id === 'dive') { api.close({ dive: b.z }); return; }
        return;
      }
    }
    // (A) RAID pins (not while rearranging)
    if (!WM.editMode) {
      for (var pi = 0; pi < WM.pins.length; pi++) {
        var pn = WM.pins[pi];
        if (Math.hypot(px - pn.x, py - pn.y) <= pn.r) {
          if (global.AKRaid && global.AKRaid.warMap) api.close({ warmap: true });  // reuse raid.js war map
          else api.close({ raid: pn.base });                                       // else launch raid straight
          return;
        }
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
    WM.editMode = false; WM.drag = null; WM.pins = [];
    try { applyLayout(ctx); } catch (_e0) {}    // mirror saved p.baseLayout onto the live building objects
    fetchRivals(ctx);                           // (A) kick off the ak-raid targets fetch (degrades to local)
    var vp0 = { w: (typeof innerWidth !== 'undefined' ? innerWidth : 360), h: (typeof innerHeight !== 'undefined' ? innerHeight : 640) };
    fitToScreen(vp0);
    try {
      WM.ov = ctx.overlay.open({
        id: 'worldmap',
        onFrame: function (g, dt, vp) { drawFrame(g, dt, vp, ctx); },
        onPointer: function (e, api) { try { onPointer(e, api); } catch (_e) {} },
        onClose: function (res) {
          WM.ov = null;
          if (WM.drag) { WM.drag.b.x = WM.drag.x0; WM.drag.b.y = WM.drag.y0; WM.drag = null; } // revert an in-flight drag
          if (!res) return;
          if (res.dive && global.enterZone) { // host's own dive_in transition (S3); state is IN_ZONE again here
            try { global.enterZone(res.dive, { x: ZW / 2, y: ZH / 2 }); } catch (_e) {} return;
          }
          if (res.warmap) { try { if (global.AKRaid && global.AKRaid.warMap) global.AKRaid.warMap(); } catch (_e) {} return; }
          if (res.raid)   { try { raidFrom(ctx, res.raid); } catch (_e) {} return; }
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
      // (B) mirror the saved base layout onto the live ZONES building objects so the
      // hub (index.html's frozen draw()) renders the rearranged base from frame 1.
      try { applyLayout(ctx); } catch (_e0) {}
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
