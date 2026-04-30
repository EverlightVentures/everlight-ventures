"""
Everlight Blackjack - Models
Full in-game economy: chips, premium gems, cosmetics, avatars, ad rewards
"""
import uuid

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bj_profile')
    # Currencies
    chips = models.BigIntegerField(default=1000)          # Free currency (Gold Coins in sweepstakes)
    gems = models.IntegerField(default=0)                  # Premium currency ($)
    sweeps_coins = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Redeemable for cash (1 SC = $1)
    total_chips_won = models.BigIntegerField(default=0)
    total_chips_lost = models.BigIntegerField(default=0)
    total_sc_won = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sc_redeemed = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Crypto wallet (for international OnyxBet)
    crypto_balance_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # USD equivalent
    crypto_deposit_address = models.CharField(max_length=128, blank=True, default='')
    preferred_crypto = models.CharField(max_length=10, default='BTC')  # BTC, ETH, XLM, USDT

    # Player region (determines sweepstakes vs crypto mode)
    region = models.CharField(max_length=10, default='us')  # us, intl
    country_code = models.CharField(max_length=2, default='US')
    kyc_verified = models.BooleanField(default=False)
    kyc_verified_at = models.DateTimeField(null=True, blank=True)

    # Stats
    hands_played = models.IntegerField(default=0)
    hands_won = models.IntegerField(default=0)
    hands_lost = models.IntegerField(default=0)
    hands_push = models.IntegerField(default=0)
    blackjacks = models.IntegerField(default=0)
    biggest_win = models.BigIntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    best_streak = models.IntegerField(default=0)

    # Rank / XP
    xp = models.IntegerField(default=0)
    rank = models.CharField(max_length=20, default='Bronze')  # Bronze/Silver/Gold/Platinum/Diamond/Legend
    rank_points = models.IntegerField(default=0)

    # Avatar
    avatar_name = models.CharField(max_length=60, default='Player')
    avatar_base = models.CharField(max_length=30, default='silhouette_1')  # base model id
    avatar_outfit = models.CharField(max_length=30, default='default_suit')
    avatar_accessory = models.CharField(max_length=30, default='none')
    avatar_hat = models.CharField(max_length=30, default='none')
    avatar_aura = models.CharField(max_length=30, default='none')  # hologram effect
    avatar_title = models.CharField(max_length=60, default='Rookie')
    avatar_color_primary = models.CharField(max_length=7, default='#c9a84c')
    avatar_color_secondary = models.CharField(max_length=7, default='#1a1a2e')

    # Table seat preference
    seat_number = models.IntegerField(default=1)  # 1-5

    # OAuth provider
    oauth_provider = models.CharField(max_length=20, blank=True, default='')
    oauth_uid = models.CharField(max_length=100, blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')

    # Ad rewards
    ad_refills_today = models.IntegerField(default=0)
    ad_refill_date = models.DateField(null=True, blank=True)

    # Achievements (list of unlocked achievement ids)
    achievements = models.JSONField(default=list)

    # VIP subscription
    is_vip = models.BooleanField(default=False)
    vip_expires = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_played = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'bj_player_profile'

    def __str__(self):
        return f"{self.user.username} | {self.chips:,} chips | Rank: {self.rank}"

    @property
    def win_rate(self):
        if self.hands_played == 0:
            return 0
        return round(self.hands_won / self.hands_played * 100, 1)

    @property
    def can_refill_today(self):
        today = timezone.now().date()
        if self.ad_refill_date != today:
            return True
        return self.ad_refills_today < 10

    @property
    def refills_remaining(self):
        today = timezone.now().date()
        if self.ad_refill_date != today:
            return 10
        return max(0, 10 - self.ad_refills_today)

    def get_rank_from_xp(self):
        thresholds = [
            (0, 'Bronze'), (1000, 'Silver'), (5000, 'Gold'),
            (15000, 'Platinum'), (40000, 'Diamond'), (100000, 'Legend')
        ]
        rank = 'Bronze'
        for threshold, name in thresholds:
            if self.xp >= threshold:
                rank = name
        return rank

    def get_avatar_config(self):
        return {
            'base': self.avatar_base,
            'outfit': self.avatar_outfit,
            'accessory': self.avatar_accessory,
            'hat': self.avatar_hat,
            'aura': self.avatar_aura,
            'name': self.avatar_name,
            'title': self.avatar_title,
            'color_primary': self.avatar_color_primary,
            'color_secondary': self.avatar_color_secondary,
            'rank': self.rank,
            'xp': self.xp,
        }


class CosmeticItem(models.Model):
    CATEGORY_CHOICES = [
        ('outfit', 'Outfit'),
        ('accessory', 'Accessory'),
        ('hat', 'Hat'),
        ('aura', 'Aura / Hologram'),
        ('card_back', 'Card Back'),
        ('table_felt', 'Table Felt'),
        ('chip_style', 'Chip Style'),
        ('title', 'Title'),
        ('emote', 'Emote'),
    ]
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]

    item_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    description = models.TextField(blank=True)
    thumbnail = models.CharField(max_length=100, blank=True)  # icon ref

    # Pricing (3-tier model)
    price_chips = models.IntegerField(default=0)    # Free currency price (0 = not available for chips)
    price_gems = models.IntegerField(default=0)     # Premium currency ($0.01/gem roughly)
    price_usd = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # Direct $ purchase

    # Unlock conditions
    rank_required = models.CharField(max_length=20, default='Bronze')
    is_limited = models.BooleanField(default=False)
    is_vip_only = models.BooleanField(default=False)

    # Visual data (color, shader, etc.)
    visual_config = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bj_cosmetic_item'
        ordering = ['category', 'rarity', 'name']

    def __str__(self):
        return f"[{self.rarity.upper()}] {self.name} ({self.category})"


