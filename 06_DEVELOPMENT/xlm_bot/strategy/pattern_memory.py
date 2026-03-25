"""Pattern Memory: real-time chart pattern detection from wick zones + price action.

Uses the wick zone map (support/resistance from multi-TF wick clusters) to
detect forming chart structures:

- Double top / double bottom (two touches at a wick zone)
- Channel / range (parallel support + resistance zones with price between)
- Breakout (price closes through a strong wick zone)
- Failed breakout / fakeout (price pierces a zone then reclaims)

The detector REMEMBERS recent zone interactions so it can recognize
patterns as they form across multiple candles, not just single-bar events.

Results feed into the score modifier and decision log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from strategy.wick_zones import WickZone


@dataclass
class PatternSignal:
    """A detected chart pattern."""
    pattern: str        # "double_top", "double_bottom", "channel", "breakout", "fakeout"
    direction_bias: str # "long", "short", "neutral"
    confidence: float   # 0.0 - 1.0
    zone_level: float   # the key price level involved
    zone_strength: float
    description: str    # human-readable for decision log
    score_modifier: int # suggested score bonus/penalty (-10 to +10)
    meta: dict = field(default_factory=dict)


def detect_patterns(
    price: float,
    df: pd.DataFrame,
    zones: list[WickZone],
    atr_value: float,
    state: dict | None = None,
    config: dict | None = None,
) -> list[PatternSignal]:
    """Scan for chart patterns using wick zones and recent price history.

    Args:
        price: current price
        df: OHLCV DataFrame (15m preferred for pattern timeframe)
        zones: wick zones from build_wick_zones()
        atr_value: current ATR for distance calculations
        state: bot state dict (for persisting pattern memory across cycles)
        config: optional config overrides

    Returns:
        List of PatternSignal objects (may be empty).
    """
    if not zones or df is None or df.empty or len(df) < 10 or atr_value <= 0:
        return []

    cfg = config or {}
    patterns: list[PatternSignal] = []

    # Detect double top / double bottom
    dt_signals = _detect_double_touch(price, df, zones, atr_value, cfg)
    patterns.extend(dt_signals)

    # Detect channel / range
    ch_signal = _detect_channel(price, zones, atr_value, cfg)
    if ch_signal:
        patterns.append(ch_signal)

    # Detect breakout through a wick zone
    bk_signals = _detect_breakout(price, df, zones, atr_value, cfg)
    patterns.extend(bk_signals)

    # Detect fakeout / failed breakout
    fk_signals = _detect_fakeout(price, df, zones, atr_value, cfg)
    patterns.extend(fk_signals)

    # Update pattern memory in state for cross-cycle awareness
    if state is not None:
        _update_pattern_memory(state, patterns, price, zones)

    return patterns


def pattern_score_modifier(patterns: list[PatternSignal], direction: str) -> int:
    """Compute net score modifier from detected patterns for a given direction.

    Supportive patterns add points, hostile patterns subtract.
    """
    if not patterns:
        return 0

    total = 0
    d = direction.lower().strip()
    for p in patterns:
        if p.direction_bias == d:
            total += p.score_modifier
        elif p.direction_bias != "neutral" and p.direction_bias != d:
            total -= abs(p.score_modifier)
    return max(-15, min(15, total))


# ---------------------------------------------------------------------------
# Pattern detectors
# ---------------------------------------------------------------------------

def _detect_double_touch(
    price: float,
    df: pd.DataFrame,
    zones: list[WickZone],
    atr_value: float,
    cfg: dict,
) -> list[PatternSignal]:
    """Detect double top/bottom: price touched a zone at least twice.

    A zone with touch_count >= 2 where the current price is approaching
    signals a potential double top (resistance) or double bottom (support).
    """
    signals = []
    proximity_atr = float(cfg.get("double_touch_proximity_atr", 1.5) or 1.5)

    for z in zones:
        if z.touch_count < 2:
            continue

        dist = abs(price - z.level)
        dist_atr = dist / atr_value

        if dist_atr > proximity_atr:
            continue

        if z.side == "support" and price >= z.zone_low:
            # Price approaching support that has bounced before = double bottom forming
            conf = min(1.0, (z.strength / 80.0) * (z.touch_count / 3.0))
            signals.append(PatternSignal(
                pattern="double_bottom",
                direction_bias="long",
                confidence=round(conf, 3),
                zone_level=z.level,
                zone_strength=z.strength,
                description=f"Double bottom forming at {z.level:.6f} ({z.touch_count} touches, strongest on {z.strongest_tf})",
                score_modifier=min(8, int(conf * 10)),
                meta={"touches": z.touch_count, "tf_hits": z.timeframe_hits, "dist_atr": round(dist_atr, 2)},
            ))

        elif z.side == "resistance" and price <= z.zone_high:
            # Price approaching resistance that has rejected before = double top forming
            conf = min(1.0, (z.strength / 80.0) * (z.touch_count / 3.0))
            signals.append(PatternSignal(
                pattern="double_top",
                direction_bias="short",
                confidence=round(conf, 3),
                zone_level=z.level,
                zone_strength=z.strength,
                description=f"Double top forming at {z.level:.6f} ({z.touch_count} touches, strongest on {z.strongest_tf})",
                score_modifier=min(8, int(conf * 10)),
                meta={"touches": z.touch_count, "tf_hits": z.timeframe_hits, "dist_atr": round(dist_atr, 2)},
            ))

    return signals


def _detect_channel(
    price: float,
    zones: list[WickZone],
    atr_value: float,
    cfg: dict,
) -> PatternSignal | None:
    """Detect channel/range: parallel support and resistance zones with price between.

    If price is between a support zone below and resistance zone above,
    we're in a defined range. Bias depends on which edge price is nearer.
    """
    min_channel_width_atr = float(cfg.get("min_channel_width_atr", 1.5) or 1.5)
    max_channel_width_atr = float(cfg.get("max_channel_width_atr", 8.0) or 8.0)

    support_zones = [z for z in zones if z.side == "support" and z.level < price]
    resist_zones = [z for z in zones if z.side == "resistance" and z.level > price]

    if not support_zones or not resist_zones:
        return None

    # Pick strongest support below and resistance above
    best_sup = max(support_zones, key=lambda z: z.strength)
    best_res = max(resist_zones, key=lambda z: z.strength)

    channel_width = best_res.level - best_sup.level
    channel_atr = channel_width / atr_value if atr_value > 0 else 99

    if channel_atr < min_channel_width_atr or channel_atr > max_channel_width_atr:
        return None

    # Where is price within the channel?
    position = (price - best_sup.level) / channel_width if channel_width > 0 else 0.5

    # Near support = long bias, near resistance = short bias
    if position <= 0.35:
        direction_bias = "long"
        modifier = 5
    elif position >= 0.65:
        direction_bias = "short"
        modifier = 5
    else:
        direction_bias = "neutral"
        modifier = 2

    combined_strength = (best_sup.strength + best_res.strength) / 2.0
    conf = min(1.0, combined_strength / 70.0)

    return PatternSignal(
        pattern="channel",
        direction_bias=direction_bias,
        confidence=round(conf, 3),
        zone_level=round(best_sup.level + channel_width * 0.5, 8),
        zone_strength=round(combined_strength, 1),
        description=f"Channel: support {best_sup.level:.6f} to resistance {best_res.level:.6f} (width {channel_atr:.1f} ATR, price at {position:.0%})",
        score_modifier=modifier,
        meta={
            "support_level": best_sup.level,
            "resistance_level": best_res.level,
            "channel_width_atr": round(channel_atr, 2),
            "position_pct": round(position, 3),
            "support_touches": best_sup.touch_count,
            "resistance_touches": best_res.touch_count,
        },
    )


def _detect_breakout(
    price: float,
    df: pd.DataFrame,
    zones: list[WickZone],
    atr_value: float,
    cfg: dict,
) -> list[PatternSignal]:
    """Detect breakout: current price closed through a strong wick zone.

    A breakout through resistance = bullish continuation signal.
    A breakdown through support = bearish continuation signal.
    """
    signals = []
    min_strength = float(cfg.get("breakout_min_zone_strength", 25) or 25)
    confirm_bars = int(cfg.get("breakout_confirm_bars", 2) or 2)

    for z in zones:
        if z.strength < min_strength:
            continue

        # Breakout above resistance
        if z.side == "resistance" and price > z.zone_high:
            # Check that we were below the zone recently
            recent = df.tail(confirm_bars + 3)
            was_below = any(float(row["close"]) < z.level for _, row in recent.head(3).iterrows())
            if not was_below:
                continue
            # Confirm: last N closes are above zone
            closes_above = sum(1 for _, row in recent.tail(confirm_bars).iterrows() if float(row["close"]) > z.zone_high)
            if closes_above < confirm_bars:
                continue

            excess_atr = (price - z.zone_high) / atr_value if atr_value > 0 else 0
            conf = min(1.0, (z.strength / 70.0) * min(1.0, z.touch_count / 2.0))
            signals.append(PatternSignal(
                pattern="breakout",
                direction_bias="long",
                confidence=round(conf, 3),
                zone_level=z.level,
                zone_strength=z.strength,
                description=f"Breakout above resistance {z.level:.6f} (strength {z.strength:.0f}, {z.touch_count} prior rejections)",
                score_modifier=min(10, int(conf * 12)),
                meta={"excess_atr": round(excess_atr, 2), "prior_rejections": z.touch_count},
            ))

        # Breakdown below support
        elif z.side == "support" and price < z.zone_low:
            recent = df.tail(confirm_bars + 3)
            was_above = any(float(row["close"]) > z.level for _, row in recent.head(3).iterrows())
            if not was_above:
                continue
            closes_below = sum(1 for _, row in recent.tail(confirm_bars).iterrows() if float(row["close"]) < z.zone_low)
            if closes_below < confirm_bars:
                continue

            excess_atr = (z.zone_low - price) / atr_value if atr_value > 0 else 0
            conf = min(1.0, (z.strength / 70.0) * min(1.0, z.touch_count / 2.0))
            signals.append(PatternSignal(
                pattern="breakout",
                direction_bias="short",
                confidence=round(conf, 3),
                zone_level=z.level,
                zone_strength=z.strength,
                description=f"Breakdown below support {z.level:.6f} (strength {z.strength:.0f}, {z.touch_count} prior bounces)",
                score_modifier=min(10, int(conf * 12)),
                meta={"excess_atr": round(excess_atr, 2), "prior_bounces": z.touch_count},
            ))

    return signals


def _detect_fakeout(
    price: float,
    df: pd.DataFrame,
    zones: list[WickZone],
    atr_value: float,
    cfg: dict,
) -> list[PatternSignal]:
    """Detect fakeout: price pierced a zone then snapped back.

    Fakeout above resistance = bearish (failed breakout, sellers won).
    Fakeout below support = bullish (stop hunt, buyers absorbed it).

    This is complementary to the micro-sweep detector but works on any timeframe
    and uses the multi-TF zone strength for conviction.
    """
    signals = []
    min_strength = float(cfg.get("fakeout_min_zone_strength", 20) or 20)

    if len(df) < 5:
        return signals

    recent = df.tail(5)

    for z in zones:
        if z.strength < min_strength:
            continue

        # Fakeout below support (bullish): recent bar wicked below zone, current close above
        if z.side == "support":
            for _, row in recent.iterrows():
                bar_low = float(row["low"])
                bar_close = float(row["close"])
                if bar_low < z.zone_low and bar_close > z.level:
                    # Wick pierced below support but closed back above
                    conf = min(1.0, (z.strength / 60.0) * min(1.0, z.touch_count / 2.0))
                    signals.append(PatternSignal(
                        pattern="fakeout",
                        direction_bias="long",
                        confidence=round(conf, 3),
                        zone_level=z.level,
                        zone_strength=z.strength,
                        description=f"Fakeout below support {z.level:.6f} (stop hunt absorbed, {z.touch_count} prior bounces)",
                        score_modifier=min(8, int(conf * 10)),
                        meta={"wick_low": bar_low, "reclaim_close": bar_close, "zone_touches": z.touch_count},
                    ))
                    break  # one signal per zone

        # Fakeout above resistance (bearish)
        elif z.side == "resistance":
            for _, row in recent.iterrows():
                bar_high = float(row["high"])
                bar_close = float(row["close"])
                if bar_high > z.zone_high and bar_close < z.level:
                    conf = min(1.0, (z.strength / 60.0) * min(1.0, z.touch_count / 2.0))
                    signals.append(PatternSignal(
                        pattern="fakeout",
                        direction_bias="short",
                        confidence=round(conf, 3),
                        zone_level=z.level,
                        zone_strength=z.strength,
                        description=f"Fakeout above resistance {z.level:.6f} (failed breakout, {z.touch_count} prior rejections)",
                        score_modifier=min(8, int(conf * 10)),
                        meta={"wick_high": bar_high, "reject_close": bar_close, "zone_touches": z.touch_count},
                    ))
                    break

    return signals


def _update_pattern_memory(
    state: dict,
    patterns: list[PatternSignal],
    price: float,
    zones: list[WickZone],
) -> None:
    """Persist pattern state across bot cycles for cross-bar awareness.

    Stores in state["_pattern_memory"] so the next cycle can see
    what patterns were forming and track progression.
    """
    memory = state.get("_pattern_memory") or {}

    # Store current zone interaction summary
    zone_summary = []
    for z in zones[:5]:
        dist = abs(price - z.level)
        zone_summary.append({
            "level": z.level,
            "side": z.side,
            "strength": z.strength,
            "touches": z.touch_count,
            "dist": round(dist, 8),
        })

    # Store active patterns
    active_patterns = []
    for p in patterns:
        active_patterns.append({
            "pattern": p.pattern,
            "bias": p.direction_bias,
            "confidence": p.confidence,
            "level": p.zone_level,
        })

    memory["last_zones"] = zone_summary
    memory["last_patterns"] = active_patterns
    memory["last_price"] = price

    state["_pattern_memory"] = memory
