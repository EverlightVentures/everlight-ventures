# Alley Kingz Shop Wiring (Stripe x Supabase, TEST MODE)

Status: scaffolded 2026-06-10. Nothing deployed, no migrations applied, no live keys touched.

## What exists

| Piece | Location | Role |
|---|---|---|
| Edge function | `supabase/functions/alley-kingz-shop/index.ts` | Server-authoritative shop API. `game_id = 'alley-kingz'`. Actions: get-shop, buy-card, open-chest, level-up-card, level-up-tower, buy-gems, confirm-gems, top-off-card, open-draw. Fail-closed: `liveBlocked()` rejects any `sk_live_` key while `AK_SHOP_TEST_MODE` is on. |
| Economy schema | `supabase/migrations/20260607_alley_kingz_economy.sql` | Defines `ak_shop_products`, `ak_card_catalog`, `ak_level_costs`, `ak_card_inventory`, `ak_tower_levels`, `ak_chest_inventory`, `ak_transactions`, heals `game_currencies` / `player_accounts`. RLS: public read on reference tables, own-row read on player state, service-role writes only. |
| Economy seed | `supabase/migrations/20260607_alley_kingz_economy_seed.sql` | 48 cards + 5 spells, 54 level-cost bands, 14 products. |
| Product catalog seed (NEW) | `supabase/migrations/20260610_ak_shop_products.sql` | Idempotent upsert of all 14 products. Adds `art_path` (`assets/shop/<sku>.png`) plus `stripe_product_id` / `stripe_price_id` columns to `ak_shop_products`. |
| Stripe seeder (NEW) | `03_AUTOMATION_CORE/01_Scripts/ak_stripe_seed_products.py` | Creates the 5 gem packs as Stripe Products + Prices (TEST keys only, refuses sk_live). Writes ids to `_state/ak_stripe_products.json`. |
| Checkout router | `supabase/functions/create-checkout/index.ts` | Hardcoded `PRICE_MAP` slug -> Stripe price id. The 5 `ak-gems-*` slugs are NOT in it yet; the seeder output supplies them. |
| Client | `01_BUSINESSES/.../Alley_Kingz/ecosystem/game/shop/shop.js` | Calls the edge function; demo mode mirrors the same SKUs offline. |

Canonical gem SKUs (sku == checkout_slug):

| SKU | Title | USD | Gems |
|---|---|---|---|
| ak-gems-rookie | Rookie Stash | 4.99 | 500 |
| ak-gems-player | Player Pack | 9.99 | 1100 |
| ak-gems-baller | Baller Bag | 19.99 | 2500 |
| ak-gems-highroller | High Roller Crate | 49.99 | 6500 |
| ak-gems-kingpin | Kingpin Vault | 99.99 | 14000 |

Chests: `chest_scrap_crate` (40 gems, fixed), `chest_crew` (150, fixed), `chest_chop_shop` (400, random, gated), `chest_kingpin` (900, random, gated), `chest_mythic_vault` (2000, random, gated). Lucky Draw: 100 gems / 900 gems 10-pull, odds + pity served by the edge function.

## Apply the migration (when ready, NOT done yet)

```bash
# linked project
supabase db push
# or direct
psql "$SUPABASE_DB_URL" -f supabase/migrations/20260610_ak_shop_products.sql
```

Idempotent: safe to re-run. It heals the table if `20260607` never ran, adds the new columns, and upserts the catalog with `ON CONFLICT (sku) DO UPDATE`.

## Run the Stripe seeder (TEST key only)

```bash
export STRIPE_SECRET_KEY=sk_test_...   # TEST key. sk_live is refused, hard exit 2.
python3 03_AUTOMATION_CORE/01_Scripts/ak_stripe_seed_products.py --dry-run   # preview
python3 03_AUTOMATION_CORE/01_Scripts/ak_stripe_seed_products.py             # create
```

Output: `_state/ak_stripe_products.json` with `{sku: {product_id, price_id, ...}}`. Idempotent: looks up products by `metadata.sku` + `metadata.game_id` before creating, reuses matching active USD prices.

Then wire the ids:
1. Add the 5 `"ak-gems-*": "price_..."` entries to `PRICE_MAP` in `supabase/functions/create-checkout/index.ts` (TEST price ids).
2. Optional: backfill `ak_shop_products.stripe_product_id` / `stripe_price_id` from the JSON for audit/receipt use.

## Basket / checkout flow

1. Client POSTs `{action:"get-shop", player_id}` -> catalog (`ak_shop_products` where active, by sort_order), card catalog, level costs, player snapshot, draw odds, test-mode disclaimer.
2. Gem purchase: `{action:"buy-gems", sku, player_id, success_url, cancel_url}` -> edge fn loads the product, calls `create-checkout` server-to-server with `slug = checkout_slug` and metadata `{player_id, game_id, ak_sku}` -> returns the Stripe Checkout URL (TEST).
3. After redirect back: `{action:"confirm-gems", session_id, player_id}` -> verifies `payment_status == "paid"` with Stripe, credits `grants.gems` into `game_currencies`. Idempotent: the unique `ak_transactions.stripe_event_id` row (`gems:<session_id>`) is the lock, so double-confirms return `already_credited`.
4. Gem spends (chests, Lucky Draw, top-offs) are all server-side debits against `game_currencies`; every mutation lands in `ak_transactions`.

## What flips for LIVE (gated, operator + legal greenlight required)

Currently fail-closed at three layers; ALL must change deliberately:
1. `AK_SHOP_TEST_MODE` env on the edge function: defaults to test; only `"false"` disables the guard.
2. `STRIPE_SECRET_KEY` swapped to a REVIEWED live key. Until step 1, any `sk_live_` key makes buy-gems/confirm-gems return `LIVE_STRIPE_BLOCKED` (403, no charge attempted).
3. The seeder must be re-run with a live key it currently REFUSES; lifting that refusal is a deliberate code change after operator + legal go-live (Lane A posture: in-game value only, no cash-out, random chests stay gated until legal Gate 3).

Also for live: re-create Products/Prices in live mode (test ids do not carry over) and update `PRICE_MAP` with live price ids.

## Art

`art_path = assets/shop/<sku>.png`. Per the no-generic-art doctrine, enqueue each missing tile in the art_factory queue (`art_factory.py --enqueue`) so Leonardo replaces placeholders via the daily cron.
