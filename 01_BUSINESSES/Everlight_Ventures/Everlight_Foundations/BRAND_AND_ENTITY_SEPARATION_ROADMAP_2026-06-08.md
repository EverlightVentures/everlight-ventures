# Everlight Ventures -- Brand & Entity Separation Roadmap
**Status:** ROADMAP (no execution yet -- operator chose "keep as roadmap" 2026-06-08)
**Decision owner:** Rich (operator) / Lucrex
**Contributors:** Everlight Content Director (brand) - Theo Briggs GC (legal/entity) - Everlight Architect (infra)
**Casino model (operator-confirmed):** Sweepstakes / redeemable coin

---

## The problem (verified from live code, not hypothetical)
One Next.js app (`06_DEVELOPMENT/vantaris/`, codename **Vantaris**) deploys to Cloudflare Pages project `everlightventures` = **everlightventures.io**. That single domain + single Supabase project (`jdqqmsmwmbsnlnstyavl`) + single Stripe currently serves **three incompatible legal regimes at once**:

- **B2B / venture:** `/hivemind`, `/wholesale`, `/logistics`, `/onyx`, `/publishing`, `/find-tools`, `/list-your-tool`, `/sell`, `/him-loadout`
- **Casino (sweepstakes/redeemable):** `/play/blackjack|crash|dice|mines|plinko|roulette`, `/tables`, `/wallet`, `/redeem`, `/rewards`, `/fairness`
- **Crypto gaming:** `/alley-kingz`, `/arcade`, `$BCARDD`

This is not a 2-audience branding smell. It is **B2B services + gambling + crypto** under one entity, one domain, one DB, one Stripe.

## The verdict
**House of brands, not branded house.** One landlord, multiple doors.
> **One repo. Separate domains. Two databases. Separate legal entities for gambling and crypto.** That is the whole separation.

Operator instinct ("this feels messy") was correct; the real issue is liability + payment-processor exposure, which is bigger than branding.

---

## MUST / SHOULD / SKIP

| Layer | Verdict | Why |
|---|---|---|
| **Legal entities** | **MUST** -- separate LLC for gambling, separate LLC for crypto; discrete LLCs (NOT series -- CA) | One LLC = one liability pool; a gambling action or SEC look at $BCARDD reaches consulting cash + personal assets (veil-pierce risk) |
| **Stripe** | **MUST** -- pull gambling onto its own account/entity FIRST | Stripe bans unlicensed gambling; a review freezes ALL funds in the account, B2B receivables included |
| **Domains** | **SHOULD** (cheap, do it) -- separate apex + separate Pages project per brand | Clean deploys, SEO firewall, regulatory distinctness |
| **Supabase** | **SHOULD** -- **2 projects** (B2B vs gaming/crypto money-data) | Split wallets/balances/on-chain/KYC from B2B leads; different breach + compliance class. Casino vs $BCARDD = schemas+RLS within the gaming project for now |
| **Repos** | **SKIP** -- keep the monorepo | Brand separation != code separation. One repo, multiple deploy targets. Alley Kingz already its own repo for a real reason (Solana/Metaplex stack) -- the only justified split |

**Core insight:** *legal separation* and *code separation* are different axes. Four legally-isolated brands can run from one repo. Don't split repos to solve a brand problem.

---

## Brand topology
- **everlightventures.io** = B2B house ONLY (Hive Mind, Wholesale, Logistics, Onyx, Publishing, tool marketplace, HIM Loadout) + a clean **"Ventures / Portfolio"** page that *links out* to the games (showcase, never storefront).
- **Alley Kingz** -> own brand + domain (`alleykingz.gg`/`.com`), footer "an Everlight venture" only. Already on `alley-kingz.pages.dev`.
- **Casino** -> own gaming brand + domain. **Do NOT name it "Everlight Casino."**
- **$BCARDD** -> own apex.

## Sweepstakes / redeemable-coin legal note (operator-confirmed model)
"No purchase necessary" free entry is **not a safe harbor** -- contested + under active state-AG attack 2024-2026. Redeeming into **$BCARDD** stacks all three risks: gambling (consideration/value), **money-transmitter/MSB** (coin<->value conversion), **securities/Howey** (redemption utility + cap targets = expectation of profit).
**Lever to lower the bar:** decouple the coin from the redemption rail -- redeem for gift cards / merch / play-value, keep $BCARDD separate. Splits the gambling question from the securities question.

---

## Remediation order (highest risk first)
1. **Casino off shared Stripe + main domain** (URGENT) -- *Architect ships deploy split; Theo/Wen stand up entity*
2. **Form gaming LLC** -- *Wen Marsh*
3. **Form crypto LLC**, move $BCARDD + AK NFT there **before** more public marketing -- *Wen + securities counsel*
4. **Form holding parent**, assign subsidiaries -- *Wen*
5. **Split Supabase** -- gaming/money data -> own project; freeze writes, snapshot, migrate, verify row counts, flip (drift kills you if rushed) -- *Architect*
6. **Rewrite everlightventures.io** for ONE buyer + add Portfolio link-out -- *Content Director*

## Shared infra that can stay shared (reuse without re-mixing)
Design tokens (gold `#D4AF37` / Playfair-Inter), the `content_tools` branded pipeline (outbound-only), an internal shared-component package, the *login component* (NOT the user table). **Never** share one auth user-pool across regulated + B2B.

## Entity map (target)
- **Holding parent:** Everlight Ventures Holdings
- **Under parent / single OpCo:** consulting + Onyx + Hive Mind SaaS + publishing
- **Own LLC:** Wholesale (real-estate licensing regime)
- **Own LLC (MUST):** Gaming/casino
- **Own LLC (MUST), separately counseled:** Crypto ($BCARDD / Alley Kingz NFT)

## Resolved conflict
Architect = 2 Supabase projects (combined gaming/crypto); Theo = crypto fully isolated as its own entity. **Resolution:** 2 projects now for blast-radius; when $BCARDD becomes its own counseled entity, give it its own project so data boundary = legal boundary. Phase 2.

## Dropped
- Series LLC (CA doesn't cleanly recognize).
- One SSO across everything (a casino player must not exist in the corporate auth table).

## Follow-up owners
- **Wen Marsh** -- formation, CA reinstatement, intercompany + capitalization agreements (so the veil holds)
- **Priya** -- privacy/data-separation + consent gating once DBs split
- **Theo Briggs** -- long-form risk memo to audit log; securities-counsel referral for $BCARDD

*Advisory, not formal legal opinion. Take the entity map to a licensed attorney before formation.*
