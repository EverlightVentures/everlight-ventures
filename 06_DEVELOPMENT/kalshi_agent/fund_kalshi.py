#!/usr/bin/env python3
"""Move wallet funds -> Kalshi (Zero Hash deposit address). Guarded + irreversible.

The wallet holds USDC.e (bridged, 0x2791). Kalshi/Zero Hash on Polygon most likely
wants NATIVE USDC (0x3c49). So: swap USDC.e -> native USDC, then ERC20-transfer it
to the Zero Hash deposit address. Zero Hash converts it to USD in the Kalshi account.

SAFETY (the $500-loss + irreversible-send lessons):
- DRY-RUN by default. --confirm required to sign anything.
- Sends are IRREVERSIBLE -> always test a small amount first and confirm it credits
  in the Kalshi balance (via the API) BEFORE sending the rest.
- Slippage-capped stable<->stable swap.

Subcommands:
  balance
  swap  --amount 5            [--confirm]   # USDC.e -> native USDC
  send  --amount 3 --to 0x..  [--token native|usdce] [--confirm]   # ERC20 transfer
"""
import argparse
import sys
from decimal import Decimal

from kalshi_agent.execution.clob_live import read_key_file

KEY = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key"
RPCS = ["https://1rpc.io/matic", "https://polygon.llamarpc.com",
        "https://polygon.drpc.org", "https://polygon-bor-rpc.publicnode.com"]
USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
USDC_E      = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
SWAP_ROUTER = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"
QUOTER_V2   = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
FEE_TIERS   = [100, 500]

