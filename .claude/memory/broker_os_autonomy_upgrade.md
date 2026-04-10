---
name: Broker OS autonomy upgrade (2026-03-13)
description: Full autonomous pipeline built - Reddit monitor, email enrichment, reply detection, lowered thresholds, cron 4x daily
type: project
---

Major Broker OS upgrade on 2026-03-13 to make it fully autonomous.

**Changes made:**
- Added Reddit buyer scouting (r/SaaS, r/smallbusiness, r/entrepreneur, r/startups, r/selfhosted)
- Added HN comment mining for buyer signals (not just post titles)
- Added step_enrich_emails() to replace @placeholder.io with real contacts
- Lowered auto-approve threshold from 75 to 65, inline approve >= 70
- Created reddit_monitor.py - scans 6 subreddits every 30 min, drafts replies, alerts Slack
- Added step_check_replies() via IMAP for auto-classifying seller/buyer responses
- Expired 1,837 placeholder matches (cleanup)
- Added reddit/hacker_news/github to LEAD_SOURCE_CHOICES + migration
- Rewrote crontab: 4x daily orchestrator + Reddit monitor every 30 min
- Added replies subcommand to orchestrator

**Key files:**
- 03_AUTOMATION_CORE/01_Scripts/broker_daily_orchestrator.py (now ~1700 lines)
- 03_AUTOMATION_CORE/01_Scripts/reddit_monitor.py (new, ~450 lines)
- _logs/broker_ops/broker_crontab (rewritten)
- _logs/broker_ops/reddit_monitor.db (SQLite for dedup)

**Pending user action:** Generate Gmail App Password at myaccount.google.com/apppasswords, add IMAP_PASS to .env

**Why:** User wants Broker OS to be "Tinder for business" - fully autonomous SaaS matchmaking with zero human intervention except posting Reddit replies and confirming money.
