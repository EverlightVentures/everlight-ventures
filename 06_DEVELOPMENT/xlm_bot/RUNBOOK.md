# XLM Bot Operational Runbook

Last updated: 2026-02-27

This runbook is written for a tired operator at 3 AM. Follow the steps in order.
Skip nothing. When in doubt, stop the bot -- it will not lose money if it is off.


## Infrastructure Overview

| What             | Where                                      |
|------------------|--------------------------------------------|
| Oracle VM        | 163.192.19.196, user `opc`, us-sanjose-1   |
| Instance type    | VM.Standard.E2.1.Micro (1 OCPU, 1GB RAM)  |
| Usable RAM       | ~503 MB + 1 GB swap (swappiness=10)        |
| Bot directory    | `/home/opc/xlm-bot/`                       |
| Python venv      | `/home/opc/xlm-bot/venv/`                  |
| Config           | `/home/opc/xlm-bot/config.yaml`            |
| API credentials  | `/home/opc/xlm-bot/secrets/config.json`    |
| State file       | `/home/opc/xlm-bot/data/state.json`        |
| Heartbeat        | `/home/opc/xlm-bot/data/.heartbeat`        |
| Trade log        | `/home/opc/xlm-bot/logs/trades.csv`        |
| Instance OCID    | `ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq` |
| OCI CLI config   | `/root/.oci/config` (on phone)             |

### Three Services

| Service          | What it does                            | Priority |
|------------------|-----------------------------------------|----------|
| `xlm-bot`        | Runs `run-bot.sh` -- loops main.py      | HIGHEST  |
| `xlm-dashboard`  | Streamlit on port 8502                  | LOW      |
| `xlm-ws`         | WebSocket feed (`live_ws.py`)           | MEDIUM   |

The bot is NOT a long-running process. Each `main.py` invocation is one 3-5
second cycle. The `run-bot.sh` wrapper loops it with 5s sleep when in a trade
or 30s sleep when idle.

### Cron Jobs (on Oracle VM)

| Schedule              | Script              | Purpose                                 |
|-----------------------|---------------------|-----------------------------------------|
| Every 5 min (1,6,...) | `memory_guard.sh`   | RAM monitor, cache clear, CPU keepalive |
| Every 5 min (2,7,...) | `watchdog.sh`       | Zombie detection, service restart       |
| Hourly (minute 0)     | `log_rotate.sh`     | Trim logs, prevent disk fill            |

### Phone-Side Watchdog

`oracle_watchdog.sh` runs every 60 seconds on your phone. It SSHes into Oracle,
checks the bot, and auto-reboots the instance via OCI CLI if it has been down
more than 10 minutes.

### Key File Locations (Oracle VM)

```
~/xlm-bot/
  main.py                -- bot logic (do not edit live)
  config.yaml            -- configuration (hot-reloaded every cycle)
  run-bot.sh             -- loop wrapper for main.py
  run-dashboard.sh       -- loop wrapper for streamlit
  run-ws.sh              -- loop wrapper for WS feed
  secrets/config.json    -- Coinbase API credentials
  data/state.json        -- live bot state (atomic writes only)
  data/.heartbeat        -- Unix timestamp, updated every cycle
  data/.circuit_breaker  -- if present, all automation halts
  logs/trades.csv        -- realized trade ledger (NEVER delete)
  logs/decisions.jsonl   -- every bot decision with reasons
  logs/incidents.jsonl   -- reconciliation + risk events
  logs/watchdog.log      -- watchdog + memory guard log
  logs/xpb_service.log   -- systemd bot stdout/stderr
  logs/xlb_console.log   -- main.py stderr
```


---


## SOP 1: Daily Checklist

Do this every morning. Takes about 2 minutes.

1. **Check Slack channel.** Look for any alerts from overnight -- bot restarts,
   memory kills, watchdog triggers, or trade entries/exits.

2. **Check the dashboard.** Open `http://163.192.19.196:8502` in your browser.
   Confirm it loads and shows recent data (not stale from hours ago).

3. **Check today's PnL.** Dashboard shows `exchange_pnl_today_usd` -- this is
   the real number from Coinbase, not the bot's internal math.

