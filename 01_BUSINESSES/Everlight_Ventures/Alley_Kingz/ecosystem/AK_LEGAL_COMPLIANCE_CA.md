# ALLEY KINGZ -- California + US Monetization Legal-Compliance Memo

**Prepared for:** Operator (Everlight Ventures), solo launch from California
**Subject:** Proactive legal protection for Alley Kingz monetization (soft currency + real-money "gems" via Stripe + seasonal battle pass + randomized chests)
**Date:** 2026-06-25
**Law current as of:** June 2026 (every point web-grounded below)

> **NOT LEGAL ADVICE.** This is informational compliance guidance assembled from public sources for planning purposes only. It is not legal advice and does not create an attorney-client relationship. Several items below are flagged as requiring a licensed California attorney before launch. Treat this memo as a build-and-budget checklist, not a substitute for counsel.

---

## (a) TL;DR -- Risk Summary

Alley Kingz sits in the single most-scrutinized corner of mobile monetization in 2026: **a free-to-play game with paid randomized chests, an audience that will skew under-18, real-money checkout run direct from California, and (today) a blanket "non-refundable / no cash value" stance.** None of that is illegal, but the combination is exactly the profile regulators are hunting.

**Biggest single risk: the gem-bought randomized "Crates" (and "Lucky Draw") played by minors, sold without published odds and without a parental-consent / refund path.** In January 2025 the FTC hit HoYoverse (Genshin Impact) with a **$20 million settlement** over loot-box mechanics that (1) misled players on real-money cost, (2) hid item odds, and (3) let minors buy without parental consent. The order forced clear odds disclosure, transparent currency exchange rates, simplified purchasing, and **parental consent for buyers under 16**. That order is the template the FTC will reuse, and it does not need a loot-box statute to do it -- it runs on Section 5 (unfair/deceptive) authority. AK's gem chests are functionally identical to what got fined. ([FTC / HoYoverse](https://natlawreview.com/article/us-regulation-loot-boxes-heats-announcement-new-legislation), [Loot Box Laws 2025](https://blog.promise.legal/loot-box-laws-game-developers/))

Stacked on top of that federal exposure:

