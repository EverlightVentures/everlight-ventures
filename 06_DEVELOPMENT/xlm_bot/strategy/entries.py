from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from indicators.atr import atr
from indicators.ema import ema
from indicators.rsi import rsi
from strategy.confluence import compute_confluences, confluence_passes, structure_zone, fib_zone
from structure.levels import level_breakout, nearest_level


def _ema_zone_hit(df_15m: pd.DataFrame) -> bool:
    if df_15m.empty:
        return False
    e21 = ema(df_15m["close"], 21).iloc[-1]
    e55 = ema(df_15m["close"], 55).iloc[-1]
    price = df_15m["close"].iloc[-1]
    low = min(e21, e55)
    high = max(e21, e55)
    return low <= price <= high


def pullback_continuation(
    price: float,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    df_15m: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
) -> Optional[Dict]:
    conf = compute_confluences(price, df_1h, df_4h, df_15m, levels, fibs, direction)
    if not confluence_passes(conf):
        return None
    # Direction trigger: price on correct side of EMA21
    trigger = False
    if direction == "long":
        trigger = df_15m["close"].iloc[-1] > ema(df_15m["close"], 21).iloc[-1]
    else:
        trigger = df_15m["close"].iloc[-1] < ema(df_15m["close"], 21).iloc[-1]
    if not trigger:
        return None
    return {"type": "pullback", "confluence": conf}


def breakout_retest(
    price: float,
    df_15m: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
) -> Optional[Dict]:
    conf = compute_confluences(price, df_15m, df_15m, df_15m, levels, fibs, direction)
    if not confluence_passes(conf):
        return None
    breakout = level_breakout(price, levels, direction)
    if not breakout:
        return None
    if direction == "long":
        if df_15m["close"].iloc[-1] < df_15m["close"].iloc[-2]:
            return None
    else:
        if df_15m["close"].iloc[-1] > df_15m["close"].iloc[-2]:
            return None
    return {"type": "breakout_retest", "confluence": conf}


def _is_exhaustion_candle(row: pd.Series) -> bool:
    """Doji or small-bodied candle indicating indecision/exhaustion."""
    body = abs(float(row["close"]) - float(row["open"]))
    full_range = float(row["high"]) - float(row["low"])
    if full_range <= 0:
        return False
    # Body is less than 30% of full range = exhaustion/doji
    return (body / full_range) < 0.30


def _is_impulse_candle(df_15m: pd.DataFrame, idx: int = -1, mult: float = 1.5) -> bool:
    """Current candle body >= mult * average of prior 5 candle bodies."""
    if len(df_15m) < 7:
        return False
    row = df_15m.iloc[idx]
    body = abs(float(row["close"]) - float(row["open"]))
    prior_bodies = []
    for i in range(idx - 5, idx):
        r = df_15m.iloc[i]
        prior_bodies.append(abs(float(r["close"]) - float(r["open"])))
    avg_body = sum(prior_bodies) / len(prior_bodies) if prior_bodies else 0
    if avg_body <= 0:
        return False
    return body >= mult * avg_body


def _near_structure_band(price: float, levels: Dict[str, float],
                         direction: str, tolerance_pct: float = 0.015) -> bool:
    """Check if price is near resistance (short) or support (long)."""
    if not levels:
        return False
    for name, lvl in levels.items():
        dist_pct = abs(price - lvl) / price if price > 0 else 0
        if dist_pct > tolerance_pct:
            continue
        if direction == "short" and price >= lvl * 0.99:
            return True
        if direction == "long" and price <= lvl * 1.01:
            return True
    return False


def reversal_impulse(
    price: float,
    df_1h: pd.DataFrame,
    df_15m: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
) -> Optional[Dict]:
    """
    Reversal Impulse Entry - structure rejection reversals.

    Requires 4 core conditions (all must be true) plus at least 1 of 3
    optional confirmations. This replaces the old 7-AND gate.

    Bypasses EMA slope requirement since reversals trade against trend.
    """
    if df_15m.empty or len(df_15m) < 10:
        return None

    # --- REQUIRED 1: Near structure/Fib zone ---
    near_struct = _near_structure_band(price, levels, direction)
    near_fib = fib_zone(price, fibs, tolerance_pct=0.008)
    if not near_struct and not near_fib:
        return None

    # --- REQUIRED 2: Impulse candle (body >= 1.3x avg, lowered from 1.5x) ---
    if not _is_impulse_candle(df_15m, mult=1.3):
        return None

    # --- REQUIRED 3: Direction-confirming close ---
    curr = df_15m.iloc[-1]
    if direction == "short" and float(curr["close"]) >= float(curr["open"]):
        return None
    if direction == "long" and float(curr["close"]) <= float(curr["open"]):
        return None

    # --- REQUIRED 4: Volume elevated (>= 1.2x 10-bar avg; 1.0x was always-true, no filter) ---
    vol_spike = False
    if len(df_15m) >= 12:
        vol_avg = df_15m["volume"].iloc[-11:-1].mean()
        vol_now = float(df_15m["volume"].iloc[-1])
        vol_spike = bool(vol_avg > 0 and vol_now >= 1.2 * vol_avg)
    if not vol_spike:
        return None

    # --- OPTIONAL (need at least 1 of 3) ---
    # A: Exhaustion candle on prior bar
    exhaustion = _is_exhaustion_candle(df_15m.iloc[-2])

    # B: RSI crossing 50 in direction
    rsi_cross = False
    r = rsi(df_15m["close"], 14)
    if not r.isna().iloc[-1] and not r.isna().iloc[-2]:
        rsi_now = float(r.iloc[-1])
        rsi_prev = float(r.iloc[-2])
        if direction == "short" and rsi_prev >= 50 and rsi_now < 50:
            rsi_cross = True
        if direction == "long" and rsi_prev <= 50 and rsi_now > 50:
            rsi_cross = True

    # C: ATR expanding or range expansion
    atr_series = atr(df_15m, 14)
    atr_now = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 0
    atr_mean = float(atr_series.rolling(20).mean().iloc[-1]) if len(atr_series) >= 20 else atr_now
    atr_expanding = atr_mean > 0 and atr_now > 1.15 * atr_mean
    candle_range = float(curr["high"]) - float(curr["low"])
    avg_range = (df_15m["high"] - df_15m["low"]).iloc[-6:-1].mean()
    range_expansion = avg_range > 0 and candle_range > 1.3 * avg_range
    vol_expansion = atr_expanding or range_expansion

    if not (exhaustion or rsi_cross or vol_expansion):
        return None

    conf = {
        "STRUCTURE_ZONE": near_struct,
        "FIB_ZONE": near_fib,
        "EXHAUSTION_CANDLE": exhaustion,
        "IMPULSE_BODY": True,
        "RSI_CROSS_50": rsi_cross,
        "VOLUME_SPIKE": vol_spike,
        "ATR_EXPANDING": atr_expanding,
        "RANGE_EXPANSION": range_expansion,
    }

    return {"type": "reversal_impulse", "confluence": conf}


def compression_breakout(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    expansion_state: dict,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
) -> Optional[Dict]:
    """Compression Breakout — fires when vol transitions from COMPRESSION to
    IGNITION/EXPANSION with structure proximity and impulse candle.

    Catches early moves out of squeeze ranges before a clean retest forms.
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 12:
        return None

    # 1. Vol phase must be IGNITION or EXPANSION
    phase = str(expansion_state.get("phase", "COMPRESSION")).upper()
    if phase not in ("IGNITION", "EXPANSION"):
        return None

    # 2. Confidence threshold
    confidence = float(expansion_state.get("confidence", 0))
    if confidence < 50:
        return None

    # 3. Direction alignment: expansion direction must match or be NEUTRAL
    exp_dir = str(expansion_state.get("direction", "NEUTRAL")).upper()
    if exp_dir != "NEUTRAL":
        if direction == "long" and exp_dir != "LONG":
            return None
        if direction == "short" and exp_dir != "SHORT":
            return None

    # 4. Near structure or Fib zone
    near_struct = _near_structure_band(price, levels, direction)
    near_fib = fib_zone(price, fibs, tolerance_pct=0.008)
    if not near_struct and not near_fib:
        return None

    # 5. Impulse candle on current bar (body >= 1.3x avg)
    if not _is_impulse_candle(df_15m, mult=1.3):
        return None

    # 6. Direction-confirming close
    curr = df_15m.iloc[-1]
    if direction == "long" and float(curr["close"]) <= float(curr["open"]):
        return None
    if direction == "short" and float(curr["close"]) >= float(curr["open"]):
        return None

    conf = {
        "STRUCTURE_ZONE": near_struct,
        "FIB_ZONE": near_fib,
        "IMPULSE_BODY": True,
        "VOL_IGNITION": phase == "IGNITION",
        "VOL_EXPANSION": phase == "EXPANSION",
        "EXPANSION_CONFIDENCE": confidence >= 50,
    }

    return {"type": "compression_breakout", "confluence": conf}


def early_impulse(
    price: float,
    df_15m: pd.DataFrame,
    expansion_state: dict,
    direction: str,
) -> Optional[Dict]:
    """Early Impulse — catch the FIRST strong directional candle after compression,
    before waiting for a full pullback or retest.

    No structure requirement. Safety comes from routing to Lane A/B (high threshold).
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 15:
        return None

    # 1. Vol phase must be IGNITION or EXPANSION
    phase = str(expansion_state.get("phase", "COMPRESSION")).upper()
    if phase not in ("IGNITION", "EXPANSION"):
        return None

    # 2. Current candle body >= 1.5x average body of prior 10 bars (was 2.0x)
    prior_bodies = []
    for i in range(-11, -1):
        if abs(i) > len(df_15m):
            continue
        r = df_15m.iloc[i]
        prior_bodies.append(abs(float(r["close"]) - float(r["open"])))
    if not prior_bodies:
        return None
    avg_prior_body = sum(prior_bodies) / len(prior_bodies)
    curr = df_15m.iloc[-1]
    curr_body = abs(float(curr["close"]) - float(curr["open"]))
    if avg_prior_body <= 0 or curr_body < 1.5 * avg_prior_body:
        return None

    # 3. Strong directional close — close in top/bottom 25% of candle range
    curr_range = float(curr["high"]) - float(curr["low"])
    if curr_range <= 0:
        return None
    if direction == "long":
        close_position = (float(curr["close"]) - float(curr["low"])) / curr_range
        if close_position < 0.75 or float(curr["close"]) <= float(curr["open"]):
            return None
    else:
        close_position = (float(curr["high"]) - float(curr["close"])) / curr_range
        if close_position < 0.75 or float(curr["close"]) >= float(curr["open"]):
            return None

    # 4. Volume spike >= 1.2x 10-bar average (was 1.5x — more opportunity)
    if len(df_15m) >= 12 and "volume" in df_15m.columns:
        vol_avg = df_15m["volume"].iloc[-11:-1].mean()
        vol_now = float(df_15m["volume"].iloc[-1])
        if vol_avg > 0 and vol_now < 1.2 * vol_avg:
            return None
    else:
        return None

    conf = {
        "IMPULSE_BODY": True,
        "VOLUME_SPIKE": True,
        "STRONG_CLOSE": True,
        "PRIOR_COMPRESSION": True,
        "VOL_IGNITION": phase == "IGNITION",
        "VOL_EXPANSION": phase == "EXPANSION",
    }

    return {"type": "early_impulse", "confluence": conf}


