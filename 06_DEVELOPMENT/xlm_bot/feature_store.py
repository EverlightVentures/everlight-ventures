from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(os.environ.get("CRYPTO_BOT_DIR", Path(__file__).resolve().parent))
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

FEATURE_SNAPSHOTS_PATH = LOGS_DIR / "feature_snapshots.jsonl"
TRADE_LABELS_PATH = LOGS_DIR / "trade_labels.jsonl"
LATEST_FEATURE_PATH = DATA_DIR / "feature_snapshot_latest.json"
LATEST_TRADE_LABEL_PATH = DATA_DIR / "trade_label_latest.json"
MARKET_PULSE_PATH = DATA_DIR / "market_pulse.json"
MARKET_BRIEF_PATH = DATA_DIR / "market_brief.json"
SENTIMENT_PATH = DATA_DIR / "sentiment_cache.json"
LIVE_TICK_PATH = LOGS_DIR / "live_tick.json"


def configure(*, base_dir: Path | None = None, data_dir: Path | None = None, logs_dir: Path | None = None) -> None:
    global BASE_DIR, DATA_DIR, LOGS_DIR
    global FEATURE_SNAPSHOTS_PATH, TRADE_LABELS_PATH
    global LATEST_FEATURE_PATH, LATEST_TRADE_LABEL_PATH
    global MARKET_PULSE_PATH, MARKET_BRIEF_PATH, SENTIMENT_PATH, LIVE_TICK_PATH

    if base_dir is not None:
        BASE_DIR = Path(base_dir)
    if data_dir is not None:
        DATA_DIR = Path(data_dir)
    if logs_dir is not None:
        LOGS_DIR = Path(logs_dir)

    FEATURE_SNAPSHOTS_PATH = LOGS_DIR / "feature_snapshots.jsonl"
    TRADE_LABELS_PATH = LOGS_DIR / "trade_labels.jsonl"
    LATEST_FEATURE_PATH = DATA_DIR / "feature_snapshot_latest.json"
    LATEST_TRADE_LABEL_PATH = DATA_DIR / "trade_label_latest.json"
    MARKET_PULSE_PATH = DATA_DIR / "market_pulse.json"
    MARKET_BRIEF_PATH = DATA_DIR / "market_brief.json"
    SENTIMENT_PATH = DATA_DIR / "sentiment_cache.json"
    LIVE_TICK_PATH = LOGS_DIR / "live_tick.json"


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        pass
    return {}


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=str) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except Exception:
        return default


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


def _minutes_since(value: Any) -> float | None:
    parsed = _parse_iso(value)
    if not parsed:
        return None
    return round((datetime.now(timezone.utc) - parsed).total_seconds() / 60.0, 1)


def _brief_meta() -> tuple[dict, float | None]:
    wrapper = _read_json(MARKET_BRIEF_PATH)
    brief = wrapper.get("brief") if isinstance(wrapper.get("brief"), dict) else {}
    age_min = _minutes_since(wrapper.get("timestamp"))
    if age_min is None:
        expires_ts = _safe_float(wrapper.get("expires_ts"))
        if expires_ts is not None:
            age_min = round(max((time_now := datetime.now(timezone.utc).timestamp()) - (expires_ts - 900.0), 0.0) / 60.0, 1)
    return brief, age_min


def _pulse_meta() -> tuple[dict, dict]:
    wrapper = _read_json(MARKET_PULSE_PATH)
    pulse = wrapper.get("pulse") if isinstance(wrapper.get("pulse"), dict) else {}
    components = pulse.get("components") if isinstance(pulse.get("components"), dict) else {}
    return pulse, components


def _trade_minutes(row: dict) -> float | None:
    entry_ts = _parse_iso(row.get("entry_time"))
    exit_ts = _parse_iso(row.get("exit_time") or row.get("timestamp"))
    if not entry_ts or not exit_ts:
        return None
    return round((exit_ts - entry_ts).total_seconds() / 60.0, 1)


