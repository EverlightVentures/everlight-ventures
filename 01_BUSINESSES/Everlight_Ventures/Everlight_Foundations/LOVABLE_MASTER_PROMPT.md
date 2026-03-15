# LOVABLE MASTER PROMPT
# Copy this entire prompt into Lovable chat to build the full site.
# Then upload LOVABLE_SITE_MASTER.md as the content source.

---

## PROMPT (copy everything below this line into Lovable):

Build "Everlight Ventures" -- a premium multi-page brand hub website for a venture studio. This is a real business at everlightventures.io.

## BRAND IDENTITY

- Company: Everlight Ventures (parent brand / venture studio)
- Legal entity: Everlight Logistics LLC
- Tagline: "Build Different. Build in the Light."
- Tone: Premium, luxury, confident. Think Apple meets venture studio. Not corporate. Not startup-bro. Clean, bold, and purposeful.

## DESIGN SYSTEM (STRICT)

Theme: Dark luxury
- Background: #0A0A0A (near-black)
- Card surfaces: #141414 with border #2A2A2A
- Text primary: #F5F5F5 (off-white)
- Text secondary: #A0A0A0
- Text muted: #6B7280
- Primary accent: #D4AF37 (warm gold -- CTAs, hover states, highlights, logo)
- Glass effects: subtle backdrop-blur on cards, rgba(255,255,255,0.03) backgrounds
- Borders: rgba(255,255,255,0.08)

Typography:
- Headings: Inter or Sora, bold weight, tight letter-spacing
- Body: Inter or DM Sans, 400 weight, generous line-height
- Serif accent for Publishing section only: Playfair Display

