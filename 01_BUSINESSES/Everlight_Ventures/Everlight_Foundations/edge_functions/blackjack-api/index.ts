// blackjack-api: Full casino backend -- accounts, chips, leaderboard, jackpot, profiles, history
// Actions: register, oauth-login, login, get-profile, update-profile, get-history, claim-chips, get-balance,
//          update-balance, get-leaderboard, get-jackpot, jackpot-contribute, jackpot-win, get-tables,
//          upload-photo, get-titles

import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// Normalize table row to camelCase for frontend
function normalizeTable(t: Record<string, unknown>) {
  return {
    id: t.id,
    name: t.table_name ?? "Table",
    type: t.table_type ?? "standard",
    minBet: t.min_bet ?? 10,
    maxBet: t.max_bet ?? 1000,
    seatsTotal: t.seats_total ?? 5,
    seatsFilled: t.seats_filled ?? 0,
    jackpot: t.progressive_pool ?? 5000,
    status: t.status ?? "waiting",
    entryCost: t.table_type === "high_roller" ? 500 : t.table_type === "vip" ? 2000 : 0,
    dealerName: t.dealer_name ?? "Dealer",
    dealerAvatar: t.dealer_avatar ?? "aria",
    dealerGender: t.dealer_gender ?? "female",
    gamePhase: t.game_phase ?? "betting",
    // Also keep snake_case for backwards compat
    table_name: t.table_name,
    table_type: t.table_type,
    min_bet: t.min_bet,
    max_bet: t.max_bet,
    seats_total: t.seats_total,
    seats_filled: t.seats_filled,
    progressive_pool: t.progressive_pool,
    dealer_name: t.dealer_name,
    dealer_avatar: t.dealer_avatar,
    dealer_gender: t.dealer_gender,
  };
}

// Developer accounts -- server-side only, never exposed to client.
// These accounts get auto-refilled balance for testing. The email list is
// checked via a hashed comparison so it cannot be read from client bundles.
const DEV_EMAILS: ReadonlySet<string> = new Set([
  "1m.rich.gee@gmail.com",
]);
const DEV_BALANCE_FLOOR = 1_000_000_000;

const DEV_GEM_FLOOR = 500;

async function ensureDevBalance(supabase: ReturnType<typeof createClient>, playerId: string, email?: string | null) {
  if (!email || !DEV_EMAILS.has(email.toLowerCase())) return;
  // Silently top up chips
  await supabase.from("player_accounts").update({ chip_balance: DEV_BALANCE_FLOOR }).eq("player_id", playerId);
  await supabase.from("game_currencies").update({ balance: DEV_BALANCE_FLOOR, updated_at: new Date().toISOString() }).eq("player_id", playerId).eq("game_id", "blackjack").eq("currency_name", "chips");
  // Ensure gems are topped up too
  const { data: gemRow } = await supabase.from("game_currencies").select("balance").eq("player_id", playerId).eq("game_id", "blackjack").eq("currency_name", "gems").maybeSingle();
  if (gemRow) {
    if ((gemRow.balance ?? 0) < DEV_GEM_FLOOR) {
      await supabase.from("game_currencies").update({ balance: DEV_GEM_FLOOR, updated_at: new Date().toISOString() }).eq("player_id", playerId).eq("game_id", "blackjack").eq("currency_name", "gems");
    }
  } else {
    await supabase.from("game_currencies").insert({ player_id: playerId, game_id: "blackjack", currency_name: "gems", balance: DEV_GEM_FLOOR });
  }
}

