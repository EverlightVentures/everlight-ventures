"""
Everlight Blackjack - Views
Handles: game rendering, auth, ad rewards, shop, avatar, game API
"""
import json
import uuid
import random
import logging
import secrets
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import (
    PlayerProfile, CosmeticItem, PlayerInventory,
    GameSession, AdRewardLog, GemPackage
)

logger = logging.getLogger(__name__)

RANK_CONFIG = {
    'Bronze':   {'min_xp': 0,      'color': '#cd7f32', 'presence_bonus': 0.0},
    'Silver':   {'min_xp': 1000,   'color': '#c0c0c0', 'presence_bonus': 0.05},
    'Gold':     {'min_xp': 5000,   'color': '#ffd700', 'presence_bonus': 0.10},
    'Platinum': {'min_xp': 15000,  'color': '#e5e4e2', 'presence_bonus': 0.15},
    'Diamond':  {'min_xp': 40000,  'color': '#b9f2ff', 'presence_bonus': 0.20},
    'Legend':   {'min_xp': 100000, 'color': '#ff6b35', 'presence_bonus': 0.30},
}

FASHION_SCORES = {
    'default_suit': 1.0, 'gold_tux': 1.15, 'diamond_blazer': 1.25,
    'neon_suit': 1.20, 'royal_robe': 1.35, 'legendary_drip': 1.50,
}
AURA_SCORES = {
    'none': 1.0, 'golden_glow': 1.05, 'hologram_blue': 1.10,
    'fire_aura': 1.15, 'legend_aura': 1.25,
}

# Cosmetic items that are FREE (no purchase needed to equip)
FREE_OUTFITS = {'default_suit'}
FREE_AURAS = {'none'}
FREE_BASES = {'silhouette_1', 'silhouette_2', 'silhouette_3'}

ACHIEVEMENT_DEFS = {
    'first_win':       {'name': 'First Blood',   'desc': 'Win your first hand',           'reward': 50},
    'first_blackjack': {'name': 'Natural 21',    'desc': 'Get your first blackjack',      'reward': 200},
    'hot_streak_5':    {'name': 'On Fire',        'desc': 'Win 5 hands in a row',          'reward': 500},
    'hot_streak_10':   {'name': 'Unstoppable',   'desc': 'Win 10 hands in a row',         'reward': 2000},
    'centurion':       {'name': 'Centurion',     'desc': 'Play 100 hands',                'reward': 1000},
    'big_winner':      {'name': 'High Roller',   'desc': 'Win 10,000+ chips in one hand', 'reward': 0},
    'gold_rank':       {'name': 'Going for Gold','desc': 'Reach Gold rank',               'reward': 2500},
    'diamond_rank':    {'name': 'Diamond Club',  'desc': 'Reach Diamond rank',            'reward': 10000},
    'lucky_seven':     {'name': 'Lucky Seven',   'desc': 'Win 7 blackjacks total',        'reward': 777},
}

VALID_CARD_RANKS = {"A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"}
SUIT_ALIASES = {
    "spades": "spades",
    "hearts": "hearts",
    "diamonds": "diamonds",
    "clubs": "clubs",
    "♠": "spades",
    "♥": "hearts",
    "♦": "diamonds",
    "♣": "clubs",
}


def _record_business_event(event_type: str, summary: str, *, status: str = "warning", payload: dict | None = None) -> None:
    try:
        from business_os.services import record_event

        record_event(
            event_type=event_type,
            source="blackjack",
            summary=summary,
            status=status,
            priority="high" if status == "failed" else "medium",
            owner_agent="arcade_operator",
            entity_type="game",
            entity_id="blackjack",
            payload=payload or {},
        )
    except Exception:
        logger.debug("Business OS event emit skipped for %s", event_type)


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_card(card: Any) -> dict[str, str] | None:
    if not isinstance(card, dict):
        return None
    rank = str(card.get("val") or card.get("rank") or "").upper()
    suit = SUIT_ALIASES.get(str(card.get("suit") or "").lower()) or SUIT_ALIASES.get(str(card.get("suit") or ""))
    if rank not in VALID_CARD_RANKS or suit not in {"spades", "hearts", "diamonds", "clubs"}:
        return None
    return {"val": rank, "suit": suit}


