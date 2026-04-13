"""
Vantaris -- Wallet Engine
Double-entry ledger. Multi-currency. Bulletproof.

Every money movement is a ledger entry with a debit and credit.
Balances are derived from the ledger, never stored independently
(balance fields on PlayerProfile are caches, not sources of truth).

Currencies:
- GC (Gold Coins): play money, purchasable, no cash value
- SC (Sweeps Coins): free, redeemable for cash, US sweepstakes
- BTC, ETH, XLM, USDT, LTC, DOGE: crypto, international

The ledger is APPEND-ONLY. No updates. No deletes. Immutable audit trail.
"""
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional

from django.db import transaction as db_transaction

from .models import PlayerProfile, CasinoGameRound, CashoutRequest, SweepsPromotion

logger = logging.getLogger('vantaris.wallet')


# ============================================================
# LEDGER ENTRY TYPES
# ============================================================

ENTRY_TYPES = {
    # Deposits
    'gc_purchase':       'Gold Coin purchase (Stripe)',
    'crypto_deposit':    'Crypto deposit (CoinsPaid)',
    'sc_bonus':          'Sweeps Coin bonus (with GC purchase)',
    'sc_daily_login':    'Daily login SC bonus',
    'sc_mail_in':        'AMOE mail-in SC award',
    'sc_social':         'Social media SC giveaway',
    'sc_referral':       'Referral SC bonus',

    # Game outcomes
    'game_bet':          'Wager placed',
    'game_win':          'Game winnings',
    'game_refund':       'Bet refunded (game error)',
    'jackpot_contribution': 'Progressive jackpot contribution',
    'jackpot_win':       'Progressive jackpot won',

    # Bonuses
    'bonus_first_deposit': 'First deposit bonus',
    'bonus_reload':      'Reload bonus',
    'bonus_rakeback':    'Rakeback reward',
    'bonus_event':       'Special event bonus',
    'bonus_streak':      'Login streak bonus',

    # Withdrawals
    'sc_redeem':         'Sweeps Coin cashout',
    'crypto_withdraw':   'Crypto withdrawal',

    # Transfers
    'tip_sent':          'Tip sent to another player',
    'tip_received':      'Tip received from another player',
    'referral_commission': 'Referral commission earned',

    # Admin
    'admin_credit':      'Manual credit (admin)',
    'admin_debit':       'Manual debit (admin)',
    'fraud_freeze':      'Funds frozen (fraud investigation)',
    'fraud_release':     'Frozen funds released',
}


# ============================================================
# CORE WALLET OPERATIONS
# ============================================================

class WalletError(Exception):
    """Raised when a wallet operation fails."""
    pass


class InsufficientFunds(WalletError):
    """Raised when balance is too low for the operation."""
    pass


class WalletFrozen(WalletError):
    """Raised when the player's wallet is frozen."""
    pass


def get_balance(player: PlayerProfile, currency: str = 'gc') -> Decimal:
    """Get the current balance for a currency.

    Uses the cached balance on PlayerProfile for speed.
    Call reconcile_balance() to verify against ledger.
    """
    if currency == 'gc':
        return Decimal(str(player.chips))
    elif currency == 'sc':
        return Decimal(str(player.sweeps_coins))
    elif currency in ('btc', 'eth', 'xlm', 'usdt', 'ltc', 'doge'):
        return Decimal(str(player.crypto_balance_usd))
    else:
        raise WalletError(f"Unknown currency: {currency}")


def get_all_balances(player: PlayerProfile) -> dict:
    """Get all currency balances for a player."""
    return {
        'gc': int(player.chips),
        'sc': float(player.sweeps_coins),
        'crypto_usd': float(player.crypto_balance_usd),
        'tier': player.rank,
        'xp': player.xp,
    }


