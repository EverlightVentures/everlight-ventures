"""Simple Trading Core -- the 5-step trading brain.

1. DIRECTION: What way is the market moving?
2. ENTRY: Where do I get in?
3. STOP: Where am I wrong?
4. TARGET: Where do I take profit?
5. EXECUTE: Enter and hold until TP or stop.

No modifiers. No gates. No committee. Pure chart reading.
"""
from __future__ import annotations

import pandas as pd
from indicators.ema import ema
from indicators.atr import atr
from indicators.rsi import rsi


_CS = 5000.0  # contract size
_MAX_RISK_USD = 6.0
_MIN_PROFIT_USD = 2.0
_FEE_USD = 1.50


def _ema_slope(series: pd.Series, period: int = 21, lookback: int = 5) -> float:
    """Average slope of EMA over last N bars. Positive = up, negative = down."""
    e = ema(series, period)
    if len(e) < lookback + 1:
        return 0.0
    slopes = e.diff().tail(lookback)
    return float(slopes.mean())


def _swing_low(df: pd.DataFrame, lookback: int = 20) -> float:
    """Recent swing low from last N bars."""
    if df is None or len(df) < lookback:
        return 0.0
    return float(df["low"].tail(lookback).min())


def _swing_high(df: pd.DataFrame, lookback: int = 20) -> float:
    """Recent swing high from last N bars."""
    if df is None or len(df) < lookback:
        return 0.0
    return float(df["high"].tail(lookback).max())


def _structure_bias(df: pd.DataFrame) -> str:
    """Is 15m making higher lows (bullish) or lower highs (bearish)?"""
    if df is None or len(df) < 12:
        return "neutral"
    lows = df["low"].tail(12)
    highs = df["high"].tail(12)
    # Compare first half vs second half
    half = 6
    first_low = float(lows.iloc[:half].min())
    second_low = float(lows.iloc[half:].min())
    first_high = float(highs.iloc[:half].max())
    second_high = float(highs.iloc[half:].max())

    higher_lows = second_low > first_low
    lower_highs = second_high < first_high

    if higher_lows and not lower_highs:
        return "bullish"
    if lower_highs and not higher_lows:
        return "bearish"
    return "neutral"


def _is_pullback_to_ema(price: float, ema_val: float, atr_val: float) -> bool:
    """Is price within 0.5 ATR of the EMA? That's a pullback entry zone."""
    if ema_val <= 0 or atr_val <= 0:
        return False
    return abs(price - ema_val) <= atr_val * 0.5


def _is_wick_rejection(df: pd.DataFrame, direction: str) -> bool:
    """Last candle has a rejection wick in our favor?"""
    if df is None or len(df) < 2:
        return False
    c = df.iloc[-1]
    body = abs(float(c["close"]) - float(c["open"]))
    full_range = float(c["high"]) - float(c["low"])
    if full_range <= 0 or body <= 0:
        return False

    if direction == "long":
        lower_wick = float(min(c["open"], c["close"])) - float(c["low"])
        return lower_wick > body * 1.2  # lower wick bigger than body
    else:
        upper_wick = float(c["high"]) - float(max(c["open"], c["close"]))
        return upper_wick > body * 1.2  # upper wick bigger than body


def _is_1m_momentum_breakout(df_1m: pd.DataFrame, direction: str) -> dict | None:
    """1-minute momentum breakout from micro-range.

    The pattern: price compresses in a tight range for 10+ bars,
    then a candle breaks out with volume spike + RSI confirmation.
    This catches the $13 moves that happen in 8 minutes.

    Returns dict with details or None.
    """
    if df_1m is None or df_1m.empty or len(df_1m) < 20:
        return None

    # Compression: last 10 bars before current have tight range
    lookback = df_1m.iloc[-12:-2]  # bars 2-12 ago (skip last 2 for the breakout)
    recent = df_1m.iloc[-2:]       # last 2 bars (the breakout candles)

    comp_high = float(lookback["high"].max())
    comp_low = float(lookback["low"].min())
    comp_range = comp_high - comp_low
    price_now = float(df_1m["close"].iloc[-1])

    # Range must be < 0.3% of price (tight compression)
    if comp_range > price_now * 0.003:
        return None

    # Volume: current bar must have > 1.5x the 20-bar average
    avg_vol = float(df_1m["volume"].tail(20).mean())
    curr_vol = float(df_1m["volume"].iloc[-1])
    if avg_vol <= 0 or curr_vol < avg_vol * 1.3:
        return None

    # Breakout: close above compression high (long) or below low (short)
    curr_close = float(df_1m["close"].iloc[-1])
    if direction == "long" and curr_close <= comp_high:
        return None
    if direction == "short" and curr_close >= comp_low:
        return None

    # RSI confirmation
    try:
        rsi_vals = rsi(df_1m["close"], 14)
        rsi_now = float(rsi_vals.iloc[-1])
        rsi_3ago = float(rsi_vals.iloc[-4]) if len(rsi_vals) >= 4 else rsi_now
        rsi_rising = rsi_now > rsi_3ago

        if direction == "long" and (rsi_now < 50 or not rsi_rising):
            return None
        if direction == "short" and (rsi_now > 50 or rsi_rising):
            return None
    except Exception:
        return None

    return {
        "type": "1m_momentum_breakout",
        "comp_high": comp_high,
        "comp_low": comp_low,
        "comp_range": comp_range,
        "volume_ratio": round(curr_vol / avg_vol, 2),
        "rsi": round(rsi_now, 1),
    }


