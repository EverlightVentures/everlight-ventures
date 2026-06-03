# Kalshi -- Tomorrow's Playbook (built 2026-06-03 from today's hard lessons)

## What today taught us (don't repeat)
1. **Liquid markets are efficient.** Crypto, NBA moneylines, weather -- all priced to the cent vs the sharp consensus. Tested rigorously, every lane.
2. **Big "edges" are bugs, not gold.** Every 20-97% edge today was a model error (crypto vol too high, sports LLM hallucination, weather sigma 2x too wide, market-type misread). A liquid market does NOT gift a 20%+ edge -- when it looks like it does, OUR MODEL is wrong.
3. **Lead with the stats, always.** The miss today: placed the Spurs bet, THEN gave the breakdown. Standard now: every bet ships with market% / sharp line / model% / edge / EV / why -- BEFORE it's placed.
4. **$0 lost** -- discipline (refusing fake edges) worked. Keep it.

## The three REAL edge engines (ranked by evidence)
1. **Favorite-longshot (`hunt_favorites.py`)** -- the ONLY academically-documented PERSISTENT Kalshi edge. Heavy favorites (85-96c) win slightly more than priced. Systematic basket, measured by the scorecard. Running on e5 cron. *This is the #1 real shot.*
2. **News/injury speed (BUILD NEXT)** -- Perplexity/OSINT monitors the day's slate for breaking news (scratches, lineups, weather alerts, announcements) the market hasn't priced yet, and acts in the seconds-to-minutes window before it corrects. A genuine information/speed edge.
3. **Player-prop research edges** -- where our research read on a specific player (minutes restriction, matchup, rest) beats the market. Props are less efficient than moneylines. (Today's Wemby/Brunson instinct lives here, not in the moneyline.)

## Tomorrow's routine (automated on e5, no babysitting)
- **Morning:** scorecard auto-report -- overnight settled predictions, win-rate/Brier/paper-PnL by lane. THIS is the evidence on whether any lane has real edge.
- **Slate pull:** the day's games/events/weather + new markets (new-market mispricing window).
- **Run the 3 engines** -> candidates, each WITH the full stat breakdown.
- **Bet only real edges** (model meaningfully beats market + a reason that survives scrutiny) -- small, recorded live in the scorecard. Operator can always add an involvement bet (clearly labeled fair/no-edge).
- **Trade AND measure together** -- real trades feed the scorecard; we learn by doing, sized small until a lane proves out.

## The discipline (the whole point)
Quiet edges = trust. Loud edges = suspect a bug. The market is usually right; our job is to find the rare spot where better/faster information says it's wrong -- prove it on the scorecard -- then size up. No gambling dressed as strategy; no waiting forever either. Build, measure, act.

## Status
- e5 24/7: hunt_kalshi (crypto), hunt_events (research), hunt_favorites (favorite-longshot), scorecard settle -- all on cron, all logging.
- Funded $103.14 (after the Spurs bet). Connection solid via public IP (`ssh e5`).
- NEXT BUILD: the news/injury-speed monitor (engine #2).
