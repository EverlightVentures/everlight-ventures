import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// Maps slug to lives granted for credit packs
const LIVES_MAP: Record<string, number> = {
  "arcade-lives-t1": 3,
  "arcade-lives-t2": 10,
  "arcade-lives-t3": 25,
};

// Maps slug to NOS bottles granted (Alley Kingz)
const NOS_MAP: Record<string, number> = {
  "nos-50": 50,
  "nos-300": 300,
  "nos-800": 800,
};

// Maps slug to chips granted (Blackjack)
const CHIPS_MAP: Record<string, number> = {
  "chips-500": 500,
  "chips-3000": 3000,
  "chips-8000": 8000,
};

async function postSlack(webhookUrl: string, text: string): Promise<void> {
  try {
    await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
  } catch (err) {
    console.error("Slack notification failed:", err);
  }
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
      apiVersion: "2023-10-16",
      httpClient: Stripe.createFetchHttpClient(),
    });

    const supabaseAdmin = createClient(
      SUPABASE_URL,
      Deno.env.get("SB_SERVICE_ROLE_KEY")!
    );

    const { session_id, player_id } = await req.json();

    if (!session_id || !player_id) {
      return new Response(
        JSON.stringify({ error: "Missing session_id or player_id" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Retrieve session from Stripe
    const session = await stripe.checkout.sessions.retrieve(session_id);

    if (session.payment_status !== "paid") {
      return new Response(
        JSON.stringify({ error: "Payment not completed", payment_status: session.payment_status }),
        { status: 402, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const slug = session.metadata?.slug;
    const productType = session.metadata?.product_type;

    if (!slug) {
      return new Response(
        JSON.stringify({ error: "No slug in session metadata" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Fetch current player account
    const { data: player, error: playerErr } = await supabaseAdmin
      .from("player_accounts")
      .select("*")
      .eq("player_id", player_id)
      .single();

    if (playerErr || !player) {
      return new Response(
        JSON.stringify({ error: "Player not found" }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    let livesBalance = player.lives_balance ?? 0;
    let activeDayPass = false;
    let seasonPass = player.season_pass ?? false;

    // Route by slug pattern
    if (LIVES_MAP[slug]) {
      // Arcade credits -- add lives
      const livesGranted = LIVES_MAP[slug];
      livesBalance += livesGranted;

      const { error: updateErr } = await supabaseAdmin
        .from("player_accounts")
        .update({ lives_balance: livesBalance })
        .eq("player_id", player_id);

      if (updateErr) console.error("Update lives_balance error:", updateErr);

    } else if (slug === "arcade-day-pass") {
      // Day pass -- insert session row
      const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

      const { error: sessionErr } = await supabaseAdmin
        .from("arcade_sessions")
        .insert({
          player_id,
          session_id: session.id,
          expires_at: expiresAt,
        });

      if (sessionErr) console.error("Insert arcade_sessions error:", sessionErr);
      activeDayPass = true;

    } else if (slug === "ak-season-pass") {
      // Season pass
      seasonPass = true;

      const { error: updateErr } = await supabaseAdmin
        .from("player_accounts")
        .update({ season_pass: true })
        .eq("player_id", player_id);

      if (updateErr) console.error("Update season_pass error:", updateErr);

    } else if (NOS_MAP[slug]) {
      // NOS Bottles (Alley Kingz currency)
      const nosAmount = NOS_MAP[slug];
      const { data: gc } = await supabaseAdmin
        .from("game_currencies")
        .select("balance")
        .eq("player_id", player_id)
        .eq("game_id", "alley-kingz")
        .maybeSingle();

      if (gc) {
        await supabaseAdmin.from("game_currencies")
          .update({ balance: gc.balance + nosAmount, updated_at: new Date().toISOString() })
          .eq("player_id", player_id).eq("game_id", "alley-kingz");
      } else {
        await supabaseAdmin.from("game_currencies").insert({
          player_id, game_id: "alley-kingz", currency_name: "nos", balance: nosAmount,
        });
      }

    } else if (CHIPS_MAP[slug]) {
      // Chips (Blackjack currency)
      const chipAmount = CHIPS_MAP[slug];
      const { data: gc } = await supabaseAdmin
        .from("game_currencies")
        .select("balance")
        .eq("player_id", player_id)
        .eq("game_id", "blackjack")
        .eq("currency_name", "chips")
        .maybeSingle();

      if (gc) {
        await supabaseAdmin.from("game_currencies")
          .update({ balance: gc.balance + chipAmount, updated_at: new Date().toISOString() })
          .eq("player_id", player_id).eq("game_id", "blackjack").eq("currency_name", "chips");
      } else {
        await supabaseAdmin.from("game_currencies").insert({
          player_id, game_id: "blackjack", currency_name: "chips", balance: chipAmount,
        });
      }
      // Also sync to player_accounts.chip_balance
      await supabaseAdmin.from("player_accounts")
        .update({ chip_balance: (gc?.balance ?? 0) + chipAmount })
        .eq("player_id", player_id);

    } else if (slug === "ak-game-pass" || slug === "bj-game-pass" || slug === "master-pass") {
      // Game passes
      const gameId = slug === "ak-game-pass" ? "alley-kingz" : slug === "bj-game-pass" ? "blackjack" : "all";
      await supabaseAdmin.from("game_passes").insert({
        player_id,
        pass_type: slug,
        game_id: gameId,
        stripe_subscription_id: session.subscription as string ?? null,
        active: true,
      });
    }

    // Insert purchase record
    const { error: purchaseErr } = await supabaseAdmin.from("arcade_purchases").insert({
      session_id: session.id,
      player_id,
      slug,
      product_type: productType,
      amount_total: session.amount_total,
      currency: session.currency,
      purchased_at: new Date().toISOString(),
    });

    if (purchaseErr) console.error("Insert arcade_purchases error:", purchaseErr);

    // Slack notification
    const slackUrl = Deno.env.get("SLACK_WEBHOOK_URL");
    if (slackUrl) {
      const amount = session.amount_total
        ? `$${(session.amount_total / 100).toFixed(2)}`
        : "unknown";
      await postSlack(
        slackUrl,
        `Arcade purchase! "${slug}" by player ${player_id} for ${amount}`
      );
    }

    return new Response(
      JSON.stringify({
        success: true,
        lives_balance: livesBalance,
        active_day_pass: activeDayPass,
        season_pass: seasonPass,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("verify-arcade-purchase error:", err);
    return new Response(
      JSON.stringify({ error: err.message ?? "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
