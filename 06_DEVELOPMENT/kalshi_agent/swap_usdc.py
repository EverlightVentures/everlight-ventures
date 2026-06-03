#!/usr/bin/env python3
"""Guarded native-USDC -> USDC.e swap on Polygon (Uniswap v3).

Polymarket's CLOB collateral is USDC.e (0x2791...). Crypto.com sends NATIVE USDC
(0x3c49...). This converts one to the other so the bot can trade.

SAFETY (the $500-loss lesson):
- DRY-RUN by default. It quotes the real route + shows expected output + min-out
  and DOES NOT sign anything. You must pass --confirm to move funds.
- Operator-gated: requires --confirm; refuses if balance/gas insufficient.
- Slippage-capped (default 0.5%, stable<->stable).
- Reads the wallet key from the same secure file the bot uses.

Usage:
  python3 swap_usdc.py                  # dry-run: quote the whole native USDC balance
  python3 swap_usdc.py --amount 4.0     # dry-run a specific amount
  python3 swap_usdc.py --amount 4.0 --confirm   # ACTUALLY swap (signs + sends)
"""
import argparse
import sys
import time
from decimal import Decimal

from kalshi_agent.execution.clob_live import read_key_file

DEFAULT_KEY = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key"
RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://polygon.llamarpc.com",
        "https://1rpc.io/matic", "https://polygon.drpc.org"]

USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
USDC_E      = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
SWAP_ROUTER = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"  # Uniswap SwapRouter02 (Polygon)
QUOTER_V2   = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"  # Uniswap QuoterV2 (Polygon)
FEE_TIERS   = [100, 500]  # 0.01%, 0.05% -- try tightest stable pool first

