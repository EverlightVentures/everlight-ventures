# Everlight Blackjack OS Audit 2026

## Bottom line

Everlight Blackjack is not one product yet. It is three overlapping systems:

1. A local Django blackjack app used inside `hive_dashboard`.
2. A much larger Supabase edge-function backend that looks closer to the real production game.
3. A Lovable/public-site layer that sells and presents the game.

That split is why the product feels powerful on paper but unreliable in practice. The missing piece is not more features. It is one control plane, one source of truth for balances and purchases, and one honest ops view that tells you whether the game is live, safe, and monetizable.

## What I fixed now

### Django game integrity

- Duplicate settlement is now blocked at the server.
- Result submissions now validate card payloads, recompute hand values, and reject mismatched outcomes.
- The broken `double` path is disabled in the frontend because it was changing the client bet without a matching server-side deduction.

This does not make the Django game fully server-authoritative yet, but it closes the easiest abuse path immediately.

### Business OS integration

- Blackjack now has a real `blackjack_arcade` revenue stream in Business OS.
- The CEO board now shows a blackjack watchtower with:
  - players and activity
  - wagers and chip delta
  - ad-reward activity
  - VIP count
  - Stripe package readiness
  - integrity rejection count
  - open alerts

### Supabase purchase path

- The gem verification function was writing to the wrong place.
- The arcade purchase verifier and blackjack API had chip-balance reads that did not pin `currency_name`, which can break once both chips and gems exist for the same player.
- Those ledger reads are now aligned to the `game_currencies` model used by the main blackjack backend.

## What is still structurally weak

### The Django blackjack table is still not fully server-authoritative

It now validates what the client submits, but the client still authors the hand sequence. A real money-grade social casino backend should own:

- shoe/deck state
- each hit/stand/double/surrender action
- final settlement
- replayable audit log

Until that exists, the Django version should be treated as a controlled product surface, not the final authority.

### The product still has split brains

- Django tracks local chips, gems, cosmetics, and sessions.
- Supabase edge functions track player accounts, currencies, tables, VIP, missions, and purchases.
- Lovable presents the public experience.

That is workable only if one layer is clearly primary. Right now the real long-term primary should be Supabase plus edge functions, with Django acting as private ops and Business OS.

### Revenue attribution is still incomplete

The game can sell:

- chip packs
- gem packs
- VIP/game passes
- cosmetics

But the control plane still needs one reliable revenue ledger and one dashboard surface for:

- purchases today
- MRR
- payer conversion
- active VIP
- failed fulfillment
- top products

## Recommended operating shape

### Use Supabase as the game system of record

- balances
- purchases
- VIP and passes
- missions and rewards
- player sessions
- leaderboards

### Use Business OS as the executive layer

- stream status
- incidents
- monetization readiness
- traffic and engagement
- public proof surfaces

### Use Lovable as the public shell

- `/arcade`
- `/arcade/blackjack`
- pricing and pack presentation
- AI coach marketing
- public status honesty

## Highest-leverage next moves

1. Move from client-authored hands to a server-authored action log for the live blackjack economy.
2. Add a purchase and fulfillment board that reads `arcade_purchases`, `gem_purchases`, VIP status, and failed verification events from Supabase.
3. Make `/arcade` and `/arcade/blackjack` present the real product truth:
   - AI strategy coach
   - social casino only, no cash-out
   - live packs and VIP
   - operational honesty when systems are degraded

## Revenue view

The blackjack product can be one of the cleanest cash generators in the stack because it has:

- repeat usage
- natural VIP logic
- high-margin digital goods
- ad-supported free play
- strong cross-sell potential with the rest of the arcade

But that only works if the economy and fulfillment are trustworthy. Monetization without ledger integrity is fake leverage.