def compression_range(
    price: float,
    df_15m: pd.DataFrame,
    expansion_state: dict,
    direction: str,
) -> Optional[Dict]:
    """Compression Range Scalp — mean reversion inside the compression box.

    Fires when vol is COMPRESSION and price is near a range edge with a
    rejection signal (RSI hook or wick rejection).  Targets mid-range.
    This is the "kneel-down killer" — takes trades while waiting for ignition.
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return None

    # 1. Vol phase must be COMPRESSION (the whole point — trade the range)
    phase = str(expansion_state.get("phase", "")).upper()
    if phase != "COMPRESSION":
        return None

    # 2. Get compression range from expansion state
    rng = expansion_state.get("range") or {}
    range_high = float(rng.get("high", 0))
    range_low = float(rng.get("low", 0))
    if range_high <= 0 or range_low <= 0 or range_high <= range_low:
        return None

    range_width = range_high - range_low
    if range_width <= 0:
        return None

    # 3. Price must be near a range edge (within 30% of width from edge)
    edge_zone = range_width * 0.30
    near_low = price <= (range_low + edge_zone)
    near_high = price >= (range_high - edge_zone)

    # Direction alignment: long near bottom, short near top
    if direction == "long" and not near_low:
        return None
    if direction == "short" and not near_high:
        return None

    # 4. RSI hook or wick rejection (need 1 of 2)
    rsi_hook = False
    wick_rejection = False

    r = rsi(df_15m["close"], 14)
    if not r.isna().iloc[-1] and not r.isna().iloc[-2]:
        rsi_now = float(r.iloc[-1])
        rsi_prev = float(r.iloc[-2])
        if direction == "long" and rsi_prev < 40 and rsi_now > rsi_prev:
            rsi_hook = True  # RSI turning up from oversold zone
        if direction == "short" and rsi_prev > 60 and rsi_now < rsi_prev:
            rsi_hook = True  # RSI turning down from overbought zone

    curr = df_15m.iloc[-1]
    curr_range = float(curr["high"]) - float(curr["low"])
    body = abs(float(curr["close"]) - float(curr["open"]))
    if curr_range > 0:
        wick_ratio = 1.0 - (body / curr_range)
        if wick_ratio >= 0.50:  # 50%+ wick = rejection candle
            if direction == "long" and float(curr["close"]) > float(curr["open"]):
                wick_rejection = True  # bullish rejection near bottom
            if direction == "short" and float(curr["close"]) < float(curr["open"]):
                wick_rejection = True  # bearish rejection near top

    if not rsi_hook and not wick_rejection:
        return None

    # 5. Direction-confirming close
    if direction == "long" and float(curr["close"]) <= float(curr["open"]):
        return None
    if direction == "short" and float(curr["close"]) >= float(curr["open"]):
        return None

    # Compute target: mid-range
    mid_range = (range_high + range_low) / 2.0
    position_in_range = (price - range_low) / range_width  # 0=bottom, 1=top

    conf = {
        "RANGE_EDGE": True,
        "RSI_HOOK": rsi_hook,
        "WICK_REJECTION": wick_rejection,
        "DIRECTION_CONFIRM": True,
        "COMPRESSION_PHASE": True,
    }

    return {
        "type": "compression_range",
        "confluence": conf,
        "range_high": round(range_high, 8),
        "range_low": round(range_low, 8),
        "mid_range": round(mid_range, 8),
        "position_in_range": round(position_in_range, 3),
    }


# ---------------------------------------------------------------------------
# Trend Continuation — structure-based entries (Lane H)
# ---------------------------------------------------------------------------

def _detect_swing_points(df: pd.DataFrame, left: int = 2, right: int = 2) -> dict:
    """5-bar swing detection on any OHLC dataframe.

    A swing high has ``left`` lower-high bars before it and ``right``
    lower-high bars after it.  Inverse for swing lows.

    Returns ``{"swing_highs": [(idx, price), ...], "swing_lows": [...]}``
    with the **most recent first**.
    """
    if df is None or df.empty or len(df) < left + right + 1:
        return {"swing_highs": [], "swing_lows": []}

    highs = df["high"].values
    lows = df["low"].values
    swing_highs: list = []
    swing_lows: list = []

    for i in range(left, len(df) - right):
        # --- swing high ---
        is_sh = True
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if highs[j] >= highs[i]:
                is_sh = False
                break
        if is_sh:
            swing_highs.append((i, float(highs[i])))

        # --- swing low ---
        is_sl = True
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if lows[j] <= lows[i]:
                is_sl = False
                break
        if is_sl:
            swing_lows.append((i, float(lows[i])))

    swing_highs.reverse()
    swing_lows.reverse()
    return {"swing_highs": swing_highs, "swing_lows": swing_lows}


def _classify_structure(swings: dict, min_swings: int = 2) -> dict:
    """Classify price structure from swing points.

    * **bearish** = lower-high AND lower-low (trend day short structure)
    * **bullish** = higher-high AND higher-low (trend day long structure)
    """
    result = {
        "bearish_structure": False,
        "bullish_structure": False,
        "last_swing_high": None,
        "last_swing_low": None,
        "prev_swing_high": None,
        "prev_swing_low": None,
    }

    shs = swings.get("swing_highs", [])
    sls = swings.get("swing_lows", [])
    if len(shs) < min_swings or len(sls) < min_swings:
        return result

    _sh0_idx, sh0 = shs[0]
    _sh1_idx, sh1 = shs[1]
    _sl0_idx, sl0 = sls[0]
    _sl1_idx, sl1 = sls[1]

    result["last_swing_high"] = sh0
    result["last_swing_low"] = sl0
    result["prev_swing_high"] = sh1
    result["prev_swing_low"] = sl1

    if sh0 < sh1 and sl0 < sl1:
        result["bearish_structure"] = True
    if sh0 > sh1 and sl0 > sl1:
        result["bullish_structure"] = True

    return result


def detect_15m_structure_bias(df_15m: pd.DataFrame) -> str:
    """Return ``"bearish"``, ``"bullish"``, or ``"neutral"`` from 15m swings.

    Lightweight wrapper used by the countertrend block in main.py.
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 40:
        return "neutral"
    swings = _detect_swing_points(df_15m.tail(60), left=2, right=2)
    structure = _classify_structure(swings, min_swings=2)
    if structure["bearish_structure"]:
        return "bearish"
    if structure["bullish_structure"]:
        return "bullish"
    return "neutral"


