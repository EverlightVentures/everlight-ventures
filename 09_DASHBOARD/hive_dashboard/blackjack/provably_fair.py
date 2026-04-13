"""
Vantaris -- Provably Fair RNG Engine

Cryptographic fairness verification for all casino games.
Players can independently verify every outcome.

Protocol:
1. Server generates a random server_seed
2. Server gives player hash(server_seed) as commitment
3. Player provides (or auto-generates) a client_seed
4. Game outcome = HMAC-SHA256(server_seed, client_seed:nonce)
5. After game, server reveals server_seed
6. Player verifies: hash(server_seed) == committed hash
7. Player verifies: outcome matches HMAC(server_seed, client_seed:nonce)

This is the same system used by Stake.com, BC.Game, and Roobet.
"""
import hashlib
import hmac
import secrets
import struct


def generate_server_seed() -> str:
    """Generate a cryptographically secure random server seed."""
    return secrets.token_hex(32)  # 256-bit


def generate_client_seed() -> str:
    """Generate a default client seed (player can override)."""
    return secrets.token_hex(16)  # 128-bit


def hash_seed(seed: str) -> str:
    """SHA-256 hash of a seed. Used for commitment (shown to player before game)."""
    return hashlib.sha256(seed.encode()).hexdigest()


def generate_outcome_bytes(server_seed: str, client_seed: str, nonce: int) -> bytes:
    """Generate deterministic pseudo-random bytes from seeds + nonce.

    Uses HMAC-SHA256 with the server seed as key and
    "client_seed:nonce" as message. Returns 32 bytes of
    cryptographically deterministic randomness.
    """
    message = f"{client_seed}:{nonce}".encode()
    return hmac.new(server_seed.encode(), message, hashlib.sha256).digest()


def outcome_to_float(server_seed: str, client_seed: str, nonce: int) -> float:
    """Convert seeds + nonce to a float in [0, 1).

    Takes first 4 bytes of HMAC output, converts to uint32,
    divides by 2^32 to get a uniform float.
    """
    raw = generate_outcome_bytes(server_seed, client_seed, nonce)
    value = struct.unpack('>I', raw[:4])[0]  # big-endian uint32
    return value / (2 ** 32)


def outcome_to_int(server_seed: str, client_seed: str, nonce: int,
                   min_val: int, max_val: int) -> int:
    """Convert seeds + nonce to an integer in [min_val, max_val]."""
    f = outcome_to_float(server_seed, client_seed, nonce)
    return min_val + int(f * (max_val - min_val + 1))


def outcome_to_card(server_seed: str, client_seed: str, nonce: int,
                    deck_size: int = 52) -> int:
    """Convert seeds + nonce to a card index [0, deck_size)."""
    return outcome_to_int(server_seed, client_seed, nonce, 0, deck_size - 1)


def generate_shuffle(server_seed: str, client_seed: str,
                     deck_size: int = 312, start_nonce: int = 0) -> list[int]:
    """Generate a provably fair deck shuffle (Fisher-Yates).

    Uses sequential nonces to generate each swap in the shuffle.
    312 = 6 decks × 52 cards (standard blackjack shoe).
    """
    deck = list(range(deck_size))
    for i in range(deck_size - 1, 0, -1):
        j = outcome_to_int(server_seed, client_seed, start_nonce + (deck_size - 1 - i), 0, i)
        deck[i], deck[j] = deck[j], deck[i]
    return deck


def verify_outcome(server_seed: str, server_seed_hash: str,
                   client_seed: str, nonce: int) -> dict:
    """Verify a game outcome was fair.

    This is what the PLAYER runs to verify:
    1. Check that hash(server_seed) matches the hash they were given
    2. Recompute the outcome using the revealed seeds
    """
    computed_hash = hash_seed(server_seed)
    hash_matches = computed_hash == server_seed_hash

    outcome_float = outcome_to_float(server_seed, client_seed, nonce)

    return {
        "server_seed": server_seed,
        "server_seed_hash": server_seed_hash,
        "computed_hash": computed_hash,
        "hash_valid": hash_matches,
        "client_seed": client_seed,
        "nonce": nonce,
        "outcome_float": outcome_float,
        "verified": hash_matches,
    }


# ============================================================
# GAME-SPECIFIC OUTCOME GENERATORS
# ============================================================

