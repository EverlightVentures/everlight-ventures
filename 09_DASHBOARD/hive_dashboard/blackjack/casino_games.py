"""
Vantaris -- Game Engine
5 provably fair games + shared economy layer.

Games: Roulette, Crash, Dice, Plinko, Mines
All use the provably fair RNG from provably_fair.py.
All share the same currency system (Chips/GC + Gems + SC).

Design: Luxury, seductive, dark aesthetic.
Every game response includes presentation data for the frontend:
- Ambient colors, particle effects, sound cues
- Dealer persona reactions
- Win celebrations with tier-appropriate flair
"""
import json
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from . import provably_fair as pf


# ============================================================
# GAME THEME / PRESENTATION LAYER
# ============================================================

GAME_THEMES = {
    "roulette": {
        "name": "Vantaris Roulette",
        "tagline": "Where fortune meets obsidian.",
        "ambient": "#1a0a2e",        # deep purple-black
        "accent": "#c9a84c",          # gold
        "glow": "#ff2d55",            # roulette red
        "particle": "gold_dust",
        "sound_spin": "roulette_spin_luxury",
        "sound_win": "crystal_chime",
        "sound_loss": "velvet_fade",
        "dealer_name": "Aria",
        "dealer_avatar": "aria_roulette",
    },
    "crash": {
        "name": "Vantaris Crash",
        "tagline": "How high do you dare?",
        "ambient": "#0a0a1a",        # midnight
        "accent": "#00ff88",          # neon green (the rising line)
        "glow": "#ff3366",            # crash red
        "particle": "neon_trail",
        "sound_rising": "tension_build",
        "sound_crash": "shatter_glass",
        "sound_cashout": "cash_register_luxury",
        "dealer_name": "Cipher",
        "dealer_avatar": "cipher_crash",
    },
    "dice": {
        "name": "Vantaris Dice",
        "tagline": "Roll the obsidian.",
        "ambient": "#0d1117",
        "accent": "#58a6ff",          # ice blue
        "glow": "#c9a84c",            # gold
        "particle": "ice_shatter",
        "sound_roll": "dice_obsidian",
        "sound_win": "bass_drop_smooth",
        "sound_loss": "silk_whisper",
        "dealer_name": "Marcus",
        "dealer_avatar": "marcus_dice",
    },
    "plinko": {
        "name": "Vantaris Plinko",
        "tagline": "Watch it fall. Pray it lands.",
        "ambient": "#1a0520",        # dark magenta
        "accent": "#ff6b35",          # ember orange
        "glow": "#ffd700",            # gold
        "particle": "ember_cascade",
        "sound_bounce": "crystal_ping",
        "sound_land": "slot_ding_luxury",
        "sound_jackpot": "fireworks_luxury",
        "dealer_name": "Kanisha",
        "dealer_avatar": "kanisha_plinko",
    },
    "mines": {
        "name": "Vantaris Mines",
        "tagline": "Every tap could be your last. Or your fortune.",
        "ambient": "#0a1a0a",        # dark emerald
        "accent": "#00ff41",          # matrix green
        "glow": "#ff0000",            # mine red
        "particle": "gem_sparkle",
        "sound_safe": "gem_collect",
        "sound_mine": "explosion_muffled",
        "sound_cashout": "vault_open",
        "dealer_name": "Bacardi Ice",
        "dealer_avatar": "bacardi_mines",
    },
}

# Dealer reactions based on outcome
DEALER_REACTIONS = {
    "big_win": [
        "Now THAT's what I'm talking about. 🔥",
        "Obsidian energy. You were born for this.",
        "The table bows to you tonight.",
        "I've seen thousands of players. You're different.",
    ],
    "win": [
        "Clean win. Let it ride?",
        "Fortune favors the bold.",
        "Nicely done, love.",
        "The Vantaris gods smile tonight.",
    ],
    "loss": [
        "The night is still young.",
        "Even kings lose a hand. The crown stays.",
        "That one stings. But you'll be back.",
        "The table remembers courage, not outcomes.",
    ],
    "jackpot": [
        "LADIES AND GENTLEMEN. We have a WINNER.",
        "The entire floor just felt that.",
        "I need a moment. That was... magnificent.",
        "History. You just made history at this table.",
    ],
    "cashout_early": [
        "Smart. Protect the bag.",
        "Discipline is the real flex.",
        "Cash secured. Legend move.",
    ],
    "streak": [
        "Three in a row. The table is yours.",
        "You're on fire and the whole floor knows it.",
        "I'd bet on you right now. And I never bet.",
    ],
}

