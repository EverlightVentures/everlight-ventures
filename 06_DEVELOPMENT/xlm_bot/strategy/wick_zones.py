"""Multi-timeframe wick rejection zone detector.

Scans candles on every available timeframe (5m, 15m, 1h, 4h) for
price levels where wicks have clustered -- repeated rejections at
the same level signal strong support or resistance.

Higher timeframes carry more weight:
    4h = 4x,  1h = 2.5x,  15m = 1.5x,  5m = 1x

The output is a list of WickZone objects that can be merged into
the existing structure levels dict so every entry lane, exit rule,
and stop-loss calculation benefits automatically.

Usage in main.py:
    zones = build_wick_zones(df_5m, df_15m, df_1h, df_4h, config)
    levels.update(zones_to_levels(zones, price))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


# Timeframe weights: higher = stronger signal
TF_WEIGHTS: dict[str, float] = {
    "1m": 0.5,
    "5m": 1.0,
    "15m": 1.5,
    "1h": 2.5,
    "4h": 4.0,
    "1d": 6.0,
    "1w": 8.0,
}


@dataclass
class WickZone:
    """A price zone where wicks have clustered across timeframes."""
    level: float                # center of the zone
    zone_low: float             # bottom edge
    zone_high: float            # top edge
    strength: float             # composite score (0-100)
    touch_count: int            # total wick touches across all timeframes
    side: str                   # "support" or "resistance"
    timeframe_hits: dict[str, int] = field(default_factory=dict)
    strongest_tf: str = ""      # which timeframe contributed most
    avg_wick_ratio: float = 0.0 # average wick-to-range ratio at this zone
    last_touch_bars_ago: int = 0  # how recently the zone was tested


def build_wick_zones(
    df_5m: pd.DataFrame | None,
    df_15m: pd.DataFrame | None,
    df_1h: pd.DataFrame | None,
    df_4h: pd.DataFrame | None,
    config: dict | None = None,
    df_1m: pd.DataFrame | None = None,
    df_1d: pd.DataFrame | None = None,
    df_1w: pd.DataFrame | None = None,
) -> list[WickZone]:
    """Scan all timeframes for wick rejection clusters and merge into zones.

    Args:
        df_1m .. df_1w: OHLCV DataFrames for each timeframe (any can be None)
        config: optional wick_zones config overrides

    Returns:
        List of WickZone objects sorted by strength (strongest first).
    """
    cfg = config or {}
    min_wick_ratio = float(cfg.get("min_wick_ratio", 0.30) or 0.30)
    lookback_bars = int(cfg.get("lookback_bars", 60) or 60)
    zone_width_pct = float(cfg.get("zone_width_pct", 0.003) or 0.003)
    min_touches = int(cfg.get("min_touches", 2) or 2)
    min_strength = float(cfg.get("min_strength", 15) or 15)
    max_zones = int(cfg.get("max_zones", 10) or 10)
    lookback_1m = int(cfg.get("lookback_bars_1m", 120) or 120)

    lookback_1d = int(cfg.get("lookback_bars_1d", 30) or 30)
    lookback_1w = int(cfg.get("lookback_bars_1w", 20) or 20)

    # Step 1: Collect raw wick rejection points from each timeframe
    raw_points: list[dict] = []
    frames = [
        ("1m", df_1m, lookback_1m),
        ("5m", df_5m, lookback_bars),
        ("15m", df_15m, lookback_bars),
        ("1h", df_1h, lookback_bars),
        ("4h", df_4h, lookback_bars),
        ("1d", df_1d, lookback_1d),
        ("1w", df_1w, lookback_1w),
    ]

    for tf_label, df, tf_lookback in frames:
        if df is None or df.empty or len(df) < 10:
            continue
        weight = TF_WEIGHTS.get(tf_label, 1.0)
        points = _extract_wick_points(df, tf_label, weight, tf_lookback, min_wick_ratio)
        raw_points.extend(points)

    if not raw_points:
        return []

    # Step 2: Cluster nearby points into zones
    zones = _cluster_points_into_zones(raw_points, zone_width_pct)

    # Step 3: Filter by minimum touches and strength
    zones = [z for z in zones if z.touch_count >= min_touches and z.strength >= min_strength]

    # Sort by strength descending
    zones.sort(key=lambda z: z.strength, reverse=True)

    return zones[:max_zones]


def zones_to_levels(zones: list[WickZone], price: float) -> dict[str, float]:
    """Convert wick zones to a levels dict compatible with compute_structure_levels.

    Entries are keyed like "wick_support_1", "wick_resistance_2" etc.
    Only includes the zone center so it integrates cleanly with
    _near_structure_band() and other level-aware functions.
    """
    out: dict[str, float] = {}
    sup_idx = 0
    res_idx = 0
    for z in zones:
        if z.side == "support":
            sup_idx += 1
            out[f"wick_support_{sup_idx}"] = z.level
        else:
            res_idx += 1
            out[f"wick_resistance_{res_idx}"] = z.level
    return out


def zone_proximity_score(
    price: float,
    zones: list[WickZone],
    direction: str,
    atr_value: float,
) -> dict[str, Any]:
    """Score how close the current price is to a strong wick zone.

    Returns a dict with:
        near_zone: bool
        zone: WickZone or None (nearest relevant zone)
        distance_atr: float (distance in ATR multiples)
        confidence: float (0-1 based on zone strength and proximity)
        bounce_bias: str ("support_bounce", "resistance_reject", "none")
    """
    if not zones or atr_value <= 0:
        return {"near_zone": False, "zone": None, "distance_atr": 99.0,
                "confidence": 0.0, "bounce_bias": "none"}

    d = direction.lower().strip()
    best_zone = None
    best_dist_atr = 99.0

    for z in zones:
        dist = abs(price - z.level)
        dist_atr = dist / atr_value if atr_value > 0 else 99.0

        # For longs, we care about support zones below price
        # For shorts, we care about resistance zones above price
        if d == "long" and z.side == "support" and price >= z.zone_low:
            if dist_atr < best_dist_atr:
                best_dist_atr = dist_atr
                best_zone = z
        elif d == "short" and z.side == "resistance" and price <= z.zone_high:
            if dist_atr < best_dist_atr:
                best_dist_atr = dist_atr
                best_zone = z
        # Also consider: price approaching a zone from either side
        elif dist_atr < best_dist_atr and dist_atr < 2.0:
            best_dist_atr = dist_atr
            best_zone = z

    if best_zone is None:
        return {"near_zone": False, "zone": None, "distance_atr": 99.0,
                "confidence": 0.0, "bounce_bias": "none"}

    # Confidence = zone strength * proximity factor
    proximity_factor = max(0, 1.0 - best_dist_atr / 2.0)
    confidence = min(1.0, (best_zone.strength / 100.0) * proximity_factor)

    if d == "long" and best_zone.side == "support":
        bias = "support_bounce"
    elif d == "short" and best_zone.side == "resistance":
        bias = "resistance_reject"
    else:
        bias = "zone_nearby"

    return {
        "near_zone": best_dist_atr <= 1.5,
        "zone": best_zone,
        "distance_atr": round(best_dist_atr, 3),
        "confidence": round(confidence, 4),
        "bounce_bias": bias,
        "zone_strength": best_zone.strength,
        "zone_touches": best_zone.touch_count,
        "zone_strongest_tf": best_zone.strongest_tf,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_wick_points(
    df: pd.DataFrame,
    tf_label: str,
    weight: float,
    lookback: int,
    min_wick_ratio: float,
) -> list[dict]:
    """Extract wick rejection points from a single timeframe.

    Each point = a price level where a candle showed a significant wick.
    """
    points = []
    window = df.tail(lookback)
    total_bars = len(window)

    for idx, (_, candle) in enumerate(window.iterrows()):
        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])
        total_range = h - l
        if total_range <= 0:
            continue

        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)

        bars_ago = total_bars - idx - 1

        # Lower wick = support rejection
        lower_ratio = lower_wick / total_range
        if lower_ratio >= min_wick_ratio:
            # Recency decay: recent touches count more
            recency = max(0.3, 1.0 - (bars_ago / max(1, lookback)))
            points.append({
                "level": l + lower_wick * 0.3,  # zone center slightly above the wick tip
                "wick_tip": l,
                "body_edge": min(o, c),
                "side": "support",
                "wick_ratio": lower_ratio,
                "weight": weight * recency,
                "tf": tf_label,
                "bars_ago": bars_ago,
            })

        # Upper wick = resistance rejection
        upper_ratio = upper_wick / total_range
        if upper_ratio >= min_wick_ratio:
            recency = max(0.3, 1.0 - (bars_ago / max(1, lookback)))
            points.append({
                "level": h - upper_wick * 0.3,
                "wick_tip": h,
                "body_edge": max(o, c),
                "side": "resistance",
                "wick_ratio": upper_ratio,
                "weight": weight * recency,
                "tf": tf_label,
                "bars_ago": bars_ago,
            })

    return points


def _cluster_points_into_zones(
    points: list[dict],
    zone_width_pct: float,
) -> list[WickZone]:
    """Group nearby wick points into zones using simple clustering.

    Points within zone_width_pct of each other's level are merged.
    """
    if not points:
        return []

    # Sort by level
    points.sort(key=lambda p: p["level"])

    zones: list[WickZone] = []
    used = [False] * len(points)

    for i, anchor in enumerate(points):
        if used[i]:
            continue

        # Start a new cluster
        cluster = [anchor]
        used[i] = True
        anchor_level = anchor["level"]
        threshold = anchor_level * zone_width_pct

        for j in range(i + 1, len(points)):
            if used[j]:
                continue
            if abs(points[j]["level"] - anchor_level) <= threshold:
                # Must be same side (support/resistance)
                if points[j]["side"] == anchor["side"]:
                    cluster.append(points[j])
                    used[j] = True

        if not cluster:
            continue

        # Compute zone stats
        levels = [p["level"] for p in cluster]
        weights = [p["weight"] for p in cluster]
        wick_ratios = [p["wick_ratio"] for p in cluster]

        # Weighted center
        total_weight = sum(weights)
        center = sum(l * w for l, w in zip(levels, weights)) / total_weight if total_weight > 0 else sum(levels) / len(levels)

        zone_low = min(p["wick_tip"] for p in cluster)
        zone_high = max(p.get("body_edge", p["level"]) for p in cluster)

        # Count touches per timeframe
        tf_hits: dict[str, int] = {}
        for p in cluster:
            tf = p["tf"]
            tf_hits[tf] = tf_hits.get(tf, 0) + 1

        # Find strongest contributing timeframe
        strongest_tf = max(tf_hits.keys(), key=lambda t: tf_hits[t] * TF_WEIGHTS.get(t, 1.0))

        # Compute strength score (0-100)
        # Base: weighted touch count
        strength = total_weight * 5.0

        # Bonus for multi-timeframe confirmation
        tf_count = len(tf_hits)
        if tf_count >= 3:
            strength += 20
        elif tf_count >= 2:
            strength += 10

        # Bonus for high wick ratios
        avg_wick_ratio = sum(wick_ratios) / len(wick_ratios)
        if avg_wick_ratio >= 0.60:
            strength += 10
        elif avg_wick_ratio >= 0.45:
            strength += 5

        # Bonus for 4h or 1h touches
        if "4h" in tf_hits:
            strength += 15 * tf_hits["4h"]
        if "1h" in tf_hits:
            strength += 8 * tf_hits["1h"]

        # Recency bonus
        min_bars_ago = min(p["bars_ago"] for p in cluster)

        zone = WickZone(
            level=round(center, 8),
            zone_low=round(zone_low, 8),
            zone_high=round(zone_high, 8),
            strength=min(100, round(strength, 1)),
            touch_count=len(cluster),
            side=cluster[0]["side"],
            timeframe_hits=tf_hits,
            strongest_tf=strongest_tf,
            avg_wick_ratio=round(avg_wick_ratio, 4),
            last_touch_bars_ago=min_bars_ago,
        )
        zones.append(zone)

    return zones
