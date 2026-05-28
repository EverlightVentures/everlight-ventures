# Polymarket Live Trader -- Design Spec

**Date:** 2026-05-28
**Owner:** Lucrex (Hive Mind orchestrator) + Rex Thornton (risk) + Cipher Wolfe (scanner/predictor) + Bull Archer (research) + Thomas Rourke (postmortem)
**Operator:** Rich (final decision authority on bankroll, kill-switch, halt-clear)
**Status:** PENDING OPERATOR APPROVAL of this spec, then writing-plans phase

## 1. Purpose + Operator Context

Polymarket Live Trader is the small-chip-maker in Rich's three-tempo passive-income
strategy (small=Polymarket, medium=XLM revived later, large=wholesale). The XLM bot
LOST $500+ via confused paper-vs-real reconciliation in May 2026. This spec is
designed first and foremost to PREVENT THAT FAILURE MODE on a new venue.

- **Bankroll:** $250 USDC.e on Polygon (operator-funded, one-time).
- **Max bet:** 5% of bankroll ($12.50 to start, scales with bankroll).
- **Daily-loss circuit breaker:** -$37 (-15% of bankroll).
- **Max concurrent positions:** 10.
- **Live-trade default:** OFF. Two-factor opt-in (env var + executor re-check) to enable.
- **Operator success criterion:** Bankroll grows. Stays profitable. Does NOT confuse
  paper and real. Reconciles cleanly every cycle.
- **Operator failure criterion:** Repeats the XLM ghost-trade pattern. Drift between
  internal accounting and on-chain wallet.

## 2. Constraints (Golden Rules)

These constraints are non-negotiable, sourced from operator-corrected HARD LAW
memory entries. Spec must satisfy ALL of them.

1. **FREE-FIRST** (`feedback_free_first_golden_rule`). Zero recurring tool spend.
   Only money out is the $250 wallet seed. Every infrastructure choice exhausts
   existing-infra / OSS-self-host / free-tier / build-from-scratch BEFORE proposing
   anything paid. No "$4/mo VPS." No Twitter API. No paid proxies.
2. **WALLET = SOURCE OF TRUTH** (`project_xlm_bot_parked_2026_05_28`). On-chain
   balance is the only authority. Internal accounting reconciles every cycle.
   Drift > $0.01 = HALT. Sticky halt.
3. **NO PAPER-LIVE MODE TOGGLE** in the live executor. Paper mode = a completely
   separate module path that never imports wallet or signing code. Different file
   = impossible to confuse.
4. **EVERY STATE TRANSITION CROSSES A FILE BOUNDARY.** No agent passes data to the
   next via RAM. Each agent reads/writes JSON ledgers. Grepping the file tells you
   exactly what state the bot was in at any moment.
5. **MACRO-MICRO CARVE-OUT** (`feedback_apply_macro_micro_gate_before_recommendation_list`).
   Polymarket is MACRO -- does not gate Deal 1 (TN wholesale). Operator explicitly
   carved it out as parallel track 2026-05-28. Build proceeds; Deal 1 stays primary.
6. **BRANDED COMMS** (CLAUDE.md doctrine). Every Slack alert via
   `content_tools.branded_slack`. Every email via `content_tools.branded_mailer`.
   Every weekly report via `content_tools.gdocs_bridge.publish_gdoc()`.
7. **STRUCTURED LOGGING** (`logging_standard`, `canonical_log_line`). One canonical
   log line per cycle. JSON logs to `logs/polymarket.jsonl`. No PII (wallet address
   is operational data; private key never leaves the secrets vault).

## 3. Architecture

### 3.1 Repo Layout (Phase 1, standalone in `polymarket_agent/`)

