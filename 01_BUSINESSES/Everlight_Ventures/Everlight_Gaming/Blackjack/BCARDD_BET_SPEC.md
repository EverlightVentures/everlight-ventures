# THE B-CARDD BET - $BCARDD's 1-in-a-Million House Hand
**Spec date:** 2026-06-03 | **Status:** design locked (rules), 3 numbers + compliance pending before build
**Target system:** `Everlight_Foundations/edge_functions/blackjack-api/index.ts` (server-authoritative) + the deck/RNG in every card game.

## The hook (Rich's vision)
$BCARDD's signature **B-Card** (the crowned-B blackjack card) is secretly shuffled into the shoe of
**every card game**. It is the rarest pull in the house. If a player draws it, $BCARDD himself "deals
them in" to a house-backed mega-hand. It **replaces the old 777 side bet** and **becomes THE progressive.**

## Core rules
1. **The B-Card is in every deck/shoe** across all card games (blackjack first).
2. **Draw odds = exactly 1 in 1,854,799 cards dealt.** That number is **"$BCARDD" spelled in digits**:
   `$=1 B=8 C=5 A=4 R=7 D=9 D=9` -> **1,854,799**. (Per-card server RNG check; server-authoritative so it
   cannot be client-spoofed.)
3. **On a B-Card hit, the player CHOOSES (optional jackpot - this is the hook):**
   - **Option A - TAKE IT (guaranteed):** automatically WIN the current hand at **100x the player's average
     bet.** House-staked, player risks nothing, house covers any double-down. Bird in hand.
   - **Option B - RIDE IT (gamble up to 200x):** the B-Card plays as an **8** in the current hand (fitting:
     **B = 8** in "$BCARDD numbers"); the player keeps playing at their **normal current bet.** The perk:
     the **very next hand becomes a "Golden Hand" worth 200x average bet - but NOT automatic. The player
     must actually BEAT THE DEALER to collect.** Beat the dealer = 200x avg bet. Push or lose = jackpot
     gone (they gambled away the guaranteed 100x). Higher ceiling, real risk, real agency.
   - Winnings credit in the currency of play (SC in sweeps mode = redeemable; Gold mode = for-fun only).
   - **House math (why offering the choice is house-positive):** Option B only pays if the player beats the
     dealer (~<50% with the house edge), so its **expected cost is LOWER** than the guaranteed 100x. The
     choice feels more generous to the player while actually costing the house less. Average bet is tracked
     + proven **server-side** (auditable avg-bet log) so the multiplier cannot be gamed.
4. **It replaces the 777.** Wherever the game currently offers a "777" side bet / jackpot trigger, the
   B-CARDD BET takes its slot. (Confirm exact 777 location in code at build time.)
5. **It IS the progressive - tailored, not a flat jackpot (the "tax-bracket" model).** Instead of one
   global jackpot number, the "average bet" the 100x multiplies is set by the player's **bracket (Tier
   1 / 2 / 3)** based on their pot / average bet, like tax brackets. A high-roller's B-Card hand is bigger
   than a casual's. The progressive is **individual**, scaling to how the player actually bets.

## HOW THE HOUSE MAKES MONEY (the revenue engine)
**Revenue = Gold Coin sales. Cost = Sweeps Coin (SC) redemptions. Profit = the gap, and the gap is
structural, not luck.** Plain version:
- Players **buy Gold Coins** to play for fun. That money is **yours, permanently** - Gold is never
  redeemable, so a Gold purchase is locked-in revenue the moment it happens. Most players play Gold mode
  for entertainment and never cash anything out.
- You only ever pay **cash for SC** (the free/bonus coin), and only above a redemption threshold + after
  playthrough + KYC. **Gold winnings are never cashed** - paying out a Gold-mode hand costs you nothing real.
- **Why redemptions stay smaller than Gold revenue (the 3 structural levers):**
  1. **House edge** - SC games run a casino RTP (~95%). In aggregate SC balances **decay back to the house**
     the more they are played.
  2. **Playthrough + minimum-redemption threshold** - SC must be wagered before redeeming, and a chunk never
     reaches the cash-out minimum. Lots of free SC simply churns away.
  3. **Free SC is a sized marketing cost** - the bonus SC bundled with Gold is calibrated so total expected
     redemptions stay well under Gold revenue.
