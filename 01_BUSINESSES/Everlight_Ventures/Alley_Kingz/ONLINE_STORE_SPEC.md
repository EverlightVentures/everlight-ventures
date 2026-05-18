# Alley Kingz Online Store - Build Spec

**Owner**: Piper (catalog + copy) + writer (product descriptions) + Chart (dashboard)
**Source**: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/10_Sales_and_Services/launch_an_online_store_today.txt`
**Status**: Spec ready. Implementation requires Stripe products + React component + edge function.
**Date**: 2026-04-21

---

## Decision: Stripe Checkout on the existing React site (not Shopify)

### Options considered

| Option | Cost | Pros | Cons | Verdict |
|---|---|---|---|---|
| Shopify | $29/mo + 2.9% | Full storefront, inventory UI, shipping rules | Vendor lock-in, duplicate brand presence, $29 floor | REJECT at MVP |
| WooCommerce self-hosted | hosting only | Full control, no vendor fee | Needs WordPress stack, maintenance burden | REJECT |
| Snipcart on existing React | $10/mo floor + 2% | Lightweight, drop-in, mature | Vendor | MAYBE later |
| **Stripe Checkout + React** | only 2.9% + $0.30 per txn | Zero monthly floor, we already have Stripe, zero new vendor, tight brand | Manual fulfillment UI needed | **PICK** |
| Medusa self-hosted | hosting | Modern headless | Heavy setup | REJECT at MVP |

### Why Stripe Checkout wins for MVP

1. **Zero additional vendor cost.** We already have live Stripe keys.
2. **Fits the site**: everlightventures.io is React on Cloudflare. We just add a page + a Checkout edge function.
3. **Fulfillment is manual at first** (3 products, low volume). No inventory UI needed yet.
4. **Graduate to Snipcart or Medusa** when we exceed ~100 orders/month and manual ops break.

---

## Phase 1 catalog (3 products to launch with)

From `01_BUSINESSES/Everlight_Ventures/Alley_Kingz/`, the brand is built. We drop 3 SKUs.

### SKU 1: Alley Kingz Hoodie (Limited Drop 001)

- **Price**: $65 (unit cost ~$25 via Printful or similar POD, 60% margin)
- **Colors**: Black, cream
- **Sizes**: S, M, L, XL, 2XL
- **Copy (Piper)**: "Alley Kingz Drop 001. Heavyweight 12oz cotton. Gold foil crown on the back. Limited to 50 pieces in each color. Numbered on the inside tag. When they're gone, they're gone."

### SKU 2: Alley Kingz Tee (Everyday)

- **Price**: $32
- **Colors**: Black, cream, midnight navy
- **Sizes**: S, M, L, XL, 2XL
- **Copy (Piper)**: "Heavyweight cotton tee. Embroidered crown at the chest. The kind of shirt you reach for on the days that matter."

### SKU 3: Founder Sticker Pack (Tier-gate for VIP)

- **Price**: $8
- **Content**: 5 vinyl stickers - crown, king of divine light, logo, tagline, blank
- **Copy (Piper)**: "5 stickers. Laptops, water bottles, cars. Put the crown where people can see it."

---

## Stripe product setup commands

Run once from a shell with `STRIPE_SECRET_KEY` in env.

```bash
# SKU 1: Hoodie
stripe products create \
  --name "Alley Kingz Hoodie - Drop 001" \
  --description "Heavyweight cotton hoodie. Gold foil crown on the back. Numbered interior tag. Limited to 50 per color." \
  --metadata[brand]=alley_kingz \
  --metadata[drop]=001 \
  --metadata[fulfillment]=pod_printful \
  --shippable true

stripe prices create \
  --product <HOODIE_PRODUCT_ID> \
  --unit_amount 6500 \
  --currency usd \
  --nickname "Hoodie base price"

