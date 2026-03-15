"""
Broker OS - Services

Core matching and commission logic + Stripe payment integration
+ contract/memo generation.
"""
import json
import logging
import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    stripe = None
    STRIPE_AVAILABLE = False
from django.conf import settings
from django.utils import timezone

from .models import (
    BrokerMatch,
    CommissionRecord,
    Deal,
    LeadProfile,
    OfferListing,
    OutreachSequence,
)

logger = logging.getLogger(__name__)

# Configure Stripe from env
if STRIPE_AVAILABLE:
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


def _emit_business_event(summary: str, **kwargs):
    try:
        from business_os.services import record_event, upsert_revenue_stream

        event = record_event(source="broker_ops", summary=summary, **kwargs)
        upsert_revenue_stream("broker_os", status="active", last_event_at=event.created_at)
        return event
    except Exception as exc:
        logger.debug("Business OS event skipped: %s", exc)
        return None


def _emit_business_alert(summary: str, **kwargs):
    try:
        from business_os.services import record_alert

        return record_alert(summary=summary, source="broker_ops", **kwargs)
    except Exception as exc:
        logger.debug("Business OS alert skipped: %s", exc)
        return None


# ---------------------------------------------------------------------------
# MATCHING ENGINE
# ---------------------------------------------------------------------------

def score_match(offer: OfferListing, lead: LeadProfile) -> tuple[float, str]:
    """
    Rule-based scoring (0-100). Returns (score, reasoning).
    Upgrade to Claude API call when needed.
    """
    score = 0.0
    reasons = []

    # Category overlap (40 pts)
    if offer.category in (lead.categories_needed or []):
        score += 40
        reasons.append(f"Category match: {offer.category}")
    elif any(k.lower() in offer.description.lower() for k in (lead.categories_needed or [])):
        score += 20
        reasons.append("Partial category overlap in description")

    # Keyword overlap (30 pts, capped)
    offer_kw = set(kw.lower() for kw in (offer.keywords or []))
    need_kw  = set(lead.need_description.lower().split())
    overlap  = offer_kw & need_kw
    if overlap:
        kw_score = min(30, len(overlap) * 5)
        score += kw_score
        reasons.append(f"Keyword hits: {', '.join(list(overlap)[:5])}")

    # Budget fit (20 pts)
    if lead.budget_max > 0 and offer.price_min <= lead.budget_max:
        score += 20
        reasons.append(f"Budget fits: offer ${offer.price_min}-${offer.price_max}, lead budget up to ${lead.budget_max}")
    elif lead.budget_max == 0:
        score += 10
        reasons.append("Budget unspecified (neutral)")

    # Intent bonus (10 pts)
    intent_bonus = {"hot": 10, "warm": 5, "cold": 0}
    score += intent_bonus.get(lead.intent, 0)
    if lead.intent != "cold":
        reasons.append(f"Intent: {lead.intent}")

    # Company size bonus (mid-size companies = better B2B fit)
    if lead.company_size == "51_200":
        score += 5
        reasons.append("Mid-size company bonus (+5)")
    elif lead.company_size == "200_plus":
        score += 3
        reasons.append("Enterprise company bonus (+3)")

    # Negative signals: personal email penalty (B2B context)
    personal_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}
    email_domain = (lead.email or "").split("@")[-1].lower()
    if email_domain in personal_domains:
        score -= 10
        reasons.append(f"Personal email penalty (-10): {email_domain}")

    # Negative signal: empty company field
    if not (lead.company or "").strip():
        score -= 5
        reasons.append("No company listed (-5)")

    return round(max(min(score, 100.0), 0.0), 1), " | ".join(reasons) if reasons else "No strong signals"