def trend_continuation(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    state: dict | None = None,
) -> Optional[Dict]:
    """Structure-based trend continuation entry.

    Fires when ALL of:
      1. Swing structure confirmed (lower-H + lower-L for shorts, etc.)
      2. Price breaks beyond the most recent swing low (short) / high (long)
      3. RSI slope confirms direction
      4. Current candle closed in entry direction
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 40:
        return None

    window = df_15m.tail(60)
    swings = _detect_swing_points(window, left=2, right=2)
    structure = _classify_structure(swings, min_swings=2)

    # --- direction alignment ---
    if direction == "short" and not structure["bearish_structure"]:
        return None
    if direction == "long" and not structure["bullish_structure"]:
        return None

    # --- break of structure level ---
    if direction == "short":
        trigger_level = structure["last_swing_low"]
        if trigger_level is None or price >= trigger_level:
            return None
    else:
        trigger_level = structure["last_swing_high"]
        if trigger_level is None or price <= trigger_level:
            return None

    # --- RSI slope confirmation ---
    r = rsi(df_15m["close"], 14)
    if r.isna().iloc[-1] or r.isna().iloc[-3]:
        return None
    rsi_now = float(r.iloc[-1])
    rsi_prev = float(r.iloc[-3])
    if direction == "short" and rsi_now >= rsi_prev:
        return None
    if direction == "long" and rsi_now <= rsi_prev:
        return None

    # --- direction-confirming candle close ---
    curr = df_15m.iloc[-1]
    if direction == "short" and float(curr["close"]) >= float(curr["open"]):
        return None
    if direction == "long" and float(curr["close"]) <= float(curr["open"]):
        return None

    # --- structure-based stop ---
    if direction == "short":
        structure_stop = structure["last_swing_high"]
    else:
        structure_stop = structure["last_swing_low"]

    # --- continuation re-entry ---
    is_reentry = False
    if state and state.get("_last_trend_exit_structure_intact"):
        last_dir = str(state.get("_last_trend_exit_direction") or "")
        if last_dir == direction:
            last_exit_px = float(state.get("_last_trend_exit_price") or 0)
            last_entry_px = float(state.get("_last_trend_entry_price") or 0)
            if last_exit_px > 0 and last_entry_px > 0:
                impulse = abs(last_exit_px - last_entry_px)
                retrace = abs(price - last_exit_px)
                if impulse > 0 and retrace < 0.50 * impulse:
                    is_reentry = True

    conf = {
        "BEARISH_STRUCTURE": structure["bearish_structure"],
        "BULLISH_STRUCTURE": structure["bullish_structure"],
        "SWING_BREAK": True,
        "RSI_SLOPE_CONFIRM": True,
        "DIRECTION_CLOSE": True,
        "CONTINUATION_REENTRY": is_reentry,
    }

    return {
        "type": "trend_continuation",
        "confluence": conf,
        "structure_stop": round(structure_stop, 8) if structure_stop else None,
        "trigger_level": round(trigger_level, 8),
        "last_swing_high": structure["last_swing_high"],
        "last_swing_low": structure["last_swing_low"],
        "prev_swing_high": structure["prev_swing_high"],
        "prev_swing_low": structure["prev_swing_low"],
        "is_reentry": is_reentry,
    }


# ---------------------------------------------------------------------------
# Fib Retrace — countertrend entries after significant swing moves (Lane I)
# ---------------------------------------------------------------------------

def fib_retrace(
    price: float,
    df_1h: pd.DataFrame,
    df_15m: pd.DataFrame,
    direction: str,
    config: dict | None = None,
) -> Optional[Dict]:
    """Fib retracement entry after a significant swing move.

    Fires when ALL of:
      1. A significant swing (>= 3%) detected on 1h data
      2. Price is near the swing extreme (bottom/top 35% of range)
      3. At least one fib level gives >= 1.5 R:R
      4. >= 2 of 4 reversal confirmations on 15m
      5. Direction-confirming candle close on 15m
    """
    cfg = config or {}
    fib_cfg = cfg.get("fib_retrace") or {}
    if isinstance(fib_cfg, dict) and not fib_cfg.get("enabled", True):
        return None

    if df_1h is None or df_1h.empty or len(df_1h) < 20:
        return None
    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return None

    lookback = int(fib_cfg.get("lookback_bars_1h", 48) or 48)
    min_swing_pct = float(fib_cfg.get("min_swing_pct", 0.03) or 0.03)
    depth_max = float(fib_cfg.get("retrace_depth_max", 0.35) or 0.35)
    min_confirms = int(fib_cfg.get("min_confirmations", 2) or 2)
    min_rr = float(fib_cfg.get("min_rr_ratio", 1.5) or 1.5)
    sl_buf_mult = float(fib_cfg.get("sl_atr_buffer_mult", 0.3) or 0.3)
    sw_left = int(fib_cfg.get("swing_left", 3) or 3)
    sw_right = int(fib_cfg.get("swing_right", 3) or 3)

    # --- 1. Detect significant swing on 1h ---
    window_1h = df_1h.tail(lookback)
    swings = _detect_swing_points(window_1h, left=sw_left, right=sw_right)
    shs = swings.get("swing_highs", [])
    sls = swings.get("swing_lows", [])
    if not shs or not sls:
        return None

    # Find swing pair — for longs: need a down-move (high before low)
    # For shorts: need an up-move (low before high)
    swing_high = swing_low = 0.0
    sh_idx = sl_idx = -1

    if direction == "long":
        # Find most recent swing low, then the swing high that preceded it
        for sl_i, sl_p in sls:
            for sh_i, sh_p in shs:
                if sh_i < sl_i and sh_p > sl_p:
                    swing_high, swing_low = sh_p, sl_p
                    sh_idx, sl_idx = sh_i, sl_i
                    break
            if swing_high > 0:
                break
    else:
        # Find most recent swing high, then the swing low that preceded it
        for sh_i, sh_p in shs:
            for sl_i, sl_p in sls:
                if sl_i < sh_i and sl_p < sh_p:
                    swing_high, swing_low = sh_p, sl_p
                    sh_idx, sl_idx = sh_i, sl_i
                    break
            if swing_high > 0:
                break

    if swing_high <= 0 or swing_low <= 0:
        return None

    swing_range = swing_high - swing_low
    mid_price = (swing_high + swing_low) / 2.0
    swing_range_pct = swing_range / mid_price if mid_price > 0 else 0
    if swing_range_pct < min_swing_pct:
        return None

    # --- 2. Price near swing extreme ---
    if direction == "long":
        depth = (price - swing_low) / swing_range if swing_range > 0 else 1.0
        if depth > depth_max:
            return None
    else:
        depth = (swing_high - price) / swing_range if swing_range > 0 else 1.0
        if depth > depth_max:
            return None

    # --- 3. Compute fib levels and check R:R ---
    fib_38 = swing_low + 0.382 * swing_range
    fib_50 = swing_low + 0.500 * swing_range
    fib_618 = swing_low + 0.618 * swing_range

    # ATR buffer for stop
    atr_buf = 0.0
    atr_series = atr(df_15m, 14)
    if not atr_series.empty and not pd.isna(atr_series.iloc[-1]):
        atr_buf = sl_buf_mult * float(atr_series.iloc[-1])

    if direction == "long":
        stop_price = swing_low - atr_buf
        # Pick best fib TP: prefer 50%, fall back to 38.2%
        fib_tp = fib_50
        fib_name = "fib_0.5"
        sl_dist = price - stop_price
        tp_dist = fib_tp - price
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if rr < min_rr:
            # Try 61.8%
            tp_dist_618 = fib_618 - price
            if tp_dist_618 / sl_dist >= min_rr:
                fib_tp = fib_618
                fib_name = "fib_0.618"
                rr = tp_dist_618 / sl_dist
            else:
                return None
    else:
        stop_price = swing_high + atr_buf
        fib_tp = fib_50
        fib_name = "fib_0.5"
        sl_dist = stop_price - price
        tp_dist = price - fib_tp
        if sl_dist <= 0:
            return None
        rr = tp_dist / sl_dist
        if rr < min_rr:
            tp_dist_618 = price - fib_618
            if sl_dist > 0 and tp_dist_618 / sl_dist >= min_rr:
                fib_tp = fib_618
                fib_name = "fib_0.618"
                rr = tp_dist_618 / sl_dist
            else:
                return None

    # --- 4. Reversal confirmations on 15m (need >= min_confirms) ---
    confirms = 0

    # A: RSI extreme
    r = rsi(df_15m["close"], 14)
    rsi_extreme = False
    rsi_slope_turn = False
    if not r.isna().iloc[-1]:
        rsi_now = float(r.iloc[-1])
        if direction == "long" and rsi_now <= 35:
            rsi_extreme = True
        elif direction == "short" and rsi_now >= 65:
            rsi_extreme = True
        # C: RSI slope turn
        if len(r) >= 3 and not r.isna().iloc[-2]:
            rsi_prev = float(r.iloc[-2])
            if direction == "long" and rsi_now > rsi_prev and rsi_prev < 40:
                rsi_slope_turn = True
            elif direction == "short" and rsi_now < rsi_prev and rsi_prev > 60:
                rsi_slope_turn = True
    if rsi_extreme:
        confirms += 1
    if rsi_slope_turn:
        confirms += 1

    # B: Rejection candle
    curr = df_15m.iloc[-1]
    curr_range = float(curr["high"]) - float(curr["low"])
    body = abs(float(curr["close"]) - float(curr["open"]))
    rejection_candle = False
    if curr_range > 0:
        wick_ratio = 1.0 - (body / curr_range)
        if wick_ratio >= 0.50:
            if direction == "long" and float(curr["close"]) > float(curr["open"]):
                rejection_candle = True
            elif direction == "short" and float(curr["close"]) < float(curr["open"]):
                rejection_candle = True
    if rejection_candle:
        confirms += 1

    # D: Volume spike
    vol_spike = False
    if len(df_15m) >= 12 and "volume" in df_15m.columns:
        vol_avg = df_15m["volume"].iloc[-11:-1].mean()
        vol_now = float(df_15m["volume"].iloc[-1])
        if vol_avg > 0 and vol_now >= 1.0 * vol_avg:
            vol_spike = True
    if vol_spike:
        confirms += 1

    if confirms < min_confirms:
        return None

    # --- 5. Direction-confirming candle close ---
    if direction == "long" and float(curr["close"]) <= float(curr["open"]):
        return None
    if direction == "short" and float(curr["close"]) >= float(curr["open"]):
        return None

    conf = {
        "SWING_DETECTED": True,
        "NEAR_EXTREME": True,
        "FIB_TP_VALID": True,
        "RSI_EXTREME": rsi_extreme,
        "REJECTION_CANDLE": rejection_candle,
        "RSI_SLOPE_TURN": rsi_slope_turn,
        "VOLUME_SPIKE": vol_spike,
        "DIRECTION_CONFIRM": True,
    }

    return {
        "type": "fib_retrace",
        "confluence": conf,
        "swing_high": round(swing_high, 8),
        "swing_low": round(swing_low, 8),
        "swing_range_pct": round(swing_range_pct, 4),
        "fib_tp_price": round(fib_tp, 8),
        "fib_target_name": fib_name,
        "fib_38": round(fib_38, 8),
        "fib_50": round(fib_50, 8),
        "fib_618": round(fib_618, 8),
        "retrace_depth": round(depth, 3),
        "structure_stop": round(stop_price, 8),
    }


# ---------------------------------------------------------------------------
# Slow Bleed Hunter — catches gradual directional grinds
# ---------------------------------------------------------------------------

def slow_bleed_hunter(
    price: float,
    df_15m,
    direction: str,
    config: dict | None = None,
) -> Optional[Dict]:
    """Detect gradual directional moves (slow bleeds) via consecutive candle structure.

    Fires on low-energy trends that indicator-heavy strategies miss:
    steady stair-step moves with no RSI extremes, no volume spikes, no breakout.

    Requirements:
        1. N+ consecutive lower-highs AND lower-lows (short) or the inverse (long)
        2. Price on correct side of EMA-20
        3. Volume at least 80% of 10-bar average (not dead, just not spiking)
        4. RSI in midrange 30-65 (NOT extreme — slow move, not panic)
        5. Candle bodies roughly consistent (no wild spikes)
        6. Confirming candle close in bleed direction
    """
    if config is None:
        config = {}
    sbh = config.get("slow_bleed_hunter") or {}
    if not sbh.get("enabled", True):
        return None

    import numpy as np

    min_bars = int(sbh.get("min_consecutive_bars", 3))
    ema_period = int(sbh.get("ema_period", 20))
    rsi_lo = float(sbh.get("rsi_min", 30))
    rsi_hi = float(sbh.get("rsi_max", 65))
    vol_ratio = float(sbh.get("volume_min_ratio", 0.8))

    if len(df_15m) < max(ema_period + 5, 25):
        return None

    highs = df_15m["high"].values
    lows = df_15m["low"].values
    closes = df_15m["close"].values
    opens = df_15m["open"].values
    volumes = df_15m["volume"].values

    # --- 1. Consecutive bar detection (most recent bars, walk backwards) ---
    consecutive = 0
    for i in range(len(highs) - 1, 0, -1):
        if direction == "short":
            if highs[i] < highs[i - 1] and lows[i] < lows[i - 1]:
                consecutive += 1
            else:
                break
        else:  # long
            if highs[i] > highs[i - 1] and lows[i] > lows[i - 1]:
                consecutive += 1
            else:
                break

    if consecutive < min_bars:
        return None

    # --- 2-6. Confluence checks ---
    conf: Dict[str, bool] = {}

    # Core: consecutive bars (always True if we reached here)
    conf["CONSECUTIVE_BARS"] = True

    # EMA position
    ema = df_15m["close"].ewm(span=ema_period, adjust=False).mean()
    ema_val = float(ema.iloc[-1])
    if direction == "short":
        conf["EMA_POSITION"] = price < ema_val
    else:
        conf["EMA_POSITION"] = price > ema_val

    # Volume trend (alive but not spiking)
    vol_window = volumes[-10:] if len(volumes) >= 10 else volumes
    vol_avg = float(vol_window.mean()) if len(vol_window) > 0 else 1.0
    vol_now = float(volumes[-1]) if len(volumes) > 0 else 0.0
    conf["VOLUME_TREND"] = vol_now >= vol_avg * vol_ratio

    # RSI in midrange (no extremes)
    try:
        from indicators.rsi import rsi as _rsi_fn
        rsi_vals = _rsi_fn(df_15m["close"], 14)
        rsi_now = float(rsi_vals.iloc[-1])
        conf["RSI_MIDRANGE"] = rsi_lo <= rsi_now <= rsi_hi
    except Exception:
        conf["RSI_MIDRANGE"] = True  # fail-open

    # Candle body consistency (bleed = steady bars, not wild swings)
    bodies = np.abs(closes[-consecutive:] - opens[-consecutive:])
    if len(bodies) >= 2 and float(bodies.mean()) > 0:
        body_ratio = float(bodies.max()) / float(bodies.mean())
        conf["CANDLE_CONSISTENCY"] = body_ratio < float(sbh.get("body_consistency_max", 2.5))
    else:
        conf["CANDLE_CONSISTENCY"] = False

    # Confirming candle close (last bar closes in bleed direction)
    if direction == "short":
        conf["CONFIRMING_CLOSE"] = float(closes[-1]) < float(opens[-1])
    else:
        conf["CONFIRMING_CLOSE"] = float(closes[-1]) > float(opens[-1])

    # Need at least 2 confirmations beyond CONSECUTIVE_BARS
    confirm_count = sum(1 for k, v in conf.items() if v and k != "CONSECUTIVE_BARS")
    min_confirms = int(sbh.get("min_confirmations", 2))
    if confirm_count < min_confirms:
        return None

    # --- Structure stop: high/low of the bar where bleed started ---
    bleed_start_idx = max(0, len(highs) - 1 - consecutive)
    if direction == "short":
        structure_stop = float(highs[bleed_start_idx])
    else:
        structure_stop = float(lows[bleed_start_idx])

    # Average bar body size (useful for TP estimation)
    avg_bar = float(bodies.mean()) if len(bodies) > 0 else 0.0

    return {
        "type": "slow_bleed_hunter",
        "confluence": conf,
        "bleed_bars": consecutive,
        "avg_bar_size": round(avg_bar, 8),
        "structure_stop": round(structure_stop, 8),
    }


# ---------------------------------------------------------------------------
# Lane K: Wick Rejection at Structure (entry lane)
# ---------------------------------------------------------------------------

def wick_rejection(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    levels: Dict[str, float],
    direction: str,
) -> Optional[Dict]:
    """Wick Rejection Entry -- large wick at S/R level, body closes away.

    Catches institutional liquidity grabs where price pokes through a level
    then snaps back. The wick shows the grab, the close shows the rejection.

    Requirements (all must be true):
        1. Price within 1.5% of a structure level
        2. Wick >= 60% of candle range (strong rejection)
        3. Body closes away from the level in entry direction
        4. Volume >= 1.0x 10-bar average
        5. Previous bar was NOT also a big-wick rejection (no double-wick chop)
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 12:
        return None

    curr = df_15m.iloc[-1]
    prev = df_15m.iloc[-2]
    c_open = float(curr["open"])
    c_close = float(curr["close"])
    c_high = float(curr["high"])
    c_low = float(curr["low"])
    c_range = c_high - c_low
    if c_range <= 0:
        return None

    # 1. Near a structure level
    near_struct = _near_structure_band(price, levels, direction, tolerance_pct=0.015)
    if not near_struct:
        return None

    # 2. Wick >= 60% of candle range
    body = abs(c_close - c_open)
    wick_pct = 1.0 - (body / c_range) if c_range > 0 else 0
    if wick_pct < 0.60:
        return None

    # 3. Body closes away from level in entry direction
    if direction == "long" and c_close <= c_open:
        return None  # need bullish close for long
    if direction == "short" and c_close >= c_open:
        return None  # need bearish close for short

    # For longs: wick should poke below (low is the wick), body closes up
    # For shorts: wick should poke above (high is the wick), body closes down
    if direction == "long":
        lower_wick = min(c_open, c_close) - c_low
        if lower_wick < 0.5 * c_range:
            return None  # lower wick must be dominant
    else:
        upper_wick = c_high - max(c_open, c_close)
        if upper_wick < 0.5 * c_range:
            return None  # upper wick must be dominant

    # 4. Volume >= 1.0x 10-bar average
    vol_avg = df_15m["volume"].iloc[-11:-1].mean()
    vol_now = float(df_15m["volume"].iloc[-1])
    if vol_avg <= 0 or vol_now < 1.0 * vol_avg:
        return None

    # 5. Previous bar must NOT also be a big wick (no double-wick chop)
    p_range = float(prev["high"]) - float(prev["low"])
    if p_range > 0:
        p_body = abs(float(prev["close"]) - float(prev["open"]))
        p_wick_pct = 1.0 - (p_body / p_range)
        if p_wick_pct >= 0.60:
            return None  # previous bar was also a rejection -- choppy

    conf = {
        "STRUCTURE_ZONE": True,
        "WICK_REJECTION": True,
        "DIRECTION_CONFIRM": True,
        "VOLUME_SPIKE": vol_now >= 1.3 * vol_avg,
        "VOLUME_ADEQUATE": True,
        "SINGLE_WICK": True,
    }

    return {"type": "wick_rejection", "confluence": conf}


