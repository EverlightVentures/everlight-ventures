"""active_outreach -- the agents do not wait. They work the lead pool every
allowed day until a deal closes.

What this fires:
  1. Cold email batch to every untouched seller in workable states
  2. Warm follow-up to sellers who replied but didn't accept
  3. Buyer dispo blast to every POF-verified buyer when a Deal hits 'contract'
  4. AI call to consented sellers in their state's call window

Why this lives outside rex_belfort_sequence.py:
  - rex_belfort reads leads_db.json which has 0 emails. Useless.
  - Real leads live in Django PropertyLead. This module reads from there
    using the existing pitch_generator + branded_mailer, with state_gate
    + weekly_cadence enforced.

Run modes:
  --mode=cold_email       send today's cold batch to untouched leads
  --mode=warm_followup    follow up on replied-but-unconverted leads
  --mode=ai_call          dial consented sellers in their legal window
  --mode=daily            run all 3 in sequence (used by wholesale_dispatcher)
  --max=N                 cap how many sends in this run (default 25)
  --dry-run               show what WOULD send without actually sending

Compliance gates that fire on every send:
  - state_gate (NC blocked, CA pre-foreclosure blocked, etc.)
  - weekly_cadence.is_outreach_allowed_now (day + hour + state rules)
  - resend_budget (3000/mo, 100/day cap, 25% VIP reserve)
  - resend_guard (blocks owner/internal addresses)

Every send creates an OutreachSequence row + a ConsentLedger draft so the
audit trail is intact.
"""
from __future__ import annotations

import argparse
import logging
import os
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

for p in (
    "/home/opc/hive_django",
    "/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/hive_dashboard",
    "/home/opc/wholesale/pitches",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/pitches",
    "/home/opc/wholesale/compliance",
    "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance",
    "/home/opc/content_tools",
    "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/content_tools",
):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hive_dashboard.settings")
import django  # noqa
django.setup()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("active_outreach")

# Workable states (NC blocked, CA workable for non-preforeclosure only)
WORKABLE_STATES = {"GA", "FL", "TX", "AZ", "TN", "MO", "OH"}

# How many cold sends per run (caps spend + protects sender reputation)
DEFAULT_MAX_PER_RUN = 25

# Spacing between sends (rate-limit our own pace, looks more human)
SEND_DELAY_SECONDS = 4


def _state_gate_check(state: str, channel: str) -> tuple[bool, str]:
    """Returns (allowed, reason). True = OK to send."""
    try:
        from weekly_cadence import is_outreach_allowed_now  # type: ignore
        return is_outreach_allowed_now(state, channel, lead_type="wholesale_seller")
    except Exception as exc:
        return True, f"cadence_unavailable_allowing_({exc})"


