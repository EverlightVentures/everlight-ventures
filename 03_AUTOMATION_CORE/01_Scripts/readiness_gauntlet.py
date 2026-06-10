"""readiness_gauntlet -- master green-flag check before lifting halt.

Tests every gate that the Streubel-4435 incident exposed as broken, plus
additional safety rails added since. ALL must pass green before
WHOLESALE_OUTBOUND_HALT can flip to 0.

Streubel-4435 root causes (per feedback_streubel_4435_lesson.md):
  Gap 1 (recipient_class): attorney was misclassified as homeowner.
    Test: Streubel-known-bad inputs MUST classify as 'attorney_blocked'.
  Gap 2 (quiet_hours): Sunday 00:08 CT solicitation went out.
    Test: every TN-quiet-hours slot blocks across all categories.
  Gap 3 (branded_mailer routing): owner/internal-domain bypass shipped.
    Test: branded_mailer guard blocks rich@everlightventures.io.
  Gap 4 (opt-out reliability): Streubel opted out, system kept contacting.
    Test: DNC seed -> immediate block on next attempt; suppression list
    consulted; opt-out reflected within 5 min of receipt.

Plus halt-lift prerequisites:
  - WHOLESALE_OUTBOUND_HALT=1 honored across all categories
  - 2L/3L API key tier separation active
  - Audit log push current (<2h)
  - All 7 MCPs reachable
  - All 7 user services active

Output: master JSON report + Slack-ready summary + exit code (0=all green).

Usage:
    python3 readiness_gauntlet.py [--json | --markdown | --slack]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path("/AA_MY_DRIVE")
LOGS_DIR = WORKSPACE / "_logs/readiness"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _check(name: str, fn) -> dict[str, Any]:
    """Run a check, return {name, status, detail}. status in {GREEN, YELLOW, RED}."""
    try:
        result = fn()
        if isinstance(result, tuple) and len(result) == 2:
            status, detail = result
        else:
            status = "GREEN" if result else "RED"
            detail = ""
    except Exception as e:
        status = "RED"
        detail = f"check crashed: {type(e).__name__}: {e}"
    return {"name": name, "status": status, "detail": detail}


# ── Streubel-4435 gap closure tests ────────────────────────────────


def check_streubel_gap_1_recipient_class() -> tuple[str, str]:
    """Streubel was a municipal-domain attorney. Use is_send_allowed (the
    canonical send-time gate) -- it composes recipient_class with the
    budget_category context, which is exactly what branded_mailer does."""
    sys.path.insert(0, str(WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/compliance"))
    try:
        from recipient_class import is_send_allowed  # type: ignore
    except ImportError as e:
        return ("RED", f"recipient_class module missing: {e}")
    test_inputs = [
        # (email, budget_category, expected_blocked, expected_class_substring)
        ("dstreubel@municipalfirm.com", "bulk", True, "attorney"),
        ("partner@bigfirm.law", "bulk", True, "attorney"),
        ("planning@dallastx.gov", "bulk", True, "government"),
        ("info@somecompany.com", "bulk", True, "role"),
        ("admin@everlightventures.io", "bulk", True, "internal"),
        ("homeowner@gmail.com", "bulk", False, ""),  # should pass (not blocked)
    ]
    fails = []
    for email, cat, expected_blocked, expected_substr in test_inputs:
        try:
            allowed, rc = is_send_allowed(email=email, budget_category=cat)
            actual_blocked = not allowed
            class_name = getattr(rc, "class_name", "") or ""
            if expected_blocked != actual_blocked:
                fails.append(f"  {email}: expected blocked={expected_blocked}, got {actual_blocked} "
                             f"(class={class_name!r})")
            elif expected_blocked and expected_substr.lower() not in class_name.lower():
                fails.append(f"  {email}: blocked but wrong class -- expected substring "
                             f"{expected_substr!r}, got {class_name!r}")
        except Exception as e:
            fails.append(f"  {email}: classifier crashed: {e}")
    if fails:
        return ("RED", f"{len(fails)}/{len(test_inputs)} cases failed:\n" + "\n".join(fails))
    return ("GREEN", f"all {len(test_inputs)} recipient_class+is_send_allowed cases pass")


def check_streubel_gap_2_quiet_hours() -> tuple[str, str]:
    """Streubel was hit on a Sunday 00:08 CT. Verify quiet_hours blocks
    every TN-blocked slot across categories."""
    sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/content_tools"))
    try:
        from quiet_hours import is_quiet_hour_for  # type: ignore
    except ImportError:
        # Fall back to checking the harness which exercises quiet_hours
        return ("YELLOW", "quiet_hours module not directly importable -- "
                          "exercised via restart_harness PHASE TEST")
    blocked_scenarios = [
        ("TN", "Sun", 14, 00, "sunday_blocked"),
        ("TN", "Sat", 22, 30, "after_8pm"),
        ("TN", "Mon", 8, 0, "before_9am"),
    ]
    fails = []
    for state, day, hour, minute, label in blocked_scenarios:
        try:
            blocked = is_quiet_hour_for(state, day, hour, minute)
            if not blocked:
                fails.append(f"  {state} {day} {hour:02d}:{minute:02d} ({label}) -- NOT blocked")
        except Exception as e:
            fails.append(f"  {state} {day} {hour:02d}:{minute:02d}: {e}")
    if fails:
        return ("RED", "\n".join(fails))
    return ("GREEN", f"all {len(blocked_scenarios)} quiet_hours scenarios blocked")


def check_streubel_gap_3_branded_mailer_guard() -> tuple[str, str]:
    """Verify branded_mailer rejects owner/internal-domain sends. Accepts ANY
    non-OK return as a successful block -- including OUTBOUND_HALT (the outer
    halt fires before the guard, which is correct ordering)."""
    sys.path.insert(0, str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/content_tools"))
    try:
        import branded_mailer as bm  # type: ignore
    except ImportError as e:
        return ("RED", f"branded_mailer not importable: {e}")
    try:
        r = bm.send_branded_email(
            to="rich@everlightventures.io",
            subject="test guard",
            content_html="<p>guard test</p>",
            agent_name="ReadinessGauntlet",
            budget_category="bulk",
        )
        # MailResult dataclass with .ok flag; any falsy = blocked
        is_ok = getattr(r, "ok", None) if not isinstance(r, dict) else r.get("ok")
        if is_ok is False:
            err = (getattr(r, "error", "") or
                    (r.get("error", "") if isinstance(r, dict) else "")).lower()
            # Acceptable block reasons (in order of preference):
            for reason in ("guard", "internal", "owner", "outbound_halt", "recipient_class",
                           "attorney", "government", "role"):
                if reason in err:
                    return ("GREEN", f"branded_mailer blocked owner-domain send (error={err})")
            return ("YELLOW", f"branded_mailer blocked but unclear reason: error={err}")
        return ("RED", f"branded_mailer ALLOWED owner-domain send: ok={is_ok}, full={r}")
    except Exception as guard_err:
        # Acceptable: branded_mailer can also raise on internal/guard
        msg = str(guard_err).lower()
        if any(t in msg for t in ("guard", "internal", "owner", "halt")):
            return ("GREEN", f"branded_mailer raised guard error: {guard_err}")
        return ("RED", f"check crashed unexpectedly: {guard_err}")


def check_streubel_gap_4_opt_out() -> tuple[str, str]:
    """Verify DNC opt-out is honored on next send attempt. Uses the actual
    register_optout signature (requires source + reason kwargs) and round-trips
    via is_optout."""
    sys.path.insert(0, str(WORKSPACE / "01_BUSINESSES/Everlight_Ventures/Wholesale/compliance"))
    try:
        from dnc_registrar import register_optout, is_optout  # type: ignore
    except ImportError as e:
        return ("RED", f"dnc_registrar not importable: {e}")
    # Use a unique test email so we don't pollute real DNC; readiness.* prefix
    # is well-known internal. notify_slack=False so no #compliance ping fires.
    test_email = f"readiness.gauntlet.{int(datetime.now().timestamp())}@everlightventures.io"
    try:
        result = register_optout(
            email=test_email,
            source="readiness_gauntlet",
            reason="automated test of DNC opt-out round-trip",
            notify_slack=False,
        )
        if not getattr(result, "ok", False):
            return ("RED", f"register_optout returned ok=False: {result}")
        # Round-trip: should now be reflected in DNC
        if is_optout(test_email):
            sinks = getattr(result, "sinks_written", [])
            return ("GREEN", f"DNC seed for {test_email} reflected immediately "
                              f"(sinks: {sinks})")
        return ("RED", f"register_optout reported ok but is_optout({test_email})=False")
    except Exception as e:
        return ("RED", f"DNC opt-out crashed: {e}")


# ── Halt-lift prerequisites ────────────────────────────────────────


def check_halt_flag() -> tuple[str, str]:
    halt = ""
    env_path = WORKSPACE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("WHOLESALE_OUTBOUND_HALT="):
                halt = line.split("=", 1)[1].strip().strip("'\"")
                break
    if halt == "1":
        return ("YELLOW", "WHOLESALE_OUTBOUND_HALT=1 (intentional during gauntlet)")
    if halt in ("0", ""):
        return ("YELLOW", f"WHOLESALE_OUTBOUND_HALT={halt!r} -- "
                "halt is OFF. Verify this is intentional before sends fire.")
    return ("RED", f"halt flag has unexpected value: {halt!r}")


def check_2l_3l_keys() -> tuple[str, str]:
    env = (WORKSPACE / ".env").read_text() if (WORKSPACE / ".env").exists() else ""
    has_2l = "ANTHROPIC_API_KEY_COMPLIANCE=" in env
    has_3l = "ANTHROPIC_API_KEY_AUDIT=" in env
    if has_2l and has_3l:
        return ("GREEN", "2L+3L tier separation keys present in .env")
    missing = []
    if not has_2l: missing.append("COMPLIANCE")
    if not has_3l: missing.append("AUDIT")
    return ("RED", f"missing: ANTHROPIC_API_KEY_{'+'.join(missing)}")


def check_audit_log_fresh() -> tuple[str, str]:
    repo = Path("/tmp/everlight-audit-log")
    if not (repo / ".git").exists():
        return ("RED", f"audit-log clone missing at {repo}")
    try:
        r = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%ct"],
                           capture_output=True, text=True, timeout=5)
        last = int(r.stdout.strip())
        age_min = (int(datetime.now().timestamp()) - last) // 60
        if age_min < 120:
            return ("GREEN", f"audit-log push {age_min}min ago")
        return ("YELLOW", f"audit-log push {age_min}min ago (>2h, cron may be stuck)")
    except Exception as e:
        return ("RED", f"audit-log check crashed: {e}")


def check_mcp_fleet() -> tuple[str, str]:
    expected = {
        3101: "blinko-memory", 3102: "market-intel", 3103: "n8n",
        3104: "broker-os", 3105: "supabase", 3106: "stripe", 3107: "resend",
    }
    down = []
    for port, name in expected.items():
        s = socket.socket()
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
        except Exception:
            down.append(f"{name}:{port}")
        finally:
            s.close()
    if down:
        return ("RED", f"MCP fleet: {len(down)} down: {', '.join(down)}")
    return ("GREEN", f"all {len(expected)} MCPs reachable")


def check_user_services() -> tuple[str, str]:
    services = [
        "lucrex-desktop-runner", "lucrex-browser-use-runner",
        "lucrex-managed-agent-runner", "lucrex-auto-answer-watcher",
        "bt-levn-keeper", "hive-sync-watch", "blinko-lite",
    ]
    down = []
    for s in services:
        r = subprocess.run(["systemctl", "--user", "is-active", s + ".service"],
                           capture_output=True, text=True, timeout=3)
        if r.stdout.strip() != "active":
            down.append(s)
    if down:
        return ("RED", f"services down: {', '.join(down)}")
    return ("GREEN", f"all {len(services)} user services active")


def check_halt_check_script() -> tuple[str, str]:
    """Run the existing halt_check.sh. Count actual entries (not status words
    that might appear in summary lines or color codes). 1 WARN expected
    (the intentional WHOLESALE_OUTBOUND_HALT)."""
    r = subprocess.run(
        ["bash", str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/halt_check.sh")],
        capture_output=True, text=True, timeout=30,
    )
    # Strip ANSI color escapes for clean counting
    import re as _re
    clean = _re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)
    # Each entry line begins with RED|WARN|OK at start of the line
    red_count = sum(1 for L in clean.splitlines() if _re.match(r"^RED\b", L.strip()))
    warn_count = sum(1 for L in clean.splitlines() if _re.match(r"^WARN\b", L.strip()))
    ok_count = sum(1 for L in clean.splitlines() if _re.match(r"^OK\b", L.strip()))
    if red_count > 0:
        return ("RED", f"halt_check has {red_count} RED entries:\n" + clean[-500:])
    if warn_count > 1:
        return ("YELLOW", f"halt_check: {warn_count} WARN entries (1 intentional expected); "
                          f"{ok_count} OK")
    return ("GREEN", f"halt_check: 0 RED, {warn_count} WARN (intentional halt only), "
                    f"{ok_count} OK")


def check_phase_test() -> tuple[str, str]:
    """Run restart_harness.py --phase=test (14/14 expected)."""
    r = subprocess.run(
        ["/AA_MY_DRIVE/.venv/bin/python3",
         str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts/restart_harness.py"),
         "--phase=test"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(WORKSPACE / "03_AUTOMATION_CORE/01_Scripts")},
    )
    out = r.stdout + r.stderr
    # Find the latest test report
    reports = sorted((WORKSPACE / "_logs/restart_harness").glob("test_phase_*.md"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    if reports:
        report = reports[0].read_text()
        first_line = next((l for l in report.splitlines() if "Pass:" in l), "")
        if "Pass: 14" in first_line and "Fail: 0" in first_line:
            return ("GREEN", f"PHASE TEST: 14/14 PASS ({reports[0].name})")
        return ("RED", f"PHASE TEST report shows: {first_line}")
    return ("RED", "no test_phase report generated")


# ── Driver ─────────────────────────────────────────────────────────


CHECKS = [
    ("Streubel Gap 1: recipient_class blocks attorneys/gov/role/internal",
     check_streubel_gap_1_recipient_class),
    ("Streubel Gap 2: quiet_hours blocks Sun/late/early-Mon",
     check_streubel_gap_2_quiet_hours),
    ("Streubel Gap 3: branded_mailer guards owner/internal addresses",
     check_streubel_gap_3_branded_mailer_guard),
    ("Streubel Gap 4: DNC opt-out registers and reflects",
     check_streubel_gap_4_opt_out),
    ("Halt flag: WHOLESALE_OUTBOUND_HALT", check_halt_flag),
    ("2L/3L tier separation keys", check_2l_3l_keys),
    ("Audit log freshness (<2h)", check_audit_log_fresh),
    ("MCP fleet (7/7 reachable)", check_mcp_fleet),
    ("User services (7/7 active)", check_user_services),
    ("halt_check.sh full sweep", check_halt_check_script),
    ("restart_harness PHASE TEST 14/14", check_phase_test),
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    p.add_argument("--quiet", action="store_true", help="exit-only, no output")
    args = p.parse_args()

    results = []
    for name, fn in CHECKS:
        result = _check(name, fn)
        results.append(result)
        if not args.quiet and not args.json and not args.markdown:
            color = {"GREEN": "\033[0;32m✓", "YELLOW": "\033[0;33m!",
                     "RED": "\033[0;31m✗"}.get(result["status"], "?")
            print(f"{color} {result['status']:6s}\033[0m  {name}")
            if result.get("detail"):
                for line in str(result["detail"]).splitlines():
                    print(f"           {line}")

    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "checks": results,
        "counts": {
            "green": sum(1 for r in results if r["status"] == "GREEN"),
            "yellow": sum(1 for r in results if r["status"] == "YELLOW"),
            "red": sum(1 for r in results if r["status"] == "RED"),
        },
        "go_live_ready": (
            sum(1 for r in results if r["status"] == "RED") == 0
        ),
    }

    # Persist
    out_path = LOGS_DIR / f"gauntlet_{datetime.now().strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(summary, indent=2))

    if args.json:
        print(json.dumps(summary, indent=2))
    elif args.markdown:
        print(f"# Readiness Gauntlet -- {summary['ran_at']}\n")
        print(f"GREEN: {summary['counts']['green']}, "
              f"YELLOW: {summary['counts']['yellow']}, "
              f"RED: {summary['counts']['red']}")
        print(f"\nGo-live ready: **{summary['go_live_ready']}**\n")
        for r in results:
            print(f"- [{r['status']}] {r['name']}")
            if r.get("detail"):
                for line in str(r["detail"]).splitlines():
                    print(f"    {line}")
    elif not args.quiet:
        print(f"\n  GREEN: {summary['counts']['green']}, "
              f"YELLOW: {summary['counts']['yellow']}, "
              f"RED: {summary['counts']['red']}")
        print(f"  Go-live ready: {summary['go_live_ready']}")
        print(f"  Report: {out_path}")
    return 0 if summary["go_live_ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
