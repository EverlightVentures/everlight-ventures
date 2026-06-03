#!/usr/bin/env python3
"""Paper-bet settlement -- the missing link that makes calibration COMPLETE.

Each cycle the bot opens paper bets. This resolves them against REAL market
outcomes: for every open bet whose market has resolved on Polymarket, it records
win/loss + the predicted probability, moves it to closed_bets.json, credits the
paper bankroll, and appends a calibration_ledger row. The postmortem then has
real resolved trades to score (Brier, win-rate) -- the 20-trade gate to live.

Resolution source: Polymarket gamma. A resolved market has closed=true and
outcomePrices like ["1","0"] (first outcome won) / ["0","1"] (second won).

Run periodically (cron / loop): python3 -m kalshi_agent.settle_paper
"""
import json
import logging
import time
import urllib.request
from decimal import Decimal
from pathlib import Path

log = logging.getLogger("polymarket.settle")
GAMMA = "https://gamma-api.polymarket.com"


def fetch_market_resolution(market_id: str) -> tuple:
    """Return (resolved: bool, winning_outcome: str|None). Best-effort.

    Looks up the gamma market by id; if closed, the winning outcome is the one
    whose outcomePrice rounds to 1."""
    try:
        # gamma single-market endpoint is the PATH form /markets/{id}
        # (the ?id= query filter returns an empty list).
        req = urllib.request.Request(
            f"{GAMMA}/markets/{market_id}",
            headers={"User-Agent": "ev-settle/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        if isinstance(data, list):
            m = data[0] if data else None
        elif isinstance(data, dict) and "id" in data:
            m = data
        else:
            m = (data.get("data") or [None])[0] if isinstance(data, dict) else None
        if not m:
            return (False, None)
        if not (m.get("closed") or m.get("umaResolutionStatus") == "resolved"):
            return (False, None)
        outcomes = m.get("outcomes")
        prices = m.get("outcomePrices")
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if isinstance(prices, str):
            prices = json.loads(prices)
        for o, p in zip(outcomes, prices):
            if round(float(p)) == 1:
                return (True, o)
        return (True, None)  # closed but indeterminate (refund/void)
    except Exception as e:
        log.debug("resolution lookup failed for %s: %s", market_id, e)
        return (False, None)


def settle(data_dir: Path, resolver=fetch_market_resolution, now_ts=None) -> dict:
    data_dir = Path(data_dir)
    open_path = data_dir / "paper_open_bets.json"
    closed_path = data_dir / "closed_bets.json"
    state_path = data_dir / "paper_bankroll.json"
    ledger_path = data_dir / "calibration_ledger.jsonl"
    if not open_path.exists():
        return {"checked": 0, "resolved": 0, "still_open": 0}

    open_bets = json.loads(open_path.read_text())
    closed = json.loads(closed_path.read_text()) if closed_path.exists() else []
    state = json.loads(state_path.read_text()) if state_path.exists() else {"cash_usdc": 0.0}
    now = now_ts if now_ts is not None else time.time()

    still_open, resolved = [], 0
    for bet in open_bets:
        is_resolved, winner = resolver(bet["market_id"])
        if not is_resolved:
            still_open.append(bet)
            continue
        amount = Decimal(str(bet["amount_usdc"]))
        price = Decimal(str(bet["limit_price"]))
        won = winner is not None and str(winner).lower() == str(bet["outcome"]).lower()
        if winner is None:
            # void/refund -> return stake, no P&L
            pnl = Decimal("0"); shares = Decimal("0"); status = "void"
            payout = amount
        elif won:
            # shares = amount/price each pay $1 on win -> payout = amount/price
            shares = amount / price if price > 0 else Decimal("0")
            payout = shares  # $1 per share
            pnl = payout - amount
            status = "won"
        else:
            payout = Decimal("0"); pnl = -amount; status = "lost"

        bet.update({
            "status": status,
            "pnl_usdc": str(pnl),
            "outcome_resolved": winner,
            "bet_outcome": bet["outcome"],
            "settled_date": _iso(now),
        })
        closed.append(bet)
        state["cash_usdc"] = float(Decimal(str(state.get("cash_usdc", 0))) + payout)
        # calibration row for Brier/log-loss
        with open(ledger_path, "a") as f:
            f.write(json.dumps({
                "ts": now, "market_id": bet["market_id"],
                "predicted_prob": bet.get("predicted_prob", 0.0),
                "bet_outcome": bet["outcome"], "outcome_resolved": winner,
                "won": won, "pnl_usdc": str(pnl),
            }) + "\n")
        resolved += 1

    _atomic_write(open_path, json.dumps(still_open, indent=2))
    _atomic_write(closed_path, json.dumps(closed, indent=2))
    _atomic_write(state_path, json.dumps(state, indent=2))
    return {"checked": len(open_bets), "resolved": resolved, "still_open": len(still_open)}


def _atomic_write(path: Path, text: str):
    import os
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _iso(ts: float) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def main():
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "data"
    result = settle(data_dir)
    print(f"settlement: checked={result['checked']} resolved={result['resolved']} "
          f"still_open={result['still_open']}")


if __name__ == "__main__":
    main()
