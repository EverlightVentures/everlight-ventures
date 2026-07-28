# AK MP4 OVERHAUL -- THE DEFINITIVE AUDIT + SHOT LIST
**Date:** 2026-07-01 | **Author:** Everlight Researcher (Hive) | **Budget:** 927 Higgsfield credits total, ~300 ring-fenced for the trailer, **~600 spendable** | **Measured cost:** Kling ~7.5 credits per 5s clip (10s = ~15)

---

## 0. THE THREE INTEGRATION PATTERNS THAT ALREADY EXIST (reuse, do not reinvent)

| Pattern | Where it lives | What it does | Use it for |
|---|---|---|---|
| **P1 -- `akPlayCinematic(name, then)`** | `game/index.html:1279` | Full-screen MP4 stinger from `assets/cinematics/<name>.mp4`, muted, tap-to-skip, 6.5s hard cap, error -> continue. Already sandwiches win/lose before `akRaidEndScreen` (line 1274) and story_intro before tutorial replay (line 945). | Every stinger, transition, and cutscene. Zero new plumbing. |
| **P2 -- interiors_mp4 / loops.js single reused `<video>`** | `game/index.html:465-479` (`intVidSrc`, `applyInteriorVid`), video element owned by `systems/loops.js` (`AKLoops.get('interior')`) | ONE `<video>` re-pointed per building at `assets/interiors_mp4/<name>.mp4`; static PNG stays underneath as poster/fallback; `_intVidDead` guard = graceful 404 degrade, no re-probe. | Any ambient loop where only one is visible at a time (interiors DONE; lobby hero, panel headers, result-screen bg). |
| **P3 -- `<video>`-in-panel** | `game/index.html:933` (story panel) | `<video src=... muted loop autoplay playsinline onerror="this.style.display='none'">` inline in panel HTML. | Panel header loops (fence, trade, agenda, chapter panels, tutorial coach cards). |

Also live: `#loadscreen` already plays `assets/ui/menu_bg.mp4` (index.html:325). Battler result screen is still STATIC jpg (`game.html:5387`).

**Existing MP4 inventory (repo):** `ui/menu_bg.mp4`, `avatar/bcardd_walk{,_front,_back}.mp4`, `cinematics/{win,lose,story_intro}.mp4`. Interiors: 18 mapped in `INT_BG` (index.html:451 -- arena, trophy_hall, kennel, drop_shop, garage, wardrobe, archive, crew_yard, pass_house, fixer_den, gem_mine, gold_mint, card_forge, street_mode, arcade, research_lab, power_gen, infirmary) -- loops shipped on the deploy host (e5), **DONE**, not re-shot here.

---

## 1. PART A -- SURFACE-BY-SURFACE AUDIT

**Clip-type legend:** MICRO = micro-loop <2s (HUD buttons/chips) | AMB = ambient loop ~5s | STING = stinger 3-5s (play once, P1) | TRANS = transition 1-2s screen-blend wipe | CUT = cutscene 5-10s (P1).

**House style block (prepend to every prompt):**
> `STYLE: dark 1990s street-noir cyberpunk alley world, Twisted Metal grit, deep blacks #0a0a10, molten gold rim light #e8c55a, wet asphalt reflections, chain-link fences, sodium-vapor haze, subtle film grain and VHS undertone, cinematic, no text, no watermark, no humans.`

**$BCARDD canon block (whenever he appears):**
> `CHARACTER: $BCARDD, the masked dog kingpin -- muscular street dog in a black hoodie, heavy gold chain with crown emblem, eyes catching gold light, face half in shadow, never fully revealed.`

**VFX-for-compositing block (all TRANS + screen-blend overlays):**
> `PURE BLACK BACKGROUND, the effect only, no scene, no subject, high contrast, bright gold and cyan values on black, designed for screen/add blend mode compositing, seamless, 1-2 seconds of action.`

### 1.1 HUB -- index.html

