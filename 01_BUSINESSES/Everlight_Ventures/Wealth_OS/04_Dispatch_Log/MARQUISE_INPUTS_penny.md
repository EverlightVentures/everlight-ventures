# Inputs Required from Marquise to Tighten the 947k Model

**From:** Penny Liang, Financial Safeguard
**Date:** 2026-04-25
**Purpose:** Convert the theoretical 12-month model in `penny_2026_04_25_947k_math.md` into an operational forecast. Sorted by impact: highest-leverage input first.

Every assumption in the math file is a guess until you confirm. Each line below states which assumption it tightens. Answer them in order, top to bottom.

---

**1. Realistic productive hours per week, no fluff** -- What: hours/week Marquise can spend on revenue-generating work (sales calls, build delivery, deal disposition), not infra/research/learning | Why: drives wholesale dispatch volume, AI build capacity, and whether VA hire moves from "nice-to-have" to "month-3 forced move". 50hrs/wk is the prompt assumption, but if real number is 25 the BASE case drops 40%. | Format: integer hours, single number.

**2. Bank balance today** -- What: liquid USD across all checking/savings/Cash App/Venmo right now | Why: determines runway months, whether the $2,500-3,000 unlock-cascade tool stack is reachable before Deal 1 or strictly after, and how aggressively WORST can be tolerated. | Format: number to the dollar.

**3. Available credit limit AND current credit utilization** -- What: total credit limit across all open cards + current balance owed | Why: gates whether direct mail spend ($0.85 per yellow letter, 500-letter test = $425), Lob credit, ATTOM API, and DocuSign can be float-financed before commission lands. Affects WORST and BASE scenarios where Deal 1 timing slips. | Format: two numbers, "limit / utilization".

**4. Personal monthly burn** -- What: rent/mortgage, food, transport, insurance, phone, minimum debt payments. The "I will go homeless if I do not earn this" floor. | Why: divides cash projections by personal runway. Determines how many months WORST case can be tolerated before forced pivot. | Format: number per month.

**5. AI Consulting pipeline count today, by stage** -- What: how many real prospects exist right now at each stage: cold-contacted / responded / discovery-call-booked / discovery-call-completed / proposal-sent / closed | Why: the $3,500/mo AI builds in BASE assume warm pipeline by M2. If pipeline is 0 today, M1-M2 build revenue is fiction and BASE shifts right by 60 days. | Format: 6 integers in stage order.

**6. Current wholesale deals under contract or close to contract** -- What: any property currently under contract, in PSA negotiation, or with a verbal agreement | Why: the M2-M3 first wholesale close drives the entire funding cascade. If there is nothing at PSA stage today, M3 close is unlikely and BASE's $30k cash by M3 collapses. | Format: count + closest stage + estimated assignment fee.

**7. License reinstatement timeline AND cost** -- What: weeks until RE license is active again + reinstatement fee | Why: blocks any wholesale activity outside Cleveland boomerang strategy in license-required states. Hard gate on M1-M3 WORST case revenue. | Format: weeks (integer) + dollar fee.

**8. Onyx POS and Hive Mind paying clients today** -- What: count of currently paying customers on each product, and the actual MRR they contribute | Why: BASE assumes $0 today. If real MRR is $200, that adds $2,400/yr immediately and lifts the floor. If it is $0 confirmed, then SaaS forecast starts cold. | Format: two pairs of "client count / MRR".

**9. Stripe account status** -- What: is Stripe live, can it accept payments today, any holds or restrictions, last payout date | Why: gates ability to collect AI consulting deposits and SaaS subs in M1. A frozen or unactivated Stripe pushes all collections to manual invoicing, which kills SaaS pricing leverage. | Format: yes/no + any restriction notes.

**10. Existing AI consulting deliveries (case studies)** -- What: count of completed AI builds for paying clients (not for self/Everlight) + any usable testimonials | Why: drives close-rate assumption on consulting outreach. Zero case studies means BASE's 2 builds/mo is optimistic until 1-2 are landed at lower price. | Format: integer + 1-line on most credible reference.

**11. VA hire willingness and budget** -- What: would Marquise hire a $5/hr Filipino VA at M3 if Deal 1 funds it, and at what task split (calls / data entry / outreach) | Why: BEST case requires capacity expansion. Without VA, the BEST ceiling drops from $851k toward $600k because solo bandwidth caps consulting builds at 2/mo not 4/mo. | Format: yes/no + monthly budget cap.

**12. JV partnership pitches in flight** -- What: count of wholesalers / agents pitched on JV referral in last 30 days, and any responses | Why: the only modeled path to clear $947k requires either VA hire OR a JV that adds ~1 deal/mo of leverage. If JV pipeline is 0, the structural lever has to come from the VA path. | Format: count pitched / count replied / count agreed.

**13. Current debts and minimum payments** -- What: total debt outstanding (CCs, loans, tax, child support, anything) + total minimum monthly payment | Why: net cash flow projection in section 7 of the math file ignores debt service. If minimums are $800/mo, that compresses M1-M3 cash dramatically and changes the unlock-cascade timing. | Format: total balance / total monthly minimum.

**14. Tax position and estimated quarterlies** -- What: any open IRS/state balance, expected Q1 2026 estimated tax payment, and whether you have made it | Why: sole prop on $285k gross owes ~$70k self-employment + federal. If quarterlies are not being set aside, real "cash you keep" by M12 is closer to $200k not $281k. | Format: balance + Q1 plan (paid / due / unfunded).

**15. KDP backlist actuals** -- What: trailing 90-day royalty actual from existing titles | Why: BASE models $50/mo passive. If actual is $0, drop the line. If actual is $300/mo, raise the line. | Format: 90-day total in dollars.

**16. Vantaris and XLM bot live revenue** -- What: any actual cash deposit from a Vantaris user or actual withdrawal of XLM bot profit to a bank account in last 30 days | Why: lets me decide if either deserves a non-zero line in BASE. Currently both are excluded from BASE for lack of evidence. | Format: dollar amount or "$0 confirmed".

**17. Domicile and state of operation** -- What: which state Marquise lives in, which states wholesale deals are being worked, and any move planned in next 12 months | Why: state_gate compliance file blocks NC, TX (cold SMS), CA (pre-foreclosure). If primary state is one of these, the wholesale deal volume assumption needs to drop or shift to compliant states. | Format: home state + 1-3 target wholesale states.

**18. Insurance and benefits floor** -- What: do you have health insurance, what does it cost monthly, any disability or term life | Why: not in current model but creeping cost during ramp. Affects M7+ expense line ($500/mo placeholder might be light). | Format: monthly insurance burn.

---

## When to send these back

Send 1-7 first if you are time-boxed. Those seven inputs alone tighten the BASE case from "theoretical" to "executable" and let me deliver an updated math file with confidence intervals instead of point estimates.

Send 8-18 within a week. They refine the model from "executable" to "audit-ready" so we can defend the projection in a banker meeting or to Justine for any structuring decision.

I am holding the math file as theoretical until at least 1-7 are answered. The numbers don't reconcile to reality until they do.

---

Penny Liang, Financial Safeguard.
