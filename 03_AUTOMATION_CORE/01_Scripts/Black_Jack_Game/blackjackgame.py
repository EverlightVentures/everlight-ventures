import random
import sqlite3
import os
from colorama import Fore, Style

# Define suits and emotes
suits = {
    'Hearts': f"{Fore.RED}♥{Style.RESET_ALL}",
    'Diamonds': f"{Fore.RED}♦{Style.RESET_ALL}",
    'Clubs': f"{Fore.BLACK}♣{Style.RESET_ALL}",
    'Spades': f"{Fore.BLACK}♠{Style.RESET_ALL}"
}

# Ranks and values
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
values = {rank: min(index + 2, 10) for index, rank in enumerate(ranks[:-1])}
values['Ace'] = 11  # Ace is worth 11 by default

# Format card display
def format_card(card):
    return f"{card['rank']} {suits[card['suit']]}"

# Create, shuffle, and deal from deck
def create_deck(num_decks=1):
    return [{'rank': rank, 'suit': suit, 'value': values[rank]} for rank in ranks for suit in suits] * num_decks

def shuffle_deck(deck):
    random.shuffle(deck)
    return deck

def render_table(dealer_hand, player_seats):
    table_width = 80
    print("=" * table_width)
    print(f"{' ' * (table_width // 2 - 8)}| Dealer: {', '.join(format_card(card) for card in dealer_hand)} |")
    print("-" * table_width)

    base_names = ["4th Base", "3rd Base", "2nd Base", "1st Base"]
    for i, player in enumerate(reversed(player_seats)):
        print(f"{base_names[i]:<10} | {player['name']:<10} | Cards: {', '.join(format_card(card) for card in player['cards'])} | Wager: ${player['wager']}")
    print("=" * table_width)

def deal_cards(deck, num=2):
    return [deck.pop() for _ in range(num)]

# Calculate hand value
def calculate_hand_value(hand):
    value = sum(card['value'] for card in hand)
    aces = sum(1 for card in hand if card['rank'] == 'Ace')
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

