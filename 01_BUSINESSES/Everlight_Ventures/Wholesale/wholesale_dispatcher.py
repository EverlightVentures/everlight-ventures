"""wholesale_dispatcher -- the single cron entrypoint that runs the right
activity at the right time on the right day.

Why this design
---------------
Adding 30+ separate cron lines (one per day-time-activity combo) is brittle:
DST kills it, Oracle crontab edits get out of sync, and you cannot reason
about it. Instead we have ONE cron line that calls this dispatcher every
30 minutes. The dispatcher reads `weekly_cadence.DAILY_PLAN`, figures out
which activities are due in the current 30-minute window, and runs them.

When you change the schedule, edit `weekly_cadence.DAILY_PLAN`, not the
crontab. One source of truth.

Cron line on Oracle (via deploy_to_oracle.sh)
---------------------------------------------
    */30 * * * * cd /home/opc && source .env && \
        python3 /home/opc/wholesale/wholesale_dispatcher.py >> \
        /home/opc/_logs/wholesale_dispatcher.log 2>&1

How it decides what to run
--------------------------
1. Loads today's plan (filtered by SUNDAY_PHILOSOPHY)
2. Computes current PT hour + minute
3. For each scheduled activity whose `time_local_pt` is within
   [now - 30 min, now], fires the corresponding handler
4. Records the run to `_logs/wholesale_dispatcher.jsonl` so re-runs in
   the same window don't double-fire

Every handler is a thin function. To add a new activity, add it to
DAILY_PLAN and add the function to the HANDLERS dict.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import zoneinfo
    PT = zoneinfo.ZoneInfo("America/Los_Angeles")
except Exception:
    PT = None

log = logging.getLogger("wholesale_dispatcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WORKSPACE_CANDIDATES = [
    Path("/home/opc"),
    Path("/mnt/sdcard/AA_MY_DRIVE"),
]


def _workspace() -> Path:
    for p in WORKSPACE_CANDIDATES:
        if p.exists():
            return p
    return WORKSPACE_CANDIDATES[0]


# Ensure compliance + content_tools are on path
for sub in [
    "/home/opc/wholesale/compliance",
    "/home/opc/content_tools",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
]:
    if Path(sub).exists() and sub not in sys.path:
        sys.path.insert(0, sub)


from weekly_cadence import DAILY_PLAN, SUNDAY_PHILOSOPHY  # type: ignore  # noqa


WINDOW_MIN = 30  # cron fires every 30 min; activities within last 30 min fire
LEDGER = _workspace() / "_logs" / "wholesale_dispatcher.jsonl"


def _now_pt() -> datetime:
    if PT:
        return datetime.now(PT)
    return datetime.now()


def _within_window(scheduled_local_pt: str, now: datetime) -> bool:
    """True if `scheduled_local_pt` (HH:MM) is within the last WINDOW_MIN minutes."""
    try:
        h, m = scheduled_local_pt.split(":")
        sched = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    except Exception:
        return False
    delta = (now - sched).total_seconds() / 60
    return 0 <= delta < WINDOW_MIN


def _ledger_load_today(now: datetime) -> set[str]:
    """Return set of activity names already-run-today. Prevents double-fire."""
    if not LEDGER.exists():
        return set()
    today_str = now.strftime("%Y-%m-%d")
    out: set[str] = set()
    try:
        with LEDGER.open(encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    if row.get("date") == today_str and row.get("ok"):
                        out.add(row.get("name", ""))
                except Exception:
                    continue
    except Exception:
        return out
    return out


def _ledger_record(name: str, ok: bool, detail: str, now: datetime) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    try:
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "name": name,
                "ok": ok,
                "detail": detail[:500],
            }) + "\n")
    except Exception:
        pass


# ── ACTIVITY HANDLERS ──────────────────────────────────────────
#
# Each handler returns (ok: bool, detail: str). They MUST NOT raise --
# raising here would kill the whole dispatcher run and skip later
# activities. Wrap external calls in try/except.

def _run_python(args: list[str]) -> tuple[bool, str]:
    """Run a Python subprocess and return (ok, last_lines)."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=600)
        out = (r.stdout or "")[-1500:]
        if r.returncode == 0:
            return True, out
        return False, f"exit={r.returncode} stderr={(r.stderr or '')[-500:]}"
    except subprocess.TimeoutExpired:
        return False, "timeout_after_600s"
    except Exception as exc:
        return False, f"exception:{exc!r}"


