# Georgia — State Playbook

**Last Updated:** 2026-05-05 11:20 PT (2026-05-05T11:20:00-07:00)
**Status:** CONFIGURED, not yet activated. Need anchor buyer + RESPA letter from title partner.
**Counsel sign-off:** Bernard countersign + external GA counsel pending.

---

## 1. Quick verdict

**Wholesaling is LEGAL in GA without a real estate license.** Assignment fee must be disclosed to all parties per GREC Rule 520-1-.10. **GA is an ATTORNEY-CLOSING state** — every closing must be conducted by a licensed GA attorney (different operational pattern than TX/FL/TN). Flat 5.39% state income tax. $1+$0.10/$100 transfer tax.

## 2. Wholesale licensing requirement

- **Statute:** O.C.G.A. §43-40-1 (real estate brokerage).
- **License:** NOT required to assign equitable interest. Marketing the property itself = unlicensed brokerage.

## 3. Required wholesaler disclosure

- **GREC Rule 520-1-.10** — assignment fee must be disclosed to all parties.
- **No standalone wholesaler statute** (unlike TX §5.0205 or TN SB 909).
- **Best practice:** standalone written notice via Documenso, signed by all parties, archived.

## 4. Volume thresholds

No published number. Doctrine-based ("engaged in business" via marketing the property crosses into brokerage).

## 5. Surety bond / fee

NONE required for unlicensed wholesalers.

## 6. Title closing model

**ATTORNEY CLOSING STATE.** O.C.G.A. §15-19-51 + GA Supreme Court precedent — only a licensed GA attorney can conduct a real estate closing. Title insurance issued through attorney's title office.

**Active partners (per `title_companies.json` — atlanta section):**
- **Katz Durell LLC** (Joshua Katz, 404-487-0040) — handles_assignments=true
- **Bagwell & Associates PC** (678-528-1908) — handles_assignments=true, free initial consultation

**RESPA attestations:** PENDING Hammer phone-verify.

## 7. Channel restrictions

| Channel | Status | Conditions |
|---|---|---|
| Email | LEGAL | GREC Rule 520-1-.10 disclosure footer + CAN-SPAM |
| Direct mail | LEGAL | Disclosure on the same physical sheet |
| Cold SMS | RESTRICTED | TCPA + GA Telephone Solicitations Act + FCC one-to-one consent (Jan 2025) |
| Cold voice | RESTRICTED | TCPA + DNC scrub required; manual dial only |

## 8. Option / inspection period

Contractual; GAR contract due-diligence period typically 7-14 days.

## 9. Penalty regime

- **Unlicensed brokerage:** misdemeanor under §43-40-30, fine up to $1,000 per violation.
- **Civil:** GREC enforcement + Georgia Fair Business Practices Act private right of action.

## 10. Tax economics

- **Personal income tax:** 5.39% flat (2025), 5.19% (2026).
- **Capital gains:** taxed as ordinary income.
- **Real estate transfer tax:** $1 first $1,000 + $0.10 per additional $100 (~0.10%, paid by seller typically).
- **Intangible recording tax:** $1.50 per $500 of mortgage value (0.30%); cap $25,000/note.
- **HB 586 (Jul 1, 2025):** loans ≤62 months exempt from intangible tax (was 36 months).
- **Wholesale fees:** federal ordinary income + 5.39% GA state.

## 11. Best wholesale-friendly metros

1. **Atlanta MSA** — dominant. Submarkets: Stone Mountain, Decatur, Marietta, Lithonia.
2. **Augusta** — secondary, lower competition.
3. **Macon** — emerging.
4. **Savannah** — coastal, niche.

## 12. Recent material change (2024-2026)

- **HB 586 (2025)** — intangible tax exemption expansion.
- **No new GA wholesaler-specific statute** in this window.

## 13. Active configuration

| Field | Value |
|---|---|
| `state_gates.json` active | (TBD — verify) |
| Anchor buyer | NONE — needs Hammer cold-blast for Atlanta turnkey operators |
| Title partners | Katz Durell + Bagwell & Associates — RESPA letters pending |
| Disclosure file | TBD (`compliance/states/GA_DISCLOSURE_v1.0_DRAFT.md`) |
| Disclosure counsel-signed | NO |
| Closing model | attorney-closing |

## 14. Sources

- [O.C.G.A. Title 43 Ch. 40](https://law.justia.com/codes/georgia/title-43/chapter-40/)
- [GA DOR Real Estate Transfer Tax](https://dor.georgia.gov/real-estate-transfer-tax)
- [GA HB 586 Intangible Tax Update](https://www.bbga.com/articles/new-georgia-law-extends-intangible-tax-exemption-period-for-real-estate-loans/)
- [GA attorney closing requirement (Brian Douglas Law 2025)](https://www.atlantagaestateplanning.com/blog/2025/10/08/what-is-georgias-attorney-closing-requirement/)
- [Holland & Knight 2025 GA legislative update](https://www.hklaw.com/en/insights/publications/2025/08/georgia-legislative-session-brings-changes-to-code-affecting)

## 15. Last counsel review

PENDING — Bernard + external GA counsel.

---

## Operator notes

- **Attorney-closing state means +5-7 days to timeline + $750-1,500 attorney closing fee per deal.** Plan that into MAO calculations.
- **Atlanta wholesale community is mature** — competition is real. Differentiate via cleaner contracts, faster close, branded touchpoints.
- **GA tax burden is real** — 5.39% state income tax adds 5.39% to every wholesale dollar earned by a GA resident. If Marquise residency is in TN or TX, only the property-side closing taxes apply (transfer tax + recording).
