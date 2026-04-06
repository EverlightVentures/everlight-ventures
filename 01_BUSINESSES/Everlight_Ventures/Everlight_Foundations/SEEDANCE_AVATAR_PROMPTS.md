# Seedance Avatar & Brand Asset Prompt Guide
## Everlight Blackjack V3

**Important**: Seedance is a VIDEO generator (4-15 sec clips). For still images/sprites, use **Seedream** (ByteDance's image model, available in Dreamina) or export a single frame from a Seedance clip. The workflow below covers both.

---

## WORKFLOW STRATEGY

| Asset | Tool | Why |
|-------|------|-----|
| Dealer animated portraits | **Seedance 2.0** | Looping video clips of dealers breathing, blinking, reacting |
| Player avatar base templates | **Seedream** (image) | Static layered character pieces for the avatar builder |
| Accessories/fashion items | **Seedream** (image) | Individual PNG items on transparent bg |
| App icon / logo | **Seedream** (image) | Static brand mark |
| Promo video / trailer | **Seedance 2.0** | Marketing clips |

**Output settings for Seedance 2.0**: 1080p, 4-6 seconds (for looping dealer animations), 9:16 or 1:1 aspect ratio

**Output settings for Seedream**: 1024x1024 or 2048x2048, PNG with transparency where possible

---

## PART 1: DEALER AVATARS (Seedance 2.0 -- Animated Video Loops)

These become looping video portraits displayed at the dealer position. Each is 4-6 seconds, designed to seamlessly loop.

### Dealer 1: ARIA (Table 1 -- Standard, Warm & Friendly)

```
A close-up portrait of a young woman casino dealer, warm caramel skin tone, dark brown wavy hair falling past her shoulders, gold hoop earrings catching the light, wearing a fitted black dealer vest with gold trim piping over a white dress shirt. She has a warm, welcoming smile with soft brown eyes. She breathes gently, blinks naturally, and gives a subtle knowing nod as if encouraging a player. Warm pink and amber ambient lighting from above, dark casino background with soft golden bokeh lights. The camera holds steady in a medium close-up, slight shallow depth of field. Cinematic quality, luxury casino atmosphere, photorealistic, high detail skin texture. Maintain face and clothing consistency, no distortion, seamless loop. --ar 1:1 --duration 5s
```

### Dealer 2: MARCUS (Table 2 -- Standard, Confident & Cool)

```
A close-up portrait of a confident Black male casino dealer, rich dark skin with clean high-fade haircut, sharp jawline, wearing a tailored black suit jacket with a gold tie clip that catches the light. He has a cool confident smirk with intense brown eyes. He breathes steadily, blinks naturally, and tilts his chin up slightly with a subtle "let's go" expression. Cool blue and ambient lighting from above, dark casino background with soft blue and white bokeh lights. The camera holds steady in a medium close-up, slight shallow depth of field. Cinematic quality, luxury VIP casino atmosphere, photorealistic, high detail skin texture. Maintain face and clothing consistency, no distortion, seamless loop. --ar 1:1 --duration 5s
```

### Dealer 3: VALENTINA (High Roller Table -- Elegant & Sophisticated)

```
A close-up portrait of an elegant female casino dealer, fair porcelain skin, platinum blonde hair swept up in a sophisticated updo with loose tendrils framing her face, red lipstick, wearing a sleek black off-shoulder dress with a diamond necklace that sparkles in the light. She has a refined raised eyebrow and subtle mysterious smile. She breathes gently, blinks slowly and deliberately, and gives a slight impressed nod. Warm gold ambient lighting from above creating soft highlights on the diamonds, dark luxurious casino background with gold and champagne bokeh lights. The camera holds steady in a medium close-up, cinematic shallow depth of field. Ultra luxury atmosphere like a Monte Carlo casino, photorealistic, high detail, glamorous. Maintain face and clothing consistency, no distortion, seamless loop. --ar 1:1 --duration 5s
```

### Dealer 4: DOMINIC (VIP Table -- Mysterious & Intense)

```
A close-up portrait of a mysterious male casino dealer, olive Mediterranean skin tone, dark hair slicked back with precision, well-groomed short beard, wearing a black tuxedo with gold cufflinks that catch subtle light. He has an intense penetrating gaze with dark eyes and a slight enigmatic half-smile. He breathes steadily, blinks slowly, and gives a barely perceptible knowing look as if he sees everything. Deep purple and dark ambient lighting from above, dark ultra-exclusive casino background with purple and gold bokeh lights. The camera holds steady in a medium close-up, dramatic cinematic lighting with one side of his face slightly shadowed. Ultra luxury underground casino vibe, photorealistic, high detail skin and fabric texture. Maintain face and clothing consistency, no distortion, seamless loop. --ar 1:1 --duration 5s
```

### DEALER REACTION CLIPS (generate separately for each dealer)

For each dealer, also generate these 4-second reaction clips. Use the same reference image from the idle portrait as `@image1` to maintain face consistency:

**On Player Blackjack (impressed):**
```
@image1 as face reference. The casino dealer's eyes widen slightly with genuine surprise, eyebrows raise, and they break into an impressed smile while giving a single slow nod of respect. Their expression shifts from neutral to admiration over 3 seconds. Same lighting and background as reference. Maintain exact face, hair, clothing consistency. Photorealistic, cinematic. --ar 1:1 --duration 4s
```

**On Player Bust (sympathetic smirk):**
```
@image1 as face reference. The casino dealer's expression shifts to a subtle sympathetic smirk -- one corner of their mouth lifts slightly, they tilt their head a few degrees, and give a small shrug as if to say "tough luck." Understated, not mocking. Same lighting and background as reference. Maintain exact face, hair, clothing consistency. Photorealistic, cinematic. --ar 1:1 --duration 4s
```

**On Big Win (excited):**
```
@image1 as face reference. The casino dealer breaks into a wide genuine smile, their eyes light up, and they give two slow claps of appreciation. The ambient lighting brightens slightly with warm gold tones. Celebratory energy. Same background as reference. Maintain exact face, hair, clothing consistency. Photorealistic, cinematic. --ar 1:1 --duration 4s
```

**On Jackpot (shocked and thrilled):**
```
@image1 as face reference. The casino dealer's jaw drops open in genuine shock, eyes go wide, then they break into an enormous smile and clap enthusiastically. Their whole demeanor shifts from composed to electrified. Gold light flares intensify behind them. Same background as reference. Maintain exact face, hair, clothing consistency. Photorealistic, cinematic. --ar 1:1 --duration 5s
```

---

## PART 2: PLAYER AVATAR BASE TEMPLATES (Seedream -- Static Images)

Generate these as character portrait bases for the avatar customization system. Each should be a clean bust portrait (shoulders up), looking directly at camera, neutral expression, on a solid dark background for easy compositing.

### Skin Tone Bases (generate 8)

Use this template, changing skin description for each:

```
A clean digital portrait of a person with [SKIN TONE] skin, looking directly at the camera with a calm neutral expression, shoulders visible, no hair (bald/clean head for layering), no accessories, no jewelry, wearing a plain dark gray crew neck shirt. Solid black background #0A0A0A. Even studio lighting, no harsh shadows. Clean edges, high detail skin texture, semi-stylized art style that sits between photorealistic and high-quality game art -- think premium mobile game character select screen. PNG with clean edges. Square format. --ar 1:1
```

**Skin tones to generate:**
1. `fair ivory skin tone, light complexion with subtle warm undertones`
2. `light beige skin tone, European complexion with neutral undertones`
3. `warm tan olive skin tone, Mediterranean complexion`
4. `golden caramel skin tone, warm complexion`
5. `warm brown skin tone, South Asian or Latin complexion`
6. `rich brown skin tone, warm undertones`
7. `deep dark brown skin tone, rich mahogany undertones`
8. `deep ebony skin tone, cool undertones with smooth texture`

### Hairstyle Overlays (generate 12 per gender, use consistent art style)

```
A [HAIRSTYLE] hairstyle in [COLOR] color, rendered as an isolated element on a solid black background, top-down 3/4 angle as it would appear on a person's head looking at camera. Semi-stylized premium game art style, detailed hair strands visible, soft lighting with subtle shine highlights. Clean edges suitable for compositing. No face, no body -- just the hair. Square format. --ar 1:1
```

**Hairstyles:**
1. `clean high fade` (male)
2. `long flowing locs falling past shoulders` (unisex)
3. `neat cornrow braids pulled back` (unisex)
4. `high ponytail` (female)
5. `military buzz cut` (male)
6. `wavy medium-length tousled` (unisex)
7. `tight natural curls, short` (unisex)
8. `tall mohawk with faded sides` (male)
9. `completely bald smooth head` (unisex)
10. `slicked back with pomade shine` (male)
11. `voluminous afro, perfectly rounded` (unisex)
12. `chin-length bob with straight bangs` (female)

**Hair colors to cycle through:** jet black, dark brown, honey blonde, auburn red, silver gray, electric blue, hot pink, deep purple

### Expression Overlays (4 base expressions -- generate as face close-ups)

```
A close-up face showing a [EXPRESSION] expression, looking directly at camera. Semi-stylized premium game art, detailed eyes and mouth. Even lighting, black background. Clean edges. No hair visible. Square format. --ar 1:1
```

1. `warm confident smile, friendly approachable energy`
2. `serious focused look, determined intense gaze, slight furrowed brow`
3. `playful sideways smirk, one eyebrow slightly raised, mischievous energy`
4. `calm mysterious half-smile, subtle and enigmatic, cool composure`

---

## PART 3: FASHION & ACCESSORIES (Seedream -- Isolated Items)

Generate each item isolated on transparent/black background for compositing onto avatars.

### Outfit Tops

```
A [OUTFIT] rendered as an isolated clothing item on solid black background, shown from the front as it would appear on a person's upper body. No body visible inside -- the garment holds its shape as if on an invisible mannequin. Premium quality fabric rendering with realistic wrinkles and texture. Semi-stylized game art quality. [COLOR] color. Clean edges. Square format. --ar 1:1
```

**Outfits:**
1. `fitted plain crew neck t-shirt` (casual) -- in white, black, red, navy, gray, olive
2. `crisp button-up dress shirt, collar open one button` -- in white, light blue, black, lavender, pink, charcoal
3. `tailored single-breasted suit jacket over dress shirt` -- in black, navy, charcoal, burgundy, cream, forest green
4. `black leather biker jacket, zippered, minimal hardware` -- black only, also brown variant
5. `premium cotton hoodie, strings visible` -- in black, gray, navy, forest green, burgundy, white
6. `structured blazer with gold buttons` -- in black, navy, camel, maroon, white, hunter green
7. `fitted sleeveless tank top` -- in white, black, red, gray, olive, purple
8. `classic black tuxedo jacket with satin lapels, white dress shirt, black bow tie` -- black only, also midnight blue variant

### Accessories (isolated items, transparent bg)

**Hats:**
```
A [HAT TYPE] rendered floating on a solid black background, 3/4 angle from slightly above as it would sit on someone's head. Premium quality, detailed texture and stitching. Semi-stylized game art. [COLOR]. Clean edges, suitable for compositing. --ar 1:1
```
1. `flat-brim snapback cap` -- black, red, white, gold, custom "EV" logo variant
2. `classic felt fedora with ribbon band` -- black, charcoal, brown, cream
3. `knit beanie, slightly slouched` -- black, gray, navy, burgundy, cream
4. `ornate golden crown with gemstones, fit for royalty` -- gold with rubies (VIP EXCLUSIVE)

**Glasses:**
```
A pair of [GLASSES TYPE] rendered floating on a solid black background, straight-on angle. Premium quality, detailed frame and lens rendering. Semi-stylized game art. Clean edges. --ar 1:1
```
1. `classic aviator sunglasses with dark lenses and gold metal frames`
2. `oversized square designer sunglasses with thick black frames`
3. `round wire-frame spectacles with clear lenses, intellectual style`
4. `diamond-encrusted cat-eye sunglasses, crystals catching light, ultra luxury` (PREMIUM)

**Jewelry:**
```
A [JEWELRY TYPE] rendered on a solid black background, shown as it would appear worn. Premium metallic rendering with realistic light reflections. Semi-stylized game art. Clean edges. --ar 1:1
```
1. `simple gold Cuban link chain necklace, medium weight`
2. `heavy diamond-encrusted Cuban chain, iced out, blinding sparkle` (PREMIUM)
3. `luxury gold wristwatch with black face, visible on wrist`
4. `diamond-studded gold Rolex-style watch, iced out bezel` (PREMIUM)
5. `single gold hoop earring, medium size`
6. `diamond stud earring, brilliant white sparkle`

**Special Items:**
```
A [ITEM] rendered on a solid black background. Premium quality, semi-stylized game art. Detailed and atmospheric. Clean edges for compositing. --ar 1:1
```
1. `lit cigar with wisps of smoke curling upward, warm amber glow at the tip`
2. `premium over-ear headphones with gold accents, DJ style, around neck position`
3. `small minimalist face tattoo, a single teardrop below the left eye and a small star near the temple` (render as a face overlay)
4. `wide confident smile showing a single gold front tooth with subtle gleam`

---

## PART 4: EVERLIGHT VENTURES LOGO & APP ICON (Seedream)

### App Icon (1024x1024 for stores)

```
A premium app icon for a luxury casino game called "Everlight." The icon is a square with rounded corners (iOS style). The background is a rich gradient from deep black #0A0A0A at the edges to very dark charcoal #1A1A1A in the center, with a subtle radial gold spotlight glow behind the main element. In the center, a geometric monogram combining the letters E and V -- three horizontal gold bars of decreasing length stacked vertically connected by a vertical stroke on the left (forming the E), with two diagonal strokes converging to a right-side apex (forming the V). The monogram is rendered in metallic gold #D4AF37 with a subtle 3D bevel giving it a stamped/embossed quality. A very faint gold particle dust floats around the mark. Ultra clean, luxury, minimalist. No text on the icon. The feeling is "premium casino meets tech startup." --ar 1:1
```

### Profile Photo / Social Avatar (512x512)

```
A square social media profile image for the brand "Everlight Ventures." The geometric gold EV monogram logo (three horizontal bars forming an E, connected to a V shape) is embossed into a surface that looks like black Italian leather with visible grain texture. A single overhead spotlight illuminates the gold mark from above, creating a soft warm highlight and a subtle shadow beneath. The background fades to pure black at the edges. Extreme luxury feel -- like the cover of a Hermès box or a private members' club emblem. Photorealistic material rendering, cinematic lighting. No text. Square format. --ar 1:1
```

### Casino-Specific Logo (for in-game branding)

```
A luxury casino logo rendered in 3D gold metallic text reading "EVERLIGHT" in elegant serif typography with wide letter spacing. Below it, "CASINO" in smaller text, same style. The text appears to be solid gold with subtle reflections and light catching the edges. Behind the text, very subtle dark green felt texture barely visible. A faint golden spotlight from above. The overall look is like a sign above a high-end casino entrance. Black background. No other elements. Ultra premium, clean, authoritative. --ar 3:1
```

### Favicon / Small Icon (render large, will be shrunk)

```
A simple geometric mark on a solid black square background. Three horizontal gold lines of decreasing length stacked vertically, connected by a single vertical gold line on the left. Two diagonal gold lines extend from the top and bottom bars to meet at a point on the right, forming a V shape. Bold stroke weight, sharp corners, no curves. Gold color is warm metallic #D4AF37. Centered with generous padding. Flat vector style, extremely clean and legible at small sizes. Minimalist. --ar 1:1
```

---

## PART 5: PROMO / MARKETING VIDEO (Seedance 2.0)

### App Store Preview Trailer (15 seconds)

```
A cinematic casino game trailer. Opening shot: slow zoom into a dark luxury casino room, golden chandelier light illuminating a green felt blackjack table from above. Bokeh lights twinkle in the background. Cut to: a pair of playing cards sliding across the felt -- an Ace of Spades and King of Hearts, landing with a satisfying stop. Cut to: stacked casino chips in gold, black, and red being pushed forward by an elegant hand. Cut to: a close-up of the gold "EVERLIGHT" text glowing on the felt surface. Final shot: the geometric EV logo mark materializes in gold particles that swirl together and lock into place, centered on screen against black. Luxury casino atmosphere, warm golden lighting throughout, cinematic quality, slow motion moments, photorealistic. Dramatic orchestral music. --duration 15s --ar 9:16
```

---

## TIPS FOR BEST RESULTS

### Character Consistency (Critical)
- Generate the IDLE portrait first for each dealer
- Screenshot/export the best frame as a reference image
- Use that frame as `@image1` in ALL subsequent reaction clips for that dealer
- This is how you maintain the same face across multiple clips

### Avatar Component Compositing
- Generate all base elements at the same angle and lighting
- Use consistent "solid black background" for easy removal/compositing
- In Lovable, layer the components using absolute positioning and z-index
- Order (bottom to top): base skin → expression → hair → outfit → hat → glasses → jewelry → special

### File Naming Convention
```
dealers/aria_idle.mp4
dealers/aria_blackjack.mp4
dealers/aria_bust.mp4
dealers/aria_bigwin.mp4
dealers/aria_jackpot.mp4
dealers/marcus_idle.mp4
...etc

avatars/base/skin_01_fair.png
avatars/base/skin_02_light.png
...
avatars/hair/fade_black.png
avatars/hair/fade_brown.png
...
avatars/outfits/suit_black.png
avatars/accessories/hat_snapback_black.png
avatars/accessories/glasses_aviator.png
avatars/accessories/chain_gold.png
...

brand/ev_app_icon_1024.png
brand/ev_profile_512.png
brand/ev_casino_logo.png
brand/ev_favicon.png
```

### Upload to Supabase Storage
After generating, upload all assets to your `public-content` bucket:
```
public-content/
  dealers/          -- dealer video clips
  avatars/
    base/           -- skin tone bases
    hair/           -- hairstyle overlays
    outfits/        -- clothing items
    accessories/    -- hats, glasses, jewelry, specials
    expressions/    -- face expression overlays
  brand/            -- logos and icons
```

Base URL: `https://jdqqmsmwmbsnlnstyavl.supabase.co/storage/v1/object/public/public-content/`

### Recommended Generation Order
1. **App icon + profile photo** (brand identity first -- you need these immediately)
2. **4 dealer idle portraits** (the main visual impact of the game)
3. **Dealer reaction clips** (use idle frames as @image1 reference)
4. **8 skin tone bases** (foundation of avatar system)
5. **12 hairstyles × 2-3 colors each** (most visible customization)
6. **8 outfits × 2-3 colors each**
7. **Accessories** (hats, glasses, jewelry -- premium items last)
8. **Promo trailer** (after all game assets exist for reference)

Total assets: ~150-200 individual images/videos. Budget 2-3 sessions of focused generation.
