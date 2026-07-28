# Alley Kingz -- DEV TEAM PLAYBOOKS (Graphics / Audio / VFX+Haptics)
*Research-backed standards (Fortnite, WoW, Clash of Clans, Roblox) ADAPTED to OUR stack: AK is a browser HTML5/Canvas game, NOT UE5/Unity -- so the AAA tools are reference, but the PRINCIPLES + retention drivers + OUR real tools are the law. Feed these to the relevant build agents as reference. 2026-06-27.*

## OUR REAL TOOLCHAIN (what the AAA tools map to for a browser game)
- GRAPHICS: CF Workers AI + art_factory (image gen, free), Leonardo (when funded), ffmpeg on e5 (interior video loops), Canvas2D + CSS (render), the gold-cyberpunk palette from report_template.py. NO UE5/Maya/Blender pipeline -- we generate + wire 2D/2.5D art.
- AUDIO: WebAudio API (the districtmusic.js procedural bed + the needle-drop stinger system is OUR "adaptive music"); no Wwise/FMOD (browser). Adaptive = duck-and-drop on events (DONE), per-district key/scale (DONE).
- VFX: Canvas2D particles + CSS animations + the engine's fx (killstreak DOG-GOD glow, type auras) -- NO Niagara/Houdini; keep it 60fps on cheap Android. Haptics = the browser Vibration API (navigator.vibrate) on mobile.

## TEAM 1 -- GRAPHICS (principles that DO apply)
- ART DIRECTION CONSISTENCY > technical complexity (WoW): one style guide -- gritty gold-cyberpunk, strong SILHOUETTE readability, the gold #D4AF37 / dark #0A0A0A / light #E8E8E8 palette, Playfair/Inter type.
- MOBILE READABILITY (Clash): exaggerated proportions, limited high-contrast palettes, instant recognition; asset optimization (small files, fast load) is survival.
- MODULAR KITS: create once, reuse everywhere (district bg + facade + interior reuse).
- RETENTION DRIVERS: visual clarity (instantly read the screen); emotional color (warm=safe, cool=danger, saturated=reward); PROGRESSION VISIBILITY (gear/skins look increasingly impressive -- our killstreak tiers, rank chips); SOCIAL SIGNALING (rare = visually distinct -- the seasonal exclusive, mythic auras); biome diversity (our 9 districts must feel different).
- HARD LAW (ours): NO default emojis as icons; custom art everywhere (de-emojify doctrine); engine.js frozen.

## TEAM 2 -- AUDIO (principles that DO apply)
- ADAPTIVE MUSIC by gameplay state (Fortnite combat layers): OUR version = districtmusic.js bed + needle-drop on killstreak/tier-up (LIVE). Extend: layer intensity in raids/RPG combat.
- AUDIO FEEDBACK = DOPAMINE (Clash): every action has a satisfying sound (chest open, level up, claim). Mobile audio must work without headphones -- clear, punchy, short.
- ZONE/MUSIC NOSTALGIA (WoW): per-district music identity (DONE) -- players bond to a district's sound.
- AUDIO BRANDING: a recognizable AK sting (the crown/level-up). RETENTION: feedback loops, zone nostalgia, accessibility (visual indicator for every audio cue -- hearing-impaired).
- HARD LAW (ours): procedural WebAudio only, no asset bloat, 60fps, offline-capable.

## TEAM 3 -- VFX + HAPTICS (principles that DO apply)
- VFX COMMUNICATES STATE (Fortnite/WoW): effects clearly read hit/miss/crit/shield-break/status -- readability in a crowded fight is the design challenge (our raids + real-time combat).
- POWER FANTASY (WoW spells): abilities feel impactful -- the killstreak DOG-GOD, the real-time combat spells/lasers (P11). Spectacle for boss/ultimate moments (the throne, the season finale).
- MOBILE VFX = LIGHTWEIGHT (Clash): screen shake + camera kick amplify impact without heavy particles; cap particles; sprite/CSS over real-time lighting.
- HAPTICS (browser Vibration API): short crisp buzz for UI (50-100ms), pattern for rewards, intensity by impact; ALWAYS a toggle; respect battery. (e.g., claim the streak = a reward buzz; a hit in combat = a short buzz.)
- RETENTION: power fantasy, clarity, spectacle, tactile confirmation (haptic on every significant action), environmental storytelling (weather/destruction/zone effects -- we have day/night + weather now).

## CROSS-TEAM (the law)
1. Gameplay clarity OVER spectacle. 2. Performance budget discipline (every asset/sound/effect has a cost -- 60fps cheap Android). 3. Platform scalability (mobile first, enhance up). 4. ONE style guide all agents reference. 5. Iterative playtest. Integration: VFX triggers audio (the needle-drop on the DOG-GOD); audio LFE could trigger haptics; VFX respects the scene.