# SKU 2: Tee
stripe products create \
  --name "Alley Kingz Tee" \
  --description "Heavyweight cotton tee. Embroidered crown. Everyday wear." \
  --metadata[brand]=alley_kingz \
  --metadata[fulfillment]=pod_printful \
  --shippable true

stripe prices create \
  --product <TEE_PRODUCT_ID> \
  --unit_amount 3200 \
  --currency usd \
  --nickname "Tee base price"

# SKU 3: Sticker pack
stripe products create \
  --name "Alley Kingz Founder Sticker Pack" \
  --description "5-piece vinyl sticker set." \
  --metadata[brand]=alley_kingz \
  --metadata[fulfillment]=manual_fulfilled_everlight \
  --shippable true

stripe prices create \
  --product <STICKERS_PRODUCT_ID> \
  --unit_amount 800 \
  --currency usd \
  --nickname "Sticker pack price"
```

Save each `price_xxx` into `.env`:

```
STRIPE_PRICE_AK_HOODIE=price_xxx
STRIPE_PRICE_AK_TEE=price_yyy
STRIPE_PRICE_AK_STICKERS=price_zzz
```

## Shipping

- All 3 products: $6 flat-rate US shipping, +$12 to CA.
- POD items (Hoodie, Tee) via Printful: 4-7 business days.
- Stickers: packed + shipped from Everlight ops (Lucrex mails them) for tight margin.
- Add shipping as a Stripe shipping rate at checkout session creation.

```bash
stripe shipping_rates create \
  --display_name "US Standard" \
  --type fixed_amount \
  --fixed_amount[amount]=600 \
  --fixed_amount[currency]=usd \
  --delivery_estimate[minimum][unit]=business_day \
  --delivery_estimate[minimum][value]=4 \
  --delivery_estimate[maximum][unit]=business_day \
  --delivery_estimate[maximum][value]=7
```

## Checkout flow (React + edge function)

User hits `/shop` on everlightventures.io, sees the 3 SKUs, clicks "Buy." React calls our edge function, which creates a Stripe Checkout Session, which Stripe hosts. Post-payment, Stripe redirects back to `/shop/thanks?order=<session_id>`.

### Edge function stub

Path: `01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/edge_functions/alley-kingz-checkout/index.ts`

```typescript
import Stripe from 'stripe';