def run_matching(min_score: float = 60.0, dry_run: bool = False) -> list[dict]:
    """
    Pair all active offers against leads with real (non-placeholder) emails.
    Creates BrokerMatch records for pairs >= min_score.
    Minimum score raised from 40 -> 60 to cut noise.
    Returns list of match summaries.
    """
    offers = OfferListing.objects.filter(status="active")
    # Gate 1: only real emails -- placeholder leads cannot be contacted
    leads = LeadProfile.objects.filter(unsubscribed=False).exclude(
        email__contains="@placeholder.io"
    ).exclude(email="")
    results = []

    for offer in offers:
        for lead in leads:
            # Skip already-matched or expired pairs
            if BrokerMatch.objects.filter(offer=offer, lead=lead).exclude(
                status="expired"
            ).exists():
                continue

            score, reasoning = score_match(offer, lead)
            if score < min_score:
                continue

            result = {
                "offer": str(offer),
                "lead":  str(lead),
                "score": score,
                "reasoning": reasoning,
            }

            if not dry_run:
                auto_status = "approved" if score >= 70 else "pending"
                match, created = BrokerMatch.objects.get_or_create(
                    offer=offer,
                    lead=lead,
                    defaults={
                        "match_score": score,
                        "match_reasoning": reasoning,
                        "matched_by": "auto_approved" if auto_status == "approved" else "auto",
                        "status": auto_status,
                    }
                )
                if not created:
                    match.match_score = score
                    match.match_reasoning = reasoning
                    match.save(update_fields=["match_score", "match_reasoning", "updated_at"])
                result["match_id"] = str(match.id)
                result["created"] = created

            results.append(result)

    logger.info(f"Matching run complete: {len(results)} real-email pairs scored >= {min_score}")
    _emit_business_event(
        event_type="broker.matching.completed",
        entity_type="workflow",
        entity_id="matching",
        status="success" if results else "info",
        priority="high" if results else "medium",
        owner_agent="30_match_maker",
        summary=f"Broker matching run produced {len(results)} matches at min score {min_score}.",
        payload={
            "min_score": min_score,
            "dry_run": dry_run,
            "result_count": len(results),
        },
    )
    return results


def expire_stale_matches(hours: int = 48, dry_run: bool = False) -> int:
    """
    Expire pending matches older than `hours` that still have no outreach.
    Prevents pipeline bloat from stale ghost matches.
    Returns number of matches expired.
    """
    cutoff = timezone.now() - timedelta(hours=hours)
    stale = BrokerMatch.objects.filter(
        status="pending",
        created_at__lt=cutoff,
        outreach_sent_at__isnull=True,
    )
    count = stale.count()
    if not dry_run:
        stale.update(status="expired")
    logger.info(f"Expired {count} stale matches (>{hours}h, no outreach)")
    return count


def auto_approve_high_score_matches(min_score: float = 65.0, limit: int = 20,
                                    dry_run: bool = False) -> int:
    """
    Auto-approve pending matches with score >= min_score that have real emails.
    Removes human approval bottleneck for clear-cut high-confidence matches.
    Returns number of matches approved.
    """
    candidates = BrokerMatch.objects.filter(
        status="pending",
        match_score__gte=min_score,
    ).exclude(
        lead__email__contains="@placeholder.io"
    ).exclude(
        lead__email=""
    ).order_by("-match_score")[:limit]

    count = 0
    for match in candidates:
        if not dry_run:
            match.status = "approved"
            match.matched_by = "auto_approved"
            match.save(update_fields=["status", "matched_by", "updated_at"])
        count += 1

    logger.info(f"Auto-approved {count} high-score matches (>= {min_score})")
    return count


# ---------------------------------------------------------------------------
# DEAL MANAGEMENT
# ---------------------------------------------------------------------------

def create_deal_from_match(match: BrokerMatch, deal_value: Decimal, notes: str = "") -> Deal:
    """Convert an approved match into an active Deal."""
    deal = Deal.objects.create(
        match=match,
        offer=match.offer,
        lead=match.lead,
        stage="intro",
        deal_value=deal_value,
        commission_pct=match.offer.commission_pct,
        notes=notes,
    )
    match.status = "converted"
    match.save(update_fields=["status", "updated_at"])

    # Record initial commission as pending
    record_commission(deal, "pending", deal.commission_due, "Deal opened - commission pending")

    logger.info(f"Deal created: {deal.id} value=${deal_value}")
    _emit_business_event(
        event_type="broker.deal.created",
        entity_type="deal",
        entity_id=str(deal.id),
        status="success",
        priority="high",
        requires_approval=True,
        owner_agent="32_deal_closer",
        revenue_impact_usd=deal.commission_due,
        summary=f"Broker deal created for {deal.offer.title if deal.offer else 'unlinked offer'} with ${deal.commission_due} commission due.",
        payload={
            "deal_value": str(deal.deal_value),
            "commission_due": str(deal.commission_due),
            "lead": deal.lead.name if deal.lead else "",
        },
    )
    return deal


def close_deal(deal: Deal, won: bool = True) -> Deal:
    """Mark a deal closed and finalize commission record."""
    deal.stage = "closed_won" if won else "closed_lost"
    deal.closed_at = timezone.now()
    deal.save(update_fields=["stage", "closed_at"])

    if won:
        # Mark pending commissions earned
        deal.commissions.filter(record_type="pending").update(record_type="earned")
        logger.info(f"Deal closed won: {deal.id} commission=${deal.commission_due}")
        _emit_business_event(
            event_type="broker.deal.closed_won",
            entity_type="deal",
            entity_id=str(deal.id),
            status="success",
            priority="high",
            owner_agent="32_deal_closer",
            revenue_impact_usd=deal.commission_due,
            summary=f"Broker deal closed won with ${deal.commission_due} commission for {deal.offer.title if deal.offer else 'unlinked offer'}.",
            payload={
                "stage": deal.stage,
                "commission_due": str(deal.commission_due),
            },
        )
    else:
        # Reverse pending
        deal.commissions.filter(record_type="pending").update(record_type="reversed")
        _emit_business_event(
            event_type="broker.deal.closed_lost",
            entity_type="deal",
            entity_id=str(deal.id),
            status="warning",
            priority="medium",
            owner_agent="32_deal_closer",
            summary=f"Broker deal closed lost for {deal.offer.title if deal.offer else 'unlinked offer'}.",
            payload={"stage": deal.stage},
        )

    return deal


