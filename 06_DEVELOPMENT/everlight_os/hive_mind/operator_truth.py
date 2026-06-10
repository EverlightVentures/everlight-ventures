"""
Operator Truth Officer
======================

Charles Dawson's scoped veto layer over money-decision status claims.
Stops the "wired = working" failure mode.

Plan v3 reference: Move B + Dispatches #5, #21.

Why this exists
---------------
Twice in two weeks, we had real-money decisions made on the strength of a
"green pixel" service status while the underlying work produced zero
throughput. Examples:

- xlm-bot service active, returncode=0, but cycles were NO_TRADE for days
  (called "trading" in a status update -- $200 manual reset triggered).
- 8 of 15 phone timers crashing silently while service status read "wired"
  (audit claimed pipeline was running -- $0 in 63 days).
- broker_daily_orchestrator.py replies cron firing every 2 hours on Oracle,
  hitting AUTHENTICATIONFAILED on Gmail credentials, returning cleanly,
  log shows error, no alert, 42 silent failures over 84 hours
  (discovered 2026-04-28 09:00 PT during live audit).

The pattern: a status claim ("X is working") that does NOT parse exit codes,
sample log content, count meaningful output, or check the date. The audit
believes the service-active flag and ships the claim. Money decisions get
made on the false signal.

This module is the chokepoint that stops it.

Usage
-----
As a decorator on any audit / status-reporting function:

    from hive_mind.operator_truth import operator_truth

    @operator_truth(requires=["exit_codes", "log_content", "output_count", "date_check"])
    def daily_pipeline_status() -> dict:
        return {
            "claim": "wholesale_pipeline outreach ran today",
            "exit_code": rc,
            "log_tail": tail("/_logs/wholesale_hive_pipeline.log", 20),
            "meaningful_output_count": emails_sent_today,
            "as_of_pt": now_pt(),
        }

If any of the 4 checks fail, the wrapped function's result is REPLACED with
a corrected status that reads "[CHARLES VETO] claim retracted: <reason>",
and the original claim is logged to the audit JSONL for review.

As a sidecar on Slack publishing:

    from hive_mind.operator_truth import scan_slack_post

    cleared, replacement = scan_slack_post(
        channel="#wholesale-deals",
        text="3 emails sent overnight, pipeline running normally",
        evidence_pull=lambda: {
            "exit_code": last_orchestrator_returncode(),
            "log_tail": tail("/_logs/broker_ops/orchestrator.log", 50),
            "meaningful_output_count": resend_count_since(midnight_pt()),
            "as_of_pt": now_pt(),
        },
    )
    if not cleared:
        slack.send(replacement)  # The corrected, honest version

Scope (what Charles vetoes vs what he doesn't)
----------------------------------------------
VETO scope: money-decision status claims only.
  - Pipeline reports ("X emails sent today", "Y deals in pipeline")
  - Deal-close claims ("Deal 1 wired", "commission received")
  - Paid-tool ROI claims ("ATTOM is paying off")
  - "X is working" framing on services that touch money or compliance

NOT vetoed:
  - Internal sanity checks during dev
  - Code review comments
  - Routine debug logging
  - Build/CI status
"""
from __future__ import annotations

import functools
import inspect
import json
import re
import subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo


PT = ZoneInfo("America/Los_Angeles")
AUDIT_LOG = Path("/mnt/sdcard/AA_MY_DRIVE/_logs/operator_truth/veto_audit.jsonl")


# ====================================================================
# Data shapes
# ====================================================================
@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class TruthCheckOutcome:
    timestamp_pt: str
    function_name: str
    original_claim: dict[str, Any]
    checks: list[CheckResult] = field(default_factory=list)
    cleared: bool = False
    replacement_text: str = ""

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)


# ====================================================================
# The 4-point check primitives
# ====================================================================
def check_exit_codes(payload: dict[str, Any]) -> CheckResult:
    """A claim of 'service ran' must include an exit code that was actually parsed."""
    if "exit_code" not in payload and "returncode" not in payload:
        return CheckResult("exit_codes", False, "no exit_code/returncode field present")
    rc = payload.get("exit_code", payload.get("returncode"))
    if rc is None:
        return CheckResult("exit_codes", False, "exit_code is None -- not actually parsed")
    if not isinstance(rc, int):
        return CheckResult("exit_codes", False, f"exit_code is {type(rc).__name__} not int")
    return CheckResult("exit_codes", True, f"rc={rc}")


