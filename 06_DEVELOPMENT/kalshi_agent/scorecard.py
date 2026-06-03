"""Scorecard -- the evidence engine. Logs every prediction the hunters make, then
settles them against ACTUAL Kalshi outcomes so we MEASURE real edge before risking
capital. Answers the only question that matters: does any lane beat the market?

record(...) appends a prediction. settle() resolves finished markets + scores them.
summary() prints hit-rate, Brier, and paper P&L by lane. Pure stdlib (runs on e5).
"""
import json
import time
import urllib.request
from pathlib import Path

LEDGER = Path(__file__).parent / "data" / "scorecard.jsonl"
K = "https://api.elections.kalshi.com/trade-api/v2"


def _get(path):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(K + path, headers={"User-Agent": "ev-score/1.0"}), timeout=15).read())


def record(lane, ticker, side, our_prob, market_price, confidence=None, reasoning="", stamp=None):
    """Log a prediction. market_price = our entry price (0..1) on the chosen side.
    Dedupe: one OPEN prediction per ticker (cron re-runs won't pile up duplicates)."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    if any(r.get("ticker") == ticker and r.get("status") == "open" for r in _rows()):
        return None
    row = {"ts": stamp or int(time.time()), "lane": lane, "ticker": ticker, "side": side,
           "our_prob": round(our_prob, 4), "entry_price": round(market_price, 4),
           "edge": round(our_prob - market_price, 4), "confidence": confidence,
           "reasoning": reasoning[:120], "status": "open"}
    with open(LEDGER, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def _rows():
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def settle():
    """Resolve open predictions whose market has settled; append scored rows."""
    rows = _rows()
    open_rows = [r for r in rows if r.get("status") == "open"]
    settled_keys = {(r["ts"], r["ticker"]) for r in rows if r.get("status") == "settled"}
    newly = 0
    for r in open_rows:
        if (r["ts"], r["ticker"]) in settled_keys:
            continue
        try:
            m = _get(f"/markets/{r['ticker']}")["market"]
        except Exception:
            continue
        if m.get("status") not in ("settled", "finalized", "determined"):
            continue
        res = m.get("result")  # 'yes' or 'no'
        if res not in ("yes", "no"):
            continue
        won = (res == r["side"])
        # paper P&L for a 1-contract bet at entry_price on our side
        pnl = (1 - r["entry_price"]) if won else -r["entry_price"]
        scored = dict(r); scored.update({"status": "settled", "result": res, "won": won,
                                         "pnl_per_contract": round(pnl, 4),
                                         "settled_ts": int(time.time())})
        with open(LEDGER, "a") as f:
            f.write(json.dumps(scored) + "\n")
        newly += 1
    return newly


def summary():
    rows = [r for r in _rows() if r.get("status") == "settled"]
    if not rows:
        return {"settled": 0, "note": "no settled predictions yet"}
    out = {}
    for lane in sorted(set(r["lane"] for r in rows)):
        lr = [r for r in rows if r["lane"] == lane]
        wins = sum(1 for r in lr if r["won"])
        brier = sum((r["our_prob"] - (1 if r["won"] else 0)) ** 2 for r in lr) / len(lr)
        pnl = sum(r["pnl_per_contract"] for r in lr)
        out[lane] = {"n": len(lr), "win_rate": round(wins / len(lr), 3),
                     "brier": round(brier, 3), "paper_pnl_per_contract": round(pnl, 3)}
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "settle":
        print("newly settled:", settle())
    print(json.dumps(summary(), indent=2))
