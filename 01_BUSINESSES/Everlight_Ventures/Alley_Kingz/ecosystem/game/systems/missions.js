/* game/systems/missions.js -- AK_SYSTEMS module: WAVE 2 "MISSIONS".
   ------------------------------------------------------------------------
   THE FIXER (HOME of the Hit List). Marrow the Fixer runs jobs out of THE
   FIXER (THE_YARDS). Two layers, one keeper card:

     (A) LOCAL DELIVERIES  -- the Fixer GIVES one job at a time; you TAKE it,
         grind it, then TURN IT IN. Every delivery is verified straight off
         the live profile (no event bus, no shared-file edits), so it is
         dupe-proof and headless-safe:
            * "bring N <rarity> scrap"   -> reads p.scrap, consumes on turn-in
            * "front N gold"             -> reads p.coins, consumes (a gold sink)
            * "slide me a key"           -> reads p.keys (keys come off the GEN
                                            producer), consumes + pays a chest
            * "get a rig to Lv 3"        -> reads p.prod[*].lvl  (collect from a
                                            producer: you raise it by collecting)
            * "push the Town Hall to L2" -> reads p.townHall (one-time milestone)
         Rewards ride ctx.currency (gold / scrap / keys / BONES) + AK_ECON
         chests. BONES feed the 6 handler skill trees (The Mender / Tracker /
         Shadow / Rigger / Bruiser / Dealer), so the loop ties straight into
         the meta. Monopoly-GO Reward Flow: the instant you turn one in, the
         NEXT job surfaces -- there is never a dead end.

     (B) THE LIVE HIT LIST -- the server daily/weekly quests (the same surface
         as shop/shop.html#hit2). Read + claimed through the LIVE `ak-quests`
         edge fn and paid out through the `ak_grants` rail (via AKSocial.
         claimGrants). The keeper card shows how many are ready and claims them
         in place (surface-the-next), or opens the full Hit List screen.

   HARD-LAW COMPLIANCE:
   - Soft currency + bones ONLY. No gems (server-only -> grant('gems') is a
     no-op), no $BCARDD / ALK anywhere in a reward or turn-in. Card/handler
     names are reused BY NAME as flavor only -- never re-stat, never placeholder.
   - The ONLY new player-state is `p.missions:{}` + the shared `p.bones:0`, both
     already added once by the Lead in economy.js ensureShape (Section 6.B). A
     zero-state profile stays byte-identical: nothing happens until you walk in
     and TAKE a job.
   - Headless-safe: bails if AK_SYSTEMS is absent; zero top-level DOM/localStorage;
     every storage touch is through AK_ECON (already try/catch wrapped); every
     server call is guarded by AKAccount presence and degrades gracefully offline.
   - Owns ONLY the FIXER interior (Section 4). Returns false for everything else.
   ------------------------------------------------------------------------ */
