# AUTH SEPARATION DOCTRINE -- Alley Kingz vs Vantaris Casino
**Operator hard law (2026-06-11). Read before touching ANY login, OAuth, account, or profile code.**

## THE LAW
There are TWO different games, TWO different logins, TWO different accounts. They have
nothing to do with each other.

| | Alley Kingz | Vantaris Casino / Everlight |
|---|---|---|
| Domain | alleykingz.online | everlightventures.io |
| Login lands on | alleykingz.online (the game) | everlightventures.io (the casino) |
| Player profile | AK profile ONLY: `ak_player_saves`, `ak_card_inventory`, `ak_*` tables | Casino profile ONLY: its own tables |
| Branding on consent + UI | Alley Kingz | Vantaris / Everlight |
| Money rail | AK Stripe products (`ak-gems-*`), in-game value only | Casino's own rail |

- A login started on a domain returns to THAT domain and loads THAT product's profile. Never
  route a player from one product's login into the other product. Ever.
- The same human may play both games. Fine. The accounts, routing, and profile surfaces stay
  per-product. No shared profile UI, no shared wallet, no shared money rail.
- This is WHY alleykingz.online is a separate domain. Respect the wall.

## WHY THIS DOC EXISTS (the incident)
2026-06-11: AK Google sign-in routed the operator to everlightventures.io. Cause: shared
Supabase project auth -- `site_url` (the fallback) is everlightventures.io, and the AK
domains were allowlisted as EXACT urls while Supabase matches GLOB patterns, so every
redirect fell back to the casino domain. Fix: `https://alleykingz.online/**` +
`https://alley-kingz.pages.dev/**` wildcard entries.

## CURRENT STATE -- SPLIT COMPLETE (2026-06-11)
The END STATE below is LIVE: AK runs on Supabase project `mfghdobptredxxhbjwyz` with the
operator's dedicated "Alley Kingz" Google OAuth client. The notes below describe the
prior interim setup for history.

### (historical) interim, shared project
- Both products currently share Supabase project `jdqqmsmwmbsnlnstyavl` for auth + DB.
- Separation is enforced by: wildcard redirects per domain, `redirectTo = location.origin +
  location.pathname` in `game/ak_account.js`, and a hard table namespace (`ak_*` = game only,
  RLS owner-scoped). The casino never reads `ak_*`; the game never reads casino tables.

## END STATE (the split, per the brand/entity separation roadmap)
1. Alley Kingz gets its OWN Supabase project (own auth, own DB, own keys).
2. Alley Kingz gets its OWN Google OAuth client in Google Cloud Console, consent screen
   branded "Alley Kingz" (operator creates; see ANSWER SHEET below when ready).
3. `ak_account.js` consts flip to the new project URL + anon key; migrations
   (20260607 economy + seed, 20260610 products, 20260611 saves) re-apply on the new project;
   `alley-kingz-shop` + `create-checkout` (AK slugs) deploy there with the same secrets.
4. Casino keeps the old project untouched.

## RULES FOR ANY NEW PRODUCT DOMAIN
1. Allowlist `https://<domain>/**` (GLOB, not exact) in that product's auth config BEFORE the
   sign-in button ships.
2. `redirectTo` = the current product origin. Never hardcode another product's URL.
3. Verify the full round-trip (sign in -> consent -> back) lands on the product domain.
4. Player state goes in that product's own table namespace with owner-scoped RLS.
5. No corporate Everlight branding on player-facing surfaces unless the operator opts in.
