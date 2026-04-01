"""Contract order book context for the XLM bot.

Adds a cheap, exchange-native microstructure signal using the exact traded
product instead of relying only on candle-shape proxies.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class OrderBookSnapshot:
    timestamp: str = ""
    product_id: str = ""
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    mid_price: Optional[float] = None
    spread_bps: Optional[float] = None
    bid_depth_topn: Optional[float] = None
    ask_depth_topn: Optional[float] = None
    imbalance_ratio: Optional[float] = None
    depth_bias: str = "UNKNOWN"
    mid_move_bps: Optional[float] = None
    bid_replenishment_ratio: Optional[float] = None
    ask_replenishment_ratio: Optional[float] = None
    absorption_bias: str = "NEUTRAL"
    spoof_risk: Optional[float] = None
    spoof_side: str = "NONE"
    depth_flip: bool = False
    levels_sampled: int = 0
    history_samples: int = 0
    history_bias: str = "UNKNOWN"
    history_avg_imbalance: Optional[float] = None
    history_absorption_rate: Optional[float] = None
    history_spoof_rate: Optional[float] = None
    history_depth_flips: int = 0
    history_mid_move_bps_avg: Optional[float] = None


@dataclass
class OrderBookModResult:
    bonus: int = 0
    reasons: list[str] = field(default_factory=list)


class OrderBookContext:
    """Caches the most recent order book snapshot for the contract."""

    def __init__(self, api, product_id: str, cache_dir: Path, config: dict | None = None):
        self._api = api
        self._product_id = product_id
        self._cache_dir = Path(cache_dir)
        cfg = config or {}
        self._stale_seconds = float(cfg.get("stale_seconds", 8.0) or 8.0)
        self._depth_levels = max(1, int(cfg.get("depth_levels", 10) or 10))
        self._history_limit = max(10, int(cfg.get("history_limit", 180) or 180))
        self._last_snap: Optional[OrderBookSnapshot] = self._load_cached_snapshot()
        self._last_fetch_ts = 0.0
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self) -> Optional[OrderBookSnapshot]:
        now = time.time()
        if self._last_snap and (now - self._last_fetch_ts) < self._stale_seconds:
            return self._last_snap

        raw = self._api.get_orderbook(self._product_id)
        snap = self._build_snapshot(raw)
        if snap is None:
            return self._last_snap
        history_summary = self._update_history(snap)
        snap.history_samples = int(history_summary.get("samples") or 0)
        snap.history_bias = str(history_summary.get("bias") or "UNKNOWN")
        snap.history_avg_imbalance = _round(_flt(history_summary.get("avg_imbalance")), 4)
        snap.history_absorption_rate = _round(_flt(history_summary.get("absorption_rate")), 3)
        snap.history_spoof_rate = _round(_flt(history_summary.get("spoof_rate")), 3)
        snap.history_depth_flips = int(history_summary.get("depth_flips") or 0)
        snap.history_mid_move_bps_avg = _round(_flt(history_summary.get("mid_move_bps_avg")), 2)
        self._last_snap = snap
        self._last_fetch_ts = now
        self._persist(snap)
        return snap

    def as_dict(self) -> dict:
        if self._last_snap:
            return asdict(self._last_snap)
        return {}

    def _build_snapshot(self, raw: dict | None) -> Optional[OrderBookSnapshot]:
        if not isinstance(raw, dict):
            return None
        payload = raw.get("pricebook") if isinstance(raw.get("pricebook"), dict) else raw
        bids = self._parse_levels(payload.get("bids"))
        asks = self._parse_levels(payload.get("asks"))
        if not bids and not asks:
            return None

        prev = self._last_snap
        bid_depth = sum(level["size"] for level in bids[: self._depth_levels])
        ask_depth = sum(level["size"] for level in asks[: self._depth_levels])
        total_depth = bid_depth + ask_depth
        imbalance = (bid_depth / total_depth) if total_depth > 0 else None
        best_bid = bids[0]["price"] if bids else None
        best_ask = asks[0]["price"] if asks else None
        mid = None
        spread_bps = None
        if best_bid and best_ask and best_bid > 0 and best_ask > 0:
            mid = (best_bid + best_ask) / 2.0
            if mid > 0:
                spread_bps = ((best_ask - best_bid) / mid) * 10000.0

        depth_bias = "UNKNOWN"
        if imbalance is not None:
            if imbalance >= 0.58:
                depth_bias = "BID_HEAVY"
            elif imbalance <= 0.42:
                depth_bias = "ASK_HEAVY"
            else:
                depth_bias = "BALANCED"

        prev_mid = _flt(getattr(prev, "mid_price", None)) if prev else None
        prev_bid_depth = _flt(getattr(prev, "bid_depth_topn", None)) if prev else None
        prev_ask_depth = _flt(getattr(prev, "ask_depth_topn", None)) if prev else None
        prev_bias = str(getattr(prev, "depth_bias", "UNKNOWN")) if prev else "UNKNOWN"
        prev_imbalance = _flt(getattr(prev, "imbalance_ratio", None)) if prev else None

        mid_move_bps = None
        if mid and prev_mid and prev_mid > 0:
            mid_move_bps = ((mid - prev_mid) / prev_mid) * 10000.0

        bid_replenishment = (bid_depth / prev_bid_depth) if prev_bid_depth and prev_bid_depth > 0 else None
        ask_replenishment = (ask_depth / prev_ask_depth) if prev_ask_depth and prev_ask_depth > 0 else None
        depth_flip = (
            prev_bias in {"BID_HEAVY", "ASK_HEAVY"}
            and depth_bias in {"BID_HEAVY", "ASK_HEAVY"}
            and prev_bias != depth_bias
        )

        absorption_bias = "NEUTRAL"
        if mid_move_bps is not None and imbalance is not None:
            if mid_move_bps <= -2.0 and imbalance >= 0.55 and (bid_replenishment or 0.0) >= 0.92:
                absorption_bias = "BID_ABSORBING"
            elif mid_move_bps >= 2.0 and imbalance <= 0.45 and (ask_replenishment or 0.0) >= 0.92:
                absorption_bias = "ASK_ABSORBING"
            elif depth_bias == "BALANCED":
                absorption_bias = "BALANCED"

        spoof_risk, spoof_side = _detect_spoof_risk(
            prev_bias=prev_bias,
            depth_bias=depth_bias,
            prev_bid_depth=prev_bid_depth,
            prev_ask_depth=prev_ask_depth,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            prev_imbalance=prev_imbalance,
            imbalance=imbalance,
            mid_move_bps=mid_move_bps,
        )

        return OrderBookSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            product_id=self._product_id,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=_round(mid, 6),
            spread_bps=_round(spread_bps, 2),
            bid_depth_topn=_round(bid_depth, 4),
            ask_depth_topn=_round(ask_depth, 4),
            imbalance_ratio=_round(imbalance, 4),
            depth_bias=depth_bias,
            mid_move_bps=_round(mid_move_bps, 2),
            bid_replenishment_ratio=_round(bid_replenishment, 3),
            ask_replenishment_ratio=_round(ask_replenishment, 3),
            absorption_bias=absorption_bias,
            spoof_risk=_round(spoof_risk, 3),
            spoof_side=spoof_side,
            depth_flip=depth_flip,
            levels_sampled=min(max(len(bids), len(asks)), self._depth_levels),
        )

    @staticmethod
    def _parse_levels(levels: Any) -> list[dict[str, float]]:
        out: list[dict[str, float]] = []
        if not isinstance(levels, list):
            return out
        for raw in levels:
            price = None
            size = None
            if isinstance(raw, dict):
                price = _flt(raw.get("price") or raw.get("px"))
                size = _flt(raw.get("size") or raw.get("qty") or raw.get("quantity"))
            elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                price = _flt(raw[0])
                size = _flt(raw[1])
            if price is None or size is None or price <= 0 or size <= 0:
                continue
            out.append({"price": price, "size": size})
        return out

    def _persist(self, snap: OrderBookSnapshot) -> None:
        payload = asdict(snap)
        path = self._cache_dir / "orderbook_context.json"
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(payload, default=str))
            tmp.replace(path)
        except Exception:
            pass

    def _update_history(self, snap: OrderBookSnapshot) -> dict[str, Any]:
        history_path = self._cache_dir / "orderbook_history.jsonl"
        summary_path = self._cache_dir / "orderbook_history_summary.json"
        payload = {
            "timestamp": snap.timestamp,
            "depth_bias": snap.depth_bias,
            "imbalance_ratio": snap.imbalance_ratio,
            "absorption_bias": snap.absorption_bias,
            "spoof_risk": snap.spoof_risk,
            "depth_flip": snap.depth_flip,
            "mid_move_bps": snap.mid_move_bps,
        }
        try:
            with history_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, default=str) + "\n")
        except Exception:
            return {}

        samples: list[dict[str, Any]] = []
        try:
            with history_path.open(encoding="utf-8") as handle:
                for raw in handle.readlines()[-self._history_limit :]:
                    try:
                        row = json.loads(raw)
                    except Exception:
                        continue
                    if isinstance(row, dict):
                        samples.append(row)
        except Exception:
            return {}

        if not samples:
            return {}

        bid_heavy = sum(1 for row in samples if str(row.get("depth_bias") or "") == "BID_HEAVY")
        ask_heavy = sum(1 for row in samples if str(row.get("depth_bias") or "") == "ASK_HEAVY")
        if bid_heavy > ask_heavy + 2:
            bias = "BID_HEAVY"
        elif ask_heavy > bid_heavy + 2:
            bias = "ASK_HEAVY"
        else:
            bias = "BALANCED"

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "samples": len(samples),
            "bias": bias,
            "avg_imbalance": _round(_avg(_flt(row.get("imbalance_ratio")) for row in samples), 4),
            "absorption_rate": _round(_share(str(row.get("absorption_bias") or "NEUTRAL") in {"BID_ABSORBING", "ASK_ABSORBING"} for row in samples), 3),
            "spoof_rate": _round(_share((_flt(row.get("spoof_risk")) or 0.0) >= 0.65 for row in samples), 3),
            "depth_flips": sum(1 for row in samples if bool(row.get("depth_flip"))),
            "mid_move_bps_avg": _round(_avg(_flt(row.get("mid_move_bps")) for row in samples), 2),
        }
        try:
            tmp = summary_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(summary, default=str))
            tmp.replace(summary_path)
        except Exception:
            pass
        return summary

    def _load_cached_snapshot(self) -> Optional[OrderBookSnapshot]:
        path = self._cache_dir / "orderbook_context.json"
        try:
            if not path.exists():
                return None
            payload = json.loads(path.read_text())
            if not isinstance(payload, dict):
                return None
            allowed = {field.name for field in OrderBookSnapshot.__dataclass_fields__.values()}
            filtered = {k: v for k, v in payload.items() if k in allowed}
            return OrderBookSnapshot(**filtered)
        except Exception:
            return None


def score_orderbook_modifier(
    direction: str,
    orderbook_ctx: dict,
    config: dict | None = None,
) -> OrderBookModResult:
    cfg = config or {}
    bonus_max = max(1, int(cfg.get("bonus_max", 4) or 4))
    long_threshold = float(cfg.get("imbalance_long_threshold", 0.58) or 0.58)
    short_threshold = float(cfg.get("imbalance_short_threshold", 0.42) or 0.42)
    max_spread_bps = float(cfg.get("max_spread_bps", 12.0) or 12.0)
    absorption_bonus = max(1, int(cfg.get("absorption_bonus", 2) or 2))
    replenishment_bonus = max(1, int(cfg.get("replenishment_bonus", 1) or 1))
    flip_bonus = max(1, int(cfg.get("flip_bonus", 1) or 1))
    spoof_penalty = max(1, int(cfg.get("spoof_penalty", 2) or 2))
    spoof_risk_threshold = float(cfg.get("spoof_risk_threshold", 0.65) or 0.65)
    replenishment_floor = float(cfg.get("replenishment_floor", 0.92) or 0.92)

    out = OrderBookModResult()
    if not direction or not orderbook_ctx:
        return out

    depth_bias = str(orderbook_ctx.get("depth_bias") or "UNKNOWN")
    imbalance = _flt(orderbook_ctx.get("imbalance_ratio"))
    spread_bps = _flt(orderbook_ctx.get("spread_bps"))
    absorption_bias = str(orderbook_ctx.get("absorption_bias") or "NEUTRAL")
    bid_replenishment = _flt(orderbook_ctx.get("bid_replenishment_ratio"))
    ask_replenishment = _flt(orderbook_ctx.get("ask_replenishment_ratio"))
    spoof_risk = _flt(orderbook_ctx.get("spoof_risk"))
    spoof_side = str(orderbook_ctx.get("spoof_side") or "NONE")
    depth_flip = bool(orderbook_ctx.get("depth_flip"))
    side = direction.lower().strip()

    if spread_bps is not None and spread_bps > max_spread_bps:
        out.bonus -= min(2, bonus_max)
        out.reasons.append(f"wide_book_spread {spread_bps:.2f}bps")

    if depth_bias == "BID_HEAVY" and imbalance is not None and imbalance >= long_threshold:
        if side == "long":
            out.bonus += bonus_max
            out.reasons.append(f"bid_stack_support {imbalance:.2f}")
        else:
            out.bonus -= min(3, bonus_max)
            out.reasons.append(f"bid_stack_against_short {imbalance:.2f}")
    elif depth_bias == "ASK_HEAVY" and imbalance is not None and imbalance <= short_threshold:
        if side == "short":
            out.bonus += bonus_max
            out.reasons.append(f"ask_stack_support {imbalance:.2f}")
        else:
            out.bonus -= min(3, bonus_max)
            out.reasons.append(f"ask_stack_against_long {imbalance:.2f}")

    if absorption_bias == "BID_ABSORBING":
        if side == "long":
            out.bonus += absorption_bonus
            out.reasons.append("bid_absorption_support")
        else:
            out.bonus -= absorption_bonus
            out.reasons.append("bid_absorption_against_short")
    elif absorption_bias == "ASK_ABSORBING":
        if side == "short":
            out.bonus += absorption_bonus
            out.reasons.append("ask_absorption_support")
        else:
            out.bonus -= absorption_bonus
            out.reasons.append("ask_absorption_against_long")

    if bid_replenishment is not None and bid_replenishment >= replenishment_floor and side == "long":
        out.bonus += replenishment_bonus
        out.reasons.append(f"bid_replenishment {bid_replenishment:.2f}")
    if ask_replenishment is not None and ask_replenishment >= replenishment_floor and side == "short":
        out.bonus += replenishment_bonus
        out.reasons.append(f"ask_replenishment {ask_replenishment:.2f}")

    if depth_flip:
        if depth_bias == "BID_HEAVY" and side == "long":
            out.bonus += flip_bonus
            out.reasons.append("book_flip_support_long")
        elif depth_bias == "ASK_HEAVY" and side == "short":
            out.bonus += flip_bonus
            out.reasons.append("book_flip_support_short")

    if spoof_risk is not None and spoof_risk >= spoof_risk_threshold:
        if (spoof_side == "ASK" and side == "long") or (spoof_side == "BID" and side == "short"):
            out.bonus -= spoof_penalty
            out.reasons.append(f"spoof_risk_against_trade {spoof_risk:.2f}")
        else:
            out.bonus -= 1
            out.reasons.append(f"spoof_risk_noise {spoof_risk:.2f}")

    out.bonus = max(-bonus_max, min(bonus_max, out.bonus))
    return out


def _detect_spoof_risk(
    *,
    prev_bias: str,
    depth_bias: str,
    prev_bid_depth: Optional[float],
    prev_ask_depth: Optional[float],
    bid_depth: float,
    ask_depth: float,
    prev_imbalance: Optional[float],
    imbalance: Optional[float],
    mid_move_bps: Optional[float],
) -> tuple[float, str]:
    spoof_risk = 0.0
    spoof_side = "NONE"
    if mid_move_bps is None or abs(mid_move_bps) > 12:
        return spoof_risk, spoof_side

    bid_drop = _drop_ratio(prev_bid_depth, bid_depth)
    ask_drop = _drop_ratio(prev_ask_depth, ask_depth)
    imbalance_shift = abs((imbalance or 0.5) - (prev_imbalance or 0.5))

    if prev_bias == "BID_HEAVY" and bid_drop >= 0.35 and depth_bias != "BID_HEAVY":
        spoof_risk = max(spoof_risk, min(1.0, bid_drop + imbalance_shift))
        spoof_side = "BID"
    if prev_bias == "ASK_HEAVY" and ask_drop >= 0.35 and depth_bias != "ASK_HEAVY":
        risk = min(1.0, ask_drop + imbalance_shift)
        if risk > spoof_risk:
            spoof_risk = risk
            spoof_side = "ASK"
    return spoof_risk, spoof_side


def _drop_ratio(previous: Optional[float], current: Optional[float]) -> float:
    if previous is None or previous <= 0 or current is None:
        return 0.0
    return max(0.0, min(1.0, (previous - current) / previous))


def _flt(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if value.endswith("%"):
                value = value[:-1]
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float], digits: int) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _avg(values) -> Optional[float]:
    usable = [float(v) for v in values if v is not None]
    if not usable:
        return None
    return sum(usable) / float(len(usable))


def _share(flags) -> float:
    items = list(flags)
    if not items:
        return 0.0
    return sum(1 for item in items if item) / float(len(items))
