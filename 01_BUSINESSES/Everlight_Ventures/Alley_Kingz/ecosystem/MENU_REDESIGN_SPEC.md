# ALLEY KINGZ -- MENU REDESIGN SPEC (build-ready)
**Goal: kill the boring vertical grid. Make the lobby a premium, immersive hub that routes players to
the money + retention surfaces -- the way Clash Royale / Fortnite / CoD Mobile / Mobile Legends do it.**
Date: 2026-06-14 | Vanilla-JS + CSS, no framework. PLAY stays prominent + consistent.

## WHAT THE WINNERS DO (researched patterns -> AK application)
| Game | Pattern | Why it works | AK application |
|---|---|---|---|
| Clash Royale | Persistent **bottom tab bar**; **Battle** button is the fixed center anchor | One-thumb nav; the money tabs (Shop) are always one tap away; Battle never moves | Bottom tab bar w/ **PLAY** as the big center pillar |
| Clash Royale | **Red-dot badges** on tabs (free chest, shop deal, donate request) | The single strongest pull -- players tap to clear dots | Red-dots on Hit List (claimable), Drip (new Drop), Crew (donation requests) |
| Fortnite | **Item Shop as a front door** + rotating **featured carousel** | Puts the best cosmetic in your face daily; FOMO countdown | **Hero banner** up top: rotating The-Drop deal / season / event w/ countdown |
| Fortnite / CoD | **Battle-pass progress bar on the home screen** | Constant "so close to the next tier" pull | Always-visible **Alley Pass strip** under the hero |
| CoD Mobile | **Top currency header** (taps open store) + event tiles | Currency visible = spend intent; quick store access | Top-right **Gems / Gold** chips, tap -> Shop |
| Mobile Legends | **Side rail of event/shop shortcuts** + daily login | Many surfaces without a wall of buttons | Secondary icons (Deck Lab, Crates, Profile, Codex, Draw) in a tidy **top icon row**, not the main grid |
| Mobile Legends | **Animated background** + spotlight | Feels alive/premium vs a static menu | Subtle parallax city backdrop + a spotlighted featured card/skin |
| PUBG / all | **Zone the screen** (don't clutter) | Each area owns one job; attention is directed | 4 clear zones: header / hero / PLAY / tab bar |

## THE NEW LAYOUT (4 zones)
```
+------------------------------------------------+
|  AK logo        [☁ saved]      💎 1,200  💰 4.2k |   ZONE 1: top bar (brand + auth + currency, tap->shop)
+------------------------------------------------+
|   [  HERO / FEATURED BANNER -- rotates  ]  •••  |   ZONE 2: hero carousel (The Drop deal / season /
|   "GILDED SKIN -- 30% off -- ends 4h"          |            event / new card). Big art, FOMO countdown.
|   ALLEY PASS  Tier 7 ▓▓▓▓▓▓░░░  +120 XP to T8   |            + Pass progress strip pinned under it.
+------------------------------------------------+
|                                                |
|              ( cyberpunk city bg )             |   ZONE 3: stage -- the spotlight + the PLAY pillar.
|              +----------------+                |
|              |   ▶  PLAY NOW  |  <- big, gold,  |
|              +----------------+     pulsing     |
|                                                |
+------------------------------------------------+
| [🛍 DRIP] [🛡 CREW]  [ ▶ PLAY ] [🎖 PASS] [🎯 HIT]|   ZONE 4: persistent bottom tab bar.
+------------------------------------------------+      Center PLAY = same action as the pillar.
```
- **Bottom tab bar (5):** DRIP/Shop | CREW | **PLAY (center, raised, gold)** | ALLEY PASS | HIT LIST.
  These are the 5 live-ops surfaces (money + social + progression). PLAY is center + biggest (operator: keep it prominent + consistent).
- **Top icon row (secondary):** Deck Lab, World Map, Crates, Lucky Draw, Profile, Codex -- a compact horizontal
  scroll of small round icons under the top bar, so they're available but don't dominate.
- **Hero carousel:** 3-4 rotating slides (auto + swipe): featured Drop deal (countdown), current season, a live
  event, a spotlighted new card/skin. Each slide is a tap-through to that surface.
- **Pass strip:** thin always-visible Alley Pass progress bar (tier + XP-to-next) pinned under the hero -> taps to the Pass.

## FANCY BUTTONS (CSS recipe -- real polish now, no external art needed)
```css
.ak-btn3d{
  position:relative; border:0; border-radius:14px; cursor:pointer; color:#1a1405; font-weight:900;
  background:linear-gradient(180deg,#ffe39a 0%, #f0c14b 45%, #cf9b22 100%);   /* gold face */
  box-shadow: 0 4px 0 #8a6612, 0 8px 18px rgba(0,0,0,.45),                     /* chunky 3D base */
              inset 0 1px 0 rgba(255,255,255,.7), inset 0 -3px 6px rgba(0,0,0,.25);
}
.ak-btn3d:active{ transform:translateY(3px); box-shadow:0 1px 0 #8a6612, 0 3px 8px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.6); }
.ak-btn3d::before{ content:""; position:absolute; inset:0; border-radius:14px; box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.35); }
/* faction-accent variant: swap the gold stops for the faction palette; tab icons get a soft inner glow */
.ak-play{ animation: akpulse 2.2s ease-in-out infinite; }                      /* PLAY breathes */
@keyframes akpulse{ 0%,100%{ filter:drop-shadow(0 0 0 rgba(240,193,75,0)); } 50%{ filter:drop-shadow(0 0 14px rgba(240,193,75,.55)); } }
```
Tab icons: round, dark glassy (`rgba(20,20,28,.85)` + 1px gold ring), active tab gets a gold underline + lift.
Hero card: full-bleed art, gradient scrim bottom for text legibility, gold "ends in HH:MM" pill.

## NOTIFICATION RED-DOTS (the top traffic driver) -- triggers per tab
- **HIT LIST**: any quest `claimable` (progress >= target, unclaimed) -> red dot w/ count.
- **DRIP**: a Drop item the player doesn't own rotated in today (once/day) OR unclaimed grant -> dot.
- **CREW**: open donation request the player can fill, or a join request (if leader/co) -> dot.
- **ALLEY PASS**: a tier reward reached + unclaimed -> dot.
- Implement: a small `akBadge(tabId, n)` that adds a `.ak-dot` span; each module reports its count on load
  (reuse the get calls already made: ak-quests get, ak-cosmetics get, ak-crew mine, ak-pass get).

## SEEDANCE BUTTON-ART BRIEF (generate later; CSS art ships now)
Style for ALL: gritty cyberpunk dog-gang, TV-MA, neon-on-concrete, faction-color accent, icon-on-transparent, 256x256.
| Surface | Prompt | Size |
|---|---|---|
| PLAY pillar bg | "neon alley gate, two glowing rails converging, gold rim light, no text" | 1024x512 |
| Drip/Shop tab | "spray-can + gold dog-tag crown icon, neon outline" | 256x256 |
| Crew tab | "riot shield with a dog-paw sigil, chain-link texture" | 256x256 |
| Pass tab | "gold medal / dog-bone ribbon, season banner" | 256x256 |
| Hit List tab | "crosshair over a hit-list clipboard, red accent" | 256x256 |
| Hero frame | "torn neon poster frame, gold corners, grime" | 1200x420 |
| Faction crests x4 | "Boneguard skull-bone / Zoomie speed-bolt / Leashbreak broken-chain / K9 circuit-paw, each in faction color" | 512x512 |

## BUILD PLAN (vanilla, incremental, low-risk)
1. Add `#ak-topbar` (brand + auth chip moved here + currency chips) and `#ak-tabbar` (fixed bottom) to `#startscreen`.
2. Replace `.mode-grid` with: hero carousel `#ak-hero` + pass strip + the centered PLAY pillar; move the 6 secondary
   tiles into a compact `#ak-iconrow`. Keep all existing button IDs (`#playbtn`, `#shopbtn`, `#crewbtn`, `#passbtn`,
   `#questsbtn`, `#dripbtn`, etc.) so all existing wiring + the self-mounting modules keep working -- we only
   re-parent + restyle them. ZERO logic changes, pure layout/CSS + the badge helper.
3. Add the `.ak-btn3d` styles + tab-bar CSS + hero carousel JS (auto-rotate + swipe) + `akBadge` red-dots.
4. Keep PLAY NOW's behavior exactly (routes to World Map / resume). Tab-bar center PLAY calls the same handler.
5. Verify in a real browser (lobby renders, all tiles still reachable, PLAY works, no JS errors).
