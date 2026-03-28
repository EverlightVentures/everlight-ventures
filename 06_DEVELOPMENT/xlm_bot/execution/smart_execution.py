"""
Smart Order Execution Engine
-----------------------------
Uses LIMIT (maker) orders instead of MARKET (taker) orders to save fees.
Coinbase CDE fee schedule:
  - Taker: 0.90 bps (you pay ~$0.74 per market order on typical size)
  - Maker: -0.85 bps (you EARN a rebate on limit fills)

Falls back to market orders when limit orders don't fill within timeout,
or when urgency demands immediate execution (stop loss, circuit breaker).

Does NOT import from main.py -- only uses execution/coinbase_advanced types.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

_log = logging.getLogger(__name__)

# XLM perp tick size (minimum price increment)
TICK_SIZE = 0.00001

# Coinbase CDE fee schedule (basis points)
TAKER_FEE_BPS = 0.90
MAKER_FEE_BPS = -0.85  # negative = rebate

# Default timeouts per urgency level (seconds)
DEFAULT_TIMEOUTS = {
    "emergency": 0,
    "normal": 15,
    "patient": 45,
}

# Poll interval when waiting for limit fill (seconds)
POLL_INTERVAL = 3.0


def _get_bid_ask(api: Any, product_id: str) -> tuple[float, float]:
    """
    Fetch best bid and ask from the orderbook.
    Returns (bid, ask). Raises ValueError on failure.
    """
    book = api.api.get_orderbook(product_id) or {}
    pricebook = book.get("pricebook", book)
    bids = pricebook.get("bids") or book.get("bids") or []
    asks = pricebook.get("asks") or book.get("asks") or []
    if not bids or not asks:
        raise ValueError(f"Empty orderbook for {product_id}")
    try:
        bid = float(bids[0].get("price") if isinstance(bids[0], dict) else bids[0][0])
        ask = float(asks[0].get("price") if isinstance(asks[0], dict) else asks[0][0])
    except (IndexError, TypeError, KeyError) as e:
        raise ValueError(f"Failed to parse bid/ask from orderbook: {e}")
    if bid <= 0 or ask <= 0:
        raise ValueError(f"Invalid bid/ask: bid={bid}, ask={ask}")
    return bid, ask


def _check_fill(api: Any, order_id: str) -> Optional[dict]:
    """
    Check order fill status. Returns fill info dict if filled, None otherwise.
    """
    try:
        fill = api.verify_order_fill(order_id)
        if fill and fill.get("filled"):
            return fill
    except Exception as e:
        _log.debug(f"Fill check error for {order_id}: {e}")
    return None


def _cancel_order(api: Any, order_id: str) -> bool:
    """Best-effort cancel. Returns True if cancel call succeeded."""
    try:
        api.api.cancel_order(order_id)
        return True
    except Exception as e:
        _log.warning(f"Cancel failed for {order_id}: {e}")
        return False


def _place_limit(api: Any, product_id: str, side: str, size: int, price: float) -> dict:
    """
    Place a limit order via the CFM endpoint with post_only semantics.
    Returns the raw API response dict.
    """
    # Use the vendor API directly so we can inject post_only into the config
    import secrets as _secrets

    rounded_price = api.api._round_price(price, product_id)
    rounded_size = api.api._round_base_size(size, product_id)
    if not rounded_size or rounded_size <= 0:
        return {"success": False, "failure_response": {"error": "size_too_small"}}

    order_config = {
        "base_size": str(rounded_size),
        "limit_price": str(rounded_price),
        "post_only": True,
    }
    data = {
        "client_order_id": f"smart_{side.lower()}_{int(time.time() * 1000)}_{_secrets.token_hex(4)}",
        "product_id": product_id,
        "side": side.upper(),
        "order_configuration": {
            "limit_limit_gtc": order_config,
        },
    }
    _log.info(f"Smart limit order: {product_id} {side} size={rounded_size} price={rounded_price} post_only=True")
    return api.api._request("POST", "/api/v3/brokerage/orders", data=data) or {}


def _place_market(api: Any, product_id: str, side: str, size: int) -> dict:
    """Place a market order as fallback. Returns raw API response."""
    res = api.api.place_cfm_order(
        product_id=product_id,
        side=side.upper(),
        base_size=size,
        price=None,
    )
    return res or {}


def _extract_order_id(res: dict) -> Optional[str]:
    """Pull order_id from a Coinbase v3 response."""
    return (
        res.get("order_id")
        or (res.get("success_response") or {}).get("order_id")
    )


def _build_result(
    success: bool,
    method: str,
    order_id: Optional[str] = None,
    fill_price: float = 0.0,
    size: float = 0.0,
    fees: float = 0.0,
    saved_vs_market: float = 0.0,
    error: str = "",
) -> dict:
    """Build a standardized execution result dict."""
    return {
        "success": success,
        "method": method,
        "order_id": order_id or "",
        "fill_price": fill_price,
        "size": size,
        "fees": fees,
        "saved_vs_market": saved_vs_market,
        "error": error,
    }


def _estimate_taker_fee(fill_price: float, size: float) -> float:
    """Estimate what taker fee would have been for comparison."""
    # XLM perp: 1 contract = $1 notional (contract_size from exchange)
    # Fee in USD = notional * fee_rate
    notional = fill_price * size  # approximate
    return notional * (TAKER_FEE_BPS / 10000.0)


def _wait_for_fill(api: Any, order_id: str, timeout_sec: float) -> Optional[dict]:
    """
    Poll for order fill up to timeout_sec. Returns fill dict or None.
    """
    elapsed = 0.0
    while elapsed < timeout_sec:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        fill = _check_fill(api, order_id)
        if fill:
            return fill
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def smart_entry_order(
    api: Any,
    product_id: str,
    direction: str,
    size: int,
    config: Optional[dict] = None,
) -> dict:
    """
    Place a maker (limit) entry order at an optimal price, with market fallback.

    Args:
        api: CoinbaseAdvanced instance
        product_id: e.g. "XLP-20DEC30-CDE"
        direction: "long" or "short"
        size: number of contracts
        config: optional overrides -- {"timeout_sec": 30}

    Returns:
        {"success", "method", "order_id", "fill_price", "size", "fees", "saved_vs_market"}
    """
    config = config or {}
    timeout_sec = float(config.get("timeout_sec", 30))

    try:
        bid, ask = _get_bid_ask(api, product_id)
    except ValueError as e:
        _log.error(f"Smart entry -- orderbook error: {e}")
        return _build_result(False, "failed", error=str(e))

    mid_price = (bid + ask) / 2.0
    direction_lower = direction.lower().strip()

    # Compute limit price
    if direction_lower == "long":
        # BUY at bid + 1 tick (just above best bid, still maker)
        limit_price = bid + TICK_SIZE
        side = "BUY"
    elif direction_lower == "short":
        # SELL at ask - 1 tick (just below best ask, still maker)
        limit_price = ask - TICK_SIZE
        side = "SELL"
    else:
        return _build_result(False, "failed", error=f"invalid direction: {direction}")

    _log.info(
        f"Smart entry: {direction_lower} {size} @ limit {limit_price:.5f} "
        f"(bid={bid:.5f} ask={ask:.5f} mid={mid_price:.5f}) timeout={timeout_sec}s"
    )

    # Place limit order with post_only
    res = _place_limit(api, product_id, side, size, limit_price)
    if not res.get("success", True) is not False:
        pass  # success field may be absent on 200 OK
    order_id = _extract_order_id(res)

    if not order_id:
        # Limit order rejected -- immediate market fallback
        fail_msg = (res.get("failure_response") or {}).get("error", "limit_rejected")
        _log.warning(f"Limit entry rejected ({fail_msg}), falling back to market")
        return _market_fallback(api, product_id, side, size, "entry")

    # Wait for fill
    fill = _wait_for_fill(api, order_id, timeout_sec)

    if fill:
        fill_price = float(fill.get("average_filled_price", 0))
        fill_size = float(fill.get("filled_size", size))
        fill_fees = float(fill.get("total_fees", 0))
        taker_fee_est = _estimate_taker_fee(fill_price, fill_size)
        saved = taker_fee_est - fill_fees  # maker rebate means fees could be negative
        _log.info(
            f"Smart entry FILLED (maker): {fill_size} @ {fill_price:.5f}, "
            f"fees=${fill_fees:.4f}, saved=${saved:.4f} vs taker"
        )
        return _build_result(
            success=True,
            method="maker",
            order_id=order_id,
            fill_price=fill_price,
            size=fill_size,
            fees=fill_fees,
            saved_vs_market=saved,
        )

    # Not filled -- cancel and fall back to market
    _log.info(f"Limit entry {order_id} not filled in {timeout_sec}s, cancelling -> market")
    _cancel_order(api, order_id)
    time.sleep(0.3)  # brief pause after cancel

    return _market_fallback(api, product_id, side, size, "entry")


def _market_fallback(
    api: Any,
    product_id: str,
    side: str,
    size: int,
    context: str,
) -> dict:
    """Place a market order as fallback after limit timeout/rejection."""
    res = _place_market(api, product_id, side, size)
    order_id = _extract_order_id(res)

    if not order_id:
        fail_msg = (res.get("failure_response") or {}).get("error", "market_order_failed")
        _log.error(f"Market {context} also failed: {fail_msg}")
        return _build_result(False, "failed", error=fail_msg)

    # Give market order a moment to fill, then check
    time.sleep(1.0)
    fill = _check_fill(api, order_id)

    fill_price = 0.0
    fill_size = float(size)
    fill_fees = 0.0

    if fill:
        fill_price = float(fill.get("average_filled_price", 0))
        fill_size = float(fill.get("filled_size", size))
        fill_fees = float(fill.get("total_fees", 0))

    _log.info(f"Market {context} fallback: {fill_size} @ {fill_price:.5f}, fees=${fill_fees:.4f}")
    return _build_result(
        success=True,
        method="taker",
        order_id=order_id,
        fill_price=fill_price,
        size=fill_size,
        fees=fill_fees,
        saved_vs_market=0.0,
    )


def smart_exit_order(
    api: Any,
    product_id: str,
    direction: str,
    size: int,
    urgency: str = "normal",
    config: Optional[dict] = None,
) -> dict:
    """
    Exit a position with limit or market order based on urgency.

    Args:
        api: CoinbaseAdvanced instance
        product_id: e.g. "XLP-20DEC30-CDE"
        direction: "long" or "short" (the position being closed)
        size: number of contracts to close
        urgency: "emergency" | "normal" | "patient"
        config: optional overrides

    Returns:
        {"success", "method", "order_id", "fill_price", "size", "fees", "saved_vs_market"}
    """
    config = config or {}
    urgency = urgency.lower().strip()

    # Determine exit side (opposite of position direction)
    direction_lower = direction.lower().strip()
    if direction_lower == "long":
        side = "SELL"
    elif direction_lower == "short":
        side = "BUY"
    else:
        return _build_result(False, "failed", error=f"invalid direction: {direction}")

    # Emergency -- immediate market order, no limit attempt
    if urgency == "emergency":
        _log.info(f"EMERGENCY exit: {side} {size} contracts via market order")
        return _market_fallback(api, product_id, side, size, "emergency_exit")

    # Get orderbook for limit pricing
    try:
        bid, ask = _get_bid_ask(api, product_id)
    except ValueError as e:
        _log.error(f"Smart exit -- orderbook error, falling back to market: {e}")
        return _market_fallback(api, product_id, side, size, "exit_no_book")

    mid_price = (bid + ask) / 2.0

    # Compute limit price and timeout based on urgency
    if urgency == "patient":
        timeout_sec = float(config.get("timeout_sec", 45))
        # Patient: place at a more favorable price
        if side == "SELL":
            # Selling: place at ask - 1 tick (favorable for seller)
            limit_price = ask - TICK_SIZE
        else:
            # Buying to close short: place at bid + 1 tick (favorable for buyer)
            limit_price = bid + TICK_SIZE
    else:
        # Normal urgency: mid-price, shorter timeout
        timeout_sec = float(config.get("timeout_sec", 15))
        limit_price = mid_price

    _log.info(
        f"Smart exit ({urgency}): {side} {size} @ limit {limit_price:.5f} "
        f"(bid={bid:.5f} ask={ask:.5f}) timeout={timeout_sec}s"
    )

    # Place limit order
    res = _place_limit(api, product_id, side, size, limit_price)
    order_id = _extract_order_id(res)

    if not order_id:
        fail_msg = (res.get("failure_response") or {}).get("error", "limit_rejected")
        _log.warning(f"Limit exit rejected ({fail_msg}), falling back to market")
        return _market_fallback(api, product_id, side, size, "exit")

    # Wait for fill
    fill = _wait_for_fill(api, order_id, timeout_sec)

    if fill:
        fill_price = float(fill.get("average_filled_price", 0))
        fill_size = float(fill.get("filled_size", size))
        fill_fees = float(fill.get("total_fees", 0))
        taker_fee_est = _estimate_taker_fee(fill_price, fill_size)
        saved = taker_fee_est - fill_fees
        _log.info(
            f"Smart exit FILLED (maker): {fill_size} @ {fill_price:.5f}, "
            f"fees=${fill_fees:.4f}, saved=${saved:.4f} vs taker"
        )
        return _build_result(
            success=True,
            method="maker",
            order_id=order_id,
            fill_price=fill_price,
            size=fill_size,
            fees=fill_fees,
            saved_vs_market=saved,
        )

    # Not filled -- cancel and market fallback
    _log.info(f"Limit exit {order_id} not filled in {timeout_sec}s, cancelling -> market")
    _cancel_order(api, order_id)
    time.sleep(0.3)

    return _market_fallback(api, product_id, side, size, "exit")


def compute_execution_cost(
    spread_pct: float,
    size_contracts: int,
    method: str = "taker",
    price: float = 0.0,
) -> dict:
    """
    Pre-compute expected execution cost before placing an order.

    Args:
        spread_pct: current spread as a percentage (e.g. 0.05 for 0.05%)
        size_contracts: number of contracts
        method: "taker" or "maker"
        price: current price (for USD cost estimate). If 0, USD costs are 0.

    Returns:
        {"method", "fee_bps", "spread_cost_bps", "total_cost_bps", "cost_usd", "savings_vs_taker"}
    """
    spread_bps = spread_pct * 100  # convert pct to bps (0.05% -> 5 bps)

    if method == "maker":
        fee_bps = MAKER_FEE_BPS  # negative = rebate
        spread_cost_bps = 0.0  # maker sits on the book, no spread crossing
    else:
        fee_bps = TAKER_FEE_BPS
        spread_cost_bps = spread_bps / 2.0  # crossing half the spread

    total_cost_bps = fee_bps + spread_cost_bps

    # USD cost estimate
    # XLM perp notional ~ price * size (1 contract ~ 1 XLM equivalent)
    notional = price * size_contracts if price > 0 else 0.0
    cost_usd = notional * (total_cost_bps / 10000.0)

    # Taker baseline for comparison
    taker_total_bps = TAKER_FEE_BPS + (spread_bps / 2.0)
    taker_cost_usd = notional * (taker_total_bps / 10000.0)
    savings_vs_taker = taker_cost_usd - cost_usd

    return {
        "method": method,
        "fee_bps": fee_bps,
        "spread_cost_bps": spread_cost_bps,
        "total_cost_bps": total_cost_bps,
        "cost_usd": cost_usd,
        "savings_vs_taker": savings_vs_taker,
    }


def should_use_limit(
    spread_pct: float,
    atr_pct: float,
    urgency: str = "normal",
) -> bool:
    """
    Decide whether to use a limit (maker) order or market (taker) order.

    Args:
        spread_pct: current spread as percentage (e.g. 0.05 for 0.05%)
        atr_pct: ATR as percentage of price (e.g. 1.5 for 1.5%)
        urgency: "emergency" | "normal" | "patient"

    Returns:
        True if limit order is recommended, False for market.
    """
    urgency = urgency.lower().strip()

    # Emergency -- always market, no time to wait
    if urgency == "emergency":
        return False

    # Wide spread -- limit order saves real money
    if spread_pct > 0.15:
        return True

    # Tight spread -- market is fine, not worth the fill risk
    if spread_pct < 0.03:
        return False

    # High volatility -- price moving fast, limit may miss
    if atr_pct > 1.0:
        return False

    # Default: use limit for moderate conditions
    return True
