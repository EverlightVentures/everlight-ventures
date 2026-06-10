# Everlight Caviar + Grow - Two-Phase Roadmap

**Owner:** Rich (Lucrex / Everlight Ventures)
**Date:** 2026-05-21 (updated 2026-05-22)
**Thesis:** Don't fish for sturgeon. Broker the caviar now ($0 cash engine), then use that cash to build a grow asset later (the bucket the faucet fills).
**Decision locked (2026-05-22):** Both, in sequence. Operator has NO physical space, based in California. Therefore Phase 1 (brokerage) starts now; Phase 2 (grow) is funded by Phase 1 and gated on acquiring space.

- **PHASE 1 (now, $0, no space):** caviar brokerage. The cash engine. Sections 1-7 below.
- **PHASE 2 (later, funded by Phase 1, needs space):** the owned grow asset. Section 8.
- **THE BRIDGE:** sequencing + triggers that connect them. Section 9.

---
## PHASE 1 - Caviar Brokerage (the cash engine)
**Capital required to start:** $0 (affiliate), then $0 inventory (drop-ship broker), then capital only at Rung 2.

---

## 1. The Hard Reframe (read first)

**Wild sturgeon fishing for caviar is legally dead in the US. Do not pursue it.**
- All sturgeon (order Acipenseriformes) are CITES-listed; beluga federally banned since 2005.
- California banned commercial sturgeon fishing in 1954; selling wild sturgeon roe is illegal.
- Wild roe plus interstate sale = a state crime escalated into a federal Lacey Act case.
- The only legal wild-roe niche is paddlefish (TN and a few Mississippi-basin states), but that is a licensed commercial-fishing operation with gear/season/permit costs, NOT a $0 entry.

**Farming sturgeon is the opposite of zero-cost.**
- 7 to 15 years before a female yields harvestable roe (~10 yrs to stable production).
- RAS filtration, multi-age-class feed (~28% of cost), wages (~30%), wildlife compliance.
- Multi-year capital build with a ~decade revenue lag.

**Therefore the only near-zero path is brokerage, which is the machine you already run.**
Real-estate wholesaling and caviar reselling are the same motion: source supply, source demand, match, broker, take the spread. Broker OS does not care if the asset is a house or a tin of osetra.

---

## 2. The Capital Ladder (your best path)

Climb a rung only when the rung below is paying.

### Rung 0 - Affiliate ($0, this week)
Monetize buyer intros while building a restaurant book. Zero inventory, zero compliance.
- **IKRAA Caviar** - 10% per sale - https://af.secomapp.com/ikraa-caviar/register
- **Beverly Hills Caviar** - 10% (invitation partner) - https://www.beverlyhillscaviar.com/partner/
- **The Caviar Co.** - affiliate via Awin (creative assets) - https://ui.awin.com/merchant-profile/98929

### Rung 1 - Drop-ship wholesale broker ($0 inventory, the core business)
Open wholesale accounts (apply with proof of business, no capital):
- **Marshallberg Farm (NC)** - largest US indoor RAS, Russian osetra, wholesale starts ~$55/30g tin, takes chef orders by text - https://thecaviarfarm.com/wholesale-caviar/
- **Sterling Caviar / Tsar Nicoulai (CA)** - largest US producer (Dec 2024 merger), "Wholesale Partners" program - https://sterlingcaviar.com/pages/wholesale-partners
- Backup low-MOQ supply: Browne Trading (free ship >=$200), Fish Breeders of Idaho, Bemka (FL), Marky's (FL).

**Critical negotiation: ask the farm to DROP-SHIP directly to your buyer.**
- FDA: a "merchant office" that handles only paperwork while the manufacturer ships direct does NOT need FDA food-facility registration. Taking physical possession (fridge/warehouse) forces registration plus a licensed inspected cold-storage facility. That is the cost cliff; drop-ship keeps you on the free side.
- Stay 100% domestic, and CITES labeling plus USFWS export license plus the $100 export form all apply to international trade only. Domestic farmed-caviar reselling = zero FWS permit burden.
- Net Rung-1 compliance cost: business license plus sales-tax registration. ~$0.

