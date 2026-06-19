# ALLEY KINGZ -- MENU REDESIGN (Plain English)

**Problem:** the lobby is one boring vertical column of square buttons. It works, but it feels simple, not
premium or immersive, and it doesn't pull players toward the shop / pass / quests.

**Fix:** copy what every top game does -- a **persistent bottom tab bar** with **PLAY as the big center button**
(kept prominent + consistent, like you wanted), a **rotating hero banner** up top showing today's best deal /
season / event with a countdown, your **Alley Pass progress bar always visible**, **currency up top**, and
**red-dot badges** on the tabs when there's something to claim. The boring grid of extra buttons (Deck Lab,
World Map, Crates, Profile, Codex, Draw) becomes a tidy little icon row, out of the way but one tap away.

## Before vs After
- **Before:** PLAY, then a vertical wall of 11 identical squares. Static. Quiet.
- **After:** alive hub -- featured art banner + countdown on top, your pass climbing, a glowing PLAY pillar in
  the center, and a Clash-style bottom bar (Drip · Crew · PLAY · Pass · Hit List) with red dots pulling you in.

## Why it makes money + keeps people
- The **hero banner** puts your best cosmetic in their face daily (Fortnite's #1 trick).
- **Red dots** are the strongest pull in mobile games -- players tap to clear them, landing on quests/shop/crew.
- **Pass bar always visible** = "so close to the next tier" pressure.
- **Currency on top** = spend intent + one-tap to the shop.

## What ships now vs later
- **Now (no new art needed):** the whole layout + **fancy 3D gold buttons in pure CSS** (chunky, glowing,
  pressed states, the PLAY button breathes), the bottom tab bar, hero carousel, red-dots, animated feel.
- **Later (Seedance):** custom painted icon art for each tab + hero frames + faction crests -- I wrote the exact
  art prompts; they drop in once you send the Seedance login.

## Safe to build
Every existing button keeps its ID and wiring -- I'm re-parenting + restyling, not rewiring. PLAY behaves exactly
as today. Zero logic changes, pure layout/CSS. Verified in a real browser before it goes live.

## The one decision
**Approve the bottom-tab + hero-banner layout** (mockup in MENU_REDESIGN_SPEC.md)? On yes, I build the CSS/layout
now (real visual upgrade) and drop in the Seedance art when the login lands.
