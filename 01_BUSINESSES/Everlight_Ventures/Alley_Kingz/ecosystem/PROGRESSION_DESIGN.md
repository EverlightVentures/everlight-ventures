# Alley Kingz -- Single-Player Progression Loop
Author: Aisha Vance (progression). Shipped 2026-06-09 on the bj-finish branch.
Closes the audit's #1 CRITICAL: matches now grant XP, coins, and card drops; levels
climb; all 8 deck slots are reachable; the shop and the deck lab share one inventory.

## Where it lives
- Match rewards + levels + reward screen: `game/index.html` (inside the main inline IIFE)
- Shop sync shim: `game/shop/shop.js`
- `engine.js` and `canon.js` are untouched. The hook is `showResult(g)` in index.html,
  which reads the finished `AK.game` state from the renderer side.

## The profile (single source of truth for single player)
Everything persists in `localStorage.ak_profile`:

```
{ level, xp, coins, trophies, owned: [card names], decks: [8 slots], active }
```

- `level` starts at 1, caps at 21. `xp` is the partial progress toward the NEXT level.
- `owned` is keyed by card NAME (matches canon names; verified all 106 shop catalog
  names exist in canon).
- `trophies` is reserved for the ladder; nothing grants it yet.
- All localStorage access is guarded, so the headless node harness never throws.

## Reward table (granted once per match in `grantMatchRewards`)
| Outcome | XP | Coins | Card drops |
|---|---|---|---|
| WIN (or Clean Sweep) | 40 | 60 | 2 |
| LOSS | 15 | 20 | 1 |
| DRAW | 15 | 20 | 1 (treated as a loss) |
| Per convoy Gate cleared (`g.gatesCleared`) | +10 each | -- | -- |

Forfeits count as losses and still pay out (the `g._rewarded` flag stops double grants).

## Card drop weights
Rolled per drop from the full canon catalog (cards + spells), weighted by rarity:

| Rarity | Weight |
|---|---|
| Common | 70 |
| Rare | 22 |
| Epic | 7 |
| Mythic | 1 |

- Legendary is intentionally absent from match drops -- it stays shop and Lucky Draw
  exclusive.
- A drop the player already owns converts to +5 coins instead (shown as a dupe chip
  on the reward screen).

## XP curve
Level N needs `80 + 40*(N-1)` XP to advance. Cap is level 21.

| Level | XP to next |
|---|---|
| 1 | 80 |
| 5 | 240 |
| 10 | 440 |
| 20 | 840 |

Total XP from 1 to 21: 9,600. At a winning pace (~60 XP/match) that is roughly 160
matches to max -- the existing `SLOT_UNLOCK = [1,3,6,9,12,15,18,21]` deck-slot gates
now unlock on schedule with zero changes to the deck lab.

## Reward screen
`showResult` calls `grantMatchRewards(g)` then `renderRewards(rw)`, which fills the
`#rewardpanel` block on the result screen: +XP, +Coins, one chip per card drop
(rarity-tinted, dupes marked "+5c"), and a LEVEL UP callout that flags "NEW DECK SLOT"
when the new level sits on the SLOT_UNLOCK table. Gold-on-vanta, portrait, built with
safe DOM methods, fully guarded. A new Lobby button on the result screen returns to
the start screen and re-renders the player chip so level changes show immediately.

## Shop sync shim (`profileSync` in shop.js)
Problem: the shop writes server inventory keyed by `player_id`; the deck lab reads
`localStorage.ak_profile.owned` by card name. Without a bridge, purchases never
appear in the deck lab.

Fix: after any grant resolves in the shop surface, the granted card names are ALSO
merged into `ak_profile.owned` (unique merge; coins merge when a grant includes them):

- Lucky Draw, demo mode: `localRoll` results sync before the reveal.
- Lucky Draw, online: server `results` sync on `r.ok`.
- Buy Copy, demo mode: previously blocked entirely; now grants the card locally and
  syncs it ("saved to your crew").
- Buy Copy, online: syncs the bought card on `r.ok`.
- Open chest, online: best-effort -- if the server response carries
  `r.grants.cards` / `r.grants.coins`, they merge too.

Shop duplicates merge as no-ops (server-side dupes feed the Garage upgrade economy;
the +5 coin dupe rule applies to match drops only).

Shop-first edge case: if the shop runs before the game ever has, the shim writes a
deckless stub profile (`{level, xp, coins, trophies, owned}`). On next game boot,
`loadProfile()` in index.html detects the missing `decks` array and merges the stub
over the starter set instead of dropping it, so nothing bought is ever lost.

## Verification (2026-06-09)
- `node ecosystem/tests/ak_match_harness.js` -> FULL MATCH RAN CLEAN.
- Stub-DOM behavioral test: boot profile correct; WIN paid 60 XP / 60+5 coins / 2
  drops with a live dupe conversion; LOSS paid 15 XP; third match crossed 80 XP and
  hit level 2 with carryover XP 45; reward panel rendered; lobby chip showed the new
  level; 10-pull demo draw synced 9 new cards into `ak_profile.owned`; demo Buy Copy
  synced; shop-first stub profile written correctly.
