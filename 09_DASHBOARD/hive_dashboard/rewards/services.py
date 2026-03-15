"""
Everlight Rewards Engine -- Service Layer

All business logic: points awarding, comp triggers, referrals, daily login.
Call these from payment webhooks, login events, and signup flows.
"""
import logging
import os
from datetime import date, timedelta

import requests
from django.db import transaction
from django.utils import timezone

log = logging.getLogger(__name__)

# -- Points config --
SIGNUP_BONUS_POINTS = 150
REFERRAL_REFERRER_ON_SIGNUP = 250      # referrer earns when someone signs up
REFERRAL_REFEREE_WELCOME = 100         # new customer welcome bonus
REFERRAL_REFERRER_ON_CONVERSION = 500  # referrer earns when referee makes first purchase
DEFAULT_DAILY_LOGIN_POINTS = 15


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _slack(message, channel="#05-revenue"):
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"text": message, "channel": channel}, timeout=5)
    except Exception:
        pass


def _award_points(account, points, transaction_type, description, reference_id=""):
    """Award (or deduct) points atomically. Returns updated account."""
    from rewards.models import LoyaltyTransaction

    with transaction.atomic():
        account.points_balance = max(0, account.points_balance + points)
        if points > 0:
            account.points_lifetime += points

        tier_changed = account.recalculate_tier()
        account.save()

        LoyaltyTransaction.objects.create(
            account=account,
            transaction_type=transaction_type,
            points=points,
            balance_after=account.points_balance,
            description=description,
            reference_id=reference_id,
        )

        if tier_changed:
            _slack(
                f"TIER UP: {account.customer.email} is now {account.tier.title()} "
                f"({account.tier_badge}) | {account.points_lifetime} lifetime pts"
            )

    return account


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_or_create_loyalty(customer):
    """Get or create a LoyaltyAccount for a customer. Issues signup bonus once."""
    from rewards.models import LoyaltyAccount

    account, created = LoyaltyAccount.objects.get_or_create(customer=customer)
    if created:
        _award_points(
            account, SIGNUP_BONUS_POINTS,
            "earn_signup", "Welcome to Everlight Rewards!"
        )
        log.info(f"New loyalty account created: {customer.email}")
    return account


def award_purchase_points(customer, amount_cents, payment_id="", product=""):
    """
    Award loyalty points for a payment.
    Call this from the Stripe payment webhook handler.
    """
    if amount_cents <= 0:
        return

    account = get_or_create_loyalty(customer)
    dollars = amount_cents / 100
    pts = max(1, int(dollars * account.points_per_dollar))

    # Update lifetime spend (needed for comp threshold checks)
    with transaction.atomic():
        account.total_spent_cents += amount_cents
        account.save(update_fields=["total_spent_cents"])

    _award_points(
        account, pts, "earn_purchase",
        f"Purchase: {product or 'unknown'} (${dollars:.2f})",
        reference_id=payment_id,
    )

    # Check for first-purchase referral conversion bonus
    process_referral_conversion(customer)

    # Check if any comp thresholds were crossed
    check_comp_thresholds(account)

    log.info(f"Awarded {pts} pts to {customer.email} for ${dollars:.2f}")


def check_comp_thresholds(account):
    """
    Check if customer's lifetime spend qualifies them for any auto-comps.
    Only fires for CompThresholds with points_cost=0 (auto-triggered).
    """
    from rewards.models import CompThreshold, CompReward

    thresholds = CompThreshold.objects.filter(is_active=True, points_cost=0)

    for threshold in thresholds:
        if account.total_spent_cents < threshold.spend_threshold_cents:
            continue

        existing = CompReward.objects.filter(
            account=account, threshold=threshold
        )

        if threshold.is_repeating:
            # How many times should it have triggered?
            expected_count = account.total_spent_cents // threshold.spend_threshold_cents
            if existing.count() < expected_count:
                _trigger_comp(account, threshold)
        else:
            if not existing.exists():
                _trigger_comp(account, threshold)


def _trigger_comp(account, threshold):
    """Create a CompReward and alert the fulfillment team via Slack."""
    from rewards.models import CompReward

    comp = CompReward.objects.create(
        account=account,
        threshold=threshold,
        comp_type=threshold.comp_type,
        description=f"Comp earned: {threshold.name}",
        value=threshold.comp_value,
        expires_at=timezone.now() + timedelta(days=90),
    )

    log.info(f"Comp triggered: {account.customer.email} -> {threshold.name}")
    _slack(
        f"COMP TRIGGERED: {account.customer.email} earned '{threshold.name}' "
        f"| Lifetime spend: ${account.total_spent_cents / 100:.0f} "
        f"| Type: {threshold.comp_type} | Value: {threshold.comp_value}",
        channel="#05-revenue",
    )
    return comp


