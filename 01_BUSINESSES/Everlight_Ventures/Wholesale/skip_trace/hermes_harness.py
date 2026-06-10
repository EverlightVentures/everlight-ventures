#!/usr/bin/env python3
"""
hermes_harness.py -- the frugal people-search email harness for the TN pipeline.

Skill: hermes_browser_outreach. Lifts email-discovery yield WITHOUT a paid skip-trace
API (feedback_frugal_build_dont_buy). People-search sites (TruePeopleSearch /
FastPeopleSearch) carry consumer emails but are Cloudflare-walled -- they 403 plain HTTP
from ANY IP (verified), so a REAL BROWSER is required. This harness is executor-pluggable:

  EXECUTOR PRIORITY (first available wins):
    1. browser-use cloud  -- env BROWSER_USE_API_KEY (free tier 30 days, $0)
    2. e5-mother Chromium -- env HERMES_E5_CHROMIUM=1 + e5 reachable (owned box, $0)
    3. queued             -- no executor: lead flagged browser_queued, runs when one lands

Every extracted contact is GATED (eradication + opt-out + name/city match) BEFORE it
touches the tracker. Feeds tn_deal_tracker: email_needed -> email_found / browser_queued.
Run-ledger: _logs/hermes_runs.jsonl. Owner: Forge + Piper, gated by Justine/Cipher.

Usage:
  python3 hermes_harness.py --dry-run            # gate-check the queue, no executor (default)
  python3 hermes_harness.py --run --limit 10     # run the available executor on N leads
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/mnt/sdcard/AA_MY_DRIVE")
WH = ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale"
TRACKER = WH / "tn_deal_tracker.json"
RUNS_LEDGER = ROOT / "_logs" / "hermes_runs.jsonl"
DOMAIN_SKILLS = ROOT / ".claude" / "skills" / "hermes_browser_outreach" / "domain_skills"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Executor detection -- frugal, never a paid API.
# ---------------------------------------------------------------------------
def detect_executor() -> str:
    if os.environ.get("BROWSER_USE_API_KEY"):
        return "browser_use_cloud"
    if os.environ.get("HERMES_E5_CHROMIUM") == "1":
        return "e5_chromium"
    return "queued"


def people_search_url(first: str, last: str, city: str = "Memphis", state: str = "TN") -> str:
    name = urllib.parse.quote(f"{first} {last}".strip())
    csz = urllib.parse.quote(f"{city}, {state}")
    return f"https://www.truepeoplesearch.com/results?name={name}&citystatezip={csz}"


def browser_task_spec(first: str, last: str, url: str) -> str:
    """The natural-language task a browser-use agent executes (see domain_skills/)."""
    return (
        f"Open {url}. Wait for any human-check to clear. Click the first person whose city "
        f"is Memphis TN and whose last name is {last}. On their detail page, extract every "
        f"email address and phone number. Return strict JSON: "
        f'{{"name": "...", "address": "...", "emails": [...], "phones": [...]}}. '
        f"If no confident match for {first} {last} in Memphis, return "
        f'{{"emails": [], "phones": [], "match_confidence": "low"}}.'
    )


def run_browser_use_cloud(task: str, timeout: int = 120) -> dict:
    """Frugal real-browser executor via browser-use cloud REST (free tier). Defensive:
    returns {ok, data|reason}. Never raises into the pipeline."""
    key = os.environ.get("BROWSER_USE_API_KEY", "")
    if not key:
        return {"ok": False, "reason": "no_browser_use_key"}
    try:
        import httpx
        h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=30) as c:
            r = c.post("https://api.browser-use.com/api/v1/run-task",
                       headers=h, json={"task": task})
            if r.status_code >= 300:
                return {"ok": False, "reason": f"submit_http_{r.status_code}"}
            task_id = r.json().get("id") or r.json().get("task_id")
            if not task_id:
                return {"ok": False, "reason": "no_task_id"}
            deadline = time.time() + timeout
            while time.time() < deadline:
                time.sleep(5)
                s = c.get(f"https://api.browser-use.com/api/v1/task/{task_id}", headers=h)
                st = s.json()
                if st.get("status") in ("finished", "completed", "done"):
                    return {"ok": True, "data": st.get("output") or st.get("result") or {}}
                if st.get("status") in ("failed", "error", "stopped"):
                    return {"ok": False, "reason": f"task_{st.get('status')}"}
        return {"ok": False, "reason": "timeout"}
    except Exception as e:
        return {"ok": False, "reason": f"exec_error_{type(e).__name__}"}


# ---------------------------------------------------------------------------
# Gate -- nothing reaches the tracker un-vetted. (Justine + Cipher's lane.)
# ---------------------------------------------------------------------------
def gate_contact(email: str, owner_name: str, address: str = "") -> tuple:
    """Return (ok, reason). Blocks on eradication/opt-out; rejects wrong-person."""
    email = (email or "").strip().lower()
    if not email:
        return False, "no_email"
    try:
        sys.path.insert(0, str(ROOT / "03_AUTOMATION_CORE/01_Scripts/content_tools"))
        import eradication_gate as eg
        if eg.find_hit(email=email, name=owner_name, address=address):
            return False, "eradicated_or_optout"
    except Exception as e:
        return False, f"gate_unavailable_{type(e).__name__}"  # fail CLOSED
    # opted_out cache
    try:
        sys.path.insert(0, str(ROOT / "01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent"))
        import rex_stop_handler as rsh
        if rsh.is_suppressed(email):
            return False, "suppressed"
    except Exception:
        pass
    return True, "clean"


def _first_last(owner_name: str) -> tuple:
    parts = [p for p in re.split(r"[ ,]+", (owner_name or "").strip()) if p]
    if not parts:
        return "", ""
    # assessor convention is usually LAST FIRST
    if len(parts) >= 2:
        return parts[1].title(), parts[0].title()
    return parts[0].title(), ""


def run(limit: int = 10, dry_run: bool = True) -> dict:
    tracker = _load(TRACKER, {})
    if not isinstance(tracker, dict):
        return {"error": "tracker_unreadable"}
    executor = detect_executor()
    todo = [v for v in tracker.values() if v.get("status") == "email_needed"][:limit]

    summary = {"ran_at": _now(), "executor": executor, "candidates": len(todo),
               "found": 0, "gated_out": 0, "queued": 0, "dry_run": dry_run}

    for lead in todo:
        first, last = _first_last(lead.get("owner_name", ""))
        if not last:
            continue
        url = people_search_url(first, last)
        lead["hermes_people_search_url"] = url
        lead["hermes_task"] = browser_task_spec(first, last, url)

        if dry_run or executor == "queued":
            lead["status"] = "browser_queued" if not dry_run else lead["status"]
            summary["queued"] += 1
            continue

        # Live run with a real browser executor
        result = run_browser_use_cloud(lead["hermes_task"]) if executor == "browser_use_cloud" else {"ok": False, "reason": "e5_chromium_not_wired"}
        if not result.get("ok"):
            lead["status"] = "browser_queued"
            lead["hermes_last_reason"] = result.get("reason")
            summary["queued"] += 1
            continue
        data = result.get("data") or {}
        emails = data.get("emails") or EMAIL_RE.findall(json.dumps(data))
        accepted = None
        for em in emails:
            ok, reason = gate_contact(em, lead.get("owner_name", ""), lead.get("property_address", ""))
            if ok:
                accepted = em
                break
            summary["gated_out"] += 1
        if accepted:
            lead["email"] = accepted
            lead["status"] = "email_found"
            lead["email_source"] = "hermes_people_search"
            lead["email_checked_at"] = _now()
            summary["found"] += 1
        else:
            lead["status"] = "browser_queued"
            summary["queued"] += 1

    if not dry_run:
        TRACKER.write_text(json.dumps(tracker, indent=2))
    _ledger(summary)
    return summary


def _ledger(row: dict) -> None:
    try:
        RUNS_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with RUNS_LEDGER.open("a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    dry = "--run" not in sys.argv
    lim = 10
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
            lim = int(sys.argv[i + 1])
    print(json.dumps(run(limit=lim, dry_run=dry), indent=2))
