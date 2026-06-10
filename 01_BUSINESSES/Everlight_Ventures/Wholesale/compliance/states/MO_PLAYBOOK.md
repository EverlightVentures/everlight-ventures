# Missouri — State Playbook

**Last Updated:** 2026-05-05 11:20 PT (2026-05-05T11:20:00-07:00)
**Status:** CONFIGURED, not yet activated. **HB 2517 PENDING SENATE — passed House Apr 9, 2026.** Build disclosure form preemptively.
**Counsel sign-off:** Bernard countersign + external MO counsel pending.

---

## 1. Quick verdict

**Wholesaling is currently LEGAL in MO without a real estate license.** Marketing without ownership = unlicensed brokerage (Class B misdemeanor + $10K civil penalty). **HB 2517 passed the House 130-6 on Apr 9, 2026 and is pending the Senate vote (session ends mid-May 2026)** — would require 14-day pre-contract written disclosure to property owner. Probability of enactment is HIGH. **MO has a 2025 state cap gains exemption (HB 594) but wholesale fees are dealer income — likely INELIGIBLE.**

## 2. Wholesale licensing requirement

- **Statute:** RSMo Ch. 339 (real estate brokerage), enforced by Missouri Real Estate Commission.
- **License:** NOT required to assign equitable interest currently. Marketing the property = unlicensed brokerage.

## 3. Required wholesaler disclosure

- **CURRENT:** No standalone wholesaler statute. Best practice: written equitable-interest disclosure.
- **PENDING — HB 2517** (passed House Apr 9, 2026; Senate pending mid-May):
  - Buyer-wholesaler must disclose IN WRITING to property owner ≥14 DAYS before contract signing.
  - Failure = voidable contract + earnest money refund + private/AG action under Missouri Merchandising Practices Act (MMPA, RSMo §407.020).
- **Operator strategy:** draft the 14-day pre-contract disclosure form NOW. If HB 2517 passes, we're already compliant. If it doesn't, we still ship a defensive disclosure that exceeds best practice.

## 4. Volume thresholds

No published number.

## 5. Surety bond / fee

NONE for wholesaling (current) or under HB 2517 (pending).

## 6. Title closing model

**Hybrid.** Title companies handle most closings; optional 5-day attorney review period customary. Attorney not required.

**Active partners (per `title_companies.json` — st_louis section):**
- **Freedom Title** (314-786-4000, Ryan Kerner) — handles_assignments=true
- **Investors Title Company** (314-862-0303) — handles_assignments=true (50+ years STL)

**RESPA attestations:** PENDING Hammer phone-verify.

## 7. Channel restrictions

| Channel | Status | Conditions |
|---|---|---|
| Email | LEGAL | Disclosure footer + CAN-SPAM |
| Direct mail | LEGAL | Disclosure on the same physical sheet |
| Cold SMS | RESTRICTED | TCPA + MO No Call Law (RSMo §407.1098). Consent + DNC scrub required |
| Cold voice | RESTRICTED | TCPA + MO No Call. Manual dial only |

## 8. Option / inspection period

Contractual; standard 10-day inspection.

## 9. Penalty regime

- **CURRENT:** unlicensed brokerage = Class B misdemeanor + $10,000 civil penalty per violation.
- **POST-HB 2517:** contract voidable + MMPA private action.
- **MMPA (RSMo §407.020):** civil enforcement, treble damages possible, attorney fees.

## 10. Tax economics

- **Personal income tax:** 4.7% top bracket (declining).
- **Capital gains:** **HB 594 (Jan 1, 2025): MO became the FIRST state to fully exempt individual capital gains from state income tax.** 100% subtraction.
- **CRITICAL CAVEAT:** wholesale assignment fees are dealer income (federal ordinary income classification), NOT capital gains. The MO cap gains exemption likely does NOT cover wholesale flips. **Confirm with CPA before relying on the exemption.**
- **State real estate transfer tax:** NONE.
- **Recordation:** county-level only.
- **Wholesale fees:** federal ordinary income + 4.7% MO state (likely; verify with CPA).
- **For buy-and-hold investors:** MO HB 594 is a meaningful incentive — long-term hold + sell qualifies for exemption.

## 11. Best wholesale-friendly metros

1. **Kansas City** — MAREI hub, strong investor community.
2. **St. Louis** — cash flow, distressed inventory.
3. **Springfield** — secondary, lower competition.

## 12. Recent material change (2024-2026)

- **HB 594 (Jan 1, 2025)** — full state cap gains exemption (likely doesn't cover wholesale dealer income).
- **HB 2517 PENDING** — 14-day pre-contract disclosure law. Senate vote due mid-May 2026.

## 13. Active configuration

| Field | Value |
|---|---|
| `state_gates.json` active | (TBD — verify; recommend pause until HB 2517 outcome known) |
| Anchor buyer | NONE — needs Hammer cold-blast for KC + STL |
| Title partners | Freedom Title + Investors Title Company — RESPA letters pending |
| Disclosure file | DRAFT preemptively for HB 2517 (14-day window) |
| Disclosure counsel-signed | NO |
| Closing model | hybrid (title with optional attorney review) |

## 14. Sources

- [MO Rev Stat Ch. 339](https://law.justia.com/codes/missouri/title-xxii/chapter-339/)
- [HB 2517 text](https://documents.house.mo.gov/billtracking/bills261/hlrbillspdf/5859H.01I.pdf)
- [MAREI HB 2517 / SB 973 explainer](https://marei.org/missouri-hb-2517-sb-973-wholesaler-disclosures/)
- [MO DOR Capital Gains Exemption](https://dor.mo.gov/news/newsitem/uuid/15044650-59dd-48f4-975a-01988d485255)
- [Stinson LLP MO CapGains analysis](https://www.stinson.com/newsroom-publications-missouri-eliminates-capital-gains-tax)
- [RSMo §407.020 (MMPA)](https://revisor.mo.gov/main/OneSection.aspx?section=407.020)

## 15. Last counsel review

PENDING — Bernard + external MO counsel. **MO is the highest-priority state for legislative monitoring** due to HB 2517.

---

## Operator notes

- **Watch the MO Senate vote in May 2026.** If HB 2517 passes, the 14-day pre-contract disclosure becomes mandatory. Build the form NOW so we're not caught.
- **Don't bank on the MO cap gains exemption for wholesale.** Confirm with CPA — most likely interpretation is wholesale fees = dealer income = ordinary, not eligible.
- **STL has more distressed inventory than KC; KC has the more sophisticated investor community.** Mid-South Title's STL counterpart could be Freedom Title. Phone-verify both shops.
- **MO is the only state in our list with no state real estate transfer tax** (alongside TX). Closing friction is minimal.
