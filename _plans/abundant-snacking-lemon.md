# Plan: Triple Upgrade -- SSH Reliability + Human Posting + Dashboard

## Context
Three critical problems identified after the user's 5-hour nap test:
1. **SSH to Micro is flaky** -- God Mode reads 9999s stale ticks every cycle because SSH times out. This makes the bot appear dead when it's actually live ($459 equity, WS at 5s fresh). Root cause of ALL blind spots today.
2. **Posts are robotic** -- Work engine drops "[WORK COMPLETE] Pipeline: 436,20,0,0,0" like a log file. Real people say something human first, then hand you the report. Dual-post (Canvas + HTML) exists but isn't wired into any system.
3. **Dashboard is isolated** -- :8502 Streamlit dashboard on Micro has beautiful charts (equity curves, trade grades, Wolf's Monologue) but its AI chat uses dead Anthropic key and it doesn't report to Slack or generate shareable docs.

---

## Phase 1: Fix SSH to Micro (30 min, do FIRST)

**Problem:** Every SSH from E5 to Micro (10.0.0.22) opens a new connection that takes 3-5s and sometimes times out. God Mode, work engine, and bot checks all fail silently.

**Fix A (immediate, 3 lines):** SSH connection pooling via config
```
# Add to /home/opc/.ssh/config on Oracle E5
Host micro
    HostName 10.0.0.22
    User opc
    IdentityFile /home/opc/.ssh/oracle_key.pem
    StrictHostKeyChecking no
    ControlMaster auto
    ControlPath /tmp/ssh-micro-%r@%h:%p
    ControlPersist 600
```
One connect, reused for 10 minutes. All subsequent commands are instant.

**Fix B (permanent):** autossh systemd service
```ini
# /etc/systemd/system/ssh-tunnel-micro.service
[Service]
ExecStart=/usr/bin/autossh -M 0 -N -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -L 2222:localhost:22 -i /home/opc/.ssh/oracle_key.pem opc@10.0.0.22
Restart=always
```
Then God Mode connects to `localhost:2222` -- instant, never times out.

**Fix C (read optimization):** God Mode reads E5's local state.json copy FIRST (synced every 2 min by existing cron). Only SSHes to Micro for actions (restart, parameter change). Reading = local file. Fixing = SSH.

**Files to modify:**
- Create: `/home/opc/.ssh/config` on Oracle E5 (SSH pooling)
- Create: `/etc/systemd/system/ssh-tunnel-micro.service` on E5 (autossh)
- Modify: `/home/opc/hive_god_mode.py` -- read local state.json first, SSH only for actions

**Verification:** Run `time ssh micro hostname` -- should be <0.1s after first connect.

---

## Phase 2: Human Posting + Dual Format (2-3 hours)

**Problem:** Every system posts raw text. Rex says "[WORK COMPLETE] Pipeline: 436,20,0,0,0" instead of walking up to your desk like a person.

**What it should look like:**
> *Rex Blackwell:* Morning partner. Just ran the numbers on those STL leads -- couple of 'em look real promising. That 63113 zip code is heating up.
> [Canvas: STL Pipeline Report] [HTML: Full luxury report]

**Approach:** Create a `hive_smart_post.py` module that replaces ALL raw `post()` calls across every system. It:
1. Takes raw data + agent name + channel
2. Uses AI (Gemini free for short, GPT-4o-mini for medium) to add a human intro in the agent's voice
3. If content > 3 lines: generates Canvas + HTML luxury report via `hive_dual_post.py`
4. Posts the human intro + links to Slack
5. Short updates (1-2 lines): just raw text with agent name, no doc needed

**Files to create:**
- `hive_smart_post.py` on Oracle -- the universal posting module

**Files to modify (replace raw post calls):**
- `hive_work_engine.py` -- 2 post() calls (line 461, 476)
- `hive_shift_system.py` -- 12+ post() calls
- `hive_god_mode.py` -- 3 post_to_slack() calls (line 995, 1029, 1038)
- `hive_ambient.py` -- 4 post() calls

**Key design:** The smart_post function signature:
```python
def smart_post(channel, agent_name, agent_style, raw_data, event_type="update"):
    """
    Post like a human, not a machine.

    - Short updates (1-2 data points): human intro + data in one message
    - Medium reports (3-10 lines): human intro + Canvas + HTML link
    - Long documents (10+ lines): human intro + Canvas + HTML link + Blinko log
    """
```

**Verification:** Run work engine and check that Rex's pipeline report sounds like Rex talking, not a log file. Check that reports over 3 lines generate both Canvas and HTML links.

---

## Phase 3: Dashboard Upgrade (2-3 hours)

**Problem:** The :8502 Streamlit dashboard is beautiful but:
- AI chat uses dead Anthropic key (no credits)
- Reads local state.json which may diverge from Micro production
- Doesn't share reports to Slack
- Isolated from the Hive

**What the dashboard already has (from exploration):**
- 5 tabs: Terminal, Portfolio, Signals, Ledger, System
- Wolf's Monologue (decision feed), equity curves, trade quality grades (A-D)
- Sharpe/Sortino/max drawdown calculations
- Trade history with fills, incidents, cash movements
- Bot DNA config viewer, file age monitoring

**File:** `/mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/xlm_bot/dashboard.py` (487KB)

**Fix A: AI Chat to OpenAI**
- Find the Claude Chat section (line 3071-3080) and the `claude_chat_api.py` module
- Switch from Anthropic API to OpenAI (same fix as Slack agent)
- Pass recent trade context to chat so it can answer "why did you take that trade?"

**Fix B: Fresh data**
- Dashboard on Micro reads local files -- these ARE the production files, so data should be fresh
- Add a "last refreshed" indicator to the top bar
- If on E5, read from Micro via SSH tunnel (Phase 1 fix)

**Fix C: Share to Slack button**
- Add "Share Report" button that snapshots current metrics
- Calls gdocs_bridge to create Google Doc
- Posts link to #xlm-trading via Slack API
- Rex Thornton's name on the report

**Verification:** Open :8502, use AI chat, verify it responds. Click Share Report, verify it posts to #xlm-trading.

---

## Execution Order

| Phase | Task | Effort | Dependencies |
|-------|------|--------|-------------|
| 1A | SSH config pooling on E5 | 10 min | None |
| 1B | autossh systemd service | 15 min | None |
| 1C | God Mode read local first | 15 min | 1A |
| 2 | Smart posting module + wire into all systems | 2-3h | None |
| 3A | Dashboard AI chat to OpenAI | 30 min | None |
| 3B | Dashboard share to Slack | 1h | 1A (for fresh data) |

**Phases 1, 2, 3 can all run in parallel.** Total: 3-4 hours.

---

## Key Files

| File | Location | Change |
|------|----------|--------|
| `.ssh/config` | Oracle E5 `/home/opc/.ssh/config` | CREATE -- SSH pooling |
| `ssh-tunnel-micro.service` | Oracle E5 `/etc/systemd/system/` | CREATE -- autossh |
| `hive_god_mode.py` | Oracle E5 `/home/opc/` | MODIFY -- read local state first |
| `hive_smart_post.py` | Oracle E5 `/home/opc/` | CREATE -- universal human posting |
| `hive_work_engine.py` | Oracle E5 `/home/opc/` | MODIFY -- use smart_post |
| `hive_shift_system.py` | Oracle E5 `/home/opc/` | MODIFY -- use smart_post |
| `hive_god_mode.py` | Oracle E5 `/home/opc/` | MODIFY -- use smart_post |
| `hive_ambient.py` | Oracle E5 `/home/opc/` | MODIFY -- use smart_post |
| `dashboard.py` | Micro `/home/opc/xlm-bot/` | MODIFY -- AI chat + share button |
| `hive_dual_post.py` | Oracle E5 `/home/opc/` | Already exists, used by smart_post |
| `hive_html_report.py` | Oracle E5 `/home/opc/` | Already exists, used by smart_post |

## Verification
1. `time ssh micro hostname` -- <0.1s (SSH pooling works)
2. God Mode cycle shows real tick age (5-10s, not 9999)
3. Work engine Rex post sounds like a person talking
4. Reports over 3 lines have Canvas + HTML link
5. Dashboard AI chat responds when you type
6. Dashboard "Share Report" posts to #xlm-trading
