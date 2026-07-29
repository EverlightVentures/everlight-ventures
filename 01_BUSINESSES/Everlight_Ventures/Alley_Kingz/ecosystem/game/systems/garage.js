/* Alley Kingz -- THE GARAGE (window.AK_GARAGE)
 * AK-GARAGE 2026-07-18
 *
 * WHAT WAS HERE BEFORE: nothing. "The Garage" was a raid-loot multiplier building
 * (economy.js garageLootMult) that opened the deck builder (index.html B('GARAGE',...,
 * 'shop/shop.html#deck')). art/rig_bible.json authored 20 real chassis with real stats
 * and the game read exactly none of them. This module is the part system that makes a
 * rig gear instead of decoration, per AK_RIG_SYSTEM_MAP.html section 03.
 *
 * FOUR THINGS IT OWNS:
 *   1. PARTS      8 slots x 5 tiers, equipped per rig, persisted.
 *   2. STATS      chassis base (REAL, from the bible) + part deltas + dog pairing.
 *   3. PAIRING    the dog on the rig, in one of 4 mount positions, with the
 *                 signature bonus when its rigClass matches the chassis.
 *   4. CAPACITY   rig rarity sets weapon hardpoints, weapon rarity sets attachment
 *                 slots. Enforced on every write AND every read, so a hand-edited
 *                 save gets clipped back to legal on the next load.
 *
 * PERSISTENCE LAW: every write goes through AK_ECON.mutateProfile. This module never
 * touches localStorage directly. A whole class of save bugs came from modules doing
 * their own read-modify-write and clobbering a neighbour's field mid-flight.
 *
 * UNITS: the bible stats are integers 1..10 (armor/speed/handling/payload). Everything
 * in here is expressed in THOSE units so a part is directly comparable to a chassis
 * point. The player-facing number is SPEC = chassis units x10, so a Sport exhaust
 * (+1.2 speed) reads as "+12 speed" on the card. One scale, one place to retune.
 *
 * Headless-safe: no DOM or storage touched at load, every global access guarded, and
 * the whole stat core is pure so it runs under node with zero mocks.
 * No innerHTML anywhere: nodes are built and cleared with explicit DOM calls.
 */