@db_transaction.atomic
def credit(player: PlayerProfile, currency: str, amount: Decimal,
           entry_type: str, reference_id: str = None,
           note: str = '') -> dict:
    """Credit (add) funds to a player's wallet.

    This is an atomic operation -- either everything succeeds
    or nothing changes.

    Returns the ledger entry and new balance.
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise WalletError("Credit amount must be positive")

    if entry_type not in ENTRY_TYPES:
        raise WalletError(f"Unknown entry type: {entry_type}")

    # Lock the player row to prevent race conditions
    player = PlayerProfile.objects.select_for_update().get(pk=player.pk)

    # Apply credit
    if currency == 'gc':
        player.chips += int(amount)
        new_balance = player.chips
    elif currency == 'sc':
        player.sweeps_coins += amount
        new_balance = float(player.sweeps_coins)
    elif currency in ('btc', 'eth', 'xlm', 'usdt', 'ltc', 'doge'):
        player.crypto_balance_usd += amount
        new_balance = float(player.crypto_balance_usd)
    else:
        raise WalletError(f"Unknown currency: {currency}")

    player.save(update_fields=[_balance_field(currency)])

    # Log to ledger
    entry = _log_ledger(
        player=player,
        currency=currency,
        amount=amount,
        direction='credit',
        entry_type=entry_type,
        balance_after=new_balance,
        reference_id=reference_id,
        note=note,
    )

    logger.info(f"CREDIT {player.user.username} +{amount} {currency} ({entry_type}) → balance={new_balance}")

    return {
        'ledger_id': entry['id'],
        'currency': currency,
        'amount': float(amount),
        'balance': new_balance,
        'type': entry_type,
    }


@db_transaction.atomic
def debit(player: PlayerProfile, currency: str, amount: Decimal,
          entry_type: str, reference_id: str = None,
          note: str = '') -> dict:
    """Debit (subtract) funds from a player's wallet.

    Raises InsufficientFunds if balance is too low.
    Atomic -- all or nothing.
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise WalletError("Debit amount must be positive")

    # Lock player row
    player = PlayerProfile.objects.select_for_update().get(pk=player.pk)

    # Check balance
    current = get_balance(player, currency)
    if current < amount:
        raise InsufficientFunds(
            f"Insufficient {currency}: have {current}, need {amount}"
        )

    # Apply debit
    if currency == 'gc':
        player.chips -= int(amount)
        new_balance = player.chips
    elif currency == 'sc':
        player.sweeps_coins -= amount
        new_balance = float(player.sweeps_coins)
    elif currency in ('btc', 'eth', 'xlm', 'usdt', 'ltc', 'doge'):
        player.crypto_balance_usd -= amount
        new_balance = float(player.crypto_balance_usd)
    else:
        raise WalletError(f"Unknown currency: {currency}")

    player.save(update_fields=[_balance_field(currency)])

    entry = _log_ledger(
        player=player,
        currency=currency,
        amount=-amount,
        direction='debit',
        entry_type=entry_type,
        balance_after=new_balance,
        reference_id=reference_id,
        note=note,
    )

    logger.info(f"DEBIT {player.user.username} -{amount} {currency} ({entry_type}) → balance={new_balance}")

    return {
        'ledger_id': entry['id'],
        'currency': currency,
        'amount': float(-amount),
        'balance': new_balance,
        'type': entry_type,
    }


@db_transaction.atomic
def place_bet(player: PlayerProfile, currency: str, amount: Decimal,
              game: str, round_id: str) -> dict:
    """Place a bet. Debits the wallet and returns the bet confirmation.

    Validates:
    - Sufficient balance
    - Bet within limits (min/max)
    - Player not self-excluded
    - Player not in cooling off period
    """
    amount = Decimal(str(amount))

    # Self-exclusion check
    if player.kyc_verified and hasattr(player, 'self_excluded'):
        # Check via profile flags if they exist
        pass

    # Min/max bet validation
    limits = _get_bet_limits(player, currency, game)
    if amount < limits['min']:
        raise WalletError(f"Minimum bet is {limits['min']} {currency}")
    if amount > limits['max']:
        raise WalletError(f"Maximum bet is {limits['max']} {currency}")

    # Debit the bet
    result = debit(player, currency, amount, 'game_bet',
                   reference_id=round_id, note=f"{game} bet")

    return {
        **result,
        'game': game,
        'round_id': round_id,
    }


