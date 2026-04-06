# ElevenLabs Integration Runbook
# Everlight Ventures | Hive Mind: hive_83877943 | 2026-03-10

## Overview

This runbook connects ElevenLabs TTS across the entire Everlight stack:
- Blackjack dealer voice (live, streaming)
- Audiobook chapters (long-form, cached)
- Book trailer samples (30-second cinematic previews for the website)
- All other site audio

Central module: `06_DEVELOPMENT/speech_service.py`

---

## Step 1: Get Your ElevenLabs API Key

1. Go to elevenlabs.io and create a free account
2. Profile > API Key > Copy
3. Free tier gives 10,000 chars/month (Multilingual) or 20,000 (Flash/Turbo)
4. Add to your env: `export ELEVENLABS_API_KEY=your_key_here`

---

## Step 2: Configure Supabase Secrets

In your Supabase project dashboard:
Settings > Edge Functions > Secrets > Add:

```
ELEVENLABS_API_KEY = your_key_here
EL_DEALER_VOICE   = pNInz6obpgDQGcFmaJgB
```

This powers the dealer-speak edge function used by the Lovable frontend.

---

## Step 3: Deploy the Edge Function

From your project root (with Supabase CLI):

```bash
supabase functions deploy dealer-speak
```

The function code is in LOVABLE_BLACKJACK_V4_PROMPT.md, Part 1.
Copy it to: supabase/functions/dealer-speak/index.ts

---

## Step 4: Update Lovable (Blackjack V4)

Paste LOVABLE_BLACKJACK_V4_PROMPT.md into Lovable.
This prompt covers:
- ElevenLabs dealer voice with browser TTS fallback
- NPC bot names (human names from a 35-name pool)
- NPC chip counts (randomized tiers: $50 to $500)
- NPC sit/walk timing (3-12 min arrival, 5-25 min stay)
- Table spacing CSS fixes

---

## Step 5: Generate Trailer Audio Samples

```bash
cd /mnt/sdcard/AA_MY_DRIVE

# Check usage first
python 06_DEVELOPMENT/speech_service.py --usage

# Dry run to preview
python 06_DEVELOPMENT/generate_trailer_samples.py --dry-run

# Generate all trailers
python 06_DEVELOPMENT/generate_trailer_samples.py

# Or one at a time
python 06_DEVELOPMENT/generate_trailer_samples.py --book btv
python 06_DEVELOPMENT/generate_trailer_samples.py --book sam_1
python 06_DEVELOPMENT/generate_trailer_samples.py --book sam_2
```

Output files:
- `.../Book1/audiobook/trailer_sample.mp3`
- `.../Book 2/audiobook/trailer_sample.mp3`
- `.../BEYOND_THE_VEIL_HaileyPink_Book1/audiobook/trailer_sample.mp3`

---

## Step 6: Upload Audio to Supabase Storage

```bash
# Create the audio-assets bucket if it does not exist
# Then upload:
supabase storage cp ./trailer_sample.mp3 ss:///audio-assets/sam_1/trailer_sample.mp3
supabase storage cp ./trailer_sample.mp3 ss:///audio-assets/sam_2/trailer_sample.mp3
supabase storage cp ./trailer_sample.mp3 ss:///audio-assets/btv/trailer_sample.mp3
```

Or upload via Supabase dashboard > Storage > audio-assets.

---

## Step 7: Update build_audiobooks.py for ElevenLabs

The Sam series audiobooks currently use OpenAI TTS.
To regenerate them with ElevenLabs (higher quality):

1. Open `build_audiobooks.py`
2. Replace the `tts_generate()` function to call `speech_service.generate_audiobook_chapter()`
3. Set `genre="kids"` for Sam series

Note: Full audiobook regeneration requires ~150k characters per book.
With the free tier (10k chars), this will burn through quota quickly.
Either upgrade ElevenLabs or use OpenAI TTS for bulk and ElevenLabs for samples only.

---

## Step 8: Add .env and rotate the exposed key

IMPORTANT: The OpenAI API key was previously hardcoded in build_audiobooks.py.
It has been moved to `os.environ.get("OPENAI_API_KEY")`.

Action required:
1. Rotate/regenerate the old OpenAI key at platform.openai.com > API Keys
2. Add the new key to your `.env` file (copy `.env.example`)
3. Confirm `.env` is in `.gitignore`

---

## Budget Tracking

The speech_service tracks monthly usage automatically.
Check at any time:

```bash
python 06_DEVELOPMENT/speech_service.py --usage
```

Budget alerts fire at 80% usage via log warning.
Recommended: set a Supabase edge function cron to email you when ElevenLabs hits 80%.

Provider fallback chain:
  ElevenLabs -> MiniMax -> OpenAI -> espeak (offline)

---

## Architecture Summary

```
Lovable frontend
    |
    v
dealer-speak (Supabase Edge Function)
    |
    v
ElevenLabs API (eleven_flash_v2, Adam voice)
    |
    v
MP3 audio -> browser Audio API -> plays to user

Python scripts (local/server)
    |
    v
speech_service.py (06_DEVELOPMENT/)
    |-- speak_dealer()              -> dealer phrases
    |-- generate_audiobook_chapter() -> book chapters
    |-- generate_trailer_sample()   -> 30s cinematic previews
    |-- generate_site_sample()      -> web player embeds
    |
    v
07_STAGING/tts_cache/              -> file cache (hash-keyed .mp3)
07_STAGING/tts_cache/usage.json    -> monthly char tracking
```

---

## Rollback Plan

If ElevenLabs integration causes issues:
1. Frontend: `dealerSpeak()` already falls back to `speechSynthesis` automatically
2. Python scripts: set `ELEVENLABS_API_KEY=""` to force OpenAI fallback
3. Trailer samples: old samples in audiobook/ dirs are preserved (not overwritten unless regenerated)
