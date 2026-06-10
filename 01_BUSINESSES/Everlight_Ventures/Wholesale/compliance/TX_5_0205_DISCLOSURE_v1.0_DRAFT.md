# TX §5.0205 Wholesale Disclosure — Standalone (v1.0 DRAFT)

**Last Updated:** 2026-05-05 09:55 PT (2026-05-05T09:55:00-07:00)
**Status:** DRAFT v1.0 — pending Bernard Calloway countersign + external TX real estate counsel sign-off. NOT for live use.
**Supersedes:** `TX_DISCLOSURE_APPENDIX.md` v0.1 (2026-04-26), which contained three errors corrected here.
**Authority:** Tex. Prop. Code §5.0205 (renumbered from §5.086 by SB 1577, effective 2024-01-01).
**Delivery:** standalone written notice, e-signed via DocuSign or Dropbox Sign with audit certificate, delivered to BOTH the seller AND the end buyer BEFORE the assignment contract is executed.

---

## What this document does (plain English)

Texas law (Property Code §5.0205) requires a wholesaler to tell both the seller and the end buyer, in writing and before the assignment contract is signed, that:

1. The wholesaler is selling only an option or assigning an interest in a contract — not transferring legal title.
2. The wholesaler does not own the property and intends to assign the contract for profit.

This document is the standalone written notice that satisfies that requirement. It is delivered separately from the purchase contract, signed by the receiving party, and archived to defend any §5.0205-based dispute.

The previous internal v0.1 of this document referenced §5.086 (now renumbered) and asserted a "24-month rescission tail" that does not appear in the statute. Both errors have been removed.

---

## Disclosure block (verbatim — for DocuSign / Dropbox Sign signature flow)

> **TEXAS PROPERTY CODE §5.0205 WHOLESALE DISCLOSURE**
>
> **Date of delivery:** _________________________
>
> **Property address:** _________________________
>
> **Wholesaler:** Marquise Smith, doing business as Everlight Ventures
> **Wholesaler mailing address:** [Sacramento CA address on file]
> **Wholesaler license status (Texas):** Not licensed as a real estate broker, sales agent, or attorney in Texas. Acting as principal-buyer / equitable-interest holder under Texas Property Code §5.0205 and Texas Occupations Code §1101.0045.
>
> **Disclosure to the recipient:**
>
> 1. Marquise Smith / Everlight Ventures has entered into, or intends to enter into, a written purchase contract for the property identified above and holds, or will hold, an equitable interest in that contract.
>
> 2. Marquise Smith / Everlight Ventures DOES NOT hold legal title to the property. The wholesaler is selling only an option to purchase, or assigning the wholesaler's interest in the purchase contract, and is NOT conveying the property itself.
>
> 3. Marquise Smith / Everlight Ventures intends to profit from the assignment of the contract, not from acquiring fee simple ownership of the property.
>
> 4. The recipient is encouraged to consult independent legal, tax, and real estate counsel of the recipient's choosing before signing this disclosure or any related contract.
>
> 5. Closing on the property will occur through a Texas-licensed title company under Texas Insurance Code Chapter 2651. Earnest money and assignment fees flow through that title company, not directly between the parties.
>
> 6. Recipient's role:
>    - [ ] Seller of the property (acknowledging wholesaler will assign before closing)
>    - [ ] End buyer / assignee (acknowledging wholesaler is not selling the property itself, only assigning a contract right)
>
> **Acknowledgement:** By signing below, the recipient confirms receipt of this written §5.0205 disclosure prior to executing any related purchase or assignment contract.
>
> Recipient name (printed): _________________________
>
> Recipient signature: _________________________
>
> Date: _________________________
>
> Wholesaler signature: _________________________ (Marquise Smith / Everlight Ventures)
>
> Date: _________________________

---

## Statutory basis (for counsel review)

- **Tex. Prop. Code §5.0205 (eff. 2024-01-01)** — wholesaler must give written disclosure before selling an option or assigning an interest in a contract to purchase real property; disclosure goes to both seller and end buyer; statutory text quoted in `TX_LOCKDOWN_RESEARCH_2026-05-04.md`.
- **Tex. Occ. Code §1101.0045** — equitable-interest carve-out from real estate licensing if disclosure is delivered.
- **Tex. Occ. Code §1101.758** — Class A misdemeanor for unlicensed real estate brokerage; non-disclosure of §5.0205-style intent is the trigger.
- **Tex. Bus. & Com. Code §17.46 (DTPA)** — common-law fraud + treble damages exposure if "we will buy" representation is made without §5.0205 disclosure of intent to assign.
- **Tex. Insurance Code Chapter 2651** — title insurance agency licensing; closing must flow through a Texas-licensed title company.