class PlayerInventory(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='inventory')
    item = models.ForeignKey(CosmeticItem, on_delete=models.CASCADE)
    acquired_at = models.DateTimeField(auto_now_add=True)
    acquisition_method = models.CharField(max_length=30, default='purchase')  # purchase/reward/achievement

    class Meta:
        db_table = 'bj_player_inventory'
        unique_together = ['player', 'item']

    def __str__(self):
        return f"{self.player.avatar_name} owns {self.item.name}"


class GameSession(models.Model):
    OUTCOME_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('push', 'Push'),
        ('blackjack', 'Blackjack'),
        ('bust', 'Bust'),
        ('surrender', 'Surrender'),
    ]
    STATE_CHOICES = [
        ('pending', 'Pending'),
        ('player_turn', 'Player Turn'),
        ('dealer_turn', 'Dealer Turn'),
        ('settled', 'Settled'),
    ]

    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='game_sessions')
    session_id = models.CharField(max_length=40, unique=True)

    # Server FSM state
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='pending')

    # Bet
    bet_chips = models.BigIntegerField(default=0)
    side_bet_chips = models.BigIntegerField(default=0)  # War bet / insurance
    doubled = models.BooleanField(default=False)

    # Cards (stored as JSON lists)
    player_hand = models.JSONField(default=list)
    dealer_hand = models.JSONField(default=list)
    player_value = models.IntegerField(default=0)
    dealer_value = models.IntegerField(default=0)

    # Server-authoritative shoe (NEVER exposed in API responses)
    shoe_state = models.JSONField(default=list)
    shoe_seed = models.CharField(max_length=64, blank=True, default='')
    action_log = models.JSONField(default=list)

    # Outcome
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, blank=True)
    chips_delta = models.BigIntegerField(default=0)  # net gain/loss

    # Meta
    deck_count = models.IntegerField(default=6)
    played_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.IntegerField(default=0)

    # XP earned this hand
    xp_earned = models.IntegerField(default=0)

    # Alley Kingz mechanic: "Table Presence" multiplier from fashion score
    presence_multiplier = models.FloatField(default=1.0)

    class Meta:
        db_table = 'bj_game_session'
        ordering = ['-played_at']

    def __str__(self):
        return f"{self.player.avatar_name} | {self.outcome} | {self.chips_delta:+,} chips"


class AdRewardLog(models.Model):
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='ad_rewards')
    reward_date = models.DateField()
    chips_awarded = models.IntegerField(default=100)
    ad_unit_id = models.CharField(max_length=100, blank=True)
    rewarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bj_ad_reward_log'

    def __str__(self):
        return f"{self.player.avatar_name} | +{self.chips_awarded} chips | {self.reward_date}"


class Leaderboard(models.Model):
    """Snapshot leaderboard updated periodically"""
    PERIOD_CHOICES = [('daily', 'Daily'), ('weekly', 'Weekly'), ('alltime', 'All Time')]
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    rank_position = models.IntegerField()
    chips_won = models.BigIntegerField(default=0)
    hands_won = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bj_leaderboard'
        ordering = ['period', 'rank_position']


class GemPackage(models.Model):
    """Premium gem purchase packages"""
    name = models.CharField(max_length=50)
    gems = models.IntegerField()
    bonus_gems = models.IntegerField(default=0)
    price_usd = models.DecimalField(max_digits=6, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'bj_gem_package'
        ordering = ['price_usd']

    def __str__(self):
        total = self.gems + self.bonus_gems
        return f"{self.name}: {total} gems for ${self.price_usd}"


class GemPurchase(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name="gem_purchases")
    package = models.ForeignKey(GemPackage, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, default="")
    amount_cents = models.IntegerField(default=0)
    currency = models.CharField(max_length=10, default="usd")
    gems_awarded = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    purchased_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "bj_gem_purchase"
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.player.avatar_name} | {self.session_id} | {self.status}"


