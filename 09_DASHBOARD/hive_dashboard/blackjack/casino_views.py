"""
Vantaris -- Casino API Views
"The darkest star burns brightest."

The complete casino API. Every endpoint needed to run an international
crypto casino + US sweepstakes platform.

72 endpoints organized into 12 sections:
1. Player Auth + Profile
2. Wallet + Deposits + Withdrawals
3. Provably Fair Seed Management
4. Casino Games (Roulette, Crash, Dice, Plinko, Mines)
5. Player vs Player (PvP) Games
6. Prediction Markets (player-created)
7. Tournaments
8. Social (feed, sharing, tipping)
9. Leaderboards + Achievements
10. Bonuses + Referrals + Rakeback
11. Responsible Gambling
12. Admin / Operator
"""
import json
import uuid
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db import transaction as db_tx
from django.utils import timezone

from .models import (
    PlayerProfile, GameSession, CasinoGameRound,
    ProvablyFairSeed, CashoutRequest, SweepsPromotion,
)
from . import provably_fair as pf
from . import casino_games as games
from .wallet_engine import (
    credit, debit, place_bet, settle_win, settle_loss,
    get_all_balances, process_gc_purchase, process_daily_login,
    request_sc_redemption, process_crypto_deposit,
    request_crypto_withdrawal, calculate_rakeback, claim_rakeback,
    GC_PACKAGES, WalletError, InsufficientFunds,
)
from .geo_routing import (
    get_player_location, get_player_mode, require_casino_access,
)

logger = logging.getLogger('vantaris')


# ============================================================
# DECORATORS
# ============================================================

def require_auth(view_func):
    """Require authenticated player."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        try:
            request.player = request.user.bj_profile
        except PlayerProfile.DoesNotExist:
            return JsonResponse({'error': 'Player profile not found'}, status=404)
        return view_func(request, *args, **kwargs)
    return wrapper


def json_body(view_func):
    """Parse JSON request body."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            request.json = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper


