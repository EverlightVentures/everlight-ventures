from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import websockets

DEFAULT_FEED_URL = "wss://fstream.binance.com/ws/!forceOrder@arr"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        pass
    return {}


@dataclass
class LiquidationModResult:
    bonus: int = 0
    reasons: list[str] = field(default_factory=list)


class LiquidationFeedCollector:
    def __init__(self, *, cache_dir: Path, symbol: str = "XLMUSDT", config: dict | None = None):
        cfg = config or {}
        self._symbol = str(cfg.get("symbol") or symbol or "XLMUSDT").upper()
        self._feed_url = str(cfg.get("ws_url") or DEFAULT_FEED_URL)
        self._stale_seconds = float(cfg.get("stale_seconds", 45.0) or 45.0)
        self._window_seconds = int(cfg.get("window_seconds", 900) or 900)
        self._reconnect_seconds = float(cfg.get("reconnect_seconds", 3.0) or 3.0)
        self._cache_path = Path(cache_dir) / "liquidation_feed.json"
        self._events: deque[dict[str, Any]] = deque()

    async def run_forever(self) -> None:
        while True:
            try:
                async with websockets.connect(
                    self._feed_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    max_size=1_000_000,
                ) as socket:
                    self._write_snapshot(live=True, error="")
                    async for raw in socket:
                        self._handle_message(raw)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._write_snapshot(live=False, error=str(exc))
                await asyncio.sleep(self._reconnect_seconds)

    def _handle_message(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except Exception:
            return

        events = payload if isinstance(payload, list) else [payload]
        changed = False
        for event in events:
            force_order = event.get("o") if isinstance(event, dict) and isinstance(event.get("o"), dict) else None
            if not force_order:
                continue
            normalized = self._normalize_event(force_order)
            if not normalized:
                continue
            self._events.append(normalized)
            changed = True
        if changed:
            self._prune()
            self._write_snapshot(live=True, error="")

    def _normalize_event(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        symbol = str(payload.get("s") or "").upper()
        if symbol != self._symbol:
            return None

        side = str(payload.get("S") or "").upper()
        price = _safe_float(payload.get("ap") or payload.get("p"))
        qty = _safe_float(payload.get("q") or payload.get("l"))
        notional = (price or 0.0) * (qty or 0.0) if price and qty else None
        ts_ms = payload.get("T") or payload.get("E") or int(time.time() * 1000)
        try:
            ts_iso = datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc).isoformat()
        except Exception:
            ts_iso = _now_iso()

        liquidated_side = "unknown"
        if side == "SELL":
            liquidated_side = "longs"
        elif side == "BUY":
            liquidated_side = "shorts"

        return {
            "ts": ts_iso,
            "symbol": symbol,
            "order_side": side,
            "liquidated_side": liquidated_side,
            "price": price,
            "qty": qty,
            "notional_usd": round(notional, 2) if notional is not None else None,
        }

    def _prune(self) -> None:
        now_ts = time.time()
        while self._events:
            head = self._events[0]
            try:
                age = now_ts - datetime.fromisoformat(str(head.get("ts")).replace("Z", "+00:00")).timestamp()
            except Exception:
                age = self._window_seconds + 1
            if age <= self._window_seconds:
                break
            self._events.popleft()

    def _window_stats(self, seconds: int) -> dict[str, Any]:
        cutoff = time.time() - seconds
        total = 0.0
        count = 0
        longs = 0.0
        shorts = 0.0
        for event in self._events:
            try:
                ts = datetime.fromisoformat(str(event.get("ts")).replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if ts < cutoff:
                continue
            count += 1
            notional = float(event.get("notional_usd") or 0.0)
            total += notional
            if event.get("liquidated_side") == "longs":
                longs += notional
            elif event.get("liquidated_side") == "shorts":
                shorts += notional
        return {
            "events": count,
            "notional_usd": round(total, 2),
            "longs_usd": round(longs, 2),
            "shorts_usd": round(shorts, 2),
        }

    def _write_snapshot(self, *, live: bool, error: str) -> None:
        self._prune()
        latest = self._events[-1] if self._events else {}
        one_min = self._window_stats(60)
        five_min = self._window_stats(300)
        fifteen_min = self._window_stats(900)

        bias = "BALANCED"
        long_flow = float(five_min.get("longs_usd") or 0.0)
        short_flow = float(five_min.get("shorts_usd") or 0.0)
        total = float(five_min.get("notional_usd") or 0.0)
        if total >= 10_000:
            if long_flow >= short_flow * 1.35 and long_flow >= 7_500:
                bias = "LONGS_FLUSHED"
            elif short_flow >= long_flow * 1.35 and short_flow >= 7_500:
                bias = "SHORTS_FLUSHED"

        snapshot = {
            "generated_at": _now_iso(),
            "symbol": self._symbol,
            "feed_live": bool(live),
            "stale_seconds": self._stale_seconds,
            "error": error,
            "last_event_at": latest.get("ts"),
            "last_event": latest,
            "bias": bias,
            "window_1m": one_min,
            "window_5m": five_min,
            "window_15m": fifteen_min,
        }
        _write_json(self._cache_path, snapshot)


def read_liquidation_snapshot(cache_dir: Path, config: dict | None = None) -> dict[str, Any]:
    cfg = config or {}
    stale_seconds = float(cfg.get("stale_seconds", 45.0) or 45.0)
    path = Path(cache_dir) / "liquidation_feed.json"
    snapshot = _read_json(path)
    if not snapshot:
        return {}
    last_event_at = str(snapshot.get("last_event_at") or "")
    age_seconds = None
    if last_event_at:
        try:
            age_seconds = round(
                time.time() - datetime.fromisoformat(last_event_at.replace("Z", "+00:00")).timestamp(),
                1,
            )
        except Exception:
            age_seconds = None
    snapshot["age_seconds"] = age_seconds
    snapshot["feed_live"] = bool(snapshot.get("feed_live")) and (
        age_seconds is None or age_seconds <= stale_seconds
    )
    return snapshot


def score_liquidation_modifier(
    direction: str,
    liquidation_ctx: dict[str, Any] | None,
    config: dict | None = None,
) -> LiquidationModResult:
    cfg = config or {}
    out = LiquidationModResult()
    if not direction or not liquidation_ctx or not liquidation_ctx.get("feed_live"):
        return out

    bonus_max = max(1, int(cfg.get("bonus_max", 5) or 5))
    min_notional = float(cfg.get("min_notional_5m_usd", 25000.0) or 25000.0)
    bias = str(liquidation_ctx.get("bias") or "BALANCED").upper()
    total = float(((liquidation_ctx.get("window_5m") or {}).get("notional_usd")) or 0.0)
    side = direction.lower().strip()
    if total < min_notional:
        return out

    if bias == "LONGS_FLUSHED":
        if side == "long":
            out.bonus += bonus_max
            out.reasons.append(f"forced_sells_flush_support ${total:,.0f}/5m")
        elif side == "short":
            out.bonus -= min(1, bonus_max)
            out.reasons.append(f"avoid_chasing_post_flush ${total:,.0f}/5m")
    elif bias == "SHORTS_FLUSHED":
        if side == "short":
            out.bonus += bonus_max
            out.reasons.append(f"forced_buys_flush_support ${total:,.0f}/5m")
        elif side == "long":
            out.bonus -= min(1, bonus_max)
            out.reasons.append(f"avoid_chasing_post_short_flush ${total:,.0f}/5m")

    out.bonus = max(-bonus_max, min(bonus_max, out.bonus))
    return out


def main() -> int:
    cache_dir = Path(os.environ.get("CRYPTO_BOT_DIR", Path(__file__).resolve().parents[1])) / "data"
    symbol = os.environ.get("BINANCE_LIQ_SYMBOL", "XLMUSDT")
    collector = LiquidationFeedCollector(cache_dir=cache_dir, symbol=symbol)
    asyncio.run(collector.run_forever())
    return 0
