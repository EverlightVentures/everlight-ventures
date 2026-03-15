import Stripe from "https://esm.sh/stripe@14.21.0?target=deno";

const SUPABASE_URL = "https://jdqqmsmwmbsnlnstyavl.supabase.co";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const PRICE_MAP: Record<string, string> = {
  "sam-book-1": "price_1T86XVGd8n4Fz3nAs7ubL82A",
  "sam-book-2": "price_1T86XVGd8n4Fz3nACgflduDO",
  "sam-book-3": "price_1T86XWGd8n4Fz3nAqwJsmpjJ",
  "sam-book-4": "price_1T86XXGd8n4Fz3nABRzxEp33",
  "sam-book-5": "price_1T86XYGd8n4Fz3nAI0vnzdv8",
  "sam-bundle": "price_1T86XZGd8n4Fz3nAnYniGGZq",
  "beyond-the-veil": "price_1T86XaGd8n4Fz3nAksUXrOkU",
  "arcade-lives-t1": "price_1T86XbGd8n4Fz3nA2Dku9288",
  "arcade-lives-t2": "price_1T86XcGd8n4Fz3nAAfe2DqpT",
  "arcade-lives-t3": "price_1T86XcGd8n4Fz3nAn9DuNkfk",
  "arcade-day-pass": "price_1T86XdGd8n4Fz3nAEmjFNQcS",
  "arcade-vip-monthly": "price_1T86XfGd8n4Fz3nAPsmaVqPS",
  "ak-season-pass": "price_1T86XgGd8n4Fz3nA06V8zK8m",
  "gems-100": "price_1T86XiGd8n4Fz3nAsJk2s93y",
  "gems-600": "price_1T86XjGd8n4Fz3nASyIVCA70",
  "gems-1500": "price_1T86XkGd8n4Fz3nAjXXz9pcI",
  "gems-4000": "price_1T86XlGd8n4Fz3nAHfTgPqih",
  // NOS Bottles (Alley Kingz)
  "nos-50": "price_1T9CPHGd8n4Fz3nACi5Ol8di",
  "nos-300": "price_1T9CPIGd8n4Fz3nANejJM5Pq",
  "nos-800": "price_1T9CPIGd8n4Fz3nAWqFyYBQd",
  // Chips (Blackjack)
  "chips-500": "price_1T9CPJGd8n4Fz3nAdplghkkh",
  "chips-3000": "price_1T9CPKGd8n4Fz3nA2jxRil2f",
  "chips-8000": "price_1T9CPKGd8n4Fz3nAczOpCzET",
  // Game Passes
  "ak-game-pass": "price_1T9CPLGd8n4Fz3nA52PnZRgm",
  "bj-game-pass": "price_1T9CPMGd8n4Fz3nAXyX7odXJ",
  "master-pass": "price_1T9CPMGd8n4Fz3nAVlfEbWGv",
};

function deriveProductType(slug: string): string {
  if (slug.startsWith("sam-") || slug === "beyond-the-veil") return "ebook";
  if (slug.startsWith("arcade-") || slug === "ak-season-pass") return "arcade";
  if (slug.startsWith("gems-")) return "gems";
  if (slug.startsWith("nos-")) return "nos";
  if (slug.startsWith("chips-")) return "chips";
  if (slug.endsWith("-game-pass") || slug === "master-pass") return "game-pass";
  return "unknown";
}

function isSubscription(slug: string): boolean {
  return slug === "arcade-vip-monthly" || slug === "ak-game-pass" || slug === "bj-game-pass" || slug === "master-pass";
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

    const { slug, success_url, cancel_url } = await req.json();

    if (!slug || !PRICE_MAP[slug]) {
      return new Response(
        JSON.stringify({ error: "Invalid or missing slug" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const priceId = PRICE_MAP[slug];
    const productType = deriveProductType(slug);
    const isSub = isSubscription(slug);

    const session = await stripe.checkout.sessions.create({
      mode: isSub ? "subscription" : "payment",
      line_items: [{ price: priceId, quantity: 1 }],
      success_url:
        success_url ??
        "https://everlightventures.io/purchase/success?session_id={CHECKOUT_SESSION_ID}",
      cancel_url: cancel_url ?? "https://everlightventures.io",
      metadata: { slug, product_type: productType },
    });

    return new Response(
      JSON.stringify({ url: session.url, session_id: session.id }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("create-checkout error:", err);
    return new Response(
      JSON.stringify({ error: err.message ?? "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
