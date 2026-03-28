#!/usr/bin/env python3
"""Analyze all closed trades from decisions.jsonl with full PnL breakdown."""
import json

entries = {}
exits = []
with open("/home/opc/xlm_bot/logs/decisions.jsonl") as f:
    for line in f:
        try:
            d = json.loads(line.strip())
        except Exception:
            continue
        r = d.get("reason", "")
        if r == "open_position_tick":
            et = d.get("entry_time", "")
            if et and et not in entries:
                entries[et] = {
                    "entry_price": d.get("entry_price", 0),
                    "direction": d.get("direction", ""),
                    "entry_time": et,
                    "max_unrealized": 0,
                }
            if et in entries:
                cur_max = float(d.get("max_unrealized_usd") or 0)
                if cur_max > entries[et]["max_unrealized"]:
                    entries[et]["max_unrealized"] = cur_max
                entries[et]["last_pnl"] = float(d.get("pnl_usd_live") or 0)
                entries[et]["last_price"] = d.get("price", 0)
                entries[et]["bars"] = d.get("bars_since_entry", 0)
        if r == "exit_order_sent":
            exits.append(d)

print("=== FULL TRADE HISTORY ===")
print(f"Total closed: {len(exits)}")
print()

total_pnl = 0.0
total_left = 0.0
total_fees = 0.0

for i, ex in enumerate(exits):
    et = ex.get("entry_time", "")
    ed = entries.get(et, {})
    ep = ed.get("entry_price", 0)
    d = ed.get("direction", "?")
    max_u = ed.get("max_unrealized", 0)
    bars = ed.get("bars", 0)
    er = ex.get("exit_reason", "?")
    held = ex.get("time_in_trade_min", 0)

    ci = ex.get("close_info", {})
    fill = ci.get("fill", {}) if isinstance(ci, dict) else {}
    fill_price = float(fill.get("average_filled_price", 0) or 0)
    fees = float(fill.get("total_fees", 0) or 0)
    total_fees += fees

    if fill_price > 0 and ep > 0:
        if d == "short":
            gross = (ep - fill_price) * 5000
        else:
            gross = (fill_price - ep) * 5000
        net = gross - fees
    else:
        net = ed.get("last_pnl", 0) - 1.50
        gross = net + 1.50

    total_pnl += net
    left = max(0, max_u - max(0, net))
    total_left += left

    tag = "WIN" if net > 0.50 else ("SCRATCH" if net > -2 else "LOSS")
    hrs = held / 60.0

    print(f"Trade {i+1}: {d.upper()} @ ${ep:.5f}")
    print(f"  Exit: {er} after {hrs:.1f}hrs ({bars} bars)")
    print(f"  Gross: ${gross:.2f} | Fees: ${fees:.2f} | Net: ${net:.2f} | {tag}")
    print(f"  Max unrealized: ${max_u:.2f} | Left on table: ${left:.2f}")
    if left > 3:
        print(f"  ** GAVE BACK ${left:.2f} of profit **")
    print()

print("=" * 60)
print(f"Total net PnL:      ${total_pnl:.2f}")
print(f"Total fees paid:    ${total_fees:.2f}")
print(f"Total left on table: ${total_left:.2f}")
print(f"Avg net per trade:  ${total_pnl / max(1, len(exits)):.2f}")
print()

# What could have been
print("=== WHAT COULD HAVE BEEN ===")
print(f"If we captured max unrealized on every trade:")
potential = sum(entries[ex.get('entry_time','')].get('max_unrealized', 0) for ex in exits if ex.get('entry_time','') in entries)
print(f"  Potential PnL: ${potential:.2f}")
print(f"  Actual PnL:    ${total_pnl:.2f}")
print(f"  Capture rate:  {(total_pnl / potential * 100) if potential > 0 else 0:.0f}%")
print()

# Diagnose each loss
print("=== EXIT REASON BREAKDOWN ===")
by_reason = {}
for ex in exits:
    er = ex.get("exit_reason", "?")
    et = ex.get("entry_time", "")
    ed = entries.get(et, {})
    ep = ed.get("entry_price", 0)
    d = ed.get("direction", "?")
    ci = ex.get("close_info", {})
    fill = ci.get("fill", {}) if isinstance(ci, dict) else {}
    fill_price = float(fill.get("average_filled_price", 0) or 0)
    fees = float(fill.get("total_fees", 0) or 0)
    if fill_price > 0 and ep > 0:
        if d == "short":
            net = (ep - fill_price) * 5000 - fees
        else:
            net = (fill_price - ep) * 5000 - fees
    else:
        net = ed.get("last_pnl", 0) - 1.50
    if er not in by_reason:
        by_reason[er] = {"count": 0, "pnl": 0.0}
    by_reason[er]["count"] += 1
    by_reason[er]["pnl"] += net

for er, v in sorted(by_reason.items(), key=lambda x: x[1]["pnl"]):
    print(f"  {er:<25}: {v['count']}x | ${v['pnl']:.2f}")

# Current position
last_tick = None
with open("/home/opc/xlm_bot/logs/decisions.jsonl") as f:
    for line in f:
        try:
            d = json.loads(line.strip())
        except Exception:
            continue
        if d.get("reason") == "open_position_tick":
            last_tick = d

print()
if last_tick and last_tick.get("entry_price"):
    p = last_tick
    print(f"CURRENT: {p.get('direction','?')} @ ${p.get('entry_price',0):.5f}")
    print(f"  PnL: ${float(p.get('pnl_usd_live',0)):.2f}")
    print(f"  Max unrealized: ${float(p.get('max_unrealized_usd',0)):.2f}")
    print(f"  Bars: {p.get('bars_since_entry',0)} | Held: {float(p.get('time_in_trade_min',0))/60:.1f}hrs")
else:
    print("No open position")
