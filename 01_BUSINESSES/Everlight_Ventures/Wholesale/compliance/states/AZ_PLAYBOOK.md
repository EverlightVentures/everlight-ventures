# Arizona — State Playbook

**Last Updated:** 2026-05-05 11:25 PT (2026-05-05T11:25:00-07:00)
**Status:** CONFIGURED, not yet activated. Need anchor buyer + RESPA letter from title partner.
**Counsel sign-off:** Bernard countersign + external AZ counsel pending.

---

## 1. Quick verdict

**Wholesaling is LEGAL in AZ — strongest statutory clarity in the country** under A.R.S. §32-2122 (selling equitable interest in contract is NOT brokerage). **A.R.S. §44-5101 (HB 2747, eff. Sep 24, 2022)** requires written wholesaler disclosure to seller (and from seller-wholesaler to end buyer) BEFORE binding contract is signed. AZ courts have rescinded contracts even where end-buyer was satisfied. **Flat 2.5% state income tax + 25% LTCG subtraction** = effective 1.875% on long-term gains. **No state real estate transfer tax.** Standard 10-day inspection period.

## 2. Wholesale licensing requirement

- **Statute:** A.R.S. §32-2122 (real estate brokerage) + §32-2101 exemption for principal-buyer.
- **License:** NOT required to wholesale equitable interest. Strongest carve-out language in any state.
- **Marketing the property = unlicensed brokerage.**

## 3. Required wholesaler disclosure

- **Statute:** **A.R.S. §44-5101** (HB 2747, effective Sep 24, 2022).
- **What:** Wholesale buyer must disclose IN WRITING to seller, BEFORE binding contract is signed, that buyer is a wholesaler. Wholesale seller (assigning to end buyer) must also disclose.
- **To whom:** Seller (pre-contract) AND end buyer (pre-assignment).
- **When:** BEFORE the binding contract is signed.
- **Surface:** Standalone written notice. Documenso envelope is the audit-defensible mode.
- **Applies to:** Residential property with <5 dwelling units.

## 4. Volume thresholds

§44-5101 applies to every transaction; no de minimis exception.

## 5. Surety bond / fee

- NO bond for wholesalers.
- Telephone solicitor must register with AZ Secretary of State if cold-calling.

## 6. Title closing model

**Title/escrow state.** Closings handled by escrow officers at title companies. Attorney not required.

**Active partners:** TBD — Phoenix and Tucson title shops not yet added to `title_companies.json`. Hammer needs to source 2 wholesale-friendly title agencies.

## 7. Channel restrictions

| Channel | Status | Conditions |
|---|---|---|
| Email | LEGAL | §44-5101 disclosure footer + CAN-SPAM |
| Direct mail | LEGAL | Disclosure on the same physical sheet |
| Cold SMS | RESTRICTED | TCPA + AZ HB 2498 (2022) prohibits text solicitations to DNC numbers without consent. AG can fine up to $1,000/violation |
| Cold voice | RESTRICTED | Federal TCPA + AZ Secretary of State telephone solicitor registration |

## 8. Option / inspection period

Contractual. **AAR (Arizona Association of Realtors) standard contract = 10-day inspection** — same as TX TREC paragraph 23.

## 9. Penalty regime

- **§44-5101 violation:** unlawful practice under Arizona Consumer Fraud Act (§44-1521 et seq.).
- **AZ courts have rescinded contracts even where end-buyer was satisfied** — judicial willingness to enforce strict.
- **Civil only** under §44-5101 (no criminal). Damages + attorney fees + injunctive relief.
- **Unlicensed brokerage** if crosses into broker activity = separate enforcement under §32-2122.

## 10. Tax economics

- **Personal income tax:** **2.5% flat** (2023 tax reform — one of the lowest in the country).
- **Capital gains:** taxed as ordinary income BUT 25% subtraction for long-term gains = **effective 1.875%** on LTCG.
- **Jan 1, 2026:** 25% LTCG subtraction expands to ALL long-term gains regardless of acquisition date.
- **State real estate transfer tax:** NONE.
- **Recordation fee:** per page only (~$10-30).
- **Doc fee on land transfers:** $2.20 per $250 (only on UNIMPROVED land — does NOT apply to improved residential property).
- **Wholesale fees:** federal ordinary income + 2.5% AZ state.

## 11. Best wholesale-friendly metros

1. **Phoenix** — largest market, ~$445K median, highest deal flow.
2. **Tucson** — ~$311K median, easier entry for new wholesalers.
3. **Maricopa, Pima, Pinal counties** — highest foreclosure activity = highest distressed inventory.

## 12. Recent material change (2024-2026)

- **Jan 1, 2026:** 25% LTCG subtraction expands to all long-term gains regardless of acquisition date.
- **Courts continuing to enforce §44-5101 rescission rights** — judicial trend favors strict construction.

## 13. Active configuration

| Field | Value |
|---|---|
| `state_gates.json` active | (TBD — verify) |
| Anchor buyer | NONE — needs Hammer cold-blast for Phoenix turnkey operators |
| Title partners | NEEDS SOURCING — Phoenix + Tucson |
| Disclosure file | TBD (`compliance/states/AZ_DISCLOSURE_v1.0_DRAFT.md`) |
| Disclosure counsel-signed | NO |
| Closing model | title-company |

## 14. Sources

- [A.R.S. §44-5101](https://www.azleg.gov/ars/44/05101.htm)
- [A.R.S. §44-5101 Justia 2025](https://law.justia.com/codes/arizona/title-44/section-44-5101/)
- [HB 2747 Senate Fact Sheet](https://www.azleg.gov/legtext/55leg/2R/summary/S.2747COM.DOCX.htm)
- [DealRun AZ compliance guide](https://dealrun.ai/compliance/arizona)
- [Arizona TCPA / DropCowboy](https://www.dropcowboy.com/state-compliance/az)
- [AZ Capital Gains 2025 (Valur)](https://learn.valur.com/arizona-capital-gains-tax/)
- [Gottlieb Law AZ disclosure 2025](https://gottlieblawaz.com/2025/07/21/arizona-real-estate-disclosure-laws/)

## 15. Last counsel review

PENDING — Bernard + external AZ counsel.

---

## Operator notes

- **AZ has the cleanest statutory carve-out in the country** — §32-2122 explicitly says equitable-interest assignment is NOT brokerage. Easiest state to defend against unlicensed-brokerage claims.
- **§44-5101 has teeth** — judicial rescission remedy even with happy end-buyer. Compliance is mandatory, not optional.
- **Tax advantage:** 2.5% flat is the lowest non-zero state. AZ residency keeps wholesale margin almost as clean as TN/TX/FL.
- **Title sourcing is a TODO** — Phoenix has many wholesale-friendly shops; Hammer needs to phone-source 2 and add them to `title_companies.json`.
- **Phoenix wholesale community is mature.** Differentiate via clean compliance + faster close + branded touchpoints.
- **AZ + TX combination** is the strongest two-state operating posture in the country: lowest-friction taxes, clearest statutory carve-outs, longest option periods (10 days both).