```
06_DEVELOPMENT/polymarket_agent/
  main.py                         # Existing; rewire as orchestrator shim
  config.yaml                     # Existing; extend
  execution/
    __init__.py
    exceptions.py                 # Mirror executor_alpaca exception classes
    wallet.py                     # Polygon wallet load + EIP-712 signing
    executor_polymarket.py        # 9-check defensive pattern
    executor_polymarket_paper.py  # ENTIRELY SEPARATE; never imports wallet.py
    reconcile.py                  # On-chain truth vs internal state
  dataflows/
    __init__.py
    interface.py                  # Common Signal shape
    polymarket_clob.py            # Markets + orderbook + positions
    perplexity_sonar.py           # Wraps xlm_bot.ai.perplexity_advisor
    telegram_signals.py           # Telegram Bot API (free, unlimited)
    rsshub_client.py              # Self-hosted RSSHub on e5-mother
    orderbook_sentinel.py         # Internal volume/liquidity spike detector
    rss_news.py                   # Reuters/AP/BBC/CoinDesk/ESPN
  agents/
    __init__.py
    scanner.py                    # Cipher Wolfe
    researcher.py                 # Bull Archer
    predictor.py                  # Cipher Wolfe
    risk_manager.py               # Rex Thornton
    postmortem.py                 # Thomas Rourke / 56_data_verifier
  data/
    active_markets.json           # Scanner output
    research_briefs.json          # Researcher output
    predictions.json              # Predictor output
    approved_bets.json            # Risk manager output
    open_bets.json                # Executor output (mutable ledger)
    closed_bets.json              # Settled positions
    calibration_ledger.jsonl      # Brier/log-loss history
    bankroll_state.json           # Internal accounting (gets reconciled)
  logs/
    polymarket.jsonl              # Canonical log lines
  tests/
    test_executor.py
    test_reconcile.py
    test_risk_manager.py
    test_calibration.py
  podman-compose.yml              # Existing; extend
  Dockerfile                      # Existing; extend
  systemd/
    polymarket-agent.service      # Restart=always
    polymarket-postmortem.timer   # weekly Sunday 6 PM PT
```

Phase 2 (deferred): absorb into `06_DEVELOPMENT/trading_agents/` framework as a
new venue. Designed so the migration is `mv` + import-path rewrite, not a refactor.

### 3.2 Venue + Geo

- **Venue:** Polymarket offshore CLOB on Polygon (chain 137). Markets via
  `gamma-api.polymarket.com`; orders via `clob.polymarket.com`.
- **Geo routing:** Cloudflare Worker proxy at `clob-proxy.everlightventures.io`
  (FREE on existing CF zone, 100k req/day tier; our peak is ~3k req/day). Worker
  egresses from CF network; Polymarket sits behind CF; geo-block bypassed by being
  in the same network. Worker source in
  `06_DEVELOPMENT/cloudflare_workers/polymarket_proxy/` deployed via `wrangler`.
- **Geo fallback (if CF Worker blocked):** Second Oracle Always Free tenancy in
  `eu-frankfurt-1` via an ImprovMX `@everlightventures.io` alias. Run a tiny
  proxy (50-line `aiohttp` server) on the free instance. Still $0.
- **US-fallback (long game, not blocking Phase 1):** Add
  `executor_polymarket_qcx.py` adapter when QCX API opens. Same agent pipeline,
  different execution module.

### 3.3 Deploy Target

- e5-mother (Ampere ARM, tailnet, us-sanjose-1).
- Single podman container per `06_DEVELOPMENT/polymarket_agent/podman-compose.yml`.
- `systemd unit polymarket-agent.service` with `Restart=always` per
  Amendment XI (Samantha Law) heartbeat requirements.
- Cron-fired weekly postmortem (Sunday 6 PM PT).

## 4. Components

### 4.1 `execution/`

