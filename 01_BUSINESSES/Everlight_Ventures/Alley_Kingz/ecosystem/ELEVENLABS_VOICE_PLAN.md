# Alley Kingz -- ElevenLabs Premium Voice Plan (DESIGN ONLY)

Upgrade the 111 spoken lore lines from the FREE browser `speechSynthesis`
(AK-SPEAK / AK-VOICEVAR in `engine.js`) to premium ElevenLabs mp3s, with a
zero-break fallback to the existing free voice. No code edits, no API calls,
no spend in this doc. Key already lives in `03_Credentials/.env`
(`ELEVENLABS_API_KEY`, confirmed present).

Real setup it rides on: static client on Cloudflare Pages (alleykingz.online),
data + auth on Supabase project `mfghdobptredxxhbjwyz`, server logic in Supabase
edge functions, e5-mother (tailnet ARM box) as the always-on render host.
`game/` is already ~287MB, so off-repo audio hosting matters (see HOSTING).

## 1. COST (measured, not guessed)

Counted directly from `game/cards_lore.js` (106 cards 0001-0106 + 5 spells
S001-S005 = 111 entries, fallback default excluded):

| Scope                | Lines | Total chars | Avg/line |
|----------------------|-------|-------------|----------|
| Taglines only        | 111   | 3,114       | 28.1     |
| Bios only (phase 2)  | 111   | 14,718      | 132.6    |
| Taglines + bios      | 111   | 17,832      | --       |

Tier assumption: ElevenLabs charges 1 credit = 1 character (English, Multilingual
v2 / Flash v2.5). Costed at the **Creator** plan: $22/mo (often $11 first month),
100,000 credits included -> blended $0.00022 per char.

| Job                      | Chars  | Cost @ Creator | With 2x best-of-2 QA |
|--------------------------|--------|----------------|----------------------|
| Taglines only            | 3,114  | ~$0.69         | ~$1.37               |
| Taglines + bios          | 17,832 | ~$3.92         | ~$7.85               |

Bottom line: taglines-only fits inside the **FREE tier** (10,000 credits/mo)
entirely -> $0 marginal. The full 111-line job is ~18k credits -- one month of
Creator covers it ~5.6x over. Net new spend for everything = a single
cancellable $22 month (or ~$4-8 pay-as-you-go). This is a rounding error.

## 2. VOICE CASTING (map to existing logic, do NOT do 20)

`engine.js` already encodes the casting axes: `BREED_SIZE` (5 size classes
0 tiny..4 giant -> pitch/rate) and `FACTION_TIMBRE` (4 factions -> timbre tint).
The matrix is 4 x 5 = 20 theoretical slots; that is over-casting. ElevenLabs
carries timbre in the voice itself and exposes a speed knob (not pitch), so
collapse to **9 licensed voices**:

- **1 signature hero** -- $BCARDD (0001): regal, commanding, matches the existing
  `assets/vo/bcardd_kingly.mp3` vibe. The brand voice.
- **2 voices per faction x 4 = 8** -- one "heavy" (giant/tank, deep) + one "light"
  (small/young) per crew. The existing breed-size pitch/speed fingerprint and the
  ElevenLabs speed param cover the in-between sizes.

Faction tint -> voice direction (from `FACTION_TIMBRE`):
- Boneguard (heavy/dark, square -30): deep gravelly menace; all size-4 giants are
  Boneguard by design, so its heavy voice does the most lifting.
- K9 Circuitry (electric/bright, +35): crisp, clipped, lightly synthetic.
- Leashbreak Tactix (street grit, +10): mid, raspy, tactical.
- Zoomie Syndicate (zippy/light, +60): fast, young, hyped.

Gender lean (`_akCardGender` f/m/?) picks heavy-vs-light within a faction.
Optional later expansion: 12+1 (giant/mid/tiny per faction). Voice count does NOT
change $ cost -- ElevenLabs bills characters, not voices.