def check_log_content(payload: dict[str, Any]) -> CheckResult:
    """A claim of 'work happened' must include sampled log content, not just status."""
    log_tail = payload.get("log_tail") or payload.get("log_content") or payload.get("log_sample")
    if not log_tail:
        return CheckResult("log_content", False, "no log_tail/log_content/log_sample field present")
    if isinstance(log_tail, list):
        log_tail = "\n".join(str(x) for x in log_tail)
    if not log_tail.strip():
        return CheckResult("log_content", False, "log content is empty -- service ran but produced no output")
    # Look for known silent-failure signatures.
    silent_failure_patterns = [
        (r"AUTHENTICATIONFAILED", "Gmail/IMAP auth failed"),
        (r"401 Unauthorized", "API auth failed"),
        (r"403 Forbidden", "anti-bot block"),
        (r"connection timed out", "downstream unreachable"),
        (r"NO_TRADE", "bot ran but did not trade"),
        (r"0 emails sent", "pipeline ran but produced no outbound"),
        (r"0 leads scored", "scoring ran but produced no qualified leads"),
    ]
    for pat, label in silent_failure_patterns:
        if re.search(pat, log_tail, re.IGNORECASE):
            return CheckResult("log_content", False, f"silent-failure signature detected: {label}")
    return CheckResult("log_content", True, f"log content {len(log_tail)} chars, no silent-failure signatures")


def check_output_count(payload: dict[str, Any]) -> CheckResult:
    """Throughput-relevant outputs only. Cycles and runs are NOT meaningful output.

    Acceptable count names: emails_sent, sms_sent, vm_dropped, deals_advanced,
    leads_scored_hot, replies_received, calls_placed, prospects_added,
    wires_received, contracts_signed, audits_passed.

    Rejected as meaningless: cycles_run, iterations, attempts, polls,
    successes (without specifying what).
    """
    accepted_keys = {
        "emails_sent", "sms_sent", "vm_dropped", "deals_advanced",
        "leads_scored_hot", "replies_received", "calls_placed",
        "prospects_added", "wires_received", "contracts_signed",
        "audits_passed", "meaningful_output_count",
    }
    rejected_keys = {
        "cycles_run", "iterations", "attempts", "polls", "runs",
        "successes",  # too vague
    }
    found_accepted = {k: v for k, v in payload.items() if k in accepted_keys and v is not None}
    found_rejected = {k: v for k, v in payload.items() if k in rejected_keys}
    if not found_accepted:
        if found_rejected:
            return CheckResult(
                "output_count",
                False,
                f"only meaningless counts found ({list(found_rejected.keys())}); "
                f"need throughput-relevant count e.g. emails_sent, deals_advanced",
            )
        return CheckResult(
            "output_count",
            False,
            "no throughput count present (need at least one of: emails_sent, "
            "sms_sent, deals_advanced, replies_received, calls_placed, etc.)",
        )
    total = sum(int(v) for v in found_accepted.values() if isinstance(v, (int, float)))
    if total == 0:
        return CheckResult(
            "output_count",
            False,
            f"throughput is 0 (counts: {found_accepted}). Service ran but produced nothing.",
        )
    return CheckResult("output_count", True, f"meaningful output: {found_accepted} (sum={total})")


def check_date_rollover(payload: dict[str, Any]) -> CheckResult:
    """Every 'today' claim must verify against current PT date.

    Watches for: claims about 'today' that come from a session/process that
    started yesterday but is still running. The orchestrator log timestamp
    is the source of truth, not when the claim was generated.
    """
    as_of = payload.get("as_of_pt") or payload.get("timestamp_pt")
    if not as_of:
        return CheckResult("date_check", False, "no as_of_pt/timestamp_pt field present")
    try:
        if isinstance(as_of, str):
            # Allow either ISO or "YYYY-MM-DD HH:MM:SS PT" format
            iso = as_of.replace(" PT", "").replace("Z", "+00:00")
            ts = datetime.fromisoformat(iso)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=PT)
        elif isinstance(as_of, datetime):
            ts = as_of
        else:
            return CheckResult("date_check", False, f"as_of_pt is {type(as_of).__name__} not parseable")
    except Exception as e:
        return CheckResult("date_check", False, f"as_of_pt unparseable: {e}")
    now = datetime.now(PT)
    delta = (now - ts.astimezone(PT)).total_seconds()
    if delta < 0:
        return CheckResult("date_check", False, f"as_of_pt is in the future ({-delta:.0f}s)")
    if delta > 24 * 3600:
        return CheckResult(
            "date_check",
            False,
            f"as_of_pt is {delta/3600:.1f} hours old; do not call this 'today'",
        )
    if ts.astimezone(PT).date() != now.date():
        return CheckResult(
            "date_check",
            False,
            f"as_of_pt date ({ts.astimezone(PT).date()}) != current PT date ({now.date()}); "
            f"this is yesterday's claim",
        )
    return CheckResult("date_check", True, f"as_of_pt {delta/60:.1f} min ago, same PT day")


