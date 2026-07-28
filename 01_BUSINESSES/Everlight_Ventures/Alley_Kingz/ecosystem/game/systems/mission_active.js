/* game/systems/mission_active.js -- AK_SYSTEMS module: "mission_active".
   ==========================================================================
   THE FACTION MISSION LOOP -- the connective tissue that turns the karma.js
   RECRUITER from an instant-karma handout into a REAL job:

       accept  ->  you get a concrete TASK that forces you to traverse another
                   district + touch the economy (harvest / win a scrap / scout a
                   building / haul goods)
       work    ->  progress is tracked off observable signals (AK_ECON profile
                   deltas, the active zone, trophy bumps, building proximity)
       ready   ->  "MISSION READY -- return to <giver> in <giverZone>"
       turn in ->  walk BACK to the giver's district (a TURN-IN beacon spawns
                   there), they acknowledge it is done, drop a RECEIPT, and pay
                   the reward.  Then the job clears.

   STATE / CONTRACT (mirrors karma.js + missions.js):
   - Self-registers into window.AK_SYSTEMS; edits NO shared file. The orchestrator
     adds <script src="systems/mission_active.js"> and points the JOBS chip at the
     exported window.akOpenMissions. The recruiter accept path lives in karma.js
     (interact -> window.AKMissions.acceptFromRecruiter).
   - ALL player state via window.AK_ECON behind TWO falsy-default fields that this
     wave creates lazily ON WRITE (economy.js ensureShape is frozen, so we never
     rely on it pre-creating them -- zero-state stays byte-identical until you
     accept your first job):
         p.activeMissions []   (the live jobs)
         p.missionLog []       (turn-in receipts, capped)
   - Public API on window.AKMissions (mirrors AKKarma / AKQuests). window.akOpenMissions
     opens the JOB BOARD overlay. Both exported BEFORE the registry bail so the file
     is harmless + headless-safe on pages without AK_SYSTEMS (node harness no-ops).
   - SOFT-CURRENCY ONLY: rewards are gold / scrap / district karma. Never gems,
     never $BCARDD / ALK. Gold + scrap ride ctx.currency.grant; karma rides
     window.AKKarma.addKarma into the giver's district.
   - 60fps: zero per-frame heavy work. Progress is polled on a ~0.8s throttle and
     batched into ONE mutateProfile per poll. The beacon is a single light roamer.
   ========================================================================== */
