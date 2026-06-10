# L6: Teardown Hunt (Dedicated Lane)

**Status:** Launch in parallel with L1 + L5 after L2 ships its first contract. Uses the shared Zillow + Propwire + assessor stack.

## Thesis

Dedicated hunt for teardown candidates in infill zones where new-home builders have active demand. L6 is the "pure" builder-play lane; L1/L2/L5 may opportunistically produce teardowns, but L6 targets them directly for volume.

## Relationship to Default Offer

L6 runs the `teardown_assignment_80pct.md` offer as its only pricing play. When a L1/L2/L5 lead matches the teardown buy-box (via `wholesale/teardown_candidate_check.py`), it borrows L6's offer strategy without crossing lane boundaries.

## Daily Scout Cadence

- Morning cron: Zillow search for teardown keywords ("teardown", "land value", "needs demo", "tear-down", "estate sale", "as-is")
- Filter by: lot size 6000+ sqft, structure 1500 sqft or less, year built < 1980
- For each hit: pull county assessor record, compute 80%-of-assessed offer, check 3+ active new-home builders within 25-mile radius
- Route qualified leads to `builder_new_home` outreach queue

## Scout Targets (starter)

- **Phoenix, AZ** (Maricopa County assessor) -- most active builder market
- **Dallas, TX** (Dallas + Collin County assessor)
- **Atlanta, GA** (Fulton + Gwinnett assessor)

## KPIs

- Leads scouted/day (target: 20 per market)
- Leads qualified/day (target: 3 per market after 80% rule + builder proximity)
- Offers sent/day (target: 2 per market)
- Contracts signed/week (target: 1 per market)
- Closed assignments/month (target: 1 per market = $30K / month / market)

## Cron Slot

Add L6 to `rex_master_pipeline.py` ROUTE_TABLE as a morning-phase lane with a dedicated call to the teardown scout. Volume separate from L1/L2/L5 so KPIs don't cross.

## Retrospective Rule

If L6 does not close 1 deal in 60 days, freeze the lane and redirect resources to whichever of L1/L2/L5 has produced teardown leads through the overlay. This prevents L6 from siloed-burning budget while the overlay proves the strategy for us.
