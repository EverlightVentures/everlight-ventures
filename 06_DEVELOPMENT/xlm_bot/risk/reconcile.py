from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from state_store import StateStore


@dataclass
class ReconcileOutcome:
    state: dict
    incidents: list[dict]
    closed_trade: dict | None
    repaired: bool


def _pick(d: dict, keys: tuple[str, ...]) -> Any | None:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _as_float(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _as_int(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except Exception:
        return None


def _parse_ts_utc(raw: Any) -> datetime | None:
    try:
        if raw is None:
            return None
        s = str(raw).strip()
        if not s:
            return None
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _minutes_between(start: Any, end: Any) -> float | None:
    a = _parse_ts_utc(start)
    b = _parse_ts_utc(end)
    if not a or not b:
        return None
    return max(0.0, (b - a).total_seconds() / 60.0)


def _product_ids(api, config: dict, local_open: dict | None) -> set[str]:
    out: set[str] = set()
    for k in ("product_id", "futures_product_id"):
        v = config.get(k)
        if isinstance(v, str) and v:
            out.add(v)
    if isinstance(local_open, dict):
        pid = local_open.get("product_id")
        if isinstance(pid, str) and pid:
            out.add(pid)
    try:
        sel_l = api.select_xlm_product(config.get("selector", {}), direction="long") or {}
        sel_s = api.select_xlm_product(config.get("selector", {}), direction="short") or {}
        if sel_l.get("product_id"):
            out.add(str(sel_l["product_id"]))
        if sel_s.get("product_id"):
            out.add(str(sel_s["product_id"]))
    except Exception:
        pass
    return out


def _parse_exchange_position(p: dict, default_leverage: int) -> dict | None:
    product_id = _pick(p, ("product_id", "productId", "symbol", "instrument_id"))
    if not product_id:
        return None
    raw_size = _pick(p, ("number_of_contracts", "contracts", "size", "base_size", "position_size", "net_size"))
    size_f = _as_float(raw_size)
    if size_f is None or abs(size_f) <= 0:
        return None
    side = str(_pick(p, ("side", "position_side", "direction")) or "").lower()
    if "short" in side or "sell" in side:
        direction = "short"
    elif "long" in side or "buy" in side:
        direction = "long"
    else:
        direction = "short" if size_f < 0 else "long"
    entry_price = _as_float(_pick(p, ("avg_entry_price", "average_entry_price", "entry_price", "entryPrice", "avg_price")))
    liquidation_price = _as_float(
        _pick(
            p,
            (
                "liquidation_price",
                "liquidationPrice",
                "liquidation",
                "estimated_liquidation_price",
                "est_liquidation_price",
                "liquidation_trigger_price",
            ),
        )
    )
    leverage = _as_int(_pick(p, ("leverage", "effective_leverage"))) or default_leverage
    return {
        "product_id": str(product_id),
        "direction": direction,
        "size": int(abs(size_f)),
        "entry_price": float(entry_price) if entry_price is not None else None,
        "liquidation_price": float(liquidation_price) if liquidation_price is not None else None,
        "leverage": int(leverage),
        "raw": p,
    }


def _contract_size(api, product_id: str) -> float | None:
    try:
        details = api.get_product_details(product_id) or {}
        fpd = details.get("future_product_details") or {}
        cs = _as_float(fpd.get("contract_size"))
        return cs if cs and cs > 0 else None
    except Exception:
        return None


def _is_mismatch(local_open: dict, exch: dict) -> bool:
    if str(local_open.get("product_id") or "") != str(exch.get("product_id") or ""):
        return True
    if str(local_open.get("direction") or "") != str(exch.get("direction") or ""):
        return True
    try:
        if int(local_open.get("size") or 0) != int(exch.get("size") or 0):
            return True
    except Exception:
        return True
    ep_local = _as_float(local_open.get("entry_price"))
    ep_exch = _as_float(exch.get("entry_price"))
    if ep_local and ep_exch:
        if abs(ep_local - ep_exch) / max(abs(ep_local), 1e-9) > 0.002:
            return True
    return False


def _build_exchange_close_trade(
    now: datetime,
    local_open: dict,
    mark_price: float | None,
    contract_size: float | None,
) -> dict:
    entry = float(local_open.get("entry_price") or 0.0)
    exit_px = float(mark_price or entry or 0.0)
    direction = str(local_open.get("direction") or "long")
    size = int(local_open.get("size") or 0)
    pnl_pct = 0.0
    if entry > 0:
        pnl_pct = (exit_px - entry) / entry
        if direction == "short":
            pnl_pct = -pnl_pct
    pnl_usd = None
    if contract_size and size > 0:
        raw = (exit_px - entry) * float(contract_size) * size
        pnl_usd = -raw if direction == "short" else raw
    result = "win" if pnl_pct > 0 else "loss" if pnl_pct < 0 else "flat"
    entry_time = local_open.get("entry_time")
    exit_time = now.isoformat()
    dur_min = _minutes_between(entry_time, exit_time)
    return {
        "timestamp": now.isoformat(),
        "product_id": str(local_open.get("product_id") or ""),
        "side": direction,
        "size": size,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "time_in_trade_min": round(float(dur_min), 2) if dur_min is not None else None,
        "entry_price": entry if entry > 0 else None,
        "exit_price": exit_px if exit_px > 0 else None,
        "pnl_pct": pnl_pct,
        "pnl_usd": pnl_usd,
        "result": result,
        "exit_reason": "exchange_side_close",
    }


def reconcile_exchange_truth(
    api,
    config: dict,
    state: dict,
    store: StateStore | None,
    *,
    now: datetime | None = None,
    mark_price: float | None = None,
) -> ReconcileOutcome:
    """
    Exchange-truth reconciliation:
    - Exchange open position + no local state => reconstruct local.
    - Local open position + no exchange position => force-close locally as exchange_side_close.
    - Both present but mismatched => sync local to exchange.
    """
    now = now or datetime.now(timezone.utc)
    incidents: list[dict] = []
    closed_trade: dict | None = None
    repaired = False

    local_open = state.get("open_position") if isinstance(state.get("open_position"), dict) else None
    expected_ids = _product_ids(api, config, local_open)

    positions = []
    _positions_fetch_ok = False
    open_orders = []
    try:
        positions = api.get_futures_positions() or []
        _positions_fetch_ok = True
    except Exception as e:
        incidents.append({"timestamp": now.isoformat(), "type": "RECONCILE_ERROR", "error": f"positions_fetch_failed: {e}"})
    try:
        open_orders = api.get_open_orders() or []
    except Exception as e:
        incidents.append({"timestamp": now.isoformat(), "type": "RECONCILE_ERROR", "error": f"open_orders_fetch_failed: {e}"})

    parsed: list[dict] = []
    unexpected_positions: list[dict] = []
    default_lev = int(config.get("leverage") or 1)
    for p in positions:
        pp = _parse_exchange_position(p or {}, default_lev)
        if not pp:
            continue
        pid = str(pp.get("product_id") or "")
        if expected_ids and pid not in expected_ids:
            # Track unexpected positions for alerting
            unexpected_positions.append(pp)
            continue
        if not expected_ids and ("XLM" not in pid.upper() and "XLP" not in pid.upper()):
            unexpected_positions.append(pp)
            continue
        parsed.append(pp)

    # Alert on unauthorized positions found on the account
    for _unexp in unexpected_positions:
        _u_pid = _unexp.get("product_id", "?")
        _u_side = _unexp.get("direction", "?")
        _u_size = _unexp.get("size", "?")
        incidents.append({
            "timestamp": now.isoformat(),
            "type": "UNAUTHORIZED_POSITION_DETECTED",
            "product_id": _u_pid,
            "direction": _u_side,
            "size": _u_size,
            "severity": "CRITICAL",
            "message": f"Position found on {_u_pid} ({_u_side} x{_u_size}) — NOT managed by this bot",
        })

    exch_pos = None
    if parsed:
        if local_open and local_open.get("product_id"):
            local_pid = str(local_open.get("product_id"))
            for pp in parsed:
                if str(pp.get("product_id")) == local_pid:
                    exch_pos = pp
                    break
        if exch_pos is None:
            parsed.sort(key=lambda d: int(d.get("size") or 0), reverse=True)
            exch_pos = parsed[0]

    # Exchange has position, local does not -> reconstruct local
    # GUARD: skip reconstruction if we just processed an exchange_side_close
    # (prevents ghost loop: close → reconstruct → close → reconstruct ...)
    _last_esc_ts = _parse_ts_utc(state.get("_last_exchange_close_ts"))
    _esc_cooldown_sec = 300  # 5 minutes
    _esc_too_recent = (
        _last_esc_ts is not None
        and (now - _last_esc_ts).total_seconds() < _esc_cooldown_sec
    )
    if exch_pos and not local_open and _esc_too_recent:
        incidents.append({
            "timestamp": now.isoformat(),
            "type": "RECONCILE_RECONSTRUCTION_SUPPRESSED",
            "reason": f"exchange_side_close was {(now - _last_esc_ts).total_seconds():.0f}s ago, skipping reconstruction for {_esc_cooldown_sec}s",
            "product_id": str(exch_pos.get("product_id") or ""),
        })
        return ReconcileOutcome(state=state, incidents=incidents, closed_trade=None, repaired=False)

    if exch_pos and not local_open:
        cs = _contract_size(api, str(exch_pos.get("product_id") or ""))
        recovered = {
            "product_id": str(exch_pos.get("product_id") or ""),
            "entry_time": now.isoformat(),
            "entry_price": float(exch_pos.get("entry_price") or mark_price or 0.0),
            "direction": str(exch_pos.get("direction") or "long"),
            "size": int(exch_pos.get("size") or 0),
            "leverage": int(exch_pos.get("leverage") or default_lev),
            "stop_loss": None,
            "tp1": None,
            "tp2": None,
            "tp3": None,
            "adverse_bars": 0,
            "contract_size": cs,
            "liquidation_price": exch_pos.get("liquidation_price"),
            "rescue_done": False,
            "breakout_type": "unknown",
            "breakout_tf": "unknown",
            "recovered": True,
        }
        state["open_position"] = recovered
        repaired = True
        incidents.append(
            {
                "timestamp": now.isoformat(),
                "type": "RECONCILE_MISMATCH",
                "reason": "exchange_has_position_local_missing",
                "product_id": recovered["product_id"],
                "size": recovered["size"],
                "direction": recovered["direction"],
                "open_orders_count": len(open_orders),
            }
        )
        if store:
            store.set_kv("open_position", recovered)
            store.log_event(
                "recovered_open_position_exchange_truth",
                {"product_id": recovered["product_id"], "size": recovered["size"], "direction": recovered["direction"]},
            )
        return ReconcileOutcome(state=state, incidents=incidents, closed_trade=None, repaired=repaired)

    # Local has position, exchange does not -> exchange-side close
    # GUARD: Only declare exchange_side_close if positions fetch succeeded AND
    # a second independent check confirms position is truly gone.
    if local_open and not exch_pos:
        pid = str(local_open.get("product_id") or "")

        # Safety: if the positions fetch failed, do NOT assume exchange closed it.
        if not _positions_fetch_ok:
            incidents.append({
                "timestamp": now.isoformat(),
                "type": "RECONCILE_SKIP_CLOSE_API_ERROR",
                "product_id": pid,
                "message": "Positions fetch failed — skipping exchange_side_close to prevent ghost exit",
            })
            return ReconcileOutcome(state=state, incidents=incidents, closed_trade=None, repaired=False)

        # Double-check: call get_position() independently to confirm position is truly gone.
        # This prevents ghost exits from transient API issues returning empty position lists.
        _double_check_pos = None
        try:
            import time as _time
            _time.sleep(0.5)  # brief pause for API consistency
            _double_check_pos = api.get_position(pid)
        except Exception:
            pass
        if _double_check_pos is not None:
            _dc_size = abs(float(_double_check_pos.get("number_of_contracts") or _double_check_pos.get("size") or 0))
            if _dc_size > 0:
                # Position still exists! Do NOT declare exchange_side_close.
                incidents.append({
                    "timestamp": now.isoformat(),
                    "type": "GHOST_EXIT_PREVENTED_RECONCILER",
                    "product_id": pid,
                    "double_check_size": _dc_size,
                    "message": "Reconciler would have declared exchange_side_close but double-check found position still open",
                })
                return ReconcileOutcome(state=state, incidents=incidents, closed_trade=None, repaired=False)

        cs = _as_float(local_open.get("contract_size")) or (_contract_size(api, pid) if pid else None)
        closed_trade = _build_exchange_close_trade(now, local_open, mark_price, cs)
        state["open_position"] = None
        # Stamp close time to prevent ghost reconstruction loop
        state["_last_exchange_close_ts"] = now.isoformat()
        if closed_trade.get("result") == "loss":
            state["losses"] = int(state.get("losses") or 0) + 1
        pnl_usd = _as_float(closed_trade.get("pnl_usd"))
        if pnl_usd is not None:
            state["pnl_today_usd"] = float(state.get("pnl_today_usd") or 0.0) + pnl_usd
        repaired = True
        incidents.append(
            {
                "timestamp": now.isoformat(),
                "type": "EXCHANGE_SIDE_CLOSE_DETECTED",
                "product_id": pid,
                "direction": local_open.get("direction"),
                "size": local_open.get("size"),
                "entry_price": local_open.get("entry_price"),
                "exit_price": closed_trade.get("exit_price"),
                "pnl_usd": closed_trade.get("pnl_usd"),
                "open_orders_count": len(open_orders),
            }
        )
        if store:
            store.set_kv("open_position", None)
            store.log_event(
                "exchange_side_close_detected",
                {"product_id": pid, "pnl_usd": closed_trade.get("pnl_usd"), "exit_price": closed_trade.get("exit_price")},
            )
        return ReconcileOutcome(state=state, incidents=incidents, closed_trade=closed_trade, repaired=repaired)

    # Both have position; patch local drift
    if local_open and exch_pos and _is_mismatch(local_open, exch_pos):
        pid = str(exch_pos.get("product_id") or local_open.get("product_id") or "")
        local_open["product_id"] = pid
        local_open["direction"] = str(exch_pos.get("direction") or local_open.get("direction") or "long")
        local_open["size"] = int(exch_pos.get("size") or local_open.get("size") or 0)
        local_open["leverage"] = int(exch_pos.get("leverage") or local_open.get("leverage") or default_lev)
        if exch_pos.get("entry_price"):
            local_open["entry_price"] = float(exch_pos["entry_price"])
        if exch_pos.get("liquidation_price"):
            local_open["liquidation_price"] = float(exch_pos["liquidation_price"])
        if not local_open.get("entry_time"):
            local_open["entry_time"] = now.isoformat()
        if not local_open.get("contract_size"):
            cs = _contract_size(api, pid)
            if cs:
                local_open["contract_size"] = cs
        state["open_position"] = local_open
        repaired = True
        incidents.append(
            {
                "timestamp": now.isoformat(),
                "type": "RECONCILE_MISMATCH",
                "reason": "exchange_local_position_drift",
                "product_id": pid,
                "local": {
                    "direction": local_open.get("direction"),
                    "size": local_open.get("size"),
                    "entry_price": local_open.get("entry_price"),
                },
                "exchange": {
                    "direction": exch_pos.get("direction"),
                    "size": exch_pos.get("size"),
                    "entry_price": exch_pos.get("entry_price"),
                },
                "open_orders_count": len(open_orders),
            }
        )
        if store:
            store.set_kv("open_position", local_open)
            store.log_event("reconciled_open_position", {"product_id": pid, "size": local_open.get("size")})

    return ReconcileOutcome(state=state, incidents=incidents, closed_trade=closed_trade, repaired=repaired)
