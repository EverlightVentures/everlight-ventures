"""Prompt templates for Claude AI advisor.

All prompts are framed as "analyzing bot telemetry data" to avoid
safety refusals.  Each builds a rich context with actual OHLCV data,
indicator values, and trade history so Claude can truly see the chart.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


# -- Data formatting helpers --

def _fmt_candles(df: pd.DataFrame, n: int = 20) -> str:
    """Format last N candles as compact OHLCV table."""
    if df is None or df.empty:
        return "(no candle data)"
    tail = df.tail(n)
    lines = ["Time            Open     High     Low      Close    Vol"]
    for idx, row in tail.iterrows():
        ts = str(idx)[-16:] if hasattr(idx, 'isoformat') else str(idx)[-16:]
        lines.append(
            f"{ts}  {row.get('open',0):.5f}  {row.get('high',0):.5f}  "
            f"{row.get('low',0):.5f}  {row.get('close',0):.5f}  {int(row.get('volume',0)):>8}"
        )
    return "\n".join(lines)


def _fmt_indicators(regime_v4: dict, expansion: dict, price: float) -> str:
    """Format current indicator values from regime and expansion data."""
    m = expansion.get("metrics") or {}
    lines = [
        f"Current price: {price:.5f}",
        f"RSI(14): {m.get('rsi', '?')}",
        f"ADX(14): {regime_v4.get('adx_15m', '?')}",
        f"ATR(14): {m.get('atr', '?')}",
        f"ATR ratio (recent/avg): {m.get('tr_ratio', '?')}",
        f"Vol ratio: {m.get('vol_ratio', '?')}",
        f"VWAP: {regime_v4.get('vwap_price', '?')} (price {'above' if regime_v4.get('vwap_side') == 'above' else 'below'})",
        f"ATR expanding: {regime_v4.get('atr_expanding', '?')}",
        f"BB expanding: {regime_v4.get('bb_expanding', '?')}",
        f"ATR shock: {regime_v4.get('atr_shock', '?')}",
        f"Extreme candle: {regime_v4.get('extreme_candle', '?')}",
        f"RSI divergence: {regime_v4.get('rsi_divergence', 'none')}",
        f"OBV divergence: {regime_v4.get('obv_divergence', 'none')}",
        f"Vol phase: {expansion.get('phase', '?')} (conf: {expansion.get('confidence', '?')})",
        f"Vol direction: {expansion.get('direction', '?')}",
    ]
    return "\n".join(lines)


def _fmt_math_lens(candles: pd.DataFrame | None, n: int = 20) -> str:
    """Summarize calculus/trigonometry/algebra signals from recent closes."""
    import math

    if candles is None or candles.empty or "close" not in candles.columns:
        return "(no math lens data)"

    closes = pd.to_numeric(candles["close"], errors="coerce").dropna().tail(max(8, n))
    if len(closes) < 8:
        return "(insufficient candles for math lens)"

    # Algebra: linear trend fit slope over the recent window.
    x = pd.Series(range(len(closes)), dtype="float64")
    y = closes.reset_index(drop=True).astype("float64")
    xm = float(x.mean())
    ym = float(y.mean())
    var_x = float(((x - xm) ** 2).sum())
    cov_xy = float(((x - xm) * (y - ym)).sum())
    slope = (cov_xy / var_x) if var_x > 0 else 0.0
    y_hat = ym + slope * (x - xm)
    ss_res = float(((y - y_hat) ** 2).sum())
    ss_tot = float(((y - ym) ** 2).sum())
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Calculus: first and second discrete derivatives of price.
    velocity = float(y.iloc[-1] - y.iloc[-2])
    acceleration = float((y.iloc[-1] - y.iloc[-2]) - (y.iloc[-2] - y.iloc[-3]))
    integral_move = float((y.diff().fillna(0)).sum())

    # Trigonometry: slope angle + normalized phase position in recent range.
    slope_angle_deg = math.degrees(math.atan(slope))
    p_min = float(y.min())
    p_max = float(y.max())
    rng = max(p_max - p_min, 1e-9)
    phase_deg = ((float(y.iloc[-1]) - p_min) / rng) * 360.0

    lines = [
        "Algebra:",
        f"- Trend slope (close/bar): {slope:+.6f}",
        f"- Trend fit quality (R^2): {r2:.3f}",
        "Calculus:",
        f"- Velocity dP: {velocity:+.6f}",
        f"- Acceleration d2P: {acceleration:+.6f}",
        f"- Integral move sum(dP): {integral_move:+.6f}",
        "Trigonometry:",
        f"- Slope angle: {slope_angle_deg:+.2f} deg",
        f"- Range phase: {phase_deg:.1f} deg (0=range low, 360=range high)",
    ]
    return "\n".join(lines)


def _fmt_trades(trades_path: str | Path, n: int = 8) -> str:
    """Format last N completed trades from trades.csv."""
    try:
        p = Path(trades_path)
        if not p.exists():
            return "(no trade history)"
        df = pd.read_csv(p)
        # Filter to completed trades (have exit_price)
        if "exit_price" in df.columns:
            df = df[df["exit_price"].notna()].tail(n)
        else:
            df = df.tail(n)
        if df.empty:
            return "(no completed trades)"
        lines = ["# | Side  | Entry    | Exit     | PnL $  | Duration | Type         | Exit Reason"]
        for i, (_, row) in enumerate(df.iterrows(), 1):
            side = str(row.get("side", "?")).upper()[:5]
            entry_px = f"{float(row.get('entry_price', 0)):.5f}"
            exit_px = f"{float(row.get('exit_price', 0)):.5f}" if pd.notna(row.get("exit_price")) else "open"
            pnl = f"{float(row.get('pnl_usd', 0)):+.2f}" if pd.notna(row.get("pnl_usd")) else "?"
            # Duration
            dur = "?"
            try:
                et = pd.to_datetime(row.get("entry_time"))
                xt = pd.to_datetime(row.get("exit_time"))
                if pd.notna(et) and pd.notna(xt):
                    dur = f"{int((xt - et).total_seconds() // 60)}m"
            except Exception:
                pass
            etype = str(row.get("entry_type", "?"))[:14]
            ereason = str(row.get("exit_reason", "?"))[:16]
            lines.append(f"{i:>2} | {side:<5} | {entry_px} | {exit_px} | {pnl:>7} | {dur:>8} | {etype:<14} | {ereason}")
        return "\n".join(lines)
    except Exception:
        return "(error reading trade history)"


def _fmt_feedback(feedback: list[dict]) -> str:
    """Format AI decision feedback for self-learning.

    Shows Claude its own past decisions and whether they won or lost,
    so it can identify patterns in its own reasoning.
    """
    if not feedback:
        return "(no feedback yet -- this is your first session)"
    lines = ["#  | Decision    | Conf | PnL $  | Duration | Result    | Your Reasoning (excerpt)"]
    wins = 0
    losses = 0
    flat_missed = 0
    flat_correct = 0
    for i, fb in enumerate(feedback, 1):
        action = fb.get("action", "?")
        conf = f"{float(fb.get('confidence', 0)):.0%}"
        if action == "FLAT":
            missed = fb.get("missed_move", False)
            move = fb.get("move_pct", 0)
            result = f"MISSED {move:+.2f}%" if missed else "CORRECT"
            if missed:
                flat_missed += 1
            else:
                flat_correct += 1
            reason = fb.get("reasoning", "")[:60]
            lines.append(f"{i:>2} | {'FLAT':<11} | {conf:>4} | {'n/a':>6} | {'n/a':>8} | {result:<9} | {reason}")
        else:
            pnl = fb.get("pnl_usd")
            pnl_str = f"{float(pnl):+.2f}" if pnl is not None else "?"
            dur = fb.get("duration_min")
            dur_str = f"{int(dur)}m" if dur is not None else "?"
            won = fb.get("won", False)
            if won:
                wins += 1
            else:
                losses += 1
            result = "WIN" if won else "LOSS"
            reason = fb.get("reasoning", "")[:60]
            direction = fb.get("direction", "?")
            lines.append(f"{i:>2} | {action:<11} | {conf:>4} | {pnl_str:>6} | {dur_str:>8} | {result:<9} | {reason}")

    # Summary stats
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    lines.append("")
    lines.append(f"Your stats: {wins}W / {losses}L ({win_rate:.0f}% win rate)")
    if flat_missed > 0:
        lines.append(f"FLAT calls: {flat_correct} correct, {flat_missed} missed moves (you should have traded)")
    if losses > wins and total_trades >= 3:
        lines.append("WARNING: You're losing more than winning. Try different patterns or tighter stops.")
    if flat_missed > flat_correct and (flat_missed + flat_correct) >= 3:
        lines.append("WARNING: You're saying FLAT too often and missing moves. Be more aggressive.")
    total_flats = flat_correct + flat_missed
    if total_flats >= 5 and total_trades == 0:
        lines.append("CRITICAL: You have said FLAT 5+ times with ZERO trades. You are NOT trading. Enter on the next decent setup.")
    elif total_flats >= 3 and total_trades <= 1:
        lines.append("NOTE: Many FLAT calls, very few trades. Lower your bar slightly - a B+ setup is worth taking.")

    return "\n".join(lines)


def _fmt_lane_performance(lane_perf_path: str | Path | None = None) -> str:
    """Format per-lane performance stats for Claude's master directive.

    Shows Claude which lanes are winning/losing so it can adjust thresholds.
    """
    import json as _json
    if not lane_perf_path:
        return "(no lane performance data)"
    try:
        p = Path(lane_perf_path)
        if not p.exists():
            return "(lane performance file not found)"
        data = _json.loads(p.read_text())
        lanes = data.get("lanes", {})
        if not lanes:
            return "(no lane stats yet)"
        lines = ["Lane | Win/Loss | Win Rate | Avg PnL | Status"]
        for lane_id in sorted(lanes.keys()):
            s = lanes[lane_id]
            w = s.get("wins", 0)
            l = s.get("losses", 0)
            wr = f"{s.get('win_rate', 0):.0%}"
            avg = f"${s.get('avg_pnl_usd', 0):+.2f}"
            override = s.get("override", "active")
            lines.append(f"  {lane_id}   | {w}W/{l}L    | {wr:>6}   | {avg:>7} | {override}")
        return "\n".join(lines)
    except Exception:
        return "(error reading lane performance)"


def _fmt_kv(d: dict) -> str:
    """Format dict as readable key-value lines."""
    lines = []
    for k, v in d.items():
        if isinstance(v, float):
            lines.append(f"  {k}: {v:.4f}")
        elif isinstance(v, list):
            lines.append(f"  {k}: {', '.join(str(x) for x in v[:10])}")
        elif isinstance(v, dict):
            inner = ", ".join(f"{ik}={iv}" for ik, iv in list(v.items())[:8])
            lines.append(f"  {k}: {{{inner}}}")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def _query_blinko_context(price: float = 0.0) -> str | None:
    """Query Blinko knowledge base for relevant trade memory context.

    Returns a brief summary of past trade patterns at similar price levels,
    or None if Blinko is unavailable.
    """
    import json as _json
    import os
    from urllib.request import Request, urlopen

    blinko_url = os.environ.get("BLINKO_URL", "")
    if not blinko_url:
        # Try loading from .env
        _env_file = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
        if _env_file.exists():
            for line in _env_file.read_text().splitlines():
                if line.startswith("BLINKO_URL="):
                    blinko_url = line.split("=", 1)[1].strip()
    if not blinko_url:
        return None

    query = f"XLM trade patterns near ${price:.4f}"
    payload = _json.dumps({"searchText": query, "size": 3}).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    # Try both known Blinko note-search endpoints for compatibility.
    for endpoint in ("/api/v1/note/search", "/api/v1/note/list"):
        try:
            req = Request(f"{blinko_url}{endpoint}", data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8")
            data = _json.loads(raw) if raw else {}
            notes = data.get("items") or data.get("notes") or []
            if notes:
                summaries = []
                for note in notes[:3]:
                    content = str(note.get("content", ""))[:200]
                    if content:
                        summaries.append(f"- {content}")
                if summaries:
                    return "\n".join(summaries)
        except Exception:
            continue
    return None


# -- Prompt builders --

def entry_prompt(
    signal: dict,
    candles_15m: pd.DataFrame | None = None,
    candles_1h: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion: dict | None = None,
    trades_path: str | Path | None = None,
    price: float = 0.0,
) -> str:
    """Build prompt for pre-entry evaluation with full chart context."""
    regime_v4 = regime_v4 or {}
    expansion = expansion or {}

    sections = [
        "You are a quantitative analyst reviewing telemetry from an automated trading system.",
        "The system detected an entry signal. You have access to the actual price data,",
        "technical indicators, and recent trade history. Analyze the chart context and",
        "assess whether this entry has edge or is repeating a losing pattern.",
        "",
        "Key things to evaluate:",
        "- Is the setup aligned with the current regime (trend/mean-reversion/compression)?",
        "- Are indicators confirming the direction (RSI, MACD divergence, VWAP position)?",
        "- Does the recent trade history show this same setup losing repeatedly?",
        "- Is the entry chasing (price far from VWAP/EMA) or well-positioned?",
        "- After consecutive losses, is this a revenge re-entry into the same failing pattern?",
        "",
        "Respond ONLY with valid JSON (no markdown, no commentary):",
        '{"verdict": "proceed" or "caution" or "skip",',
        ' "confidence": 0.0 to 1.0,',
        ' "score_adjustment": -10 to +10 (integer),',
        ' "reasoning": "1-2 sentences explaining your analysis",',
        ' "warnings": ["specific concerns if any"]}',
        "",
        "=== SIGNAL ===",
        _fmt_kv(signal),
    ]

    if candles_15m is not None and not candles_15m.empty:
        sections.extend([
            "",
            "=== 15-MINUTE CANDLES (last 20) ===",
            _fmt_candles(candles_15m, 20),
        ])

    if candles_1h is not None and not candles_1h.empty:
        sections.extend([
            "",
            "=== 1-HOUR CANDLES (last 12) ===",
            _fmt_candles(candles_1h, 12),
        ])

    if regime_v4 or expansion:
        sections.extend([
            "",
            "=== INDICATORS ===",
            _fmt_indicators(regime_v4, expansion, price),
        ])
    if candles_15m is not None and not candles_15m.empty:
        sections.extend([
            "",
            "=== MATH LENS (calculus/trigonometry/algebra) ===",
            _fmt_math_lens(candles_15m, 20),
        ])

    if trades_path:
        sections.extend([
            "",
            "=== RECENT TRADE HISTORY ===",
            _fmt_trades(trades_path, 8),
        ])

    return "\n".join(sections)


def exit_prompt(
    position: dict,
    candles_15m: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion: dict | None = None,
    price: float = 0.0,
) -> str:
    """Build prompt for exit evaluation with live chart context."""
    regime_v4 = regime_v4 or {}
    expansion = expansion or {}

    sections = [
        "You are a quantitative analyst reviewing an open position in an automated trading system.",
        "Assess whether the position should be held, have stops tightened, or be exited immediately.",
        "",
        "Key things to evaluate:",
        "- Is the trade giving back too much profit from its peak? (check giveback_usd vs max_unrealized)",
        "- Has the regime shifted against the trade direction since entry?",
        "- Are indicators deteriorating (RSI reversing, MACD crossing against)?",
        "- How many bars has the trade been open vs typical winning duration?",
        "- Is the opposite direction scoring higher than the current direction?",
        "",
        "Respond ONLY with valid JSON (no markdown, no commentary):",
        '{"urgency": "hold" or "tighten" or "exit_now",',
        ' "hold_confidence": 0.0 to 1.0,',
        ' "reasoning": "1-2 sentences explaining your analysis"}',
        "",
        "=== POSITION ===",
        _fmt_kv(position),
    ]

    if candles_15m is not None and not candles_15m.empty:
        sections.extend([
            "",
            "=== 15-MINUTE CANDLES (last 15) ===",
            _fmt_candles(candles_15m, 15),
        ])

    if regime_v4 or expansion:
        sections.extend([
            "",
            "=== INDICATORS ===",
            _fmt_indicators(regime_v4, expansion, price),
        ])
    if candles_15m is not None and not candles_15m.empty:
        sections.extend([
            "",
            "=== MATH LENS (calculus/trigonometry/algebra) ===",
            _fmt_math_lens(candles_15m, 15),
        ])

    return "\n".join(sections)


def regime_prompt(
    regime_data: dict,
    candles_1h: pd.DataFrame | None = None,
) -> str:
    """Build prompt for regime transition evaluation with chart context."""
    sections = [
        "You are a quantitative analyst reviewing a regime transition in an automated trading system.",
        "The system's volatility state machine detected a phase change. Assess the reliability",
        "of this transition and recommend how the system should adapt its trading bias.",
        "",
        "Respond ONLY with valid JSON (no markdown, no commentary):",
        '{"regime_confidence": 0.0 to 1.0,',
        ' "trading_bias": "aggressive" or "neutral" or "defensive",',
        ' "reasoning": "1-2 sentences explaining your analysis"}',
        "",
        "=== REGIME TRANSITION ===",
        _fmt_kv(regime_data),
    ]

    if candles_1h is not None and not candles_1h.empty:
        sections.extend([
            "",
            "=== 1-HOUR CANDLES (last 12) ===",
            _fmt_candles(candles_1h, 12),
        ])

    return "\n".join(sections)


# -- Master Directive (Executive Mode) --

def master_directive_prompt(
    status: dict,
    candles_15m: pd.DataFrame | None = None,
    candles_1h: pd.DataFrame | None = None,
    regime_v4: dict | None = None,
    expansion: dict | None = None,
    trades_path: str | Path | None = None,
    price: float = 0.0,
    engine_recommendation: dict | None = None,
    feedback: list[dict] | None = None,
    mtf_levels: str | None = None,
    macro_news: str | None = None,
    peer_intel: dict | None = None,
    lane_perf_path: str | Path | None = None,
) -> str:
    """Build the master directive prompt -- Claude makes the executive call.

    This is the ONE prompt per cycle that asks Claude to decide what to do:
    enter, exit, hold, or stay flat.
    """
    regime_v4 = regime_v4 or {}
    expansion = expansion or {}
    engine_recommendation = engine_recommendation or {}

    # Dynamic balance from status (never hardcode)
    _equity = status.get("equity_start_usd") or status.get("equity_usd") or 0
    _spot = sum((status.get("spot_balances") or {}).values()) if isinstance(status.get("spot_balances"), dict) else 0
    _total_bal = _equity + _spot
    _consecutive_losses = status.get("consecutive_losses", 0)
    _pnl_today = status.get("pnl_today_usd", 0)
    _trades_today = status.get("trades_today", 0)

    sections = [
        "You are the executive decision engine for an automated XLM futures trading system.",
        "You have full authority to decide: enter a trade, exit a trade, hold, or stay flat.",
        "You are analyzing live market data from the XLM-USD perpetual futures contract.",
        "",
        "GOAL: $25-$100 profit per day. Achievable with 2-4 good trades at size 1-2.",
        "",
        f"ACCOUNT: ${_total_bal:.0f} total (${_equity:.0f} derivatives + ${_spot:.0f} spot).",
        f"Today: {_trades_today} trades, ${_pnl_today:+.2f} PnL, {_consecutive_losses} consecutive losses.",
        "",
        "YOUR TEAM (PEER ADVISORS):",
        "- Gemini (Risk/Math): risk limits and math. Listen on sizing.",
        "- Perplexity (Intel): macro news/catalysts. If risk_off, be careful.",
        "- Codex (Data): data integrity. If data is stale, HOLD.",
        "",
        "CORE RULES:",
        "- ONE decision per cycle. Bot executes your call immediately.",
        "- For entries: specify direction, stop_loss_price, AND size (1 or 2 contracts).",
        "- For exits: say EXIT. Bot closes at market.",
        "- Max position: 2 contracts. Size 1 = default. Size 2 = high conviction ONLY.",
        "",
        "POSITION SIZING (you have 2 sizes, use them wisely):",
        "",
        "  SIZE 1 (Default, use 80% of the time):",
        "    When: Any decent setup. First trade of session. After a loss. Unclear direction.",
        "    Risk: ~$5 max loss per trade. Target: $8-$25 profit.",
        "    This is your bread and butter. Consistent size-1 winners compound fast.",
        "",
        "  SIZE 2 (Conviction, use sparingly, max 1-2 per day):",
        "    When: MONSTER tier, 75%+ confidence, MTF alignment, volume confirming,",
        "    key S/R rejection with clear structure. Everything lines up perfectly.",
        "    Risk: ~$10 max loss. Target: $15-$50+ profit.",
        "    DO NOT use after a loss. EARN it with a size-1 win first.",
        "",
        "DAILY PROFIT MATH (how to hit $25-$100/day):",
        "- At size 1: avg winner = $12-$20, avg loser = $5-$8.",
        "- 3 wins + 1 loss at size 1 = ~$30-$50 net. That is a great day.",
        "- 2 wins at size 2 + 1 loss at size 1 = ~$30-$90 net. Monster day.",
        "- You do NOT need home runs. You need consistency.",
        "- Fees: ~$1.50 round trip. Need $3+ gross to be worth it.",
        "",
        "YOUR JOB IS TO TRADE PROFITABLY, NOT TO AVOID TRADING.",
        "Sitting FLAT all day = $0 earned. The bot exists to make money.",
        "Target: 2-4 quality trades per day. NOT 0. NOT 14.",
        "",
        "ENTRY TRIGGERS (do NOT say FLAT if these are met):",
        "- Engine score >= 70 AND ADX > 25: ENTER with trend, size 1.",
        "- MONSTER tier (score >= 80) with 2+ confluence: ENTER, size 1-2.",
        "- Key S/R level with clear rejection candle + volume: ENTER the rejection.",
        "- Strong trend (ADX > 40) with pullback to EMA/VWAP: ENTER the pullback.",
        "- Expansion phase (ATR shock, volume surge): your best edge. ENTER.",
        "- BTC + ETH confirming direction: adds conviction. ENTER.",
        "- If engine says MONSTER and you say FLAT, you need a STRONG reason.",
        "- Lane V (Liquidity Sweep): cluster swept + wick >35% + reclaim + fib = ENTER reversal.",
        "- Magnet continuation: strong cluster ahead + momentum aligned = ENTER toward cluster.",
        "",
        "STAY FLAT ONLY WHEN:",
        "- Compression (ADX < 20) with no clear direction or structure.",
        "- Within 15 min of margin cutoff (12:45 PM PT).",
        "- 3+ consecutive losses today (take 30 min break, then re-engage).",
        "- RSI extreme (>85 or <15) with zero volume confirmation.",
        "- Equal liquidation clusters on both sides with balanced magnet = chop zone.",
        "- Cluster exists but no sweep yet and no momentum = wait for sweep first.",
        "",
        "RISK RULES:",
        "- Stop loss at structural level (swing high/low), 0.3-1% from entry.",
        "- Optimal hold: 15-90 minutes. That is the winning time range.",
        "- After 1 loss: size 1, 10 min cooldown. Then trade again.",
        "- After 2 losses: size 1, 20 min cooldown. Re-evaluate direction.",
        "- Never re-enter same direction within 5 min of being stopped out.",
        "- Max 6 trades/day. But 0 trades is ALSO a failure.",
        "",
        "DIRECTION:",
        "- Follow the trend (ADX + BTC/ETH correlation).",
        "- Uptrend: longs on pullbacks. Downtrend: shorts on bounces.",
        "- Neutral: whichever direction has better structure.",
        "",
        "SELF-CORRECTION (study your scorecard below):",
        "- Too many FLAT calls missing moves? Lower your bar, trade B+ setups.",
        "- Entries keep losing? Tighten stops, wait for better structure. Do NOT stop trading.",
        "- Goal: 45%+ win rate with 2:1+ R:R = profitable every day.",
        "",
        "Respond ONLY with valid JSON (no markdown, no commentary):",
        '{',
        '  "action": "ENTER_LONG" or "ENTER_SHORT" or "EXIT" or "HOLD" or "FLAT",',
        '  "confidence": 0.0 to 1.0,',
        '  "size": 1 or 2 (REQUIRED for ENTER_LONG/ENTER_SHORT, omit otherwise),',
        '  "stop_loss_price": number (required for ENTER_LONG/ENTER_SHORT, omit otherwise),',
        '  "take_profit_price": number (optional, for ENTER_LONG/ENTER_SHORT),',
        '  "reasoning": "1-2 sentences: your decision + why this size",',
        '  "market_read": "1 sentence: what the chart is telling you right now",',
        '  "lane_adjustments": {"<lane_letter>": {"action": "disable"|"raise_threshold"|"lower_threshold"|"ok", "reason": "..."}} (optional)',
        '}',
    ]

    # Current account/position status
    sections.extend([
        "",
        "=== ACCOUNT STATUS ===",
        _fmt_kv(status),
    ])

    # Contract Context (Specific to the traded instrument)
    if status.get("contract_context"):
        sections.extend([
            "",
            "=== CONTRACT SPECIFICS (20DEC30 / XLM-PERP) ===",
            _fmt_kv(status.get("contract_context")),
        ])

    # Strategy engine's recommendation (Claude can agree or override)
    if engine_recommendation:
        sections.extend([
            "",
            "=== STRATEGY ENGINE RECOMMENDATION ===",
            "(The bot's built-in scoring engine suggests this. You can agree or override.)",
            _fmt_kv(engine_recommendation),
        ])

    if candles_15m is not None and not candles_15m.empty:
        sections.extend([
            "",
            "=== 15-MINUTE CANDLES (last 25) ===",
            _fmt_candles(candles_15m, 25),
        ])

    if candles_1h is not None and not candles_1h.empty:
        sections.extend([
            "",
            "=== 1-HOUR CANDLES (last 16) ===",
            _fmt_candles(candles_1h, 16),
        ])

    if mtf_levels:
        sections.extend([
            "",
            "=== MULTI-TIMEFRAME S/R & FIB LEVELS (Monthly to 1min) ===",
            "Use these as confluence zones. When 3+ timeframes align at a level = HIGH PROBABILITY zone.",
            mtf_levels,
        ])

    if regime_v4 or expansion:
        sections.extend([
            "",
            "=== TECHNICAL INDICATORS ===",
            _fmt_indicators(regime_v4, expansion, price),
        ])
    if candles_15m is not None and not candles_15m.empty:
        sections.extend([
            "",
            "=== MATH LENS (calculus/trigonometry/algebra) ===",
            _fmt_math_lens(candles_15m, 25),
        ])

    if trades_path:
        sections.extend([
            "",
            "=== RECENT TRADE HISTORY (your past decisions) ===",
            _fmt_trades(trades_path, 10),
        ])

    # Self-learning feedback loop
    if feedback:
        sections.extend([
            "",
            "=== YOUR DECISION SCORECARD (learn from these) ===",
            "These are YOUR past calls and their actual outcomes.",
            "Study your wins, losses, and missed moves. Adapt your strategy.",
            _fmt_feedback(feedback),
        ])

    # Lane performance data (self-learning feedback)
    if lane_perf_path:
        sections.extend([
            "",
            "=== LANE PERFORMANCE (adapt based on these stats) ===",
            "Each lane is a different entry strategy. Disable losing lanes, boost winning ones.",
            "You may return lane_adjustments in your JSON to tune them.",
            _fmt_lane_performance(lane_perf_path),
        ])

    # Macro news from Perplexity (BTC, S&P 500, NASDAQ, Fed, XLM-specific)
    if macro_news:
        sections.extend([
            "",
            "=== LIVE MACRO NEWS (from Perplexity, refreshed every 15 min) ===",
            "Use this for macro context. Crypto follows BTC; BTC follows risk-on/risk-off sentiment.",
            "If Fed is hawkish or S&P dumping -> risk-off -> XLM likely drops -> favor shorts.",
            "If BTC pumping or risk-on -> XLM follows -> favor longs.",
            "Weight this as 20% of your decision. Chart data is 80%.",
            macro_news,
        ])

    # Market Pulse: composite health score fusing sentiment + news + live tick
    _mkt_health = status.get("market_health_score")
    _mkt_regime = status.get("market_regime")
    if _mkt_health is not None:
        sections.extend([
            "",
            f"=== MARKET PULSE: {_mkt_health}/100 ({_mkt_regime or '?'}) ===",
            "Composite score: 0-25=DANGER (block most entries), 25-40=RISK_OFF (reduce size),",
            "40-60=NEUTRAL (normal), 60+=RISK_ON (favorable). Factor into sizing and conviction.",
            f"Price source: {status.get('price_source', 'unknown')}",
            f"Live tick age: {status.get('live_tick_age_sec', '?')}s" + (
                f" (live price: ${status.get('live_price', 0):.6f})" if status.get("live_price") else ""
            ),
        ])

    # Peer Intel (Gemini/Codex)
    if peer_intel:
        sections.extend([
            "",
            "=== PEER ADVISOR REPORTS (CONSULT THESE) ===",
            _fmt_kv(peer_intel),
        ])

    # Liquidation intelligence (cluster analysis, magnet bias, sweep detection)
    _liq_intel = status.get("liquidation_intelligence")
    if _liq_intel and isinstance(_liq_intel, str):
        sections.extend([
            "",
            "=== LIQUIDATION INTELLIGENCE (heatmap proxy) ===",
            "Liquidation clusters act as price magnets. Trade toward the cluster,",
            "then reverse on sweep + wick + reclaim. If no rejection, continue to next pool.",
            _liq_intel,
        ])

    # Blinko trade memory context (if available)
    try:
        _blinko_ctx = _query_blinko_context(price)
        if _blinko_ctx:
            sections.extend([
                "",
                "=== TRADE MEMORY (from Blinko knowledge base) ===",
                "Past trade patterns and lessons at similar price levels:",
                _blinko_ctx,
            ])
    except Exception:
        pass

    # Daily brief: last 3 days performance context for posture calibration
    try:
        import json as _json
        _brief_path = Path(__file__).parent.parent / "data" / "daily_brief.json"
        if _brief_path.exists():
            _b = _json.loads(_brief_path.read_text())
            _posture = _b.get("suggested_posture", "normal")
            _trend = _b.get("equity_trend", "stable")
            _3d_pnl = _b.get("total_3day_pnl_usd", 0)
            _days_str = "; ".join(
                f"{d['date']}: {d['trades']} trades, ${d['pnl_usd']:+.2f}, WR {d['win_rate_pct']}%"
                for d in (_b.get("last_3_days") or [])
            )
            _posture_inst = (
                "Size down, wait for A+ setups only."
                if _posture == "conservative"
                else (
                    "Normal sizing, follow your rules."
                    if _posture == "normal"
                    else "Healthy equity, push on MONSTER setups."
                )
            )
            sections.extend([
                "",
                "=== SESSION CONTEXT (last 3 days) ===",
                f"3-day PnL: ${_3d_pnl:+.2f} | equity trend: {_trend} | suggested posture: {_posture.upper()}",
                _days_str,
                f"POSTURE INSTRUCTION: {_posture.upper()} mode. {_posture_inst}",
            ])
    except Exception:
        pass

    return "\n".join(sections)
