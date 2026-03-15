# Stripe Product Catalog & Supabase Wiring Specification

**Everlight Ventures -- Payment Infrastructure Reference**
**Last Updated:** 2026-03-06
**Purpose:** Step-by-step reference for creating all 17 Stripe products and wiring them to Supabase Edge Functions, storage, and Slack notifications.

---

## STRIPE PRODUCTS (17 Total)

Create each product in the Stripe Dashboard under **Products > + Add product**. Use the exact names, prices, and metadata listed below.

---

### EBOOKS (One-Time Purchases)

| # | Stripe Product Name | Price | Billing | Slug |
|---|---------------------|-------|---------|------|
| 1 | Sam's First Superpower (Digital EPUB) | $6.99 | One-time | `sam-book-1` |
| 2 | Sam's Second Superpower (Digital EPUB) | $6.99 | One-time | `sam-book-2` |
| 3 | Sam's Third Superpower (Digital EPUB) | $6.99 | One-time | `sam-book-3` |
| 4 | Sam's Fourth Superpower (Digital EPUB) | $6.99 | One-time | `sam-book-4` |
| 5 | Sam's Fifth Superpower (Digital EPUB) | $6.99 | One-time | `sam-book-5` |
| 6 | Sam & Robo Complete Bundle (5 Books) | $29.99 | One-time | `sam-bundle` |
| 7 | Beyond the Veil (Digital EPUB) | $6.99 | One-time | `beyond-the-veil` |

#### Product Details

**1. Sam's First Superpower (Digital EPUB)**
- **Price:** $6.99 one-time
- **Description:** Join Sam on an adventure of self-discovery as he unlocks his very first superpower -- believing in himself. A beautifully illustrated children's book for ages 4-8.
- **Slug:** `sam-book-1`
- **Stripe Metadata:**
  - `product_type`: `ebook`
  - `slug`: `sam-book-1`
  - `series`: `adventures-with-sam`
  - `book_number`: `1`
  - `file_format`: `epub`

**2. Sam's Second Superpower (Digital EPUB)**
- **Price:** $6.99 one-time
- **Description:** Sam's adventure continues as he discovers a brand new superpower that changes everything. Book 2 in the beloved Adventures with Sam series for ages 4-8.
- **Slug:** `sam-book-2`
- **Stripe Metadata:**
  - `product_type`: `ebook`
  - `slug`: `sam-book-2`
  - `series`: `adventures-with-sam`
  - `book_number`: `2`
  - `file_format`: `epub`

**3. Sam's Third Superpower (Digital EPUB)**
- **Price:** $6.99 one-time
- **Description:** Sam faces his biggest challenge yet and unlocks superpower number three. Book 3 in the Adventures with Sam series for ages 4-8.
- **Slug:** `sam-book-3`
- **Stripe Metadata:**
  - `product_type`: `ebook`
  - `slug`: `sam-book-3`
  - `series`: `adventures-with-sam`
  - `book_number`: `3`
  - `file_format`: `epub`

**4. Sam's Fourth Superpower (Digital EPUB)**
- **Price:** $6.99 one-time
- **Description:** The adventure grows as Sam discovers superpower number four with help from his friend Robo. Book 4 in the Adventures with Sam series for ages 4-8.
- **Slug:** `sam-book-4`
- **Stripe Metadata:**
  - `product_type`: `ebook`
  - `slug`: `sam-book-4`
  - `series`: `adventures-with-sam`
  - `book_number`: `4`
  - `file_format`: `epub`

**5. Sam's Fifth Superpower (Digital EPUB)**
- **Price:** $6.99 one-time
- **Description:** The epic conclusion to Sam's journey as he unlocks his ultimate superpower. Book 5 in the Adventures with Sam series for ages 4-8.
- **Slug:** `sam-book-5`
- **Stripe Metadata:**
  - `product_type`: `ebook`
  - `slug`: `sam-book-5`
  - `series`: `adventures-with-sam`
  - `book_number`: `5`
  - `file_format`: `epub`

