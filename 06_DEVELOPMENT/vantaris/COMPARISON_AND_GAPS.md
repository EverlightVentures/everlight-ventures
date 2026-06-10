# Vantaris vs Everlight -- Full Comparison + Gaps

## VERDICT

The NEW Vantaris Next.js game has BETTER game mechanics (split, insurance,
side bets, lightning, card skins, table lobby) and BETTER architecture
(modular, typed, testable, modern React).

The OLD Everlight game has BETTER infrastructure connections (Supabase,
Stripe, Django, auth, leaderboards, hand history) and a MORE REFINED
3D scene (iterated on, bot seat projection working).

Neither is complete. The path forward: wire Vantaris frontend to the
existing Everlight backend infrastructure.

---

## MISSING LIBRARIES TO INSTALL

### Immediate Impact (install now)
1. gsap -- cinematic animation timelines (card deals, chip tosses)
2. @lottiefiles/react-lottie-player -- pre-made casino animations
3. tone -- procedural audio synthesis (living sound design)

### Next Phase (install when building multiplayer)
4. colyseus.js -- multiplayer game server client
5. pixi.js -- 2D WebGL renderer for game layer performance

### Visual Polish (enable in existing packages)
6. SSR effect in @react-three/postprocessing (table reflections)
7. N8AO effect in @react-three/postprocessing (chip stack depth)
8. threejs-holographic-material (card rarity visual effects)

### Future
9. onnxruntime-web -- ML models in browser
10. WebGPURenderer -- quality tier for modern hardware

---

## INFRASTRUCTURE TO WIRE

### Supabase (already have the project)
- Project: jdqqmsmwmbsnlnstyavl.supabase.co
- Edge functions already deployed: dealer-speak, create-checkout, verify-checkout
- Need to: add Supabase client to Next.js, wire auth, connect edge functions

### Django Backend (already running on Oracle)
- 14 blackjack API endpoints at /blackjack/api/*
- Need to: proxy API calls from Next.js to Django on Oracle
- Or: rebuild game API as Next.js API routes + Supabase direct

### Stripe (already have account)
- 4 gem packages with live Stripe price IDs in catalog.py
- Need to: wire create-checkout edge function to gem store UI

### Blinko RAG (already running)
- 458 notes at http://e5-mother:1111
- Need to: use for AI dealer knowledge, player support

### Deploy
- everlightventures.io on Cloudflare Pages via GitHub
- Vantaris needs its own domain (vantaris.casino or similar)
- Or: deploy as /arcade/blackjack-v2 on everlightventures.io first

---

## GAME FEATURES COMPARISON

| Feature | Everlight (OLD) | Vantaris (NEW) |
|---------|----------------|---------------|
| Split | Stub | Engine ready |
| Insurance | None | Engine ready |
| Side Bets (PP/21+3/LL) | Stub | Engine ready |
| Lightning Multipliers | None | Engine ready |
| Six Card Charlie | None | Engine ready |
| Multi-hand | None | Designed |
| Card Skins (7 decks) | None | Built |
| Card Rarity (5 tiers) | None | Built |
| Card XP Leveling | None | Built |
| Gambit Energy Effect | None | Designed |
| Table Lobby | None | Built (7 tables) |
| Table Variants | None | 5 variants (engine) |
| VIP Room | None | Designed |
| Seat Selection | None | Designed |
| Provably Fair | None | Engine exists |
| Sweeps Coins (SC) | Model exists | Engine + UI built |
| Crypto Deposits | None | Geo-routing + CoinsPaid built |
| Server-Auth Game | Yes (Django) | No (client-only) |
| Stripe Payments | Yes (working) | UI only |
| Auth | Django sessions | None |
| Leaderboard Data | Server-fetched | Mock data |
| Hand History | Server-stored | None |
| ElevenLabs Voice | Working | Same code, not tested |
| Procedural Jazz | Working | Same code |
| 3D Scene | Refined (iterated) | New (postprocessing added) |
| Bot 3D Projection | Working | Not working |
| Cosmetics Applied | Not applied to cards | Skin system built |
| Table Felts Applied | Not applied to 3D | Config exists |
| Framework | Vanilla JS (1 file) | Next.js + React + TS (15 files) |
| Postprocessing | None | Bloom + Vignette + ChromAb |
| Casino Chips | CSS buttons | SVG with edge notches |

---

## ACTION PLAN

### Phase 1: Wire the Backend (makes Vantaris functional)
1. Install Supabase client (@supabase/supabase-js)
2. Add auth (Supabase Auth, not Django)
3. Connect dealer-speak edge function (already works)
4. Connect Stripe via create-checkout edge function
5. Build Next.js API routes for game logic (or proxy to Django)
6. Store hand history + leaderboards in Supabase

### Phase 2: Install Missing Libraries (makes Vantaris premium)
7. Install GSAP for cinematic card deal sequences
8. Install Lottie for pre-made casino animations
9. Install Tone.js for procedural audio
10. Enable SSR + N8AO postprocessing effects

### Phase 3: Deploy (makes Vantaris live)
11. Register vantaris.casino domain
12. Deploy to Cloudflare Pages (or Oracle + Vercel)
13. Wire custom domain
14. Launch

### Phase 4: Multiplayer (makes Vantaris social)
15. Install Colyseus on Oracle E5
16. Build multiplayer rooms (seat selection, shared dealer)
17. Real-time player actions visible to others
18. Chat + emotes

This is the complete gap analysis.
