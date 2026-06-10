// alley-kingz-checkout - Cloudflare Pages Function (edge).
// Source: 01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ONLINE_STORE_SPEC.md
//
// POST body:
//   { price_id: string, quantity: number, size?: string, color?: string }
//
// Returns 200 { url } with a Stripe Checkout URL to redirect the buyer to.

import Stripe from 'stripe';

interface EnvBindings {
  STRIPE_SECRET_KEY: string;
  STRIPE_SHIPPING_RATE_US: string;
  STRIPE_PRICE_AK_HOODIE: string;
  STRIPE_PRICE_AK_TEE: string;
  STRIPE_PRICE_AK_STICKERS: string;
}

interface CheckoutBody {
  price_id: string;
  quantity: number;
  size?: string;
  color?: string;
}

const CORS = {
  'Access-Control-Allow-Origin': 'https://everlightventures.io',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export const onRequest: PagesFunction<EnvBindings> = async (ctx) => {
  if (ctx.request.method === 'OPTIONS') {
    return new Response(null, { headers: CORS });
  }
  if (ctx.request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405, headers: CORS });
  }

  const env = ctx.env;
  if (!env.STRIPE_SECRET_KEY) {
    return new Response(JSON.stringify({ error: 'missing env' }), { status: 500, headers: { ...CORS, 'Content-Type': 'application/json' } });
  }

  let body: CheckoutBody;
  try {
    body = await ctx.request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'invalid json' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });
  }

  const validPriceIds = new Set([
    env.STRIPE_PRICE_AK_HOODIE,
    env.STRIPE_PRICE_AK_TEE,
    env.STRIPE_PRICE_AK_STICKERS,
  ].filter(Boolean));

  if (!validPriceIds.has(body.price_id)) {
    return new Response(JSON.stringify({ error: 'invalid price_id' }), { status: 400, headers: { ...CORS, 'Content-Type': 'application/json' } });
  }

  const qty = Math.max(1, Math.min(10, Math.floor(body.quantity || 1)));
  const stripe = new Stripe(env.STRIPE_SECRET_KEY, { apiVersion: '2024-06-20' });

  const session = await stripe.checkout.sessions.create({
    mode: 'payment',
    line_items: [{ price: body.price_id, quantity: qty }],
    shipping_address_collection: { allowed_countries: ['US'] },
    shipping_options: env.STRIPE_SHIPPING_RATE_US
      ? [{ shipping_rate: env.STRIPE_SHIPPING_RATE_US }]
      : undefined,
    metadata: {
      brand: 'alley_kingz',
      size: body.size || '',
      color: body.color || '',
    },
    success_url: 'https://everlightventures.io/shop/thanks?order={CHECKOUT_SESSION_ID}',
    cancel_url: 'https://everlightventures.io/shop',
  });

  return new Response(JSON.stringify({ url: session.url }), {
    status: 200,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
};
