# Alley Kingz -- Seedance Animated-Units Budget + Pipeline
**Date:** 2026-06-03 | For: operator (Rich). Goal: characters that VISUALLY WALK the lane -- taking steps, tires turning, steering, firing missiles. Premium, not cheap.

## The asset split (locked by this decision)
- **Leonardo portraits (41/48 done, ~$0.70)** = the CARD FACES. Static is correct there (the deck/hand art, like a Pokemon/Clash card). Keep them.
- **Seedance 2.0 clips** = the MOVING UNITS on the board (walk cycle, rig motion, weapon fire). This is the premium animated layer.

## Real Seedance 2.0 cost (researched 2026-06-03)
Per-second pricing varies a LOT by provider:
| Provider | $/sec | A 5s unit clip | Notes |
|---|---|---|---|
| Atlas Cloud (Fast, 2K) | ~$0.022 | **~$0.11** | cheapest, still 2K |
| fal.ai / PiAPI (3rd-party API) | ~$0.05-0.08 | **~$0.25-0.40** | best dev API, scriptable |
| Official ByteDance/Volcengine | ~$0.14 | **~$0.70** | top quality, source |
| Dreamina credit bundles | ~$0.19/sec eff. | **~$0.95** | consumer credits |
Source: Atlas Cloud + fal + Volcengine pricing pages.

## The honest engineering truth (so it looks good AND runs)
You CANNOT play 48 live MP4s on a phone board -- it would stutter and die. How real mobile games (incl. Clash Royale) do animated units:
1. Generate a short Seedance clip of the character walking/firing **on a clean flat background** (so it can be cut out).
2. On **e5-mother** (phone proot cannot ffmpeg): extract frames -> remove background per frame -> assemble a **SPRITE SHEET** (one transparent PNG grid of, say, 8-16 frames).
3. The game **flipbooks** the frames per unit (draw the current frame each tick) = smooth walk/fire animation at ~zero cost. Dozens on screen, still 60fps.
So: Seedance makes the MOTION; we bake it into a sprite sheet; the game plays it cheap.
**Hard part (the "not cheap" effort):** getting clean transparent frames from a cinematic clip. We generate on a solid background for easy keying and gate every sheet through the Art Review. This is where the polish time goes.

## Phased budget (do NOT bulk-buy before a proof)
| Phase | Scope | Clips | Est. cost (mid-tier ~$0.30/clip) | When |
|---|---|---|---|---|
| **PoC** | $BCARDD only: 1 walk-cycle clip -> sprite sheet -> in game | 1 | **~$0.30-0.70** | FIRST -- prove the look + the pipeline before spending more |
| **Category A** | The 4 Mythics ($BCARDD, Jagged, Rosco, Crown Foxhound) | 4 | **~$1.20-2.80** | after PoC approved |
| **Category B** | One full faction (12 cards) | 12 | **~$3.60-8.40** | the "at least one category" you asked for |
| **Full set** | all 48 units | 48 | **~$14-34** | only after the style is locked |
| **NFT heroes** | the cinematic 16:9 hero/NFT clips (separate, premium) | ~5 | ~$3-7 | the on-chain collection, Seedance 2.0 best tier |
Each clip is 4-5s. Prices scale with provider tier; "looks good not cheap" = the fal.ai or official tier, ~$0.30-0.70/clip.

## Division of labor
- **AI builds (free):** the per-character motion prompts (walk + fire + rig motion), the frames->sprite-sheet pipeline script (runs on e5), and wires the game to flipbook the sheets (fallback to the static icon, then the shape).
- **You provide:** the Seedance 2.0 access/credits (the only real spend) + the spend cap.
- **e5-mother runs:** the ffmpeg frame extraction + background removal + sheet assembly (phone proot cannot).

## Recommendation
Do the **1-clip PoC on $BCARDD first (~$0.50)**. AI-video-to-game-sprite is finicky; prove ONE looks good and animates smoothly in the game before committing a category budget. Then knock out **one faction (12)** as your first full "category." Hold the full 48 + NFT heroes until the look is locked.
