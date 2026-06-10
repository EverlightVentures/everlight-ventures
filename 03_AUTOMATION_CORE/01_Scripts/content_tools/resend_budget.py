"""resend_budget -- monthly pacing + VIP reserve for every Resend send.

Why
---
Before this module the bot would blow through the Resend quota in one mass
send, leaving nothing for the critical back-and-forth with serious clients
who actually respond. This gate enforces a monthly pacing rule AND reserves a
slice for high-value reply traffic.

How it works
------------
Every email has a `category`:

  - "vip_reply"  -- replies to engaged prospects (never blocked except at 98%)
  - "nurture"    -- follow-up sequences to warm leads (soft cap at 85%)
  - "bulk"       -- cold outreach blasts (hard cap at monthly * (1 - reserve))
  - "system"     -- admin/internal alerts (counted, never blocked)

Caps come from env (see CONFIG). Defaults are conservative for Resend Free
(100/day, 3000/month) and the VIP reserve is 25% of the monthly cap.

Daily pacing: the monthly cap is divided evenly across the month. If today's
sends exceed today's share, `bulk` gets rejected but `nurture` can still go
up to 1.5x the daily share. `vip_reply` bypasses pacing entirely.

Storage
-------
  `_logs/resend_budget.jsonl`  -- append-only ledger, one line per send.

Public API
----------
    from resend_budget import check_budget, record_send, budget_status

    dec = check_budget(category="bulk", count=1)
    if dec.allowed:
        # ... actually send via branded_mailer ...
        record_send(category="bulk", message_id="abc", to="p@e.com")
    else:
        log.warning("resend budget: %s", dec.reason)
"""
from __future__ import annotations

import calendar
import json
import os
import threading
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

# ── Config from env (with sane defaults for Resend Free tier) ──────
_MONTHLY_CAP = int(os.environ.get("RESEND_MONTHLY_CAP", "3000"))
_DAILY_CAP = int(os.environ.get("RESEND_DAILY_CAP", "100"))
_VIP_RESERVE_PCT = float(os.environ.get("RESEND_VIP_RESERVE_PCT", "0.25"))
_NURTURE_SOFT_PCT = float(os.environ.get("RESEND_NURTURE_SOFT_PCT", "0.85"))

WORKSPACE_CANDIDATES = [
    Path("/mnt/sdcard/AA_MY_DRIVE"),
    Path("/home/opc/AA_MY_DRIVE"),
    Path("/home/opc"),
]


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


LEDGER = _workspace() / "_logs" / "resend_budget.jsonl"

VALID_CATEGORIES = {"vip_reply", "nurture", "bulk", "system"}
_IO_LOCK = threading.Lock()


@dataclass
class BudgetDecision:
    allowed: bool
    reason: str = ""
    sent_today: int = 0
    sent_month: int = 0
    daily_cap_effective: int = 0
    monthly_cap_effective: int = 0


# ── Ledger I/O ──────────────────────────────────────────────────────

def _append(row: dict) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with _IO_LOCK:
            with LEDGER.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, default=str) + "\n")
    except Exception:
        pass  # Budget must never crash the sender


def _iter_ledger(since: datetime) -> list[dict]:
    """Return all ledger rows on or after `since`. Skips malformed lines."""
    if not LEDGER.exists():
        return []
    out: list[dict] = []
    try:
        with LEDGER.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                ts = row.get("ts", "")
                try:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    continue
                if t >= since:
                    out.append(row)
    except Exception:
        return []
    return out


def _month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _day_start(now: datetime) -> datetime:
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _days_in_month(now: datetime) -> int:
    return calendar.monthrange(now.year, now.month)[1]


