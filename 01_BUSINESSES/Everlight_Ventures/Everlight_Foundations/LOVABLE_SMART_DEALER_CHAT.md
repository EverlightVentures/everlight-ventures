# LOVABLE: Smart Dealer Chat -- Replace Canned Responses with AI Coach

Paste this into Lovable. This replaces the current dealer chat experience with a smart, context-aware dealer that actually sees the cards and teaches strategy. Do NOT remove any existing features.

**Supabase API:** `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api`
**Headers:** `Content-Type: application/json`, `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
**Authorization:** `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

---

## THE PROBLEM

The current dealer chat uses hardcoded canned responses. When a player asks "how was that hand?" the dealer says "Interesting. How about we focus on the cards?" -- which is dismissive, unhelpful, and repeated for different questions. The dealer has no awareness of the actual cards on the table.

## THE FIX

Replace ALL dealer chat responses with calls to the new `dealer-chat` API action. This action:
- Sees the player's cards, dealer upcard, hand total, and game phase
- Looks up the correct basic strategy play for the exact hand
- Responds with friendly, educational messages
- Handles greetings, hand questions, strategy questions, frustration, and everything in between

---

## IMPLEMENTATION

### 1. Replace the dealer response function

Find wherever the dealer generates a response to player chat messages. It currently uses canned/hardcoded strings. Replace it entirely with this API call:

```typescript
async function getDealerResponse(
  playerId: string,
  playerMessage: string,
  displayName: string,
  tableId: string,
  // Pass current game state so the dealer can see the cards
  gameState?: {
    player_cards?: Array<{ value: number | string; suit: string }>;
    dealer_upcard?: number | string;
    player_total?: number;
    dealer_total?: number;
    phase?: string; // 'betting' | 'playing' | 'dealer_turn' | 'result'
    last_action?: string; // 'hit' | 'stand' | 'double' | 'split'
    last_result?: string; // 'win' | 'lose' | 'push' | 'blackjack' | 'bust'
    hand_count?: number;
  }
): Promise<string> {
  try {
    const res = await fetch(BLACKJACK_API, {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({
        action: 'dealer-chat',
        player_id: playerId,
        message: playerMessage,
        display_name: displayName,
        table_id: tableId,
        game_state: gameState ?? {},
      }),
    });
    if (res.ok) {
      const data = await res.json();
      return data.reply;
    }
    return "Good question! Play a hand and ask me about it -- I'll break down the strategy for you.";
  } catch {
    return "I'm here to help you play your best. Ask me about any hand!";
  }
}
```

### 2. Pass game state with every chat message

When the player sends a chat message, gather the current game state and include it:

```typescript
// When player sends a message in the chat panel:
async function handlePlayerChat(message: string) {
  // Add player message to chat UI immediately
  addChatMessage({ type: 'player', displayName, message, timestamp: Date.now() });

  // Gather current game state from your game logic
  const gameState = {
    player_cards: currentPlayerCards,     // Array of { value, suit }
    dealer_upcard: currentDealerUpcard,   // The dealer's face-up card value
    player_total: currentPlayerTotal,     // Player's current hand total
    dealer_total: currentDealerTotal,     // Dealer's total (if revealed)
    phase: currentGamePhase,             // 'betting', 'playing', 'dealer_turn', 'result'
    last_action: lastPlayerAction,       // What the player last did
    last_result: lastHandResult,         // Result of last completed hand
    hand_count: handsPlayed,             // Total hands this session
  };

  // Get smart dealer response
  const reply = await getDealerResponse(playerId, message, displayName, tableId, gameState);

  // Add dealer response to chat UI
  addChatMessage({ type: 'dealer', displayName: 'Dealer', message: reply, timestamp: Date.now() });
}
```

### 3. Remove ALL canned dealer responses

Delete or remove any hardcoded dealer response arrays, switch statements, or if/else chains that generate dealer messages. Examples of things to DELETE:

- Any array like `["Welcome to the table", "Basic tip: stand on 17+...", "Interesting. How about we focus on the cards?"]`
- Any `Math.random()` selection from a response pool
- Any dealer response that doesn't come from the API

The ONLY dealer messages should come from the `dealer-chat` API call.

### 4. Dealer welcome message on table join

When a player first sits at the table, send an automatic greeting via the API:

```typescript
// On table join / first load
useEffect(() => {
  if (playerId && tableId) {
    getDealerResponse(playerId, "hello", displayName, tableId).then(reply => {
      addChatMessage({ type: 'dealer', displayName: 'Dealer', message: reply, timestamp: Date.now() });
    });
  }
}, [playerId, tableId]);
```

### 5. Auto-prompt after each hand resolves

After every hand result (win/lose/push/bust/blackjack), automatically send a coaching message:

```typescript
// After hand resolves (where you show the win/lose result)
useEffect(() => {
  if (handJustCompleted && playerId) {
    const autoMessage = `how was that hand?`;
    const gameState = {
      player_cards: lastHandPlayerCards,
      dealer_upcard: lastHandDealerUpcard,
      player_total: lastHandPlayerTotal,
      dealer_total: lastHandDealerTotal,
      last_action: lastAction,
      last_result: handResult, // 'win', 'lose', 'push', 'blackjack', 'bust'
    };

    getDealerResponse(playerId, autoMessage, displayName, tableId, gameState).then(reply => {
      addChatMessage({ type: 'dealer', displayName: 'Coach', message: reply, timestamp: Date.now() });
    });
  }
}, [handJustCompleted]);
```

### 6. Render dealer messages with markdown support

The dealer response may contain **bold text** and line breaks. Render dealer messages with basic markdown:

```typescript
function DealerChatBubble({ message }: { message: string }) {
  // Convert **bold** to <strong> and \n to <br>
  const html = message
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-[#D4AF37]">$1</strong>')
    .replace(/\n/g, '<br/>');

  return (
    <div className="flex gap-2 items-start my-2">
      <span className="text-lg">&#127183;</span>
      <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-xl px-3 py-2 max-w-[85%]">
        <span className="text-xs font-bold text-[#D4AF37] block mb-1">Dealer</span>
        <p className="text-sm text-[#E5E5E5] leading-relaxed"
           dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </div>
  );
}
```

---

## WHAT THE NEW EXPERIENCE LOOKS LIKE

**Player:** "Hello"
**Dealer:** "Hey! Welcome to the table. I'm your dealer -- but I'm also here to help you learn. Ask me anything about your hand or basic strategy."

**Player:** "how was that hand?" (had 13 vs dealer 5, won)
**Dealer:** "Your hard 13 vs my 5? Basic strategy says **Stand**. And you took it down -- nice work!"

**Player:** "is there a chart?"
**Dealer:** "Great question! Basic strategy is a mathematically proven chart... **Hard hands:** Stand on 17+. Stand on 13-16 vs dealer 2-6..."

**Player:** "I had 14 vs dealer 6"
**Dealer:** "With a hard 14 vs dealer 6, basic strategy says **Stand**. Stand pat. Let me (the dealer) take the risk of busting."

**Player:** "this game is rigged"
**Dealer:** "Losing streaks feel personal, but they're pure statistics. A 10-hand losing streak happens to EVERY player eventually. Stay with basic strategy and the numbers come back to you."

---

## IMPORTANT
- Do NOT remove existing chat features (emotes, player-to-player chat if it exists)
- Do NOT change the chat panel UI layout -- just replace WHAT the dealer says
- Dealer responses come from the API now, so there may be a brief delay (show a typing indicator: "..." for 500ms before showing the response)
- Keep the existing Strategy Coach post-hand analysis (from LOVABLE_STRATEGY_COACH_PROMPT) separate -- that appears as a Coach badge, this is the conversational chat
