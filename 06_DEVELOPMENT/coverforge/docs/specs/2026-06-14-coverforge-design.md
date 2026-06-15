# COVERFORGE - KDP Launch Command Center

**Design spec** | 2026-06-14 | Status: **APPROVED (Rich, 2026-06-14)**
Working name: `COVERFORGE` (public brand + domain TBD, kept private until launch per IP doctrine)

---

## 1. One-liner

For **fiction self-publishers on Amazon KDP**: type your book's details, get a **print-ready cover wrap** (front + spine + back, dimensionally correct so Amazon never rejects it) **plus** the listing assets that actually sell it: 7 backend keywords, 3 category picks, a back-cover blurb, and 5 Amazon Ads headlines, in one session, one credit.

**The moat is the bundle, not the cover model.** Competitors do covers OR keywords, never both, never print-correct. We fuse them.

## 2. Decisions locked (this session)

| Decision | Locked choice |
|---|---|
| First niche | **Fiction** (seed romance / thriller / fantasy genre packs first) |
| MVP scope | **Full thin bundle**: cover + 7 keywords + 3 categories + blurb + 5 ad headlines (A+ content = fast-follow) |
| Pricing | **Freemium + credit packs**: free first cover (watermarked low-res preview), pay credits to unlock print-ready PDF + bundle |
| Lane | Cheap-text bundle (sub-cent) + one cheap background image (~2-3 cents) = ~90% margin |

## 3. The core architecture - two-layer render (the differentiator)

The whole product hinges on **not letting the image model write the text.**

```
   +- AI image model --------------+     +- Deterministic compositor -------------+
   | generates BACKGROUND / scene  | --> | - lays real title+author as TRUE fonts |
   | only, NO text                 |     | - exact KDP pixel dims + 0.125" bleed  |
   +-------------------------------+     | - spine width COMPUTED from page count |
                                         | - 300 DPI front-only (ebook) +         |
                                         |   full-wrap PDF/X (paperback)          |
                                         +----------------+-----------------------+
                                                          v
                                          +- Template-dimension validator -+
                                          | asserts output matches Amazon's |
                                          | spec BEFORE unlock, so it never |
                                          | bounces on first upload         |
                                          +---------------------------------+
```

Image models render warped, misspelled titles; every pure-AI cover tool has this flaw. By generating only the background and compositing real typography on top, COVERFORGE produces legible, reproducible, print-exact covers the competition structurally can't. The "AI" is the cheapest, smallest part; the **engineering around it is the product.**

**Spine width** is deterministic, not guessed: `spine_inches = page_count x paper_factor` (white ~0.002252 in/pg, cream ~0.0025 in/pg, B&W; color ~0.002347 in/pg). Full-wrap width = `(2 x trim_width) + spine + (2 x 0.125 in bleed)`.

## 4. System components (all on existing Everlight rails)

| Layer | Tech | New or reused |
|---|---|---|
| **Frontend** | Next.js on Cloudflare Pages (vantaris shell pattern) | NEW UI, reused shell + deploy path (`cf_pages_direct_upload.py`) |
| **Auth / DB / storage** | Supabase (`jdqqmsmwmbsnlnstyavl`) | NEW tables, reused project |
| **Payments** | Stripe: reuse live `create-checkout` + `stripe-webhook` + `verify-checkout-session` | reused, add `cover_credits` SKUs |
| **Job + credit state** | Supabase tables `cover_jobs`, `credit_ledger` (gem-pack pattern), `covers` bucket, RLS per user | NEW |
| **Text bundle** | Edge function `coverforge-bundle` calling Claude **Haiku** (keywords/categories/blurb/ads) | NEW, cheap, Deno-native |
| **Cover render worker** | **Python on e5-mother** (always-on): image API -> Pillow composite -> Ghostscript PDF/X -> validator -> upload | NEW, the core novel piece |
| **Email** | Resend via `branded_mailer` ("cover ready" + receipts) | reused |

**Why the render worker lives on e5, not an edge function:** print-exact compositing, 300 DPI full-wrap (~3825x2775 px for 6x9), and **PDF/X-1a** export (Ghostscript) exceed Deno edge-function CPU/time limits and aren't Deno-native. e5 is the always-on prod compute host; the phone never renders. The edge function just validates input, debits credit, and enqueues a row in `cover_jobs`; the worker polls, renders, uploads, marks `done`; the frontend polls job status.

**Image model:** tiered (the `ImageProvider` makes it a config swap). **Standard (default) = Flux Dev (fal.ai, ~$0.04) or Imagen 4 Standard (~$0.04)** - because the compositor renders the title text, the model only paints a background scene, so we never pay for text-capable models. **Premium SKU = Nano Banana Pro batch (~$0.067) or GPT Image high**, priced as its own product. **Excluded:** Leonardo (API dead 2026-06-10), Midjourney (no official API), Seedance (video). Full economics in section 11.

## 5. Data flow

**Free preview path (new user, COGS ~2-3 cents):**
1. User fills form (title, author, genre/subgenre, trim size, page count, paper, vibe).
2. `coverforge-create-job` -> no credit charged, flag `tier=free`, insert `cover_jobs` row.
3. Worker renders background + composites -> outputs **watermarked, low-res PNG** + a **partial bundle preview** (e.g. 3 of 7 keywords, blurb teaser).
4. Frontend shows preview + "Unlock print-ready + full bundle" CTA.

