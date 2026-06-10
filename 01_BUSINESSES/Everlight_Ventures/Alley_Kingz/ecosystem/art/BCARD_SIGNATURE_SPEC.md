# The B-Card - $BCARDD's Signature Device
**Spec date:** 2026-06-03 | **Status:** locked design, queued for art generation

> **$BCARDD CANONICAL LOOK (LOCKED 2026-06-03):** $BCARDD's official appearance is the **AI dealer MP4
> look - specifically BUFF $BCARDD dealing the cards out.** All $BCARDD art (this B-Card device, card
> #0001, the brand emblem, the casino dealer avatar) should match that buff-dealer look. The B-Card is
> also the 1-in-1,854,799 jackpot trigger in the casino - see `Everlight_Gaming/Blackjack/BCARDD_BET_SPEC.md`.

## What it is
$BCARDD's signature piece and the brand's primary logo/emblem. A blackjack/casino-style
playing card, but the rank/suit symbol is replaced by a **crowned letter B**: a bold capital
**B** with a **crown resting on top of it**. Think "Ace of [Crowned-B]" instead of Ace of Diamonds.

## Exact layout (like a real playing card)
- **Center:** ONE large crowned-B, dominant, centered.
- **Corners:** a smaller crowned-B in EACH of the 4 corners (top-left, top-right, bottom-left,
  bottom-right), the way rank pips sit on a real card. (Top corners upright; bottom corners may
  mirror/rotate 180 like a true card, designer's call.)
- **Card body:** clean rounded-rect card, premium feel.

## Brand styling (match $BCARDD / Everlight)
- Palette: Everlight gold `#D4AF37` for the crowned-B + border, deep near-black `#0A0A0A` card
  face, subtle cyberpunk neon edge glow. Luxury + street, NOT cartoonish.
- The crown = small, regal, sits cleanly on the B's top.
- This is a CLEAN ORIGINAL device. Do NOT reference playing-card suit symbols beyond layout, and
  absolutely NO bat, no rum/liquor cues, no $BCARDD red/script (per LEGAL_TRADEMARK_DEFENSE.md).

## Uses (where it appears)
1. **Brand emblem / logo** - the face of $BCARDD across the game, coin, site, NFT collection badge.
2. **Necklace prop** - worn on a chain by the $BCARDD dog character (dealer drip).
3. **In-hand dealer prop** - $BCARDD holding/dealing the B-Card.
4. Optional: the back-of-card design for the in-game deck + the card #0001 accent.

## Generation prompts (Leonardo Phoenix, via art/generate_icons.py style)
**A) The emblem (primary logo), centered, on dark:**
`A premium casino playing card emblem, dark near-black card face with a thin glowing gold border,
the rank symbol is a bold gold capital letter B with a small regal crown resting on top of it,
ONE large crowned-B centered, plus a small matching crowned-B in each of the four corners like
playing-card rank pips, cyberpunk luxury aesthetic, gold #D4AF37 on black, subtle neon edge glow,
clean vector-like logo, high detail, no text, centered, square`

**B) Necklace pendant version (for the dog):**
`A luxury pendant shaped like a small casino card on a gold chain, the card face shows a bold gold
capital B with a small crown on top, centered, premium cyberpunk streetwear jewelry, gold and black,
glowing edges, product shot on transparent/dark background`

**C) Dealer holding it (character beat, optional for Seedance/poster):**
`A confident cyberpunk dog dealer in a neon-lit alley casino holding up a single glowing playing
card whose symbol is a crowned gold letter B, dramatic lighting, gold and black palette, cinematic`

## Next step
Run the emblem (prompt A) first; once Rich approves the look, wire it as: the start-screen crest
(replaces the current placeholder logo at `game/assets/ui/logo.png`), the brand mark on the coin/site,
and the $BCARDD card accent. Save outputs to `game/assets/ui/bcard_emblem.png` (+ necklace/dealer variants).
