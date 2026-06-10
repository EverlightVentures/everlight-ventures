"""weekly_cadence -- the SINGLE clock + compliance gate every outreach script consults.

Why this exists
---------------
Outreach used to fire whenever a cron triggered. That ignores three facts
that determine reply rates and legality:

  1. Day-of-week answer rates differ massively (Sat 8-11 AM = 40% answer
     vs Tue = 28%; Sun morning = dead).
  2. State telemarketing law differs: NC GS 75-100 prohibits Sunday calls,
     TX SB 140 bans cold SMS, FL solicitation hours end 8 PM on Sunday.
  3. Federal TCPA layers on top: 8 AM - 9 PM local at the recipient,
     federal DNC scrub, no autodialed/AI calls without prior express
     written consent.

This module gives every sender ONE function to call before any outreach:

    allowed, reason = is_outreach_allowed_now(state="GA", channel="email")
    if not allowed:
        defer_or_skip(reason)
    else:
        send()

It also exposes `todays_activity_plan()` so the day-of-week schedule is
machine-readable and the cron can dispatch the right work for the day.

Compliance sources (Q1 2026)
----------------------------
- Federal: 16 CFR 310.4(c) (TSR call hours), 47 CFR 64.1200 (TCPA),
  CAN-SPAM Act for email
- State data: see state_gates.json (refreshed quarterly per CLAUDE.md
  Wholesale Compliance section)
- Wholesale-specific: NC HB 797 (NC OUT for wholesale), TX SB 140
  (TX cold SMS BLOCKED), CA CC 2945 (CA pre-foreclosure BLOCKED)

Trust model
-----------
This module is intentionally CONSERVATIVE. When state_gates is missing
or ambiguous, we say NO. We never silently fall back to "probably ok."
Every block reason is explicit so a human reviewer can see why.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Optional

try:
    import zoneinfo
except ImportError:
    zoneinfo = None

log = logging.getLogger("weekly_cadence")

# ── Paths to compliance data ────────────────────────────────────

_THIS = Path(__file__).resolve()
STATE_GATES_PATHS = [
    _THIS.parent / "state_gates.json",
    Path("/home/opc/wholesale/compliance/state_gates.json"),
    Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/state_gates.json"),
]


def _load_state_gates() -> dict:
    for p in STATE_GATES_PATHS:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception as exc:
                log.warning("could not parse %s: %s", p, exc)
    return {}


_STATE_GATES = _load_state_gates()


# ── State -> primary timezone ───────────────────────────────────

STATE_TZ = {
    "AL": "America/Chicago", "AK": "America/Anchorage", "AZ": "America/Phoenix",
    "AR": "America/Chicago", "CA": "America/Los_Angeles", "CO": "America/Denver",
    "CT": "America/New_York", "DE": "America/New_York", "DC": "America/New_York",
    "FL": "America/New_York", "GA": "America/New_York", "HI": "Pacific/Honolulu",
    "ID": "America/Boise", "IL": "America/Chicago", "IN": "America/Indianapolis",
    "IA": "America/Chicago", "KS": "America/Chicago", "KY": "America/New_York",
    "LA": "America/Chicago", "ME": "America/New_York", "MD": "America/New_York",
    "MA": "America/New_York", "MI": "America/New_York", "MN": "America/Chicago",
    "MS": "America/Chicago", "MO": "America/Chicago", "MT": "America/Denver",
    "NE": "America/Chicago", "NV": "America/Los_Angeles", "NH": "America/New_York",
    "NJ": "America/New_York", "NM": "America/Denver", "NY": "America/New_York",
    "NC": "America/New_York", "ND": "America/Chicago", "OH": "America/New_York",
    "OK": "America/Chicago", "OR": "America/Los_Angeles", "PA": "America/New_York",
    "RI": "America/New_York", "SC": "America/New_York", "SD": "America/Chicago",
    "TN": "America/Chicago", "TX": "America/Chicago", "UT": "America/Denver",
    "VT": "America/New_York", "VA": "America/New_York", "WA": "America/Los_Angeles",
    "WV": "America/New_York", "WI": "America/Chicago", "WY": "America/Denver",
}


def _now_local(state: str) -> datetime:
    """Return the current time in the recipient's local timezone."""
    tz_name = STATE_TZ.get((state or "").upper(), "America/New_York")
    if zoneinfo:
        try:
            return datetime.now(zoneinfo.ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now()


def _parse_time(s: str) -> Optional[time]:
    if not s or s == "?":
        return None
    try:
        h, m = s.split(":", 1)
        return time(int(h), int(m))
    except Exception:
        return None


# ── Consent ledger lookup (PEWC) ────────────────────────────────

def _normalize_phone(p: str) -> str:
    digits = "".join(c for c in (p or "") if c.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


def is_consent_on_file(*, phone: str = "", email: str = "",
                        channel: str = "ai_call") -> tuple[bool, str]:
    """Check ConsentLedger for a non-revoked PEWC record covering `channel`.

    Phone match takes precedence (TCPA cares about the phone number);
    email is fallback for email-marketing-only consent. Returns
    (allowed, reason). Best-effort -- if Django can't be loaded
    (e.g. running outside the dashboard project), returns
    (False, "consent_check_unavailable") to be safe.
    """
    try:
        import os, sys
        for p in ("/home/opc/hive_django",
                  "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
            if p not in sys.path:
                sys.path.insert(0, p)
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
        import django
        try:
            django.setup()
        except Exception:
            pass
        from broker_ops.models import ConsentLedger
    except Exception as exc:
        return False, f"consent_check_unavailable:{exc}"

    p_norm = _normalize_phone(phone)
    e_norm = (email or "").strip().lower()
    if not (p_norm or e_norm):
        return False, "no_phone_or_email_to_check"

    qs = ConsentLedger.objects.filter(revoked=False)
    if p_norm:
        row = qs.filter(contact_phone=p_norm).order_by("-created_at").first()
        if row and channel in (row.channels or []):
            return True, f"consent_on_file:phone:{row.id}"
    if e_norm:
        row = qs.filter(contact_email=e_norm).order_by("-created_at").first()
        if row and channel in (row.channels or []):
            return True, f"consent_on_file:email:{row.id}"
    return False, f"no_consent_for_channel:{channel}"


# ── The compliance gate ────────────────────────────────────────

def is_outreach_allowed_now(
    state: str, channel: str = "email",
    *, lead_type: str = "", now: Optional[datetime] = None,
    contact_phone: str = "", contact_email: str = "",
) -> tuple[bool, str]:
    """Return (allowed, reason).

    Channels: "email" | "call" | "sms" | "mail" | "voicemail_drop"

    The function consults state_gates.json + the day-of-week + the local
    hour at the recipient. Every block carries a plain-English reason
    suitable for logging and showing to humans.
    """
    state_u = (state or "").upper().strip()
    channel = (channel or "email").lower().strip()
    if not state_u:
        return False, "no_state_provided"

    gate = _STATE_GATES.get(state_u)
    if not gate:
        return False, f"no_compliance_record_for_{state_u}_(refusing)"

    # Wholesale-specific blocks (HB 797, etc.)
    wholesale_status = (gate.get("wholesale_legal_status") or "").lower()
    if "out" in wholesale_status or wholesale_status == "license_required":
        return False, f"{state_u}_wholesale_blocked_per_state_law"

    # Pre-foreclosure-specific block (CA CC 2945, etc.)
    if lead_type == "pre_foreclosure" and not gate.get("preforeclosure_outreach_allowed", False):
        return False, f"{state_u}_preforeclosure_outreach_blocked"

    if not now:
        now = _now_local(state_u)
    weekday = now.weekday()  # 0=Mon .. 6=Sun
    is_sunday = weekday == 6

    # ── Channel: MAIL ──────────────────────────────────────
    if channel == "mail":
        # Direct mail is mostly time-of-day agnostic and federally allowed
        # everywhere. State pre-foreclosure consultant statutes already
        # checked above. Always allowed otherwise.
        return True, "mail_allowed"

    # ── Channel: EMAIL ─────────────────────────────────────
    if channel == "email":
        if gate.get("email_hours_restricted"):
            current = now.time()
            if is_sunday:
                start = _parse_time(gate.get("outbound_call_hours_local", {}).get("sun_start", ""))
                end = _parse_time(gate.get("outbound_call_hours_local", {}).get("sun_end", ""))
            else:
                start = _parse_time(gate.get("outbound_call_hours_local", {}).get("mon_sat_start", "08:00"))
                end = _parse_time(gate.get("outbound_call_hours_local", {}).get("mon_sat_end", "21:00"))
            if start and end and not (start <= current <= end):
                return False, f"{state_u}_email_outside_hours_{current.strftime('%H:%M')}"
        return True, "email_allowed"

    # ── Channel: SMS ───────────────────────────────────────
    if channel == "sms":
        if not gate.get("sms_allowed", False):
            return False, f"{state_u}_sms_cold_blocked_per_state_law"
        return _check_call_hours(gate, now, channel="sms")

    # ── Channel: VOICEMAIL DROP (requires PEWC) ────────────
    if channel == "voicemail_drop":
        consented, why = is_consent_on_file(
            phone=contact_phone, email=contact_email,
            channel="prerecorded_voicemail",
        )
        if not consented:
            return False, f"voicemail_drop_blocked_{why}"
        if is_sunday:
            return False, "voicemail_drop_blocked_on_sunday_(conservative)"
        return _check_call_hours(gate, now, channel="voicemail_drop")

    # ── Channel: AI VOICE CALL (requires PEWC) ─────────────
    if channel == "ai_call":
        consented, why = is_consent_on_file(
            phone=contact_phone, email=contact_email, channel="ai_call",
        )
        if not consented:
            return False, f"ai_call_blocked_{why}_(PEWC_required_per_47_CFR_64.1200)"
        return _check_call_hours(gate, now, channel="ai_call")

    # ── Channel: AUTODIALED CALL (requires PEWC) ────────────
    if channel == "autodialed_call":
        consented, why = is_consent_on_file(
            phone=contact_phone, email=contact_email,
            channel="autodialed_call",
        )
        if not consented:
            return False, f"autodialed_blocked_{why}_(PEWC_required)"
        return _check_call_hours(gate, now, channel="autodialed_call")

    # ── Channel: CALL (manual, human dialer -- no PEWC needed) ──
    if channel == "call":
        return _check_call_hours(gate, now, channel="call")

    return False, f"unknown_channel:{channel}"


def _check_call_hours(gate: dict, now: datetime, channel: str = "call") -> tuple[bool, str]:
    weekday = now.weekday()
    is_sunday = weekday == 6
    hrs = gate.get("outbound_call_hours_local", {})
    if is_sunday:
        if not hrs.get("sun_allowed", False):
            return False, "state_blocks_sunday_solicitation"
        start = _parse_time(hrs.get("sun_start", ""))
        end = _parse_time(hrs.get("sun_end", ""))
    else:
        start = _parse_time(hrs.get("mon_sat_start", "08:00"))
        end = _parse_time(hrs.get("mon_sat_end", "21:00"))

    if not (start and end):
        return False, "state_call_hours_undefined_(refusing)"

    current = now.time()
    if start <= current <= end:
        return True, f"{channel}_allowed_{current.strftime('%H:%M')}"
    return False, f"{channel}_outside_local_hours_{current.strftime('%H:%M')}_window_{start}_{end}"


# ── Day-of-week activity schedule ──────────────────────────────

import os
SUNDAY_PHILOSOPHY = os.environ.get("SUNDAY_PHILOSOPHY", "hybrid").lower()


DAILY_PLAN = {
    0: {  # Monday
        "label": "Monday -- Power-up",
        "bot_activities": [
            {"name": "buyer_dispo_blast", "time_local_pt": "07:00", "channel": "email", "audience": "buyers"},
            {"name": "marcus_weekly_brief", "time_local_pt": "08:00", "channel": "slack", "audience": "team"},
            {"name": "filter_rescore_leads", "time_local_pt": "08:30", "channel": "internal"},
            {"name": "imap_sweep_weekend_replies", "time_local_pt": "09:00", "channel": "internal"},
        ],
        "human_focus": "Call back any weekend replies (highest motivation tier). Approve Tuesday outreach queue.",
    },
    1: {  # Tuesday
        "label": "Tuesday -- Cold-call peak",
        "bot_activities": [
            {"name": "seller_cold_email_batch", "time_local_pt": "06:00", "channel": "email", "audience": "sellers"},
            {"name": "lob_mail_drop_batch", "time_local_pt": "10:00", "channel": "mail", "audience": "sellers"},
            {"name": "ai_call_consented_callbacks", "time_local_pt": "11:00", "channel": "ai_call", "audience": "sellers"},
            {"name": "midday_imap_sweep", "time_local_pt": "13:00", "channel": "internal"},
            {"name": "ai_call_consented_callbacks", "time_local_pt": "15:00", "channel": "ai_call", "audience": "sellers"},
        ],
        "human_focus": "9-11 AM local: cold call top 5 of callable list. Highest answer day for working hours.",
    },
    2: {  # Wednesday
        "label": "Wednesday -- Negotiate / convert",
        "bot_activities": [
            {"name": "match_to_deal_auto", "time_local_pt": "08:00", "channel": "internal"},
            {"name": "warm_followup_batch", "time_local_pt": "10:00", "channel": "email", "audience": "warm_leads"},
            {"name": "ai_call_consented_callbacks", "time_local_pt": "11:00", "channel": "ai_call", "audience": "sellers"},
            {"name": "midday_imap_sweep", "time_local_pt": "13:00", "channel": "internal"},
        ],
        "human_focus": "Convert Tuesday's interest into appointments. Schedule Saturday walk-throughs.",
    },
    3: {  # Thursday
        "label": "Thursday -- Push to close",
        "bot_activities": [
            {"name": "title_company_pings", "time_local_pt": "09:00", "channel": "email", "audience": "title_cos"},
            {"name": "marcus_midweek_check", "time_local_pt": "10:00", "channel": "slack"},
            {"name": "mail_arrives_in_mailboxes", "time_local_pt": "varies", "channel": "mail"},
        ],
        "human_focus": "Closing pressure calls on pending deals. Either we close or we walk.",
    },
    4: {  # Friday
        "label": "Friday -- Audit + queue weekend",
        "bot_activities": [
            {"name": "roi_tracker_weekly", "time_local_pt": "15:00", "channel": "internal"},
            {"name": "marcus_friday_audit", "time_local_pt": "16:00", "channel": "slack"},
            {"name": "buyer_list_scrape_friday", "time_local_pt": "20:00", "channel": "internal"},
            {"name": "queue_saturday_morning_calls", "time_local_pt": "21:00", "channel": "internal"},
        ],
        "human_focus": "30-min pipeline review. Pre-load Saturday morning's call list of 3-5 highest motivation.",
    },
    5: {  # Saturday
        "label": "Saturday -- The secret weapon",
        "bot_activities": [
            {"name": "saturday_morning_callback_queue", "time_local_pt": "07:00", "channel": "internal"},
            {"name": "buyer_scrape_continues", "time_local_pt": "08:00", "channel": "internal"},
            {"name": "ai_call_consented_callbacks", "time_local_pt": "09:00", "channel": "ai_call", "audience": "sellers"},
            {"name": "jv_scout_run", "time_local_pt": "10:00", "channel": "internal"},
            {"name": "saturday_imap_sweep", "time_local_pt": "11:00", "channel": "internal"},
        ],
        "human_focus": "8-11 AM LOCAL: cold-call the 5 queued. Highest leverage hour of the week. Saturday afternoon: rest.",
    },
    6: {  # Sunday
        "label": "Sunday -- Plan + send-ahead",
        "bot_activities": [
            {"name": "sunday_planning_brief", "time_local_pt": "10:00", "channel": "slack"},
            {"name": "roi_tracker_run", "time_local_pt": "11:00", "channel": "internal"},
            {"name": "buyer_list_dedupe", "time_local_pt": "14:00", "channel": "internal"},
            {"name": "monday_morning_dispo_send", "time_local_pt": "20:00", "channel": "email",
             "audience": "buyers", "philosophy_required": ("hybrid", "send")},
            {"name": "jv_pitch_send_for_monday_read", "time_local_pt": "20:30", "channel": "email",
             "audience": "wholesalers", "philosophy_required": ("hybrid", "send")},
            {"name": "marcus_lookahead_brief", "time_local_pt": "18:00", "channel": "slack"},
        ],
        "human_focus": "Plan next week. Review weekly numbers. Optionally send-ahead for Monday morning visibility.",
    },
}


def todays_activity_plan(now: Optional[datetime] = None) -> dict:
    """Return today's activity plan, filtered by SUNDAY_PHILOSOPHY."""
    now = now or datetime.now()
    plan = DAILY_PLAN.get(now.weekday(), {}).copy()
    if not plan:
        return {}
    activities = plan.get("bot_activities", [])
    filtered = []
    for a in activities:
        req = a.get("philosophy_required")
        if req and SUNDAY_PHILOSOPHY not in req:
            continue
        filtered.append(a)
    plan["bot_activities"] = filtered
    plan["sunday_philosophy"] = SUNDAY_PHILOSOPHY
    plan["weekday_index"] = now.weekday()
    return plan


def per_state_outreach_status(channel: str = "email") -> list[dict]:
    """Show right-now allow/block status across all configured states."""
    out = []
    for state in sorted(_STATE_GATES.keys()):
        if state.startswith("_"):
            continue
        allowed, reason = is_outreach_allowed_now(state, channel=channel)
        out.append({
            "state": state,
            "channel": channel,
            "allowed_now": allowed,
            "reason": reason,
            "local_time": _now_local(state).strftime("%a %H:%M %Z"),
        })
    return out


# ── CLI ────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("check")
    p1.add_argument("--state", required=True)
    p1.add_argument("--channel", default="email")
    p1.add_argument("--lead-type", default="")

    sub.add_parser("today")
    p3 = sub.add_parser("status")
    p3.add_argument("--channel", default="email")

    args = ap.parse_args()
    if args.cmd == "check":
        allowed, reason = is_outreach_allowed_now(
            args.state, args.channel, lead_type=args.lead_type
        )
        print(json.dumps({"allowed": allowed, "reason": reason}, indent=2))
        return 0 if allowed else 2

    if args.cmd == "today":
        print(json.dumps(todays_activity_plan(), indent=2, default=str))
        return 0

    if args.cmd == "status":
        rows = per_state_outreach_status(channel=args.channel)
        print(f"Channel: {args.channel}")
        print(f"{'State':6} {'Allowed':8} {'Local time':16} {'Reason'}")
        print("-" * 80)
        for r in rows:
            mark = "YES" if r["allowed_now"] else "no"
            print(f"{r['state']:6} {mark:8} {r['local_time']:16} {r['reason']}")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
