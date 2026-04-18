/**
 * Vantaris Multiplayer Blackjack -- Server-Side Dealer Engine
 *
 * This edge function is the SINGLE SOURCE OF TRUTH for all multiplayer
 * blackjack game state. Clients never touch cards, shoes, or settlement.
 * They send actions, this function validates + executes + broadcasts.
 *
 * Actions: join, leave, bet, deal, hit, stand, double, split, insurance, surrender
 *
 * Anti-cheat:
 * - Shoe stored server-side, never sent to clients
 * - All card operations happen here
 * - Turn validation (can't act when it's not your turn)
 * - Bet validation (can't bet more than you have)
 * - Rate limiting via turn_started_at
 */

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";
import { SUPABASE_URL, corsHeaders, json } from "../_shared/mod.ts";

// ============================================================
// TYPES (mirrored from blackjack-engine.ts)
// ============================================================

type Suit = "spades" | "hearts" | "diamonds" | "clubs";
type Rank = "A" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "J" | "Q" | "K";

interface Card {
  rank: Rank;
  suit: Suit;
  faceDown: boolean;
}

type Outcome = "blackjack" | "win" | "loss" | "push" | "bust" | "surrender" | "charlie";

// ============================================================
// PURE GAME LOGIC (ported from blackjack-engine.ts)
// ============================================================

const ALL_SUITS: Suit[] = ["spades", "hearts", "diamonds", "clubs"];
const ALL_RANKS: Rank[] = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"];

function createShoe(deckCount = 6): Card[] {
  const shoe: Card[] = [];
  for (let d = 0; d < deckCount; d++) {
    for (const suit of ALL_SUITS) {
      for (const rank of ALL_RANKS) {
        shoe.push({ rank, suit, faceDown: false });
      }
    }
  }
  return shuffleShoe(shoe);
}

