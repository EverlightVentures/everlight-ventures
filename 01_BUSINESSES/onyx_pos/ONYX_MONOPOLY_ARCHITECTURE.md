# ONYX -- Monopoly Architecture
## Economic Chokehold Blueprint

> A monopoly isn't built on features. It's built on owning something
> nobody else can replicate, then making everyone pay to use it.

---

## THE 7 CHOKEPOINTS

Every real monopoly controls chokepoints -- narrow passages that all
commerce MUST flow through. Onyx needs to own 7 of them.

---

### CHOKEPOINT 1: THE PAYMENT RAIL
**Model:** Visa/Mastercard
**Mechanism:** Own the pipe between every buyer and seller

Visa doesn't sell to consumers. Visa doesn't sell to merchants. Visa owns
the RAIL between them and taxes every transaction 1.5-3.5%. In 2024,
Visa processed $15.3 TRILLION. Their cost to process? Fractions of a penny.
The rest is pure margin.

**Why they can't leave:** Two-sided network effect. Merchants accept Visa
because 80% of consumers have one. Consumers carry Visa because 99% of
merchants accept it. Neither side can quit without losing the other.
This is the most powerful lock-in in economics.

**Onyx implementation:**
- **Onyx Pay** becomes the payment method between local consumers and merchants
- Every Onyx transaction earns points. No other payment method does.
- Merchants get lower fees through Onyx Pay (2.2%) vs Visa/MC (2.9%).
  This is a LOSS LEADER -- the real revenue is everywhere else.
- As consumer base grows, merchants MUST accept Onyx Pay or lose customers.
- As merchant base grows, consumers MUST have Onyx or miss deals/points/lottery.
- **The chokehold:** Neither side can leave without losing the other side.
  This is mathematically identical to Visa's lock-in.

**Financial chokepoint within the rail:**
- **Float capture (Starbucks model):** Onyx wallet balances are YOUR money
  to hold. Starbucks holds $1.8B in unredeemed gift cards. That's an
  interest-free loan from customers. At 5% APY, that's $90M/year in
  pure profit from money just SITTING there.
- **Breakage:** 10-15% of loaded wallet funds are never spent (Starbucks
  breakage rate is ~10%). That's revenue from money customers gave you
  and forgot about.
- **Settlement delay:** You collect from consumer instantly but settle to
  merchant in 1-3 days. That float earns interest. At scale, this is
  massive.

---

### CHOKEPOINT 2: THE CUSTOMER IDENTITY
**Model:** Google (account), Apple (Apple ID), WeChat (everything)
**Mechanism:** Own WHO the customer is. Rent access to merchants.

Google knows what you search for. Apple knows what apps you use. WeChat
knows everything -- payments, messages, social, government ID. In China,
93% of urban residents use WeChat Pay. You literally cannot function in
Chinese cities without it. That's a monopoly.

**Why they can't leave:** Your identity IS the platform. Your purchase
history, your loyalty tier, your prediction record, your social graph,
your payment methods -- all locked inside. Leaving means starting from
zero everywhere else.

**Onyx implementation:**
- **Single identity across ALL merchants.** Customer doesn't create a new
  loyalty account at every shop. One Onyx profile. One wallet. One tier.
- **The merchant doesn't own the customer. Onyx does.** The merchant sees
  "Onyx customer #4,827 (Gold tier, 142 visits, prefers morning lattes)."
  They do NOT see the customer's phone number, email, or payment info.
- **Merchants PAY to reach their own customers.** Want to send a push
  notification to your regulars? That goes through Onyx. $0.02 per push.
  Want to see purchase analytics? That's the $149/mo plan.
- **The linguistic lock:** Customers say "I'm Gold on Onyx" not "I'm a
  regular at Joe's Coffee." The IDENTITY belongs to the platform, not
  the merchant. This is how airline alliances work -- you're a United
  MileagePlus member, not a "frequent SFO-LAX flyer."

**Data monopoly within identity:**
- You see EVERY transaction at EVERY merchant. No single merchant has
  this view. You know that Customer #4,827 spends $47/week at the coffee
  shop, $120/week at the bar, and $85/week at the boutique.