**6. Sam & Robo Complete Bundle (5 Books)**
- **Price:** $29.99 one-time
- **Description:** Get all 5 Adventures with Sam books in one bundle and save over $5. The complete illustrated series for ages 4-8, delivered as digital EPUBs.
- **Slug:** `sam-bundle`
- **Stripe Metadata:**
  - `product_type`: `ebook-bundle`
  - `slug`: `sam-bundle`
  - `series`: `adventures-with-sam`
  - `book_count`: `5`
  - `file_format`: `zip`

**7. Beyond the Veil (Digital EPUB)**
- **Price:** $6.99 one-time
- **Description:** A gripping standalone novel that pulls back the curtain on reality itself. Digital download, delivered instantly after purchase.
- **Slug:** `beyond-the-veil`
- **Stripe Metadata:**
  - `product_type`: `ebook`
  - `slug`: `beyond-the-veil`
  - `series`: `standalone`
  - `book_number`: `1`
  - `file_format`: `epub`

---

### ARCADE (One-Time Purchases)

| # | Stripe Product Name | Price | Billing | Slug |
|---|---------------------|-------|---------|------|
| 8 | Arcade Credits - 3 Lives Tier 1 | $0.25 | One-time | `arcade-lives-t1` |
| 9 | Arcade Credits - 3 Lives Tier 2 | $0.50 | One-time | `arcade-lives-t2` |
| 10 | Arcade Credits - 3 Lives Tier 3 | $1.00 | One-time | `arcade-lives-t3` |
| 11 | Arcade Day Pass | $2.99 | One-time | `arcade-day-pass` |

#### Product Details

**8. Arcade Credits - 3 Lives Tier 1**
- **Price:** $0.25 one-time
- **Description:** Drop a quarter, get 3 lives. Classic arcade style -- play any game in Alley Kingz.
- **Slug:** `arcade-lives-t1`
- **Stripe Metadata:**
  - `product_type`: `arcade-credits`
  - `slug`: `arcade-lives-t1`
  - `lives_granted`: `3`
  - `tier`: `1`

**9. Arcade Credits - 3 Lives Tier 2**
- **Price:** $0.50 one-time
- **Description:** Drop two quarters, get 3 lives with a bonus multiplier. Play any game in Alley Kingz.
- **Slug:** `arcade-lives-t2`
- **Stripe Metadata:**
  - `product_type`: `arcade-credits`
  - `slug`: `arcade-lives-t2`
  - `lives_granted`: `3`
  - `tier`: `2`

**10. Arcade Credits - 3 Lives Tier 3**
- **Price:** $1.00 one-time
- **Description:** Drop a dollar, get 3 lives with the maximum multiplier. Play any game in Alley Kingz.
- **Slug:** `arcade-lives-t3`
- **Stripe Metadata:**
  - `product_type`: `arcade-credits`
  - `slug`: `arcade-lives-t3`
  - `lives_granted`: `3`
  - `tier`: `3`

**11. Arcade Day Pass**
- **Price:** $2.99 one-time
- **Description:** Unlimited lives for 24 hours across every game in the Alley Kingz arcade. Play all day, no quarters needed.
- **Slug:** `arcade-day-pass`
- **Stripe Metadata:**
  - `product_type`: `arcade-pass`
  - `slug`: `arcade-day-pass`
  - `duration_hours`: `24`
  - `unlimited_lives`: `true`

---

### SUBSCRIPTIONS (Recurring)

| # | Stripe Product Name | Price | Billing | Slug |
|---|---------------------|-------|---------|------|
| 12 | Arcade VIP Monthly | $4.99/mo | Recurring (monthly) | `arcade-vip-monthly` |

#### Product Details

**12. Arcade VIP Monthly**
- **Price:** $4.99/month recurring
- **Description:** VIP arcade membership with unlimited daily lives, exclusive games, leaderboard badges, and early access to new Alley Kingz content. Cancel anytime.
- **Slug:** `arcade-vip-monthly`
- **Stripe Metadata:**
  - `product_type`: `subscription`
  - `slug`: `arcade-vip-monthly`
  - `tier`: `vip`
  - `perks`: `unlimited-lives,exclusive-games,badges,early-access`

---

### SEASON (One-Time Purchase)

| # | Stripe Product Name | Price | Billing | Slug |
|---|---------------------|-------|---------|------|
| 13 | Alley Kingz Season Pass | $7.99 | One-time | `ak-season-pass` |

#### Product Details

