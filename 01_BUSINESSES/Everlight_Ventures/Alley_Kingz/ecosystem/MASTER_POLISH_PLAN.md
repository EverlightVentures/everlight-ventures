# ALLEY KINGZ - MASTER POLISH PLAN
## One brain, every surface. Bring the whole game to the chest-reveal bar.

Owner: Lucrex (lead producer)
Date: 2026-06-16
Scope: visual polish + cinematic loading + audio for the live alleykingz.online build.
Source of truth for game code: phone `game/`. Deploy ONLY via e5-mother + ship.sh, verify in a real browser (sole-deployer rule).

ASCII-only doc (a write hook blocks long dashes). All "-" are plain hyphens.

---

## 1. EXECUTIVE SUMMARY

Alley Kingz already has one surface that hits the premium bar: the chest reveal. It mounts real art into a DOM `<img>` (`.rw-chestico`, index.html:853 / JS index.html:4957), rims it in gold, and animates the open. Every other surface still ships flat OS emoji (money bag, wrench, box, key, joker, star, gift, bone, smiley, dog, padlock), bare CSS diamonds/dots, and plain-text titles. The game also has NO boot gate: the lobby visibly assembles on screen as scripts run and `restructure()` re-parents buttons, which reads as broken on a phone.

This plan unifies three workstreams into one polish push:

1. A cinematic preload gate (loading screen) that paints instantly, shows a real progress bar driven by actual asset loads, plays the existing menu video as its backdrop, and reveals a fully built lobby. Code-only, additive, byte-safe, ZERO new art required to ship.

2. A token + emblem system that replaces every flat emoji and CSS-dot across the reward screen, lobby, shop, pass, quests, handlers, drip, crew, street code, and HUD with forged-collectible art mounted the exact same way the chest already works (img first, glyph only on `onerror`). Roughly half the wiring uses art already on disk; the other half needs net-new Seedance generation.

3. Audio: a lobby/intro theme plus a small hero-SFX set, sourced from a budget-aware, license-clean stack (paid AI music from Beatoven or Soundraw, paid ElevenLabs Starter for hero SFX, free royalty-free for everything else). The chest open, victory sting, and tap are the load-bearing sounds.

Core design law for the whole effort: PRESERVE the chest reveal exactly as-is, and lift everything else to that bar. Every art mount uses the proven pattern (real `<img>`, `onerror` falls back to the current glyph/dot), so a missing or 404 asset degrades to exactly today's behavior and the Node test harness stays byte-identical.

Hard external dependency: net-new art is gated on Seedance access + budget from the operator. Seedance is currently the only viable generator (Leonardo API is dead; CF Workers AI failover needs CF_AI_TOKEN). The loading screen and all "wire existing art" fixes can ship immediately without that unblock; everything tagged net-new waits on it.

---

## 2. PRIORITIZED ROADMAP

Three lanes by dependency: BUILD-NOW (code only, no new art), WIRE-EXISTING (code only, art already on disk), and NEEDS-ART (gated on Seedance).

### PHASE 0 - BUILD NOW (no new art, highest operator-pain payoff)

