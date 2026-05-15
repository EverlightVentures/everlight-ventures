# Everlight Open Deal -- Build Spec (Buyer War Page)

**Status:** Ready for Hive sprint
**Sprint length:** 7-10 days
**Cost to launch:** $0 (everything on free tiers)
**Brand:** CarMax of wholesaling. Apple-store calm with auction-house tension. Gold-on-dark.

---

## Pages to build on `everlightventures.io`

1. **`/drops`** -- Live buyer war page. Public feed of fresh TN parcels.
2. **`/drops/[id]`** -- Single drop detail. Photos, numbers, "Lock 24h" CTA.
3. **`/buyer/dashboard`** -- My locks. My status. Tier upgrade prompts.
4. **`/verify`** -- $99 Verified tier upgrade. KYC-lite upload flow.
5. **`/inner-circle`** -- $49/mo Inner Circle subscription page.
6. **`/legal/lock-fee-disclosure`** -- Public render of `BUYER_DISCLOSURE_LOCK_FEE.md`. Linked from every Lock button.

---

## Supabase tables (3 new migrations)

```sql
-- 1. deal_drops -- fresh parcels become drops
create table deal_drops (
  id uuid primary key default gen_random_uuid(),
  parcel_id text not null,
  county text not null,
  state text not null default 'TN',
  address text not null,
  asking_price int not null,
  arv int,
  rehab_estimate int,
  spread int generated always as (arv - asking_price - rehab_estimate) stored,
  hero_photo_url text,
  gallery jsonb default '[]'::jsonb,
  signal_summary text,  -- the OSINT seller intel digest
  status text default 'live',  -- live | locked | sold | expired
  current_lock_id uuid,
  inner_circle_visible_at timestamptz default now(),
  public_visible_at timestamptz default now() + interval '4 hours',
  created_at timestamptz default now(),
  created_by text default 'inbound_watch_daemon'
);

-- 2. drop_locks -- one row per lock event
create table drop_locks (
  id uuid primary key default gen_random_uuid(),
  drop_id uuid references deal_drops(id),
  buyer_id uuid references auth.users(id),
  tier text not null,  -- browser | verified | inner_circle
  stripe_payment_intent_id text,
  lock_fee_cents int not null,
  lock_started_at timestamptz default now(),
  lock_expires_at timestamptz default now() + interval '24 hours',
  outcome text default 'pending',  -- pending | signed | walked | expired
  outcome_at timestamptz,
  refund_amount_cents int,
  house_kept_cents int,
  disclosure_version text default '1.0',
  disclosure_accepted_at timestamptz,
  disclosure_client_ip inet
);

-- 3. pulse_events -- the live activity feed
create table pulse_events (
  id bigserial primary key,
  event_type text not null,  -- drop_created | lock_initiated | viewing | lock_disclosure_accepted | walked | signed | sold
  drop_id uuid references deal_drops(id),
  buyer_id uuid references auth.users(id),
  tier text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
create index on pulse_events (created_at desc);
create index on pulse_events (drop_id, created_at desc);
```

RLS enabled on all three. Buyers see public drops + their own locks. Service role bypasses.

---

## Code surfaces (~265 LOC total)

### Frontend (`06_DEVELOPMENT/everlightventures/`)

- `src/routes/drops/+page.svelte` -- public feed, Supabase Realtime subscribed to `pulse_events`. ~80 LOC.
- `src/routes/drops/[id]/+page.svelte` -- detail + Lock modal + disclosure consent + Stripe Checkout redirect. ~70 LOC.
- `src/routes/buyer/dashboard/+page.svelte` -- buyer's locks list, tier badge, upgrade CTAs. ~40 LOC.
- `src/routes/verify/+page.svelte` + `src/routes/inner-circle/+page.svelte` -- Stripe Checkout for $99 KYC + $49/mo sub. ~30 LOC each.
- `src/routes/legal/lock-fee-disclosure/+page.svelte` -- markdown render. ~10 LOC.

### Cloudflare Worker (webhook handler, `functions/api/stripe/webhook.ts`)

- Single endpoint, ~80 LOC.
- Listens to `payment_intent.succeeded`, `payment_intent.canceled`, `customer.subscription.*`, `refund.created`.
- Inserts/updates `drop_locks` + writes `pulse_events`.

### Hive integration (existing code)

- `inbound_watch_daemon` -> add 10 LOC to push new parcel JSON to `deal_drops` table on ingest.
- `hive_deal_orchestrator` -> add 10 LOC to listen for `drop_locks.outcome='signed'` and kick off PSA generation.
- `branded_mailer` -> add 5 LOC to send "Drop locked by X" notification to non-locking buyers (creates FOMO).
- `branded_slack` -> add 5 LOC to push every drop to `#broker-pipeline` as a card with View Drop button.