| Module | Public Interface | Key Invariants |
|---|---|---|
| `exceptions.py` | `PolymarketExecutorError` (base) -> `UnauthorizedInstrumentError`, `DollarCapExceededError`, `LiveTradingDisabledError`, `WalletReconciliationError`, `KillSwitchActiveError`, `OnChainBalanceShortfallError`, `OrderRejectedByVenueError` | Same names as `executor_alpaca.py` for Phase 2 migration ease. Each exception carries a `context` dict for branded Slack alerts. |
| `wallet.py` | `PolygonWallet(private_key_path).get_usdc_balance() -> Decimal`, `get_matic_balance() -> Decimal`, `sign_clob_order(order: dict) -> bytes` | Wallet load FAILS LOUDLY (RuntimeError, no silent fallback) if key file missing or zero balance. Private key never logged, never sent to LLM, only read by `sign_clob_order`. Reads from `03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key` (chmod 600, gitignored). |
| `executor_polymarket.py` | `PolymarketExecutor.submit_order(market_id, outcome, amount_usdc, limit_price) -> Bet` | 9 pre-checks in fixed order before any network call: (1) `LIVE_TRADING==true`, (2) `_state/HALT` does not exist, (3) `EV_TRADER_HALT!=true`, (4) market in active whitelist, (5) `amount<=max_bet_pct*bankroll`, (6) `open_positions<max_concurrent`, (7) `daily_pnl>-max_daily_loss`, (8) `wallet.get_usdc_balance()>=amount` (on-chain), (9) sign + submit + wait for fill + reconcile. ANY check failing raises the corresponding exception. |
| `executor_polymarket_paper.py` | `PaperExecutor.submit_order(market_id, outcome, amount_usdc, limit_price) -> Bet` | ENTIRELY SEPARATE module. Does not import `wallet.py`. Does not import `clob_client`. Maintains its own `data/paper_bankroll_state.json`. The ONLY way to switch from paper to live is to swap `main.py`'s executor import line AND set `LIVE_TRADING=true`. Cannot be confused with live. |
| `reconcile.py` | `Reconciler(wallet, clob, bankroll_state_path).reconcile_now() -> ReconcileResult` | Pulls on-chain USDC + open CLOB positions. Compares to `bankroll_state.json` + `open_bets.json`. Drift > $0.01 = `result.halt_required=True`. On halt: writes `_state/HALT` flag file with timestamp + drift detail; posts branded Slack alert to `#hive-alerts`; blocks all subsequent `executor.submit_order` calls. Sticky -- only `python3 -m polymarket_agent.clear_halt --operator-confirm` clears it. |

### 4.2 `dataflows/`

| Module | Public Interface | Key Invariants |
|---|---|---|
| `polymarket_clob.py` | `PolymarketCLOB(proxy_url).scan_markets() -> list[Market]`, `get_orderbook(market_id) -> Orderbook`, `get_positions(wallet_address) -> list[Position]`, `submit_order(signed_order) -> str` | Stateless. 30s cache on scan + orderbook. Only `submit_order` is called by `executor_polymarket.py`; never by agents directly. Uses CF Worker proxy URL from config. |
| `perplexity_sonar.py` | `Sonar.get_news_velocity(category, last_minutes=10) -> list[Signal]`, `query(prompt, cache_ttl=300) -> dict` | Thin wrapper over existing `06_DEVELOPMENT/xlm_bot/ai/perplexity_advisor.py`. Reuses its 15-min cache + risk_on/off/neutral tagging. Re-points category queries from XLM -> Polymarket categories. |
| `telegram_signals.py` | `TelegramBridge.get_recent_signals(last_minutes=10) -> list[Signal]` | Free Telegram Bot API. Bot subscribes to mirror channels (whalealert_official, etc.). Background daemon (`systemd polymarket-telegram-bridge.service`) appends to `data/telegram_signals.jsonl`. Append-only ledger; agent reads tail. |
| `rsshub_client.py` | `RSSHubClient.get_recent_tweets(usernames, last_minutes=15) -> list[Signal]` | Polls self-hosted RSSHub at `http://e5-mother:1200/twitter/user/{username}`. RSSHub runs as additional podman service on e5 (open-source, self-hosted, $0). 60s polling, ~1-2 min effective latency. |
| `orderbook_sentinel.py` | `OrderbookSentinel.check_spikes() -> list[SpikeAlert]` | Rolling 5-min volume + liquidity baseline per active market. Spike threshold 3x. Internal-only signal (the "follow the smart money" detector). Zero external cost. |
| `rss_news.py` | `RSSNews.get_recent_items(last_minutes=15) -> list[Signal]` | feedparser over Reuters / AP / BBC / CoinDesk / ESPN RSS. 60s polling. |
| `interface.py` | `@dataclass Signal(source, text, url, author, timestamp, credibility, sentiment, market_ids)` | Common shape across all sources. Predictor consumes `list[Signal]` agnostically. Same shape as `trading_agents/tradingagents/dataflows/interface.py`. |

### 4.3 `agents/`