- **Answering the direct question - "do I pay them in SC or Gold?":** redeemable cash payouts are **ALWAYS
  in SC, never Gold.** Winnings from a Gold-mode hand stay as (non-cashable) Gold. Winnings from an SC-mode
  hand are SC, which is the only thing that can become real cash on redemption.
- **The B-CARDD BET fits cheaply** because the **1-in-1,854,799 rarity** means the flashy house-staked 100x
  hand almost never actually fires - but the *legend* of it ("you could hit the B-Card and let the house
  bet 100x for you") drives Gold Coin sales + retention. Its expected payout cost is tiny vs. the hype it
  buys. That is the trick: a jackpot that markets hard but pays out rarely.

Worked mini-example (illustrative): a player buys a **$20 Gold package** -> you bank **$20**. They get, say,
**20 free SC** as the bonus. With a ~5% house edge + playthrough, that 20 SC trends down as they play; many
players never hit the (e.g. 50 SC) redemption minimum at all. Even if a winner redeems some SC, your Gold
revenue across all players dwarfs total redemptions. **Net: Gold in >> SC cashed out = profit.**

## HOUSE RESERVE / SAVINGS SIZING (how much cash to park)
**Your reserve = your single-hand payout cap. That is the whole answer.** The most you can ever owe on one
B-Card event is the **200x Golden Hand**, so you cap that number and keep that much (plus a small buffer) in
savings. Two facts make the reserve small and predictable:
1. **Hit frequency scales with total CARDS dealt (per card, not per player).** At LAUNCH volume it is
   rare (one hit per ~370,000-460,000 hands). At SCALE it is frequent - see "AT SCALE" below - so the
   reserve must cover the **expected daily payout rate**, not a single hit.
2. **Not all of a win cashes out.** Playthrough + redemption minimum + KYC + the house edge mean a chunk of
   any SC win is replayed/lost back before it ever becomes cash. Reserve planning still assumes worst case
   (full cap cashed), but real cost is usually lower.

**Formula (assume 1 SC = $1 at redemption; adjust to your rate):**
`max single payout = 200 x (capped average bet)` ... `reserve = max single payout x ~1.5 buffer`

| You cap a single B-Card payout at | Implied top-tier avg bet (200x) | Keep in savings (~1.5x) |
|---|---|---|
| **$500**  | ~2.5 SC/hand | **~$750** |
| **$1,000**| ~5 SC/hand   | **~$1,500** |
| **$5,000**| ~25 SC/hand  | **~$7,500** |
| **$10,000**| ~50 SC/hand | **~$15,000** |

**Simplest control = cap the PAYOUT directly** (e.g. "max B-Card payout = $1,000 of SC, whatever the tier").
Then reserve = that cap x 1.5, full stop. Raise the cap as Gold-Coin sales build the float.

**Launch recommendation (given a small starting bankroll):** start with a **$500-$1,000 payout cap** =
**~$750-$1,500 parked in savings.** Because the 10x-profit target means Gold revenue should run ~10x your
SC payouts, ongoing Gold sales **refill the reserve faster than B-Card hits drain it** - the savings float is
just the cushion to cover a hit *before* that revenue lands. Scale the cap up as the bankroll grows.

### AT SCALE (Rich's point: "1M players a day = multiple payouts a day")
Correct - at volume the B-Card fires often, because the odds are **per card dealt**, not per player:
- `hits/day = (players x hands_per_player x cards_per_hand) / 1,854,799`
- Worked example: **1M players x 30 hands x ~5 cards = 150M cards/day -> ~81 B-Card hits/day** (NOT 3; more
  play per user = more hits). At ~1 hand/user it would be ~3/day; real engagement pushes it to dozens-plus.
**Why this is still safe - it SELF-BALANCES.** The very same volume that creates hits creates Gold-Coin
revenue, so the RATIO (payout / revenue) is constant at any scale:
- Expected daily payout = `hits/day x avg payout/hit`. Example: 81 hits x ~$300 avg = **~$24k/day** payout.
- Daily Gold revenue at 1M players (even ~5% buy a $20 pack) = 50,000 x $20 = **~$1,000,000/day.**
- Payout is **~2.4% of revenue** - and it stays ~that % whether you have 1,000 players or 10M. Double the
  players = double the hits AND double the revenue; your margin does not move.
**So the reserve at scale = ~1-2 weeks of expected payout** (a rolling float, e.g. ~$170k-340k in the 1M/day
example), continuously refilled by Gold revenue that is ~40x larger. It is a small line item, not a threat.
**Frequency is also a MARKETING win:** dozens of winners a day = "people win the B-CARDD BET every hour"
hype, while each individual player's daily odds (~1 in 12,500 in the example) still feel rare. If you ever
want FEWER, bigger jackpots, raise the odds denominator (trade-off: lose the branded 1,854,799) or lower the
cap. Recommendation: keep the branded odds; frequency scaling with volume is self-funding and good for hype.

## THE SELF-SUFFICIENT LOOP (Rich's model - the core economic logic)
1. **The B-CARDD BET is the DRAW.** The dream of pulling the 1-in-1,854,799 card and riding the house's
   money is the hook that makes the sweepstakes exciting.
2. **The sweepstakes is why players buy Gold.** Wanting in on the draw drives Gold-Coin purchases.
3. **Gold is the revenue.** That is where the money is made.
4. **The average bet PROVES affordability.** The payout is a multiple of the player's OWN average bet, and
   the house has ALREADY profited off that exact betting stream (house edge x their volume). The player
   self-funds their own jackpot. **Self-sufficient by design.**

**Why the math makes this airtight:** the B-Card fires ~once per **370,000 hands**. With a ~5% house edge,
by the time it hits the house has banked roughly `0.05 x avg_bet x 370,000 = ~18,500 x avg_bet` in profit
off the surrounding play. The payout is at most **200 x avg_bet, hard-capped at 888.** So the profit
collected *around* each hit is on the order of **~90x larger than the biggest possible payout.** The bigger
someone's average bet, the more the house already made off them - which is exactly why the average bet
"proves you can pay it." Every jackpot is pre-funded by the betting that earned it.

**Profit target:** keep total Gold revenue >> total payouts (the ~10x cushion). Given the loop above, that
holds automatically at any scale - the draw funds the buy-in, the buy-in is the profit, and the house edge
on the same volume pre-pays the rare jackpot. Self-sufficient.

### "Make sure they bought enough Gold to cover their 888" - YES self-funds, but NOT a purchase gate (LEGAL LANDMINE)
Rich's instinct (the player should have funded their own payout) is correct - but it must be achieved
**implicitly via the math, NEVER by an explicit rule.** **DO NOT** code "you can only win / only redeem the
SC jackpot if you have bought >= $X of Gold." That single rule **conditions a prize on a purchase = adds
consideration = converts the legal sweepstakes back into ILLEGAL GAMBLING.** It would break the whole thing.
**How you get the exact protection you want, legally:**
1. **Payout scales with the SWEEPS average bet** (100x/200x of their SC avg) - already in the formula.
2. **Free SC is handed out in SMALL amounts** (the mail-in/daily AMOE gives a little). So a freebie-only,
   never-paid player has a tiny SC average -> a tiny payout (their 200x might be $5, not 888). They simply
   cannot reach the 888 cap on dribs of free SC.
3. **To build an SC average big enough to approach 888, a player basically had to buy Gold** (that is where
   the large SC bonuses come bundled). So **big payouts naturally land on people who paid** - WITHOUT you
   ever requiring a purchase. The economics do the gating; the rules never mention it.
4. **Cap 888 + redemption threshold + playthrough + KYC + house edge** bound and pre-fund the rest.
So: **is it cooked in? YES - structurally.** A non-buyer can technically win (law requires that they CAN),
but only a trivial amount; the 888-tier payouts self-select to Gold buyers via SC-average sizing, not a gate.

## $BCARDD canonical look (LOCKED)
$BCARDD's **official appearance = the AI dealer MP4 look**, specifically **buff $BCARDD dealing the cards
out**. That frame/style is the canon for: the B-Card art, card #0001, the brand emblem, and the casino
dealer avatar. All future $BCARDD art should match the buff-dealer look. (See `ecosystem/art/BCARD_SIGNATURE_SPEC.md`.)

## PLAYER RATING - "average bet" (LOCKED 2026-06-03)
The multiplier basis = the player's **real Quarter-To-Date (QTD) average bet**, tracked **per player** from
**actual logged wagers**, **reset at the start of every calendar quarter** (Jan 1 / Apr 1 / Jul 1 / Oct 1).
Modeled on a **casino player rating / reward-points tier** that requalifies each quarter. Properties:
- **Real + provable:** `qtd_avg_bet = sum(wagers this quarter) / count(hands this quarter)`, computed
  server-side from the immutable hand log. Auditable; cannot be spoofed client-side.
- **Tracked PER CURRENCY (resolves the confusion):** keep TWO separate QTD averages per player - one for
  **Gold** bets, one for **Sweeps (SC)** bets. A hand is played in ONE coin. The B-Card pays in the **same
  coin as the hand it hit on**, at **that coin's** average. A Sweeps jackpot uses the SC average (and only
  SC can cash out); a Gold jackpot uses the Gold average (fun only, never cashes out). You never pay an SC
  prize off a Gold average. The 888 cap applies to the redeemable (SC) side.
