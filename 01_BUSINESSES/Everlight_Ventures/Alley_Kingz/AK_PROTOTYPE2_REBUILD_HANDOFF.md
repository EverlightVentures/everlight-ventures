# ALLEY KINGZ to PROTOTYPE 2 CLASS -- Rebuild Plan + AI Production Workflow (HANDOFF)

_Owner: Rich / Lucrex. Written 2026-07-28. This is the execution handoff for the flagship 3D rebuild. Beat 2012 P2, do not just match it._

---

## 0. The vision (locked)

The movement and visuals of Prototype 2, on a dog-gang superhero power fantasy:
- **Movement:** momentum free-run, wall-run and climb up buildings, air-dash, glide between rooftops, dash gap-close to targets. Fluid and vertical, not grounded and pedestrian.
- **Visuals:** deferred/dynamic lighting + ambient occlusion depth, gritty comic-realism, biomass/decay corruption.
- **World:** a New-York-Zero-style zoned city that visually DECAYS as you push through it (clean -> quarantine -> corrupted), mapped onto Alley Kingz's district-control war.
- **Combat:** bio-powers (tendril grab, bio-bomb, weaponization) plus the dogs' boxing clips as melee.
- **Ownership:** player-owned NFT heroes + $BCARDD economy. This is the structural edge P2 never had.

Modern tech genuinely beats Titanium 2.0 (2012: SSAO, deferred, FXAA, DX9). In 2026 the floor is UE5 Nanite/Lumen or Unity 6 URP/HDRP + Cinemachine, WebGPU where web-native, GTAO/HBAO (better than SSAO), real-time GI. The ceiling is real.

---

## 1. Two tracks (run in parallel, neither blocks the other)

