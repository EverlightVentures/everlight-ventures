"""
Webhooks - Stripe events and OAuth callbacks.
"""

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.tenant import Tenant

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
    import stripe

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc

    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata", {}) or {}
    tenant_id = metadata.get("tenant_id")

    async with AsyncSessionLocal() as db:
        tenant = None
        if tenant_id:
            tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))

        if event_type in {"checkout.session.completed", "customer.subscription.created", "customer.subscription.updated"} and tenant:
            tenant.plan_tier = metadata.get("plan_id", tenant.plan_tier)
            tenant.stripe_customer_id = obj.get("customer", tenant.stripe_customer_id)
            tenant.stripe_subscription_id = obj.get("subscription", tenant.stripe_subscription_id)
            await db.commit()
            await post_audit(
                AuditEvent.SUBSCRIPTION_CREATED,
                tenant_name=tenant.name,
                tenant_id=tenant.id,
                summary=f"Subscription activated for {tenant.plan_tier}.",
                details={"event_type": event_type},
            )
        elif event_type == "customer.subscription.deleted" and tenant:
            tenant.plan_tier = "spark"
            tenant.stripe_subscription_id = ""
            await db.commit()
            await post_audit(
                AuditEvent.SUBSCRIPTION_CANCELLED,
                tenant_name=tenant.name,
                tenant_id=tenant.id,
                summary="Subscription canceled; tenant returned to spark tier.",
                details={"event_type": event_type},
            )
        elif event_type == "invoice.payment_succeeded" and tenant:
            await post_audit(
                AuditEvent.BILLING_PAYMENT,
                tenant_name=tenant.name,
                tenant_id=tenant.id,
                summary="Invoice payment succeeded.",
                details={"event_type": event_type, "amount_paid": obj.get("amount_paid", 0)},
            )
        elif event_type == "invoice.payment_failed" and tenant:
            await post_audit(
                AuditEvent.BILLING_FAILED,
                tenant_name=tenant.name,
                tenant_id=tenant.id,
                summary="Invoice payment failed.",
                details={"event_type": event_type},
            )

    return {"received": True, "event_type": event_type}
