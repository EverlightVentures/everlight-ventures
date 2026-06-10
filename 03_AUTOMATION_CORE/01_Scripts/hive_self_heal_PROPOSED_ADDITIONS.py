"""
Hive Self-Heal -- PROPOSED ADDITIONS (NOT THE CANONICAL FILE)
=============================================================

**STATUS:** Proposed merge into the existing canonical `hive_self_healer.py`
(291 lines, 6 recipes, deployed at `Wealth_OS/03_Engines/oracle_systemd/hive-self-healer.service`).

This file was originally written 2026-04-28 09:00 PT as a from-scratch
implementation. The truth-audit run later in the same session found that
`hive_self_healer.py` already exists with overlapping job. To avoid
deployment confusion (two self-heal services on the same VM tripping over
each other), this file has been renamed to `_PROPOSED_ADDITIONS` and
serves as a SOURCE for capabilities to merge INTO the canonical file.

What's NEW here that should be PORTED into hive_self_healer.py:
  1. Circuit breaker -- recipe-budget rate limit (max 3 firings per recipe per
     rolling 60 min) + `/tmp/hive_self_heal.killswitch` file for emergency halt.
     Canonical lacks rate limiting; if a recipe loops it will keep firing.
  2. Recipe `attom_key_rotation` -- ATTOM 401/403 -> rotate from key pool,
     fall back to county-records mode if exhausted.
  3. Recipe `resend_rate_limit_retry` -- Resend 429 -> halve SEND_RATE_PER_MIN,
     gradual restore via separate ramp-up cron.
  4. Recipe `disk_cleanup` -- root partition >85% -> journalctl vacuum 7d,
     compress hive_reports HTML older than 14d, /tmp cleanup older than 7d.

What's DUPLICATE (already in `hive_self_healer.py` -- DO NOT re-add):
  - IMAP credentials recipe (canonical: `recipe_imap_credentials`)
  - OAuth invalid_grant recipe (canonical: `recipe_invalid_oauth_grant`)
  - Oracle reachability recipe (canonical: `recipe_oracle_not_reachable`)
  - Missing env var recipe (canonical: `recipe_missing_env_var`)
  - General "scan systemd failed units, run recipe, post Slack" loop.

Merge plan (when Forge is dispatched, after Oracle reachable):
  1. Read `hive_self_healer.py` to understand existing recipe pattern.
  2. Add circuit-breaker logic to its run loop.
  3. Add the 3 new recipes following its function-shape convention.
  4. Update `hive-self-healer.service` cadence if needed.
  5. Delete this file.

Original plan v3 reference: Move C + Dispatch #4. Penny's Condition 3
(self-heal recipes deployed within 7 days). Apply via merge, not parallel.
======================================================

Original Plan v3 spec (preserved below for the merge):
====================

What it does
------------
Every 5 minutes (systemd timer on Oracle E5):

1. Scan known failure signatures across the wholesale + broker stack.
2. For each detected signature, run a known-fix recipe.
3. Circuit breaker: max 3 firings per recipe per rolling hour. Beyond that,
   STOP and page Marquise (the recipe is masking a deeper problem).
4. Kill-switch: if /tmp/hive_self_heal.killswitch exists, halt immediately.
5. Post EVERY firing to #hive-alerts with recipe name + failure pattern.
   (Iron Stack catch from round 3: silent self-heal can paper over a
   credential leak or cascading fallback failure. Every recovery is logged.)

What it deliberately does NOT do
--------------------------------
- Modify customer data (only operational state).
- Restart services that touch money (Stripe webhooks, commission_ledger,
  PSA generation) without paging first.
- Fire when /tmp/hive_self_heal.killswitch exists.
- Fire the same recipe more than 3 times in a rolling 60-minute window.
- Run on the phone (workspace doctrine: all crons on Oracle).

Initial recipe set (5)
----------------------
1. attom_key_rotation       -- ATTOM 401/403 -> rotate key from pool, fall back to county records
2. resend_rate_limit_retry  -- Resend 429 -> exponential back-off + reduce send rate
3. oauth_gdocs_refresh      -- Google Docs OAuth refresh-token expired -> rerun reauth_google_docs.py
4. cron_stall_restart       -- systemd timer >2x cadence stale -> restart timer
5. disk_cleanup             -- /var disk >85% -> clean journal logs, rotate hive_reports HTML

Each recipe is a class implementing detect() -> bool and fix() -> dict.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


# ====================================================================
# Configuration
# ====================================================================
PT = ZoneInfo("America/Los_Angeles")
WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/opc"))  # Oracle path; phone overrides via env
ALERT_LOG = Path("/tmp/hive_self_heal_alerts.jsonl")
RECIPE_LEDGER = Path("/tmp/hive_self_heal_recipe_ledger.jsonl")
KILLSWITCH = Path("/tmp/hive_self_heal.killswitch")
RECIPE_BUDGET_PER_HOUR = 3
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_ALERTS_CHANNEL = "C09ALERTS"  # #hive-alerts (placeholder; Marquise sets actual channel ID)


# ====================================================================
# Data shapes
# ====================================================================
@dataclass
class RecipeOutcome:
    timestamp_pt: str
    recipe_name: str
    detected_signature: str = ""
    detected: bool = False
    fired: bool = False
    fix_summary: str = ""
    fix_evidence: dict[str, Any] = field(default_factory=dict)
    blocked_by_circuit_breaker: bool = False
    error: str = ""


# ====================================================================
# Base recipe class
# ====================================================================
class Recipe:
    """Base class. Subclass for each known-fix recipe.

    Each subclass implements:
      - name: short identifier
      - detect() -> tuple[bool, str]: returns (detected, signature_description)
      - fix() -> dict: returns evidence dict; called only if detect() returns True

    Recipes must be IDEMPOTENT -- running fix() twice should not cause harm.
    """
    name: str = "base"

    def detect(self) -> tuple[bool, str]:
        raise NotImplementedError

    def fix(self) -> dict[str, Any]:
        raise NotImplementedError


class ATTOMKeyRotationRecipe(Recipe):
    name = "attom_key_rotation"

    def detect(self) -> tuple[bool, str]:
        log_path = WORKSPACE / "_logs" / "attom" / "attom_api.log"
        if not log_path.exists():
            return False, "no log present"
        tail = _tail(log_path, 100)
        if re.search(r"(401|403|Unauthorized|Forbidden|API key.*expired)", tail, re.IGNORECASE):
            return True, "ATTOM 401/403/expired in attom_api.log"
        return False, "no ATTOM auth signature"

    def fix(self) -> dict[str, Any]:
        # Rotate from pool if env has alternates; otherwise fall back to county records.
        pool = os.environ.get("ATTOM_KEY_POOL", "").split(",")
        current = os.environ.get("ATTOM_API_KEY", "")
        used_path = WORKSPACE / "_state" / "attom_used_keys.txt"
        used = set(used_path.read_text().splitlines()) if used_path.exists() else set()
        used.add(current)
        candidates = [k for k in pool if k and k.strip() and k.strip() not in used]
        if candidates:
            new_key = candidates[0].strip()
            # Update Oracle .env
            _update_env_var("ATTOM_API_KEY", new_key)
            used_path.parent.mkdir(parents=True, exist_ok=True)
            used_path.write_text("\n".join(used))
            return {
                "action": "rotated_to_alternate_key",
                "new_key_suffix": new_key[-4:] if len(new_key) >= 4 else "?",
                "remaining_in_pool": len(candidates) - 1,
            }
        # No alternates -- fall back to county records mode.
        _update_env_var("ATTOM_FALLBACK_MODE", "county_records_only")
        return {
            "action": "fallback_to_county_records",
            "note": "ATTOM_KEY_POOL exhausted. Pipeline now uses Maricopa, Davidson, Cuyahoga, Fulton, Dallas county APIs only.",
        }


class ResendRateLimitRetryRecipe(Recipe):
    name = "resend_rate_limit_retry"

    def detect(self) -> tuple[bool, str]:
        log_path = WORKSPACE / "_logs" / "resend" / "send.log"
        if not log_path.exists():
            return False, "no Resend log"
        tail = _tail(log_path, 50)
        if re.search(r"(429|rate limit|Too Many Requests)", tail, re.IGNORECASE):
            return True, "Resend 429 / rate limit signature"
        return False, "no rate-limit signature"

    def fix(self) -> dict[str, Any]:
        # Reduce send rate via env: branded_mailer reads SEND_RATE_PER_MIN.
        current = int(os.environ.get("SEND_RATE_PER_MIN", "30"))
        new_rate = max(5, current // 2)
        _update_env_var("SEND_RATE_PER_MIN", str(new_rate))
        return {
            "action": "halved_send_rate",
            "previous_rate_per_min": current,
            "new_rate_per_min": new_rate,
            "note": "Will gradually restore over 24 hours via daily ramp-up cron (separate)",
        }


class OAuthGDocsRefreshRecipe(Recipe):
    name = "oauth_gdocs_refresh"

    def detect(self) -> tuple[bool, str]:
        token_path = Path("/home/opc/secrets/google_docs_token.json")
        if not token_path.exists():
            return True, "google_docs_token.json missing"
        # Token exists -- check if recent attempts have hit refresh failure.
        log_path = WORKSPACE / "_logs" / "gdocs_bridge.log"
        if log_path.exists():
            tail = _tail(log_path, 50)
            if re.search(r"(invalid_grant|refresh.*expired|token.*expired)", tail, re.IGNORECASE):
                return True, "Google OAuth refresh token failure in gdocs_bridge.log"
        return False, "OAuth token apparently valid"

    def fix(self) -> dict[str, Any]:
        # Cannot programmatically refresh a Google OAuth user-consent token.
        # Best we can do: page Marquise with the runbook URL and disable
        # gdoc publishing in branded layer until rotation is done (HTML+Slack
        # still ship -- this matches the existing graceful-degrade pattern).
        _update_env_var("GDOCS_DISABLE", "1")
        return {
            "action": "disabled_gdoc_publishing_temporarily",
            "human_action_required": True,
            "runbook": "/home/opc/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/runbooks/google_oauth_rotation.md (TODO: write runbook)",
            "fallback_runbook": "Run python3 /home/opc/reauth_google_docs.py for browser-OAuth flow",
            "note": "HTML reports + Slack cards still ship via branded layer. Only gdoc sink disabled until OAuth rotated.",
        }


class CronStallRestartRecipe(Recipe):
    name = "cron_stall_restart"

    # Wholesale-critical timers and their expected max-staleness in minutes.
    WATCHED_TIMERS = {
        "broker-orch-replies.timer": 130,         # every 2hr expected
        "broker-orch-outreach.timer": 600,        # twice daily 10/00 UTC
        "hive-deal-orchestrator.timer": 65,       # hourly
        "wholesale-pipeline-day.timer": 1500,     # daily
        "wholesale-outreach.timer": 1500,         # daily
        "rex-negotiator.timer": 5,                # every 2 min
    }

    def detect(self) -> tuple[bool, str]:
        # systemctl list-timers --no-pager
        try:
            out = subprocess.run(
                ["systemctl", "list-timers", "--all", "--no-pager"],
                capture_output=True, text=True, timeout=10,
            ).stdout
        except Exception as e:
            return False, f"systemctl unavailable: {e}"
        stale = []
        for timer, max_min in self.WATCHED_TIMERS.items():
            m = re.search(rf"(\d+\w+ ago).*{re.escape(timer)}", out)
            if m:
                ago_str = m.group(1)
                ago_min = _parse_ago_to_minutes(ago_str)
                if ago_min is not None and ago_min > 2 * max_min:
                    stale.append((timer, ago_min, max_min))
        if stale:
            sig = "; ".join(f"{t} stale {m}min (max {mx})" for t, m, mx in stale)
            return True, sig
        return False, "all timers within 2x cadence"

    def fix(self) -> dict[str, Any]:
        # Restart all watched timers that are stale.
        try:
            out = subprocess.run(
                ["systemctl", "list-timers", "--all", "--no-pager"],
                capture_output=True, text=True, timeout=10,
            ).stdout
        except Exception as e:
            return {"action": "skipped", "error": str(e)}
        restarted = []
        for timer, max_min in self.WATCHED_TIMERS.items():
            m = re.search(rf"(\d+\w+ ago).*{re.escape(timer)}", out)
            if m:
                ago_min = _parse_ago_to_minutes(m.group(1))
                if ago_min and ago_min > 2 * max_min:
                    try:
                        subprocess.run(
                            ["sudo", "systemctl", "restart", timer],
                            check=True, timeout=15,
                        )
                        restarted.append(timer)
                    except Exception as e:
                        restarted.append(f"{timer}: FAILED ({e})")
        return {
            "action": "restarted_stale_timers",
            "restarted": restarted,
        }


class DiskCleanupRecipe(Recipe):
    name = "disk_cleanup"

    def detect(self) -> tuple[bool, str]:
        try:
            out = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True, timeout=5
            ).stdout
        except Exception as e:
            return False, f"df unavailable: {e}"
        m = re.search(r"(\d+)%\s+/$", out, re.MULTILINE)
        if m:
            used_pct = int(m.group(1))
            if used_pct >= 85:
                return True, f"root disk at {used_pct}% used"
        return False, "disk under 85%"

    def fix(self) -> dict[str, Any]:
        actions = []
        # 1. Vacuum journal logs (keep 7 days).
        try:
            out = subprocess.run(
                ["sudo", "journalctl", "--vacuum-time=7d"],
                capture_output=True, text=True, timeout=30,
            )
            actions.append(f"journalctl vacuum: rc={out.returncode}, freed: {_grep(out.stdout, 'Vacuuming')}")
        except Exception as e:
            actions.append(f"journalctl vacuum FAILED: {e}")

        # 2. Rotate/compress hive_reports HTML older than 14 days.
        reports_dir = Path("/home/opc/hive_reports")
        if reports_dir.exists():
            cutoff = datetime.now() - timedelta(days=14)
            count = 0
            for f in reports_dir.glob("*.html"):
                try:
                    if f.stat().st_mtime < cutoff.timestamp():
                        # Compress in place; keep .gz.
                        subprocess.run(["gzip", "-9", str(f)], check=True, timeout=10)
                        count += 1
                except Exception:
                    pass
            actions.append(f"hive_reports HTML compressed: {count} files")

        # 3. Clear /tmp older than 7 days.
        try:
            subprocess.run(
                ["find", "/tmp", "-type", "f", "-mtime", "+7", "-delete"],
                check=False, timeout=30,
            )
            actions.append("/tmp older than 7d cleared")
        except Exception as e:
            actions.append(f"/tmp clear FAILED: {e}")

        # Re-check disk.
        try:
            out = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5).stdout
            actions.append(f"post-cleanup df: {out.strip().split(chr(10))[-1]}")
        except Exception:
            pass

        return {"action": "cleaned_journals_reports_tmp", "details": actions}


# ====================================================================
# Engine
# ====================================================================
RECIPES = [
    ATTOMKeyRotationRecipe(),
    ResendRateLimitRetryRecipe(),
    OAuthGDocsRefreshRecipe(),
    CronStallRestartRecipe(),
    DiskCleanupRecipe(),
]


def run_once() -> list[RecipeOutcome]:
    """Single self-heal pass. Called by systemd timer every 5 min."""
    if KILLSWITCH.exists():
        return [_record(RecipeOutcome(
            timestamp_pt=_now_pt(),
            recipe_name="ALL",
            error="kill-switch present at /tmp/hive_self_heal.killswitch -- halting",
        ))]

    outcomes = []
    for recipe in RECIPES:
        outcome = RecipeOutcome(
            timestamp_pt=_now_pt(),
            recipe_name=recipe.name,
        )
        # Detect.
        try:
            detected, signature = recipe.detect()
            outcome.detected = detected
            outcome.detected_signature = signature
        except Exception as e:
            outcome.error = f"detect() raised: {e}"
            outcomes.append(_record(outcome))
            continue

        if not detected:
            # Don't record clean passes -- only when detect() fired.
            continue

        # Circuit breaker.
        recent = _recent_firings(recipe.name, within_minutes=60)
        if recent >= RECIPE_BUDGET_PER_HOUR:
            outcome.blocked_by_circuit_breaker = True
            outcome.error = f"circuit breaker: {recent} firings in last 60 min, budget is {RECIPE_BUDGET_PER_HOUR}"
            _alert_marquise_circuit_open(recipe.name, signature, recent)
            outcomes.append(_record(outcome))
            continue

        # Fire.
        try:
            evidence = recipe.fix()
            outcome.fired = True
            outcome.fix_evidence = evidence
            outcome.fix_summary = evidence.get("action", "")
            _alert_slack(recipe.name, signature, evidence)
        except Exception as e:
            outcome.error = f"fix() raised: {e}"

        outcomes.append(_record(outcome))

    return outcomes


# ====================================================================
# Internals
# ====================================================================
def _now_pt() -> str:
    return datetime.now(PT).isoformat(timespec="seconds")


def _tail(path: Path, n: int) -> str:
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            chunk = min(size, n * 200)  # ~200 bytes/line est
            f.seek(-chunk, 2)
            return f.read().decode("utf-8", errors="replace").splitlines()[-n:].__str__()
    except Exception:
        return ""


def _grep(text: str, pattern: str) -> str:
    for line in text.splitlines():
        if pattern in line:
            return line.strip()
    return ""


def _parse_ago_to_minutes(s: str) -> int | None:
    """Parse '5min ago', '2h ago', '1day ago' to minutes."""
    m = re.match(r"(\d+)\s*(\w+)", s)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("min") or unit.startswith("m"):
        return val
    if unit.startswith("h") or unit.startswith("hour"):
        return val * 60
    if unit.startswith("d") or unit.startswith("day"):
        return val * 60 * 24
    if unit.startswith("s") or unit.startswith("sec"):
        return max(1, val // 60)
    return None


def _update_env_var(key: str, value: str) -> None:
    """Update /home/opc/.env idempotently. Marker-based."""
    env_path = Path("/home/opc/.env")
    if not env_path.exists():
        env_path.write_text(f"{key}={value}\n")
        return
    lines = env_path.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n")
    os.environ[key] = value  # Update current process too.


def _recent_firings(recipe_name: str, within_minutes: int) -> int:
    """Count how many times this recipe FIRED in the last N minutes."""
    if not RECIPE_LEDGER.exists():
        return 0
    cutoff = datetime.now(PT) - timedelta(minutes=within_minutes)
    count = 0
    try:
        for line in RECIPE_LEDGER.read_text().splitlines():
            try:
                row = json.loads(line)
                if row.get("recipe_name") != recipe_name:
                    continue
                if not row.get("fired"):
                    continue
                ts = datetime.fromisoformat(row["timestamp_pt"])
                if ts >= cutoff:
                    count += 1
            except Exception:
                continue
    except Exception:
        pass
    return count


def _record(outcome: RecipeOutcome) -> RecipeOutcome:
    RECIPE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(RECIPE_LEDGER, "a") as f:
        f.write(json.dumps(asdict(outcome)) + "\n")
    return outcome


def _alert_slack(recipe_name: str, signature: str, evidence: dict[str, Any]) -> None:
    """Post recipe firing to #hive-alerts. Iron Stack rule: every fix posted, not just net-new."""
    text = (
        f":wrench: *Self-heal recipe fired*\n"
        f"Recipe: `{recipe_name}`\n"
        f"Signature: {signature}\n"
        f"Action: {evidence.get('action', 'unknown')}\n"
        f"Details: ```{json.dumps({k: v for k, v in evidence.items() if k != 'action'}, indent=2)[:500]}```"
    )
    _slack_post(SLACK_ALERTS_CHANNEL, text)
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ALERT_LOG, "a") as f:
        f.write(json.dumps({
            "ts_pt": _now_pt(),
            "recipe": recipe_name,
            "signature": signature,
            "evidence": evidence,
        }) + "\n")