**13. Alley Kingz Season Pass**
- **Price:** $7.99 one-time
- **Description:** Unlock the full current season of Alley Kingz content -- all maps, characters, and bonus challenges included.
- **Slug:** `ak-season-pass`
- **Stripe Metadata:**
  - `product_type`: `season-pass`
  - `slug`: `ak-season-pass`
  - `season`: `current`
  - `includes`: `maps,characters,challenges`

---

### GEMS (One-Time Purchases)

| # | Stripe Product Name | Price | Billing | Slug |
|---|---------------------|-------|---------|------|
| 14 | Gem Pack Starter (100 Gems) | $0.99 | One-time | `gems-100` |
| 15 | Gem Pack Standard (600 Gems) | $4.99 | One-time | `gems-600` |
| 16 | Gem Pack Premium (1,500 Gems) | $9.99 | One-time | `gems-1500` |
| 17 | Gem Pack Ultra (4,000 Gems) | $19.99 | One-time | `gems-4000` |

#### Product Details

**14. Gem Pack Starter (100 Gems)**
- **Price:** $0.99 one-time
- **Description:** 100 gems to spend on skins, power-ups, and cosmetics in Alley Kingz. A quick starter boost.
- **Slug:** `gems-100`
- **Stripe Metadata:**
  - `product_type`: `gems`
  - `slug`: `gems-100`
  - `gem_count`: `100`
  - `tier`: `starter`

**15. Gem Pack Standard (600 Gems)**
- **Price:** $4.99 one-time
- **Description:** 600 gems for Alley Kingz -- 20% bonus over buying starters individually. Unlock skins, power-ups, and more.
- **Slug:** `gems-600`
- **Stripe Metadata:**
  - `product_type`: `gems`
  - `slug`: `gems-600`
  - `gem_count`: `600`
  - `tier`: `standard`

**16. Gem Pack Premium (1,500 Gems)**
- **Price:** $9.99 one-time
- **Description:** 1,500 gems for Alley Kingz -- best value for regular players. Unlock premium skins, power-ups, and exclusive items.
- **Slug:** `gems-1500`
- **Stripe Metadata:**
  - `product_type`: `gems`
  - `slug`: `gems-1500`
  - `gem_count`: `1500`
  - `tier`: `premium`

**17. Gem Pack Ultra (4,000 Gems)**
- **Price:** $19.99 one-time
- **Description:** 4,000 gems for Alley Kingz -- the ultimate gem haul with maximum value. Go all-in on customization and power-ups.
- **Slug:** `gems-4000`
- **Stripe Metadata:**
  - `product_type`: `gems`
  - `slug`: `gems-4000`
  - `gem_count`: `4000`
  - `tier`: `ultra`

---

## SUPABASE EDGE FUNCTIONS

Four Edge Functions handle all post-purchase logic. Each is deployed to Supabase and called either by Stripe webhook or by the frontend after a Checkout Session completes.

---

### 1. verify-ebook-purchase

**Trigger:** Called by frontend after Stripe Checkout redirect with `session_id` query param.

**Inputs:**
```
POST /verify-ebook-purchase
{
  "session_id": "cs_live_abc123..."
}
```

**Logic:**
1. Call `stripe.checkout.sessions.retrieve(session_id)` and confirm `payment_status === "paid"`
2. Extract `slug` from session metadata
3. Insert row into `ebook_purchases` table
4. Generate a one-time download token (UUID v4), insert into `download_tokens` table with 24-hour expiry
5. Generate a Supabase Storage signed URL for the file in the `ebooks` bucket (1-hour expiry)
6. Post Slack notification
7. Return `{ download_url, token, expires_at }` to frontend

**Supabase Tables Touched:**

| Table | Operation | Fields |
|-------|-----------|--------|
| `ebook_purchases` | INSERT | `id`, `stripe_session_id`, `stripe_customer_id`, `email`, `slug`, `amount_cents`, `currency`, `purchased_at` |
| `download_tokens` | INSERT | `id`, `token` (UUID), `purchase_id` (FK), `slug`, `expires_at` (now + 24h), `used` (false), `created_at` |

**Outputs:**
```json
{
  "success": true,
  "download_url": "https://<project>.supabase.co/storage/v1/object/sign/ebooks/sam-book-1/Sams_First_Superpower.epub?token=...",
  "token": "a1b2c3d4-...",
  "expires_at": "2026-03-07T12:00:00Z"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Payment not confirmed or session expired."
}
```