def handle_buyer_dispo_blast() -> tuple[bool, str]:
    """Mon 7 AM PT: send branded buyer dispo for any active deal with priced inventory."""
    return _run_python([
        "python3", "/home/opc/hive_deal_orchestrator.py", "--pipeline", "broker",
    ])


def handle_marcus_weekly_brief() -> tuple[bool, str]:
    """Mon 8 AM PT: weekly briefing post."""
    return _run_python(["python3", "/home/opc/wholesale/marcus_briefings.py", "monday_weekly"])


def handle_filter_rescore_leads() -> tuple[bool, str]:
    """Mon 8:30 AM PT: re-run lead scoring with current niche-bonus settings."""
    return _run_python([
        "python3", "/home/opc/hive_django/manage.py", "shell", "-c",
        "from broker_ops.models import PropertyLead; from broker_ops.wholesale import score_property; "
        "n=0\nfor l in PropertyLead.objects.filter(status='new')[:1000]:\n  ns=score_property(l)\n  "
        "if ns!=l.motivation_score: l.motivation_score=ns; l.save(update_fields=['motivation_score']); n+=1\n"
        "print('rescored', n, 'leads')",
    ])


def handle_imap_sweep_weekend_replies() -> tuple[bool, str]:
    """Mon 9 AM PT: sweep weekend inbox for replies, create CallbackTasks."""
    return _run_python([
        "python3", "/home/opc/broker_daily_orchestrator.py", "replies",
    ])


def handle_seller_cold_email_batch() -> tuple[bool, str]:
    """Tue 6 AM PT: send personalized cold email batch to qualified sellers in compliant states."""
    return _run_python([
        "python3", "/home/opc/broker_daily_orchestrator.py", "outreach",
    ])


def handle_lob_mail_drop_batch() -> tuple[bool, str]:
    """Tue 10 AM PT: ship Lob mail batch (skips silently if no API key)."""
    return _run_python([
        "python3", "/home/opc/wholesale/direct_mail/lob_mail_sender.py", "status",
    ])


def handle_match_to_deal_auto() -> tuple[bool, str]:
    """Wed 8 AM PT: auto-approve high-score matches and convert to deals."""
    return _run_python([
        "python3", "/home/opc/hive_django/manage.py", "shell", "-c",
        "from broker_ops.services import auto_approve_high_score_matches as f; "
        "n=f(min_score=65.0, limit=20, auto_deal_min_score=70.0); print('approved', n)",
    ])


def handle_warm_followup_batch() -> tuple[bool, str]:
    """Wed 10 AM PT: warm follow-up email batch."""
    return _run_python([
        "python3", "/home/opc/broker_daily_orchestrator.py", "outreach",
    ])


def handle_title_company_pings() -> tuple[bool, str]:
    """Thu 9 AM PT: ping title cos on pending deals (placeholder until tool wired)."""
    return _run_python(["python3", "-c", "print('title_pings: 0 pending deals')"])


def handle_marcus_midweek_check() -> tuple[bool, str]:
    """Thu 10 AM PT: midweek pipeline check Slack post."""
    return _run_python(["python3", "/home/opc/wholesale/marcus_briefings.py", "thursday_midweek"])


def handle_roi_tracker_weekly() -> tuple[bool, str]:
    """Fri 3 PM PT: full week ROI tracker run."""
    return _run_python([
        "python3", "/home/opc/wholesale/wholesale_roi_tracker.py", "--days", "7",
    ])


def handle_marcus_friday_audit() -> tuple[bool, str]:
    """Fri 4 PM PT: Marcus Friday audit Slack post."""
    return _run_python(["python3", "/home/opc/wholesale/marcus_briefings.py", "friday_audit"])


def handle_buyer_list_scrape() -> tuple[bool, str]:
    """Sat morning + Fri evening: scrape Google Places (skips if no API key)."""
    return _run_python([
        "python3", "/home/opc/wholesale/buyer_acquisition/buyer_list_builder.py",
        "sweep",
    ])


