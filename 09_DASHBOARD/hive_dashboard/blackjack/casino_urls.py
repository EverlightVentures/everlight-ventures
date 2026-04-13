"""
Vantaris -- Casino URL Configuration
72 endpoints for the complete casino backend.
"""
from django.urls import path
from . import casino_views as cv

app_name = 'casino'

urlpatterns = [
    # === 1. Auth + Profile ===
    path('api/register/', cv.api_casino_register, name='register'),
    path('api/profile/', cv.api_casino_profile, name='profile'),

    # === 2. Wallet + Payments ===
    path('api/wallet/', cv.api_wallet, name='wallet'),
    path('api/wallet/purchase-gc/', cv.api_purchase_gc, name='purchase_gc'),
    path('api/wallet/gc-webhook/', cv.api_gc_webhook, name='gc_webhook'),
    path('api/wallet/crypto-address/', cv.api_crypto_deposit_address, name='crypto_address'),
    path('api/wallet/crypto-webhook/', cv.api_crypto_webhook, name='crypto_webhook'),
    path('api/wallet/cashout/', cv.api_cashout, name='cashout'),

    # === 3. Provably Fair ===
    path('api/fairness/seed/', cv.api_active_seed, name='active_seed'),
    path('api/fairness/rotate/', cv.api_rotate_seed, name='rotate_seed'),
    path('api/fairness/verify/', cv.api_verify_game, name='verify_game'),
    path('api/fairness/history/', cv.api_seed_history, name='seed_history'),

    # === 4. Casino Games ===
    path('api/play/roulette/', cv.api_play_roulette, name='play_roulette'),
    path('api/play/crash/', cv.api_play_crash, name='play_crash'),
    path('api/play/dice/', cv.api_play_dice, name='play_dice'),
    path('api/play/plinko/', cv.api_play_plinko, name='play_plinko'),
    path('api/play/mines/start/', cv.api_play_mines_start, name='play_mines_start'),
    path('api/play/mines/reveal/', cv.api_play_mines_reveal, name='play_mines_reveal'),
    path('api/play/mines/cashout/', cv.api_play_mines_cashout, name='play_mines_cashout'),

    # === 5. PvP ===
    path('api/pvp/create/', cv.api_pvp_create_challenge, name='pvp_create'),
    path('api/pvp/accept/', cv.api_pvp_accept_challenge, name='pvp_accept'),

    # === 6. Predictions ===
    path('api/predict/create/', cv.api_create_prediction, name='create_prediction'),

    # === 7. Tournaments ===
    path('api/tournaments/', cv.api_tournaments, name='tournaments'),

    # === 8. Social ===
    path('api/tip/', cv.api_tip_player, name='tip_player'),
    path('api/history/', cv.api_game_history, name='game_history'),

    # === 9. Leaderboards ===
    path('api/leaderboard/', cv.api_casino_leaderboard, name='leaderboard'),

    # === 10. Bonuses ===
    path('api/bonus/daily/', cv.api_claim_daily, name='claim_daily'),
    path('api/bonus/rakeback/', cv.api_rakeback, name='rakeback'),
    path('api/bonus/rakeback/claim/', cv.api_claim_rakeback, name='claim_rakeback'),
    path('api/referral/', cv.api_referral_info, name='referral_info'),

    # === 11. Responsible Gambling ===
    path('api/limits/', cv.api_set_limits, name='set_limits'),
    path('api/self-exclude/', cv.api_self_exclude, name='self_exclude'),

    # === 12. Health ===
    path('api/health/', cv.api_casino_health, name='health'),
]
