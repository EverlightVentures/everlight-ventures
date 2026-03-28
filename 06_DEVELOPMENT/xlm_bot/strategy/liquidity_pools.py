"""Liquidity pool detection -- equal highs/lows clusters.

Maps buy-side liquidity (equal highs above price) and sell-side
liquidity (equal lows below price).  Institutional players hunt
these clusters for stop sweeps, so proximity to a pool signals
a likely sweep-and-reverse pattern.

Score adjustments are designed to plug into the existing lane
scoring system via score_adj_long / score_adj_short fields.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd


def detect_equal_levels(
    df: pd.DataFrame,
    tolerance_pct: float = 0.001,
    min_touches: int = 2,
) -> Dict[str, List[Dict]]:
    """Scan for clusters of equal highs and equal lows.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV dataframe with columns: high, low (at minimum).
    tolerance_pct : float
        Two prices are "equal" if they differ by less than this
        fraction of the lower price.  Default 0.1%.
    min_touches : int
        Minimum number of touches at a level to qualify as a pool.

    Returns
    -------
    dict with keys:
        buy_side  -- list of equal-high clusters (liquidity above price)
        sell_side -- list of equal-low clusters (liquidity below price)
    Each entry: {"level": float, "touches": int, "last_touch_idx": int}
    """
    if df.empty or len(df) < min_touches:
        return {"buy_side": [], "sell_side": []}

    highs = df["high"].values.astype(float)
    lows = df["low"].values.astype(float)

    buy_side = _cluster_levels(highs, tolerance_pct, min_touches)
    sell_side = _cluster_levels(lows, tolerance_pct, min_touches)

    return {"buy_side": buy_side, "sell_side": sell_side}


def _cluster_levels(
    values: np.ndarray,
    tolerance_pct: float,
    min_touches: int,
) -> List[Dict]:
    """Group nearby price values into clusters and return qualifying ones."""
    if len(values) == 0:
        return []

    # Sort unique indices by value for clustering
    order = np.argsort(values)
    sorted_vals = values[order]

    clusters: List[Dict] = []
    cluster_start = 0

    for i in range(1, len(sorted_vals) + 1):
        # End of array or gap too large -- finalize current cluster
        if i == len(sorted_vals) or (
            sorted_vals[i] - sorted_vals[cluster_start]
        ) / max(sorted_vals[cluster_start], 1e-12) > tolerance_pct:
            count = i - cluster_start
            if count >= min_touches:
                cluster_indices = order[cluster_start:i]
                level = float(np.mean(sorted_vals[cluster_start:i]))
                last_idx = int(np.max(cluster_indices))
                clusters.append(
                    {"level": level, "touches": count, "last_touch_idx": last_idx}
                )
            cluster_start = i

    return clusters


def liquidity_bias(
    price: float,
    pools: Dict[str, List[Dict]],
    atr: float,
) -> Dict:
    """Determine directional bias based on proximity to liquidity pools.

    Parameters
    ----------
    price : float
        Current price.
    pools : dict
        Output of detect_equal_levels().
    atr : float
        Current ATR value for distance normalization.

    Returns
    -------
    dict with keys:
        nearest_pool   -- "buy_side", "sell_side", or "none"
        distance_atr   -- distance to nearest pool in ATR multiples
        sweep_expected -- True if within 1.5 ATR of a pool
        bias           -- "long", "short", or "neutral"
        score_adj_long -- int score adjustment for long setups
        score_adj_short -- int score adjustment for short setups
    """
    neutral = {
        "nearest_pool": "none",
        "distance_atr": 999.0,
        "sweep_expected": False,
        "bias": "neutral",
        "score_adj_long": 0,
        "score_adj_short": 0,
    }

    if atr <= 0 or not pools:
        return neutral

    best_side = "none"
    best_dist_atr = 999.0
    best_level = 0.0

    # Check sell-side pools (equal lows below price)
    for pool in pools.get("sell_side", []):
        dist = price - pool["level"]
        if dist > 0:  # pool is below price
            dist_atr = dist / atr
            if dist_atr < best_dist_atr:
                best_dist_atr = dist_atr
                best_side = "sell_side"
                best_level = pool["level"]

    # Check buy-side pools (equal highs above price)
    for pool in pools.get("buy_side", []):
        dist = pool["level"] - price
        if dist > 0:  # pool is above price
            dist_atr = dist / atr
            if dist_atr < best_dist_atr:
                best_dist_atr = dist_atr
                best_side = "buy_side"
                best_level = pool["level"]

    if best_side == "none" or best_dist_atr > 3.0:
        return neutral

    sweep_expected = best_dist_atr <= 1.5

    # Approaching sell-side liquidity (equal lows) -> expect sweep then bounce
    if best_side == "sell_side" and sweep_expected:
        return {
            "nearest_pool": "sell_side",
            "distance_atr": round(best_dist_atr, 3),
            "sweep_expected": True,
            "bias": "long",
            "score_adj_long": 6,
            "score_adj_short": -4,
        }

    # Approaching buy-side liquidity (equal highs) -> expect sweep then drop
    if best_side == "buy_side" and sweep_expected:
        return {
            "nearest_pool": "buy_side",
            "distance_atr": round(best_dist_atr, 3),
            "sweep_expected": True,
            "bias": "short",
            "score_adj_long": -4,
            "score_adj_short": 6,
        }

    # Within 3 ATR but beyond 1.5 -- aware but not actionable
    return {
        "nearest_pool": best_side,
        "distance_atr": round(best_dist_atr, 3),
        "sweep_expected": False,
        "bias": "neutral",
        "score_adj_long": 0,
        "score_adj_short": 0,
    }


def detect_stop_hunt(
    df: pd.DataFrame,
    pools: Dict[str, List[Dict]],
    atr: float,
) -> Dict:
    """Check if price just swept through a liquidity pool and reclaimed.

    A bullish stop hunt: wick pierced below equal lows, then the candle
    closed back above the level.  A bearish stop hunt: wick pierced above
    equal highs, then closed back below.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV dataframe. Uses the last candle for detection.
    pools : dict
        Output of detect_equal_levels().
    atr : float
        Current ATR for threshold calibration.

    Returns
    -------
    dict with keys:
        detected    -- True if a stop hunt pattern was found
        type        -- "bullish_hunt", "bearish_hunt", or "none"
        swept_level -- the liquidity level that was swept (0.0 if none)
        score_adj   -- int score adjustment (+10 for confirmed hunts)
    """
    no_hunt = {
        "detected": False,
        "type": "none",
        "swept_level": 0.0,
        "score_adj": 0,
    }

    if df.empty or len(df) < 2 or atr <= 0:
        return no_hunt

    last = df.iloc[-1]
    candle_low = float(last["low"])
    candle_high = float(last["high"])
    candle_close = float(last["close"])

    # Check for bullish stop hunt -- swept sell-side (equal lows)
    for pool in pools.get("sell_side", []):
        level = pool["level"]
        # Wick went below the level but close reclaimed above it
        if candle_low < level and candle_close > level:
            # Sweep depth should be meaningful but not a full breakdown
            sweep_depth = level - candle_low
            if 0 < sweep_depth <= 1.5 * atr:
                return {
                    "detected": True,
                    "type": "bullish_hunt",
                    "swept_level": round(level, 6),
                    "score_adj": 10,
                }

    # Check for bearish stop hunt -- swept buy-side (equal highs)
    for pool in pools.get("buy_side", []):
        level = pool["level"]
        # Wick went above the level but close reclaimed below it
        if candle_high > level and candle_close < level:
            sweep_depth = candle_high - level
            if 0 < sweep_depth <= 1.5 * atr:
                return {
                    "detected": True,
                    "type": "bearish_hunt",
                    "swept_level": round(level, 6),
                    "score_adj": 10,
                }

    return no_hunt
