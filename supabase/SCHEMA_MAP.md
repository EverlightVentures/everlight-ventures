# Supabase Schema Map
> Last updated: 2026-03-19

## Project
- Ref: jdqqmsmwmbsnlnstyavl
- Region: East US (N. Virginia)

## Migrations (apply in order)

| File | Owner App | What it does |
|------|-----------|--------------|
| 20260313_broker_os_setup.sql | broker_ops | Broker deals, leads, commissions tables |
| 20260315_xlm_bot_schema.sql | xlm_bot | Base XLM bot tables (metrics, trades, state) |
| 20260315212500_xlm_bot_report_history.sql | xlm_bot | Report history tracking |
| 20260315213200_xlm_bot_liquidation_feed_columns.sql | xlm_bot | Liquidation feed columns |
| 20260316030000_market_intel_service.sql | xlm_bot | Market intel service tables |
| 20260318_gear_engine_tables.sql | gear_engine | Daily Drop Engine catalog + queue |
| 20260319_fix_xlm_write_policies.sql | xlm_bot | RLS policy fixes for bot writes |
| 20260319_hive_mind_tables.sql | hive_dashboard | Hive sessions, agent reports, agent status, user profiles |

## Additional SQL (not timestamped)

| File | Location | Purpose |
|------|----------|---------|
| business_os_schema.sql | supabase/sql/ | Business OS dashboard tables |

## Edge Functions

| Function | Purpose | Called By |
|----------|---------|----------|
| blackjack-api | Game state CRUD (hit, stand, deal, player state) | Lovable blackjack |
| create-checkout | Stripe checkout session creation | Lovable shop |
| dealer-speak | AI dealer chat responses | Lovable blackjack |
| download-ebook | Signed URL for purchased ebooks | Lovable publishing |
| recovery-sweep | Recover failed purchases | Cron / manual |
| send-purchase-email | Email receipt after purchase | stripe-webhook |
| strategy-coach | AI strategy advice for blackjack | Lovable blackjack |
| stripe-webhook | Stripe event handler (payment, subscription) | Stripe |
| verify-arcade-purchase | Verify arcade item purchases | Lovable arcade shop |
| verify-checkout-session | Verify Stripe checkout completion | Lovable / Django |
| verify-ebook-purchase | Verify ebook purchases | Lovable publishing |
| verify-gem-purchase | Verify gem pack purchases | Lovable / Django |

## Table Ownership (which app is authoritative)

| Table Pattern | Owner | Writers |
|---------------|-------|---------|
| player_accounts, purchases, vip_* | blackjack-api edge fn | Lovable, Django (via edge fn) |
| xlm_bot_*, watchtower_* | xlm_bot | Oracle VM bot |
| broker_*, deals, commissions | broker_ops | Django broker_ops |
| business_os_* | business_os | Django business_os |
| hive_sessions, hive_agent_* | hive_dashboard | Django hive app |
| user_profiles | auth system | Supabase auth triggers |
| gear_engine_* | gear_engine | Django / Lovable |

## Data Flow Summary

```
Django 8504 --writes--> Supabase <--reads-- Lovable (everlightventures.io)
Oracle VM   --writes--> Supabase <--reads-- Lovable /dashboard (watchtower)
```