---

## Delivery rules (operational)

1. **Channel:** DocuSign or Dropbox Sign envelope sent separately from the purchase contract (NOT bundled). Recipient receives a dedicated email with the disclosure as the only document in the envelope.
2. **Subject line on the envelope:** "Texas §5.0205 Wholesale Disclosure for [property address] — please review and sign"
3. **Sender:** branded as Marcus Cole (operations@everlightventures.io) for TX deals during the Marcus-quarterback period; transitions to Hammer (closing@) once a TX anchor buyer + title partner are signed.
4. **Timing:** delivered BEFORE the recipient signs any related purchase or assignment contract. Pre-contract is statutory; at-contract or post-contract does not satisfy §5.0205.
5. **Both sides required:** seller-side AND end-buyer-side disclosures. Two separate envelopes, one to each party, each signed.
6. **Audit certificate:** DocuSign / Dropbox Sign envelope completion certificate (timestamps + IP + email-open + signed-at) is the audit artifact. Saved as PDF.

---

## Storage + retention

- **Primary:** `Wholesale/audit_kit/01_5_0205_disclosures/<deal_id>/` per the audit binder index.
- **Filename pattern:** `<deal_id>_<recipient_role>_5_0205_disclosure.signed.pdf` (e.g., `tx_dallas_001_seller_5_0205_disclosure.signed.pdf`).
- **Audit certificate:** stored alongside as `<same_basename>.audit_cert.pdf`.
- **Supabase mirror:** `tx_5_0205_disclosures` table, columns `deal_id`, `recipient_email`, `recipient_role`, `signed_at`, `pdf_sha256`, `audit_cert_sha256`, `envelope_provider`, `envelope_id`.
- **Retention:** 7 years from close (DTPA SoL is 4, we hold 7 to cover successor liability).

---

## What changed from v0.1 (errors corrected)

1. **Statute citation:** v0.1 cited §5.086 + §5.0865 (SB 1577 expansion). Both were renumbered into a single §5.0205 by SB 1577. v1.0 cites §5.0205 only.
2. **Effective date:** v0.1 said "SB 1577 (2023)." Bill passed 88R 2023, effective 2024-01-01. v1.0 reflects 2024-01-01.
3. **24-month rescission:** v0.1 asserted SB 1577 created a 24-month seller-rescission right surviving closing. No such right exists in the enrolled statute. v1.0 removes the claim. Penalty for non-disclosure is Class A misdemeanor + DTPA exposure, NOT statutory rescission.
4. **Delivery method:** v0.1 treated a contract paragraph as sufficient. §5.0205 requires a standalone pre-assignment notice with audit-trail signature. v1.0 mandates DocuSign / Dropbox Sign envelope.

---

## Counsel review checklist

Before this v1.0 goes live in any TX deal:

1. **Bernard Calloway (internal regulatory editor)** — review disclosure block language, statutory citations, delivery flow, audit-cert plan. Countersign.
2. **External TX real estate counsel** — review for compliance with §5.0205 + Occ. Code §1101.0045 + DTPA + Insurance Code Chapter 2651. Provide one-page sign-off letter on firm letterhead.
3. **External CA real estate counsel (Carlos Moreno)** — review the wholesaler-license-status sentence to confirm it does not create a CA holding-out risk for Marquise's lapsed CA salesperson license.
4. **Justine Park** — workflow gate audit confirming the DocuSign envelope flow plus the Supabase mirror plus the 7-year retention are wired into the operational pipeline.
5. **Final sign-off:** Marquise Smith approves v1.0 for live use after items 1-4 land. Document filename version-bumps to v1.0 (no DRAFT suffix). Old v0.1 stays SUPERSEDED.

---

## Re-review triggers

This document goes back through the counsel pipeline if:

1. Any amendment to §5.0205, §1101.0045, §1101.758, §17.46, or Insurance Code Chapter 2651.
2. Any TREC bulletin, AG opinion, or published TX appellate opinion materially refining §5.0205 disclosure mechanics.
3. Any change in Marquise's license status (CA reactivation, TX licensure, etc.).
4. Every 18 months from the date of last counsel sign-off, regardless of statutory activity.

---

**THIS IS DRAFT v1.0. NOT FOR LIVE USE. PENDING BERNARD COUNTERSIGN + EXTERNAL TX COUNSEL SIGN-OFF.**
