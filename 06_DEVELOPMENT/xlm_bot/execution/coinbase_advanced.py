from __future__ import annotations

import os
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_env_dir = os.environ.get("CRYPTO_BOT_DIR", "")
if _env_dir and Path(_env_dir).is_dir():
    CRYPTO_BOT_DIR = Path(_env_dir)
else:
    _vendor = Path(__file__).resolve().parent.parent / "vendor"
    if _vendor.is_dir():
        CRYPTO_BOT_DIR = _vendor
    else:
        CRYPTO_BOT_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/crypto_bot")
if str(CRYPTO_BOT_DIR) not in sys.path:
    sys.path.insert(0, str(CRYPTO_BOT_DIR))

from utils.coinbase_api import CoinbaseAPI


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str]
    message: str


ALLOWED_PRODUCT = "XLP-20DEC30-CDE"


def _validate_product(product_id: str) -> None:
    """Hard lock: refuse to trade any product other than the authorized one."""
    if product_id != ALLOWED_PRODUCT:
        raise RuntimeError(
            f"UNAUTHORIZED INSTRUMENT: '{product_id}' — only '{ALLOWED_PRODUCT}' is allowed"
        )


class CoinbaseAdvanced:
    def __init__(self, config_path: str):
        cfg = json.loads(Path(config_path).read_text())
        exch = cfg.get("exchange", {})
        self.api = CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )

    def is_product_available(self, product_id: str) -> bool:
        products = self.api.get_cfm_futures_products() or []
        for p in products:
            if p.get("product_id") == product_id:
                return True
        return False

    def list_cfm_products(self) -> list[str]:
        products = self.api.get_cfm_futures_products() or []
        return [p.get("product_id", "") for p in products if p.get("product_id")]

    def select_xlm_product(self, selector_cfg: dict, direction: str = "long") -> dict | None:
        products = self.api.get_cfm_futures_products() or []
        xlm = []
        for p in products:
            pid = p.get("product_id", "")
            if "XLM" in pid or "XLP" in pid:
                xlm.append(p)
        if not xlm:
            return None

        min_vol = float(selector_cfg.get("min_volume_24h", 0))
        min_oi = float(selector_cfg.get("min_open_interest", 0))
        prefer_perp = bool(selector_cfg.get("prefer_perp", True))
        roll_days = int(selector_cfg.get("roll_days", 7))

        def _ok(p: dict) -> bool:
            vol = float(p.get("volume_24h") or 0)
            oi = float((p.get("future_product_details") or {}).get("open_interest") or 0)
            return vol >= min_vol and oi >= min_oi

        # Prefer perp-style if available
        if prefer_perp:
            perps = [p for p in xlm if "Perpetual" in (p.get("future_product_details") or {}).get("display_name", "")]
            perps = [p for p in perps if _ok(p)] or perps
            if perps:
                perps.sort(key=lambda p: float((p.get("future_product_details") or {}).get("open_interest") or 0), reverse=True)
                return {"product_id": perps[0].get("product_id"), "reason": "perp_preferred"}

        # Otherwise choose nearest expiry with liquidity
        def _expiry_ts(p: dict) -> float:
            details = p.get("future_product_details") or {}
            ts = details.get("contract_expiry")
            if not ts:
                return float("inf")
            try:
                from datetime import datetime
                return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                return float("inf")

        liquid = [p for p in xlm if _ok(p)] or xlm
        liquid.sort(key=_expiry_ts)

        # If multiple contracts, choose the one that favors current direction
        top = liquid[:3] if len(liquid) >= 3 else liquid
        def _mid_price(p: dict) -> float:
            return float(p.get("mid_market_price") or p.get("price") or 0)

        if direction == "long":
            top.sort(key=_mid_price)
        else:
            top.sort(key=_mid_price, reverse=True)

        return {"product_id": top[0].get("product_id"), "reason": "nearest_expiry_best_price"}

    @staticmethod
    def _parse_order_response(res: dict | None) -> OrderResult:
        """Parse Coinbase v3 order response, checking for actual success."""
        if not res:
            return OrderResult(False, None, "order failed (no response)")
        # Coinbase v3 returns {"success": true/false, "success_response": {...}, ...}
        # A 200 status with success=false is a FAILED order (e.g. insufficient margin)
        if res.get("success") is False:
            fail = res.get("failure_response") or res.get("error_response") or {}
            err_msg = fail.get("error") or fail.get("message") or fail.get("preview_failure_reason") or "unknown"
            return OrderResult(False, None, f"exchange rejected: {err_msg}")
        # Extract order_id from nested success_response
        _oid = res.get("order_id") or (res.get("success_response") or {}).get("order_id")
        if not _oid:
            return OrderResult(False, None, f"no order_id in response: {list(res.keys())}")
        return OrderResult(True, _oid, "ok")

    def place_order(self, product_id: str, side: str, size: int, leverage: int, paper: bool = True, client_order_id: str = "") -> OrderResult:
        _validate_product(product_id)
        if paper:
            return OrderResult(True, "paper-order", "paper mode")
        res = self.api.place_cfm_order(product_id=product_id, side=side, base_size=size, client_order_id=client_order_id)
        return self._parse_order_response(res)

    def place_order_with_bracket(
        self,
        product_id: str,
        side: str,
        size: int,
        *,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        paper: bool = True,
        client_order_id: str = "",
    ) -> OrderResult:
        """
        Place an entry order with an attached bracket (stop and/or take profit) when supported.

        Falls back to a plain order if the bracket is rejected by the exchange
        (e.g. stop price out of bounds for Coinbase CDE).
        """
        _validate_product(product_id)
        if paper:
            return OrderResult(True, "paper-order", "paper mode")
        # Try bracket order first
        if stop_loss is not None or take_profit is not None:
            res = self.api.place_cfm_order(
                product_id=product_id,
                side=side,
                base_size=size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                client_order_id=client_order_id,
            )
            result = self._parse_order_response(res)
            if result.success:
                return result
            # Bracket rejected — fall back to plain order (bot manages SL/TP in software)
            import logging
            logging.getLogger(__name__).warning(
                f"Bracket order rejected ({result.message}), falling back to plain order"
            )
        res = self.api.place_cfm_order(
            product_id=product_id,
            side=side,
            base_size=size,
            client_order_id=client_order_id,
        )
        return self._parse_order_response(res)

    def get_futures_positions(self) -> list[dict]:
        """Return CFM futures positions (best-effort, empty list on failure)."""
        try:
            return self.api.get_futures_positions() or []
        except Exception:
            return []

    def get_position(self, product_id: str) -> dict | None:
        """Best-effort lookup for one futures position by product_id."""
        if not product_id:
            return None
        try:
            for p in self.get_futures_positions():
                pid = (p or {}).get("product_id") or (p or {}).get("productId") or (p or {}).get("symbol")
                if str(pid) == str(product_id):
                    return p
        except Exception:
            return None
        return None

    def get_order(self, order_id: str) -> dict | None:
        """Passthrough to vendor API get_order()."""
        return self.api.get_order(order_id)

    def verify_order_fill(self, order_id: str) -> dict | None:
        """Check if an order filled on Coinbase. Returns parsed fill info or None."""
        if not order_id:
            return None
        try:
            resp = self.api.get_order(order_id)
            if not resp:
                return None
            order = resp.get("order", resp)
            status = str(order.get("status") or "").upper()
            if status != "FILLED":
                return {"status": status, "filled": False, "order_id": order_id}
            return {
                "filled": True,
                "order_id": order_id,
                "status": status,
                "filled_size": float(order.get("filled_size") or 0),
                "average_filled_price": float(order.get("average_filled_price") or 0),
                "total_fees": float(order.get("total_fees") or 0),
                "completion_percentage": order.get("completion_percentage"),
            }
        except Exception:
            return None

    def get_liquidation_price(self, product_id: str) -> float | None:
        """Extract liquidation price from the exchange position payload when available."""
        pos = self.get_position(product_id)
        if not isinstance(pos, dict):
            return None
        for key in (
            "liquidation_price",
            "liquidationPrice",
            "liquidation",
            "estimated_liquidation_price",
            "est_liquidation_price",
            "liquidation_trigger_price",
        ):
            val = pos.get(key)
            try:
                if isinstance(val, dict):
                    val = val.get("value")
                fv = float(val)
                if fv > 0:
                    return fv
            except Exception:
                continue
        return None

    def get_futures_balance_summary(self) -> dict:
        """Return CFM futures balance summary (best-effort, empty dict on failure)."""
        try:
            return self.api.get_futures_balance_summary() or {}
        except Exception:
            return {}

    def get_current_margin_window(self) -> dict:
        """Return current margin window info for CFM (best-effort, empty dict on failure)."""
        try:
            return self.api.get_current_margin_window() or {}
        except Exception:
            return {}

    def get_open_orders(self, product_id: str | None = None) -> list[dict]:
        """Return open orders (best-effort, empty list on failure)."""
        try:
            return self.api.get_open_orders(pair=product_id) or []
        except Exception:
            return []

    def cancel_open_orders(self, product_id: str | None = None, *, limit: int = 50) -> dict:
        """
        Best-effort cancel of open orders. Returns a small summary for logging/UI.
        """
        cancelled = 0
        attempted = 0
        errs = 0
        try:
            orders = self.get_open_orders(product_id=product_id) or []
            for o in orders[: int(limit)]:
                oid = o.get("order_id") or o.get("orderId")
                if not oid:
                    continue
                attempted += 1
                try:
                    ok = bool(self.api.cancel_order(str(oid)))
                    if ok:
                        cancelled += 1
                    else:
                        errs += 1
                except Exception:
                    errs += 1
        except Exception:
            errs += 1
        return {"attempted": attempted, "cancelled": cancelled, "errors": errs}

    def close_cfm_position(self, product_id: str, *, paper: bool = True) -> dict:
        """
        Close a CFM futures position.  Strategy: limit order first for better
        fill price (maker fees), then fall back to market if limit doesn't fill.

        1. Fetch position side + size
        2. Get best bid/ask from orderbook
        3. Place limit order at best price (bid for sells, ask for buys)
        4. Wait up to 3 seconds for fill
        5. If unfilled: cancel limit, place market order
        """
        if paper:
            return {"ok": True, "paper": True, "product_id": product_id}
        import logging
        _log = logging.getLogger(__name__)
        try:
            # --- Get position details ---
            positions = self.api.get_futures_positions() or []
            pos = None
            for p in positions:
                pid = p.get("product_id") or p.get("productId") or ""
                if str(pid) == str(product_id):
                    pos = p
                    break
            if not pos:
                return {"ok": True, "product_id": product_id, "note": "position_already_closed"}

            size = float(pos.get("number_of_contracts") or pos.get("contracts") or 0)
            side_raw = str(pos.get("side") or "").lower()
            close_side = "BUY" if ("short" in side_raw or "sell" in side_raw) else "SELL"
            if size <= 0:
                return {"ok": False, "product_id": product_id, "error": "zero_size"}

            # --- Try limit order at best price ---
            limit_price = None
            try:
                book = self.api.get_orderbook(product_id) or {}
                bids = book.get("pricebook", {}).get("bids") or book.get("bids") or []
                asks = book.get("pricebook", {}).get("asks") or book.get("asks") or []
                if close_side == "BUY" and asks:
                    limit_price = float(asks[0].get("price") or asks[0][0])
                elif close_side == "SELL" and bids:
                    limit_price = float(bids[0].get("price") or bids[0][0])
            except Exception:
                pass  # Fall through to market

            if limit_price and limit_price > 0:
                res_limit = self.api.place_cfm_order(
                    product_id=product_id,
                    side=close_side,
                    base_size=abs(size),
                    price=limit_price,
                    reduce_only=False,
                )
                limit_ok = bool(res_limit and res_limit.get("success"))
                if limit_ok:
                    limit_oid = (res_limit.get("success_response") or {}).get("order_id") or res_limit.get("order_id")
                    if limit_oid:
                        # Wait up to 3 seconds for fill, checking every 0.5s
                        import time
                        for _wait in range(6):
                            time.sleep(0.5)
                            fill = self.verify_order_fill(limit_oid)
                            if fill and fill.get("filled"):
                                _log.info(f"Limit exit filled at {fill.get('average_filled_price')} (maker)")
                                return {"ok": True, "product_id": product_id, "result": res_limit,
                                        "order_id": limit_oid, "method": "limit", "fill": fill}
                        # Not filled in 3s — cancel and fall through to market
                        _log.info(f"Limit exit {limit_oid} not filled in 3s, cancelling → market")
                        self.api.cancel_order(limit_oid)
                        import time as _t2
                        _t2.sleep(0.3)  # Brief pause after cancel

            # --- Market order fallback ---
            res2 = self.api.place_cfm_order(
                product_id=product_id,
                side=close_side,
                base_size=abs(size),
                price=None,
                reduce_only=False,
            )
            success2 = bool(res2 and res2.get("success", False))
            mkt_oid = (res2.get("success_response") or {}).get("order_id") or res2.get("order_id") if res2 else None
            return {"ok": success2, "product_id": product_id, "result": res2,
                    "order_id": mkt_oid, "method": "market", "fallback": True}
        except Exception as e:
            return {"ok": False, "product_id": product_id, "error": str(e)}

    def get_product_details(self, product_id: str) -> Optional[dict]:
        try:
            return self.api._request("GET", f"/api/v3/brokerage/products/{product_id}")
        except Exception:
            return None

    def get_futures_equity(self) -> float | None:
        summary = self.api.get_futures_balance_summary() or {}
        try:
            equity = summary.get("balance_summary", {}).get("equity", {})
            return float(equity.get("value") or 0)
        except Exception:
            return None

    def get_spot_cash(self, currency: str = "USDC") -> float | None:
        try:
            accounts = self.api.get_accounts() or []
            total = 0.0
            for acc in accounts:
                if acc.get("currency") == currency:
                    bal = acc.get("available_balance", {})
                    val = float(bal.get("value", 0)) if isinstance(bal, dict) else float(bal or 0)
                    total += val
            return total
        except Exception:
            return None

    def get_spot_cash_map(self, currencies: list[str]) -> dict[str, float]:
        wanted = []
        for c in (currencies or []):
            cc = str(c or "").strip().upper()
            if cc and cc not in wanted:
                wanted.append(cc)
        out = {cc: 0.0 for cc in wanted}
        if not wanted:
            return out
        try:
            accounts = self.api.get_accounts() or []
            for acc in accounts:
                cc = str(acc.get("currency") or "").strip().upper()
                if cc not in out:
                    continue
                bal = acc.get("available_balance", {})
                val = float(bal.get("value", 0)) if isinstance(bal, dict) else float(bal or 0)
                out[cc] += max(0.0, val)
        except Exception:
            pass
        return out

    def _resolve_portfolio_uuids(self) -> dict[str, str | None]:
        out = {"default_uuid": None, "futures_uuid": None}
        try:
            portfolios = self.api.get_portfolios() or []
        except Exception:
            return out
        if not portfolios:
            return out

        def _ptype(p: dict) -> str:
            try:
                return str(p.get("type", "") or "").upper()
            except Exception:
                return ""

        def _pname(p: dict) -> str:
            try:
                return str(p.get("name", "") or "").lower()
            except Exception:
                return ""

        for p in portfolios:
            if _ptype(p) == "DEFAULT":
                out["default_uuid"] = p.get("uuid")
                break

        candidates = [p for p in portfolios if _ptype(p) != "DEFAULT"]

        def _score(p: dict) -> int:
            pt = _ptype(p)
            name = _pname(p)
            if pt == "CFM" or "CFM" in pt or "FUT" in pt:
                return 300
            if "futures" in name or "derivative" in name:
                return 280
            if pt == "INTX" or "INTX" in pt:
                return 200
            if pt == "CONSUMER" or "CONSUMER" in pt:
                return 150
            return 100

        if candidates:
            candidates.sort(key=_score, reverse=True)
            out["futures_uuid"] = candidates[0].get("uuid")
        return out

    def estimate_required_margin(self, product_id: str, size: int, direction: str, price: float | None = None) -> dict:
        details = self.get_product_details(product_id) or {}
        fpd = details.get("future_product_details") or {}
        contract_size = float(fpd.get("contract_size") or 0)
        if price is None:
            price = float(details.get("price") or details.get("mid_market_price") or 0)
        intraday = fpd.get("intraday_margin_rate") or {}
        margin_rate = float(intraday.get("long_margin_rate") or intraday.get("short_margin_rate") or 0)
        if direction == "short":
            margin_rate = float(intraday.get("short_margin_rate") or margin_rate)
        notional = price * contract_size * size if price and contract_size else 0
        required = notional * margin_rate if notional and margin_rate else 0
        return {
            "contract_size": contract_size or None,
            "price": price or None,
            "margin_rate": margin_rate or None,
            "required_margin": required or None,
            "notional": notional or None,
        }

    def ensure_futures_margin(
        self,
        product_id: str,
        size: int,
        direction: str,
        buffer_pct: float = 0.10,
        reserve_usd: float = 0.0,
        auto_transfer: bool = False,
        currency: str = "USDC",
        preferred_currencies: list[str] | None = None,
        conversion_cost_bps: float = 0.0,
        spot_reserve_floor_usd: float = 0.0,
        max_transfer_usd: float | None = None,
        transfer_used_usd: float = 0.0,
    ) -> tuple[bool, dict]:
        info = self.estimate_required_margin(product_id, size, direction)
        required = info.get("required_margin") or 0
        buying_power = self.api.get_cfm_buying_power() or 0
        info["futures_buying_power"] = buying_power
        if required <= 0:
            info["ok"] = False
            info["reason"] = "missing_margin_data"
            return False, info
        needed_total = required * (1 + buffer_pct) + reserve_usd
        info["needed_total"] = needed_total
        requested_currency = str(currency or "USDC").strip().upper() or "USDC"
        prefs: list[str] = []
        for c in (preferred_currencies or [requested_currency, "USD", "USDC"]):
            cc = str(c or "").strip().upper()
            if cc and cc not in prefs:
                prefs.append(cc)
        if requested_currency not in prefs:
            prefs.insert(0, requested_currency)
        info["requested_currency"] = requested_currency
        info["preferred_currencies"] = list(prefs)

        if buying_power >= needed_total:
            info["ok"] = True
            info["reason"] = "sufficient_buying_power"
            info["transfer_attempted"] = False
            return True, info
        if not auto_transfer:
            info["ok"] = False
            info["reason"] = "insufficient_buying_power"
            info["transfer_attempted"] = False
            return False, info
        # Attempt transfer from spot to futures portfolio
        shortfall = needed_total - buying_power
        spot_cash_map = self.get_spot_cash_map(prefs)
        info["spot_cash_by_currency"] = spot_cash_map
        info["spot_cash"] = float(spot_cash_map.get(requested_currency, 0.0))
        max_transfer = max_transfer_usd if max_transfer_usd is not None else shortfall
        remaining_cap = max(0.0, max_transfer - transfer_used_usd)
        info["remaining_daily_transfer_cap"] = remaining_cap
        candidates: list[dict[str, Any]] = []
        for cc in prefs:
            cash = float(spot_cash_map.get(cc, 0.0) or 0.0)
            transferable = max(0.0, cash - spot_reserve_floor_usd)
            candidate_amt = min(shortfall, transferable, remaining_cap)
            candidates.append(
                {
                    "currency": cc,
                    "spot_cash": cash,
                    "transferable_after_reserve": transferable,
                    "candidate_amount": max(0.0, candidate_amt),
                }
            )
        info["transfer_candidates"] = candidates
        chosen = next((c for c in candidates if float(c.get("candidate_amount") or 0.0) > 0), None)
        if not chosen:
            info["ok"] = False
            info["reason"] = "insufficient_spot_cash_preferred"
            info["transfer_attempted"] = False
            return False, info
        chosen_currency = str(chosen.get("currency") or requested_currency)
        transfer_amt = float(chosen.get("candidate_amount") or 0.0)
        info["chosen_currency"] = chosen_currency
        info["transferable"] = transfer_amt
        info["estimated_conversion_cost_usd"] = (
            transfer_amt * max(0.0, float(conversion_cost_bps or 0.0)) / 10000.0
            if chosen_currency != "USD"
            else 0.0
        )
        info["conversion_cost_bps"] = float(conversion_cost_bps or 0.0)
        info["transfer_direction"] = "spot_to_futures"

        # CDE auto-sweep check: Coinbase CDE auto-transfers from CBI (spot)
        # to CFM (futures) when you place an order. The move_portfolio_funds
        # endpoint only works for INTX (international) — CDE has just one
        # portfolio (DEFAULT). If spot + derivatives covers the margin,
        # approve the entry and let Coinbase handle the sweep.
        total_spot_available = sum(
            float(c.get("candidate_amount") or 0.0) for c in candidates
        )
        if total_spot_available > 0 and (buying_power + total_spot_available) >= needed_total:
            info["ok"] = True
            info["reason"] = "cde_auto_sweep_available"
            info["transfer_attempted"] = False
            info["cde_spot_available"] = total_spot_available
            info["cde_combined_buying_power"] = buying_power + total_spot_available
            import logging
            logging.getLogger(__name__).info(
                f"CDE auto-sweep: buying_power=${buying_power:.2f} + "
                f"spot=${total_spot_available:.2f} = "
                f"${buying_power + total_spot_available:.2f} >= "
                f"needed ${needed_total:.2f} -- approving entry"
            )
            return True, info

        # CDE only has one portfolio (DEFAULT) so move_portfolio_funds always
        # fails with "Could not identify source and destination portfolios".
        # Skip it entirely; CDE auto-sweeps spot to futures on order placement.
        info["ok"] = False
        info["transfer_attempted"] = False
        info["reason"] = "cde_no_portfolio_transfer"
        return False, info

    def transfer_futures_profit(self, amount: float, currency: str = "USDC") -> dict:
        result: dict[str, Any] = {
            "ok": False,
            "amount": float(amount or 0.0),
            "currency": str(currency or "USDC").strip().upper() or "USDC",
            "direction": "futures_to_spot",
        }
        if float(amount or 0.0) <= 0:
            result["reason"] = "invalid_amount"
            return result
        try:
            # Check if a CFM sweep is already pending; if so, don't spam another
            try:
                pending = self.api.get_cfm_sweeps() or {}
                sweeps_list = pending.get("sweeps") or []
                if sweeps_list:
                    result["ok"] = True
                    result["reason"] = "sweep_already_pending"
                    result["method"] = "cfm_sweep"
                    result["pending_sweeps"] = len(sweeps_list)
                    return result
            except Exception as _sweep_check_err:
                import logging
                logging.getLogger(__name__).debug(
                    f"get_cfm_sweeps() failed: {_sweep_check_err} -- assuming sweep pending, skipping"
                )
                result["ok"] = True
                result["reason"] = "sweep_check_failed_assume_pending"
                return result

            # Primary: Use CFM sweeps endpoint (correct for CDE/US futures)
            res = self.api.schedule_cfm_sweep(float(amount))
            result["transfer_response"] = res
            result["method"] = "cfm_sweep"
            if res is not None:
                result["ok"] = True
                result["reason"] = "cfm_sweep_scheduled"
                return result
            # CFM sweep failed (no pending sweep either). For CDE accounts,
            # move_portfolio_funds does NOT work (only 1 portfolio visible).
            # Don't attempt it; just report the failure cleanly.
            result["reason"] = "cfm_sweep_failed"
            return result
        except Exception as e:
            result["reason"] = "exception"
            result["error"] = str(e)
            return result

    def convert_usd_to_usdc(self, amount: float) -> dict:
        """Convert USD to USDC via Coinbase convert endpoint (1:1, zero fee)."""
        result: dict[str, Any] = {
            "ok": False,
            "amount": float(amount or 0.0),
            "direction": "USD_to_USDC",
        }
        if float(amount or 0.0) < 1.0:
            result["reason"] = "amount_too_small"
            return result
        # Coinbase deprecated from_currency/to_currency fields (Feb 2026).
        # Convert API now requires account UUIDs which adds complexity.
        # USD sitting in spot is harmless -- skip convert to avoid API spam.
        result["reason"] = "convert_disabled_api_change"
        return result

    def get_spread_pct(self, product_id: str) -> float | None:
        book = self.api.get_orderbook(product_id) or {}
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        if not bids or not asks:
            return None
        try:
            bid = float(bids[0].get("price"))
            ask = float(asks[0].get("price"))
            if bid <= 0 or ask <= 0:
                return None
            mid = (bid + ask) / 2
            return (ask - bid) / mid
        except Exception:
            return None
