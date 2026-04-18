# Vantaris Multiplayer Blackjack -- Implementation Plan
# Resume keyword: "build multiplayer blackjack"

## Overview

Real-time multiplayer blackjack where 2-5 real players sit at the same
table, see each other's cards, bets, reactions, and chat -- all in real
time. Dealer logic runs server-side so nobody can cheat.

## Architecture

```
Player A (browser)                    Player B (browser)
     |                                      |
     v                                      v
Supabase Realtime Channel: "table:{table_id}"
     |           |           |
     |    Supabase DB        |
     |  game_tables          |
     |  game_seats           |
     |  game_hands           |
     |                       |
     +--- Supabase Edge Function: "blackjack-dealer" ---+
          (shuffles, deals, evaluates, settles)
          (runs on every player action)
          (single source of truth for game state)
```

## Database Schema (Supabase)

### game_tables
```sql
CREATE TABLE game_tables (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,               -- "VIP Lounge #1"
  variant text DEFAULT 'classic',   -- classic, vip, lightning, etc.
  min_bet int DEFAULT 100,
  max_bet int DEFAULT 100000,
  max_seats int DEFAULT 5,
  status text DEFAULT 'waiting',    -- waiting, active, settling
  shoe jsonb,                       -- encrypted shoe state (server only)
  phase text DEFAULT 'betting',     -- betting, dealing, player_turn, dealer_turn, settled
  current_seat int DEFAULT 0,       -- whose turn (seat index)
  dealer_hand jsonb DEFAULT '[]',   -- dealer cards
  dealer_total int DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

### game_seats
```sql
CREATE TABLE game_seats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  table_id uuid REFERENCES game_tables(id) ON DELETE CASCADE,
  seat_index int NOT NULL,          -- 0-4
  user_id uuid REFERENCES auth.users(id),
  display_name text,
  avatar_url text,
  is_vip boolean DEFAULT false,
  chips int DEFAULT 0,
  bet int DEFAULT 0,
  side_bets jsonb DEFAULT '{}',
  cards jsonb DEFAULT '[]',
  hand_total int DEFAULT 0,
  status text DEFAULT 'waiting',    -- waiting, betting, acting, standing, busted, blackjack, settled
  outcome text,                     -- win, loss, push, blackjack, bust, surrender
  payout int DEFAULT 0,
  joined_at timestamptz DEFAULT now(),
  UNIQUE(table_id, seat_index)
);
```

### game_hands (history)
```sql
CREATE TABLE game_hands (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  table_id uuid REFERENCES game_tables(id),
  hand_number int,
  seats_snapshot jsonb,             -- full state at settlement
  dealer_hand jsonb,
  dealer_total int,
  settled_at timestamptz DEFAULT now()
);
```

## Edge Function: blackjack-dealer

Server-side game engine. Handles ALL game logic. Clients NEVER touch
cards, shoes, or settlement. They only send actions.

### Endpoints (via POST body action field):

```
{ action: "join", table_id, seat_index }
  - Validates seat is empty
  - Adds player to game_seats
  - Broadcasts "player_joined" to channel

{ action: "bet", table_id, amount, side_bets }
  - Validates it's betting phase
  - Validates player has enough chips
  - Deducts chips, records bet
  - When all seated players have bet, auto-starts deal

{ action: "deal", table_id }
  - Only host or auto-triggered after all bets
  - Shuffles/draws from shoe
  - Deals 2 cards to each seat + dealer
  - Checks for naturals
  - Sets phase to player_turn, current_seat to first active seat
  - Broadcasts full state

{ action: "hit", table_id }
  - Validates it's this player's turn
  - Draws card, updates hand
  - Checks bust/charlie
  - If bust/charlie, advances to next seat
  - Broadcasts updated state

{ action: "stand", table_id }
  - Validates it's this player's turn
  - Advances to next seat or dealer turn
  - Broadcasts

{ action: "double", table_id }
  - Validates chips, turn
  - Doubles bet, draws one card, stands
  - Broadcasts

{ action: "split", table_id }
  - Validates pair, chips, turn
  - Creates split hand
  - Broadcasts

{ action: "insurance", table_id, take: boolean }
  - Validates dealer ace showing
  - Deducts half bet if taken
  - Broadcasts

{ action: "leave", table_id }
  - Removes player from seat
  - Refunds any active bet if in betting phase
  - Broadcasts "player_left"