**Track A -- the LIVE web game (the current Three.js build, parent session's lane).**
Keep shipping the P2-FEEL increments on alleykingz.online so players feel progress cheaply while the flagship is built. Key unlock already found in the code: `world3d.project(x, y, height)` at `systems/world3d.js:332` already accepts a HEIGHT argument (currently always 0), so jump/glide/climb are projectable NOW by adding a `me.z` to the hero. Increments: momentum camera (replace the snap `akCamFollow` at `index.html:1015` with a leading lerp + sprint FOV kick), sprint acceleration (replace the flat `1.75x` at `index.html:2745`), `me.z` verticality, dash-punch, sonar ping, and an FXAA+bloom post pass (needs ~8 three.js postprocessing addons vendored on e5, not the phone -- see constraints).

**Track B -- the FLAGSHIP 3D rebuild (THIS handoff).**
A real engine build using the 2026 AI production pipeline. This is where "beat P2" happens.

---

## 2. Engine decision

**Primary recommendation: Unreal Engine 5 (Nanite + Lumen).**
Why UE5 leads for this project:
1. Your own synthesis table picked UE5 + Nanite/Lumen -- Nanite eats the dense city geometry (the zoned NYZ blocks), Lumen gives dynamic lighting that surpasses P2's baked SSAO.
2. There is a PROVEN Claude-Code-in-engine loop: the two free plugins **Unreal Claude** (MCP: screenshots + move objects in-scene) + **Web UE / Vibe UE** (MCP: edit Blueprints, run Python). Claude writes the gameplay logic in natural language, tests itself with screenshots, commits to git. That is the whole "make it happen with AI" thesis, working.
3. FAB marketplace has third-person / open-world / traversal templates to start from.

**Strong alternative: Unity 6 (URP/HDRP + Cinemachine).** Pick this instead if you want (a) the smoothest asset pipeline -- Tripo AI exports models with textures DIRECTLY into Unity, (b) Cinemachine, which delivers the P2 trailing/leaning/FOV camera out of the box, (c) the most mature web3/NFT SDKs (thirdweb, Immutable) and a WebGL export path that keeps an instant-play URL, and (d) it is already the roster's planned AK conversion track. Trade-off: the Claude-Code-in-engine MCP loop is less proven on Unity than the UE5 plugin pair above.

**Web-native fallback (keep the browser URL):** PlayCanvas or Babylon.js 9 + WebGPU. Both beat 2012 fidelity (clustered/volumetric lighting via compute) and stay in the browser. Use only if no-app-store distribution matters more than max fidelity.

**Decision rule:** default to **UE5** for max fidelity + the proven Claude-MCP build loop. Switch to **Unity 6** if the smoother AI-asset pipeline + Cinemachine + web3 SDK maturity + WebGL URL matter more than Nanite/Lumen. Do not run both in parallel for the flagship -- pick one, commit.

---

## 3. The AI production pipeline (the repeatable workflow)

This is the exact loop from the Stefan 3D AI videos, adapted. Each asset runs this pipeline:

1. **Concept art** -- OpenArt / GPT-image / Nanobanana Pro. Claude writes the prompts. Lock ONE style keyword set (e.g. "gritty comic, biomass corruption, dog-gang") and keep it across every asset so the kit is cohesive.
2. **Multi-view** -- generate front/left/right/back views before 3D. This is the single biggest quality lever. (Top view is still a gap; fix chimney-hole-type details manually in Blender.)
3. **3D model -- Tripo AI.** Smart Mesh for characters + simple props (clean animation-ready topology, pick the polycount). High-poly then retopology for complex assets (buildings, vehicles) -- smart mesh fails on complex meshes. Polycount budgets: characters ~20k, hero vehicles 30-60k retopo'd to ~40k, props 2k-12k. Segmentation V2 for part separation.
4. **Texture** -- Tripo texture (2K/4K standard; 8K only for first-person close-ups, wasted on mid/far). Or **Patina.ai** for cheap tileable PBR map sets (~8 cents each) for surfaces you paint in the engine landscape tool: concrete, asphalt, biomass, sand.
5. **Rig** -- **AccuRig** (free; body + fingers) -> export the Unreal/Unity skeleton -> retarget in-engine. Manual weight-paint fixes in Blender for odd body shapes (a dog's rigid torso vs moving limbs).
6. **Animate** -- Mixamo retarget for locomotion/combat, or reuse the existing hero GLB clips.
7. **Assemble (template-first)** -- start from a FAB (UE5) or Unity Asset Store third-person open-world / superhero / traversal template. Swap AI assets in as MODULAR KITS (a fence, a wall, a spire you can place many times). Never build core systems or unique per-block geometry from scratch -- this is what bypassed Radical's 3-year pipeline.
8. **Code (Claude-in-engine)** -- Claude Code opened in the project folder, connected via the MCP plugins. Describe the mechanic in natural language -> Claude writes the Blueprint/C++ -> it screenshots and self-tests -> you review and iterate. `git init` first and commit every milestone (Claude triggers the commits) so you can revert.
9. **Iterate** -- screenshot-review loop; PBR-map fix-ups; polish passes.

---

## 4. Map P2 mechanics to build tasks (natural-language prompts for Claude-in-engine)

Each of these is a "describe it, Claude writes the node graph / C++, you test" task:
- **Traversal component:** momentum sprint with an acceleration curve + lean; wall-run and climb (raycast wall-detect + climb state + root motion); air-dash; glide (clamped descent + forward carry). This is Increment 1 and the go/no-go on the whole vision.
- **Sonar / hunt:** an echo-location pulse that highlights loot, targets, and objectives in-world. Replaces minimap dots. Fits the street/hunt theme.
- **Bio-combat:** tendril grab/impale from range; bio-bomb (inject an enemy -> viral grenade); weaponization (rip a weapon off a vehicle); the dogs' boxing clips as melee contact.
- **Zones = district war:** Green/Yellow/Red decay mapped onto Alley Kingz district control. One modular kit per zone STATE -- clean turf you hold vs corrupted biomass turf that is contested. Material/asset swap per state.
- **NPC density:** crowds, patrols, rooftop life, reactive civilians -- template AI + spawners.

---

## 5. Milestone slices (the videos' cadence: weekend prototype -> asset library in a week -> vertical slice in a month)

- **Week 0 -- stand up the rig.** Designate the BUILD MACHINE (see constraints -- the phone cannot do this). Install UE5 + Claude Code + Unreal Claude + Web UE MCP plugins + node/C++ deps + git. Get a FAB traversal/third-person template running with ONE Alley Kingz hero (bcardd) retargeted in via AccuRig.
- **Week 1 -- weekend prototype (the movement proof).** Core traversal loop playable on a greybox block: momentum run + wall-run + glide + dash. This is the "that is the movement I want" moment. Feel it side by side with a Prototype 2 clip. GO / NO-GO here before spending asset-generation resources.
- **Weeks 2-3 -- asset library + one zone.** Generate the modular NYZ-style city kit (Green -> Red decay states), biomass spires, barricades, via Tripo; tileable PBR surfaces via Patina. Assemble ONE zone as a vertical-slice map.
- **Week 4 -- vertical slice demo.** One walkable zone with traversal + sonar + one combat power + district-control decay + one mission. A real playable demo of the vision.
- **Beyond -- scale.** More zones, combat depth, the NFT hero pipeline, $BCARDD integration, port + polish.

---

## 6. Web3 / NFT hook

The six hero GLBs already shipped -- **bcardd, balboa, jagged, rottweiler, bulldog, malamute** -- are the seed NFT roster. Run them through the same Tripo / AccuRig / Mixamo pipeline for engine-grade rigs. On-chain ownership via thirdweb or Immutable. $BCARDD as the in-game currency. Player-owned heroes rendered at UE5/Unity fidelity = the structural advantage P2 never had.

---

## 7. Honest constraints (flagged, not hidden)

- **Needs a desktop build machine.** UE5/Unity + the MCP plugins do NOT run on the phone (proot) or on e5 headless comfortably. Step 0 is designating a Windows/Linux desktop (the AceMagician PC is the candidate; verify it can run UE5 + the plugins, which lean Windows). This is the real gate.
- **Claude-generated Blueprints work but are messy ("spaghetti").** Human review + supervision is required; detailed prompts beat vague ones. Budget token cost -- roughly 14k tokens per 15 minutes of active generation in the reference builds.
- **AI assets need manual touch-ups** -- weight painting on odd body shapes, retopology on complex meshes, top-view gaps (chimney holes). Hybrid pipeline, not push-button.
- **This is a multi-week project, not a one-shot install.** Anyone claiming a fork "installed" a P2-class UE5 game in one pass is lying. Track A keeps the live web game improving meanwhile.
- **Two source videos unidentified** (`kS36mudf3t4`, `V57nUF7kOjs`) -- returned no indexed metadata (likely unlisted/very new). Paste their titles to fold their workflows in.

---

## 8. First move (do this next)

Designate the build machine, then run Week 0 + Week 1: UE5 + Claude-MCP + a FAB traversal template + bcardd retargeted, and hit the momentum-run + wall-run + glide prototype. That greybox traversal demo is the honest go/no-go on the movement feel before any asset-generation spend. Everything else in this plan is downstream of that one proof.

_Cross-refs: the live-game Track A increments live in the parent session's field-test report and the punch-list workflow. The AK Unity conversion was already a planned dual-track in memory (`project_ak_unity_conversion_dual_track`). This handoff supersedes the vague "make it look better" framing with an executable pipeline._
