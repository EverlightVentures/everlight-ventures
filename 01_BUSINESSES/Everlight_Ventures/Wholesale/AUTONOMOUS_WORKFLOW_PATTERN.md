# Autonomous Wholesale Workflow Pattern (AWWP)

**Codified from Marquise's 2026-04-29 manual session.** This is the canonical pattern the Hive replicates -- every wholesale deal flows through these 12 phases. Each phase has a named agent owner, a defined hand-off trigger, and a written-output artifact.

**No phase requires Marquise's manual touch.** When agents block on a state-gate (probate authority, real-name capture, MX verification), they queue, escalate, or fall back to the next-best path. Marquise reviews outcomes only -- not steps.

---

## The 12 phases (one canonical run)

| # | Phase | Agent owner | Hand-off trigger | Artifact |
|---|---|---|---|---|
| 1 | Lead intake | (cron) | Daily | `leads_db.json` row |
| 2 | Assessor enrichment | (Playwright + parse_assessor_mhtml.py) | Per parcel selected | `parsed/{parcel}.json` |
| 3 | Buy-box gate | parser's chris_check | Auto on parse | PASS / VACANT / REJECT |
| 4 | Intel deepdive | Cipher Wolfe | On PASS / VACANT verdict | `seller_intel/{parcel}/intel.md` |
| 5 | Skip-trace cascade | Phil Banks (Filter) | On intel done | `seller_intel/{parcel}/skip_trace.json` |
| 6 | Real-name + email gate | Justine Park | Per skip-trace output | `READY_FOR_OUTREACH` flag set |
| 7 | Pre-call email send | Piper Reeves | On `READY_FOR_OUTREACH` | Email sent via `branded_mailer` |
| 8 | Reply triage | (phone_imap_poller + classifier) | Inbound match | Reply tagged + queued |
| 9 | Negotiation + PSA gen | Henry Knox (Hammer) | On positive reply | PSA PDF via `gen_psa.py` |
| 10 | Buyer package + Assignment | Penny Vance + Henry | On signed PSA + EMD wired | Package emailed to Chris first, backups parallel |
| 11 | Title coordination + BEC | Henry + Shield | On Assignment signed + GFAD wired | Closing instructions verified |
| 12 | Wire + ledger + tax reserve | Carlos Moreno | On wire confirm | Commission ledger entry + 30% tax flag |

---

## Phase 1: Lead intake (autonomous, daily)

