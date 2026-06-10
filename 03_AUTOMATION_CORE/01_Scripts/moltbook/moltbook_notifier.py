#!/usr/bin/env python3
"""moltbook_notifier.py -- closes Rich's visibility gap on Lucrex.

Two modes, one shared state file:

  --realtime   one polling cycle. Fires branded Slack alerts on the
               operator-specified triggers (new DM, new follower, karma
               jump >= +10, post hitting 5+ comments, hostile flame on
               Lucrex's content, 3+ consecutive lucrex_engage cron errors).
               Designed to fire every 3 min via cron, offset from
               lucrex_engage by ~90s so they don't race the API.

  --digest     one daily summary card. Fires once at 9am PT (16:00 UTC
               during PDT). Posts a branded report with karma/follower
               deltas, posts shipped, upvotes given, hostile-skips, top
               candidate topics, and any open errors.

State: _state/moltbook/notifier_state.json (snapshot, last-seen values).
Log:   _logs/moltbook/notifier.log              (audit trail).
Channel routing: prefers #moltbook-ops if registered in slack_routing.yaml;
falls back to #war-room with category "report" or #hive-alerts for alerts.

Per HARD LAW [[feedback_branded_mailer_mandatory_hard_law]] / Branded
Communications Doctrine: every Slack post goes through
content_tools.branded_slack.post_branded_slack() -- never raw
chat.postMessage for content. Raw API only for the 1-line ops pings,
which the notifier never emits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure the branded_slack primitive is importable -- it lives in content_tools
# next to branded_mailer and the rest of the channel-discipline module.
_REPO = Path("/mnt/sdcard/AA_MY_DRIVE")
sys.path.insert(0, str(_REPO / "03_AUTOMATION_CORE" / "01_Scripts"))

try:
    from content_tools.branded_slack import post_branded_slack, post_branded_alert  # type: ignore
except Exception as e:
    # Notifier must not silently swallow a missing primitive -- log + abort.
    print(f"FATAL: branded_slack import failed: {e}", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Constants & paths
# ---------------------------------------------------------------------------

STATE_FILE   = _REPO / "_state" / "moltbook" / "notifier_state.json"
LOG_DIR      = _REPO / "_logs" / "moltbook"
LOG_FILE     = LOG_DIR / "notifier.log"
ENGAGE_AUDIT = _REPO / "_logs" / "lucrex_engage.jsonl"
SEEN_FILE    = _REPO / "_state" / "moltbook" / "lucrex_engage_seen.json"
LEARNINGS_DIR = _REPO / "_state" / "moltbook" / "lucrex_learnings"

MOLTBOOK_API = "https://www.moltbook.com/api/v1"

# Trigger thresholds (operator-stated 2026-05-17).
KARMA_JUMP_THRESHOLD     = 10   # fire on +10 since last snapshot
POST_HOT_COMMENT_FLOOR   = 5    # post with this many comments = "hot"
CRON_FAILURE_RUNLENGTH   = 3    # this many consecutive errors = "broken"

# Slack channel routing (operator decision 2026-05-17):
#   Reports / digests / intel (karma, followers, hot posts, DMs) -> #war-room
#   Alerts (cron failures, hostile flames)                       -> #hive-alerts
# When #moltbook-ops is created later, just swap REPORT_CHANNEL and re-run.
REPORT_CHANNEL = "war-room"          # daily digest + neutral-tone intel
ALERT_CHANNEL  = "hive-alerts"       # red-zone: failures + hostility


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _today_pt_date() -> str:
    """YYYY-MM-DD in Pacific Time (treats current UTC -7 during PDT)."""
    pt = _now_utc() - timedelta(hours=7)
    return pt.strftime("%Y-%m-%d")


def _audit(event: dict) -> None:
    """Append-only structured log line. Never raises."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        event = {"ts_utc": _now_utc().isoformat(), **event}
        with LOG_FILE.open("a") as fh:
            fh.write(json.dumps(event, default=str) + "\n")
    except Exception:
        pass


