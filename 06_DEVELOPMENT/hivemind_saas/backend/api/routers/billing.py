"""
Billing API - Stripe subscription management.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from core.config import settings

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
async def create_checkout(body: SubscribeRequest):
    """
    Create a Stripe Checkout session. Returns a redirect URL.
    Client redirects user to stripe_checkout_url.
    """
    plan = next((p for p in PLANS if p["id"] == body.plan_id), None)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    # TODO: create Stripe checkout session via stripe-python
    # import stripe
    # stripe.api_key = settings.stripe_secret_key
    # price_id = settings.stripe_price_hive if body.plan_id == "hive" else ...
    # session = stripe.checkout.Session.create(...)
    # return {"checkout_url": session.url}

    raise HTTPException(status_code=501, detail="Stripe not yet connected")


@router.post("/portal")
async def billing_portal():
    """Create a Stripe Customer Portal session for self-service billing management."""
    # TODO: stripe.billing_portal.Session.create(...)
    raise HTTPException(status_code=501, detail="Stripe not yet connected")


@router.get("/usage")
async def get_usage():
    """Return current month usage for the tenant (sessions, tokens, seats)."""
    # TODO: query DB aggregate
    return {
        "sessions_used": 0,
        "sessions_limit": 100,
        "seats_used": 1,
        "seats_limit": 1,
        "integrations_count": 0,
        "integrations_limit": 3,
    }
