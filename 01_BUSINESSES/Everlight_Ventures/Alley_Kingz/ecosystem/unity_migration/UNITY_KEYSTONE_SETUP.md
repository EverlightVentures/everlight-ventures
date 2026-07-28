# Alley Kingz -> Unity 3D : Phase 0 Keystone Runbook

The portable half is DONE (this folder). This runbook is the desktop half -- the
short session on the AceMagician PC that ends with $BCARDD 0001 walking in a real
3D scene. Everything here is copy-paste; no guesswork.

Phone/e5 cannot run the Unity Editor. The AceMagician (Garuda/Arch, richgee@100.93.253.49)
is the dev box. First power-on, we read the GPU; that decides the art pipeline cost.

---

## Step 0 -- read the GPU (30 seconds, the one open decision)

When the PC is on and on the tailnet, from the phone:

```
ssh -i /root/.ssh/phone_to_arch richgee@100.93.253.49 \
  'lspci | grep -iE "vga|3d controller"; (command -v nvidia-smi && nvidia-smi -L) || echo "no NVIDIA driver"; glxinfo 2>/dev/null | grep -i "renderer"'
```

- NVIDIA with >= ~8-12 GB VRAM -> self-host TRELLIS 2 / Hunyuan3D 2.1 -> whole 425-model
  pipeline is $0. Batch time: ~1-3 min/model on a mid GPU -> the full roster in an
  afternoon-to-overnight run.
- Small/old card (< ~6 GB) -> either a lighter local model or the ~$170 fal.ai batch.
  Still cheap, just not free.
- No dedicated GPU -> ~$170 fal.ai one-time (or ~$20/mo Tripo Pro for the top 24 only).

The Unity Editor itself runs fine on any modern iGPU/dGPU -- the GPU question is ONLY
about the mesh-generation batch, not about running Unity.

---

## Step 1 -- install Unity (one time, ~30-45 min mostly download)

1. Install **Unity Hub** (Arch: `yay -S unityhub`, or the AppImage from unity.com).
2. In Hub -> Installs -> Install Editor -> **Unity 6.3 LTS** (6000.3.x). Add the
   **Android Build Support** module (SDK + NDK + OpenJDK) now so Play Store is one click later.
3. Unity Personal is free under the revenue cap; the Runtime Fee was cancelled in 2024.

## Step 2 -- create the project

1. Hub -> New Project -> **Universal 3D (URP)** template -> name it `AlleyKingz3D`.
2. Window -> Package Manager -> **+** -> Add package by name -> `com.unity.nuget.newtonsoft-json`
   (the importer needs it).

## Step 3 -- drop in the keystone (this folder)

Copy this folder's `Assets/AlleyKingz/` into the project's `Assets/`. You should have:

```
Assets/AlleyKingz/
  Data/cards.json          <- 106 cards, straight from canon.js
  Scripts/CardDef.cs       <- the card ScriptableObject (mirrors cards.json field-for-field)
  Editor/CardImporter.cs   <- the importer
```

Pull the latest `cards.json` any time from the phone/e5:

```
cd .../Alley_Kingz/ecosystem/game
node -e 'var w={};global.window=w;require("./canon.js");require("fs").writeFileSync("cards.json",JSON.stringify({version:1,count:w.CANON_CARDS.length,cards:w.CANON_CARDS},null,1))'
```

## Step 4 -- run the import (the keystone proof)

Menu bar -> **Alley Kingz -> Import Cards from cards.json**.

Console prints `Imported 106 new ... CardDefs`. You now have
`Assets/AlleyKingz/Cards/Card_0001.asset ... Card_0106.asset`, each showing the real
hp/damage/cost/ability/rig in the Inspector. **This proves the "balance never forks"
thesis: the web game's numbers are now canonical Unity assets.**

---

## Step 5 -- the one-dog art pipeline (the other half of the bet)

Target: **$BCARDD 0001**. Source art: `game/assets/cards/0001_bcardd.webp` (+ the
avatar `game/assets/avatar/bcardd_idle.png` for a cleaner front reference).

1. **Mesh.** Upload the card art to Tripo3D (free tier for this one pilot) -> generate
   -> use **Smart Mesh / low-poly** for clean game topology -> download **FBX** (or GLB).
   (Free-tier output is watermark/CC for the pilot only; production uses self-host or Pro.)
2. **Import.** Drag the FBX into `Assets/AlleyKingz/Models/`. Select it -> Inspector ->
   Rig tab -> Animation Type = **Humanoid** -> Apply. Unity auto-maps the skeleton.
3. **Animate.** Go to mixamo.com (free Adobe account) -> upload the same FBX (or use a
   matching character) -> grab **Idle, Walk, Run, Attack (melee), Hit Reaction, Death**
   -> download each as FBX for Unity, **Without Skin** -> drop in `Assets/AlleyKingz/Anims/`.
   Because 0001 is Humanoid, these clips **retarget to every future dog** -- that is the
   whole "425 mesh jobs + 1 animation job" trick.
4. **Controller.** Create an Animator Controller: Idle -> Walk -> Attack transitions on a
   `moving` bool and an `attack` trigger. Assign to the 0001 model in the scene.
5. **Scene + camera.** New scene: a flat ground plane, the 0001 model, a directional
   light. Camera: position high and angled, **~50-60 deg pitch**, Perspective (NOT
   orthographic). This is the "diorama" look -- familiar tilt, real 3D depth.
6. **Play.** Press Play -> 0001 idles, then walk it and trigger an attack. That is the
   vertical slice: **canon data -> Unity asset -> 3D rig -> live animation -> in scene.**

## Step 6 -- in parallel (calendar-hard, start day one)

Register the **$25 Google Play developer account** and enroll **12 closed testers**
(personal accounts created after Nov 2023 need a continuous 14-day closed test before
Production). Money cannot shortcut this clock, so start it while the art scales.

---

## What "done" looks like for Phase 0/1 slice

- [ ] 106 CardDefs imported, stats visible in Inspector (Step 4).
- [ ] 0001 is a rigged 3D model animating (idle/walk/attack) in a URP scene (Step 5).
- [ ] The high-angle perspective camera reads like the game, in true 3D.
- [ ] Play account registered, 12 testers enrolling (Step 6).

Once this slice is real, Phase 1 is: port the engine.js tick loop to C# (with the
tests/ harness as a golden oracle) and add 2-4 more hero dogs. See the blueprint
(AK_UNITY_BLOCKCHAIN_BLUEPRINT.html) for the full seven-phase road.