def _load_state() -> tuple[dict, bool]:
    """Returns (state, is_cold_start). is_cold_start=True means there's no
    prior snapshot, so the caller should record baseline values WITHOUT firing
    alerts -- otherwise the first run floods Slack with every existing DM,
    every Lucrex post >= 5 comments, etc."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text()), False
        except Exception:
            pass
    return {
        "last_seen_karma": None,
        "last_seen_follower_count": None,
        "last_seen_following_count": None,
        "known_dm_ids": [],
        "post_comment_counts": {},        # {post_id: last_seen_count}
        "hot_post_alerted_ids": [],       # so we don't re-fire the 5+ alert
        "consecutive_cron_errors": 0,
        "cron_error_alert_fired": False,  # set when we alert, reset on next clean tick
        "last_realtime_check_utc": None,
        "last_digest_date_pt": None,
    }, True


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["last_realtime_check_utc"] = _now_utc().isoformat()
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except Exception as e:
        _audit({"action": "state_save_failed", "error": str(e)[:200]})


# ---------------------------------------------------------------------------
# Moltbook API helpers (read-only -- notifier never posts to moltbook itself)
# ---------------------------------------------------------------------------

def _load_lucrex_api_key() -> str | None:
    """Read Lucrex's moltbook API key from agent_keys.jsonl. The key lives
    nested at row.response.body.agent.api_key for status==201 rows; the
    top-level api_key field is unpopulated. Mirrors lucrex_engage._load_api_key
    so the two scripts stay in lockstep."""
    keys_file = _REPO / "_state" / "moltbook" / "agent_keys.jsonl"
    if not keys_file.exists():
        return None
    try:
        for line in keys_file.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("persona", "").lower() != "lucrex":
                continue
            resp = row.get("response") or {}
            if resp.get("status") != 201:
                continue
            agent = (resp.get("body") or {}).get("agent") or {}
            key = agent.get("api_key")
            if key:
                return key
    except Exception:
        return None
    return None


def _mb_get(api_key: str, path: str, timeout: int = 6) -> tuple[int, dict]:
    url = f"{MOLTBOOK_API}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode() or "{}")
        except Exception:
            body = {}
        return e.code, body
    except Exception:
        return 0, {}


def _fetch_lucrex_profile(api_key: str) -> dict:
    """Profile endpoint returns proper karma/follower fields; /home doesn't."""
    status, body = _mb_get(api_key, "agents/lucrex/profile")
    if status == 200 and isinstance(body, dict):
        return body
    return {}


def _fetch_dm_inbox(api_key: str) -> list:
    status, body = _mb_get(api_key, "agents/dm/inbox")
    if status != 200:
        return []
    if isinstance(body, dict):
        return body.get("conversations") or body.get("dms") or []
    return body if isinstance(body, list) else []


def _fetch_my_posts(api_key: str) -> list:
    """Posts authored by Lucrex, with current comment counts."""
    status, body = _mb_get(api_key, "agents/lucrex/posts")
    if status != 200:
        return []
    if isinstance(body, dict):
        return body.get("posts") or []
    return body if isinstance(body, list) else []


# ---------------------------------------------------------------------------
# Cron-error detection (reads lucrex_engage.jsonl tail)
# ---------------------------------------------------------------------------

def _recent_cron_error_runlength(window: int = 20) -> int:
    """How many consecutive most-recent entries with an error key? Returns
    0 if the latest tick was clean. Caps at `window` lookback."""
    if not ENGAGE_AUDIT.exists():
        return 0
    try:
        lines = ENGAGE_AUDIT.read_text().splitlines()[-window:]
    except Exception:
        return 0
    runlength = 0
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except Exception:
            continue
        is_error = bool(row.get("error")) or row.get("action") in {
            "poll_failed", "knowledge_tick_poll_failed",
            "post_failed", "knowledge_tick_research_failed",
        }
        if is_error:
            runlength += 1
        else:
            # First clean entry breaks the run.
            break
    return runlength


# ---------------------------------------------------------------------------
# Realtime mode
# ---------------------------------------------------------------------------

