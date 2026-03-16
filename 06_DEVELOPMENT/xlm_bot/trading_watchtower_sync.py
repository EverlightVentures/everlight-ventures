#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from export_metrics import build_metrics, write_metrics
from public_watchtower import build_public_watchtower_fields
from push_metrics_supabase import run_push

BASE = Path(os.environ.get("CRYPTO_BOT_DIR", Path(__file__).resolve().parent))
DATA = BASE / "data"
LOGS = BASE / "logs"
FEATURE_LATEST = DATA / "feature_snapshot_latest.json"
PULSE_PATH = DATA / "market_pulse.json"
BRIEF_PATH = DATA / "market_brief.json"
TRADE_LABEL_PATH = DATA / "trade_label_latest.json"
STATUS_PATH = DATA / "trading_watchtower_status.json"
STATE_PATH = DATA / "trading_watchtower_notify_state.json"


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        pass
    return {}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _minutes_old(ts_value: str) -> float | None:
    if not ts_value:
        return None
    try:
        parsed = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - parsed).total_seconds() / 60.0, 1)
    except Exception:
        return None


def _brief_age_min() -> float | None:
    wrapper = _read_json(BRIEF_PATH)
    if not wrapper:
        return None
    return _minutes_old(str(wrapper.get("timestamp") or ""))


def _post_webhook(url: str, payload: dict) -> None:
    if not url:
        return
    requests.post(url, json=payload, timeout=10)


def build_watchtower(metrics: dict) -> dict:
    feature = _read_json(FEATURE_LATEST)
    pulse_wrapper = _read_json(PULSE_PATH)
    pulse = pulse_wrapper.get("pulse") if isinstance(pulse_wrapper.get("pulse"), dict) else {}
    pulse_components = pulse.get("components") if isinstance(pulse.get("components"), dict) else {}
    last_trade = _read_json(TRADE_LABEL_PATH)

    snapshot_age_min = _minutes_old(str(metrics.get("generated_at") or ""))
    decision_age_min = _minutes_old(str(feature.get("ts") or "")) or snapshot_age_min
    pulse_regime = str(feature.get("pulse_regime") or pulse.get("regime") or "unknown")
    pulse_health = feature.get("pulse_health")
    if pulse_health is None:
        pulse_health = pulse.get("health_score")
    tick_health = str(feature.get("tick_health") or pulse_components.get("tick_health") or "unknown")
    tick_age_sec = feature.get("tick_age_sec")
    if tick_age_sec is None:
        tick_age_sec = pulse_components.get("tick_age_sec")
    brief_age_min = feature.get("brief_age_min")
    if brief_age_min is None:
        brief_age_min = _brief_age_min()
    if brief_age_min is None:
        brief_age_min = pulse_components.get("brief_age_min")
    sentiment_stale = bool(
        feature.get("sentiment_stale")
        if feature.get("sentiment_stale") is not None
        else pulse_components.get("sentiment_stale")
    )

    data_quality_status = "healthy"
    quality_flags: list[str] = []
    if pulse_regime == "danger":
        data_quality_status = "degraded"
        quality_flags.append("pulse danger")
    if tick_health in {"dead", "stale"}:
        data_quality_status = "degraded"
        quality_flags.append(f"tick {tick_health}")
    if (snapshot_age_min or 0) >= 60:
        data_quality_status = "degraded"
        quality_flags.append("snapshot stale")
    if brief_age_min is not None and float(brief_age_min or 0) >= 45:
        data_quality_status = "degraded"
        quality_flags.append("brief stale")
    if sentiment_stale:
        quality_flags.append("sentiment stale")
    if str(metrics.get("data_quality_status") or "").lower() == "degraded" and data_quality_status != "degraded":
        data_quality_status = "degraded"
        quality_flags.append("metrics degraded")

    stream_status = "pilot"
    if data_quality_status == "degraded":
        stream_status = "watch"
    elif metrics.get("bot_alive"):
        stream_status = "active"

    open_alert = None
    if data_quality_status == "degraded":
        open_alert = {
            "severity": "error" if tick_health == "dead" or (snapshot_age_min or 0) >= 60 else "warning",
            "summary": "XLM bot health degraded",
            "detail": "Pulse danger, stale brief, dead tick, or stale snapshot detected in live telemetry.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    watchtower = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stream_status": stream_status,
        "data_quality_status": data_quality_status,
        "quality_flags": quality_flags,
        "bot_state": metrics.get("bot_state") or feature.get("bot_state") or ("LIVE" if metrics.get("bot_alive") else "unknown"),
        "price": feature.get("price") or feature.get("live_tick_price"),
        "direction": feature.get("direction") or metrics.get("position_side"),
        "entry_signal": feature.get("entry_signal") or metrics.get("entry_signal"),
        "quality_tier": feature.get("quality_tier") or metrics.get("quality_tier"),
        "route_tier": feature.get("route_tier") or metrics.get("route_tier"),
        "decision_reason": feature.get("reason") or metrics.get("latest_decision_reason"),
        "decision_age_min": decision_age_min,
        "snapshot_age_min": snapshot_age_min,
        "pulse_regime": pulse_regime,
        "pulse_health": pulse_health,
        "tick_health": tick_health,
        "tick_age_sec": tick_age_sec,
        "brief_age_min": brief_age_min,
        "sentiment_stale": sentiment_stale,
        "gates_pass": feature.get("gates_pass"),
        "ai_action": feature.get("ai_action") or metrics.get("ai_action"),
        "ai_confidence": feature.get("ai_confidence") or metrics.get("ai_confidence"),
        "last_trade": last_trade if last_trade else None,
        "open_alert": open_alert,
        "telemetry_source": "local_bot",
    }
    watchtower.update(build_public_watchtower_fields(watchtower))
    return watchtower


