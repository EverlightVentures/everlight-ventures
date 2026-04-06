# Gear Engine -- Quick Setup (2 minutes)

## Step 1: Create Tables (paste once in Supabase)

1. Open: https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl/sql/new
2. Paste the ENTIRE contents of this file: `supabase/migrations/20260318_gear_engine_tables.sql`
3. Click "Run"
4. Done -- tables created + 8 products seeded

## Step 2: Add Service Key to .env

1. Go to: https://supabase.com/dashboard/project/jdqqmsmwmbsnlnstyavl/settings/api
2. Copy the `service_role` key (under "Project API keys")
3. Add to `03_AUTOMATION_CORE/03_Credentials/.env`:
   ```
   SUPABASE_SERVICE_KEY=eyJ...your_service_key...
   ```

## Step 3: Refresh Access Token

1. Go to: https://supabase.com/dashboard/account/tokens
2. Generate new token
3. Update in `.env`:
   ```
   SUPABASE_ACCESS_TOKEN=sbp_new_token_here
   ```

## Step 4: Test It

```bash
python3 03_AUTOMATION_CORE/01_Scripts/daily_drop_orchestrator.py full
```

## Step 5: Build Lovable Frontend

Paste `LOVABLE_GEAR_DROP_PROMPT.md` into Lovable to build the /him-loadout widget.

## Already Done (by Claude)
- Migration SQL with tables + seed data
- Cron job: 6:05 PM PT daily (01:05 UTC)
- Orchestrator pipeline: fetch -> rank -> validate -> publish -> log
- Fallback queue: 5 products as safety net
- Scoring: Rating 50% + Velocity 30% + Commission 20%
- Logging: _logs/gear_drops/
