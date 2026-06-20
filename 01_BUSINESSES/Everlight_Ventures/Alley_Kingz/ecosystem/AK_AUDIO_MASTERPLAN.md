# ALLEY KINGZ -- AUDIO + SENSORY MASTERPLAN (master-plan systems; 2026-06-19)
> Companion to AUDIO_DESIGN_REFERENCE.md (recipes), AUDIO_FREE_STACK.md (free tools), SOUND_MAP.md (the
> in-match event->sound table), AUDIO_TOOL_DECISION.md (Suno + ElevenLabs picks). This file extends the
> SOUND_MAP to the NINE new master-plan / meta-game systems (AK_MASTER_BLUEPRINT.md + AK_WORLD_BIBLE.md):
> raid siege alert, crew-chest open, war countdown, reinforce, ascension, district-vs-district,
> squad combo/synergy, building damage, alley-crate open.
>
> "Sound is as important as the graphics." -- operator, 2026-06-17.

## 0. GROUND RULES (carried from the canon, do not relitigate)
- **EventBus pub/sub, no direct imports.** None of these systems "call audio." They EMIT a fact on
  SHARED/EventBus.js; a single new pure-listener module (the **AudioDirector**, modeled on M05
  SOCIAL_URGENCY's listener-only pattern) subscribes and fires the cue. Re-platforming the renderer never
  touches the audio map -- it is bus-driven. See section 5.
- **The engine already owns the playback chain.** `sfx(name)` in engine.js is SAMPLE-FIRST / synth-fallback:
  it plays `assets/sfx/<name>.mp3` if present (preloaded via `SFX_NAMES` + `loadAllSfx()`), else a procedural
  `tone()` synth. Routed through master gain -> compressor -> 8-voice cap -> `ak_muted` toggle automatically.
  Exposed on the global as `AK.sfx(name)` / `AK.playSfx(name)`. **Every identifier below ships TODAY as a
  synth placeholder and UPGRADES the instant a named mp3 lands in `game/assets/sfx/` -- zero code change, $0,
  non-blocking.** That is the free fallback path for all of them.
- **Sensory feedback is four channels, not one** (the engine already has all four primitives):
  1. **SFX** -- `sfx(name)` / `AK.playSfx(name)`.
  2. **Haptics** -- `haptic(kind, force)` reads `HAPTIC_PAT` (navigator.vibrate, guarded, `AK_HAPTICS` chip,
     70ms throttle; `force=true` bypasses for big moments). Add new patterns to `HAPTIC_PAT` (section 6).
  3. **Screen shake** -- `game.shake += N` (renderer reads + decays). Only meaningful on a live battle canvas
     (in-match synergy, DvD siege). Hub/meta moments use a CSS pulse instead (section 6).
  4. **Music** -- the BGM A/B crossfade deck (`_bgm`/`_deckA`/`_deckB` in index.html). Big moments DUCK the
     bed or crossfade to a stinger, then return.
- **The 6 recipe laws** (AUDIO_DESIGN_REFERENCE.md): every SFX = transient + body + tail; readability beats
  realism (know it eyes-closed); fire under ~40ms; vary pitch/round-robin so it never fatigues; **reward sound
  = anticipation then payoff, ESCALATING by tier**; lobby music = hype, battle music = tense focus.
- **Tool routing** (AUDIO_TOOL_DECISION.md + AUDIO_FREE_STACK.md):
  - **ElevenLabs Text-to-SFX** = the rich cinematic one-shots (sieges, fanfares, collapses, chests). Paid but
    cheap, royalty-free commercial, perpetual, scriptable via `art/generate_sfx.py`. PRIMARY for this set.
  - **ZzFX (MIT, $0, runtime-baked)** = the tiny UI ticks (countdown ticks, contribution blips, combo steps).
    Bake into `SFX_BUF` via `bakeUiSfx()` -- no file, no key, offline. TRULY-free path.
  - **Suno (locked Persona)** = the music stings/anthems (DvD siege anthem, ascension anthem, war bed).
    Truly-free music fallback = Pixabay battle theme / Stable Audio Open self-host.
  - **Procedural `tone()` synth** = the always-on $0 placeholder under every name until an mp3 is generated.
- **NeonReach canon** (AK_WORLD_BIBLE.md): it is **crew** not clan, **graffiti** not runes, urban street
  culture. House style for every prompt: gritty TV-MA cyberpunk dog gangs, neon-noir, analog synth + street
  grime. Keep it street, never generic-fantasy.

---

## 1. THE NEW-SYSTEMS SOUND LIST (the master table)

Legend: **Tool** -- 11L=ElevenLabs Text-to-SFX, ZzFX=runtime synth, Suno=music. `force` = haptic bypasses
the 70ms throttle (big moment). All sound names are new `sfx()` identifiers; add to `SFX_NAMES` (section 6).

| # | System | Bus event(s) it listens to | Sound identifier(s) | Reward? escalation | Haptic | Shake / pulse | Music | Tool |
|---|--------|----------------------------|---------------------|--------------------|--------|---------------|-------|------|
| 1 | **Raid siege alert** | `CREW_UNDER_SIEGE`, `raid.attack.launched` | `siege_alert` | no (alarm) | `siege` [40,60,40,60,200] `force` | red vignette pulse (hub) | DUCK bed -20%, low pulse layer | 11L |
| 2 | **Crew-chest open** | `crew.chest.ready`, `crew.chest.open` | `crew_chest_open` (+ pitch by haul) | YES, riser->crack->arpeggio->shimmer | `chest` [10,30,10,30,80] | gold particle burst + CSS pop | brief positive swell | 11L |
| 3 | **War countdown** | `crew.war.countdown{tier}` (1h/30m/10m/2m), `crew.war.start` | `war_tick` (pitch climbs per tier), `war_horn` (NOW) | tension build, not reward | `war_tick` [12] -> `war_now` [60,40,120] `force` | none (UI ring flash) | tension bed rises each tier | ZzFX (tick) + 11L (horn) |
| 4 | **Reinforce** | `crew.reinforcement.requested`, `crew.reinforcement.filled` | `reinforce_call` (request), `reinforce_arrive` (filled) | filled = small positive | call [9,40,9]; arrive `chest`-lite [10,30] | ally-glow CSS | none / tiny swell | 11L |
| 5 | **Ascension** (prestige) | `progression.prestige`, `crew.ascension{tier}` | `ascension_bronze..ascension_crown` (6 tiers) | YES -- the GRANDEST in game | `ascension` [30,50,30,50,250] `force` | gold full-screen flash + radial light | CROSSFADE to ascension stinger, return | 11L SFX + Suno anthem |
| 6 | **District-vs-District** | `dvd.phase{hype\|siege\|rebuild}`, `dvd.tower.captured`, `dvd.contribution` | `dvd_hype`, `dvd_siege`, `dvd_capture`, `dvd_rebuild`, `dvd_contribute` | capture = reward; rebuild = somber | siege [50,40,90] `force`; capture `chest`; contribute [6] | siege: `game.shake+=8` (live); else CSS | crossfade to DvD siege anthem during Siege Phase | 11L + Suno (siege anthem) |
| 7 | **Squad combo / synergy** | `squad.synergy.proc{count}`, `combo.proc{step}` | `synergy_proc` (pitch climbs per combo step) | escalates with combo count | tick [5] ramping; big combo `knock` [22] | flash faction tint; big combo `game.shake+=3` | duck minor sfx so it cuts | ZzFX (steps) + 11L (the "lock-in" stab) |
| 8 | **Building damage** | `building:damaged`, `building:destroyed`, `building:repaired` | `building_hit`, `building_destroyed`, `building_repaired` | no (loss-aversion) | hit `tower_hit` [12]; destroyed `bld_down` [45,40,85] `force` | shake if hub-visible; else CSS shake | low ominous swell on destroyed | 11L |
| 9 | **Alley-crate open** | `crate.open{tier}` (wooden/metal/neon/golden) | `crate_wooden`, `crate_metal`, `crate_neon`, `crate_golden` | YES -- Clash-style escalate per tier | escalates: wooden [10] -> golden [10,30,10,30,120] | gold burst on neon/golden | golden = brief fanfare swell | ZzFX (wooden) + 11L (metal/neon/golden) |

---

## 2. PER-SYSTEM DESIGN (recipe + sensory + free fallback)

### 1. RAID SIEGE ALERT -- "BUDDY'S BASE IS BURNING" (Tier-1 urgency)
- **Triggers:** AudioDirector subscribes to `CREW_UNDER_SIEGE` (emitted by M03 RaidController) and
  `raid.attack.launched`. This is the single most retention-critical alert in the game (Whiteout/Clash DNA).
- **Recipe (`siege_alert`, ~1.2s):** a rising neon air-raid klaxon -- two-tone alarm sweep that LIFTS in pitch
  (anticipation/threat), gritty analog-synth body, short distorted tail. Readability law: it must be unmistakable
  from across the room; nothing else in the game uses a rising klaxon. NOT a reward sound -- this is threat.
- **Sensory:** `haptic('siege', true)` long urgent pattern (bypasses throttle); red vignette pulse on the hub
  canvas (CSS, 2 beats); DUCK the BGM bed -20% and layer a low sub pulse under the alert so the room feels heavy.
- **Free fallback:** synth placeholder -- `tone()` does a fast rising sawtooth sweep until the mp3 lands.

### 2. CREW-CHEST OPEN (Tier-3 shared reward anxiety; the #1 engagement sound)
- **Triggers:** `crew.chest.ready` (the timer fills -> a soft "ready" shimmer + push) and `crew.chest.open`
  (the crack). The crew chest is a TIMED open -- miss it = miss out -- so the open is a high-dopamine payoff.
- **Recipe (`crew_chest_open`, ~1.0-1.4s):** the full reward formula -- (1) anticipation riser, (2) satisfying
  latch crack (transient+body), (3) ascending pitch run root->3rd->5th->octave ("it got better"), (4) sparkle
  shimmer tail. Pitch/scale the one base UP by haul size (small haul = shorter run, big haul = full fanfare),
  the engine already pitches via `playSample(name, rate)`.
- **Sensory:** `haptic('chest')` celebratory stutter; gold particle burst + a CSS "pop" scale-bounce on the chest
  card; brief positive music swell. The `ready` cue is a gentle 2-note shimmer (anticipation, pulls them back in).
- **Free fallback:** reuse the existing `chest_open`/`reward` synth placeholders already in `sfx()`.

### 3. WAR COUNTDOWN (Tier-1 escalation: 1h -> 30m -> 10m -> 2m -> NOW)
- **Triggers:** `crew.war.countdown{tier}` fired at each threshold by M04/M08, then `crew.war.start`.
- **Recipe:** ONE `war_tick` whose pitch CLIMBS each threshold (`playSample('war_tick', 1.0/1.15/1.3/1.5)`) so
  the tension audibly tightens -- crisp high tick, dry, <60ms (ZzFX-perfect). At NOW, `war_horn` -- a deep
  cyberpunk battle horn blast (sub + brass-synth body, ~1.3s, 11L) = "it's on."
- **Sensory:** light `war_tick` haptic [12] per threshold escalating to `war_now` [60,40,120] `force` at the horn;
  a UI ring flash on the war widget; the battle/tension bed creeps up in level each threshold.
- **Free fallback:** `war_tick` is a ZzFX tick (zero file); `war_horn` synth = layered low `tone()` until mp3.

### 4. REINFORCE (Tier-1 reciprocity: emergency shield / crew help)
- **Triggers:** `crew.reinforcement.requested` (a member begs the crew) and `crew.reinforcement.filled` (an ally
  answers -- the reciprocity payoff). Both already emitted by M04 CrewManager.
- **Recipe:** `reinforce_call` -- a short crew rally whistle/horn (street-gang signal, ~0.5s, urgent-but-friendly).
  `reinforce_arrive` -- supportive whoosh into a warm 2-note "ally lands" chime (~0.5s); positive, you were saved.
- **Sensory:** request = light double-buzz [9,40,9]; filled = a soft `chest`-lite stutter + an ally-glow CSS pulse
  on the helped building. No shake (hub/meta). Optional tiny music swell on filled.
- **Free fallback:** synth placeholders -- call = short rising `tone()`, arrive = warm 2-note `tone()`.

### 5. ASCENSION (Crew Ascension / prestige -- 6 tiers Bronze->Silver->Gold->Platinum->Diamond->Crown)
- **Triggers:** `progression.prestige` (M07, burns 500 ALK) and `crew.ascension{tier}`. This is the rarest,
  highest-status moment in the game -- it must SOUND like the biggest reward you can earn.
- **Recipe (6 escalating files `ascension_bronze..ascension_crown`, 1.6-2.5s):** the reward formula at MAX --
  huge anticipation riser -> golden explosion burst -> triumphant brass-and-synth fanfare -> cascading sparkle +
  deep sub. **Escalate brightness/length/grandeur per tier:** Bronze = bold but contained; Crown = a full
  cyberpunk-royal anthem stinger, the grandest in the game (Clash-Royale legendary-chest energy, dialed past it).
- **Sensory:** `haptic('ascension', true)` heavy celebratory rumble; gold FULL-SCREEN flash + a radial light sweep
  from the Main Tower; the BGM CROSSFADES to the ascension stinger then returns to the hub bed. Crown tier earns
  a 2s Suno anthem stinger.
- **Free fallback:** reuse `win`/`crown`/`evo_up` synth placeholders, pitched up per tier, until the mp3s land.

### 6. DISTRICT-VS-DISTRICT (DvD monthly cross-district war: Hype -> Siege -> Rebuild)
- **Triggers:** `dvd.phase{hype|siege|rebuild}`, `dvd.tower.captured`, `dvd.contribution`.
- **Recipe:**
  - `dvd_hype` (~0.7s): a positive "war is coming" rally sting (bass drop into bright ascending triad) -- akin to
    `sting_major`, hype energy.
  - `dvd_siege` (~1.2s): the BIG one -- war drums + a low alarm swell, dread + adrenaline. Siege Phase turns VIP
    buffs OFF, so the audio signals "no mercy now."
  - `dvd_capture` (~1.0s): Central Tower captured -- triumphant golden burst (reward formula, mid-length).
  - `dvd_rebuild` (~1.0s): somber-hopeful descending pad (the 24h repair window -- miss it = permanent loss; a
    loss-aversion tone, not a defeat).
  - `dvd_contribute` (~60ms): a crisp leaderboard blip each time you add contribution (ZzFX; pitch climbs with rank).
- **Sensory:** Siege Phase is a LIVE battle, so `dvd_siege` does `game.shake += 8` + `haptic('siege', true)`; the
  BGM CROSSFADES to a dedicated DvD siege anthem (Suno) for the duration of the phase and crossfades back at
  Rebuild. Capture = `haptic('chest')` + gold burst. Contribution blip = `haptic [6]`.
- **Free fallback:** `dvd_hype`/`dvd_rebuild` reuse `sting_major`/`sting_minor`; `dvd_siege`/`dvd_capture` reuse
  `tower_down`/`win` placeholders; `dvd_contribute` is a ZzFX blip.

### 7. SQUAD COMBO / SYNERGY (in-match; faction/squad synergy procs)
- **Triggers:** `squad.synergy.proc{count}` / `combo.proc{step}` (in-match, when a faction or squad-composition
  synergy fires). Must read OVER constant combat -- duck minor sfx so it cuts (recipe law 2 + the voice cap).
- **Recipe (`synergy_proc`, ~0.2-0.4s):** a bright harmonic "lock-in" chord stab + power-up shimmer -- clearly
  NOT a normal unit ability (distinct spell-layer law). Pitch CLIMBS per combo step (`playSample('synergy_proc',
  1.0 + step*0.08)`) like a combo meter audibly stacking -- a mini reward run inside the fight.
- **Sensory:** a light haptic tick [5] that ramps with the combo; a brief screen flash tinted to the squad's
  faction color; a big combo (count >= 4) adds `game.shake += 3` + `haptic('knock')`. Keep it tasteful -- it
  fires often, so short + varied beats loud.
- **Free fallback:** ZzFX bright stab for the steps + the `ability`/`evo_up` synth for the big lock-in.

### 8. BUILDING DAMAGE (Clash-of-Clans offline-raid stat decay; loss aversion)
- **Triggers:** `building:damaged`, `building:destroyed`, `building:repaired` (M02 BuildingBase, driven by M03
  raids). Distinct from the in-match `tower_hit`/`tower_down` (that's combat; this is the META hub layer).
- **Recipe:** `building_hit` (~0.4s) -- concrete/metal structure crack + debris flecks (low impact, dry).
  `building_destroyed` (~0.8s) -- a heavier collapse rumble + deep sub + crumbling debris (your base lost a
  building while you slept -- it should hurt). `building_repaired` (~0.5s) -- a satisfying mechanical
  reassemble/lock-in (relief + progress).
- **Sensory:** if the hub is on-screen, `game.shake` (hit +=4, destroyed +=10) + `haptic('tower_hit')` /
  `haptic('bld_down', true)`; if it's a "while you were away" summary, a CSS shake on the building card + the
  destroyed cue carries a low ominous music swell. Repaired = light positive haptic + green progress flash.
- **Free fallback:** reuse the shipped `tower_hit`/`tower_down` mp3s (already in assets/sfx) as the placeholders.

### 9. ALLEY-CRATE OPEN (overworld pickups: Wooden / Metal / Neon / Golden)
- **Triggers:** `crate.open{tier}` (M01/M02/M06 -- crates scattered on the overworld, respawn on a timer, rare
  Golden during events). Classic Clash-Royale escalate-per-tier chest psychology.
- **Recipe (4 tier files):** the reward formula, ESCALATING by tier --
  - `crate_wooden` (~0.4s): small wood-crack pop + soft 2-note chime (ZzFX-perfect).
  - `crate_metal` (~0.7s): metal latch crack + rising 3-note arpeggio + light shimmer.
  - `crate_neon` (~0.9s): anticipation riser + bright neon burst + ascending arpeggio + sparkle tail.
  - `crate_golden` (~1.6s): big riser + golden explosion + triumphant fanfare + cascading shimmer + sub
    (legendary energy -- the event reward, just under Ascension in grandeur).
- **Sensory:** haptic escalates with tier (wooden [10] -> golden [10,30,10,30,120]); neon/golden add a gold
  particle burst; golden adds a brief fanfare music swell. Overworld pickup = satisfying pop + shimmer.
- **Free fallback:** reuse `chest_open`/`reward`/`scoop*` synth placeholders, pitched per tier.

---

## 3. GEN COMMANDS -- ElevenLabs Text-to-SFX (paste into art/generate_sfx.py MANIFEST)

`art/generate_sfx.py` is the existing, phone-safe (pure-stdlib) generator. Add this block to its `MANIFEST`
dict (name -> (prompt, duration_seconds)). House style is baked into each prompt: gritty cyberpunk dog-gang
neon-noir, dry, punchy, readable, "no music" on SFX so the BGM owns the music lane.

```python
# --- AK_AUDIO_MASTERPLAN: meta-system SFX (append to MANIFEST in art/generate_sfx.py) ---
MANIFEST.update({
  # 1 RAID SIEGE ALERT
  "siege_alert":       ("a rising neon air-raid klaxon alarm, two-tone alarm sweep climbing in pitch, gritty analog synth, urgent cyberpunk warning, threatening, no music", 1.2),
  # 2 CREW-CHEST OPEN (the reward-formula hero)
  "crew_chest_open":   ("opening a big crew loot chest, anticipation riser then a satisfying latch crack, ascending bright arpeggio root to octave, magical sparkle shimmer tail, rewarding, cyberpunk gold, no music", 1.3),
  "crew_chest_ready":  ("a soft gentle two-note ready shimmer, a chest is ready to open, inviting, short, no music", 0.5),
  # 3 WAR COUNTDOWN
  "war_horn":          ("a deep cyberpunk battle war horn blast, low sub plus brass-synth body, the war begins now, commanding, no music", 1.3),
  # 4 REINFORCE
  "reinforce_call":    ("a short urgent crew rally whistle horn, street gang signal calling for backup, punchy, no music", 0.5),
  "reinforce_arrive":  ("a supportive whoosh into a warm reassuring two-note chime, allied reinforcements arrive, relief, no music", 0.6),
  # 5 ASCENSION (6 escalating tiers -- regen per tier with rising grandeur)
  "ascension_bronze":  ("a triumphant prestige ascension fanfare, anticipation riser into a golden burst, bold brass and synth, sparkle tail, cyberpunk royal, no music", 1.6),
  "ascension_silver":  ("a triumphant prestige ascension fanfare, brighter and longer riser into a golden explosion, brass and synth, cascading sparkle, cyberpunk royal, no music", 1.8),
  "ascension_gold":    ("a grand prestige ascension fanfare, big anticipation riser, golden explosion burst, triumphant brass and synth swell, lush cascading shimmer, cyberpunk royal, no music", 2.0),
  "ascension_platinum":("an epic prestige ascension fanfare, huge riser, radiant platinum burst, soaring brass and synth, deep sub, grand sparkle cascade, cyberpunk royal, no music", 2.2),
  "ascension_diamond": ("a majestic prestige ascension fanfare, enormous riser, brilliant diamond burst, full triumphant orchestra-synth, deep sub, dazzling shimmer cascade, cyberpunk royal, no music", 2.3),
  "ascension_crown":   ("the grandest royal coronation ascension anthem sting, colossal anticipation riser, blinding golden crown explosion, full triumphant brass-and-synth fanfare, deep sub, cascading sparkle, supreme grand-prize energy, cyberpunk royal, no music", 2.5),
  # 6 DISTRICT-VS-DISTRICT
  "dvd_hype":          ("a hype war-is-coming rally sting, bass drop into a bright ascending triad, gold premium, energizing, no music", 0.7),
  "dvd_siege":         ("a heavy war siege alarm, pounding war drums plus a low dread alarm swell, adrenaline and danger, cyberpunk battle, no music", 1.2),
  "dvd_capture":       ("a triumphant central-tower-captured burst, golden victory swell, ascending fanfare, rewarding, cyberpunk, no music", 1.0),
  "dvd_rebuild":       ("a somber but hopeful descending synth pad, a rebuild window opens, bittersweet, no music", 1.0),
  # 7 SQUAD COMBO / SYNERGY (the lock-in stab; steps come from ZzFX)
  "synergy_proc":      ("a bright harmonic synergy lock-in chord stab plus a quick power-up shimmer, distinct from a normal ability, crisp, short, cyberpunk, no music", 0.35),
  # 8 BUILDING DAMAGE (meta hub layer; distinct from in-match tower)
  "building_hit":      ("a concrete and metal building structure crack, low impact thud with debris flecks, dry, no music", 0.4),
  "building_destroyed":("a building collapsing and crumbling, deep sub rumble, beams snapping, heavy debris crash, your base is hit, no music", 0.8),
  "building_repaired": ("a satisfying mechanical building reassemble and lock into place, progress restored, relief, no music", 0.5),
  # 9 ALLEY-CRATE OPEN (escalate per tier; wooden is ZzFX, these three are 11L)
  "crate_metal":       ("a metal crate latch crack opening, rising three-note arpeggio, light shimmer, rewarding, no music", 0.7),
  "crate_neon":        ("a neon loot crate opening, anticipation riser, bright neon burst, ascending arpeggio, sparkle tail, rewarding, cyberpunk, no music", 0.9),
  "crate_golden":      ("an epic legendary golden crate opening, big anticipation riser, golden explosion burst, triumphant fanfare, cascading sparkle, deep sub, grand-prize energy, cyberpunk royal, no music", 1.6),
})
```

**RUN (phone or e5):**
```bash
cd 01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/art
ELEVENLABS_API_KEY=sk_xxxx python3 generate_sfx.py            # makes only the missing ones
ELEVENLABS_API_KEY=sk_xxxx python3 generate_sfx.py --force    # regen all (e.g. to re-roll an ascension tier)
# key lives in 03_Credentials/.env ; output lands in game/assets/sfx/*.mp3
```
After generating, add the names to `SFX_NAMES` in engine.js (section 6) so `loadAllSfx()` preloads them. The
synth placeholder auto-yields the moment the mp3 is present. Maintain the license manifest CSV
(identifier, tool, license, date) per SOUND_MAP production workflow.

## 3b. GEN COMMANDS -- ZzFX (truly-free, runtime-baked; no file, no key)
The tiny high-frequency UI ticks should be ZzFX, not mp3s -- they fire constantly and must be <60ms.
Vendor `ZzFXMicro.min.js` (MIT) once, then bake into `SFX_BUF` after `getAC()` (per AUDIO_FREE_STACK.md).
Dial each param array at https://killedbyapixel.github.io/ZzFX/ (these are tuned starting points):

```js
function bakeMetaUiSfx(){   // AK_AUDIO_MASTERPLAN -- runtime UI ticks, $0/MIT
  SFX_BUF['war_tick']       = zzBuf([1.1,,420,.01,.03,.05,1,1.6,,,,,,,,,,.5,.02]);   // crisp tension tick; pitch-climb via playSample rate
  SFX_BUF['dvd_contribute'] = zzBuf([.8,,720,,.02,.05,1,2,,,200,.04,,,,,.05,.7,.02]); // leaderboard blip; rate climbs with rank
  SFX_BUF['crate_wooden']   = zzBuf([1.4,,180,.01,.12,.25,,1.4,,,,,,,,.1,,.6,.05]);   // small wood-crack pop + 2-note tail
  SFX_BUF['synergy_step']   = zzBuf([,,900,.01,.06,.1,1,2,,,300,.05,,,,,.06,.7,.03]); // optional combo-step blip under synergy_proc
}
```
`war_tick` escalates by threshold via `playSample('war_tick', rate)` with rate 1.0/1.15/1.3/1.5; `crate_wooden`
keeps the cheapest tier file-free.

## 3c. GEN COMMANDS -- Suno (music stings/anthems; locked Persona for one cohesive band)
Music is made ONCE and owned forever (AUDIO_TOOL_DECISION.md). Lock ONE Suno Persona so every track is the
same band, render, download stems, drop into `assets/music/`, wire to the `_bgm` deck (URL + file, no new
system). Truly-free fallback = Pixabay battle theme / Stable Audio Open self-host.

```
# DvD SIEGE ANTHEM (crossfades in during the Siege Phase, out at Rebuild) -- assets/music/dvd_siege_anthem.mp3
"110 BPM tense cyberpunk war anthem, pounding war drums, distorted analog synth bass, neon arps, ominous
 brass stabs, relentless driving rhythm, street-gang siege energy, loopable, instrumental"

# ASCENSION ANTHEM STINGER (Crown tier crossfade) -- assets/music/ascension_anthem.mp3
"a 2-second triumphant cyberpunk-royal coronation anthem sting, soaring brass and synth over a deep sub,
 golden victorious, grand, instrumental"

# WAR BED (escalating under the countdown) -- reuse the battle bed or a low tension loop ~95 BPM
```

---

## 4. SENSORY-FEEDBACK SUMMARY (the non-audio channels per system)
- **Haptics** ride the SAME call site as the SFX (never new timing -- the engine's existing law). `force=true`
  for siege_alert, war_horn->NOW, ascension, dvd_siege, building_destroyed (these bypass the 70ms throttle).
- **Screen shake** (`game.shake += N`) ONLY where a battle/hub canvas is live: in-match synergy (+3 on big
  combos), DvD Siege (+8), building damage when the hub is on-screen (hit +4 / destroyed +10). Meta/hub-summary
  moments use a CSS pulse/shake on the relevant widget instead -- never fake a shake with no canvas.
- **Visual** pairs with each: red vignette (siege), gold particle burst (chest/crate-neon+golden/capture),
  full-screen gold flash + radial light (ascension), faction-tint flash (synergy), green progress flash
  (repaired), ally-glow (reinforce). These hook the renderer's existing effects/particles arrays.
- **Music** is a deliberate channel: DUCK on threat (siege), brief SWELL on reward (chest/crate-golden/capture),
  full CROSSFADE on the rare grand moments (ascension Crown, DvD Siege Phase), return to the hub bed after.

---

## 5. WIRING -- the AudioDirector (pure EventBus listener, no direct imports)
A single new listener module (mirrors M05 SOCIAL_URGENCY: it reacts to facts other modules already emit and
produces NO game state). It is the ONLY contact point between the meta systems and the audio engine, so the
audio map is renderer-agnostic and survives the 2.5D/Unity re-platform.

```js
// ALLEY_KINGZ_CORE/MODULE_05_SOCIAL_URGENCY/AudioDirector.js (or a sibling AudioBridge)
// Pure listener. Imports NOTHING. Calls only the AK adapter (AK.playSfx / AK.haptic).
function mountAudioDirector(bus, AK){
  const fire = (name, hap, hapForce) => { AK.playSfx(name); if (hap && AK.haptic) AK.haptic(hap, !!hapForce); };

  bus.on('CREW_UNDER_SIEGE',              () => fire('siege_alert', 'siege', true));
  bus.on('raid.attack.launched',          () => fire('siege_alert', 'siege', true));
  bus.on('crew.chest.ready',              () => AK.playSfx('crew_chest_ready'));
  bus.on('crew.chest.open',               () => fire('crew_chest_open', 'chest'));
  bus.on('crew.war.countdown',            (p) => AK.playSfx('war_tick'));          // engine pitches by p.tier
  bus.on('crew.war.start',                () => fire('war_horn', 'war_now', true));
  bus.on('crew.reinforcement.requested',  () => fire('reinforce_call', 'lance'));
  bus.on('crew.reinforcement.filled',     () => fire('reinforce_arrive', 'chest'));
  bus.on('crew.ascension',                (p) => fire('ascension_' + (p.tier||'bronze'), 'ascension', true));
  bus.on('progression.prestige',          (p) => fire('ascension_' + (p.tier||'bronze'), 'ascension', true));
  bus.on('dvd.phase',                     (p) => fire('dvd_' + p.phase, p.phase==='siege' ? 'siege' : null, true));
  bus.on('dvd.tower.captured',            () => fire('dvd_capture', 'chest'));
  bus.on('dvd.contribution',              () => AK.playSfx('dvd_contribute'));
  bus.on('squad.synergy.proc',            (p) => fire('synergy_proc', (p.count>=4)?'knock':null));
  bus.on('combo.proc',                    () => AK.playSfx('synergy_proc'));
  bus.on('building:damaged',              () => fire('building_hit', 'tower_hit'));
  bus.on('building:destroyed',            () => fire('building_destroyed', 'bld_down', true));
  bus.on('building:repaired',             () => AK.playSfx('building_repaired'));
  bus.on('crate.open',                    (p) => fire('crate_' + (p.tier||'wooden'),
                                                 (p.tier==='golden'||p.tier==='neon') ? 'chest' : 'melee'));
}
```
Music ducking / crossfades + screen-shake + the CSS visual pulses are handled in the renderer adapter that
also listens to these same events (so a headless run is a clean no-op). The AudioDirector itself only touches
`AK.playSfx` + `AK.haptic`.

## 6. ENGINE DELTAS (small, additive, byte-safe)
**`SFX_NAMES` (engine.js ~L4451) -- append so loadAllSfx() preloads the mp3s:**
```js
,'siege_alert','crew_chest_open','crew_chest_ready','war_horn','reinforce_call','reinforce_arrive',
'ascension_bronze','ascension_silver','ascension_gold','ascension_platinum','ascension_diamond','ascension_crown',
'dvd_hype','dvd_siege','dvd_capture','dvd_rebuild','synergy_proc',
'building_hit','building_destroyed','building_repaired','crate_metal','crate_neon','crate_golden'
// war_tick / dvd_contribute / crate_wooden / synergy_step are ZzFX-baked (no preload needed)
```
**`HAPTIC_PAT` (engine.js ~L4421) -- append the new big-moment patterns:**
```js
,siege:[40,60,40,60,200]      // raid siege klaxon (force)
,chest:[10,30,10,30,80]       // crew-chest / crate-neon+golden / capture (celebratory)
,war_now:[60,40,120]          // war countdown -> NOW (force)
,ascension:[30,50,30,50,250]  // prestige ascension -- the grandest (force)
,bld_down:[45,40,85]          // hub building destroyed in a raid (force)
```
**Expose `haptic` on the AK adapter (engine.js AK object ~L4554), one line, so the AudioDirector can fire it:**
```js
haptic(kind, force){ try{ haptic(kind, force); }catch(_e){} },
```
Everything else (shake, music duck, CSS pulse) already exists. No combat-sim change. No new timing. Headless
harness = silent no-op (navigator.vibrate guard + sample/synth no-op).

## 7. PRODUCTION ORDER (most-felt first)
1. **Crew-chest open + Alley-crate tiers** -- the reward-formula sounds; biggest retention lever, fired most.
   (`crew_chest_open`, `crate_metal/neon/golden`; `crate_wooden` via ZzFX.)
2. **Raid siege alert + building damage** -- the "come on buddy" Tier-1 threat loop (the reason they re-open).
3. **Ascension (6 tiers)** -- the rare grand reward; make Crown unmistakable.
4. **War countdown + reinforce** -- the crew-war urgency texture (ZzFX tick + 11L horn + reinforce pair).
5. **DvD phase stings + siege anthem** -- the monthly event; needs the Suno anthem crossfade.
6. **Squad combo/synergy** -- in-match polish; short, varied, ducked so it cuts.

Every name ships TODAY as a synth placeholder; this order is the upgrade-to-bespoke sequence, not a blocker.