# ---------------------------------------------------------------------------
# COMMISSION LEDGER
# ---------------------------------------------------------------------------

def record_commission(deal: Deal, record_type: str, amount: Decimal, description: str = "",
                       stripe_payout_id: str = "", reference: str = "") -> CommissionRecord:
    return CommissionRecord.objects.create(
        deal=deal,
        record_type=record_type,
        amount=amount,
        description=description,
        stripe_payout_id=stripe_payout_id,
        reference=reference,
    )


def get_commission_summary() -> dict:
    """Aggregate commission stats for dashboard."""
    from django.db.models import Sum

    earned  = CommissionRecord.objects.filter(record_type="earned").aggregate(t=Sum("amount"))["t"] or 0
    paid    = CommissionRecord.objects.filter(record_type="paid").aggregate(t=Sum("amount"))["t"] or 0
    pending = CommissionRecord.objects.filter(record_type="pending").aggregate(t=Sum("amount"))["t"] or 0

    return {
        "earned_total":  float(earned),
        "paid_total":    float(paid),
        "pending_total": float(pending),
        "unpaid_balance": float(earned) - float(paid),
        "active_deals":  Deal.objects.filter(stage__in=["intro","negotiating","contracted","active"]).count(),
        "closed_won":    Deal.objects.filter(stage="closed_won").count(),
    }


# ---------------------------------------------------------------------------
# LEAD INGEST (from pipeline script)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PAIN POINT MAPPING
# ---------------------------------------------------------------------------

def get_pain_points(category):
    """Return 2-3 common pain points for a tool category."""
    mapping = {
        "crm": [
            "tracking leads across spreadsheets",
            "losing deals in the pipeline",
            "no visibility into team activity",
        ],
        "analytics": [
            "guessing instead of knowing what works",
            "manual report building every week",
            "data scattered across tools",
        ],
        "automation": [
            "repetitive tasks eating your day",
            "things falling through the cracks",
            "no way to scale without hiring",
        ],
        "communication": [
            "messages lost across channels",
            "slow response times hurting deals",
            "no centralized team inbox",
        ],
        "project_management": [
            "missed deadlines and scope creep",
            "no visibility into team workload",
            "status updates taking longer than the work",
        ],
        "security": [
            "compliance audit anxiety",
            "no idea who has access to what",
            "one breach away from disaster",
        ],
        "ai_saas": [
            "AI hype but no practical implementation",
            "spending hours on tasks AI could handle",
            "competitors moving faster with AI",
        ],
        "developer_tools": [
            "slow deployment cycles",
            "debugging taking longer than building",
            "developer productivity plateauing",
        ],
    }
    default = [
        "spending too much time on operations",
        "manual processes slowing growth",
        "ready to scale but tools can not keep up",
    ]
    return mapping.get(category, default)


# ---------------------------------------------------------------------------
# OUTREACH SEQUENCE MANAGEMENT
# ---------------------------------------------------------------------------

SEQUENCE_TEMPLATES = {
    "buyer_intro": {
        "subject": "Quick thought on {need_description_short}",
        "body": """Hi {lead_name},

If you are dealing with {pain_point}, {offer_title} might be exactly what you need.

{offer_description}

The reason I am reaching out -- {offer_title} was built to solve this specific problem, and based on what you are looking for, it looks like a strong fit.

Want me to make an intro to {seller_name}? No cost on your end unless you decide to move forward.

Best,
Sage
Everlight Ventures
everlightventures.io

---
Reply STOP to unsubscribe."""
    },
    "followup_1": {
        "subject": "Re: {offer_title} -- quick question",
        "body": """Hi {lead_name},

Following up on {offer_title}. Companies like yours typically save 5-10 hours a week after switching to a purpose-built tool for this.

Would it be worth a 10-minute look? A simple yes or no works.

Sage
Everlight Ventures"""
    },
    "breakup": {
        "subject": "Closing out your request",
        "body": """Hi {lead_name},

I am closing out your request for {need_description_short}. If timing changes or you want a fresh recommendation later, just reply here.

Sage
Everlight Ventures"""
    },
}

