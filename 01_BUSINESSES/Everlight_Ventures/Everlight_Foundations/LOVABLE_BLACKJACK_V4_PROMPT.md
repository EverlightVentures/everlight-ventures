# LOVABLE PROMPT: Everlight Blackjack V4 - ElevenLabs Voice + Bot Behavior + Table Spacing

Paste everything below the line into Lovable. This builds ON TOP of V3.
Do not remove any existing features. This adds:
1. ElevenLabs hyper-realistic dealer voice (replaces robotic Web Speech API)
2. NPC bots behave like real players (human names, varying chip counts, random sit/walk)
3. Table layout spacing fixes (cards and seats no longer overlap)

---

## PART 1: ELEVENLABS DEALER VOICE

### Problem
The dealer currently uses the browser's Web Speech API which sounds robotic.
Replace all dealer speech with ElevenLabs API calls.

### Implementation

Add this SpeechService to your Supabase Edge Function (or call directly from the frontend):

The dealer speaks in these moments:
- Game start: "Place your bets."
- Cards dealt: "Cards are dealt. Player shows [value]."
- Player bust: "Bust. Dealer wins."
- Dealer reveal: "Dealer shows [value]."
- Player blackjack: "Blackjack! Congratulations."
- Player wins: "Winner winner."
- Push: "Push. No winner this hand."
- Legend greeting: "Welcome back, Legend [name]. The table just got interesting."

Frontend JavaScript - replace any existing `speechSynthesis.speak()` calls:

```javascript
// speech_client.js - drop this into your Lovable project
const SPEECH_CACHE = new Map();

async function dealerSpeak(text) {
  if (SPEECH_CACHE.has(text)) {
    playAudioBlob(SPEECH_CACHE.get(text));
    return;
  }

  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

  try {
    const res = await fetch(`${supabaseUrl}/functions/v1/dealer-speak`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${supabaseKey}`,
      },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error(`TTS error: ${res.status}`);

    const blob = await res.blob();
    SPEECH_CACHE.set(text, blob);
    playAudioBlob(blob);
  } catch (err) {
    console.warn('ElevenLabs TTS failed, falling back to browser TTS:', err);
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 0.8;
    speechSynthesis.speak(utterance);
  }
}

function playAudioBlob(blob) {
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.play();
  audio.onended = () => URL.revokeObjectURL(url);
}

// Pre-warm the cache on page load for zero-latency dealer phrases
const DEALER_PHRASES = [
  "Place your bets.",
  "Cards are dealt.",
  "Bust. Dealer wins.",
  "Dealer stands.",
  "Blackjack! Congratulations.",
  "Winner winner.",
  "Push. No winner this hand.",
  "No more bets.",
];

window.addEventListener('load', () => {
  DEALER_PHRASES.forEach(phrase => dealerSpeak(phrase).catch(() => {}));
});
```

Supabase Edge Function (create at supabase/functions/dealer-speak/index.ts):

```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const ELEVENLABS_API_KEY = Deno.env.get("ELEVENLABS_API_KEY") ?? "";
const DEALER_VOICE_ID    = Deno.env.get("EL_DEALER_VOICE") ?? "pNInz6obpgDQGcFmaJgB";

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const { text } = await req.json();
  if (!text) return new Response("Missing text", { status: 400 });

  const res = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${DEALER_VOICE_ID}`,
    {
      method: "POST",
      headers: {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        model_id: "eleven_flash_v2",
        voice_settings: {
          stability: 0.60,
          similarity_boost: 0.85,
          style: 0.20,
          use_speaker_boost: true,
        },
      }),
    }
  );

  if (!res.ok) {
    return new Response("ElevenLabs error", { status: 502 });
  }

  const audio = await res.arrayBuffer();
  return new Response(audio, {
    headers: {
      "Content-Type": "audio/mpeg",
      "Access-Control-Allow-Origin": "*",
    },
  });
});
```

Add these env vars to your Supabase project secrets:
- ELEVENLABS_API_KEY  (from elevenlabs.io)
- EL_DEALER_VOICE    (default: pNInz6obpgDQGcFmaJgB = Adam voice)

Replace ALL instances of `speechSynthesis.speak()` with `dealerSpeak()` throughout the codebase.

---

