# ATTOM Key Expired -- Choose A New Data Provider

Date: 2026-04-24

**Status:** ATTOM API key `8b8f49842c214289928801e9bc67ecc7` returns 401 on
every call. Trial was cancel-by-April-16; we're 8 days past.

This blocks the AZ/TN fresh pull I planned tonight. The `discover_properties_in_zip`
endpoint is wired up and ready -- it just needs a working key.

## Option A -- Renew ATTOM

- Free trial: new email, ~30 days, ~500 calls/month.
  https://api.developer.attomdata.com/
- Paid: **~$300/mo starter**, bigger quotas, expanded endpoints.

**Pros:** the code already works with ATTOM's response shape.
**Cons:** $300/mo is ~$11/deal if we hit 1 deal/week.

## Option B -- RealEstateAPI.com

- Pricing: $49/mo (5k calls) up to $199/mo (50k calls).
  https://realestateapi.com/pricing
- Endpoints: bulk zip search, owner lookup, skip trace add-on.

**Pros:** cheaper than ATTOM, owner data included.
**Cons:** would need to rewrite the enrichment module (different response shape).
  ~2 hours engineering.

## Option C -- BatchData

- Pricing: pay-per-lead, ~$0.02-0.05 each.
- Does both **discovery** (find distressed leads in a zip) and **skip tracing**
  in the same dashboard.

**Pros:** one vendor for both levers. Wholesale-focused.
**Cons:** no free tier. Need a card on file.

## Option D -- Public Playwright scrape (Zillow FSBO, Redfin, Realtor)

- No API cost.
- Playwright already installed in the workspace (`wholesale_property_scraper.py`).

**Pros:** free.
**Cons:** brittle (bot detection), slower (~2s/property), TOS grey area.
Would probably cap out at ~50 leads/day before IP ban.

## Recommendation

Short-term: **Option A renewed free trial** using a different email if the
original one is blocked, OR start with **Option D Playwright** to unblock AZ/TN
today while we decide on a paid plan.

Long-term: **Option C BatchData**. $0.03/lead across both discovery and
skip-trace = ~$6 for the full 200-lead AZ batch. Same vendor unifies the
two biggest levers we need (fresh leads + contact info).

## What's wired already

- `broker/attom_enrichment.py` has `discover_properties_in_zip(zip)`,
  `discover_metro("phoenix")`, and `discover_metro("memphis")`.
- Metro zip batches pre-picked: 18 Phoenix zips, 16 Memphis zips.
- State hunter (`state_property_hunter.py`) ready to ingest whatever the
  discovery call returns.

As soon as a working key / vendor is in place, one command populates AZ + TN.

## Choose one and paste me the key / credentials

I'll finish wiring AZ + TN the same night you give me the go signal.
