# NOTE: do not add logging to this module; any log call risks
# leaking key fragments via repr or traceback.
"""Polygon wallet. Loads key from secrets vault. Signs CLOB EIP-712 orders.
Never logs private key. Never sends it to LLM."""
import re
from decimal import Decimal
from pathlib import Path

try:
    from eth_account import Account
    from web3 import Web3
except ImportError as e:
    raise ImportError(
        "wallet.py requires `pip install web3 eth-account`. "
        "Add to kalshi_agent/Dockerfile."
    ) from e

# polygon-rpc.com now returns 401 (auth-required). Use a no-key public endpoint.
POLYGON_RPC = "https://polygon-bor-rpc.publicnode.com"
USDC_E_ADDR = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC.e on Polygon
USDC_E_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],' \
             '"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],' \
             '"type":"function"}]'


class PolygonWallet:
    def __init__(self, private_key_path: Path, rpc_url: str = POLYGON_RPC):
        key_path = Path(private_key_path)
        if not key_path.exists():
            raise RuntimeError(
                f"wallet key file missing at {key_path} -- aborting wallet load"
            )

        # I1 -- file permission check. Security-meaningful invariant: NO world
        # (other) access. Group access (0o660) is tolerated because Android
        # sdcard/exFAT cannot represent finer perms; on real ext4 prefer 0o600.
        mode = key_path.stat().st_mode & 0o777
        if mode & 0o007:
            raise RuntimeError(
                f"wallet key file perms {oct(mode)} at {key_path} are world-accessible -- forbidden"
            )

        # I3 -- BOM-safe read + hex validation
        key_text = key_path.read_text(encoding="utf-8-sig").strip()
        if not re.fullmatch(r"(0x)?[0-9a-fA-F]{64}", key_text):
            raise RuntimeError(
                f"wallet key file at {key_path} is not a 64-hex-char private key"
            )

        # C2 -- closure-based signer: capture raw key bytes in closure cell only.
        # We do NOT keep a LocalAccount on self; bound methods retain LocalAccount
        # via __self__, which exposes .key (the residual leak closed here).
        try:
            key_bytes = bytes.fromhex(key_text.removeprefix("0x"))
            address = Account.from_key(key_bytes).address
        except Exception as e:
            raise RuntimeError(
                f"wallet key file at {key_path} failed Account.from_key validation -- refusing to start"
            ) from e

        self.address = address

        # Bind key_bytes via default-arg so the closure owns its own private copy
        # in _kb rather than sharing the enclosing-scope cell for key_bytes.
        # Deleting key_bytes and key_text below then only removes the local names;
        # _kb inside the closure is unaffected.
        def _sign(*, full_message, _kb=key_bytes):
            return Account.sign_typed_data(_kb, full_message=full_message)

        self.__signer = _sign

        # Scrub locals so a traceback through RPC checks does not expose key material.
        del key_text
        del key_bytes

        self._w3 = Web3(Web3.HTTPProvider(rpc_url))

        # I2 -- RPC health + chain check at construct time (after key material scrubbed)
        if not self._w3.is_connected():
            raise RuntimeError(
                f"polygon RPC unreachable at {rpc_url} -- aborting wallet init"
            )
        chain_id = self._w3.eth.chain_id
        if chain_id != 137:
            raise RuntimeError(
                f"wrong chain: expected 137 (Polygon mainnet), got {chain_id}"
            )

        self._usdc = self._w3.eth.contract(address=USDC_E_ADDR, abi=USDC_E_ABI)

    def get_usdc_balance(self) -> Decimal:
        raw = self._usdc.functions.balanceOf(self.address).call()
        return Decimal(raw) / Decimal(10**6)

    def get_matic_balance(self) -> Decimal:
        raw = self._w3.eth.get_balance(self.address)
        return Decimal(raw) / Decimal(10**18)

    def sign_clob_order(self, typed_data: dict) -> str:
        """EIP-712 sign. Returns hex signature string with 0x prefix.

        NOTE: do not log inputs or outputs of this method; signature material
        must not appear in any branded Slack alert or log line.
        """
        # I6 -- EIP-712 sanity checks
        required = {"types", "primaryType", "domain", "message"}
        missing = required - typed_data.keys()
        if missing:
            raise RuntimeError(f"typed_data missing keys: {sorted(missing)}")
        chain_id_in_data = typed_data.get("domain", {}).get("chainId", 137)
        if chain_id_in_data != 137:
            raise RuntimeError(
                f"typed_data chainId {chain_id_in_data} != 137 -- refusing to sign"
            )

        # C1 -- call closure signer; key_bytes captured in closure cell, not on self
        sig_bytes = self.__signer(full_message=typed_data).signature
        sig = sig_bytes.hex()
        return sig if sig.startswith("0x") else "0x" + sig