export default {
  async fetch(request: Request, env: any): Promise<Response> {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }
    const { price_id, quantity, size, color } = await request.json();
    if (!price_id || !quantity) {
      return new Response(JSON.stringify({ error: 'missing fields' }), { status: 400 });
    }
    const stripe = new Stripe(env.STRIPE_SECRET_KEY, { apiVersion: '2024-06-20' });
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      line_items: [{ price: price_id, quantity }],
      shipping_address_collection: { allowed_countries: ['US'] },
      shipping_options: [{ shipping_rate: env.STRIPE_SHIPPING_RATE_US }],
      metadata: {
        brand: 'alley_kingz',
        size: size || '',
        color: color || '',
      },
      success_url: 'https://everlightventures.io/shop/thanks?order={CHECKOUT_SESSION_ID}',
      cancel_url: 'https://everlightventures.io/shop',
    });
    return new Response(JSON.stringify({ url: session.url }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
```

### React `/shop` page outline

Component: `src/pages/AlleyKingzShop.tsx`

```tsx
const products = [
  {
    id: 'hoodie',
    name: 'Alley Kingz Hoodie - Drop 001',
    price_id: import.meta.env.VITE_STRIPE_PRICE_AK_HOODIE,
    price_display: '$65',
    sizes: ['S','M','L','XL','2XL'],
    colors: ['Black','Cream'],
    image: '/shop/ak-hoodie.jpg',
  },
  // ...tee and stickers
];

async function checkout(product, qty, size, color) {
  const res = await fetch('/api/alley-kingz-checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ price_id: product.price_id, quantity: qty, size, color }),
  });
  const { url } = await res.json();
  window.location = url;
}
```

## Fulfillment process (manual at first)

A Stripe webhook fires on `checkout.session.completed`. Django receives it, parses the metadata, and:

- For POD items: submit order to Printful API (uses SKU metadata + shipping address from session)
- For manual items (stickers): drop a card into `#fun_chat` or `#ev-support` saying "pack and ship N stickers to <address>"
- Log the order to Supabase `alley_kingz_orders` table
- Send a receipt email via Resend (template already exists)

### Django webhook extension

Path: `09_DASHBOARD/hive_dashboard/payments/views.py` (add branch):

```python
if session["metadata"].get("brand") == "alley_kingz":
    from alley_kingz.fulfillment import fulfill_order
    fulfill_order(session)
    notify_slack("C0ANPRDUP0R", f"Alley Kingz order: {session['id']}")  # #content-factory
```

## Dashboard (Chart Dawson)

Django `/shop/alley-kingz/` view showing:
- Orders this week / this month
- Revenue bar chart
- Top SKU
- Pending fulfillments (those not yet shipped)
- Printful integration status

Reuses existing Shadcn card components. Chart should knock it out in 2 hours once orders exist.

## Printful integration (for POD SKUs)

Printful API is free to use; we pay only per-order at cost.

Required:
- Printful account (free signup)
- Printful API key in `.env` as `PRINTFUL_API_KEY`
- Product variants mapped to Printful product IDs (stored in product metadata)

Webhook handler makes one POST per order:

```bash
POST https://api.printful.com/orders
{
  "recipient": {...shipping address from Stripe...},
  "items": [{"variant_id": PRINTFUL_VARIANT_ID, "quantity": N}]
}
```

## MVP launch checklist

- [ ] Stripe products + prices created per commands above
- [ ] Price IDs saved in .env + Cloudflare env
- [ ] Printful account created, hoodie + tee variants picked + IDs stored
- [ ] Edge function `alley-kingz-checkout` deployed
- [ ] React `/shop` page implemented (3 product cards + qty/size/color selectors)
- [ ] Django webhook branch added for `brand=alley_kingz`
- [ ] Supabase table `alley_kingz_orders` created (session_id, email, sku, qty, address_json, status, created_at)
- [ ] Printful fulfillment function implemented for POD SKUs
- [ ] Receipt email template adjusted for store purchases
- [ ] Chart's `/shop/alley-kingz/` dashboard draft
- [ ] Product photos shot / AI-generated (ArtBible + Printful mockups)
- [ ] First 10 orders fulfilled manually; record any ops gaps

## Cost to launch

- Stripe: $0 floor
- Printful: $0 floor (per-order cost)
- Cloudflare: $0 (existing)
- Photography: use ArtBible AI-generated mockups first, $0
- Time: Forge ~6 hours for edge fn + webhook. Piper ~4 hours for catalog + copy. Chart ~2 hours for dashboard.

Total marginal cost: zero dollars, 12 hours of internal labor.

## Success metric for "we built it"

- 10 completed orders across the 3 SKUs in the first 30 days
- Zero customer-reported fulfillment errors
- Supabase + Django dashboard accurately reflect order state at all times
- Printful automation works without manual intervention for at least 5 POD orders

Once proven, same pattern scales to HIM Loadout, Everlight Literature direct sales, etc.

## What goes in git / what doesn't

- React page + edge function: in repo
- Stripe price IDs + Printful API key: `.env` only, never committed
- Product photos: `_uploads/` folder (gitignored until finalized)
- Supabase schema migration: `supabase/migrations/20260421_alley_kingz_orders.sql`

## Next actions

Say `ship alley kingz phase 1` in a future session and Forge picks up:
1. Creates Stripe products via CLI
2. Writes the Supabase migration
3. Writes the edge function
4. Writes the Django webhook branch

Lucrex picks: 3 product photos (or approves AI-generated mockups) + confirms the $65/$32/$8 pricing.
Piper picks: final copy on the 3 descriptions.
Chart picks: dashboard layout.
