/* ==========================================================================
   ALLEY KINGZ -- LIVING POPULATION (Wave 3 rebuild)
   Self-mounting vanilla-JS AK_SYSTEMS module. Makes the streets feel ALIVE.
   ----------------------------------------------------------------------------
   THREE jobs, in priority order:
     (1) ROSTER  -- a DETERMINISTIC pack of AI dogs (~6 per clan + a few strays),
                    each with a street name, a real card avatar (akCardArtRel),
                    a home district + a trophy count. Fixed seed => SAME dogs
                    every session, so the world has memory.
     (2) STREET TALK -- a self-mounted, toggleable chat overlay (mirrors the
                    social.js injectCss + panel pattern) that streams throttled,
                    deeply-templated procedural banter: rival-clan trash-talk,
                    your-pack crew chat (calls YOU by name), and context lines
                    (district / time / season / the Crown Bloodline lore). This
                    is the priority "alive" signal -- the feed never repeats.
     (3) ROAMERS -- a CAPPED few AI dogs that physically walk their home
                    district (host roamer bus: ctx.world.addRoamer). They greet
                    on proximity, friendly if they fly your colors, rival if not.
   ----------------------------------------------------------------------------
   HARD LAWS honored (AK_ROADMAP_V2_NAMED.md section 0 NAME CANON):
     Clans: Zoomie Syndicate / Leashbreak Tactix / Boneguard Crew / K9 Circuitry,
            neutral = Stray. Ranks: Stray -> Pup -> Runner -> Warrior -> Enforcer
            -> Right Paw -> King of the Block. Story: THE CROWN BLOODLINE, the
            Old Pack, the Mongrel King "the Dog That Eats Names". Districts: OUR 9
            (The Lot/Downtown/The Strip/Neon Heights/The Overlook/The Yards/
            Factory Row/The Docks/The Undercity). Systems: the Fence, the Watch.
     No Kimi generics. No new canon names. No em-dashes (use --). Gritty gangland.
   PERF: lazy DOM, capped entities (<=3 roamers), timer-pumped feed (NOT per-frame),
         onTick does only light bookkeeping -- keeps 60fps on a cheap Android.
   STATE: stateless against AK_ECON.profile (roster is seed-derived, chatter is
          ephemeral) so a zero-state profile stays byte-identical. AK_ECON is
          read-only here (loadProfile) and only via AK_ECON.mutateProfile if ever
          written, falsy-default. XSS-safe: every dynamic value via textContent.
   Load AFTER canon.js (akCardArtRel + CANON_CARDS) and the systems registry.
   ========================================================================== */