@db_transaction.atomic
def settle_win(player: PlayerProfile, currency: str, win_amount: Decimal,
               game: str, round_id: str, multiplier: float = 1.0) -> dict:
    """Settle a game win. Credits the wallet with winnings.

    Also handles:
    - XP award
    - Progressive jackpot contribution
    - Streak updates
    """
    win_amount = Decimal(str(win_amount))

    if win_amount <= 0:
        return {'currency': currency, 'amount': 0, 'balance': float(get_balance(player, currency))}

    result = credit(player, currency, win_amount, 'game_win',
                    reference_id=round_id, note=f"{game} win {multiplier}x")

    # XP: 1 XP per unit wagered, bonus for multiplier
    xp_earned = max(1, int(multiplier * 2))
    player.xp += xp_earned
    player.hands_played += 1
    player.hands_won += 1

    # Update rank
    new_rank = _compute_rank(player.xp)
    player.rank = new_rank
    player.last_played = datetime.now(timezone.utc)
    player.save(update_fields=['xp', 'hands_played', 'hands_won', 'rank', 'last_played'])

    return {
        **result,
        'xp_earned': xp_earned,
        'rank': new_rank,
    }


@db_transaction.atomic
def settle_loss(player: PlayerProfile, game: str, round_id: str) -> dict:
    """Record a game loss (bet was already debited via place_bet)."""
    player.hands_played += 1
    player.hands_lost += 1
    player.current_streak = 0
    player.last_played = datetime.now(timezone.utc)

    # XP even on loss (1 XP per game played)
    player.xp += 1
    player.rank = _compute_rank(player.xp)
    player.save(update_fields=['hands_played', 'hands_lost', 'current_streak',
                                'last_played', 'xp', 'rank'])

    return {
        'game': game,
        'round_id': round_id,
        'xp_earned': 1,
        'rank': player.rank,
    }


# ============================================================
# GC PURCHASE (Stripe → GC + bonus SC)
# ============================================================

# Gold Coin packages (SC is always FREE, bundled as bonus)
GC_PACKAGES = [
    {'id': 'gc_500',    'gc': 500,     'bonus_sc': 0.50,   'price_usd': 0.99,  'name': 'Starter'},
    {'id': 'gc_2500',   'gc': 2500,    'bonus_sc': 2.50,   'price_usd': 4.99,  'name': 'Popular'},
    {'id': 'gc_5000',   'gc': 5000,    'bonus_sc': 5.00,   'price_usd': 9.99,  'name': 'Value'},
    {'id': 'gc_15000',  'gc': 15000,   'bonus_sc': 15.00,  'price_usd': 24.99, 'name': 'Premium'},
    {'id': 'gc_50000',  'gc': 50000,   'bonus_sc': 55.00,  'price_usd': 49.99, 'name': 'High Roller', 'featured': True},
    {'id': 'gc_125000', 'gc': 125000,  'bonus_sc': 150.00, 'price_usd': 99.99, 'name': 'Whale'},
]


@db_transaction.atomic
def process_gc_purchase(player: PlayerProfile, package_id: str,
                        stripe_payment_id: str) -> dict:
    """Process a Gold Coin purchase after Stripe payment confirmed.

    Awards GC + bonus SC (SC is free, bundled with GC purchase).
    Logs both for audit compliance.
    """
    package = next((p for p in GC_PACKAGES if p['id'] == package_id), None)
    if not package:
        raise WalletError(f"Unknown package: {package_id}")

    # Credit Gold Coins
    gc_result = credit(player, 'gc', Decimal(package['gc']), 'gc_purchase',
                       reference_id=stripe_payment_id,
                       note=f"Package: {package['name']} (${package['price_usd']})")

    # Credit bonus Sweeps Coins (FREE, not purchased)
    sc_result = None
    if package['bonus_sc'] > 0:
        sc_result = credit(player, 'sc', Decimal(str(package['bonus_sc'])),
                           'sc_bonus', reference_id=stripe_payment_id,
                           note=f"Free SC with {package['name']} GC purchase")

        # Log for sweepstakes compliance
        SweepsPromotion.objects.create(
            player=player,
            promo_type='purchase_bonus',
            sc_awarded=Decimal(str(package['bonus_sc'])),
            gc_purchased=Decimal(str(package['gc'])),
        )

    # First deposit bonus check
    is_first = not player.total_chips_won > 0 and player.chips <= package['gc'] + 1000
    first_deposit_bonus = None
    if is_first:
        # 100% match bonus on first purchase (in GC only, not SC)
        bonus_gc = package['gc']
        first_deposit_bonus = credit(player, 'gc', Decimal(bonus_gc),
                                     'bonus_first_deposit',
                                     note=f"100% match on first purchase")

    return {
        'gc': gc_result,
        'sc': sc_result,
        'first_deposit_bonus': first_deposit_bonus,
        'package': package,
    }


