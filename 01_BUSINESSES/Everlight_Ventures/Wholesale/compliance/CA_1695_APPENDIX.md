# CA Civil Code 1695 Appendix -- Home Equity Sales Contract Disclosures

**Filed by:** Justine Park, Compliance Gate (drafted by Lucrex while Justine was rate-limited; pending Justine countersign)
**Date:** 2026-04-25
**Status:** DRAFT v0.1, requires CA RE attorney review before first use
**Attaches to:** ASSIGNMENT_CONTRACT_BASE.md
**Trigger:** Any CA 1-4 unit residential principal-residence transaction where the seller is in default OR a Notice of Default has been recorded.

> **THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.** Marquise must engage a California real estate attorney before using this appendix in any actual transaction. Civil Code 1695 violations are misdemeanors (up to 1 year imprisonment + $25,000 fine per Civ. Code 2945.7) and Section 1695.7 provides treble damages plus attorney fees to the seller. The CA preforeclosure outreach gate in `state_gates.json` remains BLOCKED. This appendix exists for the case where a seller already engaged through a non-default channel and a default condition is later discovered before closing.

---

## When This Appendix Attaches

Per Cal. Civ. Code 1695.1(a), a "Home Equity Sales Contract" is triggered when ALL of the following are true:

1. The property is a 1-to-4 unit residential dwelling.
2. The property is the seller's principal residence.
3. A Notice of Default has been recorded against the property under Cal. Civ. Code 2924.
4. The buyer (Everlight Ventures or its assignee) is acquiring the property for any consideration other than as the personal residence of the buyer.

If ALL FOUR conditions apply, this appendix MUST be attached to the assignment contract and executed alongside it. The contract is otherwise void and the seller may rescind without penalty.

---

## Required Statutory Notice (Civ. Code 1695.5)

The following notice MUST appear on the front page of the contract in 14-point bold type, in the same language principally used in the negotiation. If negotiations were conducted primarily in Spanish, Chinese, Tagalog, Vietnamese, or Korean, a translated counterpart pursuant to Civ. Code 1632 is also required.

```
NOTICE REQUIRED BY CALIFORNIA LAW

Until your right to cancel this contract has ended,
[BUYER NAME] cannot ask you to sign or have you sign
any deed or any other document.

YOU MAY CANCEL THIS TRANSACTION, WITHOUT ANY
PENALTY OR OBLIGATION, AT ANY TIME BEFORE [DATE
AND TIME OF CANCELLATION DEADLINE].

See the attached notice of cancellation form for an
explanation of this right.
```

The cancellation deadline is the EARLIER of:
- 5 business days after the day the seller signs the contract, OR
- 8:00 a.m. on the day scheduled for the trustee's sale of the property.

If the trustee's sale is rescheduled, the cancellation deadline does not extend.

---

## Notice of Cancellation Form (Civ. Code 1695.5)

A separate sheet must accompany the contract with the following form, in 12-point type, in the same language as the negotiation:

```
NOTICE OF CANCELLATION

[ENTER DATE OF TRANSACTION]

You may cancel this transaction, without any penalty
or obligation, within five business days from the above
date or anytime prior to 8:00 a.m. on the day scheduled
for the sale of your property pursuant to a power of
sale conveyed in a deed of trust on your property,
whichever occurs first.

To cancel this transaction, mail or deliver a signed
and dated copy of this cancellation notice, or any other
written notice, to:

[BUYER NAME]
[BUYER ADDRESS]
[BUYER PHONE]

NOT LATER THAN [CANCELLATION DEADLINE].

I hereby cancel this transaction.

___________________________     ____________________
Date                            Seller's signature
```

---

## Prohibited Practices (Civ. Code 1695.13 and 1695.14)

The buyer SHALL NOT:

