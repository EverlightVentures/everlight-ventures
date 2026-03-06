from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from execution.coinbase_advanced import CoinbaseAdvanced
from state_store import StateStore


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


def _pick(d: dict, keys: tuple[str, ...]) -> Any | None:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _parse_position(p: dict, config: dict) -> dict | None:
    """
    Best-effort parsing of Coinbase CFM position payloads.
    We intentionally keep this permissive to survive schema shifts.
    """
    product_id = _pick(p, ("product_id", "productId", "symbol", "instrument_id"))
    if not product_id:
        return None

    # Size can show up as net_size, contracts, base_size, etc.
    raw_size = _pick(p, ("net_size", "size", "base_size", "position_size", "contracts"))
    size_f = _as_float(raw_size)
    if size_f is None:
        return None
    if abs(size_f) <= 0:
        return None

    side = _pick(p, ("side", "position_side", "direction"))
    if isinstance(side, str):
        s = side.lower()
        if "short" in s:
            direction = "short"
        elif "long" in s:
            direction = "long"
        elif "sell" in s:
            direction = "short"
        elif "buy" in s:
            direction = "long"
        else:
            direction = "long" if size_f > 0 else "short"
    else:
        direction = "long" if size_f > 0 else "short"

    entry_price = _as_float(_pick(p, ("avg_entry_price", "average_entry_price", "entry_price", "entryPrice", "avg_price")))
    leverage = _as_int(_pick(p, ("leverage", "effective_leverage"))) or int(config.get("leverage") or 1)

    opened_at = _pick(p, ("opened_at", "open_time", "created_at", "timestamp"))
    # If we can't parse, we fall back to "now" in caller.
    entry_time_iso = None
    if isinstance(opened_at, str):
        try:
            entry_time_iso = datetime.fromisoformat(opened_at.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except Exception:
            entry_time_iso = None

    return {
        "product_id": str(product_id),
        "direction": direction,
        "size": int(abs(size_f)),
        "entry_price": float(entry_price) if entry_price is not None else None,
        "leverage": int(leverage),
        "entry_time": entry_time_iso,
        "raw": p,
    }


def reconcile_state_with_exchange(
    api: CoinbaseAdvanced,
    config: dict,
    state: dict,
    store: StateStore | None,
    now: datetime | None = None,
) -> dict:
    """
    Crash recovery routine.

    - If exchange has an open XLM position but state.json does not, reconstruct open_position.
    - If state.json thinks we're in a position but exchange does not, clear it.
    - If both exist, fill missing fields from exchange.
    """
    now = now or _utc_now()
    open_pos = state.get("open_position")

    # Coinbase API: list all CFM positions, then pick the one that corresponds to this bot.
    #
    # Important: CFM futures product IDs (e.g. "XLP-20DEC30-CDE") do not necessarily contain the
    # underlying spot symbol ("XLM"), so we cannot rely on substring matching.
    positions = api.get_futures_positions()

    expected_product_ids: set[str] = set()
    for k in ("product_id", "futures_product_id"):
        v = config.get(k)
        if isinstance(v, str) and v:
            expected_product_ids.add(v)
    try:
        sel_long = api.select_xlm_product(config.get("selector", {}), direction="long") or {}
        sel_short = api.select_xlm_product(config.get("selector", {}), direction="short") or {}
        if sel_long.get("product_id"):
            expected_product_ids.add(str(sel_long["product_id"]))
        if sel_short.get("product_id"):
            expected_product_ids.add(str(sel_short["product_id"]))
    except Exception:
        # Selection is best-effort; recovery must not fail because selection fails.
        pass

    parsed: list[dict] = []
    for p in positions:
        pp = _parse_position(p or {}, config)
        if not pp:
            continue

        pid = str(pp.get("product_id") or "")
        if expected_product_ids:
            if pid not in expected_product_ids:
                continue
        else:
            # Last-resort fallback: use product display_name if available.
            details = api.get_product_details(pid) or {}
            dn = str(details.get("display_name") or "")
            if "XLM" not in dn.upper():
                continue

        parsed.append(pp)

    # If multiple matches exist, pick the largest by size.
    exch_pos = sorted(parsed, key=lambda d: int(d.get("size") or 0), reverse=True)[0] if parsed else None

    if exch_pos and not open_pos:
        last_known = store.get_kv("open_position") if store else None
        entry_px = exch_pos.get("entry_price")
        if (entry_px is None or float(entry_px) <= 0) and isinstance(last_known, dict):
            entry_px = last_known.get("entry_price")
        entry_time_iso = exch_pos.get("entry_time")
        if not entry_time_iso and isinstance(last_known, dict):
            entry_time_iso = last_known.get("entry_time")

        recovered = {
            "product_id": str(exch_pos.get("product_id") or ""),
            "entry_time": entry_time_iso or now.isoformat(),
            "entry_price": float(entry_px or 0.0),
            "direction": exch_pos["direction"],
            "size": int(exch_pos["size"]),
            "leverage": int(exch_pos["leverage"]),
            "adverse_bars": 0,
            "contract_size": None,
            "rescue_done": False,
            "breakout_type": "unknown",
            "breakout_tf": "unknown",
            "recovered": True,
        }
        state["open_position"] = recovered
        if store:
            store.log_event("recovered_open_position", {"product_id": exch_pos["product_id"], "direction": exch_pos["direction"], "size": exch_pos["size"]})
            store.set_kv("open_position", recovered)
        return state

    if open_pos and not exch_pos:
        state["open_position"] = None
        if store:
            store.log_event("cleared_stale_open_position", {"reason": "no_exchange_position"})
            store.set_kv("open_position", None)
        return state

    if open_pos and exch_pos:
        # Fill in any missing values without clobbering strategy-specific fields.
        if not open_pos.get("product_id"):
            open_pos["product_id"] = str(exch_pos.get("product_id") or "")
        if not open_pos.get("entry_time"):
            open_pos["entry_time"] = exch_pos.get("entry_time") or now.isoformat()
        if not open_pos.get("entry_price"):
            open_pos["entry_price"] = float(exch_pos.get("entry_price") or 0.0)
        if not open_pos.get("direction"):
            open_pos["direction"] = exch_pos["direction"]
        if not open_pos.get("size"):
            open_pos["size"] = int(exch_pos["size"])
        if not open_pos.get("leverage"):
            open_pos["leverage"] = int(exch_pos["leverage"])
        state["open_position"] = open_pos
        if store:
            store.set_kv("open_position", open_pos)
        return state

    return state
