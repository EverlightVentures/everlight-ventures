# LOVABLE BLACKJACK BUSINESS OS PROMPT

Paste this into the Everlight Lovable project to update `/arcade` and `/arcade/blackjack` so the public site reflects the real product and operating system.

---

Update the Everlight Arcade experience so `/arcade` and `/arcade/blackjack` feel like one premium, profitable system tied into Everlight Ventures Business OS.

## Brand and positioning

- Product: Everlight Blackjack
- Parent brand: Everlight Ventures
- Model: social casino only -- entertainment currency, no cash-out, no redeemable real-world value
- Differentiator: AI strategy coach + premium arcade presentation + honest live ops posture

## Design direction

- Keep the dark luxury / neon arcade feel already established for Everlight.
- `/arcade` should feel like a premium game hub.
- `/arcade/blackjack` should feel like a live table product, not a generic landing page.
- Use bold contrast, deliberate spacing, and premium motion.

## What to build

### `/arcade`

- Hero: "Two games. One account. One progression machine."
- Position the arcade as a digital product business, not just a game menu.
- Show:
  - unified player account
  - shared progression
  - VIP and passes
  - leaderboards
  - premium currency
  - AI-powered coaching
- Add a compact "System status" section that says the arcade is part of the Everlight operating system and surfaces live status honestly if data is stale or degraded.

### `/arcade/blackjack`

- Hero copy should position the game as:
  - free to play
  - AI-assisted
  - social casino only
  - built for repeat play and skill improvement
- Add sections for:
  - AI Strategy Coach
  - VIP / Game Pass benefits
  - Gem and Chip packs
  - Cosmetics / table identity
  - Daily rewards and progression
  - Social casino disclaimer
  - Operational honesty / live status

## Product truth to reflect

- The game has AI coaching, profiles, rewards, VIP logic, and purchasable packs.
- The backend is Supabase plus edge functions.
- Stripe is the payment rail.
- Business OS tracks product and system status.
- If a feature is not fully live, say so clearly instead of pretending.

## Backend hooks to use

- `blackjack-api`
- `create-checkout`
- `verify-gem-purchase`
- `verify-arcade-purchase`

Use the existing Supabase integration already connected to the site. Do not create duplicate storage or fake data models.

## Commercial goals

- Increase conversion into:
  - chip packs
  - gem packs
  - VIP / game passes
- Make the AI coach feel like the moat.
- Make the game feel premium enough that spending money makes sense.
- Keep the experience honest and legally clean: virtual currency only, no redemption language.

## UX rules

- No fake jackpot or fake revenue claims.
- No misleading "win real money" language.
- Add clear purchase CTAs, but do not make the page feel cheap or spammy.
- Mobile-first.
- Keep the page premium and intentional.

## Final requirement

The updated public copy must match the real operating model:

- social casino
- Stripe-backed packs
- Supabase-backed player state
- AI coach moat
- Business OS status visibility

Do not market the product as if it already has features that are still only partially wired.
