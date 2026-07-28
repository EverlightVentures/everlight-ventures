# Alley Kingz -- UI DESIGN WORKFLOW (pro inspiration -> human-quality, non-AI-looking UI)
*The operator's pipeline: pull pro UI inspiration (Behance / Dribbble / ThemeForest / Figma) -> screenshot the one you like -> feed it to an AI UI tool (Claude Design / Figma Make / Google Stitch / v0) with a NEGATIVE PROMPT "do not make it look AI-made; give it a human touch" -> integrate. This doc operationalizes it for OUR stack. 2026-06-27.*

## THE PRINCIPLE (why this works)
Behance/Dribbble/ThemeForest/Figma are where UI/UX PROS publish. Feeding a pro screenshot to an AI UI tool gives the AI a HUMAN-designed target to replicate, so the output gets a human touch instead of the generic "obviously-AI" look. The NEGATIVE PROMPT ("don't look AI-made") is mandatory -- AI nails the generic look by default, so you must steer AWAY from it.

## OUR STACK MAPPING (what's automatable vs operator-driven)
- **Our "AI that makes non-AI UI" = the `frontend-design` skill** (in-house): it exists to "create distinctive, production-grade interfaces that avoid generic AI aesthetics." That IS our v0/Figma-Make endpoint, and it edits OUR real HTML/CSS/Canvas (not throwaway mockups).
- **OPERATOR-DRIVEN (interactive, needs your eyes/hands):** browsing Behance/Dribbble + picking + screenshotting the one you like + (optionally) pasting into v0/Figma-Make/Stitch. I cannot visually browse + screenshot those galleries autonomously. When YOU drop a screenshot into the Websites/Download folder (the browser-downloads doctrine), I decode it and use it as the design target.
- **AUTOMATABLE (I run it):** research pro game-UI PATTERNS for our genre (WebSearch/WebFetch the galleries + design writeups), distill a DESIGN LANGUAGE / brief, then apply it via the frontend-design skill onto AK's real surfaces with the anti-AI negative prompt baked in.

## THE SEAMLESS WORKFLOW (repeatable per UI surface)
1. **INSPIRE** -- (operator) screenshot a pro UI you love from Behance/Dribbble/ThemeForest/Figma into Websites/Download, OR (me) research the genre's pro patterns via WebSearch/WebFetch. Output: a reference target + the pattern notes.
2. **BRIEF** -- distill the reference into AK's design language: layout grid, type scale (Playfair/Inter), spacing rhythm, color (gold #D4AF37 / dark #0A0A0A / light #E8E8E8), component shapes, depth/shadow, motion. Plus the HUMAN-TOUCH cues that defeat the AI look (see below).
3. **GENERATE** -- invoke the `frontend-design` skill on the target AK surface (shop / HUD / a panel / the ladder) with: the brief + the reference + the NEGATIVE PROMPT. Keep the existing LOGIC; restyle the PRESENTATION only. engine.js FROZEN; soft-currency parity; 60fps cheap-Android.
4. **INTEGRATE + VERIFY** -- wire into the real file, parse-check, deploy via e5 ship.sh, probe live (no errors, looks right).

## THE ANTI-AI NEGATIVE PROMPT (bake into every UI gen)
"Do NOT make this look AI-generated or like a generic template. Avoid: centered everything, evenly-spaced symmetric cards, default rounded-rectangle everything, lorem-ipsum blandness, the purple-gradient SaaS look, perfect uniformity. DO: intentional asymmetry + visual hierarchy, a real grid with deliberate off-grid accents, gritty texture + grain, hand-tuned spacing, a strong focal point, brand-specific gold-cyberpunk character (worn metal, neon edge-light, street grime), micro-detail that implies a human designer made deliberate choices. Replicate the human-designed reference's COMPOSITION + craft, not a clean-room guess."

## APPLY TO AK (the standing "I cant stand how it looks" fix)
Run this workflow surface-by-surface, highest-traffic first: (1) the HUD + lobby, (2) the SHOP, (3) the core panels (Town Hall / Hit List / the Fence / the Ladder), (4) the interiors, (5) the real-time combat HUD. Each pass = frontend-design skill + the brief + the negative prompt, restyling the real file. Pairs with AK_DEV_TEAM_PLAYBOOKS.md (the art/audio/VFX standards) + the de-emojify doctrine (custom art, never emoji).

## OPTIONAL AUTOMATION (future)
The hermes_browser_outreach harness (browser-use cloud) COULD be repurposed to auto-pull Behance/Dribbble screenshots -- a future upgrade. For now, the operator-screenshot + frontend-design path is the seamless loop.