def process_daily_login(customer):
    """
    Process a daily login reward claim.
    Returns dict: {points_awarded, streak_day, already_claimed_today, is_milestone}
    """
    from rewards.models import DailyLoginReward

    account = get_or_create_loyalty(customer)
    today = date.today()

    if account.last_login_reward_date == today:
        return {
            "points_awarded": 0,
            "streak_day": account.login_streak,
            "already_claimed_today": True,
            "is_milestone": False,
        }

    # Streak continuity: must have claimed yesterday
    yesterday = today - timedelta(days=1)
    if account.last_login_reward_date == yesterday:
        account.login_streak += 1
    else:
        account.login_streak = 1  # reset

    # Look up reward config for this streak day
    reward_cfg = DailyLoginReward.objects.filter(streak_day=account.login_streak).first()
    if reward_cfg:
        pts = reward_cfg.points_reward
        is_milestone = reward_cfg.is_milestone
    else:
        # Default formula: base + 5 pts per completed 7-day week
        pts = DEFAULT_DAILY_LOGIN_POINTS + (account.login_streak // 7) * 5
        is_milestone = account.login_streak in {7, 14, 21, 30, 60, 100, 365}

    if is_milestone:
        pts = int(pts * 2)  # 2x on milestones
        tx_type = "earn_streak"
        desc = f"Streak milestone! Day {account.login_streak} (2x bonus = {pts} pts)"
    else:
        tx_type = "earn_login"
        desc = f"Daily login reward (day {account.login_streak} streak)"

    account.last_login_reward_date = today
    account.save(update_fields=["last_login_reward_date", "login_streak"])
    _award_points(account, pts, tx_type, desc)

    return {
        "points_awarded": pts,
        "streak_day": account.login_streak,
        "already_claimed_today": False,
        "is_milestone": is_milestone,
    }


def process_referral_signup(referral_code, new_customer):
    """
    Called when a new customer signs up using a referral code.
    Awards welcome points to new customer and signup credit to referrer.
    Returns the ReferralUse instance or None.
    """
    from rewards.models import LoyaltyAccount, ReferralUse

    if not referral_code:
        return None

    referrer_account = LoyaltyAccount.objects.filter(
        referral_code=referral_code.upper()
    ).first()

    if not referrer_account:
        log.warning(f"Referral code not found: {referral_code}")
        return None

    if referrer_account.customer == new_customer:
        return None  # no self-referrals

    # Prevent duplicate referral from same email
    if ReferralUse.objects.filter(
        referrer=referrer_account, referee_email=new_customer.email
    ).exists():
        return None

    referee_account = get_or_create_loyalty(new_customer)

    referral = ReferralUse.objects.create(
        referrer=referrer_account,
        referee_email=new_customer.email,
        referee_customer=new_customer,
        referral_code_used=referral_code.upper(),
        referrer_points_awarded=REFERRAL_REFERRER_ON_SIGNUP,
        referee_points_awarded=REFERRAL_REFEREE_WELCOME,
    )

    _award_points(
        referrer_account, REFERRAL_REFERRER_ON_SIGNUP,
        "earn_referral",
        f"Referral: {new_customer.email} signed up using your link",
        reference_id=str(referral.id),
    )
    _award_points(
        referee_account, REFERRAL_REFEREE_WELCOME,
        "earn_referral",
        f"Welcome bonus! Referred by {referrer_account.customer.email}",
    )

    referrer_account.referral_count += 1
    referrer_account.save(update_fields=["referral_count"])

    log.info(
        f"Referral signup: {referrer_account.customer.email} -> {new_customer.email}"
    )
    return referral


def process_referral_conversion(customer):
    """
    Called on first purchase by a referred customer.
    Awards conversion bonus to referrer. Safe to call on every purchase (idempotent).
    """
    from rewards.models import ReferralUse

    referral = ReferralUse.objects.filter(
        referee_customer=customer, converted=False
    ).first()

    if not referral:
        return

    referral.converted = True
    referral.converted_at = timezone.now()
    bonus = REFERRAL_REFERRER_ON_CONVERSION
    referral.referrer_points_awarded += bonus
    referral.save()

    _award_points(
        referral.referrer, bonus,
        "earn_referral",
        f"Referral converted: {customer.email} made their first purchase!",
        reference_id=str(referral.id),
    )
    log.info(
        f"Referral conversion: {referral.referrer.customer.email} +{bonus} pts"
    )


def redeem_comp(account, comp_id):
    """
    Spend points to redeem a redeemable comp (points_cost > 0).
    Returns (success: bool, message: str)
    """
    from rewards.models import CompReward, CompThreshold

    try:
        comp = CompReward.objects.get(
            id=comp_id, account=account, status="pending"
        )
    except CompReward.DoesNotExist:
        return False, "Comp not found or already redeemed."

    if comp.is_expired:
        comp.status = "expired"
        comp.save()
        return False, "This comp has expired."

    if comp.threshold and comp.threshold.points_cost > 0:
        cost = comp.threshold.points_cost
        if account.points_balance < cost:
            return False, f"Not enough points (need {cost}, have {account.points_balance})."
        _award_points(
            account, -cost, "spend_comp",
            f"Redeemed: {comp.description}",
            reference_id=str(comp.id),
        )

    comp.status = "notified"
    comp.save()

    _slack(
        f"COMP REDEEMED: {account.customer.email} | {comp.description} | {comp.value}",
        channel="#05-revenue",
    )
    return True, "Comp redeemed! Our team will be in touch."


def get_account_summary(customer):
    """Return a JSON-serializable dict of the customer's loyalty status."""
    account = get_or_create_loyalty(customer)
    pending_comps = account.comps.filter(status="pending").count()
    recent_txns = list(
        account.transactions.values(
            "transaction_type", "points", "balance_after", "description", "created_at"
        )[:10]
    )

    # Stringify datetimes for JSON
    for t in recent_txns:
        if t.get("created_at"):
            t["created_at"] = t["created_at"].isoformat()

    return {
        "email": customer.email,
        "points_balance": account.points_balance,
        "points_lifetime": account.points_lifetime,
        "tier": account.tier,
        "tier_badge": account.tier_badge,
        "tier_progress_pct": account.tier_progress_pct,
        "next_tier": account.next_tier,
        "points_to_next_tier": account.points_to_next_tier,
        "total_spent": round(account.total_spent_cents / 100, 2),
        "login_streak": account.login_streak,
        "referral_code": account.referral_code,
        "referral_count": account.referral_count,
        "pending_comps": pending_comps,
        "recent_transactions": recent_txns,
    }
