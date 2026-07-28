/* game/systems/karma.js -- AK_SYSTEMS module: "karma" (the DEEP-DIVE glue, Part 3).
   ============================================================================
   DISTRICT SOCIAL KARMA -- the net-new connective tissue from
   AK_DEEP_DIVE_SYNTHESIS.md Part 3. A second reputation axis that runs ALONGSIDE
   combat Reputation: you earn it by HELPING the block, not by fighting. Each of
   the NeonReach districts belongs to one of the 4 canon crews (World Bible:
   The Crowned / The Rusted / The Hologhosts / The Unbound), plus the neutral
   Central Plaza (THE LOT / HOME_TURF). Karma is stored PER DISTRICT and unlocks
   missions, shop discounts, NPC dialog, building access + perks as it climbs the
   7 tiers (Stranger -> New Face -> Known -> Trusted -> Respected -> Revered ->
   Legend).

   THE HEADLINE MECHANIC -- FRIENDLY ENCOUNTERS:
   the wild-stray roamer roll (encounters.js wave 3) is re-weighted by your karma
   in the active district. Low karma = the block doesn't know you, so it's mostly
   HOSTILE strays. As karma climbs, the same roll skews toward FRIENDLY NPCs,
   RESOURCE caches, and rare SPECIAL story beats. The 5 friendly NPC types are:
     - Lost Pup        -> escort it home          (a real Common crew dog by name)
     - Injured Stray   -> patch it up             (a real Rare crew dog by name)
     - Merchant Caravan-> trade fair              (a real Epic crew dog by name)
     - Faction Recruiter-> hear a job             (a real Legendary crew dog by name)
     - Mysterious Stranger-> listen (story chain) (faceless -- the king/dealer TEASE)
   Each one GRANTS karma + a soft reward on a good interaction.

   CONTRACT COMPLIANCE (MODULE_CONTRACT.md):
   - Self-registers into window.AK_SYSTEMS; edits NO shared file. The hub already
     loads this via a <script src="systems/karma.js"> tag (the only host seam) and
     the falsy-default field p.karma:{} lives in economy.js ensureShape.
   - ALL player state via window.AK_ECON behind ONE falsy-default field:
       p.karma {}  (zoneId -> social-karma points; prestige resets it, 0% burn)
   - Public API on window.AKKarma (mirrors AKQuests / AK_COLLISION / AKHandlers).
     encounters.js consults global.AKKarma.rollEncounter + spawnFriendly (see the
     returned hook) -- this file NEVER edits encounters.js.
   - Crypto/parity LAW: soft-currency + cosmetic ONLY. grant('gems') is a no-op
     (gems are server-only); NO $BCARDD / ALK in any reward (the Mythic $BCARDD is
     referenced as LEGEND TEASE only, never fielded, never paid).
   - Reuse the 106 cards BY NAME as every NPC face. Never invent a dog.
   - Headless-safe: window.AKKarma is exported before the registry bail; no
     top-level DOM/localStorage; new Image() only at runtime inside the overlay.
   - "crew" never "clan." Gritty gold cyberpunk dog-gang voice in every line.
   ============================================================================ */