4. **Quick SSH health check:**
   ```
   ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196
   sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws
   free -m
   df -h /home
   cat ~/xlm-bot/data/state.json | python3 -m json.tool | head -20
   ```
   You want: all three services "active", RAM available > 50 MB, disk < 80%,
   and state.json modified within the last minute.

5. **Check heartbeat freshness:**
   ```
   echo $(( $(date +%s) - $(stat -c '%Y' ~/xlm-bot/data/.heartbeat) )) seconds ago
   ```
   Should be under 60 seconds. If over 300 seconds, the bot is stuck.

6. **Review trades.csv** for anything weird -- phantom trades, duplicate entries,
   missing exit prices:
   ```
   tail -5 ~/xlm-bot/logs/trades.csv
   ```

7. **Margin window awareness.** If it is after 1:00 PM PT (4:00 PM ET),
   overnight margin is in effect. The bot needs ~$432/contract instead of ~$207.
   If your equity is under $432, the bot will not open new positions until
   5:00 AM PT tomorrow. This is correct behavior -- do not override it.


---


## SOP 2: Bot Not Trading

The bot is running but has not opened a position in a while.

1. **Is the bot actually cycling?**
   ```
   stat -c '%Y' ~/xlm-bot/data/state.json
   ```
   If this timestamp is more than 2 minutes old, the bot is stuck -- go to SOP 5.

2. **Check the state file for a position:**
   ```
   python3 -c "
   import json
   s = json.load(open('data/state.json'))
   print('Position:', s.get('open_position', 'NONE'))
   print('Mode:', s.get('mode', '?'))
   print('Losses today:', s.get('losses_today', 0))
   "
   ```
   If there is an open position, the bot is managing it. If mode is SAFE_MODE
   or similar, that is why it is not entering.

3. **Check if margin window is blocking:**
   ```
   python3 -c "
   from datetime import datetime
   from zoneinfo import ZoneInfo
   now_et = datetime.now(ZoneInfo('America/New_York'))
   h = now_et.hour
   print(f'ET hour: {h}')
   if 8 <= h < 16:
       print('INTRADAY window -- lower margin, bot can trade')
   else:
       print('OVERNIGHT window -- higher margin required')
   "
   ```

4. **Check daily loss cap:**
   Config says `max_losses_per_day: 5`. If you hit 5 losses, the bot sits out
   the rest of the day. Check decisions log for "max_losses" blocks.

5. **Check the circuit breaker:**
   ```
   ls -la ~/xlm-bot/data/.circuit_breaker 2>/dev/null
   ```
   If this file exists, the bot and watchdog will not trade or restart.
   Remove it to resume: `rm ~/xlm-bot/data/.circuit_breaker`

6. **Check decisions log for rejections:**
   ```
   tail -20 ~/xlm-bot/logs/decisions.jsonl | python3 -m json.tool
   ```
   This shows why signals were rejected -- bad R:R, cooldown active, gate
   failures, etc.

7. **Check candle data freshness:**
   ```
   tail -1 ~/xlm-bot/data/XLM_15m.csv
   ```
   If the latest candle is hours old, the API fetch is failing. Check
   `logs/xlb_console.log` for errors.


---


## SOP 3: Instance Unreachable (SSH Timeout)

You cannot SSH in. The dashboard does not load. Do not panic -- the instance
may just need a reboot.

1. **Wait 2 minutes and try again.** Transient network blips happen.

2. **Check the phone-side watchdog.** If `oracle_watchdog.sh` is running, it
   will detect the outage within 60 seconds and attempt an OCI reboot after
   10 minutes. Check its log:
   ```
   tail -20 /mnt/sdcard/AA_MY_DRIVE/_logs/oracle_watchdog.log
   ```

3. **Force a reboot from your phone:**
   ```
   bash /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/oracle_watchdog.sh --reboot
   ```

4. **Or use OCI CLI directly:**
   ```
   oci compute instance action \
     --instance-id ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq \
     --action RESET
   ```

5. **If OCI CLI is not working, use the web console:**
   - Go to https://cloud.oracle.com
   - Compute -- Instances
   - Click your instance
   - Click "Reboot"
   - Wait 3-5 minutes, then try SSH again