| Module | Hive Persona | Reads | Writes | Key Invariant |
|---|---|---|---|---|
| `scanner.py` | Cipher Wolfe | `polymarket_clob.scan_markets()` (300+ markets) | `data/active_markets.json` (top ~30) | Filters by `min_liquidity=$5k`, `min_volume_24h=$1k`, `min_time_to_resolution=4h`, `max_spread=0.05`. Markets only -- no predictions yet. |
| `researcher.py` | Bull Archer | `active_markets.json` + 5 dataflows in parallel | `data/research_briefs.json` | Per-market aggregation: signals grouped by source, sentiment scored, key facts extracted by Claude Sonnet 4.6. Cross-checked by `clx_delegate.py` (Codex) for the top 3 by predicted alpha per cycle. |
| `predictor.py` | Cipher Wolfe | `research_briefs.json` + brain policy from `polymarket_bridge` | `data/predictions.json` | Claude Sonnet 4.6 narrative probability estimate per market. Brain bridge multiplies confidence by `(decisive*0.3 + logical*0.3 + plasticity*0.2 + self_healing*0.2)`. Output: `Prediction(market_id, outcome, predicted_prob, market_price, edge, confidence, reasoning, signals)`. Min edge 5% to pass downstream. |
| `risk_manager.py` | Rex Thornton | `predictions.json` + `bankroll_state.json` + `open_bets.json` + `daily_pnl.json` | `data/approved_bets.json` | Quarter-Kelly sizing: `bet_size = bankroll * (edge / odds) * 0.25`, hard-capped at `max_bet_pct * bankroll`. All 9 pre-checks duplicated here (defense in depth). Predictions failing any check are dropped with reason logged. |
| `postmortem.py` | Thomas Rourke / 56_data_verifier | `closed_bets.json` | `calibration_ledger.jsonl` + branded Slack `#xlm-trading` + branded email + GDoc | Computes Brier score, log loss, win rate, P&L. Weekly Sunday 6 PM PT branded report via `publish_gdoc()`. If Brier > 0.30 or win rate < 50% over 20+ closed bets, posts branded alert recommending halt. |

### 4.4 `main.py`

Sequential cycle every `scan_interval` (default 5 min):

```
1. scanner.scan() -> active_markets.json
2. researcher.research() -> research_briefs.json
3. predictor.predict() -> predictions.json
4. risk_manager.evaluate() -> approved_bets.json
5. for bet in approved_bets:
     executor.submit_order(bet) -> updates open_bets.json
6. reconciler.reconcile_now() -> halt if drift
7. (every 60 min) postmortem.review_settled() -> closed_bets.json
8. canonical_log_line() to logs/polymarket.jsonl
```

Each step succeeds OR raises a typed exception that gets caught, logged, and
posted to branded Slack `#hive-alerts` with `auto_repair_target` tag per
`feedback_fail_loud_with_it_auto_repair`.

## 5. Data Flow (one 5-min cycle, concrete state-file transitions)

```
T+0s   main.py wakes (systemd timer or sleep loop)
T+1s   scanner reads polymarket_clob.scan_markets() (cached 30s if recent)
T+3s     writes data/active_markets.json
T+4s   researcher reads active_markets.json
T+4s     spawns 5 parallel dataflows: perplexity_sonar, telegram, rsshub, orderbook_sentinel, rss_news
T+12s    each dataflow returns list[Signal], merged per-market
T+15s    Claude Sonnet 4.6 narrative analysis per market (batched 5 at a time, prompt cached)
T+30s    (high-stakes only) clx_delegate.py cross-check
T+45s    writes data/research_briefs.json
T+46s  predictor reads research_briefs.json
T+47s    brain policy bridge multiplies confidence per market
T+50s    writes data/predictions.json (filtered to edge>=5%)
T+51s  risk_manager reads predictions.json + bankroll_state.json + open_bets.json
T+52s    Quarter-Kelly sizing + 9 pre-checks per prediction
T+53s    writes data/approved_bets.json (typically 0-3 bets per cycle)
T+54s  for each approved bet:
T+54s    executor 9 pre-checks (defense in depth)
T+55s    wallet.sign_clob_order(order)
T+56s    polymarket_clob.submit_order(signed)
T+58s    wait for fill confirmation (max 10s timeout)
T+59s    update open_bets.json + bankroll_state.json
T+60s  reconciler.reconcile_now()
T+62s    on-chain USDC vs bankroll_state.json
T+62s    on-chain open positions vs open_bets.json
T+63s    if drift > $0.01: write _state/HALT, alert, RAISE
T+64s  canonical_log_line emitted
T+65s  main.py sleeps until next cycle (T+5min)
```