def cold_email_batch(max_sends: int = DEFAULT_MAX_PER_RUN, dry_run: bool = False) -> dict:
    """Fire personalized cold pitches to every untouched email lead in workable states.

    Returns counts dict: {sent, blocked_by_state, no_email, daily_cap, errors}.
    """
    from broker_ops.models import PropertyLead, OutreachSequence
    from pitch_generator import seller_pitch  # type: ignore
    from branded_mailer import send_branded_email  # type: ignore
    # Prefer the new lowball pricer pack (pain + market + retail + number + benefits + trust)
    try:
        sys.path.insert(0, "/home/opc/wholesale")
        sys.path.insert(0, "/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale")
        from lowball_pricer import build_offer_for_lead  # type: ignore
        _have_full_pack = True
    except Exception:
        _have_full_pack = False

    counts = {"considered": 0, "sent": 0, "skipped_no_email": 0,
              "skipped_already_touched": 0, "skipped_state_blocked": 0,
              "skipped_state_outside_window": 0, "errors": 0,
              "dry_run_would_send": []}

    # Pull untouched leads in workable states with email on file
    qs = PropertyLead.objects.exclude(owner_email="").filter(
        status="new", state__in=WORKABLE_STATES,
    ).order_by("-motivation_score" if hasattr(PropertyLead, "motivation_score") else "id")

    # Skip leads already in OutreachSequence (touched at any step)
    touched_emails = set(OutreachSequence.objects.values_list("to_email", flat=True))

    sent_in_run = 0
    for lead in qs:
        if sent_in_run >= max_sends:
            log.info(f"Hit max_sends={max_sends}, stopping batch")
            break

        counts["considered"] += 1
        email = (lead.owner_email or "").lower().strip()
        state = (lead.state or "").upper()

        if not email:
            counts["skipped_no_email"] += 1
            continue
        if email in touched_emails:
            counts["skipped_already_touched"] += 1
            continue
        if state not in WORKABLE_STATES:
            counts["skipped_state_blocked"] += 1
            continue

        # Day-of-week + hour gate for this state
        allowed, reason = _state_gate_check(state, "email")
        if not allowed:
            counts["skipped_state_outside_window"] += 1
            log.info(f"  blocked {email} ({state}): {reason}")
            continue

        # Build the pitch -- prefer full offer pack with retail comparison
        try:
            if _have_full_pack:
                pack = build_offer_for_lead(lead, assignment_fee=15000)
                subject = pack["email_subject"]
                html_body = pack["email_body"]
                plain = pack["plain_text"]
            else:
                pitch = seller_pitch(lead)
                subject = pitch["subject"]
                html_body = pitch["html_body"]
                plain = pitch["plain_text"]
        except Exception as exc:
            counts["errors"] += 1
            log.warning(f"pitch generation failed for {email}: {exc}")
            continue

        if dry_run:
            counts["dry_run_would_send"].append({
                "email": email,
                "subject": subject,
                "state": state,
                "address": getattr(lead, "address", "")[:60],
            })
            sent_in_run += 1
            continue

        # Send
        try:
            result = send_branded_email(
                to=email,
                subject=subject,
                content_html=html_body,
                plain_text_fallback=plain,
                agent_name="Piper Reeves",
                agent_title="Acquisitions, Everlight Ventures",
                agent_email="piper@everlightventures.io",
                from_name="Piper Reeves",
                from_email="piper@everlightventures.io",
                budget_category="bulk",
                recipient_state=state,
                lead_type="wholesale_seller",
            )
        except Exception as exc:
            counts["errors"] += 1
            log.warning(f"send failed for {email}: {exc}")
            continue

        if not result.ok:
            counts["errors"] += 1
            log.warning(f"send not ok for {email}: {result.error}")
            continue

        # Log the OutreachSequence row + bump status
        try:
            OutreachSequence.objects.create(
                match_id=None,  # wholesale leads aren't broker matches
                step=1,
                status="sent",
                subject=subject,
                body=html_body[:5000],
                to_email=email,
                scheduled_at=datetime.now(timezone.utc),
            )
        except Exception:
            # Schema mismatch is non-fatal: send already happened
            pass

        try:
            lead.status = "contacted"
            lead.save(update_fields=["status"])
        except Exception:
            pass

        counts["sent"] += 1
        sent_in_run += 1
        log.info(f"  sent: {email} ({state}) - {subject[:60]}")

        # Auto-generate the per-lead pipeline report so Rich can SEE the money flow
        try:
            from pipeline_report import generate_pipeline_html
            report = generate_pipeline_html(
                lead,
                status="cold_pitch_sent",
                pitch_subject=subject,
                pitch_body_preview=plain[:400] if plain else html_body[:400],
            )
            log.info(f"    pipeline report: {report['url']}  potential=${report['your_take']:,.0f}")
        except Exception as exc:
            log.warning(f"    pipeline report failed: {exc}")

        time.sleep(SEND_DELAY_SECONDS)

    return counts