def handle_queue_saturday_calls() -> tuple[bool, str]:
    """Fri 9 PM PT: queue Saturday morning's 5 highest-motivation callbacks."""
    return _run_python([
        "python3", "/home/opc/hive_django/manage.py", "shell", "-c",
        "from broker_ops.models import PropertyLead, CallbackTask; from django.db.models import Q; "
        "qs = PropertyLead.objects.filter(status='new', state__in=['GA','FL','TX','AZ','TN','MO']).exclude(owner_phone='').order_by('-motivation_score')[:5]; "
        "n=0\nfor l in qs:\n  CallbackTask.objects.get_or_create(lead_id=str(l.id), defaults={'priority':'high','reason':f'Sat-morning queued {l.address}','phone':l.owner_phone or '','contact_name':l.owner_name or '','status':'pending','source':'sat_morning_queue'}); n+=1\n"
        "print('queued', n, 'callbacks for Saturday')",
    ])


def handle_saturday_callback_load() -> tuple[bool, str]:
    """Sat 7 AM PT: ensure callback queue is fresh + post short Slack ping."""
    return _run_python(["python3", "/home/opc/wholesale/marcus_briefings.py", "saturday_callbacks"])


def handle_jv_scout_run() -> tuple[bool, str]:
    """Sat 10 AM PT: scout JV wholesaler candidates (skips if no API key)."""
    return _run_python([
        "python3", "/home/opc/wholesale/jv_partnerships/jv_wholesaler_scout.py",
        "scout", "--city", "Atlanta",
    ])


def handle_imap_sweep_short() -> tuple[bool, str]:
    """Various daily times: short IMAP reply sweep."""
    return _run_python([
        "python3", "/home/opc/broker_daily_orchestrator.py", "replies",
    ])


def handle_sunday_planning_brief() -> tuple[bool, str]:
    """Sun 10 AM PT: planning brief Slack post."""
    return _run_python(["python3", "/home/opc/wholesale/marcus_briefings.py", "sunday_planning"])


def handle_roi_tracker_run() -> tuple[bool, str]:
    """Sun 11 AM PT: 30-day ROI tracker run."""
    return _run_python([
        "python3", "/home/opc/wholesale/wholesale_roi_tracker.py", "--days", "30",
    ])


def handle_buyer_list_dedupe() -> tuple[bool, str]:
    """Sun 2 PM PT: status check on buyer list."""
    return _run_python([
        "python3", "/home/opc/wholesale/buyer_acquisition/buyer_list_builder.py",
        "status",
    ])


def handle_marcus_lookahead_brief() -> tuple[bool, str]:
    """Sun 6 PM PT: week-ahead Marcus brief."""
    return _run_python(["python3", "/home/opc/wholesale/marcus_briefings.py", "sunday_lookahead"])


def handle_monday_morning_dispo_send() -> tuple[bool, str]:
    """Sun 8 PM PT: send-ahead buyer dispo so it lands top of inbox Mon AM."""
    return _run_python([
        "python3", "/home/opc/hive_deal_orchestrator.py", "--pipeline", "broker",
    ])


def handle_jv_pitch_send() -> tuple[bool, str]:
    """Sun 8:30 PM PT: send branded JV pitches to scouted wholesalers."""
    return _run_python([
        "python3", "/home/opc/wholesale/jv_partnerships/jv_wholesaler_scout.py",
        "pitch", "--city", "Atlanta", "--limit", "10",
    ])


def handle_ai_call_consented_callbacks() -> tuple[bool, str]:
    """Tue/Wed/Thu/Sat compliant windows: dial up to MAX_PER_CYCLE consented sellers.

    Pulls CallbackTask rows that:
      - have a phone number,
      - have non-revoked consent on file with `ai_call` channel,
      - are status=pending.

    Fires `ai_caller.dial_consented()` -- which runs all 6 compliance gates
    again on each call. Hard cap per cycle (default 5) prevents runaway.
    """
    return _run_python([
        "python3", "/home/opc/wholesale/voice/dispatch_ai_calls.py",
    ])