Every state file is JSON or JSONL. Grepping any file at any time tells you what
state the bot was in. No in-RAM state across agent boundaries.

## 6. Error Handling + Kill Switches

In order of severity (least to most aggressive):

| Trigger | Action | Recoverable by |
|---|---|---|
| Single bet placement fails (network) | Retry once, log, skip if still failing | Auto (next cycle) |
| 3 consecutive losing bets | 5-min cooldown (`config.risk.cooldown_after_loss`) | Auto |
| Daily P&L < -$37 (-15% bankroll) | Halt for the day, branded Slack alert | Auto (next day 00:00 PT) |
| Bankroll < $200 (20% wiped) | Reduce `max_bet_pct` to 2%, branded Slack alert | Auto |
| Bankroll < $150 (40% wiped) | Halt + `_state/HALT` flag, branded Slack alert | Operator (`clear_halt`) |
| Reconciliation drift > $0.01 | Halt + `_state/HALT` flag, branded Slack alert with drift detail | Operator (`clear_halt`) |
| Manual: `EV_TRADER_HALT=true` env | Halt on next cycle, no new bets, existing positions held | Operator (unset env) |
| Wallet load failure | Crash with RuntimeError, systemd restarts, crashes again, branded alert | Operator (fix key file) |
| CF Worker proxy down | Fall back to direct CLOB call from e5-mother (probably geo-blocked, will fail loud), branded alert | Operator (check Worker) |

Halt clear procedure: `python3 -m polymarket_agent.clear_halt --operator-confirm`
prompts for explicit "I understand the drift was [X] and accept restart" then
60-second cooldown before next cycle runs.

## 7. Testing + Calibration

### 7.1 Unit tests (`tests/`)

- `test_executor.py`: each of the 9 pre-checks fires correctly; bypassing any raises the matching exception.
- `test_reconcile.py`: drift detection at $0.01 boundary; sticky halt; clear_halt requires confirmation.
- `test_risk_manager.py`: Quarter-Kelly math on synthetic edge cases; daily-loss boundary; max-concurrent cap.
- `test_calibration.py`: Brier score + log loss on synthetic predictions vs outcomes.

### 7.2 Paper-trade calibration gate (REQUIRED BEFORE LIVE FUND)

Phase 0c: run `executor_polymarket_paper.py` for minimum 20 resolved markets,
real Polymarket data, real research pipeline, fake fills. Calibration ledger
must show:

- Brier score < 0.25
- Win rate > 52% (need to beat ~50% + venue fees)
- P&L > 0 on paper bankroll

If these gates fail, do NOT fund the live wallet. Debug the predictor/researcher
first. This is the XLM-disaster prevention gate.

### 7.3 Live cutover criteria

After paper calibration passes:

1. Fund Polygon wallet with $50 USDC.e + $5 MATIC for gas (10% of $250 bankroll
   first; prove execution works before full fund).
2. Flip `LIVE_TRADING=true` + restart service.
3. Watch first 5 cycles. Verify reconciliation passes every time.
4. If 5 clean cycles + at least 1 successful fill, top up to $250.

If any reconciliation fails in the first 5 cycles, halt + debug. Do NOT proceed.

## 8. Phase 0 Verification Checklist (BEFORE any code is written)

1. **Cloudflare Workers test**: deploy a 20-line "hello world" Worker on
   `clob-proxy.everlightventures.io`. Verify it can fetch
   `https://gamma-api.polymarket.com/markets?limit=1` from CF and return JSON.
   PASS = green light Phase 1. FAIL = go to step 2.
2. **Oracle eu-frankfurt-1 fallback**: register second Always Free tenancy via
   ImprovMX alias. Verify direct fetch from EU IP works. PASS = use this. FAIL
   = go to step 3.
3. **US-Polymarket QCX path**: research QCX API status. If API open, build
   `executor_polymarket_qcx.py` adapter. PASS = ship US-only. FAIL = halt
   Phase 1, escalate to operator.

