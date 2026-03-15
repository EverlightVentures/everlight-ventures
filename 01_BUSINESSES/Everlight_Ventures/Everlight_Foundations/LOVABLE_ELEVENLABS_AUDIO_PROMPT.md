# LOVABLE PROMPT: ElevenLabs Audio Integration + Publishing Audio Cleanup

Paste everything below into Lovable. This is a focused update that:
1. Integrates ElevenLabs dealer voice into the blackjack game
2. Cleans up the publishing audiobook previews -- removes old previews, keeps only the Hollywood trailer sample renamed to "Sample Audiobook"
3. Ensures the dealer voice and audiobook samples both work with fallback handling

Do NOT remove or change any existing features beyond what is specifically described below.

---

## PART 1: ELEVENLABS DEALER VOICE (Blackjack)

### What's Changing
Replace the browser's robotic Web Speech API (`speechSynthesis.speak()`) with ElevenLabs hyper-realistic voice for the blackjack dealer. Keep browser TTS as a silent fallback.

### Dealer Voice Edge Function

A new Supabase edge function `dealer-speak` handles the TTS. It's already deployed. The frontend calls it like this:

```typescript
// Dealer voice client -- add this to the blackjack game module
const SPEECH_CACHE = new Map<string, Blob>();
const SUPABASE_URL = 'https://jdqqmsmwmbsnlnstyavl.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww';

// Master volume control (0.0 to 1.0) -- respect user's sound preference
let dealerVoiceEnabled = true;
let dealerVolume = 0.8;

async function dealerSpeak(text: string) {
  if (!dealerVoiceEnabled) return;

  // Check cache first for zero-latency common phrases
  if (SPEECH_CACHE.has(text)) {
    playAudioBlob(SPEECH_CACHE.get(text)!, dealerVolume);
    return;
  }

  try {
    const res = await fetch(`${SUPABASE_URL}/functions/v1/dealer-speak`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${SUPABASE_KEY}`,
      },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) throw new Error(`TTS error: ${res.status}`);

    const blob = await res.blob();
    SPEECH_CACHE.set(text, blob);
    playAudioBlob(blob, dealerVolume);
  } catch (err) {
    console.warn('ElevenLabs TTS failed, falling back to browser TTS:', err);
    // Silent fallback to browser speech synthesis
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 0.8;
      utterance.volume = dealerVolume;
      speechSynthesis.speak(utterance);
    }
  }
}

function playAudioBlob(blob: Blob, volume: number) {
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.volume = volume;
  audio.play().catch(() => {}); // Catch autoplay restrictions gracefully
  audio.onended = () => URL.revokeObjectURL(url);
}
```

### Pre-warm Cache on Game Load

When the blackjack page loads, silently pre-fetch the most common dealer phrases so they play instantly during gameplay:

```typescript
const DEALER_PHRASES = [
  "Place your bets.",
  "No more bets.",
  "Cards are dealt.",
  "Bust. Dealer wins.",
  "Dealer stands.",
  "Blackjack! Congratulations.",
  "Winner winner.",
  "Push. No winner this hand.",
  "Insurance?",
  "Dealer busts. Players win.",
];

