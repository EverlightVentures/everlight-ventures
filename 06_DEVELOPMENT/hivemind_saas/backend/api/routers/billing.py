"""
Billing API - Stripe subscription management.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import RequestContext, get_request_context
from core.config import settings
from core.database import get_db
from models.tenant import HiveSession, Integration, Tenant, User

router = APIRouter()

PLANS = [
    {
        "id": "spark",
        "name": "Spark",
        "price_monthly": 49,
        "price_annual": 470,  # ~20% off
        "features": [
            "1 user seat",
            "100 hive sessions per month",
            "3 integrations",
            "Basic dashboard",
            "Slack audit logging",
            "Email support",
        ],
        "limits": {"seats": 1, "sessions_per_month": 100, "integrations": 3},
    },
    {
        "id": "hive",
        "name": "Hive",
        "price_monthly": 129,
        "price_annual": 1238,
        "popular": True,
        "features": [
            "5 user seats",
            "Unlimited hive sessions",
            "20 integrations",
            "Mindmap visualization",
            "War Room dashboard",
            "Priority support",
            "Usage analytics",
            "Custom Slack channels",
        ],
        "limits": {"seats": 5, "sessions_per_month": -1, "integrations": 20},
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price_monthly": 399,
        "price_annual": 3830,
        "features": [
            "Unlimited seats",
            "Unlimited sessions",
            "Unlimited integrations",
            "White-label option",
            "Dedicated Slack support",
            "SLA 99.9% uptime",
            "Custom AI agents",
            "SAML SSO",
            "Audit logs export",
        ],
        "limits": {"seats": -1, "sessions_per_month": -1, "integrations": -1},
    },
]


@router.get("/plans")
async def get_plans():
    """Return all available subscription plans."""
    return {"plans": PLANS}


class SubscribeRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"  # "monthly" | "annual"
    success_url: str
    cancel_url: str


@router.post("/subscribe")
async def create_checkout(
    body: SubscribeRequest,
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Stripe Checkout session. Returns a redirect URL.
    Client redirects user to stripe_checkout_url.
    """
    plan = next((p for p in PLANS if p["id"] == body.plan_id), None)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    price_lookup = {
        ("spark", "monthly"): settings.stripe_price_spark,
        ("spark", "annual"): settings.stripe_price_spark,
        ("hive", "monthly"): settings.stripe_price_hive,
        ("hive", "annual"): settings.stripe_price_hive,
        ("enterprise", "monthly"): settings.stripe_price_enterprise,
        ("enterprise", "annual"): settings.stripe_price_enterprise,
    }

    if settings.stripe_secret_key and price_lookup.get((body.plan_id, body.billing_cycle)):
        import stripe

        stripe.api_key = settings.stripe_secret_key
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_lookup[(body.plan_id, body.billing_cycle)], "quantity": 1}],
            success_url=body.success_url,
            cancel_url=body.cancel_url,
            customer_email=context.user.email,
            metadata={
                "tenant_id": context.tenant.id,
                "plan_id": body.plan_id,
                "billing_cycle": body.billing_cycle,
            },
        )
        return {"checkout_url": checkout.url, "mode": "stripe"}

    return {
        "checkout_url": f"{settings.billing_base_url}?tenant_id={context.tenant.id}&plan={body.plan_id}&cycle={body.billing_cycle}",
        "mode": "manual",
        "message": "Stripe is not configured; falling back to manual billing link.",
    }


@router.post("/portal")
async def billing_portal(context: RequestContext = Depends(get_request_context)):
    """Create a Stripe Customer Portal session for self-service billing management."""
    if settings.stripe_secret_key and context.tenant.stripe_customer_id:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        session = stripe.billing_portal.Session.create(
            customer=context.tenant.stripe_customer_id,
            return_url=settings.frontend_url,
        )
        return {"portal_url": session.url, "mode": "stripe"}

    return {
        "portal_url": f"{settings.billing_base_url}?tenant_id={context.tenant.id}",
        "mode": "manual",
        "message": "Stripe billing portal is not configured.",
    }


@router.get("/usage")
async def get_usage(
    context: RequestContext = Depends(get_request_context),
    db: AsyncSession = Depends(get_db),
):
    """Return current month usage for the tenant (sessions, tokens, seats)."""
    plan = next((item for item in PLANS if item["id"] == context.tenant.plan_tier), PLANS[0])
    sessions_used = await db.scalar(
        select(func.count()).select_from(HiveSession).where(HiveSession.tenant_id == context.tenant.id)
    ) or 0
    seats_used = await db.scalar(
        select(func.count()).select_from(User).where(User.tenant_id == context.tenant.id, User.is_active.is_(True))
    ) or 0
    integrations_count = await db.scalar(
        select(func.count()).select_from(Integration).where(Integration.tenant_id == context.tenant.id, Integration.is_active.is_(True))
    ) or 0

    return {
        "plan_id": plan["id"],
        "sessions_used": sessions_used,
        "sessions_limit": plan["limits"]["sessions_per_month"],
        "seats_used": seats_used,
        "seats_limit": plan["limits"]["seats"],
        "integrations_count": integrations_count,
        "integrations_limit": plan["limits"]["integrations"],
    }