ERC20 = [
    {"name":"balanceOf","inputs":[{"name":"o","type":"address"}],"outputs":[{"type":"uint256"}],"type":"function","stateMutability":"view"},
    {"name":"allowance","inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],"outputs":[{"type":"uint256"}],"type":"function","stateMutability":"view"},
    {"name":"approve","inputs":[{"name":"s","type":"address"},{"name":"a","type":"uint256"}],"outputs":[{"type":"bool"}],"type":"function","stateMutability":"nonpayable"},
    {"name":"transfer","inputs":[{"name":"to","type":"address"},{"name":"a","type":"uint256"}],"outputs":[{"type":"bool"}],"type":"function","stateMutability":"nonpayable"},
]
QUOTER_ABI = [{"name":"quoteExactInputSingle","inputs":[{"components":[
    {"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},
    {"name":"amountIn","type":"uint256"},{"name":"fee","type":"uint24"},
    {"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"params","type":"tuple"}],
    "outputs":[{"name":"amountOut","type":"uint256"},{"name":"a","type":"uint160"},
    {"name":"b","type":"uint32"},{"name":"c","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]
ROUTER_ABI = [{"name":"exactInputSingle","inputs":[{"components":[
    {"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},
    {"name":"fee","type":"uint24"},{"name":"recipient","type":"address"},
    {"name":"amountIn","type":"uint256"},{"name":"amountOutMinimum","type":"uint256"},
    {"name":"sqrtPriceLimitX96","type":"uint160"}],"name":"params","type":"tuple"}],
    "outputs":[{"name":"amountOut","type":"uint256"}],"stateMutability":"payable","type":"function"}]


def _w3():
    from web3 import Web3
    for u in RPCS:
        try:
            w = Web3(Web3.HTTPProvider(u, request_kwargs={"timeout": 15}))
            if w.is_connected() and w.eth.chain_id == 137:
                return w, u
        except Exception:
            continue
    raise RuntimeError("no working Polygon RPC")


def _acct():
    from eth_account import Account
    return Account.from_key(read_key_file(KEY))


def cmd_balance(w3, me):
    from web3 import Web3
    for name, addr in (("native USDC", USDC_NATIVE), ("USDC.e", USDC_E)):
        c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ERC20)
        print(f"  {name:12}: {c.functions.balanceOf(me).call()/1e6:.4f}")
    print(f"  POL (gas)   : {w3.eth.get_balance(me)/1e18:.4f}")


def cmd_swap(w3, acct, me, amount, slippage, confirm):
    from web3 import Web3
    src = w3.eth.contract(address=Web3.to_checksum_address(USDC_E), abi=ERC20)
    bal = src.functions.balanceOf(me).call()
    amt = int(Decimal(str(amount)) * 1_000_000)
    if amt <= 0 or amt > bal:
        print(f"[ABORT] amount {amt/1e6} > USDC.e balance {bal/1e6}"); return 2
    q = w3.eth.contract(address=Web3.to_checksum_address(QUOTER_V2), abi=QUOTER_ABI)
    best = (None, 0)
    for fee in FEE_TIERS:
        try:
            out = q.functions.quoteExactInputSingle((Web3.to_checksum_address(USDC_E),
                  Web3.to_checksum_address(USDC_NATIVE), amt, fee, 0)).call()
            o = out[0] if isinstance(out, (list, tuple)) else out
            if o > best[1]: best = (fee, o)
        except Exception:
            continue
    fee, out_raw = best
    if not fee:
        print("[ABORT] no USDC.e->native route"); return 3
    min_out = int(out_raw * (1 - slippage))
    print(f"  swap {amt/1e6:.4f} USDC.e -> ~{out_raw/1e6:.4f} native USDC "
          f"(min {min_out/1e6:.4f}, fee {fee/10000:.2f}%)")
    if not confirm:
        print("  DRY-RUN -- add --confirm to execute"); return 0
    router_cs = Web3.to_checksum_address(SWAP_ROUTER)
    nonce = w3.eth.get_transaction_count(me); gp = w3.eth.gas_price
    if src.functions.allowance(me, router_cs).call() < amt:
        tx = src.functions.approve(router_cs, amt).build_transaction(
            {"from": me, "nonce": nonce, "gas": 80000, "gasPrice": gp, "chainId": 137})
        h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
        print(f"  approve tx: {h.hex()}"); w3.eth.wait_for_transaction_receipt(h, timeout=180); nonce += 1
    router = w3.eth.contract(address=router_cs, abi=ROUTER_ABI)
    tx = router.functions.exactInputSingle((Web3.to_checksum_address(USDC_E),
        Web3.to_checksum_address(USDC_NATIVE), fee, me, amt, min_out, 0)).build_transaction(
        {"from": me, "nonce": nonce, "gas": 300000, "gasPrice": gp, "chainId": 137})
    h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
    print(f"  swap tx: {h.hex()}")
    r = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    print("  status:", "SUCCESS" if r.get("status") == 1 else "FAILED")
    return 0 if r.get("status") == 1 else 4


def cmd_send(w3, acct, me, amount, to, token, confirm):
    from web3 import Web3
    addr = USDC_NATIVE if token == "native" else USDC_E
    c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ERC20)
    bal = c.functions.balanceOf(me).call()
    amt = int(Decimal(str(amount)) * 1_000_000)
    to_cs = Web3.to_checksum_address(to)
    print(f"  SEND {amt/1e6:.4f} {token} USDC -> {to_cs}")
    print(f"  (token bal {bal/1e6:.4f})  *** IRREVERSIBLE ***")
    if amt <= 0 or amt > bal:
        print(f"[ABORT] amount > balance"); return 2
    if not confirm:
        print("  DRY-RUN -- add --confirm to actually send"); return 0
    nonce = w3.eth.get_transaction_count(me); gp = w3.eth.gas_price
    tx = c.functions.transfer(to_cs, amt).build_transaction(
        {"from": me, "nonce": nonce, "gas": 100000, "gasPrice": gp, "chainId": 137})
    h = w3.eth.send_raw_transaction(acct.sign_transaction(tx).raw_transaction)
    print(f"  transfer tx: {h.hex()}")
    r = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    print("  status:", "SUCCESS" if r.get("status") == 1 else "FAILED")
    print(f"  polygonscan: https://polygonscan.com/tx/{h.hex()}")
    return 0 if r.get("status") == 1 else 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["balance", "swap", "send"])
    ap.add_argument("--amount", type=float)
    ap.add_argument("--to")
    ap.add_argument("--token", choices=["native", "usdce"], default="native")
    ap.add_argument("--slippage", type=float, default=0.005)
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    w3, rpc = _w3()
    acct = _acct(); me = acct.address
    print("=" * 60); print(f"  FUND KALSHI  wallet {me}  rpc {rpc}"); print("=" * 60)
    if args.cmd == "balance":
        return cmd_balance(w3, me) or 0
    if args.cmd == "swap":
        return cmd_swap(w3, acct, me, args.amount, args.slippage, args.confirm)
    if args.cmd == "send":
        if not args.to:
            print("[ABORT] --to required"); return 2
        return cmd_send(w3, acct, me, args.amount, args.to, args.token, args.confirm)


if __name__ == "__main__":
    sys.exit(main())