| # | Surface | Current state | MP4 wanted | Target path | Prompt gist (after style block) | Cr | Integration hook |
|---|---|---|---|---|---|---|---|
| H1 | Loading screen `#loadscreen` | **HAS VIDEO** (menu_bg.mp4) | keep; optional v2 re-shoot later | `assets/ui/menu_bg.mp4` | -- | 0 | Done (index.html:325) |
| H2 | Win/lose raid cinematics | **HAS VIDEO** (win/lose.mp4) | keep | `assets/cinematics/{win,lose}.mp4` | -- | 0 | P1 at akRaidEnd (1274) |
| H3 | Story intro | **HAS VIDEO** | keep | `assets/cinematics/story_intro.mp4` | -- | 0 | P1 (945) + P3 loop in story panel (933) |
| H4 | Interiors x18 | **HAS VIDEO** (interiors_mp4, e5) | keep | `assets/interiors_mp4/*.mp4` | -- | 0 | P2 |
| H5 | **House transition wipe** (zone enter, transit ride, panel open/close, raid launch) | none -- hard cuts | TRANS 1.2s, screen-blend | `assets/cinematics/transition_wipe.mp4` | VFX block + "a wall of gold embers and black smoke sweeps left-to-right across frame like a curtain, brief chain-link silhouette flicker inside the smoke" | 7.5 | New `akPlayTransition()` = thin P1 variant (z-index under panels, `mix-blend-mode:screen`, 1.4s cap); call in `enterZone()`, transit `trow.onclick` (index.html:664-667), `akFlyRoute` |
| H6 | **Combat glitch smash-cut** (raid start, encounter start, watch defense) | none | TRANS 1s, screen-blend | `assets/cinematics/transition_glitch.mp4` | VFX block + "harsh analog VHS glitch burst, RGB channel split, scanlines tear, two frames of white flash, red and gold interference on black" | 7.5 | Same `akPlayTransition('glitch')` before `akOpenRaidMap` dive-in + encounters.js spawn |
| H7 | HUD action chips `ph-story, ph-mk, ph-raid, ph-watch, ph-infirm, ph-fence, ph-transit, ph-crew, ph-th, ph-rank, ph-tools, ph-bld` (index.html:327) | static emoji chips w/ CSS glow | MICRO <2s backplate, **played one-at-a-time** on the beacon's "next action" chip only (perf rule R1) | `assets/ui_mp4/chip_<id>.mp4` (raid, story, fence, watch, infirm, transit first) | VFX block + per-chip motif: raid = "crossed gold blades flash and ember burst"; story = "old scroll edge burns with gold fire"; fence = "neon pawn-shop sign flickers"; watch = "gold shield pulse with rain streaks"; infirm = "green cross heartbeat pulse with steam"; transit = "train light streak rushes past" | 7.5 ea | One shared 34px-high `<video>` absolutely positioned behind the highlighted chip; driven by the AK-GOALBEACON controller; poster = current chip look; loop trimmed to <2s in post |
| H8 | Currency chips `ph-gold/gem/scrap/keys/bones/wood/stone/metal/produce` | static PNG icons | STING 0.8s "value-changed" burst (single shared overlay video, screen-blend) -- NOT 9 loops | `assets/ui_mp4/chip_gain.mp4` | VFX block + "small burst of gold coins and sparks pops upward and dissolves" | 7.5 | `akHud.tick()` diff -> position shared overlay over the chip that changed, play once |
| H9 | Goal beacon `#ak-beacon` claim-ready | CSS pulse | reuse H8 burst on claim | -- | -- | 0 | `.akb-claim.ready` handler |
| H10 | Story panel per-chapter header (akOpenStory, 926-946) | reuses story_intro.mp4 for ALL chapters | AMB 5s per generation (3 clips: Gen I stray-era, Gen II heir-era, Gen III war-era) | `assets/cinematics/story_gen{1,2,3}_loop.mp4` | style block + $BCARDD block + gen1: "a lone stray dog silhouette under a flickering streetlight, rain, gold puddle reflections, slow push-in, seamless loop"; gen2: "a young dog wearing a too-big crown chain on a throne of car seats, candles"; gen3: "city skyline burning gold on the horizon, war banners of rival dog crews" | 22.5 | Swap `story_intro.mp4` src by `AKStory.stage().gen` in the P3 video tag (933) |
| H11 | **Story chapter-card stingers** (13 stages: story.js:91-147 -- Stray Awakening, Pick Your Clan, Prove Yourself, Crew Wars, Seasonal Supremacy, Challenge the King, Crowned, Heir Rising, Defend the Throne, Bloodline Crowned, Embers of War, City Aflame, Legend Eternal) | full-screen TEXT chapter cards only (`chapterCard`, story.js:579) | STING 3-4s before each chapter card ("mp4 sandwiched before static") -- shoot the 7 Gen-I first | `assets/cinematics/story_ch{1..7}.mp4` | style block + per-chapter beat, e.g. ch1: "$BCARDD block + a stray dog wakes in a rain-soaked alley, slow rise to feet, eyes ignite gold, crash of thunder"; ch4 Crew Wars: "two packs of dogs face off across a burning intersection, slow dolly between them"; ch7 Crowned: "gold crown lowered onto a dog's head in silhouette, ember rain, crowd of dogs howling" | 7.5 ea | `AKStory.chapterCard` consumer in index.html -> `akPlayCinematic('story_ch'+n, showCard)` -- exact sandwich the operator ordered |
| H12 | Cold-open CROWNED->STRAY flash (story.js:604-612) | text cards | reuse ch7 + ch1 stingers | -- | -- | 0 | same hook |
| H13 | Agenda panel (akOpenAgenda) | static | AMB 5s header: "the day's agenda" street map table | `assets/ui_mp4/agenda_loop.mp4` | style block + "overhead of a beat-up table with a hand-drawn block map, cigarette smoke curling, a paw slides a gold marker across it, loop" | 7.5 | P3 tag at top of agenda HTML |
| H14 | Upgrade board (AK-UPGRADE, 670+) | static | STING 2s on upgrade-confirm: dust + gold sparks build burst | `assets/cinematics/build_up.mp4` | VFX block + "construction dust plume with gold welding sparks and rising scaffold silhouette flash" | 7.5 | play via screen-blend overlay on the building card when `upCost` paid |
| H15 | Transit panel + ride (644-668) | static rows, instant teleport | TRANS: reuse H5 wipe on depart; optional AMB header "subway lights" later | `assets/cinematics/transition_wipe.mp4` | -- | 0 | `trow.onclick` -> `akPlayTransition(...)` -> `enterZone` |
| H16 | Dog picker / ASSIGN DOG (`#int-assign`, 343) | static list | STING 1.5s "dog reports for duty" paw-slam | `assets/ui_mp4/dog_assign.mp4` | VFX block + "a heavy paw slams down leaving a glowing gold paw-print that embers out" | 7.5 | screen-blend overlay on assign-confirm |
| H17 | Raid end screen (akRaidEndScreen, 1294) | static gradient + text (cinematic already plays BEFORE it -- correct sandwich) | AMB 5s bg loop behind VICTORY/DEFEAT text (P2-style, jpg poster) | `assets/ui_mp4/raidend_{win,lose}.mp4` | win: style + "slow ember rain over a conquered block, gold haze, dogs silhouetted on a rooftop howling, loop"; lose: "red emergency light sweeping a wrecked alley, smoke, loop" | 15 | insert `<video>` as first child of `#ak-raid-end`, text on top |
| H18 | Worldmap zoom (systems/worldmap.js -- Canvas2D overlay) | canvas paint | AMB atmosphere composited via `ctx.drawImage(video,...)` -- drifting smog/searchlights | `assets/ui_mp4/map_smog.mp4` | VFX block + "thin drifting smoke layers and a slow searchlight beam sweep on black, loop" | 7.5 | one offscreen `<video>`, drawImage each frame at low alpha; kill on close |
| H19 | Raid war map (systems/raidmap.js) | canvas paint | AMB red war-room scanline loop, same drawImage technique | `assets/ui_mp4/map_war.mp4` | VFX block + "red radar sweep with scanlines and small gold blips pulsing on black, loop" | 7.5 | as H18 |
| H20 | Fence / marketplace panel | static | AMB 5s header: neon fence sign | `assets/ui_mp4/fence_loop.mp4` | style + "flickering neon sign reading nothing (abstract shapes), stacked hot goods under tarp, rain drips, loop" | 7.5 | P3 tag in marketplace.js panel HTML |
| H21 | Trade post panel (359-368) | static | AMB header: coins/scales | `assets/ui_mp4/trade_loop.mp4` | style + "gold coins slowly cascading onto a scale pan, dust motes in a light shaft, loop" | 7.5 | P3 tag |
| H22 | Watch / guard (systems/guard.js) | static panel | STING 2s defense-won: shield slam | reuse H6 glitch on attack start + `assets/ui_mp4/watch_win.mp4` | VFX block + "gold shield emblem slams into frame, cracks ripple out as embers" | 7.5 | guard resolve callback |
| H23 | Infirmary (systems/infirmary.js) | interior loop exists | STING 2s heal-complete: green-gold pulse | `assets/ui_mp4/heal_pulse.mp4` | VFX block + "soft green-gold healing pulse rings expanding with rising steam wisps" | 7.5 | heal timer complete -> overlay on dog card |
| H24 | Encounters (systems/encounters.js wild stray) | banner + canvas | TRANS: reuse H6 glitch; optional STING "eyes in the dark" | `assets/cinematics/encounter_intro.mp4` | style + "two glowing eyes ignite in a pitch-dark alley doorway, chain-link shadow slides, 2 seconds" | 7.5 | before encounter overlay opens |
| H25 | Arcade cabinets (systems/arcade.js: bone_dig, alley_dash, whack + gem_tap, forge_temper) | canvas games, static menu | AMB attract-mode loop for the cabinet select screen (ONE shared clip) + reuse H8 burst on payout | `assets/ui_mp4/arcade_attract.mp4` | style + "a row of grimy arcade cabinets glowing gold and cyan in a dark room, screens flickering demo static, loop" | 7.5 | P3 tag in arcade menu overlay |
| H26 | Ladder rank-up (systems/ladder.js, ph-rank) | banner text | STING 2.5s rank-up: crown tier flash | `assets/cinematics/rank_up.mp4` | VFX block + "a gold laurel-and-crown emblem forges itself out of sparks, flash to bright, embers fall" | 7.5 | ladder promotion event -> P1 |
| H27 | Seasons (systems/seasons.js -- 6 season icons exist) | icon + text | CUT 5s season intro, one per active season (shoot current first) | `assets/cinematics/season_<name>.mp4` | style + season motif (frost: "the block frozen over, breath fog, ice-blue replacing gold accents"; neon: "every sign in the alley buzzes to full neon life") | 7.5 ea | season rollover -> P1 |
| H28 | Day/night + weather (daynight.js, wx_* icons) | canvas tint | SKIP video -- canvas FX sufficient (perf) | -- | -- | 0 | -- |
| H29 | Avatar movement ($BCARDD walks exist) | 3 walk clips | add idle + victory-pose loops | `assets/avatar/bcardd_idle.mp4`, `assets/avatar/bcardd_win.mp4` | $BCARDD block + "idle: subtle breathing, chain sways, ears flick, seamless loop, black background"; "win: slow head raise and howl, gold light flare" | 15 | same drawImage path as walk clips |

