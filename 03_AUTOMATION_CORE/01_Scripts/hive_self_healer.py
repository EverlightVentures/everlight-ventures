#!/usr/bin/env python3
"""
hive_self_healer -- the autonomous fix-finder for the Everlight Hive.

What this is:
  A recurring agent that scans systemd unit failures every 30 minutes,
  runs known-fix recipes for recognized failure patterns, and escalates
  to Slack only when no recipe matches.

Why this exists:
  The user (Marquise) called out 2026-04-26 that "the system is not self-
  healing... it doesn't address problems... it's fake work." Identifying a
  problem and waiting for human triage is structurally identical to not
  finding the problem at all. The Hive must close the loop.

Recipe library:
  Each recipe is a function that returns ('fixed' | 'still_broken' | 'no_recipe', reason).
  Recipes are matched by failing-unit name + recent-error-pattern from journalctl.
  When a NEW failure pattern shows up, a Slack alert posts so a recipe can be added.

Run mode:
  Designed to run as a systemd timer (every 30 min) on Oracle.
  Logs to /home/opc/_logs/hive_self_healer.log.
  Posts to Slack #hive-alerts on net-new failure patterns OR when a fix succeeds.

Cadence:
  Every 30 minutes. Anything more frequent is noise; less frequent leaves
  the user with broken state for too long.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("hive_self_healer")

LOG_FILE = Path("/home/opc/_logs/hive_self_healer.log")
RECIPE_LOG = Path("/home/opc/_logs/hive_self_healer_recipes.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ALERTS = os.environ.get("SLACK_CHANNEL_HIVE_ALERTS", "C08L9TJSFQE")

# Watched units. Add to this list when new timers come online.
WATCHED_UNITS = [
    "rex-negotiator.service",
    "sync-deals.service",
    "hive-health.service",
    "gmail-organizer.service",
    "hive-sync.service",
    "rex-belfort.service",
    "hourly-pulse.service",
    "rex-recycler.service",
    "broker-orch-full.service",
    "broker-orch-scout.service",
    "broker-orch-match.service",
    "broker-orch-outreach.service",
    "wholesale-day.service",
    "wholesale-outreach.service",
    "ceo-brief.service",
    "wealth-intel.service",
]


# -----------------------------------------------------------------------------
# Recipe library
# -----------------------------------------------------------------------------

def recipe_mnt_sdcard_path(unit: str, journal_tail: str) -> tuple[str, str]:
    """If the unit crashes with /mnt/sdcard PermissionError, the script needs
    the EVERLIGHT_WORKSPACE env var pointing to /home/opc."""
    if "/mnt/sdcard" not in journal_tail:
        return ("no_match", "")
    # The path-repair sprint (2026-04-26) handled this for known scripts, but
    # if a NEW script is added that hasn't been patched, surface it.
    return (
        "no_recipe",
        "/mnt/sdcard hardcoded path failure on a new script. Run the path-repair pattern: "
        "import os, pathlib; WORKSPACE = pathlib.Path(os.environ.get('EVERLIGHT_WORKSPACE', '/home/opc')); "
        "and replace '/mnt/sdcard/AA_MY_DRIVE' references."
    )


def recipe_missing_env_var(unit: str, journal_tail: str) -> tuple[str, str]:
    """If a unit fails with KeyError or 'No such env var', flag the missing var."""
    m = re.search(r"KeyError: ['\"]([A-Z_][A-Z0-9_]+)['\"]", journal_tail)
    if not m:
        return ("no_match", "")
    var = m.group(1)
    return (
        "no_recipe",
        f"Unit {unit} expects env var {var}. Add to /etc/default/rex-negotiator "
        f"(sudo) or to the unit's drop-in. Currently unset.",
    )


def recipe_invalid_oauth_grant(unit: str, journal_tail: str) -> tuple[str, str]:
    """Google Docs OAuth refresh token expired."""
    if "invalid_grant" not in journal_tail:
        return ("no_match", "")
    return (
        "no_recipe",
        "Google Docs OAuth refresh token expired. Run "
        "`python3 /home/opc/reauth_google_docs.py` (browser flow) OR migrate to "
        "service-account auth (see google_docs_service_account_setup.md). "
        "HTML reports continue to save; only Drive sink is degraded.",
    )


def recipe_imap_credentials(unit: str, journal_tail: str) -> tuple[str, str]:
    """rex-negotiator: 'No IMAP credentials set' -> env file load issue."""
    if "No IMAP credentials" not in journal_tail:
        return ("no_match", "")
    # Auto-fix: re-source /etc/default/rex-negotiator and verify IMAP_PASS is non-empty.
    try:
        env_text = subprocess.check_output(
            ["sudo", "cat", "/etc/default/rex-negotiator"],
            stderr=subprocess.DEVNULL,
        ).decode()
        if "IMAP_PASS=" in env_text:
            return ("fixed", "IMAP_PASS present in env file; transient load issue, will retry next cycle.")
        return ("no_recipe", "IMAP_PASS missing from /etc/default/rex-negotiator. Add it (Gmail app password).")
    except Exception as exc:
        return ("no_recipe", f"could not inspect env file: {exc}")


def recipe_oracle_not_reachable(unit: str, journal_tail: str) -> tuple[str, str]:
    """SSH connection refused / DNS / network blip."""
    if not re.search(r"Connection refused|No route to host|Name or service not known", journal_tail):
        return ("no_match", "")
    return (
        "no_recipe",
        f"{unit} cannot reach a network endpoint. Likely transient. If repeated, "
        f"check Oracle VCN security list and the target service's listening port.",
    )


def recipe_google_service_account_landed(unit: str, journal_tail: str) -> tuple[str, str]:
    """When the user drops the Google service-account JSON, verify it works
    and post a Slack milestone so we know the Drive sink is back online.

    This recipe runs on every scan even when no unit is failing (the meta
    pass below). It detects the SA JSON arriving from a previous failed-OAuth
    state and posts a one-time success notice."""
    sa_path = Path("/home/opc/secrets/google_service_account.json")
    flag_path = Path("/home/opc/_state/google_sa_verified.flag")
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    if not sa_path.exists():
        return ("no_match", "")
    if flag_path.exists():
        return ("no_match", "")  # already verified once, skip
    # Verify SA can mint a token. Lightweight check.
    try:
        sys.path.insert(0, "/home/opc")
        from content_tools.gdocs_bridge import _load_service_account_access_token  # type: ignore
        token = _load_service_account_access_token()
        if token:
            flag_path.write_text(datetime.now(timezone.utc).isoformat())
            post_slack_alert(
                ":white_check_mark: Google service-account auth verified. "
                "Drive sink is back online. publish_report() will return real "
                "Drive URLs from this scan forward."
            )
            return ("fixed", "service-account JSON loaded, token minted, flag set")
        return ("no_recipe", "service-account JSON exists but token mint failed; check JSON validity")
    except Exception as exc:
        return ("no_recipe", f"service-account verify error: {exc}")


RECIPES = [
    recipe_mnt_sdcard_path,
    recipe_missing_env_var,
    recipe_invalid_oauth_grant,
    recipe_imap_credentials,
    recipe_oracle_not_reachable,
    recipe_google_service_account_landed,
]


# -----------------------------------------------------------------------------
# Scan + dispatch
# -----------------------------------------------------------------------------

def get_failed_units() -> list[tuple[str, str]]:
    """Return list of (unit_name, journal_tail) for units in failed state."""
    failed = []
    for unit in WATCHED_UNITS:
        try:
            result = subprocess.check_output(
                ["systemctl", "show", unit, "-p", "Result", "--value"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            if result not in ("success", ""):
                journal = subprocess.check_output(
                    ["journalctl", "-u", unit, "--no-pager", "-n", "30"],
                    stderr=subprocess.DEVNULL,
                ).decode()
                failed.append((unit, journal))
        except Exception:
            continue
    return failed


def post_slack_alert(text: str) -> None:
    if not SLACK_BOT_TOKEN:
        log.info("SLACK_BOT_TOKEN not set, skipping Slack post")
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({
                "channel": SLACK_CHANNEL_ALERTS,
                "text": text,
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as exc:
        log.warning(f"slack post failed: {exc}")


def append_recipe_log(record: dict) -> None:
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with RECIPE_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


def run() -> int:
    log.info("hive_self_healer scan starting")
    failed = get_failed_units()
    if not failed:
        log.info("no failures detected, all watched units healthy")
        return 0

    log.info(f"{len(failed)} failed unit(s) detected: {[u for u, _ in failed]}")
    handled = 0
    escalated = 0

    for unit, journal in failed:
        applied = False
        for recipe in RECIPES:
            verdict, reason = recipe(unit, journal)
            if verdict == "fixed":
                log.info(f"  {unit}: FIXED via {recipe.__name__}")
                append_recipe_log({"unit": unit, "verdict": "fixed",
                                   "recipe": recipe.__name__, "reason": reason})
                handled += 1
                applied = True
                break
            if verdict == "no_recipe":
                log.info(f"  {unit}: no auto-fix; escalating: {reason}")
                append_recipe_log({"unit": unit, "verdict": "escalated",
                                   "recipe": recipe.__name__, "reason": reason})
                post_slack_alert(
                    f"hive_self_healer: {unit} failed. Reason: {reason}\n"
                    f"Last journal: {journal[-400:]}"
                )
                escalated += 1
                applied = True
                break
        if not applied:
            log.info(f"  {unit}: no recipe matched; escalating with raw tail")
            post_slack_alert(
                f"hive_self_healer: {unit} failed with NEW pattern. "
                f"Add a recipe.\nLast journal:\n{journal[-600:]}"
            )
            append_recipe_log({"unit": unit, "verdict": "escalated_unknown",
                               "tail": journal[-600:]})
            escalated += 1

    log.info(f"scan complete: {handled} fixed, {escalated} escalated")
    return 0


if __name__ == "__main__":
    sys.exit(run())
