#!/usr/bin/env python3
"""Show the bot wallet balances + current growth phase. Read-only, no key needed
to VIEW (the wallet is public on Polygon). Run anytime: python3 -m kalshi_agent.balance"""
import json
import sys
import urllib.request
from decimal import Decimal
from pathlib import Path

import yaml

ADDR_FILE = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.addr"
CONFIG = Path(__file__).parent / "config.yaml"
RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://polygon.llamarpc.com",
        "https://1rpc.io/matic", "https://polygon.drpc.org"]
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"


def _rpc(url, method, params):
    req = urllib.request.Request(url, data=json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "ev/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read()).get("result")


def _erc20(url, token, addr):
    data = "0x70a08231" + addr[2:].rjust(64, "0")
    r = _rpc(url, "eth_call", [{"to": token, "data": data}, "latest"])
    return int(r, 16) if r and r != "0x" else 0


def main():
    addr = (sys.argv[1] if len(sys.argv) > 1
            else Path(ADDR_FILE).read_text().strip() if Path(ADDR_FILE).exists() else None)
    if not addr:
        print("no wallet address"); return 2
    for url in RPCS:
        try:
            pol = int(_rpc(url, "eth_getBalance", [addr, "latest"]) or "0x0", 16) / 1e18
            ue = _erc20(url, USDC_E, addr) / 1e6
            un = _erc20(url, USDC_NATIVE, addr) / 1e6
            break
        except Exception:
            continue
    else:
        print("all RPCs failed"); return 3

    cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    from kalshi_agent import growth
    tradeable = Decimal(str(ue))
    plan = growth.harvest_plan(tradeable, cfg)
    tier = growth.max_bet_for(tradeable, cfg)

    print("=" * 56)
    print("  EVERLIGHT POLYMARKET WALLET")
    print("=" * 56)
    print(f"  address: {addr}")
    print(f"  view anytime: https://polygonscan.com/address/{addr}")
    print(f"               https://debank.com/profile/{addr}")
    print("  ---")
    print(f"  USDC.e (tradeable collateral): ${ue:,.2f}")
    print(f"  USDC (native, needs swap):     ${un:,.2f}")
    print(f"  POL (gas):                     {pol:,.4f}")
    print("  ---")
    print(f"  growth phase:   {plan['phase']}  ({plan['reason']})")
    print(f"  max bet ceiling (this tier):   ${tier:,.0f}")
    print(f"  withdraw available today:      ${plan['withdraw_today']:,.2f}")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    sys.exit(main())