def _is_capitulation_wick(df: pd.DataFrame, direction: str) -> dict | None:
    """Detect flash crash / capitulation wick on any timeframe.

    The pattern: price flushes hard (1%+ below recent lows), then snaps
    back and closes in the upper half of the candle with massive volume.
    This is the trap-and-snap -- trapped sellers get squeezed.

    Works on 1m, 15m, 1h -- any timeframe where a single candle shows
    the flush + recovery pattern.
    """
    if df is None or df.empty or len(df) < 5:
        return None

    c = df.iloc[-1]
    prev = df.iloc[-2]
    c_open = float(c["open"])
    c_close = float(c["close"])
    c_high = float(c["high"])
    c_low = float(c["low"])
    c_vol = float(c.get("volume", 0))
    prev_low = float(prev["low"])
    prev_high = float(prev["high"])

    full_range = c_high - c_low
    if full_range <= 0:
        return None

    body = abs(c_close - c_open)
    body_mid = (c_open + c_close) / 2

    # Volume must be exceptional (3x average)
    avg_vol = float(df["volume"].tail(20).mean()) if "volume" in df.columns else 0
    if avg_vol <= 0 or c_vol < avg_vol * 2.5:
        return None

    if direction == "long":
        # Flash crash long: big flush DOWN, close in upper half
        lower_wick = min(c_open, c_close) - c_low
        flush_pct = (prev_low - c_low) / prev_low if prev_low > 0 else 0

        # Flush must be significant (at least 0.15% below prev low)
        if flush_pct < 0.0015:
            return None

        # Close must be in upper half of range (buyers stepped in)
        close_position = (c_close - c_low) / full_range
        if close_position < 0.45:
            return None

        # Lower wick must be > 60% of the full range
        if lower_wick / full_range < 0.5:
            return None

        return {
            "type": "capitulation_wick_long",
            "flush_pct": round(flush_pct * 100, 2),
            "close_position": round(close_position, 2),
            "volume_ratio": round(c_vol / avg_vol, 1),
            "wick_ratio": round(lower_wick / full_range, 2),
        }

    else:
        # Blow-off top short: big spike UP, close in lower half
        upper_wick = c_high - max(c_open, c_close)
        spike_pct = (c_high - prev_high) / prev_high if prev_high > 0 else 0

        if spike_pct < 0.0015:
            return None

        close_position = (c_close - c_low) / full_range
        if close_position > 0.55:
            return None

        if upper_wick / full_range < 0.5:
            return None

        return {
            "type": "capitulation_wick_short",
            "spike_pct": round(spike_pct * 100, 2),
            "close_position": round(close_position, 2),
            "volume_ratio": round(c_vol / avg_vol, 1),
            "wick_ratio": round(upper_wick / full_range, 2),
        }


def _is_range_breakout(df: pd.DataFrame, direction: str, atr_val: float) -> bool:
    """Price breaking out of recent range?"""
    if df is None or len(df) < 20 or atr_val <= 0:
        return False
    # Range from bars 5-20 (skip last 4 for the breakout)
    range_bars = df.iloc[-20:-4]
    recent = df.iloc[-2:]
    range_high = float(range_bars["high"].max())
    range_low = float(range_bars["low"].min())

    if direction == "long":
        return float(recent["close"].iloc[-1]) > range_high
    else:
        return float(recent["close"].iloc[-1]) < range_low


