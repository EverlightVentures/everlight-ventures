#!/usr/bin/env python3
"""
Broker OS — Daily Orchestrator
Marcus Cole / Chief Operator — Everlight Ventures

Full daily pipeline cycle:
  1. Expire stale pending matches (>48h, no outreach sent)
  2. Run matching engine against all active offers + live leads
  3. Auto-approve high-confidence matches (score >= 65)
  4. Schedule next outreach steps for approved matches
  5. Generate KPI report
  6. Post comprehensive status to Slack #broker-pipeline

Usage:
  python3 broker_daily_orchestrator.py           # Full cycle
  python3 broker_daily_orchestrator.py --dry-run # Preview only, no DB writes
  python3 broker_daily_orchestrator.py --status  # Status report only, no pipeline run
  python3 broker_daily_orchestrator.py --slack-only  # Re-post last status to Slack

Env vars:
  DJANGO_SETTINGS_MODULE  (default: hive_dashboard.settings)
  SLACK_BROKER_WEBHOOK    Slack incoming webhook for #broker-pipeline channel
  BROKER_MIN_SCORE        Minimum match score to keep (default 60)
  BROKER_AUTO_APPROVE_MIN Auto-approve threshold (default 65)

Schedule:
  Cron: 0 7 * * *   (07:00 daily, before the team day starts)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap Django
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]  # /AA_MY_DRIVE
DASHBOARD_PATH = REPO_ROOT / "09_DASHBOARD" / "hive_dashboard"

sys.path.insert(0, str(DASHBOARD_PATH))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")

try:
    import django
    django.setup()
    DJANGO_OK = True
except Exception as e:
    DJANGO_OK = False
    _DJANGO_ERROR = str(e)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = REPO_ROOT / "_logs" / "broker_ops"
LOG_DIR.mkdir(parents=True, exist_ok=True)

today_str = datetime.now().strftime("%Y-%m-%d")
log_file  = LOG_DIR / f"orchestrator_{today_str}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("broker_orchestrator")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MIN_SCORE        = float(os.environ.get("BROKER_MIN_SCORE", "60"))
AUTO_APPROVE_MIN = float(os.environ.get("BROKER_AUTO_APPROVE_MIN", "65"))
SLACK_WEBHOOK    = os.environ.get("SLACK_BROKER_WEBHOOK", "")


# ---------------------------------------------------------------------------
# Slack helper
# ---------------------------------------------------------------------------

def _post_slack(text: str, blocks: list | None = None) -> bool:
    """Post to Slack #broker-pipeline. Falls back to console if no webhook."""
    if not SLACK_WEBHOOK:
        log.info("[Slack fallback — no webhook configured]\n%s", text)
        return False

    try:
        import urllib.request
        payload = json.dumps({"text": text, "blocks": blocks} if blocks else {"text": text}).encode()
        req = urllib.request.Request(
            SLACK_WEBHOOK,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = resp.status == 200
            if not ok:
                log.warning("Slack post returned %s", resp.status)
            return ok
    except Exception as exc:
        log.error("Slack post failed: %s", exc)
        return False


def _slack_blocks(report: dict, issues: list[str], top5: list[dict]) -> list:
    """Build Slack Block Kit payload for the pipeline status report."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    p  = report["pipeline"]
    c  = report["commissions"]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":bar_chart: Broker OS Daily Status — {today_str}",
                "emoji": True,
            },
        },
        {"type": "divider"},
        # Pipeline counts
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Total Offers:*\n{p['total_offers']} ({p['active_offers']} active)"},
                {"type": "mrkdwn", "text": f"*Total Leads:*\n{p['total_leads']} ({p['hot_leads']} hot / {p['warm_leads']} warm)"},
                {"type": "mrkdwn", "text": f"*Matches:*\n{p['total_matches']} total ({p['pending_matches']} pending / {p['approved_matches']} approved)"},
                {"type": "mrkdwn", "text": f"*Deals:*\n{p['total_deals']} total ({p['active_deals']} active / {p['closed_won']} won)"},
            ],
        },
        # Outreach
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Emails Sent (all-time):*\n{p['outreach_sent']}"},
                {"type": "mrkdwn", "text": f"*Outreach Pending:*\n{p['outreach_pending']}"},
                {"type": "mrkdwn", "text": f"*Opened:*\n{p['outreach_opened']}"},
                {"type": "mrkdwn", "text": f"*Replied:*\n{p['outreach_replied']}"},
            ],
        },
        # Commission
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Commission Earned:*\n${c['earned_total']:,.2f}"},
                {"type": "mrkdwn", "text": f"*Commission Pending:*\n${c['pending_total']:,.2f}"},
                {"type": "mrkdwn", "text": f"*Unpaid Balance:*\n${c['unpaid_balance']:,.2f}"},
                {"type": "mrkdwn", "text": f"*Paid Out:*\n${c['paid_total']:,.2f}"},
            ],
        },
        {"type": "divider"},
    ]

    # Top 5 actionable matches
    if top5:
        match_lines = []
        for i, m in enumerate(top5[:5], 1):
            match_lines.append(
                f"{i}. *{m['score']:.0f}%* | {m['offer'][:40]} ↔ {m['lead'][:30]} [{m['status']}]"
            )
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*:dart: Top 5 Actionable Matches*\n" + "\n".join(match_lines),
            },
        })
        blocks.append({"type": "divider"})

    # Issues / flags
    if issues:
        issue_lines = "\n".join(f":warning: {iss}" for iss in issues)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Issues & Flags*\n{issue_lines}"},
        })
        blocks.append({"type": "divider"})

    # Next actions
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "*:rocket: Recommended Next Actions*\n"
                + "\n".join(f"• {a}" for a in report.get("next_actions", []))
            ),
        },
    })

    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Generated by Marcus Cole / Broker OS Orchestrator | {ts}"}],
    })

    return blocks


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def step_expire_stale(dry_run: bool = False) -> int:
    from broker_ops.services import expire_stale_matches
    count = expire_stale_matches(hours=48, dry_run=dry_run)
    log.info("Expired %d stale matches (48h, no outreach)%s", count, " [dry-run]" if dry_run else "")
    return count


def step_run_matching(dry_run: bool = False) -> list:
    from broker_ops.services import run_matching
    results = run_matching(min_score=MIN_SCORE, dry_run=dry_run)
    log.info("Matching produced %d results (min_score=%.0f)%s", len(results), MIN_SCORE, " [dry-run]" if dry_run else "")
    return results


def step_auto_approve(dry_run: bool = False) -> int:
    from broker_ops.services import auto_approve_high_score_matches
    count = auto_approve_high_score_matches(min_score=AUTO_APPROVE_MIN, limit=20, dry_run=dry_run)
    log.info("Auto-approved %d matches (score >= %.0f)%s", count, AUTO_APPROVE_MIN, " [dry-run]" if dry_run else "")
    return count


def step_schedule_outreach(dry_run: bool = False) -> int:
    """
    For every newly approved match without a buyer_intro outreach step,
    schedule the first outreach email (buyer_intro, T+0).
    """
    from django.utils import timezone as dj_tz

    from broker_ops.models import BrokerMatch, OutreachSequence
    approved_no_outreach = BrokerMatch.objects.filter(
        status="approved",
        outreach_sent_at__isnull=True,
    ).exclude(
        outreach_steps__step="buyer_intro",
    ).select_related("offer", "lead")

    count = 0
    for match in approved_no_outreach:
        if not match.lead.email or "@placeholder.io" in match.lead.email:
            continue
        if not dry_run:
            OutreachSequence.objects.get_or_create(
                match=match,
                step="buyer_intro",
                defaults={
                    "status": "pending",
                    "to_email": match.lead.email,
                    "subject": f"Intro: {match.offer.title[:60]}",
                    "scheduled_at": dj_tz.now(),
                },
            )
        count += 1

    log.info("Scheduled outreach for %d approved matches%s", count, " [dry-run]" if dry_run else "")
    return count


def collect_stats() -> dict:
    """Aggregate all pipeline stats for the report."""
    from django.db.models import Count, Sum

    from broker_ops.models import (
        BrokerMatch,
        Deal,
        LeadProfile,
        OfferListing,
        OutreachSequence,
    )
    from broker_ops.services import get_commission_summary

    commission = get_commission_summary()

    outreach_agg = OutreachSequence.objects.values("status").annotate(cnt=Count("id"))
    outreach_by_status = {row["status"]: row["cnt"] for row in outreach_agg}

    matches_agg = BrokerMatch.objects.values("status").annotate(cnt=Count("id"))
    matches_by_status = {row["status"]: row["cnt"] for row in matches_agg}

    top5 = list(
        BrokerMatch.objects.filter(
            status__in=["pending", "approved"],
        ).select_related("offer", "lead").order_by("-match_score")[:5].values(
            "match_score", "status",
            "offer__title", "lead__name", "lead__company",
        )
    )
    top5_clean = [
        {
            "score": m["match_score"],
            "status": m["status"],
            "offer": m["offer__title"],
            "lead": f"{m['lead__name']} @ {m['lead__company'] or 'Unknown'}",
        }
        for m in top5
    ]

    return {
        "pipeline": {
            "total_offers":      OfferListing.objects.count(),
            "active_offers":     OfferListing.objects.filter(status="active").count(),
            "total_leads":       LeadProfile.objects.count(),
            "hot_leads":         LeadProfile.objects.filter(intent="hot").count(),
            "warm_leads":        LeadProfile.objects.filter(intent="warm").count(),
            "cold_leads":        LeadProfile.objects.filter(intent="cold").count(),
            "unsubscribed":      LeadProfile.objects.filter(unsubscribed=True).count(),
            "total_matches":     BrokerMatch.objects.count(),
            "pending_matches":   matches_by_status.get("pending", 0),
            "approved_matches":  matches_by_status.get("approved", 0),
            "converted_matches": matches_by_status.get("converted", 0),
            "expired_matches":   matches_by_status.get("expired", 0),
            "total_deals":       Deal.objects.count(),
            "active_deals":      commission["active_deals"],
            "closed_won":        commission["closed_won"],
            "outreach_pending":  outreach_by_status.get("pending", 0),
            "outreach_sent":     outreach_by_status.get("sent", 0),
            "outreach_opened":   outreach_by_status.get("opened", 0),
            "outreach_replied":  outreach_by_status.get("replied", 0),
            "outreach_bounced":  outreach_by_status.get("bounced", 0),
        },
        "commissions": commission,
        "top5_matches": top5_clean,
    }


def flag_issues(stats: dict) -> list[str]:
    """Identify pipeline issues and opportunities."""
    issues = []
    p = stats["pipeline"]
    c = stats["commissions"]

    if p["active_offers"] == 0:
        issues.append("CRITICAL: No active offers. Ingest pipeline needs to be run (`broker_run ingest`).")

    if p["total_leads"] == 0:
        issues.append("CRITICAL: No leads in DB. Lead ingest pipeline or public form has not fired.")

    if p["total_offers"] > 0 and p["total_leads"] > 0 and p["total_matches"] == 0:
        issues.append("No matches generated yet. Run `broker_run match` to seed the match table.")

    if p["pending_matches"] > 50:
        issues.append(f"Match backlog: {p['pending_matches']} pending matches not yet reviewed. "
                      "Consider raising auto-approve threshold or manual review sprint.")

    if p["expired_matches"] > p["total_matches"] * 0.3 and p["total_matches"] > 0:
        issues.append(f"High expiry rate: {p['expired_matches']} / {p['total_matches']} matches expired. "
                      "Outreach is not keeping up with match velocity.")

    if p["outreach_bounced"] > 0:
        issues.append(f"{p['outreach_bounced']} bounced outreach emails. "
                      "Clean lead email list and check sender domain health.")

    if p["active_deals"] > 0 and c["pending_total"] > 0:
        issues.append(f"${c['pending_total']:,.2f} pending commission on {p['active_deals']} active deals — "
                      "chase closing or escalate to contracted stage.")

    if c["unpaid_balance"] > 500:
        issues.append(f"${c['unpaid_balance']:,.2f} earned but unpaid. Create Stripe invoices for open deals.")

    if not SLACK_WEBHOOK:
        issues.append("Slack webhook not configured. Set SLACK_BROKER_WEBHOOK env var or update "
                      "06_DEVELOPMENT/everlight_os/configs/everlight.yaml slack.webhook_url.")

    # Check for missing broker_ingest.py
    ingest_path = REPO_ROOT / "03_AUTOMATION_CORE" / "01_Scripts" / "broker_ingest.py"
    if not ingest_path.exists():
        issues.append("broker_ingest.py is MISSING from 03_AUTOMATION_CORE/01_Scripts/. "
                      "The `broker_run ingest` command will fail. Build the ingest script.")

    return issues


def build_next_actions(stats: dict, new_matches: int, auto_approved: int, stale_expired: int) -> list[str]:
    """Recommend next actions based on pipeline state."""
    actions = []
    p = stats["pipeline"]

    if p["active_offers"] == 0:
        actions.append("URGENT: Build broker_ingest.py and run `broker_run ingest` to seed the offer catalog.")
    else:
        actions.append(f"Offers catalog healthy: {p['active_offers']} active. "
                       "Continue sourcing from Product Hunt, Indie Hackers, and direct outreach.")

    if new_matches > 0:
        actions.append(f"Review {new_matches} new match(es) in Django admin: "
                       "http://localhost:8503/admin/broker_ops/brokermatch/?status=pending")

    if auto_approved > 0:
        actions.append(f"{auto_approved} match(es) auto-approved (score ≥{AUTO_APPROVE_MIN:.0f}). "
                       "Trigger outreach sequences via `broker_run full`.")

    if p["approved_matches"] > 0 and p["outreach_pending"] == 0:
        actions.append(f"{p['approved_matches']} approved match(es) have no outreach scheduled. "
                       "Run orchestrator with email sender enabled.")

    if p["hot_leads"] > 0:
        actions.append(f"Priority: {p['hot_leads']} HOT lead(s) in pipeline. "
                       "Manual review and personal outreach recommended within 24h.")

    if p["closed_won"] == 0 and p["total_deals"] > 0:
        actions.append(f"{p['total_deals']} deal(s) in flight, none closed won yet. "
                       "Push deals to contracted/closed stage to unlock commission.")

    if stale_expired > 0:
        actions.append(f"{stale_expired} stale match(es) expired — likely placeholder leads. "
                       "Refresh lead quality: run ingest with `--source linkedin,product_hunt`.")

    if not SLACK_WEBHOOK:
        actions.append("Configure Slack webhook in everlight.yaml to enable live #broker-pipeline alerts.")

    return actions or ["Pipeline is healthy. Run `broker_run full` tomorrow to refresh matches."]


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def run(dry_run: bool = False, status_only: bool = False, slack_only: bool = False) -> None:
    log.info("=== BROKER OS DAILY ORCHESTRATOR START === dry_run=%s date=%s", dry_run, today_str)

    if not DJANGO_OK:
        log.error("Django failed to initialise: %s", _DJANGO_ERROR)
        log.error("Ensure DJANGO_SETTINGS_MODULE is set and hive_dashboard is in PYTHONPATH.")
        sys.exit(1)

    new_matches   = 0
    auto_approved = 0
    stale_expired = 0
    outreach_sched = 0

    if not status_only and not slack_only:
        log.info("--- Step 1: Expire stale matches ---")
        stale_expired = step_expire_stale(dry_run=dry_run)

        log.info("--- Step 2: Run matching engine ---")
        match_results = step_run_matching(dry_run=dry_run)
        new_matches = len(match_results)

        log.info("--- Step 3: Auto-approve high-confidence matches ---")
        auto_approved = step_auto_approve(dry_run=dry_run)

        log.info("--- Step 4: Schedule outreach for approved matches ---")
        outreach_sched = step_schedule_outreach(dry_run=dry_run)

    log.info("--- Step 5: Collect pipeline stats ---")
    stats = collect_stats()

    log.info("--- Step 6: Flag issues ---")
    issues = flag_issues(stats)
    for iss in issues:
        log.warning("FLAG: %s", iss)

    next_actions = build_next_actions(stats, new_matches, auto_approved, stale_expired)
    stats["next_actions"] = next_actions

    # Save JSON report
    report_path = LOG_DIR / f"daily_report_{today_str}.json"
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "cycle": {
            "stale_expired": stale_expired,
            "new_matches": new_matches,
            "auto_approved": auto_approved,
            "outreach_scheduled": outreach_sched,
        },
        **stats,
        "issues": issues,
    }
    report_path.write_text(json.dumps(report_data, indent=2, default=str))
    log.info("Report saved: %s", report_path)

    # Console summary
    p = stats["pipeline"]
    c = stats["commissions"]
    print("\n" + "=" * 60)
    print(f"  BROKER OS — PIPELINE STATUS — {today_str}")
    print("=" * 60)
    print(f"  Offers    : {p['total_offers']} total / {p['active_offers']} active")
    print(f"  Leads     : {p['total_leads']} total / {p['hot_leads']} hot / {p['warm_leads']} warm")
    print(f"  Matches   : {p['total_matches']} total / {p['pending_matches']} pending / {p['approved_matches']} approved")
    print(f"  Deals     : {p['total_deals']} total / {p['active_deals']} active / {p['closed_won']} won")
    print(f"  Emails    : {p['outreach_sent']} sent / {p['outreach_opened']} opened / {p['outreach_replied']} replied")
    print(f"  Commission: ${c['earned_total']:,.2f} earned / ${c['pending_total']:,.2f} pending / ${c['unpaid_balance']:,.2f} unpaid")
    if stats["top5_matches"]:
        print("\n  Top 5 Actionable Matches:")
        for i, m in enumerate(stats["top5_matches"], 1):
            print(f"    {i}. {m['score']:.0f}% | {m['offer'][:40]} ↔ {m['lead'][:30]} [{m['status']}]")
    if issues:
        print(f"\n  ⚠  Issues ({len(issues)}):")
        for iss in issues:
            print(f"    - {iss}")
    print("\n  Recommended Next Actions:")
    for act in next_actions:
        print(f"    • {act}")
    print("=" * 60 + "\n")

    # Post to Slack #broker-pipeline
    log.info("--- Step 7: Post to Slack #broker-pipeline ---")
    blocks = _slack_blocks(stats, issues, stats["top5_matches"])
    plain_fallback = (
        f"Broker OS Daily Status — {today_str}\n"
        f"Offers: {p['total_offers']} ({p['active_offers']} active) | "
        f"Leads: {p['total_leads']} ({p['hot_leads']} hot) | "
        f"Matches: {p['total_matches']} | Deals: {p['total_deals']} ({p['closed_won']} won) | "
        f"Emails sent: {p['outreach_sent']} | "
        f"Commission: ${c['earned_total']:,.2f} earned / ${c['pending_total']:,.2f} pending"
    )
    posted = _post_slack(plain_fallback, blocks=blocks)
    log.info("Slack post: %s", "OK" if posted else "fallback (no webhook)")

    log.info("=== BROKER OS DAILY ORCHESTRATOR COMPLETE ===")


def main() -> int:
    parser = argparse.ArgumentParser(description="Broker OS Daily Orchestrator")
    parser.add_argument("--dry-run",    action="store_true", help="Preview mode — no DB writes")
    parser.add_argument("--status",     action="store_true", help="Status report only")
    parser.add_argument("--slack-only", action="store_true", help="Re-post last status to Slack")
    args = parser.parse_args()

    run(dry_run=args.dry_run, status_only=args.status, slack_only=args.slack_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