def _alert_marquise_circuit_open(recipe_name: str, signature: str, firings: int) -> None:
    """Circuit breaker fired -- something is masking a deeper problem."""
    text = (
        f":rotating_light: *CIRCUIT BREAKER OPEN*\n"
        f"Recipe `{recipe_name}` fired {firings} times in the last 60 min.\n"
        f"Budget exceeded. Recipe disabled until manual investigation.\n"
        f"Latest signature: {signature}\n"
        f"Investigate: the recipe is masking a deeper failure that keeps recurring.\n"
        f"To halt all self-heal: `touch {KILLSWITCH}`\n"
        f"To reset budget: clear ledger entries for {recipe_name} from {RECIPE_LEDGER}"
    )
    _slack_post(SLACK_ALERTS_CHANNEL, text)


def _slack_post(channel: str, text: str) -> None:
    if not SLACK_BOT_TOKEN:
        return
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel, "text": text}).encode(),
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass  # Slack failures must not break self-heal.


# ====================================================================
# CLI / smoke test
# ====================================================================
if __name__ == "__main__":
    if "--smoke" in sys.argv:
        # Run each recipe's detect() against current state. Don't fix.
        print("=== Self-heal smoke test (detect only, no fixes) ===\n")
        for r in RECIPES:
            try:
                detected, sig = r.detect()
                status = "DETECTED" if detected else "clean"
                print(f"  {r.name:30} {status:10} {sig}")
            except Exception as e:
                print(f"  {r.name:30} ERROR     {e}")
        print(f"\n=== Recipe ledger: {RECIPE_LEDGER} ===")
        if RECIPE_LEDGER.exists():
            print(f"Lines: {sum(1 for _ in open(RECIPE_LEDGER))}")
    elif "--once" in sys.argv:
        outcomes = run_once()
        print(json.dumps([asdict(o) for o in outcomes], indent=2))
    else:
        print("Usage: python3 hive_self_heal.py --smoke   # detect-only test")
        print("       python3 hive_self_heal.py --once    # full run (would fix)")
        print(f"Kill-switch: {KILLSWITCH}")
        print(f"Recipe ledger: {RECIPE_LEDGER}")
        print(f"Alert log: {ALERT_LOG}")
