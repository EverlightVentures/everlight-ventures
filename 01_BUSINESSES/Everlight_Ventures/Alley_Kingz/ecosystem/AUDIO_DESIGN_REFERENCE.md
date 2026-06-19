# ALLEY KINGZ -- AUDIO DESIGN REFERENCE & RECIPE BOOK
"Sound is as important as the graphics." -- Operator directive, 2026-06-17.
Premium cyberpunk dog battler (Clash-Royale-style). Goal: generate custom sounds modeled on proven
winners so the game FEELS like the titles whose audio players love. Section 6 maps onto the engine's
sfx()/sfxCard()/playSample() system. Every claim cited (URLs at bottom).

## THE 6 PRINCIPLES THAT MATTER MOST
1. **Every SFX = transient + body + tail.** The transient (sharp high-freq snap, <10ms) makes a sound
   punchy and cut through the mix; body (80-300Hz) = weight; tail = decay. SHARPEN the transient rather
   than raise volume. Universal recipe for hits, taps, everything.
2. **Readability beats realism (the Supercell rule).** Every important event needs a DISTINCT,
   identifiable sound -- you should know what happened with your eyes closed. Clash Royale codes
   melee=heavy/dull, ranged=sharp/high, legendaries=signature roars.
3. **Fire under ~40ms.** The sound must land on the same frame as the action. 4ms undetectable, ~15-30ms
   noticeable, 100ms+ obvious; expert players have LOWER tolerance. Trim every sample so the transient
   is at sample 0.
4. **Vary pitch/timbre per play or it fatigues fast.** Small randomized pitch shifts + 2-3 round-robin
   variations on frequently-played sounds. AK already pitches by breed-size/cost + tints by faction --
   feed it neutral bases + a couple variants.
5. **Reward sound = anticipation, not payoff.** Dopamine fires on the BUILD-UP. Winning formula: rising
   riser -> satisfying crack -> ascending pitch run (root->3rd->5th->octave = "it got better") ->
   sparkle tail, ESCALATING by rarity (Common=2-note chime, Mythic=full fanfare+sub+lush shimmer). The
   single biggest retention lever.
6. **Lobby music = anime-OP hype; battle music = tense focus.** Lobby ~150-175 BPM J-rock + cyberpunk
   synth, hook in first 10-20s, loop the chorus. Battle beds ~90-120 BPM, atmospheric, under the SFX.

Reference takeaways: Clash Royale/Supercell = sound-as-readability + chest fanfare climax; Hearthstone =
musical pacing + a distinct spell layer + "subjective" per-card design from art (not animation); Marvel
Snap = one signature "snap" = the sonic logo. Common thread in beloved-audio games: readability,
escalating reward fanfares, musical pacing, a signature identity, tight/short/varied sounds.

## ENGINE REALITY (recipes plug straight in)
sfx(name) is SAMPLE-FIRST: plays `assets/sfx/<name>.mp3` at a per-card playbackRate, falls back to a
procedural `tone()` synth if the mp3 is missing. Per-card "voice": breed size -> bark pitch/length,
weaponType -> attack family, cost -> fattens the hit, faction -> timbre tint, rarity -> shimmer. 8-voice
cap + compressor + `ak_muted`. To add/upgrade ANY sound: generate an mp3, name it the engine event, drop
in assets/sfx/, add to SFX_NAMES to preload. The synth fallback is the placeholder/spec.

## REWARD-SOUND FORMULA (the engagement driver)
Dopamine fires on ANTICIPATION not receipt -- design the build-up. (1) anticipation layer (riser/tick
before the reveal) (2) the break/impact (transient+body) (3) ascending pitch run (4) sparkle/shimmer tail
(5) escalate by rarity tier. Sound is a deliberate dopamine trigger; variable reinforcement = retention.

## COMBAT IMPACT RECIPE
Impact = transient + body + tail (+ sub for heavy, + mechanical). 3-5 layers per hit. Differentiate by
which layer dominates: bullet=transient-forward/tiny body; cannon=sub+body/long tail; beam=sustained mid
whine/no transient; melee=body thud+organic crunch. Pitch-per-unit so 50 simultaneous hits stay legible
(AK does this via playbackRate). Attacker-sound (fire) vs getting-hit-sound (impact) are two distinct
events in time = cause->effect (call & response). Cap voices + duck minor sounds so the key hit cuts.

