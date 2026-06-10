# Alley Kingz Stripe Go-Live Runbook

From "operator pastes keys" to "live $4.99 test checkout". Run steps in order.
Nothing here runs without keys. The seeder and the shop edge function are both
fail-closed: the seeder refuses live keys, and the shop refuses live charges
while AK_SHOP_TEST_MODE is on.

Project ref: `jdqqmsmwmbsnlnstyavl`
Workspace root: `/mnt/sdcard/AA_MY_DRIVE`

---

## Phase 1: Test mode end to end (sk_test key)

### Step 1. Operator pastes the Stripe TEST secret key

Export it in the shell only. Do not write it to any file in the repo.

```bash
export STRIPE_SECRET_KEY=sk_test_PASTE_HERE
```

### Step 2. Run the seeder (creates 5 gem products + prices in Stripe test mode)

```bash
cd /mnt/sdcard/AA_MY_DRIVE
STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY python3 03_AUTOMATION_CORE/01_Scripts/ak_stripe_seed_products.py --dry-run
STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY python3 03_AUTOMATION_CORE/01_Scripts/ak_stripe_seed_products.py
```

The seeder is idempotent (safe to re-run) and refuses any non-test key.
Output lands at `_state/ak_stripe_products.json`. Pull the 5 price ids:

```bash
python3 -c "import json; d=json.load(open('/mnt/sdcard/AA_MY_DRIVE/_state/ak_stripe_products.json'))['products']; [print(k, v['price_id']) for k,v in d.items()]"
```

### Step 3. Apply the migrations, in this order

20260607 (economy tables) must land before 20260610 (shop products, which
references the economy schema). Apply the specific files. Do NOT blanket-apply
the whole folder, because `20260607_alley_kingz_economy_down.sql` sits in the
same directory and a lexicographic push would run the down right after the up.

```bash
cd /mnt/sdcard/AA_MY_DRIVE
supabase db push --include-all=false   # or apply manually, in this order:
# 1. supabase/migrations/20260607_alley_kingz_economy.sql
# 2. supabase/migrations/20260607_alley_kingz_economy_seed.sql
# 3. supabase/migrations/20260610_ak_shop_products.sql
```

If using psql directly:

```bash
psql "$SUPABASE_DB_URL" -f supabase/migrations/20260607_alley_kingz_economy.sql
psql "$SUPABASE_DB_URL" -f supabase/migrations/20260607_alley_kingz_economy_seed.sql
psql "$SUPABASE_DB_URL" -f supabase/migrations/20260610_ak_shop_products.sql
```

### Step 4. Set the edge function secrets (5 price ids + the Stripe key)

Replace each `price_...` with the matching price_id from Step 2.

```bash
supabase secrets set --project-ref jdqqmsmwmbsnlnstyavl \
  STRIPE_SECRET_KEY=sk_test_PASTE_HERE \
  AK_PRICE_AK_GEMS_ROOKIE=price_xxx \
  AK_PRICE_AK_GEMS_PLAYER=price_xxx \
  AK_PRICE_AK_GEMS_BALLER=price_xxx \
  AK_PRICE_AK_GEMS_HIGHROLLER=price_xxx \
  AK_PRICE_AK_GEMS_KINGPIN=price_xxx
```

Optional but recommended: backfill `ak_shop_products.stripe_product_id` and
`stripe_price_id` from the seeder JSON so the shop table carries the ids too.

### Step 5. Deploy the edge functions

```bash
supabase functions deploy create-checkout --project-ref jdqqmsmwmbsnlnstyavl
supabase functions deploy alley-kingz-shop --project-ref jdqqmsmwmbsnlnstyavl
supabase functions deploy stripe-webhook --project-ref jdqqmsmwmbsnlnstyavl
```

### Step 6. Test checkout ($4.99 rookie pack, Stripe test card)

```bash
curl -s -X POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/create-checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -d '{"slug":"ak-gems-rookie"}'
```

Expect `{"url": "https://checkout.stripe.com/...", "session_id": "cs_test_..."}`.
Open the URL, pay with test card `4242 4242 4242 4242`, any future expiry, any
CVC. Amount must read $4.99.

---

## Phase 2: Go live (operator + legal greenlight required)

The seeder will NOT create live-mode products (it refuses sk_live keys by
design). Recreate the 5 products and prices in the Stripe dashboard in live
mode (same names, amounts, and metadata: sku, game_id=alley-kingz), or get an
explicit operator decision to adapt the seeder.

### Step 7. Swap secrets to live values

```bash
supabase secrets set --project-ref jdqqmsmwmbsnlnstyavl \
  STRIPE_SECRET_KEY=sk_live_PASTE_HERE \
  AK_PRICE_AK_GEMS_ROOKIE=price_LIVE_xxx \
  AK_PRICE_AK_GEMS_PLAYER=price_LIVE_xxx \
  AK_PRICE_AK_GEMS_BALLER=price_LIVE_xxx \
  AK_PRICE_AK_GEMS_HIGHROLLER=price_LIVE_xxx \
  AK_PRICE_AK_GEMS_KINGPIN=price_LIVE_xxx
```

### Step 8. Flip test mode off

Only after operator + legal greenlight. While AK_SHOP_TEST_MODE is on (the
default), the shop blocks live charges even if a live key is set.

```bash
supabase secrets set --project-ref jdqqmsmwmbsnlnstyavl AK_SHOP_TEST_MODE=false
```

### Step 9. Redeploy so the new secrets take effect

```bash
supabase functions deploy create-checkout --project-ref jdqqmsmwmbsnlnstyavl
supabase functions deploy alley-kingz-shop --project-ref jdqqmsmwmbsnlnstyavl
```

### Step 10. Live $4.99 test checkout

Repeat the Step 6 curl, open the URL, and pay $4.99 with a REAL card. Then
refund it from the Stripe dashboard once verification passes.

---

## Verification checklist

Before flipping live, confirm every box in test mode first.

- [ ] Seeder ran clean and `_state/ak_stripe_products.json` has 5 price ids
- [ ] All 5 products visible in the Stripe dashboard (test mode) with metadata sku + game_id
- [ ] Migrations applied: `ak_shop_products` table exists with 5 gem-pack rows
- [ ] Secrets set: `supabase secrets list --project-ref jdqqmsmwmbsnlnstyavl` shows STRIPE_SECRET_KEY plus the 5 AK_PRICE_ vars
- [ ] create-checkout with `ak-gems-rookie` returns a checkout URL (not a 400)
- [ ] create-checkout with a bogus slug still returns 400 "Invalid or missing slug"
- [ ] BEFORE secrets were set, `ak-gems-rookie` returned the same 400 (env fallback works)
- [ ] Checkout page shows $4.99 for rookie, $9.99 player, $19.99 baller, $49.99 high roller, $99.99 kingpin
- [ ] Completed test payment fires stripe-webhook and `product_type` metadata is `gems` (not `unknown`)
- [ ] `gem_purchases` (or shop fulfillment path) shows the purchase row
- [ ] Gems credited to the test account in game
- [ ] Live phase only: real $4.99 charge appears in Stripe live mode, gems credit, refund issued
- [ ] Live phase only: AK_SHOP_TEST_MODE=false was set AFTER operator + legal greenlight, never before
