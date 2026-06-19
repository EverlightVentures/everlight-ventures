# ALLEY KINGZ -- BUILD SCORECARD (honest: shipped vs not)
Date: 2026-06-15. Live = on alleykingz.online + verified in a real browser. Hard-refresh to see live items.

## SHIPPED + VERIFIED LIVE
| # | Thing | Notes |
|---|---|---|
| 1 | HUD fixes | enemy tower HP draws below, combo chips moved to a left rail, phase-2 speed 1.0, one voice per card |
| 2 | HD maps | full-quality PNG on a separate host (can't be clobbered); 4 cities painted, rest fall back cleanly |
| 3 | Crews + World/Crew chat | Supabase Realtime + presence; create/join/leave/roster |
| 4 | Donations + grants rail | "carry your weight"; the server-to-client reward rail everything reuses |
| 5 | Alley Pass (battle pass) | 30 tiers, match-XP feeds it, claim rewards, premium unlock = 800 gems (atomic spend) |
| 6 | Hit List (quests) | daily + weekly, rewards via grants or Pass XP |
| 7 | The Drop + Drip | rotating cosmetic shop + card skins (in-match), board themes, emotes |
| 8 | Lobby redesign | bottom tab bar + hero + dog photo backdrop, CR/CoD style, playable |
| 9 | Ubuntu boot screen | now lists Alley Kingz + Kalshi dashboards |
| 10 | Docs = viewable HTML + auto-open | this file is proof; lives in 09_DASHBOARD/reports/ |

## SHIPPED but NEEDS YOUR EYES / not fully there
| Thing | Status |
|---|---|
| Combat spacing + team rings (blue=you / red=enemy) | deployed, 0 errors -- needs you to PLAY a match so I can tune the spacing (SEP_VIS_R) |
| Brand sweep (gold + Cinzel on all panels) | done, but you said panels still look "basic" -> needs the FULLER Chop Shop styling (card frames/glass) next |
| Pricing strategy (your per-token model built in) | doc done -- needs your 2 numbers (tool budget + Seedance cost-per-asset) to set exact prices |

## DESIGNED / SPEC'D but NOT BUILT YET
| Thing | Where |
|---|---|
| Chop Shop <- Collection merge | shop already has Card Shop / Crates / Garage; MISSING = a Collection (owned-cards) tab + retire the separate Deck Lab collection |
| Handler Classes (DMZ specials + skill trees + the $BCARDD Dealer) | HANDLER_CLASSES_SPEC.md -- touches the battle engine; phased build |
| 2v2 (ghost, then real-time) | Social Phase 2/3 |
| Tutorial rebuild for the new layout | currently hidden + auto-fire off (so it can't mislead); needs re-targeting to the new tabs |
| Panels -> full Chop Shop look (card frames, glass, layout) | beyond the gold swap I already did |

## BLOCKED ON YOU (these unblock the rest)
| Need | Unblocks |
|---|---|
| Seedance art (API key, OR you generate with the prompt sheet) | custom menu art, the 9:16 portrait hero, card art, the 6 unpainted maps, handler portraits |
| 2 pricing numbers (tool-build budget + Seedance cost-per-asset) | exact per-item gem prices |
| Play-test the live build | confirm combat readability + the lobby before I stack more on top |

## RECOMMENDED ORDER (my plan unless you redirect)
1. You generate the portrait hero -> I wire it -> menu nailed.
2. Me: Chop Shop Collection tab -> the all-in-one card hub.
3. Me: fuller Chop-Shop styling on the chat / gems / pass / quests panels.
4. Me: Handler Classes Phase 1 -> the big new gameplay feature.
