# Everlight Blackjack - Seedance AI Art Brief
**Budget:** ~1,300 credits | Images: 10-20 credits each | Videos: 300 credits each

---

## STRATEGY: Credit-First Priority Order

### TIER 1 - MUST HAVE (spend here first)
These directly replace the emoji placeholders visible every session.

| Asset | Type | Est. Cost | Description for Prompt |
|-------|------|-----------|------------------------|
| **Dealer Character** | Image | 15 | A sophisticated human casino dealer in a crisp black tuxedo with gold cufflinks, standing behind a blackjack table. Dark, moody casino lighting from above. Cinematic portrait style, 3/4 view, confident expression, holding a playing card. Realistic render. |
| **Dealer Idle Animation** | Video | 300 | Same dealer character, slowly shuffling cards at a green felt blackjack table, chandelier light overhead. Loop-ready 3-4 second clip. Dark luxury casino atmosphere. Photorealistic. |
| **Table Felt Texture** | Image | 10 | Top-down view of a dark green casino felt blackjack table. Gold trim ring at the edges. Subtle "EVERLIGHT BLACKJACK" embossed text in the center. Realistic fabric texture with subtle embossing. |
| **Chip Stack - Gold** | Image | 10 | A tall stack of gold casino chips on a dark background. Metallic sheen, each chip has a subtle "EV" logo. Studio product shot style, dramatic side lighting. |
| **Playing Card Back Design** | Image | 10 | Luxury card back design: deep navy background, intricate gold filigree pattern in the corners, small diamond motif in the center, Everlight "E" monogram. High-end playing card aesthetic. |

**Tier 1 Subtotal: ~345 credits**

---

### TIER 2 - HIGH IMPACT (unlock economy)

| Asset | Type | Est. Cost | Description for Prompt |
|-------|------|-----------|------------------------|
| **Gold Tuxedo Avatar** | Image | 15 | Full-body silhouette of a person wearing a shimmering gold tuxedo jacket with black lapels, standing confidently. Transparent/isolated background. Casino gala lighting. Stylized but realistic, art-deco influenced. |
| **Neon Synthwave Suit Avatar** | Image | 15 | Full-body figure in a black suit with electric neon-pink and cyan glowing trim lines, like a Tron-inspired synthwave outfit. Dark background with subtle neon reflections. Futuristic casino vibe. |
| **Fire Aura Effect** | Image | 12 | A circular ring of stylized fire/ember effect, viewed from slightly above. Transparent background (PNG). Warm orange-red, casino-dark atmosphere. Used as player aura overlay. |
| **Golden Glow Aura** | Image | 12 | A soft golden radiant glow halo effect, circular, transparent background. Warm gold tone. Elegant, not harsh. Used as player prestige aura. |
| **Diamond Blazer Avatar** | Image | 15 | Full-body figure in a white blazer covered in glittering synthetic diamonds/crystals, catching the light. Dark dramatic background. High fashion, casino gala style. |

**Tier 2 Subtotal: ~69 credits**

---

### TIER 3 - TABLE ATMOSPHERE (make the game feel live)

| Asset | Type | Est. Cost | Description for Prompt |
|-------|------|-----------|------------------------|
| **Casino Background Panorama** | Image | 15 | Wide panoramic interior of a luxury underground casino. Dark wood paneling, crystal chandeliers, glowing neon accents in purple and gold, crowded with silhouetted figures. Film noir meets art-deco. |
| **Jackpot / Win Celebration** | Video | 300 | Explosion of gold coins, confetti, and light beams erupting from center of screen. 3-4 second burst, celebratory. Dark background so it overlays cleanly. Photorealistic particles. |
| **Bot Player - Vegas Vic** | Image | 12 | Stylized casino character: older gentleman, gray slicked-back hair, white shirt with suspenders, smug grin, holding a fan of cards. Illustrated but detailed. Side-table seat pose. |
| **Bot Player - Miss Fortune** | Image | 12 | Stylized casino character: confident woman in a red satin dress, dark sunglasses, large diamond earrings, one eyebrow raised. Holding a glass of champagne. Seated at blackjack table edge. |
| **Bot Player - The Shark** | Image | 12 | Lean man in an all-black suit, no tie, sharp features, expressionless gaze. Poker face energy. Seated at a blackjack table, one hand on chip stack. Dramatic side lighting. |

