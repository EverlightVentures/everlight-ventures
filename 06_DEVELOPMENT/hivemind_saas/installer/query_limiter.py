#!/usr/bin/env python3
"""
Hive Mind -- Query Limiter
Tracks daily query count and enforces per-plan limits.

Plan limits:
    trial       5 queries/day
    spark       100 queries/day
    hive        unlimited
    enterprise  unlimited

Usage:
    python3 query_limiter.py              # check if query allowed (exit 0=yes, 1=no)
    python3 query_limiter.py --increment  # check AND increment counter
    python3 query_limiter.py --status     # print current usage
"""

import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from pathlib import Path

HIVEMIND_HOME = Path.home() / ".hivemind"
CONFIG_FILE = HIVEMIND_HOME / "config.json"
USAGE_FILE = HIVEMIND_HOME / "usage.json"

PLAN_LIMITS = {
    "trial": 5,
    "spark": 100,
    "hive": -1,        # unlimited
    "enterprise": -1,  # unlimited
}

UPGRADE_URL = "https://everlightventures.io/hivemind"


def load_config() -> dict:
    """Load user config."""
    if not CONFIG_FILE.exists():
        return {"plan": "trial", "email": ""}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_usage() -> dict:
    """Load today's usage or reset if date has rolled over."""
    today = date.today().isoformat()

    if not USAGE_FILE.exists():
        return {"date": today, "queries": 0}

    with open(USAGE_FILE) as f:
        usage = json.load(f)

    # Reset counter if it's a new day
    if usage.get("date") != today:
        usage = {"date": today, "queries": 0}

    return usage


def save_usage(usage: dict) -> None:
    """Persist usage to disk."""
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f, indent=4)


def report_usage_to_supabase(config: dict, usage: dict) -> None:
    """
    Report usage to Supabase hivemind_usage table.
    Fire-and-forget -- failures are silently ignored.
    """
    email = config.get("email", "")
    supabase_url = config.get("supabase_url", "")
    anon_key = config.get("supabase_anon_key", "")

    if not email or not supabase_url or not anon_key:
        return

    url = f"{supabase_url}/rest/v1/hivemind_usage"
    payload = json.dumps({
        "email": email,
        "date": usage["date"],
        "queries": usage["queries"],
        "plan": config.get("plan", "trial"),
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }).encode()

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("apikey", anon_key)
    req.add_header("Authorization", f"Bearer {anon_key}")
    req.add_header("Content-Type", "application/json")
    # Upsert on (email, date)
    req.add_header("Prefer", "resolution=merge-duplicates")

    try:
        urllib.request.urlopen(req, timeout=5)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        pass  # Non-critical -- usage reporting can lag


def check_query_allowed(config: dict, usage: dict) -> bool:
    """Return True if the user has queries remaining today."""
    plan = config.get("plan", "trial").lower()
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])

    # Unlimited plans
    if limit == -1:
        return True

    return usage.get("queries", 0) < limit


def get_remaining(config: dict, usage: dict) -> str:
    """Return a human-readable remaining count."""
    plan = config.get("plan", "trial").lower()
    limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])

    if limit == -1:
        return "unlimited"

    used = usage.get("queries", 0)
    remaining = max(0, limit - used)
    return f"{remaining}/{limit}"


def main():
    increment = "--increment" in sys.argv
    status_only = "--status" in sys.argv

    config = load_config()
    usage = load_usage()
    plan = config.get("plan", "trial").lower()

    if status_only:
        remaining = get_remaining(config, usage)
        print(f"Plan: {plan}")
        print(f"Today's queries: {usage.get('queries', 0)}")
        print(f"Remaining: {remaining}")
        sys.exit(0)

    allowed = check_query_allowed(config, usage)

    if not allowed:
        limit = PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])
        print(f"Daily query limit reached ({limit} queries for {plan} plan).")
        print(f"Upgrade your plan at: {UPGRADE_URL}")
        sys.exit(1)

    if increment:
        usage["queries"] = usage.get("queries", 0) + 1
        save_usage(usage)

        # Report to Supabase every 10 queries to reduce API calls
        if usage["queries"] % 10 == 0 or usage["queries"] == 1:
            report_usage_to_supabase(config, usage)

    # Print remaining for caller's info
    remaining = get_remaining(config, usage)
    if plan in ("trial", "spark"):
        # Only print remaining for limited plans, keep output clean
        pass  # caller can use --status if needed

    sys.exit(0)


if __name__ == "__main__":
    main()