(function (global) {
  'use strict';
  if (!global.AK_SYSTEMS) return;            // hub-only; node harness / pages without the registry no-op

  var BID = 'FIXER';                          // the one building this wave owns (Section 4)
  var KEEPER = { name: 'Marrow the Fixer', glyph: '📋' }; // clipboard -- he runs the job board
  var PIP_COLOR = '#ff9d5c';                  // matches the FIXER building tint in index.html

  // ---- THE DELIVERY POOL ----------------------------------------------------
  // Each job: prog(p) reads the live profile; ready = prog >= target. Consumable
  // jobs deduct their inputs on turn-in (a real sink); milestone jobs pay once
  // then never re-offer (tracked in p.missions.done). reward = [[kind,amt,rarity?]],
  // chest = optional AK_ECON chest tier. Flavor reuses canon card + handler names.
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

  // ---- module-private state (NO profile state lives here) -------------------
  var S = { server: null, fetching: false, fetched: false, open: false,
            ready: false, _acc: 0, _now: 0 };

  // ---- helpers --------------------------------------------------------------
  function profile(ctx) { return (ctx && ctx.econ) ? ctx.econ.loadProfile() : null; }
  function ms(p) {                                   // ensure the p.missions shape inside a write
    if (!p.missions || typeof p.missions !== 'object') p.missions = {};
    var m = p.missions;
    if (!m.active || typeof m.active !== 'object') m.active = null;
    if (!Array.isArray(m.done)) m.done = [];
    if (typeof m.offerIdx !== 'number' || !isFinite(m.offerIdx)) m.offerIdx = 0;
    return m;
  }
  function availableFor(p) {                          // consumables always offered; done milestones drop out
    var m = ms(p);
    return DELIVERIES.filter(function (d) { return !(d.milestone && m.done.indexOf(d.id) >= 0); });
  }
  function currentOffer(p) {
    var av = availableFor(p); if (!av.length) return null;
    var i = ((ms(p).offerIdx | 0) % av.length + av.length) % av.length;
    return av[i];
  }
  function activeJob(p) {
    var m = ms(p); if (!m.active || !m.active.id) return null;
    return DBYID[m.active.id] || null;
  }

  // ---- reward labelling -----------------------------------------------------
  function rewardBit(kind, amt, rar) {
    if (kind === 'gold')      return amt + ' gold';
    if (kind === 'bones')     return amt + ' bones';
    if (kind === 'keys')      return amt + ' key' + (amt === 1 ? '' : 's');
    if (kind === 'fragments') return amt + ' fragments';
    if (kind === 'scrap')     return amt + ' ' + (rar || '') + ' scrap';
    return amt + ' ' + kind;
  }
  function rewardPreview(job) {
    var bits = (job.reward || []).map(function (r) { return rewardBit(r[0], r[1], r[2]); });
    if (job.chest) bits.push('a ' + job.chest + ' chest');
    return bits.join(' + ');
  }

  // ---- actions (all writes are atomic via AK_ECON.mutateProfile) ------------
  function accept(ctx, job) { ctx.econ.mutateProfile(function (p) { ms(p).active = { id: job.id, takenAt: Date.now() }; }); }
  function abandon(ctx)     { ctx.econ.mutateProfile(function (p) { var m = ms(p); m.active = null; m.offerIdx = (m.offerIdx | 0) + 1; }); }
  function switchOffer(ctx) { ctx.econ.mutateProfile(function (p) { var m = ms(p); m.offerIdx = (m.offerIdx | 0) + 1; }); }

  // TURN IN: verify off the live profile, grant FIRST (favor the player if a
  // grant throws), THEN consume the inputs + advance the queue in one write.
  function turnIn(ctx, job) {
    var p = profile(ctx); if (!p) return null;
    if (job.prog(p) < job.target) return null;       // not ready -- never pay
    var summary = rewardPreview(job);
    (job.reward || []).forEach(function (r) { ctx.currency.grant(r[0], r[1], r[2]); }); // gold/scrap/keys/bones -- never gems
    if (job.chest && ctx.econ && ctx.econ.grantChest) { try { ctx.econ.grantChest(job.chest, 1); } catch (_e) {} }
    ctx.econ.mutateProfile(function (pp) {
      if (!job.milestone && typeof job.consume === 'function') job.consume(pp);
      var m = ms(pp);
      if (job.milestone && m.done.indexOf(job.id) < 0) m.done.push(job.id);
      m.active = null; m.offerIdx = (m.offerIdx | 0) + 1;   // surface the NEXT job (Reward Flow)
    });
    return summary;
  }

  // ---- LIVE HIT LIST server bridge (ak-quests edge fn + ak_grants rail) -----
  function sbc() { try { return global.AKAccount && global.AKAccount.client && global.AKAccount.client(); } catch (_) { return null; } }
  function me()  { try { return global.AKAccount && global.AKAccount.user && global.AKAccount.user(); } catch (_) { return null; } }
  function call(fn, body) {                            // mirrors quests.js / social.js call()
    var sb = sbc(); if (!sb) return Promise.resolve({ ok: false, error: 'offline' });
    return sb.functions.invoke(fn, { body: body }).then(function (r) {
      if (r.error) {
        var c = r.error && r.error.context;
        if (c && typeof c.json === 'function') return c.json().then(function (j) { return j || { ok: false, error: r.error.message }; }, function () { return { ok: false, error: r.error.message }; });
        return { ok: false, error: (r.error && r.error.message) || 'error' };
      }
      return r.data || { ok: false, error: 'empty' };
    }, function (e) { return { ok: false, error: String((e && e.message) || e) }; });
  }
  function fetchServer(ctx, cb) {                      // LIVE: ak-quests "get" -> summarize claimable/done
    if (S.fetching) { if (cb) cb(); return; }
    if (!me()) { S.server = null; S.fetched = true; if (cb) cb(); return; }
    S.fetching = true;
    call('ak-quests', { action: 'get' }).then(function (r) {
      S.fetching = false; S.fetched = true;
      if (r && r.ok && r.quests) {
        var claimable = 0, done = 0;
        r.quests.forEach(function (q) { if (q.claimable) claimable++; if (q.claimed) done++; });
        S.server = { quests: r.quests, claimable: claimable, done: done, total: r.quests.length };
      } else S.server = null;
      if (cb) cb();
    }, function () { S.fetching = false; S.fetched = true; S.server = null; if (cb) cb(); });
  }
  function openHitList(ctx) {
    // Prefer the in-page LIVE Hit List overlay (ak-quests + ak_grants) if it is loaded.
    try { if (global.AKQuests && global.AKQuests.open) { global.AKQuests.open(); return; } } catch (_e) {}
    // Fallback: navigate to the canonical Hit List shop surface, preserving the hub
    // zone + spot the exact way the host doEnter() does (return restores position).
    try {
      localStorage.setItem('ak_hub_zone', ctx.zoneId);
      localStorage.setItem('ak_hub_pos', JSON.stringify({ x: Math.round(ctx.me.x), y: Math.round(ctx.me.y) }));
      localStorage.setItem('ak_returning', '1');
    } catch (_e) {}
    if (ctx.showBanner) ctx.showBanner('Opening the Hit List…', 2);
    try { window.location.href = 'shop/shop.html#hit2'; } catch (_e) {}
  }
  function claimAllServer(ctx) {                       // claim every ready server quest in place, then pay grants
    var srv = S.server;
    if (!srv || !srv.quests) { openHitList(ctx); return; }
    var ready = srv.quests.filter(function (q) { return q.claimable; });
    if (!ready.length) { openHitList(ctx); return; }
    var i = 0;
    (function step() {
      if (i >= ready.length) {
        try { if (global.AKSocial && global.AKSocial.claimGrants) global.AKSocial.claimGrants(); } catch (_e) {}
        if (ctx.showBanner) ctx.showBanner('Hit List paid out -- check your stash.', 1.8);
        fetchServer(ctx, function () { if (isOpen()) renderFixer(ctx); });
        return;
      }
      call('ak-quests', { action: 'claim', quest_id: ready[i++].id }).then(step, step);
    })();
  }

  // ---- open-state guard (async re-renders must NOT pop the panel back open) -
  // onTick fires ONLY while the interior is closed (host gate), so it clears
  // S.open; onEnterBuilding sets it true and onTick is frozen during the visit.
  function isOpen() {
    try { var el = document.getElementById('interior'); return S.open && !!el && el.style.display !== 'none'; } catch (_e) { return false; }
  }

  // ---- the keeper interior (re-rendered after every action) -----------------
  function renderFixer(ctx) {
    var p = profile(ctx); if (!p) return;
    var job = activeJob(p);
    var offer = job || currentOffer(p);
    var buttons = [];
    var line;

    if (!job) {
      // No job taken -- the Fixer is offering one.
      line = (offer ? offer.pitch.replace('{t}', offer.target) + '  Pays ' + rewardPreview(offer) + '.' : "Quiet day. Check back, mutt.")
             + "  Bones feed your handlers' skill trees.";
      if (offer) buttons.push({ label: 'TAKE THE JOB', primary: true, onClick: function (c) { accept(c, offer); renderFixer(c); } });
      buttons.push({ label: 'NEXT JOB', primary: false, onClick: function (c) { switchOffer(c); renderFixer(c); } });
    } else {
      var prog = job.prog(p), ready = prog >= job.target;
      if (ready) {
        line = "Job's done. Bring it in -- " + rewardPreview(job) + " on the table.";
        buttons.push({ label: 'TURN IN  ▸  ' + rewardPreview(job), primary: true, onClick: function (c) {
          var sum = turnIn(c, job);
          if (sum && c.showBanner) c.showBanner('Squared up: ' + sum, 2);
          renderFixer(c);   // next offer surfaces immediately (Reward Flow)
        } });
      } else {
        line = job.pitch.replace('{t}', job.target) + '   [' + Math.min(prog, job.target) + '/' + job.target + ' ' + job.res + ']';
        buttons.push({ label: prog + '/' + job.target + ' ' + job.res.toUpperCase(), primary: true, disabled: true, onClick: function () {} });
      }
      buttons.push({ label: 'DROP JOB', primary: false, onClick: function (c) { abandon(c); renderFixer(c); } });
    }

    // Button 3: the LIVE Hit List (server quests). Claim-in-place when ready,
    // else open the full screen. The count is a goal-gradient nudge.
    var srv = S.server, hitLabel, hitOnClick;
    if (!me()) {
      hitLabel = 'THE HIT LIST'; hitOnClick = function (c) { openHitList(c); };
    } else if (srv && srv.claimable > 0) {
      hitLabel = 'CLAIM HIT LIST (' + srv.claimable + ')'; hitOnClick = function (c) { claimAllServer(c); };
    } else if (srv) {
      hitLabel = 'HIT LIST  ' + srv.done + '/' + srv.total; hitOnClick = function (c) { openHitList(c); };
    } else {
      hitLabel = 'THE HIT LIST'; hitOnClick = function (c) { openHitList(c); };
    }
    buttons.push({ label: hitLabel, primary: false, onClick: hitOnClick });

    ctx.ui.keeperCard({ place: 'THE FIXER', glyph: KEEPER.glyph, name: KEEPER.name, line: line, buttons: buttons });
  }

  // ---- the AK_SYSTEMS module ------------------------------------------------
  global.AK_SYSTEMS.register({
    id: 'missions',

    init: function (ctx) {
      // No per-frame work. Pre-roll the readiness flag from local state so the
      // FIXER pip can light up on the first frame for a returning player.
      try {
        var p = profile(ctx); var job = activeJob(p);
        S.ready = !!(job && job.prog(p) >= job.target);
      } catch (_e) { S.ready = false; }
    },

    onEnterBuilding: function (b, ctx) {
      if (!b || b.id !== BID) return false;            // own ONLY the FIXER (Section 4)
      S.open = true;
      renderFixer(ctx);                                // synchronous: panel is ready before we return true
      fetchServer(ctx, function () { if (isOpen()) renderFixer(ctx); }); // live Hit List fills in async
      return true;                                     // host shows the panel + suppresses the default keeper
    },

    onTick: function (dt, ctx) {
      S.open = false;                                  // interior is closed whenever onTick runs (host gate)
      S._acc += dt;
      if (S._acc >= 1.0) {
        S._acc = 0;
        S._now = (global.performance && performance.now) ? performance.now() : Date.now();
        try {
          if (!S.fetched && !S.fetching && me()) fetchServer(ctx);   // one lazy fetch so the pip reflects server quests
          var p = profile(ctx); var job = activeJob(p);
          S.ready = (!!(job && job.prog(p) >= job.target)) || (!!(S.server && S.server.claimable > 0));
        } catch (_e) { S.ready = false; }
      }
    },

    // a "job ready" pip over THE FIXER (THE_YARDS) when a turn-in or a Hit List
    // claim is waiting -- the Monopoly-GO goal-gradient pull back to the keeper.
    onDrawWorld: function (ctx) {
      if (!S.ready) return;
      if (!ctx.activeZone || ctx.activeZone.id !== 'THE_YARDS') return;
      var bs = ctx.activeZone.buildings; if (!bs) return;
      var b = null, i;
      for (i = 0; i < bs.length; i++) { if (bs[i].id === BID) { b = bs[i]; break; } }
      if (!b) return;
      var g = ctx.world.g, W = ctx.world.W, H = ctx.world.H;
      var X = ctx.world.wx(b.x), Y = ctx.world.wy(b.y - (b.h ? b.h / 2 : 48) - 22);
      if (X < -40 || X > W + 40 || Y < -40 || Y > H + 40) return;
      var now = S._now || ((global.performance && performance.now) ? performance.now() : Date.now());
      var pulse = 0.55 + 0.45 * Math.sin(now / 300);
      g.save();
      g.globalAlpha = pulse; g.shadowColor = PIP_COLOR; g.shadowBlur = 14; g.fillStyle = PIP_COLOR;
      g.beginPath(); g.arc(X, Y, 9, 0, 7); g.fill();
      g.shadowBlur = 0; g.globalAlpha = 1;
      g.font = 'bold 13px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#15110a';
      g.fillText('!', X, Y + 0.5);
      g.restore();
    }
  });
})(typeof window !== 'undefined' ? window : globalThis);