1. Take any power of attorney from the seller.
2. Acquire any interest in the property prior to expiration of the cancellation period, by deed, contract, or otherwise.
3. Record the deed, transfer the contract for sale to a third party, or encumber the property prior to expiration of the cancellation period.
4. Make any false or misleading statement regarding the value of the property, the amount of equity, or the seller's rights.
5. Cause the seller to execute any document where the spaces for material terms are blank or where the seller does not have a fully completed copy.
6. Receive any consideration from the seller for services not yet fully performed.
7. Misrepresent the buyer's intent to keep the property as a principal residence (the federal "purchase money" mortgage exception does not apply here).

The contract is voidable at the seller's option for any of the above. Civ. Code 1695.10 makes any waiver by the seller of these protections void as against public policy.

---

## Counterpart Execution and Effective Date

This appendix and the assignment contract together constitute one agreement. Both the appendix and the contract must be:

- Signed by both parties on the same date as the underlying assignment contract.
- Notarized in CA (Civ. Code 1695.3 requires the equity sales contract be in writing, signed, and the buyer's signature acknowledged before a notary public).
- If a Spanish counterpart is required under Civ. Code 1632, both English and Spanish versions are signed in counterpart and treated as one instrument.

The "transaction date" for purposes of the cancellation calculation is the date the SELLER signs, not the date the buyer signs.

---

## Spanish-Language Trigger Clause

If the negotiation between buyer and seller was conducted primarily in Spanish, Chinese, Tagalog, Vietnamese, or Korean, the following clause attaches:

```
LANGUAGE OF NEGOTIATION

The parties acknowledge that the negotiation of this
agreement was conducted primarily in [LANGUAGE]. Per
California Civil Code 1632, the buyer has provided to
the seller, before this contract was executed, a
[LANGUAGE]-language translation of every term of this
contract, including but not limited to the cancellation
notice and the cancellation form. The seller acknowledges
receipt of the translated copy at the time of execution
and confirms that the [LANGUAGE] copy and this English
copy together constitute one agreement.
```

If the language is Spanish, the companion file is
`/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/ASSIGNMENT_CONTRACT_ES.md`.

---

## Filing Instructions for Marquise

1. The appendix attaches to every CA 1-4 unit residential transaction once any default-related fact appears: NOD recorded, missed mortgage payment disclosed by seller, cure-letter referenced, or AB 519 expanded "in default" condition (any documented delinquency).
2. The appendix is executed in counterpart with the main assignment contract on the SAME day. Notarization happens at the same sitting.
3. The signed appendix is stored under the matching deal folder at `/home/opc/wholesale_agent/contracts_out/<deal_id>/ca_1695_appendix.signed.pdf`.
4. The cancellation deadline must be entered as a calendar event in the operator's calendar (use `branded_calendar.render_event_description()`) the moment the seller signs, with reminders at T-48h, T-24h, T-1h.
5. If the seller cancels before the deadline, the cancellation form is filed in the deal folder, the deal stage is moved to "rescinded_per_1695," and the seller is sent the EMD return immediately (no setoff, no fee, no penalty per Civ. Code 1695.6).
6. NO RECORDING of the deed and NO TRANSFER to an end buyer until the cancellation window has fully expired.

---

## Counsel Review Requirement

Before this appendix is used in a live deal:

1. Engage a California real estate attorney (BAR certified, RE specialty) to review the appendix and the underlying assignment contract together.
2. Have the attorney provide a one-page sign-off letter on firm letterhead acknowledging the appendix as compliant for the operator's first use.
3. Re-engage the attorney any time CA Civ. Code 1695, 2945, AB 519, AB 968, AB 1837, or SB 1079 are amended, or every 18 months, whichever is sooner.
4. Carlos Moreno, Bernard Calloway, and Harrison Knox shall countersign the appendix as internal sign-off after attorney review.

---

**This is research and education, NOT legal advice.**
**DRAFT v0.1. Pending Justine Park final review and CA counsel sign-off.**

Filed by Lucrex on behalf of Justine Park, Compliance Gate.
