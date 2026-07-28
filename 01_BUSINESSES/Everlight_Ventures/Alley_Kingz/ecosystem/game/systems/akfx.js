/*
 * akfx.js -- AK_FX
 * Reusable, dependency-free Canvas2D effects for Alley Kingz.
 * Mirrors the frozen tower-lane EVO killstreak look so the hero ALWAYS
 * renders the advanced aura, and the kill-streak FX can fire ANYWHERE
 * (raids, hub, any canvas mode), not just the tower-lane engine.
 *
 * Pure. No external deps. No ES modules. 60fps-friendly on cheap Android.
 * Fully guarded: never throws if args are missing.
 *
 * Public API:
 *   AK_FX.tier(kills)                         -> int 0..4
 *   AK_FX.tierName(kills)                      -> string ('' for tier 0)
 *   AK_FX.tierColor(kills)                     -> hex string
 *   AK_FX.drawAura(g, x, y, r, kills, t)       -> always-on pulsing aura
 *   AK_FX.spawnHit(list, x, y, color, n)       -> push n hit sparks (world)
 *   AK_FX.spawnTierUp(list, x, y, kills)       -> celebratory burst + text
 *   AK_FX.stepDraw(g, list, dt, toX, toY)      -> step, draw, splice dead
 *   AK_FX.LOW                                  -> bool reduced-motion path
 *
 *   --- raid hero ARSENAL (Mobile-Legends-style multi-ability kit) ---
 *   AK_FX.ARSENAL                                          -> ability data table
 *   AK_FX.castSpell(g, kind, x1,y1, x2,y2, color, t)       -> in-flight/impact VFX (screen)
 *   AK_FX.spawnSpellParticles(list, kind, x, y, color, n)  -> push impact sparks (world)
 *     kind in {bolt, beam, nova, nuke, chain, dot}; t = cast progress 0..1.
 */
