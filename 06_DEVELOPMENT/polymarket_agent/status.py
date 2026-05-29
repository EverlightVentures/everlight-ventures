#!/usr/bin/env python3
"""EVERLIGHT POLYMARKET -- account + activity dashboard (CLI).

One screen: on-chain balance, growth phase, open/closed paper bets, calibration
stats (Brier, win-rate, P&L), recent predictions, and last cycle time. Read-only.
Run anytime:  python3 -m polymarket_agent.status
"""
import json
import sys
import time
import urllib.request
from decimal import Decimal
from pathlib import Path

ADDR_FILE = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.addr"
RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://polygon.llamarpc.com", "https://1rpc.io/matic"]
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_NATIVE = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"


def _rpc(url, method, params):
    req = urllib.request.Request(url, data=json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "ev/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=12).read()).get("result")


def _bal(url, token, addr):
    r = _rpc(url, "eth_call", [{"to": token, "data": "0x70a08231" + addr[2:].rjust(64, "0")}, "latest"])
    return (int(r, 16) if r and r != "0x" else 0) / 1e6


def _onchain(addr):
    for u in RPCS:
        try:
            pol = int(_rpc(u, "eth_getBalance", [addr, "latest"]) or "0x0", 16) / 1e18
            return _bal(u, USDC_E, addr), _bal(u, USDC_NATIVE, addr), pol
        except Exception:
            continue
    return None, None, None


def _load(data_dir, name, default):
    p = data_dir / f"{name}.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "data"
    addr = Path(ADDR_FILE).read_text().strip() if Path(ADDR_FILE).exists() else None

    bar = "=" * 60
    print(bar); print("  EVERLIGHT POLYMARKET  --  ACCOUNT + ACTIVITY"); print(bar)

    if addr:
        ue, un, pol = _onchain(addr)
        print(f"  wallet: {addr}")
        print(f"  polygonscan.com/address/{addr}")
        if ue is not None:
            print(f"  USDC.e (tradeable): ${ue:,.2f}    USDC native: ${un:,.2f}    POL gas: {pol:,.3f}")
            try:
                from polymarket_agent import growth
                plan = growth.harvest_plan(ue)
                print(f"  growth phase: {plan['phase']}  |  max-bet tier: ${growth.max_bet_for(ue):,.0f}")
            except Exception:
                pass

    print("  " + "-" * 56)
    openb = _load(data_dir, "paper_open_bets", [])
    closed = _load(data_dir, "closed_bets", [])
    preds = _load(data_dir, "predictions", [])
    approved = _load(data_dir, "approved_bets", [])
    markets = _load(data_dir, "active_markets", [])
    print(f"  PAPER ACTIVITY (data: {data_dir})")
    print(f"  markets scanned: {len(markets)}   predictions: {len(preds)}   "
          f"approved this cycle: {len(approved)}")
    print(f"  OPEN paper bets: {len(openb)}   RESOLVED (closed): {len(closed)}")

    # calibration stats
    try:
        from polymarket_agent.agents.postmortem import Postmortem
        pm = Postmortem()
        if closed:
            print(f"  Brier: {pm.brier_score(closed):.4f}   win-rate: {pm.win_rate(closed)*100:.0f}%   "
                  f"P&L: ${pm.total_pnl(closed)}")
            print(f"  calibration gate (need 20+ resolved, Brier<0.25, win>52%): "
                  f"{len(closed)}/20 resolved")
        else:
            print("  calibration: 0 resolved trades yet -- need qualifying bets to flow first")
    except Exception:
        pass

    print("  " + "-" * 56)
    if openb:
        print("  OPEN POSITIONS:")
        for b in openb[:8]:
            print(f"    {b.get('outcome')} ${b.get('amount_usdc')} @ {b.get('limit_price')} :: {b.get('market_id','')[:34]}")
    if preds:
        print("  LATEST EDGE CALLS:")
        for p in preds[:5]:
            print(f"    {p.get('outcome')} edge={p.get('edge',0):+.3f} conf={p.get('confidence',0):.2f}")
    if not openb and not preds:
        print("  No open positions or edge calls this cycle.")
        print("  (If 0 across cycles: signal->market coverage is thin -- populate")
        print("   smart_money.wallets and/or check Sonar, so opportunities surface.)")
    print(bar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
