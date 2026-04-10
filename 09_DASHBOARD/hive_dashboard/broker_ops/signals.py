"""
Broker OS -- Event-Driven Pipeline Signals

Instead of crons polling every N hours, these fire IMMEDIATELY when something happens:
- Deal stage changes → auto-advance pipeline
- Email reply detected → create deal, assign agent, notify Slack
- Invoice paid → update commission, celebrate
- Call logged with commitment → schedule follow-up
- Document signed → advance to next stage

The crons still exist as fallback sweeps, but signals handle the real-time flow.
"""
from __future__ import annotations

import logging
import threading
from functools import wraps

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    BrokerMatch, CallLog, ClientDocument, ClientFile,
    CommissionRecord, Deal, DealEvent, InvestorBuyer,
    OutreachSequence, PropertyLead,
)

logger = logging.getLogger("broker_ops.signals")


def _async(fn):
    """Run signal handler in a background thread so it doesn't block the save."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
        t.start()
    return wrapper


def _slack_alert(channel: str, message: str):
    """Post to Slack. Non-blocking, best-effort."""
    try:
        import os
        import requests
        token = os.getenv("SLACK_BOT_TOKEN", "")
        if not token:
            from pathlib import Path
            env_path = Path("/home/opc/.env")
            if not env_path.exists():
                env_path = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if line.startswith("SLACK_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"')
                        break
        if token:
            requests.post("https://slack.com/api/chat.postMessage",
                          headers={"Authorization": f"Bearer {token}"},
                          json={"channel": channel, "text": message},
                          timeout=10)
    except Exception as e:
        logger.warning(f"Slack alert failed: {e}")


# Channel IDs
CH_BROKER = "C0APJQX7CJ4"      # #broker-pipeline
CH_HUNTERS = "C0APJSFTFHX"      # #ft-hunters
CH_WAR_ROOM = "C08LVE3HFNM"     # #war-room
CH_REVENUE = "C0APJS4DVJ5"      # #revenue-dashboard


# ============================================================
# DEAL STAGE CHANGES -- the main event reactor
# ============================================================

@receiver(pre_save, sender=Deal)
def capture_previous_stage(sender, instance, **kwargs):
    """Stash the old stage before save so post_save can detect transitions."""
    if instance.pk:
        try:
            instance._previous_stage = Deal.objects.filter(pk=instance.pk).values_list("stage", flat=True).first()
        except Exception:
            instance._previous_stage = None
    else:
        instance._previous_stage = None


@receiver(post_save, sender=Deal)
@_async
def on_deal_stage_change(sender, instance, created, **kwargs):
    """React to deal stage transitions. This is the event-driven pipeline core."""
    deal = instance
    old_stage = getattr(deal, '_previous_stage', None)
    new_stage = deal.stage

    if created:
        logger.info(f"[EVENT] New deal created: {deal.id} stage={new_stage}")
        _slack_alert(CH_BROKER,
                     f":new: *New Deal Created*\n"
                     f"Deal `{str(deal.id)[:8]}` | Stage: {new_stage}\n"
                     f"Value: ${deal.deal_value:,.0f} | Commission: ${deal.commission_due:,.0f}")
        return

    if old_stage == new_stage:
        return  # No stage change

    logger.info(f"[EVENT] Deal {deal.id} stage: {old_stage} → {new_stage}")

    # Log the transition
    from .services import _log_deal_event
    _log_deal_event(deal, "stage_change",
                     f"Stage: {old_stage} → {new_stage}",
                     agent_name="system")

    # ---- TRANSITION HANDLERS ----

    if new_stage == "contracted":
        # Deal is contracted → auto-advance to legal review
        _handle_contracted(deal)

    elif new_stage == "legal_review":
        _slack_alert(CH_HUNTERS,
                     f":scales: *Legal Review Started*\n"
                     f"Justine Park reviewing deal `{str(deal.id)[:8]}`\n"
                     f"Value: ${deal.deal_value:,.0f}")

    elif new_stage == "signing":
        _handle_signing(deal)

    elif new_stage == "title_engaged":
        _handle_title_engaged(deal)

    elif new_stage == "closing":
        _slack_alert(CH_BROKER,
                     f":house_with_garden: *Deal Entering Closing*\n"
                     f"Deal `{str(deal.id)[:8]}` moving to close\n"
                     f"Commission: ${deal.commission_due:,.0f}")

    elif new_stage == "closed_won":
        _handle_closed_won(deal)

    elif new_stage == "closed_lost":
        _slack_alert(CH_BROKER,
                     f":x: *Deal Lost*\n"
                     f"Deal `{str(deal.id)[:8]}` closed lost.")


def _handle_contracted(deal):
    """Deal just got a contract → auto-send to Justine for legal review."""
    try:
        from .services import advance_to_legal_review
        advance_to_legal_review(deal)
        logger.info(f"[EVENT] Auto-advanced deal {deal.id} to legal_review")
    except Exception as e:
        logger.error(f"[EVENT] Failed to advance {deal.id} to legal: {e}")
        _slack_alert(CH_HUNTERS,
                     f":warning: Deal `{str(deal.id)[:8]}` contracted but legal review failed: {e}")


def _handle_signing(deal):
    """Documents sent for signing → notify agents, start tracking."""
    _slack_alert(CH_BROKER,
                 f":memo: *Signing Package Sent*\n"
                 f"Deal `{str(deal.id)[:8]}` | Piper sent docs for signature\n"
                 f"Hammer following up if no response in 48h")


def _handle_title_engaged(deal):
    """Title company engaged → notify team, start escrow tracking."""
    client_file = getattr(deal, 'client_file', None)
    title_co = client_file.title_company if client_file else "TBD"
    _slack_alert(CH_HUNTERS,
                 f":classical_building: *Title Company Engaged*\n"
                 f"Deal `{str(deal.id)[:8]}` | Title: {title_co}\n"
                 f"Harrison coordinating escrow and closing")


def _handle_closed_won(deal):
    """Deal closed won → celebrate, update revenue, notify everyone."""
    _slack_alert(CH_WAR_ROOM,
                 f":moneybag: *DEAL CLOSED WON* :moneybag:\n"
                 f"Deal `{str(deal.id)[:8]}`\n"
                 f"Revenue: ${deal.commission_due:,.0f}\n"
                 f"Cash Holloway tracking payment.")

    _slack_alert(CH_REVENUE,
                 f":chart_with_upwards_trend: *Revenue Event*\n"
                 f"Commission earned: ${deal.commission_due:,.0f}\n"
                 f"Stripe invoice: {deal.stripe_invoice_id or 'pending'}")


# ============================================================
# OUTREACH REPLY DETECTED -- immediate deal creation
# ============================================================

@receiver(post_save, sender=OutreachSequence)
@_async
def on_outreach_reply(sender, instance, **kwargs):
    """When an outreach step is marked 'replied', fire the deal creation pipeline."""
    if instance.status != "replied":
        return

    match = instance.match
    if not match:
        return

    # Check if deal already exists for this match
    if hasattr(match, 'deal'):
        return

    logger.info(f"[EVENT] Reply detected on outreach {instance.id} → creating deal")

    _slack_alert(CH_BROKER,
                 f":incoming_envelope: *REPLY DETECTED*\n"
                 f"Match `{str(match.id)[:8]}` | {match.lead.name if match.lead else 'Unknown'}\n"
                 f"Score: {match.match_score}% | Auto-creating deal...")

    try:
        from .services import create_deal_from_match
        deal = create_deal_from_match(match)
        logger.info(f"[EVENT] Deal {deal.id} auto-created from reply")
    except Exception as e:
        logger.error(f"[EVENT] Deal creation from reply failed: {e}")


# ============================================================
# PROPERTY LEAD STATUS CHANGES -- wholesale pipeline events
# ============================================================

@receiver(pre_save, sender=PropertyLead)
def capture_previous_property_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_status = PropertyLead.objects.filter(
                pk=instance.pk).values_list("status", flat=True).first()
        except Exception:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=PropertyLead)
@_async
def on_property_status_change(sender, instance, created, **kwargs):
    """React to wholesale property lead status changes."""
    prop = instance
    old = getattr(prop, '_previous_status', None)
    new = prop.status

    if created:
        return  # New leads are handled by the scout, not signals

    if old == new:
        return

    logger.info(f"[EVENT] Property {prop.address} status: {old} → {new}")

    if new == "negotiating" and old == "contacted":
        # Seller is responding → Hammer takes over
        _slack_alert(CH_HUNTERS,
                     f":handshake: *Seller Engaging!*\n"
                     f"{prop.address}, {prop.city} {prop.state}\n"
                     f"Owner: {prop.owner_name} | Motivation: {prop.motivation_score}/100\n"
                     f"Hammer Knox negotiating. MAO: ${prop.mao:,.0f}")

    elif new == "under_contract":
        _slack_alert(CH_HUNTERS,
                     f":page_facing_up: *Property Under Contract!*\n"
                     f"{prop.address}, {prop.city} {prop.state}\n"
                     f"Assignment fee: ${prop.assignment_fee:,.0f}\n"
                     f"Moving to buyer matching...")

    elif new == "assigned":
        _slack_alert(CH_WAR_ROOM,
                     f":dart: *Property Assigned to Buyer!*\n"
                     f"{prop.address}, {prop.city} {prop.state}\n"
                     f"Assignment fee: ${prop.assignment_fee:,.0f}\n"
                     f"Heading to closing...")

    elif new == "closed":
        _slack_alert(CH_WAR_ROOM,
                     f":house: *WHOLESALE DEAL CLOSED* :moneybag:\n"
                     f"{prop.address}, {prop.city} {prop.state}\n"
                     f"Assignment fee collected: ${prop.assignment_fee:,.0f}")


# ============================================================
# CALL LOG -- auto-schedule follow-ups, advance deals
# ============================================================

@receiver(post_save, sender=CallLog)
@_async
def on_call_logged(sender, instance, created, **kwargs):
    """React to call outcomes -- schedule follow-ups, advance deals."""
    if not created:
        return

    call = instance

    if call.outcome == "deal_advanced" and call.deal:
        # Call resulted in deal advancement
        _slack_alert(CH_BROKER,
                     f":phone: *Call Advanced Deal*\n"
                     f"{call.caller_agent} called {call.contact_name}\n"
                     f"Deal `{str(call.deal_id)[:8]}` moving forward\n"
                     f"Commitments: {', '.join(call.commitments) if call.commitments else 'none logged'}")

    elif call.outcome == "callback" and call.followup_date:
        # Callback scheduled
        _slack_alert(CH_BROKER,
                     f":calendar: *Callback Scheduled*\n"
                     f"{call.contact_name} | {call.followup_date.strftime('%b %d at %I:%M %p PT')}\n"
                     f"Agent: {call.caller_agent} | Action: {call.followup_action}")

    elif call.outcome == "dead" and call.property_lead:
        # Lead declared dead on call
        prop = call.property_lead
        if prop.status not in ("dead", "closed"):
            prop.status = "dead"
            prop.save(update_fields=["status"])
            logger.info(f"[EVENT] Property {prop.address} marked dead after call")

    # Log objections for learning
    if call.objections:
        logger.info(f"[EVENT] Objections from {call.contact_name}: {call.objections}")


# ============================================================
# DOCUMENT SIGNED -- advance to next stage
# ============================================================

@receiver(post_save, sender=ClientDocument)
@_async
def on_document_status_change(sender, instance, **kwargs):
    """When a document is signed, advance the deal."""
    doc = instance

    if doc.status != "signed":
        return

    client_file = doc.client_file
    deal = client_file.deal if client_file else None

    if not deal:
        return

    logger.info(f"[EVENT] Document signed: {doc.title} for deal {deal.id}")

    if doc.doc_type == "assignment_contract" and deal.stage == "signing":
        # Assignment contract signed → engage title company
        _slack_alert(CH_HUNTERS,
                     f":white_check_mark: *Contract Signed!*\n"
                     f"{doc.title}\n"
                     f"Deal `{str(deal.id)[:8]}` → engaging title company")

        try:
            from .services import engage_title_company
            engage_title_company(deal,
                                 title_company=client_file.title_company,
                                 title_contact=client_file.title_contact,
                                 title_email=client_file.title_email)
        except Exception as e:
            logger.error(f"[EVENT] Title engagement failed: {e}")

    elif doc.doc_type == "signed_contract" and deal.stage == "signing":
        # Finder fee agreement signed → advance to closing (B2B, no title company)
        deal.stage = "closing"
        deal.save(update_fields=["stage"])

    elif doc.doc_type == "closing_statement" and deal.stage in ("title_engaged", "closing"):
        # Closing statement received → close the deal
        try:
            from .services import close_deal
            close_deal(deal, won=True)
        except Exception as e:
            logger.error(f"[EVENT] Auto-close failed: {e}")


# ============================================================
# COMMISSION PAID -- Stripe webhook feeds this
# ============================================================

@receiver(post_save, sender=CommissionRecord)
@_async
def on_commission_update(sender, instance, created, **kwargs):
    """React to commission state changes."""
    if not created:
        return

    rec = instance

    if rec.record_type == "paid":
        _slack_alert(CH_REVENUE,
                     f":white_check_mark: *Commission PAID*\n"
                     f"Deal `{str(rec.deal_id)[:8]}` | ${rec.amount:,.2f}\n"
                     f"Stripe: {rec.stripe_payout_id or rec.stripe_invoice_id or 'manual'}")

        _slack_alert(CH_WAR_ROOM,
                     f":dollar: *MONEY IN THE BANK*\n"
                     f"${rec.amount:,.2f} commission collected.\n"
                     f"Cash Holloway confirmed payment.")


# ============================================================
# INVESTOR BUYER MATCH -- auto-pitch when a hot buyer appears
# ============================================================

@receiver(post_save, sender=InvestorBuyer)
@_async
def on_new_buyer(sender, instance, created, **kwargs):
    """When a new buyer is added, check for matching properties to pitch."""
    if not created:
        return

    buyer = instance
    if not buyer.is_active or not buyer.markets:
        return

    # Find properties under_contract or negotiating in buyer's markets
    matching = PropertyLead.objects.filter(
        status__in=["under_contract", "negotiating"],
        state__in=[m.upper()[:2] for m in buyer.markets if len(m) >= 2],
    ).order_by("-motivation_score")[:3]

    if matching:
        prop_list = "\n".join(
            f"  • {p.address}, {p.city} {p.state} (fee: ${p.assignment_fee:,.0f})"
            for p in matching
        )
        _slack_alert(CH_HUNTERS,
                     f":mag: *New Buyer Matched to Properties*\n"
                     f"Buyer: {buyer.name} ({buyer.company})\n"
                     f"Markets: {', '.join(buyer.markets[:5])}\n"
                     f"Matching properties:\n{prop_list}\n"
                     f"Ace preparing investment pitches...")
