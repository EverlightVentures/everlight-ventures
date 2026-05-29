#!/usr/bin/env python3
"""Guarded profit withdrawal -- pay yourself from the bot wallet.

The bot wallet is YOURS; the bot just holds the key. This sends funds OUT to
your personal address. Two modes:

  manual:  withdraw a specific amount to your address
  sweep:   keep a fixed working bankroll, send everything above it (passive
           profit-taking -- run on a daily/weekly cron once set).

SAFETY:
- DESTINATION LOCK: it will only send to the treasury address configured in
  config.yaml `treasury.address` (your personal wallet). It refuses any other
  --to unless that address matches. The bot can NEVER send your money elsewhere.
- DRY-RUN by default; --confirm required to sign + send.
- Working-capital floor: sweep never drains below `treasury.working_capital`.

Usage:
  python3 withdraw.py                              # dry-run sweep preview
  python3 withdraw.py --amount 100 --confirm       # send $100 USDC.e to treasury
  python3 withdraw.py --sweep --confirm            # send profit above working capital
"""
import argparse
import sys
from decimal import Decimal
from pathlib import Path

import yaml

from polymarket_agent.execution.clob_live import read_key_file

DEFAULT_KEY = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key"
CONFIG = Path(__file__).parent / "config.yaml"
RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://polygon.llamarpc.com",
        "https://1rpc.io/matic", "https://polygon.drpc.org"]
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
ERC20_ABI = [
    {"name":"balanceOf","inputs":[{"name":"o","type":"address"}],
     "outputs":[{"name":"","type":"uint256"}],"type":"function","stateMutability":"view"},
    {"name":"transfer","inputs":[{"name":"to","type":"address"},{"name":"a","type":"uint256"}],
     "outputs":[{"name":"","type":"bool"}],"type":"function","stateMutability":"nonpayable"},
]


def _w3():
    from web3 import Web3
    for url in RPCS:
        try:
            w = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 15}))
            if w.is_connected() and w.eth.chain_id == 137:
                return w, url
        except Exception:
            continue
    raise RuntimeError("no working Polygon RPC")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--to", default=None, help="destination (must match config treasury.address)")
    ap.add_argument("--amount", type=float, default=None, help="USDC.e to send")
    ap.add_argument("--sweep", action="store_true", help="send all profit above working_capital")
    ap.add_argument("--confirm", action="store_true", help="ACTUALLY sign + send (else dry-run)")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    treasury = (cfg.get("treasury") or {})
    locked_addr = treasury.get("address")
    working_capital = Decimal(str(treasury.get("working_capital", 250)))

    if not locked_addr or "REPLACE" in str(locked_addr):
        print("[ABORT] No treasury.address set in config.yaml. Add YOUR personal")
        print("        Polygon address under `treasury: { address: 0x...,")
        print("        working_capital: 250 }` first. This locks where profit can go.")
        return 2

    dest = args.to or locked_addr
    if dest.lower() != locked_addr.lower():
        print(f"[ABORT] --to {dest} != locked treasury {locked_addr}. Refusing.")
        return 2

    from web3 import Web3
    from eth_account import Account
    acct = Account.from_key(read_key_file(args.key))
    w3, rpc = _w3()
    me = acct.address
    usdce = w3.eth.contract(address=Web3.to_checksum_address(USDC_E), abi=ERC20_ABI)
    bal = Decimal(usdce.functions.balanceOf(me).call()) / Decimal(10**6)
    pol = Decimal(w3.eth.get_balance(me)) / Decimal(10**18)

    print("=" * 60)
    print("  WITHDRAW / PAY YOURSELF (USDC.e -> your treasury)")
    print("=" * 60)
    print(f"  bot wallet:      {me}")
    print(f"  treasury (you):  {locked_addr}")
    print(f"  USDC.e balance:  {bal:.4f}   POL gas: {pol:.4f}")
    print(f"  working capital: {working_capital:.2f} (kept in bot)")

    if args.sweep:
        amount = max(Decimal(0), bal - working_capital)
        label = f"SWEEP profit above {working_capital}"
    elif args.amount is not None:
        amount = Decimal(str(args.amount)); label = "MANUAL"
    else:
        amount = max(Decimal(0), bal - working_capital)
        label = f"SWEEP preview (profit above {working_capital})"

    print(f"  action: {label}  ->  send {amount:.4f} USDC.e")
    if amount <= 0:
        print("\n  Nothing to withdraw (balance <= working capital).")
        return 0
    if amount > bal:
        print(f"\n[ABORT] {amount} > balance {bal}")
        return 2
    if pol <= 0:
        print("\n[ABORT] no POL for gas")
        return 2

    if not args.confirm:
        print("\n  DRY-RUN. No funds moved. Re-run with --confirm to send.")
        print("=" * 60)
        return 0

    raw = int(amount * Decimal(10**6))
    tx = usdce.functions.transfer(Web3.to_checksum_address(locked_addr), raw).build_transaction(
        {"from": me, "nonce": w3.eth.get_transaction_count(me),
         "gas": 90000, "gasPrice": w3.eth.gas_price, "chainId": 137})
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"\n  withdraw tx: {h.hex()}")
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    print(f"  status: {'SUCCESS' if rcpt.get('status')==1 else 'FAILED'}")
    print(f"  sent {amount:.4f} USDC.e to {locked_addr}")
    print("=" * 60)
    return 0 if rcpt.get("status") == 1 else 4


if __name__ == "__main__":
    sys.exit(main())
