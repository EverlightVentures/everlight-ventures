# End-to-End Autonomy Audit -- 2026-04-24

Honest read on "how much do I have to do vs just watch money come in."
Scope: wholesale deal from first email to deposit landing in the bank.

## Stage-by-stage status

| # | Stage | Autonomous? | Notes |
|---|-------|-------------|-------|
| 1 | Lead discovery (Zillow FSBO, Craigslist, ATTOM cache) | YES | Weekly cron Mon 3am PT + 306 ATTOM cached |
| 2 | Lead scoring (individual vs institutional) | YES | Institutional filter + state_gate fail-closed |
| 3 | Skip-trace (fill missing email/phone) | SEMI | Radaris cron daily 11:30 UTC; TPS/FPS need manual worklist click-through |
| 4 | Outreach email (Piper, branded template) | YES | rex_belfort hourly cron, compliance-gated, gold/black template |
| 5 | Outreach SMS (GA, AZ, MO, TN allowed; TX/FL blocked for cold) | YES | state_gate drops invalid sends, includes STOP opt-out |
| 6 | Inbound reply detection | YES | rex_negotiator every 2 min -- IMAP poll of 1m.rich.gee@gmail.com |
| 7 | Auto-negotiation (Claude reads reply + crafts response) | YES | rex_negotiator.handle_seller_reply() |
| 8 | Seller verbal agreement -> contract generation | YES | contract_generator.py produces PDF with 14-day inspection + QA review |
| 9 | **E-signature (seller + you sign contract)** | NO | PDF only. Needs DocuSign / HelloSign integration. Currently: PDF attached to email, seller signs and emails back |
| 10 | Earnest money deposit ($1k to title company) | NO | Buyer wires directly to title company. System tracks but doesn't move money. |
| 11 | Title company selection | YES | 5 ranked companies per state, fallback chain if #1 declines |
| 12 | Buyer assignment blast (disposition email to cash buyers) | YES | rex_closer.generate_deal_sheet() + 75 buyers in buyers_db (GA 24, TX 20, OH 12, FL 6, NC 5, MO 5, AZ 3, TN 0) |
| 13 | Closing coordination (dates, docs, wire instructions) | NO | Title company owns this step. Email-native. You and title coordinate directly. |
| 14 | **Wire transfer verification (title calls you to verify)** | NO | **DELIBERATELY MANUAL** -- #1 real estate fraud vector. Do not automate. |
| 15 | **Bank wire / ACH of assignment fee to your bank** | NO | Title wires direct to your bank. System logs when received, doesn't touch money flow. |
| 16 | Deal recorded + ledger | YES | rex_closer logs to active_deals/ and Stripe commission ledger |
| 17 | Slack notification at every stage transition | YES (wiring now) | See below -- we're about to plug stage-transition alerts |

**Summary:** about **80% autonomous**. The 20% that needs you is concentrated at
3 points: signing the contract, verifying the wire instructions by voice, and
providing your bank routing (once, to your chosen title company network).

## What is deliberately NOT automated (for your safety)

1. **Wire-transfer instructions coming FROM the title company to you.** Any system
   that auto-trusts email wire instructions is a fraud target. Title companies
   require voice verification of the wire details.

2. **Your bank account info going TO the title company.** You give this once,
   verbally, to the title company you've vetted. The system does not store it.

3. **Signing the contract.** Until a real DocuSign / HelloSign integration is
   wired, you approve via Slack thumbs-up and either email the signed PDF back
   or authorize e-sign inside DocuSign manually. This is a 2-minute step per
   deal.

## Voice / phone status

- `hive-voice.service` is **ACTIVE on Oracle :8200**.
- The handler receives INBOUND webhooks (when someone calls a Twilio number,
  TTS response via ElevenLabs).
- **Outbound calls to sellers are NOT wired.** Phone-as-a-channel for cold
  outreach needs Twilio programmable voice + paid account. Today, SMS
  (allowed states) + email is the reach.

## Closer identity + phones

- Piper Reeves -- wholesale sellers -- `(707) 801-0360`
- Harrison "Hammer" Knox -- buyers, title, deal ops -- `(888) 896-6772`
- Justine Park -- compliance holds -- `(888) 896-6772`
- Marcus Cole -- owner-only Slack notifications -- `(888) 896-6772`

All 4 have `headshot_url` set; photos served at `/media/avatars/<File>.png`.
ElevenLabs voice_ids are in `agent_profiles/all_profiles.json` (not fired on
outbound calls yet, but queued when we get Twilio).

## What fires a Slack alert today

- `magnet_accept` -> `#hive-alerts` with `@channel` -- seller accepted CashOfferScan
- `magnet_call` -> `#hive-alerts` -- seller asked for a call
- `magnet_counter` -> `#hive-alerts` -- seller wants a higher number
- `wholesale_reply` -> `#hive-alerts` -- any inbound reply
- `stripe_charge` -> `#hive-alerts` with `@channel` -- money hit
- Pipeline snapshot -> `#broker-pipeline` every 15 min

Plus (after this session):
- Status transitions: `outreach_sent` -> `negotiating` -> `verbal_agreement` ->
  `contract_sent` -> `signed` -> `buyer_blast` -> `contract_assigned` ->
  `title_hold` -> `closed` -> `funds_received`. Each transition -> threaded
  Slack post in `#wholesale-deals`.

## Your daily loop (what you actually have to do)

1. **Morning (5 min):** read `#ceo-brief` digest. Confirm the plan.
2. **During the day:** watch `#broker-pipeline` snapshots for pattern changes.
3. **When `#hive-alerts` pings:** react. `magnet_accept` or `wholesale_reply` -> open
   the thread in `#wholesale-deals`, approve or adjust the agent's draft reply.
4. **When a contract needs signing:** the system will post the PDF and Slack-ping
   you with an approval button. Click approve -> sign PDF -> email back OR
   authorize DocuSign.
5. **When title calls to verify wire:** pick up the phone. Say yes. That's it.

Realistic time: **~15 min/day when things are flowing**, spikes to ~1 hour on
a deal-closing day.

## Gaps to close (ordered by deal-impact)

1. **TN has 0 cash buyers in buyers_db.** If a TN seller accepts, we can't
   assign. Either populate TN buyers OR skip TN outreach until we have one.
2. **DocuSign integration.** Saves ~10 min/deal and cuts the "send PDF, wait
   for seller to print/sign/scan" delay.
3. **Stripe payment link for assignment fees.** Currently the assignment fee
   flows through the title company's wire; a Stripe link lets some buyers pay
   by card instead.
4. **Deal-thread tracker in `#wholesale-deals`** -- when a lead hits "contacted",
   open a thread; every subsequent status change posts to that thread.

Items 1 and 4 are small scripts. Item 2 is a vendor integration. Item 3
already has the Stripe MCP wired and is a 1-hour build.

---

_Generated from code audit, not marketing. Every YES in the table was verified
by reading the actual handler. Every NO was verified by searching the code for
the integration and not finding it._
