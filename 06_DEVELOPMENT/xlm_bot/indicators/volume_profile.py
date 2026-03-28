"""Volume Profile -- candle-based price/volume distribution.

Builds a volume-at-price histogram from OHLCV candles (no tick data needed).
Identifies Point of Control (POC), Value Area High/Low, and naked POC magnets.

Usage:
    profile = compute_volume_profile(df, num_bins=30)
    bias = volume_profile_bias(current_price, profile["poc"], profile["vah"], profile["val"])
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import List


def compute_volume_profile(df: pd.DataFrame, num_bins: int = 30) -> dict:
    """Compute a volume profile from OHLCV candles.

    For each candle, volume is distributed across every bin that the
    candle's high-low range touches. Volume is weighted toward the
    close: bins nearer the close receive proportionally more volume.

    Args:
        df: DataFrame with columns open, high, low, close, volume.
            Must have at least 2 rows.
        num_bins: Number of equal-width price bins to divide the range into.

    Returns:
        Dictionary with keys:
            poc   -- Point of Control price (highest-volume bin midpoint)
            vah   -- Value Area High (upper edge of 70% volume zone)
            val   -- Value Area Low  (lower edge of 70% volume zone)
            bins  -- List of dicts with price_low, price_high, mid, volume
            value_area_pct -- The percentage used for the value area (0.70)
    """
    if df.empty or len(df) < 2:
        mid = df["close"].iloc[-1] if len(df) == 1 else 0.0
        return {
            "poc": mid, "vah": mid, "val": mid,
            "bins": [], "value_area_pct": 0.70,
        }

    price_low = df["low"].min()
    price_high = df["high"].max()

    # Guard against flat price (all candles identical)
    if price_high - price_low < 1e-12:
        mid = (price_high + price_low) / 2.0
        return {
            "poc": mid, "vah": mid, "val": mid,
            "bins": [], "value_area_pct": 0.70,
        }

    bin_width = (price_high - price_low) / num_bins
    bin_edges = np.linspace(price_low, price_high, num_bins + 1)
    bin_volumes = np.zeros(num_bins, dtype=np.float64)

    # Vectorised column access
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    volumes = df["volume"].values

    for i in range(len(df)):
        h, l, c, v = highs[i], lows[i], closes[i], volumes[i]
        if v <= 0 or h - l < 1e-12:
            continue

        # Which bins does this candle touch?
        first_bin = max(int((l - price_low) / bin_width), 0)
        last_bin = min(int((h - price_low) / bin_width), num_bins - 1)

        if first_bin == last_bin:
            bin_volumes[first_bin] += v
            continue

        # Distribute volume with close-proximity weighting.
        # Each touched bin gets a base share plus a bonus proportional
        # to how close the bin midpoint is to the close price.
        touched = last_bin - first_bin + 1
        mids = bin_edges[first_bin:last_bin + 1] + bin_width / 2.0
        distances = np.abs(mids - c)
        max_dist = distances.max()
        if max_dist < 1e-12:
            weights = np.ones(touched)
        else:
            # Invert distance so closer bins get more weight
            weights = 1.0 - (distances / (max_dist + 1e-12)) * 0.5

        weights /= weights.sum()
        bin_volumes[first_bin:last_bin + 1] += v * weights

    # Build bin list
    bins = []
    for b in range(num_bins):
        bins.append({
            "price_low": float(bin_edges[b]),
            "price_high": float(bin_edges[b + 1]),
            "mid": float(bin_edges[b] + bin_width / 2.0),
            "volume": float(bin_volumes[b]),
        })

    # POC = bin with highest volume
    poc_idx = int(np.argmax(bin_volumes))
    poc = bins[poc_idx]["mid"]

    # Value Area: expand outward from POC until 70% of total volume captured
    vah, val = _compute_value_area(bin_volumes, bin_edges, bin_width, poc_idx, 0.70)

    return {
        "poc": float(poc),
        "vah": float(vah),
        "val": float(val),
        "bins": bins,
        "value_area_pct": 0.70,
    }


def _compute_value_area(
    bin_volumes: np.ndarray,
    bin_edges: np.ndarray,
    bin_width: float,
    poc_idx: int,
    target_pct: float,
) -> tuple:
    """Expand outward from the POC bin until target_pct of total volume is captured.

    Returns (vah, val) as price levels.
    """
    total_vol = bin_volumes.sum()
    if total_vol <= 0:
        mid = float(bin_edges[poc_idx] + bin_width / 2.0)
        return mid, mid

    captured = bin_volumes[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx
    n = len(bin_volumes)

    while captured / total_vol < target_pct:
        look_down = bin_volumes[lo_idx - 1] if lo_idx > 0 else -1.0
        look_up = bin_volumes[hi_idx + 1] if hi_idx < n - 1 else -1.0

        if look_down < 0 and look_up < 0:
            break  # Expanded to full range

        if look_up >= look_down:
            hi_idx += 1
            captured += bin_volumes[hi_idx]
        else:
            lo_idx -= 1
            captured += bin_volumes[lo_idx]

    val = float(bin_edges[lo_idx])          # Lower edge of lowest included bin
    vah = float(bin_edges[hi_idx + 1])      # Upper edge of highest included bin
    return vah, val


def volume_profile_bias(
    price: float, poc: float, vah: float, val: float
) -> dict:
    """Determine trading bias based on price position relative to the value area.

    Args:
        price: Current market price.
        poc:   Point of Control.
        vah:   Value Area High.
        val:   Value Area Low.

    Returns:
        Dictionary with keys:
            zone              -- "above_va", "value_area", "below_va", or "at_poc"
            distance_to_poc_pct -- Distance from price to POC as a percentage of POC
            bias              -- "long", "short", or "neutral"
            score_adj         -- Integer score adjustment for the scoring engine
    """
    if poc <= 0:
        return {
            "zone": "neutral",
            "distance_to_poc_pct": 0.0,
            "bias": "neutral",
            "score_adj": 0,
        }

    dist_pct = round(abs(price - poc) / poc * 100.0, 4)

    # "At POC" if within 0.1% of the POC level
    poc_tolerance = poc * 0.001
    if abs(price - poc) <= poc_tolerance:
        return {
            "zone": "at_poc",
            "distance_to_poc_pct": dist_pct,
            "bias": "neutral",
            "score_adj": 0,
        }

    if price > vah:
        return {
            "zone": "above_va",
            "distance_to_poc_pct": dist_pct,
            "bias": "short",
            "score_adj": 8,
        }

    if price < val:
        return {
            "zone": "below_va",
            "distance_to_poc_pct": dist_pct,
            "bias": "long",
            "score_adj": 8,
        }

    # Inside the value area
    return {
        "zone": "value_area",
        "distance_to_poc_pct": dist_pct,
        "bias": "neutral",
        "score_adj": 0,
    }


def compute_session_profile(
    df: pd.DataFrame, lookback_hours: int = 4, num_bins: int = 30
) -> dict:
    """Compute a volume profile for the most recent N hours of candle data.

    This gives an intraday POC that shifts with the current session,
    useful for short-term magnet/support/resistance detection.

    Args:
        df: DataFrame with columns open, high, low, close, volume, time.
            The 'time' column should be a datetime or parseable timestamp.
        lookback_hours: How many hours of recent data to include.
        num_bins: Number of price bins.

    Returns:
        Same structure as compute_volume_profile.
    """
    if df.empty:
        return compute_volume_profile(df, num_bins)

    time_col = pd.to_datetime(df["time"])
    cutoff = time_col.iloc[-1] - pd.Timedelta(hours=lookback_hours)
    mask = time_col >= cutoff
    session_df = df.loc[mask].copy()

    if session_df.empty:
        session_df = df.tail(1)

    return compute_volume_profile(session_df, num_bins)


def find_naked_pocs(
    profiles: List[dict], current_price: float, atr: float
) -> List[dict]:
    """Find POCs from prior sessions that price has not revisited.

    A POC is considered "naked" if the current price has not come within
    0.5 * ATR of it. Naked POCs act as price magnets because the market
    tends to revisit areas of high prior activity.

    Args:
        profiles: List of profile dicts (each from compute_volume_profile or
                  compute_session_profile). Must contain at least a "poc" key.
        current_price: The current market price.
        atr: Current ATR value (used to define the revisit threshold).

    Returns:
        List of dicts sorted by proximity to current_price (nearest first).
        Each dict has:
            poc       -- The naked POC price level
            distance  -- Absolute distance from current_price
            side      -- "above" or "below" current_price
    """
    if atr <= 0 or not profiles:
        return []

    threshold = 0.5 * atr
    naked = []

    for profile in profiles:
        poc = profile.get("poc")
        if poc is None or poc <= 0:
            continue

        distance = abs(current_price - poc)

        # If price is currently AT the POC (within threshold), it is not naked
        if distance < threshold:
            continue

        naked.append({
            "poc": float(poc),
            "distance": float(distance),
            "side": "above" if poc > current_price else "below",
        })

    # Sort by proximity (nearest first)
    naked.sort(key=lambda x: x["distance"])
    return naked
