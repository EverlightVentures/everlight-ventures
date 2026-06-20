// ak-raid -- Alley Kingz RAID / BASE DEFENSE server-authoritative edge function.
// Mirrors the ak-crew pattern: the CLIENT posts an INTENT {action, ...}, the SERVER
// (service role) is the only writer and enforces every rule. RLS blocks all direct
// client writes, so this function is the sole path to mutate the raid tables.
//
// CLIENT: ecosystem/game/systems/raid.js -> callAkRaid({action,...}). Every shape
// below matches what raid.js sends/reads EXACTLY (the war map swaps in r.bases, the
// gem shield reads r.shieldUntil, the night defense fires reinforce).
//
// Actions:
//   targets       -> the rotation window's 3 snapshot-as-bot rival bases (war map list)
//   resolve       -> award surgical raid loot via ak_grants (+50% on revenge); anti-farm
//   buy-shield    -> GEM-TIER shields ONLY (Fortress Dome 80 / Panic 160); gems server-only
//   reinforce     -> validate crew + cooldown for night defense (returns defender count)
//   revenge       -> the server-pushed 24h revenge inbox (merges into local p.raid.revenge)
//   claim-grants  -> drain queued ak_grants for this user (same inbox ak-crew claims)
//
// CRYPTO GATE (HARD LAW): loot is soft-currency ONLY (gold + scrap); a FORBID regex
// rejects any $BCARDD/ALK line. Shields bought here are gem-tier ONLY (gems are
// server-only, spent via ak_spend_gems). Mythic is NEVER fielded as a defender/loot.
//
// Targets AK's OWN project only (SUPABASE_URL/SERVICE_ROLE injected at runtime:
// project mfghdobptredxxhbjwyz -- NEVER the casino project).
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// ---- HARD LAW guard: no $BCARDD / ALK / $-token ever appears on a loot line -------
const TOKEN_RE = /\$|bcardd|alk/i;

// ---- server-purchasable shields: GEM TIERS ONLY (parity: a gem buys a TIMER) -------
// gold tiers (street/crew/iron) settle client-side; these mirror raid.js SHIELDS.
const GEM_SHIELDS: Record<string, { hrs: number; gems: number; name: string }> = {
  fortress: { hrs: 16, gems: 80,  name: "Fortress Dome" },
  panic:    { hrs: 24, gems: 160, name: "Panic Button" },
};

// ---- loot caps (anti-farm; soft-currency only) -------------------------------------
const LOOT_GOLD_CAP = 600, LOOT_SCRAP_CAP = 12;
const REINFORCE_COOLDOWN_MS = 6 * 3600 * 1000;   // one crew call-out per 6h
const WINDOW_MS = 720000;                         // ~12 min rotation (raid.js CYCLE_MS*2)

// ===========================================================================
// the 4 crews/factions + REAL card pools BY NAME (verbatim from raid.js so a
// server base is byte-consistent with the client fallback; Mythic is NEVER
// selected -- the tier ladders cap at Legendary).
// ===========================================================================
const FACTIONS = [
  { id: "boneguard_crew",   cls: "Boneguard Crew",   accent: "#e8c55a",
    gangs: ["The Boneyard Mob", "Crypt Kings", "Marrow Syndicate"],
    pool: { Common: ["Tank Pug", "Copper Chow", "Brick Bullmastiff", "Hatchet"], Rare: ["Granite Saint", "Grit Bulldog", "Alloy Akita", "Warden Newfie"], Epic: ["Balboa", "Iron Rottweiler", "Anvil", "Bonecrusher"], Legendary: ["Stonejaw", "Cinderblock", "Tombstone"] } },
  { id: "zoomie_syndicate", cls: "Zoomie Syndicate", accent: "#7CFFB0",
    gangs: ["Zoomie Riot", "Nitro Pack", "The Burnouts"],
    pool: { Common: ["Neon Whippet", "Turbo Jack", "Drift Sheltie", "Byte Beagle"], Rare: ["Pixel Greyhound", "Circuit Shiba", "Flash Saluki", "Bolt Corgi"], Epic: ["Razor Vizsla", "Aero Malinois", "Roadblock", "Bullbar"], Legendary: ["Rollcage", "Deadweight"] } },
  { id: "leashbreak_tactix", cls: "Leashbreak Tactix", accent: "#9d8bff",
    gangs: ["Leashless Cartel", "Ghost Wire Tactix", "The Static Saints"],
    pool: { Common: ["Echo Dalmatian", "Static Sheba Inu", "Vibe Shih Tzu", "Hexer"], Rare: ["Holo Husky", "Chill Samoyed", "Prism Poodle", "Signal Pointer"], Epic: ["Synth Collie", "Noir Setter", "Pulse Border Collie", "Deadbolt"], Legendary: ["Firewall", "Sandbag", "Bulwark"] } },
  { id: "k9_circuitry",     cls: "K9 Circuitry",     accent: "#7fc8ff",
    gangs: ["Circuit Hounds", "The Grid Pack", "Voltage Kennel"],
    pool: { Common: ["Neon Dachshund", "Flux Pomeranian", "Rail Terrier", "Buckshot"], Rare: ["Laser Beagle", "Volt Corgi", "Grid Schnauzer", "Beacon Basset"], Epic: ["Circuit Retriever", "Nova Shepherd", "Bunker", "Howitzer"], Legendary: ["Casemate", "Emplacement"] } },
];
const BLD = [
  { id: "GEM", name: "Gem Mine" }, { id: "MINT", name: "Gold Mint" }, { id: "FORGE", name: "Card Forge" },
  { id: "LAB", name: "Research Lab" }, { id: "GEN", name: "Generator" },
];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}
function clamp(v: number, lo: number, hi: number) { return Math.max(lo, Math.min(hi, v)); }