# Activity name -> handler
HANDLERS: dict[str, Any] = {
    "buyer_dispo_blast": handle_buyer_dispo_blast,
    "marcus_weekly_brief": handle_marcus_weekly_brief,
    "filter_rescore_leads": handle_filter_rescore_leads,
    "imap_sweep_weekend_replies": handle_imap_sweep_weekend_replies,
    "seller_cold_email_batch": handle_seller_cold_email_batch,
    "lob_mail_drop_batch": handle_lob_mail_drop_batch,
    "midday_imap_sweep": handle_imap_sweep_short,
    "match_to_deal_auto": handle_match_to_deal_auto,
    "warm_followup_batch": handle_warm_followup_batch,
    "title_company_pings": handle_title_company_pings,
    "marcus_midweek_check": handle_marcus_midweek_check,
    "roi_tracker_weekly": handle_roi_tracker_weekly,
    "marcus_friday_audit": handle_marcus_friday_audit,
    "buyer_list_scrape_friday": handle_buyer_list_scrape,
    "queue_saturday_morning_calls": handle_queue_saturday_calls,
    "saturday_morning_callback_queue": handle_saturday_callback_load,
    "buyer_scrape_continues": handle_buyer_list_scrape,
    "jv_scout_run": handle_jv_scout_run,
    "saturday_imap_sweep": handle_imap_sweep_short,
    "sunday_planning_brief": handle_sunday_planning_brief,
    "roi_tracker_run": handle_roi_tracker_run,
    "buyer_list_dedupe": handle_buyer_list_dedupe,
    "marcus_lookahead_brief": handle_marcus_lookahead_brief,
    "monday_morning_dispo_send": handle_monday_morning_dispo_send,
    "jv_pitch_send_for_monday_read": handle_jv_pitch_send,
    "mail_arrives_in_mailboxes": lambda: (True, "mail_arrives_no_action_needed"),
    "ai_call_consented_callbacks": handle_ai_call_consented_callbacks,
}


def dispatch_now() -> dict:
    """Run every activity whose scheduled time is within the last WINDOW_MIN minutes."""
    now = _now_pt()
    plan = DAILY_PLAN.get(now.weekday(), {})
    activities = plan.get("bot_activities", [])
    fired_today = _ledger_load_today(now)

    summary = {
        "now_pt": now.strftime("%Y-%m-%d %H:%M %Z"),
        "weekday": now.strftime("%A"),
        "label": plan.get("label", ""),
        "sunday_philosophy": SUNDAY_PHILOSOPHY,
        "fired": [],
        "skipped_filtered": [],
        "skipped_already_today": [],
        "skipped_outside_window": [],
        "errors": [],
    }

    for act in activities:
        name = act.get("name")
        sched = act.get("time_local_pt", "")

        # Sunday philosophy filter
        req = act.get("philosophy_required")
        if req and SUNDAY_PHILOSOPHY not in req:
            summary["skipped_filtered"].append(name)
            continue

        # Already-ran-today guard
        if name in fired_today:
            summary["skipped_already_today"].append(name)
            continue

        # Time window check
        if not _within_window(sched, now):
            summary["skipped_outside_window"].append(f"{name}@{sched}")
            continue

        handler = HANDLERS.get(name)
        if not handler:
            summary["errors"].append(f"no_handler:{name}")
            _ledger_record(name, False, "no_handler", now)
            continue

        try:
            ok, detail = handler()
            _ledger_record(name, ok, detail, now)
            (summary["fired"] if ok else summary["errors"]).append(
                f"{name} -> {'OK' if ok else 'FAIL: ' + detail[:100]}"
            )
        except Exception as exc:
            tb = traceback.format_exc()[-300:]
            _ledger_record(name, False, f"exception:{exc!r} {tb}", now)
            summary["errors"].append(f"{name} EXC: {exc}")

    return summary


def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Show what would fire, don't run")
    ap.add_argument("--force", help="Force-run a single activity by name")
    args = ap.parse_args()

    if args.force:
        h = HANDLERS.get(args.force)
        if not h:
            print(f"unknown handler: {args.force}")
            return 1
        ok, detail = h()
        print(json.dumps({"name": args.force, "ok": ok, "detail": detail[:400]}, indent=2))
        return 0 if ok else 2

    if args.dry_run:
        now = _now_pt()
        plan = DAILY_PLAN.get(now.weekday(), {})
        print(f"now_pt: {now.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"label : {plan.get('label')}")
        for a in plan.get("bot_activities", []):
            in_window = _within_window(a.get("time_local_pt", ""), now)
            print(f"  - {a['name']:42} @{a.get('time_local_pt','?')} -> {'WOULD FIRE' if in_window else 'wait'}")
        return 0

    summary = dispatch_now()
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
