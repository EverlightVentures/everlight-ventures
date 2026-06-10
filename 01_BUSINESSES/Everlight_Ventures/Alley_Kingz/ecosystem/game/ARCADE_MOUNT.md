# Alley Kingz -- Arcade Mount Guide

How the static prototype in this `game/` folder drops into the Everlight site
arcade at `vantaris/src/app/alley-kingz/page.tsx`.

The build is fully self-contained: `index.html` + `canon.js` + `engine.js`,
zero npm, zero build step. It runs from any static host (`python3 -m http.server`,
Cloudflare Pages, an iframe). That makes mounting trivial.

---

## Option A -- iframe (simplest, recommended for first ship)

1. Copy the three files into the Next public dir:
   ```
   cp index.html canon.js engine.js \
     /path/to/vantaris/public/alley-kingz/
   ```
   (resulting URL path: `/alley-kingz/index.html`)

2. Create `vantaris/src/app/alley-kingz/page.tsx`:
   ```tsx
   export const metadata = {
     title: "Alley Kingz | Everlight Arcade",
     description: "Cyberpunk dog crews, Twisted-Metal rigs, Clash-Royale lanes.",
   };

   export default function AlleyKingzPage() {
     return (
       <main style={{ width: "100%", height: "100dvh", background: "#050507" }}>
         <iframe
           src="/alley-kingz/index.html"
           title="Alley Kingz"
           style={{ width: "100%", height: "100%", border: "none" }}
           allow="autoplay"
         />
       </main>
     );
   }
   ```

The game already handles its own responsive sizing, so the iframe just needs to
fill its container. WebAudio unlocks on the first Play tap (user gesture), which
satisfies the autoplay policy inside the iframe.

---

## Option B -- inline the canvas into the React tree (later)

Only worth it if the arcade needs to share state with the game (score sync,
wallet, leaderboard). Port `index.html`'s inline `<script>` to a client component
that loads `canon.js` + `engine.js` via `next/script` with `strategy="afterInteractive"`,
then drives `window.AK` from a `useEffect` game loop. The engine is framework-agnostic
(it only writes to `window.AK`), so no engine changes are required. Defer this until
there's a reason to couple the two.

---

## Build / deploy note (IMPORTANT)

Any Next build step (`next build`, `next dev`, `pnpm install`) runs on **e5-mother**,
NOT on the phone. The phone proot segfaults on `npm`/`pnpm install` (SIGSEGV, exit 139)
-- this is a known hard constraint. Workflow:

- Edit on the phone, rsync to e5-mother.
- `next build` + `next start` on e5-mother, or push to the `everlightventures.io`
  branch and let Cloudflare Pages build it.
- The static `game/` files themselves need NO build -- they are copy-and-serve.
  You can validate them locally with `python3 -m http.server` on the phone with
  zero risk.

---

## What this is / is not (honest scope)

- IS: single-player playable prototype vs scripted AI, client-side 2D canvas,
  the real 48-card canon (`canon.js`), Clash-Royale lane combat, Twisted-Metal
  rig flavor, abilities firing as a categorized effect set.
- IS NOT (yet): server-authoritative multiplayer, matchmaking, the full 2-ability
  rotation per dog, Seedance 3D rigs, $BCARDD / NFT mint hooks, ladder + chests.
  See the header of `engine.js` for the full DEMO vs FULL-BUILD gap list.

## Boot contract (for whoever maintains the shell)

`engine.js` touches NO DOM -- it exposes everything through `window.AK`.
`index.html` is the renderer + input layer. The shell calls, in order:

1. `AK.init()` once after scripts load (builds the 48-card index).
2. `AK.newMatch(AK.STARTER_DECK_NAMES)` on Play.
3. `AK.update(dt)` every frame, then reads `AK.game`, `AK.effects`,
   `AK.projectiles`, `AK.particles` to draw.
4. `AK.deploy(AK.game.player, handIdx, gx, gy)` on a valid arena tap
   (guarded by `AK.canDeploy(...)`).
5. `AK.resumeAudio()` on the Play gesture to unlock WebAudio.

Match phases: `countdown -> live -> ended`. Result is `AK.game.result`
(`win` | `lose` | `draw`). Arena is `AK.ARENA_W` x `AK.ARENA_H` units;
map taps with `gx = nx * ARENA_W`, `gy = ny * ARENA_H`.
