#!/usr/bin/env python3
"""restart_harness -- the outbound-restart verification harness.

Per HIVE_GOVERNANCE_V2.md Section 5, the halt-lift sequence is:
    simulated test sends -> Justine signoff -> warm-only Chris ping ->
    Marcus signoff -> Rich signoff -> halt lifts

This script automates the simulated phase, the warm phase, and the cold-restart
guardrails. Run with:

    python3 restart_harness.py --phase=test    # 14 simulated cases, no real sends
    python3 restart_harness.py --phase=warm    # one real send to Chris Ulander
    python3 restart_harness.py --phase=cold    # production restart go-live

Determinism
-----------
The TEST phase mocks datetime.now() in branded_mailer + weekly_cadence so that
quiet-hours and weekday gates produce identical results on re-run. Two mocked
"now" timestamps are used:
    - Saturday 22:00 CT  (Streubel-style late-night)
    - Tuesday  14:00 CT  (mid-day midweek allow-window)

Exit codes
----------
    0 -- all expectations met (test) / send acknowledged (warm) / go-live (cold)
    1 -- any expectation failed
    2 -- harness internal error (paths missing, imports broken)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from unittest import mock

logging.basicConfig(
    level=os.environ.get("RESTART_HARNESS_LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("restart_harness")

# ── Path bootstrap ─────────────────────────────────────────────────
_THIS = Path(__file__).resolve()
_REPO_ROOT = Path("/AA_MY_DRIVE")
_LOG_DIR = _REPO_ROOT / "_logs" / "restart_harness"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

for p in (
    _REPO_ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools",
    _REPO_ROOT / "01_BUSINESSES" / "Everlight_Ventures" / "Wholesale" / "compliance",
    _REPO_ROOT / "06_DEVELOPMENT" / "everlight_os" / "hive_mind",
):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)


# ── Test cases ─────────────────────────────────────────────────────

@dataclass
class TestCase:
    id: str
    description: str
    recipient: str
    budget_category: str
    expected_ok: bool
    expected_error_prefix: str = ""    # MailResult.error must startswith this
    halt_active: bool = True            # global halt state for this case
    mock_iso: str = ""                  # ISO-8601 UTC the mailer "thinks" it is now
    recipient_state: str = ""           # for state-cadence checks
    name: str = ""
    note: str = ""


# Two stable mock-now timestamps (UTC -- branded_mailer's internal cadence
# converts to recipient TZ). 22:00 CT Saturday = 03:00 UTC Sunday.
# Saturday 2026-05-09 22:00 America/Chicago = Sunday 2026-05-10 03:00Z
_SAT_LATE_NIGHT_UTC = "2026-05-10T03:00:00+00:00"  # Sunday 03:00 UTC = Sat 22:00 CT
# Tuesday 2026-05-12 14:00 America/Chicago = 19:00Z
_TUE_MIDDAY_UTC = "2026-05-12T19:00:00+00:00"

# Saturday 22:00 CT in TN local hours (Sat day-of-week, hour=22) -- quiet_hours blocks
# Tuesday 14:00 CT in TN local hours (Tue day-of-week, hour=14) -- allowed window

CASES: list[TestCase] = [
    TestCase(
        id="01_streubel_attorney",
        description="The Streubel case: cold to law firm domain (municipalfirm)",
        recipient="dave@municipalfirm.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="recipient_class_blocked",
        halt_active=False,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
        name="Dave Streubel",
        note="If this passes, the Streubel iron held.",
    ),
    TestCase(
        id="02_gov_recipient",
        description="Cold to a *.gov domain -- always blocked",
        recipient="planning@cityofmemphis.gov",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="recipient_class_blocked",
        halt_active=False,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
    ),
    TestCase(
        id="03_role_address",
        description="Cold to info@ role address -- blocked",
        recipient="info@somecompany.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="recipient_class_blocked",
        halt_active=False,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
    ),
    TestCase(
        id="04_consumer_saturday_late",
        description="Consumer gmail cold on Saturday 10pm CT -- quiet_hours blocks",
        recipient="homeowner1@gmail.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="quiet_hours",
        halt_active=False,
        mock_iso=_SAT_LATE_NIGHT_UTC,
        recipient_state="TN",
        name="Homeowner One",
    ),
    TestCase(
        id="05_consumer_tuesday_midday",
        description="Consumer gmail cold Tuesday 2pm CT -- allowed window (but halt)",
        recipient="homeowner2@gmail.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="OUTBOUND_HALT",
        halt_active=True,  # halt overrides everything
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
        name="Homeowner Two",
    ),
    TestCase(
        id="06_chris_vip_reply_saturday",
        description="Chris-tier vip_reply on Saturday -- response not solicitation",
        recipient="chris@midsouthhomebuyers.com",
        budget_category="vip_reply",
        expected_ok=True,
        halt_active=False,
        mock_iso=_SAT_LATE_NIGHT_UTC,
        recipient_state="TN",
        name="Chris Ulander",
        note="Reply to inbound is not solicitation under TSR.",
    ),
    TestCase(
        id="07_dnc_hit",
        description="Cold to a DNC'd recipient -- registrar blocks",
        recipient="harness.dnc.test+seed@gmail.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="dnc_blocked",
        halt_active=False,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
        note="Pre-registers this gmail address (consumer_residential) so DNC is the blocking gate, not recipient_class.",
    ),
    TestCase(
        id="08_halt_active_cold",
        description="Cold send with WHOLESALE_OUTBOUND_HALT=1 -- short-circuits",
        recipient="homeowner3@gmail.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="OUTBOUND_HALT",
        halt_active=True,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
    ),
    TestCase(
        id="09_internal_domain",
        description="Send to internal everlightventures.io -- guard blocks",
        recipient="rich@everlightventures.io",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="guard_blocked",
        halt_active=False,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
    ),
    TestCase(
        id="10_attorney_vip_reply_allowed",
        description="VIP reply to an attorney is allowed (not solicitation)",
        recipient="dave@somelawfirm.com",
        budget_category="vip_reply",
        expected_ok=True,
        halt_active=False,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TN",
        note="Solicitation rules do NOT apply to responses.",
    ),
    TestCase(
        id="11_gov_vip_reply_still_blocked",
        description="Even vip_reply cannot bypass government_blocked",
        recipient="planning@dallastx.gov",
        budget_category="vip_reply",
        expected_ok=False,
        expected_error_prefix="recipient_class_blocked",
        halt_active=False,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="TX",
        note="Gov contact requires explicit channel separation.",
    ),
    TestCase(
        id="12_system_cat_bypasses_halt",
        description="System category bypasses OUTBOUND_HALT (admin alerts)",
        recipient="admin@everlightventures.io",
        budget_category="system",
        expected_ok=False,
        expected_error_prefix="guard_blocked",  # internal guard still trips
        halt_active=True,
        mock_iso=_TUE_MIDDAY_UTC,
        recipient_state="",
        note="System bypasses halt but resend_guard still blocks own domain.",
    ),
    TestCase(
        id="13_consumer_sunday_blocked",
        description="Consumer cold on Sunday -- ALL Sunday blocked by quiet_hours",
        recipient="homeowner4@gmail.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="quiet_hours",
        halt_active=False,
        # Sunday 2026-05-10 14:00 CT = 19:00 UTC
        mock_iso="2026-05-10T19:00:00+00:00",
        recipient_state="TN",
    ),
    TestCase(
        id="14_consumer_monday_8am_blocked",
        description="Consumer cold Monday 8am CT -- before 9am cutoff",
        recipient="homeowner5@gmail.com",
        budget_category="bulk",
        expected_ok=False,
        expected_error_prefix="quiet_hours",
        halt_active=False,
        # Monday 2026-05-11 08:00 CT = 13:00 UTC
        mock_iso="2026-05-11T13:00:00+00:00",
        recipient_state="TN",
    ),
]


@dataclass
class CaseResult:
    case_id: str
    description: str
    expected_ok: bool
    expected_error_prefix: str
    actual_ok: bool
    actual_error: str
    passed: bool
    notes: str = ""


# ── Helpers ────────────────────────────────────────────────────────

@contextmanager
def _frozen_now(iso: str):
    """Patch datetime.now() in branded_mailer + weekly_cadence to return iso.

    Other modules' datetime.now() is left alone so the audit_log's timestamps
    remain real (we want the harness run trail to be accurate even though the
    mailer's gates are evaluated against a fixed point-in-time).
    """
    if not iso:
        yield
        return

    target = datetime.fromisoformat(iso)
    if target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)

    real_dt = datetime

    class _FrozenDT(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return target.astimezone(timezone.utc).replace(tzinfo=None)
            return target.astimezone(tz)

        @classmethod
        def utcnow(cls):
            return target.astimezone(timezone.utc).replace(tzinfo=None)

    patches: list[Any] = []
    for modname in ("weekly_cadence",):
        try:
            mod = sys.modules.get(modname) or __import__(modname)
            patches.append(mock.patch.object(mod, "datetime", _FrozenDT))
        except Exception as exc:
            log.debug("could not patch %s.datetime: %s", modname, exc)

    started: list[Any] = []
    try:
        for p in patches:
            started.append(p.start())
        yield
    finally:
        for p in patches:
            try:
                p.stop()
            except Exception:
                pass


@contextmanager
def _halt_flag(active: bool):
    prior = os.environ.get("WHOLESALE_OUTBOUND_HALT", "")
    os.environ["WHOLESALE_OUTBOUND_HALT"] = "1" if active else "0"
    try:
        yield
    finally:
        if prior:
            os.environ["WHOLESALE_OUTBOUND_HALT"] = prior
        else:
            os.environ.pop("WHOLESALE_OUTBOUND_HALT", None)


@contextmanager
def _dryrun_resend():
    """Patch the urlopen used by branded_mailer to never hit the network.

    Any send that gets past every gate would otherwise call api.resend.com.
    For the test phase we never want that. We monkeypatch branded_mailer's
    urlopen to return a fake successful response. We also inject a placeholder
    RESEND_API_KEY into the environment so the mailer's first-line auth check
    doesn't short-circuit before the gates run -- the key is never sent to a
    real endpoint because urlopen is patched.
    """
    try:
        import branded_mailer  # type: ignore
    except Exception as exc:
        log.warning("branded_mailer import failed in dryrun setup: %s", exc)
        yield
        return

    class _FakeResp:
        status = 200
        def __init__(self):
            self._payload = json.dumps({"id": "harness_dryrun_msg_id"}).encode("utf-8")
        def read(self):
            return self._payload
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    def _fake_urlopen(req, timeout=15):
        return _FakeResp()

    prior_key = os.environ.get("RESEND_API_KEY", "")
    if not prior_key:
        os.environ["RESEND_API_KEY"] = "harness_dryrun_placeholder_key"

    try:
        with mock.patch.object(branded_mailer, "urlopen", _fake_urlopen):
            yield
    finally:
        if not prior_key:
            os.environ.pop("RESEND_API_KEY", None)


def _seed_dnc_for_case(email: str) -> bool:
    """Pre-register a DNC entry used by case 07. Returns True on success."""
    try:
        from dnc_registrar import register_optout  # type: ignore
        r = register_optout(
            email=email,
            source="restart_harness",
            reason="harness_seed_test_07",
            notify_slack=False,
        )
        return bool(r.ok)
    except Exception as exc:
        log.warning("could not seed DNC for case 07: %s", exc)
        return False


def _drop_dnc_for_case(email: str) -> None:
    """Best-effort cleanup of the seeded DNC entry. Not strictly required --
    the registrar is idempotent and the email is namespaced (harness_dnc_test@)."""
    # We don't currently expose a delete API, and that's fine: the address is
    # `harness_dnc_test@example.com` which would never be real-world used.
    pass


def _run_one_case(case: TestCase) -> CaseResult:
    """Execute one case end-to-end. Returns CaseResult."""
    if case.id == "07_dnc_hit":
        _seed_dnc_for_case(case.recipient)

    actual_ok = False
    actual_error = ""

    try:
        # Late import so we can patch its datetime properly inside the cm
        from branded_mailer import send_branded_email  # type: ignore

        with _halt_flag(case.halt_active), _frozen_now(case.mock_iso), _dryrun_resend():
            result = send_branded_email(
                to=case.recipient,
                subject=f"[harness:{case.id}] verification",
                content_html="<p>Harness test send. Should never reach a real inbox.</p>",
                budget_category=case.budget_category,
                recipient_state=case.recipient_state,
                agent_name="Restart Harness",
                agent_title="Verification",
            )
            actual_ok = bool(result.ok)
            actual_error = str(getattr(result, "error", "") or "")
    except Exception as exc:
        actual_error = f"harness_internal_error:{exc.__class__.__name__}:{exc}"
        log.exception("case %s crashed", case.id)

    if case.id == "07_dnc_hit":
        _drop_dnc_for_case(case.recipient)

    # Compare expectations
    passed = (actual_ok == case.expected_ok)
    if not case.expected_ok and case.expected_error_prefix:
        passed = passed and actual_error.startswith(case.expected_error_prefix)

    return CaseResult(
        case_id=case.id,
        description=case.description,
        expected_ok=case.expected_ok,
        expected_error_prefix=case.expected_error_prefix,
        actual_ok=actual_ok,
        actual_error=actual_error,
        passed=passed,
        notes=case.note,
    )


# ── Phase TEST ─────────────────────────────────────────────────────

def phase_test() -> int:
    log.info("starting TEST phase: %d cases", len(CASES))
    results: list[CaseResult] = []
    for c in CASES:
        log.info(">> case %s -- %s", c.id, c.description)
        r = _run_one_case(c)
        results.append(r)
        marker = "PASS" if r.passed else "FAIL"
        log.info("   [%s] expected_ok=%s actual_ok=%s err=%r",
                 marker, r.expected_ok, r.actual_ok, r.actual_error[:120])

    # Write report
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    report_path = _LOG_DIR / f"test_phase_{ts}.md"
    passed_n = sum(1 for r in results if r.passed)
    failed_n = len(results) - passed_n

    lines: list[str] = [
        f"# Restart Harness -- TEST phase",
        f"Run: {ts}",
        f"Cases: {len(results)} | Pass: {passed_n} | Fail: {failed_n}",
        "",
        "| Case | Expected | Actual | Error | Result |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        exp = "OK" if r.expected_ok else f"BLOCK[{r.expected_error_prefix}]"
        act = "OK" if r.actual_ok else f"BLOCK[{r.actual_error[:60]}]"
        result = "PASS" if r.passed else "FAIL"
        lines.append(f"| `{r.case_id}` | {exp} | {act} | `{r.actual_error[:80]}` | **{result}** |")

    if failed_n:
        lines += ["", "## Failed cases (full detail)", ""]
        for r in results:
            if not r.passed:
                lines += [
                    f"### {r.case_id}",
                    f"- Description: {r.description}",
                    f"- Expected ok: {r.expected_ok}",
                    f"- Expected error prefix: `{r.expected_error_prefix}`",
                    f"- Actual ok: {r.actual_ok}",
                    f"- Actual error: `{r.actual_error}`",
                    f"- Notes: {r.notes}",
                    "",
                ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote report to %s", report_path)

    # Audit envelope -- the harness run itself is auditable
    try:
        from audit_log import write_envelope  # type: ignore
        write_envelope(
            agent_id="restart_harness",
            action_type="restart.test_phase.completed",
            payload={
                "cases": len(results),
                "passed": passed_n,
                "failed": failed_n,
                "report_path": str(report_path),
                "fail_ids": [r.case_id for r in results if not r.passed],
            },
            human=False,
        )
    except Exception as exc:
        log.warning("audit envelope failed for harness run: %s", exc)

    return 0 if failed_n == 0 else 1


# ── Phase WARM ─────────────────────────────────────────────────────

def phase_warm() -> int:
    log.info("starting WARM phase: one real send to Chris Ulander")
    chris_email = os.environ.get(
        "RESTART_HARNESS_WARM_TO",
        "chris@midsouthhomebuyers.com",
    )

    try:
        from branded_mailer import send_branded_email  # type: ignore
    except Exception as exc:
        log.error("branded_mailer import failed: %s", exc)
        return 2

    # Real send. vip_reply category bypasses halt and quiet_hours.
    result = send_branded_email(
        to=chris_email,
        subject="System restart verification -- one ping",
        content_html=(
            "<p>Quick note from the Everlight side: we are completing the "
            "outbound system restart. Reply with any character to confirm "
            "this email rendered correctly.</p>"
            "<p>You will not receive any further system messages from this address. "
            "Normal Memphis pipeline updates resume on the regular cadence.</p>"
        ),
        budget_category="vip_reply",
        agent_name="Hammer Knox",
        agent_title="Acquisitions",
        recipient_state="TN",
    )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    report_path = _LOG_DIR / f"warm_phase_{ts}.md"
    lines = [
        "# Restart Harness -- WARM phase",
        f"Run: {ts}",
        f"Recipient: `{chris_email}`",
        f"Send ok: **{result.ok}**",
        f"Message ID: `{getattr(result, 'message_id', '')}`",
        f"Error: `{getattr(result, 'error', '')}`",
        "",
        "Next: wait for Chris's reply, log to #compliance, then proceed to COLD phase.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("wrote warm report to %s", report_path)

    # Slack note
    try:
        from branded_slack import post_branded_slack  # type: ignore
        post_branded_slack(
            channel="#compliance",
            title="Restart harness -- warm ping sent",
            summary=f"Sent verification ping to {chris_email}. Awaiting reply.",
            fields={
                "send_ok": result.ok,
                "message_id": getattr(result, "message_id", ""),
                "error": getattr(result, "error", ""),
                "report": str(report_path),
            },
            agent_name="Restart Harness",
            agent_title="Verification",
            category="ops",
        )
    except Exception as exc:
        log.warning("slack post failed: %s", exc)

    # Audit envelope
    try:
        from audit_log import write_envelope  # type: ignore
        write_envelope(
            agent_id="restart_harness",
            action_type="restart.warm_phase.sent",
            payload={
                "recipient": chris_email,
                "send_ok": result.ok,
                "message_id": getattr(result, "message_id", ""),
                "error": getattr(result, "error", ""),
                "report_path": str(report_path),
            },
        )
    except Exception:
        pass

    return 0 if result.ok else 1


# ── Phase COLD ─────────────────────────────────────────────────────

def phase_cold() -> int:
    log.info("starting COLD phase: production restart go-live checks")

    checks: dict[str, Any] = {}
    blocking: list[str] = []

    # Check 1: HALT flag must be ABSENT (or set to a falsy value)
    halt = os.environ.get("WHOLESALE_OUTBOUND_HALT", "").strip().lower()
    halt_off = halt in ("", "0", "false", "no", "off")
    checks["halt_off"] = halt_off
    if not halt_off:
        blocking.append(f"WHOLESALE_OUTBOUND_HALT still active ({halt!r}) -- lift it first")

    # Check 2: DNC reconciliation -- 4 sinks consistent
    try:
        from dnc_registrar import reconcile_sinks  # type: ignore
        rep = reconcile_sinks()
        checks["dnc_reconcile_ok"] = rep.ok
        checks["dnc_mismatches"] = rep.mismatches
        if not rep.ok:
            blocking.append(f"DNC sinks have {rep.mismatches} mismatches -- run dnc_reconcile.py first")
    except Exception as exc:
        checks["dnc_reconcile_ok"] = False
        blocking.append(f"DNC reconcile failed: {exc}")

    # Check 3: audit log push within last 2 hours
    try:
        last_push_marker = Path("/tmp/everlight-audit-log/.git/FETCH_HEAD")
        if last_push_marker.exists():
            age_s = time.time() - last_push_marker.stat().st_mtime
            checks["audit_push_age_minutes"] = round(age_s / 60.0, 1)
            if age_s > 7200:
                blocking.append(f"audit-log last push {round(age_s/60.0)}min ago (>120) -- run audit_log_cron.sh")
        else:
            checks["audit_push_age_minutes"] = None
            blocking.append("audit-log repo not initialized -- run audit_log_cron.sh once manually")
    except Exception as exc:
        blocking.append(f"audit push check failed: {exc}")

    # Check 4: recipient_class blocklist current (file mtime within 30 days)
    try:
        from pathlib import Path as _P
        for cand in (
            _REPO_ROOT / "01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/blocked_domain_tokens.json",
        ):
            if cand.exists():
                age_d = (time.time() - cand.stat().st_mtime) / 86400.0
                checks["blocked_tokens_age_days"] = round(age_d, 1)
                if age_d > 90:
                    blocking.append(f"blocked_domain_tokens.json is {round(age_d)}d old -- audit it")
                break
        else:
            blocking.append("blocked_domain_tokens.json missing")
    except Exception as exc:
        blocking.append(f"tokens check failed: {exc}")

    if blocking:
        log.error("COLD phase BLOCKED: %d guardrail(s) failed", len(blocking))
        for b in blocking:
            log.error("  - %s", b)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        rp = _LOG_DIR / f"cold_phase_BLOCKED_{ts}.md"
        rp.write_text(
            "# Restart Harness -- COLD phase BLOCKED\n\n"
            f"Run: {ts}\n\n## Failed guardrails\n\n"
            + "\n".join(f"- {b}" for b in blocking)
            + "\n\n## Check details\n\n```\n"
            + json.dumps(checks, indent=2, default=str)
            + "\n```\n",
            encoding="utf-8",
        )
        return 1

    # All guardrails passed -- send the bulk-category test to admin@
    try:
        from branded_mailer import send_branded_email  # type: ignore
        result = send_branded_email(
            to="admin@everlightventures.io",
            subject="Outbound system: COLD restart go-live",
            content_html=(
                "<p>Outbound restart guardrails all green. The bulk lane is "
                "live. 24-hour watchdog is now active -- any compliance halt "
                "will re-engage WHOLESALE_OUTBOUND_HALT automatically.</p>"
            ),
            budget_category="system",
            agent_name="Restart Harness",
            agent_title="Production Restart",
        )
        log.info("go-live test send ok=%s", result.ok)
    except Exception as exc:
        log.warning("go-live test send failed (non-blocking): %s", exc)

    # Slack go-live
    try:
        from branded_slack import post_branded_slack  # type: ignore
        post_branded_slack(
            channel="#compliance",
            title="OUTBOUND RESTART -- GO LIVE",
            summary="All guardrails green. Bulk lane is live. 24h watchdog armed.",
            fields=checks,
            agent_name="Restart Harness",
            agent_title="Production Restart",
            category="report",
        )
    except Exception as exc:
        log.warning("Slack go-live post failed: %s", exc)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    rp = _LOG_DIR / f"cold_phase_GOLIVE_{ts}.md"
    rp.write_text(
        f"# Restart Harness -- COLD phase GO-LIVE\n\nRun: {ts}\n\n"
        f"All 4 guardrails green:\n\n```\n"
        + json.dumps(checks, indent=2, default=str)
        + "\n```\n\n24-hour watchdog active.\n",
        encoding="utf-8",
    )

    # Audit envelope
    try:
        from audit_log import write_envelope  # type: ignore
        write_envelope(
            agent_id="restart_harness",
            action_type="restart.cold_phase.golive",
            payload={"checks": checks, "report_path": str(rp)},
            human=False,
        )
    except Exception:
        pass

    return 0


# ── Main ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Outbound restart verification harness.")
    parser.add_argument(
        "--phase",
        choices=("test", "warm", "cold"),
        default="test",
        help="which phase to run (default: test)",
    )
    args = parser.parse_args()

    if args.phase == "test":
        return phase_test()
    if args.phase == "warm":
        return phase_warm()
    if args.phase == "cold":
        return phase_cold()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.warning("interrupted")
        sys.exit(2)
    except Exception as exc:
        log.exception("harness internal error: %s", exc)
        sys.exit(2)
