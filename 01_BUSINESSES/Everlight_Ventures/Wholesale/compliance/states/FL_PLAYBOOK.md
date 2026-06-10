# Florida — State Playbook

**Last Updated:** 2026-05-05 11:20 PT (2026-05-05T11:20:00-07:00)
**Status:** CONFIGURED, not yet activated. Need anchor buyer + RESPA letter from title partner.
**Counsel sign-off:** Bernard countersign + external FL counsel pending.

---

## 1. Quick verdict

**Wholesaling is LEGAL in FL without a real estate license.** No wholesaler-specific disclosure statute; best practice is written equitable-interest disclosure. Acting as broker for non-owned property = third-degree felony under Fla. Stat. §475.42. **Florida Mini-TCPA §501.059 is the most aggressive in the country** — class action exposure on cold SMS. **No state income tax. Doc stamp tax $0.70/$100 (highest closing friction in our priority states).**

## 2. Wholesale licensing requirement

- **Statute:** Fla. Stat. Ch. 475 (real estate brokerage).
- **License:** NOT required to wholesale equitable interest.
- **Penalty for acting as broker:** Third-degree felony under §475.42.

## 3. Required wholesaler disclosure

- **No wholesaler-specific statute** (unlike TX §5.0205 or TN SB 909).
- **Fla. Stat. §475.278** governs licensee single-agent/transaction-broker disclosures (does NOT apply to unlicensed wholesalers).
- **Best practice:** standalone written disclosure of equitable-interest position via Documenso.

## 4. Volume thresholds

No published number. "Engaged in business" doctrine — marketing the property itself triggers broker classification.

## 5. Surety bond / fee

NONE for wholesaling.

## 6. Title closing model

**Title/escrow state.** Most closings via title agency. Attorneys frequently own title companies.

**Active partners (per `title_companies.json` — jacksonville section):**
- **Marina Title** (855-513-5880, Info@MarinaTitle.com) — handles_assignments=true, explicitly serves wholesalers
- **FL Title Closings** (1-833-FL-TITLE) — handles_assignments=true, serves investors, wholesalers, iBuyers

**RESPA attestations:** PENDING Hammer phone-verify.

## 7. Channel restrictions

| Channel | Status | Conditions |
|---|---|---|
| Email | LEGAL | Equitable-interest disclosure footer + CAN-SPAM |
| Direct mail | LEGAL | Disclosure on the same physical sheet |
| Cold SMS | **HIGH RISK** | Florida Mini-TCPA §501.059 — prior express written consent + 3 attempts/24h limit + 8a-8p local. $500-$1500/violation, class action exposure |
| Cold voice | **HIGH RISK** | Same Mini-TCPA constraints as SMS |

## 8. Option / inspection period

Contractual; FAR/BAR contract = 15-day inspection default; "AS IS" addendum = inspection-only termination right.

## 9. Penalty regime

- **Unlicensed brokerage:** Third-degree felony under §475.42 — up to 5 years prison + $5,000 fine.
- **Civil:** Florida Deceptive and Unfair Trade Practices Act (FDUTPA Ch. 501 Pt. II) — actual damages + attorney fees.
- **Mini-TCPA §501.059:** $500/violation, $1,500 if willful, class action eligible.

## 10. Tax economics

- **Personal income tax:** 0% (NO state income tax).
- **Capital gains:** 0%.
- **Documentary stamp tax (deed):** **$0.70 per $100 of consideration** (all counties except Miami-Dade = $0.60/$100 + $0.45 surtax for non-single-family).
- **Intangible tax (mortgage):** $0.20/$100.
- **Recording fee:** per page.
- **Wholesale fees:** federal ordinary income only.
- **NOTE:** FL has the highest closing friction in our priority states due to doc stamp tax. Negotiate who pays in PSA.

## 11. Best wholesale-friendly metros

1. **Jacksonville** — best balance of affordability + buyer demand.
2. **Tampa** — large market but **wholesaler-saturated**.
3. **Orlando** — saturated.
4. **Secondary plays (better margin):** Polk, Pasco, Lee, Citrus counties.

## 12. Recent material change (2024-2026)

- **No 2024-2026 wholesaler-specific statute.**
- **Mini-TCPA continues to drive litigation** (Florida Telephone Solicitation Act).
- **2023 amendment** narrowed but did not eliminate exposure.

## 13. Active configuration

| Field | Value |
|---|---|
| `state_gates.json` active | (TBD — verify) |
| Anchor buyer | NONE — needs Hammer cold-blast for FL turnkey operators |
| Title partners | Marina Title + FL Title Closings — RESPA letters pending |
| Disclosure file | TBD (`compliance/states/FL_DISCLOSURE_v1.0_DRAFT.md`) |
| Disclosure counsel-signed | NO |
| Closing model | title-company |

## 14. Sources

- [Fla. Stat. §475.278](https://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0400-0499%2F0475%2FSections%2F0475.278.html)
- [Fla. Stat. §501.059 (Mini-TCPA)](https://www.leg.state.fl.us/Statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0501/Sections/0501.059.html)
- [FL DOR Doc Stamp Tax](https://floridarevenue.com/taxes/taxesfees/Pages/doc_stamp.aspx)
- [Mini-TCPA McGuireWoods 2023 amendments](https://www.mcguirewoods.com/client-resources/alerts/2023/5/pro-business-amendments-to-floridas-mini-tcpa-now-in-effect/)
- [Holland & Knight FL Mini-TCPA](https://www.hklaw.com/en/insights/publications/2021/07/floridas-new-mini-tcpa-what-you-need-to-know)
- [Morrison Foerster FTSA litigation 2024](https://www.mofo.com/resources/insights/241111-uptick-in-florida-telephone-solicitation-act-litigation)

## 15. Last counsel review

PENDING — Bernard + external FL counsel.

---

## Operator notes

- **Mini-TCPA is the #1 risk in FL.** Class action lawyers actively chase wholesalers. **Email + direct mail only in FL.** No SMS, no cold voice without ironclad prior express written consent.
- **FL doc stamp at $0.70/$100 means $700 closing tax per $100K of price.** Negotiate who pays in PSA. Many sellers expect to pay; some buyers contest.
- **Tampa/Miami/Orlando are saturated.** Jacksonville is the best-margin major metro. Secondary counties (Polk, Pasco, Lee, Citrus) have less wholesaler competition.
- **Tax advantage:** zero state income tax. Marquise FL residency is competitive with TN/TX for personal tax.
- **Closing-friction strategy:** larger deals justify the doc stamp; very small deals (<$50K) may not pencil after $350+ doc stamp. Set min deal size accordingly.
