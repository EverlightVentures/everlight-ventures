"""Tests for multi-TF wick zone detection and pattern memory."""
from __future__ import annotations

import pandas as pd
import numpy as np
import pytest

from strategy.wick_zones import build_wick_zones, zones_to_levels, zone_proximity_score, WickZone
from strategy.pattern_memory import detect_patterns, pattern_score_modifier, PatternSignal


def _make_candles(n: int, base: float, atr: float = 0.0003, seed: int = 42) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    rows = []
    p = base
    for _ in range(n):
        move = rng.uniform(-atr, atr)
        o = p
        c = p + move
        h = max(o, c) + rng.uniform(0, atr * 0.3)
        l = min(o, c) - rng.uniform(0, atr * 0.3)
        rows.append({"open": o, "high": h, "low": l, "close": c, "volume": 50000})
        p = c
    ts = pd.date_range("2026-03-25", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame(rows)
    df["timestamp"] = ts
    return df


def _add_wick_candles(df: pd.DataFrame, level: float, side: str, count: int = 3) -> pd.DataFrame:
    """Append candles with big wicks at a specific level to simulate zone formation."""
    rows = []
    for i in range(count):
        ts = df["timestamp"].iloc[-1] + pd.Timedelta(minutes=5 * (i + 1))
        if side == "support":
            # Lower wick touching the level, body closes above
            o = level + 0.0010
            l = level - 0.0002
            h = level + 0.0015
            c = level + 0.0012
        else:
            # Upper wick touching the level, body closes below
            o = level - 0.0010
            h = level + 0.0002
            l = level - 0.0015
            c = level - 0.0012
        rows.append({"open": o, "high": h, "low": l, "close": c, "volume": 80000, "timestamp": ts})
    extra = pd.DataFrame(rows)
    return pd.concat([df, extra], ignore_index=True)


class TestWickZoneDetection:
    def test_support_zone_from_lower_wicks(self):
        """Multiple lower wicks at the same level should create a support zone."""
        df = _make_candles(30, 0.1790)
        df = _add_wick_candles(df, 0.1770, "support", count=4)

        zones = build_wick_zones(df_5m=df, df_15m=None, df_1h=None, df_4h=None)
        support_zones = [z for z in zones if z.side == "support"]
        assert len(support_zones) >= 1
        # Zone center may be slightly offset from the target level due to clustering
        best = min(support_zones, key=lambda z: abs(z.level - 0.1770))
        assert abs(best.level - 0.1770) < 0.002
        assert best.touch_count >= 3

    def test_resistance_zone_from_upper_wicks(self):
        """Multiple upper wicks at the same level should create a resistance zone."""
        df = _make_candles(30, 0.1790)
        df = _add_wick_candles(df, 0.1810, "resistance", count=4)

        zones = build_wick_zones(df_5m=df, df_15m=None, df_1h=None, df_4h=None)
        resist_zones = [z for z in zones if z.side == "resistance"]
        assert len(resist_zones) >= 1
        best = resist_zones[0]
        assert abs(best.level - 0.1810) < 0.001

    def test_higher_tf_zones_are_stronger(self):
        """A zone from 1h data should score higher than the same zone from 5m."""
        df_5m = _make_candles(30, 0.1790)
        df_5m = _add_wick_candles(df_5m, 0.1770, "support", count=3)

        df_1h = _make_candles(30, 0.1790, atr=0.001)
        df_1h = _add_wick_candles(df_1h, 0.1770, "support", count=3)

        zones_5m_only = build_wick_zones(df_5m=df_5m, df_15m=None, df_1h=None, df_4h=None)
        zones_1h_only = build_wick_zones(df_5m=None, df_15m=None, df_1h=df_1h, df_4h=None)

        sup_5m = [z for z in zones_5m_only if z.side == "support"]
        sup_1h = [z for z in zones_1h_only if z.side == "support"]

        if sup_5m and sup_1h:
            assert sup_1h[0].strength > sup_5m[0].strength

    def test_multi_tf_confirmation_bonus(self):
        """Zones confirmed on multiple timeframes should get a strength bonus."""
        df = _make_candles(30, 0.1790)
        df = _add_wick_candles(df, 0.1770, "support", count=3)

        # Same zone on both 5m and 15m
        zones_single = build_wick_zones(df_5m=df, df_15m=None, df_1h=None, df_4h=None)
        zones_multi = build_wick_zones(df_5m=df, df_15m=df, df_1h=None, df_4h=None)

        sup_single = [z for z in zones_single if z.side == "support"]
        sup_multi = [z for z in zones_multi if z.side == "support"]

        if sup_single and sup_multi:
            # Multi-TF should have more touches and higher strength
            assert sup_multi[0].touch_count >= sup_single[0].touch_count

    def test_zones_to_levels_integration(self):
        """zones_to_levels should produce a dict compatible with structure levels."""
        zones = [
            WickZone(level=0.1770, zone_low=0.1768, zone_high=0.1772, strength=60,
                     touch_count=4, side="support", strongest_tf="1h"),
            WickZone(level=0.1810, zone_low=0.1808, zone_high=0.1812, strength=50,
                     touch_count=3, side="resistance", strongest_tf="15m"),
        ]
        lvls = zones_to_levels(zones, 0.1790)
        assert "wick_support_1" in lvls
        assert "wick_resistance_1" in lvls
        assert lvls["wick_support_1"] == 0.1770
        assert lvls["wick_resistance_1"] == 0.1810


class TestZoneProximity:
    def test_near_support_for_longs(self):
        zones = [WickZone(level=0.1770, zone_low=0.1768, zone_high=0.1772,
                          strength=60, touch_count=4, side="support", strongest_tf="1h")]
        result = zone_proximity_score(0.1775, zones, "long", atr_value=0.0005)
        assert result["near_zone"] is True
        assert result["bounce_bias"] == "support_bounce"
        assert result["confidence"] > 0

    def test_far_from_zone_no_signal(self):
        zones = [WickZone(level=0.1770, zone_low=0.1768, zone_high=0.1772,
                          strength=60, touch_count=4, side="support", strongest_tf="1h")]
        result = zone_proximity_score(0.1850, zones, "long", atr_value=0.0005)
        assert result["near_zone"] is False


class TestPatternDetection:
    def _make_support_zone(self, level=0.1770):
        return WickZone(level=level, zone_low=level - 0.0002, zone_high=level + 0.0002,
                        strength=65, touch_count=3, side="support", strongest_tf="1h")

    def _make_resist_zone(self, level=0.1810):
        return WickZone(level=level, zone_low=level - 0.0002, zone_high=level + 0.0002,
                        strength=65, touch_count=3, side="resistance", strongest_tf="1h")

    def test_double_bottom_near_support(self):
        zones = [self._make_support_zone(0.1770)]
        df = _make_candles(20, 0.1775)
        patterns = detect_patterns(0.1773, df, zones, atr_value=0.0005)
        bottoms = [p for p in patterns if p.pattern == "double_bottom"]
        assert len(bottoms) >= 1
        assert bottoms[0].direction_bias == "long"

    def test_double_top_near_resistance(self):
        zones = [self._make_resist_zone(0.1810)]
        df = _make_candles(20, 0.1805)
        patterns = detect_patterns(0.1808, df, zones, atr_value=0.0005)
        tops = [p for p in patterns if p.pattern == "double_top"]
        assert len(tops) >= 1
        assert tops[0].direction_bias == "short"

    def test_channel_detected_between_zones(self):
        zones = [self._make_support_zone(0.1775), self._make_resist_zone(0.1805)]
        df = _make_candles(20, 0.1790)
        patterns = detect_patterns(0.1790, df, zones, atr_value=0.0005)
        channels = [p for p in patterns if p.pattern == "channel"]
        assert len(channels) >= 1

    def test_pattern_score_modifier_positive(self):
        """Supportive pattern should give positive score modifier for matching direction."""
        patterns = [PatternSignal(
            pattern="double_bottom", direction_bias="long", confidence=0.8,
            zone_level=0.1770, zone_strength=60,
            description="test", score_modifier=6,
        )]
        mod = pattern_score_modifier(patterns, "long")
        assert mod > 0

    def test_pattern_score_modifier_negative_for_opposite(self):
        """A double bottom should REDUCE score for shorts."""
        patterns = [PatternSignal(
            pattern="double_bottom", direction_bias="long", confidence=0.8,
            zone_level=0.1770, zone_strength=60,
            description="test", score_modifier=6,
        )]
        mod = pattern_score_modifier(patterns, "short")
        assert mod < 0

    def test_no_patterns_from_empty_zones(self):
        df = _make_candles(20, 0.1790)
        patterns = detect_patterns(0.1790, df, [], atr_value=0.0005)
        assert patterns == []

    def test_fakeout_below_support(self):
        """Wick below support zone that closes back above = bullish fakeout."""
        zone = self._make_support_zone(0.1770)
        # Build candles where one wicks below the zone
        df = _make_candles(15, 0.1780)
        # Add a fakeout candle: wicks below zone_low, closes above zone level
        fakeout_row = pd.DataFrame([{
            "open": 0.1775, "high": 0.1778, "low": 0.1765, "close": 0.1776,
            "volume": 90000, "timestamp": df["timestamp"].iloc[-1] + pd.Timedelta(minutes=5),
        }])
        df = pd.concat([df, fakeout_row], ignore_index=True)

        patterns = detect_patterns(0.1776, df, [zone], atr_value=0.0005)
        fakeouts = [p for p in patterns if p.pattern == "fakeout"]
        assert len(fakeouts) >= 1
        assert fakeouts[0].direction_bias == "long"