- **No US/CA loot-box statute exists** (every bill since 2018 failed), but **Apple and Google both require pre-purchase odds disclosure**, and **California minors can legally disaffirm (undo) their purchases** -- a blanket no-refund policy has already drawn class actions against Apple, Supercell (Clash), and Niantic. ([Minor disaffirmance](https://www.faegredrinker.com/en/insights/publications/2024/3/does-californias-right-for-minors-to-disaffirm-contracts-apply-to-online-purchases))
- **California's Age-Appropriate Design Code is partly alive again** as of the Ninth Circuit's **March 12, 2026** ruling -- high-privacy-by-default for minors, age estimation, and geolocation limits are now enforceable. ([9th Cir. ruling](https://www.hklaw.com/en/insights/publications/2026/03/ninth-circuit-issues-mixed-ruling-on-california-age-appropriate-design))
- **COPPA's 2025 amendments are live** (effective June 23, 2025; full compliance by April 22, 2026) and expand what counts as kids' data and when you need separate parental consent. ([COPPA 2025](https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule))
- **Stripe's own rules** restrict virtual currency: it must be non-redeemable, non-exchangeable for real money, and confined to the game -- which means the card **trading** feature must never become a cash-out path or Stripe can terminate the account (independent of any law). ([Stripe restricted businesses](https://stripe.com/en-mx/legal/restricted-businesses))

**Good news baked into the current design:** gems are already named "gems" (Stripe-compliant), the battle pass is a **one-time 800-gem unlock with no auto-renew** (which sidesteps almost all of California's Automatic Renewal Law), and a **deterministic Card Shop already exists** (buy the exact card with gems) sitting right next to the randomized chests. Those three facts cut the risk a lot. The work is mostly disclosure, age handling, a refund path, and a clean privacy/ToS layer -- all buildable by a solo operator.

**Net posture:** Launchable with discipline. Do not ship paid randomized chests to an under-18 audience until odds are published, real-money pricing is unmistakable, an age gate + parental-refund path exist, and the privacy/ToS pack is posted.

---

## (b) MUST-DO Checklist (implementable, mapped to AK's design)

### Loot boxes / randomized chests
- [ ] **Publish odds for every randomized purchase.** The weights already live in code (`economy.js`: `DROP_W = Common 70 / Rare 22 / Epic 7 / Mythic 1`; `CHEST_TABLE` per-tier floors + `diamond.mythicChance 0.05`). Surface them in-product on the **Crates** and **Lucky Draw** tabs, on a "View drop rates" link reachable **before** purchase. This is mandatory for App Store / Google Play and is the cure for the HoYoverse problem.
- [ ] **Keep and feature the deterministic alternative.** AK already has `gemBuyBtn` / `gem-buy-copy` (Card Shop: Common 2 / Rare 10 / Epic 50 / Legendary 500 / Mythic 2000 gems). Make sure every chest screen visibly points to "or buy this card directly." Pairing a guaranteed-purchase path with each randomized path is the strongest defensive design choice.
- [ ] **Show the real-money cost trail.** When a player spends gems on a chest, the UI should make the gem-to-dollars relationship discoverable (gem packs already disclose `$4.99 = 500 gems`, etc.). The FTC's HoYoverse order specifically faulted obscured exchange rates.
- [ ] **Confirm contents are in-game only.** `CHEST_TABLE` grants cards/coins/scrap/keys -- all in-game value, never cash. Keep it that way; do not let chest output become tradable for real money.
- [ ] **Earned vs. paid: keep them separable.** Match-earned chests (opened with earned keys) are far lower-risk than gem-bought chests. Keep the earned path generous so the paid chest is never the only route to content.

### Minors / youth
- [ ] **Add a neutral age gate** (date-of-birth entry, not a yes/no "are you 18") at first run / before any purchase. Drives COPPA, AADC, and CCPA-minor handling.
- [ ] **Privacy-by-default for minors.** Per the now-enforceable AADC provisions: high-privacy default settings for users estimated to be minors, and no collection/use of **precise geolocation** for minors without a clear need + signal. AK collects via Google OAuth sign-in -- keep minor data minimal.
- [ ] **No behavioral / targeted ads to minors, no selling or "sharing" minor data.** Under CCPA/CPRA you may not sell or share the personal info of a known under-16 without opt-in (under-13 = verified parent; 13--15 = the teen). Simplest compliant posture: **do not sell or share any user data at all**, and say so.
- [ ] **Under-13 path = COPPA.** If you knowingly collect data from under-13s you need verifiable parental consent and a COPPA-specific notice. Practical solo-operator move: **gate sign-in / purchases to 13+** (and require parental consent for purchases under 16, mirroring the FTC's HoYoverse remedy) so you avoid the heaviest COPPA machinery.
- [ ] **Parental refund path for minors.** Because California minors can disaffirm purchases, publish a simple "parent request a refund for a minor's purchase" contact and honor it. This is your shield against the Apple/Supercell/Niantic-style class action.
- [ ] **Age-appropriate ToS/privacy language** if the audience includes children (AADC, now enforceable): plain-language version of the rules a kid can understand.

### Auto-renewing subscriptions (battle pass)
- [ ] **Keep the Alley Pass a one-time per-season purchase. Do NOT auto-renew.** Current code (`ak-pass`, `pass.js`) already does this -- 800 gems, one season, manual re-buy. This avoids California's ARL almost entirely. **Recommended: stay one-time.**
- [ ] If you ever switch to a real-money auto-renewing subscription (monthly VIP, etc.), you trigger California's ARL (AB 2863, effective July 1, 2025) in full: affirmative consent to the renewal terms, clear pre-purchase disclosure, **cancel via the same channel you signed up through**, annual reminders, 7--30 day notice before any fee change, and keep consent records 3 years. Treat that as a separate build with attorney sign-off.

### Dark patterns
- [ ] **Symmetry in choice.** Any opt-out / cancel / decline path must be as short and easy as the buy/opt-in path (CPRA requirement; CPPA enforced this in 2024). No buried "cancel," no double-negatives, no pre-checked consent.
- [ ] **No fake urgency or fake discounts.** The "limited drop, gone in 48h" scarcity tactic in `PRICING_STRATEGY.md` is fine **only if the scarcity is real**. A countdown that resets, or a "was $X" price that was never charged, is a deceptive dark pattern (FTC + CA).
- [ ] **Honest buttons.** Per CARU, purchase buttons must make real-money cost obvious ("Buy 500 Gems -- $4.99," not just "Get" or "Unlock"). AK's gem tiles already show price; keep that discipline on every spend surface.

### Virtual currency (ToS / EULA)
- [ ] **Ship a EULA / ToS that states gems and all in-game items: have no cash value, are a revocable limited license (not property), are non-transferable for real money, and are non-refundable except where law requires** (the minor-disaffirmance carve-out above). AK's shop copy already says "in-game value only -- never cashable"; formalize it in a posted ToS.
- [ ] **Stripe compliance:** keep the currency named "gems/coins/scrap" (compliant), never imply convertibility to cash, and **never let the `ak-trading` card-trade feature touch real money.** Stripe prohibits exchangeable virtual currency; an RMT path can get the merchant account killed regardless of the law.
- [ ] **Gift-card / stored-value:** do not market gem packs as "gift cards," "store credit," or "wallet balance," and do not let unused gems be cashed out -- that's what keeps gems out of California's gift-certificate cash-back rules. (Attorney sign-off item below.)

### Consumer protection / refunds / advertising
- [ ] **Clear, all-in pricing before purchase** -- shown in dollars at the gem-pack level and in gems at the item level, with the conversion discoverable.
- [ ] **Written refund policy** that is honest (states the no-refund default AND the legally-required exceptions: minors, billing errors, non-delivery).
- [ ] **No deceptive "sale" framing.** If `original_price_usd` is shown as a strikethrough, it must be a genuine former price.
- [ ] **CARU ad rules** if kids are in the audience: clearly separate ads from gameplay, make exit/dismiss of any ad obvious, and label real-money purchases plainly.

### Privacy baseline
- [ ] **Post a CCPA/CPRA + CalOPPA-compliant Privacy Policy** at a visible link (footer of alleykingz.online and in-game). Must list: categories of data collected (account/Google OAuth ID, gameplay, device, purchase records via Stripe), purposes, whether you sell/share (say "we do not sell or share"), retention, and the consumer rights (know, delete, correct, opt-out of sale/share, limit sensitive-info use).
- [ ] **Provide the rights mechanisms:** an email/web form to request know/delete/correct, and -- only if you ever sell or share -- a "Do Not Sell or Share My Personal Information" link. If you never sell/share, you can state that instead.
- [ ] **Data minimization + retention limit** (COPPA 2025 now requires a written retention policy for kids' data; good practice for all). Collect only what the game needs.
- [ ] **Date-stamp the policy and keep a changelog.**

---

## (c) Per-Topic Detail + Current-Law Citations

### 1. Loot boxes / randomized purchases

**Do AK's chests count as loot boxes?** Yes -- for the **gem-purchased** ones. A "loot box" is any mechanism that, for a purchase, returns a **randomized** virtual item. AK's shop "Crates" tab sells chest SKUs for gems with an `is_random` flag, and gems are bought with real money via Stripe; the `CHEST_TABLE` in `economy.js` returns randomized cards/coins/scrap with rarity floors and a `mythicChance`. That is a textbook loot box. The "Lucky Draw" tab is gacha and counts too. **Match-earned chests opened with earned keys are lower risk** (no purchase triggers the randomness) but are still randomized and benefit from the same odds transparency.

**Platform policy (this binds you the moment you list on a store):**
- **Apple App Store Guideline 3.1.1:** "Apps offering 'loot boxes' or other mechanisms that provide randomized virtual items for purchase must disclose the odds of receiving each type of item to customers prior to purchase." ([Fenwick](https://www.fenwick.com/insights/publications/apple-now-requires-disclosure-of-loot-box-odds), [Sheppard Mullin / JDSupra](https://www.jdsupra.com/legalnews/apple-requires-disclosure-of-odds-for-48923/))
- **Google Play:** apps offering randomized virtual items from a purchase must "clearly disclose the odds of receiving those items in advance of purchase"; a game without it will not pass review. ([Fenwick](https://www.fenwick.com/insights/publications/google-play-now-requires-disclosure-of-loot-box-odds), [Game Developer](https://www.gamedeveloper.com/business/games-on-the-google-play-store-now-required-to-disclose-loot-box-odds))
- **Nuance for AK as a web/PWA game:** Apple/Google store *policies* technically bind apps distributed *through those stores*. A pure web game on alleykingz.online billed via Stripe is not under store review today. **But** (1) the FTC standard below applies regardless, (2) the moment AK is wrapped as a TWA/native app or listed in either store, no-odds = rejection, and (3) odds disclosure is now the global market norm. **Build odds disclosure now.**

**Is there CA or federal loot-box law as of 2026?** **No enacted statute.** The federal "Protecting Children from Abusive Games Act" (Hawley, 2019) failed; state bills in Hawaii, Minnesota, Washington, and California (warning-label proposals) all failed. As of 2026 no US state has an enacted loot-box law. ([Loot Box Laws by Jurisdiction 2025](https://blog.promise.legal/loot-box-laws-game-developers/), [2026 regulation overview](https://programminginsider.com/loot-boxes-regulation-and-where-the-line-sits-in-2026/))

**The real teeth -- FTC Section 5:** In **January 2025 the FTC settled with Cognosphere/HoYoverse (Genshin Impact) for $20 million** over loot boxes that misled players on real-money cost and odds and targeted minors. The order requires clear odds disclosure, transparent virtual-currency exchange rates, simplified purchasing, and **parental consent for purchases by players under 16.** This is how loot boxes get regulated in the US right now -- consumer-protection enforcement, no statute required. ([Nat Law Review](https://natlawreview.com/article/us-regulation-loot-boxes-heats-announcement-new-legislation), [Gamma Law -- consumer protection analysis](https://gammalaw.com/how-does-us-consumer-protection-law-apply-to-video-game-loot-boxes-and-gacha-mechanics/))

**Minor protections (loot-box specific):** mirror the FTC remedy -- odds published, real-money cost unmistakable, and parental consent for under-16 purchases.

### 2. Minors / youth

**California Age-Appropriate Design Code (AADC / CAADCA) -- current status:** Litigated and **partially revived.** On **March 12, 2026**, the Ninth Circuit (NetChoice v. Bonta) issued a split ruling that vacated the blanket injunction. **Now enforceable / not enjoined:** age-estimation requirement, strict limits on collecting/sharing minors' **precise geolocation**, **high-privacy default settings** for minors, age-appropriate-language privacy policy + ToS, an "obvious signal" when a parent is monitoring, and accessible tools for kids/parents to exercise privacy rights. **Still blocked:** the Data Protection Impact Assessment (DPIA) mandate and certain data-use/dark-pattern provisions (struck on vagueness / compelled-speech grounds). Litigation continues on remand and the state has previously agreed to stay enforcement, so the enforceable set could shift again. **Build to the enforceable provisions now.** ([Holland & Knight](https://www.hklaw.com/en/insights/publications/2026/03/ninth-circuit-issues-mixed-ruling-on-california-age-appropriate-design), [DLA Piper](https://privacymatters.dlapiper.com/2026/03/the-ninth-circuits-latest-caadca-ruling-navigating-an-evolving-compliance-landscape/), [Loeb & Loeb](https://www.loeb.com/en/insights/passle/2026/03/ninth-circuit-rules-parts-of-california-ageappropriate-design-code-are-effective-and-enforceable))

**COPPA (under-13) -- 2025 amendments are LIVE:** The FTC published final amendments April 22, 2025; **effective June 23, 2025; full compliance required by April 22, 2026.** Key changes: expanded "personal information" definition (now includes biometric + government identifiers), **separate verifiable parental consent before disclosing a child's data to third parties**, text-message consent now allowed, and new data-retention limits (written retention policy, no indefinite holding). If you knowingly collect under-13 data you owe a COPPA notice + verifiable parental consent. ([Federal Register](https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule), [White & Case](https://www.whitecase.com/insight-alert/unpacking-ftcs-coppa-amendments-what-you-need-know), [Taft -- effective June 23 2025](https://www.privacyanddatasecurityinsight.com/2025/05/childrens-online-privacy-protection-act-amendments-effective-june-23-2025/))

**CCPA / CPRA minors' data -- the operative rule is UNDER-16 (not under-18):** A business may not **sell or share** the personal information of a consumer it knows is under 16 without opt-in consent -- for under-13 the parent must opt in; for 13--15 the teen may opt in. Statutory penalty up to **$7,500 per violation involving a child under 16.** **Important fact-check:** AB 1949, the 2024 bill that would have raised this to **under-18**, was **vetoed by Governor Newsom on September 24, 2024 and did NOT become law** -- so under-16 remains the rule despite some secondary sources claiming otherwise. ([Hunton -- veto](https://www.hunton.com/privacy-and-information-security-law/california-state-legislature-passes-childrens-privacy-amendments-to-the-ccpa-pending-governors-signature), [CA AG -- CCPA](https://oag.ca.gov/privacy/ccpa), [DataGrail -- children's data](https://www.datagrail.io/blog/data-privacy/california-privacy-ccpa-cpra-childrens-data-protection/))

**What a game likely played by under-18s should implement:** neutral age gate; privacy-by-default for minors; no precise-geolocation collection on minors; no behavioral ads to kids; no sale/sharing of minor data (easiest: no sale/sharing at all); verifiable parental consent for under-13 (or gate to 13+); parental consent for under-16 purchases (FTC HoYoverse template); plain-language rules for kids.

### 3. Auto-renewing subscriptions (battle pass)

**California Automatic Renewal Law (ARL), as amended by AB 2863 -- effective July 1, 2025.** If AK ever sells a real-money auto-renewing subscription, it must: get **express affirmative consent** to the renewal terms (and not bury anything that undermines that consent); disclose the renewing terms clearly and conspicuously before charge; now also cover **free-to-pay / free-trial conversions**; allow cancellation **through the same medium used to subscribe**; send **annual reminders** of what's renewing, the amount, and how to cancel; give **7--30 days' notice before any fee change**; and **retain proof of consent for 3 years**. ([Fenwick](https://www.fenwick.com/insights/publications/california-tightens-requirements-for-automatically-renewing-subscriptions), [Barnes & Thornburg](https://btlaw.com/en/insights/alerts/2025/california-expands-automatic-renewal-law-new-requirements-now-in-effect), [Davis Wright Tremaine](https://www.dwt.com/insights/2024/10/ab-2863-updates-california-automatic-renewal-law))

**Federal FTC "click-to-cancel" status:** The FTC's revised Negative Option / "Click-to-Cancel" Rule was **vacated by the Eighth Circuit on July 8, 2025** (procedural defect -- no preliminary regulatory analysis) and is **not currently in effect.** However, the FTC submitted a new ANPRM on **January 30, 2026** to revive negative-option regulation, and the FTC + state AGs still pursue deceptive-subscription practices under existing authority. **California's ARL governs you regardless of the federal rule's status.** ([Mayer Brown](https://www.mayerbrown.com/en/insights/publications/2025/07/click-to-cancelled-eighth-circuit-vacates-federal-trade-commissions-revised-negative-option-rule), [Crowell -- FTC revival](https://www.crowell.com/en/insights/client-alerts/clicking-all-the-right-boxes-ftc-moves-to-revive-click-to-cancel-rule-following-eighth-circuit-vacatur))

**Recommendation: keep the Alley Pass one-time per season (as built).** Auto-renew adds ARL exposure, cancellation-flow build, reminder emails, and recordkeeping for a battle pass that re-buys naturally each season anyway. The one-time gem unlock is the lower-risk, simpler, and player-friendlier choice. Only go auto-renew with counsel and a full ARL build.

### 4. Dark patterns

**CPRA defines a dark pattern** as "a user interface designed or manipulated with the substantial effect of subverting or impairing user autonomy, decision-making, or choice." **Consent obtained through dark patterns is not valid consent.** The CPPA's September 2024 enforcement advisory stressed: **symmetry in choice** (the privacy-protective / cancel path may not be longer or harder than the opposite), easy-to-understand language, easy-to-execute actions, and no confusing or manipulative architecture. ([CPPA enforcement advisory](https://www.hunton.com/privacy-and-cybersecurity-law-blog/cppa-issues-enforcement-advisory-regarding-dark-patterns), [Davis Wright Tremaine](https://www.dwt.com/blogs/privacy--security-law-blog/2024/09/california-guidance-on-dark-patterns-and-privacy))

**AK-specific UI/UX to avoid:** no pre-checked purchase/consent boxes; no decline option hidden behind a tiny/greyed link; cancel/opt-out must be as easy as buy/opt-in; **countdown timers and "limited" scarcity must reflect real limits** (the `PRICING_STRATEGY.md` "gone in 48h" tactic is legal only if it's true); **strikethrough "was $X" prices must be genuine former prices**; no nagging confirm-shaming ("No, I don't want to be a King"). Note: some AADC dark-pattern provisions are currently enjoined, but the **CPRA** dark-pattern rules above are independently in force.

### 5. Virtual currency (ToS / EULA + gift-card concerns)

**ToS/EULA must establish:** gems and all in-game items are a **limited, revocable license -- not the player's property**; have **no cash value**; are **non-transferable for real-world money**; and are **non-refundable except as required by law** (minor disaffirmance, billing errors, non-delivery). This is standard and AK's shop copy already gestures at it ("in-game value only -- never cashable"); it needs to live in a posted ToS, not just UI microcopy.

**Stripe's rules add a hard constraint independent of any statute:** Stripe permits selling in-game currency only if you are the operator of the virtual world (AK is -- fine), but **prohibits virtual currency that can be exchanged for real money**, and recommends fictional non-redeemable names ("Gems," "Coins") -- which AK uses. **Implication: the `ak-trading` card-trade feature must never enable cashing out or real-money trades.** Stored-value/"wallet" framing is also prohibited. Violating this risks losing the merchant account, separate from legal risk. ([Stripe -- Prohibited & Restricted Businesses](https://stripe.com/en-mx/legal/restricted-businesses), [Stripe Acceptable Use](https://stripe.com/legal/consumer/acceptable-use))

**California gift-card / stored-value concern:** California's gift-certificate law (Civil Code 1749.5) gives cash-back and no-expiration rights to "gift certificates." In-game currency usable **only inside the game** and not redeemable for cash/goods beyond it generally falls outside that definition -- but the safe posture is: don't market gems as gift cards or wallet credit, don't allow cash-out, and don't let gems buy real-world goods. **Confirm with counsel** (attorney list below).

### 6. Consumer protection / refunds / advertising

**Clear pricing:** show the real-money price before purchase (dollars at pack level, gems at item level, conversion discoverable). **Refunds:** publish an honest policy -- a no-refund default is allowed, but it **cannot override** the legally required exceptions, the biggest of which is the **California minor's right to disaffirm**. Courts have rejected attempts (Apple in-app litigation) to treat individual in-game buys as outside disaffirmance; Apple settled with refunds/credits, and active class actions target Supercell (Clash gems) and Niantic (Pokemon Go) over exactly this no-refund-to-minors posture. **Build a parent-refund request path.** ([Faegre Drinker](https://www.faegredrinker.com/en/insights/publications/2024/3/does-californias-right-for-minors-to-disaffirm-contracts-apply-to-online-purchases), [classaction.org -- Supercell](https://www.classaction.org/news/clash-of-clans-maker-refuses-to-refund-minors-for-in-game-purchases-class-action-alleges))

**No deceptive "sale" framing:** genuine former prices only; no perpetual "limited-time" that never ends. **CARU (kids' advertising, BBB National Programs):** apps/games for kids must not use deceptive or manipulative tactics to drive purchases, must make exit from any ad clear and conspicuous, and **must make clear that a purchase involves real currency** -- "Buy for $4.99 -- Ask a Parent First" rather than "Get" or "Unlock." ([CARU revised guidelines](https://natlawreview.com/article/caru-issues-updated-guidelines-children-s-advertising), [BBB -- in-app ads & kids](https://bbbprograms.org/media/insights/blog/in-app-ads-kids))

### 7. Privacy baseline

A California-facing game that collects personal info (AK does -- Google OAuth account IDs, gameplay/profile data, device data, Stripe purchase records) must post a **CCPA/CPRA + CalOPPA-compliant Privacy Policy** that discloses: the categories of personal info collected and their sources; the business/commercial purposes; whether the info is sold or shared (state plainly if not); retention periods; and the consumer rights -- to know, delete, correct, opt out of sale/sharing, and limit use of sensitive personal info -- plus how to exercise them. If you sell or share, you must post a "Do Not Sell or Share My Personal Information" link and honor opt-out preference signals; **if you never sell or share, say so** and you avoid that machinery. Add a data-retention statement (now expected under the 2025 COPPA amendments for kids' data and good practice generally), date the policy, and keep it linked from both the site footer and in-game. ([CA AG -- CCPA](https://oag.ca.gov/privacy/ccpa), [DataGrail](https://www.datagrail.io/blog/data-privacy/california-privacy-ccpa-cpra-childrens-data-protection/))

---

## (d) Needs a Licensed California Attorney BEFORE Launch

1. **Final ToS / EULA + Privacy Policy review.** Use a games/privacy attorney (or a vetted template service) to finalize the posted documents -- especially the license grant, no-cash-value / non-transferable language, the arbitration/class-waiver clause, and the limitation of liability. Templates are fine to draft from; a lawyer should bless the final.
2. **Minor refund / disaffirmance policy.** How far the no-refund default holds against California's minor-disaffirmance doctrine, and exactly what the parent-refund process must say and do, is a litigated, fact-specific area -- get counsel given the live Supercell/Niantic class actions.
3. **Loot-box / randomized-chest design sign-off.** Whether AK's specific gem-chest + odds-disclosure + parental-consent setup is defensible against an FTC Section 5 theory (post-HoYoverse) is a judgment call a lawyer should make before you sell paid chests to a youth audience.
4. **AADC applicability + minor-handling.** Whether AK is "likely to be accessed by children," which now-enforceable AADC provisions attach, and how to implement age estimation without over-collecting data -- have counsel confirm given the still-moving March 2026 ruling.
5. **COPPA exposure decision.** If you choose to allow under-13 users, the verifiable-parental-consent mechanism and COPPA notice need legal review; if you gate to 13+, counsel should confirm the gate is sufficient.
6. **Virtual-currency / gift-card classification.** Confirm gems do not fall under California stored-value / gift-certificate rules (Civil Code 1749.5) and that the `ak-trading` feature design avoids creating a regulated money-transmission or real-money-trade situation.
7. **Auto-renew (only if you change the pass).** If the battle pass or any product ever becomes a real-money auto-renewing subscription, a full California ARL (AB 2863) compliance build needs attorney sign-off before it goes live.
8. **Sweepstakes / "Lucky Draw" framing.** Confirm the "Lucky Draw" gacha mechanic is structured as a purchase-of-randomized-item (with odds) and not an unlawful lottery/sweepstakes (consideration + chance + prize) under California law.

---

## Sources

**Loot boxes / platform policy / FTC**
- Apple loot-box odds disclosure (Guideline 3.1.1): https://www.fenwick.com/insights/publications/apple-now-requires-disclosure-of-loot-box-odds | https://www.jdsupra.com/legalnews/apple-requires-disclosure-of-odds-for-48923/
- Google Play loot-box odds disclosure: https://www.fenwick.com/insights/publications/google-play-now-requires-disclosure-of-loot-box-odds | https://www.gamedeveloper.com/business/games-on-the-google-play-store-now-required-to-disclose-loot-box-odds
- US/CA loot-box legislative status (none enacted): https://blog.promise.legal/loot-box-laws-game-developers/ | https://programminginsider.com/loot-boxes-regulation-and-where-the-line-sits-in-2026/
- FTC / HoYoverse $20M loot-box settlement + Section 5: https://natlawreview.com/article/us-regulation-loot-boxes-heats-announcement-new-legislation | https://gammalaw.com/how-does-us-consumer-protection-law-apply-to-video-game-loot-boxes-and-gacha-mechanics/

**Minors / youth**
- 9th Circuit AADC ruling (Mar 12, 2026): https://www.hklaw.com/en/insights/publications/2026/03/ninth-circuit-issues-mixed-ruling-on-california-age-appropriate-design | https://privacymatters.dlapiper.com/2026/03/the-ninth-circuits-latest-caadca-ruling-navigating-an-evolving-compliance-landscape/ | https://www.loeb.com/en/insights/passle/2026/03/ninth-circuit-rules-parts-of-california-ageappropriate-design-code-are-effective-and-enforceable
- COPPA 2025 amendments (effective Jun 23, 2025; comply by Apr 22, 2026): https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule | https://www.whitecase.com/insight-alert/unpacking-ftcs-coppa-amendments-what-you-need-know | https://www.privacyanddatasecurityinsight.com/2025/05/childrens-online-privacy-protection-act-amendments-effective-june-23-2025/
- CCPA/CPRA minors (under-16 opt-in) + AB 1949 veto: https://oag.ca.gov/privacy/ccpa | https://www.datagrail.io/blog/data-privacy/california-privacy-ccpa-cpra-childrens-data-protection/ | https://www.hunton.com/privacy-and-information-security-law/california-state-legislature-passes-childrens-privacy-amendments-to-the-ccpa-pending-governors-signature

**Subscriptions / auto-renew**
- CA ARL / AB 2863 (effective Jul 1, 2025): https://www.fenwick.com/insights/publications/california-tightens-requirements-for-automatically-renewing-subscriptions | https://btlaw.com/en/insights/alerts/2025/california-expands-automatic-renewal-law-new-requirements-now-in-effect | https://www.dwt.com/insights/2024/10/ab-2863-updates-california-automatic-renewal-law
- FTC click-to-cancel vacated (Jul 8, 2025) + 2026 revival: https://www.mayerbrown.com/en/insights/publications/2025/07/click-to-cancelled-eighth-circuit-vacates-federal-trade-commissions-revised-negative-option-rule | https://www.crowell.com/en/insights/client-alerts/clicking-all-the-right-boxes-ftc-moves-to-revive-click-to-cancel-rule-following-eighth-circuit-vacatur

**Dark patterns**
- CPPA dark-pattern enforcement advisory (Sept 2024): https://www.hunton.com/privacy-and-cybersecurity-law-blog/cppa-issues-enforcement-advisory-regarding-dark-patterns | https://www.dwt.com/blogs/privacy--security-law-blog/2024/09/california-guidance-on-dark-patterns-and-privacy

**Virtual currency / Stripe / refunds / kids' ads**
- Stripe restricted businesses + acceptable use (virtual currency): https://stripe.com/en-mx/legal/restricted-businesses | https://stripe.com/legal/consumer/acceptable-use
- California minor disaffirmance of in-app purchases: https://www.faegredrinker.com/en/insights/publications/2024/3/does-californias-right-for-minors-to-disaffirm-contracts-apply-to-online-purchases | https://www.classaction.org/news/clash-of-clans-maker-refuses-to-refund-minors-for-in-game-purchases-class-action-alleges
- CARU children's advertising guidelines (in-app purchases / real-currency disclosure): https://natlawreview.com/article/caru-issues-updated-guidelines-children-s-advertising | https://bbbprograms.org/media/insights/blog/in-app-ads-kids

---
*Reminder: informational compliance guidance, not legal advice. Items in section (d) require a licensed California attorney before launch.*