# Win celebration tiers
WIN_CELEBRATIONS = {
    "small": {    # < 2x
        "animation": "subtle_glow",
        "particles": 20,
        "screen_shake": False,
        "confetti": False,
    },
    "medium": {   # 2-10x
        "animation": "gold_pulse",
        "particles": 100,
        "screen_shake": True,
        "confetti": False,
    },
    "large": {    # 10-50x
        "animation": "diamond_burst",
        "particles": 500,
        "screen_shake": True,
        "confetti": True,
        "confetti_type": "gold",
    },
    "massive": {  # 50x+
        "animation": "obsidian_eruption",
        "particles": 2000,
        "screen_shake": True,
        "confetti": True,
        "confetti_type": "platinum",
        "full_screen_takeover": True,
        "dealer_standing_ovation": True,
    },
}


def _get_celebration(multiplier: float) -> dict:
    if multiplier >= 50:
        return WIN_CELEBRATIONS["massive"]
    elif multiplier >= 10:
        return WIN_CELEBRATIONS["large"]
    elif multiplier >= 2:
        return WIN_CELEBRATIONS["medium"]
    return WIN_CELEBRATIONS["small"]


def _get_dealer_reaction(outcome: str) -> str:
    import random
    reactions = DEALER_REACTIONS.get(outcome, DEALER_REACTIONS["win"])
    return random.choice(reactions)


# ============================================================
# GAME: ROULETTE
# ============================================================

ROULETTE_RED = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
ROULETTE_BLACK = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

ROULETTE_PAYOUTS = {
    "straight": 35,    # single number
    "split": 17,       # 2 numbers
    "street": 11,      # 3 numbers (row)
    "corner": 8,       # 4 numbers
    "line": 5,         # 6 numbers (2 rows)
    "dozen": 2,        # 12 numbers (1-12, 13-24, 25-36)
    "column": 2,       # 12 numbers (column)
    "red": 1,          # 18 numbers
    "black": 1,
    "odd": 1,
    "even": 1,
    "high": 1,         # 19-36
    "low": 1,          # 1-18
}


def play_roulette(server_seed: str, client_seed: str, nonce: int,
                  bets: list[dict]) -> dict:
    """Play a round of roulette.

    bets: [{type: "red", amount: 100}, {type: "straight", number: 17, amount: 50}]

    Returns full game result with presentation data.
    """
    result_number = pf.roulette_outcome(server_seed, client_seed, nonce)
    color = "red" if result_number in ROULETTE_RED else "black" if result_number in ROULETTE_BLACK else "green"

    total_bet = sum(b["amount"] for b in bets)
    total_win = 0
    bet_results = []

    for bet in bets:
        bet_type = bet["type"]
        amount = bet["amount"]
        won = False

        if bet_type == "straight" and bet.get("number") == result_number:
            won = True
        elif bet_type == "red" and color == "red":
            won = True
        elif bet_type == "black" and color == "black":
            won = True
        elif bet_type == "odd" and result_number > 0 and result_number % 2 == 1:
            won = True
        elif bet_type == "even" and result_number > 0 and result_number % 2 == 0:
            won = True
        elif bet_type == "low" and 1 <= result_number <= 18:
            won = True
        elif bet_type == "high" and 19 <= result_number <= 36:
            won = True
        elif bet_type == "dozen":
            dozen = bet.get("dozen", 1)
            if dozen == 1 and 1 <= result_number <= 12:
                won = True
            elif dozen == 2 and 13 <= result_number <= 24:
                won = True
            elif dozen == 3 and 25 <= result_number <= 36:
                won = True

        payout_multiplier = ROULETTE_PAYOUTS.get(bet_type, 0)
        win_amount = amount * (payout_multiplier + 1) if won else 0
        total_win += win_amount

        bet_results.append({
            "type": bet_type,
            "amount": amount,
            "won": won,
            "payout": win_amount,
        })

    net = total_win - total_bet
    multiplier = total_win / total_bet if total_bet > 0 else 0

    theme = GAME_THEMES["roulette"]

    return {
        "game": "roulette",
        "round_id": str(uuid.uuid4()),
        "result": {
            "number": result_number,
            "color": color,
        },
        "bets": bet_results,
        "total_bet": total_bet,
        "total_win": total_win,
        "net": net,
        "multiplier": round(multiplier, 2),
        # Provably fair
        "server_seed_hash": pf.hash_seed(server_seed),
        "client_seed": client_seed,
        "nonce": nonce,
        # Presentation
        "theme": theme,
        "celebration": _get_celebration(multiplier) if net > 0 else None,
        "dealer_says": _get_dealer_reaction("big_win" if multiplier >= 10 else "win" if net > 0 else "loss"),
    }