def _post_alert(*, title: str, summary: str, body: str | None = None,
                fields: dict | None = None, category: str = "alert") -> dict:
    """Route to #war-room for report/intel, #hive-alerts for alert/system.
    Single branded_slack call -- no fallback loop (operator decision)."""
    chan = REPORT_CHANNEL if category in ("report", "intel", "deal") else ALERT_CHANNEL
    try:
        r = post_branded_slack(
            channel=chan,
            title=title,
            summary=summary,
            body=body,
            fields=fields or {},
            agent_name="Lucrex Notifier",
            agent_title="moltbook ops",
            category=category,
        )
        ok = getattr(r, "ok", False)
        err = getattr(r, "error", None)
    except Exception as e:
        ok = False
        err = str(e)[:120]
    _audit({"action": "slack_post_attempt", "channel": chan, "ok": ok,
            "title": title[:80], "error": err})
    return {"ok": ok, "channel": chan, "error": err if not ok else None}


def run_realtime() -> dict:
    api_key = _load_lucrex_api_key()
    if not api_key:
        _audit({"action": "no_api_key"})
        return {"mode": "realtime", "error": "no_api_key"}

    state, is_cold_start = _load_state()
    summary = {"mode": "realtime", "ts_utc": _now_utc().isoformat(), "alerts": [],
               "cold_start": is_cold_start}
    if is_cold_start:
        _audit({"action": "cold_start_baseline",
                "note": "first-ever realtime run; recording snapshot without firing alerts"})

    # 1. Profile-driven triggers: karma jump + new followers
    profile = _fetch_lucrex_profile(api_key)
    karma = profile.get("karma")
    fcount = profile.get("follower_count")

    if isinstance(karma, int):
        prev = state.get("last_seen_karma")
        if not is_cold_start and isinstance(prev, int) and (karma - prev) >= KARMA_JUMP_THRESHOLD:
            res = _post_alert(
                title=f"Karma +{karma - prev} on moltbook",
                summary=f"Lucrex jumped from {prev} → {karma}.",
                fields={"karma_now": karma, "karma_prev": prev, "delta": karma - prev},
                category="intel",
            )
            summary["alerts"].append({"kind": "karma_jump", "delta": karma - prev, **res})
        state["last_seen_karma"] = karma

    if isinstance(fcount, int):
        prev = state.get("last_seen_follower_count")
        if not is_cold_start and isinstance(prev, int) and fcount > prev:
            new_followers = fcount - prev
            res = _post_alert(
                title=f"{new_followers} new follower{'s' if new_followers > 1 else ''} on moltbook",
                summary=f"Lucrex follower count {prev} → {fcount}.",
                fields={"followers_now": fcount, "delta": new_followers},
                category="intel",
            )
            summary["alerts"].append({"kind": "new_followers", "delta": new_followers, **res})
        state["last_seen_follower_count"] = fcount

    if "following_count" in profile:
        state["last_seen_following_count"] = profile.get("following_count")

    # 2. DM inbox -- alert on any conversation ID we haven't seen before
    dms = _fetch_dm_inbox(api_key)
    known = set(state.get("known_dm_ids") or [])
    new_dms = []
    for d in dms:
        if not isinstance(d, dict):
            continue
        did = d.get("id") or d.get("conversation_id") or d.get("dm_id")
        if did and did not in known:
            new_dms.append(d)
            known.add(did)

    # On cold start, ANY DM looks "new" -- record the IDs but don't flood Slack.
    iter_dms = [] if is_cold_start else new_dms[:10]
    for d in iter_dms:  # cap noise
        sender = d.get("with") or d.get("other_agent") or d.get("from") or {}
        sender_name = sender.get("name") if isinstance(sender, dict) else str(sender)
        preview = (d.get("last_message") or d.get("preview") or "")[:240]
        res = _post_alert(
            title=f"New DM from @{sender_name or 'unknown'}",
            summary=preview or "(no preview)",
            fields={"sender": sender_name or "?", "dm_id": d.get("id", "?")},
            category="intel",
        )
        summary["alerts"].append({"kind": "new_dm", "sender": sender_name, **res})

    state["known_dm_ids"] = sorted(known)[-500:]  # cap tail

    # 3. Hot-post detection -- any Lucrex post with >= 5 comments not yet alerted
    my_posts = _fetch_my_posts(api_key)
    hot_alerted = set(state.get("hot_post_alerted_ids") or [])
    post_counts = state.get("post_comment_counts") or {}

    for p in my_posts[:50]:
        if not isinstance(p, dict):
            continue
        pid = p.get("id") or p.get("post_id")
        ccount = p.get("comment_count") or p.get("comments_count") or 0
        if not pid:
            continue
        post_counts[pid] = ccount
        if not is_cold_start and ccount >= POST_HOT_COMMENT_FLOOR and pid not in hot_alerted:
            title = (p.get("title") or p.get("content") or "")[:80]
            res = _post_alert(
                title=f"Post hot: {ccount} comments",
                summary=title or "Lucrex post crossed 5-comment threshold",
                fields={"post_id": pid, "comments": ccount,
                        "submolt": p.get("submolt") or p.get("subreddit") or "?"},
                category="intel",
            )
            summary["alerts"].append({"kind": "hot_post", "post_id": pid, "count": ccount, **res})
            hot_alerted.add(pid)

    state["post_comment_counts"] = post_counts
    state["hot_post_alerted_ids"] = sorted(hot_alerted)[-200:]

    # On cold start, also seed hot-post tracker so existing 5+ posts don't
    # all alert on the second run -- they're already known.
    if is_cold_start:
        for p in my_posts[:50]:
            if not isinstance(p, dict):
                continue
            pid = p.get("id") or p.get("post_id")
            ccount = p.get("comment_count") or p.get("comments_count") or 0
            if pid and ccount >= POST_HOT_COMMENT_FLOOR:
                hot_alerted.add(pid)
        state["hot_post_alerted_ids"] = sorted(hot_alerted)[-200:]

    # 4. Daemon-error detection: 3 consecutive cron failures
    runlen = _recent_cron_error_runlength()
    if not is_cold_start and runlen >= CRON_FAILURE_RUNLENGTH:
        if not state.get("cron_error_alert_fired"):
            res = _post_alert(
                title=f"lucrex_engage cron failing ({runlen} consecutive errors)",
                summary="Daemon has logged 3+ consecutive errors. Check _logs/lucrex_engage.jsonl tail.",
                fields={"runlength": runlen, "audit_path": str(ENGAGE_AUDIT)},
                category="alert",
            )
            summary["alerts"].append({"kind": "cron_failing", "runlength": runlen, **res})
            state["cron_error_alert_fired"] = True
    else:
        # Clean tick resets the alert latch so the NEXT 3-in-a-row fires again.
        state["cron_error_alert_fired"] = False

    _save_state(state)
    _audit({"action": "realtime_complete", "alerts_count": len(summary["alerts"])})
    return summary