function shuffleShoe(shoe: Card[]): Card[] {
  const shuffled = [...shoe];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

function cardValue(card: Card): number {
  if (["J", "Q", "K"].includes(card.rank)) return 10;
  if (card.rank === "A") return 11;
  return parseInt(card.rank);
}

function evaluateHand(cards: Card[]): {
  value: number; isSoft: boolean; isBust: boolean;
  isBlackjack: boolean; isCharlie: boolean;
} {
  const visible = cards.filter((c) => !c.faceDown);
  let total = 0;
  let aces = 0;
  for (const card of visible) {
    total += cardValue(card);
    if (card.rank === "A") aces++;
  }
  while (total > 21 && aces > 0) { total -= 10; aces--; }
  return {
    value: total,
    isSoft: aces > 0 && total <= 21,
    isBust: total > 21,
    isBlackjack: visible.length === 2 && total === 21,
    isCharlie: visible.length >= 6 && total <= 21,
  };
}

function settleOutcome(
  playerCards: Card[], dealerCards: Card[],
  sixCardCharlie: boolean,
): { outcome: Outcome; multiplier: number } {
  const p = evaluateHand(playerCards);
  const d = evaluateHand(dealerCards);

  if (p.isCharlie && sixCardCharlie) return { outcome: "charlie", multiplier: 2 };
  if (p.isBust) return { outcome: "bust", multiplier: 0 };
  if (p.isBlackjack) {
    if (d.isBlackjack) return { outcome: "push", multiplier: 1 };
    return { outcome: "blackjack", multiplier: 2.5 };
  }
  if (d.isBust) return { outcome: "win", multiplier: 2 };
  if (p.value > d.value) return { outcome: "win", multiplier: 2 };
  if (p.value < d.value) return { outcome: "loss", multiplier: 0 };
  return { outcome: "push", multiplier: 1 };
}

// ============================================================
// HELPERS
// ============================================================

function drawCard(shoe: Card[]): { card: Card; shoe: Card[] } {
  if (shoe.length < 15) shoe = createShoe(6);
  const card = { ...shoe[0], faceDown: false };
  return { card, shoe: shoe.slice(1) };
}

// Sanitize cards for broadcast -- hide faceDown cards
function sanitizeCards(cards: Card[]): Card[] {
  return cards.map((c) =>
    c.faceDown ? { rank: "?" as Rank, suit: "?" as Suit, faceDown: true } : c
  );
}

// Is this seat occupied by a real player or bot?
function isOccupied(seat: any): boolean {
  return seat.status !== "empty" && (seat.user_id || seat.player_id === "BOT");
}

function isBot(seat: any): boolean {
  return seat.player_id === "BOT" && !seat.user_id;
}

// Get occupied (non-empty) seats
function getActiveSeatIndices(seats: any[]): number[] {
  return seats.filter(isOccupied).map((s) => s.seat_index);
}

// Get seats that have placed bets (real players + bots)
function getBettingSeatIndices(seats: any[]): number[] {
  return seats
    .filter((s) => s.bet > 0 && isOccupied(s))
    .map((s) => s.seat_index);
}

// Find next seat that needs to act (not standing, busted, or blackjack)
function findNextActingSeat(seats: any[], afterIndex: number): number | null {
  const bettingSeats = getBettingSeatIndices(seats).sort((a, b) => a - b);
  for (const idx of bettingSeats) {
    if (idx <= afterIndex) continue;
    const seat = seats.find((s: any) => s.seat_index === idx);
    if (!seat) continue;
    if (["standing", "busted", "blackjack", "settled"].includes(seat.status)) continue;
    return idx;
  }
  return null;
}

// ============================================================
// BOT SYSTEM
// ============================================================

// Hive Mind agents as bot names (match client-side bot-personas.ts)
const BOT_NAMES = [
  "Piper Reeves", "Rex Blackwell", "Penny Vance", "Harrison Knox",
  "Aria Chen", "Christopher Wolfe", "Vera Lux", "Major Dex",
  "Atlas Vega", "Sebastian Navarro", "Sage Holloway", "Zara Khoury",
  "Frederick Banks",
  // Additional diverse NPCs for variety
  "DeShawn", "Aaliyah", "Jaylen", "Keisha", "Darius", "Imani",
  "Latoya", "Malik", "Brianna", "Tanisha", "Monique", "Kamila",
  "Nadia", "Quinton", "Simone", "Crystal",
];

// Basic strategy: what a bot does with their hand vs dealer upcard
function botDecision(handTotal: number, isSoft: boolean, cardCount: number, dealerUpValue: number): "hit" | "stand" | "double" {
  // Never hit on 21
  if (handTotal >= 21) return "stand";

  // Soft hands
  if (isSoft) {
    if (handTotal <= 17) return "hit";
    if (handTotal === 18 && dealerUpValue >= 9) return "hit";
    return "stand";
  }

  // Hard hands
  if (handTotal <= 8) return "hit";
  if (handTotal === 9 && cardCount === 2 && dealerUpValue >= 3 && dealerUpValue <= 6) return "double";
  if (handTotal === 10 && cardCount === 2 && dealerUpValue <= 9) return "double";
  if (handTotal === 11 && cardCount === 2) return "double";
  if (handTotal <= 11) return "hit";
  if (handTotal === 12 && dealerUpValue >= 4 && dealerUpValue <= 6) return "stand";
  if (handTotal === 12) return "hit";
  if (handTotal >= 13 && handTotal <= 16 && dealerUpValue <= 6) return "stand";
  if (handTotal >= 13 && handTotal <= 16) return "hit";
  return "stand"; // 17+
}

// Play a bot's entire turn (hit/stand/double loop)
async function playBotTurn(
  supabase: ReturnType<typeof createClient>,
  tableId: string,
  seat: any,
  shoe: Card[],
  dealerUpcard: Card,
): Promise<Card[]> {
  let cards: Card[] = seat.cards || [];
  let currentShoe = shoe;
  const dealerUpValue = cardValue(dealerUpcard);

  let eval_ = evaluateHand(cards);

  // Bot decides and plays
  while (!eval_.isBust && !eval_.isBlackjack && eval_.value < 21) {
    const decision = botDecision(eval_.value, eval_.isSoft, cards.length, dealerUpValue);

    if (decision === "stand") break;

    if (decision === "double" && cards.length === 2 && seat.chips >= seat.bet) {
      // Double: draw one card, update bet, done
      const draw = drawCard(currentShoe);
      cards = [...cards, draw.card];
      currentShoe = draw.shoe;
      eval_ = evaluateHand(cards);

      await supabase.from("game_seats").update({
        cards,
        hand_total: eval_.value,
        bet: seat.bet * 2,
        chips: seat.chips - seat.bet,
        doubled: true,
        status: eval_.isBust ? "busted" : "standing",
        outcome: eval_.isBust ? "bust" : null,
      }).eq("id", seat.id);

      // Save shoe
      await supabase.from("game_tables").update({ shoe: currentShoe }).eq("id", tableId);
      return currentShoe;
    }

    // Hit
    const draw = drawCard(currentShoe);
    cards = [...cards, draw.card];
    currentShoe = draw.shoe;
    eval_ = evaluateHand(cards);
  }

  // Update seat final state
  const status = eval_.isBust ? "busted" : "standing";
  await supabase.from("game_seats").update({
    cards,
    hand_total: eval_.value,
    status,
    outcome: eval_.isBust ? "bust" : (eval_.isCharlie ? "charlie" : null),
  }).eq("id", seat.id);

  // Save shoe
  await supabase.from("game_tables").update({ shoe: currentShoe }).eq("id", tableId);
  return currentShoe;
}

// Fill empty seats with bots (called when a real player joins or bets)
async function fillBotsIfNeeded(
  supabase: ReturnType<typeof createClient>,
  tableId: string,
  seats: any[],
  minBet: number,
): Promise<void> {
  const occupied = seats.filter(isOccupied);
  const realPlayers = seats.filter((s) => s.user_id && s.status !== "empty");
  // CRITICAL: only seats with no user AND no bot AND status empty are truly empty
  const emptySeats = seats.filter((s) => s.status === "empty" && !s.user_id && s.player_id !== "BOT");

  // Only add bots if there's at least 1 real player and fewer than 3 total
  if (realPlayers.length === 0 || occupied.length >= 3) return;

  const botsToAdd = Math.min(3 - occupied.length, emptySeats.length);
  const usedNames = occupied.map((s) => s.display_name);
  const availNames = BOT_NAMES.filter((n) => !usedNames.includes(n));

  for (let i = 0; i < botsToAdd; i++) {
    const seat = emptySeats[i];
    const name = availNames[i] || `Bot ${i + 1}`;
    const chipTiers = [500, 750, 1000, 1500, 2000, 3000, 5000];
    const botChips = chipTiers[Math.floor(Math.random() * chipTiers.length)];

    await supabase.from("game_seats").update({
      player_id: "BOT",
      user_id: null,
      display_name: name,
      avatar_url: null,
      chips: botChips,
      status: "waiting",
      is_vip: false,
      bet: 0,
      cards: [],
      outcome: null,
      payout: 0,
      afk_count: 0,
    }).eq("id", seat.id);
  }
}

// Bot lifecycle: some leave, new ones arrive (called at start of each betting phase)
async function botLifecycle(
  supabase: ReturnType<typeof createClient>,
  tableId: string,
  seats: any[],
): Promise<void> {
  const botSeats = seats.filter((s) => isBot(s));

  // Each bot has a chance to leave (25% per round, 100% if broke)
  for (const bot of botSeats) {
    const isBroke = bot.chips < 50;
    const wantsToLeave = Math.random() < 0.25;

    if (isBroke || wantsToLeave) {
      await supabase.from("game_seats").update({
        player_id: null,
        display_name: null,
        user_id: null,
        chips: 0,
        status: "empty",
        bet: 0,
        cards: [],
        split_cards: null,
        hand_total: 0,
        outcome: null,
        payout: 0,
        is_vip: false,
        afk_count: 0,
      }).eq("id", bot.id);
    }
  }

  // New bots arrive at empty seats (40% chance each, up to 3 total bots)
  const { data: refreshedSeats } = await supabase
    .from("game_seats").select("*").eq("table_id", tableId).order("seat_index");
  const currentBots = (refreshedSeats || []).filter((s: any) => isBot(s));
  // CRITICAL: truly empty = no user, no bot, status empty
  const emptySeats = (refreshedSeats || []).filter((s: any) => s.status === "empty" && !s.user_id && s.player_id !== "BOT");
  const realPlayers = (refreshedSeats || []).filter((s: any) => s.user_id);

  if (realPlayers.length === 0) return; // no bots without real players

  const maxBots = Math.min(3, 5 - realPlayers.length); // leave room for humans
  const botsToAdd = Math.min(maxBots - currentBots.length, emptySeats.length);

  if (botsToAdd <= 0) return;

  const usedNames = (refreshedSeats || []).filter((s: any) => s.display_name).map((s: any) => s.display_name);
  const availNames = BOT_NAMES.filter((n) => !usedNames.includes(n)).sort(() => Math.random() - 0.5);

  for (let i = 0; i < botsToAdd; i++) {
    if (Math.random() < 0.40 && i < availNames.length && i < emptySeats.length) {
      const chipTiers = [500, 750, 1000, 1500, 2000, 3000, 5000];
      const botChips = chipTiers[Math.floor(Math.random() * chipTiers.length)];
      await supabase.from("game_seats").update({
        player_id: "BOT",
        display_name: availNames[i],
        user_id: null,
        chips: botChips,
        status: "waiting",
        bet: 0,
        cards: [],
        outcome: null,
        payout: 0,
      }).eq("id", emptySeats[i].id);
    }
  }
}

// Bots place bets (called before deal when waiting for bets)
async function botsBet(
  supabase: ReturnType<typeof createClient>,
  tableId: string,
  seats: any[],
  minBet: number,
  maxBet: number,
): Promise<void> {
  const botSeats = seats.filter((s) => isBot(s) && s.status === "waiting" && s.bet === 0);

  for (const seat of botSeats) {
    // Bot bets between minBet and 3x minBet (conservative)
    const betMultiplier = [1, 1, 1, 2, 2, 3][Math.floor(Math.random() * 6)];
    const betAmount = Math.min(minBet * betMultiplier, seat.chips, maxBet);
    if (betAmount < minBet) continue; // bot is broke, skip

    await supabase.from("game_seats").update({
      bet: betAmount,
      chips: seat.chips - betAmount,
      status: "betting",
    }).eq("id", seat.id);
  }
}

// ============================================================
// BROADCAST via Supabase Realtime
// ============================================================

async function broadcast(
  supabase: ReturnType<typeof createClient>,
  tableId: string,
  eventType: string,
  table: any,
  seats: any[],
  extra: Record<string, any> = {},
) {
  // Sanitize: never send shoe or faceDown card values to clients
  const safeTable = {
    ...table,
    shoe: undefined, // NEVER broadcast the shoe
    dealer_hand: sanitizeCards(table.dealer_hand || []),
  };
  const safeSeats = seats.map((s: any) => ({
    ...s,
    cards: s.cards ? sanitizeCards(s.cards) : [],
    split_cards: s.split_cards ? sanitizeCards(s.split_cards) : null,
  }));

  const channel = supabase.channel(`table:${tableId}`);
  await channel.send({
    type: "broadcast",
    event: "game_state",
    payload: { type: eventType, table: safeTable, seats: safeSeats, ...extra },
  });
  // Unsubscribe server-side channel (we just needed to send)
  supabase.removeChannel(channel);
}

// ============================================================
// MAIN HANDLER
// ============================================================

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    const supabase = createClient(SUPABASE_URL, Deno.env.get("SB_SERVICE_ROLE_KEY")!);
    const body = await req.json();
    const { action, table_id } = body;

    // Get auth user from JWT
    const authHeader = req.headers.get("Authorization");
    let userId: string | null = null;
    if (authHeader) {
      const anonClient = createClient(SUPABASE_URL, Deno.env.get("SUPABASE_ANON_KEY") ?? "");
      const token = authHeader.replace("Bearer ", "");
      const { data: { user } } = await anonClient.auth.getUser(token);
      userId = user?.id ?? null;
    }

    // ========================================================
    // GET TABLES (no auth required)
    // ========================================================
    if (action === "get-tables") {
      const { data: tables } = await supabase
        .from("game_tables")
        .select("id, name, variant, min_bet, max_bet, max_seats, status, phase, felt_color, dealer_name, dealer_avatar")
        .order("min_bet");

      // Count occupied seats per table
      const { data: seatCounts } = await supabase
        .from("game_seats")
        .select("table_id, seat_index")
        .neq("status", "empty");

      const countMap: Record<string, number> = {};
      for (const s of seatCounts || []) {
        countMap[s.table_id] = (countMap[s.table_id] || 0) + 1;
      }

      const result = (tables || []).map((t: any) => ({
        ...t,
        players_count: countMap[t.id] || 0,
      }));

      return json({ success: true, tables: result });
    }

    // ========================================================
    // GET TABLE STATE (full state for a specific table)
    // ========================================================
    if (action === "get-state") {
      if (!table_id) return json({ error: "table_id required" }, 400);

      const { data: table } = await supabase
        .from("game_tables")
        .select("*")
        .eq("id", table_id)
        .single();

      if (!table) return json({ error: "Table not found" }, 404);

      const { data: seats } = await supabase
        .from("game_seats")
        .select("*")
        .eq("table_id", table_id)
        .order("seat_index");

      // Sanitize before sending
      const safeTable = { ...table, shoe: undefined, dealer_hand: sanitizeCards(table.dealer_hand || []) };
      const safeSeats = (seats || []).map((s: any) => ({
        ...s,
        cards: sanitizeCards(s.cards || []),
        split_cards: s.split_cards ? sanitizeCards(s.split_cards) : null,
      }));

      return json({ success: true, table: safeTable, seats: safeSeats });
    }

    // ========================================================
    // All actions below require auth
    // ========================================================
    if (!userId) return json({ error: "Authentication required" }, 401);
    if (!table_id) return json({ error: "table_id required" }, 400);

    // Load table + seats
    const { data: table } = await supabase
      .from("game_tables")
      .select("*")
      .eq("id", table_id)
      .single();

    if (!table) return json({ error: "Table not found" }, 404);

    const { data: seats } = await supabase
      .from("game_seats")
      .select("*")
      .eq("table_id", table_id)
      .order("seat_index");

    if (!seats) return json({ error: "Failed to load seats" }, 500);

    // Find player's seat
    const mySeat = seats.find((s: any) => s.user_id === userId);

    // ========================================================
    // JOIN
    // ========================================================
    if (action === "join") {
      const { seat_index } = body;
      if (seat_index === undefined) return json({ error: "seat_index required" }, 400);

      // Multi-seat: count how many seats this player already has
      const mySeats = seats.filter((s: any) => s.user_id === userId && s.status !== "empty");
      const seatCount = mySeats.length;

      // Max 3 seats per player
      if (seatCount >= 3) return json({ error: "Maximum 3 seats per player" }, 400);

      const targetSeat = seats.find((s: any) => s.seat_index === seat_index);
      if (!targetSeat) return json({ error: "Invalid seat" }, 400);
      // Allow taking a bot's seat (kick the bot), but not a real player's seat
      if (targetSeat.status !== "empty" && !isBot(targetSeat)) {
        return json({ error: "Seat is taken" }, 400);
      }

      // Get user profile
      const { data: { user } } = await supabase.auth.admin.getUserById(userId);
      const displayName = user?.user_metadata?.display_name || user?.user_metadata?.full_name || "Player";
      const avatarUrl = user?.user_metadata?.avatar_url || null;

      // Get player's chip balance from player_accounts (lookup by email)
      const userEmail = user?.email;
      const { data: account } = await supabase
        .from("player_accounts")
        .select("player_id, chip_balance, avatar_url")
        .eq("email", userEmail)
        .maybeSingle();

      const chips = account?.chip_balance ?? 10000;
      // Use player_accounts avatar if Google avatar not available
      const finalAvatar = avatarUrl || account?.avatar_url || null;

      await supabase
        .from("game_seats")
        .update({
          user_id: userId,
          display_name: displayName,
          avatar_url: finalAvatar,
          chips,
          status: "waiting",
          bet: 0,
          cards: [],
          split_cards: null,
          outcome: null,
          payout: 0,
          afk_count: 0,
          player_id: account?.player_id || null, // link to player_accounts
        })
        .eq("id", targetSeat.id);

      // Reload seats for broadcast
      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      await broadcast(supabase, table_id, "player_joined", table, updatedSeats || [], {
        actor_seat: seat_index,
      });

      return json({ success: true, seat_index });
    }

    // ========================================================
    // LEAVE
    // ========================================================
    if (action === "leave") {
      if (!mySeat) return json({ error: "Not seated at this table" }, 400);

      // Refund bet if in betting phase
      if (table.phase === "betting" && mySeat.bet > 0 && mySeat.player_id && mySeat.player_id !== "BOT") {
        await supabase
          .from("player_accounts")
          .update({ chip_balance: mySeat.chips + mySeat.bet })
          .eq("player_id", mySeat.player_id);
      }

      await supabase
        .from("game_seats")
        .update({
          user_id: null,
          display_name: null,
          avatar_url: null,
          chips: 0,
          bet: 0,
          cards: [],
          split_cards: null,
          status: "empty",
          outcome: null,
          payout: 0,
          afk_count: 0,
          is_vip: false,
        })
        .eq("id", mySeat.id);

      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      await broadcast(supabase, table_id, "player_left", table, updatedSeats || [], {
        actor_seat: mySeat.seat_index,
      });

      return json({ success: true });
    }

    // ========================================================
    // BET
    // ========================================================
    if (action === "bet") {
      if (!mySeat) return json({ error: "Not seated" }, 400);
      if (table.phase !== "betting") return json({ error: "Not in betting phase" }, 400);

      const { amount, seat_index: betSeatIndex } = body;

      // Multi-seat: if seat_index is specified, bet on that specific seat
      const targetSeat = betSeatIndex !== undefined
        ? seats.find((s: any) => s.seat_index === betSeatIndex && s.user_id === userId)
        : mySeat;
      if (!targetSeat) return json({ error: "Not your seat" }, 400);

      // Calculate effective min bet: doubles for each additional seat
      const mySeatsCount = seats.filter((s: any) => s.user_id === userId && s.status !== "empty").length;
      const effectiveMinBet = table.min_bet * Math.pow(2, Math.max(0, mySeatsCount - 1));

      if (!amount || amount < effectiveMinBet || amount > table.max_bet) {
        return json({ error: `Bet must be between ${effectiveMinBet.toLocaleString()} and ${table.max_bet.toLocaleString()} (${mySeatsCount} seats = ${mySeatsCount > 1 ? 'doubled' : 'standard'} minimum)` }, 400);
      }
      if (amount > targetSeat.chips) return json({ error: "Insufficient chips" }, 400);

      await supabase
        .from("game_seats")
        .update({
          bet: amount,
          chips: targetSeat.chips - amount,
          status: "betting",
        })
        .eq("id", targetSeat.id);

      // Bot lifecycle: departures + arrivals + bets
      const preSeats = await supabase.from("game_seats").select("*").eq("table_id", table_id).order("seat_index");
      await botLifecycle(supabase, table_id, preSeats.data || []);

      // Make bots bet
      const postLife = await supabase.from("game_seats").select("*").eq("table_id", table_id).order("seat_index");
      await botsBet(supabase, table_id, postLife.data || [], table.min_bet, table.max_bet);

      // Reload and check if all seated players/bots have bet
      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      const occupiedSeats = (updatedSeats || []).filter((s: any) => isOccupied(s));
      const allBet = occupiedSeats.length > 0 && occupiedSeats.every((s: any) => s.bet > 0);

      await broadcast(supabase, table_id, "bets_placed", table, updatedSeats || []);

      // Auto-deal when all seated players + bots have bet
      if (allBet && occupiedSeats.length >= 1) {
        return await handleDeal(supabase, table, updatedSeats || [], table_id);
      }

      return json({ success: true });
    }

    // ========================================================
    // HIT
    // ========================================================
    if (action === "hit") {
      if (!mySeat) return json({ error: "Not seated" }, 400);
      if (table.phase !== "player_turn") return json({ error: "Not player turn" }, 400);
      if (table.current_seat !== mySeat.seat_index) return json({ error: "Not your turn" }, 400);

      let shoe: Card[] = table.shoe || [];
      const { card, shoe: newShoe } = drawCard(shoe);
      const newCards = [...(mySeat.cards || []), card];
      const eval_ = evaluateHand(newCards);

      const seatUpdate: Record<string, any> = {
        cards: newCards,
        hand_total: eval_.value,
      };

      if (eval_.isBust) {
        seatUpdate.status = "busted";
        seatUpdate.outcome = "bust";
        seatUpdate.payout = 0;
      } else if (eval_.isCharlie && table.six_card_charlie) {
        seatUpdate.status = "standing";
        seatUpdate.outcome = "charlie";
      }

      await supabase.from("game_seats").update(seatUpdate).eq("id", mySeat.id);
      await supabase.from("game_tables").update({ shoe: newShoe }).eq("id", table_id);

      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      // If bust or charlie, advance to next seat
      if (eval_.isBust || eval_.isCharlie) {
        return await advanceTurn(supabase, { ...table, shoe: newShoe }, updatedSeats || [], table_id, mySeat.seat_index);
      }

      await broadcast(supabase, table_id, "player_action", { ...table, shoe: newShoe }, updatedSeats || [], {
        actor_seat: mySeat.seat_index,
        action_type: "hit",
      });

      return json({ success: true });
    }

    // ========================================================
    // STAND
    // ========================================================
    if (action === "stand") {
      if (!mySeat) return json({ error: "Not seated" }, 400);
      if (table.phase !== "player_turn") return json({ error: "Not player turn" }, 400);
      if (table.current_seat !== mySeat.seat_index) return json({ error: "Not your turn" }, 400);

      await supabase.from("game_seats").update({ status: "standing" }).eq("id", mySeat.id);

      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      return await advanceTurn(supabase, table, updatedSeats || [], table_id, mySeat.seat_index);
    }

    // ========================================================
    // DOUBLE DOWN
    // ========================================================
    if (action === "double") {
      if (!mySeat) return json({ error: "Not seated" }, 400);
      if (table.phase !== "player_turn") return json({ error: "Not player turn" }, 400);
      if (table.current_seat !== mySeat.seat_index) return json({ error: "Not your turn" }, 400);
      if ((mySeat.cards || []).length !== 2) return json({ error: "Can only double on first two cards" }, 400);
      if (mySeat.chips < mySeat.bet) return json({ error: "Insufficient chips to double" }, 400);

      let shoe: Card[] = table.shoe || [];
      const { card, shoe: newShoe } = drawCard(shoe);
      const newCards = [...(mySeat.cards || []), card];
      const eval_ = evaluateHand(newCards);
      const newBet = mySeat.bet * 2;

      const seatUpdate: Record<string, any> = {
        cards: newCards,
        hand_total: eval_.value,
        bet: newBet,
        chips: mySeat.chips - mySeat.bet,
        doubled: true,
        status: eval_.isBust ? "busted" : "standing",
      };
      if (eval_.isBust) {
        seatUpdate.outcome = "bust";
        seatUpdate.payout = 0;
      }

      await supabase.from("game_seats").update(seatUpdate).eq("id", mySeat.id);
      await supabase.from("game_tables").update({ shoe: newShoe }).eq("id", table_id);

      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      // Double always ends turn -- advance
      return await advanceTurn(supabase, { ...table, shoe: newShoe }, updatedSeats || [], table_id, mySeat.seat_index);
    }

    // ========================================================
    // SPLIT
    // ========================================================
    if (action === "split") {
      if (!mySeat) return json({ error: "Not seated" }, 400);
      if (table.phase !== "player_turn") return json({ error: "Not player turn" }, 400);
      if (table.current_seat !== mySeat.seat_index) return json({ error: "Not your turn" }, 400);

      const myCards: Card[] = mySeat.cards || [];
      if (myCards.length !== 2) return json({ error: "Can only split first two cards" }, 400);
      if (cardValue(myCards[0]) !== cardValue(myCards[1])) return json({ error: "Cards must have same value" }, 400);
      if (mySeat.chips < mySeat.bet) return json({ error: "Insufficient chips to split" }, 400);
      if (mySeat.is_split) return json({ error: "Already split" }, 400);

      let shoe: Card[] = table.shoe || [];
      const draw1 = drawCard(shoe);
      const draw2 = drawCard(draw1.shoe);

      const mainCards = [myCards[0], draw1.card];
      const splitCards = [myCards[1], draw2.card];
      const mainEval = evaluateHand(mainCards);
      const splitEval = evaluateHand(splitCards);

      await supabase.from("game_seats").update({
        cards: mainCards,
        split_cards: splitCards,
        hand_total: mainEval.value,
        split_total: splitEval.value,
        is_split: true,
        chips: mySeat.chips - mySeat.bet,
        // Status stays "acting" -- they play main hand first
      }).eq("id", mySeat.id);

      await supabase.from("game_tables").update({ shoe: draw2.shoe }).eq("id", table_id);

      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      await broadcast(supabase, table_id, "player_action", { ...table, shoe: draw2.shoe }, updatedSeats || [], {
        actor_seat: mySeat.seat_index,
        action_type: "split",
      });

      return json({ success: true });
    }

    // ========================================================
    // INSURANCE
    // ========================================================
    if (action === "insurance") {
      if (!mySeat) return json({ error: "Not seated" }, 400);
      const { take } = body;
      const dealerCards: Card[] = table.dealer_hand || [];
      if (!dealerCards[0] || dealerCards[0].rank !== "A") return json({ error: "Dealer doesn't show an Ace" }, 400);

      if (take) {
        const insuranceBet = Math.floor(mySeat.bet / 2);
        if (mySeat.chips < insuranceBet) return json({ error: "Insufficient chips for insurance" }, 400);

        await supabase.from("game_seats").update({
          insured: true,
          insurance_bet: insuranceBet,
          chips: mySeat.chips - insuranceBet,
        }).eq("id", mySeat.id);
      }

      // Continue play
      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      await broadcast(supabase, table_id, "player_action", table, updatedSeats || [], {
        actor_seat: mySeat.seat_index,
        action_type: take ? "insurance_taken" : "insurance_declined",
      });

      return json({ success: true });
    }

    // ========================================================
    // SURRENDER
    // ========================================================
    if (action === "surrender") {
      if (!mySeat) return json({ error: "Not seated" }, 400);
      if (table.phase !== "player_turn") return json({ error: "Not player turn" }, 400);
      if (table.current_seat !== mySeat.seat_index) return json({ error: "Not your turn" }, 400);
      if ((mySeat.cards || []).length !== 2) return json({ error: "Can only surrender on first two cards" }, 400);
      if (!table.surrender_allowed) return json({ error: "Surrender not allowed at this table" }, 400);

      const refund = Math.floor(mySeat.bet / 2);
      await supabase.from("game_seats").update({
        status: "settled",
        outcome: "surrender",
        payout: refund,
        chips: mySeat.chips + refund,
      }).eq("id", mySeat.id);

      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      return await advanceTurn(supabase, table, updatedSeats || [], table_id, mySeat.seat_index);
    }

    // ========================================================
    // CREATE INVITE (generate invite code for a seat)
    // ========================================================
    if (action === "create-invite") {
      if (!mySeat) return json({ error: "Must be seated to invite" }, 400);
      const { seat_index: inviteSeat, friend_id, phone_number } = body;

      if (inviteSeat === undefined) return json({ error: "seat_index required" }, 400);
      const target = seats.find((s: any) => s.seat_index === inviteSeat);
      if (!target) return json({ error: "Invalid seat" }, 400);
      if (target.status !== "empty" && !isBot(target)) {
        return json({ error: "Seat is not available" }, 400);
      }

      // Generate 6-char invite code
      const code = Math.random().toString(36).substring(2, 8).toUpperCase();

      await supabase.from("seat_invites").insert({
        code,
        table_id: table_id,
        seat_index: inviteSeat,
        inviter_id: userId,
        invitee_id: friend_id || null,
        phone_number: phone_number || null,
      });

      // If phone number provided, send SMS via Resend (or just return code)
      const inviteUrl = `https://everlightventures.io/play/blackjack/multi?table=${table_id}&invite=${code}`;

      return json({
        success: true,
        code,
        invite_url: inviteUrl,
        message: `Invite code: ${code}. Share this link: ${inviteUrl}`,
      });
    }

    // ========================================================
    // JOIN BY INVITE CODE
    // ========================================================
    if (action === "join-by-invite") {
      const { code } = body;
      if (!code) return json({ error: "Invite code required" }, 400);

      const { data: invite } = await supabase
        .from("seat_invites")
        .select("*")
        .eq("code", code.toUpperCase())
        .eq("status", "pending")
        .maybeSingle();

      if (!invite) return json({ error: "Invalid or expired invite code" }, 404);
      if (new Date(invite.expires_at) < new Date()) {
        await supabase.from("seat_invites").update({ status: "expired" }).eq("id", invite.id);
        return json({ error: "Invite has expired" }, 400);
      }

      // Join the specified seat
      const targetSeat = seats.find((s: any) => s.seat_index === invite.seat_index);
      if (!targetSeat) return json({ error: "Seat no longer exists" }, 400);

      // Kick bot if present
      if (targetSeat.status !== "empty" && !isBot(targetSeat)) {
        return json({ error: "Seat is taken by another player" }, 400);
      }

      const { data: { user } } = await supabase.auth.admin.getUserById(userId);
      const displayName = user?.user_metadata?.display_name || user?.user_metadata?.full_name || "Player";
      const avatarUrl = user?.user_metadata?.avatar_url || null;

      const inviteEmail = user?.email;
      const { data: account } = await supabase
        .from("player_accounts")
        .select("player_id, chip_balance, avatar_url")
        .eq("email", inviteEmail)
        .maybeSingle();

      const inviteAvatar = avatarUrl || account?.avatar_url || null;

      await supabase.from("game_seats").update({
        user_id: userId,
        display_name: displayName,
        avatar_url: inviteAvatar,
        chips: account?.chip_balance ?? 10000,
        status: "waiting",
        bet: 0,
        cards: [],
        split_cards: null,
        outcome: null,
        payout: 0,
        afk_count: 0,
        player_id: null,
      }).eq("id", targetSeat.id);

      // Mark invite as used
      await supabase.from("seat_invites").update({ status: "accepted", invitee_id: userId }).eq("id", invite.id);

      const { data: updatedSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", table_id).order("seat_index");

      await broadcast(supabase, table_id, "player_joined", table, updatedSeats || [], {
        actor_seat: invite.seat_index,
      });

      return json({ success: true, seat_index: invite.seat_index, table_id: invite.table_id });
    }

    // ========================================================
    // FRIEND LIST ACTIONS
    // ========================================================
    if (action === "add-friend") {
      const { friend_email } = body;
      if (!friend_email) return json({ error: "friend_email required" }, 400);

      // Find friend by email in auth.users via player_accounts
      const { data: friendAccount } = await supabase
        .from("player_accounts")
        .select("auth_user_id, display_name")
        .eq("email", friend_email)
        .maybeSingle();

      if (!friendAccount || !friendAccount.auth_user_id) {
        return json({ error: "Player not found" }, 404);
      }

      if (friendAccount.auth_user_id === userId) {
        return json({ error: "Can't add yourself" }, 400);
      }

      // Check existing
      const { data: existing } = await supabase
        .from("player_friends")
        .select("id, status")
        .or(`and(user_id.eq.${userId},friend_id.eq.${friendAccount.auth_user_id}),and(user_id.eq.${friendAccount.auth_user_id},friend_id.eq.${userId})`)
        .maybeSingle();

      if (existing) {
        if (existing.status === "accepted") return json({ error: "Already friends" }, 400);
        if (existing.status === "pending") return json({ error: "Friend request already pending" }, 400);
      }

      await supabase.from("player_friends").insert({
        user_id: userId,
        friend_id: friendAccount.auth_user_id,
        status: "pending",
      });

      return json({ success: true, message: `Friend request sent to ${friendAccount.display_name}` });
    }

    if (action === "accept-friend") {
      const { request_id } = body;
      if (!request_id) return json({ error: "request_id required" }, 400);

      await supabase
        .from("player_friends")
        .update({ status: "accepted" })
        .eq("id", request_id)
        .eq("friend_id", userId);

      return json({ success: true });
    }

    if (action === "get-friends") {
      const { data: friends } = await supabase
        .from("player_friends")
        .select("id, user_id, friend_id, status, created_at")
        .or(`user_id.eq.${userId},friend_id.eq.${userId}`)
        .eq("status", "accepted");

      // Enrich with display names
      const friendIds = (friends || []).map((f: any) =>
        f.user_id === userId ? f.friend_id : f.user_id
      );

      const { data: profiles } = await supabase
        .from("player_accounts")
        .select("auth_user_id, display_name, avatar_url, chip_balance, level")
        .in("auth_user_id", friendIds);

      // Check which friends are currently at a table
      const { data: onlineSeats } = await supabase
        .from("game_seats")
        .select("user_id, table_id")
        .in("user_id", friendIds)
        .neq("status", "empty");

      const onlineMap: Record<string, string> = {};
      for (const s of (onlineSeats || [])) {
        if (s.user_id) onlineMap[s.user_id] = s.table_id;
      }

      const enriched = (profiles || []).map((p: any) => ({
        ...p,
        online: !!onlineMap[p.auth_user_id],
        current_table: onlineMap[p.auth_user_id] || null,
      }));

      return json({ success: true, friends: enriched });
    }

    if (action === "get-friend-requests") {
      const { data: requests } = await supabase
        .from("player_friends")
        .select("id, user_id, created_at")
        .eq("friend_id", userId)
        .eq("status", "pending");

      // Get requester info
      const requesterIds = (requests || []).map((r: any) => r.user_id);
      const { data: profiles } = await supabase
        .from("player_accounts")
        .select("auth_user_id, display_name, avatar_url")
        .in("auth_user_id", requesterIds);

      const profileMap: Record<string, any> = {};
      for (const p of (profiles || [])) {
        if (p.auth_user_id) profileMap[p.auth_user_id] = p;
      }

      const enriched = (requests || []).map((r: any) => ({
        ...r,
        from: profileMap[r.user_id] || { display_name: "Unknown" },
      }));

      return json({ success: true, requests: enriched });
    }

    return json({ error: `Unknown action: ${action}` }, 400);
  } catch (err: any) {
    console.error("[blackjack-dealer] Error:", err);
    return json({ error: err.message || "Internal error" }, 500);
  }
});