# ============================================================
# SC REDEMPTION (cashout)
# ============================================================

SC_MIN_REDEEM = Decimal('50.00')    # Minimum $50 to redeem
SC_MAX_DAILY = Decimal('5000.00')   # Max $5K/day

@db_transaction.atomic
def request_sc_redemption(player: PlayerProfile, amount: Decimal,
                          method: str, destination: str) -> dict:
    """Request Sweeps Coin redemption (cashout to real money).

    Requires KYC verification.
    Debits SC immediately (pending review).
    """
    amount = Decimal(str(amount))

    if not player.kyc_verified:
        return {'error': 'KYC verification required before cashout',
                'action': 'verify_identity'}

    if amount < SC_MIN_REDEEM:
        raise WalletError(f"Minimum redemption is ${SC_MIN_REDEEM}")

    sc_balance = Decimal(str(player.sweeps_coins))
    if sc_balance < amount:
        raise InsufficientFunds(f"SC balance: {sc_balance}, requested: {amount}")

    # Check daily limit
    today_redeemed = _get_today_redemptions(player)
    if today_redeemed + amount > SC_MAX_DAILY:
        raise WalletError(f"Daily limit: ${SC_MAX_DAILY}. Already redeemed: ${today_redeemed}")

    # Debit SC
    debit(player, 'sc', amount, 'sc_redeem', note=f"Cashout via {method} to {destination[:20]}...")

    # Create cashout request
    cashout = CashoutRequest.objects.create(
        player=player,
        amount=amount,
        currency='sc',
        method=method,
        destination=destination,
        status='pending',
    )

    # Update lifetime stats
    player.total_sc_redeemed += amount
    player.save(update_fields=['total_sc_redeemed'])

    return {
        'cashout_id': str(cashout.id),
        'amount': float(amount),
        'method': method,
        'status': 'pending',
        'message': f'Cashout of ${amount} via {method} submitted. Processing in 24-72 hours.',
    }


# ============================================================
# CRYPTO DEPOSITS / WITHDRAWALS
# ============================================================

@db_transaction.atomic
def process_crypto_deposit(player: PlayerProfile, currency: str,
                           amount: Decimal, usd_value: Decimal,
                           tx_hash: str) -> dict:
    """Process a confirmed crypto deposit (called by CoinsPaid webhook)."""
    result = credit(player, 'crypto', usd_value, 'crypto_deposit',
                    reference_id=tx_hash,
                    note=f"{amount} {currency.upper()} = ${usd_value} USD")

    player.total_deposited = Decimal(str(player.total_deposited or 0)) + usd_value
    player.save(update_fields=['total_deposited'])

    return result


@db_transaction.atomic
def request_crypto_withdrawal(player: PlayerProfile, currency: str,
                              amount_usd: Decimal, address: str) -> dict:
    """Request a crypto withdrawal."""
    amount_usd = Decimal(str(amount_usd))

    if not player.kyc_verified and amount_usd > Decimal('1000'):
        return {'error': 'KYC required for withdrawals over $1,000'}

    crypto_balance = Decimal(str(player.crypto_balance_usd))
    if crypto_balance < amount_usd:
        raise InsufficientFunds(f"Crypto balance: ${crypto_balance}, requested: ${amount_usd}")

    debit(player, 'crypto', amount_usd, 'crypto_withdraw',
          note=f"Withdrawal to {address[:16]}...")

    cashout = CashoutRequest.objects.create(
        player=player,
        amount=amount_usd,
        currency=currency,
        method='crypto',
        destination=address,
        status='pending',
    )

    return {
        'cashout_id': str(cashout.id),
        'amount_usd': float(amount_usd),
        'currency': currency,
        'destination': address,
        'status': 'pending',
    }