# ---------------------------------------------------------------------------
# Lane L: MTF Conflict Block (blocking lane -- prevents entries)
# ---------------------------------------------------------------------------

def mtf_conflict_block(
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    direction: str,
) -> bool:
    """MTF Conflict Block -- returns True to BLOCK entries.

    Blocks entries when the 15m signal contradicts 1h/4h trend structure.
    This is NOT an entry lane -- it prevents bad entries from other lanes.

    Blocks when 2 of 3 conditions are true:
        1. 15m EMA slope contradicts 1h EMA slope
        2. 15m RSI and 1h RSI disagree by >20 points
        3. 4h EMA slope contradicts entry direction
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return False
    if df_1h is None or df_1h.empty or len(df_1h) < 10:
        return False

    conflicts = 0

    # 1. EMA slope conflict: 15m vs 1h
    try:
        ema_15m = ema(df_15m["close"], 21)
        ema_1h_s = ema(df_1h["close"], 21)
        slope_15m = float(ema_15m.iloc[-1]) - float(ema_15m.iloc[-3])
        slope_1h = float(ema_1h_s.iloc[-1]) - float(ema_1h_s.iloc[-3])
        if direction == "long":
            if slope_15m > 0 and slope_1h < 0:
                conflicts += 1  # 15m rising but 1h falling
        else:
            if slope_15m < 0 and slope_1h > 0:
                conflicts += 1  # 15m falling but 1h rising
    except Exception:
        pass

    # 2. RSI gap > 20 between 15m and 1h
    try:
        rsi_15m = rsi(df_15m["close"], 14)
        rsi_1h_s = rsi(df_1h["close"], 14)
        rsi_15m_val = float(rsi_15m.iloc[-1])
        rsi_1h_val = float(rsi_1h_s.iloc[-1])
        if abs(rsi_15m_val - rsi_1h_val) > 20:
            conflicts += 1
    except Exception:
        pass

    # 3. 4h EMA slope contradicts direction
    try:
        if df_4h is not None and not df_4h.empty and len(df_4h) >= 5:
            ema_4h_s = ema(df_4h["close"], 21)
            slope_4h = float(ema_4h_s.iloc[-1]) - float(ema_4h_s.iloc[-3])
            if direction == "long" and slope_4h < 0:
                conflicts += 1
            elif direction == "short" and slope_4h > 0:
                conflicts += 1
    except Exception:
        pass

    return conflicts >= 2


# ---------------------------------------------------------------------------
# Lane M: Volume Climax Reversal (entry lane)
# ---------------------------------------------------------------------------

def volume_climax_reversal(
    price: float,
    df_15m: pd.DataFrame,
    direction: str,
) -> Optional[Dict]:
    """Volume Climax Reversal -- catches capitulation events.

    Fires when an extreme volume bar prints with an against-momentum close,
    indicating exhaustion and potential reversal.

    Requirements (all must be true):
        1. Current bar volume >= 2.5x 20-bar average (climax)
        2. Close is in the entry direction (reversal started)
        3. Prior 3 bars were moving against entry direction (momentum to reverse)
        4. RSI was in extreme zone (>70 or <30) within last 3 bars
        5. Vol phase is not EXPANSION (avoid catching falling knives in trends)
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 25:
        return None

    curr = df_15m.iloc[-1]
    c_close = float(curr["close"])
    c_open = float(curr["open"])

    # 1. Volume climax: >= 2.5x 20-bar average
    vol_window = df_15m["volume"].iloc[-21:-1]
    if vol_window.empty or float(vol_window.mean()) <= 0:
        return None
    vol_avg = float(vol_window.mean())
    vol_now = float(df_15m["volume"].iloc[-1])
    vol_ratio = vol_now / vol_avg
    if vol_ratio < 2.5:
        return None

    # 2. Close in entry direction (reversal candle)
    if direction == "long" and c_close <= c_open:
        return None  # need bullish close for long reversal
    if direction == "short" and c_close >= c_open:
        return None  # need bearish close for short reversal

    # 3. Prior bars were moving against entry direction (need something to reverse)
    prior_closes = [float(df_15m.iloc[i]["close"]) for i in range(-4, -1)]
    if direction == "long":
        # Prior bars should have been falling (we're reversing a drop)
        if not (prior_closes[0] > prior_closes[1] > prior_closes[2]):
            # At least 2 of 3 prior bars declining
            declining = sum(1 for i in range(len(prior_closes) - 1)
                           if prior_closes[i] > prior_closes[i + 1])
            if declining < 2:
                return None
    else:
        # Prior bars should have been rising (we're reversing a pump)
        rising = sum(1 for i in range(len(prior_closes) - 1)
                     if prior_closes[i] < prior_closes[i + 1])
        if rising < 2:
            return None

    # 4. RSI was in extreme zone within last 3 bars
    rsi_extreme = False
    try:
        r = rsi(df_15m["close"], 14)
        for offset in range(-3, 0):
            if pd.isna(r.iloc[offset]):
                continue
            rsi_val = float(r.iloc[offset])
            if direction == "long" and rsi_val < 30:
                rsi_extreme = True
                break
            if direction == "short" and rsi_val > 70:
                rsi_extreme = True
                break
    except Exception:
        pass
    if not rsi_extreme:
        return None

    # Build confluence
    c_range = float(curr["high"]) - float(curr["low"])
    body = abs(c_close - c_open)
    body_ratio = body / c_range if c_range > 0 else 0

    conf = {
        "VOLUME_CLIMAX": True,
        "DIRECTION_CONFIRM": True,
        "PRIOR_MOMENTUM": True,
        "RSI_EXTREME": True,
        "STRONG_BODY": body_ratio >= 0.5,
        "VOL_RATIO": round(vol_ratio, 1),
    }

    return {"type": "volume_climax_reversal", "confluence": conf}


