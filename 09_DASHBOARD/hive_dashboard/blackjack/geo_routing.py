"""
Vantaris Geo-Routing & Compliance Layer

Routes players to the correct experience based on location:
- US (permitted states) → Sweepstakes mode (GC + SC)
- US (restricted states) → Blocked
- UK/AU/FR/NL → Blocked (no license for these markets)
- International → Crypto mode (BTC, ETH, XLM, USDT)

Uses MaxMind GeoIP2 for IP-based geolocation.
Falls back to Cloudflare CF-IPCountry header if GeoIP2 unavailable.
"""
from functools import wraps


# States where sweepstakes casinos are banned (as of April 2026)
US_BLOCKED_STATES = {
    'CA',  # California (AB 831, effective Jan 2026)
    'NJ',  # New Jersey
    'NV',  # Nevada
    'CT',  # Connecticut
    'NY',  # New York (SB 5935)
    'MT',  # Montana
    'IN',  # Indiana (April 2026)
    'ME',  # Maine (April 2026)
}

# Countries blocked entirely (no license coverage)
BLOCKED_COUNTRIES = {
    'GB',  # United Kingdom
    'AU',  # Australia
    'FR',  # France
    'NL',  # Netherlands
    'IT',  # Italy (requires AAMS license)
    'ES',  # Spain (requires DGOJ license)
    'SE',  # Sweden (requires Spelinspektionen license)
    'DE',  # Germany (requires GGL license)
    'SG',  # Singapore
    'HK',  # Hong Kong
}

# US states + territories (for sweepstakes routing)
US_CODES = {'US', 'PR', 'VI', 'GU', 'AS', 'MP'}


def get_player_location(request) -> dict:
    """Determine player's location from request.

    Priority:
    1. Cloudflare CF-IPCountry + CF-Region headers (if behind Cloudflare)
    2. MaxMind GeoIP2 lookup (if installed)
    3. X-Forwarded-For IP → GeoIP lookup
    4. Fallback: unknown → block for safety
    """
    # Cloudflare headers (free, no API needed)
    cf_country = request.META.get('HTTP_CF_IPCOUNTRY', '').upper()
    cf_region = request.META.get('HTTP_CF_REGION', '').upper()

    if cf_country:
        return {
            'country': cf_country,
            'state': cf_region if cf_country in US_CODES else None,
            'source': 'cloudflare',
        }

    # MaxMind GeoIP2 (if installed)
    try:
        import geoip2.database
        ip = _get_client_ip(request)
        if ip:
            reader = geoip2.database.Reader('/usr/share/GeoIP/GeoLite2-City.mmdb')
            response = reader.city(ip)
            return {
                'country': response.country.iso_code or 'XX',
                'state': response.subdivisions.most_specific.iso_code if response.subdivisions else None,
                'city': response.city.name,
                'source': 'maxmind',
            }
    except Exception:
        pass

    # Fallback
    return {
        'country': 'XX',
        'state': None,
        'source': 'unknown',
    }


def _get_client_ip(request) -> str:
    """Extract real client IP from request headers."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP', '')
    if cf_ip:
        return cf_ip
    return request.META.get('REMOTE_ADDR', '')


def get_player_mode(location: dict) -> dict:
    """Determine which casino mode to serve based on location.

    Returns:
        mode: 'sweepstakes' | 'crypto' | 'blocked'
        reason: why this mode was selected
        currencies: available currencies for this mode
    """
    country = location.get('country', 'XX')
    state = location.get('state', '')

    # Blocked countries
    if country in BLOCKED_COUNTRIES:
        return {
            'mode': 'blocked',
            'reason': f'Not available in {country}. We are working on expanding to your region.',
            'currencies': [],
        }

    # US players
    if country in US_CODES:
        if state in US_BLOCKED_STATES:
            return {
                'mode': 'blocked',
                'reason': f'Not available in your state ({state}). Check back as regulations change.',
                'currencies': [],
            }
        return {
            'mode': 'sweepstakes',
            'reason': 'Sweepstakes mode active. Play with Gold Coins, win Sweeps Coins!',
            'currencies': ['gc', 'sc'],
            'features': {
                'gold_coins': True,
                'sweeps_coins': True,
                'crypto': False,
                'cashout_sc': True,
                'cashout_crypto': False,
                'amoe_available': True,
            },
        }

    # International players → crypto mode
    return {
        'mode': 'crypto',
        'reason': 'Welcome to the international experience. Deposit and play with crypto.',
        'currencies': ['btc', 'eth', 'xlm', 'usdt', 'ltc', 'doge'],
        'features': {
            'gold_coins': False,
            'sweeps_coins': False,
            'crypto': True,
            'cashout_sc': False,
            'cashout_crypto': True,
            'amoe_available': False,
        },
    }


def require_casino_access(view_func):
    """Django view decorator that checks geo-compliance before serving casino content."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from django.http import JsonResponse

        location = get_player_location(request)
        mode = get_player_mode(location)

        if mode['mode'] == 'blocked':
            return JsonResponse({
                'error': 'region_blocked',
                'message': mode['reason'],
                'country': location.get('country'),
                'state': location.get('state'),
            }, status=403)

        # Attach mode info to request for downstream use
        request.casino_mode = mode
        request.player_location = location

        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================
# COINSPAID INTEGRATION (crypto deposits/withdrawals)
# ============================================================

class CoinsPaidClient:
    """CoinsPaid API client for crypto payment processing.

    Handles deposits, withdrawals, and callbacks.
    Docs: https://docs.coinspaid.com/
    """

    def __init__(self, api_key: str = '', api_secret: str = '', sandbox: bool = True):
        import os
        self.api_key = api_key or os.environ.get('COINSPAID_API_KEY', '')
        self.api_secret = api_secret or os.environ.get('COINSPAID_API_SECRET', '')
        self.base_url = 'https://app.sandbox.coinspaid.com/api/v2' if sandbox else 'https://app.coinspaid.com/api/v2'

    def _request(self, endpoint: str, data: dict = None) -> dict:
        """Make authenticated API request to CoinsPaid."""
        import hashlib
        import hmac
        import json
        import urllib.request

        body = json.dumps(data or {}).encode()
        signature = hmac.new(
            self.api_secret.encode(),
            body,
            hashlib.sha512
        ).hexdigest()

        req = urllib.request.Request(
            f"{self.base_url}/{endpoint}",
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-Processing-Key': self.api_key,
                'X-Processing-Signature': signature,
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {'error': str(e)}

    def create_deposit_address(self, currency: str, player_id: str,
                               callback_url: str) -> dict:
        """Generate a unique deposit address for a player.

        Each player gets a persistent address per currency.
        """
        return self._request('addresses/take', {
            'foreign_id': f'player_{player_id}',
            'currency': currency.upper(),
            'convert_to': 'USD',
            'callback_url': callback_url,
        })

    def initiate_withdrawal(self, currency: str, amount: float,
                            address: str, player_id: str) -> dict:
        """Send crypto to a player's withdrawal address."""
        return self._request('withdrawal/crypto', {
            'foreign_id': f'withdraw_{player_id}_{int(amount*100)}',
            'currency': currency.upper(),
            'amount': str(amount),
            'address': address,
        })

    def get_exchange_rate(self, from_currency: str, to_currency: str = 'USD') -> dict:
        """Get current exchange rate."""
        return self._request('currencies/pairs', {
            'currency_from': from_currency.upper(),
            'currency_to': to_currency.upper(),
        })


# Singleton client instance
coinspaid = CoinsPaidClient()