SEQUENCE_SCHEDULE = [
    ("buyer_intro", 0),
    ("followup_1", 3),
    ("breakup", 7),
]


def create_outreach_sequence(match: BrokerMatch) -> list[OutreachSequence]:
    """Create a multi-step outreach sequence for a match."""
    if not match.lead.email or "@placeholder" in match.lead.email:
        return []

    steps = []
    base_time = timezone.now()

    for step_name, delay_days in SEQUENCE_SCHEDULE:
        template = SEQUENCE_TEMPLATES.get(step_name, {})
        category = match.offer.category or "other"
        pain_points = get_pain_points(category)
        need_desc = match.lead.need_description or ""
        context = {
            "lead_name": match.lead.name,
            "offer_title": match.offer.title[:50],
            "offer_description": match.offer.description[:300],
            "match_reasoning": match.match_reasoning,
            "need_description": need_desc,
            "need_description_short": need_desc[:80] if need_desc else "your tool search",
            "seller_name": match.offer.seller_name or "the team",
            "pain_point": pain_points[0] if pain_points else "operational bottlenecks",
        }

        obj, created = OutreachSequence.objects.get_or_create(
            match=match,
            step=step_name,
            defaults={
                "to_email": match.lead.email,
                "subject": template.get("subject", "").format(**context),
                "body": template.get("body", "").format(**context),
                "scheduled_at": base_time + timedelta(days=delay_days),
            }
        )
        if created:
            steps.append(obj)

    if steps:
        _emit_business_event(
            event_type="broker.outreach.sequence_created",
            entity_type="match",
            entity_id=str(match.id),
            status="success",
            priority="medium",
            owner_agent="31_outreach_agent",
            summary=f"Created {len(steps)} outreach steps for broker match {str(match.id)[:8]}.",
            payload={"step_count": len(steps), "lead_email": match.lead.email},
        )
    return steps


def get_due_outreach(limit: int = 20) -> list:
    """Get outreach steps that are due to send now."""
    return list(
        OutreachSequence.objects.filter(
            status="pending",
            scheduled_at__lte=timezone.now(),
            match__lead__unsubscribed=False,
        ).select_related("match", "match__lead", "match__offer")
        .order_by("scheduled_at")[:limit]
    )


def mark_outreach_sent(step: OutreachSequence):
    """Mark an outreach step as sent."""
    step.status = "sent"
    step.sent_at = timezone.now()
    step.save(update_fields=["status", "sent_at"])

    # Update lead contact tracking
    step.match.lead.last_contacted = timezone.now()
    step.match.lead.contact_count += 1
    step.match.lead.save(update_fields=["last_contacted", "contact_count", "updated_at"])

    # Update match outreach tracking
    if step.step == "buyer_intro":
        step.match.outreach_sent_at = timezone.now()
        step.match.outreach_channel = "email"
        step.match.outreach_template = step.step
        step.match.status = "approved"
        step.match.save(update_fields=["outreach_sent_at", "outreach_channel", "outreach_template", "status", "updated_at"])
        _emit_business_event(
            event_type="broker.outreach.sent",
            entity_type="match",
            entity_id=str(step.match.id),
            status="success",
            priority="medium",
            owner_agent="31_outreach_agent",
            summary=f"Primary outreach sent for broker match {str(step.match.id)[:8]} to {step.to_email}.",
            payload={"step": step.step, "to_email": step.to_email},
        )


# ---------------------------------------------------------------------------
# LEAD INGEST (from pipeline script)
# ---------------------------------------------------------------------------

def ingest_lead(payload: dict) -> LeadProfile:
    """
    Create or update a LeadProfile from a normalized payload dict.
    Expected keys: name, email, company, role, need_description,
                   categories_needed, budget_min, budget_max,
                   intent, lead_source, source_url, raw_data
    """
    email = payload.get("email", "").strip().lower()
    if email:
        lead, _ = LeadProfile.objects.update_or_create(
            email=email,
            defaults={k: v for k, v in payload.items() if k != "email"}
        )
    else:
        lead = LeadProfile.objects.create(**payload)

    logger.info(f"Lead ingested: {lead}")
    _emit_business_event(
        event_type="broker.lead.ingested",
        entity_type="lead",
        entity_id=str(lead.id),
        status="success",
        priority="medium",
        owner_agent="29_lead_qualifier",
        summary=f"Broker lead ingested: {lead.name}",
        payload={
            "lead_source": lead.lead_source,
            "intent": lead.intent,
            "company": lead.company,
        },
    )
    return lead