def _normalize_hand(hand: Any) -> list[dict[str, str]] | None:
    if not isinstance(hand, list) or not 2 <= len(hand) <= 12:
        return None
    normalized: list[dict[str, str]] = []
    for card in hand:
        normalized_card = _normalize_card(card)
        if not normalized_card:
            return None
        normalized.append(normalized_card)
    return normalized


def _card_value(card: dict[str, str]) -> int:
    rank = card["val"]
    if rank in {"J", "Q", "K"}:
        return 10
    if rank == "A":
        return 11
    return int(rank)


def _hand_value(hand: list[dict[str, str]]) -> int:
    total = 0
    aces = 0
    for card in hand:
        total += _card_value(card)
        if card["val"] == "A":
            aces += 1
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def _is_blackjack(hand: list[dict[str, str]]) -> bool:
    return len(hand) == 2 and _hand_value(hand) == 21


def _derive_outcome(
    declared_outcome: str,
    player_hand: list[dict[str, str]],
    dealer_hand: list[dict[str, str]],
) -> str:
    player_total = _hand_value(player_hand)
    dealer_total = _hand_value(dealer_hand)
    if declared_outcome == "surrender":
        return "surrender"
    if player_total > 21:
        return "bust"
    if _is_blackjack(player_hand):
        return "blackjack"
    if dealer_total > 21 or player_total > dealer_total:
        return "win"
    if player_total < dealer_total:
        return "loss"
    return "push"


def _check_achievements(profile, outcome, chips_delta):
    """Return list of newly unlocked achievements (dicts with id/name/desc/reward)."""
    unlocked = list(profile.achievements or [])
    new_ach = []

    checks = [
        ('first_win',       profile.hands_won == 1 and outcome in ('win', 'blackjack')),
        ('first_blackjack', profile.blackjacks == 1 and outcome == 'blackjack'),
        ('hot_streak_5',    profile.current_streak >= 5),
        ('hot_streak_10',   profile.current_streak >= 10),
        ('centurion',       profile.hands_played >= 100),
        ('big_winner',      chips_delta >= 10000),
        ('gold_rank',       profile.rank in ('Gold', 'Platinum', 'Diamond', 'Legend')),
        ('diamond_rank',    profile.rank in ('Diamond', 'Legend')),
        ('lucky_seven',     profile.blackjacks >= 7),
    ]

    for ach_id, condition in checks:
        if condition and ach_id not in unlocked:
            defn = ACHIEVEMENT_DEFS[ach_id]
            new_ach.append({'id': ach_id, 'name': defn['name'], 'desc': defn['desc'], 'reward': defn['reward']})
            unlocked.append(ach_id)

    if new_ach:
        # Award bonus chips for achievements
        bonus = sum(a['reward'] for a in new_ach)
        if bonus > 0:
            profile.chips += bonus
        profile.achievements = unlocked
        profile.save(update_fields=['achievements', 'chips'])

    return new_ach


def _get_or_create_profile(user):
    profile, _ = PlayerProfile.objects.get_or_create(user=user)
    return profile


def _calculate_presence_multiplier(profile):
    outfit_score = FASHION_SCORES.get(profile.avatar_outfit, 1.0)
    aura_score = AURA_SCORES.get(profile.avatar_aura, 1.0)
    rank_bonus = RANK_CONFIG.get(profile.rank, {}).get('presence_bonus', 0.0)
    return round(outfit_score * aura_score * (1 + rank_bonus), 3)


def _update_rank(profile):
    new_rank = 'Bronze'
    for rank_name, cfg in RANK_CONFIG.items():
        if profile.xp >= cfg['min_xp']:
            new_rank = rank_name
    profile.rank = new_rank
    profile.save(update_fields=['rank'])


# -- Auth Views --