# ============================================================
# GAME: CRASH
# ============================================================

def play_crash(server_seed: str, client_seed: str, nonce: int,
               bet_amount: int, cashout_at: float = None) -> dict:
    """Play a round of Crash.

    The multiplier rises from 1.00x until it crashes.
    Player can cash out at any point before the crash.
    If cashout_at is set, auto-cashout at that multiplier.
    If not set, the game crashes and player loses.
    """
    crash_point = pf.crash_outcome(server_seed, client_seed, nonce)

    if cashout_at and cashout_at <= crash_point:
        # Player cashed out before crash
        won = True
        multiplier = cashout_at
        win_amount = int(bet_amount * multiplier)
    else:
        # Player didn't cash out (or crash happened before cashout)
        won = False
        multiplier = crash_point
        win_amount = 0

    net = win_amount - bet_amount
    theme = GAME_THEMES["crash"]

    outcome_type = "cashout_early" if won else "loss"
    if won and multiplier >= 10:
        outcome_type = "big_win"
    elif won and multiplier >= 50:
        outcome_type = "jackpot"

    return {
        "game": "crash",
        "round_id": str(uuid.uuid4()),
        "result": {
            "crash_point": crash_point,
            "cashout_at": cashout_at,
            "crashed_before_cashout": not won,
        },
        "bet_amount": bet_amount,
        "win_amount": win_amount,
        "net": net,
        "multiplier": round(multiplier, 2),
        "server_seed_hash": pf.hash_seed(server_seed),
        "client_seed": client_seed,
        "nonce": nonce,
        "theme": theme,
        "celebration": _get_celebration(multiplier) if won else None,
        "dealer_says": _get_dealer_reaction(outcome_type),
    }


# ============================================================
# GAME: DICE
# ============================================================

def play_dice(server_seed: str, client_seed: str, nonce: int,
              bet_amount: int, target: float, over: bool = True) -> dict:
    """Play a round of Dice.

    Player bets that the roll will be OVER or UNDER a target number.
    Roll range: 0.00 - 99.99
    Lower win chance = higher payout.

    Example: target=50, over=True → 49.99% chance → ~2x payout
    """
    roll = pf.dice_outcome(server_seed, client_seed, nonce)

    if over:
        won = roll > target
        win_chance = (100.0 - target) / 100.0
    else:
        won = roll < target
        win_chance = target / 100.0

    # Payout: (1 / win_chance) * 0.98 (2% house edge)
    payout_multiplier = round((1.0 / max(win_chance, 0.01)) * 0.98, 4) if win_chance > 0 else 0

    win_amount = int(bet_amount * payout_multiplier) if won else 0
    net = win_amount - bet_amount
    theme = GAME_THEMES["dice"]

    return {
        "game": "dice",
        "round_id": str(uuid.uuid4()),
        "result": {
            "roll": roll,
            "target": target,
            "direction": "over" if over else "under",
            "win_chance": round(win_chance * 100, 2),
        },
        "bet_amount": bet_amount,
        "win_amount": win_amount,
        "net": net,
        "multiplier": round(payout_multiplier, 4),
        "server_seed_hash": pf.hash_seed(server_seed),
        "client_seed": client_seed,
        "nonce": nonce,
        "theme": theme,
        "celebration": _get_celebration(payout_multiplier) if won else None,
        "dealer_says": _get_dealer_reaction("big_win" if payout_multiplier >= 5 and won else "win" if won else "loss"),
    }


# ============================================================
# GAME: PLINKO
# ============================================================