**Paid unlock path:**
1. User buys a credit pack (Stripe checkout, reuse existing) -> webhook credits `credit_ledger`.
2. `coverforge-create-job` with `tier=paid` debits 1 credit, enqueues full job.
3. Worker -> background -> composite -> Ghostscript **PDF/X** (front-only ebook + full-wrap paperback) -> **template-dimension validator** -> upload to `covers` bucket -> run `coverforge-bundle` for full text assets -> mark `done`.
4. Frontend unlocks ZIP download; Resend sends "your cover's ready."

A **batch** = one book's asset set: up to 4 cover variations + the full text bundle, for 1 credit.

## 6. Error handling

- **Image API fail** -> retry w/ backoff -> fallback model -> if still failing, **refund the credit** + notify (never silent-fail).
- **Composite / validation fail** -> never deliver a file that fails the dimension checker; re-render once, else refund. The validator is a hard gate on unlock.
- **Stripe webhook** -> idempotent (reuse existing dedupe).
- **Stuck job** -> worker heartbeat + timeout -> auto-refund + alert.
- **Free-tier abuse** -> 1 free preview per verified account; rate-limit by IP + email.

## 7. Testing strategy

- **Golden-file tests** for the compositor: fixed inputs -> output PDF must match exact pixel dims, 300 DPI, bleed, and **computed spine width** per Amazon's formula. This is make-or-break; build it **TDD-first**.
- **Validator unit tests** against Amazon's published trim-size -> cover-dimension table.
- **Bundle chain**: schema-validated Haiku output (exactly 7 keywords, 3 categories, blurb, 5 headlines).
- **E2E**: free-preview path + paid-unlock path in Stripe **test mode** before live keys.
- **Print-accuracy validation (Wk4):** upload real generated wraps to a live KDP draft and confirm zero rejections, the one thing that, if wrong, triggers refunds and kills trust.

## 8. Build sequence (~4 weeks)

| Wk | Focus | Output |
|---|---|---|
| **1** | Render worker + compositor + spine calc + validator (TDD, golden files), the hard novel part | A correct print-ready wrap from a fixed input, validated |
| **2** | Edge functions + `cover_jobs`/`credit_ledger` + Stripe credit SKUs (reuse) + Haiku bundle chain | End-to-end job: input -> rendered files + bundle, paid in test mode |
| **3** | Next.js frontend + free-preview funnel + paywall + download + Resend | A usable site you can run your own books through |
| **4** | Print-accuracy validation on real KDP uploads + polish + go-live | Verified, live, first dogfood books shipped |

## 9. Distribution (launch)

You are your **own first customer**: dogfood on your KDP factory day one; your own published fiction becomes the launch proof. Then authority content (niche/keyword/cover-critique) on X + YouTube, with the **free first cover** as the top-of-funnel hook. The one weakness (no pre-existing author following) is the most fixable on the slate and is offset by self-validation.

## 10. Resolved decisions (Rich approved all defaults, 2026-06-14)

1. **Brand name + domain**: keep `COVERFORGE` as the private working name; lock public name + own domain right before launch (IP / house-of-brands doctrine).
2. **Credit ladder**: free first cover, then $15 / 3 batches as the front door; $29 & $49/mo subs as a later add.
3. **Fiction subgenres seeded first**: romance + thriller + fantasy (the genre prompt library covers these three at launch).
4. **A+ content**: OUT of v1, fast-follow.
5. **Stripe**: reuse the existing Everlight Stripe, add new cover-credit SKUs; split to its own account later if the brand fully separates.
6. **Image model + margins** (added 2026-06-15): standard = Flux Dev / Imagen 4 Standard (compositor adds text so cheap art models suffice); premium = a separate Nano Banana Pro / GPT Image SKU; **variation cap 4 per credit**; COGS gate encoded in `render/pricing.py`. See section 11.

## 11. Unit economics and margin guardrails (locked 2026-06-15)

The credit price must always exceed the API spend per cover (the "trades clear costs and grow" law applied to SaaS). Researched current June-2026 image-API pricing to lock this.

**Per-cover P&L (standard tier):** ~$0.03 background image + ~$0.002 Haiku bundle + ~$0.25 amortized Stripe fee (on a $15 / 3-batch pack) = **~$0.28 COGS** vs **$5.00 charged** = **~94% gross margin**.

**The gate (enforced in `render/pricing.py`):** `price_per_cover >= cogs_per_cover / (1 - target_margin)`. Floor at 90% margin + $0.28 COGS = $2.80; we charge $5, so it clears with room.

**Three hard guardrails (encode, never trust):**
1. **1 credit = 1 batch, variations CAPPED at 4.** Regenerations cost another credit. NEVER offer "unlimited" anything whose COGS scales with use - it is the one thing that flips a 94% margin negative.
2. **Premium models are a separate, higher-priced SKU**, sized so the premium model's COGS still clears the gate.
3. **Free tier rate-limited** (1 free cover per verified account) - uncapped free generation is the only real COGS leak.

**Legal-safety note:** Adobe Firefly is the only image API offering copyright indemnification (trained on licensed data). Hold in reserve if reselling-art liability becomes a concern; not needed for v1.

## 12. Out of scope (YAGNI for v1)

Series/box-set wraps, audiobook covers, hardcover case wraps, A+ content modules, multi-language, team seats, the DISPO/LAUNCHPACK products (queued separately on the same rails).
