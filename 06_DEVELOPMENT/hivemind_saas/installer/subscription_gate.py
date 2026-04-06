#!/usr/bin/env python3
"""
Hive Mind -- Subscription Gate
Checks Supabase for active subscription status.
Exit code 0 = active, 1 = expired/paused/missing.

Usage:
    python3 subscription_gate.py              # check and print status
    python3 subscription_gate.py --update-config  # check and update config.json
"""

import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

HIVEMIND_HOME = Path.home() / ".hivemind"
CONFIG_FILE = HIVEMIND_HOME / "config.json"
REACTIVATE_URL = "https://everlightventures.io/hivemind"


def load_config() -> dict:
    """Load user config from ~/.hivemind/config.json."""
    if not CONFIG_FILE.exists():
        print(f"Config not found at {CONFIG_FILE}")
        print("Run the Hive Mind installer first.")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """Write updated config back to disk."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def check_subscription(config: dict) -> dict:
    """
    Query Supabase hivemind_subscriptions table for this user's status.
    Returns a dict with keys: active (bool), status (str), plan (str), message (str).
    """
    email = config.get("email", "")
    supabase_url = config.get("supabase_url", "")
    anon_key = config.get("supabase_anon_key", "")

    if not email:
        return {
            "active": False,
            "status": "no_email",
            "plan": "trial",
            "message": "No email configured. Run the installer or edit ~/.hivemind/config.json.",
        }

    if not supabase_url or not anon_key:
        return {
            "active": False,
            "status": "no_supabase",
            "plan": config.get("plan", "trial"),
            "message": "Supabase credentials missing from config.",
        }

    # Build the REST query
    url = (
        f"{supabase_url}/rest/v1/hivemind_subscriptions"
        f"?email=eq.{urllib.request.quote(email)}"
        f"&select=subscription_status,plan,expires_at"
    )

    req = urllib.request.Request(url)
    req.add_header("apikey", anon_key)
    req.add_header("Authorization", f"Bearer {anon_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        # Network error -- allow cached status to persist for 48 hours
        return _check_cached_status(config, str(e))

    if not data:
        return {
            "active": False,
            "status": "not_found",
            "plan": "trial",
            "message": (
                f"No subscription found for {email}.\n"
                f"Sign up at: {REACTIVATE_URL}"
            ),
        }

    record = data[0]
    status = record.get("subscription_status", "unknown")
    plan = record.get("plan", "trial")
    expires_at_str = record.get("expires_at", "")

    # Check expiration
    expired = False
    if expires_at_str:
        try:
            # Handle ISO format with or without timezone
            expires_at_str_clean = expires_at_str.replace("Z", "+00:00")
            expires_at = datetime.fromisoformat(expires_at_str_clean)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            expired = datetime.now(timezone.utc) > expires_at
        except (ValueError, TypeError):
            expired = False

    if status == "active" and not expired:
        return {
            "active": True,
            "status": "active",
            "plan": plan,
            "message": f"Subscription active -- plan: {plan}",
        }

    if expired:
        return {
            "active": False,
            "status": "expired",
            "plan": plan,
            "message": (
                "Your Hive Mind subscription has expired.\n"
                f"Reactivate at: {REACTIVATE_URL}"
            ),
        }

    # paused, cancelled, or other
    return {
        "active": False,
        "status": status,
        "plan": plan,
        "message": (
            f"Your Hive Mind subscription is {status}.\n"
            f"Reactivate at: {REACTIVATE_URL}"
        ),
    }


def _check_cached_status(config: dict, error_msg: str) -> dict:
    """
    When we can't reach Supabase, allow the user to keep working
    if their cached status is 'active' and was checked within 48 hours.
    """
    cached_status = config.get("subscription_status", "")
    last_checked = config.get("last_subscription_check", "")

    if cached_status == "active" and last_checked:
        try:
            last_dt = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            if hours_since < 48:
                return {
                    "active": True,
                    "status": "active_cached",
                    "plan": config.get("plan", "trial"),
                    "message": (
                        f"Offline -- using cached status (checked {int(hours_since)}h ago). "
                        f"Network error: {error_msg}"
                    ),
                }
        except (ValueError, TypeError):
            pass

    return {
        "active": False,
        "status": "offline",
        "plan": config.get("plan", "trial"),
        "message": (
            f"Could not verify subscription and no recent cached status.\n"
            f"Network error: {error_msg}\n"
            f"Check your connection and try again."
        ),
    }


def main():
    update_config = "--update-config" in sys.argv

    config = load_config()
    result = check_subscription(config)

    # Print status message
    print(result["message"])

    # Update config if requested
    if update_config or result["active"]:
        config["subscription_status"] = result["status"]
        config["plan"] = result["plan"]
        config["last_subscription_check"] = datetime.now(timezone.utc).isoformat()
        save_config(config)

    # Exit code: 0 = active, 1 = not active
    sys.exit(0 if result["active"] else 1)


if __name__ == "__main__":
    main()