(function (global) {
  "use strict";

  // ====================== CANON (HARD -- do not rename) =====================
  var CLANS = [
    { id: "zoomie_syndicate",  name: "Zoomie Syndicate",  tag: "ZOOM",  color: "#FF2E88", epithet: "the Unbound",    home: "THE_STRIP" },
    { id: "leashbreak_tactix", name: "Leashbreak Tactix", tag: "PHNTM", color: "#7B5CFF", epithet: "the Hologhosts", home: "NEON_HEIGHTS" },
    { id: "boneguard_crew",    name: "Boneguard Crew",    tag: "BONE",  color: "#C9772E", epithet: "the Rusted",     home: "FACTORY_ROW" },
    { id: "k9_circuitry",      name: "K9 Circuitry",      tag: "VOLT",  color: "#00E0C0", epithet: "the Crowned",    home: "THE_DOCKS" },
  ];
  var STRAY = { id: "stray", name: "Stray", tag: "STRAY", color: "#c9a84c", epithet: "no colors", home: "THE_YARDS" };
  var CLAN_BY_ID = {}; CLANS.forEach(function (c) { CLAN_BY_ID[c.id] = c; }); CLAN_BY_ID.stray = STRAY;

  // canon rank ladder + the karma division floors that back each rank
  var RANKS = ["Stray", "Pup", "Runner", "Warrior", "Enforcer", "Right Paw", "King of the Block"];
  var RANK_FLOOR = [0, 200, 500, 1000, 1800, 3000, 5000];

  // OUR 9 districts -> display label (matches ZONES name in index.html)
  var DISTRICT = {
    HOME_TURF: "The Lot", DOWNTOWN: "Downtown", THE_STRIP: "The Strip",
    NEON_HEIGHTS: "Neon Heights", THE_OVERLOOK: "The Overlook", THE_YARDS: "The Yards",
    FACTORY_ROW: "Factory Row", THE_DOCKS: "The Docks", THE_UNDERCITY: "The Undercity"
  };
  var STRAY_TURF = ["THE_YARDS", "DOWNTOWN", "HOME_TURF"];

  // gritty street-dog first names -- our own flavor, never Kimi roles/ranks
  var NAMES = [
    "Rax", "Cinder", "Dozer", "Switch", "Maw", "Rivet", "Tilt", "Grime", "Husk",
    "Cleat", "Sarge", "Vex", "Knuckles", "Diesel", "Scrap", "Brick", "Fang", "Cobble",
    "Nyx", "Ratchet", "Smoke", "Wire", "Gnash", "Tar", "Hollow", "Crank", "Rebar",
    "Slug", "Patch", "Choke", "Vandal", "Static", "Dent", "Marrow", "Gristle", "Scab",
    "Howl", "Wretch", "Bane", "Creed", "Mange", "Ruckus", "Sully", "Ash", "Mutt"
  ];

  // ============================ DETERMINISTIC RNG ===========================
  // mulberry32 over a FIXED seed -> identical roster forever (world memory).
  function mulberry32(a) {
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  var SEED = 0x4B17C0DE; // "K9 code" -- stable

  // ============================ ROSTER ======================================
  // Per-clan rank spread: one King of the Block holds the block, then the chain
  // down. Strays sit at the bottom (no colors). Built ONCE; art resolved lazily.
  var CLAN_RANKS = [6, 5, 4, 3, 2, 1]; // King, Right Paw, Enforcer, Warrior, Runner, Pup
  var _roster = null;

  function troopCards() {
    var out = [], L = global.CANON_CARDS || [];
    for (var i = 0; i < L.length; i++) {
      var c = L[i];
      if (!c || c.isMythic) continue;
      if (c.type === "spell" || c.isSpell) continue;
      out.push(c);
    }
    return out;
  }
  function dogCard(dog) { var L = troopCards(); return L.length ? L[dog.av % L.length] : null; }
  function dogArtRel(dog) { try { var c = dogCard(dog); return (c && global.akCardArtRel) ? global.akCardArtRel(c) : ""; } catch (_) { return ""; } }

  function buildRoster() {
    if (_roster) return _roster;
    var rng = mulberry32(SEED), used = {}, list = [];
    function pickName() {
      // seeded draw without replacement so names never collide
      for (var guard = 0; guard < 200; guard++) {
        var i = (rng() * NAMES.length) | 0;
        if (!used[i]) { used[i] = 1; return NAMES[i]; }
      }
      return NAMES[(rng() * NAMES.length) | 0];
    }
    function mkDog(clan, rankIdx) {
      var floor = RANK_FLOOR[rankIdx];
      var span = (RANK_FLOOR[rankIdx + 1] || floor + 600) - floor;
      return {
        id: clan.id + "_" + list.length,
        name: pickName(),
        clan: clan.id,
        clanName: clan.name,
        color: clan.color,
        rankIdx: rankIdx,
        rank: RANKS[rankIdx],
        trophies: floor + ((rng() * Math.max(120, span * 0.7)) | 0),
        district: clan.home,
        av: (rng() * 1e9) | 0 // stable avatar-card index (mod len at resolve time)
      };
    }
    CLANS.forEach(function (clan) {
      for (var i = 0; i < CLAN_RANKS.length; i++) list.push(mkDog(clan, CLAN_RANKS[i]));
    });
    // a few strays, no colors, scattered across neutral turf
    for (var s = 0; s < 5; s++) {
      var d = mkDog(STRAY, s < 2 ? 1 : 0); // Pup / Stray
      d.district = STRAY_TURF[s % STRAY_TURF.length];
      list.push(d);
    }
    _roster = list;
    return list;
  }

  function rosterPublic() {
    return buildRoster().map(function (d) {
      var c = dogCard(d);
      return {
        id: d.id, name: d.name, clan: d.clan, clanName: d.clanName, color: d.color,
        rank: d.rank, trophies: d.trophies, district: d.district,
        districtName: DISTRICT[d.district] || d.district,
        avatar: dogArtRel(d), avatarCard: (c && c.name) || null
      };
    });
  }
  function leaderboard() {
    var rows = rosterPublic();
    // splice in the player at their real trophy count, marked isYou
    var nm = myName(), pc = playerClanId(), pcRow = pc ? CLAN_BY_ID[pc] : null;
    rows.push({
      id: "_you", name: nm, clan: pc || "stray",
      clanName: (pcRow && pcRow.name) || "Stray", color: (pcRow && pcRow.color) || STRAY.color,
      rank: rankForTrophies(myTrophies()), trophies: myTrophies(),
      district: "HOME_TURF", districtName: DISTRICT.HOME_TURF, avatar: "", avatarCard: null, isYou: true
    });
    rows.sort(function (a, b) { return b.trophies - a.trophies; });
    rows.forEach(function (r, i) { r.place = i + 1; });
    return rows;
  }
  function rankForTrophies(t) {
    t = t | 0; var r = 0;
    for (var i = 0; i < RANK_FLOOR.length; i++) if (t >= RANK_FLOOR[i]) r = i;
    return RANKS[r];
  }

  // ============================ PLAYER READS (read-only) ====================
  function econ() { try { return global.AK_ECON || null; } catch (_) { return null; } }
  function myName() { try { return (localStorage.getItem("ak_name") || "Stray").slice(0, 24) || "Stray"; } catch (_) { return "Stray"; } }
  function myTrophies() { try { var e = econ(), p = e && e.loadProfile && e.loadProfile(); return (p && p.trophies | 0) || 0; } catch (_) { return 0; } }
  function playerClanId() {
    try { var c = localStorage.getItem("ak_clan"); if (c && CLAN_BY_ID[c]) return c; } catch (_) {}
    try { var e = econ(), p = e && e.loadProfile && e.loadProfile(); var f = p && (p.clan || p.faction); if (f && CLAN_BY_ID[f]) return f; } catch (_) {}
    return null; // a Stray with no colors (canon-correct starting state)
  }
  function packMates() {
    var roster = buildRoster(), pc = playerClanId();
    var pack = roster.filter(function (d) { return pc ? d.clan === pc : d.clan === "stray"; });
    return pack.length ? pack : roster.filter(function (d) { return d.clan === "stray"; });
  }
  function clanDogs(id) { return buildRoster().filter(function (d) { return d.clan === id; }); }

  // ============================ PROCEDURAL STREET TALK ======================
  // Deep templated banter. pick() over big fragment banks => effectively
  // non-repeating. Categories: trash (rival clan), crew (your pack -> you), ctx.
  function pick(a) { return a[(Math.random() * a.length) | 0]; }
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
  function timeWord() {
    var h = new Date().getHours();
    if (h < 5) return "dead of night"; if (h < 11) return "morning grind";
    if (h < 17) return "afternoon heat"; if (h < 21) return "after dark"; return "late night";
  }
  function seasonWord() {
    try {
      var s = global.AKSeasons || global.AK_SEASONS;
      if (s) { var n = (s.currentName && s.currentName()) || (s.current && s.current()) || s.name; if (n) return String(n); }
    } catch (_) {}
    return null;
  }
  function anyDistrict() { var k = Object.keys(DISTRICT); return DISTRICT[k[(Math.random() * k.length) | 0]]; }

  // ---- fragment banks ----
  var WEATHER = ["rain on the neon", "fog off the docks", "heat off the asphalt", "wind kicking trash down the block", "sirens two streets over", "power flickering on the strip"];
  var TRASH = [
    "{A} run {dist}? Cute. {B} been pissing on them walls since the Old Pack died.",
    "Tell {dogB} the {Aname} hold these blocks now. Bark all you want, mutt.",
    "{Aname} don't bark. We bite. Ask {dist}.",
    "{B} flew their colors on {dist}. We tore em down by {time}.",
    "Word to {dogB}: stay off {dist} or lose a paw.",
    "{Aname}, {epA}. {B}? {epB}, and rusting.",
    "Saw {dogB} run from the Watch. {B} ain't built for this block.",
    "{B} talk crown like they ever wore one. {Aname} eats names, not stories.",
    "{dogA} put two of {B} down on {dist}. Collar tight, colors tighter.",
    "Heard {B} laundered scrap through the Fence again. Broke AND soft.",
    "{Aname} owns the night on {dist}. {B} owns the gutter.",
    "Step on {dist} flying {B} colors, you walk home on three legs.",
    "{dogB}, that crown's a cage and you ain't even king of the dumpster.",
    "{B} reinforced their turf? We reinforce graves, dog.",
    "{Aname} took {dist} clean. {B} cried to the catchers about it."
  ];
  var CREW = [
    "{you}. {mate} here. We rolling on {dist} or we waiting on the Watch?",
    "Yo {you}, the Fence shorted us again. {mate} says we hit back tonight.",
    "{you}, keep your collar tight -- catchers been thick since {time}.",
    "{mate} got eyes on {dist}. Say the word, {you}, and we move.",
    "{you}, you carried that last run. {mate} owes you a bone.",
    "Pack's hungry, {you}. {mate} says {dist} is soft right now.",
    "{you}! {mate}. They tagged our wall on {dist}. We answering or what?",
    "{mate} here -- {you}, the crown ain't given, it's took. Old Pack said so.",
    "{you}, watch the alleys. {mate} smelled rivals near {dist} at {time}.",
    "Run with us, {you}. {mate} ain't lost a block yet.",
    "{you}, the Watch is asleep. {mate} says we stack trophies while they snore.",
    "Stay sharp, {you}. {mate} swears the Mongrel King's pack is sniffing {dist}.",
    "{mate} to {you}: feed the crew first, ego second. That's how we hold the block.",
    "{you}, you flying our colors today or you a Stray again? {mate} just asking."
  ];
  var CTX = [
    "{time} on {dist}. {weather}. Stay sharp.",
    "Old Pack story goes the crown ain't given. It's took, in blood, on these blocks.",
    "The Mongrel King put another name on the board. {dist} went quiet.",
    "They call him the Dog That Eats Names. Pups laugh til they meet him.",
    "Word on the block: the catchers rolled deep through {dist} at {time}.",
    "The Fence is buying scrap cheap tonight. The Watch ain't looking. {dist}'s wide open.",
    "Crown Bloodline runs through every dog that ever held {dist}. Most of em dead.",
    "Quiet on {dist}. Too quiet. {weather}.",
    "Somebody lost their colors on {dist} tonight. Nobody's saying who.",
    "The pound's wagon was parked off {dist}. {weather}. Keep moving.",
    "Old Pack whispers the climb itself is the cage. The Mongrel King built it.",
    "{dist} smells like rust and copper. The block remembers everything."
  ];
  var SEASON = [
    "Season's turning -- {season} on the block. New colors, same gutter.",
    "{season} hit {dist}. The strong eat first, the strays eat last.",
    "They say {season} crowns a new King of the Block. We'll see who's still breathing."
  ];
  var GREET_FRIEND = [
    "{name}: ay, that's our colors. Run with the pack, {you}.",
    "{name}: {you}! Block's ours tonight. Keep your head up.",
    "{name}: good to see a face that flies {clan}. Stay sharp out here.",
    "{name}: {you}, the Watch is loose on {dist}. We got your back."
  ];
  var GREET_RIVAL = [
    "{name}: you ain't flying our colors. This is {clan} turf, Stray.",
    "{name}: {dist} belongs to {clan}. Walk soft or don't walk.",
    "{name}: lost, dog? This block bites strangers.",
    "{name}: keep it moving. {clan} don't share {dist}."
  ];

  // ============================ STORY BARK MIX (Block Chronicles) ==========
  // AK-STORIES sidecar (data/cards_stories.js) is OPTIONAL and population.js
  // never loads it -- read window.AK_STORIES fresh at call time only, fully
  // typeof-guarded. When the SPEAKING dog's assigned avatar card (dogCard ->
  // cardNumber) has a flagship entry, ~30% of the time swap the generic
  // templated line for one of that dog's own ambientBarks.streetTalk lines.
  // Absent AK_STORIES / no card match / the other 70% => null => caller keeps
  // its normal templated body (today's exact behavior).
  function storyBark(dog) {
    try {
      var stories = global.AK_STORIES;
      if (!dog || typeof stories !== "object" || !stories) return null;
      var card = dogCard(dog);
      var num = card && card.cardNumber;
      var story = num && stories[num];
      var lines = story && story.ambientBarks && story.ambientBarks.streetTalk;
      if (!lines || !lines.length) return null;
      if (Math.random() >= 0.30) return null; // ~30% mix chance
      return pick(lines);
    } catch (_) { return null; }
  }
  function fillTrash() {
    var two = pickTwoClans(), A = two[0], B = two[1];
    var dogA = pick(clanDogs(A.id)), dogB = pick(clanDogs(B.id));
    var body = pick(TRASH)
      .replace(/{Aname}/g, A.name).replace(/{A}/g, A.name)
      .replace(/{B}/g, B.name)
      .replace(/{epA}/g, A.epithet).replace(/{epB}/g, B.epithet)
      .replace(/{dogA}/g, dogA ? dogA.name : "our enforcer")
      .replace(/{dogB}/g, dogB ? dogB.name : "their pup")
      .replace(/{dist}/g, anyDistrict()).replace(/{time}/g, timeWord());
    var bark = storyBark(dogA);
    return { name: dogA ? dogA.name : A.tag, clan: A.id, clanName: A.name, color: A.color, body: bark || cap(body), cat: "trash" };
  }
  function fillCrew() {
    var pack = packMates(), me2 = myName();
    var mate = pick(pack) || { name: "the crew", clan: "stray", clanName: "Stray", color: STRAY.color };
    var body = pick(CREW)
      .replace(/{you}/g, me2).replace(/{mate}/g, mate.name)
      .replace(/{dist}/g, anyDistrict()).replace(/{time}/g, timeWord());
    var bark = storyBark(mate);
    return { name: mate.name, clan: mate.clan, clanName: mate.clanName, color: mate.color, body: bark || cap(body), cat: "crew" };
  }
  function fillCtx() {
    var sw = seasonWord();
    var bank = (sw && Math.random() < 0.35) ? SEASON : CTX;
    var speaker = pick(buildRoster());
    var body = pick(bank)
      .replace(/{dist}/g, anyDistrict()).replace(/{time}/g, timeWord())
      .replace(/{weather}/g, cap(pick(WEATHER))).replace(/{season}/g, sw || "the cold season");
    var bark = storyBark(speaker);
    return { name: speaker.name, clan: speaker.clan, clanName: speaker.clanName, color: speaker.color, body: bark || cap(body), cat: "ctx" };
  }
  function pickTwoClans() {
    var a = (Math.random() * CLANS.length) | 0, b = (Math.random() * CLANS.length) | 0;
    if (b === a) b = (b + 1) % CLANS.length;
    return [CLANS[a], CLANS[b]];
  }
  function nextLine() {
    var r = Math.random();
    if (r < 0.45) return fillTrash();
    if (r < 0.80) return fillCrew();
    return fillCtx();
  }
  function greetLine(roamer) {
    var friend = roamer.clan.id === playerClanId();
    var t = pick(friend ? GREET_FRIEND : GREET_RIVAL);
    return t.replace(/{name}/g, roamer.dog.name).replace(/{you}/g, myName())
      .replace(/{clan}/g, roamer.clan.name).replace(/{dist}/g, DISTRICT[roamer.zone] || "this block");
  }

  // ============================ TIME ANCHOR (LOCAL PT) ======================
  // Every daily roll happens on PACIFIC midnight so the whole pack shares ONE
  // "today" -- world memory + parity, never the device clock. Deterministic.
  function ptCal() {
    try {
      var f = new Intl.DateTimeFormat("en-US", {
        timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit",
        day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false
      }), o = {};
      f.formatToParts(new Date()).forEach(function (p) { if (p.type !== "literal") o[p.type] = p.value; });
      var h = +o.hour; if (h === 24) h = 0; // some engines emit "24" at midnight
      return { y: +o.year, m: +o.month, d: +o.day, h: h, min: +o.minute, s: +o.second };
    } catch (_) {
      var n = new Date();
      return { y: n.getFullYear(), m: n.getMonth() + 1, d: n.getDate(), h: n.getHours(), min: n.getMinutes(), s: n.getSeconds() };
    }
  }
  // integer that ticks up by 1 each PT calendar day (stable for "days since" math)
  function ptDayIndex() { var c = ptCal(); return Math.floor(Date.UTC(c.y, c.m - 1, c.d) / 86400000); }
  function dayKey() { var c = ptCal(); return c.y + "-" + (c.m < 10 ? "0" : "") + c.m + "-" + (c.d < 10 ? "0" : "") + c.d; }
  function msToTomorrowPT() {
    var c = ptCal(); // wall-clock ms left in the PT day (no offset math needed)
    var sec = (23 - c.h) * 3600 + (59 - c.min) * 60 + (60 - c.s);
    return Math.max(0, sec) * 1000;
  }
  // per-day deterministic RNG: SAME hit + SAME overnight story for the whole pack
  function dayRng(salt) {
    var di = ptDayIndex();
    var s = (SEED ^ Math.imul(di, 2654435761) ^ Math.imul((salt | 0) + 1, 40503)) >>> 0;
    return mulberry32(s);
  }
  function pick2(rng, a) { return a[(rng() * a.length) | 0]; }

  // population's OWN bookkeeping lives in a SEPARATE key so ak_profile stays
  // byte-identical at zero-state. The ONLY profile write is the bones reward,
  // and only when the player genuinely drops the hit (see beatHitOfDay).
  var POP_KEY = "ak_pop";
  function popState() {
    try { var raw = localStorage.getItem(POP_KEY); if (raw) { var o = JSON.parse(raw); if (o && typeof o === "object") return o; } } catch (_) {}
    return {};
  }
  function popSave(o) { try { localStorage.setItem(POP_KEY, JSON.stringify(o || {})); } catch (_) {} }

  var DISTRICT_KEYS = Object.keys(DISTRICT);

  // ============================ HIT OF THE DAY ==============================
  // A named roster dog (Warrior+) surfaces in one district for 24h. Drop it
  // before the PT day rolls for BONUS BONES (soft currency -- parity-safe,
  // never gems, never raw power). Deterministic per PT day = world memory.
  var _hitCache = null;
  function computeHit() {
    var key = dayKey();
    if (_hitCache && _hitCache.day === key) return _hitCache;
    var rng = dayRng(7), roster = buildRoster();
    var pool = roster.filter(function (d) { return d.clan !== "stray" && d.rankIdx >= 3; }); // Warrior+
    if (!pool.length) pool = roster;
    var dog = pool[(rng() * pool.length) | 0] || roster[0];
    var dk = DISTRICT_KEYS[(rng() * DISTRICT_KEYS.length) | 0];
    var clan = CLAN_BY_ID[dog.clan] || STRAY;
    var bones = 60 + dog.rankIdx * 25 + (((rng() * 5) | 0) * 5); // ~135..230, deterministic
    _hitCache = {
      day: key, dogId: dog.id, name: dog.name, clan: dog.clan, clanName: clan.name,
      color: clan.color, rank: dog.rank, rankIdx: dog.rankIdx,
      district: dk, districtName: DISTRICT[dk] || dk, bones: bones,
      avatar: dogArtRel(dog), avatarCard: (dogCard(dog) || {}).name || null
    };
    return _hitCache;
  }
  function hitClaimedToday() { return popState().hitDay === dayKey(); }
  function isHitTarget(id) { return !!id && computeHit().dogId === id; }
  function hitOfDay() {
    var h = computeHit();
    return {
      dogId: h.dogId, name: h.name, clan: h.clan, clanName: h.clanName, color: h.color,
      rank: h.rank, district: h.district, districtName: h.districtName, bones: h.bones,
      avatar: h.avatar, avatarCard: h.avatarCard, claimed: hitClaimedToday(),
      resetsInMs: msToTomorrowPT(), day: h.day
    };
  }
  // the integration/combat pass calls this when the player beats the hit dog.
  // Idempotent per PT day; pays bones ONCE via the doctrine mutateProfile path.
  function beatHitOfDay(dogId) {
    var h = computeHit();
    if (dogId && dogId !== h.dogId) return { ok: false, reason: "not-the-hit", bones: 0 };
    if (hitClaimedToday()) return { ok: false, reason: "already-claimed", bones: 0 };
    var e = econ(), granted = 0;
    if (e && e.mutateProfile) {
      try { e.mutateProfile(function (p) { p.bones = (p.bones | 0) + h.bones; }); granted = h.bones; } catch (_) {}
    }
    var st = popState(); st.hitDay = h.day; popSave(st);
    emitEvent("hit_down", "HIT DOWN -- " + myName() + " put " + h.name + " of " + h.clanName +
      " in the dirt on " + h.districtName + ". +" + h.bones + " bones on the body.",
      { district: h.district, clan: h.clan, clanName: h.clanName, color: h.color, name: myName() });
    return { ok: true, bones: granted, name: h.name, clanName: h.clanName };
  }

  // ============================ OFFLINE CHAOS (overnight) ===================
  // On load, deterministically resolve what moved on the block "overnight" --
  // a turf flip, a rival who rose, a deal at the Fence -- and post it to the
  // feed. The Rust curiosity gap: the block changed while you slept. Seeded by
  // the PT day so the whole pack reads the SAME word the morning after.
  var CHAOS_FLIP = [
    "{A} flipped {dist} while you were off the block. {B}'s pups scattered before dawn.",
    "{dist} changed colors overnight -- {A} runs it now, {B} runs from it.",
    "Word came in slow: {A} took {dist} off {B} in the dead of night.",
    "{B} held {dist} a week. {A} took it in a night. The block remembers everything."
  ];
  var CHAOS_RISE = [
    "{dog} climbed to {rank} overnight. {A} got a new {rank} -- watch that one.",
    "{dog} of {A} earned colors while you slept. A {rank} now, and hungry.",
    "They say {dog} put down two to make {rank}. {A} is rising."
  ];
  var CHAOS_DEAL = [
    "A deal went down at the Fence -- {A} moved scrap quiet while the Watch slept on {dist}.",
    "The Fence ran hot overnight. {A} came out heavy, {B} came out short.",
    "Somebody paid the Fence in blood on {dist} last night. Nobody's naming names."
  ];
  var CHAOS_KING = [
    "The Mongrel King put another name on the board overnight. {dist} went silent.",
    "The Dog That Eats Names walked {dist} after midnight. Two crews didn't open their doors.",
    "Crown Bloodline talk ran all night on {dist}. The Old Pack's ghost still owns these blocks."
  ];
  function buildChaos() {
    var rng = dayRng(13), out = [], nC = CLANS.length;
    function twoClans() {
      var a = (rng() * nC) | 0, b = (rng() * nC) | 0; if (b === a) b = (b + 1) % nC;
      return [CLANS[a], CLANS[b]];
    }
    function topDog(id) { var d = clanDogs(id); return d.length ? d[(rng() * d.length) | 0] : null; }
    function dk() { return DISTRICT_KEYS[(rng() * DISTRICT_KEYS.length) | 0]; }
    (function () { // 1) a turf flip
      var t = twoClans(), A = t[0], B = t[1], k = dk(), dg = topDog(A.id);
      out.push({ kind: "flip", color: A.color, clan: A.id, clanName: A.name, name: dg ? dg.name : A.tag, district: k,
        body: pick2(rng, CHAOS_FLIP).replace(/{A}/g, A.name).replace(/{B}/g, B.name).replace(/{dist}/g, DISTRICT[k] || k) });
    })();
    (function () { // 2) a rival rose
      var A = CLANS[(rng() * nC) | 0], dg = topDog(A.id),
          rank = RANKS[Math.min(RANKS.length - 1, 2 + ((rng() * 4) | 0))];
      out.push({ kind: "rise", color: A.color, clan: A.id, clanName: A.name, name: dg ? dg.name : A.tag,
        body: pick2(rng, CHAOS_RISE).replace(/{A}/g, A.name).replace(/{dog}/g, dg ? dg.name : "a Pup").replace(/{rank}/g, rank) });
    })();
    (function () { // 3) a deal went down / a Bloodline whisper
      var t = twoClans(), A = t[0], B = t[1], k = dk(), dg = topDog(A.id),
          bank = (rng() < 0.5) ? CHAOS_DEAL : CHAOS_KING;
      out.push({ kind: "deal", color: A.color, clan: A.id, clanName: A.name, name: dg ? dg.name : A.tag, district: k,
        body: pick2(rng, bank).replace(/{A}/g, A.name).replace(/{B}/g, B.name).replace(/{dist}/g, DISTRICT[k] || k) });
    })();
    return out;
  }
  var _overnightDone = false, _chaosCache = null;
  function resolveOvernight() {
    if (_overnightDone) return _chaosCache || [];
    _overnightDone = true;
    var st = popState(), today = ptDayIndex(), last = st.seenDay | 0, fresh = !last || last < today;
    st.seenDay = today; popSave(st);
    var items = buildChaos();
    if (fresh) emitEvent("dawn", "While you were off the block, the streets kept moving. Word came in:",
      { name: "The Block", clanName: "Street Talk", color: "#e8c55a" });
    items.forEach(function (it) { emitEvent("chaos:" + it.kind, it.body, it); });
    try {
      var h = computeHit();
      if (!hitClaimedToday())
        emitEvent("hit", "HIT OF THE DAY -- " + h.name + " (" + h.rank + ", " + h.clanName + ") is holding " +
          h.districtName + ". Drop em before the day rolls. +" + h.bones + " bones on the body.",
          { district: h.district, clan: h.clan, clanName: h.clanName, color: h.color, name: h.name });
    } catch (_) {}
    _chaosCache = items;
    return items;
  }

  // ============================ LIVE EVENT FEED =============================
  // A capped, high-signal stream of WORLD events (chaos, hits, live street
  // moves). emitEvent funnels every event into BOTH the event log (for a HUD
  // ticker via AK_POPULATION.eventFeed) AND the Street Talk overlay as a
  // gold-banded bubble. Cadence is wall-clock throttled (NOT per-frame work).
  var _eventLog = [], EVENT_CAP = 40, _evLast = 0, EVENT_EVERY_MS = 26000;
  function emitEvent(kind, body, meta) {
    meta = meta || {};
    var ev = {
      id: (_eventLog.length ? _eventLog[_eventLog.length - 1].id + 1 : 1), ts: Date.now(),
      kind: kind, body: body, district: meta.district || null,
      clan: meta.clan || null, clanName: meta.clanName || null, color: meta.color || "#e8c55a", name: meta.name || null
    };
    _eventLog.push(ev);
    if (_eventLog.length > EVENT_CAP) _eventLog.shift();
    try {
      pushMsg({ name: meta.name || "The Block", clan: meta.clan || "stray",
        clanName: meta.clanName || "Street Talk", color: ev.color, body: body, cat: "event", kind: kind }, true);
    } catch (_) {}
    return ev;
  }
  function eventFeed(n) {
    var a = _eventLog.slice(); if (n && n > 0) a = a.slice(-n);
    return a.map(function (e) {
      return { id: e.id, ts: e.ts, kind: e.kind, body: e.body, district: e.district, clan: e.clan, clanName: e.clanName, color: e.color, name: e.name };
    });
  }
  var EV_AMBIENT = [
    "{A} and {B} squared up on {dist}. The Watch is pretending not to see it.",
    "Catchers rolled three deep through {dist}. {A} went to ground.",
    "{dog} of {A} just claimed a corner on {dist}. {B} won't wear that.",
    "Scrap jumped at the Fence. {A} is buying, {B} is selling cheap.",
    "Somebody tagged the Crown Bloodline sigil on {dist} again. {A} swears it wasn't them.",
    "{A} ran a raid on {dist} and pulled back heavy. {B} is licking wounds.",
    "A Stray turned colors tonight -- {A} just got bigger on {dist}.",
    "The Mongrel King's name went up on a wall on {dist}. Pups are spooked.",
    "{dog} stood a Watch shift on {dist} and dared anybody to test it.",
    "{B} tried {dist} after dark. {A} sent em home on three legs."
  ];
  function liveEventLine() {
    var two = pickTwoClans(), A = two[0], B = two[1];
    var dogs = clanDogs(A.id), dog = dogs.length ? pick(dogs) : null;
    var body = pick(EV_AMBIENT).replace(/{A}/g, A.name).replace(/{B}/g, B.name)
      .replace(/{dog}/g, dog ? dog.name : "a Runner").replace(/{dist}/g, anyDistrict());
    return { kind: "street", body: body, meta: { clan: A.id, clanName: A.name, color: A.color, name: dog ? dog.name : A.tag } };
  }
  // wall-clock throttled -- safe to call every frame from onTick (one Date.now()
  // + compare). Emits one live event every EVENT_EVERY_MS, overlay open or not.
  function tickEvents() {
    var now = Date.now();
    if (!_evLast) { _evLast = now; return; }
    if (now - _evLast < EVENT_EVERY_MS) return;
    _evLast = now;
    try { var L = liveEventLine(); emitEvent(L.kind, L.body, L.meta); } catch (_) {}
  }

  // ============================ BOT MARKETPLACE LISTINGS ====================
  // Deterministic per-hour batch: each bot may post at the Fence for one full
  // PT hour. Keyed to (botIndex x hourBucket) via a fresh mulberry32 seed so
  // the board rotates each hour without touching any save state. No Math.random
  // on persisted state. AK_POPULATION.marketListings(nowMs?) returns the live
  // batch for the marketplace to display and let the player buy from directly.
  var BOT_GIVE_KINDS  = ["wood", "stone", "metal", "scrap", "produce"];
  var BOT_WANT_KINDS  = ["gold", "wood", "stone", "metal", "produce"]; // bots never demand scrap as payment
  var BOT_SCRAP_RAR   = ["Common", "Rare"];
  // amount per kind per rankIdx (Stray=0 .. King of the Block=6 -- idx capped to 5)
  var BOT_AMT = {
    gold:    [30,  60,  120, 250, 500, 1000],
    produce: [8,   15,  30,  60,  100, 200],
    wood:    [8,   15,  30,  60,  100, 200],
    stone:   [8,   15,  25,  50,  80,  150],
    metal:   [3,   6,   12,  25,  50,  100],
    scrap:   [3,   6,   10,  20,  35,  60]
  };
  var BOT_ACTIVE_FRAC = 0.42; // ~12 of 29 bots have an active listing per hour
  var _botListCache   = null; // { bucket, listings } -- rebuilt on hour rollover

  function hourBucket(ms) { return Math.floor((ms || Date.now()) / 3600000); }
  function botRng(botIdx, bucket) {
    // each (botIdx, bucket) pair gets its OWN fresh mulberry32 stream
    var s = (SEED ^ Math.imul((botIdx | 0) + 1, 0x9E3779B9) ^ Math.imul((bucket | 0) + 1, 0x6C62272E)) >>> 0;
    return mulberry32(s);
  }
  function botAmtFor(kind, rankIdx) {
    var arr = BOT_AMT[kind] || BOT_AMT.wood;
    return arr[Math.min(rankIdx | 0, arr.length - 1)] | 0;
  }
  function buildBotListings(nowMs) {
    var bucket = hourBucket(nowMs || Date.now());
    if (_botListCache && _botListCache.bucket === bucket) return _botListCache.listings;
    var roster = buildRoster(), out = [];
    roster.forEach(function (dog, idx) {
      var rng = botRng(idx, bucket);
      if (rng() > BOT_ACTIVE_FRAC) return; // bot is idle this hour
      // what the bot GIVES (you receive it)
      var gk = BOT_GIVE_KINDS[(rng() * BOT_GIVE_KINDS.length) | 0];
      var gr = (gk === "scrap") ? BOT_SCRAP_RAR[(rng() * BOT_SCRAP_RAR.length) | 0] : undefined;
      var ga = Math.max(1, botAmtFor(gk, dog.rankIdx) + (((rng() * 6) | 0) - 3));
      // what the bot WANTS (you pay it) -- never the same kind as give
      var wpool = BOT_WANT_KINDS.filter(function (k) { return k !== gk; });
      var wk = wpool[(rng() * wpool.length) | 0];
      var wr = (wk === "scrap") ? BOT_SCRAP_RAR[(rng() * BOT_SCRAP_RAR.length) | 0] : undefined;
      var wa = Math.max(1, botAmtFor(wk, dog.rankIdx) + (((rng() * 6) | 0) - 3));
      var clan = CLAN_BY_ID[dog.clan] || STRAY;
      out.push({
        id: "bot_" + idx + "_" + bucket,
        _src: "bot",
        seller_name: dog.name,
        seller_clan: dog.clan,
        seller_clanName: clan.name,
        color: clan.color,
        give: { kind: gk, rarity: gr, amount: ga },
        want: { kind: wk, rarity: wr, amount: wa },
        expiresAt: (bucket + 1) * 3600000 // top of next PT hour
      });
    });
    _botListCache = { bucket: bucket, listings: out };
    return out;
  }

  // ============================ BOT BEHAVIOR ACTIONS ========================
  // Wall-clock throttled (NOT per-frame). Every ~40s, spotlight a currently
  // active bot and push a Street Talk "world event" line describing what it is
  // doing in the world -- trading at the Fence, guarding turf, running a raid.
  // Uses Math.random() ONLY for the ephemeral selection (never saved).
  var BOT_ACTION_LINES = [
    "{name} is posting at the Fence right now. {clan} moves goods, not just muscle.",
    "{name} ran a raid on {dist}. Came back heavy with {kind}.",
    "{name} is holding {dist} tonight. Nobody tests a {rank}.",
    "{name} cleared a deal at the Fence -- {gk} for {wk}. That is how {clan} eats.",
    "{name} posted and pulled fast at the Fence. Smart money on the block.",
    "{name} scouting {dist} right now. {clan} plays the long game.",
    "{name} sitting on surplus {kind} after last run. Moving it through the Fence.",
    "{name} locked in on {dist}. A {rank} does not guard soft turf.",
    "{name} flipped {gk} into {wk} at the Fence. Efficient.",
    "{name} running {dist} for {clan}. The block knows the name."
  ];
  var _botActLast      = 0;
  var BOT_ACT_EVERY_MS = 40000; // one bot world line every ~40s (wall-clock)

  function tickBotActions() {
    var now = Date.now();
    if (!_botActLast) { _botActLast = now; return; }
    if (now - _botActLast < BOT_ACT_EVERY_MS) return;
    _botActLast = now;
    try {
      var listings = buildBotListings(now), roster = buildRoster();
      var dog, gk, wk;
      if (listings.length) {
        var L = listings[(Math.random() * listings.length) | 0];
        gk = L.give.kind; wk = L.want.kind;
        for (var i = 0; i < roster.length; i++) {
          if (roster[i].name === L.seller_name) { dog = roster[i]; break; }
        }
      }
      if (!dog) dog = roster[(Math.random() * roster.length) | 0];
      if (!dog) return;
      var clan = CLAN_BY_ID[dog.clan] || STRAY;
      var tpl = BOT_ACTION_LINES[(Math.random() * BOT_ACTION_LINES.length) | 0];
      var body = tpl
        .replace(/{name}/g, dog.name).replace(/{clan}/g, clan.name)
        .replace(/{rank}/g, dog.rank).replace(/{dist}/g, anyDistrict())
        .replace(/{kind}/g, gk || "scrap").replace(/{gk}/g, gk || "scrap")
        .replace(/{wk}/g, wk || "gold");
      emitEvent("bot_action", body, { clan: dog.clan, clanName: clan.name, color: clan.color, name: dog.name });
    } catch (_) {}
  }

  // seed the overlay feed ONCE: overnight chaos + today's hit, then live banter
  function seedFeed() {
    if (S._seeded) return; S._seeded = true;
    resolveOvernight();
    for (var i = 0; i < 5; i++) { try { pushMsg(nextLine(), false); } catch (_) {} }
  }

  // ============================ STREET TALK OVERLAY (DOM) ===================
  var S = { open: false, booted: false, msgs: [], filter: "all", timer: 0, lastSeen: null };
  var root, listEl, launchEl, dotEl;
  var FEED_CAP = 60;

  function mk(tag, attrs, kids) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      var v = attrs[k]; if (v == null) return;
      if (k === "class") e.className = v;
      else if (k === "text") e.textContent = v;
      else if (k.slice(0, 2) === "on" && typeof v === "function") e[k] = v;
      else e.setAttribute(k, v);
    });
    if (kids != null) (Array.isArray(kids) ? kids : [kids]).forEach(function (c) {
      if (c == null || c === false) return;
      e.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    });
    return e;
  }

  function injectCss() {
    if (document.getElementById("ak-pop-css")) return;
    var st = document.createElement("style"); st.id = "ak-pop-css";
    st.textContent = [
      "#ak-pop-launch{position:fixed;right:8px;top:43%;z-index:55;display:flex;align-items:center;gap:6px;padding:7px 11px;border-radius:7px;border:1px solid #2a2620;background:linear-gradient(165deg,#15131c,#0a0a0a);color:#e8c55a;font:800 10.5px/1 Cinzel,Georgia,serif;letter-spacing:.8px;text-transform:uppercase;cursor:pointer;box-shadow:0 3px 14px rgba(0,0,0,.55),inset 0 1px 0 rgba(201,168,76,.16),inset 0 0 0 1px rgba(0,0,0,.4)}",
      "#ak-pop-launch:active{transform:scale(.96)}",
      "#ak-pop-launch .pdot{width:8px;height:8px;border-radius:50%;background:#5fd35f;box-shadow:0 0 7px #5fd35f;animation:akpPulse 1.8s ease-in-out infinite}",
      "@keyframes akpPulse{0%,100%{opacity:.5}50%{opacity:1}}",
      "#ak-talk-btn{position:fixed;left:50%;bottom:92px;transform:translateX(-50%);z-index:56;padding:9px 16px;border-radius:7px;border:1px solid #2a2620;border-left:3px solid #c9a84c;background:linear-gradient(165deg,#1a1622,#0a0a0a);color:#e8c55a;font:800 12px/1 Cinzel,Georgia,serif;letter-spacing:.8px;text-transform:uppercase;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.6),inset 0 1px 0 rgba(201,168,76,.18);animation:akpTalkRise .25s ease-out}",
      "@keyframes akpTalkRise{from{opacity:0;transform:translateX(-50%) translateY(8px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}",
      "#ak-pop{position:fixed;left:0;right:0;bottom:0;max-height:62dvh;z-index:62;display:none;flex-direction:column;background:linear-gradient(180deg,#0b0b12,#08080c);border-top:1px solid rgba(201,168,76,.32);box-shadow:0 -8px 30px rgba(0,0,0,.6);font-family:Inter,system-ui,sans-serif}",
      "#ak-pop.open{display:flex}",
      ".akp-top{display:flex;align-items:center;gap:8px;padding:11px 14px;border-bottom:1px solid rgba(201,168,76,.18)}",
      ".akp-top h2{margin:0;font:800 14px/1 Cinzel,Georgia,serif;letter-spacing:1.4px;color:#e8c55a;flex:1}",
      ".akp-live{font:700 9px/1 Inter;letter-spacing:.6px;color:#5fd35f;display:flex;align-items:center;gap:5px}",
      ".akp-live i{width:7px;height:7px;border-radius:50%;background:#5fd35f;box-shadow:0 0 6px #5fd35f;font-style:normal}",
      ".akp-x{background:none;border:0;color:#bbb;font-size:24px;line-height:1;cursor:pointer;padding:0 4px}",
      ".akp-tabs{display:flex;gap:6px;padding:7px 12px 0}",
      ".akp-tab{flex:1;padding:7px;border-radius:8px;border:1px solid rgba(201,168,76,.22);background:rgba(255,255,255,.03);color:#cfcfd6;font:700 10.5px/1 Inter;letter-spacing:.5px;cursor:pointer}",
      ".akp-tab.on{background:rgba(201,168,76,.16);color:#e8c55a;border-color:rgba(201,168,76,.5)}",
      ".akp-list{flex:1;overflow-y:auto;-webkit-overflow-scrolling:touch;padding:9px 12px 12px;display:flex;flex-direction:column;gap:8px}",
      ".akp-row{display:flex;align-items:flex-end;gap:8px;max-width:90%;align-self:flex-start}",
      ".akp-av{flex:0 0 auto;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font:800 12px Inter;background:radial-gradient(circle at 50% 32%,rgba(201,168,76,.22),rgba(10,10,16,.92));border:1.5px solid var(--cl,#c9a84c);color:#f3e6c0;overflow:hidden}",
      ".akp-av img{width:100%;height:100%;object-fit:cover}",
      ".akp-bub{min-width:0;background:linear-gradient(180deg,rgba(20,20,28,.94),rgba(10,10,16,.94));border:1px solid rgba(201,168,76,.22);border-left:2px solid var(--cl,#c9a84c);border-radius:13px 13px 13px 4px;padding:5px 11px 6px;box-shadow:0 2px 8px rgba(0,0,0,.42)}",
      ".akp-hd{display:flex;align-items:baseline;gap:6px;margin-bottom:1px}",
      ".akp-nm{font:700 11px/1 Cinzel,Georgia,serif;letter-spacing:.3px;color:var(--cl,#e8c55a)}",
      ".akp-ft{font:700 8.5px/1 Inter;letter-spacing:.4px;text-transform:uppercase;color:var(--cl,#8a8a96);opacity:.8}",
      ".akp-bd{color:#ece7da;font-size:13px;line-height:1.4;word-break:break-word}",
      ".akp-note{color:#9a9aa6;font-size:12px;text-align:center;padding:20px 8px}",
      ".akp-row.fresh{animation:akpPop .26s cubic-bezier(.2,.8,.2,1) both}",
      "@keyframes akpPop{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}",
      ".akp-row.ev{align-self:stretch;max-width:100%}",
      ".akp-row.ev .akp-bub{background:linear-gradient(180deg,rgba(42,33,9,.96),rgba(20,16,6,.96));border:1px solid rgba(232,197,90,.5);border-left:3px solid var(--cl,#e8c55a);border-radius:10px;box-shadow:0 2px 12px rgba(201,168,76,.2),inset 0 0 0 1px rgba(0,0,0,.3)}",
      ".akp-row.ev .akp-bd{color:#f4e8c4}",
      ".akp-row.ev .akp-nm{letter-spacing:.6px;color:#f0d57a}",
      ".akp-row.ev .akp-av{border-width:2px;box-shadow:0 0 8px rgba(232,197,90,.35)}",
      "@media (prefers-reduced-motion:reduce){.akp-row.fresh{animation:none}#ak-pop-launch .pdot{animation:none}}"
    ].join("");
    document.head.appendChild(st);
  }

  function buildShell() {
    if (root) return;
    injectCss();
    var x = mk("button", { class: "akp-x", type: "button", "aria-label": "close", text: "×", onclick: close });
    var live = mk("span", { class: "akp-live" }, [mk("i", {}), "LIVE"]);
    var top = mk("div", { class: "akp-top" }, [mk("h2", { text: "STREET TALK" }), live, x]);
    var tabs = mk("div", { class: "akp-tabs" }, [
      tabBtn("all", "ALL"), tabBtn("crew", "YOUR PACK"), tabBtn("block", "THE BLOCK")
    ]);
    listEl = mk("div", { class: "akp-list" });
    root = mk("section", { id: "ak-pop" }, [top, tabs, listEl]);
    document.body.appendChild(root);
  }
  function tabBtn(id, label) {
    return mk("button", {
      class: "akp-tab" + (S.filter === id ? " on" : ""), type: "button", text: label,
      "data-f": id, onclick: function () { setFilter(id); }
    });
  }
  function setFilter(f) {
    S.filter = f;
    if (root) root.querySelectorAll(".akp-tab").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-f") === f); });
    renderAll();
  }
  function passes(m) {
    if (S.filter === "all") return true;
    if (S.filter === "crew") return m.cat === "crew";
    return m.cat === "trash" || m.cat === "ctx" || m.cat === "event"; // "the block"
  }

  function avatarNode(m) {
    var node = mk("span", { class: "akp-av", text: (m.name || "?").charAt(0) });
    // resolve a real card avatar for clan dogs (akCardArtRel); strays/ctx keep the initial
    try {
      var dog = byName(m.name, m.clan), rel = dog ? dogArtRel(dog) : "";
      if (rel) {
        var img = mk("img", { alt: "", src: "assets/" + rel });
        img.onerror = function () { try { if (!global.akImgErr || !global.akImgErr(img)) img.remove(); } catch (_) { img.remove(); } };
        node.textContent = ""; node.appendChild(img);
      }
    } catch (_) {}
    return node;
  }
  function byName(name, clan) {
    var r = buildRoster();
    for (var i = 0; i < r.length; i++) if (r[i].name === name && (!clan || r[i].clan === clan)) return r[i];
    return null;
  }
  function rowNode(m, fresh) {
    return mk("div", { class: "akp-row" + (fresh ? " fresh" : "") + (m.cat === "event" ? " ev" : ""), style: "--cl:" + (m.color || "#c9a84c") }, [
      avatarNode(m),
      mk("div", { class: "akp-bub" }, [
        mk("div", { class: "akp-hd" }, [
          mk("span", { class: "akp-nm", text: m.name || "Stray" }),
          mk("span", { class: "akp-ft", text: m.clanName || "Stray" })
        ]),
        mk("div", { class: "akp-bd", text: m.body || "" })
      ])
    ]);
  }
  function renderAll() {
    if (!listEl) return;
    var arr = S.msgs.filter(passes);
    if (!arr.length) { listEl.replaceChildren(mk("div", { class: "akp-note", text: "The block's quiet... for now." })); return; }
    listEl.replaceChildren.apply(listEl, arr.map(function (m) { return rowNode(m, false); }));
    listEl.scrollTop = listEl.scrollHeight;
  }
  function pushMsg(m, isGreet) {
    m.id = (S.msgs.length ? S.msgs[S.msgs.length - 1].id + 1 : 1);
    S.msgs.push(m);
    if (S.msgs.length > FEED_CAP) S.msgs.shift();
    if (!S.open || !listEl) return;
    if (!passes(m)) return;
    // lazy DOM: append ONE node, trim the front -- never rebuild the whole list
    var note = listEl.querySelector(".akp-note"); if (note) note.remove();
    listEl.appendChild(rowNode(m, true));
    while (listEl.childElementCount > FEED_CAP) listEl.removeChild(listEl.firstChild);
    listEl.scrollTop = listEl.scrollHeight;
  }

  // timer-pumped stream (only while open) -- NOT per-frame, protects 60fps
  function pump() {
    if (!S.open) return;
    try { pushMsg(nextLine(), false); } catch (_) {}
    S.timer = setTimeout(pump, 3400 + ((Math.random() * 3200) | 0));
  }
  function open() {
    buildShell();
    seedFeed();
    S.open = true; root.classList.add("open"); renderAll();
    clearTimeout(S.timer); S.timer = setTimeout(pump, 1200);
    if (launchEl) launchEl.style.display = "none";
  }
  function close() {
    S.open = false; clearTimeout(S.timer);
    if (root) root.classList.remove("open");
    if (launchEl) launchEl.style.display = "flex";
  }
  function toggle() { if (S.open) close(); else open(); }

  function mountLauncher() {
    if (launchEl || !document.body) return;
    injectCss();
    launchEl = mk("button", { id: "ak-pop-launch", type: "button", "aria-label": "Street Talk", onclick: toggle }, [
      mk("span", { class: "pdot" }), mk("span", { text: "STREET TALK" })
    ]);
    document.body.appendChild(launchEl);
  }

  // ============================ ROAMERS (capped, host bus) ==================
  var MAX_ROAMERS = 3, BX = [220, 1480], BY = [220, 1120];
  var _mine = [], _lastZone = null, _imgs = {}, _near = null, _talkBtn = null;
  function dogImg(dog) {
    var c = dogCard(dog); if (!c) return null;
    var key = c.name, im = _imgs[key]; if (im) return im;
    im = new Image();
    try { var rel = global.akCardArtRel ? global.akCardArtRel(c) : ""; if (rel) im.src = "assets/" + rel; } catch (_) {}
    im.onerror = function () { try { if (global.akImgErr) global.akImgErr(im); } catch (_) {} };
    _imgs[key] = im; return im;
  }
  // ---- AK-BOTWALK 2026-07-02: SHARED directional walk clips for the roamers.
  // THREE <video> elements TOTAL (side/front/back) -- the same generic clip is
  // drawn into every moving bot's circle, mirroring the hero's AK-LIVEAVATAR
  // pattern in index.html (mkWalkVid / walkClipFor). Lazy: nothing is created
  // until the first MOVING roamer draws; the clips only PLAY while a roamer on
  // screen used them in the last 400ms; document.hidden pauses all (global
  // kill). A missing/broken mp4 keeps _ok=false and the bot degrades to the
  // existing portrait/dot render -- zero behavior change on 404.
  var _botVids = null, _botVidUsed = { side: 0, front: 0, back: 0, idle: 0 };
  function mkBotVid(src, dir) {
    var v = document.createElement("video");
    v.src = src; v.muted = true; v.loop = true; v.playsInline = true;
    v.setAttribute("playsinline", ""); v.preload = "auto"; v._ok = false; v._dir = dir;
    v.addEventListener("canplay", function () { v._ok = true; });
    v.addEventListener("error", function () { v._ok = false; });
    return v;
  }
  function botVids() {
    if (_botVids || typeof document === "undefined") return _botVids;
    _botVids = {
      side:  mkBotVid("assets/avatar/bot_walk_side.mp4",  "side"),
      front: mkBotVid("assets/avatar/bot_walk_front.mp4", "front"),
      back:  mkBotVid("assets/avatar/bot_walk_back.mp4",  "back"),
      idle:  mkBotVid("assets/avatar/bot_idle.mp4",       "idle")
    };
    return _botVids;
  }
  // pick the clip that matches the dominant movement axis (same 1.15 vertical
  // bias as the hero's walkClipFor); side is the fallback while front/back load
  function botClipFor(vx, vy) {
    var V = botVids(); if (!V) return null;
    if (Math.abs(vy) > Math.abs(vx) * 1.15) {
      var c = (vy > 0) ? V.front : V.back;
      if (c._ok) return c;
    }
    return V.side;
  }
  // budget keeper (called from onTick): a shared clip plays ONLY while some
  // visible roamer stamped it in the last 400ms; everything pauses when hidden
  function tickBotVids() {
    if (!_botVids) return;
    var now = Date.now(), hid = !!(typeof document !== "undefined" && document.hidden);
    ["side", "front", "back", "idle"].forEach(function (k) {
      var v = _botVids[k]; if (!v) return;
      var want = !hid && v._ok && (now - _botVidUsed[k] < 400);
      try { if (want) { if (v.paused) v.play().catch(function () {}); } else if (!v.paused) v.pause(); } catch (_) {}
    });
  }
  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", function () { // global kill on tab-hide
      if (document.hidden && _botVids) ["side", "front", "back", "idle"].forEach(function (k) {
        try { var v = _botVids[k]; if (v && !v.paused) v.pause(); } catch (_) {}
      });
    });
  }

  function spawnRoamer(dog, zoneId) {
    var clan = CLAN_BY_ID[dog.clan] || STRAY;
    var r = {
      dog: dog, clan: clan, img: dogImg(dog), zone: zoneId,
      x: BX[0] + Math.random() * (BX[1] - BX[0]),
      y: BY[0] + Math.random() * (BY[1] - BY[0]),
      tx: 0, ty: 0, _t: 99, _cd: 4,
      _kf: true, // friendly NPC flag the hub's encind reads
      npc: { def: { label: dog.name + " [" + clan.tag + "]" } },
      update: roamUpdate, draw: roamDraw
    };
    try { global.AK_CTX.world.addRoamer(r); _mine.push(r); } catch (_) {}
  }
  function clearRoamers() {
    if (!global.AK_CTX || !global.AK_CTX.world) { _mine = []; return; }
    _mine.forEach(function (r) { try { global.AK_CTX.world.removeRoamer(r); } catch (_) {} });
    _mine = [];
  }
  function populateZone(zoneId) {
    clearRoamers();
    var clan = CLANS.filter(function (c) { return c.home === zoneId; })[0];
    var pool = clan ? clanDogs(clan.id) : (STRAY_TURF.indexOf(zoneId) >= 0 ? clanDogs("stray") : []);
    if (!pool.length) return;
    var n = Math.min(MAX_ROAMERS, clan ? 2 : 2);
    // deterministic-ish pick: highest-rank dogs walk the block first
    pool.slice().sort(function (a, b) { return b.trophies - a.trophies; }).slice(0, n)
      .forEach(function (d) { spawnRoamer(d, zoneId); });
  }
  function roamUpdate(dt, r, akctx) {
    r._t += dt;
    var dx = r.tx - r.x, dy = r.ty - r.y, d = Math.hypot(dx, dy);
    if (d < 8 || r._t > 4) {
      r._t = 0;
      r.tx = BX[0] + Math.random() * (BX[1] - BX[0]);
      r.ty = BY[0] + Math.random() * (BY[1] - BY[0]);
      dx = r.tx - r.x; dy = r.ty - r.y; d = Math.hypot(dx, dy) || 1;
    }
    if (d > 1) { var step = Math.min(42 * dt, d), mx = dx / d * step, my = dy / d * step; r.x += mx; r.y += my; r._vx = mx; r._vy = my; r._mv = true; }  // AK-BOTWALK: last x/y delta -> walk-clip direction
    else { r._mv = false; }
    r._cd = Math.max(0, r._cd - dt);
    var pd = 1e9; try { pd = akctx.world.distToMe(r.x, r.y); } catch (_) {}
    if (r._cd <= 0 && pd < 80) {
      r._cd = 14;
      try { akctx.showBanner(greetLine(r), 1.8); } catch (_) {}
      // mirror the encounter into the feed so the world stays alive even if closed later
      var friend = r.clan.id === playerClanId();
      pushMsg({ name: r.dog.name, clan: r.clan.id, clanName: r.clan.name, color: r.clan.color,
        body: friend ? (myName() + ", good to run with you on " + (DISTRICT[r.zone] || "the block") + ".")
                     : ("Eyes on you, Stray. This is " + r.clan.name + " turf."),
        cat: friend ? "crew" : "trash" }, true);
    }
    if (pd < 95) { _near = r; showTalkBtn(r); }            // RUN UP + TALK: button shows when you reach an AI dog
    else if (_near === r) { _near = null; hideTalkBtn(); }
  }
  function roamDraw(g, r, akctx) {
    var X, Y;
    try { X = akctx.world.wx(r.x); Y = akctx.world.wy(r.y); } catch (_) { return; }
    g.save();
    g.globalAlpha = 0.32; g.fillStyle = "#000";
    g.beginPath(); g.ellipse(X, Y + 17, 17, 5.5, 0, 0, 7); g.fill();
    g.globalAlpha = 1;
    var R = 17;
    g.beginPath(); g.arc(X, Y, R + 2.5, 0, 7); g.fillStyle = r.clan.color; g.globalAlpha = 0.9; g.fill();
    g.globalAlpha = 1;
    g.save(); g.beginPath(); g.arc(X, Y, R, 0, 7); g.clip();
    // AK-BOTWALK: EVERY visible roamer draws a LIVE clip inside its circle -- a
    // MOVING bot uses the directional walk clip, a RESTING bot uses the idle
    // (breathing) clip. The host already culls off-screen roamers before calling
    // draw, so every roamer here is visible. The static card portrait is now only
    // a last-resort fallback while a clip 404s or is still loading.
    var vid = null, V = botVids();
    if (V && !(typeof document !== "undefined" && document.hidden)) {
      var bc = r._mv ? botClipFor(r._vx || 0, r._vy || 0) : V.idle;   // idle clip is front-facing (_dir==='idle') -> never mirrored
      if (bc) {
        _botVidUsed[bc._dir] = Date.now();   // stamp usage -> tickBotVids keeps it playing (and warms a not-yet-ready clip)
        if (bc._ok && bc.readyState >= 2) { vid = bc; if (bc.paused) { try { bc.play().catch(function () {}); } catch (_) {} } }
      }
    }
    var im = r.img;
    if (vid) {
      if (vid._dir === "side" && (r._vx || 0) < 0) {   // bot_walk_side faces RIGHT natively -- mirror when walking LEFT
        g.scale(-1, 1); g.drawImage(vid, -X - R, Y - R, R * 2, R * 2); g.scale(-1, 1);
      } else g.drawImage(vid, X - R, Y - R, R * 2, R * 2);
    }
    else if (im && im.complete && im.naturalWidth) g.drawImage(im, X - R, Y - R, R * 2, R * 2);
    else { g.fillStyle = "#16161d"; g.fillRect(X - R, Y - R, R * 2, R * 2); g.fillStyle = r.clan.color; g.font = "800 17px Inter"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(r.dog.name.charAt(0), X, Y); }
    g.restore();
    g.font = "700 10px Inter"; g.textAlign = "center"; g.textBaseline = "alphabetic";
    g.fillStyle = "rgba(0,0,0,.6)"; g.fillText(r.dog.name, X + 0.5, Y - R - 5.5);
    g.fillStyle = r.clan.color; g.fillText(r.dog.name, X, Y - R - 6);
    g.restore();
  }

  // ---- RUN UP + TALK: a TALK button shows when you reach a roamer; tapping opens a real chat ----
  function ensureTalkBtn() {
    if (_talkBtn || typeof document === "undefined") return _talkBtn;
    try { injectCss(); } catch (_) {}
    var b = document.createElement("button"); b.id = "ak-talk-btn"; b.type = "button"; b.style.display = "none";
    try { document.body.appendChild(b); } catch (_) {}
    _talkBtn = b; return b;
  }
  function showTalkBtn(r) {
    var b = ensureTalkBtn(); if (!b) return;
    b.textContent = "TALK -- " + r.dog.name;
    b.style.borderLeftColor = r.clan.color;
    b.onclick = function () { talkTo(r); };
    if (b.style.display === "none") b.style.display = "block";
  }
  function hideTalkBtn() { if (_talkBtn) _talkBtn.style.display = "none"; }
  function talkTo(r) {
    try { open(); } catch (_) {}                            // the chat plays out in Street Talk
    var friend = r.clan.id === playerClanId();
    pushMsg({ name: myName(), clan: "you", clanName: "you", color: "#e8c55a",
      body: friend ? ("Yo " + r.dog.name + ", what's good on the block?")
                   : (r.dog.name + ", we got a problem? Just passing through."), cat: "you" }, true);
    var rep = friend
      ? [r.dog.name + ": all love, " + myName() + ". " + r.clan.name + " holds it down.",
         r.dog.name + ": stay sharp out here -- we run together.",
         r.dog.name + ": you good? Block's been too quiet lately."]
      : [r.dog.name + ": passing through? Keep it moving, Stray.",
         r.dog.name + ": this is " + r.clan.name + " turf -- watch your tail.",
         r.dog.name + ": you got heart walking up to me. Don't make it your last."];
    var line = rep[(Date.now() / 1000 | 0) % rep.length];
    setTimeout(function () { try { pushMsg({ name: r.dog.name, clan: r.clan.id, clanName: r.clan.name, color: r.clan.color, body: line, cat: friend ? "crew" : "trash" }, true); } catch (_) {} }, 700);
  }

  // ============================ AK_SYSTEMS module ===========================
  var MODULE = {
    id: "population",
    init: function (ctx) {
      try { _lastZone = ctx && ctx.zoneId; populateZone(_lastZone); } catch (_) {}
      try { resolveOvernight(); } catch (_) {} // post the overnight chaos + today's hit on load
    },
    // light bookkeeping ONLY -- district re-seed + wall-clock-throttled live event
    onTick: function (dt, ctx) {
      try { tickEvents(); } catch (_) {}    // throttled internally -- safe per-frame, 60fps
      try { tickBotActions(); } catch (_) {} // throttled -- emits one bot world line every ~40s
      try { tickBotVids(); } catch (_) {}    // AK-BOTWALK: play/pause the 3 shared walk clips (usage-stamped, hidden-tab kill)
      if (!ctx) return;
      var z = ctx.zoneId;
      if (z !== _lastZone) { _lastZone = z; populateZone(z); }
    },
    onDrawWorld: function () {} // host draws roamers from its _roamers bus; nothing extra
  };

  // ============================ EXPORT + WIRE ===============================
  // Export the global BEFORE any registry bail (HARD requirement).
  var API = {
    roster: rosterPublic,
    leaderboard: leaderboard,
    clans: function () { return CLANS.slice(); },
    open: open, close: close, toggle: toggle,
    speak: function () { try { pushMsg(nextLine(), true); } catch (_) {} },
    // ---- P5: living population (integration globals) ----
    eventFeed: eventFeed,             // (n?) -> recent world events [{id,ts,kind,body,district,clan,clanName,color,name}]
    hitOfDay: hitOfDay,               // () -> today's HIT {name,clan,district,bones,claimed,resetsInMs,...}
    isHitTarget: isHitTarget,         // (dogId) -> is this dog today's hit?
    beatHitOfDay: beatHitOfDay,       // (dogId?) -> grant bonus BONES once/day (parity-safe; combat layer calls on a win)
    overnight: function () {          // () -> today's deterministic offline-chaos items
      try { resolveOvernight(); } catch (_) {}
      return (_chaosCache || []).map(function (e) {
        return { kind: e.kind, body: e.body, district: e.district || null, clan: e.clan, clanName: e.clanName, color: e.color, name: e.name };
      });
    },
    emit: function (kind, body, meta) { try { return emitEvent(String(kind || "street"), String(body || ""), meta || {}); } catch (_) { return null; } },
    dayKey: dayKey,                   // () -> "YYYY-MM-DD" anchored to PT
    resetsInMs: msToTomorrowPT,       // () -> ms until the next PT midnight roll
    // () -> array of bot listings for the current PT hour (deterministic, offline-safe).
    // Each entry: { id, _src:"bot", seller_name, seller_clan, seller_clanName, color,
    //               give:{kind,rarity?,amount}, want:{kind,rarity?,amount}, expiresAt }
    // Only soft resources (wood/stone/metal/scrap/produce for give; + gold for want).
    // Rotates at the top of each PT hour. marketplace.js consumes this for its BOARD tab.
    marketListings: function (nowMs) { try { return buildBotListings(nowMs); } catch (_) { return []; } }
  };
  try { global.AK_POPULATION = API; } catch (_) {}
  try { if (global.AK_SYSTEMS && global.AK_SYSTEMS.register) global.AK_SYSTEMS.register(MODULE); } catch (_) {}

  function wire() {
    if (S.booted) return; S.booted = true;
    mountLauncher();
    // hook an existing button if the hub ever adds one; the launcher is the default
    try { var b = document.getElementById("streettalkbtn"); if (b) b.addEventListener("click", toggle); } catch (_) {}
    // resolve the overnight chaos + today's hit on load so the event feed (and
    // any HUD ticker) has the morning-after word even before Street Talk opens
    try { resolveOvernight(); } catch (_) {}
  }
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
    else wire();
  }
})(typeof window !== "undefined" ? window : this);