6. **If the instance stays down after reboot:**
   - Check the Oracle Cloud Console for instance state (STOPPED, TERMINATED)
   - Oracle sometimes reclaims free-tier instances for low CPU usage --
     `memory_guard.sh` runs a CPU keepalive to prevent this, but it can
     still happen
   - If TERMINATED, go to SOP 10 (Disaster Recovery)

7. **While the instance is down, your open position is unmanaged.**
   If you have a position open, consider closing it manually through the
   Coinbase app or website. See SOP 6.


---


## SOP 4: High Memory / OOM

The VM has only 503 MB usable RAM. Memory pressure is the most common problem.

### Kill priority (lowest number = kill first)

| Priority | Process         | Typical RAM | How to kill                          |
|----------|-----------------|-------------|--------------------------------------|
| 1 (first)| Dashboard      | 80-150 MB   | `sudo systemctl stop xlm-dashboard`  |
| 2        | WS feed         | 30-60 MB    | `sudo systemctl stop xlm-ws`         |
| 3 (last) | Bot             | 40-80 MB    | DO NOT KILL unless true emergency    |

### Diagnosis

```
free -m
```

If "available" is under 30 MB, you are in trouble.

### Quick fix

```
# Clear page cache (safe, instant)
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# Check what is running
ps aux --sort=-%mem | head -10
```

### If that is not enough

```
# Kill dashboard (biggest consumer, least important)
sudo systemctl stop xlm-dashboard

# Still bad? Kill WS feed
sudo systemctl stop xlm-ws

# Check again
free -m
```

### How the automation handles this

- `memory_guard.sh` runs every 5 minutes and does all of the above automatically
- It writes lockfiles (`/tmp/xlm_memkill_dashboard`, `/tmp/xlm_memkill_ws`) so
  the watchdog does not immediately restart what it just killed
- After 10 minutes, if memory is OK, services auto-restart
- The bot process is protected from the OOM killer (oom_score_adj = -900)

### If the bot itself is using too much memory

This usually means a Python memory leak. Restart it:
```
sudo systemctl restart xlm-bot
```
This is safe -- the bot is stateless between cycles. State lives in `data/state.json`.

### Nuclear option

If nothing works and the machine is completely stuck:
```
sudo reboot
```
All three services are systemd-enabled and will start automatically on boot.


---


## SOP 5: Bot Crash Loop

The bot service is active but main.py keeps crashing and restarting.

1. **Check the service status:**
   ```
   sudo systemctl status xlm-bot --no-pager -l
   ```
   Look for "active (running)" and how many times it has restarted.

2. **Read the recent logs:**
   ```
   tail -100 ~/xlm-bot/logs/xpb_service.log
   tail -50 ~/xlm-bot/logs/xlb_console.log
   ```
   The error traceback will tell you what is wrong.

3. **Common causes and fixes:**

   **Import error / missing module:**
   ```
   cd ~/xlm-bot && source venv/bin/activate && pip install -r requirements.txt
   sudo systemctl restart xlm-bot
   ```

   **Config syntax error (bad YAML):**
   ```
   cd ~/xlm-bot
   python3 -c "import yaml; yaml.safe_load(open('config.yaml')); print('OK')"
   ```
   If this throws an error, your config.yaml has a typo. Fix it, save, and the
   next cycle will pick it up.

   **API credential error (401 / authentication failed):**
   Check `secrets/config.json` exists and is valid JSON:
   ```
   python3 -c "import json; json.load(open('secrets/config.json')); print('OK')"
   ```
   If the keys expired, go to SOP 9.

   **Coinbase API returning errors (429 rate limit, 500 server error):**
   These are transient. The bot will retry next cycle. If persistent, Coinbase
   may be having an outage -- check https://status.coinbase.com

   **State file corruption:**
   ```
   python3 -c "import json; json.load(open('data/state.json')); print('OK')"
   ```
   If corrupted, and you have NO open position on Coinbase:
   ```
   echo '{}' > ~/xlm-bot/data/state.json
   sudo systemctl restart xlm-bot
   ```
   WARNING: Only reset state if you are SURE there is no open position.
   The reconciler will detect exchange-side positions, but resetting state
   while a position is open can cause phantom trades.

4. **If you cannot figure it out, stop the bot and investigate later:**
   ```
   sudo systemctl stop xlm-bot
   ```
   No bot running = no new trades = no new losses. Safe to leave stopped
   while you debug.