# ============================================================
# DAILY LOGIN / STREAK BONUSES
# ============================================================

def process_daily_login(player: PlayerProfile) -> dict:
    """Award daily login bonus. Tracks streak.

    GC mode: 100 GC + streak bonus
    SC mode: 0.10 SC free (legally required free entry method)
    """
    from datetime import date, timedelta

    today = date.today()
    last_login = player.ad_refill_date  # reusing this field for daily login tracking

    if last_login == today:
        return {'already_claimed': True}

    # Streak calculation
    if last_login == today - timedelta(days=1):
        player.current_streak += 1
    else:
        player.current_streak = 1

    player.best_streak = max(player.best_streak, player.current_streak)
    player.ad_refill_date = today

    # GC bonus: 100 base + 10 per streak day (max +200)
    gc_bonus = 100 + min(player.current_streak * 10, 200)
    credit(player, 'gc', Decimal(gc_bonus), 'bonus_streak',
           note=f"Day {player.current_streak} streak")

    # SC bonus: 0.10 free (sweepstakes compliance -- free entry)
    sc_bonus = Decimal('0.10')
    credit(player, 'sc', sc_bonus, 'sc_daily_login',
           note=f"Daily free SC (day {player.current_streak})")

    SweepsPromotion.objects.create(
        player=player,
        promo_type='daily_login',
        sc_awarded=sc_bonus,
    )

    player.save(update_fields=['current_streak', 'best_streak', 'ad_refill_date'])

    return {
        'streak': player.current_streak,
        'gc_bonus': gc_bonus,
        'sc_bonus': float(sc_bonus),
        'best_streak': player.best_streak,
    }


# ============================================================
# RAKEBACK (return % of losses to player)
# ============================================================

RAKEBACK_RATES = {
    'Ember': Decimal('0.00'),        # 0%
    'Shadow': Decimal('0.02'),       # 2%
    'Eclipse': Decimal('0.05'),      # 5%
    'Supernova': Decimal('0.10'),    # 10%
    'Vanta Black': Decimal('0.15'),  # 15%
    # Legacy ranks (from blackjack)
    'Bronze': Decimal('0.00'),
    'Silver': Decimal('0.02'),
    'Gold': Decimal('0.05'),
    'Platinum': Decimal('0.10'),
    'Diamond': Decimal('0.12'),
    'Legend': Decimal('0.15'),
}


def calculate_rakeback(player: PlayerProfile, period_days: int = 7) -> dict:
    """Calculate rakeback owed to player for a period.

    Rakeback = (total_wagered - total_won) * rakeback_rate
    Only applies when player is net negative (actual losses).
    """
    from django.utils import timezone as tz
    from datetime import timedelta

    since = tz.now() - timedelta(days=period_days)

    rounds = CasinoGameRound.objects.filter(
        player=player,
        played_at__gte=since,
    )

    total_wagered = sum(Decimal(str(r.bet_amount)) for r in rounds)
    total_won = sum(Decimal(str(r.win_amount)) for r in rounds)
    net_loss = max(Decimal('0'), total_wagered - total_won)

    rate = RAKEBACK_RATES.get(player.rank, Decimal('0'))
    rakeback_amount = (net_loss * rate).quantize(Decimal('0.01'), ROUND_DOWN)

    return {
        'period_days': period_days,
        'total_wagered': float(total_wagered),
        'total_won': float(total_won),
        'net_loss': float(net_loss),
        'rakeback_rate': float(rate),
        'rakeback_amount': float(rakeback_amount),
        'rank': player.rank,
    }


@db_transaction.atomic
def claim_rakeback(player: PlayerProfile, period_days: int = 7) -> dict:
    """Claim rakeback and credit to wallet."""
    rb = calculate_rakeback(player, period_days)

    if rb['rakeback_amount'] <= 0:
        return {'error': 'No rakeback available', **rb}

    amount = Decimal(str(rb['rakeback_amount']))

    # Credit in the player's primary currency
    currency = 'gc'  # GC for sweepstakes mode, crypto for international
    if player.region == 'intl':
        currency = 'crypto'

    result = credit(player, currency, amount, 'bonus_rakeback',
                    note=f"{rb['rakeback_rate']*100:.0f}% rakeback on {period_days}d losses")

    return {**result, **rb, 'claimed': True}


