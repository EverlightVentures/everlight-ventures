#!/usr/bin/env python3
"""Generate a branded HTML dashboard you can open on your phone.

Reads on-chain balance + the activity ledgers, writes a self-contained gold/dark
Everlight page to data/dashboard.html, and prints the file:// link. Auto-open:
  am start -a android.intent.action.VIEW -d file://.../dashboard.html
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ADDR_FILE = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.addr"
RPCS = ["https://polygon-bor-rpc.publicnode.com", "https://polygon.llamarpc.com", "https://1rpc.io/matic"]
USDC_E = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"


def _rpc(u, m, p):
    req = urllib.request.Request(u, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "ev/1.0"})
    return json.loads(urllib.request.urlopen(req, timeout=12).read()).get("result")


def _onchain(addr):
    for u in RPCS:
        try:
            pol = int(_rpc(u, "eth_getBalance", [addr, "latest"]) or "0x0", 16) / 1e18
            r = _rpc(u, "eth_call", [{"to": USDC_E, "data": "0x70a08231" + addr[2:].rjust(64, "0")}, "latest"])
            return (int(r, 16) if r and r != "0x" else 0) / 1e6, pol
        except Exception:
            continue
    return None, None


def _load(d, n, dv):
    try:
        return json.loads((d / f"{n}.json").read_text())
    except Exception:
        return dv


def build(data_dir: Path) -> Path:
    addr = Path(ADDR_FILE).read_text().strip() if Path(ADDR_FILE).exists() else "n/a"
    ue, pol = _onchain(addr) if addr != "n/a" else (None, None)
    openb = _load(data_dir, "paper_open_bets", []) + _load(data_dir, "candle_open_bets", [])
    closed = _load(data_dir, "closed_bets", []) + _load(data_dir, "candle_closed_bets", [])
    preds = _load(data_dir, "predictions", [])
    wins = sum(1 for b in closed if str(b.get("status")) == "won")
    from decimal import Decimal
    pnl = sum((Decimal(str(b.get("pnl_usdc", 0))) for b in closed), Decimal("0"))
    wr = (wins / len(closed) * 100) if closed else 0

    rows = "".join(
        f"<tr><td>{b.get('asset', b.get('outcome',''))}</td><td>{b.get('outcome','')}</td>"
        f"<td>${b.get('amount_usdc','')}</td><td>{b.get('price', b.get('limit_price',''))}</td></tr>"
        for b in openb[:12]) or "<tr><td colspan=4 style='color:#888'>no open positions</td></tr>"

    html = f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Everlight Polymarket</title><style>
body{{background:#0A0A0A;color:#E8E8E8;font-family:Inter,system-ui,sans-serif;margin:0;padding:18px}}
h1{{font-family:'Playfair Display',Georgia,serif;color:#D4AF37;font-size:22px;margin:0 0 4px}}
.sub{{color:#888;font-size:12px;margin-bottom:16px}}
.card{{background:#141414;border:1px solid #2a2a2a;border-radius:12px;padding:16px;margin-bottom:12px}}
.big{{font-size:30px;color:#D4AF37;font-weight:700}}
.k{{color:#999;font-size:12px}}.v{{font-size:16px}}
.grid{{display:flex;gap:18px;flex-wrap:wrap}}
table{{width:100%;border-collapse:collapse;font-size:13px}}td{{padding:6px 4px;border-bottom:1px solid #222}}
a{{color:#D4AF37}}.pos{{color:#39d353}}.neg{{color:#ff6b6b}}
</style></head><body>
<h1>EVERLIGHT VENTURES &mdash; Polymarket</h1>
<div class=sub>updated {time.strftime('%Y-%m-%d %H:%M PT', time.localtime())} &middot; PAPER mode</div>
<div class=card>
  <div class=k>tradeable balance (USDC.e)</div>
  <div class=big>${ue:,.2f}</div>
  <div class=v style='color:#888'>POL gas: {pol:,.3f}</div>
  <div class=sub><a href="https://polygonscan.com/address/{addr}">view wallet on Polygonscan &rarr;</a></div>
</div>
<div class=card><div class=grid>
  <div><div class=k>open positions</div><div class=v>{len(openb)}</div></div>
  <div><div class=k>resolved trades</div><div class=v>{len(closed)}</div></div>
  <div><div class=k>win rate</div><div class=v>{wr:.0f}%</div></div>
  <div><div class=k>net P&amp;L</div><div class="v {'pos' if pnl>=0 else 'neg'}">${pnl}</div></div>
  <div><div class=k>edge calls (cycle)</div><div class=v>{len(preds)}</div></div>
</div>
<div class=sub>calibration gate: {len(closed)}/20 resolved (need Brier&lt;0.25, win&gt;52% net of fees)</div>
</div>
<div class=card><div class=k style='margin-bottom:8px'>OPEN POSITIONS</div>
<table><tr><td class=k>market</td><td class=k>side</td><td class=k>stake</td><td class=k>price</td></tr>
{rows}</table></div>
<div class=sub>This is paper (no real money) until calibration clears + you flip live.</div>
</body></html>"""
    out = data_dir / "dashboard.html"
    out.write_text(html)
    return out


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out = build(data_dir)
    print(f"dashboard written: file://{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