```

### Dealer Turn Logic (runs in edge function):
```
When all player seats are resolved (stood, busted, blackjack):
1. Reveal dealer hole card
2. Hit until 17+ (soft 17 rule per table variant)
3. Evaluate each seat vs dealer
4. Calculate payouts (including side bets)
5. Credit chips to winners
6. Record hand in game_hands
7. Reset table to betting phase
8. Broadcast final state
```

## Realtime Channel Structure

Each table subscribes to: `realtime:table:{table_id}`

### Broadcast Events:
```
table_state_update  -- full state refresh (seats, cards, phase)
player_joined       -- { seat_index, name, avatar_url }
player_left         -- { seat_index }
player_action       -- { seat_index, action, data }
dealer_action       -- { action, cards, total }
chat_message        -- { seat_index, text, emoji }
emoji_reaction      -- { seat_index, emoji, target_seat }
hand_settled        -- { results: [{ seat, outcome, payout }] }
```

### Presence:
```
Each player tracks:
{
  user_id, display_name, avatar_url, seat_index,
  chips, is_vip, online_since
}
```

## Client Changes

### New Components:
- `MultiplayerTable.tsx` -- replaces single-player game when table_id is set
- `SeatRenderer.tsx` -- renders a single seat (cards, bet, avatar, status)
- `TableChat.tsx` -- real-time chat panel for the table
- `TurnTimer.tsx` -- countdown when it's your turn (30s default, 15s warning)
- `JoinTable.tsx` -- seat picker when entering a multiplayer table

### Modified Components:
- `BettingLayout.tsx` -- send bet action to edge function instead of local store
- `ActionButtons.tsx` -- send hit/stand/double/split to edge function
- `SocialBar.tsx` -- broadcast emoji/gifts via Realtime channel

### State Management:
- New `useMultiplayerStore` (Zustand) that subscribes to Realtime channel
- Single-player store stays for solo play
- Game page detects `?multiplayer=true` or table_id param to switch modes

## Turn Timer

- 30 seconds per turn
- At 15s: yellow warning pulse
- At 5s: red countdown
- At 0s: auto-stand
- AFK for 3 consecutive turns: auto-kicked from seat

## Anti-Cheat

1. Shoe state stored encrypted server-side (players never see upcoming cards)
2. All card dealing happens in edge function
3. Bet validation server-side (can't bet more than you have)
4. Turn validation (can't act when it's not your turn)
5. Rate limiting (max 1 action per second)
6. Hand history audit log

## Monetization

- Multiplayer tables are FREE (social casino model)
- Revenue from GC package purchases (Stripe)
- Premium table environments cost gems
- VIP tables require VIP status
- Spectator mode is free (watch but can't play)

## Implementation Order

### Phase 1: Foundation (1 session)
1. Create Supabase tables (game_tables, game_seats, game_hands)
2. Build blackjack-dealer edge function (deal, hit, stand, settle)
3. Build useMultiplayerStore with Realtime subscription
4. Basic 2-player test (you + tapizme@gmail.com)

### Phase 2: UI (1 session)
5. MultiplayerTable component (renders all seats from server state)
6. SeatRenderer with real avatars, Google profile pics, names
7. Turn timer with visual countdown
8. Join/leave flow

### Phase 3: Social (1 session)
9. Real-time chat
10. Emoji reactions broadcast to all players
11. Gift/troll animations between real players
12. Spectator mode

### Phase 4: Polish (1 session)
13. Table lobby showing active tables with player counts
14. Auto-matchmaking (join a table with open seats)
15. Private tables (invite link)
16. Hand history viewer
17. Anti-cheat hardening

## Files to Create
```
src/lib/multiplayer-store.ts        -- Zustand store + Realtime subscription
src/lib/multiplayer-types.ts        -- Shared types
src/app/play/blackjack/multi/page.tsx -- Multiplayer game page
src/components/blackjack/MultiplayerTable.tsx
src/components/blackjack/SeatRenderer.tsx
src/components/blackjack/TurnTimer.tsx
src/components/blackjack/TableChat.tsx
supabase/functions/blackjack-dealer/index.ts -- Server-side game engine
supabase/migrations/multiplayer_tables.sql
```

## Resume Instructions

Start a new session and say: "build multiplayer blackjack"

Read this file first: 06_DEVELOPMENT/vantaris/MULTIPLAYER_PLAN.md
Read the existing engine: src/lib/blackjack-engine.ts (reuse evaluation logic)
Read the existing store: src/lib/blackjack-store.ts (reference for state shape)

Begin with Phase 1: Supabase tables + edge function + store.
Test with two browser tabs before building UI.