# Database operations
def init_db():
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'game.db')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 100.0,
                rounds INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0
            )
        ''') 


  # Check for missing columns and add them
        cursor.execute("PRAGMA table_info(players)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'rounds' not in columns:
            cursor.execute("ALTER TABLE players ADD COLUMN rounds INTEGER NOT NULL DEFAULT 0")
        if 'wins' not in columns:
            cursor.execute("ALTER TABLE players ADD COLUMN wins INTEGER NOT NULL DEFAULT 0")
        if 'losses' not in columns:
            cursor.execute("ALTER TABLE players ADD COLUMN losses INTEGER NOT NULL DEFAULT 0")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                bet_amount REAL NOT NULL,
                result TEXT NOT NULL,
                winnings REAL NOT NULL,
                FOREIGN KEY(player_id) REFERENCES players(id)
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        conn.close()


#define add player

def add_player(name):
    try:
        conn = sqlite3.connect('game.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO players (name) VALUES (?)", (name,))
        player_id = cursor.lastrowid
        conn.commit()
        return player_id
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close() 
        
def get_balance(player_id):
    try:
        conn = sqlite3.connect('game.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM players WHERE id = ?", (player_id,))
        balance = cursor.fetchone()
        return balance[0] if balance else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def update_balance(player_id, new_balance):
    try:
        conn = sqlite3.connect('game.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET balance = ? WHERE id = ?", (new_balance, player_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def update_player_stats(player_id, result):
    try:
        conn = sqlite3.connect('game.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE players SET rounds = rounds + 1 WHERE id = ?", (player_id,))
        if result == "Win":
            cursor.execute("UPDATE players SET wins = wins + 1 WHERE id = ?", (player_id,))
        elif result == "Lose":
            cursor.execute("UPDATE players SET losses = losses + 1 WHERE id = ?", (player_id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

# Display results
def display_results(player_hand, dealer_hand, player_value, dealer_value, result):
    print("\nFinal Results:")
    print(f"Player Hand: {', '.join(format_card(card) for card in player_hand)} (Sum: {player_value})")
    print(f"Dealer Hand: {', '.join(format_card(card) for card in dealer_hand)} (Sum: {dealer_value})")
    print(f"Result: {Fore.GREEN if result == 'Win' else Fore.RED}{result}{Style.RESET_ALL}")

def setup_game():
    print("\nSelect Deck Type:")
    print("1. Single Deck")
    print("2. Double Deck")
    print("3. 8 Decks")
    deck_choice = int(input("Enter choice (1/2/3): "))
    num_decks = {1: 1, 2: 2, 3: 8}[deck_choice]

    print("\nDo you want to play alone or with others?")
    print("1. Play Alone")
    print("2. Play with Others")
    player_choice = int(input("Enter choice (1/2): "))

    num_players = 1
    player_seats = []
    if player_choice == 2:
        num_players = int(input("How many players (including yourself)? (2-5): "))
        while num_players < 2 or num_players > 5:
            num_players = int(input("Please choose between 2 and 5 players: "))

    print("\nSetting up the table...")
    for i in range(num_players):
        if i == 0:
            name = input("Enter your name: ")
            player_id = add_player(name)
            player_seats.append({'id': player_id, 'name': name, 'balance': 100.0, 'wager': 0, 'cards': []})
        else:
            player_seats.append({'id': None, 'name': f"Bot-{i}", 'balance': 100.0, 'wager': 0, 'cards': []})

    return num_decks, player_seats
#sync_balance

def sync_balance(player):
    player['balance'] = get_balance(player['id'])  # Sync with database


# Play a round of blackjack
def play_round(player, deck, main_bet, war_bet=0):
    balance = get_balance['balance']
    if balance < main_bet + war_bet:
        print("Insufficient balance.")
        return

    # Initial dealing
    player_hand = deal_cards(deck, num=2)
    dealer_hand = deal_cards(deck, num=2)
    player_value = calculate_hand_value(player_hand)
    dealer_value = calculate_hand_value(dealer_hand)

    print(f"Your cards: {format_card(player_hand[0])}, {format_card(player_hand[1])} (Sum: {player_value})")
    print(f"Dealer's visible card: {format_card(dealer_hand[1])}")


for player in player_seats:
    print(f"Player: {player['name']}, Balance: ${player['balance']}")
    main_bet = float(input(f"{player['name']}, enter your main bet: "))
    war_bet = float(input(f"{player['name']}, enter your war bet (0 to skip): "))
    play_round(player, deck, main_bet, war_bet)
    update_balance(player['id'], player['balance'])
    sync_balance(player)
    
    # War feature
    if war_bet > 0:
        print("\nWar Bet!")
        player_war_card = player_hand[1]  # Second card is the player's war card
        dealer_war_card = dealer_hand[1]  # Dealer's visible card is their war card
        print(f"Your war card: {format_card(player_war_card)}")
        print(f"Dealer's war card: {format_card(dealer_war_card)}")

        if player_war_card['value'] > dealer_war_card['value']:
            print(f"{Fore.GREEN}You win the war bet!{Style.RESET_ALL}")
            war_winnings = war_bet * 2
            print(f"You won {war_winnings} 💵 from the war bet.")
            reinvest = input(f"Do you want to reinvest the {war_winnings} 💵 into your main bet? (y/n): ").lower()
            if reinvest == 'y':
                main_bet += war_winnings
                print(f"Your new main bet is: {main_bet} 💵.")
            else:
                balance += war_winnings
        else:
            print(f"{Fore.RED}You lose the war bet.{Style.RESET_ALL}")

    # Player's turn
    while player_value < 21:
        action = input("Hit or Stand? (h/s): ").lower()
        if action == 'h':
            player_hand.extend(deal_cards(deck, num=1))
            player_value = calculate_hand_value(player_hand)
            print(f"Your Hand: {', '.join(format_card(card) for card in player_hand)} (Sum: {player_value})")
        elif action == 's':
            break

    # Dealer's turn
    while dealer_value < 17:
        dealer_hand.extend(deal_cards(deck, num=1))
        dealer_value = calculate_hand_value(dealer_hand)

    # Determine winner
    if player_value > 21:
        result = "Lose"
    elif dealer_value > 21 or player_value > dealer_value:
        result = "Win"
    elif player_value < dealer_value:
        result = "Lose"
    else:
        result = "Tie"

    # Display results and update stats
    display_results(player_hand, dealer_hand, player_value, dealer_value, result)
    update_player_stats(player_id, result)
    update_balance(player_id, balance - main_bet + (main_bet * 2 if result == "Win" else 0))

if __name__ == "__main__":
    init_db()
    print("WELCOME TO BLACKJACK!")
    num_decks, player_seats = setup_game()  # Assign `player_seats`
    deck = shuffle_deck(create_deck(num_decks))

    while True:
        for player in player_seats:
            print(f"{player['name']}'s Balance: ${player['balance']}")
            main_bet = float(input(f"{player['name']}, enter your main bet: "))
            war_bet = float(input(f"{player['name']}, enter your war bet (0 to skip): "))
            play_round(player, deck, main_bet, war_bet)

        again = input("Play another round? (y/n): ").lower()
        if again != 'y':
            print("Thanks for playing!")
            break