- **Quarterly reset** keeps it current AND blocks sandbagging - you cannot spike the average with one giant
  bet because it is averaged over the quarter's whole hand volume, and the reset re-levels everyone each Q.
- **Drives the Tier** (1/2/3 below): your QTD average IS your bracket, like requalifying for a casino tier
  each quarter.
- **New-player fallback:** under **20 logged hands** this quarter, basis = the larger of (their average so
  far) or the **table minimum bet**, so a hand-1 B-Card cannot produce a junk average. (Threshold tunable.)

## Remaining numbers I need from Rich (these change the code, confirm before build)
1. **Tier 1/2/3 bracket thresholds** (by average bet, in chips/SC). PROPOSED defaults to confirm/adjust:
   - **Tier 1 (casual):** avg bet up to 100  -> B-Card hand = 100x of avg (capped at 100-bet basis)
   - **Tier 2 (mid):** avg bet 101 - 1,000   -> 100x of avg
   - **Tier 3 (high-roller):** avg bet 1,000+ -> 100x of avg (with a house-exposure cap, e.g. max single
     house hand = X, so one whale can't drain the pool)
   (Brackets exist mainly to floor/cap the "average bet" used so the payout is fair + the house exposure
   is bounded. Tell me the real ranges + whether you want a hard cap on Tier 3.)
2. **House-exposure cap = 888 (LOCKED 2026-06-03).** Max single B-Card payout is **888**, hard cap, any
   tier (lucky-8, ties to the B-Card = 8). Phase 1 (chips): max 888-chip payout = no real cost. Phase 2
   (SC cash-out): reserve = 888 x ~1.5 = **~$1,332** parked. Raise only as Gold revenue builds the float.

## DOES IT QUALIFY AS A SWEEPSTAKES (not betting)? - the legal test
Gambling = **(1) consideration (you pay) + (2) chance + (3) prize**, ALL THREE. Remove any one and it is
not illegal gambling. Sweepstakes are legal because they remove **consideration** via a genuine free entry.
- **Chance** = present (the card + the hand). **Prize** = present (SC redeemable). **Consideration** = the
  ONLY lever. A **genuine no-purchase free way to get Sweeps Coins (AMOE)** removes it -> **legal sweepstakes.**
- **The B-CARDD BET does NOT change this.** A flashy 100x/200x jackpot is just the *prize*; excitement is
  irrelevant to the legal test. Only "did you have to pay to play for it" matters - and the free entry says no.
- **So it qualifies as a sweepstakes IF AND ONLY IF:** (a) SC is always obtainable FREE and never *required*
  to be purchased, (b) the free path is GENUINE (not a buried sham), (c) states that ban sweeps regardless
  (WA, MI, ID + the growing 2024-2025 list) are GEO-BLOCKED, (d) wagering uses SC that was obtained free/as
  a bonus (SC is never sold directly).
- **Honest risk note:** even a clean sweeps structure is under rising 2024-2025 regulatory heat; it is a
  watched, moving target, not set-and-forget. **Phase 1 (for-fun chips, no cash-out) sidesteps ALL of this**
  (no prize = no gambling). The test only bites at Phase 2 cash-out.

## COMPLIANCE MODEL (the kosher structure - dual currency + free entry)
Rich's intent (2026-06-03): "to bet it you have to buy the sweepstakes coin... make it all kosher and
compliant." **CRITICAL legal flip to get this right:** in a legal US sweepstakes casino you must **NEVER
sell the redeemable coin directly.** Selling a "buy this coin and bet it for cash" coin = consideration +
chance + prize = **illegal gambling.** The compliant structure that delivers exactly what Rich wants:

**Two currencies (the industry-standard sweeps model - Chumba/LuckyLand/Stake.us pattern):**
- **Gold Coins (GC)** - play-FOR-FUN only. **Purchasable.** NO cash value, NOT redeemable. This is what
  players BUY. Gold-Coin mode = pure entertainment.
- **Sweeps Coins (SC)** - the **redeemable** currency (cash-out eligible above a threshold + KYC). **NEVER
  sold directly.** Players receive SC for **FREE**: as a promotional **bonus bundled with Gold Coin
  purchases**, via daily login / social bonuses, AND via a genuine **no-purchase mail-in Alternative Method
  of Entry (AMOE)**.

**Why this is the rule:** the free AMOE removes the "consideration" element, which is what would otherwise
make it illegal gambling. "Buy Gold Coins, Sweeps Coins come free (and there is always a free way to get SC)"
= legal sweepstakes. "Buy Sweeps Coins to bet for cash" = illegal. Same game, one critical flip.

**How the B-CARDD BET fits:** it plays in EITHER currency. In GC mode it is pure fun (no redemption); in SC
mode the house-staked 100x hand pays out in redeemable SC. A player "bets it" by spending the coin from
their balance - and the way they GOT redeemable SC was always free/bonus, never a direct SC purchase. The
progressive + Tier brackets work the same in both modes.

**Still required before SC cash-out goes live (non-negotiable):**
- **ENTITY: form an LLC - do NOT run the cash-out as a sole prop.** A CA sole prop puts Rich's PERSONAL
  assets on the line for a gambling-adjacent business (regulator action, player suit, chargebacks). Wrap
  Phase 2 in an LLC (CA, or a friendlier state w/ CA foreign-registration) for a liability shield. Phase 1
  (for-fun) is fine as-is. CA itself ALLOWS genuine sweepstakes (free entry); it bans lotteries (pay+chance
  +prize) - the free AMOE is what keeps you on the legal side as a CA operator.
- **PAYMENT PROCESSOR: Stripe and most mainstream processors PROHIBIT gambling/many sweeps** - the real
  "get kicked out" risk is the processor/app-store, NOT the state. Phase 2 needs a sweeps-friendly processor
  + compliance with Apple/Google real-money rules (or web-only distribution).
- Gaming/sweepstakes **attorney review** of the full structure, terms, and AMOE wording.
- **Geo-exclude** restricted states (e.g. WA, MI, ID, NV + the growing 2024-2025 banned list).
- **KYC/AML** on redemption; minimum redemption threshold + playthrough; age gating (18+/21+).
- **No-purchase-necessary** disclosures everywhere coins are offered.
Build the mechanic now; enable SC cash-out only after counsel signs off. (Same build-now-clear-before-public
discipline as `Alley_Kingz/ecosystem/LEGAL_TRADEMARK_DEFENSE.md`.)

## CODEBASE RECON (2026-06-03) - what already exists
- **Currency = "chips" + "gems" ONLY** (`game_currencies` table). **No cash-out today = pure for-fun =
  NOT gambling.** So Phase 1 below has ZERO legal gate.
- **Deal logic is CLIENT-SIDE** (`06_DEVELOPMENT/vantaris/src/lib/blackjack-engine.ts`); the edge function
  `blackjack-api/index.ts` only RECORDS hands (`record-hand`) + balances + jackpot + tables. Cards are not
  dealt server-side today. (Fine for for-fun; MUST move server-side for real-money Phase 2 anti-cheat.)
- **VIP table already exists** (`table_type === 'vip'`, entry 2000) and **already runs a Spanish 21
  ruleset.** INCORPORATE the B-Card INTO that existing VIP table - **do NOT add a new table** (Rich
  2026-06-03). Spanish 21 = 48-card deck (no rank-10 cards; J/Q/K stay). The B-Card plays as an **8** (8s
  are in the Spanish deck) so it slots in cleanly; the B-CARDD BET layers on top of the existing Spanish 21
  bonuses. B-Card injection is ruleset-agnostic (intercepts the draw), so it coexists with Spanish 21 rules.
- **Progressive already exists:** `progressive_pool` + actions get-jackpot / jackpot-contribute /
  jackpot-win. The B-CARDD BET replaces/becomes this.
- **QTD average** is derivable from the immutable hand log (`record-hand` stores bet_amount per hand).

## BUILD PHASING (locked)
### PHASE 1 - B-Card on the EXISTING VIP (Spanish 21) table, FOR-FUN (build + ship NOW, no legal gate)
1. `blackjack-engine.ts`: add the B-Card (53rd card, value **8**) to the VIP-table shoe; per-card
   `1/1,854,799` trigger; the optional-jackpot choice (Take 100x | Ride for 200x golden-hand).
2. Frontend page/components: B-Card reveal (buff $BCARDD dealer art), the choice UI, the golden-hand next
   hand, "THE B-CARDD BET" banner.
3. Edge fn `blackjack-api`: new `bcard-resolve` action -> compute **QTD avg bet** + tier, pay the 100x/200x
   in **chips**, ledger the event (auditable). Gate the B-Card to the EXISTING VIP (Spanish 21) table only -- no new table row.
4. All in for-fun chips. Test + deploy. **No cash-out = legal now.**
### PHASE 2 - real-money sweeps cash-out (attorney-gated, later)
5. Add **Gold/Sweeps** dual currency to `game_currencies`; move the deal + B-Card RNG **server-side**
   (anti-cheat for real money); AMOE/free-entry, geo-block, KYC/AML, redemption.
6. Gaming/sweepstakes attorney signs off -> flip the SC cash-out switch on.
7. Roll the B-Card into the other card games' decks with the same odds + handler.

## TEST / BETA MODE (build requirement)
- A `BETA_MODE` flag. When ON, the B-Card forces every **50 cards** BUT **only for player
  `1m.rich.gee@gmail.com`** (gate on the authenticated player id/email so other beta testers still see
  normal odds). Lets Rich exercise the take/ride/payout flow on demand.
- **Production = disable the flag** (comment the forced-trigger line) -> defaults to real 1/1,854,799 odds.
- Implementation: `const BETA_BCARD_EVERY = 50;` + `if (BETA_MODE && player.email === OWNER_EMAIL && cardCount % BETA_BCARD_EVERY === 0) forceBCard();` else the production RNG path.

## SECURITY / ANTI-CHEAT (hard requirement for Phase 2 real-money)
- **Server is the single source of truth.** The B-Card trigger (RNG), the avg-bet lookup, the 100x/200x
  resolution, and the payout are all computed + signed **server-side**. The client only *renders* the result.
- **Client cannot self-grant a jackpot.** If a client submits a B-Card win the server did not generate (or a
  mismatched payout), the server **rejects it, marks the jackpot INVALID, and flags the account.** No
  client-asserted win is ever paid.
- **Tamper detection:** every B-Card event carries a server-side token/signature; any modification or replay
  is identified and rejected. Hand + payout ledger is immutable + audited.
- **Deploy/access control:** code + config changes ship only from **Rich's approved devices** via signed
  deploys; no ad-hoc edits to the live money function. (Phase 1 for-fun can keep client-side dealing; this
  server-authoritative move is part of the Phase 2 cash-out gate.)