# ---------------------------------------------------------------------------
# Lane N: VWAP Reversion (entry lane)
# ---------------------------------------------------------------------------

def vwap_reversion(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    vwap_dev_pct: float = 0.01,
) -> Optional[Dict]:
    """VWAP Reversion Entry -- price snaps back to VWAP after deviation.

    Fires when price has been >1% away from VWAP and is now reverting
    back toward fair value.

    Requirements (all must be true):
        1. Current price deviation from VWAP > vwap_dev_pct (overextended)
        2. Price is moving BACK toward VWAP (reversion started)
        3. Direction aligns with reversion (long if below VWAP, short if above)
        4. RSI supports reversion (not in extreme opposing zone)
        5. Volume declining from recent peak (climax passed)
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return None

    # Compute VWAP
    try:
        from indicators.vwap import vwap as vwap_fn
        vwap_series = vwap_fn(df_15m)
        if vwap_series.empty or pd.isna(vwap_series.iloc[-1]):
            return None
        vwap_val = float(vwap_series.iloc[-1])
    except Exception:
        return None

    if vwap_val <= 0:
        return None

    # 1. Deviation from VWAP
    deviation = (price - vwap_val) / vwap_val
    abs_dev = abs(deviation)
    if abs_dev < vwap_dev_pct:
        return None  # not overextended enough

    # 2-3. Direction must align with reversion
    if direction == "long" and deviation >= 0:
        return None  # price is above VWAP, can't go long for reversion
    if direction == "short" and deviation <= 0:
        return None  # price is below VWAP, can't go short for reversion

    # Check price is actually reverting (current candle moves toward VWAP)
    curr = df_15m.iloc[-1]
    prev = df_15m.iloc[-2]
    if direction == "long":
        # Price below VWAP, reverting up: close should be > prior close
        if float(curr["close"]) <= float(prev["close"]):
            return None
    else:
        # Price above VWAP, reverting down: close should be < prior close
        if float(curr["close"]) >= float(prev["close"]):
            return None

    # 4. RSI supports reversion
    rsi_ok = False
    try:
        r = rsi(df_15m["close"], 14)
        if not pd.isna(r.iloc[-1]):
            rsi_val = float(r.iloc[-1])
            if direction == "long" and rsi_val < 60:
                rsi_ok = True  # not overbought, room to rise
            if direction == "short" and rsi_val > 40:
                rsi_ok = True  # not oversold, room to fall
    except Exception:
        rsi_ok = True  # fail-open

    if not rsi_ok:
        return None

    # 5. Volume declining from recent peak (climax has passed)
    vol_declining = False
    try:
        vols = df_15m["volume"].iloc[-5:]
        if len(vols) >= 3:
            peak_idx = vols.idxmax()
            peak_pos = list(vols.index).index(peak_idx)
            # Peak should be in position 0-2 (earlier), not the latest bar
            if peak_pos < len(vols) - 1:
                vol_declining = True
    except Exception:
        vol_declining = True  # fail-open

    if not vol_declining:
        return None

    conf = {
        "VWAP_DEVIATION": True,
        "DIRECTION_ALIGN": True,
        "REVERSION_STARTED": True,
        "RSI_SUPPORTS": rsi_ok,
        "VOLUME_DECLINING": vol_declining,
        "DEVIATION_PCT": round(abs_dev * 100, 2),
    }

    return {
        "type": "vwap_reversion",
        "confluence": conf,
        "vwap_price": round(vwap_val, 8),
        "deviation_pct": round(deviation * 100, 3),
    }


# ---------------------------------------------------------------------------
# Lane O: Grid Range (grid-style mean-reversion at range edges)
# ---------------------------------------------------------------------------

def grid_range(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    levels: list,
    fibs: dict,
    expansion_state: dict,
) -> Optional[Dict]:
    """Grid Range Entry -- grid-bot-style trades at range boundaries.

    Fires when price touches support/resistance in a ranging market.
    Mimics grid bot: buy at support, sell at resistance. Low threshold
    because range edges have 70-80% bounce rate in confirmed ranges.

    Requirements (all must be true):
        1. Vol regime is COMPRESSION (confirmed range, ADX < 25)
        2. Price is near a structure level or fib level (within 1%)
        3. RSI is at extreme for direction (long < 35, short > 65)
        4. No ATR expansion (not breaking out)
        5. At least 2 touches of the level in last 20 bars (confirmed S/R)
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return None

    phase = str(expansion_state.get("phase") or "").upper()
    if phase != "COMPRESSION":
        return None  # only trade in confirmed ranges

    # RSI extreme check
    try:
        r = rsi(df_15m["close"], 14)
        rsi_val = float(r.iloc[-1]) if not pd.isna(r.iloc[-1]) else 50
    except Exception:
        rsi_val = 50

    if direction == "long" and rsi_val > 35:
        return None  # not oversold enough for long
    if direction == "short" and rsi_val < 65:
        return None  # not overbought enough for short

    # Near structure level check (within 1.0%)
    near_level = False
    nearest_level = None
    tolerance = 0.01  # 1%
    for lvl in (levels or []):
        lvl_price = float(lvl.get("price") or lvl if isinstance(lvl, (int, float)) else 0)
        if lvl_price <= 0:
            continue
        dist = abs(price - lvl_price) / lvl_price
        if dist <= tolerance:
            near_level = True
            nearest_level = lvl_price
            break

    # Also check fib levels
    if not near_level and fibs:
        for fib_key in ["fib_382", "fib_500", "fib_618", "fib_236", "fib_786"]:
            fib_val = float(fibs.get(fib_key) or 0)
            if fib_val <= 0:
                continue
            dist = abs(price - fib_val) / fib_val
            if dist <= tolerance:
                near_level = True
                nearest_level = fib_val
                break

    if not near_level:
        return None

    # No ATR expansion (must be calm, range-bound market)
    try:
        from indicators.atr import atr as atr_fn
        atr_vals = atr_fn(df_15m, 14)
        if len(atr_vals) >= 20:
            atr_now = float(atr_vals.iloc[-1])
            atr_mean = float(atr_vals.iloc[-20:].mean())
            if atr_mean > 0 and (atr_now / atr_mean) > 1.3:
                return None  # ATR expanding, likely breakout
    except Exception:
        pass

    # Level touch count: at least 2 touches in last 20 bars
    touch_count = 0
    if nearest_level and nearest_level > 0:
        for i in range(-20, 0):
            try:
                bar = df_15m.iloc[i]
                bar_low = float(bar["low"])
                bar_high = float(bar["high"])
                if bar_low <= nearest_level <= bar_high:
                    touch_count += 1
            except Exception:
                pass

    if touch_count < 2:
        return None  # not enough touches to confirm level

    # Candle confirmation: direction-confirming close
    curr = df_15m.iloc[-1]
    curr_open = float(curr["open"])
    curr_close = float(curr["close"])
    if direction == "long" and curr_close < curr_open:
        return None  # bearish candle, wait for confirmation
    if direction == "short" and curr_close > curr_open:
        return None  # bullish candle, wait for confirmation

    conf = {
        "COMPRESSION_RANGE": True,
        "RSI_EXTREME": True,
        "NEAR_LEVEL": True,
        "NO_ATR_EXPANSION": True,
        "LEVEL_TOUCHES": touch_count,
        "CANDLE_CONFIRM": True,
    }

    return {
        "type": "grid_range",
        "confluence": conf,
        "nearest_level": round(nearest_level, 8) if nearest_level else None,
        "rsi": round(rsi_val, 1),
        "touch_count": touch_count,
    }