// deterministic PRNG (mulberry32) -- identical to raid.js so bases are stable per window
function rng32(seed: number) {
  let s = seed >>> 0;
  return function () {
    s |= 0; s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function pickRoster(f: typeof FACTIONS[number], tier: number, r: () => number): string[] {
  const tiers = tier >= 3 ? ["Legendary", "Epic", "Epic", "Rare"]
    : tier === 2 ? ["Epic", "Rare", "Rare", "Common"]
    : ["Rare", "Common", "Common", "Common"];
  const out: string[] = [];
  tiers.forEach((rar) => {
    const bag: string[] = (f.pool as Record<string, string[]>)[rar] || f.pool.Common;
    const n = bag[Math.floor(r() * bag.length)];
    if (out.indexOf(n) < 0) out.push(n);
    else out.push(bag[(bag.indexOf(n) + 1) % bag.length]);
  });
  return out;
}
// generate the window's 3 bot bases (deterministic; mirrors raid.js genTargets)
function genWindowBases(windowId: number) {
  const r = rng32((windowId * 2654435761) >>> 0);
  const out = [];
  for (let i = 0; i < 3; i++) {
    const f = FACTIONS[Math.floor(r() * FACTIONS.length)];
    const tier = 1 + Math.floor(r() * 3);
    const gang = f.gangs[Math.floor(r() * f.gangs.length)];
    const roster = pickRoster(f, tier, r);
    const blds = BLD.map((b) => ({ id: b.id, name: b.name, lvl: clamp(tier + Math.floor(r() * 3), 1, 10) }));
    const scrapR = tier >= 3 ? "Epic" : "Rare";
    out.push({
      window_id: windowId, slot: i, name: gang, faction: f.id, cls: f.cls, accent: f.accent,
      tier, trophies: 280 + tier * 210 + Math.floor(r() * 160),
      roster, buildings: blds,
      loot: { gold: 110 * tier + Math.floor(r() * 90), scrap: tier >= 2 ? 2 * tier : 0, scrapR },
      city: clamp(tier + 1, 0, 9), level: clamp(2 + tier * 2, 1, 10), diff_offset: tier - 1,
      seed: (windowId * 2654435761) >>> 0,
    });
  }
  return out;
}
// shape a DB row -> the EXACT object raid.js's war map renders (note diffOffset camelCase)
// deno-lint-ignore no-explicit-any
function shapeBase(row: any) {
  return {
    id: row.id, name: row.name, faction: row.faction, cls: row.cls, accent: row.accent,
    tier: row.tier, trophies: row.trophies, roster: row.roster || [], buildings: row.buildings || [],
    loot: row.loot || { gold: 0 }, city: row.city, level: row.level, diffOffset: row.diff_offset,
  };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "POST only" }, 405);

  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const admin = createClient(url, serviceKey, { auth: { persistSession: false } });

  // verify the caller (same as ak-crew)
  const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return json({ ok: false, error: "sign in required" }, 401);
  const { data: udata, error: uerr } = await admin.auth.getUser(jwt);
  const user = udata?.user;
  if (uerr || !user) return json({ ok: false, error: "invalid session" }, 401);
  const uid = user.id;

  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch { /* empty */ }
  const action = String(body.action || "");

  // the caller's crew faction (for revenge attribution); null if not in a crew
  async function myFaction(): Promise<string | null> {
    const { data: m } = await admin.from("ak_crew_members").select("crew_id").eq("user_id", uid).maybeSingle();
    if (!m) return null;
    const { data: c } = await admin.from("ak_crews").select("faction").eq("id", m.crew_id).maybeSingle();
    return (c && c.faction) || null;
  }

  try {
    // ---- TARGETS: serve (and lazily seed) the current window's 3 bot bases ---------
    if (action === "targets") {
      const windowId = Math.floor(Date.now() / WINDOW_MS);
      let { data: rows } = await admin.from("ak_bot_bases").select("*").eq("window_id", windowId).order("slot");
      if (!rows || rows.length < 3) {
        // generate + upsert deterministically (idempotent on window_id,slot)
        const gen = genWindowBases(windowId);
        await admin.from("ak_bot_bases").upsert(gen, { onConflict: "window_id,slot" });
        const re = await admin.from("ak_bot_bases").select("*").eq("window_id", windowId).order("slot");
        rows = re.data || [];
      }
      // never serve a shielded real-player snapshot as a target (bots have no snap_user_id)
      const nowMs = Date.now();
      const safe = [];
      for (const row of rows) {
        if (row.snap_user_id) {
          const { data: st } = await admin.from("ak_raid_state").select("shield_until").eq("user_id", row.snap_user_id).maybeSingle();
          if (st && st.shield_until && new Date(st.shield_until).getTime() > nowMs) continue;  // skip shielded players
        }
        safe.push(shapeBase(row));
      }
      return json({ ok: true, bases: safe });
    }

    // ---- RESOLVE: award surgical raid loot via ak_grants (+50% on revenge) ---------
    if (action === "resolve") {
      const baseId = String(body.base_id || body.id || "");
      const isRevenge = !!body.revenge;
      const won = body.won === undefined ? true : !!body.won;   // default: a raid that calls resolve won
      if (!baseId) return json({ ok: false, error: "base_id required" }, 400);

      const { data: base } = await admin.from("ak_bot_bases").select("*").eq("id", baseId).maybeSingle();
      if (!base) return json({ ok: false, error: "base not found" }, 404);

      // mark that this player raided (anti-chain bookkeeping)
      await admin.from("ak_raid_state").upsert({ user_id: uid, last_raid_at: new Date().toISOString(), updated_at: new Date().toISOString() });

      if (!won) return json({ ok: true, looted: false, loot: { gold: 0, scrap: 0 } });

      // anti-farm: loot a given base ONCE (replays still play for fun, pay nothing)
      const { data: prior } = await admin.from("ak_raid_log").select("id").eq("raider_id", uid).eq("base_id", baseId).maybeSingle();
      if (prior) return json({ ok: true, looted: false, loot: { gold: 0, scrap: 0 }, note: "already looted" });

      const loot = (base.loot || {}) as { gold?: number; scrap?: number; scrapR?: string };
      const mult = isRevenge ? 1.5 : 1.0;
      let gold = clamp(Math.round((loot.gold || 0) * mult), 0, LOOT_GOLD_CAP);
      let scrap = clamp(Math.round((loot.scrap || 0) * mult), 0, LOOT_SCRAP_CAP);
      let scrapR = String(loot.scrapR || "Rare");
      // HARD LAW: soft-currency loot only; never a $BCARDD/ALK line.
      if (TOKEN_RE.test(scrapR)) { scrapR = "Rare"; }
      if (scrapR === "Mythic" || scrapR === "Legendary") scrapR = "Epic";  // loot scrap caps at Epic

      // queue soft-currency grants on the shared ak_grants rail (claimed via AKSocial.claimGrants)
      const grants: Record<string, unknown>[] = [
        { user_id: uid, kind: "gold", amount: gold, source: "raid", note: (isRevenge ? "Revenge raid: " : "Raid: ") + String(base.name).slice(0, 40) },
      ];
      if (scrap > 0) grants.push({ user_id: uid, kind: "scrap", rarity: scrapR, amount: scrap, source: "raid", note: "Raid scrap" });
      // defense-in-depth: drop any grant whose note/rarity smuggled a token (cannot happen above, but assert)
      const cleanGrants = grants.filter((g) => !TOKEN_RE.test(String(g.rarity || "")) && !TOKEN_RE.test(String(g.note || "")) || g.kind === "gold");
      await admin.from("ak_grants").insert(cleanGrants);

      await admin.from("ak_raid_log").insert({
        raider_id: uid, base_id: baseId, window_id: base.window_id, is_revenge: isRevenge,
        loot_gold: gold, loot_scrap: scrap, loot_scrapr: scrap > 0 ? scrapR : null,
      });

      // if this base was a REAL-player snapshot, push a 24h revenge row to that victim
      let revengePushed = false;
      if (base.snap_user_id && base.snap_user_id !== uid) {
        const attackerName = String(body.name || "Rival Crew").slice(0, 24);
        const attackerFaction = await myFaction();
        await admin.from("ak_raid_revenge").insert({
          victim_id: base.snap_user_id, attacker_name: attackerName,
          attacker_faction: attackerFaction, tier: base.tier,
        });
        revengePushed = true;
      }

      return json({ ok: true, looted: true, loot: { gold, scrap, scrapR }, revenge: revengePushed });
    }

    // ---- BUY-SHIELD: GEM tiers ONLY (gold tiers settle client-side) -----------------
    if (action === "buy-shield") {
      const tierId = String(body.tier || "");
      const t = GEM_SHIELDS[tierId];
      if (!t) return json({ ok: false, error: "gold shields settle client-side; only gem tiers are sold here" }, 400);

      // gems are server-only -> spend atomically via the shared RPC (returns new bal or -1)
      const { data: newBal, error: spendErr } = await admin.rpc("ak_spend_gems", { p_player: uid, p_amount: t.gems });
      if (spendErr) return json({ ok: false, error: String(spendErr.message) }, 500);
      if (newBal === null || Number(newBal) < 0) return json({ ok: false, error: "not enough gems" }, 402);

      // extend (never shorten) the shield; persist server-side
      const { data: st } = await admin.from("ak_raid_state").select("shield_until").eq("user_id", uid).maybeSingle();
      const curMs = st && st.shield_until ? new Date(st.shield_until).getTime() : 0;
      const untilMs = Math.max(curMs, Date.now()) + t.hrs * 3600 * 1000;
      await admin.from("ak_raid_state").upsert({ user_id: uid, shield_until: new Date(untilMs).toISOString(), updated_at: new Date().toISOString() });

      return json({ ok: true, shieldUntil: untilMs, gems: Number(newBal), tier: tierId, hrs: t.hrs });
    }

    // ---- REINFORCE: validate crew + cooldown for night defense ----------------------
    if (action === "reinforce") {
      const { data: m } = await admin.from("ak_crew_members").select("crew_id").eq("user_id", uid).maybeSingle();
      if (!m) return json({ ok: false, error: "join a crew to call backup", defenders: 0 });

      const { data: st } = await admin.from("ak_raid_state").select("last_reinforce_at").eq("user_id", uid).maybeSingle();
      const lastMs = st && st.last_reinforce_at ? new Date(st.last_reinforce_at).getTime() : 0;
      if (Date.now() - lastMs < REINFORCE_COOLDOWN_MS) {
        return json({ ok: true, defenders: 0, cooldown: true });
      }
      await admin.from("ak_raid_state").upsert({ user_id: uid, last_reinforce_at: new Date().toISOString(), updated_at: new Date().toISOString() });
      return json({ ok: true, defenders: 2 });   // mirrors raid.js callCrew() n=2
    }

    // ---- REVENGE: the server-pushed 24h revenge inbox (merge into p.raid.revenge) ---
    if (action === "revenge") {
      const { data: rows } = await admin.from("ak_raid_revenge")
        .select("id,attacker_name,attacker_faction,tier,created_at")
        .eq("victim_id", uid).eq("claimed", false).gt("expires_at", new Date().toISOString())
        .order("created_at", { ascending: false }).limit(40);
      const list = (rows || []).map((r) => ({
        id: r.id, name: r.attacker_name, faction: r.attacker_faction, tier: r.tier,
        at: new Date(r.created_at).getTime(),
      }));
      if (list.length) {
        await admin.from("ak_raid_revenge").update({ claimed: true }).in("id", list.map((x) => x.id));
      }
      return json({ ok: true, revenge: list });
    }

    // ---- CLAIM-GRANTS: drain queued grants (same inbox ak-crew claims; mirror it) ---
    if (action === "claim-grants") {
      const { data: grants } = await admin.from("ak_grants")
        .select("id,kind,card_id,rarity,amount,source,note").eq("user_id", uid).eq("claimed", false)
        .order("created_at", { ascending: true }).limit(100);
      if (!grants || !grants.length) return json({ ok: true, grants: [] });
      const ids = grants.map((g) => g.id);
      await admin.from("ak_grants").update({ claimed: true }).in("id", ids);
      return json({ ok: true, grants });
    }

    return json({ ok: false, error: "unknown action" }, 400);
  } catch (e) {
    return json({ ok: false, error: String((e as Error)?.message || e) }, 500);
  }
});
