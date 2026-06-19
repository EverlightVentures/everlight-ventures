# Alley Kingz -- AI Audio Tool Decision (longevity + consistency first)

Researched 2026-06-17. Criteria in priority order: longevity (will the company exist + be supported in
2-3 yrs), consistency/control, commercial-license clarity, quality, cost, API.

## THE PICKS (decisive)
| Need | PRIMARY | FALLBACK | Cost |
|------|---------|----------|------|
| Hero MUSIC (lobby/battle/victory) | **Suno** (Premier / Suno Studio) | **AIVA** Pro | ~$24/mo annual; cancel after, rights perpetual |
| Growing SFX library | **ElevenLabs** Text-to-SFX | one-time royalty-free SFX pack (non-AI) | $5-22/mo |

**Use a 2-tool stack, not one tool.** ElevenLabs technically does both, but its MUSIC self-serve license
EXCLUDES "Studio Games" (a monetized game shipped on >1 platform = our iOS+Android), forcing music to an
Enterprise contract; and its music is weaker on anime-opening vocal energy than Suno. The two needs also
have opposite cadences: music = a few tracks made ONCE and owned forever; SFX = an ongoing, scriptable pipeline.

## MUSIC = Suno (why)
- LONGEVITY: $400M raise at $5.4B valuation (Jun 2026), 2M+ paying subs, Warner Music SETTLED + signed a
  licensing deal (Nov 2025). Best-capitalized + label-peace = still here in 2-3 yrs.
- CONSISTENCY: **Personas** lock a vocal/style fingerprint so all 3 themes feel like one band; **Suno Studio**
  (Premier) = 12-stem separation, section-targeted regeneration (fix the chorus without re-rolling), warp
  markers, style-consistency slider, reference-audio steering. The strongest option for a cohesive identity.
- LICENSE: Pro/Premier subscribers are assigned all of Suno's rights in the output, PERPETUAL, survives
  cancellation, 0% royalty. Anime/energetic vocal tracks are its strength.
- PLAY: subscribe Premier (~$24/mo annual) for 1-2 months, build + iterate the 3 hero tracks with a locked
  Persona, download stems, cancel. Rights persist. Total to own the music identity: ~$24-48.
- RISKS: (1) Sony still litigating Suno/Udio; a fair-use ruling is expected SUMMER 2026 -- RE-VERIFY before
  final commit (labels sue platforms, not downstream devs, so practical exposure is low). (2) No copyright-
  vesting warranty (you can monetize but may not register copyright on the raw track -- irrelevant for in-game
  music). (3) No official API (fine -- music is made-once).
- FALLBACK = AIVA Pro (~$33/mo): FULL perpetual copyright ownership, no attribution -- the cleanest IP setup
  in the field. Take it if Suno's Sony cloud is a dealbreaker or you want cinematic scoring.

## SFX = ElevenLabs (why)
- LONGEVITY: $500M Series D at $11B (Feb 2026), ~$500M ARR, Sequoia-led, Nvidia-backed, eyeing IPO. The
  safest "rely on it for years" company in the whole field.
- FIT: top-rated SFX quality 2026; text-to-SFX up to 30s with a LOOP parameter; full REST API so
  "chest-open, shimmer, tap, level-up, error" becomes a repeatable SCRIPT (perfect for a growing library).
- LICENSE: every paid plan = royalty-free commercial, no attribution, perpetual after cancel. The "Studio
  Games" exclusion that blocks ElevenLabs MUSIC does NOT apply to SFX (only bar: don't resell the sounds as
  a standalone pack -- irrelevant when embedded).
- PLAY: Creator ($22/mo) for volume + commercial license; move to an API tier ($99 Pro / $330 Scale) only
  when you script the pipeline.
- FALLBACK (deliberately non-AI): a one-time-purchase royalty-free SFX pack you own outright (zero longevity risk).

## ELIMINATIONS (why-not)
- Udio: post-UMG it became a WALLED GARDEN -- downloads/exports/stems DISABLED. You can't ship what you can't
  download. Dead for any game.
- Sonauto (the operator's initial lean): contradictory license (assigns rights vs "non-commercial only") --
  too ambiguous to bet a monetized game on. NOT recommended.
- Soundraw: perpetual + ethically trained + keep-forever, BUT loop/template-based -- can't hit a precise anime
  vocal vibe. A license-safe alt if control matters less than peace of mind.
- Beatoven.ai: cleanest training story (licensed, artist payouts) but only ~$2.4M raised = longevity risk.
- Mubert: game-licensed MUSIC API but generative-loop style, not bespoke hero tracks; not a UI-SFX tool.

## BOTTOM LINE
**Suno (music) + ElevenLabs (SFX).** Two well-capitalized leaders, each the strongest pick for its lane,
each granting perpetual commercial rights on cheap tiers. Track ONE thing: the Sony v. Suno/Udio fair-use
ruling expected summer 2026 -- re-verify before final commit; keep AIVA Pro as the bulletproof-copyright
escape hatch. Net spend to own a full audio identity: ~$24-48 once (music) + $5-22/mo (SFX library).

Sources: Variety/THR (Suno $400M/$5.4B); MBW (Warner-Suno settlement); Chartlex + TechTimes (AI-music lawsuit
tracker, summer-2026 ruling); Suno Help + Terms.Law (rights); Oreate + HookGenius (Personas/Studio/stems);
CNBC + TechCrunch (ElevenLabs $11B/$500M); ElevenLabs Eleven Music terms (Studio Games exclusion); LicenseOrg
(ElevenLabs licensing); RouteNote + Chartlex (Udio walled garden); AIVA EULA; Soundraw license; Sonauto TOS.
