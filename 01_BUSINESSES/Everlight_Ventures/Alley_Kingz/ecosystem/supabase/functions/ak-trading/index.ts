// ak-trading -- Alley Kingz "The Trading Post" server-authoritative barter edge fn.
// Keeper: "Switch the Broker" in THE_YARDS. Mirrors ak-crew EXACTLY: the CLIENT posts
// an INTENT {action, ...}, the SERVER (service role) is the only writer, RLS blocks all
// direct client writes, so this fn is the sole path to mutate ak_trade_listings.
//
// Actions: list | post | accept | cancel | mine | claim-grants
// Auth: caller's Supabase JWT in Authorization: Bearer is verified; auth.uid is identity.
//
// SERVER-AUTHORITATIVE ESCROW (soft items ONLY):
//   Inventory lives client-side (ak_profile localStorage, economy.js) today, so a
//   LIST/ACCEPT deducts locally up front (the "deposit"); this server records the
//   listing, matchmakes, and DELIVERS only via the existing ak_grants rail. The server
//   NEVER trusts a client to mint -- it only ever GRANTS. A failed call refunds
//   client-side, so the net is always conservative (dupe-proof by construction).
//   // TODO-SERVER: when the economy moves server-side, the deposit becomes a real
//   // server-held escrow and the gold tax a server debit.
//
// HARD LAW (re-enforced here, belt + suspenders to the client selects):
//   FORBID = kind 'gems'  OR  rarity 'Mythic'  OR  card_id ~ /\$|bcardd|alk/i
//            OR a give card flagged capture-origin (provenance = p.captures).
//   Soft goods ONLY: give kind 'card' (cosmetic reserved); want kind 'gold'|'scrap'|'card'.
//   DAILY <= 5 (posts seller_id=uid + accepts filled_by=uid, last 24h).
//   BAND match on list/accept (band = floor(trophies/400), client-supplied).
//
// Targets AK's OWN project only (mfghdobptredxxhbjwyz; SUPABASE_URL/SERVICE_ROLE injected).
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// economy knobs -- MIRROR trading.js constants (the server re-enforces these).
const DAILY_CAP = 5;          // posts + accepts per rolling 24h
const BAND_SIZE = 400;        // trophy-band width (informational; band is client-supplied)
const LIST_LIMIT = 50;        // max board rows returned
const GIVE_KINDS = ["card"];                 // cosmetic reserved -- not grantable/deliverable yet
const WANT_KINDS = ["gold", "scrap", "card"];
const TRADE_RARITIES = ["Common", "Rare", "Epic", "Legendary"]; // Mythic NEVER tradeable
// sane upper bounds so a tampered client can't list an absurd ask (pure anti-abuse).
const MAX_GOLD = 100000, MAX_SCRAP = 999, MAX_CARD_QTY = 10;
const FORBID_RE = /\$|bcardd|alk/i;          // RMT / securities line -- $BCARDD + ALK hard-blocked

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
}
function nowISO() { return new Date().toISOString(); }
function isoAgo(hours: number) { return new Date(Date.now() - hours * 3600 * 1000).toISOString(); }

type Item = { kind?: string; card_id?: string; rarity?: string; amount?: number; captured?: boolean; capture_only?: boolean; origin?: string };

// ---- HARD-LAW guard: returns an error string if the item is forbidden, else "" ----
function forbidItem(it: Item | null, side: "give" | "want"): string {
  if (!it || typeof it !== "object") return "missing " + side;
  const kind = String(it.kind || "");
  if (kind === "gems") return "gems are never tradeable";
  // rarity gate (Mythic is prestige + the $BCARDD card -- never tradeable on either leg)
  if (it.rarity && String(it.rarity) === "Mythic") return "Mythic cards are never tradeable";
  // $BCARDD / ALK / any $ token -- the RMT + securities line
  if (it.card_id && FORBID_RE.test(String(it.card_id))) return "that asset can't be traded";
  if (side === "give") {
    if (!GIVE_KINDS.includes(kind)) return kind === "cosmetic" ? "cosmetic trades not enabled yet" : "you can only give a card";
    // capture-origin copies are NON-tradeable (provenance = p.captures). The client does
    // not flag this yet (inventory is client-side); honor any flag it sends, forward-compat.
    // // TODO-SERVER: full enforcement when inventory is server-held + p.captures is readable.
    if (it.captured === true || it.capture_only === true || String(it.origin) === "capture") return "captured cards can't be traded";
  } else {
    if (!WANT_KINDS.includes(kind)) return "you can want gold, scrap, or a card";
    if (kind === "scrap" && it.rarity && !TRADE_RARITIES.includes(String(it.rarity))) return "bad scrap rarity";
  }
  return "";
}