# ====================================================================
# Decorator + sidecar
# ====================================================================
DEFAULT_CHECKS = ["exit_codes", "log_content", "output_count", "date_check"]
CHECK_FNS = {
    "exit_codes": check_exit_codes,
    "log_content": check_log_content,
    "output_count": check_output_count,
    "date_check": check_date_rollover,
}


def operator_truth(
    requires: list[str] | None = None,
    on_fail: str = "veto",  # "veto" | "warn" | "raise"
):
    """Decorator: wraps an audit/status function. Runs the 4-point check on
    the function's dict return value. If any check fails:
      - on_fail='veto' (default): replaces the result with a [CHARLES VETO] dict.
      - on_fail='warn': prints a warning, returns original.
      - on_fail='raise': raises OperatorTruthVetoError.

    The original claim is always written to the audit log.
    """
    requires = requires or DEFAULT_CHECKS

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            if not isinstance(result, dict):
                # Can't check non-dict returns. Pass through.
                return result
            outcome = _run_checks(fn.__name__, result, requires)
            _write_audit(outcome)
            if outcome.all_passed:
                return result
            # Failed.
            if on_fail == "raise":
                raise OperatorTruthVetoError(outcome)
            if on_fail == "warn":
                print(f"[CHARLES WARN] {outcome.replacement_text}")
                return result
            # Default: veto. Replace result.
            return {
                "_charles_veto": True,
                "veto_reason": outcome.replacement_text,
                "original_claim_keys": list(result.keys()),
                "failed_checks": [c.name for c in outcome.checks if not c.passed],
                "audit_log": str(AUDIT_LOG),
            }

        return wrapper

    return decorator


def scan_slack_post(
    channel: str,
    text: str,
    evidence_pull: Callable[[], dict[str, Any]] | None = None,
    requires: list[str] | None = None,
) -> tuple[bool, str]:
    """Sidecar mode -- check a Slack post BEFORE publishing.

    For non-money channels (#dev, #ops-pings), we don't gate.
    For money-decision channels (#wholesale-deals, #ceo-brief, #revenue-dashboard),
    we require evidence_pull() to return a dict that passes the 4-point check.

    Returns (cleared, replacement_text):
      - cleared=True: original text is fine to publish.
      - cleared=False: replacement_text is the corrected honest version.
    """
    requires = requires or DEFAULT_CHECKS
    money_channels = {
        "#wholesale-deals", "#ceo-brief", "#revenue-dashboard",
        "#broker-pipeline", "#ai-consulting", "#xlm-trading",
        "#deals", "#commissions", "#finance",
    }
    is_money_channel = channel.lstrip("@") in money_channels or channel in money_channels
    if not is_money_channel:
        return True, ""
    if not evidence_pull:
        replacement = (
            f"[CHARLES VETO] Post to {channel} requires evidence pull. "
            f"Original text held: '{text[:100]}...'"
        )
        return False, replacement
    payload = evidence_pull()
    outcome = _run_checks(f"slack_post_to_{channel}", payload, requires)
    outcome.original_claim = {"text": text, **payload}
    _write_audit(outcome)
    if outcome.all_passed:
        return True, ""
    # Compose corrected message.
    failed = [c for c in outcome.checks if not c.passed]
    failures_str = "; ".join(f"{c.name}: {c.detail}" for c in failed)
    replacement = (
        f"[CHARLES OPERATOR TRUTH HOLD]\n"
        f"Original draft: {text}\n\n"
        f"Held because the following checks failed:\n  - {failures_str}\n\n"
        f"Corrected version (failures lead, greens follow):\n"
        f"{_compose_honest_status(payload, outcome)}"
    )
    return False, replacement


# ====================================================================
# Internals
# ====================================================================
class OperatorTruthVetoError(Exception):
    def __init__(self, outcome: TruthCheckOutcome):
        self.outcome = outcome
        super().__init__(outcome.replacement_text or "Operator Truth check failed")