def ingest_offer(payload: dict) -> OfferListing:
    """
    Create or update an OfferListing from a normalized payload dict.
    """
    seller_email = payload.get("seller_email", "").strip().lower()
    title = payload.get("title", "").strip()

    if seller_email and title:
        offer, _ = OfferListing.objects.update_or_create(
            seller_email=seller_email,
            title=title,
            defaults={k: v for k, v in payload.items() if k not in ("seller_email", "title")}
        )
    else:
        offer = OfferListing.objects.create(**payload)

    logger.info(f"Offer ingested: {offer}")
    _emit_business_event(
        event_type="broker.offer.ingested",
        entity_type="offer",
        entity_id=str(offer.id),
        status="success",
        priority="medium",
        owner_agent="28_deal_scout",
        summary=f"Broker offer ingested: {offer.title}",
        payload={
            "source": offer.source,
            "category": offer.category,
            "seller_name": offer.seller_name,
        },
    )
    return offer


# ---------------------------------------------------------------------------
# STRIPE PAYMENT INTEGRATION
# ---------------------------------------------------------------------------

def _notify_slack(message):
    """Send a Slack notification for payment events."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        import requests
        requests.post(webhook, json={"text": message, "channel": "#05-revenue"}, timeout=5)
    except Exception:
        pass


def create_stripe_invoice(deal: Deal) -> str:
    """
    Create a Stripe invoice for the finder fee on a closed deal.
    Uses the lead's email as the customer. Sets deal.stripe_invoice_id.
    Returns the Stripe invoice ID.
    """
    if not stripe.api_key:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")

    if deal.stripe_invoice_id:
        logger.warning(f"Deal {deal.id} already has invoice {deal.stripe_invoice_id}")
        return deal.stripe_invoice_id

    if not deal.commission_due or deal.commission_due <= 0:
        raise ValueError(f"Deal {deal.id} has no commission due (${deal.commission_due})")

    # Find or create the Stripe customer from the lead email
    lead_email = deal.lead.email if deal.lead else ""
    lead_name = deal.lead.name if deal.lead else "Unknown"
    if not lead_email:
        raise ValueError(f"Deal {deal.id} has no lead email -- cannot create invoice")

    # Search for existing Stripe customer by email
    existing = stripe.Customer.list(email=lead_email, limit=1)
    if existing.data:
        customer = existing.data[0]
    else:
        customer = stripe.Customer.create(
            email=lead_email,
            name=lead_name,
            metadata={
                "source": "broker_ops",
                "deal_id": str(deal.id),
            },
        )
    logger.info(f"Stripe customer: {customer.id} ({lead_email})")

    # Create the invoice
    amount_cents = int(float(deal.commission_due) * 100)
    offer_title = deal.offer.title if deal.offer else "Brokered Deal"

    inv = stripe.Invoice.create(
        customer=customer.id,
        collection_method="send_invoice",
        days_until_due=14,
        metadata={
            "deal_id": str(deal.id),
            "source": "broker_ops",
        },
    )

    # Add the line item for the finder fee
    stripe.InvoiceItem.create(
        customer=customer.id,
        invoice=inv.id,
        amount=amount_cents,
        currency="usd",
        description=f"Finder fee -- {offer_title} (Deal {str(deal.id)[:8]})",
    )

    # Finalize and send the invoice
    inv = stripe.Invoice.finalize_invoice(inv.id)

    # Save the invoice ID on the deal
    deal.stripe_invoice_id = inv.id
    deal.save(update_fields=["stripe_invoice_id"])

    # Create a commission record linking to this invoice
    CommissionRecord.objects.filter(
        deal=deal, record_type__in=["earned", "pending"]
    ).update(stripe_invoice_id=inv.id)

    logger.info(f"Stripe invoice created: {inv.id} for ${deal.commission_due} on deal {deal.id}")
    _notify_slack(f"INVOICE SENT: ${deal.commission_due} finder fee -- {offer_title} -- {lead_email}")
    _emit_business_event(
        event_type="broker.invoice.created",
        entity_type="deal",
        entity_id=str(deal.id),
        status="success",
        priority="high",
        owner_agent="32_deal_closer",
        revenue_impact_usd=deal.commission_due,
        summary=f"Stripe invoice created for broker deal {str(deal.id)[:8]} worth ${deal.commission_due}.",
        payload={"invoice_id": inv.id, "lead_email": lead_email},
    )

    return inv.id


def check_stripe_payment_status(deal: Deal) -> dict:
    """
    Check whether the Stripe invoice for a deal has been paid.
    Updates the CommissionRecord status accordingly.
    Returns a dict with invoice status info.
    """
    if not stripe.api_key:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")

    if not deal.stripe_invoice_id:
        return {"status": "no_invoice", "message": "No Stripe invoice on this deal"}

    try:
        inv = stripe.Invoice.retrieve(deal.stripe_invoice_id)
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe invoice lookup failed for {deal.stripe_invoice_id}: {e}")
        return {"status": "error", "message": str(e)}

    result = {
        "invoice_id": inv.id,
        "status": inv.status,
        "amount_due": inv.amount_due / 100,
        "amount_paid": inv.amount_paid / 100,
        "hosted_invoice_url": inv.hosted_invoice_url or "",
    }

    # If paid, update commission records
    if inv.status == "paid":
        updated = deal.commissions.filter(
            record_type__in=["earned", "pending"]
        ).update(record_type="paid")
        if updated:
            logger.info(f"Deal {deal.id} invoice paid -- {updated} commission record(s) marked paid")
            _notify_slack(
                f"PAYMENT RECEIVED: ${inv.amount_paid / 100:.2f} finder fee for deal {str(deal.id)[:8]}"
            )
            _emit_business_event(
                event_type="broker.invoice.paid",
                entity_type="deal",
                entity_id=str(deal.id),
                status="success",
                priority="high",
                owner_agent="32_deal_closer",
                revenue_impact_usd=Decimal(str(inv.amount_paid / 100)),
                summary=f"Stripe invoice paid for broker deal {str(deal.id)[:8]} (${inv.amount_paid / 100:.2f}).",
                payload={"invoice_id": inv.id, "amount_paid": inv.amount_paid / 100},
            )

    return result


def create_stripe_checkout_link(deal: Deal, success_url: str = "", cancel_url: str = "") -> str:
    """
    Create a Stripe Checkout session for the buyer/seller to pay the finder fee.
    Returns the checkout URL.
    """
    if not stripe.api_key:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")

    if not deal.commission_due or deal.commission_due <= 0:
        raise ValueError(f"Deal {deal.id} has no commission due")

    amount_cents = int(float(deal.commission_due) * 100)
    offer_title = deal.offer.title if deal.offer else "Brokered Deal"
    lead_email = deal.lead.email if deal.lead else None

    base_url = os.environ.get("SITE_BASE_URL", "https://everlightventures.io")
    if not success_url:
        success_url = f"{base_url}/broker/payment/success?deal_id={deal.id}"
    if not cancel_url:
        cancel_url = f"{base_url}/broker/payment/cancel?deal_id={deal.id}"

    session_kwargs = {
        "payment_method_types": ["card"],
        "mode": "payment",
        "line_items": [{
            "price_data": {
                "currency": "usd",
                "unit_amount": amount_cents,
                "product_data": {
                    "name": f"Finder Fee -- {offer_title}",
                    "description": f"Everlight Ventures broker commission for deal {str(deal.id)[:8]}",
                },
            },
            "quantity": 1,
        }],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {
            "deal_id": str(deal.id),
            "source": "broker_ops",
        },
    }

    if lead_email:
        session_kwargs["customer_email"] = lead_email

    session = stripe.checkout.Session.create(**session_kwargs)

    logger.info(f"Checkout session created: {session.id} for deal {deal.id} (${deal.commission_due})")
    _emit_business_event(
        event_type="broker.checkout.created",
        entity_type="deal",
        entity_id=str(deal.id),
        status="success",
        priority="high",
        owner_agent="32_deal_closer",
        revenue_impact_usd=deal.commission_due,
        summary=f"Broker checkout link created for deal {str(deal.id)[:8]}.",
        payload={"checkout_id": session.id, "amount_due": str(deal.commission_due)},
    )
    return session.url


def handle_broker_invoice_paid(invoice_data: dict) -> bool:
    """
    Handle a Stripe invoice.paid event for broker_ops invoices.
    Returns True if this was a broker_ops invoice we handled.
    """
    metadata = invoice_data.get("metadata", {})
    deal_id = metadata.get("deal_id")
    source = metadata.get("source")

    if source != "broker_ops" or not deal_id:
        return False

    try:
        deal = Deal.objects.get(id=deal_id)
    except Deal.DoesNotExist:
        logger.error(f"Broker invoice.paid -- deal {deal_id} not found")
        return False

    amount_paid = invoice_data.get("amount_paid", 0) / 100
    invoice_id = invoice_data.get("id", "")

    # Mark commissions as paid
    updated = deal.commissions.filter(
        record_type__in=["earned", "pending"]
    ).update(record_type="paid", stripe_invoice_id=invoice_id)

    logger.info(f"Broker invoice paid: deal {deal_id}, ${amount_paid}, {updated} records updated")
    _notify_slack(f"BROKER FEE PAID: ${amount_paid:.2f} for deal {str(deal_id)[:8]}")
    _emit_business_event(
        event_type="broker.invoice.webhook_paid",
        entity_type="deal",
        entity_id=str(deal.id),
        status="success",
        priority="high",
        owner_agent="32_deal_closer",
        revenue_impact_usd=Decimal(str(amount_paid)),
        summary=f"Broker invoice webhook confirmed payment of ${amount_paid:.2f} for deal {str(deal_id)[:8]}.",
        payload={"invoice_id": invoice_id, "updated_records": updated},
    )
    return True


def handle_broker_checkout_completed(session_data: dict) -> bool:
    """
    Handle a Stripe checkout.session.completed event for broker_ops sessions.
    Returns True if this was a broker_ops checkout we handled.
    """
    metadata = session_data.get("metadata", {})
    deal_id = metadata.get("deal_id")
    source = metadata.get("source")

    if source != "broker_ops" or not deal_id:
        return False

    try:
        deal = Deal.objects.get(id=deal_id)
    except Deal.DoesNotExist:
        logger.error(f"Broker checkout completed -- deal {deal_id} not found")
        return False

    payment_intent = session_data.get("payment_intent", "")
    amount_total = session_data.get("amount_total", 0) / 100

    # Update deal stripe_invoice_id with the payment intent for tracking
    if not deal.stripe_invoice_id:
        deal.stripe_invoice_id = f"checkout_{payment_intent}"
        deal.save(update_fields=["stripe_invoice_id"])

    # Mark commissions as paid
    updated = deal.commissions.filter(
        record_type__in=["earned", "pending"]
    ).update(record_type="paid")

    # Record the payment as a new commission entry
    record_commission(
        deal=deal,
        record_type="paid",
        amount=Decimal(str(amount_total)),
        description=f"Checkout payment received -- {payment_intent}",
        stripe_payout_id=payment_intent,
    )

    logger.info(f"Broker checkout completed: deal {deal_id}, ${amount_total}")
    _notify_slack(f"BROKER CHECKOUT PAID: ${amount_total:.2f} for deal {str(deal_id)[:8]}")
    _emit_business_event(
        event_type="broker.checkout.completed",
        entity_type="deal",
        entity_id=str(deal.id),
        status="success",
        priority="high",
        owner_agent="32_deal_closer",
        revenue_impact_usd=Decimal(str(amount_total)),
        summary=f"Broker checkout completed for deal {str(deal_id)[:8]} (${amount_total:.2f}).",
        payload={"payment_intent": payment_intent, "updated_records": updated},
    )
    return True


# ---------------------------------------------------------------------------
# CONTRACT & MEMO GENERATION
# ---------------------------------------------------------------------------

# Base path for contract templates and output
_CONTRACTS_BASE = Path("/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/contracts")


def _read_template(template_name: str) -> str:
    """Read a contract template file and return its contents."""
    template_path = _CONTRACTS_BASE / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Contract template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def generate_contract(deal: Deal, payment_method: str = "stripe") -> str:
    """
    Generate a personalized Finder Fee Agreement from the template.

    Reads the FINDER_FEE_AGREEMENT_TEMPLATE.md, fills in all {{PLACEHOLDER}}
    values from the Deal and its related OfferListing and LeadProfile, and
    saves the output to the generated/ directory.

    If payment_method == "crypto", also appends the CRYPTO_PAYMENT_ADDENDUM.

    Returns the absolute file path of the generated contract.
    """
    template = _read_template("FINDER_FEE_AGREEMENT_TEMPLATE.md")

    today = date.today().strftime("%B %d, %Y")
    short_id = str(deal.id)[:8].upper()

    # Pull related objects (guard against None)
    offer = deal.offer
    lead = deal.lead

    seller_name = offer.seller_name if offer else "TBD"
    seller_email = offer.seller_email if offer else "TBD"
    offer_title = offer.title if offer else "TBD"
    offer_desc = (offer.description[:200] if offer else "TBD")
    commission_pct = float(offer.commission_pct) if offer else 20

    buyer_name = ""
    buyer_email = ""
    if lead:
        buyer_name = lead.company.strip() or lead.name
        buyer_email = lead.email
    buyer_name = buyer_name or "TBD"
    buyer_email = buyer_email or "TBD"

    deal_description = f"{offer_title} -- {offer_desc}"
    payment_label = "Stripe" if payment_method != "crypto" else "Cryptocurrency (see addendum)"

    replacements = {
        "{{EFFECTIVE_DATE}}": today,
        "{{SELLER_LEGAL_NAME}}": seller_name,
        "{{SELLER_EMAIL}}": seller_email,
        "{{BUYER_LEGAL_NAME}}": buyer_name,
        "{{BUYER_EMAIL}}": buyer_email,
        "{{DEAL_DESCRIPTION}}": deal_description,
        "{{COMMISSION_PERCENTAGE}}": str(commission_pct),
        "{{DEAL_VALUE}}": f"{float(deal.deal_value):,.2f}",
        "{{COMMISSION_AMOUNT}}": f"{float(deal.commission_due):,.2f}",
        "{{PAYMENT_METHOD}}": payment_label,
        "{{TAIL_PERIOD_MONTHS}}": "12",
        "{{AGREEMENT_ID}}": f"EV-{short_id}",
    }

    contract = template
    for placeholder, value in replacements.items():
        contract = contract.replace(placeholder, value)

    # Append crypto addendum if needed
    if payment_method == "crypto":
        addendum = _read_template("CRYPTO_PAYMENT_ADDENDUM.md")
        for placeholder, value in replacements.items():
            addendum = addendum.replace(placeholder, value)
        contract += "\n" + addendum

    # Save to generated/ directory
    out_dir = _CONTRACTS_BASE / "generated"
    os.makedirs(out_dir, exist_ok=True)

    date_slug = date.today().strftime("%Y-%m-%d")
    filename = f"AGREEMENT_{short_id}_{date_slug}.md"
    out_path = out_dir / filename
    out_path.write_text(contract, encoding="utf-8")

    logger.info(f"Contract generated: {out_path} for deal {deal.id}")
    return str(out_path)


def generate_deal_memo(deal: Deal) -> str:
    """
    Generate a Deal Memo from the DEAL_MEMO_TEMPLATE.

    Fills in deal, offer, lead, and match details and saves the output
    to the memos/ directory.

    Returns the absolute file path of the generated memo.
    """
    template = _read_template("DEAL_MEMO_TEMPLATE.md")

    today = date.today().strftime("%B %d, %Y")
    short_id = str(deal.id)[:8].upper()

    offer = deal.offer
    lead = deal.lead
    match = deal.match if hasattr(deal, "match") else None

    # Build replacement map
    replacements = {
        "{{DEAL_ID}}": short_id,
        "{{MEMO_DATE}}": today,
        "{{DEAL_STAGE}}": deal.get_stage_display() if hasattr(deal, "get_stage_display") else deal.stage,
        "{{DEAL_CREATED}}": deal.created_at.strftime("%Y-%m-%d %H:%M") if deal.created_at else "N/A",
        "{{DEAL_VALUE}}": f"{float(deal.deal_value):,.2f}",
        "{{COMMISSION_PERCENTAGE}}": str(float(deal.commission_pct)),
        "{{COMMISSION_AMOUNT}}": f"{float(deal.commission_due):,.2f}",
        "{{SELLER_NAME}}": offer.seller_name if offer else "N/A",
        "{{SELLER_EMAIL}}": offer.seller_email if offer else "N/A",
        "{{OFFER_TITLE}}": offer.title if offer else "N/A",
        "{{OFFER_CATEGORY}}": offer.get_category_display() if offer else "N/A",
        "{{PRICING_MODEL}}": offer.get_pricing_model_display() if offer else "N/A",
        "{{PRICE_MIN}}": f"{float(offer.price_min):,.2f}" if offer else "0.00",
        "{{PRICE_MAX}}": f"{float(offer.price_max):,.2f}" if offer else "0.00",
        "{{OFFER_DESCRIPTION}}": offer.description if offer else "N/A",
        "{{BUYER_NAME}}": lead.name if lead else "N/A",
        "{{BUYER_COMPANY}}": lead.company if lead else "N/A",
        "{{BUYER_EMAIL}}": lead.email if lead else "N/A",
        "{{BUYER_ROLE}}": lead.role if lead else "N/A",
        "{{BUYER_INTENT}}": lead.get_intent_display() if lead else "N/A",
        "{{LEAD_SOURCE}}": lead.get_lead_source_display() if lead else "N/A",
        "{{BUYER_NEED}}": lead.need_description if lead else "N/A",
        "{{MATCH_SCORE}}": f"{match.match_score:.0f}%" if match else "N/A",
        "{{MATCHED_BY}}": match.matched_by if match else "N/A",
        "{{MATCH_REASONING}}": match.match_reasoning if match else "N/A",
        "{{DEAL_NOTES}}": deal.notes or "None",
    }

    memo = template
    for placeholder, value in replacements.items():
        memo = memo.replace(placeholder, value)

    # Save to memos/ directory
    out_dir = _CONTRACTS_BASE / "memos"
    os.makedirs(out_dir, exist_ok=True)

    date_slug = date.today().strftime("%Y-%m-%d")
    filename = f"MEMO_{short_id}_{date_slug}.md"
    out_path = out_dir / filename
    out_path.write_text(memo, encoding="utf-8")

    logger.info(f"Deal memo generated: {out_path} for deal {deal.id}")
    return str(out_path)
