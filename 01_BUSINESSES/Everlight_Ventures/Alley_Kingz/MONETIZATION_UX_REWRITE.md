# Everlight Arcade -- Monetization UX Rewrite
# "Dark Luxury" Premium Experience Design

**Version:** 1.0
**Date:** 2026-03-10
**Directive:** Kill the streetwalker energy. Build a VIP lounge.
**Design North Star:** Apple Store meets Wynn casino host.

---

## Design Philosophy

The old monetization UX had one problem: it was loud. Gem icons pulsing in the corner. Buy buttons stacked on buy buttons. Popups interrupting hands mid-deal. The entire experience communicated desperation -- "please spend" -- instead of confidence.

The new approach communicates the opposite: we do not need your money. We built something worth paying for, and when you are ready, the door is open.

**Three principles govern every monetization surface:**

1. **Invitation, never interruption.** No element related to spending should ever block, overlay, obscure, or pause gameplay. Every purchase moment is a doorway the player walks through by choice.

2. **Scarcity through restraint.** Fewer purchase touchpoints, not more. A single elegant card in the right place outperforms six flashing banners. Luxury brands do not have clearance racks.

3. **The player discovers value -- we do not announce it.** Benefits are revealed through experience, not bullet-point lists. The Master Pass member notices they are earning double gems before they read a tooltip about it. The feeling comes first, the explanation second.

**Color System (Monetization-Specific)**

| Role | Hex | Usage |
|------|-----|-------|
| Canvas | #0A0A0A | All backgrounds, surfaces |
| Elevated Surface | #111111 | Cards, panels, modal backgrounds |
| Border / Divider | #1A1A1A | Subtle separations |
| Gold Primary | #D4AF37 | Master Pass, premium accents, CTAs |
| Gold Soft | #E8D48B | Hover states, secondary gold text |
| Gem Purple | #7B2FF7 | Gem currency, gem shop accents |
| Gem Purple Soft | #9B6DFF | Gem hover, gem quantity text |
| Text Primary | #E5E5E5 | Headings, body copy |
| Text Muted | #8A8A8A | Captions, metadata, secondary info |
| Success | #2ECC71 | Purchase confirmations only |

**Typography for Monetization Surfaces**

- Product names: Cormorant Garamond Semi-Bold, letterspaced +80
- Price text: Inter Bold, no cents if .00 (show "$14.99" not "$14.99/mo")
- Body descriptions: Inter Regular 14px, line-height 1.6, #8A8A8A
- Billing period shown separately beneath price in 11px muted text

---

## 1. Master Pass ($14.99/month)

### What It Is

The Master Pass is the singular premium product across the entire Everlight Arcade ecosystem. It includes all individual game passes (Alley Kingz, Blackjack, future titles), a daily gem stipend, exclusive cosmetics, and VIP priority features. It is not "a subscription" -- it is membership.

### Naming and Language

Never call it a "subscription." Never say "subscribe." The language is always:

- "Become a member"
- "Join the inner circle"
- "Your membership includes..."
- "Members receive..."

The word "subscribe" communicates obligation. "Membership" communicates belonging.

### UX Copy

**Headline (seen on the membership page):**
> Your All-Access Membership

**Subhead:**
> Everything. Every game. Every month.

**Body (kept short -- three lines maximum):**
> Full access to every game pass in the Everlight Arcade. 50 Gems delivered daily. Priority matchmaking. Exclusive seasonal cosmetics. One membership. Nothing else to buy.

**CTA Button:**
> Become a Member

**Post-purchase confirmation (replaces any "thank you" popup -- appears as an inline status change):**
> Welcome to the inner circle.

### Visual Treatment

**No popup. No banner. No floating badge.** The Master Pass is presented in exactly two places:

**Location 1: The Membership Page (/arcade/membership)**

This is a dedicated, full-screen page accessible from the main arcade hub. It is not buried in settings. It is not in a shop. It has its own nav item labeled simply "Membership" in gold text.

The page structure:

```
[Full-width hero section]
  Background: #0A0A0A with a single, very subtle radial gradient
  of #D4AF37 at 3% opacity, centered, creating a warm glow
  that the eye barely registers consciously.

  Center-aligned:
  - Cormorant Garamond wordmark: "EVERLIGHT"
  - Beneath it, smaller: "MASTER PASS"
  - A thin gold line (1px, 60px wide, centered)
  - Price: "$14.99" in Inter Bold 32px, gold
  - Beneath price: "per month" in Inter Regular 12px, #8A8A8A
  - 40px of whitespace
  - CTA: "Become a Member" -- gold text on transparent background,
    1px gold border, generous padding (16px 48px), Cormorant Garamond.
    On hover: background fills to #D4AF37, text becomes #0A0A0A.
    No gradients. No glow. No animation. The simplicity IS the luxury.

[Spacer: 80px]

[Benefits section -- NOT a bullet list]
  Three columns, evenly spaced. Each column:
  - A single icon (line-weight, gold, 24px -- not filled, not emoji)
  - A two-word label in caps, letterspaced, 11px, #8A8A8A
  - A one-sentence description in 14px, #E5E5E5

  Column 1:
    Icon: Diamond outline
    Label: EVERY GAME
    Text: All current and future game passes included. No add-ons.

  Column 2:
    Icon: Gem outline
    Label: DAILY GEMS
    Text: 50 Gems deposited to your account every day you log in.

  Column 3:
    Icon: Crown outline
    Label: VIP ACCESS
    Text: Priority matchmaking. Exclusive cosmetics. Early access to new titles.

[Spacer: 60px]

[Comparison strip -- understated]
  A single horizontal row showing what individual passes cost:
  "Alley Kingz Pass: $4.99  +  Blackjack Pass: $4.99  +  50 daily gems  =  $14.99"
  All in #8A8A8A, 12px. No "SAVE $X!" badge. No strikethrough pricing.
  The math speaks. Let the player do it.

[Spacer: 40px]

[Second CTA -- identical to the first, same style]
```

**Location 2: The Profile Sidebar (Contextual)**

When a non-member views their profile or account page, a single line appears at the bottom of the sidebar:

> Everlight Master Pass -- Learn more

Gold text, no icon, no badge, no animation. A text link. Clicking it navigates to the Membership page.

That is it. Two locations. No urgency timers. No "LIMITED TIME" banners. No discount hooks. The product is the product.

### What Members See (Post-Purchase)

- A small gold diamond icon appears next to their username everywhere (chat, leaderboards, match lobbies). No text label. Members know what it means.
- The "Membership" nav item text changes from gold to white, and a small "Active" indicator appears -- a 4px gold dot.
- On the Membership page, the CTA is replaced with:
  > Member since [Month Year]
  Beneath it: "Manage membership" as a text link (leads to Stripe customer portal).
- Daily gem deposits appear in the rewards page as a line item: "Master Pass -- 50 Gems" with a gold diamond icon, distinguishing it from login streak gems.

---

## 2. Individual Game Passes

### Products

| Pass | Price | Slug |
|------|-------|------|
| Alley Kingz Pass | $4.99/mo | `ak-pass-monthly` |
| Blackjack Pass | $4.99/mo | `bj-pass-monthly` |

### Design Strategy: Secondary Without Feeling Second-Class

Individual passes exist for players who only play one game and do not want to pay for the full ecosystem. They must feel like legitimate products, not stripped-down versions of the Master Pass. But they must never compete with the Master Pass for attention.

**Rule: Individual passes are never promoted. They are discovered.**

### Where They Live

Individual passes appear in exactly one place: the settings or account page of each specific game. Not the main arcade hub. Not the shop. Not the rewards page.

Inside each game, in the settings panel or a "Game Pass" section:

```
[Card: 100% width, #111111 background, 1px #1A1A1A border, 16px padding]

  Left side:
    Game icon (small, 32px)
    "Alley Kingz Pass" in Inter Semi-Bold 16px, #E5E5E5
    Below: "$4.99 / month" in Inter Regular 13px, #8A8A8A

  Right side:
    Button: "Activate" -- outlined style, #E5E5E5 border and text
    (NOT gold -- gold is reserved for Master Pass)

  Below the card, a single line:
    "Or get every pass with Master Pass -- Learn more"
    "Master Pass" in gold. "Learn more" underlined. Everything else #8A8A8A.
```

### UX Copy for Individual Passes

**Alley Kingz Pass:**
> Full access to all Alley Kingz seasonal content, bonus challenges, and exclusive cars. Updated every season.

**Blackjack Pass:**
> Unlock premium tables, exclusive card backs, and priority seating. Your permanent seat at the high roller table.

### The Nudge to Master Pass

Every individual pass purchase screen includes one -- and only one -- reference to the Master Pass. It is never a comparison chart. It is never a "you could save X" callout. It is simply:

> This pass is also included with Everlight Master Pass.

Small text. #8A8A8A. Factual. No persuasion. The player either investigates or they do not.