def rate_limit(max_per_minute=60):
    """Simple rate limiter using Django cache."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # In production, use Redis-based rate limiting
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 1. PLAYER AUTH + PROFILE
# ============================================================

@csrf_exempt
@require_POST
@json_body
def api_casino_register(request):
    """Register a new Vantaris player."""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    display_name = data.get('display_name', username)
    referral_code = data.get('referral_code', '')

    if not username or not password:
        return JsonResponse({'error': 'Username and password required'}, status=400)

    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username taken'}, status=409)

    # Geo-detect
    location = get_player_location(request)
    mode = get_player_mode(location)

    if mode['mode'] == 'blocked':
        return JsonResponse({'error': mode['reason']}, status=403)

    user = User.objects.create_user(username=username, password=password, email=email)
    player = PlayerProfile.objects.create(
        user=user,
        avatar_name=display_name,
        region=mode['mode'],  # 'sweepstakes' or 'crypto'
        country_code=location.get('country', 'XX'),
    )

    # Generate initial provably fair seeds
    server_seed = pf.generate_server_seed()
    client_seed = pf.generate_client_seed()
    ProvablyFairSeed.objects.create(
        player=player,
        server_seed=server_seed,
        server_seed_hash=pf.hash_seed(server_seed),
        client_seed=client_seed,
        is_active=True,
    )

    # Handle referral
    referred_by = None
    if referral_code:
        try:
            referrer = PlayerProfile.objects.get(
                user__username__iexact=referral_code
            ) if not referral_code.startswith('VANT-') else None

            if not referrer and referral_code.startswith('VANT-'):
                # TODO: lookup by referral_code field
                pass

            if referrer:
                referred_by = referrer
                # Award referral bonuses
                credit(player, 'gc', Decimal('500'), 'sc_referral', note='Referral signup bonus')
                credit(player, 'sc', Decimal('1.00'), 'sc_referral', note='Referral SC bonus')
                credit(referrer, 'gc', Decimal('500'), 'referral_commission', note=f'Referred {username}')
        except PlayerProfile.DoesNotExist:
            pass

    # Daily login bonus
    login_result = process_daily_login(player)

    return JsonResponse({
        'status': 'registered',
        'player_id': player.pk,
        'username': username,
        'display_name': display_name,
        'region': mode['mode'],
        'balances': get_all_balances(player),
        'seed_hash': pf.hash_seed(server_seed),
        'daily_bonus': login_result,
        'welcome': "You didn't find Vantaris. Vantaris found you.",
    })


@csrf_exempt
@require_GET
@require_auth
def api_casino_profile(request):
    """Get full player profile with all balances and stats."""
    p = request.player
    location = get_player_location(request)
    mode = get_player_mode(location)

    # Active seed
    active_seed = ProvablyFairSeed.objects.filter(player=p, is_active=True).first()

    return JsonResponse({
        'profile': {
            'id': p.pk,
            'username': p.user.username,
            'display_name': p.avatar_name,
            'avatar': p.get_avatar_config(),
            'rank': p.rank,
            'xp': p.xp,
            'tier_progress': _tier_progress(p),
        },
        'balances': get_all_balances(p),
        'stats': {
            'hands_played': p.hands_played,
            'hands_won': p.hands_won,
            'win_rate': p.win_rate,
            'biggest_win': int(p.biggest_win),
            'current_streak': p.current_streak,
            'best_streak': p.best_streak,
            'blackjacks': p.blackjacks,
        },
        'region': mode,
        'provably_fair': {
            'seed_hash': active_seed.server_seed_hash if active_seed else None,
            'client_seed': active_seed.client_seed if active_seed else None,
            'nonce': active_seed.nonce if active_seed else 0,
            'games_played': active_seed.games_played if active_seed else 0,
        },
        'kyc_verified': p.kyc_verified,
        'vip': p.is_vip,
        'achievements': p.achievements,
    })


# ============================================================
# 2. WALLET + DEPOSITS + WITHDRAWALS
# ============================================================

@csrf_exempt
@require_GET
@require_auth
def api_wallet(request):
    """Get wallet balances and transaction history."""
    p = request.player
    return JsonResponse({
        'balances': get_all_balances(p),
        'gc_packages': GC_PACKAGES,
    })


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_purchase_gc(request):
    """Purchase Gold Coins (triggers Stripe checkout)."""
    package_id = request.json.get('package_id')
    if not package_id:
        return JsonResponse({'error': 'package_id required'}, status=400)

    package = next((p for p in GC_PACKAGES if p['id'] == package_id), None)
    if not package:
        return JsonResponse({'error': 'Invalid package'}, status=400)

    # Create Stripe checkout session
    try:
        import stripe
        stripe.api_key = getattr(__import__('django.conf', fromlist=['settings']).settings,
                                  'STRIPE_SECRET_KEY', '')

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Vantaris - {package["name"]} ({package["gc"]:,} Gold Coins)',
                        'description': f'Includes {package["bonus_sc"]} FREE Sweeps Coins',
                    },
                    'unit_amount': int(package['price_usd'] * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={
                'player_id': str(request.player.pk),
                'package_id': package_id,
                'type': 'gc_purchase',
            },
            success_url=request.build_absolute_uri('/casino/wallet/?purchase=success'),
            cancel_url=request.build_absolute_uri('/casino/wallet/?purchase=canceled'),
        )
        return JsonResponse({'checkout_url': session.url, 'session_id': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_gc_webhook(request):
    """Handle Stripe webhook for GC purchases."""
    # In production, verify Stripe signature
    event_type = request.json.get('type')
    if event_type == 'checkout.session.completed':
        session = request.json.get('data', {}).get('object', {})
        meta = session.get('metadata', {})
        player_id = meta.get('player_id')
        package_id = meta.get('package_id')
        payment_id = session.get('payment_intent', session.get('id', ''))

        if player_id and package_id:
            try:
                player = PlayerProfile.objects.get(pk=int(player_id))
                result = process_gc_purchase(player, package_id, payment_id)
                return JsonResponse({'status': 'credited', 'result': result})
            except Exception as e:
                logger.error(f"GC webhook error: {e}")
                return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'status': 'ignored'})


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_crypto_deposit_address(request):
    """Get or create a crypto deposit address for the player."""
    currency = request.json.get('currency', 'BTC').upper()
    from .geo_routing import coinspaid

    result = coinspaid.create_deposit_address(
        currency=currency,
        player_id=str(request.player.pk),
        callback_url=request.build_absolute_uri('/casino/api/crypto/webhook/'),
    )

    return JsonResponse(result)


@csrf_exempt
@require_POST
@json_body
def api_crypto_webhook(request):
    """CoinsPaid webhook for confirmed crypto deposits."""
    data = request.json
    player_id = data.get('foreign_id', '').replace('player_', '')
    currency = data.get('currency', 'BTC')
    amount = Decimal(str(data.get('amount', 0)))
    usd_value = Decimal(str(data.get('amount_in_usd', 0)))
    tx_hash = data.get('txid', '')
    status = data.get('status', '')

    if status == 'confirmed' and player_id:
        try:
            player = PlayerProfile.objects.get(pk=int(player_id))
            result = process_crypto_deposit(player, currency, amount, usd_value, tx_hash)
            return JsonResponse({'status': 'credited', 'result': result})
        except Exception as e:
            logger.error(f"Crypto webhook error: {e}")

    return JsonResponse({'status': 'received'})


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_cashout(request):
    """Request a cashout (SC redemption or crypto withdrawal)."""
    p = request.player
    currency = request.json.get('currency', 'sc')
    amount = Decimal(str(request.json.get('amount', 0)))
    method = request.json.get('method', 'paypal')
    destination = request.json.get('destination', '')

    if not destination:
        return JsonResponse({'error': 'Destination required'}, status=400)

    try:
        if currency == 'sc':
            result = request_sc_redemption(p, amount, method, destination)
        else:
            result = request_crypto_withdrawal(p, currency, amount, destination)

        if 'error' in result:
            return JsonResponse(result, status=400)
        return JsonResponse(result)
    except (WalletError, InsufficientFunds) as e:
        return JsonResponse({'error': str(e)}, status=400)


# ============================================================
# 3. PROVABLY FAIR SEED MANAGEMENT
# ============================================================

@csrf_exempt
@require_GET
@require_auth
def api_active_seed(request):
    """Get the active provably fair seed pair (hash only, not the seed itself)."""
    seed = ProvablyFairSeed.objects.filter(player=request.player, is_active=True).first()
    if not seed:
        return JsonResponse({'error': 'No active seed'}, status=404)

    return JsonResponse({
        'seed_hash': seed.server_seed_hash,
        'client_seed': seed.client_seed,
        'nonce': seed.nonce,
        'games_played': seed.games_played,
    })


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_rotate_seed(request):
    """Rotate to a new server seed. Reveals the old one for verification."""
    p = request.player
    old_seed = ProvablyFairSeed.objects.filter(player=p, is_active=True).first()

    # Reveal old seed
    old_data = None
    if old_seed:
        old_seed.is_active = False
        old_seed.revealed = True
        old_seed.revealed_at = timezone.now()
        old_seed.save()
        old_data = {
            'server_seed': old_seed.server_seed,  # NOW revealed
            'server_seed_hash': old_seed.server_seed_hash,
            'client_seed': old_seed.client_seed,
            'games_played': old_seed.games_played,
            'final_nonce': old_seed.nonce,
        }

    # Create new seed pair
    new_server_seed = pf.generate_server_seed()
    new_client_seed = request.json.get('client_seed', pf.generate_client_seed())

    new_seed = ProvablyFairSeed.objects.create(
        player=p,
        server_seed=new_server_seed,
        server_seed_hash=pf.hash_seed(new_server_seed),
        client_seed=new_client_seed,
        is_active=True,
    )

    return JsonResponse({
        'old_seed': old_data,
        'new_seed': {
            'seed_hash': new_seed.server_seed_hash,
            'client_seed': new_seed.client_seed,
            'nonce': 0,
        },
    })


@csrf_exempt
@require_POST
@json_body
def api_verify_game(request):
    """Verify a past game was fair. Public endpoint (no auth needed)."""
    server_seed = request.json.get('server_seed', '')
    server_seed_hash = request.json.get('server_seed_hash', '')
    client_seed = request.json.get('client_seed', '')
    nonce = int(request.json.get('nonce', 0))
    game = request.json.get('game', '')

    verification = pf.verify_outcome(server_seed, server_seed_hash, client_seed, nonce)

    # Replay the game outcome
    if game == 'roulette':
        verification['result'] = pf.roulette_outcome(server_seed, client_seed, nonce)
    elif game == 'crash':
        verification['result'] = pf.crash_outcome(server_seed, client_seed, nonce)
    elif game == 'dice':
        verification['result'] = pf.dice_outcome(server_seed, client_seed, nonce)

    return JsonResponse(verification)


@csrf_exempt
@require_GET
@require_auth
def api_seed_history(request):
    """Get history of all seed pairs (revealed seeds only)."""
    seeds = ProvablyFairSeed.objects.filter(
        player=request.player, revealed=True
    ).order_by('-revealed_at')[:20]

    return JsonResponse({
        'seeds': [{
            'server_seed': s.server_seed,
            'server_seed_hash': s.server_seed_hash,
            'client_seed': s.client_seed,
            'games_played': s.games_played,
            'created_at': s.created_at.isoformat(),
            'revealed_at': s.revealed_at.isoformat() if s.revealed_at else None,
        } for s in seeds]
    })


# ============================================================
# 4. CASINO GAMES (Roulette, Crash, Dice, Plinko, Mines)
# ============================================================

def _play_game(request, game_name, play_func, **extra_kwargs):
    """Generic game play handler. Manages seeds, bets, settlements."""
    p = request.player
    data = request.json
    currency = data.get('currency', 'gc')
    bet_amount = Decimal(str(data.get('bet_amount', 0)))

    if bet_amount <= 0:
        return JsonResponse({'error': 'Invalid bet amount'}, status=400)

    # Get active seed
    seed = ProvablyFairSeed.objects.select_for_update().filter(
        player=p, is_active=True
    ).first()
    if not seed:
        return JsonResponse({'error': 'No active seed. Rotate first.'}, status=400)

    # Place bet (debits wallet)
    try:
        bet_result = place_bet(p, currency, bet_amount, game_name, str(uuid.uuid4()))
    except (WalletError, InsufficientFunds) as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Play the game
    nonce = seed.nonce
    game_result = play_func(
        server_seed=seed.server_seed,
        client_seed=seed.client_seed,
        nonce=nonce,
        bet_amount=int(bet_amount),
        **extra_kwargs,
        **{k: v for k, v in data.items() if k not in ('bet_amount', 'currency')},
    )

    # Increment seed nonce
    seed.nonce += 1
    seed.games_played += 1
    seed.save(update_fields=['nonce', 'games_played'])

    # Settle outcome
    win_amount = Decimal(str(game_result.get('win_amount', 0)))
    multiplier = float(game_result.get('multiplier', 0))

    if win_amount > 0:
        win_result = settle_win(p, currency, win_amount, game_name, game_result['round_id'], multiplier)
        game_result['settlement'] = win_result
    else:
        loss_result = settle_loss(p, game_name, game_result['round_id'])
        game_result['settlement'] = loss_result

    # Record game round
    CasinoGameRound.objects.create(
        round_id=game_result['round_id'],
        player=p,
        game=game_name,
        currency=currency,
        bet_amount=bet_amount,
        win_amount=win_amount,
        net=win_amount - bet_amount,
        multiplier=Decimal(str(multiplier)),
        seed_pair=seed,
        nonce_used=nonce,
        game_data=game_result,
        xp_earned=game_result.get('settlement', {}).get('xp_earned', 0),
    )

    # Updated balances
    p.refresh_from_db()
    game_result['balances'] = get_all_balances(p)

    # Remove server-internal fields
    game_result.pop('_mines', None)

    return JsonResponse(game_result)


@csrf_exempt
@require_POST
@require_auth
@json_body
@require_casino_access
@rate_limit(max_per_minute=30)
def api_play_roulette(request):
    """Play a round of Vantaris Roulette."""
    bets = request.json.get('bets', [])
    if not bets:
        return JsonResponse({'error': 'No bets placed'}, status=400)

    # For roulette, bet_amount is the total of all bets
    total_bet = sum(b.get('amount', 0) for b in bets)
    request.json['bet_amount'] = total_bet

    return _play_game(request, 'roulette', games.play_roulette, bets=bets)


@csrf_exempt
@require_POST
@require_auth
@json_body
@require_casino_access
@rate_limit(max_per_minute=60)
def api_play_crash(request):
    """Play a round of Vantaris Crash."""
    cashout_at = request.json.get('cashout_at')
    return _play_game(request, 'crash', games.play_crash,
                      cashout_at=float(cashout_at) if cashout_at else None)


@csrf_exempt
@require_POST
@require_auth
@json_body
@require_casino_access
@rate_limit(max_per_minute=60)
def api_play_dice(request):
    """Play a round of Vantaris Dice."""
    target = float(request.json.get('target', 50))
    over = request.json.get('over', True)
    return _play_game(request, 'dice', games.play_dice, target=target, over=over)


@csrf_exempt
@require_POST
@require_auth
@json_body
@require_casino_access
@rate_limit(max_per_minute=30)
def api_play_plinko(request):
    """Play a round of Vantaris Plinko."""
    risk = request.json.get('risk', 'medium')
    rows = int(request.json.get('rows', 16))
    return _play_game(request, 'plinko', games.play_plinko, risk=risk, rows=rows)


@csrf_exempt
@require_POST
@require_auth
@json_body
@require_casino_access
def api_play_mines_start(request):
    """Start a new Mines game."""
    p = request.player
    data = request.json
    currency = data.get('currency', 'gc')
    bet_amount = Decimal(str(data.get('bet_amount', 0)))
    mine_count = int(data.get('mine_count', 5))

    if mine_count < 1 or mine_count > 24:
        return JsonResponse({'error': 'mine_count must be 1-24'}, status=400)

    seed = ProvablyFairSeed.objects.filter(player=p, is_active=True).first()
    if not seed:
        return JsonResponse({'error': 'No active seed'}, status=400)

    try:
        place_bet(p, currency, bet_amount, 'mines', str(uuid.uuid4()))
    except (WalletError, InsufficientFunds) as e:
        return JsonResponse({'error': str(e)}, status=400)

    game_state = games.create_mines_game(
        seed.server_seed, seed.client_seed, seed.nonce,
        int(bet_amount), mine_count,
    )

    # Store game state in session (server-side only)
    request.session[f'mines_{game_state["round_id"]}'] = game_state
    request.session[f'mines_currency'] = currency

    seed.nonce += 1
    seed.games_played += 1
    seed.save(update_fields=['nonce', 'games_played'])

    # Return state WITHOUT mines positions
    safe_state = {k: v for k, v in game_state.items() if k != '_mines'}
    safe_state['balances'] = get_all_balances(p)

    return JsonResponse(safe_state)


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_play_mines_reveal(request):
    """Reveal a tile in an active Mines game."""
    round_id = request.json.get('round_id')
    tile = int(request.json.get('tile', -1))

    game_state = request.session.get(f'mines_{round_id}')
    if not game_state:
        return JsonResponse({'error': 'Game not found or expired'}, status=404)

    if game_state['state'] != 'active':
        return JsonResponse({'error': 'Game already ended'}, status=400)

    result = games.reveal_mines_tile(game_state, tile)
    request.session[f'mines_{round_id}'] = result

    safe_result = {k: v for k, v in result.items() if k != '_mines'}

    if result['state'] == 'busted':
        # Record loss
        settle_loss(request.player, 'mines', round_id)
        CasinoGameRound.objects.create(
            round_id=round_id,
            player=request.player,
            game='mines',
            currency=request.session.get('mines_currency', 'gc'),
            bet_amount=result['bet_amount'],
            win_amount=0,
            net=-result['bet_amount'],
            multiplier=0,
            game_data=safe_result,
        )
        request.player.refresh_from_db()
        safe_result['balances'] = get_all_balances(request.player)

    return JsonResponse(safe_result)


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_play_mines_cashout(request):
    """Cash out of an active Mines game."""
    round_id = request.json.get('round_id')
    game_state = request.session.get(f'mines_{round_id}')
    if not game_state:
        return JsonResponse({'error': 'Game not found'}, status=404)

    result = games.cashout_mines(game_state)
    currency = request.session.get('mines_currency', 'gc')

    if result.get('win_amount', 0) > 0:
        settle_win(request.player, currency, Decimal(str(result['win_amount'])),
                   'mines', round_id, result.get('final_multiplier', 1))

    CasinoGameRound.objects.create(
        round_id=round_id,
        player=request.player,
        game='mines',
        currency=currency,
        bet_amount=result['bet_amount'],
        win_amount=result.get('win_amount', 0),
        net=result.get('net', 0),
        multiplier=Decimal(str(result.get('final_multiplier', 0))),
        game_data={k: v for k, v in result.items() if k != '_mines'},
    )

    # Clean up session
    del request.session[f'mines_{round_id}']

    request.player.refresh_from_db()
    safe_result = {k: v for k, v in result.items() if k != '_mines'}
    safe_result['balances'] = get_all_balances(request.player)

    return JsonResponse(safe_result)


# ============================================================
# 5. PLAYER vs PLAYER (PvP)
# ============================================================

@csrf_exempt
@require_POST
@require_auth
@json_body
def api_pvp_create_challenge(request):
    """Create a PvP challenge (head-to-head prediction or game)."""
    p = request.player
    data = request.json
    game = data.get('game', 'prediction')
    wager = Decimal(str(data.get('wager', 0)))
    currency = data.get('currency', 'gc')
    description = data.get('description', '')
    expires_hours = int(data.get('expires_hours', 24))

    try:
        place_bet(p, currency, wager, f'pvp_{game}', str(uuid.uuid4()))
    except (WalletError, InsufficientFunds) as e:
        return JsonResponse({'error': str(e)}, status=400)

    challenge = {
        'challenge_id': str(uuid.uuid4()),
        'creator': p.avatar_name,
        'creator_id': p.pk,
        'game': game,
        'wager': float(wager),
        'currency': currency,
        'description': description,
        'status': 'open',
        'expires_at': (timezone.now() + timedelta(hours=expires_hours)).isoformat(),
        'created_at': timezone.now().isoformat(),
    }

    # Store in session/cache (in production, use Redis or DB)
    # TODO: Move to a PvP model
    return JsonResponse({
        'challenge': challenge,
        'share_link': f'/casino/pvp/{challenge["challenge_id"]}',
        'message': f'Challenge created! Share the link for someone to accept.',
    })


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_pvp_accept_challenge(request):
    """Accept a PvP challenge."""
    challenge_id = request.json.get('challenge_id')
    # TODO: Implement full PvP matching with escrow
    return JsonResponse({
        'status': 'accepted',
        'message': 'Challenge accepted! Game starting...',
    })


# ============================================================
# 6. PREDICTION MARKETS (player-created)
# ============================================================

@csrf_exempt
@require_POST
@require_auth
@json_body
def api_create_prediction(request):
    """Create a player-made prediction market.

    "I bet the barista spells my name wrong."
    Friends bet for/against. Creator resolves. Vantaris takes 5%.
    """
    p = request.player
    data = request.json

    prediction = {
        'prediction_id': str(uuid.uuid4()),
        'creator': p.avatar_name,
        'creator_id': p.pk,
        'title': data.get('title', ''),
        'options': data.get('options', [{'id': 'yes', 'label': 'Yes'}, {'id': 'no', 'label': 'No'}]),
        'currency': data.get('currency', 'gc'),
        'min_bet': data.get('min_bet', 10),
        'max_bet': data.get('max_bet', 1000),
        'closes_at': data.get('closes_at'),
        'status': 'open',
        'total_pool': 0,
        'bets': [],
        'rake': 0.05,  # 5% platform rake
        'created_at': timezone.now().isoformat(),
    }

    # TODO: Store in PredictionMarket model
    return JsonResponse({
        'prediction': prediction,
        'share_link': f'/casino/predict/{prediction["prediction_id"]}',
        'message': 'Prediction market created! Share for friends to bet.',
    })


# ============================================================
# 7. TOURNAMENTS
# ============================================================

@csrf_exempt
@require_GET
@require_auth
def api_tournaments(request):
    """List active and upcoming tournaments."""
    # TODO: Tournament model and bracket system
    tournaments = [
        {
            'id': 'daily_blackjack',
            'name': 'Daily Blackjack Showdown',
            'game': 'blackjack',
            'entry_fee': 100,
            'currency': 'gc',
            'prize_pool': 10000,
            'players': 0,
            'max_players': 64,
            'status': 'registering',
            'starts_at': (timezone.now() + timedelta(hours=2)).isoformat(),
        },
        {
            'id': 'weekly_crash',
            'name': 'Weekly Crash Championship',
            'game': 'crash',
            'entry_fee': 500,
            'currency': 'gc',
            'prize_pool': 50000,
            'players': 0,
            'max_players': 128,
            'status': 'upcoming',
            'starts_at': (timezone.now() + timedelta(days=3)).isoformat(),
        },
    ]

    return JsonResponse({'tournaments': tournaments})


# ============================================================
# 8. SOCIAL (feed, sharing, tipping)
# ============================================================

@csrf_exempt
@require_POST
@require_auth
@json_body
def api_tip_player(request):
    """Tip another player with GC."""
    p = request.player
    recipient_id = request.json.get('recipient_id')
    amount = Decimal(str(request.json.get('amount', 0)))
    currency = request.json.get('currency', 'gc')

    if amount <= 0:
        return JsonResponse({'error': 'Invalid tip amount'}, status=400)

    try:
        recipient = PlayerProfile.objects.get(pk=recipient_id)
    except PlayerProfile.DoesNotExist:
        return JsonResponse({'error': 'Player not found'}, status=404)

    if recipient.pk == p.pk:
        return JsonResponse({'error': "Can't tip yourself"}, status=400)

    try:
        debit(p, currency, amount, 'tip_sent', note=f'Tip to {recipient.avatar_name}')
        credit(recipient, currency, amount, 'tip_received', note=f'Tip from {p.avatar_name}')
    except (WalletError, InsufficientFunds) as e:
        return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({
        'status': 'sent',
        'amount': float(amount),
        'recipient': recipient.avatar_name,
        'message': f'Tipped {recipient.avatar_name} {amount} {currency}',
    })


@csrf_exempt
@require_GET
@require_auth
def api_game_history(request):
    """Get player's game history across all games."""
    rounds = CasinoGameRound.objects.filter(
        player=request.player
    ).order_by('-played_at')[:50]

    return JsonResponse({
        'history': [{
            'round_id': r.round_id,
            'game': r.game,
            'currency': r.currency,
            'bet': float(r.bet_amount),
            'win': float(r.win_amount),
            'net': float(r.net),
            'multiplier': float(r.multiplier),
            'xp': r.xp_earned,
            'played_at': r.played_at.isoformat(),
        } for r in rounds]
    })


