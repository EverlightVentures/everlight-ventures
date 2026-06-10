# Solo Outreach SOP -- Marquise's 30-Min Morning Routine

**For:** Marquise running solo if Piper is delayed.
**Owner of the SOP:** Piper Reeves (her words, paraphrased to second-person).
**Source:** Hive synthesis 2026-04-28 (DEAL_BY_FRIDAY_PLAYBOOK.md Lane 2).

---

## The 30-Minute Routine

### 0:00-0:05 -- Open the dial sheet

```bash
cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent
ls data/phone_only_leads.csv 2>/dev/null || python3 ../../03_AUTOMATION_CORE/01_Scripts/build_phone_dial_list.py
cat data/phone_only_leads.csv | head -33  # header + 32 numbers
```

If `phone_only_leads.csv` doesn't exist yet, the build script generates it from leads_db.json filtered to `state in {GA,TX} AND has_phone AND not has_email AND status='new'`.

### 0:05-0:08 -- Prep the call sheet

```bash
python3 03_AUTOMATION_CORE/01_Scripts/rex_sdr.py --mode dial-prep --limit 32 --state GA,TX
```

Output: `_logs/broker_ops/dial_sheet_$(date +%F).txt` -- numbered list, one per line, ready to read.

### 0:08-0:25 -- Dial 32 numbers

Manual phone-side from your residential cell.

- ~60 seconds per dial average.
- 4 unanswered rings = hang up. Slybroadcast queue auto-drops the warm 12-sec script.
- Mark each row in `data/dial_log.csv`: outcome = `talked` | `vm` | `dnc` | `wrong#` | `callback` | `voicemail_dropped`.
- Talked outcomes: capture seller objection or interest in `notes` column. One sentence.

### 0:25-0:30 -- Log + tag Hammer

```bash
python3 03_AUTOMATION_CORE/01_Scripts/rex_sdr.py --mode dial-log-summarize
```

Output: count by outcome, posts a summary to Slack #wholesale-deals tagging Hammer if any `talked` rows. Hammer takes the closer hat from there.

**Stop at 30 min. Discipline beats heroics.**

---

## Hard Rules (Piper's catches)

1. **Hard cap at 32 dials/day.** Voice burns flat by call 40. Day 1 = 32 ATL. Day 2 = 32 DFW. No combining.
2. **Walk break before triage.** After 32 dials you're tired. Water + 10 min outside. Triage at minute 35, not minute 31.
3. **Never dial during dinner hours** (5-8 PM PT). Even though state_gates allow it, the conversion drops 80% and the brand cost is high.
4. **Never read the script if it doesn't sound like you.** Piper's VM script is in YOUR voice now -- record it once, Slybroadcast queues it. If the recording sounds canned, redo it.
5. **DNC = permanent.** Any seller who says "do not call" gets logged in dnc_ledger immediately + flagged in dial_log + flagged in leads_db. Permanent.

---

## What's in the cold-call opener

When someone DOES answer (not VM), 30-second opener:

> "Hi, this is Marquise with Everlight Ventures. I came across your property at {address} and wanted to ask if a no-fee cash offer would be useful right now. Are you the owner of the property?"

**Branch tree:**

- **Yes, owner, interested:** "Mind if I send you a one-page summary of how the offer works, then schedule a 10-minute call?" Get email or text-back number. Update leads_db.status to 'engaged'. Hammer takes over by EOD.
- **Yes, owner, not interested today but maybe later:** "Totally fair. Mind if I send a one-page summary just in case?" Ask permission for follow-up email. Log consent in `email_consent` field.
- **Yes, owner, do not call:** "Got it, marking you off." Update DNC immediately.
- **No, not the owner / wrong number:** "Apologies for the misdial." End. Log `wrong#`.
- **Voicemail picks up:** Hang up. Slybroadcast handles the drop.

---

## Reply Triage (when seller calls/texts back)

When you see an inbound from a dialed-today lead:

| Min | Action |
|---|---|
| 1 | Slack-tag Hammer in #broker-pipeline: "Hammer, live one -- {address}, {first_name}, {channel}." |
| 2 | Open `/broker/cashoffer/?lead_id={lead_id}` in browser. Pulls comps + max-allowable-offer. |
| 3-4 | Auto-generate 1-page offer PDF from CashOfferScan. Send via channel they replied on (text back if texted, call back if VM). |
| 5 | Schedule 24-48h follow-up callback via branded_calendar. CC Justine for state-gate compliance check on the invite. |

After minute 5, Hammer takes the closer hat. You go back to whatever else was queued.

---

## What you do NOT do (Piper's correction list)

- **Do not negotiate price on the cold call.** First call = qualify (are they owner, are they motivated). Price comes in the offer email or follow-up call after Hammer ranges the comps.
- **Do not promise specific close dates.** "We can close fast" is fine. "I can close in 7 days" is not -- title firms own that timeline, not you.
- **Do not tell them about your sole-prop status, no LLC, broke-state, or first-deal.** They don't need it. You're Everlight Ventures.
- **Do not skip the merge_field_gate check.** Every text you send through SMS or email should still go through the gate (rex_sdr does this automatically).

---

## The mistake you WILL make (Piper's veteran catch)

You'll dial all 64 in one sitting Tuesday because you're hungry.

By call 40 your tone goes flat. Your "y'all" disappears. You start sounding like a telemarketer. Conversion drops to zero. Bless your heart.

**Fix:** Hard stop at 32 Tuesday. Walk the block. Drink water. Tuesday's second 32 isn't tomorrow's batch -- tomorrow's batch is 32 DFW. The pacing is the play.

---

## File index

| File | Purpose |
|---|---|
| `Broker_OS/wholesale_agent/data/phone_only_leads.csv` | Daily generated dial list, 32 rows max |
| `Broker_OS/wholesale_agent/data/dial_log.csv` | Append-only log of every dial outcome |
| `_logs/broker_ops/dial_sheet_$(date +%F).txt` | Today's printable call sheet from rex_sdr |
| `_logs/broker_ops/dnc_ledger.csv` | Permanent DNC entries (Justine watches this) |
| `01_BUSINESSES/Everlight_Ventures/Wholesale/voicemail/scripts.md` | The Slybroadcast scripts (cold + warm) |

---

**Now go dial. Friday's already ours -- we just gotta dial it in.**

-- Piper