P0.1 Cinematic preload gate / loading screen.
- Pure code. Reuses the existing `menu_bg.mp4` (2.5 MB, on disk) as the loader backdrop and `lobby_hero.png` (on disk) as the instant poster. Warm-loads `the_lot.mp3` (on disk) soft, never blocks on it.
- 8 additive edits total (see section 5). Every edit guarded `try{ window.AKPreload && ... }catch(_){}` so it is a no-op if the controller fails or in the headless harness.
- Kills the FOUC / "lobby assembles on screen" problem (the #1 visible jank) and masks first-paint emoji.
- Ships standalone. No dependency on any other phase.

P0.2 Screen-transition veil + fade (optional within P0, code only).
- Add `.screen{transition:opacity .28s}` and a reusable `playWipe()` so screen-to-screen and match board entry cross-fade instead of hard-cutting. Uses one veil overlay. The veil ART (`ui_transition_veil.jpg`) is net-new, but the fade itself works with a CSS gradient fallback now; drop the art in later.

### PHASE 1 - WIRE EXISTING ART (no new art, parity with the lobby bar)

These all mount art that is ALREADY on disk. They remove flat emoji/CSS-dots using the proven `kwIco()` / `.ak-curico` precedent. No Seedance needed.

P1.1 Shop wallet + reveal-haul parity (shop.js).
- Wallet chips `coin()` at shop.js:318: swap `.dot` for `<img class=aks-curico>` using cur_gems/cur_gold/cur_scrap/cur_keys (all on disk). onerror restores the `.dot`.
- Crate/Lucky-Draw reveal chips shop.js:744-745: swap `.dot` for loot_coin/loot_shard/loot_key (on disk).
- Keys-ready line shop.js:831: swap green `.dot` for loot_key.jpg.
- Brings the Chop Shop wallet, hype crate-reveal, and crates header to the lobby's bar in one change.

P1.2 Drip emote tokens (drip.js + shop The Drop tiles).
- Wheel options drip.js:274, bubble drip.js:276, and The Drop store tiles shop.js:1492 already have matching files on disk: emote_woof/emote_crown/emote_gg/emote_skull.jpg. Mount them; onerror restores the emoji. (Only the toggle-button face `emote_btn.jpg` is net-new; until then keep the emoji on the button.)

P1.3 Crew crests (shop.js + social.js).
- 4 faction crests already exist (Crest_Boneguard/Zoomie/Leashbreak/K9.jpg). Wire `crewCrest(c)` to resolve faction -> crest, mounting at shop.js:1807, shop.js:1925, social.js:191, social.js:299. Only the generic `crew_crest_default.jpg` fallback is net-new; until then onerror falls to the dog glyph.

P1.4 Daily Deal hero (shop.js).
- `daily_drop.png` already exists. shop.js:582: replace the `.gift` glyph with the image; resize the CSS frame to 64x64.

P1.5 Re-surface the dead Street Wire ticker (lobby.js + index.html).
- The news ticker is currently invisible: the relayout hide-loop (lobby.js:182-187) display:none's every direct child of #startscreen whose id does not match /drawer|overlay|modal|screen/, and "newsticker" matches none. Fix by re-parenting it INTO the scroll content (lobby.js:153 add `var nt=$('newsticker'); if(nt) content.appendChild(nt);`). Pure code; the WIRE tag reskin (`wire_emblem.jpg`) is net-new and layered later.

P1.6 Crown score word -> crown glyph cleanup and CSS gold checkmarks.
- index.html:1888 "crowns" word is placeholder copy; once `rw_crown.jpg` lands it becomes an img (net-new, P3), but the reached-tier "checkmark" and "claimed" states (shop.js:2118, 2130) become CSS gold `::before` checks with NO asset needed. Do the CSS checks now.

### PHASE 2 - AUDIO (parallel, operator budget decision)

P2.1 License + budget decision (operator).
- Pick ONE paid music tool for the lobby theme: Beatoven (cleanest license) or Soundraw. Do NOT ship a free-tier AI track. Avoid Suno/Udio for a monetized title unless the operator knowingly accepts the active major-label litigation risk.
- ElevenLabs Starter ($5/mo) for the hero SFX (chest open, victory sting). Full commercial ownership, perpetual.
- Free royalty-free (Sonniss, Pixabay, Freesound-CC0, jsfxr) for taps/shimmer/defeat/ambience.

P2.2 Produce + wire 1 theme + 5 SFX (prompts in section 6). Keep a CSV manifest of every file: source, URL, license, date pulled.

### PHASE 3 - NEEDS ART (gated on Seedance unblock)

Generate the Batch-3 pack (section 4) in priority order, then drop each file into its already-prepared wiring slot (all wiring can be coded in Phase 1 with onerror fallbacks, so art is a hot-swap, not a code change).

Priority of generation (most-seen surfaces first):
1. Reward screen tokens (rw_coins, rw_salvage, rw_keys, rw_tags, rw_xp, rw_district, rw_sp) + crests (rw_crest_victory.png, rw_crest_defeat.png, rw_crown.jpg, rw_badge.jpg, rw_new_stamp.png). The match-end screen is the climactic moment every player sees every match.
2. Lobby identity (logo_crest.png hero+boot crest, auth_saved.jpg, auth_signin_plate.jpg, pass_emblem.jpg, wire_emblem.jpg, daily_drop_tile.jpg). First thing every player sees on open.
3. Boot/loading polish (boot_splash.jpg, ui_loader_paw.jpg, menu_bg_poster.jpg, ui_tile_plate.jpg, ui_transition_veil.jpg, ui_hud_pause.jpg, ui_hud_storm.jpg) and the looping menu MP4 upgrade.
4. Shop/meta-UI depth (rw_crate, rw_card, rw_drop, rw_bones [optional], emote_btn, crew_crest_default, gem_rarity, street_muscle, street_hustle, street_tech, ui_lock).

Per the art-autoroute doctrine, queue every net-new asset through `art_factory.py --enqueue` so nothing ships as a placeholder permanently.

### DEPENDENCY GRAPH (short)
- Loading screen (P0.1): depends on NOTHING. Ship first.
- Transition fade (P0.2): independent; art-optional.
- Wire-existing batch (P1.1-P1.6): independent of each other; no art dep.
- Reward token mount (P3 wiring): code can land in P1 with fallbacks; art lands in P3.1.
- Auth chip: pick ONE design (see dedupe note in section 4) before generating.
- Hero crest: pick logo_crest.png OR hero_crest.jpg (same slot) before generating.
- MP4 loop upgrade: optional; current menu_bg.mp4 already serves both loader and lobby.

---

## 3. FULL UI INCONSISTENCY AUDIT (grouped by surface)

The reference bar is the chest reveal: real `<img>` mounted into the DOM, gold 1px ring, sized to read, animated on reveal, glyph fallback on error. PRESERVE it. Lift everything below to match.

### SURFACE A - Match-end reward / victory screen (index.html)
Inconsistencies:
- Coins / Salvage / Keys / Tags / XP / District-bonus / SP reward rows render as bare `+N` text with no minted-disc icon beside them (index.html:4946-4958). The chest row right next to them DOES mount art. Visual mismatch on the most-seen screen.
- Card-drop chips render as text pills, not the real card portrait (index.html:4961-4965 and the duplicate at 7070). The card art exists and is resolvable via `artSrc()` (index.html:2218) but is not shown.
- Result headline (VICTORY / DEFEAT) is plain text over a backdrop (index.html:1886, set 4871-4874). No foreground crest lockup; the win moment leans only on screen_victory.jpg.
- Crowns score row uses a literal grey word "crowns" between the scores (index.html:1888). The crown is the literal identity of the game; a grey word reads as placeholder.
- Badge-earned row is flat text (index.html:4982); the per-badge unicode glyph has no forged medallion behind it.
Fix bar: add ONE shared `.rw-curico` class next to `.rw-chestico` (index.html:853), mount each token via `document.createElement('img')` + `insertBefore(img, node.firstChild)` exactly like the chest at index.html:4957. Add a gain keyframe reusing the akXpPop pattern (index.html:131) and stagger reveal in renderRewards (index.html:4943). Card chips become a mini framed thumbnail mounting the real portrait via artSrc(). Crests + crown + badge medallion mount as imgs.

### SURFACE B - Lobby + menus + currencies (lobby.js / index.html / ak_account.js)
Inconsistencies:
- Auth chip renders raw unicode: signed-in "cloud SAVED" text glyph (ak_account.js:167) and signed-out "SIGN IN WITH GOOGLE" bare text pill (ak_account.js:174). Renders differently per OS; not on the gold-token bar with the currency chips two pixels away.
- Daily-Drop tile is an icon-less text "Claim" button (index.html:1629), inconsistent with the art tiles (Deck/Shop) in the same row.
- Alley Pass progress strip has zero art (lobby.js:140) while the Pass tab in the bar has art: "art in the tab bar, text in the strip" inconsistency.
- Street Wire ticker is fully invisible (killed by the relayout hide-loop, lobby.js:182-187) AND its tag is a flat gold text chip "WIRE" (index.html:1719).
- Hero title block is text-only (lobby.js:132-135); the bespoke crest art (logo.png / bcard_emblem.png / lobby_hero.png) goes unused.
Fix bar: mount forged tokens at the same 14-26px sizes as the existing `.ak-curico` lobby chips (lobby.js:106), onerror to a gold dot. Re-parent the news ticker into scroll content so it survives the hide-loop. Prepend a crest img above the h1. Auth chip: keep the OFFICIAL Google G SVG for the signed-out state (trademark hard rule; do NOT generate a fake G).

### SURFACE C - Shop + progression meta-UI (shop.js / shop.css / drip.js / social.js / pass.js / quests.js)
Inconsistencies (the biggest emoji surface): flat OS emoji and CSS-diamonds everywhere -
- Pass + Hit List reward kinds: money bag / wrench / box / key / joker / star / gift (shop.js:2021-2033, 2176-2185).
- Handlers "Bones" currency: bone emoji at handler bar (shop.js:1216), skill-tree header (1267), buy node (1274), locked node (1278).
- In-match + store emote: smiley toggle (drip.js:265), wheel (274), bubble (276), The Drop tiles (shop.js:1492).
- Crew crest: universal dog box (shop.js:1807, 1925; social.js:191, 299).
- Wallet + reveal + keys-ready: generic CSS diamond `.dot` (shop.js:318, 744-745, 831).
- Daily Deal hero: bare unicode lozenge (shop.js:582).
- Lucky Draw odds table: generic CSS diamond per rarity row (shop.js:668).
- Street Code perk tree: all-text branches, no branch iconography (shop.js:1417-1432).
- Pass tier locks: OS padlock emoji (shop.js:2131-2132).
- Plain "Loading..." text nodes in many panels (shop.js:1383/1645/1646/1797/1908/2251; drip.js:172; quests.js:80; pass.js:101; social.js:225/277).
- Dead duplicate files pass.js and quests.js (every lobby entry routes to shop.html#pass2/#hit2). Preferred: DELETE both; else paste the same helpers.
Fix bar: add `rwIco(kind)` / `bonesIco()` / `lockIco()` helpers modeled exactly on the existing `kwIco()` (shop.js:1019-1023): render `<img>` first, swap to the old glyph only in `img.onerror`. Strip the leading emoji from the text labels so the adjacent text reads clean. Re-use a single neutral gem (gem_rarity.jpg), CSS-tinted per rarity via the existing --rr var. Branch sigils as both a header icon and a faint full-bleed card-background watermark to turn the all-text perk tree into a painted spec screen.

### SURFACE D - Boot + loading + screen transitions (index.html / lobby.js / ak_account.js)
Inconsistencies:
- No boot/splash/preloader; lobby is "interactive" before art loads and visibly assembles (FOUC of raw .lobby-top/.mode-grid at index.html:1610-1639).
- Menu wallpaper video has no working poster fallback path; flat black until the 2.5 MB mp4 buffers.
- Menu tiles render system emoji on first paint (index.html:1659-1703) before the art swaps in.
- Screen-to-screen are hard display:none cuts; the match board snaps in with no entrance.
- Plain-text "Loading..." placeholders (see Surface C list).
- Auth/cloud chip uses a text glyph (see Surface B).
- Orphaned logo.png / plain-text title (see Surface B hero).
- In-match HUD pause renders as text "II" (index.html:1801); storm-codex button is "?" (index.html:1807) and the storm chip is pure text (index.html:1806).
Fix bar: the cinematic preload gate (section 5) covers boot + FOUC + tile-emoji-flash + Loading placeholders in one system. The transition veil + .screen fade covers hard cuts. HUD buttons become background-image tokens with text-indent to hide residual glyphs.

---

## 4. BATCH 3 - CONSOLIDATED SEEDANCE IMAGE-PROMPT PACK

House style (applies to EVERY prompt below): gritty TV-MA cyberpunk neon-noir, battle-worn scratched forged metal, Everlight gold #D4AF37 rim-light, dramatic single-source key light, ultra-detailed PBR, matched to the live card art + chest_*.jpg reveal bar. Unless noted, each token is the subject centered and floating just above a dark charcoal recessed circular plate ringed by a thin scratched-gold band, with volumetric haze behind, square 1:1 1024x1024, and ALWAYS ends with: no text, no numbers, no letters, no watermark, no UI chrome. PNG files are transparent-ready (rendered on flat #000000 for clean alpha keying).

COUNT: 36 net-new image prompts below (consolidated from 38 raw audit filenames by merging 2 duplicate-purpose pairs, see Consolidation Notes), plus 1 MP4 loop prompt in section 5. Filenames follow the assets/ui convention. Shop paths use `../assets/ui/`; game-root files (drip.js, social.js, lobby.js, index.html) use `assets/ui/`.

### CONSOLIDATION NOTES (read before generating)
- MERGED PAIR 1 (cloud/auth chip): the audit produced auth_saved.jpg (Surface B) and ui_cloud_save.jpg (Surface D) for the SAME signed-in chip. Keep auth_saved.jpg; drop ui_cloud_save.jpg. Pair it with auth_signin_plate.jpg for the signed-out state behind the official Google G SVG.
- MERGED PAIR 2 (lobby hero crest): hero_crest.jpg (Surface B) and logo_crest.png (Surface D) both target lobby.js:132-135. Keep logo_crest.png (PNG transparent, dual-purpose: lobby hero AND boot splash crest); drop hero_crest.jpg.
- NO GENERATION NEEDED (already on disk, wiring only): cur_gold.jpg, cur_gems.jpg, cur_scrap.jpg, cur_keys.jpg, cur_bones.jpg, loot_coin.jpg, loot_shard.jpg, loot_key.jpg, loot_tag_frame.png, daily_drop.png, the 4 emote_*.jpg, the 4 Crest_*.jpg faction crests, the 12 menu icon jpgs, lobby_hero.png, screen_victory.jpg, screen_defeat.jpg, chest_*.jpg.
- rw_bones.jpg is OPTIONAL: point bonesIco() at the existing cur_bones.jpg to skip it.

### GROUP 1 - REWARD SCREEN TOKENS (12)

1. rw_coins.jpg
"A small forged reward token: a tight heaped stack of freshly struck gold coins, each embossed in deep relief with a crowned dog-tag crest sigil (no readable lettering), two coins mid-tumble off the top of the pile, thick warm gold with mirror-bright specular highlights and worn battle-scuffed edges, faint magenta-and-cyan neon-noir city glow reflecting across the metal. Subject centered and floating just above a dark charcoal recessed circular plate ringed by a thin scratched-gold band, volumetric haze behind. Reads as a collectible minted currency token. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

2. rw_salvage.jpg
"A grimy looted fistful of stripped street scrip forged into a reward token: bent scrap-metal slugs, oxidized brass washers, a couple of tarnished dented coins and a torn copper shard fused into a shakedown cut, gunmetal and verdigris with gold edge-wear, fine sparks and oil grime, deliberately rougher and dirtier than clean mint coinage. Subject centered and floating above a dark charcoal recessed circular plate with a thin scratched-gold ring, volumetric haze. Reads as a salvaged-loot currency token. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

3. rw_keys.jpg
"A single ornate forged skeleton vault-key standing upright as a reward token, heavy machined brass-and-gold body with a crowned ornamental bow and crisply cut teeth, faint cyan neon glint along the shaft, a rare relic-grade jackpot drop, slight floating presentation with a soft gold halo. Subject centered above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Reads as a rare collectible key token. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic hero rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

4. rw_tags.jpg
"A single engraved brass dog-tag medallion hanging on a short ball-chain as a trophy reward token, battle-scratched gunmetal face with a milled gold rim and a blank crowned-crest emboss (no readable text), a second tag partly visible behind it, cold neon reflection on the chain, reads as a trophy taken off a beaten rival. Subject centered above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

5. rw_xp.jpg  (GENUINELY MISSING - no XP art exists today)
"A forged five-point rank star / chevron pip emblem as an experience token, polished gold over dark brushed steel, thin energized filament glowing warm gold along the star edges and points, a military experience-insignia feel, subtle radial energy bloom behind it. Subject centered above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Reads as an experience / rank token. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI, no progress bar."

6. rw_district.jpg
"A stamped territorial district crest reward token: a circular gold signet ring enclosing a stylized cluster of cyberpunk rooftops and a single watchtower silhouette (a claimed city block), struck into dark enamel like a wax seal of conquered turf, faint coin-gold sheen on the ring, neon haze behind the skyline. Subject centered above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Reads as a territorial-claim seal token. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

7. rw_sp.jpg
"A single faceted amber-gold skill-node gem socketed into a forged talon/bracket mount as a reward token, glowing from within, thin glowing circuitry-vein tendrils branching off the socket like a skill-tree node about to unlock, premium and energized, dark steel housing with gold filigree. Subject centered above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Reads as a skill-point / talent node token. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

8. rw_new_stamp.png  (transparent)
"A small foil corner stamp / wax-seal sunburst badge: a radiant gold starburst with a crowned spark at its center and a torn-foil ribbon edge, glossy with a holographic sheen catching magenta-cyan neon, the kind of fresh-pull seal slapped on the corner of a newly won card. Rendered on a pure flat #000000 background for clean alpha keying. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, square 1024x1024 transparent-ready. No text, no numbers, no letters, no watermark, no UI."

9. rw_crest_victory.png  (transparent, ~1024x768 vertical emblem)
"A regal victory crest lockup: a heavy ornate gold crown sitting atop crossed laurel branches with a subtle dog-fang motif worked into the crown band, a radiant warm halo and light shafts behind it, triumphant and premium, battle-worn gold catching neon-noir highlights, designed to sit ABOVE a headline word. Rendered on a pure flat #000000 background for clean alpha keying. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 accents, cinematic hero rim light, shallow depth of field, vertical emblem ~1024x768. No text, no numbers, no letters, no watermark, no UI."

10. rw_crest_defeat.png  (transparent, ~1024x768 vertical emblem)
"A fractured defeat crest lockup: a toppled, cracked gold crown with a broken-off point and a snapped laurel branch, lit cold by red-steel light, drifting ash and dying embers, somber and heavy, the mirror of a triumphant crest now fallen, designed to sit ABOVE a headline word. Rendered on a pure flat #000000 background for clean alpha keying. Gritty TV-MA cyberpunk neon-noir, battle-worn tarnished metal, dim Everlight gold #D4AF37 with cold crimson rim light, cinematic, shallow depth of field, vertical emblem ~1024x768. No text, no numbers, no letters, no watermark, no UI."

11. rw_crown.jpg
"A single clean minted crown insignia struck in deep relief on a dark circular disc, the title-currency emblem of a street-empire battler, polished gold crown with a crisp readable silhouette at tiny sizes, subtle milled rim, faint neon catch-light, high-contrast so it stays legible scaled down to 24px. Subject centered. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

12. rw_badge.jpg
"A blank forged challenge-coin / wax-seal achievement medallion backplate: a heavy circular disc with a concentric milled gold ring around a dark enamel center field left intentionally empty (a badge glyph composites on top), the disc battle-nicked and hero-lit like a hard-won military commendation, faint neon reflection on the rim. Subject centered. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, dramatic rim light, shallow depth of field, reads as an earned achievement medallion backplate, square 1024x1024, empty center. No text, no numbers, no letters, no watermark, no UI."

### GROUP 2 - SHOP / META-UI TOKENS (11)

13. rw_crate.jpg
"A miniature sealed back-alley supply crate reward token: riveted gunmetal panels banded with battered steel, a glowing gold seam running the lid line, a small crowned-B latch emblem on the front face, one corner dented and scorched, a sliver of warm light leaking from inside, three-quarter hero angle. Subject centered and floating above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Matches the chest reveal-crate look but token-scaled. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

14. rw_card.jpg
"A sealed premium card pack reward token: a dark foil wrapper with iridescent neon-purple/teal sheen, a crowned-dog emblem debossed into the foil, the top edge slightly torn to reveal a sliver of a glowing holographic card inside, worn creases and a gold tear-strip, standing at a slight angle. Subject centered and floating above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Reads as a collectible card-pack drop (sealed, not a face-up card). Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

15. rw_drop.jpg
"A mysterious street drop reward token: a battered parcel wrapped in dark cloth and bound with a thin gold chain, sealed by a crimson wax stamp bearing a crowned-dog mark, faint warm light leaking from a seam, scuffed and rain-stained. Subject centered and floating above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze, single hard spotlight. Reads as a sealed mystery reward (not a birthday gift). Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

16. rw_bones.jpg  (OPTIONAL - can reuse cur_bones.jpg)
"A forged trophy currency token shaped like a stylized dog bone: cast in scratched gunmetal with gold inlay running its length, mounted like a heavy dog-tag medallion, a crowned-dog stamp at the center knuckle, neon-amber glow pooled in the engraved channels, chipped and battle-worn. Subject centered and floating above a dark charcoal recessed circular plate ringed in scratched gold, volumetric haze. Reads as a premium commander currency collectible. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

17. emote_btn.jpg
"A circular battle-worn comms/hype emblem to serve as a tap-button face: a stylized crowned-dog head mid-howl rendered as a gold sigil inside a heavy gunmetal disc, a thin neon-gold ring, rivets and scratches, a soft holographic broadcasting glow, catching a hard rim-light. Subject fills the frame, centered on a dark charcoal plate, volumetric haze. Reads as a premium in-match taunt/emote button (not a smiley). Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

18. crew_crest_default.jpg
"A neutral house crew heraldic crest: a battered gunmetal shield with a crowned-dog head emblem centered over two crossed alley pipes/wrenches, a worn gold filigree border, faint neutral neon underglow (no faction color bias), rivets, dents and grime. Centered on a dark charcoal plate, hard rim-light, volumetric haze. The generic fallback crest for a crew with no resolved faction (a heraldic emblem, not a cartoon dog face). Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

19. gem_rarity.jpg  (neutral, CSS hue-tinted per rarity)
"A single faceted cut gemstone reward token: a brilliant multi-faceted crystal (marquise/emerald cut) seated in a thin scratched-gold bezel, razor-sharp specular highlights and internal refraction, near-neutral clear/white crystal so it can be hue-tinted per rarity, against a dark charcoal plate with a faint gold ring, hard rim-light. Reads as a rarity gem token for a drop-odds table. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

20. street_muscle.jpg
"A Muscle branch combat insignia: a clenched armored dog-paw fist crashing over two crossed reinforced rebar/pipe weapons, forged in dented black iron with gold studs, knuckle plates scarred, an aggressive red-neon underglow rising from below, heraldic and brutal. Centered emblem on a dark charcoal plate, hard rim-light, volumetric haze. Reads as a raw-power faction sigil. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light plus red neon accent, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

21. street_hustle.jpg
"A Hustle branch economy insignia: a crowned gold coin centered over two crossed loaded dice and a fanned playing card, slick gunmetal-and-gold heraldry, a green-neon money underglow, faint cigar-smoke haze, mob-boss opulence with grime. Centered emblem on a dark charcoal plate, hard rim-light. Reads as a run-the-block / get-paid faction sigil. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light plus green neon accent, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

22. street_tech.jpg
"A Tech branch insignia: a hexagonal circuit-core sigil with a crowned-dog microchip at its center, glowing cyan circuit traces fanning outward, a fractured gold casing around the hex, a hacker-grid underglow, cold blue rim-light. Centered emblem on a dark charcoal plate, hard rim-light, volumetric haze. Reads as a spells/systems/sabotage faction sigil. Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light plus cyan neon accent, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

23. ui_lock.jpg
"A small forged padlock token: a battle-scarred gunmetal padlock body with a crowned-dog-shaped keyhole, a thin polished-gold shackle, rivets and rust, a faint cold red locked-glow behind the keyhole, hard rim-light. Centered on a dark charcoal plate. Reads as a premium locked-tier token (not an OS padlock). Gritty TV-MA cyberpunk neon-noir, battle-worn forged metal, Everlight gold #D4AF37 rim-light plus subtle red lock-glow, ultra-detailed PBR, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

### GROUP 3 - LOBBY IDENTITY (5)

24. auth_saved.jpg  (signed-in cloud chip; supersedes ui_cloud_save.jpg)
"A forged battle-worn collectible emblem of a heavy vault padlock fused with a stylized storm cloud, centered on a dark gunmetal plate; cyberpunk neon-noir, hand-beaten gold trim #D4AF37, faint cyan data-stream filaments arcing up into the cloud, a single small glowing emerald-green status node embedded in the lock face signaling secured, scratched street patina, rivets, rim-lit gold edges, volumetric haze, cinematic studio lighting, dark radial-vignette background, hyperdetailed premium token. Subject centered, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

25. auth_signin_plate.jpg  (wide ~1024x384 background plate; the official Google G SVG overlays on top - do NOT generate a fake G)
"A weathered horizontal forged-metal nameplate bar, dark gunmetal body with hand-beaten gold trim and rivets at the four corners #D4AF37, subtle neon-noir cyan underglow seeping from beneath, scratched battle-worn patina and faint alley-grime texture, a clean empty brushed-metal center surface reserved for an overlaid mark, rim-lit gold edges, cinematic studio lighting on pure black, hyperdetailed premium plate, wide 1024x384 horizontal pill. No text, no watermark, no logo, no letters, no glyphs."

26. daily_drop_tile.jpg  (lobby icon-row tile; distinct from the existing shop daily_drop.png hero)
"A battle-worn forged supply-drop crate emblem viewed head-on as a collectible tile, gunmetal box bound in beaten gold straps #D4AF37 with a glowing gold seal-clasp dead center, faint frayed parachute rigging and a neon-noir cyan rim light, drifting gold dust and a few sparks, a pulsing ready-to-crack light seam glowing along the lid edge, scratched street-grime patina, centered on a dark plate with a soft radial glow, cyberpunk neon-noir, hyperdetailed. Subject centered, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

27. pass_emblem.jpg
"A forged circular season-campaign medallion as a collectible insignia, battle-worn brass and gold #D4AF37, an imperial crowned-bone laurel wreath ringing a central embossed alley-king sigil, neon-noir cyan and warm amber rim light, scratched patina, riveted beaded edge, a glowing molten-gold core, cinematic studio lighting on a dark plate with soft radial glow, hyperdetailed premium medallion. Subject centered, square 1024x1024. No text, no numbers, no numerals, no letters, no watermark, no UI."

28. wire_emblem.jpg
"A forged broadcast-transmission insignia as a collectible emblem, a battle-worn antenna tower emitting stylized concentric signal arcs, gunmetal and beaten gold #D4AF37, spray-stencil pirate-radio energy, neon-noir cyan signal waves rippling outward, a single glowing gold transmit node at the tower base, scratched grime and rust, centered on a dark plate with soft radial glow, cyberpunk neon-noir, hyperdetailed. Subject centered, square 1024x1024. No text, no numbers, no letters, no watermark, no UI."

### GROUP 4 - BOOT / LOADING / TRANSITIONS / HUD (8)

29. boot_splash.jpg  (vertical full-bleed 1080x1920)
"Vertical full-bleed cinematic splash backdrop for a cyberpunk dog-battler title screen. A lone battle-worn alpha pit-bull silhouette stands on a rain-slicked rooftop overlooking a sprawling neon-noir city skyline at night, low hero angle from behind the shoulder, volumetric gold light raking through smog and drifting embers, deep crushed blacks, teal and magenta neon haze far below, wet asphalt reflecting a single warm gold streetlight. Gritty TV-MA cyberpunk neon-noir, battle-worn brushed metal textures, heavy film grain, cinematic depth of field, dramatic rim light in Everlight gold #D4AF37. Negative space dead-center and lower-third reserved (uncluttered, slightly darker) so a crest and a loading token can sit on top. No text, no logo, no watermark, no UI. 1080x1920."

30. logo_crest.png  (transparent square 1024; lobby hero AND boot crest; supersedes hero_crest.jpg)
"Square emblem on a transparent background: a forged ornamental crest for a cyberpunk dog-kingpin brand. A heraldic shield of battle-worn gold-plated metal with a crowned snarling pit-bull head in profile at center, riveted brushed-steel edges, a small crowned-B medallion motif worked into the base, faint neon-teal under-glow leaking from behind the metal, scuffs and patina, cinematic studio key light glinting on the gold bevels. Gritty TV-MA cyberpunk neon-noir, Everlight gold #D4AF37 highlights, premium collectible insignia, reads as a forged physical badge. Centered subject, clean transparent alpha, generous padding. No text, no lettering, no watermark. 1024x1024."

31. ui_loader_paw.jpg  (spinnable token)
"Square collectible token centered on a dark plate: a forged gold paw-print medallion, a thick coin of battle-worn gold-plated metal stamped with a four-toe dog paw, a tiny crowned-B mark embossed in the heel pad, riveted rim, radial brushed-metal tooling that implies rotation, faint neon-teal rim glow, scuffs and patina, dramatic single-source key light glinting off the bevels, sitting on a near-black recessed plate with a subtle gold ring. Gritty TV-MA cyberpunk neon-noir, Everlight gold #D4AF37, premium forged-coin feel, reads as a spinnable physical token. Centered, square 1024x1024. No text, no numerals, no watermark."

32. menu_bg_poster.jpg  (vertical 1080x1920; render from the actual first frame of the menu loop for a seamless handoff)
"Vertical menu wallpaper, a static frame matching a looping cyberpunk lobby ambience. A heroic battle-scarred pit-bull in a battered armored harness sits commanding on a neon-lit alley throne of stacked crates and chrome, gold graffiti crown tag glowing on the brick wall behind, rain mist and drifting embers, deep teal and amber neon reflections on wet pavement, volumetric god-rays of warm gold light, shallow depth of field. Composition keeps the upper strip and lower strip slightly darker so a glass top bar and a glowing button float legibly on top. Gritty TV-MA cyberpunk neon-noir, battle-worn metal, Everlight gold #D4AF37 accents, cinematic, atmospheric. No text, no UI, no watermark. 1080x1920."

33. ui_tile_plate.jpg  (empty waiting-slot plate, masks first-paint emoji on menu tiles)
"Square empty insignia plate centered on dark background: a blank forged badge slug, a rounded-square plate of battle-worn gunmetal with a beveled Everlight-gold riveted rim, a subtle embossed crowned-B watermark debossed faintly into the brushed-metal center, soft inner gold rim-glow, scuffs and grime, single dramatic key light catching the bevel. The center is intentionally near-empty (a waiting slot), reads as the base plate a collectible icon would be stamped onto. Gritty TV-MA cyberpunk neon-noir, Everlight gold #D4AF37, premium forged-metal token. Centered, square 1024x1024. No text, no symbol other than the faint embossed mark, no watermark."

34. ui_transition_veil.jpg  (vertical 1080x1920; mostly gradient/haze so it composites as a moving wipe overlay)
"Vertical full-screen transition veil, a sweeping curtain of light and smoke for a screen wipe. A diagonal band of warm gold volumetric light-leak and fine atmospheric haze crossing a near-black field, soft embers and dust motes catching the glow, a faint streak of teal neon at the leading edge, heavy on one side fading to transparent dark on the other so it reads as a moving wipe. Gritty TV-MA cyberpunk neon-noir, Everlight gold #D4AF37 light, cinematic motion-blur feel, atmospheric. No subject, mostly gradient/haze. No text, no watermark. 1080x1920."

35. ui_hud_pause.jpg  (HUD control token)
"Square collectible HUD token centered on a dark plate: a forged gold pause emblem, two thick vertical bars cast in battle-worn gold-plated metal with riveted ends and beveled edges, mounted on a circular gunmetal button with a thin glowing Everlight-gold rim, faint neon under-glow, scuffs and grime, dramatic key light glinting off the bevels. Gritty TV-MA cyberpunk neon-noir, Everlight gold #D4AF37, premium forged control-button feel, reads as a physical pressable token. Centered, square 1024x1024. No text, no watermark."

36. ui_hud_storm.jpg  (HUD control token)
"Square collectible HUD token centered on a dark plate: a forged storm sigil, a jagged lightning bolt cast in battle-worn gold-plated metal striking through a coiled storm-cloud relief, mounted on a circular gunmetal button with a thin glowing Everlight-gold rim, crackling neon-teal electric arcs along the bolt, scuffs and patina, dramatic key light glinting off the bevels. Gritty TV-MA cyberpunk neon-noir, Everlight gold #D4AF37 with electric-teal accent, premium forged token, reads as a physical pressable insignia. Centered, square 1024x1024. No text, no watermark."

---

## 5. LOADING-SCREEN BUILD SPEC (cinematic preload gate)

Principle: a fully self-contained additive overlay plus a tiny ES5 controller that runs FIRST (top of body, above the script tags at index.html:1983), exposes `window.AKPreload`, and is hooked by 5 one-line additive edits in the existing preloaders plus 2 completion signals. Every hook is guarded so a missing/failed gate is a pure no-op and the Node harness stays byte-identical.

### 5.1 Boot reality (as-is)
- Scripts load bottom-of-body in a documented dependency chain (index.html:1982-1999): canon -> cards_lore -> classes -> handlers_data -> keywords_data -> engine -> ak_account -> social -> pass -> quests -> drip -> lobby -> the inline boot IIFE (index.html:2000-8651, AK.init() at 8635).
- The visible lobby is assembled by lobby.js restructure() (defined lobby.js:120, runs from boot() lobby.js:232-233 on DOMContentLoaded), which re-parents buttons, appends #ak-bgvid (lobby.js:191 playing menu_bg.mp4) and calls refresh(). That is the true "lobby assembled" moment.
- Art today preloads fire-and-forget with onerror-only, NO counter: preloadIcons() (index.html:2225-2238, called at 2265) for 48 unit/variant card PNGs, preloadSections() (2240-2262) for 4 backdrops + 8 tower skins, LOOT_IMG (3499-3507) for 4 loot icons. Chest art loads on demand (4957). Menu icons preload in lobby.js:170-178. There is NO existing loader.

### 5.2 Overlay CSS - inject in <head> immediately before </head> (index.html:1602)
Self-contained `<style id="akpl-css">` block. Full-screen fixed #akpl at z-index 99999, #070708 base, opacity transition to .akpl-gone; #akpl-vid object-fit cover; #akpl-scrim radial darkening; #akpl-core column (logo Cinzel gold-gradient, Playfair tagline, gold progress bar #akpl-bar with cubic-bezier width transition, #akpl-pct, rotating #akpl-tip); akpl-pulse keyframe; honors prefers-reduced-motion. (Full CSS is in the loading-screen architecture source; mount verbatim.)

### 5.3 Overlay markup + controller - inject immediately AFTER <body> (index.html:1603), BEFORE <div id="app"> (1604)
Markup: #akpl with a `<video id="akpl-vid" autoplay loop muted playsinline preload="auto" poster="assets/ui/lobby_hero.png"><source src="assets/ui/menu_bg.mp4"></video>`, a scrim, and #akpl-core (logo "ALLEY KINGZ", sub "Run the pack. Rule the streets.", bar, pct, tip).
Controller (ES5 IIFE, no deps): tracks loaded/total/shown (monotonic, capped at 92% until seal). Functions: watch(node) (bumps total, attaches load/error/canplaythrough/loadeddata + per-asset 8s timeout, idempotent via node.__akpl), add(url,type), bump(n), seal(), bootReady(), forceReveal(reveal). reveal() sets 100%, adds .akpl-gone, self-removes after 700ms. maybeReveal() fires when sealed && booted && loaded>=total AND elapsed>=MIN_MS (1100ms anti-flash), or unconditionally at MAX_MS (12000ms). Shell manifest add()'s ~30 named UI assets (lobby_hero, play_btn, screen_victory/defeat, cur_*, chest_*, loot_*, the 12 menu icons), warm-loads the_lot.mp3 soft (preload only, never .play(), so the autoplay block at index.html:4799 is irrelevant), tracks fonts as one unit via document.fonts.ready, watches the loader video soft. Failsafes: hard watchdog setTimeout(reveal, MAX_MS); window 'error' forces sealed=booted=true then reveal; window 'load' marks booted.

### 5.4 The 8 edits (edit manifest)
| # | File | Line | Change |
|---|------|------|--------|
| 1 | index.html | before 1602 (</head>) | add `<style id="akpl-css">` block (5.2) |
| 2 | index.html | after 1603 (<body>) | add #akpl overlay markup + controller `<script>` (5.3) |
| 3 | index.html | 2235 | `try{ window.AKPreload && AKPreload.watch(img); }catch(_){}` (after UNIT_ICONS[...]=img) |
| 4 | index.html | 2245 | `try{ window.AKPreload && AKPreload.watch(bg); }catch(_){}` (after SECTION_BG[sec]=bg) |
| 5 | index.html | 2251 | `try{ window.AKPreload && AKPreload.watch(timg); }catch(_){}` (after SECTION_SKINS[sec][tt]=timg) |
| 6 | index.html | 3506 | `try{ window.AKPreload && AKPreload.watch(img); }catch(_){}` (after LOOT_IMG[e[0]]=img) |
| 7 | index.html | 8651 (})();) | insert before it: `try{ window.AKPreload && AKPreload.seal(); }catch(_){}` (single correct seal point: by line 8651 preloadIcons + LOOT_IMG have registered every image) |
| 8 | lobby.js | 201 | `try{ global.AKPreload && global.AKPreload.bootReady(); }catch(_){}` (after global.AKLobby={refresh}; the lobby-assembled signal) |

