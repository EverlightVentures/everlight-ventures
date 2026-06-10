# BBB Complaint Response Template — 72-Hour Apology + Cure SLA

**Last Updated:** 2026-05-05 10:25 PT (2026-05-05T10:25:00-07:00)
**Owner:** Hammer Knox (BBB queue) — daily inbox check
**SLA:** Acknowledge within 72 hours of BBB complaint receipt. Resolution within 14 days.
**Storage:** `Wholesale/audit_kit/06_bbb_complaints/<case_id>/`

---

## How to use this template

1. **BBB notifies us of a complaint.** Hammer receives the email or BBB portal notification.
2. **Within 72 hours:** Hammer logs the case at `audit_kit/06_bbb_complaints/<case_id>/case.md` with timestamp, complainant info, allegation, source, and BBB case number.
3. **Within 72 hours:** Hammer sends the acknowledgment response below via the BBB portal AND directly to the complainant via `resend_manager.send(agent='hammer', state=..., budget_category='vip_reply', ...)`.
4. **Within 14 days:** Hammer drives the cure to completion (DNC entry, refund if applicable, escalation to Marcus or Justine if anything is unclear), updates the BBB case, and asks complainant to mark the case resolved.
5. **All correspondence is logged** to `case.md`. Final outcome recorded.

---

## Acknowledgment response (paste into BBB portal + email body)

> Subject: Response to BBB complaint [CASE NUMBER] — [PROPERTY OR ISSUE REFERENCE]
>
> Dear [COMPLAINANT NAME],
>
> Thank you for contacting the Better Business Bureau and bringing this to our attention.
> I am Hammer Knox with Everlight Ventures, and I am personally handling your complaint.
>
> First: I am sorry. The way we engaged with you was not how we want our company to operate,
> and we own that. Whatever expectation we set or communication we sent that led you to file
> with the BBB, we missed the mark.
>
> Here is what we are doing immediately:
>
> 1. **Adding your contact details to our internal Do-Not-Contact list right now.** You will
>    not receive any further outreach from any address ending in @everlightventures.io. The
>    suppression covers email, SMS, mail, and voice. This block is permanent unless you
>    explicitly tell us to re-engage.
>
> 2. **[CURE STEP — fill in based on complaint type, e.g., "Refunding the $X earnest money"
>    OR "Withdrawing the offer letter dated [DATE]" OR "Confirming we have no contract on
>    the property at [ADDRESS]"]**.
>
> 3. **Reviewing how the original outreach happened** so we can prevent the same pattern
>    from reaching anyone else. We treat every BBB filing as a process bug we have to fix.
>
> If there is something else you need from us to consider this resolved, tell me directly
> and I will handle it. My direct contact is below.
>
> Once you confirm you are satisfied, I would appreciate it if you would mark this case
> resolved on the BBB portal so it reflects accurately. If you are not satisfied, tell me
> what would change that and I will do my best.
>
> Thank you for the chance to make this right.
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
> intends to purchase Texas properties and may assign the purchase contract before
> closing. A standalone written §5.0205 disclosure is delivered to seller and end buyer
> prior to assignment. Everlight Ventures is a real estate investor, not a licensed
> Texas broker._
>
> _If you would prefer no further communication of any kind from us, reply STOP and we
> will confirm permanent suppression by separate email._

---

## Cure-step library (fill in step #2 based on complaint type)

**Type A — "Stop emailing me, I said no":**
> "Refunding the contact to our centralized Do-Not-Contact list (`compliance/dnc_list.json`)
> with your email, name, phone, and any property addresses you have given us. The suppression
> is dual-source: any system in our company that sends email or SMS checks this list before
> every send."

**Type B — "You sent me an offer with low numbers / misleading ARV":**
> "Withdrawing the offer letter dated [DATE]. We are taking your address out of our
> active deal pipeline. If you would like a revised number based on rehab estimates or
> recent improvements you can share, send them to me and I will rerun the math through
> our comp validator. Otherwise we are off your property."

**Type C — "You promised cash close in 7 days and could not deliver":**
> "I owe you a clearer explanation of our timeline. Cash close in 7 days requires title
> clearance, lien resolution, and the option period to all align. Most TX deals close in
> 14-21 days, not 7. I have updated our outreach copy so we do not promise tighter
> timelines than we can deliver. If you are still interested in selling, I would love
> to send you a realistic timeline; if not, the case is closed and we are off your
> contact list."

**Type D — "You misrepresented yourself as a buyer when you were just going to assign":**
> "You are right. Texas Property Code §5.0205 requires that we tell you up-front if we
> intend to assign the contract for profit. Our standalone §5.0205 disclosure should
> have been delivered to you before any contract was discussed. I am sending the
> disclosure now via DocuSign for your records, even though we are no longer pursuing
> the deal. If you signed a contract and want it voided, I will deliver a written
> termination notice today."

**Type E — "You called me and would not stop":**
> "I am cancelling all phone outreach to your number. We do not autodial in Texas
> (Texas Bus. & Com. Code §302), and our voice scrub against the National DNC and our
> internal DNC should have caught this. I am personally pulling the call records to
> understand what happened so it does not recur."

---

## Logging schema (`Wholesale/audit_kit/06_bbb_complaints/<case_id>/case.md`)

```markdown
# BBB Complaint Case [CASE_ID]

**Last Updated:** [ISO PT timestamp]
**Owner:** Hammer Knox

## Receipt
- BBB notification received: [DATE/TIME PT]
- BBB case number: [NUMBER]
- Complainant name: [NAME]
- Complainant email: [EMAIL]
- Complainant phone: [PHONE]
- Property address (if any): [ADDRESS]
- Allegation summary: [1-2 sentences]
- Type code: [A | B | C | D | E | other]
- Acknowledgment SLA target (72h): [DATE/TIME PT]
- Resolution SLA target (14d): [DATE/TIME PT]

## Response
- Acknowledgment sent at: [DATE/TIME PT] via [BBB portal | direct email | both]
- Cure steps applied:
  - [ ] DNC entry written (compliance/dnc_list.json + wholesale_agent/opted_out_emails.json)
  - [ ] [Cure step #2 specific to complaint type]
  - [ ] Process review opened (link or summary)
- Direct response copied at: [path to email log entry]

## Resolution
- Resolution date: [DATE/TIME PT]
- Outcome: [resolved-with-cure | resolved-without-cure | unresolved-escalation]
- Complainant feedback: [summary]
- BBB case status: [closed | open]

## Process bug filed
- Internal ticket / commit: [link]
- Cure landed in code: [date]

## Lessons learned
- [1-3 bullets — what we changed so this does not happen again]
```

---

## Status (as of 2026-05-05)

| Case | Complainant | Property | Type | Status |
|---|---|---|---|---|
| streubel-2026-04 | David Streubel | 4435 Westminster Pl, St. Louis MO | A (DNC bypass) | DNC entry made 2026-05-05; no formal BBB filing yet but threatened. Watch for incoming. |
| (none active) | — | — | — | — |

**Action item for Hammer:** monitor `Wholesale/audit_kit/06_bbb_complaints/inbox/` daily.
First complaint that lands triggers the 72-hour SLA clock.
