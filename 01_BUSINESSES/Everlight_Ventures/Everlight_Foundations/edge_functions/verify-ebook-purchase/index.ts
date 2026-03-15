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

    const { session_id } = await req.json();

    if (!session_id) {
      return new Response(
        JSON.stringify({ error: "Missing session_id" }),
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
    if (!slug || !FILE_MAP[slug]) {
      return new Response(
        JSON.stringify({ error: "Invalid product slug in session metadata" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Insert purchase record
    const { error: purchaseErr } = await supabaseAdmin.from("ebook_purchases").insert({
      session_id: session.id,
      stripe_customer_id: session.customer as string,
      customer_email: session.customer_details?.email ?? null,
      slug,
      amount_total: session.amount_total,
      currency: session.currency,
      purchased_at: new Date().toISOString(),
    });

    if (purchaseErr) {
      console.error("Insert ebook_purchases error:", purchaseErr);
    }

    // Generate download token
    const token = crypto.randomUUID();
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();

    const { error: tokenErr } = await supabaseAdmin.from("download_tokens").insert({
      token,
      session_id: session.id,
      slug,
      expires_at: expiresAt,
      download_count: 0,
      max_downloads: 3,
    });

    if (tokenErr) {
      console.error("Insert download_tokens error:", tokenErr);
    }

    // Generate signed URL from Supabase Storage bucket "Ebooks"
    const filePath = FILE_MAP[slug];
    const { data: signedData, error: signedErr } = await supabaseAdmin.storage
      .from("Ebooks")
      .createSignedUrl(filePath, 86400); // 24 hours in seconds

    if (signedErr) {
      console.error("Signed URL error:", signedErr);
      return new Response(
        JSON.stringify({ error: "Failed to generate download link" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Slack notification
    const slackUrl = Deno.env.get("SLACK_WEBHOOK_URL");
    if (slackUrl) {
      const amount = session.amount_total
        ? `$${(session.amount_total / 100).toFixed(2)}`
        : "unknown";
      await postSlack(
        slackUrl,
        `Ebook sale! "${slug}" purchased for ${amount} by ${session.customer_details?.email ?? "unknown"}`
      );
    }

    // Auto-send purchase confirmation email with download link
    const customerEmail = session.customer_details?.email;
    if (customerEmail) {
      try {
        await fetch(
          `${SUPABASE_URL}/functions/v1/send-purchase-email`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Authorization": `Bearer ${Deno.env.get("SB_SERVICE_ROLE_KEY")}`,
            },
            body: JSON.stringify({
              to: customerEmail,
              slug,
              download_url: signedData.signedUrl,
              type: "purchase",
            }),
          }
        );
      } catch (emailErr) {
        console.error("Auto-email failed (non-blocking):", emailErr);
      }
    }

    // Token-gated download URL (use this instead of raw signed URL on frontend)
    const tokenDownloadUrl = `${SUPABASE_URL}/functions/v1/download-ebook?token=${token}`;

    return new Response(
      JSON.stringify({
        success: true,
        download_url: signedData.signedUrl,
        token_download_url: tokenDownloadUrl,
        token,
        expires_at: expiresAt,
        downloads_remaining: 3,
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("verify-ebook-purchase error:", err);
    return new Response(
      JSON.stringify({ error: err.message ?? "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
