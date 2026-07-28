# AK x HIGGSFIELD PIPELINE
## Alley Kingz asset factory on the Higgsfield CLI (PLUS plan, ~970 credits remaining this cycle)
Date: 2026-07-01 (v2 merge: external Higgsfield research folded in, corrected to our account + canon) | Owner: Lucrex / Everlight Researcher | Status: TRAILER FIRST, then P1/P2/P3 batches

Account reality (overrides any generic figure): PLUS plan, ~970 credits left this cycle. Credits do NOT roll over. We do not have Ultra/3000. No new subscriptions get added to this plan (no ElevenLabs upgrade, no "$130/mo stack"); Plus + free Cloudflare is the stack.

---

## 0. GROUND TRUTH (what Higgsfield actually is, verified 2026-07-01)

- CLI installed on e5, driven by Claude over `ssh e5` (a `higgsfield` shim exists phone-side). CLI is cheaper than MCP for agent workflows (no tool-schema token tax).
- Core commands (from github.com/higgsfield-ai/cli README):
  - `higgsfield auth login` / `higgsfield account` (credit balance + transactions)
  - `higgsfield model list` / `higgsfield voices list` / `higgsfield workflow list`
  - `higgsfield upload <file>` (push reference images/video)
  - `higgsfield generate create <model> ...` / `generate wait <job_id>` / `generate get` / `generate list`
  - `higgsfield generate cost` (ESTIMATE CREDITS BEFORE EVERY BATCH. This is law.)
  - `higgsfield soul-id create --name <name>` + `soul-id wait <soul_id>`
  - `higgsfield website create` / `website deploy <id> --env production` (React 19 + TanStack on Cloudflare Workers, D1 + R2)
  - Flags: `--wait`, `--wait-timeout 10m`, `--json` (always use `--json` when Claude drives)
- 45+ models. Relevant: Kling v3.0, Veo 3.1, Seedance 2.0, Wan 2.7, WAN 2.2 Animate, Minimax/Hailuo (video); Soul V2, Nano Banana Pro, FLUX.2, Recraft V4.1 (image); Speak 2.0 (lip-sync talking heads); `multi_image_to_3d` (3D); `text2speech_v2`, `sonilo_music`, `mirelo_text_to_audio` (audio). Workflows: `draw_to_video`, `reframe` (9:16 repurpose), `voice-change`, `dubbing`. `brain_activity` = virality predictor scoring for finished videos.

### MEASURED COSTS (our own CLI runs; these beat any third-party figure)

| Item | Measured cost | Implication |
|---|---|---|
| Soul ID training | 25 credits (paid, done) | one-time; BCARDD Soul is live |
| Soul V2 image | 0.12 credits | images are near-free; iterate stills freely, never skimp on keyframe exploration |
| Kling 3.0 std 5s video | 7.5 credits | the workhorse rate; start-frame = end-frame seamless loop works natively |

Everything else in this doc (Veo, WAN 2.2 Animate, Speak 2.0, TTS per-line) is UNVERIFIED third-party pricing until we run `generate cost` on it. Measured beats quoted, always.

### FACT vs MYTH corrections (important, budget-honest)