- This data lets you:
  - Predict demand better than any single merchant
  - Route customers to the right merchant at the right time
  - Launch competing private-label products (Amazon's playbook)
  - Price the advertising and boost products with perfect information

---

### CHOKEPOINT 3: DEMAND ROUTING (THE ALGORITHM)
**Model:** Google Search, Amazon Buy Box, DoorDash sort order
**Mechanism:** Control WHICH merchant the customer sees first

Google controls 92% of search. When someone searches "coffee near me,"
Google decides which coffee shop appears first. That #1 spot gets 28% of
clicks. Position #10 gets 2.5%. Google sells the top spots for $2-15/click.
The algorithm IS the monopoly.

Amazon's Buy Box is even more aggressive. 82% of Amazon sales go through
the Buy Box. Amazon's algorithm decides which seller gets it. Sellers
spend billions on ads to win placement. Amazon collects the ad revenue
AND the data to launch competing products.

**Why they can't leave:** Where else will the customers come from? If your
shop isn't on Onyx and your competitor is, the customer goes to your
competitor because that's where the deal/points/lottery is.

**Onyx implementation:**
- **Deals Map = Onyx's Search Engine.** When a customer opens Onyx, they
  see a map of deals. Which deal appears first? YOUR algorithm decides.
- **Boosted Deals (Google Ads model):** Merchants pay $3-50/day to boost
  their deal to the top of the map. Self-serve. Auction-based. The
  merchant with the highest bid + best customer match wins the top spot.
- **Organic ranking factors:** Transaction volume, customer ratings,
  cashback percentage, lottery win rate. These are YOUR levers. You
  decide the formula. Merchants optimize for YOUR algorithm.
- **The chokehold:** Over time, customers stop using Google Maps/Yelp for
  local discovery and use Onyx instead (because Onyx has deals, points,
  lottery -- Google doesn't). Once this happens, you ARE the local
  discovery layer. Merchants must pay you to be seen.

**Linguistic dominance in discovery:**
- Goal: Replace "Google it" with "Onyx it" for local commerce.
- "Where should we eat?" → "Check Onyx"
- "What's open near me?" → "Open Onyx"
- "Is there a deal?" → "Is it on Onyx?"
- This linguistic capture happens when the app becomes the DEFAULT
  action before spending money locally. Starbucks achieved this for
  coffee. Uber achieved this for rides. You achieve this for
  ALL local commerce.

---

### CHOKEPOINT 4: THE FINANCIAL STACK
**Model:** Shopify (Balance + Capital + Payments), Square (Loans + Banking)
**Mechanism:** Become the merchant's bank. Then they can never leave.

Shopify Capital has lent $6B+ to merchants. Repayment is automatic --
a percentage of every sale. The merchant never writes a check. Shopify
sees their sales data in real-time, so they know EXACTLY how much to
lend and the risk is near-zero.

Square Loans works the same way. See the merchant's revenue → offer a
loan → auto-deduct repayment. The merchant gets capital they can't get
from a bank (banks don't see POS data). Square gets guaranteed repayment
from the transaction stream they control.

**Why they can't leave:** If you leave Shopify, you lose your loan, your
balance, your payment history, your credit score on the platform. Starting
over on another platform means starting from zero creditworthiness.

**Onyx implementation:**
- **Onyx Capital:** Micro-loans to merchants based on their POS data.
  You SEE their daily revenue, their seasonality, their growth rate.
  Banks can't see this. You offer a $5K-$50K advance. Repayment is
  automatic: 10% of daily sales until repaid.
- **Onyx Balance:** Merchant banking. Their sales revenue lands in Onyx
  Balance (not their bank). They pay vendors from Onyx Balance. They pay
  employees from Onyx Balance. Their entire financial life runs through you.
- **Earned Wage Access** (already built): Employees access wages early
  through Onyx. The fee comes from the merchant. Now the EMPLOYEE is
  locked into Onyx too. Both sides of the labor relationship depend on you.
- **The chokehold:** Merchant has a $20K loan auto-deducting from sales.
  Switching POS systems means defaulting on the loan. They can't leave.
  This is Shopify Capital's exact playbook -- and it works.

---

### CHOKEPOINT 5: THE SOCIAL GRAPH
**Model:** Facebook (social lock-in), Strava (athletic identity)
**Mechanism:** Your friends are here. Leaving means losing them.

Facebook's monopoly was never the features. It was the social graph.
Your photos, your friends, your memories -- all on Facebook. Leaving
means losing your digital social life. This kept Facebook dominant for
15 years despite better alternatives existing.

Strava works the same way for athletes. Your running history, your
segment records, your club memberships -- all on Strava. Switching to
Nike Run Club means losing your 5-year run history and all your PRs.

**Why they can't leave:** Social capital is non-portable. Your Onyx tier,
your prediction record, your streak, your clout score, your win history
-- none of it transfers to another app.

**Onyx implementation:**
- **Tier status is social currency.** "I'm Obsidian on Onyx" becomes a
  flex. Like having a black Amex or airline status. Visible to friends
  on the social feed. People TALK about their tier.
- **Prediction leaderboard is competitive identity.** Your win rate, your
  streak, your biggest calls -- this is your sports betting resume.
  Leaving means losing your record. Starting over at 0-0.
- **Purchase history = taste profile.** Your Onyx profile shows what you
  buy, where you shop, what drops you copped. This becomes identity.
  Like how Spotify Wrapped became identity. "My Onyx Year in Review."
- **Friend referrals create obligation.** You referred 12 friends. They're
  using your code. You get kickbacks from their spending. Leaving means
  losing passive income from your network.
- **The chokehold:** Your social capital, competitive record, tier status,
  taste profile, and referral income are all non-portable and took
  months/years to build. Switching cost is total identity loss.

---

### CHOKEPOINT 6: THE LOGISTICS NETWORK (PHYSICAL LOCK-IN)
**Model:** Amazon FBA, FedEx, DoorDash driver network
**Mechanism:** Own the physical movement of goods. Can't be replicated without billions.

Amazon spent $100B+ building its logistics network. 110+ fulfillment
centers. 1,000+ delivery stations. 275,000+ delivery drivers. No
competitor can replicate this without matching the investment. FBA
merchants are locked in because Amazon handles storage, packing,
shipping, and returns. Moving to self-fulfillment means building an
entire supply chain from scratch.

DoorDash controls 67% of US food delivery. Their driver network IS the
product. Restaurants can't deliver without DoorDash's drivers. Customers
can't get food without DoorDash's logistics. The driver network is the
chokepoint.

**Onyx implementation (asset-light version):**
- **Neighborhood delivery network.** Not owning trucks -- orchestrating
  EXISTING movement. Onyx merchants already have employees, vehicles,
  and foot traffic. Route deliveries through the network.
  - Customer at Coffee Shop A orders from Boutique B (0.3 miles away).
    Coffee Shop A's employee walks it over during a slow period. Both
    merchants benefit. Onyx takes a delivery fee.
  - This is the "mesh network" model. No fleet to build. No drivers to
    hire. The merchants ARE the logistics network.
- **Dead stock redistribution.** Already built. One shop's excess inventory
  flows to another shop that needs it. Onyx routes the goods. Takes a
  commission. This is B2B wholesale logistics running on the merchant
  network you already control.
- **Cross-merchant fulfillment.** Customer wants a gift basket: coffee
  from Shop A, flowers from Shop B, chocolate from Shop C. Onyx
  orchestrates the assembly across merchants. One delivery. One payment.
  Three merchants served. No single merchant could offer this alone.
- **The chokehold:** As more merchants join, the logistics network becomes
  more capable. A standalone merchant can't offer cross-merchant bundles,
  mesh delivery, or inventory sharing. They NEED the network. And the
  network is Onyx.

---

### CHOKEPOINT 7: THE LINGUISTIC MONOPOLY
**Model:** Google ("Google it"), Uber ("Uber there"), Venmo ("Venmo me")
**Mechanism:** Own the VERB. When your brand IS the action, competitors are invisible.

"Google it" is the most valuable two words in business history. Google
became the verb for search. Competitors can't overcome this because the
language itself routes users to Google. Bing could be 10x better and
people would still say "Google it."

"Venmo me" turned a payment app into a cultural verb. Cash App tried for
years to get "$Cashtag" to stick. It partially worked. But "Venmo me" is
still the dominant phrase for P2P payments among millennials.

Uber became the verb for ride-hailing globally. Even in markets where
competitors dominate (Lyft, Bolt, Grab), people say "I'll Uber there."

**How verbs are created:**
1. **First mover in a new category.** Google was first in useful search.
   Uber was first in app-based rides. Venmo was first in social P2P.
2. **Two syllables or less.** Google. Uber. Venmo. Onyx. Easy to verb-ify.
3. **Repeated social context.** The phrase must occur in conversation
   between people, not just in marketing. "Venmo me" happens between
   friends splitting dinner. It's peer-to-peer language adoption.
4. **Action-associated, not product-associated.** "Google it" = search.
   "Uber there" = go. "Venmo me" = pay. The verb replaces the ACTION,
   not the product category.

**Onyx linguistic targets:**

| Phrase | Replaces | Context |
|--------|----------|---------|
| "Onyx it" | "Look it up" / "Check for deals" | Before spending money locally |
| "Onyx me" | "Pay me" / "Venmo me" | P2P between Onyx users |
| "Check Onyx" | "Check Yelp" / "Check Google Maps" | Finding where to go |
| "I'm Obsidian" | "I'm a regular" / "I'm VIP" | Status flex |
| "Onyx Drop" | "Limited release" / "New drop" | Boutique culture |
| "What's your Onyx?" | "What's your Venmo?" | Exchanging payment info |

**Implementation strategy:**
- **Receipt language:** Every QR receipt says "Scanned with Onyx" not
  "Powered by Onyx POS." The customer sees the brand, not the merchant's
  backend.
- **Share cards:** Social share images always say "I won on Onyx" / "Copped
  on Onyx" / "I called it on Onyx." The brand is in every share.
- **Referral language:** "Send them your Onyx link." Not "refer a friend."
- **Merchant signage:** Window stickers say "We're on Onyx" with QR code.
  Like "We Accept Visa" but for the whole ecosystem.
- **Creator vernacular:** Pay local influencers to say "Onyx" in content
  naturally. Not ads. Just organic mentions. "Got my usual on Onyx."
  Costs $50-200/creator for micro-influencers in each neighborhood.

**The chokehold:** Once "Onyx" IS the word for local commerce, no
competitor can enter the market without fighting the language itself.
You can't out-feature a verb.

---

## THE SELF-FEEDING MACHINE

Here's how all 7 chokepoints feed each other to create an inescapable system:

```
CUSTOMER downloads Onyx for cashback deals (Chokepoint 3: Demand)
  ↓
Creates Onyx identity, links payment (Chokepoint 2: Identity)
  ↓
Pays with Onyx Pay for bonus points (Chokepoint 1: Rail)
  ↓
Earns points, builds tier, joins predictions (Chokepoint 5: Social)
  ↓
Tells friends "Onyx me" to split the bill (Chokepoint 7: Linguistic)
  ↓
Friends download → more customers → merchants MUST join
  ↓
MERCHANT joins because customers demand Onyx (Chokepoint 3: Demand)
  ↓
Gets Onyx Capital loan based on sales data (Chokepoint 4: Financial)
  ↓
Uses Onyx for delivery, inventory sharing (Chokepoint 6: Logistics)
  ↓
Can't leave: loan auto-deducts, customers expect Onyx, identity locked
  ↓
More merchants → more deals → more customers → FLYWHEEL
```

**The critical insight:** Each chokepoint makes the others stronger.
The payment rail feeds the data monopoly. The data monopoly feeds the
demand routing. The demand routing feeds the financial stack. The
financial stack creates the lock-in. The lock-in makes the linguistic
monopoly possible. The linguistic monopoly makes the payment rail the
default. LOOP.

**No single chokepoint is the monopoly.** The monopoly is the SYSTEM.
Competitors can match any individual feature. No competitor can match
all 7 simultaneously. That's the moat.

---

## PIPELINE INTEGRATION (Everlight's Existing Assets)

Every Everlight pipeline feeds the Onyx monopoly:

| Everlight Asset | Onyx Monopoly Role |
|----------------|-------------------|
| **Hive Mind (42 agents)** | Operates the platform 24/7. Marcus dispatches. Agents handle customer support, merchant onboarding, fraud detection, prediction market management. |
| **AI Consulting** | Onboard enterprise merchants. $3-5K setup fee for large retailers. The consulting pipeline SELLS the monopoly. |
| **Broker OS** | Source merchants. Rex scouts businesses, Piper does outreach, Harrison closes. Every deal = another node in the network. |
| **Wholesale Pipeline** | Dead stock marketplace IS the wholesale pipeline applied to Onyx merchants. Same agents, new channel. |
| **XLM Bot** | Points-to-crypto bridge. Customers convert Onyx points to XLM. You earn the exchange spread. Bot's trading infrastructure handles the liquidity. |
| **Content Factory** | Creates "Won on Onyx" social cards, merchant profile content, prediction market graphics, drop hype campaigns. |
| **everlightventures.io** | Becomes the merchant landing page. "Put your shop on Onyx." Lead capture. Signup funnel. |
| **Django Dashboard** | Merchant ops dashboard. Real-time analytics. Loan management. Network health monitoring. |
| **Supabase** | Production database for all 25+ tables. Auth. Realtime subscriptions for live predictions. |
| **Oracle E5** | API server. The 72-endpoint backend already built. Handles all transaction processing. |
| **Stripe Connect** | Multi-merchant payments. Onyx Card issuing. Loan disbursement. Split payments. |
| **Resend / Email** | Merchant onboarding sequences. Customer win notifications. Receipt delivery. |
| **Slack** | Ops alerting. Merchant support escalation. Hive agent coordination. |

**The pipeline IS the monopoly's operating system.** You're not building
from scratch. You're connecting 12 existing assets into one self-feeding
machine where each piece was already built for this purpose.

---

## MONOPOLY GROWTH PHASES

### Phase 1: SEED (Months 1-3)
**Goal:** 50 merchants, 5,000 customers in ONE neighborhood
- Pick one neighborhood (your neighborhood)
- Onboard 50 merchants face-to-face (Broker OS agents do outreach)
- Cashback + lottery + P2P payments live
- Merchant window stickers: "We're on Onyx"
- Target: "Check Onyx" becomes the phrase in that ONE neighborhood

### Phase 2: PROVE (Months 4-6)
**Goal:** Prove the economics work in one neighborhood
- Launch Onyx Capital (micro-loans from POS data)
- Launch prediction market (local sports bar partnerships)
- Launch drops (local boutique partnerships)
- Prove: Merchants using Onyx grow 15-25% in revenue
- Prove: Customer retention rate > 60% monthly

### Phase 3: EXPAND (Months 7-12)
**Goal:** 10 neighborhoods, 500 merchants, 50K customers
- Replicate the seed model in 9 more neighborhoods
- Cross-neighborhood network effects (customer visits multiple areas)
- Launch Onyx Card (Stripe Issuing)
- Launch merchant delivery mesh
- Target: "Onyx" appears in local press as "the app for neighborhood shopping"

### Phase 4: LOCK (Months 13-24)
**Goal:** Regional monopoly. Can't be displaced.
- 2,000+ merchants, 200K+ customers
- Onyx Capital loan book > $5M (merchants can't leave)
- Customer wallet float > $2M (interest-free capital)
- "Onyx me" entering local vocabulary
- Prediction market daily volume > 500K points
- Logistics mesh handling 200+ cross-merchant deliveries/day

### Phase 5: EXTRACT (Year 3+)
**Goal:** Turn the monopoly into maximum revenue
- Raise merchant fees (they can't leave, loan lock-in)
- Launch Onyx Ads (demand routing auction, Google Ads model)
- License the platform to other cities (franchise the monopoly)
- Points-to-crypto bridge generates exchange revenue
- IPO or acquisition at 15-20x revenue multiple

---

## THE DEFENSE (why competitors can't copy this)

1. **Network effects are exponential.** A competitor launching in your
   neighborhood needs to onboard merchants AND customers simultaneously.
   You already have both sides. They need to outspend you 10:1 to match.

2. **Financial lock-in is contractual.** Merchants with Onyx Capital loans
   literally can't switch. The loan auto-deducts from sales. Leaving
   means defaulting.

3. **Data compound interest.** You've been collecting transaction data for
   2 years. A new entrant has zero data. Your prediction algorithms,
   pricing suggestions, and demand routing are 2 years ahead.

4. **Linguistic moat.** Once people say "Onyx" instead of "local deals
   app," a competitor has to fight the language. This is why no one
   displaced Google despite better search engines existing.

5. **Social graph.** Customer's 47-day streak, Platinum tier, 80% prediction
   win rate, and 12 referrals -- none of that ports to a competitor.
   Switching cost is identity death.

6. **Logistics mesh.** The cross-merchant delivery network, dead stock
   marketplace, and inventory sharing only work with merchant density.
   A new entrant in your neighborhood would need 50 merchants to
   replicate what you built over 12 months.

7. **The pipeline behind it.** 42 AI agents running onboarding, support,
   content, analytics, and outreach 24/7. A competitor needs to build
   not just the app, but the entire autonomous operations layer.

---

## THE ONE SENTENCE

**Onyx is the Visa network for neighborhood commerce: we own the rail,
the identity, the data, the demand, the capital, the logistics, and
the language -- and every piece feeds the others into an inescapable
system that gets stronger with every transaction.**

That's not an app. That's a monopoly.

---

## INFRASTRUCTURE REQUIRED

Everything below is what you need to BUILD and OWN to support
all 7 chokepoints. Organized by layer.

### LAYER 1: FINANCIAL INFRASTRUCTURE (The Rail)

| Component | What It Does | Build/Buy | Cost | Timeline |
|-----------|-------------|-----------|------|----------|
| **Stripe Connect** | Multi-merchant payment processing. Split payments. Payouts. | Buy (API) | 2.9% + $0.30/tx (passed to merchant) | Week 1 |
| **Stripe Issuing** | Onyx Card (virtual + physical debit). Branded cards in customers' hands. | Buy (API) | $1/physical card + interchange earned back | Month 3 |
| **Stripe Treasury** | Onyx Balance (merchant banking). Hold funds. ACH transfers. | Buy (API) | $0/setup + partner bank fees | Month 4 |
| **Onyx Capital Engine** | Micro-lending logic. Risk scoring from POS data. Auto-repayment from sales. | Build | Dev time only | Month 4 |
| **Float Management** | Track wallet balances, gift cards, unredeemed points. Invest float. | Build | Dev time only | Month 2 |
| **KYC/AML** | Identity verification for wallet + card. Required by law. | Buy (Stripe Identity or Plaid) | $1.50/verification | Month 2 |
| **Ledger System** | Double-entry accounting for all money movement. Points, cash, credits. | Build | Dev time only. CRITICAL. | Month 1 |

**Regulatory requirement:** To hold customer funds (wallet), you need a
money transmitter license OR partner with a sponsor bank through Stripe
Treasury / Unit / Bond. Stripe Treasury handles this -- they provide the
banking license, you provide the product. This is how Cash App, Chime,
and every fintech operates.

### LAYER 2: DATA INFRASTRUCTURE (The Brain)

| Component | What It Does | Build/Buy | Cost | Timeline |
|-----------|-------------|-----------|------|----------|
| **Supabase** (already have) | Production database. Auth. Realtime. 25+ tables. | Already built | $25-$299/mo | Done |
| **Analytics Pipeline** | Aggregate transaction data across ALL merchants. Build demand models. | Build (PostHog + custom) | PostHog free tier → $450/mo at scale | Month 2 |
| **Recommendation Engine** | "Customers who shop here also shop there." Deal ranking. Demand routing. | Build (Python + Claude API) | API costs only | Month 3 |
| **Prediction Engine** | Smart pricing. Customer order prediction. Demand forecasting. | Already built (ecosystem.py + platform.py) | Done | Done |
| **Search / Discovery** | Merchant search, deal search, product search. | Buy (Meilisearch or Typesense, self-hosted) | Free (self-hosted) | Month 2 |
| **Geolocation** | Nearby merchants, proximity triggers, delivery routing. | Build + PostGIS (Supabase supports it) | Free | Month 1 |
| **Event Streaming** | Real-time transaction feed. Live prediction updates. Push triggers. | Supabase Realtime + pg_notify | Free (included) | Month 1 |

**The data moat builds over time.** Every transaction trains the models.
After 6 months you have demand curves no competitor can replicate without
6 months of their own data. After 2 years, you're uncatchable.

### LAYER 3: MOBILE APP (The Interface)

| Component | What It Does | Build/Buy | Cost | Timeline |
|-----------|-------------|-----------|------|----------|
| **Expo / React Native** | Cross-platform iOS + Android from one codebase. | Build | Free (OSS) | Weeks 1-4 |
| **Expo Router** | File-based navigation (like Next.js for mobile). | Build | Free | Week 1 |
| **NativeWind** | Tailwind CSS for React Native. Consistent styling. | Build | Free | Week 1 |
| **Expo Notifications** | Push notifications. Deal alerts. Streak reminders. Prediction results. | Build + Expo Push Service | Free up to 1M/mo | Week 2 |
| **Apple/Google Wallet SDK** | NFC loyalty passes. Tap-to-earn at register. | Build | Free (Apple/Google developer accounts) | Month 2 |
| **MapLibre / Mapbox** | Deals map. Merchant locations. Walking directions. | Build | MapLibre free (OSS) / Mapbox $0 up to 25K loads/mo | Week 2 |
| **Camera + OpenCV** | Receipt scanning from phone camera. Already built backend. | Build (Expo Camera → API) | Free | Week 2 |
| **Lottie Animations** | Scratch-off lottery. Confetti on wins. Tier-up celebrations. | Build | Free (OSS) | Week 3 |
| **Share Cards** | Auto-generated branded images for IG/TikTok stories. | Build (canvas/SVG rendering) | Free | Week 3 |
| **Stripe SDK** | In-app payments. Card management. Wallet top-up. | Buy (Stripe React Native SDK) | Free | Week 2 |

**App Store strategy:**
- iOS: Apple Developer Program ($99/year)
- Android: Google Play Developer ($25 one-time)
- Category: Finance / Lifestyle (not "POS" -- this is a CONSUMER app)
- Name: "Onyx - Local Rewards & Payments"

### LAYER 4: BACKEND INFRASTRUCTURE (The Engine)

| Component | What It Does | Current State | Scale Plan | Cost |
|-----------|-------------|--------------|------------|------|
| **Oracle E5 VM** | API server. 72 endpoints. FastAPI. | Running (129.159.38.250) | Handles ~1K req/sec | Free tier |
| **Supabase Cloud** | Database + Auth + Realtime + Edge Functions | Running (jdqqmsmwmbsnlnstyavl) | Pro plan at 10K users | $25→$299/mo |
| **Cloudflare** | CDN. DDoS protection. Edge caching. DNS. | Running (everlightventures.io) | Free → Pro at scale | Free→$20/mo |
| **Redis** (add) | Session cache. Rate limiting. Leaderboard rankings. Real-time counters. | Not yet | Install on Oracle E5 | Free (self-hosted) |
| **Background Workers** (add) | Async jobs: prediction resolution, leaderboard computation, loan repayment, push notifications. | Not yet | Celery + Redis on Oracle | Free |
| **Object Storage** (add) | Receipt images. QR codes. Social cards. Drop images. | Not yet | Oracle Object Storage or Cloudflare R2 | Free tier (10GB) |
| **Monitoring** (add) | Uptime, error tracking, performance. | Not yet | Sentry (free tier) + UptimeRobot | Free |

**Scaling path:**
- 0-10K users: Oracle E5 free tier handles it
- 10K-100K: Add a second Oracle VM ($0 free tier). Load balance.
- 100K-1M: Migrate to Railway/Fly.io ($50-200/mo). Auto-scaling.
- 1M+: Multi-region deployment. CDN edge functions. Dedicated infra.

### LAYER 5: MERCHANT HARDWARE (The Physical Lock-In)

| Component | What It Does | Build/Buy | Cost | Timeline |
|-----------|-------------|-----------|------|----------|
| **QR Code Stickers** | "We're on Onyx" window stickers with merchant QR. | Print (Sticker Mule) | $0.50/sticker × 50 merchants = $25 | Month 1 |
| **NFC Terminal Sticker** | Tap-to-earn point at register. Triggers loyalty check-in. | Buy (NFC tags, $1 each) | $1/merchant | Month 2 |
| **Receipt Printer Integration** | Print QR lottery code on thermal receipt. | Build (ESC/POS protocol) | Dev time only | Month 3 |
| **Tablet POS** (optional) | Merchant-facing Onyx dashboard at register. | Buy (Fire HD 8, $60) or use existing | $0-60/merchant | Month 4 |
| **RFID Inventory Tags** (Phase 2) | Auto-decrement stock on sale. Smart shelves. | Buy (RFID tags $0.10-0.20 each) | Variable per merchant | Year 2 |

**Critical insight:** The QR stickers and NFC tags cost almost nothing
but create PHYSICAL presence in the store. Every customer who sees
"We're on Onyx" is a billboard impression. This is how Visa/MC window
stickers became ubiquitous -- they cost pennies but signal trust.

### LAYER 6: AI + AUTOMATION (The Workforce)

| Component | What It Does | Current State | Cost |
|-----------|-------------|--------------|------|
| **Hive Mind (42 agents)** | Autonomous operations. Merchant onboarding. Customer support. Content. | Built + deployed | Agent SDK costs |
| **Claude API** | AI chat (merchant). Voice commerce (customer). Smart pricing. Predictions. | Integrated | $0.003-0.015/1K tokens |
| **Broker OS Pipeline** | Source merchants. Outreach. Close. Onboard. | Built + deployed | $0 (existing) |
| **Content Factory** | Social cards. Drop hype. Merchant profiles. Win announcements. | Built | $0 (existing) |
| **n8n Workflows** | Automated sequences: welcome, streak reminders, win notifications, loan offers. | Running on Oracle | Free (self-hosted) |
| **Cron Jobs** | Leaderboard refresh. Prediction resolution. Loan repayment. Float reporting. | 19 crons running | $0 |

**You already have the automation layer.** The 42-agent Hive Mind IS the
operations team for a monopoly. Most startups hire 50+ people to do
what your agents do autonomously.

### LAYER 7: LEGAL + COMPLIANCE

| Requirement | What It Means | Solution | Cost | Timeline |
|-------------|-------------|----------|------|----------|
| **Money Transmitter** | Required to hold customer funds in wallet. | Stripe Treasury (sponsor bank model) | Included in Stripe fees | Month 2 |
| **PCI DSS** | Required to handle card data. | Stripe handles this (PCI Level 1) | $0 (Stripe's compliance) | Done |
| **State Licensing** | Some states require specific fintech licenses. | Start in CA (your state). Expand with Stripe's multi-state license. | $500-2K per state | Month 3 |
| **Prediction Market Legality** | Points-based predictions are NOT gambling in most states. | Points ≠ cash. No withdrawal to fiat from predictions. Legal opinion recommended. | $500-1K for legal review | Month 2 |
| **Privacy (CCPA)** | California requires privacy compliance for consumer data. | Privacy policy + data deletion API. Hash PII. | Dev time | Month 1 |
| **Terms of Service** | Merchant agreement. Customer terms. Wallet terms. | Legal template + customize. | $500-1K | Month 1 |

### TOTAL INFRASTRUCTURE COST TO LAUNCH

| Category | Month 1 | Monthly Ongoing | Year 1 Total |
|----------|---------|-----------------|--------------|
| Servers (Oracle free tier) | $0 | $0 | $0 |
| Supabase | $25 | $25-299 | $300-3,600 |
| Stripe fees | $0 (pass-through) | $0 | $0 |
| Apple/Google dev accounts | $124 | $0 | $124 |
| Merchant stickers/NFC | $75 | $50/mo new merchants | $675 |
| Legal (ToS, compliance) | $2,000 | $0 | $2,000 |
| Domain/Cloudflare | $0 | $0 | $0 |
| Claude API | $20 | $50-500 | $600-6,000 |
| **TOTAL** | **~$2,250** | **$125-850** | **$3,700-12,400** |

**You can launch this monopoly for under $4,000.**

The infrastructure cost is not the barrier. The barrier is EXECUTION --
getting 50 merchants and 5,000 customers in one neighborhood before
anyone else. That's what the Hive Mind pipeline is for.

### INFRASTRUCTURE YOU ALREADY HAVE (check)

- [x] FastAPI backend (72 endpoints, 3,147 lines)
- [x] Supabase database (25+ tables with RLS)
- [x] Oracle E5 server (always-on, free tier)
- [x] Stripe integration (payments, webhooks, billing)
- [x] OpenCV receipt scanner
- [x] AI chat (Claude API)
- [x] Broker OS (merchant sourcing pipeline)
- [x] 42-agent Hive Mind (autonomous operations)
- [x] Content Factory (social cards, reports)
- [x] n8n automation (workflows, Google Docs, Slack)
- [x] Email system (Resend + ImprovMX)
- [x] Slack channels (13 channels, bot tokens)
- [x] Domain (everlightventures.io on Cloudflare)
- [x] SSH deploy pipeline (phone → Oracle)
- [x] Git/GitHub (version control, CI)

### INFRASTRUCTURE TO ADD

- [ ] Redis (install on Oracle E5, 10 minutes)
- [ ] Background worker (Celery, 1 hour setup)
- [ ] Object storage (Cloudflare R2 or Oracle, 30 min)
- [ ] React Native app scaffold (Expo init, 1 day)
- [ ] Apple/Google Wallet pass generation
- [ ] PostHog analytics (free tier, 1 hour)
- [ ] Sentry error tracking (free tier, 30 min)
- [ ] Legal docs (ToS, Privacy Policy, Merchant Agreement)