def roulette_outcome(server_seed: str, client_seed: str, nonce: int) -> int:
    """Generate roulette number [0-36]. 0 = green, 1-36 = red/black."""
    return outcome_to_int(server_seed, client_seed, nonce, 0, 36)


def crash_outcome(server_seed: str, client_seed: str, nonce: int) -> float:
    """Generate crash multiplier. House edge: ~3%.

    Uses the formula from Stake/BC.Game:
    - Generate a hash
    - Convert to a number
    - Apply house edge
    - Result is the crash point (1.00x minimum)

    Higher multipliers are exponentially rarer.
    """
    raw = generate_outcome_bytes(server_seed, client_seed, nonce)
    h = int.from_bytes(raw[:4], 'big')

    # House edge: 3% of games crash at 1.00x instantly
    if h % 33 == 0:
        return 1.00

    # Exponential distribution for crash point
    # E = 2^32 / (2^32 - h) gives values from 1.0 to infinity
    # Capped at 1000x for sanity
    e = (2 ** 32) / (2 ** 32 - h)
    crash_point = max(1.00, min(round(e * 100) / 100, 1000.00))

    return crash_point


def dice_outcome(server_seed: str, client_seed: str, nonce: int) -> float:
    """Generate dice roll result [0.00 - 99.99]."""
    f = outcome_to_float(server_seed, client_seed, nonce)
    return round(f * 10000) / 100  # two decimal places


def plinko_outcome(server_seed: str, client_seed: str, nonce: int,
                   rows: int = 16) -> list[str]:
    """Generate plinko ball path. Returns list of 'L'/'R' directions.

    Each row, the ball goes left or right. The final bucket
    determines the multiplier.
    """
    path = []
    for row in range(rows):
        f = outcome_to_float(server_seed, client_seed, nonce * 100 + row)
        path.append('R' if f >= 0.5 else 'L')
    return path


def plinko_multiplier(path: list[str], risk: str = 'medium') -> float:
    """Convert plinko path to a multiplier based on risk level.

    The ball lands in a bucket based on how many times it went right.
    Center buckets = low multiplier. Edge buckets = high multiplier.
    """
    rights = sum(1 for d in path if d == 'R')
    rows = len(path)
    center = rows // 2

    # Distance from center determines bucket
    distance = abs(rights - center)

    multipliers = {
        'low': {0: 1.5, 1: 1.2, 2: 1.1, 3: 1.0, 4: 0.7, 5: 0.5, 6: 0.3, 7: 0.2, 8: 0.2},
        'medium': {0: 3.0, 1: 2.0, 2: 1.5, 3: 1.0, 4: 0.5, 5: 0.3, 6: 5.0, 7: 10.0, 8: 25.0},
        'high': {0: 10.0, 1: 5.0, 2: 3.0, 3: 1.5, 4: 0.3, 5: 0.2, 6: 25.0, 7: 50.0, 8: 1000.0},
    }

    table = multipliers.get(risk, multipliers['medium'])
    return table.get(min(distance, 8), 0.2)


def mines_layout(server_seed: str, client_seed: str, nonce: int,
                 grid_size: int = 25, mine_count: int = 5) -> list[int]:
    """Generate mine positions for a Mines game.

    Returns list of mine positions [0, grid_size).
    Uses sequential nonces to pick each mine position without repeats.
    """
    mines = set()
    sub_nonce = 0
    while len(mines) < mine_count:
        pos = outcome_to_int(server_seed, client_seed, nonce * 1000 + sub_nonce, 0, grid_size - 1)
        mines.add(pos)
        sub_nonce += 1
    return sorted(mines)


def mines_multiplier(tiles_revealed: int, mine_count: int, grid_size: int = 25) -> float:
    """Calculate current multiplier for revealed tiles in Mines.

    Uses combinatorial probability: probability of surviving N reveals
    with M mines in a grid of G tiles.
    """
    if tiles_revealed == 0:
        return 1.0

    safe_tiles = grid_size - mine_count
    prob = 1.0
    for i in range(tiles_revealed):
        prob *= (safe_tiles - i) / (grid_size - i)

    if prob <= 0:
        return 0.0

    # House edge: ~2%
    return round((1.0 / prob) * 0.98, 2)
