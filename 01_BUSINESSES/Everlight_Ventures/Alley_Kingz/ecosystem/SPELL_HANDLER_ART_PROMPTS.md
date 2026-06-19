# Alley Kingz -- Spell + Handler-Special Art Prompts (2026-06-18)

Operator asked for custom art for the 5 spells + the 6 handler specials (currently glyphs/procedural).
All 11 are ENQUEUED in the art factory (art_factory.py). House style (gritty TV-MA cyberpunk dog-gang,
neon-noir, analog grime) is auto-appended by the factory, so the core prompts below are deliberately lean.
These also work pasted straight into Seedance. Render square, drop the PNG at the listed path, and it shows.

## SPELLS  -> game/assets/spells/<slug>.png   (slug = hyphenated card name)
| id | card | path | prompt core |
|----|------|------|-------------|
| spell_freeze | Boneshatter Freeze | spells/boneshatter-freeze.png | cryo blast freezing a neon-lit alley, shattered ice shards + frost shockwave, no characters |
| spell_tar | Tar Pour | spells/tar-pour.png | thick black tar slick flooding a neon street, viscous oil sheen, hazard glow, no characters |
| spell_snare | Snare Trap | spells/snare-trap.png | hidden steel snare wired with a neon tripwire on wet asphalt, about to spring, no characters |
| spell_jolt | Jolt | spells/jolt.png | electric AOE shock burst, blue-white lightning arcs cratering a neon street, no characters |
| spell_strike | Strike | spells/strike.png | fireball artillery strike exploding on a neon street, orange blast core + debris, no characters |

## HANDLER SPECIALS  -> game/assets/specials/<kind>.png
| id | handler -> special | path | prompt core |
|----|--------------------|------|-------------|
| spec_heal_totem | Mender -> Field Kennel | specials/heal-totem.png | deployable neon field-kennel healing totem beacon, green med-cross glow, medic tech, no characters |
| spec_mark | Tracker -> Scent Probe | specials/mark.png | scanning recon pulse painting red target reticles over enemies, scan rings, surveillance, no characters |
| spec_slipstream | Shadow -> Slipstream | specials/slipstream.png | stealth speed-blur slipstream, violet motion trails + cloaking shimmer, no characters |
| spec_drop_rig | Rigger -> Drop Rig | specials/drop-rig.png | deployable turret rig drop-pod, gun nest + tesla coil sparks, street ordnance, no characters |
| spec_war_cry | Bruiser -> War Cry | specials/war-cry.png | shockwave rally roar buff aura, red pulse rings radiating out, aggressive warband energy, no characters |
| spec_house_edge | Dealer -> House Edge | specials/house-edge.png | dealer's gamble: neon playing card + dice burst, gold luck aura, casino, no characters |

## BLOCKER -- generation needs ONE of:
- **CF_AI_TOKEN** (Cloudflare Workers AI) -> the daily art cron generates all 11 automatically (Leonardo API is dead since 2026-06-10).
- **Seedance** -> operator generates with the prompts above (premium quality; pick this for hero-grade art).

## CODE TO SHOW THEM (ready, ~10 lines, ships when art exists):
- Spells: `artSrc()`/`artCandidates()` currently return '' for spells -> add `assets/spells/<slug>.png` with glyph fallback.
- Handler specials: the spawned effect (totem/turret) renders procedurally -> blit `assets/specials/<kind>.png` when present, else keep the procedural shape.
