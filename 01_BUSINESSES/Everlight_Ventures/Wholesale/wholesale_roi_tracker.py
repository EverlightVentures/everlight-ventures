"""wholesale_roi_tracker -- channel-by-channel ROI for the wholesale stack.

Pulls live data from:
  - Django InvestorBuyer / PropertyLead / BrokerMatch / Deal / OutreachSequence
  - direct_mail.jsonl ledger (Lob sends)
  - resend_budget.jsonl ledger (email sends)
  - jv_partnerships/pitched.jsonl
  - callback_queue.jsonl

Outputs a structured dict that the Marcus daily briefing AND a future
dashboard view can both consume.

Public API
----------
    from wholesale_roi_tracker import compute_funnel, render_text_summary

    f = compute_funnel(days=30)
    print(render_text_summary(f))

CLI
---
    python3 wholesale_roi_tracker.py --days 7
    python3 wholesale_roi_tracker.py --days 30 --json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("wholesale_roi_tracker")

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


# Cost-per-touch defaults (tweak via env or config)
COST_EMAIL = float(os.environ.get("ROI_COST_EMAIL_USD", "0.001"))         # negligible
COST_MAIL = float(os.environ.get("ROI_COST_MAIL_USD", "0.85"))            # yellow letter
COST_VA_HOUR = float(os.environ.get("ROI_COST_VA_HOUR_USD", "5.0"))       # phone callbacks
COST_PER_DIAL_MIN = float(os.environ.get("ROI_COST_PER_DIAL_MIN", "0.08"))  # = $5/hr / 60 min

# Industry conversion benchmarks for sanity-checking
BENCHMARK_REPLY_RATE = {
    "email": 0.001,   # cold email to property owners
    "mail": 0.015,    # yellow letter response rate
    "phone": 0.30,    # outbound to warm replies
}


def _bootstrap_django() -> bool:
    project_dir = _workspace() / "09_DASHBOARD" / "hive_dashboard"
    try:
        if str(project_dir) not in sys.path:
            sys.path.insert(0, str(project_dir))
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        import django
        django.setup()
        return True
    except Exception as exc:
        log.warning("Django bootstrap failed: %s", exc)
        return False


def _count_jsonl(path: Path, since: datetime, ts_field: str = "ts", filter_fn=None) -> int:
    if not path.exists():
        return 0
    n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                t = datetime.fromisoformat(row.get(ts_field, "").replace("Z", "+00:00"))
                if t < since:
                    continue
                if filter_fn and not filter_fn(row):
                    continue
                n += 1
            except Exception:
                continue
    return n


def compute_funnel(days: int = 30) -> dict[str, Any]:
    """Build the full wholesale funnel snapshot."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    out: dict[str, Any] = {
        "as_of": now.isoformat(),
        "window_days": days,
        "window_start": since.isoformat(),
    }

    ws = _workspace()
    logs = ws / "_logs"

    # ── Email channel ────────────────────────────────────────
    email_sent = _count_jsonl(logs / "resend_budget.jsonl", since)
    out["email"] = {
        "sent": email_sent,
        "cost_usd": round(email_sent * COST_EMAIL, 2),
        "benchmark_reply_rate": BENCHMARK_REPLY_RATE["email"],
        "expected_replies": int(email_sent * BENCHMARK_REPLY_RATE["email"]),
    }

    # ── Direct mail channel ────────────────────────────────────────
    mail_sent = _count_jsonl(logs / "direct_mail.jsonl", since,
                             filter_fn=lambda r: r.get("ok") is True)
    out["mail"] = {
        "sent": mail_sent,
        "cost_usd": round(mail_sent * COST_MAIL, 2),
        "benchmark_reply_rate": BENCHMARK_REPLY_RATE["mail"],
        "expected_replies": int(mail_sent * BENCHMARK_REPLY_RATE["mail"]),
    }

    # ── JV outreach channel ─────────────────────────────────
    jv_pitched = _count_jsonl(
        ws / "_logs" / "jv_partnerships" / "pitched.jsonl",
        since, ts_field="sent_at",
    )
    out["jv"] = {
        "pitches_sent": jv_pitched,
        "cost_usd": round(jv_pitched * COST_EMAIL, 2),
    }

    # ── Phone callback channel ──────────────────────────────
    callbacks_queued = _count_jsonl(logs / "callback_queue.jsonl", since)
    out["phone"] = {
        "callbacks_queued": callbacks_queued,
        "estimated_va_minutes": callbacks_queued * 4,  # 4 min per dial average
        "estimated_va_cost_usd": round(callbacks_queued * 4 * COST_PER_DIAL_MIN, 2),
    }

    # ── Pipeline state from Django ──────────────────────────
    if _bootstrap_django():
        try:
            from broker_ops.models import (
                BrokerMatch, Deal, InvestorBuyer, OutreachSequence,
                PropertyLead,
            )
            from django.utils import timezone as dj_tz
            now_dj = dj_tz.now()
            since_dj = now_dj - timedelta(days=days)

            out["pipeline"] = {
                "buyers_active": InvestorBuyer.objects.filter(is_active=True, cash_buyer=True).count(),
                "buyers_target": 150,
                "leads_total": PropertyLead.objects.count(),
                "leads_at_new": PropertyLead.objects.filter(status="new").count(),
                "matches_total": BrokerMatch.objects.count(),
                "matches_approved": BrokerMatch.objects.filter(status="approved").count(),
                "matches_converted": BrokerMatch.objects.filter(status="converted").count(),
                "deals_total": Deal.objects.count(),
                "deals_window": Deal.objects.filter(started_at__gte=since_dj).count(),
                "deals_closed_won": Deal.objects.filter(stage="closed_won").count(),
                "outreach_sent_window": OutreachSequence.objects.filter(sent_at__gte=since_dj).count(),
            }

            # Per-channel cost-per-deal (only meaningful if deals > 0)
            total_cost = (
                out["email"]["cost_usd"] + out["mail"]["cost_usd"]
                + out["jv"]["cost_usd"] + out["phone"]["estimated_va_cost_usd"]
            )
            out["totals"] = {
                "spend_usd": round(total_cost, 2),
                "deals_closed_won": out["pipeline"]["deals_closed_won"],
                "cost_per_close": round(total_cost / out["pipeline"]["deals_closed_won"], 2)
                                  if out["pipeline"]["deals_closed_won"] else None,
            }
        except Exception as exc:
            out["pipeline_error"] = str(exc)[:200]

    # ── Q3 trajectory ──────────────────────────────────────
    q3_end = datetime(now.year, 9, 30, tzinfo=timezone.utc)
    weeks_left = max(0, (q3_end - now).days / 7)
    deals_won = (out.get("pipeline") or {}).get("deals_closed_won", 0)
    deals_per_week_needed_low = max(0, (6 - deals_won) / weeks_left) if weeks_left else 0
    deals_per_week_needed_high = max(0, (12 - deals_won) / weeks_left) if weeks_left else 0
    out["q3_trajectory"] = {
        "weeks_left_in_q3": round(weeks_left, 1),
        "deals_won_to_date": deals_won,
        "deals_per_week_needed_low_target": round(deals_per_week_needed_low, 2),
        "deals_per_week_needed_high_target": round(deals_per_week_needed_high, 2),
    }

    return out


