---
name: hermes_browser_outreach
description: Self-improving browser-harness agent for outreach lead-scraping. Hostinger VPS + browser-use cloud, gated through DNC + state-gates, integrates with Piper/Hammer pipeline.
---

When to use:
- Scrape leads / find sellers / find buyers on a non-API site (Craigslist, FB Marketplace, county records, LinkedIn, Zillow gated pages).
- Piper or Hammer needs to send outbound to a list that does not yet exist in `leads_db`.
- "Do this on the browser like a human" -- multi-step nav, login, click, extract.
- DNS-blocked or anti-bot site that 403s our Oracle IP.
- Repeating outreach task that should compound (skill written once, reused forever).

Procedure (every dispatch):
1. Marcus dispatches: Forge owns the run, Piper owns copy, Cipher gates send, Justine clears DNC + state.
2. Hermes (on Hostinger VPS) opens browser-use cloud session, hits target site, extracts rows -> `/tmp/hermes_leads_<run>.json`.
3. SCP/rsync JSON to Oracle E5 -> `dnc_filter.assert_safe_recipient()` + `state_gate.allow(state, channel)` per row.
4. Survivors upsert into Supabase `leads_db` with `source='hermes'` + provenance JSON.
5. Piper drafts via `branded_mailer.send_branded_email(budget_category='bulk')` OR Hammer queues SMS via `branded_sms`. NEVER raw `api.resend.com`.
6. Hermes contributes a `domain_skills/<site>.md` artifact back to repo so next run is faster + cheaper.
7. Log run via `hive_logger.current_run()`; post `branded_slack` card to `#ft-hunters` with HiveArtifact link.

VPS sizing + cost:
- Hostinger **KVM 2** (2 vCPU / 8 GB RAM / 100 GB NVMe), Germany region, Hermes pre-built template.
- 24-month plan = $7.99/mo with code DAVID (10% off) -> ~$192 upfront.
- Adequate for headless Chromium + 3-5 parallel skills.
- Pair with browser-use cloud free tier first 30 days; only graduate to local Chromium if data-center IP gets blocked.

Integration points:
- `Piper` (`.claude/agents/31_outreach_agent.md`) -- consumes Hermes JSON, calls `branded_mailer`.
- `Hammer` (`.claude/agents/32_deal_closer.md`) -- 3-day follow-up cadence reads same `leads_db.source='hermes'`.
- `Resend` -- only via `branded_mailer` + `resend_budget` (3000/mo cap, 25% VIP reserve, owner-block guard).
- `Supabase` -- `leads_db` + `hive_artifacts` + new `hermes_runs` table (run_id, site, rows_in, rows_kept, dnc_blocked, ts).
- `Blinko` -- tag `#hive/hermes #hive/skill-forge` on every contributed domain skill.
- `branded_slack` -- category `report` to `#ft-hunters`, alerts to `#hive-alerts`.

Done criterion (revenue impact):
- 3+ DNC-clean qualified leads/day from Hermes, attributable to a closed wholesale deal within 30 days.
- First $10k+ commission tagged `source=hermes` in Supabase = skill graduates from trial to permanent fire-team member.

Quick wins (today, $0, no VPS yet):
1. Create `domain_skills/` subfolder. When VPS ships, scp existing folder up so Hermes inherits day-1 context (Cleveland zip codes, distress keywords, our state-gate rules).
2. DNC + state-gate dry run on existing scraped lists. Whatever dies in dry run would have killed Hermes runs too.
3. Write `hermes_runs` Supabase migration today + create `#ft-hermes` Slack channel. Day-1 ready when VPS lights up.

Source: 05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/02_AI_Agents_and_Swarms/hermes_agent_100k_github_stars.txt + TODO_AGENTS.md WO1.
Owner: Forge + Piper + Hammer + Cipher.