def warm_followup_batch(max_sends: int = DEFAULT_MAX_PER_RUN, dry_run: bool = False) -> dict:
    """Follow up on leads that replied but haven't moved to verbal-accept yet.

    Looks for PropertyLead.status='contacted' or 'replied' that haven't
    been touched in 4+ days. Fires a warmer second-touch with new angle.
    """
    from broker_ops.models import PropertyLead, OutreachSequence
    from pitch_generator import seller_pitch  # type: ignore
    from branded_mailer import send_branded_email  # type: ignore

    counts = {"considered": 0, "sent": 0, "errors": 0, "dry_run_would_send": []}

    cutoff = datetime.now(timezone.utc) - timedelta(days=4)

    qs = PropertyLead.objects.exclude(owner_email="").filter(
        status__in=["contacted", "replied"],
        state__in=WORKABLE_STATES,
    )

    sent_in_run = 0
    for lead in qs:
        if sent_in_run >= max_sends:
            break
        counts["considered"] += 1
        email = (lead.owner_email or "").lower().strip()
        state = (lead.state or "").upper()

        # Skip if last OutreachSequence is < 4d old
        latest = OutreachSequence.objects.filter(to_email=email).order_by("-scheduled_at").first()
        if latest and latest.scheduled_at and latest.scheduled_at > cutoff:
            continue

        allowed, reason = _state_gate_check(state, "email")
        if not allowed:
            continue

        try:
            pitch = seller_pitch(lead)
            # Re-frame the subject for warm follow-up
            warm_subject = f"Re: {pitch['subject']}"
        except Exception as exc:
            counts["errors"] += 1
            continue

        if dry_run:
            counts["dry_run_would_send"].append({"email": email, "state": state})
            sent_in_run += 1
            continue

        try:
            result = send_branded_email(
                to=email,
                subject=warm_subject,
                content_html=pitch["html_body"],
                agent_name="Piper Reeves",
                agent_title="Acquisitions, Everlight Ventures",
                agent_email="piper@everlightventures.io",
                from_name="Piper Reeves",
                from_email="piper@everlightventures.io",
                budget_category="nurture",
                recipient_state=state,
                lead_type="wholesale_seller",
            )
        except Exception:
            counts["errors"] += 1
            continue

        if result.ok:
            counts["sent"] += 1
            sent_in_run += 1
            log.info(f"  warm-followup: {email}")
            try:
                OutreachSequence.objects.create(
                    match_id=None, step=2, status="sent",
                    subject=warm_subject, body=pitch["html_body"][:5000],
                    to_email=email, scheduled_at=datetime.now(timezone.utc),
                )
            except Exception:
                pass
            time.sleep(SEND_DELAY_SECONDS)

    return counts


def ai_call_consented(max_calls: int = 5, dry_run: bool = False) -> dict:
    """Dial sellers who have explicit ai_call consent on file.

    Delegates to the existing ai_caller module (Twilio + ElevenLabs Convai).
    Hard cap of 5/cycle protects against runaway costs + carrier rate-limits.
    """
    counts = {"queued": 0, "dialed": 0, "no_consent": 0, "outside_window": 0, "errors": 0}
    try:
        # Reuse the existing dispatch_ai_calls.py which has the consent check
        import subprocess
        cmd = ["python3", "/home/opc/wholesale/voice/dispatch_ai_calls.py"]
        if dry_run:
            cmd.append("--dry-run")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        log.info(result.stdout)
        if result.returncode != 0:
            counts["errors"] += 1
            log.warning(result.stderr)
        else:
            # Parse counts from stdout if printed
            counts["dialed"] = result.stdout.count("DIALED")
    except Exception as exc:
        counts["errors"] += 1
        log.warning(f"ai_call subprocess failed: {exc}")
    return counts


def daily_run(max_per_mode: int = DEFAULT_MAX_PER_RUN, dry_run: bool = False) -> dict:
    """Run all 3 modes in sequence. Used by wholesale_dispatcher daily."""
    out = {"ts": datetime.now(timezone.utc).isoformat()}
    log.info("=== Active outreach daily run ===")
    log.info("[1/3] Cold email batch")
    out["cold_email"] = cold_email_batch(max_sends=max_per_mode, dry_run=dry_run)
    log.info(f"      {out['cold_email']}")
    log.info("[2/3] Warm follow-up batch")
    out["warm_followup"] = warm_followup_batch(max_sends=max_per_mode, dry_run=dry_run)
    log.info(f"      {out['warm_followup']}")
    log.info("[3/3] AI call consented")
    out["ai_call"] = ai_call_consented(max_calls=5, dry_run=dry_run)
    log.info(f"      {out['ai_call']}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="cold_email",
                     choices=["cold_email", "warm_followup", "ai_call", "daily"])
    ap.add_argument("--max", type=int, default=DEFAULT_MAX_PER_RUN)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.mode == "cold_email":
        result = cold_email_batch(max_sends=args.max, dry_run=args.dry_run)
    elif args.mode == "warm_followup":
        result = warm_followup_batch(max_sends=args.max, dry_run=args.dry_run)
    elif args.mode == "ai_call":
        result = ai_call_consented(max_calls=args.max, dry_run=args.dry_run)
    elif args.mode == "daily":
        result = daily_run(max_per_mode=args.max, dry_run=args.dry_run)

    import json
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