---

## Hive dispatch (parallel, single message)

When Rich greenlights, dispatch in one message:

1. `62_frontend_architect` -- scaffold the 5 Svelte routes against existing CF Pages site
2. `67_backend_architect` -- write the 3 Supabase migrations + RLS policies
3. `64_component_engineer` -- build the Drop Card component + Pulse Feed component
4. `74_growth_engineer` -- wire the Stripe Checkout flows for all 3 tiers
5. `legal_heck_aurelio` + `legal_priya_bhattacharya` -- countersign disclosure draft + flag open questions
6. `state_marvin_tn` -- re-brief Chris on the new model, get his sign-off on the auto-comp arrangement
7. `state_lo_hines_tn` -- audit the disclosure against TN-specific rules
8. `68_devops_engineer` -- ship CF Worker for Stripe webhooks + Supabase migration deploys

Marcus Cole orchestrates the converge.

---

## Day-by-day sprint

- **Day 1:** Migrations + RLS + Stripe SKUs created (`create_stripe_skus.sh` extended). Disclosure countersign begins.
- **Day 2-3:** Frontend scaffolding, Drop Card + Pulse Feed components.
- **Day 4:** Stripe Checkout flows wired for all 3 tiers. Webhook handler deployed.
- **Day 5:** `inbound_watch_daemon` integration. First synthetic drop end-to-end with TEST keys.
- **Day 6:** Disclosure copy locked. Buyer dashboard. Inner Circle subscription page.
- **Day 7:** Chris re-brief by Marvin. Marquise dry-run on staging. Synthetic walks + signs tested.
- **Day 8-9:** Real-money smoke test with Chris on a real TN parcel (test the full Inner Circle flow).
- **Day 10:** Public soft launch. First 5 outreach buyers from existing pipeline get invite-only Verified upgrade.

---

## Pre-launch checklist (Rich greenlight before public soft launch)

- [ ] Disclosure draft countersigned by `legal_heck_aurelio`
- [ ] Stripe live keys swapped in (production)
- [ ] Mid South Title relationship confirmed for Inner Circle EMD flow (Marvin owns)
- [ ] Chris explicitly approves auto-comp + ANCHOR badge placement (Marvin owns)
- [ ] First 3 real drops in `deal_drops` table (real Memphis parcels from `Wholesale/owner_downloads/parsed/`)
- [ ] PSA v3 template updated with the three tier-specific Schedule A clauses (`legal_heck_aurelio` owns)
- [ ] Geofence config: TN, CA, AZ, FL allowed; others blocked at signup until per-state disclosure is drafted
- [ ] PostHog wired for funnel tracking (Browser -> Verified -> Inner Circle conversion)
- [ ] Slack `#broker-pipeline` getting drop cards via `branded_slack`
- [ ] `branded_mailer` test send to a non-real address confirms VIP / nurture / bulk routing

---

## Cost ledger (final, for the record)

| Item | One-time | Monthly |
|---|---|---|
| Domain | $0 (already own everlightventures.io) | $0 |
| Cloudflare Pages hosting | $0 | $0 (free tier) |
| Supabase | $0 | $0 (free tier covers 500MB / 500MAU) |
| Stripe acct | $0 | $0 (2.9% + $0.30 on real txns only) |
| PostHog | $0 | $0 (free tier 1M events) |
| Resend | $0 | $0 (3,000/mo free tier) |
| Mid South Title account | $0 | $0 (existing relationship, per-deal fees only) |
| Hive labor | $0 (already paying for Claude) | $0 |
| **Total to launch v1** | **$0** | **$0 fixed, % only on revenue** |

When revenue justifies, upgrade: Supabase Pro ($25/mo) when MAU > 500, Stripe stays variable, PostHog stays free until 1M events.

---

## Risk / kill-switch triggers

Stop and reassess if any of these hit during the first 30 days:

1. TN AG inquiry or BBB complaint about the Lock Fee structure -> pause `/verify` and `/inner-circle` upgrades, keep Browser only
2. Stripe risk-team flagging account -> immediately pull Stripe live keys, fall back to test mode + manual EMD wires
3. Chris signals discomfort with the ANCHOR badge or public Inner Circle visibility -> hide his account presence from pulse feed
4. Conversion data shows <2% Browser -> Verified click-through after 200 signups -> rework Verified value prop before adding paid traffic
5. Any locked buyer disputes a charge with their card issuer -> immediate refund + escalate to `legal_imani_calder` for civil-action posture review
