# Buyer Lock Fee Disclosure -- Everlight Open Deal (v1.0 DRAFT)

**Last Updated:** 2026-05-15
**Status:** DRAFT v1.0 -- pending `legal_heck_aurelio` countersign + TN counsel sign-off. NOT for live use until both sign.
**Renders at:** `https://everlightventures.io/legal/lock-fee-disclosure`
**Delivery:** Inline modal MUST display the disclosure block (below) to every buyer BEFORE the Lock button captures funds. Buyer clicks "I Understand" checkbox to proceed. Click + timestamp logged.

---

## What this document does (plain English)

When a buyer clicks "Lock Deal 24h" on `everlightventures.io/drops/[id]`, they're paying a fee for a 24-hour exclusivity window on a specific wholesale property. This document tells the buyer, in writing and before the charge is captured, that:

1. The Lock Fee is a **service charge** for the exclusivity window, NOT an earnest money deposit.
2. The Lock Fee is NOT held in real estate escrow. Real EMD goes separately to Mid South Title once a Purchase and Sale Agreement is signed.
3. Everlight Ventures (acting as Marquise Reed in TN) is the **buyer-side equitable interest holder**, NOT the seller's broker, NOT a licensed Tennessee real estate broker, and NOT a money transmitter.
4. The Lock Fee refund mechanics depend on the buyer's tier (Verified or Inner Circle). The Browser tier carries no charge.
5. By clicking Lock, the buyer agrees to be bound by the Master Terms of Service at `/legal/tos` and the Lock-specific terms below.

This document is the standalone written notice that satisfies disclosure best practices for short-window pre-contract deposits in Tennessee. It does not replace the seller-facing Tenn. Code Ann. 66-32-101 (SB 909) disclosure, which still applies separately to every PSA.

---

## Disclosure block (verbatim -- for site modal + DocuSign envelope archive)

> **EVERLIGHT OPEN DEAL -- LOCK FEE DISCLOSURE**
>
> **Date of delivery:** _________________________ (auto-stamped at click)
>
> **Property address:** _________________________ (auto-filled from drop)
>
> **Buyer (you):** _________________________ (your account name)
>
> **Wholesaler:** Marquise Reed, designated agent for Everlight Ventures
> **Wholesaler mailing address:** [Memphis TN mailing address on file]
> **Wholesaler license status (Tennessee):** Not licensed as a real estate broker, sales agent, or attorney in Tennessee. Acting as principal-buyer / equitable-interest holder under **Tenn. Code Ann. 62-13-104(b) (principal-party exemption to the Tennessee Real Estate Broker License Act)** and longstanding TN common-law equitable interest doctrine. The seller has been provided the separate disclosure required by Tenn. Code Ann. 66-32-101 (TN SB 909, Wholesaler Disclosure) prior to or contemporaneously with the wholesaler's purchase contract with seller.
>
> **Disclosure to you, the buyer:**
>
> 1. The Lock Fee you are about to pay is a **service charge** for the exclusive 24-hour negotiation window on the property identified above. It is NOT earnest money. It is NOT held in escrow. It is NOT a real estate deposit governed by RESPA, Regulation X, or Tennessee Real Estate Commission rules.
>
> 2. Everlight Ventures DOES NOT hold legal title to the property. Everlight Ventures holds an equitable contractual interest under a separate Purchase and Sale Agreement with the seller, and intends to assign that interest to you (or to another buyer) for a profit that may exceed the seller's proceeds.
>
> 3. **Your Lock Fee mechanics depend on your tier:**
>
>    - **Browser tier:** Stripe authorizes the hold but does NOT charge your card. If you sign a Purchase and Sale Agreement within 24 hours, the hold converts to a charge. If you do not sign, the hold expires and no money moves.
>
>    - **Buyer-Funds-Verified tier:** Stripe charges $___ to your card immediately. If you sign a Purchase and Sale Agreement within 24 hours, the entire amount credits toward your earnest money deposit under that Agreement. If you do not sign, we refund 90% of the charge ($___). Everlight retains 10% ($___) as a service charge for the 24-hour exclusivity window. Everlight absorbs Stripe's payment-processing fee; your refund is the full 90% with no additional deduction.
>
>    - **Inner Circle tier:** Stripe charges $99 to your card immediately. This $99 is non-refundable in all cases. If you sign a Purchase and Sale Agreement within 24 hours, the $99 credits toward the assignment fee at close. If you do not sign, you forfeit the $99. Your separate earnest money deposit (real EMD) under the Purchase and Sale Agreement is wired by you directly to Mid South Title Co., not to Everlight, and is governed by that company's escrow procedures.
>
> 4. The Lock Fee gives you an exclusive 24-hour window to negotiate, inspect, and sign a Purchase and Sale Agreement with Everlight. It does NOT obligate you to close. It does NOT obligate Everlight to accept any specific offer terms. Either party may walk away within the 24-hour window and the only consequence is the Lock Fee treatment above.
>
> 5. By clicking "I Understand and Agree" below, you confirm that:
>    (a) you have read this disclosure;
>    (b) you understand the Lock Fee is a service charge, not earnest money or escrow;
>    (c) you understand the refund mechanics for your tier;
>    (d) you agree to the Master Terms of Service at `everlightventures.io/legal/tos`.
>
> **Governing law:** Tennessee.
> **Venue for disputes:** Shelby County, Tennessee.
> **Statute of limitations:** any claim relating to this Lock Fee shall be governed by Tennessee statutory limitations periods.
>
> ___ I have read and understood this disclosure.
>
> _________________________ Buyer signature (DocuSign / inline)
>
> _________________________ Date

---

## Implementation notes (engineering)

1. The disclosure modal renders on `/drops/[id]` BEFORE the Stripe Checkout flow opens. Buyer cannot click Lock without first clicking "I Understand."
2. Modal acceptance logged to `pulse_events` table with `event_type=lock_disclosure_accepted`, `buyer_id`, `drop_id`, `tier`, `timestamp`, `disclosure_version=1.0`, `client_ip`, `user_agent`.
3. The same disclosure text is also attached as a PDF page in any DocuSign envelope for the corresponding PSA, so it lives in the deal audit trail.
4. On disclosure version bumps (v1.1, v2.0, etc.), prior accepted-version records remain valid for active locks; new locks require fresh acceptance.

---

## Open legal questions for `legal_heck_aurelio` countersign

1. Does the "service charge, not earnest money" framing in section 1 survive TN Real Estate Commission scrutiny if a complaint is filed? (Reasonable likely yes given equitable-interest doctrine, but get a one-page memo.)
2. Is the 1-year SOL enforceable against a Tennessee consumer? (TN consumer protection statutes may override -- confirm.)
3. Does the Inner Circle Lock Fee crediting to assignment fee create a RESPA Section 8 kickback concern if Mid South Title is the title agent? (Likely no because Mid South is independent and the credit is between buyer and Everlight, not buyer/title -- but confirm.)
4. Does the 10% house fee on Verified walks need a per-state ceiling for cross-border buyers? (TN has no statutory ceiling; CA does -- if CA buyer locks a TN deal, which state's consumer rules apply?)
