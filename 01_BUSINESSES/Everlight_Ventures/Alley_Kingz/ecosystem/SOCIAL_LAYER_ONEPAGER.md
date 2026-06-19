# ALLEY KINGZ -- SOCIAL LAYER (Plain English)

The plan to make Alley Kingz a place players come back to because their CREW is there.
Full build map: `SOCIAL_LAYER_ARCHITECTURE.md`.

## What the research found (Clash Royale + Brawl Stars + Clash of Clans + Marvel Snap)
Every winner runs the same play: **a social home + small daily obligations to other humans.**
Three mechanics do the heavy lifting, in order of payoff:
1. **Clans (we call them CREWS)** -- a home base with a name, tag, crest, roster. Belonging
   alone lifts retention. We tie each crew to one of our 4 factions, so a Boneguard crew flies
   under the $BCARDD house.
2. **The donation loop** -- ask your crew for cards, they send them, both sides get rewarded.
   This is the #1 retention hook in Clash: dozens of tiny interactions a day, and it makes a
   player's *absence felt* by their team. Cheapest to build, deepest hook.
3. **Crew Wars** -- a shared weekly goal with a per-member match quota. Turns "I might log in"
   into "my crew needs my matches before reset."
Chat is the glue: **world chat** (everybody, shows who's online) + **crew chat** (your gang,
green online dots that feed the donation loop).

## What each phase gives players
**Phase 1 -- Crews + Chat + Donations (the big one).** ~3-5 days. **$0.**
- Make/join a crew (a dog gang) tied to a faction; world chat + crew chat with online dots.
- "Carry your weight" card donations -- the daily-return hook above.
- Crew Wars shell: weekly board off everyone's wins.
- Runs entirely on what we already pay for (Supabase). No new servers, no new bills.

**Phase 2 -- Ghost 2v2.** ~1-2 weeks. **$0.**
- Tag-team battles: you + an AI-driven crewmate vs two real snapshot decks. Feels like real
  2v2 (real names, real decks, real ladder) with no live-server cost. Crew Wars become real
  battles here.

**Phase 3 -- Real-time 2v2.** ~2-4 weeks. **~$0 now, ~$5-20/mo later.**
- True live tag-team matches on our always-on e5 box (free), moving to Railway only when lots
  of people play at once. The cheat-proof real-deal version -- earned after 1-2 prove sticky.
- Same "ship the feel, earn the live version" path we already locked for 1v1 PvP.

## Cost summary
Phases 1 and 2 are FREE. Only Phase 3 ever costs money, and only once it's busy enough to need it.

## Safe + locked to Alley Kingz
In-game value only (no money, no pay-to-win). Chat strips links + filters profanity (same
positive-vibes posture as $BCARDD). Uses AK's own login only -- never touches the casino.

## What to build first
Stand up the two crew tables in Supabase (crews + members) + the create/join function -- so
one player starts a crew and another joins it. Chat, donations, and wars all bolt onto those two.

## The one call for you
**Green-light Phase 1 (crews + chat + donations) to ship this week on the free tier?**
Yes = the strongest "come back tomorrow" feature lands fast at zero cost; 2v2 follows after.
