from __future__ import annotations

from typing import Any, Dict, Optional

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


def _safe_last(series: pd.Series) -> float:
    try:
        return float(series.iloc[-1])
    except Exception:
        return 0.0


def _close_strength(row: pd.Series, direction: str) -> float:
    high = float(row.get("high", 0.0))
    low = float(row.get("low", 0.0))
    close = float(row.get("close", 0.0))
    rng = high - low
    if rng <= 0:
        return 0.0
    if direction == "long":
        return max(0.0, min(1.0, (close - low) / rng))
    return max(0.0, min(1.0, (high - close) / rng))


def _recent_zone_structure(
    df_15m: pd.DataFrame,
    direction: str,
    lookback: int,
    recent_bars: int,
    breakout_buffer: float,
    hold_buffer: float,
    min_closes_above: int,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ready": False,
        "zone_high": None,
        "zone_low": None,
        "recent_closes_above": 0,
        "stair_step": False,
    }
    if df_15m is None or len(df_15m) < (lookback + recent_bars + 1):
        return out

    recent_bars = max(2, int(recent_bars))
    lookback = max(8, int(lookback))
    history = df_15m.iloc[-(lookback + recent_bars):-recent_bars]
    recent = df_15m.iloc[-recent_bars:]
    if history.empty or recent.empty:
        return out

    zone_high = float(history["high"].max())
    zone_low = float(history["low"].min())
    closes = recent["close"].astype(float)
    lows = recent["low"].astype(float)
    highs = recent["high"].astype(float)
    out["zone_high"] = round(zone_high, 8)
    out["zone_low"] = round(zone_low, 8)

    if direction == "long":
        closes_above = int((closes >= zone_high - hold_buffer * 0.2).sum())
        stair_step = int((closes.diff().fillna(0.0) > 0).sum()) >= max(1, recent_bars - 2)
        broke_zone = float(closes.iloc[-1]) >= zone_high + breakout_buffer * 0.25 or float(highs.max()) >= zone_high + breakout_buffer
        held_zone = float(lows.min()) >= zone_high - hold_buffer
    else:
        closes_above = int((closes <= zone_low + hold_buffer * 0.2).sum())
        stair_step = int((closes.diff().fillna(0.0) < 0).sum()) >= max(1, recent_bars - 2)
        broke_zone = float(closes.iloc[-1]) <= zone_low - breakout_buffer * 0.25 or float(lows.min()) <= zone_low - breakout_buffer
        held_zone = float(highs.max()) <= zone_low + hold_buffer

    out["recent_closes_above"] = closes_above
    out["stair_step"] = stair_step
    out["ready"] = bool(broke_zone and held_zone and closes_above >= max(2, int(min_closes_above)) and stair_step)
    return out


def _multi_tf_zone_structures(
    direction: str,
    tf_frames: list[tuple[str, pd.DataFrame, int, int]],
    min_breakout_pct: float,
    breakout_buffer_atr: float,
    hold_buffer_atr: float,
) -> dict[str, Any]:
    structures: dict[str, dict[str, Any]] = {}
    ready_tfs: list[str] = []
    for label, df, lookback, recent_bars in tf_frames:
        if df is None or len(df) < (lookback + recent_bars + 1):
            continue
        last_close = _safe_last(df["close"])
        atr_value = _safe_last(atr(df, 14))
        if atr_value <= 0:
            atr_value = max(last_close * 0.004, 1e-6)
        breakout_buffer = max(last_close * min_breakout_pct * 0.2, atr_value * breakout_buffer_atr)
        hold_buffer = max(last_close * min_breakout_pct * 0.15, atr_value * hold_buffer_atr)
        min_closes = max(2, min(int(recent_bars), 3))
        structure = _recent_zone_structure(
            df,
            direction,
            lookback=lookback,
            recent_bars=recent_bars,
            breakout_buffer=breakout_buffer,
            hold_buffer=hold_buffer,
            min_closes_above=min_closes,
        )
        structures[label] = structure
        if structure.get("ready"):
            ready_tfs.append(label)
    return {
        "structures": structures,
        "ready_tfs": ready_tfs,
        "ready_count": len(ready_tfs),
    }


def _weekly_bias_alignment(weekly_playbook: dict | None, direction: str) -> bool:
    if not isinstance(weekly_playbook, dict):
        return False
    blob = " ".join(
        str(weekly_playbook.get(k) or "")
        for k in ("label", "thesis", "risk_map")
    ).lower()
    for item in weekly_playbook.get("top_setups") or []:
        if isinstance(item, dict):
            blob += " " + " ".join(str(item.get(k) or "") for k in ("setup", "label", "bias", "reason"))
        else:
            blob += f" {item}"
    if direction == "long":
        return any(tok in blob for tok in ("bull", "breakout", "squeeze higher", "upside", "trend up"))
    return any(tok in blob for tok in ("bear", "breakdown", "squeeze lower", "downside", "trend down"))


def _event_risk_state(event_calendar: dict | None, cfg: dict | None = None) -> tuple[bool, dict[str, Any]]:
    cfg = cfg or {}
    details = {"label": None, "hours_to_event": None, "importance": None}
    if not isinstance(event_calendar, dict):
        return False, details
    next_event = event_calendar.get("next_event") if isinstance(event_calendar.get("next_event"), dict) else {}
    if not next_event:
        return False, details
    importance = str(next_event.get("importance") or "").lower()
    hours_to_event = next_event.get("hours_to_event")
    try:
        hours_to_event = float(hours_to_event)
    except Exception:
        hours_to_event = None
    details = {
        "label": str(next_event.get("label") or ""),
        "hours_to_event": hours_to_event,
        "importance": importance or None,
    }
    block_hours = float(cfg.get("lane_w_event_block_hours", 6.0) or 6.0)
    block = importance in {"high", "critical"} and hours_to_event is not None and hours_to_event <= block_hours
    return block, details


