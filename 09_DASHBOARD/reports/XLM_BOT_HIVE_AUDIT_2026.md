# XLM Bot Hive Audit 2026
Generated: 2026-03-16 UTC

## Verdict
The bot is materially stronger than before, but it is not yet "best in the world." The main weakness is no longer raw strategy logic. The main weakness is operational edge density: too much good intelligence is hidden, some context is still inferred instead of directly measured, and the system still lacks a closed loop from pattern -> expectancy -> capital scaling -> monetization.

The current build is good enough to trade carefully. It is not yet good enough to press size aggressively.

## What Is Working
- Coinbase-first contract trading on `XLP-20DEC30-CDE`
- Lane V bidirectional liquidation logic
- Growth ladder and 2-contract readiness logic
- Margin-window playbook with attack vs defense behavior
- Order-entry preflight and protection-state inspection
- Live Oracle runtime, dashboard, liquidation feed, websocket feed, and watchtower

## Highest-Value Gaps
### 1. Edge Measurement Is Still Weaker Than Edge Creation
The bot can detect setups, but it still does not maintain a first-class expectancy table by:
- lane
- session window
- direction
- cluster side
- volatility regime
- hold time bucket
- time-to-target bucket

Consequence:
- the bot can recognize a setup without proving which versions of that setup actually print money
- capital scaling risks being based on confidence instead of measured expectancy

### 2. Liquidation Intelligence Is Better, But Still Partly Inferred
The system has a live liquidation feed, but it still falls back to price and OI inference on some cycles.

Missing alpha:
- full exchange-native liquidation density history
- persistence of repeated sweep levels across sessions
- sweep-to-reclaim latency statistics
- cluster decay logic after repeated taps

Consequence:
- the bot may still overrate stale liquidity magnets
- reversal quality can look stronger than it really is

### 3. Order Book Intelligence Is Still Too Thin
The bot reads product-book context, but it still needs stronger microstructure features:
- pull/cancel aggression near cluster
- best-bid / best-ask replenishment speed
- imbalance persistence instead of point-in-time imbalance
- spoof suspicion flags
- absorption score after sweep

Consequence:
- it sees location, but not always the quality of participation at that location
- this is exactly where false reversals survive longer than they should

### 4. Session Edge Is Modeled, But Session Expectancy Is Not
The bot now understands `INTRADAY_ATTACK`, `PRE_CUTOFF_DEFENSE`, and `OVERNIGHT_DEFENSE`.

What is still missing:
- win rate by session mode
- average MAE/MFE by session mode
- expected hold time by session mode
- Friday break behavior profiling
- pre-cutoff forced-exit slippage profile

Consequence:
- the playbook is directionally right, but not yet numerically optimized

### 5. Execution Visibility Was Too Hidden
Before this pass, the dashboard did not clearly show:
- live session playbook
- real protection mode
- whether exchange TP or software protection was active
- live blind spots degrading the signal

Consequence:
- you had to trust the bot without seeing the safety state
- that creates avoidable operator confusion and bad manual overrides

### 6. Monetization Loop Is Still Weakly Coupled To Trading Performance
The bot is improving, but the monetization system around it is still underused.

Missing business loop opportunities:
- publish redacted trade recaps automatically as content
- maintain a public scoreboard with delayed stats
- turn session reports into educational assets, newsletters, or premium signals
- use the bot's structured reasoning as product inventory, not just private telemetry

Consequence:
- the trading engine is not yet fully monetizing the data exhaust it already creates

## Patterns The Bot Still Needs To Learn Better
### A. Repeated Sweep Failure
If the same cluster gets swept multiple times without a strong displacement, reversal quality degrades quickly.

Needed:
- per-cluster touch count
- failed follow-through counter
- cluster freshness score

### B. Sweep + Absorption + Immediate Continuation Failure
Some of the best reversals are not just wick reclaims. They show:
- sweep
- aggressive counterfill
- failure to continue in sweep direction on the next impulse

