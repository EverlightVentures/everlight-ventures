// ak-cosmetics -- Alley Kingz "The Drop" cosmetic shop + ownership.
// Server records OWNERSHIP (persists); the catalog's visual recipes live in
// drip.js. Daily rotation is deterministic by date so every player sees the same
// Drop with a shared countdown. Gold is deducted client-side (cosmetic, low stakes).
//
// Actions: get | buy
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
// id -> gold price. Must stay in sync with the drip.js CATALOG (visuals there).
// kinds: style_* (card skins) | board_* (arena themes) | emote_* (battle emotes)
const PRICES: Record<string, number> = {
  style_gilded: 800, style_neon: 600, style_toxic: 600,
  style_shadow: 500, style_frost: 700, style_inferno: 900,
  board_noir: 400, board_vapor: 500, board_bloodmoon: 600,
  emote_woof: 200, emote_crown: 300, emote_gg: 200, emote_skull: 250,
};
const IDS = Object.keys(PRICES);
const DROP_SIZE = 5;

function json(b: unknown, s = 200) { return new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } }); }
function dayKey() { return new Date().toISOString().slice(0, 10); }
// deterministic daily rotation: hash the date, rotate the id list, take DROP_SIZE
function rotation() {
  let h = 0; const d = dayKey();
  for (let i = 0; i < d.length; i++) h = (h * 31 + d.charCodeAt(i)) >>> 0;
  const start = h % IDS.length;
  const out = [];
  for (let i = 0; i < Math.min(DROP_SIZE, IDS.length); i++) out.push(IDS[(start + i) % IDS.length]);
  return out;
}
function secsToMidnightUTC() {
  const now = new Date();
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1, 0, 0, 0));
  return Math.max(0, Math.floor((end.getTime() - now.getTime()) / 1000));
}

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

  try {
    if (action === "get") {
      const { data: owned } = await admin.from("ak_owned_cosmetics").select("cosmetic_id").eq("user_id", uid);
      // gems for the lobby currency header (read-only; the shop's game_currencies table)
      const { data: gemRow } = await admin.from("game_currencies").select("balance").eq("player_id", uid).eq("game_id", "alley-kingz").eq("currency_name", "gems").maybeSingle();
      return json({ ok: true, owned: (owned || []).map((o) => o.cosmetic_id), rotation: rotation(), prices: PRICES, resets_in: secsToMidnightUTC(), gems: gemRow ? Number(gemRow.balance) : 0 });
    }
    if (action === "buy") {
      const id = String(body.id || "");
      if (!PRICES[id]) return json({ ok: false, error: "no such item" }, 400);
      const { data: have } = await admin.from("ak_owned_cosmetics").select("cosmetic_id").eq("user_id", uid).eq("cosmetic_id", id).maybeSingle();
      if (have) return json({ ok: false, error: "already owned" }, 409);
      const { error } = await admin.from("ak_owned_cosmetics").insert({ user_id: uid, cosmetic_id: id, source: "shop" });
      if (error) return json({ ok: false, error: String(error.message) }, 500);
      return json({ ok: true, id: id, price: PRICES[id] });
    }
    return json({ ok: false, error: "unknown action" }, 400);
  } catch (e) { return json({ ok: false, error: String((e as Error)?.message || e) }, 500); }
});