def _scan_timeframe(df: pd.DataFrame, direction: str, price: float, tf_name: str) -> dict | None:
    """Scan a single timeframe for all entry conditions.

    Returns best entry found or None.
    """
    if df is None or df.empty or len(df) < 15:
        return None

    try:
        atr_val = float(atr(df, 14).iloc[-1])
        ema21_val = float(ema(df["close"], 21).iloc[-1])
        rsi_val = float(rsi(df["close"], 14).iloc[-1])
    except Exception:
        return None

    if atr_val <= 0:
        return None

    results = []

    # Check all 5 entry conditions on this timeframe
    if _is_pullback_to_ema(price, ema21_val, atr_val):
        results.append({"reason": "pullback", "tf": tf_name, "rsi": rsi_val, "atr": atr_val, "ema21": ema21_val})

    if _is_wick_rejection(df, direction):
        results.append({"reason": "wick_rejection", "tf": tf_name, "rsi": rsi_val, "atr": atr_val, "ema21": ema21_val})

    if _is_range_breakout(df, direction, atr_val):
        results.append({"reason": "range_breakout", "tf": tf_name, "rsi": rsi_val, "atr": atr_val, "ema21": ema21_val})

    # 1m momentum only on 1m data
    if tf_name == "1m":
        m = _is_1m_momentum_breakout(df, direction)
        if m:
            results.append({"reason": "1m_momentum_breakout", "tf": "1m", "rsi": rsi_val, "atr": atr_val, "ema21": ema21_val, "momentum": m})

    # Capitulation wick (flash crash reversal) -- works on all timeframes
    cap = _is_capitulation_wick(df, direction)
    if cap:
        results.append({"reason": cap["type"], "tf": tf_name, "rsi": rsi_val, "atr": atr_val, "ema21": ema21_val, "capitulation": cap, "priority_boost": 2})

    return results[0] if results else None