1. **"AutoSprite Animation model" is NOT a Higgsfield model.** AutoSprite (autosprite.io / sorceress.games) is a SEPARATE product: upload one character image, pick a moveset (idle / walk / run / jump / attack / custom, per direction), it exports a PNG sprite sheet + atlas JSON ready for Phaser/Unity/Godot. It has a free tier (3 credits/day, commercial use OK) and its own MCP server. **Verdict: use AutoSprite.io free tier as lane A for sprite sheets (zero Higgsfield credits), and Kling 3.0 video + ffmpeg frame-slice as lane B when AutoSprite's style drifts off the AK look.** Free-first rule satisfied.
2. **There is NO `higgsfield game` command in the CLI.** "Higgsfield Games" is a separate product on their Supercomputer platform + MCP: prompt-to-playable browser games, auto hosting + shareable URL, one-toggle multiplayer, marketplace + remix. Their own announcement says games are "powered by Claude Fable 5." **Verdict: Supercomputer/Games = PROTOTYPING ONLY.** Do NOT rebuild Alley Kingz on it (AK canon: wrap, don't rebuild; e5 ship.sh is the sole deploy path). Acceptable uses: throwaway marketing playables and microgame spinoffs (e.g. a 60-second "BCARDD alley run" that funnels to alleykingz.online). The `website` command is real but AK already has hosting; ignore it for the game.
3. **Soul ID on BCARDD: RESOLVED, it works.** The experiment paid off despite the "human faces, avoid sunglasses" guidance. The $BCARDD Soul is TRAINED: id `91e8b2b5-a0af-4fd1-b266-544f064a7732` (25 credits, one-time). Identity now comes for free on every Soul V2 still at 0.12 credits. Wardrobe CAN change between shots as long as the dog stays consistent; the crown, flag-tint aviators, $-style B chain pendant, cigar, breed, fur color, and cropped ears never change.

### Model choice cheat sheet (our measured figures where we have them)

| Job | Model | Why | Est. credits |
|---|---|---|---|
| Character action (walk/attack cycles, cutscene beats) | **Kling 3.0** | best character-driven video, 4K, start/end frame control, cheapest workhorse | **7.5/5s clip (MEASURED)** |
| Seamless ambient loops | **Kling 3.0** start-frame = end-frame | native perfect-loop trick, confirmed in our runs | **7.5/clip (MEASURED)** |
| Card idle animations (breathing, blink, tail-wag) | **WAN 2.2 Animate** | static card art + a motion reference video in, animated character out; purpose-built for exactly this | unverified; run `generate cost` in P0 |
| Talking keepers (lip-sync) | **Speak 2.0** | portrait + audio in, talking head out; wires straight into existing keeper dialog | unverified; run `generate cost` in P0 |
| 1-2 hero atmospheric shots only (trailer opener, DOG-GOD reveal) | **Veo 3.1** | best outdoor/atmosphere + native audio; EXPENSIVE | 22 (Veo 3 Fast 8s) to 58-70 (premium, unverified) |
| Fast short-form / TikTok volume | **Minimax/Hailuo or Seedance 2.0 Fast** | speed + cost | low-mid (unverified) |
| Cinematic camera language (district intros, combat intros, trailer spine) | **Cinema Studio 3.0/3.5** | 70+ presets, 50+ named camera moves, stereo audio, 15s max | mid (unverified) |
| Stills (cards, interiors keyframes, shop art, storyboards) | **Soul V2 / Nano Banana Pro / FLUX.2** | 4K stills, Soul ID + reference conditioning | **0.12/image (MEASURED, Soul V2)** |
| In-game VO | **text2speech_v2** (+ `voices list`, 21 presets, cloning) | IN-PLAN, free-first winner; ElevenLabs is fallback only, never a new subscription | ~1/line (unverified) |

At 7.5/clip measured, 970 credits = ~129 Kling clips if nothing else were funded. But the trailer ring-fence and reserve come first (Section 3). Community reviews warn of a 3-5x iteration factor on "usable" video outputs; stills at 0.12 are where iteration is free, so lock the keyframe BEFORE spending 7.5 on motion.

### Prompting doctrine (community, 2026)

- **MCSLA formula** (OSideMedia Claude skill for Higgsfield): Model, Camera, Subject, Look, Action. Build every video prompt in that order.
- **Separate identity from motion**: the Soul ID / reference image carries WHO, the prompt carries WHAT HAPPENS. Never re-describe the character differently between shots; paste the same canon block verbatim.
- Presets beat freehand on Soul 2.0; Cinema Studio named camera moves beat prose camera descriptions.
- Sprite lane: prompt "locked static camera, full body side view, solid bright green chroma key background #00FF00, character occupies center frame, no camera motion" then chroma-key in ffmpeg.
- Loop lane: same image as first AND last frame = perfect loop (confirmed working natively in our Kling 3.0 runs); for pure ambient motion (steam, neon flicker, rain) first-frame-only is enough and a forced end frame can hurt. Frame-chaining (last frame of clip N = first frame of clip N+1) builds longer cutscenes with continuity.
- Install their skills: `npx skills add higgsfield-ai/skills` (ships `/higgsfield:generate`, `/higgsfield:soul-id`, `/higgsfield:product-photoshoot` 10 modes, `/higgsfield:marketplace-cards`, `/higgsfield:websites`). Also worth adding: `OSideMedia/higgsfield-ai-prompt-skill` (20 sub-skills, MCSLA, Kling Motion Control, 17 templates).

---

## 1. THE $BCARDD CANON (Soul ID + blocks + name registry)

**Soul ID (trained, live): `91e8b2b5-a0af-4fd1-b266-544f064a7732`** -- reference it on every Soul V2 still. For video, use the approved Soul V2 still as the Kling start frame.

Canon block (paste verbatim into EVERY BCARDD prompt):

```
CHARACTER CANON (do not change, do not restyle): a white Dogo Argentino dog,
cropped ears clearly visible, wearing a gold crown, aviator glasses with
American-flag tint lenses, a gold chain with a dollar-sign-style B pendant,
smoking a cigar. Exact same dog in every frame. Wardrobe and outfit may vary
by scene, but never remove or swap the crown, glasses, chain, pendant, or
cigar. Never change breed, fur color, or ear crop.
```

AK style block appended to every prompt (BCARDD or not):

```
STYLE: dark 90s-kid nostalgia, Twisted Metal energy, gritty gold-cyberpunk
alley world. Grimy urban textures, chain-link, wet asphalt, neon signage,
gold (#e8c55a highlights, #c9a84c mids) rim light against vanta black
shadows, VHS-era grit, moody cinematic contrast. Always dog-themed.
No cute pastel, no corporate clean, no purple/cyan synthwave palette.
```

### CANON NAME REGISTRY (the ONLY names that exist; never invent, never accept invented names from external docs)

- **Keepers (building NPCs)**: Coach Diesel (Town Hall), Prospector Pip (Gem Mine), Banker Bones (Gold Mint), Sparks (Card Forge), Doc Wattson (Research Lab), Volt (Generator), Patch the Medic (Infirmary), Marrow the Fixer (The Fixer)
- **Clans**: Zoomie Syndicate, Leashbreak Tactix, Boneguard Crew, K9 Circuitry
- **Districts**: THE LOT, DOWNTOWN, NEON HEIGHTS, THE YARDS, FACTORY ROW, THE STRIP, THE DOCKS, THE OVERLOOK, THE UNDERCITY
- **Ranks**: Stray up through King of the Block
- **Story**: THE CROWN BLOODLINE (the Old Pack, the Mongrel King)

If a name is not on this list, it is not in the game. Any external brief inventing characters or factions gets corrected to this registry before a single credit is spent.

---

## 2. OPPORTUNITY MAP (ranked by player impact; [P1]/[P2]/[P3] = funded this cycle, [LATER] = next cycle)

### [P1] Card idle animations (WAN 2.2 Animate)
- **Gap**: battle cards are static art; a subtle idle (breathing, blink, tail-wag, chain glint) on the TOP cards is the highest-visibility motion per credit in the whole game.
- **Model**: WAN 2.2 Animate: existing static card art + ONE motion reference video (record/generate a single generic "idle breathing dog" reference, reuse it across every card).
- **Recipe**: `[WAN 2.2 Animate, image = card art, motion ref = idle_ref.mp4] Action: subtle idle only: slow breathing, occasional blink, faint tail movement, gear sway. Camera locked. Character stays in card pose. Loops cleanly.`
- **Credits**: unverified; P0 validates one card first. Planning figure ~7.5/clip x 12 top cards x 1.5 iterations = ~135.
- **Wire-in**: `ecosystem/game/assets/cards/anim/<card>_idle.mp4` (720p h264, <1MB); card renderer swaps static art for the loop ONLY on the focused/inspected card (performance budget, Section 3.5). Static art stays as poster fallback.

### [P2] Talking keepers (Speak 2.0 lip-sync)
- **Gap**: keeper dialog exists as text; lip-synced talking heads make the eight keepers feel alive for a handful of credits.
- **Model**: `text2speech_v2` for the line audio (in-plan, free-first) then Speak 2.0: keeper portrait + audio in, talking head out. ElevenLabs is fallback ONLY if TTS quality fails validation; no new subscription either way.
- **Recipe**: one locked voice per keeper in `VOICE_CAST.md`; lines under 12 words, gritty register. Coach Diesel: "Back to work, pup. The Block don't run itself." Banker Bones: "Gold in, gold out. Crown takes its cut." Portraits = existing keeper art (Soul V2 upscale/redo at 0.12 if a portrait is too rough for lip-sync).
- **Credits**: unverified; P0 validates one keeper line end-to-end. Planning figure ~80 for 8 keepers x 2-3 lines + iterations.
- **Wire-in**: `ecosystem/game/assets/keepers/<keeper>_<line>.mp4`; plays in the existing keeper dialog panel on building open, muted-by-default with tap-for-sound, static portrait fallback.

### [P3] District intro loops + screen transitions (Kling 3.0 + Cinema Studio moves)
- **Gap**: the nine districts (THE LOT through THE UNDERCITY) are named but not felt; a 5s ambient loop with a named Cinema Studio camera move as each district's intro is cheap atmosphere. Same lane covers combat-intro transitions.
- **Model**: Kling 3.0 (start=end frame loop) for ambient; Cinema Studio named moves (slow push-in, crane down, whip pan) for intro/transition beats.
- **Recipe**: `Camera: slow push-in through chain-link (Cinema Studio preset). Subject: <district> establishing shot, no characters. Look: <STYLE BLOCK>. Action: neon flicker, steam, rain sheen, hanging chain sways. Motion returns to the exact starting state.`
- **Credits**: 7.5 x 5 priority districts x 1.5 iterations = ~56, + ~40 for 3-4 combat/screen transitions = ~100 this cycle. Remaining districts next cycle.
- **Wire-in**: `ecosystem/game/assets/districts/<district>_loop.mp4`; fullscreen behind the district UI, lazy-loaded on district open only, per the performance budget.

### [LATER] Animated hero walk/attack cycles (sprite sheets)
- **Gap**: heroes/handlers are static; motion is a big "alive" upgrade but heavier per credit than card idles.
- **Model**: Lane A: AutoSprite.io free tier (3/day, runs in parallel EVERY day at zero cost, start now). Lane B: Kling 3.0 image-to-video, chroma green, ffmpeg slice.
- **Credits (Lane B)**: 7.5 x 6 handlers x 2 iterations = ~90. Funded next cycle unless AutoSprite free lane covers it first.
- **Wire-in**: `ecosystem/game/assets/sprites/<name>_walk.png` + atlas JSON; canvas render loop swaps static portrait for sheet playback.

### [LATER] Living building interiors (seamless ambient loops)
- Same technique as district loops (start=end frame). 7.5 x 8 interiors x 1.5 = ~90. Next cycle; district loops prove the lane first.

### [LATER] Crown Bloodline story cutscenes
- 10-15s cinematic beats between chapters (the Old Pack, the Mongrel King). Kling frame-chaining for continuity, Cinema Studio presets for camera, ONE Veo 3 Fast establishing shot max per chapter. ~7.5 x 10 beats x 2 + 22 Veo = ~172 per chapter. Next cycle; storyboard stills can be built THIS cycle at 0.12/image (near-free pre-production).
- **Wire-in**: `ecosystem/game/assets/story/ch<N>_<beat>.mp4`; story spine triggers a fullscreen video overlay with skip button.

### [LATER] Killstreak / DOG-GOD spectacle overlays + victory/defeat stingers
- Kling 3.0, black background, `globalCompositeOperation = "screen"` over the arena canvas. Killstreaks ~7.5 x 4 tiers x 2 = ~60; stingers (BCARDD cigar puff + gold dog-tag confetti / rain on an empty crown) ~30. Never strip the existing glows; this layers on top.

### [FUNDED, RING-FENCED] Game trailer + IG trailer cuts
- **Operator priority #1 this cycle.** Cinema Studio 3.0/3.5 for the trailer spine, Kling for character beats (Soul V2 keyframes first at 0.12), `reframe` to 9:16 for the IG cuts, `brain_activity` virality score BEFORE posting (post only the top scorer).
- **Rules**: BCARDD content = fun and positive vibes ONLY, never investment framing (standing law). Founder stays faceless.
- **Credits**: ~300 ring-fenced (Section 3).
- **Wire-in**: `02_CONTENT_FACTORY/01_Queue/` for distribution; x_autopilot/content_engine pick up from there.

### [NEAR-FREE, ANYTIME] Marketplace product cards for the shop
- Soul V2 / Nano Banana Pro stills at 0.12/image, or `/higgsfield:marketplace-cards` skill. 12 SKUs x heavy iteration still costs ~5-10 credits total. Kills the "no generic art ever stays" debt (cur_*.jpg placeholders). Do this in idle time; it barely touches the budget.
- **Wire-in**: `ecosystem/game/assets/ui/` + Stripe shop images.

Deprioritized: `multi_image_to_3d` (AK is 2D canvas; revisit at WebGL decision), `sonilo_music` (AUDIO_FREE_STACK covers music), `website`/Games deploy (AK deploy = e5 ship.sh only; Supercomputer = prototyping only).

---

## 3. BUDGET PLAN: ~970 CREDITS THIS CYCLE (no rollover)

Hard rules: run `higgsfield generate cost` before every batch (unverified figures are planning numbers, not gospel). Log every job to the ledger. Kling by default; Veo only on explicit sign-off per shot. Stills iterate freely at 0.12; video never generates until the keyframe is operator-approved.

| Phase | What | Est. credits | Gate |
|---|---|---|---|
| **RESERVE** | untouchable | **250** | released only by operator; credits do NOT roll over, so operator decides release/redeploy by ~day 25 of the cycle or they evaporate |
| **TRAILER** | game trailer + 2 IG cuts (Cinema Studio + Kling + reframe + brain_activity) | **~300** | ring-fenced, operator priority #1 |
| **P0 Validation** | 1 WAN 2.2 card idle + 1 Speak 2.0 keeper line (TTS in-plan) + 1 Kling district loop + `generate cost` on every unverified model | **~30** | operator tests EACH in the live game before any batch unlocks |
| **P1 Card idles** | ~12 top cards via WAN 2.2 Animate | **~135** | P0 pass |
| **P2 Keeper lip-sync** | 8 keepers x 2-3 lines, text2speech_v2 + Speak 2.0 | **~80** | P1 shipped |
| **P3 District loops + transitions** | 5 priority district loops + 3-4 screen/combat transitions | **~100** | P2 shipped |
| **Float** | re-rolls across phases; sweep into extra P3 districts or storyboard stills before cycle reset | **~75** | as needed |
| **Total** | | **~970** | |

### Week-by-week build sequence (rescaled to PLUS credits)

- **Week 1**: P0 validation (+ cost-verify WAN/Speak/TTS/Cinema). Trailer pre-production in parallel: storyboard + keyframes as Soul V2 stills at 0.12 each (a 40-still storyboard costs ~5 credits). AutoSprite free lane starts its daily 3-credit drip.
- **Week 2**: TRAILER week. Burn the ~300 ring-fence on the game trailer + 2 IG cuts. reframe to 9:16, brain_activity score, post top scorer only.
- **Week 3**: P1 card idle batch (top 12 cards). Ship, verify live, ledger.
- **Week 4**: P2 keeper lip-sync + P3 district loops/transitions. Final sweep: spend remaining float on stills/storyboards (near-free) rather than stranding credits; confirm reserve decision with operator before the cycle resets.

If iteration burn exceeds 2x on any phase, stop, tighten prompts against this doc, and re-estimate before continuing.

### 3.5 VIDEO PERFORMANCE BUDGET (game-side law, Canvas2D browser game)

- **Max 3 videos playing concurrently**, ever. Card idle plays only on the focused card; district loop pauses when a dialog covers it.
- **Lazy-load**: no video asset loads until its screen is opened. Nothing video in the initial bundle.
- **Static fallback always**: every video has its source still as poster; if decode fails, is offscreen, or the 3-slot budget is full, the static art shows instead.
- **Encode target**: 720p h264, muted, `playsinline`, <1MB per loop (`ffmpeg -crf 28 -preset slow -movflags +faststart`, strip audio).
- Pause and release offscreen videos; never let hidden `<video>` elements keep decoding.

---

## 4. THE 9-STAGE PRODUCTION PIPELINE (Claude drives, e5 executes)

Every asset moves through the same nine stages; no stage skips:

1. **Brief**: asset name, canon block, registry names only, budget line it charges against.
2. **Cost estimate**: `higgsfield generate cost` (law), result written to the ledger.
3. **Reference prep**: Soul V2 stills at 0.12 (Soul ID `91e8b2b5-...` for BCARDD); iterate freely here, this is the cheap stage.
4. **Still lock**: operator approves the keyframe. No motion credits before this.
5. **Motion pass**: Kling 3.0 / WAN 2.2 Animate / Speak 2.0 / Cinema Studio per the cheat sheet.
6. **Post-process**: ffmpeg on e5 (chroma key, loop trim, loudnorm, 720p h264 <1MB).
7. **Wire-in**: asset into `ecosystem/game/assets/...`, code hookup (sprite player / video layer / audio map).
8. **Ship**: rsync -> e5 -> ship.sh. SOLE deploy path. GitHub Action stays DISABLED.
9. **Verify + log**: operator plays it live on alleykingz.online; job_id, model, credits, verdict to the ledger + Blinko note.

The CLI lives on e5. Claude calls it via `ssh e5 'higgsfield ... --json'` (phone-side `higgsfield` shim wraps this). Nothing generates from the phone directly.

```bash
# 0. One-time setup (done: Plus plan, Soul trained)
ssh e5 'higgsfield account --json'                   # confirm ~970 credits
ssh e5 'npx skills add higgsfield-ai/skills'         # official prompt skills

# 1. Budget check BEFORE anything (law)
ssh e5 'higgsfield model list --json'
ssh e5 'higgsfield generate cost <model> ... --json' # write result to the ledger

# 2. Upload canonical references
ssh e5 'higgsfield upload /home/ubuntu/ak_refs/bcardd_canon_01.png --json'
# (rsync refs up first: rsync -av <game>/assets/refs/ e5:/home/ubuntu/ak_refs/)

# 3. Identity: Soul already trained. Reference it for stills:
#    soul_id = 91e8b2b5-a0af-4fd1-b266-544f064a7732 (0.12/image, iterate freely)

# 4. Generate (canon block + style block pasted verbatim, MCSLA order)
ssh e5 'higgsfield generate create kling-v3 \
  --image /home/ubuntu/ak_refs/bcardd_canon_01.png \
  --prompt "<MCSLA prompt with CANON + STYLE blocks>" \
  --duration 5 --wait --wait-timeout 10m --json'

# 5. Download on e5
ssh e5 'curl -sL "<result_url>" -o /home/ubuntu/ak_out/bcardd_walk_v1.mp4'

# 6a. Post-process: SPRITE SHEET (frame-slice + chroma key + pack)
ssh e5 'ffmpeg -i ak_out/bcardd_walk_v1.mp4 -vf "fps=12" ak_out/frames/f_%02d.png'
ssh e5 'for f in ak_out/frames/*.png; do ffmpeg -y -i "$f" \
  -vf "chromakey=0x00FF00:0.12:0.06" "${f%.png}_t.png"; done'
ssh e5 'ffmpeg -i ak_out/frames/f_%02d_t.png \
  -vf "scale=256:-1,tile=8x1" ak_out/bcardd_walk_sheet.png'
# hand-pick the 8 cleanest frames if gait drifts; write the atlas JSON alongside

# 6b. Post-process: GAME LOOP (start=end frame loops natively; encode to budget)
ssh e5 'ffmpeg -i ak_out/thelot_v1.mp4 -vf "scale=-2:720" \
  -c:v libx264 -crf 28 -preset slow -movflags +faststart -an \
  ak_out/assets_ready/thelot_loop.mp4'   # target <1MB per loop
# crossfade fallback only if a seam shows:
#   xfade=transition=fade:duration=0.5:offset=4.0

# 6c. Post-process: VO
ssh e5 'ffmpeg -i ak_out/vo_line.mp3 -af loudnorm=I=-16:TP=-1.5 assets_ready/vo_line.mp3'

# 7. Wire into the game (pull back to source of truth, phone-side game/ dir)
rsync -av e5:/home/ubuntu/ak_out/assets_ready/ \
  /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Alley_Kingz/ecosystem/game/assets/
# edit the game code to reference the new asset (sprite player / video layer / audio map)

# 8. Ship: AK sole deploy path (rsync -> e5 -> ship.sh). GitHub Action stays DISABLED.
# 9. Verify LIVE on alleykingz.online, operator plays it.
# 10. Log: append job_id, model, credits, verdict to the ledger below + Blinko session note.
```

**Miss-nothing checklist per batch**: cost estimated -> canon block verbatim -> registry names only -> keyframe operator-approved -> chroma/loop directive present -> `--json` captured -> encode within performance budget -> ledger updated -> operator played it in-game -> only then next batch.

---

## 5. CREDIT LEDGER (append every job)

| Date | Job ID | Model | Asset | Credits | Verdict (in-game test) |
|---|---|---|---|---|---|
| 2026-07-01 | (CLI run) | soul-id | $BCARDD Soul training (91e8b2b5-a0af-4fd1-b266-544f064a7732) | 25 | TRAINED, live |
| 2026-07-01 | (CLI run) | soul_v2 | test still (cost calibration) | 0.12 | measured baseline |
| 2026-07-01 | (CLI run) | kling-v3 std 5s | test clip (cost calibration, start=end loop confirmed) | 7.5 | measured baseline |

---

## 6. SOURCES

- Higgsfield CLI page: https://higgsfield.ai/cli
- CLI README (commands, models, workflows): https://github.com/higgsfield-ai/cli
- Official skills repo: https://github.com/higgsfield-ai/skills
- Soul ID guides (20+ refs, presets over freehand): https://higgsfield.ai/blog/Soul-ID-AI-Character-Consistency , https://higgsfield.ai/blog/sould-id-best-character-consistency
- Model comparison (Kling char-driven / Veo atmospheric / Minimax fast): https://higgsfield.ai/blog/5-Best-AI-Video-Models-2026-Tested-Compared
- Cinema Studio: https://higgsfield.ai/blog/cinema-studio-guide , https://higgsfield.ai/cinematic-video-generator
- Audio / Speak 2.0 / cloning / 21 preset voices: https://higgsfield.ai/blog/higgsfield-audio-ai-voice-tools , https://higgsfield.ai/blog/Speak-2.0-Your-Guide-to-Voice-Creation
- Higgsfield Games (separate product, Fable 5 powered): https://higgsfield.ai/games-intro , https://higgsfield.ai/blog/Higgsfield-Games
- Third-party pricing (Veo 22-58+, 3-5x iteration warning): https://www.vo3ai.com/higgsfield-ai-pricing , https://www.yangsweb.com/blog/higgsfield-ai-review-alternatives-pricing , https://aifunnelinsider.com/higgsfield-ai-review-2026/
- MCSLA + Kling Motion Control community skill: https://github.com/OSideMedia/higgsfield-ai-prompt-skill
- CLI vs MCP cost: https://www.mindstudio.ai/blog/higgsfield-mcp-vs-cli-claude-code-agents-token-cost
- AutoSprite (separate tool, free 3/day, sheet+atlas export): https://www.autosprite.io/ , https://sorceress.games/pages/auto-sprite
- Seamless loop trick (first frame = last frame) + frame chaining: https://cybercorsairs.com/kling-ai-trick-for-longer-videos-seamless-loops/ , https://tonaai.io/blog/kling-3-start-end-frame-tutorial , https://hailuoai.video/pages/blog/how-to-make-seamless-loop-videos
- Video-to-sprite pipelines (chroma key #00FF00, ffmpeg fps slice): https://github.com/tylertroy/video2sprites , https://github.com/LayrKits/Sprite-Pipeline , https://shotstack.io/learn/ffmpeg-extract-frames/
- External operator research doc (2026-07): WAN 2.2 Animate card animation lane, Speak 2.0 lip-sync lane, 9-stage pipeline, week-by-week sequence, video performance budget. Folded in above, corrected to Plus-plan account metrics and canon registry.

Inference flags: Soul ID 25 / Soul V2 0.12 / Kling 7.5 are OUR MEASURED figures. Veo, WAN 2.2 Animate, Speak 2.0, TTS per-line, Cinema Studio are third-party or external-doc figures; verify each with `higgsfield generate cost` in P0 before batching.