No `?v=` bump needed for inline code.

### 5.5 Progress logic
total grows as watch/add/bump register (~95-100 tracked fetches: ~30 shell UI + 1 font unit + 1 video + 1 audio + 48 card PNGs + 4 backdrops + 8 towers + 4 loot). loaded increments on load/error/canplaythrough/timeout, so it ALWAYS reaches total even when files 404 (unpainted variant cards, missing skins). Displayed shown is monotonic and capped at 92% until seal() freezes total, so the bar never reaches 100% early and never jumps backward. Reveal fades over .6s then self-removes; the lobby underneath (already built by restructure(), already playing the SAME menu_bg.mp4) shows through seamlessly (loader video and lobby video are the same loop, so the crossfade is invisible).

### 5.6 The looping MP4
Reuses the existing assets/ui/menu_bg.mp4 (on disk, 2.5 MB, already used by lobby.js:191), poster=lobby_hero.png (on disk). Same file for loader + lobby = zero extra download + seamless handoff. Optional upgrade: render a new seamless loop.

MP4 LOOP PROMPT (1080x1920 vertical, H.264 MP4, no audio, under 3 MB, 6-8s seamless loop):
"Cinematic slow dolly-forward through a rain-slicked neon cyberpunk back-alley at night, Clash-Royale-meets-Call-of-Duty mood. Wet asphalt reflecting gold and warm-amber signage, drifting fog and floating dust embers, distant holographic billboards bokeh'd out. A pack of stylized armored battle-dogs in piloted street-rigs sit half-silhouetted in the mid-ground, breathing idle, chrome and gold trim catching the light. Subtle gold light-rays, gentle particle drift, shallow depth of field. Moody, premium, luxury-grit. Color grade: deep blacks #070708, gold accents #c9a84c to #e8c55a, restrained cyan rim light. Camera performs a slow seamless push-in and settles, looping smoothly back to start. No text, no logos, no people, no on-screen UI. Ultra high detail, filmic, 24fps, vertical 9:16."
Deliver as a drop-in replacement assets/ui/menu_bg.mp4 (both loader and lobby pick it up) or a new assets/ui/loader_bg.mp4 (point only the loader source at it). Trim to a clean cycle; first and last frames identical.

