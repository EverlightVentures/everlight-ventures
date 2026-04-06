"""Fee Intelligence -- the bot's cost-awareness brain.

Three systems that work together:
1. Fee-Aware Expectancy Gate: blocks trades where fees eat the edge
2. Churn Detector: detects and penalizes rapid-fire micro-trades
3. Loss Attribution: tags every closed trade with WHY it lost (fees vs signal vs slippage)

This module feeds into the unified scorer as a modifier and into
trade_memory for root-cause learning.

The bot had 8 learning systems but ALL were blind to fees.
A lane that loses $2 from bad signal got the same penalty as a lane
that loses $2 from fees eating a profitable trade. This fixes that.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger("fee_intelligence")

# Coinbase CDE fee schedule (perps)
MAKER_FEE_BPS = -0.85   # maker rebate (negative = you get paid)
TAKER_FEE_BPS = 5.5      # taker fee
DEFAULT_FEE_PER_TRADE_USD = 0.74  # typical taker fee on 1 contract at ~$0.16
CONTRACT_SIZE = 5000.0    # XLM perp contract size


@dataclass
class FeeIntelResult:
    """Output from fee intelligence analysis."""
    # Unified scorer modifier
    score_modifier: int = 0

    # Flags
    fee_dominated: bool = False       # expected PnL < 2x fees
    churn_detected: bool = False      # too many trades/hour in this lane
    block_entry: bool = False         # hard block: fee-adjusted expectancy negative

    # Attribution for learning
    loss_attribution: str = ""        # "fees" | "signal" | "slippage" | "unlucky" | ""

    # Stats
    fee_edge_ratio: float = 0.0       # fees / expected_edge (>0.5 = fee-dominated)
    trades_per_hour: float = 0.0      # current trade rate
    lane_fee_adjusted_wr: float = 0.0 # win rate after fee deduction
    estimated_fees_usd: float = 0.0   # what this trade will cost in fees

    reasons: list[str] = field(default_factory=list)


# ── Rolling state (persists across cycles via state dict) ──────────

def _get_rolling_state(state: dict) -> dict:
    """Get or initialize the fee intelligence rolling state."""
    if "fee_intel" not in state:
        state["fee_intel"] = {
            "trades_by_hour": [],       # list of {ts, lane, pnl, fees, duration_sec}
            "lane_fee_stats": {},       # per-lane: {trades, gross_pnl, total_fees, wins, losses}
            "churn_warnings": 0,        # consecutive churn warnings
            "last_churn_check": 0,      # timestamp
        }
    return state["fee_intel"]


def record_closed_trade(
    state: dict,
    lane: str,
    pnl_usd: float,
    fees_usd: float,
    duration_sec: float,
    gross_pnl_usd: float = 0.0,
    slippage_usd: float = 0.0,
    result: str = "",
) -> str:
    """Record a closed trade for fee intelligence learning.

    Returns loss_attribution: why the trade lost (if it lost).
    """
    fi = _get_rolling_state(state)
    now = time.time()

    # Record in hourly buffer (keep last 2 hours)
    fi["trades_by_hour"].append({
        "ts": now,
        "lane": lane,
        "pnl": pnl_usd,
        "fees": fees_usd,
        "gross_pnl": gross_pnl_usd,
        "duration_sec": duration_sec,
        "slippage": slippage_usd,
    })
    # Trim to last 2 hours
    cutoff = now - 7200
    fi["trades_by_hour"] = [t for t in fi["trades_by_hour"] if t["ts"] > cutoff]

    # Update per-lane stats
    if lane not in fi["lane_fee_stats"]:
        fi["lane_fee_stats"][lane] = {
            "trades": 0, "gross_pnl": 0.0, "total_fees": 0.0,
            "wins": 0, "losses": 0, "fee_dominated_count": 0,
            "total_pnl": 0.0, "total_slippage": 0.0,
        }
    ls = fi["lane_fee_stats"][lane]
    ls["trades"] += 1
    ls["total_pnl"] += pnl_usd
    ls["gross_pnl"] += gross_pnl_usd
    ls["total_fees"] += fees_usd
    ls["total_slippage"] += slippage_usd
    if result == "win":
        ls["wins"] += 1
    elif result == "loss":
        ls["losses"] += 1
    if abs(gross_pnl_usd) < fees_usd * 2:
        ls["fee_dominated_count"] += 1

    # ── Loss attribution ──
    attribution = ""
    if result == "loss":
        if gross_pnl_usd >= 0 and pnl_usd < 0:
            # Gross was positive or flat but fees made it negative
            attribution = "fees"
        elif slippage_usd > fees_usd and pnl_usd < 0:
            # Slippage exceeded fees -- fill quality killed us
            attribution = "slippage"
        elif duration_sec < 30 and abs(pnl_usd) < 3.0:
            # Churn trade -- too fast, barely moved
            attribution = "fees"  # churn is fee-driven
        else:
            # Genuine signal failure
            attribution = "signal"
    elif result == "win" and pnl_usd < 0:
        # "Win" that lost money after fees -- mislabeled
        attribution = "fees"

    return attribution


# ── Pre-trade analysis ──────────────────────────────────────────────

def evaluate_fee_intelligence(
    *,
    state: dict,
    direction: str = "",
    entry_type: str = "",
    lane: str = "",
    expected_pnl_usd: float = 0.0,    # from EV calculation
    estimated_fees_usd: float = 0.0,   # round-trip fees for this trade
    entry_price: float = 0.0,
    trade_size: int = 1,
    atr_value: float = 0.0,
) -> FeeIntelResult:
    """Evaluate fee intelligence before entry. Returns score modifier and flags."""
    result = FeeIntelResult()
    fi = _get_rolling_state(state)
    now = time.time()

    # Estimate fees if not provided
    if estimated_fees_usd <= 0:
        # Taker both sides: 5.5 bps * 2 * notional
        notional = entry_price * CONTRACT_SIZE * trade_size
        estimated_fees_usd = notional * TAKER_FEE_BPS * 2 / 10000
    result.estimated_fees_usd = estimated_fees_usd

    # ── 1. FEE-AWARE EXPECTANCY GATE ──
    # Aggressive: block if expected PnL < 2x fees
    if expected_pnl_usd > 0 and expected_pnl_usd < estimated_fees_usd * 2:
        result.fee_dominated = True
        result.fee_edge_ratio = estimated_fees_usd / max(expected_pnl_usd, 0.01)
        result.score_modifier -= 15
        result.reasons.append(
            "FEE GATE: expected $%.2f but fees ~$%.2f (ratio %.1fx). "
            "Edge too thin to cover costs." % (expected_pnl_usd, estimated_fees_usd, result.fee_edge_ratio)
        )
    elif expected_pnl_usd <= 0:
        # Negative EV -- fees make it worse
        result.fee_dominated = True
        result.score_modifier -= 10
        result.reasons.append(
            "FEE GATE: negative EV $%.2f + fees ~$%.2f. No edge." % (expected_pnl_usd, estimated_fees_usd)
        )

    # ── 2. CHURN DETECTOR ──
    # Count trades in the last hour for this lane
    one_hour_ago = now - 3600
    recent = [t for t in fi["trades_by_hour"] if t["ts"] > one_hour_ago]
    lane_recent = [t for t in recent if t.get("lane") == lane]

    result.trades_per_hour = len(recent)

    # Aggressive: if >8 trades/hour total, something's wrong
    if len(recent) > 8:
        # Check fee-adjusted results
        recent_pnl = sum(t["pnl"] for t in recent)
        recent_fees = sum(t["fees"] for t in recent)
        recent_wins = sum(1 for t in recent if t["pnl"] > 0)
        recent_total = len(recent)
        fee_adj_wr = (recent_wins / recent_total * 100) if recent_total > 0 else 0

        if fee_adj_wr < 45:
            result.churn_detected = True
            result.score_modifier -= 20
            result.reasons.append(
                "CHURN: %d trades/hr, %.0f%% WR, $%.2f net ($%.2f fees). "
                "Slow down." % (len(recent), fee_adj_wr, recent_pnl, recent_fees)
            )
        elif recent_pnl < 0:
            result.score_modifier -= 10
            result.reasons.append(
                "HIGH FREQUENCY: %d trades/hr losing $%.2f net. Consider wider targets." % (len(recent), abs(recent_pnl))
            )

    # Per-lane churn: if this specific lane has >5 trades/hr
    if len(lane_recent) > 5:
        lane_pnl = sum(t["pnl"] for t in lane_recent)
        if lane_pnl < 0:
            result.score_modifier -= 10
            result.reasons.append(
                "LANE CHURN: %s has %d trades/hr, losing $%.2f. This lane is churning." % (lane, len(lane_recent), abs(lane_pnl))
            )

    # ── 3. ADAPTIVE LANE FEE STATS ──
    # Check this lane's historical fee-adjusted performance
    ls = fi.get("lane_fee_stats", {}).get(lane, {})
    if ls.get("trades", 0) >= 5:
        total_trades = ls["trades"]
        fee_dom_pct = (ls.get("fee_dominated_count", 0) / total_trades) * 100
        fee_adj_pnl = ls["total_pnl"]
        gross = ls["gross_pnl"]

        result.lane_fee_adjusted_wr = (ls["wins"] / total_trades * 100) if total_trades > 0 else 0

        if fee_dom_pct > 60:
            # >60% of trades in this lane are fee-dominated
            result.score_modifier -= 12
            result.reasons.append(
                "LANE FEE PROBLEM: %s has %.0f%% fee-dominated trades (%d/%d). "
                "Gross $%.2f but fees ate $%.2f." % (
                    lane, fee_dom_pct, ls["fee_dominated_count"], total_trades,
                    gross, ls["total_fees"]
                )
            )

        if fee_adj_pnl < -10 and total_trades >= 10:
            # Lane is losing money after fees over 10+ trades
            result.block_entry = True
            result.score_modifier -= 20
            result.reasons.append(
                "LANE BLOCKED: %s is -$%.2f over %d trades (%.0f%% WR after fees). "
                "Disabled until profitable." % (lane, abs(fee_adj_pnl), total_trades, result.lane_fee_adjusted_wr)
            )

    # ── 4. HARD BLOCK CHECK ──
    if result.fee_dominated and result.churn_detected:
        result.block_entry = True
        result.reasons.append("HARD BLOCK: fee-dominated + churn detected. Do not enter.")

    return result


# ── Position aggregator (Coinbase-style grouping) ──────────────────

def aggregate_positions_from_csv(trades_csv_path: str | Path) -> list[dict]:
    """Group partial fills into flat-to-flat positions like Coinbase shows.

    Each position = from net-zero to net-zero (or current open).
    Returns list of position dicts with aggregated P&L, fees, fill count.
    """
    import csv
    from datetime import datetime, timedelta, timezone

    PT = timedelta(hours=-7)
    positions = []
    current_pos = None

    with open(trades_csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            exit_price = row.get("exit_price", "")
            if not exit_price:
                # Entry-only row -- start of position
                if current_pos is None:
                    ts = row.get("entry_time") or row.get("timestamp", "")
                    try:
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        pt_dt = dt.astimezone(timezone(PT))
                        h = pt_dt.hour
                        m = pt_dt.minute
                        ampm = "am" if h < 12 else "pm"
                        h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
                        time_12hr = f"{h12}:{m:02d} {ampm}"
                        date_pt = pt_dt.strftime("%Y-%m-%d")
                    except Exception:
                        time_12hr = ""
                        date_pt = ""
                    current_pos = {
                        "date": date_pt,
                        "open_time": time_12hr,
                        "open_ts": ts,
                        "close_time": "",
                        "close_ts": "",
                        "direction": row.get("side", ""),
                        "fills": 0,
                        "entry_prices": [],
                        "exit_prices": [],
                        "gross_pnl": 0.0,
                        "total_fees": 0.0,
                        "net_pnl": 0.0,
                        "total_duration_sec": 0.0,
                        "result": "",
                    }
                continue

            # Completed trade row
            pnl = float(row.get("pnl_usd") or 0)
            fees = float(row.get("total_fees_usd") or 0)
            entry_p = row.get("entry_price", "")
            exit_p = row.get("exit_price", "")
            side = row.get("side", "")
            dur = row.get("duration_min", "")

            if current_pos is None:
                # No open position -- this fill IS a full position
                ts = row.get("entry_time") or row.get("timestamp", "")
                exit_ts = row.get("exit_time", "")
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    pt_dt = dt.astimezone(timezone(PT))
                    h = pt_dt.hour
                    m = pt_dt.minute
                    ampm = "am" if h < 12 else "pm"
                    h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
                    open_12hr = f"{h12}:{m:02d} {ampm}"
                    date_pt = pt_dt.strftime("%Y-%m-%d")
                except Exception:
                    open_12hr = ""
                    date_pt = ""

                try:
                    edt = datetime.fromisoformat(exit_ts.replace("Z", "+00:00"))
                    ept = edt.astimezone(timezone(PT))
                    eh = ept.hour
                    em = ept.minute
                    eampm = "am" if eh < 12 else "pm"
                    eh12 = eh if 1 <= eh <= 12 else (eh - 12 if eh > 12 else 12)
                    close_12hr = f"{eh12}:{em:02d} {eampm}"
                except Exception:
                    close_12hr = ""

                current_pos = {
                    "date": date_pt,
                    "open_time": open_12hr,
                    "open_ts": ts,
                    "close_time": close_12hr,
                    "close_ts": exit_ts,
                    "direction": side,
                    "fills": 0,
                    "entry_prices": [],
                    "exit_prices": [],
                    "gross_pnl": 0.0,
                    "total_fees": 0.0,
                    "net_pnl": 0.0,
                    "total_duration_sec": 0.0,
                    "result": "",
                }

            # Add this fill to current position
            current_pos["fills"] += 1
            current_pos["net_pnl"] += pnl
            current_pos["total_fees"] += fees
            if entry_p:
                current_pos["entry_prices"].append(float(entry_p))
            if exit_p:
                current_pos["exit_prices"].append(float(exit_p))
            if dur:
                current_pos["total_duration_sec"] += float(dur) * 60

            # Update close time
            exit_ts = row.get("exit_time", "")
            if exit_ts:
                try:
                    edt = datetime.fromisoformat(exit_ts.replace("Z", "+00:00"))
                    ept = edt.astimezone(timezone(PT))
                    eh = ept.hour
                    em = ept.minute
                    eampm = "am" if eh < 12 else "pm"
                    eh12 = eh if 1 <= eh <= 12 else (eh - 12 if eh > 12 else 12)
                    current_pos["close_time"] = f"{eh12}:{em:02d} {eampm}"
                    current_pos["close_ts"] = exit_ts
                except Exception:
                    pass

            # Check if position is closed (each trade row = 1 fill that closes)
            # In XLM perps with size=1, each row IS a complete position
            current_pos["gross_pnl"] = current_pos["net_pnl"] + current_pos["total_fees"]
            current_pos["result"] = "win" if current_pos["net_pnl"] > 0 else "loss"

            # Compute averages
            if current_pos["entry_prices"]:
                current_pos["avg_entry"] = sum(current_pos["entry_prices"]) / len(current_pos["entry_prices"])
            if current_pos["exit_prices"]:
                current_pos["avg_exit"] = sum(current_pos["exit_prices"]) / len(current_pos["exit_prices"])

            # Fee attribution
            if current_pos["gross_pnl"] >= 0 and current_pos["net_pnl"] < 0:
                current_pos["loss_cause"] = "fees"
            elif current_pos["gross_pnl"] < 0:
                current_pos["loss_cause"] = "signal"
            else:
                current_pos["loss_cause"] = ""

            # Close this position
            positions.append(current_pos)
            current_pos = None

    # If there's an open position at the end
    if current_pos is not None and current_pos["fills"] > 0:
        current_pos["result"] = "open"
        positions.append(current_pos)

    return positions


def get_fee_intelligence_summary(state: dict) -> dict:
    """Get a summary of fee intelligence state for the dashboard."""
    fi = _get_rolling_state(state)
    now = time.time()
    one_hour = [t for t in fi["trades_by_hour"] if t["ts"] > now - 3600]

    # Per-lane breakdown
    lanes = {}
    for lane, ls in fi.get("lane_fee_stats", {}).items():
        if ls["trades"] < 3:
            continue
        total = ls["trades"]
        wr = (ls["wins"] / total * 100) if total > 0 else 0
        fee_dom_pct = (ls.get("fee_dominated_count", 0) / total * 100) if total > 0 else 0
        lanes[lane] = {
            "trades": total,
            "win_rate": round(wr, 1),
            "total_pnl": round(ls["total_pnl"], 2),
            "total_fees": round(ls["total_fees"], 2),
            "fee_dominated_pct": round(fee_dom_pct, 1),
            "avg_pnl_per_trade": round(ls["total_pnl"] / total, 2),
            "healthy": fee_dom_pct < 40 and ls["total_pnl"] > 0,
        }

    return {
        "trades_last_hour": len(one_hour),
        "pnl_last_hour": round(sum(t["pnl"] for t in one_hour), 2),
        "fees_last_hour": round(sum(t["fees"] for t in one_hour), 2),
        "churn_warnings": fi.get("churn_warnings", 0),
        "lanes": lanes,
    }
