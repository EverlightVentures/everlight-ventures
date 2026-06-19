# ALLEY KINGZ -- RETENTION PSYCHOLOGY + SCREEN-TIME STRATEGY (2026-06-13)
Research-grounded plan to maximize time-on-site. Sources at bottom.

## THE 5 PROVEN LEVERS (and what they buy)
1. LOSS AVERSION via streaks -- losses hurt ~2x more than equal gains. A visible
   streak players don't want to break = +35% DAU; past a 7-day streak, 2.3x more
   likely to return daily.
2. DAILY REWARD HABIT -- 95% of games use it; daily-reward engagers show +68%
   retention at 6 months. It manufactures the habit loop (open -> reward -> repeat).
3. VARIABLE-RATIO REWARDS -- unpredictable beats predictable. Loot boxes, random
   chests, card-pack openings: the UNCERTAINTY is the hook (dopamine on anticipation).
4. ESCALATING PROGRESSION -- climbing bars, tiered milestones, "almost there" gaps
   that pull the next session.
5. SURPRISE & DELIGHT -- occasional unearned gifts; breaks routine, spikes goodwill.

## ALREADY LIVE IN ALLEY KINGZ (good foundation)
- DAILY DROP streak chip (ak_streak) -- loss-aversion seed. UNDER-USED: make the
  reward ESCALATE per day and SHOW what breaks if you skip.
- Lucky Draw (variable-ratio, pity meter) -- textbook variable reward. Keep.
- Crates / chest opening with reveal -- variable reward + anticipation.
- XP bar + levels (escalating progression), World Map road (visible goal ladder).
- Per-card rap sheets / badges / nicknames (identity = retention).

## PRIORITIZED ADDS (cheap -> high ROI first)
P0 (cheap, big): 
- ESCALATING daily streak: day1 small -> day7 big, with a "you'll lose your DAY N
  streak" warning if they miss. Tie it to the existing ak_streak.
- "Come back in Xh for your free crate" timer on the lobby (appointment mechanic).
- Session-end hook: ALWAYS end a match on a forward pull ("1 more win to the City
  Vault", "next level unlocks a Legendary").
P1:
- Daily QUESTS surfaced on the lobby (already built AK-QUEST) with a claim-all.
- A "first win of the day" bonus (variable size).
- Near-miss framing on upgrades ("2 more copies to LVL 5!").
P2:
- Leaderboard / trophy road (social proof + competition) -- needs accounts (have).
- Friend/crew compare once PvP/social lands.

## METRICS TO TRACK (so we optimize, not guess)
- D1 / D7 / D30 retention (the north stars).
- DAU/MAU stickiness ratio (>20% is healthy).
- Avg session length + sessions/day.
- Streak distribution (how many reach day 7+).
- Match-completion rate, world-map progression depth, shop conversion.
- Where players churn (which level/screen = the leak).
Instrument with a lightweight event ping to Supabase (the account layer exists).

## ETHICS GUARDRAIL (operator brand-safe)
Engagement, not exploitation. No dark-pattern paywalls, no pay-to-win (levels cap;
stat curve protected). Variable rewards stay IN-GAME-VALUE-ONLY (Lane A). Make it
fun to come back, never punishing to leave.

## SOURCES
- StriveCloud: 10 ways gamification drives engagement
- Plotline: streaks & milestones (loss aversion, 7-day streak 2.3x)
- thisisglance: reward systems for retention (68% 6-mo)
- SyncGTM 2026: psychology in game dev
