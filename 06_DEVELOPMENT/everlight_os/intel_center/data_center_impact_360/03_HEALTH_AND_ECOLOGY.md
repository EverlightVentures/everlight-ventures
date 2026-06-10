# HEALTH & ECOLOGY -- Data Center Impact 360
### Everlight Intel Center | 2026-05-21 | sources in SOURCES.md
*Compiled by Helix Patel (science/health beat) with a verification pass. Contested claims flagged.*

## 1. Air pollution & human health

**The headline study (use this, not the viral numbers):**
- Caltech / UC Riverside, "The Unpaid Toll" (arXiv preprint, Dec 9 2024). Authors: Han, Wu, Li, Ren, Wierman.
- Finding: U.S. data-center air pollution causes **~$20 billion/year in public-health costs and as many as ~1,300 premature deaths/year by 2030** (range 940-1,590).
- Backup generators in Northern Virginia alone: **$190-260M/year** in regional health costs; ~10x that ($1.9-2.6B) if run at maximum permitted levels.
- It's a **preprint** -- label it as a projection, not a measured present-day cost.

**Corrected viral claims:**
- "**$5.4 billion** health cost" -- NOT in the paper. Don't attribute it to Caltech/UCR. Use $20B/yr (2030 projection).
- Diesel "**200-600x** NOx vs gas plants" -- **unverified, likely false.** Real measured ratios are ~6-20x (vendor best-case ~20x; engineering like-for-like ~6-7x). Don't print 200-600x.

**Memphis -- xAI "Colossus" (the live case):**
- xAI ran dozens of methane gas turbines (counts grew through 2025; ~35 seen by air mid-2025, 46 later listed at the Southaven MS site) to power the supercomputer, with permit fights.
- NAACP + Southern Environmental Law Center + Earthjustice are litigating (federal suit reported April 2026); turbines could emit up to **>1,700 tons NOx/year**, plus PM2.5, CO, and formaldehyde -- potentially the largest single NOx source in the Memphis metro.
- **The "80% NO2" claim, corrected:** a University of Tennessee satellite analysis found **peak NO2 +79% immediately around the facility**, but only **+9% in the Boxtown neighborhood** and **+3% area-wide.** A separate academic analysis (The Conversation, Sep 2025) found **little measurable PM2.5 change** and noted the area was already over the NO2 limit before xAI. The dispute is live and turns on which pollutant and which spatial scale you measure.
- Context: SW Memphis industrial-source cancer risk was already ~4.1x the EPA threshold before xAI (ProPublica).

## 2. Aquatic & wildlife ecology

**Honesty flag:** the best-quantified aquatic-harm science is from POWER PLANTS generally, not data centers specifically.

- **Thermal pollution (well-established for power-plant cooling):** discharge raises receiving-water temp ~10-20F; warm water holds less oxygen; can kill fish, block migrations, favor nuisance species. EPA Clean Water Act 316(b) requires intake-mortality cuts of 80-95% across ~550 facilities.
- **Biocide/chlorine discharge (data-center-relevant, but descriptive not field-quantified):** cooling blowdown carries biocides (chlorine dioxide, bromine, isothiazolinones, glutaraldehyde), corrosion inhibitors, and metals; if discharged or if treatment plants are overtopped, these threaten aquatic life. Data-center discharge cited as raising receiving-water temps ~5-15F.
- **PFAS angle:** data centers contribute to "forever chemical" pollution via certain coolants/components -- mechanism documented, site-specific toxicity not yet quantified.
- **No confirmed peer-reviewed, site-specific aquatic kill** attributable to a named data center yet. Report the mechanism and risk; don't overstate a specific kill event.

## 3. Environmental justice

- NAACP position: data centers are disproportionately sited in low-income communities and communities of color, with few lasting local jobs. Memphis/Boxtown is the sharpest single case.
- Regional concentration: the South carries both the densest buildout (VA, GA) and the highest low-income energy burden (GA, SC, AL, MS, AR).
- Methodology note: this is well-reported and consistent with prior environmental-racism literature, but a single definitive peer-reviewed *siting* study wasn't found. Frame as "well-reported pattern," not "proven by one study."
- **The regressive math:** low-income, Black, and Hispanic households can spend up to **20% of income on energy vs. 3%** for higher-income households -- so a flat $16-18/mo rate hike hits them ~7x harder in proportional terms.

## 4. Noise pollution (verified, concrete)

- Continuous cooling fans + generators run 24/7; levels reported to exceed **105 dB** at some sites; neighbors report headaches, vertigo, nausea, sleep disturbance, hypertension.
- **Prince William County VA:** routine exceedance of 60 dB, "catastrophic noise" complaints.
- **Chandler AZ:** CyrusOne cooling-fan hum led to muffling retrofits (2019), a 2022 zoning restriction, and a 2025 rejection of a new center.
- Noise is the **#1 reason cited** when data-center projects get cancelled; >=1/3 of all conflicts involve noise.
- Caveat: the worst complaints involve low-frequency infrasound that standard dB meters under-read, so readings can understate the felt impact.

## 5. The human chain of effects

```
Backup generators + retained gas/coal  -> NOx/PM2.5/NO2  -> asthma, respiratory illness, ~1,300 deaths/yr (2030 proj)
Water evaporation + blowdown            -> aquifer/reservoir stress + thermal/chemical loading -> wells fail, ag/drinking competition
Capacity-price spikes                   -> +$16-37/mo bills -> energy burden, regressive on poor households
24/7 cooling fans                       -> sleep loss, stress, lawsuits
Promised benefits don't land            -> eroded trust -> moratoria, litigation
```

**What's rock-solid vs. what's contested:**
- SOLID: PJM rate-hike numbers, Memphis litigation facts/turbine counts, power-plant thermal ecology, noise dB + zoning history, the energy-burden inequity.
- CONTESTED: the Memphis air-quality magnitude (satellite peak NO2 vs. neighborhood PM2.5), the EJ siting pattern as study-grade causation, data-center-specific aquatic kills.
- DO NOT PRINT: "200-600x NOx," "$5.4B health cost," "80% NO2 in Boxtown."
