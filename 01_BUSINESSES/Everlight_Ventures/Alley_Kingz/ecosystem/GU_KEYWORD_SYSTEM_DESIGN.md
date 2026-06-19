# Alley Kingz -- Keyword System (the Gods Unchained borrow)

**Decision (locked by operator):** stay a REAL-TIME LANE BATTLER. Do NOT go
turn-based. Borrow GU's card legibility + faction identity + combat juice, NOT
its turns/mana. This is a polish + readability layer on the engine we already have.

## The borrow in one line
GU cards "read their role" from keyword tags. We add the same tags to Alley Kingz
cards -- surfaced as little chips ON the card -- each wired to an engine flag we
mostly already have. A card becomes legible at a glance, like a real TCG.

## GU keyword -> Alley Kingz (real-time) mapping
| GU keyword | What it means in GU | Alley Kingz real-time version | Engine hook | Build |
|---|---|---|---|---|
| **Frontline** | must be attacked first (taunt) | enemies in the lane lock this dog first | `card.frontline` -> findTarget priority | NEW (small) |
| **Hidden** | untargetable until it attacks | spawns stealthed; first attack reveals | **REUSE `stealthT`** (Shadow handler) | reuse |
| **Blitz** | acts the turn it's played | no deploy wind-up -- attacks on spawn | `card.blitz` -> spawn `atkCD=0`, skip DEPLOY hold | NEW (small) |
| **Ward** | immune to the first spell | negates the first spell that hits it | `u.ward` -> castSpell consumes + skips | NEW (small) |
| **Protected** | absorbs the first damage instance | one-hit full damage negate | `u.protect` -> takeDamage eats first hit | NEW (small) |
| **Regen** | heals each turn | heals a little every second | **REUSE `regenPct`** (Mender pattern) | reuse |
| **Burn X** | takes X dmg each turn | damage-over-time tick | `burnT`/`burnDmg` status (beside slow/stun) | NEW (small) |
| **Twin Strike** | attacks twice | second hit on the same swing | `card.twinStrike` -> doAttack fires 2x | NEW (small) |
| **Deadly** (Deathtouch) | any damage kills | first hit kills the target | `card.deadly` -> doAttack zeroes target hp | NEW (balance-gated) |
| **Afterlife** | triggers on death | drops a token / effect when it dies | `card.afterlife` -> death path (reuse spawnDrone) | NEW (small) |
| **Roar** | triggers on cast | on-deploy effect | **ALREADY HAVE** (deploy abilities) | reuse |
| Confused / Backline | 50% mis-target / hide behind | map to a CC status / Frontline inverse | later | defer |

Sources (current GU keyword definitions, verified live 2026-06-15):
Official GU Glossary, GU Wiki Terminology, GU "12 Essential Card Mechanics",
gunchained.app Keywords.

## Faction = identity (the other big GU borrow)
Each of our 4 factions gets a signature keyword kit, so faction reads as
*mechanics*, not just color -- exactly how GU's domains work:
- **Boneguard (War / tank):** Frontline + Protected -- the wall.
- **Zoomie Syndicate (Speed):** Blitz + occasional Hidden -- hit before they react.
- **Leashbreak Tactix (Anger / aggro):** Burn + Twin Strike + (rare) Deadly -- punishers.
- **K9 Circuitry (Magic-tech):** Ward + chain/splash (already have) + turrets -- control.
- Cross-faction utility: Regen (medic dogs), Hidden (Shadow-aligned).

## How the chips render (legibility = the #1 win)
- A KEYWORD REGISTRY: `{id, label, glyph, color, desc, engineFlag}`.
- Cards carry `keywords:[...]` in canon data.
- Chips render in: the Chop Shop card inspect (Info tab, gd-style) + the in-match
  card-in-hand corner + a tooltip on tap. Faction-tinted, same gold-glass vibe.

## Build phases (each shippable + reversible)
1. **P1 -- Legibility (ZERO engine risk):** keyword registry + `keywords` data on
   cards + render the chips on the card inspect + hand. This alone is the big
   "reads like a TCG" win the analysis flagged. Nothing in combat changes.
2. **P2 -- Reuse wiring:** Hidden->stealthT, Regen->regenPct, Roar (already),
   Ward (small). Default-falsy -> byte-identical when a card has no keyword.
3. **P3 -- New flags:** Frontline (target priority), Blitz, Protected, Burn,
   Twin Strike, Afterlife -- each a single guarded engine read (same discipline
   as the handler system: unequipped = no behavior change).
4. **P4 -- Faction kits + balance:** assign keywords per faction, tune, verify.

## Combat juice (free polish, already have the primitives)
Wind-up telegraph + impact freeze-frame + knockback already exist (`kbVx/kbVy`,
hit-stop). Deepening the lunge/clash/recoil is engine-tuning, not new systems.

## IP note
All research was on Gods Unchained (a public game). Nothing Alley Kingz-specific
was sent to any external search -- per the protect-Rich's-IP rule.
