"""
Everlight Blackjack - Models
Full in-game economy: chips, premium gems, cosmetics, avatars, ad rewards
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class PlayerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bj_profile')
    # Currencies
    chips = models.BigIntegerField(default=1000)          # Free currency
    gems = models.IntegerField(default=0)                  # Premium currency ($)
    total_chips_won = models.BigIntegerField(default=0)
    total_chips_lost = models.BigIntegerField(default=0)

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
