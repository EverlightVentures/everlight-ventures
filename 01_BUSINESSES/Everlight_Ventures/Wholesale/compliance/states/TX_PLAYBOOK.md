# Texas — State Playbook

**Last Updated:** 2026-05-05 11:15 PT (2026-05-05T11:15:00-07:00)
**Status:** IN BUILD — engineering complete, counsel sign-off + anchor buyer pending
**Counsel sign-off:** v1.0 disclosure DRAFT pending Bernard countersign + external TX counsel.
**Re-review trigger:** TX Legislature meets biennially (odd years); next session 2027.

---

## 1. Quick verdict

**Wholesaling is LEGAL in TX without a real estate license if §5.0205 disclosure is delivered to BOTH seller and end-buyer in writing before assignment.** No surety bond required. No volume ceiling at the wholesaler level. **Best 10-day option period in any state** (TREC paragraph 23). Class A misdemeanor + DTPA exposure for non-disclosure.

## 2. Wholesale licensing requirement

- **Statute:** Tex. Occ. Code Ch. 1101 (real estate brokerage) + §1101.0045 (equitable-interest carve-out).
- **License required:** NO if §5.0205 disclosure is delivered + wholesaler holds equitable interest as principal.
- **License required (act as broker):** YES — marketing the property itself (not the contract) for a fee crosses into brokerage.
- **Operator status:** Marquise operates as principal-buyer + assignor; license not required.

## 3. Required wholesaler disclosure

- **Statute:** **Tex. Prop. Code §5.0205** (renumbered from §5.086 by SB 1577, effective Jan 1 2024).
- **What:** Wholesaler must disclose IN WRITING that:
  1. Selling only an option or assigning interest in a contract (not legal title).
  2. Does not own legal title to the property.
- **To whom:** BOTH seller AND end-buyer/assignee.
- **When:** BEFORE assignment contract executes; pre-contract delivery is best practice.
- **Surface:** Standalone written notice (DocuSign/Documenso envelope with audit cert). Three compliant methods:
  1. "and/or assigns" in original PSA
  2. Assignment provision added to PSA
  3. Standalone written notice between PSA execution and assignment ← **PREFERRED**
- **Penalty for non-disclosure:** Class A misdemeanor under Occ. Code §1101.758 + DTPA exposure (Tex. Bus. & Com. Code §17.46) + common-law fraud.

## 4. Volume thresholds

- **No published threshold.** §5.0205 codifies disclosure for every transaction.
- **No volume ceiling at wholesaler level.** TX scales freely as long as disclosure is delivered properly.

## 5. Surety bond / fee

- **NO bond required for wholesaling.**
- **TX SB 140 (effective Sep 1, 2025):** cold SMS bond requirement for unsolicited text marketing. Specific amount + scope to confirm with TX counsel before scaling SMS. **Operating posture: do NOT do cold SMS in TX until confirmed.**
- **SB 1577 LLC/S-Corp registration option** for license holders ($140 + $70 renewal) — does not apply to unlicensed wholesalers.

## 6. Title closing model

- **Title/escrow state.** Closings via title agencies licensed under TX Insurance Code Chapter 2651.
- **Active partners (per `title_companies.json`):**
  - **1st Option Title** (Garland, Scott Horne attorney+investor) — PRIMARY
  - **Patten Title Houston** — secondary
  - **Affinity Title LLC** (DFW) — backup
- **RESPA attestations:** ALL pending Hammer phone-verify.

## 7. Channel restrictions

| Channel | Status | Conditions |
|---|---|---|
| Email | LEGAL | §5.0205 disclosure footer + CAN-SPAM |
| Direct mail | LEGAL | Disclosure on the same physical sheet |
| Cold SMS | BLOCKED | TX SB 140 (eff. 2025-09-01) — bond + Secretary of State telephone-solicitor registration required |
| Cold voice | RESTRICTED | TCPA + Tex. Bus. & Com. Code §305.053 — consent + DNC scrub required; manual dial only on cold leads |
| Inbound voice | LEGAL | One-party consent state for recording |

## 8. Option / inspection period

- **TREC paragraph 23 standard 10-day option period** — strongest unilateral termination right in any state.
- **Option fee:** negotiated $200-500 non-refundable, paid directly to seller.
- **Earnest money:** held by title agent, fully refundable through option period.
- **Wholesaler use:** insist on max option period in PSA + explicit "and/or assigns" language. Option period is the assignment safety window.

## 9. Penalty regime

- **§5.0205 non-disclosure:** Class A misdemeanor under Occ. Code §1101.758 (each offense; multiple = felony).
- **Civil:** DTPA (§17.46) — actual damages + treble where willful + mental anguish + attorney fees.
- **TREC admin:** $100-1,500/day for Obligation to Respond Timely violations (relevant if licensed; not for unlicensed wholesaler).

## 10. Tax economics

- **Personal income tax:** 0% (NO state income tax).
- **Capital gains:** 0% — Proposition 2 (2025) constitutionally prohibits future state CGT on individuals/estates/trusts.
- **State transfer tax / doc stamp:** NONE.
- **Recordation:** county-level only (~$10-50 per document).
- **Margin tax (state corp):** kicks in only above $1.23M revenue (Marquise far below).
- **Wholesale fees:** federal ordinary income (dealer income); ZERO state tax burden.
- **TX is the cleanest state for wholesale margin economics.**

