#!/usr/bin/env python3
"""One-time 'enable trading' -- approve USDC.e + outcome tokens to Polymarket's
exchange contracts so the CLOB can actually use the wallet's collateral.

WHY: USDC.e sitting in the wallet is NOT usable until it's approved (allowance)
to the exchange contracts -- that's why the CLOB reports $0 collateral despite a
funded wallet. Polymarket's UI does this on first deposit; our EOA bot must do it
itself. This is what their docs call setting allowances. Done once.

Approves (standard Polymarket EOA setup on Polygon):
  - USDC.e.approve(spender, max)         for CTF Exchange + Neg-Risk Exchange + Adapter
  - CTF.setApprovalForAll(operator,true) for the same (needed to SELL outcome tokens)

DRY-RUN by default; --confirm to sign + send. ~6 small gasless-ish txs.
"""
import argparse
import sys

from polymarket_agent.execution.clob_live import read_key_file
from polymarket_agent.paths import wallet_key_path

RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://polygon.llamarpc.com", "https://1rpc.io/matic"]
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"  # ConditionalTokens
# Polymarket exchange contracts (Polygon) -- the CURRENT operator/spender set the
# live CLOB actually checks (read from get_balance_allowance().allowances; the
# older 0x4bFb/0xC5d5/0x7876 set in research docs is stale and rejected).
SPENDERS = {
    "Operator A": "0xE111180000d2663C0091e4f400237545B87B996B",
    "Operator B": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
    "Operator C": "0xe2222d279d744050d28e00520010520000310F59",
}
MAX_UINT = (1 << 256) - 1
ERC20_APPROVE = [{"name": "approve", "inputs": [{"name": "s", "type": "address"}, {"name": "a", "type": "uint256"}],
                  "outputs": [{"name": "", "type": "bool"}], "type": "function", "stateMutability": "nonpayable"},
                 {"name": "allowance", "inputs": [{"name": "o", "type": "address"}, {"name": "s", "type": "address"}],
                  "outputs": [{"name": "", "type": "uint256"}], "type": "function", "stateMutability": "view"}]
CTF_ABI = [{"name": "setApprovalForAll", "inputs": [{"name": "op", "type": "address"}, {"name": "ok", "type": "bool"}],
            "outputs": [], "type": "function", "stateMutability": "nonpayable"},
           {"name": "isApprovedForAll", "inputs": [{"name": "o", "type": "address"}, {"name": "op", "type": "address"}],
            "outputs": [{"name": "", "type": "bool"}], "type": "function", "stateMutability": "view"}]


def _w3():
    from web3 import Web3
    for u in RPCS:
        try:
            w = Web3(Web3.HTTPProvider(u, request_kwargs={"timeout": 15}))
            if w.is_connected() and w.eth.chain_id == 137:
                return w
        except Exception:
            continue
    raise RuntimeError("no Polygon RPC")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=None)
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args()
    from web3 import Web3
    from eth_account import Account
    acct = Account.from_key(read_key_file(args.key or wallet_key_path()))
    w3 = _w3(); me = acct.address
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_E), abi=ERC20_APPROVE)
    ctf = w3.eth.contract(address=Web3.to_checksum_address(CTF), abi=CTF_ABI)

    print("=" * 60); print("  ENABLE TRADING -- approve collateral to Polymarket"); print("=" * 60)
    print(f"  wallet: {me}")
    todo = []
    for name, spender in SPENDERS.items():
        sp = Web3.to_checksum_address(spender)
        allow = usdc.functions.allowance(me, sp).call()
        approved = ctf.functions.isApprovedForAll(me, sp).call()
        print(f"  {name}: USDC.e allowance={'SET' if allow > 0 else 'MISSING'}  "
              f"CTF approvedForAll={'YES' if approved else 'NO'}")
        if allow == 0:
            todo.append(("usdc_approve", name, sp))
        if not approved:
            todo.append(("ctf_approve", name, sp))

    if not todo:
        print("\n  Already fully enabled for trading. Nothing to do.")
        return 0
    print(f"\n  {len(todo)} approval tx(s) needed.")
    if not args.confirm:
        print("  DRY-RUN. Re-run with --confirm to sign + send.")
        print("=" * 60); return 0

    pol = w3.eth.get_balance(me)
    if pol == 0:
        print("[ABORT] no POL for gas"); return 2
    nonce = w3.eth.get_transaction_count(me)
    gp = w3.eth.gas_price
    for kind, name, sp in todo:
        if kind == "usdc_approve":
            tx = usdc.functions.approve(sp, MAX_UINT)
        else:
            tx = ctf.functions.setApprovalForAll(sp, True)
        built = tx.build_transaction({"from": me, "nonce": nonce, "gas": 120000, "gasPrice": gp, "chainId": 137})
        signed = acct.sign_transaction(built)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"  {kind} -> {name}: {h.hex()}")
        w3.eth.wait_for_transaction_receipt(h, timeout=180)
        nonce += 1
    print("\n  TRADING ENABLED. The CLOB can now use your USDC.e collateral.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
