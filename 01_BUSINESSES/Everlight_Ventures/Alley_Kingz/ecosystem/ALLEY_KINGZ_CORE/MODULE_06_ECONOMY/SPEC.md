# MODULE_06_ECONOMY -- ALK Token Economy (SPEC)

> Part of the 11-module Alley Kingz Core (see AK_MASTER_BLUEPRINT.md). Rule of the
> architecture: **no module imports another. All comms via EventBus pub/sub.** This
> module owns the in-game ALK ledger, the 7 burn sinks, staking, and the deflation
> dashboard. It never reaches into Crew/Raid/Live-Ops code directly -- it only
> emits and listens for events.

---

## 0. WHAT ALK IS (and is NOT)

- **ALK** = the in-game economy token. It is the unit the 7 sinks consume and the
  thing staking locks. It is an **off-chain, server-authoritative ledger** in V1.25 /
  V2 (browser + Unity). It is the blueprint's named "TOKEN ECONOMY (ALK)".
- **$BCARDD** = the on-chain settlement coin (Solana, pump.fun, fixed-supply 1B, dev
  cannot mint more). ALK is **not** $BCARDD. The on-chain bridge (ALK <-> $BCARDD) is a
  MODULE_10 adapter concern (Q4'26 Web3 phase), never a direct call from here.
- **NOS** = the pure soft currency (earned freely by play, never round-trips to
  $BCARDD without the rate-limited off-ramp). ALK sits one tier above NOS: it is
  scarcer, sink-bearing, and stakeable. NOS pays for routine upgrades; ALK pays for
  the high-stakes social/prestige sinks below.

### Legal boundary (HARD -- ECOSYSTEM_ARCHITECTURE.md LEGAL GATE 2)
On-chain "promised yield" is a Howey-test security. Therefore:
- ALK staking shares an **in-game fee pool** as a **utility reward** (access + game
  advantage), framed as in-game, never as a guaranteed return.
- The on-chain $BCARDD buyback-burn stays **weekly + discretionary + never a promised
  amount**. ALK staking math in this module MUST NOT be exposed to players as a
  $BCARDD/SOL APR. Copy law: "earn a share of in-game fees", never "earn yield".
- When the Web3 adapter eventually bridges ALK to $BCARDD, the staking-for-fee-share
  mechanic is gated behind that legal review. Until then ALK is a closed in-game unit.

---

## 1. INFLOWS (how ALK enters a player's balance)

ALK is *granted*, never minted by the player. Every inflow is an event the
CurrencyManager listens for and credits. Reuses the existing **ak_grants** reward rail
(supabase migration `20260614010000_grants_donations.sql`) and **economy.js**
(`AK_ECON`) earn paths -- this module does not re-implement the grant ledger, it
subscribes to it.

| Inflow | Event in | Cadence | Notes |
|---|---|---|---|
| Daily login | `ECONOMY_EARN` {source:"login"} | 1/day | Streak-scaled; small |
| Raid loot | `ECONOMY_EARN` {source:"raid"} | per successful raid (M03) | Variable reward |
| Task board | `ECONOMY_EARN` {source:"task"} | per task complete (M08) | Pixels-style board |
| Crew chest | `ECONOMY_EARN` {source:"crew_chest"} | timed open (M04/M05) | Shared anxiety reward |
| Staking dividend | `STAKER_POOL_PAYOUT` | on epoch close | Share of sink fees, below |
| Event prizes | `ECONOMY_EARN` {source:"event"} | live-ops (M08) | Seasonal |

**Anti-inflation rule:** total daily ALK emission is **capped** and treasury-tunable.
The CurrencyManager rejects an `ECONOMY_EARN` past the daily cap and emits
`ECONOMY_EMISSION_CAPPED` for the live-ops dashboard. No inflow path can run unbounded
(the Axie lesson).

---

## 2. OUTFLOWS / THE 7 BURN SINKS

Every sink is triggered by another module emitting `SINK_REQUEST` with a `sinkId`.
The CurrencyManager validates balance + debits, then emits `SINK_CONFIRMED`. TokenSink
listens for `SINK_CONFIRMED`, applies the burn/treasury/staker split, and emits
`ALK_BURNED` / `TREASURY_CREDITED` / `STAKER_POOL_CREDITED`. **The 7 sinks (LOCKED
numbers from AK_MASTER_BLUEPRINT.md):**

| # | sinkId | Cost (ALK) | Trigger module | Split |
|---|---|---|---|---|
| 1 | `prestige` | 500 | M07 Progression (prestige reset) | 100% burn |
| 2 | `war` | 200 / member | M04 Crew (war declaration) | 100% burn |
| 3 | `shield` | 100 | M03 PvP/Raid (emergency shield) | 100% burn |
| 4 | `relocate` | 150 | M02 Building (relocation) | 100% burn |
| 5 | `reroll` | 50 | M09 Creator/cosmetics (cosmetic reroll) | 100% burn |
| 6 | `marketplace` | 5% of sale | M09 Creator (NFT/marketplace fee) | **2.5% burn + 2.5% stakers** |
| 7 | `mint` | 25 | M09 Creator (creator mint) | 100% burn |

Notes:
- Sink #6 is the **only** split sink: a 5% marketplace fee = 2.5% burned out of supply
  + 2.5% credited to the staker pool. This mirrors the on-chain
  `AlleyKingzMarketplace.sol` FEE_BPS=250 / ROYALTY_BPS=250 constants so the off-chain
  and on-chain fee models are the same shape.
- Sink #2 scales by crew size: `200 * memberCount` is debited from the war chest at
  declaration. M04 supplies `memberCount` in the `SINK_REQUEST` meta.
- War-fee revenue (the burned 200/member) is part of the deflation engine, not a
  staker dividend -- only marketplace #6 feeds stakers in V1.

**Failure path:** if balance < cost, CurrencyManager emits `SINK_DENIED`
{sinkId, need, have} and debits nothing. The requesting module is responsible for the
"not enough ALK -> offer IAP" upsell (M08 live-ops).

---

## 3. STAKING

- **Lock:** 30-day lock. ALK staked is moved to a locked sub-balance; it cannot be
  spent on sinks or transferred until the lock matures.
- **Reward:** staked ALK earns a **pro-rata share of the staker fee pool** (currently
  fed only by marketplace sink #6's 2.5% staker slice). Payout is per epoch (epoch =
  weekly, treasury-tunable), distributed proportional to `stakedAmount * timeStaked`.
- **No compounding promise / no APR display.** See Legal boundary (sec 0). The UI shows
  "your share of this week's fee pool", a realized in-game number, never a forward APR.
- **Unlock:** at maturity the principal returns to spendable balance; the player may
  re-stake. Early unstake (if ever enabled) forfeits the pending epoch dividend -- never
  the principal.
- **Events:** `STAKE_LOCK` {amount} -> `STAKE_LOCKED` {amount, unlockAt}; epoch close
  emits `STAKER_POOL_PAYOUT` {playerShare} per staker; `STAKE_UNLOCK` at maturity ->
  `STAKE_UNLOCKED` {amount}.

---

## 4. DEFLATION TARGETS

The whole point: **supply trends down**. The CurrencyManager tracks rolling emission vs
burn and emits a `DEFLATION_TICK` for the live-ops dashboard.

- **Inflation target: < 2% / month** (net new ALK in circulation). Computed as
  `(emitted - burned) / circulating` over a trailing 30-day window. If the trailing
  rate breaches 2%, emit `DEFLATION_ALERT` so live-ops can tighten emission caps or run
  an extra sink event. The engine never silently mints.
- **Staked target: 40% of circulating ALK locked.** A high staked ratio shrinks liquid
  supply (anti-dump) and routes more players into the 30-day retention loop. Below 40%,
  live-ops leans into staking incentives (event multipliers on the fee pool); the module
  reports the live `stakedPct` on every `DEFLATION_TICK`.
- These are **dashboard targets and tuning levers**, not hard caps -- the only hard cap
  is the daily emission ceiling (sec 1).

---

## 5. SIX MONETIZATION LAYERS

Revenue mix the economy is designed to support (AK_MASTER_BLUEPRINT.md target split):

| # | Layer | Target % of revenue | How it touches ALK |
|---|---|---|---|
| 1 | IAP (gem/ALK packs, chest bundles) | 40-50% | Primary ALK on-ramp; gems stay server-only |
| 2 | Rewarded ads | 15-20% | Small ALK / NOS grants; capped (sec 1) |
| 3 | Subscriptions / VIP / Alley Pass | 20-25% | Pass XP + ALK stipend; VIP fee discounts |
| 4 | Web shop D2C | 10-15% | Direct ALK/cosmetic sales off-platform-fee |
| 5 | NFT marketplace | 5-10% | Sink #6 (2.5% burn + 2.5% stakers) |
| 6 | Staking | 2-5% | Fee-pool participation; locks supply (sec 3) |

Gems are server-only and never handled by this module (economy.js doctrine: "GEMS ARE
SERVER-ONLY"). ALK packs purchased via IAP arrive as an `ECONOMY_EARN`
{source:"iap"} grant from the server, bypassing the daily emission cap (paid inflow is
not farmed inflow) but still logged to the deflation tracker.

---

## 6. EVENTBUS CONTRACT (canonical event names)

All UPPER_SNAKE, matching the blueprint's `CREW_UNDER_SIEGE` style. The bus instance is
**injected** into each module's `init(bus, opts)` -- never imported. This is how the
"no direct imports" rule is honored.

**Listened by CurrencyManager (inbound):**
- `ECONOMY_EARN` {source, amount, meta} -- credit ALK (cap-gated)
- `SINK_REQUEST` {sinkId, amount?, meta} -- validate + debit for a sink
- `STAKE_LOCK` {amount} / `STAKE_UNLOCK` {amount}
- `STAKER_POOL_PAYOUT` {playerShare} -- credit a staker dividend back to balance

**Emitted by CurrencyManager (outbound):**
- `ECONOMY_BALANCE_CHANGED` {balance, locked, delta, reason}
- `SINK_CONFIRMED` {sinkId, amount, meta} -- TokenSink listens for this
- `SINK_DENIED` {sinkId, need, have}
- `ECONOMY_EMISSION_CAPPED` {source, requested, granted}
- `STAKE_LOCKED` {amount, unlockAt} / `STAKE_UNLOCKED` {amount}
- `DEFLATION_TICK` {monthlyInflationPct, stakedPct, circulating, burned30d}
- `DEFLATION_ALERT` {monthlyInflationPct} -- only when > 2%/mo

**Listened by TokenSink (inbound):**
- `SINK_CONFIRMED` {sinkId, amount, meta} -- apply the burn/treasury/staker split
- `STAKER_EPOCH_CLOSE` {epochId} -- distribute the accrued staker pool

**Emitted by TokenSink (outbound):**
- `ALK_BURNED` {amount, sinkId} -- removed from supply (deflation tracker reads this)
- `TREASURY_CREDITED` {amount, sinkId}
- `STAKER_POOL_CREDITED` {amount, sinkId} -- the 2.5% slice of sink #6
- `STAKER_POOL_PAYOUT` {playerId, playerShare} -- per-staker at epoch close

---

## 7. REUSE / DO-NOT-REBUILD

- **economy.js (`window.AK_ECON`)** already owns chests/scrap/keys/coins + the
  atomic `mutateProfile` read-modify-write and guarded localStorage. The ALK balance
  persists through the **same profile object** (a new `p.alk`, `p.alkLocked` field via
  `ensureShape` backfill) so there is one save path, not two. CurrencyManager calls into
  the grant rail by **event**, not import -- in the browser build the thin glue that
  bridges `ECONOMY_EARN` -> `AK_ECON.mutateProfile` lives in the bootstrapper, not here.
- **ak_grants rail** (`20260614010000_grants_donations.sql`) is the server-side grant +
  donation ledger. Server-authoritative ALK grants (IAP, raid loot validated server-
  side) flow through it; the client module just reflects the resulting balance.
- New fields are **default-falsy** (alk:0, alkLocked:0, stakeUnlockAt:0) so a profile
  with no ALK history is byte-identical to today -- no migration break (mirrors the
  handler-classes "all new fields default-falsy" doctrine).

---

## 8. FILES

- `SPEC.md` -- this document.
- `CurrencyManager.js` -- ALK ledger: balance, earn (cap-gated), sink debit/validate,
  staking lock/unlock, deflation tracking. Stub.
- `TokenSink.js` -- the 7 sinks' split logic + staker-pool accrual/payout. Stub.

Both stubs: zero direct imports, EventBus injected via `init(bus, opts)`,
headless-safe (no top-level DOM / localStorage), JSDoc-documented.