def build_feature_snapshot(payload: dict, *, event_type: str = "decision") -> dict:
    payload = payload if isinstance(payload, dict) else {}
    ts = payload.get("timestamp") or payload.get("ts") or datetime.now(timezone.utc).isoformat()
    session_id = str(payload.get("session_id") or "")
    reason = str(payload.get("reason") or payload.get("result") or event_type)
    product_id = str(payload.get("product_selected") or payload.get("product_id") or payload.get("product") or "")
    price = _safe_float(payload.get("price"))
    if price is None:
        price = _safe_float(payload.get("entry_price"))
    ai_directive = payload.get("ai_directive") if isinstance(payload.get("ai_directive"), dict) else {}
    pulse, pulse_components = _pulse_meta()
    brief, brief_age_min = _brief_meta()
    sentiment = _read_json(SENTIMENT_PATH)
    live_tick = _read_json(LIVE_TICK_PATH)
    tick_age = _safe_float(payload.get("live_tick_age_sec"))
    if tick_age is None:
        tick_age = _safe_float(pulse_components.get("tick_age_sec"))

    snapshot = {
        "feature_id": hashlib.sha1(
            f"{ts}|{session_id}|{event_type}|{reason}|{product_id}|{payload.get('direction') or ''}|{price or ''}".encode("utf-8")
        ).hexdigest()[:24],
        "ts": ts,
        "event_type": event_type,
        "reason": reason,
        "session_id": session_id or None,
        "product_id": product_id or None,
        "signal_product_id": payload.get("signal_product_id"),
        "spot_reference_product_id": payload.get("spot_reference_product_id"),
        "price": price,
        "direction": payload.get("direction") or payload.get("side"),
        "entry_signal": payload.get("entry_signal") or payload.get("entry_type"),
        "quality_tier": payload.get("quality_tier"),
        "route_tier": payload.get("route_tier"),
        "gates_pass": payload.get("gates_pass"),
        "confluence_score": _safe_float(payload.get("confluence_score")),
        "ev_usd": _safe_float((payload.get("ev") or {}).get("ev_usd") if isinstance(payload.get("ev"), dict) else payload.get("ev_usd")),
        "v4_regime": payload.get("v4_selected_regime") or payload.get("v4_regime") or payload.get("strategy_regime"),
        "vol_phase": payload.get("vol_phase"),
        "recovery_mode": payload.get("recovery_mode"),
        "exchange_pnl_today_usd": _safe_float(payload.get("exchange_pnl_today_usd") or payload.get("pnl_today_usd")),
        "trades_today": _safe_int(payload.get("trades_today")),
        "losses_today": _safe_int(payload.get("losses_today")),
        "pulse_regime": pulse.get("regime"),
        "pulse_health": _safe_int(pulse.get("health_score")),
        "tick_health": pulse_components.get("tick_health"),
        "tick_age_sec": tick_age,
        "brief_age_min": brief_age_min if brief_age_min is not None else _safe_float(pulse_components.get("brief_age_min")),
        "news_risk": brief.get("risk_modifier") or pulse_components.get("news_risk"),
        "news_confidence": _safe_float(brief.get("confidence") or pulse_components.get("news_confidence")),
        "sentiment_score": _safe_int(sentiment.get("score") or pulse_components.get("sentiment_score")),
        "sentiment_stale": bool(pulse_components.get("sentiment_stale")),
        "price_source": payload.get("price_source"),
        "bot_state": payload.get("state"),
        "contract_mark_price": _safe_float(payload.get("contract_mark_price")),
        "contract_price_change_24h_pct": _safe_float(payload.get("contract_price_change_24h_pct")),
        "orderbook_depth_bias": payload.get("orderbook_depth_bias"),
        "orderbook_imbalance": _safe_float(payload.get("orderbook_imbalance")),
        "orderbook_spread_bps": _safe_float(payload.get("orderbook_spread_bps")),
        "liquidation_signal_source": payload.get("liquidation_signal_source"),
        "liquidation_feed_live": bool(payload.get("liquidation_feed_live")),
        "liquidation_bias": payload.get("liquidation_bias"),
        "liquidation_events_5m": _safe_int(payload.get("liquidation_events_5m")),
        "liquidation_notional_5m_usd": _safe_float(payload.get("liquidation_notional_5m_usd")),
        "futures_relativity_bias": payload.get("futures_relativity_bias"),
        "futures_relativity_confidence": _safe_float(payload.get("futures_relativity_confidence")),
        "cross_venue_oi_change_pct": _safe_float(payload.get("cross_venue_oi_change_pct")),
        "cross_venue_funding_bias": payload.get("cross_venue_funding_bias"),
        "ai_action": ai_directive.get("action"),
        "ai_confidence": _safe_float(ai_directive.get("confidence")),
        "ai_initiated": bool(payload.get("entry_signal") == "ai_executive"),
        "block_reasons": payload.get("block_reasons") or payload.get("gate_reasons"),
        "live_tick_price": _safe_float(live_tick.get("price")),
    }
    return snapshot


def record_snapshot(payload: dict, *, event_type: str = "decision") -> dict:
    snapshot = build_feature_snapshot(payload, event_type=event_type)
    _append_jsonl(FEATURE_SNAPSHOTS_PATH, snapshot)
    _write_json(LATEST_FEATURE_PATH, snapshot)
    return snapshot


def build_trade_label(row: dict) -> dict:
    row = row if isinstance(row, dict) else {}
    ts = row.get("exit_time") or row.get("entry_time") or row.get("timestamp") or datetime.now(timezone.utc).isoformat()
    status = "closed" if row.get("exit_price") or row.get("exit_time") or row.get("pnl_usd") not in (None, "") else "opened"
    label = {
        "label_id": hashlib.sha1(
            f"{row.get('order_id') or ''}|{row.get('entry_time') or row.get('timestamp') or ''}|{row.get('exit_time') or ''}|{row.get('pnl_usd') or ''}|{status}".encode("utf-8")
        ).hexdigest()[:24],
        "ts": ts,
        "status": status,
        "session_id": row.get("session_id"),
        "order_id": row.get("order_id"),
        "product_id": row.get("product_id"),
        "side": row.get("side"),
        "entry_type": row.get("entry_type"),
        "strategy_regime": row.get("strategy_regime"),
        "size": _safe_int(row.get("size")),
        "entry_price": _safe_float(row.get("entry_price")),
        "exit_price": _safe_float(row.get("exit_price")),
        "pnl_usd": _safe_float(row.get("pnl_usd")),
        "result": row.get("result"),
        "exit_reason": row.get("exit_reason"),
        "hold_minutes": _trade_minutes(row),
        "fill_verified": row.get("fill_verified"),
    }
    return label


def record_trade_label(row: dict) -> dict:
    label = build_trade_label(row)
    _append_jsonl(TRADE_LABELS_PATH, label)
    _write_json(LATEST_TRADE_LABEL_PATH, label)
    return label
