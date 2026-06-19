// ak-pass -- Alley Kingz battle pass ("Alley Pass"), server-authoritative.
// Mirrors ak-crew/alley-kingz-shop: client posts an intent, server is the only
// writer. Match XP is awarded server-side (bounded + daily-capped) so the client
// can't fabricate progress. Tier rewards are paid through the ak_grants inbox
// (claimed client-side via AK_ECON), same rail as donations.
//
// Actions: get | report-match | claim-tier | unlock-premium
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const SEASON = 1, MAX_TIER = 30, XP_PER_TIER = 100, DAILY_CAP = 300;

// reward TRACK (constant; tune freely). kinds: gold | scrap | chest | keys | card.
// chest tier goes in card_id (client maps it via AK_ECON.grantChest).
function buildTrack() {
  const free = [], prem = [];
  for (let t = 1; t <= MAX_TIER; t++) {
    // escalating base amounts so the ramp feels richer as you climb
    const goldAmt = 40 + Math.floor((t - 1) / 3) * 15;   // ~40 -> ~175
    const scrapAmt = 6 + Math.floor((t - 1) / 5) * 3;    // ~6 -> ~21
    // ---- FREE lane: chest every 5, a MYTHIC card at the season finale ----
    if (t === MAX_TIER)    free.push({ kind: "card",  card_id: "0001", rarity: "Mythic", amount: 1 });  // tier 30: the $BCARDD Mythic
    else if (t % 10 === 0) free.push({ kind: "chest", card_id: "gold",   amount: 1 });
    else if (t % 5 === 0)  free.push({ kind: "chest", card_id: "silver", amount: 1 });
    else if (t % 3 === 0)  free.push({ kind: "scrap", rarity: "Common",  amount: scrapAmt });
    else                   free.push({ kind: "gold",  amount: goldAmt });
    // ---- PREMIUM lane: ~2x the haul, better rarities, diamond chests, matching finale ----
    if (t === MAX_TIER)    prem.push({ kind: "card",  card_id: "0001", rarity: "Mythic", amount: 1 });
    else if (t % 10 === 0) prem.push({ kind: "chest", card_id: "diamond", amount: 1 });
    else if (t % 5 === 0)  prem.push({ kind: "keys",  amount: 2 });
    else if (t % 3 === 0)  prem.push({ kind: "scrap", rarity: "Rare",   amount: scrapAmt });
    else                   prem.push({ kind: "gold",  amount: goldAmt * 2 });
  }
  return { free, prem };
}
const TRACK = buildTrack();

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}
function tierFor(xp: number) { return Math.max(0, Math.min(MAX_TIER, Math.floor(xp / XP_PER_TIER))); }
function today() { return new Date().toISOString().slice(0, 10); }

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "POST only" }, 405);

  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const admin = createClient(url, serviceKey, { auth: { persistSession: false } });

  const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return json({ ok: false, error: "sign in required" }, 401);
  const { data: udata, error: uerr } = await admin.auth.getUser(jwt);
  const user = udata?.user;
  if (uerr || !user) return json({ ok: false, error: "invalid session" }, 401);
  const uid = user.id;

  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch { /* empty */ }
  const action = String(body.action || "get");

  async function loadProgress() {
    const { data } = await admin.from("ak_pass_progress").select("*").eq("user_id", uid).maybeSingle();
    return data || { user_id: uid, season: SEASON, xp: 0, tier: 0, premium: false, claimed_free: [], claimed_prem: [], daily_xp: 0, daily_day: null };
  }

  try {
    if (action === "get") {
      const p = await loadProgress();
      return json({ ok: true, season: SEASON, max_tier: MAX_TIER, xp_per_tier: XP_PER_TIER,
        xp: p.xp, tier: p.tier, premium: p.premium, claimed_free: p.claimed_free || [], claimed_prem: p.claimed_prem || [],
        track: TRACK });
    }

    if (action === "report-match") {
      const p = await loadProgress();
      const won = !!body.won;
      const gates = Math.max(0, Math.min(4, parseInt(String(body.gates || 0), 10) || 0));
      let earn = (won ? 30 : 10) + 5 * gates;
      // daily anti-grind cap
      let dailyXp = p.daily_day === today() ? (p.daily_xp || 0) : 0;
      const room = Math.max(0, DAILY_CAP - dailyXp);
      earn = Math.min(earn, room);
      const xp = Math.min(MAX_TIER * XP_PER_TIER, (p.xp || 0) + earn);
      const tier = tierFor(xp);
      dailyXp += earn;
      await admin.from("ak_pass_progress").upsert({
        user_id: uid, season: SEASON, xp, tier, premium: !!p.premium,
        claimed_free: p.claimed_free || [], claimed_prem: p.claimed_prem || [],
        daily_xp: dailyXp, daily_day: today(), updated_at: new Date().toISOString(),
      });
      return json({ ok: true, awarded: earn, xp, tier, capped: room <= 0 });
    }

    if (action === "claim-tier") {
      const tier = parseInt(String(body.tier || 0), 10) || 0;
      const lane = body.lane === "prem" ? "prem" : "free";
      if (tier < 1 || tier > MAX_TIER) return json({ ok: false, error: "bad tier" }, 400);
      const p = await loadProgress();
      if (tier > (p.tier || 0)) return json({ ok: false, error: "tier not reached" }, 403);
      if (lane === "prem" && !p.premium) return json({ ok: false, error: "premium locked" }, 403);
      const claimedKey = lane === "prem" ? "claimed_prem" : "claimed_free";
      const claimed = (p[claimedKey] || []).slice();
      if (claimed.indexOf(tier) >= 0) return json({ ok: false, error: "already claimed" }, 409);
      const reward = TRACK[lane][tier - 1];
      if (!reward) return json({ ok: false, error: "no reward" }, 400);
      await admin.from("ak_grants").insert({
        user_id: uid, kind: reward.kind, card_id: reward.card_id || null, rarity: reward.rarity || null,
        amount: reward.amount || 1, source: "pass", note: "Alley Pass tier " + tier + (lane === "prem" ? " (premium)" : ""),
      });
      claimed.push(tier);
      const patch: Record<string, unknown> = { user_id: uid };
      patch[claimedKey] = claimed;
      await admin.from("ak_pass_progress").upsert(Object.assign({
        user_id: uid, season: SEASON, xp: p.xp || 0, tier: p.tier || 0, premium: !!p.premium,
        claimed_free: p.claimed_free || [], claimed_prem: p.claimed_prem || [],
        daily_xp: p.daily_xp || 0, daily_day: p.daily_day || null, updated_at: new Date().toISOString(),
      }, patch));
      return json({ ok: true, reward, tier, lane });
    }

    if (action === "unlock-premium") {
      // Premium = spend Gems (server-only, shared with the shop's game_currencies).
      // Charge atomically via ak_spend_gems (decrement-if-sufficient, no race), log
      // to the shop's ak_transactions ledger, then flip premium. Tunable price; see
      // PRICING_STRATEGY.md (~Clash Pass Royale tier).
      const p = await loadProgress();
      if (p.premium) return json({ ok: true, premium: true, already: true });
      const COST = 800;
      const { data: newBal, error: spendErr } = await admin.rpc("ak_spend_gems", { p_player: uid, p_amount: COST });
      if (spendErr) return json({ ok: false, error: String(spendErr.message) }, 500);
      if (newBal == null || Number(newBal) < 0) return json({ ok: false, error: "not enough gems", need: COST, needsGems: true });
      await admin.from("ak_transactions").insert({ player_id: uid, action: "unlock_premium_pass", sku: "alley_pass_premium_s1", currency_deltas: { gems: -COST }, source: "ak-pass" });
      await admin.from("ak_pass_progress").upsert({
        user_id: uid, season: p.season || SEASON, xp: p.xp || 0, tier: p.tier || 0, premium: true,
        claimed_free: p.claimed_free || [], claimed_prem: p.claimed_prem || [],
        daily_xp: p.daily_xp || 0, daily_day: p.daily_day || null, updated_at: new Date().toISOString(),
      });
      return json({ ok: true, premium: true, spent: COST, gems_left: Number(newBal) });
    }

    return json({ ok: false, error: "unknown action" }, 400);
  } catch (e) {
    return json({ ok: false, error: String((e as Error)?.message || e) }, 500);
  }
});