---

### 2. verify-arcade-purchase

**Trigger:** Called by frontend after Stripe Checkout redirect with `session_id` query param.

**Inputs:**
```
POST /verify-arcade-purchase
{
  "session_id": "cs_live_abc123...",
  "player_id": "player_uuid_here"
}
```

**Logic:**
1. Call `stripe.checkout.sessions.retrieve(session_id)` and confirm `payment_status === "paid"`
2. Extract `slug` and `product_type` from session metadata
3. Route by product type:
   - `arcade-credits`: Add `lives_granted` to `player_accounts.lives_balance`
   - `arcade-pass`: Insert row into `arcade_sessions` with `expires_at = now + 24h`
   - `season-pass`: Set `player_accounts.season_pass = true`, record season identifier
4. Insert row into `arcade_purchases` table
5. Post Slack notification
6. Return updated player state

**Supabase Tables Touched:**

| Table | Operation | Fields |
|-------|-----------|--------|
| `arcade_purchases` | INSERT | `id`, `stripe_session_id`, `player_id`, `slug`, `amount_cents`, `product_type`, `purchased_at` |
| `player_accounts` | UPSERT | `player_id`, `lives_balance`, `season_pass`, `vip_status`, `updated_at` |
| `arcade_sessions` | INSERT (day pass only) | `id`, `player_id`, `session_type` (`day-pass`), `started_at`, `expires_at` |

**Outputs:**
```json
{
  "success": true,
  "player_id": "player_uuid",
  "lives_balance": 6,
  "active_day_pass": false,
  "season_pass": false
}
```

---

### 3. verify-gem-purchase

**Trigger:** Called by frontend after Stripe Checkout redirect with `session_id` query param.

**Inputs:**
```
POST /verify-gem-purchase
{
  "session_id": "cs_live_abc123...",
  "player_id": "player_uuid_here"
}
```

**Logic:**
1. Call `stripe.checkout.sessions.retrieve(session_id)` and confirm `payment_status === "paid"`
2. Extract `slug` and `gem_count` from session metadata
3. Add `gem_count` to `player_accounts.gem_balance`
4. Insert row into `gem_purchases` table
5. Post Slack notification
6. Return updated gem balance

**Supabase Tables Touched:**

| Table | Operation | Fields |
|-------|-----------|--------|
| `gem_purchases` | INSERT | `id`, `stripe_session_id`, `player_id`, `slug`, `gem_count`, `amount_cents`, `purchased_at` |
| `player_accounts` | UPDATE | `gem_balance` (+= gem_count), `updated_at` |

**Outputs:**
```json
{
  "success": true,
  "player_id": "player_uuid",
  "gems_added": 600,
  "gem_balance": 1200
}
```

---

### 4. stripe-webhook-handler

**Trigger:** Stripe sends POST to this endpoint. Configure in Stripe Dashboard under Developers > Webhooks.

**Webhook Events to Listen For:**
- `checkout.session.completed` -- backup fulfillment (if frontend verify call failed)
- `customer.subscription.created` -- new VIP subscription
- `customer.subscription.updated` -- plan changes
- `customer.subscription.deleted` -- VIP cancellation
- `invoice.payment_succeeded` -- monthly VIP renewal
- `invoice.payment_failed` -- failed renewal

**Inputs:**
```
POST /stripe-webhook-handler
Headers: { "stripe-signature": "whsec_..." }
Body: raw Stripe event payload
```

**Logic:**
1. Verify webhook signature using `STRIPE_WEBHOOK_SECRET`
2. Route by `event.type`:
   - `customer.subscription.created`: Set `player_accounts.vip_status = true`, `vip_started_at = now`
   - `customer.subscription.deleted`: Set `player_accounts.vip_status = false`, `vip_ended_at = now`
   - `invoice.payment_succeeded`: Update `player_accounts.vip_renewed_at = now`, post Slack
   - `invoice.payment_failed`: Post Slack alert with customer email, do NOT revoke VIP yet (Stripe retries)
   - `checkout.session.completed`: Fallback fulfillment -- check if purchase already recorded, if not run the appropriate verify logic