// normalize + bound an item into safe DB columns (defends against a tampered client).
function normGive(it: Item) {
  return {
    kind: "card",
    card_id: String(it.card_id || "").slice(0, 64),
    rarity: it.rarity ? String(it.rarity).slice(0, 16) : null,
    amount: Math.max(1, Math.min(MAX_CARD_QTY, parseInt(String(it.amount ?? 1), 10) || 1)),
  };
}
function normWant(it: Item) {
  const kind = String(it.kind || "");
  if (kind === "gold") return { kind, card_id: null, rarity: null, amount: Math.max(1, Math.min(MAX_GOLD, parseInt(String(it.amount ?? 0), 10) || 0)) };
  if (kind === "scrap") return { kind, card_id: null, rarity: String(it.rarity || "Common").slice(0, 16), amount: Math.max(1, Math.min(MAX_SCRAP, parseInt(String(it.amount ?? 0), 10) || 0)) };
  return { kind: "card", card_id: String(it.card_id || "").slice(0, 64), rarity: it.rarity ? String(it.rarity).slice(0, 16) : null, amount: Math.max(1, Math.min(MAX_CARD_QTY, parseInt(String(it.amount ?? 1), 10) || 1)) };
}
// shape a DB row -> the nested {give,want} the client (trading.js) renders.
function rowToListing(r: Record<string, unknown>) {
  return {
    id: r.id, seller_id: r.seller_id, seller_name: r.seller_name,
    give: { kind: r.give_kind, card_id: r.give_card_id, rarity: r.give_rarity, amount: r.give_amount },
    want: { kind: r.want_kind, card_id: r.want_card_id, rarity: r.want_rarity, amount: r.want_amount },
    band: r.band, status: r.status, expires_at: r.expires_at, created_at: r.created_at,
  };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ ok: false, error: "POST only" }, 405);

  const url = Deno.env.get("SUPABASE_URL")!;
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const admin = createClient(url, serviceKey, { auth: { persistSession: false } });

  // verify the caller (same block as ak-crew)
  const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return json({ ok: false, error: "sign in required" }, 401);
  const { data: udata, error: uerr } = await admin.auth.getUser(jwt);
  const user = udata?.user;
  if (uerr || !user) return json({ ok: false, error: "invalid session" }, 401);
  const uid = user.id;

  let body: Record<string, unknown> = {};
  try { body = await req.json(); } catch { /* empty */ }
  const action = String(body.action || "");

  // rolling-24h activity gate the server CAN enforce (posts + accepts).
  async function dailyCount(): Promise<number> {
    const since = isoAgo(24);
    const { count: posts } = await admin.from("ak_trade_listings")
      .select("id", { count: "exact", head: true }).eq("seller_id", uid).gt("created_at", since);
    const { count: accepts } = await admin.from("ak_trade_listings")
      .select("id", { count: "exact", head: true }).eq("filled_by", uid).gt("filled_at", since);
    return (posts || 0) + (accepts || 0);
  }

  try {
    // ----- LIST: open offers in my band, not mine -------------------------- //
    if (action === "list") {
      const band = parseInt(String(body.band ?? 0), 10) || 0;
      // sanitize the search term -> letters/digits/space only, so it can never inject
      // into the PostgREST `or` filter (commas/parens/dots are filter syntax). Client
      // sends q:"" on the board today; this just hardens the optional path.
      const q = String(body.q || "").replace(/[^a-zA-Z0-9 ]/g, "").trim().slice(0, 40);
      let sel = admin.from("ak_trade_listings").select("*")
        .eq("status", "open").eq("band", band).neq("seller_id", uid)
        .gt("expires_at", nowISO())
        .order("created_at", { ascending: false }).limit(LIST_LIMIT);
      if (q) sel = sel.or(`give_card_id.ilike.%${q}%,want_card_id.ilike.%${q}%`);
      const { data } = await sel;
      return json({ ok: true, listings: (data || []).map(rowToListing) });
    }

    // ----- MINE: my own open offers ---------------------------------------- //
    if (action === "mine") {
      const { data } = await admin.from("ak_trade_listings").select("*")
        .eq("seller_id", uid).eq("status", "open")
        .order("created_at", { ascending: false }).limit(LIST_LIMIT);
      return json({ ok: true, listings: (data || []).map(rowToListing) });
    }

    // ----- POST: list a card (client already deducted give + gold fee) ----- //
    if (action === "post") {
      const give = body.give as Item, want = body.want as Item;
      const gErr = forbidItem(give, "give"); if (gErr) return json({ ok: false, error: gErr }, 400);
      const wErr = forbidItem(want, "want"); if (wErr) return json({ ok: false, error: wErr }, 400);
      if (await dailyCount() >= DAILY_CAP) return json({ ok: false, error: "daily trade cap reached (" + DAILY_CAP + ")" }, 429);

      const band = parseInt(String(body.band ?? 0), 10) || 0;
      const name = String(body.name || "Stray").trim().slice(0, 24) || "Stray";
      const g = normGive(give), w = normWant(want);
      if (!g.card_id) return json({ ok: false, error: "pick a card to give" }, 400);
      if (w.kind === "card" && !w.card_id) return json({ ok: false, error: "pick the card you want" }, 400);

      const { data: row, error: ierr } = await admin.from("ak_trade_listings").insert({
        seller_id: uid, seller_name: name,
        give_kind: g.kind, give_card_id: g.card_id, give_rarity: g.rarity, give_amount: g.amount,
        want_kind: w.kind, want_card_id: w.card_id, want_rarity: w.rarity, want_amount: w.amount,
        band, status: "open",
      }).select().single();
      if (ierr) return json({ ok: false, error: String(ierr.message) }, 500);
      return json({ ok: true, listing: rowToListing(row) });
    }

    // ----- ACCEPT: atomic claim; deliver GIVE now, seller's WANT via inbox -- //
    if (action === "accept") {
      const listingId = String(body.listing_id || "");
      if (!listingId) return json({ ok: false, error: "listing_id required" }, 400);
      const band = parseInt(String(body.band ?? 0), 10) || 0;
      if (await dailyCount() >= DAILY_CAP) return json({ ok: false, error: "daily trade cap reached (" + DAILY_CAP + ")" }, 429);

      const { data: L } = await admin.from("ak_trade_listings").select("*").eq("id", listingId).maybeSingle();
      if (!L) return json({ ok: false, error: "offer not found" }, 404);
      if (L.seller_id === uid) return json({ ok: false, error: "that's your own offer" }, 409);
      if (L.status !== "open") return json({ ok: false, error: "offer no longer open" }, 409);
      if (new Date(L.expires_at) <= new Date()) return json({ ok: false, error: "offer expired" }, 409);
      if ((L.band | 0) !== band) return json({ ok: false, error: "offer is in a different trophy band" }, 409);
      // re-run the HARD-LAW guard on the stored legs (defends against a row that predates a rule).
      const gErr = forbidItem(rowToListing(L).give, "give"); if (gErr) return json({ ok: false, error: gErr }, 400);
      const wErr = forbidItem(rowToListing(L).want, "want"); if (wErr) return json({ ok: false, error: wErr }, 400);

      // atomic compare-and-swap: only the first acceptor flips open -> filled.
      const { data: upd } = await admin.from("ak_trade_listings")
        .update({ status: "filled", filled_by: uid, filled_at: nowISO() })
        .eq("id", listingId).eq("status", "open").select();
      if (!upd || !upd.length) return json({ ok: false, error: "offer was just taken" }, 409);

      const giveGrant = { kind: "card", card_id: L.give_card_id, rarity: L.give_rarity, amount: L.give_amount };
      const wantGrant: Record<string, unknown> = { kind: L.want_kind, amount: L.want_amount };
      if (L.want_kind === "card") wantGrant.card_id = L.want_card_id;
      if (L.want_kind === "scrap") wantGrant.rarity = L.want_rarity;

      // Ledger BOTH legs in ak_grants. The acceptor's GIVE is returned in this response
      // and applied client-side IMMEDIATELY, so its row is marked claimed=true (audit only,
      // never re-delivered). The seller's WANT is claimed=false -> they pull it via
      // claim-grants next session. This is dupe-proof: nothing is ever delivered twice.
      await admin.from("ak_grants").insert([
        { user_id: uid, kind: giveGrant.kind, card_id: giveGrant.card_id, rarity: giveGrant.rarity, amount: giveGrant.amount, source: "trade", note: "Trade: received " + (giveGrant.card_id || "card"), claimed: true },
        { user_id: L.seller_id, kind: String(wantGrant.kind), card_id: (wantGrant.card_id as string) || null, rarity: (wantGrant.rarity as string) || null, amount: Number(wantGrant.amount) || 0, source: "trade", note: "Trade: your offer sold", claimed: false },
      ]);
      return json({ ok: true, grants: [giveGrant] });
    }

    // ----- CANCEL: seller pulls an open offer; refund the deposited GIVE ---- //
    if (action === "cancel") {
      const listingId = String(body.listing_id || "");
      if (!listingId) return json({ ok: false, error: "listing_id required" }, 400);
      const { data: L } = await admin.from("ak_trade_listings").select("*").eq("id", listingId).maybeSingle();
      if (!L) return json({ ok: false, error: "offer not found" }, 404);
      if (L.seller_id !== uid) return json({ ok: false, error: "not your offer" }, 403);
      if (L.status !== "open") return json({ ok: false, error: "offer is not open" }, 409);

      // atomic: only flip if still open (loses a race with a simultaneous accept -> reject).
      const { data: upd } = await admin.from("ak_trade_listings")
        .update({ status: "cancelled" }).eq("id", listingId).eq("status", "open").select();
      if (!upd || !upd.length) return json({ ok: false, error: "offer was just taken" }, 409);

      const refund = { kind: "card", card_id: L.give_card_id, rarity: L.give_rarity, amount: L.give_amount };
      // refund is returned + applied immediately client-side -> ledger row claimed=true (note:
      // the gold listing fee is a SINK, never refunded -- only the deposited card comes back).
      await admin.from("ak_grants").insert([
        { user_id: uid, kind: refund.kind, card_id: refund.card_id, rarity: refund.rarity, amount: refund.amount, source: "trade", note: "Trade: offer pulled (card returned)", claimed: true },
      ]);
      return json({ ok: true, grants: [refund] });
    }

    // ----- CLAIM-GRANTS: identical to ak-crew (pull the inbox) ------------- //
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
