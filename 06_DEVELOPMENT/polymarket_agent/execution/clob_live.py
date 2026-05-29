"""Real Polymarket CLOB execution backend via py-clob-client.

This is the PRODUCTION signing + order path. It replaces the hand-rolled
EIP-712 scaffold that was structurally correct only for standard binary
markets. The library is the path Polymarket ships and thousands trade through,
and it solves three live-only bugs the hand-rolled envelope could not:

  1. Neg-risk exchange selection (get_neg_risk -> correct verifyingContract)
  2. Tick-size rounding (get_tick_size -> on-tick maker/taker amounts)
  3. Signature type / proxy-wallet handling

Key custody: the private key is read from the secure key file (chmod 600,
hex-validated, fail-loud) and handed to ClobClient's internal Signer. It is
never logged. Same posture as wallet.py -- the risk is leakage, not which
in-memory object holds it.

NOTE: do not add logging of the key, creds, or signed-order bytes to this
module. API creds (api_key/secret/passphrase) are bearer secrets.
"""
import re
from decimal import Decimal
from pathlib import Path

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import (
        OrderArgs, OrderType, PartialCreateOrderOptions,
        BalanceAllowanceParams, AssetType,
    )
except ImportError as e:  # pragma: no cover - import guard
    raise ImportError(
        "clob_live.py requires `pip install py-clob-client`. "
        "Add to polymarket_agent/requirements.txt + Dockerfile."
    ) from e


_HEX_KEY = re.compile(r"(0x)?[0-9a-fA-F]{64}")


class KeyFileError(RuntimeError):
    """Raised when the wallet key file is missing, mis-permissioned, or invalid."""


def read_key_file(key_path) -> str:
    """Load + validate a private key from a secure file. Fail loud.

    Mirrors wallet.py: perms must be 0o600/0o400, content must be 64 hex
    chars (optional 0x), BOM-safe. Returns a 0x-prefixed key string.
    """
    p = Path(key_path)
    if not p.exists():
        raise KeyFileError(f"wallet key file missing at {p}")
    mode = p.stat().st_mode & 0o777
    if mode not in (0o600, 0o400):
        raise KeyFileError(
            f"wallet key file perms {oct(mode)} at {p} -- expected 0o600 or 0o400"
        )
    text = p.read_text(encoding="utf-8-sig").strip()
    if not _HEX_KEY.fullmatch(text):
        raise KeyFileError(f"wallet key file at {p} is not a 64-hex-char private key")
    return text if text.startswith("0x") else "0x" + text


class LiveClobBackend:
    """Real CLOB order execution. The executor's check 9 calls place_order;
    everything before that (the 9 risk pre-checks) stays in PolymarketExecutor."""

    def __init__(self, private_key: str, host: str, chain_id: int = 137,
                 funder: str = None, signature_type: int = 0, auto_auth: bool = True):
        # signature_type 0 = EOA (funds held directly in the signing wallet).
        # For a Polymarket proxy / Gnosis-safe funder, pass 1 or 2 + funder addr.
        self._client = ClobClient(
            host, key=private_key, chain_id=chain_id,
            signature_type=signature_type, funder=funder,
        )
        self.address = self._client.get_address()
        self.authed = False
        self._creds = None
        if auto_auth:
            self.ensure_auth()

    def ensure_auth(self):
        """Derive + set L2 API creds, then assert both auth levels.

        create_or_derive_api_creds makes a real L1-signed call to the live CLOB
        (no on-chain tx, no balance required) -- this is the $0 proof that the
        signing chain is accepted by Polymarket's server."""
        creds = self._client.create_or_derive_api_creds()
        self._client.set_api_creds(creds)
        self._client.assert_level_1_auth()
        self._client.assert_level_2_auth()
        self._creds = creds
        self.authed = True
        return creds

    def get_usdc_balance(self) -> Decimal:
        """Real USDC.e collateral balance the CLOB will check on order accept."""
        params = BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        bal = self._client.get_balance_allowance(params)
        raw = bal.get("balance", 0) if isinstance(bal, dict) else 0
        return Decimal(str(raw)) / Decimal(10 ** 6)

    @staticmethod
    def extract_order_id(resp) -> str | None:
        if not resp or not isinstance(resp, dict):
            return None
        return resp.get("orderID") or resp.get("orderId") or resp.get("id")

    def place_order(self, token_id, price, size, side: str = "BUY",
                    order_type=None):
        """Build + sign + post a real order. neg-risk + tick-size aware.

        token_id: the outcome token id string (NOT the condition_id).
        price: limit price 0..1. size: number of outcome shares.
        side: 'BUY' or 'SELL'.
        """
        if float(price) <= 0:
            raise ValueError(f"price must be > 0, got {price}")
        if float(size) <= 0:
            raise ValueError(f"size must be > 0, got {size}")

        neg_risk = self._client.get_neg_risk(str(token_id))
        tick = self._client.get_tick_size(str(token_id))
        args = OrderArgs(
            token_id=str(token_id), price=float(price), size=float(size), side=side,
        )
        options = PartialCreateOrderOptions(tick_size=tick, neg_risk=neg_risk)
        signed = self._client.create_order(args, options=options)
        otype = order_type if order_type is not None else OrderType.GTC
        return self._client.post_order(signed, otype)

    def submit_order(self, signed_or_args):
        """Adapter kept for interface symmetry with the read-only PolymarketCLOB.
        Live execution should call place_order directly."""
        raise NotImplementedError("use place_order on the live backend")

    def cancel(self, order_id):
        return self._client.cancel(order_id)
