"""
Everlight Rewards Engine -- Models

Tiered loyalty system with:
- 6 tiers: Bronze -> Silver -> Gold -> Platinum -> Diamond -> Legend
- Points per dollar (scales with tier)
- Daily login streaks with milestone bonuses
- Spend-triggered auto-comps (Caesars-style)
- Referral codes + multi-step bonuses
"""
import secrets

from django.db import models
from django.utils import timezone

from payments.models import Customer


TIER_CONFIG = {
    "bronze":   {"min_points": 0,      "points_per_dollar": 1, "badge": "Bronze",   "label": "Bronze"},
    "silver":   {"min_points": 500,    "points_per_dollar": 2, "badge": "Silver",   "label": "Silver"},
    "gold":     {"min_points": 2000,   "points_per_dollar": 3, "badge": "Gold",     "label": "Gold"},
    "platinum": {"min_points": 5000,   "points_per_dollar": 4, "badge": "Platinum", "label": "Platinum"},
    "diamond":  {"min_points": 15000,  "points_per_dollar": 5, "badge": "Diamond",  "label": "Diamond"},
    "legend":   {"min_points": 50000,  "points_per_dollar": 7, "badge": "Legend",   "label": "Legend"},
}

# Days that get milestone (2x) bonuses
LOGIN_MILESTONE_DAYS = {7, 14, 21, 30, 60, 100, 365}


class LoyaltyAccount(models.Model):
    """One loyalty account per customer. Central hub for all rewards activity."""

    TIER_CHOICES = [(k, v["label"]) for k, v in TIER_CONFIG.items()]

    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="loyalty"
    )
    points_balance = models.IntegerField(default=0, help_text="Spendable points balance")
    points_lifetime = models.IntegerField(
        default=0, help_text="All-time earned (used for tier calculation)"
    )
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="bronze")
    total_spent_cents = models.IntegerField(default=0, help_text="Lifetime spend in cents")

    # Daily login streak
    last_login_reward_date = models.DateField(null=True, blank=True)
    login_streak = models.IntegerField(default=0)

    # Referral
    referral_code = models.CharField(max_length=12, unique=True, db_index=True)
    referral_count = models.IntegerField(default=0, help_text="Successful referrals made")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-points_lifetime"]

    def __str__(self):
        return f"{self.customer.email} | {self.tier.title()} | {self.points_balance} pts"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = secrets.token_urlsafe(9)[:12].upper()
        super().save(*args, **kwargs)

    # -- Tier helpers --

    def recalculate_tier(self):
        """Update tier based on lifetime points. Returns True if tier changed."""
        new_tier = "bronze"
        for tier_key, cfg in TIER_CONFIG.items():
            if self.points_lifetime >= cfg["min_points"]:
                new_tier = tier_key
        if self.tier != new_tier:
            self.tier = new_tier
            return True
        return False

    @property
    def tier_badge(self):
        return TIER_CONFIG[self.tier]["badge"]

    @property
    def points_per_dollar(self):
        return TIER_CONFIG[self.tier]["points_per_dollar"]

    @property
    def next_tier(self):
        tiers = list(TIER_CONFIG.keys())
        idx = tiers.index(self.tier)
        return tiers[idx + 1] if idx < len(tiers) - 1 else None

    @property
    def points_to_next_tier(self):
        if not self.next_tier:
            return 0
        return max(0, TIER_CONFIG[self.next_tier]["min_points"] - self.points_lifetime)

    @property
    def tier_progress_pct(self):
        """Percentage progress toward next tier (0-100)."""
        if not self.next_tier:
            return 100
        current_min = TIER_CONFIG[self.tier]["min_points"]
        next_min = TIER_CONFIG[self.next_tier]["min_points"]
        earned_in_tier = self.points_lifetime - current_min
        needed = next_min - current_min
        return min(100, int(earned_in_tier / needed * 100)) if needed > 0 else 0


