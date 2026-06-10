# DATA CENTER IMPACT 360 -- MASTER BRIEF
### Everlight Ventures Intel Center | Compiled 2026-05-21
*Built by a 6-agent Hive fan-out (water, health/ecology, economics, California-local, state-by-state, water/power economics) + a cross-check pass. Every figure traces to SOURCES.md. Projections are labeled. Three viral "facts" were corrected (see the red box).*

---

## THE MORAL OF THE STORY (read this if you read nothing else)

The AI data-center boom is a **privatized-gains, socialized-costs** story.

A handful of cash-rich companies (Microsoft, Google, Meta, Amazon, Oracle, xAI) are racing to build city-sized computers. To do it they need two things that are **underpriced and locally finite**: electricity and water. Because those inputs are priced on *average cost*, not *scarcity*, the biggest, most price-insensitive buyer on Earth gets the cheapest rate -- and the **leftover bill (higher power rates, strained water, dirtier air, lost tax revenue) lands on the residents and small businesses who never voted for any of it.**

The benefit shows up as **trillions in private market value** on a few balance sheets. The cost shows up as **$16-21 more per month on a household power bill**, a **drained aquifer**, a **predominantly-Black Memphis neighborhood breathing turbine exhaust**, and a **county that gave away its tax base for ~50 permanent jobs.**

That's the asymmetry. You are not wrong to smell something off. The data backs your instinct -- with one honesty caveat: **AI is genuinely useful and the demand is real.** The fight is not "AI vs. no AI." The fight is **"who pays, who decides, and what's the cap."** That's where you actually have leverage.

---

## 1. WHAT IS ACTUALLY GOING ON

