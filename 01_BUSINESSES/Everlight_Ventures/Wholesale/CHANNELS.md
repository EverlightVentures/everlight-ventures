# The 3-Channel Wholesale Architecture

**Authoritative reference for which list, which strategy, which agent owns what.**

**Filed:** 2026-04-26 after Marquise's correction: *"we should have the channels... idk how u have it now but i think we are confusing lists possibly... vet that list for real people and sellers, real title companies that would be needed for said sellers, as well as buyers."*

---

## The Three Channels

A wholesale deal touches three completely different counterparties. Each one needs its own list, its own classifier rules, its own outreach strategy, its own scripts, its own named-agent owner. **A bad email in one channel is a great email in another -- "info@webuyhouses.com" is exactly who we want as a buyer and exactly who we DON'T want as a seller.**

```
        SELLERS              ->         TITLE COMPANY        ->          BUYERS
   (homeowners in pain)        (escrow + close + EMD)         (cash investors w/ POF)
        Channel 1                     Channel 2                       Channel 3
```

---

## CHANNEL 1: SELLERS (PropertyLead)

**Goal:** Find homeowners in distress willing to sell at a discount, sign them to an assignable PSA.

| Field | Value |
|---|---|
| DB Table | `broker_ops.PropertyLead` |
| Classifier rule | seller channel: gov / agent / attorney / title / business = BLOCKED |
| What's allowed | `homeowner_likely`, `unknown` (with WARN flag) |
| Owner -- Outreach | **Piper Reeves** (warm Nashville voice, "y'all", soft-touch first contact) |
| Owner -- Negotiation | **Hammer Knox** (closer, "champ", direct on price) |
| Owner -- Compliance | **Justine Park** (state gates, DNC writeback, recipient classifier) |
| Outreach channels | Email (primary, all 9 states), inbound SMS reply, manual cold-call within state hours |
| Outreach budget | 90% of total outreach spend |
| Communication cadence | 7-touch sequence: D0, D3, D7, D14, D21, D30, D45 -- all email |
| Success metric | Reply rate, then % to "engaged", then % to "under_contract" |
| Compliance gates | OH HB 132 disclosure, CA CC 1695 (pre-foreclosure), TX SB 1577 marketing scope, FL FTSA, NC HB 797 (BLOCKED entirely), all per `state_gates.json` |
| Source today | Cuyahoga delinquent-tax list, foreclosure auction listings, FSBO scrapes |
| Volume today | 434 active (after 32-row purge), only 9 with email -- skip-trace gap |

### Sellers list hygiene rules

1. Pre-ingest signal `preingest_classify_email` on `PropertyLead.save()` flips status to `blocked_non_homeowner` for any gov/agent/attorney/title/business email.
2. State_gate refuses sends without a compliance record for the property's state.
3. ConsentLedger writes any "decline / unsubscribe / stop" to permanent block list per CAN-SPAM (email = forever, phone = 5y, mail = 12mo per FCC TCPA + industry).
4. Inbound watch daemon scans every reply and routes opt-outs to DNC writeback before the next send fires.

---

## CHANNEL 2: TITLE COMPANIES (TitleCompany)

**Goal:** Build relationships with 1-2 investor-friendly title firms per market who will hold EMD, run our assignment closings, and disburse our fee on the closing statement.

| Field | Value |
|---|---|
| DB Table | `broker_ops.TitleCompany` (NEW 2026-04-26) |
| Classifier rule | title channel: gov / homeowner-personal / agent / business = BLOCKED |
| What's allowed | `title_company`, `attorney_firm` (some attys do title work), `unknown` (firm websites often use generic info@) |
| Owner -- Relationship | **Hammer Knox** (relationships happen on the phone, not in inboxes) |
| Owner -- Compliance | **Justine Park** (RESPA Section 8 violation watch, ensures no kickbacks/referral fees flow either way) |
| Outreach channels | Phone calls during business hours (10am-12pm local sweet spot), occasional email follow-up |
| Outreach budget | Time investment, ~$0/month -- relationships are the asset |
| Communication cadence | Initial email -> 3-day phone follow-up -> meet in person if local -> first deal -> ongoing every-deal contact |
| Success metric | # of "primary" relationships per market (target: 2+ per market we operate in) |
| Compliance gates | RESPA Section 8 (no referral fees either direction), state-specific licensure (GA = attorney close required, FL = title insurance regs) |
| Source today | Manual research, BiggerPockets threads, local REIA member lists |
| Volume today | 35 firms across 7 markets (5/market in AZ, FL, GA, MO, NC, TN, TX). **Cleveland OH NOT YET in the list -- add when scouted.** |

### Title-firm hygiene rules

1. **Money flows TO us, not FROM us** by default. Per `MONEY_FLOW.md`: title fees paid by buyer's closing costs. Wholesale-side fees only acceptable when the deal still pencils net-positive (per "TAKE THE DEAL" rule).
2. **No referral kickbacks either direction** per RESPA Section 8 -- federal crime. The `REFERRAL_MOU_TEMPLATE.md` has this baked in.
3. **Investor-friendly classification:** verified yes, maybe, or no. "Maybe" firms get tested on small deals before being promoted to primary.
4. **Per-market ranking 1-N.** Rank 1 is first-call, rank 2-3 backup, rank 4+ is bench.
5. **Deal counts + close-time tracked** per firm. If a firm starts taking 30+ days when they used to close in 14, that's a downgrade signal.

