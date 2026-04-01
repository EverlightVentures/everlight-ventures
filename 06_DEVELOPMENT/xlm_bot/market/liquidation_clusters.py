"""Liquidation cluster analysis -- proxy heatmap from observed force orders.

Builds estimated liquidation zones by clustering recent liquidation events
by price level.  Provides magnet bias (which side has stronger pull) and
sweep detection (price entering/exiting a cluster zone).

Separation of concerns:
  - liquidation_feed.py = raw WebSocket event collection + snapshots
  - liquidation_clusters.py = analysis layer (this file)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class LiquidationCluster:
    """A price band where liquidations have concentrated."""
    center_price: float
    band_low: float
    band_high: float
    event_count: int
    total_notional_usd: float
    longs_notional: float
    shorts_notional: float
    strength: float  # 0-100 normalized
    distance_atr: float
    side: str  # "above" or "below" current price


@dataclass
class MagnetBias:
    """Which side of price has the strongest liquidation pull."""
    side: str  # "above", "below", "balanced"
    score: float  # 0-100
    strongest_above: LiquidationCluster | None
    strongest_below: LiquidationCluster | None


@dataclass
class SweepState:
    """Tracks whether price is sweeping through a liquidation cluster."""
    status: str  # "none", "in_progress", "completed"
    sweep_side: str  # "long" (sweeping longs below) or "short" (sweeping shorts above) or ""
    cluster_center: float
    sweep_depth_atr: float
    bars_since_sweep: int
    wick_detected: bool
    touched_cluster: bool = False
    flushed_cluster: bool = False


@dataclass
class LiquidationIntelligence:
    """Full liquidation analysis result passed to strategy engine + Claude."""
    clusters_above: list[LiquidationCluster]
    clusters_below: list[LiquidationCluster]
    magnet: MagnetBias
    sweep: SweepState
    wick_score: float  # 0-100 from wick analysis
    reclaim_confirmed: bool
    rejection_confirmed: bool
    sweep_level: float
    funding_lean: str  # "long", "short", "neutral"
    raw_bias: str  # from liquidation_feed snapshot
    cluster_side: str = "balanced"
    cluster_strength: float = 0.0
    distance_to_cluster_atr: float | None = None
    next_pool_side: str = "balanced"
    touched_cluster: bool = False
    flushed_cluster: bool = False
    absorbed_reclaim: bool = False
    absorbed_reject: bool = False


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        pass
    return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def build_clusters(
    snapshot: dict[str, Any],
    current_price: float,
    atr_value: float,
    config: dict | None = None,
) -> list[LiquidationCluster]:
    """Build liquidation clusters from raw liquidation feed snapshot.

    Groups recent liquidation events into price bands of cluster_resolution_atr
    width, then scores each cluster by event count and notional volume.
    """
    cfg = config or {}
    resolution_atr = float(cfg.get("cluster_resolution_atr", 0.5) or 0.5)
    min_events = int(cfg.get("min_cluster_events", 3) or 3)
    min_notional = float(cfg.get("min_cluster_notional", 5000) or 5000)
    max_distance_atr = float(cfg.get("magnet_distance_max_atr", 5.0) or 5.0)

    if atr_value <= 0 or current_price <= 0:
        return []

    band_width = atr_value * resolution_atr
    if band_width <= 0:
        return []

    clusters: list[LiquidationCluster] = []
    recent_events = snapshot.get("recent_events") if isinstance(snapshot.get("recent_events"), list) else []
    buckets: dict[int, dict[str, float]] = {}

    for event in recent_events:
        if not isinstance(event, dict):
            continue
        price = float(event.get("price") or 0.0)
        notional = float(event.get("notional_usd") or 0.0)
        if price <= 0 or notional <= 0:
            continue
        bucket_id = int(round(price / band_width))
        bucket = buckets.setdefault(bucket_id, {"events": 0.0, "notional": 0.0, "longs": 0.0, "shorts": 0.0})
        bucket["events"] += 1.0
        bucket["notional"] += notional
        if str(event.get("liquidated_side") or "").lower() == "longs":
            bucket["longs"] += notional
        elif str(event.get("liquidated_side") or "").lower() == "shorts":
            bucket["shorts"] += notional

    for bucket_id, bucket in buckets.items():
        event_count = int(bucket["events"])
        notional = float(bucket["notional"])
        if event_count < min_events or notional < min_notional:
            continue
        center = bucket_id * band_width
        distance = (center - current_price) / atr_value if atr_value > 0 else 0.0
        if abs(distance) > max_distance_atr:
            continue
        side = "above" if center > current_price else "below"
        band_low = center - (band_width / 2)
        band_high = center + (band_width / 2)
        strength = min(100.0, (notional / max(min_notional, 1.0)) * 18.0 + event_count * 6.0)
        clusters.append(
            LiquidationCluster(
                center_price=round(center, 6),
                band_low=round(band_low, 6),
                band_high=round(band_high, 6),
                event_count=event_count,
                total_notional_usd=round(notional, 2),
                longs_notional=round(float(bucket["longs"]), 2),
                shorts_notional=round(float(bucket["shorts"]), 2),
                strength=round(strength, 1),
                distance_atr=round(abs(distance), 2),
                side=side,
            )
        )

    if not clusters:
        # Fallback for old snapshots that only have window aggregates.
        last_event = snapshot.get("last_event") or {}
        last_price = float(last_event.get("price") or 0)
        for window_key in ("window_1m", "window_5m", "window_15m"):
            w = snapshot.get(window_key) or {}
            event_count = int(w.get("events", 0))
            notional = float(w.get("notional_usd", 0))
            longs_usd = float(w.get("longs_usd", 0))
            shorts_usd = float(w.get("shorts_usd", 0))
            if event_count < min_events or notional < min_notional:
                continue
            center = last_price if last_price > 0 else current_price
            distance = (center - current_price) / atr_value if atr_value > 0 else 0.0
            if abs(distance) > max_distance_atr:
                continue
            side = "above" if center > current_price else "below"
            band_low = center - (band_width / 2)
            band_high = center + (band_width / 2)
            strength = min(100.0, (notional / max(min_notional, 1.0)) * 20.0 + event_count * 5.0)
            clusters.append(
                LiquidationCluster(
                    center_price=round(center, 6),
                    band_low=round(band_low, 6),
                    band_high=round(band_high, 6),
                    event_count=event_count,
                    total_notional_usd=round(notional, 2),
                    longs_notional=round(longs_usd, 2),
                    shorts_notional=round(shorts_usd, 2),
                    strength=round(strength, 1),
                    distance_atr=round(abs(distance), 2),
                    side=side,
                )
            )

    clusters.sort(key=lambda c: (c.distance_atr, -c.strength, -c.total_notional_usd))
    return clusters[:6]


def compute_magnet_bias(
    clusters: list[LiquidationCluster],
    current_price: float,
    price_velocity: float = 0.0,
) -> MagnetBias:
    """Determine which side has stronger liquidation pull (magnet effect).

    Considers cluster strength, distance (closer = stronger), and
    price direction (moving toward = confirming).
    """
    above = [c for c in clusters if c.side == "above"]
    below = [c for c in clusters if c.side == "below"]

    best_above = max(above, key=lambda c: c.strength, default=None)
    best_below = max(below, key=lambda c: c.strength, default=None)

    score_above = 0.0
    score_below = 0.0

    if best_above:
        dist_factor = max(0.2, 1.0 - (best_above.distance_atr / 5.0))
        score_above = best_above.strength * dist_factor
        if price_velocity > 0:
            score_above *= 1.2

    if best_below:
        dist_factor = max(0.2, 1.0 - (best_below.distance_atr / 5.0))
        score_below = best_below.strength * dist_factor
        if price_velocity < 0:
            score_below *= 1.2

    total = score_above + score_below
    if total <= 0:
        return MagnetBias("balanced", 0, best_above, best_below)

    ratio = max(score_above, score_below) / total
    if ratio < 0.6:
        side = "balanced"
        score = 50 * ratio
    elif score_above > score_below:
        side = "above"
        score = min(100, score_above)
    else:
        side = "below"
        score = min(100, score_below)

    return MagnetBias(side, round(score, 1), best_above, best_below)


def detect_cluster_sweep(
    clusters: list[LiquidationCluster],
    current_price: float,
    candle_low: float,
    candle_high: float,
    candle_close: float,
    atr_value: float,
    config: dict | None = None,
    prev_sweep_state: dict | None = None,
) -> SweepState:
    """Detect if price is sweeping through or has swept a liquidation cluster.

    A sweep occurs when price enters a cluster zone (center +/- zone_atr)
    then closes back outside the zone (completed sweep).
    """
    cfg = config or {}
    zone_atr = float(cfg.get("sweep_zone_atr", 0.25) or 0.25)
    zone_width = atr_value * zone_atr

    prev = prev_sweep_state or {}
    prev_status = prev.get("status", "none")
    prev_bars = int(prev.get("bars_since_sweep", 0))

    for cluster in clusters:
        zone_low = cluster.center_price - zone_width
        zone_high = cluster.center_price + zone_width

        entered_zone = False
        if cluster.side == "below":
            entered_zone = candle_low <= zone_high
        elif cluster.side == "above":
            entered_zone = candle_high >= zone_low

        if not entered_zone:
            continue

        closed_outside = False
        if cluster.side == "below":
            closed_outside = candle_close > zone_high
        elif cluster.side == "above":
            closed_outside = candle_close < zone_low

        if cluster.side == "below":
            depth = (zone_low - candle_low) / atr_value if atr_value > 0 else 0
        else:
            depth = (candle_high - zone_high) / atr_value if atr_value > 0 else 0

        sweep_side = "long" if cluster.side == "below" else "short"

        if closed_outside and entered_zone:
            return SweepState(
                status="completed",
                sweep_side=sweep_side,
                cluster_center=cluster.center_price,
                sweep_depth_atr=round(max(0, depth), 2),
                bars_since_sweep=0,
                wick_detected=False,
                touched_cluster=True,
                flushed_cluster=bool(max(0, depth) > 0.02),
            )
        elif entered_zone:
            return SweepState(
                status="in_progress",
                sweep_side=sweep_side,
                cluster_center=cluster.center_price,
                sweep_depth_atr=round(max(0, depth), 2),
                bars_since_sweep=0,
                wick_detected=False,
                touched_cluster=True,
                flushed_cluster=bool(max(0, depth) > 0.02),
            )

    # No active sweep -- check if previous sweep is aging
    if prev_status == "completed":
        return SweepState(
            status="completed",
            sweep_side=prev.get("sweep_side", ""),
            cluster_center=float(prev.get("cluster_center", 0)),
            sweep_depth_atr=float(prev.get("sweep_depth_atr", 0)),
            bars_since_sweep=prev_bars + 1,
            wick_detected=bool(prev.get("wick_detected", False)),
            touched_cluster=bool(prev.get("touched_cluster", False)),
            flushed_cluster=bool(prev.get("flushed_cluster", False)),
        )

    return SweepState(
        status="none",
        sweep_side="",
        cluster_center=0.0,
        sweep_depth_atr=0.0,
        bars_since_sweep=0,
        wick_detected=False,
        touched_cluster=False,
        flushed_cluster=False,
    )


def build_intelligence(
    snapshot: dict[str, Any],
    current_price: float,
    atr_value: float,
    candle_low: float,
    candle_high: float,
    candle_close: float,
    price_velocity: float = 0.0,
    funding_rate: float = 0.0,
    wick_score: float = 0.0,
    reclaim_confirmed: bool = False,
    rejection_confirmed: bool = False,
    sweep_level: float = 0.0,
    config: dict | None = None,
    prev_sweep_state: dict | None = None,
) -> LiquidationIntelligence:
    """Build complete liquidation intelligence from feed snapshot + market data.

    This is the main entry point called by the strategy engine each cycle.
    """
    clusters = build_clusters(snapshot, current_price, atr_value, config)
    above = [c for c in clusters if c.side == "above"]
    below = [c for c in clusters if c.side == "below"]

    magnet = compute_magnet_bias(clusters, current_price, price_velocity)
    sweep = detect_cluster_sweep(
        clusters, current_price, candle_low, candle_high,
        candle_close, atr_value, config, prev_sweep_state,
    )

    if funding_rate > 0.0001:
        funding_lean = "long"
    elif funding_rate < -0.0001:
        funding_lean = "short"
    else:
        funding_lean = "neutral"

    cluster_side = "balanced"
    cluster_strength = 0.0
    distance_to_cluster_atr = None
    next_pool_side = magnet.side
    if above and below:
        strength_gap = abs(above[0].strength - below[0].strength)
        cluster_side = "balanced" if strength_gap < 12 else ("above" if above[0].strength > below[0].strength else "below")
    elif above:
        cluster_side = "above"
    elif below:
        cluster_side = "below"

    relevant = None
    if sweep.sweep_side == "long" and below:
        relevant = below[0]
        next_pool_side = "above" if above else "balanced"
    elif sweep.sweep_side == "short" and above:
        relevant = above[0]
        next_pool_side = "below" if below else "balanced"
    elif magnet.side == "above" and above:
        relevant = above[0]
    elif magnet.side == "below" and below:
        relevant = below[0]
    elif above or below:
        relevant = (above or below)[0]
    if relevant:
        cluster_strength = float(relevant.strength)
        distance_to_cluster_atr = float(relevant.distance_atr)

    return LiquidationIntelligence(
        clusters_above=above,
        clusters_below=below,
        magnet=magnet,
        sweep=sweep,
        wick_score=wick_score,
        reclaim_confirmed=reclaim_confirmed,
        rejection_confirmed=rejection_confirmed,
        sweep_level=sweep_level or sweep.cluster_center,
        funding_lean=funding_lean,
        raw_bias=str(snapshot.get("bias", "BALANCED")),
        cluster_side=cluster_side,
        cluster_strength=round(cluster_strength, 1),
        distance_to_cluster_atr=round(distance_to_cluster_atr, 2) if distance_to_cluster_atr is not None else None,
        next_pool_side=next_pool_side,
        touched_cluster=sweep.touched_cluster,
        flushed_cluster=sweep.flushed_cluster,
        absorbed_reclaim=bool(reclaim_confirmed and sweep.status in {"completed", "in_progress"}),
        absorbed_reject=bool(rejection_confirmed and sweep.status in {"completed", "in_progress"}),
    )


def format_for_prompt(intel: LiquidationIntelligence) -> str:
    """Format liquidation intelligence for Claude's master directive prompt."""
    lines = []

    if intel.clusters_above:
        c = intel.clusters_above[0]
        lines.append(
            f"Nearest cluster ABOVE: ${c.center_price:.6f} "
            f"(strength: {c.strength:.0f}/100, distance: {c.distance_atr:.1f} ATR, "
            f"notional: ${c.total_notional_usd:,.0f})"
        )
    else:
        lines.append("Nearest cluster ABOVE: none detected")

    if intel.clusters_below:
        c = intel.clusters_below[0]
        lines.append(
            f"Nearest cluster BELOW: ${c.center_price:.6f} "
            f"(strength: {c.strength:.0f}/100, distance: {c.distance_atr:.1f} ATR, "
            f"notional: ${c.total_notional_usd:,.0f})"
        )
    else:
        lines.append("Nearest cluster BELOW: none detected")

    lines.append(f"Magnet bias: {intel.magnet.side.upper()} (score: {intel.magnet.score:.0f}/100)")

    lines.append(
        f"Sweep status: {intel.sweep.status.upper()} "
        f"(side: {intel.sweep.sweep_side.upper() or 'N/A'}, "
        f"depth: {intel.sweep.sweep_depth_atr:.1f} ATR)"
    )
    lines.append(
        f"Cluster side: {intel.cluster_side.upper()} | "
        f"strength: {intel.cluster_strength:.0f}/100 | "
        f"distance: {intel.distance_to_cluster_atr if intel.distance_to_cluster_atr is not None else '?'} ATR"
    )
    lines.append(
        f"Touched cluster: {intel.touched_cluster} | Flushed through: {intel.flushed_cluster} | "
        f"Next pool: {intel.next_pool_side.upper()}"
    )
    if intel.sweep.status == "completed":
        lines.append(f"  Bars since sweep: {intel.sweep.bars_since_sweep}")

    lines.append(f"Wick score: {intel.wick_score:.0f}/100")
    if intel.reclaim_confirmed:
        lines.append(f"Reclaim CONFIRMED at ${intel.sweep_level:.6f}")
    elif intel.rejection_confirmed:
        lines.append(f"Rejection CONFIRMED at ${intel.sweep_level:.6f}")

    lines.append(f"Funding lean: {intel.funding_lean.upper()} (crowd positioned {intel.funding_lean})")
    lines.append(f"Raw liquidation bias: {intel.raw_bias}")

    return "\n".join(lines)


