"""
Exchange service -- cached, read-only Coinbase API access.

All API calls are best-effort: return empty dict/list on failure, never crash.
Exchange reads can be disabled via settings.XLM_EXCHANGE_READ = False.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singleton API
# ---------------------------------------------------------------------------

_api_instance = None
_CoinbaseAPI = None


def _ensure_api_class():
    """Import CoinbaseAPI once (best-effort)."""
    global _CoinbaseAPI
    if _CoinbaseAPI is not None:
        return
    try:
        import sys
        bot_dir = settings.XLM_DATA_DIR.parent
        vendor = bot_dir / "vendor"
        for p in (str(vendor), str(bot_dir)):
            if p not in sys.path:
                sys.path.insert(0, p)
        from utils.coinbase_api import CoinbaseAPI
        _CoinbaseAPI = CoinbaseAPI
    except Exception:
        _CoinbaseAPI = None


def _get_api():
    """Return a singleton CoinbaseAPI instance, or None."""
    global _api_instance
    if _api_instance is not None:
        return _api_instance

    _ensure_api_class()
    if _CoinbaseAPI is None:
        return None

    config_path: Path = settings.XLM_COINBASE_CONFIG
    if not config_path.exists():
        return None

    try:
        cfg = json.loads(config_path.read_text())
        exch = cfg.get("exchange", {})
        _api_instance = _CoinbaseAPI(
            api_key=exch.get("api_key", ""),
            api_secret=exch.get("api_secret", ""),
            sandbox=exch.get("sandbox", False),
            use_perpetuals=True,
        )
        return _api_instance
    except Exception:
        logger.warning("Failed to initialise CoinbaseAPI", exc_info=True)
        return None


def _exchange_enabled() -> bool:
    return getattr(settings, "XLM_EXCHANGE_READ", True)


# ---------------------------------------------------------------------------
# Public API -- all cached, all safe
# ---------------------------------------------------------------------------

def get_futures_balance() -> dict:
    """Futures balance summary. Cached 15 s."""
    if not _exchange_enabled():
        return {}
    cached = cache.get("exch_futures_bal")
    if cached is not None:
        return cached

    api = _get_api()
    if api is None:
        return {}
    try:
        result = api.get_futures_balance_summary() or {}
    except Exception:
        logger.debug("get_futures_balance failed", exc_info=True)
        result = {}
    cache.set("exch_futures_bal", result, timeout=15)
    return result


def get_cfm_positions() -> list[dict]:
    """Open CFM futures positions. Cached 15 s."""
    if not _exchange_enabled():
        return []
    cached = cache.get("exch_cfm_positions")
    if cached is not None:
        return cached

    api = _get_api()
    if api is None:
        return []
    try:
        result = api.get_futures_positions() or []
    except Exception:
        logger.debug("get_cfm_positions failed", exc_info=True)
        result = []
    cache.set("exch_cfm_positions", result, timeout=15)
    return result


def get_spot_balances() -> dict[str, float]:
    """Spot wallet balances (USD, USDC). Cached 15 s."""
    if not _exchange_enabled():
        return {}
    cached = cache.get("exch_spot_bal")
    if cached is not None:
        return cached

    api = _get_api()
    if api is None:
        return {}
    try:
        accts = api._request("GET", "/api/v3/brokerage/accounts", params={"limit": 50})
        result: dict[str, float] = {}
        for a in (accts.get("accounts") or []):
            cur = str(a.get("available_balance", {}).get("currency", ""))
            val = float(a.get("available_balance", {}).get("value", 0) or 0)
            if cur in ("USD", "USDC") and val > 0:
                result[cur] = val
    except Exception:
        logger.debug("get_spot_balances failed", exc_info=True)
        result = {}
    cache.set("exch_spot_bal", result, timeout=15)
    return result


def get_portfolio_breakdown() -> dict[str, float]:
    """Portfolio breakdown -- single source of truth for totals.

    Returns dict with keys: total, cash, futures, crypto, spot_usdc.
    """
    if not _exchange_enabled():
        return {}
    cached = cache.get("exch_portfolio")
    if cached is not None:
        return cached

    api = _get_api()
    if api is None:
        return {}
    try:
        portfolios = api._request("GET", "/api/v3/brokerage/portfolios")
        plist = portfolios.get("portfolios") or [] if isinstance(portfolios, dict) else []
        uuid = None
        for p in plist:
            if str(p.get("type", "")).upper() == "DEFAULT":
                uuid = p.get("uuid")
                break
        if not uuid and plist:
            uuid = plist[0].get("uuid")
        if not uuid:
            cache.set("exch_portfolio", {}, timeout=15)
            return {}

        detail = api._request("GET", f"/api/v3/brokerage/portfolios/{uuid}")
        bd = (detail or {}).get("breakdown", {})
        pb = bd.get("portfolio_balances", {})
        result: dict[str, float] = {}
        for key, out_key in [
            ("total_balance", "total"),
            ("total_cash_equivalent_balance", "cash"),
            ("total_futures_balance", "futures"),
            ("total_crypto_balance", "crypto"),
        ]:
            val = pb.get(key, {})
            if isinstance(val, dict):
                result[out_key] = float(val.get("value", 0) or 0)
            else:
                result[out_key] = float(val or 0)

        for sp in (bd.get("spot_positions") or []):
            if str(sp.get("asset", "")).upper() == "USDC":
                try:
                    result["spot_usdc"] = float(
                        sp.get("total_balance_fiat", {}).get("value", 0) or 0
                    )
                except Exception:
                    pass
    except Exception:
        logger.debug("get_portfolio_breakdown failed", exc_info=True)
        result = {}
    cache.set("exch_portfolio", result, timeout=15)
    return result


def get_cfm_open_orders(product_id: str | None = None) -> list[dict]:
    """Open orders (optionally scoped to a product). Cached 10 s."""
    if not _exchange_enabled():
        return []
    cache_key = f"exch_orders_{product_id or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    api = _get_api()
    if api is None:
        return []
    try:
        result = api.get_open_orders(pair=product_id) or []
    except Exception:
        logger.debug("get_cfm_open_orders failed", exc_info=True)
        result = []
    cache.set(cache_key, result, timeout=10)
    return result


def get_cfm_product_details(product_id: str) -> dict:
    """CFM product details. Cached 60 s."""
    if not _exchange_enabled():
        return {}
    cache_key = f"exch_prod_{product_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    api = _get_api()
    if api is None:
        return {}
    try:
        result = api._request("GET", f"/api/v3/brokerage/products/{product_id}") or {}
    except Exception:
        logger.debug("get_cfm_product_details failed", exc_info=True)
        result = {}
    cache.set(cache_key, result, timeout=60)
    return result