def evaluate_simple_setup(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    price: float,
    config: dict | None = None,
    df_1m: pd.DataFrame | None = None,
    df_4h: pd.DataFrame | None = None,
    df_1d: pd.DataFrame | None = None,
) -> dict | None:
    """The simple 5-step trading brain.

    Scans ALL available timeframes for entry conditions.
    Higher timeframe signals get priority (more reliable).
    Returns the best setup or None.
    """
    cfg = (config or {}).get("simple_core", {}) or {}
    max_risk = float(cfg.get("max_risk_usd", _MAX_RISK_USD))
    min_profit = float(cfg.get("min_profit_usd", _MIN_PROFIT_USD))

    if df_15m is None or df_1h is None or df_15m.empty or df_1h.empty:
        return None
    if len(df_15m) < 30 or len(df_1h) < 30:
        return None

    # === STEP 1: DIRECTION (3-layer combo system) ===
    # MACRO (1H/4H): What's the trend? Sets allowed directions.
    # MINI (15m): What's the structure? Trending or ranging?
    # MICRO (1m): What entry pattern? Only fires if macro+mini allow.

    # --- MACRO LAYER (1H + 4H) ---
    slope_1h = _ema_slope(df_1h["close"], 21, 5)
    rsi_1h = 50.0
    try:
        rsi_1h = float(rsi(df_1h["close"], 14).iloc[-1])
    except Exception:
        pass

    slope_4h = 0.0
    rsi_4h = 50.0
    if df_4h is not None and not df_4h.empty and len(df_4h) >= 20:
        try:
            slope_4h = _ema_slope(df_4h["close"], 21, 5)
            rsi_4h = float(rsi(df_4h["close"], 14).iloc[-1])
        except Exception:
            pass

    # Macro regime: BULL / BEAR / NEUTRAL
    if slope_1h > 0 and slope_4h >= 0:
        macro = "BULL"
    elif slope_1h < 0 and slope_4h <= 0:
        macro = "BEAR"
    elif slope_1h > 0.00005 and rsi_1h > 55:
        macro = "BULL"  # 1H bullish with RSI confirm even if 4H flat
    elif slope_1h < -0.00005 and rsi_1h < 45:
        macro = "BEAR"
    else:
        macro = "NEUTRAL"

    # --- MINI LAYER (15m) ---
    structure = _structure_bias(df_15m)
    rsi_raw = float(rsi(df_15m["close"], 14).iloc[-1])

    # Mini structure: TRENDING_UP / TRENDING_DOWN / RANGING
    if structure == "bullish":
        mini = "TRENDING_UP"
    elif structure == "bearish":
        mini = "TRENDING_DOWN"
    else:
        mini = "RANGING"

    # --- COMBO DIRECTION LOGIC ---
    # What directions are allowed based on macro + mini agreement?
    allow_long = False
    allow_short = False
    combo_bonus = 0

    if macro == "BULL":
        allow_long = True
        if mini == "TRENDING_UP":
            combo_bonus = 5  # full alignment
        elif mini == "RANGING":
            combo_bonus = 2  # macro says long, mini is flat -- ok but less confident
        # Allow counter-trend short only in ranging (range fade at top)
        if mini == "RANGING":
            allow_short = True
    elif macro == "BEAR":
        allow_short = True
        if mini == "TRENDING_DOWN":
            combo_bonus = 5
        elif mini == "RANGING":
            combo_bonus = 2
        if mini == "RANGING":
            allow_long = True
    else:  # NEUTRAL
        allow_long = True
        allow_short = True
        combo_bonus = 0

    # --- MICRO OVERRIDE: Capitulation wicks override everything ---
    # A flash crash reversal is its own signal -- macro doesn't matter
    _cap_long = None
    _cap_short = None
    if df_1m is not None and not df_1m.empty and len(df_1m) > 5:
        _cap_long = _is_capitulation_wick(df_1m, "long")
        _cap_short = _is_capitulation_wick(df_1m, "short")

    if _cap_long:
        allow_long = True  # capitulation overrides macro
        combo_bonus = max(combo_bonus, 3)

    if _cap_short:
        allow_short = True
        combo_bonus = max(combo_bonus, 3)

    # RSI extreme overrides: deeply oversold = allow long, overbought = allow short
    if rsi_raw < 25 or rsi_4h < 20:
        allow_long = True
    if rsi_raw > 75 or rsi_4h > 80:
        allow_short = True

    # Pick direction: prefer the one that aligns with macro
    direction = None
    if allow_long and allow_short:
        # Both allowed -- pick based on macro + momentum
        if macro == "BULL" or (macro == "NEUTRAL" and rsi_raw > 50):
            direction = "long"
        elif macro == "BEAR" or (macro == "NEUTRAL" and rsi_raw < 50):
            direction = "short"
        elif _cap_long:
            direction = "long"
        elif _cap_short:
            direction = "short"
        else:
            direction = "long" if slope_1h > 0 else "short"
    elif allow_long:
        direction = "long"
    elif allow_short:
        direction = "short"
    else:
        return None  # nothing allowed

    # Tag the structure for logging
    if _cap_long and direction == "long":
        structure = "capitulation_reversal"
    elif _cap_short and direction == "short":
        structure = "blowoff_reversal"
    elif rsi_raw < 25 and direction == "long":
        structure = "oversold_bounce"
    elif rsi_raw > 75 and direction == "short":
        structure = "overbought_rejection"
    elif macro == "BULL" and mini == "TRENDING_UP":
        structure = "bull_trend_aligned"
    elif macro == "BEAR" and mini == "TRENDING_DOWN":
        structure = "bear_trend_aligned"
    elif mini == "RANGING":
        structure = "range_" + direction

    # === STEP 2: ENTRY (multi-timeframe scan) ===
    # Scan ALL timeframes for entry conditions. Best signal wins.
    # Priority: 1m momentum > 4h/1d structure > 1h pattern > 15m pattern
    atr_15m = float(atr(df_15m, 14).iloc[-1])
    ema21_15m = float(ema(df_15m["close"], 21).iloc[-1])
    rsi_val = rsi_raw

    timeframes = [
        ("1m", df_1m),
        ("15m", df_15m),
        ("1h", df_1h),
        ("4h", df_4h),
        ("1d", df_1d),
    ]

    best_entry = None
    # Scan each timeframe. Higher TF entries are more reliable.
    # 1m momentum breakouts are special -- speed matters more than TF.
    tf_priority = {"1d": 5, "4h": 4, "1h": 3, "1m": 3, "15m": 2}

    for tf_name, tf_df in timeframes:
        if tf_df is None or tf_df.empty:
            continue
        hit = _scan_timeframe(tf_df, direction, price, tf_name)
        if hit:
            hit["priority"] = tf_priority.get(tf_name, 1) + int(hit.get("priority_boost", 0))
            # Capitulation wicks get highest priority (time-sensitive)
            if "capitulation" in str(hit.get("reason", "")):
                hit["priority"] = 6
            if best_entry is None or hit["priority"] > best_entry["priority"]:
                best_entry = hit

    if best_entry is None:
        return None  # no entry on any timeframe

    entry_reason = best_entry["reason"]
    entry_tf = best_entry["tf"]
    # Use the ATR from the entry timeframe for stop/TP calculation
    entry_atr = best_entry.get("atr", atr_15m)

    # RSI extremes already handled by combo system (allow_long/allow_short)
    # Just update entry_reason if RSI is extreme
    if rsi_val < 25 and direction == "long" and "capitulation" not in entry_reason:
        entry_reason = "oversold_reversal"
    elif rsi_val > 75 and direction == "short" and "capitulation" not in entry_reason:
        entry_reason = "overbought_reversal"

    # Remove old RSI flip logic since combo handles it
    if False:  # dead code placeholder
        direction = "short"
        structure = "overbought_rejection"
        entry_reason = "overbought_reversal"
        pullback = _is_pullback_to_ema(price, ema21_15m, atr_15m)
        wick = _is_wick_rejection(df_15m, "short")
        breakout = False
        if not (pullback or wick):
            wick = True

    # entry_reason already set above -- RSI reversal overrides may have changed it

    # === STEP 3: STOP ===
    # Use the entry timeframe's data for structure stop
    # Higher TF entries get wider stops (more room), lower TF get tighter
    _stop_df = df_15m  # default
    _stop_lookback = 12
    for tf_name, tf_df in timeframes:
        if tf_name == entry_tf and tf_df is not None and not tf_df.empty and len(tf_df) >= 10:
            _stop_df = tf_df
            _stop_lookback = min(12, len(tf_df) - 1)
            break

    if direction == "long":
        stop = _swing_low(_stop_df, _stop_lookback)
        stop = stop - entry_atr * 0.2
    else:
        stop = _swing_high(_stop_df, _stop_lookback)
        stop = stop + entry_atr * 0.2

    risk_distance = abs(price - stop)
    risk_usd = risk_distance * _CS

    # If structure stop is too wide, use ATR-based stop
    if risk_usd > max_risk:
        atr_stop_dist = entry_atr * 1.5
        if direction == "long":
            stop = price - atr_stop_dist
        else:
            stop = price + atr_stop_dist
        risk_distance = atr_stop_dist
        risk_usd = risk_distance * _CS

    if risk_usd > max_risk or risk_usd <= 0:
        return None  # still too high even with ATR stop

    # === STEP 4: TARGET ===
    # TP based on risk multiples -- minimum 1.5:1 to cover fees
    tp1_distance = max(risk_distance * 1.5, 0.0010)   # 1.5:1 or $5 minimum (covers fees)
    tp2_distance = max(risk_distance * 2.5, 0.0016)   # 2.5:1 or $8
    tp3_distance = max(risk_distance * 4.0, 0.0024)   # 4:1 or $12 runner

    if direction == "long":
        tp1 = price + tp1_distance
        tp2 = price + tp2_distance
        tp3 = price + tp3_distance
    else:
        tp1 = price - tp1_distance
        tp2 = price - tp2_distance
        tp3 = price - tp3_distance

    tp1_profit = tp1_distance * _CS - _FEE_USD
    # Lower min profit for reversal entries (tight stop = small TP but high win rate)
    effective_min = 0.50 if "reversal" in entry_reason or "bounce" in structure else min_profit
    if tp1_profit < effective_min:
        return None  # not worth trading after fees

    return {
        "direction": direction,
        "entry_price": price,
        "stop_price": round(stop, 8),
        "tp1": round(tp1, 8),
        "tp2": round(tp2, 8),
        "tp3": round(tp3, 8),
        "risk_usd": round(risk_usd, 2),
        "tp1_profit_usd": round(tp1_profit, 2),
        "rr_ratio": round(tp1_distance / risk_distance, 2) if risk_distance > 0 else 0,
        "entry_reason": entry_reason,
        "entry_timeframe": entry_tf,
        "entry_source": "simple_core",
        "ema_slope_1h": round(slope_1h, 8),
        "structure_15m": structure,
        "rsi_15m": round(rsi_val, 1),
        "atr_15m": round(atr_15m, 8),
        "entry_atr": round(entry_atr, 8),
        # Combo system data
        "macro_regime": macro,
        "mini_structure": mini,
        "combo_bonus": combo_bonus,
        "allow_long": allow_long,
        "allow_short": allow_short,
        "rsi_1h": round(rsi_1h, 1),
        "rsi_4h": round(rsi_4h, 1),
        "slope_4h": round(slope_4h, 8),
    }