---


## SOP 6: Emergency Position Close

You need to close a position RIGHT NOW. Maybe the bot is down, maybe a black
swan event is happening, maybe you just want out.

### Option A: Coinbase app or website (fastest, no SSH needed)

1. Open the Coinbase app on your phone
2. Go to your Futures/Derivatives wallet
3. Find the XLP-20DEC30-CDE position
4. Tap "Close Position"
5. Confirm

Or use the Coinbase website at https://www.coinbase.com/advanced-trade

### Option B: From the Oracle VM via SSH

```
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196
cd ~/xlm-bot && source venv/bin/activate

python3 -c "
from execution.coinbase_advanced import CoinbaseAdvancedClient
import json

creds = json.load(open('secrets/config.json'))
client = CoinbaseAdvancedClient(creds)

# Check current position
pos = client.get_cfm_positions()
print('Open positions:', pos)

# Close it
result = client.close_cfm_position('XLP-20DEC30-CDE')
print('Close result:', result)
"
```

### After emergency close

Update the bot's state so it does not think a position is still open:
```
cd ~/xlm-bot
python3 -c "
import json
from pathlib import Path
p = Path('data/state.json')
s = json.loads(p.read_text())
s.pop('open_position', None)
p.write_text(json.dumps(s, indent=2))
print('Position cleared from state')
"
```

Or just restart the bot -- the reconciler will detect the position is gone:
```
sudo systemctl restart xlm-bot
```


---


## SOP 7: Config Hot Reload

The bot re-reads `config.yaml` every single cycle (every 5-30 seconds). To
change any setting:

1. **Edit the config on the server:**
   ```
   ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196
   nano ~/xlm-bot/config.yaml
   ```

2. **Save and exit.** That is it. The next bot cycle picks up the changes.
   No restart needed.

3. **Verify it took effect** by checking the next decision log entry:
   ```
   tail -5 ~/xlm-bot/logs/decisions.jsonl
   ```

### Common quick changes

| What you want                  | Config key                      | Example value |
|--------------------------------|---------------------------------|---------------|
| Stop trading entirely          | `paper`                         | `true`        |
| Reduce position size           | `position_sizing.min_contracts` | `1`           |
| Widen stops                    | `risk.max_sl_pct`              | `0.04`        |
| Tighten daily loss limit       | `risk.max_losses_per_day`      | `3`           |
| Increase cooldown after losses | `risk.cooldown_minutes`        | `30`          |
| Disable AI executive           | `ai.executive_mode`            | `false`       |

### Important

Do NOT edit `data/state.json` by hand while the bot is running. The bot
overwrites it every cycle. If you need to change state, stop the bot first,
edit, then start.


---


## SOP 8: Full Service Restart

### Restart one service

```
sudo systemctl restart xlm-bot
sudo systemctl restart xlm-dashboard
sudo systemctl restart xlm-ws
```

### Restart all three

```
sudo systemctl restart xlm-bot xlm-dashboard xlm-ws
```

### Stop everything (bot goes offline, no trading)

```
sudo systemctl stop xlm-bot xlm-dashboard xlm-ws
```

### Start everything

```
sudo systemctl start xlm-bot xlm-dashboard xlm-ws
```

### Check status of all three

```
sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws
```
You want to see three lines of "active".

### Full status with recent output

```
sudo systemctl status xlm-bot --no-pager -l
```

### View live logs

```
# Bot logs (most useful)
tail -f ~/xlm-bot/logs/xpb_service.log

# Or via journald
sudo journalctl -u xlm-bot -f --no-pager
```

### After a code deploy

```
sudo systemctl daemon-reload
sudo systemctl restart xlm-bot xlm-dashboard xlm-ws
```


---


## SOP 9: Key Rotation

### Coinbase API keys

1. Go to https://www.coinbase.com/settings/api and create a new API key
   with the same permissions as the old one (trade + view).

2. Download the new credentials.

3. Upload to the server:
   ```
   scp -i ~/.ssh/oracle_key.pem new_config.json \
     opc@163.192.19.196:~/xlm-bot/secrets/config.json
   ```

