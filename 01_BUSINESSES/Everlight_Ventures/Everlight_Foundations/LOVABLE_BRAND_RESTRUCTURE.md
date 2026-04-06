# LOVABLE: Brand Restructure (War Room bf9304dd)

Paste this into Lovable. This restructures the site navigation and hero section. Do NOT remove any existing page content or features -- this only changes navigation grouping and the homepage hero.

---

## 1. REPLACE THE NAVIGATION

Remove the current flat nav. Replace with this 5-item top nav with dropdowns:

```
[EV Monogram]   Studio   Arcade   Stack   Capital   Our Story   [Diamond VIP badge] [Login/Avatar]
```

### Dropdown contents:

**Studio** (dropdown):
- Sam & Robo -> /publishing/sam-and-robo
- Beyond the Veil -> /publishing/beyond-the-veil

**Arcade** (dropdown):
- Alley Kingz -> /arcade/alley-kingz
- Blackjack -> /arcade/blackjack
- Leaderboard -> /arcade (scroll to leaderboard section)
- Game Store -> /arcade (scroll to store section)

**Stack** (dropdown):
- Onyx POS -> /onyx
- Hive Mind -> /hivemind
- Logistics -> /logistics
- HIM Loadout -> /him-loadout

**Capital** (dropdown):
- XLM Bot Dashboard -> /dashboard

**Our Story** -- single link, goes to /about (or create this page if it doesn't exist -- founder story, press, contact)

### Nav design rules:
- Desktop: All 5 items visible. Dropdowns open on hover with a subtle fade-in (200ms). Dropdown background: #1A1A1A, border: #2A2A2A, text: #E5E5E5, hover highlight: #D4AF37.
- Mobile: Hamburger menu. Show the 5 pillar names with small icons. "Our Story" and login at the bottom.
- Keep the Diamond VIP badge and Login/Avatar exactly as they are now in the top-right.
- The EV monogram links to / (home).

---

## 2. REPLACE THE HERO SECTION ON HOMEPAGE (/)

**New headline:**
> Built from the ground up. Built to last.

**New subheadline:**
> Everlight Ventures is a venture studio for the self-made -- tools, stories, and systems that give you the infrastructure to build your own way. Five years of work. Eight operating ventures. No outside capital.

**Primary CTA button:** "Explore the Ventures" (scrolls to portfolio grid below)
**Secondary CTA link:** "Read Our Story" (goes to /about or Our Story page)

**Keep the existing visual design** -- dark gradient, diagonal light streak, EV monogram in #D4AF37, Cormorant Garamond wordmark. Only the text changes.

**Move the old tagline** "Build Different. Build in the Light." to the **site footer** as a brand signature line, small text, centered, above copyright.

---

## 3. RENAME THE PORTFOLIO GRID

The ventures grid section below the hero currently shows all products flat. Group them into the 4 pillars visually:

Each pillar gets a section header with its tagline:

- **Everlight Studio** -- "Stories built to last." -- then show Sam & Robo and Beyond the Veil cards
- **Everlight Arcade** -- "Culture deserves AAA." -- then show Alley Kingz and Blackjack cards
- **Everlight Stack** -- "Run your business without giving up a percentage." -- then show Onyx POS, Hive Mind, Logistics, HIM Loadout cards
- **Everlight Capital** -- "Money working while you work." -- then show XLM Bot card

Keep the existing card designs and accent colors. Just group them under pillar headers with the taglines in muted text (#8A8A8A) below each header.

---

## 4. CROSS-LINKING CTAs

Add a "Related" section at the bottom of these product pages (above the footer):

**On /onyx page, add:**
> "Running a team means tracking more than just sales. Hive Mind automates the reporting, scheduling, and communications that Onyx captures."
> [Button: "See How Hive Mind Works" -> /hivemind]

**On /publishing/sam-and-robo, add:**
> "Sam and Robo are learning what it means to do hard things. So is every founder. If you're building something of your own, the tools we use to run Everlight are available -- starting with Onyx POS, $49/month flat rate."
> [Button: "See Onyx POS" -> /onyx]

**On /dashboard (XLM Bot), add:**
> "The same AI system advising this bot runs our full business operations. Hive Mind is opening its waitlist to operators and founders who want AI working in their business."
> [Button: "Join the Hive Mind Waitlist" -> /hivemind]

Style these CTA sections: #1A1A1A card background, #2A2A2A border, button in #D4AF37 with dark text.

---

## 5. OUR STORY PAGE (/about)

If this page doesn't exist, create it with this content:

**Headline:** Our Story

**Body:**
> Everlight Ventures started on a Samsung Z Fold. No office. No investors. No co-working space. Just a founder who refused to wait for permission.
>
> Five years later, the portfolio spans eight operating ventures -- a POS system tested in a live retail store, a children's book series written between shifts, a card game hand-coded in Three.js, a trading bot running live, and an AI platform that replaced a $50,000-a-year operations team.
>
> Every product exists because someone decided to build it before anyone said it was possible.
>
> Everlight is the infrastructure of the self-made.

**Below the story, add:**
- Contact email link
- Social links (if any exist in the current footer)

Design: Same dark theme, centered text, generous spacing, Cormorant Garamond for the headline.

---

## IMPORTANT
- Do NOT remove the Arcade easter egg / speakeasy discovery if it exists
- Do NOT remove any existing game features, blackjack, chat, or profile systems
- Do NOT change any existing page URLs -- the nav just groups them differently
- Keep /publishing as a hub page that still works (Studio dropdown items link to sub-pages, not the hub)
