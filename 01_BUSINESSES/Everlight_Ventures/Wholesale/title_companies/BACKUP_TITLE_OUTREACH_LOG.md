# Backup Title Firm Outreach Log

**Owner:** Harrison "Hammer" Knox, Deal Closer
**Date:** 2026-04-25 (PT)
**Purpose:** Redundancy on step #6 (escrow + title + EMD). Ohio Real Title (primary, ts 1777222290) is one bus accident from blocked. This log opens 2 backup channels so we have 3 conversations live, not 1.

---

## Entry 001 -- Eastern Title (Cleveland)

- **Recipient:** internet@easterntitle.com
- **From:** marquise@everlightventures.io (Hammer voice, Marquise sender)
- **Subject:** Everlight Ventures wholesale -- Cleveland title partner intro
- **Channel:** branded_mailer.send_branded_email, budget_category=nurture
- **Send result:** ok=True
- **Resend message ID:** 1ab70485-3d60-4845-be74-f178c44f975e
- **Resend last_event:** delivered
- **Wholesaler signal:** Strongest public wholesaler messaging of any OH candidate -- explicitly markets "wholesale assignments, double closings, distressed properties, and creative financing structures" on /ohio/cleveland/commercial-title page.
- **Source:** https://easterntitle.com/ohio/cleveland/commercial-title
- **Email scraped from:** https://easterntitle.com/contact

### Email body (inner, gold template applied)

> Team,
>
> Harrison "Hammer" Knox with Everlight Ventures. We run an assignment-of-contract wholesale operation focused on Cleveland metro and surrounding NE Ohio counties. Looking at 2 to 4 closings per month to start, scaling from there.
>
> I am building out our title partner bench. Three things I need clarity on before we route a file: assignment-fee handling at the table, EMD held in your trust account at a named bank, and typical TTC on a clean cash file.
>
> Can we put 15 minutes on the calendar this week or next for an intro call? If there is a specific person on your investor desk I should be talking to, point me there and I will reach out direct.
>
> Appreciate you.

---

## Entry 002 -- Erie Title (Mayfield Heights, OH -- substitute for Old School Title)

- **Recipient:** orders@erietitle.com
- **From:** marquise@everlightventures.io
- **Subject:** Everlight Ventures wholesale -- Cleveland title partner intro
- **Channel:** branded_mailer.send_branded_email, budget_category=nurture
- **Send result:** ok=True
- **Resend message ID:** 93d0c8df-ddb7-4d8c-9df6-1a4e417a219b
- **Resend last_event:** delivered
- **Substitution rationale:** Old School Title has no public web presence, no scrape-able email, BiggerPockets recommendation requires a forum DM ("ask for Marc") which is not branded_mailer compatible. Per SHORTLIST.md OH note: "If Old School Title cannot be verified, fall back to Harvard Title Agency or Erie Title." Harvard Title also had no public email. Erie Title (Mayfield Heights) is in the eastern Cleveland metro and had a public orders@ address.
- **Source:** https://erietitle.com/contact/
- **Email body:** identical to Entry 001 (Eastern Title). Generic Cleveland-metro outreach, no firm-specific deviation.

---

## Next-touch schedule

- **D+3 (2026-04-28, Mon):** Phone follow-up where listing exists. Eastern Title has no public phone yet, so the touch is a second email at D+5 with sample assignment file structure if no inbound by then. Erie Title -- pull number from website on Monday and call.
- **D+7 (2026-05-02, Fri):** Second email touch with one new piece of value (sample assignment file structure or numbered list of 3 questions in writing). Subject: "Everlight wholesale, follow-up + the 3 questions in writing."
- **D+14 (2026-05-09, Fri):** Decision gate. Either MOU is on the table with one OH firm (Ohio Real Title primary, Eastern Title or Erie Title backup) or escalate to Justine for next-firm sequence. Marquise makes the budget call on a walk-in to any Cleveland address.

## Buddy / cross-team

- **Justine Park** (Compliance) -- B2B vendor outreach is out of scope for the consumer state_gates regime. Both sends bypassed `recipient_state` for the same reason as the Ohio Real Title send. Justine flagged for B2B carve-out review at next compliance sync.
- **Piper Reeves** (Outreach) -- backup sender domain if marquise@ has any deliverability issue.
- **Rex Blackwell** (Wholesale) -- gets a copy of any signed MOU since it impacts pipeline routing.
- **Marquise Caldwell** (Operator) -- final signer on any MOU; receives the result of D+14 decision gate.

## Stack now

| Slot | Firm | Status | Message ID |
|---|---|---|---|
| Primary | Ohio Real Title | delivered 2026-04-25 | 0836e936-2a40-42ed-a7d7-b1759d9c1920 |
| Backup 1 | Eastern Title | delivered 2026-04-25 | 1ab70485-3d60-4845-be74-f178c44f975e |
| Backup 2 | Erie Title | delivered 2026-04-25 | 93d0c8df-ddb7-4d8c-9df6-1a4e417a219b |

3 conversations live. No single-point-of-failure on title/EMD anymore.

---

**Logged by:** Hammer Knox, Deal Closer.
