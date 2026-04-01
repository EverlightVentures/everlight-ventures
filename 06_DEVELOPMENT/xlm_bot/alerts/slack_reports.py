"""
Slack Live Feed -- Google-Docs-backed reports posted to Slack.
Cadence policy:
- In a live position: frequent position updates.
- Flat/no position: hourly market update.
- Account health: hourly.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from . import slack as _slack
from . import slack_canvas_bridge

_DEFAULT_FLAT_MARKET_INTERVAL_SEC = 3600
_DEFAULT_IN_POSITION_INTERVAL_SEC = 300
_DEFAULT_HEALTH_INTERVAL_SEC = 3600
_DEFAULT_UNCHANGED_REPEAT_INTERVAL_SEC = 21600


def _bot_dir() -> Path:
    return Path(os.environ.get("CRYPTO_BOT_DIR") or os.getcwd())


def _report_state_path() -> Path:
    return _bot_dir() / "data" / "slack_report_state.json"


def _read_json(path: Path) -> dict:
    try:
        if path.exists():
            payload = json.loads(path.read_text())
            return payload if isinstance(payload, dict) else {}
    except Exception:
        pass
    return {}


def _new_report_state() -> dict:
    return {
        "last_market_ts": 0.0,
        "last_health_ts": 0.0,
        "last_position_ts": 0.0,
        "last_in_position": False,
        "last_position_key": "",
        "last_market_fingerprint": "",
        "last_health_fingerprint": "",
    }


def _load_report_state() -> dict:
    path = _report_state_path()
    if not path.exists():
        return _new_report_state()
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return _new_report_state()


def _save_report_state(state: dict) -> None:
    path = _report_state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state))
    except Exception:
        pass


def _send_canvas(text: str, title: str) -> None:
    slack_canvas_bridge.create_native_canvas(text, title, "xlmbot")


def _to_float(value, default: float | None = 0.0) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _fmt_usd(v) -> str:
    return _slack._fmt_usd(v)


def _fmt_price(v) -> str:
    value = _to_float(v, None)
    if value is None or value <= 0:
        return "n/a"
    return f"${value:.5f}"


def _fmt_pct(v) -> str:
    value = _to_float(v, None)
    if value is None:
        return "n/a"
    return f"{value:+.2f}%"


def _fmt_optional_usd(v) -> str:
    value = _to_float(v, None)
    if value is None:
        return "unavailable"
    return f"${value:.2f}"


def _fmt_optional_ratio(v) -> str:
    value = _to_float(v, None)
    if value is None:
        return "unavailable"
    return f"{value:.1%}"


def _pnl_emoji(val: float) -> str:
    if val > 0:
        return ":large_green_circle:"
    if val < 0:
        return ":red_circle:"
    return ":white_circle:"


def _position_key(open_pos: dict | None) -> str:
    if not isinstance(open_pos, dict):
        return ""
    return "|".join(
        [
            str(open_pos.get("entry_time") or ""),
            str(open_pos.get("direction") or ""),
            str(open_pos.get("entry_price") or ""),
            str(open_pos.get("size") or ""),
        ]
    )


def _spot_cash_total(state: dict, ctx: dict) -> float | None:
    cash_map = ctx.get("last_spot_cash_map") if isinstance(ctx.get("last_spot_cash_map"), dict) else None
    if cash_map is None and isinstance(state.get("last_spot_cash_map"), dict):
        cash_map = state.get("last_spot_cash_map")
    if not isinstance(cash_map, dict):
        return None
    total = 0.0
    seen = False
    for value in cash_map.values():
        amount = _to_float(value, None)
        if amount is None:
            continue
        total += amount
        seen = True
    return round(total, 2) if seen else None


def _merge_runtime_context(state: dict, ctx: dict) -> dict:
    base = _bot_dir()
    metrics = _read_json(base / "data" / "metrics.json")
    live_tick = _read_json(base / "logs" / "live_tick.json")
    feature = _read_json(base / "data" / "feature_snapshot_latest.json")

    merged = {}
    if isinstance(metrics, dict):
        merged.update(metrics)
    if isinstance(feature, dict):
        merged.update(feature)
    if isinstance(state, dict):
        merged.update(state)
    if isinstance(ctx, dict):
        merged.update(ctx)

    price = (
        ctx.get("price")
        or ctx.get("mark_price")
        or live_tick.get("price")
        or feature.get("live_tick_price")
        or feature.get("contract_mark_price")
        or metrics.get("contract_mark_price")
    )
    if price not in (None, ""):
        merged["price"] = price
        merged["mark_price"] = merged.get("mark_price") or price

    equity = (
        ctx.get("equity")
        or ctx.get("exchange_equity_usd")
        or state.get("exchange_equity_usd")
        or metrics.get("exchange_equity_usd")
    )
    if equity not in (None, ""):
        merged["equity"] = equity

    total_balance = ctx.get("total_balance")
    if total_balance in (None, ""):
        spot_total = _spot_cash_total(state, merged)
        if merged.get("equity") not in (None, "") and spot_total not in (None, ""):
            total_balance = _to_float(merged.get("equity"), 0.0) + _to_float(spot_total, 0.0)
        elif spot_total not in (None, ""):
            total_balance = spot_total
        elif merged.get("equity") not in (None, ""):
            total_balance = merged.get("equity")
        elif state.get("equity_start_usd") not in (None, ""):
            total_balance = state.get("equity_start_usd")
    if total_balance not in (None, ""):
        merged["total_balance"] = total_balance

    if merged.get("margin_ratio") in (None, ""):
        merged["margin_ratio"] = (
            ctx.get("margin_ratio")
            or state.get("margin_ratio")
            or metrics.get("margin_ratio")
        )

    if merged.get("thought") in (None, ""):
        merged["thought"] = ctx.get("thought") or "watching for a clean setup"

    if merged.get("regime") in (None, ""):
        merged["regime"] = ctx.get("regime") or merged.get("pulse_regime")

    return merged


def _market_fingerprint(state: dict, ctx: dict) -> str:
    parts = [
        str(round(_to_float(ctx.get("price") or ctx.get("mark_price"), 0.0) or 0.0, 5)),
        str(ctx.get("regime") or ctx.get("pulse_regime") or state.get("regime") or ""),
        str(state.get("vol_state") or ctx.get("vol_state") or ""),
        str(state.get("trades") or state.get("trades_today") or ""),
        str(_to_float(state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd"), 0.0) or 0.0),
        str(ctx.get("entry_signal") or ""),
        str(ctx.get("latest_decision_reason") or ctx.get("reason") or ""),
    ]
    return "|".join(parts)


def _health_fingerprint(state: dict, ctx: dict) -> str:
    open_pos = state.get("open_position") if isinstance(state.get("open_position"), dict) else {}
    parts = [
        str(_to_float(ctx.get("total_balance"), None)),
        str(_to_float(ctx.get("equity"), None)),
        str(_to_float(ctx.get("margin_ratio"), None)),
        str(_to_float(state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd"), 0.0) or 0.0),
        str(open_pos.get("direction") or "Flat"),
    ]
    return "|".join(parts)


def _format_confluences(value) -> str:
    if isinstance(value, dict):
        active = [str(k).replace("_", " ") for k, ok in value.items() if ok]
        return ", ".join(active) if active else "none active"
    if isinstance(value, (list, tuple)):
        active = [str(item).replace("_", " ") for item in value if str(item).strip()]
        return ", ".join(active) if active else "none active"
    text = str(value or "").strip()
    return text if text else "none active"


def _position_contract_pnl(direction: str, entry_price, target_price, size, contract_size) -> float | None:
    entry = _to_float(entry_price, None)
    target = _to_float(target_price, None)
    qty = _to_float(size, None)
    contracts = _to_float(contract_size, None)
    if entry is None or target is None or qty is None or contracts is None:
        return None
    move = (target - entry) * qty * contracts
    if str(direction or "").lower() == "short":
        move *= -1
    return move


def _format_target_line(label: str, price, est_pnl) -> str:
    price_txt = _fmt_price(price)
    if est_pnl is None:
        return f"- {label}: {price_txt}"
    return f"- {label}: {price_txt} | est {label.lower()} {_fmt_usd(est_pnl)}"


def _format_next_play(name: str, play) -> str:
    if not isinstance(play, dict):
        text = str(play or "").strip()
        return f"- {name}: {text or 'none queued'}"
    trigger = _fmt_price(play.get("trigger_price"))
    level_name = str(play.get("level_name") or "trigger").replace("_", " ")
    distance_atr = _to_float(play.get("distance_atr"), None)
    readiness_pct = _to_float(play.get("readiness_pct"), None)
    score = _to_float(play.get("score"), None)
    threshold = _to_float(play.get("threshold"), None)
    parts = [f"trigger {trigger}", level_name]
    if distance_atr is not None:
        parts.append(f"{distance_atr:.2f} ATR away")
    if readiness_pct is not None:
        parts.append(f"{int(readiness_pct)}% ready")
    if score is not None and threshold is not None:
        parts.append(f"score {int(score)}/{int(threshold)}")
    return f"- {name}: " + " | ".join(parts)


def _build_trade_report(state: dict, ctx: dict, event: str) -> tuple[str, str]:
    open_pos = state.get("open_position") if isinstance(state.get("open_position"), dict) else {}
    direction = str(open_pos.get("direction") or ctx.get("direction") or "flat").upper()
    product_id = str(open_pos.get("product_id") or ctx.get("product_selected") or ctx.get("product_id") or ctx.get("product") or "XLP-20DEC30-CDE")
    size = open_pos.get("size") or ctx.get("size") or "?"
    entry_price = _to_float(open_pos.get("entry_price") or ctx.get("entry_price"), None)
    live_price = _to_float(ctx.get("mark_price") or ctx.get("price") or ctx.get("exit_price"), None)
    stop_price = _to_float(open_pos.get("stop_loss") or ctx.get("stop_loss"), None)
    contract_size = _to_float(open_pos.get("contract_size") or ctx.get("contract_size"), None)
    pnl_live = _to_float(ctx.get("pnl_usd_live"), None)
    pnl_pct = _to_float(ctx.get("pnl_pct"), None)
    pnl_today = _to_float(state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd"), 0.0) or 0.0
    quality_tier = str(open_pos.get("quality_tier") or ctx.get("quality_tier") or "n/a").upper()
    regime = str(open_pos.get("strategy_regime") or ctx.get("regime") or ctx.get("market_regime") or "n/a")
    entry_signal = str(open_pos.get("entry_type") or ctx.get("entry_signal") or "n/a")
    confluence_score = open_pos.get("confluence_score") or ctx.get("confluence_score") or "n/a"
    recovery_target = _to_float(open_pos.get("recovery_target_usd"), None)
    fees_est = _to_float(open_pos.get("estimated_round_trip_fees"), None)
    min_profit = _to_float(open_pos.get("entry_profile_min_profit_usd"), None)
    thought = str(ctx.get("thought") or "No reasoning captured.")
    confluences = _format_confluences(ctx.get("confluences"))
    ai_action = None
    ai_conf = None
    if isinstance(ctx.get("ai_insight"), dict):
        ai_action = ctx["ai_insight"].get("action")
        ai_conf = ctx["ai_insight"].get("confidence")

    tp1 = _to_float(open_pos.get("tp1"), None)
    tp2 = _to_float(open_pos.get("tp2"), None)
    tp3 = _to_float(open_pos.get("tp3"), None)
    est_stop = _position_contract_pnl(direction, entry_price, stop_price, size, contract_size)
    est_tp1 = _position_contract_pnl(direction, entry_price, tp1, size, contract_size)
    est_tp2 = _position_contract_pnl(direction, entry_price, tp2, size, contract_size)
    est_tp3 = _position_contract_pnl(direction, entry_price, tp3, size, contract_size)

    headline = (
        f"Trade status: {direction} {size}c {product_id} | "
        f"entry {_fmt_price(entry_price)} | live {_fmt_price(live_price)} | "
        f"live pnl {_fmt_usd(pnl_live if pnl_live is not None else 0.0)}"
    )
    context_line = (
        f"Setup: {entry_signal} | regime {regime} | quality {quality_tier} | "
        f"score {confluence_score} | day pnl {_fmt_usd(pnl_today)}"
    )
    title = f"{product_id} {event.title()} Report"
    lines = [
        f"# {title}",
        headline,
        context_line,
        "",
        "## Thesis",
        f"- Reasoning: {thought}",
        f"- Signal: {entry_signal}",
        f"- Confluences: {confluences}",
        f"- Live state: entry {_fmt_price(entry_price)} | live {_fmt_price(live_price)} | pnl {_fmt_usd(pnl_live if pnl_live is not None else 0.0)} | pnl pct {_fmt_pct(pnl_pct)}",
        "",
        "## Risk And Targets",
        _format_target_line("Stop", stop_price, est_stop),
        _format_target_line("TP1", tp1, est_tp1),
        _format_target_line("TP2", tp2, est_tp2),
        _format_target_line("TP3", tp3, est_tp3),
    ]
    if fees_est is not None or min_profit is not None or recovery_target is not None:
        lines.append("")
        lines.append("## Profit Plan")
        if fees_est is not None:
            lines.append(f"- Estimated round-trip fees: {_fmt_usd(fees_est)}")
        if min_profit is not None:
            lines.append(f"- Minimum acceptable exit after fees: {_fmt_usd(min_profit)}")
        if recovery_target is not None and recovery_target > 0:
            lines.append(f"- Recovery target on this trade: {_fmt_usd(recovery_target)}")
    if ai_action or ai_conf is not None:
        lines.append("")
        lines.append("## AI Read")
        ai_parts = []
        if ai_action:
            ai_parts.append(f"action {ai_action}")
        if ai_conf is not None:
            ai_parts.append(f"confidence {ai_conf}")
        lines.append("- " + " | ".join(ai_parts))
    lines.extend(
        [
            "",
            "## After This Trade",
            _format_next_play("Next long", ctx.get("next_play_long")),
            _format_next_play("Next short", ctx.get("next_play_short")),
        ]
    )
    summary = f"{headline}. {context_line}."
    return "\n".join(lines), summary


def bot_pulse(state: dict, ctx: dict) -> None:
    regime = state.get("regime") or ctx.get("regime") or ctx.get("pulse_regime") or "?"
    vol_state = state.get("vol_state") or ctx.get("vol_state", "?")
    price = float(ctx.get("price") or ctx.get("mark_price") or 0.0)
    thought = str(ctx.get("thought") or "watching for a clean setup")
    trades_today = int(state.get("trades") or state.get("trades_today") or 0)
    pnl_today = float(state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd") or 0.0)

    lines = [
        f":satellite_antenna: *MARKET UPDATE* -- {_slack._now_pt()}",
        f"Price: ${price:.5f} | Regime: {regime} | Vol: {vol_state}",
        f"Today: trades={trades_today} | pnl={_fmt_usd(pnl_today)}",
        f"Thought: {thought}",
    ]
    _send_canvas("\n".join(lines), "Market Update")


def account_health(state: dict, ctx: dict) -> None:
    pnl_today = float(state.get("exchange_pnl_today_usd") or state.get("pnl_today_usd") or 0.0)
    total_balance = _to_float(ctx.get("total_balance"), None)
    equity = _to_float(ctx.get("equity"), None)
    margin_ratio = _to_float(ctx.get("margin_ratio"), None)
    direction = "Flat"
    open_pos = state.get("open_position")
    if isinstance(open_pos, dict):
        direction = str(open_pos.get("direction") or "Flat")
    source_note = ""
    if equity is None and total_balance is not None:
        source_note = "Note: derivatives equity unavailable, showing wallet cash only."
    elif total_balance is None and equity is not None:
        total_balance = equity
    elif total_balance is None and equity is None and state.get("equity_start_usd") not in (None, ""):
        total_balance = _to_float(state.get("equity_start_usd"), None)
        source_note = "Note: live balance feed unavailable, showing session baseline only."

    lines = [
        f":bank: *ACCOUNT HEALTH REPORT* -- {_slack._now_pt()}",
        f"Balances: Total: {_fmt_optional_usd(total_balance)} | Equity: {_fmt_optional_usd(equity)}",
        f"P&L Today: {_pnl_emoji(pnl_today)} {_fmt_usd(pnl_today)}",
        f"Margin: {_fmt_optional_ratio(margin_ratio)}",
        f"Position: {direction}",
    ]
    if source_note:
        lines.append(source_note)
    _send_canvas("\n".join(lines), "Account Health Summary")


def _position_update(state: dict, ctx: dict, event: str) -> None:
    report_md, _ = _build_trade_report(state, ctx, event)
    _send_canvas(report_md, f"Position Update ({event})")


def maybe_send_reports(state: dict, config: dict, ctx: dict) -> None:
    now = time.time()
    report_state = _load_report_state()
    ctx = _merge_runtime_context(state, ctx if isinstance(ctx, dict) else {})

    reporting_cfg = (config.get("reporting") or {}) if isinstance(config.get("reporting"), dict) else {}
    flat_market_interval = int(reporting_cfg.get("flat_market_interval_sec", _DEFAULT_FLAT_MARKET_INTERVAL_SEC) or _DEFAULT_FLAT_MARKET_INTERVAL_SEC)
    in_pos_interval = int(reporting_cfg.get("in_position_interval_sec", _DEFAULT_IN_POSITION_INTERVAL_SEC) or _DEFAULT_IN_POSITION_INTERVAL_SEC)
    health_interval = int(reporting_cfg.get("health_interval_sec", _DEFAULT_HEALTH_INTERVAL_SEC) or _DEFAULT_HEALTH_INTERVAL_SEC)
    unchanged_repeat_interval = int(reporting_cfg.get("unchanged_repeat_sec", _DEFAULT_UNCHANGED_REPEAT_INTERVAL_SEC) or _DEFAULT_UNCHANGED_REPEAT_INTERVAL_SEC)
    market_repeat_interval = int(reporting_cfg.get("flat_market_unchanged_repeat_sec", unchanged_repeat_interval) or unchanged_repeat_interval)
    health_repeat_interval = int(reporting_cfg.get("health_unchanged_repeat_sec", unchanged_repeat_interval) or unchanged_repeat_interval)
    flat_market_interval = max(flat_market_interval, 60)
    in_pos_interval = max(in_pos_interval, 30)
    health_interval = max(health_interval, 300)
    market_repeat_interval = max(market_repeat_interval, flat_market_interval)
    health_repeat_interval = max(health_repeat_interval, health_interval)

    open_pos = state.get("open_position") if isinstance(state.get("open_position"), dict) else None
    in_position = bool(open_pos)
    prev_in_position = bool(report_state.get("last_in_position"))
    prev_position_key = str(report_state.get("last_position_key") or "")
    curr_position_key = _position_key(open_pos)

    if in_position and (not prev_in_position or curr_position_key != prev_position_key):
        _position_update(state, ctx, "ENTRY")
        report_state["last_position_ts"] = now
    elif (not in_position) and prev_in_position:
        _position_update(state, ctx, "EXIT")
        report_state["last_position_ts"] = now

    if in_position and (now - float(report_state.get("last_position_ts") or 0.0) >= in_pos_interval):
        _position_update(state, ctx, "LIVE")
        report_state["last_position_ts"] = now

    if (not in_position) and (now - float(report_state.get("last_market_ts") or 0.0) >= flat_market_interval):
        market_fingerprint = _market_fingerprint(state, ctx)
        last_market_fingerprint = str(report_state.get("last_market_fingerprint") or "")
        last_market_ts = float(report_state.get("last_market_ts") or 0.0)
        if market_fingerprint != last_market_fingerprint or (now - last_market_ts) >= market_repeat_interval:
            bot_pulse(state, ctx)
            report_state["last_market_ts"] = now
            report_state["last_market_fingerprint"] = market_fingerprint

    if now - float(report_state.get("last_health_ts") or 0.0) >= health_interval:
        health_fingerprint = _health_fingerprint(state, ctx)
        last_health_fingerprint = str(report_state.get("last_health_fingerprint") or "")
        last_health_ts = float(report_state.get("last_health_ts") or 0.0)
        if health_fingerprint != last_health_fingerprint or (now - last_health_ts) >= health_repeat_interval:
            account_health(state, ctx)
            report_state["last_health_ts"] = now
            report_state["last_health_fingerprint"] = health_fingerprint

    report_state["last_in_position"] = in_position
    report_state["last_position_key"] = curr_position_key if in_position else ""
    _save_report_state(report_state)