**Margin:** buy ~$52 to $55/oz wholesale, sell $100 to $150/oz retail = ~35 to 50% gross. Farm handles cold chain.

### Rung 2 - Hold inventory (post-traction, deliberate, NOT now)
Only when volume justifies a licensed cold-storage food facility do you take stock and capture full margin. Post-Deal-1 unlock per macro/micro doctrine. The entry point is never here.

---

## 3. Reuse Map - repoint, don't rebuild

| Asset (already built) | RE use | Caviar repoint | Effort |
|---|---|---|---|
| broker_daily_orchestrator.py | scout-match-outreach-close-invoice | swap step-1 source to farms plus restaurants, keep steps 2 to 10 | LOW |
| content_tools/branded_mailer.py plus report_template.py | seller/buyer outreach | rebrand template, reuse cadence plus warm-up | LOW |
| broker_ops/services.py plus rex_lead_scorer*.py | ARV/property scoring | score buyer tier (restaurant rating/volume) vs supply tier (grade/origin) | MED |
| apify_lead_wrapper.py | Zillow/Redfin scrape | repoint actors to restaurant/grocer/distributor directories | MED |
| contract_generator.py plus stripe_invoicer.py | finder-fee PDFs plus invoicing | caviar reseller terms, same Stripe flow | MED |
| everlightventures.io site plus Supabase plus Stripe plus Resend | broker intake | caviar product/order page plus buyer/farm intake forms | MED |

**The moat is the premium front, not the price.** Caviar margin compresses when you compete against farms' own DTC pricing. You win as the reliable account rep a chef texts at 4pm. The 4-persona handoff sells exactly that feeling:
- **Piper Reeves** - warm first-touch to restaurants/chefs
- **Henry Hammond** - terms / volume pricing
- **Marvin Cohen** - fulfillment plus drop-ship coordination
- **Vaughn Sterling** - senior signoff on large accounts

---

## 4. Macro / Micro Split

**MICRO (first dollar this month, gates revenue):**
1. Sign up to all 3 affiliate programs (Rung 0), today, $0.
2. Build a 25-restaurant target list (local fine-dining plus sushi plus hotels) via existing scraper.
3. Apply for Marshallberg plus Sterling wholesale accounts; request drop-ship terms.
4. Fire first 10 Piper outreach emails through branded_mailer to chefs/buyers.
5. First sale = affiliate commission or first drop-ship broker order.

**MACRO (parallel, post-first-sale):**
- Branded caviar product/order page on everlightventures.io.
- Automated farm-supply vs restaurant-demand matching in Broker OS.
- Everlight private-label brand (Bester offers label development; revisit at volume).

---

## 5. Compliance Guardrails (so you don't get burned)
- **Domestic only.** US farms to US buyers. No imports/exports, so no CITES, no USFWS.
- **Drop-ship until Rung 2.** No physical possession, so no FDA facility registration, no licensed cold-storage facility.
- **Never touch wild sturgeon.** Federal plus state bans plus Lacey Act exposure.
- **Confirm your home-state PHF rules** before ever holding refrigerated inventory.
- Caviar is a refrigerated potentially-hazardous food, outside cottage-food laws everywhere. Holding it = licensed establishment.

---

## 6. Market Reality
- Market size: ~$0.4B to $3.1B depending on analyst definition; consistent signal = mid-to-high single-digit CAGR, US fastest-growing country (~5.2%).
- Farmed osetra retail: ~$75 to $200/oz. Marshallberg wholesale starts ~$55/30g (~$52/oz).
- Reseller gross: ~35 to 50% on buy-resell; affiliate caps ~10% but zero risk.

---