def register_view(request):
    if request.user.is_authenticated:
        return redirect('blackjack:game')
    if request.method == 'POST':
        ct = request.content_type or ''
        if 'json' in ct:
            data = json.loads(request.body)
        else:
            data = request.POST
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        avatar_name = data.get('avatar_name', username)

        if not username or not password:
            return JsonResponse({'error': 'Username and password required'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already taken'}, status=400)

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            PlayerProfile.objects.create(
                user=user,
                avatar_name=avatar_name or username,
                chips=1000,
            )
        login(request, user)
        return JsonResponse({'success': True, 'redirect': '/blackjack/'})
    return render(request, 'blackjack/auth.html', {'mode': 'register'})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('blackjack:game')
    if request.method == 'POST':
        ct = request.content_type or ''
        if 'json' in ct:
            data = json.loads(request.body)
        else:
            data = request.POST
        username = data.get('username', '')
        password = data.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return JsonResponse({'success': True, 'redirect': '/blackjack/'})
        return JsonResponse({'error': 'Invalid credentials'}, status=401)
    return render(request, 'blackjack/auth.html', {'mode': 'login'})


def logout_view(request):
    logout(request)
    return redirect('blackjack:auth')


def oauth_callback(request):
    """Legacy stub - kept for compatibility."""
    return redirect('blackjack:auth')


def _oauth_find_or_create_user(provider, uid, email, name, avatar_url):
    """Find or create a Django user from OAuth data. Returns the user."""
    if not email:
        return None

    base_username = email.split('@')[0]

    with transaction.atomic():
        # Try to find by OAuth uid first (most reliable)
        try:
            profile = PlayerProfile.objects.get(oauth_provider=provider, oauth_uid=uid)
            user = profile.user
        except PlayerProfile.DoesNotExist:
            # Fall back to email match
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': _unique_username(base_username),
                    'first_name': name.split()[0] if name else '',
                }
            )
            profile = _get_or_create_profile(user)
            if created:
                profile.chips = 1000
                profile.avatar_name = name or base_username

        profile.oauth_provider = provider
        profile.oauth_uid = str(uid)
        if avatar_url:
            profile.avatar_url = avatar_url
        profile.save()

    return user


def _unique_username(base):
    """Return a unique username derived from base."""
    username = base[:28]
    if not User.objects.filter(username=username).exists():
        return username
    suffix = 2
    while User.objects.filter(username=f'{username}{suffix}').exists():
        suffix += 1
    return f'{username}{suffix}'


def _fetch_json(url, post_data=None, bearer_token=None):
    """Simple urllib wrapper: GET or POST, returns parsed JSON dict."""
    data = urllib.parse.urlencode(post_data).encode() if post_data else None
    req = urllib.request.Request(url, data=data)
    req.add_header('Accept', 'application/json')
    if post_data:
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    if bearer_token:
        req.add_header('Authorization', f'Bearer {bearer_token}')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.error('OAuth fetch error %s: %s', url, exc)
        return {}


# -- Google OAuth --