(function (global) {
  'use strict';

  /* ---- palette (Everlight gold cyberpunk) -------------------------------- */
  var GOLD = '#e8c55a', GOLD_D = '#c9a84c', INK = '#06060a', TXT = '#f2e6c0', DIM = '#9a8f6a';

  /* ======================================================================== *
   * FACTIONS -- the 4 NeonReach crews (World Bible) + neutral Central Plaza.
   * crewId ties each to its cards.json factionId so NPC faces are REAL dogs.
   * color mirrors the engine FACTION_COL so districts read consistently.
   * ======================================================================== */
  var FACTIONS = {
    crowned:    { key:'crowned',    name:'The Crowned',    crew:'K9 Circuitry',      crewId:'k9_circuitry',     color:'#00E0C0', icon:'👑', ethos:'elite, arrogant, feared' },
    rusted:     { key:'rusted',     name:'The Rusted',     crew:'Boneguard Crew',    crewId:'boneguard_crew',   color:'#C9772E', icon:'🦴', ethos:'underground, resourceful, underestimated' },
    hologhosts: { key:'hologhosts', name:'The Hologhosts', crew:'Leashbreak Tactix', crewId:'leashbreak_tactix',color:'#7B5CFF', icon:'👻', ethos:'mysterious, tech, unpredictable' },
    unbound:    { key:'unbound',    name:'The Unbound',    crew:'Zoomie Syndicate',  crewId:'zoomie_syndicate', color:'#FF2E88', icon:'⚡',      ethos:'hungry underdogs, all speed' },
    neutral:    { key:'neutral',    name:'Central Plaza',  crew:'',                  crewId:'',                 color:'#e8c55a', icon:'🏙️', ethos:'neutral ground' }
  };

  /* DISTRICT -> faction. Keys are the REAL ZONES ids from index.html.
     THE LOT (HOME_TURF, the spawn / center tile) is the neutral Central Plaza.
     The other 8 tiles carry a crew, by district theme (per STORYLINE_CANON +
     the painted-district art): heights = elite (Crowned), yards/factory = scrap
     (Rusted), docks/undercity = tech-phantom (Hologhosts), downtown/strip =
     hungry-hustle (Unbound). */
  var DISTRICTS = {
    HOME_TURF:     'neutral',     // THE LOT  -- spawn / home / Central Plaza
    DOWNTOWN:      'unbound',     // street commerce, the come-up
    NEON_HEIGHTS:  'crowned',     // glossy elite heights, the drip
    THE_YARDS:     'rusted',      // industrial yards, scrap, walls
    FACTORY_ROW:   'rusted',      // forge / mint / scrap
    THE_STRIP:     'unbound',     // casino strip, street fights
    THE_DOCKS:     'hologhosts',  // research / lab / tech, phantom docks
    THE_OVERLOOK:  'crowned',     // (locked) the elite overlook -- police checkpoint
    THE_UNDERCITY: 'hologhosts'   // (locked) the mysterious underground
  };

  /* ======================================================================== *
   * THE 7 TIERS -- cumulative thresholds, gold-cyberpunk colors + icons.
   * (The synthesis names the 7 tiers; thresholds/colors/icons tuned here.)
   * ======================================================================== */
  // AK-DEEMOJI: each tier carries a PNG `art` badge; `icon` emoji stays the graceful fallback.
  var TIERS = [
    { idx:0, name:'Stranger',  min:0,    color:'#9a8f6a', icon:'👤', art:'assets/icons/tier_stranger.png' },  // bust silhouette
    { idx:1, name:'New Face',  min:25,   color:'#b9c2cf', icon:'🐾', art:'assets/icons/tier_newface.png' },   // paw prints
    { idx:2, name:'Known',     min:75,   color:'#cd8a4a', icon:'🦴', art:'assets/icons/tier_known.png' },     // bone
    { idx:3, name:'Trusted',   min:175,  color:'#5ad0ff', icon:'🤝', art:'assets/icons/tier_trusted.png' },   // handshake
    { idx:4, name:'Respected', min:350,  color:'#c08bff', icon:'⭐', art:'assets/icons/tier_respected.png' }, // star
    { idx:5, name:'Revered',   min:650,  color:'#e8c55a', icon:'👑', art:'assets/icons/tier_revered.png' },   // crown
    { idx:6, name:'Legend',    min:1100, color:'#ff7ad9', icon:'🔥', art:'assets/icons/tier_legend.png' }     // fire
  ];

  /* tier-gated NPC dialog options (slice 0..tier.idx is unlocked) */
  var DIALOG = [
    { id:'greet',   tier:0, label:'Nod and pass by' },
    { id:'ask',     tier:1, label:'Ask what’s good on the block' },
    { id:'rumor',   tier:2, label:'Trade a rumor' },
    { id:'job',     tier:3, label:'Ask for work' },
    { id:'discount',tier:4, label:'Haggle the crew price' },
    { id:'backroom',tier:5, label:'Get pointed to the back room' },
    { id:'crown',   tier:6, label:'Speak as one of their own' }
  ];

  /* tier-gated district perks (cumulative) */
  var PERKS = [
    { tier:1, id:'safe_pass',   label:'Safe passage -- fewer hostile strays' },
    { tier:2, id:'shop_5',      label:'Crew shop discount opens' },
    { tier:3, id:'jobs',        label:'District jobs from the Recruiter' },
    { tier:4, id:'caravan',     label:'Merchant caravans stop for you' },
    { tier:5, id:'backroom',    label:'Back-room access + bones bounty' },
    { tier:6, id:'legend_rep',  label:'Karma converts to crew Reputation' }
  ];

  /* ======================================================================== *
   * THE 5 FRIENDLY NPC TYPES. Each grants karma + a SOFT reward (no gems, no
   * $BCARDD/ALK). `rarity` = which crew-card rarity supplies the NPC's face
   * (REAL dog, by name). Mysterious Stranger is FACELESS (the dealer/king tease,
   * canon TEASE-ONLY) so it never fields a card. `special:true` ones only roll
   * once the block already Trusts you (the rollEncounter d100 gates them).
   * ======================================================================== */
  var FRIENDLY_NPCS = {
    lost_pup: {
      id:'lost_pup', label:'Lost Pup', verb:'WALK IT HOME', icon:'🐶', art:'assets/icons/npc_lostpup.png',
      rarity:'Common', karma:12, special:false, escort:true,   // ESCORT job -- walk him to his crew's block, NOT an instant payout
      line:function (f) { return 'A lost pup whimpers between the dumpsters -- "' + f.crew + ' colors… walk me home, mister?"'; },
      reward:[['gold',[40,80]]] },
    injured_stray: {
      id:'injured_stray', label:'Injured Stray', verb:'PATCH IT UP', icon:'🩹', art:'assets/icons/npc_injured.png',
      rarity:'Rare', karma:16, special:false,
      line:function (f) { return 'An injured stray favors a paw in the alley. Patch it and the block remembers your face.'; },
      reward:[['scrap',[3,6],'Common'],['bones',[1,2]]] },
    merchant: {
      id:'merchant', label:'Merchant Caravan', verb:'TRADE FAIR', icon:'🛒', art:'assets/icons/npc_merchant.png',
      rarity:'Epic', karma:9, special:false,
      line:function (f) { return f.crew + ' runs a scrap caravan through here. Trade fair, build a name.'; },
      reward:[['scrap',[4,8],'Rare']] },
    recruiter: {
      id:'recruiter', label:'Faction Recruiter', verb:'HEAR THE JOB', icon:'📋', art:'assets/icons/npc_recruiter.png',
      rarity:'Legendary', karma:11, special:false,
      line:function (f) { return 'A ' + f.name + ' recruiter sizes you up -- "got a job if you got the spine. See the Fixer."'; },
      reward:[['sp',[1,2]]], mission:true },
    stranger: {
      id:'stranger', label:'Mysterious Stranger', verb:'LISTEN', icon:'🎴', art:'assets/icons/npc_elder.png',
      rarity:null, faceless:true, karma:25, special:true,
      line:function (f) { return 'A hooded dog deals one card face-down on a crate. "The king never died, pup. Keep climbin’."'; },
      reward:[['bones',[6,10]],['keys',[0,1]]], story:true }
  };

  /* resource cache flavors (RESOURCE roll) -- soft loot, tiny karma. */
  var RESOURCES = [
    { id:'scrap_stash', label:'a stashed scrap crate', icon:'📦', karma:4, reward:[['scrap',[3,7],'Common']] },
    { id:'coin_drop',   label:'a dropped coin roll',   icon:'🪙', karma:4, reward:[['gold',[30,70]]] },
    { id:'frag_crate',  label:'a cracked key-frag box', icon:'🗝️', karma:5, reward:[['fragments',[2,4]]] }
  ];

  /* ---- small utils ------------------------------------------------------- */
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function profile(ctx) { try { return (ctx && ctx.econ) ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function rint(lo, hi, rng) { return lo + Math.floor((rng || Math.random)() * (hi - lo + 1)); }

  /* module state (ctx cached at init so window.AKKarma works without a passed ctx) */
  var S = { ctx: null, engaging: false, friendly: {} /* zoneId -> count */ };

  /* ---- REAL card-name resolver (BY NAME, never invented) ----------------- */
  // Pull a live name from ctx.cards() filtered by crew + rarity; fall back to a
  // hard list of REAL names from data/cards.json so a headless / canon-less load
  // still yields a true crew dog.
  var FALLBACK = {
    k9_circuitry:      { Common:['Neon Dachshund','Flux Pomeranian','Rail Terrier','Pixel Pug'], Rare:['Laser Beagle','Volt Corgi','Grid Schnauzer','Chrome Airedale'], Epic:['Circuit Retriever','Nova Shepherd'], Legendary:['Casemate','Emplacement'], Mythic:['Crown Foxhound'] },
    boneguard_crew:    { Common:['Tank Pug','Copper Chow','Brick Bullmastiff'], Rare:['Granite Saint','Grit Bulldog','Alloy Akita'], Epic:['Balboa','Iron Rottweiler','Anvil'], Legendary:['Stonejaw','Cinderblock','Tombstone'], Mythic:['Crown Foxhound'] },
    leashbreak_tactix: { Common:['Echo Dalmatian','Vibe Shih Tzu','Static Sheba Inu'], Rare:['Holo Husky','Chill Samoyed','Prism Poodle','Ghost Spaniel'], Epic:['Synth Collie','Noir Setter'], Legendary:['Firewall','Bulwark'], Mythic:['Rosco'] },
    zoomie_syndicate:  { Common:['Neon Whippet','Turbo Jack','Drift Sheltie','Nitro'], Rare:['Pixel Greyhound','Circuit Shiba','Flash Saluki'], Epic:['Razor Vizsla','Aero Malinois'], Legendary:['Rollcage','Deadweight'], Mythic:['Jagged'] }
  };
  function pickCardName(crewId, rarity, ctx, rng) {
    rng = rng || Math.random;
    if (!crewId || !rarity) return null;
    var names = [];
    try {
      var cards = (ctx && ctx.cards && ctx.cards()) || {};
      for (var k in cards) {
        var c = cards[k];
        if (c && c.factionId === crewId && c.rarity === rarity && c.type !== 'spell') names.push(c.name);
      }
    } catch (_) {}
    if (!names.length) { var fb = FALLBACK[crewId]; names = (fb && fb[rarity]) ? fb[rarity].slice() : []; }
    if (!names.length) return null;
    return names[Math.floor(rng() * names.length)];
  }
  function cardDef(ctx, name) {
    try { var cards = (ctx && ctx.cards && ctx.cards()) || {}; return cards[name] || null; } catch (_) { return null; }
  }

  /* ======================================================================== *
   * CORE KARMA API
   * ======================================================================== */
  function getZoneFaction(zoneId) { return FACTIONS[DISTRICTS[zoneId] || 'neutral']; }
  function tierByPoints(pts) { pts = pts | 0; var t = TIERS[0]; for (var i = 0; i < TIERS.length; i++) if (pts >= TIERS[i].min) t = TIERS[i]; return t; }
  function getKarma(zoneId, ctx) { var p = profile(ctx || S.ctx); return (p && p.karma && (p.karma[zoneId] | 0)) || 0; }
  function getTier(zoneId, ctx) { return tierByPoints(getKarma(zoneId, ctx)); }

  // Add (or remove, n<0) district karma via ONE atomic AK_ECON.mutateProfile.
  // Returns { zone, points, tier, prevTier, leveledUp }. Synthesis: at high tiers
  // karma converts to crew Reputation -- soft proxy here = a bones bounty on a
  // Revered+ tier-up (no rep currency in economy.js yet; server can layer real
  // crew rep later through the ak_grants rail).
  function addKarma(zoneId, n, ctx) {
    ctx = ctx || S.ctx; n = n | 0;
    if (!ctx || !ctx.econ || !zoneId || !n) return null;
    var before = getKarma(zoneId, ctx), prevTier = tierByPoints(before);
    ctx.econ.mutateProfile(function (p) {
      if (!p.karma || typeof p.karma !== 'object') p.karma = {};
      p.karma[zoneId] = Math.max(0, (p.karma[zoneId] | 0) + n);
    });
    var after = getKarma(zoneId, ctx), nowTier = tierByPoints(after);
    var leveledUp = nowTier.idx > prevTier.idx;
    if (leveledUp && nowTier.idx >= 5 && ctx.currency) { try { ctx.currency.grant('bones', nowTier.idx * 2); } catch (_) {} }
    return { zone: zoneId, points: after, tier: nowTier, prevTier: prevTier, leveledUp: leveledUp };
  }

  // prestige hook (synthesis: karma is 0% burn but RESETS on prestige).
  function resetKarma(zoneId, ctx) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return null;
    return ctx.econ.mutateProfile(function (p) {
      if (!p.karma || typeof p.karma !== 'object') { p.karma = {}; return; }
      if (zoneId) delete p.karma[zoneId]; else p.karma = {};
    });
  }

  /* karma-gated content for a district (mission tier / shop discount / dialog /
     building access / perks) -- consumed by missions, shop, NPC dialog, gates. */
  function buildingAccessFor(zoneId, tierIdx, ctx) {
    var out = [];
    try {
      var Z = (ctx || S.ctx) && (ctx || S.ctx).ZONES; var z = Z && Z[zoneId];
      var bs = (z && z.buildings) || [];
      for (var i = 0; i < bs.length; i++) {
        // base buildings always open; the crew's "special" surface (FIXER jobs,
        // back rooms) wants Trusted (tier 3). Keep it data-light + falsy-safe.
        var gated = (bs[i].id === 'FIXER' || bs[i].id === 'STREET');
        out.push({ id: bs[i].id, label: bs[i].label, locked: gated && tierIdx < 3 });
      }
    } catch (_) {}
    return out;
  }
  function getAvailableContent(zoneId, ctx) {
    ctx = ctx || S.ctx;
    var t = getTier(zoneId, ctx), fac = getZoneFaction(zoneId);
    return {
      zone: zoneId, faction: fac, tier: t,
      missionTier: t.idx,                                   // difficulty band unlocked
      shopDiscount: Math.min(0.30, t.idx * 0.05),           // tier * 5%, cap 30%
      dialogOptions: DIALOG.filter(function (d) { return t.idx >= d.tier; }),
      buildingAccess: buildingAccessFor(zoneId, t.idx, ctx),
      perks: PERKS.filter(function (pk) { return t.idx >= pk.tier; })
    };
  }

  /* ======================================================================== *
   * THE KARMA-MODIFIED d100 ENCOUNTER TABLE  (the encounters.js branch point)
   * Low karma => mostly HOSTILE strays. High karma => FRIENDLY / RESOURCE /
   * SPECIAL. Returns { kind, zone, weights, npc?, resource? }.
   * ======================================================================== */
  function rollEncounter(zoneId, ctx, rng) {
    ctx = ctx || S.ctx; rng = rng || Math.random;
    var t = getTier(zoneId, ctx).idx, f = t / 6;            // 0..1 across the 7 tiers
    var w = {
      hostile:  Math.max(8, Math.round(70 - 58 * f)),       // 70 -> 12
      friendly: Math.round(8 + 34 * f),                     // 8  -> 42
      resource: Math.round(6 + 16 * f),                     // 6  -> 22
      special:  Math.max(0, (t - 2)) * 3,                   // 0 until Trusted, -> 12 at Legend
      nothing:  10
    };
    var tot = w.hostile + w.friendly + w.resource + w.special + w.nothing;
    var x = rng() * tot, kind;
    if ((x -= w.hostile)  < 0) kind = 'hostile';
    else if ((x -= w.friendly) < 0) kind = 'friendly';
    else if ((x -= w.resource) < 0) kind = 'resource';
    else if ((x -= w.special)  < 0) kind = 'special';
    else kind = 'nothing';
    var out = { kind: kind, zone: zoneId, weights: w };
    if (kind === 'friendly' || kind === 'special') out.npc = pickFriendly(zoneId, kind, rng, ctx);
    if (kind === 'resource') out.resource = RESOURCES[Math.floor(rng() * RESOURCES.length)];
    return out;
  }

  // Choose a friendly NPC type + bind its REAL crew-dog face for this district.
  function pickFriendly(zoneId, kind, rng, ctx) {
    rng = rng || Math.random; ctx = ctx || S.ctx;
    var fac = getZoneFaction(zoneId);
    var def;
    if (kind === 'special') def = FRIENDLY_NPCS.stranger;
    else {
      var roster = ['lost_pup', 'injured_stray', 'merchant', 'recruiter'];
      def = FRIENDLY_NPCS[roster[Math.floor(rng() * roster.length)]];
    }
    var cardName = def.faceless ? null : pickCardName(fac.crewId, def.rarity, ctx, rng);
    return { def: def, faction: fac, cardName: cardName, line: def.line(fac) };
  }

  /* ---- grant a soft reward list (gems = hard no-op; no $BCARDD/ALK) ------- */
  function grantReward(ctx, reward, rng) {
    rng = rng || Math.random; var got = [];
    (reward || []).forEach(function (r) {
      var kind = r[0], amt = r[1], rar = r[2];
      if (kind === 'gems') return;                          // server-only; never here
      if (Array.isArray(amt)) amt = rint(amt[0], amt[1], rng);
      amt = amt | 0; if (amt <= 0) return;
      try { ctx.currency.grant(kind, amt, rar); got.push({ kind: kind, amt: amt, rarity: rar }); } catch (_) {}
    });
    return got;
  }
  function rewardStr(got) {
    return got.map(function (g) {
      var n = { gold: 'gold', scrap: (g.rarity || '') + ' scrap', keys: 'keys', fragments: 'key-frags', sp: 'SP', bones: 'bones' }[g.kind] || g.kind;
      return '+' + g.amt + ' ' + n;
    }).join('  ');
  }

  // PUBLIC: resolve a friendly interaction -> grant karma + soft reward.
  // npc = a FRIENDLY_NPCS def, its id, OR the {def,...} object from rollEncounter.
  function interact(npc, zoneId, ctx, rng) {
    ctx = ctx || S.ctx; rng = rng || Math.random;
    var def = (npc && npc.def) ? npc.def : (typeof npc === 'string' ? FRIENDLY_NPCS[npc] : npc);
    if (!def || !ctx) return { ok: false };
    var fac = getZoneFaction(zoneId);
    // RECRUITER -> hand the player a REAL MISSION instead of paying karma on the spot.
    // The recruiter now CREATES an active job (window.AKMissions, the mission_active wave):
    // the karma + soft loot become the TURN-IN reward, so the recruiter actually sends you
    // somewhere. Backward-compat: if mission_active is NOT loaded, fall through to the legacy
    // instant grant below (zero behavior change on pages without the wave).
    if (def.mission && global.AKMissions && global.AKMissions.acceptFromRecruiter) {
      var cardName = (npc && npc.cardName) || null, m = null;
      try { m = global.AKMissions.acceptFromRecruiter(zoneId, fac, cardName, ctx, rng, def.karma); } catch (_) { m = null; }
      try { if (global.AKQuests && global.AKQuests.reportEvent) global.AKQuests.reportEvent('karma_recruit', 1); } catch (_) {}
      return { ok: true, npc: def, faction: fac, accepted: !!m, mission: m, karma: null, rewards: [], rewardStr: '' };
    }
    // LOST PUP -> a real ESCORT job, NOT an instant handout. "WALK IT HOME" now hands the
    // player a walk-home mission (mission_active wave): the pup follows, you have to TRAVERSE
    // the blocks to his home district, and he is delivered (paid) only once you get him there.
    // Backward-compat: if the mission wave is NOT loaded, fall through to the legacy instant
    // grant below (zero behavior change on pages without it).
    if (def.escort && global.AKMissions && global.AKMissions.acceptEscort) {
      var pupName = (npc && npc.cardName) || null, em = null;
      try { em = global.AKMissions.acceptEscort(zoneId, fac, pupName, ctx, rng, def.karma); } catch (_) { em = null; }
      return { ok: true, npc: def, faction: fac, accepted: !!em, mission: em, escort: true, karma: null, rewards: [], rewardStr: '' };
    }
    var got = grantReward(ctx, def.reward, rng);
    var k = addKarma(zoneId, def.karma, ctx);
    if (def.mission) { try { if (global.AKQuests && global.AKQuests.reportEvent) global.AKQuests.reportEvent('karma_recruit', 1); } catch (_) {} }
    return { ok: true, npc: def, faction: fac, karma: k, rewards: got, rewardStr: rewardStr(got) };
  }

  // Build the banner line for a friendly interaction result (shared by the
  // overlay-less fallback + the panel onClose). Handles the new "job accepted"
  // recruiter case alongside the classic karma + soft-reward grant.
  function npcResultLine(def, r) {
    if (r && r.escort && r.accepted && r.mission) {
      return def.label + ': "' + (r.mission.objLine || 'walk me home') + '"  -- stick close through the blocks, mutt.';
    }
    if (r && r.escort && r.accepted === false) {
      return def.label + ': too much on your plate -- clear a job before you take the pup.';
    }
    if (r && r.accepted && r.mission) {
      return def.label + ': "' + (r.mission.objLine || r.mission.title || 'job') + '"  -- come back when it is done.';
    }
    if (r && r.accepted === false && def.mission) {
      return def.label + ': board is full -- finish a job first, mutt.';
    }
    return def.label + ' remembers you.  ' + ((r && r.rewardStr) || '') + ((r && r.karma) ? '  (+' + def.karma + ' karma)' : '');
  }

  /* ======================================================================== *
   * SPAWN A FRIENDLY ROAMER  (called from the encounters.js karma hook)
   * encounters owns the hostile stray; when its spawn slot rolls non-hostile it
   * yields the slot to THIS, so the world roamer budget stays balanced. Friendly
   * roamers are tagged _kf (NOT _enc) so encounters' prune/cap ignores them; we
   * cap them ourselves (MAX_FRIENDLY per zone).
   * ======================================================================== */
  var MAX_FRIENDLY = 2, FRIEND_AWAY = 200;

  function friendlyCount(ctx, zone) {
    var rs = ctx.world.roamers(), n = 0;
    for (var i = 0; i < rs.length; i++) if (rs[i]._kf && rs[i].zone === zone) n++;
    return n;
  }

  // enc = the rollEncounter result ({kind, npc?|resource?}). Returns the roamer
  // handle, or null if it declined to spawn (cap hit / no placement / bad enc).
  function spawnFriendly(zoneId, ctx, enc) {
    ctx = ctx || S.ctx;
    if (!ctx || !ctx.world || !ctx.world.addRoamer || !enc) return null;
    if (enc.kind === 'hostile' || enc.kind === 'nothing') return null;
    if (friendlyCount(ctx, zoneId) >= MAX_FRIENDLY) return null;

    var WW = ctx.world.WORLD_W, WH = ctx.world.WORLD_H, x = 0, y = 0, ok = false, tries = 0;
    while (!ok && tries++ < 12) {
      x = 80 + Math.random() * (WW - 160);
      y = 80 + Math.random() * (WH - 160);
      if (ctx.world.distToMe(x, y) > FRIEND_AWAY) ok = true;
    }
    if (!ok) return null;

    var fac = getZoneFaction(zoneId);
    var roamer = {
      _kf: true, zone: zoneId, x: x, y: y, r: 16,
      kind: enc.kind, faction: fac,
      npc: enc.npc || null, resource: enc.resource || null,
      home: { x: x, y: y }, tx: x, ty: y, wt: 0, cool: 1.2, pulse: 0, done: false,
      id: 'kf_' + (enc.npc ? enc.npc.def.id : (enc.resource ? enc.resource.id : 'x')) + '_' + (Date.now() % 100000),
      update: kfUpdate, draw: kfDraw
    };
    ctx.world.addRoamer(roamer);
    return roamer;
  }

  function kfUpdate(dt, self, ctx) {
    if (self.done) return;
    if (self.cool > 0) self.cool -= dt;
    self.pulse = (self.pulse + dt) % 2;
    // gentle wander around home (Math.random drift -- never chases the player)
    self.wt -= dt;
    if (self.wt <= 0 || Math.hypot(self.x - self.tx, self.y - self.ty) < 12) {
      self.wt = 2.5 + Math.random() * 3;
      self.tx = clamp(self.home.x + (Math.random() - 0.5) * 200, 50, ctx.world.WORLD_W - 50);
      self.ty = clamp(self.home.y + (Math.random() - 0.5) * 200, 50, ctx.world.WORLD_H - 50);
    }
    var dx = self.tx - self.x, dy = self.ty - self.y, m = Math.hypot(dx, dy);
    if (m > 0.001) { self.x += dx / m * 30 * dt; self.y += dy / m * 30 * dt; }
    // contact -> trigger the interaction (once, gated by a cooldown + engaging lock)
    if (!S.engaging && self.cool <= 0 && ctx.world.distToMe(self.x, self.y) < self.r + 26) triggerFriendly(self, ctx);
  }

  function triggerFriendly(self, ctx) {
    if (self.kind === 'resource') {                          // caches grant instantly (no panel)
      var got = grantReward(ctx, self.resource.reward, Math.random);
      var k = addKarma(self.zone, self.resource.karma, ctx);
      ctx.showBanner('Found ' + self.resource.label + '.  ' + rewardStr(got) + (k ? '  (+' + self.resource.karma + ' karma)' : ''), 1.8);
      self.done = true; ctx.world.removeRoamer(self);
      return;
    }
    openFriendly(self, ctx);                                 // NPCs get a quick keeper-style panel
  }

  // host auto-draws this (culled off-screen). Friendly = a GREEN ring + the
  // NPC/resource icon (a "?" tell, never the hostile "!"), real crew-dog face
  // when one is bound. save()/restore() balanced; never leaves canvas dirty.
  function kfDraw(g, self, ctx) {
    var X = ctx.world.wx(self.x), Y = ctx.world.wy(self.y), r = self.r;
    var col = (self.faction && self.faction.color) || GOLD;
    var icon = self.npc ? self.npc.def.icon : (self.resource ? self.resource.icon : '💬');
    var nm = self.npc ? self.npc.def.label : (self.resource ? 'supply cache' : '');
    g.save();
    // ground shadow
    g.globalAlpha = 0.35; g.fillStyle = '#000';
    g.beginPath(); g.ellipse(X, Y + r * 0.8, r * 0.9, r * 0.4, 0, 0, 6.2832); g.fill();
    g.globalAlpha = 1;
    // body: real crew-dog art if bound + loaded, else a faction-tinted token
    var im = (self.npc && self.npc.cardName) ? npcImg(ctx, self.npc.cardName) : null, drew = false;
    if (im && im.complete && im.naturalWidth > 0) {
      g.save(); g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.closePath(); g.clip();
      try { g.drawImage(im, X - r, Y - r, r * 2, r * 2); drew = true; } catch (_) {}
      g.restore();
    }
    // AK-DEEMOJI: no bound crew-dog art -> the NPC's PNG icon, then the emoji glyph
    if (!drew && self.npc && self.npc.def && self.npc.def.art) {
      var aim = artImg(self.npc.def.art);
      if (aim && aim.complete && aim.naturalWidth > 0) {
        g.save(); g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.closePath(); g.clip();
        try { g.drawImage(aim, X - r, Y - r, r * 2, r * 2); drew = true; } catch (_) {}
        g.restore();
      }
    }
    if (!drew) {
      g.fillStyle = col; g.globalAlpha = 0.9; g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.fill(); g.globalAlpha = 1;
      g.font = Math.round(r * 1.05) + 'px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(icon, X, Y + 1);
    }
    // FRIENDLY ring -- green, gently pulsing (the welcoming tell vs the red chase ring)
    var pl = 0.6 + 0.4 * Math.abs(Math.sin((self.pulse || 0) * Math.PI));
    g.lineWidth = 2; g.strokeStyle = 'rgba(124,255,176,' + pl.toFixed(2) + ')';
    g.beginPath(); g.arc(X, Y, r + 3, 0, 6.2832); g.stroke();
    // name tag
    if (nm) {
      g.font = '800 10px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
      var tw = g.measureText(nm).width + 10;
      g.fillStyle = 'rgba(8,12,8,.72)'; g.fillRect(X - tw / 2, Y - r - 18, tw, 13);
      g.fillStyle = '#d9f5cf'; g.fillText(nm, X, Y - r - 8);
    }
    // friendly "?" approach tell
    g.font = '900 15px Inter,system-ui'; g.fillStyle = '#7CFFb0'; g.textAlign = 'center';
    g.fillText('?', X, Y - r - 22);
    g.restore();
  }

  /* ---- compact friendly-NPC overlay (ctx.overlay.open) ------------------- */
  function roundRect(g, x, y, w, h, r) {
    if (w < 2 * r) r = w / 2; if (h < 2 * r) r = h / 2;
    g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r);
    g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  }
  function drawBtn(g, rc, label, primary) {
    g.save();
    g.fillStyle = primary ? GOLD : 'rgba(20,17,10,.85)';
    roundRect(g, rc.x, rc.y, rc.w, rc.h, 9); g.fill();
    if (!primary) { g.lineWidth = 1; g.strokeStyle = 'rgba(201,168,76,.5)'; roundRect(g, rc.x, rc.y, rc.w, rc.h, 9); g.stroke(); }
    g.fillStyle = primary ? '#15110a' : '#b9a76a';
    g.font = '800 12px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(label, rc.x + rc.w / 2, rc.y + rc.h / 2 + 1); g.restore();
  }
  var _img = {};
  function npcImg(ctx, cardName) {
    if (!cardName || typeof Image === 'undefined') return null;
    if (_img[cardName]) return _img[cardName];
    var im = new Image(); _img[cardName] = im;
    try {
      var def = cardDef(ctx, cardName);
      var rel = (def && global.akCardArtRel) ? global.akCardArtRel(def) : '';
      if (rel) im.src = 'assets/' + rel;
    } catch (_) {}
    try { im.onerror = function () { if (global.akImgErr) global.akImgErr(im); }; } catch (_) {}
    return im;
  }
  // AK-DEEMOJI: cached path->Image loader for tier/NPC PNG icons. Cached by path so the
  // overlay/world draw never allocates a new Image per frame; a 404 marks it dead (null)
  // so callers fall straight back to the emoji glyph (graceful fallback).
  var _artCache = {};
  function artImg(path) {
    if (!path || typeof Image === 'undefined') return null;
    if (_artCache.hasOwnProperty(path)) return _artCache[path];
    var im = new Image(); _artCache[path] = im;
    try { im.onerror = function () { _artCache[path] = null; }; } catch (_) {}
    im.src = path;
    return im;
  }

  function openFriendly(self, ctx) {
    if (S.engaging || !ctx.overlay || !ctx.overlay.open) {   // overlay-less fallback: grant + banner
      var r0 = interact(self.npc, self.zone, ctx);
      if (r0.ok) { ctx.showBanner(npcResultLine(self.npc.def, r0), 2.2); self.done = true; ctx.world.removeRoamer(self); }
      return;
    }
    S.engaging = true;
    var npc = self.npc, def = npc.def, fac = npc.faction;
    var bHelp = null, bWave = null, resolved = false;

    function draw(g, vp) {
      var W = vp.w, H = vp.h;
      g.save();
      var bg = g.createRadialGradient(W / 2, H * 0.42, 40, W / 2, H * 0.42, Math.max(W, H) * 0.8);
      bg.addColorStop(0, 'rgba(22,26,24,.96)'); bg.addColorStop(1, 'rgba(6,8,10,.98)');
      g.fillStyle = bg; g.fillRect(0, 0, W, H);

      g.textAlign = 'center';
      g.fillStyle = '#7CFFb0'; g.font = '900 22px Cinzel,"Playfair Display",serif';
      g.fillText('A FRIENDLY FACE', W / 2, 52);
      g.fillStyle = fac.color; g.font = '800 12px Inter,system-ui';
      g.fillText(def.icon + '  ' + def.label + '  ·  ' + fac.name, W / 2, 74);

      // portrait -- the REAL crew dog (art) or a faction token w/ the NPC icon
      var pr = Math.min(120, W * 0.34), px = W / 2, py = H * 0.40;
      g.save(); g.translate(px, py);
      g.fillStyle = 'rgba(10,12,9,.9)'; roundRect(g, -pr / 2 - 8, -pr / 2 - 8, pr + 16, pr + 16, 14); g.fill();
      g.lineWidth = 2; g.strokeStyle = fac.color; roundRect(g, -pr / 2 - 8, -pr / 2 - 8, pr + 16, pr + 16, 14); g.stroke();
      g.save(); roundRect(g, -pr / 2, -pr / 2, pr, pr, 10); g.clip();
      var im = npc.cardName ? npcImg(ctx, npc.cardName) : null, drew = false;
      if (im && im.complete && im.naturalWidth > 0) { try { g.drawImage(im, -pr / 2, -pr / 2, pr, pr); drew = true; } catch (_) {} }
      // AK-DEEMOJI: no bound crew-dog art -> the NPC's PNG icon, then the emoji glyph
      if (!drew && def.art) { var aim = artImg(def.art); if (aim && aim.complete && aim.naturalWidth > 0) { try { g.drawImage(aim, -pr / 2, -pr / 2, pr, pr); drew = true; } catch (_) {} } }
      if (!drew) {
        g.fillStyle = fac.color; g.globalAlpha = 0.22; g.fillRect(-pr / 2, -pr / 2, pr, pr); g.globalAlpha = 1;
        g.font = '60px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(def.icon, 0, 4);
      }
      g.restore(); g.restore();

      g.textAlign = 'center'; g.textBaseline = 'alphabetic';
      if (npc.cardName) { g.fillStyle = TXT; g.font = '800 16px Inter,system-ui'; g.fillText(npc.cardName, W / 2, py + pr / 2 + 30); }

      // the line (word-wrapped, gritty crew voice)
      g.fillStyle = '#d9e8d0'; g.font = '600 13px Inter,system-ui';
      var words = npc.line.split(' '), lineStr = '', yy = py + pr / 2 + (npc.cardName ? 54 : 34), maxW = Math.min(360, W * 0.82);
      for (var i = 0; i < words.length; i++) {
        var test = lineStr + words[i] + ' ';
        if (g.measureText(test).width > maxW && lineStr) { g.fillText(lineStr.trim(), W / 2, yy); lineStr = words[i] + ' '; yy += 18; }
        else lineStr = test;
      }
      if (lineStr) g.fillText(lineStr.trim(), W / 2, yy);

      // reward preview
      g.fillStyle = GOLD; g.font = '700 11px Inter,system-ui';
      g.fillText('+' + def.karma + ' district karma  ·  helping pays off', W / 2, H - 132);

      // buttons
      bHelp = { x: (W - 150) / 2 - 78, y: H - 100, w: 150, h: 44 };
      bWave = { x: (W - 150) / 2 + 84, y: H - 100, w: 96, h: 44 };
      drawBtn(g, bHelp, def.verb, true);
      drawBtn(g, bWave, 'WAVE OFF', false);
      g.restore();
    }

    var api = ctx.overlay.open({
      id: 'karma_friendly',
      onFrame: function (g, dt, vp) { draw(g, vp); },
      onPointer: function (evt) {
        if (evt.type !== 'pointerdown') return;
        var x = evt.clientX, y = evt.clientY;
        function hit(rc) { return rc && x >= rc.x && x <= rc.x + rc.w && y >= rc.y && y <= rc.y + rc.h; }
        if (hit(bHelp)) { resolved = true; api.close('help'); }
        else if (hit(bWave)) { api.close('wave'); }
      },
      onClose: function (res) {
        S.engaging = false;
        if (res === 'help' || resolved) {
          var r = interact(npc, self.zone, ctx);
          var msg = npcResultLine(def, r);
          if (r.karma && r.karma.leveledUp) msg = fac.name + ': you’re now ' + r.karma.tier.name + ' here!  ' + (r.rewardStr || '');
          ctx.showBanner(msg, 2.2);
          self.done = true; ctx.world.removeRoamer(self);
        } else {
          self.cool = 6; self.home = { x: self.x, y: self.y };   // backed off -- give it a beat, don't re-fire
        }
      }
    });
  }

  /* ======================================================================== *
   * PUBLIC API  (window.AKKarma) -- exported BEFORE the registry bail so it is
   * harmless + headless-safe on pages without AK_SYSTEMS.
   * ======================================================================== */
  global.AKKarma = {
    FACTIONS: FACTIONS, DISTRICTS: DISTRICTS, TIERS: TIERS,
    FRIENDLY_NPCS: FRIENDLY_NPCS, RESOURCES: RESOURCES, DIALOG: DIALOG, PERKS: PERKS,
    getZoneFaction: getZoneFaction,
    getKarma: getKarma,
    getTier: getTier,
    tierByPoints: tierByPoints,
    addKarma: addKarma,
    resetKarma: resetKarma,
    getAvailableContent: getAvailableContent,
    rollEncounter: rollEncounter,
    pickFriendly: pickFriendly,
    spawnFriendly: spawnFriendly,
    interact: interact
  };

  /* hub-only lifecycle: cache ctx so the API works without an explicit ctx. */
  if (!global.AK_SYSTEMS) return;
  global.AK_SYSTEMS.register({
    id: 'karma',
    init: function (ctx) { S.ctx = ctx; }
  });

})(typeof window !== 'undefined' ? window : globalThis);