def _run_checks(fn_name: str, payload: dict[str, Any], requires: list[str]) -> TruthCheckOutcome:
    outcome = TruthCheckOutcome(
        timestamp_pt=datetime.now(PT).isoformat(timespec="seconds"),
        function_name=fn_name,
        original_claim={k: _safe(v) for k, v in payload.items()},
    )
    for name in requires:
        check_fn = CHECK_FNS.get(name)
        if check_fn is None:
            outcome.checks.append(CheckResult(name, False, "unknown check"))
            continue
        outcome.checks.append(check_fn(payload))
    if not outcome.all_passed:
        failed = [c for c in outcome.checks if not c.passed]
        outcome.cleared = False
        outcome.replacement_text = (
            f"[CHARLES VETO] {fn_name}: claim retracted. "
            f"Failed checks: " + "; ".join(f"{c.name}({c.detail})" for c in failed)
        )
    else:
        outcome.cleared = True
    return outcome


def _compose_honest_status(payload: dict[str, Any], outcome: TruthCheckOutcome) -> str:
    """Generate an honest replacement status -- failures lead, greens follow."""
    failed = [c for c in outcome.checks if not c.passed]
    passed = [c for c in outcome.checks if c.passed]
    lines = ["FAILURES (lead with these):"]
    for c in failed:
        lines.append(f"  - {c.name}: {c.detail}")
    if passed:
        lines.append("")
        lines.append("PASSED:")
        for c in passed:
            lines.append(f"  - {c.name}: {c.detail}")
    if "exit_code" in payload:
        lines.append(f"\nReturncode: {payload['exit_code']}")
    if "as_of_pt" in payload:
        lines.append(f"As of: {payload['as_of_pt']} PT")
    return "\n".join(lines)


def _safe(v: Any) -> Any:
    """Make a value JSON-safe for the audit log. Truncate long log strings."""
    if isinstance(v, str) and len(v) > 2000:
        return v[:2000] + "...[truncated]"
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    if isinstance(v, (list, tuple)):
        return [_safe(x) for x in v[:50]]
    if isinstance(v, dict):
        return {str(k): _safe(val) for k, val in list(v.items())[:50]}
    return repr(v)[:500]


def _write_audit(outcome: TruthCheckOutcome) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(outcome)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(payload) + "\n")


# ====================================================================
# Smoke test
# ====================================================================
if __name__ == "__main__":
    import json

    # Test 1: passing audit
    @operator_truth()
    def good_audit() -> dict:
        return {
            "claim": "wholesale outreach completed",
            "exit_code": 0,
            "log_tail": "wholesale_hive_pipeline outreach: 12 emails sent, 3 SMS sent, completed in 47s",
            "emails_sent": 12,
            "sms_sent": 3,
            "as_of_pt": datetime.now(PT).isoformat(timespec="seconds"),
        }

    print("=== Test 1: passing audit ===")
    result = good_audit()
    print(json.dumps(result, indent=2, default=str))

    # Test 2: failing audit -- wired/working pattern
    @operator_truth()
    def lying_audit() -> dict:
        return {
            "claim": "pipeline running normally",
            "exit_code": 0,
            "log_tail": "STEP 8b: Checking for replies... IMAP login failed: AUTHENTICATIONFAILED Invalid credentials",
            "cycles_run": 100,
            # No emails_sent / no meaningful output count
            "as_of_pt": datetime.now(PT).isoformat(timespec="seconds"),
        }

    print("\n=== Test 2: lying audit (wired-but-not-working) ===")
    result = lying_audit()
    print(json.dumps(result, indent=2, default=str))

    # Test 3: stale "today" claim
    yesterday_pt = datetime.now(PT).replace(hour=8) - __import__("datetime").timedelta(hours=30)

    @operator_truth()
    def stale_audit() -> dict:
        return {
            "claim": "today's pipeline ran fine",
            "exit_code": 0,
            "log_tail": "wholesale pipeline outreach: 5 emails sent, completed",
            "emails_sent": 5,
            "as_of_pt": yesterday_pt.isoformat(timespec="seconds"),
        }

    print("\n=== Test 3: stale 'today' claim ===")
    result = stale_audit()
    print(json.dumps(result, indent=2, default=str))

    # Test 4: Slack sidecar -- money channel with bad evidence
    print("\n=== Test 4: Slack sidecar on #wholesale-deals ===")
    cleared, replacement = scan_slack_post(
        channel="#wholesale-deals",
        text="3 emails sent overnight, pipeline running normally",
        evidence_pull=lambda: {
            "exit_code": 0,
            "log_tail": "(empty)",
            "cycles_run": 0,
            "as_of_pt": datetime.now(PT).isoformat(timespec="seconds"),
        },
    )
    print(f"cleared={cleared}")
    print(f"replacement:\n{replacement}")

    print(f"\n=== Audit log written to {AUDIT_LOG} ===")
    print(f"Lines: {sum(1 for _ in open(AUDIT_LOG))}")