Interactions:
- Cards: subtle hover lift (2-4px) with soft shadow
- CTAs: gold fill (#D4AF37) with dark text, slight scale on hover
- Smooth scroll between sections
- Fade-in on scroll for each section
- Accent color top-border on venture cards that animates in on hover

## SITE STRUCTURE (React Router)

Build these as separate pages with a shared navigation bar and footer:

### Shared Navigation Bar
- Everlight Ventures logo (left, gold text or icon)
- Tab links: Home | Arcade | HIM Loadout | Logistics | Publishing | Alley Kingz | Onyx | Hive Mind | Dashboard
- Mobile: hamburger menu
- Style: fixed top, dark glass background with backdrop-blur

### Shared Footer
- "Everlight Ventures -- Building what matters."
- Nav links: Home | Ventures | About | Contact
- Social placeholders: Instagram, X, TikTok, LinkedIn
- Contact: hello@everlightventures.io
- Legal: "Copyright 2026 Everlight Ventures. All rights reserved. Everlight Logistics LLC."

### Pages and Routes:

1. **/** -- Homepage (brand hub)
   - Hero with tagline + CTA
   - Ventures grid (6 cards linking to each venture page)
   - About section (founder story)
   - Each venture card has its own accent color

2. **/him-loadout** -- HIM Loadout
   - Affiliate gear curation for men
   - Categories grid, featured product cards, how-it-works, newsletter signup
   - Accent: Steel blue (#4A7C9B)

3. **/logistics** -- Everlight Logistics
   - Shipping and fulfillment services
   - Services grid, differentiators, quote request form
   - Accent: Blue/teal (#D4963A)

4. **/publishing** -- Everlight Publishing
   - Publishing overview hero
   - Three book sections with individual accent colors:
     - Beyond the Veil (amber #D4871C) -- quantum western thriller, COMING SOON badge
     - The Silent Witness (steel blue #4A6FA5) -- mystery thriller, IN DEVELOPMENT badge
     - Everlight Kids / Sam & Robo (gold #E8B84B + green #5DAE72) -- children's books, LAUNCHING 2026 badge
   - Use serif font (Playfair Display) for book titles and pull quotes
   - Each book section has: badge, blurb, target audience, CTA

5. **/arcade** -- Everlight Arcade
   - Shared arcade hub for Blackjack and Alley Kingz
   - Hero, game selector, shared progression/economy section, leaderboard, VIP/pass section, and AI-assisted play proof
   - Accent: Gold plus neon cyan over void black

6. **/arcade/blackjack** -- Everlight Blackjack
   - Social casino landing page with AI strategy coach, VIP/game pass benefits, chip and gem packs, cosmetics, daily rewards, and trust/disclaimer section
   - Must clearly position the game as virtual-currency entertainment only with no cash-out or redeemable value
   - Accent: Gold, deep charcoal, and controlled neon highlights

7. **/alley-kingz** -- Alley Kingz
   - PvP mobile game landing page
   - Hero, game description, factions, art style, monetization, early access signup
   - Accent: Neon cyan (#00F5FF) on midnight (#0D0D1A)
   - Crown gold (#D4AF37) for premium elements

8. **/onyx** -- Onyx POS
   - SaaS product page (point-of-sale for small retail)
   - Hero, pain points (3), features grid (6), pricing card ($49/mo), testimonials (3), FAQ (5), final CTA with email capture
   - Accent: Gold/amber (#D4A017)
   - Free 14-day trial CTA throughout

9. **/hivemind** -- Hive Mind
   - AI orchestration and Business OS product page
   - Hero, architecture stack, operator pain points, workflow section, revenue-system section, waitlist email capture, "runs Everlight Ventures" proof section
   - Accent: Violet (#7C3AED) with restrained mint support for systems/telemetry accents
   - Copy should position Hive Mind as the command plane for agents, workflows, approvals, memory, and monetization

10. **/dashboard** -- Trading Watchtower
   - Public telemetry page for the live XLM system
   - Hero, live status badges, health/quality cards, last-trade panel, deterministic-controls section, email capture, disclaimer
   - Accent: Electric green (#00C853) on void black (#0A0A0A)
   - Pull live trading metrics and watchtower fields from Supabase-backed telemetry, not hardcoded mock numbers

## FUNCTIONAL REQUIREMENTS

- All email capture forms should collect: email address, which page they signed up from
- Store form submissions in Supabase (connect Supabase integration)
- Each venture card on the homepage links to its respective page
- `/arcade/blackjack` should wire pack and VIP CTAs through the existing Stripe plus Supabase edge-function flow, not mock buttons
- Responsive: mobile-first, all grids collapse to single column on mobile
- All CTAs should be clearly visible and accessible
- No placeholder "Lorem ipsum" text -- all real copy is provided in the uploaded content file
- Status badges on Publishing books: styled as small outlined pills (COMING SOON = amber, IN DEVELOPMENT = blue, LAUNCHING 2026 = gold)
- `/dashboard` must support live badges for data quality, stream status, pulse regime, tick health, and last trade label
- `/hivemind` and `/dashboard` should visually feel like the same operating system family, not two unrelated landing pages

## CONTENT SOURCE

All page copy, descriptions, CTAs, and section content is provided in the uploaded file LOVABLE_SITE_MASTER.md. Use that file as the single source of truth for all text on every page. Do not invent copy -- use what is in the file.

## INTEGRATIONS TO CONNECT LATER

- Supabase (database for form submissions and customer data)
- Stripe (payments for Onyx POS trials, Hive Mind, and future operator products)
- Slack (notifications when someone signs up)
- GitHub (code sync)
- n8n webhooks (incident fan-out, form automation, and watchtower notifications)
- Business OS telemetry feed (public dashboard data source via Supabase mirror)

## IMPORTANT RULES

- No emojis anywhere on the site
- Use double hyphens (--) not em-dashes
- Every page must feel premium and intentional
- White space is your friend -- do not crowd sections
- The site should feel like visiting a luxury brand, not a template
- `/dashboard` should communicate operational honesty -- if data is degraded or stale, the UI should say so directly