# ---------------------------------------------------------------------------
# Lane Q: Funding Arb Bias
# ---------------------------------------------------------------------------

def funding_arb_bias(
    price: float,
    df_15m: pd.DataFrame,
    direction: str,
    contract_ctx: dict,
    config: dict = None,
) -> Optional[Dict]:
    """Funding Arb Bias -- trade in the direction that earns funding.

    When funding rate is very negative, shorts are paying longs = bullish.
    When funding rate is very positive, longs are paying shorts = bearish.
    This is free edge: you get paid just for holding the right direction.

    Requirements:
        1. Funding rate beyond threshold (|rate| > 0.01%)
        2. Direction aligns with funding (long when negative, short when positive)
        3. RSI not extreme against direction (no buying overbought)
        4. Confirming candle in direction
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 14:
        return None
    if not contract_ctx:
        return None

    funding_rate = float(contract_ctx.get("funding_rate") or contract_ctx.get("annualized_funding") or 0)
    # Normalize: if annualized, convert to per-period (approx /365/3 for 8h funding)
    if abs(funding_rate) > 1.0:
        funding_rate = funding_rate / 365.0 / 3.0

    cfg = config or {}
    threshold = float(cfg.get("funding_arb_threshold", 0.0001) or 0.0001)

    # Direction must align with funding
    if direction == "long" and funding_rate > -threshold:
        return None  # funding not negative enough for long bias
    if direction == "short" and funding_rate < threshold:
        return None  # funding not positive enough for short bias

    # RSI check: don't buy overbought or sell oversold
    try:
        r = rsi(df_15m["close"], 14)
        rsi_val = float(r.iloc[-1]) if not pd.isna(r.iloc[-1]) else 50
    except Exception:
        rsi_val = 50

    if direction == "long" and rsi_val > 70:
        return None
    if direction == "short" and rsi_val < 30:
        return None

    # Confirming candle
    curr = df_15m.iloc[-1]
    c_open, c_close = float(curr["open"]), float(curr["close"])
    if direction == "long" and c_close < c_open:
        return None
    if direction == "short" and c_close > c_open:
        return None

    # EMA trend alignment (21-period)
    try:
        ema21 = ema(df_15m["close"], 21).iloc[-1]
        trend_aligned = (direction == "long" and price > ema21) or (direction == "short" and price < ema21)
    except Exception:
        trend_aligned = False

    conf = {
        "FUNDING_EXTREME": True,
        "DIRECTION_ALIGNED": True,
        "RSI_OK": True,
        "CANDLE_CONFIRM": True,
        "TREND_ALIGNED": trend_aligned,
    }

    return {
        "type": "funding_arb_bias",
        "confluence": conf,
        "funding_rate": round(funding_rate, 8),
        "rsi": round(rsi_val, 1),
        "trend_aligned": trend_aligned,
    }


# ---------------------------------------------------------------------------
# Lane R: Regime Low Vol (Range-Edge Scalp in Low-Vol Regime)
# ---------------------------------------------------------------------------

def regime_low_vol(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    expansion_state: dict,
    levels: list = None,
) -> Optional[Dict]:
    """Regime Low Vol -- scalp range edges when volatility is at historic lows.

    When realized vol collapses and BB width narrows to squeeze levels,
    price oscillates in tight range. Trade the edges of that range.

    Requirements:
        1. COMPRESSION phase confirmed
        2. BB width in bottom 20% of last 100 bars (squeeze)
        3. ATR declining (not expanding)
        4. Price near range edge (top/bottom 25% of recent range)
        5. RSI confirms direction (oversold for long, overbought for short)
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 100:
        return None

    phase = str(expansion_state.get("phase") or "").upper()
    if phase != "COMPRESSION":
        return None

    close = df_15m["close"]

    # BB width squeeze detection
    try:
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_width = (std20 * 2) / sma20  # normalized BB width
        bb_now = float(bb_width.iloc[-1])
        bb_pctile = float((bb_width.iloc[-100:] < bb_now).sum()) / 100.0
        if bb_pctile > 0.25:
            return None  # not in bottom 25% = not a squeeze
    except Exception:
        return None

    # ATR declining check
    try:
        atr_vals = atr(df_15m, 14)
        if len(atr_vals) >= 10:
            atr_now = float(atr_vals.iloc[-1])
            atr_5ago = float(atr_vals.iloc[-5])
            if atr_now > atr_5ago * 1.05:
                return None  # ATR rising, not a low-vol regime
    except Exception:
        return None

    # Range edge detection: top/bottom 25% of 50-bar range
    try:
        recent_high = float(df_15m["high"].iloc[-50:].max())
        recent_low = float(df_15m["low"].iloc[-50:].min())
        range_size = recent_high - recent_low
        if range_size <= 0:
            return None

        position_in_range = (price - recent_low) / range_size

        if direction == "long" and position_in_range > 0.30:
            return None  # not near bottom of range
        if direction == "short" and position_in_range < 0.70:
            return None  # not near top of range
    except Exception:
        return None

    # RSI confirmation
    try:
        r = rsi(close, 14)
        rsi_val = float(r.iloc[-1]) if not pd.isna(r.iloc[-1]) else 50
    except Exception:
        rsi_val = 50

    if direction == "long" and rsi_val > 40:
        return None
    if direction == "short" and rsi_val < 60:
        return None

    # Confirming candle
    curr = df_15m.iloc[-1]
    c_open, c_close = float(curr["open"]), float(curr["close"])
    if direction == "long" and c_close < c_open:
        return None
    if direction == "short" and c_close > c_open:
        return None

    conf = {
        "COMPRESSION_CONFIRMED": True,
        "BB_SQUEEZE": True,
        "ATR_DECLINING": True,
        "RANGE_EDGE": True,
        "RSI_EXTREME": True,
        "CANDLE_CONFIRM": True,
    }

    return {
        "type": "regime_low_vol",
        "confluence": conf,
        "bb_pctile": round(bb_pctile, 3),
        "rsi": round(rsi_val, 1),
        "range_position": round(position_in_range, 3),
        "range_high": round(recent_high, 8),
        "range_low": round(recent_low, 8),
    }


# ---------------------------------------------------------------------------
# Lane S: Stat Arb Proxy (Z-Score Mean Reversion)
# ---------------------------------------------------------------------------

