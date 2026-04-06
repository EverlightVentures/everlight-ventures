# LOVABLE PROMPT: Strategy Coach Chat -- Auto-Analyze Every Hand

Paste everything below into Lovable. This adds a **strategy coach** to the blackjack game that automatically analyzes every hand after it resolves, telling the player whether they played correctly according to basic strategy.

**Supabase API:** `POST https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/blackjack-api`
**Headers:** `Content-Type: application/json`, `apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`
**Authorization:** `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww`

Do NOT remove or change any existing features. This is ADDITIVE.

---

## FEATURE: AUTO HAND ANALYSIS IN CHAT

### What It Does

After every hand resolves (win, lose, push, bust, blackjack), the chat panel automatically shows a strategy analysis message from the "Coach". This tells the player:
- What the correct basic strategy play was
- Whether they played correctly or made a mistake
- A brief explanation of why
- Occasional strategy tips

### API Endpoint: analyze-hand

```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({
    action: 'analyze-hand',
    player_cards: [{ value: 10, suit: 'diamonds' }, { value: 9, suit: 'diamonds' }],
    dealer_upcard: 10,        // The dealer's face-up card value (2-10, or 'A' for ace)
    player_total: 19,         // Player's hand total
    action_taken: 'stand',    // What the player did: 'hit', 'stand', 'double', 'split', 'surrender'
    result: 'lose',           // Hand result: 'win', 'lose', 'push', 'blackjack', 'bust'
    dealer_total: 20,         // Dealer's final total
  }),
});

// Response:
{
  correct_action: "S",                    // Raw strategy code
  correct_action_name: "Stand",           // Human-readable action name
  hand_type: "hard",                      // "hard", "soft", or "pair"
  player_total: 19,
  dealer_upcard: "10",
  action_taken: "stand",
  is_correct: true,                       // Did the player follow basic strategy?
  explanation: "You played this hand correctly by basic strategy. Stand on hard 19 vs dealer 10 is the right call. Sometimes the dealer just has a better hand -- that's variance, not a mistake. Keep playing smart.",
  tip: null,                              // Optional bonus tip (or a string)
  result: "lose"
}
```

### API Endpoint: get-tip (random strategy tip)

```typescript
const res = await fetch(BLACKJACK_API, {
  method: 'POST',
  headers: API_HEADERS,
  body: JSON.stringify({ action: 'get-tip' }),
});
// Response: { tip: "Always split Aces and 8s. No exceptions." }
```

---

## IMPLEMENTATION

### 1. Call analyze-hand After Every Hand Resolves

In the game logic, wherever the hand result is determined and displayed (win/lose/push/bust/blackjack), add this call:

```typescript
async function analyzeLastHand(
  playerCards: Array<{ value: number | string; suit: string }>,
  dealerUpcard: number | string,
  playerTotal: number,
  actionTaken: string,
  result: string,
  dealerTotal: number,
) {
  try {
    const res = await fetch(BLACKJACK_API, {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({
        action: 'analyze-hand',
        player_cards: playerCards,
        dealer_upcard: dealerUpcard,
        player_total: playerTotal,
        action_taken: actionTaken,
        result: result,
        dealer_total: dealerTotal,
      }),
    });
    if (res.ok) {
      const analysis = await res.json();
      addCoachMessage(analysis);
    }
  } catch (err) {
    console.warn('Strategy analysis failed:', err);
  }
}
```

Call this function AFTER the hand result animation finishes (after the win/lose/push text is shown). Pass in:
- `playerCards`: Array of the player's initial 2 cards (before hits). Each card has `{ value, suit }`. Value is a number (2-10) or string ('A', 'J', 'Q', 'K').
- `dealerUpcard`: The dealer's visible card value.
- `playerTotal`: Player's final hand total.
- `actionTaken`: The player's PRIMARY decision -- 'hit', 'stand', 'double', or 'split'. If the player hit multiple times, use 'hit'. If they stood immediately, use 'stand'.
- `result`: The hand outcome -- 'win', 'lose', 'push', 'blackjack', or 'bust'.
- `dealerTotal`: The dealer's final hand total.

### 2. Display Coach Messages in the Chat Panel

The existing chat panel (the chat icon in the bottom-right corner) should show Coach messages alongside regular table chat. Coach messages have a distinct appearance:

```typescript
interface CoachMessage {
  type: 'coach';
  is_correct: boolean;
  explanation: string;
  tip: string | null;
  correct_action_name: string;
  hand_type: string;
  player_total: number;
  dealer_upcard: string;
  timestamp: number;
}

function addCoachMessage(analysis: any) {
  const msg: CoachMessage = {
    type: 'coach',
    is_correct: analysis.is_correct,
    explanation: analysis.explanation,
    tip: analysis.tip,
    correct_action_name: analysis.correct_action_name,
    hand_type: analysis.hand_type,
    player_total: analysis.player_total,
    dealer_upcard: analysis.dealer_upcard,
    timestamp: Date.now(),
  };
  // Add to chat messages array
  setChatMessages(prev => [...prev, msg]);
}
```

### 3. Coach Message UI Component

Coach messages look different from regular player chat messages:

