"""marcus_briefings -- the day-of-week Slack briefings Marcus posts automatically.

Each function pulls live data from Django + the cadence engine + the ROI
tracker and posts a branded Slack card in Marcus's voice. All bot-fired
from `wholesale_dispatcher.py` based on `DAILY_PLAN`.

Voice principle: every brief NAMES specific agents who did or will do
work, gives concrete numbers, and tells Rich exactly what he should do
next. No generic status updates.

CLI
---
    python3 marcus_briefings.py monday_weekly
    python3 marcus_briefings.py thursday_midweek
    python3 marcus_briefings.py friday_audit
    python3 marcus_briefings.py saturday_callbacks
    python3 marcus_briefings.py sunday_planning
    python3 marcus_briefings.py sunday_lookahead
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

for sub in [
    "/home/opc/content_tools",
    "/home/opc/wholesale",
    "/home/opc/wholesale/compliance",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance",
]:
    if Path(sub).exists() and sub not in sys.path:
        sys.path.insert(0, sub)


def _bootstrap_django():
    project = "/home/opc/hive_django"
    if not Path(project).exists():
        project = "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"
    if project not in sys.path:
        sys.path.insert(0, project)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
    try:
        import django
        django.setup()
        return True
    except Exception:
        return False


def _live_pipeline_state() -> dict:
    if not _bootstrap_django():
        return {"available": False}
    try:
        from broker_ops.models import (BrokerMatch, CallbackTask, Deal,
                                        InvestorBuyer, OutreachSequence,
                                        PropertyLead)
        from django.utils import timezone as dj_tz
        now = dj_tz.now()
        last24 = now - timedelta(hours=24)
        last7 = now - timedelta(days=7)
        return {
            "available": True,
            "deals_total": Deal.objects.count(),
            "deals_closed_won": Deal.objects.filter(stage="closed_won").count(),
            "deals_intro": Deal.objects.filter(stage="intro").count(),
            "matches_approved": BrokerMatch.objects.filter(status="approved").count(),
            "matches_converted": BrokerMatch.objects.filter(status="converted").count(),
            "outreach_sent_24h": OutreachSequence.objects.filter(sent_at__gte=last24).count(),
            "outreach_sent_7d": OutreachSequence.objects.filter(sent_at__gte=last7).count(),
            "outreach_pending": OutreachSequence.objects.filter(status="pending").count(),
            "leads_new": PropertyLead.objects.filter(status="new").count(),
            "buyers_active": InvestorBuyer.objects.filter(is_active=True, cash_buyer=True).count(),
            "callbacks_pending": CallbackTask.objects.filter(status="pending").count(),
            "callbacks_high_priority": CallbackTask.objects.filter(status="pending", priority__in=["urgent", "high"]).count(),
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)[:200]}


def _post(title, summary, body, fields, agent_title="Chief Operator", category="report"):
    from branded_slack import post_branded_slack
    return post_branded_slack(
        channel="#war-room",
        title=title, summary=summary, body=body, fields=fields,
        agent_name="Marcus Cole", agent_title=agent_title, category=category,
    )


# ── Mon: Weekly brief ─────────────────────────────────────────

def monday_weekly():
    s = _live_pipeline_state()
    body = (
        "*Monday. Power-up day.* Investors are back at desks, sellers are back from weekend, the highest-leverage week of the cycle starts now.\n\n"
        "*Today the team runs:*\n"
        "- *Hammer* sent buyer dispo at 7 AM PT to active cash buyers.\n"
        "- *Filter Banks* re-scored the lead pool with current niche-bonus settings.\n"
        "- *Justine* swept the IMAP for weekend replies. Any motivated reply auto-creates a CallbackTask with talking points.\n\n"
        f"*Pipeline state right now:*\n"
        f"- Deals total: {s.get('deals_total','?')} ({s.get('deals_intro','?')} at intro, {s.get('deals_closed_won','?')} closed)\n"
        f"- Approved matches awaiting deal: {s.get('matches_approved','?')}\n"
        f"- Buyers active: {s.get('buyers_active','?')} of 150 target\n"
        f"- Pending callbacks: {s.get('callbacks_pending','?')} ({s.get('callbacks_high_priority','?')} high priority)\n"
        f"- Outreach sent last 7 days: {s.get('outreach_sent_7d','?')}\n\n"
        "*Your move today (Rich):*\n"
        "- 30 min: call back any high-priority CallbackTasks (these are sellers who replied over the weekend).\n"
        "- Approve Tuesday outreach queue (Piper has cold-email batch ready for 6 AM PT tomorrow).\n\n"
        "Tomorrow is the highest-volume cold-email day of the week. Have approvals in by 9 PM PT tonight."
    )
    return _post(
        "Weekly Briefing -- Monday Power-up",
        "Buyers refreshed. Filter rescored. Weekend replies in callback queue. Tuesday cold-email batch awaits your approval.",
        body, {
            "Pipeline deals": str(s.get("deals_total", "?")),
            "Pending callbacks": str(s.get("callbacks_pending", "?")),
            "Outreach sent (7d)": str(s.get("outreach_sent_7d", "?")),
            "Buyers active": f"{s.get('buyers_active','?')} of 150",
        })


# ── Thu: Midweek check ─────────────────────────────────────────

def thursday_midweek():
    s = _live_pipeline_state()
    body = (
        "*Thursday. Push to close.* Wednesday's negotiations are now contracts to push or walk away from.\n\n"
        "*This week so far:*\n"
        f"- Outreach sent last 7d: *{s.get('outreach_sent_7d','?')}*\n"
        f"- Approved matches: *{s.get('matches_approved','?')}* (auto-conversion target: score >= 70 with priced offers)\n"
        f"- Deals at intro stage: *{s.get('deals_intro','?')}*\n"
        f"- Callbacks queued: *{s.get('callbacks_pending','?')}*\n\n"
        "*Your move (Rich):*\n"
        "- Make 2-3 closing-pressure calls on whatever is at intro / negotiating stage.\n"
        "- 'Are we doing this or not?' If they hesitate, set a Friday deadline.\n\n"
        "Direct mail batch from Tuesday is hitting mailboxes today (when LOB_API_KEY is funded -- otherwise queued)."
    )
    return _post(
        "Midweek Check -- Push to Close",
        "Wed's negotiations become Thu's contracts. Closing pressure calls today.",
        body, {
            "Deals at intro": str(s.get("deals_intro", "?")),
            "Approved matches": str(s.get("matches_approved", "?")),
            "Pending callbacks": str(s.get("callbacks_pending", "?")),
        })


# ── Fri: Audit ────────────────────────────────────────────────

def friday_audit():
    s = _live_pipeline_state()
    body = (
        "*Friday audit.* Honest read on the week.\n\n"
        "*The numbers:*\n"
        f"- Outreach sent (7d): *{s.get('outreach_sent_7d','?')}*\n"
        f"- Replies / callbacks queued: *{s.get('callbacks_pending','?')}*\n"
        f"- Deals created: *{s.get('deals_total','?')}* total ({s.get('deals_intro','?')} intro, {s.get('deals_closed_won','?')} closed)\n"
        f"- Match approval queue: *{s.get('matches_approved','?')}* approved, *{s.get('matches_converted','?')}* converted to deals\n"
        f"- Buyer list: *{s.get('buyers_active','?')}* of 150 target ({150 - int(s.get('buyers_active') or 0)} short)\n"
        f"- Lead pool: *{s.get('leads_new','?')}* at status=new\n\n"
        "*Tomorrow is the highest-leverage day of the week.* Sat 8-11 AM local cold-call answer rate is 40% (vs Tue's 28%).\n\n"
        "*Your move tonight:*\n"
        "- 30 min pipeline review.\n"
        "- The dispatcher pre-loads 5 highest-motivation calls into the CallbackTask queue at 9 PM PT.\n"
        "- Open the queue Sat morning and start at 8 AM YOUR local time."
    )
    return _post(
        "Friday Audit -- Honest Numbers",
        "The week's real output. Saturday morning cold-calls are pre-queued. 40% answer rate window is yours.",
        body, {
            "Outreach sent (7d)": str(s.get("outreach_sent_7d", "?")),
            "Deals total": str(s.get("deals_total", "?")),
            "Buyers gap to 150": str(150 - int(s.get("buyers_active") or 0)),
            "Sat queue loads": "9 PM PT tonight",
        })


# ── Sat: Callback queue load ───────────────────────────────────

def saturday_callbacks():
    s = _live_pipeline_state()
    body = (
        "*Saturday morning. The secret weapon.*\n\n"
        f"Callback queue: *{s.get('callbacks_pending','?')}* total, *{s.get('callbacks_high_priority','?')}* high priority.\n\n"
        "Open the dashboard at `:8504/admin/broker_ops/callbacktask/`. Each one has talking points pre-loaded by Hammer Knox -- pain anchor, offer range, market context, 5 qualifiers, close script.\n\n"
        "*Your one job for the next 3 hours:* call 5. That's it. The whole engine is built so this is the only window where YOU are the single point of failure.\n\n"
        "Industry benchmark: 5 cold calls in this window, 2 contacts, 1 qualified, 0-1 callback set. Over 8 weeks at 1/week = first $5K assignment."
    )
    return _post(
        "Saturday Callbacks -- 8 to 11 AM Window",
        "Highest answer rate of the week. Queue is pre-loaded. Your one move: call 5.",
        body, {
            "Callbacks queued": str(s.get("callbacks_pending", "?")),
            "High priority": str(s.get("callbacks_high_priority", "?")),
            "Window": "8-11 AM YOUR local time",
            "Talking points": "pre-loaded per lead",
        }, category="ops")


# ── Sun: Planning brief (10 AM) ────────────────────────────────

def sunday_planning():
    s = _live_pipeline_state()
    body = (
        "*Sunday morning. Quiet lap.*\n\n"
        "Bots are in low-activity mode. The pipeline is at its weekly waterline.\n\n"
        f"*Pipeline at this hour:*\n"
        f"- Deals: {s.get('deals_total','?')} | Approved matches: {s.get('matches_approved','?')} | Pending outreach: {s.get('outreach_pending','?')}\n"
        f"- Buyers active: {s.get('buyers_active','?')} of 150\n\n"
        "*Take the morning off.* Marcus look-ahead brief lands at 6 PM PT with next week's specific targets. Bots send the Mon-morning dispo at 8 PM PT so investors see it top of inbox tomorrow.\n\n"
        "If you want to use the day at all: 15 min copying 5 cash-buyer profiles from \"We Buy Houses Atlanta\" Google search into a CSV in `/home/opc/wholesale/buyer_acquisition/seeds/`. Drops auto-load to Supabase tomorrow."
    )
    return _post(
        "Sunday Planning -- Quiet Lap",
        "Bots in low-activity. Take the morning. Look-ahead brief at 6 PM PT.",
        body, {
            "Deals": str(s.get("deals_total", "?")),
            "Approved matches": str(s.get("matches_approved", "?")),
            "Buyers": str(s.get("buyers_active", "?")),
            "Look-ahead brief": "6 PM PT today",
        }, category="ops")


# ── Sun: Look-ahead brief (6 PM) ──────────────────────────────

def sunday_lookahead():
    s = _live_pipeline_state()
    body = (
        "*Look-ahead. Next week's plan.*\n\n"
        "*Mon AM:* Hammer dispo at 7 AM (any priced inventory). Filter rescore. Weekend reply sweep.\n"
        "*Tue 6 AM:* Piper sends seller cold email batch. Personalized pitches with live Zillow data, owner intel, voice pack -- one per lead.\n"
        "*Tue 9-11 AM YOUR local:* You cold-call top 5 of callable list.\n"
        "*Wed:* Match-to-deal auto. Warm follow-up batch.\n"
        "*Thu:* Closing pressure. Marcus midweek check.\n"
        "*Fri 4 PM:* Marcus Friday audit. 9 PM Saturday queue loads.\n"
        "*Sat 8-11 AM:* THE call window. 5 calls. Pre-loaded talking points.\n\n"
        f"*Open ends going into the week:*\n"
        f"- {s.get('matches_approved','?')} approved matches awaiting deal conversion (most need price data on the offer).\n"
        f"- {s.get('callbacks_pending','?')} callbacks pending. Clear them this week.\n"
        f"- Buyer list at {s.get('buyers_active','?')} of 150 -- the gating constraint on Q3.\n\n"
        "*In 30 minutes,* the dispatcher fires the Mon-morning dispo so investors see it top of inbox tomorrow. JV pitches go out at 8:30 PM. After that, the team is dark until 7 AM Mon."
    )
    return _post(
        "Sunday Look-ahead -- Next Week's Plan",
        "Mon AM dispo, Tue cold-email batch, Sat 8-11 AM your call window. Open ends to clear this week.",
        body, {
            "Approved matches awaiting deal": str(s.get("matches_approved", "?")),
            "Callbacks pending": str(s.get("callbacks_pending", "?")),
            "Buyer gap to 150": str(150 - int(s.get("buyers_active") or 0)),
            "Mon dispo fires": "8 PM PT tonight",
        })


HANDLERS = {
    "monday_weekly": monday_weekly,
    "thursday_midweek": thursday_midweek,
    "friday_audit": friday_audit,
    "saturday_callbacks": saturday_callbacks,
    "sunday_planning": sunday_planning,
    "sunday_lookahead": sunday_lookahead,
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 marcus_briefings.py <handler>")
        print("handlers:", list(HANDLERS.keys()))
        sys.exit(1)
    name = sys.argv[1]
    h = HANDLERS.get(name)
    if not h:
        print(f"unknown: {name}; valid: {list(HANDLERS.keys())}")
        sys.exit(1)
    r = h()
    print(json.dumps({"ok": getattr(r, "ok", False), "ts": getattr(r, "ts", "")}))
