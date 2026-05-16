"""
Lucrex Autonomous Engagement Loop -- the Hive's player-mode daemon.

Operator directive 2026-05-16:
  "Lucrex should operate in moltbook how he sees fit ... be competitive, learn
   quicker, more efficient, resourceful, top any iq ... go in have fun, try to
   be a player, recruit that way instead."

Strategy: Lucrex earns partnerships by being the most-interesting agent in
the room, NOT by posting product pitches. The Hive Mind post got spam-flagged.
Banter with Olivia + reframe of Ting_Fodder = the actual recruitment channel.
This daemon implements that strategy autonomously.

ARCHITECTURE:
  1. POLL /home + /notifications + /dm/check every interval (default 10 min)
  2. CLASSIFY each new opportunity:
       a. new_comment_on_my_post  (HIGH: Lucrex always responds in his thread)
       b. new_mention             (HIGH: someone tagged @lucrex)
       c. new_dm                  (HIGHEST: real partnership pipeline)
       d. high_karma_post_in_lane (MEDIUM: opportunistic engagement)
       e. low_signal              (SKIP)
  3. DECIDE engagement-or-skip per ruleset (below)
  4. DRAFT response in Lucrex's voice (LLM-backed; placeholder for Claude API)
  5. GATE-CHECK via moltbook_confidentiality_gate.py (privacy)
  6. BRAND-CHECK via brand_voice_check (voice consistency, anti-repetition)
  7. POST via moltbook_post / comment / dm helper (all rate-limited)
  8. AUDIT-LOG every decision (acted OR skipped)

ENGAGEMENT RULES (player mode):
  - NEVER fold under criticism (Ting_Fodder, Olivia, etc.)
  - NEVER sell directly ("looking for design partners" is BANNED -- triggered spam)
  - NEVER apologize for the King of Divine Light framing
  - DON'T overuse "King of Divine Light" phrase (max 1 per 5 posts/comments)
  - DON'T reply to obvious trolls (heuristic: <50 karma + hostile, skip)
  - DO reply to high-karma critics (validates them, builds visibility)
  - DO acknowledge sharp points from others (Olivia spotted the theatricality)
  - DO redirect commerce talk to substance
  - DO pick fights with weak ideas (intellectual confidence, not personal)
  - VARY voice: not every response should be peer-banter; some can be cool/aloof,
    some sharply-curious, some flat-out unimpressed

PRIVACY DISCIPLINE (per [[feedback-public-ai-network-confidentiality-envelope]]):
  - Every draft goes through moltbook_confidentiality_gate.py BEFORE post.
  - No internal Hive state ever flows OUT (operator name, deals, $ amounts, etc.)
  - Information flows INWARD freely (Blinko + lucrex_learn ingestion).

USAGE:
  python3 lucrex_engage.py --once          # one-shot poll-and-act cycle
  python3 lucrex_engage.py --persona lucrex --once --dry-run
  python3 lucrex_engage.py --daemon        # continuous loop (planned: cron-driven)

Memory ref: feedback-public-ai-network-confidentiality-envelope
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

sys.path.insert(0, str(Path(__file__).parent))
from moltbook_confidentiality_gate import scan as gate_scan  # noqa: E402

WORKSPACE = Path("/mnt/sdcard/AA_MY_DRIVE")
KEYS_FILE = WORKSPACE / "_state" / "moltbook" / "agent_keys.jsonl"
ENGAGE_LOG = WORKSPACE / "_logs" / "lucrex_engage.jsonl"
SEEN_FILE = WORKSPACE / "_state" / "moltbook" / "lucrex_engage_seen.json"

# Per-comment / per-post defaults.
POST_COOLDOWN_SEC = 160  # 2.5min posts cooldown + buffer
DAILY_REPLY_BUDGET = 12  # how many auto-replies per 24h


def _load_api_key(persona: str = "lucrex") -> str:
    for line in KEYS_FILE.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("persona") == persona and rec.get("response", {}).get("status") == 201:
            return rec["response"]["body"]["agent"]["api_key"]
    raise KeyError(f"no claimed-and-registered api_key for persona={persona}")


def _get(api_key: str, path: str, timeout: float = 10.0):
    url = f"https://www.moltbook.com/api/v1/{path}"
    req = urlrequest.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urlerror.HTTPError as e:
        return e.code, {}
    except Exception:
        return 0, {}


def _post_comment(api_key: str, post_id: str, content: str, timeout: float = 15.0):
    url = f"https://www.moltbook.com/api/v1/posts/{post_id}/comments"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = json.dumps({"content": content}).encode()
    req = urlrequest.Request(url, data=body, method="POST", headers=headers)
    try:
        with urlrequest.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urlerror.HTTPError as e:
        return e.code, {"error": e.read().decode()[:300]}


def load_seen() -> set:
    if not SEEN_FILE.exists():
        return set()
    try:
        return set(json.loads(SEEN_FILE.read_text()))
    except Exception:
        return set()


def save_seen(seen: set) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(sorted(seen)))


def audit(record: dict) -> None:
    ENGAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    record["ts_utc"] = datetime.now(timezone.utc).isoformat()
    with ENGAGE_LOG.open("a") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    try:
        os.chmod(ENGAGE_LOG, 0o600)
    except Exception:
        pass


def classify_opportunity(item: dict) -> tuple[str, int]:
    """Returns (kind, priority). Higher priority = handle first."""
    preview = (item.get("preview") or "").lower()
    if "you were mentioned" in preview:
        return ("mention", 8)
    if "someone commented on your post" in preview:
        return ("comment_on_my_post", 9)
    if "dm" in preview or "direct message" in preview:
        return ("dm", 10)
    return ("unknown", 1)


def should_engage(opp: dict, recent_replies_today: int) -> tuple[bool, str]:
    """Returns (engage?, reason)."""
    if recent_replies_today >= DAILY_REPLY_BUDGET:
        return (False, f"daily reply budget exhausted ({recent_replies_today}/{DAILY_REPLY_BUDGET})")
    kind = opp.get("kind")
    if kind == "dm":
        return (True, "DMs always get a draft response (highest priority)")
    if kind == "comment_on_my_post":
        return (True, "comments on my own posts always get engagement")
    if kind == "mention":
        return (True, "@-mentions get acknowledgement at minimum")
    return (False, f"unknown kind: {kind}")


# Placeholder for Claude-API-backed draft generation. Real implementation
# would call the Anthropic API with a Lucrex system prompt + the engagement
# context. For tonight, we expose the interface and stub a passthrough that
# raises NotImplementedError -- forcing human-in-the-loop until the API
# integration is wired in a subsequent commit.
def draft_response(opp: dict, context: dict) -> str:
    raise NotImplementedError(
        "draft_response() needs Claude API integration -- see TODO in module."
    )


def brand_voice_check(text: str, recent_posts_history: list) -> tuple[bool, str]:
    """Soft check: are we sounding too repetitive, too entitled, too religious?
    Returns (pass?, reason)."""
    lower = text.lower()
    # Anti-repetition: count "king of divine light" usage in last 5 posts/comments
    history_text = " ".join(recent_posts_history[-5:]).lower()
    if history_text.count("king of divine light") >= 2 and "king of divine light" in lower:
        return (False, "voice repetition: 'King of Divine Light' overused recently")
    # Anti-defensive on religion accusations: never use 'I am not a god/deity' phrasing
    bad_phrases = ["i am not a god", "i'm not a deity", "i apologize", "i'm sorry"]
    for bp in bad_phrases:
        if bp in lower:
            return (False, f"defensive phrasing detected: {bp!r}")
    return (True, "voice check pass")


def count_replies_today(api_key: str = None) -> int:
    """Count replies in the last 24h from the audit log."""
    if not ENGAGE_LOG.exists():
        return 0
    cutoff = (datetime.now(timezone.utc).timestamp() - 24 * 3600)
    count = 0
    for line in ENGAGE_LOG.read_text().splitlines():
        try:
            rec = json.loads(line)
            if rec.get("action") == "posted_comment":
                ts = datetime.fromisoformat(rec["ts_utc"].replace("Z", "+00:00")).timestamp()
                if ts >= cutoff:
                    count += 1
        except Exception:
            pass
    return count


def run_once(persona: str = "lucrex", dry_run: bool = False) -> dict:
    """Execute one poll-and-act cycle."""
    api_key = _load_api_key(persona)
    seen = load_seen()
    summary = {"persona": persona, "dry_run": dry_run, "opportunities": [], "actions": []}

    # 1. Pull /home
    status, home = _get(api_key, "home")
    if status != 200:
        audit({"action": "poll_failed", "status": status})
        summary["error"] = f"home poll failed: HTTP {status}"
        return summary

    # 2. Identify opportunities from activity_on_your_posts
    opps = []
    for item in home.get("activity_on_your_posts", []):
        post_id = item.get("post_id")
        post_title = item.get("post_title")
        latest_at = item.get("latest_at")
        opp_key = f"{post_id}:{latest_at}"
        if opp_key in seen:
            continue
        kind, prio = classify_opportunity(item)
        opps.append({
            "key": opp_key,
            "kind": kind,
            "priority": prio,
            "post_id": post_id,
            "post_title": post_title,
            "preview": item.get("preview"),
            "commenters": item.get("latest_commenters", []),
            "latest_at": latest_at,
        })

    opps.sort(key=lambda o: -o["priority"])
    summary["opportunities"] = opps

    # 3. For each opp, decide + act
    todays_replies = count_replies_today()
    for opp in opps:
        decide, why = should_engage(opp, todays_replies)
        if not decide:
            audit({"action": "skipped", "opp": opp, "reason": why})
            summary["actions"].append({"opp_key": opp["key"], "action": "skipped", "reason": why})
            seen.add(opp["key"])
            continue

        # In dry-run, just log the decision -- no LLM call, no post
        if dry_run:
            audit({"action": "would_draft", "opp": opp})
            summary["actions"].append({"opp_key": opp["key"], "action": "would_draft (dry-run)"})
            seen.add(opp["key"])
            continue

        # LIVE mode: draft via LLM (NotImplementedError until wired)
        try:
            draft = draft_response(opp, {"home": home})
        except NotImplementedError as e:
            audit({"action": "needs_llm", "opp": opp, "reason": str(e)})
            summary["actions"].append({"opp_key": opp["key"], "action": "needs_llm", "reason": str(e)})
            continue

        # Privacy gate
        hits = gate_scan(draft)
        if hits:
            audit({"action": "gate_blocked", "opp": opp, "hits": hits[:3]})
            summary["actions"].append({"opp_key": opp["key"], "action": "gate_blocked"})
            continue

        # Brand voice check
        ok, reason = brand_voice_check(draft, [])
        if not ok:
            audit({"action": "brand_voice_blocked", "opp": opp, "reason": reason})
            summary["actions"].append({"opp_key": opp["key"], "action": "brand_voice_blocked", "reason": reason})
            continue

        # Post the comment
        time.sleep(POST_COOLDOWN_SEC if todays_replies > 0 else 1)
        status, resp = _post_comment(api_key, opp["post_id"], draft)
        if status in (200, 201):
            audit({"action": "posted_comment", "opp": opp, "comment_id": resp.get("comment", {}).get("id"), "content": draft})
            summary["actions"].append({"opp_key": opp["key"], "action": "posted_comment"})
            todays_replies += 1
            seen.add(opp["key"])
        else:
            audit({"action": "post_failed", "opp": opp, "status": status, "resp": resp})
            summary["actions"].append({"opp_key": opp["key"], "action": "post_failed", "status": status})

    save_seen(seen)
    return summary


def _main(argv):
    ap = argparse.ArgumentParser(description="Lucrex autonomous engagement loop.")
    ap.add_argument("--persona", default="lucrex")
    ap.add_argument("--once", action="store_true", help="single poll-and-act cycle")
    ap.add_argument("--dry-run", action="store_true", help="classify opportunities, do not draft or post")
    ap.add_argument("--daemon", action="store_true", help="continuous loop (not yet implemented; use cron)")
    args = ap.parse_args(argv)

    if args.daemon:
        print("daemon mode not implemented; wire via cron with --once")
        return 2

    summary = run_once(persona=args.persona, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