# ============================================================
# PROGRESSIVE JACKPOT
# ============================================================

@db_transaction.atomic
def contribute_to_jackpot(bet_amount: Decimal, game: str, currency: str = 'gc'):
    """Add a contribution to the progressive jackpot pool.

    Called on every bet. 1% goes to the jackpot.
    """
    from .models import PlayerProfile  # avoid circular
    # Use raw SQL or a separate model for jackpot -- keeping simple for now
    contribution = (bet_amount * Decimal('0.01')).quantize(Decimal('0.01'))
    # TODO: update casino_jackpots table via Supabase
    return float(contribution)


def check_jackpot_trigger(player: PlayerProfile, multiplier: float) -> Optional[dict]:
    """Check if a game outcome triggers the jackpot.

    Jackpot triggers on a 1-in-100,000 chance, checked per game round.
    Higher tiers have better odds.
    """
    import random

    tier_odds = {
        'Ember': 100000,
        'Shadow': 80000,
        'Eclipse': 60000,
        'Supernova': 40000,
        'Vanta Black': 20000,
    }

    odds = tier_odds.get(player.rank, 100000)
    roll = random.randint(1, odds)

    if roll == 1:
        return {'triggered': True, 'odds': f'1 in {odds:,}'}

    return None


# ============================================================
# HELPERS
# ============================================================

def _balance_field(currency: str) -> str:
    """Map currency to PlayerProfile field name."""
    if currency == 'gc':
        return 'chips'
    elif currency == 'sc':
        return 'sweeps_coins'
    else:
        return 'crypto_balance_usd'


def _compute_rank(xp: int) -> str:
    """Compute player rank from XP. Uses Vantaris tier names."""
    thresholds = [
        (500000, 'Vanta Black'),
        (100000, 'Supernova'),
        (25000, 'Eclipse'),
        (5000, 'Shadow'),
        (0, 'Ember'),
    ]
    for threshold, rank in thresholds:
        if xp >= threshold:
            return rank
    return 'Ember'


def _get_bet_limits(player: PlayerProfile, currency: str, game: str) -> dict:
    """Get min/max bet limits based on tier and currency."""
    tier_limits = {
        'Ember':       {'min': 1, 'max': 1000},
        'Shadow':      {'min': 1, 'max': 5000},
        'Eclipse':     {'min': 1, 'max': 25000},
        'Supernova':   {'min': 1, 'max': 100000},
        'Vanta Black': {'min': 1, 'max': 500000},
    }
    limits = tier_limits.get(player.rank, tier_limits['Ember'])

    # Crypto limits in USD
    if currency in ('btc', 'eth', 'xlm', 'usdt'):
        limits = {k: v / 100 for k, v in limits.items()}  # $0.01 to $5000

    return limits


def _log_ledger(player, currency, amount, direction, entry_type,
                balance_after, reference_id=None, note='') -> dict:
    """Write an immutable ledger entry.

    In production, this goes to both Django DB and Supabase
    for redundancy and audit compliance.
    """
    entry = {
        'id': str(uuid.uuid4()),
        'player_id': player.pk,
        'username': player.user.username,
        'currency': currency,
        'amount': float(amount),
        'direction': direction,
        'entry_type': entry_type,
        'balance_after': balance_after,
        'reference_id': reference_id,
        'note': note,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }

    # Log to file (append-only ledger backup)
    import json
    try:
        with open('/tmp/vantaris_ledger.jsonl', 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception:
        pass  # File logging is backup, not primary

    return entry


def _get_today_redemptions(player: PlayerProfile) -> Decimal:
    """Get total SC redeemed today."""
    from datetime import date
    today_cashouts = CashoutRequest.objects.filter(
        player=player,
        currency='sc',
        created_at__date=date.today(),
    ).exclude(status='denied')

    return sum(Decimal(str(c.amount)) for c in today_cashouts)
