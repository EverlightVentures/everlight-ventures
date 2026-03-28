#!/usr/bin/env python3
"""Backtest: what if we took every HTF-blocked long?"""
import json
from datetime import datetime, timedelta, timezone

blocks = []
prices = []
last_ts = ""

with open("/home/opc/xlm_bot/logs/decisions.jsonl") as f:
    for line in f:
        try:
            d = json.loads(line.strip())
        except:
            continue
        r = d.get("reason", "")
        if "htf" in r and "blocked" in r:
            blocks.append(d)
        if r == "open_position_tick":
            ts = d["timestamp"][:16]
            if ts != last_ts:
                prices.append((d["timestamp"], d.get("spot_price") or d.get("price")))
                last_ts = ts


def parse_ts(s):
    s = s.replace("+00:00", "").replace("Z", "")
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def find_price(target, plist, tol=600):
    best_p, best_d = None, 999999
    for ts, p in plist:
        d = abs((parse_ts(ts) - target).total_seconds())
        if d < best_d:
            best_d = d
            best_p = p
    return best_p if best_d < tol else None


print(f"Blocks: {len(blocks)} | Price samples: {len(prices)}")
print()

# Collect results by (rsi_bucket, hold_minutes)
buckets = {}
for b in blocks:
    bdt = parse_ts(b["timestamp"])
    ep = find_price(bdt, prices)
    if ep is None:
        continue
    rsi = b.get("rsi_1h", 0)
    lo = int(rsi // 5) * 5
    bk = f"{lo}-{lo + 5}"

    for mins in [15, 30, 60, 120]:
        xp = find_price(bdt + timedelta(minutes=mins), prices)
        if xp is None:
            continue
        pnl = (xp - ep) * 5000  # long on 1 contract = 5000 XLM
        key = (bk, mins)
        if key not in buckets:
            buckets[key] = {"wins": 0, "losses": 0, "pnl": 0.0, "n": 0}
        buckets[key]["n"] += 1
        buckets[key]["pnl"] += pnl
        if pnl > 0:
            buckets[key]["wins"] += 1
        else:
            buckets[key]["losses"] += 1

for hold in [15, 30, 60, 120]:
    label = {15: "15m", 30: "30m", 60: "1h", 120: "2h"}[hold]
    print(f"=== {label} HOLD ===")
    tw, tl, tp = 0, 0, 0.0
    rsi_keys = sorted(set(k[0] for k in buckets.keys()))
    for bk in rsi_keys:
        key = (bk, hold)
        if key not in buckets:
            continue
        v = buckets[key]
        total = v["wins"] + v["losses"]
        wr = v["wins"] / total * 100 if total else 0
        avg = v["pnl"] / v["n"] if v["n"] else 0
        tw += v["wins"]
        tl += v["losses"]
        tp += v["pnl"]
        print(f"  RSI {bk:>5}: {v['wins']:>3}W/{v['losses']:>3}L  WR={wr:>4.0f}%  PnL=${v['pnl']:>8.2f}  avg=${avg:>6.2f}")
    total = tw + tl
    wr = tw / total * 100 if total else 0
    print(f"  TOTAL:    {tw:>3}W/{tl:>3}L  WR={wr:>4.0f}%  PnL=${tp:>8.2f}")
    print()

# Now: what if we ONLY took longs when RSI < 25 (exhaustion zone)?
print("=== EXHAUSTION-ONLY LONGS (RSI < 25) ===")
for hold in [15, 30, 60, 120]:
    label = {15: "15m", 30: "30m", 60: "1h", 120: "2h"}[hold]
    tw, tl, tp = 0, 0, 0.0
    for bk in rsi_keys:
        hi = int(bk.split("-")[1])
        if hi > 25:
            continue
        key = (bk, hold)
        if key not in buckets:
            continue
        v = buckets[key]
        tw += v["wins"]
        tl += v["losses"]
        tp += v["pnl"]
    total = tw + tl
    wr = tw / total * 100 if total else 0
    print(f"  {label}: {tw}W/{tl}L  WR={wr:.0f}%  PnL=${tp:.2f}")