## PART 2: NPC BOT BEHAVIOR OVERHAUL

### Problem
- Bots show the name "Bot" or "Bot-1" - immersion-breaking
- All bots start with exactly $100 - unrealistic
- Bots sit at the table indefinitely - unrealistic
- Bots do not actively play (no visible decision-making)

### Fix: Bot Names

Replace all hardcoded bot/NPC name generation with this pool:

```javascript
const NPC_NAME_POOL = [
  "Marcus", "DeShawn", "Aaliyah", "Jaylen", "Keisha", "Darius", "Imani",
  "Tremaine", "Latoya", "Malik", "Brianna", "Jamal", "Tanisha", "Elijah",
  "Monique", "Xavier", "Shanice", "Devon", "Kamila", "Tyrone", "Destiny",
  "Isaiah", "Nadia", "Quinton", "Zara", "Reginald", "Tamara", "Calvin",
  "Precious", "Derrick", "Amara", "Jordan", "Simone", "Anthony", "Crystal",
];

const _usedNpcNames = new Set();

function pickNpcName() {
  const available = NPC_NAME_POOL.filter(n => !_usedNpcNames.has(n));
  if (available.length === 0) _usedNpcNames.clear();
  const pool = available.length > 0 ? available : NPC_NAME_POOL;
  const name = pool[Math.floor(Math.random() * pool.length)];
  _usedNpcNames.add(name);
  return name;
}
```

### Fix: Bot Chip Count

NPCs start with randomized chip stacks (not all $100):

```javascript
function npcStartingChips() {
  const tiers   = [50,  75,  100, 150, 200, 300, 500];
  const weights = [0.10, 0.15, 0.30, 0.20, 0.15, 0.07, 0.03];
  const rand = Math.random();
  let cumulative = 0;
  for (let i = 0; i < tiers.length; i++) {
    cumulative += weights[i];
    if (rand <= cumulative) return tiers[i];
  }
  return 100;
}
```

### Fix: Bot Sit / Walk Timing

NPCs join and leave with random timing so the table feels alive:

```javascript
const NPC_SIT_RANGE  = [3 * 60 * 1000, 12 * 60 * 1000]; // 3-12 min before joining
const NPC_STAY_RANGE = [5 * 60 * 1000, 25 * 60 * 1000]; // 5-25 min at the table

function scheduleNpcArrivals(tableSeats, maxNpcs = 3) {
  const numNpcs = Math.floor(Math.random() * (maxNpcs + 1));

  for (let i = 0; i < numNpcs; i++) {
    const arrivalDelay = NPC_SIT_RANGE[0]
      + Math.random() * (NPC_SIT_RANGE[1] - NPC_SIT_RANGE[0]);
    const stayDuration = NPC_STAY_RANGE[0]
      + Math.random() * (NPC_STAY_RANGE[1] - NPC_STAY_RANGE[0]);

    setTimeout(() => {
      const npc = {
        id: `npc_${Date.now()}`,
        name: pickNpcName(),
        chips: npcStartingChips(),
        isNpc: true,
        avatar: randomNpcAvatar(),
      };
      seatNpc(npc, tableSeats);
      setTimeout(() => removeNpc(npc.id, tableSeats), stayDuration);
    }, arrivalDelay);
  }
}

function randomNpcAvatar() {
  const skinTones = ['#F5CBA7', '#E59866', '#CA8A5B', '#A0522D', '#6B3A2A', '#3D1C02'];
  return {
    skin: skinTones[Math.floor(Math.random() * skinTones.length)],
    expression: ['confident', 'serious', 'casual'][Math.floor(Math.random() * 3)],
  };
}
```

### Fix: Bots Actively Play

When it is the NPC's turn, animate their decision with a delay so they look like they are thinking:

```javascript
async function npcTakeTurn(npc, hand, dealerUpcard) {
  const thinkTime = 1200 + Math.random() * 2000; // 1.2-3.2 second think delay
  await sleep(thinkTime);

  const value = handValue(hand);
  const upcard = dealerUpcard.value;

  // Basic strategy (simplified)
  let action;
  if (value <= 11) {
    action = 'hit';
  } else if (value >= 17) {
    action = 'stand';
  } else if (value === 16 && upcard >= 7) {
    action = 'hit';
  } else if (value >= 13 && upcard <= 6) {
    action = 'stand';
  } else {
    action = 'hit';
  }

  showNpcThinking(npc.id, action); // animate thinking bubble
  return action;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
```

