# Mid South Homebuyers Disintermediation Fix -- Contract-First Model

**Compiled:** 2026-04-29 by Marcus Cole.
**Trigger:** Marquise's catch -- "if we just give chris the list, then they might not wanna use us and just go to the seller themselves. im doing the work i want money."
**This document supersedes the batch-ship plan in MIDSOUTH_STRATEGY.md.**

---

## The risk in plain terms

Sending Chris a raw list of 50 Memphis tax-delinquent addresses gives him our research for free. His acquisitions team can:

- Skip-trace the owners themselves (they have PropStream, BatchSkipTracing, etc.)
- Send their own cold-mail or door-knockers
- Buy directly from the seller without paying us a dime
- Even if Chris is honorable, his interns might not be

**The professional wholesale model is contract-first, not list-share.** The contract IS the asset. Without a signed PSA, we have nothing to sell.

---

## Chris's own email confirms this expectation

His exact words:

> "please only send us deals where you are direct to the seller, unless you have a JV agreement with the original agent or wholesaler to pass the listing on to us. We want to work with everyone, and we try our best to avoid stepping on anyone's toes."

Translation: he EXPECTS us to have the property under contract or in a written JV. Sending raw addresses is below his bar.

---

## The new model -- ship ONE deal at a time, contract-first

| Step | What | Who | Time |
|---|---|---|---|
| 1 | Pick 1 high-priority property from the 1,237-lead pool (TS2202 + Chris-zip + verified year_built >= 1940) | Filter Banks via match_to_buyer | 5 min |
| 2 | Skip-trace owner (TPS / FastPeopleSearch / Cuyahoga records / county direct) | Rex Blackwell -- cascade.py | 30 min (when implementations land) |
| 3 | Cold contact: warm postcard + email to owner. TN cold-call BLOCKED. SMS BLOCKED. Mail OK. | Piper Reeves -- branded_mailer + Lob | 1 hr |
| 4 | If owner replies, negotiate cash offer (~70% ARV - repair) | Hammer Ortiz | 1-3 days |
| 5 | Sign PSA + collect EMD ($100-1000 token) -- TN SB 909 disclosure signed in same envelope | Hammer + Marquise | 1 day |
| 6 | NOW package the deal with PSA + photos + ARV math + repair estimate + occupancy + assignment fee | Penny Vance | 2 hours |
| 7 | Send to leads@midsouthhomebuyers.com -- ONE deal, complete package | Hammer | 30 min |
| 8 | Chris reviews 24-48h, says yes/no/counter | -- | 24-48h |
| 9 | If yes: assign contract + Chris wires assignment fee at close | Title firm + Hammer | 7-14 days |

**Total elapsed time per deal: ~10-14 days from picked lead to wire.**
**Realistic close rate: 1 in 4-7 leads we contact converts to PSA. 1 in 2 PSAs makes it through Chris's MAO.**

That's the professional path. Slower than batch-ship, but it's the path that ACTUALLY pays us.

---

## Disintermediation safeguards built into this model

1. **Address withheld until PSA signed.** Cold outreach to owner = "I'm Marquise with Everlight Ventures, interested in your property at [their address]." When packaging for Chris later, the address only goes in AFTER we have the PSA in hand.

2. **PSA is the asset.** We're not selling the address; we're selling the right to take title. Without our PSA, Chris can't buy this property at this price -- the seller could just sell to him direct, but the seller would have to first break OUR contract (with EMD forfeited, which is friction).

3. **Non-circumvention clause in the JV cover sheet** sent with every Chris deal:

   > "This deal is being submitted under JV cooperation. Buyer agrees not to contact the seller directly, bypass the assignor, or attempt to acquire this property outside of this assignment without Everlight Ventures' written consent. Violation triggers buyer's responsibility for the assignment fee plus liquidated damages."

4. **EMD already in title escrow.** Once we have $100-1000 EMD held by a RESPA-clean Memphis title firm (Mid-South Title), the deal is materially locked. Chris seeing "EMD on file at [Mid-South Title]" knows we're real and the deal can't go around him.

5. **Track record builds trust.** First 3 deals are the test. If Chris closes them clean and pays our fee, the relationship works. If he tries to circumvent on deal 1, we know within 48 hours via the title firm and we cut him.

---

## What we should NOT do (retracting earlier plan)

- ❌ Send 50 raw addresses to Chris
- ❌ Send the 1,237-lead full Memphis pipeline as a "buy box match" report
- ❌ Send addresses without first having a JV agreement OR a signed PSA
- ❌ Tell Chris we have "1,237 properties" -- this signals we don't have any under contract

---

## What we DO send Chris in his next email (revised)

The reply Marquise is holding (CHRIS_REPLY_DRAFT.md v2) needs ONE adjustment. The current line:

> "First deal to leads@midsouthhomebuyers.com in 48-72 hours."

Should become:

> "First deal package to leads@midsouthhomebuyers.com next week -- we're locking the seller-side now and want to send a complete package (PSA + photos + ARV + repair + assignment fee) rather than raw addresses. Should be a clean 24h yes/no for your team when it lands."

This sets the right expectation: we're a CONTRACT-FIRST shop, not an address-broker. He'll respect that more, not less.

---

## The 1,237-lead pool is still gold -- just used differently

Use it as INTERNAL pipeline, not external bait. Pick the top 50 (TS2202 + 38106/38114/38109/38127 -- highest density Chris zips) and:

1. **Build year_built verification** for each (next section)
2. **Skip-trace owner** for each (when cascade.py lands)
3. **Outreach** in compliance-clean order (TN warm-only, mail-first)
4. **Convert** 1-3 to PSA over the next 30 days
5. **Ship those 1-3 to Chris** as deals, not as a list

The 1,234 we don't immediately work? They're our own pipeline for the next 90 days. We don't need to share them with Chris OR anyone.

---

## Year_built verification (separate doc -- being built now)

`year_built_verifier.py` -- WebSearch + cluster comp + USGS Open Addresses cross-reference. Per-property "proof document" with multiple sources stating the build year. Output: `Wholesale/buyers/proof_docs/<parcel>_year_built_proof.md`.

When we ship a deal to Chris, the year_built proof attaches to the package. No "estimated, verify on your side" -- we cite 3+ sources.

---

## Decision Marquise needs to make

| Path | Time to first wire | Risk |
|---|---|---|
| **A. Contract-first (recommended)** | 10-14 days per deal | Low -- Chris pays or we walk to backup buyer |
| **B. Batch-ship 50 addresses to Chris** | 24-48 hours | HIGH -- 30-50% chance Chris's team goes around us on hot leads |
| **C. Hybrid -- send Chris 5 SAMPLE addresses with year_built proof but NO owner info** | 48 hours | Medium -- proof of capacity but address still leaks |

**Strong recommendation: Path A.** It's slower but it's the path that actually pays. Path B looks like fast money but is the rookie trap that ruins wholesale relationships.

The reply to Chris should reflect Path A -- "first deal package next week, full package not raw list."
