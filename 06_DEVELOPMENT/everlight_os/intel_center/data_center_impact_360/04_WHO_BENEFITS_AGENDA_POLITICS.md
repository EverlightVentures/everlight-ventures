# WHO BENEFITS, THE AGENDA & THE POLITICS -- Data Center Impact 360
### Everlight Intel Center | 2026-05-21 | sources in SOURCES.md

## 1. The agenda -- why so big, why not small?

Your question: "why wouldn't they just want small data centers for themselves?"

Because **frontier AI training is one giant synchronized computation.** Thousands of GPUs must act as a single logical machine, linked by ultra-fast, low-latency interconnect (InfiniBand/RoCE at 400+ Gbps). Passive electrical interconnect maxes out at ~1 meter, which forces the chips to sit physically packed together. You cannot split a single training run across scattered small centers without crippling latency losses.

So the requirements are:
- **Colocation** -- thousands of chips in one place.
- **Uninterrupted gigawatt-scale power** for weeks/months, zero tolerance for a mid-run outage.
- **Massive cooling** for 30-100 kW per rack across thousands of racks.
- **Economies of scale** -- standardized hardware + automation drives cost-per-compute down (PUE ~1.1-1.2).

That's why it's hyperscale campuses with dedicated substations, not "a server closet per company."

**The arms race:** whoever has the most compute trains the best model first. OpenAI's "Stargate" (announced Jan 21 2025 with SoftBank, Oracle, MGX) is ~$400-500B and ~7 GW planned across TX/NM/OH/Midwest sites. It's a land-grab for the inputs of intelligence.

## 2. Who benefits / who's making the money

- **Tech giants + shareholders:** Microsoft, Google/Alphabet, Meta, Amazon, Oracle, xAI. Combined AI capex ~$300B+ (2025) -> planned **~$725B (2026)**. Alphabet nearing ~$4.3T valuation, +62% in 2025. The data centers are the engine behind that market value.
- **Utilities** that get to build rate-based infrastructure (they earn a regulated return on capital they deploy).
- **Construction/equipment vendors, Nvidia** (the chips), landowners who sell to developers.
- **Some local tax revenue + broadband** -- real but usually far smaller than promised.

## 3. Who pays

- **Ratepayers** (PJM: ~$9.3B / 63% of one capacity cycle; +$16-37/mo on bills). See `02_ENERGY_GRID_AND_MONEY.md`.
- **Taxpayers** (VA $1.6B/yr foregone; GA toward $2.5B).
- **Host community** air, water, quiet, and trust.
- **Future ratepayers** pre-funding unbuilt load (~$6.2B in the latest PJM auction).

## 4. The jobs reality (chart 08)

- Operations need ~0.15-0.35 permanent workers per MW; construction needs ~0.7-2.0 (temporary) per MW.
- Most centers run ~100-200 permanent staff; the most automated hyperscale campuses run on **20-50 permanent staff per 100 MW.**
- "Fewer than 150 permanent workers" is broadly true for many large centers but not a universal cap (range ~20-200). Brookings independently confirms muted permanent-employment effects vs. the hype.
- Bottom line: a temporary construction boom, then a skeleton crew -- against a permanently given-away tax base.

## 5. Do residents get access to the data center?

No. Residents do not get to use the facility or its compute. It serves remote corporate/developer clients over the internet. The local community gets the *externalities* (power/water/air/noise) and, sometimes, marginal broadband or tax benefits. The data inside is the operator's customers' -- cloud apps, AI training, financial systems, streaming, etc.

## 6. Do the data centers "talk to each other"?

Two distinct layers:
- **Within a campus (the supercomputer layer):** GPUs are stitched into one machine via InfiniBand/RoCE -- extremely tight coupling. This is the "one logical GPU" fabric.
- **Between centers (the internet/cloud layer):** they interconnect over long-haul fiber and meet at **Internet Exchange Points (IXPs)**, usually inside colocation facilities, where networks peer. Cloud "regions" are clusters of nearby centers; "availability zones" are isolated facilities linked by private fiber for failover.
- So: **inference and serving routinely span centers** (that's the internet). A **single frontier training run still mostly lives in one campus** -- though research (distributed/optical interconnect, Stargate's multi-site design) is actively working to break that constraint. They are not one global brain today; they are a resilient, interconnected grid.

## 7. The secrecy problem (why "people aren't voting for them")

- **NBC News** reviewed 30+ proposals across 14 states: in a majority, local officials signed **NDAs** and dealt with **shell-company LLCs** hiding the real developer.
- **Wisconsin:** at least four municipalities signed secret NDAs; Meta operated as "Degas LLC"; a predevelopment agreement was approved without "data center" appearing in the minutes.
- **Page AZ:** emails showed the mayor asking the developer for talking points to "pacify" "unreasonable citizens."
- **Memphis xAI:** ran turbines with no permits, no public input, no notice to nearby majority-Black communities.
- This is why your instinct ("people aren't voting for them") is correct: the permitting often **bypasses public input** by design. FL, MI, and NJ are considering bans on government data-center NDAs.

## 8. The politics / legislation

- **Federal:** "AI Data Center Moratorium Act," announced ~March 25 2026 by Sen. Sanders (with a Rep. Ocasio-Cortez House companion). Would pause new AI-center construction until federal safeguards exist. NOTE: no confirmed bill number; cite by name + date. Low odds of passing, but the hearings surface good data.
- **State/local:** ~300 data-center bills across 30 states in early 2026; statewide moratorium bills in ~11 states; local moratoria jumped from ~8 to **78 in a year.** Maine nearly became the first statewide moratorium (vetoed Apr 2026). Tucson and Chandler AZ rejected projects.
- **The model to copy:** Ohio's AEP tariff (see `05_STATE_BY_STATE.md`) -- forces data centers to pay for their own grid. Upheld against Big Tech's challenge.

## 9. The bubble question (the strategic uncertainty)

- **Overbuild risk:** analysts (Guinness, TradeEdge) warn physical buildout is outrunning AI revenue; stranded-asset risk if monetization disappoints.
- **Justified-demand view:** KKR, State Street argue absorption shows no overbuild yet and long-run demand justifies it.
- This is genuinely unresolved and it's the central financial risk -- because if it's a bubble, **ratepayers hold the stranded grid bill for decades.**
