# Polymarket YouTube Transcripts -- Distilled Insights (2026-05-29)

8 transcripts ingested + cross-referenced against our research-based STRATEGY.md.
Raw -> wiki -> output (karpathy intake). Honest separation of REAL edge vs HYPE.

## REAL, FREE, recurring edges (worth building -- and now wired)
1. **Smart-money copy-trade** -- follow vetted profitable wallets; signal on their
   fresh BUYs. The single most-cited accessible edge across the videos (Creo Bot's
   "AI Match", leaderboard copy-trading). BUILT: `dataflows/smart_money.py` reads
   Polymarket's public /trades feed for a wallet watchlist, feeds research + 360
   synthesis (one signal among many; never auto-fires). Discipline: VET wallets,
   they drift, most "top" wallets are stale bots.
2. **Read the RULES, not the title** -- multiple videos: titles mislead (e.g. "Mega
   ETH mcap 1 day after launch" resolves NO if not launched by expiry regardless).
   Already partly covered by our objective-resolution screen; deepen with a
   rule-ambiguity check in the predictor later.
3. **Trade OUT, use LIMIT orders, watch liquidity/slippage** -- confirmed; already
   in our design (limit_price, liquidity scanner filter, trade-out not hold).

## CONFIRMS our research/build (validation)
- ~16% win rate cited; most users lose (matches "84% lose"). Manual beginner in
  "$100->$1000" actually LOST the full $100. Discipline + edge selection is the game.
- Fees now real (maker fees on crypto) -- we corrected pnl_model.
- Domer ($3M/yr) + French whale ($80M) = information edge, not replicable at $250.
- Polymarket legit now: CFTC-cleared, NYSE-owner invested $2B, ~$9B valuation,
  Trump Jr. advisory. Real platform, here to stay.

## HYPE -- affiliate marketing, do NOT calibrate expectations to these
- **"60% daily ROI" / "$3,500/day" / "$20k/month" (PolySniper)** -- a bot PRODUCT
  being sold; numbers cherry-picked/unverifiable. NOT our model.
- **"$500/day arbitrage" (arbs.xyz)** -- real concept, but cross-platform arb needs
  Kalshi (US KYC) + sub-3-second speed; a bot war we lose at $250 (our research).
  arbs.xyz is an affiliate tool sale.
- **"$50->$800 in days" / "10-40% per trade" 15-min BTC candle scalping (Bullpen)**
  -- gambling on near-50/50 candles with fees; math does not survive. "Farm points
  for token launch" = speculative airdrop farming, not a trading edge.
- **Creo Bot / referral codes / "Polymarket Pro codes"** -- referral-driven funnels.

## The honest anchor
Our model: ~15%/mo base case at a REAL ~55% win rate, mid-single-digit honest.
The videos promise 30-60%/DAY. Those are product ads. We compound the real edge.

## Net new build from this intake
- `dataflows/smart_money.py` + config `smart_money:` block (wallets watchlist).
- 6 tests. Wired into gather_signals (degrades if no wallets set).
- Next (optional): rule-ambiguity check in predictor; auto-vet wallets from the
  trade feed (consistent profit + moderate volume, exclude mega-bots).