def _daily_share(now: datetime) -> int:
    """Monthly cap divided evenly across the month, floored."""
    return max(1, _MONTHLY_CAP // _days_in_month(now))


# ── Public API ──────────────────────────────────────────────────────

def budget_status() -> dict[str, Any]:
    """Return a dict describing the current state. Non-mutating, safe to call often."""
    now = datetime.now(timezone.utc)
    month_rows = _iter_ledger(_month_start(now))
    day_rows = _iter_ledger(_day_start(now))

    sent_month = sum(r.get("count", 1) for r in month_rows)
    sent_today = sum(r.get("count", 1) for r in day_rows)

    per_category_month: dict[str, int] = {}
    for r in month_rows:
        c = r.get("category", "bulk")
        per_category_month[c] = per_category_month.get(c, 0) + r.get("count", 1)

    daily_share = _daily_share(now)
    return {
        "now": now.isoformat(),
        "monthly_cap": _MONTHLY_CAP,
        "daily_cap": _DAILY_CAP,
        "vip_reserve_pct": _VIP_RESERVE_PCT,
        "sent_month": sent_month,
        "sent_today": sent_today,
        "daily_share": daily_share,
        "monthly_bulk_ceiling": int(_MONTHLY_CAP * (1 - _VIP_RESERVE_PCT)),
        "monthly_nurture_ceiling": int(_MONTHLY_CAP * _NURTURE_SOFT_PCT),
        "month_remaining": max(0, _MONTHLY_CAP - sent_month),
        "today_remaining": max(0, _DAILY_CAP - sent_today),
        "per_category_month": per_category_month,
    }


def check_budget(*, category: str = "bulk", count: int = 1) -> BudgetDecision:
    """Decide whether `count` sends in `category` are allowed right now.

    Rules (strictest first):

      - category must be one of VALID_CATEGORIES
      - vip_reply: allowed unless sent_month >= 98% of monthly cap
      - nurture:   allowed unless sent_month >= 85% of monthly cap OR
                   today exceeds 1.5x daily_share
      - bulk:      allowed unless sent_month >= (1 - vip_reserve) of monthly
                   cap OR today exceeds daily_share OR today exceeds daily_cap
      - system:    always allowed (counted but not enforced)
    """
    if category not in VALID_CATEGORIES:
        return BudgetDecision(
            allowed=False,
            reason=f"unknown_category:{category} (valid: {sorted(VALID_CATEGORIES)})",
        )

    stat = budget_status()
    sent_month = stat["sent_month"]
    sent_today = stat["sent_today"]
    daily_share = stat["daily_share"]
    monthly_cap = stat["monthly_cap"]
    daily_cap = stat["daily_cap"]

    projected_month = sent_month + count
    projected_today = sent_today + count

    if category == "system":
        return BudgetDecision(
            allowed=True, reason="system_uncapped",
            sent_today=sent_today, sent_month=sent_month,
            daily_cap_effective=daily_cap, monthly_cap_effective=monthly_cap,
        )

    if projected_today > daily_cap:
        return BudgetDecision(
            allowed=False,
            reason=f"daily_cap_exceeded ({projected_today}/{daily_cap})",
            sent_today=sent_today, sent_month=sent_month,
            daily_cap_effective=daily_cap, monthly_cap_effective=monthly_cap,
        )

    if category == "vip_reply":
        vip_ceiling = int(monthly_cap * 0.98)
        if projected_month > vip_ceiling:
            return BudgetDecision(
                allowed=False,
                reason=f"vip_ceiling_hit ({projected_month}/{vip_ceiling})",
                sent_today=sent_today, sent_month=sent_month,
                daily_cap_effective=daily_cap, monthly_cap_effective=vip_ceiling,
            )
        return BudgetDecision(
            allowed=True, reason="vip_allowed",
            sent_today=sent_today, sent_month=sent_month,
            daily_cap_effective=daily_cap, monthly_cap_effective=vip_ceiling,
        )

    if category == "nurture":
        nurture_ceiling = int(monthly_cap * _NURTURE_SOFT_PCT)
        nurture_daily = int(daily_share * 1.5)
        if projected_month > nurture_ceiling:
            return BudgetDecision(
                allowed=False,
                reason=f"nurture_monthly_hit ({projected_month}/{nurture_ceiling})",
                sent_today=sent_today, sent_month=sent_month,
                daily_cap_effective=nurture_daily, monthly_cap_effective=nurture_ceiling,
            )
        if projected_today > nurture_daily:
            return BudgetDecision(
                allowed=False,
                reason=f"nurture_daily_hit ({projected_today}/{nurture_daily})",
                sent_today=sent_today, sent_month=sent_month,
                daily_cap_effective=nurture_daily, monthly_cap_effective=nurture_ceiling,
            )
        return BudgetDecision(
            allowed=True, reason="nurture_allowed",
            sent_today=sent_today, sent_month=sent_month,
            daily_cap_effective=nurture_daily, monthly_cap_effective=nurture_ceiling,
        )

    # category == "bulk"
    bulk_monthly = int(monthly_cap * (1 - _VIP_RESERVE_PCT))
    if projected_month > bulk_monthly:
        return BudgetDecision(
            allowed=False,
            reason=f"bulk_monthly_hit ({projected_month}/{bulk_monthly}) -- vip_reserve intact",
            sent_today=sent_today, sent_month=sent_month,
            daily_cap_effective=daily_share, monthly_cap_effective=bulk_monthly,
        )
    if projected_today > daily_share:
        return BudgetDecision(
            allowed=False,
            reason=f"bulk_daily_pace ({projected_today}/{daily_share}) -- slow down to last the month",
            sent_today=sent_today, sent_month=sent_month,
            daily_cap_effective=daily_share, monthly_cap_effective=bulk_monthly,
        )
    return BudgetDecision(
        allowed=True, reason="bulk_allowed",
        sent_today=sent_today, sent_month=sent_month,
        daily_cap_effective=daily_share, monthly_cap_effective=bulk_monthly,
    )


def record_send(
    *,
    category: str = "bulk",
    message_id: str = "",
    to: str = "",
    subject: str = "",
    count: int = 1,
) -> None:
    """Append one send to the ledger. Safe to call from any thread."""
    _append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "category": category if category in VALID_CATEGORIES else "bulk",
        "message_id": message_id,
        "to": to,
        "subject": subject[:120],
        "count": count,
    })


# ── CLI ─────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="Print current budget status as JSON")
    ap.add_argument("--check", metavar="CATEGORY", help="Check if a send in CATEGORY is allowed")
    ap.add_argument("--count", type=int, default=1, help="How many to check (default 1)")
    args = ap.parse_args()

    if args.status:
        print(json.dumps(budget_status(), indent=2, default=str))
        return 0
    if args.check:
        dec = check_budget(category=args.check, count=args.count)
        print(json.dumps({
            "allowed": dec.allowed,
            "reason": dec.reason,
            "sent_today": dec.sent_today,
            "sent_month": dec.sent_month,
            "daily_cap_effective": dec.daily_cap_effective,
            "monthly_cap_effective": dec.monthly_cap_effective,
        }, indent=2))
        return 0 if dec.allowed else 2

    ap.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
