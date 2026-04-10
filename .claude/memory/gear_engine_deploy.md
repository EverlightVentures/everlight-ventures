---
name: Gear Engine and deployment workflow
description: Daily Drop system state, Supabase issues, and Lovable deployment via GitHub
type: project
---

## Gear Engine (Daily Drop) -- 2026-03-19
- Supabase tables: daily_drops + gear_catalog (NEED CREATING via supabase/PASTE_THIS_IN_SUPABASE.sql)
- Orchestrator: 03_AUTOMATION_CORE/01_Scripts/daily_drop_orchestrator.py
- Config: 01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/gear_engine/
- Cron: 6:05 PM PT daily (01:05 UTC)
- Frontend: DailyDrop.tsx pushed to GitHub repo EverlightVentures/everlightventures

**Why:** User wants 1+ new product/day autonomously on everlightventures.io from highest-rated items.

## CRITICAL: Supabase Access Token EXPIRED
- Token sbp_48538dbc... returns Unauthorized on all management API calls
- XLM bot Supabase pushes ALL FAILING (RLS 42501 on every table -- no write policies)
- Fix: paste supabase/PASTE_THIS_IN_SUPABASE.sql + add SUPABASE_SERVICE_ROLE_KEY to .env + Oracle runtime.env

## Lovable Site Repo
- GitHub: EverlightVentures/everlightventures
- Local clone: /tmp/lovable-site (PAT in remote URL)
- Deploy: push to GitHub -> user clicks Publish in Lovable
- NEVER suggest Lovable prompts

**How to apply:** Always push frontend changes to the GitHub repo, never create prompt files.