# ============================================================
# CASINO EXPANSION: Provably Fair + Multi-Game + Sweepstakes
# ============================================================

class ProvablyFairSeed(models.Model):
    """Server seed pairs for provably fair games.

    Each player gets an active seed pair. After rotation (or game end),
    the server seed is revealed so the player can verify.
    """
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='pf_seeds')
    server_seed = models.CharField(max_length=64)          # hex, NEVER shown until rotated
    server_seed_hash = models.CharField(max_length=64)     # SHA-256 of server_seed, shown to player
    client_seed = models.CharField(max_length=32)          # player-provided or auto-generated
    nonce = models.IntegerField(default=0)                  # increments per game round
    is_active = models.BooleanField(default=True)           # only one active pair per player
    revealed = models.BooleanField(default=False)           # True after rotation (seed exposed)
    games_played = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    revealed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'casino_pf_seeds'
        ordering = ['-created_at']

    def __str__(self):
        status = "ACTIVE" if self.is_active else "REVEALED" if self.revealed else "EXPIRED"
        return f"{self.player.avatar_name} | {status} | nonce={self.nonce}"


class CasinoGameRound(models.Model):
    """Universal game round record. Works for ALL casino games."""
    GAME_CHOICES = [
        ('blackjack', 'Blackjack'),
        ('roulette', 'Roulette'),
        ('crash', 'Crash'),
        ('dice', 'Dice'),
        ('plinko', 'Plinko'),
        ('mines', 'Mines'),
    ]
    CURRENCY_CHOICES = [
        ('chips', 'Chips / Gold Coins'),
        ('sc', 'Sweeps Coins'),
        ('crypto', 'Crypto (USD equivalent)'),
    ]

    round_id = models.CharField(max_length=40, unique=True, default=uuid.uuid4)
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='casino_rounds')
    game = models.CharField(max_length=20, choices=GAME_CHOICES)
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='chips')

    # Bet + outcome
    bet_amount = models.DecimalField(max_digits=12, decimal_places=2)
    win_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    multiplier = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    # Provably fair reference
    seed_pair = models.ForeignKey(ProvablyFairSeed, on_delete=models.SET_NULL, null=True, blank=True)
    nonce_used = models.IntegerField(default=0)

    # Game-specific data (the full result JSON)
    game_data = models.JSONField(default=dict)

    # XP earned
    xp_earned = models.IntegerField(default=0)

    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'casino_game_round'
        ordering = ['-played_at']

    def __str__(self):
        return f"{self.player.avatar_name} | {self.game} | {self.net:+} {self.currency}"


class CashoutRequest(models.Model):
    """Sweeps Coin or crypto withdrawal request."""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('kyc_required', 'KYC Required'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('denied', 'Denied'),
    ]
    METHOD_CHOICES = [
        ('paypal', 'PayPal'),
        ('bank', 'Bank Transfer'),
        ('crypto', 'Cryptocurrency'),
        ('skrill', 'Skrill'),
    ]

    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='cashout_requests')
    # Amount
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='sc')  # sc or crypto
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='paypal')
    destination = models.CharField(max_length=255)  # PayPal email, bank details, crypto address

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    denial_reason = models.TextField(blank=True, default='')

    # Transaction reference
    external_tx_id = models.CharField(max_length=255, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'casino_cashout_request'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.player.avatar_name} | ${self.amount} {self.currency} | {self.status}"


class SweepsPromotion(models.Model):
    """Free Sweeps Coin distribution events (legally required for sweepstakes model).

    Every SC distribution must be logged for compliance.
    """
    PROMO_TYPES = [
        ('daily_login', 'Daily Login Bonus'),
        ('mail_in', 'AMOE Mail-In'),
        ('social_media', 'Social Media Giveaway'),
        ('purchase_bonus', 'GC Purchase Bonus'),
        ('referral', 'Referral Bonus'),
        ('event', 'Special Event'),
    ]

    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='sc_promos')
    promo_type = models.CharField(max_length=20, choices=PROMO_TYPES)
    sc_awarded = models.DecimalField(max_digits=8, decimal_places=2)
    gc_purchased = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # if bundled with GC purchase

    # For AMOE tracking
    amoe_reference = models.CharField(max_length=100, blank=True, default='')  # mail tracking number

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'casino_sweeps_promo'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.player.avatar_name} | +{self.sc_awarded} SC | {self.promo_type}"
