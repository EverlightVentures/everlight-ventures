// ak-crew -- Alley Kingz crews (clans) server-authoritative edge function.
// Mirrors the alley-kingz-shop pattern: the CLIENT posts an INTENT {action, ...},
// the SERVER (service role) is the only writer and enforces every rule. RLS blocks
// all direct client writes, so this function is the sole path to mutate crews.
//
// Actions: create | join | leave | mine | list
// Auth: caller's Supabase JWT in the Authorization: Bearer header is verified;
//       the user's auth.uid is the identity for every membership row.
//
// Targets AK's OWN project only (SUPABASE_URL/SERVICE_ROLE injected at runtime).
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const FACTIONS = ["boneguard_crew", "zoomie_syndicate", "leashbreak_tactix", "k9_circuitry"];
const MAX_MEMBERS = 50;

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "POST only" }, 405);

  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const admin = createClient(url, serviceKey, { auth: { persistSession: false } });

  // verify the caller
  const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return json({ ok: false, error: "sign in required" }, 401);
  const { data: udata, error: uerr } = await admin.auth.getUser(jwt);
  const user = udata?.user;
  if (uerr || !user) return json({ ok: false, error: "invalid session" }, 401);
  const uid = user.id;

  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch { /* empty */ }
  const action = String(body.action || "");

  try {
    if (action === "mine") {
      const { data: m } = await admin.from("ak_crew_members").select("crew_id, role").eq("user_id", uid).maybeSingle();
      if (!m) return json({ ok: true, crew: null });
      const { data: crew } = await admin.from("ak_crews").select("*").eq("id", m.crew_id).maybeSingle();
      const { data: members } = await admin.from("ak_crew_members")
        .select("user_id, role, donated_week, received_week, fame_week, last_seen").eq("crew_id", m.crew_id);
      return json({ ok: true, crew, role: m.role, members: members || [] });
    }

    if (action === "list") {
      const q = String(body.q || "").trim().slice(0, 40);
      let sel = admin.from("ak_crews").select("id,name,tag,faction,crest,description,privacy,req_trophies,trophies,member_count")
        .order("trophies", { ascending: false }).limit(50);
      if (q) sel = sel.ilike("name", `%${q}%`);
      const { data } = await sel;
      return json({ ok: true, crews: data || [] });
    }

    if (action === "create") {
      // anti-spam gate the SERVER can enforce (gold cost deferred until economy is server-side):
      // (1) signed in, (2) not already in a crew, (3) valid name/tag/faction.
      const name = String(body.name || "").trim().slice(0, 24);
      const tag = String(body.tag || "").trim().toUpperCase().slice(0, 4);
      const faction = String(body.faction || "");
      const description = String(body.description || "").trim().slice(0, 200);
      const privacy = ["open", "request", "closed"].includes(String(body.privacy)) ? String(body.privacy) : "open";
      if (name.length < 3) return json({ ok: false, error: "name too short" }, 400);
      if (tag.length < 2) return json({ ok: false, error: "tag must be 2-4 chars" }, 400);
      if (!FACTIONS.includes(faction)) return json({ ok: false, error: "pick a faction" }, 400);

      const { data: existing } = await admin.from("ak_crew_members").select("crew_id").eq("user_id", uid).maybeSingle();
      if (existing) return json({ ok: false, error: "leave your current crew first" }, 409);

      const { data: crew, error: cerr } = await admin.from("ak_crews").insert({
        name, tag, faction, description, privacy, created_by: uid, member_count: 1,
      }).select().single();
      if (cerr) {
        if (String(cerr.message).includes("duplicate")) return json({ ok: false, error: "that crew name is taken" }, 409);
        throw cerr;
      }
      await admin.from("ak_crew_members").insert({ crew_id: crew.id, user_id: uid, role: "leader" });
      return json({ ok: true, crew, role: "leader" });
    }

    if (action === "join") {
      const crewId = String(body.crew_id || "");
      if (!crewId) return json({ ok: false, error: "crew_id required" }, 400);
      const { data: existing } = await admin.from("ak_crew_members").select("crew_id").eq("user_id", uid).maybeSingle();
      if (existing) return json({ ok: false, error: "leave your current crew first" }, 409);
      const { data: crew } = await admin.from("ak_crews").select("*").eq("id", crewId).maybeSingle();
      if (!crew) return json({ ok: false, error: "crew not found" }, 404);
      if (crew.member_count >= MAX_MEMBERS) return json({ ok: false, error: "crew is full" }, 409);

      if (crew.privacy === "closed") return json({ ok: false, error: "crew is closed" }, 403);
      if (crew.privacy === "request") {
        await admin.from("ak_crew_requests").upsert({ crew_id: crewId, user_id: uid, status: "pending" },
          { onConflict: "crew_id,user_id" });
        return json({ ok: true, requested: true });
      }
      // open crew -> instant join
      await admin.from("ak_crew_members").insert({ crew_id: crewId, user_id: uid, role: "member" });
      await admin.from("ak_crews").update({ member_count: crew.member_count + 1 }).eq("id", crewId);
      return json({ ok: true, crew, role: "member" });
    }

    if (action === "leave") {
      const { data: m } = await admin.from("ak_crew_members").select("crew_id, role").eq("user_id", uid).maybeSingle();
      if (!m) return json({ ok: true, left: true });
      await admin.from("ak_crew_members").delete().eq("user_id", uid);
      const { count } = await admin.from("ak_crew_members").select("user_id", { count: "exact", head: true }).eq("crew_id", m.crew_id);
      if (!count) {
        await admin.from("ak_crews").delete().eq("id", m.crew_id); // last one out -> crew dissolves
      } else {
        await admin.from("ak_crews").update({ member_count: count }).eq("id", m.crew_id);
        if (m.role === "leader") { // hand the crown to the longest-tenured remaining member
          const { data: heir } = await admin.from("ak_crew_members").select("user_id")
            .eq("crew_id", m.crew_id).order("joined_at", { ascending: true }).limit(1).maybeSingle();
          if (heir) await admin.from("ak_crew_members").update({ role: "leader" }).eq("crew_id", m.crew_id).eq("user_id", heir.user_id);
        }
      }
      return json({ ok: true, left: true });
    }

    // ---- DONATIONS: the "carry your weight" loop --------------------------
    // Clash-style: donating is FREE for the donor (cards are granted from
    // nothing, not deducted) and rewards the donor with gold. Grants are queued
    // to ak_grants and applied client-side via AK_ECON on next claim.
    const REQ_MAX = 8, PER_FILL_MAX = 4, DONOR_GOLD = 20, REQ_TTL_H = 6;

    async function myMembership() {
      const { data } = await admin.from("ak_crew_members").select("crew_id, donated_week, received_week").eq("user_id", uid).maybeSingle();
      return data;
    }

    if (action === "don-list") {
      const mem = await myMembership();
      if (!mem) return json({ ok: true, requests: [] });
      const { data } = await admin.from("ak_donation_requests")
        .select("id,user_id,card_id,qty_req,qty_filled,requester_name,expires_at,created_at")
        .eq("crew_id", mem.crew_id).gt("expires_at", new Date().toISOString())
        .order("created_at", { ascending: false }).limit(40);
      const open = (data || []).filter((r) => r.qty_filled < r.qty_req);
      return json({ ok: true, requests: open });
    }

    if (action === "don-request") {
      const mem = await myMembership();
      if (!mem) return json({ ok: false, error: "join a crew first" }, 403);
      const cardId = String(body.card_id || "").trim().slice(0, 64);
      if (!cardId) return json({ ok: false, error: "pick a card" }, 400);
      const qtyReq = Math.max(1, Math.min(REQ_MAX, parseInt(String(body.qty_req || REQ_MAX), 10) || REQ_MAX));
      // one open request at a time
      const { data: openReq } = await admin.from("ak_donation_requests")
        .select("id,qty_req,qty_filled").eq("user_id", uid).gt("expires_at", new Date().toISOString());
      if ((openReq || []).some((r) => r.qty_filled < r.qty_req)) return json({ ok: false, error: "you already have an open request" }, 409);
      const reqName = String(body.name || "").trim().slice(0, 24) || "Stray";
      const expires = new Date(Date.now() + REQ_TTL_H * 3600 * 1000).toISOString();
      const { data: row, error: rerr } = await admin.from("ak_donation_requests")
        .insert({ crew_id: mem.crew_id, user_id: uid, card_id: cardId, qty_req: qtyReq, requester_name: reqName, expires_at: expires })
        .select().single();
      if (rerr) return json({ ok: false, error: String(rerr.message) }, 500);
      return json({ ok: true, request: row });
    }

    if (action === "don-fill") {
      const mem = await myMembership();
      if (!mem) return json({ ok: false, error: "join a crew first" }, 403);
      const reqId = String(body.request_id || "");
      const { data: rq } = await admin.from("ak_donation_requests").select("*").eq("id", reqId).maybeSingle();
      if (!rq) return json({ ok: false, error: "request not found" }, 404);
      if (rq.crew_id !== mem.crew_id) return json({ ok: false, error: "not your crew" }, 403);
      if (rq.user_id === uid) return json({ ok: false, error: "that's your own request" }, 409);
      if (new Date(rq.expires_at) <= new Date()) return json({ ok: false, error: "request expired" }, 409);
      const remaining = rq.qty_req - rq.qty_filled;
      if (remaining <= 0) return json({ ok: false, error: "already full" }, 409);
      const want = parseInt(String(body.qty || PER_FILL_MAX), 10) || PER_FILL_MAX;
      const fill = Math.max(1, Math.min(want, PER_FILL_MAX, remaining));

      await admin.from("ak_donations").insert({ crew_id: rq.crew_id, request_id: rq.id, donor_id: uid, recipient_id: rq.user_id, card_id: rq.card_id, qty: fill });
      await admin.from("ak_donation_requests").update({ qty_filled: rq.qty_filled + fill }).eq("id", rq.id);
      // queue grants: recipient gets the cards, donor gets gold
      await admin.from("ak_grants").insert([
        { user_id: rq.user_id, kind: "card", card_id: rq.card_id, amount: fill, source: "donation", note: "Crew donation: " + rq.card_id },
        { user_id: uid, kind: "gold", amount: DONOR_GOLD, source: "donation", note: "Thanks for donating" },
      ]);
      // weekly counters + crew aggregate (best-effort)
      await admin.from("ak_crew_members").update({ donated_week: (mem.donated_week || 0) + fill }).eq("user_id", uid);
      const { data: rmem } = await admin.from("ak_crew_members").select("received_week").eq("user_id", rq.user_id).maybeSingle();
      if (rmem) await admin.from("ak_crew_members").update({ received_week: (rmem.received_week || 0) + fill }).eq("user_id", rq.user_id);
      const { data: crew } = await admin.from("ak_crews").select("donations_week").eq("id", rq.crew_id).maybeSingle();
      if (crew) await admin.from("ak_crews").update({ donations_week: (crew.donations_week || 0) + fill }).eq("id", rq.crew_id);
      return json({ ok: true, filled: fill, reward_gold: DONOR_GOLD });
    }

    // ---- GRANTS INBOX: claim queued server grants (donations now; pass/quests later)
    if (action === "claim-grants") {
      const { data: grants } = await admin.from("ak_grants")
        .select("id,kind,card_id,rarity,amount,source,note").eq("user_id", uid).eq("claimed", false)
        .order("created_at", { ascending: true }).limit(100);
      if (!grants || !grants.length) return json({ ok: true, grants: [] });
      const ids = grants.map((g) => g.id);
      await admin.from("ak_grants").update({ claimed: true }).in("id", ids);
      return json({ ok: true, grants: grants });
    }

    return json({ ok: false, error: "unknown action" }, 400);
  } catch (e) {
    return json({ ok: false, error: String((e as Error)?.message || e) }, 500);
  }
});