3. Insert event into `stripe_events` audit log

**Supabase Tables Touched:**

| Table | Operation | Fields |
|-------|-----------|--------|
| `player_accounts` | UPDATE | `vip_status`, `vip_started_at`, `vip_ended_at`, `vip_renewed_at` |
| `stripe_events` | INSERT | `id`, `event_id` (Stripe event ID), `event_type`, `customer_id`, `payload` (JSONB), `processed_at` |

**Outputs:**
```json
{ "received": true }
```
Always return 200 to Stripe, even on processing errors (log errors internally, do not cause Stripe retries).

---

## SUPABASE STORAGE

### Bucket: `ebooks`

**Access:** Private (no public access). All downloads go through signed URLs generated by Edge Functions.

**Bucket Policy:** Only the `service_role` key can generate signed URLs. Frontend never accesses storage directly.

```
ebooks/
  sam-book-1/
    Sams_First_Superpower.epub
  sam-book-2/
    Sams_Second_Superpower.epub
  sam-book-3/
    Sams_Third_Superpower.epub
  sam-book-4/
    Sams_Fourth_Superpower.epub
  sam-book-5/
    Sams_Fifth_Superpower.epub
  sam-bundle/
    Sam_And_Robo_Complete.zip
  beyond-the-veil/
    Beyond_The_Veil.epub
```

**Slug-to-Path Mapping (used by verify-ebook-purchase):**

| Slug | Storage Path |
|------|-------------|
| `sam-book-1` | `ebooks/sam-book-1/Sams_First_Superpower.epub` |
| `sam-book-2` | `ebooks/sam-book-2/Sams_Second_Superpower.epub` |
| `sam-book-3` | `ebooks/sam-book-3/Sams_Third_Superpower.epub` |
| `sam-book-4` | `ebooks/sam-book-4/Sams_Fourth_Superpower.epub` |
| `sam-book-5` | `ebooks/sam-book-5/Sams_Fifth_Superpower.epub` |
| `sam-bundle` | `ebooks/sam-bundle/Sam_And_Robo_Complete.zip` |
| `beyond-the-veil` | `ebooks/beyond-the-veil/Beyond_The_Veil.epub` |

---

## SUPABASE TABLE SCHEMAS

### ebook_purchases
```sql
CREATE TABLE ebook_purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stripe_session_id TEXT UNIQUE NOT NULL,
  stripe_customer_id TEXT,
  email TEXT NOT NULL,
  slug TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  currency TEXT DEFAULT 'usd',
  purchased_at TIMESTAMPTZ DEFAULT now()
);
```

