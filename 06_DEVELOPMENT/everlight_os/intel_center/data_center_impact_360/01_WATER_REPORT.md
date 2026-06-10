# WATER REPORT -- Data Center Impact 360
### Everlight Intel Center | 2026-05-21 | sources in SOURCES.md

## 1. How much water (the benchmarks)

| Facility | Water | Human equivalent |
|---|---|---|
| One person, home | 82-100 gal/day | baseline |
| Mid-size center (10-20 MW) | ~110M gal/year | ~1,000 households |
| Large/hyperscale (peak) | up to 5,000,000 gal/DAY | town of ~50,000 |
| Real example: Google Council Bluffs IA | ~3.9M gal/day withdrawn, ~2.8M consumed | -- |
| Real example: Google The Dalles OR (2021) | 274.5M gal/year | ~25% of the whole city |
| Real example: Meta Newton County GA | 500,000 gal/day | ~10% of the county |

**National (the corrected figures):**
- U.S. data centers **directly** consumed **~17 billion gallons in 2023** (Lawrence Berkeley National Lab, Shehabi et al., Dec 2024). Projected **38-73 billion gal/year by 2028.**
- **Indirect** water (the power plants that feed them) was ~211 billion gallons in 2023 -- roughly **10-12x the direct figure**, but this number is highly methodology-dependent (swings with how you count hydro evaporation and renewable power contracts). Treat with a caveat.
- The older, viral "449 million gallons/DAY in 2021" figure is a secondary-literature consensus estimate, not a measured value. Use the LBNL 17B/year figure as the solid anchor.
- **Do NOT use "1.7 million gallons/day per facility"** -- that is almost certainly a units error from "1.7 billion liters/day" (the converted national number).

## 2. WUE -- the accountability metric (chart 02)

Water Usage Effectiveness = liters of water per kWh of compute. **Lower is better.** This single number tells you whether an operator is a "good citizen" or "rogue."

| Operator / design | WUE (L/kWh) | Note |
|---|---|---|
| Legacy industry average (evaporative) | 1.8-1.9 | Skews high; predates modern designs |
| Google (on-site, ~2023) | ~1.1 | Varies by year/scope |
| Microsoft (FY24 / FY25) | 0.30 / 0.27 | From Microsoft's own disclosure |
| AWS (air-cooling mix) | 0.15-0.19 | Not apples-to-apples (more air cooling) |
| Air-cooled / zero-water design | ~0 | The "good citizen" ceiling |

The lesson: a 60-90x difference between best and worst is a **design and disclosure choice**, not physics.

## 3. What happens to the water (chart 04)

- **~80-85% EVAPORATES** in evaporative cooling. Gone to the atmosphere, not returned to the local supply. This is the part people miss when they say "it's just cooling water."
- **~15-20% is discharged as "blowdown"** -- warmer, saltier, and chemically treated.

**Cooling types and their water trade-off:**
| Type | Water | Trade-off |
|---|---|---|
| Evaporative towers | Highest (~80-85% lost) | Best energy efficiency in heat |
| Closed-loop / recirculating | Cuts freshwater up to ~70% | Higher cost/complexity |
| Air-cooled | Near-zero on-site | Uses more electricity (raises *indirect* water) |
| Liquid immersion | Near-zero on-site | Newest; best heat transfer |

## 4. Is the 20% discharge toxic? (your specific question)

**Short answer:** not "instant poison," but not clean tap water either, and genuinely harmful to ecosystems if mismanaged.

The blowdown contains:
- **Corrosion inhibitors** (molybdates; historically phosphates/zinc)
- **Biocides** (chlorine/halogens, which can form regulated trihalomethanes; or zinc-based for Legionella control)
- **Scale inhibitors**
- **Concentrated minerals/salts** -- TDS up to ~2,000 ppm (evaporation leaves salts behind), plus leached metals (copper, zinc)

**To humans:** it is industrial wastewater, not drinking water. Properly permitted, it goes to a treatment plant and is diluted to legal limits before it ever touches a drinking supply. Drinking it raw would be harmful (biocides are designed to kill microbes). You are never supposed to drink it.

**To the environment (the real risk):**
1. **Thermal pollution** -- discharge commonly 86-104F; warm water holds less oxygen, stressing/killing fish, especially in summer.
2. **Chemical toxicity** -- biocides/chlorine harm fish, invertebrates, algae.
3. **Salinity creep** -- repeated discharge raises salinity in freshwater systems over time.

**Honest limit:** the strongest aquatic-harm science is from power plants generally (decades of thermal-discharge studies + EPA Clean Water Act 316(b) intake rules). For *data centers specifically*, toxicity is documented as a **mechanism and risk**, not yet as a confirmed named fish-kill in peer-reviewed literature. There's also a separate **PFAS ("forever chemical")** angle from certain coolants -- documented as a mechanism, not yet quantified at a named site.

## 5. Can it be recycled?

Yes, and the good operators do:
- **On-site reuse** of blowdown (needs extra filtration/reverse osmosis -- costs money/energy).
- **Non-potable / recycled municipal water** instead of drinking water for cooling (Santa Clara CA runs 31 of 55 centers this way; San Jose's Microsoft DC04 is designed for ~680 acre-feet/year of recycled water).
- **Zero-water designs** -- Microsoft announced (Dec 9, 2024) chip-level closed-loop cooling that uses no evaporative water.

The tech exists. Whether a given center uses it is a choice driven by cost and local rules.

## 6. Sources & depletion

- Water is drawn from municipal potable supply, groundwater wells, and surface water -- the mix varies by site. Groundwater wells are the flashpoint in rural/desert siting.
- Documented harm: **Newton County GA** (private wells fouled near Meta; water rates +33%); **Arizona** (Tucson rejected Project Blue over water; a contractor caught trucking water out); **Iowa** (40 unpermitted wells found at a site, 2025).
- **Texas projection (verified, HARC):** data-center water use rising from **~49 billion gallons (2025) to ~399 billion by 2030** = ~6.6% of all Texas water, ~= drawing Lake Mead down 16 ft/year. No Texas law currently caps it. (Chart 05.)
- **>40%** of planned/existing U.S. data centers sit in high or extremely-high water-scarcity areas; **>two-thirds** of post-2022 builds are in drought-stressed areas.

## 7. Water economics (why it's mispriced)

- **Mesa AZ:** Google pays **$6.08 per 1,000 gal**; residents pay **$10.80** -- the largest user pays ~44% less, in a desert. (Chart 09.)
- Municipal water is priced on average embedded cost + volume discounts for big flat-load customers, **not on scarcity value**. Below-scarcity price -> over-consumption by the biggest buyer. Textbook externality.
- **No market price signal:** the only liquid U.S. water benchmark (Nasdaq Veles California Water Index) tracks California ag/municipal *rights* and is driven by snowpack/drought, not data centers (which buy municipal water at negotiated rates in TX/VA/AZ/GA). Data-center water demand is **largely invisible to the one place water is actually priced.** That invisibility is itself the danger -- nobody is forced to look at the meter.