```typescript
function CoachMessage({ msg }: { msg: CoachMessage }) {
  return (
    <div className={`mx-2 my-2 p-3 rounded-xl border ${
      msg.is_correct
        ? 'bg-green-900/30 border-green-700/50'
        : 'bg-amber-900/30 border-amber-700/50'
    }`}>
      {/* Coach header */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-bold text-[#D4AF37]">COACH</span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          msg.is_correct
            ? 'bg-green-800 text-green-200'
            : 'bg-amber-800 text-amber-200'
        }`}>
          {msg.is_correct ? 'Correct Play' : 'Mistake'}
        </span>
      </div>

      {/* Strategy verdict */}
      <p className="text-sm text-[#E5E5E5] mb-1">
        Basic Strategy: <span className="font-semibold text-[#D4AF37]">
          {msg.correct_action_name}
        </span> on {msg.hand_type} {msg.player_total} vs dealer {msg.dealer_upcard}
      </p>

      {/* Explanation */}
      <p className="text-xs text-[#B0B0B0] leading-relaxed">{msg.explanation}</p>

      {/* Optional tip */}
      {msg.tip && (
        <div className="mt-2 pt-2 border-t border-white/10">
          <p className="text-xs text-[#D4AF37] italic">Tip: {msg.tip}</p>
        </div>
      )}
    </div>
  );
}
```

### 4. Chat Panel Updates

In the chat panel component, render Coach messages with the special component:

```typescript
{chatMessages.map((msg, i) => (
  msg.type === 'coach'
    ? <CoachMessage key={i} msg={msg} />
    : <PlayerChatBubble key={i} msg={msg} /> // existing chat bubble
))}
```

### 5. Strategy Coach Toggle

Add a toggle in the game settings to enable/disable the coach:

- **Strategy Coach**: ON/OFF toggle (default: ON)
- Store in localStorage: `blackjack_settings.strategy_coach`
- When OFF, skip the `analyzeLastHand()` call entirely
- Show a small graduation cap icon (or book icon) next to the chat icon when Coach is ON

### 6. Random Tips Between Hands

While the player is in the betting phase (waiting to place a bet), occasionally show a random strategy tip in the chat:

```typescript
// Every 3rd hand, show a random tip
const [handCount, setHandCount] = useState(0);

useEffect(() => {
  if (gamePhase === 'betting' && handCount > 0 && handCount % 3 === 0) {
    fetchRandomTip();
  }
}, [gamePhase, handCount]);

async function fetchRandomTip() {
  if (!coachEnabled) return;
  try {
    const res = await fetch(BLACKJACK_API, {
      method: 'POST',
      headers: API_HEADERS,
      body: JSON.stringify({ action: 'get-tip' }),
    });
    if (res.ok) {
      const { tip } = await res.json();
      setChatMessages(prev => [...prev, {
        type: 'coach',
        is_correct: true,
        explanation: tip,
        tip: null,
        correct_action_name: 'Tip',
        hand_type: '',
        player_total: 0,
        dealer_upcard: '',
        timestamp: Date.now(),
      }]);
    }
  } catch {}
}
```

### 7. Coach Badge on Chat Icon

The chat icon in the bottom-right should show a small green dot when a new Coach analysis is available (i.e., the panel is closed and a new analysis came in). When the player opens the chat panel, the dot clears.

---

## EXAMPLES OF WHAT THE COACH SAYS

**Player stands on 19 vs dealer 10, loses (your screenshot):**
> COACH [Correct Play]
> Basic Strategy: **Stand** on hard 19 vs dealer 10
> "You played this hand correctly by basic strategy. Stand on hard 19 vs dealer 10 is the right call. Sometimes the dealer just has a better hand -- that's variance, not a mistake. Keep playing smart."

**Player hits on soft 18 vs dealer 9, wins:**
> COACH [Correct Play]
> Basic Strategy: **Hit** on soft 18 vs dealer 9
> "You played this hand correctly by basic strategy. Hit on soft 18 vs dealer 9 is the right move. Nice win!"
> *Tip: Soft 18 is the most misplayed hand in blackjack. Against a 9, 10, or Ace, you should HIT -- not stand!*

**Player stands on 16 vs dealer 10 (should surrender/hit):**
> COACH [Mistake]
> Basic Strategy: **Surrender (Hit if not allowed)** on hard 16 vs dealer 10
> "Basic strategy says Surrender (Hit if not allowed) on hard 16 vs dealer 10. You chose to stand. This is a common mistake. Surrender gives you the best odds in the long run."
> *Tip: 16 vs a strong dealer card is the toughest hand in blackjack. Surrendering saves you money in the long run.*

**Player splits 10s (should stand):**
> COACH [Mistake]
> Basic Strategy: **Stand** on pair 10 vs dealer 6
> "Basic strategy says Stand on pair 10 vs dealer 6. You chose to split. This is a common mistake. Stand gives you the best odds in the long run."
> *Tip: Never split 10-value cards. 20 is too strong to break up.*

---

## TESTING CHECKLIST

1. After every hand, a Coach message appears in the chat panel
2. Correct plays show green "Correct Play" badge
3. Mistakes show amber "Mistake" badge with what you should have done
4. Coach messages include explanations and occasional tips
5. Coach can be toggled OFF in settings (no analysis messages when OFF)
6. Random tips appear every 3 hands during betting phase
7. Chat icon shows green dot when new Coach message arrives while panel is closed
8. Coach works for all hand types: hard totals, soft totals, pairs, blackjacks, busts
9. Coach correctly identifies surrender situations (16 vs 9/10/A, 15 vs 10)
10. Mobile: Coach messages are readable on small screens, text wraps properly

## IMPORTANT: Do NOT break existing features
- Keep ALL existing chat functionality (player messages, emotes)
- Keep ALL existing game features
- Coach messages are ADDED to the existing chat stream, not replacing it
- The analyze-hand API is a new call that doesn't affect game flow
