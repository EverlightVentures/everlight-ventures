# MITIGATION PLAYBOOK -- Data Center Impact 360
### Everlight Intel Center | 2026-05-21 | sources in SOURCES.md
*"Are people really just gonna get pushed to the side?" -- No. Here's what's actually working.*

## THE FRAME
The fight is not "AI vs. no AI." It's **who pays, who decides, and what's the cap.** Every win below moves one of those three levers. People are NOT universally getting steamrolled -- the pushback is winning in real places.

## TIER 1 -- PROVEN WINS (already happened, copy them)

### 1. Make data centers pay for their own grid (Ohio model)
- Ohio regulators forced centers >=25 MW to **pay for 85% of contracted capacity** whether they use it or not, so households don't subsidize the buildout. Big Tech challenged it as discriminatory and **lost**. This is the single most replicable win in the country.
- **The ask:** cost-causation tariffs -- the demand-creator pays for the upgrade it triggers.

### 2. Local rejection (Arizona model)
- Tucson killed a $3.6B project (Aug 2025); Chandler rejected one (2025); 78 local moratoria in a year. Zoning + a willing city council can stop a project cold.

### 3. Transparency as public record (Oregon model)
- The Dalles established that data-center water use is **public record, not a trade secret.** FL/MI/NJ moving to ban government NDAs with developers. You cannot regulate what you can't see.

## TIER 2 -- DESIGN STANDARDS (make the operator a good citizen)

| Lever | What it does | Where it's happening |
|---|---|---|
| Recycled / non-potable water for cooling | Stops drinking-water draw | Santa Clara (31 of 55 centers), San Jose Microsoft DC04 |
| Zero-water / closed-loop cooling | Eliminates evaporative loss | Microsoft pilots (Dec 2024), Abilene Stargate |
| WUE disclosure + cap | Forces accountability on the key metric | Best operators already report <0.3 L/kWh |
| On-site/contracted clean generation | Stops the indirect-water + air-pollution chain | Anthropic pledge (Feb 2026), various PPAs |
| Backup-generator emission limits | Cuts NOx/PM2.5 health toll | EPA + local air permits (the Memphis fight) |

## TIER 3 -- THE PARITY PRINCIPLE (your idea, operationalized)

Your thesis: technology shouldn't get an open-ended claim on a finite commons that exceeds what it returns to the humans it shares that commons with.

Turn it into three concrete policy asks:
1. **Price inputs at scarcity.** End volume discounts that let the biggest user pay the lowest water/power rate (kill the Mesa $6.08-vs-$10.80 inversion).
2. **Local-supply cap.** No single facility may draw more than X% of the local water/power supply (Newton County GA's Meta center at ~10% of the county is the cautionary tale).
3. **Resource-per-value floor.** Require operators to report and improve resources consumed per unit of real service delivered, not just total -- so efficiency, not just scale, is rewarded.

The `resource_parity_calculator.py` in this folder makes #2 testable: plug in a proposed center's water/power and local supply, and it tells you the human-equivalent footprint and whether it breaches your parity cap. **You define the cap** -- it's a values call.

## TIER 4 -- WHAT'S NOT WORKING YET (manage expectations)
- **Federal moratorium** (Sanders/AOC, ~March 2026): low odds, no clear path.
- **Binding water disclosure** (California AB 93): vetoed Oct 2025.
- **Voluntary pledges:** real but unenforceable; they can't bind a grid operator to not pass costs through. Only tariffs/legislation can.

## FOR YOU SPECIFICALLY (Solano / Fairfield, pre-buildout)
Because nothing is built yet, you have the best leverage of all -- prevention:
1. Track the **California Forever / Solano Foundry EIR** for any data-center use; hold them to their stated binding power/water limits.
2. Get Solano County to adopt **cost-causation + recycled-water + disclosure conditions NOW**, before any application lands.
3. Show up to **Solano County Water Agency + city council** meetings. Pre-buildout public comment is where the leverage actually sits.

## THE ONE-LINE STRATEGY
Don't fight the technology. Fight the **subsidy and the secrecy.** Make them pay scarcity prices, fund their own grid/water, disclose everything, and cap the local draw. Ohio and Arizona already proved it works.