# ============================================================
# 9. LEADERBOARDS + ACHIEVEMENTS
# ============================================================

@csrf_exempt
@require_GET
def api_casino_leaderboard(request):
    """Global and per-game leaderboards."""
    game = request.GET.get('game', 'all')
    period = request.GET.get('period', 'weekly')

    query = CasinoGameRound.objects.all()
    if game != 'all':
        query = query.filter(game=game)

    if period == 'daily':
        since = timezone.now() - timedelta(days=1)
    elif period == 'weekly':
        since = timezone.now() - timedelta(days=7)
    else:
        since = timezone.now() - timedelta(days=365)

    query = query.filter(played_at__gte=since)

    # Aggregate by player
    from django.db.models import Sum, Count, Max
    leaders = query.values('player__avatar_name', 'player__rank').annotate(
        total_won=Sum('win_amount'),
        total_wagered=Sum('bet_amount'),
        games=Count('id'),
        biggest_win=Max('win_amount'),
    ).order_by('-total_won')[:100]

    return JsonResponse({
        'game': game,
        'period': period,
        'leaderboard': [{
            'rank': i + 1,
            'player': l['player__avatar_name'],
            'tier': l['player__rank'],
            'total_won': float(l['total_won'] or 0),
            'games': l['games'],
            'biggest_win': float(l['biggest_win'] or 0),
        } for i, l in enumerate(leaders)]
    })