**Tier 3 Subtotal: ~351 credits**

---

### TIER 4 - COSMETIC SHOP ITEMS (marketplace visuals)

| Asset | Type | Est. Cost | Description |
|-------|------|-----------|-------------|
| **Dragon Card Back** | Image | 10 | Playing card back with an embossed red and black eastern dragon coiled around a central diamond. Dark navy base. Rich embossed look. |
| **Gold Foil Card Back** | Image | 10 | Playing card back in shimmering gold foil finish. Minimal design, luxury feel, subtle geometric pattern. Very high-end. |
| **Crimson Felt Table** | Image | 10 | Top-down felt table in deep crimson/wine red with gold trim edges. Same layout as default but red. |
| **Midnight Blue Felt Table** | Image | 10 | Top-down felt table in midnight navy blue with gold embossed scrollwork around the edges. |
| **Royal Robe Avatar** | Image | 15 | Full-body royal figure in flowing purple and gold robes, crown motif on the chest, casino environment. Regal, imposing. |
| **Legend Drip Avatar** | Image | 15 | Full-body figure in an otherworldly outfit: black bodysuit with orange flame-like energy tendrils, glowing eyes, levitating slightly. Legend-tier energy. |

**Tier 4 Subtotal: ~70 credits**

---

## TOTAL ESTIMATED: ~835 credits (leaves ~465 buffer)

---

## RECOMMENDED MODELS IN SEEDANCE

| Use Case | Model |
|----------|-------|
| Characters (dealer, avatars) | Seedance Video 1.0 Pro (video) or Stable Diffusion XL (image) |
| Table textures, card backs | FLUX.1 Pro - best for detailed textures |
| Atmosphere/backgrounds | DALL-E 3 style prompts |
| Particle/aura effects | FLUX.1 Dev with transparent background prompt |
| Video clips (dealer, celebrate) | Seedance Video 1.0 (300 credits/video) |

---

## PROMPT BEST PRACTICES

### Characters
Always include:
- `cinematic lighting, casino atmosphere, dark background`
- `full body, isolated figure` (for avatars needing transparent BG)
- `ultra-detailed, photorealistic, 4K`
- Art style: `art-deco luxury, Everlight casino brand`

### Videos
- Keep to **3-4 seconds** to stay within one credit budget
- Specify `loop-ready` if it is for ambient animation
- `seamless loop` for background/atmosphere clips

### Textures
- Always say `top-down view, flat lay` for table textures
- Request `seamless tiling texture` for felt/patterns
- `transparent background PNG` for aura/effect overlays

---

## INTEGRATION GUIDE

1. **Save all images** to: `01_BUSINESSES/Everlight_Ventures/Everlight_Gaming/Blackjack/assets/`
2. **Dealer idle video**: Host as a `<video>` element overlaid on the 3D scene (replace dealer area placeholder)
3. **Avatar images**: Use as `<img>` or Three.js texture maps on the seat stand discs
4. **Aura images**: Load as Three.js `THREE.TextureLoader` and apply to sprite quads at seat positions
5. **Card backs**: Apply to Three.js card geometry material in `renderHands()`
6. **Background panorama**: Use as `scene.background = new THREE.TextureLoader().load(url)` replacing solid color

---

## DO NOT SPEND ON YET
- Full 3D animated dealer model (needs Unity/Unreal)
- NFT-style generative art for marketplace (Phase 2)
- Promotional video/trailer (Phase 2)
- Private table artwork (feature not implemented yet)

---

*Generated by Everlight Hive Mind - March 2026*