def render_text_summary(f: dict[str, Any]) -> str:
    """Human-readable text summary for the Marcus briefing."""
    lines: list[str] = []
    lines.append(f"# Wholesale ROI -- last {f.get('window_days')} days")
    lines.append("")
    lines.append("## Channel spend and reach")
    em = f.get("email", {})
    ml = f.get("mail", {})
    jv = f.get("jv", {})
    ph = f.get("phone", {})
    lines.append(f"- Email:  {em.get('sent',0):>5} sent | ${em.get('cost_usd',0):.2f} | expected replies: {em.get('expected_replies',0)}")
    lines.append(f"- Mail:   {ml.get('sent',0):>5} sent | ${ml.get('cost_usd',0):.2f} | expected replies: {ml.get('expected_replies',0)}")
    lines.append(f"- JV:     {jv.get('pitches_sent',0):>5} pitches | ${jv.get('cost_usd',0):.2f}")
    lines.append(f"- Phone:  {ph.get('callbacks_queued',0):>5} callbacks queued | ~${ph.get('estimated_va_cost_usd',0):.2f} VA cost")

    p = f.get("pipeline", {})
    if p:
        lines.append("")
        lines.append("## Pipeline state")
        lines.append(f"- Buyers active: {p.get('buyers_active',0)} / target 150")
        lines.append(f"- Leads at status=new: {p.get('leads_at_new',0)} of {p.get('leads_total',0)}")
        lines.append(f"- Matches: {p.get('matches_total',0)} (approved: {p.get('matches_approved',0)}, converted: {p.get('matches_converted',0)})")
        lines.append(f"- Deals total: {p.get('deals_total',0)} (closed_won: {p.get('deals_closed_won',0)})")

    t = f.get("totals", {})
    if t:
        lines.append("")
        lines.append(f"## Totals")
        lines.append(f"- Spend: ${t.get('spend_usd',0):.2f}")
        lines.append(f"- Cost per close: ${t.get('cost_per_close')} " if t.get("cost_per_close") else "- Cost per close: (no closes yet)")

    q = f.get("q3_trajectory", {})
    if q:
        lines.append("")
        lines.append(f"## Q3 trajectory ({q.get('weeks_left_in_q3')} weeks left)")
        lines.append(f"- For 6-deal floor: {q.get('deals_per_week_needed_low_target')}/week needed")
        lines.append(f"- For 12-deal stretch: {q.get('deals_per_week_needed_high_target')}/week needed")
    return "\n".join(lines)


def _cli() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    f = compute_funnel(days=args.days)
    if args.json:
        print(json.dumps(f, indent=2, default=str))
    else:
        print(render_text_summary(f))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
