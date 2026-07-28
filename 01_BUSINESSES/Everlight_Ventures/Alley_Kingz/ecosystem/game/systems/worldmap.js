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
    THE_DOCKS:'the_docks' , THE_OVERLOOK:'the_overlook', THE_UNDERCITY:'the_undercity' };
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

  /* ---- WAR-MAP ART LAYER (restyle 2026-07-01; presentation ONLY) ----------
   * Real painted art on every surface: district bgs as territory panels
   * (cover-fit + darkened), faction CRESTS as pins, trophy + currency chip
   * icons, Cinzel gold headers, a cached grain texture. Every image goes
   * through img() (loaded ONCE, cached forever); cover-fit is scalar math;
   * the grain pattern is built once on a tiny offscreen canvas -- zero
   * per-frame allocation beyond the gradients the file already made. */
  var FONT_H = 'Cinzel, "Playfair Display", Georgia, serif'; // brand header face (host loads Cinzel)
  function labelH(g, s, x, y, size, col, weight, align) {
    g.fillStyle = col || TXT; g.textAlign = align || 'center'; g.textBaseline = 'middle';
    g.font = (weight || '800') + ' ' + size + 'px ' + FONT_H;
    g.fillText(s, x, y);
  }
  // cover-fit drawImage (CSS background-size:cover) -- crops source, no squash
  function drawCover(g, im, x, y, w, h) {
    if (!ready(im) || w <= 0 || h <= 0) return false;
    var iw = im.naturalWidth, ih = im.naturalHeight, s = Math.max(w / iw, h / ih);
    var sw = w / s, sh = h / s;
    g.drawImage(im, (iw - sw) / 2, (ih - sh) / 2, sw, sh, x, y, w, h);
    return true;
  }
  // faction crest art (assets/ui/Crest_*.jpg) matched on cls/faction substring
  function crestPath(s) {
    s = String(s || '').toLowerCase();
    if (s.indexOf('zoomie') >= 0) return 'assets/ui/Crest_Zoomie.jpg';
    if (s.indexOf('k9') >= 0 || s.indexOf('circuit') >= 0) return 'assets/ui/Crest_K9.jpg';
    if (s.indexOf('leash') >= 0) return 'assets/ui/Crest_Leashbreak.jpg';
    return 'assets/ui/Crest_Boneguard.jpg';            // canon default crew
  }
  // circular crest badge: clipped crest art + accent ring (fallback dark disc)
  function drawCrest(g, x, y, r, key, accent, glow) {
    var im = img(crestPath(key));
    g.save();
    g.beginPath(); g.arc(x, y, r, 0, 7); g.closePath(); g.clip();
    if (!drawCover(g, im, x - r, y - r, r * 2, r * 2)) { g.fillStyle = '#161320'; g.fillRect(x - r, y - r, r * 2, r * 2); }
    g.restore();
    g.save();
    g.beginPath(); g.arc(x, y, r, 0, 7);
    g.lineWidth = Math.max(1.5, r * 0.14); g.strokeStyle = accent || GOLD_D;
    if (glow) { g.shadowColor = accent || GOLD; g.shadowBlur = 10; }
    g.stroke(); g.restore();
  }
  // the player's own crew crest (profile-driven when present; canon fallback)
  function playerCrestKey(ctx) {
    try { var p = profile(ctx); var k = p && (p.crewClass || p.crew || p.faction || (p.raid && p.raid.cls)); if (k) return String(k); } catch (_) {}
    return 'boneguard';
  }
  // trophies chip: trophy.png art + count on a dark plate
  function drawTrophyChip(g, x, y, n, fs) {
    fs = Math.max(8, fs || 10);
    g.save(); g.font = '800 ' + fs + 'px Inter, system-ui, sans-serif';
    var txt = String(n | 0), tw = g.measureText(txt).width, ih = fs + 5, w = ih + tw + 14;
    rr(g, x - w / 2, y - ih / 2 - 2, w, ih + 4, 3); g.fillStyle = 'rgba(8,8,12,.85)'; g.fill();
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.45)'; g.stroke();
    g.restore();
    var tIm = img('assets/hub/trophy.png');
    if (ready(tIm)) g.drawImage(tIm, x - w / 2 + 3, y - ih / 2, ih, ih);
    label(g, txt, x - w / 2 + ih + 7, y, fs, '#f3d9a8', '800', 'left');
  }
  // loot chip: currency icon (assets/icons/chip_*.png) + amount; returns next x
  var LOOT_ICON = { gold: 'chip_gold', scrap: 'chip_scrap', wood: 'chip_wood', stone: 'chip_stone', metal: 'chip_metal', bones: 'chip_bones' };
  function lootChip(g, x, y, kind, amt) {
    if (!amt) return x;
    var im = img('assets/icons/' + (LOOT_ICON[kind] || 'chip_gold') + '.png'), s = 15;
    if (ready(im)) g.drawImage(im, x, y - s / 2, s, s);
    else { label(g, kind.charAt(0).toUpperCase(), x + s / 2, y, 10, DIM, '800'); }
    g.save(); g.font = '800 11px Inter, system-ui, sans-serif';
    var w = g.measureText(String(amt)).width; g.restore();
    label(g, String(amt), x + s + 4, y, 11, '#f3d9a8', '800', 'left');
    return x + s + 4 + w + 14;
  }
  // film-grain texture: built ONCE on a 96x96 offscreen canvas, tiled as a
  // cached pattern (re-created only if the target context changes)
  var _grain = { cv: null, pat: null, g: null };
  function grainPat(g) {
    if (typeof document === 'undefined') return null;
    if (!_grain.cv) {
      var cv = document.createElement('canvas'); cv.width = 96; cv.height = 96;
      var gg = cv.getContext('2d'); if (!gg) return null;
      var rnd = rng32(0xA11E7);                        // deterministic speckle
      for (var i = 0; i < 900; i++) {
        var a = 0.02 + rnd() * 0.05;
        gg.fillStyle = rnd() > 0.5 ? 'rgba(255,255,255,' + a.toFixed(3) + ')' : 'rgba(0,0,0,' + (a * 1.4).toFixed(3) + ')';
        gg.fillRect((rnd() * 96) | 0, (rnd() * 96) | 0, 1, 1);
      }
      _grain.cv = cv;
    }
    if (_grain.g !== g) { try { _grain.pat = g.createPattern(_grain.cv, 'repeat'); _grain.g = g; } catch (_) { return null; } }
    return _grain.pat;
  }

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
    // anti-stick safety: if still embedded but the pre-move spot was clear, SLIDE then revert.
    // AK-WEDGE 2026-07-17: the old code reverted BOTH axes together, so holding into a rect
    // CORNER re-blocked every frame and froze the player permanently -- the "invisible wall"
    // the operator hit, with open ground right alongside. Now we keep whichever single axis is
    // clear (classic wall-slide), and only hard-revert when genuinely boxed in on both.
    if (px != null && py != null && blocks(me.x, me.y, r, obs) && !blocks(px, py, r, obs)) {
      if (!blocks(me.x, py, r, obs)) { me.y = py; }          // X move was fine -> slide horizontally
      else if (!blocks(px, me.y, r, obs)) { me.x = px; }     // Y move was fine -> slide vertically
      else { me.x = px; me.y = py; }                          // truly cornered -> revert
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

  /* ======================================================================== *
   * (C) HARVEST LAYER  -- window.AK_HARVEST      (AK-HARVEST 2026-07-18)
   *   The operator's loop, verbatim: "when you gather those materials, that's
   *   how the builder can upgrade, because now we have the supplies -- they grew
   *   on our property, we cut them down -- and now we can upgrade our wooden
   *   fence to a stone fence, and our stone fence to an iron fence."
   *
   *   So the labeled loot already sitting on the ground gets WORKED. Two feeds:
   *     GROUND  -- hand-placed harvest-only spots per district (trees in your own
   *                yard, rock, junk). NON-SOLID: they are NOT obstacles, so the
   *                collision model and the AK-WEDGE slide fix are untouched.
   *     SALVAGE -- the painted obstacles themselves (rubble/pipe/rail/car/crate
   *                /planter/fence) read THROUGH obstaclesFor(). Read-only. We
   *                never mutate, reorder, or filter that array.
   *
   *   MATERIAL KEYS are the profile's, not invented: p.wood / p.stone / p.metal
   *   are flat counters (economy.js MATERIALS) and p.scrap is rarity-keyed, so a
   *   SCRAP node banks through AK_ECON.addScrap('Common', n). "Iron" is the
   *   player-facing word for the metal tier; the KEY stays 'metal' so buildmode
   *   STRUCT.METAL and AK_ECON.bankMaterial both eat it with no translation.
   *
   *   Yields + regrow timers MIRROR worldverbs.js NODE_TYPES on purpose (wood
   *   8 / 8min, stone 8 / 12min, metal 5 / 45min, scrap 12 / 10min) so the two
   *   harvest surfaces never disagree about what a tree is worth. Depletion
   *   persists in the SAME p.nodes store worldverbs uses, under a 'wm:' key
   *   prefix so the two namespaces can never collide. No econ (headless) -> an
   *   in-memory cooldown map, same shape, so tests still exercise respawn.
   * ======================================================================== */

  var HARVEST_RANGE = 80;              // walk-up radius for the harvest prompt (world units)
  var HMIN = 60000;                    // one minute in ms (regrow timers below)

  // THE REGISTRY: node type -> what it drops. mat = the profile key it banks to.
  var HARVEST_NODES = {
    TREE:  { mat:'wood',  label:'WOOD',  verb:'CHOP',  amount:8,  respawn:8  * HMIN, tool:'axe',     glyph:'\u{1FAB5}' },
    ROCK:  { mat:'stone', label:'STONE', verb:'BREAK', amount:8,  respawn:12 * HMIN, tool:'pickaxe', glyph:'\u{1FAA8}' },
    METAL: { mat:'metal', label:'IRON',  verb:'STRIP', amount:5,  respawn:45 * HMIN, tool:'crowbar', glyph:'\u{1F529}' },
    SCRAP: { mat:'scrap', label:'SCRAP', verb:'PULL',  amount:12, respawn:10 * HMIN, tool:'crowbar', glyph:'⚙️', rar:'Common' }
  };

  // painted-obstacle 'kind' -> which node it salvages as. Anything unlisted is
  // scenery only and yields nothing (no silent free loot).
  var KIND_NODE = {
    planter:'TREE', rubble:'ROCK', train:'METAL', pipe:'METAL',
    car:'SCRAP', container:'SCRAP', fence:'SCRAP'
  };

  // GROUND spots: harvest-only, no collision body. Placed clear of every door,
  // the centre plaza, the 4 edge corridors (x 775-925 / y 575-725) and every
  // BUILTIN obstacle above. HOME_TURF carries the stand of trees on purpose --
  // that is the operator's "they grew on our property" yard.
  var GROUND = {
    HOME_TURF: [
      { type:'TREE',  x:400,  y:300  }, { type:'TREE',  x:300,  y:800  },
      { type:'TREE',  x:620,  y:1040 }, { type:'TREE',  x:1340, y:960  },
      { type:'ROCK',  x:240,  y:1020 }, { type:'SCRAP', x:1180, y:1040 }
    ],
    DOWNTOWN: [
      { type:'TREE',  x:420,  y:400  }, { type:'ROCK',  x:1420, y:480  },
      { type:'SCRAP', x:640,  y:980  }
    ],
    NEON_HEIGHTS: [
      { type:'TREE',  x:450,  y:880  }, { type:'TREE',  x:1250, y:880  },
      { type:'ROCK',  x:620,  y:220  }
    ],
    THE_YARDS: [
      { type:'SCRAP', x:420,  y:400  }, { type:'METAL', x:1380, y:1120 },
      { type:'ROCK',  x:700,  y:1120 }
    ],
    FACTORY_ROW: [
      { type:'METAL', x:460,  y:300  }, { type:'SCRAP', x:1160, y:300  },
      { type:'ROCK',  x:620,  y:1120 }
    ],
    THE_STRIP: [
      { type:'SCRAP', x:680,  y:480  }, { type:'SCRAP', x:1020, y:480  },
      { type:'TREE',  x:400,  y:1080 }
    ],
    THE_DOCKS: [
      { type:'METAL', x:700,  y:280  }, { type:'SCRAP', x:1000, y:1040 },
      { type:'ROCK',  x:460,  y:1120 }
    ],
    THE_OVERLOOK:  [ { type:'ROCK', x:1200, y:1080 }, { type:'SCRAP', x:1000, y:240 } ],
    THE_UNDERCITY: [ { type:'METAL', x:420, y:1120 }, { type:'ROCK',  x:1450, y:1120 } ]
  };

  /* ---- state store (persist through econ; memory fallback headless) ------- */
  var _hMem = {};                                    // {zid:{key:{r,d}}} when AK_ECON is absent
  function hEcon() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function hNow() { return Date.now(); }
  // a node's depletion entry {r:readyAt, d:durMs} or null when never worked
  function hState(zid, key) {
    var E = hEcon();
    if (E && typeof E.loadProfile === 'function') {
      try { var p = E.loadProfile(), z = p && p.nodes && p.nodes[zid]; if (z) return z[key] || null; } catch (_) {}
    }
    return (_hMem[zid] && _hMem[zid][key]) || null;
  }
  // stamp a harvested node with its regrow clock (ONE atomic profile write)
  function hMark(zid, key, durMs) {
    var e = { r: hNow() + durMs, d: durMs }, E = hEcon();
    if (E && typeof E.mutateProfile === 'function') {
      try {
        E.mutateProfile(function (p) {
          if (!p.nodes || typeof p.nodes !== 'object') p.nodes = {};
          if (!p.nodes[zid]) p.nodes[zid] = {};
          p.nodes[zid][key] = e;
        });
        return e;
      } catch (_) {}
    }
    if (!_hMem[zid]) _hMem[zid] = {};
    _hMem[zid][key] = e;
    return e;
  }

  /* ---- node build-out ----------------------------------------------------- */
  // accept a zone OBJECT or a bare zone id string (nodesFor takes either)
  function zoneRef(z) {
    if (!z) return null;
    if (typeof z !== 'string') return z;
    try { var C = global.AKWorldMap && global.AKWorldMap._state; if (C && C.ctx && C.ctx.ZONES && C.ctx.ZONES[z]) return C.ctx.ZONES[z]; } catch (_) {}
    return { id: z };
  }
  // bigger painted junk yields more. Area-scaled off the wall-tile footprint,
  // clamped so a bollard is still worth working and a freight train is not a jackpot.
  function bulkOf(o) {
    var a = (o.type === 'circle') ? (Math.PI * (o.r || 1) * (o.r || 1)) : ((o.w || 1) * (o.h || 1));
    return clamp(Math.sqrt(a / (84 * 48)), 0.7, 1.6);
  }
  function mkNode(zid, type, x, y, bulk, src) {
    var def = HARVEST_NODES[type]; if (!def) return null;
    var key = 'wm:' + zid + ':' + type + ':' + Math.round(x) + ',' + Math.round(y);
    var e = hState(zid, key), now = hNow(), ready = !e || now >= e.r;
    return {
      key: key, zid: zid, type: type, source: src,
      mat: def.mat, material: def.mat, label: def.label, verb: def.verb,
      glyph: def.glyph, tool: def.tool, rar: def.rar || null,
      x: x, y: y, r: 26,
      amount: Math.max(1, Math.round(def.amount * (bulk || 1))),
      respawn: def.respawn,
      ripe: ready, readyAt: e ? e.r : 0,
      remainMs: ready ? 0 : Math.max(0, e.r - now)
    };
  }
  // EVERY workable node in a district: hand-placed ground spots first, then the
  // painted obstacles read through obstaclesFor() (never mutated).
  function nodesFor(zone) {
    var z = zoneRef(zone); if (!z) return [];
    var zid = z.id || String(zone), out = [], i, n;
    var G = GROUND[zid] || [];
    for (i = 0; i < G.length; i++) { n = mkNode(zid, G[i].type, G[i].x, G[i].y, 1, 'ground'); if (n) out.push(n); }
    var obs = obstaclesFor(z) || [];
    for (i = 0; i < obs.length; i++) {
      var o = obs[i], t = KIND_NODE[o.kind];
      if (!t) continue;
      var cx = (o.type === 'circle') ? o.x : (o.x + (o.w || 0) / 2);
      var cy = (o.type === 'circle') ? o.y : (o.y + (o.h || 0) / 2);
      n = mkNode(zid, t, cx, cy, bulkOf(o), 'salvage'); if (n) out.push(n);
    }
    return out;
  }
  function nodeByKeyH(zone, key) {
    var ns = nodesFor(zone);
    for (var i = 0; i < ns.length; i++) if (ns[i].key === key) return ns[i];
    return null;
  }
  // nearest RIPE node inside HARVEST_RANGE of (x,y) -- the walk-up prompt seam
  function nodeNear(zone, x, y, range) {
    var ns = nodesFor(zone), rng = (range == null ? HARVEST_RANGE : range), best = null, bd = 1e9;
    for (var i = 0; i < ns.length; i++) {
      var n = ns[i]; if (!n.ripe) continue;
      var d = Math.hypot(x - n.x, y - n.y);
      if (d <= rng + n.r && d < bd) { bd = d; best = n; }
    }
    return best;
  }

  /* ---- THE HARVEST: gate -> bank -> start the regrow clock ---------------- */
  // harvest(node) | harvest(zoneId, key). Returns {ok,material,amount,...}.
  // A worked node goes DOWN and regrows on its own timer, so nothing gets
  // farmed flat. Materials route through AK_ECON.bankMaterial (capped grant,
  // overflow auto-sells to gold) or addScrap for the rarity-keyed scrap pocket.
  function harvest(a, b) {
    var node = a, zid = null;
    if (typeof a === 'string') { zid = a; node = nodeByKeyH(a, b); }
    else if (node && node.key) { zid = node.zid; if (node.ripe == null) node = nodeByKeyH(zid, node.key); }
    if (!node) return { ok: false, error: 'NO_NODE', material: null, amount: 0 };
    if (!node.ripe) return { ok: false, error: 'NOT_READY', material: node.mat, amount: 0, remainMs: node.remainMs, readyAt: node.readyAt };
    var def = HARVEST_NODES[node.type] || HARVEST_NODES.SCRAP;
    var amt = Math.max(1, node.amount | 0);
    var out = { ok: true, material: def.mat, amount: amt, label: def.label, key: node.key,
      zid: zid, banked: amt, overflow: 0, gold: 0, respawnMs: node.respawn, readyAt: 0 };
    var E = hEcon();
    if (def.mat === 'scrap') {
      out.rarity = def.rar || 'Common';
      if (E && typeof E.addScrap === 'function') { try { E.addScrap(out.rarity, amt); } catch (_) {} }
    } else if (E && typeof E.bankMaterial === 'function') {
      var r = null; try { r = E.bankMaterial(def.mat, amt); } catch (_) {}
      if (r) { out.banked = r.added | 0; out.overflow = r.overflow | 0; out.gold = r.gold | 0; }
    }
    var e = hMark(zid, node.key, node.respawn);
    out.readyAt = e.r;
    return out;
  }
  // regrow read-outs (no side effects) -- for HUD timers / test harnesses
  function nodeReady(zone, key) { var n = nodeByKeyH(zone, key); return !n || n.ripe; }
  function respawnMs(type) { var d = HARVEST_NODES[type]; return d ? d.respawn : 0; }
  function clearNodes(zid) {                                   // test seam / debug regrow-all
    var E = hEcon();
    if (E && typeof E.mutateProfile === 'function') {
      try { E.mutateProfile(function (p) { if (p.nodes) { if (zid) delete p.nodes[zid]; else p.nodes = {}; } }); } catch (_) {}
    }
    if (zid) delete _hMem[zid]; else _hMem = {};
  }

  /* ---- THE FENCE LADDER: wood -> stone -> iron --------------------------- *
   * The payoff end of the loop. Keys + costs + HP are the SAME ones buildmode
   * STRUCT already ships (WALL/STONE/METAL), so the build and defense layers
   * consume this ladder without a translation table and without a second price
   * list drifting out of sync. Exported for them to read; the DEBIT stays with
   * whoever places the structure (call payFenceUpgrade OR your own STRUCT
   * debit, never both, or you charge the player twice).
   * ----------------------------------------------------------------------- */
  var FENCE_TIERS = [
    { tier:1, key:'WALL',  struct:'WALL',  name:'Wood Fence',  material:'wood',  cost:{ wood:10 },           hp:200,  next:'STONE',
      blurb:'Splintered pallet wood. Keeps stray mutts out. Keeps nobody else out.' },
    { tier:2, key:'STONE', struct:'STONE', name:'Stone Fence', material:'stone', cost:{ stone:12 },          hp:500,  next:'METAL',
      blurb:'Cinder block and mortar. Now a crew has to WORK to get on your lot.' },
    { tier:3, key:'METAL', struct:'METAL', name:'Iron Fence',  material:'metal', cost:{ metal:10, stone:4 }, hp:1200, next:null,
      blurb:'Welded iron on a stone footing. They bring tools or they turn around.' }
  ];
  function fenceTier(key) {
    for (var i = 0; i < FENCE_TIERS.length; i++) if (FENCE_TIERS[i].key === key || FENCE_TIERS[i].tier === key) return FENCE_TIERS[i];
    return null;
  }
  function nextFence(key) { var t = fenceTier(key); return (t && t.next) ? fenceTier(t.next) : null; }
  // what the NEXT rung costs from where you stand. fromKey null/absent = the
  // first rung (you have no fence yet). Returns null once you are at iron.
  function fenceUpgrade(fromKey) {
    var to = fromKey ? nextFence(fromKey) : FENCE_TIERS[0];
    if (!to) return null;
    return { from: fromKey ? fenceTier(fromKey) : null, to: to, cost: to.cost, material: to.material };
  }
  function costLabelH(cost) {
    var s = [];
    for (var k in cost) if (cost.hasOwnProperty(k)) s.push(cost[k] + ' ' + k.toUpperCase());
    return s.join(' + ');
  }
  function hProfile() { var E = hEcon(); try { return (E && E.loadProfile) ? E.loadProfile() : null; } catch (_) { return null; } }
  function canAffordFence(fromKey, p) {
    var u = fenceUpgrade(fromKey); if (!u) return false;
    p = p || hProfile(); if (!p) return false;
    for (var k in u.cost) if (u.cost.hasOwnProperty(k) && ((p[k] | 0) < u.cost[k])) return false;
    return true;
  }
  // ATOMIC debit for the next rung. {ok,to,cost} or {ok:false,error,need,have}.
  function payFenceUpgrade(fromKey) {
    var u = fenceUpgrade(fromKey);
    if (!u) return { ok: false, error: 'MAX_TIER' };
    var E = hEcon();
    if (!E || typeof E.mutateProfile !== 'function') return { ok: false, error: 'NO_ECON', cost: u.cost };
    var res = { ok: false, error: 'CANT_AFFORD', cost: u.cost, need: costLabelH(u.cost) };
    E.mutateProfile(function (p) {
      for (var k in u.cost) if (u.cost.hasOwnProperty(k) && ((p[k] | 0) < u.cost[k])) return;
      for (var k2 in u.cost) if (u.cost.hasOwnProperty(k2)) p[k2] = Math.max(0, (p[k2] | 0) - u.cost[k2]);
      res = { ok: true, to: u.to, cost: u.cost };
    });
    return res;
  }

  global.AK_HARVEST = {
    // registry + placement
    NODE_TYPES: HARVEST_NODES, KIND_NODE: KIND_NODE, GROUND: GROUND, RANGE: HARVEST_RANGE,
    // the loop: find it, work it, wait for it to grow back
    nodesFor: nodesFor, nodeAt: nodeByKeyH, nodeNear: nodeNear,
    harvest: harvest, isReady: nodeReady, respawnMs: respawnMs, resetNodes: clearNodes,
    // the payoff: wood fence -> stone fence -> iron fence
    FENCE_TIERS: FENCE_TIERS, fenceTier: fenceTier, nextFence: nextFence,
    fenceUpgrade: fenceUpgrade, canAffordFence: canAffordFence, payFenceUpgrade: payFenceUpgrade,
    fenceCostLabel: costLabelH
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
    rivals:[], rivalsLoading:false, pins:[], editMode:false, drag:null,
    // SPRINT 3 -- DARK WAR strategic world tier (#3)
    tier:'base',          // 'base' (your 3x3 territory) | 'world' (Dark-War strategic map)
    wsel:null,            // selected enemy territory object (world tier)
    march:null,           // active crew march {terr,t,dur}
    wterr:[],             // placed enemy territories [{target,wx,wy,...}]
    wtargets:[],          // the raw AK_RAIDSCENE-shaped targets feeding wterr
    wpins:[],             // hit-test pins for territories (screen space)
    _home:null,           // {wx,wy} your home territory in world-map space
    _api:null };          // live overlay api (captured each frame) -> march closes via it

  // visual grid: each district is a TILE square with GAP between, WALL perimeter
  var TILE = 230, GAP = 30, WALL = 16;
  var GRID_W = 3 * TILE + 2 * GAP, GRID_H = 3 * TILE + 2 * GAP;
  // DARK WAR strategic-map logical bounds (a larger world ABOVE the 3x3 base)
  var WW = 2600, WH = 1900;
  // which content the shared cam/scale is framing -> fit/clamp use this
  function contentDims() { return WM.tier === 'world' ? { w: WW, h: WH } : { w: GRID_W, h: GRID_H }; }

  function profile(ctx) { try { return ctx.econ ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }

  // building level for the badge -- single source of truth, in priority order:
  //   ARENA = real Town Hall level -> producer = profile.prod[id].lvl ->
  //   ctx.buildingLevels[id] (cosmetic host LV map, fallback only) -> 1
  // AK-THSYNC 2026-06-22: REAL economy state must win over the static cosmetic map
  // (same class of bug as the Town Hall "Lv8" display lie -- a producer you upgraded
  // must show its true level, not the placeholder).
  function buildingLevel(ctx, id) {
    try {
      if (id === 'ARENA' && ctx.econ && ctx.econ.townHallLevel) return ctx.econ.townHallLevel();
      var p = profile(ctx);
      if (p && p.prod && p.prod[id] && p.prod[id].lvl) return p.prod[id].lvl | 0;
      if (ctx.buildingLevels && ctx.buildingLevels[id] != null) return ctx.buildingLevels[id] | 0;
    } catch (_) {}
    return 1;
  }

  /* ======================================================================== *
   * SPRINT 2 (A) -- OTHER PLAYERS' BASES  (live ak-raid snapshots as RAID pins)
   * ======================================================================== */
  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  // AK-WARMAP 2026-07-03: this is a multiplayer MMORPG world -- the map must feel
  // POPULATED, not 3 pins. Cap the crews we ring around HOME_TURF at ~a dozen.
  var RIVAL_CAP = 12;
  // tier mirrors raidmap.js/raid.js: <600 = 1, <1200 = 2, else 3 (so a pin's
  // stars + its raid difficulty read the same as the raid LIST for that crew).
  function tierForTr(tr) { tr = tr | 0; return tr >= 1200 ? 3 : tr >= 600 ? 2 : 1; }
  // The signed-out / offline fallback pins. FIRST choice: the FULL living
  // population -- the SAME ~24 roster dogs the raid LIST reads (AK_POPULATION
  // .leaderboard()/roster(), the source raidmap.js consumes), minus the player
  // row (isYou). That gives many DISTINCT crews with real clan/rank/trophies, so
  // the world map looks alive. GUARDED: if AK_POPULATION is missing/empty we fall
  // back to the 3 canon crews below (verbatim clan names -> real crest art), so a
  // bad/absent module is a no-op, never a crash mid-map.
  function localRivals() {
    try {
      var P = global.AK_POPULATION;
      if (P) {
        var rows = (P.leaderboard && P.leaderboard()) || (P.roster && P.roster()) || [];
        rows = rows.filter(function (r) { return r && !r.isYou; });
        if (rows.length) {
          return rows.slice(0, RIVAL_CAP).map(function (r) {
            return {
              id: 'wm_pop_' + (r.id || r.name),           // stable per-crew id (raid grant is client-side)
              name: r.name || 'Rival Crew',               // street name -> seeds a DISTINCT base in raidscene
              cls: r.clanName || r.clan || 'Rival Crew',  // clan class -> crestPath() resolves the real crest art
              faction: r.clan,
              accent: r.color || RED,                     // clan color -> pin ring / tether
              tier: tierForTr(r.trophies),
              trophies: r.trophies | 0,
              roster: r.avatarCard ? [r.avatarCard] : [], // marquee defender -> nemesisFor() fields the nemesis
              local: true
            };
          });
        }
      }
    } catch (_) {}
    // canon crew names (verbatim from raid.js FACTIONS.gangs) -- never invented placeholders.
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
        if (d && d.ok && Array.isArray(d.bases) && d.bases.length) WM.rivals = d.bases.slice(0, RIVAL_CAP);
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
    // AK-RAID-RPG 2026-06-26: world-map raids are RPG-STYLE (modes' openWorldMoba), NOT the lane/tower engine.
    var _M = global.AK_MODES;
    base.onResult = function (res) { try { if (res && !res.win && global.AK_ECON && typeof AK_ECON.raidDamage === 'function') AK_ECON.raidDamage(AK_ECON.loadProfile ? AK_ECON.loadProfile() : null, 1); } catch (_e) {} };
    // AK-HUBRAID 2026-06-30: raid INSIDE the hub renderer (walk their real district); arena is the fallback.
    if (typeof global.akEnterRaid === 'function') { try { global.akEnterRaid(base); return; } catch (_e4) {} }
    if (_M && typeof _M.openWorldMoba === 'function') {
      _M.openWorldMoba(ctx, { enemyHero: nemesisFor(ctx, base), raidTarget: base, label: 'RAID -- ' + ((base && base.name) || 'Rival Crew'), onResult: base.onResult });
    } else {
      ctx.battle.launch({
        mode: 'raid',
        city: (base && base.city != null) ? base.city : clamp(tier + 1, 0, 9),
        level: (base && base.level != null) ? base.level : clamp(2 + tier * 2, 1, 10),
        diffOffset: (base && base.diffOffset != null) ? base.diffOffset : (tier - 1),
        nemesis: nemesisFor(ctx, base),
        label: 'RAID -- ' + ((base && base.name) || 'Rival Crew')
      });
    }
  }

  /* ======================================================================== *
   * AK-RAID-STAMINA (CAPTIVATION_PLAN P4) -- "BONES TO RUN": gate REWARD-raids
   *   behind AK_ECON's time-regen stamina pool. A reward-raid (a world-map
   *   MARCH or a base-tier rival-pin raid) costs 1 stamina; when empty we show
   *   "rest up -- N min or spend bones" (the soft-currency, NEVER gems / never
   *   pay-to-win). Refills by TIME or BONES only via AK_ECON.refillStamina.
   *   Free-roam / story / the Watch are NEVER routed through here, so the
   *   open-world feel survives. If AK_ECON lacks the stamina API the gate is a
   *   NO-OP (always allows) and the HUD chip simply does not render.
   *   Deterministic-by-elapsed-time (econ owns the clock); no client RNG here.
   * ======================================================================== */
  // human countdown ("12m 30s" / "2h 5m" / "45s") for the regen timer + banner
  function fmtDur(ms) {
    ms = Math.max(0, ms | 0);
    var s = Math.ceil(ms / 1000), m = (s / 60) | 0; s = s % 60;
    if (m >= 60) { var h = (m / 60) | 0; return h + 'h ' + (m % 60) + 'm'; }
    if (m > 0) return m + 'm ' + (s < 10 ? '0' + s : s) + 's';
    return s + 's';
  }
  // resolve the econ module (window.AK_ECON wins; ctx.econ is the same handle)
  function econ() { try { return global.AK_ECON || (WM.ctx && WM.ctx.econ) || null; } catch (_) { return null; } }
  // live stamina pool, or null when the econ stamina API is absent (=> no-op gate).
  // 60fps-safe: raidStamina() with no profile hits localStorage (econ flags this),
  // and the HUD chip reads it every frame -- so we cache for ~300ms (stamina moves
  // over HOURS; the countdown shows m/s, so a sub-second hold is invisible). The
  // GATE never reads this cache (it calls econ.spendStamina directly = always
  // authoritative); a spend/refill invalidates so the chip flips instantly.
  var _stam = { t: -1e9, v: null };
  function nowMs() { try { return (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now(); } catch (_) { return Date.now(); } }
  function staminaRead() {
    var E = econ(); if (!E || typeof E.raidStamina !== 'function') { _stam.v = null; return null; }
    var t = nowMs(); if (_stam.v && (t - _stam.t) < 300) return _stam.v;
    var v; try { v = E.raidStamina(); } catch (_) { v = null; }
    _stam.t = t; _stam.v = v; return v;
  }
  function invalidateStam() { _stam.t = -1e9; _stam.v = null; }
  // THE GATE: pay 1 stamina to launch a reward-raid. Returns true when allowed
  // (or when the econ stamina API is absent -> no-op). On empty: false + the
  // "rest up -- N min or spend bones" banner. NEVER touches gems.
  function payRaidStamina(ctx) {
    ctx = ctx || WM.ctx;
    var E = econ();
    if (!E || typeof E.spendStamina !== 'function' || typeof E.raidStamina !== 'function') return true; // no-op gate
    var r; try { r = E.spendStamina(1); } catch (_) { return true; }
    invalidateStam();
    if (r && r.ok) return true;
    var s = staminaRead();
    var wait = (s && !s.full) ? fmtDur(s.nextInMs) : 'a bit';
    try { ctx && ctx.showBanner && ctx.showBanner('NO STAMINA -- rest up ' + wait + ' or spend \u{1F9B4} bones', 2.2); } catch (_b) {}
    return false;
  }
  // the "or spend bones" path -- soft-currency refill ONLY (econ refuses gems).
  function bonesRefill(ctx) {
    ctx = ctx || WM.ctx;
    var E = econ();
    if (!E || typeof E.refillStamina !== 'function') { try { ctx.showBanner('Stamina refill unavailable.', 1.4); } catch (_) {} return; }
    var r; try { r = E.refillStamina('bones'); } catch (_) { return; }
    invalidateStam();
    if (r && r.ok) { try { ctx.showBanner('\u{1F9B4} Bones spent -- stamina refilled.', 1.6); } catch (_) {} }
    else if (r && r.error === 'INSUFFICIENT_BONES') { try { ctx.showBanner('Not enough bones -- need ' + (r.need || 0) + ' \u{1F9B4}.', 1.8); } catch (_) {} }
    else if (r && r.error === 'ALREADY_FULL') { try { ctx.showBanner('Stamina already full.', 1.2); } catch (_) {} }
    else { try { ctx.showBanner('Refill failed.', 1.2); } catch (_) {} }
  }
  // the raid-affordance stamina chip: pool + regen timer ("Bones to Run").
  // Drawn on BOTH zoom tiers next to the raid surface. No-op when econ absent.
  function drawStaminaPill(g, vp, x, y) {
    var s = staminaRead(); if (!s) return null;
    var txt = '\u{1F9B4} ' + s.cur + '/' + s.max + (s.full ? '  ·  FULL' : '  ·  +1 in ' + fmtDur(s.nextInMs));
    g.save(); g.font = '800 11px Inter, system-ui, sans-serif';
    var w = g.measureText(txt).width + 22, h = 22;
    rr(g, x, y, w, h, 7); g.fillStyle = 'rgba(8,8,12,.82)'; g.fill();
    g.lineWidth = 1; g.strokeStyle = (s.cur >= 1) ? 'rgba(201,168,76,.5)' : 'rgba(192,57,43,.65)'; g.stroke();
    g.restore();
    var col = s.full ? GOLD : (s.cur >= 1 ? '#f3d9a8' : '#ff8a7a');
    label(g, txt, x + 11, y + h / 2, 11, col, '800', 'left');
    return { x: x, y: y, w: w, h: h };
  }

  /* ======================================================================== *
   * SPRINT 3 -- DARK WAR STRATEGIC WORLD MAP  (#3: log out -> world map ->
   *   crew marches to attack). A SECOND zoom tier ABOVE the base view:
   *   YOUR home territory + multiple ENEMY territories scattered on a larger,
   *   fogged war map. Tap an enemy -> scout/confirm -> MARCH animation -> on
   *   arrival call window.AK_RAIDSCENE.launch(target) (Agent A's walk-on raid).
   *
   *   SHARED INTERFACE (must match Agent A exactly):
   *     window.AK_RAIDSCENE.launch(target)
   *       target = { name, crew, faction,
   *                  layout:[{type,x,y,hp,maxHp}],   // base-as-battlefield
   *                  coreHp, trophies,
   *                  reward:{gold,scrap,wood,stone,metal} }  // soft/material ONLY
   *     window.AK_RAIDSCENE.targets() -> [target,...]  (preferred source)
   *
   *   DEGRADE (Agent A not loaded yet): we build VALID targets ourselves from
   *   live ak-raid snapshots (WM.rivals) or canon local war-crews, and the march
   *   falls back to the live battler raid (raidFrom) so it still fully works.
   *   HARD RULE: reward is gold/scrap/wood/stone/metal ONLY -- never gems/$BCARDD.
   * ======================================================================== */

  // wall/structure HP -- mirrors buildmode.js STRUCT + AK_RAID_DEFENSE_SYSTEM
  // (wood 200 / stone 500 / metal 1200) so the enemy base uses the SAME vocab.
  var WALL_HP = { WALL: 200, STONE: 500, METAL: 1200, BARRICADE: 120 };

  // tiny deterministic PRNG so a crew's base layout + scatter is stable per id
  function strHash(s) { s = String(s); var h = 2166136261 >>> 0; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function rng32(seed) { var s = seed >>> 0; return function () { s |= 0; s = (s + 0x6D2B79F5) | 0; var t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

  // canon war crews (verbatim from raid.js FACTIONS.gangs + cls/accent) so the
  // degrade map still reuses REAL crews + REAL cards BY NAME -- no placeholders.
  function localWarCrews(ctx) {
    var C = [
      { id:'wc_boneyard', name:'The Boneyard Mob', cls:'Boneguard Crew',   accent:'#e8c55a', tier:1, marquee:'Tank Pug' },
      { id:'wc_crypt',    name:'Crypt Kings',      cls:'Boneguard Crew',   accent:'#e8c55a', tier:3, marquee:'Stonejaw' },
      { id:'wc_zoomie',   name:'Zoomie Riot',      cls:'Zoomie Syndicate', accent:'#7CFFB0', tier:2, marquee:'Neon Whippet' },
      { id:'wc_burnout',  name:'The Burnouts',     cls:'Zoomie Syndicate', accent:'#7CFFB0', tier:1, marquee:'Turbo Jack' },
      { id:'wc_leashless',name:'Leashless Cartel', cls:'Leashbreak Tactix',accent:'#9d8bff', tier:3, marquee:'Firewall' },
      { id:'wc_circuit',  name:'Circuit Hounds',   cls:'K9 Circuitry',     accent:'#7fc8ff', tier:2, marquee:'Laser Beagle' }
    ];
    return C.map(function (c) {
      var t = c.tier;
      // only keep a marquee that exists in the live card table (else drop it)
      var marquee = (function () { try { return ctx.cards()[c.marquee] ? c.marquee : null; } catch (_) { return null; } })();
      return {
        id: c.id, name: c.name, cls: c.cls, faction: c.cls.toLowerCase().replace(/[^a-z]+/g, '_'),
        accent: c.accent, tier: t, trophies: 280 + t * 210 + (strHash(c.id) % 160),
        roster: marquee ? [marquee] : [],
        loot: { gold: 110 * t, scrap: t >= 2 ? 2 * t : 0 },
        city: clamp(t + 1, 0, 9), level: clamp(2 + t * 2, 1, 10), diffOffset: t - 1
      };
    });
  }

  // FALLBACK base-as-battlefield layout in raidscene's PLOT-COORDINATE space
  // (0..100, the SAME space the scout scene renders) -> [{type,x,y,hp,maxHp}], using
  // the buildmode structure vocab. Walls upgrade with tier. Includes a CORE so the
  // scout scene shows the Town Hall. Only used headless / when AK_RAIDSCENE is absent
  // (toRaidTarget delegates to AK_RAIDSCENE.genTarget when it's loaded).
  function buildLayout(tier, seedKey) {
    tier = tier || 1;
    var r = rng32(strHash(seedKey || ('t' + tier)));
    var cx = 50, cy = 36, coreHp = 1000 + tier * 600;
    var wallType = tier >= 3 ? 'METAL' : tier === 2 ? 'STONE' : 'WALL';
    var whp = WALL_HP[wallType], L = [];
    L.push({ type: 'CORE', x: cx, y: cy, hp: coreHp, maxHp: coreHp, name: 'TOWN HALL' });
    var segs = 12, rx = 30, ry = 22;                          // perimeter wall ring
    for (var i = 0; i < segs; i++) { var a = (i / segs) * Math.PI * 2;
      L.push({ type: wallType, x: clamp(Math.round(cx + Math.cos(a) * rx), 7, 93), y: clamp(Math.round(cy + Math.sin(a) * ry), 8, 64), hp: whp, maxHp: whp }); }
    var bn = 3 + (tier >= 2 ? 1 : 0);                         // forward barricade gate (south approach)
    for (var k = 0; k < bn; k++) {
      L.push({ type: 'BARRICADE', x: clamp(cx - 14 + k * 14, 8, 92), y: clamp(Math.round(cy + ry + 8 + (r() * 4)), 10, 70), hp: WALL_HP.BARRICADE, maxHp: WALL_HP.BARRICADE }); }
    var blds = ['GEM', 'MINT', 'FORGE'], bhp = 800 + tier * 200;   // producers inside the ring
    for (var b = 0; b < blds.length; b++) { var ang = (b / blds.length) * Math.PI * 2 - Math.PI / 2;
      L.push({ type: blds[b], x: clamp(Math.round(cx + Math.cos(ang) * 14), 14, 86), y: clamp(Math.round(cy + Math.sin(ang) * 11), 12, 60), hp: bhp, maxHp: bhp }); }
    return L;
  }

  // a snapshot base (genTargets/local shape) -> a VALID AK_RAIDSCENE target.
  // SINGLE SOURCE OF TRUTH: when raidscene (Agent A) is loaded we DELEGATE the
  // layout/coreHp/reward/roster to AK_RAIDSCENE.genTarget so the base is built in
  // ITS plot-coordinate space (0..100). The scout scene then renders it 1:1 (fixes
  // the bug where worldmap's world-scale 0..1700 coords drew every structure
  // off-screen -> "no enemy map loads"), and the defenders are real cards BY NAME.
  // `crew` stays a class STRING for the world-map's own pin + bottom-bar display.
  function toRaidTarget(ctx, b) {
    b = b || {}; var tier = b.tier || 1;
    var rs = global.AK_RAIDSCENE, layout, coreHp, reward, roster, accent;
    if (rs && typeof rs.genTarget === 'function') {
      var gt = rs.genTarget({ id: b.id, name: b.name, faction: b.faction, cls: b.cls, tier: tier,
        trophies: b.trophies, city: b.city, level: b.level, diffOffset: b.diffOffset }, ctx);
      layout = gt.layout; coreHp = gt.coreHp; reward = gt.reward;
      roster = (Array.isArray(gt.roster) && gt.roster.length) ? gt.roster : (Array.isArray(b.roster) ? b.roster : []);
      accent = b.accent || gt.accent || RED;
    } else {                                       // headless / raidscene-less fallback (0..100 layout)
      layout = buildLayout(tier, b.id || b.name);
      coreHp = 1000 + tier * 600;
      reward = { gold: (b.loot && b.loot.gold) || (110 * tier), scrap: (b.loot && b.loot.scrap) || (tier >= 2 ? 2 * tier : 0),
        wood: 20 * tier, stone: tier >= 2 ? 10 * tier : 0, metal: tier >= 3 ? 5 * tier : 0 };
      roster = Array.isArray(b.roster) ? b.roster : [];
      accent = b.accent || RED;
    }
    return {
      // carry the SERVER base id (uuid for bots, the victim's user_id for a real
      // player) so modes.js can settle loot via ak-raid {action:'resolve'} on a win.
      id:      b.id,
      name:    b.name || 'Rival Crew',
      crew:    b.cls || b.crew || 'Stray Pack',    // STRING -> world-map pin/bar display
      cls:     b.cls || 'Stray Pack',
      faction: b.faction || 'boneguard_crew',
      layout:  layout, coreHp: coreHp,
      trophies:b.trophies || (280 + tier * 210),
      reward:  reward,
      // kept for the degrade battler launch (raidFrom) + the scout panel
      accent: accent, tier: tier, city: b.city, level: b.level,
      diffOffset: b.diffOffset, roster: roster, _base: b
    };
  }

  // ensure a partner-supplied target (AK_RAIDSCENE.targets()) is fully shaped +
  // token-safe before we hand it to launch (guards against partial data).
  function normalizeTarget(ctx, t) {
    t = t || {}; var tier = t.tier || 1;
    if (!Array.isArray(t.layout) || !t.layout.length) t.layout = buildLayout(tier, t.id || t.name || 'x');
    if (typeof t.coreHp !== 'number') t.coreHp = 1000 + tier * 600;
    if (!t.reward || typeof t.reward !== 'object') t.reward = {};
    var rw = t.reward; ['gold', 'scrap', 'wood', 'stone', 'metal'].forEach(function (k) { if (typeof rw[k] !== 'number') rw[k] = 0; });
    // HARD RULE: strip any gem/token leakage a partner reward might carry
    ['gems', 'gem', 'ALK', 'alk', 'bcardd', 'BCARDD', '$BCARDD'].forEach(function (k) { if (k in rw) delete rw[k]; });
    if (!t.name) t.name = 'Rival Crew';
    if (!t.crew) t.crew = t.cls || 'Stray Pack';
    if (!t.faction) t.faction = 'boneguard_crew';
    if (typeof t.trophies !== 'number') t.trophies = 280 + tier * 210;
    if (typeof t.accent !== 'string') t.accent = RED;
    return t;
  }

  // the world-tier target source, in priority order:
  //   1) Agent A's shared generator window.AK_RAIDSCENE.targets()
  //   2) live ak-raid snapshots already pulled into WM.rivals (Sprint 2)
  //   3) canon local war-crews (always available -> map always populates)
  function worldTargets(ctx) {
    try {
      if (global.AK_RAIDSCENE && typeof global.AK_RAIDSCENE.targets === 'function') {
        var a = global.AK_RAIDSCENE.targets();
        if (Array.isArray(a) && a.length) return a.map(function (t) { return normalizeTarget(ctx, t); });
      }
    } catch (_) {}
    try {
      if (WM.rivals && WM.rivals.length && !WM.rivals[0].local) return WM.rivals.map(function (b) { return toRaidTarget(ctx, b); });
    } catch (_2) {}
    return localWarCrews(ctx).map(function (b) { return toRaidTarget(ctx, b); });
  }

  // THE HANDOFF: enter Agent A's walk-on raid scene (degrade -> battler raid)
  function launchRaidScene(ctx, target) {
    if (!target) return false;
    if (global.AK_RAIDSCENE && typeof global.AK_RAIDSCENE.launch === 'function') {
      try { global.AK_RAIDSCENE.launch(target); return true; } catch (_) {}
    }
    try { raidFrom(ctx, target._base || target); return true; } catch (_2) {}
    try { ctx.showBanner('Raid scene loading -- try again in a sec.', 1.8); } catch (_3) {}
    return false;
  }

  // scatter the enemy territories on an upper war-front arc around your home
  function placeTerritories(ctx) {
    var ts = worldTargets(ctx); WM.wtargets = ts;
    var homeX = WW / 2, homeY = WH * 0.66, n = ts.length, out = [];
    for (var i = 0; i < n; i++) {
      var t = ts[i];
      var ang = -Math.PI / 2 + ((i - (n - 1) / 2) * 0.62);
      var rad = 430 + (i % 3) * 250 + ((strHash(t.name) >>> 8) % 140);
      var x = clamp(homeX + Math.cos(ang) * rad, 200, WW - 200);
      var y = clamp(homeY + Math.sin(ang) * rad * 0.78, 170, WH - 300);
      out.push({ target: t, wx: x, wy: y, accent: t.accent || RED, name: t.name, crew: t.crew, tier: t.tier || 1, trophies: t.trophies || 0 });
    }
    WM.wterr = out; WM._home = { wx: homeX, wy: homeY };
    return out;
  }

  // switch zoom tiers (base <-> world); refits the shared camera to the content
  function switchTier(tier, vp) {
    WM.tier = tier; WM.sel = null; WM.wsel = null; WM.march = null; WM.editMode = false; WM.drag = null;
    if (tier === 'world') { try { placeTerritories(WM.ctx); } catch (_) {} }
    var v = vp || { w: (typeof innerWidth !== 'undefined' ? innerWidth : 360), h: (typeof innerHeight !== 'undefined' ? innerHeight : 640) };
    fitToScreen(v); clampCam(v);
  }

  // begin a crew march on a selected territory (solo march fully works)
  function startMarch(ctx, terr, api) {
    if (!terr || WM.march) return;
    WM._api = api; WM.march = { terr: terr, t: 0, dur: 1.25 }; WM.wsel = null;
    try { ctx.showBanner('Crew marches on ' + (terr.name || 'the block') + '...', 1.4); } catch (_) {}
  }

  /* ---- DARK WAR drawing -------------------------------------------------- */
  function drawFog(g, vp, hsx, hsy) {
    g.save();
    g.fillStyle = 'rgba(4,5,9,.55)'; g.fillRect(0, 0, vp.w, vp.h);
    function reveal(X, Y, rad, col) { var rg = g.createRadialGradient(X, Y, 0, X, Y, rad); rg.addColorStop(0, col); rg.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = rg; g.beginPath(); g.arc(X, Y, rad, 0, 7); g.fill(); }
    reveal(hsx, hsy, 200 * WM.scale + 60, 'rgba(232,197,90,.16)');
    for (var i = 0; i < WM.wterr.length; i++) { var tr = WM.wterr[i]; reveal(sx(tr.wx), sy(tr.wy), 150 * WM.scale + 40, 'rgba(192,57,43,.12)'); }
    var vg = g.createRadialGradient(vp.w / 2, vp.h / 2, Math.min(vp.w, vp.h) * 0.3, vp.w / 2, vp.h / 2, Math.max(vp.w, vp.h) * 0.78);
    vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,.62)'); g.fillStyle = vg; g.fillRect(0, 0, vp.w, vp.h);
    g.restore();
  }

  function drawHome(g, ctx, X, Y) {
    var R = clamp(56 * WM.scale, 34, 86);
    var W = R * 2, H = R * 1.64, px = X - R, py = Y - R * 0.82;
    // the REAL painted home turf (THE LOT) as the panel art, cover-fit + matte darken
    g.save();
    rr(g, px, py, W, H, 4); g.clip();
    if (!drawCover(g, img('assets/hub/the_lot_bg.png'), px, py, W, H)) { g.fillStyle = 'rgba(20,17,9,.92)'; g.fillRect(px, py, W, H); }
    g.fillStyle = 'rgba(6,6,10,.34)'; g.fillRect(px, py, W, H);
    var sh0 = g.createLinearGradient(0, py, 0, py + H);
    sh0.addColorStop(0, 'rgba(0,0,0,.5)'); sh0.addColorStop(0.42, 'rgba(0,0,0,0)'); sh0.addColorStop(1, 'rgba(0,0,0,.58)');
    g.fillStyle = sh0; g.fillRect(px, py, W, H);
    g.restore();
    // gold command frame (hard-edge, glowing -- this is YOUR seat of power)
    g.save();
    rr(g, px, py, W, H, 4);
    g.lineWidth = Math.max(2, 3 * WM.scale); g.strokeStyle = GOLD; g.shadowColor = GOLD; g.shadowBlur = 18; g.stroke();
    g.restore();
    // crew crest seal on the top edge (real crest art, not an emoji)
    drawCrest(g, X, py, clamp(15 * WM.scale, 11, 20), playerCrestKey(ctx), GOLD, true);
    labelH(g, 'YOUR TURF', X, py + H - 17 * WM.scale, clamp(12 * WM.scale, 9, 15), GOLD, '900');
    label(g, 'THE LOT', X, py + H - 6 * WM.scale, clamp(8 * WM.scale, 7, 10), '#d8c98a', '800');
    // shield pip if active
    try { var p = profile(ctx); if (p && p.raid && p.raid.shieldUntil > Date.now()) label(g, '🛡 SHIELDED', X, py + H + 11 * WM.scale, clamp(8 * WM.scale, 7, 10), '#7CFFB0', '800'); } catch (_) {}
  }

  // deterministic themed district art for an enemy block (stable per crew name)
  var TERR_BGS = ['downtown', 'neon_heights', 'the_yards', 'factory_row', 'the_strip', 'the_docks', 'the_overlook', 'the_undercity'];
  function terrBg(tr) { return 'assets/hub/' + TERR_BGS[strHash(tr.name || 'x') % TERR_BGS.length] + '_bg.png'; }

  function drawTerritory(g, tr) {
    var X = sx(tr.wx), Y = sy(tr.wy), R = clamp(48 * WM.scale, 30, 78), ac = tr.accent || RED;
    var seld = (WM.wsel === tr);
    var W = R * 2, H = R * 1.6, px = X - R, py = Y - R * 0.8;
    // themed PAINTED district panel (cover-fit, darkened -- enemy turf reads as a real block)
    g.save();
    rr(g, px, py, W, H, 4); g.clip();
    if (!drawCover(g, img(terrBg(tr)), px, py, W, H)) { g.fillStyle = 'rgba(14,9,10,.9)'; g.fillRect(px, py, W, H); }
    g.fillStyle = 'rgba(8,5,7,.42)'; g.fillRect(px, py, W, H);
    var sh1 = g.createLinearGradient(0, py, 0, py + H);
    sh1.addColorStop(0, 'rgba(0,0,0,.44)'); sh1.addColorStop(0.45, 'rgba(0,0,0,0)'); sh1.addColorStop(1, 'rgba(0,0,0,.62)');
    g.fillStyle = sh1; g.fillRect(px, py, W, H);
    g.restore();
    // frame: faction accent normally, gold glow when scouted/selected
    g.save();
    rr(g, px, py, W, H, 4);
    g.lineWidth = seld ? Math.max(3, 3.5 * WM.scale) : Math.max(1.5, 2 * WM.scale);
    g.strokeStyle = seld ? GOLD : ac; if (seld) { g.shadowColor = GOLD; g.shadowBlur = 16; } else { g.shadowColor = ac; g.shadowBlur = 8; }
    g.stroke();
    g.restore();
    // clan CREST seal on the top edge (real crest art) + tier stars above it
    var cr = clamp(13 * WM.scale, 10, 18);
    drawCrest(g, X, py, cr, tr.crew || (tr.target && tr.target.faction), ac, seld);
    var st = ''; for (var s = 0; s < (tr.tier || 1); s++) st += '★';
    label(g, st, X, py - cr - 8 * WM.scale, clamp(9 * WM.scale, 7, 12), GOLD, '800');
    // crew nameplate (Cinzel gold, inside the darkened band) + trophies chip below
    var nm = String(tr.name || 'Rival Crew');
    var fs = clamp(9.5 * WM.scale, 8, 12), ph = Math.max(14, 15 * WM.scale);
    g.save(); g.font = '800 ' + fs + 'px ' + FONT_H; g.textAlign = 'center';
    var tw = g.measureText(nm).width + 12;
    g.fillStyle = 'rgba(8,8,12,.78)'; rr(g, X - tw / 2, py + H - ph - 3, tw, ph, 3); g.fill();
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.35)'; g.stroke();
    g.restore();
    labelH(g, nm, X, py + H - ph / 2 - 3, fs, '#f0d98a', '800');
    drawTrophyChip(g, X, py + H + 11 * WM.scale, tr.trophies || 0, clamp(9 * WM.scale, 8, 11));
    WM.wpins.push({ x: X, y: Y, r: R + 6, terr: tr });
  }

  function advanceMarch(g, dt, ctx, hsx, hsy) {
    var m = WM.march; m.t += dt;
    var p = clamp(m.t / m.dur, 0, 1), tr = m.terr;
    var tx = sx(tr.wx), ty = sy(tr.wy);
    var e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;   // ease in-out
    var mx = hsx + (tx - hsx) * e, my = hsy + (ty - hsy) * e;
    g.save();
    g.strokeStyle = 'rgba(232,197,90,.75)'; g.lineWidth = Math.max(2, 3 * WM.scale); g.setLineDash([3, 6]);
    g.beginPath(); g.moveTo(hsx, hsy); g.lineTo(mx, my); g.stroke(); g.setLineDash([]);
    var mr = clamp(15 * WM.scale, 12, 22);
    g.fillStyle = 'rgba(10,8,6,.94)'; g.beginPath(); g.arc(mx, my, mr, 0, 7); g.fill();
    g.lineWidth = 2; g.strokeStyle = GOLD; g.shadowColor = GOLD; g.shadowBlur = 12; g.stroke();
    g.restore();
    label(g, '🐕', mx, my, clamp(mr, 10, 18), '#fff', '900');
    label(g, 'MARCHING', mx, my - mr - 8 * WM.scale, clamp(9 * WM.scale, 8, 12), GOLD, '800');
    if (p >= 1) {
      var target = tr.target; WM.march = null;
      try { ctx.showBanner('Crew reaches ' + (tr.name || 'the block') + ' -- breach!', 1.2); } catch (_) {}
      if (WM._api && WM._api.close) { try { WM._api.close({ raidscene: target }); } catch (_2) {} }
    }
  }

  function drawWorldFrame(g, dt, vp, ctx) {
    if (!WM.wterr.length) { try { placeTerritories(ctx); } catch (_) {} }
    // war ground -- the painted aerial burned-city plate (CF-generated), gradient fallback while it loads
    var grd = g.createLinearGradient(0, 0, 0, vp.h); grd.addColorStop(0, '#0a0c14'); grd.addColorStop(1, '#05060a');
    g.fillStyle = grd; g.fillRect(0, 0, vp.w, vp.h);
    var wg = img('assets/hub/war_ground.png');
    if (wg && wg.complete && wg.naturalWidth > 0) {
      g.save(); g.globalAlpha = 0.6;
      // parallax the plate slightly against the camera so the war ground reads deep
      var ps = Math.max(vp.w / wg.naturalWidth, vp.h / wg.naturalHeight) * 1.15;
      var pw = wg.naturalWidth * ps, ph = wg.naturalHeight * ps;
      g.drawImage(wg, -(WM.cam.x * 0.06) % Math.max(1, pw - vp.w) - (pw - vp.w) * 0.5, -(WM.cam.y * 0.06) % Math.max(1, ph - vp.h) - (ph - vp.h) * 0.5, pw, ph);
      g.globalAlpha = 0.35; g.fillStyle = '#05060a'; g.fillRect(0, 0, vp.w, vp.h);   // re-darken so panels/pins stay legible
      g.restore();
    }
    // faint scan grid
    g.save(); g.strokeStyle = 'rgba(201,168,76,.05)'; g.lineWidth = 1;
    for (var gx = (WM.cam.x % 50); gx < vp.w; gx += 50) { g.beginPath(); g.moveTo(gx, 0); g.lineTo(gx, vp.h); g.stroke(); }
    for (var gy = (WM.cam.y % 50); gy < vp.h; gy += 50) { g.beginPath(); g.moveTo(0, gy); g.lineTo(vp.w, gy); g.stroke(); }
    g.restore();
    // matte grain finish (cached pattern, built once)
    var gp0 = grainPat(g);
    if (gp0) { g.save(); g.globalAlpha = 0.55; g.fillStyle = gp0; g.fillRect(0, 0, vp.w, vp.h); g.restore(); }
    var home = WM._home || { wx: WW / 2, wy: WH * 0.66 };
    var hsx = sx(home.wx), hsy = sy(home.wy);
    drawFog(g, vp, hsx, hsy);
    // march roads (home -> each territory)
    g.save(); g.setLineDash([8, 7]); g.lineWidth = Math.max(1, 1.6 * WM.scale);
    for (var i = 0; i < WM.wterr.length; i++) { var tr = WM.wterr[i];
      g.strokeStyle = (WM.wsel === tr) ? 'rgba(232,197,90,.5)' : 'rgba(192,57,43,.18)';
      g.beginPath(); g.moveTo(hsx, hsy); g.lineTo(sx(tr.wx), sy(tr.wy)); g.stroke(); }
    g.restore();
    // territories
    WM.wpins = [];
    for (var j = 0; j < WM.wterr.length; j++) { try { drawTerritory(g, WM.wterr[j]); } catch (_e) {} }
    drawHome(g, ctx, hsx, hsy);
    if (WM.march) { try { advanceMarch(g, dt, ctx, hsx, hsy); } catch (_m) {} }
    drawWorldHud(g, vp, ctx);
  }

  function drawWorldHud(g, vp, ctx) {
    WM.btns = [];
    // top bar -- matte plate + gold hairline + Cinzel wordmark
    g.fillStyle = 'rgba(8,8,12,.86)'; g.fillRect(0, 0, vp.w, 50);
    g.fillStyle = 'rgba(201,168,76,.45)'; g.fillRect(0, 49, vp.w, 1);
    labelH(g, 'WAR MAP', 14, 24, 17, GOLD, '900', 'left');
    label(g, WM.wterr.length + ' rival blocks scouted', 14, 41, 11, DIM, '700', 'left');
    var cb = { id:'close', x: vp.w - 50, y: 8, w: 38, h: 34 };
    g.save(); rr(g, cb.x, cb.y, cb.w, cb.h, 3); g.fillStyle = 'rgba(255,255,255,.06)'; g.fill();
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.3)'; g.stroke(); g.restore();
    label(g, '×', cb.x + cb.w / 2, cb.y + cb.h / 2, 24, '#ccc', '700'); WM.btns.push(cb);
    var bb = { id:'wback', x: vp.w - 50 - 12 - 128, y: 8, w: 128, h: 34 };
    g.save(); rr(g, bb.x, bb.y, bb.w, bb.h, 3); g.fillStyle = 'rgba(201,168,76,.10)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,.5)'; g.lineWidth = 1; g.stroke(); g.restore();
    labelH(g, '◂ MY BASE', bb.x + bb.w / 2, bb.y + bb.h / 2, 11, GOLD, '900'); WM.btns.push(bb);
    drawStaminaPill(g, vp, 12, 56);   // P4 "Bones to Run": pool + regen on the raid surface
    // bottom bar
    var barY = vp.h - 92;
    g.fillStyle = 'rgba(8,8,12,.92)'; g.fillRect(0, barY, vp.w, 92);
    g.strokeStyle = 'rgba(201,168,76,.25)'; g.lineWidth = 1; g.beginPath(); g.moveTo(0, barY); g.lineTo(vp.w, barY); g.stroke();
    if (WM.march) {
      var tr0 = WM.march.terr;
      labelH(g, 'MARCHING ON ' + String(tr0.name || 'RIVAL BLOCK').toUpperCase(), 16, barY + 26, 13, GOLD, '900', 'left');
      label(g, 'crew en route -- breach imminent', 16, barY + 48, 11, DIM, '700', 'left');
      var pp = clamp(WM.march.t / WM.march.dur, 0, 1);
      g.fillStyle = 'rgba(255,255,255,.08)'; rr(g, 16, barY + 62, vp.w - 32, 10, 5); g.fill();
      g.fillStyle = GOLD; rr(g, 16, barY + 62, (vp.w - 32) * pp, 10, 5); g.fill();
      return;
    }
    var tr = WM.wsel;
    if (tr) {
      var tgt = tr.target, walls = 0, blds = 0;
      for (var i = 0; i < tgt.layout.length; i++) { var ty = tgt.layout[i].type; if (ty === 'WALL' || ty === 'STONE' || ty === 'METAL' || ty === 'BARRICADE') walls++; else blds++; }
      // crest thumbnail + Cinzel crew name on the scout bar
      drawCrest(g, 30, barY + 26, 14, tr.crew || (tr.target && tr.target.faction), tr.accent || RED, false);
      labelH(g, tr.name, 52, barY + 22, 14, '#f0d98a', '800', 'left');
      var st = ''; for (var s = 0; s < (tr.tier || 1); s++) st += '★';
      label(g, (tr.crew || 'Stray Pack') + '   ' + st + '   ' + (tr.trophies || 0) + ' tr', 52, barY + 42, 11, '#cfa0a0', '700', 'left');
      label(g, 'DEF: ' + walls + ' walls · core ' + tgt.coreHp + ' HP · ' + blds + ' buildings', 16, barY + 62, 10, DIM, '700', 'left');
      // loot row: real currency chip icons, not text codes
      var rw = tgt.reward, lx = 16, lyy = barY + 81;
      label(g, 'LOOT', lx, lyy, 10, DIM, '800', 'left'); lx += 36;
      lx = lootChip(g, lx, lyy, 'gold', rw.gold);
      lx = lootChip(g, lx, lyy, 'wood', rw.wood);
      lx = lootChip(g, lx, lyy, 'stone', rw.stone);
      lx = lootChip(g, lx, lyy, 'metal', rw.metal);
      lx = lootChip(g, lx, lyy, 'scrap', rw.scrap);
      var s2 = staminaRead(), empty = !!(s2 && s2.cur < 1);   // P4: MARCH is a reward-raid -> "Bones to Run"
      var mb = { id:'march', x: vp.w - 148, y: barY + 14, w: 132, h: 38 };
      g.save(); rr(g, mb.x, mb.y, mb.w, mb.h, 3);
      if (empty) { g.fillStyle = 'rgba(58,28,26,.85)'; g.fill(); g.strokeStyle = 'rgba(192,57,43,.6)'; g.lineWidth = 1; g.stroke(); }
      else { var gr = g.createLinearGradient(0, mb.y, 0, mb.y + mb.h); gr.addColorStop(0, GOLD); gr.addColorStop(1, GOLD_D); g.fillStyle = gr; g.fill(); }
      g.restore();
      if (empty) label(g, '\u{1F9B4} REST ' + fmtDur(s2.nextInMs), mb.x + mb.w / 2, mb.y + mb.h / 2, 11, '#ffb4a6', '900');
      else label(g, '⚔ MARCH ▸' + (s2 ? '  (1\u{1F9B4})' : ''), mb.x + mb.w / 2, mb.y + mb.h / 2, s2 ? 12 : 14, '#15110a', '900');
      WM.btns.push(mb);
      if (empty) {   // the "or spend bones" affordance (soft-currency refill, NEVER gems)
        var srb = { id:'srefill', x: vp.w - 148, y: barY + 56, w: 132, h: 28 };
        g.save(); rr(g, srb.x, srb.y, srb.w, srb.h, 3); g.fillStyle = 'rgba(232,197,90,.14)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,.55)'; g.lineWidth = 1; g.stroke(); g.restore();
        label(g, '\u{1F9B4} SPEND BONES', srb.x + srb.w / 2, srb.y + srb.h / 2, 10, GOLD, '800'); WM.btns.push(srb);
      } else {
        var rcb = { id:'rally', x: vp.w - 148, y: barY + 56, w: 132, h: 28 };
        g.save(); rr(g, rcb.x, rcb.y, rcb.w, rcb.h, 3); g.fillStyle = 'rgba(255,255,255,.05)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,.3)'; g.lineWidth = 1; g.stroke(); g.restore();
        label(g, 'RALLY CREW (soon)', rcb.x + rcb.w / 2, rcb.y + rcb.h / 2, 10, DIM, '800'); WM.btns.push(rcb);
      }
    } else {
      label(g, 'Tap a rival block to scout · drag to pan, pinch to zoom', 16, barY + 30, 12, DIM, '700', 'left');
      label(g, 'Your crew marches from THE LOT. Solo march is live; crew rally soon.', 16, barY + 52, 10, '#7a7468', '700', 'left');
    }
  }

  function handleWorldTap(px, py, api) {
    var ctx = WM.ctx;
    for (var i = 0; i < WM.btns.length; i++) {
      var b = WM.btns[i];
      if (px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h) {
        if (b.id === 'close') { api.close(); return; }
        if (b.id === 'wback') { switchTier('base', api.vp); return; }
        if (b.id === 'march') { if (WM.wsel && payRaidStamina(ctx)) startMarch(ctx, WM.wsel, api); return; }   // costs "Bones to Run"
        if (b.id === 'srefill') { bonesRefill(ctx); return; }                                                   // the "or spend bones" path
        if (b.id === 'rally') { ctx.showBanner('Crew rally lands with the war update -- solo march is live.', 2.0); return; }
        return;
      }
    }
    if (WM.march) return;                              // locked mid-march
    for (var pi = 0; pi < WM.wpins.length; pi++) { var pn = WM.wpins[pi];
      if (Math.hypot(px - pn.x, py - pn.y) <= pn.r) { WM.wsel = (WM.wsel === pn.terr ? null : pn.terr); return; } }
    WM.wsel = null;
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
    // AK-WARMAP 2026-07-03: a FULL population (~12 crews) packs a single ring too
    // tight, so SCATTER the pins across TWO concentric rings (inner + a half-step
    // staggered outer). Neighbors never share a ring => crests never overlap, even
    // at min zoom. <=6 crews still sit on one clean ring (unchanged look).
    var twoRing = n > 6, per = twoRing ? Math.ceil(n / 2) : n;
    for (var i = 0; i < n; i++) {
      var base = rivals[i];
      var onOuter = twoRing && (i % 2 === 1);
      var ringR = twoRing ? (onOuter ? TILE * 1.22 : TILE * 0.78) : ringG;
      var slot = twoRing ? (i >> 1) : i;               // index within this crew's ring
      var stag = onOuter ? (Math.PI / per) : 0;        // rotate the outer ring half a slot
      var ang = -Math.PI / 2 + (slot / per) * Math.PI * 2 + stag;  // start at top, spread evenly
      var px = sx(cxg + Math.cos(ang) * ringR), py = sy(cyg + Math.sin(ang) * ringR);
      var pr = clamp(15 * WM.scale, 11, 20), ac = base.accent || RED;
      // tether line back to the base
      g.save(); g.strokeStyle = 'rgba(192,57,43,.32)'; g.lineWidth = 1; g.setLineDash([4, 4]);
      g.beginPath(); g.moveTo(sx(cxg), sy(cyg)); g.lineTo(px, py); g.stroke(); g.restore();
      // crest chip -- the rival clan's REAL crest art, accent ring + glow
      drawCrest(g, px, py, pr, base.cls || base.faction || base.name, ac, true);
      // tier stars + Cinzel crew-name tag + trophies chip when known
      var st = ''; for (var s = 0; s < (base.tier || 1); s++) st += '★';
      label(g, st, px, py - pr - 6 * WM.scale, clamp(8 * WM.scale, 7, 11), GOLD, '800');
      var nm = String(base.name || 'Rival Crew');
      var nfs = clamp(9 * WM.scale, 8, 11), nph = Math.max(13, 14 * WM.scale);
      g.save(); g.font = '800 ' + nfs + 'px ' + FONT_H; g.textAlign = 'center';
      var tw = g.measureText(nm).width + 10;
      g.fillStyle = 'rgba(8,8,12,.82)'; rr(g, px - tw / 2, py + pr + 3 * WM.scale, tw, nph, 3); g.fill();
      g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.3)'; g.stroke();
      g.restore();
      labelH(g, nm, px, py + pr + 3 * WM.scale + nph / 2, nfs, '#f0d98a', '800');
      if (base.trophies) drawTrophyChip(g, px, py + pr + 3 * WM.scale + nph + 10 * WM.scale, base.trophies, clamp(8 * WM.scale, 7, 10));
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
    var cd = contentDims(), pad = 46;
    WM.fitScale = Math.min((vp.w - pad * 2) / cd.w, (vp.h - 150) / cd.h);
    WM.scale = WM.fitScale;
    WM.cam.x = (vp.w - cd.w * WM.scale) / 2;
    WM.cam.y = (vp.h - cd.h * WM.scale) / 2 - 8;
  }
  function clampCam(vp) {
    var cd = contentDims(), gw = cd.w * WM.scale, gh = cd.h * WM.scale, pad = 90;
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
    // district background -- the painted districtBg art, COVER-FIT (no squash), else the tint
    var bg = DBG[z.id] ? img('assets/hub/' + DBG[z.id] + '_bg.png') : null;
    g.globalAlpha = z.locked ? 0.32 : 1;
    if (!drawCover(g, bg, X, Y, S, S)) { var c = z.tint || [12, 12, 18]; g.fillStyle = 'rgb(' + c[0] + ',' + c[1] + ',' + c[2] + ')'; g.fillRect(X, Y, S, S); }
    g.globalAlpha = 1;
    // legibility pass: matte darken + a top band for the nameplate
    if (!z.locked) {
      g.fillStyle = 'rgba(6,6,10,.22)'; g.fillRect(X, Y, S, S);
      var tb = g.createLinearGradient(0, Y, 0, Y + S * 0.26);
      tb.addColorStop(0, 'rgba(4,4,8,.74)'); tb.addColorStop(1, 'rgba(4,4,8,0)');
      g.fillStyle = tb; g.fillRect(X, Y, S, S * 0.26);
    }
    if (z.locked) { g.fillStyle = 'rgba(6,6,10,.62)'; g.fillRect(X, Y, S, S); }
    g.restore();

    // tile frame + perimeter "wall" feel (gold-glow highlight on YOUR district)
    g.save();
    rr(g, X, Y, S, S, 12 * WM.scale);
    g.lineWidth = Math.max(2, WALL * 0.5 * WM.scale);
    g.strokeStyle = z.locked ? 'rgba(120,120,130,.5)' : (z.id === WM.ctx.zoneId ? GOLD : 'rgba(201,168,76,.42)');
    if (z.id === WM.ctx.zoneId) { g.shadowColor = GOLD; g.shadowBlur = 22; }
    g.stroke();
    g.restore();

    // district nameplate (Cinzel gold) + the owning crew's crest badge
    labelH(g, z.name, X + S / 2, Y + 13 * WM.scale, clamp(13 * WM.scale, 9, 15), z.locked ? '#9a9aa6' : GOLD, '800');
    if (!z.locked) drawCrest(g, X + 15 * WM.scale, Y + 14 * WM.scale, clamp(9 * WM.scale, 7, 13), playerCrestKey(ctx), (z.id === WM.ctx.zoneId) ? GOLD : GOLD_D, z.id === WM.ctx.zoneId);

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
    // top title -- matte plate + gold hairline + Cinzel wordmark
    g.fillStyle = 'rgba(8,8,12,.86)'; g.fillRect(0, 0, vp.w, 50);
    g.fillStyle = 'rgba(201,168,76,.45)'; g.fillRect(0, 49, vp.w, 1);
    labelH(g, WM.editMode ? 'REBUILD YOUR BASE' : 'YOUR TERRITORY', 14, 24, 16, GOLD, '900', 'left');
    label(g, WM.editMode ? 'drag a building to a new spot · snaps to grid'
      : (liveTerritoryCount(ctx) + ' districts held'), 14, 41, 11, DIM, '700', 'left');
    // close (x)
    var cb = { id:'close', x: vp.w - 50, y: 8, w: 38, h: 34 };
    g.save(); rr(g, cb.x, cb.y, cb.w, cb.h, 3); g.fillStyle = 'rgba(255,255,255,.06)'; g.fill();
    g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.3)'; g.stroke(); g.restore();
    label(g, '×', cb.x + cb.w / 2, cb.y + cb.h / 2, 24, '#ccc', '700'); WM.btns.push(cb);
    // (B) REARRANGE / LOCK IN toggle (top bar, left of close)
    var eb = { id:'edit', x: vp.w - 50 - 12 - 116, y: 8, w: 116, h: 34 };
    g.save(); rr(g, eb.x, eb.y, eb.w, eb.h, 3);
    if (WM.editMode) { var grd0 = g.createLinearGradient(0, eb.y, 0, eb.y + eb.h); grd0.addColorStop(0, GOLD); grd0.addColorStop(1, GOLD_D); g.fillStyle = grd0; g.fill(); }
    else { g.fillStyle = 'rgba(201,168,76,.10)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,.5)'; g.lineWidth = 1; g.stroke(); }
    g.restore();
    label(g, WM.editMode ? '✓ LOCK IN' : '✛ REARRANGE', eb.x + eb.w / 2, eb.y + eb.h / 2, 12, WM.editMode ? '#15110a' : GOLD, '900'); WM.btns.push(eb);
    if (!WM.editMode) drawStaminaPill(g, vp, 12, 56);   // P4 "Bones to Run": pool + regen by the rival raid pins

    // bottom action bar
    var barY = vp.h - 78;
    g.fillStyle = 'rgba(8,8,12,.9)'; g.fillRect(0, barY, vp.w, 78);
    g.strokeStyle = 'rgba(201,168,76,.25)'; g.lineWidth = 1; g.beginPath(); g.moveTo(0, barY); g.lineTo(vp.w, barY); g.stroke();

    if (WM.editMode) {                                  // (B) edit-mode bar
      labelH(g, 'EDIT MODE', 16, barY + 22, 13, GOLD, '800', 'left');
      label(g, 'Buildings stay in their district. Green = OK, red = blocked.', 16, barY + 44, 11, DIM, '700', 'left');
      var rsb = { id:'reset', x: vp.w - 150, y: barY + 18, w: 134, h: 42 };
      g.save(); rr(g, rsb.x, rsb.y, rsb.w, rsb.h, 3); g.fillStyle = 'rgba(255,255,255,.05)';
      g.fill(); g.strokeStyle = 'rgba(201,168,76,.4)'; g.lineWidth = 1; g.stroke(); g.restore();
      label(g, '↺ RESET LAYOUT', rsb.x + rsb.w / 2, barY + 39, 11, GOLD, '800'); WM.btns.push(rsb);
      return;
    }

    var z = WM.sel ? ctx.ZONES[WM.sel] : null;
    if (z) {
      labelH(g, z.name, 16, barY + 22, 13, z.locked ? '#9a9aa6' : GOLD, '800', 'left');
      var sub = z.locked ? (z.barrierLabel || 'SEALED -- soon')
        : ((z.buildings ? z.buildings.length : 0) + ' buildings  ·  ' + (z.id === ctx.zoneId ? 'you are here' : 'tap DIVE IN to walk it'));
      label(g, sub, 16, barY + 44, 11, DIM, '700', 'left');
      if (!z.locked && z.id !== ctx.zoneId) {
        var db = { id:'dive', z:z.id, x: vp.w - 150, y: barY + 18, w: 134, h: 42 };
        g.save(); rr(g, db.x, db.y, db.w, db.h, 3);
        var grd = g.createLinearGradient(0, db.y, 0, db.y + db.h); grd.addColorStop(0, GOLD); grd.addColorStop(1, GOLD_D);
        g.fillStyle = grd; g.fill(); g.restore();
        label(g, 'DIVE IN ▸', db.x + db.w / 2, db.y + db.h / 2, 14, '#15110a', '900'); WM.btns.push(db);
      } else if (!z.locked && z.id === ctx.zoneId) {
        label(g, 'YOU ARE HERE', vp.w - 16, barY + 36, 12, GOLD, '800', 'right');
      }
    } else {
      label(g, 'Tap a district to inspect · drag to pan, pinch to zoom', 16, barY + 26, 12, DIM, '700', 'left');
      label(g, 'Zoom out again -> the WAR MAP, where your crew marches on rivals.', 16, barY + 48, 10, '#7a7468', '700', 'left');
      // WORLD WAR MAP -> the Dark War strategic tier (#3, second zoom-out step)
      var wb = { id:'world', x: vp.w - 150, y: barY + 8, w: 134, h: 32 };
      g.save(); rr(g, wb.x, wb.y, wb.w, wb.h, 3);
      var wgr = g.createLinearGradient(0, wb.y, 0, wb.y + wb.h); wgr.addColorStop(0, GOLD); wgr.addColorStop(1, GOLD_D);
      g.fillStyle = wgr; g.fill(); g.restore();
      label(g, '⚔️ WORLD WAR MAP', wb.x + wb.w / 2, wb.y + wb.h / 2, 12, '#15110a', '900'); WM.btns.push(wb);
      // (A) SCOUT RIVALS -> raid.js war map if loaded, else a heads-up
      var live = !!(global.AKRaid && global.AKRaid.warMap);
      var rb = { id:'rivals', x: vp.w - 150, y: barY + 44, w: 134, h: 28 };
      g.save(); rr(g, rb.x, rb.y, rb.w, rb.h, 3);
      if (live) { g.fillStyle = 'rgba(192,57,43,.18)'; g.fill(); g.strokeStyle = 'rgba(192,57,43,.6)'; g.lineWidth = 1.2; g.stroke(); }
      else { g.fillStyle = 'rgba(255,255,255,.05)'; g.fill(); g.strokeStyle = 'rgba(201,168,76,.3)'; g.lineWidth = 1; g.stroke(); }
      g.restore();
      label(g, '☠ SCOUT RIVALS', rb.x + rb.w / 2, rb.y + rb.h / 2, 10, live ? '#f3a0a0' : GOLD, '800'); WM.btns.push(rb);
    }
  }

  // ---- frame ----
  function drawFrame(g, dt, vp, ctx) {
    if (WM.tier === 'world') { drawWorldFrame(g, dt, vp, ctx); return; }   // DARK WAR strategic tier
    g.fillStyle = INK; g.fillRect(0, 0, vp.w, vp.h);
    // faint backdrop grid
    g.save(); g.strokeStyle = 'rgba(201,168,76,.05)'; g.lineWidth = 1;
    for (var x = (WM.cam.x % 60); x < vp.w; x += 60) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, vp.h); g.stroke(); }
    for (var y = (WM.cam.y % 60); y < vp.h; y += 60) { g.beginPath(); g.moveTo(0, y); g.lineTo(vp.w, y); g.stroke(); }
    g.restore();
    // matte grain finish (cached pattern, built once)
    var gp1 = grainPat(g);
    if (gp1) { g.save(); g.globalAlpha = 0.55; g.fillStyle = gp1; g.fillRect(0, 0, vp.w, vp.h); g.restore(); }
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
    if (WM.tier === 'world') { handleWorldTap(px, py, api); return; }   // DARK WAR strategic tier
    var ctx = WM.ctx;
    // HUD buttons first
    for (var i = 0; i < WM.btns.length; i++) {
      var b = WM.btns[i];
      if (px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h) {
        if (b.id === 'close') { api.close(); return; }
        if (b.id === 'world') { switchTier('world', api.vp);   // SECOND zoom-out step -> Dark War
          ctx.showBanner('Zooming out to the war map...', 1.2); return; }
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
          if (global.AKRaid && global.AKRaid.warMap) { api.close({ warmap: true }); return; }  // war map (raid.js gates its own launch)
          if (payRaidStamina(WM.ctx)) api.close({ raid: pn.base });                            // direct reward-raid -> costs "Bones to Run"
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

  function openMap(ctx, startTier) {
    WM.ctx = ctx; WM.sel = ctx.zoneId; WM.ptrs = {}; WM.pinch = null;
    WM.editMode = false; WM.drag = null; WM.pins = [];
    WM.tier = (startTier === 'world') ? 'world' : 'base';
    WM.wsel = null; WM.march = null; WM._api = null;
    try { applyLayout(ctx); } catch (_e0) {}    // mirror saved p.baseLayout onto the live building objects
    fetchRivals(ctx);                           // (A) kick off the ak-raid targets fetch (degrades to local)
    if (WM.tier === 'world') { try { placeTerritories(ctx); } catch (_pt) {} }  // (#3) build the war map
    var vp0 = { w: (typeof innerWidth !== 'undefined' ? innerWidth : 360), h: (typeof innerHeight !== 'undefined' ? innerHeight : 640) };
    fitToScreen(vp0);
    try {
      WM.ov = ctx.overlay.open({
        id: 'worldmap',
        onFrame: function (g, dt, vp, api) { WM._api = api; drawFrame(g, dt, vp, ctx); },  // capture api -> march closes through it
        onPointer: function (e, api) { try { onPointer(e, api); } catch (_e) {} },
        onClose: function (res) {
          WM.ov = null;
          if (WM.drag) { WM.drag.b.x = WM.drag.x0; WM.drag.b.y = WM.drag.y0; WM.drag = null; } // revert an in-flight drag
          if (!res) return;
          if (res.raidscene) { try { launchRaidScene(ctx, res.raidscene); } catch (_e) {} return; }  // (#3) crew-march handoff to Agent A
          if (res.dive && global.enterZone) { // host's own dive_in transition (S3); state is IN_ZONE again here
            // AK-TRANSIT-FARE 2026-06-25: fast-travel via the world map COSTS gold (Town Hall civic discount).
            // Walking the district edges on foot stays free; only the instant jump charges a fare.
            if (res.dive !== ctx.zoneId) {
              var _ec = ctx.econ, _pp = _ec ? _ec.loadProfile() : null;
              var _th = (_ec && _ec.townHallLevel) ? _ec.townHallLevel() : 1;
              var _fare = Math.max(8, Math.round(30 * (1 - Math.min(0.5, (_th - 1) * 0.05))));
              if (!_pp || ((_pp.coins | 0) < _fare)) { try { ctx.showBanner && ctx.showBanner('NEED ' + _fare + ' GOLD FOR THE FARE -- walk there free', 1.8); } catch (_b) {} return; }
              try { _ec.mutateProfile(function (p) { p.coins = Math.max(0, (p.coins | 0) - _fare); }); } catch (_m) {}
              try { ctx.showBanner && ctx.showBanner('\u{1F68D} Transit fare -' + _fare + 'g', 1.4); } catch (_b2) {}
            }
            try { global.enterZone(res.dive, { x: ZW / 2, y: ZH / 2 }); } catch (_e) {} return;
          }
          if (res.warmap) { try { if (global.AKRaid && global.AKRaid.warMap) global.AKRaid.warMap(); } catch (_e) {} return; }
          if (res.raid)   { try { raidFrom(ctx, res.raid); } catch (_e) {} return; }
        }
      });
    } catch (_e) { WM.ov = null; }
  }
  // open straight into the Dark War strategic tier (for a future dedicated host button)
  function openWorld(ctx) { openMap(ctx || WM.ctx, 'world'); }

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
        // war-map art layer: faction crests + trophy + currency chips (loaded once)
        img('assets/ui/Crest_Boneguard.jpg'); img('assets/ui/Crest_Zoomie.jpg');
        img('assets/ui/Crest_K9.jpg'); img('assets/ui/Crest_Leashbreak.jpg');
        img('assets/hub/trophy.png');
        for (var lk in LOOT_ICON) if (LOOT_ICON.hasOwnProperty(lk)) img('assets/icons/' + LOOT_ICON[lk] + '.png');
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

  /* ---- public API (host buttons) + test seams (node harness) ------------- */
  global.AKWorldMap = {
    open:      function (ctx) { openMap(ctx || WM.ctx, 'base'); },   // base territory view
    // --- P4 RAID STAMINA "Bones to Run" (the gated reward-raid entry) -------
    // raidStamina(): live pool { cur,raw,max,full,regenMs,nextInMs,fullInMs } | null when econ stamina API absent
    raidStamina: function () { return staminaRead(); },
    // tryRaid(ctx): THE gate -- spends 1 stamina + returns true if a reward-raid may launch;
    //   false + "rest up -- N min or spend bones" banner when empty; true (no-op) if econ absent. NEVER gems.
    tryRaid:     function (ctx) { return payRaidStamina(ctx || WM.ctx); },
    // refillRaidStamina(ctx): the "or spend bones" path -- soft-currency refill only (econ refuses gems)
    refillRaidStamina: function (ctx) { return bonesRefill(ctx || WM.ctx); },
    openWorld: function (ctx) { openWorld(ctx || WM.ctx); },          // straight to the Dark War map
    isOpen:    function () { return !!WM.ov; },
    // --- AK-HARVEST 2026-07-18: ground loot -> materials -> fence tiers ----
    // Same handles as window.AK_HARVEST (that one exports pre-guard so it lives
    // headless too); mirrored here so the hub can reach the loop off one global.
    nodesFor:      nodesFor,
    harvestNode:   harvest,
    harvestNear:   nodeNear,
    FENCE_TIERS:   FENCE_TIERS,
    fenceUpgrade:  fenceUpgrade,
    // --- seams used by tests/worldmap_darkwar_harness.js (no DOM needed) ---
    _state:        WM,
    _targets:      function (ctx) { return worldTargets(ctx || WM.ctx); },
    _placeTerritories: function (ctx) { return placeTerritories(ctx || WM.ctx); },
    _normalize:    function (ctx, t) { return normalizeTarget(ctx || WM.ctx, t); },
    _toTarget:     function (ctx, b) { return toRaidTarget(ctx || WM.ctx, b); },
    _buildLayout:  buildLayout,
    _launch:       function (ctx, t) { return launchRaidScene(ctx || WM.ctx, t); },
    _startMarch:   function (ctx, terr, api) { return startMarch(ctx || WM.ctx, terr, api); },
    _switchTier:   switchTier
  };

})(typeof window !== 'undefined' ? window : globalThis);