### 1.2 TUTORIAL -- systems/tutorial.js (the operator's explicit order: video on tutorial screens)

12-step intro flow (tutorial.js:53-86) + ~20 `firstVisit` coach screens (336-450). Coach card renderer gets ONE optional `<video>` slot (P3) above the text: `assets/tutorial_mp4/<screenId>.mp4`, jpg poster, `preload="none"`, loaded only when that coach fires. Shoot order = the money path first:

| Screen (id) | Clip | Prompt gist | Cr |
|---|---|---|---|
| game / THE CROWN BLOODLINE opener | STING 5s | $BCARDD block + "montage: stray in rain -> pack forming -> crown in gold light" | 7.5 |
| townhall | AMB 4s | "the Town Hall interior, a war table with the whole block modeled on it, gold ledger light" | 7.5 |
| fence | AMB 4s | reuse H20 fence loop | 0 |
| raid + raidmap | STING 4s | "a crew of dogs vaulting a fence at night toward a rival block, sirens glow" | 7.5 |
| infirmary | AMB 4s | reuse interior loop `interiors_mp4/infirmary.mp4` | 0 |
| deck / YOUR PACK | STING 4s | "playing cards of dogs fan out across a table, one flips and ignites gold" | 7.5 |
| watch, farming, ladder, economy, districts, streak, daynight, story, encounter, builders, interior, hitlist, world | reuse nearest loop/stinger above; shoot only if a wave has spare credits | -- | 0 |