## 9. What This Does NOT Include (YAGNI)

- Multi-venue arbitrage. One venue at a time.
- DEX integrations beyond Polymarket. The plan is Polymarket -> revisit XLM ->
  add stream 3. One at a time.
- Real-time WebSocket order book streaming. REST polling every 5 min is
  enough at this bankroll.
- Reinforcement-learning predictor. Claude Sonnet 4.6 + signals is the
  baseline. RL is a Phase 3 idea after we have 200+ resolved bets to train on.
- Twitter API. Telegram + RSSHub + Sonar covers 80-90% of velocity edge for
  $0. Revisit only after profitable operation funds the $100/mo.
- A dashboard. `logs/polymarket.jsonl` + branded Slack alerts + weekly GDoc
  report is the surface. Django dashboard at :8504 stays deferred per
  CLAUDE.md.

## 10. Rollout Phases

| Phase | Gate | Approx effort |
|---|---|---|
| 0a | CF Worker proxy deployed + verified | 1 hour |
| 0b (fallback) | Oracle eu-frankfurt-1 proxy | 2 hours |
| 1 | Spec approved (THIS DOC). writing-plans phase. | -- |
| 2 | Plan approved. Build per plan (TDD). | 2-3 sessions |
| 3 | Unit tests green | 0.5 session |
| 4 | Paper calibration (20 resolved markets, ~2-4 weeks real-time) | passive |
| 5 | Operator review of paper calibration ledger | 30 min |
| 6 | $50 live cutover; 5 clean cycles | 1 day |
| 7 | $250 full fund | -- |
| 8 (later) | Phase 2 absorb into trading_agents framework | 1 session |

## 11. Open Questions for Operator

1. **Phase 0a Cloudflare Worker test:** approve me to deploy a test Worker on
   the `everlightventures.io` zone? (Risk: noisy CF dashboard entry. Cost: $0.)
2. **Wallet creation:** approve me to generate a fresh Polygon wallet for this
   bot (separate from any existing wallet)? Private key stored at
   `03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key` chmod 600.
   Operator funds it manually post-creation.
3. **Bankroll funding:** confirm $250 USDC.e on Polygon, NOT main USDC. (USDC.e
   is the bridged token Polymarket requires; you'll need to bridge from
   USDC main on a chain like Base or Ethereum via stargate.finance or
   the Polygon bridge.)
4. **Telegram bot:** approve me to register a Telegram bot via @BotFather for
   the mirror-channel signals? (One-time setup, free, no PII.)
5. **Branded Slack channel for fills:** use existing `#xlm-trading` (config
   default) or create `#polymarket-trades`? `#xlm-trading` reuses the channel
   but conflates streams; `#polymarket-trades` is cleaner.

## 12. References

- Mirrors defensive pattern from `06_DEVELOPMENT/trading_agents/everlight/executor_alpaca.py:42`
- Reuses `06_DEVELOPMENT/xlm_bot/ai/perplexity_advisor.py` advisor pattern
- Reuses `06_DEVELOPMENT/everlight_os/neuromorphic/polymarket_bridge.py` brain bridge
- Reuses `03_AUTOMATION_CORE/01_Scripts/ai_workers/{ppx_terminal,clx_delegate}.py`
- Reuses `03_AUTOMATION_CORE/01_Scripts/content_tools/{branded_slack,branded_mailer,gdocs_bridge}.py`
- Spec pattern follows `06_DEVELOPMENT/everlight_os/docs/specs/2026-05-27-inbound-sentinel-design.md`
- Governing HARD LAW memories:
  - `feedback_free_first_golden_rule` (THE golden rule)
  - `project_xlm_bot_parked_2026_05_28` (do not repeat ghost-trade pattern)
  - `feedback_aa_my_drive_is_the_brain` (use existing infra always)
  - `feedback_apply_macro_micro_gate_before_recommendation_list` (Polymarket is macro)
  - `feedback_prove_real_not_simulated` (verification receipts, not assurances)
  - `feedback_brain_intact_local_first` (every write local-first w/ fallback)
  - `feedback_fail_loud_with_it_auto_repair` (failures fire IT triage)