Needed:
- post-sweep impulse failure score
- delta between sweep candle and next candle range efficiency

### C. Session Open / Restart Imbalance
Good moves often begin when the contract re-enters activity with one-sided pressure.

Needed:
- session-reopen imbalance profile
- post-break expansion classifier
- Friday break risk model

### D. Range Box Magnet Compression
Balanced liquidity on both sides is already a no-trade condition, but there is a second pattern:
- price compresses under or over a major cluster
- book tilts
- then one side gets vacuumed

Needed:
- compression depth score
- time-in-box counter
- breakout quality after compression

### E. Funding / Basis Trap
The bot already uses crowd context softly, but it still needs sharper trap logic:
- positive funding + overhead short-liq cluster + weak continuation
- negative funding + downside long-liq cluster + weak continuation

Needed:
- trap score combining basis, funding, and cluster geometry

## Gaps That Can Directly Cause Loss
### 1. Margin-Window Ambiguity
Coinbase blocks the margin-window endpoint on this key, so the bot uses the ET fallback schedule.

This is acceptable, but not ideal.

Risk:
- if Coinbase changes the schedule or eligibility, your internal model can drift

### 2. Exchange Bracket Uncertainty
The bot now exposes whether exchange TP was actually armed or whether software protection is carrying the position. That transparency is good, but it highlights a risk:

Risk:
- operator assumes native bracket protection exists when the bot is really managing exits in software

### 3. No First-Class Slippage/Fee/Funding Decomposition Dashboard
You need to see:
- gross edge
- fees
- funding paid/received
- slippage
- net edge after execution friction

Risk:
- a strategy can look profitable on price movement but fail after execution costs

### 4. No Expectancy-Based Capital Promotion
The growth ladder is currently capital-based plus margin-based. It should also be expectancy-based.

Risk:
- deposits can create the illusion of readiness before the strategy has earned bigger size

## Monetization Opportunities Being Left On The Table
### 1. Trade Content Engine
Each structured trade memo can become:
- internal learning record
- public redacted recap
- Slack + Drive + Calendar artifact
- premium subscriber content

### 2. Session Intelligence Product
Your session playbook and contract-specific intelligence could be packaged as:
- delayed market brief
- XLM session map
- premium "attack / defense" report

### 3. Strategy Research SKU
The bot's labeled feature store can become a research product:
- best reversal hours
- best wick types
- best sweep depths
- best cluster freshness profiles

### 4. Operator Dashboard Premiumization
The same dashboard primitives could later support:
- public delayed scoreboard
- member-only strategy diagnostics
- managed account / signal review tools

## What The Dashboard Still Needed
This pass closes the biggest UI blind spots:
- session playbook card
- execution safety card
- blind-spot card

Still recommended next:
- expectancy by lane/session/regime
- fee/funding/slippage decomposition
- Friday break countdown and risk badge
- "why flat" timeline for the last 20 blocked setups
- contract ladder panel for 1/2/3/5 contract readiness

## Ranked Next Builds
### Tier 1
1. Expectancy table by lane, session, and regime
2. Fee/funding/slippage decomposition
3. Friday break / reopen risk model
4. Contract ladder readiness panel through 5 contracts

### Tier 2
1. Cluster freshness and repeat-sweep degradation
2. Order-book absorption and replenishment scoring
3. Post-sweep continuation-failure model
4. Pre-cutoff forced-exit analytics

### Tier 3
1. Public delayed trade scoreboard
2. Premium XLM session brief productization
3. Auto-published redacted trade recaps
4. Content pipeline from bot reports into Everlight properties

## Bottom Line
The biggest remaining gap is not "more AI." It is measured edge concentration.

The bot now knows enough to trade carefully. To become elite, it needs:
- better expectancy accounting
- deeper microstructure truth
- tighter session analytics
- visible execution state
- stronger monetization of the intelligence it already produces

That is how this becomes not just a bot, but a business asset.
