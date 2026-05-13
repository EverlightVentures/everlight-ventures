# SOP -- Deal Intake (Lead to Signed PSA)

**Trigger:** Lead signals interest (replies to email, signs consent, requests callback).
**Owner:** Hammer Knox (acquisitions). Backup: Rich.
**SLA:** First contact within 24 hours of trigger. PSA signed within 14 days of first contact.

## Steps

1. CallbackTask auto-creates from IMAP reply or consent-form submission.
2. Hammer reviews talking_points, calls within 24h.
3. On-call: run the 5 qualifiers (condition, occupancy, timeline, motivation, target number). Log to CallLog.
4. If qualified: send written cash-offer range within 24h via branded_mailer.
5. If accepted in writing: send PSA from `contracts/templates/PSA_master_template.md` filled with deal-specific data.
6. PSA signed: Deal moves stage `intro` -> `legal_review`. EMD field set with title-co name + date received.
7. Title search ordered via `free_title_search.py` + manual review of returned URLs.
8. Inspection scheduled within 7 days. inspection_due_date set on Deal.

## Failure modes + fix

- Seller goes silent post-offer: 7-day Belfort follow-up sequence kicks in via `rex_belfort.py`.
- Title comes back with liens: pause Deal, notify seller, decide if liens can be cleared at close.
- Inspection fails: Deal status -> `terminated`. EMD refunded per PSA contingency clause.