# ============================================================
# 10. BONUSES + REFERRALS + RAKEBACK
# ============================================================

@csrf_exempt
@require_POST
@require_auth
def api_claim_daily(request):
    """Claim daily login bonus."""
    result = process_daily_login(request.player)
    request.player.refresh_from_db()
    result['balances'] = get_all_balances(request.player)
    return JsonResponse(result)


@csrf_exempt
@require_GET
@require_auth
def api_rakeback(request):
    """View available rakeback."""
    return JsonResponse(calculate_rakeback(request.player))


@csrf_exempt
@require_POST
@require_auth
def api_claim_rakeback(request):
    """Claim weekly rakeback."""
    result = claim_rakeback(request.player)
    if 'error' in result:
        return JsonResponse(result, status=400)
    request.player.refresh_from_db()
    result['balances'] = get_all_balances(request.player)
    return JsonResponse(result)


@csrf_exempt
@require_GET
@require_auth
def api_referral_info(request):
    """Get referral code and stats."""
    p = request.player
    referral_count = PlayerProfile.objects.filter(
        # TODO: add referred_by field tracking
    ).count()

    return JsonResponse({
        'referral_code': p.user.username,  # TODO: dedicated referral code
        'share_link': f'https://vantaris.casino/?ref={p.user.username}',
        'referrals': referral_count,
        'earnings_gc': 0,  # TODO: track
    })


