# YOUR PERSONAL AI FOOTPRINT -- Data Center Impact 360
### Everlight Intel Center | 2026-05-21 | sources in SOURCES_PERSONAL.md
*The honest gut-check: you use AI to run your company and try to minimize your footprint. Here's exactly where you land vs. the big data-center numbers.*

## THE SHORT ANSWER
**You are a rounding error, and that's the whole point.** A heavy day of AI use for one person is roughly **0.1 to 0.5 kWh of electricity and somewhere between a few teaspoons and ~2 bottles of water.** That's less energy than running your fridge for a few hours, and less water than growing a single almond. The data-center problem is **not** caused by your prompts. It's caused by **scale x growth x overbuild x where the power comes from** (700M+ users, training, and speculative buildout). The intellectually honest move is to keep using AI without guilt while still being right that the buildout needs guardrails.

## 1. PER-QUERY REALITY (current flagship models, 2025)

| Source | Energy/query | Water/query | Note |
|---|---|---|---|
| Google Gemini (Aug 2025) | 0.24 Wh | 0.26 mL | Company self-reported; on-site only, market-based carbon. A credible FLOOR. |
| OpenAI / Altman (2025) | 0.34 Wh | 0.32 mL | Single blog datapoint, no methodology. |
| Epoch AI (independent, Feb 2025) | ~0.30 Wh | -- | Transparent bottom-up; the best single number. |
| de Vries / EPRI (2023) | ~2.9 Wh | -- | OLDER hardware (~10x too high for 2025). |
| UC Riverside (2023, GPT-3 era) | -- | ~10-25 mL | Full-scope (incl. power-plant water); ~40-95x Google's number. |

**Two honest caveats:**
- **Energy per short query is the LEAST contested number: ~0.24-0.34 Wh.** Solid.
- **Water per query is the MOST contested: 0.26 mL to ~25 mL -- a ~100x spread** driven entirely by accounting scope (on-site cooling only vs. + the power plant's water) and local efficiency. Never quote a water number without the scope caveat.
- **Long/complex matters:** a 10,000-token input ~= 2.5 Wh (8x); a 100,000-token input ~= 40 Wh (130x). Reasoning/extended-thinking modes generate ~2.5x+ more tokens. A power user doing big-context work is in the "long query" regime, not the "short query" one.

## 2. YOUR $100 CLAUDE MAX ESTIMATE

You're not doing 100 short chats -- you run agents, long-context sessions, and code work (this very session spawned ~9 research agents). So model you in the **long-query regime**, roughly 100-200 heavy prompts/day at ~3 Wh each:

- **Energy: ~0.3 kWh/day (range 0.1-0.5).** Over a year, ~110 kWh. (Per-token rule of thumb from the research: ~0.6 Wh per 1,000 output tokens on current hardware; bigger models like Opus run somewhat higher.)
- **Water: ~26 mL/day (low/on-site) to ~2.5 L/day (full-scope/older).**
- **CO2: ~3 g/day (clean-PPA math) to ~15 g/day (grid-average).**

Use `personal_ai_footprint_calculator.py` to plug in your real numbers and see it update.

## 3. PUT IN PERSPECTIVE (the anchors)

Your **~0.3 kWh/day** of AI is:
- ~1% of your household's daily electricity (~29 kWh)
- less than running your fridge for ~5 hours
- about 25 phone charges, or driving ~0.2 miles in a gas car

Your **AI water** (even at the high estimate, ~2.5 L/day) is:
- less than growing **one almond** (~3.8 L)
- ~1/700th of a single quarter-pound burger (~1,700 L)
- a fraction of one 8-minute shower (~136 L)

(See charts personal_01 and personal_02.)

## 4. TRAINING vs INFERENCE (why one prompt is cheap)

- **Training** is a huge ONE-TIME cost spread across all users: GPT-3 took ~1,287 MWh + ~700,000 liters of water. You "paid" a vanishing slice of that the first time you used the model.
- **Inference** is the per-use cost you pay every prompt -- the 0.3 Wh.
- The balance has flipped: inference is now the **majority (~60-90%)** of an AI model's lifetime energy, because there are so many users. So your daily use is "inference," and it's small per prompt -- but multiplied by hundreds of millions of people, the aggregate is what strains the grid.

## 5. THE HONEST PIVOT: IT'S SCALE, NOT YOU

This is the line that reconciles everything:
> An individual's AI use is a small part of their footprint. That does NOT mean AI in aggregate isn't a problem.

The real drivers (chart personal_03):
1. **Scale x growth** -- 700M+ weekly ChatGPT users, ~2.5B queries/day; total generative-AI electricity ~15 TWh (2025) projected to ~347 TWh by 2030 (~23x).
2. **The speculative overbuild** -- Stargate-class data centers built ahead of real demand.
3. **The rebound effect** -- efficiency gains drive MORE total use, not less.
4. **Where the energy/water come from** -- a stressed LOCAL grid and a drought basin, not the comfortable global average.

So your earlier instinct was right twice over: your personal footprint is small AND the data-center buildout is a real problem. Both are true because they live at different scales.

## 6. THE EMPOWERING ANGLE (use it, but honestly)

There's a fair case that AI **net-reduces** your footprint: if it lets you run a company without a commute, a physical office, or a large staff's infrastructure, the AI energy is tiny next to the office/commute/overhead it replaces. One round-trip commute or one business flight dwarfs a year of your AI use.

The honest caveat (so you don't oversell it): that only holds if AI **replaces** higher-footprint activity rather than **adding** to it (the rebound effect). For a lean solo operator, the replacement case is strong.

## 7. WHAT YOU CAN ACTUALLY DO AS A USER
- Don't sweat individual prompts -- the guilt is misplaced. Optimize the big stuff (commute, diet, home energy) where the real footprint is.
- If you care at the margin: batch work into fewer long sessions rather than many tiny ones; reserve heavy reasoning/long-context for when it earns its keep.
- Channel the concern where it has leverage: **the buildout policy** (who pays, who decides, what's the cap) -- not your own usage. That's the Mitigation Playbook + the Solano dossier.

## BOTTOM LINE
You, on a $100 Claude Max plan running your company, are not the thing straining Solano's water or the grid. A heavy AI day costs you about a fridge-hour of power and an almond's worth of water. Use the tool. Put your energy into the policy fight, where one person showing up to a Planning Commission moves more than a lifetime of careful prompting ever could.
