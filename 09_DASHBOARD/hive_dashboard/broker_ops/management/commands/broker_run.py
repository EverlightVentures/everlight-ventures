"""
Broker OS management command -- single entry point for all broker automation.

Usage:
  python3 manage.py broker_run ingest      # Run lead/offer ingest pipeline
  python3 manage.py broker_run match       # Run matching engine
  python3 manage.py broker_run report      # Generate commission/KPI report
  python3 manage.py broker_run full        # Run full daily pipeline (ingest + match + report)
  python3 manage.py broker_run status      # Show current pipeline status
"""
import json
import os
import subprocess
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from broker_ops.models import (
    BrokerMatch,
    CommissionRecord,
    Deal,
    LeadProfile,
    OfferListing,
)
from broker_ops.services import get_commission_summary, run_matching

try:
    from business_os.services import record_alert, record_event
except Exception:
    def record_event(*args, **kwargs):
        return None

    def record_alert(*args, **kwargs):
        return None


INGEST_SCRIPT = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/broker_ingest.py"
LOG_DIR = "/mnt/sdcard/AA_MY_DRIVE/_logs/broker_ops"


class Command(BaseCommand):
    help = "Broker OS automation runner"

    def add_arguments(self, parser):
        parser.add_argument(
            "action",
            choices=["ingest", "match", "report", "full", "status"],
            help="Which pipeline step to run"
        )
        parser.add_argument("--min-score", type=float, default=40.0)
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        action = options["action"]
        os.makedirs(LOG_DIR, exist_ok=True)
        if action == "status":
            self._status()
            return

        record_event(
            event_type="broker.command.started",
            source="broker_run",
            entity_type="workflow",
            entity_id=action,
            status="running",
            priority="medium",
            owner_agent="23_automation_architect",
            summary=f"broker_run {action} started.",
            payload={"dry_run": options["dry_run"]},
        )

        try:
            if action == "ingest":
                self._ingest(options["limit"])
            elif action == "match":
                self._match(options["min_score"], options["dry_run"])
            elif action == "report":
                self._report()
            elif action == "full":
                self.stdout.write("=== BROKER OS FULL PIPELINE ===")
                self._ingest(options["limit"])
                self._match(options["min_score"], options["dry_run"])
                self._report()
                self.stdout.write(self.style.SUCCESS("=== PIPELINE COMPLETE ==="))
        except Exception as exc:
            failed_event = record_event(
                event_type="broker.command.failed",
                source="broker_run",
                entity_type="workflow",
                entity_id=action,
                status="failed",
                priority="high",
                owner_agent="23_automation_architect",
                summary=f"broker_run {action} failed: {exc}",
                payload={"dry_run": options["dry_run"]},
            )
            record_alert(
                summary=f"broker_run {action} failed",
                source="broker_run",
                detail=str(exc),
                severity="error",
                alert_key=f"broker_run:{action}:failure",
                entity_type="workflow",
                entity_id=action,
                related_event=failed_event,
            )
            raise

        record_event(
            event_type="broker.command.completed",
            source="broker_run",
            entity_type="workflow",
            entity_id=action,
            status="success",
            priority="medium",
            owner_agent="23_automation_architect",
            summary=f"broker_run {action} completed.",
            payload={"dry_run": options["dry_run"]},
        )

    def _status(self):
        self.stdout.write("\n--- BROKER OS STATUS ---")
        self.stdout.write(f"Offers:  {OfferListing.objects.count()} total, {OfferListing.objects.filter(status='active').count()} active")
        self.stdout.write(f"Leads:   {LeadProfile.objects.count()} total, {LeadProfile.objects.filter(intent='hot').count()} hot")
        self.stdout.write(f"Matches: {BrokerMatch.objects.count()} total, {BrokerMatch.objects.filter(status='pending').count()} pending")
        self.stdout.write(f"Deals:   {Deal.objects.count()} total, {Deal.objects.filter(stage='closed_won').count()} won")

        summary = get_commission_summary()
        self.stdout.write(f"\nCommissions: ${summary['earned_total']:.2f} earned, ${summary['pending_total']:.2f} pending, ${summary['unpaid_balance']:.2f} unpaid")
        self.stdout.write(f"Active deals: {summary['active_deals']} | Won: {summary['closed_won']}")

    def _ingest(self, limit):
        self.stdout.write("\n--- INGEST ---")
        cmd = ["python3", INGEST_SCRIPT, "--source", "all", "--limit", str(limit)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            self.stdout.write(result.stdout)
            if result.returncode != 0:
                self.stderr.write(result.stderr)
        except FileNotFoundError:
            self.stderr.write(f"Ingest script not found at {INGEST_SCRIPT}")
        except subprocess.TimeoutExpired:
            self.stderr.write("Ingest timed out after 120s")

    def _match(self, min_score, dry_run):
        self.stdout.write(f"\n--- MATCHING (min_score={min_score}, dry_run={dry_run}) ---")
        results = run_matching(min_score=min_score, dry_run=dry_run)
        self.stdout.write(f"Matches created: {len(results)}")

        if results:
            top = sorted(results, key=lambda x: x["score"], reverse=True)[:5]
            for r in top:
                self.stdout.write(f"  {r['score']:.0f}% | {r['offer'][:40]} <-> {r['lead'][:30]}")

        # Save run log
        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(LOG_DIR, f"match_run_{today}.json")
        with open(log_path, "w") as f:
            json.dump({"timestamp": timezone.now().isoformat(), "count": len(results), "results": results[:50]}, f, indent=2)
        self.stdout.write(f"Log saved: {log_path}")

    def _report(self):
        self.stdout.write("\n--- COMMISSION REPORT ---")
        summary = get_commission_summary()
        for k, v in summary.items():
            self.stdout.write(f"  {k}: {v}")

        today = datetime.now().strftime("%Y-%m-%d")
        log_path = os.path.join(LOG_DIR, f"kpi_{today}.json")
        report = {
            "timestamp": timezone.now().isoformat(),
            "commissions": summary,
            "pipeline": {
                "total_offers": OfferListing.objects.count(),
                "active_offers": OfferListing.objects.filter(status="active").count(),
                "total_leads": LeadProfile.objects.count(),
                "hot_leads": LeadProfile.objects.filter(intent="hot").count(),
                "warm_leads": LeadProfile.objects.filter(intent="warm").count(),
                "pending_matches": BrokerMatch.objects.filter(status="pending").count(),
                "total_deals": Deal.objects.count(),
            }
        }
        with open(log_path, "w") as f:
            json.dump(report, f, indent=2)
        self.stdout.write(f"Report saved: {log_path}")