def play_plinko(server_seed: str, client_seed: str, nonce: int,
                bet_amount: int, risk: str = "medium", rows: int = 16) -> dict:
    """Play a round of Plinko.

    Ball drops from top, bouncing L/R at each peg row.
    Risk level affects multiplier distribution:
    - Low: frequent small wins
    - Medium: balanced
    - High: rare huge wins, frequent losses
    """
    path = pf.plinko_outcome(server_seed, client_seed, nonce, rows)
    multiplier = pf.plinko_multiplier(path, risk)
    win_amount = int(bet_amount * multiplier)
    net = win_amount - bet_amount
    theme = GAME_THEMES["plinko"]

    # Which bucket did it land in
    rights = sum(1 for d in path if d == 'R')
    bucket = rights  # 0 = far left, rows = far right

    outcome = "jackpot" if multiplier >= 25 else "big_win" if multiplier >= 5 else "win" if net > 0 else "loss"

    return {
        "game": "plinko",
        "round_id": str(uuid.uuid4()),
        "result": {
            "path": path,
            "bucket": bucket,
            "total_buckets": rows + 1,
            "risk": risk,
            "rows": rows,
        },
        "bet_amount": bet_amount,
        "win_amount": win_amount,
        "net": net,
        "multiplier": round(multiplier, 2),
        "server_seed_hash": pf.hash_seed(server_seed),
        "client_seed": client_seed,
        "nonce": nonce,
        "theme": theme,
        "celebration": _get_celebration(multiplier) if net > 0 else None,
        "dealer_says": _get_dealer_reaction(outcome),
    }


# ============================================================
# GAME: MINES
# ============================================================

def create_mines_game(server_seed: str, client_seed: str, nonce: int,
                      bet_amount: int, mine_count: int = 5,
                      grid_size: int = 25) -> dict:
    """Start a new Mines game. Returns the game state (mines hidden)."""
    mines = pf.mines_layout(server_seed, client_seed, nonce, grid_size, mine_count)

    return {
        "game": "mines",
        "round_id": str(uuid.uuid4()),
        "state": "active",
        "grid_size": grid_size,
        "mine_count": mine_count,
        "bet_amount": bet_amount,
        "tiles_revealed": 0,
        "current_multiplier": 1.0,
        "safe_tiles_revealed": [],
        # Mines are SECRET until game ends
        "_mines": mines,  # store server-side only, never send to client
        "server_seed_hash": pf.hash_seed(server_seed),
        "client_seed": client_seed,
        "nonce": nonce,
        "theme": GAME_THEMES["mines"],
        "dealer_says": "Pick a tile. Any tile. But choose wisely... 💎",
    }


def reveal_mines_tile(game_state: dict, tile_index: int) -> dict:
    """Reveal a tile in an active Mines game.

    Returns updated game state. If mine hit, game over.
    If safe, multiplier increases. Player can cashout anytime.
    """
    mines = game_state["_mines"]
    grid_size = game_state["grid_size"]
    mine_count = game_state["mine_count"]
    bet_amount = game_state["bet_amount"]
    revealed = list(game_state["safe_tiles_revealed"])

    if tile_index in revealed:
        return {**game_state, "error": "Tile already revealed"}

    if tile_index in mines:
        # BOOM -- hit a mine
        return {
            **game_state,
            "state": "busted",
            "mine_hit": tile_index,
            "mines_revealed": mines,
            "win_amount": 0,
            "net": -bet_amount,
            "dealer_says": _get_dealer_reaction("loss"),
            "celebration": None,
        }

    # Safe tile
    revealed.append(tile_index)
    multiplier = pf.mines_multiplier(len(revealed), mine_count, grid_size)

    # Check if all safe tiles revealed (max win)
    safe_total = grid_size - mine_count
    all_revealed = len(revealed) >= safe_total

    state = "complete" if all_revealed else "active"
    win_amount = int(bet_amount * multiplier) if all_revealed else 0

    return {
        **game_state,
        "state": state,
        "tiles_revealed": len(revealed),
        "safe_tiles_revealed": revealed,
        "current_multiplier": multiplier,
        "potential_win": int(bet_amount * multiplier),
        "mines_revealed": mines if all_revealed else None,
        "win_amount": win_amount,
        "dealer_says": _get_dealer_reaction("streak") if len(revealed) >= 5 else "💎" if len(revealed) < 3 else "Nerves of steel...",
    }


def cashout_mines(game_state: dict) -> dict:
    """Cash out of an active Mines game at the current multiplier."""
    if game_state["state"] != "active":
        return {**game_state, "error": "Game not active"}

    bet = game_state["bet_amount"]
    multiplier = game_state["current_multiplier"]
    win = int(bet * multiplier)

    return {
        **game_state,
        "state": "cashed_out",
        "win_amount": win,
        "net": win - bet,
        "final_multiplier": multiplier,
        "mines_revealed": game_state["_mines"],
        "celebration": _get_celebration(multiplier),
        "dealer_says": _get_dealer_reaction("cashout_early" if multiplier < 5 else "big_win"),
    }
