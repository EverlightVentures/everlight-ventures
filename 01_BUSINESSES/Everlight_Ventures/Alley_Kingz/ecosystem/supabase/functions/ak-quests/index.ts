// ak-quests -- Alley Kingz "Hit List" daily/weekly quests, server-side.
// Raw-counter model: per-period counters (ak_period_stats) bumped by play/donate/
// chat; quests (constant below) are thresholds against those counters. Rewards pay
// via ak_grants, or bump ak_pass_progress for pass-XP rewards (quests feed the pass).
// Counters cap so over-reporting can't be exploited (in-game value only, no money).
//
// Actions: get | report-match | report-event | claim
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const CAP = 100; // counters never stored above this
const PASS_MAX_TIER = 30, PASS_XP_PER = 100;

// metric: matches | wins | gates | donates | chats ; scope: daily | weekly
const QUESTS = [
  { id: "d_play3",   scope: "daily",  metric: "matches", target: 3,  title: "Hit the streets",   desc: "Play 3 matches",     reward: { kind: "gold", amount: 60 } },
  { id: "d_win2",    scope: "daily",  metric: "wins",    target: 2,  title: "Take the block",    desc: "Win 2 matches",      reward: { kind: "passxp", amount: 40 } },
  { id: "d_gates6",  scope: "daily",  metric: "gates",   target: 6,  title: "Crack the gates",   desc: "Break 6 gate towers", reward: { kind: "scrap", rarity: "Rare", amount: 4 } },
  { id: "w_win10",   scope: "weekly", metric: "wins",    target: 10, title: "Run the city",      desc: "Win 10 matches",     reward: { kind: "chest", card_id: "gold", amount: 1 } },
  { id: "w_donate8", scope: "weekly", metric: "donates", target: 8,  title: "Carry your weight", desc: "Donate 8 cards",     reward: { kind: "keys", amount: 1 } },
  { id: "w_play20",  scope: "weekly", metric: "matches", target: 20, title: "Grind season",      desc: "Play 20 matches",    reward: { kind: "passxp", amount: 150 } },
];