## 11. Best wholesale-friendly metros

1. **Dallas-Fort Worth** — #1 market 2026 ULI/PwC ranking. 1st Option Title (Garland) is local. Most active wholesale community.
2. **Houston** — most diverse deal flow. Patten Title (Houston) is local.
3. **San Antonio** — highest yields, military renter base.
4. **Austin** — corrected market (post-2022 cooldown), creative plays now profitable.

## 12. Recent material change (2024-2026)

- **§5.0205 renumbering + SB 1577** effective Jan 1, 2024.
- **SB 140 cold SMS bond** effective Sep 1, 2025.
- **TX Proposition 2 (Nov 2025)** — constitutionally prohibits future state CGT.

## 13. Active configuration (as of 2026-05-05)

| Field | Value |
|---|---|
| `state_gates.json` active | true |
| `wholesale_legal_status` | legal_unlicensed_with_disclosures |
| `sb1577_required` | true |
| `arv_in_writing_to_seller_allowed` | false |
| `risk_rating` | high (until v1.0 disclosure cleared) |
| Anchor buyer | NONE YET — 10-target seed CSV ready for Hammer cold-blast |
| Title partner (DFW) | 1st Option Title (Scott Horne) — RESPA letter pending |
| Title partner (Houston) | Patten Title — RESPA letter pending |
| Disclosure file | `compliance/states/TX_5_0205_DISCLOSURE_v1.0_DRAFT.md` (DRAFTED today) |
| Disclosure counsel-signed | NO (Bernard countersign pending; external TX counsel pending) |
| Lead inventory | 409 leads in pipeline |
| First close target | end of week 3 (after v1.0 sign-off + anchor buyer + RESPA letters) |

## 14. Sources

**Statute / official:**
- [TX Tex. Prop. Code §5.0205 / SB 1577](https://capitol.texas.gov/tlodocs/88R/analysis/html/SB01577F.htm)
- [TX SB 1577 introduced text](https://capitol.texas.gov/tlodocs/88R/billtext/html/SB01577I.htm)
- [TREC SB 1577 article](https://www.trec.texas.gov/article/want-receive-your-compensation-through-llc-or-s-corp-there%E2%80%99s-new-option-coming-january-2024)
- [Tex. Prop. Code §5.0205 Justia](https://texas.public.law/statutes/tex._prop._code_section_5.0205)
- [Tex. Occ. Code §1101.0045](https://texas.public.law/statutes/tex._occ._code_section_1101.0045)
- [Texas Proposition 2 (Ballotpedia)](https://ballotpedia.org/Texas_Proposition_2,_Prohibit_Capital_Gains_Tax_on_Individuals,_Estates,_and_Trusts_Amendment_(2025))
- [TRERC: New Texas Assignment Law](https://trerc.tamu.edu/article/new-texas-assignment-law-what-buyers-and-sellers-need-to-know/)

**Commentary (2024-2026):**
- [LoneStarLandLaw: Wholesaling in Texas](https://lonestarlandlaw.com/wholesaling-in-texas-real-estate/)
- [Real Estate Skills TX wholesaling 2026](https://www.realestateskills.com/blog/wholesaling-real-estate-legal-texas)
- [TX wholesale market guide 2025](https://wholeselltx.com/articles/texas-market-guide.html)
- [Creekstone: Option Period in Texas (2026)](https://www.creekstonere.com/option-period-texas/)

## 15. Last counsel review

- **Bernard countersign:** PENDING — v1.0 §5.0205 disclosure draft ready for review at `compliance/TX_5_0205_DISCLOSURE_v1.0_DRAFT.md`.
- **External TX counsel:** PENDING — recommended before first live deal. Best-practice but not statutorily required per §5.0205.
- **Justine workflow gate:** PASSED 2026-05-04 after Forge round-2 remediation.

---

## Operator notes (for Marquise)

- **Tax advantage:** zero state income tax + zero state CGT + zero state transfer tax = **TX has the cleanest wholesale margin in the country.** Combined with §5.0205 carve-out and 10-day option period, TX is structurally the best operating state for high-volume wholesale.
- **The 409 leads:** sitting in `Wholesale/prospecting/TX_prospects.csv`. ~30 marked status=contacted from 2026-03-21 with zero replies — likely SMS-tainted under SB 140. Audit + purge SMS-touched leads before re-engagement.
- **Anchor buyer is the unblock:** Hammer's 10-target B2B cold-blast (held until pristine ship) lands an anchor in 14-21 days. Without an anchor, every TX seller "yes" is a deal we can't close.
- **§5.0205 form factor matters:** Bernard's research shows the statute requires standalone pre-assignment notice. "and/or assigns" buried in PSA is NOT enough. Documenso envelope is the audit-defensible mode.
- **DTPA verb scrub:** Bernard flagged "we will buy" copy as DTPA exposure. Already cleaned at the template level + send-time gate. Confirm before any TX outbound.