4. Restart the bot:
   ```
   ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 \
     "sudo systemctl restart xlm-bot"
   ```

5. Verify it works -- check for successful API calls in the logs:
   ```
   tail -20 ~/xlm-bot/logs/xpb_service.log
   ```

6. Revoke the old key in Coinbase settings.

### SSH keys

1. Generate a new key pair on your phone/laptop:
   ```
   ssh-keygen -t ed25519 -f ~/.ssh/oracle_key_new.pem
   ```

2. While you can still SSH in with the old key, add the new public key:
   ```
   ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196
   nano ~/.ssh/authorized_keys
   # Paste the new public key on a new line, save
   ```

3. Test the new key from a second terminal:
   ```
   ssh -i ~/.ssh/oracle_key_new.pem opc@163.192.19.196 "echo works"
   ```

4. Once confirmed, remove the old public key from `~/.ssh/authorized_keys`
   on the server.

5. Update these files on your phone to use the new key path:
   - `oracle_watchdog.sh` (SSH_KEY variable)
   - Any aliases or shortcuts you use for SSH

### Slack webhook

1. Create or update the webhook at https://api.slack.com/apps

2. Update the SLACK_WEBHOOK variable in these files on the server:
   - `~/xlm-bot/memory_guard.sh`
   - `~/xlm-bot/watchdog.sh`
   - `~/xlm-bot/log_rotate.sh`

3. Update on your phone:
   - `oracle_watchdog.sh`

4. Optionally set it in `config.yaml` as `slack_webhook_url`.


---


## SOP 10: Disaster Recovery

The Oracle instance is gone -- terminated, corrupted, or otherwise destroyed.
Here is how to rebuild from scratch.

### What you need

- Your phone with the bot code at `/mnt/sdcard/AA_MY_DRIVE/xlm_bot/`
- Coinbase API credentials (`secrets/config.json` or regenerate on Coinbase)
- OCI CLI configured (at `/root/.oci/config`)
- SSH key pair

### Step 1: Create a new Oracle instance

**Option A -- OCI CLI:**
```
oci compute instance launch \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaacm32hkslhfxorfn7jubhjqjffr4roltyjwjrkfcdkup37o7qt4ca \
  --availability-domain <pick-one> \
  --shape VM.Standard.E2.1.Micro \
  --image-id <oracle-linux-9-image-ocid> \
  --subnet-id <your-subnet-ocid> \
  --ssh-authorized-keys-file ~/.ssh/oracle_key.pem.pub \
  --assign-public-ip true
```

**Option B -- Oracle Cloud Console:**
1. Go to https://cloud.oracle.com
2. Compute -- Instances -- Create Instance
3. Pick Oracle Linux 9, VM.Standard.E2.1.Micro, your VCN/subnet
4. Paste your SSH public key
5. Create

### Step 2: Note the new public IP

Update `oracle_watchdog.sh` on your phone with the new IP address.

### Step 3: Open port 8502 in Oracle security list

1. Oracle Cloud Console -- Networking -- Virtual Cloud Networks
2. Click your VCN -- Security Lists -- Default
3. Add Ingress Rule: Source 0.0.0.0/0, TCP, Destination Port 8502

### Step 4: Deploy the bot

From your phone:
```
cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot
bash deploy-native.sh <NEW-IP> ~/.ssh/oracle_key.pem
```

This script handles everything: installs Python, creates the venv, sets up
swap, creates systemd services, uploads code and secrets, starts all three
services.

### Step 5: Set up cron jobs

SSH into the new instance:
```
ssh -i ~/.ssh/oracle_key.pem opc@<NEW-IP>
crontab -e
```

Add these lines:
```
1-56/5 * * * * flock -xn /tmp/xlm_memguard.lock /home/opc/xlm-bot/memory_guard.sh
2-57/5 * * * * flock -xn /tmp/xlm_watchdog.lock /home/opc/xlm-bot/watchdog.sh
0 * * * * flock -xn /tmp/xlm_logrotate.lock /home/opc/xlm-bot/log_rotate.sh
```

### Step 6: Set swappiness

```
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Step 7: Verify

1. Check all services: `sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws`
2. Check the dashboard loads: `http://<NEW-IP>:8502`
3. Check Slack gets a "bot_started" alert
4. Wait for one full cycle and check `data/state.json` is updating

