# Teardown Assignment at 80% of Assessed Value

**Status:** Default offer for the wholesale pipeline until proven otherwise. Dual-deployed: primary offer in L6 AND auto-applied in L1/L2/L5 when lead fits the teardown buy-box.

## Thesis

Teardown candidates (old structure on a large lot in a gentrifying market) have land value that dwarfs improved value. Sellers often price based on assessed value because they have no ARV reference. Offering 80% of assessed captures the building-lot premium AND gives new-home builders their typical 15-25% margin on finished builds.

## Buy-Box

- Lot 6000+ sqft in an infill zone (zoned SFR or R-1 in a city where builders are active)
- Structure 1500 sqft or less
- Year built < 1980 (or listed as "teardown", "needs demo", or "land value only")
- Assessed value publicly available on county assessor site
- At least 3 active new-home builders within 25-mile radius (builder_new_home segment)
- No historic district designation

## Offer Formula

```
offer_to_seller   = 0.80 * assessed_value
assignment_fee    = 30_000   (target; range 20K-50K)
buyer_pays        = offer_to_seller + assignment_fee
margin_ok_if      = buyer_pays <= 0.85 * (assessed_value * local_land_premium_multiplier)
```

Where `local_land_premium_multiplier` is 1.2-2.0 depending on the market (Phoenix 1.8, Atlanta 1.5, Dallas 1.4, Nashville 1.6).

## SMS Template (pending Justine review + A2P approval)

```
Hi [FIRST], I'm Piper with Everlight Ventures. We buy older homes on bigger lots for cash and close in 14 days. Any interest in an offer on [ADDRESS]? Reply STOP to opt out.
```

## Contract Clause

Include "Quality Assurance Review Period" (7-day inspection window post-contract). This gives Ace time to re-validate the builder-buyer match before we are on the hook.

## Buyer Segment

`builder_new_home` in `buyers_db.json` and `rex_buyer_segmenter.py`. Seed list covers Phoenix, Dallas, Atlanta (starter markets). Target 10-20 builders per market.

## Fire Team

| Role | Agent | Action |
|---|---|---|
| Scout | Rex Blackwell | Zillow teardown keywords + assessor scrape |
| Qualifier | Frederick "Filter" Banks | 80% rule + lot size + builder proximity check |
| Profit | Penny Prescott | land-premium multiplier per market |
| Matcher | Calvin "Cupid" Hayes | match to builder_new_home segment |
| Marketer | Ace Morgan | one-pager pitch for builder buyer |
| Outreach | Piper Reeves | SMS + builder-specific email |
| Closer | Harrison Cole | assignment contract with QA clause |
| Compliance | Justine Park | pre-clear SMS template + contract |

## Success Metric

1 closed assignment per 30 days at $30K average fee. If we hit that in any starter market, double the buy-box into adjacent markets.

## Dual Deployment

This playbook is used in TWO places:
1. **L6 lane** -- dedicated teardown hunt with its own scout (Zillow teardown keywords) and own cron slot
2. **L1/L2/L5 overlay** -- `wholesale/teardown_candidate_check.py::is_teardown_candidate(property)` gates auto-switch to this offer when a lead from any other lane matches the buy-box