## ANIME-OP / HYPE MUSIC (lobby)
~150-200 BPM pop-punk/alt feel (120-160 heavier rock). J-rock core: driving electric guitars, tight live
drums, bass, bright synth stabs, hooky melody. Structure: short identifiable intro -> verse -> pre-chorus
(build) -> chorus (the lift/drop) -> v2 -> chorus -> bridge -> final chorus. HOOK in the first 10-20s. For
AK: fuse J-rock energy with cyberpunk/street -- analog synth bass, trap hats under rock drums, neon arps.
Loop the chorus as the lobby bed. Battle themes lower-energy so lobby = "the rush", combat = "the work".

## SECTION 6 -- PER-SOUND RECIPES + READY-TO-USE GENERATION PROMPTS
House style: gritty TV-MA cyberpunk dog gangs, neon-noir, analog synth + street grime. Short, punchy,
readable. Generate 3-8 variations, pick the punchiest, normalize ~-3dBFS, trim so the transient is at
sample 0, export mp3, name = engine event, drop in assets/sfx/. Make 2-3 variants of hit/deploy/scoop/tap
for round-robin. (Tool: ElevenLabs Text-to-SFX for these per AUDIO_TOOL_DECISION.md.)

### COMBAT ATTACK (atk_melee/bullet/cannon/beam/lance/spread) -- ~60-250ms
- atk_melee: "Short brutal melee impact, dog bite crunch plus low body thud, dry, punchy, no reverb, 120ms"
- atk_bullet: "Quick suppressed pistol-style snap, sharp transient, minimal body, dry, 80ms"
- atk_cannon: "Heavy cannon boom, deep sub thump, sharp crack transient, cyberpunk artillery, 350ms"
- atk_beam: "Sci-fi energy beam whine, rising synth, electric crackle, neon laser, 200ms"
- atk_lance: "Metallic piercing lance jab, sharp metal transient, short ring tail, 120ms"
- atk_spread: "Shotgun spread double-snap, two fast transients, scattered debris tail, 150ms"

### COMBAT HIT (the getting-hit answer)
- hit_impact: "Short dull flesh/metal hit thud, low, dry, 60ms, no tail" (keep tiny -- combat texture)
- tower_hit: "Concrete/metal structure crack, low impact, debris flecks, 200ms"
- tower_down: "Building collapse rumble, deep sub, crumbling debris, dramatic, 600ms"
- death: "Cyberpunk robot-dog power-down, short descending whine plus low thud, mournful, 250ms"

### KEYWORD PROCS (must be instantly distinct from normal hits)
- kw_burn: "Igniting fire whoosh into a sizzling crackle, loop-friendly tail, aggressive, 250ms"
- kw_deadly: "Ominous low hit then a sharp high danger sting, lethal, cyberpunk, 200ms"
- afterlife: "Ethereal spectral spawn, descending reverse-reverb shimmer, ghostly dog spirit, 350ms"

### EVOLUTION + LOADING
- evo_up: "Triumphant power-up tier-up fanfare, fast ascending arpeggio, bright synth + sparkle, cyberpunk,
  600ms" (it's a REWARD moment -- escalate brightness/length per tier)
- boot_reveal: "Cinematic whoosh into a neon chime, anticipation build, premium UI reveal, 700ms"

### CHEST OPEN BY RARITY (the #1 engagement sound -- escalate per tier, a la Clash Royale)
- Common: "Small loot crate pop, quick wood crack, soft two-note chime, 400ms"
- Rare/Epic: "Treasure chest unlock, rising anticipation riser, satisfying latch crack, ascending bright
  arpeggio, magical sparkle tail, 900ms"
- Legendary/Mythic: "Epic legendary chest opening, big anticipation riser, golden explosion burst,
  triumphant brass-and-synth fanfare, cascading sparkle, deep sub, grand-prize energy, cyberpunk royal,
  1600ms" (make chest_open_common..chest_open_mythic, or pitch/scale one base)