class LoyaltyTransaction(models.Model):
    """Immutable ledger of every points earn/spend event."""

    TYPE_CHOICES = [
        ("earn_purchase", "Earned: Purchase"),
        ("earn_referral", "Earned: Referral Bonus"),
        ("earn_login",    "Earned: Daily Login"),
        ("earn_streak",   "Earned: Login Streak Milestone"),
        ("earn_signup",   "Earned: Signup Bonus"),
        ("earn_promo",    "Earned: Promo / Admin"),
        ("spend_comp",    "Spent: Comp Redemption"),
        ("spend_reward",  "Spent: Reward Redemption"),
        ("expire",        "Expired"),
        ("adjust",        "Admin Adjustment"),
    ]

    account = models.ForeignKey(
        LoyaltyAccount, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    points = models.IntegerField(help_text="Positive = earn, negative = spend")
    balance_after = models.IntegerField()
    description = models.CharField(max_length=300)
    reference_id = models.CharField(
        max_length=100, blank=True, help_text="Payment ID, session ID, etc."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.points >= 0 else ""
        return (
            f"{self.account.customer.email} | "
            f"{sign}{self.points} pts | {self.get_transaction_type_display()}"
        )


class CompThreshold(models.Model):
    """
    Admin-configured comp trigger rules.
    When customer lifetime spend hits threshold, they earn this comp.
    Set points_cost=0 for automatic comps (Caesars-style).
    Set points_cost>0 for redeemable comps (player chooses to redeem).
    """

    COMP_TYPE_CHOICES = [
        ("service_voucher", "Everlight Service Voucher"),
        ("free_month",      "Free Month of Subscription"),
        ("merch",           "Everlight Merch"),
        ("chips_bonus",     "Bonus Blackjack Chips"),
        ("gems_bonus",      "Bonus Gems"),
        ("vip_trial",       "Free VIP Trial"),
        ("cash_back",       "Cash Back Credit"),
        ("custom",          "Custom Comp"),
    ]

    PRODUCT_CHOICES = [
        ("all",                 "All Products"),
        ("alley_kingz_vip",     "Alley Kingz VIP"),
        ("onyx_pro",            "Onyx POS Pro"),
        ("hivemind_starter",    "Hive Mind Starter"),
        ("hivemind_pro",        "Hive Mind Pro"),
        ("hivemind_enterprise", "Hive Mind Enterprise"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    spend_threshold_cents = models.IntegerField(
        help_text="Lifetime spend in cents to trigger (e.g. 5000 = $50)"
    )
    comp_type = models.CharField(max_length=30, choices=COMP_TYPE_CHOICES)
    product_filter = models.CharField(
        max_length=50, choices=PRODUCT_CHOICES, default="all"
    )
    comp_value = models.CharField(
        max_length=200, blank=True,
        help_text="Display value e.g. '$20 service credit', '500 chips'"
    )
    points_cost = models.IntegerField(
        default=0,
        help_text="Points player must spend to redeem (0 = auto-triggered at threshold)"
    )
    is_active = models.BooleanField(default=True)
    is_repeating = models.BooleanField(
        default=False,
        help_text="Triggers again at each multiple of threshold (e.g. every $50)"
    )
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["spend_threshold_cents", "sort_order"]

    def __str__(self):
        return (
            f"{self.name} "
            f"(${self.spend_threshold_cents / 100:.0f} spend | "
            f"{self.get_comp_type_display()})"
        )


class CompReward(models.Model):
    """A comp that has been triggered for a specific customer."""

    STATUS_CHOICES = [
        ("pending",   "Pending Fulfillment"),
        ("notified",  "Customer Notified"),
        ("fulfilled", "Fulfilled"),
        ("expired",   "Expired"),
        ("declined",  "Declined"),
    ]

    account = models.ForeignKey(
        LoyaltyAccount, on_delete=models.CASCADE, related_name="comps"
    )
    threshold = models.ForeignKey(
        CompThreshold, on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    comp_type = models.CharField(max_length=30)
    description = models.CharField(max_length=500)
    value = models.CharField(max_length=200, blank=True)
    triggered_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Fulfillment notes")

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"{self.account.customer.email} | {self.comp_type} | {self.status}"

    @property
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at


class ReferralUse(models.Model):
    """
    Tracks each use of a referral code.
    Referrer gets points on signup, bonus on first purchase.
    """

    referrer = models.ForeignKey(
        LoyaltyAccount, on_delete=models.CASCADE, related_name="referrals_made"
    )
    referee_email = models.EmailField()
    referee_customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_by",
    )
    referral_code_used = models.CharField(max_length=12)
    signed_up_at = models.DateTimeField(auto_now_add=True)
    converted = models.BooleanField(default=False, help_text="Made their first purchase?")
    converted_at = models.DateTimeField(null=True, blank=True)
    referrer_points_awarded = models.IntegerField(default=0)
    referee_points_awarded = models.IntegerField(default=0)

    class Meta:
        ordering = ["-signed_up_at"]
        unique_together = [("referrer", "referee_email")]

    def __str__(self):
        status = "converted" if self.converted else "pending"
        return f"{self.referrer.customer.email} -> {self.referee_email} ({status})"


class DailyLoginReward(models.Model):
    """
    Per-streak-day reward config.
    Day 1 = small. Day 7 = bigger. Day 30 = milestone.
    Days without a row use a default formula.
    """

    streak_day = models.IntegerField(unique=True)
    points_reward = models.IntegerField(default=15)
    is_milestone = models.BooleanField(
        default=False, help_text="Show special UI treatment"
    )
    chips_bonus = models.IntegerField(default=0, help_text="Bonus blackjack chips")
    gems_bonus = models.IntegerField(default=0, help_text="Bonus gems")
    label = models.CharField(max_length=100, blank=True, help_text="Display text")

    class Meta:
        ordering = ["streak_day"]

    def __str__(self):
        milestone = " *MILESTONE*" if self.is_milestone else ""
        return f"Day {self.streak_day}: {self.points_reward} pts{milestone}"
