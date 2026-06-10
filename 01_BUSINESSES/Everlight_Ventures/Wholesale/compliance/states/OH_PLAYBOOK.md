# Ohio — State Playbook

**Last Updated:** 2026-05-05 11:25 PT (2026-05-05T11:25:00-07:00)
**Status:** CONFIGURED, **HARD DEADLINE — SB 155 effective Mar 1, 2026.** Disclosure form required before then.
**Counsel sign-off:** Bernard countersign + external OH counsel pending.

---

## 1. Quick verdict

**Wholesaling is LEGAL in OH without a real estate license.** **OH SB 155 (signed Dec 1, 2025; EFFECTIVE Mar 1, 2026) requires written wholesaler disclosure to property owner, signed+dated by both, BEFORE contract execution.** Penalty stack: REC sanctions + private CSPA lawsuit (up to $5K statutory + treble) + AG civil penalty up to $25K/violation + $5K/day for injunction violations. **~10 months runway from today to Mar 1, 2026 deadline.**

## 2. Wholesale licensing requirement

- **Statute:** ORC Chapter 4735 (real estate brokerage).
- **License:** NOT required to wholesale (S.B. 155 explicitly stops short of licensure).
- **Marketing the property = unlicensed brokerage.**

## 3. Required wholesaler disclosure

- **Statute:** **OH SB 155** (signed Dec 1, 2025; EFFECTIVE Mar 1, 2026).
- **What:** Written disclosure form must declare:
  1. Buyer is a wholesaler.
  2. Lack of disclosure is a cause of action.
  3. Contract cannot be signed prior to disclosure execution.
- **To whom:** Property owner.
- **When:** BEFORE contract execution. Owner must sign + date disclosure FIRST.
- **Surface:** Standalone written form. Documenso envelope with audit cert is the audit-defensible mode.

## 4. Volume thresholds

Any wholesale transaction triggers disclosure. No de minimis exception.

## 5. Surety bond / fee

NONE for wholesaling.

## 6. Title closing model

**Title/escrow state.** Title agencies handle closings; attorneys optional.

**Active partners (per `title_companies.json` — cleveland section):**
- **Black Tie Title** (216-333-1295, sales@blacktietitle.net) — handles_assignments=true, "incredibly investor-friendly"
- **Ohio Real Title Agency** (866-373-9900, info@ohiorealtitle.com) — handles_assignments=true, BiggerPockets-recommended

**RESPA attestations:** PENDING Hammer phone-verify.

## 7. Channel restrictions

| Channel | Status | Conditions |
|---|---|---|
| Email | LEGAL | SB 155 disclosure footer + CAN-SPAM |
| Direct mail | LEGAL | Disclosure on the same physical sheet |
| Cold SMS | RESTRICTED | TCPA + Ohio Telephone Solicitation Sales Act (ORC §4719). Express written consent required |
| Cold voice | RESTRICTED | TCPA + ORC §4719. DNC scrub + manual dial only |

## 8. Option / inspection period

Contractual; OAR contract = standard 7-14 day inspection.

## 9. Penalty regime (HEAVY post-Mar 2026)

**SB 155 violation triggers THREE consequences simultaneously:**

1. **Ohio Real Estate Commission (REC) disciplinary sanctions** — even though wholesaler is unlicensed, REC can issue cease-and-desist + administrative penalties.
2. **Private CSPA lawsuit** by property owner — actual damages + up to $5,000 statutory + **treble damages where willful**.
3. **Ohio AG action under CSPA** — civil penalty up to **$25,000 per violation** + **$5,000/day for injunction violations**.

**Plus:** unlicensed brokerage if marketing crosses into broker activity = misdemeanor under ORC §4735.

## 10. Tax economics

- **Personal income tax:** 0-3.125% graduated (2025); flat 2.75% above $26,050 starting 2026.
- **Capital gains:** taxed as ordinary income.
- **Local income tax:** many cities impose 1-3% (e.g., Cleveland 2.5%, Columbus 2.5%).
- **Real estate conveyance fee:** $1 per $1,000 state + up to $3 per $1,000 county permissive (varies by county). Total ~0.10-0.40%.
- **Wholesale fees:** federal ordinary income + 2.75% OH state + local city tax (can total 5%+).

## 11. Best wholesale-friendly metros

1. **Cleveland** — cash flow + distressed inventory. Black Tie + Ohio Real Title both based here.
2. **Columbus** — population growth, Intel campus driving demand.
3. **Cincinnati** — stable yields.
4. **Dayton** — secondary, lower competition.

## 12. Recent material change (2024-2026)

- **OH SB 155** (Dec 1, 2025 signed; Mar 1, 2026 effective) — major operator-impact change.
- Replaces older HB 532 framework on wholesale-specific issue.

## 13. Active configuration

| Field | Value |
|---|---|
| `state_gates.json` active | (TBD — verify) |
| Anchor buyer | NONE — needs Hammer cold-blast for Cleveland + Columbus |
| Title partners | Black Tie Title + Ohio Real Title Agency — RESPA letters pending |
| Disclosure file | TBD (`compliance/states/OH_DISCLOSURE_v1.0_DRAFT.md`) — **MUST EXIST BY MAR 1, 2026** |
| Disclosure counsel-signed | NO |
| Closing model | title-company |

## 14. Sources

- [Ohio LSC SB 155 analysis (Dec 23, 2025)](https://www.legislature.ohio.gov/download?key=26902)
- [Ohio LSC SB 155 analysis (Oct 29, 2025)](https://www.legislature.ohio.gov/download?key=26368)
- [Richland Source: Ohio lawmakers approve wholesaling bill](https://www.richlandsource.com/2025/11/30/ohio-lawmakers-approve-bill-on-real-estate-wholesaling/)
- [American Homeland Title — Ohio Wholesaling Rules](https://americanhomelandtitle.com/ohio-real-estate-wholesaling-rules/)
- [Ohio HB 532 (Ohio REALTORS)](https://www.ohiorealtors.org/ohio-hb-532-resources/)

## 15. Last counsel review

PENDING — Bernard + external OH counsel. **Hard deadline: must clear before Mar 1, 2026.**

---

## Operator notes

- **OH penalty stack is the heaviest of any non-license state:** REC + CSPA + AG = three separate enforcement bodies all empowered. Single SB 155 violation = $25K AG + $5K statutory + treble = potentially $80K+ exposure per misstep.
- **Build the OH disclosure form NOW.** Not negotiable. 10 months runway.
- **Cleveland has the best wholesale infrastructure** of OH metros (Black Tie + Ohio Real Title both local). Columbus is the growth lane (Intel + tech) but newer to wholesale.
- **Tax burden is real:** OH state 2.75% + local city 1-3% = 4-6% combined. Marquise residency in TN/TX/FL keeps wholesale margin clean even when wholesaling OH properties.
