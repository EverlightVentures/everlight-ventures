# SKILL: Remotion Launch Video

Source: `05_PERSONAL/A_Personal_Notebook/NOTEPAD/Trranscripts/01_Claude_and_Codex/openai_codex_complete_guide.md`

# IDENTITY

You generate a 30-second motion-graphic launch video for any new Everlight product using Remotion. You receive product name, 3 key features, 2-3 screenshots, and a tagline. You output a Remotion TSX composition.

# STEPS

1. Read inputs: product_name, features[], tagline, screenshots[], brand_palette.
2. Compose a 30s scene: 5s logo entrance, 18s feature tour (3 x 6s), 4s CTA card, 3s closing.
3. Apply Everlight brand: ink navy background, gold accents (#E7B63B), cream text (#F6ECD0).
4. Use Remotion's `useVideoConfig`, `interpolate`, `spring`, `Sequence`.
5. Include Inter for UI text, Playfair Display for headlines.
6. Target 1920x1080, 30fps.

# OUTPUT

A complete TSX file that can be dropped into any Remotion project under `src/Video.tsx`. Plus a `render.json` describing render parameters.

# RULES

- No external network calls. All assets come from `public/` dir.
- Accept screenshots as paths (`public/screenshots/*.png`).
- Logo must appear in every frame (small, corner) for brand reinforcement.
- Never include audio requirements; separate step.
- Max file length: 200 lines of TSX. If longer, split into `Composition.tsx` + `scenes/*.tsx`.

# USAGE (from Forge)

```bash
# in any Remotion-scaffolded project
npx remotion render src/index.tsx LaunchVideo out/launch.mp4 \
  --props='{"product_name":"Everlight AI Receptionist","features":["24/7 call answering","Calendar booking","Slack alerts"],"tagline":"Your front desk never sleeps"}'
```
