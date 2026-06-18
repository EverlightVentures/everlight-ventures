#!/usr/bin/env python3
"""
Coinbase API Wrapper
Handles authentication and API calls to Coinbase Advanced Trade API
Supports both legacy HMAC and newer JWT (ES256) authentication
"""

import time
import json
import logging
import secrets
import math
from typing import Optional, Dict, List
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    raise

# JWT support for newer API keys
try:
    import jwt
    from cryptography.hazmat.primitives import serialization
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logger = logging.getLogger(__name__)


class CoinbaseAPI:
    """Coinbase Advanced Trade API wrapper with JWT auth support"""

    BASE_URL = "https://api.coinbase.com"
    CB_VERSION = "2024-06-10"

    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True, use_perpetuals: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.use_perpetuals = use_perpetuals
        self.intx_available = True
        self._intx_warned = False

        # Detect if using new Cloud API keys (JWT auth)
        self.use_jwt = "-----BEGIN" in api_secret or api_key.startswith("organizations/")

        if self.use_jwt and not JWT_AVAILABLE:
            raise ImportError("JWT auth requires: pip install pyjwt cryptography")

        if self.use_jwt:
            logger.info("Using JWT (ES256) authentication")
            # Parse the EC private key
            try:
                self.private_key = serialization.load_pem_private_key(
                    api_secret.encode(),
                    password=None
                )
            except Exception as e:
                logger.error(f"Failed to load private key: {e}")
                raise

        if sandbox:
            logger.info("Running in SANDBOX mode - no real trades")

    def _intx_allowed(self, path: str) -> bool:
        if "/intx/" in path and not self.use_perpetuals:
            logger.debug(f"Skipping INTX endpoint (perps disabled): {path}")
            return False
        return True

    def _generate_jwt(self, method: str, path: str) -> str:
        """Generate JWT token for Cloud API authentication"""
        uri = f"{method} {self.BASE_URL.replace('https://', '')}{path}"

        payload = {
            "sub": self.api_key,
            "iss": "cdp",
            "nbf": int(time.time()),
            "exp": int(time.time()) + 120,  # 2 minute expiry
            "uri": uri,
        }

        headers = {
            "kid": self.api_key,
            "nonce": secrets.token_hex(16),
        }

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm="ES256",
            headers=headers,
        )

        return token

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> Optional[dict]:
        """Make authenticated API request"""
        # Build path with query params for the actual request
        path = endpoint
        if params:
            path += "?" + urlencode(params)
        request_params = None

        body = json.dumps(data) if data else ""

        if self.use_jwt:
            # JWT authentication - uri should NOT include query params
            token = self._generate_jwt(method, endpoint)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "CB-VERSION": self.CB_VERSION
            }
        else:
            # Legacy HMAC authentication
            import hmac
            import hashlib
            timestamp = str(int(time.time()))
            message = timestamp + method + path + body
            signature = hmac.new(
                self.api_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            headers = {
                "CB-ACCESS-KEY": self.api_key,
                "CB-ACCESS-SIGN": signature,
                "CB-ACCESS-TIMESTAMP": timestamp,
                "Content-Type": "application/json",
                "CB-VERSION": self.CB_VERSION
            }

        if not self._intx_allowed(path):
            return None

        url = self.BASE_URL + path

        try:
            # Basic retry/backoff for 429 and 503/500
            for attempt in range(3):
                if method == "GET":
                    response = requests.get(url, headers=headers, params=request_params, timeout=15)
                elif method == "POST":
                    response = requests.post(url, headers=headers, data=body, timeout=15)
                elif method == "DELETE":
                    response = requests.delete(url, headers=headers, timeout=15)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if response.status_code in (200, 201, 202):
                    return response.json()

                # Backoff on rate limits / transient errors
                if response.status_code in (429, 500, 503):
                    wait = 1.5 * (attempt + 1)
                    logger.warning(f"Transient API error {response.status_code} on {path} - retrying in {wait:.1f}s")
                    time.sleep(wait)
                    continue

                # Handle different status codes appropriately
                if response.status_code == 404:
                    # Endpoint not found - likely feature not enabled
                    if "/intx/" in path or "/cfm/" in path:
                        self.intx_available = False
                        if not self._intx_warned:
                            logger.warning("INTX endpoints returned 404. Perpetuals may not be enabled for this API key/account.")
                            self._intx_warned = True
                        logger.warning(
                            f"Futures endpoint not accessible (404): {path}\n"
                            "This usually means:\n"
                            "  1. You haven't completed futures onboarding in Coinbase Advanced\n"
                            "  2. Your API key was created BEFORE you onboarded for futures\n"
                            "Solution: Complete onboarding and create a NEW API key.\n"
                            "Run api.diagnose_futures_access() for detailed steps."
                        )
                    else:
                        logger.warning(f"Endpoint not found (404): {path}")
                    return None
                elif response.status_code == 401:
                    logger.error(f"Authentication failed (401) on {path} - check API keys")
                    return None
                elif response.status_code == 403:
                    logger.error(f"Access forbidden (403) - check API permissions")
                    return None
                elif response.status_code == 429:
                    logger.warning(f"Rate limited (429) - slowing down")
                    return None
                elif response.status_code == 409:
                    # 409 Conflict is expected (e.g. pending sweep already exists)
                    logger.debug(f"API 409 on {path}: already in progress")
                    return None
                else:
                    # Coinbase errors come back as {"errors":[{"id":"...","message":"..."}]}
                    try:
                        err_json = response.json()
                        if isinstance(err_json, dict) and "errors" in err_json:
                            messages = ", ".join(
                                f"{e.get('id','UNKNOWN')}: {e.get('message','')}" .strip()
                                for e in err_json.get("errors", [])
                            )
                            logger.error(f"API Error {response.status_code}: {messages}")
                            return None
                    except Exception:
                        pass
                    logger.error(f"API Error {response.status_code}: {response.text}")
                    return None

            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    # ============ Market Data (Public) ============

    def get_current_price(self, pair: str) -> Optional[float]:
        """Get current price for a trading pair (public endpoint)"""
        url = f"https://api.coinbase.com/v2/prices/{pair}/spot"
        headers = {"CB-VERSION": self.CB_VERSION}
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return float(data["data"]["amount"])
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Failed to get price: {e}")
            time.sleep(0.5 * (attempt + 1))
        return None

    def get_candles_public(self, pair: str, granularity: str = "ONE_DAY", limit: int = 300) -> Optional[List]:
        """
        Get historical candles using public endpoint
        Granularity options: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, THIRTY_MINUTE,
                           ONE_HOUR, TWO_HOUR, SIX_HOUR, ONE_DAY
        Max 300 candles per request - will batch if needed
        """
        try:
            # Map granularity to seconds for time calculation
            granularity_seconds = {
                "ONE_MINUTE": 60,
                "FIVE_MINUTE": 300,
                "FIFTEEN_MINUTE": 900,
                "THIRTY_MINUTE": 1800,
                "ONE_HOUR": 3600,
                "TWO_HOUR": 7200,
                "SIX_HOUR": 21600,
                "ONE_DAY": 86400
            }

            seconds = granularity_seconds.get(granularity, 86400)
            all_candles = []

            # Batch requests (max 300 per request)
            batch_size = 300
            remaining = min(limit, 365)  # Cap at 365 for yearly data
            end_time = int(time.time())

            while remaining > 0 and len(all_candles) < limit:
                batch_limit = min(remaining, batch_size)
                start_time = end_time - (seconds * batch_limit)

                url = f"https://api.exchange.coinbase.com/products/{pair}/candles"
                params = {
                    "granularity": seconds,
                    "start": start_time,
                    "end": end_time
                }

                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    candles = response.json()
                    if not candles:
                        break

                    # Convert to consistent format
                    batch_formatted = [
                        {
                            "start": str(c[0]),
                            "low": str(c[1]),
                            "high": str(c[2]),
                            "open": str(c[3]),
                            "close": str(c[4]),
                            "volume": str(c[5])
                        }
                        for c in candles
                    ]
                    all_candles.extend(batch_formatted)

                    # Move end_time for next batch
                    end_time = start_time
                    remaining -= len(candles)

                    # Small delay between batches
                    if remaining > 0:
                        time.sleep(0.1)
                else:
                    logger.error(f"Candles API Error: {response.status_code} - {response.text}")
                    break

            return all_candles if all_candles else None

        except Exception as e:
            logger.error(f"Failed to get candles: {e}")
        return None

    def get_orderbook(self, pair: str, level: int = 2) -> Optional[dict]:
        """Get orderbook for a pair"""
        endpoint = f"/api/v3/brokerage/product_book"
        params = {"product_id": pair, "limit": 50}
        return self._request("GET", endpoint, params=params)

    def get_candles(self, pair: str, granularity: int = 300, limit: int = 100) -> Optional[List]:
        """
        Get historical candles (authenticated endpoint)
        Granularity: 60, 300, 900, 3600, 21600, 86400 (seconds)
        Falls back to public endpoint if auth fails
        """
        # Map seconds to string granularity
        granularity_map = {
            60: "ONE_MINUTE",
            300: "FIVE_MINUTE",
            900: "FIFTEEN_MINUTE",
            1800: "THIRTY_MINUTE",
            3600: "ONE_HOUR",
            7200: "TWO_HOUR",
            21600: "SIX_HOUR",
            86400: "ONE_DAY"
        }

        gran_str = granularity_map.get(granularity, "ONE_DAY")

        # Try authenticated endpoint first
        endpoint = f"/api/v3/brokerage/products/{pair}/candles"
        params = {"granularity": gran_str, "limit": limit}
        result = self._request("GET", endpoint, params=params)

        if result and "candles" in result:
            return result["candles"]

        # Fall back to public endpoint
        logger.info("Falling back to public candles endpoint")
        return self.get_candles_public(pair, gran_str, limit)

    def get_ticker(self, pair: str) -> Optional[dict]:
        """Get 24h ticker stats"""
        endpoint = f"/api/v3/brokerage/products/{pair}/ticker"
        return self._request("GET", endpoint)

    # ============ Account ============

    def get_accounts(self) -> Optional[List]:
        """Get all accounts/balances"""
        endpoint = "/api/v3/brokerage/accounts"
        result = self._request("GET", endpoint)
        if result and "accounts" in result:
            if result.get("pagination", {}).get("next_uri"):
                return self._paginate(result, "accounts")
            return result["accounts"]
        return None

    def get_products(self) -> Optional[List]:
        """Get all tradable products"""
        # Try authenticated endpoint first
        endpoint = "/api/v3/brokerage/products"
        result = self._request("GET", endpoint, params={"limit": 1000})
        if result and "products" in result:
            if result.get("pagination", {}).get("next_uri"):
                return self._paginate(result, "products")
            return result["products"]

        # Fallback to public endpoint (no auth required)
        try:
            import requests
            logger.info("Trying public products endpoint (no auth)")
            resp = requests.get(
                f"{self.BASE_URL}/api/v3/brokerage/market/products",
                params={"limit": 1000},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                if "products" in data:
                    logger.info(f"Got {len(data['products'])} products from public endpoint")
                    return data["products"]
        except Exception as e:
            logger.warning(f"Public products endpoint failed: {e}")

        return None

    def get_product_details_public(self, product_id: str) -> Optional[dict]:
        """Fetch product details from the public market/products endpoint."""
        try:
            import requests
            resp = requests.get(
                f"{self.BASE_URL}/api/v3/brokerage/market/products",
                params={"product_ids": [product_id]},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("products", [])
                return products[0] if products else None
        except Exception as e:
            logger.warning(f"Public product lookup failed for {product_id}: {e}")
        return None

    def get_product_details(self, product_id: str) -> Optional[dict]:
        """Fetch authenticated product details (includes futures fields)."""
        try:
            return self._request("GET", f"/api/v3/brokerage/products/{product_id}")
        except Exception:
            return None

    def _decimal_places_from_increment(self, increment: str) -> int:
        try:
            inc = str(increment)
            if "." in inc:
                return len(inc.split(".")[1].rstrip("0"))
        except Exception:
            pass
        return 0

    def _round_base_size(self, size: float, product_id: str) -> Optional[float]:
        """Round base size to the product's base_increment and respect min/max."""
        details = self.get_product_details_public(product_id)
        if not details:
            return size

        try:
            base_inc = float(details.get("base_increment", "1") or "1")
        except Exception:
            base_inc = 1.0

        try:
            base_min = float(details.get("base_min_size", "0") or "0")
        except Exception:
            base_min = 0.0

        try:
            base_max = float(details.get("base_max_size", "0") or "0")
        except Exception:
            base_max = 0.0

        if base_inc > 0:
            rounded = math.floor(size / base_inc) * base_inc
            rounded = round(rounded, self._decimal_places_from_increment(str(details.get("base_increment", "1"))))
        else:
            rounded = size

        if base_max and rounded > base_max:
            rounded = base_max

        if base_min and rounded < base_min:
            return None

        return rounded

    def _paginate(self, first_response: dict, list_key: str) -> List[dict]:
        """
        Follow Coinbase pagination via next_uri.
        Expects the initial response and list_key (e.g., "products", "accounts").
        """
        items: List[dict] = []
        if not first_response:
            return items

        items.extend(first_response.get(list_key, []))
        pagination = first_response.get("pagination") or {}
        next_uri = pagination.get("next_uri")

        while next_uri:
            page = self._request("GET", next_uri)
            if not page:
                break
            items.extend(page.get(list_key, []))
            pagination = page.get("pagination") or {}
            next_uri = pagination.get("next_uri")

        return items

    def get_cfm_futures_products(self) -> Optional[List]:
        """Get CFM futures products from public endpoint (no auth required)"""
        try:
            import requests
            resp = requests.get(
                f"{self.BASE_URL}/api/v3/brokerage/market/products",
                params={"product_type": "FUTURE"},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                if "products" in data:
                    logger.info(f"Got {len(data['products'])} CFM futures from public endpoint")
                    return data["products"]
        except Exception as e:
            logger.warning(f"CFM futures endpoint failed: {e}")
        return None

    def get_balance(self, currency: str) -> Optional[float]:
        """Get balance for a specific currency"""
        accounts = self.get_accounts()
        if accounts:
            for acc in accounts:
                if acc.get("currency") == currency:
                    return float(acc.get("available_balance", {}).get("value", 0))
        return None

    # ============ Perpetuals / Margin ============

    def get_perpetuals_portfolio(self) -> Optional[dict]:
        """Get perpetuals portfolio summary"""
        endpoint = "/api/v3/brokerage/intx/portfolio"
        return self._request("GET", endpoint)

    def get_perpetuals_positions(self) -> Optional[List]:
        """Get all open perpetual positions"""
        endpoint = "/api/v3/brokerage/intx/positions"
        result = self._request("GET", endpoint)
        if result and "positions" in result:
            return result["positions"]
        return None

    def get_perpetuals_position(self, pair: str) -> Optional[dict]:
        """Get specific perpetual position"""
        endpoint = f"/api/v3/brokerage/intx/positions/{pair}"
        return self._request("GET", endpoint)

    def place_perpetual_order(self, pair: str, side: str, size: float,
                              leverage: int = 4, price: float = None,
                              stop_loss: float = None, take_profit: float = None) -> Optional[dict]:
        """
        Place a perpetual futures order with leverage

        Args:
            pair: Trading pair (e.g., "BTC-PERP-INTX")
            side: "BUY" or "SELL"
            size: Position size in base currency
            leverage: Leverage multiplier (1-10x typically)
            price: Limit price (None for market)
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        endpoint = "/api/v3/brokerage/intx/orders"

        # Convert spot pair to perpetual format if needed
        if not pair.endswith("-PERP-INTX"):
            perp_pair = pair.replace("-USD", "-PERP-INTX")
        else:
            perp_pair = pair

        data = {
            "client_order_id": f"perp_{side.lower()}_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            "product_id": perp_pair,
            "side": side.upper(),
            "size": str(size),
            "leverage": str(leverage)
        }

        if price:
            data["order_type"] = "LIMIT"
            # Round price to correct precision to avoid INVALID_PRICE_PRECISION error
            price = self._round_price(price, pair)
            data["limit_price"] = str(price)
        else:
            data["order_type"] = "MARKET"

        # Add bracket orders for SL/TP if provided (round prices)
        if stop_loss or take_profit:
            data["stop_trigger_price"] = str(self._round_price(stop_loss, pair)) if stop_loss else None
            data["take_profit_price"] = str(self._round_price(take_profit, pair)) if take_profit else None

        logger.info(f"Placing PERP {side} order: {perp_pair} size={size} leverage={leverage}x")
        return self._request("POST", endpoint, data=data)

    def close_perpetual_position(self, pair: str) -> Optional[dict]:
        """Close an open perpetual position"""
        # Get current position
        position = self.get_perpetuals_position(pair)
        if not position:
            return None

        size = abs(float(position.get("size", 0)))
        side = "SELL" if float(position.get("size", 0)) > 0 else "BUY"

        return self.place_perpetual_order(pair, side, size)

    def set_perpetual_leverage(self, pair: str, leverage: int) -> Optional[dict]:
        """Set leverage for a perpetual pair"""
        endpoint = "/api/v3/brokerage/intx/leverage"

        if not pair.endswith("-PERP-INTX"):
            perp_pair = pair.replace("-USD", "-PERP-INTX")
        else:
            perp_pair = pair

        data = {
            "product_id": perp_pair,
            "leverage": str(leverage)
        }
        return self._request("POST", endpoint, data=data)

    def add_margin_to_position(self, pair: str, amount: float) -> Optional[dict]:
        """Add margin to an existing position to prevent liquidation"""
        endpoint = "/api/v3/brokerage/intx/margin"

        if not pair.endswith("-PERP-INTX"):
            perp_pair = pair.replace("-USD", "-PERP-INTX")
        else:
            perp_pair = pair

        data = {
            "product_id": perp_pair,
            "amount": str(amount)
        }
        logger.info(f"Adding ${amount} margin to {perp_pair}")
        return self._request("POST", endpoint, data=data)

    # ============ CFM (US Regulated Futures) ============

    def get_futures_balance_summary(self) -> Optional[dict]:
        """
        Get CFM (US regulated futures) balance summary

        CFM = Coinbase Financial Markets (US regulated)
        Different from INTX (international perpetuals)
        """
        endpoint = "/api/v3/brokerage/cfm/balance_summary"
        return self._request("GET", endpoint)

    def get_cfm_buying_power(self) -> Optional[float]:
        """Get CFM futures buying power in USD."""
        summary = self.get_futures_balance_summary()
        try:
            if summary and "balance_summary" in summary:
                bp = summary["balance_summary"].get("futures_buying_power", {})
                return float(bp.get("value", 0) or 0)
        except Exception:
            pass
        return None

    def get_futures_positions(self) -> Optional[List]:
        """Get CFM futures positions (US regulated)"""
        endpoint = "/api/v3/brokerage/cfm/positions"
        result = self._request("GET", endpoint)
        if result and "positions" in result:
            return result["positions"]
        return None

    def get_intraday_margin_setting(self) -> Optional[dict]:
        """Get current intraday margin setting for CFM futures"""
        endpoint = "/api/v3/brokerage/cfm/intraday/margin_setting"
        return self._request("GET", endpoint)

    def set_intraday_margin_setting(self, setting: str) -> Optional[dict]:
        """
        Set intraday margin setting for CFM

        Args:
            setting: "INTRADAY" or "STANDARD"
        """
        endpoint = "/api/v3/brokerage/cfm/intraday/margin_setting"
        data = {"setting": setting}
        return self._request("POST", endpoint, data=data)

    def get_current_margin_window(self) -> Optional[dict]:
        """Get current margin window info for CFM"""
        endpoint = "/api/v3/brokerage/cfm/intraday/current_margin_window"
        return self._request("GET", endpoint)

    # ============ CFM Sweeps (CDE fund transfers) ============

    def get_cfm_sweeps(self) -> Optional[dict]:
        """Get pending CFM sweep status (futures → spot)."""
        endpoint = "/api/v3/brokerage/cfm/sweeps"
        return self._request("GET", endpoint)

    def schedule_cfm_sweep(self, usd_amount: float) -> Optional[dict]:
        """
        Schedule a CFM sweep to move funds FROM futures TO spot.

        For CDE (US regulated futures), this is the correct way to transfer
        derivatives balance back to spot. The move_portfolio_funds endpoint
        does NOT work for CDE (only one portfolio exists).

        Note: Transfers INTO futures happen automatically when you place
        an order — Coinbase auto-sweeps from CBI (spot) to CFM (futures).

        Args:
            usd_amount: USD amount to sweep from futures to spot
        """
        endpoint = "/api/v3/brokerage/cfm/sweeps/schedule"
        data = {"usd_amount": str(usd_amount)}
        logger.info(f"Scheduling CFM sweep: ${usd_amount:.2f} futures → spot")
        return self._request("POST", endpoint, data=data)

    # ============ Portfolio Management ============

    def get_portfolios(self) -> Optional[List]:
        """Get all portfolios including perpetuals/futures portfolio"""
        endpoint = "/api/v3/brokerage/portfolios"
        result = self._request("GET", endpoint)
        if result and "portfolios" in result:
            return result["portfolios"]
        return None

    def move_portfolio_funds(self, amount: float, currency: str = "USDC",
                              from_portfolio: str = None, to_portfolio: str = None) -> Optional[dict]:
        """
        Transfer funds between portfolios (e.g., from Default to Futures)

        Args:
            amount: Amount to transfer
            currency: Currency to transfer (USDC, BTC, ETH)
            from_portfolio: Source portfolio UUID (None = auto-detect default)
            to_portfolio: Destination portfolio UUID (None = auto-detect futures)

        Note: For futures, collateral must be in the futures portfolio.
        """
        endpoint = "/api/v3/brokerage/portfolios/move_funds"

        # Auto-detect portfolios if not specified
        if not from_portfolio or not to_portfolio:
            portfolios = self.get_portfolios()
            if portfolios:
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

                # Source: default portfolio (spot)
                if not from_portfolio:
                    for p in portfolios:
                        if _ptype(p) == "DEFAULT":
                            from_portfolio = p.get("uuid")
                            break

                # Target: prefer CFM (US futures) when present, else INTX, else other non-default.
                if not to_portfolio:
                    targets = []
                    for p in portfolios:
                        pt = _ptype(p)
                        if pt == "DEFAULT":
                            continue
                        targets.append(p)

                    def _score(p: dict) -> int:
                        pt = _ptype(p)
                        name = _pname(p)
                        # Higher score => higher priority
                        if pt == "CFM" or "CFM" in pt or "FUT" in pt:
                            return 300
                        if "futures" in name or "derivative" in name:
                            return 280
                        if pt == "INTX" or "INTX" in pt:
                            return 200
                        if pt == "CONSUMER" or "CONSUMER" in pt:
                            return 150
                        return 100

                    if targets:
                        targets.sort(key=_score, reverse=True)
                        to_portfolio = targets[0].get("uuid")

        if not from_portfolio or not to_portfolio:
            logger.debug("Could not identify source and destination portfolios (expected on CDE)")
            return None

        data = {
            "funds": {
                "value": str(amount),
                "currency": currency
            },
            "source_portfolio_uuid": from_portfolio,
            "target_portfolio_uuid": to_portfolio
        }

        logger.info(f"Transferring {amount} {currency} to futures portfolio")
        return self._request("POST", endpoint, data=data)

    # ============ Futures Diagnostics ============

    def diagnose_futures_access(self) -> dict:
        """
        Comprehensive check for futures/perpetuals API access

        Tests CFM (US) and INTX (international) endpoints.
        Returns detailed diagnosis with onboarding instructions if needed.
        """
        results = {
            "cfm_accessible": False,
            "intx_accessible": False,
            "portfolios": [],
            "cfm_balance": None,
            "intx_portfolio": None,
            "error_details": [],
            "onboarding_required": False,
            "recommendation": ""
        }

        # Test 1: Get portfolios
        try:
            portfolios = self.get_portfolios()
            if portfolios:
                results["portfolios"] = [
                    {"name": p.get("name"), "type": p.get("type"), "uuid": p.get("uuid", "")[:8]}
                    for p in portfolios
                ]
        except Exception as e:
            results["error_details"].append(f"Portfolios test failed: {e}")

        # Test 2: CFM (US Futures) endpoints
        try:
            cfm_balance = self.get_futures_balance_summary()
            if cfm_balance:
                results["cfm_accessible"] = True
                results["cfm_balance"] = cfm_balance
        except Exception as e:
            results["error_details"].append(f"CFM test failed: {e}")

        # Test 3: INTX (International Perpetuals) endpoints
        try:
            # Temporarily enable perpetuals check
            old_perps = self.use_perpetuals
            self.use_perpetuals = True

            intx_portfolio = self._request("GET", "/api/v3/brokerage/intx/portfolio")
            if intx_portfolio:
                results["intx_accessible"] = True
                results["intx_portfolio"] = intx_portfolio

            self.use_perpetuals = old_perps
        except Exception as e:
            results["error_details"].append(f"INTX test failed: {e}")

        # Generate recommendation
        if results["cfm_accessible"]:
            results["recommendation"] = (
                "CFM (US Futures) access confirmed. You can trade US-regulated futures.\n"
                "Use get_futures_positions() and place orders with CFM product IDs."
            )
        elif results["intx_accessible"]:
            results["recommendation"] = (
                "INTX (International Perpetuals) access confirmed.\n"
                "Use get_perpetuals_positions() and place_perpetual_order()."
            )
        else:
            results["onboarding_required"] = True
            results["recommendation"] = (
                "FUTURES ACCESS NOT DETECTED\n"
                "═══════════════════════════\n"
                "\n"
                "Required steps:\n"
                "1. Open Coinbase Advanced Trade (app or web)\n"
                "2. Navigate to a futures market (e.g., BTC-PERP or BIT futures)\n"
                "3. Complete the futures onboarding flow\n"
                "4. Transfer funds to your Futures account\n"
                "\n"
                "CRITICAL: After onboarding, you MUST:\n"
                "5. Create a NEW API key in Settings > API\n"
                "   (Old API keys don't inherit futures permissions)\n"
                "6. Update config.json with the new API key\n"
                "7. Run this diagnostic again to verify\n"
                "\n"
                "Note: CFM = US regulated futures, INTX = International perpetuals"
            )

        return results

    # ============ Spot Orders ============

    def place_buy_order(self, pair: str, amount: float, price: float = None, post_only: bool = False) -> Optional[dict]:
        """
        Place a buy order
        If price is None, places market order
        """
        endpoint = "/api/v3/brokerage/orders"

        # Round price to correct precision to avoid INVALID_PRICE_PRECISION error
        if price is not None:
            price = self._round_price(price, pair)

        order_config = {
            "quote_size": str(amount)
        } if price is None else {
            "base_size": str(amount),
            "limit_price": str(price)
        }
        if price is not None and post_only:
            order_config["post_only"] = True

        data = {
            "client_order_id": f"buy_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            "product_id": pair,
            "side": "BUY",
            "order_configuration": {
                "market_market_ioc": order_config
            } if price is None else {
                "limit_limit_gtc": order_config
            }
        }

        logger.info(f"Placing BUY order: {pair} amount={amount} price={price or 'MARKET'}")
        return self._request("POST", endpoint, data=data)

    def place_sell_order(self, pair: str, amount: float, price: float = None, post_only: bool = False) -> Optional[dict]:
        """
        Place a sell order
        If price is None, places market order
        """
        endpoint = "/api/v3/brokerage/orders"

        # Round price to correct precision to avoid INVALID_PRICE_PRECISION error
        if price is not None:
            price = self._round_price(price, pair)

        order_config = {
            "base_size": str(amount)
        }

        if price:
            order_config["limit_price"] = str(price)
            if post_only:
                order_config["post_only"] = True

        data = {
            "client_order_id": f"sell_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            "product_id": pair,
            "side": "SELL",
            "order_configuration": {
                "market_market_ioc": order_config
            } if price is None else {
                "limit_limit_gtc": order_config
            }
        }

        logger.info(f"Placing SELL order: {pair} amount={amount} price={price or 'MARKET'}")
        return self._request("POST", endpoint, data=data)

    def place_cfm_order(
        self,
        product_id: str,
        side: str,
        base_size: float,
        price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        reduce_only: bool = False,
        client_order_id: str = "",
    ) -> Optional[dict]:
        """
        Place a CFM (US futures) order using base_size.
        """
        endpoint = "/api/v3/brokerage/orders"

        rounded_size = self._round_base_size(base_size, product_id)
        if rounded_size is None or rounded_size <= 0:
            logger.warning(f"CFM order size too small for {product_id}: requested={base_size}")
            return None

        # Coinbase CFM orders accept a reduce_only flag inside the order_configuration object.
        # Only include reduce_only when True — some venues reject it outright.
        order_config = {"base_size": str(rounded_size)}
        if reduce_only:
            order_config["reduce_only"] = True
        if price:
            # Round price to correct precision to avoid INVALID_PRICE_PRECISION error
            price = self._round_price(price, product_id)
            order_config["limit_price"] = str(price)

        data = {
            "client_order_id": client_order_id or f"cfm_{side.lower()}_{int(time.time()*1000)}_{secrets.token_hex(4)}",
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": {
                "market_market_ioc": order_config
            } if price is None else {
                "limit_limit_gtc": order_config
            }
        }

        # Attach TP/SL bracket if provided
        if take_profit is not None or stop_loss is not None:
            attached = {}
            if take_profit is not None:
                attached["limit_price"] = str(self._round_price(take_profit, product_id))
            if stop_loss is not None:
                attached["stop_trigger_price"] = str(self._round_price(stop_loss, product_id))
            if attached:
                data["attached_order_configuration"] = {
                    "trigger_bracket_gtc": attached
                }

        logger.info(f"Placing CFM order: {product_id} side={side} size={rounded_size} price={price or 'MARKET'}")
        return self._request("POST", endpoint, data=data)

    def cancel_open_orders(self, product_id: str) -> int:
        """Cancel all currently OPEN orders for a given product_id (spot or futures). Returns count attempted."""
        if not product_id:
            return 0
        try:
            orders = self.get_open_orders(product_id) or []
        except Exception:
            orders = []
        count = 0
        for o in orders:
            oid = o.get("order_id") or o.get("orderId") or o.get("id")
            if not oid:
                continue
            try:
                if self.cancel_order(str(oid)):
                    count += 1
            except Exception:
                continue
        return count

    def close_cfm_position(self, product_id: str) -> Optional[dict]:
        """
        Close a CFM futures position using a reduce-only market order.
        This should not flip position direction.
        """
        if not product_id:
            return None
        positions = self.get_futures_positions() or []
        pos = None
        for p in positions:
            pid = p.get("product_id") or p.get("productId") or p.get("symbol")
            if str(pid) == str(product_id):
                pos = p
                break
        if not pos:
            return None

        # Different payloads can express size/side differently; handle both.
        size = None
        try:
            size = float(
                pos.get("number_of_contracts")
                or pos.get("contracts")
                or pos.get("size")
                or pos.get("base_size")
                or pos.get("position_size")
                or 0
            )
        except Exception:
            size = 0.0
        side_raw = str(pos.get("side") or "").lower()

        # If "size" is signed, infer side from sign.
        if size and not side_raw:
            side_raw = "sell" if size < 0 else "buy"
        close_side = "BUY" if ("sell" in side_raw or "short" in side_raw or (size and size < 0)) else "SELL"
        close_size = abs(size)
        if close_size <= 0:
            return None

        # Safety: place close order first, then cancel remaining orders only
        # after the position is confirmed closed. Canceling stops first can create an unprotected gap.
        # Try reduce_only first, fall back to plain order if venue rejects it.
        resp = self.place_cfm_order(
            product_id=product_id,
            side=close_side,
            base_size=close_size,
            price=None,
            reduce_only=True,
        )
        # Coinbase CDE rejects reduce_only — fall back to plain close order
        if resp and resp.get("success") is False:
            logger.warning(f"reduce_only close rejected: {resp.get('error_response') or resp.get('failure_response')}, retrying without reduce_only")
            resp = self.place_cfm_order(
                product_id=product_id,
                side=close_side,
                base_size=close_size,
                price=None,
                reduce_only=False,
            )

        # Best-effort cleanup of leftover orders (TP/SL/etc.) once the position is gone.
        try:
            closed = False
            for _ in range(5):
                time.sleep(0.3)
                cur = None
                for p in (self.get_futures_positions() or []):
                    pid = p.get("product_id") or p.get("productId") or p.get("symbol")
                    if str(pid) == str(product_id):
                        cur = p
                        break
                if not cur:
                    closed = True
                    break
                try:
                    cur_size = float(
                        cur.get("number_of_contracts")
                        or cur.get("contracts")
                        or cur.get("size")
                        or cur.get("base_size")
                        or cur.get("position_size")
                        or 0
                    )
                except Exception:
                    cur_size = 0.0
                if abs(cur_size) <= 0:
                    closed = True
                    break
            if closed:
                self.cancel_open_orders(product_id)
        except Exception:
            pass

        return resp

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        endpoint = "/api/v3/brokerage/orders/batch_cancel"
        data = {"order_ids": [order_id]}
        result = self._request("POST", endpoint, data=data)
        return result is not None

    def get_open_orders(self, pair: str = None) -> Optional[List]:
        """Get open orders"""
        endpoint = "/api/v3/brokerage/orders/historical/batch"
        params = {"order_status": "OPEN"}
        if pair:
            params["product_id"] = pair
        result = self._request("GET", endpoint, params=params)
        if result and "orders" in result:
            return result["orders"]
        return None

    def get_historical_orders(self, order_status: str = "FILLED", pair: str = None, limit: int = 100) -> Optional[List]:
        """Get historical orders by status (FILLED, DONE, CANCELED, etc.)."""
        endpoint = "/api/v3/brokerage/orders/historical/batch"
        params = {"order_status": order_status, "limit": limit}
        if pair:
            params["product_id"] = pair
        result = self._request("GET", endpoint, params=params)
        if result and "orders" in result:
            return result["orders"]
        return None

    def get_order(self, order_id: str) -> Optional[dict]:
        """Get order details"""
        endpoint = f"/api/v3/brokerage/orders/historical/{order_id}"
        return self._request("GET", endpoint)

    # ============ Helpers ============

    def get_min_order_size(self, pair: str) -> Optional[float]:
        """Get minimum order size for a pair"""
        endpoint = f"/api/v3/brokerage/products/{pair}"
        result = self._request("GET", endpoint)
        if result:
            return float(result.get("base_min_size", 0))
        return None

    def get_price_precision(self, pair: str) -> int:
        """
        Get the price precision (decimal places) for a pair.
        Uses price_increment (actual tick size) over quote_increment (min dollar amount).
        """
        endpoint = f"/api/v3/brokerage/products/{pair}"
        result = self._request("GET", endpoint)
        if result:
            # Prefer price_increment (actual tick size, e.g. "0.00001" = 5 decimals)
            # Fall back to quote_increment (min quote amount, e.g. "0.01" = 2 decimals)
            increment = result.get("price_increment") or result.get("quote_increment") or "0.01"
            if "." in str(increment):
                return len(str(increment).split(".")[1].rstrip("0")) or 2
        # Default to 5 for sub-dollar assets like XLM
        return 5

    _price_precision_cache: dict = {}

    def _round_price(self, price: float, pair: str) -> float:
        """Round price to the appropriate precision for the pair (cached)."""
        if pair not in self._price_precision_cache:
            self._price_precision_cache[pair] = self.get_price_precision(pair)
        return round(price, self._price_precision_cache[pair])


# Quick test
if __name__ == "__main__":
    api = CoinbaseAPI("test", "test", sandbox=True)
    price = api.get_current_price("BTC-USD")
    print(f"BTC-USD Price: ${price:,.2f}" if price else "Failed to get price")

    # Test public candles
    candles = api.get_candles_public("BTC-USD", "ONE_DAY", 30)
    if candles:
        print(f"Got {len(candles)} daily candles")
        if candles:
            latest = candles[0]
            print(f"Latest: High=${float(latest['high']):,.0f}, Low=${float(latest['low']):,.0f}")
