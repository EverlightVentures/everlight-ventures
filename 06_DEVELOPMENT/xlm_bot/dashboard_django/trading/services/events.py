"""
Events service -- merge multiple event sources into a unified timeline.

Produces a chronological list of dicts for the Major Events panel.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from .formatters import coerce_ts_utc, format_money, safe_float, safe_str


# ---------------------------------------------------------------------------
# Per-source event extractors
# ---------------------------------------------------------------------------

def _major_from_decision(row: dict) -> dict | None:
    reason = safe_str(row.get("reason"))
    if not reason:
        return None
    reason_l = reason.lower()
    ts = coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None

    exit_reason = safe_str(row.get("exit_reason")).lower()
    direction = safe_str(row.get("direction")).upper()
    product = safe_str(row.get("product_id")) or safe_str(row.get("product_selected")) or "-"

    if reason_l == "exit_order_sent":
        _entry_px = safe_float(row.get("entry_price"), default=None)
        _exit_px = safe_float(row.get("exit_price"), default=None) or safe_float(
            row.get("price"), default=None
        )
        _pnl_usd = safe_float(row.get("pnl_usd"), default=None)
        _pnl_part = ""
        if _entry_px and _exit_px:
            _pnl_part = f"${_entry_px:.5f} -> ${_exit_px:.5f}"
            if _pnl_usd is not None:
                _pnl_part += f" = {'+'if _pnl_usd >= 0 else ''}${_pnl_usd:.2f}"
        elif _pnl_usd is not None:
            _pnl_part = f"{'+'if _pnl_usd >= 0 else ''}${_pnl_usd:.2f}"
        _detail = f"{product} {direction} {_pnl_part}".strip()

        if exit_reason in ("tp1", "profit_lock", "recovery_take_profit"):
            return {"ts": ts, "tone": "good", "headline": f"TAKE PROFIT ({exit_reason})", "detail": _detail}
        if exit_reason in ("emergency_exit_mr", "plrl3_exit", "cutoff_derisk"):
            return {"ts": ts, "tone": "bad", "headline": f"RISK EXIT ({exit_reason})", "detail": _detail}
        return {"ts": ts, "tone": "warn", "headline": f"POSITION EXIT ({exit_reason or 'signal'})", "detail": _detail}

    if reason_l == "exchange_side_close":
        pnl = safe_float(row.get("pnl_usd"), default=None)
        result = safe_str(row.get("result")).lower()
        tone = (
            "good" if result == "win" or (pnl is not None and pnl > 0) else
            "bad" if result == "loss" or (pnl is not None and pnl < 0) else
            "warn"
        )
        return {
            "ts": ts,
            "tone": tone,
            "headline": "EXCHANGE-SIDE CLOSE",
            "detail": f"{product} pnl {format_money(pnl) if pnl is not None else 'n/a'}",
        }

    if reason_l in ("plrl3_rescue", "trend_scale_in"):
        add = int(safe_float(row.get("add_contracts") or row.get("add_size")))
        return {"ts": ts, "tone": "warn", "headline": "POSITION ADD", "detail": f"{product} +{add} contracts"}

    if reason_l == "entry_order_failed":
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "ENTRY FAILED",
            "detail": f"{product} {safe_str(row.get('message'))}".strip(),
        }

    return None


def _major_from_trade(row: dict) -> dict | None:
    ts = coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None
    product = safe_str(row.get("product_id")) or "-"
    side = safe_str(row.get("side")).upper()
    result = safe_str(row.get("result")).lower()
    exit_reason = safe_str(row.get("exit_reason")).lower()
    pnl = safe_float(row.get("pnl_usd"), default=None)
    has_exit = safe_float(row.get("exit_price"), default=None) is not None

    if not has_exit:
        if result in ("ok", "paper mode") or safe_str(row.get("order_id")):
            return {
                "ts": ts,
                "tone": "info",
                "headline": "ENTRY",
                "detail": f"{product} {side} {int(safe_float(row.get('size')))}c".strip(),
            }
        return None

    if exit_reason in ("tp1", "profit_lock", "recovery_take_profit"):
        tone = "good"
        headline = f"TAKE PROFIT ({exit_reason})"
    elif result == "win" or (pnl is not None and pnl > 0):
        tone = "good"
        headline = "CLOSED WIN"
    elif result == "loss" or (pnl is not None and pnl < 0):
        tone = "bad"
        headline = "CLOSED LOSS"
    else:
        tone = "warn"
        headline = f"CLOSED ({exit_reason or 'flat'})"

    return {
        "ts": ts,
        "tone": tone,
        "headline": headline,
        "detail": f"{product} {side} pnl {format_money(pnl) if pnl is not None else 'n/a'}",
    }


def _major_from_incident(row: dict) -> dict | None:
    ts = coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None
    itype = safe_str(row.get("type")).upper()
    product = safe_str(row.get("product_id")) or "-"
    if not itype:
        return None

    if itype == "LIQUIDATION_TIER_OBSERVED":
        mr = safe_float(row.get("active_mr"), default=None)
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "LIQUIDATION TIER",
            "detail": f"{product} active_mr={mr:.3f}" if mr is not None else product,
        }
    if itype in ("EMERGENCY_EXIT_TRIGGERED", "CLOSE_NOT_REDUCE_ONLY"):
        return {"ts": ts, "tone": "bad", "headline": itype.replace("_", " "), "detail": product}
    if itype in ("RECONCILE_MISMATCH", "EXCHANGE_SIDE_CLOSE_DETECTED"):
        return {"ts": ts, "tone": "warn", "headline": itype.replace("_", " "), "detail": product}
    return None


def _major_from_cash_movement(row: dict) -> dict | None:
    ts = coerce_ts_utc(row.get("timestamp"))
    if ts is None:
        return None
    mtype = safe_str(row.get("type")).upper()
    if not mtype:
        return None
    context = safe_str(row.get("context")).lower()
    amount = safe_float(row.get("amount_usd"), default=None)
    currency = safe_str(row.get("currency")) or "USD"
    currency = currency.upper()
    shortfall = safe_float(row.get("shortfall_usd"), default=None)
    conv = safe_float(row.get("estimated_conversion_cost_usd"), default=None)
    detail_ctx = f" ({context})" if context else ""

    if mtype == "SPOT_TO_FUTURES_TRANSFER":
        detail = f"{format_money(amount)} {currency} to futures{detail_ctx}".strip()
        if conv is not None and conv > 0:
            detail += f" | est conversion cost {format_money(conv)}"
        return {"ts": ts, "tone": "warn", "headline": "MARGIN TRANSFER IN", "detail": detail}
    if mtype == "FUTURES_TO_SPOT_TRANSFER":
        return {
            "ts": ts,
            "tone": "good",
            "headline": "PROFIT TRANSFER OUT",
            "detail": f"{format_money(amount)} {currency} to spot{detail_ctx}".strip(),
        }
    if mtype in ("SPOT_TO_FUTURES_TRANSFER_FAILED", "FUTURES_TO_SPOT_TRANSFER_FAILED"):
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "TRANSFER FAILED",
            "detail": f"{mtype.replace('_', ' ').title()}{detail_ctx}",
        }
    if mtype == "FUNDING_SHORTFALL":
        return {
            "ts": ts,
            "tone": "bad",
            "headline": "FUNDING SHORTFALL",
            "detail": f"shortfall {format_money(shortfall)}{detail_ctx}",
        }
    if mtype == "SPOT_CONVERSION_DETECTED":
        return {
            "ts": ts,
            "tone": "warn",
            "headline": "SPOT CONVERSION DETECTED",
            "detail": f"USD/USDC balances changed{detail_ctx}",
        }
    if mtype == "SPOT_BALANCE_DELTA":
        return {
            "ts": ts,
            "tone": "info",
            "headline": "SPOT BALANCE CHANGE",
            "detail": f"manual/account movement detected{detail_ctx}",
        }
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_major_events(
    decisions,
    trades_df,
    incidents,
    cash_movements,
    lookback_days: int = 7,
    max_items: int = 80,
) -> list[dict]:
    """Merge all event sources into a de-duplicated chronological list.

    Each source can be a list[dict] or a pd.DataFrame.
    Returns list of dicts: {ts, tone, headline, detail}.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(lookback_days)))
    out: list[dict] = []

    def _iter_rows(source):
        if source is None:
            return
        if isinstance(source, pd.DataFrame):
            if source.empty:
                return
            for _, r in source.iterrows():
                yield r.to_dict() if hasattr(r, "to_dict") else dict(r)
        elif isinstance(source, list):
            yield from source

    for row in _iter_rows(decisions):
        ev = _major_from_decision(row)
        if ev and ev.get("ts") and ev["ts"] >= cutoff:
            out.append(ev)

    for row in _iter_rows(trades_df):
        ev = _major_from_trade(row)
        if ev and ev.get("ts") and ev["ts"] >= cutoff:
            out.append(ev)

    for row in _iter_rows(incidents):
        ev = _major_from_incident(row)
        if ev and ev.get("ts") and ev["ts"] >= cutoff:
            out.append(ev)

    for row in _iter_rows(cash_movements):
        ev = _major_from_cash_movement(row)
        if ev and ev.get("ts") and ev["ts"] >= cutoff:
            out.append(ev)

    # Sort newest-first, de-duplicate.
    out.sort(key=lambda e: e.get("ts") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    dedup: list[dict] = []
    seen: set[tuple] = set()
    for e in out:
        key = (str(e.get("ts")), str(e.get("headline")), str(e.get("detail")))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(e)
        if len(dedup) >= max_items:
            break
    return dedup
