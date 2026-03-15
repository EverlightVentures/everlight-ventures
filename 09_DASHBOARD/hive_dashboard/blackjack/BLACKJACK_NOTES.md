# Everlight Blackjack - Implementation Notes

## URL
`/blackjack/` (registered in Django hive_dashboard)

## Auth Fixes
- Email/password accounts: working, session-persisted via django.contrib.auth
- Google/Facebook OAuth: redirects to `/accounts/google/login/` (requires django-allauth)
  - Install: `pip install django-allauth`
  - Add to INSTALLED_APPS: `allauth`, `allauth.account`, `allauth.socialaccount`, `allauth.socialaccount.providers.google`, `allauth.socialaccount.providers.facebook`
  - Add `path('accounts/', include('allauth.urls'))` to urls.py
  - Configure Google/Facebook OAuth credentials in Django admin > Social Applications
  - The "coming soon" message goes away once allauth is wired up

## Account Persistence Fix
- Root cause was likely no Django session middleware or missing `SESSION_ENGINE` config
- Now uses `django.contrib.sessions` (already in INSTALLED_APPS)
- Sessions stored in DB by default - persist across browser refreshes
- CSRF token is included in all API calls from the frontend

## Ad Reward System
- Server-side enforced: `PlayerProfile.ad_refills_today` + `ad_refill_date`
- 100 chips per ad, max 10/day per account, resets at midnight
- Replace `GOOGLE_ADS_CLIENT` and `GOOGLE_ADS_SLOT_REWARD` in settings.py with real AdSense IDs
- For rewarded ads: integrate Google AdSense Rewarded Ad Units (available for Web)

## Pricing Strategy (Optimized)
### Chip Funnel (Free)
- 1,000 chips on signup (low friction onboarding)
- 100 chips/ad refill, 10x/day (drives daily active users and ad revenue)
- Chips earned via gameplay (win payouts)

### Gem Monetization (Premium)
- $0.99 = 100 gems (impulse buy, low barrier)
- $4.99 = 600 gems (5x value vs starter - conversion sweet spot)
- $9.99 = 1,600 gems (most popular tier, best margin)
- $24.99 = 4,000 gems (whale tier)
- $49.99 = 10,000 gems (high roller)

### Cosmetics Pricing Rationale
- Common (chips only): 500-2,000 chips - keep F2P players engaged
- Rare: 3,000-15,000 chips OR 30-75 gems - dual currency drives choice
- Epic: gems only (60-150) - quality gate on premium currency
- Legendary: gems only (200-300) - aspirational, whale attractor

### VIP Tier: $4.99/mo
- Ad-free experience
- 2x daily chip bonus
- Exclusive VIP cosmetics
- Early access to new items

### Key Margin Insight
- $0.01/gem effective cost to user at $0.99 tier
- Legendary items at 300 gems = $3.00 effective cost
- Common cosmetics at 500 chips = 5 ad watches = $0.50-1.00 in ad revenue
- Presence multiplier system means cosmetics directly affect payout = pay-to-win lite (not exploitative, bounded by skill)

## Alley Kingz Integration: "Table Presence" Mechanic
- Outfit fashion score x Aura score x Rank bonus = Presence Multiplier
- Presence multiplier applied to chip payouts (win, blackjack)
- Max multiplier: ~1.98x at full Legend + Legendary Drip + Legend Aura
- Not pay-to-win: only ~10-50% bonus, skill still dominates

## 3D Implementation
- Three.js r128 (via CDN)
- TWEEN.js for animations
- Features: Casino table mesh, chip tray, hologram avatar stands (5 seats), chandelier lighting, particle dust, animated neon point lights, ACESFilmic tone mapping
- Cards: DOM-overlaid on canvas (2.5D hybrid - fast, readable)
- TODO for full WebGL cards: render cards as Three.js PlaneGeometry with dynamic canvas textures

## TODO / Deferred
- django-allauth install for real Google/Facebook OAuth
- Stripe integration for gem purchases (wire to /payments/ app)
- WebSocket (Django Channels) for live multiplayer
- Full 3D card meshes with Three.js texture rendering
- Split hand mechanic (stub in place)
- Rewarded ad SDK integration (replace sleep() simulation)
- Push GOOGLE_ADS_CLIENT to real publisher ID
