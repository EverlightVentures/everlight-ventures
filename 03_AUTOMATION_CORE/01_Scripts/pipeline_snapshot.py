"""pipeline_snapshot -- every 15 min, post the live wholesale pipeline to Slack.

Posts to #broker-pipeline in a single pinned-style message that gives the
observer (owner) the "glance during the day" view:

    PIPELINE SNAPSHOT -- 09:15 AM PT (Apr 24)
    =========================================
    TOTAL LEADS:   550  ( +0 since last check )
    CONTACTED:     38 active sequences
    REPLIED:       0 this week
    CLOSED:        0 this week

    BY STATE:
      GA  144 | 24 contactable | 15 in-sequence | 0 replied
      TX  156 | 25 contactable | 13 in-sequence | 0 replied
      MO   81 | 18 contactable |  8 in-sequence | 0 replied
      FL   96 | 14 contactable |  2 in-sequence | 0 replied

    HOT LEADS  (magnet clicks in last 24h):
      pilot_4fc133  637 MCGRUDER ST NE, ATLANTA GA   clicks=5  (top!)

    NEXT TOUCHES (next hour):
      Jarek Tadla   Jacksonville FL     step 3  email
      Donna Brooks  St Louis MO         step 3  email

Cursor-tracked so the delta line shows real change each run.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta

ROOT = pathlib.Path("/mnt/sdcard/AA_MY_DRIVE")
LEADS_DB = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Broker_OS" / "wholesale_agent" / "leads_db.json"
EVENTS   = ROOT / "_logs" / "dispatcher" / "events.jsonl"
STATE    = ROOT / "_logs" / "pipeline_snapshot.state.json"
CREDS    = ROOT / "03_AUTOMATION_CORE" / "03_Credentials" / ".env"

CHANNEL_ID = os.environ.get("PIPELINE_SNAPSHOT_CHANNEL", "C0AN7FTTK2R")  # #broker-pipeline
STALE_TOUCHES_H = 72  # "in-sequence" means last touch < 72h ago

INST_TOKENS = {"LLC", "TRUST", "INC", "CORP", " LP", "BANK", "AUTHORITY", "DIOCESE",
               "DEVELOPMENT", "ASSOCIATION", "NEIGHBORHOOD", "REALTY", "HOLDINGS",
               "INVESTMENTS", "PROPERTIES", "PARTNERS"}


def _slack_token() -> str:
    t = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if t: return t
    if CREDS.exists():
        m = re.search(r"^SLACK_BOT_TOKEN\s*=\s*['\"]?(xoxb-[A-Za-z0-9\-]+)['\"]?",
                      CREDS.read_text(), re.M)
        if m: return m.group(1)
    return ""


def _pt_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:
        return datetime.now(timezone.utc) - timedelta(hours=8)


def _is_individual(lead: dict) -> bool:
    nm = (lead.get("owner_name") or "").upper()
    return not any(t in nm for t in INST_TOKENS)


def _has_contact(lead: dict) -> bool:
    return bool(lead.get("email") or lead.get("owner_email")
                or lead.get("phone") or lead.get("owner_phone"))


def _in_sequence(lead: dict, now: datetime) -> bool:
    if lead.get("status") != "contacted":
        return False
    last = lead.get("last_outreach") or ""
    if not last:
        return False
    try:
        ts = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return (now - ts) < timedelta(hours=STALE_TOUCHES_H)
    except Exception:
        return False


def _load_prev_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"total": 0, "contacted": 0, "replied": 0, "ts": ""}


def _save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s))


def _recent_magnet_clicks(hours: int = 24) -> Counter:
    counts: Counter = Counter()
    if not EVENTS.exists():
        return counts
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    with EVENTS.open("r", encoding="utf-8") as f:
        for ln in f:
            try:
                row = json.loads(ln)
            except Exception:
                continue
            t = row.get("type", "")
            if t != "magnet_click":
                continue
            try:
                ts = datetime.fromisoformat(row.get("ts", "").replace("Z", "+00:00"))
            except Exception:
                continue
            if ts < cutoff:
                continue
            lid = (row.get("payload", {}) or {}).get("lead_id") or ""
            if lid and lid != "?":
                counts[lid] += 1
    return counts


def _next_touches_eta(leads: list[dict], now: datetime, limit: int = 5) -> list[dict]:
    """Pick the leads most likely to get their next touch in the next hour."""
    BELFORT_DELAY_H = {0: 0, 1: 4, 2: 24, 3: 48, 4: 72, 5: 96, 6: 120}
    due: list[tuple[float, dict]] = []
    for l in leads:
        if l.get("status") == "dead": continue
        step = l.get("sequence_step", 0)
        if step >= 7: continue
        if not _has_contact(l): continue
        last = l.get("last_outreach") or l.get("created_at") or ""
        try:
            ts = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        expected_delay = BELFORT_DELAY_H.get(step, 24)
        next_due = ts + timedelta(hours=expected_delay)
        hours_to_due = (next_due - now).total_seconds() / 3600
        due.append((hours_to_due, l))
    due.sort(key=lambda t: t[0])
    out = []
    for h, l in due[:limit]:
        out.append({
            "name": (l.get("owner_name") or "Unknown").title()[:22],
            "city": (l.get("city") or "?")[:18],
            "state": (l.get("state") or "?").upper(),
            "step": l.get("sequence_step", 0),
            "eta_hours": h,
        })
    return out


def build_snapshot() -> str:
    if not LEADS_DB.exists():
        return "Pipeline snapshot: leads_db.json not found"
    leads = json.loads(LEADS_DB.read_text())
    now = datetime.now(timezone.utc)
    now_pt = _pt_now()

    # Overall counts
    total = len(leads)
    by_state = Counter((l.get("state") or "?").upper() for l in leads)
    contactable_by_state: Counter = Counter()
    in_seq_by_state: Counter = Counter()
    replied_by_state: Counter = Counter()
    dead_by_state: Counter = Counter()
    for l in leads:
        st = (l.get("state") or "?").upper()
        if _is_individual(l) and _has_contact(l):
            contactable_by_state[st] += 1
        if _in_sequence(l, now):
            in_seq_by_state[st] += 1
        if l.get("reply_received"):
            replied_by_state[st] += 1
        if l.get("status") == "dead":
            dead_by_state[st] += 1

    contacted_total = sum(1 for l in leads if l.get("status") == "contacted")
    replied_total   = sum(replied_by_state.values())
    closed_total    = sum(1 for l in leads if l.get("status") == "closed")

    # Delta since last run
    prev = _load_prev_state()
    delta_total     = total - prev.get("total", 0)
    delta_contacted = contacted_total - prev.get("contacted", 0)
    delta_replied   = replied_total - prev.get("replied", 0)

    # Hot leads (magnet clicks in last 24h)
    clicks = _recent_magnet_clicks(24)
    hot = []
    lead_by_id = {str(l.get("id", "")): l for l in leads}
    for lid, n in clicks.most_common(5):
        l = lead_by_id.get(str(lid))
        if not l: continue
        hot.append((n, l))

    # Next touches in next hour
    upcoming = _next_touches_eta(leads, now, limit=5)

    # Render
    lines = []
    lines.append(f"*PIPELINE SNAPSHOT* -- {now_pt:%a %b %-d, %-I:%M %p PT}")
    lines.append("=" * 44)
    lines.append(f"*Total leads:*   {total:<4}  ({delta_total:+d} since last)")
    lines.append(f"*Contactable:*   {sum(contactable_by_state.values())}")
    lines.append(f"*In-sequence:*   {contacted_total:<4}  ({delta_contacted:+d})")
    lines.append(f"*Replied:*       {replied_total:<4}  ({delta_replied:+d})")
    lines.append(f"*Closed:*        {closed_total}")
    lines.append("")
    lines.append("*By state:*  `total | contactable | in-seq | replied`")
    priority = ["GA", "TX", "MO", "FL", "AZ", "TN"]
    for st in priority:
        if st not in by_state: continue
        lines.append(
            f"  `{st}` {by_state[st]:>3}  |  {contactable_by_state[st]:>3}  |  "
            f"{in_seq_by_state[st]:>3}  |  {replied_by_state[st]:>3}"
        )

    if hot:
        lines.append("")
        lines.append("*:fire: Hot leads* (magnet clicks in last 24h):")
        for n, l in hot:
            addr = (l.get("address") or "")[:38]
            st = (l.get("state") or "").upper()
            lines.append(f"  `{l.get('id','')}`  {addr} ({st})  clicks={n}")

    if upcoming:
        lines.append("")
        lines.append("*Next touches* (due within ~1h):")
        for u in upcoming:
            eta = f"{u['eta_hours']:+.1f}h"
            lines.append(f"  step {u['step']}  {u['name']:22s}  {u['city']}, {u['state']}   {eta}")

    # Footer: links to key resources
    lines.append("")
    lines.append(
        "_live dashboard:_  http://127.0.0.1:2200/broker/  "
        "_|_  _magnet:_  /broker/cashoffer/?lead_id=<X>"
    )
    text = "\n".join(lines)

    _save_state({
        "total": total, "contacted": contacted_total, "replied": replied_total,
        "ts": now.isoformat(),
    })
    return text


def post(text: str, channel: str = CHANNEL_ID) -> bool:
    token = _slack_token()
    if not token:
        sys.stderr.write("no SLACK_BOT_TOKEN\n")
        return False
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": channel, "text": text, "mrkdwn": True}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=utf-8"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=8).read()
        resp = json.loads(r)
        if not resp.get("ok"):
            sys.stderr.write(f"slack err: {resp}\n")
            return False
        return True
    except Exception as e:
        sys.stderr.write(f"slack post err: {e}\n")
        return False


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print snapshot instead of posting")
    ap.add_argument("--channel", default=CHANNEL_ID, help="Slack channel id or #name")
    args = ap.parse_args()
    text = build_snapshot()
    if args.dry_run:
        print(text)
        return
    ok = post(text, channel=args.channel)
    print("posted" if ok else "failed")


if __name__ == "__main__":
    main()