### 5.7 Fallback (never hard-block boot)
1. Per-asset 8s timeout in watch() so one stuck fetch cannot stall.
2. error events count as done so 404s reach 100% normally.
3. Hard watchdog setTimeout(reveal, MAX_MS=12s).
4. window 'error' listener forces sealed=booted=true then reveals on any uncaught boot exception.
5. window 'load' marks booted as a backstop if restructure() is skipped.
6. Video failure -> poster lobby_hero.png; poster failure -> #070708 bg. Video is soft, never required.
7. Audio is warm-load only (preload, no play) so autoplay policy never gates reveal.
8. Every hook is try/catch guarded so a parse-failed controller leaves boot exactly as today.
9. Node harness: HAS_IMAGE is false (index.html:2208), window.AKPreload undefined, all edits no-op, tests byte-identical.

---

## 6. AUDIO - TOOL PICKS, PROMPT PACK, LICENSE RISK

Headline: the tools with the best anime-opening vibe (Suno, Udio) are the two with the worst legal exposure, and every free tier here is non-commercial. For a Stripe-monetized game, the safe path is a paid clean-license music tool plus paid ElevenLabs for hero SFX plus free royalty-free for the rest.

### 6.1 Recommended stack
- Lobby/intro theme: PAY for ONE of Beatoven.ai (cleanest commercial license, perpetual, survives cancellation, ~$20/mo) or Soundraw (~$same, verify the free-download commercial clause in-app at export). Use Udio/Suno Pro ONLY if the operator knowingly accepts active major-label litigation risk. NEVER ship a free-tier AI track.
- Hero SFX (chest open, victory sting): ElevenLabs Sound Effects, Starter $5/mo, full commercial ownership, perpetual. The free tier PROHIBITS commercial use and forces attribution, so do not ship free-tier SFX.
- Everything else (taps, shimmer, defeat, ambience): zero cost from Sonniss GDC Bundle (free, royalty-free, game-specific), Pixabay (free commercial, no attribution), Freesound CC0 filter (no attribution), jsfxr/Bfxr/ChipTone (you generate, clean provenance).
- Keep a CSV manifest of every audio file: source, URL, license, date pulled. Screenshot each paid tool's live license/ToS at ship time and store it with the manifest.