(function (global) {
  'use strict';

  var MODELS = 'assets/models/';
  var RIGART = 'assets/rigs/';
  var FALLBACK_ART = 'assets/hub/garage.png';   // ships today; rig art lands later

  // =========================================================================
  // 1. CHASSIS -- generated from art/rig_bible.json v3 (20 rigs, count:20).
  // These four numbers per rig are the REAL authored balance. Do not hand-tune
  // them here: re-export from the bible instead. hydrate() below re-reads the
  // real file when it is served, and adds the prose the table drops.
  // =========================================================================
  var RIGS = [
    { id:'rig_mon_dozerhead', name:'Dozerhead', family:'monster', crew:'K-CLUB', rarity:'Rare',
      armor:9, speed:3, handling:2, payload:7, weapon:'The Gavel Blade', sig:'turret_util' },
    { id:'rig_mon_hooktooth', name:'Hooktooth', family:'monster', crew:'RUST HALO', rarity:'Rare',
      armor:7, speed:3, handling:3, payload:8, weapon:'Debt Hook', sig:'turret_util' },
    { id:'rig_mon_railhound', name:'Railhound', family:'monster', crew:'BONEGUARD', rarity:'Mythic',
      armor:9, speed:2, handling:2, payload:8, weapon:'Anchor Rail', sig:'turret_util' },
    { id:'rig_mon_stiltjack', name:'Stiltjack', family:'monster', crew:'SCRAPJAW', rarity:'Rare',
      armor:7, speed:4, handling:3, payload:7, weapon:'Marquee Stomp', sig:'turret_util' },
    { id:'rig_mon_technical', name:'Technical', family:'monster', crew:'ASHLINE', rarity:'Epic',
      armor:5, speed:5, handling:4, payload:8, weapon:'The Retainer', sig:'turret_util' },
    { id:'rig_muscle_boneyard', name:'Boneyard', family:'muscle', crew:'RUST HALO', rarity:'Epic',
      armor:8, speed:6, handling:3, payload:6, weapon:'Last Rites Stacks', sig:'bruiser' },
    { id:'rig_muscle_brickhouse', name:'Brickhouse', family:'muscle', crew:'K-CLUB', rarity:'Legendary',
      armor:10, speed:4, handling:3, payload:7, weapon:'Foreclosure', sig:'bruiser' },
    { id:'rig_muscle_coffin_nail', name:'Coffin Nail', family:'muscle', crew:'BONEGUARD', rarity:'Epic',
      armor:8, speed:4, handling:2, payload:7, weapon:'The Sixth Nail', sig:'bruiser' },
    { id:'rig_muscle_ratking', name:'Ratking', family:'muscle', crew:'SCRAPJAW', rarity:'Rare',
      armor:8, speed:5, handling:4, payload:6, weapon:'Grudge Nailer', sig:'bruiser' },
    { id:'rig_muscle_sunday_best', name:'Sunday Best', family:'muscle', crew:'SNAKE EYES', rarity:'Rare',
      armor:7, speed:5, handling:4, payload:6, weapon:'Encore Hop', sig:'bruiser' },
    { id:'rig_sport_driftrat', name:'Driftrat', family:'sport', crew:'SCRAPJAW', rarity:'Rare',
      armor:3, speed:8, handling:9, payload:3, weapon:'Wager Hook', sig:'sprinter' },
    { id:'rig_sport_hatchmutt', name:'Hatchmutt', family:'sport', crew:'MUTT$', rarity:'Common',
      armor:2, speed:7, handling:8, payload:3, weapon:'Runt Spitter', sig:'sprinter' },
    { id:'rig_sport_rotorwind', name:'Rotorwind', family:'sport', crew:'ASHLINE', rarity:'Rare',
      armor:2, speed:9, handling:8, payload:2, weapon:'Redline Backfire', sig:'sprinter' },
    { id:'rig_sport_shadowblade', name:'Shadowblade', family:'sport', crew:'NIGHTSHIFT', rarity:'Mythic',
      armor:4, speed:9, handling:8, payload:2, weapon:'The Hush Lunge', sig:'sprinter' },
    { id:'rig_sport_silkcut', name:'Silkcut', family:'sport', crew:'NIGHTSHIFT', rarity:'Epic',
      armor:3, speed:9, handling:8, payload:3, weapon:'Micron Rail', sig:'sprinter' },
    { id:'rig_van_bread_truck', name:'Bread Truck', family:'van', crew:'MUTT$', rarity:'Common',
      armor:5, speed:4, handling:6, payload:7, weapon:'Back-Door Special', sig:'tech_ops' },
    { id:'rig_van_cable_guy', name:'Cable Guy', family:'van', crew:'K-CLUB', rarity:'Epic',
      armor:6, speed:4, handling:5, payload:8, weapon:'Blackout Boom', sig:'tech_ops' },
    { id:'rig_van_jammer', name:'The Jammer', family:'van', crew:'NIGHTSHIFT', rarity:'Mythic',
      armor:5, speed:4, handling:5, payload:8, weapon:'The Dead Air Dish', sig:'tech_ops' },
    { id:'rig_van_meat_wagon', name:'Meat Wagon', family:'van', crew:'RUST HALO', rarity:'Rare',
      armor:6, speed:3, handling:4, payload:7, weapon:'Reliquary Censer', sig:'tech_ops' },
    { id:'rig_van_sunshine_bus', name:'Sunshine Bus', family:'van', crew:'SNAKE EYES', rarity:'Rare',
      armor:8, speed:3, handling:4, payload:8, weapon:'The Bouncer\'s Line', sig:'tech_ops' }
  ];

  var RIG_BY_ID = {};
  (function () { for (var i = 0; i < RIGS.length; i++) RIG_BY_ID[RIGS[i].id] = RIGS[i]; })();

  function rig(rigId) { return RIG_BY_ID[String(rigId || '')] || null; }
  function rigList() { return RIGS.slice(); }

  // Re-read the REAL bible when something serves it (fetch, build step, node test).
  // Overwrites the four stats and pulls in the prose the embedded table drops, so the
  // panel can quote the authored signature bonus verbatim instead of paraphrasing it.
  function hydrate(bible) {
    var n = 0;
    try {
      var rows = (bible && bible.rigs) || [];
      for (var i = 0; i < rows.length; i++) {
        var r = rows[i], t = RIG_BY_ID[r && r.id];
        if (!t || !r.stats) continue;
        t.armor = r.stats.armor | 0; t.speed = r.stats.speed | 0;
        t.handling = r.stats.handling | 0; t.payload = r.stats.payload | 0;
        if (r.rarity) t.rarity = r.rarity;
        if (r.synergy) {
          if (r.synergy.signatureDogClass) t.sig = r.synergy.signatureDogClass;
          if (r.synergy.signatureBonus) t.sigBonus = r.synergy.signatureBonus;
          if (r.synergy.offClassNote) t.offNote = r.synergy.offClassNote;
        }
        if (r.weapon && r.weapon.name) { t.weapon = r.weapon.name; t.weaponMount = r.weapon.mount || ''; }
        if (r.personality) t.personality = r.personality;
        n++;
      }
    } catch (_e) {}
    return n;
  }

  // =========================================================================
  // 2. SLOTS + TIERS
  // Slot list is verbatim from AK_WAR_RIG_MERGE_PLAN.md section 2 item 4.
  // =========================================================================
  var SLOTS = ['engine', 'turbo', 'armor', 'weapon_mount', 'tires', 'transmission', 'exhaust', 'utility'];

  var TIERS = ['Stock', 'Sport', 'Pro', 'Elite', 'Kingz Custom'];

  // mult scales every delta in SLOT_DELTA. drama/glow drive the visual escalation:
  // Stock is dull painted steel, Kingz Custom is the one that glows in the dark and
  // is the whole reason a player grinds the last tier. Never strip the glow.
  var TIER = {
    'Stock':        { i: 0, mult: 0,   key: 'stock',  color: '#8a8f96', glow: 0,    drama: 'flat paint, factory bolts, honest rust' },
    'Sport':        { i: 1, mult: 1,   key: 'sport',  color: '#7fc8ff', drama: 'polished alloy, one clean stripe', glow: 0.15 },
    'Pro':          { i: 2, mult: 1.8, key: 'pro',    color: '#7ee787', drama: 'machined billet, visible weave, heat-blued tips', glow: 0.35 },
    'Elite':        { i: 3, mult: 2.7, key: 'elite',  color: '#b48ead', drama: 'anodized purple, etched panels, cold underlight', glow: 0.6 },
    'Kingz Custom': { i: 4, mult: 3.6, key: 'kingz',  color: '#e8c55a', drama: 'gold leaf, engraved crown, live ember glow and a shadow that moves', glow: 1 }
  };

  // Per-slot deltas AT SPORT TIER, in chassis units (x10 = the spec number the UI shows).
  // Anchor: exhaust Sport = +1.2 speed = "+12 speed from Sport Exhaust" on the card.
  // Every slot pays for its gain somewhere, which is what makes a build a choice and
  // not a checklist. ONE table: retune the game here, not in eight call sites.
  var SLOT_DELTA = {
    engine:       { speed: 1.2, payload: 0.3, handling: -0.2 },
    turbo:        { speed: 1.0, armor: -0.3 },
    armor:        { armor: 1.4, speed: -0.4, handling: -0.2 },
    weapon_mount: { damage: 1.4, payload: -0.3, handling: -0.1 },
    tires:        { handling: 1.2, speed: 0.3 },
    transmission: { handling: 0.7, speed: 0.6 },
    exhaust:      { speed: 1.2, handling: 0.2 },
    utility:      { payload: 1.3, armor: 0.3 }
  };

  var SLOT_LABEL = {
    engine: 'Engine', turbo: 'Turbo', armor: 'Armor', weapon_mount: 'Weapon Mount',
    tires: 'Tires', transmission: 'Transmission', exhaust: 'Exhaust', utility: 'Utility'
  };

  // Street names so a part reads like a part and not like a spreadsheet row.
  var PART_NAME = {
    engine:       ['Factory Block', 'Sport Block', 'Pro Stroker', 'Elite Big Block', 'Kingz Crown Block'],
    turbo:        ['No Turbo', 'Sport Snail', 'Pro Twin-Scroll', 'Elite Ballbearing', 'Kingz Hot-Side'],
    armor:        ['Bare Panel', 'Sport Skidplate', 'Pro Scale Plate', 'Elite Bunker Skirt', 'Kingz Crown Plate'],
    weapon_mount: ['Bare Eye', 'Sport Pintle', 'Pro Ring Mount', 'Elite Stabilized Ring', 'Kingz Throne Mount'],
    tires:        ['Bald Set', 'Sport Radials', 'Pro Semi-Slicks', 'Elite Beadlocks', 'Kingz Gold Beadlocks'],
    transmission: ['Stock Box', 'Sport Short-Shift', 'Pro Dogbox', 'Elite Sequential', 'Kingz Crown Sequential'],
    exhaust:      ['Stock Pipe', 'Sport Cat-Back', 'Pro Straight-Pipe', 'Elite Side Stacks', 'Kingz Organ Stacks'],
    utility:      ['Empty Bay', 'Sport Rack', 'Pro Cargo Cage', 'Elite Loadmaster', 'Kingz Vault Bay']
  };

  // Catalog, generated so the ladder can never drift from the delta table.
  // id = '<slot>:<tierKey>'  e.g. 'exhaust:sport'
  var PARTS = {};
  (function () {
    for (var s = 0; s < SLOTS.length; s++) {
      for (var t = 0; t < TIERS.length; t++) {
        var slot = SLOTS[s], tier = TIERS[t], tm = TIER[tier];
        var d = {}, base = SLOT_DELTA[slot], k;
        for (k in base) { d[k] = Math.round(base[k] * tm.mult * 100) / 100; }
        PARTS[slot + ':' + tm.key] = {
          id: slot + ':' + tm.key, slot: slot, tier: tier, tierIndex: t,
          name: PART_NAME[slot][t], deltas: d,
          color: tm.color, glow: tm.glow, drama: tm.drama
        };
      }
    }
  })();

  function part(partId) { return PARTS[String(partId || '')] || null; }
  function partsForSlot(slot) {
    var out = [];
    if (SLOT_DELTA[slot]) for (var t = 0; t < TIERS.length; t++) out.push(PARTS[slot + ':' + TIER[TIERS[t]].key]);
    return out;
  }

  // =========================================================================
  // 3. CAPACITY -- the compounding rule, enforced in the data layer.
  // Rig rarity sets how many weapons it can carry. Weapon rarity sets how many
  // attachments that weapon can carry. Both tables are read from the CHASSIS
  // record and the WEAPON registry, never from the save file, so editing
  // localStorage buys nothing: sanitizeRig() clips it back on the next read.
  // =========================================================================
  var HARDPOINTS = { Common: 1, Rare: 2, Epic: 3, Legendary: 4, Mythic: 5 };
  var ATTACH_SLOTS = { Common: 1, Uncommon: 1, Rare: 2, Epic: 2, Legendary: 3, Mythic: 3, Ultra: 3 };

  function hardpointsFor(rigId) {
    var r = rig(rigId);
    return r ? (HARDPOINTS[r.rarity] || 1) : 0;
  }
  // Weapon rarity resolves against window.AK_WEAPONS when that roster lands (the
  // authoritative source). Until then the caller-supplied rarity is accepted but
  // still clamped to the known ladder, so an unknown string can never buy slots.
  function weaponRarity(weaponId, hinted) {
    var r = null;
    try {
      var reg = global.AK_WEAPONS;
      if (reg) { var w = (reg.byId && reg.byId[weaponId]) || (reg[weaponId]); if (w && w.rarity) r = w.rarity; }
    } catch (_e) {}
    if (!r) r = hinted;
    return ATTACH_SLOTS[r] ? r : 'Common';
  }
  function attachSlotsFor(weaponId, hinted) { return ATTACH_SLOTS[weaponRarity(weaponId, hinted)] || 1; }

  // =========================================================================
  // 4. PERSISTED STATE  (profile.garage, lazily created inside mutateProfile)
  //   p.garage = { active: rigId, rigs: { rigId: {
  //       parts: { slot: partId },
  //       hp: [ { w: weaponId, r: rarity, at: [attachId] } ],   // hp = hardpoints
  //       dog: { card: '0013', mount: 'driver' } } } }
  // sanitizeRig is the gate: it runs on every read and every write.
  // =========================================================================
  function emptyRig() { return { parts: {}, hp: [], dog: null }; }

  function sanitizeRig(state, rigId) {
    var out = emptyRig(), i, k;
    if (!state || typeof state !== 'object') return out;
    // parts: slot must be real, part must exist, and the part must belong to that slot
    if (state.parts && typeof state.parts === 'object') {
      for (k in state.parts) {
        var pd = PARTS[state.parts[k]];
        if (pd && pd.slot === k) out.parts[k] = pd.id;
      }
    }
    // hardpoints: clipped to the CHASSIS capacity, attachments clipped to WEAPON capacity
    var cap = hardpointsFor(rigId);
    if (Object.prototype.toString.call(state.hp) === '[object Array]') {
      for (i = 0; i < state.hp.length && out.hp.length < cap; i++) {
        var h = state.hp[i];
        if (!h || !h.w) continue;
        var rar = weaponRarity(h.w, h.r), acap = ATTACH_SLOTS[rar] || 1, at = [];
        if (Object.prototype.toString.call(h.at) === '[object Array]') {
          for (var j = 0; j < h.at.length && at.length < acap; j++) {
            if (h.at[j] && at.indexOf(h.at[j]) < 0) at.push(String(h.at[j]));
          }
        }
        out.hp.push({ w: String(h.w), r: rar, at: at });
      }
    }
    // dog: one dog, one legal mount position
    if (state.dog && state.dog.card && MOUNTS[state.dog.mount]) {
      out.dog = { card: String(state.dog.card), mount: state.dog.mount };
    }
    return out;
  }

  function profile(p) {
    if (p) return p;
    try { return (global.AK_ECON && AK_ECON.loadProfile) ? AK_ECON.loadProfile() : null; } catch (_e) { return null; }
  }
  function rigState(rigId, p) {
    p = profile(p);
    var raw = null;
    try { raw = p && p.garage && p.garage.rigs && p.garage.rigs[rigId]; } catch (_e) {}
    return sanitizeRig(raw, rigId);
  }

  // The ONE write path. Never localStorage, never a bare saveProfile.
  function write(rigId, fn) {
    if (!rig(rigId)) return { ok: false, reason: 'no_rig' };
    var res = { ok: false, reason: 'no_econ' };
    try {
      if (!(global.AK_ECON && AK_ECON.mutateProfile)) return res;
      AK_ECON.mutateProfile(function (p) {
        if (!p.garage || typeof p.garage !== 'object') p.garage = { active: '', rigs: {} };
        if (!p.garage.rigs || typeof p.garage.rigs !== 'object') p.garage.rigs = {};
        var st = sanitizeRig(p.garage.rigs[rigId], rigId);
        res = fn(st, p) || { ok: true };
        p.garage.rigs[rigId] = sanitizeRig(st, rigId);   // clip again on the way out
        res.state = p.garage.rigs[rigId];
      });
      // AK-GARAGE 2026-07-18: every mutation invalidates the outward resolver cache in
      // the same breath that commits it. This is why the district cannot disagree with
      // the garage: there is no window where a stale visual outlives the write.
      _rev++;
    } catch (_e) { res = { ok: false, reason: 'throw' }; }
    return res;
  }

  // ---- parts ----
  // AK-FIX-lane-H 2026-07-28: fitting a part burns a little Common scrap -- a cheap
  // sink so a rig is EARNED, not free. Stock (tier 0) is free (it IS the default / a
  // downgrade); the cost climbs with tier. Best-effort + fully guarded: no AK_ECON
  // (headless / node) or an empty bag just charges what is there and still bolts the
  // part on, so equip never blocks the build and never throws.
  var PART_SCRAP_COST = [0, 2, 4, 7, 12];   // by tierIndex: Stock / Sport / Pro / Elite / Kingz Custom
  function partScrapCost(pd) { var c = pd ? PART_SCRAP_COST[pd.tierIndex | 0] : 0; return (typeof c === 'number' && c > 0) ? c : 0; }
  function equip(rigId, slot, partId) {
    var pd = part(partId);
    if (!pd) return { ok: false, reason: 'no_part' };
    if (pd.slot !== slot) return { ok: false, reason: 'wrong_slot' };
    // charge only when the slot is actually CHANGING to this part (re-fitting the same part is free)
    var cur = rigState(rigId), cost = (!cur || cur.parts[slot] !== pd.id) ? partScrapCost(pd) : 0;
    return write(rigId, function (st, p) {
      st.parts[slot] = pd.id;
      var paid = 0;
      if (cost > 0 && p) {                          // best-effort scrap sink (guarded, floors at 0)
        if (!p.scrap || typeof p.scrap !== 'object') p.scrap = {};
        paid = Math.min(cost, p.scrap.Common | 0);
        p.scrap.Common = Math.max(0, (p.scrap.Common | 0) - paid);
      }
      return { ok: true, slot: slot, part: pd.id, cost: cost, paid: paid };
    });
  }
  function unequip(rigId, slot) {
    if (!SLOT_DELTA[slot]) return { ok: false, reason: 'no_slot' };
    return write(rigId, function (st) { delete st.parts[slot]; return { ok: true, slot: slot }; });
  }

  // ---- weapons + attachments (capacity is enforced HERE, not in the UI) ----
  function mountWeapon(rigId, weaponId, rarity) {
    if (!weaponId) return { ok: false, reason: 'no_weapon' };
    return write(rigId, function (st) {
      var cap = hardpointsFor(rigId);
      if (st.hp.length >= cap) return { ok: false, reason: 'hardpoints_full', cap: cap };
      st.hp.push({ w: String(weaponId), r: weaponRarity(weaponId, rarity), at: [] });
      return { ok: true, index: st.hp.length - 1, cap: cap };
    });
  }
  // AK-GARAGE 2026-07-18: hardpoint index must be a real integer. `index | 0` would
  // turn undefined into 0 and silently retarget the FIRST hardpoint, which is how a
  // failed mountWeapon (returning no .index) quietly writes to the wrong weapon.
  function hpIndex(v) { return (typeof v === 'number' && isFinite(v) && v >= 0 && v === Math.floor(v)) ? v : -1; }

  function unmountWeapon(rigId, index) {
    var ix = hpIndex(index);
    if (ix < 0) return { ok: false, reason: 'bad_index' };
    return write(rigId, function (st) {
      if (!st.hp[ix]) return { ok: false, reason: 'empty' };
      st.hp.splice(ix, 1);
      return { ok: true };
    });
  }
  function attachToWeapon(rigId, index, attachId) {
    if (!attachId) return { ok: false, reason: 'no_attach' };
    var ix = hpIndex(index);
    if (ix < 0) return { ok: false, reason: 'bad_index' };
    return write(rigId, function (st) {
      var h = st.hp[ix];
      if (!h) return { ok: false, reason: 'no_weapon' };
      var cap = ATTACH_SLOTS[h.r] || 1;
      if (h.at.length >= cap) return { ok: false, reason: 'attach_full', cap: cap };
      if (h.at.indexOf(String(attachId)) >= 0) return { ok: false, reason: 'dupe' };
      h.at.push(String(attachId));
      return { ok: true, cap: cap, used: h.at.length };
    });
  }
  function detachFromWeapon(rigId, index, attachId) {
    var ix = hpIndex(index);
    if (ix < 0) return { ok: false, reason: 'bad_index' };
    return write(rigId, function (st) {
      var h = st.hp[ix];
      if (!h) return { ok: false, reason: 'no_weapon' };
      var i = h.at.indexOf(String(attachId));
      if (i < 0) return { ok: false, reason: 'not_attached' };
      h.at.splice(i, 1);
      return { ok: true };
    });
  }
  function capacity(rigId, p) {
    var st = rigState(rigId, p), out = { hardpoints: hardpointsFor(rigId), used: st.hp.length, weapons: [] };
    for (var i = 0; i < st.hp.length; i++) {
      out.weapons.push({ id: st.hp[i].w, rarity: st.hp[i].r,
        attachCap: ATTACH_SLOTS[st.hp[i].r] || 1, attachUsed: st.hp[i].at.length, attach: st.hp[i].at.slice() });
    }
    return out;
  }

  // =========================================================================
  // 5. DOG PAIRING
  // The bible carries synergy.signatureDogClass per rig and canon.js carries
  // rig.rigClass per card. Match them and the lore pays out as a stat.
  // Four mount positions, each reading a different one of the dog's real canon
  // numbers, so WHERE you sit the dog matters as much as WHICH dog it is.
  // =========================================================================
  var MOUNTS = {
    driver: { label: 'DRIVER', reads: 'AGI',  blurb: 'Hands on the wheel. Its speed becomes the rig\'s speed.' },
    gunner: { label: 'GUNNER', reads: 'ATK',  blurb: 'Up top on the mount. Its bite becomes the rig\'s damage.' },
    guard:  { label: 'GUARD',  reads: 'DEF',  blurb: 'Riding the plate. Its body becomes the rig\'s hull.' },
    solo:   { label: 'SOLO',   reads: 'ALL',  blurb: 'One dog, three jobs. Everything at 60% and the flank is open.' }
  };

  var SOLO_SHARE = 0.6;      // one dog cannot do three jobs at full strength
  var SOLO_RISK = 0.15;      // and nobody is watching the flank
  var SIGNATURE_MULT = 1.10; // canon rig for that dog class
  var HP_PER_ARMOR = 120;    // armor -> hp readout (base 9 armor = 1080, dog scale)

  // Canon card -> the three pairing numbers. Real fields only: hp, damage,
  // move_speed. Divisors put them on the 1..10 chassis scale, nothing invented.
  function dogStats(card) {
    if (!card) return null;
    var cls = '';
    try { cls = (card.rig && card.rig.rigClass) || card.rigClass || ''; } catch (_e) {}
    return {
      card: String(card.cardNumber || card.num || card.id || ''),
      name: card.name || '',
      cls: cls,
      atk: round2((+card.damage || 0) / 100),
      def: round2((+card.hp || 0) / 500),
      agi: round2((+card.move_speed || 0) * 1.6)
    };
  }
  function findCard(cardNumber) {
    try {
      var list = global.CANON_CARDS;
      if (!list) return null;
      var want = String(cardNumber);
      for (var i = 0; i < list.length; i++) if (String(list[i].cardNumber) === want) return list[i];
    } catch (_e) {}
    return null;
  }
  function setDog(rigId, cardNumber, mount) {
    if (!MOUNTS[mount]) return { ok: false, reason: 'no_mount' };
    if (!cardNumber) return { ok: false, reason: 'no_card' };
    return write(rigId, function (st) {
      st.dog = { card: String(cardNumber), mount: mount };
      return { ok: true, dog: st.dog };
    });
  }
  function clearDog(rigId) { return write(rigId, function (st) { st.dog = null; return { ok: true }; }); }

  // Pure: given a rig record, a dogStats block and a mount, what does the dog add.
  function pairingFor(r, ds, mount) {
    var add = { armor: 0, speed: 0, handling: 0, payload: 0, damage: 0 };
    var out = { mount: mount, dog: ds ? ds.name : '', cls: ds ? ds.cls : '',
                signature: false, risk: false, add: add, note: '' };
    if (!r || !ds || !MOUNTS[mount]) return out;
    var k = (mount === 'solo') ? SOLO_SHARE : 1;
    if (mount === 'driver' || mount === 'solo') { add.speed += ds.agi * k; add.handling += ds.agi * 0.5 * k; }
    if (mount === 'gunner' || mount === 'solo') { add.damage += ds.atk * k; }
    if (mount === 'guard'  || mount === 'solo') { add.armor += ds.def * 0.6 * k; add.payload += ds.def * 0.2 * k; }
    if (mount === 'solo') { out.risk = true; out.note = 'Solo: -' + Math.round(SOLO_RISK * 100) + '% armor, no second pair of eyes.'; }
    out.signature = !!(ds.cls && r.sig && ds.cls === r.sig);
    if (out.signature) out.note = (r.sigBonus || ('Signature pairing: ' + ds.cls + ' in a ' + r.family + ' chassis.'));
    return out;
  }

  // =========================================================================
  // 6. computeStats -- the whole point.
  // Returns the final block AND the per-slot contribution, so the UI can print
  // "+12 speed from Sport Exhaust" without recomputing anything.
  // Pure when opts.parts / opts.dog are supplied; reads the profile otherwise.
  // =========================================================================
  var STAT_KEYS = ['armor', 'speed', 'handling', 'payload', 'damage'];

  function round2(n) { return Math.round(n * 100) / 100; }
  function spec(n) { return Math.round(n * 10); }

  function computeStats(rigId, opts) {
    opts = opts || {};
    var r = rig(rigId);
    if (!r) return null;

    var state = (opts.state) ? sanitizeRig(opts.state, rigId) : rigState(rigId, opts.profile);
    if (opts.parts) { state = sanitizeRig({ parts: opts.parts, hp: state.hp, dog: state.dog }, rigId); }

    // base: the REAL bible numbers. damage is 0 on purpose: the bible names each
    // rig's signature weapon but authors no number for it, so nothing is invented
    // here. Damage comes from the weapon mount and the gunner.
    var base = { armor: r.armor, speed: r.speed, handling: r.handling, payload: r.payload, damage: 0 };
    var total = { armor: base.armor, speed: base.speed, handling: base.handling, payload: base.payload, damage: 0 };

    // ---- per-slot contributions ----
    var contrib = [], i, k;
    for (i = 0; i < SLOTS.length; i++) {
      var slot = SLOTS[i], pid = state.parts[slot], pd = pid ? PARTS[pid] : null;
      if (!pd || pd.tierIndex === 0) {
        contrib.push({ slot: slot, slotLabel: SLOT_LABEL[slot], partId: pid || '', tier: pd ? pd.tier : 'Stock',
                       name: pd ? pd.name : PART_NAME[slot][0], deltas: {}, lines: [], empty: true });
        continue;
      }
      var lines = [], d = {};
      for (k in pd.deltas) {
        var v = pd.deltas[k];
        if (!v) continue;
        total[k] = (total[k] || 0) + v;
        d[k] = round2(v);
        lines.push((v > 0 ? '+' : '') + spec(v) + ' ' + k + ' from ' + pd.tier + ' ' + SLOT_LABEL[slot]);
      }
      contrib.push({ slot: slot, slotLabel: SLOT_LABEL[slot], partId: pd.id, tier: pd.tier,
                     name: pd.name, color: pd.color, glow: pd.glow, deltas: d, lines: lines, empty: false });
    }

    // ---- dog pairing ----
    var ds = opts.dog ? dogStats(opts.dog) : (state.dog ? dogStats(findCard(state.dog.card)) : null);
    var mount = (opts.dog && opts.mount) || (state.dog && state.dog.mount) || 'driver';
    var pair = pairingFor(r, ds, mount);
    for (k in pair.add) { if (pair.add[k]) total[k] = (total[k] || 0) + pair.add[k]; }
    if (pair.risk) total.armor *= (1 - SOLO_RISK);
    if (pair.signature) { for (i = 0; i < STAT_KEYS.length; i++) total[STAT_KEYS[i]] *= SIGNATURE_MULT; }

    // ---- weapons on the hardpoints ----
    var cap = capacity(rigId, opts.profile);
    if (opts.state || opts.parts) cap = { hardpoints: hardpointsFor(rigId), used: state.hp.length, weapons: capacity_from(state) };

    var stats = {}, specOut = {};
    for (i = 0; i < STAT_KEYS.length; i++) {
      var key = STAT_KEYS[i];
      stats[key] = round2(Math.max(0, total[key] || 0));
      specOut[key] = spec(stats[key]);
    }
    stats.hp = Math.round(stats.armor * HP_PER_ARMOR);
    specOut.hp = stats.hp;

    return {
      rigId: r.id, name: r.name, family: r.family, crew: r.crew, rarity: r.rarity,
      weapon: r.weapon,
      base: base,                 // chassis units, straight off the bible
      stats: stats,               // final, chassis units (1 decimal) + derived hp
      spec: specOut,              // player-facing x10 integers
      contrib: contrib,           // per slot, with ready-to-print lines
      pairing: pair,              // dog contribution + signature + risk
      capacity: cap,              // hardpoints and attachment usage
      parts: state.parts,
      dog: state.dog
    };
  }
  function capacity_from(state) {
    var out = [];
    for (var i = 0; i < state.hp.length; i++) {
      out.push({ id: state.hp[i].w, rarity: state.hp[i].r,
        attachCap: ATTACH_SLOTS[state.hp[i].r] || 1, attachUsed: state.hp[i].at.length, attach: state.hp[i].at.slice() });
    }
    return out;
  }

  // Every printable contribution line, flattened. What the panel actually renders.
  function contribLines(rigId, opts) {
    var cs = computeStats(rigId, opts), out = [];
    if (!cs) return out;
    for (var i = 0; i < cs.contrib.length; i++) out = out.concat(cs.contrib[i].lines);
    return out;
  }

  function activeRig(p) {
    p = profile(p);
    try { return (p && p.garage && p.garage.active) || ''; } catch (_e) { return ''; }
  }
  function setActiveRig(rigId) {
    if (!rig(rigId)) return { ok: false, reason: 'no_rig' };
    try {
      if (!(global.AK_ECON && AK_ECON.mutateProfile)) return { ok: false, reason: 'no_econ' };
      AK_ECON.mutateProfile(function (p) {
        if (!p.garage || typeof p.garage !== 'object') p.garage = { active: '', rigs: {} };
        p.garage.active = rigId;
      });
      _rev++;                                    // AK-GARAGE 2026-07-18: see write()
      return { ok: true, active: rigId };
    } catch (_e) { return { ok: false, reason: 'throw' }; }
  }

  // =========================================================================
  // 6b. OUTWARD RESOLVERS -- AK-GARAGE 2026-07-18. THE REFLECTION.
  //
  // The law this file exists to serve: an edit made INSIDE the garage has to be
  // true OUTSIDE it. That only holds if the world does not keep its own copy of
  // the rig. So the world gets no copy. It gets these two functions, and both of
  // them read the SAME p.garage state the garage panel writes through equip().
  // There is exactly one source of truth and it is the save file.
  //
  //   rigVisual(card) -> { model, art, decals, tint, glow, mountPoints, ... }
  //   rigStats(card)  -> the final stat block (computeStats, dog already paired)
  //
  // Keyed by CARD (name string or the card object heroCard() already returns), because
  // every outside call site is holding a dog, not a chassis id: index.html:2295 (raid
  // draw) and index.html:2537 (hub avatar draw) both call heroCard(). The dog carries
  // its chassis in canon.js card.rig.rigId, so the card IS the key to the rig.
  //
  // PER-FRAME SAFE. index.html:2537 runs every frame. A resolver that re-read and
  // re-parsed the profile there would be a per-frame JSON.parse, which is the exact
  // cost production.js:_cache exists to avoid. Same fix: memoize on a revision counter
  // bumped by write(), with a 1s ceiling so an out-of-band profile swap still lands.
  // =========================================================================
  function clampN(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }

  // Visual identity per chassis family. Layout + colour only, never balance: these
  // never feed computeStats, they only tell a renderer where the dog sits and what
  // the paint reads as before any part has been bolted on.
  var FAMILY = {
    monster: { tint: '#c98f4a', radius: 2.35, deck: 'high' },
    muscle:  { tint: '#c05a5a', radius: 1.85, deck: 'low' },
    sport:   { tint: '#7fc8ff', radius: 1.55, deck: 'low' },
    van:     { tint: '#8fae7a', radius: 2.05, deck: 'high' }
  };

  // Mount offsets in UNIT rig-space (x right, y up, z forward), scaled by the family
  // radius at read time. A 2D drawer multiplies by sprite width; a 3D drawer feeds
  // them straight to a mesh. One geometry, both renderers, which is the whole point.
  var MOUNT_GEOM = {
    driver: { ox: -0.22, oy: 0.30, oz:  0.10 },
    gunner: { ox:  0.00, oy: 0.62, oz: -0.18 },
    guard:  { ox:  0.26, oy: 0.22, oz: -0.30 },
    solo:   { ox:  0.00, oy: 0.34, oz:  0.02 }
  };

  var _rev = 0;                 // bumped by every successful write (see write())
  var _visCache = {};           // key -> { rev, at, v }
  var CACHE_MS = 1000;

  function cardKey(card) {
    if (!card) return '';
    if (typeof card === 'string') return card;
    return String(card.name || card.cardNumber || '');
  }
  // Accepts a card object (what heroCard() hands back) or a card NAME. Name match is
  // case/space tolerant so 'coffin nail' and 'Coffin Nail' resolve to the same dog.
  function cardFor(card) {
    if (card && typeof card === 'object' && card.rig) return card;
    var want = String(cardKey(card) || '').trim().toLowerCase();
    if (!want) return null;
    try {
      var list = global.CANON_CARDS;
      if (!list) return null;
      for (var i = 0; i < list.length; i++) {
        var c = list[i];
        if (String(c.name || '').trim().toLowerCase() === want) return c;
        if (String(c.cardNumber || '') === want) return c;
      }
    } catch (_e) {}
    return null;
  }

  // card -> bible chassis. 20 of the 21 rigIds in canon.js ARE bible ids, so this is
  // a direct hit for 126 of 127 cards. The one that is not ($BCARDD's unique
  // rig_crown_bcardd, which the bible never authored) falls back to the highest-rarity
  // chassis in its own family rather than to invented stats, and says so in .source so
  // a caller can tell a real chassis from a stand-in.
  var RARITY_RANK = { Common: 1, Uncommon: 2, Rare: 3, Epic: 4, Legendary: 5, Mythic: 6 };
  function familyTop(family) {
    var best = null;
    for (var i = 0; i < RIGS.length; i++) {
      var r = RIGS[i];
      if (r.family !== family) continue;
      if (!best || (RARITY_RANK[r.rarity] || 0) > (RARITY_RANK[best.rarity] || 0)) best = r;
    }
    return best;
  }
  function chassisForCard(card) {
    var c = cardFor(card);
    if (!c) return null;
    var cr = c.rig || {};
    var direct = rig(cr.rigId);
    if (direct) return { rig: direct, card: c, source: 'canon' };
    var fam = familyTop(cr.rigFamily || 'muscle') || RIGS[0];
    return { rig: fam, card: c, source: 'family_top' };
  }
  // The chassis id the garage panel should edit for a given dog. This is the join:
  // the garage writes p.garage.rigs[thisId], the world reads p.garage.rigs[thisId].
  function rigIdForCard(card) {
    var m = chassisForCard(card);
    return m ? m.rig.id : '';
  }

  // The mount the dog is actually sitting in. If the save already pairs THIS dog to
  // this chassis we honour the stored mount; otherwise the dog is assumed to be
  // driving its own rig, which is the sane default for a hero card in the world.
  function mountForCard(chassisId, card, p) {
    var st = rigState(chassisId, p);
    var c = cardFor(card);
    var num = c ? String(c.cardNumber || '') : '';
    if (st.dog && st.dog.card === num && MOUNTS[st.dog.mount]) return st.dog.mount;
    return 'driver';
  }

  // ---- rigStats: the SAME computeStats the panel prints, dog already paired ----
  function rigStats(card, p) {
    var m = chassisForCard(card);
    if (!m) return null;
    var mount = mountForCard(m.rig.id, m.card, p);
    var cs = computeStats(m.rig.id, { profile: p, dog: m.card, mount: mount });
    if (!cs) return null;
    cs.card = m.card.name || '';
    cs.cardNumber = String(m.card.cardNumber || '');
    cs.chassisSource = m.source;         // 'canon' | 'family_top'
    return cs;
  }

  // ---- rigLootMult: AK-FIX-lane-H 2026-07-28. THE GARAGE FINALLY PAYS OUT ----
  // The rig stats were inert -- nothing outside the panel read them for balance. A built
  // rig now HAULS MORE: the ADDED payload over the bare chassis (parts + a paired dog)
  // lifts raid loot a little. Delta-based, so a stock rig is exactly 1x (no free baseline);
  // clamped, so a maxed hauler is a bonus and never an exploit. Pure + guarded: pass a card
  // to score that dog's rig, or nothing to use the active rig; any gap reads a flat 1x.
  var RIG_LOOT_PER_PAYLOAD = 0.06;   // +6% raid loot per chassis-unit of ADDED payload
  var RIG_LOOT_MULT_MAX = 1.5;       // a fully-kitted hauler tops out at +50%
  function rigLootMult(card, p) {
    try {
      var cs = null;
      if (card != null) cs = rigStats(card, p);
      else { var id = activeRig(p); cs = id ? computeStats(id, { profile: p }) : null; }
      if (!cs || !cs.stats || !cs.base) return 1;
      var addPayload = Math.max(0, (+cs.stats.payload || 0) - (+cs.base.payload || 0));
      return clampN(1 + RIG_LOOT_PER_PAYLOAD * addPayload, 1, RIG_LOOT_MULT_MAX);
    } catch (_e) { return 1; }
  }

  // ---- rigVisual: everything a renderer needs, derived from the same state ----
  // decals/tint/glow are a pure function of the equipped parts, so bolting a Kingz
  // Custom part on in the garage is what puts gold on the rig in the district. The
  // renderer never decides; it draws what this returns.
  function buildVisual(card, p) {
    var m = chassisForCard(card);
    if (!m) return null;
    var r = m.rig, c = m.card, cr = c.rig || {};
    var fam = FAMILY[r.family] || FAMILY.muscle;
    var st = rigState(r.id, p);
    var mount = mountForCard(r.id, c, p);
    var cs = computeStats(r.id, { profile: p, dog: c, mount: mount });

    // decals: one per non-stock part, plus the signature crown when the pairing is canon
    var decals = [], top = null, glow = 0, i, slot, pd;
    for (i = 0; i < SLOTS.length; i++) {
      slot = SLOTS[i]; pd = st.parts[slot] ? PARTS[st.parts[slot]] : null;
      if (!pd || pd.tierIndex === 0) continue;
      decals.push({ slot: slot, key: TIER[pd.tier].key, tier: pd.tier, name: pd.name,
                    color: pd.color, glow: pd.glow, drama: pd.drama });
      if (!top || pd.tierIndex > top.tierIndex) top = pd;
      if (pd.glow > glow) glow = pd.glow;
    }
    if (cs && cs.pairing && cs.pairing.signature) {
      decals.push({ slot: 'signature', key: 'kingz', tier: 'Signature', name: 'Crown Pairing',
                    color: '#e8c55a', glow: 1, drama: 'the crown mark, earned by a canon pairing' });
      if (glow < 1) glow = 1;
    }

    var mountPoints = [], k, g2;
    for (k in MOUNTS) {
      g2 = MOUNT_GEOM[k] || MOUNT_GEOM.solo;
      mountPoints.push({
        id: k, label: MOUNTS[k].label, reads: MOUNTS[k].reads,
        ox: g2.ox, oy: g2.oy, oz: g2.oz, radius: fam.radius,
        occupied: (k === mount),
        dog: (k === mount) ? (c.name || '') : '',
        card: (k === mount) ? String(c.cardNumber || '') : ''
      });
    }

    var weapons = [];
    for (i = 0; i < st.hp.length; i++) weapons.push({ id: st.hp[i].w, rarity: st.hp[i].r, attach: st.hp[i].at.slice() });

    return {
      rigId: r.id, name: r.name, family: r.family, crew: r.crew, rarity: r.rarity,
      card: c.name || '', cardNumber: String(c.cardNumber || ''), chassisSource: m.source,
      rigName: cr.name || r.name,             // the card's own name for its rig, when it has one
      // 3D first, 2D always. Both paths are strings a renderer can try in order and
      // fall through, exactly like renderStage() does inside the panel.
      model: MODELS + 'rig_' + r.id.replace(/^rig_/, '') + '.glb',
      art: RIGART + r.id + '.webp',
      fallbackArt: FALLBACK_ART,
      tint: (top ? top.color : fam.tint),
      baseTint: fam.tint,
      glow: glow,
      topTier: top ? top.tier : 'Stock',
      decals: decals,
      mountPoints: mountPoints,
      weapons: weapons,
      weaponMod: cr.weaponMod || '',
      radius: fam.radius,
      deck: fam.deck
    };
  }

  function rigVisual(card, p) {
    var key = cardKey(card);
    if (!key) return null;
    var now = Date.now(), hit = _visCache[key];
    if (hit && hit.rev === _rev && (now - hit.at) < CACHE_MS && !p) return hit.v;
    var v = buildVisual(card, p);
    if (!p) _visCache[key] = { rev: _rev, at: now, v: v };
    return v;
  }

  // =========================================================================
  // 6c. TEST DRIVE -- pure. Turns the stat block into numbers a player can feel.
  //
  // These four readouts are FEEL, derived transparently from the stats above; they
  // are not new balance and nothing else in the game reads them. The chassis numbers
  // still come from the bible and only from the bible. Pure and headless, so the
  // server can score a drive with the identical function later.
  // =========================================================================
  function testDrive(rigId, opts) {
    var cs = (rigId && typeof rigId === 'object' && rigId.stats) ? rigId : computeStats(rigId, opts);
    if (!cs) return null;
    var s = cs.stats;
    var mass = 1 + (s.armor * 0.085) + (s.payload * 0.05);            // 1.0 .. ~2.3
    var topSpeed = Math.round(38 + s.speed * 9.2);                    // mph
    var s060 = round2(clampN((mass * 26) / Math.max(1, s.speed + 1.5), 1.9, 14));
    var grip = round2(clampN(0.55 + s.handling * 0.055, 0.5, 1.4));   // lateral g
    var slalom = round2(clampN((mass * 8.2) / grip / Math.max(1, 1 + s.handling * 0.16), 3.4, 22));
    var brake = Math.round((topSpeed * topSpeed) / (250 * grip));     // ft from top
    var notes = [];
    if (s.speed >= 9) notes.push('Pulls hard past the second block.');
    if (s.handling >= 8) notes.push('Turns in flat, no wallow.');
    if (s.armor >= 9) notes.push('Heavy. It stops when it feels like it.');
    if (mass > 1.9 && s.handling < 4) notes.push('Understeers wide. Brake earlier than you want to.');
    if (!notes.length) notes.push('Honest and unremarkable, which is its own kind of useful.');
    return { rigId: cs.rigId, name: cs.name, topSpeed: topSpeed, s060: s060,
             grip: grip, slalom: slalom, brake: brake, mass: round2(mass), notes: notes };
  }

  // =========================================================================
  // 7. UI -- guarded, no innerHTML, model-viewer turntable with a 2D fallback.
  // The vehicle is the showpiece, so it gets the same treatment hub3d.js gives
  // the hero: a live rotating mesh when one exists, the rig's flat art when it
  // does not, and a lettered plate when neither has shipped yet. Fully usable
  // today with zero rig meshes, and it upgrades itself as meshes land.
  // =========================================================================
  var el = null, curRig = '', curSlot = 'engine', _dragOff = null;

  // the colour the rig currently wears: its highest equipped tier, else its family.
  // Same rule buildVisual() uses for .tint, so the test-drive rig and the rig in the
  // district are painted by one decision, not two.
  function topTierColor(cs, family) {
    var top = null;
    if (cs && cs.contrib) {
      for (var i = 0; i < cs.contrib.length; i++) {
        var c = cs.contrib[i];
        if (c.empty || !c.tier) continue;
        var ti = TIER[c.tier] ? TIER[c.tier].i : 0;
        if (!top || ti > top.i) top = { i: ti, color: c.color };
      }
    }
    return top ? top.color : ((FAMILY[family] || FAMILY.muscle).tint);
  }

  function clear(node) { while (node && node.firstChild) node.removeChild(node.firstChild); }

  function h(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'style') n.style.cssText = attrs[k];
      else if (k === 'on') { for (var e in attrs[k]) n.addEventListener(e, attrs[k][e]); }
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function css() {
    return '#ak-gar{position:fixed;inset:0;z-index:62;background:rgba(6,6,10,.95);display:flex;'
      + 'flex-direction:column;font-family:Inter,system-ui,sans-serif;color:#e8e8e8;}'
      + '#ak-gar .g-h{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid rgba(232,197,90,.25);}'
      + '#ak-gar .g-t{font-weight:900;letter-spacing:1px;color:#e8c55a;font-size:15px;}'
      + '#ak-gar .g-sub{font-size:11px;color:#9aa3ad;}'
      + '#ak-gar .g-x{margin-left:auto;background:none;border:1px solid rgba(232,197,90,.4);color:#e8c55a;'
      + 'border-radius:8px;padding:6px 12px;font-weight:800;}'
      + '#ak-gar .g-body{flex:1;display:flex;gap:14px;padding:12px 16px 16px;overflow:hidden;}'
      + '#ak-gar .g-view{width:280px;display:flex;flex-direction:column;gap:8px;}'
      + '#ak-gar .g-stage{height:220px;border-radius:12px;border:1px solid rgba(232,197,90,.22);'
      + 'background:radial-gradient(circle at 50% 70%,rgba(232,197,90,.10),rgba(255,255,255,.02));'
      + 'display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative;}'
      + '#ak-gar .g-stage img{max-width:92%;max-height:92%;object-fit:contain;}'
      + '#ak-gar .g-stage model-viewer{width:100%;height:100%;background:transparent;}'
      + '#ak-gar .g-plate{font:900 20px Inter,system-ui;color:#e8c55a;letter-spacing:2px;text-align:center;padding:12px;}'
      + '#ak-gar .g-bars{display:flex;flex-direction:column;gap:5px;}'
      + '#ak-gar .g-bar{display:flex;align-items:center;gap:7px;font-size:10px;color:#9aa3ad;letter-spacing:.5px;}'
      + '#ak-gar .g-bar b{width:64px;font-weight:800;color:#cfd4da;}'
      + '#ak-gar .g-tr{flex:1;height:7px;border-radius:4px;background:rgba(255,255,255,.07);overflow:hidden;}'
      + '#ak-gar .g-fill{height:100%;border-radius:4px;}'
      + '#ak-gar .g-num{width:34px;text-align:right;font-weight:800;color:#e8e8e8;}'
      + '#ak-gar .g-cols{flex:1;display:flex;gap:12px;overflow:hidden;}'
      + '#ak-gar .g-slots{width:180px;display:flex;flex-direction:column;gap:5px;overflow:auto;}'
      + '#ak-gar .g-slot{padding:8px 10px;border-radius:9px;border:1px solid rgba(255,255,255,.10);'
      + 'background:rgba(255,255,255,.03);text-align:left;color:#cfd4da;font-size:11px;font-weight:700;}'
      + '#ak-gar .g-slot.on{border-color:#e8c55a;background:rgba(232,197,90,.12);color:#e8c55a;}'
      + '#ak-gar .g-slot span{display:block;font-size:9px;font-weight:600;color:#9aa3ad;margin-top:2px;}'
      + '#ak-gar .g-parts{flex:1;display:flex;flex-direction:column;gap:6px;overflow:auto;}'
      + '#ak-gar .g-part{padding:9px 11px;border-radius:10px;border:1px solid rgba(255,255,255,.10);'
      + 'background:rgba(255,255,255,.03);text-align:left;}'
      + '#ak-gar .g-part.on{border-width:2px;}'
      + '#ak-gar .g-pn{font-size:12px;font-weight:800;}'
      + '#ak-gar .g-pd{font-size:10px;color:#9aa3ad;margin-top:3px;line-height:1.5;}'
      + '#ak-gar .g-cap{font-size:10px;color:#9aa3ad;padding:2px 0;}'
      + '#ak-gar .g-sig{font-size:10px;color:#e8c55a;line-height:1.5;}'
      // AK-GARAGE 2026-07-18: turntable light-rig gradient, drag-to-slot, preview, test drive
      + '#ak-gar .g-key{position:absolute;inset:0;pointer-events:none;z-index:0;}'
      + '#ak-gar .g-stage img{position:relative;z-index:1;transition:none;will-change:transform;}'
      + '#ak-gar .g-slot.drop{border-color:#7ee787;background:rgba(126,231,135,.14);color:#7ee787;}'
      + '#ak-gar .g-slot.stage{border-color:#e8c55a;border-style:dashed;}'
      + '#ak-gar .g-part{touch-action:none;cursor:grab;}'
      + '#ak-gar .g-part.lift{opacity:.45;}'
      + '#ak-gar .g-ghost{position:fixed;z-index:64;pointer-events:none;padding:7px 10px;border-radius:9px;'
      + 'font:800 11px Inter,system-ui;background:rgba(12,12,18,.96);border:1px solid #e8c55a;color:#e8c55a;'
      + 'box-shadow:0 10px 26px rgba(0,0,0,.6);transform:translate(-50%,-140%);}'
      + '#ak-gar .g-prev{border:1px solid rgba(232,197,90,.45);border-radius:11px;padding:10px 11px;'
      + 'background:rgba(232,197,90,.07);display:flex;flex-direction:column;gap:7px;}'
      + '#ak-gar .g-prev-t{font:900 11px Inter,system-ui;color:#e8c55a;letter-spacing:.6px;}'
      + '#ak-gar .g-dr{display:flex;align-items:center;gap:8px;font-size:11px;}'
      + '#ak-gar .g-dr b{width:70px;font-weight:700;color:#9aa3ad;text-transform:uppercase;font-size:9px;letter-spacing:.5px;}'
      + '#ak-gar .g-dv{color:#cfd4da;font-weight:700;width:34px;text-align:right;}'
      + '#ak-gar .g-da{font-weight:900;width:52px;}'
      + '#ak-gar .g-up{color:#7ee787;}#ak-gar .g-dn{color:#ff8f6b;}#ak-gar .g-nc{color:#6b727a;}'
      + '#ak-gar .g-btns{display:flex;gap:7px;}'
      + '#ak-gar .g-ok{flex:1;background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#15110a;border:0;'
      + 'border-radius:9px;padding:9px 0;font-weight:900;font-size:12px;}'
      + '#ak-gar .g-no{flex:0 0 auto;background:none;border:1px solid rgba(255,255,255,.20);color:#9aa3ad;'
      + 'border-radius:9px;padding:9px 13px;font-weight:800;font-size:12px;}'
      + '#ak-gar .g-drive{width:100%;background:none;border:1px solid rgba(127,200,255,.5);color:#7fc8ff;'
      + 'border-radius:9px;padding:9px 0;font-weight:800;font-size:12px;letter-spacing:.5px;}'
      + '#ak-gar .g-arena{display:flex;flex-direction:column;gap:8px;}'
      + '#ak-gar .g-arena canvas{width:100%;height:74px;border-radius:10px;border:1px solid rgba(127,200,255,.25);'
      + 'background:linear-gradient(180deg,rgba(127,200,255,.06),rgba(0,0,0,.30));display:block;}'
      + '#ak-gar .g-tdg{display:grid;grid-template-columns:1fr 1fr;gap:5px;}'
      + '#ak-gar .g-tdc{border:1px solid rgba(255,255,255,.10);border-radius:9px;padding:7px 9px;}'
      + '#ak-gar .g-tdk{font-size:9px;color:#9aa3ad;letter-spacing:.6px;font-weight:700;}'
      + '#ak-gar .g-tdv{font:900 15px Inter,system-ui;color:#7fc8ff;margin-top:1px;}'
      + '#ak-gar .g-tdn{font-size:10px;color:#9aa3ad;line-height:1.55;}'
      // the footer carries preview + test drive so BOTH survive the mobile breakpoint
      // that hides .g-view. A confirm you cannot reach on a phone is not a confirm.
      + '#ak-gar .g-foot{flex:0 0 auto;padding:0 16px 14px;display:flex;flex-direction:column;gap:9px;}'
      + '@media(max-width:760px){#ak-gar .g-view{display:none;}#ak-gar .g-slots{width:132px;}}';
  }

  function statBar(label, val, max, color) {
    var pct = Math.max(0, Math.min(100, (val / max) * 100));
    return h('div', { class: 'g-bar' }, [
      h('b', { text: label }),
      h('div', { class: 'g-tr' }, [h('div', { class: 'g-fill', style: 'width:' + pct.toFixed(0) + '%;background:' + color + ';' })]),
      h('div', { class: 'g-num', text: String(val) })
    ]);
  }

  // 3D first, then the rig's own art, then a lettered plate. Never a blank box.
  function renderStage(box, r) {
    stopTurntable();
    clear(box);
    var has3d = false;
    try { has3d = !!(global.customElements && customElements.get('model-viewer')); } catch (_e) {}
    if (has3d && r.mesh !== false) {
      var mv = document.createElement('model-viewer');
      mv.setAttribute('src', MODELS + 'rig_' + r.id.replace(/^rig_/, '') + '.glb');
      mv.setAttribute('camera-controls', ''); mv.setAttribute('auto-rotate', '');
      mv.setAttribute('rotation-per-second', '18deg');
      mv.setAttribute('interaction-prompt', 'none'); mv.setAttribute('shadow-intensity', '0');
      mv.setAttribute('exposure', '1.15');
      mv.addEventListener('error', function () { renderFlat(box, r); });
      box.appendChild(mv);
      return;
    }
    renderFlat(box, r);
  }
  function renderFlat(box, r) {
    clear(box);
    var img = h('img', { src: RIGART + r.id + '.webp', alt: r.name });
    img.addEventListener('error', function () {
      if (!img._fb) { img._fb = 1; img.src = FALLBACK_ART; return; }
      if (img.parentNode) img.parentNode.removeChild(img);
      box.appendChild(h('div', { class: 'g-plate', text: r.name.toUpperCase() }));
    });
    box.appendChild(img);
    startTurntable(box, img, r);
  }

  // ---- the turntable, driven by the REAL GarageCamera ----------------------
  // AK-GARAGE 2026-07-18. systems/cameras/GarageCamera.js is already written and
  // already loaded (index.html:434) and had no consumer. It is one now.
  //
  // THREE is not vendored yet, so the mode reports degraded and builds no lights. Its
  // header documents exactly this case: "when THREE is absent lights() still returns
  // the same data, so a 2D or CSS presentation can drive a gradient with it." That is
  // what happens here. The mode owns the turntable math (0.22 rad/s drift, drag to
  // scrub, 1.6s idle before the drift eases back in) and this code only paints it:
  // theta becomes a CSS yaw on the rig art, and the three-point rig becomes the key
  // and rim gradients behind and across it. When three.min.js lands the SAME mode
  // starts returning real lights and the model-viewer path takes over, with no change
  // to the turntable feel, because the feel was never implemented here.
  var _tt = null;
  function stopTurntable() {
    if (!_tt) return;
    try { if (_tt.raf) global.cancelAnimationFrame(_tt.raf); } catch (_e) {}
    try { if (_tt.mode && _tt.mode.exit) _tt.mode.exit(_tt.env); } catch (_e2) {}
    try {
      if (_tt.box && _tt.onPtr) {
        ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'wheel'].forEach(function (n) {
          _tt.box.removeEventListener(n, _tt.onPtr);
        });
      }
    } catch (_e3) {}
    _tt = null;
  }
  function startTurntable(box, img, r) {
    try {
      var CM = global.AK_CAMERAS;
      var mode = CM && CM.get ? CM.get('garage') : null;
      var P = (CM && CM.P) || global.AK_PROJ;
      if (!mode || !P || !P.state || typeof global.requestAnimationFrame !== 'function') return;

      var fam = FAMILY[r.family] || FAMILY.muscle;
      var env = {
        id: 'garage', ctx: null, P: P,
        opts: { subject: { x: 0, y: 0, z: 0, radius: fam.radius }, fov: mode.FOV },
        state: P.state({}),
        three: null, degraded: true,
        vp: { w: box.clientWidth || 280, h: box.clientHeight || 220, dpr: 1 },
        overlay: null
      };
      if (mode.enter) mode.enter(env);

      var onPtr = function (e) { try { if (mode.pointer) mode.pointer(e, env); } catch (_e) {} };
      ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'wheel'].forEach(function (n) {
        box.addEventListener(n, onPtr, { passive: true });
      });

      var glowEl = h('div', { class: 'g-key' });
      box.insertBefore(glowEl, box.firstChild);

      var t0 = (global.performance && global.performance.now) ? global.performance.now() : Date.now();
      _tt = { mode: mode, env: env, box: box, onPtr: onPtr, raf: 0 };

      var step = function (t) {
        if (!_tt) return;
        var dt = Math.min(0.05, (t - t0) / 1000); t0 = t;
        try { if (mode.update) mode.update(dt, env); } catch (_e) {}
        var s = env.state;
        // yaw the flat art as if the camera were orbiting it: the silhouette squashes
        // toward edge-on at the quarters, which is what sells a turntable in 2D.
        var yaw = Math.cos(s.theta);
        try {
          img.style.transform = 'perspective(720px) rotateY(' + (yaw * 26).toFixed(2) + 'deg) '
            + 'scaleX(' + (0.82 + 0.18 * Math.abs(yaw)).toFixed(3) + ')';
        } catch (_e2) {}
        // the mode's three-point rig, as a gradient. key follows the camera, rim sits
        // opposite it, so the gold edge stays on the silhouette through the whole lap.
        try {
          var L = mode.lights ? mode.lights(env) : [];
          var key = L[0], rimL = L[2];
          if (key && rimL && glowEl) {
            var kx = 50 + 42 * Math.cos(s.theta - 0.60), ky = 62 - 20 * Math.sin(s.phi);
            var rx = 50 + 46 * Math.cos(s.theta + Math.PI * 0.92);
            glowEl.style.background =
              'radial-gradient(circle at ' + kx.toFixed(1) + '% ' + ky.toFixed(1) + '%,rgba(255,242,208,.20),rgba(255,242,208,0) 58%),'
              + 'radial-gradient(circle at ' + rx.toFixed(1) + '% 46%,rgba(232,197,90,.26),rgba(232,197,90,0) 52%)';
          }
        } catch (_e3) {}
        _tt.raf = global.requestAnimationFrame(step);
      };
      _tt.raf = global.requestAnimationFrame(step);
    } catch (_e) { _tt = null; }
  }

  function open(opts) {
    try {
      if (typeof document === 'undefined' || !document.body) return;
      opts = opts || {};
      close();
      curRig = opts.rigId || activeRig() || RIGS[0].id;
      curSlot = opts.slot || 'engine';
      var r = rig(curRig);
      if (!r) return;

      var stage = h('div', { class: 'g-stage' });
      var bars = h('div', { class: 'g-bars' });
      var slotCol = h('div', { class: 'g-slots' });
      var partCol = h('div', { class: 'g-parts' });
      var sub = h('div', { class: 'g-sub', text: '' });
      var foot = h('div', { class: 'g-foot' });

      // AK-GARAGE 2026-07-18: the staged part. Dropping a part on a slot does NOT
      // equip it. It stages it, the footer prints the real before/after delta from
      // computeStats (pure, opts.parts, zero writes), and only CONFIRM calls equip().
      // Nothing reaches the save file until the player has seen what it costs him.
      var staged = null;          // { slot, partId }

      function stagedParts() {
        var cs0 = computeStats(curRig), merged = {}, k;
        for (k in cs0.parts) merged[k] = cs0.parts[k];
        if (staged) {
          if (staged.partId) merged[staged.slot] = staged.partId;
          else delete merged[staged.slot];
        }
        return merged;
      }

      // The delta strip: current stat, arrow, what it becomes, how much it moved.
      // Both sides come from the SAME computeStats, so the preview cannot drift from
      // what actually lands when CONFIRM is pressed.
      function paintPreview() {
        clear(foot);
        if (!staged) {
          foot.appendChild(h('button', {
            class: 'g-drive', text: '> TEST DRIVE',
            on: { click: function () { openArena(curRig, null); } }
          }));
          return;
        }
        var now = computeStats(curRig);
        var next = computeStats(curRig, { parts: stagedParts() });
        if (!now || !next) { staged = null; paintPreview(); return; }
        var pd = staged.partId ? PARTS[staged.partId] : null;
        var box = h('div', { class: 'g-prev' }, [
          h('div', { class: 'g-prev-t',
            text: (pd ? pd.name.toUpperCase() : 'STRIP TO STOCK') + '  ->  ' + SLOT_LABEL[staged.slot].toUpperCase() })
        ]);
        var keys = STAT_KEYS.concat(['hp']), moved = false;
        for (var i = 0; i < keys.length; i++) {
          var k = keys[i];
          var a = (k === 'hp') ? now.stats.hp : now.spec[k];
          var b = (k === 'hp') ? next.stats.hp : next.spec[k];
          var d = b - a;
          if (d) moved = true;
          box.appendChild(h('div', { class: 'g-dr' }, [
            h('b', { text: k === 'hp' ? 'HULL' : k }),
            h('span', { class: 'g-dv', text: String(a) }),
            h('span', { class: 'g-nc', text: '->' }),
            h('span', { class: 'g-dv', text: String(b) }),
            h('span', { class: 'g-da ' + (d > 0 ? 'g-up' : (d < 0 ? 'g-dn' : 'g-nc')),
                        text: d > 0 ? ('+' + d) : (d < 0 ? String(d) : '--') })
          ]));
        }
        if (!moved) box.appendChild(h('div', { class: 'g-tdn', text: 'No change. This is what is already bolted on.' }));
        else if (pd && pd.drama) box.appendChild(h('div', { class: 'g-tdn', text: pd.drama }));
        box.appendChild(h('div', { class: 'g-btns' }, [
          h('button', { class: 'g-ok', text: moved ? 'CONFIRM AND BOLT IT ON' : 'ALREADY FITTED',
            on: { click: function () {
              if (!staged) return;
              // the ONE write, and the only one this panel performs
              if (staged.partId) equip(curRig, staged.slot, staged.partId);
              else unequip(curRig, staged.slot);
              staged = null;
              paint();
            } } }),
          h('button', { class: 'g-no', text: 'CANCEL',
            on: { click: function () { staged = null; paint(); } } })
        ]));
        // feel it BEFORE you commit it: the drive-by runs on the staged build, not the
        // saved one, which is the only version of this button that changes a decision.
        box.appendChild(h('button', {
          class: 'g-drive', text: '> TEST DRIVE THIS BUILD',
          on: { click: function () { openArena(curRig, stagedParts()); } }
        }));
        foot.appendChild(box);
      }

      // ---- pointer drag: part card -> slot button ---------------------------
      // Pointer events, not HTML5 drag-and-drop: this is a phone game first, and
      // dragstart never fires on touch. A drag that ends anywhere but a slot is a
      // no-op; a press that never moves falls through to the click handler, so the
      // whole thing stays usable with one thumb and with a mouse.
      var drag = null;
      function slotUnder(x, y) {
        var kids = slotCol.childNodes;
        for (var i = 0; i < kids.length; i++) {
          var el2 = kids[i];
          if (!el2 || !el2.getBoundingClientRect) continue;
          var b = el2.getBoundingClientRect();
          if (x >= b.left && x <= b.right && y >= b.top && y <= b.bottom) return { el: el2, slot: el2._slot };
        }
        return null;
      }
      function clearDrop() {
        var kids = slotCol.childNodes;
        for (var i = 0; i < kids.length; i++) { try { kids[i].classList.remove('drop'); } catch (_e) {} }
      }
      function endDrag(commit, x, y) {
        if (!drag) return;
        try { drag.node.classList.remove('lift'); } catch (_e) {}
        try { if (drag.ghost && drag.ghost.parentNode) drag.ghost.parentNode.removeChild(drag.ghost); } catch (_e2) {}
        clearDrop();
        var hit = commit ? slotUnder(x, y) : null;
        var pd = drag.pd;
        drag = null;
        if (hit && hit.slot === pd.slot) {                 // a part only fits its own slot
          curSlot = pd.slot;
          staged = { slot: pd.slot, partId: pd.tierIndex === 0 ? '' : pd.id };
          paint();
        } else if (hit) {
          staged = null;
          paint();
          try { if (global.showBanner) global.showBanner(pd.name + ' does not fit the ' + SLOT_LABEL[hit.slot] + ' mount', 1.6); } catch (_e3) {}
        }
      }
      function onMove(e) {
        if (!drag) return;
        var x = e.clientX, y = e.clientY;
        if (!drag.live) {
          if (Math.abs(x - drag.x0) + Math.abs(y - drag.y0) < 8) return;
          drag.live = true;
          try { drag.node.classList.add('lift'); } catch (_e) {}
          drag.ghost = h('div', { class: 'g-ghost', text: drag.pd.name });
          document.body.appendChild(drag.ghost);
        }
        if (drag.ghost) { drag.ghost.style.left = x + 'px'; drag.ghost.style.top = y + 'px'; }
        clearDrop();
        var hit = slotUnder(x, y);
        if (hit && hit.el) { try { hit.el.classList.add('drop'); } catch (_e2) {} }
      }
      function onUp(e) { if (drag) endDrag(!!drag.live, e.clientX, e.clientY); }
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', onUp);
      document.addEventListener('pointercancel', onUp);
      _dragOff = function () {
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', onUp);
        document.removeEventListener('pointercancel', onUp);
      };

      // ---- TEST DRIVE: real numbers plus a scripted drive-by ----------------
      // A strip of asphalt the rig actually crosses, timed by testDrive() off the
      // CURRENT stat block (staged part included, so you can feel a part before you
      // buy it). The pass is scripted, not a driveable arena: the rig launches, hits
      // the computed top speed, brakes at the far cone. Stats drive every number on
      // screen and the speed of the animation, so the tuning is legible in motion.
      function openArena(rigId, previewParts) {
        var o = previewParts ? { parts: previewParts } : null;
        var td = testDrive(rigId, o);
        if (!td) return;
        td._tint = topTierColor(computeStats(rigId, o), rig(rigId) && rig(rigId).family);
        clear(foot);
        var cvs = document.createElement('canvas');
        cvs.width = 560; cvs.height = 148;
        var grid = h('div', { class: 'g-tdg' }, [
          h('div', { class: 'g-tdc' }, [h('div', { class: 'g-tdk', text: 'TOP SPEED' }), h('div', { class: 'g-tdv', text: td.topSpeed + ' mph' })]),
          h('div', { class: 'g-tdc' }, [h('div', { class: 'g-tdk', text: '0 TO 60' }), h('div', { class: 'g-tdv', text: td.s060.toFixed(2) + ' s' })]),
          h('div', { class: 'g-tdc' }, [h('div', { class: 'g-tdk', text: 'SLALOM' }), h('div', { class: 'g-tdv', text: td.slalom.toFixed(2) + ' s' })]),
          h('div', { class: 'g-tdc' }, [h('div', { class: 'g-tdk', text: 'GRIP' }), h('div', { class: 'g-tdv', text: td.grip.toFixed(2) + ' g' })])
        ]);
        foot.appendChild(h('div', { class: 'g-arena' }, [
          cvs, grid,
          h('div', { class: 'g-tdn', text: td.notes.join('  ') + '  Brakes from top in ' + td.brake + ' ft.' }),
          h('div', { class: 'g-btns' }, [
            h('button', { class: 'g-ok', text: 'RUN IT AGAIN', on: { click: function () { openArena(rigId, previewParts); } } }),
            h('button', { class: 'g-no', text: 'DONE', on: { click: function () { stopArena(); paintPreview(); } } })
          ])
        ]));
        runArena(cvs, td, rig(rigId));
      }

      function paint() {
        var cs = computeStats(curRig);
        if (!cs) return;
        sub.textContent = r.name.toUpperCase() + '  |  ' + r.rarity + ' ' + r.family
          + '  |  ' + cs.capacity.used + '/' + cs.capacity.hardpoints + ' hardpoints';

        clear(bars);
        bars.appendChild(statBar('ARMOR', cs.spec.armor, 200, '#7fc8ff'));
        bars.appendChild(statBar('SPEED', cs.spec.speed, 200, '#7ee787'));
        bars.appendChild(statBar('HANDLING', cs.spec.handling, 200, '#e8c55a'));
        bars.appendChild(statBar('PAYLOAD', cs.spec.payload, 200, '#b48ead'));
        bars.appendChild(statBar('DAMAGE', cs.spec.damage, 200, '#ff8f6b'));
        bars.appendChild(h('div', { class: 'g-cap', text: 'HULL ' + cs.stats.hp + ' hp' }));
        if (cs.pairing.signature) bars.appendChild(h('div', { class: 'g-sig', text: 'SIGNATURE: ' + cs.pairing.note }));
        else if (cs.pairing.risk) bars.appendChild(h('div', { class: 'g-sig', text: cs.pairing.note }));

        clear(slotCol);
        for (var i = 0; i < SLOTS.length; i++) {
          (function (slot) {
            var c = null;
            for (var j = 0; j < cs.contrib.length; j++) if (cs.contrib[j].slot === slot) c = cs.contrib[j];
            var isStaged = !!(staged && staged.slot === slot);
            var btn = h('button', {
              class: 'g-slot' + (slot === curSlot ? ' on' : '') + (isStaged ? ' stage' : ''),
              on: { click: function () { curSlot = slot; paint(); } }
            }, [
              h('div', { text: SLOT_LABEL[slot].toUpperCase() }),
              h('span', { text: isStaged ? ((staged.partId ? PARTS[staged.partId].name : 'Stock') + '  (staged)') : (c ? c.name : 'Stock') })
            ]);
            btn._slot = slot;                        // read by slotUnder() during a drag
            slotCol.appendChild(btn);
          })(SLOTS[i]);
        }

        clear(partCol);
        var list = partsForSlot(curSlot);
        var cur = cs.parts[curSlot] || (curSlot + ':stock');
        var stagedId = (staged && staged.slot === curSlot) ? (staged.partId || (curSlot + ':stock')) : '';
        for (var k = 0; k < list.length; k++) {
          (function (pd) {
            var bits = [], key;
            for (key in pd.deltas) { if (pd.deltas[key]) bits.push((pd.deltas[key] > 0 ? '+' : '') + spec(pd.deltas[key]) + ' ' + key); }
            var isOn = (pd.id === cur), isStage = (pd.id === stagedId);
            partCol.appendChild(h('button', {
              class: 'g-part' + (isOn ? ' on' : ''),
              style: 'border-color:' + (isStage ? '#e8c55a' : (isOn ? pd.color : 'rgba(255,255,255,.10)')) + ';'
                + (pd.glow ? 'box-shadow:0 0 ' + Math.round(pd.glow * 16) + 'px ' + pd.color + '55;' : ''),
              on: {
                // press starts a possible drag; a press that never moves falls through
                // to click, which stages the same part. Drag and tap end in one place.
                pointerdown: function (e) { drag = { pd: pd, node: this, x0: e.clientX, y0: e.clientY, live: false, ghost: null }; },
                click: function () {
                  curSlot = pd.slot;
                  staged = { slot: pd.slot, partId: pd.tierIndex === 0 ? '' : pd.id };
                  paint();
                }
              }
            }, [
              // the part NAME already carries its tier (Kingz Organ Stacks), so the tier
              // rides the detail line and the colour, not a redundant "PRO Pro ..." prefix
              h('div', { class: 'g-pn', style: 'color:' + pd.color + ';', text: pd.name }),
              h('div', { class: 'g-pd', text: (bits.length ? bits.join('   ') : 'no change') + '   |   ' + pd.drama })
            ]));
          })(list[k]);
        }

        stopArena();
        paintPreview();
      }

      el = h('div', { id: 'ak-gar' }, [
        h('style', { text: css() }),
        h('div', { class: 'g-h' }, [
          h('div', { class: 'g-t', text: 'THE GARAGE' }), sub,
          // The Garage used to BE the deck-builder link (index.html B('GARAGE',...,
          // 'shop/shop.html#deck')). Claiming the building would have deleted that
          // route, so it moves in here instead of disappearing.
          h('button', { class: 'g-x', text: 'DECK', on: { click: function () {
            try { global.location.href = 'shop/shop.html#deck'; } catch (_e) {}
          } } }),
          h('button', { class: 'g-x', text: 'CLOSE', on: { click: close } })
        ]),
        h('div', { class: 'g-body' }, [
          h('div', { class: 'g-view' }, [stage, bars]),
          h('div', { class: 'g-cols' }, [slotCol, partCol])
        ]),
        foot
      ]);
      renderStage(stage, r);
      paint();
      document.body.appendChild(el);
    } catch (_e) {
      // AK-GARAGE 2026-07-18: a bare `catch(_e){}` here turns any fault in the panel
      // into a walk-in that opens nothing at all, with no trace of why. The guard
      // stays (a broken garage must never take the hub down with it) but it says so
      // now, and it tears down the half-built panel instead of leaving a dead sheet
      // of glass over the district.
      try { if (global.console && console.warn) console.warn('[AK_GARAGE] open failed', _e); } catch (_e2) {}
      try { close(); } catch (_e3) {}
    }
  }
  function close() {
    stopTurntable(); stopArena();
    try { if (_dragOff) _dragOff(); } catch (_e0) {}
    _dragOff = null;
    try { if (el && el.parentNode) el.parentNode.removeChild(el); } catch (_e) {}
    el = null;
  }

  // ---- the scripted drive-by -----------------------------------------------
  // AK-GARAGE 2026-07-18. Not a driveable arena: a timed pass down a strip, and every
  // number in it comes from testDrive(). A rig with 40 speed crawls the strip and a
  // rig with 121 crosses it in a blink, which is the point. Cancelled on close and on
  // every repaint, so no RAF ever outlives the panel.
  var _arena = null;
  function stopArena() {
    if (!_arena) return;
    try { global.cancelAnimationFrame(_arena); } catch (_e) {}
    _arena = null;
  }
  function runArena(cvs, td, r) {
    stopArena();
    var g2;
    try { g2 = cvs.getContext('2d'); } catch (_e) { return; }
    if (!g2) return;
    var W = cvs.width, H = cvs.height;
    var fam = FAMILY[(r && r.family) || 'muscle'] || FAMILY.muscle;
    var LANE = H * 0.62;
    // real seconds: launch (0-60 at the rig's own rate), a flat-out middle, then braking
    var tRun = td.s060 * 1.35 + 1.9, t0 = 0;
    function frame(t) {
      if (!_arena) return;
      if (!t0) t0 = t;
      var e = (t - t0) / 1000, u = clampN(e / tRun, 0, 1);
      // distance curve: accelerate hard, hold, brake into the far cone
      var d = (u < 0.62) ? (Math.pow(u / 0.62, 1.55) * 0.72)
                         : (0.72 + (1 - Math.pow(1 - (u - 0.62) / 0.38, 2)) * 0.28);
      var x = 26 + d * (W - 92);
      var mph = Math.round((u < 0.62 ? Math.pow(u / 0.62, 0.7) : (1 - (u - 0.62) / 0.38 * 0.55)) * td.topSpeed);

      g2.clearRect(0, 0, W, H);
      g2.fillStyle = 'rgba(255,255,255,.05)'; g2.fillRect(0, LANE + 16, W, 2);
      // dashed centre line, scrolling under the rig at the rig's own speed
      g2.fillStyle = 'rgba(255,255,255,.13)';
      for (var i = 0; i < 20; i++) {
        var lx = ((i * 46) - (d * (W - 92) * 0.9)) % (W + 46);
        if (lx < -30) lx += W + 46;
        g2.fillRect(lx, LANE + 7, 22, 2);
      }
      // start gate and the far cone it brakes for
      g2.fillStyle = 'rgba(126,231,135,.45)'; g2.fillRect(22, LANE - 14, 2, 28);
      g2.fillStyle = 'rgba(255,143,107,.55)'; g2.fillRect(W - 62, LANE - 14, 3, 28);

      // the rig: a plate the length of its family, lit by its own top-tier tint
      var w = 34 + fam.radius * 9, hh = 15 + fam.radius * 2.2;
      g2.save();
      g2.shadowColor = td._tint || '#e8c55a'; g2.shadowBlur = 12;
      g2.fillStyle = td._tint || '#c9a84c';
      g2.fillRect(x - w / 2, LANE - hh / 2, w, hh);
      g2.shadowBlur = 0;
      g2.fillStyle = 'rgba(0,0,0,.45)';
      g2.fillRect(x - w / 2 + 5, LANE - hh / 2 + 3, w * 0.38, hh * 0.42);
      g2.restore();
      // speed blur behind it, proportional to how fast it is actually going
      g2.strokeStyle = 'rgba(255,255,255,' + (0.05 + 0.16 * (mph / Math.max(1, td.topSpeed))).toFixed(3) + ')';
      g2.lineWidth = 1;
      for (var j = 1; j <= 4; j++) {
        g2.beginPath(); g2.moveTo(x - w / 2 - j * 13, LANE - 4 + j * 2); g2.lineTo(x - w / 2 - j * 5, LANE - 4 + j * 2); g2.stroke();
      }

      g2.fillStyle = '#7fc8ff'; g2.font = '900 13px Inter,system-ui'; g2.textAlign = 'left';
      g2.fillText(Math.max(0, mph) + ' mph', 10, 18);
      g2.fillStyle = '#9aa3ad'; g2.font = '700 10px Inter,system-ui';
      g2.fillText(e.toFixed(2) + ' s', 10, 33);
      g2.textAlign = 'right';
      g2.fillText((r && r.name ? r.name.toUpperCase() : 'RIG'), W - 10, 18);

      if (u >= 1) { _arena = null; return; }
      _arena = global.requestAnimationFrame(frame);
    }
    _arena = global.requestAnimationFrame(frame);
  }

  // =========================================================================
  // 8. REGISTRATION -- the consumer path. VERIFIED 2026-07-18 against index.html.
  //
  // Walking into a building runs index.html:2401
  //     if(dwellT>0.22 && !interiorOpen) enterInterior(near);
  // and enterInterior's FOURTH statement, index.html:1277, is
  //     if(window.AK_SYSTEMS && window.AK_CTX && AK_SYSTEMS.enterBuilding(b, AK_CTX)){ interiorOpen=true; return; }
  // That `return` is the whole claim. It fires BEFORE the generic keeper interior is
  // built and long before index.html:1332 `doEnter(interiorB.url, interiorB.label)`,
  // which is the only line that ever reads b.url. So claiming GARAGE here does
  // pre-empt the shop navigation, and index.html:694 can keep declaring
  //     B('GARAGE','THE GARAGE','#7fc8ff',1140,560,170,104,'shop/shop.html#deck','deck builder')
  // untouched: that url is now simply unreachable by walking in. No host edit needed.
  // _registry.js:18 enterBuilding is first-claim-wins and nothing else claims GARAGE
  // (production.js CFG covers GEM/MINT/FORGE/LAB/GEN only), so order does not matter.
  //
  // Same claim shape arcade.js uses (arcade.js:757 `if (!b || b.id !== 'ARCADE')`).
  // The deck-builder route the Garage used to be is preserved as the DECK button in
  // the panel header. Flip AK_GARAGE.claimBuilding = false to hand the walk-in back
  // to the keeper interior and drive the panel from a button instead.
  // =========================================================================
  var claimBuilding = true;
  var api = {
    id: 'garage',
    init: function () {},
    onEnterBuilding: function (b) {
      try {
        if (!claimBuilding) return false;
        var id = (b && (b.id || b.key)) || b || '';
        if (String(id).toUpperCase() !== 'GARAGE') return false;
        open({});
        return true;
      } catch (_e) { return false; }
    },
    onTick: function () {},
    onDrawWorld: function () {}
  };
  try { if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) global.AK_SYSTEMS.register(api); } catch (_e) {}

  global.AK_GARAGE = {
    // data
    RIGS: RIGS, SLOTS: SLOTS, TIERS: TIERS, TIER: TIER, PARTS: PARTS, MOUNTS: MOUNTS,
    SLOT_DELTA: SLOT_DELTA, SLOT_LABEL: SLOT_LABEL,
    HARDPOINTS: HARDPOINTS, ATTACH_SLOTS: ATTACH_SLOTS,
    HP_PER_ARMOR: HP_PER_ARMOR, SIGNATURE_MULT: SIGNATURE_MULT, SOLO_SHARE: SOLO_SHARE, SOLO_RISK: SOLO_RISK,
    rig: rig, rigList: rigList, part: part, partsForSlot: partsForSlot, hydrate: hydrate,
    // state (every write goes through AK_ECON.mutateProfile)
    rigState: rigState, sanitizeRig: sanitizeRig,
    equip: equip, unequip: unequip,
    mountWeapon: mountWeapon, unmountWeapon: unmountWeapon,
    attachToWeapon: attachToWeapon, detachFromWeapon: detachFromWeapon,
    setDog: setDog, clearDog: clearDog,
    activeRig: activeRig, setActiveRig: setActiveRig,
    // capacity (data-layer enforcement, not UI enforcement)
    hardpointsFor: hardpointsFor, attachSlotsFor: attachSlotsFor, weaponRarity: weaponRarity, capacity: capacity,
    // stats
    dogStats: dogStats, findCard: findCard, pairingFor: pairingFor,
    computeStats: computeStats, contribLines: contribLines,
    rigLootMult: rigLootMult,   // AK-FIX-lane-H 2026-07-28: equipped-rig raid-loot multiplier (raidscene.js reads this)
    // AK-GARAGE 2026-07-18 -- THE OUTWARD RESOLVERS. Everything outside the garage
    // that draws or fights a rig reads through exactly these two, so the district and
    // the raid cannot disagree with the garage: all three read one persisted state.
    // Both accept a card NAME or the card object heroCard() already returns.
    rigVisual: rigVisual, rigStats: rigStats,
    rigIdForCard: rigIdForCard, chassisForCard: chassisForCard, cardFor: cardFor,
    mountForCard: mountForCard, FAMILY: FAMILY, MOUNT_GEOM: MOUNT_GEOM,
    testDrive: testDrive,
    rev: function () { return _rev; },   // bumps on every write; cheap staleness check
    // ui
    open: open, close: close,
    get claimBuilding() { return claimBuilding; },
    set claimBuilding(v) { claimBuilding = !!v; }
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = global.AK_GARAGE;
  // globalThis (not `this`) on the node side: under CommonJS `this` is module.exports, and the
  // AK_ECON / CANON_CARDS lookups above would then read an empty object instead of the real
  // globals. Same resolution economy.js uses, so the harness sees the same world the hub does.
})(typeof window !== 'undefined' ? window : globalThis);
