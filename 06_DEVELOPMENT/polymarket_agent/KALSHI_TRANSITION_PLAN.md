# Polymarket -> Kalshi Transition Plan
**Everlight Ventures | Autonomous Prediction-Market Trader | 2026-06-02**

## Why we are moving (the verified facts)
Polymarket geoblocks US persons at order placement and blocks **datacenter/VPN IPs** on top of restricted countries -- PROVEN 2026-06-02 by routing a real order through a German VPS and still getting 403. The only IP bypass is a residential proxy, which is costly + circumvents a CFTC-mandated block. Dead end.

**Kalshi** is the legal answer, cross-verified 2026-06-02:
- CFTC-regulated US exchange, **no geoblock for US persons**.
- **Bots explicitly allowed**; free REST + WebSocket API, official Python SDK.
- **$10 minimum**, ACH free, debit 2%. No monthly fees.
- Binary event contracts 1c-99c -- SAME structure as Polymarket (Yes/No, settle $1/$0).
- Fee = `ceil(0.07 * P * (1-P) * 100)/100` per contract (taker); makers ~25% of that. **No gas.**
- **15-min / hourly / daily BTC+ETH range markets** -> the fast-calibration candle lane ports.
- Rich event universe (Fed, CPI, jobs, weather, sports, crypto) -> BETTER fit for our news/Claude edge than Polymarket's crypto-heavy set.

## Does the strategy change? Mostly NO -- the brain is the same
The edge philosophy is identical: estimate probability, find edge vs market price, only stake when net-of-cost EV clears AND the book grows, size by quarter-Kelly + growth ladder, catch convex/asymmetric bets, and prove it on paper (calibration) first. What changes is the VENUE PLUMBING and three tactical shifts:

1. **No gas -> the cost floor drops.** `meets_profit_target` loses its "2x gas" term. More trades clear the gate; the ~50c coinflip rejection is now driven by fees alone. Net: more actionable trades than on Polymarket.
2. **Maker orders cut fees 75%.** Posting resting limit orders (maker) instead of taking the book drops the fee from 1.75c -> ~0.44c per contract at 50c. New tactic: PREFER maker limits, fall back to taker only when we need the fill. This is a real, free edge Polymarket did not offer.
3. **Richer event universe.** The predictor (Claude + Perplexity + news intel) has far more to chew on -- Fed decisions, econ prints, weather -- where research beats the crowd more reliably than on coin-flip crypto candles. The 360-synthesis approach gets stronger here.

## Architecture map: what we KEEP, ADAPT, REPLACE, DELETE

| Module | Action | Notes |
|---|---|---|
| `agents/predictor.py` | **KEEP** | Claude/Perplexity probability engine -- venue-agnostic |
| `agents/risk_manager.py` | **KEEP** | Quarter-Kelly + growth ladder + convexity -- unchanged |
| `growth.py` | **KEEP** | Compound ladder ($1k->$10k->...) -- unchanged |
| `agents/scanner.py` | **ADAPT** | Point at Kalshi market schema; objective-resolution screen stays |
| `costs.py` | **ADAPT** | Kalshi fee `0.07*p*(1-p)` taker / `0.0175*p*(1-p)` maker, ceil-to-cent, per contract; DROP gas term; keep net-EV + clears-costs gate |
| `settle_paper.py` / calibration | **ADAPT** | Settle via Kalshi market settlement (settles $1/$0); shadow-prediction calibration ports as-is |
| `dataflows/crypto_candle.py` | **ADAPT** | -> Kalshi 15-min/hourly BTC/ETH range markets (settled on CFB RTI); momentum lane + shadow calibration port |
| `main.py` orchestration | **ADAPT** | Same cycle shape; swap venue calls |
| `dataflows/polymarket_clob.py` | **REPLACE** | -> `dataflows/kalshi_api.py` (public: /series /events /markets /orderbook -- NO auth) |
| `execution/clob_live.py` | **REPLACE** | -> `execution/kalshi_exec.py` (RSA-PSS signed REST: place/cancel/balance/positions) |
| `execution/wallet.py`, `swap_usdc.py`, `enable_trading.py`, `withdraw.py` | **DELETE** | No on-chain anything. Massive simplification + removes the whole web3 attack surface |
| `execution/reconciler` (vs on-chain) | **ADAPT** | Reconcile vs Kalshi `/portfolio/balance` (USD). "Balance is source of truth, drift>X = halt" doctrine ports directly |
| geo proxy / egress (`_apply_egress`, `polymarket_proxy_setup.sh`, CF worker) | **DELETE** | Kalshi is US-legal. No proxy needed. (VPS already destroyed 2026-06-02) |