## 3. HOSTING (off-repo, named by cardNumber)

111 mp3s. Real size anchor from `assets/vo/` (existing clips 18-58KB): taglines
~30KB each at 64-96kbps mono. Bios ~5x longer (~150KB).

- Taglines deploy size: ~3.3MB. Taglines + bios: ~16-20MB.
- Cloudflare Pages limits (25MB/file, 20k files) are not a concern, BUT `game/` is
  already ~287MB, so do NOT bloat the deploy.

**Decision: Supabase Storage public bucket, not the repo.** Project
`mfghdobptredxxhbjwyz`, bucket `card-voices`, CDN-cached. Matches the
"data + auth on Supabase" architecture and lets a single voice be regenerated
without a full CF Pages redeploy. Layout, named by cardNumber:

```
card-voices/taglines/0001.mp3 ... 0106.mp3, S001.mp3 ... S005.mp3
card-voices/bios/0001.mp3 ...                (phase 2)
card-voices/voices_manifest.json             (which cardNumbers are live)
```

## 4. WIRING (preload-on-demand + graceful free fallback)

- **On-demand, not bulk.** Lazy-fetch a card's mp3 when it deploys / its detail
  overlay opens (the two spots AK-SPEAK already fires). Cache the `Audio` object
  on the card, mirroring the existing `card._akVoice` cache pattern. Optionally
  warm the 11 active-deck mp3s at match start to kill first-deploy latency.
- **Stream vs preload:** files are tiny (~30-150KB) -- a plain `new Audio(url)`
  fetch+play is enough; no chunked streaming needed.
- **Manifest-first** to avoid 404 round-trips: client reads `voices_manifest.json`;
  cardNumbers not listed skip straight to fallback.
- **Graceful fallback (never breaks):** new `akSpeakPremium(card)` tries the mp3;
  on 404 / network error / not-in-manifest it calls the EXISTING
  `akSpeak(text, card)` speechSynthesis path. Same `ak_voice` toggle, same
  `_akMuted` gate, same ~4s `_akSpeakLast` throttle. Missing mp3 = silent degrade
  to the free voice. Offline, mid-rollout, or ungenerated card all still work.

## 5. THREE-CARD SAMPLE PLAN (prove quality + cost before all 111)

Spread chosen to test 2 factions, 3 size classes, and the pitch extremes:

| Card | Name             | Breed         | Faction    | Size | Why                         |
|------|------------------|---------------|------------|------|-----------------------------|
| 0001 | $BCARDD          | Dogo Argentino| Boneguard  | 3    | Signature hero / brand voice|
| 0004 | Iron Rottweiler  | Rottweiler    | Boneguard  | 4    | Deepest giant, dark timbre  |
| 0046 | Flux Pomeranian  | Pomeranian    | K9 Circuit | 0    | Highest pitch, 2nd faction  |

The one command that would generate + upload the sample (script is the build
step, NOT yet written -- listed here as the spec, runs on e5-mother, never phone):

```
python3 03_AUTOMATION_CORE/01_Scripts/publishing/ak_voice_gen.py \
  --cards 0001,0004,0046 --field tagline --tier creator \
  --voices voice_casting.json \
  --upload supabase:mfghdobptredxxhbjwyz/card-voices/taglines \
  --manifest card-voices/voices_manifest.json
```

Cost of this sample: 3 taglines, ~95 chars -> ~$0.02. Effectively free proof.

## OPERATOR GO DECISION

**Recommended: SAMPLE FIRST.** Generate the 3 cards above (~$0.02), play them in
the game behind the manifest+fallback wiring, judge quality/voice fit. If the
$BCARDD hero voice and the giant/tiny extremes land, GO on all 111 taglines
(~$0.70, fits the free tier). Bios are phase 2 (~$3.92 more, optional). Total
worst-case spend for the entire premium voiceover is one cancellable $22 Creator
month. Zero risk to ship the sample. Awaiting GO.