### download_tokens
```sql
CREATE TABLE download_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  token UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
  purchase_id UUID REFERENCES ebook_purchases(id),
  slug TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### player_accounts
```sql
CREATE TABLE player_accounts (
  player_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE,
  display_name TEXT,
  lives_balance INTEGER DEFAULT 0,
  gem_balance INTEGER DEFAULT 0,
  vip_status BOOLEAN DEFAULT false,
  vip_started_at TIMESTAMPTZ,
  vip_ended_at TIMESTAMPTZ,
  vip_renewed_at TIMESTAMPTZ,
  season_pass BOOLEAN DEFAULT false,
  season_id TEXT,
  stripe_customer_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### arcade_purchases
```sql
CREATE TABLE arcade_purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stripe_session_id TEXT UNIQUE NOT NULL,
  player_id UUID REFERENCES player_accounts(player_id),
  slug TEXT NOT NULL,
  product_type TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  purchased_at TIMESTAMPTZ DEFAULT now()
);
```

### arcade_sessions
```sql
CREATE TABLE arcade_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_id UUID REFERENCES player_accounts(player_id),
  session_type TEXT NOT NULL,
  started_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);
```

### gem_purchases
```sql
CREATE TABLE gem_purchases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stripe_session_id TEXT UNIQUE NOT NULL,
  player_id UUID REFERENCES player_accounts(player_id),
  slug TEXT NOT NULL,
  gem_count INTEGER NOT NULL,
  amount_cents INTEGER NOT NULL,
  purchased_at TIMESTAMPTZ DEFAULT now()
);
```

### stripe_events
```sql
CREATE TABLE stripe_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id TEXT UNIQUE NOT NULL,
  event_type TEXT NOT NULL,
  customer_id TEXT,
  payload JSONB,
  processed_at TIMESTAMPTZ DEFAULT now()
);
```

---

## SLACK NOTIFICATION FORMAT

All notifications post to the `#sales` Slack channel via incoming webhook. Use the `SLACK_WEBHOOK_URL` environment variable stored in Supabase Edge Function secrets.

---

### Ebook Purchase

```
New Ebook Sale
Book: Sam's First Superpower
Customer: customer@email.com
Amount: $6.99
Stripe Session: cs_live_abc123
Time: 2026-03-06 2:15 PM PT
```

### Ebook Bundle Purchase

```
New Bundle Sale
Bundle: Sam & Robo Complete Bundle (5 Books)
Customer: customer@email.com
Amount: $29.99
Stripe Session: cs_live_abc123
Time: 2026-03-06 2:15 PM PT
```

### Arcade Credits Purchase

```
Arcade Credit Sale
Product: Arcade Credits - 3 Lives Tier 2
Player: player_display_name
Lives Added: 3
Amount: $0.50
Time: 2026-03-06 2:15 PM PT
```

### Arcade Day Pass Purchase

```
Day Pass Activated
Player: player_display_name
Expires: 2026-03-07 2:15 PM PT
Amount: $2.99
Time: 2026-03-06 2:15 PM PT
```

### Season Pass Purchase

```
Season Pass Sale
Player: player_display_name
Season: Current
Amount: $7.99
Time: 2026-03-06 2:15 PM PT
```

### Gem Purchase

```
Gem Pack Sale
Pack: Gem Pack Standard (600 Gems)
Player: player_display_name
Gems Added: 600
New Balance: 1,200
Amount: $4.99
Time: 2026-03-06 2:15 PM PT
```

### VIP Subscription Created

```
New VIP Subscriber
Player: player_display_name
Email: customer@email.com
Plan: Arcade VIP Monthly ($4.99/mo)
Started: 2026-03-06 2:15 PM PT
```

### VIP Renewal Success

```
VIP Renewal Success
Player: player_display_name
Email: customer@email.com
Amount: $4.99
Next Renewal: 2026-04-06
```

### VIP Cancellation

```
VIP Cancellation
Player: player_display_name
Email: customer@email.com
Active Until: 2026-04-06
Reason: customer_cancelled
```

### VIP Payment Failed (Alert)

```
[ALERT] VIP Payment Failed
Email: customer@email.com
Stripe Customer: cus_abc123
Amount Due: $4.99
Retry: Stripe will retry automatically
Action: Monitor -- do not revoke VIP yet
```

---

## ENVIRONMENT VARIABLES (Supabase Edge Function Secrets)

Set these in the Supabase Dashboard under Edge Functions > Secrets:

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe secret key (sk_live_...) |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret (whsec_...) |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL for #sales channel |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for storage signed URLs |

---

## STRIPE DASHBOARD SETUP CHECKLIST

1. Create all 17 products with exact names listed above
2. Add metadata key-value pairs to each product
3. Under Developers > Webhooks, add endpoint pointing to `https://<project>.supabase.co/functions/v1/stripe-webhook-handler`
4. Select these webhook events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`
5. Copy the webhook signing secret to Supabase Edge Function secrets
6. Enable Stripe Tax if applicable to your jurisdiction
7. Set up Stripe Customer Portal for VIP subscribers to manage/cancel

---

## QUICK REFERENCE: SLUG TO PRODUCT TYPE ROUTING

Used by Edge Functions to determine which verification path to run:

| Slug Pattern | Product Type | Edge Function |
|-------------|-------------|---------------|
| `sam-book-*` | ebook | verify-ebook-purchase |
| `sam-bundle` | ebook-bundle | verify-ebook-purchase |
| `beyond-the-veil` | ebook | verify-ebook-purchase |
| `arcade-lives-*` | arcade-credits | verify-arcade-purchase |
| `arcade-day-pass` | arcade-pass | verify-arcade-purchase |
| `arcade-vip-monthly` | subscription | stripe-webhook-handler |
| `ak-season-pass` | season-pass | verify-arcade-purchase |
| `gems-*` | gems | verify-gem-purchase |
