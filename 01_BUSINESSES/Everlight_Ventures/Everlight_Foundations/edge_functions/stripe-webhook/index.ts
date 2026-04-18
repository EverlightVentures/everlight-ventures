import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";
import { SUPABASE_URL, corsHeaders, postSlack } from "../_shared/mod.ts";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  // ALWAYS return 200 to Stripe, even on internal errors
  const ok = () =>
    new Response(
      JSON.stringify({ received: true }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  try {
    const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
      apiVersion: "2023-10-16",
      httpClient: Stripe.createFetchHttpClient(),
    });

    const supabaseAdmin = createClient(
      SUPABASE_URL,
      Deno.env.get("SB_SERVICE_ROLE_KEY")!
    );

    const webhookSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET");
    const slackUrl = Deno.env.get("SLACK_WEBHOOK_URL");

    // Read raw body for signature verification
    const body = await req.text();
    const signature = req.headers.get("stripe-signature");

    if (!signature || !webhookSecret) {
      console.error("Missing stripe-signature header or STRIPE_WEBHOOK_SECRET");
      return ok();
    }

    let event: Stripe.Event;
    try {
      event = await stripe.webhooks.constructEventAsync(
        body,
        signature,
        webhookSecret
      );
    } catch (err: unknown) {
      console.error("Webhook signature verification failed:", (err as Error).message);
      return ok();
    }

    // Log every event to stripe_events table
    const { error: logErr } = await supabaseAdmin.from("stripe_events").insert({
      event_id: event.id,
      event_type: event.type,
      data: event.data.object,
      created_at: new Date(event.created * 1000).toISOString(),
      received_at: new Date().toISOString(),
    });

    if (logErr) console.error("Insert stripe_events error:", logErr);

    // Route by event type
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const slug = session.metadata?.slug;
        const productType = session.metadata?.product_type;

        if (!slug) {
          console.log("checkout.session.completed with no slug metadata, skipping");
          break;
        }

        // Fallback fulfillment -- only if not already recorded
        if (productType === "ebook") {
          const { data: existing } = await supabaseAdmin
            .from("ebook_purchases")
            .select("id")
            .eq("session_id", session.id)
            .maybeSingle();

          if (!existing) {
            await supabaseAdmin.from("ebook_purchases").insert({
              session_id: session.id,
              stripe_customer_id: session.customer as string,
              customer_email: session.customer_details?.email ?? null,
              slug,
              amount_total: session.amount_total,
              currency: session.currency,
              purchased_at: new Date().toISOString(),
            });

            if (slackUrl) {
              const amount = session.amount_total
                ? `$${(session.amount_total / 100).toFixed(2)}`
                : "unknown";
              await postSlack(slackUrl, `[Webhook fallback] Ebook "${slug}" fulfilled for ${amount}`);
            }
          }
        } else if (productType === "arcade") {
          const { data: existing } = await supabaseAdmin
            .from("arcade_purchases")
            .select("id")
            .eq("session_id", session.id)
            .maybeSingle();

          if (!existing) {
            await supabaseAdmin.from("arcade_purchases").insert({
              session_id: session.id,
              slug,
              product_type: productType,
              amount_total: session.amount_total,
              currency: session.currency,
              purchased_at: new Date().toISOString(),
            });

            if (slackUrl) {
              await postSlack(slackUrl, `[Webhook fallback] Arcade "${slug}" recorded`);
            }
          }
        } else if (productType === "gems") {
          const { data: existing } = await supabaseAdmin
            .from("gem_purchases")
            .select("id")
            .eq("session_id", session.id)
            .maybeSingle();

          if (!existing) {
            // Map slug to gem amount
            const GEM_AMOUNTS: Record<string, number> = {
              "gems-100": 100, "gems-600": 600, "gems-1500": 1500, "gems-4000": 4000,
            };
            const gemAmount = GEM_AMOUNTS[slug] || 0;

            await supabaseAdmin.from("gem_purchases").insert({
              session_id: session.id,
              slug,
              amount_total: session.amount_total,
              currency: session.currency,
              purchased_at: new Date().toISOString(),
            });

            // CREDIT GEMS to player account
            if (gemAmount > 0) {
              const email = session.customer_details?.email;
              if (email) {
                const { data: player } = await supabaseAdmin
                  .from("player_accounts")
                  .select("player_id")
                  .eq("email", email)
                  .maybeSingle();

                if (player) {
                  // Update game_currencies gems balance
                  const { data: gemRow } = await supabaseAdmin
                    .from("game_currencies")
                    .select("balance")
                    .eq("player_id", player.player_id)
                    .eq("game_id", "blackjack")
                    .eq("currency_name", "gems")
                    .maybeSingle();

                  if (gemRow) {
                    await supabaseAdmin
                      .from("game_currencies")
                      .update({ balance: (gemRow.balance || 0) + gemAmount, updated_at: new Date().toISOString() })
                      .eq("player_id", player.player_id)
                      .eq("game_id", "blackjack")
                      .eq("currency_name", "gems");
                  } else {
                    await supabaseAdmin.from("game_currencies").insert({
                      player_id: player.player_id,
                      game_id: "blackjack",
                      currency_name: "gems",
                      balance: gemAmount,
                    });
                  }
                }
              }
            }

            if (slackUrl) {
              await postSlack(slackUrl, `[Gems] ${gemAmount} gems credited for "${slug}" ($${((session.amount_total || 0) / 100).toFixed(2)})`);
            }
          }
        } else if (productType === "chips") {
          // CHIP PURCHASE FULFILLMENT
          const CHIP_AMOUNTS: Record<string, number> = {
            "chips-500": 5000, "chips-3000": 30000, "chips-8000": 80000,
          };
          const chipAmount = CHIP_AMOUNTS[slug] || 0;
          const email = session.customer_details?.email;

          if (chipAmount > 0 && email) {
            const { data: player } = await supabaseAdmin
              .from("player_accounts")
              .select("player_id, chip_balance")
              .eq("email", email)
              .maybeSingle();

            if (player) {
              // Credit chip_balance on player_accounts
              await supabaseAdmin
                .from("player_accounts")
                .update({ chip_balance: (player.chip_balance || 0) + chipAmount })
                .eq("player_id", player.player_id);

              // Also update game_currencies chips balance
              const { data: chipRow } = await supabaseAdmin
                .from("game_currencies")
                .select("balance")
                .eq("player_id", player.player_id)
                .eq("game_id", "blackjack")
                .eq("currency_name", "chips")
                .maybeSingle();

              if (chipRow) {
                await supabaseAdmin
                  .from("game_currencies")
                  .update({ balance: (chipRow.balance || 0) + chipAmount, updated_at: new Date().toISOString() })
                  .eq("player_id", player.player_id)
                  .eq("game_id", "blackjack")
                  .eq("currency_name", "chips");
              } else {
                await supabaseAdmin.from("game_currencies").insert({
                  player_id: player.player_id,
                  game_id: "blackjack",
                  currency_name: "chips",
                  balance: chipAmount,
                });
              }

              if (slackUrl) {
                await postSlack(slackUrl, `[Chips] ${chipAmount.toLocaleString()} GC credited to ${email} for "${slug}" ($${((session.amount_total || 0) / 100).toFixed(2)})`);
              }
            }
          }
        } else if (productType === "nos") {
          // NOS Bottle purchase (Alley Kingz) -- record only for now
          if (slackUrl) {
            await postSlack(slackUrl, `[NOS] "${slug}" purchased ($${((session.amount_total || 0) / 100).toFixed(2)})`);
          }
        }
        break;
      }

      case "customer.subscription.created": {
        const subscription = event.data.object as Stripe.Subscription;
        const customerId = subscription.customer as string;

        // Find player by stripe_customer_id and set VIP
        const { error: updateErr } = await supabaseAdmin
          .from("player_accounts")
          .update({ vip_status: true })
          .eq("stripe_customer_id", customerId);

        if (updateErr) console.error("Set vip_status true error:", updateErr);

        if (slackUrl) {
          await postSlack(slackUrl, `New VIP subscription created for customer ${customerId}`);
        }
        break;
      }

      case "customer.subscription.deleted": {
        const subscription = event.data.object as Stripe.Subscription;
        const customerId = subscription.customer as string;

        const { error: updateErr } = await supabaseAdmin
          .from("player_accounts")
          .update({ vip_status: false })
          .eq("stripe_customer_id", customerId);

        if (updateErr) console.error("Set vip_status false error:", updateErr);

        if (slackUrl) {
          await postSlack(slackUrl, `VIP subscription cancelled for customer ${customerId}`);
        }
        break;
      }

      case "invoice.payment_succeeded": {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = invoice.customer as string;

        const { error: updateErr } = await supabaseAdmin
          .from("player_accounts")
          .update({ vip_renewed_at: new Date().toISOString() })
          .eq("stripe_customer_id", customerId);

        if (updateErr) console.error("Update vip_renewed_at error:", updateErr);

        if (slackUrl) {
          const amount = invoice.amount_paid
            ? `$${(invoice.amount_paid / 100).toFixed(2)}`
            : "unknown";
          await postSlack(
            slackUrl,
            `VIP renewal payment succeeded for customer ${customerId} -- ${amount}`
          );
        }
        break;
      }

      case "invoice.payment_failed": {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = invoice.customer as string;

        // Do NOT revoke VIP -- just alert
        if (slackUrl) {
          await postSlack(
            slackUrl,
            `ALERT: VIP payment FAILED for customer ${customerId}. VIP NOT revoked.`
          );
        }
        break;
      }

      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    return ok();
  } catch (err: unknown) {
    console.error("stripe-webhook top-level error:", err);
    // ALWAYS return 200 to Stripe
    return new Response(
      JSON.stringify({ received: true }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