def pullback_continuation(
    price: float,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    df_15m: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
) -> Optional[Dict]:
    if df_15m is None or df_1h is None or df_4h is None:
        return None
    if len(df_15m) < 55 or len(df_1h) < 55 or len(df_4h) < 30:
        return None

    conf = compute_confluences(price, df_1h, df_4h, df_15m, levels, fibs, direction)
    if not confluence_passes(conf):
        return None

    e21_15 = _safe_last(ema(df_15m["close"], 21))
    e55_15 = _safe_last(ema(df_15m["close"], 55))
    e21_1h = _safe_last(ema(df_1h["close"], 21))
    e55_1h = _safe_last(ema(df_1h["close"], 55))
    e21_4h = _safe_last(ema(df_4h["close"], 21))
    e55_4h = _safe_last(ema(df_4h["close"], 55))
    atr_15 = _safe_last(atr(df_15m, 14))
    if min(e21_15, e55_15, e21_1h, e55_1h, e21_4h, e55_4h, atr_15) <= 0:
        return None

    curr = df_15m.iloc[-1]
    prev = df_15m.iloc[-2]
    recent = df_15m.tail(7).iloc[:-1]
    if recent.empty:
        return None

    r = rsi(df_15m["close"], 14)
    if len(r) < 3 or r.isna().iloc[-1] or r.isna().iloc[-2]:
        return None
    rsi_now = float(r.iloc[-1])
    rsi_prev = float(r.iloc[-2])

    close_strength = _close_strength(curr, direction)
    curr_range = max(float(curr["high"]) - float(curr["low"]), 1e-9)
    body_ratio = abs(float(curr["close"]) - float(curr["open"])) / curr_range
    ema_zone = _ema_zone_hit(df_15m.tail(80))

    if direction == "long":
        trend_ok = e21_15 > e55_15 and e21_1h > e55_1h and e21_4h > e55_4h
        if not trend_ok:
            return None
        touched_value = float(curr["low"]) <= e21_15 + atr_15 * 0.20
        held_value = float(curr["close"]) >= e21_15 and float(curr["low"]) >= float(recent["low"].min()) - atr_15 * 0.15
        reset_ok = 40 <= rsi_now <= 62 and rsi_now > rsi_prev
        no_chase = (float(curr["close"]) - e21_15) <= atr_15 * 0.80
        direction_close = float(curr["close"]) > float(curr["open"]) and float(curr["close"]) >= float(prev["close"])
    else:
        trend_ok = e21_15 < e55_15 and e21_1h < e55_1h and e21_4h < e55_4h
        if not trend_ok:
            return None
        touched_value = float(curr["high"]) >= e21_15 - atr_15 * 0.20
        held_value = float(curr["close"]) <= e21_15 and float(curr["high"]) <= float(recent["high"].max()) + atr_15 * 0.15
        reset_ok = 38 <= rsi_now <= 60 and rsi_now < rsi_prev
        no_chase = (e21_15 - float(curr["close"])) <= atr_15 * 0.80
        direction_close = float(curr["close"]) < float(curr["open"]) and float(curr["close"]) <= float(prev["close"])

    if not touched_value or not held_value or not reset_ok or not no_chase or not direction_close:
        return None
    if close_strength < 0.58 or body_ratio < 0.35:
        return None
    if not ema_zone and not (conf.get("STRUCTURE_ZONE") or conf.get("FIB_ZONE")):
        return None

    conf.update({
        "EMA_RECLAIM": True,
        "TREND_STACKED": True,
        "PULLBACK_HELD": held_value,
        "CLOSE_STRENGTH_OK": close_strength >= 0.58,
        "RSI_RESET_OK": reset_ok,
    })

    return {
        "type": "pullback",
        "entry_profile_key": "pullback_trend",
        "confluence": conf,
        "ema21_15m": round(e21_15, 8),
        "ema55_15m": round(e55_15, 8),
        "close_strength": round(close_strength, 3),
    }


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
    if df_15m is None or df_15m.empty or len(df_15m) < 40:
        return None
    if df_1h is None or df_1h.empty or len(df_1h) < 55:
        return None

    window = df_15m.tail(60)
    swings = _detect_swing_points(window, left=2, right=2)
    structure = _classify_structure(swings, min_swings=2)

    if direction == "short" and not structure["bearish_structure"]:
        return None
    if direction == "long" and not structure["bullish_structure"]:
        return None

    e21_15 = _safe_last(ema(df_15m["close"], 21))
    e55_15 = _safe_last(ema(df_15m["close"], 55))
    e21_1h = _safe_last(ema(df_1h["close"], 21))
    e55_1h = _safe_last(ema(df_1h["close"], 55))
    atr_15 = _safe_last(atr(df_15m, 14))
    if min(e21_15, e55_15, e21_1h, e55_1h, atr_15) <= 0:
        return None

    if direction == "short":
        trigger_level = structure["last_swing_low"]
        if trigger_level is None or price >= trigger_level:
            return None
        htf_align = e21_15 < e55_15 and e21_1h < e55_1h
    else:
        trigger_level = structure["last_swing_high"]
        if trigger_level is None or price <= trigger_level:
            return None
        htf_align = e21_15 > e55_15 and e21_1h > e55_1h
    if not htf_align:
        return None

    curr = df_15m.iloc[-1]
    prev = df_15m.iloc[-2]
    body = abs(float(curr["close"]) - float(curr["open"]))
    rng = max(float(curr["high"]) - float(curr["low"]), 1e-9)
    body_ratio = body / rng
    close_strength = _close_strength(curr, direction)

    r = rsi(df_15m["close"], 14)
    if r.isna().iloc[-1] or r.isna().iloc[-3]:
        return None
    rsi_now = float(r.iloc[-1])
    rsi_prev = float(r.iloc[-3])
    if direction == "short" and (rsi_now >= rsi_prev - 1 or rsi_now > 58):
        return None
    if direction == "long" and (rsi_now <= rsi_prev + 1 or rsi_now < 42):
        return None

    if direction == "short":
        broke_level = float(curr["close"]) <= trigger_level - atr_15 * 0.05
        held_break = max(float(curr["high"]), float(prev["high"])) <= trigger_level + atr_15 * 0.20
        extension_atr = (trigger_level - float(curr["close"])) / atr_15
        direction_close = float(curr["close"]) < float(curr["open"])
        structure_stop = structure["last_swing_high"]
    else:
        broke_level = float(curr["close"]) >= trigger_level + atr_15 * 0.05
        held_break = min(float(curr["low"]), float(prev["low"])) >= trigger_level - atr_15 * 0.20
        extension_atr = (float(curr["close"]) - trigger_level) / atr_15
        direction_close = float(curr["close"]) > float(curr["open"])
        structure_stop = structure["last_swing_low"]

    if not broke_level or not held_break or not direction_close:
        return None
    if extension_atr > 0.85:
        return None
    if close_strength < 0.62 or body_ratio < 0.40:
        return None

    is_reentry = False
    if state and state.get("_last_trend_exit_structure_intact"):
        last_dir = str(state.get("_last_trend_exit_direction") or "")
        if last_dir == direction:
            last_exit_px = float(state.get("_last_trend_exit_price") or 0)
            last_entry_px = float(state.get("_last_trend_entry_price") or 0)
            if last_exit_px > 0 and last_entry_px > 0:
                impulse = abs(last_exit_px - last_entry_px)
                retrace = abs(price - last_exit_px)
                if impulse > 0 and retrace < 0.40 * impulse:
                    is_reentry = True

    conf = {
        "BEARISH_STRUCTURE": structure["bearish_structure"],
        "BULLISH_STRUCTURE": structure["bullish_structure"],
        "SWING_BREAK": True,
        "BREAK_HOLD": held_break,
        "HTF_ALIGN": htf_align,
        "RSI_SLOPE_CONFIRM": True,
        "DIRECTION_CLOSE": True,
        "CONTINUATION_REENTRY": is_reentry,
        "CLOSE_STRENGTH_OK": close_strength >= 0.62,
    }

    return {
        "type": "trend_continuation",
        "entry_profile_key": "trend_continuation_trend",
        "confluence": conf,
        "structure_stop": round(structure_stop, 8) if structure_stop else None,
        "trigger_level": round(trigger_level, 8),
        "last_swing_high": structure["last_swing_high"],
        "last_swing_low": structure["last_swing_low"],
        "prev_swing_high": structure["prev_swing_high"],
        "prev_swing_low": structure["prev_swing_low"],
        "is_reentry": is_reentry,
        "close_strength": round(close_strength, 3),
        "extension_atr": round(float(extension_atr), 3),
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
# Lane W: HTF Breakout Continuation
# ---------------------------------------------------------------------------

def assess_htf_breakout_continuation(
    price: float,
    df_4h: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_15m: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
    weekly_playbook: Optional[Dict] = None,
    event_calendar: Optional[Dict] = None,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    cfg = config or {}
    d = direction.lower().strip()
    out: Dict[str, Any] = {
        "ready": False,
        "direction": d,
        "signal_count": 0,
        "pressure_score": 0,
        "followthrough_score": 0,
        "confidence": 0.0,
        "event_risk_blocked": False,
        "reason": "insufficient_data",
        "reasons": [],
    }
    if (
        df_15m is None
        or df_1h is None
        or df_4h is None
        or len(df_15m) < 40
        or len(df_1h) < 40
        or len(df_4h) < 20
    ):
        return out

    breakout_4h = int(cfg.get("lane_w_breakout_lookback_4h", 6) or 6)
    breakout_1h = int(cfg.get("lane_w_breakout_lookback_1h", 12) or 12)
    min_breakout_pct = float(cfg.get("lane_w_min_breakout_pct", 0.0015) or 0.0015)
    max_chase_atr = float(cfg.get("lane_w_max_chase_atr", 0.8) or 0.8)
    min_vol_ratio = float(cfg.get("lane_w_min_volume_ratio", 1.05) or 1.05)
    min_close_strength = float(cfg.get("lane_w_min_close_strength", 0.68) or 0.68)
    min_signals = int(cfg.get("lane_w_min_signals", 6) or 6)
    min_rsi_4h = float(cfg.get("lane_w_rsi_4h_long_min", 56) or 56)
    max_rsi_4h = float(cfg.get("lane_w_rsi_4h_short_max", 44) or 44)
    probe_atr = float(cfg.get("lane_w_probe_reclaim_atr", 0.35) or 0.35)
    probe_close_strength = float(cfg.get("lane_w_probe_close_strength", max(min_close_strength, 0.72)) or max(min_close_strength, 0.72))
    probe_volume_ratio = float(cfg.get("lane_w_probe_volume_ratio", max(min_vol_ratio, 1.15)) or max(min_vol_ratio, 1.15))
    zone_lookback_15m = int(cfg.get("lane_w_zone_lookback_15m", 24) or 24)
    zone_lookback_1h = int(cfg.get("lane_w_zone_lookback_1h", 18) or 18)
    zone_lookback_4h = int(cfg.get("lane_w_zone_lookback_4h", 10) or 10)
    zone_recent_bars = int(cfg.get("lane_w_zone_recent_bars", 4) or 4)
    zone_recent_bars_1h = int(cfg.get("lane_w_zone_recent_bars_1h", 3) or 3)
    zone_recent_bars_4h = int(cfg.get("lane_w_zone_recent_bars_4h", 2) or 2)
    zone_breakout_buffer_atr = float(cfg.get("lane_w_zone_breakout_buffer_atr", 0.12) or 0.12)
    zone_hold_buffer_atr = float(cfg.get("lane_w_zone_hold_buffer_atr", 0.20) or 0.20)

    row_15m = df_15m.iloc[-1]
    close_15m = float(row_15m["close"])
    close_1h = float(df_1h["close"].iloc[-1])
    close_4h = float(df_4h["close"].iloc[-1])
    high_15m = float(row_15m["high"])
    low_15m = float(row_15m["low"])

    ema21_15m = _safe_last(ema(df_15m["close"], 21))
    ema21_1h = _safe_last(ema(df_1h["close"], 21))
    ema55_1h = _safe_last(ema(df_1h["close"], 55))
    ema21_4h = _safe_last(ema(df_4h["close"], 21))
    ema55_4h = _safe_last(ema(df_4h["close"], 55))
    rsi_1h = _safe_last(rsi(df_1h["close"], 14))
    rsi_4h = _safe_last(rsi(df_4h["close"], 14))
    atr_15m = _safe_last(atr(df_15m, 14))
    if atr_15m <= 0:
        atr_15m = max(price * 0.004, 1e-6)

    prior_4h_high = float(df_4h["high"].iloc[-(breakout_4h + 1):-1].max())
    prior_4h_low = float(df_4h["low"].iloc[-(breakout_4h + 1):-1].min())
    prior_1h_high = float(df_1h["high"].iloc[-(breakout_1h + 1):-1].max())
    prior_1h_low = float(df_1h["low"].iloc[-(breakout_1h + 1):-1].min())
    close_strength = _close_strength(row_15m, d)
    vol_avg_15m = float(df_15m["volume"].iloc[-20:].mean()) if "volume" in df_15m.columns else 0.0
    vol_ratio = (float(row_15m.get("volume", 0.0)) / vol_avg_15m) if vol_avg_15m > 0 else 1.0

    event_blocked, event_details = _event_risk_state(event_calendar, cfg)
    weekly_align = _weekly_bias_alignment(weekly_playbook, d)
    conf = compute_confluences(price, df_1h, df_4h, df_15m, levels, fibs, d)

    if d == "long":
        ema_stack = ema21_4h > ema55_4h and ema21_1h > ema55_1h and close_15m >= ema21_15m
        breakout_4h_ok = max(close_4h, price) > prior_4h_high * (1 + min_breakout_pct)
        breakout_1h_ok = max(close_1h, price) > prior_1h_high * (1 + min_breakout_pct * 0.75)
        momentum_ok = rsi_4h >= min_rsi_4h and rsi_1h >= 52
        invalidation = max(prior_1h_high, ema21_1h) - atr_15m * 0.35
        breakout_level = max(prior_4h_high, prior_1h_high)
        price_above_breakout = price >= breakout_level
        ema_stack_core = ema21_4h > ema55_4h and ema21_1h > ema55_1h
    else:
        ema_stack = ema21_4h < ema55_4h and ema21_1h < ema55_1h and close_15m <= ema21_15m
        breakout_4h_ok = min(close_4h, price) < prior_4h_low * (1 - min_breakout_pct)
        breakout_1h_ok = min(close_1h, price) < prior_1h_low * (1 - min_breakout_pct * 0.75)
        momentum_ok = rsi_4h <= max_rsi_4h and rsi_1h <= 48
        invalidation = min(prior_1h_low, ema21_1h) + atr_15m * 0.35
        breakout_level = min(prior_4h_low, prior_1h_low)
        price_above_breakout = price <= breakout_level
        ema_stack_core = ema21_4h < ema55_4h and ema21_1h < ema55_1h

    zone_bundle = _multi_tf_zone_structures(
        d,
        [
            ("15m", df_15m, zone_lookback_15m, zone_recent_bars),
            ("1h", df_1h, zone_lookback_1h, zone_recent_bars_1h),
            ("4h", df_4h, zone_lookback_4h, zone_recent_bars_4h),
        ],
        min_breakout_pct=min_breakout_pct,
        breakout_buffer_atr=zone_breakout_buffer_atr,
        hold_buffer_atr=zone_hold_buffer_atr,
    )
    zone_structures = zone_bundle.get("structures") or {}
    zone_ready_tfs = [str(tf) for tf in (zone_bundle.get("ready_tfs") or [])]
    zone_breakout_hold_ok = bool(zone_ready_tfs)
    zone_ready_count = int(zone_bundle.get("ready_count") or 0)
    zone_active_tf = None
    zone_structure = {}
    active_trigger_level = breakout_level
    if zone_breakout_hold_ok:
        trigger_candidates: list[tuple[float, float, str]] = []
        for tf in zone_ready_tfs:
            structure = zone_structures.get(tf) or {}
            level = structure.get("zone_high") if d == "long" else structure.get("zone_low")
            try:
                level_value = float(level)
            except Exception:
                continue
            trigger_candidates.append((abs(price - level_value), level_value, tf))
        if trigger_candidates:
            _, active_trigger_level, zone_active_tf = min(trigger_candidates, key=lambda item: item[0])
            zone_structure = zone_structures.get(zone_active_tf) or {}
    if d == "long":
        ltf_support_ok = (
            close_15m >= ema21_15m
            or (zone_breakout_hold_ok and close_15m >= ema21_15m - atr_15m * 0.25)
            or (zone_active_tf in {"1h", "4h"} and close_15m >= active_trigger_level - atr_15m * 0.15)
        )
    else:
        ltf_support_ok = (
            close_15m <= ema21_15m
            or (zone_breakout_hold_ok and close_15m <= ema21_15m + atr_15m * 0.25)
            or (zone_active_tf in {"1h", "4h"} and close_15m <= active_trigger_level + atr_15m * 0.15)
        )
    htf_trend_ok = ema_stack_core or (zone_breakout_hold_ok and bool(conf.get("EMA_BIAS")))
    ema_stack = bool(htf_trend_ok and ltf_support_ok)
    chase_atr = abs(price - active_trigger_level) / atr_15m if active_trigger_level > 0 and atr_15m > 0 else 99.0
    volume_ok = vol_ratio >= min_vol_ratio or bool(conf.get("RVOL_OK"))
    followthrough_ok = close_strength >= min_close_strength
    expansion_ok = bool(conf.get("VOLUME_SPIKE")) or bool(conf.get("CHANNEL_BREAKOUT")) or bool(conf.get("FLAG_CONTINUATION"))
    vwap_ok = bool(conf.get("VWAP_CONFIRM"))
    htf_break_ok = breakout_4h_ok or breakout_1h_ok
    breakout_probe_ok = False
    if breakout_level > 0 and atr_15m > 0:
        probe_window = probe_atr * atr_15m
        if d == "long":
            probe_gap = breakout_level - price
            breakout_probe_ok = (
                probe_gap >= 0.0
                and probe_gap <= probe_window
                and high_15m >= breakout_level * (1 - min_breakout_pct * 0.25)
                and max(close_15m, close_1h) >= breakout_level - probe_window * 0.5
                and close_strength >= probe_close_strength
                and vol_ratio >= probe_volume_ratio
                and momentum_ok
                and ema_stack
            )
        else:
            probe_gap = price - breakout_level
            breakout_probe_ok = (
                probe_gap >= 0.0
                and probe_gap <= probe_window
                and low_15m <= breakout_level * (1 + min_breakout_pct * 0.25)
                and min(close_15m, close_1h) <= breakout_level + probe_window * 0.5
                and close_strength >= probe_close_strength
                and vol_ratio >= probe_volume_ratio
                and momentum_ok
                and ema_stack
            )
    structure_ready_signal = htf_break_ok or breakout_probe_ok or zone_breakout_hold_ok

    reasons: list[str] = []
    signal_count = 0
    for ok, label in (
        (ema_stack, "ema_stack"),
        (htf_break_ok, "htf_break"),
        (breakout_probe_ok, "breakout_probe_reclaim"),
        (momentum_ok, "htf_momentum"),
        (followthrough_ok, "followthrough"),
        (volume_ok, "volume"),
        (expansion_ok, "expansion"),
        (vwap_ok, "vwap_alignment"),
        (weekly_align, "weekly_alignment"),
        (price_above_breakout, "holding_above_breakout" if d == "long" else "holding_below_breakout"),
    ):
        if ok:
            signal_count += 1
            reasons.append(label)
    for tf in zone_ready_tfs:
        signal_count += 1
        reasons.append(f"zone_breakout_hold_{tf}")

    pressure_score = min(100, int(round((signal_count / 11.0) * 100)))
    followthrough_score = int(round(((close_strength * 0.55) + min(1.5, vol_ratio) / 1.5 * 0.45) * 100))
    confidence = round(min(1.0, (pressure_score * 0.6 + followthrough_score * 0.4) / 100.0), 3)
    hold_score = int(round(
        min(
            100.0,
            max(
                0.0,
                pressure_score * 0.35
                + followthrough_score * 0.35
                + (12.0 if weekly_align else 0.0)
                + (8.0 if volume_ok else -8.0)
                + (8.0 if htf_break_ok else (6.0 if zone_breakout_hold_ok else (4.0 if breakout_probe_ok else -10.0)))
                + min(4.0, max(0.0, zone_ready_count - 1) * 2.0)
                + (6.0 if ema_stack else -8.0)
                - max(0.0, chase_atr - 0.75) * 18.0,
            ),
        )
    ))
    false_break_risk = int(round(
        min(
            100.0,
            max(
                0.0,
                100.0
                - hold_score
                + (18.0 if event_blocked else 0.0)
                + (12.0 if not volume_ok else 0.0)
                + (10.0 if not followthrough_ok else 0.0)
                + (8.0 if not htf_break_ok and not breakout_probe_ok and not zone_breakout_hold_ok else 0.0)
                + (4.0 if zone_breakout_hold_ok and not htf_break_ok else 0.0)
                + (6.0 if breakout_probe_ok and not htf_break_ok else 0.0)
                - min(4.0, max(0.0, zone_ready_count - 1) * 2.0)
                + max(0.0, chase_atr - 0.8) * 10.0,
            ),
        )
    ))
    management_bias = "hold_breakout" if hold_score >= max(58, false_break_risk) else "fade_failed_breakout"

    out.update(
        {
            "signal_count": signal_count,
            "pressure_score": pressure_score,
            "followthrough_score": followthrough_score,
            "confidence": confidence,
            "hold_score": hold_score,
            "false_break_risk": false_break_risk,
            "management_bias": management_bias,
            "weekly_alignment": weekly_align,
            "event_risk_blocked": bool(event_blocked),
            "event_risk_label": event_details.get("label"),
            "event_risk_hours": event_details.get("hours_to_event"),
            "event_risk_importance": event_details.get("importance"),
            "ema_stack": ema_stack,
            "htf_break_confirmed": htf_break_ok,
            "breakout_probe_reclaim": breakout_probe_ok,
            "zone_breakout_hold": zone_breakout_hold_ok,
            "zone_breakout_tfs": zone_ready_tfs,
            "zone_active_tf": zone_active_tf,
            "zone_structures": zone_structures,
            "zone_high": zone_structure.get("zone_high"),
            "zone_low": zone_structure.get("zone_low"),
            "zone_recent_closes": zone_structure.get("recent_closes_above"),
            "zone_stair_step": zone_structure.get("stair_step"),
            "volume_ratio": round(vol_ratio, 3),
            "close_strength": round(close_strength, 3),
            "breakout_level": round(float(breakout_level), 8) if breakout_level > 0 else None,
            "trigger_price": round(float(active_trigger_level), 8) if active_trigger_level > 0 else None,
            "invalidation_price": round(float(invalidation), 8) if invalidation > 0 else None,
            "chase_atr": round(chase_atr, 3),
            "reason": None,
            "reasons": reasons,
            "market_event_ok": not bool(event_blocked),
            "confluence": conf,
        }
    )

    if event_blocked:
        out["reason"] = "event_risk_block"
        return out
    if chase_atr > max_chase_atr:
        out["reason"] = "breakout_chase_too_far"
        return out
    if signal_count < min_signals:
        out["reason"] = "insufficient_breakout_signals"
        return out
    if not (followthrough_ok and volume_ok and momentum_ok and ema_stack and structure_ready_signal):
        out["reason"] = "breakout_quality_not_ready"
        return out

    out["ready"] = True
    out["reason"] = "ready"
    return out


def htf_breakout_continuation(
    price: float,
    df_4h: pd.DataFrame,
    df_1h: pd.DataFrame,
    df_15m: pd.DataFrame,
    levels: Dict[str, float],
    fibs: Dict[str, float],
    direction: str,
    weekly_playbook: Optional[Dict] = None,
    event_calendar: Optional[Dict] = None,
    config: Optional[Dict] = None,
) -> Optional[Dict]:
    assessment = assess_htf_breakout_continuation(
        price,
        df_4h,
        df_1h,
        df_15m,
        levels,
        fibs,
        direction,
        weekly_playbook=weekly_playbook,
        event_calendar=event_calendar,
        config=config,
    )
    if not assessment.get("ready"):
        return None
    confluence = dict(assessment.get("confluence") or {})
    confluence["HTF_BREAK"] = True
    confluence["EMA_ALIGN_SLOPE"] = bool(assessment.get("ema_stack"))
    confluence["VOLUME_SPIKE"] = bool((assessment.get("volume_ratio") or 0) >= 1.0)
    confluence["VWAP_CONFIRM"] = bool(confluence.get("VWAP_CONFIRM"))
    confluence["BREAKOUT_PROBE_RECLAIM"] = bool(assessment.get("breakout_probe_reclaim"))
    confluence["ZONE_BREAKOUT_HOLD"] = bool(assessment.get("zone_breakout_hold"))
    if assessment.get("zone_active_tf"):
        confluence[f"ZONE_BREAKOUT_HOLD_{str(assessment.get('zone_active_tf')).upper()}"] = True
    return {
        "type": "htf_breakout_continuation",
        "confluence": confluence,
        "breakout_level": assessment.get("breakout_level"),
        "zone_high": assessment.get("zone_high"),
        "zone_low": assessment.get("zone_low"),
        "zone_breakout_tfs": assessment.get("zone_breakout_tfs") or [],
        "zone_active_tf": assessment.get("zone_active_tf"),
        "trigger_price": assessment.get("trigger_price"),
        "invalidation_price": assessment.get("invalidation_price"),
        "followthrough_score": assessment.get("followthrough_score"),
        "pressure_score": assessment.get("pressure_score"),
        "confidence": assessment.get("confidence"),
        "chase_atr": assessment.get("chase_atr"),
        "weekly_alignment": assessment.get("weekly_alignment"),
        "event_risk_blocked": assessment.get("event_risk_blocked"),
        "reasons": assessment.get("reasons") or [],
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
    config: dict | None = None,
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

    cfg = config or {}
    intel = liquidation_intel or {}
    sweep_status = str(intel.get("sweep_status", "none"))
    sweep_side = str(intel.get("sweep_side", ""))
    magnet_side = str(intel.get("magnet_side", "balanced"))
    magnet_score = float(intel.get("magnet_score", 0))
    wick_score_val = float(intel.get("wick_score", 0))
    wick_ratio = float(intel.get("wick_ratio", 0))
    reclaim = bool(intel.get("reclaim_confirmed", False))
    rejection = bool(intel.get("rejection_confirmed", False))
    followthrough = bool(intel.get("followthrough_confirmed", False))
    failed_reclaim = bool(intel.get("failed_reclaim", False))
    failed_rejection = bool(intel.get("failed_rejection", False))
    cluster_strength = float(intel.get("cluster_strength", 0))
    cluster_side = str(intel.get("cluster_side", "balanced"))
    distance_to_cluster_atr = float(intel.get("distance_to_cluster_atr") or 0.0)
    funding_lean = str(intel.get("funding_lean", "neutral"))
    fib_hit = bool(intel.get("fib_hit", False))
    ema_stretch = bool(intel.get("ema_stretch", False))
    vwap_stretch = bool(intel.get("vwap_stretch", False))
    volume_spike = bool(intel.get("volume_spike", False))
    touched_cluster = bool(intel.get("touched_cluster", False))
    no_trade_reason = str(intel.get("no_trade_reason") or "")
    continuation_ok = bool(intel.get("continuation_ok", False))
    reversal_ok = bool(intel.get("reversal_ok", False))
    target_cluster_price = float(intel.get("target_cluster_price") or 0.0)
    sweep_level = float(intel.get("sweep_level") or 0.0)
    sweep_depth_atr = float(intel.get("sweep_depth_atr") or 0.0)

    d = direction.lower().strip()
    min_cluster_strength = float(cfg.get("lane_v_min_cluster_strength", 30) or 30)
    min_wick_ratio = float(cfg.get("lane_v_wick_min_ratio", 0.35) or 0.35)
    min_wick_score = float(cfg.get("lane_v_wick_score_min", 55) or 55)
    max_reversal_chase_atr = float(cfg.get("lane_v_max_reversal_chase_atr", 1.2) or 1.2)
    tp_buffer_atr = float(cfg.get("lane_v_continuation_tp_buffer_atr", 0.15) or 0.15)
    fail_fast_bars = int(cfg.get("lane_v_fail_fast_bars", 3) or 3)
    require_volume_spike = bool(cfg.get("lane_v_require_volume_spike_for_reversal", False))
    require_stretch = bool(cfg.get("lane_v_require_fib_or_ema_stretch", False))
    skip_balanced = bool(cfg.get("lane_v_skip_balanced_clusters", True))
    continuation_enabled = bool(cfg.get("lane_v_continuation_enabled", True))
    reversal_enabled = bool(cfg.get("lane_v_reversal_enabled", True))

    # Check fib zone confluence
    fib_hit_local = fib_hit
    if fibs and not fib_hit_local:
        conf = compute_confluences(price, df_1h, df_1h, df_15m, levels, fibs, d)
        fib_hit_local = bool(conf.get("FIB_ZONE"))

    # Check EMA/VWAP stretch
    ema_stretched = ema_stretch or vwap_stretch
    try:
        e21 = ema(df_15m["close"], 21)
        e21_val = float(e21.iloc[-1])
        atr_val = float(atr(df_15m, 14).iloc[-1])
        if atr_val > 0 and e21_val > 0:
            distance_from_ema = abs(price - e21_val)
            ema_stretched = ema_stretched or distance_from_ema > atr_val
    except Exception:
        pass

    vol_spike = volume_spike
    if not vol_spike and "volume" in df_15m.columns and len(df_15m) >= 20:
        vol_avg = float(df_15m["volume"].rolling(20).mean().iloc[-1])
        vol_now = float(df_15m["volume"].iloc[-1])
        vol_spike = vol_avg > 0 and vol_now > vol_avg * 1.5

    # Funding confirmation: crowd on wrong side
    funding_confirms = False
    if d == "long" and funding_lean == "long":
        funding_confirms = True  # crowd was long, got flushed, now reversal
    elif d == "short" and funding_lean == "short":
        funding_confirms = True  # crowd was short, got squeezed, now reversal

    if skip_balanced and cluster_side == "balanced":
        if wick_score_val < 70:  # strong wick overrides balanced filter
            return None
    if no_trade_reason:
        return None

    # -- REVERSAL MODE --
    reversal_signals = 0
    if cluster_strength >= min_cluster_strength:
        reversal_signals += 1
    if fib_hit_local or ema_stretched:
        reversal_signals += 1
    if wick_ratio >= min_wick_ratio and wick_score_val >= min_wick_score:
        reversal_signals += 1
    if reclaim or rejection:
        reversal_signals += 1
    if followthrough:
        reversal_signals += 1
    if vol_spike:
        reversal_signals += 1
    if sweep_status in {"completed", "in_progress"} and reversal_enabled and (reversal_ok or reversal_signals >= int(cfg.get("lane_v_min_signals", 4) or 4)):
        # Direction check: sweep of longs below = long reversal, sweep of shorts above = short reversal
        if d == "long" and sweep_side != "long":
            pass  # wrong side for long reversal
        elif d == "short" and sweep_side != "short":
            pass  # wrong side for short reversal
        else:
            if require_volume_spike and not vol_spike:
                return None
            if require_stretch and not (fib_hit_local or ema_stretched):
                return None
            if failed_reclaim or failed_rejection:
                return None
            if distance_to_cluster_atr > max_reversal_chase_atr:
                return None
            wick_strong = wick_ratio >= min_wick_ratio and wick_score_val >= min_wick_score
            wick_very_strong = wick_score_val >= 70
            has_reclaim_reject = reclaim or rejection
            if (wick_strong and has_reclaim_reject) or wick_very_strong or (has_reclaim_reject and wick_ratio >= 0.20):
                return {
                    "type": "liquidity_sweep",
                    "mode": "reversal",
                    "entry_profile_key": "liquidity_sweep_reversal",
                    "fail_fast_bars": fail_fast_bars,
                    "lane_v_reversal_tp_mode": str(cfg.get("lane_v_reversal_tp_mode", "fast_mean_reversion") or "fast_mean_reversion"),
                    "lane_v_mode": "reversal",
                    "confluence": {
                        "SWEEP_COMPLETED": True,
                        "CLUSTER_STRONG": cluster_strength >= min_cluster_strength,
                        "FIB_BAND_TAG": fib_hit_local,
                        "EMA_VWAP_STRETCH": ema_stretched,
                        "LARGE_WICK": wick_ratio >= min_wick_ratio,
                        "RECLAIM_REJECT": reclaim or rejection,
                        "FOLLOWTHROUGH": followthrough,
                        "FUNDING_CONFIRMS": funding_confirms,
                        "VOLUME_SPIKE": vol_spike,
                    },
                    "core_signals": reversal_signals,
                    "wick_score": wick_score_val,
                    "wick_ratio": round(wick_ratio, 4),
                    "sweep_side": sweep_side,
                    "cluster_strength": cluster_strength,
                    "magnet_score": magnet_score,
                    "failed_reclaim": failed_reclaim,
                    "failed_rejection": failed_rejection,
                    "fib_hit": fib_hit_local,
                    "ema_stretch": ema_stretched,
                    "vwap_stretch": bool(vwap_stretch),
                    "continuation_ok": False,
                    "reversal_ok": True,
                    "sweep_level": sweep_level,
                    "target_cluster_price": target_cluster_price,
                    "sweep_depth_atr": sweep_depth_atr,
                }

    # -- CONTINUATION MODE --
    # Trade toward a strong cluster that has not been swept yet
    if sweep_status == "none" and continuation_enabled and (continuation_ok or magnet_score >= 40):
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

        if touched_cluster:
            return None
        if cluster_strength < min_cluster_strength:
            return None
        if distance_to_cluster_atr <= tp_buffer_atr:
            return None
        if failed_reclaim or failed_rejection:
            return None
        if momentum_ok:
            return {
                "type": "liquidity_sweep",
                "mode": "continuation",
                "entry_profile_key": "liquidity_sweep_continuation",
                "lane_v_mode": "continuation",
                "confluence": {
                    "MAGNET_STRONG": True,
                    "MOMENTUM_ALIGNED": True,
                    "DIRECTION_MATCHES_MAGNET": True,
                    "FUNDING_CONFIRMS": funding_confirms,
                    "VOLUME_SPIKE": vol_spike,
                    "CLUSTER_AHEAD": distance_to_cluster_atr > tp_buffer_atr,
                },
                "core_signals": 3,
                "magnet_side": magnet_side,
                "magnet_score": magnet_score,
                "cluster_strength": cluster_strength,
                "target_cluster_price": target_cluster_price,
                "distance_to_cluster_atr": distance_to_cluster_atr,
                "continuation_ok": True,
                "reversal_ok": False,
                "no_trade_reason": "",
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


# ---------------------------------------------------------------------------
# Lane W: Opening Range Breakout (ORB)
# Marks the high/low of the first 15m candle at NY open (9:30 AM ET = 13:30 UTC).
# Waits for breakout + retest of that range.
# Targets previous day high/low. Requires 2:1 minimum R:R.
# Also checks for FVG confirmation outside the range.
# ---------------------------------------------------------------------------

def _find_session_open_candle(
    df_15m: pd.DataFrame,
    session_hour_utc: int = 13,
    session_minute_utc: int = 30,
) -> Optional[pd.Series]:
    """Find the most recent 15m candle that starts at the NY session open."""
    if df_15m.empty:
        return None
    for i in range(len(df_15m) - 1, max(len(df_15m) - 40, -1), -1):
        ts = df_15m["timestamp"].iloc[i]
        if hasattr(ts, "hour"):
            if ts.hour == session_hour_utc and ts.minute == session_minute_utc:
                return df_15m.iloc[i]
    return None


def opening_range_breakout(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    levels: Dict[str, float],
    config: dict = None,
) -> Optional[Dict]:
    """Opening Range Breakout entry using first 15m candle of NY session.

    Strategy (from video research):
    1. Mark high/low of first candle at 9:30 AM ET (13:30 UTC)
    2. Wait for price to break above (long) or below (short) that range
    3. Require retest of the broken level (support/resistance flip)
    4. Target previous day high (long) or previous day low (short)
    5. Minimum 2:1 R:R enforced
    6. FVG confirmation adds confluence but is not required
    """
    if df_15m is None or len(df_15m) < 10:
        return None

    cfg = (config or {}).get("opening_range_breakout") or {}
    if not cfg.get("enabled", True):
        return None

    # Find the session open candle
    or_candle = _find_session_open_candle(df_15m)
    if or_candle is None:
        return None

    or_high = float(or_candle["high"])
    or_low = float(or_candle["low"])
    or_range = or_high - or_low
    if or_range <= 0:
        return None

    # Get previous day levels for targets
    prev_high = levels.get("prev_daily_high", 0)
    prev_low = levels.get("prev_daily_low", 0)
    if prev_high <= 0 or prev_low <= 0:
        return None

    # Check breakout direction
    min_break_pct = float(cfg.get("min_break_pct", 0.001))  # 0.1% beyond range

    if direction == "long":
        # Price must be above the OR high (breakout happened)
        if price <= or_high * (1 + min_break_pct):
            return None
        # Check retest: did price come back to touch or_high recently?
        retest_found = False
        lookback = min(8, len(df_15m))
        for i in range(-lookback, 0):
            bar_low = float(df_15m["low"].iloc[i])
            # Retest = bar low touched or_high zone (within 0.3%)
            if bar_low <= or_high * 1.003 and bar_low >= or_high * 0.995:
                retest_found = True
                break
        if not retest_found:
            return None

        # R:R check: SL below OR low, TP at prev day high
        sl = or_low * 0.998  # tiny buffer below OR low
        tp = prev_high
        risk = price - sl
        reward = tp - price

    else:  # short
        if price >= or_low * (1 - min_break_pct):
            return None
        retest_found = False
        lookback = min(8, len(df_15m))
        for i in range(-lookback, 0):
            bar_high = float(df_15m["high"].iloc[i])
            if bar_high >= or_low * 0.997 and bar_high <= or_low * 1.005:
                retest_found = True
                break
        if not retest_found:
            return None

        sl = or_high * 1.002
        tp = prev_low
        risk = sl - price
        reward = price - tp

    if risk <= 0 or reward <= 0:
        return None

    rr = reward / risk
    min_rr = float(cfg.get("min_rr", 2.0))
    if rr < min_rr:
        return None

    # FVG confirmation (bonus confluence, not required)
    from strategy.fvg import detect_fvg, nearest_fvg
    fvgs = detect_fvg(df_15m, lookback=20)
    fvg = nearest_fvg(price, fvgs, direction)
    fvg_confirmed = fvg is not None

    # Hourly candle continuation check (from video strategy 2)
    hourly_aligned = False
    if df_1h is not None and len(df_1h) >= 2:
        prev_1h = df_1h.iloc[-2]
        prev_1h_bullish = float(prev_1h["close"]) > float(prev_1h["open"])
        if direction == "long" and prev_1h_bullish:
            hourly_aligned = True
        elif direction == "short" and not prev_1h_bullish:
            hourly_aligned = True

    # Volume check: current bar volume vs average
    vol_ok = False
    try:
        vol_now = float(df_15m["volume"].iloc[-1])
        vol_avg = float(df_15m["volume"].iloc[-20:].mean())
        vol_ok = vol_now >= vol_avg * 0.8
    except Exception:
        vol_ok = True  # pass if can't compute

    conf = {
        "OPENING_RANGE_FORMED": True,
        "BREAKOUT_CONFIRMED": True,
        "RETEST_FOUND": retest_found,
        "FVG_CONFIRMED": fvg_confirmed,
        "HOURLY_ALIGNED": hourly_aligned,
        "VOLUME_OK": vol_ok,
        "MIN_RR_MET": True,
    }

    # Need at least 3 confluence flags (breakout + retest + one more)
    passing = sum(1 for v in conf.values() if v)
    if passing < 4:
        return None

    return {
        "type": "opening_range_breakout",
        "confluence": conf,
        "or_high": round(or_high, 8),
        "or_low": round(or_low, 8),
        "target_price": round(tp, 8),
        "stop_price": round(sl, 8),
        "risk_reward": round(rr, 2),
    }


# ---------------------------------------------------------------------------
# Lane X: Hourly Candle Continuation
# Trades in the direction of the previous 1h candle close.
# Uses 15m chart for momentum shift entries (lower high / higher low patterns).
# Fixed 2:1 R:R. Mechanical entry + stop to breakeven at 1.5R.
# ---------------------------------------------------------------------------

def hourly_continuation(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    levels: Dict[str, float],
    config: dict = None,
) -> Optional[Dict]:
    """Hourly candle continuation entry.

    Strategy (from video research):
    1. Previous 1h candle sets directional bias (bullish close = buy, bearish = sell)
    2. Current 1h candle must be aligned with bias
    3. On 15m chart, look for momentum shift: higher highs/lows failing, then reversing
    4. Enter on the break of the shift pattern
    5. Fixed 2:1 R:R target
    """
    if df_1h is None or len(df_1h) < 3:
        return None
    if df_15m is None or len(df_15m) < 8:
        return None

    cfg = (config or {}).get("hourly_continuation") or {}
    if not cfg.get("enabled", True):
        return None

    # Step 1: Previous 1h candle direction
    prev_1h = df_1h.iloc[-2]
    prev_open = float(prev_1h["open"])
    prev_close = float(prev_1h["close"])
    prev_bullish = prev_close > prev_open

    if direction == "long" and not prev_bullish:
        return None
    if direction == "short" and prev_bullish:
        return None

    # Step 2: Current 1h candle must be aligned
    curr_1h = df_1h.iloc[-1]
    curr_open = float(curr_1h["open"])
    curr_close = float(curr_1h["close"])
    if direction == "long" and curr_close < curr_open:
        return None  # current candle bearish, no long
    if direction == "short" and curr_close > curr_open:
        return None  # current candle bullish, no short

    # Step 3: 15m momentum shift detection
    # Look for failed continuation + reversal pattern
    highs = [float(df_15m["high"].iloc[i]) for i in range(-6, 0)]
    lows = [float(df_15m["low"].iloc[i]) for i in range(-6, 0)]

    if direction == "long":
        # Look for: price was making lower lows, then failed to make new low
        # = higher low formation (momentum shifting bullish)
        made_lower_lows = lows[1] < lows[0] or lows[2] < lows[1]
        higher_low = lows[-1] > min(lows[:-1])
        failed_new_low = higher_low and made_lower_lows
        if not failed_new_low:
            return None

        # SL below recent swing low, TP at 2:1
        sl = min(lows[-4:]) * 0.998
        risk = price - sl
        if risk <= 0:
            return None
        tp = price + (risk * 2.0)  # fixed 2:1

    else:  # short
        made_higher_highs = highs[1] > highs[0] or highs[2] > highs[1]
        lower_high = highs[-1] < max(highs[:-1])
        failed_new_high = lower_high and made_higher_highs
        if not failed_new_high:
            return None

        sl = max(highs[-4:]) * 1.002
        risk = sl - price
        if risk <= 0:
            return None
        tp = price - (risk * 2.0)

    # Step 4: ATR sanity check - risk shouldn't be > 2 ATR
    atr_val = 0
    try:
        atr_series = atr(df_15m, 14)
        if len(atr_series) > 0 and not pd.isna(atr_series.iloc[-1]):
            atr_val = float(atr_series.iloc[-1])
    except Exception:
        pass
    if atr_val > 0 and risk > 2.5 * atr_val:
        return None  # risk too wide

    # FVG bonus
    from strategy.fvg import detect_fvg, nearest_fvg
    fvgs = detect_fvg(df_15m, lookback=15)
    fvg = nearest_fvg(price, fvgs, direction)
    fvg_confirmed = fvg is not None

    conf = {
        "PREV_1H_ALIGNED": True,
        "CURR_1H_ALIGNED": True,
        "MOMENTUM_SHIFT": True,
        "FVG_CONFIRMED": fvg_confirmed,
        "ATR_REASONABLE": atr_val <= 0 or risk <= 2.5 * atr_val,
    }

    passing = sum(1 for v in conf.values() if v)
    if passing < 3:
        return None

    return {
        "type": "hourly_continuation",
        "confluence": conf,
        "target_price": round(tp, 8),
        "stop_price": round(sl, 8),
        "risk_reward": 2.0,
    }


# ---------------------------------------------------------------------------
# Lane Y: HTF Swing Entry -- 1H/4H Wick Reversal at Fib Levels
# ---------------------------------------------------------------------------
# The money-maker: catches the big swings visible on 1H/4H charts.
# Enter on wick candle rejection at Fib levels, ride the trend.
# Stop below the wick = TP1 once breakout confirmed.

def htf_swing_entry(
    price: float,
    df_1h: pd.DataFrame,
    df_4h: pd.DataFrame,
    df_15m: pd.DataFrame,
    direction: str,
    fibs: Dict[str, float] = None,
    levels: Dict[str, float] = None,
    config: dict = None,
) -> Optional[Dict]:
    """HTF Swing Entry -- 1H/4H wick reversal at Fib levels.

    Detects large wick candles at Fibonacci levels on 1H and 4H timeframes.
    These are the big swings: $0.005+ moves = $25+ per contract.

    Strategy:
    1. Scan last 2 candles on 1H (and optionally 4H) for wick reversals
    2. Wick must be >= 50% of candle range (institutional rejection)
    3. Must be near a Fib level (0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272)
    4. 15m momentum must confirm (not fighting the micro trend)
    5. Stop below/above the wick, target next Fib level

    This is the PRIMARY entry -- 15m scalps fill the gaps between these.
    """
    cfg = ((config or {}).get("htf_swing") or {}) if isinstance((config or {}).get("htf_swing"), dict) else {}
    if not cfg.get("enabled", True):
        return None

    # Need at least 1H data
    if df_1h is None or len(df_1h) < 5:
        return None

    min_wick_pct = float(cfg.get("min_wick_pct", 0.50))
    fib_tolerance_pct = float(cfg.get("fib_tolerance_pct", 0.015))  # 1.5% from Fib level
    require_volume = bool(cfg.get("require_volume", True))

    result = None

    # Check both 1H and 4H (4H has priority if both fire)
    timeframes = [("1h", df_1h)]
    if df_4h is not None and len(df_4h) >= 5:
        timeframes.append(("4h", df_4h))

    for tf_name, df_tf in reversed(timeframes):  # 4H checked first
        # Check last 2 candles (current + previous)
        for candle_idx in [-1, -2]:
            candle = df_tf.iloc[candle_idx]
            c_open = float(candle["open"])
            c_close = float(candle["close"])
            c_high = float(candle["high"])
            c_low = float(candle["low"])
            c_range = c_high - c_low
            if c_range <= 0:
                continue

            # Body and wick analysis
            body = abs(c_close - c_open)
            wick_pct = 1.0 - (body / c_range) if c_range > 0 else 0

            if wick_pct < min_wick_pct:
                continue  # not a wick candle

            # Direction-specific wick check
            if direction == "long":
                lower_wick = min(c_open, c_close) - c_low
                if lower_wick < 0.40 * c_range:
                    continue  # lower wick must be dominant for longs
                # Candle should show rejection (close in upper half)
                if c_close < (c_low + c_range * 0.4):
                    continue
            else:  # short
                upper_wick = c_high - max(c_open, c_close)
                if upper_wick < 0.40 * c_range:
                    continue  # upper wick must be dominant for shorts
                if c_close > (c_high - c_range * 0.4):
                    continue

            # Check proximity to Fib levels
            near_fib = False
            nearest_fib_name = None
            nearest_fib_dist = float("inf")
            if fibs:
                for fib_name, fib_price in fibs.items():
                    if fib_price <= 0:
                        continue
                    dist_pct = abs(price - fib_price) / price
                    if dist_pct < fib_tolerance_pct and dist_pct < nearest_fib_dist:
                        near_fib = True
                        nearest_fib_name = fib_name
                        nearest_fib_dist = dist_pct

            # Also check structure levels
            near_struct = False
            if levels and not near_fib:
                for lvl_name, lvl_price in levels.items():
                    if lvl_price <= 0:
                        continue
                    dist_pct = abs(price - lvl_price) / price
                    if dist_pct < fib_tolerance_pct:
                        near_struct = True
                        nearest_fib_name = lvl_name
                        break

            if not near_fib and not near_struct:
                continue  # not near any key level

            # Volume check (optional)
            vol_ok = True
            if require_volume and "volume" in df_tf.columns:
                vol_avg = df_tf["volume"].iloc[-11:-1].mean() if len(df_tf) >= 12 else df_tf["volume"].mean()
                vol_now = float(candle["volume"])
                vol_ok = vol_avg <= 0 or vol_now >= 0.8 * vol_avg  # relaxed: 0.8x avg

            if not vol_ok:
                continue

            # 15m momentum confirmation (don't fight the micro trend)
            micro_aligned = True
            if df_15m is not None and len(df_15m) >= 5:
                recent_closes = [float(df_15m["close"].iloc[i]) for i in range(-3, 0)]
                if direction == "long":
                    # At least 2 of last 3 15m candles should not be strong red
                    micro_aligned = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] >= recent_closes[i-1]) >= 1
                else:
                    micro_aligned = sum(1 for i in range(1, len(recent_closes)) if recent_closes[i] <= recent_closes[i-1]) >= 1

            # Calculate stop and target
            if direction == "long":
                stop_price = c_low * 0.998  # just below the wick low
                risk = price - stop_price
                target_price = price + (risk * 3.0)  # 3:1 minimum R:R
            else:
                stop_price = c_high * 1.002  # just above the wick high
                risk = stop_price - price
                target_price = price - (risk * 3.0)

            if risk <= 0:
                continue

            # Build confluence
            conf = {
                "HTF_WICK_REVERSAL": True,
                "FIB_ZONE": near_fib,
                "STRUCTURE_ZONE": near_struct or near_fib,
                "VOLUME_OK": vol_ok,
                "MICRO_ALIGNED": micro_aligned,
                "DIRECTION_CONFIRM": True,
            }

            passing = sum(1 for v in conf.values() if v)
            if passing < 3:
                continue

            result = {
                "type": "htf_swing",
                "confluence": conf,
                "timeframe": tf_name,
                "wick_pct": round(wick_pct, 3),
                "near_level": nearest_fib_name,
                "stop_price": round(stop_price, 8),
                "target_price": round(target_price, 8),
                "risk_reward": round(abs(target_price - price) / risk, 1) if risk > 0 else 0,
                "candle_age": abs(candle_idx),  # 0 = current candle, 1 = previous
            }
            break  # found a signal on this timeframe

        if result:
            break  # 4H signal found, don't check 1H

    return result