**Source:** Shelby Tax Sale CSV (https://scgpublic.s3.amazonaws.com/TaxSaleExtract.csv) -- refreshed weekly.
**Filter:** Memphis + Chris's 15 zips + status=new.
**Daily cap:** 25 new parcels selected per day (per Marquise pacing rule).
**Trigger:** Oracle cron at 6 AM PT, runs `pipeline_intake.py`.
**Output:** Top 25 prioritized parcels written to `outreach_queue/2026-MM-DD.json`.

Selection priority order:
  1. TS2202 first (4+ year delinquent = strongest motivation)
  2. Mid-tier zips first (38127, 38109, 38108) over 38106 (oversaturated)
  3. SFR-likely (numbered street address) before vacant lots
  4. Skip parcels already in `seller_intel/`

---

## Phase 2: Assessor enrichment (replaces Marquise's manual MHTML download)

**Method:** Playwright headless Chromium on Oracle E5 navigates to `https://www.assessormelvinburgess.com/propertyDetails?IR=true&parcelid={parcel}`, waits for JS render (3 seconds), saves the rendered HTML to `owner_downloads/inbox/{parcel}.html`.

**Then:** `parse_assessor_mhtml.py` runs over inbox, extracts owner_name + sales_history + Chris verdict, writes `parsed/{parcel}.json`, archives source.

**Rate limit:** 1 parcel per 30 seconds (avoid bot-detection). 25 parcels/day = ~12 minutes of headless run.

**Fallback if assessor blocks:** route through CF Workers proxy or residential proxy (ProxyScrape free tier).

**Status:** Playwright orchestrator NOT YET BUILT -- gates on Oracle reachability (Wave 0 #0 BLOCKED). Until built, Marquise's manual MHTML drop continues to feed the pipeline -- agents process whatever lands in inbox.

---

## Phase 3: Buy-box gate (already built into parser)

`chris_check` field in parsed JSON returns:
- `VACANT_LOT_ACCEPTED`
- `YEAR_BUILT_{YYYY}_PASSES`
- `FIRST_SALE_PROXY_{YYYY}_PASSES`
- `YEAR_BUILT_{YYYY}_PRE_1940_REJECT`
- `NO_SALES_HISTORY_UNKNOWN_BUILD_YEAR`

REJECT verdicts auto-drop. PASS / VACANT continue.

---

## Phase 4: Intel deepdive

`seller_intel_deepdive.py --parcel "{p}"` runs auto on every PASS / VACANT.
Output: signals (estate / absentee / LLC / long-term-owner / etc) + pitch hooks + browser_queue for further enrichment.

Hard rules:
- Public records only (no GLBA / DPPA / HIPAA / sealed)
- No protected-class profiling
- Situational signals only

---

## Phase 5: Skip-trace cascade

Phil's free-tier cascade:
1. Property assessor mailing (already have)
2. Free people search (Anywho, FastPeopleSearch, Whitepages)
3. Probate court records (estate leads)
4. Find-a-Grave (decedent)
5. Public LinkedIn / business records
6. Email pattern guessing + MX verification

**Hard gate:** real first name MUST be captured. No first name = lead returns to enrichment queue, not outreach queue.

**Phone capture:** subject to Cloudflare blocking from phone-side. Currently blocked. Workaround: route through Oracle once reachability fixed, OR pay $30/mo BatchSkipTracing post-Deal-1.

---

## Phase 6: Real-name + email gate (Justine)

Pre-send checklist (Justine's compliance audit):
- [ ] First name captured (real, not placeholder)
- [ ] Email MX-verified (no dead domains)
- [ ] No `[placeholder]` or `{first_name}` strings in body
- [ ] CAN-SPAM compliant (sender ID, opt-out, accurate subject)
- [ ] State-specific gates clear (TN: warm-only first 3 deals; cold-call BLOCKED until registered)
- [ ] DNC scrubbed if phone present

ANY check fails = lead returns to enrichment queue.

---

## Phase 7: Pre-call email send (Piper)

**Send via:** `branded_mailer.send_branded_email(category="vip_reply")`
**From:** rich@ or henry@everlightventures.io
**Cap:** 25-30 sends/day (Marquise pacing rule)
**Spacing:** ~5-min between sends (avoid spam-trap pattern)
**Template:** pre-call email template per signal mix (estate / out-of-state / LLC / local)

---

## Phase 8: Reply triage

`phone_imap_poller` polls inbox every 5 min for replies to outbound. On match (sender = contacted address):
- Auto-tag reply with parcel_id
- Classify intent (interested / not interested / question / STOP)
- If interested: queue for Henry
- If STOP: drop lead, no further contact

---

## Phase 9: Negotiation + PSA generation (Henry)

On positive reply, Henry triggers `gen_psa.py "{parcel}"`. PDF generates with TN SB 909 Schedule A bundled. Henry reviews offer math (Penny ceiling), sends to seller via Documenso for e-signature.

---

## Phase 10: Buyer package + Assignment (Penny + Henry)

On signed PSA + EMD wired:
- Penny generates buyer package (PSA + EMD confirm + photos + assessor sheet + SB 909 disclosure)
- Email sends to Chris first (leads@midsouthhomebuyers.com + chris@)
- Parallel: package to top 2 backup Memphis buyers if Chris unresponsive >36 hrs
- Chris's Assignment Agreement triggers via `gen_assignment_agreement.py "{parcel}"` (NEW, gated on task #25)
- GFAD wire required within 48 hrs of Chris signing -- per Layer 2 of Chris-lock structure

---

## Phase 11: Title + BEC (Henry + Shield)

Shield's pre-wire BEC checklist (mandatory):
- [ ] Wire instructions verified by call to Mid-South on number from THEIR website
- [ ] Last-4 routing read-back, named agent + timestamp logged
- [ ] No instruction changes accepted within 24 hrs of wire
- [ ] Buyer wires direct to title escrow (never to us)

---

## Phase 12: Wire confirm + ledger + tax reserve (Carlos)

On wire received:
- `commission_ledger.py` logs entry (parcel, fee, source, date, tax-reserve flag)
- 30% auto-flagged for transfer to tax savings
- Slack #wholesale-deals posts summary
- All agents who contributed get credit-of-record (Cipher, Phil, Piper, Henry, Penny, Justine, Shield, Carlos)

---

## Daily Hive operating rhythm (autonomous)

```
06:00 PT  -- Phase 1: pipeline_intake.py picks top 25 parcels
06:15 PT  -- Phase 2: Playwright pulls assessor data (when Oracle live)
06:30 PT  -- Phase 3: chris_check gate auto-applies, REJECTs drop
06:45 PT  -- Phase 4: Cipher intel deepdive on PASS/VACANT
07:30 PT  -- Phase 5: Phil skip-trace cascade
08:30 PT  -- Phase 6: Justine compliance gate
09:00 PT  -- Phase 7: Piper sends pre-call emails (within 25/day cap)

continuous -- Phase 8: reply_classifier polls IMAP every 5 min
on-demand -- Phase 9-12: Henry/Penny/Shield/Carlos handle yes-replies as they land

00:00 PT  -- Charles Dawson runs Operator Truth audit on the day's claims
```

---

## What blocks full autonomy right now

| Blocker | Phase impacted | Workaround |
|---|---|---|
| Oracle E5 unreachable from phone | Phase 2 (Playwright pull-down) | Marquise's manual MHTML drop continues feeding the pipeline |
| Cloudflare blocks phone-side skip-trace | Phase 5 (phone capture) | Email-only outreach until Oracle live; phone after |
| Assignment Agreement generator not built | Phase 10 (Chris lock) | Built within 30 min, task #25 active |
| Backup buyer pipeline not yet active | Phase 10 fallback | Penny's reactivation email goes Wed AM |
| Mid-South Title not yet onboarded | Phase 11 | Henry's call script ready, Marquise dials Tuesday |

**Everything else runs autonomous.** The 4 actions Marquise was going to do tomorrow (Chris confirmation, MST call, Penny's email, hand-deliver Marco) get re-routed:

1. Chris confirmation → Marcus auto-fires from `henry@` since drafted + reviewed (or Marquise approves with one-button on phone)
2. MST call → Henry dials from his Slack-bot interface (Marquise approves transcript after; Henry's voice is a TwiML synth, not human)
3. Penny's email → fires after Marquise approves the 3 placeholders (mailing addr, callback phone, sender alias)
4. Marco hand-deliver → DROPPED. Re-routed to email pattern guess + MX verify; if no email lands, Marco moves to Tier-2 follow-up (door-knock dispatched to a contracted agent in Memphis later, NOT Marquise)

---

## How agents replicate this pattern for new buyers / new markets

When a new buyer relationship is established (after Chris): clone this 12-phase workflow with new constants:
- Buyer's buy box (zips, type, price, condition)
- Buyer's MAO formula (added to Filter's scoring)
- Buyer's decision SLA
- Buyer's preferred title firm
- New state-specific compliance gates if outside TN

Pattern is buyer-agnostic. The phases don't change; the parameters do.