ERC20_ABI = [
    {"name":"balanceOf","constant":True,"inputs":[{"name":"o","type":"address"}],
     "outputs":[{"name":"","type":"uint256"}],"type":"function","stateMutability":"view"},
    {"name":"allowance","constant":True,"inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],
     "outputs":[{"name":"","type":"uint256"}],"type":"function","stateMutability":"view"},
    {"name":"approve","constant":False,"inputs":[{"name":"s","type":"address"},{"name":"a","type":"uint256"}],
     "outputs":[{"name":"","type":"bool"}],"type":"function","stateMutability":"nonpayable"},
]
QUOTER_ABI = [{"name":"quoteExactInputSingle","inputs":[{"components":[
    {"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},
    {"name":"amountIn","type":"uint256"},{"name":"fee","type":"uint24"},
    {"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"params","type":"tuple"}],
    "outputs":[{"name":"amountOut","type":"uint256"},{"name":"a","type":"uint160"},
    {"name":"b","type":"uint32"},{"name":"c","type":"uint256"}],
    "stateMutability":"nonpayable","type":"function"}]
ROUTER_ABI = [{"name":"exactInputSingle","inputs":[{"components":[
    {"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},
    {"name":"fee","type":"uint24"},{"name":"recipient","type":"address"},
    {"name":"amountIn","type":"uint256"},{"name":"amountOutMinimum","type":"uint256"},
    {"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"params","type":"tuple"}],
    "outputs":[{"name":"amountOut","type":"uint256"}],
    "stateMutability":"payable","type":"function"}]


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


def quote_best(w3, amount_in_raw):
    """Return (fee_tier, amount_out_raw) for the best pool, or (None, 0)."""
    from web3 import Web3
    q = w3.eth.contract(address=Web3.to_checksum_address(QUOTER_V2), abi=QUOTER_ABI)
    best = (None, 0)
    for fee in FEE_TIERS:
        try:
            params = (Web3.to_checksum_address(USDC_NATIVE), Web3.to_checksum_address(USDC_E),
                      amount_in_raw, fee, 0)
            out = q.functions.quoteExactInputSingle(params).call()
            amt = out[0] if isinstance(out, (list, tuple)) else out
            if amt > best[1]:
                best = (fee, amt)
        except Exception:
            continue
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--amount", type=float, default=None, help="USDC to swap (default: full native balance)")
    ap.add_argument("--slippage", type=float, default=0.005, help="max slippage (0.005 = 0.5%)")
    ap.add_argument("--confirm", action="store_true", help="ACTUALLY sign + send (else dry-run)")
    args = ap.parse_args()

    from web3 import Web3
    from eth_account import Account
    key = read_key_file(args.key)
    acct = Account.from_key(key)
    w3, rpc = _w3()
    me = acct.address
    print("=" * 60)
    print("  USDC native -> USDC.e SWAP (Polygon, Uniswap v3)")
    print("=" * 60)
    print(f"  wallet: {me}")
    print(f"  rpc:    {rpc}")

    native = w3.eth.contract(address=Web3.to_checksum_address(USDC_NATIVE), abi=ERC20_ABI)
    bal_raw = native.functions.balanceOf(me).call()
    pol = w3.eth.get_balance(me)
    print(f"  native USDC balance: {bal_raw/1e6:.4f}")
    print(f"  POL (gas):           {pol/1e18:.4f}")

    amount_raw = int(Decimal(str(args.amount)) * 1_000_000) if args.amount else bal_raw
    if amount_raw <= 0 or amount_raw > bal_raw:
        print(f"\n[ABORT] requested {amount_raw/1e6} > balance {bal_raw/1e6}")
        return 2
    if pol == 0:
        print("\n[ABORT] no POL for gas")
        return 2

    fee, out_raw = quote_best(w3, amount_raw)
    if not fee:
        print("\n[ABORT] no Uniswap v3 route found (native USDC <-> USDC.e). "
              "Try a smaller amount or use an aggregator.")
        return 3
    min_out = int(out_raw * (1 - args.slippage))
    print(f"\n  ROUTE: Uniswap v3 fee tier {fee/10000:.2f}%")
    print(f"  swap in:   {amount_raw/1e6:.4f} native USDC")
    print(f"  expect out:{out_raw/1e6:.4f} USDC.e  (min {min_out/1e6:.4f} at {args.slippage*100:.1f}% slippage)")

    if not args.confirm:
        print("\n  DRY-RUN. No funds moved. Re-run with --confirm to execute.")
        print("=" * 60)
        return 0

    # ---- EXECUTE (operator confirmed) ----
    router_cs = Web3.to_checksum_address(SWAP_ROUTER)
    allowance = native.functions.allowance(me, router_cs).call()
    nonce = w3.eth.get_transaction_count(me)
    gas_price = w3.eth.gas_price
    if allowance < amount_raw:
        print("\n  approving USDC to router...")
        atx = native.functions.approve(router_cs, amount_raw).build_transaction(
            {"from": me, "nonce": nonce, "gas": 80000, "gasPrice": gas_price, "chainId": 137})
        signed = acct.sign_transaction(atx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  approve tx: {h.hex()}")
        w3.eth.wait_for_transaction_receipt(h, timeout=180)
        nonce += 1

    router = w3.eth.contract(address=router_cs, abi=ROUTER_ABI)
    params = (Web3.to_checksum_address(USDC_NATIVE), Web3.to_checksum_address(USDC_E),
              fee, me, amount_raw, min_out, 0)
    stx = router.functions.exactInputSingle(params).build_transaction(
        {"from": me, "nonce": nonce, "gas": 300000, "gasPrice": gas_price, "chainId": 137})
    signed = acct.sign_transaction(stx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"\n  swap tx: {h.hex()}")
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    ok = rcpt.get("status") == 1
    usdce = w3.eth.contract(address=Web3.to_checksum_address(USDC_E), abi=ERC20_ABI)
    new_e = usdce.functions.balanceOf(me).call()
    print(f"  status: {'SUCCESS' if ok else 'FAILED'}")
    print(f"  USDC.e balance now: {new_e/1e6:.4f}")
    print("=" * 60)
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