// Pre-warm on page load (fires silently in background, no audio plays)
async function prewarmDealerVoice() {
  for (const phrase of DEALER_PHRASES) {
    try {
      const res = await fetch(`${SUPABASE_URL}/functions/v1/dealer-speak`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${SUPABASE_KEY}`,
        },
        body: JSON.stringify({ text: phrase }),
      });
      if (res.ok) {
        const blob = await res.blob();
        SPEECH_CACHE.set(phrase, blob);
      }
    } catch {}
  }
}

// Call this when the blackjack component mounts
// Use requestIdleCallback or setTimeout to avoid blocking the UI
if ('requestIdleCallback' in window) {
  requestIdleCallback(() => prewarmDealerVoice());
} else {
  setTimeout(() => prewarmDealerVoice(), 2000);
}
```

### When the Dealer Speaks

Replace ALL existing `speechSynthesis.speak()` calls in the blackjack game with `dealerSpeak()`. The dealer should speak at these moments:

| Game Moment | Dealer Says |
|-------------|-------------|
| Betting phase starts | "Place your bets." |
| Betting phase ends | "No more bets." |
| Cards dealt | "Cards are dealt. Player shows {playerTotal}." |
| Player gets blackjack | "Blackjack! Congratulations." |
| Player busts | "Bust. Dealer wins." |
| Player stands | *(no speech -- just proceeds)* |
| Player doubles down | "Doubling down." |
| Dealer reveals hole card | "Dealer shows {dealerTotal}." |
| Dealer busts | "Dealer busts. Players win." |
| Dealer stands | "Dealer stands on {dealerTotal}." |
| Player wins | "Winner winner." |
| Push | "Push. No winner this hand." |
| Insurance offered | "Insurance?" |
| Legend player sits down | "Welcome back, Legend {name}. The table just got interesting." |

### Voice Toggle in Settings

Add a toggle in the blackjack settings/menu:

- **Dealer Voice**: ON/OFF toggle (default: ON)
- **Voice Volume**: Slider 0-100% (default: 80%)
- Store preferences in localStorage under `blackjack_settings`:
  ```json
  { "dealer_voice": true, "dealer_volume": 0.8 }
  ```
- When toggled OFF, `dealerSpeak()` returns immediately without making API calls
- Show a small speaker icon next to the dealer's name plate at the table -- muted icon when voice is OFF

### Fallback Handling

If the `dealer-speak` edge function is not yet deployed or returns errors:
- Fall back to browser `speechSynthesis` automatically (already handled in the code above)
- If browser TTS is also unavailable, fail silently -- no errors shown to the player
- Log a `console.warn` for debugging but never show TTS errors in the UI

---

## PART 2: PUBLISHING PAGE AUDIO CLEANUP

### What's Changing

The Adventures with Sam & Robo book pages currently reference multiple audio previews (Standard, Deep, etc.). Remove ALL old preview references. Keep ONLY the Hollywood trailer sample and rename its display label to **"Sample Audiobook"**.

### For each book on /publishing/sam-and-robo:

**Book 1 -- Sam's First Superpower:**
- Remove any old audio preview buttons/players (Standard preview, Deep preview, etc.)
- Keep ONE audio player with the Hollywood trailer sample
- Display label: **"Sample Audiobook"** (not "Hollywood preview" or "trailer_sample")
- Audio source: `https://jdqqmsmwmbsnlnstyavl.supabase.co/storage/v1/object/public/audio-assets/sam_1/trailer_sample.mp3`
- If the file doesn't exist yet in Supabase Storage, show the player in a disabled state with text: "Sample coming soon"

**Book 2 -- Sam's Second Superpower:**
- Same treatment as Book 1
- Audio source: `https://jdqqmsmwmbsnlnstyavl.supabase.co/storage/v1/object/public/audio-assets/sam_2/trailer_sample.mp3`

**Book 3-5 (if they have preview audio):**
- Same treatment -- one "Sample Audiobook" player per book, remove any legacy previews

### For /publishing/beyond-the-veil:

- Keep the existing prologue player (`ch00_00_prologue.mp3`) -- this is a chapter preview, not a trailer
- Rename its label from whatever it currently says to **"Listen to the Prologue"**
- Add a SECOND player below it with the Hollywood trailer: **"Sample Audiobook"**
- Audio source: `https://jdqqmsmwmbsnlnstyavl.supabase.co/storage/v1/object/public/audio-assets/btv/trailer_sample.mp3`

### Audio Player Component

Use this consistent audio player design across ALL publishing pages:

```typescript
interface BookSamplePlayerProps {
  title: string;        // e.g., "Sample Audiobook" or "Listen to the Prologue"
  audioUrl: string;     // Supabase Storage URL
  bookTitle: string;    // e.g., "Sam's First Superpower"
}

function BookSamplePlayer({ title, audioUrl, bookTitle }: BookSamplePlayerProps) {
  const [playing, setPlaying] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
      setPlaying(false);
    } else {
      audio.play().catch(() => {});
      setPlaying(true);
    }
  };

  return (
    <div className="flex items-center gap-4 bg-[#1A1A1A] border border-[#2A2A2A] rounded-xl px-5 py-4 w-full max-w-md">
      <audio
        ref={audioRef}
        src={audioUrl}
        onEnded={() => { setPlaying(false); setProgress(0); }}
        onCanPlayThrough={() => setLoaded(true)}
        onLoadedMetadata={(e) => setDuration((e.target as HTMLAudioElement).duration)}
        onTimeUpdate={(e) => {
          const audio = e.target as HTMLAudioElement;
          setProgress(audio.duration ? (audio.currentTime / audio.duration) * 100 : 0);
        }}
        onError={() => setLoaded(false)}
        preload="metadata"
      />

      {/* Play/Pause Button */}
      <button
        onClick={togglePlay}
        disabled={!loaded}
        className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 transition ${
          loaded
            ? 'bg-[#D4AF37] hover:bg-[#E8C84B] text-black'
            : 'bg-[#333] text-[#666] cursor-not-allowed'
        }`}
        aria-label={playing ? `Pause ${bookTitle} sample` : `Play ${bookTitle} sample`}
      >
        {playing ? (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="3" y="2" width="4" height="12" rx="1" />
            <rect x="9" y="2" width="4" height="12" rx="1" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M4 2l10 6-10 6V2z" />
          </svg>
        )}
      </button>

      {/* Info + Progress */}
      <div className="flex-1 min-w-0">
        <p className="text-[#E5E5E5] text-sm font-semibold truncate">{title}</p>
        <p className="text-[#8A8A8A] text-xs truncate">{bookTitle}</p>

        {/* Progress bar */}
        <div className="mt-2 h-1 bg-[#333] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#D4AF37] rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Duration */}
        {duration > 0 && (
          <p className="text-[#666] text-[10px] mt-1">
            {formatTime(audioRef.current?.currentTime ?? 0)} / {formatTime(duration)}
          </p>
        )}
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
```

### Audio Player Placement on Each Book Card

For the Sam & Robo series page (/publishing/sam-and-robo), each book card should show:
1. Book cover image
2. Title + description
3. **"Sample Audiobook"** player (using the component above)
4. Buy buttons (existing)

Order: Cover -> Text -> Audio Player -> Buttons. The audio player sits between the description and the buy CTA, above the fold.

### Remove Legacy Audio References

Search the entire codebase and REMOVE:
- Any references to "Standard preview", "Deep preview", "Standard voice", "Deep voice"
- Any audio player pointing to files like `book1_sample.mp3`, `book2_sample.mp3` (these are the OLD non-Hollywood samples)
- Any multiple-preview selector UI (dropdown or tabs showing different voice options)
- Any reference to "preview" in the context of audiobook samples -- the new label is **"Sample Audiobook"**

Keep:
- `ch00_00_prologue.mp3` on the Beyond the Veil page (this is a chapter, not a preview)
- `book1_complete.mp3`, `book2_complete.mp3` references if they exist in download/purchase flows (these are the full paid audiobooks)

---

## PART 3: SUPABASE STORAGE SETUP

These audio files need to be in Supabase Storage for the players to work. If the bucket doesn't exist yet, the audio players should gracefully show "Sample coming soon" instead of erroring.

### Expected Storage Structure:
```
Bucket: audio-assets (public)
├── sam_1/
│   └── trailer_sample.mp3    (30-second Hollywood trailer for Book 1)
├── sam_2/
│   └── trailer_sample.mp3    (30-second Hollywood trailer for Book 2)
├── btv/
│   └── trailer_sample.mp3    (30-second Hollywood trailer for Beyond the Veil)
└── btv/
    └── ch00_00_prologue.mp3   (Full prologue chapter for Beyond the Veil)
```

### Graceful Loading States:
- **Audio file exists**: Player loads normally, gold play button enabled
- **Audio file loading**: Play button shows small spinner, disabled
- **Audio file missing/error**: Show the player container but with text "Sample coming soon" in place of the progress bar. Play button stays disabled (gray). No error toasts or console errors shown to users.

---

## TESTING CHECKLIST

1. **Dealer voice plays** during blackjack game at all specified moments (place bets, cards dealt, bust, win, etc.)
2. **Dealer voice toggle** works in settings -- OFF suppresses all TTS, ON resumes
3. **Volume slider** changes dealer voice volume in real time
4. **Fallback works** -- if dealer-speak edge function is down, browser TTS plays instead (or silent if unavailable)
5. **Cache works** -- common phrases play instantly after first load (no network delay)
6. **Sam & Robo page** shows ONE "Sample Audiobook" player per book (no old previews)
7. **Beyond the Veil page** shows "Listen to the Prologue" + "Sample Audiobook" players
8. **No "Hollywood"** text visible anywhere on the public site -- only "Sample Audiobook"
9. **Audio player** shows progress bar, play/pause toggle, time display, and handles missing files gracefully
10. **Mobile** -- audio players are full-width on small screens, play button is 48px touch target minimum
11. **No legacy preview references** remain anywhere in the codebase

## IMPORTANT: Do NOT break existing features
- Keep ALL existing publishing page content (book descriptions, images, buy links, chapter lists)
- Keep ALL existing blackjack game features
- Keep ALL existing auth flows
- The ElevenLabs voice is additive -- browser TTS is kept as fallback
- Audio sample cleanup only affects the preview players, NOT the full audiobook download/purchase flows