## The conversion workflow (phased, each phase shippable + tested)

**K0 -- Operator step (Rich, in parallel with K1-K3):**
  1. Create + verify a Kalshi account (KYC -- you are a US person, this is the legal venue).
  2. Fund it small via ACH or debit ($25-100 to start; ACH is free).
  3. Generate an API key: dashboard -> API -> create -> save the **Key ID** + download the **RSA private key** (.key). Hand me the Key ID + key file path (store the key in `03_Credentials/`, never in chat).

**K1 -- `kalshi_api.py` (public market data, NO auth) [I can build + test NOW]**
  Live market list, event/series metadata, prices, orderbook. Plus `find_crypto_market()` for the 15-min/hourly BTC range markets. Proves the data layer against real Kalshi today.

**K2 -- `costs.py` Kalshi fee model** + drop the gas term from `meets_profit_target`. Unit-tested with the published fee table (1.75c max at 50c taker).

**K3 -- `kalshi_exec.py` (RSA-PSS auth, needs K0 key)**
  Sign requests (timestamp+METHOD+path, RSA-PSS SHA-256), place/cancel limit (maker-first) + market (taker) orders, read balance + positions. The "wallet balance is truth" -> "Kalshi balance is truth" reconciler.

**K4 -- scanner + predictor + calibration repoint to Kalshi.** Shadow-prediction calibration accrues on Kalshi 15-min crypto + a few liquid event markets.

**K5 -- candle/momentum lane -> Kalshi 15-min crypto** (CFB-RTI settled). Maker-first.

**K6 -- reconciler vs Kalshi balance** (drift>$0.01 halt -- the XLM-disaster preventer, simpler with a clean USD balance).

**K7 -- paper calibration on Kalshi -> small live (maker orders) -> growth ladder.**

## What we DELETE (and why it is a win)
The entire on-chain stack -- web3, Polygon RPC, USDC.e, EIP-712 signing, allowance approvals, the swap, the reconcile-vs-chain, AND the geo proxy -- all gone. That stack was the source of most of the complexity and the $0.01-drift fragility. Kalshi is a clean USD balance behind an API key. Simpler = safer.

## Cross-checks / risks (verified, eyes open)
- **Maker fills are not guaranteed** -- a resting limit may not fill; logic must time-out to taker when the edge is worth the higher fee. (Net still cheaper than Polymarket overall.)
- **$116 USDC.e is on Polygon, not Kalshi** -- it does not transfer. Either withdraw/repurpose it, or just fund Kalshi fresh (small) via ACH. Decide separately; it does not block the build.
- **Kalshi rate limits** -- generous for our cadence; respect them in the client.
- **Market hours / settlement timing** -- event markets settle on schedule; calibration uses real settlement, no oracle guess.
- **KYC required** -- expected and fine; this is the legal, US-person venue (the whole point).
- **Market firehose is mostly thin strike buckets** (VERIFIED 2026-06-02: first 200 open markets were all zero-volume auto-generated crypto range buckets). The scanner MUST filter by series + volume/open_interest, not consume the raw /markets feed. This is a scanner-design note, not a blocker -- the read paths (markets/detail/orderbook) are proven working against live Kalshi.

## Status (2026-06-02)
- VPS destroyed (billing stopped). Geo/proxy/egress path abandoned (proven dead).
- K1 STARTED + PROVEN: `dataflows/kalshi_api.py` reads live Kalshi markets/detail/orderbook (public, no auth). Unit-tested (`tests/test_kalshi_api.py`).
- NEXT: Rich does K0 (account + fund + API key). Then K2 (fees) + K3 (signed orders).

## Effort estimate
K1-K2 (data + fees): I build + test today, no account needed. K3 (auth/orders): ~half a build session once the API key exists. K4-K6: incremental. K7: gated on paper calibration clearing. The brain (predictor/risk/growth/calibration) is already built -- this is a venue swap, not a rebuild.