- **The build:** ~5,000 data centers already exist in the U.S. Big Tech plans to spend roughly **$725 billion in 2026 alone** (up ~77% from 2025's $300B+) on AI infrastructure. OpenAI's "Stargate" project alone is ~$400-500B and ~7 gigawatts planned.
- **Why now:** Training a frontier AI model is **one giant synchronized computation**. Thousands of chips have to sit physically next to each other, fed unbroken power for weeks. You literally cannot do it on small scattered centers -- the chips have to be in one place. That's why it's hyperscale, not "a server in every town."
- **Why so big / why not just small ones for themselves:** Economies of scale + low latency + the arms race. Whoever has the most compute trains the best model first. It's a land-grab for the inputs of intelligence.
- **The result:** Demand for power and water is spiking faster than the grid or water systems were built to handle, and it's concentrating in specific places.

---

## 2. THE RESOURCES -- HOW BIG, COMPARED TO A PERSON

### Water
| Thing | Water use | Human equivalent |
|---|---|---|
| One person (home) | 82-100 gallons/day | -- |
| Mid-size data center | ~110 million gallons/year | ~1,000 households |
| **Large/hyperscale center** | **up to 5 million gallons/DAY** (peak) | **a town of ~50,000 people** |
| Google, The Dalles OR (2021, actual) | 274.5 million gallons/year | ~25% of the entire city's water |
| **All U.S. data centers, direct (2023, LBNL)** | **~17 billion gallons** | -- |
| All U.S. data centers, INDIRECT (power plants that feed them, 2023) | ~211 billion gallons | ~12x the direct figure (methodology-dependent) |

> **The number you asked for, plainly:** one big data center's daily water draw equals about **50,000 people**. Its electricity equals **100,000+ homes** (~250,000 people). One building. (See charts 01 and 10.)

### Power
- U.S. data centers used **176 TWh in 2023 = 4.4% of all U.S. electricity** (up from 58 TWh in 2014). Headed to **325-580 TWh by 2028 = 6.7% to 12% of the entire grid** (Lawrence Berkeley National Lab, Dec 2024).
- A single hyperscale AI campus can need power for **100,000+ homes**. Meta's Nebraska center alone uses nearly as much electricity as Omaha's coal plant produced in a year.

---

## 3. WHO BENEFITS, WHO PAYS (the heart of your question)

**Who benefits / who's making the money:**
- The tech giants and their shareholders. Alphabet is closing on a ~$4.3 trillion valuation on AI optimism. Cloud/AI revenue is growing 60%+ a year. The data centers are the engine that prints that.
- **You, indirectly,** when you use AI -- which is exactly your discomfort. The service is real; the resource bill is just hidden from the person clicking "generate."

**Who pays / who eats the cost:**
- **Ratepayers.** In the PJM grid region (mid-Atlantic/Midwest), the independent market monitor attributed **63% (~$9.3 billion) of one capacity-cost cycle to data centers.** Real bills: **+$21/mo in DC, +$18/mo western Maryland, +$16/mo Ohio.** Virginia's official study projects **+$14 to +$37/month by 2040.** (Chart 06.)
- **Taxpayers.** Virginia's data-center sales-tax break cost the state **$1.6 billion in FY2025**; education funding foregone climbed to $267M. Georgia's break ballooned toward **$2.5 billion.**
- **The host community's air, water, and quiet.** (Section 4.)
- **Future ratepayers**, who are pre-paying for data centers **that haven't been built yet**: ~$6.2B of the latest PJM auction was for *forecast* load. If the AI boom cools, that grid investment is still on the rate base for 20-40 years -- a **stranded-asset transfer** with a long tail.

**The water-price tell (one stat that says it all):** In Mesa, Arizona, **Google negotiated $6.08 per 1,000 gallons while residents pay $10.80** -- the biggest user, in a desert, pays ~44% *less* per gallon. Water is priced on volume discounts, not scarcity. (Chart 09.)

---

## 4. WHAT IT DOES TO THE ENVIRONMENT AND TO PEOPLE

### The water itself (your "is the 20% toxic?" question, answered properly)
- **~80-85% of cooling water evaporates** into the sky and never comes back to the supply. (Chart 04.)
- The remaining **~15-20% is "blowdown"**: warmer, saltier, and dosed with **biocides, corrosion inhibitors, and scale inhibitors**. It is **not drinking water** and not meant to be. Properly permitted, it goes to a treatment plant and is diluted to legal limits. Mishandled, it becomes a chronic local pollutant via:
  - **Thermal pollution** -- warm discharge (often 86-104F) lowers dissolved oxygen and stresses/kills fish.
  - **Chemical toxicity** -- chlorine/biocides harm fish, invertebrates, algae.
  - **Salinity creep** -- evaporation concentrates minerals; repeated discharge raises salinity in freshwater systems.
- **Honest limit:** the strongest aquatic-kill science is from *power plants generally*, not data centers specifically. For data centers the toxicity is documented as a **mechanism and risk**, not yet as a confirmed named fish-kill in peer-reviewed literature. Don't overstate it; do take it seriously.

### Air and human health
- **Diesel/gas backup generators and the gas plants kept running to feed centers** raise NOx, NO2, and PM2.5. A Caltech/UC Riverside study (preprint, Dec 2024) estimates the U.S. data-center air-pollution toll at **~$20 billion/year and as many as ~1,300 premature deaths/year by 2030.**
- **Memphis (xAI "Colossus")** is the live test case: dozens of gas turbines run with permit fights; the NAACP + Southern Environmental Law Center + Earthjustice are litigating. Satellite data show **peak NO2 up ~79% right at the fence-line** of the facility in a predominantly Black neighborhood (smaller rises further out; a competing study found little PM2.5 change -- the dispute is live).
- **Environmental justice:** these get sited disproportionately in low-income and minority communities, and the rate hikes hit hardest there -- low-income, Black, and Hispanic households can spend up to **20% of income on energy vs. 3%** for higher-income households. A flat $16-18/mo hike is regressive.
- **Noise:** continuous cooling fans hit **>105 dB at some sites**; noise is the #1 reason cited when projects get killed.

---

## 5. THE CHAIN OF EFFECTS (before -> during -> after)

```
TRIGGER:   AI race -> hyperscalers need compute -> need power + water + land + tax deals
   |
BEFORE:    State/county offers tax breaks + cheap power + fast permits (often under NDA,
           via shell LLCs, with little public vote). Promised: jobs + tax revenue.
   |
DURING:    Construction boom (temporary jobs). Grid + water upgrades begin.
   |
AFTER:     ~20-150 permanent jobs. Tax base partly given away. Then the cascade:
   |
   +--> POWER:  demand spikes -> capacity prices jump -> EVERYONE's bill rises ($16-37/mo)
   +--> WATER:  millions of gal/day drawn -> aquifers/reservoirs stressed -> wells fail,
   |            rates rise (Newton County GA: +33% water rates; private wells ran dry)
   +--> AIR:    backup generators + retained gas/coal -> NOx/PM2.5 -> asthma, deaths
   +--> NOISE:  24/7 cooling fans -> sleep loss, complaints, lawsuits
   +--> TRUST:  promised benefits don't land -> community feels used -> moratoria, lawsuits
   +--> RISK:   if AI demand disappoints -> stranded grid assets -> ratepayers hold the bag
```

The cruelty of the cascade: the people who clicked "approve" (county boards, lured by jobs/revenue) and the people who pay (residents, future ratepayers) are often **not the same people**, and the company booking the upside is **somewhere else entirely.**

---

## 6. THE NATIONAL PICTURE + YOUR STATES

Full detail in `05_STATE_BY_STATE.md`. The short version:
- **Virginia** = the global epicenter (Loudoun "Data Center Alley," ~665 centers). Energy is the strain.
- **Texas** = deregulated grid + drought; water use projected to jump **~8x to 399 billion gallons by 2030.**
- **Georgia** = sharpest *residential water harm* (Newton County wells ran dry near Meta).
- **Arizona** = desert-water paradox; Tucson rejected a $3.6B project (Aug 2025).
- **Ohio** = the **best precedent**: regulators forced data centers (>=25 MW) to pay for 85% of their contracted capacity so households don't subsidize them. Big Tech challenged it and lost.
- **Oregon (The Dalles)** = the landmark transparency case -- a city sued its own newspaper to hide Google's water use, then settled and revealed 274.5M gallons/year.

> **Everlight footprint note:** four of your active wholesale states -- **TX, GA, OH, AZ** -- are exactly the data-center hot zones. This is relevant to your real-estate business: utility-rate hikes, water stress, and community sentiment shifts move property values and buyer behavior in the same markets where Piper and the state agents are working. Worth watching as a macro signal, not just a curiosity.

---

## 7. SAN FRANCISCO BAY AREA + FAIRFIELD (your home turf)

Full detail in `06_BAY_AREA_FAIRFIELD_DOSSIER.md`. Headlines:
- **Fairfield / Solano County: NO confirmed data center yet.** Solano EDC markets the county to developers, but it's not built. So you're in an *early-warning* position, not a *damage* position -- which is exactly when public input matters most.
- **California Forever / "Solano Foundry"** is a manufacturing megaproject; in May 2026 Rio Vista's city manager warned it "could become the nation's largest data center." California Forever publicly **denies** that. Watch it.
- **Bay Area at large:** data centers *requested* 18.7 GW statewide (the "18 million homes" figure) -- but regulators only expect **4-6 GW to actually get built by 2040.** PG&E's real pipeline is **10 GW / 17 projects (2026-2030), mostly San Jose/Silicon Valley.** Santa Clara already sends **60% of its city power** to 55 data centers.
- **Your water:** Fairfield drinks mostly from **Lake Berryessa (Solano Project / Putah Creek)**, topped up by the State Water Project. Good news: as of early 2026 **Berryessa is near-full / above average.** California briefly exited drought entirely in Jan 2026, then spring 2026 turned sharply dry (near-record-low snowpack). Reservoirs healthy, snowpack scary -- both true.
- **Your power:** you're on **PG&E at ~32 cents/kWh** (among the highest in the U.S., up ~43% in 3 years). Any large CA data-center buildout intensifies the fight over who funds grid upgrades.

---

## 8. CAN THIS BE MITIGATED, OR DO PEOPLE JUST GET STEAMROLLED?

Both are happening. People are **not** universally getting pushed aside -- the pushback is working in real places. Full playbook in `07_MITIGATION_PLAYBOOK.md`. The proven levers:
1. **Ohio's tariff model** -- make data centers pay for their own grid (85% take-or-pay). Upheld against Big Tech's legal challenge. This is the single most replicable win.
2. **Local rejections** -- Tucson and Chandler AZ killed projects; 78 local moratoria in a year; ~300 bills across 30 states in early 2026.
3. **Transparency law** -- Oregon established water use is public record, not trade secret. Several states moving to ban government NDAs with developers.
4. **Recycled-water + zero-water cooling** -- Santa Clara runs 31 of 55 centers on recycled water; Microsoft is piloting zero-water designs. The tech to be a "good citizen" exists; it's a choice.
5. **Cost-causation rules** -- make the demand-creator pay for the upgrade (Arizona, Virginia proposals; California's SB 57 study).

What's **not** working yet: federal action (the Sanders/AOC "AI Data Center Moratorium Act," announced ~March 2026, has no clear path), and binding water-disclosure rules (California's AB 93 was vetoed Oct 2025).

---

## 9. YOUR THESIS, TAKEN SERIOUSLY -- THE RESOURCE PARITY PRINCIPLE

You said: *"You can't have technology using more resources than an actual human being... that doesn't justify human existence, that justifies technological existence, and that's where the machine has won."*

That is a real philosophical position with a name in policy circles: **per-capita resource entitlement / resource parity.** It says infrastructure should be measured against, and capped relative to, the humans it serves -- not given an open-ended claim on a finite commons.

The data says your instinct is directionally sharp: **one hyperscale center already consumes the water of ~50,000 people and the power of ~250,000.** The machine's footprint *already* dwarfs the individual's. By raw resource draw, on that single metric, "the machine has won" is defensible.

The honest counter (so you can argue this and win): a data center isn't *a* human -- it serves *millions* of humans. So the fair comparison isn't "1 building vs. 1 person," it's **"resources per person served"** or **"resources per unit of real value created."** On a *per-user* basis, an efficient data center is often *more* resource-efficient than everyone running their own hardware. The strongest version of your argument is therefore:

> "Fine -- serve millions. But you don't get to do it on **underpriced** water and **socialized** power while the host community eats the bill. Price the inputs at scarcity, make the operator pay its own grid and water cost, cap the local draw relative to local supply, and *then* let the market decide how big AI gets."

That reframes "the machine has won" from a doom statement into a **policy demand** -- and it's a demand that's already winning in Ohio and Arizona. I built you a tool to make this concrete: `resource_parity_calculator.py` lets you plug in a proposed center's water/power and instantly see "this equals N humans" and "is it paying its own way?" It's wired so **you** define the parity threshold -- because that's a values call, not a math call, and it should be yours.

---

## RED BOX -- CORRECTIONS TO WIDELY-SHARED CLAIMS

| Viral claim | Reality | Use instead |
|---|---|---|
| Diesel backup NOx "200-600x higher than gas plants" | **Unverified, likely false.** Real measured ratio ~6-20x. | "Diesel/gas generators emit far more NOx per MWh than grid gas plants (roughly 6-20x)." |
| "$5.4 billion health cost (Caltech/UC)" | **Not in the paper.** Study says **~$20B/yr & ~1,300 deaths/yr by 2030.** | The $20B/yr 2030 projection, labeled as a projection. |
| "80% NO2 rise in Boxtown, Memphis" | **Misframed.** +79% *peak at the fence-line*, +9% in Boxtown, +3% area-wide; a competing study found little PM2.5 change. | "Peak NO2 right at the facility rose ~79%; the broader-neighborhood effect is contested." |
| "1.7 million gallons/day per facility" | Likely a **units error** from 1.7 billion liters/day (the U.S. national figure). | "Up to 5M gal/day for very large facilities (peak)." |
| "Bay Area / PG&E asked for 18.7 GW" | That's **statewide requested**; forecast build is **4-6 GW by 2040**. PG&E's pipeline is 10 GW. | Use the 4-6 GW forecast + PG&E 10 GW pipeline. |
| "70% of internet traffic goes through N. Virginia" | **Debunked**; realistic ~22%. | "Northern Virginia is the world's densest cluster (~22% of traffic)." |

---

## WHAT TO WATCH (next 6-12 months)
1. **California Forever / Solano Foundry** -- does a data-center use surface despite the denial? (Your backyard.)
2. **The AI capex bubble** -- if revenue disappoints, watch for the stranded-asset bill to hit ratepayers.
3. **Ohio-style tariffs spreading** -- the cleanest win to copy. Track AZ, VA, CA SB 57 study (due Jan 2027).
4. **Federal moratorium bill** -- low odds, but its hearings will surface the best data.
5. **PG&E rate redesign (March 2026)** -- changes how your own bill is structured.

*Companion files: `01_WATER_REPORT.md` | `02_ENERGY_GRID_AND_MONEY.md` | `03_HEALTH_AND_ECOLOGY.md` | `04_WHO_BENEFITS_AGENDA_POLITICS.md` | `05_STATE_BY_STATE.md` | `06_BAY_AREA_FAIRFIELD_DOSSIER.md` | `07_MITIGATION_PLAYBOOK.md` | `SOURCES.md` | `data_center_360_dashboard.html` (graphs) | `resource_parity_calculator.py`*
