# ALLEY KINGZ x FORTNITE PLAYBOOK -- Operator One-Pager
**Plain English. For Rich.** | Date: 2026-06-14

## WHAT THE RESEARCH FOUND
Fortnite makes billions on ONE engine, and it's not the shooting. It's the
**Battle Pass + a rotating cosmetic shop + daily quests**. Three mechanics, working
together, that turn "I'll play sometime" into "I have 6 days and 12 levels left, and
I already paid, so I have to finish." We can run that exact playbook in Alley Kingz on
the servers we already pay for, with NO pay-to-win and nothing cashable. Cosmetics are
fun and style only. $BCARDD stays fun and culture, never an investment.

## WHY THESE MECHANICS WIN
- **The Battle Pass (we call it the Alley Pass):** one season-long reward ladder with
  two lanes. A FREE lane everyone earns just by playing, and a PAID lane (bought with
  Gems) that lights up the season's exclusive dog skins, emotes, board art, and a pile
  of Gems. Free players grind, build up sunk cost, then stare at the locked premium
  reward sitting right next to the free one they just grabbed -- that's the
  conversion. Industry estimate: 20-30%+ of engaged players convert.
- **Earn-it-back (the genius hook):** you pay Gems for the pass, finish it, and get
  MORE Gems back than you paid -- enough to buy next season's pass for free. First time
  you buy Gems with cash; after that the pass funds itself and keeps you grinding. The
  Gems you earn get spent on impulse cosmetics in the shop -- that's where we make it
  back. Safe for us because Gems are never cashable.
- **Daily/weekly quests (the Hit List):** small daily jobs build the daily habit; big
  weekly jobs that expire create "don't waste this week." Our own retention research
  says daily-reward players retain 68% better at 6 months.
- **Seasons with a countdown:** a fresh, beatable ladder every 6-8 weeks with a live
  clock and skins that vault forever when the season ends. Scarcity = status. The clock
  turns "later" into "now."
- **The rotating shop (The Drop):** a featured cosmetic that changes daily/weekly with
  a "resets in HH:MM" timer. This is where earned + bought Gems get spent.

It all bolts onto what's already live: every match already pays rewards through one
function -- the pass just rides that. The shop is already server-authoritative and
already takes Stripe payments. The crews/chat/donations we just shipped become the
weekly quests. Nothing gets rebuilt.

## WHAT EACH PHASE GIVES PLAYERS
- **Phase 1 -- the big one:** A seasonal Alley Pass (free + paid lanes), daily + weekly
  quests with a one-tap "claim all," a rotating cosmetic shop with a countdown, and the
  cosmetics themselves -- dog skins, collars/hats, board backgrounds, emotes, crew
  crests. A reason to log in every day and a reason to come back this week.
- **Phase 2:** Seasons auto-roll every 6-8 weeks (old skins vault = bragging rights),
  the earn-it-back math gets tuned, and "skip a tier" / "pass + 10 tiers" Gem options
  for players short on time. (We only ever sell time and style -- never power.)
- **Phase 3:** A monthly subscription (Kingpin Club, ~$14.99/mo) that auto-includes the
  pass + monthly Gems + an exclusive monthly cosmetic + faster earning. Turns one-time
  buyers into recurring monthly revenue.
- **Phase 4:** Timed $BCARDD / city-unlock events with a countdown (Crown Heists),
  bigger quarterly story "chapters" with a shifting card meta, and in-house crossovers.

## COST / TIME SUMMARY
| Phase | What players get | Effort | Cost |
|---|---|---|---|
| **1** | Alley Pass + daily/weekly quests + rotating cosmetic shop + cosmetics | ~1-2 weeks | **$0** (just Stripe per-sale fees) |
| **2** | Auto seasons + vaulted skins + earn-it-back tuning + tier skips | ~1 week | **$0** |
| **3** | Monthly subscription + bonus track + catch-up XP for returners | ~1-2 weeks | **$0 fixed** (Stripe fees) |
| **4** | $BCARDD/city live events + story chapters + crossovers | ~2-3 weeks | **$0** |

No new servers. No new monthly bills. Same Supabase free tier, same Stripe, art painted
by the cron we already run.

## THE GUARDRAILS (so the brand stays clean)
- No pay-to-win. Cards are level-normalized in ranked; a maxed common never beats a
  base mythic. We sell time and looks, never stats.
- Nothing is cashable. Earned Gems buy the next pass and cosmetics -- never a payout.
- Seasons reset the PASS ONLY. Your cards, levels, Gold, and Scrap are NEVER reset.
- $BCARDD is marketed as fun and culture, never as an investment, everywhere.
- The server decides every reward; the client can't cheat itself XP or Gems.

## THE GO DECISION (Phase 1)
**Approve Phase 1: the Alley Pass (free + paid) + daily/weekly quests + the rotating
cosmetic shop with FOMO + cosmetics. ~1-2 weeks, $0 fixed cost, on infra we already
own.** This is the highest-ROI slice -- it's the actual engine behind Fortnite's
money, it makes players log in daily and come back weekly, and the earn-it-back loop
turns a one-time ~$5-8 buyer into a permanent grinder. Everything else (auto seasons,
subscription, live events) builds on top once this proves it converts.

**First build step:** stand up the two pass tables + the `ak-pass` function and wire
match XP into it -- a player earns pass XP from a real match, levels the pass, and
claims a reward, end to end. Quests, the paid lane, and the shop all hang off that.

Say GO and I ship the Phase 1 migration + `ak-pass` function this week.
