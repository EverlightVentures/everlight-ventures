# Required Disclosure Templates (by state)

Every contract and every piece of outreach must include the state-specific disclosures below. `contract_generator.py` pulls these from the keys in `state_gates.json`.

---

## Texas (SB 1577 equitable interest)

Required in EVERY marketing piece to seller AND to buyer, AND in the contract:

```
NOTICE OF EQUITABLE INTEREST. Everlight Ventures LLC holds only an
equitable and contractual interest in the property located at
[PROPERTY ADDRESS]. Everlight Ventures LLC does not hold legal title.
This offering is a sale or assignment of Everlight Ventures LLC's
contractual right to purchase, not a sale of the real property itself.
```

## Arizona (HB 2747 / A.R.S. 44-5101 wholesale buyer intent)

Required in the contract:

```
WHOLESALE BUYER DISCLOSURE. Buyer is a Wholesale Buyer as defined under
A.R.S. 44-5101. Buyer intends to assign this contract or otherwise
transfer Buyer's equitable interest to a third party prior to closing.
Seller has the right to cancel this contract at any time prior to
closing if Buyer fails to complete this assignment disclosure.
```

## Tennessee (HB 2537 bold-font equitable interest + 3-day notice)

Required in the contract, in BOLD 12pt or larger:

```
**EQUITABLE INTEREST DISCLOSURE. Buyer holds an equitable interest in
the real property described herein and intends to assign Buyer's rights
under this contract to a third party. Buyer will provide Seller with
written notice of such assignment at least three (3) business days
prior to the assignment taking effect. The ultimate purchaser of the
property may be different from the named Buyer.**
```

## California (CC 1695 equity purchaser contract)

When contracting with a CA seller in foreclosure:
- Contract must be notarized.
- Seller has right to cancel until midnight of the 5th business day following execution, OR until 8:00 a.m. the day scheduled for trustee sale, whichever is first.
- If Spanish was spoken during negotiation, contract must be in English AND Spanish.
- Required cancellation-notice text attached as Appendix A (see `ca_1695_appendix.md` -- TBD).

Until a CA attorney reviews and signs off on our CA pre-foreclosure template, CA pre-foreclosure is BLOCKED by the pipeline (`state_gates.CA.preforeclosure_outreach_allowed = false`).

## Florida (FS 501.1377 equity skimming compliance)

When contracting with a FL seller in foreclosure, contract must:
- State in bold that the seller is not required to sign.
- Provide a 3-day rescission right.
- Not contain a power of attorney in our favor.

## Recording Disclosure (CA, FL, all-party states)

Every call to a CA or FL number opens with:

```
This call may be recorded for quality and training purposes.
```

Delivered BEFORE any substantive conversation. This is a hard requirement enforced by `hive_outreach.py` before the call connects.

## CAN-SPAM Email Footer

Every outbound email must include:

```
Everlight Ventures LLC
[PHYSICAL MAILING ADDRESS]
If you no longer wish to hear from us, reply UNSUBSCRIBE or click the
unsubscribe link below. We will process your request within 10 business days.
```

## SMS Opt-Out (all states)

Every cold SMS must include `Reply STOP to opt out.` in the body. Verified by `hive_outreach.send_sms()` before send.

---

## Notes for Justine

- The TX SB 1577 template above is our draft. There is no standard TREC form -- plaintiff-side attorneys are testing the "nature of equitable interest" phrasing, so we lean verbose and explicit.
- TN HB 2537 says "bold, large font." 12pt bold is our floor; 14pt is safer.
- CA appendix needs a CA attorney sign-off before we enable CA pre-foreclosure. Park that work until after L2 ships in GA/FL/MO.
- Review this file on the 1st of each month.
