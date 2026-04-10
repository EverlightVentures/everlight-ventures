# Broker OS - Full Autonomy Plan

## Phase 1: Unblock the Pipeline

- **`03_AUTOMATION_CORE/01_Scripts/broker_daily_orchestrator.py`**
  - Add `step_enrich_emails()` -- fetch source_url for @placeholder.io records, scrape for real emails via regex + HN/GitHub user APIs
  - Expand `step_scout_buyers()` -- add Reddit JSON API (r/SaaS, r/smallbusiness, r/entrepreneur, r/startups) + mine HN Ask comment threads for buyer intent
  - Wire new steps into `run_full()`

- **`09_DASHBOARD/hive_dashboard/broker_ops/models.py`**
  - Add `"reddit"`, `"hacker_news"`, `"github"` to `LEAD_SOURCE_CHOICES`
  - Run makemigrations + migrate

- **`09_DASHBOARD/hive_dashboard/broker_ops/services.py`**
  - Lower auto-approve threshold: 75 to 65 in `auto_approve_high_score_matches()`
  - In `run_matching()`, set `status="approved"` inline for scores >= 70

- **`_logs/broker_ops/broker_crontab`** -- rewrite to call orchestrator.py 4x/day (5AM/12PM/6PM/10PM PT), install with crontab

- **One-time cleanup** -- expire BrokerMatch records where lead email contains @placeholder.io

## Phase 2: Close the Loop

- **`03_AUTOMATION_CORE/01_Scripts/broker_daily_orchestrator.py`**
  - Add `step_check_replies()` -- scan Gmail for replies to outreach subjects, classify (interested/unsubscribe/bounce), auto-advance deals

## Phase 3: Smarter Matching (after flow works)

- **`09_DASHBOARD/hive_dashboard/broker_ops/services.py`**
  - Add `score_match_semantic()` using Claude Haiku for pairs scoring >= 30 on rules. Blend 40% rule + 60% semantic. ~$1.50-3/run.

## Verify
```bash
cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts && python3 broker_daily_orchestrator.py status
```
