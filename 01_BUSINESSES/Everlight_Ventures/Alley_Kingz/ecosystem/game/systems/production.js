/* game/systems/production.js -- AK_SYSTEMS module: WAVE 1 "PRODUCTION".
   ------------------------------------------------------------------------
   Offline-accrual producer buildings (Clash builder huts x Sunflower gather).
   The 5 producer buildings accrue SOFT resources offline; their keeper lets
   you COLLECT the haul and UPGRADE the building (faster rate + bigger cap):

       GEM   "GEM MINE"      (FACTORY_ROW)  -> Rare scrap   (Prospector Pip)
       MINT  "GOLD MINT"     (FACTORY_ROW)  -> gold/coins   (Banker Bones)
       FORGE "CARD FORGE"    (FACTORY_ROW)  -> key fragments (Sparks)   [10 frags auto-forge 1 key]
       LAB   "RESEARCH LAB"  (THE_DOCKS)    -> Epic scrap   (Doc Wattson)
       GEN   "THE GENERATOR" (THE_DOCKS)    -> keys         (Volt)  + a rate boost to the other four

   HARD-LAW COMPLIANCE:
   - Soft currency ONLY. NO gems (server-only -> ctx.currency.grant('gems') is a no-op anyway),
     NO $BCARDD / ALK anywhere. Every grant rides AK_ECON (gold/scrap/keys/fragments are 100%
     client-side and deterministic from a timestamp + level -- no server needed).
   - New player-state is the single falsy-default field `prod:{}` (added once by the Lead in
     economy.js ensureShape). A zero-state profile stays byte-identical: nothing accrues until
     the player first walks into a producer building (which lazily creates its entry).
   - Headless-safe: zero top-level DOM/localStorage; bails if AK_SYSTEMS is absent; every storage
     touch is via AK_ECON (already try/catch wrapped).
   - Reuses the real keeper names from index.html KEEPERS + real card names (by name) as flavor.
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;            // hub-only; node harness / pages without the registry no-op

  // ---- tuning constants ----------------------------------------------------
  var MAX_LVL          = 10;     // production buildings cap at Lv 10 (mirrors CARD_LV_CAP feel)
  var CAP_HOURS        = 8;      // a building fills its cap in ~8h of offline accrual (at base rate)
  var RATE_GROWTH      = 0.5;    // each level adds +50% of the base rate (and base-rate cap)
  var GEN_BOOST_PER_LVL= 0.03;   // every Generator level adds +3% rate to the OTHER four buildings
  var GEN_BOOST_MAX    = 0.30;   // ...capped at +30%
  var HR_MS            = 3600000;

  // ---- per-building config (ids + colors match index.html B()/LV/FAC) -------
  // kind: 'gold' | 'scrap' | 'fragments' | 'keys'   grantKind: the ctx.currency.grant key
  var CFG = {
    GEM:  { kind:'scrap', rarity:'Rare', grantKind:'scrap', rate:5,   costBase:180,
            keeper:'Prospector Pip', glyph:"⛏️", it:'gem_mine',     color:'#b07bff',
            resLabel:'RARE SCRAP', resGlyph:"🔩",
            flavors:["Rich veins today, partner -- haul's ready.",
                     "Scrap this raw, even Stonejaw'd want a piece.",
                     "Mind the shaft, it's slick down there."] },
    MINT: { kind:'gold', rarity:null, grantKind:'gold', rate:90,  costBase:200,
            keeper:'Banker Bones', glyph:"💰", it:'merchant',       color:'#ffd76b',
            resLabel:'GOLD', resGlyph:"🪙",
            flavors:["Gold's good here. The mint never sleeps.",
                     "Count it twice -- that's how $BCARDD's crew stays paid.",
                     "Stack it deep, kid. Streets respect a full purse."] },
    FORGE:{ kind:'fragments', rarity:null, grantKind:'fragments', rate:4, costBase:220,
            keeper:'Sparks', glyph:"🔧", it:'card_forge',           color:'#ff9d5c',
            resLabel:'KEY FRAGMENTS', resGlyph:"🧩",
            flavors:["Forge's lit -- fragments comin' off the anvil.",
                     "Ten of these and you're cuttin' a fresh key.",
                     "Every key starts as scrap and sweat."] },
    LAB:  { kind:'scrap', rarity:'Epic', grantKind:'scrap', rate:2, costBase:260,
            keeper:'Doc Wattson', glyph:"🔬", it:'research_lab',     color:'#7fc8ff',
            resLabel:'EPIC SCRAP', resGlyph:"🔩",
            flavors:["Science waits for no dog -- Epic scrap's brewin'.",
                     "Pure compound, fit for Crown Foxhound himself.",
                     "The good stuff drips slow. Patience, mutt."] },
    GEN:  { kind:'keys', rarity:null, grantKind:'keys', rate:0.5, costBase:300,
            keeper:'Volt', glyph:"⚡", it:'research_lab',                  color:'#ffce6b',
            resLabel:'KEYS', resGlyph:"🗝️",
            flavors:["She's hummin' sweet -- juice keeps the row movin'.",
                     "No power, no muscle. I keep Rosco's lights on.",
                     "More watts here, faster everything else runs."] }
  };

  // ---- module-private caches (no profile state lives here) ------------------
  var _flavor = {};              // bid -> flavor string chosen on open (stable across re-renders)
  var _cache  = { prod:null, now:0 };  // throttled snapshot for the per-frame glow (no per-frame JSON.parse)
  var _acc    = 0;               // tick accumulator for the 1s cache refresh

  function profile(ctx){ return (ctx && ctx.econ) ? ctx.econ.loadProfile() : null; }

  // ---- accrual math (deterministic from lastCollect + level) ----------------
  function genBoost(prod){                 // Generator's rate boost to the OTHER four
    var gen = prod && prod.GEN; var lvl = gen ? (gen.lvl | 0) : 0;
    return 1 + Math.min(GEN_BOOST_MAX, GEN_BOOST_PER_LVL * lvl);
  }
  function baseRate(bid, lvl){             // per-hour, no Generator boost (cap rides this)
    var cfg = CFG[bid]; lvl = Math.max(1, lvl | 0);
    return cfg.rate * (1 + RATE_GROWTH * (lvl - 1));
  }
  function ratePerHr(bid, lvl, prod){      // effective per-hour (Generator boosts everyone but itself)
    var r = baseRate(bid, lvl);
    return (bid === 'GEN') ? r : r * genBoost(prod);
  }
  function capFor(bid, lvl){               // integer cap, based on the UN-boosted rate (boost only fills faster)
    return Math.max(1, Math.round(baseRate(bid, lvl) * CAP_HOURS));
  }
  function upCost(bid, lvl){               // coins to raise to the next level
    return Math.round(CFG[bid].costBase * Math.pow(1.5, Math.max(1, lvl | 0) - 1));
  }
  // pending (collectable integer units) for one building from a prod snapshot
  function pendingUnits(prod, bid, now){
    var e = prod && prod[bid]; if (!e) return 0;
    var lvl = Math.max(1, e.lvl | 0);
    var rate = ratePerHr(bid, lvl, prod), cap = capFor(bid, lvl);
    if (rate <= 0) return 0;
    var hr = Math.max(0, (now - (e.lastCollect || 0)) / HR_MS);
    var acc = rate * hr; if (acc > cap) acc = cap;
    var u = Math.floor(acc); return u < 0 ? 0 : u;
  }

  // ---- profile-state helpers (all writes via AK_ECON.mutateProfile) ---------
  function ensureProd(p, bid){             // create/repair a building entry IN a mutateProfile callback
    if (!p.prod || typeof p.prod !== 'object') p.prod = {};
    var e = p.prod[bid];
    if (!e || typeof e !== 'object') { e = { lvl:1, lastCollect: Date.now(), stored:0 }; p.prod[bid] = e; }
    if (typeof e.lvl !== 'number' || !isFinite(e.lvl) || e.lvl < 1) e.lvl = 1;
    if (typeof e.lastCollect !== 'number' || !isFinite(e.lastCollect)) e.lastCollect = Date.now();
    return e;
  }
  function ensureOpened(ctx, bid){         // first visit "claims" the building -> starts its clock (idempotent)
    var p = profile(ctx); if (!p) return;
    if (!p.prod || !p.prod[bid]) { ctx.econ.mutateProfile(function (pp) { ensureProd(pp, bid); }); }
  }

  // COLLECT: grant the haul, then advance the clock (preserving the sub-unit
  // remainder so frequent collecting of a slow producer never starves -- and
  // discarding overflow time once the cap was hit, so a capped building can't
  // be farmed twice). Grant FIRST (favor the player if anything throws).
  function doCollect(ctx, bid){
    var cfg = CFG[bid]; var p = profile(ctx);
    if (!p || !cfg) return { ok:false, units:0 };
    var prod = p.prod || {}; var e = prod[bid]; if (!e) return { ok:false, units:0 };
    var lvl = Math.max(1, e.lvl | 0);
    var rate = ratePerHr(bid, lvl, prod), cap = capFor(bid, lvl);
    if (rate <= 0) return { ok:false, units:0 };
    var hr = Math.max(0, (Date.now() - (e.lastCollect || 0)) / HR_MS);
    var acc = rate * hr; var capped = acc >= cap; if (capped) acc = cap;
    var units = Math.floor(acc); if (units <= 0) return { ok:false, units:0 };
    var gr = ctx.currency.grant(cfg.grantKind, units, cfg.rarity);     // gold/scrap/keys/fragments -- never gems
    var forged = (cfg.kind === 'fragments' && gr && gr.forged) ? gr.forged : 0;
    ctx.econ.mutateProfile(function (pp) {
      var ee = ensureProd(pp, bid);
      ee.lastCollect = capped ? Date.now() : ((ee.lastCollect || Date.now()) + (units / rate) * HR_MS);
      ee.stored = 0;
    });
    return { ok:true, units:units, forged:forged };
  }

  // UPGRADE: deduct coins + bump level in ONE atomic write.
  function doUpgrade(ctx, bid){
    var res = { ok:false };
    ctx.econ.mutateProfile(function (p) {
      var e = ensureProd(p, bid);
      if (e.lvl >= MAX_LVL) { res = { ok:false, err:'MAX', lvl:e.lvl }; return; }
      var cost = upCost(bid, e.lvl);
      if ((p.coins | 0) < cost) { res = { ok:false, err:'FUNDS', need:cost, have:p.coins | 0 }; return; }
      p.coins = (p.coins | 0) - cost; e.lvl = e.lvl + 1;
      res = { ok:true, lvl:e.lvl, cost:cost };
    });
    return res;
  }

  function collectBanner(cfg, units, forged){
    if (cfg.kind === 'gold')      return 'Collected ' + units + ' gold';
    if (cfg.kind === 'keys')      return 'Collected ' + units + ' key' + (units === 1 ? '' : 's');
    if (cfg.kind === 'fragments') return 'Collected ' + units + ' key fragment' + (units === 1 ? '' : 's') +
                                         (forged ? (' · forged ' + forged + ' key' + (forged === 1 ? '' : 's') + '!') : '');
    return 'Collected ' + units + ' ' + (cfg.rarity || '') + ' scrap';
  }

  // ---- the keeper interior (re-rendered after each action) ------------------
  function renderKeeper(ctx, b){
    var bid = b.id, cfg = CFG[bid]; if (!cfg) return;
    var p = profile(ctx); var prod = (p && p.prod) || {};
    var e = prod[bid] || { lvl:1, lastCollect: Date.now() };
    var lvl = Math.max(1, e.lvl | 0);
    var now = Date.now();
    var pend = pendingUnits(prod, bid, now);
    var cap  = capFor(bid, lvl);
    var rate = ratePerHr(bid, lvl, prod);
    var atMax = lvl >= MAX_LVL;
    var cost = upCost(bid, lvl);
    var gold = ctx.currency.get('gold');
    var flavor = _flavor[bid] || cfg.flavors[0];
    var rt = (rate >= 10) ? Math.round(rate) : (Math.round(rate * 10) / 10);

    var status = 'Lv ' + lvl + '  ·  ' + rt + '/hr  ·  ' + pend + '/' + cap + ' ' +
                 cfg.resLabel.toLowerCase() + ' ready';
    if (bid === 'GEN') {
      status += '  ·  +' + Math.round(Math.min(GEN_BOOST_MAX, GEN_BOOST_PER_LVL * lvl) * 100) + '% row boost';
    } else {
      var gb = genBoost(prod);
      if (gb > 1) status += '  ·  +' + Math.round((gb - 1) * 100) + '% gen boost';
    }

    var collectLabel = pend > 0 ? ('COLLECT ' + pend + ' ' + cfg.resLabel) : 'NOTHING READY YET';
    var upLabel = atMax ? ('MAX LEVEL (Lv ' + lvl + ')') : ('UPGRADE → Lv ' + (lvl + 1) + '  (' + cost + 'g)');

    ctx.ui.keeperCard({
      place: b.label, glyph: cfg.glyph, name: cfg.keeper,
      line: flavor + '   ' + status,
      interiorArt: 'assets/interiors/' + cfg.it + '.png',
      buttons: [
        { label: collectLabel, primary: true, disabled: pend <= 0, onClick: function (c) {
            var r = doCollect(c, bid);
            if (r && r.ok) c.showBanner(collectBanner(cfg, r.units, r.forged), 1.8);
            renderKeeper(c, b);
          } },
        { label: upLabel, primary: false, disabled: atMax || gold < cost, onClick: function (c) {
            var r = doUpgrade(c, bid);
            if (r && r.ok) c.showBanner(cfg.keeper.split(' ')[0] + ' upgraded ' + b.label + ' to Lv ' + r.lvl + '!', 1.8);
            else if (r && r.err === 'FUNDS') c.showBanner('Need ' + r.need + 'g (have ' + r.have + ')', 1.6);
            renderKeeper(c, b);
          } }
      ]
    });
  }

  // ---- the AK_SYSTEMS module ------------------------------------------------
  global.AK_SYSTEMS.register({
    id: 'production',

    init: function (ctx) {
      // prime the glow cache so a ready building lights up on the first frame
      try { var p = profile(ctx); _cache.prod = (p && p.prod) || {}; _cache.now = Date.now(); } catch (_e) {}
    },

    onEnterBuilding: function (b, ctx) {
      if (!b || !CFG[b.id]) return false;                 // claim ONLY the 5 producers (Section 4 ownership)
      var cfg = CFG[b.id];
      _flavor[b.id] = cfg.flavors[Math.floor(Math.random() * cfg.flavors.length)];
      ensureOpened(ctx, b.id);                            // first visit starts the clock
      renderKeeper(ctx, b);
      return true;                                        // host shows the panel + suppresses the default keeper
    },

    onTick: function (dt, ctx) {
      _acc += dt;
      if (_acc >= 1.0) { _acc = 0; var p = profile(ctx); _cache.prod = (p && p.prod) || {}; }
      _cache.now = Date.now();
    },

    // "ready to collect" pip floating over any producer in the current zone that has pending yield
    onDrawWorld: function (ctx) {
      var prod = _cache.prod; if (!prod) return;
      var now = _cache.now || Date.now();
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      var bs = ctx.activeZone && ctx.activeZone.buildings; if (!bs) return;
      for (var i = 0; i < bs.length; i++) {
        var b = bs[i]; var cfg = CFG[b.id]; if (!cfg) continue;
        if (!prod[b.id]) continue;
        var pend = pendingUnits(prod, b.id, now); if (pend <= 0) continue;
        var X = ctx.world.wx(b.x), Y = ctx.world.wy(b.y - (b.h ? b.h / 2 : 50) - 22);
        if (X < -40 || X > W + 40 || Y < -40 || Y > H + 40) continue;
        var pulse = 0.55 + 0.45 * Math.sin(now / 300 + i * 1.7);
        g.save();
        g.globalAlpha = pulse;
        g.shadowColor = cfg.color; g.shadowBlur = 14;
        g.fillStyle = cfg.color;
        g.beginPath(); g.arc(X, Y, 9, 0, 7); g.fill();
        g.shadowBlur = 0; g.globalAlpha = 1;
        g.font = '12px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(cfg.resGlyph, X, Y + 0.5);
        g.restore();
      }
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
