# Alley Kingz -- Custom Art Prompt Sheet (Seedance)

**How this works:** generate each one in Seedance, save to `/sdcard/Download` with the EXACT
filename in **bold** below (Seedance saves JPEG even if named .png -- that's fine, keep the name I give).
Then tell me "art's in" and I place + wire them. Same loop as the handlers + menu icons.

**House style (paste at the end of every prompt):**
> Gritty TV-MA cyberpunk street aesthetic, neon-noir alley lighting, battle-worn metal and concrete,
> Everlight gold (#D4AF37) accents, deep near-black background, high detail, dramatic rim light,
> centered subject, video-game asset, no text, no watermark.

Every icon = **square 1024x1024**, subject centered on a dark plate so it reads as a badge.
Screens = **vertical 1080x1920** (phone). I'll mask/round/crop in code.

---

## TIER 1 -- Currency & loot (you see these every screen) -- do these first

**cur_gems.jpg** -- A cluster of glowing cyan-violet crystal gems on a dark obsidian plate, faceted, internal glow, premium. [house style]

**cur_gold.jpg** -- A stack of battle-worn gold coins stamped with a crowned dog-bone "B" sigil, warm gold glow on dark. [house style]

**cur_scrap.jpg** -- A pile of salvaged metal scrap (bent rebar, bolts, a torn circuit shard), cold steel with faint sparks, on dark. [house style]

**cur_bones.jpg** -- A small pile of chrome-plated dog bones with a faint gold rune glow, trophy feel, on dark. [house style]

**cur_keys.jpg** -- A heavy ornate skeleton key forged from gold and gunmetal with a dog-bone bow, glowing keyhole teeth, on dark. [house style]

**loot_coin.jpg** -- A single spinning gold coin (the crowned-B sigil), bright glint, motion-blur edge, small battlefield pickup, on dark. [house style]

**loot_shard.jpg** -- A single sharp crystal scrap-shard, cyan glow, floating pickup with a soft ground shadow, on dark. [house style]

**loot_key.jpg** -- A single glowing key fragment (broken half of a gold key), sparks at the break, on dark. [house style]

---

## TIER 2 -- Chests (you flagged these are blank) -- high impact

**chest_wood.jpg** -- A battered wooden street-crate reinforced with rusted metal bands and a gold-bone padlock, closed, sitting in a neon alley, slight gold glow at the seams. [house style]

**chest_bronze.jpg** -- Same crate upgraded: bronze-plated corners, brighter lock, embers. [house style]

**chest_silver.jpg** -- Chrome/silver armored chest, cyan glow seams, sci-fi latches, closed. [house style]

**chest_gold.jpg** -- A royal gold chest with the crowned-B sigil, radiant gold light bursting from the seam, closed but glowing like it's about to pop. [house style]

**chest_diamond.jpg** -- A crystalline diamond-and-gold vault chest, prismatic light, the rarest tier, closed. [house style]

> **Chest opening (optional, your call):** Seedance can do short clips. If you want the
> "open" moment, generate a **3-4 sec video** per chest: `chest_gold_open.mp4` -- the gold
> chest lid bursts open, light beam shoots up, gold coins + a glowing card fly out, loops back
> closed. I can wire it to play once on the reward screen (a small inline video), then show
> the rewards. Start with just `chest_gold_open.mp4` so we prove the flow before doing all 5.

---

## TIER 3 -- The Play button & screens (you asked for the big yellow play)

**play_btn.jpg** -- A wide horizontal battle-CTA plate: brushed gold metal with a glowing forward-chevron / play arrow, crowned-B sigil embossed left, riveted edges, the word-space left blank (I add "BATTLE" text in code), neon underglow. **Make this 1024x512 (wide).** [house style]
> I'll wire it as the lobby's big PLAY button background. If you'd rather a tall vertical
> version too, also make **play_btn_tall.jpg** at 512x1024.

**screen_victory.jpg** -- A triumphant cyberpunk alley at golden dawn: a victorious armored dog-king silhouette on a throne of scrap, gold confetti light, crowns and bones raining, room left at center/bottom for the result card. Vertical 1080x1920. [house style]

**screen_defeat.jpg** -- A somber rain-soaked neon alley at night, a lone battle-worn dog silhouette under a flickering streetlight, broken crown on wet concrete, cold blue tone, room left center/bottom for the result card. Vertical 1080x1920. [house style]

**timer_frame.jpg** -- A small ornate gold-and-gunmetal HUD bezel/frame for the match countdown clock, hexagonal, glowing edge, dark empty center (I overlay the live numbers). 512x512. [house style]

---

## TIER 4 -- Keyword icons (the 10 card mechanics, faction-tinted badges)

Square 1024x1024 badges, each a small emblem on a dark plate tinted with the listed color.
(These are the chips players see on cards -- making them custom sells the mechanics.)

**kw_frontline.jpg** -- A riot-shield wall of scrap metal, "hold the line," tinted burnt-orange #c0612e. [house style]
**kw_hidden.jpg** -- A dog silhouette dissolving into static/shadow, stealth, tinted violet #9B8CFF. [house style]
**kw_ward.jpg** -- A glowing hexagonal tech-rune barrier deflecting a spell bolt, tinted blue #6fb6ff. [house style]
**kw_protected.jpg** -- A golden bubble shield over a dog tag, first-hit guard, tinted gold #D4AF37. [house style]
**kw_regen.jpg** -- A pulsing green heartbeat/cross over a bandaged paw, healing, tinted green #5fff8f. [house style]
**kw_burn.jpg** -- A snarling ember-mawed flame glyph, damage-over-time, tinted hot-orange #ff5a2c. [house style]
**kw_twin_strike.jpg** -- Two crossed neon fangs/blades striking twice, tinted teal #1fd6c4. [house style]
**kw_deadly.jpg** -- A skull-and-fang poison glyph, lethal, tinted red #ff4d6d. [house style]
**kw_afterlife.jpg** -- A ghostly spectral dog rising from a grave glyph, death-spawn, tinted purple #b06bff. [house style]
**kw_blitz.jpg** -- A lightning-fast dog blur with speed lines, instant-charge, tinted cyan #2ee6ff. [house style]

---

## TIER 5 -- Emotes & flair (lowest priority, nice-to-have)

**emote_woof.jpg / emote_crown.jpg / emote_gg.jpg / emote_skull.jpg** -- small circular sticker-style
dog emotes (woof bark, gold crown, handshake, skull), comic punch, on dark. [house style]

---

### Notes
- **Format:** square icons + wide play button + vertical screens. JPEG is fine (no transparency
  needed -- the dark plate IS the background, it blends into the game's dark UI).
- **Priority order:** Tier 1 -> 2 -> 3, then 4/5 whenever. Even just Tier 1 makes the whole HUD feel custom.
- Don't worry about exact pixel size -- get close, I crop/mask in code.
- When a batch is in `/sdcard/Download`, ping me and I'll place + wire + deploy + verify live.
