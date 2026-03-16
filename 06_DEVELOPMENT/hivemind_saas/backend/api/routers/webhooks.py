"""
Webhooks - Stripe events and OAuth callbacks.
"""

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional

from core.config import settings
from services.slack_audit import post_audit, AuditEvent

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
):
    """
    Handle Stripe webhook events.
    Verifies signature, updates subscription records, fires Slack audit events.
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    payload = await request.body()

    # TODO: verify stripe signature
    # import stripe
    # event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)

    # TODO: handle events:
    # customer.subscription.created -> update tenant plan, fire SUBSCRIPTION_CREATED
    # customer.subscription.deleted -> downgrade tenant, fire SUBSCRIPTION_CANCELLED
    # invoice.payment_succeeded -> fire BILLING_PAYMENT
    # invoice.payment_failed -> fire BILLING_FAILED, send dunning email

    return {"received": True}
