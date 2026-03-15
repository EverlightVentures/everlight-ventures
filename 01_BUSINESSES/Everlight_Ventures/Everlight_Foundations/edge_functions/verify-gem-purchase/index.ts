import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const GEM_COUNT_MAP: Record<string, number> = {
  "gems-100": 100,
  "gems-600": 600,
  "gems-1500": 1500,
  "gems-4000": 4000,
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

    if (!slug || !GEM_COUNT_MAP[slug]) {
      return new Response(
        JSON.stringify({ error: "Invalid gem product in session metadata" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const gemCount = GEM_COUNT_MAP[slug];

    // Verify player exists
    const { data: player, error: playerErr } = await supabaseAdmin
      .from("player_accounts")
      .select("player_id")
      .eq("player_id", player_id)
      .single();

    if (playerErr || !player) {
      return new Response(
        JSON.stringify({ error: "Player not found" }),
        { status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { data: gemCurrency, error: gemCurrencyErr } = await supabaseAdmin
      .from("game_currencies")
      .select("balance")
      .eq("player_id", player_id)
      .eq("game_id", "blackjack")
      .eq("currency_name", "gems")
      .maybeSingle();

    if (gemCurrencyErr) console.error("Fetch game_currencies gem balance error:", gemCurrencyErr);

    const newBalance = (gemCurrency?.balance ?? 0) + gemCount;

    if (gemCurrency) {
      const { error: updateErr } = await supabaseAdmin
        .from("game_currencies")
        .update({ balance: newBalance, updated_at: new Date().toISOString() })
        .eq("player_id", player_id)
        .eq("game_id", "blackjack")
        .eq("currency_name", "gems");

      if (updateErr) console.error("Update game_currencies gem balance error:", updateErr);
    } else {
      const { error: insertErr } = await supabaseAdmin.from("game_currencies").insert({
        player_id,
        game_id: "blackjack",
        currency_name: "gems",
        balance: newBalance,
      });
      if (insertErr) console.error("Insert game_currencies gem balance error:", insertErr);
    }

    // Insert purchase record
    const { error: purchaseErr } = await supabaseAdmin.from("gem_purchases").insert({
      session_id: session.id,
      player_id,
      slug,
      gem_count: gemCount,
      amount_total: session.amount_total,
      currency: session.currency,
      purchased_at: new Date().toISOString(),
    });

    if (purchaseErr) console.error("Insert gem_purchases error:", purchaseErr);

    // Slack notification
    const slackUrl = Deno.env.get("SLACK_WEBHOOK_URL");
    if (slackUrl) {
      const amount = session.amount_total
        ? `$${(session.amount_total / 100).toFixed(2)}`
        : "unknown";
      await postSlack(
        slackUrl,
        `Gem purchase! ${gemCount} gems by player ${player_id} for ${amount}`
      );
    }

    return new Response(
      JSON.stringify({
        success: true,
        gems_added: gemCount,
        gem_balance: newBalance,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("verify-gem-purchase error:", err);
    return new Response(
      JSON.stringify({ error: err.message ?? "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
