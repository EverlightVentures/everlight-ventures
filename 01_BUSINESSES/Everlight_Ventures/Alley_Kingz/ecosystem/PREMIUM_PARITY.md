# ALLEY KINGZ -- PREMIUM PARITY WITH everlightventures.io
**Goal: make the game FEEL as premium as the website (the blackjack/wholesale Seedance menus).**
Date: 2026-06-14

## COMPARE & CONTRAST -- the quality gaps I found
Source of truth = the live site's design system (`06_DEVELOPMENT/vantaris/src/styles/design-system.css`
+ `content_tools/report_template.py`).

| Dimension | everlightventures.io (premium) | Game lobby (before) | Fix shipped |
|---|---|---|---|
| **Gold** | gradient `#c9a84c -> #e8c55a -> #c9a84c` + gold-glow | flat `#f0c14b` | adopted the exact brand gold gradient |
| **Typography** | Cinzel + Playfair (luxury serif) headlines, Inter body | system sans everywhere | loaded Cinzel/Playfair/Inter; brand title in Cinzel, hero headings Playfair, body Inter |
| **Surfaces** | glass-morphism (backdrop-blur 16-24px), `#0A0A0A/#1A1A1A`, gold borders | flat dark panels | top bar / hero / pass strip / tab bar now glass (backdrop-blur + gold borders) |
| **Depth/glow** | gold glow + soft shadows, radius 16-24 | hard flat shadows | gold-glow + brand radii (18-24) |
| **Motion** | gsap/framer fades, glow pulse | minimal | brand gold-glow PULSE on PLAY, hero crossfade carousel |
| **Background** | deep radial gradient | solid | radial `#15151f -> #070709` lobby backdrop |
| **Custom art** | **Seedance-painted** menu cards (blackjack/wholesale) | emoji + CSS | CSS art now; **Seedance art = next, brief below** |

## WHAT SHIPPED NOW (no new art needed -- pure CSS, matches the brand)
- The redesigned bottom-tab + hero lobby, re-skinned to the **exact** Everlight brand: gold gradient,
  Cinzel/Playfair/Inter, glass panels, gold-glow pulse on PLAY, premium radial background.
- This closes most of the "feels cheap" gap through **typography + color + glass + motion** -- the same levers
  that make the website feel premium -- WITHOUT waiting on art.

## WHAT NEEDS SEEDANCE (the last 20% -- custom painted art, gated on your login)
The website's premium edge is its **Seedance menu-card art**. Same play for the game. Brief (gritty cyberpunk
dog-gang, TV-MA, faction colors, on the `#0A0A0A` brand frame, gold accents):

| Surface | Prompt | Size |
|---|---|---|
| Hero banner frames (x3: Drop / Season / Crew) | "torn neon poster, gold corner filigree, grime, [theme] backdrop, no text" | 1200x420 |
| PLAY pillar backdrop | "neon alley gate, gold rim light, converging rails, depth" | 1024x512 |
| Tab icons (Drip/Crew/Pass/Hit) | "[spray-crown / riot-shield-paw / gold-medal-bone / crosshair-clipboard], neon line-art on dark, gold accent" | 256x256 |
| Secondary icons (Deck/Shop/Map/Draw/Crates/Profile/Codex) | matching neon line-art icon set, gold accent | 256x256 |
| Faction crests (x4) | "Boneguard skull-bone / Zoomie speed-bolt / Leashbreak broken-chain / K9 circuit-paw, each in faction color, embossed" | 512x512 |

**On your Seedance login I will:** generate this set in the brand style, drop the hero/icon art into the lobby
(swap the CSS gradients for painted frames + replace emoji with painted icons), and route any premium card/skin
art into the gem-priced tier per `PRICING_STRATEGY.md`. The whole game then matches the website's premium vibe.

## STILL TODO for full parity (after art)
- Apply the same brand tokens to the in-panel screens (Crew/Pass/Hit/Drip currently use the older `#f0c14b`) --
  a quick token sweep so the whole app is consistent, not just the lobby.