def to_dict(intel: LiquidationIntelligence) -> dict[str, Any]:
    """Serialize intelligence to dict for caching/logging."""
    return {
        "clusters_above": [
            {"center": c.center_price, "strength": c.strength, "distance_atr": c.distance_atr,
             "notional": c.total_notional_usd}
            for c in intel.clusters_above
        ],
        "clusters_below": [
            {"center": c.center_price, "strength": c.strength, "distance_atr": c.distance_atr,
             "notional": c.total_notional_usd}
            for c in intel.clusters_below
        ],
        "magnet_side": intel.magnet.side,
        "magnet_score": intel.magnet.score,
        "sweep_status": intel.sweep.status,
        "sweep_side": intel.sweep.sweep_side,
        "sweep_depth_atr": intel.sweep.sweep_depth_atr,
        "bars_since_sweep": intel.sweep.bars_since_sweep,
        "touched_cluster": intel.sweep.touched_cluster,
        "flushed_cluster": intel.sweep.flushed_cluster,
        "wick_score": intel.wick_score,
        "reclaim_confirmed": intel.reclaim_confirmed,
        "rejection_confirmed": intel.rejection_confirmed,
        "sweep_level": intel.sweep_level,
        "funding_lean": intel.funding_lean,
        "raw_bias": intel.raw_bias,
        "cluster_side": intel.cluster_side,
        "cluster_strength": intel.cluster_strength,
        "distance_to_cluster_atr": intel.distance_to_cluster_atr,
        "next_pool_side": intel.next_pool_side,
        "absorbed_reclaim": intel.absorbed_reclaim,
        "absorbed_reject": intel.absorbed_reject,
    }