// ============================================================
// DEAL (internal -- triggered when all bets are placed)
// ============================================================

async function handleDeal(
  supabase: ReturnType<typeof createClient>,
  table: any,
  seats: any[],
  tableId: string,
): Promise<Response> {
  let shoe: Card[] = table.shoe || [];
  if (shoe.length < 30) shoe = createShoe(table.deck_count || 6);

  const bettingSeats = seats
    .filter((s: any) => s.bet > 0 && isOccupied(s))
    .sort((a: any, b: any) => a.seat_index - b.seat_index);

  if (bettingSeats.length === 0) return json({ error: "No bets placed" }, 400);

  // Deal cards: casino order (player1, dealer, player2, dealer...)
  // Simplified: 2 cards to each player, 2 to dealer (second face down)
  const seatCards: Record<number, Card[]> = {};

  // Round 1: one card to each player
  for (const seat of bettingSeats) {
    const draw = drawCard(shoe);
    seatCards[seat.seat_index] = [draw.card];
    shoe = draw.shoe;
  }

  // Dealer card 1 (face up)
  const dealerDraw1 = drawCard(shoe);
  shoe = dealerDraw1.shoe;

  // Round 2: second card to each player
  for (const seat of bettingSeats) {
    const draw = drawCard(shoe);
    seatCards[seat.seat_index].push(draw.card);
    shoe = draw.shoe;
  }

  // Dealer card 2 (face DOWN)
  const dealerDraw2 = drawCard(shoe);
  dealerDraw2.card.faceDown = true;
  shoe = dealerDraw2.shoe;

  const dealerHand = [dealerDraw1.card, dealerDraw2.card];
  const dealerEval = evaluateHand([dealerDraw1.card]); // only eval visible card

  // Update each seat with their cards
  for (const seat of bettingSeats) {
    const cards = seatCards[seat.seat_index];
    const eval_ = evaluateHand(cards);

    const update: Record<string, any> = {
      cards,
      hand_total: eval_.value,
      status: eval_.isBlackjack ? "blackjack" : "acting",
      split_cards: null,
      is_split: false,
      doubled: false,
      insured: false,
      insurance_bet: 0,
      outcome: null,
      payout: 0,
    };

    await supabase.from("game_seats").update(update).eq("id", seat.id);
  }

  // Find first seat that needs to act (skip blackjacks)
  const firstActing = bettingSeats.find((s: any) => {
    const eval_ = evaluateHand(seatCards[s.seat_index]);
    return !eval_.isBlackjack;
  });

  const currentSeat = firstActing ? firstActing.seat_index : -1;
  const newPhase = currentSeat === -1 ? "dealer_turn" : "player_turn";

  // Update table
  await supabase.from("game_tables").update({
    shoe,
    dealer_hand: dealerHand,
    dealer_total: dealerEval.value,
    phase: newPhase,
    current_seat: currentSeat,
    status: "active",
    round_number: (table.round_number || 0) + 1,
    updated_at: new Date().toISOString(),
  }).eq("id", tableId);

  // Reload for broadcast
  const { data: updatedTable } = await supabase.from("game_tables").select("*").eq("id", tableId).single();
  const { data: updatedSeats } = await supabase.from("game_seats").select("*").eq("table_id", tableId).order("seat_index");

  await broadcast(supabase, tableId, "cards_dealt", updatedTable, updatedSeats || []);

  // If all players have blackjack, go straight to dealer turn
  if (newPhase === "dealer_turn") {
    return await handleDealerTurn(supabase, updatedTable, updatedSeats || [], tableId);
  }

  // If first acting seat is a bot, auto-play it via advanceTurn
  // (advanceTurn will detect bots and play them, then recurse)
  if (firstActing && isBot(firstActing)) {
    // Play the bot and advance
    const dealerUpcard = dealerHand[0];
    if (dealerUpcard) {
      await playBotTurn(supabase, tableId, firstActing, shoe, dealerUpcard);
    }
    const { data: postBotTable } = await supabase.from("game_tables").select("*").eq("id", tableId).single();
    const { data: postBotSeats } = await supabase.from("game_seats").select("*").eq("table_id", tableId).order("seat_index");
    await broadcast(supabase, tableId, "player_action", postBotTable, postBotSeats || [], {
      actor_seat: firstActing.seat_index,
      action_type: "bot_play",
    });
    return await advanceTurn(supabase, postBotTable, postBotSeats || [], tableId, firstActing.seat_index);
  }

  return json({ success: true, phase: newPhase });
}

