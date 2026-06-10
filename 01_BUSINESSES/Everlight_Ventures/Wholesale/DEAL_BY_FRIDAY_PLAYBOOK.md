# Deal by Friday -- Execution Playbook

**Compiled:** 2026-04-28 by Marcus Cole orchestrating 5-agent Hive (Rex, Piper, Hammer, Filter, Justine) + cross-check by Slate Mercer.
**Doctrine:** Cross-check + synthesize pattern. Provenance below.
**Friday target:** 1+ hot lead in PSA-pipeline (signed seller agreement OR active negotiation with offer outstanding). Realistic close-by-Friday probability per Filter: 18%. Realistic hot-lead-by-Friday probability: ~50% if all tracks fire.

---

## The Two-Queue Truth (cross-check resolution)

Filter's score >= 60 rule applies to **email queue ONLY**. Phone-only leads use a DIFFERENT scoring scale (max 75 since `has_email` adds 25 pts they can't earn). Both queues fire Tuesday.

| Queue | Source | Pull rule | Owner | Cadence |
|---|---|---|---|---|
| **Email queue** | leads_db.json + CL scrape (Wed+) | `score>=60 AND has_email AND state in {GA,TX,FL,IN} AND status='new'` | rex_sdr.py via Resend | 8 AM + 12 PM + 5 PM PT |
| **Phone queue** | 64 GA+TX phone-only leads | `score>=50 AND has_phone AND state in {GA,TX} AND last_contacted IS NULL` | Marquise dialing + Slybroadcast | Tue 11 AM + Wed 11 AM (32+32) |