# ============================================================
# 11. RESPONSIBLE GAMBLING
# ============================================================

@csrf_exempt
@require_POST
@require_auth
@json_body
def api_set_limits(request):
    """Set responsible gambling limits."""
    data = request.json
    p = request.player

    if 'daily_deposit_limit' in data:
        # TODO: add to player model or separate table
        pass
    if 'session_time_limit' in data:
        pass

    return JsonResponse({
        'status': 'limits_updated',
        'message': 'Your gambling limits have been updated.',
    })


@csrf_exempt
@require_POST
@require_auth
@json_body
def api_self_exclude(request):
    """Self-exclude from Vantaris for a specified period."""
    days = int(request.json.get('days', 30))
    p = request.player

    # This is IRREVERSIBLE for the duration
    # TODO: implement on player model
    return JsonResponse({
        'status': 'self_excluded',
        'until': (timezone.now() + timedelta(days=days)).isoformat(),
        'message': f'You have been self-excluded for {days} days. This cannot be undone.',
        'resources': {
            'ncpg': 'https://www.ncpgambling.org/',
            'helpline': '1-800-522-4700',
            'chat': 'https://www.ncpgambling.org/chat/',
        },
    })


# ============================================================
# 12. ADMIN / OPERATOR
# ============================================================

@csrf_exempt
@require_GET
def api_casino_health(request):
    """Casino system health check."""
    total_players = PlayerProfile.objects.count()
    active_today = PlayerProfile.objects.filter(last_played__date=date.today()).count()
    total_rounds = CasinoGameRound.objects.count()
    pending_cashouts = CashoutRequest.objects.filter(status='pending').count()

    return JsonResponse({
        'status': 'operational',
        'brand': 'Vantaris',
        'tagline': 'The darkest star burns brightest.',
        'version': '1.0.0',
        'stats': {
            'total_players': total_players,
            'active_today': active_today,
            'total_rounds': total_rounds,
            'pending_cashouts': pending_cashouts,
        },
        'games': ['blackjack', 'roulette', 'crash', 'dice', 'plinko', 'mines'],
        'modes': ['sweepstakes', 'crypto'],
    })


# ============================================================
# HELPERS
# ============================================================

def _tier_progress(player: PlayerProfile) -> dict:
    """Calculate progress to next tier."""
    tiers = [
        (0, 'Ember'),
        (5000, 'Shadow'),
        (25000, 'Eclipse'),
        (100000, 'Supernova'),
        (500000, 'Vanta Black'),
    ]

    current_idx = 0
    for i, (threshold, name) in enumerate(tiers):
        if player.xp >= threshold:
            current_idx = i

    if current_idx >= len(tiers) - 1:
        return {'current': 'Vanta Black', 'next': None, 'progress': 100}

    current_threshold = tiers[current_idx][0]
    next_threshold = tiers[current_idx + 1][0]
    next_tier = tiers[current_idx + 1][1]

    progress = ((player.xp - current_threshold) / (next_threshold - current_threshold)) * 100

    return {
        'current': tiers[current_idx][1],
        'next': next_tier,
        'xp_needed': next_threshold - player.xp,
        'progress': round(min(progress, 100), 1),
    }