If a player who owns an individual pass later purchases the Master Pass, their individual pass is automatically credited back as a prorated refund for the remaining billing period. This is communicated once, cleanly:

> Your Alley Kingz Pass has been folded into your Master Pass membership. The remaining balance has been credited to your account.

---

## 3. Gem Shop

### Design Philosophy

The current gem shop has the energy of a convenience store display -- packs stacked vertically with giant GEM icons, "BEST VALUE" badges, and purchase buttons that look like they were designed for a free-to-play clicker game.

The new gem shop should feel like walking into a jeweler. Quiet. Curated. Every item presented with space and intention.

### Gem Shop Page (/arcade/gems)

Accessible from the arcade hub via a nav item labeled "Gems" with a small purple diamond icon.

```
[Page Header]
  "Gems" in Cormorant Garamond, 28px, #E5E5E5
  Below: Your current balance -- "1,247" in Inter Bold 20px, #7B2FF7
  with a small purple diamond icon inline before the number.
  No "YOUR BALANCE:" label. The context is obvious.

[Spacer: 48px]

[Gem Tiers -- Horizontal Row on Desktop, Vertical Stack on Mobile]
  Each tier is a card. Maximum 4 visible at once (the fifth, largest
  pack lives behind a "View all" expansion -- whales will find it).

  Card design (each):
    Width: equal, filling the row
    Background: #111111
    Border: 1px solid #1A1A1A
    Border-radius: 12px
    Padding: 24px, center-aligned

    Top: Gem count in Inter Bold 24px, #7B2FF7
         "100" or "600" or "1,500" or "4,000"

    Middle: A single purple diamond icon, sized proportionally
            to the tier (32px for Starter, 40px for Standard,
            48px for Premium, 56px for Ultra). The icon gets
            slightly more detailed/faceted at higher tiers.

    Bottom: Price in Inter Semi-Bold 16px, #E5E5E5
            "$0.99" / "$4.99" / "$9.99" / "$24.99"

    Button: "Purchase" -- 1px #7B2FF7 border, #7B2FF7 text,
            transparent background. On hover: filled #7B2FF7
            background, #FFFFFF text.

  NO BADGES. No "BEST VALUE." No "POPULAR." No "WHALE."
  No percentage-off callouts. No "bonus gems" marketing.

  The value scaling is self-evident:
    100 gems for $0.99 = 101 gems per dollar
    600 gems for $4.99 = 120 gems per dollar
    1,500 gems for $9.99 = 150 gems per dollar
    4,000 gems for $24.99 = 160 gems per dollar

  Players who buy frequently will notice the scaling.
  That discovery feels like insider knowledge, not a sales pitch.
```

### Purchase Flow

When a player taps "Purchase" on a gem tier:

1. The card subtly elevates (2px box-shadow increase, 150ms ease).
2. A confirmation appears INLINE beneath the card (not a modal, not a popup):
   > "600 Gems for $4.99"
   > [Confirm] [Cancel]
   Both buttons are text-style, small. Confirm is #7B2FF7. Cancel is #8A8A8A.
3. On confirm: redirect to Stripe Checkout (clean, fast, no interstitials).
4. On return: the balance updates with a subtle count-up animation. A brief toast (bottom of screen, auto-dismisses after 3 seconds):
   > "+600 Gems"
   Purple text on #111111 background. No celebration animation. No confetti. No fanfare. The transaction is complete. Move on.

### What NOT to Do

- No "first purchase bonus" popups
- No gem sale events with countdown timers
- No "gem rain" animations after purchase
- No push notifications about gem deals
- No "you're running low on gems" alerts
- No gem balance displayed persistently in the game UI header (show it only in the gem shop and rewards pages)

---

## 4. In-Game Purchase Moments (The Empty Wallet)

This is the most critical UX surface. The moment a player runs out of chips at the blackjack table or needs gems and does not have them -- this is where most games destroy trust with aggressive popups. We do the opposite.

### Blackjack: Out of Chips

**Current (bad) pattern:** Player loses last chips. Full-screen popup: "OUT OF CHIPS! Buy more now!" with three tiered options and a giant BUY button.

**New pattern:**

The player's chip count reaches zero. The following happens:

1. The table dims very slightly (brightness drops to 0.92, not dramatic).
2. The betting interface grays out naturally -- the bet slider becomes unresponsive, the "Deal" button fades to #8A8A8A. No popup.
3. After 1.5 seconds of the player sitting at an empty table, a single line of text fades in below the betting area, centered:

   > "Your table balance is empty."

   Inter Regular, 14px, #8A8A8A. Understated. Factual.