These run in parallel. They never compete for the same lead because email-having leads are ineligible for phone (use email, it's free) and phone-only leads can't be emailed.

---

## Tuesday Morning -- Time-Boxed Order of Operations (the gap all 5 missed)

| Time PT | Action | Owner | Duration |
|---|---|---|---|
| 7:00 AM | Wake. Coffee. Open INFRASTRUCTURE.md + this file. | Marquise | 15 min |
| 7:15 AM | **Verify Oracle reachability** (Cloud Console, VCN list). 5-min unblock. | Marquise | 5 min |
| 7:20 AM | **Rotate Gmail app password** per `runbooks/gmail_app_password_rotation.md`. | Marquise | 5 min |
| 7:25 AM | Update `/home/opc/.env GMAIL_APP_PASSWORD` (only if Oracle responded). Else update phone `.env`. | Marquise | 3 min |
| 7:30 AM | Background scrape: trigger CL ATL+DFW scrape (script below). Runs ~2 hours unattended. | rex_blackwell.py | 2 hours bg |
| 7:30 AM | **Run rex_sdr.py with morning batch** -- whatever's eligible from existing leads_db (~5-10 emails). | rex_sdr | 5 min |
| 7:35 AM | Quick reply check (last 24h Resend/Gmail). | Marquise | 5 min |
| 7:40 AM | **Title firm calls (3 calls, Hammer's script)**: Campbell & Brannon Marietta -> Capital Title TX Plano -> Weissman PC Sandy Springs. | Marquise | 30-45 min |
| 8:30 AM | **First phone batch (32 dials)** ATL leads. 60 sec/dial avg, Slybroadcast on no-answer. | Marquise | 35 min |
| 9:05 AM | Walk break. Water. (Piper's catch -- voice burns out at call 40.) | Marquise | 10 min |
| 9:15 AM | Triage any inbound replies from morning send. | Marquise + Hammer (Slack) | 15 min |
| 9:30 AM | **PSA prep for any hot reply.** CashOfferScan + draft contract via existing PSA generator. | Marquise + Hammer | 30 min |
| 10:00 AM | **DBA filings** -- file GA OCGA 10-1-490 + TX Form 503 in person at Fulton + Dallas County clerks (`dba_filings.md`). | Marquise (in person) | 90 min |

**Stop at 11:30 AM PT.** Lunch + reset. Afternoon = afternoon outreach + DFW dial batch tomorrow.

---

## Wednesday Morning -- After CL Scrape Lands

CL scrape output processed Tuesday night by Filter scoring (auto). Wednesday Marquise wakes to a fresh top-50 email queue.

| Time PT | Action |
|---|---|
| 7:00 AM | Coffee. Read overnight Slack #wholesale-deals. Check for replies. |
| 7:30 AM | **Run rex_sdr.py morning batch** -- now hitting CL-scraped leads, much higher email volume (~20-50). |
| 8:00 AM | DFW phone batch (32 dials, second half of the 64). |
| 8:45 AM | Triage replies. Hammer ready in #broker-pipeline. |
| 9:30 AM | If any title firm came back with pre-approval letter Tuesday -- send first PSA via Documenso. |
| 10:00 AM | Free hours. Use for whatever the day surfaces. |

---

## Thursday + Friday

Continue daily cycle: morning rex_sdr + afternoon rex_sdr + reply triage + PSA prep on hot leads. Filter predicts probability of a closed deal by Friday at 18% (one realistic conversion path) -- but probability of a hot lead with PSA signed by Friday is ~50%.

If a hot lead lands Wednesday or Thursday, the Friday wire is plausible: same-day PSA signed via Documenso -> earnest money to Campbell & Brannon escrow Thursday -> 7-day inspection waiver -> close Friday or Tuesday next week.

---

## The Five Lanes Synthesized

### Lane 1: Email outreach (Rex + Filter + Justine)

**Source code:** `rex_sdr.py` (existing, working) + Filter's scoring weights applied to leads_db.json + Justine's compliance pre-check + merge_field_gate.

**Lead supply path** (Rex's call):
- Today/tonight: CL ATL+DFW housing-by-owner scrape with 8 distressed keywords. Realistic capture: 60-70 emails per 100 listings (CL relay-emails).
- Wed+: top-50 email queue refreshed daily from CL deltas + existing leads.

**Pre-send compliance gates** (Justine's chain, fail-closed):
1. state_gate active_in_pipeline clear
2. recipient_classifier passes (homeowner)
3. DNC ledger no entry
4. merge_field_gate audit clean
5. CAN-SPAM footer + opt-out + physical address
6. resend_budget under daily 100 cap

**Volume target:** 8 today (existing leads), 30 Wednesday, 50 Thursday, 50 Friday. Cumulative ~140 by Friday close.

**Operator Truth on volume claims:** Resend API `/emails` count is the truth, not the script's internal counter. If rex_sdr says 12 sent and Resend API shows 8, the report says 8 and we investigate.

### Lane 2: Phone outreach (Piper)

**The 32+32 split.** Piper's hard rule: voice burns flat by call 40. Day 1 = 32 ATL. Day 2 = 32 DFW. No 64-in-one-sitting heroics.

**Cold VM script (recorded once, queued via Slybroadcast):**

> "Hey {first_name}, this is Marquise with Everlight Ventures down in Nashville. I came across your property at {address} and I think we may be able to help y'all out -- no pressure, no listing fees, no repairs. If it's worth a 2-minute conversation, ring me back at this number. Thanks {first_name}, talk soon."

**Reply triage workflow** (5 minutes flat per reply):
- Min 1: Slack-tag Hammer in #broker-pipeline
- Min 2: Open `/broker/cashoffer/?lead_id={id}` for comps + MAO
- Min 3-4: Auto-generate 1-page offer PDF, send via reply channel
- Min 5: Schedule 24-48h callback via branded_calendar

### Lane 3: Title firm intake (Hammer)

**Tuesday 9-11 AM PT, top 3 calls in this order:**

1. **Campbell & Brannon, Marietta** (770-422-5135). GA volume shop, assignment-friendly.
2. **Capital Title of Texas, Plano** (972-403-7800). DFW heavyweight, investor desk.
3. **Weissman PC, Sandy Springs** (404-926-4500). Backup ATL, attorney-state credibility.

**Phone script verbatim** (read off card):

> "Morning, this is Marquise with Everlight Ventures out of California. I'm wholesaling residential -- assignment of contract -- and I'm building a short list of title firms I trust in [Atlanta/DFW]. Got five minutes for a few quick questions?"

**The 5 questions:**
1. Do you close double-closings and assignment-of-contract deals?
2. Are your assignment fees disclosed on the HUD-1 / CD as a separate line item to all parties?
3. Do you require any earnest money or fees from me up front, before a contract is in escrow?
4. What's your standard turnaround from contract-to-close on a cash assignment?
5. How many assignment closings have you handled in the last 30 days?

**Walk if:** money up front, hidden assignment fee, "we don't do those."
**Sign if:** disclosed line item, no advance fees, 7-14 day turnaround, recent reps.

**DO NOT MENTION (Hammer's hard rule):** "first deal," "no LLC," "broke," "sole prop," "I just got my license back." You're Everlight Ventures. Period.

**Pre-approval letter request after 5-min test passes:**

> Subject: Title firm pre-approval -- Everlight Ventures
> 
> Hi [Closer Name] -- appreciate the call this morning. Confirming Everlight Ventures will be sending assignment contracts to your firm for closing. Could you send a one-paragraph confirmation letter on firm letterhead stating your firm closes assignment-of-contract transactions and discloses the fee on the CD? Need it for buyer-side underwriting. -- Marquise

### Lane 4: Lead scoring (Filter)

**Run Tuesday morning before rex_sdr fires.** Updates leads_db.json scores so the morning email batch hits the right targets.

**Scoring weights (linear, 0-100):**

| Attribute | Pts | Logic |
|---|---|---|
| lead_type | 25 | tax_lien=25, pre_foreclosure=25, code_violation=18, expired_listing=15, vacant=15, generic=5 |
| has_email | 25 | email=25, phone-only=8, neither=0 |
| active_state | 20 | GA/TX/FL/IN=20, adjacent=10, other=0 |
| asking_price>0 | 10 | known value=10, zero=0 |
| DoM tier | 10 | >180d=10, 90-180=7, 30-90=4, <30=1 |
| individual_owner | 10 | INDIVIDUAL=10, TRUST=6, LLC=2 |

**Top-50 rule:** `score >= 60 AND has_email AND state in {GA,TX,FL,IN} AND status='new'`. Expected yield from existing 553: 6-12 leads (8 most likely).

**Phone-queue rule:** `score >= 50 (out of 75 max) AND has_phone AND state in {GA,TX}`. Expected yield: ~50 of the 64 GA+TX phone-only.

**Filter's predicted throughput Friday:**
- Cumulative emails: ~140
- Cumulative phone touches: 64
- Total contacts: ~204
- Conversations: 8-15
- Hot leads: 1-3
- Deal-eligible by Friday: 0.3 (single-digit probability)
- Deal-by-Friday close: 18%

### Lane 5: Compliance (Justine)

**The 5 auto-blocked categories** (pre-rendered drop list):
1. LLC/entity owners cold first-touch (commercial-intent statute differences)
2. Probate executors with retained counsel (interference exposure)
3. Bank-owned REO / servicer-held (Fannie/Freddie/HUD)
4. Trust-owned with institutional fiduciary
5. Active-litigation parcels (lis pendens; tortious interference)

**The 3 GA+TX mid-sequence leads** (Aguayo, Garnica, Chavez): leave on existing cadence. Step 4 hits day-10 (Friday 5/2 from 4/22 last touch). They auto-fire Friday morning if rex_sdr is running. Don't reset; don't double-touch.

**Pre-send dry-run command Marquise runs before every batch:**
```bash
python3 -m broker_os.compliance.rex_sdr_dryrun --batch today --show-verdicts
```
Shows each lead row with state_gate / classifier / DNC / merge / CAN-SPAM / budget verdicts and final SEND or DROP.

---

## The 3 Gating Marquise Actions (still URGENT, today)

These are blockers across multiple lanes:

1. **Verify Oracle E5 reachability.** Currently HTTP 000 across all probed ports + SSH timeout. Without Oracle, lanes 1 + 4 + 5 run on phone-side fallback (which works but is fragile). Open Cloud Console, verify instance running + VCN security list.
2. **Rotate Gmail app password.** IMAP failing since 2026-04-24. Without this, replies from outreach batches don't reach Hammer for triage. **Reply detection is broken until rotated.** 5-min runbook ready.
3. **GA + TX d/b/a registration filings.** Without these, no GA or TX PSA gets signed (sole prop personal-asset exposure). ~$300 + 2-3 weeks parallel; 90-min Tuesday.

If you do nothing else today, do these three.

---

## Operator Truth on Daily Reports

Marquise sees one Slack post each evening at 6 PM PT in #revenue-dashboard with the day's numbers. Charles Dawson 4-point check applies to every claim:

| Claim | 4-point verification |
|---|---|
| "Sent N emails today" | Resend API count + log row count + DNC writes + Django outbound rows must agree |
| "Talked to N homeowners" | Phone-call audit log + Slack #wholesale-deals reply triage entries + dial_log.csv outcomes must agree |
| "K hot leads in pipeline" | leads_db.json status='engaged' count + Hammer's #broker-pipeline tags + match_score>=70 rows |
| "Title firm X passed RESPA-clean test" | Phone-call recording (or Marquise notes) + pre-approval letter received + TitleCompany.respa_clean_verified=True written |

Failures lead. Greens follow. The day's headline = the failure that mattered most + the singlest most-important green.

---

## Provenance Index

| Section | Primary contributor | Cross-checker | Resolution |
|---|---|---|---|
| Two-queue truth | Filter Banks | Slate Mercer | Cross-check resolved phone-only score gap; separate queues |
| Tuesday morning order | Slate Mercer (gap catch) | Marcus Cole (final order) | All 5 agents had pieces; Slate caught the missing time-axis |
| Lane 1 email outreach | Rex Blackwell + Filter + Justine | Justine compliance lock | Rex CL scrape + Filter scoring + Justine compliance gates |
| Lane 2 phone outreach | Piper Reeves | (no conflicts) | Verbatim including the 32+32 hard rule |
| Lane 3 title firms | Hammer Ortiz | (no conflicts) | Verbatim including 5 don't-mentions |
| Lane 4 scoring | Filter Banks | Slate (range adjustment for phone-only) | Two-queue scoring scales |
| Lane 5 compliance | Justine Park | Marcus (Operator Truth integration) | 5-category auto-block + dry-run command |
| 3 gating actions | Marcus (synthesizer) | All 5 agents flagged at least one | Consolidated to top-3 blockers |
| Reply-detection gap | Slate cross-check | (no original audit covered) | Surfaced as URGENT #2 |
| Mid-sequence 3 leads gap | Slate cross-check + Justine resolution | Justine final call | Leave on existing cadence |
| Operator Truth integration | Charles Dawson (prior dispatch) | Justine confirms applies | 4-point check applies to all daily reports |

---

## Decision Log

- **2026-04-28 conflict:** Filter score>=60+has_email vs Piper 64 phone-only dial plan. **Resolution:** two parallel queues, separate scoring scales.
- **2026-04-28 strategic:** Title firm call order (3 firms in priority). **Decision:** Campbell & Brannon -> Capital Title TX -> Weissman PC. Hammer's call.
- **2026-04-28 compliance:** 3 mid-sequence GA+TX leads at step=3 from 4/24. **Decision:** leave on existing cadence (Justine's call). Step 4 fires Friday automatically.
- **2026-04-28 doctrine:** This is the second artifact under cross-check + synthesize. INFRASTRUCTURE.md was first. The pattern works.

---

**Read this file first thing Tuesday morning. Execute the time-boxed order. Friday is in play.**