(function (global) {
  'use strict';

  /* ---- palette (Everlight gold cyberpunk -- matches karma.js) ------------- */
  var GOLD = '#e8c55a', GOLD_D = '#c9a84c', TXT = '#f2e6c0', DIM = '#9a8f6a';

  var MAX_ACTIVE = 4;                 // the recruiter board cap (finish a job to take more)
  var POLL_SEC = 0.8;                 // progress poll throttle (no per-frame work)
  var VISIT_RANGE = 110;              // how close you must get to "tap" a target building
  var CREW_LEAD_RATE = 0.10;          // CO-OP: SHARED-objective progress/sec from the lead crew role
  var CREW_SUPPORT_RATE = 0.055;      // CO-OP: ...from the support crew role

  // the 8 walkable districts (the 2 locked tiles -- THE_OVERLOOK / THE_UNDERCITY --
  // are never a travel target). Mirrors index.html ZONES (unlocked only).
  var UNLOCKED = ['HOME_TURF', 'DOWNTOWN', 'NEON_HEIGHTS', 'THE_YARDS', 'FACTORY_ROW', 'THE_STRIP', 'THE_DOCKS'];
  var MATS = ['wood', 'stone', 'metal'];
  var MAT_LABEL = { wood: 'WOOD', stone: 'STONE', metal: 'METAL' };

  /* module-private state (NO profile state lives here) */
  var S = { ctx: null, _acc: 0, open: false, root: null, bodyEl: null, beacons: {} /* mid -> roamer */, pups: {} /* mid -> escort follower roamer */ };

  /* ---- small utils -------------------------------------------------------- */
  function rint(lo, hi, rng) { return lo + Math.floor((rng || Math.random)() * (hi - lo + 1)); }
  function pick(arr, rng) { return arr[Math.floor((rng || Math.random)() * arr.length)]; }
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function profile(ctx) { try { return (ctx && ctx.econ) ? ctx.econ.loadProfile() : null; } catch (_) { return null; } }
  function zoneName(ctx, id) { try { var z = (ctx && ctx.ZONES) && ctx.ZONES[id]; return (z && z.name) || id; } catch (_) { return id; } }
  function zoneFaction(id) { try { return (global.AKKarma && global.AKKarma.getZoneFaction) ? global.AKKarma.getZoneFaction(id) : null; } catch (_) { return null; } }
  function activeMissions(ctx) { var p = profile(ctx); return (p && Array.isArray(p.activeMissions)) ? p.activeMissions : []; }
  // effective objective progress = YOUR work (have) + the CREW's shared contribution
  // (crewHave), capped at need. Falsy-default: solo jobs never carry crewHave, so this
  // is identical to the old min(have,need) for them -- zero-state stays byte-identical.
  function effHave(o) { return Math.min(o.need | 0, ((o && o.have) | 0) + ((o && o.crewHave) | 0)); }
  // Manhattan hop count between two districts on the world grid (gx/gy). Drives the
  // reward scale -- a job that hauls you clear across the map pays more than a hop next door.
  function gridDist(ctx, a, b) {
    try {
      var Z = ctx && ctx.ZONES, za = Z && Z[a], zb = Z && Z[b];
      if (!za || !zb) return 1;
      return Math.max(1, Math.abs((za.gx | 0) - (zb.gx | 0)) + Math.abs((za.gy | 0) - (zb.gy | 0)));
    } catch (_) { return 1; }
  }

  /* ======================================================================== *
   * THE FIXER -- local delivery jobs, FOLDED IN from the old missions.js so the
   * board carries BOTH the Fixer's runs and the faction recruiter jobs (ONE Hit
   * List). Marrow the Fixer runs these out of THE FIXER (THE_YARDS). Soft
   * currency + BONES only; consumable jobs deduct their inputs on turn-in (a real
   * sink), milestone jobs pay once then never re-offer (tracked in p.missions.done).
   * Card / handler names are canon flavor only -- never re-stat.
   * ======================================================================== */
  var FIXER_NAME = 'Marrow the Fixer', FIXER_GLYPH = '📋', FIXER_COLOR = '#ff9d5c';

  var DELIVERIES = [
    { id: 'haul_rare', title: 'Scrap Haul', res: 'Rare scrap', target: 12,
      pitch: "Bring me {t} Rare scrap. Stonejaw's crew melt it down for the docks.",
      prog: function (p) { return (p.scrap && p.scrap.Rare | 0) || 0; },
      consume: function (p) { p.scrap.Rare = Math.max(0, (p.scrap.Rare | 0) - 12); },
      reward: [['gold', 240], ['bones', 6]] },

    { id: 'haul_epic', title: 'Epic Order', res: 'Epic scrap', target: 4,
      pitch: "I need {t} Epic scrap, no questions. Granite Saint's payin' double.",
      prog: function (p) { return (p.scrap && p.scrap.Epic | 0) || 0; },
      consume: function (p) { p.scrap.Epic = Math.max(0, (p.scrap.Epic | 0) - 4); },
      reward: [['gold', 420], ['bones', 12]] },

    { id: 'front_gold', title: 'Front Money', res: 'gold', target: 700,
      pitch: "Front me {t} gold and I'll square you up in scrap. Banker Bones vouches.",
      prog: function (p) { return p.coins | 0; },
      consume: function (p) { p.coins = Math.max(0, (p.coins | 0) - 700); },
      reward: [['scrap', 5, 'Rare'], ['bones', 10]] },

    { id: 'run_key', title: 'Key Run', res: 'key', target: 1,
      pitch: "Slide me {t} key off Volt's Generator line. Rosco's got a locked crate for ya.",
      prog: function (p) { return p.keys | 0; },
      consume: function (p) { p.keys = Math.max(0, (p.keys | 0) - 1); },
      reward: [['gold', 360], ['bones', 9]], chest: 'gold' },

    { id: 'rig_lv3', title: 'Rig Tune', res: 'producer Lv', target: 3, milestone: true,
      pitch: "Get one of my rigs to Lv {t}. The Rigger don't deal with amateurs.",
      prog: function (p) { var m = 0, k, v; for (k in (p.prod || {})) { v = (p.prod[k] && p.prod[k].lvl | 0) || 0; if (v > m) m = v; } return m; },
      reward: [['scrap', 3, 'Rare'], ['bones', 8]] },

    { id: 'th_lv2', title: 'Tower Push', res: 'Town Hall Lv', target: 2, milestone: true,
      pitch: "Push the Town Hall to Lv {t}. Then $BCARDD's crew talks real jobs.",
      prog: function (p) { return p.townHall | 0; },
      reward: [['gold', 400], ['bones', 14]] }
  ];
  var DBYID = {}; DELIVERIES.forEach(function (d) { DBYID[d.id] = d; });

  // MANGA MISSIONS -- fixer-voice ACCEPT captions (the toast that stamps the deal).
  // Marrow talks when you take a job; {job} is the run's title. Street voice, canon only.
  var FIXER_ACCEPT = [
    "{job} is yours. It's on my books now, so don't make me chase you, mutt.",
    "Took the {job}? Good. Bring it back clean and the block hears your name right.",
    "{job}. No questions, no shortcuts. Work it and walk it back.",
    "The {job} is on the wire. Deliver and I pay. Simple as a bone."
  ];

  /* p.missions = { done:[], offerIdx:0 } -- the Fixer's offer rotation + milestone
     ledger. Read falsy-default; created lazily ON WRITE only so zero-state stays
     byte-identical (economy.js ensureShape already seeds an empty {} -- harmless). */
  function missionsRead(p) {
    var m = (p && p.missions && typeof p.missions === 'object') ? p.missions : null;
    return {
      done: (m && Array.isArray(m.done)) ? m.done : [],
      offerIdx: (m && typeof m.offerIdx === 'number' && isFinite(m.offerIdx)) ? (m.offerIdx | 0) : 0
    };
  }
  function ensureMissions(p) {                          // write-side shape (inside mutateProfile)
    if (!p.missions || typeof p.missions !== 'object') p.missions = {};
    var m = p.missions;
    if (!Array.isArray(m.done)) m.done = [];
    if (typeof m.offerIdx !== 'number' || !isFinite(m.offerIdx)) m.offerIdx = 0;
    return m;
  }
  function availableDeliveries(p) {                     // consumables always offered; done milestones drop out
    var done = missionsRead(p).done;
    return DELIVERIES.filter(function (d) { return !(d.milestone && done.indexOf(d.id) >= 0); });
  }
  function currentOffer(p) {
    var av = availableDeliveries(p); if (!av.length) return null;
    var n = av.length, i = ((missionsRead(p).offerIdx % n) + n) % n;
    return av[i];
  }
  function activeFixer(ctx) {
    var arr = activeMissions(ctx), i;
    for (i = 0; i < arr.length; i++) { if (arr[i] && arr[i].source === 'fixer') return arr[i]; }
    return null;
  }
  // unified readiness test (recruiter jobs carry state; Fixer jobs are computed live)
  function isReady(ctx, m) {
    if (!m) return false;
    if (m.source === 'fixer') { var j = DBYID[m.jobId], p = profile(ctx); return !!(j && p && j.prog(p) >= j.target); }
    return m.state === 'ready';
  }
  function fixerRewardBit(kind, amt, rar) {
    if (kind === 'gold')  return '+' + (amt | 0) + ' gold';
    if (kind === 'bones') return '+' + (amt | 0) + ' bones';
    if (kind === 'keys' || kind === 'key') return '+' + (amt | 0) + ' key' + ((amt | 0) === 1 ? '' : 's');
    if (kind === 'scrap') return '+' + (amt | 0) + ' ' + (rar || '') + ' scrap';
    return '+' + (amt | 0) + ' ' + kind;
  }
  function fixerRewardBits(job) {
    var bits = (job.reward || []).map(function (r) { return fixerRewardBit(r[0], r[1], r[2]); });
    if (job.chest) bits.push('a ' + job.chest + ' chest');
    return bits;
  }
  function makeFixerMission(job) {
    return {
      id: 'akf_' + Date.now().toString(36) + '_' + Math.floor(Math.random() * 1e6).toString(36),
      source: 'fixer', jobId: job.id,
      giver: 'fixer', giverName: FIXER_NAME, giverCard: null, giverZone: 'THE_YARDS',
      facColor: FIXER_COLOR, facIcon: FIXER_GLYPH,
      title: job.title, objLine: job.pitch.replace('{t}', job.target), res: job.res,
      state: 'active', takenAt: Date.now()
    };
  }

  // ACCEPT a Fixer delivery (the keeper's TAKE THE JOB). One Fixer run at a time;
  // also respects the shared board cap so it never blows past MAX_ACTIVE.
  function acceptFromFixer(ctx) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return null;
    if (activeFixer(ctx)) return null;                       // one Fixer run at a time
    if (activeMissions(ctx).length >= MAX_ACTIVE) return null;
    var p = profile(ctx); if (!p) return null;
    var job = currentOffer(p); if (!job) return null;
    var m = makeFixerMission(job);
    ctx.econ.mutateProfile(function (pp) {
      if (!Array.isArray(pp.activeMissions)) pp.activeMissions = [];   // falsy-default ON WRITE
      pp.activeMissions.push(m);
    });
    try { if (window.akPlayCinematic) akPlayCinematic('mission_accept'); } catch (_e) {}   // STORY STINGER -- job taken (rare, every-time)
    // MANGA MISSIONS -- accept lands a fixer-voice CAPTION toast (the page talks back)
    try { if (ctx.showBanner) ctx.showBanner(FIXER_NAME + ': ' + pick(FIXER_ACCEPT).replace('{job}', m.title), 2.6); } catch (_e2) {}
    return m;
  }
  // NEXT JOB -- rotate the Fixer's offer (only meaningful when no Fixer run is active).
  function fixerNext(ctx) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return;
    ctx.econ.mutateProfile(function (p) { var m = ensureMissions(p); m.offerIdx = (m.offerIdx | 0) + 1; });
  }
  // TURN IN a Fixer delivery -- verify off the live profile, grant FIRST (favor the
  // player), then consume inputs + advance the queue + drop a receipt in one write.
  function turnInFixer(m, ctx) {
    var job = DBYID[m.jobId];
    if (!job) {                                              // template gone -> just clear the dead job
      ctx.econ.mutateProfile(function (p) { p.activeMissions = (Array.isArray(p.activeMissions) ? p.activeMissions : []).filter(function (x) { return x && x.id !== m.id; }); });
      removeBeacon(ctx, m.id);
      return { ok: false, error: 'gone' };
    }
    var p = profile(ctx); if (!p) return { ok: false, error: 'no_ctx' };
    if (job.prog(p) < job.target) return { ok: false, error: 'not_ready' };
    (job.reward || []).forEach(function (r) { try { if (ctx.currency) ctx.currency.grant(r[0], r[0] === 'gold' ? Math.round(r[1] * ((global.AK_ECON && AK_ECON.fixerPayMult) ? AK_ECON.fixerPayMult() : 1)) : r[1], r[2]); } catch (_) {} }); // gold/scrap/bones -- never gems
    if (job.chest && ctx.econ && ctx.econ.grantChest) { try { ctx.econ.grantChest(job.chest, 1); } catch (_) {} }
    var receipt = { id: 'rcpt_' + Date.now().toString(36), title: job.title, giver: FIXER_NAME,
                    zone: 'THE_YARDS', bits: fixerRewardBits(job), t: Date.now() };
    ctx.econ.mutateProfile(function (pp) {
      if (!job.milestone && typeof job.consume === 'function') { try { job.consume(pp); } catch (_) {} }
      var mm = ensureMissions(pp);
      if (job.milestone && mm.done.indexOf(job.id) < 0) mm.done.push(job.id);
      mm.offerIdx = (mm.offerIdx | 0) + 1;                   // surface the NEXT job (Reward Flow)
      if (!Array.isArray(pp.activeMissions)) pp.activeMissions = [];
      pp.activeMissions = pp.activeMissions.filter(function (x) { return x && x.id !== m.id; });
      if (!Array.isArray(pp.missionLog)) pp.missionLog = [];
      pp.missionLog.unshift(receipt);
      if (pp.missionLog.length > 12) pp.missionLog.length = 12;
    });
    removeBeacon(ctx, m.id);
    if (ctx.showBanner) ctx.showBanner(FIXER_NAME + ': squared up -- ' + fixerRewardBits(job).join('  '), 3.0);
    emitMissionWin(m, ctx, receipt);                         // STORY PAYOFF -- name what they just did + tease next
    return { ok: true, mission: m, receipt: receipt };
  }
  // A render-ready view of the Fixer's state for the keeper card (missions.js).
  function fixerView(ctx) {
    ctx = ctx || S.ctx;
    var p = profile(ctx) || {}, active = activeFixer(ctx);
    if (active) {
      var job = DBYID[active.jobId] || null;
      var prog = job ? (job.prog(p) | 0) : 0, target = job ? (job.target | 0) : (active.target | 0);
      return { hasJob: true, mid: active.id, title: active.title, pitch: active.objLine,
               res: (job && job.res) || active.res || '', prog: prog, target: target,
               ready: !!(job && prog >= target), rewardPreview: job ? fixerRewardBits(job).join('  ') : '' };
    }
    var offer = currentOffer(p);
    return { hasJob: false, offer: !!offer, title: offer ? offer.title : '',
             pitch: offer ? offer.pitch.replace('{t}', offer.target) : '',
             target: offer ? offer.target : 0,
             rewardPreview: offer ? fixerRewardBits(offer).join('  ') : '' };
  }

  /* ======================================================================== *
   * OBJECTIVE GENERATION -- always picks a district OTHER than the giver and
   * an economy action, so every job makes you travel + interact.
   * ======================================================================== */
  // Every generated objective is now a REAL economy or combat act -- harvest, haul, or
  // win a scrap. The old bare 'visit'/recon type (satisfied by mere presence) is GONE:
  // it let the "do the task" step be a no-op the instant you reached the district.
  // (The poll still HONORS legacy 'visit' objectives on old saves; we just never mint new ones.)
  function weightedType(rng) {
    var w = [['harvest', 46], ['deliver', 34], ['win_battle', 20]];
    var tot = 0, i; for (i = 0; i < w.length; i++) tot += w[i][1];
    var x = (rng || Math.random)() * tot;
    for (i = 0; i < w.length; i++) { x -= w[i][1]; if (x < 0) return w[i][0]; }
    return 'harvest';
  }
  function weightedMat(rng) {
    var w = [['wood', 45], ['stone', 35], ['metal', 20]];
    var tot = 0, i; for (i = 0; i < w.length; i++) tot += w[i][1];
    var x = (rng || Math.random)() * tot;
    for (i = 0; i < w.length; i++) { x -= w[i][1]; if (x < 0) return w[i][0]; }
    return 'wood';
  }
  function otherDistrict(giverZone, ctx, rng) {
    var pool = UNLOCKED.filter(function (z) { return z !== giverZone; });
    // prefer a district that actually exists in the live ZONES table
    var live = pool.filter(function (z) { try { return ctx && ctx.ZONES && ctx.ZONES[z]; } catch (_) { return false; } });
    var src = live.length ? live : pool;
    return pick(src, rng);
  }
  function pickBuilding(ctx, district, rng) {
    try {
      var z = ctx && ctx.ZONES && ctx.ZONES[district];
      var bs = (z && z.buildings) || [];
      var ok = bs.filter(function (b) { return b && b.id && b.label; });
      return ok.length ? pick(ok, rng) : null;
    } catch (_) { return null; }
  }

  // Build a fully-resolved mission for a recruiter accept. baseKarma = the
  // recruiter NPC's karma value (so the reward scales off the same number the
  // old instant-grant used). Returns the mission object (NOT yet persisted).
  function genMission(giverZone, fac, cardName, ctx, rng, baseKarma) {
    rng = rng || Math.random;
    fac = fac || { name: 'The Crew', key: 'neutral', color: GOLD, icon: '🏙️' };
    baseKarma = (baseKarma | 0) || 11;
    var type = weightedType(rng);
    var district = otherDistrict(giverZone, ctx, rng);
    var obj = { type: type, district: district, need: 1, have: 0, _mark: null };
    var dName = zoneName(ctx, district), objLine = '', title = '';

    if (type === 'harvest') {
      var mat = weightedMat(rng); obj.mat = mat; obj.need = rint(3, 6);
      title = fac.name + ' Supply Run';
      objLine = 'Harvest ' + obj.need + ' ' + MAT_LABEL[mat] + ' in ' + dName;
    } else if (type === 'deliver') {
      var dmat = weightedMat(rng); obj.mat = dmat; obj.need = rint(4, 8);
      title = fac.name + ' Haul';
      objLine = 'Haul ' + obj.need + ' ' + MAT_LABEL[dmat] + ' over to ' + dName;
    } else { // win_battle
      obj.need = 1; obj.kind = 'battle';
      title = fac.name + ' Turf Scrap';
      objLine = 'Win a ranked scrap based out of ' + dName;
    }

    // reward -- soft currency ONLY (gold / scrap / produce / karma + a SHOT at a card).
    // Scales with BOTH the need AND how far you have to haul it: a job clear across the
    // map pays fatter than a hop next door (longer journey = bigger cut, canon req 4).
    var hop = gridDist(ctx, giverZone, district);            // 1..4 districts away
    var distMul = 1 + 0.35 * (hop - 1);
    var reward = {
      karma: baseKarma + rint(4, 12) + (hop - 1) * 3,
      gold: Math.round((60 + obj.need * 20 + rint(0, 60)) * distMul),
      produce: rint(2, 5) + obj.need + (hop - 1) * 2,         // crops tie-in (canon: crops -> currency + missions)
      cardChance: clamp(0.10 + 0.05 * (hop - 1) + (obj.kind === 'battle' ? 0.08 : 0), 0, 0.35)
    };
    if (rng() < 0.34) reward.scrap = { rar: (rng() < 0.25 ? 'Epic' : 'Rare'), amt: rint(2, 4) };

    return {
      id: 'akm_' + Date.now().toString(36) + '_' + Math.floor(rng() * 1e6).toString(36),
      giver: fac.key, giverName: cardName || (fac.name + ' recruiter'), giverCard: cardName || null,
      giverZone: giverZone, facColor: fac.color || GOLD, facIcon: fac.icon || '📋',
      title: title, objLine: objLine, objective: obj, state: 'active',
      reward: reward, takenAt: Date.now()
    };
  }

  /* ======================================================================== *
   * ACCEPT (called from karma.js interact when the recruiter mission fires)
   * ======================================================================== */
  function acceptFromRecruiter(giverZone, fac, cardName, ctx, rng, baseKarma) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return null;
    rng = rng || Math.random;
    var cur = activeMissions(ctx);
    if (cur.length >= MAX_ACTIVE) return null;               // board full -> karma.js shows the "finish a job" line
    var f = fac || zoneFaction(giverZone) || { name: 'The Crew', key: 'neutral', color: GOLD, icon: '🏙️' };
    var m = genMission(giverZone, f, cardName, ctx, rng, baseKarma);
    if (!m) return null;
    ctx.econ.mutateProfile(function (p) {
      if (!Array.isArray(p.activeMissions)) p.activeMissions = [];   // falsy-default ON WRITE
      p.activeMissions.push(m);
    });
    // MANGA MISSIONS -- the giver stamps the deal in their own voice (caption toast)
    try { if (ctx.showBanner) ctx.showBanner(m.giverName + ': ' + m.objLine + '. Come find me when it\'s done.', 2.8); } catch (_e2) {}
    // FIRST FACTION JOB -- teach the four crews (tutorial.js owns the seen-gate)
    try { if (global.AK_TUTORIAL && typeof global.AK_TUTORIAL.firstVisit === 'function') global.AK_TUTORIAL.firstVisit('factions'); } catch (_e3) {}
    return m;
  }

  /* ======================================================================== *
   * ESCORT -- the LOST PUP walk-home job. karma.js routes the lost_pup HERE instead
   * of paying on the spot, so "WALK IT HOME" stops being an instant handout. You find
   * the pup in district X; his HOME is one of his OWN crew's other blocks (district Y).
   * He FOLLOWS at your heel; you have to TRAVERSE the streets to Y -- crossing district
   * lines naturally rolls the encounter table on the way -- and he is delivered the
   * moment you walk him onto his home block. Thank-you + a cut scaled by how far you
   * hauled him. NEVER instant: accept is in X, delivery only fires once zoneId === Y.
   * ======================================================================== */
  function escortHome(foundZone, fac, ctx, rng) {
    var key = fac && fac.key;
    // his own crew's OTHER open blocks (his colors -> his people), never where you found him
    var same = UNLOCKED.filter(function (z) { return z !== foundZone && zoneFaction(z) && zoneFaction(z).key === key; });
    if (same.length) return pick(same, rng);
    return otherDistrict(foundZone, ctx, rng);            // crew has no other open block -> any other district
  }
  function acceptEscort(foundZone, fac, cardName, ctx, rng, baseKarma) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return null;
    rng = rng || Math.random;
    if (activeMissions(ctx).length >= MAX_ACTIVE) return null;   // board full -> karma.js shows the "clear a job" line
    var f = fac || zoneFaction(foundZone) || { name: 'The Crew', key: 'neutral', color: GOLD, icon: '🐶' };
    var home = escortHome(foundZone, f, ctx, rng);
    var hop = gridDist(ctx, foundZone, home);
    baseKarma = (baseKarma | 0) || 12;
    var dName = zoneName(ctx, home);
    var m = {
      id: 'akm_' + Date.now().toString(36) + '_' + Math.floor(rng() * 1e6).toString(36),
      source: 'escort', giver: f.key, giverName: cardName || 'Lost Pup', giverCard: cardName || null,
      giverZone: home, facColor: f.color || GOLD, facIcon: '🐶', homeFac: f.name || 'the crew',
      title: 'Walk the Pup Home',
      objLine: 'Walk the lost pup home to ' + dName + ' -- keep him close through the blocks',
      objective: { type: 'escort', district: home, need: 1, have: 0, _mark: null, pup: true },
      reward: {
        karma: baseKarma + rint(6, 14, rng) + (hop - 1) * 3,
        gold: 50 + hop * 30 + rint(0, 40, rng),
        produce: rint(2, 4, rng) + (hop - 1) * 2,
        cardChance: clamp(0.12 + 0.06 * (hop - 1), 0, 0.30)
      },
      state: 'active', takenAt: Date.now()
    };
    ctx.econ.mutateProfile(function (p) {
      if (!Array.isArray(p.activeMissions)) p.activeMissions = [];   // falsy-default ON WRITE
      p.activeMissions.push(m);
    });
    spawnPup(ctx, m, cardName, f);
    return m;
  }
  // The follower pup -- a light roamer that trots at the player's heel and re-homes to
  // whatever district the player is in (the poll keeps its .zone synced), so he tags
  // along across the map. Tagged _kpup so the encounter prune/cap never touches him.
  function spawnPup(ctx, m, cardName, fac) {
    if (!ctx || !ctx.world || !ctx.world.addRoamer || S.pups[m.id]) return null;
    var px = 850, py = 650;
    try { px = (ctx.me && ctx.me.x) || ((ctx.world.WORLD_W || 1700) / 2); py = (ctx.me && ctx.me.y) || ((ctx.world.WORLD_H || 1300) / 2); } catch (_) {}
    var pup = {
      _kpup: true, mid: m.id, zone: ctx.zoneId, x: px - 40, y: py + 16, r: 13, pulse: 0,
      cardName: cardName || null, faction: fac || null,
      update: pupUpdate, draw: pupDraw
    };
    ctx.world.addRoamer(pup); S.pups[m.id] = pup;
    return pup;
  }
  function removePup(ctx, mid) {
    var h = S.pups[mid]; if (!h) return;
    try { if (ctx && ctx.world && ctx.world.removeRoamer) ctx.world.removeRoamer(h); } catch (_) {}
    delete S.pups[mid];
  }
  function pupUpdate(dt, self, ctx) {
    self.pulse = (self.pulse + dt) % 2;
    var tx, ty; try { tx = ctx.me.x - 34; ty = ctx.me.y + 10; } catch (_) { return; }
    var dx = tx - self.x, dy = ty - self.y, d = Math.hypot(dx, dy);
    if (d > 380) { self.x = tx; self.y = ty; return; }          // fell way behind (zone hop) -> snap to heel
    if (d > 5) { var sp = Math.min(d, 150 * dt); self.x += dx / d * sp; self.y += dy / d * sp; }  // trot to heel, keeps up
  }
  function pupDraw(g, self, ctx) {
    var X = ctx.world.wx(self.x), Y = ctx.world.wy(self.y), r = self.r;
    var col = (self.faction && self.faction.color) || GOLD;
    g.save();
    g.globalAlpha = 0.32; g.fillStyle = '#000';
    g.beginPath(); g.ellipse(X, Y + r * 0.8, r * 0.9, r * 0.4, 0, 0, 6.2832); g.fill();
    g.globalAlpha = 1;
    g.fillStyle = col; g.globalAlpha = 0.92; g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.fill(); g.globalAlpha = 1;
    g.font = Math.round(r * 1.05) + 'px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText('🐶', X, Y + 1);
    var pl = 0.6 + 0.4 * Math.abs(Math.sin((self.pulse || 0) * Math.PI));
    g.lineWidth = 2; g.strokeStyle = 'rgba(124,255,176,' + pl.toFixed(2) + ')';
    g.beginPath(); g.arc(X, Y, r + 3, 0, 6.2832); g.stroke();
    g.font = '800 9px Inter,system-ui'; g.textBaseline = 'alphabetic';
    var nm = 'PUP', tw = g.measureText(nm).width + 8;
    g.fillStyle = 'rgba(8,12,8,.72)'; g.fillRect(X - tw / 2, Y - r - 16, tw, 12);
    g.fillStyle = '#d9f5cf'; g.fillText(nm, X, Y - r - 7);
    g.restore();
  }

  /* ======================================================================== *
   * CO-OP -- RUNNING WITH THE CREW. Upgrade an ALREADY-accepted recruiter job into
   * a crew run: your PACK fields asymmetric roles (Wheelman / Muscle / Inside-Dog),
   * they grind the SHARED objective alongside you (crewHave, banked in the poll),
   * and the loot SPLITS on turn-in. Your faction REP stays whole -- it's your name
   * on the job. The solo flow + recruiter accept are untouched; nothing here runs
   * until you opt in, so zero-state stays byte-identical.
   * ======================================================================== */
  var CREW_ROLES = {
    wheelman: { label: 'Wheelman' },   // drives the haul -- harvest / deliver runs
    muscle:   { label: 'Muscle' },     // loads heavy + guards the goods
    inside:   { label: 'Inside-Dog' }  // slips in + scouts the recon target
  };
  // Field a 2-dog crew with asymmetric roles picked for the objective TYPE (the
  // right dog leads the right job). rate = shared progress/sec banked by the poll.
  function buildCrew(type) {
    var lead, support;
    if (type === 'visit') { lead = 'inside'; support = 'wheelman'; }   // scout up front, wheels behind
    else { lead = 'wheelman'; support = 'muscle'; }                    // harvest / deliver -- haul + muscle
    return {
      size: 2, type: type, rate: CREW_LEAD_RATE + CREW_SUPPORT_RATE,
      roles: [
        { key: lead, label: CREW_ROLES[lead].label, lead: true },
        { key: support, label: CREW_ROLES[support].label, lead: false }
      ]
    };
  }
  // Loot split -- gold + scrap divide across the whole crew (you + crewmates); the
  // player's cut rounds UP (favor the player, same as the turn-in doctrine). Faction
  // karma is YOUR reputation, so it never splits.
  function splitReward(rw, crew) {
    var n = ((crew && crew.size) | 0) + 1;
    if (n <= 1) return rw;
    var out = { karma: rw.karma | 0 };
    if (rw.gold) out.gold = Math.max(1, Math.ceil((rw.gold | 0) / n));
    if (rw.produce) out.produce = Math.max(1, Math.ceil((rw.produce | 0) / n));
    if (rw.scrap && rw.scrap.amt) out.scrap = { rar: rw.scrap.rar, amt: Math.max(1, Math.ceil((rw.scrap.amt | 0) / n)) };
    if (rw.cardChance) out.cardChance = rw.cardChance;       // a shot at a card never splits -- it is a roll, not a stack
    return out;
  }
  // PUBLIC -- bring the crew onto an active recruiter job. The board's "RUN W/ CREW"
  // affordance calls this; the integration pass wires window.AKMissions.acceptWithCrew.
  function acceptWithCrew(mid, ctx) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return { ok: false, error: 'no_ctx' };
    var arr = activeMissions(ctx), m = null, i;
    for (i = 0; i < arr.length; i++) { if (arr[i] && arr[i].id === mid) { m = arr[i]; break; } }
    if (!m) return { ok: false, error: 'gone' };
    if (m.source === 'fixer') return { ok: false, error: 'fixer' };       // Fixer runs count resources off the profile -- no shared bar
    if (m.source === 'escort') return { ok: false, error: 'solo_only' };  // YOU walk the pup home -- no crew to farm the bar for you
    if (!m.objective) return { ok: false, error: 'no_obj' };
    if (m.crew) return { ok: false, error: 'already_crew' };
    if (m.state === 'ready') return { ok: false, error: 'ready' };
    if (m.objective.type === 'win_battle') return { ok: false, error: 'solo_only' };  // your ranked scrap, your win
    var crew = buildCrew(m.objective.type);
    ctx.econ.mutateProfile(function (p) {
      var a = Array.isArray(p.activeMissions) ? p.activeMissions : [];
      for (var k = 0; k < a.length; k++) { if (a[k] && a[k].id === mid) { a[k].crew = crew; break; } }  // crewHave/_crewAcc seed lazily in poll
    });
    if (ctx.showBanner) ctx.showBanner('Crew rolling out -- ' + crew.roles.map(function (r) { return r.label; }).join(' + ') + ' on the job. Cut splits ' + (crew.size + 1) + ' ways.', 3.0);
    return { ok: true, crew: crew };
  }

  /* ======================================================================== *
   * PROGRESS POLL -- observe-only, throttled, ONE write per poll.
   * ======================================================================== */
  function visitHit(ctx, o) {
    // close enough to "tap" the named building (or just be in a building-less district)
    try {
      var z = ctx.activeZone, bs = (z && z.buildings) || [], i, b = null;
      if (!o.building) return true;                          // plain scout -> presence counts
      for (i = 0; i < bs.length; i++) { if (bs[i] && bs[i].id === o.building) { b = bs[i]; break; } }
      if (!b) return true;                                   // building gone from map -> presence counts
      if (!ctx.world || typeof ctx.world.distToMe !== 'function') return true; // headless -> presence counts
      var ty = b.y + (b.h ? b.h / 2 : 48);
      return ctx.world.distToMe(b.x, ty) < VISIT_RANGE;
    } catch (_) { return true; }
  }

  function poll(ctx) {
    var zid = ctx.zoneId, newlyReady = [], escortFinish = [];
    ctx.econ.mutateProfile(function (p) {
      var arr = p.activeMissions; if (!Array.isArray(arr) || !arr.length) return;
      var trophies = p.trophies | 0;
      for (var i = 0; i < arr.length; i++) {
        var m = arr[i]; if (!m || !m.objective || m.state === 'ready') continue;
        var o = m.objective, inZone = (zid === o.district);
        if (o.type === 'harvest') {
          if (inZone) {
            var curM = p[o.mat] | 0;
            if (o._mark == null) o._mark = curM;
            else if (curM > o._mark) { o.have = Math.min(o.need, (o.have | 0) + (curM - o._mark)); o._mark = curM; o._worked = true; }
            else if (curM < o._mark) o._mark = curM;          // spent some -- re-baseline, never subtract progress
          } else if (o._mark != null) o._mark = null;          // left district -> don't bank gains made elsewhere
        } else if (o.type === 'deliver') {
          if (inZone) { o.have = Math.min(o.need, p[o.mat] | 0); if (o.have > 0) o._worked = true; } // proof you hauled the goods to the drop district
        } else if (o.type === 'win_battle') {
          if (inZone) {
            if (o._mark == null) o._mark = trophies;
            else if (trophies > o._mark) { o.have = Math.min(o.need, (o.have | 0) + 1); o._mark = trophies; o._worked = true; }
            else if (trophies < o._mark) o._mark = trophies;   // a loss sank trophies -- re-baseline
          } else if (o._mark != null) o._mark = null;
        } else if (o.type === 'visit') {
          if (inZone && visitHit(ctx, o)) { o.have = o.need; o._worked = true; }   // LEGACY only -- no new visit jobs are minted
        } else if (o.type === 'escort') {
          // ESCORT -- the pup tags along; keep his follower roamer homed to your zone so
          // he stays with you across blocks. He is DELIVERED only once you walk him onto
          // his home district -- accept happens elsewhere, so this can never fire on accept.
          var pup = S.pups[m.id]; if (pup) pup.zone = zid;
          if (inZone) { o.have = o.need; o._worked = true; }
        }
        // CO-OP -- the crew works the SHARED objective too. Their contribution rides
        // on crewHave (NOT have) so it never fights the player-side logic (esp. deliver,
        // which re-reads have off live mats). Throttled, integer-banked, capped at need.
        if (m.crew && m.crew.rate) {
          o._crewAcc = (o._crewAcc || 0) + m.crew.rate * POLL_SEC;
          var addC = Math.floor(o._crewAcc);
          if (addC > 0) { o.crewHave = Math.min(o.need | 0, (o.crewHave | 0) + addC); o._crewAcc -= addC; o._worked = true; }
        }
        // READY-FLIP -- a job can ONLY go ready once REAL work has been banked in the target
        // district. `_worked` is set only by an in-district act (harvest gain / haul proof /
        // battle win / crew bank / escort delivery); legacy progress (have/crewHave > 0) also
        // counts so old saves still resolve. A freshly accepted job sits at have=0/_worked=unset
        // in the GIVER's zone, so accept can NEVER auto-complete -- you must travel + do the task.
        var worked = o._worked || (o.have | 0) > 0 || (o.crewHave | 0) > 0;
        if (effHave(o) >= (o.need | 0) && worked && m.state !== 'ready') {
          m.state = 'ready';
          if (m.source === 'escort') escortFinish.push(m.id);        // escort is DELIVERED on arrival -- no return trip
          else newlyReady.push({ name: m.giverName, zone: m.giverZone });
        }
      }
    });

    // ESCORT delivery -- once the pup is on his home block the job pays out on the spot
    // (turnIn grants + clears; giverZone === the home district so its zone-gate passes).
    for (var e = 0; e < escortFinish.length; e++) { try { turnIn(escortFinish[e], ctx); } catch (_) {} }

    // ready banner (after the write so the read is consistent)
    for (var b = 0; b < newlyReady.length; b++) {
      if (ctx.showBanner) ctx.showBanner('MISSION READY -- return to ' + newlyReady[b].name + ' in ' + zoneName(ctx, newlyReady[b].zone), 2.8);
    }

    // beacon upkeep: a TURN-IN contact stands in the giver's district for every ready job
    syncBeacons(ctx);
  }

  /* ======================================================================== *
   * TURN-IN BEACON -- a light roamer in the giver's district. Walk up to it and
   * it flags you down (opens the JOB BOARD). Host loops _roamers + culls by zone.
   * ======================================================================== */
  function syncBeacons(ctx) {
    if (!ctx.world || !ctx.world.addRoamer) return;
    var arr = activeMissions(ctx), wantByZone = {}, mid;
    var readyHere = arr.filter(function (m) { return m && m.state === 'ready' && m.source !== 'escort'; });  // escort delivers on arrival -- no turn-in beacon
    // prune beacons whose mission is gone or no longer ready
    for (mid in S.beacons) {
      if (!S.beacons.hasOwnProperty(mid)) continue;
      var still = false;
      for (var i = 0; i < readyHere.length; i++) { if (readyHere[i].id === mid) { still = true; break; } }
      if (!still) removeBeacon(ctx, mid);
    }
    // ensure a beacon for each ready job in ITS giver zone (spawn only when we are there)
    for (var j = 0; j < readyHere.length; j++) {
      var m = readyHere[j];
      if (m.giverZone !== ctx.zoneId) continue;               // host only updates/draws roamers in the active zone
      if (S.beacons[m.id]) continue;
      spawnBeacon(ctx, m);
    }
  }
  function spawnBeacon(ctx, m) {
    var WW = (ctx.world.WORLD_W) || 1700, WH = (ctx.world.WORLD_H) || 1300;
    var x = WW * 0.5, y = WH * 0.5, ok = false, tries = 0;
    while (!ok && tries++ < 12) {
      x = 120 + Math.random() * (WW - 240);
      y = 120 + Math.random() * (WH - 240);
      try { ok = ctx.world.distToMe(x, y) > 180; } catch (_) { ok = true; }
    }
    var beacon = {
      _km: true, mid: m.id, zone: m.giverZone, x: x, y: y, rr: 16, pulse: 0, armed: true,
      faction: zoneFaction(m.giverZone), title: m.title,
      update: beaconUpdate, draw: beaconDraw
    };
    ctx.world.addRoamer(beacon); S.beacons[m.id] = beacon;
    return beacon;
  }
  function removeBeacon(ctx, mid) {
    var h = S.beacons[mid]; if (!h) return;
    try { if (ctx && ctx.world && ctx.world.removeRoamer) ctx.world.removeRoamer(h); } catch (_) {}
    delete S.beacons[mid];
  }
  function beaconUpdate(dt, self, ctx) {
    self.pulse = (self.pulse + dt) % 2;
    var d; try { d = ctx.world.distToMe(self.x, self.y); } catch (_) { return; }
    if (d > self.rr + 64) { self.armed = true; return; }      // walked off -> re-arm
    if (self.armed && d < self.rr + 30) { self.armed = false; openBoard(); }
  }
  function beaconDraw(g, self, ctx) {
    var X = ctx.world.wx(self.x), Y = ctx.world.wy(self.y), r = self.rr;
    var col = (self.faction && self.faction.color) || GOLD;
    g.save();
    g.globalAlpha = 0.35; g.fillStyle = '#000';
    g.beginPath(); g.ellipse(X, Y + r * 0.8, r * 0.9, r * 0.4, 0, 0, 6.2832); g.fill();
    g.globalAlpha = 1;
    g.fillStyle = col; g.globalAlpha = 0.92; g.beginPath(); g.arc(X, Y, r, 0, 6.2832); g.fill(); g.globalAlpha = 1;
    g.font = Math.round(r * 1.05) + 'px Inter,system-ui'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText('📋', X, Y + 1);                      // clipboard -- ties back to the recruiter/Fixer
    var pl = 0.6 + 0.4 * Math.abs(Math.sin((self.pulse || 0) * Math.PI));
    g.lineWidth = 2.5; g.strokeStyle = 'rgba(232,197,90,' + pl.toFixed(2) + ')';
    g.beginPath(); g.arc(X, Y, r + 4, 0, 6.2832); g.stroke();
    g.font = '800 10px Inter,system-ui'; g.textBaseline = 'alphabetic';
    var nm = 'TURN IN', tw = g.measureText(nm).width + 10;
    g.fillStyle = 'rgba(20,16,8,.8)'; g.fillRect(X - tw / 2, Y - r - 18, tw, 13);
    g.fillStyle = '#ffe9a8'; g.fillText(nm, X, Y - r - 8);
    g.font = '900 15px Inter,system-ui'; g.fillStyle = GOLD; g.fillText('!', X, Y - r - 22);
    g.restore();
  }

  /* ======================================================================== *
   * STORY PAYOFF -- every turn-in is a plot point (NARRATIVE CONTINUITY SPEC
   * sec.2). On a successful turn-in we resolve a "win beat" (authored on the
   * mission as m.onWinBeat, else from missionPayoff so NO win goes unacknowledged),
   * log its scar to the Old Pack ledger (AKStory.logDeed), show it (AKStory's host
   * renderer, degrading to showBanner), then re-check the chapter gate when the
   * beat advances the saga (AKStory.check). PURE data + reads, fully guarded -- a
   * missing AKStory simply degrades to a banner and a fresh profile is never
   * written. Voice: gritty gold-cyberpunk street, plain punctuation (no dashes).
   * ======================================================================== */
  // The written payoff library (spec sec.2.4). Authored jobs may set any of these
  // directly as m.onWinBeat; missionPayoff picks the type-appropriate one for the
  // generated Fixer / recruiter / escort jobs that carry none.
  var WIN_BEATS = {
    first_fixer: { id: 'first_fixer', advancesChapter: true,
      title: 'YOU GOT A NAME NOW',
      line: "You ran Marrow's first job clean and walked it back like you'd done it a hundred times. The Old Pack stopped circling for half a second. That half second is the whole game, pup. Nobody fed you and you ate anyway.",
      next: "Next: a clan is already your blood. Go work their blocks til they call you family.",
      scar: "Ran the Fixer's first job clean, start to finish, no crew." },
    escort_home: { id: 'escort_pup_homed',
      title: 'THE OLD PACK IS WATCHING',
      line: "You walked the lost pup home through three blocks of steel and never once let go of his collar. Word travels fast on the wire. The whole crew owes you now, and the Old Pack circled tighter tonight. They saw.",
      next: "Next: keep running their turf. Loyalty like that earns colors.",
      scar: "Walked a lost pup home through enemy steel and never let the collar go." },
    turf_scrap: { id: 'turf_scrap_won',
      title: 'THAT BLOCK KNOWS YOUR TEETH NOW',
      line: "You won the scrap and you held the ground after. The block that flinched when you walked in flinches harder now. Respect ain't handed out on these streets. You took it, bite by bite, like the dead ones told you.",
      next: "Next: stack wins like this and the old heads start nodding when you pass.",
      scar: "Won the scrap and held the block after the bell." },
    supply_run: { id: 'supply_run',
      title: 'THE CREW EATS TONIGHT',
      line: "You hauled the goods and the crew eats tonight because of it. Small jobs build big names. The clan marked it. That is how a stray turns into somebody.",
      next: "Next: keep feeding them. Trust gets built one honest haul at a time." },
    long_haul: { id: 'long_haul',
      title: 'YOU MOVE WEIGHT NOW',
      line: "You ran that load clear across the city, past two crews that wanted it for free, and you dropped it where it belonged. People remember who can move weight without losing it. Now they remember you.",
      next: "Next: a name that moves weight gets offered the jobs that pay in respect." },
    clan_colors: { id: 'clan_colors', advancesChapter: true,
      title: 'THEY CALL YOU BY YOUR COLORS',
      line: "They stopped calling you the stray. You bled for these blocks and now you wear the colors. A lone dog dies in winter, the old king said. You found your pack. Don't ever make em regret claiming you.",
      next: "Next: colors don't make you, work does. Climb til they Trust you." },
    old_heads_nod: { id: 'old_heads_nod', advancesChapter: true,
      title: 'THE OLD HEADS NOD',
      line: "You climbed to Trusted and the old heads nod when you pass now. No flinch, no test, just respect. You proved it the only way the streets accept. Over and over til it was undeniable.",
      next: "Next: peace is for pets. The Dog That Eats Names is already counting your blocks. Win a crew war." },
    held_the_line: { id: 'held_the_line', advancesChapter: true,
      title: 'YOU HELD THE LINE',
      line: "They came for what's yours and you buried them in the concrete before the Dog That Eats Names could swallow your name whole. The blocks held. The crew rides for you now, and the rivals tell stories about the wrong dog to cross.",
      next: "Next: one war don't crown nobody. Rule the whole season.",
      scar: "Held the line in a crew war and buried the ones who came for mine." },
    season_era: { id: 'season_era', advancesChapter: true,
      title: 'AN ERA WITH YOUR NAME ON IT',
      line: "You ran the whole season and pushed the clan's blocks to the top of the board. An era belongs to whoever survives it. The Mongrel King has eaten every season but his own. Make this one yours, and make him remember it.",
      next: "Next: the season's almost up. The King is up that tower and he won't kneel." },
    three_blocks: { id: 'three_blocks', advancesChapter: true,
      title: 'THREE BLOCKS FLY YOUR COLORS',
      line: "Three districts fly your colors at dawn now. That is real weight. Hold it. Lose it and the story stalls til you take it back, cause out here you are only as big as the ground you can keep.",
      next: "Next: turn three into the whole city." },
    king_choked: { id: 'king_choked', advancesChapter: true,
      title: 'YOU MADE HIM CHOKE ON YOUR NAME',
      line: "You climbed the Town Hall tower and faced the Dog That Eats Names where every king before you fell. He ate names for a living. Tonight he choked on yours. The Old Pack went dead silent and made room for one more crown.",
      next: "Next: take what he stole from all of us. Take the crown.",
      scar: "Climbed the tower and beat the Mongrel King in the final." },
    crowned_block: { id: 'crowned_block', advancesChapter: true,
      title: 'KING OF THE BLOCK',
      line: "You put the Dog That Eats Names in the dirt and pulled the crown off his skull. You are the King now, the one the strays will dream about. But the Old Pack drift their eyes past you, up to the floodlights over the pound fence. The collar was always the real teeth. Now you finally see it.",
      next: "Next: hold the crown. Choose an heir when you're ready and let the bloodline ride.",
      scar: "Took the crown and became the one the strays dream about." }
  };

  // current CROWN BLOODLINE stage idx (guarded read of AKStory) -- lets the Fixer's
  // very first turn-in land the naming beat and later runs the supply beat.
  function storyIdxNow() {
    try { return (global.AKStory && AKStory.stage) ? (AKStory.stage().idx | 0) : 0; } catch (_) { return 0; }
  }
  // PURE-DATA fallback resolver: pick a written beat by the completed mission's
  // source + objective type, so generated jobs (Fixer / recruiter / escort) always
  // land a line. Never throws; returns a beat for every shape (supply_run default).
  function missionPayoff(m, ctx) {
    try {
      m = m || {}; var o = m.objective || {};
      if (m.source === 'fixer') return (storyIdxNow() <= 0) ? WIN_BEATS.first_fixer : WIN_BEATS.supply_run;
      if (m.source === 'escort' || o.type === 'escort') return WIN_BEATS.escort_home;
      var t = o.type || o.kind || '';
      if (t === 'win_battle' || t === 'battle') return WIN_BEATS.turf_scrap;
      if (t === 'deliver') return WIN_BEATS.long_haul;
      if (t === 'harvest' || t === 'visit') return WIN_BEATS.supply_run;
      return WIN_BEATS.supply_run;
    } catch (_) { return WIN_BEATS.supply_run; }
  }
  /* ======================================================================== *
   * MANGA MISSIONS (bible 9.1) -- the turn-in IS a comic page. A successful
   * turn-in slams AK_MANGA.victoryPage: JOB DONE across the seam, the payout
   * stamped on as loot rows, and a heroLine spoken by the RUNNER (his own
   * cards_stories street bark) or by Marrow's flavor when the runner is quiet.
   * Fully guarded: no AK_MANGA (or headless) degrades to the STINGER ONLY --
   * the exact akPlayCinematic('mission_complete') behavior that shipped before.
   * ======================================================================== */
  function pad4(n) { n = parseInt(n, 10) || 0; var s = String(n); while (s.length < 4) s = '0' + s; return s; }
  // the RUNNER's own street bark (p.heroName -> CANON_CARDS -> AK_STORIES
  // ambientBarks.streetTalk). Pure guarded reads; '' when anything is missing.
  function runnerBark(ctx) {
    try {
      var p = profile(ctx || S.ctx), nm = p && p.heroName; if (!nm) return '';
      var L = global.CANON_CARDS || [], c = null, i;
      for (i = 0; i < L.length; i++) { if (L[i] && (L[i].name === nm || L[i].id === nm)) { c = L[i]; break; } }
      if (!c || !c.cardNumber) return '';
      var st = global.AK_STORIES && global.AK_STORIES[pad4(c.cardNumber)];
      var lines = st && st.ambientBarks && st.ambientBarks.streetTalk;
      return (lines && lines.length) ? String(pick(lines)) : '';
    } catch (_) { return ''; }
  }
  // Marrow's turn-in flavor -- the fallback voice when the runner has no bark
  var FIXER_FLAVOR = [
    "Marrow: clean work, mutt. The block keeps the receipts.",
    "Marrow: paid in full. Don't spend it all on one bone.",
    "Marrow: job done, name heavier. That's how it works out here.",
    "Marrow: you deliver, I remember. The whole block remembers."
  ];
  function heroLineFor(m, ctx) {
    var line = runnerBark(ctx);
    if (!line) line = pick(FIXER_FLAVOR);
    // first sentence only -- the page's speech row is one stamped line, not a paragraph
    var cut = line.indexOf('. ');
    if (cut > 0 && cut < line.length - 2) line = line.slice(0, cut + 1);
    return line;
  }
  // receipt bits ('+240 gold', 'a gold chest') -> victoryPage loot rows
  function lootIcon(bit) {
    var s = String(bit || '').toLowerCase();
    if (s.indexOf('chest') >= 0) return '';                 // chests carry no coin icon
    if (s.indexOf('gold') >= 0) return 'assets/ui/cur_gold.jpg';
    if (s.indexOf('bone') >= 0) return 'assets/ui/cur_bones.jpg';
    if (s.indexOf('key') >= 0) return 'assets/ui/cur_keys.jpg';
    return '';
  }
  function lootRowsFrom(bits) {
    var rows = [];
    (bits || []).forEach(function (b) {
      b = String(b || ''); if (!b) return;
      var mm = b.match(/^\+\s*(\d+)\s+(.+)$/);
      if (mm) rows.push({ icon: lootIcon(b), label: mm[2].toUpperCase(), qty: mm[1] | 0 });
      else rows.push({ icon: lootIcon(b), label: b.toUpperCase() });
    });
    return rows;
  }
  // the one-page comic beat -- STINGER-ONLY fallback when the manga layer is out
  function mangaVictory(m, ctx, receipt) {
    var shown = false;
    try {
      var MG = global.AK_MANGA;
      if (MG && typeof MG.victoryPage === 'function') {
        var rows = lootRowsFrom(receipt && receipt.bits);
        var line = heroLineFor(m, ctx);
        if (line) rows.unshift({ icon: (m && m.facIcon) || FIXER_GLYPH, label: line }); // the spoken beat leads the page
        shown = !!MG.victoryPage({ won: true, title: 'JOB DONE', heroLine: line,
                                   accent: (m && m.facColor) || GOLD, loot: rows, shareKind: 'win' });
      }
    } catch (_) { shown = false; }
    if (!shown) { try { if (window.akPlayCinematic) akPlayCinematic('mission_complete'); } catch (_e) {} }  // STORY STINGER -- the pre-manga behavior, byte-identical
  }

  // Fire the STORY PAYOFF on a successful turn-in: resolve the beat, log its scar,
  // show it (AKStory host renderer, else showBanner), then re-check the chapter gate
  // if it advances the saga. Fully guarded -- a missing AKStory just banners the line.
  function emitMissionWin(m, ctx, receipt) {
    mangaVictory(m, ctx, receipt);   // MANGA MISSIONS -- the comic page (or the stinger) BEFORE the beat surfaces
    try {
      if (!m) return;
      var beat = m.onWinBeat || missionPayoff(m, ctx);
      if (!beat) return;
      var ST = global.AKStory;
      if (ST && beat.scar && typeof ST.logDeed === 'function') { try { ST.logDeed(beat.scar); } catch (_) {} }
      var shown = false;
      if (ST && typeof ST.storyBeat === 'function') { try { shown = !!ST.storyBeat(beat, ctx); } catch (_) { shown = false; } }
      if (!shown && ctx && typeof ctx.showBanner === 'function') { try { ctx.showBanner(beat.line, 4.2); shown = true; } catch (_) {} }
      if (beat.advancesChapter && ST && typeof ST.check === 'function') { try { ST.check(); } catch (_) {} }
    } catch (_) {}
  }

  /* ======================================================================== *
   * TURN-IN -- verify ready + in the giver district, grant FIRST (favor the
   * player), drop a RECEIPT, then clear the job in one atomic write.
   * ======================================================================== */
  function rewardBits(rw) {
    var bits = [];
    if (rw.karma) bits.push('+' + (rw.karma | 0) + ' karma');
    if (rw.gold) bits.push('+' + (rw.gold | 0) + ' gold');
    if (rw.produce) bits.push('+' + (rw.produce | 0) + ' produce');
    if (rw.scrap && rw.scrap.amt) bits.push('+' + (rw.scrap.amt | 0) + ' ' + rw.scrap.rar + ' scrap');
    if (rw.cardChance) bits.push('a shot at a card');
    return bits;
  }
  function turnIn(mid, ctx) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return { ok: false, error: 'no_ctx' };
    var arr = activeMissions(ctx), m = null, i;
    for (i = 0; i < arr.length; i++) { if (arr[i] && arr[i].id === mid) { m = arr[i]; break; } }
    if (!m) return { ok: false, error: 'gone' };
    if (m.source === 'fixer') return turnInFixer(m, ctx);    // unified flow -- Fixer runs verify off the live profile
    if (m.state !== 'ready') return { ok: false, error: 'not_ready' };
    if (ctx.zoneId !== m.giverZone) return { ok: false, error: 'wrong_zone' };

    var rw = m.reward || {};
    var eff = m.crew ? splitReward(rw, m.crew) : rw;   // CO-OP -- loot splits with the crew (rep stays yours)
    try { if (eff.gold && ctx.currency) ctx.currency.grant('gold', Math.round((eff.gold | 0) * ((global.AK_ECON && AK_ECON.fixerPayMult) ? AK_ECON.fixerPayMult() : 1))); } catch (_) {}
    try { if (eff.scrap && eff.scrap.amt && ctx.currency) ctx.currency.grant('scrap', eff.scrap.amt | 0, eff.scrap.rar); } catch (_) {}
    try { if (eff.produce && ctx.econ) ctx.econ.mutateProfile(function (p) { p.produce = Math.max(0, (p.produce | 0) + (eff.produce | 0)); }); } catch (_) {} // crops payout (no currency.grant lane for produce)
    var karmaRes = null;
    try { if (eff.karma && global.AKKarma && global.AKKarma.addKarma) karmaRes = global.AKKarma.addKarma(m.giverZone, eff.karma | 0, ctx); } catch (_) {}
    // a SHOT at a card -- the canon card path is a chest (encounter / Town Hall / shop / chest).
    // Rolled on turn-in, scaled by the job: a turf scrap cracks a bronze crate, the rest a wood.
    // Soft only, never gems / $BCARDD. The chance does not split with the crew.
    var cardHit = null;
    try {
      if ((rw.cardChance || 0) > 0 && Math.random() < rw.cardChance && ctx.econ && ctx.econ.grantChest) {
        cardHit = (m.objective && m.objective.kind === 'battle') ? 'bronze' : 'wood';
        ctx.econ.grantChest(cardHit, 1);
      }
    } catch (_) {}

    var bits = rewardBits(eff).filter(function (b) { return b !== 'a shot at a card'; });
    if (cardHit) bits.push('+1 ' + cardHit + ' chest');       // the shot LANDED -- record the real drop on the receipt
    var receipt = { id: 'rcpt_' + Date.now().toString(36), title: m.title, giver: m.giverName,
                    zone: m.giverZone, bits: bits, t: Date.now() };
    ctx.econ.mutateProfile(function (p) {
      if (!Array.isArray(p.activeMissions)) p.activeMissions = [];
      p.activeMissions = p.activeMissions.filter(function (x) { return x && x.id !== mid; });
      if (!Array.isArray(p.missionLog)) p.missionLog = [];     // falsy-default ON WRITE
      p.missionLog.unshift(receipt);
      if (p.missionLog.length > 12) p.missionLog.length = 12;
    });
    removeBeacon(ctx, mid);
    removePup(ctx, mid);                                       // ESCORT -- the pup is home now, retire the follower

    var lvUp = (karmaRes && karmaRes.leveledUp) ? ('  You are now ' + karmaRes.tier.name + ' here.') : '';
    var crewNote = m.crew ? ('  (split ' + (((m.crew.size | 0) + 1)) + ' ways with the crew)') : '';
    if (ctx.showBanner) {
      if (m.source === 'escort') ctx.showBanner(m.giverName + ': home safe -- ' + (m.homeFac || 'the crew') + ' owe you one. Your cut: ' + bits.join('  ') + lvUp, 3.2);
      else ctx.showBanner(m.giverName + ': good work. Here is your cut -- ' + bits.join('  ') + lvUp + crewNote, 3.0);
    }
    emitMissionWin(m, ctx, receipt);                         // STORY PAYOFF -- name what they just did + tease next
    return { ok: true, mission: m, karma: karmaRes, receipt: receipt };
  }
  function abandon(mid, ctx) {
    ctx = ctx || S.ctx; if (!ctx || !ctx.econ) return { ok: false };
    var arr = activeMissions(ctx), m = null, i;
    for (i = 0; i < arr.length; i++) { if (arr[i] && arr[i].id === mid) { m = arr[i]; break; } }
    var wasFixer = !!(m && m.source === 'fixer');
    ctx.econ.mutateProfile(function (p) {
      if (!Array.isArray(p.activeMissions)) return;
      p.activeMissions = p.activeMissions.filter(function (x) { return x && x.id !== mid; });
      if (wasFixer) { var mm = ensureMissions(p); mm.offerIdx = (mm.offerIdx | 0) + 1; }  // rotate the Fixer's next offer
    });
    removeBeacon(ctx, mid);
    removePup(ctx, mid);                                       // ESCORT -- dropped the walk, the pup wanders off
    if (m && ctx.showBanner) ctx.showBanner('Dropped the job: ' + m.title, 1.8);
    return { ok: true };
  }

  /* ======================================================================== *
   * THE JOB BOARD -- a self-contained fixed-position DOM panel (mirrors the
   * trading.js / social.js pattern). Exposed as window.akOpenMissions.
   * ======================================================================== */
  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k]; if (v == null) return;
      if (k === 'class') e.className = v;
      else if (k === 'text') e.textContent = v;
      else if (k.slice(0, 2) === 'on' && typeof v === 'function') e[k] = v;
      else e.setAttribute(k, v);
    });
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) {
      if (c == null || c === false) return;
      e.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c);
    });
    return e;
  }
  function injectCss() {
    if (document.getElementById('ak-missions-css')) return;
    var st = document.createElement('style'); st.id = 'ak-missions-css';
    st.textContent = [
      '#ak-missions{position:fixed;inset:0;z-index:62;display:none;flex-direction:column;background:linear-gradient(180deg,#0c0b08,#08080c);color:#e9e9ee;font-family:Inter,system-ui,sans-serif}',
      '#ak-missions.open{display:flex}',
      '.akm-top{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid rgba(201,168,76,.22)}',
      '.akm-glyph{font-size:26px;line-height:1}',
      '.akm-ttl{flex:1}.akm-ttl h2{margin:0;font-size:16px;letter-spacing:1px;color:#e8c55a;font-family:Cinzel,serif}',
      '.akm-ttl .sub{color:#9a8f6a;font-size:11px}',
      '.akm-x{background:none;border:0;color:#bbb;font-size:26px;line-height:1;cursor:pointer}',
      '.akm-body{flex:1;overflow-y:auto;padding:10px 12px;-webkit-overflow-scrolling:touch}',
      '.akm-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:12px;margin-bottom:10px}',
      '.akm-card.ready{border-color:rgba(232,197,90,.55);background:rgba(232,197,90,.06)}',
      '.akm-head{display:flex;align-items:center;gap:8px;margin-bottom:4px}',
      '.akm-fic{font-size:18px;line-height:1}',
      '.akm-nm{font-weight:800;color:#fff;font-size:14px;flex:1}',
      '.akm-pill{font-size:10px;font-weight:800;letter-spacing:.06em;padding:3px 8px;border-radius:20px;background:rgba(255,255,255,.07);color:#cfc7a8}',
      '.akm-pill.go{background:rgba(232,197,90,.18);color:#ffe9a8}',
      '.akm-obj{color:#cfc7a8;font-size:12px;margin:4px 0 8px}',
      '.akm-bar{height:8px;border-radius:6px;background:rgba(255,255,255,.08);overflow:hidden;margin-bottom:4px}',
      '.akm-fill{height:100%;background:linear-gradient(90deg,#c9a84c,#e8c55a)}',
      '.akm-prog{font-size:11px;color:#9a9aa6;margin-bottom:8px}',
      '.akm-rw{font-size:11px;color:#e8c55a;margin-bottom:8px}',
      '.akm-btns{display:flex;gap:8px}',
      '.akm-btn{flex:2;background:linear-gradient(180deg,#e8c55a,#c9a84c);color:#1a1405;border:0;border-radius:9px;padding:11px 14px;font-weight:800;letter-spacing:.4px;cursor:pointer;font-size:13px}',
      '.akm-btn.ghost{flex:1;background:rgba(255,255,255,.05);color:#e9e9ee;border:1px solid rgba(255,255,255,.16)}',
      '.akm-btn.dng{flex:1;background:rgba(220,80,80,.14);color:#f3a0a0;border:1px solid rgba(220,80,80,.3)}',
      '.akm-btn:active{transform:scale(.97)}.akm-btn[disabled]{opacity:.5;cursor:not-allowed;filter:grayscale(.4)}',
      '.akm-note{color:#9a9aa6;font-size:12px;text-align:center;padding:24px 10px;line-height:1.5}',
      '.akm-sec{color:#9a8f6a;font-size:11px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;margin:6px 2px 8px}',
      '.akm-rcpt{display:flex;gap:8px;align-items:center;padding:8px 4px;border-bottom:1px solid rgba(255,255,255,.06);font-size:12px}',
      '.akm-rcpt .t{flex:1;color:#cfc7a8}.akm-rcpt .v{color:#e8c55a;font-weight:700}',
      '.akm-crew{display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin:-2px 0 8px}',
      '.akm-crew .lbl{font-size:10px;font-weight:800;letter-spacing:.08em;color:#ff9d5c}',
      '.akm-crew .cut{font-size:10px;color:#9a8f6a}',
      '.akm-role{font-size:10px;font-weight:800;letter-spacing:.04em;padding:2px 7px;border-radius:20px;background:rgba(255,255,255,.06);color:#cfc7a8}',
      '.akm-role.lead{background:rgba(232,197,90,.16);color:#ffe9a8}'
    ].join('');
    document.head.appendChild(st);
  }

  function progLabel(o) { return effHave(o) + ' / ' + (o.need | 0); }
  function rewardLine(rw) { var b = rewardBits(rw); return b.length ? ('Pays ' + b.join('  ')) : 'Pays out'; }

  function buildCard(ctx, m) {
    var o = m.objective, ready = (m.state === 'ready'), inZone = (ctx.zoneId === m.giverZone);
    var have = effHave(o);
    var pct = o.need ? clamp(Math.round(100 * have / o.need), 0, 100) : 0;
    var head = mk('div', { class: 'akm-head' }, [
      mk('span', { class: 'akm-fic', text: m.facIcon || '📋' }),
      mk('span', { class: 'akm-nm', text: m.title }),
      mk('span', { class: 'akm-pill' + (ready ? ' go' : ''), text: ready ? (inZone ? 'TURN IN' : 'READY') : 'ACTIVE' })
    ]);
    var obj = mk('div', { class: 'akm-obj', text: m.objLine });
    var bar = mk('div', { class: 'akm-bar' }, [mk('div', { class: 'akm-fill', style: 'width:' + pct + '%' })]);
    var prog = mk('div', { class: 'akm-prog', text: ready
      ? (inZone ? ('Report to ' + m.giverName) : ('Return to ' + m.giverName + ' in ' + zoneName(ctx, m.giverZone)))
      : (progLabel(o) + '  --  in ' + zoneName(ctx, o.district)) });
    var rw = mk('div', { class: 'akm-rw', text: rewardLine(m.reward) });

    var actBtn;
    if (ready && inZone) {
      actBtn = mk('button', { class: 'akm-btn', type: 'button', text: 'TURN IN', onclick: function () {
        var r = turnIn(m.id, ctx); if (r.ok) render(ctx);
      } });
    } else if (ready) {
      actBtn = mk('button', { class: 'akm-btn', type: 'button', disabled: 'disabled', text: 'GO TO ' + zoneName(ctx, m.giverZone) });
    } else {
      actBtn = mk('button', { class: 'akm-btn', type: 'button', disabled: 'disabled', text: progLabel(o) });
    }
    var drop = mk('button', { class: 'akm-btn dng', type: 'button', text: 'DROP', onclick: function () {
      abandon(m.id, ctx); render(ctx);
    } });

    // CO-OP affordance -- a status row when the crew is rolling, or a RUN W/ CREW
    // button when the job is eligible (objective job, not yet ready, not a solo scrap).
    var crewEls = [];
    if (m.crew && m.crew.roles) {
      var chips = m.crew.roles.map(function (r) { return mk('span', { class: 'akm-role' + (r.lead ? ' lead' : ''), text: (r.lead ? '★ ' : '') + r.label }); });
      crewEls.push(mk('div', { class: 'akm-crew' },
        [mk('span', { class: 'lbl', text: 'RUNNING W/ CREW' })].concat(chips, [mk('span', { class: 'cut', text: 'cut splits ' + ((m.crew.size | 0) + 1) + ' ways' })])));
    }
    var btns = [actBtn];
    if (!m.crew && !ready && o.type !== 'win_battle' && m.source !== 'escort') {
      btns.push(mk('button', { class: 'akm-btn ghost', type: 'button', text: 'RUN W/ CREW', onclick: function () {
        var r = acceptWithCrew(m.id, ctx); if (r && r.ok) render(ctx);
      } }));
    }
    btns.push(drop);

    return mk('div', { class: 'akm-card' + (ready ? ' ready' : '') }, [head, obj, bar, prog, rw].concat(crewEls, [mk('div', { class: 'akm-btns' }, btns)]));
  }

  // Fixer runs read progress straight off the live profile (no travel, no beacon),
  // so they get their own card. Same board, same turn-in flow.
  function buildFixerCard(ctx, m) {
    var p = profile(ctx) || {}, job = DBYID[m.jobId] || null;
    var target = job ? (job.target | 0) : (m.target | 0);
    var prog = job ? (job.prog(p) | 0) : 0;
    var ready = !!(job && prog >= target);
    var pct = target ? clamp(Math.round(100 * Math.min(prog, target) / target), 0, 100) : 0;
    var head = mk('div', { class: 'akm-head' }, [
      mk('span', { class: 'akm-fic', text: m.facIcon || FIXER_GLYPH }),
      mk('span', { class: 'akm-nm', text: m.title }),
      mk('span', { class: 'akm-pill' + (ready ? ' go' : ''), text: ready ? 'TURN IN' : 'ACTIVE' })
    ]);
    var obj = mk('div', { class: 'akm-obj', text: m.objLine });
    var bar = mk('div', { class: 'akm-bar' }, [mk('div', { class: 'akm-fill', style: 'width:' + pct + '%' })]);
    var prog2 = mk('div', { class: 'akm-prog', text: ready
      ? ('Done -- bring it to ' + FIXER_NAME)
      : (Math.min(prog, target) + ' / ' + target + ' ' + ((job && job.res) || m.res || '')) });
    var rw = mk('div', { class: 'akm-rw', text: job ? ('Pays ' + fixerRewardBits(job).join('  ')) : 'Pays out' });
    var actBtn;
    if (ready) {
      actBtn = mk('button', { class: 'akm-btn', type: 'button', text: 'TURN IN', onclick: function () {
        var r = turnIn(m.id, ctx); if (r && r.ok) render(ctx);
      } });
    } else {
      actBtn = mk('button', { class: 'akm-btn', type: 'button', disabled: 'disabled', text: Math.min(prog, target) + ' / ' + target });
    }
    var drop = mk('button', { class: 'akm-btn dng', type: 'button', text: 'DROP', onclick: function () {
      abandon(m.id, ctx); render(ctx);
    } });
    return mk('div', { class: 'akm-card' + (ready ? ' ready' : '') }, [head, obj, bar, prog2, rw, mk('div', { class: 'akm-btns' }, [actBtn, drop])]);
  }

  function render(ctx) {
    ctx = ctx || S.ctx; if (!S.bodyEl) return;
    var p = profile(ctx) || {}, arr = Array.isArray(p.activeMissions) ? p.activeMissions : [];
    var log = Array.isArray(p.missionLog) ? p.missionLog : [];
    var kids = [];
    if (!arr.length) {
      kids.push(mk('div', { class: 'akm-note', text: 'No active jobs. Hit Marrow the Fixer in THE YARDS for a run, or flag down a faction Recruiter roaming the districts.' }));
    } else {
      for (var i = 0; i < arr.length; i++) {
        var mm2 = arr[i]; if (!mm2) continue;
        if (mm2.source === 'fixer') kids.push(buildFixerCard(ctx, mm2));
        else if (mm2.objective) kids.push(buildCard(ctx, mm2));
      }
    }
    if (log.length) {
      kids.push(mk('div', { class: 'akm-sec', text: 'Receipts' }));
      for (var j = 0; j < Math.min(log.length, 6); j++) {
        var r = log[j];
        kids.push(mk('div', { class: 'akm-rcpt' }, [
          mk('span', { text: '🧾' }),
          mk('span', { class: 't', text: r.title + '  (' + (r.giver || '') + ')' }),
          mk('span', { class: 'v', text: (r.bits && r.bits.length) ? r.bits.join(' ') : 'paid' })
        ]));
      }
    }
    S.bodyEl.replaceChildren.apply(S.bodyEl, kids);
  }

  function openBoard() {
    var ctx = S.ctx;
    if (typeof document === 'undefined' || !document.body) return;
    if (S.open) { render(ctx); return; }
    injectCss();
    var glyph = mk('span', { class: 'akm-glyph', text: '📋' });
    var ttl = mk('div', { class: 'akm-ttl' }, [mk('h2', { text: 'JOB BOARD' }), mk('div', { class: 'sub', text: 'The Fixer runs + faction jobs -- work them, report back for your cut' })]);
    var x = mk('button', { class: 'akm-x', type: 'button', 'aria-label': 'close', text: '×', onclick: closeBoard });
    var top = mk('div', { class: 'akm-top' }, [glyph, ttl, x]);
    S.bodyEl = mk('div', { class: 'akm-body' });
    S.root = mk('section', { id: 'ak-missions' }, [top, S.bodyEl]);
    document.body.appendChild(S.root);
    S.open = true;
    render(ctx);
    S.root.classList.add('open');
  }
  function closeBoard() {
    S.open = false;
    if (S.root) { try { S.root.remove(); } catch (_) {} S.root = null; S.bodyEl = null; }
  }

  /* ======================================================================== *
   * PUBLIC API -- exported BEFORE the registry bail (headless-safe).
   * ======================================================================== */
  global.AKMissions = {
    MAX_ACTIVE: MAX_ACTIVE,
    acceptFromRecruiter: acceptFromRecruiter,   // karma.js (recruiter) -- unchanged contract
    acceptEscort: acceptEscort,                 // karma.js (lost pup) -- walk-home ESCORT job (not an instant payout)
    acceptWithCrew: acceptWithCrew,             // CO-OP -- upgrade an active job to a crew run (loot splits)
    acceptFromFixer: acceptFromFixer,           // missions.js (the Fixer keeper)
    fixerNext: fixerNext,                       // missions.js NEXT JOB
    fixerView: fixerView,                       // missions.js keeper-card render data
    list: function () { return activeMissions(S.ctx).slice(); },
    count: function () { return activeMissions(S.ctx).length; },
    readyCount: function () { var c = S.ctx; return activeMissions(c).filter(function (m) { return isReady(c, m); }).length; },
    turnIn: turnIn,
    abandon: abandon,
    emitMissionWin: emitMissionWin,             // STORY PAYOFF -- fire a win beat for a turn-in (host/debug)
    missionPayoff: missionPayoff,               // pure-data beat resolver (by source + objective type)
    WIN_BEATS: WIN_BEATS,                        // the written payoff library (spec sec.2.4)
    open: openBoard
  };
  global.akOpenMissions = openBoard;

  /* hub-only lifecycle */
  if (!global.AK_SYSTEMS) return;
  global.AK_SYSTEMS.register({
    id: 'mission_active',
    init: function (ctx) { S.ctx = ctx; },
    onTick: function (dt, ctx) {
      S.ctx = ctx;
      S._acc += dt;
      if (S._acc < POLL_SEC) return;
      S._acc = 0;
      try { if (activeMissions(ctx).length) poll(ctx); } catch (_) {}
    }
  });

})(typeof window !== 'undefined' ? window : globalThis);
