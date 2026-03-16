import hashlib
import hmac
import json
import logging
import os
from datetime import timedelta

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Count, Q

from .models import Customer, Subscription, Payment, RevenueSnapshot

log = logging.getLogger(__name__)

WORKSPACE = "/mnt/sdcard/AA_MY_DRIVE"


def _notify_slack(message, channel="#05-revenue"):
    """Send revenue notification to Slack."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        import requests
        requests.post(webhook, json={"text": message, "channel": channel}, timeout=5)
    except Exception:
        pass


def _send_receipt_email(customer, payment):
    """Trigger receipt email via SMTP."""
    try:
        import smtplib
        from email.mime.text import MIMEText

        smtp_host = os.environ.get("SMTP_HOST")
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")
        if not all([smtp_host, smtp_user, smtp_pass]):
            return

        body = f"""Thank you for your purchase!

Product: {payment.product}
Amount: ${payment.amount_cents / 100:.2f}
Date: {payment.created_at.strftime('%B %d, %Y')}

{'Receipt: ' + payment.receipt_url if payment.receipt_url else ''}

Questions? Reply to this email or visit everlightventures.io

-- Everlight Ventures
"""
        msg = MIMEText(body)
        msg["Subject"] = f"Receipt: {payment.product} -- ${payment.amount_cents / 100:.2f}"
        msg["From"] = smtp_user
        msg["To"] = customer.email

        port = int(os.environ.get("SMTP_PORT", "587"))
        with smtplib.SMTP(smtp_host, port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        log.info(f"Receipt sent to {customer.email}")
    except Exception as e:
        log.warning(f"Receipt email failed: {e}")


# -- Stripe Webhook Handler --------------------------------------------------

@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Receives Stripe webhook events and processes them.
    Handles: payment_intent.succeeded, customer.subscription.created/updated/deleted,
    checkout.session.completed, invoice.paid
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    # Verify signature if we have the secret
    if endpoint_secret:
        try:
            import stripe
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except (ValueError, Exception) as e:
            log.warning(f"Stripe webhook signature verification failed: {e}")
            return HttpResponse(status=400)
    else:
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    log.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout(data)
    elif event_type == "payment_intent.succeeded":
        _handle_payment(data)
    elif event_type == "invoice.paid":
        _handle_invoice_paid(data)
    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        _handle_subscription_update(data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_canceled(data)

    return HttpResponse(status=200)


def _get_or_create_customer(stripe_data):
    """Get or create a Customer from Stripe data."""
    email = stripe_data.get("customer_email", "") or stripe_data.get("email", "")
    stripe_id = stripe_data.get("customer", "") or stripe_data.get("id", "")

    if not email and stripe_id:
        # Try to find by stripe ID
        customer = Customer.objects.filter(stripe_customer_id=stripe_id).first()
        if customer:
            return customer

    if email:
        customer, created = Customer.objects.get_or_create(
            email=email,
            defaults={"stripe_customer_id": stripe_id}
        )
        if not customer.stripe_customer_id and stripe_id:
            customer.stripe_customer_id = stripe_id
            customer.save()
        return customer

    return None


def _handle_checkout(data):
    """Process completed checkout session."""
    customer = _get_or_create_customer(data)
    if not customer:
        return

    product = data.get("metadata", {}).get("product", "unknown")
    customer.source = customer.source or product
    customer.save()

    amount = data.get("amount_total", 0)
    _notify_slack(
        f"NEW SALE: ${amount/100:.2f} -- {product} -- {customer.email}"
    )


def _handle_payment(data):
    """Process successful payment."""
    customer = _get_or_create_customer(data)
    if not customer:
        return

    payment_id = data.get("id", "")
    if Payment.objects.filter(stripe_payment_id=payment_id).exists():
        return

    amount = data.get("amount", 0) or data.get("amount_received", 0)
    product = data.get("metadata", {}).get("product", "unknown")

    payment = Payment.objects.create(
        customer=customer,
        stripe_payment_id=payment_id,
        product=product,
        amount_cents=amount,
        status="succeeded",
        receipt_url=data.get("receipt_url", ""),
        metadata=data.get("metadata", {}),
    )

    _send_receipt_email(customer, payment)
    _notify_slack(
        f"PAYMENT: ${amount/100:.2f} -- {product} -- {customer.email}"
    )


def _handle_invoice_paid(data):
    """Process paid invoice (subscription renewals)."""
    customer = _get_or_create_customer(data)
    if not customer:
        return

    payment_id = data.get("payment_intent", "") or data.get("id", "")
    if Payment.objects.filter(stripe_payment_id=payment_id).exists():
        return

    amount = data.get("amount_paid", 0)
    product = data.get("lines", {}).get("data", [{}])[0].get("description", "Subscription")

    payment = Payment.objects.create(
        customer=customer,
        stripe_payment_id=payment_id,
        product=product,
        amount_cents=amount,
        payment_type="subscription",
        status="succeeded",
    )

    _send_receipt_email(customer, payment)


def _handle_subscription_update(data):
    """Create or update subscription record."""
    stripe_sub_id = data.get("id", "")
    stripe_customer_id = data.get("customer", "")

    customer = Customer.objects.filter(stripe_customer_id=stripe_customer_id).first()
    if not customer:
        return

    plan = data.get("plan", {}) or {}
    amount = plan.get("amount", 0)
    product_id = plan.get("product", "") or data.get("metadata", {}).get("product", "unknown")

    # Map Stripe product IDs to our product codes (configured in env)
    product_map = json.loads(os.environ.get("STRIPE_PRODUCT_MAP", "{}"))
    product = product_map.get(product_id, product_id)

    sub, created = Subscription.objects.update_or_create(
        stripe_subscription_id=stripe_sub_id,
        defaults={
            "customer": customer,
            "product": product,
            "status": data.get("status", "active"),
            "amount_cents": amount,
            "current_period_end": timezone.datetime.fromtimestamp(
                data.get("current_period_end", 0), tz=timezone.utc
            ) if data.get("current_period_end") else None,
            "trial_end": timezone.datetime.fromtimestamp(
                data.get("trial_end", 0), tz=timezone.utc
            ) if data.get("trial_end") else None,
        }
    )

    if created:
        _notify_slack(
            f"NEW SUBSCRIPTION: {product} -- ${amount/100:.2f}/mo -- {customer.email}"
        )


def _handle_subscription_canceled(data):
    """Handle subscription cancellation."""
    stripe_sub_id = data.get("id", "")
    sub = Subscription.objects.filter(stripe_subscription_id=stripe_sub_id).first()
    if sub:
        sub.status = "canceled"
        sub.canceled_at = timezone.now()
        sub.save()
        _notify_slack(
            f"CHURN: {sub.product} canceled -- {sub.customer.email}"
        )


# -- Revenue Dashboard -------------------------------------------------------

def revenue_dashboard(request):
    """Revenue overview for the ops dashboard."""
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())

    # MRR
    active_subs = Subscription.objects.filter(status__in=["active", "trialing"])
    mrr_cents = active_subs.aggregate(total=Sum("amount_cents"))["total"] or 0
    mrr = mrr_cents / 100

    # Revenue today / this week / this month
    rev_today = Payment.objects.filter(
        created_at__date=today, status="succeeded"
    ).aggregate(total=Sum("amount_cents"))["total"] or 0

    rev_week = Payment.objects.filter(
        created_at__date__gte=week_start, status="succeeded"
    ).aggregate(total=Sum("amount_cents"))["total"] or 0

    rev_month = Payment.objects.filter(
        created_at__date__gte=month_start, status="succeeded"
    ).aggregate(total=Sum("amount_cents"))["total"] or 0

    # Customer counts
    total_customers = Customer.objects.count()
    new_today = Customer.objects.filter(created_at__date=today).count()
    active_sub_count = active_subs.count()

    # Revenue by product
    product_breakdown = (
        Payment.objects.filter(created_at__date__gte=month_start, status="succeeded")
        .values("product")
        .annotate(total=Sum("amount_cents"), count=Count("id"))
        .order_by("-total")
    )

    # MRR by product
    mrr_breakdown = (
        active_subs
        .values("product")
        .annotate(total=Sum("amount_cents"), count=Count("id"))
        .order_by("-total")
    )

    # Recent payments
    recent_payments = Payment.objects.filter(status="succeeded")[:10]

    # 30-day revenue chart data
    chart_data = []
    for i in range(30):
        d = today - timedelta(days=29 - i)
        day_rev = Payment.objects.filter(
            created_at__date=d, status="succeeded"
        ).aggregate(total=Sum("amount_cents"))["total"] or 0
        chart_data.append({"date": d.isoformat(), "revenue": day_rev / 100})

    # Goal tracking ($10k/mo)
    goal = 10000
    progress_pct = min(int(rev_month / 100 / goal * 100), 100) if goal > 0 else 0

    context = {
        "mrr": mrr,
        "rev_today": rev_today / 100,
        "rev_week": rev_week / 100,
        "rev_month": rev_month / 100,
        "total_customers": total_customers,
        "new_today": new_today,
        "active_subscriptions": active_sub_count,
        "product_breakdown": product_breakdown,
        "mrr_breakdown": mrr_breakdown,
        "recent_payments": recent_payments,
        "chart_data": json.dumps(chart_data),
        "goal": goal,
        "goal_pct": progress_pct,
    }

    return render(request, "payments/revenue_dashboard.html", context)


@csrf_exempt
@require_GET
def api_revenue_summary(request):
    """API endpoint for revenue data (used by Jupyter notebooks, agents)."""
    now = timezone.now()
    today = now.date()
    month_start = today.replace(day=1)

    active_subs = Subscription.objects.filter(status__in=["active", "trialing"])
    mrr_cents = active_subs.aggregate(total=Sum("amount_cents"))["total"] or 0

    rev_month = Payment.objects.filter(
        created_at__date__gte=month_start, status="succeeded"
    ).aggregate(total=Sum("amount_cents"))["total"] or 0

    return JsonResponse({
        "mrr": mrr_cents / 100,
        "revenue_this_month": rev_month / 100,
        "active_subscriptions": active_subs.count(),
        "total_customers": Customer.objects.count(),
        "goal": 10000,
        "goal_pct": min(int(rev_month / 100 / 10000 * 100), 100),
    })