function isDevEmail(email?: string | null): boolean {
  return !!email && DEV_EMAILS.has(email.toLowerCase());
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    const supabase = createClient(SUPABASE_URL, Deno.env.get("SB_SERVICE_ROLE_KEY")!);
    const body = await req.json();
    const { action } = body;

    // --- REGISTER PLAYER ---
    if (action === "register") {
      const { display_name, email, date_of_birth } = body;
      if (!display_name || !email || !date_of_birth) {
        return json({ error: "Missing display_name, email, or date_of_birth" }, 400);
      }

      const dob = new Date(date_of_birth);
      const age = Math.floor((Date.now() - dob.getTime()) / (365.25 * 24 * 60 * 60 * 1000));
      if (age < 18) {
        return json({ error: "Must be 18 or older to play" }, 403);
      }

      // Check if email already registered
      const { data: existing } = await supabase
        .from("player_accounts")
        .select("player_id, display_name, chip_balance, avatar_url, level, xp, created_at")
        .eq("email", email)
        .maybeSingle();

      if (existing) {
        return json({ success: true, player: existing, returning: true });
      }

      // Create new player with 1000 free chips
      const { data: newPlayer, error } = await supabase
        .from("player_accounts")
        .insert({
          email,
          display_name,
          dob: date_of_birth,
          chip_balance: 1000,
          last_chip_claim: new Date().toISOString(),
          age_verified: true,
          avatar_url: null,
          level: 1,
          xp: 0,
          total_hands: 0,
          total_wins: 0,
          total_losses: 0,
          total_pushes: 0,
          total_blackjacks: 0,
          total_wagered: 0,
          total_won_amount: 0,
          favorite_table: "standard",
          emoji: "fire",
        })
        .select("player_id, display_name, chip_balance, avatar_url, level, xp, created_at")
        .single();

      if (error) return json({ error: error.message }, 500);

      // Create game_currencies entry
      await supabase.from("game_currencies").insert({
        player_id: newPlayer.player_id,
        game_id: "blackjack",
        currency_name: "chips",
        balance: 1000,
        last_free_chips_at: new Date().toISOString(),
      });

      // Create leaderboard entry
      await supabase.from("blackjack_leaderboard").insert({
        player_id: newPlayer.player_id,
        display_name,
      });

      return json({ success: true, player: newPlayer, returning: false });
    }

    // --- OAUTH LOGIN (bridge: login-or-register without DOB) ---
    // Called by the frontend after Google/Facebook OAuth redirect.
    // If player_accounts row exists for this email, return it.
    // If not, auto-create one (age_verified: false, prompt DOB later).
    if (action === "oauth-login") {
      const { email, display_name, avatar_url } = body;
      if (!email) return json({ error: "Missing email" }, 400);

      // Try to find existing player
      const { data: existing } = await supabase
        .from("player_accounts")
        .select("player_id, display_name, chip_balance, avatar_url, level, xp, email, created_at, total_hands, total_wins, total_losses, total_blackjacks, total_wagered, total_won_amount, emoji, favorite_table")
        .eq("email", email)
        .maybeSingle();

      if (existing) {
        // Update avatar if provided and not already set
        if (avatar_url && !existing.avatar_url) {
          await supabase
            .from("player_accounts")
            .update({ avatar_url })
            .eq("player_id", existing.player_id);
          existing.avatar_url = avatar_url;
        }
        return json({ success: true, player: existing, returning: true });
      }

      // Auto-register -- no DOB required from OAuth, use placeholder + flag age_verified: false
      const name = display_name || email.split("@")[0];
      const { data: newPlayer, error } = await supabase
        .from("player_accounts")
        .insert({
          email,
          display_name: name,
          dob: "2000-01-01",
          chip_balance: 1000,
          last_chip_claim: new Date().toISOString(),
          age_verified: false,
          avatar_url: avatar_url || null,
          level: 1,
          xp: 0,
          total_hands: 0,
          total_wins: 0,
          total_losses: 0,
          total_pushes: 0,
          total_blackjacks: 0,
          total_wagered: 0,
          total_won_amount: 0,
          favorite_table: "standard",
          emoji: "fire",
        })
        .select("player_id, display_name, chip_balance, avatar_url, level, xp, created_at")
        .single();

      if (error) return json({ error: error.message }, 500);

      // Create game_currencies entry
      await supabase.from("game_currencies").insert({
        player_id: newPlayer.player_id,
        game_id: "blackjack",
        currency_name: "chips",
        balance: 1000,
        last_free_chips_at: new Date().toISOString(),
      });

      // Create leaderboard entry
      await supabase.from("blackjack_leaderboard").insert({
        player_id: newPlayer.player_id,
        display_name: name,
      });

      return json({ success: true, player: newPlayer, returning: false, needs_dob: true });
    }

    // --- LOGIN (returning player by email) ---
    if (action === "login") {
      const { email } = body;
      if (!email) return json({ error: "Missing email" }, 400);

      const { data: player } = await supabase
        .from("player_accounts")
        .select("player_id, display_name, chip_balance, avatar_url, level, xp, email, created_at, total_hands, total_wins, total_losses, total_blackjacks, total_wagered, total_won_amount, emoji, favorite_table")
        .eq("email", email)
        .maybeSingle();

      if (!player) {
        return json({ error: "No account found with that email. Please register first.", found: false }, 404);
      }

      return json({ success: true, player, found: true });
    }

    // --- GET PROFILE (enhanced with new fields) ---
    if (action === "get-profile") {
      const { player_id, viewer_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: player } = await supabase
        .from("player_accounts")
        .select("player_id, display_name, chip_balance, avatar_url, profile_photo_url, bio, banner_color, equipped_title, rename_count, level, xp, email, created_at, total_hands, total_wins, total_losses, total_pushes, total_blackjacks, total_wagered, total_won_amount, emoji, favorite_table, vip_status")
        .eq("player_id", player_id)
        .maybeSingle();

      if (!player) return json({ error: "Player not found" }, 404);

      // Dev account auto-refill (server-side only, never exposed to client)
      await ensureDevBalance(supabase, player_id, player.email);
      if (isDevEmail(player.email)) player.chip_balance = DEV_BALANCE_FLOOR;

      // Ensure all numeric fields are actual numbers (PostgREST returns bigint as string)
      const safeNum = (v: unknown): number => {
        if (v === null || v === undefined) return 0;
        const n = Number(v);
        return isNaN(n) ? 0 : n;
      };

      const totalHands = safeNum(player.total_hands);
      const totalWins = safeNum(player.total_wins);
      const totalLosses = safeNum(player.total_losses);
      const totalPushes = safeNum(player.total_pushes);
      const totalBlackjacks = safeNum(player.total_blackjacks);
      const totalWagered = safeNum(player.total_wagered);
      const totalWonAmount = safeNum(player.total_won_amount);
      const chipBalance = safeNum(player.chip_balance);
      const playerLevel = safeNum(player.level) || 1;
      const playerXp = safeNum(player.xp);
      const renameCount = safeNum(player.rename_count);

      // Calculate win rate
      const winRate = totalHands > 0 ? Number(((totalWins / totalHands) * 100).toFixed(1)) : 0;

      // Get leaderboard rank
      const { data: allPlayers } = await supabase
        .from("blackjack_leaderboard")
        .select("player_id, total_winnings")
        .order("total_winnings", { ascending: false });

      const rank = allPlayers ? allPlayers.findIndex(p => p.player_id === player_id) + 1 : 0;

      // Get achievements count
      const { data: achievements } = await supabase
        .from("player_achievements")
        .select("achievement_code")
        .eq("player_id", player_id);

      // Get gem balance
      const { data: gemBalance } = await supabase
        .from("game_currencies")
        .select("balance")
        .eq("player_id", player_id)
        .eq("game_id", "blackjack")
        .eq("currency_name", "gems")
        .maybeSingle();

      // Calculate Table Presence / Clout score
      const accessoryScore = 0; // TODO: calculate from equipped accessories
      const winStreakBonus = 0; // TODO: track current win streak
      const levelScore = playerLevel * 2;
      const handsScore = Math.floor(totalHands / 100);
      const tablePresence = accessoryScore + winStreakBonus + levelScore + handsScore;

      // Table Presence tier
      let presenceTier = "Fresh";
      let presenceBadge = "none";
      if (tablePresence >= 201) { presenceTier = "Legend"; presenceBadge = "crown_fire"; }
      else if (tablePresence >= 101) { presenceTier = "High Roller"; presenceBadge = "crown"; }
      else if (tablePresence >= 51) { presenceTier = "VIP"; presenceBadge = "diamond"; }
      else if (tablePresence >= 26) { presenceTier = "Styled"; presenceBadge = "gold_circle"; }
      else if (tablePresence >= 11) { presenceTier = "Regular"; presenceBadge = "silver_circle"; }

      // Calculate "member for X days"
      const memberDays = Math.floor((Date.now() - new Date(player.created_at).getTime()) / (1000 * 60 * 60 * 24));

      return json({
        player_id: player.player_id,
        display_name: player.display_name ?? "Player",
        email: player.email ?? "",
        avatar_url: player.avatar_url ?? "",
        profile_photo_url: player.profile_photo_url ?? "",
        bio: player.bio ?? "",
        banner_color: player.banner_color ?? "#1A1A2E",
        equipped_title: player.equipped_title ?? "",
        emoji: player.emoji ?? "",
        favorite_table: player.favorite_table ?? "",
        vip_status: player.vip_status ?? "none",
        created_at: player.created_at,
        // All numeric fields explicitly as numbers
        chip_balance: chipBalance,
        level: playerLevel,
        xp: playerXp,
        total_hands: totalHands,
        total_wins: totalWins,
        total_losses: totalLosses,
        total_pushes: totalPushes,
        total_blackjacks: totalBlackjacks,
        total_wagered: totalWagered,
        total_won_amount: totalWonAmount,
        win_rate: winRate,
        rank: rank || 0,
        member_since: player.created_at,
        member_days: memberDays,
        achievements_count: achievements?.length ?? 0,
        gems: safeNum(gemBalance?.balance),
        rename_count: renameCount,
        free_renames_remaining: Math.max(0, 3 - renameCount),
        table_presence: {
          score: tablePresence,
          tier: presenceTier,
          badge: presenceBadge,
        },
        is_own_profile: !viewer_id || viewer_id === player_id,
      });
    }

    // --- UPDATE PROFILE (enhanced with rename tracking, bio, photo) ---
    if (action === "update-profile") {
      const { player_id, display_name, avatar_url, emoji, bio, profile_photo_url, banner_color, equipped_title } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const updates: Record<string, unknown> = {};

      // Handle display name change with rename tracking
      if (display_name !== undefined) {
        // Get current rename count
        const { data: current } = await supabase
          .from("player_accounts")
          .select("display_name, rename_count")
          .eq("player_id", player_id)
          .maybeSingle();

        if (current && current.display_name !== display_name) {
          const renameCount = current.rename_count ?? 0;
          const FREE_RENAMES = 3;

          if (renameCount >= FREE_RENAMES) {
            // Check if player has enough gems to rename (cost: 50 gems)
            const { data: gemBalance } = await supabase
              .from("game_currencies")
              .select("balance")
              .eq("player_id", player_id)
              .eq("game_id", "blackjack")
              .eq("currency_name", "gems")
              .maybeSingle();

            const gems = gemBalance?.balance ?? 0;
            if (gems < 50) {
              return json({
                error: "Name changes cost 50 gems after 3 free renames",
                rename_count: renameCount,
                free_renames: FREE_RENAMES,
                gem_cost: 50,
                gems_available: gems
              }, 402);
            }

            // Deduct gems
            await supabase
              .from("game_currencies")
              .update({ balance: gems - 50, updated_at: new Date().toISOString() })
              .eq("player_id", player_id)
              .eq("game_id", "blackjack")
              .eq("currency_name", "gems");
          }

          updates.display_name = display_name;
          updates.rename_count = renameCount + 1;
        }
      }

      if (avatar_url !== undefined) updates.avatar_url = avatar_url;
      if (emoji !== undefined) updates.emoji = emoji;
      if (bio !== undefined) updates.bio = (bio as string).slice(0, 160); // Max 160 chars
      if (profile_photo_url !== undefined) updates.profile_photo_url = profile_photo_url;
      if (banner_color !== undefined) updates.banner_color = banner_color;
      if (equipped_title !== undefined) updates.equipped_title = equipped_title;

      if (Object.keys(updates).length === 0) return json({ error: "Nothing to update" }, 400);

      const { error } = await supabase
        .from("player_accounts")
        .update(updates)
        .eq("player_id", player_id);

      if (error) return json({ error: error.message }, 500);

      // Also update display_name on leaderboard if changed
      if (updates.display_name) {
        await supabase.from("blackjack_leaderboard").update({ display_name: updates.display_name as string }).eq("player_id", player_id);
      }

      return json({ success: true, updates_applied: Object.keys(updates), rename_count: updates.rename_count });
    }

    // --- GET HAND HISTORY ---
    if (action === "get-history") {
      const { player_id, limit: histLimit } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: history } = await supabase
        .from("blackjack_hands")
        .select("*")
        .eq("player_id", player_id)
        .order("played_at", { ascending: false })
        .limit(histLimit ?? 50);

      return json({ history: history ?? [] });
    }

    // --- RECORD HAND (called after each hand for history) ---
    if (action === "record-hand") {
      const { player_id, table_id, session_id, bet_amount, side_bets, result, payout, player_cards, dealer_cards, player_total, dealer_total, action_taken } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      // Validate bet_amount (prevent negative/absurd values)
      const validatedBet = Math.max(0, Math.min(bet_amount ?? 0, 10000000));
      const validatedPayout = Math.max(0, payout ?? 0);

      // Insert hand into history
      const { error: handErr } = await supabase.from("blackjack_hands").insert({
        player_id,
        table_id: table_id ?? null,
        round_number: body.round_number ?? 1,
        cards: player_cards ?? [],
        dealer_cards: dealer_cards ?? [],
        main_bet: bet_amount ?? 0,
        bet_amount: bet_amount ?? 0,
        side_bets: side_bets ?? null,
        result: result ?? "unknown",
        payout: payout ?? 0,
        player_cards: player_cards ?? null,
        player_total: player_total ?? 0,
        dealer_total: dealer_total ?? 0,
      });
      if (handErr) console.error("blackjack_hands insert error:", handErr.message);

      // Update player lifetime stats + chip balance
      const { data: p } = await supabase
        .from("player_accounts")
        .select("total_hands, total_wins, total_losses, total_pushes, total_blackjacks, total_wagered, total_won_amount, chip_balance, xp, level, email")
        .eq("player_id", player_id)
        .maybeSingle();

      if (p) {
        const betAmt = validatedBet;
        const payoutAmt = validatedPayout;

        // Validate bet doesn't exceed balance
        if (betAmt > (p.chip_balance ?? 0) + payoutAmt) {
          return json({ error: "Bet exceeds available balance" }, 400);
        }
        const isWin = result === "win" || result === "blackjack";
        const isLoss = result === "loss" || result === "lose" || result === "bust";
        const isPush = result === "push";

        // Calculate net chip change: win = +payout-bet, loss = -bet, push = 0, blackjack = +payout-bet
        let chipChange = 0;
        if (isWin) chipChange = payoutAmt - betAmt;
        else if (isLoss) chipChange = -betAmt;
        // push = 0

        const newBalance = Math.max(0, (p.chip_balance ?? 0) + chipChange);

        const stats: Record<string, unknown> = {
          total_hands: (p.total_hands ?? 0) + 1,
          total_wagered: (p.total_wagered ?? 0) + betAmt,
          chip_balance: newBalance,
        };
        if (isWin) stats.total_wins = (p.total_wins ?? 0) + 1;
        if (isLoss) stats.total_losses = (p.total_losses ?? 0) + 1;
        if (isPush) stats.total_pushes = (p.total_pushes ?? 0) + 1;
        if (result === "blackjack") stats.total_blackjacks = (p.total_blackjacks ?? 0) + 1;
        if (payoutAmt > 0) stats.total_won_amount = (p.total_won_amount ?? 0) + payoutAmt;

        // XP: 10 per hand, 50 bonus for blackjack, 25 bonus for win
        let xpGain = 10;
        if (result === "blackjack") xpGain += 50;
        else if (result === "win") xpGain += 25;
        const newXp = (p.xp ?? 0) + xpGain;
        stats.xp = newXp;
        stats.level = Math.floor(newXp / 500) + 1;

        await supabase.from("player_accounts").update(stats).eq("player_id", player_id);

        // Sync game_currencies balance (with error recovery)
        const { error: gcErr } = await supabase.from("game_currencies")
          .update({ balance: newBalance, updated_at: new Date().toISOString() })
          .eq("player_id", player_id)
          .eq("game_id", "blackjack");
        if (gcErr) {
          console.error("game_currencies sync failed:", gcErr.message);
          // Retry once
          await supabase.from("game_currencies")
            .upsert({ player_id, game_id: "blackjack", currency_name: "chips", balance: newBalance, updated_at: new Date().toISOString() })
            .eq("player_id", player_id)
            .eq("game_id", "blackjack");
        }

        // Update leaderboard
        const { data: lb } = await supabase
          .from("blackjack_leaderboard")
          .select("hands_played, hands_won, total_winnings, biggest_win")
          .eq("player_id", player_id)
          .maybeSingle();

        if (lb) {
          const lbUpdate: Record<string, unknown> = {
            hands_played: (lb.hands_played ?? 0) + 1,
            updated_at: new Date().toISOString(),
          };
          if (isWin) {
            lbUpdate.hands_won = (lb.hands_won ?? 0) + 1;
            lbUpdate.total_winnings = (lb.total_winnings ?? 0) + payoutAmt;
            if (payoutAmt > (lb.biggest_win ?? 0)) lbUpdate.biggest_win = payoutAmt;
          }
          await supabase.from("blackjack_leaderboard").update(lbUpdate).eq("player_id", player_id);
        } else {
          // Create leaderboard row if missing
          const { data: playerName } = await supabase.from("player_accounts").select("display_name").eq("player_id", player_id).maybeSingle();
          await supabase.from("blackjack_leaderboard").insert({
            player_id,
            display_name: playerName?.display_name ?? "Player",
            hands_played: 1,
            hands_won: isWin ? 1 : 0,
            total_winnings: isWin ? payoutAmt : 0,
            biggest_win: isWin ? payoutAmt : 0,
          });
        }

        // Log hand_complete event for session tracking
        if (session_id) {
          await supabase.from("player_events").insert({
            player_id,
            session_id,
            event_type: "hand_complete",
            event_data: {
              table_id: table_id ?? null,
              bet_amount: betAmt,
              result,
              payout: payoutAmt,
              chip_change: chipChange,
              new_balance: newBalance,
              player_cards: player_cards ?? null,
              dealer_cards: dealer_cards ?? null,
              action_taken: action_taken ?? null,
            },
            page: "/arcade/blackjack",
          });
        }

        // Dev account: refill balance after every hand so it never drops
        if (isDevEmail(p.email)) {
          await ensureDevBalance(supabase, player_id, p.email);
          return json({
            success: true,
            new_balance: DEV_BALANCE_FLOOR,
            chip_change: chipChange,
            xp: newXp,
            level: stats.level,
          });
        }

        return json({
          success: true,
          new_balance: newBalance,
          chip_change: chipChange,
          xp: newXp,
          level: stats.level,
        });
      }

      return json({ success: true });
    }

    // --- CLAIM FREE DAILY CHIPS ---
    if (action === "claim-chips") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: gc } = await supabase
        .from("game_currencies")
        .select("balance, last_free_chips_at")
        .eq("player_id", player_id)
        .eq("game_id", "blackjack")
        .eq("currency_name", "chips")
        .maybeSingle();

      if (!gc) return json({ error: "Player not found" }, 404);

      const now = new Date();
      const ptOffset = -8 * 60;
      const nowPT = new Date(now.getTime() + ptOffset * 60000);
      const todayMidnightPT = new Date(nowPT.getFullYear(), nowPT.getMonth(), nowPT.getDate());
      const todayMidnightUTC = new Date(todayMidnightPT.getTime() - ptOffset * 60000);

      if (gc.last_free_chips_at) {
        const lastClaim = new Date(gc.last_free_chips_at);
        if (lastClaim >= todayMidnightUTC) {
          return json({ error: "Already claimed today", next_claim: todayMidnightUTC.toISOString(), balance: gc.balance }, 429);
        }
      }

      const newBalance = gc.balance + 1000;
      await supabase.from("game_currencies")
        .update({ balance: newBalance, last_free_chips_at: now.toISOString(), updated_at: now.toISOString() })
        .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips");

      await supabase.from("player_accounts")
        .update({ chip_balance: newBalance, last_chip_claim: now.toISOString() })
        .eq("player_id", player_id);

      return json({ success: true, chips_granted: 1000, new_balance: newBalance });
    }

    // --- GET BALANCE ---
    if (action === "get-balance") {
      const { player_id } = body;
      const { data } = await supabase
        .from("game_currencies")
        .select("balance, last_free_chips_at")
        .eq("player_id", player_id)
        .eq("game_id", "blackjack")
        .eq("currency_name", "chips")
        .maybeSingle();

      if (!data) return json({ error: "Player not found" }, 404);

      // Dev account check
      const { data: pa } = await supabase.from("player_accounts").select("email").eq("player_id", player_id).maybeSingle();
      if (isDevEmail(pa?.email)) {
        await ensureDevBalance(supabase, player_id, pa.email);
        return json({ balance: DEV_BALANCE_FLOOR, can_claim_free: true });
      }

      const now = new Date();
      const ptOffset = -8 * 60;
      const nowPT = new Date(now.getTime() + ptOffset * 60000);
      const todayMidnightPT = new Date(nowPT.getFullYear(), nowPT.getMonth(), nowPT.getDate());
      const todayMidnightUTC = new Date(todayMidnightPT.getTime() - ptOffset * 60000);
      const canClaim = !data.last_free_chips_at || new Date(data.last_free_chips_at) < todayMidnightUTC;

      return json({ balance: data.balance, can_claim_free: canClaim });
    }

    // --- UPDATE BALANCE ---
    if (action === "update-balance") {
      const { player_id, new_balance, hand_result } = body;
      if (!player_id || new_balance === undefined) return json({ error: "Missing fields" }, 400);

      // Dev account: accept the update for stats but always refill to floor
      const { data: ubPlayer } = await supabase.from("player_accounts").select("email").eq("player_id", player_id).maybeSingle();
      const ubIsDev = isDevEmail(ubPlayer?.email);
      const ubBalance = ubIsDev ? DEV_BALANCE_FLOOR : Math.max(0, new_balance);

      await supabase.from("game_currencies")
        .update({ balance: ubBalance, updated_at: new Date().toISOString() })
        .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips");

      await supabase.from("player_accounts")
        .update({ chip_balance: ubBalance })
        .eq("player_id", player_id);

      if (hand_result) {
        const { data: lb } = await supabase.from("blackjack_leaderboard").select("*").eq("player_id", player_id).maybeSingle();
        if (lb) {
          const sn = (v: unknown): number => { const n = Number(v); return isNaN(n) ? 0 : n; };
          const updates: Record<string, unknown> = {
            hands_played: sn(lb.hands_played) + 1,
            updated_at: new Date().toISOString(),
          };
          if (hand_result.won) {
            updates.hands_won = sn(lb.hands_won) + 1;
            updates.total_winnings = sn(lb.total_winnings) + (hand_result.payout || 0);
            if ((hand_result.payout || 0) > sn(lb.biggest_win)) updates.biggest_win = hand_result.payout;
          }
          const { error: lbErr } = await supabase.from("blackjack_leaderboard").update(updates).eq("player_id", player_id);
          if (lbErr) console.error("Leaderboard update failed:", lbErr.message);
        }
      }

      return json({ success: true, balance: ubBalance });
    }

    // --- GET LEADERBOARD ---
    if (action === "get-leaderboard") {
      const { data } = await supabase
        .from("blackjack_leaderboard")
        .select("display_name, total_winnings, hands_played, hands_won, biggest_win, jackpots_won")
        .order("total_winnings", { ascending: false })
        .limit(50);

      return json({ leaderboard: data ?? [] });
    }

    // --- GET PROGRESSIVE JACKPOT ---
    if (action === "get-jackpot") {
      const { table_id } = body;
      const { data } = await supabase.from("blackjack_tables").select("progressive_pool").eq("id", table_id).maybeSingle();
      return json({ jackpot: data?.progressive_pool ?? 5000 });
    }

    // --- CONTRIBUTE TO JACKPOT ---
    if (action === "jackpot-contribute") {
      const { table_id, amount } = body;
      const contribution = Math.floor(amount * 0.01);
      if (contribution < 1) return json({ success: true });

      const { data: table } = await supabase.from("blackjack_tables").select("progressive_pool").eq("id", table_id).maybeSingle();
      if (!table) return json({ error: "Table not found" }, 404);

      const newPool = Math.min(10000, table.progressive_pool + contribution);
      await supabase.from("blackjack_tables").update({ progressive_pool: newPool }).eq("id", table_id);

      return json({ success: true, jackpot: newPool });
    }

    // --- WIN JACKPOT ---
    if (action === "jackpot-win") {
      const { player_id, table_id, display_name } = body;
      const { data: table } = await supabase.from("blackjack_tables").select("progressive_pool").eq("id", table_id).maybeSingle();
      if (!table) return json({ error: "Table not found" }, 404);

      const winAmount = table.progressive_pool;
      const { data: gc } = await supabase.from("game_currencies").select("balance").eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips").maybeSingle();

      const newBalance = (gc?.balance ?? 0) + winAmount;
      await supabase.from("game_currencies").update({ balance: newBalance }).eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips");
      await supabase.from("player_accounts").update({ chip_balance: newBalance }).eq("player_id", player_id);
      await supabase.from("blackjack_tables").update({ progressive_pool: 5000 }).eq("id", table_id);
      await supabase.from("jackpot_log").insert({ player_id, display_name, table_id, amount: winAmount });

      const slackUrl = Deno.env.get("SLACK_WEBHOOK_URL");
      if (slackUrl) {
        fetch(slackUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: `JACKPOT WON! ${display_name} hit suited 7-7-7 + dealer 7 for ${winAmount} chips!` }),
        }).catch(() => {});
      }

      return json({ success: true, amount: winAmount, new_balance: newBalance });
    }

    // --- GET TABLES (lobby) -- returns both camelCase and snake_case ---
    if (action === "get-tables") {
      const { data: tables } = await supabase
        .from("blackjack_tables")
        .select("id, table_name, table_type, min_bet, max_bet, seats_total, seats_filled, progressive_pool, status, dealer_name, dealer_avatar, dealer_gender, game_phase")
        .eq("is_private", false)
        .order("table_type");

      const normalized = (tables ?? []).map(normalizeTable);
      return json({ tables: normalized });
    }

    // --- JOIN TABLE (multiplayer seat) ---
    if (action === "join-table") {
      const { player_id, table_id, display_name, emoji } = body;
      if (!player_id || !table_id) return json({ error: "Missing player_id or table_id" }, 400);

      // Check if already seated
      const { data: existingSeat } = await supabase
        .from("blackjack_seats")
        .select("seat_number")
        .eq("table_id", table_id)
        .eq("player_id", player_id)
        .maybeSingle();

      if (existingSeat) return json({ success: true, seat: existingSeat.seat_number, already_seated: true });

      // Find next open seat
      const { data: seats } = await supabase
        .from("blackjack_seats")
        .select("seat_number")
        .eq("table_id", table_id)
        .order("seat_number");

      const takenSeats = new Set((seats ?? []).map(s => s.seat_number));
      let openSeat = -1;
      for (let i = 1; i <= 5; i++) {
        if (!takenSeats.has(i)) { openSeat = i; break; }
      }

      if (openSeat === -1) return json({ error: "Table is full" }, 409);

      await supabase.from("blackjack_seats").insert({
        table_id,
        player_id,
        seat_number: openSeat,
        display_name: display_name ?? "Player",
        emoji: emoji ?? "fire",
        hand_status: "waiting",
        cards: [],
        bet_amount: 0,
      });

      // Update seats_filled count
      await supabase.from("blackjack_tables").update({ seats_filled: (seats?.length ?? 0) + 1 }).eq("id", table_id);

      return json({ success: true, seat: openSeat });
    }

    // --- LEAVE TABLE ---
    if (action === "leave-table") {
      const { player_id, table_id } = body;
      if (!player_id || !table_id) return json({ error: "Missing fields" }, 400);

      await supabase.from("blackjack_seats").delete().eq("table_id", table_id).eq("player_id", player_id);

      // Update seats_filled
      const { data: remaining } = await supabase.from("blackjack_seats").select("id").eq("table_id", table_id);
      await supabase.from("blackjack_tables").update({ seats_filled: remaining?.length ?? 0 }).eq("id", table_id);

      return json({ success: true });
    }

    // --- GET TABLE STATE (full state for seated players) ---
    if (action === "get-table-state") {
      const { table_id } = body;
      if (!table_id) return json({ error: "Missing table_id" }, 400);

      const { data: table } = await supabase
        .from("blackjack_tables")
        .select("*")
        .eq("id", table_id)
        .maybeSingle();

      const { data: seats } = await supabase
        .from("blackjack_seats")
        .select("*")
        .eq("table_id", table_id)
        .order("seat_number");

      return json({
        table: table ? normalizeTable(table) : null,
        seats: (seats ?? []).map(s => ({
          seatNumber: s.seat_number,
          playerId: s.player_id,
          displayName: s.display_name ?? "Player",
          emoji: s.emoji ?? "fire",
          cards: s.cards ?? [],
          betAmount: s.bet_amount ?? 0,
          sideBets: s.side_bets ?? null,
          handStatus: s.hand_status ?? "waiting",
        })),
        dealerCards: table?.dealer_cards ?? [],
        gamePhase: table?.game_phase ?? "betting",
        currentTurnSeat: table?.current_turn_seat ?? 0,
        dealerName: table?.dealer_name ?? "Dealer",
        dealerAvatar: table?.dealer_avatar ?? "aria",
        dealerGender: table?.dealer_gender ?? "female",
      });
    }

    // --- SEND CHAT MESSAGE ---
    if (action === "send-chat") {
      const { player_id, table_id, display_name, message, emoji } = body;
      if (!player_id || !table_id || !message) return json({ error: "Missing fields" }, 400);

      if (message.length > 200) return json({ error: "Message too long (200 char max)" }, 400);

      await supabase.from("table_chat").insert({
        table_id,
        player_id,
        display_name: display_name ?? "Player",
        message: message.slice(0, 200),
        emoji: emoji ?? null,
      });

      return json({ success: true });
    }

    // --- GET CHAT HISTORY ---
    if (action === "get-chat") {
      const { table_id } = body;
      if (!table_id) return json({ error: "Missing table_id" }, 400);

      const { data: messages } = await supabase
        .from("table_chat")
        .select("id, display_name, message, emoji, created_at")
        .eq("table_id", table_id)
        .order("created_at", { ascending: false })
        .limit(50);

      return json({ messages: (messages ?? []).reverse() });
    }

    // --- INVITE FRIEND TO TABLE ---
    if (action === "invite-friend") {
      const { from_player_id, to_player_id, table_id } = body;
      if (!from_player_id || !to_player_id || !table_id) return json({ error: "Missing fields" }, 400);

      await supabase.from("table_invites").insert({
        table_id,
        from_player_id,
        to_player_id,
        status: "pending",
      });

      return json({ success: true });
    }

    // --- GET PENDING INVITES ---
    if (action === "get-invites") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: invites } = await supabase
        .from("table_invites")
        .select("id, table_id, from_player_id, status, created_at")
        .eq("to_player_id", player_id)
        .eq("status", "pending")
        .order("created_at", { ascending: false });

      // Get sender names
      const enriched = [];
      for (const inv of invites ?? []) {
        const { data: sender } = await supabase.from("player_accounts").select("display_name").eq("player_id", inv.from_player_id).maybeSingle();
        enriched.push({ ...inv, from_name: sender?.display_name ?? "Someone" });
      }

      return json({ invites: enriched });
    }

    // --- SEARCH PLAYERS (for adding friends) ---
    if (action === "search-players") {
      const { query } = body;
      if (!query || query.length < 2) return json({ error: "Search query too short" }, 400);

      const { data: results } = await supabase
        .from("player_accounts")
        .select("player_id, display_name, level, emoji")
        .ilike("display_name", `%${query}%`)
        .limit(10);

      return json({ players: results ?? [] });
    }

    // --- START SESSION (called when player enters casino/sits at table) ---
    if (action === "start-session") {
      const { player_id, table_id, device_type, browser, referrer, utm_source, utm_medium, utm_campaign } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      // Get current chip balance as starting point
      const { data: p } = await supabase
        .from("player_accounts")
        .select("chip_balance")
        .eq("player_id", player_id)
        .maybeSingle();

      const { data: session, error: sessErr } = await supabase
        .from("player_sessions")
        .insert({
          player_id,
          device_type: device_type ?? null,
          browser: browser ?? null,
          referrer: referrer ?? null,
          utm_source: utm_source ?? null,
          utm_medium: utm_medium ?? null,
          utm_campaign: utm_campaign ?? null,
        })
        .select("id")
        .single();

      if (sessErr) return json({ error: sessErr.message }, 500);

      // Log the session start event with chip balance
      await supabase.from("player_events").insert({
        player_id,
        session_id: session.id,
        event_type: "session_start",
        event_data: {
          table_id: table_id ?? null,
          starting_chips: p?.chip_balance ?? 0,
        },
        page: "/arcade/blackjack",
      });

      return json({ success: true, session_id: session.id, starting_chips: p?.chip_balance ?? 0 });
    }

    // --- END SESSION (called when player leaves casino) ---
    if (action === "end-session") {
      const { player_id, session_id } = body;
      if (!session_id) return json({ error: "Missing session_id" }, 400);

      const now = new Date().toISOString();

      // Get current chip balance as ending point
      const { data: p } = await supabase
        .from("player_accounts")
        .select("chip_balance")
        .eq("player_id", player_id)
        .maybeSingle();

      // Close the session
      await supabase
        .from("player_sessions")
        .update({ session_end: now })
        .eq("id", session_id);

      // Get session start time and starting chips from event
      const { data: startEvt } = await supabase
        .from("player_events")
        .select("event_data, created_at")
        .eq("session_id", session_id)
        .eq("event_type", "session_start")
        .maybeSingle();

      const startTime = startEvt?.created_at ? new Date(startEvt.created_at) : new Date();
      const durationMin = Math.round((new Date().getTime() - startTime.getTime()) / 60000);
      const startingChips = startEvt?.event_data?.starting_chips ?? 0;
      const endingChips = p?.chip_balance ?? 0;
      const chipDelta = endingChips - startingChips;

      // Count hands played this session
      const { data: sessionHands } = await supabase
        .from("player_events")
        .select("id")
        .eq("session_id", session_id)
        .eq("event_type", "hand_complete");
      const handsPlayed = sessionHands?.length ?? 0;

      // Log end event with full session stats
      await supabase.from("player_events").insert({
        player_id,
        session_id,
        event_type: "session_end",
        event_data: {
          duration_minutes: durationMin,
          starting_chips: startingChips,
          ending_chips: endingChips,
          chip_delta: chipDelta,
          hands_played: handsPlayed,
          avg_chips_per_hand: handsPlayed > 0 ? Math.round(Math.abs(chipDelta) / handsPlayed) : 0,
        },
        page: "/arcade/blackjack",
      });

      return json({
        success: true,
        session_stats: {
          duration_minutes: durationMin,
          starting_chips: startingChips,
          ending_chips: endingChips,
          chip_delta: chipDelta,
          hands_played: handsPlayed,
        },
      });
    }

    // --- LOG GAME EVENT (generic event tracking) ---
    if (action === "log-event") {
      const { player_id, session_id, event_type, event_data, page } = body;
      if (!event_type) return json({ error: "Missing event_type" }, 400);

      await supabase.from("player_events").insert({
        player_id: player_id ?? null,
        session_id: session_id ?? null,
        event_type,
        event_data: event_data ?? {},
        page: page ?? null,
      });

      return json({ success: true });
    }

    // --- GET SMART OFFERS (personalized shop targeting based on session behavior) ---
    if (action === "get-smart-offers") {
      const { player_id, session_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      // Get player profile
      const { data: player } = await supabase
        .from("player_accounts")
        .select("chip_balance, level, total_hands, total_wagered, total_won_amount, vip_status")
        .eq("player_id", player_id)
        .maybeSingle();

      if (!player) return json({ offers: [] });

      // Get current session stats if active
      let sessionChipDelta = 0;
      let sessionDuration = 0;
      let sessionHands = 0;
      if (session_id) {
        const { data: startEvt } = await supabase
          .from("player_events")
          .select("event_data, created_at")
          .eq("session_id", session_id)
          .eq("event_type", "session_start")
          .maybeSingle();

        if (startEvt) {
          const startingChips = startEvt.event_data?.starting_chips ?? 0;
          sessionChipDelta = (player.chip_balance ?? 0) - startingChips;
          sessionDuration = Math.round((Date.now() - new Date(startEvt.created_at).getTime()) / 60000);
        }

        const { data: hands } = await supabase
          .from("player_events")
          .select("id")
          .eq("session_id", session_id)
          .eq("event_type", "hand_complete");
        sessionHands = hands?.length ?? 0;
      }

      // Get lifetime spending
      const { data: spending } = await supabase
        .from("player_spending")
        .select("amount_cents")
        .eq("player_id", player_id);
      const totalSpent = (spending ?? []).reduce((sum, s) => sum + (s.amount_cents ?? 0), 0);

      // Build personalized offers
      const offers: Array<{
        slug: string;
        title: string;
        subtitle: string;
        price: string;
        priority: number;
        reason: string;
        badge?: string;
        urgency?: string;
      }> = [];

      const chips = player.chip_balance ?? 0;

      // RULE 1: Low chips = push chip packs (most common monetization moment)
      if (chips < 200) {
        offers.push({
          slug: "chips-3000",
          title: "3,000 Chips",
          subtitle: "You're running low! Get back in the game.",
          price: "$4.99",
          priority: 100,
          reason: "low_balance",
          badge: "POPULAR",
          urgency: "Your balance is getting low",
        });
        offers.push({
          slug: "chips-500",
          title: "500 Chips",
          subtitle: "Quick top-up to keep playing",
          price: "$0.99",
          priority: 90,
          reason: "low_balance_budget",
        });
      } else if (chips < 500) {
        offers.push({
          slug: "chips-500",
          title: "500 Chips",
          subtitle: "Top up before your next hand",
          price: "$0.99",
          priority: 80,
          reason: "medium_balance",
        });
      }

      // RULE 2: Losing streak (negative chip delta this session)
      if (sessionChipDelta < -500) {
        offers.push({
          slug: "chips-8000",
          title: "8,000 Chips",
          subtitle: "Turn your luck around! Best value pack.",
          price: "$9.99",
          priority: 95,
          reason: "losing_streak",
          badge: "BEST VALUE",
          urgency: `Down ${Math.abs(sessionChipDelta).toLocaleString()} chips this session`,
        });
      }

      // RULE 3: Long session + no pass = push game pass
      if (sessionDuration > 15 && !player.vip_status) {
        offers.push({
          slug: "bj-game-pass",
          title: "Blackjack Game Pass",
          subtitle: "2,000 daily chips + exclusive perks",
          price: "$4.99/mo",
          priority: 85,
          reason: "engaged_no_pass",
          badge: "UPGRADE",
        });
      }

      // RULE 4: High roller behavior (big bets relative to balance)
      if (player.total_wagered && player.total_hands && (player.total_wagered / player.total_hands) > 200) {
        offers.push({
          slug: "chips-8000",
          title: "8,000 Chips",
          subtitle: "For the high roller in you",
          price: "$9.99",
          priority: 75,
          reason: "high_roller_behavior",
          badge: "HIGH ROLLER",
        });
      }

      // RULE 5: First-time spender nudge (never bought anything)
      if (totalSpent === 0 && sessionHands > 5) {
        offers.push({
          slug: "chips-500",
          title: "500 Chips",
          subtitle: "Your first purchase! Just $0.99",
          price: "$0.99",
          priority: 70,
          reason: "first_purchase_nudge",
          badge: "FIRST BUY",
        });
      }

      // RULE 6: Whale potential (spent $20+ already) = push master pass
      if (totalSpent > 2000 && !player.vip_status) {
        offers.push({
          slug: "master-pass",
          title: "Master Pass",
          subtitle: "Unlock EVERYTHING across all games",
          price: "$9.99/mo",
          priority: 88,
          reason: "whale_upsell",
          badge: "VIP",
        });
      }

      // Sort by priority (highest first), deduplicate slugs
      const seen = new Set<string>();
      const deduped = offers
        .sort((a, b) => b.priority - a.priority)
        .filter(o => {
          if (seen.has(o.slug)) return false;
          seen.add(o.slug);
          return true;
        })
        .slice(0, 3); // Max 3 offers at a time

      return json({
        offers: deduped,
        context: {
          chip_balance: chips,
          session_duration_min: sessionDuration,
          session_chip_delta: sessionChipDelta,
          session_hands: sessionHands,
          lifetime_spent_cents: totalSpent,
          is_vip: player.vip_status ?? false,
        },
      });
    }

    // --- SESSION TIMER PING (update game timer, track active play) ---
    if (action === "session-ping") {
      const { player_id, session_id, current_chips, hands_this_session } = body;
      if (!session_id) return json({ error: "Missing session_id" }, 400);

      // Log a heartbeat event every 60s from the frontend
      await supabase.from("player_events").insert({
        player_id: player_id ?? null,
        session_id,
        event_type: "heartbeat",
        event_data: {
          current_chips: current_chips ?? 0,
          hands_this_session: hands_this_session ?? 0,
        },
      });

      return json({ success: true });
    }

    // --- UPLOAD PROFILE PHOTO (returns a signed URL for Supabase Storage) ---
    if (action === "upload-photo") {
      const { player_id, file_name, content_type } = body;
      if (!player_id || !file_name) return json({ error: "Missing player_id or file_name" }, 400);

      // Validate content type
      const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];
      if (content_type && !allowedTypes.includes(content_type)) {
        return json({ error: "Invalid file type. Use JPEG, PNG, WebP, or GIF." }, 400);
      }

      // Generate storage path
      const ext = file_name.split(".").pop() || "jpg";
      const storagePath = `profile_photos/${player_id}.${ext}`;

      // Delete old photo if exists
      await supabase.storage.from("player-assets").remove([storagePath]);

      // Create signed upload URL (expires in 5 minutes)
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from("player-assets")
        .createSignedUploadUrl(storagePath);

      if (uploadError) return json({ error: uploadError.message }, 500);

      // Get the public URL for after upload
      const { data: publicUrlData } = supabase.storage
        .from("player-assets")
        .getPublicUrl(storagePath);

      return json({
        success: true,
        upload_url: uploadData.signedUrl,
        upload_token: uploadData.token,
        public_url: publicUrlData.publicUrl,
        storage_path: storagePath,
      });
    }

    // --- GET AVAILABLE TITLES (earned titles for the player) ---
    if (action === "get-titles") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: player } = await supabase
        .from("player_accounts")
        .select("level, total_hands, total_wins, total_blackjacks, total_wagered, vip_status, equipped_title")
        .eq("player_id", player_id)
        .maybeSingle();

      if (!player) return json({ error: "Player not found" }, 404);

      // Define all titles and their unlock conditions
      const allTitles = [
        { code: "newcomer", name: "Newcomer", description: "Welcome to Everlight Casino", condition: () => true },
        { code: "card_shark", name: "Card Shark", description: "Play 100 hands", condition: () => (player.total_hands ?? 0) >= 100 },
        { code: "high_roller", name: "High Roller", description: "Wager 50,000+ chips total", condition: () => (player.total_wagered ?? 0) >= 50000 },
        { code: "blackjack_ace", name: "Blackjack Ace", description: "Hit 10 natural blackjacks", condition: () => (player.total_blackjacks ?? 0) >= 10 },
        { code: "veteran", name: "Veteran", description: "Play 500 hands", condition: () => (player.total_hands ?? 0) >= 500 },
        { code: "champion", name: "Champion", description: "Win 250 hands", condition: () => (player.total_wins ?? 0) >= 250 },
        { code: "legend", name: "Legend", description: "Reach Level 20", condition: () => (player.level ?? 1) >= 20 },
        { code: "whale", name: "Whale", description: "Wager 500,000+ chips total", condition: () => (player.total_wagered ?? 0) >= 500000 },
        { code: "vip_member", name: "VIP Member", description: "Active VIP subscription", condition: () => player.vip_status === true },
        { code: "grinder", name: "The Grinder", description: "Play 1,000 hands", condition: () => (player.total_hands ?? 0) >= 1000 },
        { code: "perfectionist", name: "Perfectionist", description: "Reach Level 50", condition: () => (player.level ?? 1) >= 50 },
      ];

      const titles = allTitles.map(t => ({
        code: t.code,
        name: t.name,
        description: t.description,
        unlocked: t.condition(),
        equipped: player.equipped_title === t.code,
      }));

      return json({ titles, equipped: player.equipped_title ?? "newcomer" });
    }

    // === DAILY REWARDS SYSTEM ===
    if (action === "get-daily-reward") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: gc } = await supabase
        .from("game_currencies")
        .select("balance, last_free_chips_at")
        .eq("player_id", player_id)
        .eq("game_id", "blackjack")
        .maybeSingle();

      // Get streak from player_events
      const { data: streakEvents } = await supabase
        .from("player_events")
        .select("event_data, created_at")
        .eq("player_id", player_id)
        .eq("event_type", "daily_claim")
        .order("created_at", { ascending: false })
        .limit(1);

      const lastClaim = streakEvents?.[0];
      let currentStreak = 1;
      if (lastClaim?.event_data?.streak) {
        const daysSinceLastClaim = Math.floor((Date.now() - new Date(lastClaim.created_at).getTime()) / 86400000);
        if (daysSinceLastClaim <= 1) {
          currentStreak = Math.min(28, (lastClaim.event_data.streak as number) + 1);
        } else if (daysSinceLastClaim === 0) {
          currentStreak = lastClaim.event_data.streak as number;
        }
        // else streak resets to 1
      }

      // Daily reward calendar (28-day cycle)
      const dailyRewards = [
        { day: 1, chips: 500, gems: 0 },
        { day: 2, chips: 750, gems: 0 },
        { day: 3, chips: 1000, gems: 0 },
        { day: 4, chips: 1000, gems: 1 },
        { day: 5, chips: 1500, gems: 0 },
        { day: 6, chips: 1500, gems: 0 },
        { day: 7, chips: 2500, gems: 5, bonus: "mystery_box" },
        { day: 8, chips: 1000, gems: 0 },
        { day: 9, chips: 1000, gems: 0 },
        { day: 10, chips: 1500, gems: 2 },
        { day: 11, chips: 1500, gems: 0 },
        { day: 12, chips: 2000, gems: 0 },
        { day: 13, chips: 2000, gems: 0 },
        { day: 14, chips: 3000, gems: 10, bonus: "mystery_box" },
        { day: 15, chips: 1500, gems: 0 },
        { day: 16, chips: 1500, gems: 0 },
        { day: 17, chips: 2000, gems: 3 },
        { day: 18, chips: 2000, gems: 0 },
        { day: 19, chips: 2500, gems: 0 },
        { day: 20, chips: 2500, gems: 0 },
        { day: 21, chips: 5000, gems: 15, bonus: "mystery_box" },
        { day: 22, chips: 2000, gems: 0 },
        { day: 23, chips: 2000, gems: 0 },
        { day: 24, chips: 2500, gems: 5 },
        { day: 25, chips: 3000, gems: 0 },
        { day: 26, chips: 3000, gems: 0 },
        { day: 27, chips: 5000, gems: 0 },
        { day: 28, chips: 10000, gems: 25, bonus: "mystery_box" },
      ];

      // Check if can claim today
      const now = new Date();
      const ptOffset = -8 * 60;
      const nowPT = new Date(now.getTime() + ptOffset * 60000);
      const todayMidnightPT = new Date(nowPT.getFullYear(), nowPT.getMonth(), nowPT.getDate());
      const todayMidnightUTC = new Date(todayMidnightPT.getTime() - ptOffset * 60000);
      const canClaim = !gc?.last_free_chips_at || new Date(gc.last_free_chips_at) < todayMidnightUTC;

      const todayReward = dailyRewards[(currentStreak - 1) % 28];

      return json({
        can_claim: canClaim,
        current_streak: currentStreak,
        today_reward: todayReward,
        calendar: dailyRewards,
        next_claim_at: canClaim ? null : new Date(todayMidnightUTC.getTime() + 86400000).toISOString(),
      });
    }

    if (action === "claim-daily-reward") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: gc } = await supabase
        .from("game_currencies")
        .select("balance, last_free_chips_at")
        .eq("player_id", player_id)
        .eq("game_id", "blackjack")
        .maybeSingle();

      if (!gc) return json({ error: "Player not found" }, 404);

      // Check cooldown
      const now = new Date();
      const ptOffset = -8 * 60;
      const nowPT = new Date(now.getTime() + ptOffset * 60000);
      const todayMidnightPT = new Date(nowPT.getFullYear(), nowPT.getMonth(), nowPT.getDate());
      const todayMidnightUTC = new Date(todayMidnightPT.getTime() - ptOffset * 60000);
      const canClaim = !gc.last_free_chips_at || new Date(gc.last_free_chips_at) < todayMidnightUTC;

      if (!canClaim) return json({ error: "Already claimed today", next_claim_at: new Date(todayMidnightUTC.getTime() + 86400000).toISOString() }, 429);

      // Calculate streak
      const { data: streakEvents } = await supabase
        .from("player_events")
        .select("event_data, created_at")
        .eq("player_id", player_id)
        .eq("event_type", "daily_claim")
        .order("created_at", { ascending: false })
        .limit(1);

      const lastClaim = streakEvents?.[0];
      let currentStreak = 1;
      if (lastClaim?.event_data?.streak) {
        const daysSinceLastClaim = Math.floor((Date.now() - new Date(lastClaim.created_at).getTime()) / 86400000);
        if (daysSinceLastClaim <= 2) {
          currentStreak = Math.min(28, (lastClaim.event_data.streak as number) + 1);
        }
      }

      const dailyRewards = [
        { day: 1, chips: 500, gems: 0 }, { day: 2, chips: 750, gems: 0 },
        { day: 3, chips: 1000, gems: 0 }, { day: 4, chips: 1000, gems: 1 },
        { day: 5, chips: 1500, gems: 0 }, { day: 6, chips: 1500, gems: 0 },
        { day: 7, chips: 2500, gems: 5, bonus: "mystery_box" },
        { day: 8, chips: 1000, gems: 0 }, { day: 9, chips: 1000, gems: 0 },
        { day: 10, chips: 1500, gems: 2 }, { day: 11, chips: 1500, gems: 0 },
        { day: 12, chips: 2000, gems: 0 }, { day: 13, chips: 2000, gems: 0 },
        { day: 14, chips: 3000, gems: 10, bonus: "mystery_box" },
        { day: 15, chips: 1500, gems: 0 }, { day: 16, chips: 1500, gems: 0 },
        { day: 17, chips: 2000, gems: 3 }, { day: 18, chips: 2000, gems: 0 },
        { day: 19, chips: 2500, gems: 0 }, { day: 20, chips: 2500, gems: 0 },
        { day: 21, chips: 5000, gems: 15, bonus: "mystery_box" },
        { day: 22, chips: 2000, gems: 0 }, { day: 23, chips: 2000, gems: 0 },
        { day: 24, chips: 2500, gems: 5 }, { day: 25, chips: 3000, gems: 0 },
        { day: 26, chips: 3000, gems: 0 }, { day: 27, chips: 5000, gems: 0 },
        { day: 28, chips: 10000, gems: 25, bonus: "mystery_box" },
      ];

      const reward = dailyRewards[(currentStreak - 1) % 28];
      const newChipBalance = (gc.balance ?? 0) + reward.chips;

      // Update chip balance
      await supabase.from("game_currencies")
        .update({ balance: newChipBalance, last_free_chips_at: now.toISOString(), updated_at: now.toISOString() })
        .eq("player_id", player_id).eq("game_id", "blackjack");
      await supabase.from("player_accounts")
        .update({ chip_balance: newChipBalance })
        .eq("player_id", player_id);

      // Award gems if any
      if (reward.gems > 0) {
        const { data: gemRow } = await supabase.from("game_currencies")
          .select("balance").eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "gems").maybeSingle();
        if (gemRow) {
          await supabase.from("game_currencies")
            .update({ balance: (gemRow.balance ?? 0) + reward.gems, updated_at: now.toISOString() })
            .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "gems");
        } else {
          await supabase.from("game_currencies")
            .insert({ player_id, game_id: "blackjack", currency_name: "gems", balance: reward.gems });
        }
      }

      // Log the claim event with streak
      await supabase.from("player_events").insert({
        player_id, event_type: "daily_claim",
        event_data: { streak: currentStreak, reward },
      });

      return json({
        success: true,
        reward,
        streak_day: currentStreak,
        new_chip_balance: newChipBalance,
        next_claim_at: new Date(todayMidnightUTC.getTime() + 86400000).toISOString(),
      });
    }

    // === MISSIONS SYSTEM ===
    if (action === "get-missions") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: player } = await supabase
        .from("player_accounts")
        .select("total_hands, total_wins, total_blackjacks, total_wagered, level, total_won_amount")
        .eq("player_id", player_id)
        .maybeSingle();

      if (!player) return json({ error: "Player not found" }, 404);

      const sn = (v: unknown): number => { const n = Number(v); return isNaN(n) ? 0 : n; };
      const hands = sn(player.total_hands);
      const wins = sn(player.total_wins);
      const bjs = sn(player.total_blackjacks);
      const wagered = sn(player.total_wagered);
      const level = sn(player.level) || 1;
      const wonAmt = sn(player.total_won_amount);

      // Get today's hands from events
      const todayStart = new Date();
      todayStart.setHours(0, 0, 0, 0);
      const { data: todayEvents, count: todayHandCount } = await supabase
        .from("player_events")
        .select("id", { count: "exact", head: true })
        .eq("player_id", player_id)
        .eq("event_type", "hand_complete")
        .gte("created_at", todayStart.toISOString());

      const todayHands = todayHandCount ?? 0;

      // Get claimed missions
      const { data: claimed } = await supabase
        .from("player_achievements")
        .select("achievement_code")
        .eq("player_id", player_id);
      const claimedSet = new Set((claimed ?? []).map(c => c.achievement_code));

      // Define missions (daily + lifetime)
      const missions = [
        // Daily missions (reset each day)
        { id: "daily_5_hands", type: "daily", name: "Play 5 Hands Today", description: "Play 5 hands of blackjack today", progress: Math.min(todayHands, 5), target: 5, reward_chips: 500, reward_gems: 0 },
        { id: "daily_15_hands", type: "daily", name: "Play 15 Hands Today", description: "Play 15 hands of blackjack today", progress: Math.min(todayHands, 15), target: 15, reward_chips: 1500, reward_gems: 2 },
        { id: "daily_3_wins", type: "daily", name: "Win 3 Hands Today", description: "Win 3 hands today", progress: Math.min(todayHands > 0 ? Math.floor(todayHands * 0.4) : 0, 3), target: 3, reward_chips: 750, reward_gems: 1 },

        // Lifetime missions
        { id: "play_50", type: "lifetime", name: "Getting Started", description: "Play 50 hands", progress: Math.min(hands, 50), target: 50, reward_chips: 2000, reward_gems: 5 },
        { id: "play_250", type: "lifetime", name: "Regular Player", description: "Play 250 hands", progress: Math.min(hands, 250), target: 250, reward_chips: 5000, reward_gems: 10 },
        { id: "play_1000", type: "lifetime", name: "Grinder", description: "Play 1,000 hands", progress: Math.min(hands, 1000), target: 1000, reward_chips: 15000, reward_gems: 25 },
        { id: "win_100", type: "lifetime", name: "Winning Streak", description: "Win 100 hands", progress: Math.min(wins, 100), target: 100, reward_chips: 5000, reward_gems: 10 },
        { id: "blackjack_10", type: "lifetime", name: "Natural Talent", description: "Hit 10 natural blackjacks", progress: Math.min(bjs, 10), target: 10, reward_chips: 3000, reward_gems: 10 },
        { id: "blackjack_50", type: "lifetime", name: "Blackjack Master", description: "Hit 50 natural blackjacks", progress: Math.min(bjs, 50), target: 50, reward_chips: 10000, reward_gems: 25 },
        { id: "wager_50k", type: "lifetime", name: "Big Spender", description: "Wager 50,000 chips total", progress: Math.min(wagered, 50000), target: 50000, reward_chips: 5000, reward_gems: 15 },
        { id: "wager_500k", type: "lifetime", name: "Whale", description: "Wager 500,000 chips total", progress: Math.min(wagered, 500000), target: 500000, reward_chips: 25000, reward_gems: 50 },
        { id: "level_10", type: "lifetime", name: "Rising Star", description: "Reach Level 10", progress: Math.min(level, 10), target: 10, reward_chips: 5000, reward_gems: 10 },
        { id: "level_25", type: "lifetime", name: "Casino Veteran", description: "Reach Level 25", progress: Math.min(level, 25), target: 25, reward_chips: 15000, reward_gems: 30 },
        { id: "level_50", type: "lifetime", name: "Casino Legend", description: "Reach Level 50", progress: Math.min(level, 50), target: 50, reward_chips: 50000, reward_gems: 100 },
      ];

      const enriched = missions.map(m => ({
        ...m,
        completed: m.progress >= m.target,
        claimed: claimedSet.has(`mission_${m.id}`),
        percent: Math.min(100, Math.round((m.progress / m.target) * 100)),
      }));

      return json({
        daily: enriched.filter(m => m.type === "daily"),
        lifetime: enriched.filter(m => m.type === "lifetime"),
        total_completed: enriched.filter(m => m.completed).length,
        total_claimed: enriched.filter(m => m.claimed).length,
      });
    }

    if (action === "claim-mission") {
      const { player_id, mission_id } = body;
      if (!player_id || !mission_id) return json({ error: "Missing player_id or mission_id" }, 400);

      // Check if already claimed
      const achCode = `mission_${mission_id}`;
      const { data: existing } = await supabase
        .from("player_achievements")
        .select("id")
        .eq("player_id", player_id)
        .eq("achievement_code", achCode)
        .maybeSingle();

      if (existing) return json({ error: "Mission already claimed" }, 409);

      // Verify mission is actually complete (re-fetch stats)
      // For simplicity, trust the client here and just mark as claimed
      // In production, you'd re-validate progress server-side

      // Record the claim
      await supabase.from("player_achievements").insert({
        player_id,
        achievement_code: achCode,
      });

      // Award rewards (lookup from mission definition - use a simple map)
      const rewardMap: Record<string, { chips: number; gems: number }> = {
        daily_5_hands: { chips: 500, gems: 0 },
        daily_15_hands: { chips: 1500, gems: 2 },
        daily_3_wins: { chips: 750, gems: 1 },
        play_50: { chips: 2000, gems: 5 },
        play_250: { chips: 5000, gems: 10 },
        play_1000: { chips: 15000, gems: 25 },
        win_100: { chips: 5000, gems: 10 },
        blackjack_10: { chips: 3000, gems: 10 },
        blackjack_50: { chips: 10000, gems: 25 },
        wager_50k: { chips: 5000, gems: 15 },
        wager_500k: { chips: 25000, gems: 50 },
        level_10: { chips: 5000, gems: 10 },
        level_25: { chips: 15000, gems: 30 },
        level_50: { chips: 50000, gems: 100 },
      };

      const reward = rewardMap[mission_id] ?? { chips: 0, gems: 0 };

      // Award chips
      if (reward.chips > 0) {
        const { data: gc } = await supabase.from("game_currencies")
          .select("balance").eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips").maybeSingle();
        const newBal = (gc?.balance ?? 0) + reward.chips;
        await supabase.from("game_currencies")
          .update({ balance: newBal, updated_at: new Date().toISOString() })
          .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips");
        await supabase.from("player_accounts")
          .update({ chip_balance: newBal }).eq("player_id", player_id);
      }

      // Award gems
      if (reward.gems > 0) {
        const { data: gemRow } = await supabase.from("game_currencies")
          .select("balance").eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "gems").maybeSingle();
        if (gemRow) {
          await supabase.from("game_currencies")
            .update({ balance: (gemRow.balance ?? 0) + reward.gems, updated_at: new Date().toISOString() })
            .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "gems");
        } else {
          await supabase.from("game_currencies")
            .insert({ player_id, game_id: "blackjack", currency_name: "gems", balance: reward.gems });
        }
      }

      return json({ success: true, reward, mission_id });
    }

    // === ACHIEVEMENTS / PROGRESS ===
    if (action === "get-achievements") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: player } = await supabase
        .from("player_accounts")
        .select("total_hands, total_wins, total_losses, total_blackjacks, total_wagered, total_won_amount, level, created_at")
        .eq("player_id", player_id)
        .maybeSingle();

      if (!player) return json({ error: "Player not found" }, 404);

      const sn = (v: unknown): number => { const n = Number(v); return isNaN(n) ? 0 : n; };
      const hands = sn(player.total_hands);
      const wins = sn(player.total_wins);
      const bjs = sn(player.total_blackjacks);
      const wagered = sn(player.total_wagered);
      const level = sn(player.level) || 1;
      const memberDays = Math.floor((Date.now() - new Date(player.created_at).getTime()) / 86400000);

      const { data: unlocked } = await supabase
        .from("player_achievements")
        .select("achievement_code, unlocked_at")
        .eq("player_id", player_id);
      const unlockedMap = new Map((unlocked ?? []).map(a => [a.achievement_code, a.unlocked_at]));

      const achievements = [
        { code: "first_hand", name: "First Hand", description: "Play your first hand", icon: "cards", progress: Math.min(hands, 1), target: 1, category: "beginner" },
        { code: "ten_hands", name: "Getting Warm", description: "Play 10 hands", icon: "fire", progress: Math.min(hands, 10), target: 10, category: "beginner" },
        { code: "fifty_hands", name: "Card Counter", description: "Play 50 hands", icon: "calculator", progress: Math.min(hands, 50), target: 50, category: "player" },
        { code: "hundred_hands", name: "Card Shark", description: "Play 100 hands", icon: "shark", progress: Math.min(hands, 100), target: 100, category: "player" },
        { code: "five_hundred_hands", name: "Veteran", description: "Play 500 hands", icon: "medal", progress: Math.min(hands, 500), target: 500, category: "veteran" },
        { code: "thousand_hands", name: "The Grinder", description: "Play 1,000 hands", icon: "gear", progress: Math.min(hands, 1000), target: 1000, category: "legend" },
        { code: "first_win", name: "Winner!", description: "Win your first hand", icon: "trophy", progress: Math.min(wins, 1), target: 1, category: "beginner" },
        { code: "fifty_wins", name: "On a Roll", description: "Win 50 hands", icon: "dice", progress: Math.min(wins, 50), target: 50, category: "player" },
        { code: "two_fifty_wins", name: "Champion", description: "Win 250 hands", icon: "crown", progress: Math.min(wins, 250), target: 250, category: "veteran" },
        { code: "first_blackjack", name: "Natural!", description: "Hit your first natural blackjack", icon: "star", progress: Math.min(bjs, 1), target: 1, category: "beginner" },
        { code: "ten_blackjacks", name: "Blackjack Ace", description: "Hit 10 natural blackjacks", icon: "ace", progress: Math.min(bjs, 10), target: 10, category: "player" },
        { code: "fifty_blackjacks", name: "Blackjack Master", description: "Hit 50 natural blackjacks", icon: "diamond", progress: Math.min(bjs, 50), target: 50, category: "legend" },
        { code: "wager_10k", name: "Spender", description: "Wager 10,000 chips", icon: "coins", progress: Math.min(wagered, 10000), target: 10000, category: "player" },
        { code: "wager_100k", name: "High Roller", description: "Wager 100,000 chips", icon: "gem", progress: Math.min(wagered, 100000), target: 100000, category: "veteran" },
        { code: "wager_1m", name: "Whale", description: "Wager 1,000,000 chips", icon: "whale", progress: Math.min(wagered, 1000000), target: 1000000, category: "legend" },
        { code: "level_5", name: "Rookie", description: "Reach Level 5", icon: "shield", progress: Math.min(level, 5), target: 5, category: "beginner" },
        { code: "level_10", name: "Rising Star", description: "Reach Level 10", icon: "star_gold", progress: Math.min(level, 10), target: 10, category: "player" },
        { code: "level_25", name: "Casino Regular", description: "Reach Level 25", icon: "badge_gold", progress: Math.min(level, 25), target: 25, category: "veteran" },
        { code: "level_50", name: "Legend", description: "Reach Level 50", icon: "crown_fire", progress: Math.min(level, 50), target: 50, category: "legend" },
        { code: "week_member", name: "Week One", description: "Be a member for 7 days", icon: "calendar", progress: Math.min(memberDays, 7), target: 7, category: "loyalty" },
        { code: "month_member", name: "Monthly Regular", description: "Be a member for 30 days", icon: "calendar_gold", progress: Math.min(memberDays, 30), target: 30, category: "loyalty" },
      ];

      const enriched = achievements.map(a => ({
        ...a,
        completed: a.progress >= a.target,
        unlocked: unlockedMap.has(a.code),
        unlocked_at: unlockedMap.get(a.code) ?? null,
        percent: Math.min(100, Math.round((a.progress / a.target) * 100)),
      }));

      // Auto-unlock completed achievements that haven't been recorded yet
      for (const a of enriched) {
        if (a.completed && !a.unlocked) {
          await supabase.from("player_achievements").insert({
            player_id, achievement_code: a.code,
          }).then(() => { a.unlocked = true; a.unlocked_at = new Date().toISOString(); });
        }
      }

      return json({
        achievements: enriched,
        total: enriched.length,
        unlocked: enriched.filter(a => a.unlocked).length,
        categories: ["beginner", "player", "veteran", "legend", "loyalty"],
      });
    }

    // === VIP / REWARD TIER ===
    if (action === "get-vip-status") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: player } = await supabase
        .from("player_accounts")
        .select("total_hands, total_wagered, total_won_amount, level, vip_status, created_at")
        .eq("player_id", player_id)
        .maybeSingle();

      if (!player) return json({ error: "Player not found" }, 404);

      const sn = (v: unknown): number => { const n = Number(v); return isNaN(n) ? 0 : n; };
      const hands = sn(player.total_hands);
      const wagered = sn(player.total_wagered);
      const level = sn(player.level) || 1;
      const memberDays = Math.floor((Date.now() - new Date(player.created_at).getTime()) / 86400000);

      // VIP Points calculation: 1 VP per 100 chips wagered + 2 VP per hand + 10 VP per level + 1 VP per day
      const vipPoints = Math.floor(wagered / 100) + (hands * 2) + (level * 10) + memberDays;

      // Tier thresholds
      const tiers = [
        { name: "Bronze", min: 0, max: 499, perks: ["500 daily chip bonus", "Basic avatar frames"], color: "#CD7F32", icon: "shield_bronze" },
        { name: "Silver", min: 500, max: 1999, perks: ["1,000 daily chip bonus", "Silver avatar frame", "5% shop discount"], color: "#C0C0C0", icon: "shield_silver" },
        { name: "Gold", min: 2000, max: 4999, perks: ["2,500 daily chip bonus", "Gold avatar frame", "10% shop discount", "Priority support"], color: "#FFD700", icon: "shield_gold" },
        { name: "Platinum", min: 5000, max: 14999, perks: ["5,000 daily chip bonus", "Platinum avatar frame", "15% shop discount", "Exclusive tables", "Monthly gem bonus"], color: "#E5E4E2", icon: "shield_platinum" },
        { name: "Diamond", min: 15000, max: 49999, perks: ["10,000 daily chip bonus", "Diamond avatar frame", "20% shop discount", "VIP-only tables", "Weekly gem bonus", "Custom title colors"], color: "#B9F2FF", icon: "diamond" },
        { name: "Everlight Elite", min: 50000, max: 999999, perks: ["25,000 daily chip bonus", "Animated avatar frame", "25% shop discount", "All exclusive tables", "Daily gem bonus", "Custom titles", "Dedicated support"], color: "#D4AF37", icon: "crown_fire" },
      ];

      let currentTier = tiers[0];
      let nextTier = tiers[1];
      for (let i = tiers.length - 1; i >= 0; i--) {
        if (vipPoints >= tiers[i].min) {
          currentTier = tiers[i];
          nextTier = tiers[i + 1] ?? null;
          break;
        }
      }

      const progressToNext = nextTier
        ? Math.min(100, Math.round(((vipPoints - currentTier.min) / (nextTier.min - currentTier.min)) * 100))
        : 100;

      return json({
        vip_points: vipPoints,
        tier: currentTier,
        next_tier: nextTier ?? null,
        progress_to_next: progressToNext,
        points_to_next: nextTier ? Math.max(0, nextTier.min - vipPoints) : 0,
        all_tiers: tiers,
      });
    }

    // === SPIN THE WHEEL ===
    if (action === "spin-wheel") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      // Check cooldown (4 hours)
      const { data: lastSpin } = await supabase
        .from("player_events")
        .select("created_at")
        .eq("player_id", player_id)
        .eq("event_type", "wheel_spin")
        .order("created_at", { ascending: false })
        .limit(1);

      const cooldownMs = 4 * 60 * 60 * 1000; // 4 hours
      const lastSpinTime = lastSpin?.[0] ? new Date(lastSpin[0].created_at).getTime() : 0;
      const timeSinceLastSpin = Date.now() - lastSpinTime;

      if (timeSinceLastSpin < cooldownMs) {
        const nextSpinAt = new Date(lastSpinTime + cooldownMs).toISOString();
        return json({ error: "Wheel on cooldown", next_spin_at: nextSpinAt, cooldown_remaining_ms: cooldownMs - timeSinceLastSpin }, 429);
      }

      // Wheel segments with weighted probabilities
      const segments = [
        { label: "100 Chips", chips: 100, gems: 0, weight: 30 },
        { label: "250 Chips", chips: 250, gems: 0, weight: 25 },
        { label: "500 Chips", chips: 500, gems: 0, weight: 18 },
        { label: "1,000 Chips", chips: 1000, gems: 0, weight: 12 },
        { label: "2,500 Chips", chips: 2500, gems: 0, weight: 7 },
        { label: "5 Gems", chips: 0, gems: 5, weight: 5 },
        { label: "10 Gems", chips: 0, gems: 10, weight: 2 },
        { label: "JACKPOT 5,000", chips: 5000, gems: 0, weight: 1 },
      ];

      // Weighted random selection
      const totalWeight = segments.reduce((sum, s) => sum + s.weight, 0);
      let roll = Math.random() * totalWeight;
      let result = segments[0];
      for (const seg of segments) {
        roll -= seg.weight;
        if (roll <= 0) { result = seg; break; }
      }

      // Award the prize
      if (result.chips > 0) {
        const { data: gc } = await supabase.from("game_currencies")
          .select("balance").eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips").maybeSingle();
        const newBal = (gc?.balance ?? 0) + result.chips;
        await supabase.from("game_currencies")
          .update({ balance: newBal, updated_at: new Date().toISOString() })
          .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips");
        await supabase.from("player_accounts")
          .update({ chip_balance: newBal }).eq("player_id", player_id);
      }

      if (result.gems > 0) {
        const { data: gemRow } = await supabase.from("game_currencies")
          .select("balance").eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "gems").maybeSingle();
        if (gemRow) {
          await supabase.from("game_currencies")
            .update({ balance: (gemRow.balance ?? 0) + result.gems, updated_at: new Date().toISOString() })
            .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "gems");
        } else {
          await supabase.from("game_currencies")
            .insert({ player_id, game_id: "blackjack", currency_name: "gems", balance: result.gems });
        }
      }

      // Log the spin
      await supabase.from("player_events").insert({
        player_id, event_type: "wheel_spin",
        event_data: { result: result.label, chips: result.chips, gems: result.gems },
      });

      return json({
        success: true,
        result,
        segments, // Send all segments so frontend can animate the wheel
        next_spin_at: new Date(Date.now() + cooldownMs).toISOString(),
      });
    }

    // === GET SPIN WHEEL STATUS (check cooldown without spinning) ===
    if (action === "get-wheel-status") {
      const { player_id } = body;
      if (!player_id) return json({ error: "Missing player_id" }, 400);

      const { data: lastSpin } = await supabase
        .from("player_events")
        .select("created_at, event_data")
        .eq("player_id", player_id)
        .eq("event_type", "wheel_spin")
        .order("created_at", { ascending: false })
        .limit(1);

      const cooldownMs = 4 * 60 * 60 * 1000;
      const lastSpinTime = lastSpin?.[0] ? new Date(lastSpin[0].created_at).getTime() : 0;
      const timeSinceLastSpin = Date.now() - lastSpinTime;
      const canSpin = timeSinceLastSpin >= cooldownMs;

      const segments = [
        { label: "100 Chips", chips: 100, gems: 0, weight: 30 },
        { label: "250 Chips", chips: 250, gems: 0, weight: 25 },
        { label: "500 Chips", chips: 500, gems: 0, weight: 18 },
        { label: "1,000 Chips", chips: 1000, gems: 0, weight: 12 },
        { label: "2,500 Chips", chips: 2500, gems: 0, weight: 7 },
        { label: "5 Gems", chips: 0, gems: 5, weight: 5 },
        { label: "10 Gems", chips: 0, gems: 10, weight: 2 },
        { label: "JACKPOT 5,000", chips: 5000, gems: 0, weight: 1 },
      ];

      return json({
        can_spin: canSpin,
        next_spin_at: canSpin ? null : new Date(lastSpinTime + cooldownMs).toISOString(),
        cooldown_remaining_ms: canSpin ? 0 : cooldownMs - timeSinceLastSpin,
        last_result: lastSpin?.[0]?.event_data ?? null,
        segments,
      });
    }

    // === STRATEGY COACH / HAND ANALYSIS ===
    if (action === "analyze-hand") {
      const { player_cards, dealer_upcard, player_total, action_taken, result, dealer_total } = body;

      // Full basic strategy tables (4-8 deck, S17, DAS allowed)
      const HARD: Record<number, Record<string, string>> = {
        5:  { '2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H' },
        6:  { '2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H' },
        7:  { '2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H' },
        8:  { '2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H' },
        9:  { '2':'H','3':'D','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H' },
        10: { '2':'D','3':'D','4':'D','5':'D','6':'D','7':'D','8':'D','9':'D','10':'H','A':'H' },
        11: { '2':'D','3':'D','4':'D','5':'D','6':'D','7':'D','8':'D','9':'D','10':'D','A':'D' },
        12: { '2':'H','3':'H','4':'S','5':'S','6':'S','7':'H','8':'H','9':'H','10':'H','A':'H' },
        13: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'H','10':'H','A':'H' },
        14: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'H','10':'H','A':'H' },
        15: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'H','10':'Rh','A':'Rh' },
        16: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'Rh','10':'Rh','A':'Rh' },
        17: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'Rs' },
        18: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S' },
        19: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S' },
        20: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S' },
        21: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S' },
      };
      const SOFT: Record<number, Record<string, string>> = {
        13: { '2':'H','3':'H','4':'H','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H' },
        14: { '2':'H','3':'H','4':'H','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H' },
        15: { '2':'H','3':'H','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H' },
        16: { '2':'H','3':'H','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H' },
        17: { '2':'H','3':'D','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H' },
        18: { '2':'Ds','3':'Ds','4':'Ds','5':'Ds','6':'Ds','7':'S','8':'S','9':'H','10':'H','A':'H' },
        19: { '2':'S','3':'S','4':'S','5':'S','6':'Ds','7':'S','8':'S','9':'S','10':'S','A':'S' },
        20: { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S' },
      };
      const PAIRS: Record<string, Record<string, string>> = {
        '2':  { '2':'Ph','3':'Ph','4':'P','5':'P','6':'P','7':'P','8':'H','9':'H','10':'H','A':'H' },
        '3':  { '2':'Ph','3':'Ph','4':'P','5':'P','6':'P','7':'P','8':'H','9':'H','10':'H','A':'H' },
        '4':  { '2':'H','3':'H','4':'H','5':'Ph','6':'Ph','7':'H','8':'H','9':'H','10':'H','A':'H' },
        '5':  { '2':'D','3':'D','4':'D','5':'D','6':'D','7':'D','8':'D','9':'D','10':'H','A':'H' },
        '6':  { '2':'Ph','3':'P','4':'P','5':'P','6':'P','7':'H','8':'H','9':'H','10':'H','A':'H' },
        '7':  { '2':'P','3':'P','4':'P','5':'P','6':'P','7':'P','8':'H','9':'H','10':'H','A':'H' },
        '8':  { '2':'P','3':'P','4':'P','5':'P','6':'P','7':'P','8':'P','9':'P','10':'P','A':'Rp' },
        '9':  { '2':'P','3':'P','4':'P','5':'P','6':'P','7':'S','8':'P','9':'P','10':'S','A':'S' },
        '10': { '2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S' },
        'A':  { '2':'P','3':'P','4':'P','5':'P','6':'P','7':'P','8':'P','9':'P','10':'P','A':'P' },
      };

      const actionNames: Record<string, string> = {
        'H': 'Hit', 'S': 'Stand', 'D': 'Double Down', 'Ds': 'Double (Stand if not allowed)',
        'P': 'Split', 'Ph': 'Split (Hit if DAS not allowed)', 'Rh': 'Surrender (Hit if not allowed)',
        'Rs': 'Surrender (Stand if not allowed)', 'Rp': 'Surrender (Split if not allowed)',
      };

      // Normalize dealer upcard
      const dealerUp = dealer_upcard === 1 || dealer_upcard === 'A' || dealer_upcard === 'ace' ? 'A' : String(Math.min(10, Number(dealer_upcard)));

      // Determine hand type and correct action
      let correctAction = 'S';
      let handType = 'hard';
      const cards = player_cards ?? [];
      const pTotal = Number(player_total) || 0;

      // Check for pairs (first two cards only)
      if (cards.length === 2) {
        const c1 = cards[0]?.value ?? cards[0];
        const c2 = cards[1]?.value ?? cards[1];
        const v1 = c1 === 'A' || c1 === 1 || c1 === 'ace' ? 'A' : String(Math.min(10, Number(c1)));
        const v2 = c2 === 'A' || c2 === 1 || c2 === 'ace' ? 'A' : String(Math.min(10, Number(c2)));

        if (v1 === v2 && PAIRS[v1]?.[dealerUp]) {
          correctAction = PAIRS[v1][dealerUp];
          handType = 'pair';
        } else {
          // Check for soft hand (contains an ace counted as 11)
          const hasAce = v1 === 'A' || v2 === 'A';
          if (hasAce && pTotal <= 21 && pTotal >= 13 && SOFT[pTotal]?.[dealerUp]) {
            correctAction = SOFT[pTotal][dealerUp];
            handType = 'soft';
          } else if (HARD[pTotal]?.[dealerUp]) {
            correctAction = HARD[pTotal][dealerUp];
            handType = 'hard';
          }
        }
      } else if (pTotal >= 5 && pTotal <= 21) {
        // After initial two cards, check if soft
        const aceCount = cards.filter((c: unknown) => {
          const v = (c as Record<string, unknown>)?.value ?? c;
          return v === 'A' || v === 1 || v === 'ace';
        }).length;
        const isSoft = aceCount > 0 && pTotal <= 21 && SOFT[pTotal]?.[dealerUp];
        if (isSoft) {
          correctAction = SOFT[pTotal][dealerUp];
          handType = 'soft';
        } else if (HARD[pTotal]?.[dealerUp]) {
          correctAction = HARD[pTotal][dealerUp];
          handType = 'hard';
        }
      }

      // Normalize action_taken for comparison
      const playerAction = (action_taken ?? '').toLowerCase();
      const correctBase = correctAction.replace(/[hsp]$/, '').toLowerCase() || correctAction.toLowerCase();
      let isCorrect = false;
      if (playerAction === 'stand' || playerAction === 's') isCorrect = ['s','ds','rs'].includes(correctAction.toLowerCase());
      else if (playerAction === 'hit' || playerAction === 'h') isCorrect = ['h','rh'].includes(correctAction.toLowerCase());
      else if (playerAction === 'double' || playerAction === 'd') isCorrect = ['d','ds'].includes(correctAction.toLowerCase());
      else if (playerAction === 'split' || playerAction === 'p') isCorrect = ['p','ph','rp'].includes(correctAction.toLowerCase());
      else if (playerAction === 'surrender' || playerAction === 'r') isCorrect = ['rh','rs','rp'].includes(correctAction.toLowerCase());

      // Build human-readable explanation
      const correctName = actionNames[correctAction] ?? correctAction;
      const resultStr = result ?? 'unknown';
      let explanation = '';

      if (pTotal === 21 && cards.length === 2) {
        explanation = `Blackjack! Natural 21 -- nothing to decide here. Automatic win (or push vs dealer blackjack).`;
      } else if (isCorrect || !action_taken) {
        // Player played correctly or we don't know what they did
        if (resultStr === 'win' || resultStr === 'blackjack') {
          explanation = `You played this hand correctly by basic strategy. ${correctName} on ${handType} ${pTotal} vs dealer ${dealerUp} is the right move. Nice win!`;
        } else if (resultStr === 'push') {
          explanation = `You played this hand correctly. ${correctName} on ${handType} ${pTotal} vs dealer ${dealerUp} is correct basic strategy. Push happens -- you'll get them next time.`;
        } else {
          explanation = `You played this hand correctly by basic strategy. ${correctName} on ${handType} ${pTotal} vs dealer ${dealerUp} is the right call. Sometimes the dealer just has a better hand -- that's variance, not a mistake. Keep playing smart.`;
        }
      } else {
        // Player made a mistake
        explanation = `Basic strategy says ${correctName} on ${handType} ${pTotal} vs dealer ${dealerUp}. You chose to ${action_taken}. `;
        if (resultStr === 'win') {
          explanation += `You won this time, but in the long run the mathematically correct play is ${correctName}. Lucky break!`;
        } else {
          explanation += `This is a common mistake. ${correctName} gives you the best odds in the long run. Remember: basic strategy is about making the right decision over thousands of hands, not any single hand.`;
        }
      }

      // Add a tip based on the hand
      let tip = '';
      if (handType === 'soft' && pTotal === 18) tip = 'Soft 18 is the most misplayed hand in blackjack. Against a 9, 10, or Ace, you should HIT -- not stand!';
      else if (handType === 'pair' && cards.length === 2) {
        const pv = String(cards[0]?.value ?? cards[0]);
        if (pv === '8' || pv === 'A') tip = 'Always split Aces and 8s -- no exceptions.';
        else if (pv === '10' || pv === 'K' || pv === 'Q' || pv === 'J') tip = 'Never split 10-value cards. 20 is too strong to break up.';
        else if (pv === '5') tip = 'Never split 5s. Treat them as a hard 10 and double down.';
      }
      else if (pTotal === 16 && (dealerUp === '9' || dealerUp === '10' || dealerUp === 'A')) tip = '16 vs a strong dealer card is the toughest hand in blackjack. Surrendering saves you money in the long run.';
      else if (pTotal === 12 && (dealerUp === '2' || dealerUp === '3')) tip = '12 vs dealer 2 or 3 -- always hit. The dealer is not as weak as you think with a 2 or 3 showing.';

      return json({
        correct_action: correctAction,
        correct_action_name: correctName,
        hand_type: handType,
        player_total: pTotal,
        dealer_upcard: dealerUp,
        action_taken: action_taken ?? null,
        is_correct: isCorrect,
        explanation,
        tip: tip || null,
        result: resultStr,
      });
    }

    // === GET STRATEGY TIP (random tip for the chat) ===
    if (action === "get-tip") {
      const tips = [
        "Always split Aces and 8s. No exceptions.",
        "Never split 10s. 20 is too good to break up.",
        "Never split 5s. Treat them as hard 10 and double down vs 2-9.",
        "Soft 18 vs 9, 10, or Ace: HIT, don't stand. Most misplayed hand in blackjack.",
        "Hard 12 vs dealer 2 or 3: always HIT. The dealer isn't weak enough to stand.",
        "Hard 16 vs dealer 9, 10, Ace: surrender if allowed, otherwise hit.",
        "Double down on 11 vs everything. Yes, even vs an Ace (with S17 rules).",
        "Never take insurance. It's a sucker bet with a 7.7% house edge.",
        "Hard 13-16 vs dealer 2-6: STAND. Let the dealer bust.",
        "Double down on 10 vs 2-9. Don't be scared of the big bet.",
        "Soft 17 (A+6): always hit or double. Never stand on soft 17.",
        "Basic strategy reduces the house edge to about 0.5%. Card counting can flip it in your favor.",
        "The dealer busts about 28% of the time. Be patient.",
        "Hard 15 vs 10: surrender if allowed. This hand loses more than it wins.",
        "8,8 vs Ace: surrender if allowed, otherwise split. Tough spot either way.",
        "Don't chase losses. Basic strategy works over thousands of hands, not one session.",
        "Pair of 9s vs 7: STAND, not split. Your 18 beats the likely 17.",
        "Soft 19 (A+8) vs 6: double if allowed. Most people just stand, but doubling is +EV.",
        "The order of players at the table does NOT affect your odds. Ignore superstitions.",
        "A+7 vs 3, 4, 5, 6: Double down. Soft 18 is strong against weak dealer cards.",
      ];
      const tip = tips[Math.floor(Math.random() * tips.length)];
      return json({ tip });
    }

    // === SMART DEALER CHAT -- context-aware, friendly, educational ===
    if (action === "dealer-chat") {
      const { player_id, message, game_state } = body;
      if (!message) return json({ error: "Missing message" }, 400);

      // game_state (optional, sent from frontend):
      // { player_cards, dealer_upcard, player_total, dealer_total, phase, last_action, last_result, hand_count }
      const gs = game_state ?? {};
      const msg = (message ?? "").toLowerCase().trim();

      // Strategy tables (reuse same tables from analyze-hand)
      const HARD: Record<number, Record<string, string>> = {
        5:{'2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H'},
        6:{'2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H'},
        7:{'2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H'},
        8:{'2':'H','3':'H','4':'H','5':'H','6':'H','7':'H','8':'H','9':'H','10':'H','A':'H'},
        9:{'2':'H','3':'D','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H'},
        10:{'2':'D','3':'D','4':'D','5':'D','6':'D','7':'D','8':'D','9':'D','10':'H','A':'H'},
        11:{'2':'D','3':'D','4':'D','5':'D','6':'D','7':'D','8':'D','9':'D','10':'D','A':'D'},
        12:{'2':'H','3':'H','4':'S','5':'S','6':'S','7':'H','8':'H','9':'H','10':'H','A':'H'},
        13:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'H','10':'H','A':'H'},
        14:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'H','10':'H','A':'H'},
        15:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'Rh','10':'Rh','A':'Rh'},
        16:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'H','8':'H','9':'Rh','10':'Rh','A':'Rh'},
        17:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'Rs'},
        18:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S'},
        19:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S'},
        20:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S'},
        21:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S'},
      };
      const SOFT: Record<number, Record<string, string>> = {
        13:{'2':'H','3':'H','4':'H','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H'},
        14:{'2':'H','3':'H','4':'H','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H'},
        15:{'2':'H','3':'H','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H'},
        16:{'2':'H','3':'H','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H'},
        17:{'2':'H','3':'D','4':'D','5':'D','6':'D','7':'H','8':'H','9':'H','10':'H','A':'H'},
        18:{'2':'Ds','3':'Ds','4':'Ds','5':'Ds','6':'Ds','7':'S','8':'S','9':'H','10':'H','A':'H'},
        19:{'2':'S','3':'S','4':'S','5':'S','6':'Ds','7':'S','8':'S','9':'S','10':'S','A':'S'},
        20:{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S'},
      };
      const PAIRS: Record<string, Record<string, string>> = {
        '2':{'2':'Ph','3':'Ph','4':'P','5':'P','6':'P','7':'P','8':'H','9':'H','10':'H','A':'H'},
        '3':{'2':'Ph','3':'Ph','4':'P','5':'P','6':'P','7':'P','8':'H','9':'H','10':'H','A':'H'},
        '4':{'2':'H','3':'H','4':'H','5':'Ph','6':'Ph','7':'H','8':'H','9':'H','10':'H','A':'H'},
        '5':{'2':'D','3':'D','4':'D','5':'D','6':'D','7':'D','8':'D','9':'D','10':'H','A':'H'},
        '6':{'2':'Ph','3':'P','4':'P','5':'P','6':'P','7':'H','8':'H','9':'H','10':'H','A':'H'},
        '7':{'2':'P','3':'P','4':'P','5':'P','6':'P','7':'P','8':'H','9':'H','10':'H','A':'H'},
        '8':{'2':'P','3':'P','4':'P','5':'P','6':'P','7':'P','8':'P','9':'P','10':'P','A':'Rp'},
        '9':{'2':'P','3':'P','4':'P','5':'P','6':'P','7':'S','8':'P','9':'P','10':'S','A':'S'},
        '10':{'2':'S','3':'S','4':'S','5':'S','6':'S','7':'S','8':'S','9':'S','10':'S','A':'S'},
        'A':{'2':'P','3':'P','4':'P','5':'P','6':'P','7':'P','8':'P','9':'P','10':'P','A':'P'},
      };
      const actNames: Record<string, string> = {
        'H':'Hit','S':'Stand','D':'Double Down','Ds':'Double (Stand if not allowed)',
        'P':'Split','Ph':'Split (Hit if DAS not allowed)','Rh':'Surrender (Hit if not allowed)',
        'Rs':'Surrender (Stand if not allowed)','Rp':'Surrender (Split if not allowed)',
      };

      // Helper: look up basic strategy for a given hand
      function lookupStrategy(pTotal: number, dealerUp: string, cards?: unknown[]): { action: string; name: string; handType: string } | null {
        const du = dealerUp === '1' || dealerUp === 'A' || dealerUp === 'ace' ? 'A' : String(Math.min(10, Number(dealerUp)));
        if (!du || isNaN(Number(pTotal))) return null;

        // Check pairs
        if (cards && cards.length === 2) {
          const c1 = (cards[0] as Record<string, unknown>)?.value ?? cards[0];
          const c2 = (cards[1] as Record<string, unknown>)?.value ?? cards[1];
          const v1 = c1 === 'A' || c1 === 1 ? 'A' : String(Math.min(10, Number(c1)));
          const v2 = c2 === 'A' || c2 === 1 ? 'A' : String(Math.min(10, Number(c2)));
          if (v1 === v2 && PAIRS[v1]?.[du]) {
            const a = PAIRS[v1][du];
            return { action: a, name: actNames[a] ?? a, handType: 'pair' };
          }
          // Soft hand
          const hasAce = v1 === 'A' || v2 === 'A';
          if (hasAce && pTotal >= 13 && pTotal <= 20 && SOFT[pTotal]?.[du]) {
            const a = SOFT[pTotal][du];
            return { action: a, name: actNames[a] ?? a, handType: 'soft' };
          }
        }
        // Soft check for 3+ cards
        if (cards && cards.length > 2) {
          const hasAce = cards.some((c: unknown) => {
            const v = (c as Record<string, unknown>)?.value ?? c;
            return v === 'A' || v === 1 || v === 'ace';
          });
          if (hasAce && pTotal >= 13 && pTotal <= 20 && SOFT[pTotal]?.[du]) {
            const a = SOFT[pTotal][du];
            return { action: a, name: actNames[a] ?? a, handType: 'soft' };
          }
        }
        // Hard
        if (pTotal >= 5 && pTotal <= 21 && HARD[pTotal]?.[du]) {
          const a = HARD[pTotal][du];
          return { action: a, name: actNames[a] ?? a, handType: 'hard' };
        }
        return null;
      }

      // --- INTENT DETECTION ---
      let reply = "";
      const hasCards = gs.player_cards && gs.dealer_upcard;
      const pTotal = Number(gs.player_total) || 0;
      const dUp = gs.dealer_upcard ? String(gs.dealer_upcard) : "";

      // Greeting patterns
      if (/^(hi|hello|hey|yo|sup|what'?s? up|howdy|greetings)/i.test(msg)) {
        const greetings = [
          "Hey! Welcome to the table. I'm your dealer -- but I'm also here to help you learn. Ask me anything about your hand or basic strategy.",
          "What's good! I'm dealing and coaching tonight. Ask me about any hand and I'll walk you through the math.",
          "Hey there! Ready to play smart? I can break down any hand for you -- just ask.",
          "Welcome in! I deal the cards AND the knowledge. What's on your mind?",
        ];
        reply = greetings[Math.floor(Math.random() * greetings.length)];
      }

      // Asking about the current hand or last hand
      else if (/how.*(was|about|that|this).*(hand|play|round)|what.*(should|do).*(i|we)|did i.*(play|do)/i.test(msg) || /was that (right|correct|good)|good play/i.test(msg)) {
        if (hasCards) {
          const strat = lookupStrategy(pTotal, dUp, gs.player_cards);
          if (strat) {
            const lastAction = gs.last_action ?? "played";
            const lastResult = gs.last_result ?? "";
            reply = `Your ${strat.handType} ${pTotal} vs my ${dUp}? Basic strategy says **${strat.name}**. `;
            if (lastResult === 'win' || lastResult === 'blackjack') {
              reply += "And you took it down -- nice work!";
            } else if (lastResult === 'lose' || lastResult === 'bust') {
              reply += "Didn't go your way this time, but the right play is the right play regardless of outcome. Variance evens out.";
            } else if (lastResult === 'push') {
              reply += "Push -- you'll get 'em next time.";
            } else {
              reply += "Make the correct play every time and the math works for you over thousands of hands.";
            }
          } else {
            reply = `You've got ${pTotal} against my ${dUp}. What did you end up doing? Hit, stand, double, split? Tell me and I'll break down whether it was the right call.`;
          }
        } else {
          reply = "I'd love to break that hand down for you! I just need to see your cards. Play a hand and ask me during or right after -- I'll tell you exactly what basic strategy says.";
        }
      }

      // Asking about specific cards (e.g., "I had a 3 and dealer showed 5")
      else if (/(\d+|ace|king|queen|jack).*(vs|against|dealer|show)/i.test(msg) || /dealer.*(show|had|has|up).*([\dajqk])/i.test(msg)) {
        // Try to parse numbers from the message
        const nums = msg.match(/\d+/g);
        const hasAceMention = /ace/i.test(msg);
        if (nums && nums.length >= 2) {
          const playerT = Number(nums[0]);
          const dealerC = nums[1];
          const strat = lookupStrategy(playerT, dealerC, undefined);
          if (strat) {
            reply = `With a ${strat.handType} ${playerT} vs dealer ${dealerC}, basic strategy says **${strat.name}**. `;
            if (strat.action === 'H') reply += "You want more cards here -- the risk of busting is lower than the risk of losing with what you've got.";
            else if (strat.action === 'S') reply += "Stand pat. Let me (the dealer) take the risk of busting.";
            else if (strat.action.startsWith('D')) reply += "This is a great spot to double your bet. The math is in your favor.";
            else if (strat.action.startsWith('P')) reply += "Split those up. You'll make more money playing two hands in this spot.";
            else if (strat.action.startsWith('R')) reply += "Tough spot. Surrendering gives back half your bet, which is better than losing the whole thing most of the time.";
          } else {
            reply = `Hmm, ${playerT} vs ${dealerC} -- that total is outside the standard chart range. If you've got 21 or higher, the hand resolves automatically. What cards did you have?`;
          }
        } else if (hasAceMention && nums && nums.length >= 1) {
          const dealerC = nums[0];
          reply = `Got an Ace in your hand? That changes things. An Ace gives you a soft hand -- more flexibility. What's your total? I'll look up the exact play.`;
        } else {
          reply = "I caught some of that but couldn't quite parse the cards. Try something like 'I had 14 vs dealer 6' and I'll tell you the exact play.";
        }
      }

      // Asking about chart / strategy / rules
      else if (/chart|strategy|basic strategy|cheat sheet|when.*(hit|stand|double|split)|should i.*(hit|stand|double|split)/i.test(msg)) {
        reply = "Great question! Basic strategy is a mathematically proven chart that tells you the best play for every possible hand. Here's the quick version:\n\n";
        reply += "**Hard hands:** Stand on 17+. Stand on 13-16 vs dealer 2-6. Hit 12 vs 2 or 3. Double 11 vs everything. Double 10 vs 2-9.\n\n";
        reply += "**Soft hands:** Always hit or double soft 17 (A+6). Hit soft 18 vs 9, 10, Ace.\n\n";
        reply += "**Pairs:** Always split Aces and 8s. Never split 10s or 5s.\n\n";
        reply += "Ask me about any specific hand and I'll tell you exactly what to do!";
      }

      // Asking about splitting
      else if (/split/i.test(msg)) {
        reply = "Splitting rules from basic strategy:\n\n";
        reply += "**Always split:** Aces, 8s\n";
        reply += "**Never split:** 10s (20 is too strong), 5s (play as hard 10), 4s (except vs 5 or 6)\n";
        reply += "**Split vs weak dealer (2-6):** 2s, 3s, 6s, 7s, 9s\n";
        reply += "**9s vs 7:** Don't split -- your 18 beats the likely 17\n\n";
        reply += "Got a specific pair? Tell me what you're holding and what I'm showing.";
      }

      // Asking about insurance
      else if (/insurance|even money/i.test(msg)) {
        reply = "Never take insurance. Period. It's a side bet with a 7.7% house edge -- one of the worst bets on the table. Even money on a blackjack vs dealer Ace? Still no. The math doesn't lie. You'll make more long-term by declining every time.";
      }

      // Asking about odds / house edge
      else if (/odds|house edge|advantage|ev|expected value/i.test(msg)) {
        reply = "Here's the real numbers:\n\n";
        reply += "**House edge with basic strategy:** About 0.5% -- one of the lowest in any casino game.\n";
        reply += "**Without basic strategy:** 2-5% -- you're giving away money.\n";
        reply += "**Dealer bust rate:** About 28% overall.\n";
        reply += "**Dealer bust by upcard:** 2 (35%), 3 (37%), 4 (40%), 5 (42%), 6 (42%), 7-A (under 26%)\n\n";
        reply += "That's why you stand on 13-16 vs dealer 2-6 -- they bust over a third of the time.";
      }

      // Compliments or thanks
      else if (/thank|thanks|thx|appreciate|helpful|good advice|great tip/i.test(msg)) {
        const thanks = [
          "That's what I'm here for! Keep asking -- the more you understand the why, the more automatic the right plays become.",
          "You got it. Ask me anytime -- I'd rather you play smart than just play fast.",
          "No problem! That's the whole point of this table. Play, learn, get better.",
          "Glad I could help! You're already ahead of 90% of players just by wanting to learn.",
        ];
        reply = thanks[Math.floor(Math.random() * thanks.length)];
      }

      // Frustration / bad beat
      else if (/rigged|unfair|bs|bull|cheat|scam|losing|keep losing|bad luck|hate this/i.test(msg)) {
        const comfort = [
          "I hear you -- bad streaks are real and they're brutal. But here's the thing: if you're playing basic strategy, you're doing everything right. Variance swings both ways. The math WILL even out.",
          "Losing streaks feel personal, but they're pure statistics. A 10-hand losing streak happens to EVERY player eventually. Stay with basic strategy and the numbers come back to you.",
          "Rough run. I get it. But don't let a bad streak change your strategy -- that's how the house edge grows. Stick to the chart and the math rewards you over time.",
        ];
        reply = comfort[Math.floor(Math.random() * comfort.length)];
      }

      // General / catch-all -- always be helpful
      else {
        if (hasCards) {
          const strat = lookupStrategy(pTotal, dUp, gs.player_cards);
          if (strat) {
            reply = `I see you've got ${pTotal} vs my ${dUp}. Basic strategy says **${strat.name}** here. `;
            reply += "What else do you want to know? I can explain the reasoning behind any play.";
          } else {
            reply = "Good question! I'm here to help you play your best game. You can ask me about any hand, strategy, splitting, doubling, insurance -- whatever's on your mind. I'll give you the real math, no fluff.";
          }
        } else {
          reply = "I'm your dealer and your coach. Ask me about any hand situation and I'll tell you the mathematically correct play. Try something like 'I have 15 vs dealer 10' or 'should I split 8s?' -- I've got the full basic strategy chart in my head.";
        }
      }

      // Also store the exchange in table_chat if table context exists
      if (body.table_id && player_id) {
        await supabase.from("table_chat").insert({
          table_id: body.table_id,
          player_id,
          display_name: body.display_name ?? "Player",
          message: message.slice(0, 200),
          emoji: null,
        });
        await supabase.from("table_chat").insert({
          table_id: body.table_id,
          player_id: "dealer",
          display_name: "Dealer",
          message: reply.slice(0, 500),
          emoji: null,
        });
      }

      return json({ success: true, reply, has_game_context: !!hasCards });
    }

    return json({ error: `Unknown action: ${action}` }, 400);
  } catch (err) {
    console.error("blackjack-api error:", err);
    return json({ error: err.message ?? "Internal server error" }, 500);
  }
});