def stat_arb_proxy(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
) -> Optional[Dict]:
    """Stat Arb Proxy -- z-score mean reversion using price vs rolling mean.

    Without multi-pair data, we use XLM's own statistical properties:
    when price deviates >2 standard deviations from its rolling mean,
    mean reversion is 75-85% likely within 4-8 hours.

    Requirements:
        1. Z-score > 2.0 (short) or < -2.0 (long) on 1h data
        2. Z-score on 15m confirms same direction
        3. Price showing initial mean-reversion move (candle reversal)
        4. Not in strong trend (ADX < 30 on 1h)
    """
    if df_1h is None or df_1h.empty or len(df_1h) < 100:
        return None
    if df_15m is None or df_15m.empty or len(df_15m) < 50:
        return None

    # 1h z-score (100-period rolling mean and std)
    try:
        close_1h = df_1h["close"].astype(float)
        mean_1h = close_1h.rolling(100).mean().iloc[-1]
        std_1h = close_1h.rolling(100).std().iloc[-1]
        if std_1h <= 0 or pd.isna(mean_1h) or pd.isna(std_1h):
            return None
        zscore_1h = (price - mean_1h) / std_1h
    except Exception:
        return None

    # Direction must align with z-score
    if direction == "long" and zscore_1h > -1.8:
        return None  # not enough downside deviation
    if direction == "short" and zscore_1h < 1.8:
        return None  # not enough upside deviation

    # 15m z-score confirmation (50-period)
    try:
        close_15m = df_15m["close"].astype(float)
        mean_15m = close_15m.rolling(50).mean().iloc[-1]
        std_15m = close_15m.rolling(50).std().iloc[-1]
        if std_15m <= 0 or pd.isna(mean_15m) or pd.isna(std_15m):
            return None
        zscore_15m = (price - mean_15m) / std_15m
    except Exception:
        return None

    if direction == "long" and zscore_15m > -1.5:
        return None
    if direction == "short" and zscore_15m < 1.5:
        return None

    # ADX check on 1h: must NOT be strong trend (ADX < 30)
    try:
        # Simplified ADX proxy: use ATR slope as trend strength
        atr_1h = atr(df_1h, 14)
        if len(atr_1h) >= 14:
            atr_now = float(atr_1h.iloc[-1])
            atr_mean = float(atr_1h.iloc[-14:].mean())
            # Strong trend = ATR expanding rapidly
            if atr_mean > 0 and (atr_now / atr_mean) > 1.5:
                return None  # strong trend, don't mean-revert
    except Exception:
        pass

    # Confirming candle: initial reversal move
    curr = df_15m.iloc[-1]
    c_open, c_close = float(curr["open"]), float(curr["close"])
    if direction == "long" and c_close < c_open:
        return None  # still falling
    if direction == "short" and c_close > c_open:
        return None  # still rising

    conf = {
        "ZSCORE_1H_EXTREME": True,
        "ZSCORE_15M_CONFIRM": True,
        "NO_STRONG_TREND": True,
        "CANDLE_REVERSAL": True,
    }

    return {
        "type": "stat_arb_proxy",
        "confluence": conf,
        "zscore_1h": round(zscore_1h, 3),
        "zscore_15m": round(zscore_15m, 3),
        "mean_1h": round(mean_1h, 8),
        "std_1h": round(std_1h, 8),
    }


# ---------------------------------------------------------------------------
# Lane T: Orderflow Imbalance (Volume Delta Proxy)
# ---------------------------------------------------------------------------

def orderflow_imbalance(
    price: float,
    df_15m: pd.DataFrame,
    direction: str,
) -> Optional[Dict]:
    """Orderflow Imbalance -- approximate buy/sell pressure from candle structure.

    Without L2 order book data, we estimate volume delta using the
    close position within each bar's range (close-to-range method):
      buy_vol  = volume * (close - low) / (high - low)
      sell_vol = volume * (high - close) / (high - low)

    When 3-bar aggregate ratio exceeds 2:1, strong directional pressure.

    Requirements:
        1. 3-bar volume delta ratio > 2:1 in direction
        2. Current bar volume above average (confirming interest)
        3. Direction-confirming candle
        4. RSI not extreme against direction
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return None
    if "volume" not in df_15m.columns:
        return None

    # Compute 3-bar buy/sell volume delta
    buy_vol_total = 0.0
    sell_vol_total = 0.0
    for i in range(-3, 0):
        try:
            bar = df_15m.iloc[i]
            h = float(bar["high"])
            l = float(bar["low"])
            c = float(bar["close"])
            v = float(bar["volume"])
            bar_range = h - l
            if bar_range <= 0 or v <= 0:
                continue
            buy_pct = (c - l) / bar_range
            sell_pct = (h - c) / bar_range
            buy_vol_total += v * buy_pct
            sell_vol_total += v * sell_pct
        except Exception:
            continue

    if buy_vol_total <= 0 and sell_vol_total <= 0:
        return None

    # Calculate ratio
    if direction == "long":
        if sell_vol_total <= 0:
            ratio = 10.0
        else:
            ratio = buy_vol_total / sell_vol_total
        if ratio < 2.0:
            return None  # not enough buying pressure
    else:
        if buy_vol_total <= 0:
            ratio = 10.0
        else:
            ratio = sell_vol_total / buy_vol_total
        if ratio < 2.0:
            return None  # not enough selling pressure

    # Current bar volume above 20-bar average
    try:
        vol_avg = float(df_15m["volume"].iloc[-20:].mean())
        vol_now = float(df_15m["volume"].iloc[-1])
        if vol_avg > 0 and vol_now < vol_avg * 0.8:
            return None  # low volume, weak signal
    except Exception:
        return None

    # Confirming candle
    curr = df_15m.iloc[-1]
    c_open, c_close = float(curr["open"]), float(curr["close"])
    if direction == "long" and c_close < c_open:
        return None
    if direction == "short" and c_close > c_open:
        return None

    # RSI sanity: don't chase extremes
    try:
        r = rsi(df_15m["close"], 14)
        rsi_val = float(r.iloc[-1]) if not pd.isna(r.iloc[-1]) else 50
    except Exception:
        rsi_val = 50

    if direction == "long" and rsi_val > 72:
        return None
    if direction == "short" and rsi_val < 28:
        return None

    conf = {
        "VOLUME_DELTA_EXTREME": True,
        "VOLUME_ABOVE_AVG": True,
        "CANDLE_CONFIRM": True,
        "RSI_OK": True,
    }

    return {
        "type": "orderflow_imbalance",
        "confluence": conf,
        "delta_ratio": round(ratio, 2),
        "buy_vol": round(buy_vol_total, 0),
        "sell_vol": round(sell_vol_total, 0),
        "rsi": round(rsi_val, 1),
    }


# ---------------------------------------------------------------------------
# Lane U: Macro MA Cross (200-MA Breakout on Higher TF)
# ---------------------------------------------------------------------------

def macro_ma_cross(
    price: float,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    direction: str,
) -> Optional[Dict]:
    """Macro MA Cross -- 200-period MA break on 1h with 4h confirmation.

    The 200 MA is the institutional dividing line. When price crosses it
    with momentum, large moves follow. This catches the big regime shifts.

    Requirements:
        1. Price crossed 200 MA on 1h within last 3 bars
        2. Direction matches the cross (long = cross above, short = cross below)
        3. 50 MA on 4h confirms trend direction
        4. Momentum candle on cross bar (strong body)
        5. Volume above average on cross
    """
    if df_1h is None or df_1h.empty or len(df_1h) < 200:
        return None

    close_1h = df_1h["close"].astype(float)

    # 200 MA on 1h
    try:
        ma200 = close_1h.rolling(200).mean()
        ma200_now = float(ma200.iloc[-1])
        if pd.isna(ma200_now) or ma200_now <= 0:
            return None
    except Exception:
        return None

    # Check for recent cross (within last 3 bars)
    cross_found = False
    cross_bar_idx = -1
    for i in range(1, 4):
        try:
            prev_close = float(close_1h.iloc[-(i + 1)])
            curr_close = float(close_1h.iloc[-i])
            prev_ma = float(ma200.iloc[-(i + 1)])
            curr_ma = float(ma200.iloc[-i])

            if pd.isna(prev_ma) or pd.isna(curr_ma):
                continue

            if direction == "long":
                if prev_close < prev_ma and curr_close > curr_ma:
                    cross_found = True
                    cross_bar_idx = -i
                    break
            else:
                if prev_close > prev_ma and curr_close < curr_ma:
                    cross_found = True
                    cross_bar_idx = -i
                    break
        except Exception:
            continue

    if not cross_found:
        return None

    # 4h 50 MA confirmation (if available)
    htf_confirmed = False
    if df_4h is not None and not df_4h.empty and len(df_4h) >= 50:
        try:
            ma50_4h = df_4h["close"].astype(float).rolling(50).mean()
            ma50_4h_now = float(ma50_4h.iloc[-1])
            if not pd.isna(ma50_4h_now):
                if direction == "long" and price > ma50_4h_now:
                    htf_confirmed = True
                elif direction == "short" and price < ma50_4h_now:
                    htf_confirmed = True
        except Exception:
            pass
    else:
        htf_confirmed = True  # no 4h data, skip this check

    # Cross bar must be a momentum candle (body > 60% of range)
    try:
        cross_bar = df_1h.iloc[cross_bar_idx]
        body = abs(float(cross_bar["close"]) - float(cross_bar["open"]))
        bar_range = float(cross_bar["high"]) - float(cross_bar["low"])
        if bar_range > 0:
            body_ratio = body / bar_range
        else:
            body_ratio = 0
        if body_ratio < 0.50:
            return None  # weak cross, not convincing
    except Exception:
        return None

    # Volume above average on cross
    vol_confirmed = True
    try:
        if "volume" in df_1h.columns:
            vol_avg = float(df_1h["volume"].iloc[-20:].mean())
            vol_cross = float(df_1h.iloc[cross_bar_idx]["volume"])
            if vol_avg > 0 and vol_cross < vol_avg * 0.9:
                vol_confirmed = False
    except Exception:
        pass

    if not vol_confirmed:
        return None

    # Current price still on correct side of MA
    if direction == "long" and price < ma200_now:
        return None
    if direction == "short" and price > ma200_now:
        return None

    conf = {
        "MA200_CROSS": True,
        "DIRECTION_ALIGNED": True,
        "HTF_CONFIRMED": htf_confirmed,
        "MOMENTUM_CANDLE": True,
        "VOLUME_CONFIRMED": True,
    }

    return {
        "type": "macro_ma_cross",
        "confluence": conf,
        "ma200": round(ma200_now, 8),
        "cross_bars_ago": abs(cross_bar_idx),
        "body_ratio": round(body_ratio, 3),
        "htf_confirmed": htf_confirmed,
    }


# ---------------------------------------------------------------------------
# Lane V: Liquidity Sweep (bidirectional heatmap strategy)
# ---------------------------------------------------------------------------

def liquidity_sweep(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    liquidation_intel: Optional[Dict] = None,
) -> Optional[Dict]:
    """Liquidity Sweep -- bidirectional entry based on liquidation clusters.

    Two modes:
      Reversal: cluster swept + wick + reclaim/reject + fib + EMA stretch
      Continuation: cluster ahead as magnet + momentum aligned

    Requirements for reversal (primary):
      1. Liquidation cluster was recently swept (sweep_completed)
      2. Large wick on sweep candle (ratio >= 35%)
      3. Reclaim (long) or rejection (short) confirmed
      4. Price at fib band or EMA/VWAP stretch
      5. Minimum 4 of 6 core signals present

    Requirements for continuation (secondary):
      1. Strong cluster ahead (magnet pull)
      2. Momentum aligned toward cluster (ADX > 25, EMA slope)
      3. No sweep yet -- trade toward the cluster
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 20:
        return None

    intel = liquidation_intel or {}
    sweep_status = str(intel.get("sweep_status", "none"))
    sweep_side = str(intel.get("sweep_side", ""))
    magnet_side = str(intel.get("magnet_side", "balanced"))
    magnet_score = float(intel.get("magnet_score", 0))
    wick_score_val = float(intel.get("wick_score", 0))
    wick_ratio = float(intel.get("wick_ratio", 0))
    reclaim = bool(intel.get("reclaim_confirmed", False))
    rejection = bool(intel.get("rejection_confirmed", False))
    cluster_strength = float(intel.get("cluster_strength", 0))
    funding_lean = str(intel.get("funding_lean", "neutral"))

    d = direction.lower().strip()

    # Check fib zone confluence
    fib_hit = False
    if fibs:
        conf = compute_confluences(price, df_1h, df_1h, df_15m, levels, fibs, d)
        fib_hit = bool(conf.get("FIB_ZONE"))

    # Check EMA/VWAP stretch
    ema_stretched = False
    try:
        e21 = ema(df_15m["close"], 21)
        e21_val = float(e21.iloc[-1])
        atr_val = float(atr(df_15m, 14).iloc[-1])
        if atr_val > 0 and e21_val > 0:
            distance_from_ema = abs(price - e21_val)
            ema_stretched = distance_from_ema > atr_val
    except Exception:
        pass

    # Check volume spike
    vol_spike = False
    if "volume" in df_15m.columns and len(df_15m) >= 20:
        vol_avg = float(df_15m["volume"].rolling(20).mean().iloc[-1])
        vol_now = float(df_15m["volume"].iloc[-1])
        vol_spike = vol_avg > 0 and vol_now > vol_avg * 1.5

    # Funding confirmation: crowd on wrong side
    funding_confirms = False
    if d == "long" and funding_lean == "long":
        funding_confirms = True  # crowd was long, got flushed, now reversal
    elif d == "short" and funding_lean == "short":
        funding_confirms = True  # crowd was short, got squeezed, now reversal

    # -- REVERSAL MODE --
    if sweep_status == "completed":
        # Direction check: sweep of longs below = long reversal, sweep of shorts above = short reversal
        if d == "long" and sweep_side != "long":
            pass  # wrong side for long reversal
        elif d == "short" and sweep_side != "short":
            pass  # wrong side for short reversal
        else:
            # Count core signals
            core_signals = 0
            if cluster_strength >= 30:
                core_signals += 1
            if fib_hit:
                core_signals += 1
            if ema_stretched:
                core_signals += 1
            if wick_ratio >= 0.35:
                core_signals += 1
            if reclaim or rejection:
                core_signals += 1

            if core_signals >= 3:  # relaxed from 4 since not all data always available
                return {
                    "type": "liquidity_sweep",
                    "mode": "reversal",
                    "confluence": {
                        "SWEEP_COMPLETED": True,
                        "CLUSTER_STRONG": cluster_strength >= 30,
                        "FIB_BAND_TAG": fib_hit,
                        "EMA_VWAP_STRETCH": ema_stretched,
                        "LARGE_WICK": wick_ratio >= 0.35,
                        "RECLAIM_REJECT": reclaim or rejection,
                        "FUNDING_CONFIRMS": funding_confirms,
                        "VOLUME_SPIKE": vol_spike,
                    },
                    "core_signals": core_signals,
                    "wick_score": wick_score_val,
                    "wick_ratio": round(wick_ratio, 4),
                    "sweep_side": sweep_side,
                    "cluster_strength": cluster_strength,
                    "magnet_score": magnet_score,
                }

    # -- CONTINUATION MODE --
    # Trade toward a strong cluster that has not been swept yet
    if sweep_status == "none" and magnet_score >= 40:
        # Direction must align with magnet
        if d == "long" and magnet_side == "above":
            pass  # good: trading long toward cluster above
        elif d == "short" and magnet_side == "below":
            pass  # good: trading short toward cluster below
        else:
            return None

        # Need momentum alignment
        momentum_ok = False
        try:
            e21 = ema(df_15m["close"], 21)
            slope = float(e21.diff().tail(3).mean())
            if d == "long" and slope > 0:
                momentum_ok = True
            elif d == "short" and slope < 0:
                momentum_ok = True
        except Exception:
            pass

        if momentum_ok:
            return {
                "type": "liquidity_sweep",
                "mode": "continuation",
                "confluence": {
                    "MAGNET_STRONG": True,
                    "MOMENTUM_ALIGNED": True,
                    "DIRECTION_MATCHES_MAGNET": True,
                    "FUNDING_CONFIRMS": funding_confirms,
                    "VOLUME_SPIKE": vol_spike,
                },
                "core_signals": 3,
                "magnet_side": magnet_side,
                "magnet_score": magnet_score,
                "cluster_strength": cluster_strength,
            }

    return None


