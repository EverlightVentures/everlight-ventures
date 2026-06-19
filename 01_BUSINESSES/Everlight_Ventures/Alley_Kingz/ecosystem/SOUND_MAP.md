# Alley Kingz -- SOUND MAP (every event gets a sound identifier)

THE ARCHITECTURE (already built): `sfx(name)` in engine.js is **sample-first, synth-fallback**.
It tries `assets/sfx/<name>.mp3` first; if there's no file it plays a procedural `tone()` synth.
=> Every identifier below is UPGRADEABLE by dropping a named `.mp3` into `game/assets/sfx/`.
No code change needed to swap a placeholder for a bespoke clip. Routed through master gain +
8-voice cap + the `ak_muted` toggle automatically. Add new sample names to `SFX_NAMES` so they preload.

STATUS KEY:  [WIRED] fires + has a synth placeholder today   [NEW] just added this pass
             [TODO] needs wiring   [SAMPLE] drop an mp3 to upgrade from synth to bespoke

## 1. COMBAT
| identifier | trigger | status |
|---|---|---|
| `atk_bullet/cannon/beam/lance/spread/melee` | a unit attacks (per weapon type, pitched by cost+faction via sfxCard) | [WIRED][SAMPLE] |
| `hit_impact` | a UNIT takes a damaging hit (flesh/armor thud) -- was MISSING, combat felt dead | [NEW][SAMPLE] |
| `death` | a unit dies (per-card pitched farewell) | [WIRED][SAMPLE] |
| `tower_hit` / `tower_down` | tower damaged / destroyed | [WIRED][SAMPLE] |
| `proj_whoosh` | projectile launch travel (optional, can fold into atk_*) | [TODO] |

## 2. KEYWORD / ABILITY PROCS (the mechanics we just built)
| identifier | trigger | status |
|---|---|---|
| `ability` | any unit ability cast | [WIRED][SAMPLE] |
| `kw_burn` | a burn unit IGNITES a target (DoT starts) | [NEW][SAMPLE] |
| `kw_deadly` | a deadly hit lands a lethal bite | [NEW][SAMPLE] |
| `kw_ward` / `kw_shield` | ward negates a spell / protected absorbs a hit | [TODO] |
| `afterlife` | a dying unit spawns its spectral token | [NEW][SAMPLE] |
| `evo_up` | a unit climbs an evolution tier (kill-streak) | [NEW][SAMPLE] (was reusing 'ability') |
| handler specials (heal/mark/slip/rig/cry/edge) | tap-fired commander special | [WIRED] via ability/crown |

## 3. CHESTS / REWARDS / LOOT
| identifier | trigger | status |
|---|---|---|
| `chest_open` | crack a crate (wood crack -> gold burst) | [WIRED] -- per-tier variants are a [TODO] upgrade |
| `reward` | match-end reward haul shimmer | [WIRED] |
| `scoop0..4` | loot magnet pickup, pitch climbs with rarity | [WIRED][SAMPLE] |

## 4. UI
| identifier | trigger | status |
|---|---|---|
| `tap` | primary button press (play badge wired; extend to shop/menu CTAs) | [WIRED] -- [TODO] wire more buttons |
| `ui_open` / `ui_back` | open a panel / close it | [TODO] |
| `ui_error` | blocked action (can't afford, locked) | [TODO] |
| `gem_spend` / `coin_spend` | purchase confirm | [TODO] |

## 5. MATCH FLOW
| identifier | trigger | status |
|---|---|---|
| `tick` | 3-2-1 countdown | [WIRED] |
| `sting_major` / `sting_minor` | district/phase transition | [WIRED] |
| `gate_clear` | a district gate breaks | [TODO] (currently reuses crown) |
| `win` / `lose` | victory / defeat result | [WIRED][SAMPLE] |
| `crown` | crown/mythic flourish | [WIRED] |

## 6. MOVEMENT (deliberate recommendation)
| identifier | trigger | recommendation |
|---|---|---|
| `deploy` | unit dropped on the board (thump) | [WIRED][SAMPLE] |
| walk / footsteps | per-unit continuous | **SKIP continuous walk audio** -- with 20-150 units on a Clash-style board it becomes mud + eats the voice cap. The deploy thump + attack/hit sounds carry the motion. Optional: ONE subtle `stomp_heavy` for Vanguard/tank deploys only. |

## 7. LOADING / BOOT
| identifier | trigger | status |
|---|---|---|
| `boot_reveal` | the preload gate fades into the lobby (a satisfying whoosh/chime) | [NEW][SAMPLE] |
| loading ambient | a soft loop under the loading screen | [TODO][SAMPLE] (drop `assets/sfx/load_ambient.mp3`) |

## 8. MUSIC (the BGM deck -- index.html _bgm/_deckA/_deckB, A/B crossfade)
| track | when | status |
|---|---|---|
| lobby theme (energetic anime-opening) | on the lobby | [TODO] -- pick tool first (AUDIO_TOOL_DECISION.md) |
| battle theme | in-match | [TODO] |
| victory / defeat stinger-into-theme | result screen | [TODO] |

---

## PRODUCTION WORKFLOW (once the tool is chosen)
1. For each [SAMPLE] identifier, generate a clip and save it as `game/assets/sfx/<identifier>.mp3`,
   then add the name to `SFX_NAMES` so `loadAllSfx()` preloads it. The synth placeholder auto-yields to it.
2. Keep clips SHORT + punchy (UI/combat 0.1-0.6s; stings 0.5-1.5s) and consistent in loudness
   (the master gain + 8-voice cap handle mixing, but normalize roughly).
3. Music goes to the BGM deck (URL + file), not SFX_BUF.
4. Maintain a CSV manifest: identifier, source tool, license, date pulled (license discipline).

## PRIORITY ORDER (most-felt first)
1. Combat impact pack: `hit_impact`, the 6 `atk_*`, `death` (these play constantly -- biggest feel upgrade).
2. The new mechanics: `kw_burn`, `kw_deadly`, `afterlife`, `evo_up` (so the features READ in audio).
3. Chests + rewards: `chest_open` per tier, `reward`, `scoop*`.
4. Lobby music + `boot_reveal`.
5. UI polish: `ui_open/back/error`, more `tap` coverage.
