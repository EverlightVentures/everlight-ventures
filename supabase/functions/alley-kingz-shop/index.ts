// ============================================================================
// alley-kingz-shop  --  server-authoritative Alley Kingz shop + economy API
// ============================================================================
// Author: Amara Osei (Iron Stack / SaaS Factory). Date: 2026-06-07.
//
// WHY THIS EXISTS / THREAT MODEL:
//   The browser is hostile. It may NOT self-grant currency, copies, or levels.
//   This function (service-role key, bypasses RLS) is the ONLY writer of the AK
//   player-state tables. Every spend is validated against the DB before any
//   grant. The client sends an intent ("buy card 0007"); the server decides.
//
// LEGAL POSTURE (Lane A only -- see MONETIZATION_LEGAL_LANES.md):
//   * Everything sold here is IN-GAME VALUE ONLY. No balance is ever cashable.
//   * Deterministic Card Shop (buy-card) ships: spend matching-rarity Scrap for
//     the EXACT card. NO RNG.
//   * Lucky Draw (open-draw) is the LANE-A loot box: PAY + CHANCE + IN-GAME-ONLY
//     prize. This is the COD/PUBG model -- the prize is an in-game card grant
//     that is NEVER cashable and is NEVER a tradeable NFT. Odds are disclosed to
//     the client and pity (soft + hard) is server-enforced. Legal precisely
//     because the prize has no cash value -- that is how it is built, not a bolt-on.
//   * Random/odds CHESTS remain deterministic-or-gated separately; the cashable
//     B-CARDD BET sweeps is a SEPARATE Lane-B product and is NOT in this function.
//   * No pay-to-win: levels cap at 10; the stat curve lives in the engine.
//
// STRIPE = TEST MODE (fail-closed):
//   buy-gems / confirm-gems refuse to run against a LIVE key while AK_SHOP_TEST_MODE
//   is on. No live charge is possible from this code until an operator flips the
//   flag with a reviewed key. Every checkout response carries a TEST-MODE disclaimer.
//
// ACTIONS (POST { action, player_id, ... }):
//   get-shop        -> catalog + level costs + the player's snapshot (no writes)
//   buy-card        -> { card_id } deterministic: spend scrap -> +1 copy. NO RNG.
//   open-chest      -> { chest_id } deterministic chests grant fixed contents.
//   level-up-card   -> { card_id } spend copies(+scrap substitute)+coins, level+1
//   level-up-tower  -> { tower_id } spend tower copies+coins, level+1
//   buy-gems        -> { sku } -> create-checkout (TEST) -> Stripe URL
//   confirm-gems    -> { session_id } credit gems after a verified TEST session (idempotent)
//   top-off-card    -> { card_id } Gem shortcut: buy the EXACT missing copies for
//                      the next level. Deterministic (NO RNG), in-game copies only.
//   open-draw       -> { pulls } Lane-A loot box: spend Gems, roll the disclosed
//                      odds with soft+hard pity, grant a RANDOM IN-GAME card.
//                      Never cash, never an NFT. Server-authoritative.
// ============================================================================

import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";
import { SUPABASE_URL, corsHeaders, postSlack } from "../_shared/mod.ts";

const GAME_ID = "alley-kingz"; // canonical AK namespace (matches live NOS rows)
const DISCLAIMER =
  "TEST MODE -- no real charges. Gems and all items are in-game value only.";

const STRIPE_KEY = Deno.env.get("STRIPE_SECRET_KEY") ?? "";
const TEST_MODE = (Deno.env.get("AK_SHOP_TEST_MODE") ?? "true") !== "false";
const SERVICE_KEY = Deno.env.get("SB_SERVICE_ROLE_KEY") ?? "";

