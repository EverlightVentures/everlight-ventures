# Inbox Automation Setup
**One-time setup for Rich's `1m.rich.gee@gmail.com`. ~10 minutes.**

This wires the autonomous deal loop end-to-end:
- Replies from real counterparties (Mikal, Chris) hit `1m.rich.gee@gmail.com` (because all `@everlightventures.io` aliases forward there via ImprovMX)
- The phone-side IMAP poller catches them every 2 minutes via cron
- The deal-arc router classifies the reply and fires the next email automatically

## Step 1 — Gmail App Password (5 min, one-time)

The poller needs an **app password** (not your main account password) for IMAP login.

1. Go to https://myaccount.google.com/security
2. Make sure 2-Step Verification is ON (required for app passwords)
3. Click **App passwords** → Select app: "Mail" → Select device: "Other" → name it `phone-imap-poller`
4. Copy the 16-character password (looks like `abcd efgh ijkl mnop`, paste WITHOUT spaces)
5. Add to phone env:

```bash
echo 'export GMAIL_APP_PASSWORD="abcdefghijklmnop"' >> ~/.bashrc
echo 'export IMAP_USER="1m.rich.gee@gmail.com"' >> ~/.bashrc
source ~/.bashrc
```

## Step 2 — Gmail Folders / Labels per Agent (10 min, one-time)

So replies are visually segregated and auditable, set up labels in Gmail UI:

| Label name | Filter rule (Gmail UI: Settings → Filters → Create new filter) |
|---|---|
| `Hive/Marquise` | Has the words: `to:marquise@everlightventures.io OR cc:marquise@everlightventures.io` |
| `Hive/Hammer` | Has the words: `to:hammer@everlightventures.io OR cc:hammer@everlightventures.io` |
| `Hive/Piper` | Has the words: `to:piper@everlightventures.io OR cc:piper@everlightventures.io` |
| `Hive/Rex` | Has the words: `to:rex@everlightventures.io OR cc:rex@everlightventures.io` |
| `Hive/Justine` | Has the words: `to:justine@everlightventures.io OR cc:justine@everlightventures.io` |
| `Hive/E-Sign` | Has the words: `from:esign@everlightventures.io OR to:esign@everlightventures.io` |
| `Hive/Wholesale-Replies` | Has the words: `(to:marquise@ OR to:hammer@) -from:noreply` Apply: Skip Inbox, Apply label, Mark as important |

Per filter:
- Apply the label
- Optionally: Skip Inbox (so they don't clutter your main view)
- Apply to existing matching messages (checkbox at the bottom)

The poller doesn't NEED these labels to work — it watches the whole inbox. But Rich asked for visual segregation per agent, and these labels make it easy to skim.

## Step 3 — Activate the cron poller (1 min, one-time)

```bash
# Add to phone crontab
crontab -e

# Then add this line (every 2 minutes during 8am-9pm PT, business hours)
*/2 8-21 * * * cd /mnt/sdcard/AA_MY_DRIVE && python3 03_AUTOMATION_CORE/01_Scripts/phone_imap_poller.py --once >> _logs/inbound/poller.log 2>&1
```

Or for 24/7 watch (uses ~5MB RAM, polls every 2 min):

```bash
# In tmux/screen so it survives logout
tmux new -s poller
cd /mnt/sdcard/AA_MY_DRIVE
python3 03_AUTOMATION_CORE/01_Scripts/phone_imap_poller.py --watch
# Ctrl+B then D to detach
```

## Step 4 — Verify the loop works (5 min)

1. Make sure a deal is live: `intel deal status <key>`
2. Make sure last_stage is M1 or M3 (in negotiation, not past contract)
3. Send a reply from the registered counterparty's email to the agent alias
4. Wait 2-4 minutes (poller cycle)
5. Check `intel deal status <key>` again — should show new `email_received` + next-step `email_sent`

## What gets routed automatically

| Inbound from | Last stage | Reply class | Next action |
|---|---|---|---|
| `mhakeem@timemphis.org` | M1 | any (except STOP) | Fire M3 (opening offer) |
| `mhakeem@timemphis.org` | M3 | counter | Fire M5 (meet) |
| `mhakeem@timemphis.org` | M3 | accept | Fire M7 (contract package) |
| `mhakeem@timemphis.org` | M5 | accept | Fire M7 (contract package) |
| `mhakeem@timemphis.org` | M5 | counter | Fire M5 again (second-round meet) |
| `leads@midsouthhomebuyers.com` | C1 | counter | Fire C3 (meet) — TODO |
| `leads@midsouthhomebuyers.com` | C3 | accept | Fire C4 (assignment package) — TODO |
| Any counterparty | any | STOP | Halt arc, log policy_violation |

## Manual override

If the autonomous flow ever fires the wrong thing, you can manually fire any stage:

```bash
intel deal fire <key> m3_open
intel deal fire <key> m5_meet 12000   # with counter amount
intel deal fire <key> m7_contract
```

## Audit trail

Every event lands in `01_BUSINESSES/Everlight_Ventures/Wholesale/audit/deal_execution.sqlite`
with hash-chained immutability. View any deal's timeline:

```bash
intel deal status <key>     # last 15 events
intel deal verify <key>     # global chain integrity check
```

## Troubleshooting

**Poller log silent for >5 min**:
```bash
tail -50 /mnt/sdcard/AA_MY_DRIVE/_logs/inbound/poller.log
# Common: GMAIL_APP_PASSWORD missing in cron env -> add `source ~/.bashrc;` to the cron line
```

**Reply received but no next step fired**:
- Check classifier: the reply text may not match any signal patterns (returns "neutral")
- Check last_stage: if past negotiation (M7+), counter doesn't route automatically
- Manual override: fire the next step yourself

**Poller fires but classifier wrong**:
- Add the missing pattern to `osint_api/arc_send.py:COUNTER_SIGNALS` etc.
- Re-run; classification picks up immediately (no restart needed for arc_send)