# ---------------------------------------------------------------------------
# Exhaustion Warning Block (blocking lane -- prevents entries)
# ---------------------------------------------------------------------------

def exhaustion_warning_block(
    df_15m: pd.DataFrame,
    direction: str,
    expansion_state: dict,
) -> bool:
    """Exhaustion Warning Block -- returns True to BLOCK late entries.

    Detects parabolic acceleration + indicator saturation. Prevents
    entering moves that are about to reverse.

    Blocks when 3 of 4 conditions are true:
        1. 3+ consecutive candles with expanding body (acceleration)
        2. RSI in deep extreme (>75 for longs, <25 for shorts)
        3. Volume declining while price still extending (divergence)
        4. ATR shock detected (> 2x normal)
    """
    if df_15m is None or df_15m.empty or len(df_15m) < 15:
        return False

    warnings = 0

    # 1. Body acceleration: 3+ consecutive expanding-body candles in direction
    try:
        bodies = []
        for i in range(-4, 0):
            row = df_15m.iloc[i]
            b = abs(float(row["close"]) - float(row["open"]))
            bodies.append(b)

        expanding = 0
        for i in range(1, len(bodies)):
            if bodies[i] > bodies[i - 1] * 1.05:  # each bar bigger than last
                expanding += 1
        if expanding >= 2:  # 3 of 4 bars expanding
            # Also check direction matches
            if direction == "long":
                all_bullish = all(
                    float(df_15m.iloc[j]["close"]) > float(df_15m.iloc[j]["open"])
                    for j in range(-3, 0)
                )
                if all_bullish:
                    warnings += 1
            else:
                all_bearish = all(
                    float(df_15m.iloc[j]["close"]) < float(df_15m.iloc[j]["open"])
                    for j in range(-3, 0)
                )
                if all_bearish:
                    warnings += 1
    except Exception:
        pass

    # 2. RSI in deep extreme
    try:
        r = rsi(df_15m["close"], 14)
        if not pd.isna(r.iloc[-1]):
            rsi_val = float(r.iloc[-1])
            if direction == "long" and rsi_val > 75:
                warnings += 1
            if direction == "short" and rsi_val < 25:
                warnings += 1
    except Exception:
        pass

    # 3. Volume divergence: price extending but volume declining
    try:
        vols = [float(df_15m["volume"].iloc[i]) for i in range(-4, 0)]
        closes = [float(df_15m["close"].iloc[i]) for i in range(-4, 0)]
        vol_declining = vols[-1] < vols[0] * 0.8  # latest vol < 80% of 4 bars ago
        if direction == "long":
            price_rising = closes[-1] > closes[0]
        else:
            price_rising = closes[-1] < closes[0]  # "rising" in short = price falling
        if vol_declining and price_rising:
            warnings += 1
    except Exception:
        pass

    # 4. ATR shock (> 2x normal)
    try:
        atr_series = atr(df_15m, 14)
        if len(atr_series) >= 20 and not pd.isna(atr_series.iloc[-1]):
            atr_now = float(atr_series.iloc[-1])
            atr_mean = float(atr_series.iloc[-20:].mean())
            if atr_mean > 0 and atr_now > 2.0 * atr_mean:
                warnings += 1
    except Exception:
        pass

    return warnings >= 3