---

## PART 3: TABLE LAYOUT SPACING FIX

### Problem
The table looks squishy. Player seats, card areas, chip stacks, and name labels overlap
or crunch together, especially with 3+ players at the table.

### Fix: Table CSS Overhaul

Apply these spacing rules to the table container and seat elements:

```css
/* Table container - give it breathing room */
.blackjack-table {
  min-height: 520px;
  padding: 24px 32px;
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 16px;
}

/* Dealer area - top zone */
.dealer-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.12);
  min-height: 120px;
}

/* Player seats row - bottom zone */
.player-seats {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: nowrap;
  padding-top: 16px;
  min-height: 180px;
}

/* Individual seat */
.player-seat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 120px;
  max-width: 160px;
  flex: 1;
}

/* Card hand within a seat - no overlap */
.player-hand {
  display: flex;
  flex-direction: row;
  gap: 6px;
  flex-wrap: nowrap;
  justify-content: center;
  min-height: 90px;
}

/* Individual card - fixed size, no squishing */
.playing-card {
  width: 60px;
  height: 84px;
  min-width: 60px;
  border-radius: 6px;
  flex-shrink: 0;
}

/* Player name label */
.seat-label {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

/* Chip count */
.seat-chips {
  font-size: 12px;
  white-space: nowrap;
}

/* Bet circle */
.bet-circle {
  width: 56px;
  height: 56px;
  min-width: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}

/* Responsive: 5 players - shrink cards, keep spacing */
@media (max-width: 700px) {
  .player-seats {
    gap: 10px;
  }
  .player-seat {
    min-width: 80px;
    max-width: 110px;
  }
  .playing-card {
    width: 44px;
    height: 62px;
    min-width: 44px;
  }
  .seat-label {
    font-size: 11px;
    max-width: 100px;
  }
  .bet-circle {
    width: 42px;
    height: 42px;
    font-size: 11px;
  }
}

/* 6+ cards in a hand - fan them with overlap */
.player-hand.many-cards .playing-card:not(:first-child) {
  margin-left: -20px;
}
```

---

## PART 4: AUDIOBOOK SAMPLE PLAYER ON PUBLISHING PAGE

Add this audio player component to the /publishing route for each book.
The samples are pre-generated trailer_sample.mp3 files stored in Supabase Storage.

```javascript
// BookSamplePlayer.jsx
function BookSamplePlayer({ bookId, title, supabaseUrl, bucketName }) {
  const [playing, setPlaying] = React.useState(false);
  const [loaded, setLoaded]   = React.useState(false);
  const audioRef = React.useRef(null);

  const sampleUrl = `${supabaseUrl}/storage/v1/object/public/${bucketName}/${bookId}/trailer_sample.mp3`;

  function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play();
      setPlaying(true);
    }
  }

  return (
    <div className="sample-player">
      <audio
        ref={audioRef}
        src={sampleUrl}
        onEnded={() => setPlaying(false)}
        onCanPlayThrough={() => setLoaded(true)}
        preload="metadata"
      />
      <button
        onClick={togglePlay}
        disabled={!loaded}
        className="sample-play-btn"
        aria-label={playing ? `Pause ${title} sample` : `Play ${title} sample`}
      >
        {playing ? '|| Pause' : '> Play Sample Audio'}
      </button>
      <span className="sample-label">Sample audio book</span>
    </div>
  );
}
```

Upload the generated trailer_sample.mp3 files to Supabase Storage:
- Bucket: audio-assets
- Path: {book_id}/trailer_sample.mp3
  - sam_1/trailer_sample.mp3
  - sam_2/trailer_sample.mp3
  - btv/trailer_sample.mp3

---

## DO NOT BREAK EXISTING FEATURES

- All V3 features remain (daily rewards, avatar system, VIP tiers, tournaments, etc.)
- All Supabase API endpoints remain unchanged
- The ElevenLabs voice is additive - browser TTS is kept as fallback
- Bot changes are purely cosmetic / behavioral, no database schema changes needed
