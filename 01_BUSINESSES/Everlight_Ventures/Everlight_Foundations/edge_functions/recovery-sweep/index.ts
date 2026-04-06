// recovery-sweep: Finds Stripe purchases that never got delivered and auto-sends recovery emails
// Can be triggered manually or via cron (Supabase pg_cron or external)
// Checks Stripe for paid sessions, cross-refs with ebook_purchases table
// Generates fresh download links and sends recovery emails with free bonus book

import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.0";

const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const FILE_MAP: Record<string, string> = {
  "sam-book-1": "sam-book-1/Sams_First_Superpower.zip",
  "sam-book-2": "sam-book-2/Sams_Second_Superpower.zip",
  "sam-book-3": "sam-book-3/Sams_Third_Superpower.zip",
  "sam-book-4": "sam-book-4/Sams_Fourth_Superpower.zip",
  "sam-book-5": "sam-book-5/Sams_Fifth_Superpower.zip",
  "sam-bundle": "sam-bundle/Sam_And_Robo_Complete.zip",
  "beyond-the-veil": "beyond-the-veil/Beyond_The_Veil.zip",
};

// Bonus book to include with recovery emails (free gift)
const BONUS_SLUG = "sam-book-2";

async function postSlack(text: string): Promise<void> {
  const url = Deno.env.get("SLACK_WEBHOOK_URL");
  if (!url) return;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
  } catch (e) {
    console.error("Slack failed:", e);
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
      if (!slug || productType !== "ebook" || !email || !FILE_MAP[slug]) {
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
      const filePath = FILE_MAP[slug];
      const { data: signedData } = await supabaseAdmin.storage
        .from("Ebooks")
        .createSignedUrl(filePath, 604800); // 7 days

      if (!signedData?.signedUrl) {
        results.push({ email, slug, status: "FAILED - no signed URL" });
        continue;
      }

      // 3. Generate bonus book link
      const bonusPath = FILE_MAP[BONUS_SLUG];
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
  } catch (err) {
    console.error("recovery-sweep error:", err);
    await postSlack(`Recovery sweep ERROR: ${err.message}`);
    return new Response(
      JSON.stringify({ error: err.message ?? "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
