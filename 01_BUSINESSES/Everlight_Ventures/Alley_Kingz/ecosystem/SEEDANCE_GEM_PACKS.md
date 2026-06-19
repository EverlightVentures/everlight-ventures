# Alley Kingz -- Gem-Pack Tier Art (Chop Shop currency)

Answer to "do I need more art or just implement?": the 5 gem packs ALREADY have art
(`assets/shop/ak-gems-*.png`, painted by the old Leonardo bot) and they load fine -- what you're
seeing as "old teal/gold/bronze/green diamonds" IS that old art. So this is a REPLACE: generate
fresh Seedance art in our current premium style for the 5 tiers, and I'll swap them in.

Save each to `/sdcard/Download` with the EXACT filename below, ping me, I place + wire (I'll point the
shop at `.jpg`). **Square 1024x1024**, subject centered on a dark plate.

**House style (paste at end):**
> Gritty TV-MA cyberpunk street aesthetic, neon-noir alley lighting, Everlight gold (#D4AF37) accents,
> deep near-black background, high detail, dramatic rim light, premium mobile-game store asset,
> collectible energy, no text, no watermark.

The 5 tiers should ESCALATE (small -> jackpot), each a distinct hero gem object, not just a recolor:

**ak-gems-rookie.jpg** -- "Rookie Stash" (500): a small handful of glowing cyan gems spilling from a
torn canvas pouch on a dark plate, modest, starter-tier. [house style]

**ak-gems-player.jpg** -- "Player Pack" (1,100): a tidy stack of cyan-violet gems in a battered metal
tin, a little more loot, brighter glow. [house style]

**ak-gems-baller.jpg** -- "Baller Bag" (2,500): a bulging duffel bag overflowing with glowing gems +
a few gold coins, street-baller energy, richer light. [house style]

**ak-gems-highroller.jpg** -- "High Roller Crate" (6,500): an open armored crate packed with radiant
gems spilling out, gold trim, sparks, high-value drama. [house style]

**ak-gems-kingpin.jpg** -- "Kingpin Vault" (14,000): a cracked-open vault door pouring a cascade of
brilliant gems + gold, crowned-B sigil on the vault, the jackpot tier, blinding gold-cyan glow,
the most epic of the five. [house style]

---

## Also: the inline gem icon (the little diamond on prices)
The shop shows a `diamond` glyph on every "buy with gems" price + the premium-unlock button. I'm
wiring those to your existing `cur_gems.jpg` so the currency reads consistently with the lobby --
no new art needed for that part, just implementation.
