#!/usr/bin/env python3
"""
pnl_watch -- REAL-money Kalshi winnings watcher.

Pulls actual account settlements + balance + open positions via the authed
client (execution.kalshi_exec), categorizes every settlement by market family,
maintains a dedup ledger, and sends Rich a Telegram digest.

Distinct from scorecard.py (paper prediction scoring): this watches the MONEY.

Ledger: data/pnl_ledger.jsonl   Baseline: data/pnl_baseline.json
Cron (e5): 10 15,3 * * *  (after the 15:00 scorecard settle)

Env for the digest: TELEGRAM_BOT_TOKEN + PNL_TG_CHAT (Rich's DM chat id).
Falls back to stdout-only when unset.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
LEDGER = HERE / "data" / "pnl_ledger.jsonl"
BASELINE = HERE / "data" / "pnl_baseline.json"
DEPOSIT_BASELINE = 116.26  # memory: total funded 2026-06-02

CATEGORIES = [
    ("sports", ["NBA", "MLB", "NHL", "NFL", "UFC", "MMA", "PGA", "GOLF", "TENNIS",
                "WTA", "ATP", "SOCCER", "EPL", "UCL", "MLS", "NCAA", "F1", "NASCAR",
                "SERIEA", "LALIGA", "BUNDES", "FIFA", "WNBA", "BOXING"]),
    ("crypto", ["BTC", "ETH", "SOL", "DOGE", "XRP", "CRYPTO"]),
    ("politics", ["PRES", "POTUS", "SENATE", "HOUSE", "GOV", "ELECT", "PRIMARY",
                  "IMPEACH", "CABINET", "SCOTUS"]),
    ("econ", ["FED", "CPI", "GDP", "JOBS", "NFP", "RATE", "INFLATION", "RECESSION",
              "SP500", "NASDAQ", "TREASURY"]),
    ("entertainment", ["OSCAR", "GRAMMY", "EMMY", "ROTTEN", "BOXOFFICE", "ALBUM",
                       "SPOTIFY", "MOVIE", "TV", "GTA"]),
    ("weather", ["HIGHTEMP", "LOWTEMP", "RAIN", "SNOW", "HURRICANE", "TORNADO"]),
]


def categorize(ticker: str) -> str:
    t = (ticker or "").upper()
    for cat, keys in CATEGORIES:
        if any(k in t for k in keys):
            return cat
    return "other"


def _rows():
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]


def _cents(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def pull(client):
    """Fetch settlements (paginated) -> list of normalized rows."""
    out, cursor = [], None
    for _ in range(10):
        path = "/portfolio/settlements?limit=100" + (f"&cursor={cursor}" if cursor else "")
        resp = client._request("GET", path)
        for s in resp.get("settlements", []):
            cost = _cents(s.get("yes_total_cost")) + _cents(s.get("no_total_cost"))
            rev = _cents(s.get("revenue"))
            out.append({
                "key": f"{s.get('ticker')}|{s.get('settled_time')}",
                "ticker": s.get("ticker"),
                "category": categorize(s.get("ticker")),
                "result": s.get("market_result"),
                "cost_usd": round(cost / 100, 2),
                "revenue_usd": round(rev / 100, 2),
                "pnl_usd": round((rev - cost) / 100, 2),
                "won": rev > cost,
                "settled_time": s.get("settled_time"),
                "raw": s,
            })
        cursor = resp.get("cursor")
        if not cursor:
            break
    return out


def update_ledger(settlements):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    seen = {r["key"] for r in _rows()}
    new = [s for s in settlements if s["key"] not in seen]
    with open(LEDGER, "a") as f:
        for s in new:
            f.write(json.dumps(s) + "\n")
    return new


def digest(client, new_rows):
    rows = _rows()
    bal = client.get_balance()
    positions = client.get_positions()
    open_n = sum(1 for p in positions if p.get("position", 0) != 0)
    exposure = round(sum(abs(_cents(p.get("market_exposure"))) for p in positions) / 100, 2)

    if not BASELINE.exists():
        BASELINE.write_text(json.dumps({"deposit": DEPOSIT_BASELINE}))
    base = json.loads(BASELINE.read_text()).get("deposit", DEPOSIT_BASELINE)

    total = round(sum(r["pnl_usd"] for r in rows), 2)
    wins = sum(1 for r in rows if r["won"])
    by_cat = {}
    for r in rows:
        c = by_cat.setdefault(r["category"], {"n": 0, "pnl": 0.0, "w": 0})
        c["n"] += 1
        c["pnl"] = round(c["pnl"] + r["pnl_usd"], 2)
        c["w"] += 1 if r["won"] else 0

    lines = ["\U0001F3B0 KALSHI WINNINGS REPORT"]
    if new_rows:
        lines.append(f"\nNEW since last check ({len(new_rows)}):")
        for r in new_rows[:8]:
            emo = "✅" if r["won"] else "❌"
            lines.append(f"{emo} {r['ticker']} [{r['category']}] {r['pnl_usd']:+.2f}")
    lines.append(f"\nRecord: {wins}-{len(rows) - wins} | settled P&L: {total:+.2f}")
    for cat, c in sorted(by_cat.items(), key=lambda kv: -kv[1]["pnl"]):
        lines.append(f"  {cat}: {c['w']}-{c['n'] - c['w']}  {c['pnl']:+.2f}")
    lines.append(f"\nBalance: ${bal:.2f} (vs ${base:.2f} deposited -> {bal - base:+.2f})")
    lines.append(f"Open: {open_n} positions, ~${exposure:.2f} at risk")
    lines.append("Note: balance moves before settlement; open bets not counted as P&L until they land.")
    return "\n".join(lines)


def send_telegram(text):
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("PNL_TG_CHAT", "")
    if not tok or not chat:
        return False
    body = json.dumps({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage",
                                 body, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=20)).get("ok", False)


def main():
    from kalshi_agent.execution.kalshi_exec import from_creds
    client = from_creds()
    new = update_ledger(pull(client))
    text = digest(client, new)
    print(text)
    # DM only when something settled, or on the morning run (15:xx UTC)
    if new or time.gmtime().tm_hour == 15:
        sent = send_telegram(text)
        print(f"[telegram sent: {sent}]")


if __name__ == "__main__":
    main()
