# Buy-Box Survey -- Investor Buyer Activation
**Date:** 2026-04-26
**Operator:** Hammer Knox, Deal Closer
**Channel:** Branded email via `content_tools.branded_mailer.send_branded_email()`
**From:** marquise@everlightventures.io
**Reply-to:** marquise@everlightventures.io

---

## Numbers

- **Total buyers contacted:** 84 of 84 (100% of InvestorBuyer rows had valid email)
- **Successful sends:** 77
- **Blocked by state_gate compliance:** 7
- **Send success rate:** 91.7% (77/84)
- **Resend chokepoint delta:** 33 -> 110 lines in `/home/opc/_logs/resend_budget.jsonl` = 77 confirmed sends through `branded_mailer`
- **Per-send log:** `/home/opc/_logs/buybox_survey_2026_04_26.jsonl` (84 rows)

## Compliance Holds (Justine working)

7 buyers blocked at `state_gate`:
- 4x OH (no compliance record on file -- needs Justine to whitelist b2b_vendor for OH)
- 2x NC (NC HB 797 wholesale block, hard rule, do not bypass)
- 1x NV (no compliance record on file -- same as OH)

These are not bugs. The compliance layer caught what we asked it to catch. NC will never go out cold under current law. OH/NV need a one-line Justine update to add b2b_vendor whitelist if we want to reach those buyers next round.

## Personalization Proof (3 Live Subjects)

1. `Marcus Webb, what are you buying right now in Cleveland, OH?`
2. `Darnell King, what are you buying right now in Cleveland, OH?`
3. `Teresa Howell, what are you buying right now in Saint Louis, MO?`

Buyer name + first market token both pulled from `InvestorBuyer.markets`. Real-CRM tone, no blast-list scent.

## Expected Reply Window

- **3-day window reply rate (warm B2B nurture):** 10 to 25%
- **Conservative target:** 8 replies
- **Realistic target:** 12 to 19 replies
- **Aggressive target:** 20+

Each reply = a real buy box (price, neighborhoods, condition, close speed) for Marquise's manual hunt.

## Action -- Marquise

1. Daily inbox scan on `marquise@everlightventures.io` for replies
2. For each reply, parse the buy box and add to Cleveland scout list
3. Prioritize replies by: cash, close speed under 14 days, Cleveland-OH proximity
4. Route hottest 3 buy boxes to Rex for active hunting
5. Anyone who does not reply in 7 days: hold for Round 2 (different angle, after we close Deal 1)

## Doctrine Check

- branded_mailer chokepoint: yes, every send through it (77/77 logged in resend_budget.jsonl)
- budget_category: nurture (warm-list, not cold blast) -- preserves VIP reserve
- No drafts, all sent direct
- No em-dashes, no filler
- No api.resend.com bypass

Hammer Knox, Deal Closer.
