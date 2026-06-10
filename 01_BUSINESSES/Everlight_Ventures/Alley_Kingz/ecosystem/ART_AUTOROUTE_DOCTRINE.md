# ALLEY KINGZ -- ART AUTO-ROUTE DOCTRINE
### Operator law, 2026-06-07. "No generic art ever stays."

> "anytime there's a new item or whatever to pop up (shop item, anything) -- if it's
> got generic art and it can be custom art, it should auto-route to Leonardo AI or be
> added into the cron queue to be printed." -- Rich

## THE RULE
A placeholder is **always temporary**. Any new item -- a shop product, a card, a chest,
a cosmetic, a banner, a map, anything that renders an image -- must never ship with
generic/stock/programmer art as its permanent state. The moment it exists, it is
registered for custom Leonardo art. The cron paints it; real art replaces the
placeholder automatically; prod redeploys.

## THE MECHANISM (one queue, one cron)
- **Queue:** `_state/ak_art_queue.json` -- `[{id, prompt, negative, out, w, h}]`
- **Drainer:** `01_BUSINESSES/.../Alley_Kingz/ecosystem/art/art_factory.py`
  - Builds a missing-art worklist over THREE sources, in priority order:
    1. the ad-hoc queue (new items -- painted FIRST)
    2. cards (`data/card_art_manifest.json`, new-variants-first) -- auto-scanned, no manual step
    3. maps (the 10-city x 10-level x 4-district set, imported from `generate_world_maps.py`)
  - De-dupes by output path, skips anything already on disk (idempotent), continues on failure.
- **Cron:** `03_AUTOMATION_CORE/01_Scripts/art_factory_cron.sh` @ `15 17 * * *` (daily, `--limit 12`,
  free Leonardo). Paints the top 12 by priority, then `deploy_to_oracle.sh`. Never self-retires
  (the queue can grow any day); no-ops cheaply when nothing is missing.
  - This REPLACES the two old competing crons (`generate_world_maps_cron.sh`,
    `generate_card_art_cron.sh`) so the shared free daily cap is spent top-down, not raced.

## HOW TO REGISTER A NEW ITEM
- **Cards:** nothing to do -- add the card to `card_art_manifest.json` (slug + prompt + art_path)
  and the factory auto-scans it.
- **Anything else (shop products, chests, cosmetics, banners, one-offs):**
  ```
  python3 art_factory.py --enqueue \
    --id shop_chest_crew \
    --prompt "<what the art shows -- the house gritty style is auto-appended>" \
    --out game/assets/shop/chest_crew.png
  ```
  The house art voice (gritty TV-MA street / Twisted-Metal cyberpunk dog-crew, chrome+rust+neon,
  Everlight gold on vanta-black, NOT kiddish) is appended automatically -- you only write WHAT it shows.

## THE CONTRACT FOR CATALOGS
Any product/item catalog (shop, deck, cosmetics) declares per entry:
- `art`  -- the asset path the renderer points at (a placeholder until painted)
- `art_prompt` -- what the custom art should show
A scanner reads the catalog and enqueues any entry whose `art` file is missing. Until painted,
the placeholder renders; after the next cron, the real art renders. Same path, zero code change.

## INVARIANTS
- Free-first: Leonardo free tier only; `--limit 12/day` respects the shared cap.
- Idempotent: never repaints an existing file.
- On-brand: the gritty house style is enforced at enqueue time, not left to chance.
- Self-deploying: painted art ships to prod on the same cron run.