function json(b: unknown, s = 200) { return new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } }); }
function dayKey() { return new Date().toISOString().slice(0, 10); }
function weekKey() {
  const d = new Date();
  const u = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const day = u.getUTCDay() || 7;
  u.setUTCDate(u.getUTCDate() + 4 - day);
  const ys = new Date(Date.UTC(u.getUTCFullYear(), 0, 1));
  const wk = Math.ceil((((u.getTime() - ys.getTime()) / 86400000) + 1) / 7);
  return u.getUTCFullYear() + "-W" + String(wk).padStart(2, "0");
}
function keyFor(scope: string) { return scope === "weekly" ? weekKey() : dayKey(); }

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "POST only" }, 405);
  const url = Deno.env.get("SUPABASE_URL")!, key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const admin = createClient(url, key, { auth: { persistSession: false } });
  const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return json({ ok: false, error: "sign in required" }, 401);
  const { data: ud, error: ue } = await admin.auth.getUser(jwt);
  const user = ud?.user; if (ue || !user) return json({ ok: false, error: "invalid session" }, 401);
  const uid = user.id;
  let body: Record<string, unknown> = {}; try { body = await req.json(); } catch { /* */ }
  const action = String(body.action || "get");

  async function statsFor(pk: string) {
    const { data } = await admin.from("ak_period_stats").select("*").eq("user_id", uid).eq("period_key", pk).maybeSingle();
    return data || { user_id: uid, period_key: pk, matches: 0, wins: 0, gates: 0, donates: 0, chats: 0 };
  }
  async function bump(pk: string, d: Record<string, number>) {
    const s = await statsFor(pk);
    const row: Record<string, unknown> = { user_id: uid, period_key: pk, updated_at: new Date().toISOString() };
    ["matches", "wins", "gates", "donates", "chats"].forEach((m) => { row[m] = Math.min(CAP, (s[m] || 0) + (d[m] || 0)); });
    await admin.from("ak_period_stats").upsert(row);
  }

  try {
    if (action === "report-match") {
      const won = !!body.won, gates = Math.max(0, Math.min(4, parseInt(String(body.gates || 0), 10) || 0));
      const d = { matches: 1, wins: won ? 1 : 0, gates: gates, donates: 0, chats: 0 };
      await bump(dayKey(), d); await bump(weekKey(), d);
      return json({ ok: true });
    }
    if (action === "report-event") {
      const metric = String(body.metric || ""); const n = Math.max(1, Math.min(20, parseInt(String(body.n || 1), 10) || 1));
      if (["donates", "chats"].indexOf(metric) < 0) return json({ ok: false, error: "bad metric" }, 400);
      const d: Record<string, number> = { donates: 0, chats: 0 }; d[metric] = n;
      await bump(dayKey(), d); await bump(weekKey(), d);
      return json({ ok: true });
    }
    if (action === "get") {
      const day = await statsFor(dayKey()), week = await statsFor(weekKey());
      const { data: claims } = await admin.from("ak_quest_claims").select("quest_id,period_key").eq("user_id", uid);
      const claimedSet = new Set((claims || []).map((c) => c.quest_id + "|" + c.period_key));
      const list = QUESTS.map((q) => {
        const stats = q.scope === "weekly" ? week : day;
        const pk = keyFor(q.scope);
        const prog = Math.min(q.target, stats[q.metric] || 0);
        const claimed = claimedSet.has(q.id + "|" + pk);
        return { id: q.id, scope: q.scope, title: q.title, desc: q.desc, target: q.target, progress: prog, reward: q.reward, claimed: claimed, claimable: prog >= q.target && !claimed };
      });
      return json({ ok: true, quests: list, day_key: dayKey(), week_key: weekKey() });
    }
    if (action === "claim") {
      const qid = String(body.quest_id || "");
      const q = QUESTS.find((x) => x.id === qid);
      if (!q) return json({ ok: false, error: "no such quest" }, 400);
      const pk = keyFor(q.scope);
      const stats = await statsFor(pk);
      if ((stats[q.metric] || 0) < q.target) return json({ ok: false, error: "not complete" }, 403);
      // claim ledger guards double-claim (PK conflict)
      const { error: cerr } = await admin.from("ak_quest_claims").insert({ user_id: uid, quest_id: qid, period_key: pk });
      if (cerr) return json({ ok: false, error: "already claimed" }, 409);
      const r = q.reward as Record<string, unknown>;
      if (r.kind === "passxp") {
        const { data: pp } = await admin.from("ak_pass_progress").select("*").eq("user_id", uid).maybeSingle();
        const cur = pp || { season: 1, xp: 0, claimed_free: [], claimed_prem: [], premium: false, daily_xp: 0, daily_day: null };
        const xp = Math.min(PASS_MAX_TIER * PASS_XP_PER, (cur.xp || 0) + (Number(r.amount) || 0));
        const tier = Math.max(0, Math.min(PASS_MAX_TIER, Math.floor(xp / PASS_XP_PER)));
        await admin.from("ak_pass_progress").upsert({
          user_id: uid, season: cur.season || 1, xp, tier, premium: !!cur.premium,
          claimed_free: cur.claimed_free || [], claimed_prem: cur.claimed_prem || [],
          daily_xp: cur.daily_xp || 0, daily_day: cur.daily_day || null, updated_at: new Date().toISOString(),
        });
        return json({ ok: true, reward: r, passxp: r.amount, tier });
      }
      await admin.from("ak_grants").insert({ user_id: uid, kind: r.kind, card_id: r.card_id || null, rarity: r.rarity || null, amount: Number(r.amount) || 1, source: "quest", note: "Hit List: " + q.title });
      return json({ ok: true, reward: r });
    }
    return json({ ok: false, error: "unknown action" }, 400);
  } catch (e) { return json({ ok: false, error: String((e as Error)?.message || e) }, 500); }
});