### 1.3 BATTLER -- game.html

| # | Surface | Current state | MP4 wanted | Target path | Prompt gist | Cr | Hook |
|---|---|---|---|---|---|---|---|
| B1 | Lobby `#startscreen` hero | static `lobby_hero.png` + CSS film grain | AMB 6s hero loop, png poster | `assets/ui_mp4/lobby_hero.mp4` | style + $BCARDD + "hero shot: the pack posted up under a gold streetlight, rain, slow cinematic drift, seamless loop" | 7.5 | P2-style single video behind `.lobby-hero` (#lobbyhero, css:842-863) |
| B2 | **Result screen** (`#resultscreen`, bg set at game.html:5387 from `screen_victory/defeat.jpg`) | STATIC jpg | Sandwich: STING (reuse `cinematics/win.mp4` / `lose.mp4` via a local P1 copy -- 0 credits) then AMB loop behind rewards (reuse H17 raidend loops) | reuse | -- | 0 | before `resultScreen.classList.remove('hidden')` (5444); poster stays the jpg |
| B3 | **Chest/crate opening** (chest_wood..diamond jpgs; crate drawer css:901) | static jpg + CSS | STING 3s master crate-rip (gold), tier variants by color grade in post (free) | `assets/cinematics/chest_open.mp4` | VFX-ish: style + "a battered street crate strains, gold light knifes through the seams, lid blasts off in slow motion, ember and card-shaped light shards erupt, black bg edges" | 7.5 | crate-open handler -> P1-style overlay, then reveal cards (sandwich) |
| B4 | Killstreak evolutions 2/4/6/8 (ADVANCED..DOG GOD, game.html:3630) | canvas FX | STING 1s screen-blend flash for DOG GOD only (rest stay canvas -- perf) | `assets/ui_mp4/doggod_flash.mp4` | VFX block + "gold lightning crown shockwave bursts from center, 1 second" | 7.5 | evolve event -> screen-blend overlay |
| B5 | Keyword popups kw_*.jpg (10) | static | SKIP for now (low impact, 10 clips = 75cr) | -- | -- | 0 | -- |
| B6 | Emotes (4) | static | SKIP / wave 6 | -- | -- | 0 | -- |

### 1.4 SHOP -- shop/shop.html + shop.js

| # | Surface | Current | MP4 | Target | Prompt gist | Cr | Hook |
|---|---|---|---|---|---|---|---|
| S1 | Shop hero ("Rip the chop-shop crate...") | static | AMB 5s chop-shop loop | `assets/ui_mp4/shop_hero.mp4` | style + "a chop shop at night, sparks from an angle grinder, stacked crates glowing gold at the seams, loop" | 7.5 | P3 tag in aks-hero |
| S2 | Crate open (chest_scrap_crate etc., shop.js:219+) | static | reuse B3 chest_open | -- | -- | 0 | openChest flow |
| S3 | Purchase success (gems/pass) | toast | STING 2s celebration | `assets/ui_mp4/purchase_win.mp4` | VFX block + "gold gem cluster crystallizes out of sparks and flares" | 7.5 | Stripe success callback |

---

## 2. PART B -- RESEARCH DIGEST (with sources)

**Transitions: quick, consistent, purposeful.** The literature is unanimous: transitions must be "quick enough to feel smooth without becoming a wait," used in ONE coherent house style, with a more dramatic variant reserved for major moments; slow or inconsistent transitions frustrate more than they polish ([Bugnet](https://bugnet.io/blog/how-to-implement-screen-transitions-that-feel-good), [FredericRP/Medium](https://medium.com/@FredericRP/elevate-user-experience-use-transition-screens-in-your-games-f8742fea219b)). Practical implication for AK: one 1.2s house wipe everywhere + one 1s glitch smash-cut reserved for combat. Never a 5s transition on a repeatable action.

**Juice doctrine.** Juice = layered animation + audio on every interaction; buttons pulse/glow, UI echoes the core fantasy; in dynamic games go loud, in story beats go subtle ([GameDev4U](https://gamedev4u.medium.com/when-you-play-a-great-game-it-feels-good-d23761b6eccf), [Juice It or Lose It](https://gamejuice.co.uk/resources/juice-it-or-lose-it), [bradwoods garden](https://garden.bradwoods.io/notes/design/juice), [GameAnalytics](https://www.gameanalytics.com/blog/squeezing-more-juice-out-of-your-game-design), [Punchev](https://punchev.com/blog/transforming-game-interfaces-with-animated-ui), [Genieee](https://genieee.com/best-practices-for-game-ui-ux-design/), [Justinmind](https://www.justinmind.com/ui-design/game)).

**How the top mobile games do it.** Reference libraries [Game UI Database -- Clash Royale](https://www.gameuidatabase.com/gameData.php?id=1299), [Brawl Stars](https://www.gameuidatabase.com/gameData.php?id=465), [Marvel Snap](https://www.gameuidatabase.com/gameData.php?id=1785) and [Interface In Game](https://interfaceingame.com/games/brawl-stars/), ([Clash Royale](https://interfaceingame.com/games/clash-royale/)) document the shared pattern: **motion is concentrated at reward and identity moments** -- chest/crate openings, victory screens, rank-ups, season intros -- while navigation stays snappy with sub-second wipes. Menus use one ambient hero scene, not motion on every tile. Inference (clearly flagged as inference): AK should spend credits on chest-open, victory, chapter, and season moments before decorating passive panels -- that is where Supercell/Second Dinner spend their animation budget.

**Video-in-UI performance on mobile browsers (facts).** `autoplay muted loop playsinline` is the required combo; mobile blocks unmuted autoplay ([Cloudinary](https://cloudinary.com/guides/video-effects/video-autoplay-in-html), [Mux 2025 guide](https://www.mux.com/articles/best-practices-for-video-playback-a-complete-guide-2025)). 720p is enough for UI video (a 10s 720p clip ~= 3-4 MB); strip the audio track (~20% bandwidth saved); lazy-load anything not visible; give simultaneous background loops different durations so they don't beat-sync ([web.dev](https://web.dev/learn/performance/video-performance), [DamienG HTML5 video cheatsheet](https://damieng.com/blog/2025/12/05/html5-video-cheatsheet/), [ignite.video](https://www.ignite.video/en/articles/basics/autoplay-videos), [MDN](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Performance/video)). iOS Safari has blank-poster/first-frame quirks -- always set an explicit `poster` ([SiteLint](https://www.sitelint.com/blog/fixing-html-video-autoplay-blank-poster-first-frame-and-improving-performance-in-safari-and-ios-devices)). Multiple decoding `<video>` elements each hold a hardware decoder session and drain battery -- hence the hard concurrency cap in section 4. `canvas.drawImage(video)` per-frame is viable for map atmosphere but costs a texture upload per frame -- one such video max.

**Seamless micro-loops.** The proven trick: **use the same image as start AND end frame** in Kling's start/end-frame mode (via Higgsfield) so the clip cycles with no visible seam; keep prompts minimal, let the model infer motion, add one camera verb only if needed; 5s for dynamic loops, 10s for complex transformations ([Higgsfield -- Kling Start & End Frames](https://higgsfield.ai/blog/Kling-Start-End-Frames), [Grokipedia -- seamless looping](https://grokipedia.com/page/Seamless_looping_in_AI-generated_videos), [CyberCorsairs Kling loop trick](https://cybercorsairs.com/kling-ai-trick-for-longer-videos-seamless-loops/), [fluxnote guide](https://fluxnote.io/guides/how-to-make-seamless-loop-video-ai)). Also append "seamless loop" to the prompt. For AK: render each interior/panel poster jpg first, feed it as both frames, prompt only the internal motion ("smoke drifts, sign flickers").

**Higgsfield/Kling for TRANSITION + VFX clips.** VFX assets are conventionally delivered on a pure black background and composited with **Screen/Add blend** (removes black, keeps bright values -- fire, smoke, light leaks, particles) ([MyCreativeFX](https://mycreativefx.com/blog/5000-free-vfx-download-4k-overlays-transitions-effects-mycreativef)). Strong Higgsfield prompts name ONE subject + ONE camera/VFX move + lighting/mood; known transition presets include whip pans, ink spreads, **glitch cuts**, zoom blurs, particle wipes, liquid transitions ([Techpresso Higgsfield prompts](https://academy.techpresso.co/prompts/higgsfield-prompts), [filmart.ai guide](https://filmart.ai/higgsfield-ai-guide-higgsfield-ai-prompts/), [Higgsfield Kling O1 guide](https://higgsfield.ai/blog/Kling-01-is-Here-A-Complete-Guide-to-Video-Model), [Kling O1 prompt bank](https://higgsfield.ai/blog/kling-O1-prompt-bank)). For AK this means: shoot every transition ON BLACK, drop it in a fixed full-screen div with `mix-blend-mode:screen` over the live canvas -- no alpha channel needed, works in Canvas2D world, ~1 MB clips.

**VERDICT -- the single best transition style for the AK brand:** a **1.2s gold-ember smoke wipe on black, screen-blended** (H5) as the house transition -- it is literally the brand palette (#e8c55a embers on #0a0a10 black), it hides the hard cut like the research demands, it costs one 7.5-credit clip reused everywhere, and the black-background/screen-blend delivery means zero compositing work. Reserve the **VHS glitch smash-cut** (H6) as the "dramatic variant" for combat (raid/encounter/watch) per the consistency-with-one-dramatic-exception rule.

---

## 3. PRIORITIZED SHOT LIST (waves of ~6, ~600 spendable credits)

Costs = single Kling 5s gen at 7.5 cr. **Plan x2 for retries** -- right column. Running total with retries stays under 600; trailer's ~300 untouched.

### WAVE 1 -- highest player impact: the reward + transition spine (45 cr / 90 w-retry)
| Clip | Type | Target | Hook |
|---|---|---|---|
| 1. `chest_open.mp4` -- master crate-rip stinger (gold; tier variants graded free in post) | STING 3s | `assets/cinematics/chest_open.mp4` | B3/S2: crate-open flow in game.html drawer + shop.js openChest, P1-style overlay before card reveal |
| 2. `transition_wipe.mp4` -- gold-ember smoke wipe on black (THE house transition) | TRANS 1.2s | `assets/cinematics/transition_wipe.mp4` | H5: new `akPlayTransition()` in enterZone / transit / akFlyRoute |
| 3. `transition_glitch.mp4` -- VHS glitch smash-cut on black | TRANS 1s | `assets/cinematics/transition_glitch.mp4` | H6: raid launch + encounter + watch |
| 4. `raidend_win.mp4` -- ember-rain victory loop | AMB 5s | `assets/ui_mp4/raidend_win.mp4` | H17/B2: `<video>` behind #ak-raid-end + battler #resultscreen (jpg poster) |
| 5. `raidend_lose.mp4` -- red-light wrecked-alley defeat loop | AMB 5s | `assets/ui_mp4/raidend_lose.mp4` | same |
| 6. `story_ch1.mp4` -- STRAY AWAKENING chapter stinger ($BCARDD canon) | STING 4s | `assets/cinematics/story_ch1.mp4` | H11: akPlayCinematic before chapterCard render |

*Plus 0-credit wins shipped alongside wave 1: battler result screen sandwiches existing `win.mp4`/`lose.mp4` (B2); tutorial fence/infirmary coaches reuse existing loops.*

### WAVE 2 -- tutorial + lobby (45 / 90)
`tutorial_mp4/game.mp4` (Crown Bloodline opener), `tutorial_mp4/townhall.mp4`, `tutorial_mp4/raid.mp4`, `tutorial_mp4/deck.mp4`, `ui_mp4/lobby_hero.mp4` (B1), `ui_mp4/shop_hero.mp4` (S1).

### WAVE 3 -- HUD chip micro-loops, one-at-a-time playback (45 / 90)
`ui_mp4/chip_raid.mp4`, `chip_story.mp4`, `chip_fence.mp4`, `chip_watch.mp4`, `chip_infirm.mp4`, `chip_gain.mp4` (shared currency burst H8). Loop trick: poster jpg as start+end frame in Kling.

### WAVE 4 -- story mode Gen I spine (45 / 90)
`story_ch2..ch7.mp4` (Pick Your Clan, Prove Yourself, Crew Wars, Seasonal Supremacy, Challenge the King, Crowned). Completes the "transitions are important for story mode" order for Generation I.

### WAVE 5 -- systems juice (45 / 90)
`cinematics/rank_up.mp4` (H26), `cinematics/build_up.mp4` (H14), `ui_mp4/heal_pulse.mp4` (H23), `ui_mp4/watch_win.mp4` (H22), `ui_mp4/purchase_win.mp4` (S3), `cinematics/season_<current>.mp4` (H27).

### WAVE 6 -- atmosphere + reserves (45 / 90)
`ui_mp4/map_smog.mp4` (H18), `ui_mp4/map_war.mp4` (H19), `ui_mp4/fence_loop.mp4` (H20), `ui_mp4/trade_loop.mp4` (H21), `ui_mp4/arcade_attract.mp4` (H25), `avatar/bcardd_idle.mp4` (H29).

**Backlog (only if credits remain):** story Gen II/III stingers, story_gen loops (H10), agenda loop, dog_assign, doggod_flash, chip_transit/th/crew, remaining tutorial coaches, kw/emote loops, remaining seasons.

**Ledger:** 6 waves x 45 = 270 cr single-pass; 540 with a full retry on everything. Ring-fenced trailer ~300 remains intact either way (270+300=570; 540+300=840 <= 927 only without full-double-retry on wave 6 -- treat wave 6 as retry-budget-permitting).

---

## 4. PERFORMANCE BUDGET RULES (hard law for every integration PR)

- **R1 -- Max 3 concurrent `<video>` elements decoding, ever.** Hub steady-state target = 1 (the highlighted chip OR an interior OR a panel header -- never stacked). A P1 stinger pauses all loops for its duration. HUD chips play ONE at a time (the beacon's next-action chip), never all 22.
- **R2 -- Lazy everything.** `preload="none"`, src assigned only when the surface opens (the P2 `applyInteriorVid` re-point pattern is the template). Tutorial clips load per-coach, never up front.
- **R3 -- Poster/static fallback under every video, no exceptions.** Existing jpg/png stays as the poster layer; onerror hides the video (the `_intVidDead` + `onerror="this.style.display='none'"` patterns). A missing mp4 must degrade to today's game, pixel-identical.
- **R4 -- Pause/unload offscreen.** Panel close, overlay close, `document.visibilitychange`, and IntersectionObserver for in-scroll videos -> `pause()` + `removeAttribute('src')` + `load()` on long-lived elements. drawImage map videos are killed on overlay close.
- **R5 -- Encode discipline.** H.264 720p max (chips: 240px square crops), no audio track, 24fps, target <=1.5 MB per loop / <=4 MB per cutscene, `playsinline muted loop autoplay`. Different durations for any two loops that could co-exist (anti beat-sync).
- **R6 -- Respect `prefers-reduced-motion`:** show posters only (the CSS media query already exists at index.html:322 -- extend it to videos).
- **R7 -- Transitions never trap:** every P1/transition keeps the tap-to-skip + hard cap (<=1.5s for TRANS, 6.5s existing cap for CUT).

---

## 5. SOURCES
Listed inline in section 2. Primary: Bugnet transitions, GameJuice/GameAnalytics juice doctrine, Game UI Database + Interface In Game (Clash Royale / Brawl Stars / Marvel Snap references), Mux 2025 playback guide, web.dev video performance, DamienG HTML5 cheatsheet, SiteLint iOS quirks, Higgsfield Kling Start/End Frames + Kling O1 prompt bank, Grokipedia/CyberCorsairs seamless-loop technique, MyCreativeFX screen-blend VFX convention. Not financial advice does not apply; no crypto claims made -- $BCARDD appears as game canon character only.

*Monetization relevance: 9/10 -- chest-open, purchase-success, and shop-hero clips sit directly on the IAP funnel; victory/chapter clips drive retention.*
