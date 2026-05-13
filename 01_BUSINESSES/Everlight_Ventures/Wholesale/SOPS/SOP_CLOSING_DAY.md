# SOP -- Closing Day Coordination

**Trigger:** Deal scheduled to close. Title has cleared, buyer EMD wired, all contingencies removed.
**Owner:** Hammer (acquisitions handoff) + Rich (final approval).
**Goal:** Smooth, on-time settlement with no surprises.

## T-7 days

- Confirm closing date with title + buyer + seller in writing
- Confirm wire instructions for assignment fee (verify via SECURE channel, not email -- wire fraud risk)
- Schedule final walk-through within 24-48h of close
- Branded calendar invite to all parties via `branded_calendar.render_event_description`

## T-3 days

- Title sends Closing Disclosure / settlement statement for review
- Verify all line items: purchase price, EMD applied, assignment fee, prorations, closing costs allocated correctly
- Flag any discrepancy to title same-day

## T-24 hours

- Final walk-through. Property condition matches PSA representations.
- If anything off (fixtures removed, undisclosed damage): pause + escalate to Rich.
- All signed addenda, PSA, assignment, POF, EMD receipt confirmed in title file

## Closing day

- Wires sent before noon. Confirm receipt at title.
- Seller funds disbursed. Buyer takes title.
- Deeds recorded same-day with county.
- Assignment fee disbursed to Everlight via Stripe invoice or direct ACH (per `Deal.stripe_invoice_id`)
- Deal stage -> `closed_won`. Trigger CommissionRecord creation.

## T+1 day

- Branded thank-you email to seller via `branded_mailer` (vip_reply category)
- Branded thank-you email to buyer with the same property details for their records
- Slack post to #broker-pipeline with deal recap (auto via Marcus closing brief)

## T+7 days

- Branded testimonial request email to seller (per FREE_ACTION_GUIDE testimonial workflow)

## Failure modes

- Wire delay: title escalates with bank. Closing pushed by 1 business day. Notify all parties.
- Funding falls through: revert to assignment alternative (transactional funder if double-close was the plan).
- Buyer no-show at close: 4-hour grace. Then default per PSA.
