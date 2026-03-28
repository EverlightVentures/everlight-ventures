#!/usr/bin/env python3
"""Backtest v2: deduplicated signals, compare blocked longs vs actual shorts taken."""
import json
from datetime import datetime, timedelta, timezone

decisions = []
with open("/home/opc/xlm_bot/logs/decisions.jsonl") as f:
    for line in f:
        try:
            decisions.append(json.loads(line.strip()))
        except:
            continue

def parse_ts(s):
    s = s.replace("+00:00", "").replace("Z", "")
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

# Build price timeline (deduplicate to ~1 per minute)
prices = []
last_min = ""
for d in decisions:
    if d.get("reason") != "open_position_tick":
        continue
    ts = d["timestamp"][:16]
    if ts != last_min:
        p = d.get("spot_price") or d.get("price")
        prices.append((parse_ts(d["timestamp"]), p))
        last_min = ts

def find_price(target, tol_sec=600):
    best_p, best_d = None, 999999
    for ts, p in prices:
        d = abs((ts - target).total_seconds())
        if d < best_d:
            best_d = d
            best_p = p
    return best_p if best_d < tol_sec else None

# Deduplicate blocks: merge blocks within 5 min of each other
raw_blocks = [d for d in decisions if "htf" in d.get("reason","") and "blocked" in d.get("reason","")]
deduped_blocks = []
last_block_time = None
for b in raw_blocks:
    bdt = parse_ts(b["timestamp"])
    if last_block_time is None or (bdt - last_block_time).total_seconds() > 300:
        deduped_blocks.append(b)
        last_block_time = bdt

# Find actual short entries (position changes)
short_entries = []
prev_state = None
for d in decisions:
    if d.get("reason") != "open_position_tick":
        continue
    if d.get("direction") == "short" and d.get("entry_time"):
        et = d["entry_time"]
        if et != prev_state:
            short_entries.append(d)
            prev_state = et

print(f"Raw blocks: {len(raw_blocks)}")
print(f"Deduplicated blocks (unique signals): {len(deduped_blocks)}")
print(f"Actual short entries taken: {len(short_entries)}")
print(f"Price samples: {len(prices)}")
print()

# === Analyze deduped blocked longs ===
print("=" * 60)
print("BLOCKED LONGS (deduplicated) -- what if we took them?")
print("=" * 60)
for hold_min in [15, 30, 60, 120]:
    label = {15: "15m", 30: "30m", 60: "1h", 120: "2h"}[hold_min]
    by_rsi = {}
    for b in deduped_blocks:
        bdt = parse_ts(b["timestamp"])
        ep = find_price(bdt)
        if ep is None:
            continue
        xp = find_price(bdt + timedelta(minutes=hold_min))
        if xp is None:
            continue
        rsi = b.get("rsi_1h", 0)
        lo = int(rsi // 5) * 5
        bk = f"{lo}-{lo+5}"
        pnl = (xp - ep) * 5000
        if bk not in by_rsi:
            by_rsi[bk] = {"w": 0, "l": 0, "pnl": 0.0, "n": 0, "best": -9999, "worst": 9999}
        by_rsi[bk]["n"] += 1
        by_rsi[bk]["pnl"] += pnl
        if pnl > 0:
            by_rsi[bk]["w"] += 1
        else:
            by_rsi[bk]["l"] += 1
        by_rsi[bk]["best"] = max(by_rsi[bk]["best"], pnl)
        by_rsi[bk]["worst"] = min(by_rsi[bk]["worst"], pnl)

    print(f"\n  --- {label} hold ---")
    tw, tl, tp = 0, 0, 0.0
    for bk in sorted(by_rsi.keys()):
        v = by_rsi[bk]
        total = v["w"] + v["l"]
        wr = v["w"] / total * 100 if total else 0
        avg = v["pnl"] / v["n"] if v["n"] else 0
        tw += v["w"]
        tl += v["l"]
        tp += v["pnl"]
        print(f"  RSI {bk:>5}: {v['w']:>2}W/{v['l']:>2}L  WR={wr:>4.0f}%  PnL=${v['pnl']:>7.2f}  avg=${avg:>6.2f}  best=${v['best']:>6.2f}  worst=${v['worst']:>7.2f}")
    total = tw + tl
    wr = tw / total * 100 if total else 0
    print(f"  TOTAL:    {tw:>2}W/{tl:>2}L  WR={wr:>4.0f}%  PnL=${tp:>7.2f}")

# === Analyze actual shorts taken ===
print()
print("=" * 60)
print("ACTUAL SHORTS TAKEN -- how did they do?")
print("=" * 60)
for se in short_entries:
    entry_p = se.get("entry_price", 0)
    entry_t = parse_ts(se["entry_time"])
    pnl_live = se.get("pnl_usd_live", 0)
    rsi = se.get("adx_15m", 0)  # we don't have rsi in tick, use what we have
    mins_in = se.get("time_in_trade_min", 0)
    print(f"  {se['entry_time'][:16]} | entry=${entry_p:.5f} | pnl=${pnl_live:>7.2f} | {mins_in:.0f}min in")

# === The key question: what SHOULD the bot do at each RSI level? ===
print()
print("=" * 60)
print("OPTIMAL STRATEGY BY RSI (what direction wins at each level?)")
print("=" * 60)
for hold_min in [30, 60]:
    label = {30: "30m", 60: "1h"}[hold_min]
    print(f"\n  --- {label} hold ---")
    # Check both long AND short PnL at each price point where blocks happened
    by_rsi = {}
    for b in deduped_blocks:
        bdt = parse_ts(b["timestamp"])
        ep = find_price(bdt)
        if ep is None:
            continue
        xp = find_price(bdt + timedelta(minutes=hold_min))
        if xp is None:
            continue
        rsi = b.get("rsi_1h", 0)
        lo = int(rsi // 5) * 5
        bk = f"{lo}-{lo+5}"
        long_pnl = (xp - ep) * 5000
        short_pnl = (ep - xp) * 5000
        if bk not in by_rsi:
            by_rsi[bk] = {"long_pnl": 0.0, "short_pnl": 0.0, "long_w": 0, "short_w": 0, "n": 0}
        by_rsi[bk]["n"] += 1
        by_rsi[bk]["long_pnl"] += long_pnl
        by_rsi[bk]["short_pnl"] += short_pnl
        if long_pnl > 0:
            by_rsi[bk]["long_w"] += 1
        if short_pnl > 0:
            by_rsi[bk]["short_w"] += 1

    for bk in sorted(by_rsi.keys()):
        v = by_rsi[bk]
        long_wr = v["long_w"] / v["n"] * 100 if v["n"] else 0
        short_wr = v["short_w"] / v["n"] * 100 if v["n"] else 0
        winner = "LONG" if v["long_pnl"] > v["short_pnl"] else "SHORT" if v["short_pnl"] > 0 else "FLAT"
        print(f"  RSI {bk:>5}: LONG WR={long_wr:>4.0f}% PnL=${v['long_pnl']:>7.2f} | SHORT WR={short_wr:>4.0f}% PnL=${v['short_pnl']:>7.2f} | BEST={winner}")