// ---- Lucky Draw config (Lane A loot box: PAY + CHANCE + IN-GAME-ONLY prize) ----
// The COD/PUBG model. Every prize is an in-game card grant; it is NEVER cashable
// and NEVER a tradeable NFT (the NFT mint is a separate deterministic track).
// Odds below are the disclosed "Drop Rates" echoed to the client via get-shop.draw.
const DRAW = {
  cost_gems: 100, // single pull
  cost_gems_10: 900, // 10-pull (one pull free)
  featured_card: "0001", // $BCARDD -- the featured Mythic on the banner
  odds: { Mythic: 0.01, Legendary: 0.04, Epic: 0.15, Rare: 0.35, Common: 0.45 },
  soft_pity_start: 30, // Mythic chance starts ramping after this many dry pulls
  soft_pity_step: 0.10, // +10pp Mythic chance per pull past the soft-pity start
  hard_pity_mythic: 40, // guaranteed Mythic by this pull (counter resets on a Mythic)
  legendary_floor: 10, // guaranteed Legendary-or-better at least every 10 pulls
};
const RARITY_ORDER = ["Common", "Rare", "Epic", "Legendary", "Mythic"];
// Deterministic Gem top-off price per missing copy, by rarity (Lane A, no RNG).
const GEM_PER_COPY: Record<string, number> = {
  Common: 2, Rare: 10, Epic: 50, Legendary: 500, Mythic: 2000,
};

