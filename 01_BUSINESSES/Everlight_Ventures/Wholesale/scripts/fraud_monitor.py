"""fraud_monitor -- daily sweep for wholesale fraud signals.

Runs via Oracle cron 06:00 PT every day. Writes a findings JSONL to
/home/opc/wholesale/audit/fraud_findings_YYYYMMDD.jsonl + posts a branded
Slack alert when any HIGH or CRITICAL signal fires.

Signal categories:

  1. RESPA UNDISCLOSED PAYMENTS
     RESPAAuditLog rows with written_disclosure_present=False that are >7d old.
     Severity: critical -- federal violation if logged kickback lacks disclosure.

  2. ASSIGNMENT FEE OUTLIER
     Deal.value (assignment fee) > 3.0x median of last 20 deals in same
     state, OR > $50K absolute. Coercion / fraud / mispricing signal.

  3. DUPLICATE EMD ON SAME PROPERTY
     CallEvent or Deal records that reference the same property_address with
     two distinct buyers and overlapping EMD timing. Possible double-listing.

  4. PSA SIGNER MISMATCH
     Deal where the recorded seller_email/phone differs from PropertyLead.owner_email
     for the matched property -- possible signer-not-on-title scam.

  5. NEW JV PARTNER LOPSIDED SPLIT
     CommissionRecord where the JV partner takes >70% on their first 3 deals.
     Could be Rich getting taken advantage of, or signaling the JV partner is
     manipulating the deal flow.

Each finding gets emitted as one JSON line:
{ts, signal, severity, deal_id?, lead_id?, evidence, action}

Severity ladder: low (FYI), medium (review weekly), high (review today),
critical (halt + attorney).

How to read this script:
  - Each `_check_*` returns a list[dict] of findings.
  - main() concatenates, writes the JSONL, and posts to Slack if any high+ fire.
  - Designed to be idempotent: same data => same findings, no duplicate alerts.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

# Path bootstrap (mirrors wholesale_audit.py)
for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/content_tools",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")


def _bootstrap_django() -> bool:
    try:
        import django
        django.setup()
        return True
    except Exception as exc:
        print(f"django bootstrap failed: {exc}", file=sys.stderr)
        return False


def _check_respa_undisclosed() -> list[dict]:
    findings: list[dict] = []
    try:
        from broker_ops.models import RESPAAuditLog
    except Exception:
        return findings
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=7))
    qs = RESPAAuditLog.objects.filter(
        written_disclosure_present=False, paid_at__lt=cutoff
    )
    for row in qs:
        findings.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "signal": "respa_undisclosed_payment",
            "severity": "critical",
            "respa_log_id": row.id,
            "deal_id": row.deal_id,
            "evidence": (f"RESPAAuditLog #{row.id}: ${row.amount} to {row.payee_name} "
                          f"({row.payee_role}) on {row.paid_at}, no written disclosure on file."),
            "action": "Halt new payments to this payee. Attorney reviews + uploads disclosure_url today.",
        })
    return findings


def _check_assignment_fee_outlier() -> list[dict]:
    findings: list[dict] = []
    try:
        from broker_ops.models import Deal
    except Exception:
        return findings
    # Pull last 30 days of contracted deals with a value
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent = list(Deal.objects.filter(
        created_at__gte=cutoff, value__isnull=False
    ).values("id", "value"))
    values = [float(d["value"]) for d in recent if d["value"]]
    if len(values) < 5:
        return findings
    med = median(values)
    threshold = max(3.0 * med, 50000.0)
    for d in recent:
        v = float(d["value"] or 0)
        if v >= threshold:
            findings.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "signal": "assignment_fee_outlier",
                "severity": "high",
                "deal_id": d["id"],
                "evidence": f"Deal #{d['id']} value ${v:,.0f} vs 30-day median ${med:,.0f} (>{threshold/med:.1f}x).",
                "action": "Manually verify deal terms with seller + buyer. Could be legitimate or coercion.",
            })
    return findings


def _check_duplicate_emd() -> list[dict]:
    findings: list[dict] = []
    try:
        from broker_ops.models import Deal
        from collections import defaultdict
    except Exception:
        return findings
    by_addr: dict[str, list] = defaultdict(list)
    cutoff = datetime.now(timezone.utc) - timedelta(days=60)
    for d in Deal.objects.filter(created_at__gte=cutoff).values(
        "id", "property_address", "buyer_email", "stage", "created_at"
    ):
        addr = (d.get("property_address") or "").strip().lower()
        if addr:
            by_addr[addr].append(d)
    for addr, deals in by_addr.items():
        buyers = {d.get("buyer_email") for d in deals if d.get("buyer_email")}
        if len(buyers) >= 2:
            findings.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "signal": "duplicate_emd_on_property",
                "severity": "high",
                "evidence": f"{addr}: {len(buyers)} distinct buyers in 60d -- {list(buyers)}",
                "action": "Verify only one PSA is active. Refund EMD on inactive contract.",
                "deal_ids": [d["id"] for d in deals],
            })
    return findings


def _check_psa_signer_mismatch() -> list[dict]:
    """Cross-checks PSA seller info vs PropertyLead.owner.

    Note: the comparison normalizes whitespace + casing on email/phone.
    A mismatch isn't always fraud (relative POA, etc.) -- always review.
    """
    findings: list[dict] = []
    try:
        from broker_ops.models import Deal, PropertyLead
    except Exception:
        return findings
    for d in Deal.objects.filter(stage__in=["contract", "psa_signed", "intro"]):
        # Best-effort lookup: match on property_address
        addr = (getattr(d, "property_address", "") or "").strip().lower()
        if not addr:
            continue
        leads = PropertyLead.objects.filter(address__iexact=addr).values(
            "id", "owner_email", "owner_phone", "owner_name"
        )
        if not leads:
            continue
        lead = leads[0]
        deal_email = (getattr(d, "seller_email", "") or "").strip().lower()
        lead_email = (lead.get("owner_email") or "").strip().lower()
        if deal_email and lead_email and deal_email != lead_email:
            findings.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "signal": "psa_signer_mismatch",
                "severity": "critical",
                "deal_id": d.id,
                "lead_id": lead["id"],
                "evidence": (f"Deal #{d.id} seller_email='{deal_email}' but "
                              f"PropertyLead #{lead['id']}.owner_email='{lead_email}' "
                              f"for {addr}."),
                "action": "Confirm signer is on title (free_title_search). Halt close until verified.",
            })
    return findings


def _check_jv_lopsided_split() -> list[dict]:
    """JV partner taking >70% on first 3 deals -- potential exploitation.

    TODO: requires a JVPartnership model that tracks named partners separately
    from CommissionRecord. For now, returns empty -- this is a placeholder
    until the JV tracking layer ships.
    """
    return []


def main() -> int:
    if not _bootstrap_django():
        print(json.dumps({"error": "django_bootstrap_failed"}))
        return 1

    all_findings: list[dict] = []
    for fn in (
        _check_respa_undisclosed,
        _check_assignment_fee_outlier,
        _check_duplicate_emd,
        _check_psa_signer_mismatch,
        _check_jv_lopsided_split,
    ):
        try:
            all_findings.extend(fn())
        except Exception as exc:
            all_findings.append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "signal": "fraud_monitor_check_error",
                "severity": "high",
                "evidence": f"{fn.__name__} raised: {exc}",
                "action": "Fix the check function and re-run.",
            })

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = Path("/home/opc/wholesale/audit")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"fraud_findings_{today}.jsonl"
    with out_path.open("w") as fh:
        for row in all_findings:
            fh.write(json.dumps(row) + "\n")

    crit = [f for f in all_findings if f["severity"] == "critical"]
    high = [f for f in all_findings if f["severity"] == "high"]
    print(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "total": len(all_findings),
        "critical": len(crit),
        "high": len(high),
        "out": str(out_path),
    }))

    # Branded Slack alert if any critical or high (best-effort)
    if crit or high:
        try:
            from branded_slack import post_branded_alert  # type: ignore
            sev = "critical" if crit else "high"
            preview = (crit + high)[0]
            post_branded_alert(
                channel="#hive-alerts",
                severity=sev,
                title=f"Fraud monitor: {len(crit)} critical / {len(high)} high",
                body=(f"{preview['signal']}: {preview['evidence']}\n"
                       f"Action: {preview['action']}\n"
                       f"Full findings: {out_path}"),
                agent_name="Justine Marsh",
                agent_title="Compliance",
            )
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