### 6.2 Music prompt (loopable anime-opening intro / lobby theme)
"High-energy anime opening theme for a neon cyberpunk street-dog battle arena. 146 BPM, key of E minor. Mood: defiant, heroic, swaggering, gritty. Instrumentation: distorted power-chord electric guitar, punchy orchestral brass stabs, fast bright synth arpeggio, taiko plus 808 trap hats, short choir hey shouts, deep sub bass. Structure: 2-bar riser into a hard downbeat drop, anthemic hook, energy stays maxed. Clean 8-bar seamless loop, no fade, no vocals, ends on the downbeat so it loops back into the intro. Reference feel: shonen opening meets electronic hybrid trailer music."

### 6.3 SFX prompts (ElevenLabs text-to-SFX; retro ones also doable on jsfxr/ChipTone)
1. Chest open: "Heavy metal-and-leather loot crate unlatching: two mechanical clicks, a low creak as the lid lifts, then a warm magical whoosh and a short golden chime as light spills out. 2 seconds, crisp, game UI."
2. Reward shimmer: "Bright cascading magical sparkle, like gold coins and gems catching light, ascending crystalline shimmer with a soft bell tail. 1.2 seconds, clean, no reverb wash."
3. Victory sting: "Triumphant short victory fanfare: rising brass swell, synth arpeggio flourish, single big orchestra-hit plus cymbal accent, confident and street-cool. 2.5 seconds, ends decisively."
4. Button tap: "Crisp futuristic UI button tap: short snappy digital click with a tiny synth blip, premium and tactile, no resonance. 0.15 seconds."
5. Defeat: "Somber defeat cue: descending detuned synth tone powering down into a low muffled thud, slight vinyl-grit, deflating and final. 1.8 seconds."