4. Below that, after another 0.5 second delay, two options appear side by side:

   > [Convert Gems]  |  [Visit Gem Shop]

   Both are text links, not buttons. "Convert Gems" is #7B2FF7. "Visit Gem Shop" is #8A8A8A. The vertical bar separator is #1A1A1A.

   If the player has gems, "Convert Gems" opens an inline mini-panel (not a modal) showing:
   ```
   Your Gems: 247
   Convert: [slider or input, default 5] Gems -> 500 Chips
   [Convert]
   ```
   Clean, fast, stays on the table page. After conversion, the table reactivates immediately. No celebration. The game continues.

   If they have no gems, only "Visit Gem Shop" appears (no point showing a conversion option with nothing to convert).

5. The table remains visible the entire time. The cards from the last hand stay dealt. The atmosphere does not break. The player never leaves the table mentally.

**The VIP host metaphor in practice:** Imagine sitting at a Wynn blackjack table and running out of chips. The dealer does not shout. A host appears at your shoulder, leans in quietly, and says, "Would you like me to bring more?" That is this interaction. Quiet. Respectful. Available but not aggressive.

### Alley Kingz: Insufficient Currency for an Action

Same philosophy. When a player attempts an action they cannot afford (upgrading a card, opening a chest, entering a special event):

1. The button they tapped shows a brief shake animation (subtle, 200ms, 2px horizontal displacement -- the universal "nope" signal).
2. A tooltip or inline message appears near the button:

   > "Requires 50 Gems"
   > [View Gem Shop]

   Just information and a path forward. No modal. No overlay. No "YOU NEED MORE GEMS!" banner.

### What This Kills

- Full-screen "OUT OF CHIPS" overlays -- gone
- Popup modals with tiered purchase options at the moment of loss -- gone
- "Watch an ad for free chips" buttons -- gone (no ads in the Everlight ecosystem, ever)
- Countdown timers on "special offers" triggered by empty balances -- gone
- Any element that makes the player feel punished for running out of currency -- gone

---

## 5. Conversion Nudges (Luxury-Grade Persuasion)

Luxury brands do not persuade through urgency or scarcity theater. They persuade through aspiration, social proof, and the careful curation of what you are allowed to see.

### Nudge 1: The Quiet Upgrade Path

**Where:** Post-match summary screen (Alley Kingz) or session summary (Blackjack)

**What:** After a strong session (3+ wins in a row, or a profitable blackjack run), a single line appears at the bottom of the summary:

> Members earned 2x rewards this session.

Gold text. No button. No link. No CTA. Just a fact. The player either already knows what the Master Pass is, or they will look into it. The curiosity does the work.

**Luxury parallel:** Hermes does not advertise the Birkin. They let you see someone carrying one.

### Nudge 2: The Member Glow

**Where:** Everywhere members are visible (match lobbies, leaderboards, chat)

**What:** Master Pass members have a gold diamond next to their name. That is it. No "VIP" badge. No animated border. A single, small, elegant icon.

Non-members see this icon constantly on other players. They are never told what it means. Eventually, they either ask in chat (social proof from peers, infinitely more powerful than marketing copy) or they find the Membership page on their own.

**Luxury parallel:** Members-only clubs do not explain their exclusivity. The velvet rope is the marketing.

### Nudge 3: The Soft Gate

**Where:** Specific premium cosmetic items in the customization screen

**What:** Certain items (card backs, table themes, avatar accessories) are visible but dimmed, with a small gold lock icon. No price tag. No "UNLOCK WITH GEMS" button. Just the lock.

When tapped, the item expands to show a clean detail view with one line:

> Included with Master Pass

And beneath it, a text link: "Learn more" leading to the Membership page.

The player sees the item. They want the item. The path to getting it is quiet and clear. No urgency. No discount hook. The item's desirability does the selling.

**Luxury parallel:** The window display at Cartier. You see it. You want it. You walk in when you are ready. Nobody outside with a megaphone.

### Nudge 4: The Session Bookmark

**Where:** When a non-member closes the game or navigates away

**What:** No exit-intent popup. No "WAIT! Before you go..." modal. Instead, on their next visit (next session), a single line appears on the arcade hub:

> Welcome back. Your streak is at 4 days.

If they are a non-member and this is their 7th+ session, a second line appears beneath it:

> Members earn 2x streak rewards.

Small, muted, informational. Disappears after 5 seconds or any interaction.

