# Execution Loop: Remote Triggers + Computer Use + Hive Broker Pipeline

## Context

Everlight Ventures has 436 broker leads, 4,872 matches, and **0 deals closed**. The pipeline (scout, match, draft, send) works -- but the execution loop is broken: Slack webhooks died March 23, reply checks only run 4x/day, and no way to dispatch from phone on-demand. This plan wires everything into an autonomous deal-closing loop where CEO only closes on phone.

---

## Phase 1.5: Fix Slack (DO FIRST -- everything depends on this)

**Problem:** `broker_daily_orchestrator.py` uses `SLACK_WEBHOOK_URL` in 6 places. Webhooks died March 23. All alerts silently fail.

**Fix:** Replace webhook with `chat.postMessage` using bot tokens (pattern from `hive_watchdog.py`).

**File:** `03_AUTOMATION_CORE/01_Scripts/broker_daily_orchestrator.py`
- Add `_slack_post_bot(text, channel)` helper using `SLACK_BOT_TOKEN` + `urllib.request`
- Replace all `SLACK_WEBHOOK_URL` calls:
  - `_slack_notify_reply()` (~line 1536) -> #ft-hunters (C0AMVEWLT9D)
  - `_slack_raw_fallback()` (~line 1705) -> #war-room (C0ANAU30UQ2)
  - `step_status()` (~line 1838) -> #war-room (C0ANAU30UQ2)
- Hot leads "interested" -> #war-room with fire emoji

**File:** `03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh`
- Fix `curl $SLACK_WH` at ~line 196

**Verify:** `python3 broker_daily_orchestrator.py status` -> message in Slack

---

## Phase 1: Remote Triggers ($0, immediate)

Create 6 triggers via `RemoteTrigger action: "create"`:

| Trigger | What It Does |
|---------|-------------|
| `check-bot` | SSH to Oracle, systemctl status xlm-bot, last trade + P&L |
| `run-broker-pipeline` | Full scout+match+outreach cycle |
| `send-outreach` | Send pending emails |
| `check-replies` | Scan inbox + escalate hot leads |
| `morning-brief` | CEO brief on demand |
| `audit-services` | Health check all services |

No files modified -- triggers are API-side. Scripts already exist on Oracle.

---

## Phase 3A: Reply Check Every 2 Hours

Add cron on Oracle:
```
0 */2 * * * cd /home/opc && python3 broker_daily_orchestrator.py replies >> /tmp/broker_replies.log 2>&1
```

**File:** `03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh` -- add `install_broker_reply_cron()`

---

## Phase 3B: Outreach 2x/Day

Add cron on Oracle (10 AM + 4 PM PT):
```
0 17,0 * * * cd /home/opc && python3 broker_daily_orchestrator.py outreach >> /tmp/broker_outreach.log 2>&1
```

---

## Phase 2: Computer Use Container (~$10-20/mo API)

Deploy Anthropic computer-use Docker container on Oracle E5 (ARM64).

**New files:**
- `06_DEVELOPMENT/everlight_os/computer_use/docker-compose.yml` -- container on `everlight` network, ports 8501 + 5900, 2GB memory limit
- `06_DEVELOPMENT/everlight_os/computer_use/Dockerfile` -- ARM64 build if needed (Xvfb, Mutter, Firefox, anthropic SDK)
- `03_AUTOMATION_CORE/01_Scripts/computer_use_task.py` -- task submission wrapper

**Note:** ARM64 needs either source build or `--platform linux/amd64` QEMU emulation.

---

## Full Execution Loop (When Complete)

```
Scout (4x/day) -> Match -> Draft -> Send (2x/day + trigger)
                                        |
                              Check replies (every 2h + trigger)
                                        |
                              Classify (interested/bounce/unsub)
                                        |
                    [interested] -> Deal + Slack #war-room alert
                                        |
                              CEO closes on phone
```

---

## Implementation Order

1. **Phase 1.5**: Fix Slack in orchestrator + deploy script (TODAY)
2. **Phase 1**: Create 6 Remote Triggers (TODAY)
3. **Phase 3A**: Reply cron every 2h (TODAY)
4. **Phase 3B**: Outreach cron 2x/day (TODAY)
5. **Phase 2**: Computer Use container (NEXT WEEK)
6. **Phase 3D**: County recorder scanner (AFTER Phase 2)

Steps 1-4 ship today. Steps 5-6 ship next week.

---

## Files Modified

| File | Change |
|------|--------|
| `03_AUTOMATION_CORE/01_Scripts/broker_daily_orchestrator.py` | Replace webhook with bot token (6 sites) |
| `03_AUTOMATION_CORE/01_Scripts/deploy_to_oracle.sh` | Fix Slack, add broker cron installer |
| `06_DEVELOPMENT/everlight_os/computer_use/docker-compose.yml` | NEW |
| `06_DEVELOPMENT/everlight_os/computer_use/Dockerfile` | NEW (if ARM64 build) |
| `03_AUTOMATION_CORE/01_Scripts/computer_use_task.py` | NEW |

---

## Verification

| Test | Expected |
|------|----------|
| `broker_daily_orchestrator.py status` | Slack message in #war-room |
| `RemoteTrigger action: "list"` | 6 triggers |
| `RemoteTrigger action: "run" check-replies` | Reply scan results |
| Oracle `crontab -l` | Reply 2h + outreach 2x/day |
| `docker ps` on Oracle | computer-use container |
| Send test email to inbox | Slack alert within 2 hours |

---

## Risk Mitigation

- All changes additive -- existing functions stay, just route through new helper
- Computer Use capped at 2GB RAM (Oracle has ~6-8GB free)
- Each phase independent -- rollback any one file/cron without breaking others
- New `_slack_post_bot()` logs errors instead of silent drops
