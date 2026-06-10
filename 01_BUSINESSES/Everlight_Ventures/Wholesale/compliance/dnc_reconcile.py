#!/usr/bin/env python3
"""dnc_reconcile -- daily DNC sink reconciliation cron.

Runs once per day via cron. Calls dnc_registrar.reconcile_sinks() and posts
a branded Slack message to #compliance with:
  - Total DNC count per sink
  - Mismatches (records in one sink but not another)
  - Age of oldest entry

Exit code:
  0 -- all sinks consistent (or no DNC entries yet)
  1 -- mismatches found OR Slack post failed (so cron alert fires)

Cron line (PT, runs 9:00 AM PT daily):
  0 9 * * * /usr/bin/python3 /home/opc/wholesale/compliance/dnc_reconcile.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("dnc_reconcile")

# Defensive path fixup
_THIS = Path(__file__).resolve()
for p in (_THIS.parent, "/home/opc/wholesale/compliance",
          "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance"):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from dnc_registrar import reconcile_sinks  # type: ignore  # noqa: E402

# Defensive: branded_slack
_post = None
try:
    for p in (
        "/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
        "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
        "/home/opc/content_tools",
    ):
        if os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    from branded_slack import post_branded_slack  # type: ignore
    _post = post_branded_slack
except Exception as exc:
    log.warning("branded_slack unavailable: %s", exc)


def main() -> int:
    try:
        report = reconcile_sinks()
    except Exception as exc:
        log.exception("reconcile_sinks crashed: %s", exc)
        return 1

    log.info("reconcile result: %s", json.dumps(report.to_dict(), default=str))

    # Persist daily reconciliation log file (halt_check.sh looks for this dir)
    try:
        from datetime import datetime, timezone
        log_root = Path("/AA_MY_DRIVE/_logs/dnc_reconcile")
        log_root.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = log_root / f"{today}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        log.info("daily log written: %s", out)
    except Exception as e:
        log.warning("daily log write failed (non-fatal): %s", e)

    counts = report.counts
    summary_parts = [
        f"DNC entries: dnc_list.json={counts.get('dnc_list_json', 0)}, "
        f"opted_out_emails.json={counts.get('opted_out_emails_json', 0)}, "
        f"phrase_scrub_jsonl={counts.get('phrase_scrub_jsonl', 0)}, "
        f"supabase={counts.get('supabase_dnc_emails', 0)}.",
        f"Mismatches: {report.mismatches}.",
    ]
    if report.oldest_entry_iso:
        summary_parts.append(
            f"Oldest entry: {report.oldest_entry_iso} ({report.oldest_entry_age_days} days)."
        )
    summary = " ".join(summary_parts)

    fields: dict[str, object] = {
        "sink1_dnc_list": counts.get("dnc_list_json", 0),
        "sink2_opted_out": counts.get("opted_out_emails_json", 0),
        "sink3_phrase_scrub": counts.get("phrase_scrub_jsonl", 0),
        "sink4_supabase": counts.get("supabase_dnc_emails", 0),
        "mismatches": report.mismatches,
        "oldest_entry_age_days": report.oldest_entry_age_days,
    }
    if report.mismatches:
        # Show the first 5 of each diff to keep the message short
        for k, v in report.only_in.items():
            if v:
                fields[k] = ", ".join(v[:5]) + (f" (+{len(v)-5} more)" if len(v) > 5 else "")

    title = "DNC Reconciliation -- All Sinks Consistent" if report.ok \
            else "DNC Reconciliation -- MISMATCHES FOUND"
    category = "report" if report.ok else "alert"

    if _post is not None:
        try:
            _post(
                channel="#compliance",
                title=title,
                summary=summary,
                fields=fields,
                agent_name="DNC Registrar",
                agent_title="Compliance Backstop",
                category=category,
            )
        except Exception as exc:
            log.exception("Slack post failed: %s", exc)
            return 1
    else:
        log.warning("No Slack poster -- printing report instead")
        print(json.dumps(report.to_dict(), indent=2, default=str))

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