### What you lose in a disaster

| Data                | Impact                          | Recovery                         |
|---------------------|---------------------------------|----------------------------------|
| `logs/trades.csv`   | Trade history gone              | Only from backups                |
| `data/state.json`   | Bot starts fresh                | Reconciler finds open positions  |
| `data/XLM_15m.csv`  | Candle cache gone               | Auto-fetched on first cycle      |
| Decision logs       | Debug history gone              | Not critical for operation       |

### Backups (recommended)

Set up a daily rsync from Oracle to your phone:
```
rsync -avz -e "ssh -i ~/.ssh/oracle_key.pem" \
  opc@163.192.19.196:~/xlm-bot/logs/trades.csv \
  /mnt/sdcard/AA_MY_DRIVE/xlm_bot/backups/trades_oracle.csv
```


---


## SOP 11: Escalation Tiers

Not everything needs your attention. Here is when to act and when to ignore.

### Tier 0: Informational -- no action needed

- Slack says bot entered or exited a trade -- normal operation
- Dashboard shows a small loss -- the bot is designed to take small losses
- Memory guard cleared caches -- normal on a 503 MB machine
- Watchdog restarted a service -- automation doing its job
- Bot is not trading during overnight margin hours -- correct behavior

### Tier 1: Check within 1 hour

- Two or more consecutive losses in a short period -- check if the market
  shifted and consider tightening config (SOP 7)
- Dashboard is down -- bot is still trading, you just have no visibility.
  Memory guard probably killed it. It will auto-restart when RAM frees up.
- Disk warning at >80% -- log rotation should handle it, but verify with
  `df -h /home`

### Tier 2: Check within 15 minutes

- Bot stuck for >10 minutes (stale heartbeat) -- SSH in and check SOP 5
- Three or more losses in a row -- consider stopping the bot for the day
  via `sudo systemctl stop xlm-bot`
- Margin warning from Coinbase (Slack alert at 12:30 PM PT) -- the bot
  should handle this, but verify it is not entering new positions
- `SAFE_MODE` triggered -- check state.json for the reason

### Tier 3: Act immediately

- Oracle instance unreachable -- follow SOP 3
- OOM kill of the bot process -- follow SOP 4
- Crash loop (bot restarting every few seconds) -- follow SOP 5
- Unexpected large position or wrong direction -- follow SOP 6
- API keys compromised -- rotate immediately per SOP 9
- Exchange PnL diverges significantly from bot-calculated PnL -- stop the
  bot and reconcile manually

### Tier 4: Everything is on fire

- Oracle instance terminated by Oracle (free-tier reclamation) -- follow SOP 10
- Coinbase exchange outage -- stop the bot, close position via app if
  possible, wait for exchange to recover
- Multiple systems failing simultaneously -- stop everything, close any
  open position through the Coinbase app, investigate when calm

**The golden rule: when in doubt, stop the bot.** A stopped bot cannot
lose money. You can always restart it after you understand what happened.


---


## Quick Reference Card

Print this out or keep it on your home screen for 3 AM incidents.

```
SSH IN:
  ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196

STATUS:
  sudo systemctl is-active xlm-bot xlm-dashboard xlm-ws
  free -m && df -h /home

LOGS:
  tail -50 ~/xlm-bot/logs/xpb_service.log
  tail -20 ~/xlm-bot/logs/decisions.jsonl

STATE:
  cat ~/xlm-bot/data/state.json | python3 -m json.tool | head -30

RESTART:
  sudo systemctl restart xlm-bot xlm-dashboard xlm-ws

STOP EVERYTHING:
  sudo systemctl stop xlm-bot xlm-dashboard xlm-ws

EMERGENCY CLOSE:
  Use Coinbase app > Futures wallet > Close Position

FORCE REBOOT (from phone, no SSH needed):
  oci compute instance action \
    --instance-id ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgachuw5tsdglraq4cuco4qoznrtarctqspta52mta5qf5aq \
    --action RESET

DEPLOY CODE UPDATE (from phone):
  cd /mnt/sdcard/AA_MY_DRIVE/xlm_bot
  bash deploy-native.sh 163.192.19.196 ~/.ssh/oracle_key.pem
```
