"""Polygon wallet. Loads key from secrets vault. Signs CLOB EIP-712 orders.
Never logs private key. Never sends it to LLM."""
from decimal import Decimal
from pathlib import Path

try:
    from eth_account import Account
    from web3 import Web3
except ImportError as e:
    raise ImportError(
        "wallet.py requires `pip install web3 eth-account`. "
        "Add to polymarket_agent/Dockerfile."
    ) from e

POLYGON_RPC = "https://polygon-rpc.com"
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
        key_text = key_path.read_text().strip()
        if not key_text:
            raise RuntimeError(f"wallet key file empty at {key_path}")
        self._account = Account.from_key(key_text)
        self.address = self._account.address
        self._w3 = Web3(Web3.HTTPProvider(rpc_url))
        self._usdc = self._w3.eth.contract(address=USDC_E_ADDR, abi=USDC_E_ABI)

    def get_usdc_balance(self) -> Decimal:
        raw = self._usdc.functions.balanceOf(self.address).call()
        return Decimal(raw) / Decimal(10**6)

    def get_matic_balance(self) -> Decimal:
        raw = self._w3.eth.get_balance(self.address)
        return Decimal(raw) / Decimal(10**18)

    def sign_clob_order(self, typed_data: dict) -> str:
        """EIP-712 sign. Returns hex signature."""
        signed = Account.sign_typed_data(self._account.key, full_message=typed_data)
        return signed.signature.hex()
