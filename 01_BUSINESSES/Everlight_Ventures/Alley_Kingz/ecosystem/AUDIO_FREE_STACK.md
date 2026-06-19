# Alley Kingz -- FREE Audio Stack (Music + SFX)

Research 2026-06-16. Scope: FREE tools + FREE APIs only, safe to ship in a MONETIZED game.
(Earlier pass leaned paid: Beatoven/Soundraw/ElevenLabs. This is the free path.)

Engine reality: `engine.js` already has a WebAudio system -- one shared AudioContext, master gain ->
compressor, 8-voice cap, mute via localStorage `ak_muted`, and a sample-first/synth-fallback dispatcher
`sfx(name)` -> `playSample()` (loads `assets/sfx/<name>.mp3`) else procedural `tone()`. The old combat
mp3s were ElevenLabs (paid). We replace with free + procedural.

## RECOMMENDED FREE STACK
| Need | Pick | Cost | License verdict |
|------|------|------|-----------------|
| UI SFX (chest open, reward shimmer, tap, etc.) | **ZzFX** generated at runtime into SFX_BUF | $0 | MIT, no attribution. SMARTEST PATH. |
| Heavier recorded SFX (impacts, whooshes, ambience) | **Sonniss #GameAudioGDC** -> assets/sfx/ | $0 | Royalty-free, commercial, no attribution, game-licensed. |
| Lobby theme (ship now) | **Pixabay Music** | $0 | Commercial OK, no attribution, games OK. SAFE. |
| Lobby theme (bespoke) | **Sonauto** free (1500 credits, has API) | $0 start | Claims commercial/royalty-free; thin ToS -> VERIFY before ship. |
| Zero-file fallback music | **ZzFXM** (JS tracker on ZzFX) | $0 | MIT. Chiptune, fallback only. |

Code-synth verdict (operator's direct question): YES. For small UI sounds, ZzFX is the smartest
zero-cost zero-license path AND drops into the existing SFX_BUF/playSample pipeline -- no files, no
key, works offline, routes through master gain + mute + voice-cap automatically.

## AI MUSIC -- SAFE vs FLAGGED
SAFE (with caveats): **Sonauto** (free tier commercial-claimed + real API at api.sonauto.ai; verify ToS);
**Udio** (free IS commercial BUT requires "Made with Udio" attribution + under the UMG legal cloud);
**Stable Audio Open** (self-host, commercial-free if org revenue < $1M/yr -- AK qualifies; better at
loops/SFX than full vocal openings).
DO NOT SHIP FREE: **Suno** free = non-commercial (Pro $10/mo, and Pro does NOT retroactively license
free songs); **Meta MusicGen** = non-commercial weights; generic "free unlimited commercial" aggregator
sites = vague ToS, don't build the signature hook on them.

## FREE SFX SOURCES
- **Sonniss GameAudioGDC** -- BEST. Royalty-free, commercial, no attribution.
- **Freesound** -- CC0 = commercial no-credit; CC-BY = commercial WITH credit. API TRAP: the API is free
  for NON-commercial only (commercial API needs a license). Path: browse site, filter CC0, download
  manually, ship.
- **Pixabay** -- commercial OK, no attribution. SAFE.
- **Mixkit** -- SFX commercial OK (incl. games); MUSIC explicitly BANNED in video games. SFX only.
- **OpenGameArt** -- CC0/CC-BY OK (credit for BY); AVOID CC-BY-SA / GPL audio (copyleft).
- **ZzFX (MIT) / jsfxr (public domain) / ZzFXM (MIT)** -- all clean, commercial, no attribution.
- Text-to-SFX (ElevenLabs etc.) -- no clean fully-free + commercial option; skip, use ZzFX + Sonniss.

## INTEGRATION PATH (reuses the existing system)
Bridge ZzFX into the existing SFX_BUF/playSample plumbing (the only change is where the buffer comes
from -- synth-generated vs fetched mp3):
```js
// engine.js, after getAC(). ZzFXMicro.min.js exposes zzfxG + zzfxR(=44100)
function zzBuf(p){ const ac=getAC(); if(!ac) return null; const s=zzfxG(...p);
  const b=ac.createBuffer(1,s.length,(typeof zzfxR!=='undefined'?zzfxR:44100)); b.getChannelData(0).set(s); return b; }
function bakeUiSfx(){  // params dialed at killedbyapixel.github.io/ZzFX
  SFX_BUF['chest_open']     = zzBuf([1.5,,260,.02,.2,.4,,1.8,,,,,,,,.1,,.6,.05]);
  SFX_BUF['reward_shimmer'] = zzBuf([,,1200,.01,.25,.3,1,2,,,400,.06,,,,,.1,.7,.04]);
  SFX_BUF['tap']            = zzBuf([.5,,520,,.02,.04,1,1.2,,,,,,,,,,.5]);
}
```
Then `sfx('chest_open')` works unchanged. Lobby theme: drop a Pixabay/Sonauto mp3 into assets and point
the existing BGM deck (`_bgm`/`_deckA`/`_deckB` in index.html ~L4673) at it -- URL + file, no new system.
Heavier SFX: name a CC0/Sonniss clip `assets/sfx/<name>.mp3`, add to SFX_NAMES, loadAllSfx() handles it.

## RISKS
- Sonauto commercial license is claimed but thinly documented -- verify live ToS before it's the hero theme.
- AI music has unsettled copyright broadly -- don't treat an AI theme as defensible IP.
- Easy traps to ship by accident: Mixkit MUSIC + Suno free output -- both unsafe for a paid game.
- Freesound: the sounds are fine; the commercial API is not free.

## SUGGESTED BUILD ORDER (when operator says go)
1. Vendor ZzFXMicro.min.js (MIT) + bake the UI SFX (chest/shimmer/tap/victory/defeat) -- $0, code-only.
2. Pull 1 Pixabay battle theme for the lobby -- wire the existing BGM deck.
3. Optionally try Sonauto for a bespoke anime-opening theme (verify license first).

Sources: Suno help/Dynamoi; Udio ToS/musicmake; Sonauto docs/skywork; Stability license/HF; Freesound API
terms + FAQ; Sonniss GDC license; Pixabay license; Mixkit license; OpenGameArt FAQ; ZzFX/ZzFXM/jsfxr repos.