def google_login(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        return render(request, 'blackjack/auth.html', {
            'mode': 'login',
            'oauth_error': 'Google login is not configured yet. Please use email/password.',
        })
    state = secrets.token_urlsafe(16)
    request.session['google_oauth_state'] = state
    redirect_uri = request.build_absolute_uri('/blackjack/oauth/google/callback/')
    params = urllib.parse.urlencode({
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


def google_callback(request):
    error = request.GET.get('error')
    if error:
        logger.warning('Google OAuth error: %s', error)
        return redirect('blackjack:auth')

    state = request.GET.get('state', '')
    if state != request.session.pop('google_oauth_state', None):
        logger.warning('Google OAuth state mismatch')
        return redirect('blackjack:auth')

    code = request.GET.get('code', '')
    if not code:
        return redirect('blackjack:auth')

    redirect_uri = request.build_absolute_uri('/blackjack/oauth/google/callback/')

    # Exchange code for tokens
    token_data = _fetch_json('https://oauth2.googleapis.com/token', post_data={
        'code': code,
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    })
    access_token = token_data.get('access_token', '')
    if not access_token:
        logger.error('Google token exchange failed: %s', token_data)
        return redirect('blackjack:auth')

    # Get user info
    userinfo = _fetch_json('https://www.googleapis.com/oauth2/v3/userinfo', bearer_token=access_token)
    uid = userinfo.get('sub', '')
    email = userinfo.get('email', '')
    name = userinfo.get('name', '')
    avatar_url = userinfo.get('picture', '')

    user = _oauth_find_or_create_user('google', uid, email, name, avatar_url)
    if not user:
        return redirect('blackjack:auth')

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('blackjack:game')


# -- Facebook OAuth --

def facebook_login(request):
    if not settings.FB_OAUTH_CLIENT_ID:
        return render(request, 'blackjack/auth.html', {
            'mode': 'login',
            'oauth_error': 'Facebook login is not configured yet. Please use email/password.',
        })
    state = secrets.token_urlsafe(16)
    request.session['fb_oauth_state'] = state
    redirect_uri = request.build_absolute_uri('/blackjack/oauth/facebook/callback/')
    params = urllib.parse.urlencode({
        'client_id': settings.FB_OAUTH_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': 'email,public_profile',
        'state': state,
        'response_type': 'code',
    })
    return redirect(f'https://www.facebook.com/v18.0/dialog/oauth?{params}')


def facebook_callback(request):
    error = request.GET.get('error')
    if error:
        logger.warning('Facebook OAuth error: %s', error)
        return redirect('blackjack:auth')

    state = request.GET.get('state', '')
    if state != request.session.pop('fb_oauth_state', None):
        logger.warning('Facebook OAuth state mismatch')
        return redirect('blackjack:auth')

    code = request.GET.get('code', '')
    if not code:
        return redirect('blackjack:auth')

    redirect_uri = request.build_absolute_uri('/blackjack/oauth/facebook/callback/')

    # Exchange code for access token
    token_url = (
        f'https://graph.facebook.com/v18.0/oauth/access_token'
        f'?client_id={urllib.parse.quote(settings.FB_OAUTH_CLIENT_ID)}'
        f'&client_secret={urllib.parse.quote(settings.FB_OAUTH_CLIENT_SECRET)}'
        f'&code={urllib.parse.quote(code)}'
        f'&redirect_uri={urllib.parse.quote(redirect_uri)}'
    )
    token_data = _fetch_json(token_url)
    access_token = token_data.get('access_token', '')
    if not access_token:
        logger.error('Facebook token exchange failed: %s', token_data)
        return redirect('blackjack:auth')

    # Get user info
    me_url = (
        f'https://graph.facebook.com/v18.0/me'
        f'?fields=id,name,email,picture.type(large)'
        f'&access_token={urllib.parse.quote(access_token)}'
    )
    me = _fetch_json(me_url)
    uid = me.get('id', '')
    email = me.get('email', '')
    name = me.get('name', '')
    avatar_url = me.get('picture', {}).get('data', {}).get('url', '') if isinstance(me.get('picture'), dict) else ''

    user = _oauth_find_or_create_user('facebook', uid, email, name, avatar_url)
    if not user:
        return redirect('blackjack:auth')

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('blackjack:game')


# -- Main Game View --

def game_view(request):
    player_data = None
    if request.user.is_authenticated:
        profile = _get_or_create_profile(request.user)
        profile.last_played = timezone.now()
        profile.save(update_fields=['last_played'])
        player_data = {
            'username': request.user.username,
            'avatar': profile.get_avatar_config(),
            'chips': profile.chips,
            'gems': profile.gems,
            'rank': profile.rank,
            'xp': profile.xp,
            'win_rate': profile.win_rate,
            'hands_played': profile.hands_played,
            'refills_remaining': profile.refills_remaining,
            'presence_multiplier': _calculate_presence_multiplier(profile),
            'is_vip': profile.is_vip,
        }

    gem_packages = list(GemPackage.objects.filter(is_active=True).values(
        'name', 'gems', 'bonus_gems', 'price_usd', 'is_featured'
    ))

    return render(request, 'blackjack/game.html', {
        'player_data_json': json.dumps(player_data),
        'gem_packages_json': json.dumps(gem_packages, default=str),
        'google_ads_client': getattr(settings, 'GOOGLE_ADS_CLIENT', 'ca-pub-XXXXXXXXXXXXXXXX'),
        'google_ads_slot': getattr(settings, 'GOOGLE_ADS_SLOT_REWARD', ''),
    })


# -- Shoe Builder --

SUITS = ["spades", "hearts", "diamonds", "clubs"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]


def _build_shoe(num_decks=6, seed=None):
    """Build a shuffled shoe. Returns (card_list, seed_hex)."""
    if seed is None:
        seed = secrets.token_hex(32)
    cards = [{"val": r, "suit": s} for _ in range(num_decks) for s in SUITS for r in RANKS]
    rng = random.Random(seed)
    rng.shuffle(cards)
    return cards, seed


def _pop_card(gs):
    """Pop one card from the shoe stored on the GameSession."""
    shoe = gs.shoe_state
    if not shoe:
        # Reshuffle (should not happen in 6-deck with single hand)
        shoe, _ = _build_shoe(6)
    card = shoe.pop(0)
    gs.shoe_state = shoe
    return card


def _log_action(gs, action, card=None):
    """Append an entry to the session action log."""
    log = gs.action_log or []
    entry = {"action": action, "ts": timezone.now().isoformat()}
    if card:
        entry["card"] = card
    entry["player_value"] = _hand_value(gs.player_hand)
    entry["dealer_value"] = _hand_value(gs.dealer_hand)
    log.append(entry)
    gs.action_log = log


def _settle_hand(gs, profile, outcome):
    """Settle the hand: compute payout, update profile stats, save everything."""
    bet = gs.bet_chips
    if gs.doubled:
        bet = bet * 2
    side_bet = gs.side_bet_chips
    presence = gs.presence_multiplier

    chips_back = 0
    xp_earn = 5
    if outcome == 'blackjack':
        chips_back = int(gs.bet_chips * 2.5 * presence)  # BJ pays on original bet
        xp_earn = 20
    elif outcome == 'win':
        chips_back = int(bet * 2 * presence)
        xp_earn = 10
    elif outcome == 'push':
        chips_back = bet
        xp_earn = 3
    elif outcome == 'surrender':
        chips_back = gs.bet_chips // 2
        xp_earn = 2
    elif outcome in ('loss', 'bust'):
        chips_back = 0
        xp_earn = 2

    total_wagered = gs.bet_chips + side_bet
    if gs.doubled:
        total_wagered = gs.bet_chips * 2 + side_bet
    chips_delta = chips_back - total_wagered

    with transaction.atomic():
        profile.chips += max(chips_back, 0)
        profile.hands_played += 1
        profile.xp += xp_earn
        profile.rank_points += xp_earn

        if outcome in ('win', 'blackjack'):
            profile.hands_won += 1
            profile.current_streak = max(0, profile.current_streak) + 1
            profile.best_streak = max(profile.best_streak, profile.current_streak)
            profile.total_chips_won += max(0, chips_delta)
            if chips_delta > profile.biggest_win:
                profile.biggest_win = chips_delta
        elif outcome in ('loss', 'bust'):
            profile.hands_lost += 1
            profile.current_streak = 0
            profile.total_chips_lost += abs(min(0, chips_delta))
        elif outcome == 'push':
            profile.hands_push += 1
        if outcome == 'blackjack':
            profile.blackjacks += 1

        profile.save()

        gs.outcome = outcome
        gs.state = 'settled'
        gs.chips_delta = chips_delta
        gs.player_value = _hand_value(gs.player_hand)
        gs.dealer_value = _hand_value(gs.dealer_hand)
        gs.xp_earned = xp_earn
        gs.save()

        _update_rank(profile)

    new_achievements = _check_achievements(profile, outcome, chips_delta)

    return {
        'outcome': outcome,
        'dealer_hand': gs.dealer_hand,
        'dealer_value': gs.dealer_value,
        'player_hand': gs.player_hand,
        'player_value': gs.player_value,
        'chips': profile.chips,
        'chips_delta': chips_delta,
        'xp': profile.xp,
        'xp_earned': xp_earn,
        'rank': profile.rank,
        'win_rate': profile.win_rate,
        'streak': profile.current_streak,
        'hands_played': profile.hands_played,
        'hands_won': profile.hands_won,
        'best_streak': profile.best_streak,
        'biggest_win': profile.biggest_win,
        'achievements': new_achievements,
        'state': 'settled',
    }


def _run_dealer_and_settle(gs, profile):
    """Dealer draws to 17+, then settle."""
    gs.state = 'dealer_turn'
    while _hand_value(gs.dealer_hand) < 17:
        card = _pop_card(gs)
        gs.dealer_hand = gs.dealer_hand + [card]
        _log_action(gs, 'dealer_hit', card)

    player_val = _hand_value(gs.player_hand)
    dealer_val = _hand_value(gs.dealer_hand)

    if player_val > 21:
        outcome = 'bust'
    elif _is_blackjack(gs.player_hand):
        outcome = 'blackjack'
    elif dealer_val > 21:
        outcome = 'win'
    elif player_val > dealer_val:
        outcome = 'win'
    elif player_val < dealer_val:
        outcome = 'loss'
    else:
        outcome = 'push'

    return _settle_hand(gs, profile, outcome)


# -- Game API --

@login_required
@require_POST
def api_deal(request):
    """Server-authoritative deal: builds shoe, deals 4 cards, returns initial state."""
    profile = _get_or_create_profile(request.user)
    data = json.loads(request.body)
    bet = _coerce_int(data.get('bet', 0))
    side_bet = _coerce_int(data.get('side_bet', 0))

    if bet <= 0:
        return JsonResponse({'error': 'Invalid bet'}, status=400)
    if bet + side_bet > profile.chips:
        return JsonResponse({'error': 'Insufficient chips'}, status=400)
    if bet < 10:
        return JsonResponse({'error': 'Minimum bet is 10 chips'}, status=400)
    if bet > 50000:
        return JsonResponse({'error': 'Maximum bet is 50,000 chips'}, status=400)

    with transaction.atomic():
        profile.chips -= (bet + side_bet)
        profile.save(update_fields=['chips'])

    session_id = str(uuid.uuid4())
    presence = _calculate_presence_multiplier(profile)
    shoe, seed = _build_shoe(6)

    # Deal alternating: player, dealer, player, dealer
    p1 = shoe.pop(0)
    d1 = shoe.pop(0)
    p2 = shoe.pop(0)
    d2 = shoe.pop(0)

    player_hand = [p1, p2]
    dealer_hand = [d1, d2]

    gs = GameSession.objects.create(
        player=profile,
        session_id=session_id,
        bet_chips=bet,
        side_bet_chips=side_bet,
        presence_multiplier=presence,
        state='player_turn',
        shoe_state=shoe,
        shoe_seed=seed,
        player_hand=player_hand,
        dealer_hand=dealer_hand,
        action_log=[],
    )

    _log_action(gs, 'deal')
    gs.save(update_fields=['action_log'])

    player_val = _hand_value(player_hand)

    # Check for natural blackjack
    if _is_blackjack(player_hand):
        result = _settle_hand(gs, profile, 'blackjack')
        result['session_id'] = session_id
        result['is_blackjack'] = True
        result['presence_multiplier'] = presence
        return JsonResponse(result)

    # Hide dealer's hole card
    visible_dealer = [dealer_hand[0], {"val": "?", "suit": "?"}]

    can_double = (len(player_hand) == 2 and profile.chips >= bet)

    return JsonResponse({
        'session_id': session_id,
        'player_hand': player_hand,
        'dealer_hand': visible_dealer,
        'player_value': player_val,
        'chips_remaining': profile.chips,
        'presence_multiplier': presence,
        'state': 'player_turn',
        'can_double': can_double,
        'is_blackjack': False,
    })


@login_required
@require_POST
def api_action(request):
    """Server-authoritative game action: hit, stand, double, surrender."""
    profile = _get_or_create_profile(request.user)
    data = json.loads(request.body)
    session_id = data.get('session_id')
    action = str(data.get('action', '')).strip().lower()

    if action not in ('hit', 'stand', 'double', 'surrender'):
        return JsonResponse({'error': 'Invalid action'}, status=400)

    try:
        gs = GameSession.objects.get(session_id=session_id, player=profile)
    except GameSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    if gs.state == 'settled':
        return JsonResponse({'error': 'Session already settled'}, status=409)
    if gs.state != 'player_turn':
        return JsonResponse({'error': 'Not your turn'}, status=400)

    if action == 'hit':
        card = _pop_card(gs)
        gs.player_hand = gs.player_hand + [card]
        _log_action(gs, 'hit', card)

        player_val = _hand_value(gs.player_hand)

        # Bust
        if player_val > 21:
            result = _settle_hand(gs, profile, 'bust')
            result['card'] = card
            return JsonResponse(result)

        # Auto-stand on 21
        if player_val == 21:
            gs.save()
            result = _run_dealer_and_settle(gs, profile)
            result['card'] = card
            return JsonResponse(result)

        gs.save()
        return JsonResponse({
            'card': card,
            'player_hand': gs.player_hand,
            'player_value': player_val,
            'state': 'player_turn',
            'can_double': False,  # can only double on first 2 cards
        })

    elif action == 'stand':
        _log_action(gs, 'stand')
        gs.save()
        result = _run_dealer_and_settle(gs, profile)
        return JsonResponse(result)

    elif action == 'double':
        if len(gs.player_hand) != 2:
            return JsonResponse({'error': 'Can only double on first two cards'}, status=400)
        if profile.chips < gs.bet_chips:
            return JsonResponse({'error': 'Insufficient chips to double'}, status=400)

        # Deduct extra bet
        with transaction.atomic():
            profile.chips -= gs.bet_chips
            profile.save(update_fields=['chips'])

        gs.doubled = True
        card = _pop_card(gs)
        gs.player_hand = gs.player_hand + [card]
        _log_action(gs, 'double', card)

        player_val = _hand_value(gs.player_hand)

        # Bust on double
        if player_val > 21:
            result = _settle_hand(gs, profile, 'bust')
            result['card'] = card
            return JsonResponse(result)

        # Auto-stand after double (one card only)
        gs.save()
        result = _run_dealer_and_settle(gs, profile)
        result['card'] = card
        return JsonResponse(result)

    elif action == 'surrender':
        if len(gs.player_hand) != 2:
            return JsonResponse({'error': 'Can only surrender on first two cards'}, status=400)
        _log_action(gs, 'surrender')
        result = _settle_hand(gs, profile, 'surrender')
        return JsonResponse(result)

    return JsonResponse({'error': 'Unknown action'}, status=400)


@login_required
@require_POST
def api_result(request):
    """Deprecated: settlement is now server-authoritative via api_action."""
    return JsonResponse(
        {'error': 'Settlement is now server-authoritative. Use /blackjack/api/action/ for gameplay.'},
        status=400,
    )


@login_required
@require_GET
def api_profile(request):
    profile = _get_or_create_profile(request.user)
    owned_ids = list(
        PlayerInventory.objects.filter(player=profile).values_list('item__item_id', flat=True)
    )
    return JsonResponse({
        'username': request.user.username,
        'chips': profile.chips,
        'gems': profile.gems,
        'rank': profile.rank,
        'xp': profile.xp,
        'avatar': profile.get_avatar_config(),
        'win_rate': profile.win_rate,
        'hands_played': profile.hands_played,
        'hands_won': profile.hands_won,
        'hands_lost': profile.hands_lost,
        'hands_push': profile.hands_push,
        'blackjacks': profile.blackjacks,
        'biggest_win': profile.biggest_win,
        'best_streak': profile.best_streak,
        'current_streak': profile.current_streak,
        'total_chips_won': profile.total_chips_won,
        'refills_remaining': profile.refills_remaining,
        'presence_multiplier': _calculate_presence_multiplier(profile),
        'is_vip': profile.is_vip,
        'achievements': profile.achievements or [],
        'owned_items': owned_ids,
    })


@login_required
@require_POST
def api_ad_reward(request):
    """
    Called after rewarded ad completes.
    Awards 100 chips, max 10x per day per account, server-side enforced.
    """
    profile = _get_or_create_profile(request.user)
    today = timezone.now().date()
    data = json.loads(request.body)
    ad_unit_id = data.get('ad_unit_id', '')

    if profile.ad_refill_date != today:
        profile.ad_refills_today = 0
        profile.ad_refill_date = today

    if profile.ad_refills_today >= 10:
        return JsonResponse(
            {'error': 'Daily ad limit reached (10/day)', 'refills_remaining': 0},
            status=429
        )

    with transaction.atomic():
        profile.chips += 100
        profile.ad_refills_today += 1
        profile.ad_refill_date = today
        profile.save(update_fields=['chips', 'ad_refills_today', 'ad_refill_date'])

        AdRewardLog.objects.create(
            player=profile,
            reward_date=today,
            chips_awarded=100,
            ad_unit_id=ad_unit_id,
        )

    return JsonResponse({
        'chips_awarded': 100,
        'chips': profile.chips,
        'refills_remaining': profile.refills_remaining,
    })


@login_required
@require_POST
def api_update_avatar(request):
    profile = _get_or_create_profile(request.user)
    data = json.loads(request.body)

    # Enforce ownership: premium items must be purchased before equipping
    outfit = data.get('avatar_outfit', '')
    if outfit and outfit not in FREE_OUTFITS:
        if not PlayerInventory.objects.filter(player=profile, item__item_id=outfit).exists():
            return JsonResponse({'error': f'Purchase required: {outfit}', 'purchase_required': outfit}, status=403)

    aura = data.get('avatar_aura', '')
    if aura and aura not in FREE_AURAS:
        if not PlayerInventory.objects.filter(player=profile, item__item_id=aura).exists():
            return JsonResponse({'error': f'Purchase required: {aura}', 'purchase_required': aura}, status=403)

    allowed_fields = [
        'avatar_name', 'avatar_base', 'avatar_outfit', 'avatar_accessory',
        'avatar_hat', 'avatar_aura', 'avatar_title',
        'avatar_color_primary', 'avatar_color_secondary',
    ]

    update_fields = []
    for field in allowed_fields:
        if field in data:
            setattr(profile, field, str(data[field])[:60])
            update_fields.append(field)

    if update_fields:
        profile.save(update_fields=update_fields)

    return JsonResponse({
        'success': True,
        'avatar': profile.get_avatar_config(),
        'presence_multiplier': _calculate_presence_multiplier(profile),
    })


@login_required
@require_POST
def api_purchase_cosmetic(request):
    profile = _get_or_create_profile(request.user)
    data = json.loads(request.body)
    item_id = data.get('item_id')
    currency = data.get('currency', 'chips')

    try:
        item = CosmeticItem.objects.get(item_id=item_id, is_active=True)
    except CosmeticItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)

    if PlayerInventory.objects.filter(player=profile, item=item).exists():
        return JsonResponse({'error': 'Already owned'}, status=400)

    rank_order = list(RANK_CONFIG.keys())
    if rank_order.index(profile.rank) < rank_order.index(item.rank_required):
        return JsonResponse({'error': f'Requires {item.rank_required} rank'}, status=403)

    with transaction.atomic():
        if currency == 'chips':
            if item.price_chips == 0:
                return JsonResponse({'error': 'Not available for chips'}, status=400)
            if profile.chips < item.price_chips:
                return JsonResponse({'error': 'Insufficient chips'}, status=402)
            profile.chips -= item.price_chips
            profile.save(update_fields=['chips'])
        elif currency == 'gems':
            if item.price_gems == 0:
                return JsonResponse({'error': 'Not available for gems'}, status=400)
            if profile.gems < item.price_gems:
                return JsonResponse({'error': 'Insufficient gems'}, status=402)
            profile.gems -= item.price_gems
            profile.save(update_fields=['gems'])
        else:
            return JsonResponse({'error': 'Invalid currency'}, status=400)

        PlayerInventory.objects.create(
            player=profile, item=item, acquisition_method='purchase'
        )

    return JsonResponse({'success': True, 'chips': profile.chips, 'gems': profile.gems, 'item_id': item_id})


def api_shop_items(request):
    items = CosmeticItem.objects.filter(is_active=True).values(
        'item_id', 'name', 'category', 'rarity', 'description',
        'price_chips', 'price_gems', 'price_usd', 'rank_required',
        'is_vip_only', 'is_limited', 'visual_config',
    )
    owned_ids = []
    if request.user.is_authenticated:
        profile = _get_or_create_profile(request.user)
        owned_ids = list(
            PlayerInventory.objects.filter(player=profile).values_list('item__item_id', flat=True)
        )
    return JsonResponse({'items': list(items), 'owned': owned_ids})


@login_required
@require_GET
def api_history(request):
    profile = _get_or_create_profile(request.user)
    sessions = GameSession.objects.filter(player=profile, outcome__gt='').order_by('-played_at')[:20]
    rows = []
    for gs in sessions:
        rows.append({
            'outcome': gs.outcome,
            'bet': gs.bet_chips,
            'chips_delta': gs.chips_delta,
            'xp_earned': gs.xp_earned,
            'player_value': gs.player_value,
            'dealer_value': gs.dealer_value,
            'played_at': gs.played_at.strftime('%b %d %I:%M %p'),
        })
    return JsonResponse({'history': rows})


def api_leaderboard(request):
    top = PlayerProfile.objects.order_by('-total_chips_won')[:10]
    rows = []
    for i, p in enumerate(top, 1):
        rows.append({
            'position': i,
            'name': p.avatar_name,
            'rank': p.rank,
            'chips_won': p.total_chips_won,
            'win_rate': p.win_rate,
            'hands_played': p.hands_played,
        })
    return JsonResponse({'leaderboard': rows})
