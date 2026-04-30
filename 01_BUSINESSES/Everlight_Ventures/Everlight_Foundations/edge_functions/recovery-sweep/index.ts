// recovery-sweep: Finds Stripe purchases that never got delivered and auto-sends recovery emails
// Can be triggered manually or via cron (Supabase pg_cron or external)
// Checks Stripe for paid sessions, cross-refs with ebook_purchases table
// Generates fresh download links and sends recovery emails with free bonus book

import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";
import { SUPABASE_URL, corsHeaders, postSlack, EBOOK_FILE_MAP } from "../_shared/mod.ts";

const BONUS_SLUG = "sam-book-2";

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

    // Get all completed checkout sessions from Stripe (last 30 days)
    const sessions = await stripe.checkout.sessions.list({
      limit: 100,
      status: "complete",
    });

    let recovered = 0;
    let alreadyFulfilled = 0;
    let skipped = 0;
    const results: Array<{ email: string; slug: string; status: string }> = [];

    for (const session of sessions.data) {
      if (session.payment_status !== "paid") continue;

      const slug = session.metadata?.slug;
      const productType = session.metadata?.product_type;
      const email = session.customer_details?.email;

      // Only process ebook purchases
      if (!slug || productType !== "ebook" || !email || !EBOOK_FILE_MAP[slug]) {
        skipped++;
        continue;
      }

      // Check if already fulfilled in our DB
      const { data: existing } = await supabaseAdmin
        .from("ebook_purchases")
        .select("id")
        .eq("session_id", session.id)
        .maybeSingle();

      if (existing) {
        alreadyFulfilled++;
        continue;
      }

      // --- ORPHANED PURCHASE: paid in Stripe but not in our DB ---

      // 1. Record the purchase
      await supabaseAdmin.from("ebook_purchases").insert({
        session_id: session.id,
        stripe_customer_id: session.customer as string,
        customer_email: email,
        slug,
        amount_total: session.amount_total,
        currency: session.currency,
        purchased_at: new Date((session.created ?? 0) * 1000).toISOString(),
      });

      // 2. Generate download link (7-day expiry for recovery)
      const filePath = EBOOK_FILE_MAP[slug];
      const { data: signedData } = await supabaseAdmin.storage
        .from("Ebooks")
        .createSignedUrl(filePath, 604800); // 7 days

      if (!signedData?.signedUrl) {
        results.push({ email, slug, status: "FAILED - no signed URL" });
        continue;
      }

      // 3. Generate bonus book link
      const bonusPath = EBOOK_FILE_MAP[BONUS_SLUG];
      const { data: bonusData } = await supabaseAdmin.storage
        .from("Ebooks")
        .createSignedUrl(bonusPath, 604800);

      // 4. Send recovery email via send-purchase-email function
      const emailPayload: Record<string, string> = {
        to: email,
        slug,
        download_url: signedData.signedUrl,
        type: "recovery",
      };

      if (bonusData?.signedUrl) {
        emailPayload.bonus_slug = BONUS_SLUG;
        emailPayload.bonus_download_url = bonusData.signedUrl;
      }

      const emailResp = await fetch(
        `${SUPABASE_URL}/functions/v1/send-purchase-email`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${Deno.env.get("SB_SERVICE_ROLE_KEY")}`,
          },
          body: JSON.stringify(emailPayload),
        }
      );

      const emailResult = await emailResp.json();

      if (emailResult.success) {
        recovered++;
        results.push({ email, slug, status: "RECOVERED - email sent" });
      } else {
        results.push({ email, slug, status: `EMAIL FAILED: ${JSON.stringify(emailResult)}` });
      }
    }

    const summary = `Recovery sweep complete: ${recovered} recovered, ${alreadyFulfilled} already fulfilled, ${skipped} skipped (non-ebook)`;
    await postSlack(summary);

    return new Response(
      JSON.stringify({ summary, recovered, alreadyFulfilled, skipped, results }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err: unknown) {
    console.error("recovery-sweep error:", err);
    await postSlack(`Recovery sweep ERROR: ${(err as Error).message}`);
    return new Response(
      JSON.stringify({ error: (err as Error).message ?? "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