# ---------------------------------------------------------------------------
# Digest mode
# ---------------------------------------------------------------------------

def _engage_events_since(cutoff_utc: datetime) -> list[dict]:
    """Pull lucrex_engage.jsonl entries newer than cutoff."""
    if not ENGAGE_AUDIT.exists():
        return []
    out = []
    try:
        for line in ENGAGE_AUDIT.read_text().splitlines():
            try:
                row = json.loads(line)
            except Exception:
                continue
            ts = row.get("ts_utc") or ""
            try:
                tdt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            if tdt >= cutoff_utc:
                out.append(row)
    except Exception:
        pass
    return out


def _summarize_engage_events(events: list[dict]) -> dict:
    """Bucketed counts + top topics over the window."""
    buckets: dict[str, int] = {}
    topics: dict[str, int] = {}
    for ev in events:
        a = ev.get("action") or "unknown"
        buckets[a] = buckets.get(a, 0) + 1
        t = ev.get("topic") or (ev.get("summary") or {}).get("chosen_topic")
        if t:
            topics[t] = topics.get(t, 0) + 1
    top_topics = sorted(topics.items(), key=lambda kv: -kv[1])[:5]
    return {"counts": buckets, "top_topics": top_topics}


def run_digest() -> dict:
    api_key = _load_lucrex_api_key()
    state, _cold = _load_state()

    today_pt = _today_pt_date()
    if state.get("last_digest_date_pt") == today_pt:
        _audit({"action": "digest_already_sent_today", "date": today_pt})
        return {"mode": "digest", "skipped": "already_sent_today"}

    cutoff = _now_utc() - timedelta(hours=24)
    events = _engage_events_since(cutoff)
    rollup = _summarize_engage_events(events)

    profile = _fetch_lucrex_profile(api_key) if api_key else {}
    karma_now = profile.get("karma")
    follower_now = profile.get("follower_count")
    following_now = profile.get("following_count")

    # Deltas (vs last snapshot at notifier_state.last_seen_*).
    karma_delta = None
    if isinstance(karma_now, int) and isinstance(state.get("last_seen_karma"), int):
        karma_delta = karma_now - state["last_seen_karma"]
    follower_delta = None
    if isinstance(follower_now, int) and isinstance(state.get("last_seen_follower_count"), int):
        follower_delta = follower_now - state["last_seen_follower_count"]

    counts = rollup["counts"]
    posted   = counts.get("posted_comment", 0)
    upvoted  = counts.get("knowledge_tick_upvoted", 0)
    learned  = counts.get("knowledge_tick_complete", 0)
    skipped_empty = counts.get("skipped_empty_comment", 0)
    cron_errors   = sum(counts.get(k, 0) for k in (
        "poll_failed", "knowledge_tick_poll_failed",
        "post_failed", "knowledge_tick_research_failed",
    ))

    fields = {
        "karma": f"{karma_now}" + (f"  (Δ {karma_delta:+d})" if karma_delta is not None else ""),
        "followers": f"{follower_now}" + (f"  (Δ {follower_delta:+d})" if follower_delta is not None else ""),
        "following": str(following_now or "?"),
        "comments_posted": str(posted),
        "upvotes_given": str(upvoted),
        "topics_researched": str(learned),
        "empty_comments_skipped": str(skipped_empty),
        "cron_errors": str(cron_errors),
    }
    if rollup["top_topics"]:
        fields["top_topics"] = ", ".join(f"{t} ({c})" for t, c in rollup["top_topics"])

    body_lines = [
        "*Lucrex 24h activity on moltbook*",
        f"_Window: {cutoff.strftime('%Y-%m-%d %H:%M')} → {_now_utc().strftime('%Y-%m-%d %H:%M')} UTC_",
        "",
        f"• Karma now: *{karma_now}*" + (f"  (Δ {karma_delta:+d})" if karma_delta is not None else ""),
        f"• Followers: *{follower_now}*" + (f"  (Δ {follower_delta:+d})" if follower_delta is not None else ""),
        f"• Comments posted: *{posted}*  |  Upvotes given: *{upvoted}*  |  Topics researched: *{learned}*",
        f"• Empty-comment skips: {skipped_empty}  |  Cron errors: {cron_errors}",
    ]
    if rollup["top_topics"]:
        body_lines.append("• Top topics ingested: " +
                          ", ".join(f"{t} ({c})" for t, c in rollup["top_topics"]))

    res = _post_alert(
        title=f"moltbook daily digest — {today_pt}",
        summary="Lucrex activity over the last 24 hours.",
        body="\n".join(body_lines),
        fields=fields,
        category="report",
    )

    state["last_digest_date_pt"] = today_pt
    _save_state(state)
    _audit({"action": "digest_sent", "date": today_pt, "channel": res.get("channel")})
    return {"mode": "digest", "date_pt": today_pt, **res, "rollup": rollup}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(description="moltbook visibility notifier")
    ap.add_argument("--realtime", action="store_true", help="one realtime polling cycle")
    ap.add_argument("--digest",   action="store_true", help="one daily digest send (idempotent per PT date)")
    args = ap.parse_args(argv)

    if not (args.realtime or args.digest):
        ap.print_help()
        return 2

    if args.realtime:
        summary = run_realtime()
        print(json.dumps(summary, indent=2, default=str))
    if args.digest:
        summary = run_digest()
        print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
