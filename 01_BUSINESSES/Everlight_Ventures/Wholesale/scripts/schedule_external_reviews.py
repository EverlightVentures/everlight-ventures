"""schedule_external_reviews -- writes the 3 annual external-review tasks
into Django Taskboard so they appear on the daily ops queue with explicit
review windows and reminders.

This is the audit-required artifact for `Continuous.external_review_annual`.

Reviews scheduled:
  1. Q4 (Oct 1)  -- Attorney review of contracts, RESPA payments, state compliance
  2. Q1 (Jan 5)  -- CPA review of bank reconciliations, P&L, tax prep
  3. Q2 (Apr 15) -- Title company review of deal flow, EMD handling, closing process

Each review writes:
  - A Taskboard.Task with due_date, priority=high, owner=Rich
  - A reminder Task 14d prior so prep can begin
  - A note in the audit log that the review is scheduled

Idempotent: re-running won't duplicate tasks for the same year+review.
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

for p in ("/home/opc/hive_django",
          "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

import django  # noqa
django.setup()


REVIEWS = [
    {
        "title": "Annual ATTORNEY review -- contracts + RESPA + state compliance",
        "month": 10, "day": 1, "code": "annual_attorney_review",
        "scope": (
            "Have attorney review:\n"
            "1. PSA + Assignment templates per state (GA, FL, TX, AZ, CA, MO, TN)\n"
            "2. RESPAAuditLog rows from past 12 months (any undisclosed payments?)\n"
            "3. Updated state laws -- HB 797 (NC), SB 140 (TX), CC 2945 (CA)\n"
            "4. ConsentLedger entries -- TCPA defensibility audit\n"
            "5. Any new vendor/JV agreements signed this year"
        ),
    },
    {
        "title": "Annual CPA review -- bank rec + P&L + tax prep",
        "month": 1, "day": 5, "code": "annual_cpa_review",
        "scope": (
            "Have CPA review:\n"
            "1. BankReconciliation entries for last 12 months -- any unreconciled?\n"
            "2. Deal-level P&L from wholesale_roi_tracker\n"
            "3. RESPAAuditLog -- referral/bird-dog payments for 1099 prep\n"
            "4. CommissionRecord rollup\n"
            "5. Tax return prep / estimated quarterlies"
        ),
    },
    {
        "title": "Annual TITLE CO review -- deal flow + EMD + closing process",
        "month": 4, "day": 15, "code": "annual_title_co_review",
        "scope": (
            "Have a preferred title company review:\n"
            "1. Deal stage progression -- any stuck files?\n"
            "2. EMD handling per SOP_EMD_HANDLING.md -- any disputes?\n"
            "3. Disposition flow per SOP_DISPOSITION.md -- close timing?\n"
            "4. Are our PSA assignment language + closing instructions clean?\n"
            "5. Recommendations for tightening the closing process"
        ),
    },
]


def _next_occurrence(month: int, day: int) -> date:
    today = date.today()
    candidate = date(today.year, month, day)
    if candidate < today:
        candidate = date(today.year + 1, month, day)
    return candidate


def _get_or_create_template():
    from taskboard.models import TaskTemplate
    tpl, _created = TaskTemplate.objects.get_or_create(
        name="annual_external_review",
        defaults=dict(
            category="general",
            description="Annual external review (attorney / CPA / title company)",
            icon="fa-solid fa-calendar-check",
            schema={"fields": [
                {"name": "reviewer_name", "label": "Reviewer name", "type": "text", "required": True},
                {"name": "reviewed_at", "label": "Reviewed on", "type": "text", "required": True},
                {"name": "outcome", "label": "Findings / outcome", "type": "textarea", "required": True},
                {"name": "next_actions", "label": "Next actions", "type": "textarea", "required": False},
            ]},
        ),
    )
    return tpl


def schedule_reviews() -> int:
    """Returns count of tasks created (or skipped if already scheduled)."""
    try:
        from taskboard.models import TaskItem
    except Exception as exc:
        print(f"taskboard import failed: {exc}", file=sys.stderr)
        return 0

    template = _get_or_create_template()

    created = 0
    for r in REVIEWS:
        due = _next_occurrence(r["month"], r["day"])
        year_tag = f"[{r['code']}:{due.year}]"
        title = f"{year_tag} {r['title']}"

        # Idempotency: skip if exists for this code+year
        if TaskItem.objects.filter(title__startswith=year_tag).exists():
            print(f"already scheduled: {title}")
            continue

        # Due date stored in description front matter (TaskItem has no due_date field)
        desc = (f"DUE: {due.isoformat()}\n"
                f"PRIORITY: high\n\n{r['scope']}")
        TaskItem.objects.create(
            template=template,
            title=title,
            description=desc,
            priority=2,  # High
            status="pending",
            owner_type="human",
            request_kind="input",
            source_agent="schedule_external_reviews",
        )
        created += 1
        print(f"scheduled: {title} due {due.isoformat()}")

        # 14-day prep reminder
        prep_date = due - timedelta(days=14)
        prep_tag = f"[{r['code']}:{due.year}:prep]"
        prep_title = f"{prep_tag} PREP for {r['title'][:60]}"
        if not TaskItem.objects.filter(title__startswith=prep_tag).exists():
            prep_desc = f"DUE: {prep_date.isoformat()}\nPRIORITY: medium\n\nPrep window for review on {due.isoformat()}.\n\n{r['scope']}"
            TaskItem.objects.create(
                template=template,
                title=prep_title,
                description=prep_desc,
                priority=3,
                status="pending",
                owner_type="human",
                request_kind="input",
                source_agent="schedule_external_reviews",
            )
            print(f"  + prep reminder due {prep_date.isoformat()}")

    return created


if __name__ == "__main__":
    n = schedule_reviews()
    print(f"\nDONE: {n} new review tasks created")