(function (global) {
  'use strict';

  // --- killstreak tier table (matches frozen engine.js EVO system) ---
  var THRESH = [0, 2, 4, 6, 8];
  var NAMES = ['', 'ADVANCED', 'EXCELLENT', 'SUPREME', 'DOG GOD'];
  var COLORS = ['#c9a84c', '#ffe7a0', '#6fe0ff', '#ff8af0', '#ffd24a'];
  var TAU = Math.PI * 2;
  var CROWN = '♛'; // chess black queen / crown glyph
  var GOLD = '#D4AF37'; // brand gold default (PAL.gold)

  // --- CARD IDENTITY tables (mirror the frozen tower renderer, engine.js +
  //     game.html drawUnit). These reproduce the EXACT always-on card look the
  //     operator loves: faction tint + rarity sheen + role-shape outline. Kept
  //     inline so akfx stays dependency-free (never reaches into engine.js). ---
  // faction base tint -> the aura color (engine.js FACTION_PAL[].base / FACTION_COL)
  var FAC_COL = {
    boneguard_crew:   '#C9772E', // amber / brick   (bruiser)
    zoomie_syndicate: '#FF2E88', // hot magenta      (sprinter)
    leashbreak_tactix:'#7B5CFF', // violet           (tech-ops)
    k9_circuitry:     '#00E0C0'  // teal / chrome    (turret-util)
  };
  // rarity frame color -> the sheen-ring color (engine.js RARITY_COL)
  var RAR_COL = {
    Mythic:'#D4AF37', Legendary:'#E6B800', Epic:'#C1440E', Rare:'#00BFFF', Common:'#4A4A55'
  };
  // rarity aura amplitude -> glow intensity (game.html RAR_AURA)
  var RAR_AMP = {
    Common:0.12, Rare:0.18, Epic:0.24, Legendary:0.32, Mythic:0.36
  };
  // role -> token silhouette shape (game.html ROLE_SHAPE)
  var ROLE_SHAPE = {
    Striker:'circle', Skirmisher:'circle', Vanguard:'shield', Assassin:'triangle',
    Spawner:'square', Support:'hexagon', Lancer:'diamond', Controller:'hexagon',
    Hacker:'octagon', Blaster:'diamond', Structure:'square', Spell:'diamond'
  };
  // range-class lane -> outline color (game.html CLASS_OUTLINE_LOCAL)
  var CLASS_OUTLINE = {
    melee:'#FF6B4A', brawler:'#FFC246', mid:'#46C8FF', long:'#B07BFF', siege:'#FF4FD8'
  };

  function clamp01(v) {
    return v < 0 ? 0 : (v > 1 ? 1 : v);
  }

  // deterministic FNV-1a-ish hash (mirrors engine.js hashStr) for the seed
  // fallback so a card with no silhouetteSeed still gets a stable pulse offset.
  function hashStr(s) {
    var h = 2166136261 >>> 0;
    s = String(s || '');
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h >>> 0;
  }

  // 0..1 alpha -> 2-char hex byte for `#rrggbb` + AA concat (matches drawAura)
  function aHex(v) {
    v = clamp01(v);
    var s = Math.round(v * 255).toString(16);
    return s.length < 2 ? '0' + s : s;
  }

  // 1. highest threshold index where (kills|0) >= threshold
  function tier(kills) {
    var k = kills | 0;
    var ti = 0;
    for (var i = 0; i < THRESH.length; i++) {
      if (k >= THRESH[i]) { ti = i; }
    }
    return ti;
  }

  // 2. tier name string
  function tierName(kills) {
    return NAMES[tier(kills)] || '';
  }

  // 3. tier hex color string
  function tierColor(kills) {
    return COLORS[tier(kills)] || COLORS[0];
  }

  // 4. always-on pulsing aura at SCREEN coords (x,y), base radius r.
  //    t = time-in-seconds float. Tier 0 = subtle gold halo (never bare).
  function drawAura(g, x, y, r, kills, t) {
    if (!g) { return; }
    x = +x || 0;
    y = +y || 0;
    r = +r || 0;
    t = +t || 0;
    if (r <= 0) { r = 16; }

    var ti = tier(kills);
    var col = COLORS[ti] || COLORS[0];
    var pulse = 0.5 + 0.5 * Math.sin(t * 3 + ti); // 0..1

    g.save();

    // base halo -- the ONE radial gradient allocated this call
    var haloR = r * (1.5 + 0.25 * pulse + ti * 0.15);
    var grad = g.createRadialGradient(x, y, r * 0.2, x, y, haloR);
    var innerA = ti === 0 ? '40' : '70';
    var midA = ti === 0 ? '14' : '2a';
    grad.addColorStop(0, col + innerA);
    grad.addColorStop(0.55, col + midA);
    grad.addColorStop(1, col + '00');
    g.fillStyle = grad;
    g.beginPath();
    g.arc(x, y, haloR, 0, TAU);
    g.fill();

    // reduced-motion / tier 0: just the subtle halo
    if (ti === 0 || API.LOW) {
      g.restore();
      return;
    }

    // glowing pulsing ring
    g.lineWidth = 2 + ti * 0.6;
    g.strokeStyle = col;
    g.globalAlpha = 0.5 + 0.4 * pulse;
    g.beginPath();
    g.arc(x, y, r * (1.15 + 0.05 * pulse), 0, TAU);
    g.stroke();
    g.globalAlpha = 1;

    // ti*2 orbiting spark dots
    var dots = ti * 2;
    var orbitR = r * 1.35;
    var dotR = 2 + ti * 0.3;
    for (var i = 0; i < dots; i++) {
      var a = t * 2 + (i / dots) * TAU;
      var dx = x + Math.cos(a) * orbitR;
      var dy = y + Math.sin(a) * orbitR;
      g.globalAlpha = 0.7 + 0.3 * Math.sin(t * 4 + i);
      g.fillStyle = col;
      g.beginPath();
      g.arc(dx, dy, dotR, 0, TAU);
      g.fill();
    }
    g.globalAlpha = 1;

    // DOG GOD spectacle: second outer ring + crown glyph above the unit
    if (ti >= 4) {
      g.strokeStyle = col + '88';
      g.lineWidth = 1.5;
      g.globalAlpha = 0.6 + 0.4 * pulse;
      g.beginPath();
      g.arc(x, y, r * (1.7 + 0.08 * pulse), 0, TAU);
      g.stroke();

      g.globalAlpha = 0.85 + 0.15 * pulse;
      g.fillStyle = col;
      g.font = 'bold ' + Math.max(12, Math.round(r * 0.9)) + 'px serif';
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.fillText(CROWN, x, y - r * 1.7);
      g.globalAlpha = 1;
    }

    g.restore();
  }

  // 4b. CARD IDENTITY FX -- the ALWAYS-ON "premium card" look the tower engine
  //     draws around every unit (faction tint + rarity sheen + role-shape
  //     outline + mythic crown). Separate from drawAura's killstreak tiers.
  //     Accepts a canon card (factionId/rarity/role) OR an engine card
  //     (faction/palette). null card -> brand-gold default.

  // range-class lane from a card's range (mirrors game.html unitClassOf)
  function classLaneOf(card) {
    if (!card) { return 'mid'; }
    if (card.role === 'Structure') { return 'siege'; }
    var rg = +card.range || 1;
    if (rg <= 1.3) { return 'melee'; }
    if (rg <= 2.0) { return 'brawler'; }
    if (rg <= 5.0) { return 'mid'; }
    return 'long';
  }

  // the ONE identity color for a card (faction first, then rarity, then gold).
  // Callers tint other things (UI chrome, trails) with this to match the hero.
  function cardFxColor(card) {
    if (!card) { return GOLD; }
    if (card.palette && card.palette.base) { return card.palette.base; } // engine card
    var fid = card.factionId || card.faction;
    if (fid && FAC_COL[fid]) { return FAC_COL[fid]; }
    if (card.color) { return card.color; }
    if (card.rarity && RAR_COL[card.rarity]) { return RAR_COL[card.rarity]; }
    if (card.accent) { return card.accent; }
    return GOLD;
  }

  // resolve the full FX param set for a card (no allocation hot path: object is
  // tiny + short-lived; called once per drawCardFx, not per primitive).
  function cardFxInfo(card) {
    var rar = (card && card.rarity) || null;
    var seed = (card && (card.silhouetteSeed != null
      ? (card.silhouetteSeed >>> 0)
      : hashStr(card.name || card.cardNumber || ''))) || 0;
    return {
      fac: cardFxColor(card),
      rarCol: (rar && RAR_COL[rar]) || GOLD,
      amp: (rar && RAR_AMP[rar]) || 0.14,
      isMythic: !!(card && (card.isMythic || rar === 'Mythic')),
      shape: (card && card.tokenShape) || (card && ROLE_SHAPE[card.role]) || 'circle',
      clsCol: CLASS_OUTLINE[classLaneOf(card)] || CLASS_OUTLINE.mid,
      seed: seed
    };
  }

  // closed path for a role token shape in LOCAL space (mirror of game.html
  // shapePath). No array allocation -- math in a tight loop. Caller strokes.
  function shapePath(g, shape, r) {
    g.beginPath();
    var k, a;
    switch (shape) {
      case 'shield':
        g.moveTo(-r * 0.95, -r * 0.72); g.lineTo(r * 0.95, -r * 0.72);
        g.lineTo(r * 0.88, r * 0.30); g.lineTo(0, r * 1.0);
        g.lineTo(-r * 0.88, r * 0.30); g.closePath(); break;
      case 'triangle':
        g.moveTo(0, -r * 1.05); g.lineTo(r * 0.92, r * 0.62);
        g.lineTo(-r * 0.92, r * 0.62); g.closePath(); break;
      case 'square':
        g.moveTo(-r * 0.88, -r * 0.88); g.lineTo(r * 0.88, -r * 0.88);
        g.lineTo(r * 0.88, r * 0.88); g.lineTo(-r * 0.88, r * 0.88); g.closePath(); break;
      case 'hexagon':
        for (k = 0; k < 6; k++) { a = Math.PI / 6 + k * Math.PI / 3; if (k) { g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } else { g.moveTo(Math.cos(a) * r, Math.sin(a) * r); } }
        g.closePath(); break;
      case 'diamond':
        g.moveTo(0, -r * 1.08); g.lineTo(r * 0.78, 0);
        g.lineTo(0, r * 1.08); g.lineTo(-r * 0.78, 0); g.closePath(); break;
      case 'octagon':
        for (k = 0; k < 8; k++) { a = Math.PI / 8 + k * Math.PI / 4; if (k) { g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } else { g.moveTo(Math.cos(a) * r, Math.sin(a) * r); } }
        g.closePath(); break;
      default: // circle
        g.arc(0, 0, r, 0, TAU); break;
    }
  }

  // draw the tower-game card identity around a unit at SCREEN coords (x,y),
  // base radius r, t = seconds. Cheap: 1 radial gradient, no per-frame arrays.
  function drawCardFx(g, x, y, r, card, t) {
    if (!g) { return; }
    x = +x || 0;
    y = +y || 0;
    r = +r || 0;
    t = +t || 0;
    if (r <= 0) { r = 16; }

    var fx = cardFxInfo(card);
    var pulse = 0.5 + 0.5 * Math.sin(t * 2.1 + (fx.seed % 7)); // breathing, mirrors tower /300ms

    g.save();

    // 1) FACTION AURA -- the ONE radial gradient (mirrors game.html RAR_AURA glow).
    //    intensity scales with rarity (amp), breathes with pulse.
    var auraR = r * (1.40 + 0.06 * pulse);
    var baseA = fx.amp * (0.65 + 0.35 * pulse);
    var grad = g.createRadialGradient(x, y, r * 0.25, x, y, auraR);
    grad.addColorStop(0, fx.fac + aHex(baseA * 1.6));
    grad.addColorStop(0.6, fx.fac + aHex(baseA * 0.7));
    grad.addColorStop(1, fx.fac + '00');
    g.fillStyle = grad;
    g.beginPath();
    g.arc(x, y, auraR, 0, TAU);
    g.fill();

    // reduced-motion: aura + a single rarity sheen ring, no spin/dots/blur.
    if (API.LOW) {
      g.lineWidth = (r * 0.07 > 1) ? r * 0.07 : 1;
      g.strokeStyle = fx.rarCol;
      g.globalAlpha = 0.55;
      g.beginPath();
      g.arc(x, y, r * 1.32, 0, TAU);
      g.stroke();
      g.globalAlpha = 1;
      g.restore();
      return;
    }

    // 2) CLASS-OUTLINE SHAPE RING -- the role's token silhouette, slowly spinning.
    //    This is the "shape identity" the tower draws as the class outline.
    g.save();
    g.translate(x, y);
    g.rotate(t * 0.5); // slow premium spin
    g.lineWidth = (r * 0.09 > 1.2) ? r * 0.09 : 1.2;
    g.strokeStyle = fx.clsCol;
    g.globalAlpha = 0.55 + 0.2 * pulse;
    g.shadowColor = fx.clsCol;
    g.shadowBlur = 6;
    shapePath(g, fx.shape, r * 1.15);
    g.stroke();
    g.restore();
    g.shadowBlur = 0;

    // 3) RARITY SHEEN RING -- stacked OUTSIDE, RARITY_COL (mirror r*1.32 ring)
    g.lineWidth = (r * 0.07 > 1) ? r * 0.07 : 1;
    g.strokeStyle = fx.rarCol;
    g.globalAlpha = 0.6 + 0.3 * pulse;
    g.shadowColor = fx.rarCol;
    g.shadowBlur = 8;
    g.beginPath();
    g.arc(x, y, r * 1.32, 0, TAU);
    g.stroke();
    g.shadowBlur = 0;
    g.globalAlpha = 1;

    // 4) two faction-tinted accent dots orbiting the unit (subtle, always-on)
    var orbitR = r * 1.5;
    var dotR = (r * 0.10 > 1.5) ? r * 0.10 : 1.5;
    for (var i = 0; i < 2; i++) {
      var a = t * 1.2 + i * Math.PI;
      g.globalAlpha = 0.5 + 0.3 * Math.sin(t * 3 + i);
      g.fillStyle = fx.fac;
      g.beginPath();
      g.arc(x + Math.cos(a) * orbitR, y + Math.sin(a) * orbitR, dotR, 0, TAU);
      g.fill();
    }
    g.globalAlpha = 1;

    // 5) MYTHIC CROWN -- gold outer ring + crown glyph (mirror c.isMythic aura)
    if (fx.isMythic) {
      g.strokeStyle = GOLD;
      g.lineWidth = (r * 0.08 > 1.4) ? r * 0.08 : 1.4;
      g.globalAlpha = 0.45 + 0.35 * pulse;
      g.shadowColor = GOLD;
      g.shadowBlur = 12;
      g.beginPath();
      g.arc(x, y, r * 1.62, 0, TAU);
      g.stroke();
      g.shadowBlur = 0;
      g.globalAlpha = 0.85 + 0.15 * pulse;
      g.fillStyle = GOLD;
      g.font = 'bold ' + Math.max(11, Math.round(r * 0.85)) + 'px serif';
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.fillText(CROWN, x, y - r * 1.78);
      g.globalAlpha = 1;
    }

    g.restore();
  }

  // 5. push n hit-spark particles into `list` at WORLD coords (x,y)
  function spawnHit(list, x, y, color, n) {
    if (!list || typeof list.push !== 'function') { return; }
    x = +x || 0;
    y = +y || 0;
    n = (n | 0) || 6;
    color = color || '#ffd76b';
    for (var i = 0; i < n; i++) {
      var ang = Math.random() * TAU;
      var spd = 40 + Math.random() * 120;
      var life = 0.25 + Math.random() * 0.2; // ~0.35s
      list.push({
        x: x,
        y: y,
        vx: Math.cos(ang) * spd,
        vy: Math.sin(ang) * spd,
        life: life,
        maxLife: life,
        col: color,
        r: 1.5 + Math.random() * 2
      });
    }
  }

  // 6. celebratory tier-up burst (ring of ~14) + one rising text marker
  function spawnTierUp(list, x, y, kills) {
    if (!list || typeof list.push !== 'function') { return; }
    x = +x || 0;
    y = +y || 0;
    var col = tierColor(kills);
    var nm = tierName(kills);
    var ring = 14;
    for (var i = 0; i < ring; i++) {
      var a = (i / ring) * TAU;
      var spd = 90 + Math.random() * 60;
      var life = 0.5 + Math.random() * 0.3;
      list.push({
        x: x,
        y: y,
        vx: Math.cos(a) * spd,
        vy: Math.sin(a) * spd,
        life: life,
        maxLife: life,
        col: col,
        r: 2 + Math.random() * 2
      });
    }
    // rising text marker
    list.push({
      text: nm,
      rise: true,
      life: 1.1,
      maxLife: 1.1,
      col: col,
      x: x,
      y: y,
      vx: 0,
      vy: -40
    });
  }

  // 7. advance + draw + splice particles. toX/toY map world->screen.
  //    If toX/toY are not functions, coords are treated as screen-space.
  function stepDraw(g, list, dt, toX, toY) {
    if (!list || !list.length) { return; }
    dt = +dt || 0;
    var hasTx = typeof toX === 'function';
    var hasTy = typeof toY === 'function';

    for (var i = list.length - 1; i >= 0; i--) {
      var p = list[i];
      if (!p) { list.splice(i, 1); continue; }

      if (p.rise) {
        // text marker floats upward, no gravity
        p.y += (p.vy || -40) * dt;
        p.life -= dt;
      } else {
        // spark: integrate with gravity
        p.x += (p.vx || 0) * dt;
        p.y += (p.vy || 0) * dt;
        p.vy = (p.vy || 0) + 320 * dt;
        p.life -= dt;
      }

      if (p.life <= 0) { list.splice(i, 1); continue; }
      if (!g) { continue; } // still step + splice without a context

      var sx = hasTx ? (+toX(p.x) || 0) : p.x;
      var sy = hasTy ? (+toY(p.y) || 0) : p.y;
      var a = clamp01(p.life / (p.maxLife || p.life || 1));

      if (p.rise) {
        g.save();
        g.globalAlpha = a;
        g.fillStyle = p.col || '#ffd24a';
        g.font = 'bold 16px sans-serif';
        g.textAlign = 'center';
        g.textBaseline = 'middle';
        g.fillText(String(p.text || ''), sx, sy);
        g.restore();
      } else {
        g.save();
        g.globalAlpha = a;
        g.fillStyle = p.col || '#ffd76b';
        g.beginPath();
        g.arc(sx, sy, p.r || 2, 0, TAU);
        g.fill();
        g.restore();
      }
    }
  }

  // ===================================================================
  //  RAID HERO ARSENAL -- a Mobile-Legends-style weapon/spell kit.
  //  Data-driven so the raid HUD can loop ARSENAL to build ability
  //  buttons, then call castSpell(kind) + spawnSpellParticles(kind).
  //  Gold-cyberpunk dog-gang voice. Balanced-ish: cheap bolt = low
  //  energy / near-zero cd; ultimate nuke = max energy / long cd.
  //    id     stable key for HUD / cooldown tracking
  //    name   on-brand display name
  //    kind   one of {bolt, beam, nova, nuke, chain, dot}
  //    color  brand-tied accent (drives VFX + button tint)
  //    energy mana cost
  //    cd     cooldown seconds
  //    dmg    hit value (dot = per-tick)
  //    range  reach in tiles
  //    blurb  HUD tooltip copy
  // ===================================================================
  // RAID REBALANCE (retune here): AoE (nova/nuke) trimmed in dmg + slowed so
  // the player must aim + pace instead of AoE-deleting a defended district on
  // cooldown; single-target (bolt/beam/chain) got a modest cd bump only, still
  // satisfying; dot left as pure chip. Nuke is a rare finisher, not spam.
  var ARSENAL = [
    { id: 'snap_shot', name: 'Snap Shot', kind: 'bolt', color: '#6fe0ff',
      energy: 10, cd: 0.75, dmg: 42, range: 6,   // cd 0.6 -> 0.75 (still near-zero tap)
      blurb: 'Quickdraw muzzle pop. Cheap chip, near-zero cooldown -- keep it tapping.' },
    { id: 'laser_leash', name: 'Laser Leash', kind: 'beam', color: '#FF2E88',
      energy: 30, cd: 5.0, dmg: 120, range: 8,   // cd 4.0 -> 5.0 (single-target, keep burst)
      blurb: 'Lock a chrome beam on one mark and melt it. Hold the line, hold the block.' },
    { id: 'shockwave_bark', name: 'Shockwave Bark', kind: 'nova', color: '#D4AF37',
      energy: 35, cd: 8.0, dmg: 60, range: 3,    // AoE: dmg 90 -> 60, cd 6.0 -> 8.0
      blurb: 'Point-blank gold boom. Clears the pile around you and staggers the swarm.' },
    { id: 'live_wire', name: 'Live Wire', kind: 'chain', color: '#00E0C0',
      energy: 40, cd: 9.0, dmg: 130, range: 7,   // cd 7.0 -> 9.0 (aim the bounce, keep dmg)
      blurb: 'Arc jumps mark to mark. Bunch them up and the whole crew lights up.' },
    { id: 'acid_spit', name: 'Acid Spit', kind: 'dot', color: '#9BE021',
      energy: 25, cd: 5.0, dmg: 24, range: 5,    // unchanged: stays as chip damage
      blurb: 'Hock a corrosive pool. Low hit, bleeds them out over time -- tag and move.' },
    { id: 'crown_nuke', name: 'Crown Nuke', kind: 'nuke', color: '#ffd24a',
      energy: 100, cd: 42.0, dmg: 360, range: 99,  // AoE ult: dmg 520 -> 360, cd 30.0 -> 42.0 (rare finisher)
      blurb: 'ULTIMATE. Drop the crown. Full-screen shockwave, kings only, once a fight.' }
  ];

  // normalize the cast-progress arg: 0..1, default full impact (1).
  function castP(t) {
    if (t === undefined || t === null) { return 1; }
    var p = +t;
    if (!(p >= 0)) { return 0; }
    return p > 1 ? 1 : p;
  }

  // draw the in-flight / impact visual for an ability `kind` at SCREEN coords,
  // from origin (x1,y1) toward / at target (x2,y2). t = cast progress 0..1
  // (host drives 0->1 over the cast window; defaults to full impact).
  // Cheap, save/restore wrapped, GPU-friendly (strokes/fills only). No-op on
  // falsy g. No per-frame array allocation.
  function castSpell(g, kind, x1, y1, x2, y2, color, t) {
    if (!g) { return; }
    kind = kind || 'bolt';
    x1 = +x1 || 0; y1 = +y1 || 0; x2 = +x2 || 0; y2 = +y2 || 0;
    color = color || GOLD;
    var p = castP(t);
    var dx = x2 - x1, dy = y2 - y1;
    var dist = Math.sqrt(dx * dx + dy * dy) || 1;

    g.save();
    g.lineCap = 'round';
    g.lineJoin = 'round';

    switch (kind) {
      case 'beam': {
        // thick beam: wide faint glow -> mid -> white-hot core + muzzle flare
        g.strokeStyle = color;
        g.shadowColor = color;
        g.shadowBlur = 14;
        g.globalAlpha = 0.30;
        g.lineWidth = 12;
        g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
        g.globalAlpha = 0.6;
        g.lineWidth = 5;
        g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
        g.shadowBlur = 0;
        g.strokeStyle = '#ffffff';
        g.globalAlpha = 0.95;
        g.lineWidth = 1.6;
        g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
        g.fillStyle = color; g.globalAlpha = 0.5;
        g.beginPath(); g.arc(x1, y1, 7, 0, TAU); g.fill();
        break;
      }
      case 'nova': {
        // expanding ring at origin, fades as it grows
        var nr = dist * (0.2 + 0.8 * p);
        var na = clamp01(0.15 + 0.7 * (1 - p));
        g.strokeStyle = color;
        g.shadowColor = color;
        g.shadowBlur = 12;
        g.globalAlpha = na;
        g.lineWidth = 3 + 4 * (1 - p);
        g.beginPath(); g.arc(x1, y1, nr, 0, TAU); g.stroke();
        g.globalAlpha = clamp01(na * 0.6);
        g.lineWidth = 2;
        g.beginPath(); g.arc(x1, y1, nr * 0.6, 0, TAU); g.stroke();
        break;
      }
      case 'nuke': {
        // big shockwave + white flash ring (the ULTIMATE)
        var kmax = dist > 120 ? dist : 120;
        var kr = kmax * (0.15 + 0.85 * p);
        var fa = clamp01(0.8 * (1 - p));
        var flashR = kr * 0.7;
        var grad = g.createRadialGradient(x1, y1, 0, x1, y1, flashR);
        grad.addColorStop(0, '#ffffff' + aHex(fa));
        grad.addColorStop(0.4, color + aHex(fa * 0.7));
        grad.addColorStop(1, color + '00');
        g.fillStyle = grad;
        g.beginPath(); g.arc(x1, y1, flashR, 0, TAU); g.fill();
        g.strokeStyle = color;
        g.shadowColor = color;
        g.shadowBlur = 16;
        g.globalAlpha = clamp01(0.12 + 0.6 * (1 - p));
        g.lineWidth = 5 + 6 * (1 - p);
        g.beginPath(); g.arc(x1, y1, kr, 0, TAU); g.stroke();
        g.globalAlpha = clamp01(0.08 + 0.4 * (1 - p));
        g.lineWidth = 3;
        g.beginPath(); g.arc(x1, y1, kr * 0.55, 0, TAU); g.stroke();
        break;
      }
      case 'chain': {
        // jagged lightning polyline (built once, stroked twice: glow + core).
        // no array alloc -- lineTo straight into the path in a tight loop.
        var nx = -dy / dist, ny = dx / dist;
        var segs = 8;
        g.beginPath();
        g.moveTo(x1, y1);
        for (var ci = 1; ci < segs; ci++) {
          var cf = ci / segs;
          var amp = 12 * Math.sin(cf * Math.PI); // bulge in the middle
          var jit = Math.sin(ci * 2.3 + p * 18 + ci * ci * 0.7);
          g.lineTo(x1 + dx * cf + nx * jit * amp, y1 + dy * cf + ny * jit * amp);
        }
        g.lineTo(x2, y2);
        g.strokeStyle = color;
        g.shadowColor = color;
        g.shadowBlur = 10;
        g.globalAlpha = 0.35;
        g.lineWidth = 5;
        g.stroke();
        g.shadowBlur = 0;
        g.strokeStyle = '#ffffff';
        g.globalAlpha = 0.9;
        g.lineWidth = 1.6;
        g.stroke();
        g.fillStyle = color; g.globalAlpha = 0.8;
        g.beginPath(); g.arc(x2, y2, 3, 0, TAU); g.fill();
        break;
      }
      case 'dot': {
        // lingering corrosive ember puff at the target
        var cx = x2, cy = y2;
        var pr = 18;
        var dgrad = g.createRadialGradient(cx, cy, 0, cx, cy, pr);
        dgrad.addColorStop(0, color + aHex(0.45));
        dgrad.addColorStop(1, color + '00');
        g.fillStyle = dgrad;
        g.beginPath(); g.arc(cx, cy, pr, 0, TAU); g.fill();
        g.fillStyle = color;
        g.shadowColor = color;
        g.shadowBlur = 6;
        for (var di = 0; di < 4; di++) {
          var ph = p * 0.8 + di * 0.25;
          var fr = ph - Math.floor(ph); // 0..1 rise fraction
          g.globalAlpha = clamp01(0.6 * (1 - fr));
          g.beginPath();
          g.arc(cx + Math.sin(di * 2 + p * 3) * 6, cy - fr * 16, 2.2, 0, TAU);
          g.fill();
        }
        break;
      }
      default: {
        // bolt: glowing tracer with a travelling bright head
        var hx = x1 + dx * p, hy = y1 + dy * p;
        g.strokeStyle = color;
        g.shadowColor = color;
        g.shadowBlur = 10;
        g.globalAlpha = 0.35;
        g.lineWidth = 6;
        g.beginPath(); g.moveTo(x1, y1); g.lineTo(hx, hy); g.stroke();
        g.shadowBlur = 0;
        g.globalAlpha = 0.95;
        g.lineWidth = 2;
        g.beginPath(); g.moveTo(x1, y1); g.lineTo(hx, hy); g.stroke();
        g.fillStyle = '#ffffff';
        g.globalAlpha = 0.9;
        g.beginPath(); g.arc(hx, hy, 3.5, 0, TAU); g.fill();
        break;
      }
    }

    g.shadowBlur = 0;
    g.globalAlpha = 1;
    g.restore();
  }

  // push impact particles for an ability `kind` into the given WORLD-coord
  // particle array, reusing the exact spawnHit shape so stepDraw renders them.
  // n<=0 -> a sensible per-kind default. Hard-capped for 60fps on cheap Android.
  function spawnSpellParticles(list, kind, x, y, color, n) {
    if (!list || typeof list.push !== 'function') { return; }
    kind = kind || 'bolt';
    x = +x || 0;
    y = +y || 0;
    color = color || GOLD;
    n = n | 0;
    if (n <= 0) {
      n = (kind === 'nuke') ? 22
        : (kind === 'nova') ? 14
        : (kind === 'chain') ? 8
        : (kind === 'beam') ? 7
        : (kind === 'dot') ? 6
        : 5; // bolt
    }
    if (n > 28) { n = 28; } // particle budget cap

    var baseSpd, spread, life0, lift;
    switch (kind) {
      case 'nuke': baseSpd = 140; spread = 160; life0 = 0.55; lift = 0; break;
      case 'nova': baseSpd = 110; spread = 90; life0 = 0.45; lift = 0; break;
      case 'beam': baseSpd = 60; spread = 90; life0 = 0.30; lift = 0; break;
      case 'chain': baseSpd = 70; spread = 110; life0 = 0.30; lift = 0; break;
      case 'dot': baseSpd = 25; spread = 35; life0 = 0.70; lift = 20; break; // embers drift up
      default: baseSpd = 50; spread = 100; life0 = 0.30; lift = 0; break; // bolt
    }
    var ring = (kind === 'nova' || kind === 'nuke');
    var rBoost = (kind === 'nuke') ? 3 : 2;
    for (var i = 0; i < n; i++) {
      var ang = ring ? (i / n) * TAU : Math.random() * TAU;
      var spd = baseSpd + Math.random() * spread;
      var life = life0 + Math.random() * 0.2;
      list.push({
        x: x,
        y: y,
        vx: Math.cos(ang) * spd,
        vy: Math.sin(ang) * spd - lift,
        life: life,
        maxLife: life,
        col: color,
        r: 1.5 + Math.random() * rBoost
      });
    }
  }

  var API = {
    tier: tier,
    tierName: tierName,
    tierColor: tierColor,
    drawAura: drawAura,
    drawCardFx: drawCardFx,
    cardFxColor: cardFxColor,
    spawnHit: spawnHit,
    spawnTierUp: spawnTierUp,
    stepDraw: stepDraw,
    // raid hero arsenal (additive)
    ARSENAL: ARSENAL,
    castSpell: castSpell,
    spawnSpellParticles: spawnSpellParticles,
    // public tier table (read-only intent)
    THRESHOLDS: THRESH,
    TIER_NAMES: NAMES,
    TIER_COLORS: COLORS,
    // 8. reduced-motion / perf path toggle
    LOW: false
  };

  global.AK_FX = API;

})(typeof window !== 'undefined' ? window : globalThis);