### REWARD + LOOT
- reward: "Reward collected shimmer, ascending bright bells, coins/credits cascade, satisfying, 500ms"
- scoop0-4: "Quick bright pickup blip, satisfying coin/shard scoop, clean transient, 80ms" (engine pitches
  by tier, or make 5 rising variants -- a rare scoop should READ over combat)

### UI
- tap: "Crisp premium UI tap click, short snappy transient, high-mid, dry, 40ms" (2 variants)
- ui_open: "Soft UI panel open whoosh into a gentle chime, premium, 200ms"
- ui_error: "Subtle UI error tone, short descending two-note, polite negative, 200ms" (clearly != success)

### VICTORY / DEFEAT / DEPLOY / TRANSITIONS
- win: "Triumphant victory fanfare, rising major chord brass + synth, celebratory, cyberpunk anthem, 2s"
- lose: "Defeat sting, descending minor melody, somber synth, short, 1.5s"
- deploy: "Unit deploy thump plus short aggressive dog bark/grunt, street gang energy, punchy, 250ms"
- sting_major: "Major positive transition sting, bass drop into bright ascending triad, gold/premium, 700ms"
- sting_minor: "Urgent transition sting, bass drop into tense rising chord, time-pressure, 700ms"
- tick: "Crisp countdown tick, short high click, 60ms"

### SPELLS & STORMS (the distinct spell layer -- clearly NOT a unit)
spell_freeze "icy freeze crackle, glassy shimmer, frost snap 400ms"; spell_tar "thick gloopy splat, sticky
low squelch 400ms"; spell_snare "snapping net/trap clamp 300ms"; spell_jolt "electric zap arc 300ms";
spell_strike "magic strike, transient crack + low boom 350ms"; storm_lightning "thunder rumble -> sharp
crack 1.2s"; storm_flood "rising water surge, low rumble 1.5s"; storm_scraprain "metal scrap clatter
1.5s"; storm_drone "ominous low atmospheric drone, loopable 2s"; golden_hour "warm radiant golden swell,
hopeful shimmer 1.5s"; crown "royal crown chime, regal bell flourish, premium gold 600ms".

### MUSIC (assets/music/, wire to the _bgm deck)
- Lobby (the_lot): "150 BPM energetic J-rock anime opening, driving electric guitars, live drums, neon
  synth arpeggios, analog bass, triumphant hooky chorus, cyberpunk street-gang energy, loopable,
  instrumental" (Suno, per AUDIO_TOOL_DECISION.md; lock a Persona for consistency)
- Battle districts: lower-energy tense beds ~90-120 BPM; subway=industrial techno, casino=neon synthwave,
  frost=cold ambient, citadel=epic. Keep under the SFX bed.

## PRODUCTION CHECKLIST (every sound)
1. Trim the head -> transient at sample 0 (latency). 2. EQ for mobile (roll off muddy lows, keep the
high-mid snap). 3. Sharpen the transient (punch without loudness). 4. 2-3 variations of frequently-played
sounds for round-robin. 5. Normalize ~-3dBFS (engine compressor + 0.5 master mixes). 6. Test on a phone
speaker muted + unmuted. 7. Readability check: can you tell what happened eyes closed? 8. Name = engine
event, drop in assets/sfx/, add to SFX_NAMES.

## SOURCES
Juice: GameAnalytics; Game Developer; Vlambeer "Art of Screenshake". Latency: ACM (JND audio latency);
Games Learning Society; ACM (auditory latency on FPS). Combat/layering: Splice; Pro Sound Effects (Kilborn);
Pixflow; A Sound Effect; Audiokinetic. Pitch/round-robin: A Sound Effect; Game Developer; Andrew Mushel;
SoundBridge. Reward psych: Dodefy; PNAS (dopamine & music); JCOMA. Mobile refs: Powerplaygamers (Clash
Royale); Blizzard (Hearthstone harmonic design); Bigmouth (Marvel Snap); Supercell fankit; GDC (Brawl
Stars). UI: Toptal; SFX Engine; UXmatters. Anime music: Fandom; Apolline; Melodigging; Level Tunes.