## 7. 7-Day Action List
- [ ] Day 1: Register IKRAA plus Beverly Hills plus The Caviar Co. affiliate accounts ($0).
- [ ] Day 1-2: Repoint apify_lead_wrapper.py to pull 25 local fine-dining/sushi/hotel buyers.
- [ ] Day 2: Submit Marshallberg plus Sterling/Tsar Nicoulai wholesale applications; ask for drop-ship.
- [ ] Day 3: Draft Piper first-touch template in branded_mailer (warm register, chef-facing).
- [ ] Day 4: Fire first 10 outreach emails. Log replies to inbound_reply_matcher.
- [ ] Day 5-6: Stand up a one-page order intake on everlightventures.io / Supabase form.
- [ ] Day 7: First affiliate link live in outreach; track first commission.

---

## PHASE 2 - The Owned Grow Asset (funded by Phase 1, needs space)

This is the retirement/wealth piece. You do NOT start here. Phase 1 cash buys it.
Two gates, in order: (1) capital from the brokerage, then (2) physical space (none today, CA).

**Grow options ranked for a no-space CA operator (easiest to hardest):**

1. **Aquaponics - tilapia/trout + leafy greens.** The real "fish + hydroponics hand in hand."
   Cheapest, food-safe, smallest footprint, harvests in weeks. The honest first grow. Proves your
   grow chops with low capital before any long-horizon bet.
2. **Sturgeon -> your own caviar.** CA is the #1 US sturgeon-farming state, so it is viable here,
   but it is a ~10-year patient-capital legacy asset (RAS tanks, cold water, aquaculture registration,
   water access). Vertical-integration payoff: you are ALREADY the broker from Phase 1, so when your
   own fish produce, you sell through a pipeline you already built.
3. **Cannabis hydroponic grow (the blueprint at 05_PERSONAL/.../Cannabis_Startup/).** Biggest headline
   number, hardest reality. CA cultivation license + local permit (many CA cities ban cultivation),
   Metrc track-and-trace, ~$50k+ startup, ~$109k/yr electricity (per the blueprint's own math). The
   blueprint assumes ~$100/oz wholesale; 2026 CA wholesale has been ~$20-45/oz, so its ~$236k profit
   line is likely overstated 3-5x. Real business, not passive, not cheap. Re-validate CA economics +
   local permitting before this gets serious.

**Hard rule:** never combine caviar + cannabis in one water loop. Sturgeon want cold water (~60-68F),
cannabis/tilapia want warm (~75-82F) - thermally incompatible - AND a food product (caviar) sharing a
system with a Schedule I crop is a compliance landmine. One lane per system.

---

## THE BRIDGE - Sequencing + Triggers

1. **Run Phase 1 until it throws off consistent margin.** Define a capital target before opening
   Phase 2 (e.g., first $X banked from brokerage). No grow spend before that.
2. **Space is the gate, not cash alone.** With no space today, Phase 2 cannot start regardless of
   how much the brokerage earns. This ties directly into the Personal Overhead OS endgame
   (Fannie Mae / CalHFA house-hack): a property with a garage/yard/outbuilding BECOMES the Phase 2
   grow site. So Phase 2 is downstream of BOTH brokerage cash AND the housing move already planned.
3. **Sequence:** brokerage cash -> secure property/space (house-hack or lease) -> start with
   aquaponics (cheapest, food-safe, proves the grow) -> optionally layer sturgeon-for-caviar as the
   long legacy asset -> cannabis only if CA economics + local permits justify it.

---

*Sources: USFWS/CITES, FDA food-facility registration guidance, FactMR/Mordor/Precedence market reports, Marshallberg/Sterling/Tsar Nicoulai/IKRAA/Beverly Hills published programs. Cannabis blueprint at 05_PERSONAL/A_Personal_Notebook/Y_My_Inventory_Bag/Personal_Documents/Business_Ideas/Cannabis_Startup/. CA cannabis wholesale figures are directional and must be re-validated at Phase 2 activation. Full citations in the research brief that generated this plan (2026-05-21 Hive dispatch).*