function reply(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// Fail-closed Stripe guard: in TEST_MODE we refuse a LIVE key outright.
function liveBlocked(): Response | null {
  if (TEST_MODE && STRIPE_KEY.startsWith("sk_live_")) {
    return reply({
      ok: false,
      error: "LIVE_STRIPE_BLOCKED",
      message:
        "AK_SHOP_TEST_MODE is on but a LIVE Stripe key is configured. Live charges " +
        "require an operator + legal go-live. No charge attempted.",
    }, 403);
  }
  return null;
}

const admin = () => createClient(SUPABASE_URL, SERVICE_KEY);

// ---- currency helpers (game_currencies, namespaced to AK) ------------------
// Reads all AK currencies for a player in ONE query -> a {name: balance} map.
async function loadCurrencies(
  db: ReturnType<typeof admin>,
  playerId: string,
): Promise<Record<string, number>> {
  const { data } = await db
    .from("game_currencies")
    .select("currency_name, balance")
    .eq("player_id", playerId)
    .eq("game_id", GAME_ID);
  const map: Record<string, number> = {};
  for (const row of data ?? []) map[row.currency_name] = Number(row.balance);
  return map;
}

// Apply a set of currency deltas (upsert per touched currency). Few rows, not N+1.
async function applyCurrencyDeltas(
  db: ReturnType<typeof admin>,
  playerId: string,
  current: Record<string, number>,
  deltas: Record<string, number>,
): Promise<void> {
  for (const [name, delta] of Object.entries(deltas)) {
    if (!delta) continue;
    const next = (current[name] ?? 0) + delta;
    await db.from("game_currencies").upsert(
      {
        player_id: playerId,
        game_id: GAME_ID,
        currency_name: name,
        balance: next,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "player_id,game_id,currency_name" },
    );
    current[name] = next;
  }
}

// Set currencies to ABSOLUTE values (used for pity counters, which are stored as
// pseudo-currencies in game_currencies -- no schema change, no migration).
async function setCurrencies(
  db: ReturnType<typeof admin>,
  playerId: string,
  values: Record<string, number>,
  current?: Record<string, number>,
): Promise<void> {
  for (const [name, val] of Object.entries(values)) {
    await db.from("game_currencies").upsert(
      {
        player_id: playerId,
        game_id: GAME_ID,
        currency_name: name,
        balance: val,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "player_id,game_id,currency_name" },
    );
    if (current) current[name] = val;
  }
}

async function logTx(
  db: ReturnType<typeof admin>,
  row: Record<string, unknown>,
): Promise<{ ok: boolean; conflict: boolean }> {
  const { error } = await db.from("ak_transactions").insert(row);
  if (error) {
    // 23505 = unique_violation on stripe_event_id -> already processed
    const conflict = (error as { code?: string }).code === "23505";
    return { ok: false, conflict };
  }
  return { ok: true, conflict: false };
}

// ============================================================================
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return reply({ ok: false, error: "POST only" }, 405);

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return reply({ ok: false, error: "invalid json" }, 400);
  }

  const action = String(body.action ?? "");
  const playerId = body.player_id ? String(body.player_id) : "";
  const db = admin();

  try {
    // ---------------------------------------------------------------- get-shop
    if (action === "get-shop") {
      const [products, catalog, costs] = await Promise.all([
        db.from("ak_shop_products").select("*").eq("active", true).order("sort_order"),
        db.from("ak_card_catalog").select("*").eq("active", true).order("card_id"),
        db.from("ak_level_costs").select("*"),
      ]);

      let player: Record<string, unknown> | null = null;
      if (playerId) {
        const [cur, inv, towers, chests] = await Promise.all([
          loadCurrencies(db, playerId),
          db.from("ak_card_inventory").select("card_id, copies, level").eq("player_id", playerId),
          db.from("ak_tower_levels").select("tower_id, copies, level").eq("player_id", playerId),
          db.from("ak_chest_inventory").select("chest_id, qty").eq("player_id", playerId).gt("qty", 0),
        ]);
        player = {
          currencies: cur,
          inventory: inv.data ?? [],
          towers: towers.data ?? [],
          chests: chests.data ?? [],
        };
      }

      return reply({
        ok: true,
        test_mode: TEST_MODE,
        disclaimer: DISCLAIMER,
        products: products.data ?? [],
        catalog: catalog.data ?? [],
        level_costs: costs.data ?? [],
        player,
        // Lucky Draw is LIVE (Lane A loot box). Disclosed odds + pity for the UI.
        draw: {
          live: true,
          cost_gems: DRAW.cost_gems,
          cost_gems_10: DRAW.cost_gems_10,
          featured_card: DRAW.featured_card,
          odds: DRAW.odds,
          soft_pity_start: DRAW.soft_pity_start,
          hard_pity_mythic: DRAW.hard_pity_mythic,
          legendary_floor: DRAW.legendary_floor,
          prize_type: "in-game-card",
          cashable: false,
          nft: false,
        },
        gem_per_copy: GEM_PER_COPY,
        legal: {
          lane: "A",
          cashable: false,
          gacha_live: true,
          draw_prize: "in-game-card-only",
          note:
            "All items are in-game value only. The Lucky Draw grants in-game cards " +
            "only -- never cash, never a tradeable NFT.",
        },
      });
    }

    // -------------------------------------------------------------- (auth gate)
    if (!playerId) return reply({ ok: false, error: "player_id required" }, 400);

    // --------------------------------------------------------------- buy-card
    // Deterministic: spend matching-rarity Scrap Tokens -> exactly +1 copy. NO RNG.
    if (action === "buy-card") {
      const cardId = String(body.card_id ?? "");
      const { data: card } = await db
        .from("ak_card_catalog").select("*").eq("card_id", cardId).maybeSingle();
      if (!card || !card.active) return reply({ ok: false, error: "CARD_NOT_FOUND" }, 404);

      const scrapName = `scrap_${card.rarity}`;
      const price = Number(card.card_shop_price);
      const cur = await loadCurrencies(db, playerId);
      if ((cur[scrapName] ?? 0) < price) {
        return reply({
          ok: false, error: "INSUFFICIENT_SCRAP",
          need: { [scrapName]: price }, have: { [scrapName]: cur[scrapName] ?? 0 },
        }, 402);
      }

      await applyCurrencyDeltas(db, playerId, cur, { [scrapName]: -price });

      // +1 copy (upsert; create the row at level 1 if first copy)
      const { data: inv } = await db
        .from("ak_card_inventory").select("copies, level")
        .eq("player_id", playerId).eq("card_id", cardId).maybeSingle();
      const copies = (inv?.copies ?? 0) + 1;
      await db.from("ak_card_inventory").upsert(
        { player_id: playerId, card_id: cardId, copies, level: inv?.level ?? 1,
          updated_at: new Date().toISOString() },
        { onConflict: "player_id,card_id" });

      await logTx(db, {
        player_id: playerId, action: "buy-card", sku: cardId,
        currency_deltas: { [scrapName]: -price }, card_deltas: { [cardId]: 1 },
      });
      return reply({ ok: true, card_id: cardId, copies, level: inv?.level ?? 1,
        balances: cur });
    }

    // ------------------------------------------------------------- open-chest
    // Deterministic chests grant FIXED contents. Random (is_random) chests are GATED.
    if (action === "open-chest") {
      const chestId = String(body.chest_id ?? "");
      const { data: prod } = await db
        .from("ak_shop_products").select("*").eq("sku", chestId).eq("kind", "chest").maybeSingle();
      if (!prod) return reply({ ok: false, error: "CHEST_NOT_FOUND" }, 404);

      if (prod.is_random) {
        // Random crates are not a separate surface yet -- the Lucky Draw is the
        // live odds-based experience. Steer the player there (no scary gate copy).
        return reply({
          ok: false, gated: true, error: "USE_LUCKY_DRAW",
          message: "This crate is coming soon. Pull the Lucky Draw for odds-based rewards.",
        }, 200);
      }

      const { data: chestInv } = await db
        .from("ak_chest_inventory").select("qty")
        .eq("player_id", playerId).eq("chest_id", chestId).maybeSingle();
      if (!chestInv || chestInv.qty <= 0) return reply({ ok: false, error: "NO_CHEST_OWNED" }, 400);

      // Apply fixed grants: coins, scrap_*, and optional card_copies map.
      const grants = (prod.grants ?? {}) as Record<string, unknown>;
      const curDeltas: Record<string, number> = {};
      const cardDeltas: Record<string, number> = {};
      for (const [k, v] of Object.entries(grants)) {
        if (k === "card_copies" && v && typeof v === "object") {
          for (const [cid, n] of Object.entries(v as Record<string, number>)) cardDeltas[cid] = Number(n);
        } else if (k === "coins" || k.startsWith("scrap_") || k === "gems") {
          curDeltas[k] = Number(v);
        }
      }
      const cur = await loadCurrencies(db, playerId);
      await applyCurrencyDeltas(db, playerId, cur, curDeltas);

      for (const [cid, n] of Object.entries(cardDeltas)) {
        const { data: inv } = await db.from("ak_card_inventory").select("copies, level")
          .eq("player_id", playerId).eq("card_id", cid).maybeSingle();
        await db.from("ak_card_inventory").upsert(
          { player_id: playerId, card_id: cid, copies: (inv?.copies ?? 0) + n,
            level: inv?.level ?? 1, updated_at: new Date().toISOString() },
          { onConflict: "player_id,card_id" });
      }

      await db.from("ak_chest_inventory")
        .update({ qty: chestInv.qty - 1, updated_at: new Date().toISOString() })
        .eq("player_id", playerId).eq("chest_id", chestId);

      await logTx(db, { player_id: playerId, action: "open-chest", sku: chestId,
        currency_deltas: curDeltas, card_deltas: cardDeltas });
      return reply({ ok: true, chest_id: chestId, granted: { currencies: curDeltas, cards: cardDeltas },
        balances: cur, chest_qty_left: chestInv.qty - 1 });
    }

    // ---------------------------------------------------------- level-up-card
    // Spend copies (+ matching-rarity scrap to cover any shortfall, 1:1) + coins.
    if (action === "level-up-card") {
      const cardId = String(body.card_id ?? "");
      const { data: card } = await db.from("ak_card_catalog").select("rarity").eq("card_id", cardId).maybeSingle();
      if (!card) return reply({ ok: false, error: "CARD_NOT_FOUND" }, 404);

      const { data: inv } = await db.from("ak_card_inventory").select("copies, level")
        .eq("player_id", playerId).eq("card_id", cardId).maybeSingle();
      if (!inv) return reply({ ok: false, error: "CARD_NOT_OWNED" }, 404);
      if (inv.level >= 10) return reply({ ok: false, error: "MAX_LEVEL" }, 409);

      const { data: cost } = await db.from("ak_level_costs").select("copies_required, coins_required")
        .eq("entity_type", "card").eq("rarity", card.rarity).eq("from_level", inv.level).maybeSingle();
      if (!cost) return reply({ ok: false, error: "COST_BAND_MISSING" }, 500);

      const cur = await loadCurrencies(db, playerId);
      const scrapName = `scrap_${card.rarity}`;
      const useCopies = Math.min(inv.copies, cost.copies_required);
      const shortfall = cost.copies_required - useCopies;          // covered by scrap 1:1
      const coinsHave = cur["coins"] ?? 0;
      const scrapHave = cur[scrapName] ?? 0;

      if (shortfall > scrapHave || cost.coins_required > coinsHave) {
        return reply({
          ok: false, error: "INSUFFICIENT_FUNDS",
          need: { copies: cost.copies_required, coins: cost.coins_required, [`${scrapName}_substitute`]: shortfall },
          have: { copies: inv.copies, coins: coinsHave, [scrapName]: scrapHave },
        }, 402);
      }

      const curDeltas: Record<string, number> = { coins: -cost.coins_required };
      if (shortfall > 0) curDeltas[scrapName] = -shortfall;
      await applyCurrencyDeltas(db, playerId, cur, curDeltas);

      const newLevel = inv.level + 1;
      await db.from("ak_card_inventory")
        .update({ copies: inv.copies - useCopies, level: newLevel, updated_at: new Date().toISOString() })
        .eq("player_id", playerId).eq("card_id", cardId);

      await logTx(db, { player_id: playerId, action: "level-up-card", sku: cardId,
        currency_deltas: curDeltas, card_deltas: { [cardId]: -useCopies } });
      return reply({ ok: true, card_id: cardId, level: newLevel, copies: inv.copies - useCopies, balances: cur });
    }

    // --------------------------------------------------------- level-up-tower
    if (action === "level-up-tower") {
      const towerId = String(body.tower_id ?? "");
      if (!["crown", "left_garrison", "right_garrison"].includes(towerId))
        return reply({ ok: false, error: "TOWER_NOT_FOUND" }, 404);

      const { data: row } = await db.from("ak_tower_levels").select("copies, level")
        .eq("player_id", playerId).eq("tower_id", towerId).maybeSingle();
      const level = row?.level ?? 1;
      const haveCopies = row?.copies ?? 0;
      if (level >= 10) return reply({ ok: false, error: "MAX_LEVEL" }, 409);

      const { data: cost } = await db.from("ak_level_costs").select("copies_required, coins_required")
        .eq("entity_type", "tower").is("rarity", null).eq("from_level", level).maybeSingle();
      if (!cost) return reply({ ok: false, error: "COST_BAND_MISSING" }, 500);

      const cur = await loadCurrencies(db, playerId);
      const coinsHave = cur["coins"] ?? 0;
      if (haveCopies < cost.copies_required || coinsHave < cost.coins_required) {
        return reply({ ok: false, error: "INSUFFICIENT_FUNDS",
          need: { tower_copies: cost.copies_required, coins: cost.coins_required },
          have: { tower_copies: haveCopies, coins: coinsHave } }, 402);
      }

      await applyCurrencyDeltas(db, playerId, cur, { coins: -cost.coins_required });
      const newLevel = level + 1;
      await db.from("ak_tower_levels").upsert(
        { player_id: playerId, tower_id: towerId, copies: haveCopies - cost.copies_required,
          level: newLevel, updated_at: new Date().toISOString() },
        { onConflict: "player_id,tower_id" });

      await logTx(db, { player_id: playerId, action: "level-up-tower", sku: towerId,
        currency_deltas: { coins: -cost.coins_required } });
      return reply({ ok: true, tower_id: towerId, level: newLevel, balances: cur });
    }

    // --------------------------------------------------------------- buy-gems
    // Routes to the existing create-checkout edge fn (TEST). Crediting = confirm-gems.
    if (action === "buy-gems") {
      const blocked = liveBlocked();
      if (blocked) return blocked;

      const sku = String(body.sku ?? "");
      const { data: prod } = await db.from("ak_shop_products").select("*")
        .eq("sku", sku).eq("kind", "gems").maybeSingle();
      if (!prod || !prod.checkout_slug)
        return reply({ ok: false, error: "GEM_SKU_NOT_FOUND" }, 404);

      // Server-to-server call into create-checkout (reuse, do not rebuild Stripe).
      const res = await fetch(`${SUPABASE_URL}/functions/v1/create-checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${SERVICE_KEY}` },
        body: JSON.stringify({
          slug: prod.checkout_slug,
          success_url: body.success_url,
          cancel_url: body.cancel_url,
          metadata: { player_id: playerId, game_id: GAME_ID, ak_sku: sku },
        }),
      });
      const out = await res.json();
      if (!res.ok || !out.url) {
        return reply({
          ok: false, error: "CHECKOUT_UNAVAILABLE", test_mode: TEST_MODE,
          detail: out.error ??
            `create-checkout has no TEST price ID for slug '${prod.checkout_slug}'. Add it before this SKU resolves.`,
        }, 502);
      }
      return reply({ ok: true, test_mode: TEST_MODE, disclaimer: DISCLAIMER,
        url: out.url, session_id: out.session_id, gems: (prod.grants as Record<string, number>)?.gems });
    }

    // ------------------------------------------------------------ confirm-gems
    // Credit gems after a verified TEST checkout session. Idempotent on session id.
    if (action === "confirm-gems") {
      const blocked = liveBlocked();
      if (blocked) return blocked;
      if (!STRIPE_KEY) return reply({ ok: false, error: "STRIPE_NOT_CONFIGURED", test_mode: TEST_MODE }, 503);

      const sessionId = String(body.session_id ?? "");
      const stripe = new Stripe(STRIPE_KEY, {
        apiVersion: "2023-10-16", httpClient: Stripe.createFetchHttpClient(),
      });
      const session = await stripe.checkout.sessions.retrieve(sessionId);
      if (session.payment_status !== "paid")
        return reply({ ok: false, error: "PAYMENT_NOT_COMPLETED", status: session.payment_status }, 402);

      const sku = String(session.metadata?.ak_sku ?? "");
      const { data: prod } = await db.from("ak_shop_products").select("grants")
        .eq("sku", sku).maybeSingle();
      const gems = Number((prod?.grants as Record<string, number>)?.gems ?? 0);
      if (!gems) return reply({ ok: false, error: "NO_GEM_GRANT_FOR_SKU" }, 400);

      // The unique txn row IS the idempotency lock (uq_ak_tx_stripe_event).
      const claim = await logTx(db, {
        player_id: playerId, action: "confirm-gems", sku,
        currency_deltas: { gems }, stripe_session_id: sessionId,
        stripe_event_id: `gems:${sessionId}`,
      });
      if (claim.conflict) {
        const cur = await loadCurrencies(db, playerId);
        return reply({ ok: true, already_credited: true, gem_balance: cur["gems"] ?? 0 });
      }

      const cur = await loadCurrencies(db, playerId);
      await applyCurrencyDeltas(db, playerId, cur, { gems });
      const slackUrl = Deno.env.get("SLACK_WEBHOOK_URL");
      if (slackUrl) await postSlack(`[TEST] AK gems credited: ${gems} to ${playerId}`, slackUrl);
      return reply({ ok: true, test_mode: TEST_MODE, gems_added: gems, gem_balance: cur["gems"] ?? 0 });
    }

    // ------------------------------------------------------------ top-off-card
    // Gem shortcut (Lane A, NO RNG): buy the EXACT missing copies for the next
    // level. Grants in-game copies only -- never cash, never an NFT.
    if (action === "top-off-card") {
      const cardId = String(body.card_id ?? "");
      const { data: card } = await db.from("ak_card_catalog").select("rarity").eq("card_id", cardId).maybeSingle();
      if (!card) return reply({ ok: false, error: "CARD_NOT_FOUND" }, 404);

      const { data: inv } = await db.from("ak_card_inventory").select("copies, level")
        .eq("player_id", playerId).eq("card_id", cardId).maybeSingle();
      if (!inv) return reply({ ok: false, error: "CARD_NOT_OWNED" }, 404);
      if (inv.level >= 10) return reply({ ok: false, error: "MAX_LEVEL" }, 409);

      const { data: cost } = await db.from("ak_level_costs").select("copies_required")
        .eq("entity_type", "card").eq("rarity", card.rarity).eq("from_level", inv.level).maybeSingle();
      if (!cost) return reply({ ok: false, error: "COST_BAND_MISSING" }, 500);

      const missing = Math.max(0, Number(cost.copies_required) - Number(inv.copies));
      if (missing <= 0) return reply({ ok: false, error: "NO_TOPOFF_NEEDED", copies: inv.copies }, 200);

      const perCopy = GEM_PER_COPY[card.rarity] ?? 50;
      const gemCost = missing * perCopy;
      const cur = await loadCurrencies(db, playerId);
      if ((cur["gems"] ?? 0) < gemCost) {
        return reply({ ok: false, error: "INSUFFICIENT_GEMS",
          need: { gems: gemCost }, have: { gems: cur["gems"] ?? 0 } }, 402);
      }

      await applyCurrencyDeltas(db, playerId, cur, { gems: -gemCost });
      const copies = Number(inv.copies) + missing;
      await db.from("ak_card_inventory")
        .update({ copies, updated_at: new Date().toISOString() })
        .eq("player_id", playerId).eq("card_id", cardId);

      await logTx(db, { player_id: playerId, action: "top-off-card", sku: cardId,
        currency_deltas: { gems: -gemCost }, card_deltas: { [cardId]: missing } });
      return reply({ ok: true, card_id: cardId, copies, copies_added: missing,
        gems_spent: gemCost, balances: cur });
    }

    // --------------------------------------------------------------- open-draw
    // LANE-A LOOT BOX (COD/PUBG). PAY (gems) + CHANCE (disclosed odds + pity) +
    // IN-GAME-ONLY PRIZE (a card copy granted to inventory). The prize is NEVER
    // cashable and is NEVER a tradeable NFT -- that no-cash-value property is what
    // keeps this legal, and it is enforced here on the server, not in the UI.
    if (action === "open-draw") {
      const pulls = Math.max(1, Math.min(10, Number(body.pulls ?? 1)));
      const gemCost = pulls >= 10 ? DRAW.cost_gems_10 : DRAW.cost_gems * pulls;

      const cur = await loadCurrencies(db, playerId);
      if ((cur["gems"] ?? 0) < gemCost) {
        return reply({ ok: false, error: "INSUFFICIENT_GEMS",
          need: { gems: gemCost }, have: { gems: cur["gems"] ?? 0 } }, 402);
      }

      // The prize pool is the live in-game card catalog, grouped by rarity.
      const { data: poolRows } = await db.from("ak_card_catalog")
        .select("card_id, name, rarity").eq("active", true);
      const pool = poolRows ?? [];
      if (!pool.length) return reply({ ok: false, error: "EMPTY_CATALOG" }, 500);
      const byRarity: Record<string, { card_id: string; name: string }[]> = {};
      for (const c of pool) (byRarity[c.rarity] ??= []).push({ card_id: c.card_id, name: c.name });

      // Pity counters live as pseudo-currencies (no schema change).
      let pityM = Number(cur["draw_pity_m"] ?? 0);
      let pityL = Number(cur["draw_pity_l"] ?? 0);
      let total = Number(cur["draw_total"] ?? 0);

      function rollRarity(): string {
        pityM += 1; pityL += 1; total += 1;
        let rarity: string;
        if (pityM >= DRAW.hard_pity_mythic) {
          rarity = "Mythic"; // hard pity: guaranteed Mythic
        } else {
          let mChance = DRAW.odds.Mythic;
          if (pityM > DRAW.soft_pity_start) {
            mChance = Math.min(1, DRAW.odds.Mythic + (pityM - DRAW.soft_pity_start) * DRAW.soft_pity_step);
          }
          if (Math.random() < mChance) {
            rarity = "Mythic";
          } else if (pityL >= DRAW.legendary_floor) {
            rarity = "Legendary"; // 10-pull Legendary floor
          } else {
            const tiers: [string, number][] = [
              ["Legendary", DRAW.odds.Legendary], ["Epic", DRAW.odds.Epic],
              ["Rare", DRAW.odds.Rare], ["Common", DRAW.odds.Common],
            ];
            const sum = tiers.reduce((a, [, w]) => a + w, 0);
            let x = Math.random() * sum, acc = 0;
            rarity = "Common";
            for (const [name, w] of tiers) { acc += w; if (x < acc) { rarity = name; break; } }
          }
        }
        if (rarity === "Mythic") { pityM = 0; pityL = 0; }
        else if (rarity === "Legendary") { pityL = 0; }
        return rarity;
      }

      const results: { card_id: string; name: string; rarity: string }[] = [];
      const cardDeltas: Record<string, number> = {};
      for (let i = 0; i < pulls; i++) {
        let rarity = rollRarity();
        let bucket = byRarity[rarity];
        if (!bucket || !bucket.length) { // defensive: step down to a populated tier
          for (let j = RARITY_ORDER.indexOf(rarity) - 1; j >= 0; j--) {
            const b = byRarity[RARITY_ORDER[j]];
            if (b && b.length) { bucket = b; rarity = RARITY_ORDER[j]; break; }
          }
        }
        if (!bucket || !bucket.length) continue;
        const card = bucket[Math.floor(Math.random() * bucket.length)];
        cardDeltas[card.card_id] = (cardDeltas[card.card_id] ?? 0) + 1;
        results.push({ card_id: card.card_id, name: card.name, rarity });
      }

      // Charge gems, persist pity, grant in-game copies.
      await applyCurrencyDeltas(db, playerId, cur, { gems: -gemCost });
      await setCurrencies(db, playerId, { draw_pity_m: pityM, draw_pity_l: pityL, draw_total: total }, cur);

      for (const [cid, n] of Object.entries(cardDeltas)) {
        const { data: inv } = await db.from("ak_card_inventory").select("copies, level")
          .eq("player_id", playerId).eq("card_id", cid).maybeSingle();
        await db.from("ak_card_inventory").upsert(
          { player_id: playerId, card_id: cid, copies: (inv?.copies ?? 0) + n,
            level: inv?.level ?? 1, updated_at: new Date().toISOString() },
          { onConflict: "player_id,card_id" });
      }

      await logTx(db, { player_id: playerId, action: "open-draw", sku: `draw:${pulls}`,
        currency_deltas: { gems: -gemCost }, card_deltas: cardDeltas });

      return reply({
        ok: true, test_mode: TEST_MODE,
        prize_type: "in-game-card", cashable: false, nft: false,
        pulls, gems_spent: gemCost, results,
        pity: {
          mythic: pityM, legendary: pityL, total,
          hard_pity_mythic: DRAW.hard_pity_mythic, legendary_floor: DRAW.legendary_floor,
        },
        balances: cur,
      });
    }

    return reply({ ok: false, error: `unknown action '${action}'` }, 400);
  } catch (err: unknown) {
    console.error("alley-kingz-shop error:", err);
    return reply({ ok: false, error: (err as Error).message ?? "internal error" }, 500);
  }
});
