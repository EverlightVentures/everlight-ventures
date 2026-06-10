# RESPA Zero-Kickback Attestation Request — Title Partner Template

**Last Updated:** 2026-05-05 10:25 PT (2026-05-05T10:25:00-07:00)
**Owner:** Hammer Knox (closing) — phone-verifies title partners before requesting written attestation
**Audience:** Title partners (1st Option Title, Patten Title, Affinity Title, others)
**Purpose:** RESPA §8 anti-kickback compliance — written confirmation that no fees, splits, or referral payments flow between Everlight Ventures and the title partner

---

## How to use this template

1. Hammer phones the title partner first (RESPA-clean test): walk through their typical
   double-close mechanics for a wholesale assignment. Confirm separate funds, two HUDs,
   no shortcut funding.
2. After the call, Hammer emails this attestation request from `hammer@everlightventures.io`
   via `resend_manager.send(agent='hammer', state='TX', budget_category='vip_reply', ...)`.
3. Title partner returns a one-page signed letter on company letterhead.
4. Save the signed letter to `Wholesale/audit_kit/05_respa_title/<title_partner_slug>_<YYYY-MM-DD>.signed.pdf`.
5. Update `wholesale_agent/title_companies.json` `respa_attestation_signed: true` for that partner.
6. Annual re-attestation per the audit binder calendar.

---

## Email body (paste into resend_manager.send body_html field)

> Subject: RESPA §8 attestation for Everlight Ventures wholesale closings
>
> Hello [TITLE PARTNER CONTACT NAME],
>
> Following up on our call earlier this week. Per our compliance program, we ask every
> title partner we route deals through to provide a one-page written attestation
> confirming RESPA §8 compliance.
>
> Specifically we need your firm to confirm:
>
> 1. **No referral fees** flow from your firm to Everlight Ventures, Marquise Smith, or
>    any of our agents in exchange for routing closings to your firm.
>
> 2. **No fee-splits** on title insurance commissions or escrow fees with our firm.
>
> 3. **No affiliated business arrangement** (AfBA) currently exists between our firms.
>    If one is contemplated in the future, an ABA Disclosure Form will be delivered to
>    every consumer at first referral.
>
> 4. **Sellers retain free choice of title company.** If a seller designates an
>    alternate title company, we honor it — no penalty, no pressure.
>
> A short letter on your firm letterhead, signed by an authorized officer, satisfies
> our records. We re-confirm annually.
>
> Happy to send a sample template if that helps.
>
> Best,
> Hammer Knox
> Closing Operations, Everlight Ventures
> hammer@everlightventures.io
> [Sacramento CA mailing address]
>
> ---
>
> _Required by Texas Property Code Section 5.0205: Everlight Ventures or its assignee
> intends to purchase TX properties and may assign the purchase contract before
> closing. A standalone written §5.0205 disclosure is delivered to seller and end
> buyer prior to assignment. Everlight Ventures is a real estate investor, not a
> licensed Texas broker._
>
> _To stop receiving messages from us, reply STOP._

---

## Sample title partner reply letter (what we are asking them to sign)

> [TITLE PARTNER LETTERHEAD]
>
> [DATE]
>
> Marquise Smith
> Everlight Ventures
> [Sacramento CA address]
>
> RE: RESPA §8 Attestation
>
> Dear Mr. Smith,
>
> [TITLE PARTNER NAME] confirms the following with respect to closings handled for
> Everlight Ventures:
>
> 1. No referral fees, kickbacks, or other things of value flow from [TITLE PARTNER]
>    to Everlight Ventures or any of its agents in connection with the routing of
>    closings.
>
> 2. There are no fee-splits on title insurance commissions or escrow fees between
>    our firms.
>
> 3. No affiliated business arrangement (AfBA) currently exists between our firms.
>    Should one be contemplated, an ABA Disclosure Form will be delivered to every
>    consumer at first referral, in compliance with 12 CFR §1024.15.
>
> 4. Sellers and buyers represented in any transaction we close for Everlight
>    Ventures retain their statutory right to choose any title company. We honor
>    seller-designated alternates without penalty or pressure.
>
> This attestation is good for one year from the date above and will be re-confirmed
> annually.
>
> Sincerely,
>
> [AUTHORIZED OFFICER NAME]
> [TITLE]
> [TITLE PARTNER NAME]

---

## Phone-verify checklist (before sending the attestation request)

Hammer's 5-minute call to the title partner — confirm answers before requesting
the written letter:

1. **Double-close mechanics:** "When we wholesale-assign a property to your firm,
   how do you handle the two contracts? Do you fund both legs from end-buyer money?"
   Acceptable: separate funds for each leg, two HUDs, end-buyer funds only fund the
   buyer-side leg. Unacceptable: "we just net the difference" or "single-funded
   double-close."

2. **Earnest money:** "Where does seller-side EMD live until close? Is it
   refundable through the option period?" Acceptable: title partner escrow,
   refundable through option period per TREC paragraph 23.

3. **Assignment fee disbursement:** "Does the assignment fee come through the
   closing statement, or do we collect direct from the assignee?" Acceptable:
   through the closing statement. Unacceptable: direct outside escrow.

4. **TX licensure:** "Is your firm licensed under Texas Insurance Code Chapter 2651?"
   Required answer: yes, with license number on file.

5. **Wholesale familiarity:** "How many wholesale assignments do you handle a month?"
   Acceptable: 1+ per month. Sub-1: not first choice but acceptable as backup.

6. **Sellers' right to choose:** "If a seller designates a different title company,
   how do you handle it?" Required answer: honored without pressure.

If any answer is non-conforming, escalate to Marcus and do not request the
attestation letter — the partner is not RESPA-clean enough for our flow.

---

## Storage

- Phone-verify notes: `Wholesale/audit_kit/05_respa_title/<title_partner_slug>_phone_verify_<YYYY-MM-DD>.md`
- Signed attestation letter: `Wholesale/audit_kit/05_respa_title/<title_partner_slug>_attestation_<YYYY-MM-DD>.signed.pdf`
- Update `wholesale_agent/title_companies.json` `respa_attestation_signed: true` after letter received.

---

## Status (as of 2026-05-05)

| Title partner | Phone-verified | Attestation signed | Active |
|---|---|---|---|
| Mid-South Title (Memphis) | ❓ unknown | ❌ not on file | ✓ in active use for Chris/MSHB closings |
| 1st Option Title (Garland TX) | ❌ pending Hammer | ❌ pending letter | Web-verified only |
| Patten Title (Houston) | ❌ pending Hammer | ❌ pending letter | Web-verified only |
| Affinity Title (DFW backup) | ❌ pending | ❌ pending | Backup only |

**Action item for Hammer:** phone-verify 1st Option Title and Patten Title this week. Send attestation requests after each call. File signed letters as they come back.