def main() -> int:
    metrics = build_metrics()
    write_metrics(metrics)

    push_exit = 0
    if os.environ.get("WATCHTOWER_PUSH_SUPABASE", "1").lower() not in {"0", "false", "no"}:
        try:
            push_exit = run_push()
        except Exception:
            push_exit = 1

    watchtower = build_watchtower(metrics)
    status_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "push_exit": push_exit,
        "watchtower": watchtower,
    }
    _write_json(STATUS_PATH, status_payload)

    prior = _read_json(STATE_PATH)
    current_flag = watchtower.get("data_quality_status") or "unknown"
    prior_flag = prior.get("data_quality_status") or "unknown"
    fingerprint = "|".join(
        [
            current_flag,
            str(watchtower.get("pulse_regime") or ""),
            str(watchtower.get("tick_health") or ""),
            str((watchtower.get("open_alert") or {}).get("severity") or ""),
            str(watchtower.get("decision_reason") or ""),
        ]
    )
    changed = fingerprint != str(prior.get("fingerprint") or "")

    if changed and current_flag in {"degraded", "healthy"} and current_flag != prior_flag:
        message = (
            f"Trading Watchtower {current_flag.upper()}: "
            f"state={watchtower.get('bot_state')} | "
            f"pulse={watchtower.get('pulse_regime')} ({watchtower.get('pulse_health')}) | "
            f"tick={watchtower.get('tick_health')} | "
            f"decision={watchtower.get('decision_reason') or 'n/a'}"
        )
        try:
            from alerts import slack as slack_alert

            slack_alert.send(message, level="error" if current_flag == "degraded" else "info")
        except Exception:
            pass

        webhook_payload = {
            "event": "trading_watchtower_state_change",
            "generated_at": status_payload["generated_at"],
            "watchtower": watchtower,
        }
        try:
            _post_webhook(os.environ.get("N8N_TRADING_WATCHTOWER_WEBHOOK", ""), webhook_payload)
        except Exception:
            pass
        try:
            _post_webhook(os.environ.get("TRADING_WATCHTOWER_WEBHOOK", ""), webhook_payload)
        except Exception:
            pass

    _write_json(
        STATE_PATH,
        {
            "fingerprint": fingerprint,
            "data_quality_status": current_flag,
            "updated_at": status_payload["generated_at"],
        },
    )

    print(json.dumps(status_payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
