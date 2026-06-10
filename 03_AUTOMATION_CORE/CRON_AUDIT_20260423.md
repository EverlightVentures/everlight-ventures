# Cron Audit -- 2026-04-23

Classification of every crontab line. Legend:
- **KEEP (time)**: truly time-based (heartbeat, daily cadence) -- stays as cron.
- **KEEP (hybrid)**: now event-driven for new items, but cron continues as a backlog-sweep safety net.
- **REPLACE (next)**: will convert to trigger in the next session; leaving as-is tonight so nothing breaks.
- **KILL**: dead / superseded.

## Keep as cron (time-based)

| Schedule | Job | Why |
|----------|-----|-----|
| `0 12 * * *` | `broker_daily_orchestrator.py full` | daily broker morning run |
| `0 19 * * *` | `broker_daily_orchestrator.py outreach` | daily 12 PM PT outreach window |
| `0 1  * * *` | `broker_daily_orchestrator.py scout` | nightly scout |
| `0 5  * * *` | `broker_daily_orchestrator.py match` | daily match |
| `*/30 8-23 *`| `reddit_monitor.py scan` | scheduled scrape (Reddit has no webhook) |
| `5 1  * * *` | `daily_drop_orchestrator.py full` | daily gear drop |
| `0 15 * * *` | `wholesale_hive_pipeline.py scout qualify match pitch` | feeds ATTOM bulk |
| `0 20 * * *` | `wholesale_hive_pipeline.py outreach` | outreach batch window |
| `0 0  * * *` | `wholesale_hive_pipeline.py followup report` | end-of-day close |
| `0 16 * * 0` | `rex_lead_recycler.py` | weekly dead-lead recycle |
| `0 15 * * *` | `ceo_daily_brief.py` | 7 AM PT brief |
| `0 *  * * *` | `hourly_status_pulse.py` | heartbeat |
| `30 11 * * *`| `blinko_log_ingest.sh` | daily Blinko ingest |
| `*/5  * * * *`| `hive_health_monitor.py --fix` | heartbeat |
| `*/2  * * * *`| n8n tunnel curl keepalive | heartbeat |
| `*/5  * * * *`| `blinko_lite.py` watchdog | heartbeat |
| `*/10 * * * *`| `deploy_to_oracle.sh` | deploy sync |
| `*/5  * * * *`| `mcp_tunnel.sh` | MCP tunnel supervisor |
| `*/5  * * * *`| `mcp_broker_os_local.sh` | MCP broker-os supervisor |
| `15 *  * * *`| `mcp_fleet_health.sh` | hourly MCP health |
| `*/3  * * * *`| `hive_dispatcher_supervisor.sh` | dispatcher supervisor (new) |

## Keep as hybrid (cron + new event trigger)

| Schedule | Job | New behavior |
|----------|-----|--------------|
| `0 *  * * *` | `rex_belfort_sequence.py` | Cron continues as **backlog sweep**. NEW leads inserted by hunter / Supabase webhook trigger the dispatcher -> `rex_belfort_sequence.py --lead-id=X` (event-mode, single-lead). |

## Replace with trigger next session

| Schedule | Job | Replacement |
|----------|-----|-------------|
| `*/2  * * * *` | `rex_negotiator.py` | Gmail push notification via IMAP IDLE daemon (`rex_imap_idle.py`) -> dispatcher `/event/wholesale_reply`. Polling every 2 min goes away. |

## Kill (redundant / dead)

None identified tonight. Test-email scripts (`hive_email_test.py`, `hive_email_live_test.py`) were never cron-scheduled -- they just got a `HIVE_EMAIL_TEST_ENABLED=1` gate so they cannot fire accidentally.

## Net effect

- **Before:** 21 cron lines, wholesale "running" but processing 0 leads.
- **Now:** same 21 lines + 1 new supervisor = 22. Dispatcher catches each new lead the instant the hunter writes it. Hourly Belfort cron stays as a safety net for anything missed.
- **Next session:** convert `rex_negotiator` polling to Gmail IMAP IDLE triggers, drop that cron entirely.