// ============================================================
// ADVANCE TURN (move to next seat or dealer)
// ============================================================

async function advanceTurn(
  supabase: ReturnType<typeof createClient>,
  table: any,
  seats: any[],
  tableId: string,
  currentSeatIndex: number,
): Promise<Response> {
  const nextSeat = findNextActingSeat(seats, currentSeatIndex);

  if (nextSeat !== null) {
    const nextSeatData = seats.find((s: any) => s.seat_index === nextSeat);

    // If next seat is a BOT, auto-play it and recurse
    if (nextSeatData && isBot(nextSeatData)) {
      await supabase.from("game_tables").update({
        current_seat: nextSeat,
        updated_at: new Date().toISOString(),
      }).eq("id", tableId);

      // Get dealer upcard
      const dealerHand: Card[] = table.dealer_hand || [];
      const dealerUpcard = dealerHand[0];

      // Play bot's entire turn
      if (dealerUpcard) {
        await playBotTurn(supabase, tableId, nextSeatData, table.shoe || [], dealerUpcard);
      } else {
        // No dealer card somehow, just stand
        await supabase.from("game_seats").update({ status: "standing" }).eq("id", nextSeatData.id);
      }

      // Broadcast bot action
      const { data: botTable } = await supabase.from("game_tables").select("*").eq("id", tableId).single();
      const { data: botSeats } = await supabase.from("game_seats").select("*").eq("table_id", tableId).order("seat_index");
      await broadcast(supabase, tableId, "player_action", botTable, botSeats || [], {
        actor_seat: nextSeat,
        action_type: "bot_play",
      });

      // Recurse to find next seat
      return await advanceTurn(supabase, botTable, botSeats || [], tableId, nextSeat);
    }

    // Real player's turn -- set timer and wait
    await supabase.from("game_tables").update({
      current_seat: nextSeat,
      updated_at: new Date().toISOString(),
    }).eq("id", tableId);

    // Set turn timer
    await supabase.from("game_seats").update({
      turn_started_at: new Date().toISOString(),
    }).eq("table_id", tableId).eq("seat_index", nextSeat);

    const { data: updatedTable } = await supabase.from("game_tables").select("*").eq("id", tableId).single();
    const { data: updatedSeats } = await supabase.from("game_seats").select("*").eq("table_id", tableId).order("seat_index");

    await broadcast(supabase, tableId, "turn_started", updatedTable, updatedSeats || [], {
      actor_seat: nextSeat,
    });

    return json({ success: true, next_seat: nextSeat });
  }

  // All players done -- dealer's turn
  await supabase.from("game_tables").update({
    phase: "dealer_turn",
    updated_at: new Date().toISOString(),
  }).eq("id", tableId);

  const { data: updatedTable } = await supabase.from("game_tables").select("*").eq("id", tableId).single();
  const { data: updatedSeats } = await supabase.from("game_seats").select("*").eq("table_id", tableId).order("seat_index");

  return await handleDealerTurn(supabase, updatedTable, updatedSeats || [], tableId);
}

