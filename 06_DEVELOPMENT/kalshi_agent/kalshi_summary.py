#!/usr/bin/env python3
"""kalshi_summary.py -- compact JSON summary of the Kalshi account for the Everlight
Command Center. Runs on e5 (creds + live data there); the band watchdog mirrors the
output JSON to the phone, where build_command_center.py folds it into ev_data.js.
Read-only (balance/fills/settlements + local engine files).

    PYTHONPATH=/home/ubuntu/AA_MY_DRIVE/06_DEVELOPMENT python3 -m kalshi_agent.kalshi_summary
"""
import json
import time
from collections import defaultdict
from pathlib import Path

from kalshi_agent.execution.kalshi_exec import from_creds

HERE = Path(__file__).parent
FUNDED = 116.26


def sport_of(t):
    t = (t or "").upper()
    for pre, sp in (("KXNBA", "nba"), ("KXMLB", "mlb"), ("KXNHL", "nhl"), ("KXWC", "wc"),
                    ("KXUFC", "ufc"), ("KXNFL", "nfl"), ("KXWNBA", "wnba")):
        if t.startswith(pre):
            return sp
    return "other"


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def build(creds=None):
    k = from_creds(creds) if creds else from_creds()
    try:
        bal = k.get_balance()
    except Exception:
        bal = None
    fills = k._request("GET", "/portfolio/fills").get("fills", [])
    setls = {s["ticker"]: s for s in k._request("GET", "/portfolio/settlements").get("settlements", [])}
    agg = defaultdict(lambda: {"c": 0.0, "cost": 0.0, "side": None})
    for f in fills:
        tk, sd = f.get("ticker"), f.get("side")
        c = float(f.get("count_fp") or 0)
        px = float(f.get("yes_price_dollars") or 0) if sd == "yes" else float(f.get("no_price_dollars") or 0)
        sgn = 1 if f.get("action") == "buy" else -1
        a = agg[tk]; a["c"] += sgn * c; a["cost"] += sgn * c * px
        if a["side"] is None:
            a["side"] = sd
    settled, openpos, w, l, open_cost = [], [], 0, 0, 0.0
    for tk, a in agg.items():
        if abs(a["c"]) < 0.01:
            continue
        if tk in setls:
            s = setls[tk]; won = s.get("market_result") == a["side"]
            pnl = (a["c"] if won else 0.0) - a["cost"]
            w += 1 if won else 0; l += 0 if won else 1
            settled.append({"when": (s.get("settled_time") or "")[:16], "ticker": tk, "sport": sport_of(tk),
                            "side": a["side"], "won": won, "pnl": round(pnl, 2)})
        else:
            open_cost += a["cost"]
            openpos.append({"ticker": tk, "sport": sport_of(tk), "side": a["side"], "ct": round(a["c"]),
                            "cost": round(a["cost"], 2), "avg": round(a["cost"] / a["c"], 3) if a["c"] else 0})
    settled.sort(key=lambda x: x["when"])
    total = w + l
    wr = (w / total) if total else None
    # profit FACTOR (Rich's 2:1 target) = gross wins / gross losses; + avg win vs avg loss
    wins = [r["pnl"] for r in settled if r["won"]]
    losses = [-r["pnl"] for r in settled if not r["won"]]
    gw, gl = sum(wins), sum(losses)
    pf = round(gw / gl, 2) if gl > 0 else None
    avg_win = round(gw / len(wins), 2) if wins else None
    avg_loss = round(gl / len(losses), 2) if losses else None
    u = _json(HERE / "data" / "upcoming_edges.json") or {}
    memos = []
    try:
        memos = [json.loads(x) for x in (HERE / "data" / "watchdog_memos.jsonl").read_text().splitlines() if x.strip()]
    except Exception:
        pass
    st = _json(HERE / "data" / "watchdog_state.json") or {}
    now = time.time()
    brakes = {x: v for x, v in st.get("quarantine", {}).items() if v.get("until", 0) > now}
    gas = {x: v for x, v in st.get("lean_in", {}).items() if v.get("until", 0) > now}
    equity = (bal or 0) + open_cost          # cash + open positions at cost (conservative)
    pnl = equity - FUNDED
    return {"balance": round(bal, 2) if bal is not None else None, "funded": FUNDED,
            "equity": round(equity, 2), "pnl": round(pnl, 2), "pnl_pct": round(pnl / FUNDED * 100, 1),
            "win_rate": round(wr, 4) if wr is not None else None, "w": w, "l": l,
            "profit_factor": pf, "avg_win": avg_win, "avg_loss": avg_loss,
            "open": openpos, "recent": settled[-12:][::-1], "upcoming": u.get("edges", [])[:8],
            "memo": memos[-1] if memos else None, "brakes": brakes, "gas": gas, "ts": int(time.time())}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--creds", default=None)
    print(json.dumps(build(ap.parse_args().creds)))
