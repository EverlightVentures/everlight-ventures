// ak-chat -- Alley Kingz world + crew chat, server-authoritative send.
// SEND goes through here so the server can rate-limit, profanity-filter, ban-check,
// strip links (anti-scam, matches $BCARDD "no links" posture), and INSERT the row.
// RECEIVE is client-side via Supabase Realtime Postgres Changes on ak_chat_messages
// (RLS already scopes crew rows to members) -- not handled here.
//
// Actions: send | history
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const MAX_LEN = 200;
const RATE_WINDOW_MS = 60_000;   // 1 minute
const RATE_MAX = 20;             // 20 msgs / min
const MIN_GAP_MS = 1_500;        // >= 1.5s between messages
// light mask list (extend server-side; positive-vibes posture)
const BAD = ["fuck", "shit", "bitch", "nigger", "faggot", "cunt", "retard"];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}
function clean(s: string, scope: string): string {
  let out = s;
  if (scope === "world") out = out.replace(/https?:\/\/\S+|\b[\w.-]+\.(com|net|io|xyz|gg|co|app|fun|link)\S*/gi, "[link removed]");
  for (const w of BAD) out = out.replace(new RegExp(w, "gi"), (m) => "*".repeat(m.length));
  return out.trim();
}

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
  const action = String(body.action || "send");
  const scope = body.scope === "crew" ? "crew" : "world";

  // resolve the caller's crew (for crew scope + name/faction stamp)
  const { data: m } = await admin.from("ak_crew_members").select("crew_id").eq("user_id", uid).maybeSingle();
  const crewId = m?.crew_id || null;

  if (action === "history") {
    let sel = admin.from("ak_chat_messages").select("id,scope,crew_id,user_id,name,faction,body,created_at")
      .eq("scope", scope).order("created_at", { ascending: false }).limit(50);
    if (scope === "crew") {
      if (!crewId) return json({ ok: true, messages: [] });
      sel = sel.eq("crew_id", crewId);
    }
    const { data } = await sel;
    return json({ ok: true, messages: (data || []).reverse() });
  }

  if (action === "send") {
    // ban-check
    const { data: ban } = await admin.from("ak_chat_bans").select("until").eq("user_id", uid).maybeSingle();
    if (ban && (!ban.until || new Date(ban.until) > new Date())) {
      return json({ ok: false, error: "you are muted", until: ban.until }, 403);
    }
    if (scope === "crew" && !crewId) return json({ ok: false, error: "join a crew to use crew chat" }, 403);

    let text = String(body.body || "").slice(0, MAX_LEN);
    text = clean(text, scope);
    if (!text) return json({ ok: false, error: "empty message" }, 400);

    // rate-limit: inspect this user's recent sends
    const since = new Date(Date.now() - RATE_WINDOW_MS).toISOString();
    const { data: recent } = await admin.from("ak_chat_messages")
      .select("created_at").eq("user_id", uid).gte("created_at", since).order("created_at", { ascending: false });
    if (recent && recent.length >= RATE_MAX) return json({ ok: false, error: "slow down" }, 429);
    if (recent && recent[0] && (Date.now() - new Date(recent[0].created_at).getTime()) < MIN_GAP_MS) {
      return json({ ok: false, error: "slow down" }, 429);
    }

    const name = String(body.name || "").trim().slice(0, 24) || "Stray";
    const faction = body.faction ? String(body.faction).slice(0, 24) : null;
    const { data: row, error: ierr } = await admin.from("ak_chat_messages")
      .insert({ scope, crew_id: scope === "crew" ? crewId : null, user_id: uid, name, faction, body: text })
      .select().single();
    if (ierr) return json({ ok: false, error: String(ierr.message) }, 500);
    return json({ ok: true, message: row });
  }

  return json({ ok: false, error: "unknown action" }, 400);
});