### 6.4 License risk (honest)
- Litigation (HIGH): Suno and Udio are under active major-label lawsuits over training data. A paid license does NOT indemnify against a third-party claim if an output resembles protected material. Prefer Beatoven/Soundraw or hand-curated royalty-free for a monetized title.
- Copyrightability gap: the US Copyright Office does not grant copyright to purely AI-generated audio, so others may reuse the AK theme regardless of generator. Human editing/arrangement strengthens the position.
- Free-tier traps: Suno, Udio, Stable Audio, Mubert, Loudly, AIVA, ElevenLabs all forbid commercial use on free tiers (ElevenLabs + AIVA also force attribution). Rights bind to the plan AT GENERATION TIME; you cannot retroactively clear a free-tier asset by upgrading.
- Conflicting Soundraw reporting: confirm the exact license text in-app before shipping any free Soundraw export. Beatoven free plan cannot download (effectively paid-only).
- Sonniss restriction: their license bars using the sounds to TRAIN AI (fine for direct in-game playback; relevant only if fed into the art/sound factory). Pixabay/CC0: do not ship sounds containing recognizable trademarks and never redistribute raw files as a standalone pack.

---

## 7. HONEST RISKS

SCOPE
- This is a broad polish push across 4 surfaces plus boot plus audio, touching index.html, lobby.js, shop.js, drip.js, social.js, ak_account.js, and CSS. Land it in waves (Phase 0 then Phase 1 then Phase 3 art) rather than one mega-commit. The reward-screen + lobby first paint are the highest-ROI; the deep shop/Street-Code polish is lower visibility.
- pass.js and quests.js are dead duplicates (lobby routes to shop.html#pass2/#hit2). Preferred action is DELETE them to cut maintenance surface; if kept, every helper must be pasted twice and can drift.

PERFORMANCE
- The preload gate adds ~95-100 tracked fetches but they were already being fetched fire-and-forget; the gate only adds listeners + a 12s ceiling, so net cost is negligible. Risk is mis-set MIN_MS/MAX_MS making the splash feel slow; tune MIN_MS down if testing shows fast loads.
- Mounting many <img> tokens at small sizes is cheap, but the reward screen builds them per-row on reveal; keep the shared .rw-curico class so the browser reuses cached decodes. Tokens are 1024x1024 source rendered at 14-42px; ensure the CDN serves them compressed (target under ~80 KB each) or first paint of the reward screen could stutter on low-end phones. Consider a 256px export variant for UI tokens vs the 1024 master.
- A new menu_bg.mp4 must stay under ~3 MB and seamless; a heavier loop hurts mobile data and the loader handoff.

LICENSE
- Audio is the real legal exposure (section 6.4). Do not ship any free-tier AI music. The official Google G for the sign-in plate MUST be the official inline SVG; do NOT Seedance-generate a fake G (trademark).
- Per existing doctrine, keep brand/IP discreet: do not feed unreleased AK concepts into third-party generators beyond what is necessary; queue art through the internal art factory.

ART VOLUME (the binding constraint)
- 36 net-new image assets plus 1 MP4 loop. At the chest-reveal quality bar, that is a meaningful generation queue. Generation is BLOCKED on operator-provided Seedance access + budget (Leonardo API is dead; CF Workers AI failover needs CF_AI_TOKEN). Until that unblock, only Phase 0 (loading screen, code-only) and Phase 1 (wire existing on-disk art) can ship.
- Because every wiring slot has an onerror fallback to today's glyph/dot, art can land incrementally as a hot-swap; the game is never broken by a missing asset. Generate in the section-2 priority order (reward tokens + lobby identity first).
- Two duplicate-purpose designs were merged (auth_saved vs ui_cloud_save; logo_crest.png vs hero_crest.jpg). Confirm those merge choices before generating to avoid producing throwaway art.

DEPLOY / VERIFY
- Phone game/ is the source of truth. Deploy ONLY via rsync phone -> e5-mother -> ship.sh (stamps ?v=timestamp). A 2nd chat deploying from stale e5 sources has clobbered the live site before; this is the sole-deployer lane. Maps live on a separate CF project (alley-kingz-maps) and must not be touched by game deploys.
- Always VERIFY the live edge in a real browser (Playwright on e5-mother), not just the Node harness. Inline-code edits need no ?v= bump; new binary assets do (ship.sh handles it).
