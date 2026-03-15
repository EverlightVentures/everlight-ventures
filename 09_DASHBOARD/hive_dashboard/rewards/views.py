"""
Rewards Engine -- Views

Public API endpoints (called by frontend/apps) + staff admin dashboard.
"""
import json
import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from payments.models import Customer
from rewards.models import (
    LoyaltyAccount,
    LoyaltyTransaction,
    CompReward,
    CompThreshold,
    ReferralUse,
    DailyLoginReward,
)
from rewards import services

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@csrf_exempt
@require_GET
def api_account(request, email):
    """GET /rewards/api/account/<email>/  -- loyalty account summary."""
    try:
        customer = Customer.objects.get(email=email)
    except Customer.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)

    summary = services.get_account_summary(customer)
    return JsonResponse(summary)


@csrf_exempt
@require_POST
def api_daily_login(request):
    """
    POST /rewards/api/login/
    Body: {"email": "user@example.com"}
    Claim today's daily login reward.
    """
    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not email:
        return JsonResponse({"error": "email required"}, status=400)

    try:
        customer = Customer.objects.get(email=email)
    except Customer.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)

    result = services.process_daily_login(customer)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def api_referral_apply(request):
    """
    POST /rewards/api/referral/apply/
    Body: {"email": "new@user.com", "code": "ABC123"}
    Apply a referral code at signup.
    """
    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
        code = data.get("code", "").strip().upper()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not email or not code:
        return JsonResponse({"error": "email and code required"}, status=400)

    try:
        customer = Customer.objects.get(email=email)
    except Customer.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)

    referral = services.process_referral_signup(code, customer)
    if referral:
        return JsonResponse({
            "status": "ok",
            "points_awarded": services.REFERRAL_REFEREE_WELCOME,
            "message": f"Referral applied! You earned {services.REFERRAL_REFEREE_WELCOME} bonus points.",
        })
    return JsonResponse(
        {"status": "invalid", "message": "Invalid or already-used referral code."},
        status=400,
    )


@csrf_exempt
@require_POST
def api_redeem_comp(request):
    """
    POST /rewards/api/comp/redeem/
    Body: {"email": "user@example.com", "comp_id": 42}
    Redeem a redeemable comp using points.
    """
    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
        comp_id = data.get("comp_id")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    try:
        customer = Customer.objects.get(email=email)
        account = LoyaltyAccount.objects.get(customer=customer)
    except (Customer.DoesNotExist, LoyaltyAccount.DoesNotExist):
        return JsonResponse({"error": "Account not found"}, status=404)

    success, message = services.redeem_comp(account, comp_id)
    return JsonResponse({"success": success, "message": message})


# ---------------------------------------------------------------------------
# Referral landing page
# ---------------------------------------------------------------------------

def referral_landing(request, code):
    """
    GET /rewards/join/<code>/
    Landing page for referred visitors. Stores code in session for use at signup.
    """
    code = code.upper()
    account = LoyaltyAccount.objects.filter(referral_code=code).first()

    # Stash code in session so signup form can pick it up
    request.session["referral_code"] = code

    context = {
        "referral_code": code,
        "referrer_name": account.customer.name if account else "a friend",
        "bonus_points": services.REFERRAL_REFEREE_WELCOME,
        "valid": account is not None,
    }
    return render(request, "rewards/referral_landing.html", context)


# ---------------------------------------------------------------------------
# Staff admin dashboard
# ---------------------------------------------------------------------------

@staff_member_required
def admin_dashboard(request):
    """
    GET /rewards/admin-dashboard/
    Ops view: pending comps, top players, recent transactions.
    """
    pending_comps = (
        CompReward.objects
        .filter(status="pending")
        .select_related("account__customer", "threshold")
        .order_by("-triggered_at")
    )
    top_accounts = (
        LoyaltyAccount.objects
        .select_related("customer")
        .order_by("-points_lifetime")[:25]
    )
    recent_txns = (
        LoyaltyTransaction.objects
        .select_related("account__customer")
        .order_by("-created_at")[:30]
    )
    total_referrals = LoyaltyAccount.objects.aggregate(
        total=Sum("referral_count")
    )["total"] or 0

    context = {
        "pending_comps": pending_comps,
        "top_accounts": top_accounts,
        "recent_txns": recent_txns,
        "total_accounts": LoyaltyAccount.objects.count(),
        "total_referrals": total_referrals,
        "active_comps": pending_comps.count(),
    }
    return render(request, "rewards/admin_dashboard.html", context)


@staff_member_required
@require_POST
@csrf_exempt
def admin_fulfill_comp(request, comp_id):
    """Mark a comp as fulfilled."""
    comp = get_object_or_404(CompReward, id=comp_id)
    notes = request.POST.get("notes", "")
    comp.status = "fulfilled"
    comp.fulfilled_at = timezone.now()
    comp.notes = notes
    comp.save()
    return JsonResponse({"status": "fulfilled", "comp_id": comp_id})
