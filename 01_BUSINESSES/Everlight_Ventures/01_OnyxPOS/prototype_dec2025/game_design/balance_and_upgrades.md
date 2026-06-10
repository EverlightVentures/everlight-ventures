# BCARDI Game Balance and Upgrades

## Core Scaling
- Stat scaling per level: stat(L) = stat_base * (1 + L * 0.07)
- Ability scaling per level:
  - Common/Rare: +3% effect per level
  - Epic: +5% effect per level
  - Legendary/Mythic: +7% effect per level

## Tower Scaling
- QHP(L) = QHP_base * (1 + L * q_scale)
- PTHP(L) = QHP(L) / 3
- Suggested: QHP_base = 3000, q_scale = 0.10

## Upgrade Costs
Token cost model:
- token_cost(L) = base_cost * (1.2 ^ (L-1))

Shard requirement model:
- shards_required(L) = base_shards * L

Base costs:
- Common: base_cost 20, base_shards 2
- Rare: base_cost 50, base_shards 3
- Epic: base_cost 100, base_shards 5
- Legendary: base_cost 200, base_shards 8
- Mythic: base_cost 400, base_shards 12

## Balance Sheet Targets
Target DPS bands by cost:
- Cost 1-2: 60-90 DPS
- Cost 3-4: 90-130 DPS
- Cost 5-6: 130-170 DPS
- Cost 7-8: 170-210 DPS
- Cost 9-11: 200-260 DPS

Target HP bands by role:
- Skirmisher/Blaster: 500-900
- Striker/Lancer: 900-1400
- Support: 700-1100
- Controller/Hacker: 700-1100
- Vanguard: 1600-2600
- Structure: 1000-1600
- Assassin: 1200-1700

Utility caps:
- Hard disable: 1.0-1.5s
- Slow: 20-35% for 2-3s
- Shield: 10-20% HP for 3-4s
- Heal: 4-6% HP per pulse (3 pulses)