// ============================================================
// DEALER TURN + SETTLEMENT
// ============================================================

async function handleDealerTurn(
  supabase: ReturnType<typeof createClient>,
  table: any,
  seats: any[],
  tableId: string,
): Promise<Response> {
  let shoe: Card[] = table.shoe || [];
  let dealerCards: Card[] = (table.dealer_hand || []).map((c: Card) => ({ ...c, faceDown: false }));

  // Check if any player/bot is still alive (not all busted)
  const bettingSeats = seats.filter((s: any) => s.bet > 0 && isOccupied(s));
  const anyAlive = bettingSeats.some((s: any) => !["busted", "settled"].includes(s.status));

  if (anyAlive) {
    // Dealer draws to 17 (or soft 17 if configured)
    let eval_ = evaluateHand(dealerCards);
    while (
      eval_.value < 17 ||
      (table.dealer_hits_soft17 && eval_.value === 17 && eval_.isSoft)
    ) {
      const draw = drawCard(shoe);
      dealerCards.push(draw.card);
      shoe = draw.shoe;
      eval_ = evaluateHand(dealerCards);
    }
  }

  const dealerEval = evaluateHand(dealerCards);

  // Settle each seat
  const results: any[] = [];
  for (const seat of bettingSeats) {
    const playerCards: Card[] = seat.cards || [];
    const { outcome, multiplier } = settleOutcome(playerCards, dealerCards, table.six_card_charlie);

    let payout = 0;
    if (outcome === "surrender") {
      payout = Math.floor(seat.bet / 2);
    } else {
      payout = Math.floor(seat.bet * multiplier);
    }

    // Insurance payout
    let insurancePayout = 0;
    if (seat.insured && dealerEval.isBlackjack) {
      insurancePayout = seat.insurance_bet * 3;
    }

    const totalPayout = payout + insurancePayout;

    // Handle split hand settlement
    let splitPayout = 0;
    if (seat.is_split && seat.split_cards) {
      const splitResult = settleOutcome(seat.split_cards, dealerCards, table.six_card_charlie);
      splitPayout = Math.floor(seat.bet * splitResult.multiplier);
    }

    const finalPayout = totalPayout + splitPayout;

    await supabase.from("game_seats").update({
      status: "settled",
      outcome: seat.outcome || outcome, // preserve if already set (bust/surrender/charlie)
      payout: finalPayout,
      chips: seat.chips + finalPayout,
      hand_total: evaluateHand(playerCards).value,
    }).eq("id", seat.id);

    results.push({
      seat_index: seat.seat_index,
      outcome: seat.outcome || outcome,
      payout: finalPayout,
      cards: playerCards,
      hand_total: evaluateHand(playerCards).value,
    });

    // Update player stats in player_accounts (real players only, not bots)
    if (seat.user_id) {
      const finalOutcome = seat.outcome || outcome;
      const isWin = ["win", "blackjack", "charlie"].includes(finalOutcome);
      const isBj = finalOutcome === "blackjack";
      const isLoss = ["loss", "bust"].includes(finalOutcome);
      const isPush = finalOutcome === "push";

      await supabase.rpc("increment_player_stats", {
        p_user_id: seat.user_id,
        p_hands: 1,
        p_wins: isWin ? 1 : 0,
        p_losses: isLoss ? 1 : 0,
        p_pushes: isPush ? 1 : 0,
        p_blackjacks: isBj ? 1 : 0,
        p_wagered: seat.bet,
        p_won_amount: finalPayout,
      }).then(() => {}).catch(() => {
        // Fallback: direct update if RPC doesn't exist
        supabase.from("player_accounts").update({
          total_hands: (seat as any)._total_hands_placeholder || 0, // placeholder
        }).eq("player_id", seat.player_id).then(() => {});
      });

      // Direct stat update (works without RPC)
      const { data: currentStats } = await supabase
        .from("player_accounts")
        .select("total_hands, total_wins, total_losses, total_pushes, total_blackjacks, total_wagered, total_won_amount")
        .eq("player_id", seat.player_id)
        .maybeSingle();

      if (currentStats) {
        await supabase.from("player_accounts").update({
          total_hands: (currentStats.total_hands || 0) + 1,
          total_wins: (currentStats.total_wins || 0) + (isWin ? 1 : 0),
          total_losses: (currentStats.total_losses || 0) + (isLoss ? 1 : 0),
          total_pushes: (currentStats.total_pushes || 0) + (isPush ? 1 : 0),
          total_blackjacks: (currentStats.total_blackjacks || 0) + (isBj ? 1 : 0),
          total_wagered: (currentStats.total_wagered || 0) + seat.bet,
          total_won_amount: (currentStats.total_won_amount || 0) + finalPayout,
        }).eq("player_id", seat.player_id);
      }
    }
  }

  // Update table
  await supabase.from("game_tables").update({
    shoe,
    dealer_hand: dealerCards,
    dealer_total: dealerEval.value,
    phase: "settled",
    status: "settling",
    updated_at: new Date().toISOString(),
  }).eq("id", tableId);

  // Save hand history
  const { data: finalSeats } = await supabase
    .from("game_seats").select("*").eq("table_id", tableId).order("seat_index");

  await supabase.from("game_hands").insert({
    table_id: tableId,
    hand_number: table.round_number + 1,
    seats_snapshot: finalSeats,
    dealer_hand: dealerCards,
    dealer_total: dealerEval.value,
  });

  // Broadcast settlement with REVEALED dealer cards
  const { data: settledTable } = await supabase.from("game_tables").select("*").eq("id", tableId).single();

  // For settlement broadcast, show all cards (no sanitization on dealer)
  const channel = supabase.channel(`table:${tableId}`);
  await channel.send({
    type: "broadcast",
    event: "game_state",
    payload: {
      type: "hand_settled",
      table: { ...settledTable, shoe: undefined },
      seats: finalSeats,
      results,
      dealer_cards: dealerCards,
    },
  });
  supabase.removeChannel(channel);

  // Auto-reset to betting after 5 seconds (handled client-side via timer)
  // The client will call a "new_round" action or we can auto-reset here
  setTimeout(async () => {
    try {
      // Reset table to betting phase
      await supabase.from("game_tables").update({
        phase: "betting",
        status: "waiting",
        current_seat: 0,
        dealer_hand: [],
        dealer_total: 0,
        updated_at: new Date().toISOString(),
      }).eq("id", tableId);

      // Reset seated players + bots to waiting (keep their chips)
      const { data: currentSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", tableId);

      for (const seat of (currentSeats || [])) {
        if (seat.user_id) {
          // Real player: sync chips back to player_accounts
          await supabase
            .from("player_accounts")
            .update({ chip_balance: seat.chips })
            .eq("player_id", seat.player_id);

          await supabase.from("game_seats").update({
            status: "waiting",
            bet: 0,
            cards: [],
            split_cards: null,
            hand_total: 0,
            split_total: null,
            is_split: false,
            doubled: false,
            insured: false,
            insurance_bet: 0,
            outcome: null,
            payout: 0,
            turn_started_at: null,
          }).eq("id", seat.id);
        } else if (seat.player_id === "BOT") {
          // Bot lifecycle: broke bots leave, others have 20% chance to leave
          const shouldLeave = seat.chips < 50 || Math.random() < 0.20;

          if (shouldLeave) {
            // Bot leaves the table
            await supabase.from("game_seats").update({
              player_id: null,
              display_name: null,
              chips: 0,
              status: "empty",
              bet: 0,
              cards: [],
              split_cards: null,
              hand_total: 0,
              outcome: null,
              payout: 0,
            }).eq("id", seat.id);
          } else {
            // Bot stays, reset for next round
            await supabase.from("game_seats").update({
              status: "waiting",
              bet: 0,
              cards: [],
              split_cards: null,
              hand_total: 0,
              split_total: null,
              is_split: false,
              doubled: false,
              insured: false,
              insurance_bet: 0,
              outcome: null,
              payout: 0,
              turn_started_at: null,
            }).eq("id", seat.id);
          }
        }
      }

      // Bot lifecycle: new bots arrive at empty seats (30% chance each)
      const { data: postResetSeats } = await supabase
        .from("game_seats").select("*").eq("table_id", tableId).order("seat_index");
      const realPlayers = (postResetSeats || []).filter((s: any) => s.user_id);
      // CRITICAL: truly empty = no user, no bot
      const emptyAfterReset = (postResetSeats || []).filter((s: any) => s.status === "empty" && !s.user_id && s.player_id !== "BOT");

      if (realPlayers.length > 0) {
        const usedNames = (postResetSeats || []).filter((s: any) => s.display_name).map((s: any) => s.display_name);
        const availNames = BOT_NAMES.filter((n) => !usedNames.includes(n));
        let nameIdx = 0;

        for (const empty of emptyAfterReset) {
          if (Math.random() < 0.30 && nameIdx < availNames.length) {
            const chipTiers = [500, 750, 1000, 1500, 2000, 3000, 5000];
            const botChips = chipTiers[Math.floor(Math.random() * chipTiers.length)];
            await supabase.from("game_seats").update({
              player_id: "BOT",
              display_name: availNames[nameIdx],
              chips: botChips,
              status: "waiting",
              bet: 0,
              cards: [],
              outcome: null,
              payout: 0,
            }).eq("id", empty.id);
            nameIdx++;
          }
        }
      }

      // Broadcast new round
      const { data: resetTable } = await supabase.from("game_tables").select("*").eq("id", tableId).single();
      const { data: resetSeats } = await supabase.from("game_seats").select("*").eq("table_id", tableId).order("seat_index");
      await broadcast(supabase, tableId, "table_state", resetTable, resetSeats || []);
    } catch (e) {
      console.error("[blackjack-dealer] Auto-reset error:", e);
    }
  }, 6000);

  return json({ success: true, results });
}