**Luxury parallel:** A good hotel concierge remembers your name and preferences. They do not chase you down the hallway with a room upgrade offer.

### Nudge 5: Social Gifting (Future Feature)

**Where:** Post-match screen, between friends

**What:** Members can send a small gem gift (5 Gems) to an opponent after a match. The recipient sees:

> [Player Name] sent you a gift. [Accept]

When they accept and see "5 Gems" with a note "Sent by a Master Pass member" -- that is the most effective ad for the Master Pass that exists. Generosity as marketing.

**Luxury parallel:** AMEX Centurion cardholders buying rounds for strangers. The card sells itself through the cardholder's behavior.

---

## 6. What We Remove Entirely

The following elements from the current UX are eliminated:

| Kill | Why |
|------|-----|
| Gem balance in the persistent header/nav | Creates constant spending anxiety. Show only on relevant pages. |
| "SALE" or "LIMITED TIME" badges on any product | Discount culture destroys premium positioning. |
| Tiered purchase popups at moment of loss | Predatory. The worst mobile game pattern. |
| "Best Value" / "Most Popular" badges on gem packs | Let the math speak. Players are not stupid. |
| Animated gem/coin icons anywhere in the UI | Slot machine energy. Kill it. |
| Push notifications about deals, sales, or spending | Never interrupt a player's life to ask for money. |
| "First purchase bonus" or "starter pack" promotions | Signals that the base product is overpriced. |
| Comparison charts between free and paid tiers | Creates a "free = inferior" feeling that damages the base experience. |
| Any countdown timer attached to a purchase opportunity | Fabricated urgency is the opposite of luxury. |

---

## 7. Stripe Product Catalog Updates

Based on this rewrite, the Stripe product catalog should be updated:

| Stripe Product Name | Price | Slug | Notes |
|---------------------|-------|------|-------|
| Everlight Master Pass | $14.99/mo | `master-pass-monthly` | NEW -- replaces arcade-vip-monthly as the flagship |
| Alley Kingz Game Pass | $4.99/mo | `ak-pass-monthly` | Individual pass, secondary positioning |
| Blackjack Game Pass | $4.99/mo | `bj-pass-monthly` | Individual pass, secondary positioning |
| Gems -- 100 | $0.99 | `gems-100` | Existing, no copy changes |
| Gems -- 600 | $4.99 | `gems-600` | Remove "POPULAR" badge |
| Gems -- 1,500 | $9.99 | `gems-1500` | Remove "BEST VALUE" badge |
| Gems -- 4,000 | $24.99 | `gems-4000` | Remove "WHALE" badge |
| Gems -- 10,000 | $49.99 | `gems-10000` | Hidden behind "View all," no badge |

The old `arcade-vip-monthly` ($4.99) should be sunset and existing subscribers migrated or grandfathered. The Master Pass at $14.99 is the new anchor.

---

## 8. Implementation Priority

| Phase | What | Impact |
|-------|------|--------|
| 1 | Remove all aggressive popups, badges, and animated purchase elements | Immediate trust improvement |
| 2 | Build the Membership page (/arcade/membership) with Master Pass | Revenue anchor |
| 3 | Redesign gem shop with quiet luxury treatment | Purchase experience upgrade |
| 4 | Implement the "empty wallet" inline flow for Blackjack and Alley Kingz | Critical moment redesign |
| 5 | Add conversion nudges (member glow, quiet upgrade path, soft gates) | Long-term conversion lift |
| 6 | Relocate individual game passes to in-game settings only | Declutter, protect Master Pass |

---

## 9. Success Metrics

Measure the rewrite against these, not raw conversion rate (which will temporarily dip as aggressive prompts are removed):

| Metric | Target | Why |
|--------|--------|-----|
| Master Pass adoption rate | 8-12% of DAU within 90 days | Higher ARPU per subscriber than many small purchases |
| Average session length | +15% increase | Players stay longer when not interrupted by purchase prompts |
| Day-7 retention | +10% increase | Aggressive monetization is the #1 driver of early churn |
| Gem shop revenue per buyer | Maintain or increase | Fewer buyers, higher average order value = luxury model |
| Refund/chargeback rate | Below 1% | Clean purchase flows reduce regret purchases |
| Master Pass churn (monthly) | Below 8% | Members who feel respected stay |

---

*This document is the single source of truth for monetization UX across the Everlight Arcade. All implementation work -- Lovable prompts, Stripe configuration, Supabase logic -- must reference this file.*