---

## CHANNEL 3: BUYERS (InvestorBuyer)

**Goal:** Maintain a pre-vetted pool of cash buyers with POF (proof of funds), tagged by market + budget + speed-to-close, ready to receive a contract assignment within 24 hours.

| Field | Value |
|---|---|
| DB Table | `broker_ops.InvestorBuyer` |
| Classifier rule | buyer channel: gov = BLOCKED, attorney = WARN. Agent + business + unknown = OK |
| What's allowed | `real_estate_agent` (we-buy-houses.com style), `business_other`, `unknown`, `homeowner_likely` (individual investors) |
| Owner -- Sourcing | **Cupid** (matches buyers to seller deals, scoring algorithm in `wholesale_buyer_matcher.py`) |
| Owner -- Pitching | **Cash** (sends investment pitches via `wholesale_auto_pitch.py`, fires when match score >= 70 + fee >= $5k) |
| Owner -- Onboarding | **Filter Banks** (vets new buyers, validates POF, scores buy-box) |
| Outreach channels | Email pitch with deal details, follow-up phone call within 4 hours, Slack notification on DMable matches |
| Outreach budget | Free -- buyers come to us once we publish deals |
| Communication cadence | On-deal: instant pitch (within 1hr of match), 24hr follow-up if no response, drop after 48hr no-response |
| Success metric | # of active buyers, % responsive within 4hr, # of deals matched -> closed |
| Compliance gates | None -- buyers initiated contact + signed up. SMS allowed if they texted us first (TCPA exception). |
| Source today | GCREIA Facebook, BiggerPockets Cleveland forum, FB groups, direct sign-up via `/investor-signup/` page |
| Volume today | 84 active buyers across 7 markets. 1 deal closed (the Apr 24 first-ever). |

### Buyers list hygiene rules

1. **POF required for premium tier.** We Buy Houses brands and small individuals OK without POF on day-1 but do not match to deals over $300k until POF on file.
2. **Buy-box defined.** Markets, property types, budget range, can-close-days. If a buyer has empty buy-box, no auto-match -- they go to manual queue.
3. **`is_active` flag.** If a buyer ghosts 3 deals in a row, set `is_active=False`. They can be reactivated by signing back in.
4. **Pre-ingest validation:** the new web form at `/investor-signup/` runs `is_blocked_for_channel(email, name, "buyer")` -- only government addresses blocked, all other classes allowed.

---

## Cross-Channel Workflow (a normal deal)

```
Day 0:    Piper sends 7-touch email to homeowner (Channel 1).
Day 3:    Homeowner replies "what would you offer?" (Channel 1 -> warm).
Day 5:    Hammer cold-calls + sends PSA at $X. Seller signs Documenso (Channel 1 -> under_contract).
Day 5:    Cupid scores 84 buyers against deal, top 5 fire pitches via Cash (Channel 3).
Day 6:    Buyer #1 says "I'll take it" (Channel 3 -> matched).
Day 6:    Hammer calls primary title firm in market, opens escrow (Channel 2).
Day 7:    EMD wired by buyer to title firm; assignment contract signed (Channel 1+3 -> closing).
Day 14:   Inspection contingency clears.
Day 21:   Cash close. Buyer wires to title. Title disburses assignment fee to Everlight.
          (Channel 2 collects from buyer, Everlight does NOT pay title fees.)
Day 21:   Stripe webhook fires, CommissionRecord created, JV split if applicable.
```

---

## Rule of thumb -- which channel does this belong to?

| Email pattern | Probably... |
|---|---|
| `firstname.lastname@gmail.com` / `yahoo.com` / `aol.com` | **Seller** (homeowner) or buyer (individual investor) |
| `info@somecompany.com` where `somecompany` includes "buy", "homes", "properties", "cash", "fast" | **Buyer** (We Buy Houses brand) |
| `info@firmnametitle.com` / `escrow.com` / `closing.com` | **Title** |
| `firstname@somefirmlaw.com` / contains "esq", "attorney", "legal" | Could be **title** (attorney close states) or buyer (atty-investor) -- check context |
| `*.gov` / `*.us` (state) / `mayor*` | **NOTHING. Block everywhere.** |
| `realtor@kw.com` / `compass.com` / `coldwellbanker.com` | **Buyer** (agent-investors are common) -- but never a seller |

---

## When in doubt, route to Justine

If a lead doesn't cleanly fit one channel, don't auto-add it to anything. Drop it to `/home/opc/_unrouted/` for Justine to manually classify or reject. Better to lose a lead than to pollute a list.

---

**Maintained by:** Justine Park (compliance gate), Lucrex (architecture)
**Reviewed:** Quarterly minimum, or whenever a new state opens up

This document is the contract between channels. Cross-contamination violates it.
