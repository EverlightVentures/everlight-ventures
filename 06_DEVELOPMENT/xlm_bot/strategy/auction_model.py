"""Auction Market Model -- Fabio Valentina inspired.

Two models based on Auction Market Theory (AMT):

Model 1: AUCTION_TREND (imbalance -> trend following)
    - Market is OUT OF BALANCE (price outside value area)
    - Wait for pullback to low volume node
    - Trigger on CVD confirmation + volume aggression
    - Target: previous session POC
    - Tight SL beyond aggression candle

Model 2: AUCTION_REVERSION (balance -> mean reversion)
    - Market is IN BALANCE (price inside value area, ranging)
    - Price at value area edge (VAH or VAL)
    - Failed auction (sweep + reclaim) + CVD confirmation
    - Target: POC (center of balance)
    - SL beyond the failed sweep extreme

Core principle: READ, don't PREDICT.
    - No entry without volume confirmation
    - Be wrong immediately (tight SL)
    - Break even fast after 1 ATR move
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional

from indicators.volume_profile import compute_volume_profile
from indicators.cvd import compute_cvd, cvd_divergence, cvd_momentum, cvd_absorption


# ---------------------------------------------------------------------------
# Market state detection
# ---------------------------------------------------------------------------

def detect_market_state(
    price: float,
    profile: dict,
    atr: float,
) -> dict:
    """Classify market as BALANCED or IMBALANCED using volume profile.

    IMBALANCED: price is outside the value area (above VAH or below VAL).
    This means the market has moved away from fair value and is searching
    for a new balance point. Trend-following setups are valid.

    BALANCED: price is inside the value area. The market is in consensus.
    Mean-reversion setups are valid (trade from edges back to POC).

    Returns dict with state, zone, distances, and bias direction.
    """
    poc = profile.get("poc", 0)
    vah = profile.get("vah", 0)
    val = profile.get("val", 0)

    if poc <= 0 or vah <= 0 or val <= 0:
        return {"state": "unknown", "zone": "unknown", "bias": "neutral"}

    va_width = vah - val
    va_width_pct = va_width / poc * 100 if poc > 0 else 0

    dist_to_poc = abs(price - poc)
    dist_to_poc_pct = dist_to_poc / poc * 100 if poc > 0 else 0

    # How far outside the value area (in ATR units)
    if price > vah:
        dist_outside = (price - vah) / atr if atr > 0 else 0
        zone = "above_va"
        bias = "long"  # market is pushing up, trend is long
    elif price < val:
        dist_outside = (val - price) / atr if atr > 0 else 0
        zone = "below_va"
        bias = "short"  # market is pushing down, trend is short
    else:
        dist_outside = 0
        # Inside VA -- where exactly?
        if abs(price - vah) < atr * 0.3:
            zone = "near_vah"
            bias = "short"  # near top of range, fade
        elif abs(price - val) < atr * 0.3:
            zone = "near_val"
            bias = "long"  # near bottom of range, fade
        else:
            zone = "mid_va"
            bias = "neutral"

    # Imbalanced if price is > 0.5 ATR outside value area
    if dist_outside > 0.5:
        state = "imbalanced"
    else:
        state = "balanced"

    return {
        "state": state,
        "zone": zone,
        "bias": bias,
        "poc": poc,
        "vah": vah,
        "val": val,
        "va_width_pct": round(va_width_pct, 4),
        "dist_to_poc_pct": round(dist_to_poc_pct, 4),
        "dist_outside_atr": round(dist_outside, 2),
    }


# ---------------------------------------------------------------------------
# Low Volume Node finder
# ---------------------------------------------------------------------------

def find_low_volume_nodes(profile: dict, threshold_pct: float = 0.3) -> list:
    """Find price levels with significantly less volume than surrounding areas.

    Low volume nodes are where price moved fast without much transaction.
    They act as magnets (price tends to revisit) and as support/resistance
    (price reacts when it hits them).

    Args:
        profile: Volume profile dict from compute_volume_profile.
        threshold_pct: Bins with volume below this fraction of max volume
                       are considered LVN candidates.

    Returns:
        List of dicts with mid price, volume, and relative_volume for each LVN.
    """
    bins = profile.get("bins", [])
    if not bins:
        return []

    max_vol = max(b["volume"] for b in bins)
    if max_vol <= 0:
        return []

    lvns = []
    for b in bins:
        rel_vol = b["volume"] / max_vol
        if rel_vol < threshold_pct and b["volume"] > 0:
            lvns.append({
                "price_low": b["price_low"],
                "price_high": b["price_high"],
                "mid": b["mid"],
                "volume": b["volume"],
                "relative_volume": round(rel_vol, 4),
            })

    # Sort by proximity to center (most interesting LVNs are in the middle)
    poc = profile.get("poc", 0)
    if poc > 0:
        lvns.sort(key=lambda x: abs(x["mid"] - poc))

    return lvns


def find_nearest_lvn(price: float, lvns: list, direction: str) -> Optional[dict]:
    """Find the nearest LVN in the given direction from current price.

    For longs: find LVN below price (pullback target)
    For shorts: find LVN above price (pullback target)
    """
    if not lvns:
        return None

    if direction == "long":
        candidates = [l for l in lvns if l["mid"] < price]
        if candidates:
            return min(candidates, key=lambda x: abs(x["mid"] - price))
    else:
        candidates = [l for l in lvns if l["mid"] > price]
        if candidates:
            return min(candidates, key=lambda x: abs(x["mid"] - price))

    return None


# ---------------------------------------------------------------------------
# Volume aggression detection
# ---------------------------------------------------------------------------

def detect_aggression(df: pd.DataFrame, lookback: int = 5) -> dict:
    """Detect aggressive buying or selling from recent candles.

    Aggression = volume spike + directional candle body.
    This is the candle-level proxy for Fabio's "big order bubbles."

    Checks:
    1. Volume in last candle vs average (>1.5x = spike)
    2. Candle body direction and size relative to range
    3. Follow-through: does the next candle continue or fail?
    """
    result = {
        "detected": False,
        "type": "none",  # "buy_aggression" or "sell_aggression"
        "strength": 0.0,
        "volume_ratio": 0.0,
        "body_ratio": 0.0,
        "follow_through": False,
    }

    if df is None or len(df) < lookback + 2:
        return result

    recent = df.tail(lookback + 1)
    prev_bars = recent.iloc[:-1]
    current = recent.iloc[-1]

    avg_vol = prev_bars["volume"].mean()
    if avg_vol <= 0:
        return result

    vol_ratio = current["volume"] / avg_vol
    bar_range = current["high"] - current["low"]
    if bar_range <= 0:
        return result

    body = current["close"] - current["open"]
    body_ratio = abs(body) / bar_range  # How much of the candle is body vs wick

    result["volume_ratio"] = round(vol_ratio, 2)
    result["body_ratio"] = round(body_ratio, 2)

    # Need volume spike (>1.5x) AND directional body (>50% of range)
    if vol_ratio < 1.5 or body_ratio < 0.4:
        return result

    result["detected"] = True
    result["strength"] = round(min(vol_ratio / 3.0, 1.0) * body_ratio, 3)

    if body > 0:
        result["type"] = "buy_aggression"
    else:
        result["type"] = "sell_aggression"

    # Check follow-through from previous candle
    if len(df) >= lookback + 2:
        prev = df.iloc[-2]
        prev_body = prev["close"] - prev["open"]
        if (body > 0 and prev_body > 0) or (body < 0 and prev_body < 0):
            result["follow_through"] = True

    return result


# ---------------------------------------------------------------------------
# Failed auction detection
# ---------------------------------------------------------------------------

def detect_failed_auction(
    df: pd.DataFrame,
    vah: float,
    val: float,
    atr: float,
    lookback: int = 10,
) -> dict:
    """Detect failed auction -- price sweeps beyond VA then reclaims.

    This is the key setup for mean reversion: the market tries to break
    out of balance but fails, trapping breakout traders.

    Failed auction UP: price spikes above VAH then closes back below
    Failed auction DOWN: price dips below VAL then closes back above
    """
    result = {
        "detected": False,
        "type": "none",  # "failed_auction_high" or "failed_auction_low"
        "sweep_price": 0.0,
        "reclaim_price": 0.0,
        "trapped_side": "none",
    }

    if df is None or len(df) < 3 or atr <= 0:
        return result

    recent = df.tail(lookback)
    current = recent.iloc[-1]

    # Failed auction HIGH: wick above VAH, close below VAH
    highs_above_vah = recent[recent["high"] > vah]
    if len(highs_above_vah) > 0 and current["close"] < vah:
        max_sweep = recent["high"].max()
        if max_sweep > vah and (max_sweep - vah) > atr * 0.2:
            result["detected"] = True
            result["type"] = "failed_auction_high"
            result["sweep_price"] = float(max_sweep)
            result["reclaim_price"] = float(current["close"])
            result["trapped_side"] = "longs"  # longs trapped above VAH

    # Failed auction LOW: wick below VAL, close above VAL
    lows_below_val = recent[recent["low"] < val]
    if len(lows_below_val) > 0 and current["close"] > val:
        min_sweep = recent["low"].min()
        if min_sweep < val and (val - min_sweep) > atr * 0.2:
            # Only override if we didn't already detect a high failure,
            # or if the low failure is more recent
            if not result["detected"]:
                result["detected"] = True
                result["type"] = "failed_auction_low"
                result["sweep_price"] = float(min_sweep)
                result["reclaim_price"] = float(current["close"])
                result["trapped_side"] = "shorts"  # shorts trapped below VAL

    return result


# ---------------------------------------------------------------------------
# Model 1: AUCTION_TREND
# ---------------------------------------------------------------------------

def auction_trend_entry(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    atr: float,
    config: dict = None,
) -> Optional[dict]:
    """Trend-following entry when market is OUT OF BALANCE.

    Fabio's Model 1:
    Step 1: Market state = IMBALANCED (price outside value area)
    Step 2: Location = price is pulling back toward a low volume node
    Step 3: Trigger = CVD confirms direction + volume aggression present

    The idea: when the market leaves balance, it searches for new balance.
    We ride that search by entering on pullbacks to low-volume areas
    where price moved fast (little resistance).

    Target: previous session POC (where the market was balanced before)
    SL: beyond the aggression candle (tight)
    """
    if df_15m is None or len(df_15m) < 30:
        return None

    cfg = config or {}

    # Step 1: Compute volume profile and check market state
    # Use 1h data for the "big picture" profile (like Fabio's daily profile)
    if df_1h is not None and len(df_1h) >= 20:
        profile = compute_volume_profile(df_1h.tail(48), num_bins=30)  # ~2 days
    else:
        profile = compute_volume_profile(df_15m.tail(96), num_bins=30)

    # Session profile for recent activity (use tail instead of time-based
    # because bot DataFrames use 'timestamp' not 'time')
    session_bars = min(24, len(df_15m))  # ~6 hours of 15m candles
    session_profile = compute_volume_profile(df_15m.tail(session_bars), num_bins=20)

    market = detect_market_state(price, profile, atr)

    if market["state"] != "imbalanced":
        return None

    # Direction must align with imbalance
    if direction == "long" and market["zone"] != "above_va":
        return None
    if direction == "short" and market["zone"] != "below_va":
        return None

    # Step 2: Find low volume nodes for entry location
    lvns = find_low_volume_nodes(session_profile, threshold_pct=0.35)
    nearest_lvn = find_nearest_lvn(price, lvns, direction)

    # Check if price is AT or NEAR a low volume node (within 0.5 ATR)
    at_lvn = False
    lvn_price = None
    if nearest_lvn:
        dist_to_lvn = abs(price - nearest_lvn["mid"])
        if dist_to_lvn < atr * 0.8:  # Within 0.8 ATR of LVN
            at_lvn = True
            lvn_price = nearest_lvn["mid"]

    # Step 3: Trigger -- CVD confirmation + aggression
    cvd_mom = cvd_momentum(df_15m, fast=5, slow=15)
    aggression = detect_aggression(df_15m, lookback=5)
    absorption = cvd_absorption(df_15m, window=5)

    # CVD must confirm direction
    cvd_confirms = False
    if direction == "long" and cvd_mom["momentum"] in ("buy", "strong_buy"):
        cvd_confirms = True
    elif direction == "short" and cvd_mom["momentum"] in ("sell", "strong_sell"):
        cvd_confirms = True

    # Need at least one of: aggression in our direction, absorption against us, or CVD crossover
    aggression_confirms = False
    if aggression["detected"]:
        if direction == "long" and aggression["type"] == "buy_aggression":
            aggression_confirms = True
        elif direction == "short" and aggression["type"] == "sell_aggression":
            aggression_confirms = True

    absorption_confirms = False
    if absorption["detected"]:
        if direction == "long" and absorption["type"] == "buying_absorption":
            absorption_confirms = True
        elif direction == "short" and absorption["type"] == "selling_absorption":
            absorption_confirms = True

    cvd_cross = cvd_mom["crossover"]
    crossover_confirms = (
        (direction == "long" and cvd_cross == "bullish") or
        (direction == "short" and cvd_cross == "bearish")
    )

    # Scoring: need CVD + at least one more confirmation
    confirmations = sum([
        cvd_confirms,
        aggression_confirms,
        absorption_confirms,
        crossover_confirms,
        at_lvn,
    ])

    # Minimum: CVD confirms + 1 other, OR at LVN + 2 others
    if not cvd_confirms and confirmations < 3:
        return None
    if cvd_confirms and confirmations < 2:
        return None

    # Compute entry, SL, TP
    poc = market["poc"]
    vah = market["vah"]
    val = market["val"]

    if direction == "long":
        stop_loss = price - atr * 1.2
        # Target: POC if we're above it, or VAH if we're still climbing
        if price > poc:
            # Already above POC, target extension
            tp1 = price + atr * 2.0
            tp2 = price + atr * 3.5
        else:
            tp1 = poc
            tp2 = poc + atr * 1.5
        tp3 = tp1 + (tp1 - stop_loss) * 2  # 3R target
    else:
        stop_loss = price + atr * 1.2
        if price < poc:
            tp1 = price - atr * 2.0
            tp2 = price - atr * 3.5
        else:
            tp1 = poc
            tp2 = poc - atr * 1.5
        tp3 = tp1 - (stop_loss - tp1) * 2

    risk = abs(price - stop_loss)
    reward = abs(tp1 - price)
    rr = reward / risk if risk > 0 else 0

    if rr < 1.5:
        return None  # Fabio minimum is 1:1.5

    return {
        "type": "auction_trend",
        "price": price,
        "stop": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr": round(rr, 2),
        "entry_profile_key": "auction_trend",
        "confluence": {
            "MARKET_IMBALANCED": True,
            "CVD_CONFIRMS": cvd_confirms,
            "AGGRESSION": aggression_confirms,
            "ABSORPTION": absorption_confirms,
            "CVD_CROSSOVER": crossover_confirms,
            "AT_LVN": at_lvn,
        },
        "confluence_score": confirmations,
        "market_state": market,
        "cvd_momentum": cvd_mom["momentum"],
        "aggression_detail": aggression,
        "lvn_price": lvn_price,
    }


# ---------------------------------------------------------------------------
# Model 2: AUCTION_REVERSION
# ---------------------------------------------------------------------------

def auction_reversion_entry(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    atr: float,
    config: dict = None,
) -> Optional[dict]:
    """Mean-reversion entry when market is IN BALANCE.

    Fabio's Model 2:
    Step 1: Market state = BALANCED (price inside value area)
    Step 2: Location = price at value area edge (VAH or VAL)
    Step 3: Trigger = failed auction (sweep + reclaim) + CVD confirms reversal

    The idea: in a balanced market, 70% of the time price stays within
    the value area. We trade FROM the edges BACK TO the POC.
    Wait for the SECOND drive (don't take the first -- could be fake).

    Target: POC (center of balance)
    SL: beyond the failed auction sweep
    """
    if df_15m is None or len(df_15m) < 30:
        return None

    cfg = config or {}

    # Step 1: Compute volume profile and check market state
    if df_1h is not None and len(df_1h) >= 20:
        profile = compute_volume_profile(df_1h.tail(48), num_bins=30)
    else:
        profile = compute_volume_profile(df_15m.tail(96), num_bins=30)

    market = detect_market_state(price, profile, atr)

    if market["state"] != "balanced":
        return None

    poc = market["poc"]
    vah = market["vah"]
    val = market["val"]

    # Step 2: Price must be near an edge of the value area
    if direction == "long" and market["zone"] != "near_val":
        return None
    if direction == "short" and market["zone"] != "near_vah":
        return None

    # Step 3: Failed auction detection
    failed = detect_failed_auction(df_15m, vah, val, atr, lookback=10)

    # For longs: need failed auction LOW (shorts trapped)
    # For shorts: need failed auction HIGH (longs trapped)
    failed_confirms = False
    if direction == "long" and failed["detected"] and failed["type"] == "failed_auction_low":
        failed_confirms = True
    elif direction == "short" and failed["detected"] and failed["type"] == "failed_auction_high":
        failed_confirms = True

    # CVD must show reversal momentum building
    cvd_mom = cvd_momentum(df_15m, fast=5, slow=15)
    cvd_div = cvd_divergence(df_15m, lookback=15)
    aggression = detect_aggression(df_15m, lookback=5)
    absorption = cvd_absorption(df_15m, window=5)

    cvd_confirms = False
    if direction == "long" and cvd_mom["momentum"] in ("buy", "strong_buy", "neutral"):
        # For reversion, even neutral CVD is okay if we have failed auction
        if cvd_mom["momentum"] != "neutral" or failed_confirms:
            cvd_confirms = True
    elif direction == "short" and cvd_mom["momentum"] in ("sell", "strong_sell", "neutral"):
        if cvd_mom["momentum"] != "neutral" or failed_confirms:
            cvd_confirms = True

    # CVD divergence is VERY bullish for mean reversion
    div_confirms = False
    if direction == "long" and cvd_div["divergence"] == "bullish":
        div_confirms = True
    elif direction == "short" and cvd_div["divergence"] == "bearish":
        div_confirms = True

    # Aggression against us that gets absorbed = trapped traders = fuel
    counter_aggression_absorbed = False
    if aggression["detected"] and absorption["detected"]:
        if direction == "long" and aggression["type"] == "sell_aggression" and absorption["type"] == "buying_absorption":
            counter_aggression_absorbed = True
        elif direction == "short" and aggression["type"] == "buy_aggression" and absorption["type"] == "selling_absorption":
            counter_aggression_absorbed = True

    confirmations = sum([
        failed_confirms,
        cvd_confirms,
        div_confirms,
        counter_aggression_absorbed,
    ])

    # Must have failed auction + at least 1 other, OR 3 of the others
    if failed_confirms and confirmations < 2:
        return None
    if not failed_confirms and confirmations < 3:
        return None

    # Entry, SL, TP
    if direction == "long":
        # SL below the sweep low (or VAL - buffer)
        if failed_confirms:
            stop_loss = failed["sweep_price"] - atr * 0.3
        else:
            stop_loss = val - atr * 0.5
        tp1 = poc  # Target POC (highest probability)
        tp2 = vah  # Extended target
        tp3 = vah + atr  # Runner
    else:
        if failed_confirms:
            stop_loss = failed["sweep_price"] + atr * 0.3
        else:
            stop_loss = vah + atr * 0.5
        tp1 = poc
        tp2 = val
        tp3 = val - atr

    risk = abs(price - stop_loss)
    reward = abs(tp1 - price)
    rr = reward / risk if risk > 0 else 0

    if rr < 1.0:
        return None  # Even for reversion, need at least 1:1

    return {
        "type": "auction_reversion",
        "price": price,
        "stop": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr": round(rr, 2),
        "entry_profile_key": "auction_reversion",
        "confluence": {
            "MARKET_BALANCED": True,
            "FAILED_AUCTION": failed_confirms,
            "CVD_CONFIRMS": cvd_confirms,
            "CVD_DIVERGENCE": div_confirms,
            "COUNTER_ABSORBED": counter_aggression_absorbed,
        },
        "confluence_score": confirmations,
        "market_state": market,
        "failed_auction": failed if failed_confirms else None,
        "cvd_momentum": cvd_mom["momentum"],
        "cvd_divergence": cvd_div["divergence"],
    }


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

def auction_entry(
    price: float,
    df_15m: pd.DataFrame,
    df_1h: pd.DataFrame,
    direction: str,
    atr: float,
    config: dict = None,
) -> Optional[dict]:
    """Try both auction models and return the best signal.

    Priority: auction_trend (imbalance) > auction_reversion (balance)
    because trend trades have higher R:R potential.
    """
    # Try trend model first (higher R:R when it hits)
    trend = auction_trend_entry(price, df_15m, df_1h, direction, atr, config)
    if trend:
        return trend

    # Fall back to reversion model
    reversion = auction_reversion_entry(price, df_15m, df_1h, direction, atr, config)
    if reversion:
        return reversion

    return None
