# Polymarket Strategy -- evidence-based, sourced (2026-05-29)

Built from real research (mainstream journalism + academic papers + Polymarket
primary docs). Honest premise: **~84% of Polymarket traders LOSE; profits
concentrate in the top ~0.03% (mostly bots).** We do not pretend to join that
top tier at $250. We target the one documented retail edge with discipline, and
size so a bad resolution can never compound into ruin.

## What does NOT work at our scale (don't build these)
- **Arbitrage (Polymarket vs Kalshi):** real but a sub-3-second bot war; 73% of
  profit goes to sub-100ms bots. We lose this race at retail latency.
- **News-latency sniping:** first-mover value compressed to 5-8c; needs 1-5ms
  execution. Not winnable on our infra.
- **Market-making / liquidity rewards:** only "meaningful" at $20k+. Not at $250.
- **Copy-trading the leaderboard:** most top wallets are bots; their on-chain
  trades are stale by the time we see them. Fragile.
- **Predicting novelty/pop-culture/awards markets:** worst-calibrated (subjective
  resolution). NEVER forecast these.
- **The $80M "French whale":** one-time proprietary-information edge (private
  neighbor polls) + huge capital. Not replicable. Lesson: the only true edge is
  information the market lacks -- which we rarely have cheaply.

## What DOES have real evidence (our edge)
**Favorite-longshot calibration fade -- as a SCREEN, not a prediction engine.**
- Longshots (<=10c) are systematically OVERpriced; heavy favorites (>=90c)
  slightly UNDERpriced. Outcomes priced <10% actually occur ~14% of the time.
- Strongest in LOW-LIQUIDITY, NON-POLITICAL, OBJECTIVE-resolution markets.
- Politics: favorites underpriced at long horizons (prices compress toward 50%)
  -- real but you trade against the sharpest crowd, so small + selective only.
- Crypto/finance threshold markets: near-perfectly calibrated at the midpoint,
  so only trade the bias at the EXTREMES, never the 50/50.

## Hard rules encoded into the bot
1. **Objective resolution only.** Skip any market whose resolution is subjective
   (awards, "best", vibes). Read the rule, not the title.
2. **Category preference:** Sports (best short-horizon calibration + lowest 0.03
   fee) > objective Crypto/Finance thresholds > Politics (small, selective).
   Avoid novelty for prediction.
3. **Fee-aware (NEW 2026):** taker fee = `C x feeRate x p x (1-p)`, PEAKS at 50c,
   shrinks toward extremes. Per category: Crypto ~0.07, Politics/Finance/Tech
   ~0.04, Culture/Weather ~0.05, Sports ~0.03, Geopolitics 0. Makers pay 0.
   Favor edges near the extremes (lower fee AND where our edge lives).
4. **Spread is the dominant cost on thin markets** -- budget 3-10% round-trip;
   only trade thin markets when mispricing clearly exceeds spread.
5. **Enter ~10-14 days before resolution** (before late liquidity tightens
   spreads + accuracy spikes to 90%+). Min 4h to resolution.
6. **Trade OUT, never hold to UMA resolution by default** -- disputes cost a
   $750 bond, prohibitive at $250. Need depth to exit.
7. **Negative skew discipline:** selling longshots wins ~92-95% but the rare loss
   is large. Quarter-Kelly (already coded) + hard 5% per-market cap + <=20%
   deployed at once. Most blowups are SIZING, not picking.
8. **Wallet = source of truth, halt on >$0.01 drift** (the XLM-loss lesson).

## Realistic expectation (honest)
- High raw win rate from longshot-fade, but small net edge per trade after spread
  + fee. Mid-single-digit monthly ROI is honest; low-double-digit is optimistic.
- Do NOT model calibration accuracy as ROI. Calibration != profit after costs.
- The calibration gate (20 resolved paper trades, Brier<0.25, win>52%) must pass
  before any real money.

## Sources (credibility-noted)
- CBS/60 Minutes (Theo whale), The Block, DL News, Finance Magnates -- journalism
- arXiv 2602.19520 (Le 2026, calibration by domain), SSRN Reichenbach/Walther,
  NBER w15923 (favorite-longshot theory) -- academic
- Polymarket docs (fees, disputes) -- PRIMARY
- tradetheoutcome, sergeenkov, managebankroll -- data blogs (directional, verify)

Full sourced report in the session research (2026-05-29). Bias-direction has a
literature conflict (longshots overpriced vs favorites underpriced at long
horizons) -- both say "prices insufficiently extreme"; do NOT hard-code one
number, run a LIVE calibration check.
